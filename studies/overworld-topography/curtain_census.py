"""THE CURTAIN CENSUS -- stock's vertical sealing classes (C1 of the CURTAIN GRAMMAR study).

Registered question (studies/path-d-new-world/CURTAIN-GRAMMAR.md, C1): does stock ship a
GENERAL vertical sealing class beyond the two decoded wall classes (topo-49/50 crest-seeded
interior walls; the topo-58 coastal cliff strip) -- and is "curtain" ONE construction or
SEVERAL?

Method, across ALL stock disc-1 TERRAIN blocks (sea/beach/object parts excluded by design --
the terrain part is the surface the census asks about; a below-side neighbor that lives in a
sea sheet therefore reads FREE here):

  1. Every near-vertical terrain face: |geometric ny| <= 0.2 (normal = normalized
     cross(v1-v0, v2-v0); sign discarded -- winding-independent). Faces group into connected
     components by shared rounded-3dp 3D edges.
  2. Per component: own topograph histogram; drop (y extent, + a local per-column drop via
     2u plan neighborhoods); tri count; the surface class ABOVE / BELOW = topograph of
     non-near-vertical terrain tris sharing the component's TOP / BOTTOM boundary verts
     (top/bottom judged per vert against its 2u-plan local y band); atlas tile cols/rows
     (floor(u/TILE_U), floor(v/TILE_V) of tri uv minima -- raw grid, no phase); and the
     PLAN-OWNER SIGNATURE: for each non-degenerate plan-projected edge, how many DISTINCT
     terrain tris in the block share that plan edge (the known forest-blob-rim signature is
     3 owners per plan edge and zero once-edges -- full_skirt.py ~1511).
  3. Nothing is pre-filtered: the two decoded classes are reported as named rows (own topo
     mostly 49/50 -> ROCK-WALL; mostly 58 -> COASTAL-CLIFF) and everything else is broken
     down by context (dominant class above | below).
  4. Subclass probe: plan-degenerate faces (|ny| <= 0.05, plan area ~ 0) vs merely-steep
     sloped faces, compared on context, drop, and owner signature.

Read-only vs stock disc-1. Artifact -> out/curtain_census.json.
Regenerate: py -X utf8 curtain_census.py
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402

TILE_U, TILE_V = 0.0625, 0.03125
NV_NY = 0.2                                                 # near-vertical gate (~78 deg)
DEGEN_NY = 0.05                                             # plan-degenerate subclass gate
DEGEN_AREA = 0.01                                           # plan area ~ 0 (u^2)
LOCAL_R = 2.0                                               # plan radius for local y bands
OUT = Path(__file__).with_name("out") / "curtain_census.json"
kk = lambda v: (round(v[0], 3), round(v[1], 3), round(v[2], 3))   # noqa: E731

PLATEAU = {10, 11, 12}
ROCK = {49, 50}
LIP = {58}
SEA = {53, 54, 55, 56, 57}
RIVER = {48, 51}
WALK = (set(range(0, 8)) | {10, 11, 12, 13} | set(range(16, 24)) | {27, 28, 30, 31}
        | set(range(32, 39)) | {41, 42, 45, 46, 52})


def grp(t):
    if t in PLATEAU:
        return "plateau"
    if t in ROCK:
        return "rock"
    if t in LIP:
        return "lip"
    if t in SEA:
        return "sea"
    if t in RIVER:
        return "river"
    if t in WALK:
        return "walk"
    return "x"


def dom_label(counter):
    """(dominant_topo, 'grpNN') of a Counter, or (None, 'FREE')."""
    if not counter:
        return None, "FREE"
    t, _ = counter.most_common(1)[0]
    return t, f"{grp(t)}{t}"


def pct(a, q):
    return round(float(np.percentile(a, q)), 2) if len(a) else None


# ---- the scan -------------------------------------------------------------------------------
blocks = X.list_blocks(disc=1)
n_scanned = 0
skipped = []
tot_tris = tot_nv = 0
comp_rows = []

for (bx, by) in blocks:
    try:
        bm = X.read_block(bx, by, disc=1, part="terrain")
    except ValueError:
        skipped.append((bx, by, "no-terrain-part"))
        continue
    except Exception as ex:                                 # noqa: BLE001
        skipped.append((bx, by, f"read-error:{ex}"))
        continue
    n_scanned += 1
    V, U, T = bm.verts, bm.uvs, bm.tangents
    ntri = len(bm.flat_index) // 3
    tot_tris += ntri
    tri_idx = [bm.flat_index[3 * t:3 * t + 3] for t in range(ntri)]
    topo = [X.decode_id(int(round(T[idx[0]][0])))["topograph"] for idx in tri_idx]

    # geometric |ny| + plan area per tri
    absny = []
    parea = []
    for idx in tri_idx:
        a, b, c = (np.array(V[i], dtype=float) for i in idx)
        n = np.cross(b - a, c - a)
        L = float(np.linalg.norm(n))
        absny.append(abs(float(n[1])) / L if L > 1e-12 else None)
        parea.append(0.5 * abs((b[0] - a[0]) * (c[2] - a[2])
                               - (b[2] - a[2]) * (c[0] - a[0])))
    nv = {t for t in range(ntri) if absny[t] is not None and absny[t] <= NV_NY}
    tot_nv += len(nv)
    if not nv:
        continue

    # block-wide DISTINCT-tri owners per non-degenerate plan edge (rounded 3dp)
    plan_owner = defaultdict(set)
    for t, idx in enumerate(tri_idx):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            pa = (round(V[idx[a]][0], 3), round(V[idx[a]][2], 3))
            pb = (round(V[idx[b]][0], 3), round(V[idx[b]][2], 3))
            if pa == pb:
                continue                                    # vertical edge: plan-degenerate
            plan_owner[tuple(sorted((pa, pb)))].add(t)

    # components of near-vertical tris by shared 3D edges
    edge_nv = defaultdict(list)
    for t in nv:
        idx = tri_idx[t]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge_nv[tuple(sorted((kk(V[idx[a]]), kk(V[idx[b]]))))].append(t)
    adj = defaultdict(set)
    for e, ts in edge_nv.items():
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                adj[ts[i]].add(ts[j])
                adj[ts[j]].add(ts[i])
    seen = set()
    comps = []
    for s in nv:
        if s in seen:
            continue
        comp = {s}
        st = [s]
        while st:
            t = st.pop()
            for t2 in adj[t]:
                if t2 not in comp:
                    comp.add(t2)
                    st.append(t2)
        seen |= comp
        comps.append(sorted(comp))

    for comp in comps:
        cverts = {}
        for t in comp:
            for i in tri_idx[t]:
                cverts[kk(V[i])] = V[i]
        P = np.array(list(cverts.values()), dtype=float)
        keys = list(cverts.keys())
        drop_max = float(P[:, 1].max() - P[:, 1].min())

        # top/bottom boundary verts, judged against the LOCAL (2u plan) y band
        topv, botv = set(), set()
        local_drops = []
        for i, p in enumerate(P):
            d2 = (P[:, 0] - p[0]) ** 2 + (P[:, 2] - p[2]) ** 2
            m = d2 <= LOCAL_R * LOCAL_R
            ly = P[m, 1]
            lo, hi = float(ly.min()), float(ly.max())
            band = hi - lo
            tol = max(0.3, 0.15 * band)
            if p[1] >= hi - tol:
                topv.add(keys[i])
                local_drops.append(round(float(p[1]) - lo, 2))
            if p[1] <= lo + tol:
                botv.add(keys[i])

        above, below = Counter(), Counter()
        for t in range(ntri):
            if t in nv:
                continue
            ks = [kk(V[i]) for i in tri_idx[t]]
            if any(k in topv for k in ks):
                above[topo[t]] += 1
            if any(k in botv for k in ks):
                below[topo[t]] += 1

        own = Counter(topo[t] for t in comp)
        tiles = Counter()
        for t in comp:
            us = [U[i][0] for i in tri_idx[t]]
            vs = [U[i][1] for i in tri_idx[t]]
            tiles[(int(math.floor(min(us) / TILE_U)),
                   int(math.floor(min(vs) / TILE_V)))] += 1

        owners = []
        deg_edges = 0
        seen_pe = set()
        for t in comp:
            idx = tri_idx[t]
            for a, b in ((0, 1), (1, 2), (2, 0)):
                pa = (round(V[idx[a]][0], 3), round(V[idx[a]][2], 3))
                pb = (round(V[idx[b]][0], 3), round(V[idx[b]][2], 3))
                if pa == pb:
                    deg_edges += 1
                    continue
                pe = tuple(sorted((pa, pb)))
                if pe in seen_pe:
                    continue
                seen_pe.add(pe)
                owners.append(len(plan_owner[pe]))
        n_pe = len(owners)
        n_once = sum(1 for o in owners if o == 1)
        n_own3 = sum(1 for o in owners if o == 3)
        own_ct = Counter(owners)                            # full owner-count histogram

        degf = sum(1 for t in comp
                   if absny[t] <= DEGEN_NY or parea[t] < DEGEN_AREA) / len(comp)
        own_dom, own_lab = dom_label(own)
        ab_dom, ab_lab = dom_label(above)
        be_dom, be_lab = dom_label(below)
        if be_lab == "FREE":
            be_lab = "FREE"                                 # no terrain below the base
        if ab_lab == "FREE":
            ab_lab = "NONE"                                 # no terrain above the top

        frac_rock = sum(v for k, v in own.items() if k in ROCK) / len(comp)
        frac_lip = own.get(58, 0) / len(comp)
        if frac_rock >= 0.5:
            klass = "ROCK-WALL"
        elif frac_lip >= 0.5:
            klass = "COASTAL-CLIFF"
        else:
            klass = "OTHER"

        wx = round(bx * 64 + float(P[:, 0].mean()), 1)
        wz = round(-by * 64 + float(P[:, 2].mean()), 1)
        comp_rows.append(dict(
            blk=(bx, by), world=(wx, round(float(P[:, 1].mean()), 1), wz),
            tris=len(comp), klass=klass,
            own={str(k): v for k, v in own.most_common(4)}, own_dom=own_dom,
            above={str(k): v for k, v in above.most_common(4)}, above_dom=ab_dom,
            below={str(k): v for k, v in below.most_common(4)}, below_dom=be_dom,
            ctx=f"{ab_lab}|{be_lab}",
            drop=round(drop_max, 2), drop_loc=pct(local_drops, 50),
            degf=round(degf, 2),
            ny_med=round(float(np.median([absny[t] for t in comp])), 3),
            tiles={f"{c},{r}": n for (c, r), n in tiles.most_common(4)},
            pe=n_pe, once=n_once, own3=n_own3,
            once_f=round(n_once / n_pe, 3) if n_pe else None,
            own3_f=round(n_own3 / n_pe, 3) if n_pe else None,
            own_ct={str(k): v for k, v in sorted(own_ct.items())},
            deg_edges=deg_edges))


# ---- summaries ------------------------------------------------------------------------------
def row_stats(rows, label):
    if not rows:
        print(f"   {label}: 0 components")
        return {}
    dr = [r["drop"] for r in rows]
    dl = [r["drop_loc"] for r in rows if r["drop_loc"] is not None]
    dg = [r["degf"] for r in rows]
    of = [r["once_f"] for r in rows if r["once_f"] is not None]
    o3 = [r["own3_f"] for r in rows if r["own3_f"] is not None]
    z_once = sum(1 for r in rows if r["once_f"] == 0.0)
    free_b = sum(1 for r in rows if r["ctx"].endswith("|FREE"))
    idm = sum(1 for r in rows
              if r["above_dom"] is not None and r["own_dom"] == r["above_dom"])
    idb = sum(1 for r in rows
              if r["below_dom"] is not None and r["own_dom"] == r["below_dom"])
    tl = Counter()
    oc = Counter()
    for r in rows:
        for k, v in r["tiles"].items():
            tl[k] += v
        for k, v in r["own_ct"].items():
            oc[int(k)] += v
    n = len(rows)
    print(f"   {label}: {n} comps, {sum(r['tris'] for r in rows)} tris")
    print(f"      drop: med {pct(dr, 50)}u p90 {pct(dr, 90)} max {max(dr)}; "
          f"local col drop med {pct(dl, 50)}u")
    print(f"      plan-degenerate tri frac: med {pct(dg, 50)} "
          f"(fully >=0.9: {sum(1 for d in dg if d >= 0.9)}/{n}; "
          f"sloped <=0.1: {sum(1 for d in dg if d <= 0.1)}/{n})")
    print(f"      owner sig: once-frac med {pct(of, 50)}; ZERO-once comps "
          f"{z_once}/{n} ({z_once / n:.0%}); 3-owner-frac med {pct(o3, 50)}")
    print(f"      own topo == ABOVE dom: {idm}/{n} ({idm / n:.0%}); "
          f"== BELOW dom: {idb}/{n}; below FREE: {free_b}/{n} ({free_b / n:.0%})")
    print(f"      top tiles (c,r): {tl.most_common(6)}")
    print(f"      plan-edge OWNER-count hist (edges): {dict(sorted(oc.items()))}")
    return dict(n=n, tris=sum(r["tris"] for r in rows),
                drop_med=pct(dr, 50), drop_p90=pct(dr, 90),
                drop_loc_med=pct(dl, 50), degf_med=pct(dg, 50),
                fully_degen=sum(1 for d in dg if d >= 0.9),
                sloped=sum(1 for d in dg if d <= 0.1),
                once_f_med=pct(of, 50), zero_once=z_once, own3_f_med=pct(o3, 50),
                own_eq_above=idm, own_eq_below=idb, below_free=free_b,
                owner_hist={str(k): v for k, v in sorted(oc.items())},
                top_tiles=tl.most_common(8))


all_rows = comp_rows
sub_rows = [r for r in comp_rows if r["drop"] >= 1.0]       # substantive seals
print(f"population: {n_scanned} blocks scanned of {len(blocks)} listed "
      f"({len(skipped)} skipped), {tot_tris} terrain tris, {tot_nv} near-vertical tris, "
      f"{len(all_rows)} components ({len(sub_rows)} substantive: drop >= 1.0u)\n")
for b in skipped:
    print(f"   skipped {b}")

print("== NAMED CLASS ROWS (substantive components) ==")
summary = {}
for klass in ("ROCK-WALL", "COASTAL-CLIFF", "OTHER"):
    rows = [r for r in sub_rows if r["klass"] == klass]
    summary[klass] = row_stats(rows, klass)
triv = [r for r in all_rows if r["drop"] < 1.0]
print(f"   (trivial drop<1.0u components, all classes: {len(triv)} comps, "
      f"{sum(r['tris'] for r in triv)} tris -- excluded from the rows above)")

print("\n== OTHER, BY CONTEXT (above|below) ==")
others = [r for r in sub_rows if r["klass"] == "OTHER"]
ctx_tab = defaultdict(list)
for r in others:
    ctx_tab[r["ctx"]].append(r)
ctx_out = {}
for ctx, rows in sorted(ctx_tab.items(), key=lambda q: -len(q[1])):
    dr = [r["drop"] for r in rows]
    dg = [r["degf"] for r in rows]
    z1 = sum(1 for r in rows if r["once_f"] == 0.0)
    idm = sum(1 for r in rows
              if r["above_dom"] is not None and r["own_dom"] == r["above_dom"])
    own_hist = Counter()
    tl = Counter()
    for r in rows:
        own_hist[r["own_dom"]] += 1
        for k, v in r["tiles"].items():
            tl[k] += v
    ex = [dict(blk=r["blk"], world=r["world"], tris=r["tris"], drop=r["drop"])
          for r in sorted(rows, key=lambda q: -q["tris"])[:4]]
    print(f"   {ctx:24s}: n={len(rows):3d} tris={sum(r['tris'] for r in rows):4d} "
          f"drop med {pct(dr, 50)}u  degf med {pct(dg, 50)}  zero-once {z1}/{len(rows)}  "
          f"own==above {idm}/{len(rows)}  own topo {own_hist.most_common(3)}  "
          f"tiles {tl.most_common(3)}")
    for e in ex[:2]:
        print(f"        e.g. blk {e['blk']} world {e['world']} "
              f"{e['tris']} tris drop {e['drop']}u")
    ctx_out[ctx] = dict(n=len(rows), tris=sum(r["tris"] for r in rows),
                        drop_med=pct(dr, 50), drop_p90=pct(dr, 90),
                        degf_med=pct(dg, 50), zero_once=z1,
                        own_eq_above=idm,
                        own_dom_hist={str(k): v for k, v in own_hist.most_common(6)},
                        top_tiles=tl.most_common(6), examples=ex)

print("\n== SUBCLASS: plan-degenerate vs sloped (substantive OTHER) ==")
sub_out = {}
for name, rows in (("fully-degenerate (degf>=0.9)", [r for r in others if r["degf"] >= 0.9]),
                   ("mixed (0.1<degf<0.9)", [r for r in others if 0.1 < r["degf"] < 0.9]),
                   ("sloped (degf<=0.1)", [r for r in others if r["degf"] <= 0.1])):
    print(f"   -- {name} --")
    sub_out[name] = row_stats(rows, name)
    ch = Counter(r["ctx"] for r in rows)
    print(f"      contexts: {ch.most_common(6)}")
    sub_out[name]["contexts"] = {k: v for k, v in ch.most_common(10)}

print("\n== THE EXEMPLAR ANCHOR: the (15,14) forest-blob rim ==")
for r in comp_rows:
    if tuple(r["blk"]) == (15, 14) and r["klass"] == "OTHER" and r["tris"] >= 5:
        print(f"   {r['tris']} tris drop {r['drop']}u degf {r['degf']} ctx {r['ctx']} "
              f"own {r['own']} tiles {r['tiles']} owner-hist {r['own_ct']} "
              f"once {r['once']}/{r['pe']}")

print("\n== THE REGISTERED ANSWER, IN NUMBERS ==")
n_o = len(others)
if n_o:
    a_deg = sum(1 for r in others if r["degf"] >= 0.9)
    a_z1 = sum(1 for r in others if r["once_f"] == 0.0)
    a_id = sum(1 for r in others
               if r["above_dom"] is not None and r["own_dom"] == r["above_dom"])
    a_all3 = sum(1 for r in others if r["degf"] >= 0.9 and r["once_f"] == 0.0
                 and r["above_dom"] is not None and r["own_dom"] == r["above_dom"])
    print(f"   substantive OTHER (the non-wall, non-cliff vertical seals): {n_o} comps")
    print(f"      fully plan-degenerate: {a_deg}/{n_o} ({a_deg / n_o:.0%})")
    print(f"      zero once-edges (the blob signature): {a_z1}/{n_o} ({a_z1 / n_o:.0%})")
    print(f"      own topo continues the surface ABOVE: {a_id}/{n_o} ({a_id / n_o:.0%})")
    print(f"      ALL THREE at once (one-construction candidate): {a_all3}/{n_o} "
          f"({a_all3 / n_o:.0%})")
    print(f"      distinct contexts: {len(ctx_tab)}; "
          f"top: {[(k, len(v)) for k, v in sorted(ctx_tab.items(), key=lambda q: -len(q[1]))[:5]]}")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(dict(
    population=dict(blocks_listed=len(blocks), blocks_scanned=n_scanned,
                    skipped=skipped, terrain_tris=tot_tris, nearvert_tris=tot_nv,
                    components=len(all_rows), substantive=len(sub_rows),
                    trivial=len(triv)),
    gates=dict(nv_ny=NV_NY, degen_ny=DEGEN_NY, degen_area=DEGEN_AREA,
               local_r=LOCAL_R, substantive_drop=1.0),
    classes=summary,
    other_by_context=ctx_out,
    degen_subclass=sub_out,
    comps=comp_rows), indent=0))
print(f"\nartifact -> {OUT}")
