import pytest

from game_audio_mcp_shared.error_codes import GameAudioMCPError
from game_audio_mcp_shared.protocol import (
    validate_duration,
    validate_model,
    validate_output_format,
    validate_prompt,
    validate_steps,
)


def test_validate_prompt_strips_and_returns():
    assert validate_prompt("  dark ambient drone  ") == "dark ambient drone"


def test_validate_prompt_rejects_empty():
    with pytest.raises(GameAudioMCPError):
        validate_prompt("   ")


def test_validate_prompt_rejects_too_long():
    with pytest.raises(GameAudioMCPError):
        validate_prompt("x" * 1001)


def test_validate_duration_accepts_in_range():
    assert validate_duration(45) == 45.0


def test_validate_duration_rejects_out_of_range():
    with pytest.raises(GameAudioMCPError):
        validate_duration(1000)


def test_validate_duration_rejects_non_number():
    with pytest.raises(GameAudioMCPError):
        validate_duration("45")


def test_validate_steps_accepts_in_range():
    assert validate_steps(8) == 8


def test_validate_steps_rejects_out_of_range():
    with pytest.raises(GameAudioMCPError):
        validate_steps(0)


def test_validate_model_normalizes_case():
    assert validate_model("MEDIUM") == "medium"


def test_validate_model_rejects_unknown():
    with pytest.raises(GameAudioMCPError):
        validate_model("large")


def test_validate_output_format_accepts_wav():
    assert validate_output_format("WAV") == "wav"


def test_validate_output_format_rejects_unknown():
    with pytest.raises(GameAudioMCPError):
        validate_output_format("mp3")
