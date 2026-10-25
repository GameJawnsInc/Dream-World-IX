"""reads_card: the real carry cards (ForestTool, MountainTool) in a Qt process, threaded exactly as the Workspace runs
them (CarryTool._bg worker threads, sync=False), timing what the user waits on when a card opens, opens again, or the
draft moves under it -- and how far the GUI thread's event loop stalls meanwhile (the window freezing).

Each run is a FRESH child process (a cold UnityPy import + env, as the first card open of a Workspace session is);
the parent runs it N times and keeps min/median.

    py studies/overworld-editor/perf/reads_card.py [runs=3]

Instrument calibration: the tick monitor is a 2 ms PreciseTimer; its idle worst gap is measured first in the same
process (``idle_gap_ms``) and every stall is reported beside it. The panel is a stub (no GL); prefs are pinned to a
temp dir; drafts go under out/perf/reads/drafts (a copy of the live world folder: the install is read only)."""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reads_common import GAME, OUT, SOURCE, DRAFTS, dump, lane_draft  # noqa: E402


class StubPanel:
    def set_overlays(self, o):
        pass

    def set_ghost(self, g):
        pass


def child(which):
    os.environ["QT_QPA_PLATFORM"] = "offscreen"          # no GL needed: the cards' reads are CPU + disk
    from ff9mapkit import provision
    cfg = Path(tempfile.mkdtemp(prefix="reads_cfg_"))
    real = provision._user_dir
    provision._user_dir = lambda sub: cfg if sub == "config" else real(sub)
    t_imp = time.perf_counter()
    from PySide6.QtCore import QElapsedTimer, QEventLoop, Qt, QTimer
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace import worldforest as WF
    from ff9mapkit.workspace.worldmountain import MountainTool
    t_imp = time.perf_counter() - t_imp
    lane_draft()                                         # the draft exists, so the cards read the DRAFT (as after Accept 1)
    pal = pick_palette("dark")

    reads = []                                           # (frame, t_start, t_end) of every soup read the card started
    real_read = WF.CarryTool._read_soup

    def counted(self, folder, seam=False):
        t0 = time.perf_counter()
        try:
            return real_read(self, folder, seam)
        finally:
            reads.append(("seam" if seam else "east", t0, time.perf_counter()))
    WF.CarryTool._read_soup = counted

    import threading
    from ff9mapkit.world import draft as D
    meta_calls = {"gui": [0, 0.0], "worker": [0, 0.0]}
    real_meta = D.read_meta

    def timed_meta(d):
        t0 = time.perf_counter()
        try:
            return real_meta(d)
        finally:
            k = "gui" if threading.current_thread() is threading.main_thread() else "worker"
            meta_calls[k][0] += 1
            meta_calls[k][1] += time.perf_counter() - t0
    D.read_meta = timed_meta
    handlers = []                                        # (what, ms) of every _on_bg handler (the GUI thread)
    real_on_bg = WF.CarryTool._on_bg

    def timed_on_bg(self, what, serial, result, err):
        t0 = time.perf_counter()
        try:
            return real_on_bg(self, what, serial, result, err)
        finally:
            handlers.append((what, round((time.perf_counter() - t0) * 1000, 1)))
    WF.CarryTool._on_bg = timed_on_bg

    def snap():
        out = {"meta_gui_calls": meta_calls["gui"][0], "meta_gui_ms": round(meta_calls["gui"][1] * 1000, 1),
               "meta_worker_calls": meta_calls["worker"][0], "handlers_ms": list(handlers)}
        for k in meta_calls:
            meta_calls[k] = [0, 0.0]
        handlers.clear()
        return out

    tools = []
    kw = dict(game_fn=lambda: GAME, source_fn=lambda: SOURCE, drafts_root=DRAFTS,
              on_changed=lambda d: [t.island_changed() for t in tools])
    tool = (WF.ForestTool if which == "forest" else MountainTool)(pal, StubPanel(), **kw)
    tools.append(tool)

    gaps = []
    last = [None]

    def tick():
        now = time.perf_counter()
        if last[0] is not None:
            gaps.append(now - last[0])
        last[0] = now
    mon = QTimer()
    mon.setTimerType(Qt.TimerType.PreciseTimer)
    mon.setInterval(2)
    mon.timeout.connect(tick)

    def wait(until, sec=600):
        """Run the real event loop until ``until()``; returns (seconds, worst GUI gap ms, gaps > 50 ms)."""
        gaps.clear()
        last[0] = None
        loop = QEventLoop()
        poll = QTimer()
        poll.setInterval(1)
        poll.timeout.connect(lambda: loop.quit() if until() else None)
        t0 = time.perf_counter()
        dead = QTimer()
        dead.setSingleShot(True)
        dead.timeout.connect(loop.quit)
        dead.start(int(sec * 1000))
        mon.start()
        poll.start()
        if not until():
            loop.exec()
        poll.stop()
        mon.stop()
        dt = time.perf_counter() - t0
        worst = max(gaps) * 1000 if gaps else 0.0
        return round(dt, 3), round(worst, 1), sum(1 for g in gaps if g > 0.05)

    def idle():
        """Every worker of the previous step done (draftinfo walks included), so steps do not overlap."""
        t0 = time.perf_counter()
        while threading.active_count() > 1 and time.perf_counter() - t0 < 120:
            app.processEvents()
            time.sleep(0.01)
        app.processEvents()

    # calibrate the instrument: an idle second
    _dt, idle_worst, _n = wait(lambda: False, 1.0)
    d0 = lane_draft()
    t0 = time.perf_counter()
    for _ in range(5):
        real_meta(d0)
    meta_ms = (time.perf_counter() - t0) * 1000 / 5
    t0 = time.perf_counter()
    info = (D.edited_blocks(d0), D.stale(d0), D.last_promote(d0))
    draftinfo_s = time.perf_counter() - t0
    res = {"which": which, "import_s": round(t_imp, 3), "idle_gap_ms": idle_worst,
           "read_meta_ms_each": round(meta_ms, 2), "draft_json_bytes": (d0 / D.DRAFT_FILE).stat().st_size,
           "draftinfo_worker_s": round(draftinfo_s, 3)}
    snap()

    def soups_in():
        return len(tool._soups) >= 2

    donor = tool.donor()
    # 1. first open: the island (both frames) + the donor's outline (a stock read: UnityPy env cold)
    t_open = time.perf_counter()
    tool.open_tool()
    open_call_ms = (time.perf_counter() - t_open) * 1000
    dt_ix, worst_ix, n_ix = wait(lambda: tool._ix is not None)
    dt_all, worst_all, n_all = wait(lambda: soups_in() and donor in tool._outlines)
    res["open1"] = {"open_tool_call_gui_ms": round(open_call_ms, 1), "ix_s": dt_ix, "ix_worst_gui_gap_ms": worst_ix,
                    "then_both_frames_and_outline_s": round(dt_all, 3), "worst_gui_gap_ms": max(worst_ix, worst_all),
                    "gaps_over_50ms": n_ix + n_all, "soup_reads": len(reads), **snap()}
    idle()
    # 2. close and open again: the outline is kept per card, the soups are dropped on open
    tool.close_tool()
    n0 = len(reads)
    t_open = time.perf_counter()
    tool.open_tool()
    open_call_ms = (time.perf_counter() - t_open) * 1000
    dt_ix, worst_ix, n_ix = wait(lambda: tool._ix is not None)
    dt_all, worst_all, _ = wait(soups_in)
    res["open2"] = {"open_tool_call_gui_ms": round(open_call_ms, 1), "ix_s": dt_ix,
                    "both_frames_s": round(dt_ix + dt_all, 3), "worst_gui_gap_ms": max(worst_ix, worst_all),
                    "soup_reads": len(reads) - n0, **snap()}
    idle()
    # 3. island_changed (an undo / redo / rescan): soups dropped and read again
    n0 = len(reads)
    t0 = time.perf_counter()
    tool.island_changed()
    call_ms = (time.perf_counter() - t0) * 1000
    dt_ix, worst_ix, _ = wait(lambda: tool._ix is not None)
    dt_all, worst_all, _ = wait(soups_in)
    res["island_changed"] = {"call_gui_ms": round(call_ms, 1), "ix_s": dt_ix, "both_frames_s": round(dt_ix + dt_all, 3),
                             "worst_gui_gap_ms": max(worst_ix, worst_all), "soup_reads": len(reads) - n0, **snap()}
    idle()
    # 4. the Accept's landing (CarryTool._accepted, the real method, its subprocess skipped): it drops and re-reads,
    #    then on_changed -> island_changed drops and re-reads AGAIN
    wait(lambda: False, 0.3)
    n0 = len(reads)
    t0 = time.perf_counter()
    tool._accepted({"ok": True, "written": [], "blocks": [], "center": None})
    call_ms = (time.perf_counter() - t0) * 1000
    dt_ix, worst_ix, _ = wait(lambda: tool._ix is not None)
    dt_all, worst_all, _ = wait(soups_in)
    idle()                                               # let the stale first pair finish too (they hold the GIL)
    started = reads[n0:]
    res["accepted"] = {"call_gui_ms": round(call_ms, 1), "ix_s": dt_ix, "both_frames_s": round(dt_ix + dt_all, 3),
                       "worst_gui_gap_ms": max(worst_ix, worst_all), "soup_reads": len(started),
                       "soup_read_spans_s": [round(e - s, 3) for _f, s, e in started], **snap()}
    idle()
    # 5. a single soup read alone vs two at once (the GIL): read east, then east+seam concurrently
    import threading
    def one(seam):
        real_read(tool, tool.target(), seam)
    t0 = time.perf_counter(); one(False); solo = time.perf_counter() - t0
    th = [threading.Thread(target=one, args=(s,)) for s in (False, True)]
    t0 = time.perf_counter()
    for t in th:
        t.start()
    for t in th:
        t.join()
    pair = time.perf_counter() - t0
    res["gil"] = {"one_read_s": round(solo, 3), "two_concurrent_reads_s": round(pair, 3)}
    if which == "mountain":                              # a second massif's outline in the same process (read_block memo)
        box = tool.donor_box
        other = box.itemData((box.currentIndex() + 1) % box.count())
        t0 = time.perf_counter()
        box.setCurrentIndex(box.findData(other))
        dt, worst, _ = wait(lambda: other in tool._outlines)
        res["outline_other_donor"] = {"donor": other, "s": dt, "worst_gui_gap_ms": worst}
        from ff9mapkit.world import mountainedit as ME
        t0 = time.perf_counter()
        ME.outline(other, game=GAME)
        res["outline_same_donor_again_direct_s"] = round(time.perf_counter() - t0, 3)
        from ff9mapkit.world import extract as X
        env = X._worldmap_env(1, GAME)
        res["block_memo_size"] = len(getattr(env, "_ff9mapkit_block_memo", {}))
    else:
        from ff9mapkit.world import forestedit as FE
        t0 = time.perf_counter()
        FE.outline(tool.donor(), game=GAME)
        res["outline_same_donor_again_direct_s"] = round(time.perf_counter() - t0, 3)
    tool.close_tool()
    print("RESULT " + json.dumps(res))


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    lane_draft()
    allr = {}
    for which in ("forest", "mountain"):
        rs = []
        for i in range(runs):
            r = subprocess.run([sys.executable, __file__, "--child", which], capture_output=True, text=True,
                               timeout=900)
            line = [ln for ln in r.stdout.splitlines() if ln.startswith("RESULT ")]
            if not line:
                print(r.stdout[-3000:], r.stderr[-3000:])
                raise SystemExit(f"{which} run {i} failed")
            rs.append(json.loads(line[0][7:]))
            print(which, i, rs[-1])
        allr[which] = rs
    dump("reads_card.json", {"cmd": "py studies/overworld-editor/perf/reads_card.py " + str(runs), "runs": allr})


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--child":
        child(sys.argv[2])
    else:
        main()
