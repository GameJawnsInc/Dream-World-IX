"""O2 AFTER THE FIX (terrain study defects 7-9, 2026-10-08): the edit-atomic disc-4 mirror, through the real kit code.

The kit now (``world/discmirror.py``):
  * gates a cell by comparing each real part as a triangle MULTISET (defect 9);
  * mirrors a group of adjacent written cells whole or not at all (``atomic=True``, what ``auto_mirror`` passes);
  * lets ``world-terrain``/``world-deploy`` hand in a ``replay``: where a written cell cannot be copied, the same
    edit is re-run on disc 4's own ground instead (defect 8).

A. GATE CALIBRATION. The kit's ``_cell_refusal`` against this lane's independent order-invariant instrument
   (``s1_gate.json`` column ``orderinv``) on every cell. Prediction: agreement on every cell; land refused 189 -> 179
   (the 10 reorder-only cells flip).
B. THE G3 DEMO (``s5b_crack_demo.py``'s edit: +4 r16 across an eligible and a refused cell). The old per-cell mirror
   must reproduce the 4.0u step on disc 4 (the instrument can fail); the atomic mirror with the replay must leave
   0.0, both cells edited on disc 4.
C. POPULATION. Random multi-cell reshapes centred near the borders of refused land cells, each written to disc 1 and
   mirrored both ways. A CRACK = an adjacent block pair whose shared-border Y differs on disc 4 by more than the same
   pair does in pure stock disc 4 (+0.05u). Prediction (README O2): the old mirror cracks a share like G3's 7.5% of
   such edits; the atomic mirror cracks 0; the replay refuses only where the verb's own gates refuse on disc 4.
Every write goes to ABSOLUTE scratch folders under ``CACHE_DIR``; the install is only read.
Writes out/o2_postfix.json.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_disc4_edit_reach/o2_postfix.py [--n 400]
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib as L                                       # noqa: E402
from ff9mapkit.world import discmirror as DM          # noqa: E402
from ff9mapkit.world import extract as X              # noqa: E402
from ff9mapkit.world import mesh as M                 # noqa: E402
from ff9mapkit.world import terrain as TER            # noqa: E402

G = L.GAME
TOL = 0.05
SCR = L.CACHE_DIR / "o2"


def quiet(*_a, **_k):
    pass


def eff4(mf, c, cache):
    """Disc 4's effective Terrain of block ``c``: the Disc4 override in ``mf`` if any, else stock disc 4."""
    p = Path(mf) / M.override_relpath(4, c[0], c[1], "0_1", "Terrain")
    if p.is_file():
        return M.blockmesh_from_ff9mesh(p, disc=4, x=c[0], y=c[1])
    if c not in cache:
        try:
            cache[c] = X.read_block(c[0], c[1], disc=4, part="terrain", game=G)
        except ValueError:
            cache[c] = None
    return cache[c]


def border_step(a, ca, b, cb):
    """Max |dy| over coincident vertices on the shared border of adjacent blocks a (at ca) and b (at cb)."""
    if a is None or b is None:
        return None
    dx, dy = cb[0] - ca[0], cb[1] - ca[1]

    def pts(bm, c, side):
        out = {}
        for v in bm.verts:
            if side == "E" and abs(v[0] - 64) < 1e-3 or side == "W" and abs(v[0]) < 1e-3:
                out[round(v[2], 3)] = v[1]
            if side == "S" and abs(v[2] + 64) < 1e-3 or side == "N" and abs(v[2]) < 1e-3:
                out[round(v[0], 3)] = v[1]
        return out
    sa, sb = {(1, 0): ("E", "W"), (-1, 0): ("W", "E"), (0, 1): ("S", "N"), (0, -1): ("N", "S")}[(dx, dy)]
    pa, pb = pts(a, ca, sa), pts(b, cb, sb)
    common = set(pa) & set(pb)
    return max((abs(pa[k] - pb[k]) for k in common), default=None)


def cracks(mf, blocks, cache, stock_cache):
    """Adjacent pairs (in-grid, not wrapping) touching the edit whose disc-4 border step exceeds stock's + TOL."""
    cells = set(blocks) | {n for c in blocks for n in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1),
                                                        (c[0], c[1] - 1))}
    out = []
    for a in sorted(cells):
        for b in ((a[0] + 1, a[1]), (a[0], a[1] + 1)):
            if b not in cells or not (a in blocks or b in blocks):
                continue
            s = border_step(eff4(mf, a, cache), a, eff4(mf, b, cache), b)
            if s is None:
                continue
            key = (a, b)
            if key not in stock_cache:
                stock_cache[key] = border_step(eff4("<stock>", a, cache), a, eff4("<stock>", b, cache), b) or 0.0
            if s > stock_cache[key] + TOL:
                out.append({"pair": [list(a), list(b)], "step": round(s, 3), "stock": round(stock_cache[key], 3)})
    return out


def fresh(name):
    d = SCR / name
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    return d / "FF9CustomMap-o2"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20261008)
    a = ap.parse_args()
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    res = {}
    # ---- A. the gate against the lane's own order-invariant instrument -------------------------------------------
    s1 = json.loads((L.OUT / "s1_gate.json").read_text(encoding="utf-8"))["rows"]
    real1, real4 = DM._real_parts(1, game=G), DM._real_parts(4, game=G)
    agree, disagree, refused_land = 0, [], []
    kit = {}
    for k, r in s1.items():
        c = tuple(int(v) for v in k.split(","))
        v = "SKIP" if DM._cell_refusal(c, real1, real4, 1, 4, "0_1", game=G) else "PASS"
        kit[c] = v
        if v == r["orderinv"].split("(")[0]:                  # the lane labels "SKIP(partset)": a SKIP all the same
            agree += 1
        else:
            disagree.append([list(c), v, r["orderinv"]])
        if r["land"] and v == "SKIP":
            refused_land.append(c)
    flips = sorted(c for c, v in kit.items() if v == "PASS" and s1[f"{c[0]},{c[1]}"]["shipped"] == "SKIP")
    res["A_gate"] = {"cells": len(s1), "agree": agree, "disagree": disagree, "land_refused": len(refused_land),
                     "flipped_from_shipped": [list(c) for c in flips]}
    print("A gate:", {k: v for k, v in res["A_gate"].items() if k != "flipped_from_shipped"}, "flips", flips)
    refused = set(refused_land)
    land = {tuple(int(v) for v in k.split(",")) for k, r in s1.items() if r["land"]}
    eligible = land - refused
    cache, stock_cache = {}, {}

    def run(at, radius, amount, tag):
        """One edit: disc-1 write, then OLD per-cell mirror and NEW atomic mirror + replay, each measured."""
        mf = fresh(tag)
        try:
            s = TER.reshape(str(mf), at=at, radius=radius, amount=amount, disc=1, game=G, skip_mirror=True,
                            allow_entrances=True)
        except ValueError as e:
            return {"disc1": "refused", "why": str(e).splitlines()[0][:120]}
        blocks = {tuple(b["block"]) for b in s["blocks"]}
        if len(blocks) < 2:
            return {"disc1": "single"}
        DM.mirror(str(mf), cells=blocks, game=G, log=quiet)
        old = cracks(mf, blocks, cache, stock_cache)
        shutil.rmtree(Path(mf) / "FF9_Data" / "WorldMap" / "Disc4", ignore_errors=True)
        out = DM.mirror(str(mf), cells=blocks, game=G, atomic=True, log=quiet,
                        replay=lambda d: TER.reshape(str(mf), at=at, radius=radius, amount=amount, disc=d, game=G,
                                                     skip_mirror=True, allow_entrances=True))
        new = cracks(mf, blocks, cache, stock_cache)
        rp = out["replay"]
        mode = ("replay refused" if rp and "refused" in rp else "replayed" if rp else
                "held" if out["held"] else "copied")
        return {"disc1": "ok", "blocks": sorted(map(list, blocks)), "mixed": bool(blocks & refused) and bool(
            blocks - refused), "old_cracks": old, "new_cracks": new, "new_mode": mode,
            "replay_refused": rp.get("refused", "")[:160] if rp and "refused" in rp else None}

    # ---- B. the G3 demo edit ------------------------------------------------------------------------------------
    demo = json.loads((L.OUT / "s5b_crack_demo.json").read_text(encoding="utf-8"))["edit"]
    b = run(tuple(demo["at"]), demo["radius"], demo["amount"], "B_demo")
    res["B_demo"] = {"edit": demo, **b}
    print("B demo:", {k: v for k, v in b.items() if k != "blocks"})
    # ---- C. the population ---------------------------------------------------------------------------------------
    rng = random.Random(a.seed)
    rows, t0 = [], time.time()
    cand = sorted(refused)
    while len([r for r in rows if r.get("disc1") == "ok"]) < a.n and len(rows) < 6 * a.n:
        c = rng.choice(cand)
        side = rng.choice("EWNS")
        u = rng.uniform(4, 60)
        off = rng.uniform(0.5, 10)
        lx, lz = {"E": (64 - off, -u), "W": (off, -u), "N": (u, -off), "S": (u, -64 + off)}[side]
        at = (64 * c[0] + lx, -64 * c[1] + lz)
        radius, amount = rng.choice((8.0, 16.0, 24.0)), rng.choice((2.0, -2.0, 4.0))
        r = run(at, radius, amount, "C")
        r.update({"at": [round(at[0], 3), round(at[1], 3)], "radius": radius, "amount": amount})
        rows.append(r)
        ok = [x for x in rows if x.get("disc1") == "ok"]
        if len(ok) % 50 == 0 and r.get("disc1") == "ok":
            print(f"  {len(ok)} edits, {time.time() - t0:.0f}s: old cracked {sum(1 for x in ok if x['old_cracks'])}, "
                  f"new cracked {sum(1 for x in ok if x['new_cracks'])}", flush=True)
    ok = [x for x in rows if x.get("disc1") == "ok"]
    from collections import Counter
    res["C_population"] = {
        "tried": len(rows), "disc1_refused": sum(1 for x in rows if x.get("disc1") == "refused"),
        "single_block": sum(1 for x in rows if x.get("disc1") == "single"), "edits": len(ok),
        "mixed": sum(1 for x in ok if x["mixed"]),
        "old_cracked": sum(1 for x in ok if x["old_cracks"]),
        "old_cracked_1u": sum(1 for x in ok if any(c["step"] - c["stock"] >= 1.0 for c in x["old_cracks"])),
        "new_cracked": sum(1 for x in ok if x["new_cracks"]),
        "new_modes": dict(Counter(x["new_mode"] for x in ok)),
        "replay_refusals": dict(Counter((x["replay_refused"] or "").split(":")[0][:40] for x in ok
                                        if x["new_mode"] == "replay refused")),
        "seconds": round(time.time() - t0)}
    res["C_rows"] = rows
    print("C population:", res["C_population"])
    ok_all = (not res["A_gate"]["disagree"] and res["A_gate"]["land_refused"] == 179
              and b.get("old_cracks") and not b.get("new_cracks") and b.get("new_mode") == "replayed"
              and res["C_population"]["new_cracked"] == 0 and res["C_population"]["old_cracked"] > 0)
    res["ok"] = bool(ok_all)
    (L.OUT / "o2_postfix.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("ALL AS PREDICTED" if ok_all else "MISMATCH -- see out/o2_postfix.json")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
