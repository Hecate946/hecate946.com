<script lang="ts">
  import { onMount } from 'svelte';
  import FloorScene from '@/features/floor/FloorScene.svelte';
  import { siteConfig } from '@/config/site';

  let legacyFloorComponent: any = null;
  let magnifyingGlassComponent: any = null;

  onMount(() => {
    if (!siteConfig.ui.enableMagnifyingGlass) return;

    // The active site uses the lightweight checkerboard renderer. The old
    // Three/Rapier floor is retained only as a compatibility host for the
    // magnifier, and is fetched solely if that global feature switch is turned
    // back on later.
    void Promise.all([
      import('@/features/floor/LegacyFloorScene.svelte'),
      import('@/features/floor/MagnifyingGlass.svelte'),
    ]).then(([floorModule, magnifierModule]) => {
      legacyFloorComponent = floorModule.default;
      magnifyingGlassComponent = magnifierModule.default;
    });
  });
</script>

{#if siteConfig.ui.enableMagnifyingGlass}
  {#if legacyFloorComponent}
    <svelte:component this={legacyFloorComponent}>
      {#if magnifyingGlassComponent}
        <svelte:component this={magnifyingGlassComponent} />
      {/if}
    </svelte:component>
  {:else}
    <FloorScene />
  {/if}
{:else}
  <FloorScene />
{/if}
