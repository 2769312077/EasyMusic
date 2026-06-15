"""意图解析 Agent。

将用户的自然语言提示词解析为结构化的音乐意图描述。
这是 MIDI 生成管线的第一阶段，后续所有阶段都基于此输出。
"""

from __future__ import annotations

from easymusic.agents.client import llm_json
from easymusic.prompts import build_intent_parser_prompt


def parse_intent(
    user_prompt: str,
    enforce_core_tracks: bool = True,
    max_duration_seconds: int | None = None,
) -> dict:
    """解析用户的自然语言提示词为结构化音乐意图。

    调用 LLM 分析用户描述，提取风格、情绪、使用场景、速度倾向、
    轨道需求等结构化信息。

    Args:
        user_prompt: 用户的自然语言音乐描述。
            示例: "Generate a dark cyberpunk battle BGM at 140 BPM"
        enforce_core_tracks: 是否强制要求核心四轨（drums/bass/chords/lead）。
            LLM 音符生成模式下为 False（允许更自由的编配），
            规则生成模式下为 True（确保四个生成器都有对应轨道）。
        max_duration_seconds: 最大时长限制（秒）。
            None 表示不限制，由 LLM 自行决定。

    Returns:
        结构化意图字典，包含：
            - task_type: 任务类型
            - user_prompt: 原始输入
            - intent: 解析后的意图详情
                - style: 风格列表
                - mood: 情绪列表
                - use_case: 使用场景
                - duration_seconds: 时长
                - loopable: 是否可循环
                - complexity: 复杂度
                - requested_tracks: 轨道需求
                - tempo_preference: 速度倾向
                - must_have: 必须包含元素
                - avoid: 避免元素
            - _meta: 元数据（标注数据来源）

    Raises:
        LLMError: API 调用失败。
        LLMResponseError: JSON 解析失败。
        ValueError: 返回 JSON 结构无效（缺少 nested 'intent' 对象）。
    """
    # 构建专门化提示词
    prompt = build_intent_parser_prompt(
        user_prompt,
        enforce_core_tracks=enforce_core_tracks,
        max_duration_seconds=max_duration_seconds,
    )

    # 调用 LLM 获取结构化结果
    data = llm_json(prompt)

    # 校验必须的嵌套结构
    if "intent" not in data or not isinstance(data["intent"], dict):
        raise ValueError("意图解析返回的 JSON 结构无效：缺少嵌套的 'intent' 对象")

    # 标注数据来源
    data.setdefault("_meta", {})
    data["_meta"]["source"] = "llm"

    return data