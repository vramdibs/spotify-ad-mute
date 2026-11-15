#!/bin/bash
set -euo pipefail
DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
exec python3 "$DIR/spotify_ad_watch.py" "$@"
