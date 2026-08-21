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
        run entirely locally on this machine's own GPU. Returns the
        finished result directly, {"audio_path": str, "diagnostics":
        {"generation_seconds", "duration_seconds"}} - NOT a job_id to
        poll. This is fast (diffusion-based, confirmed well under a
        second of actual compute once the checkpoint is cached) - unlike
        SongForge-MCP/heart-mcp's job/poll pattern, there's nothing to
        wait on.

        Describe the WHOLE arrangement in ONE prompt - do not call this
        once per instrument and mix the results yourself. Real, confirmed
        finding (2026-08-22): independently-generated instrument layers
        do not share tempo/key/phrase structure and do not musically mesh
        when mixed afterward. One rich prompt describing every element
        together (e.g. "dark swamp drone, mournful viola da gamba
        melody, tribal drums, buzzing insects, instrumental, cohesive
        arrangement") produces a single coherent result and sounds much
        better than combining separate calls.

        This tool cannot produce independently toggleable layers sharing
        one timeline (true "vertical layering") - no currently
        locally-runnable model does (checked directly: the one research
        system built for this, Stemphonic, has no public code/weights).
        For adaptive game music, prefer generating a few complete
        versions at different intensity levels and crossfading between
        them in-engine, rather than asking for separate mixable stems.

        Args:
            prompt: Full description of the desired instrumental piece -
                genre, instruments, mood, atmosphere, all together. Name
                specific instruments/techniques for real control (e.g.
                "sustained bowed strings, no plucking" avoided a generic
                "Arabian market" cliche in this project's own testing).
                Never name a real artist - describe their sound instead.
            duration: Seconds, 1-380 (Medium's own documented ceiling).
            steps: Diffusion steps, default 8 (Stable Audio's own
                default - higher is slower but not necessarily better
                for this model; only raise it if a result sounds
                under-baked).
            cfg_scale: Classifier-free guidance scale, default 1.0.
                Stable Audio's own docs suggest ~7.0 for "-base" model
                variants specifically, not the default tuned ones.
            model: One of "medium" (default, best quality, ~6.5GB VRAM),
                "small-music" (lighter, CPU-capable), "small-sfx" (sound
                EFFECTS only - footsteps/impacts/UI, not music - do not
                use this for background music), or their "-base" variants.
            negative_prompt: Optional - describe what to avoid (e.g.
                "vocals, singing" to reinforce instrumental-only).
            seed: -1 for random (default). Fix a seed to reproduce or
                nudge-iterate on a specific result.
            init_audio_path: Optional local audio file for audio-to-audio
                mode. Real caveat, confirmed this project: this
                TRANSFORMS the reference audio rather than producing an
                independent new stem - it does not solve "generate a
                separate layer that matches an existing track." Useful
                for genuine audio-to-audio variation, not for stem
                extraction.
            init_noise_level: 0.0-1.0, default 0.9. Only used when
                init_audio_path is given - higher values diverge further
                from the reference.
            song_title: Optional name for this track, used in the output
                filename instead of a bare id.

        Raises GameAudioMCPError - STABLE_AUDIO_NOT_CONFIGURED,
        FILE_NOT_FOUND (bad init_audio_path), SUBPROCESS_TIMEOUT,
        SUBPROCESS_FAILED, SYNTHESIS_FAILED.
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
