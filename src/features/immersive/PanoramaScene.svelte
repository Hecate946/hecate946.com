<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { T, useThrelte } from '@threlte/core';
  import {
    EquirectangularReflectionMapping,
    Light,
    Mesh,
    MeshBasicMaterial,
    Object3D,
    PCFSoftShadowMap,
    Plane,
    Raycaster,
    SphereGeometry,
    SRGBColorSpace,
    Texture,
    TextureLoader,
    Vector2,
    Vector3,
    type PerspectiveCamera,
  } from 'three';
  import type { ImmersiveSpace } from './catalog';
  import PanoramaCamera from './PanoramaCamera.svelte';
  import InteractiveLayer from './InteractiveLayer.svelte';
  import SpaceExtras from './SpaceExtras.svelte';

  export let space: ImmersiveSpace;
  export let onReady: () => void = () => {};
  export let resetSignal = 0;

  const CAMERA_POSITION = space.cameraPosition;
  const PANORAMA_YAW_OFFSET = space.panoramaYaw;
  const { renderer, scene, invalidate } = useThrelte();

  const previousExposure = renderer.toneMappingExposure;
  const previousOutputColorSpace = renderer.outputColorSpace;
  const previousShadowEnabled = renderer.shadowMap.enabled;
  const previousShadowType = renderer.shadowMap.type;
  const previousBackground = scene.background;
  const previousEnvironment = scene.environment;

  renderer.toneMappingExposure = 1;
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = PCFSoftShadowMap;
  scene.background = null;

  const panoramaGeometry = new SphereGeometry(24, 96, 64);
  panoramaGeometry.scale(-1, 1, 1);

  const panoramaMaterial = new MeshBasicMaterial({
    depthWrite: false,
    toneMapped: false,
  });

  const panoramaMesh = new Mesh(panoramaGeometry, panoramaMaterial);
  panoramaMesh.name = `${space.kind}_${space.slug}_Cycles_Panorama`;
  panoramaMesh.position.set(...CAMERA_POSITION);
  panoramaMesh.rotation.y = PANORAMA_YAW_OFFSET;
  panoramaMesh.frustumCulled = false;
  panoramaMesh.renderOrder = -1000;

  let displayTexture: Texture | null = null;
  let environmentTexture: Texture | null = null;
  let readySent = false;
  let interactivePrepared = false;
  let interactiveScene: Object3D | null = null;
  let grabbableMeshes: Mesh[] = [];

  const raycaster = new Raycaster();
  const pointer = new Vector2();
  const dragPlane = new Plane();
  const dragPoint = new Vector3();
  const dragOffset = new Vector3();
  const worldPosition = new Vector3();
  const cameraDirection = new Vector3();

  let draggedRoot: Object3D | null = null;
  let draggingPointerId: number | null = null;

  function sendReady() {
    if (readySent) return;
    readySent = true;
    onReady();
  }

  function findGrabRoot(object: Object3D | null) {
    let current = object;
    while (current && current !== interactiveScene) {
      if (current.name.startsWith('Grab_')) return current;
      current = current.parent;
    }
    return null;
  }

  function activeCamera() {
    return scene.getObjectByName('PanoramaCamera') as PerspectiveCamera | undefined;
  }

  function updatePointer(event: PointerEvent) {
    const bounds = renderer.domElement.getBoundingClientRect();
    pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
    pointer.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
  }

  function beginObjectDrag(event: PointerEvent) {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    if (grabbableMeshes.length === 0) return;

    const camera = activeCamera();
    if (!camera) return;

    updatePointer(event);
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(grabbableMeshes, true)[0];
    const root = findGrabRoot(hit?.object ?? null);
    if (!hit || !root) return;

    root.getWorldPosition(worldPosition);
    camera.getWorldDirection(cameraDirection);
    dragPlane.setFromNormalAndCoplanarPoint(cameraDirection, worldPosition);

    if (!raycaster.ray.intersectPlane(dragPlane, dragPoint)) return;

    draggedRoot = root;
    draggingPointerId = event.pointerId;
    dragOffset.copy(dragPoint).sub(worldPosition);

    const canvas = renderer.domElement;
    canvas.dataset.grabbingObject = 'true';
    canvas.classList.add('is-grabbing-object');
    try {
      canvas.setPointerCapture(event.pointerId);
    } catch {
      // Pointer capture is optional.
    }

    event.preventDefault();
    event.stopImmediatePropagation();
  }

  function moveObject(event: PointerEvent) {
    if (!draggedRoot || event.pointerId !== draggingPointerId) return;

    const camera = activeCamera();
    if (!camera) return;

    updatePointer(event);
    raycaster.setFromCamera(pointer, camera);
    if (!raycaster.ray.intersectPlane(dragPlane, dragPoint)) return;

    worldPosition.copy(dragPoint).sub(dragOffset);
    if (draggedRoot.parent) {
      draggedRoot.parent.worldToLocal(worldPosition);
    }
    draggedRoot.position.copy(worldPosition);
    invalidate();

    event.preventDefault();
    event.stopImmediatePropagation();
  }

  function endObjectDrag(event: PointerEvent) {
    if (event.pointerId !== draggingPointerId) return;

    const canvas = renderer.domElement;
    try {
      if (canvas.hasPointerCapture(event.pointerId)) {
        canvas.releasePointerCapture(event.pointerId);
      }
    } catch {
      // The browser may already have released it.
    }

    draggedRoot = null;
    draggingPointerId = null;
    delete canvas.dataset.grabbingObject;
    canvas.classList.remove('is-grabbing-object');

    event.preventDefault();
    event.stopImmediatePropagation();
  }

  function prepareInteractive(sceneRoot: Object3D) {
    if (interactivePrepared) return;

    interactiveScene = sceneRoot;
    grabbableMeshes = [];

    interactiveScene.traverse((object) => {
      if (object instanceof Mesh) {
        object.castShadow = true;
        object.receiveShadow = true;
        if (findGrabRoot(object)) grabbableMeshes.push(object);
      }

      if (object instanceof Light) object.castShadow = true;
    });

    interactivePrepared = true;
    invalidate();
  }

  onMount(() => {
    const canvas = renderer.domElement;

    canvas.addEventListener('pointerdown', beginObjectDrag, true);
    canvas.addEventListener('pointermove', moveObject, true);
    canvas.addEventListener('pointerup', endObjectDrag, true);
    canvas.addEventListener('pointercancel', endObjectDrag, true);

    new TextureLoader().load(
      space.panoramaUrl!,
      (texture) => {
        texture.colorSpace = SRGBColorSpace;
        displayTexture = texture;
        panoramaMaterial.map = displayTexture;
        panoramaMaterial.needsUpdate = true;

        environmentTexture = texture.clone();
        environmentTexture.colorSpace = SRGBColorSpace;
        environmentTexture.mapping = EquirectangularReflectionMapping;
        environmentTexture.needsUpdate = true;
        scene.environment = environmentTexture;

        invalidate();
        sendReady();
      },
      undefined,
      () => {
        sendReady();
      },
    );

    return () => {
      canvas.removeEventListener('pointerdown', beginObjectDrag, true);
      canvas.removeEventListener('pointermove', moveObject, true);
      canvas.removeEventListener('pointerup', endObjectDrag, true);
      canvas.removeEventListener('pointercancel', endObjectDrag, true);
      delete canvas.dataset.grabbingObject;
      canvas.classList.remove('is-grabbing-object');
    };
  });

  onDestroy(() => {
    renderer.toneMappingExposure = previousExposure;
    renderer.outputColorSpace = previousOutputColorSpace;
    renderer.shadowMap.enabled = previousShadowEnabled;
    renderer.shadowMap.type = previousShadowType;
    scene.background = previousBackground;
    scene.environment = previousEnvironment;

    panoramaGeometry.dispose();
    panoramaMaterial.dispose();
    displayTexture?.dispose();
    environmentTexture?.dispose();
  });
</script>

<PanoramaCamera
  {resetSignal}
  position={CAMERA_POSITION}
  ariaLabel={`Drag to look around. Scroll or pinch to zoom within ${space.title}.`}
/>
<T is={panoramaMesh} />

{#if space.interactiveUrl}
  <InteractiveLayer url={space.interactiveUrl} onPrepared={prepareInteractive} />
{/if}

<SpaceExtras {space} {interactiveScene} />
