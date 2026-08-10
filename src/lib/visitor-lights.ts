export const VISITOR_LIGHT_CORE_CLOSE_PX = 4.4;
export const VISITOR_LIGHT_CORE_FAR_PX = 6.8;
export const VISITOR_LIGHT_GLOW_CLOSE_PX = 11.5;
export const VISITOR_LIGHT_GLOW_FAR_PX = 18.0;

export const VISITOR_LIGHT_DENSITY_CAP = 0.65;
export const VISITOR_LIGHT_DENSITY_RATE = 0.16;

export interface VisitorLightGradientStop {
  offset: number;
  opacity: number;
}

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(maximum, Math.max(minimum, value));
}

function smoothstep(edge0: number, edge1: number, value: number) {
  const t = clamp((value - edge0) / (edge1 - edge0), 0, 1);
  return t * t * (3 - 2 * t);
}

export function visitorLightDensityScale(count: number) {
  return (
    1 +
    Math.min(
      VISITOR_LIGHT_DENSITY_CAP,
      Math.log2(Math.max(1, count)) * VISITOR_LIGHT_DENSITY_RATE,
    )
  );
}

/**
 * Normalized apparent-distance value shared conceptually by both renderers.
 * 1 = far/world view, 0 = close/detail view.
 *
 * The flat map zoom itself is multiplicative, so use logarithmic progress to
 * make 1→2→4→8× change the lights at perceptually even intervals.
 */
export function visitorLightMapDistanceT(
  zoom: number,
  minimumZoom: number,
  maximumZoom: number,
) {
  const safeMinimum = Math.max(0.0001, minimumZoom);
  const safeMaximum = Math.max(safeMinimum + 0.0001, maximumZoom);
  const clampedZoom = clamp(zoom, safeMinimum, safeMaximum);
  const closeProgress =
    Math.log(clampedZoom / safeMinimum) /
    Math.log(safeMaximum / safeMinimum);
  return 1 - clamp(closeProgress, 0, 1);
}

export function visitorLightSizePx(
  closePx: number,
  farPx: number,
  distanceT: number,
  count: number,
) {
  const apparentPx = closePx + (farPx - closePx) * clamp(distanceT, 0, 1);
  return apparentPx * visitorLightDensityScale(count);
}

// These sample the exact alpha equations used by the Three.js point shaders.
// SVG radial gradients interpolate between the samples, making the 2D light
// visually indistinguishable from the 3D light while still remaining native SVG.
function visitorLightCoreAlpha(radius: number) {
  const core = 1 - smoothstep(0.45, 0.78, radius);
  const feather = 1 - smoothstep(0.72, 1.0, radius);
  return Math.max(core, feather * 0.78);
}

function visitorLightGlowAlpha(radius: number) {
  const glow = Math.exp(-radius * radius * 4.6);
  const edge = 1 - smoothstep(0.72, 1.0, radius);
  return glow * edge * 0.3;
}

function makeStops(alphaAtRadius: (radius: number) => number) {
  const steps = 20;
  return Array.from({ length: steps + 1 }, (_, index) => {
    const radius = index / steps;
    return {
      offset: radius * 100,
      opacity: clamp(alphaAtRadius(radius), 0, 1),
    } satisfies VisitorLightGradientStop;
  });
}

export const VISITOR_LIGHT_CORE_STOPS = makeStops(visitorLightCoreAlpha);
export const VISITOR_LIGHT_GLOW_STOPS = makeStops(visitorLightGlowAlpha);
