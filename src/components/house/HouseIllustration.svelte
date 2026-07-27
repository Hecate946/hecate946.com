<script lang="ts">
  import type { HouseDestination } from '@/config/house-scene';
  import HouseShell from './HouseShell.svelte';
  import HouseWindow from './HouseWindow.svelte';

  export let destinations: readonly HouseDestination[] = [];
  export let navigationEnabled = true;
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
    A precise front elevation of a symmetrical two-story house with a central triangular pediment, five upper windows, two broad first-story windows, an arched double entrance, and three centered steps.
  </desc>

  <defs>
    <linearGradient id="house-ink" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#102d35" />
      <stop offset="0.52" stop-color="#0b252c" />
      <stop offset="1" stop-color="#071c23" />
    </linearGradient>
    <filter id="house-line-shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="1.4" stdDeviation="1.25" flood-color="#000" flood-opacity=".46" />
    </filter>
    <filter id="house-hover-glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="7" />
    </filter>
  </defs>

  <HouseShell />

  {#each destinations as destination (destination.id)}
    <HouseWindow {destination} {navigationEnabled} />
  {/each}
</svg>
