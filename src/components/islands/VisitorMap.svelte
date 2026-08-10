<script lang="ts">
  import { onMount } from 'svelte';
  import { WORLD_MAP_PATH } from '@/data/world-map';
  import { WORLD_INTERNAL_BORDERS_PATH } from '@/data/world-internal-borders';

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

  interface ProjectedVisitorLocation extends VisitorLocation {
    x: number;
    y: number;
    count: number;
    label: string;
  }

  interface Point {
    x: number;
    y: number;
  }

  interface PinchState {
    distance: number;
    zoom: number;
    worldX: number;
    worldY: number;
  }

  export let locations: VisitorLocation[] = [];
  export let totalVisitors = 0;

  const WIDTH = 1000;
  const HEIGHT = 500;
  const MIN_ZOOM = 1;
  const MAX_ZOOM = 12;
  const WORLD_COPIES = [-1, 0, 1] as const;
  // Marker sizes are expressed in CSS pixels, then converted back into map
  // units so the SVG camera transform does not make them balloon. World view
  // deliberately uses larger lights; close zoom resolves them into small points.
  const LIGHT_CORE_CLOSE_PX = 3.2;
  const LIGHT_CORE_FAR_PX = 7.6;
  const LIGHT_GLOW_CLOSE_PX = 8.4;
  const LIGHT_GLOW_FAR_PX = 21.5;
  const LIGHT_BLOOM_CLOSE_PX = 13;
  const LIGHT_BLOOM_FAR_PX = 31;

  let mapElement!: SVGSVGElement;
  let projectedLocations: ProjectedVisitorLocation[] = [];
  let locationSignature = '';
  let visitorScaleBucket = 0;
  let transform = '';
  let zoom = 1;
  let centerX = WIDTH / 2;
  let centerY = HEIGHT / 2;
  let visibleWidthAtZoomOne = WIDTH;
  let visibleHeightAtZoomOne = HEIGHT;
  let viewUnitsPerCssPixel = 1;
  let dragging = false;
  let pinching = false;
  let previousPointer: Point | null = null;
  let pinchState: PinchState | null = null;
  let fittedSignature = '';

  const activePointers = new Map<number, Point>();

  $: projectedLocations = groupLocations(locations).map((location) => ({
    ...location,
    x: wrapX(((location.longitude + 180) / 360) * WIDTH),
    y: ((90 - location.latitude) / 180) * HEIGHT,
  }));

  $: visitorScaleBucket = Math.floor(
    Math.log2(Math.max(1, totalVisitors)),
  );

  $: locationSignature = `${projectedLocations
    .map(
      (location) =>
        `${location.latitude}:${location.longitude}:${location.count}`,
    )
    .sort()
    .join('|')}|visitors:${visitorScaleBucket}`;

  $: if (locationSignature !== fittedSignature) {
    fittedSignature = locationSignature;
    fitLocations();
  }

  $: transform = `translate(${WIDTH / 2} ${HEIGHT / 2}) scale(${zoom}) translate(${-centerX} ${-centerY})`;

  onMount(() => {
    updateVisibleDimensions();
    fitLocations();

    const observer = new ResizeObserver(() => {
      updateVisibleDimensions();
      constrainCamera();
    });

    observer.observe(mapElement);
    return () => observer.disconnect();
  });

  function clamp(value: number, minimum: number, maximum: number) {
    return Math.min(maximum, Math.max(minimum, value));
  }

  function wrapX(value: number) {
    return ((value % WIDTH) + WIDTH) % WIDTH;
  }

  function locationLabel(location: VisitorLocation) {
    return [location.city, location.region, location.country]
      .filter(Boolean)
      .join(', ') || 'Approximate visitor location';
  }

  function groupLocations(values: VisitorLocation[]) {
    const groups = new Map<string, ProjectedVisitorLocation>();

    for (const location of values) {
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
        ...location,
        x: 0,
        y: 0,
        count: 1,
        label: locationLabel(location),
      });
    }

    return [...groups.values()];
  }

  function updateVisibleDimensions() {
    if (!mapElement) return;

    const bounds = mapElement.getBoundingClientRect();
    if (bounds.width <= 0 || bounds.height <= 0) return;

    const aspect = bounds.width / bounds.height;
    viewUnitsPerCssPixel = WIDTH / bounds.width;

    // The SVG uses xMidYMid slice. These are the world dimensions visible at 1×.
    visibleWidthAtZoomOne = Math.min(WIDTH, HEIGHT * aspect);
    visibleHeightAtZoomOne = Math.min(HEIGHT, WIDTH / aspect);
  }

  function constrainCamera() {
    centerX = wrapX(centerX);

    const halfVisibleHeight = visibleHeightAtZoomOne / (2 * zoom);
    centerY = clamp(
      centerY,
      halfVisibleHeight,
      HEIGHT - halfVisibleHeight,
    );
  }

  function circularHorizontalBounds(xs: number[]) {
    const sorted = xs.map(wrapX).sort((a, b) => a - b);

    if (sorted.length === 1) {
      return { center: sorted[0], span: 0 };
    }

    let largestGap = -1;
    let gapAfterIndex = 0;

    for (let index = 0; index < sorted.length; index += 1) {
      const current = sorted[index];
      const next =
        index === sorted.length - 1 ? sorted[0] + WIDTH : sorted[index + 1];
      const gap = next - current;

      if (gap > largestGap) {
        largestGap = gap;
        gapAfterIndex = index;
      }
    }

    const startIndex = (gapAfterIndex + 1) % sorted.length;
    const start = sorted[startIndex];
    const span = WIDTH - largestGap;

    return {
      center: wrapX(start + span / 2),
      span,
    };
  }

  function fitLocations() {
    if (projectedLocations.length === 0) {
      zoom = 1;
      centerX = WIDTH / 2;
      centerY = HEIGHT / 2;
      constrainCamera();
      return;
    }

    const visitorZoomCap = clamp(
      5.2 - Math.log2(totalVisitors + 1) * 0.22,
      1.25,
      5.2,
    );

    if (projectedLocations.length === 1) {
      zoom = Math.min(4.5, visitorZoomCap);
      centerX = projectedLocations[0].x;
      centerY = projectedLocations[0].y;
      constrainCamera();
      return;
    }

    const horizontal = circularHorizontalBounds(
      projectedLocations.map((location) => location.x),
    );
    const ys = projectedLocations.map((location) => location.y);
    const minimumY = Math.min(...ys);
    const maximumY = Math.max(...ys);
    const spanX = Math.max(80, horizontal.span);
    const spanY = Math.max(45, maximumY - minimumY);
    const padding = 110;

    zoom = clamp(
      Math.min(
        Math.max(1, visibleWidthAtZoomOne - padding * 2) / spanX,
        Math.max(1, visibleHeightAtZoomOne - padding * 2) / spanY,
        visitorZoomCap,
      ),
      MIN_ZOOM,
      6,
    );
    centerX = horizontal.center;
    centerY = (minimumY + maximumY) / 2;
    constrainCamera();
  }

  function viewBoxPoint(clientX: number, clientY: number): Point {
    const point = mapElement.createSVGPoint();
    point.x = clientX;
    point.y = clientY;

    const matrix = mapElement.getScreenCTM();
    if (!matrix) return { x: WIDTH / 2, y: HEIGHT / 2 };

    const transformed = point.matrixTransform(matrix.inverse());
    return { x: transformed.x, y: transformed.y };
  }

  function zoomAt(nextZoom: number, anchorX = WIDTH / 2, anchorY = HEIGHT / 2) {
    const clampedZoom = clamp(nextZoom, MIN_ZOOM, MAX_ZOOM);
    const worldX = centerX + (anchorX - WIDTH / 2) / zoom;
    const worldY = centerY + (anchorY - HEIGHT / 2) / zoom;

    centerX = worldX - (anchorX - WIDTH / 2) / clampedZoom;
    centerY = worldY - (anchorY - HEIGHT / 2) / clampedZoom;
    zoom = clampedZoom;
    constrainCamera();
  }

  function handleWheel(event: WheelEvent) {
    const point = viewBoxPoint(event.clientX, event.clientY);
    const factor = Math.exp(-event.deltaY * 0.0014);
    zoomAt(zoom * factor, point.x, point.y);
  }

  function pointerPair() {
    return Array.from(activePointers.values()).slice(0, 2);
  }

  function distanceBetween(first: Point, second: Point) {
    return Math.hypot(second.x - first.x, second.y - first.y);
  }

  function midpoint(first: Point, second: Point): Point {
    return {
      x: (first.x + second.x) / 2,
      y: (first.y + second.y) / 2,
    };
  }

  function beginPinch() {
    const [first, second] = pointerPair();
    if (!first || !second) return;

    const middle = midpoint(first, second);
    const distance = Math.max(1, distanceBetween(first, second));

    pinchState = {
      distance,
      zoom,
      worldX: centerX + (middle.x - WIDTH / 2) / zoom,
      worldY: centerY + (middle.y - HEIGHT / 2) / zoom,
    };

    pinching = true;
    dragging = false;
    previousPointer = null;
  }

  function updatePinch() {
    const [first, second] = pointerPair();
    if (!first || !second || !pinchState) return;

    const middle = midpoint(first, second);
    const distance = Math.max(1, distanceBetween(first, second));
    const nextZoom = clamp(
      pinchState.zoom * (distance / pinchState.distance),
      MIN_ZOOM,
      MAX_ZOOM,
    );

    zoom = nextZoom;
    centerX =
      pinchState.worldX - (middle.x - WIDTH / 2) / nextZoom;
    centerY =
      pinchState.worldY - (middle.y - HEIGHT / 2) / nextZoom;
    constrainCamera();
  }

  function handlePointerDown(event: PointerEvent) {
    if (event.pointerType === 'mouse' && event.button !== 0) return;

    event.preventDefault();
    activePointers.set(
      event.pointerId,
      viewBoxPoint(event.clientX, event.clientY),
    );

    try {
      mapElement.setPointerCapture(event.pointerId);
    } catch {
      // Pointer capture is an enhancement; interaction still works without it.
    }

    if (activePointers.size >= 2) {
      beginPinch();
      return;
    }

    dragging = true;
    pinching = false;
    pinchState = null;
    previousPointer = activePointers.get(event.pointerId) ?? null;
  }

  function handlePointerMove(event: PointerEvent) {
    if (!activePointers.has(event.pointerId)) return;

    const current = viewBoxPoint(event.clientX, event.clientY);
    activePointers.set(event.pointerId, current);

    if (activePointers.size >= 2) {
      if (!pinchState) beginPinch();
      updatePinch();
      return;
    }

    if (!dragging || !previousPointer) return;

    centerX -= (current.x - previousPointer.x) / zoom;
    centerY -= (current.y - previousPointer.y) / zoom;
    previousPointer = current;
    constrainCamera();
  }

  function endPointer(event: PointerEvent) {
    activePointers.delete(event.pointerId);

    if (mapElement.hasPointerCapture(event.pointerId)) {
      mapElement.releasePointerCapture(event.pointerId);
    }

    if (activePointers.size >= 2) {
      beginPinch();
      return;
    }

    pinchState = null;
    pinching = false;

    if (activePointers.size === 1) {
      dragging = true;
      previousPointer = Array.from(activePointers.values())[0] ?? null;
      return;
    }

    dragging = false;
    previousPointer = null;
  }

  function lightZoomProgress() {
    // Map zoom is multiplicative, so interpolate marker size logarithmically too.
    // This makes 1→2→4→8× produce equally natural visual steps instead of most
    // of the size change being delayed until the extreme end of the zoom range.
    const raw = clamp(
      Math.log(zoom / MIN_ZOOM) / Math.log(MAX_ZOOM / MIN_ZOOM),
      0,
      1,
    );
    return raw * raw * (3 - 2 * raw);
  }

  function lightScale(count: number) {
    const densityBoost = Math.min(0.62, Math.log2(Math.max(1, count)) * 0.17);
    // Coalesced lights communicate density most strongly at world scale, then
    // become less exaggerated as the user zooms in and geography provides context.
    return 1 + densityBoost * (1 - lightZoomProgress() * 0.32);
  }

  function lightDiameter(closePx: number, farPx: number) {
    const progress = lightZoomProgress();
    return farPx + (closePx - farPx) * progress;
  }

  function lightRadius(closePx: number, farPx: number, count: number) {
    const diameterPx = lightDiameter(closePx, farPx) * lightScale(count);
    return (diameterPx * 0.5 * viewUnitsPerCssPixel) / zoom;
  }
</script>

<div class="visitor-map-shell">
  <svg
    bind:this={mapElement}
    class="visitor-map"
    data-dragging={dragging || pinching}
    viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
    preserveAspectRatio="xMidYMid slice"
    role="img"
    aria-label="Zoomable, horizontally wrapping map of approximate visitor lights"
    on:wheel|preventDefault={handleWheel}
    on:pointerdown={handlePointerDown}
    on:pointermove={handlePointerMove}
    on:pointerup={endPointer}
    on:pointercancel={endPointer}
  >
    <defs>
      <!-- Every layer derives from the active theme accent. The core is only
           slightly "hotter" toward white; hue and halo remain the accent itself. -->
      <radialGradient id="visitor-light-core" cx="50%" cy="50%" r="50%">
        <stop
          offset="0%"
          style="stop-color:color-mix(in srgb, var(--accent-strong) 72%, white 28%);stop-opacity:1"
        />
        <stop
          offset="34%"
          style="stop-color:color-mix(in srgb, var(--accent-strong) 88%, white 12%);stop-opacity:1"
        />
        <stop offset="66%" stop-color="var(--accent-strong)" stop-opacity="0.94" />
        <stop offset="86%" stop-color="var(--accent-strong)" stop-opacity="0.52" />
        <stop offset="100%" stop-color="var(--accent-strong)" stop-opacity="0" />
      </radialGradient>
      <radialGradient id="visitor-light-glow" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="var(--accent-strong)" stop-opacity="0.36" />
        <stop offset="28%" stop-color="var(--accent-strong)" stop-opacity="0.24" />
        <stop offset="58%" stop-color="var(--accent-strong)" stop-opacity="0.10" />
        <stop offset="82%" stop-color="var(--accent-strong)" stop-opacity="0.035" />
        <stop offset="100%" stop-color="var(--accent-strong)" stop-opacity="0" />
      </radialGradient>
      <radialGradient id="visitor-light-bloom" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="var(--accent-strong)" stop-opacity="0.12" />
        <stop offset="36%" stop-color="var(--accent-strong)" stop-opacity="0.07" />
        <stop offset="70%" stop-color="var(--accent-strong)" stop-opacity="0.025" />
        <stop offset="100%" stop-color="var(--accent-strong)" stop-opacity="0" />
      </radialGradient>
    </defs>

    <g {transform}>
      {#each WORLD_COPIES as copy}
        <g transform={`translate(${copy * WIDTH} 0)`}>
          <path class="map-land" d={WORLD_MAP_PATH} />
          <path
            class="map-country-border"
            d={WORLD_INTERNAL_BORDERS_PATH}
          />

          {#each projectedLocations as location}
            <g class="map-light">
              <circle
                class="map-light-bloom"
                cx={location.x}
                cy={location.y}
                r={lightRadius(LIGHT_BLOOM_CLOSE_PX, LIGHT_BLOOM_FAR_PX, location.count)}
              />
              <circle
                class="map-light-glow"
                cx={location.x}
                cy={location.y}
                r={lightRadius(LIGHT_GLOW_CLOSE_PX, LIGHT_GLOW_FAR_PX, location.count)}
              />
              <circle
                class="map-light-core"
                cx={location.x}
                cy={location.y}
                r={lightRadius(LIGHT_CORE_CLOSE_PX, LIGHT_CORE_FAR_PX, location.count)}
              >
                <title>
                  {location.label} — {location.count === 1 ? '1 visitor' : `${location.count} visitors`}
                </title>
              </circle>
            </g>
          {/each}
        </g>
      {/each}
    </g>
  </svg>

  <div class="map-controls" aria-label="Map controls">
    <button type="button" aria-label="Zoom in" on:click={() => zoomAt(zoom * 1.5)}>
      +
    </button>
    <button type="button" aria-label="Zoom out" on:click={() => zoomAt(zoom / 1.5)}>
      −
    </button>
    <button type="button" on:click={fitLocations}>Fit</button>
  </div>
</div>
