#!/usr/bin/env bash
set -euo pipefail

# Removes files retired by the August 2026 room-theme/CSS refactor.
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
  "public/images/project-gallery"
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
