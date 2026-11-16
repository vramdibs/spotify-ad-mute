# Spotify Ad Mute

Mutes Spotify during an ad and restores the volume when music plays again. Linux (Flatpak) and Android.

A separate script exists for macOS: [YangSeungWon/spotify-ad-mute](https://github.com/YangSeungWon/spotify-ad-mute).

## Requirements

- Linux: Flatpak `com.spotify.Client`
- Android: JDK 17 or 21 (for Gradle) and the Android SDK. See [android/README.md](android/README.md)

## Enable

- PC: [pc/README.md](pc/README.md)
- Phone: [android/README.md](android/README.md)

## How it works

On a PC the service reads the Flatpak log. An explicit `spotify:ad:` from the client log is muted. A podcast, a local file, and an empty address on a track change are left alone. `spotify:track:` restores the volume. The window does not have to be in the foreground.

On a phone the app has no internet and lowers `STREAM_MUSIC` during an ad. On Android 14 the pause text in an already posted notification is read only with notification access: accessibility does not receive it while the shade is in front. If the notification still says «Реклама» and the player session is already named as a song, the volume is restored from the session.
