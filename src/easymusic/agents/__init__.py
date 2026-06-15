"""Agent 层的公开接口。

Agent 层负责与 LLM 交互，将自然语言提示词逐步转换为结构化的音乐数据。
四个 Agent 对应管线的四个规划阶段：

    parse_intent → plan_song → plan_arrangement → generate_notes
"""

from easymusic.agents.arrangement_planner import plan_arrangement
from easymusic.agents.intent_parser import parse_intent
from easymusic.agents.note_generator import generate_notes
from easymusic.agents.song_planner import plan_song

__all__ = [
    "parse_intent",
    "plan_song",
    "plan_arrangement",
    "generate_notes",
]