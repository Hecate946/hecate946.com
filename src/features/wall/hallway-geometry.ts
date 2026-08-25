import { ExtrudeGeometry, Path, Shape } from 'three';

/**
 * A rectangular frame: an outer rectangle with a smaller one cut out of it.
 * Used for the door's panel moldings and for the paintings' frames, both of
 * which are just millwork with a bevel to catch a highlight.
 */
export function createFrameGeometry(
  width: number,
  height: number,
  border: number,
  depth: number,
  bevel = depth * 0.5,
) {
  const shape = new Shape();
  shape.moveTo(-width / 2, -height / 2);
  shape.lineTo(width / 2, -height / 2);
  shape.lineTo(width / 2, height / 2);
  shape.lineTo(-width / 2, height / 2);
  shape.closePath();

  const innerX = width / 2 - border;
  const innerY = height / 2 - border;
  const hole = new Path();
  hole.moveTo(-innerX, -innerY);
  hole.lineTo(innerX, -innerY);
  hole.lineTo(innerX, innerY);
  hole.lineTo(-innerX, innerY);
  hole.closePath();
  shape.holes.push(hole);

  return new ExtrudeGeometry(shape, {
    depth,
    bevelEnabled: bevel > 0,
    bevelSize: bevel,
    bevelThickness: bevel,
    bevelSegments: 2,
    curveSegments: 1,
  });
}
