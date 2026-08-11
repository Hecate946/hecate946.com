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
  /** Keep the secondary description visible instead of revealing it only on hover/focus. */
  descriptionAlwaysVisible?: boolean;
  href?: string;
  external?: boolean;
  imageSrc?: string;
  icon?: NetworkIcon;
  accent?: string;
  radius?: number;
  anchor?: NetworkAnchor;
  featured?: boolean;
  /** Marks the route currently being viewed. */
  current?: boolean;
};

export type NetworkLink = {
  source: string;
  target: string;
  kind?: 'primary' | 'secondary';
  distance?: number;
  strength?: number;
  curve?: number;
  /** Draw an arrow toward target. */
  directed?: boolean;
  /** Normalized 0–1 visual weight, used for weighted directed edges. */
  weight?: number;
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
  /** Minimum linked-node separation as a fraction of the link's resting distance. */
  linkCompressionRatio?: number;
  /** Strength of the one-way spring that resists links becoming too short. */
  linkCompressionStrength?: number;
  /** Constraint passes per simulation tick for compressed links. */
  linkCompressionIterations?: number;
  /** Maximum linked-node separation as a fraction of the resting distance. */
  linkStretchRatio?: number;
  /** Strength of the one-way spring that resists links becoming too long. */
  linkStretchStrength?: number;
  /** Constraint passes per simulation tick for stretched links. */
  linkStretchIterations?: number;
  velocityDecay?: number;
  alphaDecay?: number;
  dragAlphaTarget?: number;
  entranceRadius?: number;
};
