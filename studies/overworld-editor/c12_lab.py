"""Rung C12 on real bytes: a sink, a coast morph and a river move, each placed and then EDITED in its own card.

    py studies/overworld-editor/c12_lab.py build

THE EDITOR'S PATH, as c9_lab and c11_lab: the real RecipeBar and the real sink, coast and river cards with their real
runners against the real install, wired as the World tab wires them, into a draft of FF9CustomMap-world:
  S a sink of the first island the sink card calls clean, away from the river and the coast block;
  M a coast morph at the first lawful window (two depth rungs or more) of a coastal block no folder overrides,
    at its ceiling;
  R the river moved to the first placement free of edits (its own files left out);
then each is picked in the recipe bar, opened with Edit, and changed in its card:
  E1 S onto a second clean island (the steps after it, M and R, composed again by world-fuse on the new ground);
  E2 M one rung shallower (R composed again after it);
  E3 R onto the next free placement, or, with none free, accepted as it stood (the open-on-its-row path all the same).
Each edit's card must open on the step's own row (said back key for key), and after each:
  I1: the edited draft == world-fuse of its recipe composed onto a fresh draft of the folder, over every world file.
No game: the cards write through the same verbs every earlier rung walked in game, and I1 holds the edited draft to
the composed path.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lab as C1                                                    # noqa: E402  (pins the worktree package)

GAME, KIT = C1.GAME, C1.KIT
SOURCE = "FF9CustomMap-world"
OUT = HERE / "out" / "c12_lab"
PREP = HERE / "out" / "c12_prep.json"


def _world(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (root / "FF9_Data" / "WorldMap").rglob("Block*")
            if ".bak-" not in p.name and p.suffix in (".ff9mesh", ".txt")}


class Lab:
    def __init__(self, drafts):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])
        from ff9mapkit.editor.theme import pick_palette
        from ff9mapkit.workspace.worldcoast import CoastTool
        from ff9mapkit.workspace.worldforest import QProcessRunner
        from ff9mapkit.workspace.worldrecipe import RecipeBar
        from ff9mapkit.workspace.worldriver import RiverTool
        from ff9mapkit.workspace.worldsink import SinkTool
        from ff9mapkit.workspace.worldview3d import WorldView3DPanel
        pal = pick_palette("dark")
        self.argvs = []
        self.notes = []

        def logged():
            r = QProcessRunner()
            real = r.start

            def start(argv, cwd, done):
                self.argvs.append([str(a) for a in argv])
                real(argv, cwd, done)
            r.start = start
            return r
        panel = WorldView3DPanel(pal)
        kw = dict(game_fn=lambda: GAME, source_fn=lambda: GAME / SOURCE, drafts_root=drafts,
                  on_changed=lambda d: self.bar.refresh())
        self.tools = {"sink": SinkTool(pal, panel, runner=logged(), **kw),
                      "morph": CoastTool(pal, panel, runner=logged(), **kw),
                      "river": RiverTool(pal, panel, runner=logged(), **kw)}
        self.bar = RecipeBar(pal, game_fn=lambda: GAME, source_fn=lambda: GAME / SOURCE, runner=logged(),
                             drafts_root=drafts, on_changed=lambda d: [t.island_changed() for t in self.tools.values()],
                             on_edit=self._edit, ask=lambda t, x: True)

    def _edit(self, row, label):
        tool = self.tools[row["table"]]
        tool.open_tool()
        tool.edit_row(row, label=label, on_accepted=self.bar.edit_accepted,
                      on_cancel=lambda note=None: (self.notes.append(note), self.bar.cancel_edit(note)))

    def pump(self, until, sec):
        t = time.time()
        while time.time() - t < sec:
            self.app.processEvents()
            if until():
                return True
            time.sleep(0.02)
        return False

    def judged(self, tool, key, sec=900):
        """Wait for the card's own Check of its handles, and say whether it passed."""
        self.pump(lambda: False, 1.0)                     # the check's delay after a handle moved
        assert self.pump(lambda: tool._job is None and tool._timer.remainingTime() < 0 and (
            tool._current_verdict() is not None or (tool._preview is not None and not tool._preview["ok"])), sec), \
            (key, tool.verdict_lbl.text())
        assert tool.accept_btn.isEnabled(), (key, tool.verdict_lbl.text(), tool._preview)

    def accept(self, tool, key, sec=1800):
        t0 = time.time()
        tool.accept_btn.click()
        assert self.pump(lambda: tool._job is None and (tool.center is None or tool.isHidden()), sec), \
            (key, tool.verdict_lbl.text())
        return round(time.time() - t0, 1)


def _occupied_fn(game, draft_fn):
    from ff9mapkit.world import mesh as M
    from ff9mapkit.world import river as RV
    stack = [GAME / f for f in RV.stack_folders(GAME) if f != SOURCE]

    def occupied(cell):
        return any(M.existing_overrides([tuple(cell)], str(fo), disc=d, game=GAME)
                   for fo in [draft_fn()] + stack for d in (1, 4))
    return occupied


def build():
    from ff9mapkit.world import coastedit as CE
    from ff9mapkit.world import draft as D
    from ff9mapkit.world import recipe as RC
    from ff9mapkit.world import riveredit as RE
    from ff9mapkit.world import sinkedit as SE
    if OUT.exists():
        shutil.rmtree(OUT)
    lab = Lab(OUT / "drafts")
    sink, coast, river = lab.tools["sink"], lab.tools["morph"], lab.tools["river"]
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "timings": {}}
    T = rec["timings"]

    # -- the river first: where it stands, and the placements free of edits
    river.open_tool()
    assert lab.pump(lambda: river._river is not None, 900), river.from_lbl.text()
    rs = river._rs()
    at0 = river.river_at()
    held = river._river[2]
    free = RE.free_shifts(rs, river_at=at0, occupied=lambda cells: {c: sorted(held[c]) for c in cells if c in held})
    print(f"river now at {RE.offset_of(at0) if at0 else None}; {len(rs.shifts)} placements, free {free}")
    assert free, "no placement of the river is free: the lab needs one"
    keep_off = {tuple(c) for s in [at0] + list(free[:2]) if s for c in rs.cells_at(s)}
    keep_off |= {tuple(b) for s in [at0] + list(free[:2]) if s for b in rs.blocks_at(s)}
    river.close_tool()

    # -- two clean islands to sink, away from the river
    rows = [r for r in SE.candidates(GAME) if SE.verdict(r)["ok"]
            and not {tuple(b) for b in r.get("blocks") or []} & keep_off]
    assert len(rows) >= 2, len(rows)
    S1, S2 = rows[0], rows[1]
    keep_off |= {tuple(b) for r in (S1, S2) for b in r["blocks"]}

    # -- a coastal block no folder overrides, with a window two rungs deep
    occupied = _occupied_fn(GAME, lambda: GAME / SOURCE)
    pick = None
    tried = []
    for r in SE.candidates(GAME):
        for b in r.get("blocks") or []:
            b = tuple(b)
            if b in keep_off or b in tried or occupied(b):
                continue
            tried.append(b)
            t0 = time.time()
            ws = CE.windows(GAME, b)
            print(f"  scanned block {b}: {len(ws)} windows ({time.time() - t0:.1f} s)")
            for w in ws:
                for verb, (lo, hi) in CE.lawful(w).items():
                    deep = hi if hi > 0 else lo
                    if abs(deep) >= 1.0 and verb in CE.VERBS:
                        pick = (b, w, verb, deep)
                        break
                if pick:
                    break
            if pick or len(tried) >= 24:
                break
        if pick or len(tried) >= 24:
            break
    assert pick, f"no coastal block with a two-rung window in {tried}"
    mcell, mwin, mverb, mdepth = pick
    print(f"placing: S1 {S1['at']}, S2 {S2['at']}, M {mverb} {mdepth:g} at block {mcell}, R to {RE.offset_of(free[0])}")

    # -- S: the sink card
    sink.open_tool()
    assert lab.pump(lambda: sink._outlines.get("islands") is not None, 900)
    sink.place(*S1["at"])
    lab.judged(sink, "S")
    T["S"] = lab.accept(sink, "S")
    sink.close_tool()
    # -- M: the coast card, at the window's own anchor
    coast.open_tool()
    coast.place(*CE.anchor(mwin, mverb))
    assert lab.pump(lambda: coast._window is not None, 600), coast.window_lbl.text()
    coast.verb_box.setCurrentIndex(coast.verb_box.findData(mverb))
    coast.depth.setValue(mdepth)
    lab.judged(coast, "M")
    T["M"] = lab.accept(coast, "M")
    coast.close_tool()
    # -- R: the river card
    river.open_tool()
    assert lab.pump(lambda: river._river is not None, 900), river.from_lbl.text()
    river.place(*RE.centre(rs, free[0]))
    lab.judged(river, "R")
    T["R"] = lab.accept(river, "R")
    river.close_tool()
    draft = sink.draft()
    rows0 = D.recipe_rows(draft)
    print(f"placed: {[RC.label(r) for r in rows0]}; accepts {T}")
    assert [r["table"] for r in rows0] == ["sink", "morph", "river"], rows0
    rec.update(S1=S1["at"], S2=S2["at"], M={"cell": mcell, "verb": mverb, "depth": mdepth}, R=list(free[:2]),
               rows0=rows0)
    bar = lab.bar
    edits = rec["edits"] = []

    def edit(k, x, z, change, key):
        """Pick step k at (x, z), Edit, change it in its card, Accept; the steps after it go back on top."""
        n0 = len(lab.argvs)
        bar.refresh()
        assert bar.pick(x, z) == k, (key, bar.status_lbl.text())
        before = D.recipe_rows(draft)[k]
        bar.edit_btn.click()
        tool = lab.tools[before["table"]]
        assert tool.editing(), (key, lab.notes, bar.status_lbl.text())
        assert lab.pump(lambda: tool._pending_row is None, 900), (key, tool.verdict_lbl.text())
        assert lab.pump(lambda: tool.handles() is not None, 900), (key, tool.verdict_lbl.text())
        said = tool.row() == before
        change(tool)
        lab.judged(tool, key)
        t0 = time.time()
        tool.accept_btn.click()
        assert lab.pump(lambda: bar._edit is None and tool._job is None, 3600), (key, bar.status_lbl.text(),
                                                                                lab.notes)
        jobs = [a[5] for a in lab.argvs[n0:]]
        rows = D.recipe_rows(draft)
        out = {"key": key, "said_back": said, "before": before, "after": rows[k], "status": bar.status_lbl.text(),
               "jobs": jobs, "s": round(time.time() - t0, 1)}
        recipe = OUT / f"{key}.toml"
        recipe.write_text(RC.dumps(rows), encoding="utf-8")
        composed = D.ensure_draft(GAME / SOURCE, game=GAME, root=OUT / f"composed-{key}")
        t1 = time.time()
        r = subprocess.run([sys.executable, "-m", "ff9mapkit", "--game", str(GAME), "world-fuse", str(recipe),
                            "--mod-folder", str(composed)], cwd=KIT, capture_output=True, text=True, timeout=7200)
        assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-1500:]
        ed, cd = _world(draft), _world(composed)
        diff = sorted(x for x in set(ed) | set(cd) if ed.get(x) != cd.get(x))
        out.update(I1={"identical": not diff, "differing": diff[:12], "files": len(ed)},
                   compose_s=round(time.time() - t1, 1))
        print(f"{key}: said back {said}; {RC.label(before)} -> {RC.label(rows[k])}; {out['s']} s, jobs {jobs}\n"
              f"  {out['status']}\n  I1 {'IDENTICAL' if not diff else 'DIFFERS ' + str(diff[:6])} over {len(ed)} "
              f"world files (compose {out['compose_s']} s)")
        edits.append(out)
        PREP.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
        shutil.rmtree(composed, ignore_errors=True)
        assert said and not diff and bar.status_lbl.property("state") == "ok", out

    # E1: the sink onto the second island
    edit(0, *S1["at"], lambda t: t.place(*S2["at"]), "E1")
    # E2: the morph one rung shallower (toward zero)
    step = CE.DEPTH_STEP if mdepth < 0 else -CE.DEPTH_STEP
    edit(1, 64.0 * mcell[0] + 32.0, -(64.0 * mcell[1] + 32.0), lambda t: t.depth.setValue(mdepth + step), "E2")
    # E3: the river onto the next free placement, or as it stood
    h = D.history(draft)
    cells = h["steps"][2]["cells"]
    b = tuple(cells[0])

    def move(t):
        nxt = RE.free_shifts(rs, river_at=t.river_at(),
                             occupied=lambda cs: {c: sorted(t._river[2][c]) for c in cs if c in t._river[2]})
        nxt = [s for s in nxt if not RE.same_shift(s, free[0])]
        rec["R_next"] = [list(s) for s in nxt]
        if nxt:
            t.place(*RE.centre(rs, nxt[0]))
    edit(2, 64.0 * b[0] + 32.0, -(64.0 * b[1] + 32.0), move, "E3")
    rec["draft"] = str(draft)
    PREP.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    print(f"-> {PREP}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["build"]:
        build()
    else:
        raise SystemExit(__doc__)
