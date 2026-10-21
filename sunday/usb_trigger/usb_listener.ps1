# usb_listener.ps1 (Runs on Host Laptop)
# This script monitors for the specific SUNDAY_DRIVE USB connection
# and silently launches the bootstrap script on the external drive.

$query = "SELECT * FROM Win32_VolumeChangeEvent WHERE EventType = 2"
Register-WmiEvent -Query $query -SourceIdentifier "USBPluggedIn" -Action {
    # Search for the specific 1TB drive labeled "SUNDAY_DRIVE"
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

Write-Host "Sunday USB Listener is running in the background. Waiting for SUNDAY_DRIVE..."
