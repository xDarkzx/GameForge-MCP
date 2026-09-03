<h1 align="center">GameForge-MCP</h1>

<p align="center">
  <strong>Local instrumental &amp; game-BGM generation through the Model Context Protocol</strong>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-green.svg" alt="License" /></a>
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-compatible-purple.svg" alt="MCP Compatible" /></a>
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/version-0.1.0-orange.svg" alt="v0.1.0" /></a>
  <a href="https://github.com/xDarkzx/GameForge-MCP/actions/workflows/ci.yml"><img src="https://github.com/xDarkzx/GameForge-MCP/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://github.com/sponsors/xDarkzx"><img src="https://img.shields.io/badge/Sponsor-30363D?logo=githubsponsors&logoColor=EA4AAA" alt="Sponsor" /></a>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &bull;
  <a href="#why-this-exists">Why This Exists</a> &bull;
  <a href="#real-findings-from-building-this">Real Findings</a> &bull;
  <a href="CHANGELOG.md">Changelog</a> &bull;
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

---

**If this is useful to you, a star helps other people find it** — that's the whole marketing budget for this project. Want to help keep it maintained? Click the **Sponsor** badge up top.

---

GameForge-MCP connects any MCP-compatible AI assistant to [Stable Audio 3](https://github.com/Stability-AI/stable-audio-3) (Medium checkpoint), generating instrumental music and game background audio entirely locally on your own GPU.

**No cloud. Nothing leaves your machine.** Generation runs through a local subprocess call to your own stable-audio-3 checkout — your prompts and audio stay on your computer.

**Fast by design.** Stable Audio 3 is diffusion-based, not autoregressive — a short clip generates in seconds once the checkpoint is cached, dramatically faster than full-song vocal models. Generation time does scale with requested duration though (confirmed: a 180s clip took ~4 minutes), so `generate_game_audio` still returns a job to poll rather than assuming every call is instant.

## Why this exists

This project sits alongside two other local music-generation MCP servers (SongForge-MCP/ACE-Step and heart-mcp/HeartMuLa), both tuned for full vocal songs. Pushing either toward short, pure-instrumental game-BGM work produced noticeably worse results — muddy, artifact-heavy output — confirmed directly in that project's own testing. Stable Audio's training lineage (production-music/stock-audio libraries, overwhelmingly instrumental) is a better architectural fit for this specific job, so it gets its own dedicated server rather than being bolted onto either existing one.

## Quick start

### 1. Get GameForge-MCP

```bash
git clone https://github.com/xDarkzx/GameForge-MCP.git
cd GameForge-MCP
```

### 2. Run the installer

The installer sets up GameForge-MCP's own venv, clones and configures [stable-audio-3](https://github.com/Stability-AI/stable-audio-3) (its `uv`-managed venv, the pinned CUDA torch build, and — with your say-so — a matching Flash Attention 2 wheel), and wires up Claude Desktop. It does **not** download the ~10GB model checkpoint itself — that's gated behind a Hugging Face license you have to accept yourself (step 3 below), and it downloads automatically on first real generation.

**Windows:** either double-click `install.bat` in File Explorer, or keep going in the same terminal from the `git clone` step above:

```
.\install.bat
```

**Linux / macOS:**

```bash
bash install.sh
```

> Requires an NVIDIA GPU — Stable Audio 3 Medium needs Flash Attention 2, which has no CPU or macOS build. On a machine without one, the installer still sets up GameForge-MCP itself but skips the stable-audio-3 stage.

Prefer to do it by hand, or already have your own stable-audio-3 checkout? See the [Installation Guide](docs/INSTALLATION.md) for the full manual steps.

### 3. Accept the model license and authenticate

Accept `stabilityai/stable-audio-3-medium`'s gated license on [Hugging Face](https://huggingface.co/stabilityai/stable-audio-3-medium), then authenticate: `hf auth login`. Both steps require your own Hugging Face account and can't be automated.

### 4. Point Claude Desktop at it

The installer does this for you if you say yes when it asks. To do it manually, or to configure another MCP client:

```json
{
  "mcpServers": {
    "game-audio": {
      "command": "path/to/GameForge-MCP/.venv/Scripts/game-audio-mcp.exe",
      "env": {
        "GAME_AUDIO_STABLE_AUDIO_HOME": "path/to/stable-audio-3"
      }
    }
  }
}
```

## Tools

- `generate_game_audio` — one prompt → a job_id
- `check_job_status` — poll a job started by `generate_game_audio`

See the tool's own docstring (surfaced to any connected AI client) for full parameter docs.

## Real findings from building this

- **One prompt, one cohesive mix.** Describing the whole arrangement in one prompt ("dark swamp drone, mournful viola da gamba melody, tribal drums, buzzing insects, instrumental, cohesive arrangement") sounds far better than generating each instrument separately and mixing the results — independent generations don't share tempo/key/phrase structure and don't musically mesh.
- **No true vertical layering available locally, checked directly.** The one research system built for synchronized multi-stem generation (Stemphonic, Adobe/MIT) has no public code or weights. For adaptive game music, prefer horizontal re-sequencing — a few complete versions at different intensity levels, crossfaded in-engine — over stem-based layering.
- `init_audio` (audio-to-audio) is real and working, but transforms the reference track rather than producing an independent new stem — it doesn't solve the layering problem either.

## Sponsor

If GameForge-MCP has helped with your game audio, consider sponsoring:

<p align="center">
  <a href="https://github.com/sponsors/xDarkzx">
    <img src="https://img.shields.io/badge/Sponsor-30363D?style=for-the-badge&logo=githubsponsors&logoColor=EA4AAA" alt="GitHub Sponsors" />
  </a>
</p>

## License

Apache 2.0 — see [LICENSE](LICENSE).
