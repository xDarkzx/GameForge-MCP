"""Auto-discovers and registers every tool module in game_audio_mcp/tools/."""
import importlib
import logging
import pkgutil
import sys

from mcp.server.fastmcp import FastMCP

import game_audio_mcp.tools as tools_package

logger = logging.getLogger(__name__)

_EXPECTED_MODULES = frozenset({"generate_tools"})


def register_all_tools(mcp: FastMCP) -> None:
    registered: list[str] = []
    failures: list[tuple[str, Exception]] = []

    for _finder, name, _ispkg in pkgutil.iter_modules(tools_package.__path__):
        try:
            module = importlib.import_module(f"game_audio_mcp.tools.{name}")
        except Exception as e:
            logger.error("IMPORT FAILED for tool module %s: %s", name, e, exc_info=True)
            sys.stderr.write(f"[game-audio-mcp] FAILED to import tool module '{name}': {e}\n")
            failures.append((name, e))
            continue

        if not hasattr(module, "register"):
            continue

        try:
            module.register(mcp)
            registered.append(name)
        except Exception as e:
            logger.error("REGISTER FAILED for %s: %s", name, e, exc_info=True)
            sys.stderr.write(f"[game-audio-mcp] Tool registration failed for '{name}': {e}\n")
            failures.append((name, e))

    missing = _EXPECTED_MODULES - set(registered) - {n for n, _ in failures}
    if missing:
        sys.stderr.write(f"[game-audio-mcp] WARNING: expected module(s) not found on disk: {sorted(missing)}\n")
    sys.stderr.write(f"[game-audio-mcp] registered {len(registered)} tool module(s)\n")
    if failures:
        sys.stderr.write(f"[game-audio-mcp] {len(failures)} tool module(s) failed to load: {[n for n, _ in failures]}\n")
