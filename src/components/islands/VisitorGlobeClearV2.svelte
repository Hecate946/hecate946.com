<script lang="ts">
  import { onMount } from 'svelte';
  import * as THREE from 'three';
  import { resolveStatsApiBase } from '@/lib/stats-api';

  export let apiBase = '';
  export let embedded = false;

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

  export let locations: VisitorLocation[] = [];
  export let totalVisitors = 0;

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

  interface GlobeFocus {
    quaternion: THREE.Quaternion;
    cameraZ: number;
  }

  const GLOBE_RADIUS = 2.35;
  const MARKER_RADIUS = GLOBE_RADIUS + 0.038;
  const MIN_CAMERA_Z = 3.55;
  const MAX_CAMERA_Z = 9.5;
  const INITIAL_CAMERA_Z = 6.45;
  const SITE_BASE = String(import.meta.env.BASE_URL ?? '/').replace(/\/?$/, '/');
  const WORLD_TEXTURE_PREVIEW_URL = `${SITE_BASE}generated/globe-world-mask-4096.png`;
  const WORLD_TEXTURE_HD_URL = `${SITE_BASE}generated/globe-world-mask-8192.png`;
  const GLOBE_SHELL_BASE_OPACITY = 0.0075;
  const GLOBE_SHELL_EDGE_OPACITY = 0.082;
  const GLOBE_SHELL_OUTER_OPACITY = 0.014;
  const MARKER_CORE_CLOSE_PX = 4.4;
  const MARKER_CORE_FAR_PX = 6.8;
  const MARKER_GLOW_CLOSE_PX = 11.5;
  const MARKER_GLOW_FAR_PX = 18.0;

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
  let zoomGlobe: ((ratio: number) => void) | null = null;
  let applyExternalLocations: ((nextLocations: VisitorLocation[], nextTotalVisitors: number) => void) | null = null;
  let lastExternalLocations: VisitorLocation[] | null = null;

  $: if (embedded && applyExternalLocations && locations !== lastExternalLocations) {
    lastExternalLocations = locations;
    applyExternalLocations(locations, totalVisitors);
  }

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

  function configureWorldTexture(texture: THREE.Texture) {
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.ClampToEdgeWrapping;
    // The source images are already high resolution. Avoiding runtime mipmap
    // generation removes a large GPU upload cost and keeps first interaction fast.
    texture.generateMipmaps = false;
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;
    texture.needsUpdate = true;
    return texture;
  }

  function loadWorldTexture(url: string) {
    return new Promise<THREE.Texture>((resolve, reject) => {
      const loader = new THREE.TextureLoader();
      loader.load(
        url,
        (texture) => resolve(configureWorldTexture(texture)),
        undefined,
        () => reject(new Error(`Unable to load globe texture: ${url}`)),
      );
    });
  }

  function waitForIdle(timeout = 700) {
    return new Promise<void>((resolve) => {
      if ('requestIdleCallback' in window) {
        window.requestIdleCallback(() => resolve(), { timeout });
      } else {
        window.setTimeout(resolve, 80);
      }
    });
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
    const initialThemeColors = readThemeColors();
    const globeMaterial = new THREE.MeshBasicMaterial({
      color: initialThemeColors.text,
      transparent: true,
      opacity: 1,
      alphaTest: 0.001,
      depthWrite: false,
      side: THREE.FrontSide,
    });
    enableSphericalTextureLookup(globeMaterial);
    const globe = new THREE.Mesh(globeGeometry, globeMaterial);
    // Never render the untextured material: this is what caused the white flash.
    globe.visible = false;
    globe.renderOrder = 0;
    globeGroup.add(globe);

    // Keep the transparent-ocean globe, but make the shell feel lighter and
    // cleaner: almost invisible in the center, then gradually more watery toward
    // the silhouette, with only a restrained final edge emphasis.
    const rimGeometry = new THREE.SphereGeometry(GLOBE_RADIUS * 1.006, 192, 128);
    const rimMaterial = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      side: THREE.FrontSide,
      uniforms: {
        rimColor: { value: new THREE.Color(initialThemeColors.text) },
        baseOpacity: { value: GLOBE_SHELL_BASE_OPACITY },
        edgeOpacity: { value: GLOBE_SHELL_EDGE_OPACITY },
        outerOpacity: { value: GLOBE_SHELL_OUTER_OPACITY },
      },
      vertexShader: `
        varying vec3 vViewPosition;
        varying vec3 vViewNormal;

        void main() {
          vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
          vViewPosition = -mvPosition.xyz;
          vViewNormal = normalize(normalMatrix * normal);
          gl_Position = projectionMatrix * mvPosition;
        }
      `,
      fragmentShader: `
        uniform vec3 rimColor;
        uniform float baseOpacity;
        uniform float edgeOpacity;
        uniform float outerOpacity;
        varying vec3 vViewPosition;
        varying vec3 vViewNormal;

        void main() {
          vec3 viewDir = normalize(vViewPosition);
          float fresnel = 1.0 - max(dot(normalize(vViewNormal), viewDir), 0.0);

          // Keep the middle of the globe almost clear, then let the water shell
          // build gradually toward the silhouette. A small extra outer term keeps
          // the rim legible without bringing back hard-looking concentric bands.
          float shell = smoothstep(0.18, 1.0, pow(clamp(fresnel, 0.0, 1.0), 2.35));
          float outer = smoothstep(0.82, 1.0, fresnel);
          float alpha = baseOpacity + shell * edgeOpacity + outer * outerOpacity;
          gl_FragColor = vec4(rimColor, alpha);
        }
      `,
    });
    const globeRim = new THREE.Mesh(rimGeometry, rimMaterial);
    globeRim.renderOrder = -1;
    globeGroup.add(globeRim);

    // Visitor markers are rendered as camera-facing points instead of little
    // tangent discs. Each point has a soft halo plus a crisp core, so it reads as
    // a restrained point of light even when the globe is zoomed out. Exact same-
    // coordinate visitors are coalesced into one slightly larger light.
    let markerGeometry = new THREE.BufferGeometry();
    const markerCoreMaterial = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.NormalBlending,
      uniforms: {
        markerColor: { value: new THREE.Color(initialThemeColors.accent) },
        cameraZ: { value: INITIAL_CAMERA_Z },
        pixelRatio: { value: renderer.getPixelRatio() },
      },
      vertexShader: `
        attribute float markerScale;
        uniform float cameraZ;
        uniform float pixelRatio;
        varying float vFacing;

        void main() {
          vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
          vec3 viewNormal = normalize(normalMatrix * normalize(position));
          vec3 viewDir = normalize(-mvPosition.xyz);
          vFacing = smoothstep(-0.01, 0.10, dot(viewNormal, viewDir));

          float zoomT = clamp(
            (cameraZ - ${MIN_CAMERA_Z.toFixed(2)}) / ${(
              MAX_CAMERA_Z - MIN_CAMERA_Z
            ).toFixed(2)},
            0.0,
            1.0
          );
          float pointSize = mix(${MARKER_CORE_CLOSE_PX.toFixed(1)}, ${MARKER_CORE_FAR_PX.toFixed(1)}, zoomT);
          gl_PointSize = pointSize * markerScale * pixelRatio;
          gl_Position = projectionMatrix * mvPosition;
        }
      `,
      fragmentShader: `
        uniform vec3 markerColor;
        varying float vFacing;

        void main() {
          vec2 point = gl_PointCoord * 2.0 - 1.0;
          float radius = length(point);
          if (radius > 1.0 || vFacing <= 0.001) discard;

          float core = 1.0 - smoothstep(0.45, 0.78, radius);
          float feather = 1.0 - smoothstep(0.72, 1.0, radius);
          float alpha = max(core, feather * 0.78) * vFacing;
          gl_FragColor = vec4(markerColor, alpha);
        }
      `,
    });

    const markerGlowMaterial = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      blending: THREE.NormalBlending,
      uniforms: {
        markerColor: { value: new THREE.Color(initialThemeColors.accent) },
        cameraZ: { value: INITIAL_CAMERA_Z },
        pixelRatio: { value: renderer.getPixelRatio() },
      },
      vertexShader: `
        attribute float markerScale;
        uniform float cameraZ;
        uniform float pixelRatio;
        varying float vFacing;

        void main() {
          vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
          vec3 viewNormal = normalize(normalMatrix * normalize(position));
          vec3 viewDir = normalize(-mvPosition.xyz);
          vFacing = smoothstep(-0.02, 0.13, dot(viewNormal, viewDir));

          float zoomT = clamp(
            (cameraZ - ${MIN_CAMERA_Z.toFixed(2)}) / ${(
              MAX_CAMERA_Z - MIN_CAMERA_Z
            ).toFixed(2)},
            0.0,
            1.0
          );
          float pointSize = mix(${MARKER_GLOW_CLOSE_PX.toFixed(1)}, ${MARKER_GLOW_FAR_PX.toFixed(1)}, zoomT);
          gl_PointSize = pointSize * markerScale * pixelRatio;
          gl_Position = projectionMatrix * mvPosition;
        }
      `,
      fragmentShader: `
        uniform vec3 markerColor;
        varying float vFacing;

        void main() {
          vec2 point = gl_PointCoord * 2.0 - 1.0;
          float radius = length(point);
          if (radius > 1.0 || vFacing <= 0.001) discard;

          float glow = exp(-radius * radius * 4.6);
          float edge = 1.0 - smoothstep(0.72, 1.0, radius);
          float alpha = glow * edge * 0.30 * vFacing;
          gl_FragColor = vec4(markerColor, alpha);
        }
      `,
    });

    let markerPoints: THREE.Points | null = null;
    let markerGlowPoints: THREE.Points | null = null;
    let markerMetadata: GlobeMarker[] = [];
    let markerPositions: THREE.Vector3[] = [];

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
    let lastStandaloneLocationSignature = '';
    let hasUserAdjustedView = false;
    let defaultFocus: GlobeFocus = {
      quaternion: globeGroup.quaternion.clone(),
      cameraZ: INITIAL_CAMERA_Z,
    };

    function disposeMarkerMesh() {
      if (markerPoints) {
        globeGroup.remove(markerPoints);
        markerPoints = null;
      }
      if (markerGlowPoints) {
        globeGroup.remove(markerGlowPoints);
        markerGlowPoints = null;
      }
      markerGeometry.dispose();
      markerGeometry = new THREE.BufferGeometry();
      markerPositions = [];
    }

    function weightedPercentile(
      values: Array<{ value: number; weight: number }>,
      percentile: number,
    ) {
      if (values.length === 0) return 0;
      const sorted = [...values].sort((a, b) => a.value - b.value);
      const totalWeight = sorted.reduce((sum, item) => sum + item.weight, 0);
      if (totalWeight <= 0) return sorted[sorted.length - 1]?.value ?? 0;

      const target = totalWeight * percentile;
      let cumulative = 0;
      for (const item of sorted) {
        cumulative += item.weight;
        if (cumulative >= target) return item.value;
      }
      return sorted[sorted.length - 1]?.value ?? 0;
    }

    function focusForMarkers(markers: GlobeMarker[]): GlobeFocus {
      if (markers.length === 0) {
        return {
          quaternion: new THREE.Quaternion().setFromEuler(
            new THREE.Euler(-0.12, -0.58, 0),
          ),
          cameraZ: INITIAL_CAMERA_Z,
        };
      }

      const directions = markers.map((marker) =>
        markerPosition(marker.latitude, marker.longitude, 1).normalize(),
      );
      const sigma = THREE.MathUtils.degToRad(34);

      // Find the point with the strongest nearby visitor mass. This is more
      // useful than a raw world centroid, which can land in an ocean whenever
      // there are a few visitors on another continent.
      let bestSeed = 0;
      let bestScore = -Infinity;
      directions.forEach((seed, seedIndex) => {
        let score = 0;
        directions.forEach((direction, index) => {
          const angle = Math.acos(clamp(seed.dot(direction), -1, 1));
          const kernel = Math.exp(-0.5 * (angle / sigma) ** 2);
          score += markers[index].count * kernel;
        });
        if (score > bestScore) {
          bestScore = score;
          bestSeed = seedIndex;
        }
      });

      const seed = directions[bestSeed];
      const focusVector = new THREE.Vector3();
      const spreadSamples: Array<{ value: number; weight: number }> = [];

      directions.forEach((direction, index) => {
        const angle = Math.acos(clamp(seed.dot(direction), -1, 1));
        const kernel = Math.exp(-0.5 * (angle / sigma) ** 2);
        const weight = markers[index].count * kernel;
        focusVector.addScaledVector(direction, weight);
      });

      if (focusVector.lengthSq() < 0.000001) focusVector.copy(seed);
      focusVector.normalize();

      directions.forEach((direction, index) => {
        const angle = Math.acos(clamp(focusVector.dot(direction), -1, 1));
        const seedAngle = Math.acos(clamp(seed.dot(direction), -1, 1));
        const localWeight =
          markers[index].count * Math.exp(-0.5 * (seedAngle / sigma) ** 2);
        spreadSamples.push({ value: angle, weight: localWeight });
      });

      const spread = weightedPercentile(spreadSamples, 0.82);
      const spreadDegrees = THREE.MathUtils.radToDeg(spread);
      const cameraZ = clamp(6.05 + spreadDegrees * 0.012, 6.05, INITIAL_CAMERA_Z);
      // Center the dominant visitor direction while keeping geographic north
      // upright. A simple setFromUnitVectors() leaves roll unconstrained and can
      // make the focused region appear tilted sideways.
      const north = new THREE.Vector3(0, 1, 0).addScaledVector(
        focusVector,
        -focusVector.y,
      );
      if (north.lengthSq() < 0.000001) {
        north.set(0, 0, -1).addScaledVector(
          focusVector,
          focusVector.z,
        );
      }
      north.normalize();
      const east = new THREE.Vector3().crossVectors(north, focusVector).normalize();
      const localBasis = new THREE.Matrix4().makeBasis(east, north, focusVector);
      const quaternion = new THREE.Quaternion().setFromRotationMatrix(
        localBasis.clone().invert(),
      );

      return { quaternion, cameraZ };
    }

    function applyDefaultFocus(markers: GlobeMarker[], force = false) {
      defaultFocus = focusForMarkers(markers);
      if (!force && hasUserAdjustedView) return;

      globeGroup.quaternion.copy(defaultFocus.quaternion);
      targetCameraZ = defaultFocus.cameraZ;
      camera.position.z = defaultFocus.cameraZ;
      inertiaAngle = 0;
    }

    function setMarkers(nextLocations: VisitorLocation[]) {
      markerMetadata = groupLocations(nextLocations);
      disposeMarkerMesh();
      applyDefaultFocus(markerMetadata);

      if (markerMetadata.length === 0) return;

      markerPositions = markerMetadata.map((marker) =>
        markerPosition(marker.latitude, marker.longitude, MARKER_RADIUS),
      );
      const positions = new Float32Array(markerPositions.length * 3);
      const markerScales = new Float32Array(markerPositions.length);

      markerPositions.forEach((position, index) => {
        positions[index * 3] = position.x;
        positions[index * 3 + 1] = position.y;
        positions[index * 3 + 2] = position.z;

        // Exact same-location visitors become one brighter/larger light. The
        // logarithm keeps dense locations expressive without letting them turn
        // into oversized bubbles.
        markerScales[index] =
          1 + Math.min(0.65, Math.log2(Math.max(1, markerMetadata[index].count)) * 0.16);
      });

      markerGeometry.setAttribute(
        'position',
        new THREE.BufferAttribute(positions, 3),
      );
      markerGeometry.setAttribute(
        'markerScale',
        new THREE.BufferAttribute(markerScales, 1),
      );
      markerGeometry.computeBoundingSphere();

      markerGlowPoints = new THREE.Points(markerGeometry, markerGlowMaterial);
      markerGlowPoints.renderOrder = 2;
      markerGlowPoints.userData.kind = 'visitor-marker-glow';

      markerPoints = new THREE.Points(markerGeometry, markerCoreMaterial);
      markerPoints.renderOrder = 3;
      markerPoints.userData.kind = 'visitor-markers';

      globeGroup.add(markerGlowPoints);
      globeGroup.add(markerPoints);
    }

    applyExternalLocations = (nextLocations, nextTotalVisitors) => {
      visitorCount = nextTotalVisitors;
      setMarkers(nextLocations ?? []);
      loading = false;
      error = '';
    };

    function applyTheme() {
      const colors = readThemeColors();
      // The map texture is a white alpha mask, so theme changes only need to
      // recolor the material. No image decode, rasterization, or GPU re-upload.
      globeMaterial.color.set(colors.text);
      markerCoreMaterial.uniforms.markerColor.value.set(colors.accent);
      markerGlowMaterial.uniforms.markerColor.value.set(colors.accent);
      rimMaterial.uniforms.rimColor.value.set(colors.text);
    }

    function installWorldTexture(nextTexture: THREE.Texture) {
      if (disposed) {
        nextTexture.dispose();
        return;
      }

      const hadTexture = Boolean(globeMaterial.map);
      currentTexture?.dispose();
      currentTexture = nextTexture;
      globeMaterial.map = nextTexture;
      // The shader needs one compile when USE_MAP is introduced. Swapping the
      // preview for the HD texture does not require another material compile.
      if (!hadTexture) globeMaterial.needsUpdate = true;
      globe.visible = true;
    }

    async function loadWorldTextures() {
      try {
        // 4K preview first: small enough to decode/upload quickly, already sharp
        // at the normal view, and prevents the UI from waiting on the 8K texture.
        const previewTexture = await loadWorldTexture(WORLD_TEXTURE_PREVIEW_URL);
        installWorldTexture(previewTexture);

        if (disposed) return;
        await waitForIdle();
        if (disposed) return;

        // Upgrade quietly to the 8K texture after the globe is already visible
        // and interactive. Browser image caching also makes remounts very cheap.
        const hdTexture = await loadWorldTexture(WORLD_TEXTURE_HD_URL);
        installWorldTexture(hdTexture);
      } catch (textureError) {
        console.error(textureError);
      }
    }

    function standaloneLocationSignature(values: VisitorLocation[]) {
      return values
        .map((location) =>
          `${location.latitude}:${location.longitude}:${location.pointIndex ?? 0}:${location.pointCount ?? 1}`,
        )
        .sort()
        .join('|');
    }

    async function loadStats() {
      const base = resolveStatsApiBase(apiBase);
      if (!base) {
        loading = false;
        error = 'Live analytics are not configured.';
        return;
      }

      try {
        const response = await fetch(`${base}/api/stats?days=30`, {
          headers: { Accept: 'application/json' },
          cache: 'default',
        });
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);

        const data = (await response.json()) as LiveStats;
        if (disposed) return;
        visitorCount = data.summary.estimatedVisitors ?? data.locations.length;
        updatedAt = data.summary.updatedAt;
        const nextLocations = data.locations ?? [];
        const nextSignature = standaloneLocationSignature(nextLocations);
        if (nextSignature !== lastStandaloneLocationSignature) {
          lastStandaloneLocationSignature = nextSignature;
          setMarkers(nextLocations);
        }
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
      markerCoreMaterial.uniforms.pixelRatio.value = renderer.getPixelRatio();
      markerGlowMaterial.uniforms.pixelRatio.value = renderer.getPixelRatio();
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
      hasUserAdjustedView = true;
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

      if (event.buttons === 0 && markerPoints) {
        const bounds = canvas.getBoundingClientRect();
        pointerNdc.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
        pointerNdc.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
        raycaster.setFromCamera(pointerNdc, camera);
        raycaster.params.Points = { threshold: 0.09 };
        const intersection = raycaster.intersectObject(markerPoints, false)[0];
        const markerIndex = intersection?.index;

        if (typeof markerIndex === 'number' && markerMetadata[markerIndex]) {
          const marker = markerMetadata[markerIndex];
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
      hasUserAdjustedView = true;

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

    zoomGlobe = (ratio: number) => {
      hasUserAdjustedView = true;
      targetCameraZ = zoomFromSurfaceDistance(targetCameraZ, ratio);
      inertiaAngle = 0;
      tooltipVisible = false;
    };

    resetGlobe = () => {
      hasUserAdjustedView = false;
      globeGroup.quaternion.copy(defaultFocus.quaternion);
      targetCameraZ = defaultFocus.cameraZ;
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
        applyTheme();
      }
    });
    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    });

    applyTheme();
    void loadWorldTextures();
    let statsInterval: number | null = null;
    if (embedded) {
      applyExternalLocations?.(locations, totalVisitors);
      lastExternalLocations = locations;
    } else {
      void loadStats();
      statsInterval = window.setInterval(() => {
        if (document.visibilityState === 'visible') void loadStats();
      }, 60_000);
    }

    let frameId = 0;
    const animate = () => {
      if (disposed) return;

      if (!dragging && activePointers.size === 0 && Math.abs(inertiaAngle) > 0.00001) {
        dragDelta.setFromAxisAngle(inertiaAxis, inertiaAngle);
        globeGroup.quaternion.premultiply(dragDelta).normalize();
        inertiaAngle *= 0.90;
      }

      camera.position.z += (targetCameraZ - camera.position.z) * 0.13;
      markerCoreMaterial.uniforms.cameraZ.value = camera.position.z;
      markerGlowMaterial.uniforms.cameraZ.value = camera.position.z;
      renderer.render(scene, camera);
      frameId = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      disposed = true;
      resetGlobe = null;
      zoomGlobe = null;
      applyExternalLocations = null;
      if (statsInterval !== null) window.clearInterval(statsInterval);
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
      markerCoreMaterial.dispose();
      markerGlowMaterial.dispose();
      currentTexture?.dispose();
      globeGeometry.dispose();
      rimGeometry.dispose();
      globeMaterial.dispose();
      rimMaterial.dispose();
      renderer.dispose();
    };
  });
</script>

<div class="globe-shell" data-embedded={embedded} bind:this={shell}>
  <p class="globe-a11y-description">
    Interactive clear three-dimensional globe showing approximate website visitor locations with transparent oceans. Pointer and touch users can grab the surface directly to rotate it one-to-one and scroll or pinch to zoom.
  </p>

  <canvas
    bind:this={canvas}
    class="globe-canvas"
    aria-hidden="true"
  ></canvas>

  {#if !embedded}
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
  {/if}

  <div class="globe-controls" aria-label="Globe controls">
    <button
      type="button"
      aria-label="Zoom in"
      on:click={() => zoomGlobe?.(1 / 1.5)}
    >+</button>
    <button
      type="button"
      aria-label="Zoom out"
      on:click={() => zoomGlobe?.(1.5)}
    >−</button>
    <button
      type="button"
      aria-label="Fit globe to visitor focus"
      on:click={() => resetGlobe?.()}
    >Fit</button>
  </div>

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

  .globe-shell[data-embedded='true'] {
    border-top: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
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
  .globe-controls,
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

  .globe-controls {
    top: clamp(1rem, 2.4vw, 1.5rem);
    right: clamp(1rem, 2.4vw, 1.5rem);
    display: flex;
    overflow: hidden;
    background: color-mix(in srgb, var(--bg) 92%, transparent);
    border: 1px solid var(--line);
    border-radius: 999px;
    backdrop-filter: blur(0.45rem);
  }

  .globe-shell[data-embedded='true'] .globe-controls {
    top: 0.75rem;
    right: 0.75rem;
  }

  .globe-controls button {
    display: grid;
    width: 2.25rem;
    height: 2.25rem;
    place-items: center;
    padding: 0;
    background: transparent;
    border: 0;
    border-right: 1px solid var(--line);
    color: var(--text);
    cursor: pointer;
    font: inherit;
    line-height: 1;
    transition: none !important;
  }

  .globe-controls button:last-child {
    width: auto;
    padding-inline: 0.8rem;
    border-right: 0;
    font-size: 0.72rem;
  }

  .globe-controls button:hover,
  .globe-controls button:focus-visible {
    background: var(--accent-soft);
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
