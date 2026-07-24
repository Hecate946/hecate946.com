import type { SeasonDefinition } from './types';

function traceMapleLeaf(context: CanvasRenderingContext2D, variant: number) {
  const asymmetry = ((variant % 5) - 2) * 0.9;
  const narrow = variant % 3 === 0 ? 0.94 : variant % 3 === 1 ? 1 : 1.04;

  context.save();
  context.scale(narrow, 1);
  context.beginPath();
  context.moveTo(-2, 47);

  // Left lower lobe and serrated shoulder.
  context.lineTo(-18, 39);
  context.lineTo(-34, 55);
  context.lineTo(-31, 31);
  context.lineTo(-57, 37);
  context.lineTo(-46, 18);
  context.lineTo(-70, 8 + asymmetry);
  context.lineTo(-50, -4);
  context.lineTo(-66, -29 + asymmetry);
  context.lineTo(-38, -23);
  context.lineTo(-43, -51);
  context.lineTo(-20, -36);
  context.lineTo(-11, -69);
  context.lineTo(1, -45);

  // Tall center lobe and right side, deliberately a little asymmetric.
  context.lineTo(14, -66);
  context.lineTo(18, -36);
  context.lineTo(45, -50 - asymmetry);
  context.lineTo(38, -22);
  context.lineTo(67, -17);
  context.lineTo(49, 0);
  context.lineTo(71, 11 - asymmetry);
  context.lineTo(48, 21);
  context.lineTo(63, 36);
  context.lineTo(36, 38);
  context.lineTo(41, 61);
  context.lineTo(17, 49);
  context.lineTo(7, 69);
  context.lineTo(0, 47);
  context.closePath();
  context.restore();
}

export function drawAutumnLeaf(context: CanvasRenderingContext2D, variant: number) {
  const palettes = [
    ['#ffb347', '#f06a32', '#a72835'],
    ['#ff9d3f', '#e95731', '#86243a'],
    ['#ffc05a', '#ed7230', '#b12d2e'],
    ['#f8923e', '#d94b33', '#72233b'],
    ['#ffad45', '#ef5a2d', '#93262f'],
    ['#ffbd55', '#df6330', '#7e2937'],
  ] as const;
  const [light, middle, dark] = palettes[variant % palettes.length]!;
  const tilt = ((variant % 7) - 3) * 0.025;

  context.save();
  context.rotate(tilt);
  context.shadowColor = 'rgba(74, 24, 27, 0.3)';
  context.shadowBlur = 9;
  context.shadowOffsetX = 1;
  context.shadowOffsetY = 5;

  traceMapleLeaf(context, variant);
  const baseGradient = context.createLinearGradient(-58, -65, 57, 64);
  baseGradient.addColorStop(0, light);
  baseGradient.addColorStop(0.43, middle);
  baseGradient.addColorStop(1, dark);
  context.fillStyle = baseGradient;
  context.fill();

  context.shadowColor = 'transparent';
  traceMapleLeaf(context, variant);
  context.clip();

  // A warm translucent wash makes the leaf feel less like flat vector art.
  const sunWash = context.createRadialGradient(-30, -34, 2, -22, -25, 74);
  sunWash.addColorStop(0, 'rgba(255, 238, 154, 0.42)');
  sunWash.addColorStop(0.45, 'rgba(255, 164, 69, 0.12)');
  sunWash.addColorStop(1, 'rgba(255, 255, 255, 0)');
  context.fillStyle = sunWash;
  context.fillRect(-80, -80, 160, 160);

  const lowerShade = context.createLinearGradient(-5, 6, 18, 72);
  lowerShade.addColorStop(0, 'rgba(101, 27, 35, 0)');
  lowerShade.addColorStop(1, 'rgba(82, 20, 34, 0.28)');
  context.fillStyle = lowerShade;
  context.fillRect(-80, -10, 160, 100);

  // Small deterministic blemishes add organic variation without animating noise.
  for (let index = 0; index < 9; index += 1) {
    const angle = variant * 1.81 + index * 2.37;
    const radius = 9 + ((index * 13 + variant * 7) % 43);
    const x = Math.cos(angle) * radius * 0.86;
    const y = Math.sin(angle * 0.91) * radius * 0.72;
    context.fillStyle = index % 3 === 0 ? 'rgba(91, 24, 32, 0.10)' : 'rgba(255, 203, 91, 0.10)';
    context.beginPath();
    context.ellipse(x, y, 1.6 + (index % 3) * 0.8, 0.8 + (index % 2) * 0.55, angle, 0, Math.PI * 2);
    context.fill();
  }

  context.restore();

  // Crisp but subdued silhouette.
  context.save();
  context.rotate(tilt);
  traceMapleLeaf(context, variant);
  context.strokeStyle = 'rgba(98, 30, 35, 0.42)';
  context.lineWidth = 1.35;
  context.stroke();

  const veinColor = 'rgba(113, 42, 34, 0.58)';
  const fineVein = 'rgba(124, 50, 37, 0.38)';
  context.strokeStyle = veinColor;
  context.lineWidth = 3.2;
  context.beginPath();
  context.moveTo(-2, 51);
  context.quadraticCurveTo(-1, 8, 1, -56);
  context.stroke();

  const primaryVeins: Array<[number, number, number, number, number, number]> = [
    [-1, 10, -16, -10, -55, -27],
    [-1, 17, -21, 20, -55, 33],
    [0, 2, 18, -13, 51, -42],
    [0, 15, 22, 19, 57, 33],
    [0, -7, -7, -29, -11, -61],
    [1, -8, 8, -29, 14, -59],
  ];

  for (const [sx, sy, cx, cy, ex, ey] of primaryVeins) {
    context.beginPath();
    context.moveTo(sx, sy);
    context.quadraticCurveTo(cx, cy, ex, ey);
    context.stroke();
  }

  context.strokeStyle = fineVein;
  context.lineWidth = 1.35;
  const secondaryVeins: Array<[number, number, number, number]> = [
    [-13, -5, -33, -12],
    [-22, -15, -42, -20],
    [-16, 20, -37, 25],
    [-27, 27, -47, 32],
    [14, -7, 34, -18],
    [25, -22, 44, -32],
    [17, 20, 38, 25],
    [28, 27, 49, 32],
    [-4, -27, -22, -37],
    [6, -28, 25, -39],
  ];
  for (const [sx, sy, ex, ey] of secondaryVeins) {
    context.beginPath();
    context.moveTo(sx, sy);
    context.lineTo(ex, ey);
    context.stroke();
  }

  const stemGradient = context.createLinearGradient(-2, 43, -19, 79);
  stemGradient.addColorStop(0, 'rgba(132, 48, 31, 0.86)');
  stemGradient.addColorStop(1, 'rgba(82, 29, 29, 0.98)');
  context.strokeStyle = stemGradient;
  context.lineWidth = 5;
  context.beginPath();
  context.moveTo(-2, 43);
  context.quadraticCurveTo(-7, 60, -21, 77);
  context.stroke();

  context.strokeStyle = 'rgba(255, 170, 78, 0.18)';
  context.lineWidth = 1.2;
  context.beginPath();
  context.moveTo(-3, 45);
  context.quadraticCurveTo(-8, 61, -20, 75);
  context.stroke();
  context.restore();
}

export const autumnShower: SeasonDefinition = {
  variantCount: 12,
  particleCount: { compact: 18, desktop: 28 },
  size: { minimum: 29, maximum: 52 },
  scale: 1,
  speed: { minimum: 34, maximum: 66 },
  drift: { minimum: -14, maximum: 14 },
  sway: { minimum: 28, maximum: 72 },
  swayRate: { minimum: 0.52, maximum: 1.08 },
  spin: { minimum: -0.82, maximum: 0.82 },
  flutterRate: { minimum: 1.45, maximum: 3.2 },
  opacity: { minimum: 0.84, maximum: 1 },
  flutter: true,
  drawSprite: drawAutumnLeaf,
};
