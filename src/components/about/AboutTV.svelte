<script lang="ts">
  import { onMount } from 'svelte';
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

  let screenElement: HTMLDivElement;
  let currentIndex = 0;
  let pendingIndex: number | null = null;
  let phase: TVPhase = 'idle';
  let offTimer = 0;
  let onTimer = 0;
  let activePointerId: number | null = null;
  let pointerStartX = 0;
  let pointerStartY = 0;
  let pointerMoved = false;
  let ignoreClickUntil = 0;

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
    window.clearTimeout(offTimer);
    window.clearTimeout(onTimer);
  };

  const changeChannel = (nextIndex: number) => {
    const clamped = clampIndex(nextIndex);
    if (clamped === currentIndex || isChanging) return;

    clearTimers();
    pendingIndex = clamped;
    phase = 'powering-down';

    offTimer = window.setTimeout(() => {
      if (pendingIndex === null) return;
      currentIndex = pendingIndex;
      pendingIndex = null;
      phase = 'powering-up';

      onTimer = window.setTimeout(() => {
        phase = 'idle';
      }, 360);
    }, 210);
  };

  const next = () => changeChannel(currentIndex + 1);
  const previous = () => changeChannel(currentIndex - 1);

  const handleClick = (event: MouseEvent) => {
    if (performance.now() < ignoreClickUntil || isChanging) return;
    if (event.target instanceof Element && event.target.closest('a, button')) return;
    const bounds = screenElement.getBoundingClientRect();
    const relativeX = event.clientX - bounds.left;
    if (relativeX < bounds.width * 0.42) previous();
    else next();
  };

  const handlePointerDown = (event: PointerEvent) => {
    if (isChanging || activePointerId !== null) return;
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    if (event.target instanceof Element && event.target.closest('a, button')) return;
    activePointerId = event.pointerId;
    pointerStartX = event.clientX;
    pointerStartY = event.clientY;
    pointerMoved = false;
  };

  const handlePointerMove = (event: PointerEvent) => {
    if (event.pointerId !== activePointerId) return;
    const dx = event.clientX - pointerStartX;
    const dy = event.clientY - pointerStartY;
    if (!pointerMoved && Math.hypot(dx, dy) < 8) return;
    if (Math.abs(dy) > Math.abs(dx) * 1.15) {
      activePointerId = null;
      pointerMoved = false;
      return;
    }
    pointerMoved = true;
    if (event.cancelable) event.preventDefault();
  };

  const finishPointer = (event: PointerEvent) => {
    if (event.pointerId !== activePointerId) return;
    const dx = event.clientX - pointerStartX;
    const dy = event.clientY - pointerStartY;
    const moved = pointerMoved;
    activePointerId = null;
    pointerMoved = false;

    if (!moved || Math.abs(dx) < 42 || Math.abs(dx) < Math.abs(dy)) return;
    ignoreClickUntil = performance.now() + 360;
    if (dx < 0) next();
    else previous();
  };

  const handleKeyDown = (event: KeyboardEvent) => {
    const target = event.target;
    if (target instanceof Element && target.closest('a, button, input, textarea, select')) return;
    if (event.key === 'ArrowRight' || event.key === 'PageDown') {
      event.preventDefault();
      next();
    } else if (event.key === 'ArrowLeft' || event.key === 'PageUp') {
      event.preventDefault();
      previous();
    }
  };

  onMount(() => {
    screenElement.addEventListener('pointerdown', handlePointerDown);
    screenElement.addEventListener('pointermove', handlePointerMove, { passive: false });
    screenElement.addEventListener('click', handleClick);
    window.addEventListener('pointerup', finishPointer);
    window.addEventListener('pointercancel', finishPointer);
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      clearTimers();
      screenElement.removeEventListener('pointerdown', handlePointerDown);
      screenElement.removeEventListener('pointermove', handlePointerMove);
      screenElement.removeEventListener('click', handleClick);
      window.removeEventListener('pointerup', finishPointer);
      window.removeEventListener('pointercancel', finishPointer);
      window.removeEventListener('keydown', handleKeyDown);
    };
  });
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

      <div class="about-tv__screen-frame" bind:this={screenElement}>
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
