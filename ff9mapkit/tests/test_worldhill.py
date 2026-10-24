"""A grass hill from the World tab (overworld editor rung 6): the ghost IS the displacement ``world-hill`` writes, the
preview's laws agree with ``interior.build_hill`` gate for gate, the located refusals, ``world-hill --report-json``,
the command and its recipe row, and the card."""
from __future__ import annotations

import json
import os

import numpy as np
import pytest

from ff9mapkit import cli
from ff9mapkit.world import draft as D
from ff9mapkit.world import hilledit as HE
from ff9mapkit.world import interior as IN
from ff9mapkit.world import recipe as RC
from ff9mapkit.world.extract import CH_POS
from ff9mapkit.world.forestedit import SoupIndex

from .test_world_forestedit import _game
from .test_world_interior import _mains_grid


def _soup():
    return IN.soup_from_blocks({(0, 0): _mains_grid()})


CHECK_ONLY = ("crack", "census")      # the gates only Check runs (hilledit's docstring)
CASES = [((24.0, -24.0), 3.5, 14.0), ((24.0, -24.0), 5.5, 14.0), ((24.0, -24.0), 2.0, 12.0),
         ((24.0, -24.0), 6.0, 18.0), ((8.0, -8.0), 3.5, 14.0), ((26.0, -22.0), 4.2, 10.0),
         ((24.0, -24.0), 4.2, 24.0)]


@pytest.mark.parametrize("center,height,radius", CASES)
def test_the_preview_agrees_with_build_hill_gate_for_gate(center, height, radius):
    soup = _soup()
    pv = HE.preview(SoupIndex(soup), center, height, radius)
    try:
        res = IN.build_hill(soup, center=center, height=height, radius=radius, log=lambda *a: None)
    except IN.CarveRefused as e:
        assert e.where                                  # every hill refusal says where
        if e.gate in CHECK_ONLY:                        # a gate the preview leaves to Check: the preview passes it
            assert pv["ok"], (pv, e.gate)
            return
        assert not pv["ok"] and pv["gate"] == e.gate, (pv, e.gate, str(e))
        return
    assert pv["ok"], pv
    r = res["report"]
    assert pv["report"] == {"displaced_tris": r["displaced_tris"], "worst_flank": round(r["worst_flank"], 1),
                            "peak_y": round(r["peak_y"], 2)}


def test_the_preview_covers_both_outcomes():
    """The parity cases include passes and each cheap gate's refusal (a parity over one outcome proves nothing)."""
    got = {HE.preview(SoupIndex(_soup()), c, h, r)["gate"] for c, h, r in CASES}
    assert {None, "flank", "footprint"} <= got
    with pytest.raises(IN.CarveRefused, match="cracks"):  # and one the preview leaves to Check: the island's edge
        IN.build_hill(_soup(), center=(8.0, -8.0), height=3.5, radius=14.0, log=lambda *a: None)


def test_the_ghost_is_the_hill_the_verb_writes():
    soup = _soup()
    ix = SoupIndex(soup)
    tris, touched = HE.lifted(ix, (24.0, -24.0), 3.5, 14.0)
    res = IN.build_hill(soup, center=(24.0, -24.0), height=3.5, radius=14.0, log=lambda *a: None)
    (_blk, bm), = res["changed"].items()
    P = np.asarray(bm.chan_arrays[CH_POS], dtype=np.float64)    # block (0,0): its local frame is the world's
    want = P[np.asarray(bm.flat_index).reshape(-1, 3)[touched]]
    assert len(touched) == res["report"]["displaced_tris"]
    assert np.allclose(tris, want)


def test_the_hill_s_refusals_say_where():
    soup = _soup()
    with pytest.raises(IN.CarveRefused) as e:
        IN.build_hill(soup, center=(24.0, -24.0), height=5.5, radius=14.0, log=lambda *a: None)
    assert e.value.gate == "flank" and "flank slope" in str(e.value) and e.value.where
    with pytest.raises(IN.CarveRefused) as e:
        IN.build_hill(soup, center=(400.0, -400.0), height=3.5, radius=14.0, log=lambda *a: None)
    assert e.value.gate == "footprint" and e.value.where == [(400.0, -400.0)]
    with pytest.raises(IN.CarveRefused) as e:
        IN.build_hill(soup, near=(400.0, -400.0), height=3.5, radius=14.0, log=lambda *a: None)
    assert e.value.gate == "footprint" and "no lawful hill placement" in str(e.value)


def test_the_command_and_its_row():
    argv = HE.command("M", (24.0, -24.0), height=3.5, radius=14.0, report="r.json")
    assert argv == ["world-hill", "--mod-folder", "M", "--center", "24,-24", "--height", "3.5", "--radius", "14",
                    "--dry-run", "--report-json", "r.json"]
    assert HE.command("M", (24.04, -24.0), dry_run=False) == ["world-hill", "--mod-folder", "M", "--center", "24,-24"]
    row = RC.row_for(HE.command("-", (24.0, -24.0), height=3.5, radius=14.0, dry_run=False))
    assert row == {"table": "hill", "center": [24.0, -24.0], "height": 3.5, "radius": 14.0}
    assert RC.row_for(HE.command("-", (24.0, -24.0), dry_run=False)) == {"table": "hill", "center": [24.0, -24.0]}
    assert RC.label(row) == "hill h3.5 r14 at 24, -24"
    with pytest.raises(ValueError, match="exact placement"):
        RC.row_for(["world-hill", "--mod-folder", "-", "--near", "1,1"])


def test_report_json_carries_the_hill_s_verdict(monkeypatch, tmp_path):
    game = _game(tmp_path)                               # made first: nothing may resolve the real install
    monkeypatch.setattr(IN, "read_deployed_blocks", lambda *a, **k: {(0, 0): _mains_grid()})
    monkeypatch.setattr(IN, "read_deployed_stack", lambda *a, **k: {})
    monkeypatch.setattr(IN, "census_gate", lambda *a, **k: None)
    rep = tmp_path / "v.json"
    assert cli.main(["--game", str(game)] + HE.command("M", (24.0, -24.0), height=3.5, radius=14.0, report=rep)) == 0
    v = json.loads(rep.read_text())
    assert v["ok"] and v["dry_run"] and v["center"] == [24.0, -24.0] and v["report"]["displaced_tris"] > 40
    assert v["blocks"] == [[0, 0]]
    assert cli.main(["--game", str(game)] + HE.command("M", (24.0, -24.0), height=5.5, radius=14.0, report=rep)) == 2
    v = json.loads(rep.read_text())
    assert not v["ok"] and v["refused"]["gate"] == "flank" and v["refused"]["where"]


# ---------------------------------------------------------------- the card
@pytest.fixture(scope="module")
def app():
    pytest.importorskip("PySide6", reason="GUI extra not installed")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_the_card_places_a_hill_shows_its_lift_and_raises_it(app, tmp_path):
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldhill import HillTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    from .test_world_forestedit import _mod
    from .test_worldforest import Scripted

    def answer(kind, argv):
        return {"ok": True, "dry_run": kind == "check", "center": [24.0, -24.0], "blocks": [[0, 0]],
                "report": {"displaced_tris": 120, "worst_flank": 21.3, "peak_y": 6.7}, "written": [], "refused": None}
    run = Scripted(answer)
    game = _game(tmp_path)
    src = _mod(game, "FF9CustomMap-world", ((0, 0),))
    panel = WorldView3DPanel(pick_palette("dark"))
    ix = SoupIndex(_soup())
    tool = HillTool(pick_palette("dark"), panel, game_fn=lambda: game, source_fn=lambda: src, runner=run,
                    drafts_root=tmp_path / "drafts", sync=True, soup_fn=lambda folder: ix)
    tool.open_tool()
    tool.height_spin.setValue(3.5)
    tool.radius_spin.setValue(14.0)
    tool.place(24.0, -24.0, 3.2)
    ghost = panel._overlays[0][0].reshape(-1, 3)
    assert np.allclose(ghost, HE.lifted(ix, (24.0, -24.0), 3.5, 14.0)[0].reshape(-1, 3))
    tool._timer.stop()
    tool._check()
    (argv,) = run.argvs
    assert argv[5:] == HE.command(tool.draft(), (24.0, -24.0), height=3.5, radius=14.0, dry_run=True,
                                  report=argv[-1])
    assert "Passes every gate at x 24, z -24: 120 triangles lifted" in tool.verdict_lbl.text()
    tool.accept_btn.click()
    assert D.recipe_rows(tool.draft()) == [{"table": "hill", "center": [24.0, -24.0], "height": 3.5, "radius": 14.0}]
    tool.place(24.0, -24.0, 3.2)
    tool.height_spin.setValue(5.5)                       # too steep for r14: refused live, before any job
    assert "Not here: a flank leans" in tool.verdict_lbl.text() and len(run.argvs) == 2


def test_the_menu_opens_the_hill_card(app):
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worlddoc import WorldDoc
    doc = WorldDoc(pick_palette("dark"))
    assert doc.tool_actions["hill"].text() == "Add a hill" and "world-hill judges it" in doc.tool_actions["hill"].toolTip()
