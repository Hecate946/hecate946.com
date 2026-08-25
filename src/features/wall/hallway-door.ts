import {
  BoxGeometry,
  BufferGeometry,
  CircleGeometry,
  CubicBezierCurve,
  DoubleSide,
  AlwaysStencilFunc,
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
  PlaneGeometry,
  ReplaceStencilOp,
  Shape,
  ShapeGeometry,
  Vector2,
  Vector3,
} from 'three';
import { createFrameGeometry } from './hallway-geometry';

/**
 * The entrance: a black arched double door standing across the corridor,
 * with a fanlight above it and gold violin f-holes for handles.
 *
 * The whole assembly is authored once at unit height with its origin on the
 * floor line, then scaled to whatever the corridor's CSS proportions work out
 * to. Only the surrounding wall is rebuilt on resize, because its opening has
 * to be cut to match the scaled assembly and a semicircle cannot survive a
 * non-uniform scale.
 *
 * Depth ordering is the whole point of building this in WebGL rather than in
 * CSS: the wall genuinely occludes the corridor, so walking through the
 * doorway is a real dolly rather than an expanding clip-path.
 */

/** Casing thickness as a fraction of the assembly's total height. */
const CASING = 0.028;
/** Doors are 1.515 times as tall as the opening is wide. */
const DOOR_ASPECT = 0.66;
/** doorHeight + archRadius + casing == 1, and archRadius == doorWidth / 2. */
const DOOR_HEIGHT = (1 - CASING) / (1 + DOOR_ASPECT / 2);
const OPENING_HALF = (DOOR_HEIGHT * DOOR_ASPECT) / 2;
const OUTER_HALF = OPENING_HALF + CASING;

/** A real doorway has depth: the wall is thick and the leaves sit inside it. */
const WALL_DEPTH = 0.058;
const LEAF_DEPTH = 0.03;
/** How far the leaves' faces sit behind the wall's outer face. */
const LEAF_SETBACK = 0.01;
const LEAF_GAP = 0.0015;
const LEAF_WIDTH = OPENING_HALF - LEAF_GAP;
/** The strip on the leading leaf that laps the meeting stile shut. */
const ASTRAGAL_WIDTH = 0.016;
const ASTRAGAL_DEPTH = 0.005;
const MUNTIN = 0.009;
const MUNTIN_DEPTH = 0.014;
const TRANSOM = 0.024;

/** Narrow shadow gaps make the casing read as set into masonry, not mounted on it. */
const RECESS_GAP = 0.013;
const RECESS_SHADOW_OPACITY = 0.58;
const FLOOR_SHADOW_DEPTH = 0.13;

const HANDLE_HEIGHT = 0.2;
const HANDLE_INSET = 0.062;
const HANDLE_CENTRE = 0.44;

/** How far past the door plane the camera ends up. */
const ENTRY_CLEARANCE = 240;
/** The door sits this fraction of the perspective distance ahead of z = 0. */
const DOOR_DISTANCE_RATIO = 0.42;

/**
 * Satin, not mirror. A near-zero clearcoatRoughness turns any directional
 * light into a single blinding blob on a flat panel; spreading the roughness
 * lets the environment wash across the leaf instead, which is what reads as
 * lacquer rather than a spotlight.
 */
const BLACK_LACQUER = {
  color: 0x0c0c0c,
  roughness: 0.48,
  metalness: 0,
  clearcoat: 0.6,
  clearcoatRoughness: 0.34,
};

// ---------------------------------------------------------------------------
// Violin f-hole
// ---------------------------------------------------------------------------

/**
 * An f-hole is a thick S-stroke with a round eye at each end and a pointed
 * nick at the waist, so that is exactly how it is built: one spine curve,
 * offset either side by a varying half-width, capped with semicircles. The
 * spine leaves both eyes vertically, which is what keeps the shape upright
 * rather than splayed.
 */
const SPINE = new CubicBezierCurve(
  new Vector2(12, 44),
  new Vector2(9, 12),
  new Vector2(-9, -12),
  new Vector2(-12, -44),
);

/** Half-width of the stroke alone: thin at the top, fullest below the waist. */
const SPINE_WIDTHS: readonly (readonly [number, number])[] = [
  [0, 3.9],
  [0.22, 4.3],
  [0.55, 5.6],
  [0.8, 4.8],
  [1, 4.2],
];

/** The eyes are drilled circles, the lower one larger, as on the instrument. */
const EYE_UPPER = 8;
const EYE_LOWER = 9.6;
/** |dP/dt| at either end, which turns t into arclength near the eyes. */
const SPINE_END_SPEED = 96.4;

const NICK_SIZE = 2.8;
const NICK_SPAN = 0.034;

function smoothstep(edge0: number, edge1: number, value: number) {
  const t = Math.min(1, Math.max(0, (value - edge0) / (edge1 - edge0)));
  return t * t * (3 - 2 * t);
}

function strokeWidth(t: number) {
  let width = SPINE_WIDTHS[SPINE_WIDTHS.length - 1][1];
  for (let i = 0; i < SPINE_WIDTHS.length - 1; i += 1) {
    const [t0, w0] = SPINE_WIDTHS[i];
    const [t1, w1] = SPINE_WIDTHS[i + 1];
    if (t <= t1) {
      width = w0 + (w1 - w0) * smoothstep(t0, t1, t);
      break;
    }
  }
  // The two nicks at the waist, as sharp triangular points.
  return width + NICK_SIZE * Math.max(0, 1 - Math.abs(t - 0.5) / NICK_SPAN);
}

/**
 * Near an end the spine is almost straight, so a half-width of
 * sqrt(r^2 - s^2) traces an exact circle of radius r about the eye's centre.
 * Taking the larger of that and the stroke gives a true drilled eye meeting
 * the stroke at a crisp shoulder, still as one continuous outline.
 */
function eyeWidth(t: number) {
  const upper = EYE_UPPER ** 2 - (SPINE_END_SPEED * t) ** 2;
  const lower = EYE_LOWER ** 2 - (SPINE_END_SPEED * (1 - t)) ** 2;
  return Math.max(
    upper > 0 ? Math.sqrt(upper) : 0,
    lower > 0 ? Math.sqrt(lower) : 0,
  );
}

function spineWidth(t: number) {
  return Math.max(strokeWidth(t), eyeWidth(t));
}

function spineFrame(t: number) {
  const point = SPINE.getPoint(t);
  const tangent = SPINE.getTangent(t);
  return {
    point,
    normal: new Vector2(tangent.y, -tangent.x),
    width: spineWidth(t),
  };
}

/** Half-turn cap around a spine end, from `+normal` round to `-normal`. */
function capPoints(t: number, segments: number) {
  const { point, normal, width } = spineFrame(t);
  const from = Math.atan2(normal.y, normal.x) + (t === 0 ? Math.PI : 0);
  const points: Vector2[] = [];
  for (let i = 1; i < segments; i += 1) {
    const angle = from + (Math.PI * i) / segments;
    points.push(
      new Vector2(
        point.x + Math.cos(angle) * width,
        point.y + Math.sin(angle) * width,
      ),
    );
  }
  return points;
}

function createFHoleShape() {
  const SEGMENTS = 130;
  const right: Vector2[] = [];
  const left: Vector2[] = [];

  for (let i = 0; i <= SEGMENTS; i += 1) {
    const { point, normal, width } = spineFrame(i / SEGMENTS);
    right.push(
      new Vector2(point.x + normal.x * width, point.y + normal.y * width),
    );
    left.push(
      new Vector2(point.x - normal.x * width, point.y - normal.y * width),
    );
  }

  const outline = [
    ...right,
    ...capPoints(1, 16),
    ...left.reverse(),
    ...capPoints(0, 16),
  ];

  // Normalise to unit height, centred, so the mesh can simply be scaled.
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  for (const point of outline) {
    minX = Math.min(minX, point.x);
    maxX = Math.max(maxX, point.x);
    minY = Math.min(minY, point.y);
    maxY = Math.max(maxY, point.y);
  }
  const scale = 1 / (maxY - minY);
  const offsetX = (minX + maxX) / 2;
  const offsetY = (minY + maxY) / 2;

  const shape = new Shape();
  outline.forEach((point, index) => {
    const x = (point.x - offsetX) * scale;
    const y = (point.y - offsetY) * scale;
    if (index === 0) shape.moveTo(x, y);
    else shape.lineTo(x, y);
  });
  shape.closePath();
  return shape;
}

// ---------------------------------------------------------------------------
// Millwork helpers
// ---------------------------------------------------------------------------

/** The arch-topped profile used for both the wall opening and the casing. */
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

// ---------------------------------------------------------------------------
// Door
// ---------------------------------------------------------------------------

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
): HallwayDoor {
  const geometries: BufferGeometry[] = [];
  const track = <T extends BufferGeometry>(geometry: T) => {
    geometries.push(geometry);
    return geometry;
  };

  const lacquer = new MeshPhysicalMaterial(BLACK_LACQUER);
  const gold = new MeshStandardMaterial({
    color: 0xc9a54e,
    metalness: 1,
    roughness: 0.32,
  });
  const glass = new MeshPhysicalMaterial({
    color: 0x9ecfc9,
    transparent: true,
    opacity: 0.1,
    roughness: 0.05,
    metalness: 0,
    depthWrite: false,
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
  const recessShadowMaterial = new MeshBasicMaterial({
    color: 0x000000,
    transparent: true,
    opacity: RECESS_SHADOW_OPACITY,
    depthWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: -2,
    polygonOffsetUnits: -2,
  });
  const floorShadowMaterial = new MeshBasicMaterial({
    color: 0x000000,
    transparent: true,
    opacity: 0.34,
    depthWrite: false,
    side: DoubleSide,
  });
  const materials: Material[] = [
    lacquer,
    gold,
    glass,
    portalMaskMaterial,
    recessShadowMaterial,
    floorShadowMaterial,
  ];

  const group = new Group();

  // --- the wall the door is set into, rebuilt whenever the corridor resizes
  const wall = new Mesh(new BufferGeometry(), wallMaterials);
  group.add(wall);

  // --- everything below is authored at unit height and scaled as one piece
  const assembly = new Group();
  group.add(assembly);

  const springHeight = DOOR_HEIGHT;

  // This mesh never paints. It writes the doorway silhouette into the stencil
  // before the corridor is rendered, allowing the shared DOM room to remain
  // the exact visible entrance wall while WebGL appears only through the arch.
  const portalShape = new Shape();
  traceOpening(portalShape, OPENING_HALF, springHeight, 0);
  const portalMask = new Mesh(
    track(new ShapeGeometry(portalShape, 48)),
    portalMaskMaterial,
  );
  portalMask.position.z = WALL_DEPTH * 0.25;
  portalMask.renderOrder = -1_000;
  assembly.add(portalMask);

  // A slim dark return around the casing supplies the contact shadow that the
  // transparent WebGL canvas cannot cast onto the DOM-rendered brick wall.
  // Because it follows the same arch exactly, it reads as the depth of a real
  // opening rather than as a generic drop shadow around a floating object.
  const recessShape = new Shape();
  traceOpening(recessShape, OUTER_HALF + RECESS_GAP, springHeight, 0);
  const recessHole = new Path();
  traceOpening(recessHole, OUTER_HALF, springHeight, 0);
  recessShape.holes.push(recessHole);
  const recessShadow = new Mesh(
    track(new ShapeGeometry(recessShape, 48)),
    recessShadowMaterial,
  );
  recessShadow.position.z = WALL_DEPTH * 1.01;
  assembly.add(recessShadow);

  // The small floor shadow and threshold visually carry the wall opening down
  // into the checkerboard, anchoring both jambs at the shared room's floor.
  const floorShadow = new Mesh(
    track(
      new PlaneGeometry(
        (OUTER_HALF + RECESS_GAP * 2.5) * 2,
        FLOOR_SHADOW_DEPTH,
      ),
    ),
    floorShadowMaterial,
  );
  floorShadow.rotation.x = -Math.PI / 2;
  floorShadow.position.set(0, 0.001, FLOOR_SHADOW_DEPTH * 0.12);
  assembly.add(floorShadow);

  const threshold = new Mesh(
    track(
      new BoxGeometry(
        (OPENING_HALF + RECESS_GAP * 0.75) * 2,
        0.012,
        WALL_DEPTH * 1.1,
      ),
    ),
    lacquer,
  );
  threshold.position.set(0, 0.006, WALL_DEPTH * 0.5);
  assembly.add(threshold);

  const casingShape = new Shape();
  traceOpening(casingShape, OUTER_HALF, springHeight, 0);
  const casingHole = new Path();
  traceOpening(casingHole, OPENING_HALF, springHeight, 0);
  casingShape.holes.push(casingHole);
  const casing = new Mesh(
    track(
      new ExtrudeGeometry(casingShape, {
        depth: WALL_DEPTH * 1.25,
        bevelEnabled: false,
        curveSegments: 32,
      }),
    ),
    lacquer,
  );
  assembly.add(casing);

  const transom = new Mesh(
    track(new BoxGeometry(OPENING_HALF * 2, TRANSOM, WALL_DEPTH * 1.2)),
    lacquer,
  );
  transom.position.set(0, springHeight, (WALL_DEPTH * 1.2) / 2);
  assembly.add(transom);

  // --- fanlight: radial muntins plus one concentric arc, over faint glass
  const fanlight = new Group();
  fanlight.position.set(0, springHeight, 0);
  assembly.add(fanlight);

  const paneRadius = OPENING_HALF - MUNTIN / 2;
  const pane = new Mesh(
    track(new CircleGeometry(paneRadius, 48, 0, Math.PI)),
    glass,
  );
  pane.position.z = MUNTIN_DEPTH * 0.4;
  fanlight.add(pane);

  const spokeGeometry = track(
    new BoxGeometry(MUNTIN, OPENING_HALF, MUNTIN_DEPTH),
  );
  const SPOKES = 6;
  for (let i = 1; i <= SPOKES; i += 1) {
    const angle = (Math.PI * i) / (SPOKES + 1);
    const spoke = new Mesh(spokeGeometry, lacquer);
    spoke.position.set(
      (Math.cos(angle) * OPENING_HALF) / 2,
      (Math.sin(angle) * OPENING_HALF) / 2,
      MUNTIN_DEPTH / 2,
    );
    spoke.rotation.z = angle - Math.PI / 2;
    fanlight.add(spoke);
  }

  const arcRadius = OPENING_HALF * 0.5;
  const arcShape = new Shape();
  arcShape.absarc(0, 0, arcRadius + MUNTIN / 2, 0, Math.PI, false);
  arcShape.absarc(0, 0, arcRadius - MUNTIN / 2, Math.PI, 0, true);
  arcShape.closePath();
  const arc = new Mesh(
    track(
      new ExtrudeGeometry(arcShape, {
        depth: MUNTIN_DEPTH,
        bevelEnabled: false,
        curveSegments: 32,
      }),
    ),
    lacquer,
  );
  fanlight.add(arc);

  // --- one leaf, built hinge-at-origin, then mirrored for the other
  const fHoleGeometry = track(
    new ExtrudeGeometry(createFHoleShape(), {
      depth: 0.06,
      bevelEnabled: true,
      bevelSize: 0.006,
      bevelThickness: 0.009,
      bevelSegments: 2,
      curveSegments: 1,
    }),
  );

  function createLeaf(withAstragal: boolean) {
    const leaf = new Group();

    const slab = new Mesh(
      track(new BoxGeometry(LEAF_WIDTH, DOOR_HEIGHT, LEAF_DEPTH)),
      lacquer,
    );
    slab.position.set(LEAF_WIDTH / 2, DOOR_HEIGHT / 2, LEAF_DEPTH / 2);
    leaf.add(slab);

    // Two applied panels, the classic tall-door split.
    const stile = 0.032;
    const panelWidth = LEAF_WIDTH - stile * 2;
    // Panel extents as fractions of the leaf height: a long upper field
    // over a shorter lower one.
    const panels = [
      [0.415, 0.7],
      [0.04, 0.375],
    ] as const;

    for (const [bottom, top] of panels) {
      const height = (top - bottom) * DOOR_HEIGHT;
      const molding = new Mesh(
        track(createFrameGeometry(panelWidth, height, 0.016, 0.006)),
        lacquer,
      );
      molding.position.set(
        LEAF_WIDTH / 2,
        ((bottom + top) / 2) * DOOR_HEIGHT,
        LEAF_DEPTH,
      );
      leaf.add(molding);
    }

    if (withAstragal) {
      // Without this the shut line is a straight slot through to the
      // corridor, which reads as a bright seam down the middle of the doors.
      const astragal = new Mesh(
        track(new BoxGeometry(ASTRAGAL_WIDTH, DOOR_HEIGHT, ASTRAGAL_DEPTH)),
        lacquer,
      );
      astragal.position.set(
        LEAF_WIDTH + LEAF_GAP,
        DOOR_HEIGHT / 2,
        LEAF_DEPTH + ASTRAGAL_DEPTH / 2,
      );
      leaf.add(astragal);
    }

    const handle = new Mesh(fHoleGeometry, gold);
    handle.scale.setScalar(HANDLE_HEIGHT);
    handle.position.set(
      LEAF_WIDTH - HANDLE_INSET,
      HANDLE_CENTRE * DOOR_HEIGHT,
      LEAF_DEPTH,
    );
    leaf.add(handle);

    return leaf;
  }

  const leafZ = WALL_DEPTH - LEAF_SETBACK - LEAF_DEPTH;

  const leftHinge = new Object3D();
  leftHinge.position.set(-OPENING_HALF, 0, leafZ);
  leftHinge.add(createLeaf(true));
  assembly.add(leftHinge);

  const rightHinge = new Object3D();
  rightHinge.position.set(OPENING_HALF, 0, leafZ);
  // A negative scale mirrors the leaf and its f-hole in one step; three
  // flips the winding order for us, so the lighting stays correct.
  rightHinge.scale.x = -1;
  rightHinge.add(createLeaf(false));
  assembly.add(rightHinge);

  // The jamb behind the leaves. Any perimeter gap now shows this rebate
  // rather than a slice of lit corridor.
  const stop = new Mesh(
    track(
      createFrameGeometry(OPENING_HALF * 2, springHeight, 0.02, leafZ * 0.9, 0),
    ),
    lacquer,
  );
  stop.position.set(0, springHeight / 2, 0);
  assembly.add(stop);

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
    // this explicit update the fixed 680px anchor collapses to roughly one
    // world unit and the doorway appears completely blank.
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
    // at the corners, and carries the casing's outline as its opening.
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
      OUTER_HALF * scale,
      floorY + springHeight * scale,
      floorY,
      centerX,
    );
    shape.holes.push(hole);

    wall.geometry.dispose();
    wall.geometry = new ExtrudeGeometry(shape, {
      depth: WALL_DEPTH * scale,
      bevelEnabled: false,
      curveSegments: 48,
    });
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
      const halfWidth = OPENING_HALF * scale;
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
      for (const geometry of geometries) geometry.dispose();
      for (const material of materials) material.dispose();
    },
  };
}
