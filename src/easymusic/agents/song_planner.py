"""歌曲规划 Agent。

根据解析后的意图规划歌曲结构：BPM、拍号、调性、段落划分、和弦进行等。
这是管线的第二阶段，为后续编配和音符生成提供完整的音乐框架。
"""

from __future__ import annotations

from easymusic.agents.client import llm_json
from easymusic.prompts import build_song_planner_prompt


def plan_song(intent_result: dict) -> dict:
    """根据意图规划歌曲结构。

    基于 LLM 对意图的分析，规划歌曲的基本参数和结构框架。

    规划内容包括：
        - title: 歌曲标题
        - bpm: 速度（每分钟拍数）
        - time_signature: 拍号（MVP 为 4/4）
        - key: 调性（如 D minor）
        - total_bars: 总小节数（8/12/16/24/32）
        - sections: 段落划分（intro/main_a/main_b/ending）
        - chord_progression: 和弦进行（每小节的根音和弦）

    使用注入的和弦知识库确保和弦进行在风格上合理、和声上规范。

    Args:
        intent_result: parse_intent 的输出结果字典。
            需要包含 "intent" 键，内含风格、情绪、使用场景等信息。

    Returns:
        歌曲计划字典，包含 "song_plan" 键和所有规划字段。

    Raises:
        LLMError: API 调用失败。
        LLMResponseError: JSON 解析失败。
    """
    prompt = build_song_planner_prompt(intent_result["intent"])
    data = llm_json(prompt)
    data.setdefault("_meta", {})
    data["_meta"]["source"] = "llm"
    return data