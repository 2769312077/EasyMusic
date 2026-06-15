"""MIDI 中间表示组装模块。

将歌曲计划、编配结果和各轨道音符事件组装为统一的 MidiIR 数据结构。
这是管线中连接"规划层"和"渲染层"的关键桥梁。
"""

from __future__ import annotations

from easymusic.core.music_theory import get_scale, is_pitch_in_scale
from easymusic.core.schema import MidiIR, NoteEvent, TrackIR

REGISTER_MAP: dict[str, tuple[int, int]] = {
    "bass":     (24, 48),
    "rhythm":   (36, 72),
    "harmony":  (48, 72),
    "pad":      (48, 84),
    "melody":   (60, 84),
    "arpeggio": (48, 84),
    "accent":   (48, 72),
    "strings":  (48, 72),
    "piano_lh": (36, 60),
    "piano_rh": (48, 84),
    "guitar":   (48, 72),
}


def _event_from_dict(d: dict) -> NoteEvent:
    pitch = d.get("p", d.get("pitch"))
    if pitch is None:
        pitch = 60
    return NoteEvent(
        type=d.get("t", d.get("type", "note")),
        pitch=pitch,
        start_beat=d.get("s", d.get("start_beat", 0)),
        duration_beat=d.get("d", d.get("duration_beat", 0.25)),
        velocity=d.get("v", d.get("velocity", 80)),
        note_name=d.get("note_name"),
        drum_name=d.get("drum_name"),
    )


def _fix_channel_assignments(tracks: list[TrackIR]) -> None:
    """自动纠正 MIDI 通道分配。

    GM 规范要求通道 9 专用于鼓轨。LLM（尤其是本地小模型）有时
    会将通道 9 分配给非鼓轨道，或将鼓轨分配到其他通道。
    本函数在 IR 组装阶段自动修正这些分配错误。

    规则：
        1. 非鼓轨使用了通道 9 → 分配一个空闲的非 9 通道
        2. 鼓轨未使用通道 9 → 强制设置为通道 9（若 9 被占用则先腾出）

    Args:
        tracks: 已组装的 TrackIR 列表，原地修改。
    """
    used = {t.channel for t in tracks}

    for t in tracks:
        if t.id == "drums":
            if t.channel != 9:
                if 9 in used:
                    for other in tracks:
                        if other.channel == 9:
                            free = next(c for c in range(16) if c != 9 and c not in used)
                            other.channel = free
                            used.discard(9)
                            used.add(free)
                            break
                t.channel = 9
                used.add(9)
        elif t.channel == 9:
            free = next(c for c in range(16) if c != 9 and c not in used)
            t.channel = free
            used.add(free)


def _clamp_pitch_by_role(track_id: str, role: str, pitch: int) -> int:
    """根据轨道角色将音高限制在合理演奏范围内。

    鼓轨不做限制（GM鼓件映射有自己的编号范围）。

    Args:
        track_id: 轨道 ID。
        role: 轨道角色。
        pitch: 原始音高。

    Returns:
        夹紧后的音高值。
    """
    if track_id == "drums":
        return pitch
    lo, hi = REGISTER_MAP.get(role, (21, 108))
    return max(lo, min(hi, pitch))


def _snap_to_scale(pitch: int, scale_notes: list[str]) -> int:
    """将音高修正到最近的调式内音高。

    对于调式外音符，向上下各搜索一个半音范围内的调式内音高，
    优先选择更近的修正方向。若上下等距，优先向下修正。

    Args:
        pitch: 原始音高。
        scale_notes: 音阶音符名称列表。

    Returns:
        修正后的音高（如果原音高已在音阶内则不变）。
    """
    if is_pitch_in_scale(pitch, scale_notes):
        return pitch
    for delta in range(1, 6):
        up = pitch + delta
        dn = pitch - delta
        up_ok = 0 <= up <= 127 and is_pitch_in_scale(up, scale_notes)
        dn_ok = 0 <= dn <= 127 and is_pitch_in_scale(dn, scale_notes)
        if dn_ok:
            return dn
        if up_ok:
            return up
    return pitch


def assemble_midi_ir(
    song_plan: dict,
    arrangement: dict,
    track_events: list[dict],
) -> MidiIR:
    """根据歌曲计划和编配结果，将所有轨道事件组装为 MidiIR。

    处理流程：
        1. 从编配结果中提取轨道配置（通道、音色、混音参数）。
        2. 从音符事件中匹配每条轨道的音符列表。
        3. 从歌曲计划中提取全局元数据（BPM、拍号、调性等）。
        4. 创建 MidiIR 实例并返回。

    Args:
        song_plan: 歌曲计划字典，必须包含 "song_plan" 键。
            内含 BPM、拍号、调性、总小节数等元数据。
        arrangement: 编配结果字典。
            内含 "tracks"（或 "arrangement.tracks"）轨道配置。
        track_events: 每条轨道的音符事件列表。
            每个元素包含 "track_id" 和 "events" 字段。

    Returns:
        组装完成的 MidiIR 实例。

    Raises:
        KeyError: 必需的字段缺失。
    """
    # 兼容两种编配结果格式：直接的 "tracks" 或 "arrangement.tracks"
    arrangement_tracks = arrangement.get("tracks")
    if arrangement_tracks is None:
        arrangement_tracks = arrangement.get("arrangement", {}).get("tracks", {})

    # 建立 track_id → events 的快速查找映射
    event_map: dict[str, list[dict]] = {x["track_id"]: x.get("events", []) for x in track_events}

    # 从歌曲计划中解析调式音阶（用于调式外音符修正）
    sp = song_plan["song_plan"]
    scale_notes: list[str] | None = None
    try:
        key_info = sp.get("key", {})
        root = key_info.get("root")
        mode = key_info.get("mode", "minor")
        scale_type = "major" if mode == "major" else "natural_minor"
        if root:
            scale_notes = get_scale(root, scale_type)
    except (ValueError, KeyError):
        scale_notes = None

    tracks: list[TrackIR] = []
    for track_id, t in arrangement_tracks.items():
        # 跳过已禁用的轨道
        if not t.get("enabled", True):
            continue
        # 将原始事件字典转换为 NoteEvent 对象列表，同时夹紧音高和调式修正
        role = t.get("role", "unknown")
        clamped_events = []
        for e in event_map.get(track_id, []):
            ev = _event_from_dict(e)
            ev.pitch = _clamp_pitch_by_role(track_id, role, ev.pitch)
            if scale_notes and track_id != "drums":
                ev.pitch = _snap_to_scale(ev.pitch, scale_notes)
            clamped_events.append(ev)
        tracks.append(
            TrackIR(
                id=track_id,
                name=t["name"],
                role=t["role"],
                channel=t["midi"]["channel"],
                program=t["midi"].get("program"),
                volume=t["mix"].get("volume", 100),
                pan=t["mix"].get("pan", 64),
                enabled=t.get("enabled", True),
                is_core_track=t.get("is_core_track", False),
                events=clamped_events,
            )
        )

    # 自动纠正通道分配：非鼓轨禁止使用通道 9，鼓轨必须使用通道 9
    _fix_channel_assignments(tracks)

    # 从歌曲计划中提取全局元数据
    plan = song_plan["song_plan"]
    bpm = plan["bpm"]
    time_sig = plan["time_signature"]
    total_bars = plan["total_bars"]
    beats_per_bar = time_sig["numerator"]

    meta = {
        "title": plan["title"],
        "bpm": bpm,
        "ticks_per_beat": 480,  # 标准 MIDI 分辨率
        "time_signature": time_sig,
        "key_signature": f"{plan['key']['root']} {plan['key']['mode']}",
        "total_bars": total_bars,
        "beats_per_bar": beats_per_bar,
        "total_beats": total_bars * beats_per_bar,
        "loopable": plan.get("loopable", True),
    }

    return MidiIR(meta=meta, tracks=tracks)