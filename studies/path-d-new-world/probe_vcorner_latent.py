"""LATENT RING-TRAP SWEEP — every bench point armed for the V-corner trap class.

The decoded mechanism (probe_vcorner_ringdump): a blocked sheet under the land enters
the ring's NEWEST slot via one full scan whose plan point escapes all walkable-first
tris, then the filter-free newest-first cache answers every fan candidate → permanent
stall. The static predictor of a HARD lock at standable point P:
  (1) some heading's cold full-scan first hit is a BLOCKED tri T,
  (2) T's plan footprint covers ALL 32 fan candidates of P (radius 0.4375),
      each with hit y <= P.y + 2.34375.
Then any walker that stalls on P with T newest is locked for good. Points where only
(1) holds are POISONABLE (partial cover: some headings still escape). READ-ONLY.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402

HEADINGS = [math.radians(11.25 * k) for k in range(32)]
GRID = 0.5
OUTD = HERE / "out" / "vcorner_trap"
PIN = (376.5, -509.5)


def scan_class(world, x, z, origin_y):
    """Cold full scan, returning the hit + whether it is mask-blocked."""
    f = W.full_scan(world, W.block_key(x, z), x, z, origin_y)
    if f is None:
        return None
    mi, ti, hy, mapid, topo = f
    return dict(mi=mi, ti=ti, y=hy, mapid=mapid, topo=topo, ok=topo in W.WALK_OK)


def sweep(world, title):
    x0, x1, z0, z1 = W.REGION
    hard, poisonable = [], []
    n_stand = 0
    x = x0
    while x <= x1 + 1e-9:
        z = z0
        while z <= z1 + 1e-9:
            walk = [s for s in W.all_sheets(world, x, z) if s[1] in W.WALK_OK]
            if not walk:
                z += GRID
                continue
            n_stand += 1
            y = max(s[0] for s in walk)
            origin = y + W.OFFSET
            # (1) blocked first-hits among the 32 cold candidates
            cands = [(x + math.sin(h) * W.SPEED, z + math.cos(h) * W.SPEED)
                     for h in HEADINGS]
            blockers = {}
            for (cx, cz) in cands:
                sc = scan_class(world, cx, cz, origin)
                if sc is not None and not sc["ok"]:
                    bk = W.block_key(cx, cz)
                    blockers[(bk, sc["mi"], sc["ti"])] = sc
            if not blockers:
                z += GRID
                continue
            # (2) does any blocker cover ALL 32 candidates below origin?
            full_cover = None
            for (bk, mi, ti), sc in blockers.items():
                tri = world[bk][mi]["tris"][ti]
                if all(W.block_key(cx, cz) == bk
                       and (hy := W.bary_y(cx, cz, tri)) is not None and hy <= origin
                       for (cx, cz) in cands):
                    full_cover = (bk, mi, ti, sc)
                    break
            rec = dict(x=round(x, 1), z=round(z, 1), y=round(y, 2))
            if full_cover is not None:
                bk, mi, ti, sc = full_cover
                rec.update(part=world[bk][mi]["name"], ti=ti,
                           mapid=sc["mapid"], topo=sc["topo"])
                hard.append(rec)
            else:
                poisonable.append(rec)
            z += GRID
        x += GRID
    print(f"\n=== LATENT SWEEP [{title}]: {n_stand} standable pts, "
          f"{len(hard)} HARD-LOCK-ARMED, {len(poisonable)} poisonable (partial cover) ===")
    # cluster the hard set (4-connected on the 0.5 grid)
    key = {(round(r["x"] * 2), round(r["z"] * 2)): r for r in hard}
    seen, clusters = set(), []
    for k in key:
        if k in seen:
            continue
        comp, stack = [], [k]
        seen.add(k)
        while stack:
            c = stack.pop()
            comp.append(key[c])
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nb = (c[0] + d[0], c[1] + d[1])
                if nb in key and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        cx = sum(r["x"] for r in comp) / len(comp)
        cz = sum(r["z"] for r in comp) / len(comp)
        parts = Counter((r["part"], r["ti"]) for r in comp)
        clusters.append(dict(n=len(comp), cx=round(cx, 1), cz=round(cz, 1),
                             pin_d=round(math.hypot(cx - PIN[0], cz - PIN[1]), 1),
                             tris=[f"{p}#{t}(x{n})" for (p, t), n in parts.most_common(3)]))
    clusters.sort(key=lambda c: -c["n"])
    for c in clusters:
        print(f"   armed cluster n={c['n']:3d} at ({c['cx']:6.1f},{c['cz']:7.1f}) "
              f"pin_d={c['pin_d']:6.1f} tris={c['tris']}")
    return hard, poisonable, clusters


def refine(world, poisonable, title, step=0.1, span=0.5):
    """The proven pin lock lives in a sub-grid sliver (the wedge the wall-slide funnels
    into). Around every poisonable point, sub-sample and re-test the hard predicate."""
    hard = []
    seen_tri = Counter()
    for rec in poisonable:
        px, pz = rec["x"], rec["z"]
        best = None
        k = int(round(span / step))
        for i in range(-k, k + 1):
            for j in range(-k, k + 1):
                x, z = px + i * step, pz + j * step
                walk = [s for s in W.all_sheets(world, x, z) if s[1] in W.WALK_OK]
                if not walk:
                    continue
                y = max(s[0] for s in walk)
                origin = y + W.OFFSET
                cands = [(x + math.sin(h) * W.SPEED, z + math.cos(h) * W.SPEED)
                         for h in HEADINGS]
                blockers = {}
                for (cx, cz) in cands:
                    sc = scan_class(world, cx, cz, origin)
                    if sc is not None and not sc["ok"]:
                        blockers[(W.block_key(cx, cz), sc["mi"], sc["ti"])] = sc
                for (bk, mi, ti), sc in blockers.items():
                    tri = world[bk][mi]["tris"][ti]
                    if all(W.block_key(cx, cz) == bk
                           and (hy := W.bary_y(cx, cz, tri)) is not None and hy <= origin
                           for (cx, cz) in cands):
                        best = dict(x=round(x, 2), z=round(z, 2), y=round(y, 2),
                                    part=world[bk][mi]["name"], ti=ti,
                                    mapid=sc["mapid"], topo=sc["topo"])
                        break
                if best:
                    break
            if best:
                break
        if best:
            hard.append(best)
            seen_tri[(best["part"], best["ti"])] += 1
    print(f"\n=== REFINED [{title}]: {len(hard)} of {len(poisonable)} poisonable pts "
          f"hide a HARD-LOCK sliver within {span}u (step {step}) ===")
    for h in hard[:20]:
        print(f"   sliver at ({h['x']:7.2f},{h['z']:8.2f}) y={h['y']:5.2f} "
              f"poisoner {h['part']}#{h['ti']} mapid={h['mapid']} topo={h['topo']} "
              f"pin_d={math.hypot(h['x'] - PIN[0], h['z'] - PIN[1]):.1f}")
    if seen_tri:
        print("   poisoner tris:", ", ".join(f"{p}#{t} x{n}"
              for (p, t), n in seen_tri.most_common(10)))
    return hard


def main():
    OUTD.mkdir(parents=True, exist_ok=True)
    print("loading LIVE world (the tuck build) ...")
    live = W.load_world()
    hard, poisonable, clusters = sweep(live, "LIVE tuck build")
    hard_fine = refine(live, poisonable, "LIVE tuck build")
    json.dump(dict(hard=hard, hard_fine=hard_fine, poisonable_n=len(poisonable),
                   clusters=clusters),
              open(OUTD / "latent.json", "w"), indent=1)
    print(f"\nreport: {OUTD / 'latent.json'}")


if __name__ == "__main__":
    main()
