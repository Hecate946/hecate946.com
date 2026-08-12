<script lang="ts">
  import { onMount, setContext } from 'svelte';
  import type * as ThreeTypes from 'three';
  import { FLOOR_SCENE_CONTEXT, type FloorSceneContext } from './floor-scene-context';
  import '@/styles/room-shell.css';
  import '@/styles/floor-scene.css';

  const TILE_SIZE_WORLD = 84;
  const CHECKER_TEXTURE_TILES = 2;
  const CAMERA_FOV_DEGREES = 45;
  const CAMERA_HEIGHT_TO_DISTANCE = 0.4;
  const MAX_PIXEL_RATIO = 2;
  const PLANE_WIDTH_MULTIPLIER = 2.75;
  const MIN_PLANE_WIDTH = 2_400;

  export let initialCameraX = 0;

  let host: HTMLElement;
  let canvas: HTMLCanvasElement;
  let fallbackSurface: HTMLElement;
  let horizonAnchor: HTMLElement;
  let lightProbe: HTMLElement;
  let darkProbe: HTMLElement;

  let THREE: typeof import('three') | null = null;
  let renderer: ThreeTypes.WebGLRenderer | null = null;
  let scene: ThreeTypes.Scene | null = null;
  let camera: ThreeTypes.PerspectiveCamera | null = null;
  let floorMesh: ThreeTypes.Mesh<ThreeTypes.PlaneGeometry, ThreeTypes.MeshBasicMaterial> | null = null;
  let floorTexture: ThreeTypes.CanvasTexture | null = null;
  let objectRoot: ThreeTypes.Group | null = null;
  let resizeObserver: ResizeObserver | null = null;
  let themeObserver: MutationObserver | null = null;
  let disposed = false;
  let contextLost = false;
  let currentCameraX = initialCameraX;
  let lastWidth = 0;
  let lastHeight = 0;
  let lastPixelRatio = 0;
  let cameraTargetY = 0;
  let floorPlaneWidth = 1;
  let floorPlaneDepth = 1;
  const registeredObjects = new Set<ThreeTypes.Object3D>();

  function modulo(value: number, period: number) {
    return ((value % period) + period) % period;
  }

  function renderFallbackPosition() {
    fallbackSurface?.style.setProperty(
      '--floor-scene-x',
      `${-modulo(currentCameraX, TILE_SIZE_WORLD)}px`,
    );
  }

  const context: FloorSceneContext = {
    addObject(object) {
      registeredObjects.add(object);
      objectRoot?.add(object);

      return () => {
        registeredObjects.delete(object);
        object.removeFromParent();
      };
    },
    getScene: () => scene,
    getObjectRoot: () => objectRoot,
    getCameraX: () => currentCameraX,
  };

  setContext(FLOOR_SCENE_CONTEXT, context);

  /**
   * Imperative camera synchronization avoids a Svelte reactive update on every
   * animation frame. The wall remains the single source of truth for cameraX.
   */
  export function setCameraX(nextCameraX: number) {
    currentCameraX = nextCameraX;
    renderFallbackPosition();
    renderThreeScene();
  }

  function solveCameraPitch(targetNdcY: number, tanHalfFov: number) {
    const ratio = CAMERA_HEIGHT_TO_DISTANCE;
    let low = (-60 * Math.PI) / 180;
    let high = (24 * Math.PI) / 180;

    const seamNdc = (pitch: number) => {
      const sin = Math.sin(pitch);
      const cos = Math.cos(pitch);
      const cameraY = ratio;
      const forwardDistance = -cameraY * sin + cos;
      const vertical = -cameraY * cos - sin;
      return vertical / (forwardDistance * tanHalfFov);
    };

    // seamNdc decreases monotonically over this range.
    for (let index = 0; index < 48; index += 1) {
      const middle = (low + high) / 2;
      if (seamNdc(middle) > targetNdcY) low = middle;
      else high = middle;
    }

    return (low + high) / 2;
  }

  function createCheckerTexture() {
    if (!THREE) return null;

    const source = document.createElement('canvas');
    source.width = 1024;
    source.height = 1024;
    const context2d = source.getContext('2d', { alpha: false });
    if (!context2d) return null;

    const texture = new THREE.CanvasTexture(source);
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.magFilter = THREE.LinearFilter;
    texture.minFilter = THREE.LinearMipmapLinearFilter;
    texture.generateMipmaps = true;
    texture.userData.sourceCanvas = source;
    texture.userData.sourceContext = context2d;
    return texture;
  }

  function updateCheckerPalette() {
    if (!floorTexture) return;

    const source = floorTexture.userData.sourceCanvas as HTMLCanvasElement | undefined;
    const context2d = floorTexture.userData.sourceContext as CanvasRenderingContext2D | undefined;
    if (!source || !context2d) return;

    const light = getComputedStyle(lightProbe).backgroundColor || 'rgb(244, 241, 233)';
    const dark = getComputedStyle(darkProbe).backgroundColor || 'rgb(5, 5, 5)';
    const half = source.width / 2;

    context2d.fillStyle = light;
    context2d.fillRect(0, 0, half, half);
    context2d.fillRect(half, half, half, half);
    context2d.fillStyle = dark;
    context2d.fillRect(half, 0, half, half);
    context2d.fillRect(0, half, half, half);
    floorTexture.needsUpdate = true;

    renderThreeScene();
  }

  function updateFloorGeometry(width: number, height: number) {
    if (!THREE || !camera || !floorMesh || !floorTexture || !horizonAnchor) return;

    const hostRect = host.getBoundingClientRect();
    const anchorRect = horizonAnchor.getBoundingClientRect();
    const horizonY = Math.max(1, Math.min(height - 1, anchorRect.top - hostRect.top));
    const targetNdcY = 1 - (2 * horizonY) / height;
    const tanHalfFov = Math.tan(THREE.MathUtils.degToRad(CAMERA_FOV_DEGREES) / 2);
    const pitch = solveCameraPitch(targetNdcY, tanHalfFov);
    const sin = Math.sin(pitch);
    const cos = Math.cos(pitch);
    const forwardBase = -CAMERA_HEIGHT_TO_DISTANCE * sin + cos;

    // At the wall/floor seam, one world unit projects to one CSS pixel. This
    // makes cameraX and the 3D floor share the exact horizontal coordinate
    // system used by the DOM wall while perspective naturally widens tiles
    // toward the viewer.
    const desiredForwardDistance = height / (2 * tanHalfFov);
    const scale = desiredForwardDistance / forwardBase;
    const cameraZ = scale;
    const cameraY = CAMERA_HEIGHT_TO_DISTANCE * scale;
    const targetY = cameraY + cameraZ * Math.tan(pitch);
    floorPlaneWidth = Math.max(MIN_PLANE_WIDTH, width * PLANE_WIDTH_MULTIPLIER);
    floorPlaneDepth = cameraZ * 1.08;
    cameraTargetY = targetY;

    camera.fov = CAMERA_FOV_DEGREES;
    camera.aspect = width / height;
    camera.near = Math.max(0.1, height * 0.0005);
    camera.far = Math.max(4_000, cameraZ * 8);
    camera.position.set(currentCameraX, cameraY, cameraZ);
    camera.lookAt(currentCameraX, targetY, 0);
    camera.updateProjectionMatrix();

    floorMesh.geometry.dispose();
    const geometry = new THREE.PlaneGeometry(floorPlaneWidth, floorPlaneDepth, 1, 1);
    geometry.rotateX(-Math.PI / 2);
    floorMesh.geometry = geometry;
    floorMesh.position.set(currentCameraX, 0, floorPlaneDepth / 2);

    const texturePeriod = TILE_SIZE_WORLD * CHECKER_TEXTURE_TILES;
    floorTexture.repeat.set(floorPlaneWidth / texturePeriod, floorPlaneDepth / texturePeriod);
    floorTexture.offset.set(
      modulo((currentCameraX - floorPlaneWidth / 2) / texturePeriod, 1),
      modulo(-floorPlaneDepth / texturePeriod, 1),
    );

    renderer?.setSize(width, height, false);
    renderThreeScene();
  }

  function refreshLayout() {
    if (!renderer || !host) return;

    const rect = host.getBoundingClientRect();
    const width = Math.max(1, Math.round(rect.width));
    const height = Math.max(1, Math.round(rect.height));
    const pixelRatio = Math.min(MAX_PIXEL_RATIO, Math.max(1, window.devicePixelRatio || 1));

    if (pixelRatio !== lastPixelRatio) {
      renderer.setPixelRatio(pixelRatio);
      lastPixelRatio = pixelRatio;
    }

    if (width === lastWidth && height === lastHeight) {
      renderThreeScene();
      return;
    }

    lastWidth = width;
    lastHeight = height;
    updateFloorGeometry(width, height);
  }

  function renderThreeScene() {
    if (
      contextLost ||
      !THREE ||
      !renderer ||
      !scene ||
      !camera ||
      !floorMesh ||
      !floorTexture ||
      !host
    )
      return;

    camera.position.x = currentCameraX;
    camera.lookAt(currentCameraX, cameraTargetY, 0);
    floorMesh.position.x = currentCameraX;

    const texturePeriod = TILE_SIZE_WORLD * CHECKER_TEXTURE_TILES;
    floorTexture.offset.x = modulo(
      (currentCameraX - floorPlaneWidth / 2) / texturePeriod,
      1,
    );

    renderer.render(scene, camera);
  }

  onMount(() => {
    let cancelled = false;
    renderFallbackPosition();

    const onContextLost = (event: Event) => {
      event.preventDefault();
      contextLost = true;
      host?.classList.remove('floor-scene--ready');
    };

    const onContextRestored = () => {
      contextLost = false;
      updateCheckerPalette();
      refreshLayout();
      host?.classList.add('floor-scene--ready');
    };

    canvas.addEventListener('webglcontextlost', onContextLost);
    canvas.addEventListener('webglcontextrestored', onContextRestored);

    const initialize = async () => {
      try {
        THREE = await import('three');
        if (cancelled || disposed || !THREE) return;

        renderer = new THREE.WebGLRenderer({
          canvas,
          alpha: true,
          antialias: true,
          powerPreference: 'low-power',
        });
        renderer.outputColorSpace = THREE.SRGBColorSpace;
        renderer.setClearColor(0x000000, 0);

        scene = new THREE.Scene();
        camera = new THREE.PerspectiveCamera(CAMERA_FOV_DEGREES, 1, 0.1, 4_000);
        objectRoot = new THREE.Group();
        objectRoot.name = 'floor-objects';
        scene.add(objectRoot);

        floorTexture = createCheckerTexture();
        if (!floorTexture) throw new Error('Could not create floor checker texture.');
        floorTexture.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());

        const material = new THREE.MeshBasicMaterial({
          map: floorTexture,
          side: THREE.FrontSide,
        });
        floorMesh = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), material);
        floorMesh.name = 'checkerboard-floor';
        floorMesh.renderOrder = -10;
        scene.add(floorMesh);

        for (const object of registeredObjects) objectRoot.add(object);

        updateCheckerPalette();
        refreshLayout();
        host.classList.add('floor-scene--ready');

        if ('ResizeObserver' in window) {
          resizeObserver = new ResizeObserver(refreshLayout);
          resizeObserver.observe(host);
        }

        if ('MutationObserver' in window) {
          themeObserver = new MutationObserver(() => {
            updateCheckerPalette();
            refreshLayout();
          });
          themeObserver.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['data-theme'],
          });
        }

        window.addEventListener('resize', refreshLayout, { passive: true });
      } catch (error) {
        // The CSS fallback remains visible if WebGL is unavailable or Three.js
        // cannot initialize. Avoid turning a decorative enhancement into a
        // functional failure for the room.
        console.warn('[FloorScene] Falling back to CSS floor.', error);
      }
    };

    void initialize();

    return () => {
      cancelled = true;
      disposed = true;
      resizeObserver?.disconnect();
      themeObserver?.disconnect();
      window.removeEventListener('resize', refreshLayout);
      canvas.removeEventListener('webglcontextlost', onContextLost);
      canvas.removeEventListener('webglcontextrestored', onContextRestored);

      for (const object of registeredObjects) object.removeFromParent();
      floorMesh?.geometry.dispose();
      floorMesh?.material.dispose();
      floorTexture?.dispose();
      renderer?.dispose();

      floorMesh = null;
      floorTexture = null;
      objectRoot = null;
      camera = null;
      scene = null;
      renderer = null;
      THREE = null;
    };
  });
</script>

<div
  bind:this={host}
  class="floor-scene"
  style={`--floor-tile-size: ${TILE_SIZE_WORLD}px;`}
  aria-hidden="true"
>
  <canvas bind:this={canvas} class="floor-scene__canvas"></canvas>

  <div class="floor-scene__fallback">
    <div
      bind:this={fallbackSurface}
      class="floor-scene__fallback-surface"
      style={`--floor-scene-x: ${-modulo(initialCameraX, TILE_SIZE_WORLD)}px;`}
    ></div>
  </div>

  <div class="floor-scene__lighting"></div>
  <div bind:this={horizonAnchor} class="floor-scene__horizon-anchor"></div>
  <div bind:this={lightProbe} class="floor-scene__palette-probe floor-scene__palette-probe--light"></div>
  <div bind:this={darkProbe} class="floor-scene__palette-probe floor-scene__palette-probe--dark"></div>

  <div class="floor-scene__registrants">
    <slot />
  </div>
</div>
