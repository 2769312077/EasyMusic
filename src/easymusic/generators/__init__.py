"""规则生成器层的公开接口。

四个生成器分别对应四种核心音乐角色：
    - drum_generator: 鼓组（节奏骨架）
    - bass_generator: 贝斯（和声基础）
    - chord_generator: 和弦伴奏（和声呈现）
    - lead_generator: 主旋律（记忆点）

当 note_generation_mode 设为 "rule" 时，管线将使用这些生成器
替代 LLM 来生成音符事件。
"""

from easymusic.generators.bass import generate_bass
from easymusic.generators.chord import generate_chords
from easymusic.generators.drum import generate_drums
from easymusic.generators.lead import generate_lead

__all__ = [
    "generate_drums",
    "generate_bass",
    "generate_chords",
    "generate_lead",
]