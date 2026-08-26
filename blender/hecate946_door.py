"""
hecate946 entrance door -- procedural Blender build.

Every dimension below was measured off the reference render and
normalised so the assembly is exactly 1.0 unit tall, floor line at
z = 0, centred on x = 0, front face at y = 0 with the body receding
toward +y.

    blender --background --python hecate946_door.py
    # or paste into Blender's Text Editor and press Alt+P

Writes hallway-door.glb into the current working directory.

The module imports fine without Blender: build_parts() returns plain
(verts, faces) data so the geometry can be checked outside Blender.
Only main() touches bpy.

After glTF export (+Y up) the three.js axes come out as:
    x -> x      z -> y      y -> -z
so the door faces +z in three.js with its body at negative z, hinges
at x = -/+ OPENING_HALF, and total height exactly 1.0.
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# MEASURED CONSTANTS  (fractions of total assembly height)
#
# Traced from the reference png: H = 962.9 px, floor at y_px = 977,
# centre at x_px = 755.7. Source pixel values are noted per line.
# ---------------------------------------------------------------------------

# --- horizontal half-widths from the centre line
OUTER_HALF = 0.3116  # outer face of pilaster / arch        (x=456)
IMPOST_HALF = 0.3168  # impost + plinth blocks              (x=451)
BASE_HALF = 0.3214  # bottom step                           (x=446)
PILASTER_GROOVE = 0.2749  # reveal in the pilaster face     (x=491)
BEAD_OUT = 0.2718  # raised bead, outer edge                (x=494)
BEAD_IN = 0.2614  # raised bead, inner edge                 (x=504)
OPENING_HALF = 0.2479  # the structural opening             (x=517)

# --- vertical, above the floor line
SPRING_Z = 1.0 - OUTER_HALF  # 0.6884; measured 0.6893, snapped so the
#                              apex lands at exactly z = 1.0
TRANSOM_TOP = 0.7078  # top face of the transom bar         (y=295)
LEAF_TOP = 0.6874  # underside of the transom               (y=315)
LEAF_BOTTOM = 0.0914  # bottom of the leaves                (y=889)
IMPOST_BOTTOM = 0.6832  # underside of the impost blocks    (y=319)
IMPOST_TOP = 0.7092  # top of the impost blocks             (y=294)
BASE_STEP_1_Z = 0.1038  # pilaster shaft ends               (y=877)
BASE_STEP_2_Z = 0.0280  # second step                       (y=950)
THRESHOLD_STEP_Z = 0.0415  # threshold moulding across the opening (y=937)

# --- leaf panels, as offsets from the meeting stile at x = 0
PANEL_OUT_X = 0.1980  # outer edge of the moulding          (x=565)
PANEL_FIELD_X = 0.1804  # bevel meets the field             (x=582)
PANEL_FIELD_INNER_X = 0.0693  # field, inner side           (x=689)
PANEL_OUT_INNER_X = 0.0527  # moulding, inner side          (x=705)

UPPER_PANEL_TOP = 0.6417  # (y=359)
UPPER_PANEL_FIELD_TOP = 0.6261  # (y=374)
UPPER_PANEL_FIELD_BOTTOM = 0.3375  # (y=652)
UPPER_PANEL_BOTTOM = 0.3209  # (y=668)
LOWER_PANEL_TOP = 0.2762  # (y=711)
LOWER_PANEL_FIELD_TOP = 0.2575  # (y=729)
LOWER_PANEL_FIELD_BOTTOM = 0.1277  # mirrored from the top rail
LOWER_PANEL_BOTTOM = 0.1090  # (y=872)

# --- fanlight.
# The glazing boundary is concentric with the ARCH centre; the spokes
# and the ring muntin are concentric with the TRANSOM TOP. Both were
# checked against the render -- fitting the ring to the transom origin
# gave a 4 px spread against 13 px for the arch origin.
FAN_GLASS_R = 0.2337  # 225 px from the arch centre
FAN_ORIGIN_Z = TRANSOM_TOP
FAN_RING_R = 0.1090  # the single concentric muntin, 105 px
FAN_HUB_R = 0.0395  # half-round boss the spokes spring from
FAN_SPOKE_ANGLES = (23.7, 47.6, 90.0, 132.4, 156.3)  # degrees
MUNTIN_HALF_W = 0.0045

# --- arch band mouldings, radii from the arch centre
ARCH_MOULD_A = 0.2685  # inner edge of the bullnose (258.5 px)
ARCH_MOULD_B = 0.2980  # outer edge of the bullnose (287 px)

# --- depths. A frontal render carries no depth information, so these
#     are architectural values consistent with the existing scene.
CASING_PROUD = 0.018
WALL_FACE_Y = CASING_PROUD
LEAF_SETBACK = 0.012
LEAF_FRONT_Y = WALL_FACE_Y + LEAF_SETBACK
LEAF_DEPTH = 0.030
LEAF_BACK_Y = LEAF_FRONT_Y + LEAF_DEPTH
WALL_DEPTH = 0.058
PANEL_RELIEF = 0.009  # how far the field sits behind the stile face
MUNTIN_DEPTH = 0.012
BEAD_PROUD = 0.010
IMPOST_PROUD = 0.006
TRANSOM_DEPTH = 0.026
THRESHOLD_H = 0.010
MOULD_PROUD = 0.006

LEAF_GAP = 0.0015
LEAF_WIDTH = OPENING_HALF - LEAF_GAP

# --- f-hole handle.
# Centreline traced from the skeleton of the gold mask in the render,
# resampled by arclength: (x, z, radius) in assembly coordinates for
# the LEFT leaf. Radii come from the distance transform, so the taper
# is the reference's own taper.
HANDLE_SPINE = (
    (-0.11600, 0.27313, 0.00425),
    (-0.11873, 0.28106, 0.00524),
    (-0.12276, 0.27988, 0.00599),
    (-0.12574, 0.27689, 0.00595),
    (-0.12535, 0.27276, 0.00542),
    (-0.12387, 0.26854, 0.00498),
    (-0.12119, 0.26482, 0.00448),
    (-0.11778, 0.26140, 0.00406),
    (-0.11368, 0.25963, 0.00360),
    (-0.10928, 0.25859, 0.00317),
    (-0.10445, 0.25859, 0.00281),
    (-0.09961, 0.25859, 0.00275),
    (-0.09522, 0.25965, 0.00288),
    (-0.09124, 0.26171, 0.00295),
    (-0.08778, 0.26501, 0.00342),
    (-0.08485, 0.26863, 0.00390),
    (-0.08168, 0.27215, 0.00435),
    (-0.07966, 0.27614, 0.00478),
    (-0.07779, 0.28019, 0.00533),
    (-0.07584, 0.28422, 0.00585),
    (-0.07463, 0.28855, 0.00616),
    (-0.07342, 0.29288, 0.00658),
    (-0.07342, 0.29771, 0.00691),
    (-0.07239, 0.30211, 0.00712),
    (-0.07135, 0.30651, 0.00720),
    (-0.07135, 0.31135, 0.00761),
    (-0.07102, 0.31604, 0.00782),
    (-0.07031, 0.32058, 0.00797),
    (-0.07055, 0.32531, 0.00831),
    (-0.07135, 0.32981, 0.00865),
    (-0.07135, 0.33464, 0.00885),
    (-0.07135, 0.33947, 0.00909),
    (-0.07135, 0.34430, 0.00911),
    (-0.07148, 0.34908, 0.00898),
    (-0.07208, 0.35280, 0.00888),
    (-0.07239, 0.35751, 0.00870),
    (-0.07239, 0.36234, 0.00847),
    (-0.07239, 0.36717, 0.00844),
    (-0.07239, 0.37200, 0.00844),
    (-0.07239, 0.37683, 0.00828),
    (-0.07275, 0.38151, 0.00804),
    (-0.07342, 0.38606, 0.00783),
    (-0.07342, 0.39089, 0.00763),
    (-0.07342, 0.39572, 0.00735),
    (-0.07342, 0.40056, 0.00706),
    (-0.07239, 0.40496, 0.00670),
    (-0.07135, 0.40936, 0.00615),
    (-0.07031, 0.41376, 0.00549),
    (-0.06927, 0.41816, 0.00474),
    (-0.06758, 0.42229, 0.00396),
    (-0.06417, 0.42571, 0.00328),
    (-0.06149, 0.42943, 0.00279),
    (-0.05730, 0.43099, 0.00221),
    (-0.05290, 0.43203, 0.00198),
    (-0.05058, 0.43514, 0.00166),
)
HANDLE_STANDOFF = 0.022  # how far the pull stands off the leaf face
HANDLE_SEGMENTS = 10

ARC_SEGMENTS = 96

MAT_LACQUER = "Lacquer"
MAT_GOLD = "Gold"
MAT_GLASS = "Glass"


# ---------------------------------------------------------------------------
# Geometry core -- pure python, no bpy
#
# Blender axes: x across, y depth (0 at the front face, + into the door),
# z height. A polygon wound counter-clockwise in the xz plane (x right,
# z up) has its normal pointing at -y, i.e. out toward the viewer.
# ---------------------------------------------------------------------------


class Part:
    """A chunk of geometry destined to become one Blender object."""

    __slots__ = ("name", "verts", "faces", "material", "smooth")

    def __init__(self, name, material, smooth=False):
        self.name = name
        self.verts: list[tuple[float, float, float]] = []
        self.faces: list[list[int]] = []
        self.material = material
        self.smooth = smooth

    def add(self, data):
        verts, faces = data
        base = len(self.verts)
        self.verts.extend(verts)
        self.faces.extend([[i + base for i in f] for f in faces])

    def merge(self, other: "Part"):
        self.add((other.verts, other.faces))

    def mirrored(self, name):
        """Mirror across x, flipping winding so normals stay outward."""
        out = Part(name, self.material, self.smooth)
        out.verts = [(-x, y, z) for x, y, z in self.verts]
        out.faces = [list(reversed(f)) for f in self.faces]
        return out

    def __repr__(self):
        return f"<Part {self.name} v={len(self.verts)} f={len(self.faces)}>"


def _signed_area(poly):
    total = 0.0
    for i in range(len(poly)):
        x0, z0 = poly[i]
        x1, z1 = poly[(i + 1) % len(poly)]
        total += x0 * z1 - x1 * z0
    return total / 2.0


def ccw(poly):
    return list(poly) if _signed_area(poly) > 0 else list(reversed(poly))


def rect(x0, x1, z0, z1):
    return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]


def face(poly, y):
    """A single flat n-gon facing the viewer."""
    poly = ccw(poly)
    return [(x, y, z) for x, z in poly], [list(range(len(poly)))]


def prism(poly, y0, y1, caps=True):
    """Extrude a closed 2D polygon between two depth planes."""
    poly = ccw(poly)
    n = len(poly)
    verts = [(x, y0, z) for x, z in poly] + [(x, y1, z) for x, z in poly]
    faces = []
    if caps:
        faces.append(list(range(n)))
        faces.append(list(range(2 * n - 1, n - 1, -1)))
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, i + n, j + n, j])
    return verts, faces


def box(x0, x1, y0, y1, z0, z1):
    return prism(rect(x0, x1, z0, z1), y0, y1)


def open_ring(outer, inner, y0, y1):
    """
    Solid band between two OPEN polylines of equal length -- used for the
    arch, whose bottom is a doorway and must not be capped.
    """
    if len(outer) != len(inner):
        raise ValueError("open_ring: contours must match in length")
    n = len(outer)
    verts = (
        [(x, y0, z) for x, z in outer]
        + [(x, y0, z) for x, z in inner]
        + [(x, y1, z) for x, z in outer]
        + [(x, y1, z) for x, z in inner]
    )
    OF, IF, OB, IB = 0, n, 2 * n, 3 * n
    faces = []
    for i in range(n - 1):
        j = i + 1
        faces.append([OF + i, OF + j, IF + j, IF + i])
        faces.append([IB + i, IB + j, OB + j, OB + i])
        faces.append([OF + i, OB + i, OB + j, OF + j])
        faces.append([IF + i, IF + j, IB + j, IB + i])
    # square off both ends of the band
    faces.append([OF + 0, IF + 0, IB + 0, OB + 0])
    last = n - 1
    faces.append([OB + last, IB + last, IF + last, OF + last])
    return verts, faces


def bevel(outline, field, y_outline, y_field):
    """
    The sloped surface of a recessed panel: from the stile face down and
    inward to the field. Wound so the normal faces the room.
    """
    n = len(outline)
    if len(field) != n:
        raise ValueError("bevel: contours must match in length")
    verts = [(x, y_outline, z) for x, z in outline] + [
        (x, y_field, z) for x, z in field
    ]
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, j, j + n, i + n])
    return verts, faces


def arch_path(half_width, spring_z, base_z, segments=ARC_SEGMENTS):
    """
    Open polyline: up the left jamb, over the semicircle, down the right
    jamb. Runs left-to-right so paired paths stay in step.
    """
    has_jambs = (spring_z - base_z) > 1e-6
    pts = [(-half_width, base_z)] if has_jambs else []
    for i in range(segments + 1):
        angle = math.pi - (math.pi * i) / segments
        pts.append(
            (
                math.cos(angle) * half_width,
                spring_z + math.sin(angle) * half_width,
            )
        )
    if has_jambs:
        pts.append((half_width, base_z))
    return pts


def half_disc(radius, origin_z, segments=ARC_SEGMENTS):
    pts = [(-radius, origin_z), (radius, origin_z)]
    for i in range(1, segments):
        angle = (math.pi * i) / segments
        pts.append(
            (math.cos(angle) * radius, origin_z + math.sin(angle) * radius)
        )
    return pts


def arc_band(r_in, r_out, origin_z, a0, a1, y0, y1, segments=48):
    """An open annular band -- the fanlight's concentric muntin."""
    verts = []
    faces = []
    for i in range(segments + 1):
        t = a0 + (a1 - a0) * i / segments
        ci, si = math.cos(t), math.sin(t)
        for y in (y0, y1):
            for r in (r_out, r_in):
                verts.append((ci * r, y, origin_z + si * r))
    for i in range(segments):
        a, b = i * 4, (i + 1) * 4
        faces.append([a + 0, b + 0, b + 1, a + 1])
        faces.append([a + 3, b + 3, b + 2, a + 2])
        faces.append([a + 0, a + 2, b + 2, b + 0])
        faces.append([a + 1, b + 1, b + 3, a + 3])
    last = segments * 4
    faces.append([0, 1, 3, 2])
    faces.append([last + 0, last + 2, last + 3, last + 1])
    return verts, faces


def tube(spine, radii, segments=HANDLE_SEGMENTS):
    """Sweep a circular profile of varying radius along a 3D polyline."""
    n = len(spine)
    verts = []
    faces = []
    for i, (px, py, pz) in enumerate(spine):
        if i == 0:
            t = [spine[1][k] - spine[0][k] for k in range(3)]
        elif i == n - 1:
            t = [spine[-1][k] - spine[-2][k] for k in range(3)]
        else:
            t = [spine[i + 1][k] - spine[i - 1][k] for k in range(3)]
        tl = math.sqrt(sum(c * c for c in t)) or 1.0
        tx, ty, tz = (c / tl for c in t)

        # The spine lies almost entirely in xz, so depth is a safe
        # reference axis for the frame and never goes parallel.
        ux, uy, uz = ty * 0.0 - tz * 1.0, tz * 0.0 - tx * 0.0, tx * 1.0 - ty * 0.0
        ul = math.sqrt(ux * ux + uy * uy + uz * uz)
        if ul < 1e-9:
            ux, uy, uz, ul = 1.0, 0.0, 0.0, 1.0
        ux, uy, uz = ux / ul, uy / ul, uz / ul
        vx = ty * uz - tz * uy
        vy = tz * ux - tx * uz
        vz = tx * uy - ty * ux

        r = radii[i]
        for s in range(segments):
            a = (math.tau * s) / segments
            ca, sa = math.cos(a) * r, math.sin(a) * r
            verts.append(
                (
                    px + ux * ca + vx * sa,
                    py + uy * ca + vy * sa,
                    pz + uz * ca + vz * sa,
                )
            )

    for i in range(n - 1):
        a, b = i * segments, (i + 1) * segments
        for s in range(segments):
            t2 = (s + 1) % segments
            faces.append([a + s, b + s, b + t2, a + t2])

    verts.append(tuple(spine[0]))
    verts.append(tuple(spine[-1]))
    cap0, cap1 = len(verts) - 2, len(verts) - 1
    last = (n - 1) * segments
    for s in range(segments):
        t2 = (s + 1) % segments
        faces.append([cap0, t2, s])
        faces.append([cap1, last + s, last + t2])
    return verts, faces


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def build_surround() -> Part:
    part = Part("Surround", MAT_LACQUER)

    # the arched casing: the band from the opening out to the outer face
    part.add(
        open_ring(
            arch_path(OUTER_HALF, SPRING_Z, LEAF_BOTTOM - THRESHOLD_H),
            arch_path(OPENING_HALF, SPRING_Z, LEAF_BOTTOM - THRESHOLD_H),
            0.0,
            WALL_DEPTH,
        )
    )

    # bullnose moulding riding on the face of that band
    part.add(
        open_ring(
            arch_path(ARCH_MOULD_B, SPRING_Z, LEAF_BOTTOM - THRESHOLD_H),
            arch_path(ARCH_MOULD_A, SPRING_Z, LEAF_BOTTOM - THRESHOLD_H),
            -MOULD_PROUD,
            0.0,
        )
    )

    # pilaster relief: a raised bead with a groove outboard of it
    for sign in (-1.0, 1.0):
        lo, hi = sorted((sign * BEAD_OUT, sign * BEAD_IN))
        part.add(box(lo, hi, -BEAD_PROUD, 0.0, BASE_STEP_1_Z, IMPOST_BOTTOM))
        lo, hi = sorted((sign * PILASTER_GROOVE, sign * BEAD_OUT))
        if hi - lo > 1e-6:
            part.add(box(lo, hi, 0.0, 0.004, BASE_STEP_1_Z, IMPOST_BOTTOM))

    # impost blocks at the arch spring
    for sign in (-1.0, 1.0):
        lo, hi = sorted((sign * OPENING_HALF, sign * IMPOST_HALF))
        part.add(
            box(lo, hi, -IMPOST_PROUD, WALL_DEPTH, IMPOST_BOTTOM, IMPOST_TOP)
        )

    # Stepped base. The upper plinth sits only in the pilaster zones --
    # spanning it across the opening would bury the bottom of the leaves,
    # which in the reference stay visible down to LEAF_BOTTOM.
    for sign in (-1.0, 1.0):
        lo, hi = sorted((sign * OPENING_HALF, sign * IMPOST_HALF))
        part.add(
            box(
                lo,
                hi,
                -IMPOST_PROUD,
                WALL_DEPTH,
                BASE_STEP_2_Z,
                BASE_STEP_1_Z,
            )
        )
    # the bottom step runs the full width
    part.add(
        box(
            -BASE_HALF,
            BASE_HALF,
            -IMPOST_PROUD - 0.004,
            WALL_DEPTH,
            0.0,
            BASE_STEP_2_Z,
        )
    )

    # transom bar under the fanlight
    part.add(
        box(
            -OPENING_HALF,
            OPENING_HALF,
            WALL_FACE_Y - TRANSOM_DEPTH,
            WALL_FACE_Y + TRANSOM_DEPTH * 0.4,
            LEAF_TOP,
            TRANSOM_TOP,
        )
    )

    # Threshold, stepped to match the mouldings the reference shows
    # crossing the opening at z = 0.0415 and z = 0.0280.
    part.add(
        box(
            -OPENING_HALF,
            OPENING_HALF,
            WALL_FACE_Y - 0.004,
            WALL_DEPTH,
            THRESHOLD_STEP_Z,
            LEAF_BOTTOM,
        )
    )
    part.add(
        box(
            -OPENING_HALF,
            OPENING_HALF,
            WALL_FACE_Y - 0.010,
            WALL_DEPTH,
            BASE_STEP_2_Z,
            THRESHOLD_STEP_Z,
        )
    )

    return part


def build_fanlight() -> tuple[Part, Part]:
    frame = Part("Fanlight", MAT_LACQUER, smooth=True)
    glass = Part("FanlightGlass", MAT_GLASS, smooth=True)

    # frame band between the glazing boundary and the opening
    frame.add(
        open_ring(
            arch_path(OPENING_HALF, SPRING_Z, SPRING_Z),
            arch_path(FAN_GLASS_R, SPRING_Z, SPRING_Z),
            WALL_FACE_Y - 0.004,
            WALL_FACE_Y + 0.018,
        )
    )

    y0 = WALL_FACE_Y - MUNTIN_DEPTH * 0.5
    y1 = WALL_FACE_Y + MUNTIN_DEPTH * 0.5

    for degrees in FAN_SPOKE_ANGLES:
        angle = math.radians(degrees)
        ca, sa = math.cos(angle), math.sin(angle)
        px, pz = -sa * MUNTIN_HALF_W, ca * MUNTIN_HALF_W
        r0, r1 = FAN_HUB_R * 0.5, FAN_GLASS_R + 0.006
        ax, az = ca * r0, sa * r0
        bx, bz = ca * r1, sa * r1
        frame.add(
            prism(
                [
                    (ax + px, FAN_ORIGIN_Z + az + pz),
                    (bx + px, FAN_ORIGIN_Z + bz + pz),
                    (bx - px, FAN_ORIGIN_Z + bz - pz),
                    (ax - px, FAN_ORIGIN_Z + az - pz),
                ],
                y0,
                y1,
            )
        )

    frame.add(
        arc_band(
            FAN_RING_R - MUNTIN_HALF_W,
            FAN_RING_R + MUNTIN_HALF_W,
            FAN_ORIGIN_Z,
            0.0,
            math.pi,
            y0,
            y1,
        )
    )

    frame.add(
        prism(half_disc(FAN_HUB_R, FAN_ORIGIN_Z, 24), y0 - 0.004, y1 + 0.004)
    )

    glass.add(
        prism(
            half_disc(FAN_GLASS_R, SPRING_Z, ARC_SEGMENTS),
            WALL_FACE_Y + 0.006,
            WALL_FACE_Y + 0.010,
        )
    )
    return frame, glass


def _panel_box(z_out_bottom, z_out_top):
    """Leaf-local x/z extents of one panel's moulding outline."""
    return (
        LEAF_WIDTH - PANEL_OUT_X,
        LEAF_WIDTH - PANEL_OUT_INNER_X,
        z_out_bottom,
        z_out_top,
    )


def _add_panel(part, z_out_bottom, z_field_bottom, z_field_top, z_out_top):
    """
    A recessed panel: the bevel runs back from the stile face to a flat
    field. The leaf's front face is built as separate rails and stiles,
    so the recess is a genuine opening rather than a decal on a slab.
    """
    x0, x1, _, _ = _panel_box(z_out_bottom, z_out_top)
    outline = ccw(rect(x0, x1, z_out_bottom, z_out_top))
    field = ccw(
        rect(
            LEAF_WIDTH - PANEL_FIELD_X,
            LEAF_WIDTH - PANEL_FIELD_INNER_X,
            z_field_bottom,
            z_field_top,
        )
    )
    part.add(bevel(outline, field, LEAF_FRONT_Y, LEAF_FRONT_Y + PANEL_RELIEF))
    part.add(face(field, LEAF_FRONT_Y + PANEL_RELIEF))


def build_leaf(name="Leaf") -> Part:
    """One leaf, hinge at the origin, meeting stile at x = LEAF_WIDTH."""
    part = Part(name, MAT_LACQUER)

    px0 = LEAF_WIDTH - PANEL_OUT_X
    px1 = LEAF_WIDTH - PANEL_OUT_INNER_X

    # front face, decomposed into stiles and rails around the two panels
    for poly in (
        rect(0.0, px0, LEAF_BOTTOM, LEAF_TOP),  # hinge stile
        rect(px1, LEAF_WIDTH, LEAF_BOTTOM, LEAF_TOP),  # meeting stile
        rect(px0, px1, UPPER_PANEL_TOP, LEAF_TOP),  # top rail
        rect(px0, px1, LOWER_PANEL_TOP, UPPER_PANEL_BOTTOM),  # lock rail
        rect(px0, px1, LEAF_BOTTOM, LOWER_PANEL_BOTTOM),  # bottom rail
    ):
        part.add(face(poly, LEAF_FRONT_Y))

    _add_panel(
        part,
        UPPER_PANEL_BOTTOM,
        UPPER_PANEL_FIELD_BOTTOM,
        UPPER_PANEL_FIELD_TOP,
        UPPER_PANEL_TOP,
    )
    _add_panel(
        part,
        LOWER_PANEL_BOTTOM,
        LOWER_PANEL_FIELD_BOTTOM,
        LOWER_PANEL_FIELD_TOP,
        LOWER_PANEL_TOP,
    )

    # perimeter walls and the back face
    outline = ccw(rect(0.0, LEAF_WIDTH, LEAF_BOTTOM, LEAF_TOP))
    n = len(outline)
    verts = [(x, LEAF_FRONT_Y, z) for x, z in outline] + [
        (x, LEAF_BACK_Y, z) for x, z in outline
    ]
    faces = [list(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        j = (i + 1) % n
        faces.append([i, i + n, j + n, j])
    part.add((verts, faces))

    return part


def build_handle(name="Handle") -> Part:
    part = Part(name, MAT_GOLD, smooth=True)
    spine = [
        (x + OPENING_HALF, LEAF_FRONT_Y - HANDLE_STANDOFF, z)
        for x, z, _ in HANDLE_SPINE
    ]
    radii = [r for _, _, r in HANDLE_SPINE]
    part.add(tube(spine, radii))
    return part


def build_parts() -> dict:
    """Every piece of the assembly, plus hinge positions. No bpy."""
    fan_frame, fan_glass = build_fanlight()
    surround = build_surround()
    surround.merge(fan_frame)

    leaf_l = build_leaf("LeafL")
    handle_l = build_handle("HandleL")

    return {
        "Surround": surround,
        "FanlightGlass": fan_glass,
        "LeafL": leaf_l,
        "HandleL": handle_l,
        "LeafR": leaf_l.mirrored("LeafR"),
        "HandleR": handle_l.mirrored("HandleR"),
        "hinges": {
            "HingeL": (-OPENING_HALF, 0.0, 0.0),
            "HingeR": (OPENING_HALF, 0.0, 0.0),
        },
    }


# ---------------------------------------------------------------------------
# Blender bindings
# ---------------------------------------------------------------------------


def _material(name):
    import bpy

    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        if name == MAT_LACQUER:
            bsdf.inputs["Base Color"].default_value = (0.016, 0.016, 0.017, 1)
            bsdf.inputs["Roughness"].default_value = 0.34
        elif name == MAT_GOLD:
            bsdf.inputs["Base Color"].default_value = (0.79, 0.65, 0.31, 1)
            bsdf.inputs["Metallic"].default_value = 1.0
            bsdf.inputs["Roughness"].default_value = 0.30
        elif name == MAT_GLASS:
            bsdf.inputs["Base Color"].default_value = (0.05, 0.07, 0.07, 1)
            bsdf.inputs["Roughness"].default_value = 0.08
    return mat


def _object_from_part(part, parent=None, location=(0.0, 0.0, 0.0)):
    import bpy

    mesh = bpy.data.meshes.new(f"{part.name}_mesh")
    mesh.from_pydata(part.verts, [], part.faces)
    mesh.validate(verbose=False)
    mesh.update()
    if part.smooth:
        for poly in mesh.polygons:
            poly.use_smooth = True
    mesh.materials.append(_material(part.material))

    obj = bpy.data.objects.new(part.name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def _empty(name, location, parent=None):
    import bpy

    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.06
    bpy.context.collection.objects.link(obj)
    obj.location = location
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def main(export_path="hallway-door.glb"):
    import bpy

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in (bpy.data.meshes, bpy.data.materials):
        for item in list(collection):
            if item.users == 0:
                collection.remove(item)

    parts = build_parts()

    root = _empty("DoorAssembly", (0.0, 0.0, 0.0))
    _object_from_part(parts["Surround"], parent=root)
    _object_from_part(parts["FanlightGlass"], parent=root)

    for side in ("L", "R"):
        hinge_name = f"Hinge{side}"
        hinge = _empty(hinge_name, parts["hinges"][hinge_name], parent=root)
        # Leaves and handles are already authored hinge-at-origin, and the
        # right-hand pair has its mirror baked into the vertex data rather
        # than applied as a negative scale -- glTF consumers dislike those.
        _object_from_part(parts[f"Leaf{side}"], parent=hinge)
        _object_from_part(parts[f"Handle{side}"], parent=hinge)

    bpy.context.view_layer.update()

    print("--- hecate946 door ---")
    for key in ("Surround", "FanlightGlass", "LeafL", "HandleL"):
        print(f"  {parts[key]}")
    print(f"  opening half-width : {OPENING_HALF:.4f}")
    print(f"  outer half-width   : {OUTER_HALF:.4f}")
    print(f"  hinge x            : +/- {OPENING_HALF:.4f}")

    bpy.ops.export_scene.gltf(
        filepath=export_path,
        export_format="GLB",
        export_yup=True,
        export_apply=True,
        export_animations=False,
        export_cameras=False,
        export_lights=False,
        use_selection=False,
    )
    print(f"exported -> {export_path}")


def _has_bpy():
    import importlib.util

    return importlib.util.find_spec("bpy") is not None


if __name__ == "__main__" and _has_bpy():
    main()
