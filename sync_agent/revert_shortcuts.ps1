# Script to revert taskbar shortcuts to original targets

$taskbarPath = "$env:APPDATA\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar"

# Revert Cursor shortcut
$cursorShortcut = "$taskbarPath\Cursor.lnk"
if (Test-Path $cursorShortcut) {
    $ws = New-Object -ComObject WScript.Shell
    $shortcut = $ws.CreateShortcut($cursorShortcut)
    $shortcut.TargetPath = "D:\cursor\Cursor.exe"
    $shortcut.Arguments = ""
    $shortcut.Save()
    Write-Host "Reverted Cursor shortcut to original"
}

# Revert Windsurf shortcut  
$windsurfShortcut = "$taskbarPath\Devin.lnk"
if (Test-Path $windsurfShortcut) {
    $ws = New-Object -ComObject WScript.Shell
    $shortcut = $ws.CreateShortcut($windsurfShortcut)
    $shortcut.TargetPath = "D:\Devin\Devin.exe"
    $shortcut.Arguments = ""
    $shortcut.Save()
    Write-Host "Reverted Windsurf shortcut to original"
}

Write-Host "Done! Shortcuts reverted to original IDE paths."
