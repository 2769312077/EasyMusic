"""鼓组规则生成器。

基于密度、段落和填充规则，程序化生成 GM 标准鼓组音符事件。
支持低/中/高三种密度等级，自动处理段落边界、过渡填充和结尾。

生成逻辑：
    1. 将段落定义映射到每个小节的密度等级。
    2. 预计算每小节的底鼓模式和踩镲密度。
    3. 逐小节生成：边界加 crash、按密度生成 kick/snare/hat。
    4. 小节末尾/段落过渡生成鼓填充（roll/fill）。
"""

from __future__ import annotations

import random

from easymusic.core.drum_map import DRUM_MAP


# ---------------------------------------------------------------------------
# 密度 → 力度范围映射 (kick / snare / hat)
# 密度越高，力度越大，音乐表现力越强
# ---------------------------------------------------------------------------
_DENSITY_VEL: dict[str, dict[str, tuple[int, int]]] = {
    "low":    {"kick": (70, 90),  "snare": (65, 85),  "hat": (50, 70)},
    "medium": {"kick": (90, 110), "snare": (85, 105), "hat": (60, 85)},
    "high":   {"kick": (100, 120), "snare": (95, 115), "hat": (70, 95)},
}

# ---------------------------------------------------------------------------
# 底鼓模式变体（每个 4 拍小节的拍位列表）
# 每种密度提供多个变体，随机选择以增加变化性
# ---------------------------------------------------------------------------
_KICK_PATTERNS: dict[str, list[list[float]]] = {
    "low":    [[0.0, 2.0]],  # Half-time 底鼓，简约
    "medium": [
        [0.0, 2.0],                     # 标准 backbeat
        [0.0, 0.75, 1.5, 2.0],          # 带 syncopation
        [0.0, 2.0, 2.75, 3.5],          # 驱动型末尾
    ],
    "high":   [
        [0.0, 1.5, 2.0, 3.5],              # 驱动型 syncopation
        [0.0, 2.0, 2.75, 3.5],              # 驱动型末尾
        [0.0, 0.75, 2.0, 2.75, 3.5],        # 跳跃 syncopation
    ],
}


def _bar_to_section(sections: list[dict], total_bars: int) -> dict[int, dict]:
    """将每个小节索引映射到它所属的段落定义。

    Args:
        sections: 段落定义列表，每项含 start_bar 和 length_bars。
        total_bars: 总小节数。

    Returns:
        {小节号: 段落定义} 的映射。
    """
    bar_sec: dict[int, dict] = {}
    for sec in sections:
        start = sec["start_bar"]
        end = start + sec["length_bars"]
        for b in range(start, min(end, total_bars)):
            bar_sec[b] = sec
    return bar_sec


def _track_section_density(track_sections: dict, sec_id: str) -> str:
    """从轨道配置中解析指定段落的密度等级。

    Args:
        track_sections: 轨道的 sections 配置字典。
        sec_id: 段落 ID。

    Returns:
        密度等级字符串 ("low" / "medium" / "high" / "off")。
    """
    if not sec_id:
        return "medium"
    ts = track_sections.get(sec_id, {})
    if not ts.get("active", True):
        return "off"
    return ts.get("density", "medium")


def _is_section_boundary(bar: int, bar_section: dict[int, dict]) -> bool:
    """判断指定小节是否是新段落的起始。"""
    if bar == 0:
        return True
    prev_sec = bar_section.get(bar - 1, {})
    curr_sec = bar_section.get(bar, {})
    return prev_sec.get("id") != curr_sec.get("id")


def _is_fill_bar(bar: int, total_bars: int, bar_section: dict[int, dict]) -> bool:
    """判断指定小节是否是填充小节（段落最后小节或整曲最后小节）。"""
    if bar == total_bars - 1:
        return True
    curr_sec = bar_section.get(bar, {})
    next_sec = bar_section.get(bar + 1, {})
    return curr_sec.get("id") != next_sec.get("id")


def _make_event(drum_name: str, start_beat: float, velocity: int, duration_beat: float = 0.1) -> dict:
    """创建标准化的鼓组音符事件字典。

    Args:
        drum_name: 鼓件名称（如 "kick", "snare", "crash"）。
        start_beat: 起始拍位。
        velocity: 力度（1-127）。
        duration_beat: 持续时长（鼓组通常很短，默认 0.1 拍）。

    Returns:
        音符事件字典。
    """
    return {
        "t": "n",
        "p": DRUM_MAP[drum_name],
        "drum_name": drum_name,
        "s": start_beat,
        "d": duration_beat,
        "v": velocity,
    }


def _vel_range(density: str, drum: str) -> tuple[int, int]:
    """获取指定密度和鼓件的力度范围。"""
    return _DENSITY_VEL.get(density, _DENSITY_VEL["medium"]).get(drum, (80, 100))


def generate_drums(song_plan: dict, track: dict) -> list[dict]:
    """根据歌曲计划生成鼓组音符事件。

    基于段落密度配置、节拍位置和填充规则，生成包含 kick、snare、
    hi-hat、crash 和 fill 的完整鼓组编排。

    生成流程：
        1. 解析段落结构，建立小节→密度映射。
        2. 预计算每小节的底鼓模式和踩镲密度种子。
        3. 逐小节生成：
            - 段落起始加 crash
            - 按密度生成 kick 模式
            - 按密度生成 snare（backbeat）
            - 按密度生成 hi-hat（16分音符网格）
            - 填充小节生成 drum fill

    Args:
        song_plan: 歌曲计划字典，须含 "song_plan" → total_bars、sections。
        track: 轨道配置字典，须含 sections 密度设置。

    Returns:
        鼓组音符事件字典列表。
    """
    plan = song_plan["song_plan"]
    total_bars = plan["total_bars"]
    sections = plan.get("sections", [])
    track_sections = track.get("sections", {})

    # 建立小节→段落映射
    bar_section = _bar_to_section(sections, total_bars)

    # 收集所有段落起始小节（用于 crash 放置）
    section_starts: set[int] = set()
    for sec in sections:
        section_starts.add(sec["start_bar"])

    events: list[dict] = []

    # ---------- 预计算每小节的模式种子 ----------
    # 提前决定每小节的底鼓变体和踩镲密度，使同一段落内的模式保持一致
    bar_kicks: list[list[float]] = []
    bar_hat_density: list[float] = []
    for bar in range(total_bars):
        sec = bar_section.get(bar, {})
        density = _track_section_density(track_sections, sec.get("id", ""))
        if density == "off":
            bar_kicks.append([])
            bar_hat_density.append(0.0)
            continue
        kick_variants = _KICK_PATTERNS.get(density, _KICK_PATTERNS["medium"])
        bar_kicks.append(random.choice(kick_variants))
        # 踩镲密度：16分音符位置被填充的比例
        bar_hat_density.append({"low": 0.15, "medium": 0.40, "high": 0.55}.get(density, 0.40))

    # ---------- 逐小节生成 ----------
    for bar in range(total_bars):
        sec = bar_section.get(bar, {})
        sec_id = sec.get("id", "")
        density = _track_section_density(track_sections, sec_id)
        if density == "off":
            continue

        base = bar * 4.0  # 每小节 4 拍
        is_boundary = bar in section_starts

        # ---- 段落边界 Crash ----
        if is_boundary:
            events.append(_make_event(
                "crash", base,
                random.randint(100, 120),
                duration_beat=0.5,
            ))

        is_fill = _is_fill_bar(bar, total_bars, bar_section)
        is_final_bar = (bar == total_bars - 1)

        # ---- Kick（底鼓）----
        vel_k = _vel_range(density, "kick")
        if not is_fill or is_final_bar:
            for beat in bar_kicks[bar]:
                events.append(_make_event("kick", base + beat, random.randint(*vel_k)))

        # ---- Snare（军鼓）----
        vel_s = _vel_range(density, "snare")
        if not is_fill:
            # low 密度仅反拍位军鼓；medium/high 使用全 backbeat
            if density == "low":
                snare_beats = [2.0]
            else:
                snare_beats = [1.0, 3.0]
            for beat in snare_beats:
                events.append(_make_event("snare", base + beat, random.randint(*vel_s)))

        # ---- Hi-Hat（踩镲）----
        vel_h = _vel_range(density, "hat")
        if not is_fill:
            hd = bar_hat_density[bar]
            for i in range(16):
                pos = i * 0.25  # 16分音符位置
                if random.random() >= hd:
                    continue
                # 高密度时偶尔使用开镲
                if density == "high" and random.random() < 0.15:
                    drum = "open_hat"
                else:
                    drum = "closed_hat"
                events.append(_make_event(drum, base + pos, random.randint(*vel_h)))

        # ---- Fill / 过渡填充 ----
        if is_fill:
            _add_fill(events, base, is_final_bar)

    return events


def _add_fill(events: list[dict], base: float, is_final_bar: bool) -> None:
    """为一个小节生成鼓组过渡填充事件。

    填充类型：
        - snare_roll: 十六分音符军鼓滚奏（渐强）
        - tom_fill: 下行通鼓 + 军鼓收尾

    Args:
        events: 目标事件列表（原地修改）。
        base: 小节的起始拍位。
        is_final_bar: 是否是整曲的最后小节。
    """
    if is_final_bar:
        # 最后小节：强 crash + 底鼓强调 + 填充
        events.append(_make_event("crash", base, random.randint(110, 127), duration_beat=0.5))
        events.append(_make_event("kick", base, random.randint(100, 120)))
    else:
        # 段落过渡小节：保留 beat 0 的底鼓作为稳定锚
        events.append(_make_event("kick", base, random.randint(90, 110)))

    # 随机选择填充类型（当前版本偏爱军鼓滚奏）
    fill_type = random.choice(["snare_roll", "tom_fill", "snare_roll"])

    if fill_type == "snare_roll":
        # 十六分音符军鼓滚奏，最后 1-2 拍，力度递增
        fill_start = random.choice([2.0, 3.0])
        steps = int((4.0 - fill_start) / 0.25)
        for i in range(steps):
            pos = fill_start + i * 0.25
            vel = min(127, random.randint(75, 95) + i * 5)
            events.append(_make_event("snare", base + pos, vel))

    elif fill_type == "tom_fill":
        # 下行通鼓填充：high → mid → low → snare
        toms: list[tuple[str, float]] = [
            ("high_tom", 2.0),
            ("mid_tom",  2.5),
            ("low_tom",  3.0),
            ("snare",    3.5),
        ]
        for drum, pos in toms:
            events.append(_make_event(drum, base + pos, random.randint(80, 110), duration_beat=0.15))