"""THE ECOTONE-STRIP DECODE -- proves (or falsifies) THE ECOTONE-STRIP TRANSLATION FINDING.

Prior earmarked fits (README.md, "THE MIXED-BIOME LANDMASS" section), taken off a 3-6
specimen-block sample per pair, recorded that family-boundary edges wear a dedicated
ONE-TILE STRIP COLUMN that looks like the grass "B" transition rect
(``grassland.FAM_REGION['B']`` = STRIP_U x STRIPS_V, a 1-tile-wide, 4-v-row column)
TRANSLATED by a family-pair-specific (du,dv) -- the same TRANSLATION LAW that grew the
mains GROUNDS table -- but at APPROXIMATE precision only, never proven at 5dp:
    desert|dunes strip  ~ B + (-0.13478, -0.06738)
    grass|desert strip  ~ B + (+0.5244,  -0.047)   (u[0.918,0.9785])
No other pair was even attempted. THE NO-ENCLOSED-DUNES LAW means a dunes patch has no
verbatim carry window and needs THIS vocabulary to compose one -- this is the highest-
leverage unblock in the arc.

METHOD (obeys THE METHOD LAW + THE 5DP BAR):
  A. RE-CENSUS the real adjacency graph map-wide -- all 480 (bx,by) candidates, not the
     prior 3-6-block specimen lists. Every walkable-family pair, edge counts, block
     counts, mains|mains fraction, lattice fraction, y-step (flat weld vs slope).
  B. per pair, per side: classify EVERY boundary-edge-owner triangle map-wide (dedup'd,
     not per-edge so a corner tri touching 2 boundary edges isn't double counted) against
     every family's translated MAINS rect + meadowD. Unclassified = RESIDUAL (the strip
     candidate).
  C. per side with residual tris: group residual tris by 4u world cell, per-cell EXACT
     LINEAR affine fit (u,v linear in x,z; residual<1e-4 -- garbage/decal cells fail and
     are dropped, counted). A linear cell's planar (x,z) triangle-area COVERAGE of the 4u
     cell decides how its rect is read: >=90% covered -> trust the affine EXTRAPOLATED to
     the cell's own lattice corners (the mains-style full-tile rect, ground_families'
     method); otherwise PARTIAL -> use the raw observed vertex bbox only (never
     extrapolate past what is actually drawn -- a sub-cell strip must not be inflated).
  D. cluster cell rects into ROWS by their 5dp-mode v0 (Counter-mode, same trick as
     ground_families' ``mode5``); each row's (u0,u1,v0,v1) is the map-wide 5dp MODE
     across every contributing cell (dozens, not a handful).
  E. THE TRANSLATION FIT, OUTER BOUNDS ONLY: du from the column-wide u0/u1 vs STRIP_U
     (checked for BOTH consistency across rows -- proves "one column" -- and against the
     grass reference); dv by trying every valid row-alignment hypothesis j (the observed
     k rows land on STRIPS_V[j..j+k-1]) and keeping the hypothesis with minimum spread
     across all 2k v-edges. PROVEN-5DP requires du_spread<2e-5 AND k>=2 (a single row
     cannot disambiguate which of 4 hypotheses it is -- reported as an ambiguous EARMARK
     with all 4 candidates) AND the winning v-spread<2e-5. A pair whose best spread never
     drops under ~0.001 is FALSIFIED as a B-translation -- its raw rect is still reported
     at full mode-5dp precision, just not claimed to be a translated B copy.
  F. explicit confirm/refute checks: desert|scrub "scrub mains IS the transition, no
     dedicated strip" and desert|brush "desert plain, brush wears its own edge column".

Artifacts -> out/ecotone_strip_decode.json. Run from the repo root:
    py studies/overworld-topography/ecotone_strip_decode.py
"""
import itertools
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402
from ff9mapkit.world import grassland as G                  # noqa: E402

BLOCK = 64.0
EPS = 0.006
OUTD = Path(__file__).with_name("out")
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))


def mode5(vals):
    return Counter(round(v, 5) for v in vals).most_common(1)[0][0]


# ---- family membership (recomputed, not trusted from any prior script) ----------------------------
FAM_OF = {}
for t in (0, 1, 2, 3, 10, 11, 12, 13, 42):
    FAM_OF[t] = "grass"
for t in (4, 5, 6):
    FAM_OF[t] = "scrub"
for t in (17, 16, 19, 20):
    FAM_OF[t] = "desert"
for t in (27, 28):
    FAM_OF[t] = "snow"
FAM_OF[38] = "brush"
FAM_OF[41] = "dunes"
FAM_OF[45] = FAM_OF[46] = "canyon"
MAIN_FAMS = ("grass", "scrub", "desert", "brush", "dunes", "snow", "canyon")


def mains_rect(fam):
    m = G.FAM_REGION["main"]
    g = G.GROUNDS[fam]
    return (m[0] + g["mains_du"], m[1] + g["mains_dv"], m[2] + g["mains_du"], m[3] + g["mains_dv"])


RECTS = {fam: mains_rect(fam) for fam in MAIN_FAMS}
RECTS["meadowD"] = G.FAM_REGION["D"]
print("== mains rects in play (5dp, translated per GROUNDS)")
for name, r in RECTS.items():
    print(f"   {name:9s} u[{r[0]:.5f},{r[2]:.5f}] v[{r[1]:.5f},{r[3]:.5f}]")
print(f"   grass B (STRIP_U x STRIPS_V outer) = {G.FAM_REGION['B']}  STRIPS_V={G.STRIPS_V}")


def uv_class(uvs):
    for name, r in RECTS.items():
        if all(r[0] - EPS <= u <= r[2] + EPS and r[1] - EPS <= v <= r[3] + EPS for (u, v) in uvs):
            return name
    return None


# ---- A+B. ONE map-wide pass: adjacency census + per-pair boundary-owner harvesting ----------------
pair_edges = Counter()
pair_blocks = defaultdict(set)
pair_detail = defaultdict(lambda: dict(mains_both=0, lattice=0, n=0, ystep=[]))
side_class = defaultdict(lambda: defaultdict(Counter))     # side_class[pair][fam][class] = n (dedup'd tris)
resid_cells = defaultdict(lambda: defaultdict(list))       # resid_cells[pair][fam] -> [(cell, w, uv), ...]
n_blocks_read = 0

for bx in range(24):
    for by in range(20):
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except ValueError:
            continue
        n_blocks_read += 1
        tris = []
        for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            fam = FAM_OF.get(topo)
            if fam is None:
                continue
            w = [(bm.verts[j][0] + BLOCK * bx, bm.verts[j][1], bm.verts[j][2] - BLOCK * by) for j in tri]
            uv = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
            tris.append(dict(fam=fam, w=w, uv=uv))
        edge_owner = defaultdict(list)
        for ti, t in enumerate(tris):
            ks = [kk(p) for p in t["w"]]
            for i in range(3):
                e = frozenset((ks[i], ks[(i + 1) % 3]))
                if len(e) == 2:
                    edge_owner[e].append(ti)
        seen = set()
        for e, owners in edge_owner.items():
            fams = {tris[ti]["fam"] for ti in owners}
            if len(fams) != 2:
                continue
            pair = tuple(sorted(fams))
            pair_edges[pair] += 1
            pair_blocks[pair].add((bx, by))
            d = pair_detail[pair]
            d["n"] += 1
            both_own = all(uv_class(tris[ti]["uv"]) == tris[ti]["fam"] for ti in owners)
            d["mains_both"] += both_own
            (a, b) = sorted(e)
            if (abs(a[0] - b[0]) < 1e-6 and abs(a[0] / 4 - round(a[0] / 4)) < 1e-3) or \
               (abs(a[2] - b[2]) < 1e-6 and abs(a[2] / 4 - round(a[2] / 4)) < 1e-3):
                d["lattice"] += 1
            d["ystep"].append(abs(a[1] - b[1]))
            for ti in owners:
                fam = tris[ti]["fam"]
                key = (pair, ti)
                if key in seen:
                    continue
                seen.add(key)
                uv, w = tris[ti]["uv"], tris[ti]["w"]
                cls = uv_class(uv)
                side_class[pair][fam][cls or "RESIDUAL"] += 1
                if cls is None:
                    cx = sum(p[0] for p in w) / 3.0
                    cz = sum(p[2] for p in w) / 3.0
                    cell = (math.floor(cx / 4.0), math.floor(cz / 4.0))
                    resid_cells[pair][fam].append((cell, w, uv))

print(f"\nblocks read: {n_blocks_read}/480")

out = {"blocks_read": n_blocks_read, "pairs": {}}

print("\n== A. family-pair shared edges (map-wide RE-CENSUS; zero = the pair NEVER touches)")
for i, f1 in enumerate(MAIN_FAMS):
    for f2 in MAIN_FAMS[i + 1:]:
        pair = tuple(sorted((f1, f2)))
        n = pair_edges.get(pair, 0)
        if n == 0:
            print(f"   {f1:7s}|{f2:7s}     0 edges  -- NEVER touch")
            continue
        d = pair_detail[pair]
        ys = sorted(d["ystep"])
        nblk = len(pair_blocks[pair])
        print(f"   {f1:7s}|{f2:7s} {n:5d} edges over {nblk:3d} blocks  "
              f"mains-both {d['mains_both']}/{d['n']} ({d['mains_both']/d['n']:.0%})  "
              f"lattice {d['lattice']}/{d['n']} ({d['lattice']/d['n']:.0%})  "
              f"ystep p50 {ys[len(ys)//2]:.3f} max {ys[-1]:.3f}")


# ---- C+D+E. per-side strip decode -------------------------------------------------------------
def strip_decode(entries):
    """entries: [(cell, w[3], uv[3]), ...] residual tris for one side of one pair."""
    cell_tris = defaultdict(list)
    for cell, w, uv in entries:
        cell_tris[cell].append((w, uv))
    cell_rects = {}
    n_nonlinear = n_full = n_partial = 0
    for cell, tl in cell_tris.items():
        rows, ru, rv = [], [], []
        for w, uv in tl:
            for (x, y, z), (u, v) in zip(w, uv):
                rows.append([x, z, 1.0])
                ru.append(u)
                rv.append(v)
        Am = np.array(rows)
        if len(rows) < 3 or np.linalg.matrix_rank(Am) < 3:
            n_nonlinear += 1
            continue
        cu, *_ = np.linalg.lstsq(Am, np.array(ru), rcond=None)
        cv, *_ = np.linalg.lstsq(Am, np.array(rv), rcond=None)
        res = max(float(np.abs(Am @ cu - ru).max()), float(np.abs(Am @ cv - rv).max()))
        if res >= 1e-4:
            n_nonlinear += 1
            continue
        us = [u for _, uv in tl for (u, v) in uv]
        vs = [v for _, uv in tl for (u, v) in uv]
        raw = (min(us), max(us), min(vs), max(vs))
        area, seen_tri = 0.0, set()
        for w, uv in tl:
            key = tuple(sorted(kk(p) for p in w))
            if key in seen_tri:
                continue
            seen_tri.add(key)
            (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = w
            area += abs((x1 - x0) * (z2 - z0) - (x2 - x0) * (z1 - z0)) / 2.0
        coverage = area / 16.0
        (i, j) = cell
        if coverage >= 0.9:
            corn = [(4.0 * i, 4.0 * j), (4.0 * (i + 1), 4.0 * j),
                    (4.0 * i, 4.0 * (j + 1)), (4.0 * (i + 1), 4.0 * (j + 1))]
            us_c = [cu[0] * x + cu[1] * z + cu[2] for (x, z) in corn]
            vs_c = [cv[0] * x + cv[1] * z + cv[2] for (x, z) in corn]
            rect = (min(us_c), max(us_c), min(vs_c), max(vs_c))
            n_full += 1
            full = True
        else:
            rect = raw
            n_partial += 1
            full = False
        cell_rects[cell] = dict(rect=rect, coverage=round(coverage, 3), full=full, ntris=len(seen_tri))
    return cell_rects, n_nonlinear, n_full, n_partial


def cluster_rows(cell_rects, min_cells=3):
    v0_of = {c: r["rect"][2] for c, r in cell_rects.items()}
    v0_counts = Counter(round(v, 5) for v in v0_of.values())
    rows = []
    for v0mode, n in v0_counts.most_common():
        if n < min_cells:
            continue
        members = [c for c, v in v0_of.items() if round(v, 5) == v0mode]
        u0 = mode5(cell_rects[c]["rect"][0] for c in members)
        u1 = mode5(cell_rects[c]["rect"][1] for c in members)
        v0 = mode5(cell_rects[c]["rect"][2] for c in members)
        v1 = mode5(cell_rects[c]["rect"][3] for c in members)
        rows.append(dict(u0=u0, u1=u1, v0=v0, v1=v1, ncells=len(members)))
    rows.sort(key=lambda r: r["v0"])
    return rows


def fit_column(rows):
    """Translation fit vs the grass B column, THE METHOD LAW applied twice over:

    (1) row-ALIGNMENT is an order-preserving SUBSET of the 4 STRIPS_V slots (not just a
        contiguous window) -- real data can skip a row a specimen set never happened to
        touch (caught live: grass|desert's grass side has rows 0,1,3 with row 2 absent).
    (2) the v-translation spread test uses OUTER BOUNDS ONLY -- the first row's v0 and
        the last row's v1 -- exactly like the mains 2x2 fit skips the internal
        quadrant-split edge. Internal row-to-row edges carry the ~1-texel (0.00098)
        painted gutter and are reported separately as a diagnostic, never gating the
        verdict (mirrors ground_families_anatomy's "internal-edge modes" print).
    """
    k = len(rows)
    if k == 0:
        return None
    u0s = [r["u0"] for r in rows]
    u1s = [r["u1"] for r in rows]
    u0_row_spread = max(u0s) - min(u0s)
    u1_row_spread = max(u1s) - min(u1s)
    u0m, u1m = float(np.median(u0s)), float(np.median(u1s))
    du0 = u0m - G.STRIP_U[0]
    du1 = u1m - G.STRIP_U[1]
    du = round(float(np.median([du0, du1])), 5)
    du_spread = round(abs(du0 - du1), 6)
    # row-PITCH check: consecutive observed row v0's should be exact TILE_V multiples
    # apart if this is really "the same column, several rows" (independent of any B
    # alignment -- a structural self-consistency check)
    v0s = [r["v0"] for r in rows]
    pitch_resid = [abs((b - a) - round((b - a) / 0.03125) * 0.03125) for a, b in zip(v0s, v0s[1:])]
    pitch_ok = all(p < 2e-5 for p in pitch_resid) if pitch_resid else True
    # for k in {2,3} a consecutive-window's OUTER span is often numerically IDENTICAL
    # for more than one starting offset (row0 is 1 texel shorter than rows1-3, so e.g.
    # rows(0,1,2) and rows(1,2,3) both span exactly 0.09277 -- caught live on
    # desert|grass) -- THE OUTER BOUNDS TEST ALONE CAN TIE. Rank every combo by outer
    # spread first (the proof criterion), break ties by internal-edge residual (still
    # informative even though gutter-noisy), and report every tie so a false single
    # "winner" is never silently presented as resolved.
    cands = []
    for combo in itertools.combinations(range(4), k):
        dv_lo = rows[0]["v0"] - G.STRIPS_V[combo[0]][0]
        dv_hi = rows[-1]["v1"] - G.STRIPS_V[combo[-1]][1]
        spread = abs(dv_lo - dv_hi)
        dv = (dv_lo + dv_hi) / 2.0
        internal = [rows[i]["v1"] - G.STRIPS_V[combo[i]][1] - dv for i in range(k - 1)] + \
                   [rows[i]["v0"] - G.STRIPS_V[combo[i]][0] - dv for i in range(1, k)]
        cands.append(dict(combo=list(combo), dv=round(dv, 5), spread=round(spread, 6),
                          internal_max=round(max((abs(x) for x in internal), default=0.0), 6)))
    cands.sort(key=lambda c: (c["spread"], c["internal_max"]))
    best = cands[0]
    tied = [c for c in cands if abs(c["spread"] - best["spread"]) < 1e-6]
    return dict(k=k, du=du, du_spread=du_spread, u0_row_spread=round(u0_row_spread, 6),
                u1_row_spread=round(u1_row_spread, 6), v_fit=best, pitch_ok=pitch_ok,
                pitch_resid_max=round(max(pitch_resid, default=0.0), 6),
                n_tied=len(tied), tied=tied if len(tied) > 1 else None)


def union_rows(rows_a, rows_b):
    """Merge two sides' rows by rounded v0 -- more distinct rows (toward the full 4)
    resolves the outer-bounds tie above (k=4 has only ONE combo)."""
    by_v0 = {}
    for r in rows_a + rows_b:
        key = round(r["v0"], 5)
        if key not in by_v0 or r["ncells"] > by_v0[key]["ncells"]:
            by_v0[key] = r
    return sorted(by_v0.values(), key=lambda r: r["v0"])


print("\n== B/C/D/E. per-pair, per-side seam classification + strip decode")
ALL_PAIRS = sorted(pair_edges.keys(), key=lambda p: -pair_edges[p])
for pair in ALL_PAIRS:
    fa, fb = pair
    n_edges = pair_edges[pair]
    print(f"\n---- {fa}|{fb}: {n_edges} edges over {len(pair_blocks[pair])} blocks ----")
    pair_out = {"n_edges": n_edges, "n_blocks": len(pair_blocks[pair]),
                "mains_both": pair_detail[pair]["mains_both"], "sides": {}}
    for fam in (fa, fb):
        cc = side_class[pair][fam]
        total = sum(cc.values())
        print(f"   {fam} side ({total} boundary tris, dedup): {dict(cc.most_common())}")
        side_out = {"class_counts": dict(cc), "total": total}
        entries = resid_cells[pair][fam]
        if len(entries) < 6:
            print(f"      residual too thin ({len(entries)} tris) -- no strip decode attempted")
            side_out["verdict"] = "too-thin" if entries else "no-residual"
            pair_out["sides"][fam] = side_out
            continue
        cell_rects, n_nonlin, n_full, n_part = strip_decode(entries)
        print(f"      residual cells: {len(cell_rects)} linear ({n_full} full-tile>=90% cov, "
              f"{n_part} partial<90%), {n_nonlin} rejected non-linear/decal")
        rows = cluster_rows(cell_rects)
        for r in rows:
            print(f"      row v0={r['v0']:.5f}: u[{r['u0']:.5f},{r['u1']:.5f}] "
                  f"v[{r['v0']:.5f},{r['v1']:.5f}]  ({r['ncells']} cells)")
        fit = fit_column(rows) if rows else None
        side_out["residual_cells"] = dict(linear=len(cell_rects), full=n_full, partial=n_part,
                                          nonlinear=n_nonlin)
        side_out["rows"] = rows
        side_out["fit"] = fit
        if fit is None:
            print("      NO rows survived clustering (min_cells=3) -- structural-only, "
                  "raw bbox below")
            us = [uv[0] for _, _, uv3 in entries for uv in uv3]
            vs = [uv[1] for _, _, uv3 in entries for uv in uv3]
            raw_bbox = (min(us), max(us), min(vs), max(vs))
            print(f"      raw residual bbox (unfiltered, {len(entries)} tris): {raw_bbox}")
            side_out["verdict"] = "too-thin-for-rows"
            side_out["raw_bbox"] = raw_bbox
        else:
            vf = fit["v_fit"]
            unique = fit["n_tied"] == 1
            proven = (fit["du_spread"] < 2e-5 and fit["k"] >= 2 and vf["spread"] < 2e-5
                      and fit["pitch_ok"] and unique)
            earmark = fit["du_spread"] < 2e-4 and vf["spread"] < 1e-3
            verdict = "proven-5dp" if proven else ("earmark-approximate" if earmark else "falsified")
            print(f"      TRANSLATION FIT: k={fit['k']} rows, du={fit['du']} "
                  f"(spread {fit['du_spread']}, u0-row-spread {fit['u0_row_spread']}, "
                  f"u1-row-spread {fit['u1_row_spread']})  row-pitch ok={fit['pitch_ok']} "
                  f"(max resid {fit['pitch_resid_max']})  best combo={vf['combo']} dv={vf['dv']} "
                  f"(OUTER-BOUNDS v-spread {vf['spread']}, internal-edge max {vf['internal_max']}, "
                  f"n_tied={fit['n_tied']}) -> {verdict}")
            if fit["n_tied"] > 1:
                print(f"      AMBIGUOUS on outer bounds alone -- {fit['n_tied']} combos tie at "
                      f"spread {vf['spread']} (kept lowest internal-edge residual as 'best'; "
                      f"see combined cross-side fit below for disambiguation):")
                for c in fit["tied"]:
                    print(f"         combo={c['combo']} dv={c['dv']} internal_max={c['internal_max']}")
            if fit["k"] == 1:
                print("      (k=1: row-alignment AMBIGUOUS among up to 4 hypotheses -- "
                      "listing all; only a width/self-consistency check, NOT an absolute "
                      "anchor)")
                for j in range(4):
                    ref0, ref1 = G.STRIPS_V[j]
                    r = rows[0]
                    cand_dv = round(((r["v0"] - ref0) + (r["v1"] - ref1)) / 2, 5)
                    cand_spread = round(abs((r["v0"] - ref0) - (r["v1"] - ref1)), 6)
                    print(f"         hyp j={j}: dv={cand_dv} (width-match spread {cand_spread})")
            side_out["verdict"] = verdict
        pair_out["sides"][fam] = side_out

    # ---- COMBINED cross-side fit: union the two sides' rows by v0 -- more distinct
    # rows (up to the full 4) breaks the outer-bounds tie a lone side can hit (caught
    # live on desert|grass and desert|dunes: each side alone ties between 2 combos,
    # the union of both sides recovers all 4 rows and the combo is FORCED unique).
    rows_a = pair_out["sides"].get(fa, {}).get("rows") or []
    rows_b = pair_out["sides"].get(fb, {}).get("rows") or []
    if rows_a or rows_b:
        urows = union_rows(rows_a, rows_b)
        ufit = fit_column(urows) if urows else None
        if ufit:
            uvf = ufit["v_fit"]
            print(f"   COMBINED (union of both sides, {ufit['k']} distinct rows): "
                  f"du={ufit['du']} (spread {ufit['du_spread']})  combo={uvf['combo']} "
                  f"dv={uvf['dv']} (v-spread {uvf['spread']}, n_tied={ufit['n_tied']}, "
                  f"pitch_ok={ufit['pitch_ok']})")
            pair_out["combined_fit"] = ufit
            pair_out["combined_rows"] = urows
    out["pairs"][f"{fa}|{fb}"] = pair_out

# ---- F. explicit confirm/refute checks ---------------------------------------------------------
print("\n== F. confirm/refute checks")


def get_pair(a, b):
    return tuple(sorted((a, b)))


ds = get_pair("desert", "scrub")
if ds in pair_edges:
    d = pair_detail[ds]
    n = d["n"]
    both = d["mains_both"]
    desert_wearing_scrub = side_class[ds]["desert"].get("scrub", 0)
    desert_total = sum(side_class[ds]["desert"].values())
    print(f"(a) desert|scrub: plain|plain {both}/{n} ({both/n:.0%}); "
          f"desert-topo tris wearing SCRUB mains {desert_wearing_scrub}/{desert_total} "
          f"({desert_wearing_scrub/max(1,desert_total):.0%}); "
          f"desert-side RESIDUAL {side_class[ds]['desert'].get('RESIDUAL',0)}/{desert_total}")
    out["desert_scrub_check"] = dict(plain_both=both, n=n, desert_wearing_scrub=desert_wearing_scrub,
                                     desert_total=desert_total,
                                     desert_residual=side_class[ds]["desert"].get("RESIDUAL", 0))
else:
    print("(a) desert|scrub: NO EDGES FOUND map-wide -- cannot check")

db = get_pair("desert", "brush")
if db in pair_edges:
    desert_total = sum(side_class[db]["desert"].values())
    desert_own = side_class[db]["desert"].get("desert", 0)
    brush_total = sum(side_class[db]["brush"].values())
    brush_resid = side_class[db]["brush"].get("RESIDUAL", 0)
    print(f"(b) desert|brush: desert-side own-mains {desert_own}/{desert_total} "
          f"({desert_own/max(1,desert_total):.0%}); brush-side RESIDUAL {brush_resid}/{brush_total} "
          f"({brush_resid/max(1,brush_total):.0%})")
    brush_rows = out["pairs"][f"{db[0]}|{db[1]}"]["sides"]["brush"].get("rows")
    if brush_rows:
        for r in brush_rows:
            near = 0.7207 - EPS <= r["u0"] <= 0.7812 + EPS and 0.7207 - EPS <= r["u1"] <= 0.7812 + EPS
            print(f"      brush edge-column row: u[{r['u0']:.5f},{r['u1']:.5f}] "
                  f"v[{r['v0']:.5f},{r['v1']:.5f}]  matches earmark u~(0.7207,0.7812)? {near}")
    out["desert_brush_check"] = dict(desert_own=desert_own, desert_total=desert_total,
                                     brush_residual=brush_resid, brush_total=brush_total,
                                     brush_rows=brush_rows)
    # brush's edge column fails the per-cell EXACT-LINEAR gate almost everywhere (515/532
    # cells rejected) -- individual triangles carry independent, non-coplanar UV inside
    # the same u/v band (a scattered fringe decal, not a lattice-tiled quad). The raw
    # bbox is still trustworthy if it is MODE-tight, not just min/max of a few outliers:
    # check how much of the vertex mass sits within 1 texel of each bbox edge.
    brush_entries = resid_cells[db]["brush"]
    us = [uv[0] for _, _, uv3 in brush_entries for uv in uv3]
    vs = [uv[1] for _, _, uv3 in brush_entries for uv in uv3]
    u_lo, u_hi, v_lo, v_hi = min(us), max(us), min(vs), max(vs)
    texel = 1.0 / 1024
    near_u_lo = sum(1 for u in us if u < u_lo + texel) / len(us)
    near_u_hi = sum(1 for u in us if u > u_hi - texel) / len(us)
    near_v_lo = sum(1 for v in vs if v < v_lo + texel) / len(vs)
    near_v_hi = sum(1 for v in vs if v > v_hi - texel) / len(vs)
    print(f"      brush edge column MODE-MASS check ({len(us)} verts): u_lo mass {near_u_lo:.1%}, "
          f"u_hi mass {near_u_hi:.1%}, v_lo mass {near_v_lo:.1%}, v_hi mass {near_v_hi:.1%} "
          f"(low mass = a free-floating decal, not a snapped tile edge)")
    print(f"      brush edge column raw rect (5dp): u[{u_lo:.5f},{u_hi:.5f}] v[{v_lo:.5f},{v_hi:.5f}]")
    out["desert_brush_check"]["brush_rect_raw"] = (u_lo, u_hi, v_lo, v_hi)
    out["desert_brush_check"]["brush_mode_mass"] = dict(u_lo=near_u_lo, u_hi=near_u_hi,
                                                          v_lo=near_v_lo, v_hi=near_v_hi)
else:
    print("(b) desert|brush: NO EDGES FOUND map-wide -- cannot check")

# (c) THE GENERIC DESERT-EDGE DECAL cross-pair check: desert|scrub's desert side (k=2,
# n_tied=1, PROVEN dv=-0.04687) and desert|brush's desert side (k=1, ambiguous alone)
# both sample the SAME u column [0.85059,0.91113] -- union them (across DIFFERENT
# pairs, not just the two sides of one pair) to see if it is really ONE shared decal.
print("\n(c) cross-pair check: is the desert-side 'rare residual' ONE shared decal "
      "regardless of neighbour (scrub vs brush)?")
rows_ds = out["pairs"].get("desert|scrub", {}).get("sides", {}).get("desert", {}).get("rows") or []
rows_db = out["pairs"].get("brush|desert", {}).get("sides", {}).get("desert", {}).get("rows") or []
if rows_ds and rows_db:
    same_u = all(abs(r["u0"] - rows_ds[0]["u0"]) < 1e-4 and abs(r["u1"] - rows_ds[0]["u1"]) < 1e-4
                 for r in rows_ds + rows_db)
    print(f"      same u column across both neighbour pairs? {same_u} "
          f"(desert|scrub u={rows_ds[0]['u0']:.5f},{rows_ds[0]['u1']:.5f}; "
          f"desert|brush u={rows_db[0]['u0']:.5f},{rows_db[0]['u1']:.5f})")
    xrows = union_rows(rows_ds, rows_db)
    xfit = fit_column(xrows)
    xvf = xfit["v_fit"]
    print(f"      CROSS-PAIR union ({xfit['k']} distinct rows): du={xfit['du']} "
          f"(spread {xfit['du_spread']})  combo={xvf['combo']} dv={xvf['dv']} "
          f"(v-spread {xvf['spread']}, n_tied={xfit['n_tied']}, pitch_ok={xfit['pitch_ok']})")
    out["generic_desert_decal_cross_pair"] = dict(same_u=same_u, fit=xfit, rows=xrows)

OUTD.mkdir(exist_ok=True)
(OUTD / "ecotone_strip_decode.json").write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {OUTD / 'ecotone_strip_decode.json'}")
