"""MIDI 中间表示层的数据模型定义。

定义了整个管线使用的核心数据结构，采用 Python dataclass 实现，
便于类型检查和 JSON 序列化。

数据模型层次：
    NoteEvent  — 单个音符事件（音高、起止节拍、力度）
    TrackIR    — 单条轨道的中间表示（通道、音色、音量、事件列表）
    MidiIR     — 完整的 MIDI 中间表示（元数据 + 所有轨道）
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class NoteEvent:
    """单个音符事件。

    表示一条轨道上的一个音符，包含完整的定位和表现力参数。

    Attributes:
        type: 事件类型，通常为 "note"。
        pitch: MIDI 音符编号（0-127），鼓轨使用 GM 打击乐编号。
        start_beat: 起始节拍位置（以拍为单位，0.0 为第一拍）。
        duration_beat: 持续时长（以拍为单位，必须 > 0）。
        velocity: 按键力度（1-127），影响音量和音色。
        note_name: 可选，音符的音名（如 "C4"），用于调试和可读性。
        drum_name: 可选，鼓件名称（如 "kick"），仅鼓轨使用。
    """

    type: str
    pitch: int
    start_beat: float
    duration_beat: float
    velocity: int
    note_name: str | None = None
    drum_name: str | None = None


@dataclass
class TrackIR:
    """单条轨道的中间表示。

    封装一条 MIDI 轨道的完整配置和所有音符事件数据。

    Attributes:
        id: 轨道唯一标识符（如 "drums", "bass", "lead"）。
        name: 轨道的显示名称（如 "Drums", "Bass Line"）。
        role: 轨道在编曲中的角色（如 "rhythm", "bass", "melody"）。
        channel: MIDI 通道编号（0-15），鼓轨固定为 9。
        program: GM 音色编号（0-127），鼓轨为 None。
        volume: 音量控制值（0-127，对应 CC7）。
        pan: 声像控制值（0-127，对应 CC10，64 为中心）。
        enabled: 是否启用此轨道。
        is_core_track: 是否为核心轨道（drums/bass/chords/lead）。
        events: 此轨道的所有音符事件列表。
    """

    id: str
    name: str
    role: str
    channel: int
    program: int | None
    volume: int
    pan: int
    enabled: bool
    is_core_track: bool
    events: list[NoteEvent] = field(default_factory=list)


@dataclass
class MidiIR:
    """完整的 MIDI 中间表示。

    包含了生成一首完整乐曲所需的所有元数据和轨道数据。

    Attributes:
        meta: 元数据字典，包含 BPM、拍号、调性、小节数、总拍数等信息。
        tracks: 所有轨道的列表。
    """

    meta: dict[str, Any]
    tracks: list[TrackIR]


def to_dict(data: Any) -> Any:
    """将 dataclass 实例递归转换为纯字典。

    用于 JSON 序列化前的数据转换，支持嵌套的 dataclass、list 和 dict。

    Args:
        data: 任意 dataclass 实例、列表或字典。

    Returns:
        纯 Python 字典、列表或原始值。

    示例:
        >>> midi_ir = MidiIR(meta={"bpm": 120}, tracks=[...])
        >>> json.dumps(to_dict(midi_ir))
    """
    if hasattr(data, "__dataclass_fields__"):
        return asdict(data)
    if isinstance(data, list):
        return [to_dict(x) for x in data]
    if isinstance(data, dict):
        return {k: to_dict(v) for k, v in data.items()}
    return data