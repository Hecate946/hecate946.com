/**
 * The entrance door's proportions, in model units.
 *
 * The mesh is authored by `blender/hecate946_door.py` and exported to
 * `public/models/hallway-door.glb`. Every value below mirrors a constant
 * in that script, so the two must be edited together.
 *
 * This module deliberately imports nothing. The homepage needs the door's
 * aspect ratio to size a DOM anchor on first paint, and three.js is loaded
 * off the critical path -- so the numbers live here rather than in
 * `hallway-door.ts`, which pulls in the renderer.
 *
 * The assembly is exactly 1.0 unit tall with its floor line at y = 0 and
 * its centre on x = 0, so `scale` is simply the door's on-screen height.
 */

/** Outer face of the pilasters, and the radius of the arch above them. */
export const DOOR_OUTER_HALF = 0.3116;

/** The base step, which is the widest point of the whole assembly. */
export const DOOR_BASE_HALF = 0.3214;

/** The structural opening the leaves fill; also the hinge x positions. */
export const DOOR_OPENING_HALF = 0.2479;

/** Height of the arch centre. The apex therefore lands at exactly 1.0. */
export const DOOR_SPRING_Z = 1 - DOOR_OUTER_HALF;

/** How deep the surrounding wall is, so the reveal has somewhere to go. */
export const DOOR_WALL_DEPTH = 0.058;

/**
 * Width over height for the whole assembly. `HomeWall` sizes its anchor
 * with this and `hallway-door.ts` builds to it; importing it in both
 * places is what stops the two from drifting apart, which is exactly what
 * happened when each file carried its own copy.
 */
export const DOOR_ASPECT = DOOR_BASE_HALF * 2;

export const DOOR_MODEL_PATH = '/models/hallway-door.glb';
