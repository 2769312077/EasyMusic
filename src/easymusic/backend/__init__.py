"""EasyMusic Backend —— FastAPI 后端服务模块。

提供 RESTful API 接口，支持音乐生成任务的提交、状态追踪、
产物下载以及运行时状态查询。

公开接口：
    - app: FastAPI 应用实例（供 uvicorn 等 ASGI 服务器挂载）
    - start_server: 启动后端服务的便捷函数
    - AppConfig: 配置管理类
    - TaskStore: 任务持久化存储
    - GlobalRuntime: 全局运行时管理器
"""

from easymusic.backend.config import AppConfig
from easymusic.backend.main import app
from easymusic.backend.runner import GlobalRuntime
from easymusic.backend.store import TaskStore


def start_server() -> None:
    """启动 EasyMusic 后端 Web 服务。

    使用 uvicorn 运行 FastAPI 应用，从 config.yaml 加载配置。
    此函数作为 ecms-server 命令的入口点。

    启动前自动执行：
        1. 从 backend/config.yaml 加载配置
        2. 初始化 TaskStore 和 GlobalRuntime
        3. 设置工作目录为 backend 所在目录
    """
    import os
    import uvicorn
    from pathlib import Path

    from easymusic._version import __version__

    # 设置工作目录为 backend 模块所在目录，确保相对路径正确解析
    backend_dir = Path(__file__).resolve().parent
    os.chdir(str(backend_dir))

    # 从配置文件加载 host 和 port
    try:
        cfg = AppConfig.load()
        host = cfg.app.host
        port = cfg.app.port
    except Exception:
        host = "0.0.0.0"
        port = 8000

    print(f"EasyMusic Server v{__version__} starting on http://{host}:{port}")
    print(f"API docs: http://{host}:{port}/docs")
    uvicorn.run("easymusic.backend:app", host=host, port=port, reload=False)


__all__ = [
    "app",
    "start_server",
    "AppConfig",
    "TaskStore",
    "GlobalRuntime",
]