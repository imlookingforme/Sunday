# USB Auto-Trigger & Environment Architecture

To ensure Sunday leaves a zero-data footprint on the host laptop (HP Pavilion) and boots directly from the 1TB external HDD, we employ a two-part architecture:

1.  **The Host Daemon (Laptop):** A tiny background process that listens for USB events.
2.  **The Bootstrap Script (HDD):** A script that sets local paths and launches the Sunday pipeline.

## 1. The Host Daemon (`usb_listener.ps1` or C# Service)

This script must be placed on the host laptop (e.g., in the Startup folder) and run in the background. It continuously monitors Windows Management Instrumentation (WMI) for `Win32_VolumeChangeEvent`.

```powershell
# usb_listener.ps1 (Runs on Host Laptop)
$query = "SELECT * FROM Win32_VolumeChangeEvent WHERE EventType = 2"
Register-WmiEvent -Query $query -SourceIdentifier "USBPluggedIn" -Action {
    $drive = Get-WmiObject Win32_Volume | Where-Object { $_.Label -eq "SUNDAY_DRIVE" }
    if ($drive) {
        $driveLetter = $drive.DriveLetter
        $scriptPath = "$driveLetter\bootstrap_sunday.bat"
        if (Test-Path $scriptPath) {
            # Execute the bootstrap script silently
            Start-Process -FilePath $scriptPath -WindowStyle Hidden
        }
    }
}
```

## 2. The Bootstrap Script (`bootstrap_sunday.bat`)

This script resides on the root of the 1TB HDD. When triggered by the Host Daemon, it forces all Python environment variables to point *inside* the HDD, ensuring no models or databases leak onto the `C:\` drive.

```bat
@echo off
:: bootstrap_sunday.bat (Resides on the 1TB HDD)

:: Get the current drive letter (e.g., E:)
set DRIVE_LETTER=%~d0

:: Set all AI paths to point to the external drive
set HF_HOME=%DRIVE_LETTER%\sunday_env\huggingface_cache
set OLLAMA_MODELS=%DRIVE_LETTER%\sunday_env\ollama_models
set SUNDAY_DB_PATH=%DRIVE_LETTER%\sunday_env\data\sunday.db
set SUNDAY_VECTOR_PATH=%DRIVE_LETTER%\sunday_env\data\vectors

:: Activate the virtual environment located on the drive
call %DRIVE_LETTER%\sunday_env\Scripts\activate.bat

:: Launch the Sunday Daemon with Insomnia (24/7) and Mobile Dashboard enabled
cd %DRIVE_LETTER%\Sunday
python -m sunday.daemon.pipeline --insomnia --dashboard --telegram
```

## Rigid Verification

**Test Procedure:**
1. Configure `usb_listener.ps1` to run on startup on the host laptop.
2. Label the 1TB external drive as `SUNDAY_DRIVE`.
3. Place `bootstrap_sunday.bat` and the `Sunday` codebase on the drive.
4. Unplug the drive, then plug it back in.

**Expected Outcome:**
1. The Sunday process (and FastAPI dashboard) should start automatically within 10 seconds of plugging in the drive.
2. Check the host laptop's `C:\Users\<User>\.cache\huggingface` and `C:\Users\<User>\.ollama` directories. They must be completely empty or non-existent, confirming that all heavy weights are stored on the external drive.
