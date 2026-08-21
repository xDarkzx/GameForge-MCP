"""Instructions loader for game-audio-mcp."""


def load_instructions() -> str:
    return """game-audio-mcp: local instrumental/game-BGM generation via Stable Audio 3

Generates instrumental music and sound design entirely locally on this
machine's own GPU via Stable Audio 3 Medium
(https://github.com/Stability-AI/stable-audio-3) - fast, diffusion-based
(not autoregressive), confirmed sub-second generation once the checkpoint
is cached. This is the right engine for short instrumental/game-BGM work
specifically - SongForge-MCP (ACE-Step) and heart-mcp (HeartMuLa) are
both tuned for full vocal songs and produced noticeably worse results
when pushed toward short pure-instrumental output (confirmed directly in
this project, 2026-08).

ONE PROMPT, ONE FULL COHESIVE MIX - not separate stems. Real, confirmed
finding (2026-08-22): asking for one instrument at a time and mixing the
independent results afterward produces takes that do NOT musically mesh
(no shared tempo/key/phrase structure - each generation is fully
independent). Describing the WHOLE desired arrangement in one prompt
(e.g. "dark swamp drone, mournful viola da gamba melody, tribal drums,
buzzing insects, instrumental, cohesive arrangement") produces a single,
already-coherent result, and sounds dramatically better. Prefer that
over calling this tool once per instrument and mixing after.

NOT capable of true vertical layering (independently toggleable stems
that share one timeline) - no current locally-runnable model does this
(checked directly: Stemphonic, the one real research system built for
synchronized multi-stem generation, is Adobe/MIT research-only, no
public code or weights). init_audio (audio-to-audio) is a real,
available parameter, but it transforms the reference audio rather than
producing an independent new stem - it does not solve the stem-toggling
problem. For a game that truly needs independent on/off layers, generate
the atmospheric bed here, then layer real recorded/composed parts on top
in a DAW - that's actual composition, not AI stems fighting to align.

For adaptive game music instead, prefer horizontal re-sequencing:
generate a few complete, self-contained versions at different intensity
levels (calm/tense/combat) and crossfade between them in the game engine
- this plays to what this tool is actually proven good at.

Available tools:
- generate_game_audio: one prompt -> one instrumental/game-audio track,
  returns immediately (no job/poll needed - this is fast)
"""
