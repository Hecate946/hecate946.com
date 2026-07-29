import type { SeasonDefinition } from './types';

const TAU = Math.PI * 2;
const AUTUMN_FRAME_COUNT = 64;
const AUTUMN_SPRITE_SIZE = 384;
const AUTUMN_DRAW_SIZE = 340;
const AUTUMN_LEAF_ASSET_PATHS = [
  '/images/seasonal/autumn/autumn-leaf-3.png',
  '/images/seasonal/autumn/autumn-leaf-4.png',
  '/images/seasonal/autumn/autumn-leaf-orange.png',
] as const;

let autumnLeafImages: HTMLImageElement[] | null = null;
let autumnLeafAssetsPromise: Promise<void> | null = null;

function loadImage(source: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image();
    image.decoding = 'async';
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(`Failed to load autumn leaf asset: ${source}`));
    image.src = source;

    if (image.complete && image.naturalWidth > 0) {
      resolve(image);
    }
  });
}

export function preloadAutumnLeafAssets() {
  if (typeof window === 'undefined') return Promise.resolve();
  if (autumnLeafImages?.length === AUTUMN_LEAF_ASSET_PATHS.length) {
    return Promise.resolve();
  }
  if (autumnLeafAssetsPromise) return autumnLeafAssetsPromise;

  autumnLeafAssetsPromise = Promise.all(AUTUMN_LEAF_ASSET_PATHS.map((path) => loadImage(path))).then(
    (images) => {
      autumnLeafImages = images;
    },
  );

  return autumnLeafAssetsPromise;
}

function currentAutumnLeafImages() {
  return autumnLeafImages ?? [];
}

function drawShadow(context: CanvasRenderingContext2D, image: CanvasImageSource) {
  context.save();
  context.translate(6, 8);
  context.scale(1.02, 0.98);
  context.globalAlpha = 0.16;
  context.filter = 'blur(5px) brightness(0.7)';
  context.drawImage(
    image,
    -AUTUMN_DRAW_SIZE / 2,
    -AUTUMN_DRAW_SIZE / 2,
    AUTUMN_DRAW_SIZE,
    AUTUMN_DRAW_SIZE,
  );
  context.restore();
}

function drawLeafImage(
  context: CanvasRenderingContext2D,
  image: CanvasImageSource,
  variant: number,
  animationFrame = 0,
) {
  const phase =
    (animationFrame / AUTUMN_FRAME_COUNT) * TAU +
    ((variant % AUTUMN_LEAF_ASSET_PATHS.length) / AUTUMN_LEAF_ASSET_PATHS.length) * TAU * 0.83;

  // The PNG is realistic and detailed already; animate it with gentle yaw,
  // pitch, and roll so it still feels wind-driven and dimensional.
  const yaw = Math.sin(phase) * 1.08;
  const pitch = Math.cos(phase * 1.18 + variant * 0.67) * 0.34;
  const roll = Math.sin(phase * 0.72 + variant * 1.13) * 0.22;
  const widthScale = 0.34 + Math.abs(Math.cos(yaw)) * 0.9;
  const heightScale = 0.93 + Math.cos(pitch) * 0.08;
  const skew = Math.sin(yaw) * 0.16;
  const bendScaleX = 1 + Math.sin(phase * 1.43 + variant * 0.37) * 0.028;
  const bendScaleY = 1 - Math.sin(phase * 1.43 + variant * 0.37) * 0.018;
  const shadowOpacity = 0.12 + Math.abs(Math.sin(yaw)) * 0.05;
  const brightness = 0.94 + Math.cos(yaw) * 0.05 + Math.sin(pitch) * 0.03;
  const saturation = 1.01 + Math.abs(Math.sin(phase * 0.91)) * 0.03;

  context.save();
  context.rotate(roll + (variant - 1.5) * 0.06);
  context.transform(widthScale * bendScaleX, 0, skew, heightScale * bendScaleY, 0, 0);

  context.save();
  context.globalAlpha = shadowOpacity;
  drawShadow(context, image);
  context.restore();

  context.filter = `brightness(${brightness}) saturate(${saturation})`;
  context.drawImage(
    image,
    -AUTUMN_DRAW_SIZE / 2,
    -AUTUMN_DRAW_SIZE / 2,
    AUTUMN_DRAW_SIZE,
    AUTUMN_DRAW_SIZE,
  );
  context.filter = 'none';
  context.restore();
}

export function drawAutumnLeaf(
  context: CanvasRenderingContext2D,
  variant: number,
  animationFrame = 0,
) {
  const images = currentAutumnLeafImages();
  const image = images[variant % AUTUMN_LEAF_ASSET_PATHS.length];
  if (!image) return;
  drawLeafImage(context, image, variant, animationFrame);
}

export const autumnShower: SeasonDefinition = {
  variantCount: AUTUMN_LEAF_ASSET_PATHS.length,
  animationFrames: AUTUMN_FRAME_COUNT,
  spriteSize: AUTUMN_SPRITE_SIZE,
  particleCount: { compact: 100, desktop: 160 },
  size: { minimum: 40, maximum: 60 },
  scale: 1.12,
  speed: { minimum: 108, maximum: 154 },
  drift: { minimum: -3.2, maximum: 3.2 },
  sway: { minimum: 1.8, maximum: 6.2 },
  swayRate: { minimum: 0.34, maximum: 0.72 },
  spin: { minimum: -0.22, maximum: 0.22 },
  flutterRate: { minimum: 2.8, maximum: 4.4 },
  opacity: { minimum: 0.97, maximum: 1 },
  flutter: false,
  drawSprite: drawAutumnLeaf,
};
