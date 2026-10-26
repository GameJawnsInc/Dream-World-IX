"""Review-3 SKEPTIC probe for R3-H5 (7c8c69c4): a two-call Accept (the sink) whose disc-4 leg WROTE a disc-4 file and
then died without a verdict4.json. Does the card commit it and say "disc 4 keeps its own ground"?

Drives the REAL SinkTool (offscreen) with the tests' Scripted runner and synthetic world (tests/test_world_sink.py's
fixture); the disc-4 answer writes one disc-4 override into the draft and returns no verdict (a died job). Hermetic:
pytest's tmp_path; never the install (the tests' _no_real_install autouse fixture).

Run from ff9mapkit/:  py -m pytest ../studies/overworld-editor/perf/review3_skeptic_h5_died_disc4.py -q -s -p no:cacheprovider
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from ff9mapkit.world import draft as D
from tests.test_world_forestedit import _no_real_install  # noqa: F401
from tests.test_world_sink import world  # noqa: F401
from tests.test_worldsink import ROW, _drafts

D4 = "FF9_Data/WorldMap/Disc4/0_1/r5/Block[5][5] Terrain.ff9mesh"


def test_died_disc4_leg_is_committed_and_called_refused(world, tmp_path):  # noqa: F811
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldsink import SinkTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    from tests.test_worldforest import Scripted

    def answer(kind, argv):
        if "--disc" in argv and kind == "accept":                       # the disc-4 leg: writes, then dies
            mod = Path(argv[argv.index("--mod-folder") + 1])
            p = mod / D4
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"half a disc-4 sink")
            return None                                                 # no verdict4.json: the job died
        return {"ok": True, "dry_run": kind == "check", "at": [344.0, -360.0], "blocks": [[5, 5]],
                "written": [], "report": {"land_tris": 4}, "refused": None}
    run = Scripted(answer)
    game, src = _drafts(tmp_path)
    tool = SinkTool(pick_palette("dark"), WorldView3DPanel(pick_palette("dark")), game_fn=lambda: game,
                    source_fn=lambda: src, runner=run, drafts_root=tmp_path / "drafts", sync=True,
                    outline_fn=lambda d: [ROW])
    tool.open_tool()
    tool.place(344.0, -360.0)
    tool._timer.stop()
    tool._check()
    tool.accept_btn.click()
    d = tool.draft()
    h = D.history(d)
    print("\njobs:", [("disc4" if "--disc" in a else "disc1") + ("-dry" if "--dry-run" in a else "") for a in run.argvs])
    print("card says:", tool.verdict_lbl.text(), "| state:", tool.verdict_lbl.property("state"))
    print("history cursor:", h["cursor"], "| step after holds the disc-4 write:",
          D4 in (h["steps"][-1]["after"] if h["steps"] else {}))
    print("draft disc-4 file:", (d / D4).read_bytes() if (d / D4).is_file() else None)
    print("edits():", D.edits(d))
    assert "disc 4 keeps its own ground" in tool.verdict_lbl.text()
    assert h["cursor"] == 1 and D4 in h["steps"][-1]["after"]
