<script lang="ts">
  import { onMount } from 'svelte';
  import { T, useThrelte } from '@threlte/core';
  import { MathUtils, type PerspectiveCamera } from 'three';

  export let resetSignal = 0;

  const { renderer, invalidate } = useThrelte();

  const INITIAL_YAW = 0;
  const INITIAL_PITCH = -0.035;
  const DRAG_SENSITIVITY = 0.0032;
  const KEY_STEP = 0.075;
  const MIN_PITCH = MathUtils.degToRad(-68);
  const MAX_PITCH = MathUtils.degToRad(72);

  let camera: PerspectiveCamera;
  let yaw = INITIAL_YAW;
  let pitch = INITIAL_PITCH;
  let previousResetSignal = resetSignal;
  let activePointer: number | null = null;
  let lastX = 0;
  let lastY = 0;

  function applyRotation() {
    if (!camera) return;

    camera.rotation.order = 'YXZ';
    camera.rotation.set(pitch, yaw, 0);
    invalidate();
  }

  function resetView() {
    yaw = INITIAL_YAW;
    pitch = INITIAL_PITCH;
    applyRotation();
  }

  $: if (camera) {
    applyRotation();
  }

  $: if (resetSignal !== previousResetSignal) {
    previousResetSignal = resetSignal;
    resetView();
  }

  onMount(() => {
    const canvas = renderer.domElement;
    canvas.tabIndex = 0;
    canvas.setAttribute('aria-label', 'Drag to look around the checkerboard room');

    function handlePointerDown(event: PointerEvent) {
      if (event.pointerType === 'mouse' && event.button !== 0) return;

      activePointer = event.pointerId;
      lastX = event.clientX;
      lastY = event.clientY;
      canvas.setPointerCapture(event.pointerId);
      canvas.classList.add('is-looking');
      canvas.focus({ preventScroll: true });
    }

    function handlePointerMove(event: PointerEvent) {
      if (activePointer !== event.pointerId) return;

      const deltaX = event.clientX - lastX;
      const deltaY = event.clientY - lastY;
      lastX = event.clientX;
      lastY = event.clientY;

      yaw -= deltaX * DRAG_SENSITIVITY;
      pitch = MathUtils.clamp(
        pitch - deltaY * DRAG_SENSITIVITY,
        MIN_PITCH,
        MAX_PITCH,
      );
      applyRotation();
    }

    function releasePointer(event: PointerEvent) {
      if (activePointer !== event.pointerId) return;

      if (canvas.hasPointerCapture(event.pointerId)) {
        canvas.releasePointerCapture(event.pointerId);
      }
      activePointer = null;
      canvas.classList.remove('is-looking');
    }

    function handleKeyDown(event: KeyboardEvent) {
      let handled = true;

      switch (event.key) {
        case 'ArrowLeft':
          yaw += KEY_STEP;
          break;
        case 'ArrowRight':
          yaw -= KEY_STEP;
          break;
        case 'ArrowUp':
          pitch = MathUtils.clamp(pitch + KEY_STEP, MIN_PITCH, MAX_PITCH);
          break;
        case 'ArrowDown':
          pitch = MathUtils.clamp(pitch - KEY_STEP, MIN_PITCH, MAX_PITCH);
          break;
        case 'Home':
          resetView();
          break;
        default:
          handled = false;
      }

      if (handled) {
        event.preventDefault();
        applyRotation();
      }
    }

    function preventContextMenu(event: MouseEvent) {
      event.preventDefault();
    }

    canvas.addEventListener('pointerdown', handlePointerDown);
    canvas.addEventListener('pointermove', handlePointerMove);
    canvas.addEventListener('pointerup', releasePointer);
    canvas.addEventListener('pointercancel', releasePointer);
    canvas.addEventListener('keydown', handleKeyDown);
    canvas.addEventListener('contextmenu', preventContextMenu);

    return () => {
      canvas.removeEventListener('pointerdown', handlePointerDown);
      canvas.removeEventListener('pointermove', handlePointerMove);
      canvas.removeEventListener('pointerup', releasePointer);
      canvas.removeEventListener('pointercancel', releasePointer);
      canvas.removeEventListener('keydown', handleKeyDown);
      canvas.removeEventListener('contextmenu', preventContextMenu);
      canvas.classList.remove('is-looking');
    };
  });
</script>

<T.PerspectiveCamera
  bind:ref={camera}
  makeDefault
  position={[0, 1.62, 0.58]}
  fov={68}
  near={0.05}
  far={32}
/>
