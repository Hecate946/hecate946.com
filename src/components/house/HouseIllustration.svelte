<script lang="ts">
  import type { HouseDestination } from '@/config/house-scene';
  import { withBase } from '@/lib/paths';
  import '@/styles/house-window-scenes.css';
  import HouseWindow from './HouseWindow.svelte';

  export let destinations: readonly HouseDestination[] = [];
  export let navigationEnabled = true;
  export let debugWindows = false;
  export let scenesEnabled = true;

  const imageHref = withBase('/images/house/house-white-current.png');
</script>

<svg
  class="house-illustration"
  viewBox="0 0 1672 941"
  role="img"
  aria-labelledby="house-illustration-title house-illustration-description"
  preserveAspectRatio="xMidYMid meet"
  data-window-debug={debugWindows ? 'true' : 'false'}
  data-scenes={scenesEnabled ? 'on' : 'off'}
>
  <title id="house-illustration-title">Cyrus's interactive house</title>
  <desc id="house-illustration-description">
    A white neoclassical house whose five upper windows contain interactive miniature room scenes.
  </desc>

  <defs>
    <filter id="house-hover-glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="7" />
    </filter>
  </defs>

  <!-- Frozen full-house artwork. -->
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

  <!-- Scene artwork and interaction live in the same SVG coordinate system. -->
  {#each destinations as destination (destination.id)}
    <HouseWindow
      {destination}
      {navigationEnabled}
    />
  {/each}
</svg>
