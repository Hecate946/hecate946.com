<script lang="ts">
  import RookGlyph from '../scenes/shared/RookGlyph.svelte';
</script>

<section
  class="chess-room-infinite"
  role="img"
  aria-label="An infinite green and ivory chessboard with a monumental black rook centered on it."
>
  <svg
    class="chess-room-rook"
    viewBox="0 0 100 110"
    preserveAspectRatio="xMidYMid meet"
    aria-hidden="true"
  >
    <defs>
      <filter id="chess-room-rook-shadow" x="-50%" y="-40%" width="200%" height="220%">
        <feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#000" flood-opacity="0.55" />
      </filter>
    </defs>
    <g filter="url(#chess-room-rook-shadow)">
      <RookGlyph x={6} y={4} scale={1.05} fill="#101416" stroke="#d9bd79" strokeWidth={1.15} />
    </g>
  </svg>
</section>
