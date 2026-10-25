"""Lane chain: the recipe bar's Open... (RecipeBar.open_recipe) of the gold's own 5-row recipe over an existing draft:
discard, ensure_draft, then one world-fuse job per row, each row its own step -- every draft call timed by thread.

    py studies/overworld-editor/perf/chain_open.py [runs]

Per run: a fresh copy of the gold (the draft the user has), the bar + four cards wired as WorldDoc wires them, the
bar's file-dialog seam returning the recipe. The composed draft's world files are compared with the gold's (the C3
acceptance: the recipe composes the bytes the cards wrote).
"""
from __future__ import annotations

import hashlib
import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_common as CC                                             # noqa: E402
import chain_ops as CO                                                # noqa: E402

from ff9mapkit.world import draft as D                                # noqa: E402
from ff9mapkit.world import recipe as RC                              # noqa: E402


def world(d):
    return {p.relative_to(d).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (Path(d) / "FF9_Data" / "WorldMap").rglob("Block*")
            if ".bak-" not in p.name and p.suffix in (".ff9mesh", ".txt")}


def main(runs=2):
    import chain_build as CB
    gold = D.draft_path(CC.SOURCE, root=CC.GOLD)
    recipe = CC.OUT / "gold_recipe.toml"
    recipe.write_text(RC.dumps(D.recipe_rows(gold), base=CC.SOURCE_NAME), encoding="utf-8")
    gold_world = world(gold)
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": runs, "rows": []}
    calls = CC.Calls(D, CO.NAMES)
    for r in range(runs):
        root = CC.fresh_copy(f"open{r}")
        base = threading.active_count()
        lab = CB.Lab(root)
        for t in lab.tools.values():
            t.open_tool()
            lab.pump(lambda: threading.active_count() <= base, 120)
            t.close_tool()
        lab.pump(lambda: threading.active_count() <= base, 120)
        lab.bar._open_path_fn = lambda: str(recipe)
        n0, m0 = len(lab.argvs), calls.mark()
        t0 = time.perf_counter()
        lab.bar.open_btn.click()
        slot = time.perf_counter() - t0
        slot_calls = calls.summary(m0)
        lp = lab.pump(lambda: lab.bar._queue is None and threading.active_count() <= base, 3600)
        total = time.perf_counter() - t0
        g, w = CO._gui_cost(calls, m0)
        d = lab.bar.draft()
        rows = D.recipe_rows(d)
        same = world(d) == gold_world
        gui_calls = [{"fn": x["fn"], "s": round(x["s"], 3)} for x in calls.rows[m0:] if x["gui"] and x["depth"] == 0
                     and x["fn"] in ("discard", "ensure_draft", "begin_step", "commit_step")]
        row = {"slot_s": round(slot, 3), "total_s": round(total, 2), "loop": lp, "gui_draft_s": g,
               "worker_draft_s": w, "gui_steps": gui_calls,
               "jobs": [{"verb": a["argv"][5], "s": round(a.get("s", -1), 2)} for a in lab.argvs[n0:]],
               "status": lab.bar.status_lbl.text(), "rows_equal_gold": rows == D.recipe_rows(gold),
               "world_equal_gold": same, "slot_calls": {k: v for k, v in slot_calls.items() if "|d0" in k},
               "calls": {k: v for k, v in calls.summary(m0).items() if "|d0" in k}}
        out["rows"].append(row)
        print(json.dumps({k: row[k] for k in ("slot_s", "total_s", "gui_draft_s", "gui_steps", "jobs",
                                               "world_equal_gold", "status")}))
        print("   loop", lp)
        for t in lab.tools.values():
            t.close_tool()
    calls.restore()
    for k in ("slot_s", "total_s", "gui_draft_s"):
        out[k] = CC.stats([row[k] for row in out["rows"]])
    CC.save("open.json", out)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2)
