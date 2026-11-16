# Spotify on Windows

The shortcut starts `watch.py`, which launches official `Spotify.exe` with `--log-file` and `--debug-level=8`. A logon task runs the same script with `--ensure`, so a Spotify autostart that has no log flag is restarted with one.

From this directory:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\install-user.ps1

`Spotify.exe` is expected at `%APPDATA%\Spotify\Spotify.exe`. The log is `%LOCALAPPDATA%\spotify-ad-mute\spotify-ad.log`.

The first `spotify:ad:` mutes only the Spotify audio session and then sends Next to the Spotify media session. `spotify:track:` restores that session. A podcast, a local file, and an empty address are left alone.

If playback never writes `track_uri`, the watcher reads the Windows media session. The title must be exactly `Advertisement`, `Реклама`, or `Объявление`. The Spotify window does not have to be in front.
