const SOUND_QUERY_KEY = 'sounds';
const SOUND_QUERY_ON = 'on';
const SOUND_QUERY_OFF = 'off';

type SoundKind =
  | 'click'
  | 'page'
  | 'redirect'
  | 'swoosh'
  | 'dropdown-open'
  | 'dropdown-close'
  | 'collision-note';

type WebkitWindow = Window &
  typeof globalThis & {
    webkitAudioContext?: typeof AudioContext;
  };

let audioContext: AudioContext | null = null;
let pageTurnAudio: HTMLAudioElement | null = null;
let toastTimer: number | undefined;
let collisionNoteIndex = 0;
let nextCollisionNoteTime = 0;

// One note advances on each new node collision in the home force graph.
// C F G Ab F Db F C G Ab F Db F G Eb C Eb G D G3 D G E G3 E G
const COLLISION_NOTE_SEQUENCE = [
  261.63, 349.23, 392, 415.3, 349.23, 277.18, 349.23, 261.63, 392, 415.3, 349.23,
  277.18, 349.23, 392, 311.13, 261.63, 311.13, 392, 293.66, 196, 293.66, 392, 329.63,
  196, 329.63, 392,
] as const;

type SiteSoundWindow = Window &
  typeof globalThis & {
    __hecateSiteSoundInstalled?: boolean;
  };

const soundModeFromUrl = (value: string | URL = window.location.href) => {
  try {
    const url = value instanceof URL ? value : new URL(value, window.location.href);
    return url.searchParams.get(SOUND_QUERY_KEY);
  } catch {
    return null;
  }
};

const isEnabled = () => soundModeFromUrl() === SOUND_QUERY_ON;

const getAudioContext = () => {
  if (audioContext) return audioContext;

  const Context = window.AudioContext ?? (window as WebkitWindow).webkitAudioContext;
  if (!Context) return null;

  audioContext = new Context();
  return audioContext;
};

const createNoiseBuffer = (context: AudioContext, seconds: number) => {
  const frameCount = Math.max(1, Math.floor(context.sampleRate * seconds));
  const buffer = context.createBuffer(1, frameCount, context.sampleRate);
  const data = buffer.getChannelData(0);

  for (let index = 0; index < frameCount; index += 1) {
    data[index] = Math.random() * 2 - 1;
  }

  return buffer;
};

const connectMaster = (context: AudioContext, volume: number) => {
  const gain = context.createGain();
  gain.gain.value = volume;
  gain.connect(context.destination);
  return gain;
};

const playClick = (context: AudioContext, now: number) => {
  // A quick, deep mechanical-keyboard press: strong bass body, a low wooden
  // clack, and a tight switch return. The whole sound lands in about 130 ms.
  const master = connectMaster(context, 0.72);
  const compressor = context.createDynamicsCompressor();
  compressor.threshold.value = -24;
  compressor.knee.value = 14;
  compressor.ratio.value = 5;
  compressor.attack.value = 0.001;
  compressor.release.value = 0.09;
  compressor.connect(master);

  const body = context.createOscillator();
  const bodyGain = context.createGain();
  const bodyFilter = context.createBiquadFilter();
  body.type = 'sine';
  body.frequency.setValueAtTime(96, now);
  body.frequency.exponentialRampToValueAtTime(49, now + 0.085);
  bodyFilter.type = 'lowpass';
  bodyFilter.frequency.value = 310;
  bodyFilter.Q.value = 0.9;
  bodyGain.gain.setValueAtTime(0.0001, now);
  bodyGain.gain.exponentialRampToValueAtTime(1, now + 0.0015);
  bodyGain.gain.exponentialRampToValueAtTime(0.16, now + 0.052);
  bodyGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.125);
  body.connect(bodyFilter).connect(bodyGain).connect(compressor);
  body.start(now);
  body.stop(now + 0.13);

  const wood = context.createOscillator();
  const woodGain = context.createGain();
  wood.type = 'triangle';
  wood.frequency.setValueAtTime(205, now);
  wood.frequency.exponentialRampToValueAtTime(118, now + 0.038);
  woodGain.gain.setValueAtTime(0.0001, now);
  woodGain.gain.exponentialRampToValueAtTime(0.58, now + 0.001);
  woodGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.055);
  wood.connect(woodGain).connect(compressor);
  wood.start(now);
  wood.stop(now + 0.06);

  const impact = context.createBufferSource();
  const impactGain = context.createGain();
  const impactFilter = context.createBiquadFilter();
  impact.buffer = createNoiseBuffer(context, 0.032);
  impactFilter.type = 'bandpass';
  impactFilter.frequency.value = 780;
  impactFilter.Q.value = 1.55;
  impactGain.gain.setValueAtTime(0.5, now);
  impactGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.03);
  impact.connect(impactFilter).connect(impactGain).connect(compressor);
  impact.start(now);

  const returnStart = now + 0.052;
  const keyReturn = context.createOscillator();
  const returnGain = context.createGain();
  const returnFilter = context.createBiquadFilter();
  keyReturn.type = 'sine';
  keyReturn.frequency.setValueAtTime(76, returnStart);
  keyReturn.frequency.exponentialRampToValueAtTime(51, returnStart + 0.045);
  returnFilter.type = 'lowpass';
  returnFilter.frequency.value = 230;
  returnGain.gain.setValueAtTime(0.0001, returnStart);
  returnGain.gain.exponentialRampToValueAtTime(0.32, returnStart + 0.002);
  returnGain.gain.exponentialRampToValueAtTime(0.0001, returnStart + 0.065);
  keyReturn.connect(returnFilter).connect(returnGain).connect(compressor);
  keyReturn.start(returnStart);
  keyReturn.stop(returnStart + 0.07);
};

const playCollisionNote = (context: AudioContext, now: number) => {
  const frequency = COLLISION_NOTE_SEQUENCE[collisionNoteIndex];
  collisionNoteIndex = (collisionNoteIndex + 1) % COLLISION_NOTE_SEQUENCE.length;

  const master = connectMaster(context, 0.17);
  const fundamental = context.createOscillator();
  const fundamentalGain = context.createGain();
  const harmonic = context.createOscillator();
  const harmonicGain = context.createGain();

  fundamental.type = 'sine';
  fundamental.frequency.setValueAtTime(frequency, now);
  fundamentalGain.gain.setValueAtTime(0.0001, now);
  fundamentalGain.gain.exponentialRampToValueAtTime(0.82, now + 0.006);
  fundamentalGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.25);
  fundamental.connect(fundamentalGain).connect(master);
  fundamental.start(now);
  fundamental.stop(now + 0.27);

  harmonic.type = 'triangle';
  harmonic.frequency.setValueAtTime(frequency * 2, now);
  harmonicGain.gain.setValueAtTime(0.0001, now);
  harmonicGain.gain.exponentialRampToValueAtTime(0.16, now + 0.004);
  harmonicGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.17);
  harmonic.connect(harmonicGain).connect(master);
  harmonic.start(now);
  harmonic.stop(now + 0.19);
};

const getPageTurnAudio = () => {
  if (pageTurnAudio) return pageTurnAudio;

  pageTurnAudio = new Audio('/audio/page.mp3');
  pageTurnAudio.preload = 'auto';
  pageTurnAudio.volume = 0.55;
  return pageTurnAudio;
};

const playPageTurn = () => {
  const template = getPageTurnAudio();
  const sound = template.cloneNode(true) as HTMLAudioElement;
  sound.volume = 0.55;
  void sound.play().catch(() => undefined);
};

const playRedirect = (context: AudioContext, now: number) => {
  const master = connectMaster(context, 0.28);
  const source = context.createBufferSource();
  const gain = context.createGain();
  const filter = context.createBiquadFilter();

  source.buffer = createNoiseBuffer(context, 0.34);
  filter.type = 'bandpass';
  filter.Q.value = 1.2;
  filter.frequency.setValueAtTime(420, now);
  filter.frequency.exponentialRampToValueAtTime(2350, now + 0.18);
  filter.frequency.exponentialRampToValueAtTime(980, now + 0.33);
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(0.9, now + 0.035);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.34);

  source.connect(filter).connect(gain).connect(master);
  source.start(now);
};

const playSwoosh = (context: AudioContext, now: number) => {
  const source = context.createBufferSource();
  const master = connectMaster(context, 0.31);
  const gain = context.createGain();
  const filter = context.createBiquadFilter();

  source.buffer = createNoiseBuffer(context, 0.82);
  filter.type = 'bandpass';
  filter.Q.value = 1.05;
  filter.frequency.setValueAtTime(320, now);
  filter.frequency.exponentialRampToValueAtTime(4700, now + 0.48);
  filter.frequency.exponentialRampToValueAtTime(2100, now + 0.8);
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(1, now + 0.13);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.82);

  source.connect(filter).connect(gain).connect(master);
  source.start(now);
};

const playDropdown = (context: AudioContext, now: number, closing: boolean) => {
  const master = connectMaster(context, 0.2);
  const notes = [261.63, 293.66, 329.63, 349.23, 392, 440, 493.88, 523.25];
  const sequence = closing ? [...notes].reverse() : notes;

  sequence.forEach((frequency, index) => {
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    const start = now + index * 0.034;

    oscillator.type = 'triangle';
    oscillator.frequency.setValueAtTime(frequency, start);
    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.exponentialRampToValueAtTime(0.68, start + 0.004);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.075);

    oscillator.connect(gain).connect(master);
    oscillator.start(start);
    oscillator.stop(start + 0.08);
  });
};

const playSound = async (kind: SoundKind) => {
  if (!isEnabled()) return;

  // HTMLAudio must start synchronously inside the click gesture. Awaiting an
  // AudioContext resume first lets immediate navigation unload the page before
  // the MP3 ever begins.
  if (kind === 'page') {
    playPageTurn();
    return;
  }

  const context = getAudioContext();
  if (!context) return;

  if (context.state === 'suspended') {
    await context.resume();
  }

  const now = context.currentTime + 0.002;
  if (kind === 'redirect') playRedirect(context, now);
  else if (kind === 'swoosh') playSwoosh(context, now);
  else if (kind === 'dropdown-open') playDropdown(context, now, false);
  else if (kind === 'dropdown-close') playDropdown(context, now, true);
  else if (kind === 'collision-note') playCollisionNote(context, now);
  else playClick(context, now);
};

let toastSequence = 0;

const animateToast = (
  toast: HTMLElement,
  keyframes: Keyframe[],
  options: KeyframeAnimationOptions,
) => {
  toast.getAnimations().forEach((animation) => animation.cancel());
  return toast.animate(keyframes, options);
};

const showToast = (message: string) => {
  const toast = document.querySelector<HTMLElement>('[data-site-sound-toast]');
  if (!toast) return;

  window.clearTimeout(toastTimer);
  const sequence = ++toastSequence;
  const computed = window.getComputedStyle(toast);
  const currentOpacity = Number.parseFloat(computed.opacity) || 0;
  const currentTransform = computed.transform === 'none'
    ? 'translate(-50%, calc(-50% + 0.45rem))'
    : computed.transform;

  const revealMessage = () => {
    if (sequence !== toastSequence) return;

    toast.textContent = message;
    toast.dataset.visible = 'true';
    toast.style.opacity = '0';
    toast.style.transform = 'translate(-50%, calc(-50% + 0.35rem))';

    const entrance = animateToast(
      toast,
      [
        { opacity: 0, transform: 'translate(-50%, calc(-50% + 0.35rem))' },
        { opacity: 1, transform: 'translate(-50%, -50%)' },
      ],
      { duration: 460, easing: 'cubic-bezier(0.22, 1, 0.36, 1)', fill: 'forwards' },
    );

    entrance.onfinish = () => {
      if (sequence !== toastSequence) return;
      toast.style.opacity = '1';
      toast.style.transform = 'translate(-50%, -50%)';
    };

    toastTimer = window.setTimeout(() => {
      if (sequence !== toastSequence) return;
      const exit = animateToast(
        toast,
        [
          { opacity: 1, transform: 'translate(-50%, -50%)' },
          { opacity: 0, transform: 'translate(-50%, calc(-50% - 0.2rem))' },
        ],
        { duration: 560, easing: 'cubic-bezier(0.4, 0, 0.2, 1)', fill: 'forwards' },
      );

      exit.onfinish = () => {
        if (sequence !== toastSequence) return;
        toast.dataset.visible = 'false';
        toast.style.opacity = '0';
        toast.style.transform = 'translate(-50%, calc(-50% + 0.45rem))';
      };
    }, 3_250);
  };

  if (currentOpacity > 0.03) {
    const transitionOut = animateToast(
      toast,
      [
        { opacity: currentOpacity, transform: currentTransform },
        { opacity: 0, transform: 'translate(-50%, calc(-50% - 0.12rem))' },
      ],
      { duration: 190, easing: 'ease-out', fill: 'forwards' },
    );
    transitionOut.onfinish = revealMessage;
  } else {
    revealMessage();
  }
};

const updateToggle = (enabled = isEnabled()) => {
  document.querySelectorAll<HTMLButtonElement>('[data-sound-toggle]').forEach((toggle) => {
    const label = enabled ? 'Disable sounds' : 'Enable sounds';
    toggle.setAttribute('aria-pressed', String(enabled));
    toggle.setAttribute('aria-label', label);
    toggle.dataset.label = label;
    const text = toggle.querySelector<HTMLElement>('[data-sound-toggle-text]');
    if (text) text.textContent = label;
  });
};

const isExternalLink = (anchor: HTMLAnchorElement) => {
  const href = anchor.getAttribute('href') ?? '';
  if (/^(mailto:|tel:|sms:)/i.test(href)) return true;

  try {
    const url = new URL(anchor.href, window.location.href);
    return url.origin !== window.location.origin;
  } catch {
    return false;
  }
};

const normalizePathname = (pathname: string) => {
  const normalized = pathname.replace(/\/+$/, '');
  return normalized || '/';
};

const isPageChangeLink = (anchor: HTMLAnchorElement) => {
  const href = anchor.getAttribute('href');
  if (!href || href.startsWith('#') || href.startsWith('javascript:')) return false;

  try {
    const target = new URL(anchor.href, window.location.href);
    return (
      target.origin === window.location.origin &&
      (normalizePathname(target.pathname) !== normalizePathname(window.location.pathname) ||
        target.search !== window.location.search)
    );
  } catch {
    return false;
  }
};

const handleClick = (event: MouseEvent) => {
  const target = event.target;
  if (!(target instanceof Element)) return;

  const toggle = target.closest<HTMLButtonElement>('[data-sound-toggle]');
  if (toggle) {
    const enabled = !isEnabled();
    const url = new URL(window.location.href);
    url.searchParams.set(
      SOUND_QUERY_KEY,
      enabled ? SOUND_QUERY_ON : SOUND_QUERY_OFF,
    );

    // The URL is the only sound state. Replace it first, then mirror that value
    // to the root attribute and controls in the same click task.
    window.history.replaceState(
      window.history.state,
      '',
      `${url.pathname}${url.search}${url.hash}`,
    );
    document.documentElement.dataset.soundEnabled = String(enabled);
    updateToggle(enabled);

    if (enabled) {
      void playSound('click');
      showToast('Sounds are enabled, click again to disable');
    } else {
      showToast('Sounds are disabled');
    }
    return;
  }

  if (!isEnabled()) return;

  const summary = target.closest('summary');
  const select = target.closest('select');
  if (summary) {
    const details = summary.closest('details');
    const isClosing = Boolean(details?.open && !details.hasAttribute('data-closing'));
    void playSound(isClosing ? 'dropdown-close' : 'dropdown-open');
    return;
  }
  if (select) {
    void playSound('dropdown-open');
    return;
  }

  const anchor = target.closest<HTMLAnchorElement>('a[href]');
  if (anchor) {
    if (isExternalLink(anchor)) {
      void playSound('swoosh');
    } else if (isPageChangeLink(anchor)) {
      const isNavbarLink = Boolean(anchor.closest('.site-header'));
      void playSound(isNavbarLink ? 'page' : 'redirect');

    }
    // Same-path/hash-only navigation is intentionally silent.
    return;
  }

  if (target.closest('button, [role="button"], input[type="button"], input[type="submit"], input[type="reset"]')) {
    void playSound('click');
  }
};

const handleChange = (event: Event) => {
  if (!isEnabled()) return;
  const target = event.target;
  if (target instanceof HTMLSelectElement) void playSound('dropdown-close');
};

export const unlockSiteSound = () => {
  if (!isEnabled()) return;

  const context = getAudioContext();
  if (context?.state === 'suspended') void context.resume();
};

export const playNetworkCollisionNote = async () => {
  if (!isEnabled()) return;

  const context = getAudioContext();
  if (!context) return;
  if (context.state === 'suspended') await context.resume();

  const startTime = Math.max(context.currentTime + 0.002, nextCollisionNoteTime);
  nextCollisionNoteTime = startTime + 0.065;
  playCollisionNote(context, startTime);
};

const applySoundStateFromUrl = () => {
  const enabled = isEnabled();
  document.documentElement.dataset.soundEnabled = String(enabled);
  updateToggle(enabled);
};

export const initializeSiteSound = () => {
  applySoundStateFromUrl();
  getPageTurnAudio().load();

  const siteSoundWindow = window as SiteSoundWindow;
  if (siteSoundWindow.__hecateSiteSoundInstalled) return;

  siteSoundWindow.__hecateSiteSoundInstalled = true;
  document.addEventListener('click', handleClick, { capture: true });
  document.addEventListener('change', handleChange, { capture: true });
  window.addEventListener('popstate', applySoundStateFromUrl);
};
