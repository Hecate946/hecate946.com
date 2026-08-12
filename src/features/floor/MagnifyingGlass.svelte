<script lang="ts">
  import { getContext, onMount } from 'svelte';
  import * as THREE from 'three';
  import RAPIER from '@dimforge/rapier3d-compat';
  import { FLOOR_SCENE_CONTEXT, type FloorSceneContext } from './floor-scene-context';
  import '@/styles/magnifying-glass.css';

  const context = getContext<FloorSceneContext>(FLOOR_SCENE_CONTEXT);

  const LENS_RADIUS = 38;
  const RING_TUBE_RADIUS = 4.7;
  const OUTER_RING_RADIUS = LENS_RADIUS + RING_TUBE_RADIUS;
  const HANDLE_HALF_WIDTH = 7.9;
  const HANDLE_Y = 0.88;
  const HANDLE_CENTER_Z = 111;
  const HANDLE_HALF_LENGTH = 52;
  const FERRULE_CENTER_Z = 49;
  const FERRULE_HALF_LENGTH = 11.5;
  const FERRULE_HALF_HEIGHT = 7.5;
  const FERRULE_Y = 0.35;
  const CAP_CENTER_Z = 166;
  const CAP_HALF_LENGTH = 4.5;
  const CAP_HALF_HEIGHT = 8.9;
  const CAP_Y = 1.15;
  const CAP_LOCAL = new THREE.Vector3(0, 0, CAP_CENTER_Z + CAP_HALF_LENGTH);
  const GRIP_LOCAL = new THREE.Vector3(0, 0, 147);
  // The physical lens extends under the metal bezel so there is never a visible
  // air gap. The optical aperture stays just inside the bezel so magnified DOM
  // content cannot bleed onto the metal ring.
  const GLASS_RADIUS = LENS_RADIUS - RING_TUBE_RADIUS + 1.15;
  const LENS_VIEW_RADIUS = LENS_RADIUS - RING_TUBE_RADIUS - 0.55;
  const LENS_PLANE_Y = 0;
  const VIEWPORT_MARGIN = 6;
  const WALL_PLANE_OFFSET_Z = 10;
  const HANDLE_SCREEN_TILT = THREE.MathUtils.degToRad(-78);
  const FLOOR_VISUAL_EPSILON = 0.65;
  const LENS_CONTOUR_POINTS = 36;

  const MAGNIFICATION = 1.58;
  const PICKUP_FOLLOW = 0.2;
  const FIXED_STEP = 1 / 60;
  const GRAVITY = -980;
  const MAX_RELEASE_SPEED = 1320;
  const FLOOR_FRICTION = 1.45;
  const FLOOR_RESTITUTION = 0.095;
  const WALL_FRICTION = 0.58;
  const WALL_RESTITUTION = 0.18;
  const BOUNDS_MARGIN_LEFT = OUTER_RING_RADIUS + 5;
  const BOUNDS_MARGIN_RIGHT = OUTER_RING_RADIUS + 5;
  const METAL_RESTITUTION = 0.31;
  const WOOD_RESTITUTION = 0.11;
  const GLASS_RESTITUTION = 0.045;
  const IMPACT_ASSIST_FACTOR = 0.24;
  const MIN_HARD_IMPACT_SPEED = 82;
  const MAX_ASSISTED_BOUNCE_SPEED = 230;
  const FLOOR_COLLIDER_THICKNESS = 8;

  type Mode = 'settling' | 'idle' | 'held' | 'airborne';
  type TransformTarget = { position: THREE.Vector3; quaternion: THREE.Quaternion };
  type ProjectedBounds = { left: number; right: number; top: number; bottom: number };
  type BodyState = {
    position: THREE.Vector3;
    rotation: THREE.Quaternion;
    linvel: THREE.Vector3;
    angvel: THREE.Vector3;
  };

  let mode: Mode = 'settling';
  let magnifier: THREE.Group | null = null;
  let shadow: THREE.Group | null = null;
  let softShadow: THREE.Group | null = null;
  let hoverGlow: THREE.Group | null = null;
  let lightRig: THREE.Group | null = null;
  let foregroundScene: THREE.Scene | null = null;
  let foregroundRenderer: THREE.WebGLRenderer | null = null;
  let foregroundCanvas: HTMLCanvasElement | null = null;

  let physicsWorld: any = null;
  let rigidBody: any = null;
  let floorCollider: any = null;
  let backWallCollider: any = null;
  let frontWallCollider: any = null;
  let leftWallCollider: any = null;
  let rightWallCollider: any = null;
  let floorColliderSignature = '';
  let physicsEventQueue: any = null;
  let preStepVerticalVelocity = 0;
  let lastBounceAssistAt = 0;
  let physicsReady = false;
  let lastViewportSafeState: BodyState | null = null;

  let hitButton: HTMLButtonElement | null = null;
  let activePointerId: number | null = null;
  let pointerX = 0;
  let pointerY = 0;
  let pointerSampleTime = 0;
  let lastTargetPosition: THREE.Vector3 | null = null;
  const filteredReleaseVelocity = new THREE.Vector3();
  let heldPosition = new THREE.Vector3();
  let heldQuaternion = new THREE.Quaternion();

  let overlayRoot: HTMLDivElement | null = null;
  let lensViewport: HTMLDivElement | null = null;
  let snapshotRoom: HTMLElement | null = null;

  let animationFrame = 0;
  let previousFrameTime = 0;
  let physicsAccumulator = 0;
  let destroyed = false;
  let visualViewport: VisualViewport | null = null;

  const tmpVectorB = new THREE.Vector3();
  const tmpVectorC = new THREE.Vector3();
  const magnifierBoundsLocalVertices: THREE.Vector3[] = [];


  function captureBodyState(): BodyState | null {
    if (!rigidBody) return null;
    const t = rigidBody.translation();
    const r = rigidBody.rotation();
    const lv = rigidBody.linvel();
    const av = rigidBody.angvel();
    return {
      position: new THREE.Vector3(t.x, t.y, t.z),
      rotation: new THREE.Quaternion(r.x, r.y, r.z, r.w),
      linvel: new THREE.Vector3(lv.x, lv.y, 0),
      angvel: new THREE.Vector3(0, 0, av.z),
    };
  }

  function applyBodyState(state: BodyState, wake = false) {
    if (!rigidBody) return;
    rigidBody.setTranslation({ x: state.position.x, y: state.position.y, z: wallPlaneZ() }, wake);
    rigidBody.setRotation(
      { x: state.rotation.x, y: state.rotation.y, z: state.rotation.z, w: state.rotation.w },
      wake,
    );
    rigidBody.setLinvel({ x: state.linvel.x, y: state.linvel.y, z: state.linvel.z }, wake);
    rigidBody.setAngvel({ x: 0, y: 0, z: state.angvel.z }, wake);
  }

  function viewportBoundsInside(bounds: ProjectedBounds | null) {
    return !!bounds
      && bounds.left >= VIEWPORT_MARGIN
      && bounds.right <= window.innerWidth - VIEWPORT_MARGIN
      && bounds.top >= VIEWPORT_MARGIN
      && bounds.bottom <= window.innerHeight - VIEWPORT_MARGIN;
  }

  function rememberViewportSafeState() {
    const bounds = projectedMagnifierBounds();
    if (viewportBoundsInside(bounds)) {
      const state = captureBodyState();
      if (state) lastViewportSafeState = state;
      return true;
    }
    return false;
  }

  function viewportViolations(bounds: ProjectedBounds | null) {
    return {
      left: !!bounds && bounds.left < VIEWPORT_MARGIN,
      right: !!bounds && bounds.right > window.innerWidth - VIEWPORT_MARGIN,
      top: !!bounds && bounds.top < VIEWPORT_MARGIN,
      bottom: !!bounds && bounds.bottom > window.innerHeight - VIEWPORT_MARGIN,
    };
  }

  function createContactShadowTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 768;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    const draw = (alpha: number, blur: number, widthScale: number) => {
      ctx.save();
      ctx.filter = `blur(${blur}px)`;
      ctx.strokeStyle = `rgba(0,0,0,${alpha})`;
      ctx.fillStyle = `rgba(0,0,0,${alpha})`;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      ctx.lineWidth = 25 * widthScale;
      ctx.beginPath();
      ctx.arc(256, 176, 102, 0, Math.PI * 2);
      ctx.stroke();

      ctx.lineWidth = 34 * widthScale;
      ctx.beginPath();
      ctx.moveTo(256, 278);
      ctx.lineTo(256, 626);
      ctx.stroke();

      ctx.beginPath();
      ctx.ellipse(256, 650, 22 * widthScale, 14 * widthScale, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    };

    draw(0.19, 17, 1.08);
    draw(0.14, 6, 0.9);

    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
  }

  function createWoodTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 1024;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    const gradient = ctx.createLinearGradient(0, 0, canvas.width, 0);
    gradient.addColorStop(0, '#a96f43');
    gradient.addColorStop(0.28, '#d5a16d');
    gradient.addColorStop(0.52, '#e0b17d');
    gradient.addColorStop(0.76, '#c68a59');
    gradient.addColorStop(1, '#98613a');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    let seed = 946;
    const random = () => {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      return seed / 4294967296;
    };

    ctx.lineCap = 'round';
    for (let index = 0; index < 62; index += 1) {
      const startX = random() * canvas.width;
      const amplitude = 2 + random() * 9;
      const frequency = 0.006 + random() * 0.014;
      const phase = random() * Math.PI * 2;
      ctx.beginPath();
      for (let y = -20; y <= canvas.height + 20; y += 12) {
        const x = startX + Math.sin(y * frequency + phase) * amplitude;
        if (y === -20) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = `rgba(${55 + Math.floor(random() * 35)},${27 + Math.floor(random() * 22)},${14 + Math.floor(random() * 12)},${0.04 + random() * 0.1})`;
      ctx.lineWidth = 0.7 + random() * 2.2;
      ctx.stroke();
    }

    // A few longer pores keep the material from reading as a flat brown tube.
    for (let index = 0; index < 38; index += 1) {
      const x = random() * canvas.width;
      const y = random() * canvas.height;
      ctx.fillStyle = `rgba(58,29,16,${0.08 + random() * 0.08})`;
      ctx.beginPath();
      ctx.ellipse(x, y, 0.8 + random() * 1.4, 6 + random() * 18, random() * 0.16, 0, Math.PI * 2);
      ctx.fill();
    }

    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(1.25, 1.05);
    texture.anisotropy = 4;
    return texture;
  }

  function createMagnifierModel() {
    const root = new THREE.Group();
    root.name = 'room-magnifying-glass';

    const metal = new THREE.MeshPhysicalMaterial({
      color: 0xe9e7e2,
      metalness: 1,
      roughness: 0.095,
      clearcoat: 0.42,
      clearcoatRoughness: 0.055,
      reflectivity: 1,
    });
    const darkMetal = new THREE.MeshPhysicalMaterial({
      color: 0x5b5855,
      metalness: 0.98,
      roughness: 0.13,
      clearcoat: 0.3,
      clearcoatRoughness: 0.07,
      reflectivity: 0.92,
    });
    const woodTexture = createWoodTexture();
    const handleMaterial = new THREE.MeshPhysicalMaterial({
      color: 0xd1a06f,
      map: woodTexture,
      bumpMap: woodTexture,
      bumpScale: 0.105,
      metalness: 0,
      roughness: 0.44,
      clearcoat: 0.12,
      clearcoatRoughness: 0.32,
      sheen: 0.08,
      sheenRoughness: 0.7,
      sheenColor: new THREE.Color(0xffdfbf),
    });
    if (woodTexture) handleMaterial.userData.disposableTexture = woodTexture;
    // The actual magnified image is a DOM layer beneath this canvas. Keep the
    // WebGL lens nearly clear and use it only for subtle surface reflections; a
    // transmissive material would incorrectly refract the transparent WebGL scene
    // instead of the page behind it.
    const glassMaterial = new THREE.MeshPhysicalMaterial({
      color: 0xf5fbff,
      transparent: true,
      opacity: 0.075,
      roughness: 0.055,
      ior: 1.52,
      metalness: 0,
      clearcoat: 0.92,
      clearcoatRoughness: 0.035,
      reflectivity: 0.16,
      depthWrite: false,
      side: THREE.DoubleSide,
    });

    const ring = new THREE.Mesh(new THREE.TorusGeometry(LENS_RADIUS, RING_TUBE_RADIUS, 28, 96), metal);
    ring.name = 'magnifier-ring';
    ring.rotation.x = Math.PI / 2;
    ring.scale.z = 1;
    ring.castShadow = true;
    ring.renderOrder = 6;
    root.add(ring);

    const glass = new THREE.Mesh(
      new THREE.CylinderGeometry(GLASS_RADIUS, GLASS_RADIUS, 1.9, 128, 1, false),
      glassMaterial,
    );
    glass.name = 'magnifier-glass';
    glass.position.y = LENS_PLANE_Y;
    glass.renderOrder = 5;
    root.add(glass);

    // A nearly transparent glass edge catches just enough light to make the lens
    // read as a real piece of glass without drawing a fake outline around it.
    const glassEdge = new THREE.Mesh(
      new THREE.TorusGeometry(GLASS_RADIUS - 0.4, 0.62, 12, 128),
      new THREE.MeshPhysicalMaterial({
        color: 0xcde7df,
        transparent: true,
        opacity: 0.2,
        roughness: 0.09,
        ior: 1.52,
        clearcoat: 0.55,
        clearcoatRoughness: 0.06,
        depthWrite: false,
        side: THREE.DoubleSide,
      }),
    );
    glassEdge.name = 'magnifier-glass-edge';
    glassEdge.rotation.x = Math.PI / 2;
    glassEdge.position.y = LENS_PLANE_Y + 0.08;
    glassEdge.renderOrder = 5;
    root.add(glassEdge);

    const ferrule = new THREE.Mesh(new THREE.CylinderGeometry(7.5, 7.5, 23, 30), darkMetal);
    ferrule.name = 'magnifier-ferrule';
    ferrule.rotation.x = Math.PI / 2;
    ferrule.position.set(0, FERRULE_Y, FERRULE_CENTER_Z);
    ferrule.castShadow = true;
    ferrule.renderOrder = 6;
    root.add(ferrule);

    const handle = new THREE.Mesh(new THREE.CylinderGeometry(7.9, 7.9, 104, 32), handleMaterial);
    handle.name = 'magnifier-handle';
    handle.rotation.x = Math.PI / 2;
    handle.position.set(0, HANDLE_Y, HANDLE_CENTER_Z);
    handle.castShadow = true;
    handle.renderOrder = 6;
    root.add(handle);

    const cap = new THREE.Mesh(new THREE.CylinderGeometry(8.9, 8.9, 8.5, 30), darkMetal);
    cap.name = 'magnifier-cap';
    cap.rotation.x = Math.PI / 2;
    cap.position.set(0, CAP_Y, CAP_CENTER_Z);
    cap.castShadow = true;
    cap.renderOrder = 6;
    root.add(cap);

    // Cache every rendered mesh vertex in the magnifier's local coordinate
    // system. Projecting these exact vertices gives a tight viewport bounding
    // rectangle for the actual triangles on screen instead of an approximate
    // world-space box.
    magnifierBoundsLocalVertices.length = 0;
    root.traverse((child) => {
      if (!(child instanceof THREE.Mesh)) return;
      child.updateMatrix();
      const positions = child.geometry.getAttribute('position');
      if (!positions) return;
      for (let index = 0; index < positions.count; index += 1) {
        const vertex = new THREE.Vector3().fromBufferAttribute(positions, index);
        vertex.applyMatrix4(child.matrix);
        magnifierBoundsLocalVertices.push(vertex);
      }
    });

    return root;
  }

  function createSilhouetteLayer(
    source: THREE.Group,
    opacity: number,
    scale = 1,
    color = 0x050505,
    side: THREE.Side = THREE.DoubleSide,
  ) {
    const group = new THREE.Group();
    source.traverse((child) => {
      if (!(child instanceof THREE.Mesh) || child.name.startsWith('magnifier-glass')) return;
      const material = new THREE.MeshBasicMaterial({
        color,
        transparent: opacity < 1,
        opacity,
        depthWrite: false,
        depthTest: true,
        side,
        toneMapped: false,
      });
      const clone = new THREE.Mesh(child.geometry.clone(), material);
      clone.name = `${child.name}-silhouette`;
      clone.position.copy(child.position);
      clone.quaternion.copy(child.quaternion);
      clone.scale.copy(child.scale).multiplyScalar(scale);
      clone.renderOrder = side === THREE.BackSide ? 5 : 1;
      group.add(clone);
    });
    return group;
  }

  function createShadow(source: THREE.Group) {
    return createSilhouetteLayer(source, 0.16, 1.006, 0x090604, THREE.DoubleSide);
  }

  function createSoftShadow(source: THREE.Group) {
    return createSilhouetteLayer(source, 0.055, 1.045, 0x090604, THREE.DoubleSide);
  }

  function createHoverGlowTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 768;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    const drawShape = (alpha: number, blur: number, expansion: number) => {
      ctx.save();
      ctx.filter = `blur(${blur}px)`;
      ctx.strokeStyle = `rgba(255,239,201,${alpha})`;
      ctx.fillStyle = `rgba(255,239,201,${alpha})`;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      ctx.lineWidth = 25 + expansion;
      ctx.beginPath();
      ctx.arc(256, 176, 102, 0, Math.PI * 2);
      ctx.stroke();

      ctx.lineWidth = 34 + expansion;
      ctx.beginPath();
      ctx.moveTo(256, 278);
      ctx.lineTo(256, 626);
      ctx.stroke();

      ctx.beginPath();
      ctx.ellipse(256, 650, 22 + expansion * 0.25, 14 + expansion * 0.18, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    };

    drawShape(0.16, 24, 12);
    drawShape(0.12, 12, 5);
    drawShape(0.08, 5, 1);

    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;
    return texture;
  }

  function createHoverGlow() {
    const texture = createHoverGlowTexture();
    if (!texture) return new THREE.Group();
    const material = new THREE.MeshBasicMaterial({
      map: texture,
      transparent: true,
      opacity: 0.62,
      depthWrite: false,
      depthTest: false,
      blending: THREE.AdditiveBlending,
      toneMapped: false,
      side: THREE.DoubleSide,
    });
    material.userData.disposableTexture = texture;
    const plane = new THREE.Mesh(new THREE.PlaneGeometry(190, 286), material);
    plane.rotation.x = -Math.PI / 2;
    plane.position.z = 75;
    plane.renderOrder = 4;
    const group = new THREE.Group();
    group.add(plane);
    group.visible = false;
    return group;
  }

  function createForegroundRenderer() {
    const canvas = document.createElement('canvas');
    canvas.className = 'room-magnifier-foreground';
    canvas.setAttribute('aria-hidden', 'true');
    document.body.append(canvas);
    foregroundCanvas = canvas;

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.04;
    renderer.setPixelRatio(Math.min(2, Math.max(1, window.devicePixelRatio || 1)));
    foregroundRenderer = renderer;
    foregroundScene = new THREE.Scene();
  }

  function resizeForegroundRenderer() {
    if (!foregroundRenderer) return;
    const width = Math.max(1, Math.round(window.innerWidth));
    const height = Math.max(1, Math.round(window.innerHeight));
    foregroundRenderer.setPixelRatio(Math.min(2, Math.max(1, window.devicePixelRatio || 1)));
    foregroundRenderer.setSize(width, height, false);
  }

  function renderForeground() {
    const camera = context.getCamera();
    if (!foregroundRenderer || !foregroundScene || !camera) return;
    resizeForegroundRenderer();
    foregroundRenderer.render(foregroundScene, camera);
  }

  function setMagnifierHovered(next: boolean) {
    document.documentElement.classList.toggle('is-hovering-room-magnifier', next);
    const visible = next && mode !== 'held';
    if (hoverGlow) hoverGlow.visible = visible;
    renderForeground();
  }

  function createLightRig() {
    const rig = new THREE.Group();
    const hemi = new THREE.HemisphereLight(0xfffbf4, 0x322721, 0.9);
    rig.add(hemi);

    // Large, offset highlights make the polished tube read as metal instead of
    // black plastic. The cooler secondary reflection also gives the glass edge a
    // convincing neutral/green optical catchlight.
    const key = new THREE.PointLight(0xfff9ef, 2.05, 1300, 1.55);
    key.position.set(-205, 260, 175);
    rig.add(key);
    const fill = new THREE.PointLight(0xdcecff, 1.15, 1100, 1.55);
    fill.position.set(285, 115, 210);
    rig.add(fill);
    const warmRim = new THREE.PointLight(0xffd5ad, 0.52, 840, 1.65);
    warmRim.position.set(-290, 40, 280);
    rig.add(warmRim);
    return rig;
  }

  function disposeObject(object: THREE.Object3D | null) {
    if (!object) return;
    object.traverse((child) => {
      if (!(child instanceof THREE.Mesh)) return;
      child.geometry.dispose();
      const materials = Array.isArray(child.material) ? child.material : [child.material];
      for (const material of materials) {
        const disposableTexture = material.userData.disposableTexture as THREE.Texture | undefined;
        disposableTexture?.dispose();
        material.dispose();
      }
    });
  }


  function addCollider(desc: any, density = 1, restitution = METAL_RESTITUTION) {
    if (!physicsWorld || !rigidBody) return;
    desc
      .setDensity(density)
      .setFriction(FLOOR_FRICTION)
      .setRestitution(restitution)
      .setRestitutionCombineRule(RAPIER.CoefficientCombineRule.Max);
    physicsWorld.createCollider(desc, rigidBody);
  }

  function removeStaticCollider(collider: any) {
    if (!physicsWorld || !collider) return;
    try {
      physicsWorld.removeCollider(collider, true);
    } catch {
      // The world may already be tearing down.
    }
  }

  function syncPhysicsFloor(force = false) {
    if (!physicsWorld) return false;
    const floor = context.getFloorSurface();
    if (!floor) return false;

    const signature = [
      floor.centerX,
      floor.centerZ,
      floor.width,
      floor.depth,
      floor.y,
    ]
      .map((value) => Math.round(value * 10) / 10)
      .join(':');
    if (!force && signature === floorColliderSignature) return true;

    removeStaticCollider(floorCollider);
    removeStaticCollider(backWallCollider);
    removeStaticCollider(frontWallCollider);
    removeStaticCollider(leftWallCollider);
    removeStaticCollider(rightWallCollider);
    floorCollider = null;
    backWallCollider = null;
    frontWallCollider = null;
    leftWallCollider = null;
    rightWallCollider = null;

    const halfThickness = FLOOR_COLLIDER_THICKNESS / 2;
    floorCollider = physicsWorld.createCollider(
      RAPIER.ColliderDesc.cuboid(floor.width / 2, halfThickness, floor.depth / 2)
        .setTranslation(floor.centerX, floor.y - halfThickness, floor.centerZ)
        .setFriction(FLOOR_FRICTION)
        .setRestitution(FLOOR_RESTITUTION)
        .setRestitutionCombineRule(RAPIER.CoefficientCombineRule.Max)
        .setActiveEvents(RAPIER.ActiveEvents.COLLISION_EVENTS),
    );

    // The visible floor starts exactly at z=0 against the baseboard. This thin
    // static wall makes that same seam physical, so objects cannot fall behind
    // the room when dropped close to the wall.
    backWallCollider = physicsWorld.createCollider(
      RAPIER.ColliderDesc.cuboid(floor.width / 2, 1200, 4)
        .setTranslation(floor.centerX, floor.y + 1200, floor.minZ - 4)
        .setFriction(WALL_FRICTION)
        .setRestitution(WALL_RESTITUTION)
        .setRestitutionCombineRule(RAPIER.CoefficientCombineRule.Max),
    );
    frontWallCollider = physicsWorld.createCollider(
      RAPIER.ColliderDesc.cuboid(floor.width / 2, 1200, 4)
        .setTranslation(floor.centerX, floor.y + 1200, floor.maxZ + 4)
        .setFriction(WALL_FRICTION)
        .setRestitution(WALL_RESTITUTION)
        .setRestitutionCombineRule(RAPIER.CoefficientCombineRule.Max),
    );
    leftWallCollider = physicsWorld.createCollider(
      RAPIER.ColliderDesc.cuboid(4, 1200, floor.depth / 2)
        .setTranslation(floor.minX - 4, floor.y + 1200, floor.centerZ)
        .setFriction(WALL_FRICTION)
        .setRestitution(WALL_RESTITUTION)
        .setRestitutionCombineRule(RAPIER.CoefficientCombineRule.Max),
    );
    rightWallCollider = physicsWorld.createCollider(
      RAPIER.ColliderDesc.cuboid(4, 1200, floor.depth / 2)
        .setTranslation(floor.maxX + 4, floor.y + 1200, floor.centerZ)
        .setFriction(WALL_FRICTION)
        .setRestitution(WALL_RESTITUTION)
        .setRestitutionCombineRule(RAPIER.CoefficientCombineRule.Max),
    );

    floorColliderSignature = signature;
    return true;
  }

  async function waitForFloorSurface() {
    for (let attempt = 0; attempt < 45 && !destroyed; attempt += 1) {
      const floor = context.getFloorSurface();
      if (floor && floor.width > 100 && floor.depth > 100) return floor;
      await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    }
    return null;
  }

  async function createPhysics() {
    await RAPIER.init();
    if (destroyed) return;

    const floor = await waitForFloorSurface();
    if (destroyed) return;
    if (!floor) {
      console.error('[MagnifyingGlass] FloorScene never exposed a valid 3D floor surface.');
      return;
    }

    physicsWorld = new RAPIER.World({ x: 0, y: GRAVITY, z: 0 });
    physicsWorld.timestep = FIXED_STEP;
    physicsEventQueue = new RAPIER.EventQueue(false);

    const host = context.getHostElement();
    const width = host?.getBoundingClientRect().width ?? window.innerWidth;
    const startX = THREE.MathUtils.clamp(
      context.getCameraX() - Math.min(72, width * 0.08),
      floor.minX + BOUNDS_MARGIN_LEFT,
      floor.maxX - BOUNDS_MARGIN_RIGHT,
    );
    const startZ = floor.minZ + WALL_PLANE_OFFSET_Z;

    const restingY = exactMinimumBodyY(cameraFacingQuaternion(), floor.y);
    const bodyDesc = RAPIER.RigidBodyDesc.dynamic()
      .setTranslation(startX, restingY, startZ)
      .setLinearDamping(0.72)
      .setAngularDamping(2.15)
      .setCcdEnabled(true)
      .setCanSleep(true)
      .enabledTranslations(true, true, false)
      .enabledRotations(false, false, true);
    rigidBody = physicsWorld.createRigidBody(bodyDesc);

    // The physical body is constrained to the wall-parallel X/Y plane. These
    // colliders match the camera-facing silhouette: circular metal ring plus a
    // near-vertical ferrule, wood handle, and metal cap leaning slightly right.
    const ringSegments = 24;
    const segmentHalfLength = (Math.PI * 2 * LENS_RADIUS) / ringSegments / 2 * 0.94;
    for (let index = 0; index < ringSegments; index += 1) {
      const angle = (index / ringSegments) * Math.PI * 2;
      const tangentAngle = angle + Math.PI / 2;
      const collider = RAPIER.ColliderDesc.cuboid(segmentHalfLength, RING_TUBE_RADIUS * 0.88, 2.6)
        .setTranslation(Math.cos(angle) * LENS_RADIUS, Math.sin(angle) * LENS_RADIUS, 0)
        .setRotation({
          x: 0,
          y: 0,
          z: Math.sin(tangentAngle / 2),
          w: Math.cos(tangentAngle / 2),
        });
      addCollider(collider, 1.0, METAL_RESTITUTION);
    }

    addCollider(RAPIER.ColliderDesc.cuboid(29, 29, 1.0), 0.05, GLASS_RESTITUTION);
    const ferrulePoint = rotatePhysicsPoint(FERRULE_CENTER_Z, 0);
    const handlePoint = rotatePhysicsPoint(HANDLE_CENTER_Z, 0);
    const capPoint = rotatePhysicsPoint(CAP_CENTER_Z, 0);
    addCollider(
      RAPIER.ColliderDesc.cuboid(FERRULE_HALF_LENGTH, FERRULE_HALF_HEIGHT, 3.5)
        .setTranslation(ferrulePoint.x, ferrulePoint.y, 0)
        .setRotation(zRotationQuaternion(HANDLE_SCREEN_TILT)),
      0.72,
      METAL_RESTITUTION,
    );
    addCollider(
      RAPIER.ColliderDesc.cuboid(HANDLE_HALF_LENGTH, HANDLE_HALF_WIDTH, 3.9)
        .setTranslation(handlePoint.x, handlePoint.y, 0)
        .setRotation(zRotationQuaternion(HANDLE_SCREEN_TILT)),
      0.24,
      WOOD_RESTITUTION,
    );
    addCollider(
      RAPIER.ColliderDesc.cuboid(CAP_HALF_LENGTH, CAP_HALF_HEIGHT, 4.1)
        .setTranslation(capPoint.x, capPoint.y, 0)
        .setRotation(zRotationQuaternion(HANDLE_SCREEN_TILT)),
      0.66,
      METAL_RESTITUTION,
    );

    // Mirror the exact Three.js checkerboard plane in Rapier. No second set of
    // guessed dimensions: render geometry and collision geometry share the same
    // X/Z coordinate system and floor/wall seam.
    if (!syncPhysicsFloor(true)) {
      console.error('[MagnifyingGlass] Could not build the Rapier floor collider.');
      return;
    }

    rigidBody.recomputeMassPropertiesFromColliders?.();
    // The default prop begins already resting on the floor. Sleeping it before
    // the first simulation frame avoids tiny solver corrections that otherwise
    // read as visible startup shaking.
    rigidBody.setLinvel({ x: 0, y: 0, z: 0 }, false);
    rigidBody.setAngvel({ x: 0, y: 0, z: 0 }, false);
    rigidBody.sleep();
    physicsReady = true;
    mode = 'idle';
    updateLightRig();
    syncVisualFromBody();
    enforceViewportBounds(false);
    rememberViewportSafeState();
    updateHitButton();
    createOverlay();
    captureRoomSnapshot();
    requestAnimationFrame(() => updateLensOverlay());
    context.requestRender();
    renderForeground();
  }

  function bodySpinAngle() {
    if (!rigidBody) return 0;
    const rotation = rigidBody.rotation();
    // Only Rapier's Z rotation is enabled, so this is the complete in-plane
    // angle of the physical prop. Normalise for stable interpolation/projection.
    return 2 * Math.atan2(rotation.z, rotation.w);
  }

  function cameraFacingQuaternion(spin = 0) {
    const camera = context.getCamera();
    if (!camera) return new THREE.Quaternion();
    camera.updateMatrixWorld(true);
    const right = new THREE.Vector3(1, 0, 0).applyQuaternion(camera.quaternion).normalize();
    const up = new THREE.Vector3(0, 1, 0).applyQuaternion(camera.quaternion).normalize();
    const towardCamera = new THREE.Vector3(0, 0, 1).applyQuaternion(camera.quaternion).normalize();
    const basis = new THREE.Matrix4().makeBasis(up, towardCamera, right);
    const facing = new THREE.Quaternion().setFromRotationMatrix(basis).normalize();
    // The lens normal stays camera-facing. Rapier may only add a rotation around
    // that normal, allowing the whole magnifier to tip over within the wall plane.
    const inPlane = new THREE.Quaternion().setFromAxisAngle(
      new THREE.Vector3(0, 1, 0),
      HANDLE_SCREEN_TILT + spin,
    );
    return facing.multiply(inPlane).normalize();
  }

  function wallPlaneZ() {
    return (context.getFloorSurface()?.minZ ?? 0) + WALL_PLANE_OFFSET_Z;
  }

  function exactMinimumBodyY(quaternion: THREE.Quaternion, floorY: number) {
    if (!magnifierBoundsLocalVertices.length) return floorY + OUTER_RING_RADIUS;
    let lowestOffset = Infinity;
    for (const localVertex of magnifierBoundsLocalVertices) {
      const offsetY = tmpVectorC.copy(localVertex).applyQuaternion(quaternion).y;
      lowestOffset = Math.min(lowestOffset, offsetY);
    }
    return floorY - lowestOffset + FLOOR_VISUAL_EPSILON;
  }

  function rotatePhysicsPoint(x: number, y: number) {
    const c = Math.cos(HANDLE_SCREEN_TILT);
    const s = Math.sin(HANDLE_SCREEN_TILT);
    return { x: x * c - y * s, y: x * s + y * c };
  }

  function zRotationQuaternion(angle: number) {
    return { x: 0, y: 0, z: Math.sin(angle / 2), w: Math.cos(angle / 2) };
  }

  function syncVisualFromBody() {
    if (!magnifier || !rigidBody) return;
    const translation = rigidBody.translation();
    magnifier.position.set(translation.x, translation.y, wallPlaneZ());
    magnifier.quaternion.copy(cameraFacingQuaternion(bodySpinAngle()));
    magnifier.updateMatrixWorld(true);
    updateShadow();
  }

  function worldPointFromLocal(local: THREE.Vector3) {
    if (!magnifier) return null;
    magnifier.updateWorldMatrix(true, false);
    return magnifier.localToWorld(local.clone());
  }

  function projectWorldPoint(point: THREE.Vector3) {
    const camera = context.getCamera();
    const host = context.getHostElement();
    if (!camera || !host) return null;
    const rect = host.getBoundingClientRect();
    const projected = point.clone().project(camera);
    if (projected.z < -1 || projected.z > 1) return null;
    return {
      x: rect.left + (projected.x * 0.5 + 0.5) * rect.width,
      y: rect.top + (-projected.y * 0.5 + 0.5) * rect.height,
    };
  }

  function updateShadow() {
    if (!shadow || !softShadow || !magnifier) return;
    const camera = context.getCamera();
    if (!camera) return;

    // The prop sits only a few world units off the wall. Build the wall shadow
    // from the exact opaque geometry, offset down/right as if lit from the
    // upper-left. Both shadow layers inherit the magnifier's real in-plane spin.
    const right = new THREE.Vector3(1, 0, 0).applyQuaternion(camera.quaternion).normalize();
    const up = new THREE.Vector3(0, 1, 0).applyQuaternion(camera.quaternion).normalize();
    const towardCamera = new THREE.Vector3(0, 0, 1).applyQuaternion(camera.quaternion).normalize();

    const place = (layer: THREE.Group, x: number, y: number, depth: number) => {
      layer.quaternion.copy(magnifier.quaternion);
      layer.position
        .copy(magnifier.position)
        .addScaledVector(right, x)
        .addScaledVector(up, y)
        .addScaledVector(towardCamera, -depth);
    };

    place(softShadow, 4.7, -5.8, 2.7);
    place(shadow, 3.2, -4.0, 2.25);
    shadow.visible = true;
    softShadow.visible = true;
    if (hoverGlow) {
      hoverGlow.position.copy(magnifier.position);
      hoverGlow.quaternion.copy(magnifier.quaternion);
    }
  }

  function updateLightRig() {
    if (!lightRig) return;
    const camera = context.getCamera();
    if (!camera) return;
    lightRig.position.copy(camera.position);
  }

  function handleScreenSegment() {
    const grip = worldPointFromLocal(GRIP_LOCAL);
    const cap = worldPointFromLocal(CAP_LOCAL);
    if (!grip || !cap) return null;
    const gripScreen = projectWorldPoint(grip);
    const capScreen = projectWorldPoint(cap);
    if (!gripScreen || !capScreen) return null;
    return { gripScreen, capScreen };
  }

  function pointerHitsMagnifier(clientX: number, clientY: number) {
    if (!physicsReady || mode === 'held' || !magnifier) return false;
    const ray = pointerRay(clientX, clientY);
    if (!ray) return false;
    magnifier.updateMatrixWorld(true);
    const raycaster = new THREE.Raycaster();
    raycaster.ray.copy(ray);
    // Raycast the actual ring, lens, ferrule, wood and cap meshes. This makes
    // the whole visible prop selectable rather than only an invisible handle
    // strip, while still ignoring empty space inside its screen bounding box.
    return raycaster.intersectObject(magnifier, true).length > 0;
  }

  function updateHitButton() {
    if (!hitButton || !physicsReady || mode === 'held' || !magnifier) {
      if (hitButton) hitButton.style.display = 'none';
      return;
    }

    // Use the exact projected mesh bounds as the native pointer/touch target.
    // This is especially important on iOS: the button receives the touch before
    // the text underneath can trigger Safari's long-press selection loupe.
    const bounds = projectedMagnifierBounds();
    if (!bounds) {
      hitButton.style.display = 'none';
      return;
    }

    const width = Math.max(1, bounds.right - bounds.left);
    const height = Math.max(1, bounds.bottom - bounds.top);
    hitButton.style.display = 'block';
    hitButton.style.left = `${bounds.left}px`;
    hitButton.style.top = `${bounds.top}px`;
    hitButton.style.width = `${width}px`;
    hitButton.style.height = `${height}px`;
    hitButton.style.transform = 'none';
    hitButton.style.setProperty('--magnifier-hit-width', `${width}px`);
    hitButton.style.setProperty('--magnifier-hit-height', `${height}px`);
    hitButton.style.setProperty('--magnifier-hit-angle', '0deg');
  }

  function pointerRay(clientX: number, clientY: number) {
    const camera = context.getCamera();
    const host = context.getHostElement();
    if (!camera || !host) return null;
    const rect = host.getBoundingClientRect();
    const ndc = new THREE.Vector2(
      ((clientX - rect.left) / rect.width) * 2 - 1,
      -((clientY - rect.top) / rect.height) * 2 + 1,
    );
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(ndc, camera);
    return raycaster.ray.clone();
  }

  function computeHeldTarget(clientX: number, clientY: number): TransformTarget | null {
    const ray = pointerRay(clientX, clientY);
    const floor = context.getFloorSurface();
    if (!ray || !floor) return null;

    const quaternion = cameraFacingQuaternion();
    const rotatedCap = CAP_LOCAL.clone().applyQuaternion(quaternion);
    const rootZ = floor.minZ + WALL_PLANE_OFFSET_Z;
    const capZ = rootZ + rotatedCap.z;
    if (Math.abs(ray.direction.z) < 1e-5) return null;
    const distance = (capZ - ray.origin.z) / ray.direction.z;
    if (distance <= 0) return null;
    const capTarget = ray.at(distance, tmpVectorB);
    const position = capTarget.clone().sub(rotatedCap);
    position.z = rootZ;
    position.x = THREE.MathUtils.clamp(
      position.x,
      floor.minX + BOUNDS_MARGIN_LEFT,
      floor.maxX - BOUNDS_MARGIN_RIGHT,
    );
    position.y = Math.max(position.y, exactMinimumBodyY(quaternion, floor.y));
    return { position, quaternion };
  }

  function createOverlay() {
    if (overlayRoot) return;
    const root = document.createElement('div');
    root.className = 'room-magnifier-overlay';
    const lens = document.createElement('div');
    lens.className = 'room-magnifier-overlay__lens';
    root.append(lens);
    document.body.append(root);
    overlayRoot = root;
    lensViewport = lens;
  }

  function destroyOverlay() {
    snapshotRoom?.remove();
    snapshotRoom = null;
    lensViewport = null;
    overlayRoot?.remove();
    overlayRoot = null;
  }

  function copyCanvasPixels(sourceRoom: HTMLElement, clonedRoom: HTMLElement) {
    const sourceCanvases = [...sourceRoom.querySelectorAll<HTMLCanvasElement>('canvas')];
    const clonedCanvases = [...clonedRoom.querySelectorAll<HTMLCanvasElement>('canvas')];
    sourceCanvases.forEach((source, index) => {
      const clone = clonedCanvases[index];
      if (!clone) return;
      try {
        clone.width = source.width;
        clone.height = source.height;
        const ctx = clone.getContext('2d');
        if (ctx) ctx.drawImage(source, 0, 0, clone.width, clone.height);
      } catch {
        // DOM content still magnifies if a browser declines to copy a WebGL buffer.
      }
    });
  }

  function captureRoomSnapshot() {
    if (!lensViewport) return;
    const floorHost = context.getHostElement();
    const sourceRoom = floorHost?.closest<HTMLElement>('.about-room');
    const sourceHeader = document.querySelector<HTMLElement>('.site-header');
    if (!sourceRoom) return;

    const snapshot = document.createElement('div');
    snapshot.className = 'room-magnifier-overlay__snapshot';
    snapshot.setAttribute('aria-hidden', 'true');
    snapshot.style.width = `${Math.max(window.innerWidth, document.documentElement.clientWidth)}px`;
    snapshot.style.height = `${Math.max(window.innerHeight, document.documentElement.clientHeight)}px`;
    snapshot.style.pointerEvents = 'none';

    const appendClone = (source: HTMLElement, kind: 'room' | 'header') => {
      const rect = source.getBoundingClientRect();
      const clone = source.cloneNode(true) as HTMLElement;
      clone.querySelectorAll('.floor-scene__registrants, .room-magnifier-hit, .room-magnifier-overlay').forEach((node) => node.remove());
      if (kind === 'header') {
        clone.classList.add('room-magnifier-overlay__header-clone');
        const liveHeaderStyle = getComputedStyle(source);
        clone.style.setProperty('--nav-ink', liveHeaderStyle.getPropertyValue('--nav-ink').trim() || liveHeaderStyle.color);
        clone.style.setProperty('--nav-border-color', liveHeaderStyle.getPropertyValue('--nav-border-color').trim());
        clone.style.setProperty('--nav-underline-color', liveHeaderStyle.getPropertyValue('--nav-underline-color').trim());
        clone.style.color = liveHeaderStyle.color;
        clone.style.opacity = '1';
        clone.style.visibility = 'visible';
      }
      clone.style.position = 'absolute';
      clone.style.inset = 'auto';
      clone.style.left = `${rect.left}px`;
      clone.style.top = `${rect.top}px`;
      clone.style.width = `${rect.width}px`;
      clone.style.height = `${rect.height}px`;
      clone.style.minHeight = '0';
      clone.style.margin = '0';
      clone.style.transform = 'none';
      clone.style.pointerEvents = 'none';
      clone.style.zIndex = kind === 'header' ? '2' : '1';
      snapshot.append(clone);
      return clone;
    };

    const roomClone = appendClone(sourceRoom, 'room');
    if (sourceHeader) appendClone(sourceHeader, 'header');
    snapshotRoom?.remove();
    snapshotRoom = snapshot;
    lensViewport.prepend(snapshot);

    // The magnifier itself now lives in a top-level foreground canvas outside
    // .about-room, so it is not part of this cloned optical sample. No temporary
    // hide/show handoff is needed and the prop never flickers during pickup.
    requestAnimationFrame(() => {
      copyCanvasPixels(sourceRoom, roomClone);
    });
  }

  function updateLensOverlay() {
    if (!lensViewport || !snapshotRoom || !magnifier) return;

    const centerWorld = worldPointFromLocal(new THREE.Vector3(0, LENS_PLANE_Y, 0));
    const edgeWorld = worldPointFromLocal(new THREE.Vector3(LENS_VIEW_RADIUS, LENS_PLANE_Y, 0));
    if (!centerWorld || !edgeWorld) return;
    const center = projectWorldPoint(centerWorld);
    const edge = projectWorldPoint(edgeWorld);
    if (!center || !edge) {
      lensViewport.style.opacity = '0';
      return;
    }

    // The lens is constrained to remain camera-facing, so its optical aperture
    // projects to a true circle. Use that exact projected circle as a small fixed
    // viewport instead of clipping a full-screen overlay. This keeps the glass
    // perfectly seated inside the ring on iOS Safari even while the visual
    // viewport changes as browser chrome expands/collapses.
    const radius = Math.max(1, Math.hypot(edge.x - center.x, edge.y - center.y));
    const diameter = radius * 2;
    lensViewport.style.opacity = '1';
    lensViewport.style.left = `${center.x - radius}px`;
    lensViewport.style.top = `${center.y - radius}px`;
    lensViewport.style.width = `${diameter}px`;
    lensViewport.style.height = `${diameter}px`;
    lensViewport.style.transform = 'none';
    lensViewport.style.clipPath = 'none';
    lensViewport.style.borderRadius = '50%';

    // snapshotRoom is authored in viewport coordinates. Translate its global
    // coordinate system into this local circular viewport, then scale around the
    // true lens center. The optical scene remains upright while the hardware may
    // rotate around its camera-facing normal.
    const tx = radius - center.x * MAGNIFICATION;
    const ty = radius - center.y * MAGNIFICATION;
    snapshotRoom.style.transform = `translate3d(${tx}px, ${ty}px, 0) scale(${MAGNIFICATION})`;
  }

  function setBodyTransform(position: THREE.Vector3, _quaternion: THREE.Quaternion) {
    if (!rigidBody) return;
    rigidBody.setTranslation({ x: position.x, y: position.y, z: wallPlaneZ() }, true);
    // Picking it up returns the prop to its normal hand-held angle. After
    // release Rapier is free to rotate it around Z again as it lands.
    rigidBody.setRotation({ x: 0, y: 0, z: 0, w: 1 }, true);
    rigidBody.setLinvel({ x: 0, y: 0, z: 0 }, true);
    rigidBody.setAngvel({ x: 0, y: 0, z: 0 }, true);
    syncVisualFromBody();
  }

  function beginPickup(event: PointerEvent) {
    if (!physicsReady || !rigidBody || !magnifier || mode === 'held' || activePointerId !== null) return;
    event.preventDefault();
    event.stopPropagation();
    activePointerId = event.pointerId;
    if (event.currentTarget instanceof Element && 'setPointerCapture' in event.currentTarget) {
      try { (event.currentTarget as Element & { setPointerCapture(id: number): void }).setPointerCapture(event.pointerId); } catch {}
    }
    pointerX = event.clientX;
    pointerY = event.clientY;
    pointerSampleTime = performance.now();
    lastTargetPosition = null;
    filteredReleaseVelocity.set(0, 0, 0);

    const t = rigidBody.translation();
    heldPosition.set(t.x, t.y, wallPlaneZ());
    heldQuaternion.copy(cameraFacingQuaternion());
    rigidBody.wakeUp();
    rigidBody.setGravityScale(0, true);
    mode = 'held';
    if (hitButton) hitButton.style.display = 'none';
    setMagnifierHovered(false);
    document.documentElement.classList.add('is-using-room-magnifier');
    createOverlay();
    captureRoomSnapshot();
    startAnimation();
  }

  function handleMagnifierTouchStart(event: TouchEvent) {
    const touch = event.touches[0];
    if (!touch) return;
    if (!pointerHitsMagnifier(touch.clientX, touch.clientY)) return;
    if (event.cancelable) event.preventDefault();
  }

  function handleMagnifierContextMenu(event: MouseEvent) {
    if (!pointerHitsMagnifier(event.clientX, event.clientY)) return;
    event.preventDefault();
  }

  function handleGlobalPointerDown(event: PointerEvent) {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    if (!pointerHitsMagnifier(event.clientX, event.clientY)) return;
    beginPickup(event);
  }

  function handlePointerMove(event: PointerEvent) {
    if (mode !== 'held' || event.pointerId !== activePointerId) {
      setMagnifierHovered(pointerHitsMagnifier(event.clientX, event.clientY));
      return;
    }
    setMagnifierHovered(false);
    if (event.cancelable) event.preventDefault();
    pointerX = event.clientX;
    pointerY = event.clientY;

    const now = performance.now();
    const target = computeHeldTarget(pointerX, pointerY);
    if (target && lastTargetPosition) {
      const dt = Math.max(1 / 240, (now - pointerSampleTime) / 1000);
      const sample = target.position.clone().sub(lastTargetPosition).divideScalar(dt);
      sample.z = 0;
      if (sample.length() > MAX_RELEASE_SPEED) sample.setLength(MAX_RELEASE_SPEED);
      filteredReleaseVelocity.lerp(sample, 0.4);

    }
    if (target) lastTargetPosition = target.position.clone();
    pointerSampleTime = now;
  }

  function releaseHeld(event: PointerEvent) {
    if (mode !== 'held' || event.pointerId !== activePointerId || !rigidBody) return;
    activePointerId = null;
    mode = 'airborne';
    rigidBody.setGravityScale(1, true);
    if (!overlayRoot || !snapshotRoom) {
      createOverlay();
      captureRoomSnapshot();
    }

    const linear = filteredReleaseVelocity.clone();
    linear.z = 0;
    if (linear.length() > MAX_RELEASE_SPEED) linear.setLength(MAX_RELEASE_SPEED);
    rigidBody.setLinvel({ x: linear.x, y: linear.y, z: 0 }, true);
    // X/Y rotations stay disabled, so the glass always faces the camera. Z is
    // intentionally free: this lets the whole prop tip over in the wall plane
    // when its cap/ring contacts the floor.
    rigidBody.setAngvel({ x: 0, y: 0, z: THREE.MathUtils.clamp(-linear.x * 0.0014, -1.6, 1.6) }, true);
    rigidBody.wakeUp();
    startAnimation();
  }

  function handlePointerCancel(event: PointerEvent) {
    releaseHeld(event);
  }

  function stepHeld() {
    if (!rigidBody) return;
    const target = computeHeldTarget(pointerX, pointerY);
    if (!target) return;
    heldPosition.lerp(target.position, PICKUP_FOLLOW);
    heldQuaternion.copy(target.quaternion);
    heldPosition.z = wallPlaneZ();
    setBodyTransform(heldPosition, heldQuaternion);
    enforceExactFloorBoundary(false);
    enforceViewportBounds(false);
    enforceExactFloorBoundary(false);
    syncVisualFromBody();
    if (!rememberViewportSafeState() && lastViewportSafeState) {
      applyBodyState(lastViewportSafeState, false);
      syncVisualFromBody();
      heldPosition.copy(lastViewportSafeState.position);
      heldQuaternion.copy(lastViewportSafeState.rotation);
    }
    updateLensOverlay();
  }

  function assistHardFloorImpact() {
    if (!rigidBody || !floorCollider || !physicsEventQueue) return;
    let hitFloor = false;
    physicsEventQueue.drainCollisionEvents((handle1: number, handle2: number, started: boolean) => {
      if (!started) return;
      if (handle1 === floorCollider.handle || handle2 === floorCollider.handle) hitFloor = true;
    });
    if (!hitFloor || preStepVerticalVelocity > -MIN_HARD_IMPACT_SPEED) return;

    const now = performance.now();
    if (now - lastBounceAssistAt < 120) return;
    const velocity = rigidBody.linvel();
    const desiredBounce = Math.min(
      MAX_ASSISTED_BOUNCE_SPEED,
      Math.abs(preStepVerticalVelocity) * IMPACT_ASSIST_FACTOR,
    );

    // Compound contacts (ring + lens plate + handle) can numerically dissipate a
    // hard impact more than a single collider would. Only intervene when Rapier's
    // own restitution produced less than half of the expected small rebound.
    if (velocity.y < desiredBounce * 0.5) {
      rigidBody.setLinvel(
        { x: velocity.x, y: desiredBounce, z: velocity.z },
        true,
      );
      const angular = rigidBody.angvel();
      const tip = Math.abs(angular.z) < 0.18
        ? (velocity.x >= 0 ? -0.72 : 0.72)
        : angular.z;
      rigidBody.setAngvel({ x: 0, y: 0, z: tip }, true);
      rigidBody.wakeUp();
    }
    lastBounceAssistAt = now;
  }

  function projectedMagnifierBounds(): ProjectedBounds | null {
    if (!magnifier || !magnifierBoundsLocalVertices.length) return null;
    magnifier.updateMatrixWorld(true);
    let left = Infinity;
    let right = -Infinity;
    let top = Infinity;
    let bottom = -Infinity;
    let count = 0;
    for (const localVertex of magnifierBoundsLocalVertices) {
      const world = tmpVectorC.copy(localVertex).applyMatrix4(magnifier.matrixWorld);
      const point = projectWorldPoint(world);
      if (!point) continue;
      left = Math.min(left, point.x);
      right = Math.max(right, point.x);
      top = Math.min(top, point.y);
      bottom = Math.max(bottom, point.y);
      count += 1;
    }
    return count ? { left, right, top, bottom } : null;
  }

  function enforceViewportBounds(wake = true) {
    if (!rigidBody || !magnifier) return;

    for (let pass = 0; pass < 5; pass += 1) {
      syncVisualFromBody();
      const bounds = projectedMagnifierBounds();
      if (!bounds) return;

      let dxPixels = 0;
      let dyPixels = 0;
      if (bounds.left < VIEWPORT_MARGIN) dxPixels += VIEWPORT_MARGIN - bounds.left;
      if (bounds.right > window.innerWidth - VIEWPORT_MARGIN) {
        dxPixels -= bounds.right - (window.innerWidth - VIEWPORT_MARGIN);
      }
      if (bounds.top < VIEWPORT_MARGIN) dyPixels += VIEWPORT_MARGIN - bounds.top;
      if (bounds.bottom > window.innerHeight - VIEWPORT_MARGIN) {
        dyPixels -= bounds.bottom - (window.innerHeight - VIEWPORT_MARGIN);
      }
      if (Math.abs(dxPixels) < 0.08 && Math.abs(dyPixels) < 0.08) {
        rememberViewportSafeState();
        return;
      }

      const translation = rigidBody.translation();
      const center = new THREE.Vector3(translation.x, translation.y, wallPlaneZ());
      const centerScreen = projectWorldPoint(center);
      const xProbe = projectWorldPoint(center.clone().add(new THREE.Vector3(1, 0, 0)));
      const yProbe = projectWorldPoint(center.clone().add(new THREE.Vector3(0, 1, 0)));
      if (!centerScreen || !xProbe || !yProbe) break;

      const j11 = xProbe.x - centerScreen.x;
      const j21 = xProbe.y - centerScreen.y;
      const j12 = yProbe.x - centerScreen.x;
      const j22 = yProbe.y - centerScreen.y;
      const determinant = j11 * j22 - j12 * j21;
      if (Math.abs(determinant) < 1e-6) break;

      const worldDx = (dxPixels * j22 - j12 * dyPixels) / determinant;
      const worldDy = (j11 * dyPixels - dxPixels * j21) / determinant;
      const velocity = rigidBody.linvel();
      const hitHorizontal = Math.abs(dxPixels) >= 0.08;
      const hitVertical = Math.abs(dyPixels) >= 0.08;
      rigidBody.setTranslation(
        {
          x: translation.x + worldDx,
          y: translation.y + worldDy,
          z: wallPlaneZ(),
        },
        wake,
      );
      rigidBody.setLinvel(
        {
          x: hitHorizontal ? -velocity.x * 0.46 : velocity.x,
          y: hitVertical ? -velocity.y * 0.34 : velocity.y,
          z: 0,
        },
        wake,
      );
      rigidBody.setAngvel({ x: 0, y: 0, z: rigidBody.angvel().z * 0.72 }, wake);
    }

    syncVisualFromBody();
    if (!viewportBoundsInside(projectedMagnifierBounds()) && lastViewportSafeState) {
      const fallback = lastViewportSafeState;
      rigidBody.setTranslation(
        { x: fallback.position.x, y: fallback.position.y, z: wallPlaneZ() },
        wake,
      );
      rigidBody.setRotation(
        { x: fallback.rotation.x, y: fallback.rotation.y, z: fallback.rotation.z, w: fallback.rotation.w },
        wake,
      );
      rigidBody.setLinvel({ x: -fallback.linvel.x * 0.35, y: -fallback.linvel.y * 0.28, z: 0 }, wake);
      rigidBody.setAngvel({ x: 0, y: 0, z: -fallback.angvel.z * 0.55 }, wake);
      syncVisualFromBody();
    }
  }

  function enforceExactFloorBoundary(wake = true) {
    if (!rigidBody) return;
    const floor = context.getFloorSurface();
    if (!floor) return;
    const minimumY = exactMinimumBodyY(cameraFacingQuaternion(), floor.y);
    const translation = rigidBody.translation();
    if (translation.y >= minimumY) return;
    const velocity = rigidBody.linvel();
    rigidBody.setTranslation({ x: translation.x, y: minimumY, z: wallPlaneZ() }, wake);
    rigidBody.setLinvel(
      { x: velocity.x, y: velocity.y < 0 ? -velocity.y * 0.2 : velocity.y, z: 0 },
      wake,
    );
    rigidBody.setAngvel({ x: 0, y: 0, z: 0 }, wake);
  }

  function enforceRoomBounds() {
    if (!rigidBody) return;
    const floor = context.getFloorSurface();
    if (!floor) return;

    const translation = rigidBody.translation();
    const minX = floor.minX + BOUNDS_MARGIN_LEFT;
    const maxX = floor.maxX - BOUNDS_MARGIN_RIGHT;
    const clampedX = THREE.MathUtils.clamp(translation.x, minX, maxX);
    const velocity = rigidBody.linvel();
    const hitX = clampedX !== translation.x;
    if (hitX || Math.abs(translation.z - wallPlaneZ()) > 0.001 || Math.abs(velocity.z) > 0.001) {
      rigidBody.setTranslation({ x: clampedX, y: translation.y, z: wallPlaneZ() }, true);
      rigidBody.setLinvel({ x: hitX ? -velocity.x * 0.42 : velocity.x, y: velocity.y, z: 0 }, true);
      const angular = rigidBody.angvel();
      rigidBody.setAngvel({ x: 0, y: 0, z: hitX ? -angular.z * 0.7 : angular.z }, true);
      rigidBody.wakeUp();
    }
  }

  function stepPhysics(deltaSeconds: number) {
    if (!physicsWorld || !rigidBody) return;
    syncPhysicsFloor();
    physicsAccumulator += Math.min(deltaSeconds, 0.05);
    while (physicsAccumulator >= FIXED_STEP) {
      const previousState = captureBodyState();
      preStepVerticalVelocity = rigidBody.linvel().y;
      physicsWorld.step(physicsEventQueue);
      assistHardFloorImpact();
      enforceRoomBounds();
      enforceViewportBounds(true);
      syncVisualFromBody();
      const bounds = projectedMagnifierBounds();
      if (!viewportBoundsInside(bounds) && previousState) {
        const fallbackState = lastViewportSafeState ?? previousState;
        const hit = viewportViolations(bounds);
        const bounced = {
          position: fallbackState.position.clone(),
          rotation: fallbackState.rotation.clone(),
          linvel: fallbackState.linvel.clone(),
          angvel: fallbackState.angvel.clone(),
        };
        if (hit.left || hit.right) {
          bounced.linvel.x = -fallbackState.linvel.x * 0.42;
          bounced.angvel.z *= -0.55;
        }
        if (hit.top || hit.bottom) {
          bounced.linvel.y = Math.abs(fallbackState.linvel.y) * 0.14;
          bounced.linvel.z = 0;
          bounced.angvel.z *= -0.55;
        }
        applyBodyState(bounced, true);
        rigidBody.wakeUp();
        syncVisualFromBody();
        rememberViewportSafeState();
      } else {
        rememberViewportSafeState();
      }
      physicsAccumulator -= FIXED_STEP;
    }
    syncVisualFromBody();

    const translation = rigidBody.translation();
    const floor = context.getFloorSurface();
    if (floor && translation.y < floor.y - 90) {
      // CCD should make this unreachable, but recovering onto the real floor is
      // safer than allowing a prop to vanish forever after a browser stall.
      const velocity = rigidBody.linvel();
      rigidBody.setTranslation(
        {
          x: THREE.MathUtils.clamp(translation.x, floor.minX + BOUNDS_MARGIN_LEFT, floor.maxX - BOUNDS_MARGIN_RIGHT),
          y: exactMinimumBodyY(cameraFacingQuaternion(), floor.y) + 10,
          z: wallPlaneZ(),
        },
        true,
      );
      rigidBody.setLinvel({ x: velocity.x * 0.55, y: Math.abs(velocity.y) * 0.08, z: 0 }, true);
      rigidBody.setAngvel({ x: 0, y: 0, z: 0.65 }, true);
      syncVisualFromBody();
      return;
    }
    if (mode === 'airborne') {
      // Keep the optical view alive for the complete rigid-body motion: falling,
      // bouncing and sliding. Orientation stays camera-facing throughout, and the
      // overlay disappears only once Rapier itself has put the body to sleep.
      updateLensOverlay();
    }

    updateHitButton();

    // Do not infer settling from hand-picked velocity thresholds. Rapier owns the
    // rigid body's sleep state, so the render/physics loop continues until the
    // solver has genuinely completed all contact and damping motion.
    if ((mode === 'settling' || mode === 'airborne') && rigidBody.isSleeping()) {
      mode = 'idle';
      document.documentElement.classList.remove('is-using-room-magnifier');
      createOverlay();
      captureRoomSnapshot();
      updateLensOverlay();
      updateHitButton();
    }
  }

  function animate(now: number) {
    animationFrame = 0;
    if (destroyed || !physicsReady) return;
    const deltaSeconds = previousFrameTime ? (now - previousFrameTime) / 1000 : FIXED_STEP;
    previousFrameTime = now;
    updateLightRig();

    if (mode === 'held') stepHeld();
    else stepPhysics(deltaSeconds);

    context.requestRender();
    renderForeground();
    if (mode !== 'idle') animationFrame = requestAnimationFrame(animate);
  }

  function startAnimation() {
    if (animationFrame) return;
    previousFrameTime = 0;
    animationFrame = requestAnimationFrame(animate);
  }

  function handleResize() {
    syncPhysicsFloor();
    updateLightRig();
    if (physicsReady && mode !== 'held') {
      enforceViewportBounds(false);
      syncVisualFromBody();
      if (!rememberViewportSafeState() && lastViewportSafeState) {
        applyBodyState(lastViewportSafeState, false);
        syncVisualFromBody();
      }
    }
    if (mode !== 'held') updateHitButton();
    if (overlayRoot) updateLensOverlay();
    context.requestRender();
    renderForeground();
  }

  onMount(() => {
    magnifier = createMagnifierModel();
    shadow = createShadow(magnifier);
    softShadow = createSoftShadow(magnifier);
    hoverGlow = createHoverGlow();
    lightRig = createLightRig();
    createForegroundRenderer();
    if (foregroundScene && softShadow && shadow && hoverGlow && magnifier && lightRig) {
      foregroundScene.add(softShadow, shadow, hoverGlow, magnifier, lightRig);
    }
    resizeForegroundRenderer();
    context.requestRender();
    renderForeground();

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'room-magnifier-hit';
    button.setAttribute('aria-label', 'Pick up the magnifying glass');
    button.addEventListener('pointerdown', beginPickup);
    button.addEventListener('focus', () => setMagnifierHovered(true));
    button.addEventListener('blur', () => setMagnifierHovered(false));
    document.body.append(button);
    hitButton = button;

    window.addEventListener('pointerdown', handleGlobalPointerDown, { capture: true, passive: false });
    window.addEventListener('touchstart', handleMagnifierTouchStart, { capture: true, passive: false });
    window.addEventListener('contextmenu', handleMagnifierContextMenu, { capture: true });
    window.addEventListener('pointermove', handlePointerMove, { passive: false });
    window.addEventListener('pointerup', releaseHeld);
    window.addEventListener('pointercancel', handlePointerCancel);
    window.addEventListener('resize', handleResize, { passive: true });
    visualViewport = window.visualViewport ?? null;
    visualViewport?.addEventListener('resize', handleResize, { passive: true });
    visualViewport?.addEventListener('scroll', handleResize, { passive: true });

    void createPhysics();

    return () => {
      destroyed = true;
      if (animationFrame) cancelAnimationFrame(animationFrame);
      window.removeEventListener('pointerdown', handleGlobalPointerDown, true);
      window.removeEventListener('touchstart', handleMagnifierTouchStart, true);
      window.removeEventListener('contextmenu', handleMagnifierContextMenu, true);
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', releaseHeld);
      window.removeEventListener('pointercancel', handlePointerCancel);
      window.removeEventListener('resize', handleResize);
      visualViewport?.removeEventListener('resize', handleResize);
      visualViewport?.removeEventListener('scroll', handleResize);
      visualViewport = null;
      document.documentElement.classList.remove('is-using-room-magnifier');
      document.documentElement.classList.remove('is-hovering-room-magnifier');
      hitButton?.removeEventListener('pointerdown', beginPickup);
      hitButton?.remove();
      hitButton = null;
      destroyOverlay();
      foregroundScene?.clear();
      disposeObject(hoverGlow);
      disposeObject(softShadow);
      disposeObject(shadow);
      disposeObject(magnifier);
      foregroundRenderer?.dispose();
      foregroundCanvas?.remove();
      magnifier = null;
      shadow = null;
      softShadow = null;
      hoverGlow = null;
      lightRig = null;
      foregroundScene = null;
      foregroundRenderer = null;
      foregroundCanvas = null;
      rigidBody = null;
      floorCollider = null;
      backWallCollider = null;
      frontWallCollider = null;
      leftWallCollider = null;
      rightWallCollider = null;
      floorColliderSignature = '';
      physicsEventQueue?.free?.();
      physicsEventQueue = null;
      physicsWorld?.free();
      physicsWorld = null;
      physicsReady = false;
      context.requestRender();
    };
  });
</script>

<span aria-hidden="true"></span>
