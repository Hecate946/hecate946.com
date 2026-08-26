import {
  AlwaysStencilFunc,
  BoxGeometry,
  BufferGeometry,
  ExtrudeGeometry,
  Group,
  KeepStencilOp,
  Material,
  Mesh,
  MeshBasicMaterial,
  MeshPhysicalMaterial,
  MeshStandardMaterial,
  Object3D,
  Path,
  PerspectiveCamera,
  ReplaceStencilOp,
  Shape,
  ShapeGeometry,
  Vector3,
} from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { withBase } from '@/lib/paths';
import {
  DOOR_MODEL_PATH,
  DOOR_OPENING_HALF,
  DOOR_OUTER_HALF,
  DOOR_SPRING_Z,
  DOOR_WALL_DEPTH,
} from './door-metrics';

/**
 * The entrance: a black arched double door standing across the corridor.
 *
 * The assembly itself is no longer built here. It is modelled by
 * `blender/hecate946_door.py`, exported as a GLB, and loaded at runtime;
 * this module owns only the things the model cannot know about -- the wall
 * it is set into, where that wall's opening falls on screen, the swing, and
 * the stencil portal that lets the corridor show through the arch.
 *
 * The model is authored at unit height with its origin on the floor line
 * and its front face on z = 0, so scaling it to the corridor is a single
 * uniform scale and the wall can be built to meet it exactly.
 *
 * Depth ordering is the whole point of doing this in WebGL rather than in
 * CSS: the wall genuinely occludes the corridor, so walking through the
 * doorway is a real dolly rather than an expanding clip-path.
 */

/** How far past the door plane the camera ends up. */
const ENTRY_CLEARANCE = 240;
/** The door sits this fraction of the perspective distance ahead of z = 0. */
const DOOR_DISTANCE_RATIO = 0.42;

/**
 * Satin, not mirror. A near-zero clearcoatRoughness turns any directional
 * light into a single blinding blob on a flat panel; spreading the
 * roughness lets the environment wash across the leaf instead, which is
 * what reads as lacquer rather than a spotlight.
 */
const BLACK_LACQUER = {
  color: 0x020303,
  roughness: 0.7,
  metalness: 0,
  clearcoat: 0.1,
  clearcoatRoughness: 0.62,
};

/** The arch-topped profile used for both the wall opening and the portal. */
function traceOpening(
  path: Shape | Path,
  halfWidth: number,
  springHeight: number,
  baseY: number,
  centerX = 0,
) {
  path.moveTo(centerX - halfWidth, baseY);
  path.lineTo(centerX - halfWidth, springHeight);
  path.absarc(centerX, springHeight, halfWidth, Math.PI, 0, true);
  path.lineTo(centerX + halfWidth, baseY);
  path.closePath();
}

export interface DoorRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

export interface HallwayDoor {
  readonly group: Group;
  /** How far the camera must travel along +z to end up past the door. */
  readonly entryDistance: number;
  /** World-space floor shared by the doorway and corridor. */
  readonly floorY: number;
  /** Project the fixed DOM doorway anchor onto the doorway's world plane. */
  layout(
    halfWidth: number,
    halfHeight: number,
    perspective: number,
    camera: PerspectiveCamera,
    viewportRect: DOMRect,
    anchorRect: DOMRect,
  ): void;
  /** 0 = shut, 1 = fully swung open toward the camera. */
  setOpen(amount: number): void;
  /** Slide the whole assembly with the corridor as the camera advances. */
  setCameraZ(cameraZ: number): void;
  /** Enable the invisible arched stencil that reveals the corridor. */
  setPortalMask(enabled: boolean): void;
  /** Whether the doorway plane is still in front of the camera. */
  isBeforeCamera(cameraZ: number): boolean;
  /** The doorway's on-screen box, for the entrance hit target. */
  project(
    camera: PerspectiveCamera,
    viewWidth: number,
    viewHeight: number,
  ): DoorRect;
  dispose(): void;
}

export function createHallwayDoor(
  wallMaterials: [Material, Material],
  /** Called once the GLB is in the scene and a redraw is needed. */
  onLoaded: () => void = () => {},
): HallwayDoor {
  const geometries: BufferGeometry[] = [];
  const track = <T extends BufferGeometry>(geometry: T) => {
    geometries.push(geometry);
    return geometry;
  };

  const lacquer = new MeshPhysicalMaterial({
    ...BLACK_LACQUER,
    envMapIntensity: 0.07,
  });
  const gold = new MeshStandardMaterial({
    color: 0x9a6a27,
    metalness: 1,
    roughness: 0.4,
    envMapIntensity: 0.5,
    emissive: 0x120900,
    emissiveIntensity: 0.12,
  });
  // The reference glazes the fanlight almost black. Leaving it clear let
  // the corridor's far end shine through the arch as a bright halo.
  const glass = new MeshPhysicalMaterial({
    color: 0x020708,
    transparent: true,
    opacity: 0.9,
    roughness: 0.58,
    metalness: 0,
    depthWrite: false,
    envMapIntensity: 0.015,
  });
  const portalMaskMaterial = new MeshBasicMaterial({
    colorWrite: false,
    depthTest: false,
    depthWrite: false,
    stencilWrite: true,
    stencilWriteMask: 0xff,
    stencilFunc: AlwaysStencilFunc,
    stencilRef: 1,
    stencilFuncMask: 0xff,
    stencilFail: KeepStencilOp,
    stencilZFail: KeepStencilOp,
    stencilZPass: ReplaceStencilOp,
  });
  const materials: Material[] = [lacquer, gold, glass, portalMaskMaterial];

  const group = new Group();

  // --- the wall the door is set into, rebuilt whenever the corridor resizes
  const wall = new Mesh(new BufferGeometry(), wallMaterials);
  group.add(wall);

  // --- everything below is authored at unit height and scaled as one piece
  const assembly = new Group();
  group.add(assembly);

  // This mesh never paints. It writes the doorway silhouette into the
  // stencil before the corridor is rendered, so the shared DOM room stays
  // the visible entrance wall and WebGL appears only through the arch.
  const portalShape = new Shape();
  traceOpening(portalShape, DOOR_OPENING_HALF, DOOR_SPRING_Z, 0);
  const portalMask = new Mesh(
    track(new ShapeGeometry(portalShape, 48)),
    portalMaskMaterial,
  );
  portalMask.position.z = -DOOR_WALL_DEPTH * 0.5;
  portalMask.renderOrder = -1_000;
  assembly.add(portalMask);

  // --- the modelled door itself
  const leftHinge = new Object3D();
  const rightHinge = new Object3D();
  assembly.add(leftHinge, rightHinge);

  // The authored leaves stop just short of the centre line. Without a real
  // astragal that hairline exposes the bright checkerboard behind the door,
  // which aliases into the white dashed seam visible in screenshots.
  const astragal = new Mesh(
    track(new BoxGeometry(0.006, 0.596, 0.014)),
    lacquer,
  );
  astragal.position.set(0.247, 0.3894, -0.022);
  leftHinge.add(astragal);

  let loadedRoot: Object3D | null = null;

  new GLTFLoader().load(
    withBase(DOOR_MODEL_PATH),
    (gltf) => {
      const root = gltf.scene;
      loadedRoot = root;

      // The exporter writes Blender's material names through, which is the
      // contract the build script promises. Overriding by name keeps the
      // real-time look in code, where it can be tuned against the corridor
      // rather than against Cycles.
      root.traverse((object) => {
        if (!(object instanceof Mesh)) return;
        object.frustumCulled = false;
        const current = Array.isArray(object.material)
          ? object.material[0]
          : object.material;
        const name = current?.name ?? '';
        if (name === 'Gold') object.material = gold;
        else if (name === 'Glass') object.material = glass;
        else object.material = lacquer;
        track(object.geometry);
      });

      // Reparent the leaves under our own hinge objects. The GLB already
      // places its hinge empties on the stiles, so the swing axis comes
      // straight from the model and no offset has to be guessed here.
      for (const [name, hinge] of [
        ['HingeL', leftHinge],
        ['HingeR', rightHinge],
      ] as const) {
        const source = root.getObjectByName(name);
        if (!source) continue;
        hinge.position.copy(source.position);
        for (const child of [...source.children]) hinge.add(child);
        source.removeFromParent();
      }

      // Whatever is left is the static surround and its glazing.
      assembly.add(root);
      onLoaded();
    },
    undefined,
    (error) => {
      // No model: the arch still cuts a real hole in the wall and every
      // interaction keeps working, so this degrades to an open doorway
      // rather than to a broken page.
      console.warn('Entrance door model unavailable', error);
    },
  );

  // --- layout state
  const MAX_SWING = (Math.PI / 180) * 96;
  /** The trailing leaf lags slightly; perfect sync reads as machinery. */
  const LEAF_LAG = 0.07;

  let doorZ = 0;
  let entryDistance = 0;
  let scale = 0;
  let floorY = 0;
  let centerX = 0;
  let laidOut = '';

  function layout(
    halfWidth: number,
    halfHeight: number,
    perspective: number,
    camera: PerspectiveCamera,
    viewportRect: DOMRect,
    anchorRect: DOMRect,
  ) {
    doorZ = -perspective * DOOR_DISTANCE_RATIO;
    entryDistance = perspective - doorZ + ENTRY_CLEARANCE;

    // `Vector3.unproject()` reads camera.matrixWorld directly. On the first
    // page load the renderer has not drawn a frame yet, so it has not had a
    // chance to update that matrix for the camera's new z position. Without
    // this explicit update the DOM anchor collapses to roughly one world
    // unit and the doorway appears completely blank.
    camera.updateMatrixWorld(true);

    const pointOnDoorPlane = (clientX: number, clientY: number) => {
      const point = new Vector3(
        ((clientX - viewportRect.left) / viewportRect.width) * 2 - 1,
        -(((clientY - viewportRect.top) / viewportRect.height) * 2 - 1),
        0,
      ).unproject(camera);
      const direction = point.sub(camera.position);
      const distance = (doorZ - camera.position.z) / direction.z;
      return camera.position.clone().addScaledVector(direction, distance);
    };

    const anchorX = anchorRect.left + anchorRect.width / 2;
    const bottom = pointOnDoorPlane(anchorX, anchorRect.bottom);
    const top = pointOnDoorPlane(anchorX, anchorRect.top);
    const projectedScale = top.y - bottom.y;
    const fallbackScale =
      anchorRect.height * ((perspective - doorZ) / perspective);
    scale =
      Number.isFinite(projectedScale) && projectedScale > 0
        ? projectedScale
        : fallbackScale;
    floorY = Number.isFinite(bottom.y) ? bottom.y : -halfHeight;
    centerX = Number.isFinite(bottom.x) ? bottom.x : 0;

    assembly.scale.setScalar(scale);
    assembly.position.x = centerX;
    assembly.position.y = floorY;

    const signature = `${halfWidth}|${halfHeight}|${scale}|${floorY}|${centerX}`;
    if (signature === laidOut) return;
    laidOut = signature;

    // The wall spans the corridor with a little overlap so no seam can show
    // at the corners, and carries the pilaster line as its opening. The
    // impost blocks and base plinth are wider than that on purpose: they
    // lap onto the wall face, which is how applied trim actually sits.
    const panelHalfWidth = halfWidth + 24;
    const shape = new Shape();
    shape.moveTo(-panelHalfWidth, -halfHeight);
    shape.lineTo(panelHalfWidth, -halfHeight);
    shape.lineTo(panelHalfWidth, halfHeight);
    shape.lineTo(-panelHalfWidth, halfHeight);
    shape.closePath();

    const hole = new Path();
    traceOpening(
      hole,
      DOOR_OUTER_HALF * scale,
      floorY + DOOR_SPRING_Z * scale,
      floorY,
      centerX,
    );
    shape.holes.push(hole);

    wall.geometry.dispose();
    wall.geometry = new ExtrudeGeometry(shape, {
      depth: DOOR_WALL_DEPTH * scale,
      bevelEnabled: false,
      curveSegments: 48,
    });
    // ExtrudeGeometry always grows along +z. Pulling the wall back by its
    // own depth puts its face on the assembly's z = 0 -- the same plane the
    // casing's face sits on -- so the door is flush with the brick instead
    // of floating in front of it, and only the mouldings stand proud.
    wall.position.z = -DOOR_WALL_DEPTH * scale;
  }

  function setOpen(amount: number) {
    const lead = Math.min(1, Math.max(0, amount));
    const trail = Math.min(
      1,
      Math.max(0, (amount - LEAF_LAG) / (1 - LEAF_LAG)),
    );
    leftHinge.rotation.y = -lead * MAX_SWING;
    rightHinge.rotation.y = trail * MAX_SWING;
  }

  return {
    group,
    get entryDistance() {
      return entryDistance;
    },
    get floorY() {
      return floorY;
    },
    layout,
    setOpen,
    setCameraZ(cameraZ: number) {
      group.position.z = doorZ + cameraZ + entryDistance;
    },
    setPortalMask(enabled: boolean) {
      portalMask.visible = enabled;
    },
    isBeforeCamera(cameraZ: number) {
      return group.position.z < cameraZ - 1;
    },
    project(camera, viewWidth, viewHeight) {
      const z = group.position.z;
      const halfWidth = DOOR_OPENING_HALF * scale;
      const top = floorY + scale;
      const corners = [
        new Vector3(centerX - halfWidth, floorY, z),
        new Vector3(centerX + halfWidth, top, z),
      ].map((corner) => corner.project(camera));

      const xs = corners.map((c) => (c.x * 0.5 + 0.5) * viewWidth);
      const ys = corners.map((c) => (-c.y * 0.5 + 0.5) * viewHeight);
      return {
        left: Math.min(...xs),
        top: Math.min(...ys),
        width: Math.abs(xs[1] - xs[0]),
        height: Math.abs(ys[1] - ys[0]),
      };
    },
    dispose() {
      wall.geometry.dispose();
      loadedRoot?.removeFromParent();
      for (const geometry of geometries) geometry.dispose();
      for (const material of materials) material.dispose();
    },
  };
}
