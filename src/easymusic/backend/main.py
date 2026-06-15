"""EasyMusic Backend FastAPI 服务主体。

提供 RESTful API 供前端调用，包括：
    - 健康检查
    - 全局运行时状态查询
    - 任务 CRUD（创建、列表、详情、重试）
    - 产物文件下载（MIDI / WAV / MP3）

客户端识别：
    通过 X-EasyMusic-Client-Id 请求头区分不同客户端。
    若未提供该请求头，默认使用 "anonymous" 作为 client_id。

生成任务执行：
    使用 threading.Thread 在后台运行 generate_music 管线，
    避免阻塞 FastAPI 事件循环。
"""

from __future__ import annotations

import os
import threading
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from easymusic._version import __version__
from easymusic.backend.config import AppConfig, config as _cfg_singleton
from easymusic.backend.models import (
    CreateTaskRequest,
    HealthResponse,
    RuntimeResponse,
    TaskResponse,
)
from easymusic.backend.runner import GlobalRuntime
from easymusic.backend.store import TaskStore
from easymusic.pipeline.orchestrator import generate_music

# =========================================================================
# 模块级全局变量
# =========================================================================

_app_config: Optional[AppConfig] = None
"""应用配置实例（在 startup 事件中初始化）"""

_store: Optional[TaskStore] = None
"""任务持久化存储实例"""

_runtime: Optional[GlobalRuntime] = None
"""全局运行时管理器实例"""

_outputs_base_dir: Optional[str] = None
"""项目根目录下的 outputs 目录绝对路径"""

# =========================================================================
# FastAPI 应用创建
# =========================================================================

app = FastAPI(
    title="EasyMusic Backend",
    version=__version__,
    description="基于 LLM 的 prompt-to-MIDI 音乐生成后端服务",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================================
# 依赖注入
# =========================================================================


def _get_client_id(x_easymusic_client_id: Optional[str] = Header(None, alias="X-EasyMusic-Client-Id")) -> str:
    """从请求头提取客户端标识。

    若客户端未提供 X-EasyMusic-Client-Id 请求头，
    则回退使用 "anonymous" 作为默认标识。

    Args:
        x_easymusic_client_id: 客户端标识请求头值。

    Returns:
        客户端标识字符串。
    """
    return x_easymusic_client_id or "anonymous"


# =========================================================================
# 后台任务执行器
# =========================================================================


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


def _run_generate_task(task_id: str, client_id: str, request: CreateTaskRequest) -> None:
    """在后台线程中执行 generate_music 管线。

    管线完成后通过 GlobalRuntime 更新任务状态。
    发生异常时自动标记任务为 failed 并记录错误信息。

    Args:
        task_id: 任务唯一标识。
        client_id: 客户端标识。
        request: 创建任务时的请求体。
    """
    cfg = _app_config
    runtime = _runtime
    store = _store

    if cfg is None or runtime is None or store is None:
        return

    md = cfg.music_defaults
    rt = cfg.runtime

    # 确定生成参数（请求参数优先，回退到配置默认值）
    project_name = request.project_name or f"{md.project_name_prefix}_{task_id[:8]}"
    note_mode = request.note_mode or md.note_mode
    out_of_bounds_mode = request.out_of_bounds_mode or md.out_of_bounds_mode

    llm_provider = (request.llm_provider or "").lower()
    llm_api_key = request.llm_api_key

    os.environ["LLM_PROVIDER"] = llm_provider

    if llm_provider == "lmstudio":
        os.environ.pop("OPENAI_API_KEY", None)
        if llm_api_key:
            os.environ["OPENAI_API_KEY"] = llm_api_key
        if request.llm_base_url:
            sanitized = _sanitize_base_url(request.llm_base_url)
            if not sanitized.endswith("/v1"):
                sanitized = sanitized.rstrip("/") + "/v1"
            os.environ["OPENAI_BASE_URL"] = sanitized
        if request.llm_model:
            os.environ["OPENAI_MODEL"] = request.llm_model
    elif llm_api_key:
        os.environ["OPENAI_API_KEY"] = llm_api_key
        if request.llm_base_url:
            os.environ["OPENAI_BASE_URL"] = _sanitize_base_url(request.llm_base_url)
        if request.llm_model:
            os.environ["OPENAI_MODEL"] = request.llm_model

    try:
        runtime.start_task(task_id, project_name)

        # 调用核心管线，传入进度回调和输出基准目录
        result = generate_music(
            user_prompt=request.prompt,
            project_name=project_name,
            project_id=task_id[:8],
            resume=False,
            soundfont_path=md.soundfont_path,
            mp3_bitrate=md.mp3_bitrate,
            note_generation_mode=note_mode,
            out_of_bounds_mode=out_of_bounds_mode,
            progress_callback=runtime.make_progress_callback(),
            base_output_dir=_outputs_base_dir,
        )

        # 检查管线是否返回错误
        if result.get("success") is False:
            error_msg = result.get("error", {}).get("message", "未知管线错误")
            runtime.fail_task(task_id, error_msg)
            return

        # 提取最终产物信息
        final_output = result.get("final_output", {})
        runtime.finish_task(task_id, final_output)

    except Exception as exc:
        error_message = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
        try:
            runtime.fail_task(task_id, error_message)
        except Exception:
            pass


# =========================================================================
# 生命周期事件
# =========================================================================


@app.on_event("startup")
def _on_startup() -> None:
    """FastAPI 启动事件：加载配置、初始化存储和运行时。

    此函数在 uvicorn 启动时自动执行。
    将工作目录切换到 backend 模块所在目录，
    确保相对路径（data/、outputs/）正确解析。
    """
    global _app_config, _store, _runtime, _outputs_base_dir

    # 确定 backend 模块所在目录
    backend_dir = Path(__file__).resolve().parent

    # 切换工作目录到 backend 目录
    os.chdir(str(backend_dir))

    # 加载配置（config.yaml 与 main.py 在同一目录）
    config_path = backend_dir / "config.yaml"
    _app_config = AppConfig.load(str(config_path))

    # 解析数据目录为绝对路径
    data_dir = (backend_dir / _app_config.runtime.data_dir).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    # 初始化 TaskStore
    _store = TaskStore(data_dir=data_dir)

    # 初始化 GlobalRuntime 并配置
    _runtime = GlobalRuntime(store=_store)
    _runtime.configure(
        single_active_task=_app_config.runtime.global_single_active_task,
    )

    # 确保输出目录存在（backend 同级的 outputs）
    outputs_dir = backend_dir / _app_config.runtime.outputs_dir
    outputs_dir.mkdir(parents=True, exist_ok=True)

    # 计算项目根目录下的 outputs 目录（供 orchestrator 使用）
    project_root = backend_dir.parent.parent.parent
    _outputs_base_dir = str((project_root / "outputs").resolve())
    os.makedirs(_outputs_base_dir, exist_ok=True)

    # 注入配置到模块单例（供其他模块引用）
    import easymusic.backend.config as config_module
    config_module.config = _app_config

    print(f"[EasyMusic Backend] v{__version__} 已启动")
    print(f"  监听地址: {_app_config.app.host}:{_app_config.app.port}")
    print(f"  数据目录: {data_dir}")
    print(f"  输出目录: {_outputs_base_dir}")
    print(f"  单任务模式: {_app_config.runtime.global_single_active_task}")


# =========================================================================
# API 端点
# =========================================================================


@app.get("/api/health", response_model=HealthResponse)
def api_health() -> HealthResponse:
    """健康检查接口。

    用于负载均衡器探活和监控系统检测服务状态。

    Returns:
        HealthResponse: 包含服务状态和版本号。
    """
    return HealthResponse(status="ok", version=__version__)


@app.get("/api/runtime", response_model=RuntimeResponse)
def api_runtime(client_id: str = Depends(_get_client_id)) -> RuntimeResponse:
    """全局运行时状态查询接口。

    前端可轮询此接口以了解：
        - 是否启用了单任务模式
        - 当前是否有任务在运行
        - 服务器忙碌状态
        - 当前客户端总项目数

    Args:
        client_id: 客户端标识（从请求头提取）。

    Returns:
        RuntimeResponse: 运行时状态快照。
    """
    cfg = _app_config
    runtime = _runtime
    store = _store
    if cfg is None or runtime is None or store is None:
        raise HTTPException(status_code=503, detail="服务尚未就绪")

    status = runtime.get_runtime_status()
    total_tasks = len(store.list_tasks_by_client(client_id))

    return RuntimeResponse(
        single_active_task=status["single_active_task"],
        current_task_id=status["current_task_id"],
        current_project_name=status["current_project_name"],
        version=__version__,
        server_status="工作" if status["current_task_id"] else "空闲",
        total_tasks=total_tasks,
    )


@app.get("/api/tasks", response_model=list[TaskResponse])
def api_list_tasks(client_id: str = Depends(_get_client_id)) -> list[TaskResponse]:
    """列出当前用户的所有任务。

    按创建时间倒序排列。

    Args:
        client_id: 客户端标识（从请求头提取）。

    Returns:
        TaskResponse 列表。
    """
    store = _store
    if store is None:
        raise HTTPException(status_code=503, detail="服务尚未就绪")

    tasks = store.list_tasks_by_client(client_id)
    return [TaskResponse(**t) for t in tasks]


@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
def api_get_task(task_id: str) -> TaskResponse:
    """获取单个任务的详细信息。

    Args:
        task_id: 任务唯一标识。

    Returns:
        TaskResponse: 任务完整状态。

    Raises:
        404: 任务不存在。
    """
    store = _store
    if store is None:
        raise HTTPException(status_code=503, detail="服务尚未就绪")

    task = store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    return TaskResponse(**task)


@app.post("/api/tasks", response_model=TaskResponse, status_code=201)
def api_create_task(
    request: CreateTaskRequest,
    client_id: str = Depends(_get_client_id),
) -> TaskResponse:
    """创建新的音乐生成任务。

    校验并发限制后，在后台线程中启动 generate_music 管线。
    立即返回任务对象（状态为 pending），前端通过轮询追踪进度。

    Args:
        request: 创建任务请求体。
        client_id: 客户端标识（从请求头提取）。

    Returns:
        TaskResponse: 新创建的任务对象。

    Raises:
        409: 全局单任务模式下已有任务运行。
    """
    cfg = _app_config
    runtime = _runtime
    store = _store
    if cfg is None or runtime is None or store is None:
        raise HTTPException(status_code=503, detail="服务尚未就绪")

    rt = cfg.runtime

    if rt.global_single_active_task and runtime.is_task_running():
        status = runtime.get_runtime_status()
        raise HTTPException(
            status_code=409,
            detail=f"全局单任务模式已启用，当前任务 {status['current_task_id']} 正在运行",
        )

    task_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    project_name = request.project_name or f"{rt.data_dir}_{task_id[:8]}"

    task_data = {
        "task_id": task_id,
        "status": "pending",
        "prompt": request.prompt,
        "project_name": project_name,
        "created_at": now,
        "updated_at": now,
        "stages": [],
        "final_output": None,
        "error": None,
        "stage_index": None,
        "stage_total": None,
        "stage_name": None,
        "track_progress": None,
    }

    store.create_task(client_id, task_data)

    # 在后台线程中启动生成任务
    thread = threading.Thread(
        target=_run_generate_task,
        args=(task_id, client_id, request),
        daemon=True,
    )
    thread.start()

    return TaskResponse(**task_data)


@app.post("/api/tasks/{task_id}/retry", response_model=TaskResponse)
def api_retry_task(task_id: str, client_id: str = Depends(_get_client_id)) -> TaskResponse:
    """重试失败的任务。

    仅当任务状态为 failed 时才允许重试。
    重试时重置任务状态为 pending，并在后台线程中重新运行。

    Args:
        task_id: 任务唯一标识。
        client_id: 客户端标识（从请求头提取）。

    Returns:
        TaskResponse: 更新后的任务对象。

    Raises:
        404: 任务不存在。
        400: 任务状态不允许重试。
        409: 全局单任务模式下已有任务运行。
    """
    cfg = _app_config
    runtime = _runtime
    store = _store
    if cfg is None or runtime is None or store is None:
        raise HTTPException(status_code=503, detail="服务尚未就绪")

    task = store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    if task["status"] != "failed":
        raise HTTPException(
            status_code=400,
            detail=f"只有失败的任务才能重试，当前状态: {task['status']}",
        )

    rt = cfg.runtime

    if rt.global_single_active_task and runtime.is_task_running():
        status = runtime.get_runtime_status()
        raise HTTPException(
            status_code=409,
            detail=f"全局单任务模式已启用，当前任务 {status['current_task_id']} 正在运行",
        )

    now = datetime.now(timezone.utc).isoformat()
    store.update_task(
        task_id,
        {
            "status": "pending",
            "stages": [],
            "final_output": None,
            "error": None,
            "stage_index": None,
            "stage_total": None,
            "stage_name": None,
            "track_progress": None,
            "updated_at": now,
        },
    )

    # 构建重试请求
    retry_request = CreateTaskRequest(
        prompt=task["prompt"],
        project_name=task.get("project_name"),
        note_mode=cfg.music_defaults.note_mode,
        out_of_bounds_mode=cfg.music_defaults.out_of_bounds_mode,
    )

    # 后台执行
    thread = threading.Thread(
        target=_run_generate_task,
        args=(task_id, client_id, retry_request),
        daemon=True,
    )
    thread.start()

    updated = store.get_task(task_id)
    return TaskResponse(**updated)


# =========================================================================
# 文件下载端点
# =========================================================================


def _download_file(task_id: str, file_key: str, file_type: str) -> FileResponse:
    """通用的文件下载处理函数。

    从任务的 final_output 中提取文件路径并返回 FileResponse。

    Args:
        task_id: 任务唯一标识。
        file_key: final_output 中的文件路径键名（如 "midi_file"）。
        file_type: 文件类型描述（用于错误消息）。

    Returns:
        FileResponse: 文件下载响应。

    Raises:
        404: 任务不存在或文件尚未生成。
    """
    store = _store
    if store is None:
        raise HTTPException(status_code=503, detail="服务尚未就绪")

    task = store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    # 检查任务是否成功完成
    if task.get("status") != "succeeded":
        raise HTTPException(
            status_code=404,
            detail=f"任务尚未完成（当前状态: {task.get('status')}），{file_type} 文件不可用",
        )

    final_output = task.get("final_output")
    if final_output is None:
        raise HTTPException(status_code=404, detail=f"任务没有产物输出，{file_type} 文件不可用")

    file_path = final_output.get(file_key)
    if not file_path:
        raise HTTPException(status_code=404, detail=f"{file_type} 文件未生成")

    file_path = Path(file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"{file_type} 文件不存在: {file_path}")

    # 确定 MIME 类型和下载文件名
    media_types = {
        "mid": "audio/midi",
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
    }
    media_type = media_types.get(file_type, "application/octet-stream")

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
    )


@app.get("/api/tasks/{task_id}/download/mid/{role}")
def api_download_mid_track(task_id: str, role: str) -> FileResponse:
    """下载任务的单轨 MIDI 产物文件。

    Args:
        task_id: 任务唯一标识。
        role: 乐器角色名称（如 drums、bass、chords、lead）。

    Returns:
        FileResponse: MIDI 文件响应。
    """
    store = _store
    if store is None:
        raise HTTPException(status_code=503, detail="服务尚未就绪")

    task = store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    if task.get("status") != "succeeded":
        raise HTTPException(
            status_code=404,
            detail=f"任务尚未完成（当前状态: {task.get('status')}），MIDI 文件不可用",
        )

    final_output = task.get("final_output")
    if final_output is None:
        raise HTTPException(status_code=404, detail="任务没有产物输出，MIDI 文件不可用")

    per_track_midi = final_output.get("per_track_midi", {})
    file_path = per_track_midi.get(role)
    if not file_path:
        raise HTTPException(status_code=404, detail=f"轨道 '{role}' 的 MIDI 文件未生成")

    file_path = Path(file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"MIDI 文件不存在: {file_path}")

    return FileResponse(
        path=str(file_path),
        media_type="audio/midi",
        filename=file_path.name,
    )


@app.get("/api/tasks/{task_id}/download/mid")
def api_download_mid(task_id: str) -> FileResponse:
    """下载任务的 MIDI 产物文件（向后兼容，默认返回第一个轨道）。

    Args:
        task_id: 任务唯一标识。

    Returns:
        FileResponse: MIDI 文件响应。
    """
    store = _store
    if store is None:
        raise HTTPException(status_code=503, detail="服务尚未就绪")

    task = store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    if task.get("status") != "succeeded":
        raise HTTPException(
            status_code=404,
            detail=f"任务尚未完成（当前状态: {task.get('status')}），MIDI 文件不可用",
        )

    final_output = task.get("final_output")
    if final_output is None:
        raise HTTPException(status_code=404, detail="任务没有产物输出，MIDI 文件不可用")

    per_track_midi = final_output.get("per_track_midi", {})
    if not per_track_midi:
        raise HTTPException(status_code=404, detail="MIDI 文件未生成")

    file_path = list(per_track_midi.values())[0]
    file_path = Path(file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"MIDI 文件不存在: {file_path}")

    return FileResponse(
        path=str(file_path),
        media_type="audio/midi",
        filename=file_path.name,
    )


@app.get("/api/tasks/{task_id}/download/wav")
def api_download_wav(task_id: str) -> FileResponse:
    """下载任务的 WAV 产物文件。

    Note:
        WAV 渲染当前暂未启用，此端点预留。

    Args:
        task_id: 任务唯一标识。

    Returns:
        FileResponse: WAV 文件响应。
    """
    return _download_file(task_id, "wav_file", "WAV")


@app.get("/api/tasks/{task_id}/download/mp3")
def api_download_mp3(task_id: str) -> FileResponse:
    """下载任务的 MP3 产物文件。

    Note:
        MP3 转码当前暂未启用，此端点预留。

    Args:
        task_id: 任务唯一标识。

    Returns:
        FileResponse: MP3 文件响应。
    """
    return _download_file(task_id, "mp3_file", "MP3")


# =========================================================================
# 前端静态文件托管
# =========================================================================

_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")