#!/usr/bin/env bash
# Undo use-local-fork.sh: put config/VENDOR_PINS back to what it was before the
# first run, re-fetch, re-apply the server mods, and rebuild the Docker image.
#
# Reads the snapshot that use-local-fork.sh wrote. If no snapshot exists we
# refuse rather than guess a SHA -- the point of the snapshot is to roll back
# to the exact upstream pin that was there, not a hardcoded guess that may be
# older than the app checkout.
#
# Env knobs:
#   APP_DIR       path to ragnarokoffline.app   (default: /mnt/f/RagnarokOffline/blaxun ragnarokoffline.app/ragnarokoffline.app)
#   PACKETVERS    space-separated list to build (default: just the app's default packetver)
#   SKIP_BUILD=1  skip `docker build`
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_DIR="${APP_DIR:-/mnt/f/RagnarokOffline/blaxun ragnarokoffline.app/ragnarokoffline.app}"
PINS="$APP_DIR/config/VENDOR_PINS"
BACKUP="$APP_DIR/config/VENDOR_PINS.upstream-backup"

[ -f "$PINS" ] || { echo "no VENDOR_PINS at $PINS -- set APP_DIR" >&2; exit 1; }
[ -f "$BACKUP" ] || {
    echo "no $BACKUP -- nothing to restore." >&2
    echo "If you have never run use-local-fork.sh, VENDOR_PINS is already upstream." >&2
    exit 1
}

echo "==> restoring $PINS from $(basename "$BACKUP")"
cp "$BACKUP" "$PINS"

echo "==> fetching the pinned commit into vendor/rathena"
rm -rf "$APP_DIR/vendor/rathena"
(cd "$APP_DIR" && scripts/vendor-fetch.sh rathena vendor/rathena)

echo "==> applying the app's server mods on top"
(cd "$APP_DIR" && scripts/apply-server-mods.sh vendor/rathena)

if [ "${SKIP_BUILD:-0}" = "1" ]; then
    echo "==> SKIP_BUILD=1 -- stopping before docker build"
    exit 0
fi

DEFAULT_PACKETVER=$(awk '$2=="default"{print $1; exit}' "$APP_DIR/config/PACKETVERS")
PACKETVERS="${PACKETVERS:-$DEFAULT_PACKETVER}"
echo "==> docker build (default=$DEFAULT_PACKETVER, building: $PACKETVERS)"
cd "$APP_DIR"
docker build \
    -f containers/rathena/Dockerfile \
    --build-arg DEFAULT_PACKETVER="$DEFAULT_PACKETVER" \
    --build-arg PACKETVERS="$PACKETVERS" \
    -t "ragnarokmac/rathena:$DEFAULT_PACKETVER" \
    vendor/rathena

echo
echo "Done. Restart the app to pick up the restored image."
