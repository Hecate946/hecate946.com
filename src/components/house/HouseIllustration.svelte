<script lang="ts">
  import type { HouseDestination } from '@/config/house-scene';
  import { withBase } from '@/lib/paths';
  import '@/styles/house-window-scenes.css';
  import HouseWindow from './HouseWindow.svelte';

  export let destinations: readonly HouseDestination[] = [];
  export let navigationEnabled = true;
  export let debugWindows = false;
  export let scenesEnabled = true;

  const imageHref = withBase('/images/house/house-shell.webp');
</script>

<svg
  class="house-illustration"
  viewBox="0 0 1800 1200"
  role="img"
  aria-labelledby="house-illustration-title house-illustration-description"
  preserveAspectRatio="xMidYMid meet"
  data-window-debug={debugWindows ? 'true' : 'false'}
  data-scenes={scenesEnabled ? 'on' : 'off'}
>
  <title id="house-illustration-title">Cyrus's interactive house</title>
  <desc id="house-illustration-description">
    A transparent cream neoclassical house with a dark slate roof whose windows contain interactive miniature scenes.
  </desc>

  <image
    class="house-illustration__reference"
    href={imageHref}
    x="0"
    y="0"
    width="1800"
    height="1200"
    preserveAspectRatio="none"
    pointer-events="none"
  />

  {#each destinations as destination (destination.id)}
    <HouseWindow {destination} {navigationEnabled} />
  {/each}
</svg>
