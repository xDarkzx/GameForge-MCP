"""Shared constants for game-audio-mcp."""
import os


def ensure_private_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _default_output_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "game_audio_mcp", "output")


class Paths:
    # Root of the stable-audio-3 checkout (git clone of
    # Stability-AI/stable-audio-3) - must be set at install time. Not
    # pip-installable as a standalone tool; points at a real local clone
    # with its own uv-managed venv.
    STABLE_AUDIO_HOME = os.environ.get("GAME_AUDIO_STABLE_AUDIO_HOME", "")
    # stable-audio-3's own venv python - generation always runs through
    # this interpreter (via subprocess), never this server's own venv,
    # since stable-audio-3's dependencies (torch, flash-attn, etc.) are
    # deliberately NOT installed in this server's own venv.
    STABLE_AUDIO_VENV_PYTHON = os.environ.get("GAME_AUDIO_STABLE_AUDIO_VENV_PYTHON", "")

    OUTPUT_ROOT = os.environ.get("GAME_AUDIO_OUTPUT_DIR", _default_output_root())
    OUTPUT_DIR = os.path.join(OUTPUT_ROOT, "renders")


class Timeouts:
    # Real, measured on this project's own hardware (RTX 5070, 2026-08-22):
    # once the Medium checkpoint is cached locally, a 45s generation at
    # the default 8 diffusion steps takes well under a second of actual
    # compute - dramatically faster than either other engine in this
    # project (ACE-Step, HeartMuLa), since this is diffusion-based, not
    # autoregressive token-by-token. This generous ceiling exists almost
    # entirely for the one slow case: the very first call ever, if the
    # ~8GB+ Medium checkpoint isn't cached yet and needs to download from
    # a gated Hugging Face repo (real auth + real multi-GB pull).
    GENERATION = float(os.environ.get("GAME_AUDIO_GENERATION_TIMEOUT", "600"))


MAX_PROMPT_LENGTH = 1000
MIN_DURATION_SECONDS = 1.0
MAX_DURATION_SECONDS = 380.0  # Medium's own documented ceiling
MIN_STEPS = 1
MAX_STEPS = 100
