<script lang="ts">
  import RookGlyph from './RookGlyph.svelte';

  const width = 1600;
  const height = 900;
  const cellSize = 100;
  const columns = Math.ceil(width / cellSize);
  const rows = Math.ceil(height / cellSize);
  const squares = Array.from({ length: columns * rows }, (_, index) => ({
    column: index % columns,
    row: Math.floor(index / columns),
  }));
</script>

<g class="chess-board-artwork" aria-hidden="true">
  <defs>
    <linearGradient id="chess-dark-square" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#355b49" />
      <stop offset="1" stop-color="#183128" />
    </linearGradient>
    <linearGradient id="chess-light-square" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#efe7ca" />
      <stop offset="1" stop-color="#d0bd8e" />
    </linearGradient>
    <radialGradient id="chess-vignette" cx="50%" cy="47%" r="72%">
      <stop offset="45%" stop-color="#000" stop-opacity="0" />
      <stop offset="100%" stop-color="#000" stop-opacity="0.46" />
    </radialGradient>
    <filter id="rook-shadow" x="-40%" y="-30%" width="180%" height="190%">
      <feDropShadow dx="0" dy="24" stdDeviation="18" flood-color="#000" flood-opacity="0.5" />
    </filter>
  </defs>

  <rect width={width} height={height} fill="#17231f" />
  {#each squares as square}
    <rect
      x={square.column * cellSize}
      y={square.row * cellSize}
      width={cellSize + 0.5}
      height={cellSize + 0.5}
      fill={(square.column + square.row) % 2 === 0 ? 'url(#chess-light-square)' : 'url(#chess-dark-square)'}
    />
  {/each}

  <g opacity="0.15" fill="#fff0bd">
    <circle cx="250" cy="150" r="38" />
    <circle cx="1350" cy="750" r="38" />
    <path d="M1170 145 1218 84 1266 145 1240 208H1196Z" />
    <path d="M334 720 382 659 430 720 404 783H360Z" />
  </g>

  <g filter="url(#rook-shadow)">
    <RookGlyph x={574} y={104} scale={5.2} fill="#101416" stroke="#d9bd79" strokeWidth={1.2} />
  </g>

  <rect width={width} height={height} fill="url(#chess-vignette)" />
  <path d={`M0 0H${width}V${height}H0Z`} fill="none" stroke="#e2c986" stroke-width="10" opacity="0.45" />
</g>
