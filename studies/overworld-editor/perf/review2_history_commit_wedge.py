"""Review-2 probe (history slice, f8ca4c76): commit_step rewrites pending/step.json WITHOUT its "stat"/"at" and deletes
the before-copies of the cells the step did not change, and only then renames pending into history/<n>. A commit
that fails at that rename (not retried: a handle open inside pending -- a scanner, an indexer -- or a history/<n>
the rmtree(ignore_errors) above it could not clear) leaves that rewritten pending. begin_step and begin_edit now
abort a pending step first; that abort trusts no stat (stat missing), so it reads a before-copy for EVERY file and
hits one that commit deleted: FileNotFoundError, every time -- after writing back the sorted files before it.

Hermetic: fake game + drafts under studies/overworld-editor/out/perf/review2/history/commit_wedge/. The real
draft.py (worktree package asserted); the failing rename is a real Windows refusal (a read handle held on a file in
pending/after while the commit runs, released right after)."""
from __future__ import annotations

import shutil
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve()
WT = HERE.parents[3]
sys.path.insert(0, str(WT / "ff9mapkit"))
from ff9mapkit.world import draft as D  # noqa: E402

assert Path(D.__file__).resolve().is_relative_to(WT), D.__file__
OUT = WT / "studies" / "overworld-editor" / "out" / "perf" / "review2" / "history" / "commit_wedge"
T00 = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Terrain.ff9mesh"
T10 = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[1][0] Terrain.ff9mesh"
ROW = {"table": "forest", "center": [1.0, -1.0], "donor": "15,15"}


def setup():
    if OUT.exists():
        shutil.rmtree(OUT)
    game = OUT / "GAME"
    src = game / "FF9CustomMap-world"
    for disc in (1, 4):
        row = src / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / "r0"
        row.mkdir(parents=True)
        for bx in range(3):
            (row / f"Block[{bx}][0] Terrain.ff9mesh").write_bytes(b"stock %d" % bx)
    return D.ensure_draft(src, game=game, root=OUT / "drafts")


def main():
    d = setup()
    pend = d / D.HISTORY_DIR / D._PENDING
    # a card's Accept: a superset snapshot (blocks 0..2); the verb writes block (1,0) only
    D.begin_step(d, [(0, 0), (1, 0), (2, 0)])
    (d / T10).write_bytes(b"a forest")
    # an outside reader opens the after-copy commit_step writes, while it runs (held until the commit returns)
    held = []
    real_snap = D._snap

    def snap(draft, cells, dest, files=None):
        out = real_snap(draft, cells, dest, files)
        if dest.name == "after":
            held.extend(open(p, "rb") for p in dest.rglob("*.ff9mesh"))
        return out
    D._snap = snap
    try:
        D.commit_step(d, ROW, "forest one")
        print("commit went through (unexpected)")
    except OSError as e:
        print("commit failed at the rename:", type(e).__name__, e)
    finally:
        D._snap = real_snap
        for f in held:
            f.close()
    print("pending left:", pend.is_dir(), "| step.json keys:",
          sorted(__import__("json").loads((pend / "step.json").read_text())))
    print("before-copies left:", sorted(p.name for p in (pend / "before").rglob("*.ff9mesh")))
    for attempt in range(3):
        try:
            D.begin_step(d, [(2, 0)])
            print(f"begin_step #{attempt + 1}: ok")
        except OSError as e:
            print(f"begin_step #{attempt + 1}: {type(e).__name__}: {e}")
    try:
        D.begin_edit(d, 0)
    except Exception as e:                                    # noqa: BLE001
        print("begin_edit:", type(e).__name__, "(the bar's _open_edit/_run_delete catch ValueError only)")
    print("block (1,0) now:", (d / T10).read_bytes(), "| history cursor", D.history(d)["cursor"])


if __name__ == "__main__":
    main()
