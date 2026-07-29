<script lang="ts">
  import type { HouseDestination } from '@/config/house-scene';
  import WindowScene from './WindowScene.svelte';

  export let destination: HouseDestination;
  export let navigationEnabled = true;

  $: geometry = destination.geometry;
  $: clipId = `house-pane-clip-${destination.id}`;
  $: sceneWidth = destination.sceneViewBox?.width ?? 100;
  $: sceneHeight = destination.sceneViewBox?.height ?? 140;
  $: sceneFit = destination.sceneViewBox?.fit ?? 'meet';
  $: paneWidth =
    (geometry.width - geometry.mullionX * (geometry.columns - 1)) / geometry.columns;
  $: paneHeight =
    (geometry.height - geometry.mullionY * (geometry.rows - 1)) / geometry.rows;
  $: panes = Array.from({ length: geometry.columns * geometry.rows }, (_, index) => {
    const column = index % geometry.columns;
    const row = Math.floor(index / geometry.columns);

    return {
      x: geometry.x + column * (paneWidth + geometry.mullionX),
      y: geometry.y + row * (paneHeight + geometry.mullionY),
      width: paneWidth,
      height: paneHeight,
    };
  });
  $: labelY = geometry.y > 500 ? geometry.y - 27 : geometry.y + geometry.height + 29;

  function handleClick(event: MouseEvent) {
    if (!navigationEnabled) event.preventDefault();
  }
</script>

<defs>
  <clipPath id={clipId} clipPathUnits="userSpaceOnUse">
    {#each panes as pane}
      <rect x={pane.x} y={pane.y} width={pane.width} height={pane.height} rx="0.6" />
    {/each}
  </clipPath>
</defs>

<a
  class="house-window"
  href={destination.href}
  aria-label={`Open ${destination.roomLabel}: ${destination.description}`}
  aria-disabled={!navigationEnabled}
  data-house-window={destination.id}
  data-window-scene={destination.scene}
  onclick={handleClick}
>
  <g class="house-window__scene" clip-path={`url(#${clipId})`}>
    <svg
      x={geometry.x}
      y={geometry.y}
      width={geometry.width}
      height={geometry.height}
      viewBox={`0 0 ${sceneWidth} ${sceneHeight}`}
      preserveAspectRatio={`xMidYMid ${sceneFit}`}
      overflow="hidden"
    >
      <WindowScene scene={destination.scene} />
    </svg>

    <rect
      class="house-window__glass"
      x={geometry.x}
      y={geometry.y}
      width={geometry.width}
      height={geometry.height}
    />
  </g>

  <rect
    class="house-window__glow"
    x={geometry.x - 6}
    y={geometry.y - 6}
    width={geometry.width + 12}
    height={geometry.height + 12}
    rx="4"
  />

  <rect
    class="house-window__hit"
    x={geometry.x - 9}
    y={geometry.y - 9}
    width={geometry.width + 18}
    height={geometry.height + 22}
    rx="4"
  />

  <g class="house-window__debug" aria-hidden="true">
    {#each panes as pane}
      <rect x={pane.x} y={pane.y} width={pane.width} height={pane.height} />
    {/each}
    <rect
      class="house-window__debug-hit"
      x={geometry.x - 9}
      y={geometry.y - 9}
      width={geometry.width + 18}
      height={geometry.height + 22}
      rx="4"
    />
    <g transform={`translate(${geometry.x + geometry.width / 2} ${geometry.y - 18})`}>
      <rect class="house-window__debug-label-bg" x="-76" y="-14" width="152" height="28" rx="14" />
      <text class="house-window__debug-label" text-anchor="middle" dominant-baseline="central">
        {destination.id} · {geometry.x},{geometry.y} · {geometry.width}×{geometry.height}
      </text>
    </g>
  </g>

  <g
    class="house-window__label"
    transform={`translate(${geometry.x + geometry.width / 2} ${labelY})`}
  >
    <rect x="-76" y="-17" width="152" height="34" rx="17" />
    <text text-anchor="middle" dominant-baseline="central">{destination.label}</text>
  </g>
</a>
