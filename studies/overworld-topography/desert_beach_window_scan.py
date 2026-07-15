"""THE DESERT VIRGIN-WINDOW SCAN -- where can a NEW desert beach lawfully mint?

Rung B of the desert beach: prove the family end-to-end in-game by authoring a new
beach on a bare stretch of REAL desert coast (the real water ladder + the real desert
berm; zero new machinery -- virgin_mint with pins_from a real desert beach block).
The scan follows THE BUILDERS-ARE-THE-ORACLE law: candidate anchor pairs on each
block's real shoreline chain are certified by virgin_mint dry-builds; refusals name
the laws.

Candidates: Outer-Continent blocks with topo-17 land + real sea parts + NO beach1.
    py studies/overworld-topography/desert_beach_window_scan.py
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import coastmorph as CM                # noqa: E402
from ff9mapkit.world import transplant as TR                # noqa: E402

PINS = (20, 5)                                              # run 39 + cap 2 -- (20,6) has
                                                            # NO decodable sand caps
OUTD = Path(__file__).with_name("out")
out = {"pins_from": list(PINS), "windows": []}

# ---- candidates ---------------------------------------------------------------------------------
# THE (18,3) LESSON: a block that never had a beach has NO Beach1/Sea2/Sea1 prefab
# transforms -- an in-place morph can't host the minted foam/wash there (overrides
# bind to existing transforms). So the lawful in-place targets are the desert BEACH
# blocks themselves: mint a SECOND beach on a bare stretch (the separation law gates
# inside virgin_mint), pins byte-read from the block's own band.
cands = []
for bx in range(12, 22):
    for by in range(0, 9):
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except ValueError:
            continue
        try:
            X.read_block(bx, by, disc=1, part="beach1")
        except ValueError:
            continue                                        # no beach -> can't host one
        missing = []
        for p in ("sea2", "sea1"):
            try:
                X.read_block(bx, by, disc=1, part=p)
            except ValueError:
                missing.append(p)
        if missing:
            continue                                        # the mint emits into these
        c = Counter()
        for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
            c[X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]] += 1
        if c.get(17, 0) >= 40:
            cands.append(((bx, by), c.get(17, 0)))
cands.sort(key=lambda kv: -kv[1])
print(f"candidate desert BEACH blocks (full part set): {[(b, n) for b, n in cands]}")

# ---- per candidate: the shoreline chain, then window dry-builds ---------------------------------
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
found = []
for (blk, n17) in cands:
    terr = TR.world_tris(*blk, "terrain", disc=1)
    water_k = set()
    for p in ("sea2", "sea1", "sea3", "sea5", "sea4"):
        for t3 in TR.world_tris(*blk, p, disc=1):
            for v in t3:
                water_k.add(kk(v[0]))
    e_count = defaultdict(int)
    pos_of = {}
    for t3 in terr:
        ps = [v[0] for v in t3]
        for v in t3:
            pos_of.setdefault(kk(v[0]), v[0])
        for i in range(3):
            e_count[frozenset((kk(ps[i]), kk(ps[(i + 1) % 3])))] += 1
    adj = defaultdict(set)
    for e, c in e_count.items():
        if c != 1 or len(e) != 2:
            continue
        a, b = tuple(e)
        if a in water_k and b in water_k:
            adj[a].add(b)
            adj[b].add(a)
    if not adj:
        continue
    # walk the longest chain
    seen, chains = set(), []
    for start in sorted(adj):
        if start in seen or len(adj[start]) != 1:
            continue
        ch, cur, prev = [start], start, None
        seen.add(start)
        while True:
            nxt = [q for q in adj[cur] if q != prev]
            if not nxt or nxt[0] in seen:
                break
            prev, cur = cur, nxt[0]
            seen.add(cur)
            ch.append(cur)
        chains.append(ch)
    if not chains:
        continue
    chain = max(chains, key=len)
    pts = [pos_of[k] for k in chain]
    arc = [0.0]
    for a, b in zip(pts, pts[1:]):
        arc.append(arc[-1] + math.hypot(b[0] - a[0], b[2] - a[2]))
    print(f"\n{blk}: shoreline chain {len(pts)} verts, {arc[-1]:.0f}u")
    n_try = n_hit = 0
    refuse = Counter()
    for i in range(len(pts) - 1):
        if n_hit >= 2 or n_try >= 120:
            break
        spans_tried = 0
        for j in range(i + 1, len(pts)):
            span = arc[j] - arc[i]
            if span < 6.0:
                continue
            if span > 16.0 or spans_tried >= 3:
                break
            spans_tried += 1
            n_try += 1
            s, e = (pts[i][0], pts[i][2]), (pts[j][0], pts[j][2])
            mid = ((s[0] + e[0]) / 2.0, (s[1] + e[1]) / 2.0)
            banks = [None] + [dict(center=list(mid), radius=r, shore_slope=sl)
                              for r in (12.0, 18.0) for sl in (0.55, 0.35)]
            for bank in banks:
                try:
                    tw, notes = CM.build_shore_tweaks(
                        blk, (1, 1), bank=bank,
                        mint=dict(start=list(s), end=list(e),
                                  pins_from=[20, 5] if blk != (20, 5) else None),
                        disc=1)
                    n_emit = sum(len(t.tris) for t in tw
                                 if type(t).__name__ == "EmitTris")
                    print(f"   WINDOW OK{' (banked)' if bank else ''}: {s} -> {e} "
                          f"(arc {span:.1f}u, {n_emit} tris, bank={bank})")
                    found.append(dict(block=list(blk), start=list(s), end=list(e),
                                      mid=list(mid), arc=round(span, 1), tris=n_emit,
                                      bank=bank))
                    n_hit += 1
                    break
                except (ValueError, KeyError, IndexError) as ex:
                    refuse[str(ex)[:64]] += 1
            if n_hit >= 2:
                break
    if refuse and not n_hit:
        top = refuse.most_common(3)
        for msg, n in top:
            print(f"   refusals x{n}: {msg}")
    if len(found) >= 4:
        break

out["windows"] = found
OUTD.mkdir(exist_ok=True)
(OUTD / "desert_beach_windows.json").write_text(json.dumps(out, indent=1))
print(f"\n{len(found)} lawful window(s) -> {OUTD / 'desert_beach_windows.json'}")
