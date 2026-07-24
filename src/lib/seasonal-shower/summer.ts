import type { SeasonDefinition } from './types';

export function drawBeachBall(context: CanvasRenderingContext2D, variant: number) {
  const panels = ['#ef476f', '#ffd166', '#06d6a0', '#118ab2', '#ffffff'] as const;
  const radius = 61;
  const hubX = -8;
  const hubY = -10;

  context.save();
  context.rotate((variant * Math.PI) / 20);
  context.shadowColor = 'rgba(8, 26, 45, 0.3)';
  context.shadowBlur = 10;
  context.shadowOffsetY = 6;

  context.beginPath();
  context.arc(0, 0, radius, 0, Math.PI * 2);
  context.clip();

  for (let index = 0; index < panels.length; index += 1) {
    const startAngle = -Math.PI / 2 + (index / panels.length) * Math.PI * 2;
    const endAngle = -Math.PI / 2 + ((index + 1) / panels.length) * Math.PI * 2;
    context.fillStyle = panels[index]!;
    context.beginPath();
    context.moveTo(hubX, hubY);
    context.bezierCurveTo(
      hubX + Math.cos(startAngle) * radius * 0.22,
      hubY + Math.sin(startAngle) * radius * 0.2,
      Math.cos(startAngle) * radius * 0.7,
      Math.sin(startAngle) * radius * 0.7,
      Math.cos(startAngle) * radius,
      Math.sin(startAngle) * radius,
    );
    context.arc(0, 0, radius, startAngle, endAngle);
    context.bezierCurveTo(
      Math.cos(endAngle) * radius * 0.7,
      Math.sin(endAngle) * radius * 0.7,
      hubX + Math.cos(endAngle) * radius * 0.22,
      hubY + Math.sin(endAngle) * radius * 0.2,
      hubX,
      hubY,
    );
    context.closePath();
    context.fill();
  }

  const volume = context.createRadialGradient(-24, -28, 5, 8, 12, radius * 1.12);
  volume.addColorStop(0, 'rgba(255,255,255,0.58)');
  volume.addColorStop(0.38, 'rgba(255,255,255,0.08)');
  volume.addColorStop(0.72, 'rgba(12,35,58,0.05)');
  volume.addColorStop(1, 'rgba(5,18,34,0.42)');
  context.fillStyle = volume;
  context.beginPath();
  context.arc(0, 0, radius, 0, Math.PI * 2);
  context.fill();

  const highlight = context.createRadialGradient(-31, -35, 0, -29, -33, 32);
  highlight.addColorStop(0, 'rgba(255,255,255,0.95)');
  highlight.addColorStop(0.28, 'rgba(255,255,255,0.46)');
  highlight.addColorStop(1, 'rgba(255,255,255,0)');
  context.fillStyle = highlight;
  context.beginPath();
  context.arc(0, 0, radius, 0, Math.PI * 2);
  context.fill();

  context.strokeStyle = 'rgba(5, 24, 42, 0.22)';
  context.lineWidth = 2.2;
  context.beginPath();
  context.arc(0, 0, radius - 1.2, 0, Math.PI * 2);
  context.stroke();

  context.fillStyle = '#ffffff';
  context.beginPath();
  context.arc(hubX, hubY, 9.5, 0, Math.PI * 2);
  context.fill();
  context.strokeStyle = 'rgba(15, 45, 70, 0.18)';
  context.lineWidth = 1.5;
  context.stroke();
  context.restore();
}

export const summerShower: SeasonDefinition = {
  variantCount: 12,
  particleCount: { compact: 14, desktop: 22 },
  size: { minimum: 29, maximum: 52 },
  scale: 0.82,
  speed: { minimum: 82, maximum: 132 },
  gravity: { minimum: 35, maximum: 60 },
  drift: { minimum: -38, maximum: 38 },
  sway: { minimum: 0, maximum: 0 },
  swayRate: { minimum: 0, maximum: 0 },
  spin: { minimum: -2.1, maximum: 2.1 },
  flutterRate: { minimum: 0, maximum: 0 },
  opacity: { minimum: 0.985, maximum: 1 },
  flutter: false,
  drawSprite: drawBeachBall,
};
