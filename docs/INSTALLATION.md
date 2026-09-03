# Installation Guide

## What `install.bat` / `install.sh` do

1. Check for Python 3.10+ (installs it for you on Windows if missing; on Linux/macOS, prints the right package-manager command).
2. Check for [`uv`](https://docs.astral.sh/uv/) (installs it via the official installer if missing) — `stable-audio-3` is `uv`-managed, unlike GameForge-MCP's own plain-venv setup.
3. Create GameForge-MCP's own `.venv` and install this package in editable mode.
4. Check for ~15GB free disk space.
5. Check for an NVIDIA GPU (`nvidia-smi`). **Stable Audio 3 Medium requires an NVIDIA GPU** — Flash Attention 2 is a hard requirement with no CPU fallback and no macOS build. If none is found, the installer still finishes setting up GameForge-MCP itself but skips steps 6-7 below.
6. Clone `stable-audio-3` (default: a sibling folder, `../stable-audio-3`, unless `GAME_AUDIO_STABLE_AUDIO_HOME` is already set), create its own `uv`-managed venv, and install its dependencies with the CUDA-enabled torch build (`torch==2.7.1+cu128`).
7. Offer to install a matching prebuilt Flash Attention 2 wheel — auto-detected (matched to your Python version, this project's pinned `torch==2.7.1+cu128`, and your OS) from the community [`flash-attention-prebuild-wheels`](https://github.com/mjun0812/flash-attention-prebuild-wheels) releases, or you can skip it and do this step manually (see below).
8. Offer to configure Claude Desktop's `claude_desktop_config.json` with a `game-audio` MCP server entry (existing configs are backed up to `.bak`, never overwritten silently).

**Deliberately not automated**, in both scripts:

- **Accepting the gated Hugging Face license** for `stabilityai/stable-audio-3-medium` — this requires clicking "Agree" on huggingface.co while logged into your own account; there's no API for it.
- **`hf auth login`** — needs a token you paste in interactively.
- **The ~10GB checkpoint download itself** — happens automatically on the first real `generate_game_audio` call, not during installation.
- **Persisting environment variables on Linux/macOS** — there's no cross-shell equivalent of Windows' `setx`. `install.sh` prints the `export` line for you to add to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.) rather than editing it for you.

## Manual installation

If you'd rather not run the installer, or already have your own `stable-audio-3` checkout:

1. Clone and set up [stable-audio-3](https://github.com/Stability-AI/stable-audio-3) separately:
   ```bash
   git clone https://github.com/Stability-AI/stable-audio-3.git
   cd stable-audio-3
   uv venv
   # Install CUDA torch matching your GPU before uv sync - the project's
   # own CUDA index is Linux-gated, so a plain `uv sync` on Windows
   # silently installs CPU-only torch.
   uv pip install torch==2.7.1+cu128 torchaudio==2.7.1+cu128 --index-url https://download.pytorch.org/whl/cu128
   uv sync --extra ui --no-install-package torch --no-install-package torchaudio
   ```
2. Install Flash Attention 2 (required — see below).
3. Accept `stabilityai/stable-audio-3-medium`'s gated license on [Hugging Face](https://huggingface.co/stabilityai/stable-audio-3-medium), then authenticate: `hf auth login`.
4. Install this server: `pip install -e .` (from the `GameForge-MCP` folder).
5. Point Claude Desktop (or any MCP client) at it — see the README's [Quick Start](../README.md#quick-start) for the exact config JSON.

## Flash Attention 2 (required)

Stable Audio 3 Medium requires Flash Attention 2 — there is no CPU fallback, and no wheels are published for macOS (it needs CUDA).

**Prebuilt wheel (fast, no compilation)** — browse [mjun0812/flash-attention-prebuild-wheels](https://github.com/mjun0812/flash-attention-prebuild-wheels/releases) for a filename matching your CUDA version, PyTorch version, and Python version (e.g. `flash_attn-2.8.3+cu128torch2.7-cp312-cp312-win_amd64.whl` = CUDA 12.8, PyTorch 2.7, Python 3.12, Windows), then from inside your `stable-audio-3` checkout:

```bash
uv pip install <wheel URL>
```

`install.bat`/`install.sh`'s auto-detect option (`scripts/find_flash_attn_wheel.py`) does exactly this search automatically, matched against this project's pinned `torch==2.7.1+cu128`.

**Build from source**, if no prebuilt wheel matches your setup:

```bash
uv pip install ninja
FLASH_ATTENTION_SKIP_CUDA_BUILD=FALSE \
FLASH_ATTENTION_FORCE_BUILD=TRUE \
TORCH_CUDA_ARCH_LIST="8.9" \
MAX_JOBS=8 \
.venv/bin/pip3 install flash-attn --no-build-isolation --no-binary flash-attn \
    --force-reinstall --no-cache-dir --no-deps
```

- `TORCH_CUDA_ARCH_LIST` — your GPU's compute capability: `8.0` (A100), `8.6` (A10/RTX 3090), `8.9` (L4/RTX 4090), `9.0` (H100/H200).
- `MAX_JOBS` — parallel compile jobs; 4–8 is typical, reduce if you run out of RAM during compilation.

**Note:** `flash-attn` isn't declared in `stable-audio-3`'s `pyproject.toml`, so a plain `uv sync` will remove it later. Use `uv sync --inexact` for any subsequent syncs.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `command not found: game-audio-mcp` | Run the installer again, or manually: `pip install -e .` from the `GameForge-MCP` folder. |
| Claude Desktop doesn't pick up the config | If you're on the Microsoft Store build of Claude Desktop, its config lives in a sandboxed `LOCALAPPDATA\Packages\Claude_*\LocalCache\Roaming\Claude` path, not the normal `%APPDATA%\Claude` — the installer detects this automatically, but a manual edit needs to target the right one. |
| `uv sync` installs CPU-only torch on Windows | Expected — `stable-audio-3`'s own CUDA index is Linux-gated. Always install the pinned CUDA torch build (`torch==2.7.1+cu128`) *before* `uv sync`, with `--no-install-package torch --no-install-package torchaudio` on the sync itself. |
| `ImportError: flash_attn` or generation fails immediately | Flash Attention 2 isn't installed — see above. This is a hard requirement, not optional. |
| No NVIDIA GPU / on macOS | Stable Audio 3 Medium can't run — there's no CPU or macOS build. GameForge-MCP itself still installs, but `generate_game_audio` calls will fail. |
| Disk space check fails | The checkpoint is ~10GB; the installer requires ~15GB free headroom. Free up space and re-run. |

## Environment variables

| Variable | Purpose |
|---|---|
| `GAME_AUDIO_STABLE_AUDIO_HOME` | Path to your `stable-audio-3` checkout. Set automatically by the installer (`setx` on Windows, printed as an `export` line on Linux/macOS) and passed explicitly in the generated Claude Desktop config. |
