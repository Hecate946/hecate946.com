<script lang="ts">
  import { trackEvent } from '@/lib/analytics';

  type ColorTheme = 'light' | 'dark';

  function resolveBrowserThemeColor() {
    const root = document.documentElement;
    const styles = getComputedStyle(document.body);
    const wallColor = styles.getPropertyValue('--wall-dark').trim();

    if (wallColor) {
      const probe = document.createElement('span');
      probe.style.cssText =
        'position:fixed;pointer-events:none;visibility:hidden;color:var(--wall-dark)';
      document.body.appendChild(probe);
      const resolved = getComputedStyle(probe).color;
      probe.remove();
      if (resolved) return resolved;
    }

    const bodyBackground = styles.backgroundColor;
    if (bodyBackground && bodyBackground !== 'rgba(0, 0, 0, 0)') {
      return bodyBackground;
    }

    return getComputedStyle(root).backgroundColor;
  }

  function updateThemeColor() {
    requestAnimationFrame(() => {
      const themeColor = resolveBrowserThemeColor();
      if (!themeColor) return;

      document
        .querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]')
        .forEach((meta) => meta.setAttribute('content', themeColor));
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
      <svg class="mode-sun" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false">
        <circle cx="12" cy="12" r="4"></circle>
        <path
          d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.66 6.34l1.41-1.41"
        ></path>
      </svg>

      <svg class="mode-moon" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false">
        <path d="M20.2 15.25A8.5 8.5 0 0 1 8.75 3.8 8.5 8.5 0 1 0 20.2 15.25Z"></path>
      </svg>
    </span>
  </button>
</div>
