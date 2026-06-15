"""MIDI 数据校验模块。

在 MIDI 渲染之前对 MidiIR 进行完整性、有效性和规范性的校验，
确保渲染阶段不会因数据问题而产生错误或不合理的 MIDI 文件。

校验项目：
    1. BPM 范围校验（40-220）
    2. 拍号合法性校验
    3. 通道分配校验（鼓轨/非鼓轨的通道使用）
    4. 音符范围校验（pitch 0-127, velocity 1-127）
    5. 时间边界校验（越界事件处理）
    6. 核心轨道存在性校验
"""

from __future__ import annotations

from easymusic.core.midi_ir import REGISTER_MAP
from easymusic.core.music_theory import get_scale, is_pitch_in_scale
from easymusic.core.schema import MidiIR

# 核心轨道集合：drums、bass、chords、lead
CORE_TRACKS: set[str] = {"drums", "bass", "chords", "lead"}

# BPM 有效范围
_BPM_MIN = 40
_BPM_MAX = 220


def validate_midi_ir(
    midi_ir: MidiIR,
    selected_tracks: list[str] | None = None,
    out_of_bounds_mode: str = "drop",
    enforce_core_tracks: bool = True,
) -> dict:
    """校验 MIDI 中间表示的有效性。

    对 MidiIR 中的所有轨道和音符事件进行全面检查，发现不合规数据时
    根据 out_of_bounds_mode 决定是丢弃还是保留越界事件。

    Args:
        midi_ir: 待校验的 MidiIR 实例。
        selected_tracks: 可选，仅校验指定 ID 的轨道。为 None 时校验全部。
        out_of_bounds_mode: 越界事件处理模式。
            - "drop": 丢弃超出 total_beats 的事件（默认）。
            - "ignore": 保留越界事件（不推荐，可能导致 MIDI 文件异常）。
        enforce_core_tracks: 是否强制要求核心四轨（drums/bass/chords/lead）
            存在且非空。仅在全轨校验（selected_tracks 为 None）时生效。

    Returns:
        校验结果字典，包含：
            - passed: 是否通过所有校验。
            - score: 0.0（未通过）或 1.0（通过）。
            - checks: 各项检查的布尔结果。
            - warnings: 警告信息列表。
            - errors: 错误信息列表。

    Note:
        此函数可能修改 midi_ir 中轨道的 events 列表（当 out_of_bounds_mode="drop" 时）。
    """
    errors: list[str] = []
    warnings: list[dict] = []

    # 越界模式合法性校验
    if out_of_bounds_mode not in {"drop", "ignore"}:
        errors.append(f"无效的 out_of_bounds_mode: {out_of_bounds_mode}，回退为 'drop'")
        out_of_bounds_mode = "drop"

    # 只考虑启用的轨道
    tracks = [t for t in midi_ir.tracks if t.enabled]
    track_map = {t.id: t for t in tracks}

    # ---------- 1. BPM 范围校验 ----------
    bpm = midi_ir.meta.get("bpm", 0)
    bpm_valid = _BPM_MIN <= bpm <= _BPM_MAX
    if not bpm_valid:
        errors.append(f"BPM ({bpm}) 超出有效范围 [{_BPM_MIN}, {_BPM_MAX}]")

    # ---------- 2. 拍号校验 ----------
    ts = midi_ir.meta.get("time_signature", {})
    ts_valid = ts.get("numerator", 0) > 0 and ts.get("denominator", 0) > 0
    if not ts_valid:
        errors.append("拍号无效")

    # ---------- 2b. 调式音阶解析 ----------
    scale_notes: list[str] | None = None
    ks = midi_ir.meta.get("key_signature", "")
    if ks:
        parts = ks.split()
        if len(parts) >= 2:
            try:
                root_note, mode = parts[0], parts[1]
                scale_mode = "major" if mode.lower() == "major" else "natural_minor"
                scale_notes = get_scale(root_note, scale_mode)
            except (ValueError, KeyError):
                scale_notes = None

    # ---------- 3. 核心轨道存在性校验 ----------
    if selected_tracks is None and enforce_core_tracks:
        for core_track in CORE_TRACKS:
            if core_track not in track_map:
                errors.append(f"核心轨道缺失: {core_track}")
            elif len(track_map[core_track].events) == 0:
                errors.append(f"核心轨道为空: {core_track}")
    else:
        if selected_tracks is not None:
            for tid in selected_tracks:
                if tid not in track_map:
                    errors.append(f"指定轨道不存在或已禁用: {tid}")

    # ---------- 4. 逐轨道字段校验 ----------
    total_beats = float(midi_ir.meta.get("total_beats", 0))
    dropped_out_of_bounds_events = 0

    for t in tracks:
        # 通道 9 是 GM 鼓组专用通道，非鼓轨不应使用
        if t.channel == 9 and t.id != "drums":
            errors.append(f"非鼓轨使用了通道 9: {t.id}")
        if t.id == "drums" and t.channel != 9:
            errors.append(f"鼓轨未使用通道 9: {t.id}（当前通道: {t.channel}）")

        # 启用的轨道不应为空
        if t.enabled and len(t.events) == 0:
            errors.append(f"启用的轨道为空: {t.id}")

        # 逐事件校验
        kept_events = []
        for e in t.events:
            # 音高范围（0-127）
            if not (0 <= e.pitch <= 127):
                errors.append(f"音高越界: {t.id} pitch={e.pitch}（应在 0-127 范围内）")
            # 角色音高范围（根据乐器合理演奏范围）
            if t.id != "drums":
                lo, hi = REGISTER_MAP.get(t.role, (21, 108))
                if not (lo <= e.pitch <= hi):
                    warnings.append({
                        "code": "pitch_out_of_register",
                        "message": f"音高超出 {t.role} 合理范围 [{lo},{hi}]: {t.id} pitch={e.pitch}",
                    })
            # 调式约束：非鼓轨音符必须在指定音阶内
            if scale_notes and t.id != "drums":
                if not is_pitch_in_scale(e.pitch, scale_notes):
                    warnings.append({
                        "code": "pitch_out_of_scale",
                        "message": f"调式外音符: {t.id} pitch={e.pitch}（不在 {ks} 音阶内）",
                    })
            # 力度范围（1-127）
            if not (1 <= e.velocity <= 127):
                errors.append(f"力度越界: {t.id} velocity={e.velocity}（应在 1-127 范围内）")
            # 时长有效性
            if e.duration_beat <= 0:
                errors.append(f"无效时长: {t.id} duration_beat={e.duration_beat}（应 > 0）")
            # 起始位置有效性
            if e.start_beat < 0:
                errors.append(f"无效起始位置: {t.id} start_beat={e.start_beat}（应 >= 0）")
            # 越界事件处理
            if e.start_beat + e.duration_beat > total_beats + 1e-6:
                if out_of_bounds_mode == "drop":
                    dropped_out_of_bounds_events += 1
                    continue  # 丢弃此事件
            kept_events.append(e)

        # 如果有被丢弃的事件，更新轨道的 events 列表
        if len(kept_events) != len(t.events):
            t.events = kept_events

    # ---------- 5. 越界事件警告 ----------
    if dropped_out_of_bounds_events > 0:
        warnings.append(
            {
                "code": "dropped_out_of_bounds_events",
                "message": (
                    f"丢弃了 {dropped_out_of_bounds_events} 个超出 "
                    f"total_beats={total_beats} 的事件"
                ),
                "count": dropped_out_of_bounds_events,
            }
        )

    # ---------- 6. 组装结果 ----------
    passed = len(errors) == 0
    return {
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "checks": {
            "valid_bpm": bpm_valid,
            "valid_time_signature": ts_valid,
            "no_empty_tracks": all((not t.enabled) or len(t.events) > 0 for t in tracks),
            "valid_channels": all(0 <= t.channel <= 15 for t in tracks),
        },
        "warnings": warnings,
        "errors": errors,
    }