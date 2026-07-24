<script lang="ts">
  import type { RailwayStop } from '@/config/railway';

  export let lineName = 'Line 946';
  export let stops: readonly RailwayStop[] = [];
  export let navigationEnabled = false;
  export let motionActive = false;
  export let steamActive = false;

  function visibleStops() {
    return [...stops].reverse();
  }
</script>

<div
  class:is-moving={motionActive}
  class:is-steaming={steamActive}
  class="railway-train-visual"
>
  <div class="railway-smoke" aria-hidden="true">
    <span></span><span></span><span></span><span></span>
    <span></span><span></span><span></span><span></span>
  </div>

<svg
  class="railway-train"
  viewBox="0 0 2550 292"
  role={navigationEnabled ? 'group' : undefined}
  aria-label={navigationEnabled ? `${lineName} navigation train` : undefined}
>
  <defs>
    <linearGradient id="railway-boiler" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#2b4242"></stop>
      <stop offset="0.42" stop-color="#12292b"></stop>
      <stop offset="0.75" stop-color="#071617"></stop>
      <stop offset="1" stop-color="#020607"></stop>
    </linearGradient>
    <linearGradient id="railway-cab" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#8b3c30"></stop>
      <stop offset="0.48" stop-color="#5b201b"></stop>
      <stop offset="1" stop-color="#290d0b"></stop>
    </linearGradient>
    <linearGradient id="railway-car" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#274d4f"></stop>
      <stop offset="0.48" stop-color="#173639"></stop>
      <stop offset="1" stop-color="#0c1f21"></stop>
    </linearGradient>
    <linearGradient id="railway-brass" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#fff2b8"></stop>
      <stop offset="0.25" stop-color="#d8a947"></stop>
      <stop offset="0.55" stop-color="#86561e"></stop>
      <stop offset="0.78" stop-color="#efca63"></stop>
      <stop offset="1" stop-color="#6a4215"></stop>
    </linearGradient>
    <linearGradient id="railway-steel" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#dde4e0"></stop>
      <stop offset="0.3" stop-color="#838d8b"></stop>
      <stop offset="0.65" stop-color="#303938"></stop>
      <stop offset="1" stop-color="#0d1111"></stop>
    </linearGradient>
    <radialGradient id="railway-window" cx="38%" cy="30%" r="80%">
      <stop offset="0" stop-color="#fff8cf"></stop>
      <stop offset="0.55" stop-color="#e2b45c"></stop>
      <stop offset="1" stop-color="#6b3f19"></stop>
    </radialGradient>
    <filter id="railway-shadow" x="-20%" y="-40%" width="150%" height="190%">
      <feDropShadow dx="0" dy="12" stdDeviation="8" flood-color="#000" flood-opacity=".42"></feDropShadow>
    </filter>
    <filter id="railway-glow" x="-200%" y="-200%" width="400%" height="400%">
      <feGaussianBlur stdDeviation="8" result="blur"></feGaussianBlur>
      <feMerge><feMergeNode in="blur"></feMergeNode><feMergeNode in="SourceGraphic"></feMergeNode></feMerge>
    </filter>
  </defs>

  <g class="railway-train-consist" transform="translate(2550 0) scale(-1 1)">
    <ellipse class="railway-ground-shadow" cx="1252" cy="262" rx="1186" ry="22"></ellipse>

    <g class="railway-locomotive" filter="url(#railway-shadow)">
      <path class="railway-cowcatcher" d="M28 229h95l-24 34H9Z"></path>
      <path class="railway-cowcatcher-line" d="m24 233 71 27M48 231l55 25M72 231l39 22"></path>
      <rect class="railway-frame" x="92" y="211" width="393" height="29" rx="8"></rect>
      <rect class="railway-front-step" x="55" y="205" width="94" height="15" rx="5"></rect>
      <path class="railway-boiler" d="M112 115h268c36 0 66 28 66 63v34H112Z"></path>
      <ellipse class="railway-smokebox" cx="119" cy="164" rx="34" ry="49"></ellipse>
      <ellipse class="railway-smokebox-ring" cx="119" cy="164" rx="25" ry="39"></ellipse>
      <circle class="railway-headlamp-shell" cx="103" cy="137" r="16"></circle>
      <circle class="railway-headlamp" cx="98" cy="134" r="9" filter="url(#railway-glow)"></circle>
      <path class="railway-headlamp-beam" d="M89 128-12 90v86l101-30Z" filter="url(#railway-glow)"></path>
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
      <text class="railway-engine-number" x="414" y="191" text-anchor="middle" transform="translate(828 0) scale(-1 1)">946</text>
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
      <text class="railway-tender-mark" x="638" y="181" text-anchor="middle" transform="translate(1276 0) scale(-1 1)">LINE 946</text>
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

          <rect class="railway-destination-board" x="68" y="101" width="138" height="27" rx="5"></rect>
          <text class="railway-destination-text" x="137" y="120" text-anchor="middle" transform="translate(274 0) scale(-1 1)">
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
  </g>
</svg>
</div>

<style>
  .railway-train-visual {
    position: relative;
    isolation: isolate;
    width: max-content;
  }

  .railway-train {
    position: relative;
    z-index: 1;
    display: block;
    width: clamp(95rem, 138vw, 146rem);
    height: auto;
    overflow: visible;
  }

  .railway-ground-shadow {
    fill: rgb(0 0 0 / 0.28);
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
    fill: #fff7bf;
  }

  .railway-headlamp-beam {
    fill: #ffe6b0;
    opacity: 0.22;
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

  .railway-train-visual.is-moving .railway-wheel-spokes {
    animation: railway-wheel-turn 0.72s linear infinite;
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

  .railway-train-visual.is-moving .railway-running-gear {
    animation: railway-running-gear 0.72s ease-in-out infinite alternate;
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
    z-index: 0;
    top: -4rem;
    left: 89.2%;
    width: 18rem;
    height: 10.5rem;
    pointer-events: none;
  }

  .railway-smoke span {
    position: absolute;
    bottom: 0;
    left: 0;
    width: 3.2rem;
    aspect-ratio: 1;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 35%, rgb(255 255 255 / 0.95), rgb(255 255 255 / 0.78) 55%, rgb(220 226 233 / 0.15) 100%);
    filter: blur(0.24rem);
    opacity: 0;
    transform: scale(0.2);
  }

  .railway-train-visual.is-steaming .railway-smoke span {
    animation: railway-smoke-rise 3.8s ease-out infinite;
  }

  .railway-smoke span:nth-child(2) { animation-delay: -0.45s; }
  .railway-smoke span:nth-child(3) { animation-delay: -0.95s; }
  .railway-smoke span:nth-child(4) { animation-delay: -1.4s; }
  .railway-smoke span:nth-child(5) { animation-delay: -1.9s; }
  .railway-smoke span:nth-child(6) { animation-delay: -2.35s; }
  .railway-smoke span:nth-child(7) { animation-delay: -2.8s; }
  .railway-smoke span:nth-child(8) { animation-delay: -3.2s; }


  @keyframes railway-wheel-turn {
    to {
      transform: rotate(-360deg);
    }
  }

  @keyframes railway-running-gear {
    from {
      transform: translateY(-2px) rotate(-0.55deg);
    }
    to {
      transform: translateY(3px) rotate(0.55deg);
    }
  }

  @keyframes railway-smoke-rise {
    0% {
      opacity: 0;
      transform: translate(0, 1rem) scale(0.22);
    }
    15% {
      opacity: 0.68;
    }
    100% {
      opacity: 0;
      transform: translate(-12rem, -8rem) scale(2.15);
    }
  }


  @media (max-width: 72rem) {
    .railway-train {
      width: clamp(88rem, 152vw, 128rem);
    }
  }

  @media (max-width: 48rem) {
    .railway-train {
      width: clamp(74rem, 210vw, 106rem);
    }

    .railway-smoke {
      top: -3.2rem;
      width: 12rem;
      height: 8rem;
    }
  }

  @media (prefers-reduced-motion: reduce) {
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
