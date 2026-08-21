# Changelog

All notable changes to GameAudioMCP will be documented in this file.

## [Unreleased]

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
