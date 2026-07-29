<script lang="ts">
  import { T } from '@threlte/core';
  import { useGltf } from '@threlte/extras';
  import {
    Mesh,
    MeshPhysicalMaterial,
    MeshStandardMaterial,
    type Material,
  } from 'three';

  export let onReady: () => void = () => {};

  const chandelier = useGltf('/models/warm-chandelier.glb');
  let prepared = false;

  function styleMaterial(material: Material) {
    const standard = material as MeshStandardMaterial;

    if (material.name === 'Chandelier Brass') {
      standard.color.set('#6f3f13');
      standard.metalness = 0.78;
      standard.roughness = 0.2;
      const physical = material as MeshPhysicalMaterial;
      physical.clearcoat = 0.38;
      physical.clearcoatRoughness = 0.08;
    } else if (material.name === 'Chandelier Dark Brass') {
      standard.color.set('#2a1608');
      standard.metalness = 0.72;
      standard.roughness = 0.31;
    } else if (material.name === 'Warm Chandelier Glass') {
      standard.color.set('#ffc56f');
      standard.roughness = 0.16;
      standard.emissive.set('#ff7a22');
      standard.emissiveIntensity = 5.2;
      const physical = material as MeshPhysicalMaterial;
      physical.clearcoat = 0.62;
      physical.clearcoatRoughness = 0.045;
    }

    material.needsUpdate = true;
  }

  $: if ($chandelier && !prepared) {
    $chandelier.scene.traverse((object) => {
      if (!(object instanceof Mesh)) return;

      object.castShadow = true;
      object.receiveShadow = true;

      const materials = Array.isArray(object.material)
        ? object.material
        : [object.material];

      for (const material of materials) {
        styleMaterial(material);
      }
    });

    prepared = true;
    onReady();
  }
</script>

{#if $chandelier}
  <T is={$chandelier.scene} />
{/if}

<T.PointLight
  position={[0, 2.68, 0]}
  intensity={34}
  distance={7.8}
  decay={2}
  color="#ffad55"
  castShadow
  oncreate={(light) => {
    light.shadow.mapSize.set(1024, 1024);
    light.shadow.bias = -0.00035;
  }}
/>

<T.PointLight
  position={[0, 3.12, 0]}
  intensity={11}
  distance={5.5}
  decay={2}
  color="#ffd39a"
/>
