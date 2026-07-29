import type { SeasonDefinition } from './types';

type AutumnPalette = {
  edge: string;
  dark: string;
  middle: string;
  light: string;
  highlight: string;
  stem: string;
  vein: string;
  microVein: string;
};

const TAU = Math.PI * 2;
const AUTUMN_FRAME_COUNT = 64;

const palettes: readonly AutumnPalette[] = [
  {
    edge: '#861019',
    dark: '#b61f25',
    middle: '#ea4a36',
    light: '#ff6b4a',
    highlight: '#ff8a61',
    stem: '#7f1d20',
    vein: 'rgba(124, 24, 28, 0.82)',
    microVein: 'rgba(139, 34, 36, 0.24)',
  },
  {
    edge: '#8f1119',
    dark: '#be2025',
    middle: '#ef4c38',
    light: '#ff7150',
    highlight: '#ff9167',
    stem: '#851f21',
    vein: 'rgba(129, 27, 29, 0.82)',
    microVein: 'rgba(144, 37, 39, 0.24)',
  },
  {
    edge: '#90111b',
    dark: '#b92025',
    middle: '#eb4734',
    light: '#ff6948',
    highlight: '#ff8c61',
    stem: '#811e20',
    vein: 'rgba(126, 25, 27, 0.82)',
    microVein: 'rgba(141, 34, 37, 0.23)',
  },
  {
    edge: '#8a1018',
    dark: '#b21d24',
    middle: '#e84533',
    light: '#ff6f4f',
    highlight: '#ff8b60',
    stem: '#7b1c1f',
    vein: 'rgba(122, 24, 27, 0.82)',
    microVein: 'rgba(137, 33, 35, 0.22)',
  },
  {
    edge: '#94151f',
    dark: '#c2262a',
    middle: '#f1533b',
    light: '#ff7954',
    highlight: '#ff936a',
    stem: '#862326',
    vein: 'rgba(132, 31, 31, 0.82)',
    microVein: 'rgba(149, 41, 40, 0.24)',
  },
  {
    edge: '#86121a',
    dark: '#b81f26',
    middle: '#ee4d39',
    light: '#ff7453',
    highlight: '#ff9065',
    stem: '#7d1d20',
    vein: 'rgba(126, 26, 28, 0.82)',
    microVein: 'rgba(142, 36, 37, 0.23)',
  },
  {
    edge: '#8f131c',
    dark: '#bf2329',
    middle: '#f04f3b',
    light: '#ff7250',
    highlight: '#ff8f64',
    stem: '#842126',
    vein: 'rgba(130, 29, 31, 0.82)',
    microVein: 'rgba(147, 39, 40, 0.24)',
  },
  {
    edge: '#871018',
    dark: '#b71e24',
    middle: '#ea4735',
    light: '#ff6d4e',
    highlight: '#ff885d',
    stem: '#7b1b1e',
    vein: 'rgba(122, 25, 26, 0.82)',
    microVein: 'rgba(139, 35, 36, 0.23)',
  },
] as const;

function seededUnit(value: number) {
  const sine = Math.sin(value * 12.9898 + 78.233) * 43758.5453;
  return sine - Math.floor(sine);
}

function mix(a: number, b: number, amount: number) {
  return a + (b - a) * amount;
}

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(maximum, Math.max(minimum, value));
}

function parseHex(hex: string) {
  const value = Number.parseInt(hex.slice(1), 16);
  return {
    red: (value >> 16) & 255,
    green: (value >> 8) & 255,
    blue: value & 255,
  };
}

function rgbaFromHex(hex: string, alpha: number) {
  const { red, green, blue } = parseHex(hex);
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

function lightenHex(hex: string, amount: number) {
  const { red, green, blue } = parseHex(hex);
  const mixChannel = (channel: number) => Math.round(mix(channel, 255, amount));
  return `rgb(${mixChannel(red)}, ${mixChannel(green)}, ${mixChannel(blue)})`;
}

function darkenHex(hex: string, amount: number) {
  const { red, green, blue } = parseHex(hex);
  const mixChannel = (channel: number) => Math.round(mix(channel, 0, amount));
  return `rgb(${mixChannel(red)}, ${mixChannel(green)}, ${mixChannel(blue)})`;
}

function traceAutumnBlazeLeaf(context: CanvasRenderingContext2D, serration = 1) {
  const serr = serration * 0.7;
  context.beginPath();
  context.moveTo(0, 70);
  context.lineTo(-5, 53);
  context.lineTo(-10, 56 + serr * 0.45);
  context.lineTo(-12, 44);
  context.lineTo(-20, 50 + serr * 0.4);
  context.lineTo(-22, 35);
  context.lineTo(-31, 42 + serr * 0.34);
  context.lineTo(-31, 24);
  context.lineTo(-43, 32 + serr * 0.3);
  context.lineTo(-39, 14);
  context.lineTo(-53, 18 + serr * 0.25);
  context.lineTo(-45, 2);
  context.lineTo(-60, 4);
  context.lineTo(-48, -7);
  context.lineTo(-56, -18 + serr * 0.2);
  context.lineTo(-41, -16);
  context.lineTo(-42, -30);
  context.lineTo(-28, -24);
  context.lineTo(-29, -40 + serr * 0.2);
  context.lineTo(-16, -31);
  context.lineTo(-14, -52 + serr * 0.18);
  context.lineTo(-4, -38);
  context.lineTo(0, -68);
  context.lineTo(4, -38);
  context.lineTo(14, -52 + serr * 0.18);
  context.lineTo(16, -31);
  context.lineTo(29, -40 + serr * 0.2);
  context.lineTo(28, -24);
  context.lineTo(42, -30);
  context.lineTo(41, -16);
  context.lineTo(56, -18 + serr * 0.2);
  context.lineTo(48, -7);
  context.lineTo(60, 4);
  context.lineTo(45, 2);
  context.lineTo(53, 18 + serr * 0.25);
  context.lineTo(39, 14);
  context.lineTo(43, 32 + serr * 0.3);
  context.lineTo(31, 24);
  context.lineTo(31, 42 + serr * 0.34);
  context.lineTo(22, 35);
  context.lineTo(20, 50 + serr * 0.4);
  context.lineTo(12, 44);
  context.lineTo(10, 56 + serr * 0.45);
  context.lineTo(5, 53);
  context.closePath();
}

function drawMicroVeins(context: CanvasRenderingContext2D, palette: AutumnPalette) {
  const branches = [
    [-5, -6, -21, -18],
    [-10, 5, -26, 0],
    [-8, 14, -22, 19],
    [-6, 25, -18, 32],
    [5, -6, 21, -18],
    [10, 5, 26, 0],
    [8, 14, 22, 19],
    [6, 25, 18, 32],
    [-2, -22, -8, -34],
    [2, -22, 8, -34],
  ] as const;

  context.strokeStyle = palette.microVein;
  context.lineWidth = 0.7;
  context.lineCap = 'round';

  for (const [sx, sy, ex, ey] of branches) {
    context.beginPath();
    context.moveTo(sx, sy);
    context.quadraticCurveTo((sx + ex) * 0.56, (sy + ey) * 0.5, ex, ey);
    context.stroke();
  }
}

function drawMajorVeins(
  context: CanvasRenderingContext2D,
  phase: number,
  palette: AutumnPalette,
  widthScale: number,
) {
  const bend = Math.sin(phase * 1.05) * 2.4;

  context.strokeStyle = palette.vein;
  context.lineCap = 'round';
  context.lineJoin = 'round';
  context.lineWidth = 2.4;
  context.beginPath();
  context.moveTo(0, 71);
  context.quadraticCurveTo(bend * 0.44, 26, 0, -60);
  context.stroke();

  context.lineWidth = 1.35;
  const segments = [
    [0, 12, -42, -15],
    [0, 19, -42, 12],
    [0, 28, -28, 38],
    [0, 3, -17, -42],
    [0, 12, 42, -15],
    [0, 19, 42, 12],
    [0, 28, 28, 38],
    [0, 3, 17, -42],
  ] as const;

  for (const [sx, sy, ex, ey] of segments) {
    context.beginPath();
    context.moveTo(sx * widthScale * 0.9, sy);
    context.quadraticCurveTo(
      (sx + ex * 0.52) * widthScale + bend * 0.22,
      sy + (ey - sy) * 0.18,
      ex * widthScale,
      ey,
    );
    context.stroke();
  }
}

function drawSpeckleTexture(context: CanvasRenderingContext2D, variant: number) {
  context.save();
  context.globalAlpha = 0.08;
  for (let index = 0; index < 10; index += 1) {
    const x = (seededUnit(variant * 13 + index * 1.7) - 0.5) * 56;
    const y = (seededUnit(variant * 17 + index * 2.1) - 0.5) * 86;
    const radius = 0.8 + seededUnit(variant * 23 + index * 1.9) * 1.3;
    context.fillStyle = index % 3 === 0 ? 'rgba(255, 210, 160, 0.8)' : 'rgba(138, 30, 22, 0.7)';
    context.beginPath();
    context.arc(x, y, radius, 0, TAU);
    context.fill();
  }
  context.restore();
}

export function drawAutumnLeaf(
  context: CanvasRenderingContext2D,
  variant: number,
  animationFrame = 0,
) {
  const palette = palettes[variant % palettes.length]!;
  const framePhase = (animationFrame / AUTUMN_FRAME_COUNT) * TAU;
  const phaseOffset = seededUnit(variant + 5) * TAU;
  const phase = framePhase + phaseOffset;

  const yaw = Math.sin(phase) * 1.14;
  const pitch = Math.cos(phase * 1.24 + seededUnit(variant + 11) * TAU) * 0.36;
  const roll = Math.sin(phase * 0.7 + seededUnit(variant + 19) * TAU) * 0.16;
  const bend = Math.sin(phase * 1.38 + seededUnit(variant + 29) * TAU) * 5.6;
  const widthScale = 0.34 + Math.abs(Math.cos(yaw)) * 0.88;
  const heightScale = 0.9 + Math.cos(pitch) * 0.08;
  const skew = Math.sin(yaw) * 0.16;
  const lightBias = 0.3 + Math.cos(yaw) * 0.16 + Math.sin(pitch) * 0.06;
  const shadowOffsetX = Math.sin(yaw) * 6.5;
  const serration = 0.7 + seededUnit(variant + 37) * 1.4;

  context.save();
  context.rotate(roll + ((variant % 7) - 3) * 0.022);
  context.transform(widthScale, 0, skew, heightScale, 0, 0);

  context.save();
  context.translate(shadowOffsetX, 4.8);
  context.scale(1, 0.98);
  context.fillStyle = 'rgba(58, 11, 9, 0.19)';
  traceAutumnBlazeLeaf(context, serration);
  context.fill();
  context.restore();

  const fillGradient = context.createLinearGradient(-26, -65, 20, 78);
  fillGradient.addColorStop(0, lightenHex(palette.highlight, clamp(lightBias * 0.88, 0.08, 0.38)));
  fillGradient.addColorStop(0.22, lightenHex(palette.light, clamp(lightBias * 0.42, 0.04, 0.2)));
  fillGradient.addColorStop(0.55, palette.middle);
  fillGradient.addColorStop(1, darkenHex(palette.dark, 0.02));

  traceAutumnBlazeLeaf(context, serration);
  context.fillStyle = fillGradient;
  context.fill();

  const centerGlow = context.createRadialGradient(-4, -4, 6, 0, 0, 68);
  centerGlow.addColorStop(0, rgbaFromHex(palette.highlight, 0.28));
  centerGlow.addColorStop(0.48, rgbaFromHex(palette.light, 0.1));
  centerGlow.addColorStop(1, 'rgba(255, 255, 255, 0)');
  traceAutumnBlazeLeaf(context, serration);
  context.fillStyle = centerGlow;
  context.fill();

  context.strokeStyle = lightenHex(palette.edge, 0.05);
  context.lineWidth = 1.28;
  context.stroke();

  const rimShade = context.createLinearGradient(-58, -4, 60, 14);
  rimShade.addColorStop(0, 'rgba(95, 8, 10, 0.12)');
  rimShade.addColorStop(0.5, 'rgba(255, 255, 255, 0)');
  rimShade.addColorStop(1, 'rgba(77, 6, 6, 0.08)');
  traceAutumnBlazeLeaf(context, serration);
  context.fillStyle = rimShade;
  context.fill();

  drawMajorVeins(context, phase, palette, widthScale);
  drawMicroVeins(context, palette);
  drawSpeckleTexture(context, variant);

  context.strokeStyle = palette.stem;
  context.lineCap = 'round';
  context.lineWidth = 3.2;
  context.beginPath();
  context.moveTo(0, 71);
  context.quadraticCurveTo(bend * 0.2, 80, -2 + bend * 0.12, 95);
  context.stroke();

  context.restore();
}

export const autumnShower: SeasonDefinition = {
  variantCount: 8,
  animationFrames: AUTUMN_FRAME_COUNT,
  spriteSize: 220,
  particleCount: { compact: 420, desktop: 760 },
  size: { minimum: 13, maximum: 20 },
  scale: 0.92,
  speed: { minimum: 122, maximum: 178 },
  drift: { minimum: -9, maximum: 9 },
  sway: { minimum: 4, maximum: 16 },
  swayRate: { minimum: 0.5, maximum: 1.0 },
  spin: { minimum: -0.42, maximum: 0.42 },
  flutterRate: { minimum: 2.8, maximum: 4.8 },
  opacity: { minimum: 0.92, maximum: 1 },
  flutter: false,
  drawSprite: drawAutumnLeaf,
};
