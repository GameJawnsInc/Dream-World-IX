"""RUNG F FRAME -- the F2 SILHOUETTE CEILING measurement (READ-ONLY, frame-only).

OPTION (c)'s open item is F2: the minted coast reads med_turn 3.7, below the stock 8-35 band. This
ladder measures how far F2 can be pushed at the site's fixed centre (160,-1152)/R125 (the radius the
verbatim carry weld depends on) using build_landmass's undulation + n_corners knobs -- to prove
whether F2 is a tuning miss or a SITE/RADIUS limitation.

RESULT (out/rung_f/f2_ceiling.json): corners-OFF, med_turn rises only 3.70 -> 3.92 across undulation
0.02..0.11 (gentle waves, median barely moves); corners-ON (the only knob that raises med_turn)
throws build_landmass's on-grain gate ('an over-8u grass edge has 1 owner(s)') at EVERY config,
because corners stretch rim arcs past 8u at R125. => F2's 8-35 band is UNREACHABLE at this site via
the shipped generator; the buildable ceiling is ~3.9. F2 is a site limitation, not a tuning miss.

Run: cd studies/overworld-topography && py rung_f_f2_ceiling.py
"""
from __future__ import annotations
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg          # noqa: E402
from ff9mapkit.world import island as ISL     # noqa: E402
import rung_f_layout as RFL                    # noqa: E402

OUT = HERE / "out" / "rung_f" / "f2_ceiling.json"


def main():
    gr = Path(_cfg.find_game_path(None))
    C, R, LH, SB = RFL.ISLAND_CENTER, RFL.ISLAND_RADIUS, RFL.LAND_HEIGHT, RFL.SITE_BLOCKS
    rows = []
    for und in (0.02, 0.04, 0.06, 0.08, 0.10, 0.11):
        for nc in (0, 3):
            cs = 0.26 if nc else 0.0
            try:
                b = ISL.build_landmass(center=C, base_radius=R, seed=40.0, lobes=1, land_height=LH,
                                       ground="grass", relief_amp=0.0, undulation=und, n_corners=nc,
                                       corner_strength=cs, n_patches=0, disc=1, game=gr)
                pl = ISL._sea_plane(disc=1, game=gr)
                v = ISL.verify_landmass(b, sea_plane=pl, land_height=LH)
                sh = v["shape"]
                rows.append(dict(und=und, nc=nc, built=True, med=round(sh["med_turn"], 2),
                                 mx=round(sh["max_turn"], 1), ac=round(sh["acute"], 3),
                                 bok=SB.issuperset(set(b["blocks"]))))
                print(f"OK und={und} nc={nc} med={rows[-1]['med']} mx={rows[-1]['mx']} bok={rows[-1]['bok']}")
            except Exception as e:
                rows.append(dict(und=und, nc=nc, built=False, err=str(e)[:60]))
                print(f"ERR und={und} nc={nc} {str(e)[:60]}")
    OUT.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    built = [r for r in rows if r.get("built")]
    print(f"\nF2 buildable ceiling med_turn = {max(r['med'] for r in built)} "
          f"| corners-on always fail on-grain: {all(not r.get('built') for r in rows if r['nc'] == 3)}")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
