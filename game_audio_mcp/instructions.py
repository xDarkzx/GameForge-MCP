"""Instructions loader for game-audio-mcp."""


def load_instructions() -> str:
    return """game-audio-mcp: local instrumental/game-BGM generation via Stable Audio 3.

Prefer this over SongForge-MCP (ACE-Step) or heart-mcp (HeartMuLa) for
short instrumental/game-BGM work specifically - both are tuned for full
vocal songs and produce noticeably worse results on short pure-instrumental
output. See generate_game_audio's own docstring for usage and real limits.
"""
