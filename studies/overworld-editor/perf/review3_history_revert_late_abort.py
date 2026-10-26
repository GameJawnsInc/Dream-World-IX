"""Review-3 probe (history slice, 972cab25): undo, redo, promote, begin_step and begin_edit now finish a pending abort
first -- but REVERT does not. A pending left by a failed abort (its before-images taken when the draft was level
with the live folder after a promote) survives a Revert promote, which rebases the draft's disc-4 files at the
promoted cells back to the live folder's restored bytes. The next Undo then finishes the abort FIRST and writes the
post-promote disc-4 images back over them: the history says the step is applied with its recorded disc-4 bytes, the
draft holds others, and the Undo the refusal told the user to reach ("Revert promote first") refuses.

Hermetic: a fake game + drafts under studies/overworld-editor/out/perf/review3/revert_late_abort/. The real draft.py
(worktree package asserted). The disc-4 mirror is replaced by the tests' fake (copy disc 1 -> disc 4, add a Sea4):
the install's bundles are never read. The failed abort is a real Windows refusal: a reader holds the file the step
created, so the abort's unlink is refused past _retry's 3 s."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

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

OUT = WT / "studies" / "overworld-editor" / "out" / "perf" / "review3" / "revert_late_abort"
ROW = {"table": "forest", "center": [1.0, -1.0], "donor": "15,15"}
T00 = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[0][0] Terrain.ff9mesh"
T10 = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[1][0] Terrain.ff9mesh"
O10 = "FF9_Data/WorldMap/Disc1/0_1/r0/Block[1][0] Object.ff9mesh"
D4_00 = "FF9_Data/WorldMap/Disc4/0_1/r0/Block[0][0] Terrain.ff9mesh"
S4_00 = "FF9_Data/WorldMap/Disc4/0_1/r0/Block[0][0] Sea4.ff9mesh"


def fake_mirror(written, *, mod_folder, log=print, **_k):
    for p in written:
        p = Path(p)
        d4 = Path(str(p).replace("Disc1", "Disc4"))
        d4.parent.mkdir(parents=True, exist_ok=True)
        if d4.exists():
            M.park_backup(d4)
        d4.write_bytes(p.read_bytes())
        (d4.parent / d4.name.replace("Terrain", "Sea4")).write_bytes(b"sea for " + p.read_bytes()[:8])


DM.auto_mirror = fake_mirror


def setup(tag):
    out = OUT / tag
    if out.exists():
        shutil.rmtree(out)
    game = out / "GAME"
    src = game / "Src"
    for disc in (1, 4):
        row = src / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / "r0"
        row.mkdir(parents=True)
        for bx in range(2):
            (row / f"Block[{bx}][0] Terrain.ff9mesh").write_bytes(b"stock %d" % bx)
    return game, D.ensure_draft(src, game=game, root=out / "drafts")


def run(fail_abort: bool):
    game, d = setup("failed" if fail_abort else "control")
    quiet = lambda *a: None  # noqa: E731
    D.begin_step(d, [(0, 0)])                                   # step A: a forest at block (0,0)
    (d / T00).write_bytes(b"forest")
    D.commit_step(d, ROW, "forest one")
    D.promote(d, game=game, log=quiet)                          # A into the game; disc 4 mirrored there
    print(f"  after promote: draft disc-4 (0,0) = {(d / D4_00).read_bytes()!r}, Sea4 there: {(d / S4_00).exists()}")
    D.begin_step(d, [(0, 0), (1, 0)])                           # step B: half writes block (1,0), then refuses
    (d / T10).write_bytes(b"half")
    (d / O10).write_bytes(b"an object B made")
    if fail_abort:
        reader = open(d / O10, "rb")                            # a reader holds the file B made, past _retry
        try:
            D.abort_step(d)
            print("  abort went through (unexpected)")
        except OSError as e:
            print(f"  B's abort failed: {type(e).__name__}: {e.strerror}; pending left: "
                  f"{(d / D.HISTORY_DIR / D._PENDING / 'step.json').is_file()}")
        finally:
            reader.close()
    else:
        D.abort_step(d)
    D.revert(d, game=game, log=quiet)                           # Revert promote (the card's, or the C19 chain's)
    print(f"  after revert:  draft disc-4 (0,0) = {(d / D4_00).read_bytes()!r}, Sea4 there: {(d / S4_00).exists()}"
          f"; history promoted={D.history(d)['promoted']}")
    try:
        D.undo(d)                                               # "Revert promote first" -- done; now Undo A
        print(f"  undo A: ok; block (0,0) disc 1 = {(d / T00).read_bytes()!r}")
    except ValueError as e:
        print(f"  undo A REFUSED: {e}")
    h = D.history(d)
    a = h["steps"][0]
    print(f"  history: cursor={h['cursor']}; A's recorded disc-4 (0,0): "
          f"{a['after'].get(D4_00) == D._sha(game / 'Src' / D4_00)} == the live stock bytes, "
          f"Sea4 recorded: {S4_00 in a['after']}")
    print(f"  draft now: disc-4 (0,0) = {(d / D4_00).read_bytes()!r}, Sea4 there: {(d / S4_00).exists()}; "
          f"edits() = {D.edits(d)}")


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


def chain():
    """The C19 chain: Edit of the in-game step A after B's failed abort. The chain's revert runs first (no abort),
    then begin_edit finishes the abort -- over the cells the revert just rebased."""
    import io
    import os
    import contextlib
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])  # noqa: F841
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldrecipe import RecipeBar
    game, d = setup("chain")
    quiet = lambda *a: None  # noqa: E731
    D.begin_step(d, [(0, 0)])
    (d / T00).write_bytes(b"forest")
    D.commit_step(d, ROW, "forest one")
    D.promote(d, game=game, log=quiet)
    D.begin_step(d, [(0, 0), (1, 0)])
    (d / T10).write_bytes(b"half")
    (d / O10).write_bytes(b"an object B made")
    reader = open(d / O10, "rb")
    try:
        D.abort_step(d)
    except OSError as e:
        print(f"  B's abort failed: {type(e).__name__}")
    finally:
        reader.close()
    run_ = InProcess()
    bar = RecipeBar(pick_palette("dark"), game_fn=lambda: game, source_fn=lambda: game / "Src", runner=run_,
                    drafts_root=d.parent, ask=lambda *a: True)
    bar.select(0)
    with contextlib.redirect_stdout(io.StringIO()):
        bar.edit()                                              # Edit step A (in the game)
    print("  jobs:", [("revert" if "--revert" in a else "promote") for a in run_.argvs])
    print("  bar says:", bar.status_lbl.text())
    print(f"  editing: {bar._edit is not None}; history cursor={D.history(d)['cursor']} "
          f"promoted={D.history(d)['promoted']}")


if __name__ == "__main__":
    print("CONTROL (B's abort succeeds):")
    run(False)
    print("FAILED ABORT (B's abort refused, then Revert promote, then Undo):")
    run(True)
    print("FAILED ABORT, then Edit of the in-game step A (the C19 chain through the real RecipeBar):")
    chain()
