<script lang="ts">
  import { onMount } from 'svelte';
  import * as THREE from 'three';
  import { WORLD_MAP_PATH } from '@/data/world-map';
  import { WORLD_INTERNAL_BORDERS_PATH } from '@/data/world-internal-borders';

  export let apiBase = '';

  interface VisitorLocation {
    city: string | null;
    region: string | null;
    country: string | null;
    countryCode: string | null;
    latitude: number;
    longitude: number;
    pageViews: number;
    estimatedVisitors: number;
    pointIndex?: number;
    pointCount?: number;
  }

  interface LiveStats {
    summary: {
      estimatedVisitors: number;
      updatedAt: string | null;
    };
    locations: VisitorLocation[];
  }

  interface GlobeMarker {
    latitude: number;
    longitude: number;
    count: number;
    label: string;
  }

  interface PointerPoint {
    x: number;
    y: number;
  }

  interface PinchState {
    distance: number;
    cameraZ: number;
  }

  const GLOBE_RADIUS = 2.35;
  const MARKER_RADIUS = GLOBE_RADIUS + 0.038;
  const MIN_CAMERA_Z = 3.55;
  const MAX_CAMERA_Z = 9.5;
  const INITIAL_CAMERA_Z = 6.45;
  const BASE_WORLD_TEXTURE_WIDTH = 4096;
  const WORLD_TEXTURE_WIDTH = 8192;
  const WORLD_TEXTURE_HEIGHT = 4096;
  // Keep the globe artwork visually identical to the 2D /stats map.
  const LAND_FILL_OPACITY = 0.12;
  const COASTLINE_OPACITY = 0.42;
  const COUNTRY_BORDER_OPACITY = 0.52;

  let shell!: HTMLDivElement;
  let canvas!: HTMLCanvasElement;
  let loading = true;
  let error = '';
  let visitorCount = 0;
  let updatedAt: string | null = null;
  let tooltipVisible = false;
  let tooltipX = 0;
  let tooltipY = 0;
  let tooltipText = '';

  let resetGlobe: (() => void) | null = null;

  function clamp(value: number, minimum: number, maximum: number) {
    return Math.min(maximum, Math.max(minimum, value));
  }


  function zoomFromSurfaceDistance(cameraZ: number, ratio: number) {
    // Zoom the distance from the camera to the globe surface, rather than the
    // distance to the globe center. Close-up zoom steps therefore become
    // naturally finer while wide-view steps remain efficient.
    const surfaceDistance = Math.max(0.08, cameraZ - GLOBE_RADIUS);
    return clamp(
      GLOBE_RADIUS + surfaceDistance * ratio,
      MIN_CAMERA_Z,
      MAX_CAMERA_Z,
    );
  }

  function locationLabel(location: VisitorLocation) {
    return [location.city, location.region, location.country]
      .filter(Boolean)
      .join(', ') || 'Approximate visitor location';
  }

  function groupLocations(locations: VisitorLocation[]): GlobeMarker[] {
    const groups = new Map<string, GlobeMarker>();

    for (const location of locations) {
      if (
        !Number.isFinite(location.latitude) ||
        !Number.isFinite(location.longitude)
      ) {
        continue;
      }

      const key = `${location.latitude.toFixed(5)}:${location.longitude.toFixed(5)}`;
      const existing = groups.get(key);

      if (existing) {
        existing.count += 1;
        continue;
      }

      groups.set(key, {
        latitude: location.latitude,
        longitude: location.longitude,
        count: 1,
        label: locationLabel(location),
      });
    }

    return [...groups.values()];
  }

  function markerPosition(latitude: number, longitude: number, radius: number) {
    const phi = THREE.MathUtils.degToRad(90 - latitude);
    const theta = THREE.MathUtils.degToRad(longitude + 180);

    return new THREE.Vector3(
      -radius * Math.sin(phi) * Math.cos(theta),
      radius * Math.cos(phi),
      radius * Math.sin(phi) * Math.sin(theta),
    );
  }

  function readThemeColors() {
    const styles = getComputedStyle(document.documentElement);

    return {
      text: styles.getPropertyValue('--text').trim() || '#242421',
      background: styles.getPropertyValue('--bg').trim() || '#ffffff',
      accent:
        styles.getPropertyValue('--accent-strong').trim() ||
        styles.getPropertyValue('--text').trim() ||
        '#242421',
    };
  }

  async function makeWorldTexture(renderer: THREE.WebGLRenderer) {
    const colors = readThemeColors();
    const textureWidth = Math.min(
      WORLD_TEXTURE_WIDTH,
      renderer.capabilities.maxTextureSize,
    );
    const textureHeight = Math.min(
      WORLD_TEXTURE_HEIGHT,
      Math.floor(textureWidth / 2),
    );
    const textureScale = textureWidth / BASE_WORLD_TEXTURE_WIDTH;
    const coastlineStrokeWidth = 0.75 * textureScale;
    const countryStrokeWidth = 0.52 * textureScale;
    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 500" width="${textureWidth}" height="${textureHeight}">
        <path
          d="${WORLD_MAP_PATH}"
          fill="${colors.text}"
          fill-opacity="${LAND_FILL_OPACITY}"
          stroke="${colors.text}"
          stroke-opacity="${COASTLINE_OPACITY}"
          stroke-width="${coastlineStrokeWidth}"
          vector-effect="non-scaling-stroke"
        />
        <path
          d="${WORLD_INTERNAL_BORDERS_PATH}"
          fill="none"
          stroke="${colors.text}"
          stroke-opacity="${COUNTRY_BORDER_OPACITY}"
          stroke-width="${countryStrokeWidth}"
          vector-effect="non-scaling-stroke"
        />
      </svg>
    `;

    const blob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    try {
      const image = await new Promise<HTMLImageElement>((resolve, reject) => {
        const nextImage = new Image();
        nextImage.onload = () => resolve(nextImage);
        nextImage.onerror = () => reject(new Error('Unable to render world texture.'));
        nextImage.src = url;
      });

      const textureCanvas = document.createElement('canvas');
      textureCanvas.width = textureWidth;
      textureCanvas.height = textureHeight;
      const context = textureCanvas.getContext('2d', { alpha: true });
      if (!context) throw new Error('Unable to create world texture canvas.');

      context.clearRect(0, 0, textureWidth, textureHeight);
      context.drawImage(image, 0, 0, textureWidth, textureHeight);

      const texture = new THREE.CanvasTexture(textureCanvas);
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.wrapS = THREE.RepeatWrapping;
      texture.wrapT = THREE.ClampToEdgeWrapping;
      texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
      texture.minFilter = THREE.LinearMipmapLinearFilter;
      texture.magFilter = THREE.LinearFilter;
      texture.generateMipmaps = true;
      texture.needsUpdate = true;
      return texture;
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  function readableTime(value: string | null) {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.valueOf())) return '';
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    }).format(date);
  }

  function enableSphericalTextureLookup(material: THREE.MeshBasicMaterial) {
    // SphereGeometry's interpolated UVs collapse at the poles. Sampling the
    // equirectangular map through those UVs stretches a few texture pixels into
    // a visible polar cap/hole. Instead, derive longitude/latitude from the actual
    // local surface position for every fragment, then sample the exact same map.
    material.onBeforeCompile = (shader) => {
      shader.vertexShader = `varying vec3 vGlobeLocalPosition;\n${shader.vertexShader}`
        .replace(
          '#include <begin_vertex>',
          '#include <begin_vertex>\n  vGlobeLocalPosition = position;',
        );

      shader.fragmentShader = `
        varying vec3 vGlobeLocalPosition;
        const float GLOBE_PI = 3.1415926535897932384626433832795;
        ${shader.fragmentShader}
      `.replace(
        '#include <map_fragment>',
        `
          #ifdef USE_MAP
            vec3 globeDirection = normalize(vGlobeLocalPosition);
            float globeLongitude = atan(globeDirection.z, -globeDirection.x);
            float globeU = globeLongitude / (2.0 * GLOBE_PI);
            if (globeU < 0.0) globeU += 1.0;
            float globeLatitude = asin(clamp(globeDirection.y, -1.0, 1.0));
            float globeV = globeLatitude / GLOBE_PI + 0.5;
            vec4 sampledDiffuseColor = texture2D(map, vec2(globeU, globeV));
            diffuseColor *= sampledDiffuseColor;
          #endif
        `,
      );
    };

    material.customProgramCacheKey = () => 'visitor-globe-spherical-texture-v2';
  }

  onMount(() => {
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
    camera.position.set(0, 0, INITIAL_CAMERA_Z);

    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2.5));
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;

    const globeGroup = new THREE.Group();
    globeGroup.rotation.set(-0.12, -0.58, 0);
    scene.add(globeGroup);

    // The globe has no ocean/base-sphere fill. Only the same translucent land,
    // coastlines and country borders used by /stats are visible. The map is sampled
    // from true spherical longitude/latitude rather than SphereGeometry UVs, which
    // prevents the equirectangular texture from smearing into a cap at the poles.
    const globeGeometry = new THREE.SphereGeometry(GLOBE_RADIUS, 192, 128);
    const globeMaterial = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 1,
      alphaTest: 0.001,
      depthWrite: false,
      side: THREE.FrontSide,
    });
    enableSphericalTextureLookup(globeMaterial);
    const globe = new THREE.Mesh(globeGeometry, globeMaterial);
    globe.renderOrder = 0;
    globeGroup.add(globe);

    const markerGeometry = new THREE.CircleGeometry(0.045, 24);
    const markerOutlineGeometry = new THREE.CircleGeometry(0.059, 24);
    let markerMaterial = new THREE.MeshBasicMaterial({
      color: readThemeColors().accent,
      side: THREE.FrontSide,
    });
    let markerOutlineMaterial = new THREE.MeshBasicMaterial({
      color: readThemeColors().background,
      side: THREE.FrontSide,
    });
    let markerMesh: THREE.InstancedMesh | null = null;
    let markerOutlineMesh: THREE.InstancedMesh | null = null;
    let markerMetadata: GlobeMarker[] = [];
    let markerPositions: THREE.Vector3[] = [];
    let markerQuaternions: THREE.Quaternion[] = [];
    let markerBaseScales: number[] = [];
    let lastMarkerCameraZ = Number.NaN;

    const raycaster = new THREE.Raycaster();
    const pointerNdc = new THREE.Vector2();
    const activePointers = new Map<number, PointerPoint>();
    let dragLocalVector: THREE.Vector3 | null = null;
    let pinchState: PinchState | null = null;
    let dragging = false;
    let targetCameraZ = INITIAL_CAMERA_Z;
    const inertiaAxis = new THREE.Vector3(0, 1, 0);
    let inertiaAngle = 0;
    let disposed = false;
    let currentTexture: THREE.Texture | null = null;

    function disposeMarkerMesh() {
      if (markerMesh) {
        globeGroup.remove(markerMesh);
        markerMesh = null;
      }
      if (markerOutlineMesh) {
        globeGroup.remove(markerOutlineMesh);
        markerOutlineMesh = null;
      }
      markerPositions = [];
      markerQuaternions = [];
      markerBaseScales = [];
      lastMarkerCameraZ = Number.NaN;
    }

    function markerZoomCompensation(cameraZ: number) {
      // Keep dots visually small while zooming toward the globe. The marker
      // radius shrinks with the camera-to-surface distance, approximately
      // cancelling perspective magnification near the visible hemisphere.
      const initialSurfaceDistance = INITIAL_CAMERA_Z - MARKER_RADIUS;
      const currentSurfaceDistance = Math.max(0.2, cameraZ - MARKER_RADIUS);
      return clamp(currentSurfaceDistance / initialSurfaceDistance, 0.16, 1);
    }

    function updateMarkerMatrices(cameraZ: number, force = false) {
      if (!markerMesh || !markerOutlineMesh || markerMetadata.length === 0) return;
      if (!force && Number.isFinite(lastMarkerCameraZ) && Math.abs(cameraZ - lastMarkerCameraZ) < 0.001) return;

      lastMarkerCameraZ = cameraZ;
      const zoomScale = markerZoomCompensation(cameraZ);
      const dummy = new THREE.Object3D();
      const outward = new THREE.Vector3();

      markerMetadata.forEach((_, index) => {
        const position = markerPositions[index];
        const quaternion = markerQuaternions[index];
        const scale = markerBaseScales[index] * zoomScale;
        if (!position || !quaternion || !Number.isFinite(scale)) return;

        outward.copy(position).normalize();
        dummy.position.copy(position);
        dummy.quaternion.copy(quaternion);
        dummy.scale.setScalar(scale);
        dummy.updateMatrix();
        markerOutlineMesh?.setMatrixAt(index, dummy.matrix);

        // Lift the accent circle a fraction above its background ring to avoid
        // z-fighting while preserving the 2D map's bordered-dot appearance.
        dummy.position.copy(position).addScaledVector(outward, 0.0025);
        dummy.updateMatrix();
        markerMesh?.setMatrixAt(index, dummy.matrix);
      });

      markerOutlineMesh.instanceMatrix.needsUpdate = true;
      markerMesh.instanceMatrix.needsUpdate = true;
    }

    function setMarkers(locations: VisitorLocation[]) {
      markerMetadata = groupLocations(locations);
      disposeMarkerMesh();

      if (markerMetadata.length === 0) return;

      markerOutlineMesh = new THREE.InstancedMesh(
        markerOutlineGeometry,
        markerOutlineMaterial,
        markerMetadata.length,
      );
      markerOutlineMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      markerOutlineMesh.userData.kind = 'visitor-marker-outlines';

      markerMesh = new THREE.InstancedMesh(
        markerGeometry,
        markerMaterial,
        markerMetadata.length,
      );
      markerMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      markerMesh.userData.kind = 'visitor-markers';

      const circleNormal = new THREE.Vector3(0, 0, 1);

      markerPositions = markerMetadata.map((marker) =>
        markerPosition(marker.latitude, marker.longitude, MARKER_RADIUS),
      );
      markerQuaternions = markerPositions.map((position) =>
        new THREE.Quaternion().setFromUnitVectors(
          circleNormal,
          position.clone().normalize(),
        ),
      );
      markerBaseScales = markerMetadata.map(
        (marker) => 0.72 + Math.min(1.35, Math.log2(marker.count + 1) * 0.24),
      );

      globeGroup.add(markerOutlineMesh);
      globeGroup.add(markerMesh);
      updateMarkerMatrices(camera.position.z, true);
    }

    async function updateTheme() {
      try {
        const nextTexture = await makeWorldTexture(renderer);
        if (disposed) {
          nextTexture.dispose();
          return;
        }

        currentTexture?.dispose();
        currentTexture = nextTexture;
        globeMaterial.map = nextTexture;
        globeMaterial.needsUpdate = true;

        const colors = readThemeColors();
        markerMaterial.color.set(colors.accent);
        markerOutlineMaterial.color.set(colors.background);
      } catch (textureError) {
        console.error(textureError);
      }
    }

    async function loadStats() {
      const base = apiBase.trim().replace(/\/$/, '');
      if (!base) {
        loading = false;
        error = 'Live analytics are not configured.';
        return;
      }

      try {
        const response = await fetch(`${base}/api/stats?days=30`, {
          headers: { Accept: 'application/json' },
          cache: 'no-store',
        });
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);

        const data = (await response.json()) as LiveStats;
        if (disposed) return;
        visitorCount = data.summary.estimatedVisitors ?? data.locations.length;
        updatedAt = data.summary.updatedAt;
        setMarkers(data.locations ?? []);
        error = '';
      } catch (statsError) {
        if (disposed) return;
        error = `Visitor data unavailable${
          statsError instanceof Error ? `: ${statsError.message}` : '.'
        }`;
      } finally {
        if (!disposed) loading = false;
      }
    }

    function resize() {
      const bounds = shell.getBoundingClientRect();
      const width = Math.max(1, bounds.width);
      const height = Math.max(1, bounds.height);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    }

    function pointerDistance() {
      const points = [...activePointers.values()];
      if (points.length < 2) return 0;
      return Math.hypot(points[1].x - points[0].x, points[1].y - points[0].y);
    }

    const dragSphere = new THREE.Sphere(new THREE.Vector3(0, 0, 0), GLOBE_RADIUS);
    const dragHit = new THREE.Vector3();
    const dragDesired = new THREE.Vector3();
    const dragExact = new THREE.Vector3();
    const dragContinuation = new THREE.Vector3();
    const dragCurrent = new THREE.Vector3();
    const dragDelta = new THREE.Quaternion();
    const dragEdgeAxis = new THREE.Vector3();
    const dragEdgeQuaternion = new THREE.Quaternion();
    const dragCameraRight = new THREE.Vector3();
    const dragCameraUp = new THREE.Vector3();

    function setRayFromClient(clientX: number, clientY: number, bounds: DOMRect) {
      pointerNdc.x = ((clientX - bounds.left) / bounds.width) * 2 - 1;
      pointerNdc.y = -((clientY - bounds.top) / bounds.height) * 2 + 1;
      raycaster.setFromCamera(pointerNdc, camera);
    }

    function pointerSurfaceVector(clientX: number, clientY: number) {
      const bounds = canvas.getBoundingClientRect();
      setRayFromClient(clientX, clientY, bounds);

      const hit = raycaster.ray.intersectSphere(dragSphere, dragHit);
      if (hit) dragExact.copy(hit).normalize();

      const centerX = bounds.left + bounds.width / 2;
      const centerY = bounds.top + bounds.height / 2;
      const dx = clientX - centerX;
      const dy = clientY - centerY;
      const radialPixels = Math.hypot(dx, dy);

      if (radialPixels < 0.0001) {
        return hit ? dragDesired.copy(dragExact) : dragDesired.set(0, 0, 1);
      }

      const focalPixels =
        bounds.height /
        (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2));
      const denominator = Math.sqrt(
        Math.max(0.0001, camera.position.z ** 2 - GLOBE_RADIUS ** 2),
      );
      const projectedRadius = Math.max(1, (focalPixels * GLOBE_RADIUS) / denominator);

      // The ray/sphere mapping is perfectly 1:1 across the face, but its rate of
      // change becomes extremely steep as the ray approaches the silhouette. The
      // outside continuation is position-continuous at the rim, yet that derivative
      // mismatch can still feel like a tiny snap. Keep exact 1:1 grabbing over
      // almost the whole globe, then use a narrow screen-space soft rim to converge
      // smoothly onto the continuation before the cursor actually crosses the edge.
      const rimBlendPixels = clamp(projectedRadius * 0.035, 10, 24);
      const rimBlendStart = projectedRadius - rimBlendPixels;
      if (hit && radialPixels <= rimBlendStart) {
        return dragDesired.copy(dragExact);
      }

      // Sample the true perspective silhouette in this radial direction. For an
      // inside pointer we deliberately project *outward* to the rim; for an outside
      // pointer we project inward. Keeping this one edge anchor on both sides is what
      // makes the continuation geometrically continuous.
      const edgeScale = (projectedRadius * 0.999999) / radialPixels;
      const edgeX = centerX + dx * edgeScale;
      const edgeY = centerY + dy * edgeScale;
      setRayFromClient(edgeX, edgeY, bounds);

      const edgeHit = raycaster.ray.intersectSphere(dragSphere, dragHit);
      if (!edgeHit) {
        // Extremely defensive fallback for tangent precision. Prefer the exact hit
        // when one exists; otherwise fall back to a normalized view-space rim point.
        if (hit) return dragDesired.copy(dragExact);
        return dragDesired.set(dx, -dy, projectedRadius).normalize();
      }

      dragContinuation.copy(edgeHit).normalize();

      const screenX = dx / radialPixels;
      const screenY = -dy / radialPixels;
      dragCameraRight.set(1, 0, 0).applyQuaternion(camera.quaternion);
      dragCameraUp.set(0, 1, 0).applyQuaternion(camera.quaternion);
      dragEdgeAxis
        .copy(dragCameraRight)
        .multiplyScalar(-screenY)
        .addScaledVector(dragCameraUp, screenX)
        .normalize();

      // Signed distance from the silhouette: negative just inside, positive outside.
      // The same tangent continuation is therefore valid on both sides of the rim.
      dragEdgeQuaternion.setFromAxisAngle(
        dragEdgeAxis,
        (radialPixels - projectedRadius) / projectedRadius,
      );
      dragContinuation.applyQuaternion(dragEdgeQuaternion).normalize();

      if (!hit || radialPixels >= projectedRadius) {
        return dragDesired.copy(dragContinuation);
      }

      // Quintic smootherstep has zero first *and* second derivative at both ends.
      // That suppresses the last perceptible velocity kink while making the soft
      // region visually impossible to distinguish from the exact sphere grab.
      const t = clamp(
        (radialPixels - rimBlendStart) / rimBlendPixels,
        0,
        1,
      );
      const smoothT = t * t * t * (t * (t * 6 - 15) + 10);

      return dragDesired
        .copy(dragExact)
        .lerp(dragContinuation, smoothT)
        .normalize();
    }

    function beginSinglePointerDrag(point: PointerPoint) {
      const worldVector = pointerSurfaceVector(point.x, point.y);
      const inverseRotation = globeGroup.quaternion.clone().invert();
      dragLocalVector = worldVector.clone().applyQuaternion(inverseRotation).normalize();
      dragging = true;
      inertiaAngle = 0;
    }

    function beginPinch() {
      const distance = pointerDistance();
      if (distance <= 0) return;
      pinchState = { distance, cameraZ: targetCameraZ };
      dragLocalVector = null;
      dragging = false;
      inertiaAngle = 0;
    }

    function onPointerDown(event: PointerEvent) {
      canvas.setPointerCapture(event.pointerId);
      activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      tooltipVisible = false;

      if (activePointers.size >= 2) {
        beginPinch();
        return;
      }

      beginSinglePointerDrag({ x: event.clientX, y: event.clientY });
    }

    function onPointerMove(event: PointerEvent) {
      if (activePointers.has(event.pointerId)) {
        activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      }

      if (activePointers.size >= 2 && pinchState) {
        const distance = pointerDistance();
        if (distance > 0) {
          targetCameraZ = zoomFromSurfaceDistance(
            pinchState.cameraZ,
            pinchState.distance / distance,
          );
        }
        return;
      }

      if (dragging && dragLocalVector && activePointers.size === 1) {
        const desiredWorld = pointerSurfaceVector(event.clientX, event.clientY);
        dragCurrent.copy(dragLocalVector).applyQuaternion(globeGroup.quaternion).normalize();
        dragDelta.setFromUnitVectors(dragCurrent, desiredWorld);
        globeGroup.quaternion.premultiply(dragDelta).normalize();

        // Preserve only a restrained trace of the final physical motion on
        // release. While held, the surface point itself follows 1:1.
        const halfSin = Math.sqrt(Math.max(0, 1 - dragDelta.w * dragDelta.w));
        const angle = 2 * Math.acos(clamp(dragDelta.w, -1, 1));
        if (halfSin > 0.00001 && Number.isFinite(angle)) {
          inertiaAxis.set(
            dragDelta.x / halfSin,
            dragDelta.y / halfSin,
            dragDelta.z / halfSin,
          ).normalize();
          inertiaAngle = Math.min(0.045, angle * 0.28);
        }
        return;
      }

      if (event.buttons === 0 && markerMesh) {
        const bounds = canvas.getBoundingClientRect();
        pointerNdc.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
        pointerNdc.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
        raycaster.setFromCamera(pointerNdc, camera);
        const intersection = raycaster.intersectObject(markerMesh, false)[0];
        const instanceId = intersection?.instanceId;

        if (typeof instanceId === 'number' && markerMetadata[instanceId]) {
          const marker = markerMetadata[instanceId];
          tooltipText = `${marker.label}${marker.count > 1 ? ` · ${marker.count} visitors` : ''}`;
          tooltipX = event.clientX - bounds.left;
          tooltipY = event.clientY - bounds.top;
          tooltipVisible = true;
          canvas.style.cursor = 'pointer';
        } else {
          tooltipVisible = false;
          canvas.style.cursor = 'grab';
        }
      }
    }

    function onPointerUp(event: PointerEvent) {
      activePointers.delete(event.pointerId);
      if (canvas.hasPointerCapture(event.pointerId)) {
        canvas.releasePointerCapture(event.pointerId);
      }

      if (activePointers.size >= 2) {
        beginPinch();
        return;
      }

      pinchState = null;
      if (activePointers.size === 1) {
        const point = [...activePointers.values()][0];
        beginSinglePointerDrag(point);
      } else {
        dragging = false;
        dragLocalVector = null;
      }
    }

    function onWheel(event: WheelEvent) {
      event.preventDefault();

      const pixelDelta =
        event.deltaMode === WheelEvent.DOM_DELTA_LINE
          ? event.deltaY * 16
          : event.deltaMode === WheelEvent.DOM_DELTA_PAGE
            ? event.deltaY * Math.max(320, shell.clientHeight)
            : event.deltaY;
      const boundedDelta = clamp(pixelDelta, -240, 240);
      const zoomRatio = Math.exp(boundedDelta * 0.0012);
      targetCameraZ = zoomFromSurfaceDistance(targetCameraZ, zoomRatio);
      tooltipVisible = false;
    }

    function onPointerLeave() {
      if (activePointers.size === 0) tooltipVisible = false;
    }

    resetGlobe = () => {
      globeGroup.rotation.set(-0.12, -0.58, 0);
      targetCameraZ = INITIAL_CAMERA_Z;
      inertiaAngle = 0;
      tooltipVisible = false;
    };

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(shell);
    resize();

    canvas.addEventListener('pointerdown', onPointerDown);
    canvas.addEventListener('pointermove', onPointerMove);
    canvas.addEventListener('pointerup', onPointerUp);
    canvas.addEventListener('pointercancel', onPointerUp);
    canvas.addEventListener('pointerleave', onPointerLeave);
    canvas.addEventListener('wheel', onWheel, { passive: false });

    const themeObserver = new MutationObserver((records) => {
      if (records.some((record) => record.attributeName === 'data-theme')) {
        void updateTheme();
      }
    });
    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    });

    void updateTheme();
    void loadStats();
    const statsInterval = window.setInterval(() => void loadStats(), 15_000);

    let frameId = 0;
    const animate = () => {
      if (disposed) return;

      if (!dragging && activePointers.size === 0 && Math.abs(inertiaAngle) > 0.00001) {
        dragDelta.setFromAxisAngle(inertiaAxis, inertiaAngle);
        globeGroup.quaternion.premultiply(dragDelta).normalize();
        inertiaAngle *= 0.90;
      }

      camera.position.z += (targetCameraZ - camera.position.z) * 0.13;
      updateMarkerMatrices(camera.position.z);
      renderer.render(scene, camera);
      frameId = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      disposed = true;
      resetGlobe = null;
      window.clearInterval(statsInterval);
      cancelAnimationFrame(frameId);
      resizeObserver.disconnect();
      themeObserver.disconnect();
      canvas.removeEventListener('pointerdown', onPointerDown);
      canvas.removeEventListener('pointermove', onPointerMove);
      canvas.removeEventListener('pointerup', onPointerUp);
      canvas.removeEventListener('pointercancel', onPointerUp);
      canvas.removeEventListener('pointerleave', onPointerLeave);
      canvas.removeEventListener('wheel', onWheel);
      disposeMarkerMesh();
      markerGeometry.dispose();
      markerOutlineGeometry.dispose();
      markerMaterial.dispose();
      markerOutlineMaterial.dispose();
      currentTexture?.dispose();
      globeGeometry.dispose();
      globeMaterial.dispose();
      renderer.dispose();
    };
  });
</script>

<div class="globe-shell" bind:this={shell}>
  <p class="globe-a11y-description">
    Interactive clear three-dimensional globe showing approximate website visitor locations with transparent oceans. Pointer and touch users can grab the surface directly to rotate it one-to-one and scroll or pinch to zoom.
  </p>

  <canvas
    bind:this={canvas}
    class="globe-canvas"
    aria-hidden="true"
  ></canvas>

  <div class="globe-meta" aria-live="polite">
    <strong>Visitor globe</strong>
    <span>
      {#if loading}
        Loading locations…
      {:else if error}
        {error}
      {:else}
        {visitorCount.toLocaleString('en-US')} visitors{updatedAt ? ` · ${readableTime(updatedAt)}` : ''}
      {/if}
    </span>
  </div>

  <div class="globe-help">Grab and drag 1:1 · scroll or pinch to zoom</div>

  <button
    class="globe-reset"
    type="button"
    aria-label="Reset globe view"
    on:click={() => resetGlobe?.()}
  >Reset</button>

  {#if tooltipVisible}
    <div
      class="globe-tooltip"
      style={`left:${tooltipX}px;top:${tooltipY}px;`}
      aria-hidden="true"
    >{tooltipText}</div>
  {/if}
</div>

<style>
  .globe-shell {
    position: relative;
    width: 100%;
    height: 100%;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    background: var(--bg);
  }

  .globe-a11y-description {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  .globe-canvas {
    display: block;
    width: 100%;
    height: 100%;
    cursor: grab;
    touch-action: none;
    user-select: none;
  }

  .globe-canvas:active {
    cursor: grabbing;
  }

  .globe-meta,
  .globe-help,
  .globe-reset,
  .globe-tooltip {
    position: absolute;
    z-index: 2;
  }

  .globe-meta {
    top: clamp(1rem, 2.4vw, 1.5rem);
    left: clamp(1rem, 2.4vw, 1.5rem);
    display: grid;
    gap: 0.22rem;
    pointer-events: none;
  }

  .globe-meta strong {
    color: var(--text);
    font-family: var(--font-display);
    font-size: 1.05rem;
    font-weight: 400;
  }

  .globe-meta span,
  .globe-help {
    color: var(--muted);
    font-size: 0.74rem;
    line-height: 1.35;
  }

  .globe-help {
    bottom: clamp(1rem, 2.4vw, 1.5rem);
    left: 50%;
    padding: 0.38rem 0.55rem;
    border: 1px solid var(--line);
    background: color-mix(in srgb, var(--bg) 82%, transparent);
    transform: translateX(-50%);
    pointer-events: none;
    white-space: nowrap;
    backdrop-filter: blur(8px);
  }

  .globe-reset {
    top: clamp(1rem, 2.4vw, 1.5rem);
    right: clamp(1rem, 2.4vw, 1.5rem);
    appearance: none;
    padding: 0.42rem 0.62rem;
    border: 1px solid var(--line);
    background: color-mix(in srgb, var(--bg) 88%, transparent);
    color: var(--text);
    font: inherit;
    font-size: 0.75rem;
    cursor: pointer;
    backdrop-filter: blur(8px);
  }

  .globe-reset:hover {
    border-color: var(--text);
  }

  .globe-tooltip {
    max-width: min(17rem, calc(100% - 2rem));
    padding: 0.38rem 0.5rem;
    border: 1px solid var(--line);
    background: var(--bg);
    color: var(--text);
    font-size: 0.72rem;
    line-height: 1.35;
    transform: translate(0.7rem, calc(-100% - 0.7rem));
    pointer-events: none;
  }

  @media (max-width: 560px) {
    .globe-help {
      bottom: 0.8rem;
      font-size: 0.68rem;
    }

    .globe-meta {
      max-width: calc(100% - 7rem);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .globe-canvas {
      scroll-behavior: auto;
    }
  }
</style>
