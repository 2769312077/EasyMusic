# EasyMusic

**AI Prompt-to-MIDI Music Generation** | [中文文档](README_zh.md)

Describe music in natural language, get multi-track MIDI. E.g., *"An upbeat pop track, 128 BPM, C major"* → drums, bass, chords, lead melody — done.

---

## Quick Start (Windows)

1. Install Python 3.10+ and run `pip install -e .` in the project root
2. Copy `.env.example` to `.env`, fill in your LLM API key
3. Double-click **`Start EasyMusic.bat`**
4. Browser opens automatically — enter a prompt and create music

---

## Usage

### Web UI

After launch, open the settings drawer to configure LLM provider/API key/model, type a music description, and hit **Create**. Download per-track MIDI, full MIDI, WAV, or MP3 when done.

### CLI

```bash
ecms "An upbeat pop track, 128 BPM, C major"

# Full options
ecms "prompt" --output ./out --tracks drums bass lead --note-mode llm --render-audio

# Resume from checkpoint
ecms --resume /path/to/project

# Test API connectivity
ecms --test
```

### Python API

```python
from easymusic.pipeline.orchestrator import generate_music

result = generate_music(
    prompt="A cheerful pop song",
    output_dir="./output",
    note_generation_mode="llm",  # or "rule"
)
```

---

## Deployment

### Requirements

- Python 3.10+
- LLM API key (OpenAI / DeepSeek / LM Studio)
- Optional: FluidSynth + FFmpeg (for audio rendering), Docker (for container deployment)

### Docker Compose

```bash
git clone https://github.com/2769312077/EasyMusic.git && cd EasyMusic
cp .env.example .env   # edit with your API key
docker-compose up -d
```

- Web UI: `http://localhost:5173`
- API: `http://localhost:8000`

### Manual

```bash
pip install -e .
cp .env.example .env   # edit with your API key
ecms-server             # starts backend + serves frontend
```

### Configuration

Priority: **env vars > config.yaml > defaults**

```yaml
# src/easymusic/backend/config.yaml
llm:
  openai_api_key: ""       # or set OPENAI_API_KEY env var
  openai_base_url: ""      # or set OPENAI_BASE_URL
  openai_model: "gpt-4o"
```

---

## How It Works

9-stage pipeline: **Intent Parsing → Song Planning → Arrangement → Note Generation (LLM×N parallel / rule-based) → MIDI IR Assembly → Validation → MIDI Render → Audio Render (optional)**

- Stages 1–3: LLM makes creative decisions
- Stages 5–7: deterministic code ensures quality
- Each stage saves JSON checkpoints — resume from any point
- Two note generation modes: `llm` (higher quality) or `rule` (no API needed)

### Tech Stack

Python 3.10+ · OpenAI SDK · mido · FastAPI · Vanilla HTML/CSS/JS · FluidSynth + FFmpeg

---

## FAQ

**JSON parse error?** — Check API key, model compatibility, and network (timeout = 180s). Built-in 3-level fault-tolerant extraction handles most cases.

**Notes out of range?** — Stage 5 auto-clamps pitches and snaps to scale. Use `--out-of-bounds-mode drop` to discard.

**No audio on Windows?** — Use Docker (recommended) or skip `--render-audio` to get MIDI only.

**Frontend can't connect?** — Verify backend is running, check CORS in `config.yaml`, confirm backend URL in settings drawer.

**Better quality?** — Use gpt-4o, write detailed prompts, use LLM mode for core tracks.
