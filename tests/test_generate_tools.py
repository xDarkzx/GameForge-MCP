import asyncio

import pytest

from game_audio_mcp.shared_state import audio_client as _client
from game_audio_mcp.tools import generate_tools


class _FakeMCP:
    """Captures registered tool functions without needing a real FastMCP
    instance or transport - same technique used to keep these tests fast
    and dependency-free."""

    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


@pytest.fixture
def registered():
    mcp = _FakeMCP()
    generate_tools.register(mcp)
    return mcp.tools


@pytest.mark.asyncio
async def test_generate_game_audio_returns_job_id_immediately(registered, monkeypatch):
    """Real regression test for the 2026-08-22 incident: generate_game_audio
    must return right away regardless of how long the underlying generation
    takes, so Claude Desktop's own client-side tool-call timeout can never
    cut it off."""

    def slow_generate(**kwargs):
        import time

        time.sleep(0.05)  # stands in for a real multi-minute generation
        return {"audio_path": kwargs.get("song_title", "x") + ".wav", "generation_seconds": 0.05}

    monkeypatch.setattr(_client, "generate", slow_generate)
    monkeypatch.setattr(generate_tools, "measure_duration_seconds", lambda path: 1.0)
    monkeypatch.setattr(generate_tools, "play_audio_now", lambda path: None)

    result = await registered["generate_game_audio"](prompt="dark ambient drone, instrumental", ctx=None)
    assert "job_id" in result


@pytest.mark.asyncio
async def test_check_job_status_reflects_completed_job(registered, monkeypatch):
    def fake_generate(**kwargs):
        return {"audio_path": "fake.wav", "generation_seconds": 1.0}

    monkeypatch.setattr(_client, "generate", fake_generate)
    monkeypatch.setattr(generate_tools, "measure_duration_seconds", lambda path: 2.0)
    monkeypatch.setattr(generate_tools, "play_audio_now", lambda path: None)

    result = await registered["generate_game_audio"](prompt="dark ambient drone, instrumental", ctx=None)
    job_id = result["job_id"]

    # Poll with a short wait until it completes - real generation is
    # async (asyncio.create_task), so it may not be done on the first poll.
    for _ in range(50):
        status = await registered["check_job_status"](job_id=job_id, wait_seconds=0.1)
        if status[0]["status"] != "running":
            break
        await asyncio.sleep(0.02)

    assert status[0]["status"] == "complete"
    assert status[0]["audio_path"] == "fake.wav"


@pytest.mark.asyncio
async def test_check_job_status_raises_for_unknown_job_id(registered):
    from game_audio_mcp_shared.error_codes import GameAudioMCPError

    with pytest.raises(GameAudioMCPError):
        await registered["check_job_status"](job_id="does-not-exist")
