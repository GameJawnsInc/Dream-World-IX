r"""THE REFRESH CENSUS -- does what a VRAM copy writes ever reach the texture the screen samples?

    py -I stale_census.py                  # every corpus container, 6 children -> SCRATCH raster/stale/
    py -I stale_census.py --only 407,38    # a few
    py -I stale_census.py --control        # the falsifier only (ef407, see below)

WHY
---
Memoria decodes a texture page once and keeps the decode until ``PSXTextureMgr.ClearKey`` drops it, and
ClearKey drops only the pages whose ORIGIN column is the write's origin column. An 8bpp page spans two
64-halfword columns and a 15bpp page four, so a write that lands in a page's second (third, fourth)
column changes VRAM and leaves the decode the screen samples exactly as it was. The kit's scroll-blit
lane tells an author who paints a copy's SOURCE that the paint "ALSO appears" in the destination; that
is only true where something refreshes the destination's decode. On ef407 something does -- its other
roll writes column 640 every frame -- and the gain-half cast was seen in game because of it.

``raster.run(track=True)`` stamps every VRAM write (DR_MOVE, LoadImage, MoveImage) and every decode,
and charges each textured read whose triangles sample a texel written AFTER their decode. This script
runs that over the corpus and joins it to ``ff9mapkit.summons.scroll_blit``'s 167 sites:

    READ_FRESH   some key reads what the copy wrote into the destination, and no read of it is stale
    READ_STALE   every read of the destination's copied texels is of a decode older than the copy
    MIXED        both, on different keys or frames
    NOT_READ     nothing reads the destination's copied texels headless -- "not observed", not safe

THE FALSIFIER (``--control``): ef407 with ClearKey suppressed for column 640 only. The census must then
call (704,384) READ_STALE; if it does not, the instrument cannot see the failure it exists to find.

Headless limits apply (``README.md``): actors at the origin, no battle camera, and an opening that can
run 19 frames off the game's. A frame count here is a headless frame count.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
import sfx_host as H                                     # noqa: E402

_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "ff9mapkit"))
from ff9mapkit.summons import scroll_blit as SB           # noqa: E402

assert os.path.normcase(SB.__file__).startswith(os.path.normcase(str(_REPO / "ff9mapkit"))), SB.__file__

OUT = H.OUT_DIR / "raster" / "stale"
CONTROL = (407, 640)                                      # effect, the column whose ClearKey is suppressed


# ============================================================== one container, in its own process
def child(ef: int, out: str, no_clear_column: int = -1) -> int:
    import raster as R
    if no_clear_column >= 0:                              # THE CONTROL: this process only
        real = R.TextureCache.clear_key

        def clear_key(self, x, y):
            if x >> 6 != no_clear_column >> 6:
                real(self, x, y)
        R.TextureCache.clear_key = clear_key
    blob, source, _ = H.load_container(ef, None, False, None)
    bdir, sha = H.resolve_bin(None, None)
    res = R.run(bdir, blob, ef, frames=set(), track=True)
    stale = {k: dict(v, stale_kinds=dict(v["stale_kinds"]), copy_cells=dict(v["copy_cells"]),
                     stale_cells=dict(v["stale_cells"])) for k, v in res["stats"].stale.items()}
    doc = {"effect": ef, "frames": res["frames"], "faults": res["faults"][:20], "plugin_sha256": sha,
           "no_clear_column": no_clear_column, "keys": stale}
    p = H._refuse_repo_path(Path(out))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    return 0


def spawn(ef: int, out: Path, no_clear_column: int = -1) -> dict:
    cmd = [sys.executable, "-I", str(Path(__file__).resolve()), "--child", str(ef), str(out),
           "--no-clear-column", str(no_clear_column)]
    cp = subprocess.run(cmd, capture_output=True, text=True, cwd=str(_HERE))
    if cp.returncode or not out.exists():
        return {"effect": ef, "error": (cp.stdout + cp.stderr)[-600:]}
    return json.loads(out.read_text(encoding="utf-8"))


# ============================================================== the join
def site_verdicts(runs: dict) -> list:
    rows = []
    for ef, bs in sorted(SB.SCROLL_BLITS.items()):
        run = runs.get(ef)
        for b in bs:
            cells = ["x%d_y%d" % c for c in SB.cells_under(b.dst_rect)]
            if run is None or "error" in run:
                rows.append({"effect": ef, "site": b.describe(), "verdict": "NO_RUN", "cells": cells})
                continue
            fresh, stale, readers = Counter(), Counter(), set()
            for key, rec in run["keys"].items():
                for c in cells:
                    n_copy, n_stale = rec["copy_cells"].get(c, 0), rec["stale_cells"].get(c, 0)
                    if n_copy or n_stale:
                        readers.add("%s %s" % (key, rec["page"]))
                    stale[c] += n_stale
                    fresh[c] += max(n_copy - n_stale, 0)
            reads, st = sum(fresh.values()) + sum(stale.values()), sum(stale.values())
            verdict = ("NOT_READ" if reads == 0 else "READ_STALE" if st and not sum(fresh.values())
                       else "MIXED" if st else "READ_FRESH")
            rows.append({"effect": ef, "site": b.describe(), "dst": list(b.dst_rect), "cells": cells,
                         "verdict": verdict, "cell_reads": reads, "stale_cell_reads": st,
                         "readers": sorted(readers)})
    return rows


def other_stale(runs: dict) -> list:
    """Stale reads of LoadImage / MoveImage writes -- outside the scroll-blit table entirely."""
    rows = []
    for ef, run in sorted(runs.items()):
        for key, rec in run.get("keys", {}).items():
            kinds = {k: n for k, n in rec["stale_kinds"].items() if k != "DR_MOVE"}
            if kinds:
                rows.append({"effect": ef, "key": key, "page": rec["page"], "kinds": kinds,
                             "frames": rec["stale_frames"], "cells": rec["stale_cells"]})
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", help="comma-separated effect ids (default: every corpus container)")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--control", action="store_true", help="run the falsifier only")
    ap.add_argument("--rejoin", action="store_true",
                    help="re-join the SAVED runs to the current scroll-blit table (no plugin run): the "
                         "tracker stamps every DR_MOVE whatever issued it, so a table that gains rows "
                         "needs no new run")
    ap.add_argument("--child", nargs=2, metavar=("EF", "OUT"), help=argparse.SUPPRESS)
    ap.add_argument("--no-clear-column", type=int, default=-1, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if a.child:
        return child(int(a.child[0]), a.child[1], a.no_clear_column)
    out = H._refuse_repo_path(OUT)
    out.mkdir(parents=True, exist_ok=True)

    ef, col = CONTROL
    if a.rejoin:
        ctrl = json.loads((out / "control" / ("ef%03d.json" % ef)).read_text(encoding="utf-8"))
    else:
        ctrl = spawn(ef, out / "control" / ("ef%03d.json" % ef), col)
    cv = {r["site"]: r["verdict"] for r in site_verdicts({ef: ctrl}) if r["effect"] == ef}
    print("CONTROL ef%03d, ClearKey suppressed on column %d:" % (ef, col))
    for site, v in cv.items():
        print("   %-12s %s" % (v, site))
    if a.control:
        return 0

    ids = [int(x) for x in a.only.split(",")] if a.only else H.corpus_ids()
    if a.rejoin:
        got = [json.loads((out / "runs" / ("ef%03d.json" % e)).read_text(encoding="utf-8"))
               for e in ids]
    else:
        with ThreadPoolExecutor(a.jobs) as pool:
            got = list(pool.map(lambda e: spawn(e, out / "runs" / ("ef%03d.json" % e)), ids))
    runs = {r["effect"]: r for r in got}
    errs = [r["effect"] for r in got if "error" in r]
    sites = site_verdicts(runs)
    others = other_stale(runs)
    doc = {"containers": len(ids), "errors": errs, "control": cv, "sites": sites, "other_stale": others,
           "verdicts": dict(Counter(r["verdict"] for r in sites))}
    (out / "stale.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    with open(out / "sites.tsv", "w", encoding="utf-8") as fh:
        fh.write("effect\tverdict\tcell_reads\tstale_cell_reads\tsite\treaders\n")
        for r in sites:
            fh.write("ef%03d\t%s\t%s\t%s\t%s\t%s\n" % (r["effect"], r["verdict"], r.get("cell_reads", ""),
                                                       r.get("stale_cell_reads", ""), r["site"],
                                                       "; ".join(r.get("readers", []))))
    print("\nrefresh census: %d containers, %d errors -> %s" % (len(ids), len(errs), out))
    print("   scroll-blit rect pairs: %s" % dict(Counter(r["verdict"] for r in sites)))
    for r in sites:
        if r["verdict"] in ("READ_STALE", "MIXED"):
            print("   %-10s ef%03d %s  (%d of %d cell reads stale)  %s" % (
                r["verdict"], r["effect"], r["site"], r["stale_cell_reads"], r["cell_reads"],
                "; ".join(r["readers"])))
    print("   stale reads of LoadImage/MoveImage writes: %d (effect, key) pairs" % len(others))
    return 0


if __name__ == "__main__":
    sys.exit(main())
