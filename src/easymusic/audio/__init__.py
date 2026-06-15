"""音频处理模块的公开接口。"""

from easymusic.audio.converter import midi_to_wav, wav_to_mp3

__all__ = ["midi_to_wav", "wav_to_mp3"]