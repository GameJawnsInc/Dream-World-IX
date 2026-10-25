"""Skeptic of lane chain (K1's S7): S7 takes a whole-map snapshot's bytes from the LIVE folder because its long-lived
files owe no first open. But the first-open cost is not only for files just written: after a Windows Defender
security-intelligence update (event 2000, logged 17:23:57 today) the owner's day-old draft owed it again
(verify_chain_reread: 9.4 s, then 0.22 s), and chain_snap warm run 2 (right after that update) measured S's begin_step
at 12.4 s. In the editor, once a draft exists nothing reads the live folder's world files (the 3D view draws the
draft in its place; stale() only stats), while the 3D view's reload re-reads the draft's disc-1 files after every
change. So a state where the DRAFT is warm and the LIVE folder is cold is ordinary, and there S7 reads the cold side.

This probe emulates that state without touching the install: a scratch "live" folder of fresh copy2 copies of the
install folder's world files (mtimes kept, so the manifest's live-side stat still matches; just written, so cold),
the twin drafts' draft.json "source" pointed at it, every draft file read once (warm). Then:
  base -- unpatched draft.begin_step(all_cells) on twin A;
  S    -- the lane's own prototype (chain_snap.begin_step_s + chain_reads.cell_files_fast) on twin B.
Each pending snapshot is removed after (rmtree, untimed; abort_step would rewrite every file and so
move its stat off the manifest).

    py studies/overworld-editor/perf/verify_chain_s7cold.py [runs]
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_common as CC                                             # noqa: E402
import chain_fuse as CF                                               # noqa: E402
import chain_reads as CR                                              # noqa: E402
import chain_snap as CS                                               # noqa: E402

from ff9mapkit.world import draft as D                                # noqa: E402

K_SINK = 4


def scratch_live(name):
    root = CC.assert_outside_game(CC.OUT / "work" / name)
    if root.exists():
        shutil.rmtree(root)
    src = root / CC.SOURCE_NAME
    for rel, p in D._world_files(CC.SOURCE).items():
        q = src / rel
        q.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, q)                                           # bytes + mtime: the manifest's col 2 still holds
    return src


def point(d, src):
    meta = D.read_meta(d)
    meta["source"] = str(Path(src).resolve())
    D._write_meta(d, meta)


def warm(d):
    for p in Path(d).rglob("*"):
        if p.is_file():
            p.read_bytes()


def drop(d):
    shutil.rmtree(Path(d) / D.HISTORY_DIR / D._PENDING)


def matching(d):
    """How many draft files S7 would take from the live side (both stats match the manifest)."""
    import os
    meta = D.read_meta(d)
    man, src = meta["manifest"], Path(meta["source"])
    n = 0
    for rel, p in D._cell_files(Path(d), D.all_cells()).items():
        rec = man.get(rel)
        if rec is None:
            continue
        s = os.stat(p)
        try:
            ls = os.stat(src / rel)
        except OSError:
            continue
        if s.st_size == rec[1] and s.st_mtime_ns == rec[3] and ls.st_size == rec[1] and ls.st_mtime_ns == rec[2]:
            n += 1
    return n


def main(runs=3):
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": runs, "rows": []}
    for r in range(runs):
        src = scratch_live(f"vs7live{r}")
        a = CF.state_before(K_SINK, f"vs7base{r}")
        b = CF.state_before(K_SINK, f"vs7S{r}")
        for d in (a, b):
            point(d, src)
            warm(d)
        row = {"live_side_matches": matching(b)}
        t = time.perf_counter()
        D.begin_step(a, D.all_cells())
        row["base_begin_s"] = round(time.perf_counter() - t, 3)
        drop(a)
        saved = D._cell_files
        D._cell_files = CR.cell_files_fast
        try:
            t = time.perf_counter()
            CS.begin_step_s(b, D.all_cells())
            row["S_begin_s"] = round(time.perf_counter() - t, 3)
        finally:
            D._cell_files = saved
        drop(b)
        # the same S again, now that its live side has been read once (the state the lane measured)
        D._cell_files = CR.cell_files_fast
        try:
            t = time.perf_counter()
            CS.begin_step_s(b, D.all_cells())
            row["S_begin_again_s"] = round(time.perf_counter() - t, 3)
        finally:
            D._cell_files = saved
        drop(b)
        out["rows"].append(row)
        print(json.dumps(row), flush=True)
    for k in ("base_begin_s", "S_begin_s", "S_begin_again_s"):
        out[k] = CC.stats([row[k] for row in out["rows"]])
        print(k, out[k])
    p = CC.OUT / "verify" / "s7cold.json"
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("->", p)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
