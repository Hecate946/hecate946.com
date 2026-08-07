#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

QUALITY="${1:-WEB}"

case "$QUALITY" in
  PREVIEW|WEB|FINAL) ;;
  *)
    echo "Usage: $0 [PREVIEW|WEB|FINAL]"
    exit 2
    ;;
esac

HECATE_EXTERIOR_QUALITY="$QUALITY" \
  blender --background --python blender/house/exterior/build_exterior_25d.py
