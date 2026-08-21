"""game-audio-mcp's core tools - drives audio_client.StableAudioClient,
which runs stable-audio-3's real local CLI.

Job/poll pattern (added 2026-08-22, replacing an original synchronous
design - see audio_client.py's module docstring for the real incident
that caused this): generation duration scales with requested audio
length, and Claude Desktop's own client-side tool-call timeout can fire
before a longer request finishes even though it completes successfully
seconds later. generate_game_audio now returns a job_id immediately;
check_job_status polls, exactly mirroring SongForge-MCP/heart-mcp.
"""
import asyncio

from mcp.server.fastmcp import Context, FastMCP

from game_audio_mcp.media_player import play_audio_now
from game_audio_mcp.shared_state import audio_client as _client, jobs as _jobs
from game_audio_mcp_shared.error_codes import ErrorCode, GameAudioMCPError
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
        ctx: Context,
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
        """Start generating one instrumental/game-BGM track via Stable
        Audio 3, entirely locally. Returns {"job_id": str} immediately -
        poll check_job_status(job_id) to follow it through. Generation
        time scales with duration (seconds-to-minutes, not always
        sub-second) - never assume it's done right away.

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

        job = _jobs.create()

        async def report(fraction: float, message: str) -> None:
            job.progress = fraction
            job.message = message
            try:
                await ctx.report_progress(progress=fraction, total=1.0, message=message)
            except Exception:  # noqa: S110 - best-effort only, see check_job_status's own docs on why this can't be relied on
                pass

        async def run_job() -> None:
            try:
                await report(0.05, "Generating via Stable Audio 3")
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
                job.result = {
                    "audio_path": result["audio_path"],
                    "diagnostics": {
                        "generation_seconds": result["generation_seconds"],
                        "duration_seconds": measured_duration,
                    },
                }
                try:
                    play_audio_now(result["audio_path"])
                except Exception:  # noqa: S110 - best-effort convenience only; the real deliverable (audio_path) is already recorded regardless
                    pass
                job.progress = 1.0
                job.message = "Generation complete"
                job.status = "complete"
            except GameAudioMCPError as e:
                job.error = f"[{e.code.name}] {e.message}"
                job.status = "error"
            except Exception as e:
                job.error = f"{type(e).__name__}: {e}"
                job.status = "error"

        asyncio.create_task(run_job())
        return {"job_id": job.id}

    @mcp.tool(structured_output=False)
    async def check_job_status(job_id: str, wait_seconds: float = 25.0) -> list:
        """Poll a job started by generate_game_audio. Waits up to
        wait_seconds server-side if still running (capped at 25s) -
        call again immediately on "running", no extra delay needed.

        Say almost nothing while polling: one message when it finishes
        or errors. Never narrate individual "still running" polls -
        generation time scales with duration, expect multiple polls for
        anything beyond a short clip.

        Returns a list; first item is a dict with "status" - "running"
        (progress, message), "error" (error), or "complete" (result
        fields, see generate_game_audio's own docs).
        """
        job = _jobs.get(job_id)
        if job is None:
            raise GameAudioMCPError(ErrorCode.FILE_NOT_FOUND, f"no such job_id: {job_id}")

        deadline = asyncio.get_event_loop().time() + max(0.0, min(wait_seconds, 25.0))
        while job.status == "running" and asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(0.5)

        if job.status == "running":
            return [{"status": "running", "progress": round(job.progress, 2), "message": job.message}]
        if job.status == "error":
            return [{"status": "error", "error": job.error}]
        return [{"status": "complete", **job.result}]
