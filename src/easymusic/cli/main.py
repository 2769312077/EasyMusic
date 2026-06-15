"""EasyMusic CLI 命令行入口。

提供 ecms 命令，支持从终端直接生成 MIDI 音乐文件。

用法：
    ecms "your music prompt"                     # 基本用法
    ecms "prompt" --output my_music.mid          # 指定输出路径
    ecms "prompt" --note-mode rule               # 使用规则生成模式
    ecms "prompt" --resume                       # 断点续运行
    ecms "prompt" --tracks drums,bass            # 仅导出指定轨道
    ecms --test                                  # API 连通性测试
    ecms --help                                  # 显示帮助信息
"""

from __future__ import annotations

import argparse
import json
import traceback
from pathlib import Path

from easymusic._version import __version__
from easymusic.pipeline.orchestrator import generate_music


def main() -> None:
    """EasyMusic CLI 主入口函数。

    解析命令行参数并调用 generate_music 管线。
    支持完整的参数配置和 API 连通性测试。
    """
    parser = argparse.ArgumentParser(
        prog="ecms",
        description=f"EasyMusic v{__version__} — 基于 LLM 的 prompt-to-MIDI 音乐生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  ecms "Generate a dark cyberpunk battle BGM at 140 BPM"
  ecms "轻快的8-bit游戏背景音乐" --note-mode rule
  ecms "Epic fantasy orchestral" --output epic.mid --project-name fantasy_01
  ecms --test
        """.strip(),
    )

    # ---------- 核心参数 ----------
    parser.add_argument(
        "prompt",
        type=str,
        nargs="?",
        default=None,
        help="音乐描述提示词（自然语言）",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="MIDI 输出文件路径（默认自动生成到 outputs/ 目录下）",
    )
    parser.add_argument(
        "--tracks",
        type=str,
        default=None,
        help="仅导出指定轨道，逗号分隔（如 drums,bass,lead）",
    )
    parser.add_argument(
        "--project-name",
        type=str,
        default="default_project",
        help="项目名称，用于生成输出目录名（默认: default_project）",
    )
    parser.add_argument(
        "--project-id",
        type=str,
        default=None,
        help="项目唯一 ID，不指定则自动生成 8 位 UUID 前缀",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="启用断点续运行，跳过已完成的管线阶段",
    )

    # ---------- 生成模式参数 ----------
    parser.add_argument(
        "--note-mode",
        type=str,
        choices=["llm", "rule"],
        default="llm",
        help="音符生成模式。llm: 使用大模型生成（最佳效果，需 API）；"
             "rule: 使用程序化规则生成（快速、低成本，默认: llm）",
    )
    parser.add_argument(
        "--out-of-bounds-mode",
        type=str,
        choices=["drop", "ignore"],
        default="drop",
        help="越界事件处理策略。drop: 丢弃超出范围的事件（推荐）；"
             "ignore: 保留越界事件（默认: drop）",
    )

    # ---------- 音频参数 ----------
    parser.add_argument(
        "--render-audio",
        action="store_true",
        help="启用音频渲染（Stage 8-9）：生成 WAV 和 MP3 文件。需要系统安装 fluidsynth 和 ffmpeg",
    )
    parser.add_argument(
        "--soundfont",
        type=str,
        default="/usr/share/sounds/sf2/FluidR3_GM.sf2",
        help="SoundFont 音色库路径（用于 WAV 渲染，默认: /usr/share/sounds/sf2/FluidR3_GM.sf2）",
    )
    parser.add_argument(
        "--mp3-bitrate",
        type=str,
        default="192k",
        help="MP3 编码比特率（默认: 192k）",
    )

    # ---------- 工具参数 ----------
    parser.add_argument(
        "--test",
        action="store_true",
        help="运行 API 连通性测试（生成一个测试 MIDI 验证 LLM 配置是否正常）",
    )
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"EasyMusic v{__version__}",
    )

    args = parser.parse_args()

    # ---------- 测试模式 ----------
    if args.test:
        _run_test()
        return

    # ---------- 参数校验 ----------
    if not args.prompt:
        parser.error("缺少必需参数: prompt（音乐描述提示词）")

    # ---------- 解析轨道选择 ----------
    selected_tracks: list[str] | None = None
    if args.tracks:
        selected_tracks = [x.strip() for x in args.tracks.split(",") if x.strip()]

    # ---------- 执行管线 ----------
    try:
        result = generate_music(
            args.prompt,
            output_path=args.output,
            selected_tracks=selected_tracks,
            project_name=args.project_name,
            project_id=args.project_id,
            resume=args.resume,
            soundfont_path=args.soundfont,
            mp3_bitrate=args.mp3_bitrate,
            note_generation_mode=args.note_mode,
            out_of_bounds_mode=args.out_of_bounds_mode,
            render_audio=args.render_audio,
        )
    except Exception as e:
        tb = traceback.format_exc()
        print(
            json.dumps(
                {
                    "success": False,
                    "error": {
                        "type": type(e).__name__,
                        "message": str(e),
                        "traceback": tb,
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    # ---------- 输出结果 ----------
    if result.get("success") is False:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 保存完整管线结果为 JSON
    out_json = Path(result["project"]["project_dir"]) / "generated.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 打印最终产物信息
    final = result.get("final_output", {})
    print(f"\n=== EasyMusic 生成完成 ===")
    print(f"MIDI 文件: {final.get('midi_file', 'N/A')}")
    per_track = final.get("per_track_midi", {})
    if per_track:
        print(f"分轨 MIDI:")
        for role, path in per_track.items():
            print(f"  [{role}] {path}")
    meta = final.get("metadata", {})
    if meta:
        print(f"标题: {meta.get('title', '?')}")
        print(f"BPM: {meta.get('bpm', '?')}  |  调性: {meta.get('key', '?')}")
        print(f"拍号: {meta.get('time_signature', '?')}  |  时长: {meta.get('duration_seconds', 0):.1f}s")
        print(f"小节数: {meta.get('total_bars', '?')}  |  可循环: {meta.get('loopable', False)}")
    tracks = final.get("tracks", [])
    if tracks:
        print(f"轨道 ({len(tracks)}):")
        for t in tracks:
            print(f"  - {t['name']} [{t['role']}]")
    print(f"JSON 结果: {out_json}")
    print(f"项目目录: {result['project']['project_dir']}")
    print(f"校验: {'通过' if result['validation']['passed'] else '失败'}")


def _run_test() -> None:
    """运行 LLM API 连通性测试。

    向配置的 LLM 服务发送一个简单的测试请求，验证 API Key、
    Base URL 和模型配置是否正确。
    """
    import mido
    from pathlib import Path

    from easymusic.agents.client import llm_json

    TEST_PROMPT = "Generate a single C4 quarter note at 120 BPM, 4/4 time, duration 2 seconds."

    print("=== EasyMusic API 连通性测试 ===\n")

    try:
        response = llm_json(
            "Generate music metadata for this prompt: " + TEST_PROMPT + "\n\n"
            "Respond with JSON only: {\"bpm\": number, \"key\": string, "
            "\"note_pitch\": number, \"note_velocity\": number, \"note_duration_beats\": number}"
        )
    except Exception as e:
        print(f"测试失败: {e}")
        print(f"\n请检查以下配置:")
        print(f"  - OPENAI_API_KEY 是否已设置且有效")
        print(f"  - OPENAI_BASE_URL 是否正确（默认: https://api.deepseek.com/v1）")
        print(f"  - OPENAI_MODEL 是否存在（默认: deepseek-chat）")
        return

    bpm = response.get("bpm", 120)
    pitch = response.get("note_pitch", 60)
    velocity = response.get("note_velocity", 80)
    duration_beats = response.get("note_duration_beats", 1.0)

    out_dir = Path("outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    midi_path = out_dir / "test_output.mid"

    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))
    track.append(mido.Message("program_change", program=0, time=0))
    ticks_per_beat = mid.ticks_per_beat
    track.append(mido.Message("note_on", note=pitch, velocity=velocity, time=0))
    track.append(
        mido.Message(
            "note_off",
            note=pitch,
            velocity=0,
            time=int(ticks_per_beat * duration_beats),
        )
    )
    mid.save(str(midi_path))

    print("测试通过! API 连接成功。")
    print(f"  生成测试 MIDI: {midi_path.resolve()}")
    print(f"  BPM: {bpm}  |  音符: MIDI {pitch}  |  力度: {velocity}")


if __name__ == "__main__":
    main()