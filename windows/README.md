# Spotify on Windows

From this directory, run:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\install-user.ps1

`Spotify.exe` is expected at `%APPDATA%\Spotify\Spotify.exe`. The Microsoft Store app is not installed there and is not supported. The log is `%LOCALAPPDATA%\spotify-ad-mute\spotify-ad.log`.

The script creates a `Spotify Ad Mute` shortcut in the Start menu. The shortcut starts `watch.py` (Python is required on PATH). The script opens the official `Spotify.exe` with `--log-file` and `--debug-level=8`. It also creates a scheduled task that runs the same script with `--ensure` at logon: a Spotify autostart without the log is restarted with the flag.

The first `spotify:ad:` mutes only the Spotify audio session and then sends Next to the Spotify media session. `spotify:track:` restores that session. A podcast, a local file, and an empty address are left alone.

If playback never writes `track_uri`, the watcher reads the Windows media session. The title must be exactly `Advertisement`, `Реклама`, or `Объявление`. The Spotify window does not have to be in front.
