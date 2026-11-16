$ProgressPreference = "SilentlyContinue"
$ErrorActionPreference = "Stop"
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding $false
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
$OutputEncoding = [Console]::OutputEncoding
Add-Type -AssemblyName System.Runtime.WindowsRuntime

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq "AsTask" -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq "IAsyncOperation``1"
})[0]

function Await-WinRt($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    if (-not $netTask.Wait(3000)) {
        throw "timeout"
    }
    return $netTask.Result
}

function Write-Line([string]$text) {
    [Console]::Out.WriteLine($text)
    [Console]::Out.Flush()
}

$manager = $null

function Get-Manager {
    if ($script:manager -ne $null) {
        return $script:manager
    }
    $type = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,Windows.Media.Control,ContentType=WindowsRuntime]
    $script:manager = Await-WinRt ($type::RequestAsync()) $type
    return $script:manager
}

function Get-SpotifySession {
    $sessions = @(Get-Manager).GetSessions()
    foreach ($session in $sessions) {
        $appId = [string]$session.SourceAppUserModelId
        if ($appId.ToLowerInvariant().Contains("spotify")) {
            return $session
        }
    }
    return $null
}

function Get-SpotifyTitle {
    $session = Get-SpotifySession
    if ($null -eq $session) {
        return ""
    }
    $propsType = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties,Windows.Media.Control,ContentType=WindowsRuntime]
    $props = Await-WinRt ($session.TryGetMediaPropertiesAsync()) $propsType
    return [string]$props.Title
}

function Invoke-SpotifyNext {
    $session = Get-SpotifySession
    if ($null -eq $session) {
        return $false
    }
    return [bool](Await-WinRt ($session.TrySkipNextAsync()) ([type][bool]))
}

while ($true) {
    $line = [Console]::In.ReadLine()
    if ($null -eq $line) {
        break
    }
    $cmd = $line.Trim()
    if ($cmd -eq "quit") {
        break
    }
    try {
        if ($cmd -eq "poll") {
            $title = Get-SpotifyTitle
            if ([string]::IsNullOrWhiteSpace($title)) {
                Write-Line "NONE"
            } else {
                Write-Line ("TITLE " + $title)
            }
        } elseif ($cmd -eq "next") {
            if (Invoke-SpotifyNext) {
                Write-Line "OK"
            } else {
                Write-Line "MISS"
            }
        } else {
            Write-Line "ERR unknown"
        }
    } catch {
        Write-Line ("ERR " + $_.Exception.Message)
    }
}
