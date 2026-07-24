"""RUNG F -- THE FRAME BUILD (attempt 1), 2026-07-24.

The approved frame design (out/rung_f/frame_design_round2.json) was OPTION (a): widen the verbatim
carry to a 4x4 (256x256u) stock window (blocks 12-15,10-13) that INCLUDES the junction's OWN
enclosing rock, so the mountain-ringed-basin FORM comes from stock bytes. Its premise: the window's
outer boundary returns to LOWLAND GRASS on the open N+E, weldable to a minted coast.

STAGE-0 MEASUREMENT FALSIFIES THAT PREMISE (rung_f_frame_probe.py -> out/rung_f/frame_probe.json,
zero playtest cost): the 4x4 window's EAST OUTER EDGE is a topo-49 CLIFF WALL (435 cliff tris +
109 topo-36/37 highland-rock tris) standing at y 25-38u -- the Daguerreo massif's east flank. The
window cuts straight THROUGH the massif; there is no open-east pocket mouth at the window edge, and
a minted flat-grass "E lobe" would weld to a 37u cliff (off-language). West + south outer edges are
also rock-walled/high in part. The basin_envelope's "E open / S+W walled" reading marched OUT from
the ecotone bbox a few cells and never reached the window's actual outer edge -- exactly the "which
tree did each measure" discrepancy the task flagged as UNRECONCILED. OPTION (a) does not fit the
320x256u site because the enclosing massif is 448x384u and its coast-facing flank is a 37u cliff.

=> THE FRAME BUILD FALLS TO OPTION (c) (the design's own honest fallback): keep the ALL-GREEN
6-block verbatim carry, FIX F2 (the near-round med_turn 3.7 coast) with an undulated silhouette in
the stock 8-35 band, and add relief on the minted grass only -- WITHOUT moving the island
centre/radius (so the proven carry weld is untouched). F1 (the mountain-ringed-basin ENCLOSURE)
is recorded UNSOLVED-AT-THIS-SITE with the frame_probe measurement as the evidence: the site
physically cannot host the pocket via a >=4x4 carry.

This module: (1) records the OPTION (a) falsification; (2) builds OPTION (c) by re-running
rung_f_layout.compose with an undulated coast (+ optional relief on minted grass, core-faded off
every carried cell); (3) runs the FULL rung_f_build gate stack + the contract screen; (4) renders
planview/oblique + a context-matched oblique; (5) writes out/rung_f/frame_build.json and injects a
"frame" section into out/rung_f/rung_f_build.json. Stages to out/rung_f/FF9CustomMap-world.

READ-ONLY vs the game install. NO deploy / --apply / mirror / commit.

Run: cd studies/overworld-topography && py rung_f_frame.py [und nc cs lobes seed [relief_amp]]
"""
from __future__ import annotations
import json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg          # noqa: E402
from ff9mapkit.world import island as ISL     # noqa: E402
from ff9mapkit.world import extract as X       # noqa: E402
from ff9mapkit.world.extract import CH_POS      # noqa: E402
import rung_f_layout as RFL                    # noqa: E402
import rung_f_build as RFB                      # noqa: E402

OUT_DIR = HERE / "out" / "rung_f"
FRAME_JSON = OUT_DIR / "frame_build.json"
BUILD_JSON = OUT_DIR / "rung_f_build.json"
PROBE_JSON = OUT_DIR / "frame_probe.json"


def log(m): print(m, flush=True)


# ------------------------------------------------------------------------------------------------
# OPTION (a) falsification record (from the stage-0 read-only probe)
# ------------------------------------------------------------------------------------------------
def option_a_falsification():
    probe = json.loads(PROBE_JSON.read_text(encoding="utf-8")) if PROBE_JSON.exists() else {}
    per_side = probe.get("per_side", {})
    return dict(
        verdict="FALSIFIED AT STAGE 0 (measured bytes, zero playtest cost)",
        design="OPTION (a) -- widen carry to a 4x4 (256x256u) window (blocks 12-15,10-13) incl. the "
               "enclosing rock; block 4 = a minted grass E lobe at the 'open pocket mouth'.",
        premise="the window's outer boundary returns to lowland grass (open N+E), weldable to a "
                "minted flat-grass coast at land_height.",
        measurement="rung_f_frame_probe.py -> frame_probe.json: the 4x4 window's per-side outer-ring "
                    "height/topo; the E outer-edge topo histogram.",
        finding="the EAST outer edge (block 15 east, cells x>=252) is a topo-49 CLIFF WALL (435 cliff "
                "tris + 109 topo-36/37 highland-rock + 45 topo-10 plateau-grass, only 2 low grass "
                "tris) at y 25-38u -- the Daguerreo massif's east flank. E outer-ring cells >8u = "
                "63/63. W ring y_p50 9.7u (8 of 16 present cells >8u), S ring y_max 21.2u (15 cells "
                ">8u). The window cuts THROUGH the massif; there is NO open-east lowland pocket mouth "
                "at the window edge, so a minted flat-grass E lobe would weld to a 37u cliff "
                "(off-language). Only N is lowland where present (41/64 N ring cells are ocean).",
        why_the_envelope_missed_it="basin_envelope.py marched OUT from the ecotone bbox ~a few cells "
                "and read rock-FAMILY only; topo-49 cliff + topo-10 plateau decode to FAM=None, so "
                "'E: 0% rock' read as OPEN. The window's ACTUAL outer edge (24u further E) is the "
                "massif cliff. This is the 'which tree did each measure' discrepancy the task flagged.",
        physical_ceiling="the full Daguerreo massif (calib_context basin) is ~448x384u; its "
                "coast-facing flank is a 37u topo-49 cliff. It cannot fit the 320x256u ocean site, "
                "and its outer flank is un-weldable to a minted coast. OPTION (a) / 5x4 / 4x3 all "
                "share this east-cliff edge (going wider EAST climbs deeper INTO the massif -- worse).",
        per_side_outer_ring=per_side,
        conclusion="F1 (the mountain-ringed-basin ENCLOSURE) is UNSOLVED AT THIS SITE. A faithful "
                "pocket carry needs a site that can host the whole 448x384u massif OR a delivery "
                "fused into continental land beside the real massif -- a mechanism change beyond a "
                "frame design. The honest floor = OPTION (c): the verbatim ecotone carry (F1's "
                "arrangement/saturation/backing are stock's, BY CONSTRUCTION) on an F2-corrected coast.")


# ------------------------------------------------------------------------------------------------
# relief on the minted grass only (core-faded off every carried cell)
# ------------------------------------------------------------------------------------------------
def _carry_rect_cells():
    """The deterministic carry footprint region = the donor window rect shifted, +1 cell margin.
    Relief is zeroed within FADE cells of this and smoothstepped out -- keeps the carry weld flat."""
    Tx, Tz = RFL.SHIFT_CELLS
    x0 = RFL.DONOR_CELL_X[0] + Tx - 1
    x1 = RFL.DONOR_CELL_X[1] + Tx + 1
    z0 = RFL.DONOR_CELL_Y[0] + Tz - 1
    z1 = RFL.DONOR_CELL_Y[1] + Tz + 1
    return (x0, x1, z0, z1)


def _install_relief(relief_amp, fade_cells=3):
    """Monkeypatch RFL.mint_grass_frame to build the frame WITH relief, then FLATTEN relief (restore
    land_height) on every grass vertex within FADE cells of the carry rect, smoothstepping to full
    relief over the next FADE cells. THE CORE FADE: the carry weld ring stays byte-flat."""
    orig = RFL.mint_grass_frame
    CELL = RFL.CELL
    LAND_H = RFL.LAND_HEIGHT
    x0, x1, z0, z1 = _carry_rect_cells()

    def cheby_cells_to_rect(cx, cz):
        dx = 0 if x0 <= cx <= x1 else (x0 - cx if cx < x0 else cx - x1)
        dz = 0 if z0 <= cz <= z1 else (z0 - cz if cz < z0 else cz - z1)
        return max(dx, dz)

    def patched(game_root):
        built = ISL.build_landmass(center=RFL.ISLAND_CENTER, base_radius=RFL.ISLAND_RADIUS,
                                   seed=RFL.ISLAND_SEED, lobes=RFL.ISLAND_LOBES,
                                   land_height=LAND_H, ground="grass", relief_amp=relief_amp,
                                   undulation=RFL.ISLAND_UNDULATION, n_corners=RFL.ISLAND_N_CORNERS,
                                   corner_strength=RFL.ISLAND_CORNER_STRENGTH, n_patches=0,
                                   disc=1, game=game_root)
        if relief_amp <= 0.0:
            return built
        n_flat = 0
        for blk, bm in built["blocks"].items():
            ox, oz = X.block_world_origin(blk[0], blk[1])
            arrs = [bm.verts]
            pos = bm.chan_arrays.get(CH_POS)
            if pos is not None and pos is not bm.verts:
                arrs.append(pos)
            for arr in arrs:
                for v in arr:
                    wx = v[0] + ox
                    wz = v[2] + oz
                    cx = math.floor(wx / CELL)
                    cz = math.floor(wz / CELL)
                    d = cheby_cells_to_rect(cx, cz)
                    if d <= fade_cells:
                        # full flatten inside fade_cells of the carry; the carried cells overwrite
                        # this block anyway, but the minted grass in a partly-carried block welds flat.
                        if abs(v[1] - LAND_H) > 1e-9:
                            v[1] = LAND_H
                            n_flat += 1
        built["_relief_flattened_verts"] = n_flat
        return built

    RFL.mint_grass_frame = patched
    return orig


# ------------------------------------------------------------------------------------------------
# OPTION (c) build -- reuse the rung_f_build gate stack with the overridden coast/relief
# ------------------------------------------------------------------------------------------------
def build_option_c(und, nc, cs, lobes, seed, relief_amp, game_root):
    # override the coast knobs on rung_f_layout (compose reads them at call time)
    RFL.ISLAND_UNDULATION = und
    RFL.ISLAND_N_CORNERS = nc
    RFL.ISLAND_CORNER_STRENGTH = cs
    if not hasattr(RFL, "ISLAND_LOBES"):
        RFL.ISLAND_LOBES = 1
    RFL.ISLAND_LOBES = lobes
    RFL.ISLAND_SEED = seed

    # patch mint_grass_frame -- it currently hard-codes lobes=1/relief=0; make it read the knobs.
    orig_mint = _install_relief(relief_amp)

    RFB.GATES.clear()
    comp = RFL.compose(game_root)
    s0 = RFB.stage0_site(game_root, set(comp["final_blocks"].keys()))
    s1 = RFB.stage1_frame_verify(comp["built"], game_root)
    s2 = RFB.stage2_rigidity(comp)
    s3 = RFB.stage3_event_strip(comp)
    s4 = RFB.stage4_composite_plumbing(comp)
    s5 = RFB.stage5_sea_and_gates(comp, game_root)
    s6 = RFB.stage6_write(comp, s5)
    s7 = RFB.stage7_contract(game_root)
    s8 = stage8_renders_frame(comp)

    RFL.mint_grass_frame = orig_mint

    plumbing_gates = [g for g in RFB.GATES if not g["name"].startswith("CONTRACT")
                      and not g["name"].startswith("ADVISORY")]
    contract_gates = [g for g in RFB.GATES if g["name"].startswith("CONTRACT")]
    advisory_gates = [g for g in RFB.GATES if g["name"].startswith("ADVISORY")]
    plumbing_green = all(g["ok"] for g in plumbing_gates)
    contract_green = s7["all_three_pass"] and s7["stock_pass"]
    all_green = plumbing_green and contract_green
    f2_pass = bool(s1["shape"]["ok"])
    return dict(
        comp_diag=comp["diag"], s0=s0, s1=s1, s2=s2, s3=s3, s4=s4,
        s5={k: s5[k] for k in ("sea_layer_ok", "orphan_ok", "wang_ok", "mod_ok", "n_armed", "donor_ref")},
        s5_orphan={k: s5["orphan"].get(k) for k in ("n_orphans", "n_ambiguous", "n_orphans_pre_redress", "ok")},
        s6=s6, s7=dict(all_three_pass=s7["all_three_pass"], stock_pass=s7["stock_pass"],
                       calibration=s7["calibration"],
                       R1=s7["rung_f"]["R1"], R2v=s7["rung_f"]["R2"]["verdict"],
                       R3v=s7["rung_f"]["R3"]["verdict"], overall=s7["rung_f"]["overall"]),
        renders=s8,
        gates=[dict(g) for g in RFB.GATES],
        plumbing_green=plumbing_green, contract_green=contract_green, all_green=all_green,
        f2_pass=f2_pass, f2_shape=s1["shape"],
        plumbing_failed=[g["name"] for g in plumbing_gates if not g["ok"]],
        contract_failed=[g["name"] for g in contract_gates if not g["ok"]],
        advisory_failed=[g["name"] for g in advisory_gates if not g["ok"]],
        coast=dict(undulation=und, n_corners=nc, corner_strength=cs, lobes=lobes, seed=seed,
                   relief_amp=relief_amp))


def stage8_renders_frame(comp):
    """Reuse rung_f_build's renders (planview/shaded/oblique) + add a CONTEXT-MATCHED oblique (a
    low-pitch az-215 shot like the eye's decisive calibration panel calib_context_oblique)."""
    base = RFB.stage8_renders(comp)
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return base
    from seam_null_recon import FAM_OF
    RENDER_DIR = RFB.RENDER_DIR
    LAND_HEIGHT = RFL.LAND_HEIGHT
    final = comp["final_blocks"]
    FAM_COL = {"grass": (86, 140, 60), "desert": (200, 176, 110), "dunes": (222, 200, 140),
               "rock": (120, 112, 104), None: (150, 150, 150)}
    tris = []
    for blk, bm in final.items():
        ox, oz = X.block_world_origin(blk[0], blk[1])
        for tri in bm.tris:
            p3 = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            fam = FAM_OF.get(topo)
            if topo == 49:
                fam = "rock"
            tris.append((p3, FAM_COL.get(fam, FAM_COL[None])))
    xs = [p[0] for (p3, _c) in tris for p in p3]
    zs = [p[2] for (p3, _c) in tris for p in p3]
    cxw, czw = (min(xs) + max(xs)) / 2.0, (min(zs) + max(zs)) / 2.0
    az = math.radians(215.0)
    pr = math.radians(16.0)                     # LOW pitch = the calib_context_oblique framing
    proj = []
    order = sorted(tris, key=lambda t: -(math.cos(az) * (sum(p[0] for p in t[0]) / 3 - cxw)
                                         + math.sin(az) * (sum(p[2] for p in t[0]) / 3 - czw)))
    pts_all = []
    for (p3, col) in order:
        sp = []
        for p in p3:
            dx = p[0] - cxw; dz = p[2] - czw; dy = p[1] - LAND_HEIGHT
            rx = math.cos(az) * dx - math.sin(az) * dz
            rz = math.sin(az) * dx + math.cos(az) * dz
            sy = rz * math.sin(pr) - dy * math.cos(pr)
            sp.append((rx, sy)); pts_all.append((rx, sy))
        proj.append((sp, p3, col))
    pxs = [q[0] for q in pts_all]; pys = [q[1] for q in pts_all]
    W, H = 1100, 520
    s = min((W - 40) / (max(pxs) - min(pxs)), (H - 40) / (max(pys) - min(pys)))
    img = Image.new("RGB", (W, H + 26), (20, 22, 26)); dr = ImageDraw.Draw(img)
    dr.text((20, 6), "RUNG F FRAME -- context oblique (az215/pitch16, calib-matched): the verbatim "
            "ecotone carry as a low decal-scatter on a flat grass island (F1 basin ring absent -- "
            "UNSOLVED at this site)", fill=(235, 225, 170))
    lv = (0.4, 0.82, 0.4); ll = math.sqrt(sum(c * c for c in lv)); lv = [c / ll for c in lv]
    for (sp, p3, col) in proj:
        pts = [(20 + (q[0] - min(pxs)) * s, 26 + 20 + (q[1] - min(pys)) * s) for q in sp]
        e1 = [p3[1][k] - p3[0][k] for k in range(3)]; e2 = [p3[2][k] - p3[0][k] for k in range(3)]
        gn = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]
        gl = math.sqrt(sum(q * q for q in gn)) or 1.0
        sh = max(0.35, min(1.0, 0.45 + 0.55 * abs(sum(gn[k] * lv[k] for k in range(3)) / gl)))
        dr.polygon(pts, fill=tuple(int(v * sh) for v in col))
    p = RENDER_DIR / "rung_f_context_oblique.png"
    img.save(p)
    base.setdefault("rendered", []).append(str(p))
    log(f"  wrote rung_f_context_oblique.png")
    return base


# ------------------------------------------------------------------------------------------------
# main
# ------------------------------------------------------------------------------------------------
def main():
    game_root = Path(_cfg.find_game_path(None))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log("=" * 96); log("RUNG F -- THE FRAME BUILD (attempt 1): OPTION (a) FALSIFIED -> OPTION (c)"); log("=" * 96)

    fa = option_a_falsification()
    log(f"OPTION (a): {fa['verdict']}")
    log(f"  finding: {fa['finding'][:160]}...")

    # coast params: CLI override, else the sweep winner (coast_sweep default), else a conservative default
    args = sys.argv[1:]
    if len(args) >= 5:
        und, nc, cs, lobes, seed = (float(args[0]), int(args[1]), float(args[2]), int(args[3]), float(args[4]))
        relief_amp = float(args[5]) if len(args) >= 6 else 0.0
    else:
        cs_json = OUT_DIR / "coast_sweep.json"
        und, nc, cs, lobes, seed, relief_amp = 0.13, 3, 0.26, 1, 40.0, 0.0
        if cs_json.exists():
            try:
                sw = json.loads(cs_json.read_text(encoding="utf-8"))
                if sw.get("winners"):
                    w = sw["winners"][0]
                    und, nc, cs, lobes, seed = (w["undulation"], w["n_corners"], w["corner_strength"],
                                                w["lobes"], w["seed"])
            except Exception:
                pass
    log(f"OPTION (c) coast: undulation={und} n_corners={nc} corner_strength={cs} lobes={lobes} "
        f"seed={seed} relief_amp={relief_amp}")

    res = build_option_c(und, nc, cs, lobes, seed, relief_amp, game_root)

    frame = dict(
        step="RUNG F FRAME BUILD (attempt 1)",
        date="2026-07-24", read_only=True, zero_game_writes=True, zero_deploys=True,
        option_a_falsification=fa,
        option_c=dict(
            mechanism="the ALL-GREEN 6-block verbatim ecotone carry (F1 arrangement/saturation/"
                      "backing = stock's BY CONSTRUCTION) on an F2-corrected undulated coast + relief "
                      "on the minted grass only (core-faded off every carried cell). Island centre/"
                      "radius UNCHANGED from the all-green base -> the proven carry weld is untouched.",
            coast=res["coast"],
            plumbing_green=res["plumbing_green"], contract_green=res["contract_green"],
            all_green=res["all_green"],
            f2_silhouette=dict(target_band=[8.0, 35.0], med_turn=res["f2_shape"]["med_turn"],
                               max_turn=res["f2_shape"]["max_turn"], acute=res["f2_shape"]["acute"],
                               passes=res["f2_pass"]),
            R1=dict(verdict=res["s7"]["R1"]["verdict"],
                    measured={k: res["s7"]["R1"]["checks"][k]["measured_u"] for k in res["s7"]["R1"]["checks"]},
                    floors="39.953/44.635/42.968",
                    convention_invalid=res["s7"]["R1"]["convention_invalid"]),
            R2=res["s7"]["R2v"], R3=res["s7"]["R3v"],
            calibration=res["s7"]["calibration"],
            once_edges_above_skirt=res["s4"]["open_edges_above_skirt"],
            weld_near_miss=res["s4"]["weld_near_miss"],
            down_grass_or_apron=res["s4"]["down_grass_or_apron"],
            relief_flatten="relief applied to minted grass only; flattened within 3 cells of the carry "
                           "rect (the CORE FADE) so the weld ring stays byte-flat.",
            f1_status="UNSOLVED AT THIS SITE (see option_a_falsification): the mountain-ringed-basin "
                      "ENCLOSURE cannot be carried into the 320x256u site -- the window's east flank "
                      "is a 37u topo-49 massif cliff. R2/R3 arrangement+backing ARE stock's (verbatim "
                      "carry), so the ecotone's own two-ground character ships; the surrounding "
                      "MASSIF RING does not.",
            gates=res["gates"],
            plumbing_failed=res["plumbing_failed"], contract_failed=res["contract_failed"],
            advisory_failed=res["advisory_failed"],
            renders=res["renders"]),
        headline=("FRAME BUILD attempt 1: OPTION (a) [4x4 whole-pocket carry] FALSIFIED AT STAGE 0 "
                  "(the window's east outer edge is a 37u topo-49 massif cliff, not an open pocket "
                  "mouth). Fell to OPTION (c): the all-green verbatim ecotone carry on an F2-corrected "
                  f"coast (med_turn {res['f2_shape']['med_turn']} vs [8,35], passes={res['f2_pass']}) "
                  + ("+ relief" if res["coast"]["relief_amp"] > 0 else "") + ". Plumbing "
                  + ("GREEN" if res["plumbing_green"] else "RED") + ", contract "
                  + ("GREEN" if res["contract_green"] else "RED")
                  + f" (R1 {res['s7']['R1']['verdict']} R2 {res['s7']['R2v']} R3 {res['s7']['R3v']}). "
                  "F1 (the massif basin ENCLOSURE) recorded UNSOLVED-AT-THIS-SITE with the "
                  "frame_probe measurement as evidence. ZERO deploy."),
        all_green=res["all_green"] and res["f2_pass"])

    FRAME_JSON.write_text(json.dumps(frame, indent=1, default=str), encoding="utf-8")
    log(f"-> {FRAME_JSON}")

    # inject the frame section into rung_f_build.json (keep the base build record intact)
    if BUILD_JSON.exists():
        try:
            doc = json.loads(BUILD_JSON.read_text(encoding="utf-8"))
        except Exception:
            doc = {}
    else:
        doc = {}
    doc["frame"] = frame
    BUILD_JSON.write_text(json.dumps(doc, indent=1, default=str), encoding="utf-8")
    log(f"-> injected 'frame' section into {BUILD_JSON}")

    log("\n" + "=" * 96)
    log(f"PLUMBING {'GREEN' if res['plumbing_green'] else 'RED'} | CONTRACT "
        f"{'GREEN' if res['contract_green'] else 'RED'} | F2 {'PASS' if res['f2_pass'] else 'FAIL'} "
        f"({res['f2_shape']['med_turn']}) | FRAME all_green={frame['all_green']}")
    log(f"plumbing failed: {res['plumbing_failed']}")
    log(f"contract failed: {res['contract_failed']}")
    return 0 if frame["all_green"] else 1


if __name__ == "__main__":
    sys.exit(main())
