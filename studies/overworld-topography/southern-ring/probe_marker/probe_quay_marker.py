"""READ-ONLY acceptance probe for THE LANTERN QUAY MARKER -- reads the DEPLOYED install bytes, both discs.

Four checks, per the marker design (donor = Alexandria Harbour, Block[21][10] Object):
  (a) the quay TRIGGER is untouched -- 6 tris, idall 16384, union bbox x[44,52] z[-1172,-1164];
      the ground query at (48,-1168) still resolves to idall 16384.
  (b) the ARRIVE point (60,-1168) is untouched -- idall 0, topograph 0, y 3.00, in BOTH query
      modes (a sky-cast sets WMPhysics.IgnoreExceptions=true, so the 4078 skip does NOT protect it).
  (c) the MARKER is present -- the whole 104-tri / 312-vert donor part, every tri idall 4078,
      per-face normal-Y distribution identical to the donor's (34 up / 60 vertical / 10 down -- a
      harbour gate, and a pure translation must not change a single face normal), world span inside
      the planned footprint and outside BOTH exclusions.
  (d) the UV carry landed -- one UV per vertex, none degenerate, the U/V sets byte-equal to the donor's
      (a carry that drops UVs renders flat WHITE off the atlas's alpha-0 corner).

Plus the behavioural pair the 4078 stamp buys: the walk-convention ground query (WMPhysics skips
4078/4088/2040) must NOT see the marker, while the IgnoreExceptions query must.

Run:  py studies/overworld-topography/southern-ring/probe_marker/probe_quay_marker.py
"""
from __future__ import annotations

import collections
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit.world import extract as W                      # noqa: E402
from ff9mapkit.world import mesh as M                         # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
MOD = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap"
BX, BY = 0, 18
OX, OZ = W.block_world_origin(BX, BY)

DONOR_BLOCK = (21, 10)
DONOR_TRIS, DONOR_VERTS = 104, 312
MARKER_IDALL = 4078
TRIGGER_IDALL = 16384
TRIGGER_TRIS = 6
TRIGGER_BBOX = (44.0, 52.0, -1172.0, -1164.0)
EXCLUSION = (42.0, 54.0, -1174.0, -1162.0)
PLANNED_SPAN = (44.861, 51.139, -1161.193, -1152.807)     # x0,x1,z0,z1
SPAN_TOL = 0.01
BASE_Y = 3.00
ARRIVE = (60.0, -1168.0)
ARRIVE_CLEARANCE = 6.0
POST_PROBE = (48.0, -1157.0)                              # the gate's centre -- where to test walk-through
IDALL_SKIP = {4078, 4088, 2040}

FAILURES: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    if not ok:
        FAILURES.append(label)
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{('  -- ' + detail) if detail else ''}")


def idall_of(bm, t: int) -> int:
    return int(round(bm.tangents[bm.flat_index[3 * t]][0]))


def tri_pts(bm, t: int, ox: float = OX, oz: float = OZ):
    return [(bm.verts[k][0] + ox, bm.verts[k][1], bm.verts[k][2] + oz) for k in bm.tris[t]]


def ny_of(pts) -> float:
    a, b, c = pts
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    return ny / (math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0)


def ground(parts, wx: float, wz: float, *, ignore_exceptions: bool = False):
    """The engine's ground query: first mesh in load order, first tri in buffer order, up-facing winding.
    ``ignore_exceptions`` mirrors WMPhysics.IgnoreExceptions=true (the sky-cast placement paths)."""
    for (nm, bm) in parts:
        for t in range(len(bm.tris)):
            i = idall_of(bm, t)
            if not ignore_exceptions and i in IDALL_SKIP:
                continue
            a, b, c = tri_pts(bm, t)
            if not ignore_exceptions and ny_of((a, b, c)) <= 0.1:
                continue
            d = (b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])
            if abs(d) < 1e-12:
                continue
            w1 = ((wx - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (wz - a[2])) / d
            w2 = ((b[0] - a[0]) * (wz - a[2]) - (wx - a[0]) * (b[2] - a[2])) / d
            if w1 < -1e-9 or w2 < -1e-9 or w1 + w2 > 1 + 1e-9:
                continue
            return (nm, a[1] + w1 * (b[1] - a[1]) + w2 * (c[1] - a[1]), i, t)
    return None


donor = W.read_block(*DONOR_BLOCK, disc=1, lod="0_1", part="object")
donor_ny = sorted(round(ny_of([tuple(donor.verts[k]) for k in donor.tris[t]]), 4) for t in range(len(donor.tris)))
donor_u = sorted({round(u[0], 6) for u in donor.uvs})
donor_v = sorted({round(u[1], 6) for u in donor.uvs})
print(f"donor Block{list(DONOR_BLOCK)} Object: {donor.vcount} verts / {len(donor.tris)} tris, "
      f"idall={sorted({idall_of(donor, t) for t in range(len(donor.tris))})}, "
      f"normal-Y up={sum(1 for n in donor_ny if n > 0.5)} vert={sum(1 for n in donor_ny if abs(n) <= 0.5)} "
      f"down={sum(1 for n in donor_ny if n < -0.5)}\n")

for disc in (1, 4):
    print("=" * 100)
    print(f"DISC {disc}  --  {MOD / f'Disc{disc}' / '0_1' / 'r18'}")
    print("=" * 100)
    ter_p = MOD / f"Disc{disc}" / "0_1" / "r18" / "Block[0][18] Terrain.ff9mesh"
    obj_p = MOD / f"Disc{disc}" / "0_1" / "r18" / "Block[0][18] Object.ff9mesh"
    ter = M.blockmesh_from_ff9mesh(str(ter_p), disc=disc, x=BX, y=BY, part="terrain")
    obj = M.blockmesh_from_ff9mesh(str(obj_p), disc=disc, x=BX, y=BY, part="object")
    print(f"Terrain {ter_p.stat().st_size} B: {ter.vcount} verts / {len(ter.tris)} tris")
    print(f"Object  {obj_p.stat().st_size} B: {obj.vcount} verts / {len(obj.tris)} tris")
    parts = [("Object", obj), ("Terrain", ter)]

    # ---- (a) the trigger, untouched -----------------------------------------------------------------
    print("\n(a) the quay TRIGGER cluster (Terrain) is untouched")
    ev = [t for t in range(len(ter.tris)) if W.decode_id(idall_of(ter, t))["event"]]
    check(len(ev) == TRIGGER_TRIS, f"exactly {TRIGGER_TRIS} event tris", f"got {len(ev)}")
    check({idall_of(ter, t) for t in ev} == {TRIGGER_IDALL}, f"all carry idall {TRIGGER_IDALL}",
          str(sorted({idall_of(ter, t) for t in ev})))
    pts = [p for t in ev for p in tri_pts(ter, t)]
    bb = (min(p[0] for p in pts), max(p[0] for p in pts), min(p[2] for p in pts), max(p[2] for p in pts))
    check(all(abs(a - b) < 1e-6 for a, b in zip(bb, TRIGGER_BBOX)),
          f"union bbox == x[{TRIGGER_BBOX[0]:.0f},{TRIGGER_BBOX[1]:.0f}] z[{TRIGGER_BBOX[2]:.0f},{TRIGGER_BBOX[3]:.0f}]",
          f"got x[{bb[0]:.2f},{bb[1]:.2f}] z[{bb[2]:.2f},{bb[3]:.2f}]")
    g = ground(parts, 48.0, -1168.0)
    check(g is not None and g[2] == TRIGGER_IDALL and abs(g[1] - 3.0) < 1e-6,
          f"ground query (48,-1168) -> idall {TRIGGER_IDALL} @ y 3.00",
          "MISS" if g is None else f"{g[0]} idall={g[2]} y={g[1]:.3f}")

    # ---- (b) the arrive point, untouched, in BOTH modes ----------------------------------------------
    print("\n(b) the ARRIVE point (60,-1168) is untouched -- a sky-cast IGNORES the 4078 skip")
    for mode, ie in (("walk (skip 4078)", False), ("sky-cast (IgnoreExceptions)", True)):
        g = ground(parts, *ARRIVE, ignore_exceptions=ie)
        ok = g is not None and g[0] == "Terrain" and g[2] == 0 and abs(g[1] - 3.0) < 1e-6
        check(ok, f"{mode}: Terrain, idall 0, topo 0, y 3.00",
              "MISS" if g is None else f"{g[0]} idall={g[2]} topo={W.decode_id(g[2])['topograph']} y={g[1]:.3f}")

    # ---- (c) the marker ------------------------------------------------------------------------------
    print("\n(c) the MARKER geometry")
    ids = collections.Counter(idall_of(obj, t) for t in range(len(obj.tris)))
    check(len(obj.tris) == DONOR_TRIS and obj.vcount == DONOR_VERTS,
          f"the WHOLE donor part landed ({DONOR_TRIS} tris / {DONOR_VERTS} verts)",
          f"got {len(obj.tris)} tris / {obj.vcount} verts")
    check(set(ids) == {MARKER_IDALL}, f"EVERY tri carries idall {MARKER_IDALL} (0x{MARKER_IDALL:04X})",
          str(dict(ids)))
    print(f"       decoded {MARKER_IDALL} = {W.decode_id(MARKER_IDALL)}   "
          f"(donor was 6382 = {W.decode_id(6382)} -- same topograph + flags, area only)")
    nys = sorted(round(ny_of(tri_pts(obj, t)), 4) for t in range(len(obj.tris)))
    check(nys == donor_ny, "per-face normal-Y distribution == the donor's (pure translation, no face altered)",
          f"up={sum(1 for n in nys if n > 0.5)} vertical={sum(1 for n in nys if abs(n) <= 0.5)} "
          f"down={sum(1 for n in nys if n < -0.5)}")
    allp = [p for t in range(len(obj.tris)) for p in tri_pts(obj, t)]
    xs = [p[0] for p in allp]; ys = [p[1] for p in allp]; zs = [p[2] for p in allp]
    span = (min(xs), max(xs), min(zs), max(zs))
    print(f"       world span x[{span[0]:.3f},{span[1]:.3f}] y[{min(ys):.3f},{max(ys):.3f}] "
          f"z[{span[2]:.3f},{span[3]:.3f}]")
    check(all(abs(a - b) <= SPAN_TOL for a, b in zip(span, PLANNED_SPAN)), "world span == the planned footprint",
          f"planned x[{PLANNED_SPAN[0]},{PLANNED_SPAN[1]}] z[{PLANNED_SPAN[2]},{PLANNED_SPAN[3]}]")
    check(abs(min(ys) - BASE_Y) < 1e-6, f"base rests on the y {BASE_Y} plateau", f"y min {min(ys):.4f}")
    tox, toz = W.block_world_origin(BX, BY)
    check(tox <= span[0] and span[1] <= tox + 64 and toz - 64 <= span[2] and span[3] <= toz,
          "inside the block's 64x64 footprint",
          f"N edge margin {toz - span[3]:.3f}u")
    dmin = min(math.dist((p[0], p[2]), ARRIVE) for p in allp)
    check(dmin >= ARRIVE_CLEARANCE, f"EXCLUSION 1: every vertex >= {ARRIVE_CLEARANCE}u from the arrive point",
          f"nearest {dmin:.3f}u")
    x0, x1, z0, z1 = EXCLUSION
    inside = [p for p in allp if x0 <= p[0] <= x1 and z0 <= p[2] <= z1]
    check(not inside, f"EXCLUSION 2: no vertex in the keep-out rect x[{x0},{x1}] z[{z0},{z1}]",
          f"{len(inside)} inside" if inside else
          f"nearest real trigger tile {span[2] - TRIGGER_BBOX[3]:.3f}u away")

    # ---- (d) the UV carry ----------------------------------------------------------------------------
    print("\n(d) the UV carry (a UV-less carry renders flat WHITE off the atlas's alpha-0 corner)")
    uvs = obj.uvs
    check(len(uvs) == obj.vcount, "one UV per vertex", f"{len(uvs)} vs {obj.vcount}")
    check(all(any(abs(c) > 1e-6 for c in u) for u in uvs), "no degenerate [0,0] UV")
    check(sorted({round(u[0], 6) for u in uvs}) == donor_u, "U set byte-equal to the donor's")
    check(sorted({round(u[1], 6) for u in uvs}) == donor_v, "V set byte-equal to the donor's")
    print(f"       u[{min(u[0] for u in uvs):.5f},{max(u[0] for u in uvs):.5f}] "
          f"v[{min(u[1] for u in uvs):.5f},{max(u[1] for u in uvs):.5f}]  (shared res(1_24)_objects atlas)")

    # ---- the 4078 behavioural pair -------------------------------------------------------------------
    print("\n(+) what the 4078 stamp buys, measured on the deployed bytes")
    gw = ground(parts, *POST_PROBE)
    gi = ground(parts, *POST_PROBE, ignore_exceptions=True)
    check(gw is not None and gw[0] == "Terrain",
          f"gate centre {POST_PROBE}: the WALK query passes THROUGH to Terrain (walk-through, no trigger shadow)",
          "MISS" if gw is None else f"hit {gw[0]} idall={gw[2]} y={gw[1]:.2f}")
    check(gi is not None and gi[0] == "Object" and gi[2] == MARKER_IDALL,
          "the same spot IS visible to a sky-cast (proves the gate is really in the walkmesh set)",
          "MISS" if gi is None else f"hit {gi[0]} idall={gi[2]} y={gi[1]:.2f}")
    print()

print("=" * 100)
print(f"{'ALL CHECKS PASS' if not FAILURES else f'{len(FAILURES)} FAILURE(S): ' + '; '.join(FAILURES)}")
print("=" * 100)
raise SystemExit(1 if FAILURES else 0)
