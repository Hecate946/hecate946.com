<script lang="ts">
  import type { Object3D } from 'three';
  import type { ImmersiveSpace } from '../../catalog';

  export let space: ImmersiveSpace;
  export let interactiveScene: Object3D | null = null;

  // Add future green-room-only Threlte objects or behavior here.
  // Permanent visual elements are usually better added to:
  // blender/rooms/green/unique.py so Cycles includes them in the panorama.
  void space;
  void interactiveScene;
</script>
