# EasyMusic

**AI 自然语言转 MIDI 音乐生成** | [English](README.md)

用自然语言描述音乐，自动生成多轨道 MIDI。例如*"一首欢快的流行舞曲，128 BPM，C 大调"*→ 鼓、贝斯、和弦、主旋律，一步到位。

---

## 快速开始（Windows）

1. 安装 Python 3.10+，在项目根目录运行 `pip install -e .`
2. 将 `.env.example` 复制为 `.env`，填入 LLM API Key
3. 双击 **`Start EasyMusic.bat`**
4. 浏览器自动打开——输入描述，创建音乐

---

## 使用方式

### Web 界面

启动后在设置抽屉中配置 LLM 提供商/API Key/模型，输入音乐描述，点击**创建**。完成后可下载分轨 MIDI、完整 MIDI、WAV 或 MP3。

### 命令行

```bash
ecms "一首欢快的流行舞曲，128 BPM，C 大调"

# 完整参数
ecms "描述" --output ./out --tracks drums bass lead --note-mode llm --render-audio

# 从 Checkpoint 恢复
ecms --resume /path/to/project

# 测试 API 连通性
ecms --test
```

### Python API

```python
from easymusic.pipeline.orchestrator import generate_music

result = generate_music(
    prompt="一首欢快的流行歌曲",
    output_dir="./output",
    note_generation_mode="llm",  # 或 "rule"
)
```

---

## 部署

### 环境要求

- Python 3.10+
- LLM API Key（OpenAI / DeepSeek / LM Studio）
- 可选：FluidSynth + FFmpeg（音频渲染）

### 安装

```bash
pip install -e .
cp .env.example .env   # 填入 API Key
ecms-server             # 启动后端并服务前端
```

### 配置

优先级：**环境变量 > config.yaml > 默认值**

```yaml
# src/easymusic/backend/config.yaml
llm:
  openai_api_key: ""       # 或设置 OPENAI_API_KEY 环境变量
  openai_base_url: ""      # 或设置 OPENAI_BASE_URL
  openai_model: "gpt-4o"
```

---

## 工作原理

九阶段管线：**意图解析 → 歌曲规划 → 编配规划 → 音符生成（LLM×N 并行 / 规则生成）→ MIDI IR 组装 → 校验 → MIDI 渲染 → 音频渲染（可选）**

- 阶段 1–3：LLM 完成创意决策
- 阶段 5–7：确定性代码保证质量
- 每阶段保存 JSON Checkpoint，支持任意阶段恢复
- 两种音符生成模式：`llm`（高质量）或 `rule`（无需 API）

### 技术栈

Python 3.10+ · OpenAI SDK · mido · FastAPI · 原生 HTML/CSS/JS · FluidSynth + FFmpeg · Docker Compose

---

## 常见问题

**JSON 解析错误？** — 检查 API Key、模型兼容性和网络（超时 180 秒）。系统内置三级容错提取，可处理大部分情况。

**音符超出范围？** — 阶段 5 自动裁剪音高并吸附到调式内音。使用 `--out-of-bounds-mode drop` 丢弃越界事件。

**Windows 无法渲染音频？** — 推荐使用 Docker，或跳过 `--render-audio` 仅生成 MIDI。

**前端连不上后端？** — 确认后端正在运行，检查 `config.yaml` 的 CORS 配置，在设置抽屉中确认后端地址。

**提升质量？** — 使用 gpt-4o，写详细提示词，核心轨道用 LLM 模式。
