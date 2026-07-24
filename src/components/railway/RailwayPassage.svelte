<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import type { RailwayStop } from '@/config/railway';

  export let lineName = 'Cyrus Line';
  export let serviceLabel = 'Through service';
  export let stops: readonly RailwayStop[] = [];
  export let navigationEnabled = false;
  export let autoPlay = true;
  export let durationSeconds = 17;

  type JourneyState = 'waiting' | 'running' | 'complete' | 'static';

  let sectionElement!: HTMLElement;
  let runnerElement!: HTMLDivElement;
  let journeyState: JourneyState = 'waiting';
  let observer: IntersectionObserver | null = null;
  let reducedMotionQuery: MediaQueryList | null = null;
  let hasPlayed = false;
  let frameOne = 0;
  let frameTwo = 0;

  const visibleStops = () => stops.slice(0, 3);

  function clearFrames() {
    window.cancelAnimationFrame(frameOne);
    window.cancelAnimationFrame(frameTwo);
    frameOne = 0;
    frameTwo = 0;
  }

  function startJourney(force = false) {
    if (reducedMotionQuery?.matches) {
      journeyState = 'static';
      return;
    }

    if (!force && hasPlayed) return;

    clearFrames();
    journeyState = 'waiting';

    frameOne = window.requestAnimationFrame(() => {
      // Reading layout forces the previous animation instance to be discarded,
      // which makes the replay control reliable across browsers.
      void runnerElement?.offsetWidth;
      frameTwo = window.requestAnimationFrame(() => {
        journeyState = 'running';
        hasPlayed = true;
      });
    });
  }

  function replayJourney() {
    startJourney(true);
  }

  function handleAnimationEnd(event: AnimationEvent) {
    if (event.animationName.includes('railway-crossing')) {
      journeyState = 'complete';
    }
  }

  function handleMotionPreference(event: MediaQueryListEvent) {
    if (event.matches) {
      clearFrames();
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
          startJourney();
          observer?.disconnect();
          observer = null;
        }
      },
      {
        rootMargin: '0px 0px -12% 0px',
        threshold: 0.22,
      },
    );

    observer.observe(sectionElement);
  });

  onDestroy(() => {
    clearFrames();
    observer?.disconnect();
    reducedMotionQuery?.removeEventListener('change', handleMotionPreference);
  });
</script>

<section
  class:railway-is-running={journeyState === 'running'}
  class:railway-is-complete={journeyState === 'complete'}
  class:railway-is-static={journeyState === 'static'}
  class="railway-passage"
  aria-labelledby="railway-passage-title"
  bind:this={sectionElement}
  style={`--railway-duration: ${Math.max(8, durationSeconds)}s`}
>
  <header class="railway-toolbar">
    <div class="railway-line-lockup">
      <span class="railway-roundel" aria-hidden="true">
        <span></span>
      </span>
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
    <div class="railway-sun" aria-hidden="true"></div>
    <div class="railway-haze railway-haze--one" aria-hidden="true"></div>
    <div class="railway-haze railway-haze--two" aria-hidden="true"></div>

    <svg
      class="railway-landscape"
      viewBox="0 0 1600 420"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path
        class="railway-landscape-far"
        d="M0 272C96 225 167 249 254 215c99-39 153-101 257-71 99 28 126 101 231 83 99-17 133-94 242-78 96 14 151 84 246 72 107-13 183-103 280-83 36 7 66 22 90 39v243H0Z"
      ></path>
      <path
        class="railway-landscape-near"
        d="M0 304c91-48 179-26 264-55 95-32 146-79 248-52 87 23 124 81 220 71 117-12 151-84 264-63 91 17 138 76 230 67 114-11 189-89 287-57 32 10 61 28 87 49v156H0Z"
      ></path>
      <g class="railway-tree-line">
        <path d="M74 289v91M44 333l30-73 30 73M51 310h47"></path>
        <path d="M271 273v107M237 322l34-82 34 82M246 296h51"></path>
        <path d="M505 298v82M477 337l28-66 28 66M484 315h42"></path>
        <path d="M822 278v102M790 326l32-76 32 76M798 302h48"></path>
        <path d="M1111 292v88M1081 333l30-70 30 70M1089 311h44"></path>
        <path d="M1438 276v104M1405 326l33-78 33 78M1414 302h48"></path>
      </g>
    </svg>

    <div class="railway-signal railway-signal--left" aria-hidden="true">
      <span class="railway-signal-light"></span>
      <span class="railway-signal-arm"></span>
    </div>

    <div class="railway-water-tower" aria-hidden="true">
      <span class="railway-water-tank"></span>
      <span class="railway-water-legs"></span>
    </div>

    <div
      class="railway-train-runner"
      bind:this={runnerElement}
      onanimationend={handleAnimationEnd}
    >
      <div class="railway-smoke" aria-hidden="true">
        <span></span><span></span><span></span><span></span><span></span>
      </div>

      <svg
        class="railway-train"
        viewBox="0 0 1600 292"
        role={navigationEnabled ? 'group' : undefined}
        aria-label={navigationEnabled ? `${lineName} navigation train` : undefined}
      >
        <defs>
          <linearGradient id="railway-boiler" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#263b3d"></stop>
            <stop offset="0.38" stop-color="#10282b"></stop>
            <stop offset="0.72" stop-color="#071719"></stop>
            <stop offset="1" stop-color="#020708"></stop>
          </linearGradient>
          <linearGradient id="railway-cab" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#8d392d"></stop>
            <stop offset="0.48" stop-color="#5f211c"></stop>
            <stop offset="1" stop-color="#2d0d0b"></stop>
          </linearGradient>
          <linearGradient id="railway-car" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#24474a"></stop>
            <stop offset="0.48" stop-color="#153437"></stop>
            <stop offset="1" stop-color="#0a1e20"></stop>
          </linearGradient>
          <linearGradient id="railway-brass" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#fff0a6"></stop>
            <stop offset="0.25" stop-color="#d9a93e"></stop>
            <stop offset="0.55" stop-color="#88571c"></stop>
            <stop offset="0.78" stop-color="#efc85d"></stop>
            <stop offset="1" stop-color="#6b4215"></stop>
          </linearGradient>
          <linearGradient id="railway-steel" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#dbe3df"></stop>
            <stop offset="0.28" stop-color="#87928f"></stop>
            <stop offset="0.64" stop-color="#313a39"></stop>
            <stop offset="1" stop-color="#0c1212"></stop>
          </linearGradient>
          <radialGradient id="railway-window" cx="38%" cy="30%" r="80%">
            <stop offset="0" stop-color="#fff6bc"></stop>
            <stop offset="0.55" stop-color="#e5b34e"></stop>
            <stop offset="1" stop-color="#6a3c18"></stop>
          </radialGradient>
          <filter id="railway-shadow" x="-20%" y="-40%" width="150%" height="190%">
            <feDropShadow dx="0" dy="12" stdDeviation="8" flood-color="#000" flood-opacity=".42"></feDropShadow>
          </filter>
          <filter id="railway-glow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="5" result="blur"></feGaussianBlur>
            <feMerge><feMergeNode in="blur"></feMergeNode><feMergeNode in="SourceGraphic"></feMergeNode></feMerge>
          </filter>
        </defs>

        <ellipse class="railway-ground-shadow" cx="782" cy="262" rx="738" ry="22"></ellipse>

        <g class="railway-locomotive" filter="url(#railway-shadow)">
          <path class="railway-cowcatcher" d="M28 229h95l-24 34H9Z"></path>
          <path class="railway-cowcatcher-line" d="m24 233 71 27M48 231l55 25M72 231l39 22"></path>
          <rect class="railway-frame" x="92" y="211" width="393" height="29" rx="8"></rect>
          <rect class="railway-front-step" x="55" y="205" width="94" height="15" rx="5"></rect>

          <path class="railway-boiler" d="M112 115h268c36 0 66 28 66 63v34H112Z"></path>
          <ellipse class="railway-smokebox" cx="119" cy="164" rx="34" ry="49"></ellipse>
          <ellipse class="railway-smokebox-ring" cx="119" cy="164" rx="25" ry="39"></ellipse>
          <circle class="railway-headlamp-shell" cx="103" cy="137" r="15"></circle>
          <circle class="railway-headlamp" cx="98" cy="134" r="8" filter="url(#railway-glow)"></circle>
          <path class="railway-headlamp-beam" d="M89 128-3 100v68l92-26Z"></path>

          <rect class="railway-boiler-band" x="174" y="115" width="12" height="97" rx="5"></rect>
          <rect class="railway-boiler-band" x="250" y="115" width="12" height="97" rx="5"></rect>
          <rect class="railway-boiler-band" x="326" y="115" width="12" height="97" rx="5"></rect>
          <path class="railway-boiler-highlight" d="M139 128h214c34 0 55 15 69 36"></path>

          <g class="railway-chimney">
            <path d="M142 113h50l-9-16v-43h-31v43Z"></path>
            <path d="M142 56h50l13-20h-77Z"></path>
            <rect x="126" y="31" width="82" height="13" rx="6"></rect>
          </g>

          <g class="railway-dome">
            <path d="M252 115V89c0-15 12-28 28-28s28 13 28 28v26Z"></path>
            <rect x="246" y="103" width="68" height="13" rx="6"></rect>
            <ellipse cx="280" cy="67" rx="21" ry="8"></ellipse>
          </g>

          <path class="railway-cab" d="M366 71h107l31 48v104H354V117Z"></path>
          <path class="railway-cab-roof" d="M347 71c11-17 25-25 43-25h80c20 0 35 8 46 25Z"></path>
          <rect class="railway-cab-window-frame" x="385" y="91" width="49" height="62" rx="5"></rect>
          <rect class="railway-cab-window" x="393" y="99" width="33" height="46" rx="3"></rect>
          <path class="railway-window-reflection" d="m398 104 23 24M396 119l18 19"></path>
          <rect class="railway-cab-panel" x="374" y="165" width="80" height="39" rx="3"></rect>
          <text class="railway-engine-number" x="414" y="191" text-anchor="middle">946</text>
          <path class="railway-brass-line" d="M368 160h102M368 209h102"></path>
          <rect class="railway-step" x="444" y="216" width="51" height="12" rx="4"></rect>

          <g class="railway-wheel railway-wheel--small" transform="translate(137 223)">
            <circle class="railway-wheel-tire" r="34"></circle>
            <circle class="railway-wheel-rim" r="26"></circle>
            <path class="railway-wheel-spokes" d="M0-24V24M-24 0h48M-17-17l34 34M17-17l-34 34"></path>
            <circle class="railway-wheel-hub" r="8"></circle>
          </g>
          <g class="railway-wheel railway-wheel--drive" transform="translate(242 218)">
            <circle class="railway-wheel-tire" r="51"></circle>
            <circle class="railway-wheel-rim" r="42"></circle>
            <path class="railway-wheel-spokes" d="M0-39V39M-39 0h78M-28-28l56 56M28-28l-56 56M-36-15l72 30M-15-36l30 72"></path>
            <circle class="railway-wheel-hub" r="11"></circle>
          </g>
          <g class="railway-wheel railway-wheel--drive" transform="translate(361 218)">
            <circle class="railway-wheel-tire" r="51"></circle>
            <circle class="railway-wheel-rim" r="42"></circle>
            <path class="railway-wheel-spokes" d="M0-39V39M-39 0h78M-28-28l56 56M28-28l-56 56M-36-15l72 30M-15-36l30 72"></path>
            <circle class="railway-wheel-hub" r="11"></circle>
          </g>
          <g class="railway-wheel railway-wheel--small" transform="translate(456 224)">
            <circle class="railway-wheel-tire" r="31"></circle>
            <circle class="railway-wheel-rim" r="23"></circle>
            <path class="railway-wheel-spokes" d="M0-21V21M-21 0h42M-15-15l30 30M15-15l-30 30"></path>
            <circle class="railway-wheel-hub" r="7"></circle>
          </g>

          <g class="railway-running-gear">
            <path class="railway-main-rod" d="M238 219 361 219 456 224"></path>
            <path class="railway-link-rod" d="M242 218 316 177 361 218"></path>
            <circle cx="242" cy="218" r="7"></circle>
            <circle cx="361" cy="218" r="7"></circle>
            <circle cx="456" cy="224" r="6"></circle>
          </g>
        </g>

        <g class="railway-coupler" transform="translate(494 218)">
          <rect x="0" y="-5" width="32" height="10" rx="4"></rect>
          <circle cx="35" cy="0" r="7"></circle>
        </g>

        <g class="railway-tender" filter="url(#railway-shadow)">
          <path class="railway-tender-body" d="M531 113h214l-18 113H545Z"></path>
          <path class="railway-coal" d="M544 112c26-18 52-16 73-5 25-18 51-16 72-3 20-9 39-6 48 8Z"></path>
          <rect class="railway-tender-rail" x="532" y="105" width="214" height="13" rx="5"></rect>
          <path class="railway-brass-line" d="M548 139h179M543 203h186"></path>
          <text class="railway-tender-mark" x="638" y="181" text-anchor="middle">C · A</text>
          <rect class="railway-frame" x="535" y="216" width="197" height="20" rx="6"></rect>
          <g class="railway-wheel railway-wheel--tender" transform="translate(582 228)">
            <circle class="railway-wheel-tire" r="33"></circle>
            <circle class="railway-wheel-rim" r="25"></circle>
            <path class="railway-wheel-spokes" d="M0-23V23M-23 0h46M-16-16l32 32M16-16l-32 32"></path>
            <circle class="railway-wheel-hub" r="7"></circle>
          </g>
          <g class="railway-wheel railway-wheel--tender" transform="translate(687 228)">
            <circle class="railway-wheel-tire" r="33"></circle>
            <circle class="railway-wheel-rim" r="25"></circle>
            <path class="railway-wheel-spokes" d="M0-23V23M-23 0h46M-16-16l32 32M16-16l-32 32"></path>
            <circle class="railway-wheel-hub" r="7"></circle>
          </g>
        </g>

        {#each visibleStops() as stop, index (stop.id)}
          <a
            class:railway-car-link--enabled={navigationEnabled}
            class="railway-car-link"
            href={navigationEnabled ? stop.href : undefined}
            aria-label={navigationEnabled ? `Travel to ${stop.label}` : undefined}
            tabindex={navigationEnabled ? 0 : -1}
          >
            <g
              class="railway-passenger-car"
              transform={`translate(${755 + index * 270} 0)`}
              filter="url(#railway-shadow)"
            >
              <path class="railway-car-roof" d="M0 91c14-19 31-27 53-27h166c22 0 40 8 54 27Z"></path>
              <rect class="railway-car-body" x="4" y="88" width="266" height="137" rx="12"></rect>
              <path class="railway-car-highlight" d="M20 102h229"></path>
              <path class="railway-brass-line" d="M14 126h247M14 204h247"></path>
              <rect class="railway-car-door" x="204" y="132" width="42" height="67" rx="4"></rect>
              <circle class="railway-door-handle" cx="214" cy="167" r="3"></circle>

              {#each Array(4) as _, windowIndex}
                <g transform={`translate(${23 + windowIndex * 45} 137)`}>
                  <rect class="railway-car-window-frame" width="34" height="42" rx="4"></rect>
                  <rect class="railway-car-window" x="5" y="5" width="24" height="32" rx="2"></rect>
                  <path class="railway-window-reflection" d="m9 8 15 18M8 18l11 13"></path>
                </g>
              {/each}

              <rect class="railway-destination-board" x="76" y="101" width="120" height="27" rx="5"></rect>
              <text class="railway-destination-text" x="136" y="120" text-anchor="middle">
                {stop.shortLabel}
              </text>

              <rect class="railway-frame" x="10" y="214" width="254" height="21" rx="6"></rect>
              <g class="railway-wheel railway-wheel--car" transform="translate(63 230)">
                <circle class="railway-wheel-tire" r="31"></circle>
                <circle class="railway-wheel-rim" r="23"></circle>
                <path class="railway-wheel-spokes" d="M0-21V21M-21 0h42M-15-15l30 30M15-15l-30 30"></path>
                <circle class="railway-wheel-hub" r="7"></circle>
              </g>
              <g class="railway-wheel railway-wheel--car" transform="translate(211 230)">
                <circle class="railway-wheel-tire" r="31"></circle>
                <circle class="railway-wheel-rim" r="23"></circle>
                <path class="railway-wheel-spokes" d="M0-21V21M-21 0h42M-15-15l30 30M15-15l-30 30"></path>
                <circle class="railway-wheel-hub" r="7"></circle>
              </g>
              <g class="railway-coupler" transform="translate(268 219)">
                <rect x="0" y="-5" width="19" height="10" rx="4"></rect>
                <circle cx="22" cy="0" r="6"></circle>
              </g>
            </g>
          </a>
        {/each}
      </svg>
    </div>

    <div class="railway-platform" aria-hidden="true">
      <div class="railway-platform-edge"></div>
      <div class="railway-platform-face"></div>
    </div>

    <div class="railway-track" aria-hidden="true">
      <div class="railway-ballast"></div>
      <div class="railway-sleepers"></div>
      <div class="railway-rail railway-rail--far"></div>
      <div class="railway-rail railway-rail--near"></div>
      <div class="railway-fasteners railway-fasteners--far"></div>
      <div class="railway-fasteners railway-fasteners--near"></div>
    </div>

    <div class="railway-station-sign" aria-hidden="true">
      <span>{lineName}</span>
      <small>946</small>
    </div>

    <div class="railway-foreground" aria-hidden="true"></div>
  </div>

  <p class="railway-status" aria-live="polite">
    {journeyState === 'running'
      ? 'The train is passing through.'
      : journeyState === 'static'
        ? 'The train is displayed without motion.'
        : journeyState === 'complete'
          ? 'The train has passed. Replay is available.'
          : 'The train is approaching.'}
  </p>
</section>

<style>
  .railway-passage {
    --railway-sky-top: color-mix(in srgb, var(--accent-soft) 52%, var(--bg));
    --railway-sky-bottom: color-mix(in srgb, var(--season-2) 14%, var(--bg));
    --railway-hill-far: color-mix(in srgb, var(--season-1) 16%, var(--bg));
    --railway-hill-near: color-mix(in srgb, var(--season-1) 28%, var(--bg));
    --railway-ink: color-mix(in srgb, var(--text) 84%, #111);
    --railway-muted: color-mix(in srgb, var(--muted) 80%, var(--text));
    position: relative;
    isolation: isolate;
    width: 100%;
    overflow: hidden;
    border-top: 1px solid var(--line);
    background: var(--bg);
    color: var(--text);
  }

  .railway-toolbar {
    position: absolute;
    z-index: 20;
    top: clamp(1rem, 2.5vw, 1.7rem);
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
    background: color-mix(in srgb, var(--bg) 84%, transparent);
    box-shadow: 0 0.35rem 1rem color-mix(in srgb, var(--text) 12%, transparent);
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
    background: color-mix(in srgb, var(--bg) 83%, transparent);
    box-shadow: 0 0.55rem 1.3rem color-mix(in srgb, var(--text) 10%, transparent);
    color: var(--text);
    cursor: pointer;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    letter-spacing: 0.08em;
    pointer-events: auto;
    text-transform: uppercase;
    backdrop-filter: blur(8px);
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
    min-height: clamp(23rem, 34vw, 31rem);
    overflow: hidden;
    background:
      linear-gradient(180deg, transparent 60%, color-mix(in srgb, var(--bg) 15%, transparent) 100%),
      linear-gradient(180deg, var(--railway-sky-top), var(--railway-sky-bottom));
  }

  .railway-scene::before {
    position: absolute;
    z-index: 1;
    inset: 0;
    background:
      linear-gradient(90deg, color-mix(in srgb, var(--bg) 34%, transparent), transparent 18% 82%, color-mix(in srgb, var(--bg) 34%, transparent)),
      repeating-linear-gradient(105deg, transparent 0 8rem, color-mix(in srgb, white 4%, transparent) 8.1rem 8.15rem);
    content: '';
    pointer-events: none;
  }

  .railway-sun {
    position: absolute;
    z-index: 0;
    top: 18%;
    right: 13%;
    width: clamp(4.5rem, 8vw, 7rem);
    aspect-ratio: 1;
    border-radius: 50%;
    background: color-mix(in srgb, var(--season-2) 46%, var(--bg));
    box-shadow: 0 0 4rem color-mix(in srgb, var(--season-2) 34%, transparent);
    opacity: 0.65;
  }

  .railway-haze {
    position: absolute;
    z-index: 0;
    height: 0.18rem;
    border-radius: 999px;
    background: color-mix(in srgb, white 44%, transparent);
    filter: blur(0.08rem);
    opacity: 0.54;
  }

  .railway-haze--one {
    top: 29%;
    left: 8%;
    width: 29%;
  }

  .railway-haze--two {
    top: 38%;
    right: 25%;
    width: 19%;
  }

  .railway-landscape {
    position: absolute;
    z-index: 2;
    right: 0;
    bottom: 5.9rem;
    left: 0;
    width: 100%;
    height: 73%;
  }

  .railway-landscape-far {
    fill: var(--railway-hill-far);
  }

  .railway-landscape-near {
    fill: var(--railway-hill-near);
  }

  .railway-tree-line {
    fill: none;
    stroke: color-mix(in srgb, var(--season-1) 39%, var(--text));
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 5;
    opacity: 0.28;
  }

  .railway-signal {
    position: absolute;
    z-index: 4;
    bottom: 6.85rem;
    left: 8%;
    width: 0.55rem;
    height: 8.5rem;
    border-radius: 0.2rem;
    background: linear-gradient(90deg, #3a3027, #8c7a64 45%, #2c241e);
    box-shadow: 0.35rem 0.5rem 0.65rem rgb(0 0 0 / 0.18);
  }

  .railway-signal::after {
    position: absolute;
    right: -1rem;
    bottom: -0.55rem;
    left: -1rem;
    height: 0.72rem;
    border-radius: 0.2rem;
    background: #3a3027;
    content: '';
  }

  .railway-signal-light {
    position: absolute;
    top: -1rem;
    left: 50%;
    width: 2.1rem;
    height: 2.65rem;
    border: 0.22rem solid #171514;
    border-radius: 0.45rem 0.45rem 0.95rem 0.95rem;
    background: #28221e;
    transform: translateX(-50%);
  }

  .railway-signal-light::before {
    position: absolute;
    top: 0.38rem;
    left: 50%;
    width: 0.78rem;
    aspect-ratio: 1;
    border: 0.12rem solid #100d0b;
    border-radius: 50%;
    background: #d76b41;
    box-shadow: 0 0 0.9rem rgb(215 107 65 / 0.7);
    content: '';
    transform: translateX(-50%);
  }

  .railway-signal-arm {
    position: absolute;
    top: 2.2rem;
    left: 0.2rem;
    width: 4.5rem;
    height: 0.48rem;
    border: 0.1rem solid #4f1b17;
    border-radius: 0.2rem 1rem 1rem 0.2rem;
    background: #c74636;
    box-shadow: inset 0 0 0 0.11rem rgb(255 255 255 / 0.22);
    transform: rotate(-14deg);
    transform-origin: 0 50%;
  }

  .railway-water-tower {
    position: absolute;
    z-index: 3;
    right: 8%;
    bottom: 6.5rem;
    width: 6.2rem;
    height: 9.8rem;
    opacity: 0.58;
  }

  .railway-water-tank {
    position: absolute;
    top: 0;
    left: 50%;
    width: 5.8rem;
    height: 3.1rem;
    border: 0.18rem solid color-mix(in srgb, var(--text) 48%, transparent);
    border-radius: 0.6rem 0.6rem 1.15rem 1.15rem;
    background:
      repeating-linear-gradient(90deg, transparent 0 0.7rem, color-mix(in srgb, var(--text) 15%, transparent) 0.72rem 0.8rem),
      color-mix(in srgb, var(--season-1) 35%, var(--bg));
    transform: translateX(-50%);
  }

  .railway-water-legs {
    position: absolute;
    top: 2.9rem;
    bottom: 0;
    left: 50%;
    width: 4.4rem;
    border-right: 0.32rem solid color-mix(in srgb, var(--text) 47%, transparent);
    border-left: 0.32rem solid color-mix(in srgb, var(--text) 47%, transparent);
    transform: translateX(-50%) perspective(4rem) rotateX(-3deg);
  }

  .railway-water-legs::before,
  .railway-water-legs::after {
    position: absolute;
    top: 1.2rem;
    left: -0.18rem;
    width: 4.4rem;
    height: 0.2rem;
    background: color-mix(in srgb, var(--text) 47%, transparent);
    content: '';
    transform: rotate(32deg);
  }

  .railway-water-legs::after {
    transform: rotate(-32deg);
  }

  .railway-train-runner {
    position: absolute;
    z-index: 9;
    bottom: 3.55rem;
    left: 0;
    width: max-content;
    transform: translateX(calc(-100% - 7rem));
    will-change: transform;
  }

  .railway-is-running .railway-train-runner {
    animation: railway-crossing var(--railway-duration) cubic-bezier(0.35, 0.02, 0.18, 1) both;
  }

  .railway-is-static .railway-train-runner {
    left: 50%;
    transform: translateX(-50%);
  }

  .railway-train {
    display: block;
    width: clamp(62rem, 88vw, 88rem);
    height: auto;
    overflow: visible;
  }

  .railway-ground-shadow {
    fill: rgb(0 0 0 / 0.25);
    filter: blur(7px);
  }

  .railway-frame,
  .railway-front-step,
  .railway-step {
    fill: #171d1d;
    stroke: #58605e;
    stroke-width: 2;
  }

  .railway-cowcatcher {
    fill: url(#railway-steel);
    stroke: #171d1d;
    stroke-width: 4;
  }

  .railway-cowcatcher-line {
    fill: none;
    stroke: #202827;
    stroke-linecap: round;
    stroke-width: 5;
  }

  .railway-boiler,
  .railway-smokebox {
    fill: url(#railway-boiler);
    stroke: #030909;
    stroke-width: 4;
  }

  .railway-smokebox-ring {
    fill: none;
    stroke: url(#railway-brass);
    stroke-width: 5;
  }

  .railway-headlamp-shell {
    fill: #161c1c;
    stroke: url(#railway-brass);
    stroke-width: 4;
  }

  .railway-headlamp {
    fill: #fff0a0;
  }

  .railway-headlamp-beam {
    fill: url(#railway-window);
    opacity: 0.08;
  }

  .railway-boiler-band,
  .railway-brass-line,
  .railway-dome,
  .railway-chimney {
    fill: url(#railway-brass);
  }

  .railway-boiler-highlight,
  .railway-car-highlight {
    fill: none;
    stroke: rgb(255 255 255 / 0.18);
    stroke-linecap: round;
    stroke-width: 4;
  }

  .railway-cab {
    fill: url(#railway-cab);
    stroke: #260908;
    stroke-width: 4;
  }

  .railway-cab-roof,
  .railway-car-roof {
    fill: #111a1a;
    stroke: #020707;
    stroke-width: 4;
  }

  .railway-cab-window-frame,
  .railway-car-window-frame {
    fill: url(#railway-brass);
  }

  .railway-cab-window,
  .railway-car-window {
    fill: url(#railway-window);
    stroke: #1f130a;
    stroke-width: 2;
  }

  .railway-window-reflection {
    fill: none;
    stroke: rgb(255 255 255 / 0.34);
    stroke-linecap: round;
    stroke-width: 2;
  }

  .railway-cab-panel {
    fill: rgb(14 8 7 / 0.42);
    stroke: url(#railway-brass);
    stroke-width: 2;
  }

  .railway-engine-number,
  .railway-tender-mark {
    fill: #f6cf67;
    font-family: Georgia, serif;
    font-size: 21px;
    font-weight: 700;
    letter-spacing: 2px;
  }

  .railway-wheel-spokes {
    transform-box: fill-box;
    transform-origin: center;
  }

  .railway-is-running .railway-wheel-spokes {
    animation: railway-wheel-turn 0.78s linear infinite;
  }

  .railway-wheel-tire {
    fill: #090c0c;
    stroke: url(#railway-steel);
    stroke-width: 7;
  }

  .railway-wheel-rim {
    fill: #561d19;
    stroke: #c79a43;
    stroke-width: 3;
  }

  .railway-wheel-spokes {
    fill: none;
    stroke: #c6a054;
    stroke-linecap: round;
    stroke-width: 4;
  }

  .railway-wheel-hub {
    fill: url(#railway-brass);
    stroke: #3d250d;
    stroke-width: 2;
  }

  .railway-running-gear {
    fill: url(#railway-brass);
    transform-box: fill-box;
    transform-origin: center;
  }

  .railway-is-running .railway-running-gear {
    animation: railway-running-gear 0.78s ease-in-out infinite alternate;
  }

  .railway-main-rod,
  .railway-link-rod {
    fill: none;
    stroke: url(#railway-brass);
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 10;
  }

  .railway-coupler rect,
  .railway-coupler circle {
    fill: #232928;
    stroke: #6c7471;
    stroke-width: 2;
  }

  .railway-tender-body {
    fill: url(#railway-cab);
    stroke: #220807;
    stroke-width: 4;
  }

  .railway-coal {
    fill: #111313;
    stroke: #040606;
    stroke-width: 3;
  }

  .railway-tender-rail {
    fill: url(#railway-brass);
  }

  .railway-car-link {
    outline: none;
  }

  .railway-passenger-car {
    transform-box: fill-box;
    transform-origin: center;
    transition: filter var(--duration-fast) ease;
  }

  .railway-car-link--enabled {
    cursor: pointer;
  }

  .railway-car-link--enabled:hover .railway-passenger-car,
  .railway-car-link--enabled:focus-visible .railway-passenger-car {
    filter: url(#railway-shadow) brightness(1.12);
  }

  .railway-car-body {
    fill: url(#railway-car);
    stroke: #071011;
    stroke-width: 4;
  }

  .railway-car-door {
    fill: color-mix(in srgb, #152f31 82%, #000);
    stroke: url(#railway-brass);
    stroke-width: 2;
  }

  .railway-door-handle {
    fill: #e5bd59;
  }

  .railway-destination-board {
    fill: #131818;
    stroke: url(#railway-brass);
    stroke-width: 2;
  }

  .railway-destination-text {
    fill: #f8da79;
    font-family: ui-monospace, monospace;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 2px;
  }

  .railway-smoke {
    position: absolute;
    z-index: -1;
    top: -2.6rem;
    left: 8.8%;
    width: 13rem;
    height: 8rem;
    pointer-events: none;
  }

  .railway-smoke span {
    position: absolute;
    bottom: 0;
    left: 0;
    width: 2.6rem;
    aspect-ratio: 1;
    border-radius: 50%;
    background: color-mix(in srgb, var(--text) 26%, var(--bg));
    filter: blur(0.18rem);
    opacity: 0;
    transform: scale(0.35);
  }

  .railway-is-running .railway-smoke span {
    animation: railway-smoke-rise 3.4s ease-out infinite;
  }

  .railway-smoke span:nth-child(2) {
    animation-delay: -0.65s;
  }

  .railway-smoke span:nth-child(3) {
    animation-delay: -1.3s;
  }

  .railway-smoke span:nth-child(4) {
    animation-delay: -1.95s;
  }

  .railway-smoke span:nth-child(5) {
    animation-delay: -2.6s;
  }

  .railway-platform {
    position: absolute;
    z-index: 7;
    right: 10%;
    bottom: 5.25rem;
    width: min(28rem, 34vw);
    height: 2.55rem;
  }

  .railway-platform-edge {
    height: 0.56rem;
    border: 1px solid color-mix(in srgb, var(--text) 38%, transparent);
    background:
      repeating-linear-gradient(135deg, #f2d36f 0 0.7rem, #2d2c28 0.7rem 1.4rem);
    box-shadow: 0 0.3rem 0.65rem rgb(0 0 0 / 0.24);
  }

  .railway-platform-face {
    height: 2rem;
    border-bottom: 1px solid color-mix(in srgb, var(--text) 30%, transparent);
    background:
      repeating-linear-gradient(90deg, transparent 0 2.8rem, color-mix(in srgb, var(--text) 13%, transparent) 2.82rem 2.9rem),
      color-mix(in srgb, var(--surface-strong) 62%, var(--text));
  }

  .railway-track {
    position: absolute;
    z-index: 8;
    right: 0;
    bottom: 0;
    left: 0;
    height: 7.1rem;
  }

  .railway-ballast {
    position: absolute;
    inset: 1.5rem -4% 0;
    background:
      radial-gradient(circle at 12% 26%, #8b8173 0 0.15rem, transparent 0.17rem),
      radial-gradient(circle at 39% 68%, #574f47 0 0.17rem, transparent 0.19rem),
      radial-gradient(circle at 72% 31%, #a69b89 0 0.13rem, transparent 0.15rem),
      radial-gradient(circle at 88% 72%, #4a433d 0 0.18rem, transparent 0.2rem),
      repeating-radial-gradient(circle at 31% 44%, #746a5e 0 0.16rem, #4f4942 0.18rem 0.3rem, #958b7d 0.32rem 0.43rem);
    clip-path: polygon(3% 8%, 97% 8%, 100% 100%, 0 100%);
    filter: contrast(1.05) saturate(0.75);
    opacity: 0.94;
  }

  .railway-sleepers {
    position: absolute;
    right: -2rem;
    bottom: 1.02rem;
    left: -2rem;
    height: 4.65rem;
    background: repeating-linear-gradient(
      90deg,
      transparent 0 2.4rem,
      #3b261b 2.4rem 3.05rem,
      #76513a 3.08rem 3.72rem,
      #2a1a13 3.75rem 4.15rem,
      transparent 4.18rem 5.9rem
    );
    filter: drop-shadow(0 0.35rem 0.25rem rgb(0 0 0 / 0.35));
    transform: perspective(18rem) rotateX(56deg);
    transform-origin: bottom;
  }

  .railway-rail {
    position: absolute;
    right: -2%;
    left: -2%;
    height: 0.55rem;
    border-bottom: 0.18rem solid #121616;
    background: linear-gradient(180deg, #d5d8d3, #5f6866 35%, #1f2726 73%, #070a0a);
    box-shadow: 0 0.35rem 0.25rem rgb(0 0 0 / 0.35);
  }

  .railway-rail::before {
    position: absolute;
    top: -0.16rem;
    right: 0;
    left: 0;
    height: 0.13rem;
    background: rgb(255 255 255 / 0.44);
    content: '';
  }

  .railway-rail--far {
    bottom: 4.45rem;
  }

  .railway-rail--near {
    bottom: 1.62rem;
  }

  .railway-fasteners {
    position: absolute;
    right: -1rem;
    left: -1rem;
    height: 0.55rem;
    background: repeating-linear-gradient(
      90deg,
      transparent 0 2.58rem,
      #171b1a 2.6rem 2.86rem,
      #8c8f88 2.88rem 3.04rem,
      transparent 3.06rem 5.9rem
    );
  }

  .railway-fasteners--far {
    bottom: 4.08rem;
  }

  .railway-fasteners--near {
    bottom: 1.25rem;
  }

  .railway-station-sign {
    position: absolute;
    z-index: 11;
    right: 14%;
    bottom: 7.45rem;
    display: flex;
    width: clamp(8.5rem, 13vw, 12rem);
    min-height: 2.5rem;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
    padding: 0.45rem 0.55rem 0.45rem 0.8rem;
    border: 0.18rem solid color-mix(in srgb, var(--accent-strong) 70%, var(--text));
    border-radius: 0.25rem;
    background: color-mix(in srgb, var(--bg) 88%, var(--surface-strong));
    box-shadow:
      0 0.45rem 1rem rgb(0 0 0 / 0.18),
      inset 0 0 0 0.12rem color-mix(in srgb, var(--accent) 25%, transparent);
    color: var(--accent-strong);
    font-family: var(--font-display);
    font-size: clamp(0.82rem, 1.3vw, 1rem);
    font-weight: 600;
  }

  .railway-station-sign::before,
  .railway-station-sign::after {
    position: absolute;
    top: 100%;
    width: 0.18rem;
    height: 4rem;
    background: color-mix(in srgb, var(--text) 65%, #1e1e1e);
    content: '';
  }

  .railway-station-sign::before {
    left: 1.15rem;
  }

  .railway-station-sign::after {
    right: 1.15rem;
  }

  .railway-station-sign small {
    display: grid;
    width: 1.6rem;
    aspect-ratio: 1;
    place-items: center;
    border-radius: 50%;
    background: var(--accent-strong);
    color: var(--bg);
    font-family: var(--font-mono);
    font-size: 0.54rem;
  }

  .railway-foreground {
    position: absolute;
    z-index: 12;
    right: -3%;
    bottom: -0.6rem;
    left: -3%;
    height: 2.3rem;
    background:
      repeating-linear-gradient(82deg, transparent 0 1.2rem, color-mix(in srgb, var(--season-1) 38%, var(--text)) 1.24rem 1.31rem, transparent 1.34rem 2.1rem),
      linear-gradient(180deg, transparent, color-mix(in srgb, var(--season-1) 15%, var(--bg)));
    opacity: 0.42;
    pointer-events: none;
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

  :global(html[data-theme='dark']) .railway-passage {
    --railway-sky-top: color-mix(in srgb, var(--season-1) 9%, var(--bg));
    --railway-sky-bottom: color-mix(in srgb, var(--season-2) 6%, var(--bg));
    --railway-hill-far: color-mix(in srgb, var(--season-1) 12%, var(--bg));
    --railway-hill-near: color-mix(in srgb, var(--season-1) 20%, var(--bg));
  }

  :global(html[data-theme='dark']) .railway-sun {
    opacity: 0.3;
  }

  :global(html[data-theme='dark']) .railway-haze {
    opacity: 0.18;
  }

  @keyframes railway-crossing {
    0% {
      transform: translateX(calc(-100% - 7rem));
    }
    20% {
      transform: translateX(-68%);
    }
    49% {
      transform: translateX(calc(50vw - 52%));
    }
    61% {
      transform: translateX(calc(50vw - 49%));
    }
    100% {
      transform: translateX(calc(100vw + 6rem));
    }
  }

  @keyframes railway-wheel-turn {
    to {
      transform: rotate(360deg);
    }
  }

  @keyframes railway-running-gear {
    from {
      transform: translateY(-2px) rotate(-0.6deg);
    }
    to {
      transform: translateY(3px) rotate(0.6deg);
    }
  }

  @keyframes railway-smoke-rise {
    0% {
      opacity: 0;
      transform: translate(0, 1rem) scale(0.3);
    }
    16% {
      opacity: 0.5;
    }
    100% {
      opacity: 0;
      transform: translate(9rem, -6.7rem) scale(1.65);
    }
  }

  @media (max-width: 68rem) {
    .railway-scene {
      min-height: 23rem;
    }

    .railway-toolbar {
      top: 1rem;
      right: 1rem;
      left: 1rem;
    }

    .railway-train {
      width: 67rem;
    }

    .railway-platform {
      right: 5%;
      width: 38vw;
    }

    .railway-station-sign {
      right: 8%;
    }

    .railway-signal--left {
      left: 5%;
    }
  }

  @media (max-width: 42rem) {
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

    .railway-train-runner {
      bottom: 3.3rem;
    }

    .railway-train {
      width: 58rem;
    }

    .railway-landscape {
      bottom: 5.5rem;
      height: 68%;
    }

    .railway-water-tower {
      display: none;
    }

    .railway-platform {
      right: 3%;
      width: 47vw;
    }

    .railway-station-sign {
      right: 4%;
      bottom: 7.25rem;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .railway-train-runner,
    .railway-wheel-spokes,
    .railway-running-gear,
    .railway-smoke span {
      animation: none !important;
      transition: none !important;
    }

    .railway-smoke {
      display: none;
    }
  }
</style>
