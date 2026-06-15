"""知识文件缓存加载器。

提供对 knowledge/ 目录下 Markdown 知识库文件的高效加载。
采用 functools.lru_cache 实现模块级别的缓存，避免每次构建提示词
时都从磁盘重复读取文件内容。

三份知识文件：
    - instruments.md: GM 乐器音色参考（约 7KB）
    - chords.md: 和弦进行选择知识（约 20KB）
    - notes.md: 音符与节奏生成知识（约 11KB）
"""

from __future__ import annotations

import functools
from pathlib import Path

# 知识文件目录：相对于 prompts/ 模块的上级目录
_KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"


@functools.lru_cache(maxsize=3)
def _load_knowledge(filename: str) -> str:
    """从知识目录加载指定文件的内容（带缓存）。

    首次加载后，后续调用将直接从 LRU 缓存中返回，无需再次读取磁盘。

    Args:
        filename: 知识文件名（如 "instruments.md"）。

    Returns:
        文件内容的字符串，文件不存在时返回空字符串。
    """
    knowledge_path = _KNOWLEDGE_DIR / filename
    try:
        return knowledge_path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def load_instrument_knowledge() -> str:
    """加载 GM 乐器音色参考知识库。"""
    return _load_knowledge("instruments.md")


def load_chord_knowledge() -> str:
    """加载和弦进行选择知识库。"""
    return _load_knowledge("chords.md")


def load_note_knowledge() -> str:
    """加载音符与节奏生成知识库。"""
    return _load_knowledge("notes.md")


def get_knowledge_dir() -> Path:
    """返回知识库目录的绝对路径。

    用于需要直接访问知识文件的场景。

    Returns:
        knowledge/ 目录的 Path 对象。
    """
    return _KNOWLEDGE_DIR