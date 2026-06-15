"""和弦规则生成器。

基于和弦进行，程序化生成块状和弦（block）或琶音式（arp）的和弦音符事件。

和弦轨道的核心职责：
    - 直接呈现当前和声色彩
    - 提供中频密度和织体
    - 连接低音和高频旋律空间

生成策略：
    - block 模式：在每小节起始同时击响和弦所有音符
    - arp 模式：将和弦音符分解为顺序琶音
    - 用 motif 序列控制切换，2→3 八度跳跃增加变化
"""

from __future__ import annotations

import random

from easymusic.core.music_theory import chord_to_midi_notes


def generate_chords(song_plan: dict, track: dict) -> list[dict]:
    """根据歌曲计划和弦进行生成和弦音符事件。

    支持两种模式：
        - block（块状和弦）：在每小节开始同时奏出所有和弦音符，
          适合需要清晰和声感的段落。
        - arp（琶音）：将和弦分解为顺序单音，营造流动感和空间感。

    motif 值含义：
        - 0, 3, 6 → block 模式，使用较低八度
        - 1, 2 → arp 模式，使用较低八度
        - 4, 5 → arp 模式，使用较高八度

    Args:
        song_plan: 歌曲计划字典，须含 "song_plan" → total_bars、chord_progression。
        track: 轨道配置字典。

    Returns:
        和弦音符事件列表。
    """
    total_bars = song_plan["song_plan"]["total_bars"]
    prog = song_plan["song_plan"]["chord_progression"]

    # 生成 motif 序列（控制模式和八度）
    motif_len = 8
    motif = [random.choice([0, 1, 2, 3, 4, 5, 6]) for _ in range(motif_len)]
    motif[0] = 0  # 从稳定的 block 开始
    motif[-1] = random.choice([0, 2, 4])  # 结尾收敛

    events: list[dict] = []
    for bar in range(total_bars):
        chord = prog[bar % len(prog)]["chord"]
        # 根据 motif 决定八度
        base_octave = 2 if motif[bar % motif_len] in (0, 1, 2) else 3
        notes = chord_to_midi_notes(chord, base_octave=base_octave)
        base = bar * 4.0

        # 决定当前小节的模式
        pattern_type = "block" if motif[bar % motif_len] in (0, 3, 6) else "arp"

        for p in notes:
            if pattern_type == "block":
                events.append(
                    {
                        "t": "n",
                        "p": p,
                        "s": base,
                        "d": random.choice([2.0, 3.0, 4.0]),
                        "v": random.randint(54, 78),
                    }
                )
            else:
                step = 0.0
                while step < 4.0:
                    events.append(
                        {
                            "t": "n",
                            "p": p,
                            "s": base + step,
                            "d": random.choice([0.25, 0.5, 0.75]),
                            "v": random.randint(52, 74),
                        }
                    )
                    step += 1.0
    return events