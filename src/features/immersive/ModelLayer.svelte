<script lang="ts">
  import { T } from '@threlte/core';
  import { useGltf } from '@threlte/extras';
  import type { Object3D } from 'three';
  import type { ImmersiveModelLayer } from './catalog';

  export let layer: ImmersiveModelLayer;
  export let onPrepared: (layer: ImmersiveModelLayer, scene: Object3D) => void = () => {};

  const gltf = useGltf(layer.url);
  let preparedScene: Object3D | null = null;

  function applyTransform(scene: Object3D) {
    const position = layer.position ?? [0, 0, 0];
    const rotation = layer.rotation ?? [0, 0, 0];
    const scale = layer.scale ?? [1, 1, 1];

    scene.position.set(...position);
    scene.rotation.set(...rotation);
    scene.scale.set(...scale);
    scene.updateMatrixWorld(true);
  }

  $: if ($gltf && preparedScene !== $gltf.scene) {
    preparedScene = $gltf.scene;
    applyTransform(preparedScene);
    onPrepared(layer, preparedScene);
  }
</script>

{#if $gltf}
  <T is={$gltf.scene} />
{/if}
