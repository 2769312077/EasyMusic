"""EasyMusic Backend 全局运行时管理模块。

GlobalRuntime 类：
    单例模式，管理全局运行时状态。
    - 跟踪当前运行的任务（单任务锁）
    - 提供 progress_callback 供管线阶段和轨道生成回调
    - 管理任务状态机：pending → running → succeeded / failed

线程安全：内部使用 threading.Lock 保护状态读写。
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from easymusic.backend.store import TaskStore


class GlobalRuntime:
    """全局运行时管理器（单例模式）。

    维护当前任务的运行状态，并提供 progress_callback
    将管线的阶段进度实时同步回 TaskStore。

    Usage:
        runtime = GlobalRuntime(store=task_store)
        runtime.start_task("task_001", "my_project")
        # ... 管线运行中 ...
        runtime.finish_task("task_001", final_output)
    """

    _instance: Optional[GlobalRuntime] = None
    """单例实例"""

    _instance_lock = threading.Lock()
    """单例创建锁"""

    def __init__(self, store: TaskStore) -> None:
        """初始化 GlobalRuntime。

        Args:
            store: TaskStore 实例，用于持久化任务状态。
        """
        self._store = store
        """任务持久化存储"""

        self._lock = threading.Lock()
        """状态读写锁"""

        self._current_task_id: Optional[str] = None
        """当前正在运行的任务 ID（无任务时为 None）"""

        self._current_project_name: Optional[str] = None
        """当前运行任务的项目名称"""

        self._single_active_task: bool = True
        """是否启用全局单任务模式"""

    def configure(self, *, single_active_task: bool) -> None:
        """配置运行时参数。

        Args:
            single_active_task: 是否启用全局单任务模式。
        """
        self._single_active_task = single_active_task

    # ------------------------------------------------------------------
    # 任务生命周期管理
    # ------------------------------------------------------------------

    def start_task(self, task_id: str, project_name: str) -> None:
        """标记任务开始运行，状态从 pending 切换到 running。

        如果启用了单任务模式且已有任务在运行，将抛出 RuntimeError。

        Args:
            task_id: 任务唯一标识。
            project_name: 项目名称。

        Raises:
            RuntimeError: 单任务模式下已有任务在运行。
        """
        with self._lock:
            if self._single_active_task and self._current_task_id is not None:
                raise RuntimeError(
                    f"全局单任务模式已启用，当前任务 {self._current_task_id} 正在运行，无法启动新任务"
                )
            self._current_task_id = task_id
            self._current_project_name = project_name

        # 更新任务状态为 running
        self._store.update_task(task_id, {"status": "running"})

    def finish_task(self, task_id: str, final_output: dict) -> None:
        """标记任务成功完成。

        更新任务状态为 succeeded，写入最终产物信息，
        并清除当前运行状态。

        Args:
            task_id: 任务唯一标识。
            final_output: 管线返回的最终产物字典。
        """
        with self._lock:
            if self._current_task_id == task_id:
                self._current_task_id = None
                self._current_project_name = None

        self._store.update_task(
            task_id,
            {
                "status": "succeeded",
                "final_output": final_output,
            },
        )

    def fail_task(self, task_id: str, error_message: str) -> None:
        """标记任务失败。

        更新任务状态为 failed，写入错误信息，
        并清除当前运行状态。

        Args:
            task_id: 任务唯一标识。
            error_message: 错误描述信息。
        """
        with self._lock:
            if self._current_task_id == task_id:
                self._current_task_id = None
                self._current_project_name = None

        self._store.update_task(
            task_id,
            {
                "status": "failed",
                "error": error_message,
            },
        )

    # ------------------------------------------------------------------
    # 进度回调
    # ------------------------------------------------------------------

    def make_progress_callback(self) -> Callable[[dict], None]:
        """创建进度回调闭包，供 generate_music 管线使用。

        回调函数接收管线各阶段的状态更新，
        实时同步到 TaskStore 中对应任务的 stages 字段。

        Returns:
            进度回调函数，签名为 (progress: dict) -> None。
        """

        def _on_progress(progress: dict) -> None:
            """管线进度回调：将阶段/轨道进度写入任务数据。

            progress 字典的典型结构：
                - stage 类型: {"type": "stage", "stage_index": N,
                               "stage_total": T, "stage_name": "...", "status": "..."}
                - track 类型: {"type": "track", ...}
            """
            task_id = self._current_task_id
            if task_id is None:
                return

            # 读取当前任务数据，追加 stages 条目
            task = self._store.get_task(task_id)
            if task is None:
                return

            stages: list[dict] = task.get("stages", [])
            stages.append(progress)
            updates: dict[str, Any] = {"stages": stages}

            # 同步当前阶段信息到顶层字段（便于前端快速展示）
            if progress.get("type") == "stage":
                updates["stage_index"] = progress.get("stage_index")
                updates["stage_total"] = progress.get("stage_total")
                updates["stage_name"] = progress.get("stage_name")
            elif progress.get("type") in ("track", "track_progress"):
                updates["track_progress"] = progress

            self._store.update_task(task_id, updates)

        return _on_progress

    # ------------------------------------------------------------------
    # 状态查询
    # ------------------------------------------------------------------

    def is_task_running(self) -> bool:
        """检查当前是否有任务正在运行。

        Returns:
            True 表示有任务正在运行。
        """
        with self._lock:
            return self._current_task_id is not None

    def get_runtime_status(self) -> dict:
        """获取全局运行时状态快照。

        Returns:
            包含当前任务信息和单任务模式的字典。
        """
        with self._lock:
            return {
                "current_task_id": self._current_task_id,
                "current_project_name": self._current_project_name,
                "single_active_task": self._single_active_task,
            }

    def get_current_task_id(self) -> Optional[str]:
        """获取当前运行中的任务 ID。

        Returns:
            当前任务 ID，无任务时为 None。
        """
        with self._lock:
            return self._current_task_id