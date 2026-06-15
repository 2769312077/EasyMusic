"""EasyMusic Backend 持久化存储模块。

TaskStore 类：
    基于文件系统的 JSON 持久化存储，使用 threading.Lock 保证线程安全。
    存储结构（以 data_dir 为根）：
        data_dir/
        ├── tasks/
        │   └── {task_id}/
        │       └── task.json          # 单个任务的完整状态
        ├── task_index.json             # 任务索引，按 client_id 分组
        └── quota/
            └── {YYYY-MM-DD}.json      # 每日配额计数，按 client_id 分组
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class TaskStore:
    """基于文件系统的任务持久化存储，线程安全。

    所有公开方法在执行文件 I/O 期间持有线程锁，保证并发安全。

    Usage:
        store = TaskStore(data_dir=Path("data"))
        store.create_task("client_001", task_data)
        tasks = store.list_tasks_by_client("client_001")
    """

    def __init__(self, data_dir: Path) -> None:
        """初始化 TaskStore 并确保目录结构存在。

        Args:
            data_dir: 数据存储根目录的绝对路径。
        """
        self._data_dir = data_dir
        """数据存储根目录"""

        self._tasks_dir = data_dir / "tasks"
        """任务数据目录"""

        self._quota_dir = data_dir / "quota"
        """每日配额数据目录"""

        self._index_path = data_dir / "task_index.json"
        """任务索引文件路径"""

        self._lock = threading.Lock()
        """线程锁，保护所有文件 I/O 操作"""

        # 确保目录结构存在
        self._tasks_dir.mkdir(parents=True, exist_ok=True)
        self._quota_dir.mkdir(parents=True, exist_ok=True)
        if not self._index_path.exists():
            self._index_path.write_text("{}", encoding="utf-8")

    # ------------------------------------------------------------------
    # 任务 CRUD
    # ------------------------------------------------------------------

    def create_task(self, client_id: str, task_data: dict) -> dict:
        """创建新任务并写入持久化存储。

        同时更新任务索引，将 task_id 关联到 client_id。

        Args:
            client_id: 客户端标识（来自 X-EasyMusic-Client-Id 请求头）。
            task_data: 完整的任务数据字典，必须包含 task_id 字段。

        Returns:
            传入的 task_data（可能被补充时间戳等字段）。
        """
        task_id = task_data["task_id"]
        with self._lock:
            # 写入任务文件
            task_dir = self._tasks_dir / task_id
            task_dir.mkdir(parents=True, exist_ok=True)
            task_path = task_dir / "task.json"
            task_path.write_text(
                json.dumps(task_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            # 更新索引
            index = self._load_index()
            index.setdefault(client_id, [])
            if task_id not in index[client_id]:
                index[client_id].append(task_id)
            self._save_index(index)

        return task_data

    def get_task(self, task_id: str) -> Optional[dict]:
        """根据 task_id 获取任务数据。

        Args:
            task_id: 任务唯一标识。

        Returns:
            任务数据字典，不存在时返回 None。
        """
        task_path = self._tasks_dir / task_id / "task.json"
        if not task_path.exists():
            return None
        with self._lock:
            return json.loads(task_path.read_text(encoding="utf-8"))

    def update_task(self, task_id: str, updates: dict) -> Optional[dict]:
        """局部更新任务数据（浅合并）。

        读取现有数据，与 updates 字典合并后写回文件。

        Args:
            task_id: 任务唯一标识。
            updates: 要合并的更新字段字典。

        Returns:
            更新后的完整任务数据，任务不存在时返回 None。
        """
        task_path = self._tasks_dir / task_id / "task.json"
        if not task_path.exists():
            return None
        with self._lock:
            current = json.loads(task_path.read_text(encoding="utf-8"))
            current.update(updates)
            current["updated_at"] = datetime.now(timezone.utc).isoformat()
            task_path.write_text(
                json.dumps(current, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return current

    def _overwrite_task(self, task_id: str, task_data: dict) -> None:
        """完全覆写任务数据（内部方法，调用方需自行持有锁）。

        Args:
            task_id: 任务唯一标识。
            task_data: 完整的任务数据字典。
        """
        task_path = self._tasks_dir / task_id / "task.json"
        task_path.write_text(
            json.dumps(task_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_tasks_by_client(self, client_id: str) -> list[dict]:
        """列出指定客户端的所有任务（按创建时间倒序）。

        Args:
            client_id: 客户端标识。

        Returns:
            任务数据字典列表，按创建时间倒序排列。
        """
        with self._lock:
            index = self._load_index()
            task_ids = index.get(client_id, [])
            tasks: list[dict] = []
            for tid in task_ids:
                task_path = self._tasks_dir / tid / "task.json"
                if task_path.exists():
                    tasks.append(json.loads(task_path.read_text(encoding="utf-8")))
            # 按创建时间倒序
            tasks.sort(key=lambda t: t.get("created_at", ""), reverse=True)
            return tasks

    # ------------------------------------------------------------------
    # 配额管理
    # ------------------------------------------------------------------

    def get_quota(self, client_id: str) -> int:
        """获取指定客户端今日已使用的配额数。

        Args:
            client_id: 客户端标识。

        Returns:
            今日已使用配额数。
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        quota_path = self._quota_dir / f"{today}.json"
        with self._lock:
            if not quota_path.exists():
                return 0
            data = json.loads(quota_path.read_text(encoding="utf-8"))
            return data.get(client_id, 0)

    def increment_quota(self, client_id: str) -> int:
        """递增指定客户端今日配额计数并返回新值。

        Args:
            client_id: 客户端标识。

        Returns:
            递增后的今日配额使用数。
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        quota_path = self._quota_dir / f"{today}.json"
        with self._lock:
            if quota_path.exists():
                data = json.loads(quota_path.read_text(encoding="utf-8"))
            else:
                data = {}
            data[client_id] = data.get(client_id, 0) + 1
            quota_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return data[client_id]

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _load_index(self) -> dict:
        """加载任务索引文件。

        Returns:
            任务索引字典 {client_id: [task_id, ...]}。
        """
        if self._index_path.exists():
            return json.loads(self._index_path.read_text(encoding="utf-8"))
        return {}

    def _save_index(self, index: dict) -> None:
        """保存任务索引文件。

        Args:
            index: 任务索引字典。
        """
        self._index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )