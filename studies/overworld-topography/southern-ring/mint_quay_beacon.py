"""THE LANTERN BEACON -- generate the Southern Ring's quay marker mesh from scratch (our own geometry).

WHY FROM SCRATCH
    The first attempt carried stock FF9's Alexandria Harbour gate verbatim. It worked functionally
    (nameplate, prompt, entry, textured) but was REJECTED on design at playtest:
      * Z-FIGHTING -- the donor embeds water-plane quads under its arch, and its base sat coplanar
        with the y=3.00 plateau;
      * BACK-FACE CULLING -- the donor's single-sided walls vanish when viewed from behind;
      * and the real objection: a HARBOUR sitting on dry land is simply wrong.
    So this mesh is authored, not carried, and every one of those three failures is designed out:
      * CLOSED WATERTIGHT SOLID -- every edge shared by exactly 2 faces, every face wound OUTWARD,
        so there is no angle from which anything culls away (asserted, not hoped);
      * NO COPLANAR-WITH-GROUND FACE -- the plinth skirt extends 0.5u BELOW the ground plane, so the
        bottom cap is buried and nothing shares the terrain's y (the doc's "seat, don't flatten" skirt
        idiom, applied as an anti-z-fight measure);
      * a LANTERN BEACON reads correctly inland, on a quay, at four different sites.

    Thematic intent: every Southern Ring quay gets the same beacon, so the silhouette becomes the
    ring's shared "you can dock here" vocabulary. This generator is the reusable source for all four.

THE SHAPE (a stacked-ring prismatoid -- tapered stone tower, gallery, lantern head, pyramid roof)
    Rings of 8 perimeter points (a square with edge midpoints) stacked up the Y axis and quad-stripped
    to their neighbour; a fan cap at the bottom, a single apex at the top. Because consecutive rings
    are connected all the way around and both ends are closed, the result is a closed 2-manifold by
    construction -- which `_assert_closed_solid` then proves.

    The horizontal midpoints exist for TEXTURING, not silhouette: they halve every side panel to
    ~2.3u, near the ~1-2u real-tile scale the atlas stamp wants ("the stamp doesn't rescale, so a big
    face smears one small tile across itself" -- OVERWORLD_ENGINE.md). The shaft and lantern are
    likewise subdivided vertically into ~1.4u and ~1.0u bands for the same reason.

    Footprint 4.60 x 5.05 u (asymmetric -- the entrance steps project south), height 10.60 u above
    ground (+0.50 u buried skirt), 270 triangles -- inside the 100-320 budget, and in the stock landmark
    legibility band (harbour gate 5.5u reads small, Alexandria castle 16.8u; ~10u is a landmark you
    notice without dwarfing the cell). The SOUTH face carries a recessed doorway + steps; see THE
    ENTRANCE FACE below.

PLACEMENT / COLLISION (the proven building-layer laws -- OVERWORLD_ENGINE.md:405-414)
    This mesh is the RENDER-ONLY Object layer. Collision is NOT this mesh -- it is the TERRAIN under
    the mesh's convex hull, stamped topograph 59 by `split_retarget_by_polygon`, which conforms to the
    ground and has zero render effect (UV-only). `world-entrance --building` does both halves.

    ⚠ "RENDER-ONLY" IS NOT AUTOMATIC AT ANY OF THE FOUR SITES. Every quay block is a RECLAIMED cell
    whose `Donor.txt` names donor (0,0), and (0,0) HAS a stock Object component -- so the engine takes
    `RegisterBlockComponent(form1: true)` and DOES feed the Object override to `AddWalkMeshForm1`
    (WMWorld.cs:775-814), ahead of Terrain in the ground query. **`--building-idall 4078` is MANDATORY
    at every site** (the `WMPhysics.Raycast` skip id); footprint collision comes from the topo-59
    terrain hull instead.

    Authored in WORLD coords at each site's own ground plane, so the deploy uses `--no-seat`: seating
    would put the LOWEST point on the ground and un-bury the skirt, reintroducing the coplanar bottom
    cap the beacon exists to avoid.

MULTI-SITE
    One `SITES` row per quay (anchor, ground_y, trigger rect, arrive point + face, host block, cell).
    The generator, the door and all 29 gates are identical at every site -- a new quay is a row, not a
    fork. `rebuild_quay_marker.sh <site>` re-deploys one; each site's southern-limit derivation is
    documented there and in REVERT.md.

USAGE
    py .../mint_quay_beacon.py                 # generate + gate ALL four quays
    py .../mint_quay_beacon.py --site tidefall # just one
    py .../mint_quay_beacon.py --tile-uv       # also print the three atlas tile rects
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))

# ---- siting (world coords) -------------------------------------------------------------------------
# THE TRIGGER-AT-THE-FOOT LAW (owner playtest, pass 3 -> 4). Pass 3 sat the beacon at z -1157, which
# left the 6 trigger tris (z[-1172,-1164]) ~12u SOUTH of it: the "!" fired in open grass with the tower
# standing apart. Stock's idiom -- and our own waystation precedent -- put the trigger AT THE
# STRUCTURE'S FOOT. So the beacon is sited as far SOUTH as the hull gates allow.
#
# ⚠ THE SOUTHERN LIMIT WAS RE-SOLVED IN PASS 5 (the entrance-face door). The hull must stay >= 1.0u
# clear of the trigger rect, and the hull is computed from the mesh's FULL XZ extent -- which now
# includes the entrance steps projecting STEP_OUT south of the plinth face:
#
#   pass 4 (no steps):   south edge = cz - 2.30            >= -1163.0  =>  cz >= -1160.70
#   pass 5 (+0.45 steps): south edge = cz - (2.30 + 0.45)  >= -1163.0  =>  cz >= -1160.25
#
# so the centre moves 0.30u NORTH to cz = -1160.20 (0.05u of slack). The STRUCTURE still gets closer
# to the trigger than before: its southern extent is now the bottom step at z -1162.95, versus pass 4's
# bare plinth face at -1162.80. The door faces the trigger across a 1.05u gap.
#
# The arrival (60,-1168) is then ~10.9u away (gate: >= 6u) and the arrival->trigger path along
# z = -1168 stays >= 5.05u south of the footprint, whose x span [45.70,50.30] is WEST of the eastern
# approach corridor -- so walking in from the east cannot clip the hull.
SKIRT_BURY = 0.50               # how far the plinth base sits BELOW the ground plane


class Site(NamedTuple):
    """One quay's siting. The generator is otherwise identical at every site -- same profile, same
    door, same gates -- so a new quay is a row here, not a fork of the code."""
    name: str
    anchor: tuple                # beacon XZ centre (= --building-at); the bbox centre --at anchors on
    ground_y: float              # the terrain plateau the base sits on
    trigger_bbox: tuple          # x0,x1,z0,z1 of the entrance's event tiles
    arrive: tuple                # the berth-exit arrive point
    block: tuple                 # the host block's world footprint x0,x1,z0,z1
    arrive_face: int             # facing byte written at the arrive point (192 = east, 64 = west)
    cell: tuple                  # the entrance cell, for the surgery command
    trigger_at: tuple            # --trigger-at for world-entrance


def _blk(bx, by):
    return (bx * 64.0, bx * 64.0 + 64.0, -(by + 1) * 64.0, -by * 64.0)


# ⚠ S.ground_y IS THE FOOTPRINT'S *MINIMUM*, NOT ITS MAXIMUM. On flat ground the two agree, but Larkspur
# has 0.116u of relief across the footprint (measured 3.037..3.154). Seating on the MAX would leave the
# plinth FLOATING 0.11u over the low corner -- a visible gap with a shadow under it. Seating on the MIN
# instead buries the base 0.11u into the high corner, which is invisible. Sink, never float.
SITES = {
    "ashvale":  Site("Ashvale",  (48.0, -1160.2),   3.00,
                     (44.0, 52.0, -1172.0, -1164.0),   (60.0, -1168.0),  _blk(0, 18),  192,
                     (1, 36),  (48.0, -1168.0)),
    "tidefall": Site("Tidefall", (420.0, -1224.2),  3.20,
                     (416.0, 424.0, -1236.0, -1228.0), (432.0, -1232.0), _blk(6, 19),  192,
                     (13, 38), (420.0, -1232.0)),
    "grimhorn": Site("Grimhorn", (1204.0, -1184.2), 3.20,
                     (1200.0, 1208.0, -1196.0, -1188.0), (1214.0, -1192.0), _blk(18, 18), 192,
                     (37, 37), (1204.0, -1192.0)),
    "larkspur": Site("Larkspur", (700.0, -608.2),   3.03,
                     (696.0, 704.0, -620.0, -612.0),   (688.0, -616.0),  _blk(10, 9),   64,
                     (21, 19), (700.0, -616.0)),
}

def obj_path(site):
    """Ashvale keeps the original filename so the pass-4/5 history and the deploy script
    still resolve; the new quays get their own."""
    return HERE / ("quay_beacon.obj" if site.name == "Ashvale"
                   else f"quay_beacon_{site.name.lower()}.obj")

# siting gates (the beacon must abut the trigger WITHOUT the hull ever reaching it)
HULL_CLEARANCE = 1.0                            # min gap from the footprint to the trigger rect
ARRIVE_CLEARANCE = 6.0

# ---- the profile: (y above ground, half-width) ------------------------------------------------------
# A pair of rings at the same y with different half-widths makes a horizontal step (a plinth lip, a
# gallery ledge, a roof eave). Consecutive rings at different y make a wall or a taper.
PLINTH_H = 2.90                 # plinth top -- RAISED in pass 5 from 1.30 so it can host the doorway

PROFILE = [
    (-SKIRT_BURY, 2.30),        # 0  buried skirt base
    (0.00, 2.30),               # 1  ground line (a ring here, so no face STRADDLES the terrain plane)
    (PLINTH_H, 2.30),           # 2  plinth top
    (PLINTH_H, 1.80),           # 3  step in to the shaft
    (3.93, 1.68),               # 4  shaft, 4 bands of ~1.0u -- tapering
    (4.95, 1.55),               # 5
    (5.98, 1.43),               # 6
    (7.00, 1.30),               # 7  shaft top
    (7.00, 2.10),               # 8  gallery ledge out
    (7.85, 2.10),               # 9  gallery top
    (7.85, 1.40),               # 10 step in to the lantern head
    (8.85, 1.40),               # 11 lantern, 2 bands of 1.0u
    (9.85, 1.40),               # 12 lantern top
    (9.85, 1.60),               # 13 roof eave out
]
APEX_Y = 10.60                  # pyramid roof apex

RING_N = 8                      # 8 perimeter points = a square with edge midpoints (2 panels per side)

# ---- THE ENTRANCE FACE (pass 5) ---------------------------------------------------------------------
# Owner's law from the pass-4 playtest: "most buildings have some obvious entrance feature; ours does
# not, making the entrance seem offset." So the SOUTH face -- the one the quay trigger sits at -- gets a
# recessed doorway with a lintel, and two shallow steps up to its threshold. The other three faces are
# untouched: THE ASYMMETRY IS THE POINT. It tells the player which side to approach.
#
# Ring index 6 is the south mid-point (t=270deg), so the south face is the two perimeter panels i=5..6,
# spanning SW corner (5) -> S mid (6) -> SE corner (7).
DOOR_STRIP = 1                  # the PROFILE strip the door lives in (1 -> 2, i.e. the plinth wall)
DOOR_SEGS = (5, 6)              # the two south perimeter panels the door surface replaces
DOOR_HALF_W = 0.80              # half the opening width (1.60u wide)
DOOR_SILL = 0.45                # threshold height above ground (the steps climb to just under it)
DOOR_TOP = 2.50                 # opening head above ground -> a 2.05u tall door, 0.40u of lintel above
DOOR_DEPTH = 0.35               # how far the recess is sunk into the wall

STEP_OUT = 0.45                 # how far the steps project SOUTH of the plinth face (<= 0.5u by brief)
STEP_BACK = 0.02                # ...and how far they poke INTO the wall, so there is no crack at the join
STEP_TIERS = [                  # (half-width, top height above ground, south projection)
    (1.20, 0.20, 0.45),         # lower/outer tread
    (1.00, 0.42, 0.22),         # upper tread -- 0.03u under DOOR_SILL so it is never COPLANAR with it
]

# ---- atlas tiles -----------------------------------------------------------------------------------
# UVs into the SHARED `res(1_24)_objects` atlas (the engine-resolved one: a Moguri install renders a
# 4096^2 HD atlas, vanilla 1024^2 -- UVs are normalised so both work). Rects were chosen by eye from a
# contact sheet of the atlas's real object tiles (`world-atlas-catalog`-style crop), then inset by one
# 4096-texel to stop a neighbouring tile bleeding in at the seam.
#
# Only COORDINATES live here, never atlas pixels -- so this file stays provenance-clean while the
# beacon still renders in real FF9 stone instead of the atlas's alpha-0 corner (which reads as white).
_TEXEL = 1.0 / 4096.0


def _inset(r):
    return (r[0] + _TEXEL, r[1] + _TEXEL, r[2] - _TEXEL, r[3] - _TEXEL)


TILE_STONE = _inset((0.0039, 0.3506, 0.0352, 0.3818))   # rough grey-brown masonry (topo-59 family)
TILE_LANTERN = _inset((0.3340, 0.4355, 0.3613, 0.4570))  # warm orange -- the lit lantern room (topo-49)
# The door recess reads as an OPENING, so it wants the flattest, darkest tile on the object atlas.
# Chosen by MEASURE, not by eye: mean luminance 2.2/255 with stddev 0.9 across the whole rect -- i.e.
# a near-uniform black panel -- the darkest of 685 candidate tiles sampled from the object palette.
TILE_DOOR = _inset((0.3359, 0.7773, 0.3486, 0.7930))

# which ring-strips are the lantern room (0-based strip k joins PROFILE[k] -> PROFILE[k+1])
LANTERN_STRIPS = {10, 11}


def _ring(S, y: float, half: float):
    """A square ring of ``RING_N`` points at height ``y``, half-width ``half``, centred on the site anchor
    in WORLD XZ (the whole mesh is authored world-positioned, so the deploy needs no seating)."""
    pts = []
    for i in range(RING_N):
        t = 2.0 * math.pi * i / RING_N
        # Chebyshev normalisation turns the unit circle into a unit SQUARE, keeping the 8 points
        # evenly distributed as 4 corners + 4 edge midpoints.
        cx, cz = math.cos(t), math.sin(t)
        m = max(abs(cx), abs(cz))
        pts.append((S.anchor[0] + half * cx / m, y, S.anchor[1] + half * cz / m))
    return pts


def _normal(face_pts):
    """The unit geometric normal of a triangle, from its winding (right-hand rule)."""
    a, b, c = face_pts
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
    L = math.sqrt(sum(k * k for k in n)) or 1.0
    return (n[0] / L, n[1] / L, n[2] / L)


def _box_solid(add, faces, uvs, verts, x0, x1, y0, y1, z0, z1, tile):
    """Append a CLOSED axis-aligned box as its own component, wound outward.

    Built from the same primitives as the tower rather than by hand-writing 12 triangles: two rings in
    the ring parameterisation's rotational order (corners at t = 45/135/225/315deg), a wall strip
    between them, a bottom fan in ``t`` order (which yields -Y, proven by the tower's buried cap) and a
    top fan in REVERSED ``t`` order (hence +Y). Reusing the derived rules is the point -- hand-flipping
    faces is what broke orientability the first time the tower was built."""
    corners = [(x1, z1), (x0, z1), (x0, z0), (x1, z0)]     # t = 45, 135, 225, 315 -- same sense as _ring
    bot = [add((cx, y0, cz)) for (cx, cz) in corners]
    top = [add((cx, y1, cz)) for (cx, cz) in corners]
    u0, v0, u1, v1 = tile
    for i in range(4):                                      # walls
        j = (i + 1) % 4
        faces.append([bot[i], top[i], top[j]]); uvs.extend([(u0, v0), (u0, v1), (u1, v1)])
        faces.append([bot[i], top[j], bot[j]]); uvs.extend([(u0, v0), (u1, v1), (u1, v0)])
    for i in range(1, 3):                                   # bottom cap (t order -> faces DOWN)
        faces.append([bot[0], bot[i], bot[i + 1]]); uvs.extend([(u0, v0), (u1, v0), (u1, v1)])
        faces.append([top[0], top[i + 1], top[i]]); uvs.extend([(u0, v0), (u1, v1), (u1, v0)])
    return bot, top


def _signed_volume(verts, faces, origin) -> float:
    """The mesh's signed volume about ``origin`` (divergence theorem, tetrahedron sum).

    For a CLOSED, consistently-wound mesh this is +|volume| when the winding is OUTWARD and
    -|volume| when it is inward. This is the right global orientation test here because the beacon is
    NOT convex (the gallery overhangs the shaft), so a per-face "does the normal point away from the
    axis" test would legitimately fail on the overhang's underside and prove nothing."""
    total = 0.0
    for f in faces:
        a, b, c = ((verts[i][0] - origin[0], verts[i][1] - origin[1], verts[i][2] - origin[2]) for i in f)
        cr = (b[1] * c[2] - b[2] * c[1], b[2] * c[0] - b[0] * c[2], b[0] * c[1] - b[1] * c[0])
        total += (a[0] * cr[0] + a[1] * cr[1] + a[2] * cr[2]) / 6.0
    return total


def build_beacon(S):
    """Return ``(verts, faces, normals)`` -- a closed watertight solid in WORLD coords.

    THE WINDING RULE (derived, not guessed). Ring points run with the angle ``t`` increasing, so the
    tangent is ``T = (-sin t, 0, cos t)`` and the outward radial is ``R = (cos t, 0, sin t)``. For a
    strip between a lower ring ``L`` and the next ring ``U`` at perimeter ``i -> j``, winding each quad
    as ``L[i] -> U[i] -> U[j] -> L[j]`` gives ``(U[i]-L[i]) x (U[j]-L[i])``, and:

      * rings at DIFFERENT y (a wall/taper): ``= h*dt*(up x T) = +R``  -> faces OUTWARD;
      * ring SHRINKS at the same y (a plinth lip): ``= -d*dt*(R x T) = +up``  -> faces UP;
      * ring GROWS at the same y (the gallery overhang): ``= +d*dt*(R x T) = -up`` -> faces DOWN.

    One rule, correct for all three, because ``R x T = (0,-1,0)`` and ``up x T = R``. The roof reuses
    it with ``U`` collapsed to the apex; the bottom-cap fan in the same ``t`` order yields ``-up``,
    which is what a buried base wants. So NO per-face flipping is needed -- and none is done, because
    per-face guessing is exactly what breaks global orientability."""
    rings = [_ring(S, S.ground_y + y, h) for (y, h) in PROFILE]
    verts: list[tuple] = []
    faces: list[list[int]] = []
    uvs: list[tuple] = []                                  # one UV per face-CORNER (3 per triangle)

    def add(p):
        verts.append(p)
        return len(verts) - 1

    ring_idx = [[add(p) for p in r] for r in rings]

    def quad(a, b, c, d, tile):
        """Emit a quad a->b->c->d (a,b = the 'left' edge) as 2 tris, UV-mapped so the WHOLE tile fills
        the panel exactly once. Mapping per QUAD (not per triangle) is what avoids the diagonal
        half-cut you get from stamping a rect onto each tri independently."""
        u0, v0, u1, v1 = tile
        faces.append([a, b, c]); uvs.extend([(u0, v0), (u0, v1), (u1, v1)])
        faces.append([a, c, d]); uvs.extend([(u0, v0), (u1, v1), (u1, v0)])

    # side strips between consecutive rings
    for k in range(len(rings) - 1):
        lo, hi = ring_idx[k], ring_idx[k + 1]
        tile = TILE_LANTERN if k in LANTERN_STRIPS else TILE_STONE
        for i in range(RING_N):
            j = (i + 1) % RING_N
            if rings[k][i] == rings[k + 1][i] and rings[k][j] == rings[k + 1][j]:
                continue                                   # identical rings -> degenerate strip, skip
            if k == DOOR_STRIP and i in DOOR_SEGS:
                continue                                   # the doorway surface replaces these two panels
            quad(lo[i], hi[i], hi[j], lo[j], tile)

    # ---- THE DOORWAY -------------------------------------------------------------------------------
    # Replaces the two south panels of the plinth strip with: a FRAME (the wall, with a rectangular
    # hole), the RECESS side walls, and the recess BACK face.
    #
    # THE MANIFOLD TRICK: the frame is a quad STRIP between two 6-vertex loops, not an ad-hoc
    # triangulation of a polygon-with-a-hole. The outer loop is exactly the boundary of the two panels
    # being replaced -- SAME vertices, no new points on the shared edges -- so the neighbouring strips
    # still find each of their edges used exactly once (add a vertex mid-edge here and you get a
    # T-junction, i.e. an edge with only one face, and the closedness gate fails). The inner loop
    # traces the door opening with the same 6-fold structure, so the annulus is a plain strip and the
    # winding follows the SAME derived rule as every other strip. Extruding the inner loop inward and
    # capping it closes the cavity.
    lo, hi = ring_idx[DOOR_STRIP], ring_idx[DOOR_STRIP + 1]
    i5, i6, i7 = DOOR_SEGS[0], DOOR_SEGS[1], (DOOR_SEGS[1] + 1) % RING_N
    # the outer boundary, in the same rotational sense the two replaced quads traced
    B = [lo[i5], hi[i5], hi[i6], hi[i7], lo[i7], lo[i6]]
    zS = verts[lo[i6]][2]                                  # the south wall plane
    yb, yt = S.ground_y + DOOR_SILL, S.ground_y + DOOR_TOP
    cxa = S.anchor[0]
    inner = [(cxa - DOOR_HALF_W, yb), (cxa - DOOR_HALF_W, yt), (cxa, yt),
             (cxa + DOOR_HALF_W, yt), (cxa + DOOR_HALF_W, yb), (cxa, yb)]
    I = [add((x, y, zS)) for (x, y) in inner]
    J = [add((x, y, zS + DOOR_DEPTH)) for (x, y) in inner]  # the recess, sunk INTO the wall
    for k in range(6):                                      # frame: outer loop -> opening rim
        quad(B[k], B[(k + 1) % 6], I[(k + 1) % 6], I[k], TILE_STONE)
    for k in range(6):                                      # jambs / lintel underside / threshold
        quad(I[k], I[(k + 1) % 6], J[(k + 1) % 6], J[k], TILE_DOOR)
    # The recess BACK face. NOT a fan: the J loop is a rectangle carrying collinear mid-points on its
    # top and bottom edges, so a fan from ANY corner emits one zero-area sliver along the edge its apex
    # sits on. Triangulate it as a 2-quad strip pairing top points to bottom points instead.
    du0, dv0, du1, dv1 = TILE_DOOR
    for (a, b, c, d) in ((J[0], J[1], J[2], J[5]), (J[5], J[2], J[3], J[4])):
        faces.append([a, b, c]); uvs.extend([(du0, dv0), (du0, dv1), (du1, dv1)])
        faces.append([a, c, d]); uvs.extend([(du0, dv0), (du1, dv1), (du1, dv0)])

    # ---- THE ENTRANCE STEPS ------------------------------------------------------------------------
    # Two shallow treads, each its OWN closed box. Separate components are fine: the gates check that
    # every edge has exactly 2 faces and every DIRECTED edge exactly one, which holds per component,
    # and the signed volumes simply add. Each box is buried to the skirt depth (no face on the ground
    # plane) and pokes STEP_BACK into the wall so there is no visible crack at the join -- that back
    # face ends up inside the solid plinth, below the door threshold, so it is never seen.
    for (half_w, top_h, out) in STEP_TIERS:
        _box_solid(add, faces, uvs, verts,
                   cxa - half_w, cxa + half_w,
                   S.ground_y - SKIRT_BURY, S.ground_y + top_h,
                   zS - out, zS + STEP_BACK, TILE_STONE)

    # pyramid roof: the eave ring collapsed to a single apex (the same rule, U[i]==U[j]==apex)
    apex = add((S.anchor[0], S.ground_y + APEX_Y, S.anchor[1]))
    top = ring_idx[-1]
    u0, v0, u1, v1 = TILE_STONE
    for i in range(RING_N):
        faces.append([top[i], apex, top[(i + 1) % RING_N]])
        uvs.extend([(u0, v0), ((u0 + u1) / 2.0, v1), (u1, v0)])

    # bottom cap: fan the buried base ring in the SAME t order -> normal is -up (downward).
    # Buried, so it is never seen; it exists only to keep the solid CLOSED.
    bot = ring_idx[0]
    for i in range(1, RING_N - 1):
        faces.append([bot[0], bot[i], bot[i + 1]])
        uvs.extend([(u0, v0), (u1, v0), (u1, v1)])

    normals = [_normal([verts[i] for i in f]) for f in faces]
    return verts, faces, normals, uvs


def _assert_closed_solid(verts, faces) -> dict:
    """Prove the mesh is a closed 2-manifold with consistent outward winding.

    Welds coincident positions first (the ring construction shares corners exactly), then checks that
    every undirected edge is used by exactly 2 faces AND that each such edge is traversed in OPPOSITE
    directions by them -- the standard orientability test. A mesh that passes cannot show a culled
    hole from any viewing angle."""
    key = {}
    weld = []
    for v in verts:
        k = (round(v[0], 5), round(v[1], 5), round(v[2], 5))
        if k not in key:
            key[k] = len(weld)
            weld.append(k)
    idx = [key[(round(v[0], 5), round(v[1], 5), round(v[2], 5))] for v in verts]

    directed = defaultdict(int)
    undirected = defaultdict(int)
    degenerate = 0
    for f in faces:
        w = [idx[i] for i in f]
        if len(set(w)) < 3:
            degenerate += 1
            continue
        for a, b in ((w[0], w[1]), (w[1], w[2]), (w[2], w[0])):
            directed[(a, b)] += 1
            undirected[(min(a, b), max(a, b))] += 1
    bad_count = {e: c for e, c in undirected.items() if c != 2}
    bad_orient = {e: c for e, c in directed.items() if c != 1}
    return {"welded_verts": len(weld), "edges": len(undirected), "degenerate": degenerate,
            "non_manifold_edges": bad_count, "misoriented_edges": bad_orient}


def gates(S, verts, faces, normals, uvs) -> int:
    bad = 0

    def check(ok, label, detail=""):
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}{('  -- ' + detail) if detail else ''}")

    print("\n=== BEACON GATES ===")
    xs = [v[0] for v in verts]; ys = [v[1] for v in verts]; zs = [v[2] for v in verts]
    print(f"  world bbox x[{min(xs):.3f},{max(xs):.3f}] y[{min(ys):.3f},{max(ys):.3f}] "
          f"z[{min(zs):.3f},{max(zs):.3f}]")
    print(f"  {len(verts)} verts (unwelded), {len(faces)} tris, footprint "
          f"{max(xs) - min(xs):.2f} x {max(zs) - min(zs):.2f}, height above ground "
          f"{max(ys) - S.ground_y:.2f}u, buried {S.ground_y - min(ys):.2f}u")

    m = _assert_closed_solid(verts, faces)
    check(m["degenerate"] == 0, "no degenerate triangles (repeated vertex)", f"{m['degenerate']} found")
    check(not m["non_manifold_edges"], "CLOSED: every edge shared by exactly 2 faces",
          f"{len(m['non_manifold_edges'])} bad edges")
    check(not m["misoriented_edges"], "ORIENTABLE: every directed edge used exactly once "
          "(consistent winding, no flipped face)", f"{len(m['misoriented_edges'])} bad")
    check(len(normals) == len(faces), "one normal per face", f"{len(normals)} vs {len(faces)}")

    # ORIENTATION: closed + orientable + positive signed volume == every face faces OUTWARD.
    # This is the anti-back-face-culling guarantee, and it is a GLOBAL test on purpose (the gallery
    # overhang makes the mesh non-convex, so no single-interior-point per-face test is valid).
    vol = _signed_volume(verts, faces, (S.anchor[0], S.ground_y, S.anchor[1]))
    check(vol > 0.0, "OUTWARD: signed volume positive -> nothing culls from any viewing angle",
          f"volume {vol:+.3f} u^3")
    up_f = sum(1 for n in normals if n[1] > 0.5)
    dn_f = sum(1 for n in normals if n[1] < -0.5)
    print(f"         faces: {up_f} up, {dn_f} down (buried cap + gallery overhang underside), "
          f"{len(faces) - up_f - dn_f} vertical")

    # anti-z-fight: no face may lie IN the ground plane
    coplanar = [i for i, f in enumerate(faces)
                if all(abs(verts[k][1] - S.ground_y) < 1e-6 for k in f)]
    check(not coplanar, f"no face coplanar with the ground plane y={S.ground_y}", f"{len(coplanar)} faces")
    check(min(ys) < S.ground_y - 1e-6, "the skirt is BURIED (lowest point below ground)",
          f"lowest {min(ys):.3f} vs ground {S.ground_y}")
    check(len([i for i, f in enumerate(faces) if all(verts[k][1] < S.ground_y for k in f)]) > 0,
          "at least one face entirely below ground (the buried bottom cap)")

    # budget + legibility (raised from 250 in pass 5: the doorway + steps are worth ~48 tris and are
    # the whole point of that pass -- the tower body itself is unchanged at 204)
    check(100 <= len(faces) <= 320, "tri count inside the 100-320 budget", str(len(faces)))
    check(4.0 <= max(xs) - min(xs) <= 5.0, "footprint 4-5u wide (x)", f"{max(xs) - min(xs):.2f}u")
    check(4.0 <= max(zs) - min(zs) <= 5.5, "footprint 4-5.5u deep (z) -- ASYMMETRIC by design, the "
          "entrance steps project south", f"{max(zs) - min(zs):.2f}u")
    check(9.0 <= max(ys) - S.ground_y <= 11.0, "height 9-11u above ground",
          f"{max(ys) - S.ground_y:.2f}u")

    # panel scale for the atlas stamp (~1-2u; the stamp does not rescale)
    areas = []
    for f in faces:
        a, b, c = (verts[i] for i in f)
        u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        areas.append(0.5 * math.sqrt(sum(k * k for k in n)))
    print(f"         face area: min {min(areas):.4f} max {max(areas):.2f} mean "
          f"{sum(areas) / len(areas):.2f} u^2  (panel edge ~{math.sqrt(2 * max(areas)):.1f}u)")
    check(max(areas) < 8.0, "largest panel under 8 u^2 (keeps the atlas tile from smearing)",
          f"max {max(areas):.2f}")
    # SLIVERS: the degeneracy check above only catches a REPEATED vertex. A triangle whose 3 DISTINCT
    # vertices are collinear has zero area and slips straight through it -- exactly what the recess
    # cap's first fan triangulation produced. Check the geometry, not just the indices.
    check(min(areas) > 1e-6, "no zero-area sliver (3 distinct but COLLINEAR vertices)",
          f"min {min(areas):.3e} u^2")

    # SITING -- the trigger-at-the-foot law, enforced HERE where the anchor is chosen (a gate that
    # only lives in the probe is a gate the next re-site can forget)
    tx0, tx1, tz0, tz1 = S.trigger_bbox
    fx0, fx1, fz0, fz1 = min(xs), max(xs), min(zs), max(zs)
    overlap = not (fx1 < tx0 or fx0 > tx1 or fz1 < tz0 or fz0 > tz1)
    check(not overlap, "the footprint does NOT overlap the trigger rect")
    gap = fz0 - tz1                       # footprint's south edge vs the trigger's north edge
    check(gap >= HULL_CLEARANCE, f"footprint >= {HULL_CLEARANCE}u clear of the trigger rect "
          f"(so the hull split can never touch a trigger tri)", f"gap {gap:+.2f}u")
    check(gap < 3.0, "...but CLOSE enough that the trigger reads as being at the tower's foot",
          f"gap {gap:+.2f}u")
    ddx = max(fx0 - S.arrive[0], 0.0, S.arrive[0] - fx1)
    ddz = max(fz0 - S.arrive[1], 0.0, S.arrive[1] - fz1)
    adist = math.hypot(ddx, ddz)
    check(adist >= ARRIVE_CLEARANCE, f"arrive point {S.arrive} >= {ARRIVE_CLEARANCE}u from the "
          f"footprint (a solid footprint is spawn-fragile)", f"{adist:.3f}u")
    bx0, bx1, bz0, bz1 = S.block
    check(bx0 <= fx0 and fx1 <= bx1 and bz0 <= fz0 and fz1 <= bz1,
          "footprint inside block (0,18)", f"N margin {bz1 - fz1:.2f}u, S margin {fz0 - bz0:.2f}u")

    # UVs -- the failure that renders flat white
    check(len(uvs) == 3 * len(faces), "one UV per face corner", f"{len(uvs)} vs {3 * len(faces)}")
    check(all(any(abs(c) > 1e-6 for c in u) for u in uvs), "no degenerate [0,0] UV (would render white)")
    check(all(0.0 <= u[0] <= 1.0 and 0.0 <= u[1] <= 1.0 for u in uvs), "every UV inside [0,1]")
    # Count by the FULL rect, not by U alone: TILE_DOOR's U range sits INSIDE TILE_LANTERN's, so a
    # U-only test silently reported the 48 door corners as lantern corners.
    def _in_rect(u, r):
        return r[0] - 1e-9 <= u[0] <= r[2] + 1e-9 and r[1] - 1e-9 <= u[1] <= r[3] + 1e-9
    n_stone = sum(1 for u in uvs if _in_rect(u, TILE_STONE))
    n_lan = sum(1 for u in uvs if _in_rect(u, TILE_LANTERN))
    n_door = sum(1 for u in uvs if _in_rect(u, TILE_DOOR))
    check(n_stone + n_lan + n_door == len(uvs), "every UV belongs to one of the 3 authored tiles",
          f"{n_stone}+{n_lan}+{n_door} vs {len(uvs)}")
    check(n_lan > 0, "the lantern room got its own warm tile", f"{n_lan // 3} tris")
    check(n_door > 0, "the doorway recess got the dark tile", f"{n_door // 3} tris")
    print(f"         tiles: stone {n_stone // 3} tris {tuple(round(c, 4) for c in TILE_STONE)} | "
          f"lantern {n_lan // 3} {tuple(round(c, 4) for c in TILE_LANTERN)} | "
          f"door {n_door // 3} {tuple(round(c, 4) for c in TILE_DOOR)}")

    # THE ENTRANCE FACE -- the asymmetry is the feature, so assert it rather than trusting the build
    south_z = min(zs)
    door_faces = [i for i, f in enumerate(faces)
                  if all(abs(verts[k][2] - (S.anchor[1] - 2.30)) < 1e-6 for k in f)]
    recess = [i for i, f in enumerate(faces)
              if all(verts[k][2] > S.anchor[1] - 2.30 + 1e-6 for k in f)
              and all(verts[k][2] < S.anchor[1] - 2.30 + DOOR_DEPTH + 1e-6 for k in f)
              and all(S.ground_y + DOOR_SILL - 1e-6 <= verts[k][1] <= S.ground_y + DOOR_TOP + 1e-6 for k in f)]
    check(len(door_faces) >= 12, "a frame surface exists on the south wall plane",
          f"{len(door_faces)} coplanar faces")
    check(len(recess) >= 4, "the recess is sunk INTO the wall (faces behind the south plane)",
          f"{len(recess)} faces at depth")
    check(abs(south_z - (S.anchor[1] - 2.30 - STEP_OUT)) < 1e-6,
          f"the steps project exactly {STEP_OUT}u south of the plinth face",
          f"southmost {south_z:.3f}")
    north_z = max(zs)
    check(abs(north_z - (S.anchor[1] + 2.30)) < 1e-6,
          "the OTHER three faces are untouched (north face still at the plain plinth line)",
          f"northmost {north_z:.3f}")
    return bad


def write_obj(S, verts, faces, normals, uvs, path: Path) -> Path:
    """Write the beacon as a Wavefront OBJ with per-face-corner UVs and per-face normals.

    The UVs are OURS (authored per panel against the shared object atlas), so no deploy-time stamp is
    needed or wanted: `build_from_obj` carries `vt` straight through, and `stamp_uv_rect`'s
    ``only_zero`` guard would skip these faces anyway. That keeps the texture deterministic and
    reviewable in this file rather than depending on a learned palette's modal pick."""
    out = ["# ff9mapkit -- THE LANTERN BEACON (Southern Ring quay marker)",
           "# GENERATED by studies/overworld-topography/southern-ring/mint_quay_beacon.py -- do not hand-edit.",
           "# Original procedural geometry (no game bytes). WORLD coords, Y up; "
           f"ground plane y={S.ground_y:.2f} (skirt buried {SKIRT_BURY:.2f}u).",
           "# UVs index the shared res(1_24)_objects atlas: stone shaft + warm lantern room.",
           "o LanternBeacon"]
    out += [f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}" for v in verts]
    out += [f"vt {u[0]:.6f} {u[1]:.6f}" for u in uvs]
    out += [f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}" for n in normals]
    for fi, f in enumerate(faces):
        out.append("f " + " ".join(f"{v + 1}/{fi * 3 + c + 1}/{fi + 1}"
                                   for c, v in enumerate(f)))
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path


def build_site(key: str) -> int:
    """Generate + gate one site's beacon. Returns the failure count (0 = clean)."""
    S = SITES[key]
    print("=" * 100)
    print(f"{S.name.upper()}  anchor {S.anchor}  ground y {S.ground_y}  cell {S.cell}  "
          f"arrive {S.arrive} face {S.arrive_face}")
    print("=" * 100)
    verts, faces, normals, uvs = build_beacon(S)
    bad = gates(S, verts, faces, normals, uvs)
    if bad:
        print(f"\n{S.name}: GATES FAILED ({bad}) -- nothing written.", file=sys.stderr)
        return bad
    path = write_obj(S, verts, faces, normals, uvs, obj_path(S))
    print(f"\nwrote {path}  ({len(verts)} verts, {len(faces)} tris, {len(uvs)} uvs)")
    print(f"  deploy with --building-at {S.anchor[0]:g} {S.anchor[1]:g} --no-seat --building-idall 4078")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", choices=sorted(SITES) + ["all"], default="all",
                    help="which quay to generate (default: all four)")
    ap.add_argument("--tile-uv", action="store_true", help="also print the chosen atlas tile rects")
    args = ap.parse_args()

    keys = sorted(SITES) if args.site == "all" else [args.site]
    bad = sum(build_site(k) for k in keys)
    if args.tile_uv:
        for nm, t in (("stone  ", TILE_STONE), ("lantern", TILE_LANTERN), ("door   ", TILE_DOOR)):
            print(f"  {nm} tile-uv {t[0]:.6f},{t[1]:.6f},{t[2]:.6f},{t[3]:.6f}")
    print("\n" + ("ALL SITES CLEAN" if not bad else f"{bad} GATE FAILURE(S)"))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
