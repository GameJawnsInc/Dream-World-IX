"""Lane chain: the GUI-thread freeze of the recipe bar's Edit click and of Cancel edit, on a session whose hill card
was already built and opened once (so first-use imports are not counted), profiled.

    py studies/overworld-editor/perf/chain_editslot.py [runs] [debt|warm]

Per run: a fresh copy of the gold draft (``warm``: every file read once first, as a long session would have); the
bar + the four cards wired as WorldDoc wires them; each card opened and closed once; then pick H, click Edit
(the slot timed and cProfiled: begin_edit's five undos, the hold, the card's open and edit_row), wait for the card's
island read, then click Cancel edit (timed: cancel_edit's five redos) and wait for the readers.
"""
from __future__ import annotations

import cProfile
import io
import json
import pstats
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_common as CC                                             # noqa: E402
import chain_ops as CO                                                # noqa: E402

from ff9mapkit.world import draft as D                                # noqa: E402


def main(runs=3, mode="warm"):
    import chain_build as CB
    build = json.loads((CC.OUT / "build.json").read_text(encoding="utf-8"))
    H = tuple(build["H"])
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": runs, "mode": mode, "rows": []}
    calls = CC.Calls(D, CO.NAMES)
    for r in range(runs):
        root = CC.fresh_copy(f"editslot{mode}{r}")
        if mode == "warm":
            for p in root.rglob("*"):
                if p.is_file():
                    p.read_bytes()
        base = threading.active_count()
        lab = CB.Lab(root)
        for t in lab.tools.values():
            t.open_tool()
            lab.pump(lambda: threading.active_count() <= base, 120)
            t.close_tool()
        lab.pump(lambda: threading.active_count() <= base, 120)
        hill = lab.tools["hill"]
        assert lab.bar.pick(H[0] + 0.7, H[1] - 0.4) == 0, lab.bar.status_lbl.text()
        m0 = calls.mark()
        pr = cProfile.Profile()
        t0 = time.perf_counter()
        pr.enable()
        lab.bar.edit_btn.click()
        pr.disable()
        slot = time.perf_counter() - t0
        g_edit, _w = CO._gui_cost(calls, m0)
        s = io.StringIO()
        pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(30)
        if r == 0:
            pr.dump_stats(str(CC.OUT / f"editslot_{mode}.pstats"))
        lp = lab.pump(lambda: hill.editing() and hill._ix is not None and threading.active_count() <= base, 300)
        ready = time.perf_counter() - t0
        calls_edit = calls.summary(m0)
        m1 = calls.mark()
        t1 = time.perf_counter()
        hill.close_btn.click()                                        # "Cancel edit"
        cslot = time.perf_counter() - t1
        g_cancel, _w = CO._gui_cost(calls, m1)
        lp2 = lab.pump(lambda: lab.bar._edit is None and threading.active_count() <= base, 300)
        row = {"edit_slot_s": round(slot, 3), "edit_slot_draft_gui_s": g_edit, "until_card_ready_s": round(ready, 2),
               "loop_after_edit": lp, "cancel_slot_s": round(cslot, 3), "cancel_slot_draft_gui_s": g_cancel,
               "loop_after_cancel": lp2, "status": lab.bar.status_lbl.text(),
               "calls_edit": {k: v for k, v in calls_edit.items() if "|d0" in k},
               "calls_cancel": {k: v for k, v in calls.summary(m1).items() if "|d0" in k},
               "profile_edit_slot": s.getvalue() if r == 0 else None}
        out["rows"].append(row)
        print(r, {k: row[k] for k in ("edit_slot_s", "edit_slot_draft_gui_s", "until_card_ready_s", "cancel_slot_s",
                                       "cancel_slot_draft_gui_s")}, row["status"][:90])
        for t in lab.tools.values():
            t.close_tool()
    calls.restore()
    for k in ("edit_slot_s", "cancel_slot_s", "until_card_ready_s"):
        out[k] = CC.stats([row[k] for row in out["rows"]])
    CC.save(f"editslot_{mode}.json", out)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3, sys.argv[2] if len(sys.argv) > 2 else "warm")
