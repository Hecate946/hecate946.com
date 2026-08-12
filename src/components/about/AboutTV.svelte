<script lang="ts">
  import { onDestroy } from 'svelte';
  import { createAboutTVChannels } from './about-tv-content';
  import TVChannel from './TVChannel.svelte';

  export let portraitUrl: string;
  export let softwareResumeUrl: string;
  export let projectsUrl: string;
  export let musicResumeUrl: string;
  export let musicVideoUrl: string;
  export let pickleballArticleUrl: string;
  export let chessProfileUrl: string;

  type TVPhase = 'idle' | 'powering-down' | 'powering-up';

  let currentIndex = 0;
  let pendingIndex: number | null = null;
  let phase: TVPhase = 'idle';
  let offTimer: ReturnType<typeof setTimeout> | null = null;
  let onTimer: ReturnType<typeof setTimeout> | null = null;

  $: channels = createAboutTVChannels({
    portraitUrl,
    softwareResumeUrl,
    projectsUrl,
    musicResumeUrl,
    musicVideoUrl,
    pickleballArticleUrl,
    chessProfileUrl,
  });
  $: currentChannel = channels[currentIndex];
  $: isChanging = phase !== 'idle';

  const clampIndex = (index: number) => Math.min(channels.length - 1, Math.max(0, index));

  const clearTimers = () => {
    if (offTimer !== null) {
      clearTimeout(offTimer);
      offTimer = null;
    }
    if (onTimer !== null) {
      clearTimeout(onTimer);
      onTimer = null;
    }
  };

  const changeChannel = (nextIndex: number) => {
    const clamped = clampIndex(nextIndex);
    if (clamped === currentIndex || isChanging) return;

    clearTimers();
    pendingIndex = clamped;
    phase = 'powering-down';

    offTimer = setTimeout(() => {
      if (pendingIndex === null) return;
      currentIndex = pendingIndex;
      pendingIndex = null;
      phase = 'powering-up';

      onTimer = setTimeout(() => {
        phase = 'idle';
      }, 360);
    }, 210);
  };

  onDestroy(clearTimers);
</script>

<div
  class="about-tv-installation"
  class:is-powering-down={phase === 'powering-down'}
  class:is-powering-up={phase === 'powering-up'}
>
  <div class="about-tv" aria-label="About television">
    <div class="about-tv__cabinet">
      <div class="about-tv__rear-shell" aria-hidden="true"></div>
      <span class="about-tv__screw about-tv__screw--tl" aria-hidden="true"></span>
      <span class="about-tv__screw about-tv__screw--tr" aria-hidden="true"></span>
      <span class="about-tv__screw about-tv__screw--bl" aria-hidden="true"></span>
      <span class="about-tv__screw about-tv__screw--br" aria-hidden="true"></span>

      <div class="about-tv__screen-frame" aria-label="Television screen">
        <div class="about-tv__glass" aria-live="polite">
          <div class="about-tv__picture">
            <TVChannel channel={currentChannel} />
          </div>
          <div class="about-tv__scanlines" aria-hidden="true"></div>
          <div class="about-tv__vignette" aria-hidden="true"></div>
          <div class="about-tv__reflection" aria-hidden="true"></div>
          <div class="about-tv__noise" aria-hidden="true"></div>
        </div>
      </div>

      <div class="about-tv__control-panel" role="group" aria-label="About sections">
        <div class="about-tv__power-light" aria-hidden="true"></div>
        <div class="about-tv__buttons">
          {#each channels as channel, index}
            <button
              type="button"
              class="about-tv__button"
              class:is-active={index === currentIndex && pendingIndex === null}
              aria-label={`Show ${channel.label}`}
              aria-current={index === currentIndex ? 'true' : undefined}
              onclick={() => changeChannel(index)}
            >
              {channel.label}
            </button>
          {/each}
        </div>
      </div>

      <div class="about-tv__feet" aria-hidden="true">
        <span></span><span></span>
      </div>
    </div>
  </div>
</div>
