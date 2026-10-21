# Startup script for Cursor IDE with sync agent
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$syncAgentPath = Join-Path $scriptDir "sync_agent.py"

# Check if Python is available
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}

if (-not $pythonCmd) {
    Write-Error "Python not found. Please install Python 3.8+ to run the sync agent."
    Read-Host "Press Enter to exit"
    exit 1
}

# Start sync agent in background
$syncProcess = Start-Process -FilePath $pythonCmd.Source -ArgumentList $syncAgentPath -WindowStyle Hidden -PassThru

Write-Host "Sync agent started (PID: $($syncProcess.Id))"
Write-Host "Starting Cursor IDE..."

# Start Cursor IDE (adjust path as needed)
$cursorPath = "D:\cursor\Cursor.exe"
if (Test-Path $cursorPath) {
    $cursorProcess = Start-Process -FilePath $cursorPath -PassThru
    Write-Host "Cursor started (PID: $($cursorProcess.Id))"

    # Wait for Cursor to close
    $cursorProcess.WaitForExit()

    # Stop sync agent when Cursor closes
    Write-Host "Cursor closed, stopping sync agent..."
    Stop-Process -Id $syncProcess.Id -Force -ErrorAction SilentlyContinue
} else {
    Write-Error "Cursor not found at $cursorPath"
    Stop-Process -Id $syncProcess.Id -Force -ErrorAction SilentlyContinue
    Read-Host "Press Enter to exit"
    exit 1
}
