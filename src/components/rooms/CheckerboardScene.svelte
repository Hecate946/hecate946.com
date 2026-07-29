<script lang="ts">
  import { onDestroy } from 'svelte';
  import { T, useThrelte } from '@threlte/core';
  import { useGltf } from '@threlte/extras';
  import {
    Color,
    FogExp2,
    Mesh,
    MeshPhysicalMaterial,
    MeshStandardMaterial,
    type Material,
    type Object3D,
  } from 'three';
  import LookAroundCamera from './LookAroundCamera.svelte';
  import WarmChandelier from './WarmChandelier.svelte';

  export let onReady: () => void = () => {};
  export let resetSignal = 0;

  const { scene } = useThrelte();
  const room = useGltf('/models/checkerboard.glb');

  const originalBackground = scene.background;
  const originalFog = scene.fog;

  scene.background = new Color('#010503');
  scene.fog = new FogExp2('#031008', 0.018);

  onDestroy(() => {
    scene.background = originalBackground;
    scene.fog = originalFog;
  });

  let roomPrepared = false;
  let chandelierPrepared = false;
  let readySent = false;

  function maybeReady() {
    if (roomPrepared && chandelierPrepared && !readySent) {
      readySent = true;
      onReady();
    }
  }

  function styleMaterial(material: Material) {
    const standard = material as MeshStandardMaterial;
    standard.metalness = 0;
    standard.envMapIntensity = 1.18;

    if (material.name.startsWith('Wall_Green_')) {
      standard.roughness = 0.075;
      const physical = material as MeshPhysicalMaterial;
      physical.clearcoat = 0.9;
      physical.clearcoatRoughness = 0.035;
    } else if (material.name.startsWith('Floor_Green_Marble_')) {
      standard.roughness = 0.105;
      const physical = material as MeshPhysicalMaterial;
      physical.clearcoat = 0.72;
      physical.clearcoatRoughness = 0.045;
    } else if (material.name.startsWith('Floor_Ivory_Marble_')) {
      standard.roughness = 0.13;
      const physical = material as MeshPhysicalMaterial;
      physical.clearcoat = 0.65;
      physical.clearcoatRoughness = 0.055;
    } else if (material.name.includes('Marble Veins')) {
      standard.roughness = 0.19;
    } else if (material.name === 'Deep Green Grout') {
      standard.color.set('#020b07');
      standard.roughness = 0.64;
    } else if (material.name === 'Warm Shadow Ceiling') {
      standard.color.set('#333a30');
      standard.roughness = 0.78;
    }

    material.needsUpdate = true;
  }

  function prepareRoom(root: Object3D) {
    root.traverse((object) => {
      if (!(object instanceof Mesh)) return;

      object.castShadow = !object.name.includes('Ceiling');
      object.receiveShadow = true;

      const materials = Array.isArray(object.material)
        ? object.material
        : [object.material];

      for (const material of materials) {
        styleMaterial(material);
      }
    });
  }

  function markChandelierReady() {
    chandelierPrepared = true;
    maybeReady();
  }

  $: if ($room && !roomPrepared) {
    prepareRoom($room.scene);
    roomPrepared = true;
    maybeReady();
  }
</script>

<LookAroundCamera {resetSignal} />

<T.HemisphereLight args={['#6d9b78', '#010302', 0.52]} />
<T.AmbientLight intensity={0.14} color="#b5c8b7" />

<T.PointLight
  position={[-2.65, 1.3, -3.8]}
  intensity={6.5}
  distance={6.5}
  decay={2}
  color="#0d5c31"
/>
<T.PointLight
  position={[2.65, 1.15, 3.6]}
  intensity={5.5}
  distance={6.2}
  decay={2}
  color="#174c2e"
/>

{#if $room}
  <T is={$room.scene} />
{/if}

<WarmChandelier onReady={markChandelierReady} />
