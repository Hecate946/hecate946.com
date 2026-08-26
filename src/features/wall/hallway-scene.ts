import {
  BufferAttribute,
  CanvasTexture,
  ClampToEdgeWrapping,
  Fog,
  LinearMipmapLinearFilter,
  Mesh,
  MeshBasicMaterial,
  PerspectiveCamera,
  PlaneGeometry,
  RepeatWrapping,
  SRGBColorSpace,
  Scene,
  Texture,
  Vector2,
  Vector3,
  WebGLRenderer,
  type Wrapping,
} from 'three';
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

/**
 * Corridor extents along the view axis. The visible wall/floor junction is
 * still measured at the old CSS near plane, but the actual quads continue
 * towards the camera. That extra foreground section prevents the loading
 * room's checkerboard from appearing as a second floor below the canvas.
 */
const TUNNEL_FAR_Z = -6_740;
const TUNNEL_NEAR_Z = 600;
const FLOOR_SEAM_REFERENCE_Z = -20;
const TUNNEL_DEPTH = TUNNEL_NEAR_Z - TUNNEL_FAR_Z;
const TUNNEL_CENTER_Z = (TUNNEL_NEAR_Z + TUNNEL_FAR_Z) / 2;

/** One brick module and one checker module, in world units. */
const BRICK_TILE_WIDTH = 120;
const BRICK_TILE_HEIGHT = 60;
const FLOOR_TILE = 240;

/** The far-wall veil that used to hide aliasing becomes honest linear fog. */
const FOG_START = 6_720 * 0.42;

/**
 * The corridor is four planes, so its vanishing point used to be a hole
 * straight through the transparent canvas onto the DOM brick backdrop --
 * which is why the far end appeared to be tiled. Capping it costs one
 * quad. The cap and the fog share `--hallway-end-color`, because a cap on
 * its own would still be tinted by fog and a fog change on its own would
 * still leave the hole; together the corridor simply dissolves into one
 * flat colour.
 */
// Sit just in front of the tiled planes' final edge. At exactly the same z,
// sub-pixel depth ties could expose the last brick row across the cap.
const END_WALL_Z = TUNNEL_FAR_Z + 4;

/** The checker is theme independent, exactly as the previous SVG was. */
const FLOOR_DARK = '#080a0a';
const FLOOR_LIGHT = '#f4f3ed';
const BLACK = 'rgb(0 0 0)';

interface Palette {
  /** --wall-dark */
  dark: string;
  /** --wall-light */
  light: string;
  /** --wall-baseboard */
  baseboard: string;
  /** --wall-trim-line */
  trim: string;
  /** --hallway-grout-color */
  grout: string;
  /** --hallway-end-color */
  endWall: string;
}

export interface HallwayScene {
  /** Re-derive camera and corridor size from the live CSS box. */
  resize(): void;
  /** Repaint the theme-dependent textures after a colour-mode change. */
  refreshTheme(): void;
  /** Draw one frame for the given corridor position. */
  render(cameraZ: number): void;
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
 * Mobile and lower-memory devices do not benefit from a full 2x backing
 * buffer on this scene. Capping them here cuts fill-rate and canvas memory
 * while CSS keeps the canvas at the exact same visual size.
 */
function choosePixelRatio() {
  const dpr = window.devicePixelRatio || 1;
  const device = navigator as Navigator & { deviceMemory?: number };
  const memory = device.deviceMemory ?? 8;
  const cores = navigator.hardwareConcurrency || 8;
  const mobile = window.matchMedia(
    '(max-width: 48rem), (pointer: coarse)',
  ).matches;

  if (memory <= 2 || cores <= 2) return Math.min(dpr, 1);
  if (mobile || memory <= 4 || cores <= 4) return Math.min(dpr, 1.25);
  return Math.min(dpr, 1.75);
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
    endWall: style.outlineColor,
  };
}

function paintWall(
  canvas: HTMLCanvasElement,
  height: number,
  palette: Palette,
  scale: number,
) {
  const width = BRICK_TILE_WIDTH;
  const pixelWidth = Math.round(width * scale);
  const pixelHeight = Math.max(1, Math.round(height * scale));
  if (canvas.width !== pixelWidth) canvas.width = pixelWidth;
  if (canvas.height !== pixelHeight) canvas.height = pixelHeight;

  const context = canvas.getContext('2d');
  if (!context) return;
  context.setTransform(scale, 0, 0, scale, 0, 0);
  context.clearRect(0, 0, width, height);

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

  // A restrained contact shadow above the baseboard. The previous broad,
  // 22% vignette read as a lighting error once the hallway filled the page.
  const rem = rootFontSize();
  const shadowHeight = 4 * rem;
  const shadow = context.createLinearGradient(
    0,
    height - shadowHeight,
    0,
    height,
  );
  shadow.addColorStop(0, 'rgb(0 0 0 / 0%)');
  shadow.addColorStop(1, 'rgb(0 0 0 / 10%)');
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

  // Keep the ceiling only fractionally darker than the walls. A larger tint
  // turns the ceiling/wall junction into a hard theatrical shadow.
  context.fillStyle = mix(palette.dark, BLACK, 0.035);
  context.fillRect(0, 0, width, height);

  // A narrow contact falloff gives the corner enough depth to read without
  // stretching a dark wedge from each top corner to the vanishing point.
  const edges = context.createLinearGradient(0, 0, width, 0);
  edges.addColorStop(0, 'rgb(0 0 0 / 3%)');
  edges.addColorStop(0.08, 'rgb(0 0 0 / 0%)');
  edges.addColorStop(0.92, 'rgb(0 0 0 / 0%)');
  edges.addColorStop(1, 'rgb(0 0 0 / 3%)');
  context.fillStyle = edges;
  context.fillRect(0, 0, width, height);
}

/** A unit plane whose vertex colours reproduce the floor's near-end shading. */
function createFloorGeometry() {
  const geometry = new PlaneGeometry(1, 1);
  const uv = geometry.attributes.uv;
  const colors = new Float32Array(uv.count * 3);

  // Keep only a soft six-percent near-floor falloff. This preserves depth
  // without producing the large artificial shadow visible in the old footer.
  const near = srgbToLinear(0.94);
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
  /** The CSS wall/floor seam used to align the WebGL floor. */
  floorSeam: HTMLElement;
  /** The gallery, in corridor order. */
  paintings: readonly PaintingSpec[];
  /** Called when a painting's texture decodes and a redraw is needed. */
  onTextureUpdate: () => void;
  /** Called after every painting texture settles and the first frame exists. */
  onReady: () => void;
}): HallwayScene {
  const {
    canvas,
    viewport,
    probe,
    frameProbe,
    floorSeam,
    onReady,
    onTextureUpdate,
  } = options;

  const renderer = new WebGLRenderer({
    canvas,
    alpha: true,
    antialias: true,
    powerPreference: 'high-performance',
    stencil: false,
  });
  const pixelRatio = choosePixelRatio();
  renderer.setPixelRatio(pixelRatio);

  const scene = new Scene();
  const camera = new PerspectiveCamera();
  const fog = new Fog(0x000000, 1, 2);
  scene.fog = fog;

  const leftWallCanvas = document.createElement('canvas');
  const rightWallCanvas = document.createElement('canvas');
  const floorCanvas = document.createElement('canvas');
  const ceilingCanvas = document.createElement('canvas');

  // Each wall owns its canvas. Sharing a resized canvas between two GPU
  // textures can leave one upload pointing at the pre-resize pixels on some
  // mobile/browser combinations, which caused the wall-only theme mismatch.
  const leftWallMap = new CanvasTexture(leftWallCanvas);
  const rightWallMap = new CanvasTexture(rightWallCanvas);
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
  // An unlit, untextured cap: it must remain a completely blank continuation
  // of the wall colour, independent of the brick maps and scene lighting.
  const endWallMaterial = new MeshBasicMaterial({
    fog: false,
    toneMapped: false,
  });
  const endWall = new Mesh(unitPlane, endWallMaterial);
  const surfaces = [leftWall, rightWall, floor, ceiling];

  leftWall.rotation.y = Math.PI / 2;
  rightWall.rotation.y = -Math.PI / 2;
  floor.rotation.x = -Math.PI / 2;
  ceiling.rotation.x = Math.PI / 2;
  for (const surface of surfaces) {
    surface.position.z = TUNNEL_CENTER_Z;
    scene.add(surface);
  }
  endWall.position.z = END_WALL_Z;
  scene.add(endWall);

  paintFloor(floorCanvas, pixelRatio);
  let settledTextures = 0;
  const paintings = createHallwayPaintings(
    options.paintings,
    pixelRatio,
    () => {
      settledTextures += 1;
      onTextureUpdate();
      if (settledTextures >= options.paintings.length) onReady();
    },
  );
  scene.add(paintings.group);

  let wallHeight = 0;
  let paintedWallHeight = -1;

  function refreshTheme() {
    const palette = readPalette(probe);
    paintWall(leftWallCanvas, wallHeight, palette, pixelRatio);
    paintWall(rightWallCanvas, wallHeight, palette, pixelRatio);
    paintCeiling(ceilingCanvas, palette, pixelRatio);
    paintedWallHeight = wallHeight;
    leftWallMap.needsUpdate = true;
    rightWallMap.needsUpdate = true;
    ceilingMap.needsUpdate = true;
    fog.color.set(palette.endWall);
    endWallMaterial.color.set(palette.endWall);
    // The ready canvas is intentionally opaque. If a sub-pixel gap opens at
    // an edge, it reveals the same solid colour as the end cap, never the
    // brick-patterned CSS loading room underneath.
    renderer.setClearColor(palette.endWall, 1);
  }

  function resize() {
    const viewportRect = viewport.getBoundingClientRect();
    const { width, height } = viewportRect;
    const box = probe.getBoundingClientRect();
    const floorSeamRect = floorSeam.getBoundingClientRect();
    if (width === 0 || height === 0 || box.width === 0) return;

    const halfWidth = box.width;
    const halfHeight = box.height;

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
    // Keep the blank far cap comfortably inside the clipping range.
    camera.far = perspective - END_WALL_Z + 100;
    camera.position.set(0, 0, perspective);
    camera.setViewOffset(fullWidth, fullHeight, 0, 0, width, height);
    camera.updateProjectionMatrix();

    fog.near = perspective + FOG_START;
    fog.far = perspective - TUNNEL_FAR_Z;

    const ceilingY = halfHeight;
    // Project the existing CSS floor seam onto the corridor's near plane.
    // This preserves the exact first-frame handoff without using doorway
    // geometry as an indirect floor measurement.
    camera.updateMatrixWorld(true);
    const seamPoint = new Vector3(
      0,
      -(((floorSeamRect.top - viewportRect.top) / height) * 2 - 1),
      0,
    ).unproject(camera);
    const seamDirection = seamPoint.sub(camera.position);
    const seamDistance =
      (FLOOR_SEAM_REFERENCE_Z - camera.position.z) / seamDirection.z;
    const projectedFloor = camera.position
      .clone()
      .addScaledVector(seamDirection, seamDistance).y;
    const floorY = Number.isFinite(projectedFloor)
      ? projectedFloor
      : -halfHeight;
    wallHeight = ceilingY - floorY;

    leftWall.scale.set(TUNNEL_DEPTH, wallHeight, 1);
    rightWall.scale.copy(leftWall.scale);
    leftWall.position.set(-halfWidth, (ceilingY + floorY) / 2, TUNNEL_CENTER_Z);
    rightWall.position.set(halfWidth, (ceilingY + floorY) / 2, TUNNEL_CENTER_Z);

    floor.scale.set(halfWidth * 2, TUNNEL_DEPTH, 1);
    ceiling.scale.copy(floor.scale);
    floor.position.y = floorY;
    ceiling.position.y = ceilingY;
    floorMap.repeat.x = (halfWidth * 2) / FLOOR_TILE;

    // Slightly oversized so no seam can open along the corridor's corners.
    endWall.scale.set(halfWidth * 2 + 8, wallHeight + 8, 1);
    endWall.position.y = (ceilingY + floorY) / 2;

    const frame = frameProbe.getBoundingClientRect();
    paintings.layout(
      halfWidth,
      (ceilingY + floorY) / 2,
      frame.width,
      frame.height,
    );
    renderer.setSize(width, height, false);
    if (wallHeight !== paintedWallHeight) refreshTheme();
  }

  function render(cameraZ: number) {
    // Geometry never moves. Recycling the texture phase keeps the corridor
    // endless and keeps the offsets small enough to stay precise.
    leftWallMap.offset.x = (cameraZ / BRICK_TILE_WIDTH) % 1;
    rightWallMap.offset.x = (-cameraZ / BRICK_TILE_WIDTH) % 1;
    floorMap.offset.y = (cameraZ / FLOOR_TILE) % 1;
    paintings.update(cameraZ);
    renderer.render(scene, camera);
  }

  resize();
  if (options.paintings.length === 0) queueMicrotask(onReady);

  return {
    resize,
    refreshTheme,
    render,
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
      unitPlane.dispose();
      floorGeometry.dispose();
      for (const surface of surfaces) {
        (surface.material as MeshBasicMaterial).dispose();
      }
      endWallMaterial.dispose();
      for (const map of [leftWallMap, rightWallMap, floorMap, ceilingMap]) {
        map.dispose();
      }
      renderer.dispose();
    },
  };
}
