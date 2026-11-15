# Spotify Flatpak: mute during an ad

The launcher starts a wrapper instead of plain Flatpak. The package file on the system stays as it is.

From the clone root:

    bash pc/install-user-desktop.sh
    systemctl --user enable --now spotify-ad-watch.path

The script writes a user unit with this clone's path and a launcher in `~/.local/share/applications`. If `com.spotify.Client` is not installed, the launcher is skipped and the unit is still written.

While the player is closed, there is no `spotify_ad_watch.py` process. The log `~/.var/app/com.spotify.Client/data/spotify-ad.log` is cleared only when `playerctl` is absent and the session goes through the log.

Check:

- start the launcher; `ps` shows `spotify_ad_watch.py` and `com.spotify.Client`
- close the player; after a couple of seconds `pgrep -f spotify_ad_watch.py` is empty
- on `spotify:ad:` the Spotify sound goes away and another application's sound stays
- on `spotify:track:` the Spotify sound comes back
- an Advertisement card in the feed during a normal track leaves the volume unchanged
