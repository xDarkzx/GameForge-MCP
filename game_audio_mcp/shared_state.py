"""Single shared instances used by every tool module."""
from game_audio_mcp.audio_client import StableAudioClient
from game_audio_mcp.job_registry import JobRegistry

audio_client = StableAudioClient()
jobs = JobRegistry()
