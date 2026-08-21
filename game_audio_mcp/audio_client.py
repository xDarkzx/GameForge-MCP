"""Drives Stable Audio 3 generation locally via its own CLI
(stable-audio.exe in stable-audio-3's venv). No persistent server -
stable-audio-3 has no server mode, each call is its own short-lived
subprocess.

Real, confirmed bug fixed 2026-08-22: this used to be a synchronous,
no-job/poll design on the assumption that generation is always fast -
true up to ~45s duration in this project's own testing, false beyond
that: a 180s clip took ~4 minutes wall-clock, and Claude Desktop's own
client-side tool-call timeout fired and reported "Tool execution
failed" before that finished, even though the generation completed
successfully seconds later (confirmed: the output file existed on disk
right after). generate_tools.py now wraps this client in the same
job/poll pattern SongForge-MCP/heart-mcp already use for exactly this
reason - see their own history for the original incident this class of
bug traces back to.

_generate_lock serializes calls on this instance - a real risk
surfaced by the same incident: Claude Desktop auto-retried the timed-
out call while the original was still genuinely running server-side,
which without a lock would let two subprocesses race for the same
GPU/VRAM at once.
"""
import os
import subprocess
import threading
import time
import uuid

from game_audio_mcp_shared.constants import Paths, Timeouts, ensure_private_dir
from game_audio_mcp_shared.error_codes import ErrorCode, GameAudioMCPError

_generate_lock = threading.Lock()


class StableAudioClient:
    def __init__(self, stable_audio_home: str | None = None):
        self.stable_audio_home = stable_audio_home if stable_audio_home is not None else Paths.STABLE_AUDIO_HOME

    def _require_configured(self) -> None:
        if not self.stable_audio_home or not os.path.isdir(self.stable_audio_home):
            raise GameAudioMCPError(
                ErrorCode.STABLE_AUDIO_NOT_CONFIGURED,
                "GAME_AUDIO_STABLE_AUDIO_HOME is not set or does not point to a valid "
                "stable-audio-3 checkout. Clone https://github.com/Stability-AI/stable-audio-3.git, "
                "set up its venv (uv sync), and accept stabilityai/stable-audio-3-medium's gated "
                "license on Hugging Face before using this server.",
            )

    def _cli_exe(self) -> str:
        configured = Paths.STABLE_AUDIO_VENV_PYTHON
        candidates = []
        if configured:
            candidates.append(os.path.join(os.path.dirname(configured), "stable-audio.exe"))
        candidates.append(os.path.join(self.stable_audio_home, ".venv", "Scripts", "stable-audio.exe"))
        candidates.append(os.path.join(self.stable_audio_home, ".venv", "bin", "stable-audio"))
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        raise GameAudioMCPError(
            ErrorCode.STABLE_AUDIO_NOT_CONFIGURED,
            f"Could not find stable-audio-3's venv CLI under {self.stable_audio_home}. "
            "Set GAME_AUDIO_STABLE_AUDIO_VENV_PYTHON explicitly if it lives elsewhere.",
        )

    def generate(
        self,
        prompt: str,
        duration: float,
        steps: int,
        cfg_scale: float,
        model: str,
        negative_prompt: str | None = None,
        seed: int = -1,
        init_audio_path: str | None = None,
        init_noise_level: float = 0.9,
        song_title: str | None = None,
    ) -> dict:
        """Runs one Stable Audio 3 generation. Blocking - callers run this
        via asyncio.to_thread, not directly in an async tool handler, so
        the event loop isn't blocked even though this is fast.

        init_audio_path, if given, switches to audio-to-audio mode -
        real, working CLI feature, but note (confirmed this project,
        2026-08-22): it transforms the reference audio rather than
        producing an independent new stem, so it does NOT solve
        "generate a cleanly separate, later-toggleable layer" - that
        remains an open problem, not something this parameter fixes.

        Returns {"audio_path": str, "generation_seconds": float}."""
        self._require_configured()
        cli_exe = self._cli_exe()

        ensure_private_dir(Paths.OUTPUT_DIR)
        job_uid = uuid.uuid4().hex[:12]
        output_path = (
            os.path.join(Paths.OUTPUT_DIR, f"{_slugify_title(song_title)}_{job_uid}.wav")
            if song_title
            else os.path.join(Paths.OUTPUT_DIR, f"{job_uid}.wav")
        )

        args = [
            cli_exe,
            "--model", model,
            "-p", prompt,
            "--duration", str(duration),
            "--steps", str(steps),
            "--cfg-scale", str(cfg_scale),
            "--seed", str(seed),
            "-o", output_path,
        ]
        if negative_prompt:
            args += ["--negative-prompt", negative_prompt]
        if init_audio_path:
            args += ["--init-audio", init_audio_path, "--init-noise-level", str(init_noise_level)]

        start = time.monotonic()
        with _generate_lock:
            try:
                result = subprocess.run(  # noqa: S603 - args built entirely from this class's own resolved cli_exe path and caller-validated values, not passed through a shell
                    args,
                    cwd=self.stable_audio_home,
                    capture_output=True,
                    text=True,
                    timeout=Timeouts.GENERATION,
                )
            except subprocess.TimeoutExpired as e:
                raise GameAudioMCPError(
                    ErrorCode.SUBPROCESS_TIMEOUT,
                    f"Stable Audio generation did not finish within {Timeouts.GENERATION:.0f}s.",
                ) from e
            except OSError as e:
                raise GameAudioMCPError(ErrorCode.SUBPROCESS_FAILED, f"failed to launch stable-audio: {e}") from e

        generation_seconds = time.monotonic() - start
        if result.returncode != 0:
            tail = (result.stdout + result.stderr)[-2000:]
            raise GameAudioMCPError(
                ErrorCode.SYNTHESIS_FAILED,
                f"stable-audio exited with code {result.returncode}. Last output:\n{tail}",
            )

        if not os.path.isfile(output_path):
            raise GameAudioMCPError(
                ErrorCode.SYNTHESIS_FAILED,
                f"stable-audio exited successfully but no output file was found at {output_path}.",
            )

        return {"audio_path": output_path, "generation_seconds": round(generation_seconds, 2)}


def _slugify_title(title: str) -> str:
    slug = "".join(c if c.isalnum() else "-" for c in title.strip().lower())
    while "--" in slug:
        slug = slug.replace("--", "-")
    slug = slug.strip("-")
    return slug[:60] or "untitled"
