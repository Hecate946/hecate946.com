const HTML_MODE_STORAGE_KEY = 'html-mode';
const HTML_MODE_ENABLED_VALUE = 'html';
const HTML_MODE_DISABLED_VALUE = 'standard';

type HtmlModeWindow = Window &
  typeof globalThis & {
    __hecateApplyHtmlPresentation?: (
      targetDocument: Document,
      htmlEnabled: boolean,
    ) => void;
  };

const readStoredHtmlMode = () => {
  try {
    return localStorage.getItem(HTML_MODE_STORAGE_KEY);
  } catch {
    return null;
  }
};

const isHtmlModeEnabled = () =>
  document.documentElement.dataset.htmlMode === 'true';

const updateThemeColor = (htmlEnabled: boolean) => {
  const meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
  if (!meta) return;

  if (htmlEnabled) {
    meta.setAttribute('content', '#ffffff');
    return;
  }

  requestAnimationFrame(() => {
    const color = getComputedStyle(document.documentElement)
      .getPropertyValue('--header-bg')
      .trim();
    if (color) meta.setAttribute('content', color);
  });
};

const updateControls = (htmlEnabled: boolean) => {
  document
    .querySelectorAll<HTMLButtonElement>('[data-html-mode-toggle]')
    .forEach((button) => {
      const label = htmlEnabled ? 'Return to standard site' : 'HTML mode';
      button.setAttribute('aria-pressed', String(htmlEnabled));
      button.setAttribute('aria-label', label);
      button.dataset.label = label;

      const text = button.querySelector<HTMLElement>('[data-html-mode-text]');
      if (text) text.textContent = label;
    });
};

const applyHtmlMode = (htmlEnabled: boolean) => {
  const root = document.documentElement;
  root.dataset.htmlMode = String(htmlEnabled);

  const htmlModeWindow = window as HtmlModeWindow;
  htmlModeWindow.__hecateApplyHtmlPresentation?.(document, htmlEnabled);

  if (!htmlEnabled) {
    root.style.colorScheme = root.dataset.theme === 'dark' ? 'dark' : 'light';
  }

  updateControls(htmlEnabled);
  updateThemeColor(htmlEnabled);
};

const applyStoredHtmlMode = () => {
  applyHtmlMode(readStoredHtmlMode() === HTML_MODE_ENABLED_VALUE);
};

const setHtmlMode = (htmlEnabled: boolean) => {
  applyHtmlMode(htmlEnabled);

  try {
    localStorage.setItem(
      HTML_MODE_STORAGE_KEY,
      htmlEnabled ? HTML_MODE_ENABLED_VALUE : HTML_MODE_DISABLED_VALUE,
    );
  } catch {
    // The mode still applies for the current page if storage is unavailable.
  }
};

export function initializeHtmlMode() {
  applyStoredHtmlMode();

  document
    .querySelectorAll<HTMLButtonElement>('[data-html-mode-toggle]')
    .forEach((button) => {
      if (button.dataset.htmlModeConnected === 'true') return;
      button.dataset.htmlModeConnected = 'true';

      button.addEventListener('click', () => {
        setHtmlMode(!isHtmlModeEnabled());
      });
    });
}
