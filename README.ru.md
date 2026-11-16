# Spotify Ad Mute

Глушит Spotify на ролике и возвращает громкость, когда снова играет музыка. Linux (Flatpak) и Android.

Для macOS есть отдельный скрипт: [YangSeungWon/spotify-ad-mute](https://github.com/YangSeungWon/spotify-ad-mute).

## Что нужно

- Linux: Flatpak `com.spotify.Client`
- Android: JDK 17 или 21 (для Gradle) и Android SDK — см. [android/README.ru.md](android/README.ru.md)

## Как включить

- ПК: [pc/README.ru.md](pc/README.ru.md)
- Телефон: [android/README.ru.md](android/README.ru.md)

## Как устроено

На ПК служба читает журнал Flatpak. Глушится явный `spotify:ad:` из журнала клиента. Подкаст, локальный файл и пустой адрес при смене трека не трогаются, `spotify:track:` возвращает громкость. Окно на переднем плане не нужно.

На телефоне приложение без интернета убавляет `STREAM_MUSIC` на ролике. На Android 14 текст паузы из уже висящего уведомления читается только при доступе к уведомлениям: специальные возможности его не получают, пока сверху шторка. Если уведомление еще пишет «Реклама», а сессия плеера уже называется песней, то громкость возвращается по сессии.
