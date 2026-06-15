"""提示词模板包的公开接口。

集中导出各阶段的提示词构建函数，外部只需导入此包即可使用所有模板。
"""

from easymusic.prompts.templates import (
    build_arrangement_planner_prompt,
    build_intent_parser_prompt,
    build_song_planner_prompt,
    build_track_note_generator_prompt,
)

__all__ = [
    "build_intent_parser_prompt",
    "build_song_planner_prompt",
    "build_arrangement_planner_prompt",
    "build_track_note_generator_prompt",
]