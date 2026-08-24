<script lang="ts">
  import { withBase } from '@/lib/paths';

  const MUSIC_URL = withBase('/audio/brahms-violin-sonata-no-3-mvt-3.mp3');
  const MUSIC_VOLUME = 0.58;
  const PIECE_TITLE =
    'Johannes Brahms — Violin Sonata No. 3 in D minor, Op. 108 — III. Un poco presto e con sentimento';

  let audio: HTMLAudioElement;
  let playing = false;
  let unavailable = false;

  async function toggleAudio() {
    if (!audio.paused) {
      audio.pause();
      return;
    }

    audio.volume = MUSIC_VOLUME;

    try {
      await audio.play();
      unavailable = false;
    } catch (error) {
      playing = false;
      unavailable = true;
      console.warn(`Music could not be played from ${MUSIC_URL}.`, error);
    }
  }
</script>

<div class="audio-control">
  <audio
    bind:this={audio}
    src={MUSIC_URL}
    preload="metadata"
    loop
    hidden
    onplay={() => (playing = true)}
    onpause={() => (playing = false)}
    onerror={() => {
      playing = false;
      unavailable = true;
    }}
  ></audio>

  <button
    type="button"
    class="header-action audio-action"
    aria-label={playing ? 'Pause background music' : 'Play background music'}
    aria-pressed={playing}
    title={unavailable
      ? 'Audio file unavailable'
      : `${playing ? 'Pause' : 'Play'} ${PIECE_TITLE}`}
    onclick={toggleAudio}
  >
    <span class="header-action-icon audio-icon" aria-hidden="true">
      {#if playing}
        <svg viewBox="0 0 24 24" width="24" height="24" focusable="false">
          <path d="M5 9.5h3.4L13 5.8v12.4l-4.6-3.7H5z" fill="currentColor" />
          <path
            d="M16.2 9.1a4.1 4.1 0 0 1 0 5.8M18.5 6.8a7.3 7.3 0 0 1 0 10.4"
          />
        </svg>
      {:else}
        <svg viewBox="0 0 24 24" width="24" height="24" focusable="false">
          <path d="M5 9.5h3.4L13 5.8v12.4l-4.6-3.7H5z" fill="currentColor" />
          <path d="m16.2 9.2 4.3 5.6M20.5 9.2l-4.3 5.6" />
        </svg>
      {/if}
    </span>
  </button>
</div>
