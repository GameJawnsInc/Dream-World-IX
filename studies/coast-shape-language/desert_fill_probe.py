"""THE TILED-MAINS FILL, pre-build measurement (DESERT-FILL-PREDICTION.md D-5 + design
inputs): for each mural-refused candidate window --

  1. TOP COMPOSITION -- which non-cliff topos actually sit behind the window's crease
     (the tris the drop set would consume).
  2. TILE LANGUAGE -- uv-rect census of those topos over the mass rect: distinct rects,
     reuse fraction (the mural discriminant the build will gate on).
  3. THE WALL U CYCLE -- do the window's clean gaps quantize into the grass CYC's
     4-phase ramp, a DIFFERENT 4-phase ramp, or not at all (D-5).

Read-only; prints a table.  Run from the repo root:  py studies/coast-shape-language/desert_fill_probe.py
"""
from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import coastscan as CS            # noqa: E402
from ff9mapkit.world import coastmorph as CM           # noqa: E402
from ff9mapkit.world.extract import decode_id          # noqa: E402

#: (label, mass donor, mass size, window block, window L)
CANDIDATES = [
    ("comma",    (9, 5),   (2, 3), (10, 5),  97.7),
    ("comma",    (9, 5),   (2, 3), (9, 6),   47.8),
    ("comma",    (9, 5),   (2, 3), (10, 6), 100.0),
    ("comma",    (9, 5),   (2, 3), (9, 7),   66.0),
    ("isthmus",  (6, 6),   (2, 2), (6, 6),   79.8),
    ("isthmus",  (6, 6),   (2, 2), (7, 6),  117.3),
    ("isthmus",  (6, 6),   (2, 2), (6, 7),  112.6),
    ("isthmus",  (6, 6),   (2, 2), (7, 7),   45.4),
    ("crescent", (14, 1),  (4, 2), (15, 1),  65.7),
    ("crescent", (14, 1),  (4, 2), (16, 1),  68.7),
    ("grass-REF", (7, 17), (4, 2), (7, 17),  72.5),
]
CYC = (0.8242, 0.7617, 0.6992, 0.8867)


def uv_rect(t3):
    us = [v[2][0] for v in t3]
    vs = [v[2][1] for v in t3]
    return (round(min(us), 3), round(max(us), 3), round(min(vs), 3), round(max(vs), 3))


def canon_u(vals, cyc):
    for u in vals:
        for u2 in (u, u - 0.25, u + 0.25):
            for c in cyc:
                if abs(u2 - c) < 0.004:
                    return c
    return None


def main() -> int:
    for label, donor, size, block, want_l in CANDIDATES:
        wins = [w for w in CS.scan_block(*block, disc=1) if w["kind"] == "cliff"
                and abs(w["L"] - want_l) < 0.5]
        if not wins:
            print(f"== {label} {block} L~{want_l}: WINDOW NOT FOUND")
            continue
        w = wins[0]
        try:
            win = CM.CliffWindow(donor, w["start"], w["end"], size=size, disc=1)
        except ValueError as e:
            print(f"== {label} {block} L~{want_l}: CliffWindow refused: {e}")
            continue
        topo = lambda t3: decode_id(int(round(t3[0][3][0])))["topograph"]

        # 1. top composition behind the crease (interior crease keys, like the drop set)
        ck = [CM._pk(p) for p in win.crease_chain]
        moved = set(ck[1:-1])
        behind = Counter(topo(t3) for t3 in win.terr
                        if topo(t3) != 58 and CM._key_set(t3) & moved)

        # 2. tile language per behind-topo over the mass rect
        langs = []
        for tp in sorted(behind):
            tris = [t3 for t3 in win.terr if topo(t3) == tp]
            cnt = Counter(uv_rect(t3) for t3 in tris)
            reused = sum(c for c in cnt.values() if c >= 3)
            langs.append(f"topo{tp}: {len(tris)}tris/{len(cnt)}rects/"
                         f"{100 * reused // max(len(tris), 1)}%reuse")

        # 3. the wall U cycle over clean gaps
        raw_us, hits = [], 0
        clean = 0
        for qi, quads in enumerate(win.quads):
            if len(quads) != 2:
                continue
            clean += 1
            us = sorted({round(v[2][0], 4) for t3 in quads for v in t3})
            raw_us.append(us)
            if canon_u(us, CYC) is not None:
                hits += 1
        flat = sorted({u for us in raw_us for u in us})
        print(f"== {label} {block} L={w['L']:.1f} gaps={len(win.quads)} clean={clean}")
        print(f"   behind-crease topos: {dict(behind)}")
        for s in langs:
            print(f"   {s}")
        print(f"   wall: {hits}/{clean} clean gaps match grass CYC; distinct U values: "
              f"{flat[:12]}{'...' if len(flat) > 12 else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
