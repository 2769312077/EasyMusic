"""提示词模板定义。

定义各阶段（意图解析 → 歌曲规划 → 编配规划 → 音符生成）的 LLM 提示词模板。
模板中注入乐理知识库和乐器知识库内容，确保 LLM 生成符合 GM 标准和解析器约束。

模板设计原则：
    - 所有模板要求 LLM 返回纯 JSON，不含 Markdown 标记或解释文本。
    - 使用严格嵌套的 JSON 结构，禁止扁平化的点号键名。
    - 每个模板包含明确的约束规则和输出示例。
"""

from __future__ import annotations

from easymusic.core.music_theory import NOTE_TO_SEMITONE, SEMITONE_TO_NOTE, get_scale, midi_to_note_name
from easymusic.prompts.loader import (
    load_chord_knowledge,
    load_instrument_knowledge,
    load_note_knowledge,
)


def build_intent_parser_prompt(
    user_prompt: str,
    enforce_core_tracks: bool = True,
    max_duration_seconds: int | None = None,
) -> str:
    """构建意图解析阶段的 LLM 提示词。

    将用户的自然语言描述解析为结构化的音乐意图，包括风格、情绪、
    使用场景、时长、轨道需求等。

    Args:
        user_prompt: 用户的自然语言音乐描述。
        enforce_core_tracks: 是否强制要求核心四轨（drums/bass/chords/lead）。
            LLM 模式下为 False（允许自由选择），规则模式下为 True。
        max_duration_seconds: 最大时长限制（秒），如设置了则 LLM 生成的
            duration_seconds 不得超过此值。

    Returns:
        完整的意图解析提示词字符串。
    """
    track_rule = (
        "- requested_tracks 必须至少包含 drums,bass,chords,lead"
        if enforce_core_tracks
        else "- requested_tracks 应由音乐意图自行决定，不要强制固定乐器组合"
    )
    duration_rule = (
        f"- intent.duration_seconds 必须 <= {max_duration_seconds}，"
        f"如用户要求更长则限制为 {max_duration_seconds}"
        if max_duration_seconds is not None
        else "- intent.duration_seconds 应适合循环 BGM，不明确时默认为 30"
    )
    return f"""
You are an Intent Parser for a MIDI music generation pipeline.
Return JSON only. No markdown, no explanations.

User prompt: {user_prompt}

Output fields:
- task_type: 任务类型，固定为 "generate_music"
- user_prompt: 原始用户提示词
- intent.style: 音乐风格列表（如 ["cyberpunk", "electronic"]）
- intent.mood: 情绪关键词列表（如 ["dark", "intense"]）
- intent.use_case: 使用场景描述（如 "game_bgm", "video_background"）
- intent.duration_seconds: 时长（秒），数值
- intent.loopable: 是否可循环（布尔）
- intent.complexity: 复杂度（"low" / "medium" / "high"）
- intent.requested_tracks: 请求的轨道列表
- intent.tempo_preference: 速度倾向（"slow" / "medium" / "fast" / "very_fast"）
- intent.must_have: 必须包含的元素列表
- intent.avoid: 应避免的元素列表

Rules:
- 输出必须是精确的嵌套 JSON 结构（禁止使用点号键名如 "intent.style"）
{track_rule}
- {duration_rule}
- 缺失值用合理默认值填充
- 输出格式示例:
{{
  "task_type": "generate_music",
  "user_prompt": "...",
  "intent": {{
    "style": ["..."],
    "mood": ["..."],
    "use_case": "...",
    "duration_seconds": 30,
    "loopable": true,
    "complexity": "medium",
    "requested_tracks": ["drums", "bass", "chords", "lead"],
    "tempo_preference": "fast",
    "must_have": ["drums", "bass", "chords", "lead"],
    "avoid": []
  }}
}}
""".strip()


def build_song_planner_prompt(intent: dict) -> str:
    """构建歌曲规划阶段的 LLM 提示词。

    基于解析后的意图规划歌曲结构：BPM、拍号、调性、段落划分、
    和弦进行等。模板中注入完整和弦知识库。

    Args:
        intent: parse_intent 输出的意图字典。

    Returns:
        完整的歌曲规划提示词字符串。
    """
    chord_knowledge = load_chord_knowledge()
    return f"""
You are a Song Planner for a MIDI music generation pipeline.
Return JSON only. No markdown, no explanations.

Input intent: {intent}

Chord progression knowledge:
{chord_knowledge}

Output top-level key: song_plan
Required song_plan fields:
  title, bpm, time_signature, key, total_bars, estimated_duration_seconds,
  loopable, global_style, sections, chord_progression

Constraints:
- time_signature 在 MVP 阶段固定为 4/4
- bpm 应与 intent 中的 tempo_preference 匹配
- total_bars 必须是 8, 12, 16, 24, 32 之一
- chord_progression 至少包含 4 小节且可循环
- 不同运行应生成新的创作，但保持风格一致性
- 自然变化和声节奏、段落对比和动机发展
- 和弦符号限制（当前解析器严格）:
  - 仅允许根音大三和弦或小三和弦形式，如 C, Dm, Bb, F#m
  - 禁止斜线和弦（如 Eb/G）、扩展和弦（maj7, m7, sus4, add9）、变和弦
  - 和弦根音必须来自此映射: {NOTE_TO_SEMITONE}
  - 系统使用的标准音名: {SEMITONE_TO_NOTE}
- 使用上述和弦进行知识作为主要决策指南:
  - 从 intent style, mood, use_case 推断大调/小调模式
  - 选择与请求风格和情绪匹配的和弦度数模板
  - 将罗马数字度数转换为选定调性中的具体和弦符号
  - 保持 chord_progression 可分段落感知且可循环
  - 如知识建议不兼容的和弦，适配合规的大/小三和弦
- chord_progression 必须包含具体和弦符号，不得使用罗马数字
- 输出格式示例:
{{
  "song_plan": {{
    "title": "...",
    "bpm": 140,
    "time_signature": {{"numerator": 4, "denominator": 4}},
    "key": {{"root": "D", "mode": "minor", "scale": "natural_minor"}},
    "total_bars": 16,
    "estimated_duration_seconds": 27.4,
    "loopable": true,
    "global_style": {{"primary": "cyberpunk", "energy": 0.8, "darkness": 0.7, "brightness": 0.3}},
    "sections": [{{"id": "intro", "name": "Intro", "start_bar": 0, "length_bars": 4, "energy": 0.4}}],
    "chord_progression": [{{"bar": 0, "chord": "Dm"}}, {{"bar": 1, "chord": "Bb"}}, {{"bar": 2, "chord": "C"}}, {{"bar": 3, "chord": "A"}}]
  }}
}}
""".strip()


def build_arrangement_planner_prompt(
    intent: dict,
    song_plan: dict,
    enforce_core_tracks: bool = True,
) -> str:
    """构建编配规划阶段的 LLM 提示词。

    根据意图和歌曲计划，规划乐器编配：轨道配置、MIDI 通道、
    混音参数、生成策略等。模板中注入完整乐器知识库。

    Args:
        intent: 解析后的意图字典。
        song_plan: 歌曲计划字典（含 "song_plan" 键）。
        enforce_core_tracks: 是否强制包含核心轨道。

    Returns:
        完整的编配规划提示词字符串。
    """
    arrangement_track_rule = (
        "- tracks 必须包含核心轨道: drums,bass,chords,lead"
        if enforce_core_tracks
        else "- tracks 应由风格和用户意图决定，不强制固定核心乐器"
    )
    instrument_knowledge = load_instrument_knowledge()
    return f"""Instrument knowledge:
{instrument_knowledge}

You are an Arrangement Planner for a MIDI music generation pipeline.
Return JSON only. No markdown, no explanations.

Input intent: {intent}
Input song_plan: {song_plan}

Output format:
{{"arrangement": {{"tracks": {{...}} }} }}

Rules:
{arrangement_track_rule}
- 当风格或用户请求需要时允许额外轨道
- drums 必须使用 channel=9 且 program=null
- 非鼓轨道不得使用 channel=9
- 每条轨道必须包含以下字段:
  id, name, role, enabled, is_core_track, generation_strategy, midi, mix, style, sections
- 鼓励跨运行变化:
  - 不锁定到单一固定旋律方向
  - 每次运行优选不同的段落密度和角色交互
  - 保持请求风格，但允许创意编配决策
- 输出格式示例:
{{
  "arrangement": {{
    "tracks": {{
      "drums": {{
        "id": "drums",
        "name": "Drums",
        "role": "rhythm",
        "enabled": true,
        "is_core_track": true,
        "generation_strategy": "drum_generator",
        "midi": {{"channel": 9, "program": null}},
        "mix": {{"volume": 105, "pan": 64}},
        "style": {{"pattern_type": "driving_electronic", "density": "high"}},
        "sections": {{
          "intro": {{"active": true, "density": "low"}},
          "main_a": {{"active": true, "density": "medium"}},
          "main_b": {{"active": true, "density": "high"}}
        }}
      }}
    }}
  }}
}}
""".strip()


def _register_constraint(track_id: str, role: str) -> str:
    """为给定轨道角色生成简洁的音高范围约束文本。

    Args:
        track_id: 轨道 ID（drums 不限制）。
        role: 轨道角色。

    Returns:
        一行约束文本，如 "Bass: pitch 24-48 (C1-C3)"。
    """
    if track_id == "drums":
        return "Drums: use GM Drum Map pitches only (no restriction)"
    from easymusic.core.midi_ir import REGISTER_MAP
    lo, hi = REGISTER_MAP.get(role, (21, 108))
    lo_name = midi_to_note_name(lo)
    hi_name = midi_to_note_name(hi)
    return f"{role}: pitch {lo}-{hi} ({lo_name}-{hi_name}), all notes MUST stay in this range"


def _scale_constraint(song_plan: dict) -> str:
    """生成调式约束的简短描述文本。

    Args:
        song_plan: 歌曲计划字典（已扁平化）。

    Returns:
        如 "D major (D,E,F#,G,A,B,C#)"。
    """
    key = song_plan.get("key", {})
    root = key.get("root", "C")
    mode = key.get("mode", "minor")
    scale_type = "major" if mode == "major" else "natural_minor"
    try:
        scale = get_scale(root, scale_type)
        scale_str = ",".join(scale)
        return f"{root} {mode} ({scale_str})"
    except (ValueError, KeyError):
        return f"{root} {mode}"


def _strict_scale_rule(song_plan: dict, track_id: str) -> str:
    """生成严格的调式内音符约束规则。

    Args:
        song_plan: 歌曲计划字典。
        track_id: 当前轨道 ID。

    Returns:
        约束规则文本。
    """
    if track_id == "drums":
        return ""
    key = song_plan.get("key", {})
    root = key.get("root", "C")
    mode = key.get("mode", "minor")
    scale_type = "major" if mode == "major" else "natural_minor"
    try:
        scale = get_scale(root, scale_type)
        allowed = ",".join(scale)
        return f"- ALL pitches MUST be in {root} {mode} scale: only [{allowed}] allowed, NO out-of-scale notes"
    except (ValueError, KeyError):
        return f"- ALL pitches MUST be in {root} {mode} scale"


def build_track_note_generator_prompt(
    song_plan: dict,
    arrangement_track: dict,
) -> str:
    """构建音符生成阶段的 LLM 提示词。

    为单条轨道生成具体的音符事件序列。如果是鼓轨，模板中会注入
    GM 鼓组映射和鼓组编排指南。

    Args:
        song_plan: 歌曲计划字典（已扁平化，包含 total_bars、time_signature 等）。
        arrangement_track: 当前轨道的配置字典。

    Returns:
        完整的音符生成提示词字符串。
    """
    from easymusic.core.drum_map import DRUM_MAP

    # 提取基本参数
    total_bars = song_plan["total_bars"]
    beats_per_bar = song_plan["time_signature"]["numerator"]
    total_beats = total_bars * beats_per_bar
    track_id = arrangement_track.get("id", "unknown")
    role = arrangement_track.get("role", "unknown")

    note_knowledge = load_note_knowledge()

    # ---------- 鼓轨特殊指南 ----------
    _is_drums = track_id == "drums" or role == "rhythm"
    drum_guidance = ""
    if _is_drums:
        # 构建 GM 鼓映射参考表（按 pitch 排序）
        drum_map_lines = "\n".join(
            f"    {pitch}: {name}" for name, pitch in sorted(DRUM_MAP.items(), key=lambda x: x[1])
        )
        drum_guidance = f"""
DRUM TRACK — use GM Drum Map pitches only (no melodic pitches 0-127):
{drum_map_lines}

Patterns by density:
- low: kick beats 0,2; snare beat 2; sparse closed_hat (1/4 or less)
- medium: kick 0,2 (+sync 0.75 optional); snare 1,3; closed_hat 1/8 moderate density
- high: kick 0,1.5,2,3.5; snare 1,3; closed_hat 1/16 at ~50% density + occasional open_hat; crash at section starts

Fills: last bar of section → snare roll (1/16 increasing velocity, last 1-2 beats only) or tom fill (high_tom→mid_tom→low_tom→snare at beats 2-4). Final bar: crash+kick at beat 0 + moderate fill.

Velocity: kick 85-110, snare 75-105, closed_hat 55-85, open_hat 65-90, crash 95-120, tom 75-105
""".strip()

    return f"""
You are a MIDI note event generator.
Return JSON only. No markdown, no explanations.

Input song_plan: {song_plan}
Input track: {arrangement_track}

Note generation knowledge:
{note_knowledge}
{chr(10) + "Drum-specific knowledge:" + chr(10) + drum_guidance if drum_guidance else ""}

Register limits for this track (MUST obey):
{_register_constraint(track_id, role)}

Output format — compact CSV, one event per semicolon block, NO JSON, NO markdown:
t:n,p:60,s:0,d:0.5,v:96;t:n,p:64,s:0.5,d:0.25,v:80

Field keys: t=type(n=note), p=pitch, s=start_beat, d=duration_beat, v=velocity
Events separated by ; fields by , key:value by :

Constraints:
- track_id: {track_id}, role: {role}, total_bars: {total_bars}, beats_per_bar: {beats_per_bar}, total_beats: {total_beats}
- Key/scale: {_scale_constraint(song_plan)}
- Keep style consistency with song_plan and track.style
- Use note generation knowledge: choose notes by chord, register by role, duration/density/velocity by section energy
- When song_plan.loopable is true, make loop ending naturally return to beginning
- Chord symbols are major/minor triads only; root notes: {NOTE_TO_SEMITONE}
{_strict_scale_rule(song_plan, track_id)}
{f"- Drum track must use GM Drum Map pitches only." if _is_drums else ""}
- 0<=p<=127, 1<=v<=127, s>=0, d>0, s+d<=total_beats
- Output ONLY the CSV text, nothing else
""".strip()