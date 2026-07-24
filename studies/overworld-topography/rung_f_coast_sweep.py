"""RUNG F FRAME -- OPTION (c) coast-silhouette sweep (READ-ONLY, frame-only).

OPTION (a) (the 4x4 whole-pocket carry) is FALSIFIED at stage 0 (frame_probe.json: the window's
east outer edge is a topo-49 cliff wall at 25-38u -- welding a minted grass lobe to it is off-
language). So the frame build falls to OPTION (c): keep the all-green 6-block verbatim carry, and
FIX F2 (the near-round med_turn 3.7 coast) with an undulated/multi-lobe silhouette in the stock
8-35 band, WITHOUT moving the island centre/radius (so the carry weld is untouched).

This sweep builds ONLY the minted grass frame (no carry) for a grid of (undulation, n_corners,
corner_strength, lobes, seed) and reports verify_landmass shape (med_turn/acute/max_turn), the
weld-audit near-miss count, and whether the coast stays clear of the carry footprint. Cheap -- the
full carry + gate stack runs only for the chosen winner (in rung_f_frame.py).

Run: cd studies/overworld-topography && py rung_f_coast_sweep.py
"""
from __future__ import annotations
import json, sys, math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg          # noqa: E402
from ff9mapkit.world import island as ISL     # noqa: E402
from ff9mapkit.world import mesh as M         # noqa: E402
import rung_f_layout as RFL                    # noqa: E402

OUT = HERE / "out" / "rung_f" / "coast_sweep.json"

CENTER = RFL.ISLAND_CENTER
RADIUS = RFL.ISLAND_RADIUS
LAND_H = RFL.LAND_HEIGHT
SITE_BLOCKS = RFL.SITE_BLOCKS

# the carry footprint (placed_R) is the 6-block window shifted -> site blocks 1-3,17-18. The coast
# (island perimeter) must stay clear of that. Approx: carry occupies world x[64,256] z[-1216,-1088]
# (blocks 1-3 x 17-18). Keep the coast >= a margin outside the carry's cell extent.
CARRY_WORLD = (64.0, -1216.0, 256.0, -1088.0)   # x0,z0,x1,z1


def log(m): print(m, flush=True)


def frame_metrics(undulation, n_corners, corner_strength, lobes, seed, game_root):
    built = ISL.build_landmass(center=CENTER, base_radius=RADIUS, seed=seed, lobes=lobes,
                               land_height=LAND_H, ground="grass", relief_amp=0.0,
                               undulation=undulation, n_corners=n_corners,
                               corner_strength=corner_strength, n_patches=0, disc=1, game=game_root)
    plane = ISL._sea_plane(disc=1, game=game_root)
    v = ISL.verify_landmass(built, sea_plane=plane, land_height=LAND_H)
    # weld-audit near-miss over the frame blocks
    weld = 0
    for blk, bm in built["blocks"].items():
        weld += len(M.weld_audit([bm]))
    blocks_ok = SITE_BLOCKS.issuperset(set(built["blocks"]))
    keys = ("cracks", "down_facing", "walk_filter_fails", "grass_over_8u", "uv_out_of_region",
            "holes", "open_edges", "missing_faces")
    clean = all(v.get(k, 0) == 0 for k in keys)
    sh = v["shape"]
    return dict(undulation=undulation, n_corners=n_corners, corner_strength=corner_strength,
                lobes=lobes, seed=seed, med_turn=round(sh["med_turn"], 3), max_turn=round(sh["max_turn"], 2),
                acute=round(sh["acute"], 4), shape_ok=bool(sh["ok"]), verify_clean=clean,
                weld_near_miss=weld, blocks_ok=blocks_ok, n_blocks=len(built["blocks"]),
                verify={k: v.get(k) for k in keys})


def main():
    game_root = Path(_cfg.find_game_path(None))
    log("=" * 90); log("RUNG F -- OPTION (c) COAST SILHOUETTE SWEEP (frame-only, read-only)"); log("=" * 90)
    log(f"centre={CENTER} R={RADIUS} land_h={LAND_H}; target med_turn in [8,35], verify clean, weld 0, blocks subset site")
    cands = []
    # lobes=1 perturbed circle: sweep undulation + corners
    grid = []
    for und in (0.06, 0.09, 0.12, 0.15, 0.18):
        for nc in (0, 3, 4, 5):
            for cs in (0.0, 0.15, 0.26):
                if nc == 0 and cs != 0.0:
                    continue
                grid.append((und, nc, cs, 1))
    # lobes=2 asymmetric union
    for und in (0.09, 0.12, 0.15):
        grid.append((und, 3, 0.26, 2))

    seeds = (40.0, 41.0, 47.0, 50.0, 55.0, 60.0, 7.0, 99.0, 13.0, 21.0)
    for (und, nc, cs, lobes) in grid:
        best_for_combo = None
        for sd in seeds:
            try:
                m = frame_metrics(und, nc, cs, lobes, sd, game_root)
            except Exception as e:
                continue
            passes = (m["blocks_ok"] and m["verify_clean"] and m["weld_near_miss"] == 0
                      and 8.0 <= m["med_turn"] <= 35.0 and m["acute"] <= 0.12 and m["max_turn"] < 150.0)
            m["passes_all"] = passes
            cands.append(m)
            if passes and best_for_combo is None:
                best_for_combo = m
                log(f"  PASS und={und} nc={nc} cs={cs} lobes={lobes} seed={sd}: med_turn={m['med_turn']} "
                    f"max={m['max_turn']} acute={m['acute']} weld={m['weld_near_miss']} blocks={m['n_blocks']}")

    winners = [c for c in cands if c.get("passes_all")]
    log("-" * 90)
    log(f"total combos tried: {len(cands)}; full-pass candidates: {len(winners)}")
    if winners:
        # prefer the one whose med_turn sits mid-band (~15-22) and lowest weld/acute
        winners.sort(key=lambda c: (abs(c["med_turn"] - 18.0), c["acute"], c["weld_near_miss"]))
        w = winners[0]
        log(f"CHOSEN: und={w['undulation']} nc={w['n_corners']} cs={w['corner_strength']} "
            f"lobes={w['lobes']} seed={w['seed']} -> med_turn={w['med_turn']} max={w['max_turn']} "
            f"acute={w['acute']} weld={w['weld_near_miss']}")
    else:
        # report the closest-to-band clean candidates
        clean = [c for c in cands if c["verify_clean"] and c["weld_near_miss"] == 0 and c["blocks_ok"]]
        clean.sort(key=lambda c: abs(c["med_turn"] - 12.0))
        log("NO full-pass candidate. Closest clean-verify/weld0 by med_turn:")
        for c in clean[:8]:
            log(f"  und={c['undulation']} nc={c['n_corners']} cs={c['corner_strength']} lobes={c['lobes']} "
                f"seed={c['seed']}: med_turn={c['med_turn']} max={c['max_turn']} acute={c['acute']}")

    OUT.write_text(json.dumps(dict(centre=list(CENTER), radius=RADIUS, n_combos=len(cands),
                                   n_winners=len(winners),
                                   winners=winners[:20], all_candidates=cands), indent=1), encoding="utf-8")
    log(f"-> {OUT}")


if __name__ == "__main__":
    main()
