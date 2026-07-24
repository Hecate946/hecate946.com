<script lang="ts">
  export let stationTitle = 'Home Station';
  export let boardLabel = 'Next train';
  export let boardPrimary = '00:06';
  export let boardSecondary = 'TO HOME STATION';
</script>

<div class="railway-station-scene" aria-hidden="true">
  <svg class="railway-depot" viewBox="0 0 760 330" role="presentation">
    <defs>
      <linearGradient id="depot-roof" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#77736b"></stop>
        <stop offset="0.52" stop-color="#56534e"></stop>
        <stop offset="1" stop-color="#34322f"></stop>
      </linearGradient>
      <linearGradient id="depot-timber" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#815337"></stop>
        <stop offset="0.48" stop-color="#5d351f"></stop>
        <stop offset="1" stop-color="#351b10"></stop>
      </linearGradient>
      <linearGradient id="depot-wall" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#c9a476"></stop>
        <stop offset="0.55" stop-color="#b8895c"></stop>
        <stop offset="1" stop-color="#93633e"></stop>
      </linearGradient>
      <linearGradient id="depot-glass" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#d5ecdf"></stop>
        <stop offset="0.45" stop-color="#79958b"></stop>
        <stop offset="1" stop-color="#283a36"></stop>
      </linearGradient>
      <pattern id="depot-siding" width="10" height="12" patternUnits="userSpaceOnUse">
        <rect width="10" height="12" fill="url(#depot-wall)"></rect>
        <path d="M0 11.2H10" stroke="#6c442c" stroke-opacity=".48" stroke-width="1"></path>
        <path d="M0 1H10" stroke="#edd3ab" stroke-opacity=".2" stroke-width=".7"></path>
      </pattern>
      <pattern id="depot-shingles" width="18" height="10" patternUnits="userSpaceOnUse">
        <rect width="18" height="10" fill="url(#depot-roof)"></rect>
        <path d="M0 9.3H18M9 0v9.3" stroke="#292825" stroke-opacity=".48" stroke-width=".8"></path>
        <path d="M0 1H18" stroke="#a09a90" stroke-opacity=".16" stroke-width=".7"></path>
      </pattern>
      <filter id="depot-shadow" x="-20%" y="-20%" width="140%" height="160%">
        <feDropShadow dx="0" dy="8" stdDeviation="7" flood-color="#000" flood-opacity=".32"></feDropShadow>
      </filter>
      <filter id="lamp-glow" x="-200%" y="-200%" width="400%" height="400%">
        <feGaussianBlur stdDeviation="4" result="blur"></feGaussianBlur>
        <feMerge><feMergeNode in="blur"></feMergeNode><feMergeNode in="SourceGraphic"></feMergeNode></feMerge>
      </filter>
    </defs>

    <ellipse cx="408" cy="306" rx="320" ry="18" fill="rgb(0 0 0 / .24)" filter="blur(7px)"></ellipse>

    <g filter="url(#depot-shadow)">
      <rect x="86" y="164" width="608" height="127" rx="2" fill="url(#depot-siding)" stroke="#4d2b19" stroke-width="4"></rect>
      <rect x="91" y="270" width="598" height="24" fill="url(#depot-timber)"></rect>
      <path d="M72 166h637L653 78H128Z" fill="url(#depot-shingles)" stroke="#2d2119" stroke-width="5" stroke-linejoin="round"></path>
      <path d="M82 164h619" fill="none" stroke="#2a1710" stroke-width="9" stroke-linecap="round"></path>
      <path d="M298 139 390 66l95 73Z" fill="url(#depot-shingles)" stroke="#342016" stroke-width="5" stroke-linejoin="round"></path>
      <path d="M325 139 390 83l68 56Z" fill="url(#depot-siding)" stroke="#4b2c1c" stroke-width="4"></path>
      <path d="M389 82v57M325 139l65-56 68 56" fill="none" stroke="url(#depot-timber)" stroke-width="9" stroke-linejoin="round"></path>
      <path d="M307 138h169" stroke="#2d180f" stroke-width="7" stroke-linecap="round"></path>

      <g>
        <rect x="183" y="43" width="30" height="66" fill="#9c7552" stroke="#4d3020" stroke-width="3"></rect>
        <path d="M177 43h42l-5-10h-32Z" fill="#514b43" stroke="#2c2925" stroke-width="3"></path>
        <path d="M185 53h26M185 64h26M185 75h26M185 86h26M185 97h26" stroke="#684a34" stroke-width="1.5"></path>
      </g>
      <g>
        <rect x="582" y="43" width="30" height="66" fill="#9c7552" stroke="#4d3020" stroke-width="3"></rect>
        <path d="M576 43h42l-5-10h-32Z" fill="#514b43" stroke="#2c2925" stroke-width="3"></path>
        <path d="M584 53h26M584 64h26M584 75h26M584 86h26M584 97h26" stroke="#684a34" stroke-width="1.5"></path>
      </g>

      <g class="depot-window" transform="translate(112 185)">
        <rect width="58" height="82" rx="2" fill="#4d2a19"></rect>
        <rect x="7" y="8" width="44" height="65" fill="url(#depot-glass)" stroke="#171b19" stroke-width="2"></rect>
        <path d="M29 8v65M7 30h44M7 51h44" stroke="#161a18" stroke-width="2"></path>
      </g>
      <g class="depot-window" transform="translate(220 185)">
        <rect width="58" height="82" rx="2" fill="#4d2a19"></rect>
        <rect x="7" y="8" width="44" height="65" fill="url(#depot-glass)" stroke="#171b19" stroke-width="2"></rect>
        <path d="M29 8v65M7 30h44M7 51h44" stroke="#161a18" stroke-width="2"></path>
      </g>
      <g class="depot-window" transform="translate(501 185)">
        <rect width="58" height="82" rx="2" fill="#4d2a19"></rect>
        <rect x="7" y="8" width="44" height="65" fill="url(#depot-glass)" stroke="#171b19" stroke-width="2"></rect>
        <path d="M29 8v65M7 30h44M7 51h44" stroke="#161a18" stroke-width="2"></path>
      </g>
      <g class="depot-window" transform="translate(612 185)">
        <rect width="58" height="82" rx="2" fill="#4d2a19"></rect>
        <rect x="7" y="8" width="44" height="65" fill="url(#depot-glass)" stroke="#171b19" stroke-width="2"></rect>
        <path d="M29 8v65M7 30h44M7 51h44" stroke="#161a18" stroke-width="2"></path>
      </g>

      <g transform="translate(309 173)">
        <rect width="70" height="98" fill="#4a2515" stroke="#2b160e" stroke-width="4"></rect>
        <rect x="9" y="10" width="23" height="39" fill="url(#depot-glass)" stroke="#171b19" stroke-width="2"></rect>
        <rect x="38" y="10" width="23" height="39" fill="url(#depot-glass)" stroke="#171b19" stroke-width="2"></rect>
        <path d="M35 0v98" stroke="#2c140c" stroke-width="3"></path>
        <circle cx="29" cy="63" r="2.5" fill="#d1a248"></circle>
        <circle cx="42" cy="63" r="2.5" fill="#d1a248"></circle>
      </g>
      <g transform="translate(410 173)">
        <rect width="70" height="98" fill="#4a2515" stroke="#2b160e" stroke-width="4"></rect>
        <rect x="9" y="10" width="23" height="39" fill="url(#depot-glass)" stroke="#171b19" stroke-width="2"></rect>
        <rect x="38" y="10" width="23" height="39" fill="url(#depot-glass)" stroke="#171b19" stroke-width="2"></rect>
        <path d="M35 0v98" stroke="#2c140c" stroke-width="3"></path>
        <circle cx="29" cy="63" r="2.5" fill="#d1a248"></circle>
        <circle cx="42" cy="63" r="2.5" fill="#d1a248"></circle>
      </g>

      <path d="M97 166v106M181 166v106M291 166v106M490 166v106M572 166v106M682 166v106" stroke="url(#depot-timber)" stroke-width="7"></path>
      <path d="m93 166 25-28M182 166l22-28M572 166l22-28M681 166l22-28" stroke="url(#depot-timber)" stroke-width="7" stroke-linecap="round"></path>

      <g transform="translate(143 267)">
        <path d="M0 0h60M8 0v15M52 0v15" stroke="#1c1713" stroke-width="5" stroke-linecap="round"></path>
        <path d="M5-8h50" stroke="#4a2a19" stroke-width="7" stroke-linecap="round"></path>
      </g>
      <g transform="translate(579 267)">
        <path d="M0 0h60M8 0v15M52 0v15" stroke="#1c1713" stroke-width="5" stroke-linecap="round"></path>
        <path d="M5-8h50" stroke="#4a2a19" stroke-width="7" stroke-linecap="round"></path>
      </g>

      <g transform="translate(95 171)">
        <path d="M0 0v75" stroke="#171a19" stroke-width="5"></path>
        <path d="M0 8h22" stroke="#171a19" stroke-width="4"></path>
        <path d="M22 8v16" stroke="#171a19" stroke-width="3"></path>
        <circle cx="22" cy="29" r="8" fill="#ffe3a0" filter="url(#lamp-glow)"></circle>
        <path d="M14 22h16l-3 15H17Z" fill="none" stroke="#171a19" stroke-width="3"></path>
      </g>
      <g transform="translate(690 171) scale(-1 1)">
        <path d="M0 0v75" stroke="#171a19" stroke-width="5"></path>
        <path d="M0 8h22" stroke="#171a19" stroke-width="4"></path>
        <path d="M22 8v16" stroke="#171a19" stroke-width="3"></path>
        <circle cx="22" cy="29" r="8" fill="#ffe3a0" filter="url(#lamp-glow)"></circle>
        <path d="M14 22h16l-3 15H17Z" fill="none" stroke="#171a19" stroke-width="3"></path>
      </g>

      <rect x="70" y="289" width="645" height="17" rx="2" fill="#77756e" stroke="#3f3d39" stroke-width="3"></rect>
      <path d="M70 296h645" stroke="#c6b55c" stroke-width="3"></path>
    </g>
  </svg>

  <div class="railway-digital-board">
    <span class="railway-digital-board__label">{boardLabel}</span>
    <strong>{boardPrimary}</strong>
    <span class="railway-digital-board__secondary">{boardSecondary}</span>
  </div>

  <div class="railway-station-sign">
    <div class="railway-station-sign__face">
      <span class="railway-station-sign__name">{stationTitle}</span>
      <span class="railway-station-sign__badge">946</span>
    </div>
    <span class="railway-station-sign__post railway-station-sign__post--left"></span>
    <span class="railway-station-sign__post railway-station-sign__post--right"></span>
  </div>
</div>

<style>
  .railway-station-scene {
    position: relative;
    width: 100%;
    aspect-ratio: 760 / 330;
    pointer-events: none;
  }

  .railway-depot {
    position: relative;
    z-index: 5;
    display: block;
    width: 100%;
    height: auto;
    overflow: visible;
  }

  .railway-digital-board {
    position: absolute;
    z-index: 18;
    top: 49%;
    right: 8.5%;
    display: grid;
    width: 28%;
    min-width: 9.5rem;
    gap: 0.24rem;
    padding: 0.58rem 0.72rem 0.62rem;
    border: 1px solid #464d4d;
    border-radius: 0.25rem;
    background: linear-gradient(180deg, #111515, #070909);
    box-shadow:
      0 0 0 1px rgb(255 255 255 / 0.035) inset,
      0 0.45rem 0.9rem rgb(0 0 0 / 0.3);
  }

  .railway-digital-board__label,
  .railway-digital-board__secondary {
    overflow: hidden;
    color: #aeb9b6;
    font-family: var(--font-mono);
    font-size: clamp(0.4rem, 0.65vw, 0.58rem);
    letter-spacing: 0.12em;
    text-overflow: ellipsis;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .railway-digital-board strong {
    overflow: hidden;
    color: #ffb45f;
    font-family: var(--font-mono);
    font-size: clamp(0.9rem, 1.65vw, 1.55rem);
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    letter-spacing: 0.12em;
    line-height: 1;
    text-overflow: ellipsis;
    text-shadow:
      0 0 0.15rem rgb(255 150 53 / 0.95),
      0 0 0.65rem rgb(255 150 53 / 0.34);
    white-space: nowrap;
  }

  .railway-station-sign {
    position: absolute;
    z-index: 18;
    left: 8%;
    bottom: 2.5%;
    width: 43%;
    min-width: 13rem;
    height: 24%;
  }

  .railway-station-sign__face {
    position: relative;
    z-index: 2;
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: 0.7rem;
    min-height: 3.35rem;
    padding: 0.45rem 0.7rem 0.45rem 0.9rem;
    border: 3px solid #aebdca;
    border-radius: 0.25rem;
    background: linear-gradient(180deg, #152a3d, #101d2e);
    box-shadow:
      0 0 0 1px rgb(255 255 255 / 0.12) inset,
      0 0.45rem 0.8rem rgb(0 0 0 / 0.28);
  }

  .railway-station-sign__name {
    overflow: hidden;
    color: #edf6ff;
    font-family: Georgia, serif;
    font-size: clamp(0.9rem, 1.6vw, 1.35rem);
    font-weight: 700;
    line-height: 1.05;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .railway-station-sign__badge {
    display: grid;
    width: clamp(1.75rem, 3vw, 2.35rem);
    height: clamp(1.75rem, 3vw, 2.35rem);
    place-items: center;
    border-radius: 999px;
    background: #edf5ff;
    color: #111a22;
    font-family: var(--font-mono);
    font-size: clamp(0.58rem, 0.9vw, 0.82rem);
    font-weight: 800;
    box-shadow: 0 0 0 2px rgb(255 255 255 / 0.2) inset;
  }

  .railway-station-sign__post {
    position: absolute;
    z-index: 1;
    top: 2.8rem;
    bottom: -1.1rem;
    width: 0.62rem;
    border-radius: 0 0 0.12rem 0.12rem;
    background:
      linear-gradient(90deg, rgb(255 255 255 / 0.08), transparent 35%, rgb(0 0 0 / 0.25)),
      repeating-linear-gradient(0deg, #5a351f 0 0.42rem, #69432b 0.42rem 0.54rem);
    box-shadow: 0.18rem 0.18rem 0.28rem rgb(0 0 0 / 0.28);
  }

  .railway-station-sign__post--left {
    left: 13%;
  }

  .railway-station-sign__post--right {
    right: 13%;
  }

  @media (max-width: 56rem) {
    .railway-station-sign {
      left: 5%;
      width: 50%;
      min-width: 11rem;
    }

    .railway-digital-board {
      right: 5%;
      width: 32%;
    }
  }

  @media (max-width: 38rem) {
    .railway-digital-board {
      top: 48%;
      width: 36%;
      min-width: 7.5rem;
      padding: 0.4rem 0.5rem;
    }

    .railway-digital-board__secondary {
      display: none;
    }

    .railway-station-sign {
      left: 4%;
      width: 55%;
      min-width: 9.5rem;
    }

    .railway-station-sign__face {
      min-height: 2.6rem;
      padding: 0.32rem 0.5rem 0.32rem 0.58rem;
      border-width: 2px;
    }

    .railway-station-sign__post {
      top: 2.2rem;
      width: 0.48rem;
    }
  }
</style>
