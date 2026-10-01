#!/usr/bin/env bash
# Point RagnarokOffline.app at this working copy of rAthena, apply the app's
# own server mods on top of it, and build the Docker image the app runs.
#
# Pins config/VENDOR_PINS in the sibling ragnarokoffline.app checkout at the
# current branch's HEAD on `origin`, so a reproducible fetch -- not a bind
# mount -- is what the app picks up. The first run of this script snapshots the
# upstream pin to config/VENDOR_PINS.upstream-backup, which restore-upstream-fork.sh
# reads back.
#
# Expects:
#   - This repo's `origin` is your rAthena fork on GitHub.
#   - The default APP_DIR below points at your working app checkout.
#   - WSL has git, docker and python3 on PATH (the app's apply-server-mods.sh
#     uses python3; the Dockerfile needs docker, obviously).
#
# Env knobs (all optional):
#   APP_DIR       path to ragnarokoffline.app   (default: /mnt/f/RagnarokOffline/blaxun ragnarokoffline.app/ragnarokoffline.app)
#   PACKETVERS    space-separated list to build (default: just the app's default packetver)
#   SKIP_BUILD=1  skip `docker build` (useful if you only want to update the pin)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_DIR="${APP_DIR:-/mnt/f/RagnarokOffline/blaxun ragnarokoffline.app/ragnarokoffline.app}"
PINS="$APP_DIR/config/VENDOR_PINS"
BACKUP="$APP_DIR/config/VENDOR_PINS.upstream-backup"

[ -f "$PINS" ] || { echo "no VENDOR_PINS at $PINS -- set APP_DIR" >&2; exit 1; }

cd "$REPO_ROOT"

# A dirty tree would be silently excluded from the push, and the app would
# build a server that is not what you are looking at.
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "working tree has uncommitted changes -- commit or stash before pointing the app at it" >&2
    git status --short
    exit 1
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "HEAD" ]; then
    echo "detached HEAD -- check out a branch first" >&2
    exit 1
fi
URL=$(git remote get-url origin)

echo "==> pushing $BRANCH to origin ($URL)"
git push -u origin "$BRANCH"
SHA=$(git rev-parse "origin/$BRANCH")
echo "    at $SHA"

# Snapshot the current upstream pin once, so restore-upstream-fork.sh has
# something to roll back to that is not a stale hardcoded SHA. If the backup
# already exists we leave it alone: a repeat run of this script would otherwise
# overwrite a true upstream pin with a local-fork pin.
if [ ! -f "$BACKUP" ]; then
    echo "==> snapshotting upstream VENDOR_PINS to $(basename "$BACKUP")"
    cp "$PINS" "$BACKUP"
fi

echo "==> rewriting the rathena row in $PINS"
# A row is: name url commit branch (branch optional). Rewrite the one named
# `rathena`, keep comments and the other rows untouched.
python3 - "$PINS" "$URL" "$SHA" "$BRANCH" <<'PY'
import sys, pathlib
pins_path, url, sha, branch = sys.argv[1:5]
p = pathlib.Path(pins_path)
out = []
seen = False
for line in p.read_text().splitlines():
    stripped = line.strip()
    if stripped and not stripped.startswith("#"):
        parts = stripped.split()
        if parts[0] == "rathena":
            out.append(f"rathena           {url}           {sha}  {branch}")
            seen = True
            continue
    out.append(line)
if not seen:
    print("no `rathena` row found in VENDOR_PINS", file=sys.stderr)
    sys.exit(1)
p.write_text("\n".join(out) + "\n")
PY

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
echo "Done. Restart the app to pick up the new image."
