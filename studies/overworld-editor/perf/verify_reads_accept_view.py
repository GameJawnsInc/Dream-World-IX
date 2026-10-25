"""verify_reads_accept_view: is the island soup on the user's critical path after an Accept?

The reads lane timed an Accept's landing with a stub on_changed that only calls island_changed. The World tab's real
on_changed is WorldDoc._draft_changed, which ALSO calls _load_view3d -> WorldView3DPanel.load(site): the 3D view is
replaced by "Loading the map..." and a worker runs load_scene over the whole map, concurrently with the card's soup
reads (one GIL). Until it lands the user cannot click the map. This probe reproduces that: the real ForestTool
(threaded, sync=False), its real _accepted, and an on_changed that does what _draft_changed does to the threads --
every card's island_changed, then load_scene(site) on a worker thread, site built as WorldDoc._render_site builds it
in "With the draft" mode (the game's FolderNames stack with the draft in place of FF9CustomMap-world; Memoria.ini is
read only).

Per variant (fresh process each, interleaved, 3 runs):
  map_alone_s     a second load_scene of the same site with nothing else running (the session's first is untimed)
  accept_ix_s     from the _accepted call until the current frame's soup is in (what the reads lane timed)
  accept_map_s    from the _accepted call until load_scene returns (the view can come back)
  accept_wait_s   max of the two: the earliest the user can place the next shape
Variants: base (unpatched), A, ABCI (the reads lane's own prototypes, reads_proto_card.patch, unchanged); AR = A
plus the Accept's own draft-label walk skipped (island_changed walks it once); K4 = base with 4 more cards built
earlier in the session and hidden (each hidden card's island_changed still starts a draft-label walk).
A real block file of the verifier's draft is changed before the landing (put back after), as an Accept writes one.

    py studies/overworld-editor/perf/verify_reads_accept_view.py [runs=3] [variants=base,A,ABCI]
Evidence: out/perf/reads/verify/verify_reads_accept_view.json"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reads_common as RC  # noqa: E402

VOUT = RC.WT / "studies" / "overworld-editor" / "out" / "perf" / "reads" / "verify"
VOUT.mkdir(parents=True, exist_ok=True)
RC.OUT, RC.DRAFTS = VOUT, VOUT / "drafts"


class StubPanel:
    def set_overlays(self, o):
        pass

    def set_ghost(self, g):
        pass


def child(variant):
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from ff9mapkit import provision
    cfg = Path(tempfile.mkdtemp(prefix="vreads_cfg_"))
    real = provision._user_dir
    provision._user_dir = lambda sub: cfg if sub == "config" else real(sub)
    from PySide6.QtCore import QEventLoop, Qt, QTimer
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace import worldforest as WF
    from ff9mapkit.workspace.worldview3d import load_scene
    from ff9mapkit.world import draft as D, extract as X, mesh as M, render as R
    import reads_proto_card as P
    import reads_soup as RS
    GAME = RC.GAME
    draft = RC.lane_draft()
    assert draft.resolve().is_relative_to(VOUT.resolve()), draft
    orig_acc = WF.CarryTool._accepted
    P.patch("".join(c for c in variant if c in "ABCI"), WF, D)
    if "R" in variant:                                   # A, and the Accept's own draft-label walk skipped too
        def accepted(self, v):                           # (island_changed, called last, walks it once)
            if self._on_changed is None or self._editing is not None:
                return orig_acc(self, v)
            oc, held = self._on_changed, []
            self._on_changed = held.append
            self._drop_soups = self._load_soup = self._refresh_draft_label = lambda: None
            try:
                orig_acc(self, v)
            finally:
                del self._drop_soups, self._load_soup, self._refresh_draft_label
                self._on_changed = oc
            for d in held:
                oc(d)
        WF.CarryTool._accepted = accepted
    walks = []                                           # every draft-label walk (draft.edited_blocks), its span
    real_eb = D.edited_blocks

    def counted_eb(d):
        t0 = time.perf_counter()
        try:
            return real_eb(d)
        finally:
            walks.append((t0, time.perf_counter()))
    D.edited_blocks = counted_eb

    cells = tuple((bx, by) for by in range(M.GRID_ROWS) for bx in range(M.GRID_COLS))
    stack = R.game_stack(GAME)
    here = RC.SOURCE.name
    names = [p.name for p in stack]
    roots = [draft if p.name == here else p for p in stack] if here in names else [draft] + list(stack)
    site = R.RenderSite(cells=cells, disc=1, game=GAME, stack=tuple(roots))

    gaps, last = [], [None]

    def tick():
        now = time.perf_counter()
        if last[0] is not None:
            gaps.append(now - last[0])
        last[0] = now
    mon = QTimer()
    mon.setTimerType(Qt.TimerType.PreciseTimer)
    mon.setInterval(2)
    mon.timeout.connect(tick)

    def wait(until, sec=300):
        loop = QEventLoop()
        poll = QTimer()
        poll.setInterval(1)
        poll.timeout.connect(lambda: loop.quit() if until() else None)
        t0 = time.perf_counter()
        poll.start()
        if not until():
            loop.exec()
        poll.stop()
        return time.perf_counter() - t0

    def idle():
        t0 = time.perf_counter()
        while threading.active_count() > 1 and time.perf_counter() - t0 < 300:
            app.processEvents()
            time.sleep(0.005)
        app.processEvents()

    res = {"variant": variant, "stack": [str(p) for p in roots]}
    t0 = time.perf_counter()
    X._worldmap_env(1, GAME)
    res["env_s"] = round(time.perf_counter() - t0, 3)
    t0 = time.perf_counter()
    load_scene(site)                                     # the session's first map load (untimed for the verdict)
    res["map_first_s"] = round(time.perf_counter() - t0, 3)

    tools = []
    box = {}

    def on_changed(d):                                   # WorldDoc._draft_changed's effect on the threads
        for t in tools:
            t.island_changed()

        def work():
            load_scene(site)
            box["map_done"] = time.perf_counter()
        box["map_th"] = threading.Thread(target=work, daemon=True)
        box["map_th"].start()
    tool = WF.ForestTool(pick_palette("dark"), StubPanel(), game_fn=lambda: GAME, source_fn=lambda: RC.SOURCE,
                         drafts_root=RC.DRAFTS, on_changed=on_changed)
    tools.append(tool)
    extra = int(variant.split("K")[1]) if "K" in variant else 0
    for _ in range(extra):                               # cards built earlier in the session, now hidden
        t = WF.ForestTool(pick_palette("dark"), StubPanel(), game_fn=lambda: GAME, source_fn=lambda: RC.SOURCE,
                          drafts_root=RC.DRAFTS, on_changed=on_changed)
        t.hide()
        tools.append(t)
    res["hidden_cards"] = extra
    tool.open_tool()
    wait(lambda: len(tool._soups) >= 2 and tool.donor() in tool._outlines)
    idle()

    # the map alone, warm (a second load of the same site, nothing else running)
    done = {}
    th = threading.Thread(target=lambda: (load_scene(site), done.setdefault("t", time.perf_counter())), daemon=True)
    t0 = time.perf_counter()
    th.start()
    wait(lambda: "t" in done)
    res["map_alone_s"] = round(done["t"] - t0, 3)
    idle()

    terr = sorted((draft / "FF9_Data" / "WorldMap" / "Disc1" / "0_1").rglob("*Terrain.ff9mesh"))
    changed, keep = terr[1], terr[1].read_bytes()
    changed.write_bytes(terr[0].read_bytes())
    try:
        gaps.clear()
        last[0] = None
        mon.start()
        walks.clear()
        t0 = time.perf_counter()
        tool._accepted({"ok": True, "written": [], "blocks": [], "center": None})
        call = time.perf_counter() - t0
        t_ix = call + wait(lambda: tool._ix is not None)
        wait(lambda: "map_done" in box)
        t_map = box["map_done"] - t0
        idle()
        t_all = time.perf_counter() - t0
        mon.stop()
        g = sorted(gaps)
        res.update({"accept_call_gui_ms": round(call * 1000, 1), "accept_ix_s": round(t_ix, 3),
                    "accept_map_s": round(t_map, 3), "accept_wait_s": round(max(t_ix, t_map), 3),
                    "accept_all_threads_idle_s": round(t_all, 3),
                    "worst_gui_gap_ms": round(g[-1] * 1000, 1) if g else 0,
                    "p99_gui_gap_ms": round(g[int(len(g) * 0.99)] * 1000, 1) if g else 0,
                    "draft_label_walks": len(walks),
                    "draft_label_walk_spans_s": [round(b - a, 3) for a, b in walks]})
        ref = RS.card_read(draft, False)
        res["identity_east"] = RS.ix_equal(tool._soups[(draft, False)], ref) or "identical"
    finally:
        changed.write_bytes(keep)
    res["restored"] = RS.ix_equal(RS.card_read(draft, False), ref) is not None
    tool.close_tool()
    print("RESULT " + json.dumps(res))


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    variants = sys.argv[2].split(",") if len(sys.argv) > 2 else ["base", "A", "ABCI"]
    RC.lane_draft()
    out = {"cmd": "py studies/overworld-editor/perf/verify_reads_accept_view.py " + " ".join(sys.argv[1:]),
           "variants": {}}
    for i in range(runs):
        for v in variants:
            r = subprocess.run([sys.executable, __file__, "--child", v], capture_output=True, text=True, timeout=1200)
            line = [ln for ln in r.stdout.splitlines() if ln.startswith("RESULT ")]
            if not line:
                print(r.stdout[-2000:], r.stderr[-3000:])
                raise SystemExit(v)
            rec = json.loads(line[0][7:])
            out["variants"].setdefault(v, []).append(rec)
            print(i, v, {k: rec[k] for k in rec if k != "stack"}, flush=True)
    summ = {}
    for v, rs in out["variants"].items():
        summ[v] = {k: RC.stat([r[k] for r in rs]) for k in ("map_alone_s", "accept_ix_s", "accept_map_s",
                                                             "accept_wait_s", "worst_gui_gap_ms")}
        summ[v]["identity"] = [r["identity_east"] for r in rs]
    out["summary"] = summ
    for v, s in summ.items():
        print(v, {k: (x["min_s"], x["median_s"]) if isinstance(x, dict) else x for k, x in s.items()})
    RC.dump("verify_reads_accept_view.json", out)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--child":
        child(sys.argv[2])
    else:
        main()
