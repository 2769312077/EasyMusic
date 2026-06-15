"""贝斯规则生成器。

基于和弦进行的根音，按节拍位置和 motif 模式程序化生成贝斯音符事件。

贝斯的核心职责：
    - 明确当前和弦的根音（和声基础）
    - 提供低频节奏动力
    - 连接和弦变化，形成低音线条

生成算法：
    1. 解析和弦进行的根音（MIDI 编号）。
    2. 生成 motif 模式（控制八度跳跃：0-2=低八度, 3-6=跳跃到更高八度）。
    3. 逐小节在 4 个拍位生成音符，根据 motif 决定八度。
"""

from __future__ import annotations

import random

from easymusic.core.music_theory import NOTE_TO_SEMITONE


def _root_pitch(chord: str) -> int:
    """从和弦符号提取根音的 MIDI 编号。

    C1 = MIDI 24 作为基准八度，确保贝斯在正确的低频音域内。

    Args:
        chord: 和弦符号，如 "C"、"Dm"、"Bb"。

    Returns:
        根音的 MIDI 编号。
    """
    root = chord[:-1] if chord.endswith("m") else chord
    return 24 + NOTE_TO_SEMITONE[root]  # C1 = 24


def generate_bass(song_plan: dict, track: dict) -> list[dict]:
    """根据歌曲计划和弦进行生成贝斯音符事件。

    生成策略：
        - 每个拍位生成一个音符（4 拍/小节 = 4 个音符/小节）。
        - 使用 motif 序列控制八度变化，避免单调。
        - motif[0] 固定为 0（小节开始用低八度根音），motif[-1] 收敛到稳定音符。
        - 力度在 82-104 之间随机（mid-high 力度范围）。

    Args:
        song_plan: 歌曲计划字典，须含 "song_plan" → total_bars、chord_progression。
        track: 轨道配置字典。

    Returns:
        贝斯音符事件列表。
    """
    total_bars = song_plan["song_plan"]["total_bars"]
    prog = song_plan["song_plan"]["chord_progression"]

    # 生成 motif 序列（控制八度跳跃的模式）
    motif_len = 8
    motif = [random.choice([0, 1, 2, 3, 4, 5, 6]) for _ in range(motif_len)]
    motif[0] = 0  # 从低八度开始
    motif[-1] = random.choice([0, 2, 4])  # 结尾收敛

    events: list[dict] = []
    for bar in range(total_bars):
        # 获取当前小节的和弦（支持循环使用和弦进行）
        chord = prog[bar % len(prog)]["chord"]
        root = _root_pitch(chord)
        base = bar * 4.0

        # 四个拍位
        beat_positions = [0.0, 1.0, 2.0, 3.0]
        for idx, beat in enumerate(beat_positions):
            m = motif[(bar * 2 + idx) % motif_len]
            # 根据 motif 值决定八度偏移
            if m in (0, 1, 2):
                octave = 0   # 低八度 — 夯实和声基础
            elif m in (5, 6):
                octave = 24  # 两个八度上 — 旋律性跳跃
            else:
                octave = 12  # 一个八度上 — 标准变化

            pitch = root + octave
            events.append(
                {
                    "t": "n",
                    "p": pitch,
                    "s": base + beat,
                    "d": random.choice([0.5, 0.75, 1.0]),
                    "v": random.randint(82, 104),
                }
            )
    return events