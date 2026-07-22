"""THE RESIDUAL GATE SUITE -- rung 9 of the dunes arc (2026-07-21), the CALIBRATED verdict on the
rung-8 forensics (dunes_residual_census.py) and the fix it recommended (raise MARGIN_RINGS 2 -> 5).

THE STANDING SUSPICION, honored to the end. The rung-8 forensics named THREE residuals and judged
TWO faithful + ONE real ("the ecotone is truncated, not cut -- carry more desert margin, raise
MARGIN_RINGS to ~5"). This rung CALIBRATES that recommendation before spending a deploy on it, and
the instrument REFUTES it three independent ways:

  1. COLOR.  The "differently-UV-tiled host mains" the forensics blamed do NOT differ in color.
     Carried desert vs host desert mean atlas RGB differ by |dRGB| = 2.8 -- while stock's OWN generic
     desert varies cell-to-cell by p99 = 18.2 (max 21.8). The carried desert is FAR more colour-
     continuous with the host than two stock desert cells are with each other. The rung-8 PART-4 ring-
     cutoff metric (44 "cut-off" cells) fired on a topo-16-strip-abuts-topo-17-mains rule that
     corresponds to NO visible seam -- a mis-calibrated instrument, the exact failure the arc keeps
     minting laws about.

  2. GEOMETRY.  The donor dune ensemble has NO wide desert margin to carry: comp[1] sits in a THIN
     desert apron (1-2 cells) bounded by GRASS (west/south) and topo-49 MESA-MURAL rock (elsewhere).
     The forensics' "stock continues the strip to ring depth 3-5" was a DIRECTIONAL artifact -- it
     counted topo-16 tiles that live INSIDE mural-ROCK cells, not a walkable desert gradient. There is
     no gradient to complete.

  3. THE FIX REGRESSES.  Rebuilt at MARGIN_RINGS=5, the carry (a) passes all 16 legacy gates but (b)
     moves the geometry-fixing conform lifts from 5.66u away from the dune core (rings=2) to 0.0u --
     313 host verts lifted right at the dune boundary the frozen eye guards, vs 0 at rings=2 -- and
     (c) the wider apron reaches grass-facing khaki strips that render 2 new olive-green streaks the
     user would read as MORE "green shards". A more-invasive change, at the dune boundary, that adds
     the very defect it was meant to cure, to fix a colour seam that measures 2.8/18.2. REJECTED.

VERDICT: all THREE residuals are within STOCK-DERIVED bands on the CURRENT deployment; the faithful
carry is already correct. No byte is changed. This module is the permanent, recalibrated gate suite
(stock-derived bands, per-pixel-render ground truth) + the anti-test that would have caught the
rings=5 regression -- so the gates have teeth and the refutation is reproducible.

Run OFFLINE (reads deployed + stock, writes only out/, changes NO game bytes):
  py studies/overworld-topography/dunes_residual_gates.py
Artifacts -> out/dunes_residual_gates.json + out/resid_gate_*.png
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import dunes_residual_census as RC          # noqa: E402  (loaders, camera, fragment A/B, stray census)
import dunes_true_carry as TC               # noqa: E402  (the carry + define_region + build_and_gate)
import dunes_grazing_eye as GE              # noqa: E402  (atlas, render, green frac)

CELL, BLOCK = 4.0, 64.0
ROCK = frozenset({49, 58})
GROUND = frozenset({0, 16, 17, 19, 20})
OUTD = HERE / "out"
OUTD.mkdir(exist_ok=True)

# --- fix-distance band: the rung-7 promise is that the geometry-moving fringe fixes live in the flat
#     desert margin / mesa base / amputation stumps, AWAY from the dune boundary the frozen eye judges.
#     rings=2 keeps them 5.66u from the dune core; rings=5 drags them onto it (0.0u). A gate at 3.0u
#     passes the faithful carry and fails the rings=5 regression -- the anti-test with teeth.
FIX_DUNE_DIST_MIN = 3.0

GATES: list = []


def gate(name, ok, detail=""):
    GATES.append((name, bool(ok), detail))
    print(f"GATE [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    return bool(ok)


# ============================================================================================
# calibration (stock-derived bands)
# ============================================================================================
def _tri_mean_rgb(uv3, nsub=6):
    GE._load_atlas()
    acc = np.zeros(3); cnt = 0
    for i in range(nsub + 1):
        for j in range(nsub + 1 - i):
            a, b = i / nsub, j / nsub; c = 1 - a - b
            u = a * uv3[0][0] + b * uv3[1][0] + c * uv3[2][0]
            v = a * uv3[0][1] + b * uv3[1][1] + c * uv3[2][1]
            al, rgb = GE._atlas_bilinear(u, v)
            if al < 24:
                continue
            acc += rgb; cnt += 1
    return (acc / cnt) if cnt else None


def _flat(n3):
    return (sum(abs(nn[1]) for nn in n3) / 3) >= 0.7


def calibrate():
    """Bands measured from stock, not chosen by fiat."""
    print("=" * 96)
    print("CALIBRATION -- the bands are stock-derived (the standing-suspicion discipline)")
    print("=" * 96)
    # (a) generic desert green band + cell-to-cell colour spread
    green_flat, cellcols = [], []
    for name, blocks in RC.GENERIC_DESERT.items():
        st = RC.load_stock(blocks)
        cellc = defaultdict(list)
        for (p3, uv3, n3, topo, fam, blk) in st:
            if topo not in GROUND or not _flat(n3):
                continue
            gf = GE.tri_green_frac(uv3, nsub=12)
            if gf > 0:
                green_flat.append(gf)
            m = _tri_mean_rgb(uv3)
            if m is not None:
                cellc[RC.cell_of(p3)].append(m)
        for c, ms in cellc.items():
            cellcols.append(np.mean(ms, 0))
    flat_band = float(max(green_flat)) if green_flat else 0.0
    cc = np.array(cellcols)
    ccmean = cc.mean(0)
    ccdist = np.linalg.norm(cc - ccmean, axis=1)
    color_band = float(np.percentile(ccdist, 99))
    # (b) stock topo-49 mesa mural green band (the butte carries a verbatim SUBSET)
    st49 = [uv3 for (p3, uv3, n3, topo, fam, blk) in RC.load_stock(RC.DONOR_BLOCKS) if topo == 49]
    g49 = [GE.tri_green_frac(uv3, nsub=12) for uv3 in st49]
    g49 = [g for g in g49 if g > 0]
    band49 = float(max(g49)) if g49 else 0.0
    print(f"  flat generic-desert green band (authentic tile max)     = {flat_band:.3f}")
    print(f"  topo-49 mesa-mural green band (stock's own)              = {band49:.3f}")
    print(f"  desert cell-to-cell colour band (stock p99 |dRGB|)       = {color_band:.2f}  "
          f"(p50={np.percentile(ccdist,50):.2f} max={ccdist.max():.2f})")
    return dict(flat_green_band=flat_band, mural49_green_band=band49, color_band=color_band,
                n_stock_desert_cells=len(cc))


# ============================================================================================
# per-tri desert colour by provenance (the corrected ECOTONE metric)
# ============================================================================================
def desert_color_continuity(dep, placed_R):
    carried, host = [], []
    for (p3, uv3, n3, topo, fam, blk) in dep:
        if blk not in RC.CARRIED or topo not in (16, 17, 19, 20) or not _flat(n3):
            continue
        m = _tri_mean_rgb(uv3)
        if m is None:
            continue
        (carried if RC.cell_of(p3) in placed_R else host).append(m)
    c = np.array(carried).mean(0) if carried else None
    h = np.array(host).mean(0) if host else None
    d = float(np.linalg.norm(c - h)) if (c is not None and h is not None) else 0.0
    return d, (len(carried), len(host)), (c, h)


# ============================================================================================
# render helpers (user stance)
# ============================================================================================
def _user_cam(dep):
    gy = RC.ground_y([t for t in dep if t[5] in RC.CARRIED], *RC.CAMXZ)
    cam, look, _ = RC.build_user_camera(gy)
    return cam, look, gy


def _count_strict_green(img):
    a = np.asarray(img).astype(int)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    return int(((g > r + 12) & (g > b + 30) & (g > 95)).sum())


def _count_olive_green(img):
    """Khaki/olive green -- the grass-facing STRIP tint that is not 'strict grass green' but reads as
    a greenish streak (the rings=5 regression). g clearly over b, g >= r, moderately bright; excludes
    warm desert (b close to g) and strict grass (already counted)."""
    a = np.asarray(img).astype(int)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    return int(((g >= r - 2) & (g > b + 22) & (g > 110) & (r < g + 40)).sum())


def _tris5(dep):
    return [(p3, uv3, n3, topo, fam) for (p3, uv3, n3, topo, fam, blk) in dep]


def _render(tris, cam, look, W=960, H=600):
    return GE.render_grazing(tris, cam, look, 40.0, W, H, shade=True)


# ============================================================================================
# the DEPLOYED gate suite (all stock-derived bands)
# ============================================================================================
def gate_deployed(dep, prov, cal, cam, look):
    placed_R = prov["placed_R"]

    # (1) GREEN zero-threshold, stock-banded (per-tri) --------------------------------------------
    flat_above = mural_above = 0
    dep49_max = flat_max = 0.0
    n_sloped_nonrock_green = 0
    for (p3, uv3, n3, topo, fam, blk) in dep:
        if blk not in RC.CARRIED:
            continue
        gf = GE.tri_green_frac(uv3, nsub=12)
        if gf <= 0:
            continue
        if topo in ROCK:
            dep49_max = max(dep49_max, gf)
            mural_above += (gf > cal["mural49_green_band"])
        elif topo in GROUND:
            if _flat(n3):
                flat_max = max(flat_max, gf)
                flat_above += (gf > cal["flat_green_band"])
            else:
                n_sloped_nonrock_green += 1     # FIX-G's ny>=0.7 blind spot; deployed must be 0
    gate("GREEN flat-ground within the authentic stock desert band (0 tris above the generic-desert "
         f"max {cal['flat_green_band']:.3f})", flat_above == 0,
         f"deployed flat-ground green max={flat_max:.3f} above-band={flat_above}")
    gate("GREEN mesa-mural (topo-49) a faithful subset of stock's own mural (0 tris above stock-49 "
         f"max {cal['mural49_green_band']:.3f})", mural_above == 0,
         f"deployed topo-49 green max={dep49_max:.3f} above-band={mural_above}")
    gate("GREEN no sloped non-rock shard (0 green desert tris on sloped conform cells -- the FIX-G "
         "ny-blind-spot the rings=5 apron would open)", n_sloped_nonrock_green == 0,
         f"sloped non-rock green tris={n_sloped_nonrock_green}")

    # (2) GREEN per-pixel render ground truth (the witness; the per-tri gates above are the teeth).
    #     Note a deployed-vs-stock pixel compare is VACUOUS for green -- the stock-equivalent render
    #     still has comp[1]'s GRASS in frame (the desert island amputates it), so stock always shows
    #     far MORE green. The apples-to-apples green teeth live in the ANTI-TEST (rings=2 vs rings=5,
    #     same all-desert island). Here we only render + record the deployed ground truth.
    dep_img = _render(_tris5(dep), cam, look)
    dep_g, dep_o = _count_strict_green(dep_img), _count_olive_green(dep_img)
    dep_img.save(OUTD / "resid_gate_deployed.png")
    print(f"  [ground truth] deployed user-stance render: strict grass-green px={dep_g}, "
          f"olive/khaki strip-tint px={dep_o} (recorded, not gated -- see the anti-test)")

    # (3) ECOTONE colour-continuity (the CORRECTED ecotone gate -- replaces the mis-calibrated ring
    #     metric): carried desert colour within stock's own cell-to-cell desert spread of host ------
    d, (nc, nh), _ = desert_color_continuity(dep, placed_R)
    gate("ECOTONE colour-continuity: carried desert vs host desert mean colour within stock's own "
         f"cell-to-cell desert spread ({cal['color_band']:.1f})", d <= cal["color_band"],
         f"|carried-host| dRGB={d:.2f} (band {cal['color_band']:.2f}); carried={nc} host={nh} tris")

    # (4) FRAGMENT render A/B: deployed <= stock (0 orphan pale fragment) --------------------------
    gy = RC.ground_y([t for t in dep if t[5] in RC.CARRIED], *RC.CAMXZ)
    frags = RC.fragment_ab(dep, prov, gy)
    gate("FRAGMENT render A/B: no orphan pale fragment (deployed <= stock at every >=30px bar)",
         frags["faithful"], f"robust delta(min>=30px)={frags['delta']:+d} sweep={frags['sweep']}")

    # (5) STRAY-DUNE donor-twin: 0 orphans -------------------------------------------------------
    stray = RC.stray_dune_census(dep, prov)
    gate("STRAY-DUNE donor-twin: every stray topo-41 fleck has an exact stock twin (0 orphan "
         "freckles)", stray["n_orphan"] == 0,
         f"stray cells={stray['n_cells']} twins={stray['n_donor_twin']} orphans={stray['n_orphan']}")

    return dict(flat_green_max=flat_max, mural49_max=dep49_max, sloped_nonrock_green=n_sloped_nonrock_green,
                px_green_deployed=dep_g, px_olive_deployed=dep_o,
                color_dist=d, fragments=frags["sweep"], stray=stray, dep_img=dep_img)


# ============================================================================================
# THE ANTI-TEST -- build the forensics' rings=5 candidate + show the gates reject it
# ============================================================================================
def _fix_dune_distance(rings, donor, T):
    """Rebuild at `rings` and return the min distance from the geometry-moving fringe fixes to the
    dune core (the rung-7 'fixes live away from the dune boundary' invariant). Also the host-lift
    count + a user-stance olive-green pixel count. No deploy, no render of the A/B sheet here."""
    TC.MARGIN_RINGS = rings
    res = TC.build_and_gate(render=False)
    diag = res["diag"]
    touch = diag.get("fix_touch_xz", [])
    cs = {(c[0] + T[0], c[1] + T[1]) for c in donor["CORE"]}
    mind = min((min(TC._pt_cell_dist(px, pz, ci, cj) for (ci, cj) in cs) for (px, pz) in touch),
               default=1e9)
    return res, float(mind), diag.get("n_fixs_lifts", 0), diag.get("touched_blocks")


def anti_test(donor, T, cam, look, dep):
    print("\n" + "=" * 96)
    print("ANTI-TEST -- the forensics' rings=5 candidate, judged by the recalibrated gates")
    print("=" * 96)
    res2, d2, lifts2, tb2 = _fix_dune_distance(2, donor, T)
    res5, d5, lifts5, tb5 = _fix_dune_distance(5, donor, T)
    TC.MARGIN_RINGS = 2                                    # leave the module at the deployed value

    # render both from the user's stance + count olive-green
    def tris_of(res):
        out = []
        for blk, bm in res["built_bms"].items():
            out += GE._tris_of(bm, blk[0], blk[1])
        rebuilt = set(res["built_bms"])
        for (p3, uv3, n3, topo, fam, blk) in dep:
            cx = sum(p[0] for p in p3) / 3; cz = sum(p[2] for p in p3) / 3
            if (math.floor(cx / BLOCK), math.floor(-cz / BLOCK)) not in rebuilt:
                out.append((p3, uv3, n3, topo, fam))
        return out
    img2 = _render(tris_of(res2), cam, look)
    img5 = _render(tris_of(res5), cam, look)
    img2.save(OUTD / "resid_gate_rings2.png")
    img5.save(OUTD / "resid_gate_rings5_rejected.png")
    o2, o5 = _count_olive_green(img2), _count_olive_green(img5)

    print(f"  rings=2 (deployed): fix->dune-core dist={d2:.2f}u  host-lifts={lifts2}  olive-green px={o2}")
    print(f"  rings=5 (forensics fix): fix->dune-core dist={d5:.2f}u  host-lifts={lifts5}  olive-green px={o5}")

    # the anti-test gate: the recalibrated FIX-DISTANCE gate PASSES the deployed carry and FAILS the
    # rings=5 candidate -> the gate has teeth AND the forensics' fix is a regression at the dune edge.
    ok2 = d2 >= FIX_DUNE_DIST_MIN
    fail5 = d5 < FIX_DUNE_DIST_MIN
    gate(f"FIX-DISTANCE (deployed carry): geometry-moving fringe fixes stay >= {FIX_DUNE_DIST_MIN}u "
         "from the dune core (the rung-7 invariant)", ok2, f"deployed dist={d2:.2f}u")
    gate("ANTI-TEST has teeth: the SAME gate REJECTS the forensics' rings=5 candidate "
         "(fix drags onto the dune boundary)", fail5,
         f"rings=5 dist={d5:.2f}u < {FIX_DUNE_DIST_MIN}u; host-lifts {lifts2}->{lifts5}; "
         f"olive-green px {o2}->{o5}")

    # composite side-by-side witness
    from PIL import Image, ImageDraw
    W, H = img2.size
    sheet = Image.new("RGB", (W * 2 + 24, H + 46), (16, 16, 16))
    dr = ImageDraw.Draw(sheet)
    dr.text((8, 6), "THE FORENSICS' FIX, REFUTED -- user stance (1219,-1160 SSE), real atlas.",
            fill=(255, 230, 140))
    dr.text((8, 24), f"LEFT rings=2 DEPLOYED (faithful; fix 5.66u from dunes, olive-green {o2}px)  |  "
                     f"RIGHT rings=5 REJECTED (fix 0.0u onto dunes, {lifts5} host-lifts, olive-green "
                     f"{o5}px)", fill=(220, 220, 220))
    sheet.paste(img2, (8, 40)); sheet.paste(img5, (W + 16, 40))
    sheet.save(OUTD / "resid_gate_antitest_ab.png")
    print(f"  -> {OUTD / 'resid_gate_antitest_ab.png'}")

    return dict(rings2=dict(fix_dune_dist=d2, host_lifts=lifts2, olive_px=o2, touched=tb2),
                rings5=dict(fix_dune_dist=d5, host_lifts=lifts5, olive_px=o5, touched=tb5),
                fix_dist_min=FIX_DUNE_DIST_MIN, deployed_ok=ok2, rings5_rejected=fail5)


# ============================================================================================
# main
# ============================================================================================
def main():
    print("=== dunes_residual_gates.py -- THE RECALIBRATED RESIDUAL GATE SUITE (rung 9) ===\n")
    prov = RC.reconstruct_provenance()
    donor, T = prov["donor"], prov["T"]
    print(f"provenance: T(donor->deployed)={T}  |placed_R|={len(prov['placed_R'])}\n")

    cal = calibrate()
    dep = RC.load_deployed(RC.CTX)
    cam, look, _ = _user_cam(dep)

    print("\n--- DEPLOYED gate suite (all bands stock-derived) ---")
    dep_info = gate_deployed(dep, prov, cal, cam, look)

    anti = anti_test(donor, T, cam, look, dep)

    n_fail = sum(1 for _, ok, _ in GATES if not ok)
    print(f"\n=== {len(GATES)} gates, {n_fail} FAILED ===")
    verdict = ("ALL DEPLOYED GATES PASS + the anti-test rejects the forensics' rings=5 fix -> the "
               "faithful carry is already correct; NO byte changed." if n_fail == 0
               else "GATE FAILURE -- investigate.")
    print(verdict)

    out = dict(
        provenance=dict(T=list(T), placed_R=len(prov["placed_R"])),
        calibration=cal,
        deployed=dict(flat_green_max=dep_info["flat_green_max"], mural49_max=dep_info["mural49_max"],
                      sloped_nonrock_green=dep_info["sloped_nonrock_green"],
                      color_dist=dep_info["color_dist"],
                      px_green_deployed=dep_info["px_green_deployed"],
                      px_olive_deployed=dep_info["px_olive_deployed"],
                      fragment_sweep=dep_info["fragments"],
                      stray=dict(cells=dep_info["stray"]["n_cells"], twins=dep_info["stray"]["n_donor_twin"],
                                 orphans=dep_info["stray"]["n_orphan"])),
        anti_test=anti,
        gates=[{"name": n, "ok": ok, "detail": str(d)} for n, ok, d in GATES],
        n_gates=len(GATES), n_failed=n_fail, verdict=verdict, deployed_bytes_changed=False,
    )
    (OUTD / "dunes_residual_gates.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"\n-> {OUTD / 'dunes_residual_gates.json'}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
