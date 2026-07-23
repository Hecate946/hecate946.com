<script lang="ts">
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
  }

  interface ProjectedVisitorLocation extends VisitorLocation {
    x: number;
    y: number;
  }

  export let locations: VisitorLocation[] = [];
  export let totalVisitors = 0;

  const WIDTH = 1000;
  const HEIGHT = 500;
  const MIN_ZOOM = 1;
  const MAX_ZOOM = 12;

  let mapElement!: SVGSVGElement;
  let projectedLocations: ProjectedVisitorLocation[] = [];
  let locationSignature = '';
  let visitorScaleBucket = 0;
  let transform = '';
  let zoom = 1;
  let centerX = WIDTH / 2;
  let centerY = HEIGHT / 2;
  let dragging = false;
  let pointerId: number | null = null;
  let previousPointer = { x: 0, y: 0 };
  let fittedSignature = '';

  $: projectedLocations = locations
    .filter(
      (location) =>
        Number.isFinite(location.latitude) &&
        Number.isFinite(location.longitude),
    )
    .map((location) => ({
      ...location,
      x: ((location.longitude + 180) / 360) * WIDTH,
      y: ((90 - location.latitude) / 180) * HEIGHT,
    }));

  $: visitorScaleBucket = Math.floor(
    Math.log2(Math.max(1, totalVisitors)),
  );

  $: locationSignature = `${projectedLocations
    .map((location) => `${location.latitude}:${location.longitude}`)
    .sort()
    .join('|')}|visitors:${visitorScaleBucket}`;

  $: if (locationSignature !== fittedSignature) {
    fittedSignature = locationSignature;
    fitLocations();
  }

  $: transform = `translate(${WIDTH / 2} ${HEIGHT / 2}) scale(${zoom}) translate(${-centerX} ${-centerY})`;

  function clamp(value: number, minimum: number, maximum: number) {
    return Math.min(maximum, Math.max(minimum, value));
  }

  function fitLocations() {
    if (projectedLocations.length === 0) {
      zoom = 1;
      centerX = WIDTH / 2;
      centerY = HEIGHT / 2;
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
      return;
    }

    const xs = projectedLocations.map((location) => location.x);
    const ys = projectedLocations.map((location) => location.y);
    const minimumX = Math.min(...xs);
    const maximumX = Math.max(...xs);
    const minimumY = Math.min(...ys);
    const maximumY = Math.max(...ys);
    const spanX = Math.max(80, maximumX - minimumX);
    const spanY = Math.max(45, maximumY - minimumY);
    const padding = 110;

    zoom = clamp(
      Math.min(
        (WIDTH - padding * 2) / spanX,
        (HEIGHT - padding * 2) / spanY,
        visitorZoomCap,
      ),
      MIN_ZOOM,
      6,
    );
    centerX = (minimumX + maximumX) / 2;
    centerY = (minimumY + maximumY) / 2;
  }

  function viewBoxPoint(clientX: number, clientY: number) {
    const bounds = mapElement.getBoundingClientRect();

    return {
      x: ((clientX - bounds.left) / bounds.width) * WIDTH,
      y: ((clientY - bounds.top) / bounds.height) * HEIGHT,
    };
  }

  function zoomAt(nextZoom: number, anchorX = WIDTH / 2, anchorY = HEIGHT / 2) {
    const clampedZoom = clamp(nextZoom, MIN_ZOOM, MAX_ZOOM);
    const worldX = centerX + (anchorX - WIDTH / 2) / zoom;
    const worldY = centerY + (anchorY - HEIGHT / 2) / zoom;

    centerX = worldX - (anchorX - WIDTH / 2) / clampedZoom;
    centerY = worldY - (anchorY - HEIGHT / 2) / clampedZoom;
    zoom = clampedZoom;
  }

  function handleWheel(event: WheelEvent) {
    const point = viewBoxPoint(event.clientX, event.clientY);
    const factor = Math.exp(-event.deltaY * 0.0014);
    zoomAt(zoom * factor, point.x, point.y);
  }

  function handlePointerDown(event: PointerEvent) {
    pointerId = event.pointerId;
    dragging = true;
    previousPointer = viewBoxPoint(event.clientX, event.clientY);
    mapElement.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event: PointerEvent) {
    if (!dragging || pointerId !== event.pointerId) return;

    const current = viewBoxPoint(event.clientX, event.clientY);
    centerX -= (current.x - previousPointer.x) / zoom;
    centerY -= (current.y - previousPointer.y) / zoom;
    previousPointer = current;
  }

  function endPointer(event: PointerEvent) {
    if (pointerId !== event.pointerId) return;

    dragging = false;
    pointerId = null;

    if (mapElement.hasPointerCapture(event.pointerId)) {
      mapElement.releasePointerCapture(event.pointerId);
    }
  }

  function dotRadius(pageViews: number) {
    const visualRadius = 4.5 + Math.min(6, Math.log2(pageViews + 1) * 1.15);
    return visualRadius / zoom;
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
    data-dragging={dragging}
    viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
    role="img"
    aria-label="Zoomable map of aggregated website visitor locations"
    tabindex="0"
    on:wheel|preventDefault={handleWheel}
    on:pointerdown={handlePointerDown}
    on:pointermove={handlePointerMove}
    on:pointerup={endPointer}
    on:pointercancel={endPointer}
  >
    <g {transform}>
      <path class="map-land" d={WORLD_MAP_PATH} />

      {#each projectedLocations as location}
        <circle
          class="map-dot"
          cx={location.x}
          cy={location.y}
          r={dotRadius(location.pageViews)}
        >
          <title>
            {locationName(location) || 'Approximate location'} — {location.estimatedVisitors.toLocaleString()} estimated visitor{location.estimatedVisitors === 1 ? '' : 's'}, {location.pageViews.toLocaleString()} page view{location.pageViews === 1 ? '' : 's'}
          </title>
        </circle>
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
