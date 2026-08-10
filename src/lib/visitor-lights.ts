export const VISITOR_LIGHT_CLOSE_PX = 12.0;
export const VISITOR_LIGHT_FAR_PX = 16.0;

// Interaction is intentionally decoupled from the rendered light. A marker can
// stay visually restrained while still meeting a comfortable pointer target.
export const VISITOR_LIGHT_HIT_RADIUS_PX = 14.0;

// Coalesced visitors should read as a stronger concentration, not a bubble.
// Keep the size gain deliberately small so dense places do not cover neighbors.
export const VISITOR_LIGHT_DENSITY_CAP = 0.25;
export const VISITOR_LIGHT_DENSITY_RATE = 0.07;

// Shared navigation constants. Both the flat map and globe use these exact
// values so wheel zoom and the eased camera response feel identical.
export const VISITOR_VIEW_ZOOM_EASING = 0.13;
export const VISITOR_VIEW_WHEEL_RATE = 0.0012;
export const VISITOR_VIEW_WHEEL_DELTA_CAP = 240;

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
 * Normalized apparent-distance value for the flat map. 1 = far/world view and
 * 0 = close/detail view. Map scale is treated as the inverse of camera surface
 * distance, matching the globe's zoom model.
 */
export function visitorLightMapDistanceT(
  zoom: number,
  minimumZoom: number,
  maximumZoom: number,
) {
  const safeMinimum = Math.max(0.0001, minimumZoom);
  const safeMaximum = Math.max(safeMinimum + 0.0001, maximumZoom);
  const clampedZoom = clamp(zoom, safeMinimum, safeMaximum);
  const farDistance = 1 / safeMinimum;
  const closeDistance = 1 / safeMaximum;
  const currentDistance = 1 / clampedZoom;
  return clamp(
    (currentDistance - closeDistance) / (farDistance - closeDistance),
    0,
    1,
  );
}

export function visitorLightSizePx(distanceT: number, count: number) {
  const apparentPx =
    VISITOR_LIGHT_CLOSE_PX +
    (VISITOR_LIGHT_FAR_PX - VISITOR_LIGHT_CLOSE_PX) *
      clamp(distanceT, 0, 1);
  return apparentPx * visitorLightDensityScale(count);
}

// One continuous light profile: a hot center plus two progressively broader
// Gaussian tails, all the same hue. There are no independently-sized layers,
// so there are no visible concentric rings when the marker is enlarged.
export function visitorLightAlpha(radius: number) {
  const r = clamp(radius, 0, 1);
  const core = Math.exp(-r * r * 20.0) * 0.82;
  const glow = Math.exp(-r * r * 5.2) * 0.30;
  const tail = Math.exp(-r * r * 1.8) * 0.08;
  const edge = 1 - smoothstep(0.82, 1.0, r);
  return clamp((core + glow + tail) * edge, 0, 1);
}

function makeStops() {
  const steps = 32;
  return Array.from({ length: steps + 1 }, (_, index) => {
    const radius = index / steps;
    return {
      offset: radius * 100,
      opacity: visitorLightAlpha(radius),
    } satisfies VisitorLightGradientStop;
  });
}

export const VISITOR_LIGHT_STOPS = makeStops();
