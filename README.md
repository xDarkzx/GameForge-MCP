<h1 align="center">GameAudioMCP</h1>

<p align="center">
  <strong>Local instrumental &amp; game-BGM generation through the Model Context Protocol</strong>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-green.svg" alt="License" /></a>
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-compatible-purple.svg" alt="MCP Compatible" /></a>
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/version-0.1.0-orange.svg" alt="v0.1.0" /></a>
  <a href="https://github.com/xDarkzx/GameAudioMCP/actions/workflows/ci.yml"><img src="https://github.com/xDarkzx/GameAudioMCP/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#why-this-exists">Why This Exists</a> &bull;
  <a href="#real-findings-from-building-this">Real Findings</a> &bull;
  <a href="CHANGELOG.md">Changelog</a> &bull;
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

---

GameAudioMCP connects any MCP-compatible AI assistant to [Stable Audio 3](https://github.com/Stability-AI/stable-audio-3) (Medium checkpoint), generating instrumental music and game background audio entirely locally on your own GPU.

**No cloud. Nothing leaves your machine.** Generation runs through a local subprocess call to your own stable-audio-3 checkout — your prompts and audio stay on your computer.

**Fast by design.** Stable Audio 3 is diffusion-based, not autoregressive — generation is confirmed sub-second to a few seconds once the checkpoint is cached, dramatically faster than full-song vocal models. There's no job/poll pattern here because there's nothing worth polling for.

## Why this exists

This project sits alongside two other local music-generation MCP servers (SongForge-MCP/ACE-Step and heart-mcp/HeartMuLa), both tuned for full vocal songs. Pushing either toward short, pure-instrumental game-BGM work produced noticeably worse results — muddy, artifact-heavy output — confirmed directly in that project's own testing. Stable Audio's training lineage (production-music/stock-audio libraries, overwhelmingly instrumental) is a better architectural fit for this specific job, so it gets its own dedicated server rather than being bolted onto either existing one.

## Quick start

1. Clone and set up [stable-audio-3](https://github.com/Stability-AI/stable-audio-3) separately:
   ```bash
   git clone https://github.com/Stability-AI/stable-audio-3.git
   cd stable-audio-3
   uv venv
   # Install CUDA torch matching your GPU before uv sync - the project's
   # own CUDA index is Linux-gated, so a plain `uv sync` on Windows
   # silently installs CPU-only torch. e.g.:
   uv pip install torch==2.7.1+cu128 torchaudio==2.7.1+cu128 --index-url https://download.pytorch.org/whl/cu128
   uv sync --extra ui --no-install-package torch --no-install-package torchaudio
   # Then a matching Windows flash-attn wheel for your torch/CUDA/Python
   # combo (see https://github.com/mjun0812/flash-attention-prebuild-wheels)
   ```
2. Accept `stabilityai/stable-audio-3-medium`'s gated license on [Hugging Face](https://huggingface.co/stabilityai/stable-audio-3-medium), then authenticate: `hf auth login`.
3. Install this server: `pip install -e .`
4. Point Claude Desktop (or any MCP client) at it:
   ```json
   {
     "mcpServers": {
       "game-audio": {
         "command": "path/to/GameAudioMCP/.venv/Scripts/game-audio-mcp.exe",
         "env": {
           "GAME_AUDIO_STABLE_AUDIO_HOME": "path/to/stable-audio-3"
         }
       }
     }
   }
   ```

## Tools

- `generate_game_audio` — one prompt → one instrumental/game-audio track, returns immediately (no job/poll)

See the tool's own docstring (surfaced to any connected AI client) for full parameter docs.

## Real findings from building this

- **One prompt, one cohesive mix.** Describing the whole arrangement in one prompt ("dark swamp drone, mournful viola da gamba melody, tribal drums, buzzing insects, instrumental, cohesive arrangement") sounds far better than generating each instrument separately and mixing the results — independent generations don't share tempo/key/phrase structure and don't musically mesh.
- **No true vertical layering available locally, checked directly.** The one research system built for synchronized multi-stem generation (Stemphonic, Adobe/MIT) has no public code or weights. For adaptive game music, prefer horizontal re-sequencing — a few complete versions at different intensity levels, crossfaded in-engine — over stem-based layering.
- `init_audio` (audio-to-audio) is real and working, but transforms the reference track rather than producing an independent new stem — it doesn't solve the layering problem either.

## License

Apache 2.0 — see [LICENSE](LICENSE).
