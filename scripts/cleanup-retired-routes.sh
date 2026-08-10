#!/usr/bin/env sh
set -eu

# Run from the repository root after overlaying this ZIP onto an older copy.
# These paths were intentionally retired in the August 2026 Lab cleanup.
rm -f \
  src/pages/pdfs.astro \
  src/styles/pdf-index.css \
  src/pages/pickleball.astro \
  src/components/house/rooms/PickleballRoom.svelte \
  src/components/islands/CommandMenuButton.svelte \
  public/scenes/house/windows/pickleball-court.png

rm -rf public/pdfs

echo "Retired routes and superseded header search component removed."
