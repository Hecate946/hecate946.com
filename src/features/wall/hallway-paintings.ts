import {
  BufferGeometry,
  CanvasTexture,
  ClampToEdgeWrapping,
  Group,
  LinearFilter,
  LinearMipmapLinearFilter,
  Mesh,
  MeshBasicMaterial,
  Object3D,
  PerspectiveCamera,
  PlaneGeometry,
  Raycaster,
  SRGBColorSpace,
  Texture,
  TextureLoader,
  Vector2,
} from 'three';
import { createFrameGeometry } from './hallway-geometry';
import { HALLWAY_LOOP_DEPTH } from './wall-config';

/**
 * The paintings, hung in the corridor as real geometry.
 *
 * They used to be DOM anchors floating in a CSS 3D layer above the canvas.
 * As meshes, their edges now receive the same mipmapping and antialiasing as
 * the rest of the corridor.
 *
 * The anchors stay in the DOM, visually hidden, so links, prefetch, focus
 * order, and screen readers keep working exactly as they did.
 */

export interface PaintingSpec {
  label: string;
  src: string;
  side: 'left' | 'right';
  /** Position along the corridor, in world units. */
  z: number;
}

/** One lap of the gallery, and how far behind the camera a frame may sit. */
export const LOOP_DEPTH = HALLWAY_LOOP_DEPTH;
const BEHIND_ALLOWANCE = 360;

/** The window in which a frame is close enough to be worth clicking. */
const PICKABLE_NEAR = 180;
const PICKABLE_FAR = 2_900;

const WALL_GAP = 4;
const FRAME_BORDER = 11.2;
const FRAME_DEPTH = 9;

/**
 * The swing window. Both edges sit far down the corridor so a frame has
 * already presented itself at the full angle long before the camera arrives,
 * rather than opening in the viewer's face. `TURN_FULL` is what "much farther
 * away" means in world units: past that point the frame is at exactly 45deg
 * and simply grows.
 */
const TURN_START = 2_600;
const TURN_FULL = 1_700;
const TURN_ANGLE = Math.PI / 4;

/**
 * The far visibility ramp. It has to clear `TURN_START`, or a frame would
 * begin its swing while still fading up and appear to open out of the fog.
 */
const FADE_FAR_START = 3_400;
const FADE_FAR_END = 6_500;

const FRAME_COLOR = 0x050505;
const FRAME_HOVER = 0x1d1d1d;

function smoothstep(edge0: number, edge1: number, value: number) {
  const t = Math.min(1, Math.max(0, (value - edge0) / (edge1 - edge0)));
  return t * t * (3 - 2 * t);
}

/** A quick outward swing that settles at exactly the requested angle. */
function swingEase(value: number) {
  const t = Math.min(1, Math.max(0, value));
  return 1 - (1 - t) ** 3;
}

function modulo(value: number, period: number) {
  return ((value % period) + period) % period;
}

/** `object-fit: cover`, expressed as a texture transform. */
function applyCover(texture: Texture, frameAspect: number) {
  const image = texture.image as { width: number; height: number } | undefined;
  if (!image?.width || !image?.height) return;

  const imageAspect = image.width / image.height;
  if (imageAspect > frameAspect) {
    const fit = frameAspect / imageAspect;
    texture.repeat.set(fit, 1);
    texture.offset.set((1 - fit) / 2, 0);
  } else {
    const fit = imageAspect / frameAspect;
    texture.repeat.set(1, fit);
    texture.offset.set(0, (1 - fit) / 2);
  }
}

function paintHeaderLabel(
  canvas: HTMLCanvasElement,
  text: string,
  width: number,
  height: number,
  pixelRatio: number,
) {
  canvas.width = Math.max(1, Math.round(width * pixelRatio));
  canvas.height = Math.max(1, Math.round(height * pixelRatio));

  const context = canvas.getContext('2d');
  if (!context) return;
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  // A subtly inset black field makes the surrounding header read as a frame.
  // Its margins are established by the geometry at exactly FRAME_BORDER.
  context.fillStyle = '#0a0a0a';
  context.fillRect(0, 0, width, height);

  const label = text.toUpperCase();
  const fontSize = height * 0.82;
  const tracking = fontSize * 0.12;
  context.font = `600 ${fontSize}px 'Times New Roman', Times, serif`;
  context.textBaseline = 'middle';
  context.fillStyle = '#f4f3ed';
  context.globalAlpha = 0.94;

  const characters = [...label];
  const widths = characters.map(
    (character) => context.measureText(character).width,
  );
  const textWidth =
    widths.reduce((total, characterWidth) => total + characterWidth, 0) +
    tracking * Math.max(0, characters.length - 1);
  let x = (width - textWidth) / 2;
  for (const [index, character] of characters.entries()) {
    context.fillText(character, x, height / 2 + fontSize * 0.035);
    x += widths[index] + tracking;
  }
  context.globalAlpha = 1;
}

interface PaintingParts {
  root: Object3D;
  frame: Mesh<BufferGeometry, MeshBasicMaterial>;
  image: Mesh<BufferGeometry, MeshBasicMaterial>;
  header: Mesh<BufferGeometry, MeshBasicMaterial>;
  label: Mesh<BufferGeometry, MeshBasicMaterial>;
  labelCanvas: HTMLCanvasElement;
  labelMap: CanvasTexture;
  imageMap: Texture;
  distance: number;
}

export interface HallwayPaintings {
  readonly group: Group;
  /** Resize the frames and re-hang them on the corridor walls. */
  layout(
    halfWidth: number,
    wallCentreY: number,
    frameWidth: number,
    frameHeight: number,
  ): void;
  /** Reposition and fade for a corridor position. */
  update(cameraZ: number): void;
  /** Index of the painting under the pointer, or -1. */
  pick(ndc: Vector2, camera: PerspectiveCamera): number;
  /** Highlight one painting, or -1 for none. */
  setHovered(index: number): void;
  dispose(): void;
}

export function createHallwayPaintings(
  specs: readonly PaintingSpec[],
  pixelRatio: number,
  onTextureReady: () => void,
): HallwayPaintings {
  const group = new Group();
  const loader = new TextureLoader();
  const raycaster = new Raycaster();
  const geometries: BufferGeometry[] = [];
  const parts: PaintingParts[] = [];

  let hingeForwardOffset = 0;
  /** Frame aspect, kept so textures that decode later can still be fitted. */
  let glassAspect = 1;

  for (const spec of specs) {
    const root = new Object3D();
    root.rotation.y = spec.side === 'left' ? Math.PI / 2 : -Math.PI / 2;

    let settled = false;
    const settleTexture = () => {
      if (settled) return;
      settled = true;
      onTextureReady();
    };
    const imageMap = loader.load(
      spec.src,
      (texture) => {
        texture.colorSpace = SRGBColorSpace;
        texture.anisotropy = 8;
        applyCover(texture, glassAspect);
        settleTexture();
      },
      undefined,
      settleTexture,
    );

    const frame = new Mesh(
      new BufferGeometry(),
      new MeshBasicMaterial({ color: FRAME_COLOR, transparent: true }),
    );
    const image = new Mesh(
      new BufferGeometry(),
      new MeshBasicMaterial({ map: imageMap, transparent: true }),
    );
    const header = new Mesh(new BufferGeometry(), frame.material);
    const labelCanvas = document.createElement('canvas');
    const labelMap = new CanvasTexture(labelCanvas);
    labelMap.colorSpace = SRGBColorSpace;
    labelMap.wrapS = ClampToEdgeWrapping;
    labelMap.wrapT = ClampToEdgeWrapping;
    labelMap.minFilter = LinearMipmapLinearFilter;
    labelMap.magFilter = LinearFilter;
    labelMap.generateMipmaps = true;
    labelMap.anisotropy = 8;
    const label = new Mesh(
      new BufferGeometry(),
      // No polygon offset: the label is recessed inside the header's opening
      // now, so pulling it towards the camera would push it through the bevel.
      new MeshBasicMaterial({
        map: labelMap,
        transparent: true,
        depthWrite: false,
      }),
    );
    label.renderOrder = 2;
    // Artwork and its integrated header act as one linked object.
    image.userData.paintingIndex = parts.length;
    header.userData.paintingIndex = parts.length;
    label.userData.paintingIndex = parts.length;

    root.add(frame, image, header, label);
    group.add(root);
    parts.push({
      root,
      frame,
      image,
      header,
      label,
      labelCanvas,
      labelMap,
      imageMap,
      distance: Infinity,
    });
  }

  function layout(
    halfWidth: number,
    wallCentreY: number,
    frameWidth: number,
    frameHeight: number,
  ) {
    const glassWidth = frameWidth - FRAME_BORDER * 2;
    const glassHeight = frameHeight - FRAME_BORDER * 2;
    const headerHeight = Math.max(46, Math.min(64, frameWidth * 0.12));
    const labelWidth = frameWidth - FRAME_BORDER * 2;
    // All four margins around the text match the artwork-frame thickness.
    const labelHeight = headerHeight - FRAME_BORDER * 2;
    glassAspect = glassWidth / glassHeight;
    hingeForwardOffset = frameWidth / 2;

    for (const geometry of geometries) geometry.dispose();
    geometries.length = 0;

    const frameGeometry = createFrameGeometry(
      frameWidth,
      frameHeight,
      FRAME_BORDER,
      FRAME_DEPTH,
      2.2,
    );
    const glassGeometry = new PlaneGeometry(glassWidth, glassHeight);
    // The header is the same millwork as the frame below it, not a slab laid
    // on top of it. A BoxGeometry of FRAME_DEPTH is centred on z, so its face
    // sat at z = FRAME_DEPTH / 2 while the extruded frame -- which carries a
    // bevel on each end -- reached z = FRAME_DEPTH + bevel. The header
    // therefore read as a thinner plate set back from the frame. Extruding it
    // through the identical call makes the two profiles literally the same
    // moulding: same depth, same bevel, same border, one flush outer edge.
    const headerGeometry = createFrameGeometry(
      frameWidth,
      headerHeight,
      FRAME_BORDER,
      FRAME_DEPTH,
      2.2,
    );
    const labelGeometry = new PlaneGeometry(labelWidth, labelHeight);
    geometries.push(
      frameGeometry,
      glassGeometry,
      headerGeometry,
      labelGeometry,
    );

    for (const [index, part] of parts.entries()) {
      const side = specs[index].side;
      part.root.position.x =
        side === 'left' ? -(halfWidth - WALL_GAP) : halfWidth - WALL_GAP;
      part.root.position.y = wallCentreY;

      // The root is the hinge at the vertical edge nearest the camera. In the
      // closed position the child offset puts the frame centre back at its
      // original wall coordinate; rotating the root then moves every other
      // point inward instead of burying half the frame in the brickwork.
      const centreFromHinge =
        side === 'left' ? frameWidth / 2 : -frameWidth / 2;
      part.frame.geometry = frameGeometry;
      part.frame.position.set(centreFromHinge, -headerHeight / 2, 0);

      part.image.geometry = glassGeometry;
      part.image.position.set(
        centreFromHinge,
        -headerHeight / 2,
        FRAME_DEPTH * 0.35,
      );
      applyCover(part.imageMap, glassAspect);

      part.header.geometry = headerGeometry;
      part.header.position.set(centreFromHinge, frameHeight / 2, 0);

      part.label.geometry = labelGeometry;
      // The header now has a real opening, so the label sits inside it at the
      // artwork's depth instead of floating in front of a solid face.
      part.label.position.set(
        centreFromHinge,
        frameHeight / 2,
        FRAME_DEPTH * 0.35,
      );
      paintHeaderLabel(
        part.labelCanvas,
        specs[index].label,
        labelWidth,
        labelHeight,
        Math.max(2.5, pixelRatio),
      );
      part.labelMap.needsUpdate = true;
    }
  }

  function update(cameraZ: number) {
    for (const [index, part] of parts.entries()) {
      const spec = specs[index];
      const distance =
        modulo(spec.z - cameraZ + BEHIND_ALLOWANCE, LOOP_DEPTH) -
        BEHIND_ALLOWANCE;
      part.distance = distance;
      part.root.position.z = -distance + hingeForwardOffset;

      // Ease the frame outward around its near-edge hinge as it approaches.
      // The frame never chases the pointer or moves the camera, so the effect
      // works equally well with touch, wheel, and keyboard navigation.
      const linearTurn =
        (TURN_START - distance) / Math.max(1, TURN_START - TURN_FULL);
      const turnProgress = swingEase(linearTurn);
      part.root.rotation.y =
        spec.side === 'left'
          ? Math.PI / 2 - TURN_ANGLE * turnProgress
          : -Math.PI / 2 + TURN_ANGLE * turnProgress;

      // The same near and far ramps the CSS layer used.
      const opacity =
        smoothstep(80, 240, distance) *
        Math.max(0.02, 1 - smoothstep(FADE_FAR_START, FADE_FAR_END, distance));
      part.root.visible = opacity > 0.02;
      for (const mesh of [part.frame, part.image, part.header, part.label]) {
        mesh.material.opacity = opacity;
      }
    }
  }

  return {
    group,
    layout,
    update,
    pick(ndc, camera) {
      raycaster.setFromCamera(ndc, camera);
      const targets = parts
        .filter(
          (part) =>
            part.root.visible &&
            part.distance > PICKABLE_NEAR &&
            part.distance < PICKABLE_FAR,
        )
        .flatMap((part) => [part.image, part.header, part.label]);
      const hit = raycaster.intersectObjects(targets, false)[0];
      return hit ? (hit.object.userData.paintingIndex as number) : -1;
    },
    setHovered(index: number) {
      for (const [i, part] of parts.entries()) {
        part.frame.material.color.setHex(
          i === index ? FRAME_HOVER : FRAME_COLOR,
        );
      }
    },
    dispose() {
      for (const geometry of geometries) geometry.dispose();
      for (const part of parts) {
        part.frame.material.dispose();
        part.image.material.dispose();
        part.label.material.dispose();
        part.labelMap.dispose();
        part.imageMap.dispose();
      }
    },
  };
}
