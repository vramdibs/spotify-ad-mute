# Mute during an ad

Install Spotify:

    flatpak install flathub com.spotify.Client

The package `ru.stabilnoitochka.spotifyadmute` is built with `./gradlew :app:assembleDebug`. Gradle 8.7 runs on JDK 17 or 21 (21 is recommended). JDK 25 does not work. If needed, set `JAVA_HOME` or `org.gradle.java.home` in a local `gradle.properties`. The Android SDK directory goes in `local.properties` (`sdk.dir=...`). Sample: [`local.properties.example`](local.properties.example).

`adb install -r` installs the apk into the personal profile. Download: [spotifyadmute-1.0.apk](https://github.com/vramdibs/spotify-ad-mute/releases/download/v1.0/spotifyadmute-1.0.apk). Shelter is not supported because accessibility settings are required, and there is no icon in the app drawer.

The package is not from the store, so its row under Accessibility is gray. On Android 17 that is the only permission: there is no separate notification access. Do the steps to unlock the setting:

1. Settings, Apps, All apps, Spotify ad mute.
2. Three dots, Allow access to settings.
3. Accessibility, Downloaded apps, Spotify ad mute. The switch is no longer gray.
4. Turn the switch on. In the dialog Allow the "Spotify ad mute" service to control your device?, tap Allow.

Android warns that the package is not from the store. That is expected. Leave the service on in the full-access check: without it, muting stops.

The service lowers the music volume on the ad screen with a pause timer. If the screen is off, there is no Spotify card in the shade: the system hides it, and the window event does not arrive. The same accessibility service reads the notification text, including a pause that is already posted. If the notification still says «Advertisement» and the player session is already named as a song, the volume is restored from the session when the system connects the notification listener. An Advertisement card in the feed leaves the volume unchanged. Android music is one stream, so another app on that stream can get quieter for the length of the ad. The package has no internet. While Spotify is closed, the service receives no events and does not write the volume.

Check:

- ad screen with a pause timer: the sound is zero, and after the screen the previous volume is back
- a feed card while a track is playing: the volume stays the same
- turn the service off in the middle of an ad: the volume comes back immediately
