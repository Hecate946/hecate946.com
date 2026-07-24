<script lang="ts">
  import type { RailwayStop } from '@/config/railway';

  export let lineName = 'Line 946';
  export let stops: readonly RailwayStop[] = [];
  export let navigationEnabled = false;
  export let motionActive = false;
  export let steamActive = false;

  function visibleStops() {
    return [...stops];
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

  <div class="railway-front-steam" aria-hidden="true">
    <span></span><span></span><span></span><span></span><span></span><span></span>
  </div>

  <svg
    class="railway-train"
    viewBox="0 0 2860 330"
    role={navigationEnabled ? 'group' : undefined}
    aria-label={navigationEnabled ? `${lineName} navigation train` : undefined}
  >
    <defs>
      <linearGradient id="railway-black-metal" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#5f6267"></stop>
        <stop offset="0.08" stop-color="#2a2e33"></stop>
        <stop offset="0.42" stop-color="#111417"></stop>
        <stop offset="0.72" stop-color="#08090b"></stop>
        <stop offset="1" stop-color="#010202"></stop>
      </linearGradient>
      <linearGradient id="railway-black-panel" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#3a3f44"></stop>
        <stop offset="0.18" stop-color="#171b1f"></stop>
        <stop offset="0.55" stop-color="#090b0d"></stop>
        <stop offset="1" stop-color="#020304"></stop>
      </linearGradient>
      <linearGradient id="railway-wood" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#7d5a38"></stop>
        <stop offset="0.45" stop-color="#5e3b21"></stop>
        <stop offset="1" stop-color="#321a0d"></stop>
      </linearGradient>
      <linearGradient id="railway-wood-dark" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#63371b"></stop>
        <stop offset="0.5" stop-color="#422311"></stop>
        <stop offset="1" stop-color="#251208"></stop>
      </linearGradient>
      <linearGradient id="railway-brass" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#d5c099"></stop>
        <stop offset="0.22" stop-color="#a78247"></stop>
        <stop offset="0.54" stop-color="#6c4824"></stop>
        <stop offset="0.8" stop-color="#b38a4e"></stop>
        <stop offset="1" stop-color="#513116"></stop>
      </linearGradient>
      <linearGradient id="railway-steel" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#f1f4f2"></stop>
        <stop offset="0.28" stop-color="#9ea7a5"></stop>
        <stop offset="0.62" stop-color="#414847"></stop>
        <stop offset="1" stop-color="#121516"></stop>
      </linearGradient>
      <radialGradient id="railway-window" cx="35%" cy="30%" r="80%">
        <stop offset="0" stop-color="#fff2d0"></stop>
        <stop offset="0.55" stop-color="#d7b16d"></stop>
        <stop offset="1" stop-color="#5f3415"></stop>
      </radialGradient>
      <linearGradient id="railway-metal-sheen" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="rgb(255 255 255 / 0.3)"></stop>
        <stop offset="0.2" stop-color="rgb(255 255 255 / 0.05)"></stop>
        <stop offset="0.55" stop-color="rgb(0 0 0 / 0.12)"></stop>
        <stop offset="1" stop-color="rgb(255 255 255 / 0.04)"></stop>
      </linearGradient>
      <filter id="railway-shadow" x="-20%" y="-35%" width="155%" height="195%">
        <feDropShadow dx="0" dy="12" stdDeviation="8" flood-color="#000" flood-opacity=".42"></feDropShadow>
      </filter>
      <filter id="railway-glow" x="-220%" y="-220%" width="440%" height="440%">
        <feGaussianBlur stdDeviation="8" result="blur"></feGaussianBlur>
        <feMerge><feMergeNode in="blur"></feMergeNode><feMergeNode in="SourceGraphic"></feMergeNode></feMerge>
      </filter>
    </defs>

    <ellipse class="railway-ground-shadow" cx="1430" cy="297" rx="1350" ry="20"></ellipse>

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
          transform={`translate(${20 + index * 286} 0)`}
          filter="url(#railway-shadow)"
        >
          <path class="railway-car-roof" d="M12 100c12-20 29-30 53-30h153c24 0 43 10 58 30l11 17H0Z"></path>
          <rect class="railway-car-body" x="4" y="108" width="272" height="110" rx="8"></rect>
          <rect class="railway-car-belt" x="4" y="152" width="272" height="7"></rect>
          <path class="railway-car-highlight" d="M20 120h236"></path>
          <path class="railway-brass-line" d="M16 130h246M16 204h246"></path>
          <rect class="railway-roof-walk" x="48" y="84" width="182" height="7" rx="3"></rect>
          <path class="railway-car-panel-lines" d="M56 129v74M94 129v74M132 129v74M170 129v74M208 129v74"></path>
          <path class="railway-car-ladder" d="M25 118v95M35 118v95M25 132h10M25 147h10M25 162h10M25 177h10M25 192h10"></path>
          <path class="railway-car-ladder" d="M243 118v95M253 118v95M243 132h10M243 147h10M243 162h10M243 177h10M243 192h10"></path>


          <rect class="railway-car-door" x="15" y="130" width="36" height="69" rx="4"></rect>
          <circle class="railway-door-handle" cx="44" cy="164" r="3"></circle>
          <rect class="railway-car-door" x="227" y="130" width="36" height="69" rx="4"></rect>
          <circle class="railway-door-handle" cx="234" cy="164" r="3"></circle>

          {#each Array(4) as _, windowIndex}
            <g transform={`translate(${60 + windowIndex * 38} 128)`}>
              <rect class="railway-car-window-frame" width="28" height="37" rx="4"></rect>
              <rect class="railway-car-window" x="4" y="4" width="20" height="29" rx="2"></rect>
              <path class="railway-window-reflection" d="m7 8 11 15M8 18l8 10"></path>
            </g>
          {/each}


          <rect class="railway-destination-board" x="76" y="97" width="128" height="22" rx="5"></rect>
          <text class="railway-destination-text" x="140" y="112" text-anchor="middle">
            {stop.shortLabel}
          </text>

          <rect class="railway-frame" x="12" y="213" width="256" height="18" rx="6"></rect>
          <rect class="railway-step" x="18" y="220" width="29" height="8" rx="3"></rect>
          <rect class="railway-step" x="233" y="220" width="29" height="8" rx="3"></rect>

          <g class="railway-wheel railway-wheel--car" transform="translate(64 230)">
            <circle class="railway-wheel-tire" r="26"></circle>
            <circle class="railway-wheel-rim" r="19"></circle>
            <path class="railway-wheel-spokes" d="M0-17V17M-17 0h34M-12-12l24 24M12-12l-24 24"></path>
            <circle class="railway-wheel-hub" r="6"></circle>
          </g>
          <g class="railway-wheel railway-wheel--car" transform="translate(210 230)">
            <circle class="railway-wheel-tire" r="26"></circle>
            <circle class="railway-wheel-rim" r="19"></circle>
            <path class="railway-wheel-spokes" d="M0-17V17M-17 0h34M-12-12l24 24M12-12l-24 24"></path>
            <circle class="railway-wheel-hub" r="6"></circle>
          </g>
          <g class="railway-coupler" transform="translate(270 221)">
            <rect x="0" y="-4.5" width="18" height="9" rx="4"></rect>
            <circle cx="21" cy="0" r="5.5"></circle>
          </g>
        </g>
      </a>
    {/each}

    <g class="railway-coupler" transform="translate(1718 221)">
      <rect x="0" y="-5" width="32" height="10" rx="4"></rect>
      <circle cx="35" cy="0" r="7"></circle>
    </g>

    <g class="railway-locomotive" filter="url(#railway-shadow)" transform="translate(-235 0)">
      <rect class="railway-frame" x="1995" y="215" width="532" height="22" rx="8"></rect>
      <path class="railway-cowcatcher" d="M2516 225h92l40 39h-170Z"></path>
      <path class="railway-cowcatcher-line" d="M2516 226 2640 262M2529 226 2618 262M2542 226 2596 262M2555 226 2578 262"></path>
      <rect class="railway-front-step" x="2466" y="205" width="86" height="13" rx="5"></rect>

      <rect class="railway-piston-cylinder" x="2408" y="177" width="93" height="31" rx="10"></rect>
      <rect class="railway-piston-arm" x="2355" y="189" width="61" height="10" rx="5"></rect>

      <path class="railway-boiler" d="M2062 111h367c42 0 77 32 77 71v31h-444Z"></path>
      <ellipse class="railway-smokebox" cx="2498" cy="163" rx="46" ry="52"></ellipse>
      <ellipse class="railway-smokebox-ring" cx="2498" cy="163" rx="35" ry="43"></ellipse>
      <path class="railway-headlamp-shell" d="M2548 132h16c15 0 26 11 26 26v3c0 12-11 23-26 23h-16Z"></path>
      <circle class="railway-headlamp" cx="2563" cy="157" r="13" filter="url(#railway-glow)"></circle>
      <circle class="railway-headlamp-core" cx="2563" cy="157" r="6"></circle>
      <path class="railway-headlamp-beam" d="M2558 149 2740 136v84l-182-26Z" filter="url(#railway-glow)"></path>
      <path class="railway-front-pipe" d="M2478 206c22-8 40-19 57-35"></path>
      <circle class="railway-smokebox-door" cx="2498" cy="163" r="8"></circle>
      <path class="railway-smokebox-hinge" d="M2489 163h-15"></path>
      <path class="railway-pilot-support" d="M2492 204h36l18 21"></path>

      <rect class="railway-boiler-band" x="2157" y="111" width="10" height="102" rx="5"></rect>
      <rect class="railway-boiler-band" x="2284" y="111" width="10" height="102" rx="5"></rect>
      <rect class="railway-boiler-band" x="2400" y="111" width="10" height="102" rx="5"></rect>
      <path class="railway-boiler-highlight" d="M2090 124h301c40 0 71 13 92 34"></path>
      <path class="railway-boiler-shadow" d="M2070 184h402"></path>
      <path class="railway-running-board-line" d="M2058 205h432"></path>
      <path class="railway-metal-sheen" d="M2078 134h335c24 0 46 7 70 22"></path>
      <path class="railway-handrail" d="M2086 142h322"></path>
      <path class="railway-pipework" d="M2092 176h278"></path>
      <path class="railway-pipework railway-pipework--lower" d="M2082 192h168l37 20"></path>
      <path class="railway-pipework railway-pipework--upper" d="M2112 128h72l18 12h126"></path>
      <path class="railway-walkway-supports" d="M2095 206v11M2145 206v11M2195 206v11M2245 206v11M2295 206v11M2345 206v11M2395 206v11M2445 206v11"></path>
      <circle class="railway-rivet" cx="2470" cy="140" r="2.2"></circle>
      <circle class="railway-rivet" cx="2470" cy="186" r="2.2"></circle>
      <circle class="railway-rivet" cx="2420" cy="136" r="2"></circle>
      <circle class="railway-rivet" cx="2420" cy="190" r="2"></circle>
      <circle class="railway-rivet" cx="2066" cy="118" r="1.8"></circle>
      <circle class="railway-rivet" cx="2106" cy="118" r="1.8"></circle>
      <circle class="railway-rivet" cx="2146" cy="118" r="1.8"></circle>
      <circle class="railway-rivet" cx="2186" cy="118" r="1.8"></circle>
      <circle class="railway-rivet" cx="2226" cy="118" r="1.8"></circle>
      <circle class="railway-rivet" cx="2266" cy="118" r="1.8"></circle>
      <circle class="railway-rivet" cx="2306" cy="118" r="1.8"></circle>

      <g class="railway-chimney">
        <path d="M2470 110h52l-9-16V48h-34v46Z"></path>
        <path d="M2466 49h60l9-15h-78Z"></path>
        <rect x="2457" y="30" width="77" height="12" rx="6"></rect>
      </g>




      <path class="railway-cab" d="M2006 73h157l35 43v110h-203V118Z"></path>
      <path class="railway-cab-roof" d="M1988 74c11-16 27-23 46-23h120c20 0 36 8 48 23Z"></path>
      <path class="railway-cab-roof-trim" d="M1998 79h188"></path>
      <rect class="railway-cab-window-frame" x="2030" y="94" width="54" height="63" rx="5"></rect>
      <rect class="railway-cab-window" x="2038" y="102" width="38" height="47" rx="3"></rect>
      <rect class="railway-cab-window-frame" x="2089" y="94" width="54" height="63" rx="5"></rect>
      <rect class="railway-cab-window" x="2097" y="102" width="38" height="47" rx="3"></rect>
      <path class="railway-window-reflection" d="M2044 108l24 25M2040 120l19 20"></path>
      <path class="railway-window-reflection" d="M2103 108l24 25M2099 120l19 20"></path>
      <rect class="railway-cab-wood-panel" x="2021" y="163" width="109" height="42" rx="4"></rect>
      <path class="railway-wood-grain" d="M2032 173h86M2032 182h86M2032 191h86"></path>
      <rect class="railway-cab-panel" x="2021" y="163" width="109" height="42" rx="4"></rect>
      <text class="railway-engine-number" x="2076" y="190" text-anchor="middle">946</text>
      <path class="railway-brass-line" d="M2010 159h143M2012 210h143"></path>
      <rect class="railway-step" x="2150" y="218" width="40" height="11" rx="4"></rect>
      <path class="railway-rear-ladder" d="M2000 118v92M2010 118v92M2000 132h10M2000 148h10M2000 164h10M2000 180h10"></path>

      <g class="railway-wheel railway-wheel--pilot" transform="translate(2040 226)">
        <circle class="railway-wheel-tire" r="22"></circle>
        <circle class="railway-wheel-rim" r="16"></circle>
        <path class="railway-wheel-spokes" d="M0-14V14M-14 0h28M-10-10l20 20M10-10l-20 20"></path>
        <circle class="railway-wheel-hub" r="5"></circle>
      </g>
      <path class="railway-underframe-shadow" d="M2048 210h430"></path>

      <g class="railway-wheel railway-wheel--driver" transform="translate(2160 218)">
        <circle class="railway-wheel-tire" r="46"></circle>
        <circle class="railway-wheel-rim" r="37"></circle>
        <path class="railway-wheel-spokes" d="M0-34V34M-34 0h68M-24-24l48 48M24-24l-48 48M-31-13l62 26M-13-31l26 62"></path>
        <circle class="railway-wheel-hub" r="10"></circle>
      </g>
      <g class="railway-wheel railway-wheel--driver" transform="translate(2285 218)">
        <circle class="railway-wheel-tire" r="46"></circle>
        <circle class="railway-wheel-rim" r="37"></circle>
        <path class="railway-wheel-spokes" d="M0-34V34M-34 0h68M-24-24l48 48M24-24l-48 48M-31-13l62 26M-13-31l26 62"></path>
        <circle class="railway-wheel-hub" r="10"></circle>
      </g>
      <g class="railway-wheel railway-wheel--driver" transform="translate(2408 218)">
        <circle class="railway-wheel-tire" r="46"></circle>
        <circle class="railway-wheel-rim" r="37"></circle>
        <path class="railway-wheel-spokes" d="M0-34V34M-34 0h68M-24-24l48 48M24-24l-48 48M-31-13l62 26M-13-31l26 62"></path>
        <circle class="railway-wheel-hub" r="10"></circle>
      </g>

      <g class="railway-driver-counterweights">
        <path d="M2148 202c8-10 18-15 30-16l-2 23c-10 0-16 4-22 12Z"></path>
        <path d="M2273 202c8-10 18-15 30-16l-2 23c-10 0-16 4-22 12Z"></path>
        <path d="M2396 202c8-10 18-15 30-16l-2 23c-10 0-16 4-22 12Z"></path>
      </g>

      <g class="railway-running-gear">
        <path class="railway-main-rod" d="M2160 218H2285H2408"></path>
        <path class="railway-side-rod" d="M2160 218 2221 178 2285 218 2347 178 2408 218"></path>
        <path class="railway-link-rod" d="M2408 218 2460 193"></path>
        <circle cx="2160" cy="218" r="7"></circle>
        <circle cx="2285" cy="218" r="7"></circle>
        <circle cx="2408" cy="218" r="7"></circle>
        <circle cx="2460" cy="193" r="6"></circle>
      </g>
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
    width: var(--railway-train-width, clamp(48rem, 68vw, 70rem));
    height: auto;
    overflow: visible;
  }

  .railway-ground-shadow {
    fill: rgb(0 0 0 / 0.28);
    filter: blur(7px);
  }

  .railway-frame,
  .railway-front-step,
  .railway-step,
  .railway-piston-cylinder,
  .railway-piston-arm {
    fill: #171b1d;
    stroke: #5e6663;
    stroke-width: 2;
  }

  .railway-cowcatcher {
    fill: url(#railway-steel);
    stroke: #171d1d;
    stroke-width: 4;
  }

  .railway-cowcatcher-line {
    fill: none;
    stroke: #aab2b3;
    stroke-linecap: round;
    stroke-width: 4.2;
    opacity: 0.92;
  }

  .railway-boiler,
  .railway-smokebox,
  .railway-headlamp-shell {
    fill: url(#railway-black-metal);
    stroke: #05080a;
    stroke-width: 4;
  }

  .railway-smokebox-ring {
    fill: none;
    stroke: url(#railway-brass);
    stroke-width: 5;
  }

  .railway-headlamp {
    fill: #fff6c3;
  }

  .railway-headlamp-core {
    fill: #fff9e4;
    opacity: 0.95;
  }

  .railway-headlamp-beam {
    fill: #ffe1a3;
    opacity: 0.2;
  }

  .railway-smokebox-door {
    fill: #111417;
    stroke: #5f6664;
    stroke-width: 2.3;
  }

  .railway-boiler-band,
  .railway-brass-line,
  .railway-running-gear,
  .railway-running-board-line {
    fill: url(#railway-brass);
  }

  .railway-chimney {
    fill: url(#railway-black-metal);
    stroke: #05080a;
    stroke-width: 4;
  }

  .railway-running-board-line,
  .railway-boiler-highlight,
  .railway-car-highlight,
  .railway-boiler-shadow,
  .railway-underframe-shadow,
  .railway-metal-sheen {
    fill: none;
    stroke-linecap: round;
  }

  .railway-running-board-line {
    stroke: url(#railway-brass);
    stroke-width: 4;
  }

  .railway-boiler-highlight,
  .railway-car-highlight {
    stroke: rgb(255 255 255 / 0.18);
    stroke-width: 4;
  }

  .railway-metal-sheen {
    stroke: url(#railway-metal-sheen);
    stroke-width: 8;
    opacity: 0.65;
  }

  .railway-boiler-shadow,
  .railway-underframe-shadow {
    stroke: rgb(0 0 0 / 0.34);
    stroke-width: 10;
    opacity: 0.8;
  }

  .railway-cab,
  .railway-car-body,
  .railway-car-door {
    fill: url(#railway-black-panel);
    stroke: #090c0e;
    stroke-width: 4;
  }

  .railway-cab-roof,
  .railway-car-roof {
    fill: #111619;
    stroke: #020607;
    stroke-width: 4;
  }

  .railway-cab-panel,
  .railway-destination-board,
  .railway-car-belt {
    fill: rgb(14 8 7 / 0.52);
    stroke: url(#railway-brass);
    stroke-width: 2;
  }

  .railway-cab-wood-panel {
    fill: url(#railway-wood);
    stroke: #2a160c;
    stroke-width: 2;
  }

  .railway-wood-grain {
    fill: none;
    stroke: rgb(255 222 171 / 0.24);
    stroke-linecap: round;
    stroke-width: 1.6;
  }

  .railway-handrail,
  .railway-pipework,
  .railway-car-panel-lines,
  .railway-car-ladder,
  .railway-front-pipe,
  .railway-cab-roof-trim,
  .railway-rear-ladder,
  .railway-walkway-supports,
  .railway-smokebox-hinge,
  .railway-pilot-support {
    fill: none;
    stroke: url(#railway-brass);
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .railway-handrail {
    stroke-width: 4;
  }

  .railway-pipework {
    stroke-width: 3.4;
  }

  .railway-pipework--lower {
    opacity: 0.72;
  }

  .railway-pipework--upper {
    stroke-width: 2.4;
    opacity: 0.84;
  }

  .railway-front-pipe {
    stroke-width: 2.8;
  }

  .railway-smokebox-hinge,
  .railway-pilot-support {
    stroke-width: 3;
  }

  .railway-walkway-supports {
    stroke-width: 2.2;
    opacity: 0.6;
  }

  .railway-cab-roof-trim,
  .railway-rear-ladder {
    stroke-width: 2.2;
  }

  .railway-car-panel-lines {
    stroke-width: 1.8;
    opacity: 0.55;
  }

  .railway-car-ladder {
    stroke-width: 2.2;
  }

  .railway-rivet {
    fill: #cda356;
    opacity: 0.85;
  }

  .railway-driver-counterweights path {
    fill: rgb(15 16 18 / 0.9);
    stroke: #a77a34;
    stroke-width: 1.8;
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

  .railway-door-handle {
    fill: #e8c167;
  }

  .railway-roof-walk {
    fill: url(#railway-wood-dark);
    stroke: url(#railway-brass);
    stroke-width: 1.5;
  }

  .railway-engine-number,
  .railway-destination-text {
    fill: #f6cf67;
    font-family: Georgia, serif;
    font-weight: 700;
    letter-spacing: 2px;
  }

  .railway-engine-number {
    font-size: 21px;
  }

  .railway-destination-text {
    font-size: 13px;
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
    stroke-width: 6;
  }

  .railway-wheel-rim {
    fill: url(#railway-wood-dark);
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
    transform-box: fill-box;
    transform-origin: center;
  }

  .railway-train-visual.is-moving .railway-running-gear {
    animation: railway-running-gear 0.72s ease-in-out infinite alternate;
  }

  .railway-main-rod,
  .railway-link-rod,
  .railway-side-rod {
    fill: none;
    stroke: url(#railway-brass);
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 9;
  }

  .railway-coupler rect,
  .railway-coupler circle {
    fill: #232928;
    stroke: #6c7471;
    stroke-width: 2;
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

  .railway-smoke {
    position: absolute;
    z-index: 0;
    top: -4rem;
    left: 77.6%;
    width: 16rem;
    height: 10rem;
    pointer-events: none;
  }

  .railway-front-steam {
    position: absolute;
    z-index: 2;
    left: 89.8%;
    bottom: 2.4rem;
    width: 7rem;
    height: 4rem;
    pointer-events: none;
  }

  .railway-smoke span {
    position: absolute;
    bottom: 0;
    left: 0;
    width: 3.2rem;
    aspect-ratio: 1;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 35%, rgb(255 255 255 / 0.98), rgb(255 255 255 / 0.84) 50%, rgb(226 232 238 / 0.22) 74%, rgb(220 226 233 / 0.08) 100%);
    filter: blur(0.24rem);
    opacity: 0;
    transform: scale(0.2);
  }

  .railway-train-visual.is-steaming .railway-smoke span {
    animation: railway-smoke-rise 4.1s ease-out infinite;
  }

  .railway-front-steam span {
    position: absolute;
    right: 0;
    bottom: 0;
    width: 2rem;
    aspect-ratio: 1;
    border-radius: 50%;
    background: radial-gradient(circle at 38% 38%, rgb(255 255 255 / 0.94), rgb(255 255 255 / 0.72) 48%, rgb(210 218 228 / 0.18) 76%, transparent 100%);
    filter: blur(0.14rem);
    opacity: 0;
    transform: scale(0.2);
  }

  .railway-train-visual.is-steaming .railway-front-steam span {
    animation: railway-front-steam-burst 1.45s ease-out infinite;
  }

  .railway-smoke span:nth-child(2) { animation-delay: -0.45s; }
  .railway-smoke span:nth-child(3) { animation-delay: -0.95s; }
  .railway-smoke span:nth-child(4) { animation-delay: -1.4s; }
  .railway-smoke span:nth-child(5) { animation-delay: -1.9s; }
  .railway-smoke span:nth-child(6) { animation-delay: -2.35s; }
  .railway-smoke span:nth-child(7) { animation-delay: -2.8s; }
  .railway-smoke span:nth-child(8) { animation-delay: -3.2s; }

  .railway-front-steam span:nth-child(2) { animation-delay: -0.22s; }
  .railway-front-steam span:nth-child(3) { animation-delay: -0.48s; }
  .railway-front-steam span:nth-child(4) { animation-delay: -0.7s; }
  .railway-front-steam span:nth-child(5) { animation-delay: -0.92s; }
  .railway-front-steam span:nth-child(6) { animation-delay: -1.16s; }

  @keyframes railway-wheel-turn {
    to {
      transform: rotate(360deg);
    }
  }

  @keyframes railway-running-gear {
    from {
      transform: translateY(-2px) rotate(-0.45deg);
    }
    to {
      transform: translateY(3px) rotate(0.45deg);
    }
  }

  @keyframes railway-smoke-rise {
    0% {
      opacity: 0;
      transform: translate(0, 1rem) scale(0.22);
    }
    10% {
      opacity: 0.78;
    }
    55% {
      opacity: 0.42;
    }
    100% {
      opacity: 0;
      transform: translate(-13rem, -8.8rem) scale(2.35);
    }
  }

  @keyframes railway-front-steam-burst {
    0% {
      opacity: 0;
      transform: translate(0, 0.25rem) scale(0.15);
    }
    18% {
      opacity: 0.86;
    }
    100% {
      opacity: 0;
      transform: translate(2.8rem, -1.8rem) scale(1.7);
    }
  }

  @media (max-width: 72rem) {
    .railway-smoke {
      top: -3.3rem;
      width: 13rem;
      height: 8rem;
    }

    .railway-front-steam {
      left: 89.2%;
      bottom: 2.05rem;
      width: 5.5rem;
      height: 3.2rem;
    }
  }

  @media (max-width: 48rem) {
    .railway-smoke {
      top: -2.55rem;
      width: 9.5rem;
      height: 6rem;
      left: 76.8%;
    }

    .railway-front-steam {
      left: 88.7%;
      bottom: 1.75rem;
      width: 4.2rem;
      height: 2.6rem;
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
