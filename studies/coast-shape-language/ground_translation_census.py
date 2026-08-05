"""THE GROUND TRANSLATION CENSUS -- is `X -> Y` mains a pure rect translation, or only `grass -> X`?

`GroundRetile` retiles a carried landmass from one ground family to another. Its mains
branch is gated on `GRASS_TOPOS`, so only a GRASS source can classify -- the translation
census (island717_retile_census.py) measured `grass -> X` and nothing else. That is the
ceiling `--ground` now reports.

The delta itself is family-agnostic arithmetic:

    mains_d = (GROUNDS[dst].mains_du - GROUNDS[src].mains_du,
               GROUNDS[dst].mains_dv - GROUNDS[src].mains_dv)

so the OPEN question is empirical, not architectural: **do a non-grass family's mains
occupy their rect the same way grass's do?** If every family's mains uvs sit at the same
offsets within their own rect, the translation carries any source. If desert's mains use a
different internal layout, translating them lands on the wrong texels and the retile would
be green-but-wrong -- the failure mode this arc is most prone to.

Measured per family, from the user's own install:
  * how many mains tris each family has, and in how many blocks
  * the mains uvs expressed RELATIVE to that family's own rect origin
  * whether those relative layouts agree across families (the translation's precondition)

  py studies/coast-shape-language/ground_translation_census.py [--disc 1]

Read-only; writes JSON to out/.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import extract as X                     # noqa: E402
from ff9mapkit.world import grassland as G                   # noqa: E402

EPS = 1e-4


def rect_of(fam):
    return G.ground_main_region(fam)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--disc", type=int, default=1)
    ap.add_argument("--out", default=str(Path(__file__).parent / "out"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    fams = sorted(G.GROUNDS)
    rects = {f: rect_of(f) for f in fams}
    print("family mains rects (u0,v0,u1,v1):")
    for f in fams:
        u0, v0, u1, v1 = rects[f]
        print(f"   {f:8s} ({u0:.4f},{v0:.4f})-({u1:.4f},{v1:.4f})  "
              f"size {u1 - u0:.4f} x {v1 - v0:.4f}  topo {G.GROUNDS[f]['topo']}")

    # per-family: collect mains tris and record uvs RELATIVE to the family rect origin
    rel: dict = defaultdict(Counter)
    tris_n: dict = Counter()
    blocks_n: dict = defaultdict(set)
    blocks = X.list_blocks(disc=args.disc)
    for n, (bx, by) in enumerate(blocks):
        bm = X.read_block(bx, by, disc=args.disc)
        uv, tan = bm.uvs, bm.tangents
        for tri in bm.tris:
            us = [uv[i][0] for i in tri]
            vs = [uv[i][1] for i in tri]
            u_lo, u_hi, v_lo, v_hi = min(us), max(us), min(vs), max(vs)
            for f in fams:
                r_u0, r_v0, r_u1, r_v1 = rects[f]
                if (u_lo >= r_u0 - EPS and u_hi <= r_u1 + EPS
                        and v_lo >= r_v0 - EPS and v_hi <= r_v1 + EPS):
                    tris_n[f] += 1
                    blocks_n[f].add((bx, by))
                    key = tuple(sorted((round(uv[i][0] - r_u0, 5),
                                        round(uv[i][1] - r_v0, 5)) for i in tri))
                    rel[f][key] += 1
                    break
        if n % 60 == 0:
            print(f"   ...{n}/{len(blocks)}", flush=True)

    print("\nper-family mains inventory:")
    for f in fams:
        print(f"   {f:8s} {tris_n[f]:>6} tris in {len(blocks_n[f]):>3} blocks, "
              f"{len(rel[f]):>4} distinct relative uv-triangles")

    # THE PRECONDITION: do families share their relative layout?
    print("\nRELATIVE-LAYOUT OVERLAP (share of src's tris whose relative uv-triangle "
          "also occurs in dst):")
    present = [f for f in fams if tris_n[f] >= 50]
    table = {}
    hdr = "            " + "".join(f"{d:>9}" for d in present)
    print(hdr)
    for s in present:
        row = f"   {s:8s} "
        for d in present:
            shared = sum(c for k, c in rel[s].items() if k in rel[d])
            frac = shared / max(1, tris_n[s])
            table[f"{s}->{d}"] = round(frac, 4)
            row += f"{frac:>9.3f}"
        print(row)

    (out / "ground_translation.json").write_text(json.dumps(dict(
        rects={f: [round(x, 6) for x in rects[f]] for f in fams},
        tris={f: tris_n[f] for f in fams},
        blocks={f: len(blocks_n[f]) for f in fams},
        distinct_rel={f: len(rel[f]) for f in fams},
        overlap=table), indent=1), encoding="utf-8")
    print(f"\n-> {out / 'ground_translation.json'}")
    print("\nREAD IT THIS WAY: a HIGH src->dst share means the two families tile their own "
          "rects\nthe same way, so translating src's mains by the rect delta lands on "
          "dst's real texels.\nA LOW share means the translation would be green-but-wrong "
          "for that pair.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
