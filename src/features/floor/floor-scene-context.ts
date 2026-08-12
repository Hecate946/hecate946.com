import type { Group, Object3D, Scene } from 'three';

/** Context key used by future declarative 3D floor-object components. */
export const FLOOR_SCENE_CONTEXT = Symbol('floor-scene');

/**
 * Small, renderer-agnostic surface exposed to descendants of FloorScene.
 * Objects can register before the WebGL scene has initialized; FloorScene queues
 * them and attaches them when its scene graph is ready.
 *
 * Coordinate contract:
 * - X is the same coordinate used by the DOM wall camera (1 world unit = 1
 *   CSS pixel at the wall/floor seam), so a 3D object can align to a painting.
 * - Y is height above the floor.
 * - Z starts at the wall (0) and increases toward the viewer.
 * - Checker tiles are true 84 x 84 world-unit squares.
 */
export interface FloorSceneContext {
  addObject(object: Object3D): () => void;
  getScene(): Scene | null;
  getObjectRoot(): Group | null;
  getCameraX(): number;
}
