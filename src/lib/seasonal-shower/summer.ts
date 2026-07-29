import type { SeasonDefinition } from './types';

const TAU = Math.PI * 2;
const BEACH_BALL_RADIUS = 61;
const BEACH_BALL_SURFACE_SIZE = 132;
const BEACH_BALL_FRAME_COUNT = 64;
const BEACH_BALL_PANELS = [
  '#ef476f',
  '#ffd166',
  '#06d6a0',
  '#118ab2',
  '#ffffff',
] as const;

interface Vector3 {
  x: number;
  y: number;
  z: number;
}

type Matrix3 = readonly [
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
];

function seededUnit(value: number) {
  const sine = Math.sin(value * 12.9898 + 78.233) * 43758.5453;
  return sine - Math.floor(sine);
}

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(maximum, Math.max(minimum, value));
}

function normalize(vector: Vector3): Vector3 {
  const length = Math.max(0.0001, Math.hypot(vector.x, vector.y, vector.z));
  return {
    x: vector.x / length,
    y: vector.y / length,
    z: vector.z / length,
  };
}

function multiply(left: Matrix3, right: Matrix3): Matrix3 {
  return [
    left[0] * right[0] + left[1] * right[3] + left[2] * right[6],
    left[0] * right[1] + left[1] * right[4] + left[2] * right[7],
    left[0] * right[2] + left[1] * right[5] + left[2] * right[8],
    left[3] * right[0] + left[4] * right[3] + left[5] * right[6],
    left[3] * right[1] + left[4] * right[4] + left[5] * right[7],
    left[3] * right[2] + left[4] * right[5] + left[5] * right[8],
    left[6] * right[0] + left[7] * right[3] + left[8] * right[6],
    left[6] * right[1] + left[7] * right[4] + left[8] * right[7],
    left[6] * right[2] + left[7] * right[5] + left[8] * right[8],
  ];
}

function rotationX(angle: number): Matrix3 {
  const cosine = Math.cos(angle);
  const sine = Math.sin(angle);
  return [1, 0, 0, 0, cosine, -sine, 0, sine, cosine];
}

function rotationY(angle: number): Matrix3 {
  const cosine = Math.cos(angle);
  const sine = Math.sin(angle);
  return [cosine, 0, sine, 0, 1, 0, -sine, 0, cosine];
}

function rotationZ(angle: number): Matrix3 {
  const cosine = Math.cos(angle);
  const sine = Math.sin(angle);
  return [cosine, -sine, 0, sine, cosine, 0, 0, 0, 1];
}

function axisAngleRotation(axis: Vector3, angle: number): Matrix3 {
  const normalizedAxis = normalize(axis);
  const { x, y, z } = normalizedAxis;
  const cosine = Math.cos(angle);
  const sine = Math.sin(angle);
  const oneMinusCosine = 1 - cosine;

  return [
    cosine + x * x * oneMinusCosine,
    x * y * oneMinusCosine - z * sine,
    x * z * oneMinusCosine + y * sine,
    y * x * oneMinusCosine + z * sine,
    cosine + y * y * oneMinusCosine,
    y * z * oneMinusCosine - x * sine,
    z * x * oneMinusCosine - y * sine,
    z * y * oneMinusCosine + x * sine,
    cosine + z * z * oneMinusCosine,
  ];
}

function parseHex(hex: string) {
  const value = Number.parseInt(hex.slice(1), 16);
  return {
    red: (value >> 16) & 255,
    green: (value >> 8) & 255,
    blue: value & 255,
  };
}

const PANEL_RGB = BEACH_BALL_PANELS.map(parseHex);
const LIGHT = normalize({ x: -0.48, y: -0.55, z: 0.78 });
const HALF_VECTOR = normalize({ x: LIGHT.x, y: LIGHT.y, z: LIGHT.z + 1 });
const SURFACE_PIXEL_COUNT = BEACH_BALL_SURFACE_SIZE * BEACH_BALL_SURFACE_SIZE;

// Geometry, lighting, antialiasing, and alpha do not change when the texture
// rotates. Precomputing them once removes millions of square roots and powers
// from the animated-frame warm-up.
const SURFACE_X = new Float32Array(SURFACE_PIXEL_COUNT);
const SURFACE_Y = new Float32Array(SURFACE_PIXEL_COUNT);
const SURFACE_Z = new Float32Array(SURFACE_PIXEL_COUNT);
const SURFACE_SHADE = new Float32Array(SURFACE_PIXEL_COUNT);
const SURFACE_HIGHLIGHT = new Float32Array(SURFACE_PIXEL_COUNT);
const SURFACE_ALPHA = new Uint8ClampedArray(SURFACE_PIXEL_COUNT);

function buildSurfaceLookup() {
  const center = BEACH_BALL_SURFACE_SIZE / 2;

  for (let pixelY = 0; pixelY < BEACH_BALL_SURFACE_SIZE; pixelY += 1) {
    const screenY = (pixelY + 0.5 - center) / BEACH_BALL_RADIUS;

    for (let pixelX = 0; pixelX < BEACH_BALL_SURFACE_SIZE; pixelX += 1) {
      const screenX = (pixelX + 0.5 - center) / BEACH_BALL_RADIUS;
      const radialSquared = screenX * screenX + screenY * screenY;
      if (radialSquared > 1) continue;

      const screenZ = Math.sqrt(Math.max(0, 1 - radialSquared));
      const diffuse = Math.max(
        0,
        screenX * LIGHT.x + screenY * LIGHT.y + screenZ * LIGHT.z,
      );
      const specular = Math.pow(
        Math.max(
          0,
          screenX * HALF_VECTOR.x +
            screenY * HALF_VECTOR.y +
            screenZ * HALF_VECTOR.z,
        ),
        34,
      );
      const sphericalEdge = Math.pow(screenZ, 0.42);
      const edgeDistance = (1 - Math.sqrt(radialSquared)) * BEACH_BALL_RADIUS;
      const index = pixelY * BEACH_BALL_SURFACE_SIZE + pixelX;

      SURFACE_X[index] = screenX;
      SURFACE_Y[index] = screenY;
      SURFACE_Z[index] = screenZ;
      SURFACE_SHADE[index] = 0.56 + diffuse * 0.3 + sphericalEdge * 0.14;
      SURFACE_HIGHLIGHT[index] = specular * 112;
      SURFACE_ALPHA[index] = clamp(edgeDistance + 0.55, 0, 1) * 255;
    }
  }
}

buildSurfaceLookup();

function ballRotation(variant: number, animationFrame: number) {
  const initialTiltX = (seededUnit(variant + 2) - 0.5) * 1.45;
  const initialTiltY = (seededUnit(variant + 7) - 0.5) * 1.15;
  const initialTurn = seededUnit(variant + 13) * TAU;
  const axisAngle = seededUnit(variant + 19) * TAU;
  const axis = normalize({
    x: Math.cos(axisAngle),
    y: Math.sin(axisAngle),
    z: (seededUnit(variant + 29) - 0.5) * 0.42,
  });
  const phaseOffset = seededUnit(variant + 37) * TAU;
  const animatedAngle =
    phaseOffset + (animationFrame / BEACH_BALL_FRAME_COUNT) * TAU;

  const initial = multiply(
    rotationZ(initialTurn),
    multiply(rotationX(initialTiltX), rotationY(initialTiltY)),
  );

  return multiply(axisAngleRotation(axis, animatedAngle), initial);
}

function renderBallSurface(variant: number, animationFrame: number) {
  const surface = document.createElement('canvas');
  surface.width = BEACH_BALL_SURFACE_SIZE;
  surface.height = BEACH_BALL_SURFACE_SIZE;
  const surfaceContext = surface.getContext('2d');
  if (!surfaceContext) return surface;

  const image = surfaceContext.createImageData(
    BEACH_BALL_SURFACE_SIZE,
    BEACH_BALL_SURFACE_SIZE,
  );
  const pixels = image.data;
  const rotation = ballRotation(variant, animationFrame);

  for (let pixelIndex = 0; pixelIndex < SURFACE_PIXEL_COUNT; pixelIndex += 1) {
    const alpha = SURFACE_ALPHA[pixelIndex]!;
    if (alpha === 0) continue;

    const screenX = SURFACE_X[pixelIndex]!;
    const screenY = SURFACE_Y[pixelIndex]!;
    const screenZ = SURFACE_Z[pixelIndex]!;

    // Multiplying by the transpose converts the visible point back into the
    // ball's rotating object space. The panel texture therefore moves over
    // the sphere instead of the entire flat sprite simply spinning in place.
    const objectX =
      rotation[0] * screenX + rotation[3] * screenY + rotation[6] * screenZ;
    const objectZ =
      rotation[2] * screenX + rotation[5] * screenY + rotation[8] * screenZ;

    const longitude = Math.atan2(objectZ, objectX);
    const panelPosition = ((longitude + Math.PI) / TAU) * BEACH_BALL_PANELS.length;
    const panelIndex =
      ((Math.floor(panelPosition) % BEACH_BALL_PANELS.length) +
        BEACH_BALL_PANELS.length) %
      BEACH_BALL_PANELS.length;
    const panelFraction = panelPosition - Math.floor(panelPosition);
    const seamDistance = Math.min(panelFraction, 1 - panelFraction);
    const panelColor = PANEL_RGB[panelIndex]!;
    let shade = SURFACE_SHADE[pixelIndex]!;

    if (seamDistance < 0.022) {
      shade *= 0.76 + (seamDistance / 0.022) * 0.24;
    }

    const highlight = SURFACE_HIGHLIGHT[pixelIndex]!;
    const offset = pixelIndex * 4;

    pixels[offset] = clamp(panelColor.red * shade + highlight, 0, 255);
    pixels[offset + 1] = clamp(panelColor.green * shade + highlight, 0, 255);
    pixels[offset + 2] = clamp(panelColor.blue * shade + highlight, 0, 255);
    pixels[offset + 3] = alpha;
  }

  surfaceContext.putImageData(image, 0, 0);
  return surface;
}

export function drawBeachBall(
  context: CanvasRenderingContext2D,
  variant: number,
  animationFrame = 0,
) {
  const radius = BEACH_BALL_RADIUS;

  context.save();

  // A restrained shadow keeps the ball dimensional without changing the
  // simple graphic language of the original summer artwork.
  context.save();
  context.translate(2.5, 5.5);
  context.scale(1, 0.9);
  const shadow = context.createRadialGradient(0, 0, radius * 0.28, 0, 0, radius * 1.08);
  shadow.addColorStop(0, 'rgba(5, 20, 36, 0.2)');
  shadow.addColorStop(0.72, 'rgba(5, 20, 36, 0.09)');
  shadow.addColorStop(1, 'rgba(5, 20, 36, 0)');
  context.fillStyle = shadow;
  context.beginPath();
  context.arc(0, 0, radius * 1.08, 0, TAU);
  context.fill();
  context.restore();

  const surface = renderBallSurface(variant, animationFrame);
  context.drawImage(
    surface,
    -BEACH_BALL_SURFACE_SIZE / 2,
    -BEACH_BALL_SURFACE_SIZE / 2,
  );

  context.strokeStyle = 'rgba(5, 23, 40, 0.3)';
  context.lineWidth = 2.1;
  context.beginPath();
  context.arc(0, 0, radius - 1.1, 0, TAU);
  context.stroke();

  context.strokeStyle = 'rgba(255, 255, 255, 0.26)';
  context.lineWidth = 0.85;
  context.beginPath();
  context.arc(-1.1, -1.3, radius - 2.5, Math.PI * 1.08, Math.PI * 1.72);
  context.stroke();

  context.restore();
}

export const summerShower: SeasonDefinition = {
  variantCount: 8,
  animationFrames: BEACH_BALL_FRAME_COUNT,
  spriteSize: 144,
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
