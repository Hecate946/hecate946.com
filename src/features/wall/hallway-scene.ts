import {
  AmbientLight,
  BufferAttribute,
  CanvasTexture,
  ClampToEdgeWrapping,
  DirectionalLight,
  EqualStencilFunc,
  Fog,
  KeepStencilOp,
  LinearMipmapLinearFilter,
  Material,
  Mesh,
  MeshBasicMaterial,
  PMREMGenerator,
  PerspectiveCamera,
  PlaneGeometry,
  RepeatWrapping,
  SRGBColorSpace,
  Scene,
  Texture,
  Vector2,
  WebGLRenderer,
  type Wrapping,
} from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { createHallwayDoor, type DoorRect } from './hallway-door';
import { createHallwayPaintings, type PaintingSpec } from './hallway-paintings';

/**
 * WebGL corridor for the homepage.
 *
 * The corridor used to be four CSS compositor layers, one of them 6720px
 * long, each repeating an SVG background. The browser rasterises those
 * without mipmaps, so the 2px grout and the 120px checker alias apart as
 * soon as perspective compresses them below a screen pixel -- that is the
 * flicker in the distance. Here the same four surfaces are textured quads
 * with mipmapping and anisotropic filtering, which is the hardware's own
 * answer to that problem, on one draw call each.
 *
 * The look is deliberately unchanged. The camera is derived from the very
 * `perspective` and `perspective-origin` the CSS scene already declares, so
 * one CSS pixel is still one world unit and the paintings stay ordinary DOM
 * anchors sharing the same 3D space.
 */

/** Corridor extents along the view axis, matching the previous CSS values. */
const TUNNEL_DEPTH = 6_720;
const TUNNEL_NEAR_Z = -20;
const TUNNEL_CENTER_Z = TUNNEL_NEAR_Z - TUNNEL_DEPTH / 2;

/** One brick module and one checker module, in world units. */
const BRICK_TILE_WIDTH = 120;
const BRICK_TILE_HEIGHT = 60;
const FLOOR_TILE = 240;

/** The far-wall veil that used to hide aliasing becomes honest linear fog. */
const FOG_START = -TUNNEL_NEAR_Z + TUNNEL_DEPTH * 0.42;

/** The checker is theme independent, exactly as the previous SVG was. */
const FLOOR_DARK = '#080a0a';
const FLOOR_LIGHT = '#f4f3ed';
const BLACK = 'rgb(0 0 0)';

interface Palette {
  /** --wall-dark */
  dark: string;
  /** --room-label-ink */
  labelInk: string;
  /** --wall-light */
  light: string;
  /** --wall-baseboard */
  baseboard: string;
  /** --wall-trim-line */
  trim: string;
  /** --hallway-grout-color */
  grout: string;
}

export interface HallwayScene {
  /** Re-derive camera and corridor size from the live CSS box. */
  resize(): void;
  /** Repaint the theme-dependent textures after a colour-mode change. */
  refreshTheme(): void;
  /** Draw one frame for the given corridor position. */
  render(cameraZ: number): void;
  /** 0 = shut, 1 = fully open. Hidden once the camera is through. */
  setDoor(open: number, visible: boolean): void;
  /** How far the camera travels between the entrance and the corridor. */
  getEntryDistance(): number;
  /** The doorway's on-screen box, for the entrance hit target. */
  getDoorRect(): DoorRect;
  /** Index of the painting under a client-space point, or -1. */
  pickPainting(clientX: number, clientY: number): number;
  /** Highlight one painting, or -1 for none. */
  setHoveredPainting(index: number): void;
  dispose(): void;
}

function parseRgb(value: string): [number, number, number] {
  const parts = value.match(/[\d.]+/g)?.map(Number) ?? [];
  return [parts[0] ?? 0, parts[1] ?? 0, parts[2] ?? 0];
}

/** `color-mix(in srgb, base, blend <amount>)`. */
function mix(base: string, blend: string, amount: number) {
  const from = parseRgb(base);
  const to = parseRgb(blend);
  const channel = (index: number) =>
    Math.round(from[index] + (to[index] - from[index]) * amount);
  return `rgb(${channel(0)} ${channel(1)} ${channel(2)})`;
}

/** Vertex colours multiply in linear space; CSS overlays composite in sRGB. */
function srgbToLinear(value: number) {
  return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
}

function rootFontSize() {
  return parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
}

/**
 * The probe maps the corridor's custom properties onto real properties. That
 * is the only way to read a `color-mix()` or a `max()` once the cascade has
 * resolved it, so CSS stays the single source of truth for both the palette
 * and the corridor's proportions.
 */
function readPalette(probe: HTMLElement): Palette {
  const style = getComputedStyle(probe);
  return {
    dark: style.color,
    light: style.backgroundColor,
    baseboard: style.borderTopColor,
    trim: style.borderRightColor,
    grout: style.borderBottomColor,
    labelInk: style.borderLeftColor,
  };
}

function paintWall(
  canvas: HTMLCanvasElement,
  height: number,
  palette: Palette,
  scale: number,
) {
  const width = BRICK_TILE_WIDTH;
  canvas.width = Math.round(width * scale);
  canvas.height = Math.max(1, Math.round(height * scale));

  const context = canvas.getContext('2d');
  if (!context) return;
  context.setTransform(scale, 0, 0, scale, 0, 0);

  const wall = context.createLinearGradient(0, 0, 0, height);
  wall.addColorStop(0, mix(palette.dark, palette.light, 0.03));
  wall.addColorStop(0.58, palette.dark);
  wall.addColorStop(1, mix(palette.dark, BLACK, 0.12));
  context.fillStyle = wall;
  context.fillRect(0, 0, width, height);

  // The same 120x60 brick module the SVG background drew, laid from the
  // ceiling down so the courses land exactly where they always did.
  context.fillStyle = palette.grout;
  for (let y = 0; y < height; y += BRICK_TILE_HEIGHT) {
    context.fillRect(0, y, width, 2);
    context.fillRect(0, y + 30, width, 2);
    context.fillRect(0, y, 2, 30);
    context.fillRect(60, y, 2, 30);
    context.fillRect(30, y + 30, 2, 30);
    context.fillRect(90, y + 30, 2, 30);
  }

  // inset 0 -6rem 8rem rgb(0 0 0 / 22%)
  const rem = rootFontSize();
  const shadowHeight = 10 * rem;
  const shadow = context.createLinearGradient(
    0,
    height - shadowHeight,
    0,
    height,
  );
  shadow.addColorStop(0, 'rgb(0 0 0 / 0%)');
  shadow.addColorStop(1, 'rgb(0 0 0 / 22%)');
  context.fillStyle = shadow;
  context.fillRect(0, height - shadowHeight, width, shadowHeight);

  const baseboardHeight = 1.05 * rem;
  const baseboardTop = height - baseboardHeight;
  const baseboard = context.createLinearGradient(0, baseboardTop, 0, height);
  baseboard.addColorStop(0, mix(palette.baseboard, palette.light, 0.1));
  baseboard.addColorStop(0.35, palette.baseboard);
  baseboard.addColorStop(1, mix(palette.baseboard, BLACK, 0.18));
  context.fillStyle = baseboard;
  context.fillRect(0, baseboardTop, width, baseboardHeight);
  context.fillStyle = palette.trim;
  context.fillRect(0, baseboardTop, width, 1);
}

function paintFloor(canvas: HTMLCanvasElement, scale: number) {
  canvas.width = canvas.height = Math.round(FLOOR_TILE * scale);

  const context = canvas.getContext('2d');
  if (!context) return;
  context.setTransform(scale, 0, 0, scale, 0, 0);

  context.fillStyle = FLOOR_DARK;
  context.fillRect(0, 0, FLOOR_TILE, FLOOR_TILE);
  context.fillStyle = FLOOR_LIGHT;
  context.fillRect(120, 0, 120, 120);
  context.fillRect(0, 120, 120, 120);
}

function paintCeiling(
  canvas: HTMLCanvasElement,
  palette: Palette,
  scale: number,
) {
  const width = 256;
  const height = 4;
  canvas.width = Math.round(width * scale);
  canvas.height = Math.round(height * scale);

  const context = canvas.getContext('2d');
  if (!context) return;
  context.setTransform(scale, 0, 0, scale, 0, 0);

  context.fillStyle = mix(palette.dark, BLACK, 0.08);
  context.fillRect(0, 0, width, height);

  const edges = context.createLinearGradient(0, 0, width, 0);
  edges.addColorStop(0, 'rgb(0 0 0 / 16%)');
  edges.addColorStop(0.2, 'rgb(0 0 0 / 0%)');
  edges.addColorStop(0.8, 'rgb(0 0 0 / 0%)');
  edges.addColorStop(1, 'rgb(0 0 0 / 16%)');
  context.fillStyle = edges;
  context.fillRect(0, 0, width, height);
}

/** A unit plane whose vertex colours reproduce the floor's near-end shading. */
function createFloorGeometry() {
  const geometry = new PlaneGeometry(1, 1);
  const uv = geometry.attributes.uv;
  const colors = new Float32Array(uv.count * 3);

  // The floor carried `linear-gradient(180deg, transparent, rgb(0 0 0 / 14%))`
  // running from the far end to the near end. v = 0 is the near end here.
  const near = srgbToLinear(0.86);
  for (let index = 0; index < uv.count; index += 1) {
    const shade = near + (1 - near) * uv.getY(index);
    colors[index * 3] = shade;
    colors[index * 3 + 1] = shade;
    colors[index * 3 + 2] = shade;
  }

  geometry.setAttribute('color', new BufferAttribute(colors, 3));
  return geometry;
}

export function createHallwayScene(options: {
  /** The <canvas> filling `.hallway-scene`. */
  canvas: HTMLCanvasElement;
  /** `.hallway-scene` -- owns `perspective` and `perspective-origin`. */
  viewport: HTMLElement;
  /** The hidden element exposing the corridor's resolved CSS values. */
  probe: HTMLElement;
  /** The hidden element sized to `--hallway-painting-width` / `-height`. */
  frameProbe: HTMLElement;
  /** The gallery, in corridor order. */
  paintings: readonly PaintingSpec[];
  /** Called when a painting's texture decodes and a redraw is needed. */
  onReady: () => void;
}): HallwayScene {
  const { canvas, viewport, probe, frameProbe, onReady } = options;

  const renderer = new WebGLRenderer({
    canvas,
    alpha: true,
    antialias: true,
    powerPreference: 'high-performance',
    stencil: true,
  });
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  renderer.setPixelRatio(pixelRatio);

  const scene = new Scene();
  const camera = new PerspectiveCamera();
  const fog = new Fog(0x000000, 1, 2);
  scene.fog = fog;

  const wallCanvas = document.createElement('canvas');
  const floorCanvas = document.createElement('canvas');
  const ceilingCanvas = document.createElement('canvas');

  // Both walls share one painted canvas but scroll in opposite directions,
  // so each gets its own texture over the same image.
  const leftWallMap = new CanvasTexture(wallCanvas);
  const rightWallMap = new CanvasTexture(wallCanvas);
  const floorMap = new CanvasTexture(floorCanvas);
  const ceilingMap = new CanvasTexture(ceilingCanvas);

  const anisotropy = renderer.capabilities.getMaxAnisotropy();
  const prepare = (map: Texture, wrapS: Wrapping, wrapT: Wrapping) => {
    map.colorSpace = SRGBColorSpace;
    map.wrapS = wrapS;
    map.wrapT = wrapT;
    map.minFilter = LinearMipmapLinearFilter;
    map.anisotropy = anisotropy;
  };

  // Walls tile down the corridor and clamp across their height; the floor
  // tiles in both directions; the ceiling is a single stretched gradient.
  prepare(leftWallMap, RepeatWrapping, ClampToEdgeWrapping);
  prepare(rightWallMap, RepeatWrapping, ClampToEdgeWrapping);
  prepare(floorMap, RepeatWrapping, RepeatWrapping);
  prepare(ceilingMap, ClampToEdgeWrapping, ClampToEdgeWrapping);

  leftWallMap.repeat.set(TUNNEL_DEPTH / BRICK_TILE_WIDTH, 1);
  rightWallMap.repeat.copy(leftWallMap.repeat);
  floorMap.repeat.y = TUNNEL_DEPTH / FLOOR_TILE;

  const unitPlane = new PlaneGeometry(1, 1);
  const floorGeometry = createFloorGeometry();
  const leftWall = new Mesh(
    unitPlane,
    new MeshBasicMaterial({ map: leftWallMap }),
  );
  const rightWall = new Mesh(
    unitPlane,
    new MeshBasicMaterial({ map: rightWallMap }),
  );
  const floor = new Mesh(
    floorGeometry,
    new MeshBasicMaterial({ map: floorMap, vertexColors: true }),
  );
  const ceiling = new Mesh(
    unitPlane,
    new MeshBasicMaterial({ map: ceilingMap }),
  );
  const surfaces = [leftWall, rightWall, floor, ceiling];

  leftWall.rotation.y = Math.PI / 2;
  rightWall.rotation.y = -Math.PI / 2;
  floor.rotation.x = -Math.PI / 2;
  ceiling.rotation.x = Math.PI / 2;
  for (const surface of surfaces) {
    surface.position.z = TUNNEL_CENTER_Z;
    scene.add(surface);
  }

  paintFloor(floorCanvas, pixelRatio);

  // Black lacquer and gold are almost entirely reflection, so they need an
  // environment far more than they need lamps. One small PMREM probe gives
  // both a believable falloff; the two lights only add the direct highlight
  // that picks out the panel moldings and the f-holes' bevel.
  const pmrem = new PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.34;
  pmrem.dispose();

  // Deliberately dim and well off-axis. A strong light square-on to a flat
  // panel puts its specular lobe dead centre, which is what turned the doors
  // into a spotlit blob; the environment does the shaping instead and this
  // only picks out the mouldings and the f-holes' bevel.
  const keyLight = new DirectionalLight(0xfff4e2, 0.42);
  keyLight.position.set(-1.15, 1.4, 0.85);
  scene.add(keyLight, new AmbientLight(0xdfeff0, 0.55));

  // The shared DOM backdrop is the entrance wall. This material writes depth
  // without painting, so the doorway retains real occlusion while the exact
  // same bricks, baseboard, lighting, and floor used by the other pages remain
  // visible beneath the transparent canvas.
  const frontWallMaterial = new MeshBasicMaterial({
    colorWrite: false,
    depthWrite: true,
  });
  const revealMaterial = new MeshBasicMaterial({ color: 0x000000 });
  const door = createHallwayDoor([frontWallMaterial, revealMaterial]);
  scene.add(door.group);

  const paintings = createHallwayPaintings(
    options.paintings,
    pixelRatio,
    onReady,
  );
  scene.add(paintings.group);

  const corridorRoots = [...surfaces, paintings.group];
  let portalStencilEnabled = false;

  function visitMaterials(
    roots: readonly (Mesh | typeof paintings.group)[],
    visit: (material: Material) => void,
  ) {
    for (const root of roots) {
      root.traverse((object) => {
        if (!(object instanceof Mesh)) return;
        const meshMaterials = Array.isArray(object.material)
          ? object.material
          : [object.material];
        for (const material of meshMaterials) visit(material);
      });
    }
  }

  function setPortalStencil(enabled: boolean) {
    if (portalStencilEnabled === enabled) return;
    portalStencilEnabled = enabled;

    visitMaterials(corridorRoots, (material) => {
      // Three.js enables the stencil test through stencilWrite. A zero write
      // mask makes these materials read the portal stencil without changing it.
      material.stencilWrite = enabled;
      material.stencilWriteMask = 0x00;
      material.stencilFunc = EqualStencilFunc;
      material.stencilRef = 1;
      material.stencilFuncMask = 0xff;
      material.stencilFail = KeepStencilOp;
      material.stencilZFail = KeepStencilOp;
      material.stencilZPass = KeepStencilOp;
      material.needsUpdate = true;
    });
  }

  let wallHeight = 0;
  let paintedWallHeight = -1;
  let viewWidth = 0;
  let viewHeight = 0;

  function refreshTheme() {
    const palette = readPalette(probe);
    paintWall(wallCanvas, wallHeight, palette, pixelRatio);
    paintCeiling(ceilingCanvas, palette, pixelRatio);
    paintedWallHeight = wallHeight;
    leftWallMap.needsUpdate = true;
    rightWallMap.needsUpdate = true;
    ceilingMap.needsUpdate = true;
    fog.color.set(palette.dark);
    paintings.setInk(palette.labelInk);
  }

  function resize() {
    const { width, height } = viewport.getBoundingClientRect();
    const box = probe.getBoundingClientRect();
    if (width === 0 || height === 0 || box.width === 0) return;
    viewWidth = width;
    viewHeight = height;

    const halfWidth = box.width;
    const halfHeight = box.height;
    wallHeight = halfHeight * 2;

    leftWall.scale.set(TUNNEL_DEPTH, wallHeight, 1);
    rightWall.scale.copy(leftWall.scale);
    leftWall.position.x = -halfWidth;
    rightWall.position.x = halfWidth;

    floor.scale.set(halfWidth * 2, TUNNEL_DEPTH, 1);
    ceiling.scale.copy(floor.scale);
    floor.position.y = -halfHeight;
    ceiling.position.y = halfHeight;
    floorMap.repeat.x = (halfWidth * 2) / FLOOR_TILE;

    // Match the CSS projection exactly: the eye sits `perspective` units in
    // front of the world origin, and `perspective-origin` decides where that
    // origin lands on screen. Rendering a frame twice the size of the origin
    // and cropping its top-left corner reproduces that off-centre centre.
    const style = getComputedStyle(viewport);
    const perspective = parseFloat(style.perspective) || 1_000;
    const [originX, originY] = style.perspectiveOrigin
      .split(' ')
      .map((value) => parseFloat(value));
    const fullWidth = Math.max(1, (originX || width / 2) * 2);
    const fullHeight = Math.max(1, (originY || height / 2) * 2);

    camera.fov =
      (2 * Math.atan(fullHeight / (2 * perspective)) * 180) / Math.PI;
    camera.aspect = fullWidth / fullHeight;
    camera.near = 1;
    camera.far = perspective + TUNNEL_DEPTH + 1;
    camera.position.set(0, 0, perspective);
    camera.setViewOffset(fullWidth, fullHeight, 0, 0, width, height);
    camera.updateProjectionMatrix();

    fog.near = perspective + FOG_START;
    fog.far = perspective + TUNNEL_DEPTH;

    door.layout(halfWidth, halfHeight, perspective);

    const frame = frameProbe.getBoundingClientRect();
    paintings.layout(halfWidth, frame.width, frame.height);
    renderer.setSize(width, height, false);
    if (wallHeight !== paintedWallHeight) refreshTheme();
  }

  function render(cameraZ: number) {
    // Geometry never moves. Recycling the texture phase keeps the corridor
    // endless and keeps the offsets small enough to stay precise.
    leftWallMap.offset.x = (cameraZ / BRICK_TILE_WIDTH) % 1;
    rightWallMap.offset.x = (-cameraZ / BRICK_TILE_WIDTH) % 1;
    floorMap.offset.y = (cameraZ / FLOOR_TILE) % 1;
    door.setCameraZ(cameraZ);
    const portalActive =
      door.group.visible && door.isBeforeCamera(camera.position.z);
    door.setPortalMask(portalActive);
    setPortalStencil(portalActive);
    paintings.update(cameraZ);
    renderer.render(scene, camera);
  }

  resize();

  return {
    resize,
    refreshTheme,
    render,
    setDoor(open: number, visible: boolean) {
      door.setOpen(open);
      door.group.visible = visible;
    },
    getEntryDistance() {
      return door.entryDistance;
    },
    getDoorRect() {
      return door.project(camera, viewWidth, viewHeight);
    },
    pickPainting(clientX: number, clientY: number) {
      const rect = viewport.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return -1;
      return paintings.pick(
        new Vector2(
          ((clientX - rect.left) / rect.width) * 2 - 1,
          -(((clientY - rect.top) / rect.height) * 2 - 1),
        ),
        camera,
      );
    },
    setHoveredPainting(index: number) {
      paintings.setHovered(index);
    },
    dispose() {
      paintings.dispose();
      door.dispose();
      frontWallMaterial.dispose();
      revealMaterial.dispose();
      scene.environment?.dispose();
      unitPlane.dispose();
      floorGeometry.dispose();
      for (const surface of surfaces) {
        (surface.material as MeshBasicMaterial).dispose();
      }
      for (const map of [leftWallMap, rightWallMap, floorMap, ceilingMap]) {
        map.dispose();
      }
      renderer.dispose();
    },
  };
}
