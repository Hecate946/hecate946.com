<script lang="ts">
  import type { HouseDestination } from '@/config/house-scene';

  export let destination: HouseDestination;
  export let navigationEnabled = true;

  $: geometry = destination.geometry;

  function handleClick(event: MouseEvent) {
    if (!navigationEnabled) event.preventDefault();
  }
</script>

<a
  class="house-window"
  href={destination.href}
  aria-label={`Open ${destination.label}: ${destination.description}`}
  aria-disabled={!navigationEnabled}
  data-house-window={destination.id}
  onclick={handleClick}
>
  <g transform={`translate(${geometry.x} ${geometry.y})`}>
    <rect
      class="house-window__glow"
      x="-7"
      y="-7"
      width={geometry.width + 14}
      height={geometry.height + 14}
      rx="4"
    />
    <rect
      class="house-window__hit"
      x="-10"
      y="-10"
      width={geometry.width + 20}
      height={geometry.height + 28}
      rx="3"
    />

    <g class="house-window__label" transform={`translate(${geometry.width / 2} ${geometry.height + 31})`}>
      <rect x="-76" y="-17" width="152" height="34" rx="17" />
      <text text-anchor="middle" dominant-baseline="central">{destination.label}</text>
    </g>
  </g>
</a>
