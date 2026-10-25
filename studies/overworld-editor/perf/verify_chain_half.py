"""Skeptic of lane chain (K1 / op_begin_step_all): the whole-map begin_step's first-open debt in the state the REAL
editor leaves a draft in. The cards and the recipe bar exist only on the 3D page (WorldDoc._open_carry turns the 3D view
on; the bar is built by _on_view3d), and every draft change reloads the 3D view (WorldDoc._draft_changed ->
_load_view3d), whose worker reads every DISC-1 file of the draft (RenderSite disc=1, the draft in the stack). So by
the time of a later whole-map step, the disc-1 half of the draft has been read and only disc 4 can still owe its first
open. This probe measures begin_step(all_cells) and commit_step (no job between: nothing changed) on twin copies at
the state before the sink step, in three states:

  debt  -- a fresh copy, nothing read (what chain_snap 'debt' measures; also the first Accept on a brand-new draft,
           and Open...'s first whole-map row);
  half  -- a fresh copy whose Disc1 files were read once (what the 3D view's reload leaves);
  warm  -- every world file read once.

    py studies/overworld-editor/perf/verify_chain_half.py [runs]

Unpatched module code only. Writes only under OUT/work (fresh copies).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_common as CC                                             # noqa: E402
import chain_fuse as CF                                               # noqa: E402

from ff9mapkit.world import draft as D                                # noqa: E402

K_SINK = 4


def read_tree(d, discs):
    n = 0
    t = time.perf_counter()
    for rel, p in D._world_files(Path(d)).items():
        if any(f"/Disc{k}/" in "/" + rel for k in discs):
            p.read_bytes()
            n += 1
    return n, round(time.perf_counter() - t, 3)


def main(runs=3):
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": runs, "rows": []}
    for r in range(runs):
        row = {}
        for state in ("debt", "half", "warm"):
            d = CF.state_before(K_SINK, f"vhalf{state}{r}")
            pre = None
            if state == "half":
                pre = read_tree(d, (1,))
            elif state == "warm":
                pre = read_tree(d, (1, 4))
            t = time.perf_counter()
            D.begin_step(d, D.all_cells())
            b = time.perf_counter() - t
            t = time.perf_counter()
            D.commit_step(d, dict(CF.GOLD_STEPS[K_SINK]["row"]), "noop")
            c = time.perf_counter() - t
            D.undo(d) if D.history(d)["cursor"] > K_SINK else None
            row[state] = {"pre_read": pre, "begin_step_s": round(b, 3), "commit_step_s": round(c, 3)}
        out["rows"].append(row)
        print(json.dumps(row), flush=True)
    for state in ("debt", "half", "warm"):
        for k in ("begin_step_s", "commit_step_s"):
            out[f"{state} {k}"] = CC.stats([row[state][k] for row in out["rows"]])
        print(state, out[f"{state} begin_step_s"], out[f"{state} commit_step_s"])
    p = CC.OUT / "verify" / "half.json"
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("->", p)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
