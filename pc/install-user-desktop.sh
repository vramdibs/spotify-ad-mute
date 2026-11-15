#!/bin/bash
set -euo pipefail
ROOT=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
case "$DEST" in
  /usr/*|/usr/local/*)
    echo "refusing system desktop dir: $DEST" >&2
    exit 1
    ;;
esac
mkdir -p "$UNIT_DIR"
cp "$ROOT/systemd/spotify-ad-watch.path" "$UNIT_DIR/spotify-ad-watch.path"
cat > "$UNIT_DIR/spotify-ad-watch.service" <<EOF
[Unit]
Description=Spotify ad mute while the Flatpak is open

[Service]
Type=simple
ExecStart=$ROOT/spotify-ad-wrap.sh --ensure
EOF
if ! flatpak info com.spotify.Client >/dev/null 2>&1; then
  echo "com.spotify.Client is not installed, desktop file not written" >&2
  exit 0
fi
mkdir -p "$DEST"
cat > "$DEST/com.spotify.Client.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Spotify
Exec=$ROOT/spotify-ad-wrap.sh
Icon=com.spotify.Client
Terminal=false
Categories=Audio;Music;
StartupWMClass=spotify
EOF
