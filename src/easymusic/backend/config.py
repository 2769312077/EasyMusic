"""EasyMusic Backend 配置管理模块。

使用 dataclass 定义配置结构，支持从 YAML 文件加载配置，
并通过环境变量覆盖关键配置项（尤其是 LLM 相关配置）。

配置域：
    - app: 服务监听地址、端口、CORS 跨域白名单
    - runtime: 运行时行为控制（数据目录、并发限制、配额等）
    - music_defaults: 音乐生成管线的默认参数
    - llm: 大语言模型 API 配置（API Key 必须从环境变量读取）
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class _AppConfig:
    """服务层配置 —— 控制 FastAPI 服务的行为。"""

    host: str = "0.0.0.0"
    """服务监听地址"""

    port: int = 8000
    """服务监听端口"""

    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    """CORS 允许的跨域来源列表"""


@dataclass
class _RuntimeConfig:
    """运行时配置 —— 控制任务调度和并发行为。"""

    data_dir: str = "data"
    """持久化数据存储目录（相对于 backend 模块所在目录）"""

    outputs_dir: str = "outputs"
    """管线输出产物目录"""

    stage_retry_count: int = 3
    """失败任务的最大重试次数"""

    max_music_duration_seconds: int = 120
    """单次音乐生成的最大时长限制（秒）"""

    global_single_active_task: bool = True
    """是否启用全局单任务模式（同时只允许一个生成任务运行）"""


@dataclass
class _MusicDefaultsConfig:
    """音乐生成管线默认参数 —— 当客户端请求未指定时使用的回退值。"""

    project_name_prefix: str = "web"
    """项目名称前缀，用于区分 Web 端发起的生成任务"""

    soundfont_path: str = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
    """SoundFont 音色库文件路径（用于 WAV 渲染，当前暂未启用）"""

    mp3_bitrate: str = "192k"
    """MP3 编码比特率"""

    note_mode: str = "llm"
    """默认音符生成模式：llm（大模型生成）或 rule（规则生成）"""

    out_of_bounds_mode: str = "ignore"
    """越界事件处理策略：ignore（保留）或 drop（丢弃）"""


@dataclass
class _LLMConfig:
    """LLM API 配置 —— API Key 必须从环境变量 OPENAI_API_KEY 读取。"""

    openai_api_key: str = ""
    """OpenAI API 密钥（优先从环境变量 OPENAI_API_KEY 读取）"""

    openai_base_url: str = ""
    """OpenAI API 基础 URL（可被环境变量 OPENAI_BASE_URL 覆盖）"""

    openai_model: str = "gpt-4o"
    """默认使用的 OpenAI 模型名称（可被环境变量 OPENAI_MODEL 覆盖）"""


@dataclass
class AppConfig:
    """EasyMusic Backend 全局配置聚合类。

    用法:
        config = AppConfig.load("config.yaml")
        print(config.app.host)
        print(config.llm.openai_model)
    """

    app: _AppConfig = field(default_factory=_AppConfig)
    """服务层配置"""

    runtime: _RuntimeConfig = field(default_factory=_RuntimeConfig)
    """运行时配置"""

    music_defaults: _MusicDefaultsConfig = field(default_factory=_MusicDefaultsConfig)
    """音乐生成默认参数"""

    llm: _LLMConfig = field(default_factory=_LLMConfig)
    """LLM API 配置"""

    @classmethod
    def load(cls, config_path: str | Path) -> AppConfig:
        """从 YAML 配置文件加载配置，并用环境变量覆盖 LLM 相关配置。

        加载顺序：
            1. 读取 YAML 文件中的原始配置
            2. 用环境变量覆盖 LLM 域的三个配置项

        Args:
            config_path: YAML 配置文件的路径。

        Returns:
            填充完毕的 AppConfig 实例。

        Raises:
            FileNotFoundError: 配置文件不存在。
            ImportError: yaml 库未安装。
        """
        import yaml

        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}

        # ---- 解析各配置域 ----
        app_raw = raw.get("app", {})
        app = _AppConfig(
            host=app_raw.get("host", "0.0.0.0"),
            port=app_raw.get("port", 8000),
            cors_origins=app_raw.get("cors_origins", ["*"]),
        )

        runtime_raw = raw.get("runtime", {})
        runtime = _RuntimeConfig(
            data_dir=runtime_raw.get("data_dir", "data"),
            outputs_dir=runtime_raw.get("outputs_dir", "outputs"),
            stage_retry_count=runtime_raw.get("stage_retry_count", 3),
            max_music_duration_seconds=runtime_raw.get("max_music_duration_seconds", 120),
            global_single_active_task=runtime_raw.get("global_single_active_task", True),
        )

        music_raw = raw.get("music_defaults", {})
        music_defaults = _MusicDefaultsConfig(
            project_name_prefix=music_raw.get("project_name_prefix", "web"),
            soundfont_path=music_raw.get("soundfont_path", "/usr/share/sounds/sf2/FluidR3_GM.sf2"),
            mp3_bitrate=music_raw.get("mp3_bitrate", "192k"),
            note_mode=music_raw.get("note_mode", "llm"),
            out_of_bounds_mode=music_raw.get("out_of_bounds_mode", "ignore"),
        )

        llm_raw = raw.get("llm", {})

        # LLM 配置：优先从环境变量读取，回退到 YAML 中的值
        llm = _LLMConfig(
            openai_api_key=os.getenv("OPENAI_API_KEY", llm_raw.get("openai_api_key", "")),
            openai_base_url=os.getenv("OPENAI_BASE_URL", llm_raw.get("openai_base_url", "")),
            openai_model=os.getenv("OPENAI_MODEL", llm_raw.get("openai_model", "gpt-4o")),
        )

        return cls(app=app, runtime=runtime, music_defaults=music_defaults, llm=llm)


# 模块级单例：在 main.py 启动时调用 AppConfig.load() 填充
config: AppConfig | None = None
"""模块级配置单例，在应用启动时由 main.py 初始化。"""