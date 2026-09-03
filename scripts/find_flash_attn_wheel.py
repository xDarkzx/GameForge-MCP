#!/usr/bin/env python3
"""Finds a prebuilt flash-attn wheel matching this machine's Python version
and this project's pinned torch/CUDA combo (torch==2.7.1+cu128 - see
CLAUDE.md and README.md's Quick Start for why this exact pin), from the
community releases at github.com/mjun0812/flash-attention-prebuild-wheels.

Stable Audio 3 Medium requires Flash Attention 2 unconditionally (no CPU
fallback - see stable-audio-3's own README) and isn't declared in its
pyproject.toml, so it's never installed by `uv sync` alone.

Run with the SAME Python version stable-audio-3's venv was created with
(this script only needs sys.version_info + the stdlib - it does not need
torch importable, since the torch/CUDA pin is fixed by this project, not
detected).

Contract, matching this project's other detection scripts (see
game_audio_mcp_shared for the general pattern): prints ONLY the matching
wheel's download URL to stdout and exits 0 on success. Prints nothing to
stdout (diagnostics go to stderr only) and exits non-zero on any failure
(no network, no match, GitHub API error) - callers must branch on exit
code, not by parsing stdout for an error string.
"""
import json
import re
import sys
import urllib.error
import urllib.request

RELEASES_URL = (
    "https://api.github.com/repos/mjun0812/flash-attention-prebuild-wheels/releases?per_page=100"
)

# Pinned to match this project's own torch/CUDA install (see README.md /
# CLAUDE.md) - not detected from the environment, since we're the ones who
# just installed that exact torch build.
TORCH_TAG = "torch2.7"
CUDA_TAG = "cu128"

# flash_attn-2.8.3+cu128torch2.7-cp312-cp312-win_amd64.whl
_ASSET_RE = re.compile(
    r"^flash_attn-(?P<version>[\d.]+)\+"
    r"(?P<cuda>cu\d+)"
    r"(?P<torch>torch[\d.]+)"
    r"-(?P<py_tag>cp\d+)-cp\d+-(?P<platform>.+)\.whl$"
)


def platform_tag() -> str | None:
    """The wheel platform tag for this OS, or None if flash-attn simply
    isn't published for it (macOS: no CUDA, so no flash-attn wheels
    exist there at all - Stable Audio 3 can't run on macOS today)."""
    if sys.platform == "win32":
        return "win_amd64"
    if sys.platform.startswith("linux"):
        return "linux_x86_64"
    return None


def python_tag() -> str:
    return f"cp{sys.version_info.major}{sys.version_info.minor}"


def _version_key(version: str) -> tuple:
    return tuple(int(part) for part in re.findall(r"\d+", version))


def pick_best_wheel(
    asset_names: list[str],
    py_tag: str,
    platform_tag_: str,
    torch_tag: str = TORCH_TAG,
    cuda_tag: str = CUDA_TAG,
) -> str | None:
    """Pure matching function (no network) - given a flat list of asset
    filenames pooled from every release, returns the filename of the
    best (highest flash-attn version) match, or None if nothing matches.
    Separated from fetch_release_assets() so this logic is unit-testable
    without hitting the network."""
    candidates = []
    for name in asset_names:
        m = _ASSET_RE.match(name)
        if not m:
            continue
        if m.group("py_tag") != py_tag:
            continue
        if m.group("platform") != platform_tag_:
            continue
        if m.group("torch") != torch_tag:
            continue
        if m.group("cuda") != cuda_tag:
            continue
        candidates.append((_version_key(m.group("version")), name))

    if not candidates:
        return None
    candidates.sort(key=lambda pair: pair[0])
    return candidates[-1][1]


def fetch_release_assets() -> list[dict]:
    """Returns every asset dict (name + browser_download_url) across all
    releases. A single per_page=100 request covers this repo's full
    release history (~90 releases as of this writing), so no pagination
    is needed."""
    # RELEASES_URL is a hardcoded https:// constant, not user input -
    # ruff's bandit-derived audit can't see that statically.
    req = urllib.request.Request(  # noqa: S310
        RELEASES_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "GameForge-MCP-installer",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        releases = json.loads(resp.read())

    assets = []
    for release in releases:
        assets.extend(release.get("assets", []))
    return assets


def main() -> int:
    plat = platform_tag()
    if plat is None:
        print(
            f"No flash-attn wheels are published for sys.platform={sys.platform!r} "
            "(flash-attn requires CUDA, so no macOS builds exist). "
            "Stable Audio 3 requires an NVIDIA GPU on Windows or Linux.",
            file=sys.stderr,
        )
        return 1

    py_tag = python_tag()

    try:
        assets = fetch_release_assets()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"Could not reach GitHub to look up flash-attn wheels: {e}", file=sys.stderr)
        return 1

    asset_by_name = {a["name"]: a["browser_download_url"] for a in assets if "name" in a}
    best_name = pick_best_wheel(list(asset_by_name), py_tag, plat)

    if best_name is None:
        print(
            f"No prebuilt flash-attn wheel found for {py_tag}/{plat}/"
            f"{TORCH_TAG}/{CUDA_TAG}. See docs/INSTALLATION.md for the "
            "manual build-from-source instructions.",
            file=sys.stderr,
        )
        return 1

    print(f"Matched: {best_name}", file=sys.stderr)
    print(asset_by_name[best_name])
    return 0


if __name__ == "__main__":
    sys.exit(main())
