import type { SeasonDefinition } from './types';

export function drawSpringFlower(
  context: CanvasRenderingContext2D,
  variant: number,
) {
  const petalCount = 5;
  const rotation = (variant * Math.PI) / 20;
  const petalFill = ['#ec9eb1', '#ed9fb3', '#eba0b4', '#eea4b8'][variant % 4]!;
  const petalHighlight = ['#f3bccb', '#f2b7c8', '#f4bfcd', '#f1b8c8'][variant % 4]!;
  const stamenPink = '#f989a7';
  const innerFill = '#f2d8e1';

  context.save();
  context.rotate(rotation);
  context.shadowColor = 'rgba(124, 67, 90, 0.12)';
  context.shadowBlur = 6;
  context.shadowOffsetY = 3;

  for (let index = 0; index < petalCount; index += 1) {
    context.save();
    context.rotate((index / petalCount) * Math.PI * 2);
    context.fillStyle = petalFill;
    context.beginPath();
    context.moveTo(0, -10);
    context.bezierCurveTo(-13, -15, -35, -31, -36, -45);
    context.bezierCurveTo(-37, -57, -23, -64, -9, -57);
    context.bezierCurveTo(-2, -53, -0.5, -44, 0, -39);
    context.bezierCurveTo(0.5, -44, 2, -53, 9, -57);
    context.bezierCurveTo(23, -64, 37, -57, 36, -45);
    context.bezierCurveTo(35, -31, 13, -15, 0, -10);
    context.closePath();
    context.fill();

    context.fillStyle = petalHighlight;
    context.beginPath();
    context.moveTo(-2, -18);
    context.bezierCurveTo(-14, -23, -24, -31, -24, -42);
    context.bezierCurveTo(-24, -49, -15, -52, -9, -47);
    context.bezierCurveTo(-4, -43, -2, -30, -2, -18);
    context.closePath();
    context.fill();
    context.restore();
  }

  context.strokeStyle = stamenPink;
  context.lineWidth = 5;

  for (let index = 0; index < petalCount; index += 1) {
    const angle = -Math.PI / 2 + (index / petalCount) * Math.PI * 2;
    context.beginPath();
    context.moveTo(0, 2);
    context.lineTo(Math.cos(angle) * 24, Math.sin(angle) * 24 + 2);
    context.stroke();
  }

  for (let index = 0; index < petalCount; index += 1) {
    context.save();
    context.rotate((index / petalCount) * Math.PI * 2 + Math.PI / 10);
    context.fillStyle = innerFill;
    context.beginPath();
    context.moveTo(0, -1);
    context.bezierCurveTo(-6, -5, -13, -13, -10, -21);
    context.bezierCurveTo(-8, -26, -1.5, -24, 1, -18);
    context.bezierCurveTo(3.5, -24, 10, -26, 12, -21);
    context.bezierCurveTo(15, -13, 8, -5, 2, -1);
    context.bezierCurveTo(3, 7, -3, 7, 0, -1);
    context.closePath();
    context.fill();
    context.restore();
  }

  context.restore();
}

export const springShower: SeasonDefinition = {
  variantCount: 8,
  particleCount: { compact: 18, desktop: 28 },
  size: { minimum: 29, maximum: 52 },
  scale: 0.72,
  speed: { minimum: 42, maximum: 82 },
  drift: { minimum: -8, maximum: 8 },
  sway: { minimum: 15, maximum: 58 },
  swayRate: { minimum: 0.65, maximum: 1.35 },
  spin: { minimum: -0.72, maximum: 0.72 },
  flutterRate: { minimum: 1.2, maximum: 2.5 },
  opacity: { minimum: 0.84, maximum: 1 },
  flutter: true,
  drawSprite: drawSpringFlower,
};
