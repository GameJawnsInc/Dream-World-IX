"""Coast morphs from the World tab (overworld editor rung C5): the windows and their lawful depths, the window under a
click, the command and the draft's disc-4 step, ``world-transplant --report-json``, the ``[[morph]]`` recipe row, the
coast card, and THE ACCEPTANCE on real bytes (install-gated): the card's two calls write what the same calls typed by
hand write, and the recipe's ``[[morph]]`` row composed into a draft writes it too."""
from __future__ import annotations

import json
import os
import warnings
from pathlib import Path

import pytest

from ff9mapkit import cli
from ff9mapkit.world import coastedit as CE
from ff9mapkit.world import coastmorph as CM
from ff9mapkit.world import draft as D
from ff9mapkit.world import fuse as FU
from ff9mapkit.world import recipe as RC
from ff9mapkit.world import transplant as TR

from .test_world_forestedit import _game, _mod

CLIFF = {"kind": "cliff", "cell": [3, 8], "L": 47.4, "n": 12,
         "run": [[211.68, -512.0], [205.0, -520.0], [198.0, -535.0], [192.0, -547.86]],
         "start": [211.68, -512.0], "end": [192.0, -547.86],
         "probes": {"cliff-bump": {"depth": 2.5, "binding": None, "window": [[211.6758, -512.0], [192.0, -547.8594]]},
                    "cliff-headland": {"depth": None, "binding": "D=8: painted-mural family", "window": None},
                    "cliff-bay": {"depth": None, "binding": "D=6: painted-mural family", "window": None}}}
BEACH = {"kind": "beach", "cell": [3, 8], "L": 20.0, "n": 6, "class": "straight", "devs": [-0.1, 0.1],
         "start": [230.0, -560.0], "end": [240.0, -575.0],
         "probes": {"beach-bump": {"seaward": 1.5, "landward": -1.0, "seaward_binding": None, "landward_binding": None,
                                   "window": [[230.0, -560.0], [240.0, -575.0]]},
                    "beach-slide": {"seaward": None, "landward": None, "seaward_binding": "D=1: x",
                                    "landward_binding": "D=-1: y", "window": [[230.0, -560.0], [240.0, -575.0]]}}}


def _real_install():
    """The install, resolved ONCE here, before any test closes the fall-through: the real-bytes test passes it as an
    explicit --game, so no call in this module ever auto-detects the game."""
    from ff9mapkit import config
    try:
        import UnityPy  # noqa: F401
        g = config.find_game_path(None)
        return g if (g / "StreamingAssets").is_dir() else None
    except Exception:
        return None


REAL_GAME = _real_install()


@pytest.fixture(autouse=True)
def _pin(monkeypatch):
    """NEVER THE REAL INSTALL by accident: a missing path raises instead of falling through to the game (a test here
    once wrote <install>/Src that way -- a scratch folder not made yet). The real-bytes test names it explicitly."""
    from ff9mapkit import config
    monkeypatch.delenv("FF9_GAME_PATH", raising=False)
    monkeypatch.setattr(config, "_read_user_config", lambda: {})
    for name in ("_registry_candidates", "_steam_library_candidates", "_fallback_candidates"):
        monkeypatch.setattr(config, name, lambda: [])


# ---------------------------------------------------------------- the windows
def test_a_window_s_lawful_depths_are_its_probed_ceilings():
    assert CE.lawful(CLIFF) == {"cliff-bump": (0.5, 2.5)}
    assert CE.lawful(BEACH) == {"beach-bump": (-1.0, 1.5)}
    assert CE.span(CLIFF, "cliff-bump") == ((211.6758, -512.0), (192.0, -547.8594))


def test_the_window_under_a_click_and_its_verdict():
    assert CE.nearest([CLIFF, BEACH], 205.0, -521.0) is CLIFF
    assert CE.nearest([CLIFF, BEACH], 236.0, -567.0) is BEACH
    assert CE.nearest([CLIFF, BEACH], 300.0, -300.0) is None
    assert CE.verdict(CLIFF, "cliff-bump", 2.5)["ok"]
    assert "outside the window's lawful 0.5..2.5" in CE.verdict(CLIFF, "cliff-bump", 3.0)["why"]
    assert "painted-mural" in CE.verdict(CLIFF, "cliff-headland", 2.0)["why"]
    assert CE.verdict(BEACH, "beach-bump", -1.0)["ok"] and not CE.verdict(BEACH, "beach-bump", 0.0)["ok"]
    v = CE.verdict(CLIFF, "cliff-bump", 2.5, edited_by=["FF9CustomMap-world"])
    assert not v["ok"] and "already edited in FF9CustomMap-world" in v["why"]


def test_the_windows_are_scanned_once_per_block(monkeypatch, tmp_path):
    from ff9mapkit import provision
    monkeypatch.setattr(provision, "cache_dir", lambda: tmp_path / "cache")
    scans = []
    game = tmp_path / "g"
    game.mkdir()
    ws = CE.windows(game, (3, 8), scan=lambda bx, by, **k: scans.append((bx, by)) or [dict(CLIFF)])
    assert ws == [CLIFF] and CE.windows(game, (3, 8), scan=lambda *a, **k: 1 / 0) == [CLIFF]
    CE.windows(game, (4, 8), scan=lambda bx, by, **k: scans.append((bx, by)) or [])
    assert scans == [(3, 8), (4, 8)]


def test_the_command_its_disc4_step_and_its_row():
    sp = CE.spec(CLIFF, "cliff-bump", 2.5)
    assert sp == "211.6758,-512.0000:192.0000,-547.8594:2.5"
    one, four = CE.commands("M", (3, 8), "cliff-bump", sp, report="a.json", report4="b.json")
    assert one == ["world-transplant", "--mod-folder", "M", "--cell", "3,8", "--donor", "3,8", "--in-place",
                   "--cliff-bump", sp, "--report-json", "a.json"]
    assert four == one[:-2] + ["--disc", "4", "--skip-mirror", "--report-json", "b.json"]
    a = cli.build_parser().parse_args(four)
    assert (a.disc, a.skip_mirror, a.in_place, a.cliff_bump) == (4, True, True, sp)
    row = RC.row_for(CE.command("-", (3, 8), "cliff-bump", sp, dry_run=False))
    assert row == {"table": "morph", "cell": [3, 8], "verb": "cliff-bump",
                   "window": [[211.6758, -512.0], [192.0, -547.8594]], "depth": 2.5}
    assert RC.label(row) == "cliff-bump 2.5 at block (3, 8)"
    with pytest.raises(ValueError, match="disc-1 morph"):
        RC.row_for(four)
    with pytest.raises(ValueError, match="is not a coast morph"):
        CE.command("M", (3, 8), "beach-mint", sp)


# ---------------------------------------------------------------- the CLI's verdict and the [[morph]] row
def _stub_morphs(monkeypatch):
    calls = []

    def bump(donor, p0, p1, depth, **k):
        calls.append(("build", donor, p0, p1, depth, k["disc"]))
        return ["a tweak"]                               # (the stubbed morph never applies it)

    def morph(mod, **k):
        calls.append(("morph", str(mod), k["disc"], k["skip_mirror"], k["dry_run"]))
        return {"op": "morph-in-place", "cell": list(k["cell"]), "touched": ["terrain"], "clean": True,
                "dry_run": k["dry_run"], "deployed": [], "gates": [{"gate": "frame", "ok": True}]}
    monkeypatch.setattr(CM, "cliff_bump", bump)
    monkeypatch.setattr(TR, "morph_in_place", morph)
    return calls


def test_report_json_carries_the_morph_s_verdict(monkeypatch, tmp_path):
    _stub_morphs(monkeypatch)
    game = _game(tmp_path)
    rep = tmp_path / "v.json"
    sp = CE.spec(CLIFF, "cliff-bump", 2.5)
    assert cli.main(["--game", str(game)] + CE.command("M", (3, 8), "cliff-bump", sp, report=rep)) == 0
    v = json.loads(rep.read_text())
    assert v["ok"] and v["dry_run"] and v["cell"] == [3, 8] and v["gates"] == [{"gate": "frame", "ok": True}]
    monkeypatch.setattr(TR, "morph_in_place", lambda mod, **k: {
        "op": "morph-in-place", "cell": [3, 8], "touched": [], "clean": False, "dry_run": True, "deployed": [],
        "gates": [{"gate": "frame", "ok": False}]})
    assert cli.main(["--game", str(game)] + CE.command("M", (3, 8), "cliff-bump", sp, report=rep)) == 2
    v = json.loads(rep.read_text())
    assert not v["ok"] and v["refused"]["gate"] == "frame" and v["refused"]["where"] == [[224.0, -544.0]]


def test_the_morph_row_is_the_command(monkeypatch, tmp_path):
    """A [[morph]] row runs world-transplant --in-place itself: the same builder call and the same morph call as the
    command typed by hand; composed into a draft it adds the disc-4 call, onto a live folder it does not."""
    calls = _stub_morphs(monkeypatch)
    game, src = _game(tmp_path), None
    src = _mod(game, "Src", ((0, 0),))
    sp = CE.spec(CLIFF, "cliff-bump", 2.5)
    assert cli.main(["--game", str(game)] + CE.command("Src", (3, 8), "cliff-bump", sp, dry_run=False)) == 0
    by_hand = list(calls)
    calls.clear()
    row = RC.row_for(CE.command("-", (3, 8), "cliff-bump", sp, dry_run=False))
    out = FU.compose_layout("Src", {"morph": [{k: v for k, v in row.items() if k != "table"}]}, game=game)
    assert out["clean"] and calls == by_hand
    calls.clear()
    d = D.ensure_draft(src, game=game, root=tmp_path / "drafts")
    FU.compose_layout(str(d), {"morph": [{k: v for k, v in row.items() if k != "table"}]}, game=game)
    assert [c[2:4] for c in calls if c[0] == "morph"] == [(1, False), (4, True)]
    odd = FU.compose_layout("Src", {"morph": [{"cell": [3, 8], "verb": "cliff-bump", "depth": 1,
                                               "window": [[0, 0], [1, 1]], "side": "sea"}]}, game=game, dry_run=True)
    assert not odd["clean"] and "unknown key(s) ['side']" in odd["gates"][-1]["error"]
    bad = FU.compose_layout("Src", {"morph": [{"cell": [3, 8], "verb": "nope", "window": [[0, 0], [1, 1]],
                                               "depth": 1}]}, game=game, dry_run=True)
    assert not bad["clean"] and "verb must be one of" in bad["gates"][-1]["error"]


# ---------------------------------------------------------------- the coast card
@pytest.fixture(scope="module")
def app():
    pytest.importorskip("PySide6", reason="GUI extra not installed")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _card(app, tmp_path, runner, stack=()):
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldcoast import CoastTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    game = _game(tmp_path)
    src = _mod(game, "FF9CustomMap-world", ((0, 0),))
    panel = WorldView3DPanel(pick_palette("dark"))
    tool = CoastTool(pick_palette("dark"), panel, game_fn=lambda: game, source_fn=lambda: src, runner=runner,
                     drafts_root=tmp_path / "drafts", sync=True, stack_fn=lambda: list(stack),
                     outline_fn=lambda cell: [] if cell == "-" else [CLIFF, BEACH])
    tool.open_tool()
    return tool, panel, game, src


def test_the_card_offers_only_lawful_morphs_and_accepts_on_both_discs(app, monkeypatch, tmp_path):
    from .test_worldforest import Scripted

    def answer(kind, argv):
        return {"ok": True, "dry_run": kind == "check", "cell": [3, 8], "blocks": [[3, 8]], "written": [],
                "gates": [{"gate": "frame", "ok": True}, {"gate": "stitch", "ok": True}], "refused": None}
    run = Scripted(answer)
    tool, panel, _g, _s = _card(app, tmp_path, run)
    tool.place(205.0, -521.0, 2.0)
    assert [tool.verb_box.itemData(i) for i in range(tool.verb_box.count())] == ["cliff-bump"]
    assert (tool.depth.minimum(), tool.depth.maximum(), tool.depth.value()) == (0.5, 2.5, 2.5)
    assert "cliff run in block (3, 8), 47 u long" in tool.window_lbl.text()
    assert len(panel._overlays) == 2
    tool._timer.stop()
    tool._check()
    assert "Passes every gate (2)" in tool.verdict_lbl.text() and tool.accept_btn.isEnabled()
    tool.accept_btn.click()
    calls = run.argvs[1:]
    assert len(calls) == 2 and "--disc" not in calls[0] and calls[1][calls[1].index("--disc") + 1] == "4"
    assert D.recipe_rows(tool.draft())[0]["table"] == "morph"
    tool.place(236.0, -567.0)                           # the beach: landward to seaward
    assert [tool.verb_box.itemData(i) for i in range(tool.verb_box.count())] == ["beach-bump"]
    assert (tool.depth.minimum(), tool.depth.maximum()) == (-1.0, 1.5)


def test_the_card_offers_no_window_on_a_block_already_edited(app, monkeypatch, tmp_path):
    from ff9mapkit.world import mesh as M
    from .test_world_interior import _bm, GRASS, _MAIN_U
    from .test_worldforest import Scripted
    game = _game(tmp_path)
    M.deploy_override(_bm([(((0, 3.0, 0), (4, 3.0, 0), (0, 3.0, -4)), GRASS, _MAIN_U)], name="Block[3][8] Terrain",
                          x=3, y=8), mod_folder="Other", game=game, part="Terrain", disc=1)
    run = Scripted()
    tool, _p, game2, _s = _card(app, tmp_path, run, stack=[str(game / "Other")])
    tool.place(205.0, -521.0)
    tool._timer.stop()
    tool._check()
    assert not run.argvs and "already edited in Other" in tool.verdict_lbl.text()


# ---------------------------------------------------------------- THE ACCEPTANCE, on real bytes
REAL = ((2, 7), "174.76953125,-512.0:179.55859375,-448.0:2.5")     # the disc-4-replay study's passing bump


def _install():
    if REAL_GAME is not None:
        return REAL_GAME
    warnings.warn("the coast card's identity went unchecked on real bytes: no FF9 install + UnityPy. Re-run in the "
                  "MAIN repo (C:/gd/Dream-World-IX/ff9mapkit).", UserWarning)
    pytest.skip("needs the FF9 install + UnityPy")


def _bytes(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in (root / "FF9_Data" / "WorldMap").rglob("*.ff9mesh") if ".bak-" not in p.name}


def test_the_card_s_calls_write_what_the_hand_typed_calls_and_the_recipe_write(tmp_path):
    """Drafts of a scratch folder OUTSIDE the install; the morph reads the install's stock bytes (--game). Nothing
    is written into the install: a draft cannot mirror, and its disc-4 call skips the mirror."""
    real = _install()
    scratch = _game(tmp_path)                            # made first: a missing folder must never resolve elsewhere
    src = _mod(scratch, "Src", ((0, 0),))
    assert src.is_relative_to(tmp_path)
    (cell, sp) = REAL
    drafts = []
    for name in ("editor", "hand"):
        d = D.ensure_draft(src, game=real, root=tmp_path / name)
        drafts.append(d)
        for argv in CE.commands(d, cell, "cliff-bump", sp):
            assert cli.main(["--game", str(real)] + argv) == 0
    composed = D.ensure_draft(src, game=real, root=tmp_path / "composed")
    recipe = tmp_path / "r.toml"
    recipe.write_text(RC.dumps([RC.row_for(CE.command("-", cell, "cliff-bump", sp, dry_run=False))]),
                      encoding="utf-8")
    assert cli.main(["--game", str(real), "world-fuse", str(recipe), "--mod-folder", str(composed)]) == 0
    ed = _bytes(drafts[0])
    assert ed == _bytes(drafts[1]) == _bytes(composed)
    assert any("Disc4" in k and "Block[2][7]" in k for k in D.edits(drafts[0]))   # the draft's own disc-4 step


# ---------------------------------------------------------------- editing a placed morph (rung C12)
def _morph_row(window, verb, depth):
    return RC.row_for(CE.command("-", (3, 8), verb, CE.spec(window, verb, depth), dry_run=False))


def test_the_held_window_keeps_a_tie():
    twin = {**CLIFF, "probes": dict(CLIFF["probes"])}   # the same run, listed first
    assert CE.nearest([twin, CLIFF], 205.0, -520.0) is twin
    assert CE.nearest([twin, CLIFF], 205.0, -520.0, prefer=CLIFF) is CLIFF
    assert CE.nearest([twin, CLIFF], 236.0, -567.0, prefer=CLIFF) is None     # nothing near: not kept for itself
    x, z = CE.anchor(CLIFF, "cliff-bump")
    assert CE.nearest([BEACH, CLIFF], x, z) is CLIFF and CE._on_run(CLIFF, x, z)[0] < 1e-9     # on its run


def test_the_coast_card_opens_on_its_row_and_says_it_back(app, tmp_path):
    from .test_worldforest import Scripted
    tool, _p, _g, _s = _card(app, tmp_path, Scripted())
    for window, verb, depth in ((CLIFF, "cliff-bump", 2.0), (BEACH, "beach-bump", -1.0), (BEACH, "beach-bump", 1.5)):
        row = _morph_row(window, verb, depth)
        tool.load_row(row)
        assert tool.row() == row and tool._window is window and tool.verb() == verb and tool.depth.value() == depth
    with pytest.raises(ValueError, match=r"not one of block \(3, 8\)'s lawful cliff-bump windows"):
        tool.load_row({**_morph_row(CLIFF, "cliff-bump", 2.0), "window": [[211.0, -512.0], [192.0, -547.8594]]})
    with pytest.raises(ValueError, match="depth 3 is outside the window's lawful 0.5 to 2.5"):
        tool.load_row({**_morph_row(CLIFF, "cliff-bump", 2.0), "depth": 3.0})
    with pytest.raises(ValueError, match="its morph cliff-shove is not one the card offers"):
        tool.load_row({**_morph_row(CLIFF, "cliff-bump", 2.0), "verb": "cliff-shove"})


def test_a_morph_row_waits_for_its_block_s_windows_and_one_it_cannot_say_cancels_the_edit(app, tmp_path):
    from .test_worldforest import Scripted
    notes = []
    for sub, row, ok in (("a", _morph_row(CLIFF, "cliff-bump", 1.5), True),
                         ("b", {**_morph_row(CLIFF, "cliff-bump", 1.5), "depth": 9.0}, False)):
        tool, _p, _g, _s = _card(app, tmp_path / sub, Scripted())
        held = []
        tool._bg = lambda what, fn, held=held: held.append((what, fn))     # the windows read on a worker
        tool.edit_row(row, label="morph", on_accepted=lambda: None, on_cancel=lambda note=None: notes.append(note))
        assert tool.editing() and tool._pending_row is row and "Reading block (3, 8)'s coast" in tool.window_lbl.text()
        (what, fn), = [h for h in held if h[0] == "outline"]
        tool._on_bg(what, 0, fn(), None)
        if ok:
            assert tool._pending_row is None and tool.row() == row and tool.editing() and notes == []
    assert notes == ["Not opened in its card: its depth 9 is outside the window's lawful 0.5 to 2.5. Delete still "
                     "works."] and not tool.editing() and tool.isHidden()


def test_a_second_read_of_the_block_keeps_the_held_window_and_its_depth(app, tmp_path):
    """Every read of a block's windows is a fresh JSON load: new dicts equal to the old. The card held its window by
    identity, so a second read landing after the edit seated took the equal window for another and reset the depth to
    its ceiling: Accept would write 2.5 for a step placed at 1.5, no handle touched (review of C12). Two reads are in
    flight whenever an edit opens on a block whose windows are not in yet (open_tool asks, then the seat)."""
    import copy
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldcoast import CoastTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    from .test_worldforest import Scripted
    game = _game(tmp_path)
    src = _mod(game, "FF9CustomMap-world", ((0, 0),))
    tool = CoastTool(pick_palette("dark"), WorldView3DPanel(pick_palette("dark")), game_fn=lambda: game,
                     source_fn=lambda: src, runner=Scripted(), drafts_root=tmp_path / "drafts", sync=False,
                     stack_fn=lambda: [], outline_fn=lambda cell: [] if cell == "-" else copy.deepcopy([CLIFF, BEACH]))
    held = []
    tool._bg = lambda what, fn: held.append((what, fn))     # the worker lane, held
    tool.open_tool()
    tool.place(205.0, -521.0)                                # the card is on block (3, 8), its windows being read
    row = _morph_row(CLIFF, "cliff-bump", 1.5)
    tool.close_tool()
    tool.open_tool()
    notes = []
    tool.edit_row(row, label="morph", on_accepted=lambda: None, on_cancel=lambda note=None: notes.append(note))
    reads = [h for h in held if h[0] == "outline"]
    assert len(reads) >= 2
    for what, fn in reads:
        tool._on_bg(what, 0, fn(), None)
        assert tool.editing() and notes == []
    assert tool.depth.value() == 1.5 and tool.row() == row


def test_who_holds_the_block_is_read_again_when_the_card_opens_on_another_folder(app, tmp_path):
    """C12 re-read who holds the card's block when the draft moved, but a folder pick or a Rescan only closes the
    card: open on another folder and clicked on the same block, it judged the block by the OLD folder's holders and
    refused a lawful morph -- or passed one the new folder already overrides (review of C12)."""
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.world import mesh as M
    from ff9mapkit.workspace.worldcoast import CoastTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    from .test_world_interior import _bm, GRASS, _MAIN_U
    from .test_worldforest import Scripted
    game = _game(tmp_path)
    a, b = _mod(game, "FolderA", ((0, 0),)), _mod(game, "FolderB", ((0, 0),))
    M.deploy_override(_bm([(((0, 3.0, 0), (4, 3.0, 0), (0, 3.0, -4)), GRASS, _MAIN_U)], name="Block[3][8] Terrain",
                          x=3, y=8), mod_folder="FolderA", game=game, part="Terrain", disc=1)     # A holds (3, 8)
    shown = {"src": a}
    tool = CoastTool(pick_palette("dark"), WorldView3DPanel(pick_palette("dark")), game_fn=lambda: game,
                     source_fn=lambda: shown["src"], runner=Scripted(), drafts_root=tmp_path / "drafts", sync=True,
                     stack_fn=lambda: [str(shown["src"])], outline_fn=lambda c: [] if c == "-" else [CLIFF, BEACH])
    for src, holders in ((a, ["FolderA"]), (b, []), (a, ["FolderA"])):
        shown["src"] = src                               # the folder pick: the tab closes the card, nothing else
        tool.close_tool()
        tool.open_tool()
        tool.place(205.0, -521.0)
        assert tool._edited_by == holders and tool._preview["ok"] == (not holders), (src.name, tool._edited_by)


def test_who_holds_the_block_is_read_again_when_the_draft_moves(app, monkeypatch, tmp_path):
    """The card read once per block which folders override it: after an undo (or an edit lifting the morph out) the
    block still read as edited, and the card refused the very morph it had just made (c12_lab, E2)."""
    from ff9mapkit.world import mesh as M
    from .test_world_interior import _bm, GRASS, _MAIN_U
    from .test_worldforest import Scripted
    stack = []
    tool, _p, game, _s = _card(app, tmp_path, Scripted(), stack=stack)
    tool._stack_fn = lambda: list(stack)
    tool.place(205.0, -521.0)
    assert tool._edited_by == []
    M.deploy_override(_bm([(((0, 3.0, 0), (4, 3.0, 0), (0, 3.0, -4)), GRASS, _MAIN_U)], name="Block[3][8] Terrain",
                          x=3, y=8), mod_folder="Other", game=game, part="Terrain", disc=1)
    stack.append(str(game / "Other"))
    tool.island_changed()
    assert tool._edited_by == ["Other"]
    stack.clear()
    tool.island_changed()
    tool.place(205.0, -521.0)
    assert tool._edited_by == [] and tool._preview["ok"], tool.verdict_lbl.text()
