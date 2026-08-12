<script lang="ts">
  import { onMount } from 'svelte';
  import FloorScene from '@/features/floor/FloorScene.svelte';
  import { siteConfig } from '@/config/site';

  let magnifyingGlassComponent: any = null;

  onMount(() => {
    if (!siteConfig.ui.enableMagnifyingGlass) return;

    // Keep the expensive Three/Rapier magnifier completely out of the active
    // About-page path while disabled. Flipping the global feature switch is
    // enough to bring the existing implementation back.
    void import('@/features/floor/MagnifyingGlass.svelte').then((module) => {
      magnifyingGlassComponent = module.default;
    });
  });
</script>

<FloorScene>
  {#if magnifyingGlassComponent}
    <svelte:component this={magnifyingGlassComponent} />
  {/if}
</FloorScene>
