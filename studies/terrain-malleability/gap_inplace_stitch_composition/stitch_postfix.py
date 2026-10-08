"""DEFECT 5 AFTER THE FIX (2026-10-08): the kit's terrain.reshape now HOLDS every Terrain vertex welded to another
part (mesh.stitch_pins), and mesh.stitch_gate refuses any tear. This re-runs the reference tear sweep's 5,292 edits
(out/tear_sweep.json: 294 beach/object-centred edits x amount {+-1,+-3,+-6} x radius {8,16,24}) through the REAL kit
code (reshape, dry run, allow_steep so the walk gate reports instead of refusing) and measures:

  CALIBRATION  with the pins switched OFF, the kit's stitch gate must count exactly the sweep model's torn positions,
               edit for edit (the model was itself calibrated against the real writer: 10 at (7,17), S5).
  TORN         with the pins ON, every edit must tear 0 welds.
  WALLS        the sweep's own crossing instrument (tear_sweep.crossing: the engine walk query, calibrated W1-W4 and
               in game at rank 3) on the same probe pairs: walkable Terrain|Beach/Object seams the field reached,
               before (stock) vs after. Pre-fix: 149-154/154 beach +-3 edits introduced a wall.
  SLOPE        the kit's one-way-wall gate verdict (an edge steeper than ~79.4 deg would be REFUSED without
               --allow-steep) and the flank warning.
  KEPT         the share of the unpinned edit's total vertical displacement the pinned edit keeps.
for seam tapers T in {0 (a hard pin), 4, 8} u. Writes out/stitch_postfix.json.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_inplace_stitch_composition/stitch_postfix.py [--quick]
"""
from __future__ import annotations

import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitchlib as S                                  # noqa: E402
import tear_sweep as TS                                # noqa: E402
from ff9mapkit.world import mesh as M, terrain as T    # noqa: E402
from ff9mapkit.world.mesh import _falloff              # noqa: E402

MOD = "FF9CustomMap-stitch-postfix-nonexistent"         # never deployed: every read is stock
TAPERS = (0.0, 4.0, 8.0)

_cap = {}
_gate = M.stitch_gate


def _capture(meshes, **kw):
    r = _gate(meshes, **kw)
    _cap["rows"], _cap["gate"] = meshes, r
    return r


M.stitch_gate = _capture


def run(cx, cz, A, R, *, pins=True, taper=0.0):
    """One kit reshape dry run -> (gate, summary or None, {block: post local verts}, {block: pre local verts})."""
    _cap.clear()
    orig = M.stitch_pins
    if not pins:
        M.stitch_pins = lambda *a, **k: M.StitchPins(set())
    try:
        s = T.reshape(MOD, at=(cx, cz), radius=R, amount=A, dry_run=True, allow_steep=True, seam_taper=taper)
    except ValueError as e:
        if "STITCH GATE" not in str(e):
            raise
        s = None
    finally:
        M.stitch_pins = orig
    post, pre = {}, {}
    for name, a, b in _cap["rows"]:
        if not name.endswith(" Terrain"):
            continue
        bx, by = (int(t) for t in name[len("Block["):name.index("] ")].split("]["))
        ox, oz = bx * 64.0, -by * 64.0
        pre[(bx, by)] = [(p[0] - ox, p[1], p[2] - oz) for p in a]
        post[(bx, by)] = [(p[0] - ox, p[1], p[2] - oz) for p in b]
    return _cap["gate"], s, post, pre


def main():
    quick = "--quick" in sys.argv
    t0 = time.time()
    rows = json.loads((S.OUT / "tear_sweep.json").read_text(encoding="utf-8"))["rows"]
    if quick:
        rows = [r for r in rows if r["radius"] == 16.0 and abs(r["amount"]) == 3.0]
    Md = S.load_disc(1)
    blocks = TS.build_world(Md)
    owners = defaultdict(set)
    for k, m in Md.items():
        for p in m.wv:
            owners[S.wrap_key(p)].add(k)
    welds, tri_at = {}, defaultdict(lambda: defaultdict(list))
    for (x, y), parts in blocks.items():
        for p, m in parts.items():
            for t in range(m.ntri):
                for k in range(3):
                    tri_at[(x, y)][m.lv[m.fi[3 * t + k]]].append((p, t))
        if "terrain" in parts:
            ter = parts["terrain"]
            welds[(x, y)] = {lp: sorted(owners[S.wrap_key(wp)] - {(x, y, "terrain")})
                             for lp, wp in zip(ter.lv, ter.wv) if owners[S.wrap_key(wp)] - {(x, y, "terrain")}}
    # the sweep stored each centre rounded to 3 decimals; every centre IS a Terrain weld vertex, so snap back to it
    exact = {}
    for r in rows:
        cx, cz = r["centre"]
        hits = {(p[0], p[2]) for p in blocks[tuple(r["block"])]["terrain"].wv
                if abs(p[0] - cx) < 0.0006 and abs(p[2] - cz) < 0.0006}
        assert len(hits) == 1, (r["block"], r["centre"], hits)
        exact[tuple(r["centre"])] = hits.pop()
    base_ml, base_idx = {}, {}

    def base(blk):
        if blk not in base_ml:
            try:
                ml = TS.meshlist_for(blocks, blk)
                base_idx[blk] = M_place.build_meshlist_index(ml)
                base_ml[blk] = ml
            except ValueError:
                base_ml[blk] = None
        return base_ml[blk]

    from ff9mapkit.world import placement as M_place

    def walls_for(cx, cz, A, R, post):
        """The sweep's crossings at walkable seams the unpinned field reached (> TOL), stock vs post."""
        walls, crossings = Counter(), 0
        for blk, tv in post.items():
            if blk not in welds or base(blk) is None:
                continue
            ox, oz = blk[0] * 64.0, -blk[1] * 64.0
            mla = TS.meshlist_for(blocks, blk, tv)
            idxa = M_place.build_meshlist_index(mla)
            for lp, others in welds[blk].items():
                if not any(o[2] in TS.WALKABLE_PARTNERS for o in others):
                    continue
                if abs(A * _falloff(math.hypot(lp[0] + ox - cx, lp[2] + oz - cz) / R, "smooth")) <= S.TOL:
                    continue
                probes = []
                for (p, t) in tri_at[blk][lp]:
                    m = blocks[blk][p]
                    cs = [m.lv[m.fi[3 * t + k]] for k in range(3)]
                    gx, gz = sum(q[0] for q in cs) / 3 - lp[0], sum(q[2] for q in cs) / 3 - lp[2]
                    L = math.hypot(gx, gz)
                    if L > 1e-6:
                        probes.append((p, (lp[0] + TS.PROBE * gx / L, lp[2] + TS.PROBE * gz / L)))
                for pa, Ap in probes:
                    for pb, Bp in probes:
                        if pa == pb or "terrain" not in (pa, pb):
                            continue
                        if pa not in TS.WALKABLE_PARTNERS | {"terrain"} or pb not in TS.WALKABLE_PARTNERS | {"terrain"}:
                            continue
                        before, _ = TS.crossing(base_ml[blk], base_idx[blk], Ap, base_ml[blk], base_idx[blk], Bp)
                        after, _ = TS.crossing(mla, idxa, Ap, mla, idxa, Bp)
                        crossings += 1
                        if before and after is False:
                            walls[f"{pa}->{pb}"] += 1
        return walls, crossings

    wall_tan = M_place.WALK_RAY_START / M_place.WALK_SPEED
    flank_tan = math.tan(math.radians(28.6))

    def model_style_torn():
        """The sweep model counts a torn position once per Terrain BLOCK holding it (a border weld twice)."""
        cl = defaultdict(list)
        for mi, (name, pre, post) in enumerate(_cap["rows"]):
            for vi, q in enumerate(pre):
                cl[(round(q[0], 4), round(q[1], 4), round(q[2], 4))].append((mi, vi))
        n = 0
        for inst in cl.values():
            if len({mi for mi, _ in inst}) < 2 and len(inst) < 2:
                continue
            pts = [_cap["rows"][mi][2][vi] for mi, vi in inst]
            if max(max(q[k] for q in pts) - min(q[k] for q in pts) for k in range(3)) > S.TOL:
                n += len({mi for mi, _ in inst if _cap["rows"][mi][0].endswith(" Terrain")})
        return n

    def slopes(pre, post):
        """(introduced one-way edges, any one-way moved edge, introduced flank edges) over moved Terrain tris."""
        intro = anyw = flank = 0
        for blk, tv in post.items():
            fi, pv = blocks[blk]["terrain"].fi, pre[blk]
            seen = set()
            for t in range(len(fi) // 3):
                ids = fi[3 * t:3 * t + 3]
                if all(abs(tv[i][1] - pv[i][1]) < 1e-9 for i in ids):
                    continue
                for a, b in ((ids[0], ids[1]), (ids[1], ids[2]), (ids[2], ids[0])):
                    e = (min(a, b), max(a, b))
                    if e in seen:
                        continue
                    seen.add(e)
                    run = math.hypot(pv[a][0] - pv[b][0], pv[a][2] - pv[b][2])
                    if run < 1e-6:
                        continue
                    t0_, t1_ = abs(pv[a][1] - pv[b][1]) / run, abs(tv[a][1] - tv[b][1]) / run
                    anyw += t1_ > wall_tan
                    intro += t0_ <= wall_tan < t1_
                    flank += t0_ <= flank_tan < t1_
        return intro, anyw, flank

    MODES = [("unpinned", False, 0.0)] + [(f"pin taper {t:g}u", True, t) for t in TAPERS]
    out = {"edits": len(rows), "quick": quick, "calibration": {}, "modes": {}}
    unp, mism, wall_mism = {}, [], []
    for mode, pins, taper in MODES:
        cls = defaultdict(lambda: {"edits": 0, "torn_edits": 0, "wall_edits": 0, "walls": 0, "crossings": 0,
                                   "intro_oneway_edits": 0, "any_oneway_edits": 0, "intro_flank_edits": 0,
                                   "kept": []})
        for r in rows:
            cx, cz = exact[tuple(r["centre"])]
            A, R = r["amount"], r["radius"]
            g, s, post, pre = run(cx, cz, A, R, pins=pins, taper=taper)
            c = cls[f"{r['kind']} A{A:+g} R{R:g}"]
            c["edits"] += 1
            c["torn_edits"] += bool(g["torn"])
            w, n = walls_for(cx, cz, A, R, post)
            c["crossings"] += n
            c["walls"] += sum(w.values())
            c["wall_edits"] += bool(w)
            if w and pins:
                c.setdefault("wall_cases", []).append({"block": r["block"], "centre": r["centre"], "walls": dict(w),
                                                       "sweep_pre_fix": r["introduced_walls"]})
            iw, aw, fl = slopes(pre, post)
            c["intro_oneway_edits"] += bool(iw)
            c["any_oneway_edits"] += bool(aw)
            c["intro_flank_edits"] += bool(fl)
            moved = sum(abs(b[1] - a[1]) for blk in post for a, b in zip(pre[blk], post[blk]))
            key = (tuple(r["centre"]), A, R)
            if not pins:
                unp[key] = moved
                kt = model_style_torn()
                if kt != r["torn_positions"]:
                    mism.append({"block": r["block"], "centre": r["centre"], "A": A, "R": R, "kit": kt,
                                 "model": r["torn_positions"]})
                if dict(w) != r["introduced_walls"]:
                    wall_mism.append({"block": r["block"], "centre": r["centre"], "A": A, "R": R, "here": dict(w),
                                      "sweep": r["introduced_walls"]})
                for blk in post:                   # the kit's vertex order is the decode's (S5's slot assert)
                    assert len(post[blk]) == len(blocks[blk]["terrain"].lv), blk
            elif unp.get(key, 0) > 1e-9:
                c["kept"].append(moved / unp[key])
        summ = {}
        for k, c in sorted(cls.items()):
            kept = sorted(c.pop("kept"))
            c.setdefault("wall_cases", [])
            summ[k] = dict(c, kept_median=round(kept[len(kept) // 2], 3) if kept else None,
                           kept_p10=round(kept[int(0.1 * (len(kept) - 1))], 3) if kept else None)
        out["modes"][mode] = summ
        if not pins:
            out["calibration"] = {"edits": len(rows), "torn_kit_equals_model": len(rows) - len(mism),
                                  "torn_mismatches": mism[:20], "walls_equal_sweep": len(rows) - len(wall_mism),
                                  "wall_mismatches": wall_mism[:20]}
            print(f"calibration (pins off): torn == model on {len(rows) - len(mism)}/{len(rows)}; crossing walls == "
                  f"sweep on {len(rows) - len(wall_mism)}/{len(rows)} ({time.time() - t0:.0f}s)")
        tot = {f: sum(v[f] for v in summ.values()) for f in ("edits", "torn_edits", "wall_edits", "intro_oneway_edits",
                                                               "any_oneway_edits", "intro_flank_edits")}
        print(f"{mode}: {tot}  ({time.time() - t0:.0f}s)")
        for k, v in summ.items():
            print(f"   {k:16s} n {v['edits']:3d} torn {v['torn_edits']:3d} wall-edits {v['wall_edits']:3d} "
                  f"(walls {v['walls']}/{v['crossings']}) one-way introduced {v['intro_oneway_edits']:3d} "
                  f"(any {v['any_oneway_edits']:3d}) flank introduced {v['intro_flank_edits']:3d} "
                  f"kept {v['kept_median']} (p10 {v['kept_p10']})")
    out["seconds"] = round(time.time() - t0, 1)
    name = "stitch_postfix_quick.json" if quick else "stitch_postfix.json"
    (S.OUT / name).write_text(json.dumps(out, indent=1), encoding="utf-8")
    cal = out["calibration"]
    ok = (cal["torn_kit_equals_model"] == len(rows) and cal["walls_equal_sweep"] == len(rows)
          and all(v["torn_edits"] == 0 for m, t in out["modes"].items() if m != "unpinned" for v in t.values()))
    print("CALIBRATED, 0 TORN" if ok else "MISMATCH -- see out/" + name)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
