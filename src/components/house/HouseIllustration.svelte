<script lang="ts">
  import type { HouseDestination } from '@/config/house-scene';
  import HouseShell from './HouseShell.svelte';
  import HouseWindow from './HouseWindow.svelte';

  export let destinations: readonly HouseDestination[] = [];
  export let navigationEnabled = true;
</script>

<svg
  class="house-illustration"
  viewBox="0 0 1400 820"
  role="img"
  aria-labelledby="house-illustration-title house-illustration-description"
>
  <title id="house-illustration-title">Cyrus's interactive house</title>
  <desc id="house-illustration-description">
    A clean, straight-on two-dimensional house with an arched double front door, violin f-hole handles, a small circular window above it, three perfectly aligned square windows, and one large half-dome window. Each window leads directly to a page.
  </desc>

  <defs>
    <linearGradient id="house-roof-main" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#9a938a" />
      <stop offset="0.42" stop-color="#6c665f" />
      <stop offset="1" stop-color="#312d2a" />
    </linearGradient>
    <linearGradient id="house-roof-shadow" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#2e2926" />
      <stop offset="1" stop-color="#141210" />
    </linearGradient>
    <linearGradient id="house-wood-light" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#dfc39e" />
      <stop offset="0.42" stop-color="#c99b6b" />
      <stop offset="1" stop-color="#8b5835" />
    </linearGradient>
    <linearGradient id="house-wood-mid" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#99613f" />
      <stop offset="0.46" stop-color="#6d4027" />
      <stop offset="1" stop-color="#3e2314" />
    </linearGradient>
    <linearGradient id="house-wood-dark" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#58311d" />
      <stop offset="0.5" stop-color="#361d11" />
      <stop offset="1" stop-color="#1c0f09" />
    </linearGradient>
    <linearGradient id="house-door" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#704126" />
      <stop offset="0.52" stop-color="#4c2919" />
      <stop offset="1" stop-color="#28140d" />
    </linearGradient>
    <linearGradient id="house-glass" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#e4f0e7" />
      <stop offset="0.38" stop-color="#9db2a9" />
      <stop offset="1" stop-color="#30443f" />
    </linearGradient>
    <linearGradient id="house-glass-hover" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#fff2c5" />
      <stop offset="0.48" stop-color="#c9b977" />
      <stop offset="1" stop-color="#52635b" />
    </linearGradient>
    <linearGradient id="house-stone" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#aaa49a" />
      <stop offset="1" stop-color="#625d57" />
    </linearGradient>
    <pattern id="house-siding" width="16" height="16" patternUnits="userSpaceOnUse">
      <rect width="16" height="16" fill="url(#house-wood-light)" />
      <path d="M0 14.4H16" stroke="#6f452d" stroke-opacity=".55" stroke-width="1.1" />
      <path d="M0 1.6H16" stroke="#f3d8b5" stroke-opacity=".24" stroke-width=".9" />
    </pattern>
    <pattern id="house-shingles" width="20" height="11" patternUnits="userSpaceOnUse">
      <rect width="20" height="11" fill="url(#house-roof-main)" />
      <path d="M0 10.2H20M10 0v10.2" stroke="#2d2925" stroke-opacity=".56" stroke-width=".85" />
      <path d="M0 1.2H20" stroke="#dad3ca" stroke-opacity=".14" stroke-width=".75" />
    </pattern>
    <pattern id="house-foundation-blocks" width="84" height="32" patternUnits="userSpaceOnUse">
      <rect width="84" height="32" fill="url(#house-stone)" />
      <path d="M0 1h84M0 31h84M42 1v30" stroke="#3f3b37" stroke-opacity=".42" stroke-width="1.4" />
      <path d="M5 7h28M49 22h27" stroke="#ddd7ce" stroke-opacity=".18" stroke-width="2" />
    </pattern>
    <filter id="house-building-shadow" x="-20%" y="-20%" width="160%" height="190%">
      <feDropShadow dx="0" dy="17" stdDeviation="13" flood-color="#000" flood-opacity=".28" />
    </filter>
    <filter id="house-window-shadow" x="-40%" y="-40%" width="180%" height="200%">
      <feDropShadow dx="0" dy="7" stdDeviation="5" flood-color="#000" flood-opacity=".3" />
    </filter>
  </defs>

  <g filter="url(#house-building-shadow)">
    <HouseShell />

    {#each destinations as destination (destination.id)}
      <HouseWindow {destination} {navigationEnabled} />
    {/each}
  </g>
</svg>
