#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

QUALITY="${1:-PREVIEW}"
SEASONS="${2:-spring,summer,autumn,winter}"

case "$QUALITY" in
  PREVIEW|WEB|FINAL) ;;
  *)
    echo "Usage: $0 [PREVIEW|WEB|FINAL] [spring,summer,autumn,winter]"
    exit 2
    ;;
esac

python3 blender/house/exterior/download_exterior_assets.py

# The source ZIP intentionally excludes heavy .blend files, so always make sure
# the current exact house source has produced house.blend before exterior build.
if [[ ! -f blender/house/house.blend ]]; then
  blender --background --python blender/house/house.py
fi

HECATE_EXTERIOR_QUALITY="$QUALITY" \
HECATE_EXTERIOR_SEASONS="$SEASONS" \
blender --background \
  --python blender/house/exterior/build_exterior_25d.py
