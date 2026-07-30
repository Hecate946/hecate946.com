<script lang="ts">
  import { T } from '@threlte/core';
  import { useGltf } from '@threlte/extras';
  import type { Object3D } from 'three';

  export let url: string;
  export let onPrepared: (scene: Object3D) => void = () => {};

  const gltf = useGltf(url);
  let prepared = false;

  $: if ($gltf && !prepared) {
    prepared = true;
    onPrepared($gltf.scene);
  }
</script>

{#if $gltf}
  <T is={$gltf.scene} />
{/if}
