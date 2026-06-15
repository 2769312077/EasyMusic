"""LLM 客户端模块。

封装对 OpenAI 兼容 API 的调用，负责发送提示词并解析返回的结构化 JSON。

参考 ToMidi 项目的设计：每次调用创建新的 OpenAI 客户端实例，
避免单例模式下 httpx 连接池中的陈旧连接导致请求挂起。
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from dotenv import load_dotenv

from easymusic.core.exceptions import ConfigError, LLMError, LLMResponseError

load_dotenv()


# ---------------------------------------------------------------------------
# 错误信息提取
# ---------------------------------------------------------------------------
def _extract_error_detail(exc: Exception) -> str:
    """从 LLM 异常中提取详细诊断信息。

    对 OpenAI SDK 返回的异常进行反射式检查，提取 status_code、
    request_id、response body 等调试信息。

    Args:
        exc: LLM API 调用抛出的异常对象。

    Returns:
        JSON 格式的详细错误信息字符串。
    """
    details: dict[str, Any] = {
        "type": exc.__class__.__name__,
        "message": str(exc),
    }

    # 提取顶层属性
    for attr in ("status_code", "request_id", "code", "param"):
        value = getattr(exc, attr, None)
        if value is not None:
            details[attr] = value

    # 提取响应对象
    response = getattr(exc, "response", None)
    if response is not None:
        details["response_status_code"] = getattr(response, "status_code", None)

        response_text = None
        try:
            response_text = response.text
        except Exception:
            response_text = None
        if response_text:
            details["response_text"] = response_text

        try:
            response_json = response.json()
        except Exception:
            response_json = None
        if response_json is not None:
            details["response_json"] = response_json

    # 提取请求体
    body = getattr(exc, "body", None)
    if body is not None:
        details["body"] = body

    return json.dumps(details, ensure_ascii=False)


# ---------------------------------------------------------------------------
# JSON 提取与解析
# ---------------------------------------------------------------------------
def _extract_json(content: str) -> dict[str, Any]:
    """从 LLM 返回的文本中提取有效的 JSON 对象。

    LLM 的返回格式不稳定，可能包含 markdown 代码块、解释文本等。
    本函数使用三级容错策略按顺序尝试提取有效的 JSON：

    策略 1: 直接解析整个响应（最理想的情况）
    策略 2: 提取 ```json ... ``` 代码块内容
    策略 3: 使用括号深度匹配提取第一个 { ... } 对象

    Args:
        content: LLM 返回的原始文本内容。

    Returns:
        解析后的 JSON 字典。

    Raises:
        LLMResponseError: 所有提取策略均失败。
    """
    if not content or not content.strip():
        raise LLMResponseError("LLM 返回空内容")

    # 策略 1: 直接解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 策略 2: 提取 ```json ... ``` 代码块
    match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 策略 3: 括号深度匹配提取第一个完整 JSON 对象
    depth = 0
    start = content.find("{")
    if start >= 0:
        for i, ch in enumerate(content[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(content[start : i + 1])
                    except json.JSONDecodeError:
                        break

    raise LLMResponseError(
        f"无法从 LLM 响应中提取有效 JSON。响应前 200 字符: {content[:200]!r}"
    )


# ---------------------------------------------------------------------------
# 核心 API
# ---------------------------------------------------------------------------
def _sanitize_base_url(url: str) -> str:
    """清理 Base URL，移除路径末尾多余的 /chat/completions 后缀。

    OpenAI SDK 会自动在 base_url 后追加 /chat/completions，
    如果用户提供的 base_url 已包含该后缀，会导致请求路径变为
    /v1/chat/completions/chat/completions。

    使用循环处理可能的多层重复后缀。

    Args:
        url: 用户提供的原始 Base URL。

    Returns:
        清理后的 Base URL。
    """
    url = url.rstrip("/")
    while url.endswith("/chat/completions"):
        url = url[: -len("/chat/completions")]
    return url


def llm_json(prompt: str) -> dict[str, Any]:
    """调用 LLM 获取结构化 JSON 响应。

    每次调用创建新的 OpenAI 客户端实例，避免单例模式下
    httpx 连接池陈旧连接导致的请求挂起问题。

    支持三种提供商模式：
        - gpt / deepseek: 需要有效的 OPENAI_API_KEY
        - lmstudio:    使用本地服务；若未提供 API Key 则不发送
                        认证头（适用于 LM Studio 默认关闭认证的场景），
                        若提供了 API Key 则作为 Bearer Token 发送

    使用参数：
        - Provider: 从 LLM_PROVIDER 环境变量读取（默认兼容旧行为）
        - API Key: 从 OPENAI_API_KEY 环境变量读取
        - Base URL: 从 OPENAI_BASE_URL 环境变量读取（默认 DeepSeek）
        - Model: 从 OPENAI_MODEL 环境变量读取（默认 deepseek-chat）
        - Temperature: 固定 0.2（保留适度创造性同时确保结构化输出）
        - Timeout: 180 秒，避免请求无限期挂起

    Args:
        prompt: 发送给 LLM 的完整提示词字符串。

    Returns:
        解析后的 JSON 字典。

    Raises:
        ConfigError: API Key 未配置（远程模型）或 SDK 未安装。
        LLMError: API 请求失败（网络错误、鉴权失败、速率限制等）。
        LLMResponseError: 返回内容无法解析为有效 JSON。
    """
    provider = os.getenv("LLM_PROVIDER", "").lower()
    api_key = os.getenv("OPENAI_API_KEY")
    is_lm_studio = provider == "lmstudio"

    if is_lm_studio:
        pass
    elif not api_key:
        raise ConfigError(
            "OPENAI_API_KEY 未设置。请设置环境变量或在 .env 文件中配置。"
        )

    try:
        from openai import OpenAI
    except ImportError as e:
        raise ConfigError("openai SDK 未安装，请执行 pip install openai") from e

    model = os.getenv("OPENAI_MODEL", "deepseek-chat")
    base_url = _sanitize_base_url(os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1"))
    if is_lm_studio and not base_url.endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"

    _lm_studio_timeout = 600.0 if is_lm_studio else 180.0

    if is_lm_studio and not api_key:
        import httpx

        def _strip_auth(request: httpx.Request) -> None:
            request.headers.pop("authorization", None)
            request.headers.pop("Authorization", None)

        http_client = httpx.Client(event_hooks={"request": [_strip_auth]})
        client = OpenAI(
            api_key="lm-studio",
            base_url=base_url,
            http_client=http_client,
            timeout=_lm_studio_timeout,
            max_retries=0,
        )
    else:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=_lm_studio_timeout, max_retries=1)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict JSON generator. Return JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
    except Exception as e:
        raise LLMError(
            f"LLM 请求失败: {_extract_error_detail(e)}",
            model=model,
        ) from e

    content = resp.choices[0].message.content
    if not content:
        raise LLMResponseError("LLM 返回空内容")
    return _extract_json(content)


def llm_text(prompt: str) -> str:
    """调用 LLM 获取原始文本响应。

    与 llm_json 使用相同的客户端配置，但不进行 JSON 解析，
    直接返回 LLM 的原始文本输出。用于 CSV 等非 JSON 格式的输出场景。

    Args:
        prompt: 发送给 LLM 的完整提示词字符串。

    Returns:
        LLM 返回的原始文本内容。

    Raises:
        ConfigError: API Key 未配置（远程模型）或 SDK 未安装。
        LLMError: API 请求失败。
        LLMResponseError: 返回内容为空。
    """
    provider = os.getenv("LLM_PROVIDER", "").lower()
    api_key = os.getenv("OPENAI_API_KEY")
    is_lm_studio = provider == "lmstudio"

    if is_lm_studio:
        pass
    elif not api_key:
        raise ConfigError(
            "OPENAI_API_KEY 未设置。请设置环境变量或在 .env 文件中配置。"
        )

    try:
        from openai import OpenAI
    except ImportError as e:
        raise ConfigError("openai SDK 未安装，请执行 pip install openai") from e

    model = os.getenv("OPENAI_MODEL", "deepseek-chat")
    base_url = _sanitize_base_url(os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1"))
    if is_lm_studio and not base_url.endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"

    _lm_studio_timeout = 600.0 if is_lm_studio else 180.0

    if is_lm_studio and not api_key:
        import httpx

        def _strip_auth(request: httpx.Request) -> None:
            request.headers.pop("authorization", None)
            request.headers.pop("Authorization", None)

        http_client = httpx.Client(event_hooks={"request": [_strip_auth]})
        client = OpenAI(
            api_key="lm-studio",
            base_url=base_url,
            http_client=http_client,
            timeout=_lm_studio_timeout,
            max_retries=0,
        )
    else:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=_lm_studio_timeout, max_retries=1)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict music data generator. Return data only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
    except Exception as e:
        raise LLMError(
            f"LLM 请求失败: {_extract_error_detail(e)}",
            model=model,
        ) from e

    content = resp.choices[0].message.content
    if not content:
        raise LLMResponseError("LLM 返回空内容")
    return content