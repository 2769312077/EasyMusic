"""音乐理论工具模块。

提供音符名称与 MIDI 编号互转、音阶生成、和弦解析等基础乐理功能。
所有音名使用升号表示法（C、C#、D、...），同时支持降号的同音异名输入（Db → C#）。

核心映射关系：
    - MIDI 音符 60 = 中央 C（C4），即八度号 4
    - MIDI 音符 0-127 对应 C-1 到 G9
    - 每增加一个八度，MIDI 编号增加 12
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 音名 → 半音序号映射（支持升号表示和降号同音异名）
# ---------------------------------------------------------------------------
NOTE_TO_SEMITONE: dict[str, int] = {
    "C": 0,
    "C#": 1,
    "Db": 1,  # 升 C 与降 D 为同音异名
    "D": 2,
    "D#": 3,
    "Eb": 3,  # 升 D 与降 E 为同音异名
    "E": 4,
    "F": 5,
    "F#": 6,
    "Gb": 6,  # 升 F 与降 G 为同音异名
    "G": 7,
    "G#": 8,
    "Ab": 8,  # 升 G 与降 A 为同音异名
    "A": 9,
    "A#": 10,
    "Bb": 10,  # 升 A 与降 B 为同音异名
    "B": 11,
}

# 半音序号 → 音名（升号表示法）
SEMITONE_TO_NOTE: list[str] = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# MIDI 音符有效范围
_MIDI_MIN = 0
_MIDI_MAX = 127


def note_name_to_midi(note_name: str) -> int:
    """将音符名称（如 "C4"、"F#3"、"Bb5"）转换为 MIDI 音符编号。

    格式：
        - 音名（1-2 个字符，C/C#/Db/Eb/...）+ 八度号（1 位数字）
        - 示例：C4 → 60，A4 → 69，C3 → 48

    Args:
        note_name: 音符名称字符串。

    Returns:
        MIDI 音符编号（0-127）。

    Raises:
        ValueError: 音名格式无效或结果超出 MIDI 范围。
    """
    # 从末尾提取八度号（最后一位数字）和音名（剩余部分）
    name = note_name[:-1]
    octave_str = note_name[-1]
    if not octave_str.isdigit():
        raise ValueError(f"无法解析音符名称中的八度号: {note_name!r}")
    octave = int(octave_str)
    if name not in NOTE_TO_SEMITONE:
        raise ValueError(f"无效的音名: {name!r}，支持: {list(NOTE_TO_SEMITONE.keys())}")

    midi_number = (octave + 1) * 12 + NOTE_TO_SEMITONE[name]
    if not (_MIDI_MIN <= midi_number <= _MIDI_MAX):
        raise ValueError(
            f"音符 {note_name} 对应的 MIDI 编号 {midi_number} 超出有效范围 [{_MIDI_MIN}, {_MIDI_MAX}]"
        )
    return midi_number


def midi_to_note_name(midi_note: int) -> str:
    """将 MIDI 音符编号转换为音符名称（升号表示法）。

    Args:
        midi_note: MIDI 音符编号（0-127）。

    Returns:
        音符名称字符串，如 "C4"、"F#3"。

    Raises:
        ValueError: MIDI 编号超出有效范围。
    """
    if not (_MIDI_MIN <= midi_note <= _MIDI_MAX):
        raise ValueError(f"MIDI 音符编号 {midi_note} 超出有效范围 [{_MIDI_MIN}, {_MIDI_MAX}]")
    octave = midi_note // 12 - 1
    note = SEMITONE_TO_NOTE[midi_note % 12]
    return f"{note}{octave}"


def _rotate_scale(root: str, intervals: list[int]) -> list[str]:
    """根据根音和音程序列生成音阶。

    Args:
        root: 根音名称（如 "C"、"F#"）。
        intervals: 半音距序列（如 [0, 2, 4, 5, 7, 9, 11] 为大调）。

    Returns:
        音阶中按顺序排列的音名列表。
    """
    root_semi = NOTE_TO_SEMITONE[root]
    return [SEMITONE_TO_NOTE[(root_semi + i) % 12] for i in intervals]


def get_scale(root: str, scale: str) -> list[str]:
    """获取指定根音和调式的音阶音符列表。

    支持的调式：
        - "major": 大调（自然大调）
        - "natural_minor" 或 "minor": 自然小调

    Args:
        root: 根音名称，如 "C"、"F#"、"Bb"。
        scale: 调式类型。

    Returns:
        音阶中按顺序排列的音符名称列表，共 7 个音。

    Raises:
        ValueError: 不支持的调式类型。
    """
    if root not in NOTE_TO_SEMITONE:
        raise ValueError(f"无效的根音名: {root!r}")
    if scale == "major":
        return _rotate_scale(root, [0, 2, 4, 5, 7, 9, 11])
    if scale in {"natural_minor", "minor"}:
        return _rotate_scale(root, [0, 2, 3, 5, 7, 8, 10])
    raise ValueError(f"不支持的调式: {scale!r}，当前仅支持 'major' 和 'natural_minor'/'minor'")


def parse_chord(chord: str) -> list[str]:
    """解析和弦符号为组成音符列表。

    支持大三和弦（如 "C"）和小三和弦（如 "Am"、"Dm"），返回根音、三音、五音。

    Args:
        chord: 和弦符号，如 "C"、"Dm"、"Bb"、"F#m"。

    Returns:
        和弦组成音符名称列表（3 个元素）。

    Raises:
        ValueError: 和弦符号格式无效。
    """
    if not chord:
        raise ValueError("和弦符号不能为空")
    is_minor = chord.endswith("m")
    root = chord[:-1] if is_minor else chord
    if root not in NOTE_TO_SEMITONE:
        raise ValueError(f"无效的和弦根音: {root!r}")
    root_semi = NOTE_TO_SEMITONE[root]
    # 大三和弦：根音 + 大三度(4) + 纯五度(7)
    # 小三和弦：根音 + 小三度(3) + 纯五度(7)
    third = (root_semi + (3 if is_minor else 4)) % 12
    fifth = (root_semi + 7) % 12
    return [SEMITONE_TO_NOTE[root_semi], SEMITONE_TO_NOTE[third], SEMITONE_TO_NOTE[fifth]]


def chord_to_midi_notes(chord: str, base_octave: int = 3) -> list[int]:
    """将和弦符号转换为 MIDI 音符编号列表。

    将和弦的根音、三音、五音映射到指定八度的 MIDI 编号。

    Args:
        chord: 和弦符号，如 "C"、"Dm"、"Bb"。
        base_octave: 基准八度，默认为 3（C3 = MIDI 48）。

    Returns:
        MIDI 音符编号列表（3 个元素）。
    """
    notes = parse_chord(chord)
    result: list[int] = []
    for n in notes:
        result.append(note_name_to_midi(f"{n}{base_octave}"))
    return result


def is_pitch_in_scale(pitch: int, scale_notes: list[str]) -> bool:
    """检查指定 MIDI 音高是否属于给定音阶。

    将 MIDI 音高取模 12 得到音名类别，再与音阶列表比对。
    例如：pitch=62 (D), scale_notes=["D","E","F#","G","A","B","C#"] → True

    Args:
        pitch: MIDI 音高编号（0-127）。
        scale_notes: 音阶音符名称列表（如 get_scale 的返回值）。

    Returns:
        True 如果音高在音阶内。
    """
    note_name = SEMITONE_TO_NOTE[pitch % 12]
    return note_name in scale_notes