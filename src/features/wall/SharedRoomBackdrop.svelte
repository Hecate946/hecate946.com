<script lang="ts">
  import { onMount } from 'svelte';
  import WallBackdrop from './WallBackdrop.svelte';
  import FloorScene from '../floor/FloorScene.svelte';

  export let initialCameraX = 0;

  type RoomCameraWindow = Window & {
    __hecateRoomCameraX?: number;
    __hecateRoomCameraAbsolute?: boolean;
    __hecateSetRoomCameraX?: (cameraX: number, absolute?: boolean) => void;
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
    // Home publishes an absolute camera before this component mounts, so
    // the flag is read from the window rather than assumed false -- which
    // is what keeps the two mount orders from producing different walls.
    let absoluteCamera = roomWindow.__hecateRoomCameraAbsolute === true;
    let widestRoomWidth = roomBackdrop.getBoundingClientRect().width;
    let currentRoomWidth = widestRoomWidth;
    let resizeFrame = 0;

    function renderRoomCamera() {
      // Ordinary pages keep the scene's right edge fixed: every pixel
      // removed from the viewport pans the shared world left by one pixel,
      // so the brick wall and checkerboard floor behave like two surfaces
      // in the same room.
      //
      // Home opts out. It pins the camera to the doorway's centre instead,
      // because there the wall has to hold station against the casing -- a
      // width-driven pan slides the mortar joints past a door that is
      // anchored to the middle of the viewport.
      applyCamera(
        absoluteCamera
          ? baseCameraX
          : baseCameraX + widestRoomWidth - currentRoomWidth,
      );
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

    const setCameraX = (cameraX: number, absolute = false) => {
      baseCameraX = cameraX;
      absoluteCamera = absolute;
      roomWindow.__hecateRoomCameraX = baseCameraX;
      roomWindow.__hecateRoomCameraAbsolute = absolute;
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
