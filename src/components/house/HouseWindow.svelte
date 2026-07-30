<script lang="ts">
  import type { HouseDestination, HouseWindowPaneAxis } from '@/config/house-scene';
  import WindowScene from './WindowScene.svelte';

  export let destination: HouseDestination;
  export let navigationEnabled = true;

  type Pane = {
    x: number;
    y: number;
    width: number;
    height: number;
  };

  function buildPanes(
    x: number,
    y: number,
    width: number,
    height: number,
    columns: number,
    rows: number,
    mullionX: number,
    mullionY: number,
    paneColumns?: readonly HouseWindowPaneAxis[],
    paneRows?: readonly HouseWindowPaneAxis[],
  ): Pane[] {
    if (paneColumns?.length && paneRows?.length) {
      return paneRows.flatMap((row) =>
        paneColumns.map((column) => ({
          x: x + column.offset,
          y: y + row.offset,
          width: column.size,
          height: row.size,
        })),
      );
    }

    const paneWidth = (width - mullionX * (columns - 1)) / columns;
    const paneHeight = (height - mullionY * (rows - 1)) / rows;

    return Array.from({ length: columns * rows }, (_, index) => {
      const column = index % columns;
      const row = Math.floor(index / columns);

      return {
        x: x + column * (paneWidth + mullionX),
        y: y + row * (paneHeight + mullionY),
        width: paneWidth,
        height: paneHeight,
      };
    });
  }

  $: geometry = destination.geometry;
  $: clipId = `house-pane-clip-${destination.id}`;
  $: sceneWidth = destination.sceneViewBox?.width ?? 100;
  $: sceneHeight = destination.sceneViewBox?.height ?? 140;
  $: sceneFit = destination.sceneViewBox?.fit ?? 'slice';
  $: panes = buildPanes(
    geometry.x,
    geometry.y,
    geometry.width,
    geometry.height,
    geometry.columns,
    geometry.rows,
    geometry.mullionX,
    geometry.mullionY,
    geometry.paneColumns,
    geometry.paneRows,
  );

  function handleClick(event: MouseEvent) {
    if (!navigationEnabled) event.preventDefault();
  }
</script>

<defs>
  <clipPath id={clipId} clipPathUnits="userSpaceOnUse">
    {#each panes as pane}
      <rect x={pane.x} y={pane.y} width={pane.width} height={pane.height} rx="0.45" />
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
      class="house-window__viewport"
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
      class="house-window__glow"
      x={geometry.x}
      y={geometry.y}
      width={geometry.width}
      height={geometry.height}
    />

    <rect
      class="house-window__glass"
      x={geometry.x}
      y={geometry.y}
      width={geometry.width}
      height={geometry.height}
    />
  </g>

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
</a>
