<script lang="ts">
  import { onMount } from 'svelte';
  import HomeWall from '@/features/wall/HomeWall.svelte';

  export let initialPath = '/';

  const normalizePath = (pathname: string) => {
    if (pathname === '/') return '/';
    return pathname.replace(/\/+$/, '');
  };

  let homeActive = normalizePath(initialPath) === '/';
  let homeMounted = homeActive;

  $: if (homeActive) homeMounted = true;

  function syncRoute() {
    homeActive = normalizePath(window.location.pathname) === '/';
  }

  onMount(() => {
    syncRoute();
    document.addEventListener('astro:after-swap', syncRoute);

    return () => {
      document.removeEventListener('astro:after-swap', syncRoute);
    };
  });
</script>

<div class="primary-room-engine" data-home-active={homeActive}>
  {#if homeMounted}
    <div class="primary-room-engine__wall" hidden={!homeActive}>
      <HomeWall active={homeActive} />
    </div>
  {/if}
</div>
