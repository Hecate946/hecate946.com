const DISCLOSURE_SELECTOR = '[data-disclosure]';
const BODY_SELECTOR = '[data-disclosure-body]';
const DEFAULT_DURATION_MS = 820;

const closeTimers = new WeakMap<HTMLDetailsElement, number>();
const closeListeners = new WeakMap<HTMLDetailsElement, (event: TransitionEvent) => void>();

type DisclosureWindow = Window &
  typeof globalThis & {
    __hecateDisclosureSwapListenerInstalled?: boolean;
  };

const isHtmlMode = () => document.documentElement.dataset.htmlMode === 'true';

const prefersReducedMotion = () =>
  window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const parseDuration = (value: string) => {
  const normalized = value.trim();
  if (!normalized) return DEFAULT_DURATION_MS;

  if (normalized.endsWith('ms')) {
    const milliseconds = Number.parseFloat(normalized);
    return Number.isFinite(milliseconds) ? milliseconds : DEFAULT_DURATION_MS;
  }

  if (normalized.endsWith('s')) {
    const seconds = Number.parseFloat(normalized);
    return Number.isFinite(seconds) ? seconds * 1000 : DEFAULT_DURATION_MS;
  }

  const milliseconds = Number.parseFloat(normalized);
  return Number.isFinite(milliseconds) ? milliseconds : DEFAULT_DURATION_MS;
};

const disclosureDuration = (details: HTMLDetailsElement) =>
  parseDuration(getComputedStyle(details).getPropertyValue('--disclosure-duration'));

const clearCloseWork = (details: HTMLDetailsElement, body?: HTMLElement) => {
  const timer = closeTimers.get(details);
  if (timer !== undefined) {
    window.clearTimeout(timer);
    closeTimers.delete(details);
  }

  const listener = closeListeners.get(details);
  if (listener && body) {
    body.removeEventListener('transitionend', listener);
    closeListeners.delete(details);
  }
};

const finishClose = (details: HTMLDetailsElement) => {
  if (details.hasAttribute('data-expanded')) return;

  const body = details.querySelector<HTMLElement>(`:scope > ${BODY_SELECTOR}`);
  clearCloseWork(details, body ?? undefined);
  details.open = false;
  details.removeAttribute('data-closing');
};

const openDisclosure = (details: HTMLDetailsElement, body: HTMLElement) => {
  clearCloseWork(details, body);
  details.removeAttribute('data-closing');

  if (!details.open) {
    /*
     * Expose the native details content in its collapsed 0fr state first.
     * Forcing one layout here guarantees the browser has a real start state
     * before data-expanded switches the grid track to 1fr.
     */
    details.open = true;
    void body.offsetHeight;
  }

  details.setAttribute('data-expanded', '');
};

const closeDisclosure = (details: HTMLDetailsElement, body: HTMLElement) => {
  clearCloseWork(details, body);
  details.setAttribute('data-closing', '');
  details.removeAttribute('data-expanded');

  const onTransitionEnd = (event: TransitionEvent) => {
    if (event.target !== body || event.propertyName !== 'grid-template-rows') return;

    body.removeEventListener('transitionend', onTransitionEnd);
    closeListeners.delete(details);
    finishClose(details);
  };

  closeListeners.set(details, onTransitionEnd);
  body.addEventListener('transitionend', onTransitionEnd);

  /* transitionend may not fire if the page is backgrounded or motion rules
     change during the transition, so keep a small fallback timer. */
  const timer = window.setTimeout(
    () => finishClose(details),
    disclosureDuration(details) + 80,
  );
  closeTimers.set(details, timer);
};

const syncNativeState = (details: HTMLDetailsElement) => {
  const body = details.querySelector<HTMLElement>(`:scope > ${BODY_SELECTOR}`);
  clearCloseWork(details, body ?? undefined);
  details.removeAttribute('data-closing');
  details.toggleAttribute('data-expanded', details.open);
};

const connectDisclosure = (details: HTMLDetailsElement) => {
  if (details.dataset.disclosureConnected === 'true') return;

  const summary = details.querySelector<HTMLElement>(':scope > summary');
  const body = details.querySelector<HTMLElement>(`:scope > ${BODY_SELECTOR}`);
  if (!summary || !body) return;

  details.dataset.disclosureConnected = 'true';
  details.toggleAttribute('data-expanded', details.open);

  summary.addEventListener('click', (event) => {
    /* HTML mode deliberately falls back to the browser-native disclosure. */
    if (isHtmlMode() || prefersReducedMotion()) return;

    event.preventDefault();

    const shouldOpen = !details.open || details.hasAttribute('data-closing');

    /*
     * Defer state changes until the click has bubbled. The site's existing
     * sound handler reads the pre-toggle native <details> state to choose its
     * dropdown-open/dropdown-close sound.
     */
    queueMicrotask(() => {
      if (shouldOpen) {
        openDisclosure(details, body);
      } else {
        closeDisclosure(details, body);
      }
    });
  });

  details.addEventListener('toggle', () => {
    if (isHtmlMode() || prefersReducedMotion()) syncNativeState(details);
  });
};

export function initializeDisclosures() {
  document
    .querySelectorAll<HTMLDetailsElement>(DISCLOSURE_SELECTOR)
    .forEach(connectDisclosure);
}

export function installDisclosures() {
  initializeDisclosures();

  const disclosureWindow = window as DisclosureWindow;
  if (disclosureWindow.__hecateDisclosureSwapListenerInstalled) return;

  disclosureWindow.__hecateDisclosureSwapListenerInstalled = true;
  document.addEventListener('astro:after-swap', initializeDisclosures);
}
