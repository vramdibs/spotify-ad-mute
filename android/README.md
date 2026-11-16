# Mute during an ad

Install Spotify:

    flatpak install flathub com.spotify.Client

The package `ru.stabilnoitochka.spotifyadmute` is built with `./gradlew :app:assembleDebug`. Gradle 8.7 runs on JDK 17 or 21 (21 is recommended). JDK 25 does not work. If needed, set `JAVA_HOME` or `org.gradle.java.home` in a local `gradle.properties`. The Android SDK directory goes in `local.properties` (`sdk.dir=...`). Sample: [`local.properties.example`](local.properties.example).

`adb install -r` installs the apk into the personal profile. Download: [spotifyadmute-1.0.apk](https://github.com/vramdibs/spotify-ad-mute/releases/download/v1.0/spotifyadmute-1.0.apk). Shelter is not supported because accessibility settings are required, and there is no icon in the app drawer.

Android 14 needs two switches.

Accessibility reads the Spotify screen. The package is not from the store, so the row is gray. To unlock it:

1. Settings, Apps, All apps, Spotify ad mute.
2. Three dots, Allow access to settings.
3. Accessibility, Downloaded apps, Spotify ad mute. The switch is no longer gray.
4. Turn the switch on. In the dialog Allow the "Spotify ad mute" service to control your device?, tap Allow.

Notification access is a separate switch. While the shade is in front, an update to an already posted notification does not reach accessibility. The line «Объявление • 1 из 2» on that pause is read only with this access.

1. Settings, Notifications, Notifications on devices and in apps.
2. Spotify ad mute in the Not allowed list.
3. Turn on Notification access.
4. In the dialog Allow the "Spotify ad mute" app to access notifications?, tap Allow.

Android warns that the package is not from the store. That is expected. Leave the service on in the full-access check: without it, muting stops.

The service lowers the music volume on the ad screen with a pause timer. If the screen is off or the shade is in front, there is no window event. If the notification still says «Реклама» and the player session is already named as a song, the volume is restored from the session when the system connects the notification listener. An Advertisement card in the feed leaves the volume unchanged. Android music is one stream, so another app on that stream can get quieter for the length of the ad. The package has no internet. While Spotify is closed, the service receives no events and does not write the volume.

Check:

- ad screen with a pause timer: the sound is zero, and after the screen the previous volume is back
- a feed card while a track is playing: the volume stays the same
- turn the service off in the middle of an ad: the volume comes back immediately
