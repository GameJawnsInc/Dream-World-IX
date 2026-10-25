"""Lane chain: the recipe's history operations on fresh copies of the 5-step gold draft.

    py studies/overworld-editor/perf/chain_ops.py module [runs]   # draft.undo/redo/begin_edit/cancel_edit/replay,
                                                                  # begin_step+commit_step over all_cells, the
                                                                  # P3 prototype (one listing per r-dir) == unpatched
    py studies/overworld-editor/perf/chain_ops.py gui [runs]      # the REAL RecipeBar + cards: Undo, Redo, Delete H
                                                                  # (H2 re-runs by world-fuse, I/T/S replay), Edit H;
                                                                  # every draft call counted by thread

Each run works on its own copy under OUT/work/ (copy2: mtimes kept). The headline is the min (three other lanes run
on this machine); the median is beside it.
"""
from __future__ import annotations

import cProfile
import hashlib
import io
import json
import math
import pstats
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_common as CC                                             # noqa: E402

from ff9mapkit.world import draft as D                                # noqa: E402
from ff9mapkit.world import recipe as RC                              # noqa: E402

SOURCE = CC.SOURCE


def _draft(root):
    d = D.draft_path(SOURCE, root=root)
    assert D.read_meta(d) is not None, d
    return d


def _tree(d: Path) -> dict:
    """rel -> sha of every file under draft ``d`` (history snapshots included), with history.json's utc stamps out."""
    out = {}
    for p in sorted(Path(d).rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(d).as_posix()
        if rel == D.HISTORY:
            h = json.loads(p.read_text(encoding="utf-8"))
            for s in h.get("steps", []):
                s.pop("utc", None)
            out[rel] = json.dumps(h, sort_keys=True)
            continue
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _prof(fn, path):
    pr = cProfile.Profile()
    pr.enable()
    fn()
    pr.disable()
    pr.dump_stats(str(path))
    s = io.StringIO()
    pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(18)
    return s.getvalue()


def _warm(root):
    """Read every file once: a long session has opened them since they were written (chain_av: the first open of
    a file just written costs ~5 ms, a later one ~0.1 ms)."""
    for p in Path(root).rglob("*"):
        if p.is_file():
            p.read_bytes()


def module(runs=3, warm=False):
    import chain_reads as CR
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": runs, "warm": warm}
    labels = [s["label"] for s in D.history(_draft(CC.GOLD))["steps"]]
    out["steps"] = [{"label": s["label"], "cells": len(s["cells"]), "before": len(s["before"]),
                     "after": len(s["after"])} for s in D.history(_draft(CC.GOLD))["steps"]]
    undo_t, redo_t = {lb: [] for lb in labels}, {lb: [] for lb in labels}
    be_t, ce_t, rp_t, rw_t, fin_t = [], [], {}, {}, []
    for r in range(runs):
        root = CC.fresh_copy(f"ops{r}")
        if warm:
            _warm(root)
        d = _draft(root)
        for _ in labels:                                              # undo all five, top first
            t = time.perf_counter()
            s = D.undo(d)
            undo_t[s["label"]].append(time.perf_counter() - t)
        for _ in labels:
            t = time.perf_counter()
            s = D.redo(d)
            redo_t[s["label"]].append(time.perf_counter() - t)
        t = time.perf_counter()
        D.begin_edit(d, 0)                                            # undo all five, lift them
        be_t.append(time.perf_counter() - t)
        t = time.perf_counter()
        D.cancel_edit(d)                                              # redo all five
        ce_t.append(time.perf_counter() - t)
        e = D.begin_edit(d, 2)                                        # lift I, T, S; put each back by replay
        for s in e["lifted"]:
            t = time.perf_counter()
            win = RC.replay_window(s)
            rw_t.setdefault(s["label"], []).append(time.perf_counter() - t)
            t = time.perf_counter()
            ok = D.replay(d, s)
            rp_t.setdefault(s["label"], []).append(time.perf_counter() - t)
            assert ok and win, s["label"]
        t = time.perf_counter()
        D.finish_edit(d)
        fin_t.append(time.perf_counter() - t)
    out["undo"] = {lb: CC.stats(v) for lb, v in undo_t.items()}
    out["redo"] = {lb: CC.stats(v) for lb, v in redo_t.items()}
    out["begin_edit(0) [5 undos]"] = CC.stats(be_t)
    out["cancel_edit [5 redos]"] = CC.stats(ce_t)
    out["replay_window"] = {lb: CC.stats(v) for lb, v in rw_t.items()}
    out["replay"] = {lb: CC.stats(v) for lb, v in rp_t.items()}
    out["finish_edit"] = CC.stats(fin_t)
    # the whole-map step snapshot: begin_step(all_cells) + commit_step with nothing written between (what a put-back
    # re-run or an opened recipe pays on the GUI thread for an island/carry/sink/morph/river row, plus the job)
    bs, cs = [], []
    for r in range(runs):
        root = CC.fresh_copy(f"snap{r}")
        if warm:
            _warm(root)
        d = _draft(root)
        t = time.perf_counter()
        D.begin_step(d, D.all_cells())
        bs.append(time.perf_counter() - t)
        t = time.perf_counter()
        D.commit_step(d, {"table": "probe"}, "probe")
        cs.append(time.perf_counter() - t)
    out["begin_step(all_cells)"] = CC.stats(bs)
    out["commit_step(all_cells, nothing changed)"] = CC.stats(cs)
    d = _draft(CC.fresh_copy("snapprof"))
    out["profile begin_step(all_cells)"] = _prof(lambda: D.begin_step(d, D.all_cells()),
                                                 CC.OUT / "begin_step_all.pstats")
    out["profile commit_step(all_cells)"] = _prof(lambda: D.commit_step(d, {"table": "probe"}, "probe"),
                                                  CC.OUT / "commit_step_all.pstats")
    # P3 in place of D._cell_files (one listing per r-directory): the same operations on twin copies, compared over
    # every file of the draft (history snapshots and history.json included, utc stamps out)
    real = D._cell_files
    pa, pb = [], []
    ident = []
    for r in range(runs):
        da, db = _draft(CC.fresh_copy(f"p3a{r}")), _draft(CC.fresh_copy(f"p3b{r}"))
        t = time.perf_counter()
        D.begin_step(da, D.all_cells())
        D.commit_step(da, {"table": "probe"}, "probe")
        D.undo(da)
        D.undo(da)
        D.redo(da)
        pa.append(time.perf_counter() - t)
        D._cell_files = CR.cell_files_fast
        try:
            t = time.perf_counter()
            D.begin_step(db, D.all_cells())
            D.commit_step(db, {"table": "probe"}, "probe")
            D.undo(db)
            D.undo(db)
            D.redo(db)
            pb.append(time.perf_counter() - t)
        finally:
            D._cell_files = real
        ta, tb = _tree(da), _tree(db)
        ident.append({"identical": ta == tb, "files": len(ta),
                      "differ": sorted(k for k in set(ta) | set(tb) if ta.get(k) != tb.get(k))[:8]})
    out["P3 begin+commit(all)+undo+undo+redo: unpatched"] = CC.stats(pa)
    out["P3 begin+commit(all)+undo+undo+redo: patched"] = CC.stats(pb)
    out["P3 identity"] = ident
    # the undo of the sink step, profiled (the largest step)
    d = _draft(CC.fresh_copy("undoprof"))
    out["profile undo(sink)"] = _prof(lambda: D.undo(d), CC.OUT / "undo_sink.pstats")
    out["profile begin_edit(0)"] = _prof(lambda: D.begin_edit(d, 0), CC.OUT / "begin_edit0.pstats")
    CC.save("ops_module_warm.json" if warm else "ops_module.json", out)
    for k, v in out.items():
        if isinstance(v, dict) and "min" in v:
            print(f"{k:55s} min {v['min']:.3f} median {v['median']:.3f}")
        elif isinstance(v, dict) and k in ("undo", "redo", "replay", "replay_window"):
            for lb, s in v.items():
                print(f"{k:8s} {lb:47s} min {s['min']:.3f} median {s['median']:.3f}")
    print("P3 identity", ident)


# ---------------------------------------------------------------- the real bar
NAMES = ["read_meta", "history", "edits", "removals", "stale", "edited_blocks", "last_promote", "promotes",
         "promote_owed", "_world_files", "_cell_files", "_sha", "undo", "redo", "begin_step", "commit_step",
         "abort_step", "replay", "begin_edit", "finish_edit", "cancel_edit", "recipe_rows", "_restore", "_snap",
         "_differs", "_put_ledger", "_keep_ledger", "_write_history", "ensure_draft", "discard"]


def _gui_cost(calls, m0):
    """GUI-thread seconds inside the draft module's outermost calls since mark ``m0``, and the worker's."""
    gui = sum(r["s"] for r in calls.rows[m0:] if r["gui"] and r["depth"] == 0)
    wrk = sum(r["s"] for r in calls.rows[m0:] if not r["gui"] and r["depth"] == 0)
    return round(gui, 4), round(wrk, 4)


def gui(runs=3, warm=False):
    import chain_build as CB
    from ff9mapkit.world import hilledit as HE
    build = json.loads((CC.OUT / "build.json").read_text(encoding="utf-8"))
    H = tuple(build["H"])
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": runs, "undo": [], "redo": [], "delete": [], "edit": []}
    calls = CC.Calls(D, NAMES)
    for r in range(runs):
        root = CC.fresh_copy(f"gui{r}")
        if warm:
            _warm(root)
        base = threading.active_count()
        lab = CB.Lab(root)
        for t in lab.tools.values():                                  # every card built and read once, then put away
            t.open_tool()                                             # (a session that placed four kinds of step)
            lab.pump(lambda: threading.active_count() <= base, 120)
            t.close_tool()
        lab.pump(lambda: threading.active_count() <= base, 120)

        def act(kind, fn):
            m0 = calls.mark()
            t0 = time.perf_counter()
            fn()
            slot = time.perf_counter() - t0
            lp = lab.pump(lambda: threading.active_count() <= base, 120)
            tail = time.perf_counter() - t0
            g, w = _gui_cost(calls, m0)
            out[kind].append({"slot_s": round(slot, 4), "until_readers_done_s": round(tail, 3), "loop": lp,
                              "gui_draft_s": g, "worker_draft_s": w, "calls": calls.summary(m0),
                              "status": lab.bar.status_lbl.text()})
        act("undo", lab.bar.undo)
        act("redo", lab.bar.redo)
        # Delete H: the put-back re-runs H2 (its read window holds H's blocks) and replays I, T, S
        assert lab.bar.pick(H[0] + 0.7, H[1] - 0.4) == 0, lab.bar.status_lbl.text()
        n0, m0 = len(lab.argvs), calls.mark()
        t0 = time.perf_counter()
        lab.bar.delete_btn.click()
        slot = time.perf_counter() - t0
        lp = lab.pump(lambda: lab.bar._edit is None and threading.active_count() <= base, 900)
        g, w = _gui_cost(calls, m0)
        out["delete"].append({"slot_s": round(slot, 4), "total_s": round(time.perf_counter() - t0, 2), "loop": lp,
                              "gui_draft_s": g, "worker_draft_s": w, "calls": calls.summary(m0),
                              "jobs": [{"verb": a["argv"][5], "s": round(a.get("s", -1), 2)}
                                       for a in lab.argvs[n0:]],
                              "status": lab.bar.status_lbl.text(), "rows": D.recipe_rows(lab.bar.draft())})
        print("delete", out["delete"][-1]["status"], out["delete"][-1]["jobs"], out["delete"][-1]["total_s"])
        # Edit H on a fresh copy: move it 8u; H2 re-runs (world-fuse), I, T, S replay
        root2 = CC.fresh_copy(f"guiedit{r}")
        if warm:
            _warm(root2)
        lab2 = CB.Lab(root2, tools=("hill",))
        hill = lab2.tools["hill"]
        assert lab2.bar.pick(H[0] + 0.7, H[1] - 0.4) == 0, lab2.bar.status_lbl.text()
        n0, m0 = len(lab2.argvs), calls.mark()
        t0 = time.perf_counter()
        lab2.bar.edit_btn.click()
        slot = time.perf_counter() - t0
        lp_open = lab2.pump(lambda: hill.editing() and hill._ix is not None, 300)
        t_open = time.perf_counter() - t0
        H1 = next(c for c in sorted(((H[0] + dx, H[1] + dz) for dx in (-8, 0, 8) for dz in (-8, 0, 8) if dx or dz),
                                    key=lambda c: math.dist(c, H)) if HE.preview(hill._ix, c, 4.2, 18.0)["ok"])
        hill.place(*H1, 0.0)
        t1 = time.perf_counter()
        lp_check = lab2.pump(lambda: hill._current_verdict() is not None, 600)
        t_check = time.perf_counter() - t1
        assert hill.accept_btn.isEnabled(), hill.verdict_lbl.text()
        t2 = time.perf_counter()
        hill.accept_btn.click()
        lp_acc = lab2.pump(lambda: lab2.bar._edit is None and hill._job is None, 1800)
        t_acc = time.perf_counter() - t2
        g, w = _gui_cost(calls, m0)
        out["edit"].append({"edit_click_slot_s": round(slot, 4), "open_until_card_ready_s": round(t_open, 2),
                            "check_s": round(t_check, 2), "accept_and_put_back_s": round(t_acc, 2),
                            "loops": {"open": lp_open, "check": lp_check, "accept": lp_acc},
                            "gui_draft_s": g, "worker_draft_s": w, "calls": calls.summary(m0),
                            "jobs": [{"verb": a["argv"][5], "s": round(a.get("s", -1), 2)} for a in lab2.argvs[n0:]],
                            "status": lab2.bar.status_lbl.text()})
        print("edit", out["edit"][-1]["status"], out["edit"][-1]["jobs"], t_acc)
        for t in list(lab.tools.values()) + list(lab2.tools.values()):
            t.close_tool()
    calls.restore()
    out["warm"] = warm
    CC.save("ops_gui_warm.json" if warm else "ops_gui.json", out)
    for kind in ("undo", "redo"):
        for x in out[kind]:
            print(kind, "slot", x["slot_s"], "until readers done", x["until_readers_done_s"], "max gap",
                  x["loop"]["max_gap"], "gui draft", x["gui_draft_s"], "worker draft", x["worker_draft_s"])


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "module"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    if mode == "module":
        module(n, warm=len(sys.argv) > 3 and sys.argv[3] == "warm")
    else:
        gui(n, warm=len(sys.argv) > 3 and sys.argv[3] == "warm")
