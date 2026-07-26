"""READ-ONLY acceptance probe for THE LANTERN BEACON (pass 3) -- DEPLOYED bytes, both discs.

Pass 3 replaced the rejected harbour carry with an authored beacon placed through the PROVEN building
layer, so this probe checks two things the earlier passes did not:

  * collision now lives in the TERRAIN (a topo-59 hull), not in the Object mesh -- so the terrain's
    IDALL changed, a first for this marker arc. The probe enumerates EXACTLY which tiles changed, by
    geometry (`split_retarget_by_polygon` RETRIANGULATES, so triangle indices are not comparable
    before/after -- each AFTER triangle is matched to the BEFORE mesh by centroid query).
  * the walkable APPROACH from the arrive point to the quay trigger is still walkable end to end
    (a topo-59 hull placed carelessly would wall the player off from the entrance they came for).

Checks:
  (a) the quay TRIGGER is intact -- 6 tris, idall 16384 (event 1, area 0: `--no-tile-area` kept the
      area field, exactly as R1 deployed it), union bbox x[44,52] z[-1172,-1164]; (48,-1168) -> 16384.
  (b) the ARRIVE point (60,-1168) -> idall 0, topo 0, y 3.00 in BOTH query modes, AND every sampled
      step of the arrival->trigger walk path is a WALKABLE topograph.
  (c) the BEACON Object mesh is present (222 tris / 666 verts), EVERY tri idall 4078, and is therefore
      RENDER-ONLY: `WMPhysics.Raycast` skips it, so the walk query passes through to Terrain. The
      terrain-idall delta is enumerated and must be topo-59-only, confined to the beacon footprint,
      and disjoint from both the trigger tiles and the approach path.
  (d) UVs valid -- one per vertex, none degenerate, inside [0,1], and BOTH authored tiles present.
  (e) Disc1 and Disc4 byte-identical.

Run:  py studies/overworld-topography/southern-ring/probe_marker/probe_quay_beacon.py
"""
from __future__ import annotations

import collections
import hashlib
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
BACKUP = REPO / "backups" / "quay-beacon-prebuild.20260725-230801"   # the PRE-beacon terrain, for the delta
BX, BY = 0, 18
OX, OZ = W.block_world_origin(BX, BY)

BEACON_IDALL = 4078
BEACON_TRIS, BEACON_VERTS = 222, 666
HULL_TOPO = 59
TRIGGER_IDALL = 16384
TRIGGER_TRIS = 6
TRIGGER_BBOX = (44.0, 52.0, -1172.0, -1164.0)
BEACON_SPAN = (45.70, 50.30, -1159.30, -1154.70)
ARRIVE = (60.0, -1168.0)
WALKABLE_TOPO = {0, 10, 36}            # on-foot limit: 10/36 walkable, 49/59 blocked (ff9.cs:5769)
IDALL_SKIP = {4078, 4088, 2040}

FAILURES: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    if not ok:
        FAILURES.append(label)
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{('  -- ' + detail) if detail else ''}")


def idall_of(bm, t: int) -> int:
    return int(round(bm.tangents[bm.tris[t][0]][0]))


def tri_pts(bm, t: int):
    return [(bm.verts[k][0] + OX, bm.verts[k][1], bm.verts[k][2] + OZ) for k in bm.tris[t]]


def ny_of(pts) -> float:
    a, b, c = pts
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    return ny / (math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0)


def _hit(bm, t, wx, wz):
    a, b, c = tri_pts(bm, t)
    d = (b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])
    if abs(d) < 1e-12:
        return None
    w1 = ((wx - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (wz - a[2])) / d
    w2 = ((b[0] - a[0]) * (wz - a[2]) - (wx - a[0]) * (b[2] - a[2])) / d
    if w1 < -1e-9 or w2 < -1e-9 or w1 + w2 > 1 + 1e-9:
        return None
    return a[1] + w1 * (b[1] - a[1]) + w2 * (c[1] - a[1])


def ground(parts, wx, wz, *, ignore_exceptions=False):
    """First mesh in load order (Object registers BEFORE Terrain), first tri in buffer order,
    up-facing winding; ``ignore_exceptions`` mirrors WMPhysics.IgnoreExceptions=true."""
    for (nm, bm) in parts:
        for t in range(len(bm.tris)):
            i = idall_of(bm, t)
            if not ignore_exceptions and i in IDALL_SKIP:
                continue
            if not ignore_exceptions and ny_of(tri_pts(bm, t)) <= 0.1:
                continue
            y = _hit(bm, t, wx, wz)
            if y is not None:
                return (nm, y, i, t)
    return None


def topo_at(bm, wx, wz):
    """The terrain topograph the MOVE gate would read at (wx, wz) (up-facing, first tri wins)."""
    for t in range(len(bm.tris)):
        if ny_of(tri_pts(bm, t)) <= 0.1:
            continue
        if _hit(bm, t, wx, wz) is not None:
            return W.decode_id(idall_of(bm, t))["topograph"], t
    return None, None


discs = {}
for disc in (1, 4):
    print("=" * 100)
    print(f"DISC {disc}")
    print("=" * 100)
    ter_p = MOD / f"Disc{disc}" / "0_1" / "r18" / "Block[0][18] Terrain.ff9mesh"
    obj_p = MOD / f"Disc{disc}" / "0_1" / "r18" / "Block[0][18] Object.ff9mesh"
    ter = M.blockmesh_from_ff9mesh(str(ter_p), disc=disc, x=BX, y=BY, part="terrain")
    obj = M.blockmesh_from_ff9mesh(str(obj_p), disc=disc, x=BX, y=BY, part="object")
    discs[disc] = (ter_p.read_bytes(), obj_p.read_bytes())
    print(f"Terrain {ter_p.stat().st_size} B: {ter.vcount} verts / {len(ter.tris)} tris")
    print(f"Object  {obj_p.stat().st_size} B: {obj.vcount} verts / {len(obj.tris)} tris")
    parts = [("Object", obj), ("Terrain", ter)]

    # ---- (a) trigger intact --------------------------------------------------------------------
    print("\n(a) the quay TRIGGER cluster is intact")
    ev = [t for t in range(len(ter.tris)) if W.decode_id(idall_of(ter, t))["event"]]
    check(len(ev) == TRIGGER_TRIS, f"exactly {TRIGGER_TRIS} event tris", f"got {len(ev)}")
    check({idall_of(ter, t) for t in ev} == {TRIGGER_IDALL},
          f"all idall {TRIGGER_IDALL} (event 1, area 0 -- --no-tile-area kept R1's area field)",
          str(sorted({idall_of(ter, t) for t in ev})))
    pts = [p for t in ev for p in tri_pts(ter, t)]
    bb = (min(p[0] for p in pts), max(p[0] for p in pts), min(p[2] for p in pts), max(p[2] for p in pts))
    check(all(abs(a - b) < 1e-6 for a, b in zip(bb, TRIGGER_BBOX)), "union bbox unmoved",
          f"x[{bb[0]:.2f},{bb[1]:.2f}] z[{bb[2]:.2f},{bb[3]:.2f}]")
    g = ground(parts, 48.0, -1168.0)
    check(g is not None and g[2] == TRIGGER_IDALL and abs(g[1] - 3.0) < 1e-6,
          f"ground query (48,-1168) -> idall {TRIGGER_IDALL} @ y 3.00",
          "MISS" if g is None else f"{g[0]} idall={g[2]} y={g[1]:.3f}")

    # ---- (b) arrival + the approach path -------------------------------------------------------
    print("\n(b) the ARRIVE point and the walkable approach to the trigger")
    for mode, ie in (("walk (skip 4078)", False), ("sky-cast (IgnoreExceptions)", True)):
        g = ground(parts, *ARRIVE, ignore_exceptions=ie)
        ok = g is not None and g[0] == "Terrain" and g[2] == 0 and abs(g[1] - 3.0) < 1e-6
        check(ok, f"{mode}: Terrain, idall 0, topo 0, y 3.00",
              "MISS" if g is None else f"{g[0]} idall={g[2]} y={g[1]:.3f}")
    blocked = []
    for k in range(25):
        f = k / 24.0
        wx = ARRIVE[0] + (48.0 - ARRIVE[0]) * f
        wz = ARRIVE[1] + (-1168.0 - ARRIVE[1]) * f
        tp, _ = topo_at(ter, wx, wz)
        if tp is None or tp not in WALKABLE_TOPO:
            blocked.append((round(wx, 1), round(wz, 1), tp))
    check(not blocked, "every step of the arrival->trigger path is a WALKABLE topograph "
          f"({sorted(WALKABLE_TOPO)})", f"blocked at {blocked[:4]}")
    # and a lateral sweep, so the approach is a corridor not a knife-edge
    lat = []
    for dz in (-6, -4, -2, 0, 2, 4, 6):
        for wx in (52, 54, 56, 58, 60):
            tp, _ = topo_at(ter, float(wx), -1168.0 + dz)
            if tp is None or tp not in WALKABLE_TOPO:
                lat.append((wx, -1168.0 + dz, tp))
    check(not lat, "a +/-6u wide corridor around the approach is walkable too", f"{len(lat)} blocked")

    # ---- (c) the beacon + the TERRAIN idall delta ----------------------------------------------
    print("\n(c) the BEACON Object mesh (render-only) + the TERRAIN collision hull")
    ids = collections.Counter(idall_of(obj, t) for t in range(len(obj.tris)))
    check(len(obj.tris) == BEACON_TRIS and obj.vcount == BEACON_VERTS,
          f"{BEACON_TRIS} tris / {BEACON_VERTS} verts", f"got {len(obj.tris)} / {obj.vcount}")
    check(set(ids) == {BEACON_IDALL}, f"EVERY tri idall {BEACON_IDALL} (0x{BEACON_IDALL:04X}) "
          f"-> WMPhysics skips it -> RENDER-ONLY", str(dict(ids)))
    allp = [p for t in range(len(obj.tris)) for p in tri_pts(obj, t)]
    xs = [p[0] for p in allp]; ys = [p[1] for p in allp]; zs = [p[2] for p in allp]
    span = (min(xs), max(xs), min(zs), max(zs))
    print(f"       beacon span x[{span[0]:.2f},{span[1]:.2f}] y[{min(ys):.2f},{max(ys):.2f}] "
          f"z[{span[2]:.2f},{span[3]:.2f}]")
    check(all(abs(a - b) <= 0.01 for a, b in zip(span, BEACON_SPAN)), "span == the planned footprint")
    check(min(ys) < 3.0 - 1e-6, "skirt BURIED below the y=3.00 plateau (no coplanar z-fight)",
          f"lowest {min(ys):.2f}")
    # render-only, measured: the walk query must pass THROUGH the beacon to the terrain
    gw = ground(parts, 48.0, -1157.0)
    gi = ground(parts, 48.0, -1157.0, ignore_exceptions=True)
    check(gw is not None and gw[0] == "Terrain",
          "the WALK query passes THROUGH the beacon to Terrain (render-only confirmed)",
          "MISS" if gw is None else f"hit {gw[0]} idall={gw[2]}")
    check(gi is not None and gi[0] == "Object" and gi[2] == BEACON_IDALL,
          "a sky-cast DOES hit it -> the mesh really is in the walkmesh set, so 4078 is load-bearing",
          "MISS" if gi is None else f"hit {gi[0]} idall={gi[2]}")

    # the terrain idall delta, by GEOMETRY (the hull split retriangulated the block)
    pre = M.blockmesh_from_ff9mesh(str(BACKUP / f"Disc{disc}-r18" / "Block[0][18] Terrain.ff9mesh"),
                                   disc=disc, x=BX, y=BY, part="terrain")
    print(f"       terrain BEFORE: {pre.vcount} verts / {len(pre.tris)} tris   "
          f"AFTER: {ter.vcount} verts / {len(ter.tris)} tris  "
          f"(+{len(ter.tris) - len(pre.tris)} tris from the hull split)")
    changed = []
    for t in range(len(ter.tris)):
        pts = tri_pts(ter, t)
        cx = sum(p[0] for p in pts) / 3.0
        cz = sum(p[2] for p in pts) / 3.0
        new = idall_of(ter, t)
        old = None
        for pt in range(len(pre.tris)):
            if _hit(pre, pt, cx, cz) is not None and ny_of(tri_pts(pre, pt)) > 0.1:
                old = idall_of(pre, pt)
                break
        if old is not None and old != new:
            changed.append((t, old, new, round(cx, 2), round(cz, 2),
                            round(min(p[0] for p in pts), 2), round(max(p[0] for p in pts), 2),
                            round(min(p[2] for p in pts), 2), round(max(p[2] for p in pts), 2)))
    print(f"       TERRAIN tiles whose IDALL changed: {len(changed)}")
    for (t, old, new, cx, cz, x0, x1, z0, z1) in changed:
        print(f"         tri {t:4d}: idall {old} -> {new}  (topo {W.decode_id(old)['topograph']} -> "
              f"{W.decode_id(new)['topograph']})  centroid ({cx},{cz})  x[{x0},{x1}] z[{z0},{z1}]")
    check(bool(changed), "the hull DID stamp terrain tiles (collision exists)", f"{len(changed)}")
    check(all(W.decode_id(c[2])["topograph"] == HULL_TOPO for c in changed),
          f"every changed tile became topograph {HULL_TOPO} (impassable structure)")
    check(all(W.decode_id(c[1])["event"] == 0 for c in changed),
          "NO event tile was overwritten by the hull (the trigger is untouched)")
    bx0, bx1, bz0, bz1 = BEACON_SPAN
    outside = [c for c in changed if not (bx0 - 0.01 <= c[5] and c[6] <= bx1 + 0.01
                                          and bz0 - 0.01 <= c[7] and c[8] <= bz1 + 0.01)]
    check(not outside, "every changed tile lies INSIDE the beacon footprint", f"{len(outside)} outside")
    tx0, tx1, tz0, tz1 = TRIGGER_BBOX
    intrig = [c for c in changed if not (c[6] < tx0 or c[5] > tx1 or c[8] < tz0 or c[7] > tz1)]
    check(not intrig, "no changed tile overlaps the trigger rect", f"{len(intrig)}")
    n59 = sum(1 for t in range(len(ter.tris))
              if W.decode_id(idall_of(ter, t))["topograph"] == HULL_TOPO)
    print(f"       total topo-{HULL_TOPO} tris in the block now: {n59}")

    # ---- (d) UVs -------------------------------------------------------------------------------
    print("\n(d) the beacon's UVs")
    uvs = obj.uvs
    check(len(uvs) == obj.vcount, "one UV per vertex", f"{len(uvs)} vs {obj.vcount}")
    check(all(any(abs(c) > 1e-6 for c in u) for u in uvs), "no degenerate [0,0] UV (would render white)")
    check(all(-1e-6 <= u[0] <= 1 + 1e-6 and -1e-6 <= u[1] <= 1 + 1e-6 for u in uvs), "every UV in [0,1]")
    ustone = sum(1 for u in uvs if u[0] < 0.2)
    ulant = sum(1 for u in uvs if u[0] > 0.2)
    check(ustone > 0 and ulant > 0, "BOTH authored tiles present (stone shaft + warm lantern room)",
          f"{ustone} stone corners, {ulant} lantern corners")
    print(f"       u[{min(u[0] for u in uvs):.5f},{max(u[0] for u in uvs):.5f}] "
          f"v[{min(u[1] for u in uvs):.5f},{max(u[1] for u in uvs):.5f}]")
    print()

# ---- (e) disc parity ---------------------------------------------------------------------------
print("=" * 100)
print("(e) DISC PARITY")
print("=" * 100)
for k, name in ((0, "Terrain"), (1, "Object")):
    h1 = hashlib.md5(discs[1][k]).hexdigest()
    h4 = hashlib.md5(discs[4][k]).hexdigest()
    check(h1 == h4, f"{name}: Disc1 and Disc4 byte-identical", f"{h1[:12]} vs {h4[:12]}")
    print(f"       {name} md5 {h1}  ({len(discs[1][k])} B)")

print()
print("=" * 100)
print(f"{'ALL CHECKS PASS' if not FAILURES else f'{len(FAILURES)} FAILURE(S): ' + '; '.join(FAILURES)}")
print("=" * 100)
raise SystemExit(1 if FAILURES else 0)
