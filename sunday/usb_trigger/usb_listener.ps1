<#
.SYNOPSIS
    Monitors for insertion of a USB drive labeled SUNDAY_DRIVE and launches Sunday AI.
.DESCRIPTION
    Runs quietly in the background (designed for Windows Startup folder).
    Polls every few seconds for volume label matching SUNDAY_DRIVE.
    When detected, invokes bootstrap_sunday.bat from the drive root or sunday/usb_trigger folder.
#>

param(
    [string]$DriveLabel = "SUNDAY_DRIVE",
    [int]$PollIntervalSeconds = 5
)

$ErrorActionPreference = "SilentlyContinue"
$LogFile = Join-Path $env:TEMP "sunday_usb_listener.log"

function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$ts] $Message" | Out-File -FilePath $LogFile -Append -Encoding utf8
}

function Show-Notification {
    param([string]$Title, [string]$Message)
    try {
        [void][System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms")
        $notification = New-Object System.Windows.Forms.NotifyIcon
        $notification.Icon = [System.Drawing.SystemIcons]::Information
        $notification.BalloonTipTitle = $Title
        $notification.BalloonTipText = $Message
        $notification.Visible = $true
        $notification.ShowBalloonTip(3000)
    } catch {}
}

Write-Log "Sunday USB Listener started. Waiting for volume labeled '$DriveLabel'..."

$DriveWasPresent = $false

while ($true) {
    $sundayDrive = Get-Volume | Where-Object { $_.FileSystemLabel -eq $DriveLabel -and $_.DriveLetter } | Select-Object -First 1

    if ($sundayDrive -and -not $DriveWasPresent) {
        $letter = "$($sundayDrive.DriveLetter):\"
        Write-Log "Found $DriveLabel at $letter"
        Show-Notification "Sunday AI Detected" "SUNDAY_DRIVE detected at $letter. Bootstrapping Sunday..."

        $bootstrapBat = Join-Path $letter "bootstrap_sunday.bat"
        if (-not (Test-Path $bootstrapBat)) {
            $bootstrapBat = Join-Path $letter "sunday\usb_trigger\bootstrap_sunday.bat"
        }
        if (-not (Test-Path $bootstrapBat)) {
            $bootstrapBat = Join-Path $letter "Sunday\sunday\usb_trigger\bootstrap_sunday.bat"
        }

        if (Test-Path $bootstrapBat) {
            Write-Log "Launching $bootstrapBat"
            Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"$bootstrapBat`"" -WindowStyle Normal
        } else {
            Write-Log "WARNING: bootstrap_sunday.bat not found on $letter"
        }

        $DriveWasPresent = $true
    } elseif (-not $sundayDrive -and $DriveWasPresent) {
        Write-Log "$DriveLabel was removed."
        $DriveWasPresent = $false
    }

    Start-Sleep -Seconds $PollIntervalSeconds
}
