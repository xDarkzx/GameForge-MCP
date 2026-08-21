import os
import subprocess

import pytest

from game_audio_mcp.audio_client import StableAudioClient, _slugify_title
from game_audio_mcp_shared.error_codes import ErrorCode, GameAudioMCPError


def test_slugify_title_produces_hyphenated_lowercase_slug():
    assert _slugify_title("Swamp Theme!") == "swamp-theme"


def test_slugify_title_returns_untitled_for_punctuation_only():
    assert _slugify_title("!!!") == "untitled"


def test_require_configured_raises_when_home_unset():
    client = StableAudioClient(stable_audio_home="")
    with pytest.raises(GameAudioMCPError) as exc_info:
        client._require_configured()
    assert exc_info.value.code == ErrorCode.STABLE_AUDIO_NOT_CONFIGURED


def test_require_configured_raises_when_home_does_not_exist(tmp_path):
    client = StableAudioClient(stable_audio_home=str(tmp_path / "does-not-exist"))
    with pytest.raises(GameAudioMCPError) as exc_info:
        client._require_configured()
    assert exc_info.value.code == ErrorCode.STABLE_AUDIO_NOT_CONFIGURED


def test_require_configured_passes_when_directory_exists(tmp_path):
    client = StableAudioClient(stable_audio_home=str(tmp_path))
    client._require_configured()


def test_cli_exe_finds_windows_venv_layout(tmp_path):
    scripts_dir = tmp_path / ".venv" / "Scripts"
    scripts_dir.mkdir(parents=True)
    exe = scripts_dir / "stable-audio.exe"
    exe.write_text("")

    client = StableAudioClient(stable_audio_home=str(tmp_path))
    assert client._cli_exe() == str(exe)


def test_cli_exe_raises_when_not_found(tmp_path):
    client = StableAudioClient(stable_audio_home=str(tmp_path))
    with pytest.raises(GameAudioMCPError) as exc_info:
        client._cli_exe()
    assert exc_info.value.code == ErrorCode.STABLE_AUDIO_NOT_CONFIGURED


class _FakeCompletedProcess:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _make_client_with_cli(tmp_path):
    scripts_dir = tmp_path / ".venv" / "Scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "stable-audio.exe").write_text("")
    return StableAudioClient(stable_audio_home=str(tmp_path))


def test_generate_raises_synthesis_failed_on_nonzero_exit(tmp_path, monkeypatch):
    client = _make_client_with_cli(tmp_path)

    def fake_run(*args, **kwargs):
        return _FakeCompletedProcess(returncode=1, stderr="real error from stable-audio")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(GameAudioMCPError) as exc_info:
        client.generate(prompt="dark ambient", duration=10.0, steps=8, cfg_scale=1.0, model="medium")
    assert exc_info.value.code == ErrorCode.SYNTHESIS_FAILED
    assert "real error from stable-audio" in exc_info.value.message


def test_generate_returns_audio_path_on_success(tmp_path, monkeypatch):
    client = _make_client_with_cli(tmp_path)

    def fake_run(args, **kwargs):
        output_path = args[args.index("-o") + 1]
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(b"fake wav bytes")
        return _FakeCompletedProcess(returncode=0, stdout="Saved: " + output_path)

    monkeypatch.setattr(subprocess, "run", fake_run)

    from game_audio_mcp_shared.constants import Paths
    monkeypatch.setattr(Paths, "OUTPUT_DIR", str(tmp_path / "output"))

    result = client.generate(
        prompt="dark ambient", duration=10.0, steps=8, cfg_scale=1.0, model="medium", song_title="Swamp"
    )
    assert os.path.isfile(result["audio_path"])
    assert result["generation_seconds"] >= 0
