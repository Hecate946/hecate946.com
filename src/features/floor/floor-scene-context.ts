import type { Group, Object3D, PerspectiveCamera, Scene } from 'three';

/** Context key used by declarative 3D floor-object components. */
export const FLOOR_SCENE_CONTEXT = Symbol('floor-scene');

export interface FloorSurface {
  y: number;
  centerX: number;
  centerZ: number;
  width: number;
  depth: number;
  minX: number;
  maxX: number;
  minZ: number;
  maxZ: number;
}

/**
 * Small renderer surface exposed to descendants of FloorScene.
 *
 * Coordinate contract:
 * - X matches the DOM wall camera (1 world unit = 1 CSS pixel at the seam).
 * - Y is height above the floor.
 * - Z starts at the wall (0) and increases toward the viewer.
 * - Checker tiles are true 84 x 84 world-unit squares.
 */
export interface FloorSceneContext {
  addObject(object: Object3D): () => void;
  getScene(): Scene | null;
  getObjectRoot(): Group | null;
  getCamera(): PerspectiveCamera | null;
  getHostElement(): HTMLElement | null;
  getCameraX(): number;
  /** Exact world-space checkerboard plane currently rendered by FloorScene. */
  getFloorSurface(): FloorSurface | null;
  requestRender(): void;
}
