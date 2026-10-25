"""Lane chain: Promote and Revert (draft.promote / draft.revert), NEVER against the real install's bytes.

    py studies/overworld-editor/perf/chain_promote.py dry [runs]         # promote(dry_run=True) on the REAL install
                                                                        # folder: read-only, proven by a stat
                                                                        # snapshot of every file there, before/after
    py studies/overworld-editor/perf/chain_promote.py scratch [runs]     # promote + revert into a SCRATCH game root
                                                                        # of COPIES, one fresh child process per run

THE SCRATCH GAME ROOT: OUT/work/promote<r>/game/FF9CustomMap-world holds byte COPIES (shutil.copy2: data and mtime,
never a link or junction) of the live folder's world files and ledger; the gold draft is copied beside it and its
draft.json's "source" pointed there. Two child modes:
  nomirror  -- as is: the scratch root has no StreamingAssets, so the disc-4 mirror logs NOT RUN (what a promote
               costs without it);
  mirror    -- the stock READS (world.extract._streaming_assets) pointed at the real install's StreamingAssets, the
               writes still at the scratch root (mirror() resolves its write root from game=<scratch>): the real
               mirror on the promoted cells. Before the patch the bundle hint is checked valid for discs 1 and 4, so
               _worldmap_env takes the hint branch and writes nothing there; every resolved game root is logged.
Each child: promote, then revert; the scratch world files after the revert == before the promote (sha).
After every child, the real install folder's stat snapshot (every file, backups and ledger included) is compared.
"""
from __future__ import annotations

import cProfile
import hashlib
import io
import json
import os
import pstats
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_common as CC                                             # noqa: E402

from ff9mapkit.world import draft as D                                # noqa: E402


def install_snapshot():
    """(rel, size, mtime_ns) of EVERY file under the live folder (read only)."""
    out = []
    for dirpath, _dirs, files in os.walk(CC.SOURCE):
        for f in files:
            p = os.path.join(dirpath, f)
            s = os.stat(p)
            out.append((os.path.relpath(p, CC.SOURCE), s.st_size, s.st_mtime_ns))
    return sorted(out)


def dry(runs=3):
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": runs}
    root = CC.fresh_copy("promotedry")
    d = D.draft_path(CC.SOURCE, root=root)
    before = install_snapshot()
    ts, plan = [], None
    for _ in range(runs):
        t = time.perf_counter()
        plan = D.promote(d, game=CC.GAME, dry_run=True, log=lambda *_a: None)
        ts.append(time.perf_counter() - t)
    pr = cProfile.Profile()
    pr.enable()
    D.promote(d, game=CC.GAME, dry_run=True, log=lambda *_a: None)
    pr.disable()
    pr.dump_stats(str(CC.OUT / "promote_dry.pstats"))
    s = io.StringIO()
    pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(22)
    after = install_snapshot()
    out.update(wall=CC.stats(ts), plan={k: (len(v) if isinstance(v, list) else v) for k, v in plan.items()},
               install_unchanged=before == after, install_files=len(before), profile=s.getvalue())
    print("promote dry_run", out["wall"], "install unchanged:", out["install_unchanged"], len(before), "files")
    CC.save("promote_dry.json", out)


def _scratch(name):
    root = CC.assert_outside_game(CC.OUT / "work" / name)
    if root.exists():
        shutil.rmtree(root)
    game = root / "game"
    src = game / CC.SOURCE_NAME
    t = time.perf_counter()
    for rel, p in D._world_files(CC.SOURCE).items():
        dst = src / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst)                                           # a byte copy, never a link
    shutil.copy2(CC.SOURCE / D.LEDGER, src / D.LEDGER)
    drafts = root / "drafts"
    shutil.copytree(CC.GOLD, drafts)
    d = D.draft_path(CC.SOURCE, root=drafts)
    meta = D.read_meta(d)
    meta["source"] = str(src.resolve())
    D._write_meta(d, meta)
    for p in src.rglob("*"):
        assert not p.is_symlink(), p
    return game, src, d, round(time.perf_counter() - t, 2)


def _world(folder):
    return {rel: D._sha(p) for rel, p in D._world_files(Path(folder)).items()}


def child(mode, r, prof=False):
    from ff9mapkit import config
    from ff9mapkit.world import discmirror as DM
    from ff9mapkit.world import extract as X
    from ff9mapkit.world import mesh as M
    game, src, d, t_copy = _scratch(f"promote{mode}{r}")
    roots = []
    real_find = config.find_game_path

    def find(explicit=None):
        g = real_find(explicit)
        roots.append(str(g))
        # the guard: no call in a scratch promote may resolve the real install (a write root there would be live)
        assert Path(g).resolve() != CC.GAME.resolve(), f"find_game_path({explicit!r}) resolved the real install"
        return g
    config.find_game_path = find
    if mode == "mirror":
        sa = CC.GAME / "StreamingAssets"
        hint = json.loads((sa / X._WM_BUNDLE_HINT).read_text(encoding="utf-8"))
        assert hint.get("1") and hint.get("4") and all((sa / hint[k]).is_file() for k in ("1", "4")), hint
        X._streaming_assets = lambda game=None: sa                     # stock reads only; writes stay at game=
    stale = D.stale(d)
    pre = _world(src)
    logs = []
    calls = CC.Calls(D, ["edits", "removals", "_ledger_last", "_ledger_tags", "_cell_files", "_write_live",
                         "_unlink_live", "_rebase", "_take_ledger", "stale", "_mark_promoted"])
    calls_m = CC.Calls(M, ["read_ledger", "park_backup", "record_ledger_write"])
    calls_dm = CC.Calls(DM, ["auto_mirror", "mirror"])
    pr = cProfile.Profile() if prof else None
    if pr:
        pr.enable()
    t = time.perf_counter()
    rec = D.promote(d, game=game, log=logs.append)
    t_p = time.perf_counter() - t
    if pr:
        pr.disable()
        pr.dump_stats(str(CC.OUT / f"promote_{mode}.pstats"))
    m_p = (calls.summary(), calls_m.summary(), calls_dm.summary())
    k0, k1, k2 = calls.mark(), calls_m.mark(), calls_dm.mark()
    mid = _world(src)
    pr2 = cProfile.Profile() if prof else None
    if pr2:
        pr2.enable()
    t = time.perf_counter()
    D.revert(d, game=game, log=logs.append)
    t_r = time.perf_counter() - t
    if pr2:
        pr2.disable()
        pr2.dump_stats(str(CC.OUT / f"revert_{mode}.pstats"))
    post = _world(src)
    out = {"mode": mode, "run": r, "scratch_copy_s": t_copy, "stale_before": len(stale),
           "promote_s": round(t_p, 3), "revert_s": round(t_r, 3), "promoted": len(rec["promoted"]),
           "cells": len(rec["cells"]), "changed_files": len(set(rec["before"]) | set(rec["after"])),
           "promote_changed_world": pre != mid, "revert_exact": pre == post,
           "mirror_lines": [ln for ln in logs if not ln.startswith(("promoted ->", "removed ->", "restored ->",
                                                                       "relabelled ->"))][:12],
           "game_roots_resolved": sorted(set(roots)),
           "calls_promote": m_p, "calls_revert": (calls.summary(k0), calls_m.summary(k1), calls_dm.summary(k2))}
    print(json.dumps(out, default=str))


def scratch(runs=3):
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": runs, "children": []}
    before = install_snapshot()
    for mode in ("nomirror", "mirror"):
        for r in range(runs + 1):
            prof = r == runs                                              # the last run profiled (not in the wall)
            t = time.perf_counter()
            p = subprocess.run([sys.executable, str(Path(__file__).resolve()), "child", mode, str(r)]
                               + (["prof"] if prof else []), capture_output=True, text=True, timeout=3600)
            wall = time.perf_counter() - t
            assert p.returncode == 0, (mode, r, p.stdout[-2000:], p.stderr[-3000:])
            rec = json.loads(p.stdout.strip().splitlines()[-1])
            rec["child_process_wall_s"] = round(wall, 2)
            rec["profiled"] = prof
            out["children"].append(rec)
            print(mode, r, {k: rec[k] for k in ("promote_s", "revert_s", "revert_exact", "promote_changed_world",
                                                "scratch_copy_s", "child_process_wall_s", "game_roots_resolved",
                                                "mirror_lines")})
            after = install_snapshot()
            assert after == before, "the install folder changed!"
    out["install_unchanged"] = install_snapshot() == before
    for mode in ("nomirror", "mirror"):
        rows = [c for c in out["children"] if c["mode"] == mode and not c["profiled"]]
        out[f"{mode}_promote"] = CC.stats([c["promote_s"] for c in rows])
        out[f"{mode}_revert"] = CC.stats([c["revert_s"] for c in rows])
    for name in ("promote_nomirror", "revert_nomirror", "promote_mirror", "revert_mirror"):
        pf = CC.OUT / f"{name}.pstats"
        if pf.is_file():
            s = io.StringIO()
            pstats.Stats(str(pf), stream=s).sort_stats("cumulative").print_stats(28)
            out[f"profile {name}"] = s.getvalue()
    CC.save("promote_scratch.json", out)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry"
    if mode == "dry":
        dry(int(sys.argv[2]) if len(sys.argv) > 2 else 3)
    elif mode == "scratch":
        scratch(int(sys.argv[2]) if len(sys.argv) > 2 else 3)
    elif mode == "child":
        child(sys.argv[2], int(sys.argv[3]), prof=len(sys.argv) > 4)
