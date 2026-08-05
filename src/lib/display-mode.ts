const DISPLAY_MODE_STORAGE_KEY = 'hecate946:display-mode';
const ASCII_MODE = 'ascii';
const DEFAULT_MODE = 'default';

let toastTimer: number | undefined;

const readMode = () => {
  try {
    return localStorage.getItem(DISPLAY_MODE_STORAGE_KEY) === ASCII_MODE
      ? ASCII_MODE
      : DEFAULT_MODE;
  } catch {
    return DEFAULT_MODE;
  }
};

const writeMode = (mode: typeof ASCII_MODE | typeof DEFAULT_MODE) => {
  try {
    if (mode === ASCII_MODE) {
      localStorage.setItem(DISPLAY_MODE_STORAGE_KEY, ASCII_MODE);
    } else {
      localStorage.removeItem(DISPLAY_MODE_STORAGE_KEY);
    }
  } catch {
    // The mode still works for the current page when storage is unavailable.
  }
};

const showToast = (message: string) => {
  const toast = document.querySelector<HTMLElement>(
    '[data-display-mode-toast]',
  );
  if (!toast) return;

  window.clearTimeout(toastTimer);
  toast.textContent = message;
  toast.dataset.visible = 'true';

  toastTimer = window.setTimeout(() => {
    toast.dataset.visible = 'false';
  }, 1_350);
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
      const label = asciiEnabled ? 'Exit ASCII mode' : 'Enable ASCII mode';
      button.setAttribute('aria-pressed', String(asciiEnabled));
      button.setAttribute('aria-label', label);
      button.dataset.label = label;
    });
};

const applyMode = (
  mode: typeof ASCII_MODE | typeof DEFAULT_MODE,
  announce = false,
) => {
  const asciiEnabled = mode === ASCII_MODE;
  document.documentElement.dataset.displayMode = mode;
  document.documentElement.style.colorScheme = asciiEnabled
    ? 'dark'
    : document.documentElement.dataset.theme === 'dark'
      ? 'dark'
      : 'light';
  updateControls(asciiEnabled);
  updateThemeColor();

  if (announce) {
    showToast(asciiEnabled ? 'ASCII mode enabled' : 'Standard mode restored');
  }
};

export function initializeDisplayMode() {
  applyMode(readMode());

  document
    .querySelectorAll<HTMLButtonElement>('[data-display-mode-toggle]')
    .forEach((button) => {
      if (button.dataset.displayModeConnected === 'true') return;
      button.dataset.displayModeConnected = 'true';

      button.addEventListener('click', () => {
        const nextMode =
          document.documentElement.dataset.displayMode === ASCII_MODE
            ? DEFAULT_MODE
            : ASCII_MODE;
        writeMode(nextMode);
        applyMode(nextMode, true);
      });
    });
}
