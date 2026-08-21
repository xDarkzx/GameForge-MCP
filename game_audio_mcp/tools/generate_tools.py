"""game-audio-mcp's core tool - drives audio_client.StableAudioClient,
which runs stable-audio-3's real local CLI (confirmed working end-to-end
on this project's hardware, 2026-08-22).
"""
import asyncio

from mcp.server.fastmcp import FastMCP

from game_audio_mcp.media_player import play_audio_now
from game_audio_mcp.shared_state import audio_client as _client
from game_audio_mcp_shared.protocol import (
    measure_duration_seconds,
    validate_audio_file_path,
    validate_duration,
    validate_model,
    validate_prompt,
    validate_steps,
)


def register(mcp: FastMCP):
    @mcp.tool(structured_output=False)
    async def generate_game_audio(
        prompt: str,
        duration: float = 45.0,
        steps: int = 8,
        cfg_scale: float = 1.0,
        model: str = "medium",
        negative_prompt: str | None = None,
        seed: int = -1,
        init_audio_path: str | None = None,
        init_noise_level: float = 0.9,
        song_title: str | None = None,
    ) -> dict:
        """Generate one instrumental/game-BGM track via Stable Audio 3,
        entirely locally. Returns the finished result directly -
        {"audio_path", "diagnostics": {"generation_seconds",
        "duration_seconds"}} - not a job_id; this is fast, nothing to
        poll for.

        Describe the WHOLE arrangement in ONE prompt (genre, all
        instruments, mood, atmosphere together) - do not call this once
        per instrument and mix results yourself; independent generations
        don't share tempo/key and won't mesh. Name specific
        instruments/techniques for real control, never a real artist.

        Cannot produce independently toggleable stems sharing one
        timeline ("vertical layering") - no locally-runnable model does.
        For adaptive intensity, generate a few complete versions and
        crossfade between them in-engine instead.

        Args:
            duration: Seconds, 1-380.
            steps: Diffusion steps (default 8 - Stable Audio's own tuned
                default; raise only if a result sounds under-baked).
            cfg_scale: Guidance scale, default 1.0 (use ~7.0 only for a
                "-base" model variant).
            model: "medium" (default), "small-music", or "small-sfx"
                (sound EFFECTS only - not music, don't use for BGM).
                "-base" variants also exist.
            negative_prompt: What to avoid, e.g. "vocals, singing".
            seed: -1 = random (default).
            init_audio_path: Audio-to-audio mode. Transforms the
                reference rather than producing an independent stem -
                not a fix for stem extraction.
            init_noise_level: 0.0-1.0, default 0.9 (init_audio_path only).
            song_title: Optional, used in the output filename.
        """
        prompt = validate_prompt(prompt)
        duration = validate_duration(duration)
        steps = validate_steps(steps)
        model = validate_model(model)
        if init_audio_path:
            init_audio_path = validate_audio_file_path(init_audio_path, param_name="init_audio_path")

        result = await asyncio.to_thread(
            _client.generate,
            prompt=prompt,
            duration=duration,
            steps=steps,
            cfg_scale=cfg_scale,
            model=model,
            negative_prompt=negative_prompt,
            seed=seed,
            init_audio_path=init_audio_path,
            init_noise_level=init_noise_level,
            song_title=song_title,
        )
        measured_duration = await asyncio.to_thread(measure_duration_seconds, result["audio_path"])

        try:
            play_audio_now(result["audio_path"])
        except Exception:  # noqa: S110 - best-effort convenience only; the real deliverable (audio_path) is already returned regardless
            pass

        return {
            "audio_path": result["audio_path"],
            "diagnostics": {
                "generation_seconds": result["generation_seconds"],
                "duration_seconds": measured_duration,
            },
        }
