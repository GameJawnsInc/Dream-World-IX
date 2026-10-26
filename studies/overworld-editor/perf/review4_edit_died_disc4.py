"""Review-4 probe (585f6073): the 'died' disc-4 note is built in CarryTool._accepted AFTER the edit branch returns, so an
edit's Accept (the C9 / C12 lane: Edit a placed sink, Accept the edit) never says disc 4 may hold a half write. The
card closes, the bar says "Edited step 1 ...", and -- for an in-game step -- the chain promotes the half write.

Drives the REAL SinkTool + RecipeBar (offscreen) with the tests' Scripted runner: a sink accepted whole, then edited;
the edit's disc-4 call writes a disc-4 file and dies (no verdict4.json), as the round-3 H5 test's does.
Run from ff9mapkit/:
  py -m pytest ../studies/overworld-editor/perf/review4_edit_died_disc4.py -q -s -p no:cacheprovider
      --basetemp=../studies/overworld-editor/out/perf/review4/edit_died_disc4"""
from __future__ import annotations

from pathlib import Path

from ff9mapkit.world import draft as D
from tests.test_world_forestedit import _no_real_install  # noqa: F401
from tests.test_world_sink import world  # noqa: F401
from tests.test_worldsink import ROW, _sink_card

D4 = "FF9_Data/WorldMap/Disc4/0_1/r5/Block[5][5] Terrain.ff9mesh"


def test_an_edit_whose_disc4_call_died_says_nothing(world, tmp_path):  # noqa: F811
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldrecipe import RecipeBar
    from tests.test_worldforest import Scripted
    die = []

    def answer(kind, argv):
        if "--disc" in argv and kind == "accept" and die:              # the edit's disc-4 call: writes, then dies
            mod = Path(argv[argv.index("--mod-folder") + 1])
            (mod / D4).parent.mkdir(parents=True, exist_ok=True)
            (mod / D4).write_bytes(b"half a disc-4 sink")
            return None
        return {"ok": True, "dry_run": kind == "check", "at": [344.0, -360.0], "blocks": [[5, 5]], "written": [],
                "report": {"land_tris": 4}, "refused": None}
    run = Scripted(answer)
    tool, game, src = _sink_card(tmp_path, [ROW], run)
    tool.place(344.0, -360.0)
    tool._timer.stop()
    tool._check()
    tool.accept_btn.click()                                             # the sink, whole
    assert D.history(tool.draft())["cursor"] == 1
    bar = RecipeBar(pick_palette("dark"), game_fn=lambda: game, source_fn=lambda: src, runner=run,
                    drafts_root=tmp_path / "drafts", ask=lambda t, x: True,
                    on_edit=lambda row, label: (tool.open_tool(), tool.edit_row(
                        row, label=label, on_accepted=bar.edit_accepted, on_cancel=bar.cancel_edit)))
    bar.refresh()
    bar.select(0)
    bar.edit_btn.click()
    assert tool.editing(), bar.status_lbl.text()
    tool.entrances.setChecked(True)                                     # retune it
    tool._timer.stop()
    tool._check()
    assert tool.accept_btn.isEnabled(), tool.verdict_lbl.text()
    die.append(1)
    tool.accept_btn.click()                                             # Accept the edit: disc 4's call dies
    d = tool.draft()
    print("\nCARD (closed):", repr(tool.verdict_lbl.text()), "| hidden:", tool.isHidden())
    print("BAR:", bar.status_lbl.text())
    print("disc-4 half write in the draft:", (d / D4).read_bytes() if (d / D4).is_file() else None,
          "| recorded in step 1:", D4 in D.history(d)["steps"][0]["after"], "| edit closed:", D.history(d)["edit"] is None)
    assert "half write" not in tool.verdict_lbl.text() and "half write" not in bar.status_lbl.text()
