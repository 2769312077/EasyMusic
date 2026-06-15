"""主旋律规则生成器。

基于调式音阶和 motif 模式，程序化生成主旋律音符事件。

旋律的核心设计原则：
    - 使用音阶步进为主，小跳为辅（65% 概率执行步进平滑）。
    - motif[0] 固定为根音作为乐句锚点，motif[-1] 收敛到稳定音。
    - 力度 84-108（突出于伴奏之上）。
    - 音符间距 0.5 拍（八分音符节奏），适合游戏 BGM 的连续能量感。

算法流程：
    1. 从调式获取音阶。
    2. 生成 motif 序列（乐句的"轮廓"）。
    3. 对 mid-motif 应用步进平滑（相邻音符间音程不超过 2 度）。
    4. 逐小节产生 8 个音符（4 beats / 0.5 = 8 notes）。
"""

from __future__ import annotations

import random

from easymusic.core.music_theory import get_scale, note_name_to_midi


def generate_lead(song_plan: dict, track: dict) -> list[dict]:
    """根据歌曲计划的调式音阶生成主旋律音符事件。

    使用内部 motif 序列作为旋律轮廓的"蓝图"，再通过步进平滑
    使旋律更自然流畅。

    生成逻辑：
        1. 获取调式的大调/小调音阶。
        2. 生成 8 长的 motif 序列（0-6 表示音阶度数）。
        3. 锁定首尾 (- 始根音，- 稳定音)。
        4. 65% 概率步进平滑 (相邻音符间 ±1~2 度)。
        5. 逐小节产生 8 个 0.5 拍间距的音符。

    Args:
        song_plan: 歌曲计划字典，须含 "song_plan" → key、total_bars。
        track: 轨道配置字典。

    Returns:
        主旋律音符事件列表。
    """
    root = song_plan["song_plan"]["key"]["root"]
    mode = song_plan["song_plan"]["key"].get("mode", "minor")
    scale = get_scale(root, "major" if mode == "major" else "natural_minor")

    # ---------- 生成旋律轮廓 (motif) ----------
    motif_len = 8
    motif = [random.choice([0, 1, 2, 3, 4, 5, 6]) for _ in range(motif_len)]
    motif[0] = 0  # 乐句起始锚点：根音
    motif[-1] = random.choice([0, 2, 4])  # 乐句结尾收敛到稳定音

    # 步进平滑：相邻音符间小幅移动，保持旋律流畅性
    for i in range(1, motif_len - 1):
        if random.random() < 0.65:
            step = random.choice([-2, -1, 1, 2])
            motif[i] = max(0, min(6, motif[i - 1] + step))

    # ---------- 生成音符事件 ----------
    total_bars = song_plan["song_plan"]["total_bars"]
    events: list[dict] = []
    for bar in range(total_bars):
        base = bar * 4.0
        for i, step in enumerate(motif):
            # 将音阶度数转换为具体 MIDI 音高（默认八度 5）
            pitch = note_name_to_midi(f"{scale[step % len(scale)]}5")
            velocity = random.randint(84, 108)
            duration = random.choice([0.25, 0.4, 0.5, 0.75])
            events.append(
                {
                    "t": "n",
                    "p": pitch,
                    "s": base + i * 0.5,
                    "d": duration,
                    "v": velocity,
                }
            )
    return events