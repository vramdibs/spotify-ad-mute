#!/bin/bash
set -euo pipefail
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d)
export XDG_DATA_HOME="$TMP/xdg"
export XDG_CONFIG_HOME="$TMP/config"
mkdir -p "$TMP/bin"
cat > "$TMP/bin/flatpak" <<'EOF'
#!/bin/bash
exit 0
EOF
chmod 755 "$TMP/bin/flatpak"
export PATH="$TMP/bin:$PATH"
bash "$ROOT/install-user-desktop.sh"
DEST="$XDG_DATA_HOME/applications/com.spotify.Client.desktop"
grep -q "Exec=$ROOT/spotify-ad-wrap.sh" "$DEST"
UNIT="$XDG_CONFIG_HOME/systemd/user/spotify-ad-watch.service"
grep -q "ExecStart=$ROOT/spotify-ad-wrap.sh --ensure" "$UNIT"
test -f "$XDG_CONFIG_HOME/systemd/user/spotify-ad-watch.path"
if [ -e /usr/share/applications/com.spotify.Client.desktop.spotify-ad-mute ]; then
  echo "system desktop was touched" >&2
  exit 1
fi
rm -rf "$TMP"
