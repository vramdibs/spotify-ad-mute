# Spotify на Windows

Ярлык запускает `watch.py`. Скрипт открывает официальный `Spotify.exe` с `--log-file` и `--debug-level=8`. Задача при входе запускает тот же скрипт с `--ensure`: автозапуск Spotify без журнала перезапускается уже с флагом.

Из этого каталога:

    powershell -NoProfile -ExecutionPolicy Bypass -File .\install-user.ps1

`Spotify.exe` ожидается в `%APPDATA%\Spotify\Spotify.exe`. Журнал: `%LOCALAPPDATA%\spotify-ad-mute\spotify-ad.log`.

Первый `spotify:ad:` глушит только звуковую сессию Spotify и сразу отправляет Next в медиасессию Spotify. `spotify:track:` возвращает громкость этой сессии. Подкаст, локальный файл и пустой адрес не трогаются.

Если воспроизведение так и не пишет `track_uri`, вотчер читает медиасессию Windows. Заголовок должен целиком совпадать с `Advertisement`, `Реклама` или `Объявление`. Окно Spotify не обязательно на переднем плане.
