const DISPLAY_MODE_STORAGE_KEY = 'hecate946:display-mode';
const ASCII_MODE = 'ascii';
const DEFAULT_MODE = 'default';

type DisplayMode = typeof ASCII_MODE | typeof DEFAULT_MODE;

const readMode = (): DisplayMode => {
  try {
    return localStorage.getItem(DISPLAY_MODE_STORAGE_KEY) === ASCII_MODE
      ? ASCII_MODE
      : DEFAULT_MODE;
  } catch {
    return DEFAULT_MODE;
  }
};

const writeMode = (mode: DisplayMode) => {
  try {
    if (mode === ASCII_MODE) {
      localStorage.setItem(DISPLAY_MODE_STORAGE_KEY, ASCII_MODE);
    } else {
      localStorage.removeItem(DISPLAY_MODE_STORAGE_KEY);
    }
  } catch {
    // The current page can still switch modes when storage is unavailable.
  }
};

const updateThemeColor = () => {
  requestAnimationFrame(() => {
    const color = getComputedStyle(document.documentElement)
      .getPropertyValue('--header-bg')
      .trim();
    if (!color) return;

    document
      .querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]')
      .forEach((meta) => meta.setAttribute('content', color));
  });
};

const updateControls = (asciiEnabled: boolean) => {
  document
    .querySelectorAll<HTMLButtonElement>('[data-display-mode-toggle]')
    .forEach((button) => {
      const label = asciiEnabled
        ? 'Return to standard site'
        : 'Enable ASCII mode';
      button.setAttribute('aria-pressed', String(asciiEnabled));
      button.setAttribute('aria-label', label);
      button.dataset.label = label;

      const text = button.querySelector<HTMLElement>('[data-display-mode-text]');
      if (text) text.textContent = label;
    });
};

const applyMode = (mode: DisplayMode) => {
  const asciiEnabled = mode === ASCII_MODE;
  document.documentElement.dataset.displayMode = mode;
  document.documentElement.style.colorScheme = asciiEnabled
    ? 'light'
    : document.documentElement.dataset.theme === 'dark'
      ? 'dark'
      : 'light';
  updateControls(asciiEnabled);
  updateThemeColor();
};

export function initializeDisplayMode() {
  applyMode(readMode());

  document
    .querySelectorAll<HTMLButtonElement>('[data-display-mode-toggle]')
    .forEach((button) => {
      if (button.dataset.displayModeConnected === 'true') return;
      button.dataset.displayModeConnected = 'true';

      button.addEventListener('click', () => {
        const nextMode: DisplayMode =
          document.documentElement.dataset.displayMode === ASCII_MODE
            ? DEFAULT_MODE
            : ASCII_MODE;
        writeMode(nextMode);
        applyMode(nextMode);
      });
    });
}
