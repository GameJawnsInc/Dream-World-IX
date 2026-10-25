"""Rung C13 on real bytes: an edit whose later coast morph and river move REPLAY instead of running again.

    py studies/overworld-editor/c13_lab.py build

THE EDITOR'S PATH, as c11_lab: the real RecipeBar and the real hill, coast and river cards with their real runners
against the real install, wired as the World tab wires them, into a draft of FF9CustomMap-world:
  H a hill on the lawn nearest the Landing Site (the step to edit),
  M a coast morph at the first lawful window of a coastal block no folder overrides, far from H,
  R the river moved to its first placement free of edits, far from H;
then H is picked, opened with Edit, moved 8u and accepted. Before C13 a morph's and a river's read window was the
whole world, so both ran again (two world-fuse jobs, about fifty seconds each); now each replays when the edit
touched nothing it reads.
  R0: the put-back ran no world-fuse job (2 replayed, 0 composed again);
  I1: the edited draft == world-fuse of the edited recipe composed onto a fresh draft of the folder, over every world
      file -- the replayed bytes are the bytes a re-run writes;
  timings: the put-back against that compose (which runs all three rows).
No game: the replay restores the very bytes the cards accepted, and I1 holds them to the composed path.
"""
from __future__ import annotations

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
import c12_lab as C12                                                  # noqa: E402  (the world hash, the waits)

GAME, KIT = C1.GAME, C1.KIT
SOURCE = "FF9CustomMap-world"
OUT = HERE / "out" / "c13_lab"
PREP = HERE / "out" / "c13_prep.json"


class Lab(C12.Lab):
    def __init__(self, drafts):
        super().__init__(drafts)
        from ff9mapkit.editor.theme import pick_palette
        from ff9mapkit.workspace.worldforest import QProcessRunner
        from ff9mapkit.workspace.worldhill import HillTool
        pal = pick_palette("dark")
        r = QProcessRunner()
        real = r.start

        def start(argv, cwd, done):
            self.argvs.append([str(a) for a in argv])
            real(argv, cwd, done)
        r.start = start
        self.tools["hill"] = HillTool(pal, self.tools["sink"].panel, runner=r, game_fn=lambda: GAME,
                                      source_fn=lambda: GAME / SOURCE, drafts_root=drafts,
                                      on_changed=lambda d: self.bar.refresh())


def build():
    from ff9mapkit.world import coastedit as CE
    from ff9mapkit.world import draft as D
    from ff9mapkit.world import hilledit as HE
    from ff9mapkit.world import recipe as RC
    from ff9mapkit.world import riveredit as RE
    from ff9mapkit.world import sinkedit as SE
    if OUT.exists():
        shutil.rmtree(OUT)
    lab = Lab(OUT / "drafts")
    hill, coast, river = lab.tools["hill"], lab.tools["morph"], lab.tools["river"]
    T = {}

    # -- the river first: where it stands and its first free placement (the folder holds all the others)
    river.open_tool()
    assert lab.pump(lambda: river._river is not None, 900), river.from_lbl.text()
    rs, at0, held = river._rs(), river.river_at(), river._river[2]
    free = RE.free_shifts(rs, river_at=at0, occupied=lambda cs: {c: sorted(held[c]) for c in cs if c in held})
    assert free, "no placement of the river is free"
    rcells = {tuple(c) for s in (at0, free[0]) for c in rs.cells_at(s)}
    river.close_tool()

    # -- H on the lawn nearest the Landing Site whose block and the three round it touch none of the river's
    hill.open_tool()
    assert lab.pump(lambda: hill._ix is not None, 300)
    k = C1.CONTROL[1:]
    fam = HE._fam(hill._ix)
    mains = hill._ix.cent[fam == "main"]
    spots = sorted({(round(x / 8) * 8.0, round(z / 8) * 8.0) for x, z in mains[::5]}, key=lambda c: math.dist(c, k))

    def around(c):
        return {((int(c[0] // 64) + dx) % 24, int(-c[1] // 64) + dy) for dx in range(-3, 4) for dy in range(-3, 4)}
    H = next(c for c in spots if not around(c) & rcells and HE.preview(hill._ix, c, 4.2, 18.0)["ok"])
    near = around(H)
    hill.place(*H, 0.0)
    lab.judged(hill, "H")
    T["H"] = lab.accept(hill, "H")
    hill.close_tool()
    keep_off = near | rcells
    occupied = C12._occupied_fn(GAME, lambda: hill.draft())
    pick, tried = None, []
    for r in SE.candidates(GAME):
        for b in r.get("blocks") or []:
            b = tuple(b)
            if pick or len(tried) >= 24 or b in keep_off or b in tried or occupied(b):
                continue
            tried.append(b)
            pick = next(((b, w, v) for w in CE.windows(GAME, b) for v in CE.lawful(w)), None)
    assert pick, f"no coastal block with a lawful window in {tried}"
    mcell, mwin, mverb = pick
    lo, hi = CE.lawful(mwin)[mverb]
    mdepth = hi if hi > 0 else lo
    print(f"placing: H {H}, M {mverb} {mdepth:g} at block {mcell}, R from {RE.offset_of(at0)} to "
          f"{RE.offset_of(free[0])}")
    river.close_tool()
    coast.open_tool()
    coast.place(*CE.anchor(mwin, mverb))
    assert lab.pump(lambda: coast._window is not None, 600), coast.window_lbl.text()
    coast.verb_box.setCurrentIndex(coast.verb_box.findData(mverb))
    coast.depth.setValue(mdepth)
    assert coast.verb() == mverb and coast.depth.value() == mdepth
    lab.judged(coast, "M")
    T["M"] = lab.accept(coast, "M")
    coast.close_tool()
    river.open_tool()
    assert lab.pump(lambda: river._river is not None, 900), river.from_lbl.text()
    river.place(*RE.centre(rs, free[0]))
    lab.judged(river, "R")
    T["R"] = lab.accept(river, "R")
    river.close_tool()
    draft = hill.draft()
    rows0 = D.recipe_rows(draft)
    print(f"placed: {[RC.label(r) for r in rows0]}; accepts {T}")
    assert [r["table"] for r in rows0] == ["hill", "morph", "river"], rows0

    # -- the edit: pick H, Edit, move it 8u, Accept; the bar puts M and R back
    bar = lab.bar
    bar.refresh()
    assert bar.pick(H[0] + 0.7, H[1] - 0.4) == 0, bar.status_lbl.text()
    bar.edit_btn.click()
    assert hill.editing() and lab.pump(lambda: hill._ix is not None, 300)
    H2 = next(c for c in sorted(((H[0] + dx, H[1] + dz) for dx in (-8, 0, 8) for dz in (-8, 0, 8) if dx or dz),
                                key=lambda c: math.dist(c, H)) if HE.preview(hill._ix, c, 4.2, 18.0)["ok"])
    n_jobs = len(lab.argvs)
    hill.place(*H2, 0.0)
    lab.judged(hill, "E")
    t0 = time.time()
    hill.accept_btn.click()
    assert lab.pump(lambda: bar._edit is None and hill._job is None, 3600), bar.status_lbl.text()
    t_edit = round(time.time() - t0, 1)
    jobs = [a[5] for a in lab.argvs[n_jobs:]]
    text = bar.status_lbl.text()
    print(f"edit: H to {H2}: accept + put back {t_edit} s; jobs {jobs}\n  {text}")
    rows = D.recipe_rows(draft)
    assert rows[1:] == rows0[1:] and rows[0]["center"] == [H2[0], H2[1]], rows
    r0 = jobs.count("world-fuse") == 0 and "2 as they were, 0 composed again" in text
    recipe = OUT / "edited.toml"
    recipe.write_text(RC.dumps(rows), encoding="utf-8")
    composed = D.ensure_draft(GAME / SOURCE, game=GAME, root=OUT / "composed")
    t0 = time.time()
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", "--game", str(GAME), "world-fuse", str(recipe),
                        "--mod-folder", str(composed)], cwd=KIT, capture_output=True, text=True, timeout=3600)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-1500:]
    t_compose = round(time.time() - t0, 1)
    ed, cd = C12._world(draft), C12._world(composed)
    d1 = sorted(x for x in set(ed) | set(cd) if ed.get(x) != cd.get(x))
    print(f"R0 no world-fuse in the put-back: {r0}; I1 recipe: {'IDENTICAL' if not d1 else 'DIFFERS ' + str(d1[:6])}"
          f" over {len(ed)} world files; the compose of all three rows {t_compose} s vs the edit's accept + put back "
          f"{t_edit} s")
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "H": H, "H2": H2, "M": {"cell": mcell, "verb": mverb,
           "depth": mdepth}, "R": [list(at0), list(free[0])], "accept_s": T, "rows0": rows0, "rows": rows,
           "edit": {"jobs": jobs, "text": text, "s": t_edit}, "R0": r0,
           "I1": {"identical": not d1, "differing": d1, "files": len(ed)}, "compose_s": t_compose, "draft": str(draft)}
    PREP.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    print(f"-> {PREP}")
    assert r0 and not d1


if __name__ == "__main__":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if sys.argv[1:2] == ["build"]:
        build()
    else:
        raise SystemExit(__doc__)
