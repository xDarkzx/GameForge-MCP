"""Startup console output for game-audio-mcp.

MUST write to stderr only, never stdout - stdout is the JSON-RPC channel
for this stdio MCP server. Same reason as SongForge-MCP/heart-mcp's own
banner.py.
"""
import sys


def print_ready_banner(model_label: str) -> None:
    border = "=" * 60
    sys.stderr.write(
        f"\n{border}\n"
        f"  GameAudio MCP Server is ready\n"
        f"  Engine: Stable Audio 3 ({model_label})\n"
        f"{border}\n\n"
    )
    sys.stderr.flush()
