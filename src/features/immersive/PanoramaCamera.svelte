<script lang="ts">
  import { onMount } from 'svelte';
  import { T, useThrelte } from '@threlte/core';
  import { MathUtils, type PerspectiveCamera } from 'three';

  export let resetSignal = 0;
  export let position: [number, number, number] = [0, 1.65, 3.8];
  export let initialYaw = 0;
  export let ariaLabel =
    'Drag to look around. Scroll or pinch to zoom. Drag interactive objects to move them.';

  const { renderer, invalidate } = useThrelte();

  const INITIAL_PITCH = 0;
  const MIN_FOV = 32;
  const MAX_FOV = 76;
  const INITIAL_FOV = MAX_FOV;
  const DRAG_SENSITIVITY = 0.00225;
  const WHEEL_ZOOM_SENSITIVITY = 0.018;
  const PINCH_ZOOM_SENSITIVITY = 0.065;
  const LOOK_SMOOTHING = 0.16;
  const ZOOM_SMOOTHING = 0.12;
  const SETTLE_EPSILON = 0.0001;
  const KEY_LOOK_STEP = 0.075;
  const KEY_ZOOM_STEP = 3;
  const MIN_PITCH = MathUtils.degToRad(-48);
  const MAX_PITCH = MathUtils.degToRad(34);

  type PointerPosition = { x: number; y: number };

  let camera: PerspectiveCamera;
  let yaw = initialYaw;
  let pitch = INITIAL_PITCH;
  let fov = INITIAL_FOV;
  let targetYaw = initialYaw;
  let targetPitch = INITIAL_PITCH;
  let targetFov = INITIAL_FOV;
  let animationFrame = 0;
  let previousResetSignal = resetSignal;
  let dragPointer: number | null = null;
  let lastX = 0;
  let lastY = 0;
  let previousPinchDistance: number | null = null;

  const pointers = new Map<number, PointerPosition>();

  function applyCamera() {
    if (!camera) return;
    camera.rotation.order = 'YXZ';
    camera.rotation.set(pitch, yaw, 0);
    camera.fov = fov;
    camera.updateProjectionMatrix();
    invalidate();
  }

  function animateCamera() {
    animationFrame = 0;

    yaw = MathUtils.lerp(yaw, targetYaw, LOOK_SMOOTHING);
    pitch = MathUtils.lerp(pitch, targetPitch, LOOK_SMOOTHING);
    fov = MathUtils.lerp(fov, targetFov, ZOOM_SMOOTHING);
    applyCamera();

    const stillMoving =
      Math.abs(targetYaw - yaw) > SETTLE_EPSILON ||
      Math.abs(targetPitch - pitch) > SETTLE_EPSILON ||
      Math.abs(targetFov - fov) > SETTLE_EPSILON;

    if (stillMoving) {
      animationFrame = requestAnimationFrame(animateCamera);
      return;
    }

    yaw = targetYaw;
    pitch = targetPitch;
    fov = targetFov;
    applyCamera();
  }

  function requestCameraAnimation() {
    if (!animationFrame) animationFrame = requestAnimationFrame(animateCamera);
  }

  function setFov(nextFov: number) {
    targetFov = MathUtils.clamp(nextFov, MIN_FOV, MAX_FOV);
    requestCameraAnimation();
  }

  function resetView() {
    targetYaw = initialYaw;
    targetPitch = INITIAL_PITCH;
    targetFov = INITIAL_FOV;
    requestCameraAnimation();
  }

  function getPinchDistance() {
    const positions = [...pointers.values()];
    if (positions.length < 2) return null;
    return Math.hypot(
      positions[0].x - positions[1].x,
      positions[0].y - positions[1].y,
    );
  }

  $: if (camera) applyCamera();

  $: if (resetSignal !== previousResetSignal) {
    previousResetSignal = resetSignal;
    resetView();
  }

  onMount(() => {
    const canvas = renderer.domElement;
    canvas.tabIndex = 0;
    canvas.setAttribute('aria-label', ariaLabel);

    function objectIsBeingGrabbed() {
      return canvas.dataset.grabbingObject === 'true';
    }

    function updateLookingClass() {
      canvas.classList.toggle(
        'is-looking',
        pointers.size > 0 && !objectIsBeingGrabbed(),
      );
    }

    function handlePointerDown(event: PointerEvent) {
      if (objectIsBeingGrabbed()) return;
      if (event.pointerType === 'mouse' && event.button !== 0) return;

      pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      try {
        canvas.setPointerCapture(event.pointerId);
      } catch {
        // Pointer capture is optional.
      }

      if (pointers.size === 1) {
        dragPointer = event.pointerId;
        lastX = event.clientX;
        lastY = event.clientY;
        previousPinchDistance = null;
      } else if (pointers.size === 2) {
        dragPointer = null;
        previousPinchDistance = getPinchDistance();
      }

      updateLookingClass();
      canvas.focus({ preventScroll: true });
    }

    function handlePointerMove(event: PointerEvent) {
      if (objectIsBeingGrabbed()) return;
      if (!pointers.has(event.pointerId)) return;

      pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });

      if (pointers.size >= 2) {
        const distance = getPinchDistance();
        if (distance !== null && previousPinchDistance !== null) {
          setFov(
            targetFov -
              (distance - previousPinchDistance) * PINCH_ZOOM_SENSITIVITY,
          );
        }
        previousPinchDistance = distance;
        return;
      }

      if (dragPointer !== event.pointerId) return;

      const deltaX = event.clientX - lastX;
      const deltaY = event.clientY - lastY;
      lastX = event.clientX;
      lastY = event.clientY;

      targetYaw -= deltaX * DRAG_SENSITIVITY;
      targetPitch = MathUtils.clamp(
        targetPitch - deltaY * DRAG_SENSITIVITY,
        MIN_PITCH,
        MAX_PITCH,
      );
      requestCameraAnimation();
    }

    function releasePointer(event: PointerEvent) {
      if (!pointers.has(event.pointerId)) return;
      pointers.delete(event.pointerId);

      try {
        if (canvas.hasPointerCapture(event.pointerId)) {
          canvas.releasePointerCapture(event.pointerId);
        }
      } catch {
        // The browser may already have released pointer capture.
      }

      if (pointers.size === 1) {
        const [remainingId, remainingPosition] = [...pointers.entries()][0];
        dragPointer = remainingId;
        lastX = remainingPosition.x;
        lastY = remainingPosition.y;
        previousPinchDistance = null;
      } else {
        dragPointer = null;
        previousPinchDistance = null;
      }

      updateLookingClass();
    }

    function handleWheel(event: WheelEvent) {
      event.preventDefault();
      const scale = event.deltaMode === WheelEvent.DOM_DELTA_LINE ? 16 : 1;
      setFov(
        targetFov + event.deltaY * scale * WHEEL_ZOOM_SENSITIVITY,
      );
    }

    function handleKeyDown(event: KeyboardEvent) {
      let handled = true;
      switch (event.key) {
        case 'ArrowLeft': targetYaw += KEY_LOOK_STEP; break;
        case 'ArrowRight': targetYaw -= KEY_LOOK_STEP; break;
        case 'ArrowUp':
          targetPitch = MathUtils.clamp(
            targetPitch + KEY_LOOK_STEP,
            MIN_PITCH,
            MAX_PITCH,
          );
          break;
        case 'ArrowDown':
          targetPitch = MathUtils.clamp(
            targetPitch - KEY_LOOK_STEP,
            MIN_PITCH,
            MAX_PITCH,
          );
          break;
        case '+':
        case '=': setFov(targetFov - KEY_ZOOM_STEP); break;
        case '-':
        case '_': setFov(targetFov + KEY_ZOOM_STEP); break;
        case '0':
        case 'Home': resetView(); break;
        default: handled = false;
      }

      if (handled) {
        event.preventDefault();
        requestCameraAnimation();
      }
    }

    function preventContextMenu(event: MouseEvent) {
      event.preventDefault();
    }

    canvas.addEventListener('pointerdown', handlePointerDown);
    canvas.addEventListener('pointermove', handlePointerMove);
    canvas.addEventListener('pointerup', releasePointer);
    canvas.addEventListener('pointercancel', releasePointer);
    canvas.addEventListener('wheel', handleWheel, { passive: false });
    canvas.addEventListener('keydown', handleKeyDown);
    canvas.addEventListener('contextmenu', preventContextMenu);

    return () => {
      canvas.removeEventListener('pointerdown', handlePointerDown);
      canvas.removeEventListener('pointermove', handlePointerMove);
      canvas.removeEventListener('pointerup', releasePointer);
      canvas.removeEventListener('pointercancel', releasePointer);
      canvas.removeEventListener('wheel', handleWheel);
      canvas.removeEventListener('keydown', handleKeyDown);
      canvas.removeEventListener('contextmenu', preventContextMenu);
      canvas.classList.remove('is-looking');
      pointers.clear();
      if (animationFrame) cancelAnimationFrame(animationFrame);
    };
  });
</script>

<T.PerspectiveCamera
  bind:ref={camera}
  name="PanoramaCamera"
  makeDefault
  {position}
  fov={INITIAL_FOV}
  near={0.05}
  far={60}
/>
