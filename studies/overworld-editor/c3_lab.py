"""Rung C3 on the real island: the recipe the World tab saves composes, through the CLI, to the bytes the tab wrote.

    py studies/overworld-editor/c3_lab.py

THE EDITOR'S PATH (as C1 and C2): the real ForestTool and MountainTool, with their real runners (world-forest /
world-mountain subprocesses), place a forest and then a turned, heightened mountain into a fresh draft of
FF9CustomMap-world; the RecipeBar undoes the mountain and redoes it, and saves the recipe. Then:
  R1 `world-fuse <saved recipe> --mod-folder <a second fresh draft>` (the hand-typed CLI) writes every world file of
     the editor's draft byte for byte (the C3 acceptance);
  R2 the RecipeBar opens the saved recipe into a fresh draft (one world-fuse job per row) and gets the same bytes,
     with one undoable step per row;
  R3 undoing both steps puts that draft back to the folder exactly.
Nothing is written into the install (drafts live under out/c3_lab).
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
import c1_lab as C1                                                    # noqa: E402  (the paths)

GAME, KIT = C1.GAME, C1.KIT
SOURCE = "FF9CustomMap-world"
FOREST = (1400.0, -460.0), "13,15"                                    # C1's forest-grove spot, on the live folder
MOUNTAIN = (32.0, -528.0), 45, 1.3                                     # Uaho on the west island, turned + taller
OUT = HERE / "out" / "c3_lab"
RESULT = HERE / "out" / "c3_result.json"


def _world(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (root / "FF9_Data" / "WorldMap").rglob("*.ff9mesh") if ".bak-" not in p.name}


def main():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.world import draft as D
    from ff9mapkit.world import recipe as RC
    from ff9mapkit.workspace.worldforest import ForestTool, QProcessRunner
    from ff9mapkit.workspace.worldmountain import MountainTool
    from ff9mapkit.workspace.worldrecipe import RecipeBar
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    if OUT.exists():
        shutil.rmtree(OUT)
    drafts, saved = OUT / "drafts", OUT / "saved-recipe.toml"
    pal = pick_palette("dark")
    panel = WorldView3DPanel(pal)
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S")}

    def pump(until, sec):
        t = time.time()
        while time.time() - t < sec:
            app.processEvents()
            if until():
                return True
            time.sleep(0.02)
        return False

    tools = []
    bar = RecipeBar(pal, game_fn=lambda: GAME, source_fn=lambda: GAME / SOURCE, drafts_root=drafts,
                    on_changed=lambda d: [t.island_changed() for t in tools], ask=lambda t, x: True,
                    save_path_fn=lambda d: saved, open_path_fn=lambda: saved)
    forest = ForestTool(pal, panel, game_fn=lambda: GAME, source_fn=lambda: GAME / SOURCE, drafts_root=drafts,
                        runner=QProcessRunner(), on_changed=lambda d: bar.refresh())
    mountain = MountainTool(pal, panel, game_fn=lambda: GAME, source_fn=lambda: GAME / SOURCE, drafts_root=drafts,
                            runner=QProcessRunner(), on_changed=lambda d: bar.refresh())
    tools += [forest, mountain]

    def place(tool, x, z, donor, **handles):
        tool.donor_box.setCurrentIndex(tool.donor_box.findData(donor))
        tool.open_tool()
        assert pump(lambda: tool._ix is not None and tool.donor() in tool._outlines, 180), tool.verdict_lbl.text()
        for name, value in handles.items():
            getattr(tool, name).setValue(value)
        tool.place(x, z, 3.0)
        t0 = time.time()
        assert pump(lambda: tool._current_verdict() is not None, 240), tool.verdict_lbl.text()
        assert tool.accept_btn.isEnabled(), tool.verdict_lbl.text()
        t1 = time.time()
        tool.accept_btn.click()
        assert pump(lambda: tool._job is None and tool.center is None, 240), tool.verdict_lbl.text()
        tool.close_tool()
        return {"check_s": round(t1 - t0, 1), "accept_s": round(time.time() - t1, 1), "said": tool.verdict_lbl.text()}

    rec["forest"] = place(forest, *FOREST[0], FOREST[1])
    (mx, mz), angle, height = MOUNTAIN
    rec["mountain"] = place(mountain, mx, mz, "0,0", angle=angle, rock_height=height)
    draft = drafts / f"{SOURCE}.draft"
    edited = _world(draft)
    bar.refresh()
    rec["bar_after_two"] = bar.status_lbl.text()
    t = time.time()
    bar.undo()
    rec["undo_s"] = round(time.time() - t, 2)
    rec["undo_moved"] = _world(draft) != edited
    bar.redo()
    rec["redo_back"] = _world(draft) == edited
    bar.save()
    text = saved.read_text(encoding="utf-8")
    rec["recipe"] = text
    print(text)

    # R1: the CLI composes the saved recipe onto a second fresh draft of the same folder
    hand = D.ensure_draft(GAME / SOURCE, game=GAME, root=OUT / "hand")
    t = time.time()
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", "world-fuse", str(saved), "--mod-folder", str(hand)],
                       cwd=KIT, capture_output=True, text=True, timeout=900)
    rec["fuse_s"], rec["fuse_rc"] = round(time.time() - t, 1), r.returncode
    rec["fuse_out"] = r.stdout[-1500:] + r.stderr[-800:]
    hw = _world(hand)
    diff = sorted(k for k in set(hw) | set(edited) if hw.get(k) != edited.get(k))
    rec["R1"] = {"identical": r.returncode == 0 and not diff, "differing": diff, "files": len(edited),
                 "edited": D.edits(draft)}
    print(f"R1 the CLI's compose vs the editor's draft: {'IDENTICAL' if rec['R1']['identical'] else diff} over "
          f"{len(edited)} world files; the draft edited {len(rec['R1']['edited'])}")

    # R2: the bar opens the recipe into a fresh draft, a world-fuse job per row
    bar._runner = QProcessRunner()
    t = time.time()
    bar.open_recipe()
    assert pump(lambda: bar._queue is None, 900), bar.status_lbl.text()
    rec["open_s"] = round(time.time() - t, 1)
    h = D.history(draft)
    rec["R2"] = {"identical": _world(draft) == edited, "steps": [s["label"] for s in h["steps"]],
                 "cursor": h["cursor"], "said": bar.status_lbl.text(), "rows": RC.loads(text)}
    # R3: undo both
    bar.undo()
    bar.undo()
    # (judged on the draft's own trees: the live folder also holds disc trees a draft never copies)
    mine = _world(draft)
    rec["R3"] = {"back_to_the_folder": D.edits(draft) == [] and all(
        hashlib.sha256((GAME / SOURCE / rel).read_bytes()).hexdigest() == h for rel, h in mine.items()),
        "files": len(mine)}
    RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    print({k: rec[k] for k in ("forest", "mountain")})
    print("R2", rec["R2"]["identical"], rec["R2"]["steps"], "R3", rec["R3"])
    print(f"-> {RESULT}")
    assert rec["R1"]["identical"] and rec["R2"]["identical"] and rec["R3"]["back_to_the_folder"]


if __name__ == "__main__":
    main()
