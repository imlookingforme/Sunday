# Script to modify taskbar shortcuts to launch with sync agent

$taskbarPath = "$env:APPDATA\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar"
$syncAgentPath = "d:\Raghuram\OneDrive\Desktop\Computer Science\Sunday\sync_agent"
$cursorScript = "$syncAgentPath\start_with_cursor.ps1"
$windsurfScript = "$syncAgentPath\start_with_windsurf.ps1"

# Modify Cursor shortcut
$cursorShortcut = "$taskbarPath\Cursor.lnk"
if (Test-Path $cursorShortcut) {
    $ws = New-Object -ComObject WScript.Shell
    $shortcut = $ws.CreateShortcut($cursorShortcut)
    
    # Backup original target
    $originalTarget = $shortcut.TargetPath
    Write-Host "Original Cursor target: $originalTarget"
    
    # Set new target to PowerShell script
    $shortcut.TargetPath = "powershell.exe"
    $shortcut.Arguments = "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$cursorScript`""
    $shortcut.Save()
    
    Write-Host "Modified Cursor shortcut to launch with sync agent"
} else {
    Write-Host "Cursor shortcut not found"
}

# Modify Windsurf shortcut  
$windsurfShortcut = "$taskbarPath\Devin.lnk"
if (Test-Path $windsurfShortcut) {
    $ws = New-Object -ComObject WScript.Shell
    $shortcut = $ws.CreateShortcut($windsurfShortcut)
    
    # Backup original target
    $originalTarget = $shortcut.TargetPath
    Write-Host "Original Windsurf target: $originalTarget"
    
    # Set new target to PowerShell script
    $shortcut.TargetPath = "powershell.exe"
    $shortcut.Arguments = "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$windsurfScript`""
    $shortcut.Save()
    
    Write-Host "Modified Windsurf shortcut to launch with sync agent"
} else {
    Write-Host "Windsurf shortcut not found"
}

Write-Host "Done! Taskbar shortcuts now launch with sync agent."
