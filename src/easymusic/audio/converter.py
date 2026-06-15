"""音频处理模块。

提供 MIDI 到 WAV（通过 fluidsynth）和 WAV 到 MP3（通过 ffmpeg）的转换功能。

依赖：
    - fluidsynth: MIDI → WAV（需要 SoundFont 音色库文件）
    - ffmpeg: WAV → MP3（编解码器 libmp3lame）

注意：
    这些转换依赖外部命令行工具，在 Windows 环境下通常不可用。
    当前版本保留代码结构但管线默认跳过音频渲染阶段。
    未来可扩展为使用内置合成器方案。
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path


def _run_command_stream(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """执行外部命令并流式读取 stdout/stderr。

    Args:
        cmd: 命令和参数列表。
        cwd: 工作目录。

    Returns:
        (退出码, 标准输出, 标准错误) 的三元组。
    """
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []

    while True:
        if proc.stdout is not None:
            out = proc.stdout.readline()
            if out:
                stdout_chunks.append(out)
        if proc.stderr is not None:
            err = proc.stderr.readline()
            if err:
                stderr_chunks.append(err)
        if proc.poll() is not None:
            break
        time.sleep(0.02)

    # 读取残留输出
    if proc.stdout is not None:
        remaining_out = proc.stdout.read()
        if remaining_out:
            stdout_chunks.append(remaining_out)
    if proc.stderr is not None:
        remaining_err = proc.stderr.read()
        if remaining_err:
            stderr_chunks.append(remaining_err)

    return proc.returncode, "".join(stdout_chunks), "".join(stderr_chunks)


def midi_to_wav(
    midi_path: str,
    wav_path: str,
    soundfont_path: str = "/usr/share/sounds/sf2/FluidR3_GM.sf2",
) -> str:
    """使用 fluidsynth 将 MIDI 文件渲染为 WAV 音频。

    调用 fluidsynth 命令行工具，使用指定的 SoundFont 音色库
    将 MIDI 文件渲染为 44100 Hz 的 WAV 音频。

    Args:
        midi_path: 输入 MIDI 文件路径（必须存在）。
        wav_path: 输出 WAV 文件路径（父目录自动创建）。
        soundfont_path: SoundFont .sf2 音色库文件路径。

    Returns:
        生成的 WAV 文件路径。

    Raises:
        FileNotFoundError: MIDI 或 SoundFont 文件不存在。
        RuntimeError: fluidsynth 执行失败。
    """
    midi_file = Path(midi_path)
    wav_file = Path(wav_path)
    sf2_file = Path(soundfont_path)

    if not midi_file.exists():
        raise FileNotFoundError(f"MIDI 文件不存在: {midi_file}")
    if not sf2_file.exists():
        raise FileNotFoundError(f"SoundFont 音色库不存在: {sf2_file}")

    wav_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "fluidsynth",
        "-ni",            # 无交互模式
        str(sf2_file),
        str(midi_file),
        "-F",             # 输出 WAV 文件
        str(wav_file),
        "-r",             # 采样率
        "44100",
    ]

    code, _out, err = _run_command_stream(cmd)
    if code != 0:
        raise RuntimeError(f"fluidsynth 失败 (退出码 {code}):\n{err}")

    return str(wav_file)


def wav_to_mp3(
    wav_path: str,
    mp3_path: str | None = None,
    bitrate: str = "192k",
    overwrite: bool = True,
) -> str:
    """使用 ffmpeg 将 WAV 文件转码为 MP3。

    Args:
        wav_path: 输入 WAV 文件路径。
        mp3_path: 输出 MP3 文件路径，None 则使用同名的 .mp3 文件。
        bitrate: 编码比特率（如 "192k"、"320k"）。
        overwrite: 是否覆盖已存在的输出文件。

    Returns:
        生成的 MP3 文件路径。

    Raises:
        FileNotFoundError: WAV 文件不存在。
        ValueError: 输入文件不是 .wav 格式。
        RuntimeError: ffmpeg 执行失败。
    """
    wav_file = Path(wav_path)
    if not wav_file.exists():
        raise FileNotFoundError(f"WAV 文件不存在: {wav_file}")
    if wav_file.suffix.lower() != ".wav":
        raise ValueError(f"输入文件必须是 .wav 格式: {wav_file}")

    if mp3_path is None:
        mp3_file = wav_file.with_suffix(".mp3")
    else:
        mp3_file = Path(mp3_path)

    mp3_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y" if overwrite else "-n",  # 强制覆盖 / 不覆盖
        "-i", str(wav_file),
        "-codec:a", "libmp3lame",
        "-b:a", bitrate,
        str(mp3_file),
    ]

    code, _out, err = _run_command_stream(cmd)
    if code != 0:
        raise RuntimeError(f"ffmpeg 失败 (退出码 {code}):\n{err}")

    return str(mp3_file)