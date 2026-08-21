"""Best-effort OS default-app playback - same pattern as SongForge-MCP/
heart-mcp's own media_player.py."""
import os
import platform
import subprocess


def play_audio_now(audio_path: str) -> None:
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(audio_path)  # noqa: S606 - fixed, non-shell OS call, not untrusted input
        elif system == "Darwin":
            subprocess.Popen(["open", audio_path])  # noqa: S603,S607 - "open" is macOS's own fixed launcher, resolved via PATH by design
        else:
            subprocess.Popen(["xdg-open", audio_path])  # noqa: S603,S607 - same as above, the Linux/XDG equivalent
    except Exception:  # noqa: S110 - best-effort convenience only; the real deliverable is the file path already returned, a failed launch must not fail the tool call
        pass
