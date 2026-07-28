import { SEASONAL_SHOWERS } from './seasons';
import type { Season } from './types';

export const SEASON_SPRITE_SIZE = 180;

const spriteCache = new Map<Season, HTMLCanvasElement[]>();

export function createSeasonSprite(season: Season, variant: number) {
  const sprite = document.createElement('canvas');
  sprite.width = SEASON_SPRITE_SIZE;
  sprite.height = SEASON_SPRITE_SIZE;

  const context = sprite.getContext('2d');
  if (!context) return sprite;

  context.translate(SEASON_SPRITE_SIZE / 2, SEASON_SPRITE_SIZE / 2);
  context.lineCap = 'round';
  context.lineJoin = 'round';
  SEASONAL_SHOWERS[season].drawSprite(context, variant);

  return sprite;
}

export function seasonSprites(season: Season) {
  const cached = spriteCache.get(season);
  if (cached) return cached;

  const definition = SEASONAL_SHOWERS[season];
  const sprites = Array.from({ length: definition.variantCount }, (_, index) =>
    createSeasonSprite(season, index),
  );

  spriteCache.set(season, sprites);
  return sprites;
}
