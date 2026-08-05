const SOUND_STORAGE_KEY = 'hecate946:sound-enabled';
const INITIALIZED_ATTRIBUTE = 'data-site-sound-initialized';

type SoundKind = 'click' | 'page' | 'swoosh' | 'dropdown';

type WebkitWindow = Window &
  typeof globalThis & {
    webkitAudioContext?: typeof AudioContext;
  };

let audioContext: AudioContext | null = null;
let toastTimer: number | undefined;

const isEnabled = () => localStorage.getItem(SOUND_STORAGE_KEY) === 'true';

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
  const master = connectMaster(context, 0.17);
  const oscillator = context.createOscillator();
  const gain = context.createGain();

  oscillator.type = 'sine';
  oscillator.frequency.setValueAtTime(230, now);
  oscillator.frequency.exponentialRampToValueAtTime(92, now + 0.055);
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(1, now + 0.003);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.075);

  oscillator.connect(gain).connect(master);
  oscillator.start(now);
  oscillator.stop(now + 0.08);

  const noise = context.createBufferSource();
  const noiseGain = context.createGain();
  const filter = context.createBiquadFilter();
  noise.buffer = createNoiseBuffer(context, 0.035);
  filter.type = 'highpass';
  filter.frequency.value = 2200;
  noiseGain.gain.setValueAtTime(0.5, now);
  noiseGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.035);
  noise.connect(filter).connect(noiseGain).connect(master);
  noise.start(now);
};

const playPageTurn = (context: AudioContext, now: number) => {
  const source = context.createBufferSource();
  const master = connectMaster(context, 0.115);
  const gain = context.createGain();
  const filter = context.createBiquadFilter();

  source.buffer = createNoiseBuffer(context, 0.32);
  filter.type = 'bandpass';
  filter.Q.value = 0.7;
  filter.frequency.setValueAtTime(850, now);
  filter.frequency.exponentialRampToValueAtTime(3100, now + 0.13);
  filter.frequency.exponentialRampToValueAtTime(720, now + 0.31);
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(1, now + 0.025);
  gain.gain.exponentialRampToValueAtTime(0.18, now + 0.17);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.32);

  source.connect(filter).connect(gain).connect(master);
  source.start(now);
};

const playSwoosh = (context: AudioContext, now: number) => {
  const source = context.createBufferSource();
  const master = connectMaster(context, 0.12);
  const gain = context.createGain();
  const filter = context.createBiquadFilter();

  source.buffer = createNoiseBuffer(context, 0.4);
  filter.type = 'bandpass';
  filter.Q.value = 1.15;
  filter.frequency.setValueAtTime(420, now);
  filter.frequency.exponentialRampToValueAtTime(4200, now + 0.24);
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(1, now + 0.075);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.4);

  source.connect(filter).connect(gain).connect(master);
  source.start(now);
};

const playDropdown = (context: AudioContext, now: number) => {
  const master = connectMaster(context, 0.09);

  for (let index = 0; index < 6; index += 1) {
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    const start = now + index * 0.026;

    oscillator.type = 'triangle';
    oscillator.frequency.setValueAtTime(260 + index * 54, start);
    oscillator.frequency.exponentialRampToValueAtTime(190 + index * 36, start + 0.055);
    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.exponentialRampToValueAtTime(0.72, start + 0.004);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.06);

    oscillator.connect(gain).connect(master);
    oscillator.start(start);
    oscillator.stop(start + 0.065);
  }
};

const playSound = async (kind: SoundKind) => {
  if (!isEnabled()) return;

  const context = getAudioContext();
  if (!context) return;

  if (context.state === 'suspended') {
    await context.resume();
  }

  const now = context.currentTime + 0.002;
  if (kind === 'page') playPageTurn(context, now);
  else if (kind === 'swoosh') playSwoosh(context, now);
  else if (kind === 'dropdown') playDropdown(context, now);
  else playClick(context, now);
};

const showToast = (message: string) => {
  const toast = document.querySelector<HTMLElement>('[data-site-sound-toast]');
  if (!toast) return;

  window.clearTimeout(toastTimer);
  toast.textContent = message;
  toast.dataset.visible = 'true';
  toastTimer = window.setTimeout(() => {
    toast.dataset.visible = 'false';
  }, 1_650);
};

const updateToggle = () => {
  const enabled = isEnabled();
  document.querySelectorAll<HTMLButtonElement>('[data-sound-toggle]').forEach((toggle) => {
    toggle.setAttribute('aria-pressed', String(enabled));
    toggle.setAttribute('aria-label', enabled ? 'Disable site sound' : 'Enable site sound');
    toggle.dataset.label = enabled ? 'Disable sound' : 'Enable sound';
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

const isPageChangeLink = (anchor: HTMLAnchorElement) => {
  const href = anchor.getAttribute('href');
  if (!href || href.startsWith('#') || href.startsWith('javascript:')) return false;

  try {
    const target = new URL(anchor.href, window.location.href);
    return (
      target.origin === window.location.origin &&
      (target.pathname !== window.location.pathname || target.search !== window.location.search)
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
    localStorage.setItem(SOUND_STORAGE_KEY, String(enabled));
    updateToggle();

    if (enabled) {
      void playSound('click');
      showToast('Sounds are enabled — click the sound button at the bottom again to disable.');
    } else {
      showToast('Sounds are disabled.');
    }
    return;
  }

  if (!isEnabled()) return;

  const summary = target.closest('summary');
  const select = target.closest('select');
  if (summary || select) {
    void playSound('dropdown');
    return;
  }

  const anchor = target.closest<HTMLAnchorElement>('a[href]');
  if (anchor) {
    if (isExternalLink(anchor)) {
      void playSound('swoosh');
    } else if (isPageChangeLink(anchor)) {
      void playSound('page');

      const shouldDelayNavigation =
        event.button === 0 &&
        !event.metaKey &&
        !event.ctrlKey &&
        !event.shiftKey &&
        !event.altKey &&
        !anchor.hasAttribute('download') &&
        (!anchor.target || anchor.target === '_self');

      if (shouldDelayNavigation) {
        event.preventDefault();
        window.setTimeout(() => window.location.assign(anchor.href), 135);
      }
    } else {
      void playSound('click');
    }
    return;
  }

  if (target.closest('button, [role="button"], input[type="button"], input[type="submit"], input[type="reset"]')) {
    void playSound('click');
  }
};

const handleChange = (event: Event) => {
  if (!isEnabled()) return;
  const target = event.target;
  if (target instanceof HTMLSelectElement) void playSound('dropdown');
};

export const initializeSiteSound = () => {
  updateToggle();

  if (document.documentElement.hasAttribute(INITIALIZED_ATTRIBUTE)) return;
  document.documentElement.setAttribute(INITIALIZED_ATTRIBUTE, 'true');
  document.addEventListener('click', handleClick, { capture: true });
  document.addEventListener('change', handleChange, { capture: true });
};
