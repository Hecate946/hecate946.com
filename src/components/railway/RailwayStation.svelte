<script lang="ts">
  export let stationTitle = 'Home Station';
</script>

<div class="railway-station-scene" aria-hidden="true">
  <svg class="railway-depot" viewBox="0 0 1240 560" role="presentation">
    <defs>
      <linearGradient id="roof-main" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#9a938a"></stop>
        <stop offset="0.42" stop-color="#6c665f"></stop>
        <stop offset="1" stop-color="#312d2a"></stop>
      </linearGradient>
      <linearGradient id="roof-shadow" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#2e2926"></stop>
        <stop offset="1" stop-color="#141210"></stop>
      </linearGradient>
      <linearGradient id="wood-light" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#ddc09a"></stop>
        <stop offset="0.4" stop-color="#c79967"></stop>
        <stop offset="1" stop-color="#895632"></stop>
      </linearGradient>
      <linearGradient id="wood-mid" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#99613f"></stop>
        <stop offset="0.46" stop-color="#6d4027"></stop>
        <stop offset="1" stop-color="#3e2314"></stop>
      </linearGradient>
      <linearGradient id="wood-dark" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#58311d"></stop>
        <stop offset="0.5" stop-color="#361d11"></stop>
        <stop offset="1" stop-color="#1c0f09"></stop>
      </linearGradient>
      <linearGradient id="glass" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#e4f0e7"></stop>
        <stop offset="0.4" stop-color="#9db2a9"></stop>
        <stop offset="1" stop-color="#30443f"></stop>
      </linearGradient>
      <pattern id="wood-siding" width="14" height="14" patternUnits="userSpaceOnUse">
        <rect width="14" height="14" fill="url(#wood-light)"></rect>
        <path d="M0 12.6H14" stroke="#6f452d" stroke-opacity=".58" stroke-width="1"></path>
        <path d="M0 1.4H14" stroke="#f3d8b5" stroke-opacity=".24" stroke-width="0.85"></path>
      </pattern>
      <pattern id="shingles" width="18" height="10" patternUnits="userSpaceOnUse">
        <rect width="18" height="10" fill="url(#roof-main)"></rect>
        <path d="M0 9.2H18M9 0v9.2" stroke="#2d2925" stroke-opacity=".56" stroke-width="0.8"></path>
        <path d="M0 1.1H18" stroke="#dad3ca" stroke-opacity=".14" stroke-width="0.7"></path>
      </pattern>
      <filter id="depot-shadow" x="-20%" y="-20%" width="160%" height="190%">
        <feDropShadow dx="0" dy="14" stdDeviation="11" flood-color="#000" flood-opacity=".28"></feDropShadow>
      </filter>
      <filter id="lamp-glow" x="-200%" y="-200%" width="400%" height="400%">
        <feGaussianBlur stdDeviation="4.8" result="blur"></feGaussianBlur>
        <feMerge><feMergeNode in="blur"></feMergeNode><feMergeNode in="SourceGraphic"></feMergeNode></feMerge>
      </filter>
    </defs>

    <ellipse cx="620" cy="506" rx="430" ry="23" fill="rgb(0 0 0 / 0.18)" filter="blur(8px)"></ellipse>

    <g filter="url(#depot-shadow)">
      <rect x="236" y="256" width="768" height="156" rx="3" fill="url(#wood-siding)" stroke="#4f2f1c" stroke-width="4"></rect>
      <rect x="242" y="388" width="756" height="26" fill="url(#wood-dark)"></rect>

      <path d="M202 258h836L942 126H296Z" fill="url(#shingles)" stroke="#2d2119" stroke-width="5" stroke-linejoin="round"></path>
      <path d="M218 256h804" fill="none" stroke="#26160f" stroke-width="10" stroke-linecap="round"></path>
      <path d="M226 257h788" fill="none" stroke="rgb(255 255 255 / 0.09)" stroke-width="2"></path>

      <path d="M470 214 620 118l151 96Z" fill="url(#shingles)" stroke="#342016" stroke-width="5" stroke-linejoin="round"></path>
      <path d="M507 214 620 141l117 73Z" fill="url(#wood-siding)" stroke="#4b2c1c" stroke-width="4"></path>
      <path d="M620 140v74M507 214l113-74 117 74" fill="none" stroke="url(#wood-mid)" stroke-width="12" stroke-linejoin="round"></path>
      <path d="M487 214h268" stroke="#27160f" stroke-width="10" stroke-linecap="round"></path>

      <path d="M218 258h804l-18 20H236Z" fill="url(#roof-shadow)"></path>
      <rect x="258" y="278" width="724" height="18" fill="rgb(32 18 12 / 0.68)"></rect>
      <path d="M258 296h724" stroke="rgb(255 228 190 / 0.12)" stroke-width="2"></path>

      <g>
        <rect x="360" y="80" width="30" height="76" fill="#9f7753" stroke="#4b3021" stroke-width="3"></rect>
        <path d="M353 80h44l-4-10h-36Z" fill="#5f5750" stroke="#2c2925" stroke-width="3"></path>
        <path d="M366 92h18M366 104h18M366 116h18M366 128h18M366 140h18M366 152h18" stroke="#735337" stroke-width="1.3"></path>
      </g>
      <g>
        <rect x="848" y="80" width="30" height="76" fill="#9f7753" stroke="#4b3021" stroke-width="3"></rect>
        <path d="M841 80h44l-4-10h-36Z" fill="#5f5750" stroke="#2c2925" stroke-width="3"></path>
        <path d="M854 92h18M854 104h18M854 116h18M854 128h18M854 140h18M854 152h18" stroke="#735337" stroke-width="1.3"></path>
      </g>

      <g transform="translate(258 294)">
        <rect width="64" height="96" rx="2" fill="#4c2a1a"></rect>
        <rect x="7" y="8" width="50" height="76" fill="url(#glass)" stroke="#141917" stroke-width="2"></rect>
        <path d="M32 8v76M7 35h50M7 60h50" stroke="#141917" stroke-width="2"></path>
        <path d="M6 86h52" stroke="rgb(0 0 0 / 0.34)" stroke-width="8"></path>
      </g>
      <g transform="translate(348 294)">
        <rect width="64" height="96" rx="2" fill="#4c2a1a"></rect>
        <rect x="7" y="8" width="50" height="76" fill="url(#glass)" stroke="#141917" stroke-width="2"></rect>
        <path d="M32 8v76M7 35h50M7 60h50" stroke="#141917" stroke-width="2"></path>
        <path d="M6 86h52" stroke="rgb(0 0 0 / 0.34)" stroke-width="8"></path>
      </g>
      <g transform="translate(830 294)">
        <rect width="64" height="96" rx="2" fill="#4c2a1a"></rect>
        <rect x="7" y="8" width="50" height="76" fill="url(#glass)" stroke="#141917" stroke-width="2"></rect>
        <path d="M32 8v76M7 35h50M7 60h50" stroke="#141917" stroke-width="2"></path>
        <path d="M6 86h52" stroke="rgb(0 0 0 / 0.34)" stroke-width="8"></path>
      </g>
      <g transform="translate(920 294)">
        <rect width="64" height="96" rx="2" fill="#4c2a1a"></rect>
        <rect x="7" y="8" width="50" height="76" fill="url(#glass)" stroke="#141917" stroke-width="2"></rect>
        <path d="M32 8v76M7 35h50M7 60h50" stroke="#141917" stroke-width="2"></path>
        <path d="M6 86h52" stroke="rgb(0 0 0 / 0.34)" stroke-width="8"></path>
      </g>

      <g transform="translate(484 284)">
        <rect width="78" height="110" fill="#4b2818" stroke="#2b160e" stroke-width="4"></rect>
        <rect x="10" y="12" width="24" height="42" fill="url(#glass)" stroke="#171b19" stroke-width="2"></rect>
        <rect x="44" y="12" width="24" height="42" fill="url(#glass)" stroke="#171b19" stroke-width="2"></rect>
        <path d="M39 0v110" stroke="#2d150d" stroke-width="3"></path>
        <circle cx="33" cy="73" r="2.6" fill="#d0a248"></circle>
        <circle cx="46" cy="73" r="2.6" fill="#d0a248"></circle>
        <path d="M2 102h74" stroke="rgb(0 0 0 / 0.42)" stroke-width="10"></path>
      </g>
      <g transform="translate(678 284)">
        <rect width="78" height="110" fill="#4b2818" stroke="#2b160e" stroke-width="4"></rect>
        <rect x="10" y="12" width="24" height="42" fill="url(#glass)" stroke="#171b19" stroke-width="2"></rect>
        <rect x="44" y="12" width="24" height="42" fill="url(#glass)" stroke="#171b19" stroke-width="2"></rect>
        <path d="M39 0v110" stroke="#2d150d" stroke-width="3"></path>
        <circle cx="33" cy="73" r="2.6" fill="#d0a248"></circle>
        <circle cx="46" cy="73" r="2.6" fill="#d0a248"></circle>
        <path d="M2 102h74" stroke="rgb(0 0 0 / 0.42)" stroke-width="10"></path>
      </g>

      <path d="M240 258v134M334 258v134M450 258v134M790 258v134M906 258v134M1000 258v134" stroke="url(#wood-mid)" stroke-width="8"></path>
      <path d="M240 258 264 228M334 258l24-30M450 258l24-30M790 258l-24-30M906 258l-24-30M1000 258l-24-30" stroke="url(#wood-mid)" stroke-width="8" stroke-linecap="round"></path>

      <rect x="474" y="188" width="294" height="32" rx="3" fill="url(#wood-dark)" stroke="#352014" stroke-width="3"></rect>
      <text x="621" y="210" text-anchor="middle" fill="#f8ead1" font-family="Georgia, serif" font-size="18" font-weight="700" letter-spacing="1.02">{stationTitle.toUpperCase()}</text>

      <path d="M255 416h734" stroke="#000" stroke-opacity=".24" stroke-width="12"></path>
      <rect x="212" y="416" width="816" height="20" rx="3" fill="#7d7a72" stroke="#43403b" stroke-width="3"></rect>
      <path d="M212 424h816" stroke="#d1bd66" stroke-width="3"></path>
      <path d="M244 436h752" stroke="#302d2a" stroke-width="5"></path>

      <g transform="translate(254 392)">
        <path d="M0 0h64M8 0v16M56 0v16" stroke="#1d1814" stroke-width="5" stroke-linecap="round"></path>
        <path d="M6-8h52" stroke="#4a2a19" stroke-width="8" stroke-linecap="round"></path>
      </g>
      <g transform="translate(920 392)">
        <path d="M0 0h64M8 0v16M56 0v16" stroke="#1d1814" stroke-width="5" stroke-linecap="round"></path>
        <path d="M6-8h52" stroke="#4a2a19" stroke-width="8" stroke-linecap="round"></path>
      </g>

      <g transform="translate(240 286)">
        <path d="M0 0v84" stroke="#171a19" stroke-width="5"></path>
        <path d="M0 8h24" stroke="#171a19" stroke-width="4"></path>
        <path d="M24 8v15" stroke="#171a19" stroke-width="3"></path>
        <circle cx="24" cy="30" r="8.4" fill="#ffe2a2" filter="url(#lamp-glow)"></circle>
        <path d="M15 23h18l-3 16H18Z" fill="none" stroke="#171a19" stroke-width="3"></path>
      </g>
      <g transform="translate(1000 286) scale(-1 1)">
        <path d="M0 0v84" stroke="#171a19" stroke-width="5"></path>
        <path d="M0 8h24" stroke="#171a19" stroke-width="4"></path>
        <path d="M24 8v15" stroke="#171a19" stroke-width="3"></path>
        <circle cx="24" cy="30" r="8.4" fill="#ffe2a2" filter="url(#lamp-glow)"></circle>
        <path d="M15 23h18l-3 16H18Z" fill="none" stroke="#171a19" stroke-width="3"></path>
      </g>

      <path d="M244 250h752" stroke="rgb(255 233 202 / 0.11)" stroke-width="4"></path>
      <path d="M250 406h740" stroke="rgb(0 0 0 / 0.34)" stroke-width="8"></path>
    </g>
  </svg>
</div>

<style>
  .railway-station-scene {
    position: relative;
    width: 100%;
    aspect-ratio: 1240 / 560;
    pointer-events: none;
  }

  .railway-depot {
    display: block;
    width: 100%;
    height: auto;
    overflow: visible;
  }
</style>
