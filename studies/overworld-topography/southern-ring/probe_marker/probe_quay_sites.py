"""READ-ONLY acceptance probe for the Southern Ring quay beacons -- DEPLOYED bytes, both discs.

Site-driven: the expectations come from `mint_quay_beacon.SITES`, the same table the generator builds
from, so the probe cannot drift from the mesh it is checking. One site per `--site`, or all four.

Per site:
  (a) the TRIGGER is intact -- exactly 6 tris, idall 16384 (event 1 / area 0: `--no-tile-area` keeps
      the area field), union bbox == the site's trigger rect, and the ground query lands on it. Not
      mere presence: `split_retarget_by_polygon` RETRIANGULATES, so a hull that reached the cluster
      would fragment it into pieces that still carry 16384 over the same area and pass every naive
      check -- so the tris are compared by VERTEX TRIPLE against the pre-deploy backup.
  (b) the ARRIVE point is untouched and WALKABLE in both query modes (walk-with-skip and
      sky-cast-with-IgnoreExceptions -- 4078 does NOT protect a sky-cast).
  (c) the BEACON is present and RENDER-ONLY -- 270 tris / 810 verts, every tri idall 4078; the walk
      query passes THROUGH it to the topo-59 hull while a sky-cast hits the Object, which is what
      proves the mesh really is in the walkmesh set and the 4078 stamp is load-bearing.
      The terrain-idall delta is enumerated by CENTROID against the backup (indices are not comparable
      across a retriangulation), and gated: topo-59 only, inside the footprint, clear of the trigger.
  (d) UVs valid -- one per vertex, none degenerate, in [0,1], all three authored tiles present.
  (e) Disc1 / Disc4 byte-identical.

Run:  py studies/overworld-topography/southern-ring/probe_marker/probe_quay_sites.py [--site NAME]
      (needs --backup-root pointing at the pre-deploy snapshot dir for this sweep)
"""
from __future__ import annotations

import argparse
import collections
import re
import hashlib
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "ff9mapkit"))
sys.path.insert(0, str(STUDY))

from ff9mapkit.world import extract as W                      # noqa: E402
from ff9mapkit.world import mesh as M                         # noqa: E402
from mint_quay_beacon import SITES, HALF_X_SPAN, DEEP_S, DEEP_N   # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
MOD = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap"

BEACON_IDALL = 4078
BEACON_TRIS, BEACON_VERTS = 270, 810
HULL_TOPO = 59
TRIGGER_IDALL = 16384
TRIGGER_TRIS = 6
IDALL_SKIP = {4078, 4088, 2040}
WALKABLE_TOPO = {0, 10, 13, 17, 36, 37}       # foot mask: 49/58/59 blocked (ff9.cs w_movementCheckTopographID)
ARRIVE_CLEARANCE = 6.0

FAILURES: list[str] = []


def check(ok, label, detail=""):
    if not ok:
        FAILURES.append(label)
    print(f"    [{'PASS' if ok else 'FAIL'}] {label}{('  -- ' + detail) if detail else ''}")


def idall_of(bm, t):
    return int(round(bm.tangents[bm.tris[t][0]][0]))


def mk_tri_pts(ox, oz):
    def f(bm, t):
        return [(bm.verts[k][0] + ox, bm.verts[k][1], bm.verts[k][2] + oz) for k in bm.tris[t]]
    return f


def ny_of(pts):
    a, b, c = pts
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    return ny / (math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0)


def hit(tri_pts, bm, t, wx, wz):
    a, b, c = tri_pts(bm, t)
    d = (b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])
    if abs(d) < 1e-12:
        return None
    w1 = ((wx - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (wz - a[2])) / d
    w2 = ((b[0] - a[0]) * (wz - a[2]) - (wx - a[0]) * (b[2] - a[2])) / d
    if w1 < -1e-9 or w2 < -1e-9 or w1 + w2 > 1 + 1e-9:
        return None
    return a[1] + w1 * (b[1] - a[1]) + w2 * (c[1] - a[1])


def ground(tri_pts, parts, wx, wz, *, ignore=False):
    """Object registers BEFORE Terrain, first tri in buffer order, up-facing winding."""
    for (nm, bm) in parts:
        for t in range(len(bm.tris)):
            i = idall_of(bm, t)
            if not ignore and i in IDALL_SKIP:
                continue
            if not ignore and ny_of(tri_pts(bm, t)) <= 0.1:
                continue
            y = hit(tri_pts, bm, t, wx, wz)
            if y is not None:
                return (nm, y, i, t)
    return None


def probe_site(key, backup_root: Path) -> None:
    S = SITES[key]
    bx = int(S.block[0] // 64)
    by = int(-S.block[3] // 64)
    ox, oz = W.block_world_origin(bx, by)
    tri_pts = mk_tri_pts(ox, oz)
    print("=" * 100)
    print(f"{S.name.upper()}   block ({bx},{by})   anchor {S.anchor}   ground_y {S.ground_y}")
    print("=" * 100)

    raw = {}
    for disc in (1, 4):
        d = MOD / f"Disc{disc}" / "0_1" / f"r{by}"
        terp, objp = d / f"Block[{bx}][{by}] Terrain.ff9mesh", d / f"Block[{bx}][{by}] Object.ff9mesh"
        ter = M.blockmesh_from_ff9mesh(str(terp), disc=disc, x=bx, y=by, part="terrain")
        obj = M.blockmesh_from_ff9mesh(str(objp), disc=disc, x=bx, y=by, part="object")
        raw[disc] = (terp.read_bytes(), objp.read_bytes())
        pre_p = backup_root / f"{key}" / f"Disc{disc}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
        pre = M.blockmesh_from_ff9mesh(str(pre_p), disc=disc, x=bx, y=by, part="terrain")
        parts = [("Object", obj), ("Terrain", ter)]
        print(f"  -- disc {disc}:  Terrain {terp.stat().st_size} B ({len(ter.tris)} tris, was "
              f"{len(pre.tris)})   Object {objp.stat().st_size} B ({len(obj.tris)} tris)")

        # (a) trigger
        ev = [t for t in range(len(ter.tris)) if W.decode_id(idall_of(ter, t))["event"]]
        check(len(ev) == TRIGGER_TRIS, f"exactly {TRIGGER_TRIS} event tris", f"got {len(ev)}")
        # The invariant is event==1 AND area==0 -- NOT a raw idall equality. `retarget_tiles` sets the
        # event bit and (with --no-tile-area) leaves area alone, but it also PRESERVES each tile's own
        # TOPOGRAPH, which is the site's terrain type: Ashvale/Tidefall/Larkspur sit on topo 0 (idall
        # 16384) while Grimhorn's bench ground is topo 17 (idall 16452). Demanding 16384 everywhere
        # would have flagged a correct deploy.
        dec = [W.decode_id(idall_of(ter, t)) for t in ev]
        check(all(d["event"] == 1 and d["area"] == 0 for d in dec)
              and len({idall_of(ter, t) for t in ev}) == 1,
              "all event tris are event 1 / area 0, and mutually consistent",
              f"idall {sorted({idall_of(ter, t) for t in ev})} -> "
              f"topo {sorted({d['topograph'] for d in dec})}")
        pts = [p for t in ev for p in tri_pts(ter, t)]
        if pts:
            bb = (min(p[0] for p in pts), max(p[0] for p in pts),
                  min(p[2] for p in pts), max(p[2] for p in pts))
            check(all(abs(a - b) < 1e-6 for a, b in zip(bb, S.trigger_bbox)),
                  f"union bbox == the site trigger rect {S.trigger_bbox}",
                  f"got x[{bb[0]:.2f},{bb[1]:.2f}] z[{bb[2]:.2f},{bb[3]:.2f}]")

        def evset(m):
            return sorted(tuple(sorted(tuple(round(c, 5) for c in p) for p in tri_pts(m, t)))
                          for t in range(len(m.tris)) if W.decode_id(idall_of(m, t))["event"])
        post_ev = evset(ter)
        pre_ev = evset(pre)
        check(len(post_ev) == TRIGGER_TRIS and (not pre_ev or post_ev == pre_ev),
              "trigger tris GEOMETRY-IDENTICAL to the pre-deploy mesh (not split by the hull)"
              if pre_ev else "trigger tris are NEW at this site (block had none before)",
              f"pre {len(pre_ev)} / post {len(post_ev)}")
        g = ground(tri_pts, parts, *S.trigger_at)
        gd = W.decode_id(g[2]) if g else None
        check(g is not None and gd["event"] == 1 and gd["area"] == 0,
              f"ground query {S.trigger_at} lands on an event-1/area-0 trigger tile",
              "MISS" if g is None else f"{g[0]} idall={g[2]} {gd} y={g[1]:.3f}")

        # (b) arrive, both modes
        for mode, ig in (("walk", False), ("sky-cast", True)):
            g = ground(tri_pts, parts, *S.arrive, ignore=ig)
            tp = W.decode_id(g[2])["topograph"] if g else None
            check(g is not None and g[0] == "Terrain" and tp in WALKABLE_TOPO,
                  f"arrive {S.arrive} [{mode}]: Terrain, walkable topo",
                  "MISS" if g is None else f"{g[0]} idall={g[2]} topo={tp} y={g[1]:.3f}")

        # (c) beacon + hull
        ids = collections.Counter(idall_of(obj, t) for t in range(len(obj.tris)))
        check(len(obj.tris) == BEACON_TRIS and obj.vcount == BEACON_VERTS,
              f"{BEACON_TRIS} tris / {BEACON_VERTS} verts", f"got {len(obj.tris)} / {obj.vcount}")
        check(set(ids) == {BEACON_IDALL}, f"EVERY tri idall {BEACON_IDALL} -> RENDER-ONLY", str(dict(ids)))
        allp = [p for t in range(len(obj.tris)) for p in tri_pts(obj, t)]
        xs = [p[0] for p in allp]; ys = [p[1] for p in allp]; zs = [p[2] for p in allp]
        want = (S.anchor[0] - HALF_X_SPAN, S.anchor[0] + HALF_X_SPAN,
                S.anchor[1] - DEEP_S, S.anchor[1] + DEEP_N)
        got = (min(xs), max(xs), min(zs), max(zs))
        check(all(abs(a - b) <= 0.01 for a, b in zip(got, want)), "span == the site footprint",
              f"got x[{got[0]:.2f},{got[1]:.2f}] z[{got[2]:.2f},{got[3]:.2f}]")
        check(min(ys) < S.ground_y - 1e-6, f"skirt BURIED below ground_y {S.ground_y}",
              f"lowest {min(ys):.3f}")
        cxp, czp = S.anchor
        gw = ground(tri_pts, parts, cxp, czp)
        gi = ground(tri_pts, parts, cxp, czp, ignore=True)
        check(gw is not None and gw[0] == "Terrain" and W.decode_id(gw[2])["topograph"] == HULL_TOPO,
              f"at the beacon centre the WALK query passes THROUGH to the topo-{HULL_TOPO} hull",
              "MISS" if gw is None else f"hit {gw[0]} idall={gw[2]}")
        check(gi is not None and gi[0] == "Object" and gi[2] == BEACON_IDALL,
              "a sky-cast DOES hit it -> the mesh IS in the walkmesh set, so 4078 is load-bearing",
              "MISS" if gi is None else f"hit {gi[0]} idall={gi[2]}")

        changed = []
        for t in range(len(ter.tris)):
            p3 = tri_pts(ter, t)
            cx = sum(p[0] for p in p3) / 3.0
            cz = sum(p[2] for p in p3) / 3.0
            new = idall_of(ter, t)
            old = None
            for pt in range(len(pre.tris)):
                if ny_of(tri_pts(pre, pt)) > 0.1 and hit(tri_pts, pre, pt, cx, cz) is not None:
                    old = idall_of(pre, pt)
                    break
            if old is not None and old != new:
                changed.append((t, old, new, round(cx, 2), round(cz, 2),
                                round(min(p[0] for p in p3), 2), round(max(p[0] for p in p3), 2),
                                round(min(p[2] for p in p3), 2), round(max(p[2] for p in p3), 2)))
        hull = [c for c in changed if W.decode_id(c[2])["topograph"] == HULL_TOPO]
        trig = [c for c in changed if W.decode_id(c[2])["event"]]
        if disc == 1:
            print(f"       TERRAIN idall changes: {len(changed)} "
                  f"({len(hull)} -> topo 59 hull, {len(trig)} -> event tiles)")
            for c in hull:
                print(f"         hull  tri {c[0]:4d}: {c[1]} -> {c[2]}  centroid ({c[3]},{c[4]})  "
                      f"x[{c[5]},{c[6]}] z[{c[7]},{c[8]}]")
        check(bool(hull), "the hull stamped terrain tiles (collision exists)", f"{len(hull)}")
        check(all(W.decode_id(c[1])["event"] == 0 for c in hull),
              "NO event tile was overwritten by the hull")
        outside = [c for c in hull if not (want[0] - 0.01 <= c[5] and c[6] <= want[1] + 0.01
                                           and want[2] - 0.01 <= c[7] and c[8] <= want[3] + 0.01)]
        check(not outside, "every hull tile lies INSIDE the beacon footprint", f"{len(outside)} outside")
        tx0, tx1, tz0, tz1 = S.trigger_bbox
        intrig = [c for c in hull if not (c[6] < tx0 or c[5] > tx1 or c[8] < tz0 or c[7] > tz1)]
        check(not intrig, "no hull tile overlaps the trigger rect", f"{len(intrig)}")
        n59 = sum(1 for t in range(len(ter.tris))
                  if W.decode_id(idall_of(ter, t))["topograph"] == HULL_TOPO)
        check(n59 == len(hull), f"the ONLY topo-{HULL_TOPO} geometry in the block is this hull "
              "(no orphaned blockers)", f"{n59} blocked vs {len(hull)} stamped")

        # (d) UVs
        uvs = obj.uvs
        check(len(uvs) == obj.vcount and all(any(abs(c) > 1e-6 for c in u) for u in uvs)
              and all(-1e-6 <= u[0] <= 1 + 1e-6 and -1e-6 <= u[1] <= 1 + 1e-6 for u in uvs),
              "UVs: one per vertex, none degenerate, all in [0,1]")

    # (e) disc parity
    for k, nm in ((0, "Terrain"), (1, "Object")):
        h1, h4 = (hashlib.md5(raw[1][k]).hexdigest(), hashlib.md5(raw[4][k]).hexdigest())
        check(h1 == h4, f"{nm}: Disc1 / Disc4 byte-identical", f"{h1[:12]} vs {h4[:12]}")
        print(f"       {nm} md5 {h1}  ({len(raw[1][k])} B)")
    print()


def ring_closure() -> None:
    """THE RING-CLOSURE CHECK -- the one invariant nothing else enforces.

    The quay arrives live in `mint_quay_beacon.SITES`; the hall's landings live in
    `lantern-hall.field.toml`. They are the same points written down in two files, and nothing ties
    them together: change one side and the ring silently half-breaks -- you sail somewhere that is no
    longer beside its beacon. Playtest-only otherwise; milliseconds here.

    Since the berth-row redesign the hall declares them in TWO places, and BOTH are checked:
      * the FERRY -- `[[ferry.destination]]` rows on the Purser (all four ports);
      * the HOME DOOR -- the single walk-out `[[gateway]]`, which must land at Ashvale.
    """
    toml = (STUDY / "lantern-hall.field.toml").read_text(encoding="utf-8")
    print("=" * 100)
    print("RING CLOSURE -- lantern-hall (ferry + home door) vs mint_quay_beacon.SITES")
    print("=" * 100)

    # --- the ferry destinations
    ferry = []
    for blk in toml.split("[[ferry.destination]]")[1:]:
        nm = re.search(r'name\s*=\s*"([^"]+)"', blk)
        a = re.search(r"arrive\s*=\s*\[\s*([-\d.]+)\s*,\s*([-\d.]+)", blk)
        f = re.search(r"arrive_face\s*=\s*(\d+)", blk)
        if nm and a:
            ferry.append((nm.group(1), float(a.group(1)), float(a.group(2)),
                          int(f.group(1)) if f else 0))
    check(len(ferry) == 4, "the ferry declares exactly 4 destinations", f"got {len(ferry)}")
    by_name = {n.lower(): (x, z, fc) for (n, x, z, fc) in ferry}
    for k in ("ashvale", "tidefall", "grimhorn", "larkspur"):
        S = SITES[k]
        want = (S.arrive[0], S.arrive[1], S.arrive_face)
        got = by_name.get(k)
        check(got == want, f"ferry row {S.name!r} lands at its quay's gated arrive point",
              f"hall {got} vs quay {want}")

    # --- the home door: the ONE walk-out gateway, which must be Ashvale
    doors = []
    for blk in toml.split("[[gateway]]")[1:]:
        a = re.search(r"arrive\s*=\s*\[\s*([-\d.]+)\s*,\s*([-\d.]+)", blk)
        f = re.search(r"arrive_face\s*=\s*(\d+)", blk)
        if a:
            doors.append((float(a.group(1)), float(a.group(2)), int(f.group(1)) if f else 0))
    A = SITES["ashvale"]
    check(len(doors) == 1, "exactly ONE walk-on exit (the home door) -- the berth row is gone",
          f"got {len(doors)}")
    check(doors and doors[0] == (A.arrive[0], A.arrive[1], A.arrive_face),
          "the home door lands at Ashvale, the home port",
          f"door {doors[0] if doors else None} vs {(A.arrive[0], A.arrive[1], A.arrive_face)}")

    # --- no stale berth-row leftovers
    # Look for an ASSIGNMENT, not the bare digits -- the file's own comment explains that these flags
    # were returned to the pool, and a substring test matches that prose and fails on a correct file.
    live = re.findall(r"^\s*flag\s*=\s*(876[0-3])", toml, re.M)
    check(not live, "the deleted berth-sign flags 8760-8763 are no longer ASSIGNED (returned to the pool)",
          f"still assigned: {live}")
    check(toml.count("[[event]]") == 0, "no [[event]] sign zones remain")
    print()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", choices=sorted(SITES) + ["all"], default="all")
    ap.add_argument("--backup-root", required=True, help="the pre-deploy snapshot dir for this sweep")
    a = ap.parse_args()
    root = Path(a.backup_root)
    for k in (sorted(SITES) if a.site == "all" else [a.site]):
        probe_site(k, root)
    if a.site == "all":
        ring_closure()
    print("=" * 100)
    print("ALL CHECKS PASS" if not FAILURES else f"{len(FAILURES)} FAILURE(S): " + "; ".join(FAILURES))
    print("=" * 100)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
