"""管线 Checkpoint 管理模块。

负责生成管线的阶段结果保存与恢复（断点续运行支持）。

Checkpoint 机制：
    - 每个管线的阶段结果都保存为独立的 JSON 文件
    - 文件命名遵循 "{stage_index:02d}_{stage_name}.json" 格式
    - 支持 resume 模式从任意阶段恢复执行
    - 最终管线结果保存为 pipeline_result.json
"""

from __future__ import annotations

import json
import uuid
from datetime import date
from pathlib import Path


def project_dir(project_name: str, base_dir: str | Path = "outputs") -> Path:
    """生成项目输出目录路径。

    格式: {base_dir}/{safe_name}_{YYYYMMDD}

    项目名中的非安全字符会被替换为下划线，避免文件系统问题。

    Args:
        project_name: 项目名称（用户提供）。
        base_dir: 输出基准目录。

    Returns:
        项目输出目录的 Path 对象。
    """
    safe_name = "".join(
        ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in project_name
    ).strip("_")
    if not safe_name:
        safe_name = "untitled"
    today = date.today().strftime("%Y%m%d")
    return Path(base_dir) / f"{safe_name}_{today}"


def generate_project_id() -> str:
    """生成 8 位十六进制项目 ID。

    Returns:
        8 字符的 UUID 前缀字符串。
    """
    return uuid.uuid4().hex[:8]


def save_stage(stage_path: Path, payload: dict) -> None:
    """将阶段结果序列化为 JSON checkpoint 文件。

    自动创建不存在的父目录。

    Args:
        stage_path: 目标文件路径。
        payload: 要保存的数据字典。
    """
    stage_path.parent.mkdir(parents=True, exist_ok=True)
    stage_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_stage(stage_path: Path) -> dict:
    """从 JSON checkpoint 文件恢复阶段结果。

    Args:
        stage_path: checkpoint 文件路径。

    Returns:
        恢复的数据字典。

    Raises:
        FileNotFoundError: checkpoint 文件不存在。
    """
    if not stage_path.exists():
        raise FileNotFoundError(f"缺失 checkpoint 文件: {stage_path}")
    return json.loads(stage_path.read_text(encoding="utf-8"))