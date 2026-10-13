"""Every disc-1 rock massif, as a `world-mountain --donor`: which ones does today's kit qualify?

Derived from `studies/overworld-topography/donor_qualify_scan.py` (July, 2026-07-19: the census that found
comp20, the 4th donor), unchanged in its gates. What changed:
  - EVERY shortlisted component is qualified, not just the 8 largest (July never checked the small ones);
  - the July comp20 donor (12,16-17) joins the known donors, so it is excluded and anchors nothing new;
  - no dry carve here: `sweep.py` carves every qualified candidate on a bench sized to it, at several
    angles (July carved three, on one bench, at the scan's quarter turns only).
Component numbers are this run's (sorted by size) and differ from July's: July's comp20 is comp21 here.
RUN:  py studies/terrain-malleability/mountaindonors/census.py   (writes out/census.json)
"""
import json
import math
import os
import shutil
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import extract as X                              # noqa: E402
from ff9mapkit.world import interior as IN                            # noqa: E402
from ff9mapkit.world import mesh as M                                 # noqa: E402
from ff9mapkit.world.island import build_landmass                     # noqa: E402

BLOCK = 64.0
ROCK = set(IN.MOUNTAIN_ROCK_TOPOS)
kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))        # noqa: E731
OUTD = Path(__file__).resolve().parent / "out"
out = {}
t0 = time.time()

# the three donors qualified before this scan, per the memory
# project-ff9-overworld-interior-topography -- used both to EXCLUDE their blocks from
# the "new candidate" search and to SANITY-ANCHOR the gates on known-good answers.
KNOWN_DONORS = {
    "uaho": [(0, 0)],
    "crag": [(10, 5), (10, 6)],
    "horseshoe": [(5, 15), (6, 15), (7, 15), (5, 16), (6, 16), (7, 16)],
    "comp20": [(12, 16), (12, 17)],                    # July's 4th donor (in game 2026-07-19)
}


# ==== stage 1: read every disc-1 terrain block ====================================================
print("stage 1: reading every disc-1 terrain block...", flush=True)
blocks_all = X.list_blocks(disc=1)
tris = []                                                              # global flat tri list
for (bx, by) in blocks_all:
    bm = X.read_block(bx, by, disc=1, part="terrain")
    V = bm.verts
    U = bm.uvs
    T = bm.tangents
    for tri in bm.tris:
        d = X.decode_id(int(round(T[tri[0]][0])))
        tris.append(dict(
            w=[(V[j][0] + BLOCK * bx, V[j][1], V[j][2] - BLOCK * by) for j in tri],
            uv=[(float(U[j][0]), float(U[j][1])) for j in tri],
            topo=d["topograph"], ea=(d["event"], d["area"]), blk=(bx, by)))
print(f"  {len(blocks_all)} blocks, {len(tris)} tris "
      f"({time.time() - t0:.0f}s)", flush=True)
out["totals"] = dict(blocks=len(blocks_all), tris=len(tris))

# ==== stage 2: map-wide edge graph + ROCK connected components ====================================
print("stage 2: map-wide rock connected-component census...", flush=True)
edge_tris = defaultdict(list)
for ti, t in enumerate(tris):
    ps = [kk(v) for v in t["w"]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        edge_tris[tuple(sorted((ps[a], ps[b])))].append(ti)
adj = defaultdict(set)
for ts in edge_tris.values():
    r = [t for t in ts if tris[t]["topo"] in ROCK]
    for i in range(len(r)):
        for j in range(i + 1, len(r)):
            adj[r[i]].add(r[j]); adj[r[j]].add(r[i])
comps, seen = [], set()
for s in range(len(tris)):
    if tris[s]["topo"] not in ROCK or s in seen:
        continue
    comp = {s}; st = [s]
    while st:
        t = st.pop()
        for t2 in adj[t]:
            if t2 not in comp:
                comp.add(t2); st.append(t2)
    seen |= comp
    comps.append(comp)
comps.sort(key=len, reverse=True)
print(f"  {len(comps)} rock components map-wide; sizes (top 15) "
      f"{[len(c) for c in comps[:15]]} ({time.time() - t0:.0f}s)", flush=True)
out["n_rock_components"] = len(comps)


def blocks_of(comp):
    return sorted({tris[t]["blk"] for t in comp})


def known_tag(blks):
    bs = set(blks)
    for name, kb in KNOWN_DONORS.items():
        if bs & set(kb):
            return name
    return None


# ==== stage 3: per-component classification (THE TWO MOUNTAIN CLASSES metric) ======================
def classify(comp):
    """Course-weld quad-vweld share -- crag_anatomy.py's exact D. step, generalized to
    any tri-index set over the GLOBAL ``tris`` list. > ~0.4 = lattice-sheet massif
    (carry material); ~0 = shingled escarpment wall (excluded -- no closed rim to carry)."""
    e2w = defaultdict(list)
    for t in comp:
        ps = [kk(v) for v in tris[t]["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            e2w[tuple(sorted((ps[a], ps[b])))].append(t)
    paired, quads = {}, []
    for e, ts in e2w.items():
        if len(ts) != 2 or ts[0] in paired or ts[1] in paired:
            continue
        vs = {kk(v) for t in ts for v in tris[t]["w"]}
        if len(vs) != 4:
            continue
        vs = sorted(vs, key=lambda p: p[1])
        lo, hi = vs[:2], vs[2:]
        if abs(lo[0][1] - lo[1][1]) > 1.5 or abs(hi[0][1] - hi[1][1]) > 1.5:
            continue
        paired[ts[0]] = paired[ts[1]] = len(quads)
        quads.append(dict(lo=lo, hi=hi))
    hi_all = set()
    for q in quads:
        hi_all.update(q["hi"])
    vweld = sum(1 for q in quads if any(p in hi_all for p in q["lo"]))
    return dict(quads=len(quads), vweld_share=round(vweld / max(1, len(quads)), 2))


def once_edges_of(comp):
    eu = Counter()
    for t in comp:
        ps = [kk(v) for v in tris[t]["w"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            eu[tuple(sorted((ps[a], ps[b])))] += 1
    return [e for e, n in eu.items() if n == 1]


def chains_ok(comp):
    try:
        rings = IN.chain_rings(once_edges_of(comp), "component")
        return True, [len(r) for r in rings]
    except ValueError as e:
        return False, str(e)


def feet_of(comp):
    """Topos of tris OUTSIDE the component that border its once-edges (informational --
    a grass-bounded rim is the mesa/hill-adjacent look; a river/dirt-bounded rim needs a
    different fringe)."""
    oe = once_edges_of(comp)
    myset = set(comp)
    feet = Counter()
    for e in oe:
        for t in edge_tris.get(e, ()):
            if t not in myset:
                feet[tris[t]["topo"]] += 1
    return feet


N_SHOW = 30
print(f"\n== per-component table (top {N_SHOW} by size) ==", flush=True)
comp_rows = []
for ci, comp in enumerate(comps):
    blks = blocks_of(comp)
    cls = classify(comp)
    ok, ring_info = chains_ok(comp)
    xs = [p[0] for t in comp for p in tris[t]["w"]]
    zs = [p[2] for t in comp for p in tris[t]["w"]]
    row = dict(idx=ci, n=len(comp), blocks=blks, known=known_tag(blks),
              extent=[round(max(xs) - min(xs), 1), round(max(zs) - min(zs), 1)],
              vweld_share=cls["vweld_share"], quads=cls["quads"],
              chains=ok, ring_info=ring_info if ok else None,
              chain_error=None if ok else ring_info)
    comp_rows.append(row)
out["components"] = comp_rows[:80]
for row in comp_rows[:N_SHOW]:
    tag = f" [KNOWN:{row['known']}]" if row["known"] else ""
    verdict = ("lattice-sheet" if row["quads"] and row["vweld_share"] > 0.4
               else "shingled/wall" if row["quads"] else "no-quads")
    chain_s = f"rings{row['ring_info']}" if row["chains"] else "NO-CHAIN"
    print(f"  comp{row['idx']:3d}: {row['n']:5d} tris, blocks {row['blocks'][:6]}"
          f"{'...' if len(row['blocks']) > 6 else ''} ({len(row['blocks'])} blks), "
          f"extent {row['extent']}, vweld {row['vweld_share']:.2f} ({row['quads']} quads) "
          f"-> {verdict}, {chain_s}{tag}", flush=True)

# ==== stage 4: shortlist -- unknown, lattice-sheet, chains, reasonably sized =======================
SHORTLIST_MIN_TRIS = 40
shortlist = [row for row in comp_rows
             if not row["known"] and row["chains"] and row["quads"] >= 4
             and row["vweld_share"] > 0.4 and row["n"] >= SHORTLIST_MIN_TRIS]
shortlist.sort(key=lambda r: -r["n"])
print(f"\nstage 4: shortlist (unknown, lattice-sheet vweld>0.4, chains, "
      f">= {SHORTLIST_MIN_TRIS} tris): {len(shortlist)} candidates", flush=True)
for row in shortlist[:15]:
    print(f"  comp{row['idx']} ({row['n']} tris, blocks {row['blocks']})", flush=True)
DEEP_CHECK_N = len(shortlist)                           # all of them (July: 8)
deep_candidates = shortlist[:DEEP_CHECK_N]
out["shortlist"] = [r["idx"] for r in shortlist]


# ==== stage 5: THE STRUCTURAL GATE -- the real interior._mountain_blob, per candidate ==============
def qualify(name, donor_blocks, *, alcove_box=None, census_n=None):
    """Run the SHIPPED ``interior._mountain_blob`` (the exact function ``carve_mountain``
    calls) on ``donor_blocks``; classify object-only vs ensemble vs disqualified. A broad
    except (not just ValueError) plus THE BALLOON GUARD catch a flood that escaped an
    un-sealed pocket (Uaho's own alcove needed a hand-tuned box for exactly this reason --
    a new donor with the same shape and no box would either raise or balloon)."""
    try:
        B = IN._mountain_blob(donor_blocks, rock_topos=ROCK, alcove_box=alcove_box, disc=1)
    except Exception as e:                                 # noqa: BLE001 -- report, don't crash the scan
        return dict(name=name, blocks=donor_blocks, ok=False,
                    verdict=f"DISQUALIFIED({type(e).__name__}: {e})")
    blob_n = len(B["blob"])
    if census_n and blob_n > 3.0 * census_n:
        return dict(name=name, blocks=donor_blocks, ok=False, blob_tris=blob_n,
                    census_tris=census_n,
                    verdict=f"DISQUALIFIED(blob ballooned {blob_n}/{census_n} tris -- "
                            f"an unsealed pocket flooded past the rock census; needs a "
                            f"hand-tuned alcove box like Uaho's UAHO_ALCOVE)")
    n_obj = len(B["apertures"])
    n_ens = len(B["ensemble_apertures"])
    ys = [p[1] for p in B["rim"]]
    verdict = ("QUALIFIED-OFFLINE (no aperture)" if not n_obj and not n_ens else
               "QUALIFIED-OFFLINE (object-only aperture)" if n_obj and not n_ens else
               "NEEDS-ENSEMBLE-CARRY (part-union aperture)" if n_ens else
               "QUALIFIED-OFFLINE (mixed apertures)")
    # the de-tilt residual (recomputed from the returned rim/plane -- _mountain_blob logs
    # it but doesn't return it): a large residual means the donor's foot is NOT flat --
    # the ROCK-RIGID carry's single global affine (the de-tilt) would badly distort a
    # donor whose footing isn't. Uaho/crag/horseshoe all measured <= ~4u; this is a
    # gate the module doesn't hard-enforce, so the scan surfaces it as a risk flag.
    cx, cz = B["c_local"]
    Amat = np.array([[p[0] - cx, p[2] - cz, 1.0] for p in B["rim"]])
    bvec = np.array(ys)
    coef, *_ = np.linalg.lstsq(Amat, bvec, rcond=None)
    res = bvec - Amat @ coef
    residual = round(float(max(abs(res.min()), abs(res.max()))), 1)
    slope = round(math.degrees(math.atan(math.hypot(B["ta"], B["tb"]))), 1)
    return dict(name=name, blocks=donor_blocks, ok=True, verdict=verdict,
               blob_tris=blob_n, census_tris=census_n,
               rim_pts=len(B["rim"]), rim_y=[round(min(ys), 1), round(max(ys), 1)],
               radius=round(B["r_rim"], 1), object_apertures=[len(r) for r in B["apertures"]],
               ensemble_apertures=[len(r) for r in B["ensemble_apertures"]],
               sweep_tris=len(B["sweep"]),
               sweep_topos=dict(Counter(B["dtopo"][t] for t in B["sweep"])),
               detilt_slope_deg=slope, detilt_residual=residual,
               footing_risk=residual > 6.0)


known_census_n = {}
for row in comp_rows:
    if row["known"] and row["known"] not in known_census_n:
        known_census_n[row["known"]] = row["n"]            # first hit = the biggest (comps sorted)

print("\n== stage 5a: SANITY ANCHOR -- reproduce the three known verdicts ==", flush=True)
anchor = {}
anchor["uaho"] = qualify("uaho", KNOWN_DONORS["uaho"], alcove_box=IN.UAHO_ALCOVE,
                         census_n=known_census_n.get("uaho"))
anchor["crag"] = qualify("crag", KNOWN_DONORS["crag"], alcove_box=None,
                         census_n=known_census_n.get("crag"))
anchor["horseshoe"] = qualify("horseshoe", KNOWN_DONORS["horseshoe"], alcove_box=None,
                              census_n=known_census_n.get("horseshoe"))
for name, r in anchor.items():
    print(f"  {name}: {r['verdict']}"
          + (f" (blob {r.get('blob_tris')} tris, radius {r.get('radius')}u, "
             f"obj-ap {r.get('object_apertures')}, ens-ap {r.get('ensemble_apertures')})"
             if r["ok"] else ""), flush=True)
anchor_ok = (anchor["uaho"]["ok"] and anchor["uaho"]["object_apertures"]
             and not anchor["uaho"]["ensemble_apertures"] and
             anchor["crag"]["ok"] and not anchor["crag"]["object_apertures"]
             and not anchor["crag"]["ensemble_apertures"] and
             anchor["horseshoe"]["ok"] and anchor["horseshoe"]["ensemble_apertures"])
print(f"  SANITY ANCHOR: {'PASS' if anchor_ok else 'FAIL -- gates are miscoded, '
      'do not trust the candidate verdicts below'}", flush=True)
out["sanity_anchor"] = dict(pass_=anchor_ok, uaho=anchor["uaho"], crag=anchor["crag"],
                            horseshoe=anchor["horseshoe"])
assert anchor_ok, "sanity anchor failed -- fix the qualification gates before trusting new donors"

print(f"\n== stage 5b: qualify {len(deep_candidates)} new candidates ==", flush=True)
results = []
for row in deep_candidates:
    comp = comps[row["idx"]]
    donor_blocks = row["blocks"]
    r = qualify(f"comp{row['idx']}", donor_blocks, alcove_box=None, census_n=row["n"])
    if r["ok"]:
        feet = feet_of(comp)
        ea_census = Counter(tris[t]["ea"] for t in comp)
        r["feet_topos"] = dict(feet.most_common(6))
        r["rock_ea_census"] = {str(k): v for k, v in ea_census.most_common(6)}
        r["grass_bounded"] = feet.get(0, 0) >= sum(feet.values()) * 0.5 if feet else None
    results.append(r)
    print(f"  {r['name']} (census {row['n']} tris, blocks {donor_blocks}): {r['verdict']}",
          flush=True)
    if r["ok"]:
        print(f"      blob {r['blob_tris']} tris, radius {r['radius']}u, "
              f"rim y{r['rim_y']}, obj-ap {r['object_apertures']}, "
              f"ens-ap {r['ensemble_apertures']}, sweep {r['sweep_tris']} tris "
              f"{r.get('sweep_topos')}, feet {r.get('feet_topos')}, "
              f"de-tilt {r['detilt_slope_deg']}deg residual +-{r['detilt_residual']}u"
              f"{' FOOTING-RISK' if r['footing_risk'] else ''}", flush=True)
out["candidates"] = results

# ==== stage 6: ranked verdict + recommend 2-3, dry-carve the top pick(s) ===========================
# rank by PRACTICALITY, not raw size: radius ascending (a carriable bench must exist) --
# the naive "biggest wins" sort picked the 3 candidates the current mint machinery can't
# reasonably bench (radius 83-98u, see comp2/3/5 below); Uaho/crag/horseshoe all sit
# 20-54u, so radius-ascending surfaces the candidates actually close to that envelope.
qualified = [r for r in results if r["ok"]]
qualified.sort(key=lambda r: r["radius"])
disqualified = [r for r in results if not r["ok"]]
print("\n== RANKED VERDICT TABLE (qualified by ascending radius = ascending practicality) ==",
      flush=True)
print(f"{'name':10s} {'blocks':32s} {'tris':>6s} {'radius':>7s} {'footing':>8s} {'verdict'}")
for r in qualified + disqualified:
    blk_s = ",".join(f"({b[0]},{b[1]})" for b in r["blocks"])
    foot = f"+-{r['detilt_residual']}u" if r["ok"] else "-"
    print(f"{r['name']:10s} {blk_s:32s} "
          f"{str(r.get('blob_tris', '-')):>6s} {str(r.get('radius', '-')):>7s} {foot:>8s} "
          f"{r['verdict']}")

recommend = qualified[:3]
print(f"\nRECOMMENDED for a first in-game carry attempt (smallest practical radius, "
      f"clean footing preferred): {[r['name'] for r in recommend]}", flush=True)
out["recommended"] = [r["name"] for r in recommend]

# ---- stage 6b (July's dry carve) moved to sweep.py: every candidate, its own bench, several angles.

# ==== write artifacts ===============================================================================
OUTD.mkdir(exist_ok=True)
outp = OUTD / "census.json"
outp.write_text(json.dumps(out, indent=1, default=str))
print(f"\n-> {outp}", flush=True)
scratch = os.environ.get("FF9_DONOR_SCAN_SCRATCH")
if scratch:
    sp = Path(scratch)
    sp.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(outp, sp / "donor_qualify_scan.json")
    print(f"-> {sp / 'donor_qualify_scan.json'} (scratchpad copy)", flush=True)
print(f"\ntotal runtime: {time.time() - t0:.0f}s", flush=True)
