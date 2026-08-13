#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
PROJECT_ROOT="$(pwd)"

if [[ ! -f package.json || ! -d src ]]; then
  echo "ERROR: Run this from the root of the hecate946.com repository." >&2
  exit 1
fi

if [[ "${HECATE_PATCH_SKIP_GIT:-0}" != "1" ]]; then
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "ERROR: This folder is not a Git repository." >&2
    exit 1
  fi
  branch="$(git branch --show-current)"
  if [[ "$branch" != "main" ]]; then
    echo "ERROR: This patch is intended for main. Current branch: ${branch:-detached}" >&2
    echo "Run: git switch main" >&2
    exit 1
  fi
  script_name="$(basename "$SCRIPT_PATH")"
  dirty="$(git status --porcelain --untracked-files=all | grep -v -F "?? $script_name" | grep -v -F "?? hecate946-mobile-polish-patch.zip" || true)"
  if [[ -n "$dirty" ]]; then
    echo "ERROR: The repository already has uncommitted changes. Commit/stash them first." >&2
    echo "$dirty" >&2
    exit 1
  fi
  echo "Updating main..."
  git pull --ff-only origin main
fi

python3 - <<'PY'
from __future__ import annotations
import base64
import re
from pathlib import Path

ROOT = Path.cwd()
ABOUT_PAGE = ROOT / 'src/pages/about.astro'
ABOUT_CSS = ROOT / 'src/styles/about.css'
CONTACT_PAGE = ROOT / 'src/pages/contact.astro'
THEMES_CSS = ROOT / 'src/styles/themes.css'
TOKENS_CSS = ROOT / 'src/styles/tokens.css'
PROJECT_IMAGE = ROOT / 'public/images/projects/hecate946-project.webp'
PROJECT_IMAGE_B64 = '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'

BEGIN_ABOUT = '/* HECATE MOBILE ABOUT POLISH 2026-08-13 — BEGIN */'
END_ABOUT = '/* HECATE MOBILE ABOUT POLISH 2026-08-13 — END */'
BEGIN_THEME = '/* HECATE REALISTIC GOLD DARK THEME 2026-08-13 — BEGIN */'
END_THEME = '/* HECATE REALISTIC GOLD DARK THEME 2026-08-13 — END */'
BEGIN_CONTACT = '<!-- HECATE MOBILE CONTACT POLISH 2026-08-13 — BEGIN -->'
END_CONTACT = '<!-- HECATE MOBILE CONTACT POLISH 2026-08-13 — END -->'


def replace_marked(text: str, begin: str, end: str, block: str) -> str:
    pattern = re.compile(re.escape(begin) + r'.*?' + re.escape(end), re.S)
    if pattern.search(text):
        return pattern.sub(block, text)
    if not text.endswith('\n'):
        text += '\n'
    return text + '\n' + block + '\n'


def class_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for match in re.finditer(r'\bclass\s*=\s*(["\'])(.*?)\1', text, re.S):
        for token in re.split(r'\s+', match.group(2).strip()):
            if token and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]*', token):
                tokens.append(token)
    return list(dict.fromkeys(tokens))


def stack_at(text: str, index: int):
    tag_re = re.compile(r'<(?P<close>/)?(?P<tag>[A-Za-z][\w:.-]*)(?P<attrs>[^<>]*?)>', re.S)
    void = {'img','br','hr','meta','link','input','source','area','base','col','embed','param','track','wbr'}
    stack = []
    for match in tag_re.finditer(text, 0, index):
        tag = match.group('tag')
        lower = tag.lower()
        if match.group('close'):
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][1].lower() == lower:
                    del stack[i:]
                    break
            continue
        attrs = match.group('attrs') or ''
        if not (attrs.rstrip().endswith('/') or lower in void):
            stack.append((match, tag, attrs))
    return stack


def classes_from_attrs(attrs: str) -> list[str]:
    m = re.search(r'\bclass\s*=\s*(["\'])(.*?)\1', attrs, re.S)
    return [t for t in re.split(r'\s+', m.group(2).strip()) if t] if m else []


def add_class_to_open_tag(text: str, tag_match: re.Match, new_class: str) -> str:
    start, end = tag_match.span()
    segment = text[start:end]
    class_match = re.search(r'\bclass\s*=\s*(["\'])(.*?)\1', segment, re.S)
    if class_match:
        classes = class_match.group(2).split()
        if new_class in classes:
            return text
        q = class_match.group(1)
        replacement = f'class={q}{class_match.group(2)} {new_class}{q}'
        segment = segment[:class_match.start()] + replacement + segment[class_match.end():]
    else:
        insert_at = segment.rfind('>')
        if insert_at < 0:
            return text
        before = segment[:insert_at]
        if before.rstrip().endswith('/'):
            before = before.rstrip()[:-1].rstrip() + f' class="{new_class}" /'
        else:
            before += f' class="{new_class}"'
        segment = before + '>'
    return text[:start] + segment + text[end:]


def css_selector(c: str) -> str:
    return '.' + c


PROJECT_IMAGE.parent.mkdir(parents=True, exist_ok=True)
PROJECT_IMAGE.write_bytes(base64.b64decode(PROJECT_IMAGE_B64))
print(f'Wrote {PROJECT_IMAGE.relative_to(ROOT)}')

# ABOUT: preserve the current implementation; only tag its portrait wrapper and add overrides.
about_source = ABOUT_PAGE.read_text() if ABOUT_PAGE.exists() else ''
if not about_source:
    raise SystemExit('ERROR: src/pages/about.astro was not found or is empty.')

portrait_anchor = None
for pattern in (
    r'<img\b[^>]*alt\s*=\s*["\'][^"\']*Cyrus[^"\']*["\'][^>]*>',
    r'<img\b[^>]*(?:portrait|cyrus-portrait)[^>]*>',
):
    m = re.search(pattern, about_source, re.I | re.S)
    if m:
        portrait_anchor = m
        break

if portrait_anchor:
    stack = stack_at(about_source, portrait_anchor.start())
    candidate = None
    for entry in reversed(stack):
        _, tag, attrs = entry
        if tag.lower() not in {'div','figure','span','aside','section'}:
            continue
        classes = ' '.join(classes_from_attrs(attrs)).lower()
        if any(k in classes for k in ('portrait','photo','image','avatar')):
            candidate = entry
            break
    if candidate is None:
        for entry in reversed(stack):
            if entry[1].lower() in {'figure','div'}:
                candidate = entry
                break
    if candidate:
        about_source = add_class_to_open_tag(about_source, candidate[0], 'about-mobile-portrait-wrap')
        ABOUT_PAGE.write_text(about_source)
        print(f'Tagged portrait wrapper in {ABOUT_PAGE.relative_to(ROOT)}')
else:
    print('WARNING: About portrait image was not identified; existing .about-portrait-frame CSS will still be handled.')

about_classes = class_tokens(about_source)
scroll_classes = [c for c in about_classes if any(k in c.lower() for k in ('scroll','paper','sheet','parchment'))]
content_scroll_classes = [c for c in scroll_classes if any(k in c.lower() for k in ('content','inner','body','copy','paper','sheet','parchment'))]
outer_scroll_classes = [c for c in scroll_classes if c not in content_scroll_classes]

outer_rule = ''
if outer_scroll_classes:
    sels = ',\n  '.join(css_selector(c) for c in outer_scroll_classes)
    outer_rule = f'''\n  {sels} {{
    box-sizing: border-box !important;
    width: min(100%, calc(100vw - 1rem)) !important;
    max-width: calc(100vw - 1rem) !important;
    margin-inline: auto !important;
  }}\n'''

content_targets = ['.about-intro', '.about-prose', '.interior-page-content']
content_targets += [css_selector(c) for c in content_scroll_classes]
content_targets = list(dict.fromkeys(content_targets))
content_sel = ',\n  '.join(content_targets)

about_block = f'''{BEGIN_ABOUT}
/* Lynn Fisher-inspired mobile composition: portrait floats left, prose wraps beside it. */
@media (max-width: 680px) {{
  .about-book {{
    box-sizing: border-box !important;
    width: 100% !important;
    padding-inline: 0 !important;
    overflow-x: clip;
  }}
{outer_rule}
  {content_sel} {{
    box-sizing: border-box !important;
    width: 100% !important;
    max-width: 31.5rem !important;
    margin-inline: auto !important;
    padding-left: clamp(1.125rem, 5vw, 1.5rem) !important;
    padding-right: clamp(1.125rem, 5vw, 1.5rem) !important;
  }}

  .about-mobile-portrait-wrap,
  .about-portrait-frame {{
    position: relative !important;
    float: left !important;
    width: clamp(7.25rem, 31vw, 9rem) !important;
    height: auto !important;
    aspect-ratio: auto !important;
    margin: 0.2rem 1rem 0.7rem 0 !important;
    padding: 0 !important;
    border: 1px solid var(--accent-strong) !important;
    border-radius: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
    overflow: hidden !important;
    transform: none !important;
  }}

  .about-mobile-portrait-wrap img,
  .about-portrait-frame img {{
    display: block !important;
    width: 100% !important;
    height: auto !important;
    aspect-ratio: auto !important;
    border: 0 !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    object-fit: cover;
  }}

  .about-intro::after,
  .about-prose::after,
  .interior-page-content::after {{
    display: block;
    clear: both;
    content: '';
  }}
}}
{END_ABOUT}'''

if not ABOUT_CSS.exists():
    raise SystemExit('ERROR: src/styles/about.css was not found.')
ABOUT_CSS.write_text(replace_marked(ABOUT_CSS.read_text(), BEGIN_ABOUT, END_ABOUT, about_block))
print(f'Updated {ABOUT_CSS.relative_to(ROOT)}')

# CONTACT: preserve the blackboard/chalk implementation and only adjust mobile sizing/scroll behavior.
if not CONTACT_PAGE.exists():
    raise SystemExit('ERROR: src/pages/contact.astro was not found.')
contact = CONTACT_PAGE.read_text()
contact = re.sub(re.escape(BEGIN_CONTACT) + r'.*?' + re.escape(END_CONTACT), '', contact, flags=re.S)
anchor_idx = -1
for needle in ('href="mailto:', "href='mailto:", 'Compose Email', 'compose email'):
    idx = contact.find(needle)
    if idx >= 0:
        anchor_idx = idx
        break

if anchor_idx >= 0:
    stack = stack_at(contact, anchor_idx)
    scored = []
    for depth, entry in enumerate(stack):
        _, tag, attrs = entry
        if tag.lower() not in {'div','section','article','aside','form','figure'}:
            continue
        cls = ' '.join(classes_from_attrs(attrs)).lower()
        score = 0
        if 'email' in cls: score += 4
        if 'compose' in cls: score += 4
        if any(k in cls for k in ('card','panel','board','primary','hero','section','area')): score += 6
        if 'contact' in cls: score += 2
        if any(k in cls for k in ('action','button','link','label','title','icon')): score -= 7
        score += depth * 0.05
        scored.append((score, entry))
    candidate = max(scored, key=lambda item: item[0])[1] if scored else None
    if candidate:
        contact = add_class_to_open_tag(contact, candidate[0], 'contact-mobile-email-screen')
        print(f'Tagged full-screen mobile email area in {CONTACT_PAGE.relative_to(ROOT)}')
    else:
        print('WARNING: Could not identify a structural Email container; text sizing still applies.')
else:
    print('WARNING: Could not find mailto/Compose Email; text sizing still applies.')

contact_block = f'''{BEGIN_CONTACT}
<style is:global>
  @media (max-width: 680px) {{
    body:has(main a[href*='github.com']) {{
      overflow-y: auto !important;
      overflow-x: clip;
    }}

    body:has(main a[href*='github.com']) main {{
      height: auto !important;
      min-height: 100svh;
      overflow: visible !important;
    }}

    .contact-mobile-email-screen {{
      box-sizing: border-box !important;
      display: flex !important;
      min-height: 100svh !important;
      width: 100% !important;
      flex-direction: column !important;
      align-items: center !important;
      justify-content: center !important;
      padding: clamp(1.5rem, 7vw, 2.25rem) !important;
    }}

    .contact-mobile-email-screen :is(p, a, button, span, label) {{
      font-size: clamp(1.05rem, 4.8vw, 1.28rem) !important;
      line-height: 1.35 !important;
    }}

    body:has(main a[href*='github.com']) main h1 {{
      font-size: clamp(2.4rem, 11vw, 4rem) !important;
    }}

    body:has(main a[href*='github.com']) main h2 {{
      font-size: clamp(1.55rem, 7vw, 2.15rem) !important;
    }}

    body:has(main a[href*='github.com']) main p {{
      font-size: clamp(1.05rem, 4.6vw, 1.22rem) !important;
      line-height: 1.55 !important;
    }}

    body:has(main a[href*='github.com']) main :is(a, button) {{
      min-height: 2.75rem;
      font-size: clamp(1rem, 4.4vw, 1.18rem) !important;
    }}
  }}
</style>
{END_CONTACT}'''
if not contact.endswith('\n'):
    contact += '\n'
contact += '\n' + contact_block + '\n'
CONTACT_PAGE.write_text(contact)
print(f'Updated {CONTACT_PAGE.relative_to(ROOT)}')

# PROJECT: swap the Hecate946.com project image, without changing the Contact chalkboard image.
new_image = '/images/projects/hecate946-project.webp'
old_candidates = ('/images/contact/chalkboard-photo.webp', '/images/contact/chalkboard-photo.png')
project_files = []
for base in (ROOT / 'src/pages/projects', ROOT / 'src/features', ROOT / 'src/components'):
    if base.exists():
        for ext in ('*.astro','*.ts','*.tsx','*.js','*.jsx','*.svelte'):
            project_files.extend(base.rglob(ext))

replacements = 0
for path in dict.fromkeys(project_files):
    text = path.read_text(errors='ignore')
    lower = text.lower()
    if not ('hecate946.com' in lower or 'portfolio' in path.name.lower() or '/projects/portfolio' in lower):
        continue
    original = text
    for old in old_candidates:
        text = text.replace(old, new_image)
    if text != original:
        path.write_text(text)
        replacements += 1
        print(f'Updated project image reference in {path.relative_to(ROOT)}')

portfolio = ROOT / 'src/pages/projects/portfolio.astro'
if replacements == 0 and portfolio.exists():
    text = portfolio.read_text()
    image_refs = list(re.finditer(r'(["\'])(/(?:images|paintings)/[^"\']+?\.(?:webp|png|jpe?g))\1', text, re.I))
    if image_refs:
        hecate_positions = [m.start() for m in re.finditer(r'hecate946|portfolio', text, re.I)] or [len(text)//2]
        best = None
        best_score = -10**9
        for m in image_refs:
            path_value = m.group(2).lower()
            score = -min(abs(m.start() - p) for p in hecate_positions)
            if any(k in path_value for k in ('icon','favicon','logo')):
                score -= 100000
            if score > best_score:
                best_score = score
                best = m
        if best:
            start, end = best.span(2)
            text = text[:start] + new_image + text[end:]
            portfolio.write_text(text)
            replacements = 1
            print(f'Updated fallback project image in {portfolio.relative_to(ROOT)}')

if replacements == 0:
    print('WARNING: Project image asset was added, but no current Hecate946.com project image reference was identified.')

# THEME: final dark-mode override to a muted, believable brass/gold rather than orange-brown.
theme_path = THEMES_CSS if THEMES_CSS.exists() else TOKENS_CSS
if not theme_path.exists():
    raise SystemExit('ERROR: Could not find src/styles/themes.css or src/styles/tokens.css.')

gold_block = f'''{BEGIN_THEME}
html[data-theme='dark'],
html[data-season][data-theme='dark'] {{
  --bg: #0e0e0c;
  --surface: rgba(28, 27, 22, 0.86);
  --surface-strong: #1d1b15;
  --text: #f3eee2;
  --muted: #b9af9b;
  --line: rgba(212, 175, 55, 0.22);
  --accent: #c9a64b;
  --accent-strong: #e0c56f;
  --accent-soft: rgba(212, 175, 55, 0.13);
  --season-1: #aa873b;
  --season-2: #d4af37;
  --season-3: #85754f;
  --shadow: 0 1.25rem 3rem rgba(0, 0, 0, 0.38);
  --header-bg: #11100d;
  --header-text: #f3eee2;
  --header-muted: #b9af9b;
  --header-line: rgba(212, 175, 55, 0.18);
  --header-hover: rgba(212, 175, 55, 0.08);
  --header-active-text: #e7ce83;
  --header-accent: #d4af37;
}}
{END_THEME}'''

theme_path.write_text(replace_marked(theme_path.read_text(), BEGIN_THEME, END_THEME, gold_block))
print(f'Updated {theme_path.relative_to(ROOT)}')
print('\nPatch complete.')
PY

if [[ "${HECATE_PATCH_SKIP_BUILD:-0}" != "1" ]]; then
  echo
  echo "Installing dependencies if needed..."
  if [[ ! -d node_modules ]]; then
    npm ci
  fi
  echo
  echo "Running production build..."
  npm run build
fi

echo
echo "Changed files:"
if [[ "${HECATE_PATCH_SKIP_GIT:-0}" != "1" ]]; then
  git status --short
fi

echo
echo "BUILD PASSED — ready to commit."

if [[ "${HECATE_PATCH_SKIP_GIT:-0}" != "1" ]]; then
  rm -f "$SCRIPT_PATH" "$PROJECT_ROOT/hecate946-mobile-polish-patch.zip"
fi
