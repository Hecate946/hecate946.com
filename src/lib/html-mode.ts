const HTML_MODE_QUERY_KEY = 'mode';
const HTML_MODE_QUERY_VALUE = 'html';
const SOUND_QUERY_KEY = 'sounds';
const SOUND_QUERY_VALUES = new Set(['on', 'off']);

type HtmlModeWindow = Window &
  typeof globalThis & {
    __hecateHtmlModeHistoryConnected?: boolean;
    __hecateHtmlModeLinksConnected?: boolean;
  };

const urlUsesHtmlMode = (value: string | URL = window.location.href) => {
  try {
    const url = value instanceof URL ? value : new URL(value, window.location.href);
    return url.searchParams.get(HTML_MODE_QUERY_KEY) === HTML_MODE_QUERY_VALUE;
  } catch {
    return false;
  }
};

const isInternalPageLink = (url: URL) => {
  if (url.origin !== window.location.origin) return false;
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return false;

  const lastSegment = url.pathname.split('/').pop() ?? '';
  const extension = lastSegment.match(/\.([a-z0-9]+)$/i)?.[1]?.toLowerCase();
  return !extension || extension === 'html' || extension === 'htm';
};

const writeAnchorUrl = (anchor: HTMLAnchorElement, url: URL) => {
  anchor.href = `${url.pathname}${url.search}${url.hash}`;
};

const prepareAnchorForShareableModes = (anchor: HTMLAnchorElement) => {
  try {
    const currentUrl = new URL(window.location.href);
    const targetUrl = new URL(anchor.href, currentUrl);
    if (!isInternalPageLink(targetUrl)) return;

    const htmlEnabled = urlUsesHtmlMode(currentUrl);
    const soundMode = currentUrl.searchParams.get(SOUND_QUERY_KEY);
    const hasShareableSoundMode = Boolean(
      soundMode && SOUND_QUERY_VALUES.has(soundMode),
    );

    if (!htmlEnabled && !hasShareableSoundMode) return;

    if (htmlEnabled) {
      targetUrl.searchParams.set(HTML_MODE_QUERY_KEY, HTML_MODE_QUERY_VALUE);
    }

    if (hasShareableSoundMode && soundMode) {
      targetUrl.searchParams.set(SOUND_QUERY_KEY, soundMode);
    }

    writeAnchorUrl(anchor, targetUrl);
  } catch {
    // Leave malformed or non-URL href values to the browser.
  }
};

const removeHtmlModeFromInternalLinks = () => {
  document.querySelectorAll<HTMLAnchorElement>('a[href]').forEach((anchor) => {
    try {
      const url = new URL(anchor.href, window.location.href);
      if (!isInternalPageLink(url)) return;
      if (url.searchParams.get(HTML_MODE_QUERY_KEY) !== HTML_MODE_QUERY_VALUE) return;

      url.searchParams.delete(HTML_MODE_QUERY_KEY);
      writeAnchorUrl(anchor, url);
    } catch {
      // Leave malformed or non-URL href values to the browser.
    }
  });
};

const prepareLinkFromEvent = (event: Event) => {
  const target = event.target;
  if (!(target instanceof Element)) return;

  const anchor = target.closest<HTMLAnchorElement>('a[href]');
  if (!anchor) return;
  prepareAnchorForShareableModes(anchor);
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

const updateControls = (htmlEnabled: boolean) => {
  document
    .querySelectorAll<HTMLButtonElement>('[data-html-mode-toggle]')
    .forEach((button) => {
      const label = htmlEnabled
        ? 'Return to standard site'
        : 'HTML mode';
      button.setAttribute('aria-pressed', String(htmlEnabled));
      button.setAttribute('aria-label', label);
      button.dataset.label = label;

      const text = button.querySelector<HTMLElement>('[data-html-mode-text]');
      if (text) text.textContent = label;
    });
};

const applyHtmlModeFromUrl = () => {
  // The current URL is deliberately the only HTML-mode state.
  const htmlEnabled = urlUsesHtmlMode();
  document.documentElement.dataset.htmlMode = String(htmlEnabled);
  document.documentElement.style.colorScheme = htmlEnabled
    ? 'light'
    : document.documentElement.dataset.theme === 'dark'
      ? 'dark'
      : 'light';

  if (!htmlEnabled) removeHtmlModeFromInternalLinks();
  updateControls(htmlEnabled);
  updateThemeColor();
};

const setHtmlModeInUrl = (htmlEnabled: boolean) => {
  const url = new URL(window.location.href);

  if (htmlEnabled) {
    url.searchParams.set(HTML_MODE_QUERY_KEY, HTML_MODE_QUERY_VALUE);
  } else {
    url.searchParams.delete(HTML_MODE_QUERY_KEY);
  }

  window.history.replaceState(
    window.history.state,
    '',
    `${url.pathname}${url.search}${url.hash}`,
  );

  applyHtmlModeFromUrl();
};

export function initializeHtmlMode() {
  applyHtmlModeFromUrl();

  document
    .querySelectorAll<HTMLButtonElement>('[data-html-mode-toggle]')
    .forEach((button) => {
      if (button.dataset.htmlModeConnected === 'true') return;
      button.dataset.htmlModeConnected = 'true';

      button.addEventListener('click', () => {
        setHtmlModeInUrl(!urlUsesHtmlMode());
      });
    });

  const htmlModeWindow = window as HtmlModeWindow;

  if (!htmlModeWindow.__hecateHtmlModeLinksConnected) {
    htmlModeWindow.__hecateHtmlModeLinksConnected = true;

    // Keep hrefs untouched while they are merely displayed. This lets the
    // browser own native blue/purple link states without a post-paint color
    // change. Copy shareable URL modes only when a link is activated.
    document.addEventListener('pointerdown', prepareLinkFromEvent, {
      capture: true,
    });
    document.addEventListener('click', prepareLinkFromEvent, { capture: true });
    document.addEventListener('auxclick', prepareLinkFromEvent, {
      capture: true,
    });
  }

  if (!htmlModeWindow.__hecateHtmlModeHistoryConnected) {
    htmlModeWindow.__hecateHtmlModeHistoryConnected = true;
    window.addEventListener('popstate', applyHtmlModeFromUrl);
  }
}
