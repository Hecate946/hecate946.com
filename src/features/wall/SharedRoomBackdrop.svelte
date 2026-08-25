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
  let roomBackdrop: HTMLElement;

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
    let baseCameraX = Number.isFinite(roomWindow.__hecateRoomCameraX)
      ? (roomWindow.__hecateRoomCameraX as number)
      : initialCameraX;
    let widestRoomWidth = roomBackdrop.getBoundingClientRect().width;
    let currentRoomWidth = widestRoomWidth;
    let resizeFrame = 0;

    function renderRoomCamera() {
      // Keep the scene's right edge fixed. Every pixel removed from the
      // viewport pans the shared world left by one pixel, so the brick wall
      // and checkerboard floor behave like two surfaces in the same room.
      applyCamera(baseCameraX + widestRoomWidth - currentRoomWidth);
    }

    function measureRoom() {
      resizeFrame = 0;
      const nextWidth = roomBackdrop.getBoundingClientRect().width;
      if (!Number.isFinite(nextWidth) || nextWidth <= 0) return;

      currentRoomWidth = nextWidth;
      widestRoomWidth = Math.max(widestRoomWidth, nextWidth);
      renderRoomCamera();
    }

    function scheduleRoomMeasurement() {
      if (resizeFrame) return;
      resizeFrame = requestAnimationFrame(measureRoom);
    }

    roomWindow.__hecateRoomCameraX = baseCameraX;
    renderRoomCamera();

    const setCameraX = (cameraX: number) => {
      baseCameraX = cameraX;
      roomWindow.__hecateRoomCameraX = baseCameraX;
      renderRoomCamera();
    };

    roomWindow.__hecateSetRoomCameraX = setCameraX;

    const resetStaticRoomBackdrop = () => {
      if (normalizePath(window.location.pathname) === '/') return;
      setCameraX(0);
    };

    document.addEventListener('astro:page-load', resetStaticRoomBackdrop);
    const resizeObserver = new ResizeObserver(scheduleRoomMeasurement);
    resizeObserver.observe(roomBackdrop);
    window.addEventListener('resize', scheduleRoomMeasurement, {
      passive: true,
    });
    resetStaticRoomBackdrop();

    return () => {
      document.removeEventListener('astro:page-load', resetStaticRoomBackdrop);
      resizeObserver.disconnect();
      window.removeEventListener('resize', scheduleRoomMeasurement);
      cancelAnimationFrame(resizeFrame);
      if (roomWindow.__hecateSetRoomCameraX === setCameraX) {
        delete roomWindow.__hecateSetRoomCameraX;
      }
    };
  });
</script>

<div
  bind:this={roomBackdrop}
  class="site-room-backdrop primary-room-backdrop wall-room-host"
  aria-hidden="true"
>
  <WallBackdrop bind:this={wallBackdrop} {initialCameraX} />
  <FloorScene bind:this={floorScene} {initialCameraX} />
</div>
