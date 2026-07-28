<script lang="ts">
  import type { HouseDestination } from '@/config/house-scene';
  import { withBase } from '@/lib/paths';
  import HouseWindow from './HouseWindow.svelte';

  export let destinations: readonly HouseDestination[] = [];
  export let navigationEnabled = true;

  const imageHref = withBase('/images/house/house-white-current.png');
</script>

<svg
  class="house-illustration"
  viewBox="0 0 1672 941"
  role="img"
  aria-labelledby="house-illustration-title house-illustration-description"
  preserveAspectRatio="xMidYMid meet"
>
  <title id="house-illustration-title">Cyrus's interactive house</title>
  <desc id="house-illustration-description">
    A white neoclassical two-story house with five upper windows, two broad first-story windows,
    a centered arched entrance, a triangular pediment, and three wide entry steps.
  </desc>

  <defs>
    <filter id="house-hover-glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="7" />
    </filter>
  </defs>

  <!--
    The frozen PNG remains the visual source of truth. It is placed inside this
    1672 × 941 SVG coordinate system so the window interactions cannot drift.
  -->
  <image
    class="house-illustration__reference"
    href={imageHref}
    x="0"
    y="0"
    width="1672"
    height="941"
    preserveAspectRatio="none"
    pointer-events="none"
  />

  {#each destinations as destination (destination.id)}
    <HouseWindow {destination} {navigationEnabled} />
  {/each}
</svg>
