$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$python = (Get-Command python).Source
$pythonw = Join-Path (Split-Path $python) "pythonw.exe"
if (-not (Test-Path $pythonw)) {
    throw "pythonw.exe was not found next to $python"
}
$watch = Join-Path $root "watch.py"
if (-not (Test-Path $watch)) {
    throw "watch.py is missing next to install-user.ps1"
}

$programs = [Environment]::GetFolderPath("Programs")
$shortcut = Join-Path $programs "Spotify Ad Mute.lnk"
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut($shortcut)
$link.TargetPath = $pythonw
$link.Arguments = "`"$watch`""
$link.WorkingDirectory = $root
$icon = Join-Path $env:APPDATA "Spotify\Spotify.exe"
if (Test-Path $icon) {
    $link.IconLocation = "$icon,0"
}
$link.Save()

$runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$spotifyRun = (Get-ItemProperty -Path $runKey -Name Spotify -ErrorAction SilentlyContinue).Spotify
if ($spotifyRun -like "*Spotify.exe*") {
    Set-ItemProperty -Path $runKey -Name Spotify -Value "`"$pythonw`" `"$watch`""
}

$action = New-ScheduledTaskAction -Execute $pythonw -Argument "`"$watch`" --ensure" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
Register-ScheduledTask -TaskName "SpotifyAdMute" -Action $action -Trigger $trigger -Force | Out-Null
Write-Output "SHORTCUT $shortcut"
Write-Output "TASK SpotifyAdMute"
