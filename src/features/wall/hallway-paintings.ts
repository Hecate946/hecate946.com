import {
  BoxGeometry,
  BufferGeometry,
  CanvasTexture,
  Group,
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
  id: string;
  label: string;
  indexLabel: string;
  src: string;
  side: 'left' | 'right';
  /** Position along the corridor, in world units. */
  z: number;
}

/** One lap of the gallery, and how far behind the camera a frame may sit. */
export const LOOP_DEPTH = 5_760;
const BEHIND_ALLOWANCE = 360;

/** The window in which a frame is close enough to be worth clicking. */
const PICKABLE_NEAR = 180;
const PICKABLE_FAR = 2_450;

const WALL_GAP = 4;
const VERTICAL_OFFSET = 26;
const LABEL_HEIGHT = 38.4;
const FRAME_BORDER = 11.2;
const FRAME_DEPTH = 9;
const SILL_HEIGHT = 8.8;

const FRAME_COLOR = 0x050505;
const FRAME_HOVER = 0x1d1d1d;

function smoothstep(edge0: number, edge1: number, value: number) {
  const t = Math.min(1, Math.max(0, (value - edge0) / (edge1 - edge0)));
  return t * t * (3 - 2 * t);
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

function paintLabel(
  canvas: HTMLCanvasElement,
  spec: PaintingSpec,
  width: number,
  ink: string,
  scale: number,
) {
  const height = LABEL_HEIGHT;
  canvas.width = Math.round(width * scale);
  canvas.height = Math.round(height * scale);

  const context = canvas.getContext('2d');
  if (!context) return;
  context.setTransform(scale, 0, 0, scale, 0, 0);
  context.clearRect(0, 0, width, height);

  const baseline = height * 0.66;
  context.font = "400 15px 'Times New Roman', Times, serif";
  context.textBaseline = 'alphabetic';
  if ('letterSpacing' in context) context.letterSpacing = '2.4px';

  context.fillStyle = ink;
  context.globalAlpha = 0.42;
  context.fillText(spec.indexLabel, 0, baseline);

  const indexWidth = context.measureText(spec.indexLabel).width;
  context.globalAlpha = 0.72;
  context.fillText(spec.label.toUpperCase(), indexWidth + 14, baseline);
  context.globalAlpha = 1;
}

interface PaintingParts {
  root: Object3D;
  frame: Mesh<BufferGeometry, MeshBasicMaterial>;
  image: Mesh<BufferGeometry, MeshBasicMaterial>;
  sill: Mesh<BufferGeometry, MeshBasicMaterial>;
  label: Mesh<BufferGeometry, MeshBasicMaterial>;
  labelCanvas: HTMLCanvasElement;
  labelMap: CanvasTexture;
  imageMap: Texture;
  distance: number;
}

export interface HallwayPaintings {
  readonly group: Group;
  /** Resize the frames and re-hang them on the corridor walls. */
  layout(halfWidth: number, frameWidth: number, frameHeight: number): void;
  /** Repaint the labels for the current colour mode. */
  setInk(ink: string): void;
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

  let ink = '#ffffff';
  let labelWidth = 0;
  /** Frame aspect, kept so textures that decode later can still be fitted. */
  let glassAspect = 1;

  for (const spec of specs) {
    const root = new Object3D();
    root.rotation.y = spec.side === 'left' ? Math.PI / 2 : -Math.PI / 2;
    root.position.y = VERTICAL_OFFSET;

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
    const sill = new Mesh(
      new BufferGeometry(),
      new MeshBasicMaterial({ color: FRAME_COLOR, transparent: true }),
    );

    const labelCanvas = document.createElement('canvas');
    const labelMap = new CanvasTexture(labelCanvas);
    labelMap.colorSpace = SRGBColorSpace;
    const label = new Mesh(
      new BufferGeometry(),
      new MeshBasicMaterial({ map: labelMap, transparent: true }),
    );

    // The image carries the click target, so it is the only pickable mesh.
    image.userData.paintingIndex = parts.length;

    root.add(frame, image, sill, label);
    group.add(root);
    parts.push({
      root,
      frame,
      image,
      sill,
      label,
      labelCanvas,
      labelMap,
      imageMap,
      distance: Infinity,
    });
  }

  function layout(halfWidth: number, frameWidth: number, frameHeight: number) {
    const glassWidth = frameWidth - FRAME_BORDER * 2;
    const glassHeight = frameHeight - FRAME_BORDER * 2;
    glassAspect = glassWidth / glassHeight;
    labelWidth = frameWidth;

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
    const sillGeometry = new BoxGeometry(
      frameWidth + 20,
      SILL_HEIGHT,
      FRAME_DEPTH * 1.5,
    );
    const labelGeometry = new PlaneGeometry(frameWidth, LABEL_HEIGHT);
    geometries.push(frameGeometry, glassGeometry, sillGeometry, labelGeometry);

    // The anchor box is frame plus label; the group's origin sits at its
    // centre, exactly as the CSS box did.
    const boxHeight = frameHeight + LABEL_HEIGHT;
    const frameCentre = boxHeight / 2 - frameHeight / 2;
    const labelCentre = -boxHeight / 2 + LABEL_HEIGHT / 2;

    for (const part of parts) {
      part.root.position.x =
        part.root.rotation.y > 0
          ? -(halfWidth - WALL_GAP)
          : halfWidth - WALL_GAP;

      part.frame.geometry = frameGeometry;
      part.frame.position.set(0, frameCentre, 0);

      part.image.geometry = glassGeometry;
      part.image.position.set(0, frameCentre, FRAME_DEPTH * 0.35);
      applyCover(part.imageMap, glassAspect);

      part.sill.geometry = sillGeometry;
      part.sill.position.set(
        0,
        frameCentre - frameHeight / 2 - SILL_HEIGHT / 2,
        FRAME_DEPTH * 0.4,
      );

      part.label.geometry = labelGeometry;
      part.label.position.set(0, labelCentre, 1);
    }

    setInk(ink);
  }

  function setInk(nextInk: string) {
    ink = nextInk;
    if (labelWidth === 0) return;
    for (const [index, part] of parts.entries()) {
      paintLabel(part.labelCanvas, specs[index], labelWidth, ink, pixelRatio);
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
      part.root.position.z = -distance;

      // The same near and far ramps the CSS layer used.
      const opacity =
        smoothstep(80, 240, distance) *
        Math.max(0.02, 1 - smoothstep(2_650, LOOP_DEPTH - 250, distance));
      part.root.visible = opacity > 0.02;
      for (const mesh of [part.frame, part.image, part.sill, part.label]) {
        mesh.material.opacity = opacity;
      }
    }
  }

  return {
    group,
    layout,
    setInk,
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
        .map((part) => part.image);
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
        part.sill.material.dispose();
        part.label.material.dispose();
        part.labelMap.dispose();
        part.imageMap.dispose();
      }
    },
  };
}
