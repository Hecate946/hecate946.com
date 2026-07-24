export type Season = 'spring' | 'summer' | 'autumn' | 'winter';

export interface Particle {
  season: Season;
  startX: number;
  x: number;
  y: number;
  size: number;
  speed: number;
  drift: number;
  sway: number;
  swayRate: number;
  phase: number;
  rotation: number;
  spin: number;
  flutterRate: number;
  delay: number;
  age: number;
  opacity: number;
  sprite: HTMLCanvasElement;
  velocityX: number;
  velocityY: number;
  gravity: number;
  bounceCount: number;
  maxBounces: number;
  fadeStartedAt: number | null;
  fadeDuration: number;
  expired: boolean;
}

export interface Range {
  minimum: number;
  maximum: number;
}

export interface SeasonDefinition {
  variantCount: number;
  particleCount: {
    compact: number;
    desktop: number;
  };
  size: Range;
  scale: number;
  speed: Range;
  gravity?: Range;
  drift: Range;
  sway: Range;
  swayRate: Range;
  spin: Range;
  flutterRate: Range;
  opacity: Range;
  flutter: boolean;
  drawSprite: (context: CanvasRenderingContext2D, variant: number) => void;
}
