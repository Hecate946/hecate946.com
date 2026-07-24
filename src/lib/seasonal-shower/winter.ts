import type { SeasonDefinition } from './types';

export function drawSnowflake(
  context: CanvasRenderingContext2D,
  variant: number,
) {
  const branches = 6;
  const length = 62;
  const branchCount = 2 + (variant % 3);

  context.save();
  context.rotate((variant * Math.PI) / 24);
  context.shadowColor = 'rgba(90, 165, 220, 0.6)';
  context.shadowBlur = 7;
  context.strokeStyle = 'rgba(165, 215, 245, 0.95)';
  context.lineWidth = 3.2;

  for (let index = 0; index < branches; index += 1) {
    context.save();
    context.rotate((index / branches) * Math.PI * 2);
    context.beginPath();
    context.moveTo(0, 0);
    context.lineTo(0, -length);
    context.stroke();

    for (let branch = 1; branch <= branchCount; branch += 1) {
      const y = -length * (0.28 + branch * 0.19);
      const branchLength = 12 + branch * 3 + (variant % 2) * 2;

      context.beginPath();
      context.moveTo(0, y);
      context.lineTo(-branchLength, y - branchLength * 0.72);
      context.moveTo(0, y);
      context.lineTo(branchLength, y - branchLength * 0.72);
      context.stroke();
    }

    context.restore();
  }

  context.fillStyle = 'rgba(238, 250, 255, 0.98)';
  context.beginPath();
  context.arc(0, 0, 5.5, 0, Math.PI * 2);
  context.fill();
  context.restore();
}

export const winterShower: SeasonDefinition = {
  variantCount: 8,
  particleCount: { compact: 22, desktop: 34 },
  size: { minimum: 22, maximum: 43 },
  scale: 1,
  speed: { minimum: 42, maximum: 82 },
  drift: { minimum: -8, maximum: 8 },
  sway: { minimum: 15, maximum: 58 },
  swayRate: { minimum: 0.65, maximum: 1.35 },
  spin: { minimum: -0.72, maximum: 0.72 },
  flutterRate: { minimum: 1.2, maximum: 2.5 },
  opacity: { minimum: 0.84, maximum: 1 },
  flutter: true,
  drawSprite: drawSnowflake,
};
