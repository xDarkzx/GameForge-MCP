"""In-memory background job tracking for long-running generation.

Real, confirmed bug this fixes (2026-08-22): generate_game_audio was
originally synchronous (no job/poll), on the assumption that Stable
Audio's diffusion generation is always fast - true up to ~45s duration
in this project's own testing, but false for longer requests: a 180s
clip took ~4 minutes wall-clock, and Claude Desktop's own client-side
tool-call timeout fired and reported "Tool execution failed" before
that finished, even though the generation completed successfully
seconds later (confirmed: the output file existed on disk right after).
Same failure mode already hit and fixed this way for SongForge-MCP's
generate_vocal_track - see its own job_registry.py for the original
incident."""
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Job:
    id: str
    status: str = "running"  # running | complete | error
    progress: float = 0.0
    message: str = "queued"
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)


_RETENTION_SECONDS = 3600.0


class JobRegistry:
    def __init__(self, retention_seconds: float = _RETENTION_SECONDS) -> None:
        self._jobs: dict[str, Job] = {}
        self._retention_seconds = retention_seconds

    def create(self) -> Job:
        self._evict_old_jobs()
        job = Job(id=str(uuid.uuid4()))
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list_all(self) -> list[Job]:
        return sorted(self._jobs.values(), key=lambda job: job.created_at, reverse=True)

    def _evict_old_jobs(self) -> None:
        cutoff = time.time() - self._retention_seconds
        stale_ids = [
            job_id
            for job_id, job in self._jobs.items()
            if job.status != "running" and job.created_at < cutoff
        ]
        for job_id in stale_ids:
            del self._jobs[job_id]
