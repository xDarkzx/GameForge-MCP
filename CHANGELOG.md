# Changelog

All notable changes to GameForge-MCP will be documented in this file.

## [Unreleased]

### Fixed

- **`generate_game_audio` could report "Tool execution failed" for a
  generation that actually succeeded seconds later** - real, confirmed
  incident, not hypothetical. It shipped synchronous (no job/poll) on
  the assumption that generation is always fast; true up to ~45s
  duration in this project's own testing, false beyond that - a 180s
  clip took ~4 minutes wall-clock, well past Claude Desktop's own
  client-side tool-call timeout, which reported failure and then
  auto-retried while the original call was still genuinely running.
  Converted to the same job/poll pattern SongForge-MCP/heart-mcp
  already use (`generate_game_audio` now returns `{"job_id"}`
  immediately; poll with the new `check_job_status`).
- **Two overlapping retries could crash with a real Windows access
  violation (exit code `0xC0000005`)**, not a graceful error - two
  `stable-audio.exe` processes racing for the same GPU/VRAM at once on
  this project's "marginal" 12GB VRAM tier. `StableAudioClient.generate`
  now serializes all calls on a process-local lock, so a retry firing
  while a previous call is still in flight blocks instead of racing it.

## [0.1.0] - 2026-08-22

### Added

- Initial release: `generate_game_audio` tool, driving Stable Audio 3
  Medium locally via subprocess. No job/poll pattern - generation is
  diffusion-based and confirmed sub-second-to-seconds once the
  checkpoint is cached, unlike this project's other two engines
  (SongForge-MCP/ACE-Step, heart-mcp/HeartMuLa), which both take many
  minutes per generation.
- Real, confirmed finding baked into `generate_game_audio`'s own
  docstring: describing a whole arrangement in one prompt produces a
  musically coherent result; generating instruments separately and
  mixing them afterward does not - independent generations don't share
  tempo/key/phrase structure.
- Real, confirmed limitation documented rather than hidden: no true
  vertical layering (independently toggleable stems sharing one
  timeline) is available from any currently locally-runnable model -
  checked directly against Stemphonic, the one research system built
  for synchronized multi-stem generation (Adobe/MIT, no public code or
  weights).
