# Spotify Ad Mute

Глушит Spotify на ролике и возвращает громкость, когда снова играет музыка. Linux (Flatpak), Windows и Android.

Для macOS есть отдельный скрипт: [YangSeungWon/spotify-ad-mute](https://github.com/YangSeungWon/spotify-ad-mute).

## Что нужно

- Linux: Flatpak `com.spotify.Client`
- Windows: официальный `Spotify.exe` и Python 3 — см. [windows/README.ru.md](windows/README.ru.md)
- Android: JDK 17 или 21 (для Gradle) и Android SDK — см. [android/README.ru.md](android/README.ru.md)

## Как включить

- Linux: [pc/README.ru.md](pc/README.ru.md)
- Windows: [windows/README.ru.md](windows/README.ru.md)
- Телефон: [android/README.ru.md](android/README.ru.md)

## Как устроено

На Linux служба читает журнал Flatpak. Глушится явный `spotify:ad:` из журнала клиента. Подкаст, локальный файл и пустой адрес при смене трека не трогаются, `spotify:track:` возвращает громкость. Окно на переднем плане не нужно.

На Windows тот же сигнал берётся из `Spotify.exe --log-file` и `--debug-level=8`. Глушится только звуковая сессия Spotify, затем Next уходит в медиасессию Spotify. Если в журнале нет `track_uri`, берётся заголовок медиасессии, который целиком равен `Advertisement`, `Реклама` или `Объявление`. Любой другой заголовок не трогается.

На телефоне приложение без интернета убавляет `STREAM_MUSIC` на ролике. На Android 14 текст паузы из уже висящего уведомления читается только при доступе к уведомлениям: специальные возможности его не получают, пока сверху шторка. Если уведомление еще пишет «Реклама», а сессия плеера уже называется песней, то громкость возвращается по сессии.
