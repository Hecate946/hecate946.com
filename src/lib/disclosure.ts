const DISCLOSURE_SELECTOR = '[data-disclosure]';
const BODY_SELECTOR = '[data-disclosure-body]';
const DEFAULT_DURATION_MS = 820;
const DEFAULT_EASING = 'cubic-bezier(0.45, 0, 0.55, 1)';

const activeAnimations = new WeakMap<HTMLDetailsElement, Animation>();

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

const animationOptions = (details: HTMLDetailsElement): KeyframeAnimationOptions => {
  const styles = getComputedStyle(details);

  return {
    duration: parseDuration(styles.getPropertyValue('--disclosure-duration')),
    easing: styles.getPropertyValue('--disclosure-easing').trim() || DEFAULT_EASING,
    fill: 'both',
  };
};

const finishAnimation = (
  details: HTMLDetailsElement,
  animation: Animation,
  closeWhenFinished: boolean,
) => {
  animation.onfinish = () => {
    if (activeAnimations.get(details) !== animation) return;

    if (closeWhenFinished) details.open = false;
    details.removeAttribute('data-closing');
    activeAnimations.delete(details);
    animation.cancel();
  };
};

const animateOpen = (details: HTMLDetailsElement, body: HTMLElement) => {
  const currentHeight = body.getBoundingClientRect().height;
  activeAnimations.get(details)?.cancel();

  details.removeAttribute('data-closing');
  details.open = true;

  const targetHeight = body.scrollHeight;
  const animation = body.animate(
    [
      { height: `${currentHeight}px` },
      { height: `${targetHeight}px` },
    ],
    animationOptions(details),
  );

  activeAnimations.set(details, animation);
  finishAnimation(details, animation, false);
};

const animateClosed = (details: HTMLDetailsElement, body: HTMLElement) => {
  const currentHeight = body.getBoundingClientRect().height;
  activeAnimations.get(details)?.cancel();

  details.setAttribute('data-closing', '');

  const animation = body.animate(
    [
      { height: `${currentHeight}px` },
      { height: '0px' },
    ],
    animationOptions(details),
  );

  activeAnimations.set(details, animation);
  finishAnimation(details, animation, true);
};

const connectDisclosure = (details: HTMLDetailsElement) => {
  if (details.dataset.disclosureConnected === 'true') return;

  const summary = details.querySelector<HTMLElement>(':scope > summary');
  const body = details.querySelector<HTMLElement>(`:scope > ${BODY_SELECTOR}`);
  if (!summary || !body) return;

  details.dataset.disclosureConnected = 'true';

  summary.addEventListener('click', (event) => {
    /* HTML mode deliberately falls back to the browser-native disclosure. */
    if (isHtmlMode() || prefersReducedMotion()) return;

    event.preventDefault();

    const shouldOpen = !details.open || details.hasAttribute('data-closing');

    /*
     * Defer the visual state change until the click has bubbled. The site's
     * existing sound handler reads the native pre-toggle <details> state to
     * choose its dropdown-open/dropdown-close sound.
     */
    queueMicrotask(() => {
      if (shouldOpen) {
        animateOpen(details, body);
      } else {
        animateClosed(details, body);
      }
    });
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
