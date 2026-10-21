@echo off
setlocal enabledelayedexpansion

title Sunday AI Assistant - External Drive Bootstrapper
echo ========================================================
echo             SUNDAY AI EXTERNAL DRIVE BOOTSTRAP
echo ========================================================

:: Detect current drive letter
set "CURRENT_DIR=%~dp0"
set "DRIVE_ROOT=%~d0\"

echo [INFO] Detected drive: %DRIVE_ROOT%
cd /d "%CURRENT_DIR%"

:: Check for Sunday project root
if exist "%DRIVE_ROOT%Sunday\pyproject.toml" (
    set "SUNDAY_ROOT=%DRIVE_ROOT%Sunday"
) else if exist "%CURRENT_DIR%..\..\pyproject.toml" (
    pushd "%CURRENT_DIR%..\.."
    set "SUNDAY_ROOT=!CD!"
    popd
) else (
    set "SUNDAY_ROOT=%DRIVE_ROOT%"
)

echo [INFO] Sunday Root: %SUNDAY_ROOT%
cd /d "%SUNDAY_ROOT%"

:: Redirect caches and storage to external drive to guarantee ZERO laptop footprint
set "HF_HOME=%DRIVE_ROOT%sunday_cache\huggingface"
set "OLLAMA_MODELS=%DRIVE_ROOT%sunday_cache\ollama"
set "SUNDAY_DATA_DIR=%DRIVE_ROOT%sunday_data"

if not exist "%SUNDAY_DATA_DIR%" mkdir "%SUNDAY_DATA_DIR%"
if not exist "%HF_HOME%" mkdir "%HF_HOME%"

:: Load .env if present
if exist "%SUNDAY_ROOT%\.env" (
    echo [INFO] Loading environment from %SUNDAY_ROOT%\.env
    for /f "usebackq tokens=1,* delims==" %%A in ("%SUNDAY_ROOT%\.env") do (
        set "line=%%A"
        if not "!line:~0,1!"=="#" (
            set "%%A=%%B"
        )
    )
)

echo [INFO] Starting Sunday Daemon...
python -m sunday.daemon.pipeline --dashboard --sidecar --telegram --insomnia --voice

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Sunday exited with code %ERRORLEVEL%
    pause
)
