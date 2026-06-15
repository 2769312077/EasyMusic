"""MIDI 文件渲染模块。

将 MidiIR 中间表示通过 mido 库渲染为标准的 .mid 文件。

渲染流程：
    1. 创建 MidiFile 对象并设置 ticks_per_beat。
    2. 在第一条轨道（conductor track）写入 tempo 和 time_signature 元事件。
    3. 为每条实际轨道创建一个 MidiTrack，写入 track_name、program_change 和 CC 控制。
    4. 将每条轨道的 note_on/note_off 事件按绝对 tick 排序后转为 delta-time 写入。

关于 delta-time：
    MIDI 文件中的每个事件都包含一个 delta-time 值，表示距离前一个事件
    经过的 tick 数。本模块使用 _absolute_to_delta 函数将绝对 tick 时间
    转换为相对 delta 值。
"""

from __future__ import annotations

from pathlib import Path

from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo

from easymusic.core.schema import MidiIR


def beat_to_tick(beat: float, ticks_per_beat: int = 480) -> int:
    """将节拍单位转换为 MIDI tick 值。

    MIDI 使用 tick 作为时间精度的最小单位。默认分辨率 480 PPQN
    （Pulses Per Quarter Note）意味着每个四分音符被分为 480 个 tick。

    Args:
        beat: 节拍位置（以拍为单位，1.0 = 一个四分音符）。
        ticks_per_beat: 每拍的 tick 数，默认 480。

    Returns:
        四舍五入后的整数 tick 值。
    """
    return int(round(beat * ticks_per_beat))


def _absolute_to_delta(events: list[dict]) -> list[Message]:
    """将绝对 tick 时间的事件列表转换为相对 delta-tick 的 mido Message 列表。

    处理逻辑：
        1. 按 (tick, kind) 排序，确保在相同 tick 上 note_off 先于 note_on。
        2. 将相邻事件的 tick 差作为前一个事件的 time 值。

    Args:
        events: 按绝对 tick 排列的事件列表，每个元素包含 "tick"、"kind" 和 "msg"。

    Returns:
        mido Message 列表，每个消息的 time 属性为相对 delta 值。
    """
    # 排序：先按时间，同 tick 时 note_off (kind="off") 优先
    events = sorted(events, key=lambda e: (e["tick"], e["kind"] == "off"))
    last_tick = 0
    out: list[Message] = []
    for e in events:
        delta = e["tick"] - last_tick
        out.append(e["msg"].copy(time=delta))
        last_tick = e["tick"]
    return out


def render_midi(
    midi_ir: MidiIR,
    output_path: str,
    selected_tracks: list[str] | None = None,
) -> dict:
    """将 MidiIR 渲染为标准的 .mid 文件。

    支持全轨渲染和选择性渲染。选择性渲染时只输出指定 ID 的轨道。

    Args:
        midi_ir: 待渲染的 MIDI 中间表示实例。
        output_path: 输出 .mid 文件的完整路径。
        selected_tracks: 可选，仅渲染指定 ID 列表的轨道。
            为 None 时渲染所有启用轨道。为空列表时会报错。

    Returns:
        渲染结果字典，包含：
            - success: 是否成功
            - output_path: 输出文件路径
            - total_tracks: 实际渲染的轨道数
            - total_note_events: 总共的音符事件数
            - duration_seconds: 音乐时长（秒）
            - warnings: 警告信息列表

    Raises:
        ValueError: selected_tracks 为空或包含不存在的轨道 ID。
    """
    # 参数校验
    if selected_tracks is not None and len(selected_tracks) == 0:
        raise ValueError("selected_tracks 不能为空列表，请传入 None 以渲染所有轨道")

    all_tracks = [t for t in midi_ir.tracks if t.enabled]
    if selected_tracks is None:
        tracks = all_tracks
    else:
        selected_set = set(selected_tracks)
        track_ids = {t.id for t in all_tracks}
        missing = selected_set - track_ids
        if missing:
            raise ValueError(f"selected_tracks 包含不存在的轨道 ID: {sorted(missing)}")
        tracks = [t for t in all_tracks if t.id in selected_set]

    # 创建 MIDI 文件并设置分辨率
    mid = MidiFile(ticks_per_beat=midi_ir.meta.get("ticks_per_beat", 480))

    # --- Conductor Track（元数据轨道）---
    # 存储全局的 tempo 和 time_signature 信息
    meta_track = MidiTrack()
    mid.tracks.append(meta_track)
    bpm = midi_ir.meta["bpm"]
    tempo = bpm2tempo(bpm)
    ts = midi_ir.meta["time_signature"]
    meta_track.append(MetaMessage("set_tempo", tempo=tempo, time=0))
    meta_track.append(
        MetaMessage(
            "time_signature",
            numerator=ts["numerator"],
            denominator=ts["denominator"],
            clocks_per_click=24,
            notated_32nd_notes_per_beat=8,
            time=0,
        )
    )

    # --- 遍历每条轨道，渲染音符事件 ---
    total_note_events = 0
    for tr in tracks:
        t = MidiTrack()
        mid.tracks.append(t)

        # 轨道元数据：名称
        t.append(MetaMessage("track_name", name=tr.name, time=0))

        # 音色切换：鼓通道（9）不发送 program_change
        if tr.program is not None and tr.channel != 9:
            t.append(Message("program_change", channel=tr.channel, program=tr.program, time=0))

        # 轨道控制：音量（CC7）和声像（CC10）
        t.append(Message("control_change", channel=tr.channel, control=7, value=tr.volume, time=0))
        t.append(Message("control_change", channel=tr.channel, control=10, value=tr.pan, time=0))

        # 将 NoteEvent 列表转换为 mido Message 事件
        abs_events: list[dict] = []
        for ev in tr.events:
            total_note_events += 1
            start_tick = beat_to_tick(ev.start_beat, mid.ticks_per_beat)
            dur_tick = beat_to_tick(ev.duration_beat, mid.ticks_per_beat)
            # note_on 事件（按键）
            abs_events.append(
                {
                    "tick": start_tick,
                    "kind": "on",
                    "msg": Message("note_on", channel=tr.channel, note=ev.pitch, velocity=ev.velocity, time=0),
                }
            )
            # note_off 事件（离键），至少持续 1 tick 以避免零长度音符
            abs_events.append(
                {
                    "tick": start_tick + max(dur_tick, 1),
                    "kind": "off",
                    "msg": Message("note_off", channel=tr.channel, note=ev.pitch, velocity=0, time=0),
                }
            )

        # 将绝对事件转为 delta-time 事件并写入轨道
        for msg in _absolute_to_delta(abs_events):
            t.append(msg)

    # 写入文件
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    mid.save(str(out))

    # 计算音乐时长
    bpm = midi_ir.meta["bpm"]
    duration_seconds = midi_ir.meta["total_beats"] * (60.0 / bpm)

    return {
        "success": True,
        "output_path": str(out),
        "selected_tracks": selected_tracks,
        "ticks_per_beat": mid.ticks_per_beat,
        "total_tracks": len(tracks),
        "total_note_events": total_note_events,
        "duration_seconds": duration_seconds,
        "warnings": [],
    }