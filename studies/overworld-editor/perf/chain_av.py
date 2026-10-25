"""Lane chain: is the whole-map snapshot's read cost the FIRST OPEN of files just written (an on-access scan), or
the bytes? Reads every world file of a draft three passes in a row, right after it was written, and the install
folder's (written long ago) the same way.

    py studies/overworld-editor/perf/chain_av.py [runs]

Per run: (a) a fresh copy of the gold draft (shutil.copytree, as the probes make them); (b) a fresh draft made by
draft.ensure_draft from the install folder (the editor's own first copy, timed too); (c) the install folder itself
(read only). Each: pass 1, 2, 3 = open + read every non-backup world file (draft._world_files).
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_common as CC                                             # noqa: E402

from ff9mapkit.world import draft as D                                # noqa: E402


def read_all(folder):
    files = D._world_files(Path(folder))
    t = time.perf_counter()
    n = 0
    for p in files.values():
        n += len(p.read_bytes())
    return time.perf_counter() - t, len(files), n


def main(runs=3):
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": runs, "copytree": [], "ensure_draft": [], "install": []}
    for r in range(runs):
        root = CC.fresh_copy(f"av{r}")
        d = D.draft_path(CC.SOURCE, root=root)
        out["copytree"].append([round(read_all(d)[0], 3) for _ in range(3)])
        er = CC.assert_outside_game(CC.OUT / "work" / f"avens{r}")
        if er.exists():
            shutil.rmtree(er)
        t = time.perf_counter()
        d2 = D.ensure_draft(CC.SOURCE, game=CC.GAME, root=er)
        t_ens = time.perf_counter() - t
        passes = [read_all(d2) for _ in range(3)]
        out["ensure_draft"].append({"ensure_draft_s": round(t_ens, 3), "passes": [round(p[0], 3) for p in passes],
                                    "files": passes[0][1], "bytes": passes[0][2]})
        out["install"].append([round(read_all(CC.SOURCE)[0], 3) for _ in range(3)])
        print(r, "copytree passes", out["copytree"][-1], "| ensure_draft", out["ensure_draft"][-1],
              "| install passes", out["install"][-1])
    CC.save("av.json", out)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
