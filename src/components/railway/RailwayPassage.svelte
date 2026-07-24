<script lang="ts">
  import { onDestroy, onMount, tick } from 'svelte';
  import type { RailwayStop } from '@/config/railway';
  import RailwayStation from './RailwayStation.svelte';
  import RailwayTrack from './RailwayTrack.svelte';
  import RailwayTrain from './RailwayTrain.svelte';

  export let lineName = 'Line 946';
  export let serviceLabel = 'Steam service';
  export let stops: readonly RailwayStop[] = [];
  export let navigationEnabled = false;
  export let autoPlay = true;
  export let durationSeconds = 17;
  export let currentStopLabel = 'Home';

  type JourneyState =
    | 'waiting'
    | 'approaching'
    | 'dwelling'
    | 'departing'
    | 'complete'
    | 'static';

  let sectionElement!: HTMLElement;
  let runnerElement!: HTMLDivElement;
  let observer: IntersectionObserver | null = null;
  let reducedMotionQuery: MediaQueryList | null = null;
  let animationHandle: Animation | null = null;
  let journeyState: JourneyState = 'waiting';
  let hasPlayed = false;
  let motionActive = false;
  let steamActive = false;
  let runNonce = 0;
  let frameOne = 0;
  let frameTwo = 0;
  let phaseTimerOne = 0;
  let phaseTimerTwo = 0;
  let completionTimer = 0;
  let clockTimer = 0;
  let phaseEndsAt = 0;
  let timeRemaining = 0;
  let approachDuration = 5.5;
  let departDuration = 7.5;

  const dwellDuration = 4;

  $: totalDuration = Math.max(14, durationSeconds);
  $: movingDuration = Math.max(8, totalDuration - dwellDuration);
  $: stationTitle = `${currentStopLabel} Station`;

  $: boardLabel =
    journeyState === 'dwelling'
      ? 'Departing in'
      : journeyState === 'departing'
        ? 'Clearing in'
        : 'Next train';

  $: boardPrimary =
    journeyState === 'static'
      ? 'DISPLAY ONLY'
      : journeyState === 'dwelling' || journeyState === 'departing'
        ? formatClock(timeRemaining)
        : journeyState === 'approaching'
          ? timeRemaining <= 1
            ? 'NOW ARRIVING'
            : formatClock(timeRemaining)
          : journeyState === 'complete'
            ? 'CLEARED'
            : formatClock(Math.ceil(approachDuration));

  $: boardSecondary =
    journeyState === 'static'
      ? 'REDUCED MOTION'
      : journeyState === 'dwelling'
        ? 'BOARDING AT PLATFORM 946'
        : journeyState === 'departing'
          ? 'NOW DEPARTING FROM PLATFORM 946'
          : journeyState === 'approaching'
            ? timeRemaining <= 1
              ? stationTitle.toUpperCase()
              : `TO ${stationTitle.toUpperCase()}`
            : journeyState === 'complete'
              ? 'PRESS REPLAY FOR NEXT PASS'
              : `TO ${stationTitle.toUpperCase()}`;

  function formatClock(value: number) {
    const safe = Math.max(0, Math.ceil(value));
    const minutes = Math.floor(safe / 60)
      .toString()
      .padStart(2, '0');
    const seconds = Math.floor(safe % 60)
      .toString()
      .padStart(2, '0');
    return `${minutes}:${seconds}`;
  }

  function updateClock() {
    if (!phaseEndsAt) {
      timeRemaining = 0;
      return;
    }

    timeRemaining = Math.max(0, Math.ceil((phaseEndsAt - Date.now()) / 1000));
  }

  function stopClock() {
    if (typeof window === 'undefined') return;
    window.clearInterval(clockTimer);
    clockTimer = 0;
    phaseEndsAt = 0;
  }

  function beginCountdown(seconds: number) {
    if (typeof window === 'undefined') return;
    stopClock();
    phaseEndsAt = Date.now() + seconds * 1000;
    updateClock();
    clockTimer = window.setInterval(updateClock, 250);
  }

  function clearFrames() {
    if (typeof window === 'undefined') return;
    window.cancelAnimationFrame(frameOne);
    window.cancelAnimationFrame(frameTwo);
    frameOne = 0;
    frameTwo = 0;
  }

  function clearTimers() {
    if (typeof window === 'undefined') return;

    clearFrames();
    stopClock();
    window.clearTimeout(phaseTimerOne);
    window.clearTimeout(phaseTimerTwo);
    window.clearTimeout(completionTimer);
    phaseTimerOne = 0;
    phaseTimerTwo = 0;
    completionTimer = 0;
    animationHandle?.cancel();
    animationHandle = null;
    motionActive = false;
    steamActive = false;
  }

  function getJourneyGeometry() {
    const trainWidth = runnerElement.getBoundingClientRect().width;
    const viewportWidth = window.innerWidth;
    const stationAnchor = viewportWidth < 720 ? 0.94 : 0.88;
    const startX = -trainWidth - Math.min(240, viewportWidth * 0.16);
    const stopX = viewportWidth * stationAnchor - trainWidth;
    const endX = viewportWidth + Math.min(260, viewportWidth * 0.18);
    const approachDistance = Math.max(1, stopX - startX);
    const departDistance = Math.max(1, endX - stopX);
    const totalDistance = approachDistance + departDistance;

    approachDuration = movingDuration * (approachDistance / totalDistance);
    departDuration = movingDuration - approachDuration;

    return { startX, stopX, endX };
  }

  function runAnimation() {
    if (typeof window === 'undefined' || !runnerElement) return;

    const { startX, stopX, endX } = getJourneyGeometry();
    const approachOffset = approachDuration / totalDuration;
    const dwellEndOffset = (approachDuration + dwellDuration) / totalDuration;

    animationHandle?.cancel();
    animationHandle = runnerElement.animate(
      [
        { transform: `translateX(${startX}px)`, offset: 0 },
        { transform: `translateX(${stopX}px)`, offset: approachOffset },
        { transform: `translateX(${stopX}px)`, offset: dwellEndOffset },
        { transform: `translateX(${endX}px)`, offset: 1 },
      ],
      {
        duration: totalDuration * 1000,
        easing: 'linear',
        fill: 'both',
      },
    );
  }

  async function startJourney(force = false) {
    if (typeof window === 'undefined') return;

    if (reducedMotionQuery?.matches) {
      clearTimers();
      journeyState = 'static';
      return;
    }

    if (!force && hasPlayed) return;

    clearTimers();
    journeyState = 'waiting';
    runNonce += 1;
    await tick();

    frameOne = window.requestAnimationFrame(() => {
      frameTwo = window.requestAnimationFrame(() => {
        void runnerElement?.offsetWidth;
        runAnimation();
        hasPlayed = true;
        journeyState = 'approaching';
        motionActive = true;
        steamActive = true;
        beginCountdown(approachDuration);

        phaseTimerOne = window.setTimeout(() => {
          journeyState = 'dwelling';
          motionActive = false;
          steamActive = true;
          beginCountdown(dwellDuration);
        }, approachDuration * 1000);

        phaseTimerTwo = window.setTimeout(() => {
          journeyState = 'departing';
          motionActive = true;
          steamActive = true;
          beginCountdown(departDuration);
        }, (approachDuration + dwellDuration) * 1000);

        completionTimer = window.setTimeout(() => {
          motionActive = false;
          steamActive = false;
          stopClock();
          journeyState = 'complete';
        }, totalDuration * 1000);
      });
    });
  }

  function replayJourney() {
    hasPlayed = false;
    void startJourney(true);
  }

  function handleMotionPreference(event: MediaQueryListEvent) {
    if (event.matches) {
      clearTimers();
      journeyState = 'static';
    } else {
      hasPlayed = false;
      journeyState = autoPlay ? 'waiting' : 'complete';
    }
  }

  onMount(() => {
    reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    reducedMotionQuery.addEventListener('change', handleMotionPreference);

    if (reducedMotionQuery.matches) {
      journeyState = 'static';
      return;
    }

    if (!autoPlay) {
      journeyState = 'complete';
      return;
    }

    observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          void startJourney();
          observer?.disconnect();
          observer = null;
        }
      },
      {
        rootMargin: '0px 0px -10% 0px',
        threshold: 0.18,
      },
    );

    observer.observe(sectionElement);
  });

  onDestroy(() => {
    if (typeof window === 'undefined') return;

    clearTimers();
    observer?.disconnect();
    reducedMotionQuery?.removeEventListener('change', handleMotionPreference);
  });
</script>

<section
  class:railway-is-static={journeyState === 'static'}
  class="railway-passage"
  aria-labelledby="railway-passage-title"
  bind:this={sectionElement}
>
  <div class="railway-boundary">
    <header class="railway-toolbar">
      <div class="railway-line-lockup">
        <span class="railway-roundel" aria-hidden="true"><span></span></span>
        <div>
          <h2 id="railway-passage-title">{lineName}</h2>
          <p>{serviceLabel}</p>
        </div>
      </div>

      <button
        class="railway-replay"
        type="button"
        aria-label="Replay the train passage"
        onclick={replayJourney}
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M20 11a8 8 0 1 0-2.34 5.66M20 4v7h-7"></path>
        </svg>
        <span>Replay</span>
      </button>
    </header>

    <div class="railway-scene" aria-hidden={!navigationEnabled}>
      <div class="railway-station-position">
        <RailwayStation
          {stationTitle}
          {boardLabel}
          {boardPrimary}
          {boardSecondary}
        />
      </div>

      {#key runNonce}
        <div class="railway-train-runner" bind:this={runnerElement}>
          <RailwayTrain
            {lineName}
            {stops}
            {navigationEnabled}
            {motionActive}
            {steamActive}
          />
        </div>
      {/key}

      <RailwayTrack />
    </div>
  </div>

  <p class="railway-status" aria-live="polite">
    {journeyState === 'approaching'
      ? 'The Line 946 train is approaching the station.'
      : journeyState === 'dwelling'
        ? 'The Line 946 train is boarding at the platform.'
        : journeyState === 'departing'
          ? 'The Line 946 train is departing the station.'
          : journeyState === 'static'
            ? 'The train is displayed without motion.'
            : journeyState === 'complete'
              ? 'The train has departed. Replay is available.'
              : 'The next train is approaching.'}
  </p>
</section>

<style>
  .railway-passage {
    --railway-muted: color-mix(in srgb, var(--muted) 82%, var(--text));
    position: relative;
    isolation: isolate;
    width: 100%;
    overflow: hidden;
    padding-block: clamp(1.75rem, 3.2vw, 3rem);
    background: transparent;
    color: var(--text);
  }

  .railway-boundary {
    position: relative;
    border-block: 1px solid color-mix(in srgb, var(--text) 18%, transparent);
  }

  .railway-toolbar {
    position: absolute;
    z-index: 26;
    top: clamp(1rem, 2.4vw, 1.6rem);
    right: var(--site-edge, clamp(1rem, 3.5vw, 4rem));
    left: var(--site-edge, clamp(1rem, 3.5vw, 4rem));
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    pointer-events: none;
  }

  .railway-line-lockup {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .railway-line-lockup h2,
  .railway-line-lockup p {
    margin: 0;
  }

  .railway-line-lockup h2 {
    font-family: var(--font-display);
    font-size: clamp(1rem, 1.8vw, 1.25rem);
    font-weight: 500;
    letter-spacing: -0.015em;
    line-height: 1;
  }

  .railway-line-lockup p {
    margin-top: 0.25rem;
    color: var(--railway-muted);
    font-family: var(--font-mono);
    font-size: 0.63rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .railway-roundel {
    display: grid;
    width: 2.4rem;
    height: 2.4rem;
    flex: 0 0 auto;
    place-items: center;
    border: 0.22rem solid var(--accent-strong);
    border-radius: 50%;
    background: transparent;
  }

  .railway-roundel span {
    width: 2.7rem;
    height: 0.56rem;
    border: 0.12rem solid color-mix(in srgb, var(--accent-strong) 75%, var(--text));
    background: var(--accent-strong);
    box-shadow: inset 0 0 0 0.08rem color-mix(in srgb, white 26%, transparent);
  }

  .railway-replay {
    display: inline-flex;
    min-height: 2.3rem;
    align-items: center;
    justify-content: center;
    gap: 0.45rem;
    padding: 0.45rem 0.8rem;
    border: 1px solid color-mix(in srgb, var(--text) 22%, transparent);
    border-radius: var(--radius-pill);
    background: rgb(0 0 0 / 0.08);
    color: var(--text);
    cursor: pointer;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    letter-spacing: 0.08em;
    pointer-events: auto;
    text-transform: uppercase;
    backdrop-filter: blur(4px);
  }

  .railway-replay:hover,
  .railway-replay:focus-visible {
    border-color: var(--accent);
    color: var(--accent-strong);
    transform: translateY(-1px);
  }

  .railway-replay svg {
    width: 1rem;
    height: 1rem;
    fill: none;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.8;
  }

  .railway-scene {
    position: relative;
    min-height: clamp(27rem, 37vw, 32rem);
    overflow: hidden;
    background: transparent;
  }

  .railway-station-position {
    position: absolute;
    right: clamp(-2.5rem, -1vw, -0.5rem);
    bottom: 4.3rem;
    width: clamp(31rem, 49vw, 48rem);
  }

  .railway-train-runner {
    position: absolute;
    z-index: 14;
    bottom: 2.95rem;
    left: 0;
    width: max-content;
    transform: translateX(calc(-100% - 18rem));
    will-change: transform;
  }

  .railway-is-static .railway-train-runner {
    transform: translateX(calc(88vw - 138rem));
  }

  .railway-status {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  @media (max-width: 72rem) {
    .railway-scene {
      min-height: 25rem;
    }

    .railway-station-position {
      right: -2rem;
      bottom: 4.1rem;
      width: clamp(27rem, 58vw, 39rem);
    }

    .railway-is-static .railway-train-runner {
      transform: translateX(calc(90vw - 121rem));
    }
  }

  @media (max-width: 48rem) {
    .railway-passage {
      padding-block: clamp(1.35rem, 6vw, 2rem);
    }

    .railway-scene {
      min-height: 21.5rem;
    }

    .railway-line-lockup p,
    .railway-replay span {
      display: none;
    }

    .railway-replay {
      width: 2.35rem;
      padding: 0;
    }

    .railway-roundel {
      width: 2rem;
      height: 2rem;
    }

    .railway-roundel span {
      width: 2.25rem;
      height: 0.46rem;
    }

    .railway-station-position {
      right: -4.5rem;
      bottom: 3.65rem;
      width: clamp(24rem, 104vw, 31rem);
    }

    .railway-train-runner {
      bottom: 2.7rem;
    }

    .railway-is-static .railway-train-runner {
      transform: translateX(calc(94vw - 102rem));
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .railway-train-runner {
      transition: none !important;
    }
  }
</style>
