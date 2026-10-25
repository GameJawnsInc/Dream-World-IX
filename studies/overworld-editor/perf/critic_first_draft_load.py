"""critic probe: is the FIRST 3D reload after a draft is made slow because of GIL contention (the gui lane's and its
verifier's attribution of the first Accept's excess) or because it is the first reader of the files ensure_draft just
wrote (the chain lane's first-open cost)? Nothing else runs in this process: no card, no worker, no GIL rival.

    py studies/overworld-editor/perf/critic_first_draft_load.py [reps]

Per rep, in ONE process (stock decode warmed first by a load of the game's stack, so stock is not the variable):
  stack_warm   load_scene(game stack)                      -- warms the env, the mesh index and the decode memo
  stack_again  load_scene(game stack)                      -- the steady stack reload
  ensure_draft (timed)                                     -- a FRESH draft under out/perf/critic/drafts_first/<rep>
  draft_1      load_scene(stack with the draft in place)   -- the first reader of the draft's files
  draft_2      the same again                              -- files now read once
  draft_3      the same again
Also the plain read pass of the draft's disc-1 files after draft_3 (should be warm) for reference.
The draft is byte-identical to its source after ensure_draft, so draft_1..3 draw the same bytes as the stack.
Evidence: out/perf/critic/critic_first_draft_load.json
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402

OUT = C.WT / "studies" / "overworld-editor" / "out" / "perf" / "critic"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    from ff9mapkit.world import draft as D
    from ff9mapkit.world import mesh as M
    from ff9mapkit.world import render as R
    from ff9mapkit.workspace import worldview3d as V
    assert Path(V.__file__).resolve().is_relative_to(C.KIT.resolve())
    cells = tuple((bx, by) for by in range(M.GRID_ROWS) for bx in range(M.GRID_COLS))
    stack = R.game_stack(C.GAME)
    assert stack is not None
    here = C.SOURCE.name

    def site_for(draft):
        roots = [draft if p.name == here else p for p in stack]
        return R.RenderSite(cells=cells, disc=1, game=C.GAME, stack=tuple(roots))

    def t(fn):
        t0 = time.perf_counter()
        r = fn()
        return time.perf_counter() - t0, r

    stack_site = R.RenderSite(cells=cells, disc=1, game=C.GAME, stack=tuple(stack))
    out = {"reps": []}
    base = OUT / "drafts_first"
    if base.exists():
        shutil.rmtree(base)
    w, (ref, _) = t(lambda: V.load_scene(stack_site))
    out["stack_warm_s"] = round(w, 3)
    for k in range(reps):
        rec = {}
        rec["stack_again_s"] = round(t(lambda: V.load_scene(stack_site))[0], 3)
        root = base / str(k)
        rec["ensure_draft_s"] = round(t(lambda: D.ensure_draft(C.SOURCE, game=C.GAME, root=root))[0], 3)
        d = D.draft_path(C.SOURCE, root=root)
        assert d.resolve().is_relative_to(OUT.resolve()), d
        site = site_for(d)
        for i in (1, 2, 3):
            s, (packed, _) = t(lambda: V.load_scene(site))
            rec[f"draft_{i}_s"] = round(s, 3)
        disc1 = [p for p in (d / "StreamingAssets").rglob("*") if p.is_file() and "Disc4" not in str(p)] \
            if (d / "StreamingAssets").exists() else [p for p in d.rglob("*.ff9mesh") if "Disc4" not in str(p)]
        rec["draft_disc1_files"] = len(disc1)
        rec["read_pass_after_s"] = round(t(lambda: [p.read_bytes() for p in disc1])[0], 3)
        print(k, rec)
        out["reps"].append(rec)
    for key in ("stack_again_s", "ensure_draft_s", "draft_1_s", "draft_2_s", "draft_3_s", "read_pass_after_s"):
        v = sorted(r[key] for r in out["reps"])
        out.setdefault("summary", {})[key] = {"min": v[0], "median": v[len(v) // 2], "all": v}
    print(out["summary"])
    p = OUT / "critic_first_draft_load.json"
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("wrote", p)


if __name__ == "__main__":
    main()
