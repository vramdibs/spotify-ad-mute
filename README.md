# Spotify Ad Mute

Mutes Spotify during an ad and restores the volume when music plays again. Linux (Flatpak), Windows, and Android.

A separate script exists for macOS: [YangSeungWon/spotify-ad-mute](https://github.com/YangSeungWon/spotify-ad-mute).

## Requirements

- Linux: Flatpak `com.spotify.Client`
- Windows: official `Spotify.exe` and Python 3. See [windows/README.md](windows/README.md)
- Android: JDK 17 or 21 (for Gradle) and the Android SDK. See [android/README.md](android/README.md)

## Enable

- Linux: [pc/README.md](pc/README.md)
- Windows: [windows/README.md](windows/README.md)
- Phone: [android/README.md](android/README.md)

## How it works

On Linux the service reads the Flatpak log. An explicit `spotify:ad:` from the client log is muted. A podcast, a local file, and an empty address on a track change are left alone. `spotify:track:` restores the volume. The window does not have to be in the foreground.

On Windows the watcher does the same with `Spotify.exe --log-file` and `--debug-level=8`. Only the Spotify audio session is muted, then Next is sent to the Spotify media session. If the log has no `track_uri`, a media-session title that is exactly `Advertisement`, `Реклама`, or `Объявление` is used. Any other title is left alone.

On a phone the app has no internet and lowers `STREAM_MUSIC` during an ad. On Android 14 the pause text in an already posted notification is read only with notification access: accessibility does not receive it while the shade is in front. If the notification still says «Реклама» and the player session is already named as a song, the volume is restored from the session.
