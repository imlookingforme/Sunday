# Startup script for Windsurf IDE with sync agent
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
Write-Host "Starting Windsurf IDE..."

# Start Windsurf IDE (adjust path as needed)
$windsurfPath = "D:\Devin\Devin.exe"
if (Test-Path $windsurfPath) {
    $windsurfProcess = Start-Process -FilePath $windsurfPath -PassThru
    Write-Host "Windsurf started (PID: $($windsurfProcess.Id))"
    
    # Wait for Windsurf to close
    $windsurfProcess.WaitForExit()
    
    # Stop sync agent when Windsurf closes
    Write-Host "Windsurf closed, stopping sync agent..."
    Stop-Process -Id $syncProcess.Id -Force -ErrorAction SilentlyContinue
} else {
    Write-Error "Windsurf not found at $windsurfPath"
    Stop-Process -Id $syncProcess.Id -Force -ErrorAction SilentlyContinue
    Read-Host "Press Enter to exit"
    exit 1
}
