"""音符生成 Agent。

根据歌曲计划和编配结果，为每条轨道生成具体的音符事件序列。
这是管线的第四阶段，也是最核心的音符生成环节。

生成模式：
    - "llm": 使用 LLM 生成音符事件（最佳音乐性，但成本较高）
    - "rule": 使用程序化规则生成器（快速、稳定、成本低）

使用 ThreadPoolExecutor 并行处理多条轨道，最大化利用并发能力。
"""

from __future__ import annotations

import json
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from easymusic.agents.client import llm_text
from easymusic.core.exceptions import LLMResponseError
from easymusic.prompts import build_track_note_generator_prompt
from easymusic.generators.bass import generate_bass
from easymusic.generators.chord import generate_chords
from easymusic.generators.drum import generate_drums
from easymusic.generators.lead import generate_lead


def _parse_csv_events(text: str) -> list[dict]:
    text = text.replace("\n", ";")
    events: list[dict] = []
    for block in text.split(";"):
        block = block.strip()
        if not block:
            continue
        event: dict[str, str | int | float] = {}
        for pair in block.split(","):
            pair = pair.strip()
            if ":" not in pair:
                continue
            k, v = pair.split(":", 1)
            k = k.strip()
            v = v.strip()
            if k in ("p",):
                event[k] = int(v)
            elif k in ("s", "d"):
                event[k] = float(v)
            elif k == "v":
                event[k] = int(v)
            else:
                event[k] = v
        if event and "p" in event:
            events.append(event)
    return events


def _generate_generic(song_plan: dict, track: dict) -> list[dict]:
    """为非核心轨道生成通用音符事件（简单的交替音符模式）。

    当轨道不是 drums/bass/chords/lead 这四个核心轨道时，
    使用此函数生成基础的交替根音+五音模式，提供最低限度的音乐内容。

    算法：
        每个小节生成两个音符：根音（1拍）+ 高五音（1拍），
        交替进行，形成简单的旋律方向。

    Args:
        song_plan: 歌曲计划字典（已含 "song_plan" 键）。
        track: 当前轨道配置字典。

    Returns:
        音符事件字典列表，每个事件包含 type、pitch、start_beat、duration_beat、velocity。
    """
    total_bars = song_plan["song_plan"]["total_bars"]
    channel = track["midi"]["channel"]
    # 基准音高根据通道号微调，避免不同轨道音高完全重叠
    base_pitch = 60 + min(channel, 12)
    events: list[dict] = []

    for bar in range(total_bars):
        start = bar * 4.0
        events.append(
            {
                "t": "n",
                "p": base_pitch,
                "s": start,
                "d": 1.0,
                "v": 72,
            }
        )
        events.append(
            {
                "t": "n",
                "p": base_pitch + 7,
                "s": start + 2.0,
                "d": 1.0,
                "v": 68,
            }
        )
    return events


def _generate_track_llm(song_plan: dict, arrangement_track: dict) -> list[dict]:
    """使用 LLM 为单条轨道生成音符事件。

    根据歌曲计划和该轨道的配置（乐器、风格、密度），调用 LLM
    生成具体的音符序列。LLM 返回紧凑 CSV 格式，由 _parse_csv_events 解析。

    内置一次重试：若 LLM 返回空内容或事件解析失败，等待 5 秒后重试。

    Args:
        song_plan: 歌曲计划字典（已含 "song_plan" 键）。
        arrangement_track: 当前轨道的编配配置。

    Returns:
        音符事件字典列表。

    Raises:
        LLMError: API 调用失败。
        LLMResponseError: 响应解析失败（重试后仍失败）。
        ValueError: 返回的事件格式无效（重试后仍失败）。
    """
    plan = song_plan["song_plan"]
    prompt = build_track_note_generator_prompt(plan, arrangement_track)

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            text = llm_text(prompt)
            events = _parse_csv_events(text)
            if not events:
                raise ValueError(
                    f"LLM 轨道输出无效：无法解析事件（轨道: {arrangement_track.get('id', '?')})"
                )
            return events
        except (LLMResponseError, ValueError) as e:
            last_error = e
            if attempt == 0:
                time.sleep(5)
                continue
            raise

    raise last_error  # type: ignore[misc]


def generate_notes(
    song_plan: dict,
    arrangement: dict,
    note_generation_mode: str = "llm",
    checkpoint_path: str | None = None,
    progress_callback: Callable[[dict], None] | None = None,
) -> dict:
    """为所有启用轨道生成音符事件。

    使用线程池并行处理多条轨道。每完成一条轨道可保存独立 checkpoint，
    支持断点续运行和进度监控。

    轨道分类与生成策略：
        - drums: 鼓组 → drum_generator（规则）/ LLM
        - bass: 贝斯 → bass_generator（规则）/ LLM
        - chords: 和弦 → chord_generator（规则）/ LLM
        - lead: 主旋律 → lead_generator（规则）/ LLM
        - 其他: → _generate_generic（基础替代模式）

    Args:
        song_plan: 歌曲计划字典。
        arrangement: 编配结果字典。
        note_generation_mode: 生成模式。
            - "llm": 所有轨道使用 LLM 生成（最佳效果，需 API）
            - "rule": 核心四轨使用规则生成器，其他使用 generic
        checkpoint_path: checkpoint 文件路径前缀。
            每轨道的中间结果保存为 "{prefix}.{track_id}.json"
        progress_callback: 进度回调函数，接收包含进度信息的字典。

    Returns:
        包含 "track_events" 的字典，值为各轨道的音符事件列表。
    """
    # 筛选启用的轨道
    enabled_tracks = [
        (track_id, track)
        for track_id, track in arrangement["arrangement"]["tracks"].items()
        if track.get("enabled", True)
    ]

    def _track_checkpoint_path(track_id: str) -> Path | None:
        """获取单轨道 checkpoint 文件的路径。"""
        if not checkpoint_path:
            return None
        path = Path(checkpoint_path)
        return path.with_name(f"{path.stem}.{track_id}{path.suffix}")

    def _save_track_checkpoint(track_event: dict) -> None:
        """将单轨道结果保存为独立 JSON checkpoint。"""
        path = _track_checkpoint_path(track_event["track_id"])
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(track_event, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _generate_one_track(track_id: str, track: dict) -> dict:
        """为单条轨道生成音符事件（在独立线程中执行）。

        根据 note_generation_mode 选择 LLM 生成或规则生成器。
        规则生成模式下，对鼓/bass/chords 轨道的力度添加微小随机扰动，
        避免重复运行时力度完全相同。
        """
        t0 = time.perf_counter()
        print(f"[Track] 音符生成开始: {track_id} (模式={note_generation_mode})")

        if note_generation_mode == "llm":
            events = _generate_track_llm(song_plan, track)
        elif track_id == "drums":
            events = generate_drums(song_plan, track)
        elif track_id == "bass":
            events = generate_bass(song_plan, track)
        elif track_id == "chords":
            events = generate_chords(song_plan, track)
        elif track_id == "lead":
            events = generate_lead(song_plan, track)
        else:
            events = _generate_generic(song_plan, track)

        # 规则生成模式下对鼓/bass/chords 添加微小力度随机扰动
        if note_generation_mode != "llm" and track_id in {"drums", "bass", "chords"}:
            for e in events:
                if e.get("t") == "n":
                    e["v"] = max(1, min(127, int(e.get("v", 90) + random.randint(-4, 4))))

        track_event = {"track_id": track_id, "events": events}
        _save_track_checkpoint(track_event)
        t1 = time.perf_counter()
        print(f"[Track] 音符生成完成: {track_id} 耗时 {t1 - t0:.3f}s, 事件数={len(events)}")
        return track_event

    # ---------- 并行执行 ----------
    results_by_track: dict[str, dict] = {}
    # LM Studio 本地模型通常只有单处理槽位，并发请求会导致排队超时，
    # 因此 LM Studio 模式下强制串行（max_workers=1）
    is_lm_studio = os.getenv("LLM_PROVIDER", "").lower() == "lmstudio"
    max_workers = 1 if is_lm_studio else max(1, min(len(enabled_tracks), 8))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_track_id = {
            executor.submit(_generate_one_track, track_id, track): track_id
            for track_id, track in enabled_tracks
        }

        # 初始进度通知
        if progress_callback:
            progress_callback(
                {
                    "type": "track_progress",
                    "track_total": len(enabled_tracks),
                    "track_completed": 0,
                    "current_track_id": None,
                }
            )

        completed = 0
        for future in as_completed(future_to_track_id):
            track_id = future_to_track_id[future]
            results_by_track[track_id] = future.result()
            completed += 1
            if progress_callback:
                progress_callback(
                    {
                        "type": "track_progress",
                        "track_total": len(enabled_tracks),
                        "track_completed": completed,
                        "current_track_id": track_id,
                    }
                )

    # 按原始顺序组装结果
    out = [results_by_track[track_id] for track_id, _ in enabled_tracks]
    if checkpoint_path:
        path = Path(checkpoint_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"track_events": out}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return {"track_events": out}