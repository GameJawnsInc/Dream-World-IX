"""Review-3 probe (history slice, 7efe9a47 + begin_edit's lift): Edit and Delete now catch an OSError from begin_edit
and close as "Not opened" / "Not deleted" -- meant for the pending abort begin_edit runs first, when nothing has
moved yet. But begin_edit also raises OSError AFTER its undo loop: the lift renames each step's folder into
history/edit/ with no _retry (a handle open in one is refused), and park.mkdir / _write_history can fail too. The
draft is then undone back to step k, the history still lists the steps as undone but a folder it names has moved
away, and nothing says so. In the in-game chain (rung C19) the bar's _closed then promotes "the recipe again": the
draft at step k -- the game loses steps k..fence-1, and the note says it has the recipe again.

Drives the REAL RecipeBar (offscreen Qt) with the tests' in-process runner: the chain's world-promote --revert and
world-promote run cli.main in this process. Hermetic: a fake game + drafts under
studies/overworld-editor/out/perf/review3/edit_lift_oserror/; the disc-4 mirror is the tests' fake (never the
install's bundles). The refused rename is a real Windows refusal: a reader holds one after-copy of step 3's folder."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = Path(__file__).resolve()
WT = HERE.parents[3]
sys.path.insert(0, str(WT / "ff9mapkit"))
from ff9mapkit import config  # noqa: E402
from ff9mapkit.world import discmirror as DM  # noqa: E402
from ff9mapkit.world import draft as D  # noqa: E402
from ff9mapkit.world import mesh as M  # noqa: E402

assert Path(D.__file__).resolve().is_relative_to(WT), D.__file__
for _n in ("_registry_candidates", "_steam_library_candidates", "_fallback_candidates"):   # never the real install
    setattr(config, _n, lambda: [])
config._read_user_config = lambda: {}
os.environ.pop("FF9_GAME_PATH", None)

OUT = WT / "studies" / "overworld-editor" / "out" / "perf" / "review3" / "edit_lift_oserror"
ROW = {"table": "forest", "center": [1.0, -1.0], "donor": "15,15"}


def rel(bx, disc=1):
    return f"FF9_Data/WorldMap/Disc{disc}/0_1/r0/Block[{bx}][0] Terrain.ff9mesh"


def fake_mirror(written, *, mod_folder, log=print, **_k):
    for p in written:
        p = Path(p)
        d4 = Path(str(p).replace("Disc1", "Disc4"))
        d4.parent.mkdir(parents=True, exist_ok=True)
        if d4.exists():
            M.park_backup(d4)
        d4.write_bytes(p.read_bytes())


DM.auto_mirror = fake_mirror


class InProcess:
    """The tests' runner: the job's argv run by cli.main in this process."""

    def __init__(self):
        self.argvs = []

    def start(self, argv, cwd, done):
        from ff9mapkit import cli
        self.argvs.append([str(a) for a in argv])
        done(cli.main([str(a) for a in argv[3:]]), "")

    def kill(self):
        pass

    def busy(self):
        return False


def main():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])  # noqa: F841
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldrecipe import RecipeBar
    if OUT.exists():
        shutil.rmtree(OUT)
    game = OUT / "GAME"
    src = game / "Src"
    for disc in (1, 4):
        row = src / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / "r0"
        row.mkdir(parents=True)
        for bx in range(3):
            (row / f"Block[{bx}][0] Terrain.ff9mesh").write_bytes(b"stock %d" % bx)
    drafts = OUT / "drafts"
    d = D.ensure_draft(src, game=game, root=drafts)
    for bx in range(3):                                          # steps 1-3: one block each
        D.begin_step(d, [(bx, 0)])
        (d / rel(bx)).write_bytes(b"step %d" % (bx + 1))
        D.commit_step(d, ROW, f"step {bx + 1}")
    D.promote(d, game=game, log=lambda *a: None)                 # all three in the game
    print("before the chain: live", [(src / rel(bx)).read_bytes() for bx in range(3)],
          "| history promoted", D.history(d)["promoted"])

    run = InProcess()
    bar = RecipeBar(pick_palette("dark"), game_fn=lambda: game, source_fn=lambda: src, runner=run,
                    drafts_root=drafts, ask=lambda *a: True)
    held = open(d / D.HISTORY_DIR / "0002" / "after" / rel(2, disc=4), "rb")   # a reader in step 3's folder
    try:
        bar.select(1)                                            # pick step 2 (in the game) ...
        bar.edit()                                               # ... Edit: revert, open, (refused), promote back
    finally:
        held.close()
    print("jobs run:", [a[a.index("world-promote"):][:1] + (["--revert"] if "--revert" in a else []) for a in run.argvs])
    print("bar says:", bar.status_lbl.text())
    print("after the chain: live", [(src / rel(bx)).read_bytes() for bx in range(3)])
    h = D.history(d)
    print(f"history: cursor={h['cursor']} promoted={h['promoted']} edit={h['edit']} owed={D.promote_owed(d)}")
    for i, s in enumerate(h["steps"]):
        print(f"  step {i + 1}: dir {s['dir']} exists={(d / s['dir']).is_dir()}")
    print("history/edit holds:", sorted(p.name for p in (d / D.HISTORY_DIR / D.EDIT_DIR).iterdir())
          if (d / D.HISTORY_DIR / D.EDIT_DIR).is_dir() else None)
    try:
        bar.redo()                                               # the user tries to get step 2 back
        print("redo: ok, cursor", D.history(d)["cursor"])
    except Exception as e:                                       # noqa: BLE001
        print(f"redo (the bar catches ValueError only): {type(e).__name__}: {e}")


def legacy():
    """No held handle: the state the kit before 2f02a533 left after a commit whose rename failed -- the undone steps'
    folders already deleted while the history still lists them (2f02a533's own message: "and the undone steps
    gone"). The next Edit of ANY step at or before them hits FileNotFoundError in the lift, after its undo loop."""
    out = OUT.parent / "edit_lift_legacy"
    if out.exists():
        shutil.rmtree(out)
    game = out / "GAME"
    src = game / "Src"
    row = src / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r0"
    row.mkdir(parents=True)
    for bx in range(2):
        (row / f"Block[{bx}][0] Terrain.ff9mesh").write_bytes(b"stock %d" % bx)
    d = D.ensure_draft(src, game=game, root=out / "drafts")
    for bx in range(2):
        D.begin_step(d, [(bx, 0)])
        (d / rel(bx)).write_bytes(b"step %d" % (bx + 1))
        D.commit_step(d, ROW, f"step {bx + 1}")
    D.undo(d)                                                    # step 2 undone (redo-able) ...
    shutil.rmtree(d / D.history(d)["steps"][1]["dir"])          # ... and its folder gone (the older kit's commit)
    try:
        D.begin_edit(d, 0)                                       # Edit step 1 (applied, its folder whole)
        print("  begin_edit: ok (unexpected)")
    except OSError as e:
        print(f"  begin_edit raised {type(e).__name__} -> the bar: 'Not opened: {e}.'")
    h = D.history(d)
    print(f"  history: cursor={h['cursor']} edit={h['edit']}; step 1 dir {h['steps'][0]['dir']} exists="
          f"{(d / h['steps'][0]['dir']).is_dir()}; draft block (0,0) = {(d / rel(0)).read_bytes()!r}")
    try:
        D.redo(d)
        print("  redo step 1: ok")
    except OSError as e:
        print(f"  redo step 1: {type(e).__name__} -- step 1, an APPLIED step, can no longer come back")


if __name__ == "__main__":
    main()
    print("LEGACY STATE (no handle held):")
    legacy()
