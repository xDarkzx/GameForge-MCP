@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo  ============================================
echo   GameForge-MCP - One-Click Installer
echo   Local instrumental / game-BGM generation
echo  ============================================
echo.

:: ---- Step 1: Python bootstrap ----
echo [1/8] Checking Python...
where python >nul 2>&1
if errorlevel 1 (
    echo   Python not found on PATH. Installing Python 3.12...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_python.ps1"
    if errorlevel 1 (
        echo.
        echo  ERROR: Failed to install Python automatically.
        echo  Install Python 3.10+ manually from python.org ^(check "Add Python
        echo  to PATH"^) and re-run this script.
        echo.
        pause
        exit /b 1
    )
    echo.
    echo  Python installed! Close and reopen this terminal, then run
    echo  install.bat again so Python is on PATH.
    echo.
    pause
    exit /b 0
)

for /f "delims=" %%V in ('python -c "import sys; print(1 if sys.version_info >= (3, 10) else 0)" 2^>nul') do set "PY_OK=%%V"
if not "%PY_OK%"=="1" (
    echo.
    echo  ERROR: Python on PATH is older than 3.10 - GameForge-MCP needs 3.10+.
    echo  Install a newer Python from python.org and re-run this script.
    echo.
    pause
    exit /b 1
)
echo   Python OK.

:: ---- Step 2: uv bootstrap (stable-audio-3 is uv-managed, unlike this
:: server's own venv) ----
echo.
echo [2/8] Checking uv...
where uv >nul 2>&1
if errorlevel 1 (
    echo   uv not found on PATH. Installing via the official installer...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    where uv >nul 2>&1
    if errorlevel 1 (
        echo.
        echo  ERROR: uv install did not put it on PATH for this session.
        echo  Close and reopen this terminal, then run install.bat again.
        echo.
        pause
        exit /b 1
    )
)
echo   uv OK.

:: ---- Step 3: this server's own venv (lightweight - no torch, see
:: pyproject.toml: mcp[cli] + soundfile only) ----
echo.
echo [3/8] Setting up GameForge-MCP's own venv...
python -m venv .venv
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 (
    echo.
    echo  ERROR: pip install failed. Try running as administrator, or
    echo  manually: .venv\Scripts\python.exe -m pip install -e .
    echo.
    pause
    exit /b 1
)
echo   GameForge-MCP installed.

:: ---- Step 4: disk space check (checkpoint is ~10GB, leave headroom) ----
echo.
echo [4/8] Checking disk space...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\check_disk_space.ps1" -RequiredGB 15
if errorlevel 1 (
    echo.
    echo  ERROR: Not enough free disk space to continue safely ^(need ~15GB free^).
    echo  Free up space first, then re-run this script.
    echo.
    pause
    exit /b 1
)

:: ---- Step 5: NVIDIA GPU check - Stable Audio 3 Medium requires Flash
:: Attention 2 unconditionally (no CPU fallback exists, per stable-audio-3's
:: own README). Without an NVIDIA GPU there's nothing useful Steps 6-7 can
:: do, so skip straight to installing just this server + Claude config.
echo.
echo [5/8] Checking for an NVIDIA GPU...
where nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo.
    echo  No NVIDIA GPU detected ^(nvidia-smi not found^). Stable Audio 3
    echo  requires an NVIDIA GPU - there is no CPU fallback. Skipping the
    echo  stable-audio-3 setup ^(steps 6-7^); GameForge-MCP itself will still
    echo  be installed and configured below, but generation will not work
    echo  until you run this installer again on a machine with an NVIDIA GPU.
    echo.
    set "SKIP_STABLE_AUDIO=1"
) else (
    echo   NVIDIA GPU detected.
    set "SKIP_STABLE_AUDIO="
)

if defined SKIP_STABLE_AUDIO goto :configure_claude

:: ---- Step 6: stable-audio-3 checkout + its own uv-managed venv ----
echo.
echo [6/8] Setting up stable-audio-3...

if "%GAME_AUDIO_STABLE_AUDIO_HOME%"=="" (
    set "STABLE_AUDIO_DEST=%~dp0..\stable-audio-3"
    echo   GAME_AUDIO_STABLE_AUDIO_HOME not set - using !STABLE_AUDIO_DEST!
    if not exist "!STABLE_AUDIO_DEST!" (
        git clone https://github.com/Stability-AI/stable-audio-3.git "!STABLE_AUDIO_DEST!"
        if errorlevel 1 (
            echo.
            echo  ERROR: git clone failed. Install git, or clone manually and
            echo  set GAME_AUDIO_STABLE_AUDIO_HOME to point at it.
            echo.
            pause
            exit /b 1
        )
    ) else (
        echo   Found an existing checkout at !STABLE_AUDIO_DEST! - reusing it.
    )
) else (
    set "STABLE_AUDIO_DEST=%GAME_AUDIO_STABLE_AUDIO_HOME%"
    echo   Using existing GAME_AUDIO_STABLE_AUDIO_HOME: !STABLE_AUDIO_DEST!
)

pushd "!STABLE_AUDIO_DEST!"
uv venv
:: Windows-specific override: stable-audio-3's own pyproject.toml only
:: pins a CUDA torch index for Linux (see its [tool.uv.sources] marker) -
:: a plain `uv sync` on Windows silently installs CPU-only torch. Pinned
:: to 2.7.1+cu128 specifically, matching this project's flash-attn wheel
:: search (scripts/find_flash_attn_wheel.py) - do not let this float.
uv pip install torch==2.7.1+cu128 torchaudio==2.7.1+cu128 --index-url https://download.pytorch.org/whl/cu128
if errorlevel 1 (
    echo.
    echo  ERROR: torch install failed. See docs/INSTALLATION.md for alternatives.
    echo.
    popd
    pause
    exit /b 1
)
uv sync --extra ui --no-install-package torch --no-install-package torchaudio
if errorlevel 1 (
    echo.
    echo  ERROR: uv sync failed. See docs/INSTALLATION.md.
    echo.
    popd
    pause
    exit /b 1
)
echo   stable-audio-3 dependencies installed.

:: ---- Step 7: Flash Attention 2 (required - Stable Audio 3 Medium will
:: not run without it) ----
echo.
echo [7/8] Flash Attention 2 setup ^(required^)...
echo   Stable Audio 3 Medium requires Flash Attention 2 to run.
set /p FLASH_MODE="  [a]uto-detect a prebuilt wheel / [s]kip / [m]anual instructions? (a/s/m): "
if /i "!FLASH_MODE!"=="a" (
    :: stderr (diagnostics) prints straight to the console; only stdout
    :: (the matched URL, per the script's contract) is captured to a file.
    "%~dp0.venv\Scripts\python.exe" "%~dp0scripts\find_flash_attn_wheel.py" >"%TEMP%\gfmcp_flash_url.txt"
    set "FLASH_URL="
    set /p FLASH_URL=<"%TEMP%\gfmcp_flash_url.txt"
    del "%TEMP%\gfmcp_flash_url.txt" >nul 2>&1
    if "!FLASH_URL!"=="" (
        echo.
        echo  Could not auto-detect a matching wheel. See docs/INSTALLATION.md
        echo  for the manual build-from-source instructions.
        echo.
    ) else (
        echo   Installing !FLASH_URL!
        uv pip install "!FLASH_URL!"
        if errorlevel 1 (
            echo.
            echo  Install failed. See docs/INSTALLATION.md for alternatives.
            echo.
        ) else (
            echo   Flash Attention 2 installed.
        )
    )
) else if /i "!FLASH_MODE!"=="m" (
    echo.
    echo  Browse https://github.com/mjun0812/flash-attention-prebuild-wheels
    echo  for a wheel matching your Python/torch/CUDA, then from inside
    echo  !STABLE_AUDIO_DEST!:
    echo    uv pip install ^<wheel URL^>
    echo  Full details, including a build-from-source fallback, are in
    echo  docs/INSTALLATION.md.
    echo.
) else (
    echo.
    echo  SKIPPED - generation will not work until Flash Attention 2 is
    echo  installed. Re-run this installer, or see docs/INSTALLATION.md.
    echo.
)
popd

setx GAME_AUDIO_STABLE_AUDIO_HOME "!STABLE_AUDIO_DEST!" >nul
set "GAME_AUDIO_STABLE_AUDIO_HOME=!STABLE_AUDIO_DEST!"

:configure_claude
:: ---- Step 8: Configure Claude Desktop ----
echo.
echo [8/8] Configuring Claude Desktop...

:: Claude Desktop installed via the Microsoft Store runs sandboxed and
:: redirects AppData\Roaming to a virtualized per-package folder - a config
:: written to the normal %APPDATA%\Claude path is silently never read in
:: that case (same real, confirmed issue SongForge-MCP's installer works
:: around). Detect which install this actually is before writing anywhere.
set "CONFIG_DIR="
for /d %%D in ("%LOCALAPPDATA%\Packages\Claude_*") do (
    if exist "%%D\LocalCache\Roaming\Claude" set "CONFIG_DIR=%%D\LocalCache\Roaming\Claude"
)
if "%CONFIG_DIR%"=="" (
    set "CONFIG_DIR=%APPDATA%\Claude"
    echo   Detected standard Claude Desktop install.
) else (
    echo   Detected Microsoft Store Claude Desktop install ^(sandboxed config path^).
)

set "CONFIG_FILE=%CONFIG_DIR%\claude_desktop_config.json"
set "GAME_AUDIO_EXE=%~dp0.venv\Scripts\game-audio-mcp.exe"

set /p CONFIGURE_CLAUDE="  Configure Claude Desktop for GameForge-MCP? (y/n): "
if /i not "!CONFIGURE_CLAUDE!"=="y" (
    echo   Skipped. See docs/INSTALLATION.md for manual setup.
    goto :skip_config
)

if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"

if exist "%CONFIG_FILE%" (
    findstr /c:"\"game-audio\"" "%CONFIG_FILE%" >nul 2>&1
    if !errorlevel! equ 0 (
        echo   Claude Desktop config already has a game-audio entry - skipping.
        goto :skip_config
    )
    copy "%CONFIG_FILE%" "%CONFIG_FILE%.bak" >nul 2>&1
    echo   Backed up existing config to: %CONFIG_FILE%.bak
    echo.
    echo   Found existing Claude Desktop config at:
    echo   %CONFIG_FILE%
    echo.
    echo   You need to MANUALLY add this inside your "mcpServers" block:
    echo.
    echo     "game-audio": {
    echo       "command": "%GAME_AUDIO_EXE:\=\\%",
    echo       "env": { "GAME_AUDIO_STABLE_AUDIO_HOME": "%GAME_AUDIO_STABLE_AUDIO_HOME:\=\\%" }
    echo     }
    echo.
    echo   Opening the config file for you...
    notepad "%CONFIG_FILE%"
    goto :skip_config
)

(
echo {
echo   "mcpServers": {
echo     "game-audio": {
echo       "command": "%GAME_AUDIO_EXE:\=\\%",
echo       "env": { "GAME_AUDIO_STABLE_AUDIO_HOME": "%GAME_AUDIO_STABLE_AUDIO_HOME:\=\\%" }
echo     }
echo   }
echo }
) > "%CONFIG_FILE%"
echo   Created Claude Desktop config at:
echo   %CONFIG_FILE%

:skip_config

:: ---- Done ----
echo.
echo  ============================================
echo   SETUP COMPLETE!
echo  ============================================
echo.
if defined SKIP_STABLE_AUDIO (
    echo  GameForge-MCP is installed, but generation will not work until you
    echo  run this installer again on a machine with an NVIDIA GPU.
) else (
    echo  Still manual, by design ^(see docs/INSTALLATION.md^):
    echo   1. Accept stabilityai/stable-audio-3-medium's gated license at
    echo      https://huggingface.co/stabilityai/stable-audio-3-medium
    echo   2. Run: hf auth login   ^(from stable-audio-3's own venv or any
    echo      environment with huggingface_hub installed^)
    echo   3. Restart Claude Desktop ^(if configured above^)
    echo   4. Ask Claude to generate some game audio - the ~10GB checkpoint
    echo      downloads automatically on that first real generation.
)
echo.
echo  Docs: https://github.com/xDarkzx/GameForge-MCP
echo  If this is useful to you, a star on GitHub helps other people find it!
echo  ============================================
echo.
pause
