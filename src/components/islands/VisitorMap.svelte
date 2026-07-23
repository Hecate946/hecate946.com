<script lang="ts">
  import { onMount } from 'svelte';
  import { WORLD_MAP_PATH } from '@/data/world-map';

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
    offsetX: number;
    offsetY: number;
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
  let dragging = false;
  let pinching = false;
  let previousPointer: Point | null = null;
  let pinchState: PinchState | null = null;
  let fittedSignature = '';

  const activePointers = new Map<number, Point>();

  $: projectedLocations = locations
    .filter(
      (location) =>
        Number.isFinite(location.latitude) &&
        Number.isFinite(location.longitude),
    )
    .map((location) => {
      const offset = separatePoint(
        location.pointIndex ?? 0,
        location.pointCount ?? 1,
      );

      return {
        ...location,
        x: wrapX(((location.longitude + 180) / 360) * WIDTH),
        y: ((90 - location.latitude) / 180) * HEIGHT,
        offsetX: offset.x,
        offsetY: offset.y,
      };
    });

  $: visitorScaleBucket = Math.floor(
    Math.log2(Math.max(1, totalVisitors)),
  );

  $: locationSignature = `${projectedLocations
    .map(
      (location) =>
        `${location.latitude}:${location.longitude}:${location.pointIndex ?? 0}:${location.pointCount ?? 1}`,
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

  function separatePoint(index: number, count: number): Point {
    if (count <= 1 || index <= 0) return { x: 0, y: 0 };

    // A deterministic sunflower pattern keeps individual visitors distinct
    // without exposing any more precise geographic information.
    const goldenAngle = Math.PI * (3 - Math.sqrt(5));
    const radius = 11.5 * Math.sqrt(index);
    const angle = index * goldenAngle;

    return {
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
    };
  }

  function updateVisibleDimensions() {
    if (!mapElement) return;

    const bounds = mapElement.getBoundingClientRect();
    if (bounds.width <= 0 || bounds.height <= 0) return;

    const aspect = bounds.width / bounds.height;

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

  function dotRadius() {
    return 4.75 / zoom;
  }

  function locationName(location: VisitorLocation) {
    return [location.city, location.region, location.country]
      .filter(Boolean)
      .join(', ');
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
    aria-label="Zoomable, horizontally wrapping map of individual anonymous visitor locations"
    tabindex="0"
    on:wheel|preventDefault={handleWheel}
    on:pointerdown={handlePointerDown}
    on:pointermove={handlePointerMove}
    on:pointerup={endPointer}
    on:pointercancel={endPointer}
  >
    <g {transform}>
      {#each WORLD_COPIES as copy}
        <g transform={`translate(${copy * WIDTH} 0)`}>
          <path class="map-land" d={WORLD_MAP_PATH} />

          {#each projectedLocations as location}
            <circle
              class="map-dot"
              cx={location.x + location.offsetX / zoom}
              cy={location.y + location.offsetY / zoom}
              r={dotRadius()}
            >
              <title>
                {locationName(location) || 'Approximate location'} — one anonymous visitor
              </title>
            </circle>
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
