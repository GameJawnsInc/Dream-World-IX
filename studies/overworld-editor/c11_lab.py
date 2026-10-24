"""Rung C11 on real bytes: an edit whose later island, carry and sink steps REPLAY instead of running again.

    py studies/overworld-editor/c11_lab.py build

THE EDITOR'S PATH, as c9_lab: the real RecipeBar and the real cards (hill, island, carry, sink) with their real
runners against the real install, wired as the World tab wires them, into a draft of FF9CustomMap-world:
  H a hill on the lawn nearest the Landing Site (the step to edit),
  I an island (radius 24, seed 5) on the first open-ocean block the card calls lawful, far from H,
  T the beach island (7,17) carried onto the first free block, far from H and I,
  S the first island the sink card calls clean, far from H;
then H is picked, opened with Edit, moved 8u and accepted. Before C11 the island, carry and sink rows had the whole
world as their read window, so all three ran again (three world-fuse jobs); now each replays when the edit touched
nothing it reads.
  R0: the put-back ran no world-fuse job (3 replayed, 0 composed again);
  I1: the edited draft == world-fuse of the edited recipe composed onto a fresh draft of the folder, over every
      world file -- the replayed bytes are the bytes a re-run writes;
  timings: the put-back against that compose (which runs all four rows).
No game: the replay restores the very bytes the cards accepted, and I1 holds them to the composed path, which every
earlier rung walked in game.
"""
from __future__ import annotations

import hashlib
import json
import math
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
OUT = HERE / "out" / "c11_lab"
PREP = HERE / "out" / "c11_prep.json"


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
        from ff9mapkit.workspace.worldforest import QProcessRunner
        from ff9mapkit.workspace.worldhill import HillTool
        from ff9mapkit.workspace.worldisland import IslandTool
        from ff9mapkit.workspace.worldrecipe import RecipeBar
        from ff9mapkit.workspace.worldsink import SinkTool
        from ff9mapkit.workspace.worldtransplant import TransplantTool
        from ff9mapkit.workspace.worldview3d import WorldView3DPanel
        pal = pick_palette("dark")
        self.argvs = []

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
        self.tools = {"hill": HillTool(pal, panel, runner=logged(), **kw),
                      "island": IslandTool(pal, panel, runner=logged(), **kw),
                      "transplant": TransplantTool(pal, panel, runner=logged(), **kw),
                      "sink": SinkTool(pal, panel, runner=logged(), **kw)}
        self.bar = RecipeBar(pal, game_fn=lambda: GAME, source_fn=lambda: GAME / SOURCE, runner=logged(),
                             drafts_root=drafts, on_changed=lambda d: [t.island_changed() for t in self.tools.values()],
                             on_edit=self._edit, ask=lambda t, x: True)

    def _edit(self, row, label):
        tool = self.tools[row["table"]]
        tool.open_tool()
        tool.edit_row(row, label=label, on_accepted=self.bar.edit_accepted, on_cancel=self.bar.cancel_edit)

    def pump(self, until, sec):
        t = time.time()
        while time.time() - t < sec:
            self.app.processEvents()
            if until():
                return True
            time.sleep(0.02)
        return False

    def accept(self, tool, at, key):
        tool.place(*at, 0.0)
        assert self.pump(lambda: tool._current_verdict() is not None, 600), (key, tool.verdict_lbl.text())
        assert tool.accept_btn.isEnabled(), (key, tool.verdict_lbl.text())
        t0 = time.time()
        tool.accept_btn.click()
        assert self.pump(lambda: tool._job is None and tool.center is None, 900), (key, tool.verdict_lbl.text())
        tool.close_tool()
        return round(time.time() - t0, 1)


def build():
    from ff9mapkit.world import draft as D, hilledit as HE, islandedit as IE, mesh as M, recipe as RC
    from ff9mapkit.world import river as RV, sinkedit as SE, transplantedit as TE
    if OUT.exists():
        shutil.rmtree(OUT)
    lab = Lab(OUT / "drafts")
    hill = lab.tools["hill"]
    hill.open_tool()
    assert lab.pump(lambda: hill._ix is not None, 300)
    k = C1.CONTROL[1:]
    fam = HE._fam(hill._ix)
    mains = hill._ix.cent[fam == "main"]
    spots = sorted({(round(x / 8) * 8.0, round(z / 8) * 8.0) for x, z in mains[::5]}, key=lambda c: math.dist(c, k))
    H = next(c for c in spots if HE.preview(hill._ix, c, 4.2, 18.0)["ok"])
    land = IE.stock_land(game=GAME)
    stack = [GAME / f for f in RV.stack_folders(GAME) if f != SOURCE]
    far = {((H[0] // 64) + dx) % 24 for dx in range(-3, 4)}, {int(-H[1] // 64) + dy for dy in range(-3, 4)}

    def away(b):
        return not (b[0] in far[0] and b[1] in far[1])

    def occupied(blocks):
        d = hill.draft() or GAME / SOURCE
        return {tuple(b): ["x"] for b in blocks if any(M.existing_overrides([tuple(b)], str(fo), disc=dd, game=GAME)
                                                       for fo in [d] + stack for dd in (1, 4))}
    timings = {"H": lab.accept(hill, H, "H")}
    isl = next(c for c in ((64.0 * bx + 32.0, -(64.0 * by + 32.0)) for by in range(2, 18) for bx in range(24))
               if away((int(c[0] // 64), int(-c[1] // 64)))
               and IE.preview(IE.outline(c, radius=24.0, seed=5.0), land=land, occupied=occupied)["ok"])
    it = lab.tools["island"]
    it.open_tool()
    it.seed.setValue(5)
    timings["I"] = lab.accept(it, isl, "I")
    cell = next(c for c in ((bx, by) for by in range(2, 18) for bx in range(24))
                if away(c) and TE.preview(c, land=land, occupied=occupied)["ok"])
    tt = lab.tools["transplant"]
    tt.open_tool()
    tt.donor_box.setCurrentIndex(tt.donor_box.findData("7,17"))
    timings["T"] = lab.accept(tt, (64.0 * cell[0] + 32.0, -(64.0 * cell[1] + 32.0)), "T")
    row = next(r for r in SE.candidates(GAME) if SE.verdict(r)["ok"]
               and all(away(tuple(b)) for b in r.get("blocks") or []))
    st = lab.tools["sink"]
    st.open_tool()
    assert lab.pump(lambda: st._outlines.get("islands") is not None or st._outlines, 300)
    timings["S"] = lab.accept(st, tuple(row["at"]), "S")
    draft = hill.draft()
    rows0 = D.recipe_rows(draft)
    print(f"placed: H {H}, I {isl}, T {cell}, S {row['at']}: accepts {timings}")
    assert [r["table"] for r in rows0] == ["hill", "island", "transplant", "sink"], rows0
    # the edit: pick H, Edit, move it 8u, Accept; the bar puts I, T, S back
    bar = lab.bar
    assert bar.pick(H[0] + 0.7, H[1] - 0.4) == 0, bar.status_lbl.text()
    bar.edit_btn.click()
    assert hill.editing() and lab.pump(lambda: hill._ix is not None, 300)
    H2 = next(c for c in sorted(((H[0] + dx, H[1] + dz) for dx in (-8, 0, 8) for dz in (-8, 0, 8) if dx or dz),
                                key=lambda c: math.dist(c, H)) if HE.preview(hill._ix, c, 4.2, 18.0)["ok"])
    n_jobs = len(lab.argvs)
    hill.place(*H2, 0.0)
    assert lab.pump(lambda: hill._current_verdict() is not None, 300), hill.verdict_lbl.text()
    t0 = time.time()
    hill.accept_btn.click()
    assert lab.pump(lambda: bar._edit is None and hill._job is None, 1800), bar.status_lbl.text()
    t_edit = round(time.time() - t0, 1)
    jobs = [a[5] for a in lab.argvs[n_jobs:]]
    text = bar.status_lbl.text()
    print(f"edit: H to {H2}: accept + put back {t_edit} s; jobs {jobs}\n  {text}")
    rows = D.recipe_rows(draft)
    assert rows[1:] == rows0[1:] and rows[0]["center"] == [H2[0], H2[1]], rows
    r0 = jobs.count("world-fuse") == 0 and "3 as they were, 0 composed again" in text
    recipe = OUT / "edited.toml"
    recipe.write_text(RC.dumps(rows), encoding="utf-8")
    composed = D.ensure_draft(GAME / SOURCE, game=GAME, root=OUT / "composed")
    t0 = time.time()
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", "--game", str(GAME), "world-fuse", str(recipe),
                        "--mod-folder", str(composed)], cwd=KIT, capture_output=True, text=True, timeout=3600)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-1500:]
    t_compose = round(time.time() - t0, 1)
    ed, cd = _world(draft), _world(composed)
    d1 = sorted(x for x in set(ed) | set(cd) if ed.get(x) != cd.get(x))
    print(f"R0 no world-fuse in the put-back: {r0}; I1 recipe: {'IDENTICAL' if not d1 else 'DIFFERS ' + str(d1[:6])}"
          f" over {len(ed)} world files; the compose of all four rows {t_compose} s vs the edit's accept + put back "
          f"{t_edit} s")
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "H": H, "H2": H2, "island": isl, "cell": cell, "sink": row["at"],
           "accept_s": timings, "rows0": rows0, "rows": rows, "edit": {"jobs": jobs, "text": text, "s": t_edit},
           "R0": r0, "I1": {"identical": not d1, "differing": d1, "files": len(ed)}, "compose_s": t_compose,
           "draft": str(draft)}
    PREP.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    print(f"-> {PREP}")
    assert r0 and not d1


if __name__ == "__main__":
    if sys.argv[1:2] == ["build"]:
        build()
    else:
        raise SystemExit(__doc__)
