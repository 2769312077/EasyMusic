"""编配规划 Agent。

根据意图和歌曲计划，规划乐器编配：轨道配置、MIDI 通道、混音参数、生成策略等。
这是管线的第三阶段，将音乐创意转化为具体的乐器配置方案。
"""

from __future__ import annotations

from easymusic.agents.client import llm_json
from easymusic.prompts import build_arrangement_planner_prompt


def plan_arrangement(
    intent_result: dict,
    song_plan: dict,
    enforce_core_tracks: bool = True,
) -> dict:
    """根据意图和歌曲计划规划乐器编配。

    确定需要哪些乐器轨道、每条轨道的 MIDI 通道（0-15）、GM 音色编号、
    混音参数（音量/声像）、段落密度配置和生成策略。

    关键约束：
        - 鼓轨必须使用通道 9（GM 打击乐专用通道）
        - 非鼓轨不得占用通道 9
        - 音色编号使用 0-based（GM 1-128 → 0-127）
        - 每条轨道都需指定各段落的密度等级（low/medium/high/off）

    Args:
        intent_result: parse_intent 的输出结果。
        song_plan: plan_song 的输出结果。
        enforce_core_tracks: 是否强制包含核心轨道。

    Returns:
        编配结果字典，包含 "arrangement" → "tracks" 的轨道配置。
            每条轨道包含:
            - id, name, role: 标识和角色
            - enabled, is_core_track: 状态标识
            - generation_strategy: 生成策略（drum_generator/bass_generator/...）
            - midi: channel 和 program 配置
            - mix: volume 和 pan 设置
            - style: 乐器风格参数
            - sections: 各段落密度和数据

    Raises:
        LLMError: API 调用失败。
        LLMResponseError: JSON 解析失败。
    """
    prompt = build_arrangement_planner_prompt(
        intent_result["intent"],
        song_plan["song_plan"],
        enforce_core_tracks=enforce_core_tracks,
    )
    data = llm_json(prompt)
    data.setdefault("_meta", {})
    data["_meta"]["source"] = "llm"
    return data