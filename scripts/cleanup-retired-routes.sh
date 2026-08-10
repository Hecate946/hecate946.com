#!/usr/bin/env bash
set -euo pipefail

# Remove routes/assets retired from the public site. Safe to run repeatedly.
rm -f \
  src/pages/resume.astro \
  src/pages/pdfs.astro \
  src/pages/pickleball.astro \
  src/pages/chess-board.astro \
  src/styles/resume.css \
  src/components/islands/PickleballCourt.svelte \
  src/components/islands/ForceNetwork.svelte \
  src/components/house/rooms/ChessBoardRoom.svelte \
  public/scenes/house/windows/pickleball-court.png \
  public/scenes/house/windows/chess-black-rook-room.png

rm -rf \
  public/pdfs \
  dist/resume \
  dist/pdfs \
  dist/pickleball \
  dist/chess-board

printf 'Retired routes cleaned: /resume, /pdfs, /pickleball, /chess-board\n'
