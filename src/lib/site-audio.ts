export const SFX_VOLUME_STORAGE_KEY = 'site-audio:sfx-volume';
export const MUSIC_VOLUME_STORAGE_KEY = 'site-audio:music-volume';
export const SITE_AUDIO_EVENT = 'hecate:audio-state';

const MUSIC_SOURCE = '/audio/music/kitty-with-the-bent-frame.mp3';

export interface SiteAudioState {
  music: number;
  sfx: number;
  musicAvailable: boolean | null;
}

type AudioWindow = Window &
  typeof globalThis & {
    __hecateSiteMusic?: HTMLAudioElement;
    __hecateAudioGestureInstalled?: boolean;
  };

let initialized = false;
let musicVolume = 0;
let sfxVolume = 0;
let musicAvailable: boolean | null = null;
let musicPlaybackPending = false;

const clampPercent = (value: number) => {
  if (!Number.isFinite(value)) return 0;
  return Math.min(100, Math.max(0, Math.round(value)));
};

const readStoredPercent = (key: string) => {
  try {
    const value = localStorage.getItem(key);
    if (value === null) return 0;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? clampPercent(parsed) : 0;
  } catch {
    return 0;
  }
};

const writeStoredPercent = (key: string, value: number) => {
  try {
    localStorage.setItem(key, String(clampPercent(value)));
  } catch {
    // The current-page setting still applies if storage is unavailable.
  }
};

const syncRootState = () => {
  const root = document.documentElement;
  root.dataset.musicVolume = String(musicVolume);
  root.dataset.sfxVolume = String(sfxVolume);
  // Keep the old attribute as a compatibility signal for any component that
  // has not yet migrated from the original boolean site-sound preference.
  root.dataset.soundEnabled = String(sfxVolume > 0);
  root.dataset.audioActive = String(musicVolume > 0 || sfxVolume > 0);
};

const currentState = (): SiteAudioState => ({
  music: musicVolume,
  sfx: sfxVolume,
  musicAvailable,
});

const emitState = () => {
  syncRootState();
  window.dispatchEvent(
    new CustomEvent<SiteAudioState>(SITE_AUDIO_EVENT, {
      detail: currentState(),
    }),
  );
};

const markMusicAvailable = (available: boolean) => {
  if (musicAvailable === available) return;
  musicAvailable = available;
  emitState();
};

const peekMusicAudio = () => (window as AudioWindow).__hecateSiteMusic ?? null;

const getMusicAudio = () => {
  const audioWindow = window as AudioWindow;
  if (audioWindow.__hecateSiteMusic) return audioWindow.__hecateSiteMusic;

  const audio = new Audio(MUSIC_SOURCE);
  audio.preload = 'metadata';
  audio.loop = true;
  audio.volume = musicVolume / 100;
  audio.setAttribute('playsinline', '');
  audio.addEventListener('canplay', () => markMusicAvailable(true));
  audio.addEventListener('loadedmetadata', () => markMusicAvailable(true));
  audio.addEventListener('error', () => {
    musicPlaybackPending = false;
    markMusicAvailable(false);
  });

  audioWindow.__hecateSiteMusic = audio;
  return audio;
};

const attemptMusicPlayback = () => {
  if (musicVolume <= 0 || musicAvailable === false) {
    musicPlaybackPending = false;
    return;
  }

  const audio = getMusicAudio();
  audio.volume = musicVolume / 100;
  const playback = audio.play();
  if (!playback) {
    musicPlaybackPending = false;
    return;
  }

  void playback
    .then(() => {
      musicPlaybackPending = false;
      markMusicAvailable(true);
    })
    .catch(() => {
      // Browsers may block remembered music volume from autoplaying after a
      // reload. Keep the preference and resume on the next real user gesture.
      musicPlaybackPending = true;
    });
};

const installGestureResume = () => {
  const audioWindow = window as AudioWindow;
  if (audioWindow.__hecateAudioGestureInstalled) return;
  audioWindow.__hecateAudioGestureInstalled = true;

  const resume = () => {
    if (!musicPlaybackPending || musicVolume <= 0) return;
    attemptMusicPlayback();
  };

  document.addEventListener('pointerdown', resume, { capture: true, passive: true });
  document.addEventListener('keydown', resume, { capture: true });
};

export const initializeSiteAudio = () => {
  if (initialized) {
    // Astro swaps page content without requiring the audio element to restart.
    // Only mirror the persistent state back onto the current root element.
    syncRootState();
    installGestureResume();
    return;
  }

  musicVolume = readStoredPercent(MUSIC_VOLUME_STORAGE_KEY);
  sfxVolume = readStoredPercent(SFX_VOLUME_STORAGE_KEY);
  initialized = true;

  // The old on/off control is intentionally retired. New installs and users
  // without the two explicit volume preferences start at 0 / 0.
  try {
    localStorage.removeItem('site-sound');
  } catch {
    // Ignore storage restrictions.
  }

  syncRootState();
  installGestureResume();

  // Zero is the default music setting. Do not touch the 2.6 MB music asset
  // until the user has actually enabled music (or a saved non-zero preference
  // needs to resume it). This keeps the default page load network-silent.
  if (musicVolume > 0) {
    const audio = getMusicAudio();
    audio.volume = musicVolume / 100;
    audio.load();
    if (audio.paused) musicPlaybackPending = true;
  }
};

export const getSiteAudioState = () => {
  if (!initialized) initializeSiteAudio();
  return currentState();
};

export const getSfxGain = () => {
  if (!initialized) initializeSiteAudio();
  return sfxVolume / 100;
};

export const setSfxVolume = (value: number, persist = true) => {
  if (!initialized) initializeSiteAudio();
  sfxVolume = clampPercent(value);
  if (persist) writeStoredPercent(SFX_VOLUME_STORAGE_KEY, sfxVolume);
  emitState();
  return sfxVolume;
};

export const setMusicVolume = (value: number, persist = true) => {
  if (!initialized) initializeSiteAudio();
  musicVolume = clampPercent(value);
  if (persist) writeStoredPercent(MUSIC_VOLUME_STORAGE_KEY, musicVolume);

  if (musicVolume <= 0) {
    musicPlaybackPending = false;
    const audio = peekMusicAudio();
    if (audio) {
      audio.volume = 0;
      audio.pause();
    }
  } else {
    const audio = getMusicAudio();
    audio.volume = musicVolume / 100;
    if (audio.paused) {
      musicPlaybackPending = true;
      attemptMusicPlayback();
    }
  }

  emitState();
  return musicVolume;
};

export const subscribeSiteAudio = (listener: (state: SiteAudioState) => void) => {
  const handleState = (event: Event) => {
    const customEvent = event as CustomEvent<SiteAudioState>;
    listener(customEvent.detail ?? getSiteAudioState());
  };

  window.addEventListener(SITE_AUDIO_EVENT, handleState);
  listener(getSiteAudioState());

  return () => window.removeEventListener(SITE_AUDIO_EVENT, handleState);
};
