"""Single shared StableAudioClient instance used by every tool module."""
from game_audio_mcp.audio_client import StableAudioClient

audio_client = StableAudioClient()
