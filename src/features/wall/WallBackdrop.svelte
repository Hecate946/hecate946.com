<script lang="ts">
  import '@/styles/room-shell.css';
  import '@/styles/wall-backdrop.css';

  const BRICK_PATTERN_WIDTH_PX = 96;

  export let showBaseboard = true;
  export let initialCameraX = 0;

  let brickPattern: HTMLElement;
  let currentCameraX = initialCameraX;

  function modulo(value: number, period: number) {
    return ((value % period) + period) % period;
  }

  function renderCamera() {
    brickPattern?.style.setProperty(
      '--wall-backdrop-brick-x',
      `${-modulo(currentCameraX, BRICK_PATTERN_WIDTH_PX)}px`,
    );
  }

  /** Synchronize the repeating brick layer with the room's shared camera. */
  export function setCameraX(nextCameraX: number) {
    currentCameraX = nextCameraX;
    renderCamera();
  }
</script>

<div class="wall-stage__wall-surface" aria-hidden="true">
  <div
    bind:this={brickPattern}
    class="wall-stage__brick-pattern"
    style={`--wall-backdrop-brick-x: ${-modulo(initialCameraX, BRICK_PATTERN_WIDTH_PX)}px;`}
  ></div>
</div>

<div class="wall-stage__mortar-light" aria-hidden="true"></div>

{#if showBaseboard}
  <div class="wall-baseboard" aria-hidden="true"></div>
{/if}

<div class="wall-stage__vignette" aria-hidden="true"></div>
