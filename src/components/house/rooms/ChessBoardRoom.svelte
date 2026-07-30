<script lang="ts">
  import { withBase } from '@/lib/paths';
  const imageHref = withBase('/scenes/house/windows/chess-black-rook-room.png');
</script>

<section
  class="chess-room-png"
  role="img"
  aria-label="An infinite green and ivory chessboard with a centered black rook based on a realistic rook silhouette."
>
  <img src={imageHref} alt="" aria-hidden="true" />
</section>

<style>
  .chess-room-png {
    width: 100%;
    height: 100%;
    display: grid;
    place-items: center;
    overflow: hidden;
    background: #17231f;
  }

  .chess-room-png img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
</style>
