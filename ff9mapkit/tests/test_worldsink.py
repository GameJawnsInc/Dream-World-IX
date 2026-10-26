"""Sinking an island from the World tab (overworld editor rung C5): the island list and its cache, the island under a
click, the precomputed verdict, the command and the draft's disc-4 step, ``world-sink --report-json``, the sink card,
and THE ACCEPTANCE: the card's two calls write the bytes the same calls typed by hand write, and a recipe's
``[[sink]]`` row composed into a draft writes them too. The world is ``tests/test_world_sink.py``'s synthetic one."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from ff9mapkit import cli
from ff9mapkit.world import draft as D
from ff9mapkit.world import fuse as FU
from ff9mapkit.world import recipe as RC
from ff9mapkit.world import sinkedit as SE
from ff9mapkit.world import transplant as TR

from .test_world_forestedit import _game, _mod, _no_real_install  # noqa: F401
from .test_world_sink import _island, world  # noqa: F401  (the synthetic world fixture)

ROW = {"at": [344.0, -360.0], "outline": [[340.0, -364.0], [348.0, -364.0], [348.0, -356.0], [340.0, -356.0]],
       "land_u2": 64.0, "max_y": 3.0, "blocks": [[5, 5]], "ok": True, "why": None, "fill": "tiles",
       "entrance_tris": 0, "cluster": None}


# ---------------------------------------------------------------- the island list
def test_every_island_carries_its_outline(world):
    at = _island(world, other=False)
    (row,) = TR.sink_candidates()
    xs, zs = [p[0] for p in row["outline"]], [p[1] for p in row["outline"]]
    assert (min(xs), max(xs), min(zs), max(zs)) == (340.0, 348.0, -364.0, -356.0)   # the pyramid's 2x2 tiles
    assert SE.hit([row], *at) is row


def test_the_island_list_is_scanned_once_per_install_and_disc(monkeypatch, tmp_path):
    from ff9mapkit import provision
    monkeypatch.setattr(provision, "cache_dir", lambda: tmp_path / "cache")
    scans = []

    def scan(**k):
        scans.append(k)
        return [dict(ROW)]
    game = _game(tmp_path)
    assert SE.candidates(game, scan=scan) == [ROW] and SE.candidates(game, scan=scan) == [ROW]
    assert len(scans) == 1
    SE.candidates(game, disc=4, scan=scan)
    SE.candidates(game, refresh=True, scan=scan)
    assert [s["disc"] for s in scans] == [1, 4, 1]


def test_the_island_under_a_click_and_its_verdict():
    other = {**ROW, "at": [400.0, -360.0], "outline": [[396.0, -364.0], [404.0, -364.0], [404.0, -356.0]],
             "ok": False, "why": "the coastal sea runs on", "cluster": {"ok": True, "members": [[1, 2], [3, 4]]},
             "entrance_tris": 3}
    rows = [ROW, other]
    assert SE.hit(rows, 344.0, -360.0) is ROW and SE.hit(rows, 351.0, -360.0) is ROW     # 3u off its coast
    assert SE.hit(rows, 370.0, -360.0) is None
    assert SE.verdict(ROW)["ok"] and SE.verdict(ROW)["how"] == "re-tiled as open water"
    assert SE.verdict(other)["why"] == "the coastal sea runs on"
    v = SE.verdict(other, cluster=True)
    assert not v["ok"] and "entrance tris" in v["why"]
    assert SE.verdict(other, cluster=True, allow_entrances=True)["how"] == "with the 2 islands its water joins"
    assert SE.verdict(None)["why"] == "no sinkable island here"


def test_the_command_and_the_draft_s_disc4_step():
    assert SE.command("M", (344.0, -360.0), dry_run=False) == ["world-sink", "--mod-folder", "M", "--at", "344",
                                                                "-360"]
    one, four = SE.commands("M", (425.098, -1020.0), cluster=True, report="a.json", report4="b.json")
    assert one == ["world-sink", "--mod-folder", "M", "--at", "425.098", "-1020", "--cluster", "--report-json",
                   "a.json"]
    assert four == ["world-sink", "--mod-folder", "M", "--at", "425.098", "-1020", "--disc", "4", "--cluster",
                    "--skip-mirror", "--report-json", "b.json"]
    a = cli.build_parser().parse_args(four)
    assert (a.at, a.disc, a.cluster, a.skip_mirror) == ([425.098, -1020.0], 4, True, True)
    assert RC.row_for(SE.command("-", (344.0, -360.0), allow_entrances=True, dry_run=False)) == \
        {"table": "sink", "at": [344.0, -360.0], "allow_entrances": True}
    with pytest.raises(ValueError, match="disc-1 sink"):
        RC.row_for(four)
    assert RC.label({"table": "sink", "at": [344.0, -360.0], "cluster": True}) == \
        "sink the island at 344, -360 (and its cluster)"


# ---------------------------------------------------------------- world-sink --report-json
def test_report_json_carries_the_sink_s_verdict(world, tmp_path, capsys):
    _island(world, other=False)
    game, _src = _drafts(tmp_path)
    rep = tmp_path / "v.json"
    assert cli.main(["--game", str(game)] + SE.command("FF9CustomMap-world", (344.0, -360.0), report=rep)) == 0
    v = json.loads(rep.read_text())
    assert v["ok"] and v["dry_run"] and v["blocks"] == [[5, 5]] and v["report"]["land_tris"] == 4
    assert cli.main(["--game", str(game)] + SE.command("FF9CustomMap-world", (100.0, -100.0), report=rep)) == 2
    v = json.loads(rep.read_text())
    assert not v["ok"] and v["refused"]["message"] in capsys.readouterr().err and v["refused"]["where"]


def test_the_disc4_preview_leaves_the_check_s_report_alone(world, monkeypatch, tmp_path, capsys):
    """The disc-4 preview re-ran the sink with every argument, ``--report-json`` included, so its verdict overwrote
    disc 1's: the card's Check showed disc 4's ("disc": 4, seen in a real Check), and "refused" for an island disc 1
    sinks and the Accept writes, disc 4 keeping its own -- the first call's verdict decides (PERF.md defect 2)."""
    from ff9mapkit.world import discmirror as DM
    _island(world, other=False)
    game, _src = _drafts(tmp_path)
    monkeypatch.setattr(DM, "copy_refusal", lambda blk, **k: "real cell differs across discs in ['terrain']")
    real = TR.sink

    def sink(mod, at, **k):
        if k.get("disc") == 4:
            raise ValueError("no island at (344, -360) on disc 4")
        return real(mod, at, **k)
    monkeypatch.setattr(TR, "sink", sink)
    rep = tmp_path / "v.json"
    assert cli.main(["--game", str(game)] + SE.command("FF9CustomMap-world", (344.0, -360.0), report=rep)) == 0
    v = json.loads(rep.read_text())
    assert v["disc"] == 1 and v["ok"] and v["refused"] is None and v["blocks"] == [[5, 5]]
    assert "the replay REFUSES there" in capsys.readouterr().out


# ---------------------------------------------------------------- THE ACCEPTANCE: the card's bytes, by hand, by recipe
def _drafts(tmp_path):
    game = _game(tmp_path)
    src = _mod(game, "FF9CustomMap-world", ((0, 0),))
    return game, src


def _world_bytes(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in (root / "FF9_Data" / "WorldMap").rglob("*.ff9mesh") if ".bak-" not in p.name}


def test_the_sink_card_writes_the_bytes_its_calls_typed_by_hand_write(world, monkeypatch, tmp_path):
    pytest.importorskip("PySide6", reason="GUI extra not installed")
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldsink import SinkTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    _island(world, other=False)
    game, src = _drafts(tmp_path)
    rows = TR.sink_candidates()
    at = tuple(rows[0]["at"])                            # the island's own point (its flattest land tri)

    class InProcess:
        def __init__(self):
            self.argvs = []

        def start(self, argv, cwd, done):
            self.argvs.append([str(a) for a in argv])
            done(cli.main([str(a) for a in argv[3:]]), "")

        def kill(self):
            pass

        def busy(self):
            return False
    run = InProcess()
    panel = WorldView3DPanel(pick_palette("dark"))
    tool = SinkTool(pick_palette("dark"), panel, game_fn=lambda: game, source_fn=lambda: src, runner=run,
                    drafts_root=tmp_path / "drafts", sync=True, outline_fn=lambda d: rows)
    tool.open_tool()
    assert "Click the map where the sink goes" in tool.verdict_lbl.text() or tool.island_lbl.text() == "Click an island."
    tool.place(345.0, -359.0, 1.0)                       # a click on the island: its own point is the command's
    assert tool.center == tuple(rows[0]["at"]) and "64 u²" in tool.island_lbl.text()
    assert len(panel._overlays) == 2 and panel._ghost["poly"].shape == (4, 2)
    tool._timer.stop()
    tool._check()
    assert tool.accept_btn.isEnabled(), tool.verdict_lbl.text()
    assert "Passes every gate" in tool.verdict_lbl.text()
    tool.accept_btn.click()
    assert [a[5:] for a in run.argvs[1:]] == [SE.commands(str(tool.draft()), at, report=run.argvs[1][-1],
                                                          report4=run.argvs[2][-1])[k] for k in (0, 1)]
    draft = tool.draft()
    assert ["FF9_Data/WorldMap/Disc1/0_1/r5/Block[5][5] Sea4.ff9mesh",
            "FF9_Data/WorldMap/Disc4/0_1/r5/Block[5][5] Sea4.ff9mesh"] == \
        [r for r in D.edits(draft) if "Sea4" in r]       # both discs: the draft's own disc-4 step
    assert D.recipe_rows(draft) == [{"table": "sink", "at": list(at)}]
    assert tool.show_btn.isHidden()                      # the island's point is open sea now

    hand = D.ensure_draft(src, game=game, root=tmp_path / "hand")
    for argv in SE.commands(hand, at):
        assert cli.main(["--game", str(game)] + argv) == 0
    assert _world_bytes(hand) == _world_bytes(draft)

    composed = D.ensure_draft(src, game=game, root=tmp_path / "composed")
    recipe = tmp_path / "r.toml"
    recipe.write_text(RC.dumps(D.recipe_rows(draft)), encoding="utf-8")
    assert cli.main(["--game", str(game), "world-fuse", str(recipe), "--mod-folder", str(composed)]) == 0
    assert _world_bytes(composed) == _world_bytes(draft)
    assert not math.isnan(at[0])


def test_a_disc4_refusal_keeps_disc4_s_island_and_says_so(world, monkeypatch, tmp_path):
    pytest.importorskip("PySide6", reason="GUI extra not installed")
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldsink import SinkTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    from .test_worldforest import Scripted

    def answer(kind, argv):
        disc4 = "--disc" in argv
        return {"ok": not disc4, "dry_run": kind == "check", "at": [344.0, -360.0], "blocks": [[5, 5]],
                "written": [], "report": {"land_tris": 4}, "refused": None if not disc4 else
                {"gate": "error", "message": "no island at (344, -360) on disc 4", "where": []}}
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
    assert len(run.argvs) == 3 and "--disc" in run.argvs[2]
    assert tool.verdict_lbl.property("state") == "warn" and "disc 4 keeps its own ground" in tool.verdict_lbl.text()
    assert D.history(tool.draft())["cursor"] == 1


# ---------------------------------------------------------------- editing a placed sink (rung C12)
def _sink_card(tmp_path, rows, runner=None, *, open_=True):
    pytest.importorskip("PySide6", reason="GUI extra not installed")
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldsink import SinkTool
    from ff9mapkit.workspace.worldview3d import WorldView3DPanel
    from .test_worldforest import Scripted
    game, src = _drafts(tmp_path)
    tool = SinkTool(pick_palette("dark"), WorldView3DPanel(pick_palette("dark")), game_fn=lambda: game,
                    source_fn=lambda: src, runner=runner or Scripted(), drafts_root=tmp_path / "drafts", sync=True,
                    outline_fn=lambda d: rows)
    if open_:
        tool.open_tool()
    return tool, game, src


def test_the_sink_card_opens_on_its_row_and_says_it_back(tmp_path):
    tool, _g, _s = _sink_card(tmp_path, [ROW])
    row = {"table": "sink", "at": [344.0, -360.0], "cluster": True}
    tool.load_row(row)
    assert tool.row() == row and tool.cluster.isChecked() and not tool.entrances.isChecked()
    assert "The island at 344, -360: 64 u²" in tool.island_lbl.text()
    with pytest.raises(ValueError, match="no island the sink takes lies at 900, -900"):
        tool.load_row({"table": "sink", "at": [900.0, -900.0]})
    tool.place(900.0, -900.0)                           # open sea, the list in: once (it recursed without end)
    assert tool._row_sel is None and tool.island_lbl.text() == "Click an island."


def test_a_sink_row_waits_for_the_island_list_and_one_it_cannot_say_cancels_the_edit(tmp_path):
    """The island list is read on a worker (minutes, once): the card holds the row until it comes, then seats it; a
    row whose island is not in the list cancels the open edit with the reason (the draft goes back)."""
    notes = []
    tool, _g, _s = _sink_card(tmp_path / "a", [ROW], open_=False)
    tool.edit_row({"table": "sink", "at": [344.0, -360.0]}, label="sink", on_accepted=lambda: None,
                  on_cancel=lambda note=None: notes.append(note))
    assert tool.editing() and tool._pending_row is not None and tool.center == (344.0, -360.0)
    tool._on_bg("outline", 0, ("islands", [ROW]), None)
    assert tool._pending_row is None and tool._row_sel is ROW and tool.editing() and notes == []
    tool, _g, _s = _sink_card(tmp_path / "b", [ROW], open_=False)
    tool.edit_row({"table": "sink", "at": [900.0, -900.0]}, label="sink", on_accepted=lambda: None,
                  on_cancel=lambda note=None: notes.append(note))
    tool._on_bg("outline", 0, ("islands", [ROW]), None)
    assert notes == ["Not opened in its card: no island the sink takes lies at 900, -900. Delete still works."]
    assert not tool.editing() and tool.isHidden()


def test_a_step_s_ticks_never_outlive_its_edit(tmp_path):
    """load_row ticks the step's boxes before it knows the row can be seated; a row refused at open (the tab closes
    the card before the author sees it) left 'Allow entrances' ticked, and the next fresh sink passed the entrance law
    on an island with a place on it -- a place that never opens again (review of C12). A card opens on the defaults;
    an edit then ticks what its row says."""
    gated = {**ROW, "entrance_tris": 12}                 # an island with an entrance on it
    tool, _g, _s = _sink_card(tmp_path, [gated])
    with pytest.raises(ValueError, match="no island the sink takes"):
        tool.edit_row({"table": "sink", "at": [900.0, -900.0], "allow_entrances": True, "cluster": True}, label="s",
                      on_accepted=lambda: None, on_cancel=lambda note=None: None)
    tool.close_tool()                                    # (WorldDoc._edit_step closes the refused card)
    tool.open_tool()                                     # the Sink button, later
    assert not tool.entrances.isChecked() and not tool.cluster.isChecked()
    tool.place(345.0, -359.0)
    assert not tool._preview["ok"], tool._preview
    tool.edit_row({"table": "sink", "at": [344.0, -360.0], "allow_entrances": True}, label="s",
                  on_accepted=lambda: None, on_cancel=lambda note=None: None)
    assert tool.entrances.isChecked() and tool.row()["allow_entrances"] is True


def test_reopening_the_sink_card_mid_edit_keeps_the_step_s_ticks(tmp_path):
    """The tab opens a card that is already open (the menu stays live during an edit), and open_tool's reset of the
    boxes wiped the edit's ticks: Accept would write the sink without --cluster, or a held row was refused against
    the cleared boxes (review of the C12 fixes). The reset is for a card opening fresh, not mid-edit."""
    row = {"table": "sink", "at": [344.0, -360.0], "cluster": True}
    tool, _g, _s = _sink_card(tmp_path / "a", [ROW])
    tool.edit_row(row, label="s", on_accepted=lambda: None, on_cancel=lambda note=None: None)
    tool.open_tool()                                     # Sink an island, picked again mid-edit
    assert tool.editing() and tool.cluster.isChecked() and tool.row() == row
    notes = []
    tool, _g, _s = _sink_card(tmp_path / "b", [ROW], open_=False)
    held = []
    tool._bg = lambda what, fn: held.append((what, fn))  # the island list still being read
    tool.edit_row(row, label="s", on_accepted=lambda: None, on_cancel=lambda note=None: notes.append(note))
    tool.open_tool()
    for what, fn in held:
        tool._on_bg(what, 0, fn(), None)
    assert tool.editing() and notes == [] and tool.row() == row


def test_a_sink_s_two_call_accept_is_never_cut_between_its_calls(tmp_path):
    """The sink's Accept is two calls, disc 1 then disc 4's replay, the second started by the first's end. close_tool
    waited for one call and then killed the runner, cutting the disc-4 call: the disc-1 sink in the draft with no
    recipe row and an orphaned pending step (review of the C19 fixes, fourth round). The card cannot be closed while
    it writes, and closed anyway it waits for every call of the job."""
    from .test_worldforest import Scripted

    def answer(kind, argv):
        return {"ok": True, "dry_run": kind == "check", "blocks": [[5, 5]], "written": [], "refused": None,
                "report": {"land_tris": 4}}
    run = Scripted(answer)
    tool, _g, _s = _sink_card(tmp_path, [ROW], run)
    tool.place(345.0, -359.0)
    tool._timer.stop()
    tool._check()
    assert tool.accept_btn.isEnabled(), tool.verdict_lbl.text()
    run.hold = True
    tool.accept_btn.click()                              # disc 1 writing
    assert run.busy() and tool.writing() and not tool.close_btn.isEnabled()
    tool.close_tool()                                    # closed anyway (from code)
    assert not run.busy() and len([a for a in run.argvs if "--dry-run" not in a]) == 2
    assert D.history(tool.draft())["cursor"] == 1 and tool.isHidden()


def test_a_sink_edited_through_the_recipe_bar_writes_what_world_fuse_writes(world, monkeypatch, tmp_path):
    """THE C12 ACCEPTANCE for the sink, on the synthetic world: a sink placed with the card, picked in the recipe bar,
    opened again in its card on its own row, retuned (entrances allowed) and accepted; the recipe is the edited row,
    and the draft is that recipe composed by world-fuse onto the folder, byte for byte."""
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.worldrecipe import RecipeBar

    class InProcess:
        def __init__(self):
            self.argvs = []

        def start(self, argv, cwd, done):
            self.argvs.append([str(a) for a in argv])
            done(cli.main([str(a) for a in argv[3:]]), "")

        def kill(self):
            pass

        def busy(self):
            return False
    _island(world, other=False)
    rows = TR.sink_candidates()
    at = tuple(rows[0]["at"])
    run = InProcess()
    tool, game, src = _sink_card(tmp_path, rows, run)
    tool.place(345.0, -359.0, 1.0)
    tool._timer.stop()
    tool._check()
    tool.accept_btn.click()
    bar = RecipeBar(pick_palette("dark"), game_fn=lambda: game, source_fn=lambda: src, runner=run,
                    drafts_root=tmp_path / "drafts", ask=lambda t, x: True,
                    on_edit=lambda row, label: (tool.open_tool(), tool.edit_row(
                        row, label=label, on_accepted=bar.edit_accepted, on_cancel=bar.cancel_edit)))
    bar.refresh()
    bar.select(0)
    assert bar.edit_btn.isEnabled(), bar.edit_btn.toolTip()
    bar.edit_btn.click()
    assert tool.editing() and tool.row() == {"table": "sink", "at": list(at)}
    tool.entrances.setChecked(True)
    tool._timer.stop()
    tool._check()
    assert tool.accept_btn.isEnabled(), tool.verdict_lbl.text()
    tool.accept_btn.click()
    draft = tool.draft()
    assert not tool.editing() and bar.status_lbl.property("state") == "ok", bar.status_lbl.text()
    edited = [{"table": "sink", "at": list(at), "allow_entrances": True}]
    assert D.recipe_rows(draft) == edited and D.history(draft)["edit"] is None
    composed = D.ensure_draft(src, game=game, root=tmp_path / "composed")
    recipe = tmp_path / "r.toml"
    recipe.write_text(RC.dumps(edited), encoding="utf-8")
    assert cli.main(["--game", str(game), "world-fuse", str(recipe), "--mod-folder", str(composed)]) == 0
    assert _world_bytes(composed) == _world_bytes(draft)
