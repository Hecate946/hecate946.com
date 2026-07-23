export type NetworkIcon = {
  viewBox?: string;
  paths: string[];
};

export type NetworkAnchor = {
  /** Horizontal position normalized from 0 to 1. */
  x: number;
  /** Vertical position normalized from 0 to 1. */
  y: number;
};

export type NetworkNode = {
  id: string;
  label: string;
  description?: string;
  href?: string;
  external?: boolean;
  imageSrc?: string;
  icon?: NetworkIcon;
  accent?: string;
  radius?: number;
  anchor?: NetworkAnchor;
  featured?: boolean;
};

export type NetworkLink = {
  source: string;
  target: string;
  kind?: 'primary' | 'secondary';
  distance?: number;
  strength?: number;
  curve?: number;
};

export type ForceNetworkSettings = {
  /** Resting layout. `radial` places non-center nodes on a regular polygon. */
  layout?: 'anchored' | 'radial';
  /** Radius of a radial layout as a fraction of the canvas's shorter side. */
  radialRadius?: number;
  /** Starting angle in radians for radial layouts. -Math.PI / 2 starts at the top. */
  radialStartAngle?: number;
  chargeStrength?: number;
  centerChargeMultiplier?: number;
  anchorStrength?: number;
  centerAnchorStrength?: number;
  collisionPadding?: number;
  linkDistance?: number;
  linkStrength?: number;
  velocityDecay?: number;
  alphaDecay?: number;
  dragAlphaTarget?: number;
  entranceRadius?: number;
};
