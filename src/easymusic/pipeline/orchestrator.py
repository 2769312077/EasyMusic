"""管线编排模块。

提供核心的 generate_music 函数，编排完整的 prompt-to-MIDI 生成流程。
这是 EasyMusic 框架中连接所有子模块的顶层编排器。

管线阶段（9 个阶段）：
    Stage 1: intent       — LLM 解析用户意图
    Stage 2: song_plan    — LLM 规划歌曲结构
    Stage 3: arrangement  — LLM 规划乐器编配
    Stage 4: track_events — 并行生成各轨道音符（LLM / 规则）
    Stage 5: midi_ir      — 组装 MIDI 中间表示
    Stage 6: validation   — 校验 MIDI 数据有效性
    Stage 7: midi_render  — 渲染 .mid 文件 + 分轨 .mid
    Stage 8: wav_render   — fluidsynth 合成 WAV 音频（可选，需系统安装 fluidsynth）
    Stage 9: mp3_render   — ffmpeg 转码 MP3（可选，需系统安装 ffmpeg）
"""

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

from easymusic.agents.arrangement_planner import plan_arrangement
from easymusic.agents.client import llm_json
from easymusic.agents.intent_parser import parse_intent
from easymusic.agents.note_generator import generate_notes
from easymusic.agents.song_planner import plan_song
from easymusic.core.midi_ir import assemble_midi_ir, _event_from_dict
from easymusic.core.renderer import render_midi
from easymusic.core.schema import MidiIR, NoteEvent, TrackIR, to_dict
from easymusic.core.validator import validate_midi_ir
from easymusic.pipeline.checkpoints import (
    project_dir,
    generate_project_id,
    save_stage,
    load_stage,
)


def generate_music(
    user_prompt: str,
    output_path: str | None = None,
    selected_tracks: list[str] | None = None,
    project_name: str = "default_project",
    project_id: str | None = None,
    resume: bool = False,
    soundfont_path: str = "/usr/share/sounds/sf2/FluidR3_GM.sf2",
    mp3_bitrate: str = "192k",
    note_generation_mode: str = "llm",
    out_of_bounds_mode: str = "drop",
    render_audio: bool = False,
    progress_callback: Callable[[dict], None] | None = None,
    base_output_dir: str | None = None,
) -> dict:
    """执行完整的 prompt-to-MIDI 生成管线（9 阶段）。

    这是 EasyMusic 的核心入口函数。从用户的自然语言描述出发，
    经过意图解析、歌曲规划、编配规划、音符生成、MIDI 组装、
    校验、分轨 MIDI 渲染、WAV 合成和 MP3 转码，最终产出分轨 .mid 文件。

    Args:
        user_prompt: 用户的自然语言音乐描述。
            示例: "Generate a dark cyberpunk battle BGM at 140 BPM"
        output_path: MIDI 输出文件路径（已弃用，保留兼容性）。
        selected_tracks: 仅导出指定轨道 ID，None 则导出所有启用轨道。
        project_name: 项目名称，用于生成输出目录。
        project_id: 项目唯一 ID。为 None 时自动生成 8 位 UUID 前缀。
        resume: 是否启用断点续运行。为 True 时跳过已完成的阶段。
        soundfont_path: SoundFont 音色库路径（用于 WAV 渲染）。
        mp3_bitrate: MP3 编码比特率（如 "192k"、"320k"）。
        note_generation_mode: 音符生成模式。
            - "llm": 使用 LLM 生成所有轨道音符（最佳音乐性）。
            - "rule": 使用程序化规则生成器（快速、低成本）。
        out_of_bounds_mode: 越界事件处理策略。
            - "drop": 丢弃超出 total_beats 范围的事件（推荐）。
            - "ignore": 保留越界事件。
        render_audio: 是否执行音频渲染阶段（Stage 8-9）。
            为 False 时跳过 WAV 和 MP3 生成，管线仅产出 MIDI 文件。
            需要系统安装 fluidsynth 和 ffmpeg。
        progress_callback: 进度回调函数，接收包含 stage/track 进度的字典。
        base_output_dir: 输出基准目录。生成的 MIDI 文件将存放于
            {base_output_dir}/{project_name}_{YYYYMMDD}/ 目录下。

    Returns:
        完整的管线结果字典，包含各阶段输出、渲染结果和最终产物信息。

    Raises:
        ConfigError: API Key 未配置。
        LLMError: LLM API 调用失败。
        PipelineError: 管线执行过程中不可恢复的错误。
    """
    # ---------- 项目初始化 ----------
    pid = project_id or generate_project_id()
    pdir = project_dir(project_name, base_dir=base_output_dir or "outputs")

    intent_path = pdir / "01_intent.json"
    song_plan_path = pdir / "02_song_plan.json"
    arrangement_path = pdir / "03_arrangement.json"
    track_events_path = pdir / "04_track_events.json"
    midi_ir_path = pdir / "05_midi_ir.json"
    wav_path = pdir / "06_wav.json"
    mp3_path = pdir / "07_mp3.json"
    pipeline_path = pdir / "pipeline_result.json"

    stage_total = 9 if render_audio else 7

    def _emit_stage(stage_index: int, stage_name: str, status: str, extra: dict | None = None) -> None:
        """向进度回调发送阶段状态更新。"""
        if not progress_callback:
            return
        payload = {
            "type": "stage",
            "stage_index": stage_index,
            "stage_total": stage_total,
            "stage_name": stage_name,
            "status": status,
        }
        if extra:
            payload.update(extra)
        progress_callback(payload)

    # ---------- 读取最大时长限制 ----------
    max_duration_seconds: int | None = None
    max_duration_raw = os.getenv("MAX_MUSIC_DURATION_SECONDS", "").strip()
    if max_duration_raw:
        try:
            parsed = int(max_duration_raw)
            if parsed > 0:
                max_duration_seconds = parsed
        except ValueError:
            max_duration_seconds = None

    # =====================================================================
    # Stage 1: 意图解析
    # =====================================================================
    t0 = time.perf_counter()
    _emit_stage(1, "intent", "start")
    print(f"[Stage 1/{stage_total}] intent: start")
    if resume and intent_path.exists():
        intent = load_stage(intent_path)
    else:
        intent = parse_intent(
            user_prompt,
            enforce_core_tracks=(note_generation_mode != "llm"),
            max_duration_seconds=max_duration_seconds,
        )
        save_stage(intent_path, intent)
    t1 = time.perf_counter()
    _emit_stage(1, "intent", "done", {"elapsed_seconds": round(t1 - t0, 3)})
    print(f"[Stage 1/{stage_total}] intent: done ({t1 - t0:.3f}s)")

    # =====================================================================
    # Stage 2: 歌曲规划
    # =====================================================================
    t0 = time.perf_counter()
    _emit_stage(2, "song_plan", "start")
    print(f"[Stage 2/{stage_total}] song_plan: start")
    if resume and song_plan_path.exists():
        song_plan = load_stage(song_plan_path)
    else:
        song_plan = plan_song(intent)
        save_stage(song_plan_path, song_plan)
    t1 = time.perf_counter()
    _emit_stage(2, "song_plan", "done", {"elapsed_seconds": round(t1 - t0, 3)})
    print(f"[Stage 2/{stage_total}] song_plan: done ({t1 - t0:.3f}s)")

    # =====================================================================
    # Stage 3: 编配规划
    # =====================================================================
    t0 = time.perf_counter()
    _emit_stage(3, "arrangement", "start")
    print(f"[Stage 3/{stage_total}] arrangement: start")
    if resume and arrangement_path.exists():
        arrangement = load_stage(arrangement_path)
    else:
        arrangement = plan_arrangement(
            intent, song_plan,
            enforce_core_tracks=(note_generation_mode != "llm"),
        )
        save_stage(arrangement_path, arrangement)
    t1 = time.perf_counter()
    _emit_stage(3, "arrangement", "done", {"elapsed_seconds": round(t1 - t0, 3)})
    print(f"[Stage 3/{stage_total}] arrangement: done ({t1 - t0:.3f}s)")

    # =====================================================================
    # Stage 4: 音符生成（并行）
    # =====================================================================
    t0 = time.perf_counter()
    _emit_stage(4, "track_events", "start")
    print(f"[Stage 4/{stage_total}] track_events: start")
    if resume and track_events_path.exists():
        track_events = load_stage(track_events_path)
    else:
        track_events = generate_notes(
            song_plan,
            arrangement,
            note_generation_mode=note_generation_mode,
            checkpoint_path=str(track_events_path),
            progress_callback=progress_callback,
        )
        save_stage(track_events_path, track_events)
    t1 = time.perf_counter()
    _emit_stage(4, "track_events", "done", {"elapsed_seconds": round(t1 - t0, 3)})
    print(f"[Stage 4/{stage_total}] track_events: done ({t1 - t0:.3f}s)")

    # =====================================================================
    # Stage 5: MIDI IR 组装
    # =====================================================================
    t0 = time.perf_counter()
    _emit_stage(5, "midi_ir", "start")
    print(f"[Stage 5/{stage_total}] midi_ir: start")
    if resume and midi_ir_path.exists():
        midi_ir_dict = load_stage(midi_ir_path)
        tracks = []
        for t in midi_ir_dict["tracks"]:
            tracks.append(
                TrackIR(
                    id=t["id"],
                    name=t["name"],
                    role=t["role"],
                    channel=t["channel"],
                    program=t.get("program"),
                    volume=t.get("volume", 100),
                    pan=t.get("pan", 64),
                    enabled=t.get("enabled", True),
                    is_core_track=t.get("is_core_track", False),
                    events=[_event_from_dict(e) for e in t.get("events", [])],
                )
            )
        midi_ir = MidiIR(meta=midi_ir_dict["meta"], tracks=tracks)
    else:
        midi_ir = assemble_midi_ir(song_plan, arrangement, track_events["track_events"])
        save_stage(midi_ir_path, to_dict(midi_ir))
    t1 = time.perf_counter()
    _emit_stage(5, "midi_ir", "done", {"elapsed_seconds": round(t1 - t0, 3)})
    print(f"[Stage 5/{stage_total}] midi_ir: done ({t1 - t0:.3f}s)")

    # =====================================================================
    # Stage 6: 校验
    # =====================================================================
    t0 = time.perf_counter()
    _emit_stage(6, "validation", "start")
    print(f"[Stage 6/{stage_total}] validation: start")
    validation = validate_midi_ir(
        midi_ir,
        selected_tracks=selected_tracks,
        out_of_bounds_mode=out_of_bounds_mode,
        enforce_core_tracks=(note_generation_mode != "llm"),
    )
    if not validation["passed"]:
        _emit_stage(6, "validation", "failed", {"errors": validation.get("errors", [])})
        return {
            "success": False,
            "error": {
                "type": "validation_error",
                "message": "; ".join(validation["errors"]),
                "module": "validator",
            },
            "validation": validation,
        }
    t1 = time.perf_counter()
    _emit_stage(6, "validation", "done", {"elapsed_seconds": round(t1 - t0, 3)})
    print(f"[Stage 6/{stage_total}] validation: done ({t1 - t0:.3f}s)")

    # =====================================================================
    # Stage 7: 分轨 MIDI 渲染
    # =====================================================================
    t0 = time.perf_counter()
    _emit_stage(7, "midi_render", "start")
    print(f"[Stage 7/{stage_total}] midi_render: start")

    per_track_midi: dict[str, str] = {}
    enabled_tracks = [t for t in midi_ir.tracks if t.enabled]

    def _render_single_track(tr: TrackIR) -> tuple[str, str] | None:
        if selected_tracks is not None and tr.id not in selected_tracks:
            return None
        safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in f"{tr.id}_{tr.role}")
        track_output = str(pdir / f"{safe_name}.mid")
        try:
            render_midi(midi_ir, output_path=track_output, selected_tracks=[tr.id])
            return tr.role, track_output
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=min(len(enabled_tracks), 4)) as executor:
        futures = [executor.submit(_render_single_track, tr) for tr in enabled_tracks]
        for f in as_completed(futures):
            result = f.result()
            if result:
                role, path = result
                per_track_midi[role] = path

    t1 = time.perf_counter()
    _emit_stage(7, "midi_render", "done", {"elapsed_seconds": round(t1 - t0, 3)})
    print(f"[Stage 7/{stage_total}] midi_render: done ({t1 - t0:.3f}s, {len(per_track_midi)} tracks)")

    # =====================================================================
    # Stage 8-9: 音频渲染（可选）
    # =====================================================================
    wav_out = None
    mp3_out = None
    if render_audio:
        try:
            from easymusic.audio.converter import midi_to_wav, wav_to_mp3
        except ImportError:
            print("[Stage 8/9] 音频模块不可用，跳过 WAV/MP3 渲染")
            render_audio = False

    if render_audio:
        t0 = time.perf_counter()
        _emit_stage(8, "wav_render", "start")
        print(f"[Stage 8/{stage_total}] wav_render: start")
        try:
            wav_output = str(pdir / f"{project_name}.wav")
            if resume and wav_path.exists():
                wav_info = load_stage(wav_path)
                wav_out = wav_info.get("wav_file")
            else:
                wav_out = midi_to_wav(list(per_track_midi.values())[0] if per_track_midi else "", wav_output, soundfont_path=soundfont_path)
                save_stage(wav_path, {"wav_file": wav_out, "soundfont": soundfont_path})
            t1 = time.perf_counter()
            _emit_stage(8, "wav_render", "done", {"elapsed_seconds": round(t1 - t0, 3)})
            print(f"[Stage 8/{stage_total}] wav_render: done ({t1 - t0:.3f}s)")
        except Exception as e:
            _emit_stage(8, "wav_render", "failed", {"error": str(e)})
            print(f"[Stage 8/{stage_total}] wav_render: failed — {e}")
            wav_out = None

    if render_audio and wav_out:
        t0 = time.perf_counter()
        _emit_stage(9, "mp3_render", "start")
        print(f"[Stage 9/{stage_total}] mp3_render: start")
        try:
            mp3_output = str(pdir / f"{project_name}.mp3")
            if resume and mp3_path.exists():
                mp3_info = load_stage(mp3_path)
                mp3_out = mp3_info.get("mp3_file")
            else:
                mp3_out = wav_to_mp3(wav_out, mp3_output, bitrate=mp3_bitrate)
                save_stage(mp3_path, {"mp3_file": mp3_out, "bitrate": mp3_bitrate})
            t1 = time.perf_counter()
            _emit_stage(9, "mp3_render", "done", {"elapsed_seconds": round(t1 - t0, 3)})
            print(f"[Stage 9/{stage_total}] mp3_render: done ({t1 - t0:.3f}s)")
        except Exception as e:
            _emit_stage(9, "mp3_render", "failed", {"error": str(e)})
            print(f"[Stage 9/{stage_total}] mp3_render: failed — {e}")
            mp3_out = None

    # =====================================================================
    # 组装最终结果
    # =====================================================================
    bpm = midi_ir.meta["bpm"]
    duration_seconds = midi_ir.meta["total_beats"] * (60.0 / bpm)

    final_output = {
        "success": True,
        "per_track_midi": per_track_midi,
        "project_dir": str(pdir),
        "wav_file": wav_out,
        "mp3_file": mp3_out,
        "metadata": {
            "title": midi_ir.meta["title"],
            "bpm": bpm,
            "key": midi_ir.meta["key_signature"],
            "time_signature": (
                f"{midi_ir.meta['time_signature']['numerator']}/"
                f"{midi_ir.meta['time_signature']['denominator']}"
            ),
            "duration_seconds": duration_seconds,
            "total_bars": midi_ir.meta["total_bars"],
            "loopable": midi_ir.meta["loopable"],
        },
        "tracks": [
            {"id": t.id, "name": t.name, "role": t.role, "description": "generated"}
            for t in midi_ir.tracks
            if t.enabled and (selected_tracks is None or t.id in selected_tracks)
        ],
        "validation": {"passed": validation["passed"], "score": validation["score"]},
    }

    result = {
        "project": {
            "project_name": project_name,
            "project_id": pid,
            "project_dir": str(pdir),
            "resume": resume,
        },
        "intent": intent,
        "song_plan": song_plan,
        "arrangement": arrangement,
        "track_events": track_events,
        "midi_ir": to_dict(midi_ir),
        "validation": validation,
        "final_output": final_output,
    }
    save_stage(pipeline_path, result)
    return result


def export_tracks(midi_ir_dict: dict, selected_tracks: list[str], output_path: str) -> dict:
    """从保存的 MidiIR 字典渲染指定轨道到文件。

    用于从已保存的 checkpoint 中导出单轨 MIDI，无需重新运行管线。

    Args:
        midi_ir_dict: MidiIR 的字典表示（来自 checkpoint 文件）。
        selected_tracks: 要导出的轨道 ID 列表。
        output_path: 输出 .mid 文件路径。

    Returns:
        render_midi 的结果字典。
    """
    tracks = []
    for t in midi_ir_dict["tracks"]:
        events = [_event_from_dict(e) for e in t.get("events", [])]
        tracks.append(
            TrackIR(
                id=t["id"],
                name=t["name"],
                role=t.get("role", "unknown"),
                channel=t["channel"],
                program=t.get("program"),
                volume=t.get("volume", 100),
                pan=t.get("pan", 64),
                enabled=t.get("enabled", True),
                is_core_track=t.get("is_core_track", False),
                events=events,
            )
        )
    midi_ir = MidiIR(meta=midi_ir_dict["meta"], tracks=tracks)
    return render_midi(midi_ir, output_path=output_path, selected_tracks=selected_tracks)