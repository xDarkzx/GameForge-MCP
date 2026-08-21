# Contributing to GameAudioMCP

Thanks for your interest in contributing! Every PR — tool, bug fix, doc, or test — is welcome.

## Development setup

```bash
git clone https://github.com/xDarkzx/GameAudioMCP.git
cd GameAudioMCP
pip install -e ".[dev]"
```

This installs `game-audio-mcp` in editable mode along with `pytest` / `pytest-asyncio` / `ruff` for tests and linting.

You'll also need [stable-audio-3](https://github.com/Stability-AI/stable-audio-3) set up separately (its own venv, its own gated checkpoint download) — this server drives it via subprocess, it isn't a dependency of this package. See `README.md` for setup steps and `GAME_AUDIO_STABLE_AUDIO_HOME`.

## Running tests

```bash
pytest tests/ -x -q
```

All tests must pass before submitting a PR. Note: the test suite mocks `subprocess`/the CLI entirely (see `tests/test_audio_client.py`) — it does not require stable-audio-3 or a GPU to run.

## Running lint

```bash
ruff check .
```

CI runs this too — it only checks for real bugs (unused/undefined names, etc.) and security-relevant patterns, not style or formatting, so it isn't fussy about how you write code. Must pass clean before submitting a PR.

## Adding a new tool

1. Add a new `*_tools.py` file in `game_audio_mcp/tools/`. The tool registry auto-discovers any module that defines `register(mcp)`.
2. Inside `register(mcp)`, define your tool with the `@mcp.tool()` decorator.
3. Validate inputs via `game_audio_mcp_shared/protocol.py`'s validators (or add new ones there) before dispatching to `audio_client.StableAudioClient`.
4. This server has no job/poll pattern by design — generation is fast enough (diffusion-based, sub-second-to-seconds once cached) that a tool can block directly. Don't add a job queue unless a genuinely slow operation needs it.

## Code style

- Python 3.10+ (type hints on public surfaces).
- No comments or docstrings on obvious code — well-named identifiers are enough.
- Keep input validation explicit; error handling should mention the specific bad value.

## Security

- Validate every parameter before dispatch — range-check numeric inputs, length-cap strings, absolute-only for file paths (`init_audio_path`).
- Never commit API keys, tokens, or credentials (including Hugging Face tokens needed for the gated checkpoint). Secrets go in `.env` (already gitignored) or your own `hf auth login` cache, never this repo.

## Pull requests

- Keep PRs focused on a single change.
- Include tests for new tools.
- Make sure all existing tests still pass, and `ruff check .` is clean.
- Describe what your change does and why.
- Update `CHANGELOG.md` under the current unreleased section.

## Reporting issues

Open an issue on GitHub with:

- What you expected to happen.
- What actually happened.
- Steps to reproduce.
- Your OS, Python version, and GPU/VRAM.
- Relevant stderr output from the MCP server (the `GameAudio MCP Server is ready` banner lines).
