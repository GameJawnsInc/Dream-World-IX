"""reads_proto_card: prototypes of the carry cards' read scheduling, each a monkeypatch inside this probe, compared
against the unpatched card in the same harness (the real ForestTool, threaded as the Workspace runs it; fresh process
per run; stub panel, prefs pinned to a temp dir, drafts under out/perf/reads/drafts).

  base   unpatched
  A      ONE re-read after an Accept: CarryTool._accepted skips its own _drop_soups + _load_soup when on_changed is set
         (the World tab's _draft_changed calls island_changed on every card, which drops and reads again anyway)
  B      the CURRENT frame first: _load_soup starts the other frame's read only once the current one has landed
         (two concurrent reads fight for the GIL: each lands at ~2x a solo read)
  C      draft() answered from draft.json's stat: read_meta parsed only when (mtime_ns, size) moved (a bool, so no
         shared mutable meta escapes)
  ABC    all three

Measured per variant: an Accept's landing (the real _accepted, its subprocess skipped) -- seconds until the current
frame's soup is in, soup reads started; an island_changed; a second open; the GUI-thread ms of draft.json parses; one
ghost drag frame (drag_to: the GUI-thread ms and its read_meta calls). The verdict-relevant state is compared at the
end of each variant: the soups the card holds == an unpatched read of the same draft (reads_soup.ix_equal).

    py studies/overworld-editor/perf/reads_proto_card.py [runs=3]
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reads_common import DRAFTS, GAME, SOURCE, dump, lane_draft, stat  # noqa: E402

VARIANTS = ("base", "A", "B", "C", "ABC")


class StubPanel:
    def set_overlays(self, o):
        pass

    def set_ghost(self, g):
        pass


def patch(variant, WF, D):
    if "A" in variant:
        real_acc = WF.CarryTool._accepted

        def accepted(self, v):
            if self._on_changed is None or self._editing is not None:
                return real_acc(self, v)
            # the real body, less its own drop + read; its on_changed (-> island_changed: drop + read) is held to the
            # end, where the real body calls it too, and runs with the real methods
            oc, held = self._on_changed, []
            self._on_changed = held.append
            self._drop_soups = lambda: None
            self._load_soup = lambda: None
            try:
                real_acc(self, v)
            finally:
                del self._drop_soups, self._load_soup
                self._on_changed = oc
            for d in held:
                oc(d)
        WF.CarryTool._accepted = accepted
    if "B" in variant:
        def load_soup(self):
            target, cur = self.target(), self._seam
            fly = self.__dict__.setdefault("_inflight", set())
            for seam in (cur, not cur):
                if seam and self._seam_soup_fn is None:
                    continue
                if (target, seam) in self._soups:
                    if seam == cur:
                        self._ix, self._ix_for = self._soups[(target, seam)], target
                    continue
                if (self._soup_gen, target, seam) in fly:
                    continue                          # already being read for this island
                if seam != cur and (target, cur) not in self._soups:
                    self._other_waits = True          # the current frame first: this one once it has landed
                    continue
                fn = self._seam_soup_fn if seam else self._soup_fn
                fly.add((self._soup_gen, target, seam))

                def read(fn=fn, seam=seam, gen=self._soup_gen):
                    try:
                        return (gen, target, seam, fn(target))
                    except Exception as e:  # noqa: BLE001
                        return (gen, target, seam, e)
                self._bg("soup", read)
        WF.CarryTool._load_soup = load_soup
        real_on_bg = WF.CarryTool._on_bg

        def on_bg(self, what, serial, result, err):
            if what == "soup" and err is None:
                self.__dict__.setdefault("_inflight", set()).discard(tuple(result[:3]))
            r = real_on_bg(self, what, serial, result, err)
            if what == "soup" and getattr(self, "_other_waits", False) and not self.isHidden():
                self._other_waits = False
                self._load_soup()
            return r
        WF.CarryTool._on_bg = on_bg
    if "I" in variant:
        import reads_soup as RS
        smemo = RS.SoupMemo()
        lock = threading.Lock()

        def read_soup(self, folder, seam=False):
            with lock:                                   # (one memo, many worker threads)
                return smemo.soup(folder, seam)[0]
        WF.CarryTool._read_soup = read_soup
    if "C" in variant:
        memo = {}
        real_meta = D.read_meta

        def is_draft(p):
            f = Path(p) / D.DRAFT_FILE
            try:
                st = f.stat()
            except OSError:
                return False
            key = (st.st_mtime_ns, st.st_size)
            hit = memo.get(str(f))
            if hit is not None and hit[0] == key:
                return hit[1]
            ok = real_meta(p) is not None
            memo[str(f)] = (key, ok)
            return ok

        def draft(self):
            p = D.draft_path(self.source(), root=self._drafts_root)
            return p if is_draft(p) else None
        WF.CarryTool.draft = draft


def child(variant):
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from ff9mapkit import provision
    cfg = Path(tempfile.mkdtemp(prefix="reads_cfg_"))
    real = provision._user_dir
    provision._user_dir = lambda sub: cfg if sub == "config" else real(sub)
    from PySide6.QtCore import QEventLoop, Qt, QTimer
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace import worldforest as WF
    from ff9mapkit.world import draft as D
    import reads_soup as RS
    draft_dir = lane_draft()
    meta_calls = {"gui": [0, 0.0]}
    real_meta = D.read_meta

    def timed_meta(d):
        t0 = time.perf_counter()
        try:
            return real_meta(d)
        finally:
            if threading.current_thread() is threading.main_thread():
                meta_calls["gui"][0] += 1
                meta_calls["gui"][1] += time.perf_counter() - t0
    D.read_meta = timed_meta
    patch(variant, WF, D)
    reads = []
    real_read = WF.CarryTool._read_soup

    def counted(self, folder, seam=False):
        reads.append(seam)
        return real_read(self, folder, seam)
    WF.CarryTool._read_soup = counted
    tools = []
    tool = WF.ForestTool(pick_palette("dark"), StubPanel(), game_fn=lambda: GAME, source_fn=lambda: SOURCE,
                         drafts_root=DRAFTS, on_changed=lambda d: [t.island_changed() for t in tools])
    tools.append(tool)

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
        return round(time.perf_counter() - t0, 3)

    def idle():
        t0 = time.perf_counter()
        while threading.active_count() > 1 and time.perf_counter() - t0 < 120:
            app.processEvents()
            time.sleep(0.01)
        app.processEvents()

    def meta_snap():
        out = (meta_calls["gui"][0], round(meta_calls["gui"][1] * 1000, 1))
        meta_calls["gui"] = [0, 0.0]
        return out

    res = {"variant": variant}
    tool.open_tool()
    res["open1_ix_s"] = wait(lambda: tool._ix is not None and tool.donor() in tool._outlines)
    idle()
    meta_snap()
    tool.close_tool()
    n0 = len(reads)
    tool.open_tool()
    res["open2_ix_s"] = wait(lambda: tool._ix is not None)
    idle()
    res["open2_reads"] = len(reads) - n0
    res["open2_meta_gui"] = meta_snap()
    n0 = len(reads)
    t0 = time.perf_counter()
    tool.island_changed()
    res["island_changed_call_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    res["island_changed_ix_s"] = wait(lambda: tool._ix is not None)
    idle()
    res["island_changed_reads"] = len(reads) - n0
    res["island_changed_meta_gui"] = meta_snap()
    n0 = len(reads)
    changed = None
    if os.environ.get("READS_CHANGE") == "1":
        terr = sorted((draft_dir / "FF9_Data" / "WorldMap" / "Disc1" / "0_1").rglob("*Terrain.ff9mesh"))
        changed, keep = terr[1], terr[1].read_bytes()
        changed.write_bytes(terr[0].read_bytes())
        res["changed_block"] = changed.name
    t0 = time.perf_counter()
    tool._accepted({"ok": True, "written": [], "blocks": [], "center": None})
    res["accepted_call_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    res["accepted_ix_s"] = round(wait(lambda: tool._ix is not None) + res["accepted_call_ms"] / 1000, 3)
    idle()
    res["accepted_reads"] = len(reads) - n0
    res["accepted_meta_gui"] = meta_snap()
    # one ghost drag frame (the island and the canopy in): place, then drag a few frames
    tool.place(1400.0, -460.0, 3.2)
    tool._timer.stop()
    frames = []
    meta_snap()
    for i in range(10):
        t0 = time.perf_counter()
        tool.drag_to(1400.0 + 2 * i, -460.0)
        frames.append((time.perf_counter() - t0) * 1000)
    n, ms = meta_snap()
    res["drag_frame_ms"] = stat([f / 1000 for f in frames])
    res["drag_frame_read_meta_calls_each"] = n / 10
    res["drag_frame_read_meta_ms_each"] = round(ms / 10, 2)
    tool._runner.kill()
    # identity: what the card now holds is what an unpatched read of the same draft gives
    ref_e, ref_s = RS.card_read(draft_dir, False), RS.card_read(draft_dir, True)
    held = tool._soups
    res["identity"] = [RS.ix_equal(held[(draft_dir, False)], ref_e) or "identical" if (draft_dir, False) in held
                       else "missing",
                       RS.ix_equal(held[(draft_dir, True)], ref_s) or "identical" if (draft_dir, True) in held
                       else "missing"]
    if changed is not None:
        changed.write_bytes(keep)
        res["draft_restored"] = RS.ix_equal(RS.card_read(draft_dir, False), ref_e) is not None   # it differed: restored
    tool.close_tool()
    print("RESULT " + json.dumps(res))


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    variants = sys.argv[2].split(",") if len(sys.argv) > 2 else VARIANTS
    name = sys.argv[3] if len(sys.argv) > 3 else "reads_proto_card.json"
    if len(sys.argv) > 4 and sys.argv[4] == "change":
        os.environ["READS_CHANGE"] = "1"
    lane_draft()
    out = {"cmd": "py studies/overworld-editor/perf/reads_proto_card.py " + " ".join(sys.argv[1:]), "variants": {}}
    for i in range(runs):                                # interleave the variants: drift in machine load hits all
        for v in variants:
            r = subprocess.run([sys.executable, __file__, "--child", v], capture_output=True, text=True, timeout=900)
            line = [ln for ln in r.stdout.splitlines() if ln.startswith("RESULT ")]
            if not line:
                print(r.stdout[-2000:], r.stderr[-3000:])
                raise SystemExit(v)
            rec = json.loads(line[0][7:])
            out["variants"].setdefault(v, []).append(rec)
            print(i, v, rec, flush=True)
    summ = {}
    for v, rs in out["variants"].items():
        summ[v] = {k: stat([r[k] for r in rs]) for k in ("open2_ix_s", "island_changed_ix_s", "accepted_ix_s")}
        summ[v]["accepted_reads"] = [r["accepted_reads"] for r in rs]
        summ[v]["accepted_meta_gui_ms"] = [r["accepted_meta_gui"][1] for r in rs]
        summ[v]["island_changed_meta_gui_ms"] = [r["island_changed_meta_gui"][1] for r in rs]
        summ[v]["drag_frame_min_ms"] = [round(r["drag_frame_ms"]["min_s"] * 1000, 2) for r in rs]
        summ[v]["drag_frame_read_meta_calls_each"] = [r["drag_frame_read_meta_calls_each"] for r in rs]
        summ[v]["identity"] = [r["identity"] for r in rs]
    out["summary"] = summ
    for v, s in summ.items():
        print(v, s)
    dump(name, out)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--child":
        child(sys.argv[2])
    else:
        main()
