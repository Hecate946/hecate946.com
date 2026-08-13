#!/usr/bin/env bash
set -euo pipefail

# Removes files retired by the August 2026 room/runtime cleanup.
#
# This script is intentionally conservative: it only removes the exact files
# known to be obsolete, so it is safe to run after extracting the new source
# ZIP over an existing checkout. It is also idempotent and can be run again.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

if [[ ! -f "$PROJECT_ROOT/package.json" ]] || \
   ! grep -q '"name"[[:space:]]*:[[:space:]]*"cyrus-asasi-portfolio"' "$PROJECT_ROOT/package.json"; then
  echo "Refusing to clean: expected hecate946.com project root at: $PROJECT_ROOT" >&2
  exit 1
fi

obsolete_files=(
  "public/favicon.svg"
  "public/images/social/about.jpg"
  "src/components/about/about-tv-content.ts"
  "src/features/wall/ProjectWall.svelte"
  "public/audio/.gitkeep"
  "public/images/about/cyrus-portrait.webp"
  "public/pdfs/scroll-test-10-pages.pdf"
  "src/components/about/AboutFloor.svelte"
  "src/components/about/AboutTV.svelte"
  "src/components/about/TVChannel.svelte"
  "src/features/floor/LegacyFloorScene.svelte"
  "src/features/floor/MagnifyingGlass.svelte"
  "src/features/floor/floor-scene-context.ts"
  "src/features/floor/README.md"
  "src/features/wall/InfiniteWall.svelte"
  "src/features/wall/project-wall-config.ts"
  "src/features/wall/resume-wall-config.ts"
  "src/styles/about.css"
  "src/styles/contact-postcards.css"
  "src/styles/magnifying-glass.css"
  "public/assets/world-map-hires.svg"
  "public/generated/globe-world-mask-4096.png"
  "public/images/about/cyrus-portrait.png"
  "public/images/about/ucla-pickleball-super-regional-1200.webp"
  "public/images/about/ucla-pickleball-super-regional-720.webp"
  "public/images/pig.png"
  "public/images/project-gallery/placeholder-03.svg"
  "public/images/project-gallery/placeholder-04.svg"
  "public/images/projects/keycad-1200.webp"
  "public/images/projects/keycad-640.webp"
  "public/images/projects/keycad-960.webp"
  "public/images/projects/keycad.png"
  "public/images/projects/neutra-1200.webp"
  "public/images/projects/neutra-640.webp"
  "public/images/projects/neutra-960.webp"
  "public/images/projects/neutra.png"
  "public/images/projects/portfolio-1200.webp"
  "public/images/projects/portfolio-640.webp"
  "public/images/projects/portfolio-960.webp"
  "public/images/projects/portfolio.png"
  "public/images/projects/sunset-1200.webp"
  "public/images/projects/sunset-640.webp"
  "public/images/projects/sunset-960.webp"
  "public/images/projects/sunset.png"
  "src/components/contact/ContactBulletinBoard.svelte"
  "src/components/contact/ContactWallLinks.astro"
  "src/components/projects/ProjectCard.astro"
  "src/styles/projects-index.css"
)

removed=0
for relative_path in "${obsolete_files[@]}"; do
  target="$PROJECT_ROOT/$relative_path"
  if [[ -e "$target" || -L "$target" ]]; then
    rm -f -- "$target"
    printf 'removed  %s\n' "$relative_path"
    ((removed += 1))
  fi
done

# Remove directories only when the cleanup left them empty. Never recurse here.
empty_dirs=(
  "src/components/projects"
  "src/features/floor"
  "public/images/project-gallery"
  "public/pdfs"
)

for relative_dir in "${empty_dirs[@]}"; do
  dir="$PROJECT_ROOT/$relative_dir"
  if [[ -d "$dir" ]]; then
    rmdir --ignore-fail-on-non-empty "$dir" 2>/dev/null || true
  fi
done

if (( removed == 0 )); then
  echo "Cleanup complete: no obsolete files were present."
else
  echo "Cleanup complete: removed $removed obsolete file(s)."
fi
