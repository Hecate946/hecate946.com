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
    Raycaster,
    RepeatWrapping,
    SphereGeometry,
    SRGBColorSpace,
    Texture,
    TextureLoader,
    Vector2,
    VideoTexture,
    type Material,
    type PerspectiveCamera,
  } from 'three';
  import type {
    ImmersiveModelLayer,
    ImmersivePanoramaView,
    ImmersiveSpace,
  } from './catalog';
  import PanoramaCamera from './PanoramaCamera.svelte';
  import ModelLayer from './ModelLayer.svelte';
  import SpaceExtras from './SpaceExtras.svelte';

  type VideoElementWithFrameCallback = HTMLVideoElement & {
    requestVideoFrameCallback?: (
      callback: (now: number, metadata: unknown) => void,
    ) => number;
    cancelVideoFrameCallback?: (handle: number) => void;
  };

  type OverlayLayer = {
    key: string;
    material: MeshBasicMaterial;
    mesh: Mesh;
    geometry: SphereGeometry;
    posterUrl?: string;
    videoUrl?: string;
    posterTexture: Texture | null;
    videoTexture: VideoTexture | null;
    videoElement: HTMLVideoElement | null;
    videoFrameRequest: number;
    videoAnimationFrame: number;
  };

  export let space: ImmersiveSpace;
  export let onReady: () => void = () => {};
  export let resetSignal = 0;
  export let activeViewId = 'default';
  export let onViewRequest: (viewId: string) => void = () => {};

  const CAMERA_POSITION = space.cameraPosition;
  const MODEL_LAYERS = space.modelLayers;
  const CYCLES_ONLY = space.cyclesOnly === true;
  const PANORAMA_VIEWS: ImmersivePanoramaView[] =
    space.panoramaViews ??
    (space.panoramaUrl
      ? [
          {
            id: 'default',
            label: 'Room view',
            panoramaUrl: space.panoramaUrl,
            panoramaYaw: space.panoramaYaw,
            cameraYaw: space.cameraYaw,
            cameraPitch: 0,
            cameraFov: 96,
          },
        ]
      : []);

  const { renderer, scene, invalidate } = useThrelte();

  const previousExposure = renderer.toneMappingExposure;
  const previousOutputColorSpace = renderer.outputColorSpace;
  const previousShadowEnabled = renderer.shadowMap.enabled;
  const previousShadowType = renderer.shadowMap.type;
  const previousBackground = scene.background;
  const previousEnvironment = scene.environment;

  renderer.toneMappingExposure = 1;
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.shadowMap.enabled = !CYCLES_ONLY;
  renderer.shadowMap.type = PCFSoftShadowMap;
  scene.background = null;
  if (CYCLES_ONLY) scene.environment = null;

  const panoramaGeometry = new SphereGeometry(24, 96, 64);
  panoramaGeometry.scale(-1, 1, 1);

  function createOverlayGeometry(radius: number) {
    const geometry = new SphereGeometry(radius, 96, 64);
    geometry.scale(-1, 1, 1);
    const uv = geometry.getAttribute('uv');
    const overlaySeamInset = 1 / 4096;
    for (let index = 0; index < uv.count; index += 1) {
      const u = uv.getX(index);
      uv.setX(index, overlaySeamInset + u * (1 - overlaySeamInset * 2));
    }
    uv.needsUpdate = true;
    return geometry;
  }

  function createPanoramaMaterial(opacity: number) {
    return new MeshBasicMaterial({
      depthWrite: false,
      toneMapped: false,
      transparent: true,
      opacity,
    });
  }

  function createOverlayLayer(
    key: string,
    radius: number,
    renderOrder: number,
    posterUrl?: string,
    videoUrl?: string,
  ): OverlayLayer {
    const geometry = createOverlayGeometry(radius);
    const material = createPanoramaMaterial(1);
    const mesh = new Mesh(geometry, material);
    mesh.name = `${space.kind}_${space.slug}_Overlay_${key}`;
    mesh.position.set(...CAMERA_POSITION);
    mesh.frustumCulled = false;
    mesh.renderOrder = renderOrder;
    return {
      key,
      material,
      mesh,
      geometry,
      posterUrl,
      videoUrl,
      posterTexture: null,
      videoTexture: null,
      videoElement: null,
      videoFrameRequest: 0,
      videoAnimationFrame: 0,
    };
  }

  const panoramaMaterials = [
    createPanoramaMaterial(1),
    createPanoramaMaterial(0),
  ];
  const panoramaMeshes = panoramaMaterials.map((material, index) => {
    const mesh = new Mesh(panoramaGeometry, material);
    mesh.name = `${space.kind}_${space.slug}_Cycles_Panorama_${index + 1}`;
    mesh.position.set(...CAMERA_POSITION);
    mesh.frustumCulled = false;
    mesh.renderOrder = -1000 + index;
    return mesh;
  });

  const overlayLayers = [
    createOverlayLayer(
      'underwater',
      23.88,
      -996,
      space.panoramaUnderwaterOverlayUrl,
    ),
    createOverlayLayer(
      'caustics',
      23.91,
      -995,
      space.panoramaCausticsOverlayUrl,
      space.panoramaCausticsOverlayVideoUrl,
    ),
    createOverlayLayer(
      'surface',
      23.94,
      -994,
      space.panoramaOverlayUrl,
      space.panoramaOverlayVideoUrl,
    ),
  ].filter((layer) => Boolean(layer.posterUrl || layer.videoUrl));

  const initialView =
    PANORAMA_VIEWS.find((view) => view.id === activeViewId) ??
    PANORAMA_VIEWS[0];
  if (initialView) {
    panoramaMeshes[0].rotation.y = initialView.panoramaYaw;
    for (const layer of overlayLayers) layer.mesh.rotation.y = initialView.panoramaYaw;
  }

  let activeView = initialView;
  let displayedViewId = initialView?.id ?? '';
  let previousActiveViewId = activeViewId;
  let activeMeshIndex = 0;
  let crossfadeFrame = 0;
  let readySent = false;
  let interactiveScene: Object3D | null = null;
  let clickTargetMeshes: Mesh[] = [];
  let clickStart:
    | { pointerId: number; x: number; y: number }
    | null = null;

  const textures = new Map<string, Texture>();
  let environmentTexture: Texture | null = null;
  const requiredAssetKeys = new Set([
    ...(initialView ? [`view:${initialView.id}`] : []),
    ...MODEL_LAYERS.map((layer) => `model:${layer.id}`),
  ]);
  const readyAssetKeys = new Set<string>();
  const preparedLayerIds = new Set<string>();
  const raycaster = new Raycaster();
  const pointer = new Vector2();

  function sendReady() {
    if (readySent) return;
    readySent = true;
    onReady();
  }

  function markAssetReady(key: string) {
    readyAssetKeys.add(key);
    if (readyAssetKeys.size >= requiredAssetKeys.size) sendReady();
  }

  function attachOverlayTexture(layer: OverlayLayer, texture: Texture) {
    texture.wrapS = RepeatWrapping;
    texture.needsUpdate = true;
    layer.material.map = texture;
    layer.material.needsUpdate = true;
    invalidate();
  }

  function stopOverlayVideoRenderLoop(layer: OverlayLayer) {
    const video = layer.videoElement as VideoElementWithFrameCallback | null;
    if (video && layer.videoFrameRequest) {
      video.cancelVideoFrameCallback?.(layer.videoFrameRequest);
    }
    layer.videoFrameRequest = 0;

    if (layer.videoAnimationFrame) cancelAnimationFrame(layer.videoAnimationFrame);
    layer.videoAnimationFrame = 0;
  }

  function startOverlayVideoRenderLoop(layer: OverlayLayer, videoElement: HTMLVideoElement) {
    stopOverlayVideoRenderLoop(layer);
    const video = videoElement as VideoElementWithFrameCallback;

    if (video.requestVideoFrameCallback) {
      const redrawOnVideoFrame = () => {
        invalidate();
        layer.videoFrameRequest =
          video.requestVideoFrameCallback?.(redrawOnVideoFrame) ?? 0;
      };
      layer.videoFrameRequest = video.requestVideoFrameCallback(redrawOnVideoFrame);
      return;
    }

    const redrawWhilePlaying = () => {
      if (!video.paused && !video.ended) invalidate();
      layer.videoAnimationFrame = requestAnimationFrame(redrawWhilePlaying);
    };
    layer.videoAnimationFrame = requestAnimationFrame(redrawWhilePlaying);
  }

  function activeCamera() {
    return scene.getObjectByName('PanoramaCamera') as
      | PerspectiveCamera
      | undefined;
  }

  function updatePointer(event: PointerEvent) {
    const bounds = renderer.domElement.getBoundingClientRect();
    pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
    pointer.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
  }

  function findViewRoot(object: Object3D | null): Object3D | null {
    let current = object;
    while (current) {
      if (
        current.userData?.interaction === 'view' &&
        typeof current.userData?.view_id === 'string'
      ) {
        return current;
      }
      current = current.parent;
    }
    return null;
  }

  function hideMaterial(material: Material | Material[]) {
    const materials = Array.isArray(material) ? material : [material];
    for (const entry of materials) entry.visible = false;
  }

  function raycastViewTarget(event: PointerEvent) {
    if (clickTargetMeshes.length === 0) return null;
    const camera = activeCamera();
    if (!camera) return null;

    updatePointer(event);
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObjects(clickTargetMeshes, true)[0];
    return findViewRoot(hit?.object ?? null);
  }

  function prepareModelLayer(layer: ImmersiveModelLayer, sceneRoot: Object3D) {
    if (preparedLayerIds.has(layer.id)) return;
    preparedLayerIds.add(layer.id);

    sceneRoot.traverse((object) => {
      if (object instanceof Light && CYCLES_ONLY) {
        object.visible = false;
        return;
      }

      if (!(object instanceof Mesh)) return;

      const viewRoot = findViewRoot(object);
      if (viewRoot) {
        clickTargetMeshes.push(object);
        object.castShadow = false;
        object.receiveShadow = false;
        hideMaterial(object.material);
        return;
      }

      object.castShadow = layer.role === 'objects';
      object.receiveShadow = true;
    });

    if (layer.role === 'objects' && !interactiveScene) {
      interactiveScene = sceneRoot;
    }

    invalidate();
    markAssetReady(`model:${layer.id}`);
  }

  function normalizeCrossfadeState() {
    const firstOpacity = panoramaMaterials[0].opacity;
    const secondOpacity = panoramaMaterials[1].opacity;
    activeMeshIndex = firstOpacity >= secondOpacity ? 0 : 1;
    panoramaMaterials[activeMeshIndex].opacity = 1;
    panoramaMaterials[1 - activeMeshIndex].opacity = 0;
  }

  function transitionToView(viewId: string) {
    const nextView = PANORAMA_VIEWS.find((view) => view.id === viewId);
    if (!nextView) return;
    activeView = nextView;

    const texture = textures.get(nextView.id);
    if (!texture || displayedViewId === nextView.id) {
      invalidate();
      return;
    }

    if (crossfadeFrame) cancelAnimationFrame(crossfadeFrame);
    crossfadeFrame = 0;
    normalizeCrossfadeState();

    const fromIndex = activeMeshIndex;
    const toIndex = 1 - fromIndex;
    const fromMaterial = panoramaMaterials[fromIndex];
    const toMaterial = panoramaMaterials[toIndex];
    const toMesh = panoramaMeshes[toIndex];

    toMaterial.map = texture;
    toMaterial.needsUpdate = true;
    toMaterial.opacity = 0;
    toMesh.rotation.y = nextView.panoramaYaw;
    for (const layer of overlayLayers) layer.mesh.rotation.y = nextView.panoramaYaw;
    toMesh.renderOrder = -999;
    panoramaMeshes[fromIndex].renderOrder = -1000;

    const duration = 700;
    const started = performance.now();

    function animate(now: number) {
      const progress = Math.min((now - started) / duration, 1);
      const eased = progress * progress * (3 - 2 * progress);
      fromMaterial.opacity = 1;
      toMaterial.opacity = eased;
      invalidate();

      if (progress < 1) {
        crossfadeFrame = requestAnimationFrame(animate);
        return;
      }

      crossfadeFrame = 0;
      fromMaterial.opacity = 0;
      toMaterial.opacity = 1;
      activeMeshIndex = toIndex;
      displayedViewId = nextView.id;
      invalidate();
    }

    crossfadeFrame = requestAnimationFrame(animate);
  }

  $: activeView =
    PANORAMA_VIEWS.find((view) => view.id === activeViewId) ??
    PANORAMA_VIEWS[0];

  $: if (activeViewId !== previousActiveViewId) {
    previousActiveViewId = activeViewId;
    transitionToView(activeViewId);
  }

  onMount(() => {
    const canvas = renderer.domElement;

    function handlePointerDown(event: PointerEvent) {
      if (event.pointerType === 'mouse' && event.button !== 0) return;
      clickStart = {
        pointerId: event.pointerId,
        x: event.clientX,
        y: event.clientY,
      };
    }

    function handlePointerMove(event: PointerEvent) {
      if (event.pointerType !== 'mouse' || event.buttons !== 0) return;
      const target = activeViewId === 'default' ? raycastViewTarget(event) : null;
      canvas.classList.toggle('is-clickable', Boolean(target));
    }

    function handlePointerUp(event: PointerEvent) {
      const start = clickStart;
      clickStart = null;
      if (!start || start.pointerId !== event.pointerId) return;
      if (activeViewId !== 'default') return;

      const distance = Math.hypot(
        event.clientX - start.x,
        event.clientY - start.y,
      );
      if (distance > 7) return;

      const target = raycastViewTarget(event);
      const viewId = target?.userData?.view_id;
      if (
        typeof viewId === 'string' &&
        PANORAMA_VIEWS.some((view) => view.id === viewId)
      ) {
        onViewRequest(viewId);
        event.preventDefault();
      }
    }

    function clearPointerState() {
      clickStart = null;
      canvas.classList.remove('is-clickable');
    }

    canvas.addEventListener('pointerdown', handlePointerDown, true);
    canvas.addEventListener('pointermove', handlePointerMove, true);
    canvas.addEventListener('pointerup', handlePointerUp, true);
    canvas.addEventListener('pointercancel', clearPointerState, true);
    canvas.addEventListener('pointerleave', clearPointerState, true);

    for (const view of PANORAMA_VIEWS) {
      new TextureLoader().load(
        view.panoramaUrl,
        (texture) => {
          texture.colorSpace = SRGBColorSpace;
          textures.set(view.id, texture);

          if (view.id === displayedViewId) {
            panoramaMaterials[activeMeshIndex].map = texture;
            panoramaMaterials[activeMeshIndex].needsUpdate = true;
          }

          if (!CYCLES_ONLY && view.id === initialView?.id) {
            environmentTexture?.dispose();
            environmentTexture = texture.clone();
            environmentTexture.colorSpace = SRGBColorSpace;
            environmentTexture.mapping = EquirectangularReflectionMapping;
            environmentTexture.needsUpdate = true;
            scene.environment = environmentTexture;
          }

          if (view.id === initialView?.id) markAssetReady(`view:${view.id}`);
          if (view.id === activeViewId && view.id !== displayedViewId) {
            transitionToView(view.id);
          }
          invalidate();
        },
        undefined,
        () => {
          if (view.id === initialView?.id) markAssetReady(`view:${view.id}`);
        },
      );
    }

    for (const layer of overlayLayers) {
      if (layer.posterUrl) {
        new TextureLoader().load(
          layer.posterUrl,
          (texture) => {
            texture.colorSpace = SRGBColorSpace;
            layer.posterTexture?.dispose();
            layer.posterTexture = texture;
            attachOverlayTexture(layer, texture);
          },
          undefined,
          () => {
            layer.material.map = null;
            layer.material.needsUpdate = true;
            invalidate();
          },
        );
      }

      if (layer.videoUrl) {
        const video = document.createElement('video');
        layer.videoElement = video;
        video.src = layer.videoUrl;
        video.crossOrigin = 'anonymous';
        video.loop = true;
        video.muted = true;
        video.playsInline = true;
        video.autoplay = true;
        video.preload = 'auto';

        const handleCanPlay = () => {
          layer.videoTexture?.dispose();
          layer.videoTexture = new VideoTexture(video);
          layer.videoTexture.colorSpace = SRGBColorSpace;
          attachOverlayTexture(layer, layer.videoTexture);

          void video
            .play()
            .then(() => {
              startOverlayVideoRenderLoop(layer, video);
            })
            .catch(() => {
              /* poster fallback remains active if autoplay is blocked */
            });
        };

        video.addEventListener('canplay', handleCanPlay, { once: true });
        video.load();
      }
    }

    if (requiredAssetKeys.size === 0) sendReady();

    return () => {
      canvas.removeEventListener('pointerdown', handlePointerDown, true);
      canvas.removeEventListener('pointermove', handlePointerMove, true);
      canvas.removeEventListener('pointerup', handlePointerUp, true);
      canvas.removeEventListener('pointercancel', clearPointerState, true);
      canvas.removeEventListener('pointerleave', clearPointerState, true);
      canvas.classList.remove('is-clickable');
    };
  });

  onDestroy(() => {
    if (crossfadeFrame) cancelAnimationFrame(crossfadeFrame);

    renderer.toneMappingExposure = previousExposure;
    renderer.outputColorSpace = previousOutputColorSpace;
    renderer.shadowMap.enabled = previousShadowEnabled;
    renderer.shadowMap.type = previousShadowType;
    scene.background = previousBackground;
    scene.environment = previousEnvironment;

    panoramaGeometry.dispose();
    for (const material of panoramaMaterials) material.dispose();
    for (const texture of textures.values()) texture.dispose();
    for (const layer of overlayLayers) {
      stopOverlayVideoRenderLoop(layer);
      layer.videoElement?.pause();
      if (layer.videoElement) {
        layer.videoElement.removeAttribute('src');
        layer.videoElement.load();
      }
      layer.videoTexture?.dispose();
      layer.posterTexture?.dispose();
      layer.material.dispose();
      layer.geometry.dispose();
    }
    environmentTexture?.dispose();
  });
</script>

{#if activeView}
  <PanoramaCamera
    {resetSignal}
    viewSignal={activeView.id}
    position={CAMERA_POSITION}
    initialYaw={activeView.cameraYaw}
    initialPitch={activeView.cameraPitch}
    initialFov={activeView.cameraFov}
    ariaLabel={`Drag to look around. Scroll or pinch to zoom within ${activeView.label}.`}
  />
{:else}
  <PanoramaCamera
    {resetSignal}
    position={CAMERA_POSITION}
    initialYaw={space.cameraYaw}
    ariaLabel={`Drag to look around. Scroll or pinch to zoom within ${space.title}.`}
  />
{/if}

{#if PANORAMA_VIEWS.length > 0}
  <T is={panoramaMeshes[0]} />
  <T is={panoramaMeshes[1]} />
  {#each overlayLayers as layer (layer.key)}
    <T is={layer.mesh} />
  {/each}
{:else}
  <T.AmbientLight intensity={0.9} />
  <T.PointLight
    position={[0, 4.6, 0]}
    intensity={180}
    distance={20}
    decay={2}
    castShadow
  />
{/if}

{#each MODEL_LAYERS as layer (layer.id)}
  <ModelLayer {layer} onPrepared={prepareModelLayer} />
{/each}

<SpaceExtras {space} {interactiveScene} />
