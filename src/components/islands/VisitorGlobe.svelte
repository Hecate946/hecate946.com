<script lang="ts">
  import { onMount } from 'svelte';
  import * as THREE from 'three';
  import { WORLD_MAP_PATH } from '@/data/world-map';
  import { WORLD_COUNTRY_OUTLINES_PATH } from '@/data/world-country-outlines';

  export let apiBase = '';

  interface VisitorLocation {
    city: string | null;
    region: string | null;
    country: string | null;
    countryCode: string | null;
    latitude: number;
    longitude: number;
    pageViews: number;
    estimatedVisitors: number;
    pointIndex?: number;
    pointCount?: number;
  }

  interface LiveStats {
    summary: {
      estimatedVisitors: number;
      updatedAt: string | null;
    };
    locations: VisitorLocation[];
  }

  interface GlobeMarker {
    latitude: number;
    longitude: number;
    count: number;
    label: string;
  }

  interface PointerPoint {
    x: number;
    y: number;
  }

  interface PinchState {
    distance: number;
    cameraZ: number;
  }

  const GLOBE_RADIUS = 2.35;
  const MARKER_RADIUS = GLOBE_RADIUS + 0.038;
  const MIN_CAMERA_Z = 3.55;
  const MAX_CAMERA_Z = 9.5;
  const INITIAL_CAMERA_Z = 6.45;
  const WORLD_TEXTURE_WIDTH = 4096;
  const WORLD_TEXTURE_HEIGHT = 2048;

  let shell!: HTMLDivElement;
  let canvas!: HTMLCanvasElement;
  let loading = true;
  let error = '';
  let visitorCount = 0;
  let updatedAt: string | null = null;
  let tooltipVisible = false;
  let tooltipX = 0;
  let tooltipY = 0;
  let tooltipText = '';

  let resetGlobe: (() => void) | null = null;

  function clamp(value: number, minimum: number, maximum: number) {
    return Math.min(maximum, Math.max(minimum, value));
  }

  function locationLabel(location: VisitorLocation) {
    return [location.city, location.region, location.country]
      .filter(Boolean)
      .join(', ') || 'Approximate visitor location';
  }

  function groupLocations(locations: VisitorLocation[]): GlobeMarker[] {
    const groups = new Map<string, GlobeMarker>();

    for (const location of locations) {
      if (
        !Number.isFinite(location.latitude) ||
        !Number.isFinite(location.longitude)
      ) {
        continue;
      }

      const key = `${location.latitude.toFixed(5)}:${location.longitude.toFixed(5)}`;
      const existing = groups.get(key);

      if (existing) {
        existing.count += 1;
        continue;
      }

      groups.set(key, {
        latitude: location.latitude,
        longitude: location.longitude,
        count: 1,
        label: locationLabel(location),
      });
    }

    return [...groups.values()];
  }

  function markerPosition(latitude: number, longitude: number, radius: number) {
    const phi = THREE.MathUtils.degToRad(90 - latitude);
    const theta = THREE.MathUtils.degToRad(longitude + 180);

    return new THREE.Vector3(
      -radius * Math.sin(phi) * Math.cos(theta),
      radius * Math.cos(phi),
      radius * Math.sin(phi) * Math.sin(theta),
    );
  }

  function readThemeColors() {
    const styles = getComputedStyle(document.documentElement);

    return {
      text: styles.getPropertyValue('--text').trim() || '#242421',
      background: styles.getPropertyValue('--bg').trim() || '#ffffff',
      accent:
        styles.getPropertyValue('--accent-strong').trim() ||
        styles.getPropertyValue('--text').trim() ||
        '#242421',
    };
  }

  async function makeWorldTexture(renderer: THREE.WebGLRenderer) {
    const colors = readThemeColors();
    const textureWidth = Math.min(
      WORLD_TEXTURE_WIDTH,
      renderer.capabilities.maxTextureSize,
    );
    const textureHeight = Math.min(
      WORLD_TEXTURE_HEIGHT,
      Math.floor(textureWidth / 2),
    );
    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 500" width="${textureWidth}" height="${textureHeight}">
        <path
          d="${WORLD_MAP_PATH}"
          fill="${colors.text}"
          fill-opacity="0.12"
          stroke="${colors.text}"
          stroke-opacity="0.42"
          stroke-width="0.75"
          vector-effect="non-scaling-stroke"
        />
        <path
          d="${WORLD_COUNTRY_OUTLINES_PATH}"
          fill="none"
          stroke="${colors.text}"
          stroke-opacity="0.52"
          stroke-width="0.52"
          vector-effect="non-scaling-stroke"
        />
      </svg>
    `;

    const blob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    try {
      const image = await new Promise<HTMLImageElement>((resolve, reject) => {
        const nextImage = new Image();
        nextImage.onload = () => resolve(nextImage);
        nextImage.onerror = () => reject(new Error('Unable to render world texture.'));
        nextImage.src = url;
      });

      const textureCanvas = document.createElement('canvas');
      textureCanvas.width = textureWidth;
      textureCanvas.height = textureHeight;
      const context = textureCanvas.getContext('2d', { alpha: true });
      if (!context) throw new Error('Unable to create world texture canvas.');

      context.clearRect(0, 0, textureWidth, textureHeight);
      context.drawImage(image, 0, 0, textureWidth, textureHeight);

      const texture = new THREE.CanvasTexture(textureCanvas);
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
      texture.minFilter = THREE.LinearMipmapLinearFilter;
      texture.magFilter = THREE.LinearFilter;
      texture.generateMipmaps = true;
      texture.needsUpdate = true;
      return texture;
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  function readableTime(value: string | null) {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.valueOf())) return '';
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    }).format(date);
  }

  onMount(() => {
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
    camera.position.set(0, 0, INITIAL_CAMERA_Z);

    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2.5));
    renderer.outputColorSpace = THREE.SRGBColorSpace;

    const globeGroup = new THREE.Group();
    globeGroup.rotation.set(-0.12, -0.58, 0);
    scene.add(globeGroup);

    // A nearly invisible depth-only sphere keeps the back hemisphere hidden
    // while leaving the ocean visually clear.
    const depthGeometry = new THREE.SphereGeometry(GLOBE_RADIUS - 0.012, 160, 112);
    const depthMaterial = new THREE.MeshBasicMaterial({
      colorWrite: false,
      depthWrite: true,
      side: THREE.FrontSide,
    });
    const depthSphere = new THREE.Mesh(depthGeometry, depthMaterial);
    depthSphere.renderOrder = -2;
    globeGroup.add(depthSphere);

    // The visible globe is only the same flat map artwork used by /stats:
    // transparent ocean, subtle land fill, coastline and country outlines.
    const globeGeometry = new THREE.SphereGeometry(GLOBE_RADIUS, 192, 128);
    const globeMaterial = new THREE.MeshBasicMaterial({
      transparent: true,
      alphaTest: 0.01,
      depthWrite: false,
      side: THREE.FrontSide,
    });
    const globe = new THREE.Mesh(globeGeometry, globeMaterial);
    globe.renderOrder = -1;
    globeGroup.add(globe);

    const markerGeometry = new THREE.CircleGeometry(0.045, 24);
    const markerOutlineGeometry = new THREE.CircleGeometry(0.059, 24);
    let markerMaterial = new THREE.MeshBasicMaterial({
      color: readThemeColors().accent,
      side: THREE.DoubleSide,
    });
    let markerOutlineMaterial = new THREE.MeshBasicMaterial({
      color: readThemeColors().background,
      side: THREE.DoubleSide,
    });
    let markerMesh: THREE.InstancedMesh | null = null;
    let markerOutlineMesh: THREE.InstancedMesh | null = null;
    let markerMetadata: GlobeMarker[] = [];
    let markerPositions: THREE.Vector3[] = [];
    let markerQuaternions: THREE.Quaternion[] = [];
    let markerBaseScales: number[] = [];
    let lastMarkerCameraZ = Number.NaN;

    const raycaster = new THREE.Raycaster();
    const pointerNdc = new THREE.Vector2();
    const activePointers = new Map<number, PointerPoint>();
    let previousPointer: PointerPoint | null = null;
    let pinchState: PinchState | null = null;
    let dragging = false;
    let targetCameraZ = INITIAL_CAMERA_Z;
    let velocityX = 0;
    let velocityY = 0;
    let disposed = false;
    let currentTexture: THREE.Texture | null = null;

    function disposeMarkerMesh() {
      if (markerMesh) {
        globeGroup.remove(markerMesh);
        markerMesh = null;
      }
      if (markerOutlineMesh) {
        globeGroup.remove(markerOutlineMesh);
        markerOutlineMesh = null;
      }
      markerPositions = [];
      markerQuaternions = [];
      markerBaseScales = [];
      lastMarkerCameraZ = Number.NaN;
    }

    function markerZoomCompensation(cameraZ: number) {
      // Keep dots visually small while zooming toward the globe. The marker
      // radius shrinks with the camera-to-surface distance, approximately
      // cancelling perspective magnification near the visible hemisphere.
      const initialSurfaceDistance = INITIAL_CAMERA_Z - MARKER_RADIUS;
      const currentSurfaceDistance = Math.max(0.2, cameraZ - MARKER_RADIUS);
      return clamp(currentSurfaceDistance / initialSurfaceDistance, 0.16, 1);
    }

    function updateMarkerMatrices(cameraZ: number, force = false) {
      if (!markerMesh || !markerOutlineMesh || markerMetadata.length === 0) return;
      if (!force && Number.isFinite(lastMarkerCameraZ) && Math.abs(cameraZ - lastMarkerCameraZ) < 0.001) return;

      lastMarkerCameraZ = cameraZ;
      const zoomScale = markerZoomCompensation(cameraZ);
      const dummy = new THREE.Object3D();
      const outward = new THREE.Vector3();

      markerMetadata.forEach((_, index) => {
        const position = markerPositions[index];
        const quaternion = markerQuaternions[index];
        const scale = markerBaseScales[index] * zoomScale;
        if (!position || !quaternion || !Number.isFinite(scale)) return;

        outward.copy(position).normalize();
        dummy.position.copy(position);
        dummy.quaternion.copy(quaternion);
        dummy.scale.setScalar(scale);
        dummy.updateMatrix();
        markerOutlineMesh?.setMatrixAt(index, dummy.matrix);

        // Lift the accent circle a fraction above its background ring to avoid
        // z-fighting while preserving the 2D map's bordered-dot appearance.
        dummy.position.copy(position).addScaledVector(outward, 0.0025);
        dummy.updateMatrix();
        markerMesh?.setMatrixAt(index, dummy.matrix);
      });

      markerOutlineMesh.instanceMatrix.needsUpdate = true;
      markerMesh.instanceMatrix.needsUpdate = true;
    }

    function setMarkers(locations: VisitorLocation[]) {
      markerMetadata = groupLocations(locations);
      disposeMarkerMesh();

      if (markerMetadata.length === 0) return;

      markerOutlineMesh = new THREE.InstancedMesh(
        markerOutlineGeometry,
        markerOutlineMaterial,
        markerMetadata.length,
      );
      markerOutlineMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      markerOutlineMesh.userData.kind = 'visitor-marker-outlines';

      markerMesh = new THREE.InstancedMesh(
        markerGeometry,
        markerMaterial,
        markerMetadata.length,
      );
      markerMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      markerMesh.userData.kind = 'visitor-markers';

      const circleNormal = new THREE.Vector3(0, 0, 1);

      markerPositions = markerMetadata.map((marker) =>
        markerPosition(marker.latitude, marker.longitude, MARKER_RADIUS),
      );
      markerQuaternions = markerPositions.map((position) =>
        new THREE.Quaternion().setFromUnitVectors(
          circleNormal,
          position.clone().normalize(),
        ),
      );
      markerBaseScales = markerMetadata.map(
        (marker) => 0.72 + Math.min(1.35, Math.log2(marker.count + 1) * 0.24),
      );

      globeGroup.add(markerOutlineMesh);
      globeGroup.add(markerMesh);
      updateMarkerMatrices(camera.position.z, true);
    }

    async function updateTheme() {
      try {
        const nextTexture = await makeWorldTexture(renderer);
        if (disposed) {
          nextTexture.dispose();
          return;
        }

        currentTexture?.dispose();
        currentTexture = nextTexture;
        globeMaterial.map = nextTexture;
        globeMaterial.needsUpdate = true;

        const colors = readThemeColors();
        markerMaterial.color.set(colors.accent);
        markerOutlineMaterial.color.set(colors.background);
      } catch (textureError) {
        console.error(textureError);
      }
    }

    async function loadStats() {
      const base = apiBase.trim().replace(/\/$/, '');
      if (!base) {
        loading = false;
        error = 'Live analytics are not configured.';
        return;
      }

      try {
        const response = await fetch(`${base}/api/stats?days=30`, {
          headers: { Accept: 'application/json' },
          cache: 'no-store',
        });
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);

        const data = (await response.json()) as LiveStats;
        if (disposed) return;
        visitorCount = data.summary.estimatedVisitors ?? data.locations.length;
        updatedAt = data.summary.updatedAt;
        setMarkers(data.locations ?? []);
        error = '';
      } catch (statsError) {
        if (disposed) return;
        error = `Visitor data unavailable${
          statsError instanceof Error ? `: ${statsError.message}` : '.'
        }`;
      } finally {
        if (!disposed) loading = false;
      }
    }

    function resize() {
      const bounds = shell.getBoundingClientRect();
      const width = Math.max(1, bounds.width);
      const height = Math.max(1, bounds.height);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    }

    function pointerDistance() {
      const points = [...activePointers.values()];
      if (points.length < 2) return 0;
      return Math.hypot(points[1].x - points[0].x, points[1].y - points[0].y);
    }

    function beginPinch() {
      const distance = pointerDistance();
      if (distance <= 0) return;
      pinchState = { distance, cameraZ: targetCameraZ };
      previousPointer = null;
      dragging = false;
      velocityX = 0;
      velocityY = 0;
    }

    function onPointerDown(event: PointerEvent) {
      canvas.setPointerCapture(event.pointerId);
      activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      tooltipVisible = false;

      if (activePointers.size >= 2) {
        beginPinch();
        return;
      }

      dragging = true;
      previousPointer = { x: event.clientX, y: event.clientY };
      velocityX = 0;
      velocityY = 0;
    }

    function onPointerMove(event: PointerEvent) {
      if (activePointers.has(event.pointerId)) {
        activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      }

      if (activePointers.size >= 2 && pinchState) {
        const distance = pointerDistance();
        if (distance > 0) {
          targetCameraZ = clamp(
            pinchState.cameraZ * (pinchState.distance / distance),
            MIN_CAMERA_Z,
            MAX_CAMERA_Z,
          );
        }
        return;
      }

      if (dragging && previousPointer && activePointers.size === 1) {
        const dx = event.clientX - previousPointer.x;
        const dy = event.clientY - previousPointer.y;
        globeGroup.rotation.y += dx * 0.0062;
        globeGroup.rotation.x += dy * 0.0047;
        velocityY = dx * 0.0013;
        velocityX = dy * 0.00095;
        previousPointer = { x: event.clientX, y: event.clientY };
        return;
      }

      if (event.buttons === 0 && markerMesh) {
        const bounds = canvas.getBoundingClientRect();
        pointerNdc.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
        pointerNdc.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
        raycaster.setFromCamera(pointerNdc, camera);
        const intersection = raycaster.intersectObject(markerMesh, false)[0];
        const instanceId = intersection?.instanceId;

        if (typeof instanceId === 'number' && markerMetadata[instanceId]) {
          const marker = markerMetadata[instanceId];
          tooltipText = `${marker.label}${marker.count > 1 ? ` · ${marker.count} visitors` : ''}`;
          tooltipX = event.clientX - bounds.left;
          tooltipY = event.clientY - bounds.top;
          tooltipVisible = true;
          canvas.style.cursor = 'pointer';
        } else {
          tooltipVisible = false;
          canvas.style.cursor = 'grab';
        }
      }
    }

    function onPointerUp(event: PointerEvent) {
      activePointers.delete(event.pointerId);
      if (canvas.hasPointerCapture(event.pointerId)) {
        canvas.releasePointerCapture(event.pointerId);
      }

      if (activePointers.size >= 2) {
        beginPinch();
        return;
      }

      pinchState = null;
      if (activePointers.size === 1) {
        const point = [...activePointers.values()][0];
        dragging = true;
        previousPointer = { ...point };
      } else {
        dragging = false;
        previousPointer = null;
      }
    }

    function onWheel(event: WheelEvent) {
      event.preventDefault();
      targetCameraZ = clamp(
        targetCameraZ + event.deltaY * 0.006,
        MIN_CAMERA_Z,
        MAX_CAMERA_Z,
      );
      tooltipVisible = false;
    }

    function onPointerLeave() {
      if (activePointers.size === 0) tooltipVisible = false;
    }

    resetGlobe = () => {
      globeGroup.rotation.set(-0.12, -0.58, 0);
      targetCameraZ = INITIAL_CAMERA_Z;
      velocityX = 0;
      velocityY = 0;
      tooltipVisible = false;
    };

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(shell);
    resize();

    canvas.addEventListener('pointerdown', onPointerDown);
    canvas.addEventListener('pointermove', onPointerMove);
    canvas.addEventListener('pointerup', onPointerUp);
    canvas.addEventListener('pointercancel', onPointerUp);
    canvas.addEventListener('pointerleave', onPointerLeave);
    canvas.addEventListener('wheel', onWheel, { passive: false });

    const themeObserver = new MutationObserver((records) => {
      if (records.some((record) => record.attributeName === 'data-theme')) {
        void updateTheme();
      }
    });
    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    });

    void updateTheme();
    void loadStats();
    const statsInterval = window.setInterval(() => void loadStats(), 15_000);

    let frameId = 0;
    const animate = () => {
      if (disposed) return;

      if (!dragging && activePointers.size === 0) {
        globeGroup.rotation.y += velocityY;
        globeGroup.rotation.x += velocityX;
        velocityX *= 0.94;
        velocityY *= 0.94;
      }

      camera.position.z += (targetCameraZ - camera.position.z) * 0.13;
      updateMarkerMatrices(camera.position.z);
      renderer.render(scene, camera);
      frameId = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      disposed = true;
      resetGlobe = null;
      window.clearInterval(statsInterval);
      cancelAnimationFrame(frameId);
      resizeObserver.disconnect();
      themeObserver.disconnect();
      canvas.removeEventListener('pointerdown', onPointerDown);
      canvas.removeEventListener('pointermove', onPointerMove);
      canvas.removeEventListener('pointerup', onPointerUp);
      canvas.removeEventListener('pointercancel', onPointerUp);
      canvas.removeEventListener('pointerleave', onPointerLeave);
      canvas.removeEventListener('wheel', onWheel);
      disposeMarkerMesh();
      markerGeometry.dispose();
      markerOutlineGeometry.dispose();
      markerMaterial.dispose();
      markerOutlineMaterial.dispose();
      currentTexture?.dispose();
      globeGeometry.dispose();
      globeMaterial.dispose();
      depthGeometry.dispose();
      depthMaterial.dispose();
      renderer.dispose();
    };
  });
</script>

<div class="globe-shell" bind:this={shell}>
  <canvas
    bind:this={canvas}
    class="globe-canvas"
    role="img"
    aria-label="Interactive clear three-dimensional globe showing approximate website visitor locations. Drag freely to rotate and scroll or pinch to zoom."
  ></canvas>

  <div class="globe-meta" aria-live="polite">
    <strong>Visitor globe</strong>
    <span>
      {#if loading}
        Loading locations…
      {:else if error}
        {error}
      {:else}
        {visitorCount.toLocaleString('en-US')} visitors{updatedAt ? ` · ${readableTime(updatedAt)}` : ''}
      {/if}
    </span>
  </div>

  <div class="globe-help">Drag freely to rotate · scroll or pinch to zoom</div>

  <button
    class="globe-reset"
    type="button"
    aria-label="Reset globe view"
    on:click={() => resetGlobe?.()}
  >Reset</button>

  {#if tooltipVisible}
    <div
      class="globe-tooltip"
      style={`left:${tooltipX}px;top:${tooltipY}px;`}
      aria-hidden="true"
    >{tooltipText}</div>
  {/if}
</div>

<style>
  .globe-shell {
    position: relative;
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    background: var(--bg);
  }

  .globe-canvas {
    display: block;
    width: 100%;
    height: 100%;
    cursor: grab;
    touch-action: none;
    user-select: none;
  }

  .globe-canvas:active {
    cursor: grabbing;
  }

  .globe-meta,
  .globe-help,
  .globe-reset,
  .globe-tooltip {
    position: absolute;
    z-index: 2;
  }

  .globe-meta {
    top: clamp(1rem, 2.4vw, 1.5rem);
    left: clamp(1rem, 2.4vw, 1.5rem);
    display: grid;
    gap: 0.22rem;
    pointer-events: none;
  }

  .globe-meta strong {
    color: var(--text);
    font-family: var(--font-display);
    font-size: 1.05rem;
    font-weight: 400;
  }

  .globe-meta span,
  .globe-help {
    color: var(--muted);
    font-size: 0.74rem;
    line-height: 1.35;
  }

  .globe-help {
    bottom: clamp(1rem, 2.4vw, 1.5rem);
    left: 50%;
    padding: 0.38rem 0.55rem;
    border: 1px solid var(--line);
    background: color-mix(in srgb, var(--bg) 82%, transparent);
    transform: translateX(-50%);
    pointer-events: none;
    white-space: nowrap;
    backdrop-filter: blur(8px);
  }

  .globe-reset {
    top: clamp(1rem, 2.4vw, 1.5rem);
    right: clamp(1rem, 2.4vw, 1.5rem);
    appearance: none;
    padding: 0.42rem 0.62rem;
    border: 1px solid var(--line);
    background: color-mix(in srgb, var(--bg) 88%, transparent);
    color: var(--text);
    font: inherit;
    font-size: 0.75rem;
    cursor: pointer;
    backdrop-filter: blur(8px);
  }

  .globe-reset:hover {
    border-color: var(--text);
  }

  .globe-tooltip {
    max-width: min(17rem, calc(100% - 2rem));
    padding: 0.38rem 0.5rem;
    border: 1px solid var(--line);
    background: var(--bg);
    color: var(--text);
    font-size: 0.72rem;
    line-height: 1.35;
    transform: translate(0.7rem, calc(-100% - 0.7rem));
    pointer-events: none;
  }

  @media (max-width: 560px) {
    .globe-help {
      bottom: 0.8rem;
      font-size: 0.68rem;
    }

    .globe-meta {
      max-width: calc(100% - 7rem);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .globe-canvas {
      scroll-behavior: auto;
    }
  }
</style>
