<script lang="ts">
  import '@/styles/room-shell.css';
  import '@/styles/floor-scene.css';

  const CHECKER_PERIOD = 168;

  export let initialCameraX = 0;

  let plane: HTMLElement;
  let currentCameraX = initialCameraX;

  function modulo(value: number, period: number) {
    return ((value % period) + period) % period;
  }

  function renderCamera() {
    if (!plane) return;
    const phase = modulo(currentCameraX, CHECKER_PERIOD);
    plane.style.transform = `translate3d(${-phase}px, 0, 0) rotateX(67.5deg)`;
  }

  export function setCameraX(nextCameraX: number) {
    if (nextCameraX === currentCameraX) return;
    currentCameraX = nextCameraX;
    renderCamera();
  }
</script>

<div class="floor-scene" aria-hidden="true">
  <div class="floor-scene__underlay"></div>
  <div class="floor-scene__viewport">
    <div
      bind:this={plane}
      class="floor-scene__plane"
      style={`transform: translate3d(${-modulo(initialCameraX, CHECKER_PERIOD)}px, 0, 0) rotateX(67.5deg);`}
    ></div>
  </div>
  <div class="floor-scene__lighting"></div>
</div>
