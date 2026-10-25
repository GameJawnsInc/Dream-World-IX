"""Lane chain: build the 5-step draft every other chain_ probe copies, through the REAL cards and runners (c11_lab's
path), into OUT/build/drafts; then copy it to OUT/gold (copy2: mtimes kept).

    py studies/overworld-editor/perf/chain_build.py

Steps: H a hill on the lawn nearest the Landing Site; H2 a second hill 40-64u from H (its read window holds H's
blocks, so an edit of H must RE-RUN it: the put-back's world-fuse lane); I an island (r24 seed 5) on open ocean far
from H; T the beach block (7,17) carried onto a free block far from H; S the first clean sink candidate far from H.
Records each Accept's wall (click -> job done) and the GUI-thread time inside draft.begin_step / commit_step (the
card calls both on the GUI thread; the sink card snapshots the whole map), with the event loop's longest freeze.
Writes nothing outside OUT: the cards' jobs write the draft (an absolute --mod-folder under OUT).
"""
from __future__ import annotations

import math
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_common as CC                                             # noqa: E402

GAME, SOURCE = CC.GAME, CC.SOURCE
BUILD = CC.OUT / "build"


class Lab:
    """RecipeBar + the four cards, wired as WorldDoc wires them (on_changed = WorldDoc._draft_changed minus the 3D
    view's reload: the bar refreshes and every built card's island_changed runs)."""

    def __init__(self, drafts, tools=("hill", "island", "transplant", "sink")):
        self.app = CC.qapp()
        self.loop = CC.Loop(self.app)
        from ff9mapkit.editor.theme import pick_palette
        from ff9mapkit.workspace.worldforest import QProcessRunner
        from ff9mapkit.workspace.worldview3d import WorldView3DPanel
        from ff9mapkit.workspace.worldrecipe import RecipeBar
        pal = pick_palette("dark")
        self.argvs = []

        def logged():
            r = QProcessRunner()
            real = r.start

            def start(argv, cwd, done):
                self.argvs.append({"argv": [str(a) for a in argv], "t0": time.perf_counter()})
                rec = self.argvs[-1]

                def fin(code, text, done=done):
                    rec["s"] = time.perf_counter() - rec["t0"]
                    rec["code"] = code
                    done(code, text)
                real(argv, cwd, fin)
            r.start = start
            return r
        self.panel = WorldView3DPanel(pal)
        classes = {}
        from ff9mapkit.workspace.worldhill import HillTool
        from ff9mapkit.workspace.worldisland import IslandTool
        from ff9mapkit.workspace.worldsink import SinkTool
        from ff9mapkit.workspace.worldtransplant import TransplantTool
        classes.update(hill=HillTool, island=IslandTool, transplant=TransplantTool, sink=SinkTool)
        kw = dict(game_fn=lambda: GAME, source_fn=lambda: SOURCE, drafts_root=drafts, on_changed=self.draft_changed)
        self.tools = {k: classes[k](pal, self.panel, runner=logged(), **kw) for k in tools}
        self.bar = RecipeBar(pal, game_fn=lambda: GAME, source_fn=lambda: SOURCE, runner=logged(),
                             drafts_root=drafts, on_changed=self.draft_changed, on_edit=self._edit,
                             ask=lambda t, x: True)

    def draft_changed(self, _draft):
        """WorldDoc._draft_changed, without the 3D page's reload."""
        self.bar.refresh()
        for t in self.tools.values():
            t.island_changed()

    def _edit(self, row, label):
        tool = self.tools[row["table"]]
        tool.open_tool()
        tool.edit_row(row, label=label, on_accepted=self.bar.edit_accepted, on_cancel=self.bar.cancel_edit)

    def pump(self, until, sec):
        return self.loop.run(until, sec)

    def accept(self, tool, at, key):
        tool.place(*at, 0.0)
        r = self.pump(lambda: tool._current_verdict() is not None, 900)
        assert r["ok"], (key, tool.verdict_lbl.text())
        assert tool.accept_btn.isEnabled(), (key, tool.verdict_lbl.text())
        t0 = time.perf_counter()
        tool.accept_btn.click()
        click = time.perf_counter() - t0
        r = self.pump(lambda: tool._job is None and tool.center is None, 1800)
        assert r["ok"], (key, tool.verdict_lbl.text())
        r["click_s"] = round(click, 4)
        r["accept_s"] = round(time.perf_counter() - t0, 2)
        tool.close_tool()
        return r


def build():
    from ff9mapkit.world import draft as D, hilledit as HE, islandedit as IE, mesh as M
    from ff9mapkit.world import river as RV, sinkedit as SE, transplantedit as TE
    if BUILD.exists():
        shutil.rmtree(BUILD)
    if CC.GOLD.exists():
        shutil.rmtree(CC.GOLD)
    drafts = CC.assert_outside_game(BUILD / "drafts")
    calls = CC.Calls(D, ["begin_step", "commit_step", "abort_step", "ensure_draft", "edited_blocks", "stale",
                         "last_promote", "edits", "removals", "read_meta", "history"])
    lab = Lab(drafts)
    hill = lab.tools["hill"]
    hill.open_tool()
    assert lab.pump(lambda: hill._ix is not None, 300)["ok"]
    k = (326.16, -569.09)                                              # the Landing Site
    fam = HE._fam(hill._ix)
    mains = hill._ix.cent[fam == "main"]
    spots = sorted({(round(x / 8) * 8.0, round(z / 8) * 8.0) for x, z in mains[::5]}, key=lambda c: math.dist(c, k))
    H = next(c for c in spots if HE.preview(hill._ix, c, 4.2, 18.0)["ok"])
    out = {"H": H}
    m0 = calls.mark()
    out["accept_H"] = lab.accept(hill, H, "H")
    out["calls_H"] = calls.summary(m0)
    hill.open_tool()                                                   # the draft's island now (H in it)
    assert lab.pump(lambda: hill._ix is not None, 300)["ok"]
    near = sorted((c for c in spots if 40.0 <= math.dist(c, H) <= 64.0), key=lambda c: math.dist(c, H))
    H2 = next(c for c in near if HE.preview(hill._ix, c, 4.2, 18.0)["ok"])
    out["H2"] = H2
    m0 = calls.mark()
    out["accept_H2"] = lab.accept(hill, H2, "H2")
    out["calls_H2"] = calls.summary(m0)
    land = IE.stock_land(game=GAME)
    stack = [GAME / f for f in RV.stack_folders(GAME) if f != CC.SOURCE_NAME]
    far = {((H[0] // 64) + dx) % 24 for dx in range(-3, 4)}, {int(-H[1] // 64) + dy for dy in range(-3, 4)}

    def away(b):
        return not (b[0] in far[0] and b[1] in far[1])

    def occupied(blocks):
        d = hill.draft() or SOURCE
        return {tuple(b): ["x"] for b in blocks if any(M.existing_overrides([tuple(b)], str(fo), disc=dd, game=GAME)
                                                       for fo in [d] + stack for dd in (1, 4))}
    isl = next(c for c in ((64.0 * bx + 32.0, -(64.0 * by + 32.0)) for by in range(2, 18) for bx in range(24))
               if away((int(c[0] // 64), int(-c[1] // 64)))
               and IE.preview(IE.outline(c, radius=24.0, seed=5.0), land=land, occupied=occupied)["ok"])
    it = lab.tools["island"]
    it.open_tool()
    it.seed.setValue(5)
    m0 = calls.mark()
    out["accept_I"] = lab.accept(it, isl, "I")
    out["calls_I"] = calls.summary(m0)
    out["I"] = isl
    cell = next(c for c in ((bx, by) for by in range(2, 18) for bx in range(24))
                if away(c) and TE.preview(c, land=land, occupied=occupied)["ok"])
    tt = lab.tools["transplant"]
    tt.open_tool()
    tt.donor_box.setCurrentIndex(tt.donor_box.findData("7,17"))
    m0 = calls.mark()
    out["accept_T"] = lab.accept(tt, (64.0 * cell[0] + 32.0, -(64.0 * cell[1] + 32.0)), "T")
    out["calls_T"] = calls.summary(m0)
    out["T"] = cell
    row = next(r for r in SE.candidates(GAME) if SE.verdict(r)["ok"]
               and all(away(tuple(b)) for b in r.get("blocks") or []))
    st = lab.tools["sink"]
    st.open_tool()
    assert lab.pump(lambda: st._outlines.get("islands") is not None or st._outlines, 300)["ok"]
    m0 = calls.mark()
    out["accept_S"] = lab.accept(st, tuple(row["at"]), "S")
    out["calls_S"] = calls.summary(m0)
    out["S"] = row["at"]
    draft = hill.draft()
    out["rows"] = D.recipe_rows(draft)
    out["jobs"] = [{"verb": a["argv"][5] if len(a["argv"]) > 5 else a["argv"], "s": round(a.get("s", -1), 2),
                    "code": a.get("code")} for a in lab.argvs]
    assert [r["table"] for r in out["rows"]] == ["hill", "hill", "island", "transplant", "sink"], out["rows"]
    calls.restore()
    shutil.copytree(BUILD / "drafts", CC.GOLD)       # GOLD is a drafts root: <GOLD>/FF9CustomMap-world.draft
    out["gold"] = str(CC.GOLD)
    out["t"] = time.strftime("%Y-%m-%d %H:%M:%S")
    CC.save("build.json", out)
    for key in ("H", "H2", "I", "T", "S"):
        a = out[f"accept_{key}"]
        c = {k: v for k, v in out[f"calls_{key}"].items() if k.startswith(("begin_step", "commit_step"))}
        print(key, "accept", a["accept_s"], "s; click", a["click_s"], "s; max GUI gap", a["max_gap"], c)


if __name__ == "__main__":
    build()
