#!/usr/bin/env bash
# GameForge-MCP installer - Linux/macOS. Mirrors install.bat's steps.
#
# Two things are deliberately NOT automated here, matching SongForge-MCP's
# own install.sh for the same reasons:
#   1. Installing Python itself - package managers differ too much
#      (apt/dnf/pacman/brew) to do this unattended and safely.
#   2. Persisting environment variables - there is no cross-shell
#      equivalent of Windows' `setx`. This prints the export lines for you
#      to add to your shell profile rather than editing it for you.
#
# GPU note: Stable Audio 3 Medium requires Flash Attention 2 unconditionally
# (no CPU fallback exists, per stable-audio-3's own README), and no
# flash-attn wheels are published for macOS at all (it needs CUDA). So on
# any machine without an NVIDIA GPU - including all of macOS - this script
# still installs GameForge-MCP itself, but skips the stable-audio-3 setup
# entirely rather than installing something that can't work.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
PROJECT_ROOT="$(pwd)"

echo "============================================================"
echo "GameForge-MCP installer"
echo "============================================================"

# ---- Step 1: Python check ----
echo "[1/8] Checking Python..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found on PATH."
    case "$(uname -s)" in
        Linux)
            if command -v apt-get >/dev/null 2>&1; then
                echo "Install it with: sudo apt-get install -y python3 python3-venv python3-pip"
            elif command -v dnf >/dev/null 2>&1; then
                echo "Install it with: sudo dnf install -y python3 python3-pip"
            elif command -v pacman >/dev/null 2>&1; then
                echo "Install it with: sudo pacman -S python python-pip"
            else
                echo "Install Python 3.10+ using your distro's package manager, then re-run this script."
            fi
            ;;
        Darwin)
            echo "Install it with: brew install python@3.12"
            echo "(or from https://python.org if you don't use Homebrew)"
            ;;
        *)
            echo "Install Python 3.10+ manually, then re-run this script."
            ;;
    esac
    exit 1
fi

PY_OK=$(python3 -c 'import sys; print(1 if sys.version_info >= (3, 10) else 0)')
if [ "$PY_OK" != "1" ]; then
    echo "python3 is older than 3.10 ($(python3 --version)). Install 3.10+ and re-run."
    exit 1
fi
echo "  Python OK."

# ---- Step 2: uv bootstrap (stable-audio-3 is uv-managed, unlike this
# server's own venv) ----
echo
echo "[2/8] Checking uv..."
if ! command -v uv >/dev/null 2>&1; then
    echo "  uv not found on PATH. Installing via the official installer..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    if ! command -v uv >/dev/null 2>&1; then
        echo "uv install did not put it on PATH for this session."
        echo "Open a new shell (or source your profile), then re-run this script."
        exit 1
    fi
fi
echo "  uv OK."

# ---- Step 3: this server's own venv (lightweight - no torch, see
# pyproject.toml: mcp[cli] + soundfile only) ----
echo
echo "[3/8] Setting up GameForge-MCP's own venv..."
python3 -m venv .venv
".venv/bin/python" -m pip install -e .
echo "  GameForge-MCP installed."

# ---- Step 4: disk space check (checkpoint is ~10GB, leave headroom) ----
echo
echo "[4/8] Checking disk space..."
REQUIRED_GB=15
AVAILABLE_KB=$(df -Pk . | awk 'NR==2 {print $4}')
AVAILABLE_GB=$((AVAILABLE_KB / 1024 / 1024))
if [ "$AVAILABLE_GB" -lt "$REQUIRED_GB" ]; then
    echo "Not enough free disk space to continue safely (need ~${REQUIRED_GB}GB free, found ~${AVAILABLE_GB}GB)."
    exit 1
fi
echo "  ${AVAILABLE_GB}GB free."

# ---- Step 5: NVIDIA GPU check - Stable Audio 3 Medium requires Flash
# Attention 2 unconditionally (no CPU fallback, no macOS wheels since
# flash-attn needs CUDA). Without an NVIDIA GPU there's nothing useful
# steps 6-7 can do.
echo
echo "[5/8] Checking for an NVIDIA GPU..."
SKIP_STABLE_AUDIO=""
if ! command -v nvidia-smi >/dev/null 2>&1; then
    echo
    echo "No NVIDIA GPU detected (nvidia-smi not found). Stable Audio 3"
    echo "requires an NVIDIA GPU - there is no CPU fallback, and no macOS"
    echo "build exists. Skipping the stable-audio-3 setup (steps 6-7);"
    echo "GameForge-MCP itself will still be installed and configured below,"
    echo "but generation will not work until you run this installer again"
    echo "on a machine with an NVIDIA GPU."
    SKIP_STABLE_AUDIO=1
else
    echo "  NVIDIA GPU detected."
fi

STABLE_AUDIO_DEST=""
if [ -z "$SKIP_STABLE_AUDIO" ]; then
    # ---- Step 6: stable-audio-3 checkout + its own uv-managed venv ----
    echo
    echo "[6/8] Setting up stable-audio-3..."

    if [ -z "${GAME_AUDIO_STABLE_AUDIO_HOME:-}" ]; then
        STABLE_AUDIO_DEST="$(pwd)/../stable-audio-3"
        echo "  GAME_AUDIO_STABLE_AUDIO_HOME not set - using $STABLE_AUDIO_DEST"
        if [ ! -d "$STABLE_AUDIO_DEST" ]; then
            git clone https://github.com/Stability-AI/stable-audio-3.git "$STABLE_AUDIO_DEST"
        else
            echo "  Found an existing checkout at $STABLE_AUDIO_DEST - reusing it."
        fi
    else
        STABLE_AUDIO_DEST="$GAME_AUDIO_STABLE_AUDIO_HOME"
        echo "  Using existing GAME_AUDIO_STABLE_AUDIO_HOME: $STABLE_AUDIO_DEST"
    fi

    pushd "$STABLE_AUDIO_DEST" >/dev/null
    uv venv
    # Pinned exactly, matching install.bat and this project's flash-attn
    # wheel search (scripts/find_flash_attn_wheel.py) - do not let this float.
    if ! uv pip install torch==2.7.1+cu128 torchaudio==2.7.1+cu128 --index-url https://download.pytorch.org/whl/cu128; then
        echo "torch install failed - see docs/INSTALLATION.md for alternatives. Aborting."
        popd >/dev/null
        exit 1
    fi
    if ! uv sync --extra ui --no-install-package torch --no-install-package torchaudio; then
        echo "uv sync failed - see docs/INSTALLATION.md."
        popd >/dev/null
        exit 1
    fi
    echo "  stable-audio-3 dependencies installed."

    # ---- Step 7: Flash Attention 2 (required) ----
    echo
    echo "[7/8] Flash Attention 2 setup (required)..."
    echo "  Stable Audio 3 Medium requires Flash Attention 2 to run."
    read -r -p "  [a]uto-detect a prebuilt wheel / [s]kip / [m]anual instructions? (a/s/m): " FLASH_MODE
    case "$FLASH_MODE" in
        [aA])
            # stderr (diagnostics) prints straight to the console; only
            # stdout (the matched URL, per the script's contract) is
            # captured. "|| true" matters under `set -e` - a no-match
            # result is a deliberate non-zero exit, not a script failure.
            "$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/scripts/find_flash_attn_wheel.py" >/tmp/gfmcp_flash_url.txt || true
            FLASH_URL="$(cat /tmp/gfmcp_flash_url.txt 2>/dev/null || true)"
            rm -f /tmp/gfmcp_flash_url.txt
            if [ -z "$FLASH_URL" ]; then
                echo
                echo "Could not auto-detect a matching wheel. See docs/INSTALLATION.md"
                echo "for the manual build-from-source instructions."
            else
                echo "  Installing $FLASH_URL"
                if uv pip install "$FLASH_URL"; then
                    echo "  Flash Attention 2 installed."
                else
                    echo "Install failed. See docs/INSTALLATION.md for alternatives."
                fi
            fi
            ;;
        [mM])
            echo
            echo "Browse https://github.com/mjun0812/flash-attention-prebuild-wheels"
            echo "for a wheel matching your Python/torch/CUDA, then from inside"
            echo "$STABLE_AUDIO_DEST:"
            echo "  uv pip install <wheel URL>"
            echo "Full details, including a build-from-source fallback, are in"
            echo "docs/INSTALLATION.md."
            ;;
        *)
            echo
            echo "SKIPPED - generation will not work until Flash Attention 2 is"
            echo "installed. Re-run this installer, or see docs/INSTALLATION.md."
            ;;
    esac
    popd >/dev/null
fi

# ---- Step 8: Configure Claude Desktop ----
GAME_AUDIO_EXE="$(pwd)/.venv/bin/game-audio-mcp"
echo
echo "[8/8] Configuring Claude Desktop..."
case "$(uname -s)" in
    Darwin)
        CONFIG_DIR="$HOME/Library/Application Support/Claude"
        CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"
        read -r -p "  Configure Claude Desktop for GameForge-MCP? (y/n): " CONFIGURE_CLAUDE
        if [ "$CONFIGURE_CLAUDE" = "y" ] || [ "$CONFIGURE_CLAUDE" = "Y" ]; then
            mkdir -p "$CONFIG_DIR"
            if [ -f "$CONFIG_FILE" ]; then
                if grep -q '"game-audio"' "$CONFIG_FILE" 2>/dev/null; then
                    echo "  Claude Desktop config already has a game-audio entry - skipping."
                else
                    cp "$CONFIG_FILE" "$CONFIG_FILE.bak"
                    echo "  Backed up existing config to: $CONFIG_FILE.bak"
                    echo
                    echo "  Found existing Claude Desktop config at: $CONFIG_FILE"
                    echo "  You need to MANUALLY add this inside your \"mcpServers\" block:"
                    echo
                    echo "    \"game-audio\": {"
                    echo "      \"command\": \"$GAME_AUDIO_EXE\","
                    echo "      \"env\": { \"GAME_AUDIO_STABLE_AUDIO_HOME\": \"${STABLE_AUDIO_DEST}\" }"
                    echo "    }"
                fi
            else
                cat > "$CONFIG_FILE" <<EOF
{
  "mcpServers": {
    "game-audio": {
      "command": "$GAME_AUDIO_EXE",
      "env": { "GAME_AUDIO_STABLE_AUDIO_HOME": "${STABLE_AUDIO_DEST}" }
    }
  }
}
EOF
                echo "  Created Claude Desktop config at: $CONFIG_FILE"
            fi
        else
            echo "  Skipped. See docs/INSTALLATION.md for manual setup."
        fi
        ;;
    *)
        echo "  Claude Desktop's official app doesn't run natively on this OS -"
        echo "  if you're using it through another means, add this to its MCP config:"
        echo
        echo "    \"game-audio\": {"
        echo "      \"command\": \"$GAME_AUDIO_EXE\","
        echo "      \"env\": { \"GAME_AUDIO_STABLE_AUDIO_HOME\": \"${STABLE_AUDIO_DEST}\" }"
        echo "    }"
        ;;
esac

echo
echo "============================================================"
echo "Done."
if [ -n "$SKIP_STABLE_AUDIO" ]; then
    echo "GameForge-MCP is installed, but generation will not work until you"
    echo "run this installer again on a machine with an NVIDIA GPU."
else
    echo "  GAME_AUDIO_STABLE_AUDIO_HOME = $STABLE_AUDIO_DEST"
    echo
    echo "Add this to your shell profile (~/.bashrc, ~/.zshrc, etc.) and restart"
    echo "your terminal / Claude Desktop for it to take effect:"
    echo
    echo "  export GAME_AUDIO_STABLE_AUDIO_HOME=\"$STABLE_AUDIO_DEST\""
    echo
    echo "Still manual, by design (see docs/INSTALLATION.md):"
    echo "  1. Accept stabilityai/stable-audio-3-medium's gated license at"
    echo "     https://huggingface.co/stabilityai/stable-audio-3-medium"
    echo "  2. Run: hf auth login"
    echo "  3. Restart Claude Desktop (if configured above)"
    echo "  4. Ask Claude to generate some game audio - the ~10GB checkpoint"
    echo "     downloads automatically on that first real generation."
fi
echo
echo "Docs: https://github.com/xDarkzx/GameForge-MCP"
echo "If this is useful to you, a star on GitHub helps other people find it!"
echo "============================================================"
