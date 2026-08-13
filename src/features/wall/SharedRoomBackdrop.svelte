<script lang="ts">
  import { onMount } from 'svelte';
  import WallBackdrop from './WallBackdrop.svelte';
  import FloorScene from '../floor/FloorScene.svelte';

  export let initialCameraX = 0;

  type RoomCameraWindow = Window & {
    __hecateRoomCameraX?: number;
    __hecateSetRoomCameraX?: (cameraX: number) => void;
  };

  let wallBackdrop: { setCameraX: (cameraX: number) => void };
  let floorScene: { setCameraX: (cameraX: number) => void };

  function applyCamera(cameraX: number) {
    wallBackdrop?.setCameraX(cameraX);
    floorScene?.setCameraX(cameraX);
  }

  function normalizePath(pathname: string) {
    if (pathname === '/') return '/';
    return pathname.replace(/\/+$/, '');
  }

  onMount(() => {
    const roomWindow = window as RoomCameraWindow;
    const inheritedCameraX = Number.isFinite(roomWindow.__hecateRoomCameraX)
      ? (roomWindow.__hecateRoomCameraX as number)
      : initialCameraX;

    roomWindow.__hecateRoomCameraX = inheritedCameraX;
    applyCamera(inheritedCameraX);

    const setCameraX = (cameraX: number) => {
      roomWindow.__hecateRoomCameraX = cameraX;
      applyCamera(cameraX);
    };

    roomWindow.__hecateSetRoomCameraX = setCameraX;

    const resetStaticRoomBackdrop = () => {
      if (normalizePath(window.location.pathname) === '/') return;
      setCameraX(0);
    };

    document.addEventListener('astro:page-load', resetStaticRoomBackdrop);
    resetStaticRoomBackdrop();

    return () => {
      document.removeEventListener('astro:page-load', resetStaticRoomBackdrop);
      if (roomWindow.__hecateSetRoomCameraX === setCameraX) {
        delete roomWindow.__hecateSetRoomCameraX;
      }
    };
  });
</script>

<div class="site-room-backdrop primary-room-backdrop wall-room-host" aria-hidden="true">
  <WallBackdrop bind:this={wallBackdrop} initialCameraX={initialCameraX} />
  <FloorScene bind:this={floorScene} initialCameraX={initialCameraX} />
</div>
