"""STEP 7 -- operation replay vs delta for a BYTE-CARRIED in-place verb on a REAL, documented site.

The one documented in-place real-land morph: block (16,5), Outer Continent east coast, the minted desert beach
(studies/overworld-topography/README.md:764-766, DEPLOYED 2026-07-15, "Real cell -> disc 1 only (no mirror)"):
  world-transplant --in-place --cell 16,5 --donor 16,5 --bank-lower "1075.22,-333.89:18"
                   --virgin-mint "1071.19,-328.14:1079.26,-339.64:2.4:3.8:pins=20,5"
(the round-2 corridor bank's exact spec is not recorded in a parseable form, so round 1 only).
PART B -- the same three-way test on GATE-REFUSED coastal cells: for each refused cell carrying a Sea part, the
first coastscan-certified cliff-bump window (coastscan.scan_block on disc 1 = the oracle the scanner itself uses)
is the disc-1 edit; replay = coastmorph.cliff_bump(disc=4) + morph_in_place(disc=4, dry_run=True); delta = the
disc-1 morph's touched parts carried with lib.delta_transfer(ring=1).

For each spec, WITHOUT writing anything (morph_in_place(dry_run=True) returns before any deploy,
transplant.py:3367-3368):
  (a) the shipped gate verdict for (16,5) (s1);
  (b) REPLAY: build the tweak set from DISC-4 bytes (coastmorph.build_shore_tweaks(disc=4)) and run the kit's own
      morph_in_place(disc=4, dry_run=True) gates -- does the verb's own law pass on disc 4?
  (c) DELTA: re-run the morph loop (a verbatim replica of transplant.py:3303-3337 so the emitted polys are
      visible), turn the touched parts into soup meshes (transplant._soup_block_mesh -- the deploy's own builder),
      and transfer the disc-1 edit onto disc-4 stock with lib.delta_transfer (ring 1, byte-carried) -- plus the
      XZ distance from the edit's R+A tris to the nearest disc-diff (unmatched) tri of the same part;
  (d) does replay(disc-4) produce the same bytes as delta when both are lawful.
Writes out/s7_morph_replay.json.
Run (from C:\\gd\\Dream-World-IX\\ff9mapkit):  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_disc4_edit_reach/s7_morph_replay.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib as L                                       # noqa: E402
import numpy as np                                    # noqa: E402
from ff9mapkit.world import coastmorph as CM         # noqa: E402
from ff9mapkit.world import mesh as M                # noqa: E402
from ff9mapkit.world import transplant as TR         # noqa: E402

G = L.GAME
CELL = (16, 5)
SPECS = {"round1": ("1075.22,-333.89:18", "1071.19,-328.14:1079.26,-339.64:2.4:3.8:pins=20,5")}
rows = json.loads((L.OUT / "s1_gate.json").read_text(encoding="utf-8"))["rows"]
data = L.load_cache()
pairs = data["pairs"]
objs = L.mesh_objects()


def tweaks_for(spec, disc):
    bank, mint = spec
    tw, notes = CM.build_shore_tweaks(CELL, (1, 1), bank=CM.parse_bank_lower_spec(bank),
                                      mint=CM.parse_virgin_mint_spec(mint), disc=disc, game=G)
    return tw


def raw_polys(tweaks, disc):
    """Replica of morph_in_place's loop (transplant.py:3303-3337): {part: (polys, originals)} for touched parts."""
    bx, by = CELL
    out = {}
    for p in TR.PARTS:
        tris = TR.world_tris(bx, by, p, disc=disc, game=G)
        if not tris:
            continue
        polys, touched = [], False
        for tri in tris:
            poly = list(tri)
            for tw in tweaks:
                p2 = tw.apply(p, poly)
                if p2 is not poly:
                    touched = True
                poly = p2
                if poly is None:
                    break
            if poly is not None:
                polys.append(poly)
        for tw in tweaks:
            if getattr(tw, "part", None) == p:
                em = tw.emit()
                if em:
                    touched = True
                    polys.extend(list(e) for e in em)
        if touched:
            out[p] = (polys, tris)
    return out


def soup(polys, disc, part):
    bx, by = CELL
    loc = [[((v[0][0] - 64.0 * bx, v[0][1], v[0][2] + 64.0 * by), v[1], v[2], v[3]) for v in poly] for poly in polys]
    return TR._soup_block_mesh(f"Block[{bx}][{by}] {TR.part_name(part)}", CELL, loc, disc=disc, lod="0_1")


def tri_xz(bm, idx):
    V = np.asarray(bm.verts)
    T = np.asarray(bm.flat_index).reshape(-1, 3)
    return V[T[idx]][:, :, [0, 2]]


def min_tri_dist(A, B):
    """Minimum 2D distance between two triangle sets (0 if any overlap / touch)."""
    if len(A) == 0 or len(B) == 0:
        return None
    best = np.inf
    def seg_pt(p, a, b):
        ab = b - a
        t = np.clip(((p - a) * ab).sum(-1) / np.maximum((ab * ab).sum(-1), 1e-18), 0, 1)
        return np.linalg.norm(p - (a + ab * t[..., None]), axis=-1)
    def inside(p, tri):
        a, b, c = tri[..., 0, :], tri[..., 1, :], tri[..., 2, :]
        cr = lambda u, v: u[..., 0] * v[..., 1] - u[..., 1] * v[..., 0]
        d1, d2, d3 = cr(b - a, p - a), cr(c - b, p - b), cr(a - c, p - c)
        return ((d1 >= 0) & (d2 >= 0) & (d3 >= 0)) | ((d1 <= 0) & (d2 <= 0) & (d3 <= 0))
    for X_, Y_ in ((A, B), (B, A)):
        for k in range(3):
            p = X_[:, k][:, None, :]
            for e in range(3):
                d = seg_pt(p, Y_[None, :, e], Y_[None, :, (e + 1) % 3])
                best = min(best, float(d.min()))
            if inside(p, Y_[None, :, :]).any():
                return 0.0
    return best


res = {"cell": list(CELL), "shipped_gate": rows[f"{CELL[0]},{CELL[1]}"]["shipped"],
       "orderinv_gate": rows[f"{CELL[0]},{CELL[1]}"]["orderinv"], "specs": {}}
print("(16,5) shipped gate:", res["shipped_gate"], "| order-invariant:", res["orderinv_gate"])
for name, spec in SPECS.items():
    r = {}
    for disc in (1, 4):
        try:
            tw = tweaks_for(spec, disc)
            s = TR.morph_in_place("", cell=CELL, tweaks=list(tw), disc=disc, game=G, dry_run=True)
            r[f"replay_d{disc}"] = {"clean": s["clean"], "touched": s["touched"],
                                    "failed_gates": [g for g in s["gates"] if not g.get("ok", True)]}
        except ValueError as e:
            r[f"replay_d{disc}"] = {"refused": str(e)[:300]}
    print(name, "disc1:", r["replay_d1"].get("clean", r["replay_d1"].get("refused")),
          "| disc4 replay:", r["replay_d4"].get("clean", r["replay_d4"].get("refused")))
    # delta of the disc-1 morph onto disc-4 stock, per touched part
    tw1 = tweaks_for(spec, 1)
    raw1 = raw_polys(tw1, 1)
    dl = {}
    try:
        raw4 = raw_polys(tweaks_for(spec, 4), 4)
    except ValueError:
        raw4 = {}
    for p, (polys, _orig) in sorted(raw1.items()):
        E1 = soup(polys, 1, p)
        S1 = L.decode(objs[(1, "0_1", CELL[0], CELL[1], p)], 1, *CELL)
        S4 = L.decode(objs[(4, "0_1", CELL[0], CELL[1], p)], 4, *CELL)
        ok, why, D, st = L.delta_transfer(S1, E1, S4, ring=1)
        # R/A geometry vs the unmatched footprint of this part (and of terrain)
        k1, ke = L.tri_keys(S1, L._vrec(S1)), L.tri_keys(E1, L._vrec(E1))
        from collections import Counter as C_
        ce = C_(ke)
        R = []
        for i, k in enumerate(k1):
            if ce.get(k):
                ce[k] -= 1
            else:
                R.append(i)
        c1 = C_(k1)
        A = []
        for j, k in enumerate(ke):
            if c1.get(k):
                c1[k] -= 1
            else:
                A.append(j)
        RA = np.concatenate([tri_xz(S1, R), tri_xz(E1, A)]) if (R or A) else np.zeros((0, 3, 2))
        pr = pairs[(CELL[0], CELL[1], p)]
        U = np.concatenate([tri_xz(S1, np.nonzero(~pr["m1"])[0]), tri_xz(S4, np.nonzero(~pr["m4"])[0])])
        dist = min_tri_dist(RA, U)
        eq = None
        if ok and p in raw4:
            R4 = soup(raw4[p][0], 4, p)
            eq = sorted(L.tri_keys(D, L._vrec(D))) == sorted(L.tri_keys(R4, L._vrec(R4)))
        dl[p] = {"delta_ok": ok, "why": why, "R": len(R), "A": len(A), "part_unmatched": int(len(U)),
                 "min_dist_RA_to_unmatched": dist, "delta_multiset_eq_replay": eq}
        print(f"   {name} part {p}: delta {ok} ({why}); R {len(R)} A {len(A)}; part unmatched {len(U)}; "
              f"dist RA->unmatched {dist}; delta==replay {eq}")
    r["delta"] = dl
    res["specs"][name] = r

# ---------------------------------------------------------------- PART B: refused coastal cells, cliff-bump
import time
from ff9mapkit.world import coastscan as CS          # noqa: E402
refused = sorted(tuple(map(int, k.split(","))) for k, r in rows.items() if r["land"] and r["shipped"].startswith("SKIP"))
coastal = [c for c in refused if any((c[0], c[1], p) in pairs for p in ("sea1", "sea2", "sea3", "sea4", "sea5"))]
print(f"PART B: {len(coastal)} refused coastal cells")
t0 = time.time()
pb = []


def run_morph(cell, tw_builder):
    global CELL
    CELL = cell
    out = {}
    for disc in (1, 4):
        try:
            tw = tw_builder(disc)
            s_ = TR.morph_in_place("", cell=cell, tweaks=list(tw), disc=disc, game=G, dry_run=True)
            out[disc] = {"clean": bool(s_["clean"]), "tw": tw,
                         "failed": [g.get("gate") for g in s_["gates"] if not g.get("ok", True)]}
        except ValueError as e:
            out[disc] = {"clean": False, "refused": str(e)[:160], "tw": None, "failed": ["raised"]}
    return out


for cell in coastal:
    if time.time() - t0 > 600:
        break
    try:
        ws = CS.scan_block(*cell, verbs=("cliff-bump",))
    except Exception as e:                                # noqa: BLE001
        pb.append({"cell": list(cell), "scan_error": str(e)[:120]}); continue
    w = next((w for w in ws if w["kind"] == "cliff" and (w["probes"].get("cliff-bump") or {}).get("depth")), None)
    if w is None:
        continue
    pr = w["probes"]["cliff-bump"]
    start, end = pr["window"]
    depth = pr["depth"]
    rr = run_morph(cell, lambda d: CM.cliff_bump(cell, start, end, depth, disc=d, game=G))
    row = {"cell": list(cell), "window": [list(start), list(end)], "depth": depth,
           "d1_clean": rr[1]["clean"], "replay_d4_clean": rr[4]["clean"], "replay_d4_failed": rr[4]["failed"],
           "replay_d4_refused": rr[4].get("refused")}
    if rr[1]["clean"]:
        raw1 = raw_polys(rr[1]["tw"], 1)
        raw4 = raw_polys(rr[4]["tw"], 4) if rr[4]["tw"] else {}
        ok_all, eq_all, why = True, True, {}
        for p, (polys, _o) in raw1.items():
            E1 = soup(polys, 1, p)
            S1 = L.decode(objs[(1, "0_1", cell[0], cell[1], p)], 1, *cell)
            S4 = L.decode(objs[(4, "0_1", cell[0], cell[1], p)], 4, *cell)
            ok, wy, D, st = L.delta_transfer(S1, E1, S4, ring=1)
            ok_all &= ok
            why[p] = wy
            # XZ distance from this part's R+A tris to the unmatched tris of the same part and of Terrain
            from collections import Counter as C_
            k1_, ke_ = L.tri_keys(S1, L._vrec(S1)), L.tri_keys(E1, L._vrec(E1))
            def _minus(a, b):                     # indices of a's keys not consumed by the multiset b
                pool, out_ = C_(b), []
                for i_, k_ in enumerate(a):
                    if pool[k_]:
                        pool[k_] -= 1
                    else:
                        out_.append(i_)
                return out_
            Ri, Ai = _minus(k1_, ke_), _minus(ke_, k1_)
            RA_ = np.concatenate([tri_xz(S1, Ri), tri_xz(E1, Ai)]) if (Ri or Ai) else np.zeros((0, 3, 2))
            Us = []
            for q in {p, "terrain"}:
                if (cell[0], cell[1], q) in pairs:
                    prq = pairs[(cell[0], cell[1], q)]
                    S1q = S1 if q == p else L.decode(objs[(1, "0_1", cell[0], cell[1], q)], 1, *cell)
                    S4q = S4 if q == p else L.decode(objs[(4, "0_1", cell[0], cell[1], q)], 4, *cell)
                    Us.append(tri_xz(S1q, np.nonzero(~prq["m1"])[0]))
                    Us.append(tri_xz(S4q, np.nonzero(~prq["m4"])[0]))
            U_ = np.concatenate(Us) if Us else np.zeros((0, 3, 2))
            dd = min_tri_dist(RA_, U_)
            if dd is not None:
                row.setdefault("min_xz_dist_to_footprint", dd)
                row["min_xz_dist_to_footprint"] = min(row["min_xz_dist_to_footprint"], dd)
            if ok and p in raw4 and rr[4]["clean"]:
                R4 = soup(raw4[p][0], 4, p)
                eq_all &= sorted(L.tri_keys(D, L._vrec(D))) == sorted(L.tri_keys(R4, L._vrec(R4)))
            elif ok:
                eq_all = None if eq_all is not False else False
        row.update({"delta_ok": ok_all, "delta_why": why, "delta_multiset_eq_replay": eq_all if ok_all and rr[4]["clean"] else None,
                    "touched_parts": sorted(raw1)})
    pb.append(row)
    print(f"  {cell}: d1 {row['d1_clean']} | replay d4 {row['replay_d4_clean']} {row['replay_d4_failed'] or ''} | "
          f"delta {row.get('delta_ok')} | eq {row.get('delta_multiset_eq_replay')}", flush=True)
done_ = [r for r in pb if r.get("d1_clean")]
res["partB"] = {"rows": pb, "tested": len(done_),
                "replay_clean": sum(1 for r in done_ if r["replay_d4_clean"]),
                "delta_ok": sum(1 for r in done_ if r.get("delta_ok")),
                "both": sum(1 for r in done_ if r["replay_d4_clean"] and r.get("delta_ok")),
                "delta_eq_replay": sum(1 for r in done_ if r.get("delta_multiset_eq_replay") is True),
                "delta_ok_min_xz_dist": sorted(round(r.get("min_xz_dist_to_footprint", 99), 2) for r in done_ if r.get("delta_ok")),
                "delta_ok_overlapping_footprint": sum(1 for r in done_ if r.get("delta_ok") and r.get("min_xz_dist_to_footprint", 99) == 0.0)}
print("PART B summary:", res["partB"] | {"rows": len(pb)})
(L.OUT / "s7_morph_replay.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
