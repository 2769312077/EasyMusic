"""EasyMusic Backend 请求/响应数据模型。

使用 Pydantic v2 定义 API 的输入输出结构，包括：
    - CreateTaskRequest: 创建音乐生成任务的请求体
    - TaskResponse: 单个任务的完整状态响应
    - RuntimeResponse: 全局运行时状态 + 每日配额信息
    - HealthResponse: 健康检查响应
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class CreateTaskRequest(BaseModel):
    """创建音乐生成任务的请求体。

    Attributes:
        prompt: 用户的自然语言音乐描述（必填）。
        project_name: 可选的项目名称，不填则使用配置中的默认前缀 + 时间戳。
        note_mode: 可选的音符生成模式，覆盖全局默认值。
        out_of_bounds_mode: 可选的越界处理策略，覆盖全局默认值。
        llm_provider: LLM 服务商选择（gpt / deepseek / lmstudio）。
        llm_api_key: 前端配置的 LLM API 密钥（LM Studio 本地模型无需此项）。
        llm_base_url: 前端配置的 LLM API Base URL（可选）。
        llm_model: 前端配置的 LLM 模型名称（可选，默认 gpt-4o）。
    """

    prompt: str = Field(..., description="自然语言音乐描述", min_length=1)
    """音乐描述提示词（必填）"""

    project_name: Optional[str] = Field(None, description="项目名称，不填则自动生成")
    """可选的项目名称"""

    note_mode: Optional[str] = Field(None, description="音符生成模式：llm 或 rule")
    """可选的音符生成模式，覆盖全局默认"""

    out_of_bounds_mode: Optional[str] = Field(None, description="越界处理策略：ignore 或 drop")
    """可选的越界处理策略，覆盖全局默认"""

    llm_provider: Optional[str] = Field(None, description="LLM 服务商：gpt / deepseek / lmstudio")
    """前端选择的 LLM 服务商"""

    llm_api_key: Optional[str] = Field(None, description="LLM API 密钥")
    """前端配置的 LLM API 密钥（LM Studio 本地模型无需此项）"""

    llm_base_url: Optional[str] = Field(None, description="LLM API Base URL")
    """前端配置的 LLM API Base URL"""

    llm_model: Optional[str] = Field(None, description="LLM 模型名称")
    """前端配置的 LLM 模型名称"""


class TaskResponse(BaseModel):
    """音乐生成任务的完整状态响应。

    该模型在任务生命周期的各个阶段都会被返回，
    随管线推进逐步填充 stage_* 和 track_progress 字段。
    """

    task_id: str = Field(..., description="任务唯一标识")
    """任务唯一 ID"""

    status: str = Field(..., description="任务状态：pending / running / succeeded / failed")
    """任务当前状态"""

    prompt: str = Field(..., description="用户原始音乐描述")
    """用户提交的原始 prompt"""

    project_name: str = Field(..., description="项目名称")
    """本次生成的项目名称"""

    created_at: str = Field(..., description="任务创建时间（ISO 8601 格式）")
    """任务创建时间"""

    updated_at: str = Field(..., description="任务最后更新时间（ISO 8601 格式）")
    """任务最后更新时间"""

    stages: list[dict] = Field(default_factory=list, description="管线各阶段的进度记录")
    """管线各阶段的进度记录列表"""

    final_output: Optional[dict] = Field(None, description="生成完成后的产物信息")
    """生成成功后的产物元信息（midi_file、metadata 等）"""

    error: Optional[str] = Field(None, description="失败时的错误信息")
    """失败时的错误描述"""

    stage_index: Optional[int] = Field(None, description="当前阶段索引（1-based）")
    """当前执行到的阶段索引"""

    stage_total: Optional[int] = Field(None, description="阶段总数")
    """管线阶段总数"""

    stage_name: Optional[str] = Field(None, description="当前阶段名称")
    """当前阶段名称"""

    track_progress: Optional[dict] = Field(None, description="音符生成轨道的逐轨进度")
    """第 4 阶段音符生成时的逐轨进度详情"""


class RuntimeResponse(BaseModel):
    """全局运行时状态响应。

    供前端轮询，展示当前服务负载和任务统计信息。
    """

    single_active_task: bool = Field(..., description="是否启用全局单任务锁")
    """是否启用全局单任务模式"""

    current_task_id: Optional[str] = Field(None, description="当前正在运行的任务 ID")
    """当前正在运行的任务 ID（无任务时为 None）"""

    current_project_name: Optional[str] = Field(None, description="当前运行任务的项目名称")
    """当前运行任务的项目名称（无任务时为 None）"""

    version: str = Field("", description="EasyMusic 版本号")
    """EasyMusic 版本号"""

    server_status: str = Field("空闲", description="服务器状态：空闲 / 工作")
    """当前服务器忙碌状态"""

    total_tasks: int = Field(0, description="当前客户端的总项目数")
    """当前客户端创建的任务总数"""


class HealthResponse(BaseModel):
    """健康检查响应。

    用于负载均衡器和监控系统探测服务可用性。
    """

    status: str = Field("ok", description="服务状态")
    """服务状态标识，正常时为 \"ok\""""

    version: str = Field(..., description="EasyMusic 版本号")
    """当前 EasyMusic 版本号"""