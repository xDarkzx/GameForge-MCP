"""Validation helpers for game-audio-mcp tool inputs."""
import os

import soundfile as sf

from game_audio_mcp_shared.constants import (
    MAX_DURATION_SECONDS,
    MAX_PROMPT_LENGTH,
    MAX_STEPS,
    MIN_DURATION_SECONDS,
    MIN_STEPS,
)
from game_audio_mcp_shared.error_codes import ErrorCode, GameAudioMCPError

_ALLOWED_OUTPUT_FORMATS = frozenset({"wav"})  # stable-audio-3's CLI only ever writes via torchaudio.save (wav)
_ALLOWED_MODELS = frozenset(
    {"medium", "small-music", "small-sfx", "medium-base", "small-music-base", "small-sfx-base"}
)


def validate_prompt(prompt: str) -> str:
    if not prompt or not prompt.strip():
        raise GameAudioMCPError(ErrorCode.MISSING_PARAMETER, "prompt must not be empty")
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise GameAudioMCPError(
            ErrorCode.VALUE_OUT_OF_RANGE,
            f"prompt length {len(prompt)} exceeds the {MAX_PROMPT_LENGTH}-character limit",
        )
    return prompt.strip()


def validate_duration(duration: float) -> float:
    if not isinstance(duration, (int, float)) or isinstance(duration, bool):
        raise GameAudioMCPError(ErrorCode.INVALID_PARAMETER, f"duration must be a number, got {duration!r}")
    if duration < MIN_DURATION_SECONDS or duration > MAX_DURATION_SECONDS:
        raise GameAudioMCPError(
            ErrorCode.VALUE_OUT_OF_RANGE,
            f"duration must be between {MIN_DURATION_SECONDS}s and {MAX_DURATION_SECONDS}s, got {duration}",
        )
    return float(duration)


def validate_steps(steps: int) -> int:
    if not isinstance(steps, int) or isinstance(steps, bool):
        raise GameAudioMCPError(ErrorCode.INVALID_PARAMETER, f"steps must be an int, got {steps!r}")
    if steps < MIN_STEPS or steps > MAX_STEPS:
        raise GameAudioMCPError(
            ErrorCode.VALUE_OUT_OF_RANGE, f"steps must be between {MIN_STEPS} and {MAX_STEPS}, got {steps}"
        )
    return steps


def validate_model(model: str) -> str:
    normalized = (model or "").strip().lower()
    if normalized not in _ALLOWED_MODELS:
        raise GameAudioMCPError(
            ErrorCode.INVALID_PARAMETER, f"model {model!r} is not one of {sorted(_ALLOWED_MODELS)}"
        )
    return normalized


def validate_output_format(output_format: str) -> str:
    normalized = (output_format or "").strip().lower()
    if normalized not in _ALLOWED_OUTPUT_FORMATS:
        raise GameAudioMCPError(
            ErrorCode.INVALID_PARAMETER,
            f"output_format {output_format!r} is not one of {sorted(_ALLOWED_OUTPUT_FORMATS)}",
        )
    return normalized


def measure_duration_seconds(audio_path: str) -> float:
    try:
        info = sf.info(audio_path)
        return info.frames / info.samplerate
    except Exception as e:
        raise GameAudioMCPError(
            ErrorCode.SYNTHESIS_FAILED, f"could not read rendered audio at {audio_path}: {e}"
        ) from e


def validate_audio_file_path(path: str, *, param_name: str) -> str:
    if not path or not str(path).strip():
        raise GameAudioMCPError(ErrorCode.MISSING_PARAMETER, f"{param_name} must not be empty")
    resolved = os.path.abspath(path)
    if not os.path.isfile(resolved):
        raise GameAudioMCPError(ErrorCode.FILE_NOT_FOUND, f"{param_name} does not exist: {path}")
    return resolved
