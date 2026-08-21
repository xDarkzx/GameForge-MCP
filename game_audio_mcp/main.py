import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

# MCP's stdio transport requires UTF-8 JSON-RPC framing. Must happen
# before anything touches stdio. Same fix as SongForge-MCP/heart-mcp's
# own main.py.
for _stream in (sys.stdout, sys.stdin, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from game_audio_mcp.banner import print_ready_banner

print_ready_banner("stable-audio-3-medium")

from mcp.server.fastmcp import FastMCP  # noqa: E402

from game_audio_mcp.instructions import load_instructions  # noqa: E402
from game_audio_mcp.tool_registry import register_all_tools  # noqa: E402


@asynccontextmanager
async def _lifespan(_app: FastMCP) -> AsyncIterator[dict]:
    """No warm-up step: stable-audio-3 has no persistent server to
    pre-launch (see audio_client.py's module docstring) - every
    generation is its own short-lived subprocess."""
    yield {}


mcp = FastMCP("GameAudioMCP", instructions=load_instructions(), lifespan=_lifespan)
register_all_tools(mcp)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
