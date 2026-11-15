# Spotify Flatpak

Ярлык запускает обертку вместо голого Flatpak. Системный файл пакета не меняется.

Из корня клона:

    bash pc/install-user-desktop.sh
    systemctl --user enable --now spotify-ad-watch.path

Скрипт пишет пользовательский unit с путём этого клона и ярлык в `~/.local/share/applications`. Если `com.spotify.Client` не установлен, ярлык не пишется, но unit все равно записывается.

Пока плеер закрыт, процесса `spotify_ad_watch.py` нет. Журнал `~/.var/app/com.spotify.Client/data/spotify-ad.log` обнуляется только когда нет `playerctl` и сессия идет через журнал.

Проверка:

- запуск ярлыка, в `ps` есть `spotify_ad_watch.py` и `com.spotify.Client`
- закрыть плеер, через пару секунд `pgrep -f spotify_ad_watch.py` пустой
- на `spotify:ad:` звук Spotify пропадает, звук другого приложения остается
- на `spotify:track:` звук Spotify возвращается
- карточка Advertisement в ленте при обычном треке громкость не меняет
