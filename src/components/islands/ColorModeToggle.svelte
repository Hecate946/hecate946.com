<script lang="ts">
  import { trackEvent } from '@/lib/analytics';

  type ColorTheme = 'light' | 'dark';

  function updateThemeColor() {
    requestAnimationFrame(() => {
      const themeColor = getComputedStyle(document.documentElement)
        .getPropertyValue('--header-bg')
        .trim();

      if (themeColor) {
        document
          .querySelector<HTMLMetaElement>('meta[name="theme-color"]')
          ?.setAttribute('content', themeColor);
      }
    });
  }

  function applyTheme(next: ColorTheme) {
    document.documentElement.dataset.theme = next;
    document.documentElement.style.colorScheme = next;

    try {
      localStorage.setItem('color-theme', next);
    } catch {
      // The selected theme still applies for this page if storage is blocked.
    }

    updateThemeColor();
    trackEvent('color_theme_changed', { theme: next });
  }

  function toggleTheme() {
    const current =
      document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
    applyTheme(current === 'light' ? 'dark' : 'light');
  }
</script>

<button
  type="button"
  class="mode-toggle"
  onclick={toggleTheme}
  aria-label="Toggle light and dark mode"
  title="Toggle light and dark mode"
>
  <span class="mode-state show-in-light" aria-hidden="true">
    <svg viewBox="0 0 24 24">
      <path d="M20.2 15.25A8.5 8.5 0 0 1 8.75 3.8 8.5 8.5 0 1 0 20.2 15.25Z"
      ></path>
    </svg>
    <span class="mode-label">Dark mode</span>
  </span>

  <span class="mode-state show-in-dark" aria-hidden="true">
    <svg viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="4"></circle>
      <path
        d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.66 6.34l1.41-1.41"
      ></path>
    </svg>
    <span class="mode-label">Light mode</span>
  </span>
</button>

<style>
  .mode-toggle {
    display: flex;
    width: 100%;
    height: 100%;
    min-width: 0;
    align-items: center;
    justify-content: center;
    padding-inline: 1rem;
    border: 0;
    background: transparent !important;
    color: var(--header-text);
    cursor: pointer;
    font-family: var(--font-sans);
    font-size: var(--nav-font-size);
    font-weight: var(--nav-font-weight);
    line-height: 1;
  }

  .mode-state {
    display: none;
    min-width: 0;
    align-items: center;
    justify-content: center;
    gap: 0.58rem;
    color: inherit;
    white-space: nowrap;
  }

  :global(html[data-theme='light']) .show-in-light,
  :global(html[data-theme='dark']) .show-in-dark {
    display: flex;
  }

  .mode-label {
    color: inherit;
    text-decoration-line: underline;
    text-decoration-color: transparent;
    text-decoration-thickness: 0.11em;
    text-underline-offset: 0.34em;
    transition: text-decoration-color 140ms ease;
  }

  .mode-toggle:hover,
  .mode-toggle:focus-visible,
  .mode-toggle:active {
    background: transparent !important;
    color: var(--header-text);
  }

  .mode-toggle:hover .mode-label,
  .mode-toggle:focus-visible .mode-label {
    text-decoration-color: var(--nav-underline-color);
  }

  svg {
    width: 1.55rem;
    height: 1.55rem;
    flex: 0 0 auto;
    fill: none;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.8;
  }

  @media (max-width: 58rem) {
    .mode-toggle {
      padding-inline: 0.75rem;
    }

    .mode-state {
      gap: 0.5rem;
    }

    svg {
      width: 1.5rem;
      height: 1.5rem;
    }
  }

  @media (max-width: 24rem) {
    .mode-toggle {
      padding-inline: 0.45rem;
    }

    .mode-state {
      gap: 0.38rem;
    }

    svg {
      width: 1.35rem;
      height: 1.35rem;
    }
  }
</style>
