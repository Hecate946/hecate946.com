import { SEASONAL_SHOWERS } from './seasons';
import type { Season } from './types';

export const SEASON_SPRITE_SIZE = 180;

const spriteCache = new Map<string, HTMLCanvasElement>();
const seasonVariantCache = new Map<Season, HTMLCanvasElement[]>();
const seasonWarmupCache = new Map<Season, Promise<void>>();
const seasonFrameMatrixCache = new Map<Season, HTMLCanvasElement[][]>();

function normalizedFrame(season: Season, animationFrame: number) {
  const frameCount = SEASONAL_SHOWERS[season].animationFrames ?? 1;
  return ((Math.floor(animationFrame) % frameCount) + frameCount) % frameCount;
}

export function createSeasonSprite(
  season: Season,
  variant: number,
  animationFrame = 0,
) {
  const definition = SEASONAL_SHOWERS[season];
  const normalizedVariant =
    ((Math.floor(variant) % definition.variantCount) + definition.variantCount) %
    definition.variantCount;
  const frame = normalizedFrame(season, animationFrame);
  const cacheKey = `${season}:${normalizedVariant}:${frame}`;
  const cached = spriteCache.get(cacheKey);
  if (cached) return cached;

  const spriteSize = definition.spriteSize ?? SEASON_SPRITE_SIZE;
  const sprite = document.createElement('canvas');
  sprite.width = spriteSize;
  sprite.height = spriteSize;

  const context = sprite.getContext('2d');
  if (!context) return sprite;

  context.translate(spriteSize / 2, spriteSize / 2);
  context.lineCap = 'round';
  context.lineJoin = 'round';
  definition.drawSprite(context, normalizedVariant, frame);

  spriteCache.set(cacheKey, sprite);
  return sprite;
}

export function seasonSpriteAt(
  season: Season,
  variant: number,
  animationFrame = 0,
) {
  return createSeasonSprite(season, variant, animationFrame);
}

export function seasonSpriteAtPhase(
  season: Season,
  variant: number,
  phase: number,
) {
  const frameCount = SEASONAL_SHOWERS[season].animationFrames ?? 1;
  const normalizedPhase = ((phase % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
  const frame = Math.floor((normalizedPhase / (Math.PI * 2)) * frameCount);
  return createSeasonSprite(season, variant, frame);
}

// The collision field uses the closest cached orientation rather than
// cross-fading two complete ball sprites. This removes translucent edge
// ghosting and halves the number of summer draw calls.
export function seasonSpriteNearestAtPhase(
  season: Season,
  variant: number,
  phase: number,
) {
  const definition = SEASONAL_SHOWERS[season];
  const frameCount = definition.animationFrames ?? 1;
  const normalizedVariant =
    ((Math.floor(variant) % definition.variantCount) + definition.variantCount) %
    definition.variantCount;
  const normalizedPhase = ((phase % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
  const frame = Math.round((normalizedPhase / (Math.PI * 2)) * frameCount) % frameCount;
  const warmedFrames = seasonFrameMatrixCache.get(season);

  return warmedFrames?.[normalizedVariant]?.[frame] ??
    createSeasonSprite(season, normalizedVariant, frame);
}


export function seasonSpriteNearestSampleAtPhase(
  season: Season,
  variant: number,
  phase: number,
) {
  const definition = SEASONAL_SHOWERS[season];
  const frameCount = definition.animationFrames ?? 1;
  const normalizedVariant =
    ((Math.floor(variant) % definition.variantCount) + definition.variantCount) %
    definition.variantCount;
  const normalizedPhase = ((phase % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
  const exactFrame = (normalizedPhase / (Math.PI * 2)) * frameCount;
  const frame = Math.round(exactFrame) % frameCount;
  const sampledPhase = (frame / frameCount) * Math.PI * 2;
  const residualPhase = Math.atan2(
    Math.sin(normalizedPhase - sampledPhase),
    Math.cos(normalizedPhase - sampledPhase),
  );
  const warmedFrames = seasonFrameMatrixCache.get(season);

  return {
    sprite:
      warmedFrames?.[normalizedVariant]?.[frame] ??
      createSeasonSprite(season, normalizedVariant, frame),
    residualPhase,
  };
}

export function seasonSpriteBlendAtPhase(
  season: Season,
  variant: number,
  phase: number,
) {
  const frameCount = SEASONAL_SHOWERS[season].animationFrames ?? 1;
  const normalizedPhase = ((phase % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
  const exactFrame = (normalizedPhase / (Math.PI * 2)) * frameCount;
  const currentFrame = Math.floor(exactFrame);
  const nextFrame = (currentFrame + 1) % frameCount;

  return {
    current: createSeasonSprite(season, variant, currentFrame),
    next: createSeasonSprite(season, variant, nextFrame),
    mix: exactFrame - currentFrame,
  };
}

// Animated sprites are expensive to synthesize pixel-by-pixel. Build the
// complete frame set in small time-budgeted batches before the collision loop
// starts, so later frames never pause to create a missing texture.
export function prewarmSeasonSpriteFrames(
  season: Season,
  timeBudgetMs = 7,
): Promise<void> {
  const definition = SEASONAL_SHOWERS[season];
  const frameCount = definition.animationFrames ?? 1;
  if (frameCount <= 1) return Promise.resolve();

  const cachedWarmup = seasonWarmupCache.get(season);
  if (cachedWarmup) return cachedWarmup;

  const warmup = new Promise<void>((resolve) => {
    const frameMatrix = Array.from(
      { length: definition.variantCount },
      () => Array<HTMLCanvasElement>(frameCount),
    );
    let variant = 0;
    let frame = 0;

    const runBatch = () => {
      const batchStartedAt = performance.now();

      while (variant < definition.variantCount) {
        frameMatrix[variant]![frame] = createSeasonSprite(season, variant, frame);
        frame += 1;

        if (frame >= frameCount) {
          frame = 0;
          variant += 1;
        }

        if (performance.now() - batchStartedAt >= timeBudgetMs) break;
      }

      if (variant >= definition.variantCount) {
        seasonFrameMatrixCache.set(season, frameMatrix);
        resolve();
        return;
      }

      window.setTimeout(runBatch, 0);
    };

    runBatch();
  });

  seasonWarmupCache.set(season, warmup);
  return warmup;
}

// Retained for all static seasonal artwork and for callers that only need one
// representative frame from each variant.
export function seasonSprites(season: Season) {
  const cached = seasonVariantCache.get(season);
  if (cached) return cached;

  const definition = SEASONAL_SHOWERS[season];
  const sprites = Array.from({ length: definition.variantCount }, (_, index) =>
    createSeasonSprite(season, index, 0),
  );

  seasonVariantCache.set(season, sprites);
  return sprites;
}
