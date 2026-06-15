"""专用异常类定义。

替换原有代码中大量裸 RuntimeError 的抛出，使上层可按异常类型精准捕获和处理。
所有自定义异常均继承自 EasyMusicError 基类。
"""

from __future__ import annotations


class EasyMusicError(Exception):
    """EasyMusic 框架所有异常的基类。

    所有自定义异常都应继承此类，便于上层统一捕获框架相关异常。
    """


class LLMError(EasyMusicError):
    """LLM API 调用失败异常。

    当 OpenAI 兼容 API 的请求失败、返回空内容或 JSON 解析失败时抛出。

    Attributes:
        status_code: HTTP 状态码（如有）。
        model: 使用的模型名称（如有）。
    """

    def __init__(self, message: str, status_code: int | None = None, model: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.model = model


class LLMResponseError(EasyMusicError):
    """LLM 返回内容无法解析为有效 JSON 时抛出的异常。

    与 LLMError 的区别在于：API 调用本身成功，但返回内容格式不符合预期。
    """


class ValidationError(EasyMusicError):
    """MIDI 数据校验失败异常。

    在校验阶段发现 BPM 越界、轨道缺失、音符范围非法等问题时抛出。

    Attributes:
        errors: 具体的错误信息列表。
    """

    def __init__(self, message: str, errors: list[str]) -> None:
        super().__init__(message)
        self.errors = errors


class ConfigError(EasyMusicError):
    """配置加载失败异常。

    当必需的配置项缺失（如 API Key 未设置）或配置值非法时抛出。
    """


class AudioRenderError(EasyMusicError):
    """音频渲染失败异常。

    在 MIDI 转 WAV（fluidsynth）或 WAV 转 MP3（ffmpeg）过程中失败时抛出。
    """


class PipelineError(EasyMusicError):
    """管线执行异常。

    当生成管线的某个阶段发生不可恢复的错误时抛出。
    """