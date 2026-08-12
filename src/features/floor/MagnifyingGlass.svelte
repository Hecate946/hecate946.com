<script lang="ts">
  import { getContext, onMount } from 'svelte';
  import * as THREE from 'three';
  import RAPIER from '@dimforge/rapier3d-compat';
  import { FLOOR_SCENE_CONTEXT, type FloorSceneContext } from './floor-scene-context';
  import '@/styles/magnifying-glass.css';

  const context = getContext<FloorSceneContext>(FLOOR_SCENE_CONTEXT);

  const LENS_RADIUS = 38;
  const RING_TUBE_RADIUS = 4.7;
  const HANDLE_HALF_WIDTH = 8.2;
  const HANDLE_HALF_HEIGHT = 3.68;
  const HANDLE_Y = 0.88;
  const HANDLE_CENTER_Z = 111;
  const HANDLE_HALF_LENGTH = 52;
  const FERRULE_CENTER_Z = 49;
  const FERRULE_HALF_LENGTH = 11.5;
  const FERRULE_HALF_HEIGHT = 3.15;
  const FERRULE_Y = 0.35;
  const CAP_CENTER_Z = 166;
  const CAP_HALF_LENGTH = 4.5;
  const CAP_HALF_HEIGHT = 3.95;
  const CAP_Y = 1.15;
  const CAP_LOCAL = new THREE.Vector3(0, 0, CAP_CENTER_Z + CAP_HALF_LENGTH);
  const GRIP_LOCAL = new THREE.Vector3(0, 0, 147);
  const LENS_EDGE_LOCAL = new THREE.Vector3(LENS_RADIUS, 0, 0);

  const HELD_LENS_RADIUS = 78;
  const HELD_LENS_RADIUS_MOBILE = 61;
  const HELD_TWIST = -0.44;
  const MAGNIFICATION = 1.82;
  const PICKUP_FOLLOW = 0.2;
  const HELD_PLANE_DEPTH_FACTOR = 1.78;
  const FIXED_STEP = 1 / 60;
  const GRAVITY = -980;
  const MAX_RELEASE_SPEED = 1320;
  const FLOOR_FRICTION = 0.82;
  const FLOOR_RESTITUTION = 0.095;
  const WALL_FRICTION = 0.58;
  const WALL_RESTITUTION = 0.18;
  const METAL_RESTITUTION = 0.31;
  const WOOD_RESTITUTION = 0.11;
  const GLASS_RESTITUTION = 0.045;
  const IMPACT_ASSIST_FACTOR = 0.24;
  const MIN_HARD_IMPACT_SPEED = 82;
  const MAX_ASSISTED_BOUNCE_SPEED = 230;
  const FLOOR_COLLIDER_THICKNESS = 8;
  const AIRBORNE_OVERLAY_CUTOFF_Y = 15;

  type Mode = 'settling' | 'idle' | 'held' | 'airborne';
  type TransformTarget = { position: THREE.Vector3; quaternion: THREE.Quaternion };

  let mode: Mode = 'settling';
  let magnifier: THREE.Group | null = null;
  let shadow: THREE.Mesh<THREE.PlaneGeometry, THREE.MeshBasicMaterial> | null = null;
  let lightRig: THREE.Group | null = null;
  let removeMagnifier: (() => void) | null = null;
  let removeShadow: (() => void) | null = null;
  let removeLightRig: (() => void) | null = null;

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
  let physicsStartedAt = 0;

  let hitButton: HTMLButtonElement | null = null;
  let activePointerId: number | null = null;
  let pointerX = 0;
  let pointerY = 0;
  let pointerSampleTime = 0;
  let lastTargetPosition: THREE.Vector3 | null = null;
  const filteredReleaseVelocity = new THREE.Vector3();
  const filteredAngularVelocity = new THREE.Vector3();
  let heldPosition = new THREE.Vector3();
  let heldQuaternion = new THREE.Quaternion();

  let overlayRoot: HTMLDivElement | null = null;
  let lensViewport: HTMLDivElement | null = null;
  let snapshotRoom: HTMLElement | null = null;
  let roomRect: DOMRect | null = null;
  let lensRadius = HELD_LENS_RADIUS;

  let animationFrame = 0;
  let previousFrameTime = 0;
  let physicsAccumulator = 0;
  let overlayRemovedAfterRelease = false;
  let destroyed = false;

  const tmpVectorA = new THREE.Vector3();
  const tmpVectorB = new THREE.Vector3();
  const tmpVectorC = new THREE.Vector3();
  const tmpQuaternion = new THREE.Quaternion();
  const tmpEuler = new THREE.Euler();

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
    gradient.addColorStop(0, '#87502f');
    gradient.addColorStop(0.28, '#b77749');
    gradient.addColorStop(0.52, '#c98a5a');
    gradient.addColorStop(0.76, '#a9653d');
    gradient.addColorStop(1, '#794329');
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
      color: 0xf0ece6,
      metalness: 1,
      roughness: 0.04,
      clearcoat: 0.58,
      clearcoatRoughness: 0.03,
    });
    const darkMetal = new THREE.MeshPhysicalMaterial({
      color: 0x635c56,
      metalness: 0.98,
      roughness: 0.08,
      clearcoat: 0.36,
      clearcoatRoughness: 0.045,
    });
    const woodTexture = createWoodTexture();
    const handleMaterial = new THREE.MeshPhysicalMaterial({
      color: 0xce9564,
      map: woodTexture,
      bumpMap: woodTexture,
      bumpScale: 0.14,
      metalness: 0,
      roughness: 0.42,
      clearcoat: 0.18,
      clearcoatRoughness: 0.3,
    });
    if (woodTexture) handleMaterial.userData.disposableTexture = woodTexture;
    const glassMaterial = new THREE.MeshPhysicalMaterial({
      color: 0xffffff,
      transmission: 0.985,
      transparent: true,
      opacity: 0.075,
      roughness: 0.004,
      thickness: 1.1,
      ior: 1.52,
      metalness: 0,
      depthWrite: false,
      side: THREE.DoubleSide,
    });

    const ring = new THREE.Mesh(new THREE.TorusGeometry(LENS_RADIUS, RING_TUBE_RADIUS, 28, 96), metal);
    ring.rotation.x = Math.PI / 2;
    ring.scale.z = 0.92;
    ring.castShadow = true;
    ring.renderOrder = 6;
    root.add(ring);

    const innerRing = new THREE.Mesh(
      new THREE.TorusGeometry(LENS_RADIUS - 4.7, 1.3, 18, 96),
      darkMetal,
    );
    innerRing.rotation.x = Math.PI / 2;
    innerRing.scale.z = 0.9;
    innerRing.position.y = 0.2;
    innerRing.castShadow = true;
    innerRing.renderOrder = 7;
    root.add(innerRing);

    const glass = new THREE.Mesh(new THREE.CircleGeometry(LENS_RADIUS - 5.9, 96), glassMaterial);
    glass.rotation.x = -Math.PI / 2;
    glass.position.y = 0.65;
    glass.renderOrder = 5;
    root.add(glass);

    const ferrule = new THREE.Mesh(new THREE.CylinderGeometry(7.5, 7.5, 23, 30), darkMetal);
    ferrule.rotation.x = Math.PI / 2;
    ferrule.scale.z = 0.5;
    ferrule.position.set(0, FERRULE_Y, FERRULE_CENTER_Z);
    ferrule.castShadow = true;
    ferrule.renderOrder = 6;
    root.add(ferrule);

    const handle = new THREE.Mesh(new THREE.CylinderGeometry(7.9, 7.9, 104, 32), handleMaterial);
    handle.rotation.x = Math.PI / 2;
    handle.scale.z = 0.52;
    handle.position.set(0, HANDLE_Y, HANDLE_CENTER_Z);
    handle.castShadow = true;
    handle.renderOrder = 6;
    root.add(handle);

    const cap = new THREE.Mesh(new THREE.CylinderGeometry(8.9, 8.9, 8.5, 30), darkMetal);
    cap.rotation.x = Math.PI / 2;
    cap.scale.z = 0.52;
    cap.position.set(0, CAP_Y, CAP_CENTER_Z);
    cap.castShadow = true;
    cap.renderOrder = 6;
    root.add(cap);

    return root;
  }

  function createShadow() {
    const texture = createContactShadowTexture();
    if (!texture) return null;
    const material = new THREE.MeshBasicMaterial({
      map: texture,
      transparent: true,
      depthWrite: false,
      opacity: 0.5,
    });
    material.userData.disposableTexture = texture;
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(190, 286), material);
    mesh.rotation.x = -Math.PI / 2;
    mesh.position.y = 0.035;
    mesh.renderOrder = -2;
    return mesh;
  }

  function createLightRig() {
    const rig = new THREE.Group();
    const hemi = new THREE.HemisphereLight(0xfaf7f2, 0x3a2821, 1.16);
    rig.add(hemi);
    const key = new THREE.PointLight(0xffffff, 1.8, 1250, 1.65);
    key.position.set(-155, 235, 145);
    rig.add(key);
    const coolRim = new THREE.PointLight(0xd9f2ff, 0.82, 980, 1.5);
    coolRim.position.set(235, 145, 185);
    rig.add(coolRim);
    const warmRim = new THREE.PointLight(0xffe1c6, 0.48, 760, 1.7);
    warmRim.position.set(-250, 70, 260);
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

  function quaternionToRapier(quaternion: THREE.Quaternion) {
    return { x: quaternion.x, y: quaternion.y, z: quaternion.z, w: quaternion.w };
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
      context.getCameraX() + Math.min(132, width * 0.15),
      floor.minX + 190,
      floor.maxX - 190,
    );
    const startZ = THREE.MathUtils.clamp(
      floor.minZ + Math.max(8, Math.min(18, width * 0.016)),
      floor.minZ + 8,
      floor.maxZ - 210,
    );

    const bodyDesc = RAPIER.RigidBodyDesc.dynamic()
      .setTranslation(startX, floor.y + 2.95, startZ)
      .setLinearDamping(0.16)
      .setAngularDamping(0.54)
      .setCcdEnabled(true)
      .setCanSleep(true);
    rigidBody = physicsWorld.createRigidBody(bodyDesc);

    // Approximate the ring with tangential boxes. This gives Rapier a thin,
    // stable footprint without inflating the lens into a solid disk.
    const ringSegments = 16;
    const segmentHalfLength = (Math.PI * 2 * LENS_RADIUS) / ringSegments / 2 * 0.9;
    for (let index = 0; index < ringSegments; index += 1) {
      const angle = (index / ringSegments) * Math.PI * 2;
      const tangentAngle = -angle - Math.PI / 2;
      const collider = RAPIER.ColliderDesc.cuboid(segmentHalfLength, 2.75, RING_TUBE_RADIUS * 0.86)
        .setTranslation(Math.cos(angle) * LENS_RADIUS, 0, Math.sin(angle) * LENS_RADIUS)
        .setRotation({
          x: 0,
          y: Math.sin(tangentAngle / 2),
          z: 0,
          w: Math.cos(tangentAngle / 2),
        });
      addCollider(collider, 1.0, METAL_RESTITUTION);
    }

    // A thin contact plate inside the lens makes the physical glass capable of
    // landing face-down instead of balancing indefinitely on the metal rim.
    addCollider(RAPIER.ColliderDesc.cuboid(29, 2.72, 29), 0.07, GLASS_RESTITUTION);

    addCollider(
      RAPIER.ColliderDesc.cuboid(7.2, FERRULE_HALF_HEIGHT, FERRULE_HALF_LENGTH).setTranslation(0, FERRULE_Y, FERRULE_CENTER_Z),
      0.72,
      METAL_RESTITUTION,
    );
    addCollider(
      RAPIER.ColliderDesc.cuboid(HANDLE_HALF_WIDTH, HANDLE_HALF_HEIGHT, HANDLE_HALF_LENGTH).setTranslation(
        0,
        HANDLE_Y,
        HANDLE_CENTER_Z,
      ),
      0.24,
      WOOD_RESTITUTION,
    );
    addCollider(
      RAPIER.ColliderDesc.cuboid(9.2, CAP_HALF_HEIGHT, CAP_HALF_LENGTH).setTranslation(0, CAP_Y, CAP_CENTER_Z),
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
    physicsReady = true;
    physicsStartedAt = performance.now();
    mode = 'settling';
    syncVisualFromBody();
    updateHitButton();
    startAnimation();
  }

  function syncVisualFromBody() {
    if (!magnifier || !rigidBody) return;
    const translation = rigidBody.translation();
    const rotation = rigidBody.rotation();
    magnifier.position.set(translation.x, translation.y, translation.z);
    magnifier.quaternion.set(rotation.x, rotation.y, rotation.z, rotation.w);
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
    if (!shadow || !rigidBody || !magnifier) return;
    const translation = rigidBody.translation();
    const rotation = rigidBody.rotation();
    tmpQuaternion.set(rotation.x, rotation.y, rotation.z, rotation.w);

    const shadowCenter = worldPointFromLocal(new THREE.Vector3(0, 0, 75));
    const handleDirection = tmpVectorA.set(0, 0, 1).applyQuaternion(tmpQuaternion);
    const faceNormal = tmpVectorB.set(0, 1, 0).applyQuaternion(tmpQuaternion);
    const yaw = Math.atan2(handleDirection.x, handleDirection.z);
    const floorY = context.getFloorSurface()?.y ?? 0;

    shadow.position.set(
      shadowCenter?.x ?? translation.x,
      floorY + 0.035,
      shadowCenter?.z ?? translation.z + 75,
    );
    shadow.rotation.set(-Math.PI / 2, 0, -yaw);

    const height = Math.max(0, translation.y - floorY - 2.8);
    const proximity = Math.exp(-height / 82);
    const flatness = Math.abs(faceNormal.y);
    const spread = 1 + Math.min(0.44, height / 330);
    shadow.scale.set(spread * (0.48 + 0.52 * flatness), spread, 1);
    shadow.material.opacity = (0.08 + 0.48 * proximity) * (0.58 + 0.42 * flatness);
    shadow.visible = mode !== 'held' || translation.y < 120;
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

  function pointerIsNearHandle(clientX: number, clientY: number) {
    if (!physicsReady || mode === 'held' || !magnifier) return false;
    const segment = handleScreenSegment();
    if (!segment) return false;
    const { gripScreen, capScreen } = segment;
    const vx = capScreen.x - gripScreen.x;
    const vy = capScreen.y - gripScreen.y;
    const lengthSq = vx * vx + vy * vy;
    if (lengthSq < 1) return false;
    const wx = clientX - gripScreen.x;
    const wy = clientY - gripScreen.y;
    const t = Math.max(0, Math.min(1, (wx * vx + wy * vy) / lengthSq));
    const nearestX = gripScreen.x + vx * t;
    const nearestY = gripScreen.y + vy * t;
    const distance = Math.hypot(clientX - nearestX, clientY - nearestY);
    return distance <= 28;
  }

  function updateHitButton() {
    if (!hitButton || !physicsReady || mode === 'held' || !magnifier) {
      if (hitButton) hitButton.style.display = 'none';
      return;
    }

    const segment = handleScreenSegment();
    const sideLeft = worldPointFromLocal(new THREE.Vector3(-13, 0, 157));
    const sideRight = worldPointFromLocal(new THREE.Vector3(13, 0, 157));
    if (!segment || !sideLeft || !sideRight) return;

    const { gripScreen, capScreen } = segment;
    const leftScreen = projectWorldPoint(sideLeft);
    const rightScreen = projectWorldPoint(sideRight);
    if (!leftScreen || !rightScreen) {
      hitButton.style.display = 'none';
      return;
    }

    const centerX = (gripScreen.x + capScreen.x) / 2;
    const centerY = (gripScreen.y + capScreen.y) / 2;
    const length = Math.hypot(capScreen.x - gripScreen.x, capScreen.y - gripScreen.y);
    const width = Math.hypot(rightScreen.x - leftScreen.x, rightScreen.y - leftScreen.y);
    const angle = Math.atan2(capScreen.y - gripScreen.y, capScreen.x - gripScreen.x) * (180 / Math.PI) - 90;

    hitButton.style.display = 'block';
    hitButton.style.setProperty('--magnifier-hit-width', `${Math.max(34, width * 2.15)}px`);
    hitButton.style.setProperty('--magnifier-hit-height', `${Math.max(48, length * 1.18)}px`);
    hitButton.style.setProperty('--magnifier-hit-angle', `${angle}deg`);
    hitButton.style.left = `${centerX - Math.max(34, width * 2.15) / 2}px`;
    hitButton.style.top = `${centerY - Math.max(48, length * 1.18) / 2}px`;
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
    const camera = context.getCamera();
    const host = context.getHostElement();
    const ray = pointerRay(clientX, clientY);
    if (!camera || !host || !ray) return null;

    const rect = host.getBoundingClientRect();
    const desiredRadius = window.innerWidth <= 672 ? HELD_LENS_RADIUS_MOBILE : HELD_LENS_RADIUS;
    const tanHalfFov = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2);
    // Keep the carry plane farther back in the room so releases happen closer
    // to the visible checkerboard near the wall instead of too far toward the viewer.
    const forwardDepth = ((LENS_RADIUS * rect.height) / (2 * desiredRadius * tanHalfFov)) * HELD_PLANE_DEPTH_FACTOR;
    const forward = camera.getWorldDirection(tmpVectorA).normalize();
    const denominator = Math.max(0.16, ray.direction.dot(forward));
    const rayDistance = forwardDepth / denominator;
    const capTarget = ray.at(rayDistance, tmpVectorB);

    const faceNormal = tmpVectorC.copy(camera.position).sub(capTarget).normalize();
    const quaternion = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), faceNormal);
    const twist = new THREE.Quaternion().setFromAxisAngle(faceNormal, HELD_TWIST);
    quaternion.premultiply(twist).normalize();

    const rotatedCap = CAP_LOCAL.clone().applyQuaternion(quaternion);
    const position = capTarget.clone().sub(rotatedCap);
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
    roomRect = null;
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

    roomRect = new DOMRect(0, 0, window.innerWidth, window.innerHeight);
    const snapshot = document.createElement('div');
    snapshot.className = 'room-magnifier-overlay__snapshot';
    snapshot.setAttribute('aria-hidden', 'true');
    snapshot.style.width = `${window.innerWidth}px`;
    snapshot.style.height = `${window.innerHeight}px`;
    snapshot.style.pointerEvents = 'none';

    const appendClone = (source: HTMLElement) => {
      const rect = source.getBoundingClientRect();
      const clone = source.cloneNode(true) as HTMLElement;
      clone.querySelectorAll('.floor-scene__registrants, .room-magnifier-hit, .room-magnifier-overlay').forEach((node) => node.remove());
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
      snapshot.append(clone);
      return clone;
    };

    const roomClone = appendClone(sourceRoom);
    if (sourceHeader) appendClone(sourceHeader);
    snapshotRoom?.remove();
    snapshotRoom = snapshot;
    lensViewport.prepend(snapshot);

    // Capture the room without the magnifier itself to avoid a recursive lens.
    const wasVisible = magnifier?.visible ?? true;
    if (magnifier) magnifier.visible = false;
    context.requestRender();
    requestAnimationFrame(() => {
      copyCanvasPixels(sourceRoom, roomClone);
      if (magnifier) magnifier.visible = wasVisible;
      context.requestRender();
    });
  }

  function updateLensOverlay() {
    if (!lensViewport || !snapshotRoom || !magnifier) return;
    const lensCenter = worldPointFromLocal(new THREE.Vector3(0, 0, 0));
    const lensEdge = worldPointFromLocal(LENS_EDGE_LOCAL);
    if (!lensCenter || !lensEdge) return;
    const center = projectWorldPoint(lensCenter);
    const edge = projectWorldPoint(lensEdge);
    if (!center || !edge) {
      lensViewport.style.opacity = '0';
      return;
    }

    lensRadius = Math.max(20, Math.hypot(edge.x - center.x, edge.y - center.y));
    const size = lensRadius * 2;
    const segment = handleScreenSegment();
    const lensAngle = segment
      ? Math.atan2(segment.capScreen.y - segment.gripScreen.y, segment.capScreen.x - segment.gripScreen.x) + Math.PI / 2
      : 0;
    lensViewport.style.opacity = '1';
    lensViewport.style.width = `${size}px`;
    lensViewport.style.height = `${size}px`;
    lensViewport.style.transform = `translate3d(${center.x - lensRadius}px, ${center.y - lensRadius}px, 0) rotate(${lensAngle}rad)`;

    const tx = lensRadius - center.x * MAGNIFICATION;
    const ty = lensRadius - center.y * MAGNIFICATION;
    snapshotRoom.style.transform = `translate3d(${tx}px, ${ty}px, 0) scale(${MAGNIFICATION}) rotate(${-lensAngle}rad)`;
  }

  function setBodyTransform(position: THREE.Vector3, quaternion: THREE.Quaternion) {
    if (!rigidBody) return;
    rigidBody.setTranslation({ x: position.x, y: position.y, z: position.z }, true);
    rigidBody.setRotation(quaternionToRapier(quaternion), true);
    rigidBody.setLinvel({ x: 0, y: 0, z: 0 }, true);
    rigidBody.setAngvel({ x: 0, y: 0, z: 0 }, true);
    syncVisualFromBody();
  }

  function beginPickup(event: PointerEvent) {
    if (!physicsReady || !rigidBody || !magnifier || mode === 'held' || activePointerId !== null) return;
    event.preventDefault();
    event.stopPropagation();
    activePointerId = event.pointerId;
    pointerX = event.clientX;
    pointerY = event.clientY;
    pointerSampleTime = performance.now();
    lastTargetPosition = null;
    filteredReleaseVelocity.set(0, 0, 0);
    filteredAngularVelocity.set(0, 0, 0);

    const t = rigidBody.translation();
    const r = rigidBody.rotation();
    heldPosition.set(t.x, t.y, t.z);
    heldQuaternion.set(r.x, r.y, r.z, r.w);
    rigidBody.wakeUp();
    rigidBody.setGravityScale(0, true);
    mode = 'held';
    overlayRemovedAfterRelease = false;
    destroyOverlay();
    if (hitButton) hitButton.style.display = 'none';
    document.documentElement.classList.add('is-using-room-magnifier');
    createOverlay();
    captureRoomSnapshot();
    startAnimation();
  }

  function handleGlobalPointerDown(event: PointerEvent) {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    if (!pointerIsNearHandle(event.clientX, event.clientY)) return;
    beginPickup(event);
  }

  function handlePointerMove(event: PointerEvent) {
    if (mode !== 'held' || event.pointerId !== activePointerId) return;
    if (event.cancelable) event.preventDefault();
    pointerX = event.clientX;
    pointerY = event.clientY;

    const now = performance.now();
    const target = computeHeldTarget(pointerX, pointerY);
    if (target && lastTargetPosition) {
      const dt = Math.max(1 / 240, (now - pointerSampleTime) / 1000);
      const sample = target.position.clone().sub(lastTargetPosition).divideScalar(dt);
      if (sample.length() > MAX_RELEASE_SPEED) sample.setLength(MAX_RELEASE_SPEED);
      filteredReleaseVelocity.lerp(sample, 0.4);

      const pointerDX = event.movementX || 0;
      const pointerDY = event.movementY || 0;
      filteredAngularVelocity.lerp(
        new THREE.Vector3(pointerDY * 0.035, -pointerDX * 0.035, pointerDX * 0.02),
        0.32,
      );
    }
    if (target) lastTargetPosition = target.position.clone();
    pointerSampleTime = now;
  }

  function releaseHeld(event: PointerEvent) {
    if (mode !== 'held' || event.pointerId !== activePointerId || !rigidBody) return;
    activePointerId = null;
    mode = 'airborne';
    physicsStartedAt = performance.now();
    rigidBody.setGravityScale(1, true);

    const linear = filteredReleaseVelocity.clone();
    if (linear.length() > MAX_RELEASE_SPEED) linear.setLength(MAX_RELEASE_SPEED);
    rigidBody.setLinvel({ x: linear.x, y: linear.y, z: linear.z }, true);

    const angular = filteredAngularVelocity.clone();
    if (angular.lengthSq() < 0.025) {
      // Even a careful real-world release is never perfectly torque-free. This
      // tiny bias prevents an unnaturally perfect edge-on fall while remaining
      // far below the spin generated by an actual throw gesture.
      angular.set(0.2 + linear.z * 0.00018, 0.07, -0.16 - linear.x * 0.00018);
    }
    rigidBody.setAngvel(
      {
        x: THREE.MathUtils.clamp(angular.x, -9, 9),
        y: THREE.MathUtils.clamp(angular.y, -9, 9),
        z: THREE.MathUtils.clamp(angular.z, -9, 9),
      },
      true,
    );
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
    heldQuaternion.slerp(target.quaternion, PICKUP_FOLLOW).normalize();
    setBodyTransform(heldPosition, heldQuaternion);
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
      rigidBody.setAngvel(
        {
          x: angular.x + THREE.MathUtils.clamp(velocity.z * 0.0007, -0.42, 0.42),
          y: angular.y,
          z: angular.z - THREE.MathUtils.clamp(velocity.x * 0.0007, -0.42, 0.42),
        },
        true,
      );
      rigidBody.wakeUp();
    }
    lastBounceAssistAt = now;
  }

  function stepPhysics(deltaSeconds: number) {
    if (!physicsWorld || !rigidBody) return;
    syncPhysicsFloor();
    physicsAccumulator += Math.min(deltaSeconds, 0.05);
    while (physicsAccumulator >= FIXED_STEP) {
      preStepVerticalVelocity = rigidBody.linvel().y;
      physicsWorld.step(physicsEventQueue);
      assistHardFloorImpact();
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
          x: THREE.MathUtils.clamp(translation.x, floor.minX + 60, floor.maxX - 60),
          y: floor.y + 12,
          z: THREE.MathUtils.clamp(translation.z, floor.minZ + 50, floor.maxZ - 80),
        },
        true,
      );
      rigidBody.setLinvel({ x: velocity.x * 0.55, y: Math.abs(velocity.y) * 0.08, z: velocity.z * 0.55 }, true);
      rigidBody.setAngvel({ x: 0.5, y: 0.15, z: -0.35 }, true);
      syncVisualFromBody();
      return;
    }
    if (mode === 'airborne') {
      if (!overlayRemovedAfterRelease) updateLensOverlay();
      if (translation.y <= AIRBORNE_OVERLAY_CUTOFF_Y) {
        overlayRemovedAfterRelease = true;
        destroyOverlay();
        // Keep the 3D canvas in the foreground until the rigid body has actually
        // settled. Otherwise the prop visually vanishes a few pixels before contact.
      }
    }

    updateHitButton();

    const linearVelocity = rigidBody.linvel();
    const angularVelocity = rigidBody.angvel();
    const linearSpeedSq =
      linearVelocity.x * linearVelocity.x +
      linearVelocity.y * linearVelocity.y +
      linearVelocity.z * linearVelocity.z;
    const angularSpeedSq =
      angularVelocity.x * angularVelocity.x +
      angularVelocity.y * angularVelocity.y +
      angularVelocity.z * angularVelocity.z;
    const nearlyStill = linearSpeedSq < 7.5 && angularSpeedSq < 0.035;
    const hasHadTimeToLand = performance.now() - physicsStartedAt > 260;

    if (rigidBody.isSleeping() || ((mode === 'settling' || mode === 'airborne') && nearlyStill && hasHadTimeToLand)) {
      rigidBody.sleep();
      mode = 'idle';
      destroyOverlay();
      document.documentElement.classList.remove('is-using-room-magnifier');
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
    if (mode !== 'idle') animationFrame = requestAnimationFrame(animate);
  }

  function startAnimation() {
    if (animationFrame) return;
    previousFrameTime = 0;
    animationFrame = requestAnimationFrame(animate);
  }

  function handleResize() {
    syncPhysicsFloor();
    if (mode !== 'held') updateHitButton();
    if (mode === 'held' || mode === 'airborne') updateLensOverlay();
  }

  onMount(() => {
    magnifier = createMagnifierModel();
    shadow = createShadow();
    lightRig = createLightRig();
    removeMagnifier = context.addObject(magnifier);
    if (shadow) removeShadow = context.addObject(shadow);
    removeLightRig = context.addObject(lightRig);
    context.requestRender();

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'room-magnifier-hit';
    button.setAttribute('aria-label', 'Pick up the magnifying glass by its handle');
    button.addEventListener('pointerdown', beginPickup);
    document.body.append(button);
    hitButton = button;

    window.addEventListener('pointerdown', handleGlobalPointerDown, { capture: true, passive: false });
    window.addEventListener('pointermove', handlePointerMove, { passive: false });
    window.addEventListener('pointerup', releaseHeld);
    window.addEventListener('pointercancel', handlePointerCancel);
    window.addEventListener('resize', handleResize, { passive: true });

    void createPhysics();

    return () => {
      destroyed = true;
      if (animationFrame) cancelAnimationFrame(animationFrame);
      window.removeEventListener('pointerdown', handleGlobalPointerDown, true);
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', releaseHeld);
      window.removeEventListener('pointercancel', handlePointerCancel);
      window.removeEventListener('resize', handleResize);
      document.documentElement.classList.remove('is-using-room-magnifier');
      hitButton?.removeEventListener('pointerdown', beginPickup);
      hitButton?.remove();
      hitButton = null;
      destroyOverlay();
      removeMagnifier?.();
      removeShadow?.();
      removeLightRig?.();
      disposeObject(magnifier);
      disposeObject(shadow);
      magnifier = null;
      shadow = null;
      lightRig = null;
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
