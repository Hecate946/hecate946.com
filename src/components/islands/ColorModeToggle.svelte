<script lang="ts">
  import { trackEvent } from '@/lib/analytics';

  type ColorTheme = 'light' | 'dark';

  function updateThemeColor() {
    requestAnimationFrame(() => {
      const themeColor = getComputedStyle(document.documentElement)
        .getPropertyValue('--bg')
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
      // The theme still applies if storage is unavailable.
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

<div class="mode-control">
  <button
    type="button"
    class="header-action mode-action"
    aria-label="Toggle color mode"
    title="Toggle light and dark mode"
    onclick={toggleTheme}
  >
    <span class="header-action-icon mode-icon" aria-hidden="true">
      <svg class="mode-sun" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="4"></circle>
        <path
          d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.66 6.34l1.41-1.41"
        ></path>
      </svg>

      <svg class="mode-moon" viewBox="0 0 24 24">
        <path d="M20.2 15.25A8.5 8.5 0 0 1 8.75 3.8 8.5 8.5 0 1 0 20.2 15.25Z"></path>
      </svg>
    </span>
  </button>

  <span class="mode-label">Mode</span>
</div>
