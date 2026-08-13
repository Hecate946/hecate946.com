#!/usr/bin/env bash
set -euo pipefail

PATCH_NAME="hecate946-mobile-polish-fix-patch.zip"
SCRIPT_NAME="$(basename "$0")"

if [[ ! -f package.json || ! -d src || ! -d public ]]; then
  echo "ERROR: Run this from the ROOT of the hecate946.com repository." >&2
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: This folder is not a Git repository." >&2
  exit 1
fi

branch="$(git branch --show-current)"
if [[ "$branch" != "main" ]]; then
  echo "ERROR: You are on '${branch:-detached}', not main." >&2
  echo "Run: git switch main" >&2
  exit 1
fi

# Clean the one file the failed first patch could create before aborting.
rm -f public/images/projects/hecate946-project.webp
rmdir public/images/projects 2>/dev/null || true

dirty="$(
  git status --porcelain --untracked-files=all \
    | grep -v -E "^\?\? (${SCRIPT_NAME}|${PATCH_NAME}|apply-mobile-polish\.sh|hecate946-mobile-polish-patch\.zip)$" \
    | grep -v -E "^\?\? patch-assets/" \
    || true
)"
if [[ -n "$dirty" ]]; then
  echo "ERROR: There are unrelated uncommitted changes in this Codespace:" >&2
  echo "$dirty" >&2
  echo >&2
  echo "I stopped rather than overwrite them." >&2
  exit 1
fi

echo "Updating main..."
git pull --ff-only origin main

python3 - <<'PY'
from pathlib import Path
import re

ROOT = Path.cwd()

ABOUT = ROOT / "src/styles/about-scroll.css"
CONTACT = ROOT / "src/styles/contact.css"
PALETTES = ROOT / "src/styles/room-palettes.css"
PROJECTS = ROOT / "src/data/projects.ts"

for path in (ABOUT, CONTACT, PALETTES, PROJECTS):
    if not path.exists():
        raise SystemExit(f"ERROR: expected current-main file is missing: {path.relative_to(ROOT)}")

def replace_marked(text: str, begin: str, end: str, block: str) -> str:
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    if pattern.search(text):
        return pattern.sub(block, text)
    return text.rstrip() + "\n\n" + block + "\n"

about_begin = "/* HECATE ABOUT LYNN-FISHER MOBILE COMPOSITION - BEGIN */"
about_end = "/* HECATE ABOUT LYNN-FISHER MOBILE COMPOSITION - END */"

about_block = r"""/* HECATE ABOUT LYNN-FISHER MOBILE COMPOSITION - BEGIN */
/*
 * Let the portrait participate in the same text flow as the introduction.
 * This mirrors the Lynn Fisher reference: image on the left, prose wrapping
 * naturally to its right and then continuing at full width below.
 */
.about-scroll-header {
  display: contents;
}

.about-scroll-portrait-wrap {
  float: left;
  width: clamp(8.75rem, 25vw, 10.5rem);
  margin: 0.2rem 1.25rem 0.65rem 0;
}

.about-scroll-portrait-frame {
  border: 1px solid var(--paper-accent);
  background: transparent;
  box-shadow: none;
}

.about-scroll-portrait-glass {
  inset: 0;
  background: transparent;
  box-shadow: none;
}

.about-scroll-portrait-shade,
.about-scroll-portrait-reflection,
.about-scroll-portrait-sill {
  display: none;
}

.about-scroll-intro {
  max-width: 31rem;
  margin-inline: auto;
}

.about-scroll-intro::after {
  display: block;
  clear: both;
  content: '';
}

@media (max-width: 44rem) {
  .about-scroll-installation {
    box-sizing: border-box;
    padding:
      clamp(1.15rem, 4vw, 1.75rem)
      max(0.75rem, env(safe-area-inset-right))
      calc(var(--room-floor-reserve, 7.25rem) + 1.4rem)
      max(0.75rem, env(safe-area-inset-left));
  }

  .about-scroll-hanging {
    width: 100%;
    max-width: 32rem;
    margin-inline: auto;
  }

  .about-scroll-paper {
    width: 100%;
    padding-inline: 0.18rem;
  }

  .about-scroll-paper__viewport {
    padding-inline: clamp(1.25rem, 5.6vw, 1.65rem);
  }

  .about-scroll-portrait-wrap {
    width: clamp(7rem, 30vw, 8.35rem);
    margin: 0.15rem 0.9rem 0.5rem 0;
  }

  .about-scroll-intro {
    font-size: clamp(0.98rem, 4vw, 1.08rem);
    line-height: 1.57;
  }
}

@media (max-width: 25rem) {
  .about-scroll-hanging {
    width: 100%;
  }

  .about-scroll-paper__viewport {
    padding-inline: 1.2rem;
  }

  .about-scroll-portrait-wrap {
    width: clamp(6.5rem, 30vw, 7.3rem);
    margin-right: 0.78rem;
  }

  .about-scroll-intro {
    font-size: 0.94rem;
  }
}
/* HECATE ABOUT LYNN-FISHER MOBILE COMPOSITION - END */"""

ABOUT.write_text(replace_marked(ABOUT.read_text(), about_begin, about_end, about_block))

contact_begin = "/* HECATE CONTACT MOBILE FULL-SCREEN COMPOSE - BEGIN */"
contact_end = "/* HECATE CONTACT MOBILE FULL-SCREEN COMPOSE - END */"

contact_block = r"""/* HECATE CONTACT MOBILE FULL-SCREEN COMPOSE - BEGIN */
@media (max-width: 40rem) {
  body.room-theme-contact {
    height: auto;
    min-height: 100svh;
    overflow-x: hidden;
    overflow-y: auto;
  }

  body.room-theme-contact main {
    min-height: 0;
    overflow: visible;
  }

  body.primary-room-page.contact-room-page .contact-page {
    height: auto;
    min-height: calc(100svh - var(--header-height));
    overflow: visible;
  }

  body.primary-room-page.contact-room-page .contact-wall {
    position: relative;
    inset: auto;
    top: auto;
    display: block;
    box-sizing: border-box;
    padding:
      0
      max(0.85rem, env(safe-area-inset-right))
      calc(var(--contact-floor-height) + 1.25rem)
      max(0.85rem, env(safe-area-inset-left));
  }

  .contact-station {
    width: 100%;
    max-width: 31rem;
    margin-inline: auto;
    gap: 1rem;
  }

  .contact-compose {
    box-sizing: border-box;
    display: flex;
    min-height: calc(100svh - var(--header-height) - 1rem);
    flex-direction: column;
    justify-content: center;
    padding: clamp(1.35rem, 6vw, 1.8rem);
  }

  .contact-kicker,
  .contact-topics legend,
  .contact-note > span {
    font-size: clamp(0.72rem, 3.15vw, 0.86rem);
    line-height: 1.2;
  }

  .contact-email-row {
    align-items: flex-start;
    gap: 0.8rem;
    margin-top: 0.72rem;
  }

  .contact-email-address {
    font-size: clamp(1.15rem, 5.35vw, 1.48rem);
    line-height: 1.08;
  }

  .contact-copy {
    min-height: 2.5rem;
    padding: 0.52rem 0.68rem;
    font-size: 0.82rem;
  }

  .contact-rule {
    margin: 1.15rem 0;
  }

  .contact-topics legend {
    margin-bottom: 0.72rem;
  }

  .contact-topic-grid {
    grid-template-columns: 1fr;
    gap: 0.58rem;
  }

  .contact-topic {
    min-height: 2.75rem;
    gap: 0.62rem;
    padding: 0.58rem 0.7rem;
    font-size: clamp(0.72rem, 3vw, 0.84rem);
  }

  .contact-topic__dot {
    width: 0.72rem;
    height: 0.72rem;
  }

  .contact-note {
    gap: 0.6rem;
    margin-top: 1rem;
  }

  .contact-note textarea {
    min-height: 6.5rem;
    max-height: 9rem;
    padding: 0.82rem 0.86rem;
    font-size: 1rem;
    line-height: 1.4;
  }

  .contact-compose-button {
    min-height: 3rem;
    margin-top: 1rem;
    padding: 0.7rem 0.9rem;
    font-size: 1rem;
  }

  .contact-social-grid {
    grid-template-columns: 1fr;
    gap: 0.85rem;
  }

  .contact-social-card {
    min-height: 8rem;
    padding: 1rem 0.8rem;
  }

  .contact-social-card__icon,
  .contact-social-card__cup {
    width: 3rem;
    height: 3rem;
    margin-bottom: 0.42rem;
  }

  .contact-social-card__title {
    font-size: 1.12rem;
  }

  .contact-social-card__detail {
    display: block;
    margin-top: 0.28rem;
    font-size: 0.72rem;
  }
}
/* HECATE CONTACT MOBILE FULL-SCREEN COMPOSE - END */"""

CONTACT.write_text(replace_marked(CONTACT.read_text(), contact_begin, contact_end, contact_block))

palettes = PALETTES.read_text()
old = """/* Deep amber. */
html[data-theme='dark'] .room-theme-resume {
  --wall-dark: #664e00;
}"""
new = """/* Antique metallic gold / brass. */
html[data-theme='dark'] .room-theme-resume {
  --wall-dark: #8a7427;
}"""
if old in palettes:
    palettes = palettes.replace(old, new)
elif "--wall-dark: #8a7427;" not in palettes:
    raise SystemExit("ERROR: Resume dark palette no longer matches the inspected main branch.")
PALETTES.write_text(palettes)

projects = PROJECTS.read_text()
old_alt = """    imageAlt:
      'Expressionist print of a pale figure with dark flowing hair inside a vivid orange-red border, with a small seated figure in the lower-left corner, used as the Hecate946.com project image.',"""
new_alt = """    imageAlt:
      'Portrait of a woman dressed in black beneath a broad black hat, set against an olive-green background, used as the Hecate946.com project image.',"""
if old_alt in projects:
    projects = projects.replace(old_alt, new_alt)
elif "Portrait of a woman dressed in black beneath a broad black hat" not in projects:
    raise SystemExit("ERROR: Hecate946.com project alt text no longer matches the inspected main branch.")
PROJECTS.write_text(projects)

print("Source edits applied.")
PY

cp patch-assets/portfolio-480.webp public/images/project-gallery/portfolio-480.webp
cp patch-assets/portfolio.webp public/images/project-gallery/portfolio.webp

echo
echo "Running production build..."
if [[ ! -d node_modules ]]; then
  npm ci
fi
npm run build

echo
echo "BUILD PASSED."

# Clean delivery-only files so git add cannot accidentally commit them.
rm -f "$SCRIPT_NAME" "$PATCH_NAME" apply-mobile-polish.sh hecate946-mobile-polish-patch.zip
rm -rf patch-assets
rm -f public/images/projects/hecate946-project.webp
rmdir public/images/projects 2>/dev/null || true

echo
echo "Final Git status:"
git status --short
echo
echo "READY TO COMMIT."
