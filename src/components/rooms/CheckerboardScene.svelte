<script lang="ts">
  import { onDestroy } from 'svelte';
  import { T, useThrelte } from '@threlte/core';
  import { useGltf } from '@threlte/extras';
  import { Light, Mesh, MeshStandardMaterial } from 'three';
  import LookAroundCamera from './LookAroundCamera.svelte';

  export let onReady: () => void = () => {};
  export let resetSignal = 0;

  const { renderer, scene, invalidate } = useThrelte();
  const room = useGltf('/models/checkerboard.glb');

  /*
   * V11 deliberately uses a single simple overhead warm light exported by
   * Blender. There is no RoomEnvironment, ambient light, or website-side
   * fallback light rig. Blender uses -0.65 exposure stops; the equivalent
   * linear Three.js multiplier is 2 ** -0.65 = 0.6372803137.
   */
  const previousExposure = renderer.toneMappingExposure;
  const previousEnvironment = scene.environment;
  const previousEnvironmentIntensity = scene.environmentIntensity;

  renderer.toneMappingExposure = 0.6372803137;
  scene.environment = null;
  scene.environmentIntensity = 0;
  invalidate();

  let readySent = false;
  let roomPrepared = false;

  onDestroy(() => {
    renderer.toneMappingExposure = previousExposure;
    scene.environment = previousEnvironment;
    scene.environmentIntensity = previousEnvironmentIntensity;
  });

  $: if ($room && !roomPrepared) {
    $room.scene.traverse((object) => {
      const objectName = object.name.toLowerCase();

      // Hide any chandelier geometry from older GLBs so the website stays in
      // sync with the chandelier-free Blender scene.
      if (objectName.includes('chandelier')) {
        object.visible = false;
        return;
      }

      if (object instanceof Mesh) {
        // The shared Blender/web overhead spotlight is intentionally shadowless.
        object.castShadow = false;
        object.receiveShadow = false;

        const materials = Array.isArray(object.material)
          ? object.material
          : [object.material];

        for (const material of materials) {
          if (!(material instanceof MeshStandardMaterial)) continue;

          // Do not add website-only environment reflections. Direct specular
          // highlights now come from Room_Overhead_Warm_Spot in the GLB.
          material.envMapIntensity = 0;
          material.needsUpdate = true;
        }
      }

      if (object instanceof Light) {
        const isSharedRoomLight = objectName.startsWith('room_');

        if (isSharedRoomLight) {
          // Preserve the exported Blender color, intensity, cone, position,
          // and direction. Only shadows are explicitly disabled.
          object.visible = true;
          object.castShadow = false;
        } else {
          // Hide all older light rigs, including earlier web lights and any
          // stray chandelier lights from previous GLBs.
          object.visible = false;
          object.intensity = 0;
          object.castShadow = false;
        }
      }
    });

    roomPrepared = true;
    invalidate();
  }

  $: if ($room && !readySent) {
    readySent = true;
    onReady();
  }
</script>

<LookAroundCamera {resetSignal} />

{#if $room}
  <T is={$room.scene} />
{/if}
