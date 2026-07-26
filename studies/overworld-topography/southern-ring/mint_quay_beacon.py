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

    Footprint 4.60 x 4.60 u, height 10.60 u above ground (+0.50 u buried skirt), 206 triangles --
    inside the 100-250 tri budget, and in the stock landmark legibility band (harbour gate 5.5u reads
    small, Alexandria castle 16.8u; ~10u is a landmark you notice without dwarfing the cell).

PLACEMENT / COLLISION (the proven building-layer laws -- OVERWORLD_ENGINE.md:405-414)
    This mesh is the RENDER-ONLY Object layer. Collision is NOT this mesh -- it is the TERRAIN under
    the mesh's convex hull, stamped topograph 59 by `split_retarget_by_polygon`, which conforms to the
    ground and has zero render effect (UV-only). `world-entrance --building` does both halves.

    ⚠ ON THIS CELL "render-only" IS NOT AUTOMATIC -- see the block comment in `mint_quay_beacon_deploy`
    below. Block (0,18)'s reclaim donor (0,0) HAS a stock Object component, so the engine DOES feed an
    Object override to `AddWalkMeshForm1`. The Object mesh therefore has to be stamped IDALL 4078
    (the `WMPhysics.Raycast` skip id) to actually BE render-only here.

    Authored in WORLD coords with the ground plane at y = 3.00 (Block[0][18]'s measured flat plateau),
    so the deploy uses `--no-seat`: seating would put the LOWEST point on the ground and un-bury the
    skirt, reintroducing the coplanar bottom cap.

USAGE
    py studies/overworld-topography/southern-ring/mint_quay_beacon.py            # write the OBJ + gates
    py studies/overworld-topography/southern-ring/mint_quay_beacon.py --tile-uv  # print the atlas rect
"""
from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))

# ---- siting (world coords) -------------------------------------------------------------------------
ANCHOR = (48.0, -1157.0)        # XZ centre; the lawful window between the quay trigger and the block edge
GROUND_Y = 3.00                 # Block[0][18]'s measured plateau
SKIRT_BURY = 0.50               # how far the plinth base sits BELOW the ground plane

OBJ_OUT = HERE / "quay_beacon.obj"

# ---- the profile: (y above ground, half-width) ------------------------------------------------------
# A pair of rings at the same y with different half-widths makes a horizontal step (a plinth lip, a
# gallery ledge, a roof eave). Consecutive rings at different y make a wall or a taper.
PROFILE = [
    (-SKIRT_BURY, 2.30),        # buried skirt base
    (0.00, 2.30),               # ground line (a ring here, so no face STRADDLES the terrain plane)
    (1.30, 2.30),               # plinth top
    (1.30, 1.80),               # step in to the shaft
    (2.72, 1.68),               # shaft, 4 bands of ~1.4u -- tapering
    (4.15, 1.55),
    (5.57, 1.43),
    (7.00, 1.30),               # shaft top
    (7.00, 2.10),               # gallery ledge out
    (7.85, 2.10),               # gallery top
    (7.85, 1.40),               # step in to the lantern head
    (8.85, 1.40),               # lantern, 2 bands of 1.0u
    (9.85, 1.40),               # lantern top
    (9.85, 1.60),               # roof eave out
]
APEX_Y = 10.60                  # pyramid roof apex

RING_N = 8                      # 8 perimeter points = a square with edge midpoints (2 panels per side)

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

# which ring-strips are the lantern room (0-based strip k joins PROFILE[k] -> PROFILE[k+1])
LANTERN_STRIPS = {10, 11}


def _ring(y: float, half: float):
    """A square ring of ``RING_N`` points at height ``y``, half-width ``half``, centred on ``ANCHOR``
    in WORLD XZ (the whole mesh is authored world-positioned, so the deploy needs no seating)."""
    pts = []
    for i in range(RING_N):
        t = 2.0 * math.pi * i / RING_N
        # Chebyshev normalisation turns the unit circle into a unit SQUARE, keeping the 8 points
        # evenly distributed as 4 corners + 4 edge midpoints.
        cx, cz = math.cos(t), math.sin(t)
        m = max(abs(cx), abs(cz))
        pts.append((ANCHOR[0] + half * cx / m, y, ANCHOR[1] + half * cz / m))
    return pts


def _normal(face_pts):
    """The unit geometric normal of a triangle, from its winding (right-hand rule)."""
    a, b, c = face_pts
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
    L = math.sqrt(sum(k * k for k in n)) or 1.0
    return (n[0] / L, n[1] / L, n[2] / L)


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


def build_beacon():
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
    rings = [_ring(GROUND_Y + y, h) for (y, h) in PROFILE]
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
            quad(lo[i], hi[i], hi[j], lo[j], tile)

    # pyramid roof: the eave ring collapsed to a single apex (the same rule, U[i]==U[j]==apex)
    apex = add((ANCHOR[0], GROUND_Y + APEX_Y, ANCHOR[1]))
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


def gates(verts, faces, normals, uvs) -> int:
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
          f"{max(ys) - GROUND_Y:.2f}u, buried {GROUND_Y - min(ys):.2f}u")

    m = _assert_closed_solid(verts, faces)
    check(m["degenerate"] == 0, "no degenerate triangles", f"{m['degenerate']} found")
    check(not m["non_manifold_edges"], "CLOSED: every edge shared by exactly 2 faces",
          f"{len(m['non_manifold_edges'])} bad edges")
    check(not m["misoriented_edges"], "ORIENTABLE: every directed edge used exactly once "
          "(consistent winding, no flipped face)", f"{len(m['misoriented_edges'])} bad")
    check(len(normals) == len(faces), "one normal per face", f"{len(normals)} vs {len(faces)}")

    # ORIENTATION: closed + orientable + positive signed volume == every face faces OUTWARD.
    # This is the anti-back-face-culling guarantee, and it is a GLOBAL test on purpose (the gallery
    # overhang makes the mesh non-convex, so no single-interior-point per-face test is valid).
    vol = _signed_volume(verts, faces, (ANCHOR[0], GROUND_Y, ANCHOR[1]))
    check(vol > 0.0, "OUTWARD: signed volume positive -> nothing culls from any viewing angle",
          f"volume {vol:+.3f} u^3")
    up_f = sum(1 for n in normals if n[1] > 0.5)
    dn_f = sum(1 for n in normals if n[1] < -0.5)
    print(f"         faces: {up_f} up, {dn_f} down (buried cap + gallery overhang underside), "
          f"{len(faces) - up_f - dn_f} vertical")

    # anti-z-fight: no face may lie IN the ground plane
    coplanar = [i for i, f in enumerate(faces)
                if all(abs(verts[k][1] - GROUND_Y) < 1e-6 for k in f)]
    check(not coplanar, f"no face coplanar with the ground plane y={GROUND_Y}", f"{len(coplanar)} faces")
    check(min(ys) < GROUND_Y - 1e-6, "the skirt is BURIED (lowest point below ground)",
          f"lowest {min(ys):.3f} vs ground {GROUND_Y}")
    check(len([i for i, f in enumerate(faces) if all(verts[k][1] < GROUND_Y for k in f)]) > 0,
          "at least one face entirely below ground (the buried bottom cap)")

    # budget + legibility
    check(100 <= len(faces) <= 250, "tri count inside the 100-250 budget", str(len(faces)))
    check(4.0 <= max(xs) - min(xs) <= 5.0 and 4.0 <= max(zs) - min(zs) <= 5.0,
          "footprint 4-5u square")
    check(9.0 <= max(ys) - GROUND_Y <= 11.0, "height 9-11u above ground",
          f"{max(ys) - GROUND_Y:.2f}u")

    # panel scale for the atlas stamp (~1-2u; the stamp does not rescale)
    areas = []
    for f in faces:
        a, b, c = (verts[i] for i in f)
        u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        areas.append(0.5 * math.sqrt(sum(k * k for k in n)))
    print(f"         face area: min {min(areas):.2f} max {max(areas):.2f} mean "
          f"{sum(areas) / len(areas):.2f} u^2  (panel edge ~{math.sqrt(2 * max(areas)):.1f}u)")
    check(max(areas) < 8.0, "largest panel under 8 u^2 (keeps the atlas tile from smearing)",
          f"max {max(areas):.2f}")

    # UVs -- the failure that renders flat white
    check(len(uvs) == 3 * len(faces), "one UV per face corner", f"{len(uvs)} vs {3 * len(faces)}")
    check(all(any(abs(c) > 1e-6 for c in u) for u in uvs), "no degenerate [0,0] UV (would render white)")
    check(all(0.0 <= u[0] <= 1.0 and 0.0 <= u[1] <= 1.0 for u in uvs), "every UV inside [0,1]")
    used = {(round(min(u[0] for u in uvs), 4), round(max(u[0] for u in uvs), 4))}
    lan = sum(1 for u in uvs if TILE_LANTERN[0] - 1e-9 <= u[0] <= TILE_LANTERN[2] + 1e-9)
    check(lan > 0, "the lantern room got its own warm tile", f"{lan // 3} tris warm, "
          f"{len(faces) - lan // 3} stone")
    print(f"         UV span u{used} -> 2 tiles: stone {tuple(round(c, 4) for c in TILE_STONE)}, "
          f"lantern {tuple(round(c, 4) for c in TILE_LANTERN)}")
    return bad


def write_obj(verts, faces, normals, uvs, path: Path) -> Path:
    """Write the beacon as a Wavefront OBJ with per-face-corner UVs and per-face normals.

    The UVs are OURS (authored per panel against the shared object atlas), so no deploy-time stamp is
    needed or wanted: `build_from_obj` carries `vt` straight through, and `stamp_uv_rect`'s
    ``only_zero`` guard would skip these faces anyway. That keeps the texture deterministic and
    reviewable in this file rather than depending on a learned palette's modal pick."""
    out = ["# ff9mapkit -- THE LANTERN BEACON (Southern Ring quay marker)",
           "# GENERATED by studies/overworld-topography/southern-ring/mint_quay_beacon.py -- do not hand-edit.",
           "# Original procedural geometry (no game bytes). WORLD coords, Y up; "
           f"ground plane y={GROUND_Y:.2f} (skirt buried {SKIRT_BURY:.2f}u).",
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tile-uv", action="store_true", help="also print the chosen atlas tile rect")
    args = ap.parse_args()

    verts, faces, normals, uvs = build_beacon()
    if gates(verts, faces, normals, uvs):
        print("\nGATES FAILED -- nothing written.", file=sys.stderr)
        return 1
    write_obj(verts, faces, normals, uvs, OBJ_OUT)
    print(f"\nwrote {OBJ_OUT}  ({len(verts)} verts, {len(faces)} tris, {len(uvs)} uvs)")
    print(f"  anchor {ANCHOR}, ground y {GROUND_Y}, authored in WORLD coords -> deploy with --no-seat")
    if args.tile_uv:
        print(f"  stone   tile-uv {TILE_STONE[0]:.6f},{TILE_STONE[1]:.6f},"
              f"{TILE_STONE[2]:.6f},{TILE_STONE[3]:.6f}")
        print(f"  lantern tile-uv {TILE_LANTERN[0]:.6f},{TILE_LANTERN[1]:.6f},"
              f"{TILE_LANTERN[2]:.6f},{TILE_LANTERN[3]:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
