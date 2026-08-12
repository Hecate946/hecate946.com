<script lang="ts">
  import { onMount } from 'svelte';
  import '@/styles/room-shell.css';
  import '@/styles/floor-scene.css';

  const TILE_SIZE_WORLD = 84;
  const CAMERA_FOV_DEGREES = 45;
  const CAMERA_HEIGHT_TO_DISTANCE = 0.4;
  // The checkerboard contains only flat fills and short diagonal edges. 1.5x
  // keeps retina edges crisp without paying the full 2x canvas cost.
  const MAX_PIXEL_RATIO = 1.5;

  export let initialCameraX = 0;

  let host: HTMLElement;
  let canvas: HTMLCanvasElement;
  let horizonAnchor: HTMLElement;
  let lightProbe: HTMLElement;
  let darkProbe: HTMLElement;

  let context2d: CanvasRenderingContext2D | null = null;
  let resizeObserver: ResizeObserver | null = null;
  let themeObserver: MutationObserver | null = null;
  let currentCameraX = initialCameraX;
  let width = 1;
  let height = 1;
  let horizonY = 1;
  let pixelRatio = 1;
  let pitch = 0;
  let pitchSin = 0;
  let pitchCos = 1;
  let visibleDepth = TILE_SIZE_WORLD;
  let lastVisibleRow = 1;
  let cameraY = 1;
  let cameraZ = 1;
  let focalDistance = 1;
  let lightColor = 'rgb(244, 241, 233)';
  let darkColor = 'rgb(5, 5, 5)';

  function solveCameraPitch(targetNdcY: number, tanHalfFov: number) {
    const ratio = CAMERA_HEIGHT_TO_DISTANCE;
    let low = (-60 * Math.PI) / 180;
    let high = (24 * Math.PI) / 180;

    const seamNdc = (candidatePitch: number) => {
      const sin = Math.sin(candidatePitch);
      const cos = Math.cos(candidatePitch);
      const forwardDistance = -ratio * sin + cos;
      const vertical = -ratio * cos - sin;
      return vertical / (forwardDistance * tanHalfFov);
    };

    for (let index = 0; index < 48; index += 1) {
      const middle = (low + high) / 2;
      if (seamNdc(middle) > targetNdcY) low = middle;
      else high = middle;
    }

    return (low + high) / 2;
  }

  function project(worldX: number, worldZ: number) {
    const forwardDistance =
      -cameraY * pitchSin + (worldZ - cameraZ) * -pitchCos;

    if (forwardDistance <= 0.001) {
      return { x: Number.POSITIVE_INFINITY, y: Number.POSITIVE_INFINITY };
    }

    const vertical = -cameraY * pitchCos + (worldZ - cameraZ) * pitchSin;
    const scale = focalDistance / forwardDistance;

    return {
      x: width / 2 + (worldX - currentCameraX) * scale,
      y: height / 2 - vertical * scale,
    };
  }

  function solveVisibleDepth() {
    // Find the world-space Z coordinate that lands exactly on the bottom of
    // the viewport. The old Three.js plane used the same camera projection;
    // solving this analytically lets the lightweight canvas draw the identical
    // visible portion without allocating a WebGL scene or importing Three.
    let low = 0;
    let high = cameraZ * 0.999;

    for (let index = 0; index < 36; index += 1) {
      const middle = (low + high) / 2;
      const point = project(currentCameraX, middle);
      if (point.y < height) low = middle;
      else high = middle;
    }

    return Math.max(TILE_SIZE_WORLD, (low + high) / 2);
  }

  function drawLightTile(x0: number, x1: number, z0: number, z1: number) {
    if (!context2d) return;

    const a = project(x0, z0);
    const b = project(x1, z0);
    const c = project(x1, z1);
    const d = project(x0, z1);

    if (
      Math.max(a.x, b.x, c.x, d.x) < -2 ||
      Math.min(a.x, b.x, c.x, d.x) > width + 2 ||
      Math.max(a.y, b.y, c.y, d.y) < horizonY - 2 ||
      Math.min(a.y, b.y, c.y, d.y) > height + 2
    ) {
      return;
    }

    context2d.moveTo(a.x, a.y);
    context2d.lineTo(b.x, b.y);
    context2d.lineTo(c.x, c.y);
    context2d.lineTo(d.x, d.y);
    context2d.closePath();
  }

  function renderFloor() {
    if (!context2d || !host || width <= 1 || height <= 1) return;

    context2d.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    context2d.clearRect(0, 0, width, height);

    // Paint the dark half once, then paint only the light checker cells on top.
    // This avoids antialiased hairline cracks between hundreds of neighboring
    // polygons and cuts the amount of path work roughly in half.
    context2d.fillStyle = darkColor;
    context2d.fillRect(0, horizonY, width, Math.max(0, height - horizonY));

    context2d.save();
    context2d.beginPath();
    context2d.rect(0, horizonY, width, Math.max(0, height - horizonY));
    context2d.clip();
    context2d.fillStyle = lightColor;

    const firstColumn = Math.floor((currentCameraX - width / 2) / TILE_SIZE_WORLD) - 1;
    const lastColumn = Math.ceil((currentCameraX + width / 2) / TILE_SIZE_WORLD) + 1;

    // Build all visible light cells into one canvas path and fill once. The old
    // renderer issued a beginPath/fill pair for every tile, which dominated CPU
    // time while the conveyor was moving. Geometry and appearance are unchanged.
    context2d.beginPath();
    for (let row = 0; row <= lastVisibleRow; row += 1) {
      const z0 = row * TILE_SIZE_WORLD;
      const z1 = Math.min((row + 1) * TILE_SIZE_WORLD, visibleDepth + TILE_SIZE_WORLD);

      for (let column = firstColumn; column <= lastColumn; column += 1) {
        // The legacy texture is anchored in world space with the first cell to
        // the right of X=0 rendered dark. Negative Z texture coordinates flip
        // the row parity, so light cells are exactly the odd parity cells here.
        if ((column + row) % 2 === 0) continue;

        const x0 = column * TILE_SIZE_WORLD;
        const x1 = (column + 1) * TILE_SIZE_WORLD;
        drawLightTile(x0, x1, z0, z1);
      }
    }

    context2d.fill();
    context2d.restore();
  }

  function refreshPalette() {
    if (!lightProbe || !darkProbe) return;
    lightColor = getComputedStyle(lightProbe).backgroundColor || 'rgb(244, 241, 233)';
    darkColor = getComputedStyle(darkProbe).backgroundColor || 'rgb(5, 5, 5)';
  }

  function refreshLayout() {
    if (!host || !canvas || !horizonAnchor) return;

    const hostRect = host.getBoundingClientRect();
    const anchorRect = horizonAnchor.getBoundingClientRect();
    width = Math.max(1, Math.round(hostRect.width));
    height = Math.max(1, Math.round(hostRect.height));
    horizonY = Math.max(1, Math.min(height - 1, anchorRect.top - hostRect.top));
    pixelRatio = Math.min(MAX_PIXEL_RATIO, Math.max(1, window.devicePixelRatio || 1));

    const backingWidth = Math.max(1, Math.round(width * pixelRatio));
    const backingHeight = Math.max(1, Math.round(height * pixelRatio));
    if (canvas.width !== backingWidth) canvas.width = backingWidth;
    if (canvas.height !== backingHeight) canvas.height = backingHeight;

    const tanHalfFov = Math.tan((CAMERA_FOV_DEGREES * Math.PI) / 360);
    const targetNdcY = 1 - (2 * horizonY) / height;
    pitch = solveCameraPitch(targetNdcY, tanHalfFov);
    pitchSin = Math.sin(pitch);
    pitchCos = Math.cos(pitch);

    const forwardBase = -CAMERA_HEIGHT_TO_DISTANCE * pitchSin + pitchCos;
    focalDistance = height / (2 * tanHalfFov);
    const scale = focalDistance / forwardBase;
    cameraZ = scale;
    cameraY = CAMERA_HEIGHT_TO_DISTANCE * scale;
    visibleDepth = solveVisibleDepth();
    lastVisibleRow = Math.ceil(visibleDepth / TILE_SIZE_WORLD) + 1;

    renderFloor();
  }

  /** Re-read inherited room colors and geometry after an Astro body swap. */
  export function refreshFromCss() {
    refreshPalette();
    refreshLayout();
  }

  /** Synchronize the checkerboard with the wall's shared horizontal camera. */
  export function setCameraX(nextCameraX: number) {
    if (nextCameraX === currentCameraX) return;
    currentCameraX = nextCameraX;
    renderFloor();
  }

  onMount(() => {
    context2d =
      canvas.getContext('2d', { alpha: true, desynchronized: true }) ??
      canvas.getContext('2d', { alpha: true });
    refreshPalette();
    refreshLayout();

    if ('ResizeObserver' in window) {
      resizeObserver = new ResizeObserver(refreshLayout);
      resizeObserver.observe(host);
    }

    if ('MutationObserver' in window) {
      themeObserver = new MutationObserver(() => {
        refreshPalette();
        renderFloor();
      });
      themeObserver.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-theme'],
      });
    }

    window.addEventListener('resize', refreshLayout, { passive: true });

    return () => {
      resizeObserver?.disconnect();
      themeObserver?.disconnect();
      window.removeEventListener('resize', refreshLayout);
      context2d = null;
    };
  });
</script>

<div bind:this={host} class="floor-scene" aria-hidden="true">
  <div class="floor-scene__underlay"></div>
  <canvas bind:this={canvas} class="floor-scene__canvas"></canvas>
  <div class="floor-scene__lighting"></div>
  <div bind:this={horizonAnchor} class="floor-scene__horizon-anchor"></div>
  <div bind:this={lightProbe} class="floor-scene__palette-probe floor-scene__palette-probe--light"></div>
  <div bind:this={darkProbe} class="floor-scene__palette-probe floor-scene__palette-probe--dark"></div>
</div>
