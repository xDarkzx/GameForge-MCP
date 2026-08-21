"""Error taxonomy for game-audio-mcp, independent of songforge_mcp_shared
and heart_mcp_shared - a third fully separate MCP server, same reasoning
as heart_mcp_shared's own docstring for why these aren't unified."""
from enum import Enum


class ErrorCode(Enum):
    MISSING_PARAMETER = 1000
    INVALID_PARAMETER = 1001
    VALUE_OUT_OF_RANGE = 1002
    FILE_NOT_FOUND = 1003
    STABLE_AUDIO_NOT_CONFIGURED = 1004
    SUBPROCESS_FAILED = 1005
    SUBPROCESS_TIMEOUT = 1006
    SYNTHESIS_FAILED = 1007


class GameAudioMCPError(Exception):
    def __init__(self, code: ErrorCode, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code.name}] {message}")
