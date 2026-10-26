"""Review-5 probe (81756cb1 R4-1): commit_step's history write refused, the folder's way back to pending refused, and
then its in-place take-back (_take_back over the commit-shaped folder) refused part way -- one reader (a scanner)
holding, through the commit, history.json, a file in the step's new folder, and a file the step created in the draft.
Every refusal is a real Windows one (Python open() handles: replace, directory rename and unlink are refused).

commit_step raises the take-back's error; the step's folder is left under history/ whole -- not pending, not in the
history -- and the draft keeps the step's writes. The card's take-back (abort_step) then finds no pending step and
returns cleanly, so the card says "the write was taken back and the draft is as it was".

Hermetic: studies/overworld-editor/out/perf/review5/commit_takeback_refused/.
Run: py studies/overworld-editor/perf/review5_commit_takeback_refused.py   (from the worktree root)"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
WT = HERE.parents[3]
sys.path.insert(0, str(WT / "ff9mapkit"))
from ff9mapkit.world import draft as D  # noqa: E402

assert Path(D.__file__).resolve().is_relative_to(WT), D.__file__
OUT = WT / "studies" / "overworld-editor" / "out" / "perf" / "review5" / "commit_takeback_refused"
ROW = {"table": "forest", "center": [1.0, -1.0], "donor": "15,15"}
ROWDIR = "FF9_Data/WorldMap/Disc1/0_1/r0"
T00, T10, O00 = (f"{ROWDIR}/Block[0][0] Terrain.ff9mesh", f"{ROWDIR}/Block[1][0] Terrain.ff9mesh",
                 f"{ROWDIR}/Block[0][0] Object.ff9mesh")


def _files(d):
    return {p.name: p.read_bytes() for p in (d / ROWDIR).iterdir() if p.is_file()}


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    game = OUT / "GAME"
    src = game / "Src"
    (src / ROWDIR).mkdir(parents=True)
    for bx in range(2):
        (src / ROWDIR / f"Block[{bx}][0] Terrain.ff9mesh").write_bytes(b"stock %d" % bx)
    d = D.ensure_draft(src, game=game, root=OUT / "drafts")
    D.begin_step(d, [(1, 0)])
    (d / T10).write_bytes(b"mountain")
    D.commit_step(d, ROW, "mountain one")
    before = _files(d)
    print("before the Accept:", before, "| cursor", D.history(d)["cursor"])

    D.begin_step(d, [(0, 0), (1, 0)])                    # the card's Accept: its snapshot, then the verb writes
    (d / T00).write_bytes(b"forest")
    (d / O00).write_bytes(b"forest's object")
    real, handles = D._write_history, []

    def scanner_arrives(draft, h):                       # the commit's history write: a reader holds three files
        home = Path(draft) / h["steps"][-1]["dir"]
        for p in (Path(draft) / D.HISTORY, home / "step.json", Path(draft) / O00):
            handles.append(open(p, "rb"))
        return real(draft, h)
    D._write_history = scanner_arrives
    try:
        D.commit_step(d, ROW, "forest two")
        print("commit_step went through (unexpected)")
    except OSError as e:
        print(f"commit_step raised {type(e).__name__}: {e}")
    finally:
        D._write_history = real
        for f in handles:
            f.close()
    print("pending step there for the card's take-back:", (d / D.HISTORY_DIR / D._PENDING / "step.json").is_file())
    D.abort_step(d)                                      # the card's _recorded -> abort_step: err2 None
    print("abort_step returned cleanly -> the card says: 'the write was taken back and the draft is as it was.'")
    h = D.history(d)
    print("history:", h["cursor"], [s["label"] for s in h["steps"]],
          "| folders under history/:", sorted(p.name for p in (d / D.HISTORY_DIR).iterdir()))
    now = _files(d)
    print("draft now:", now)
    print("draft == before the Accept:", now == before)
    D.begin_step(d, [(0, 0)])                            # the next step takes the unrecorded write as its baseline
    D.abort_step(d)
    print("after the next step's begin and abort, draft == before the Accept:", _files(d) == before)


if __name__ == "__main__":
    main()
