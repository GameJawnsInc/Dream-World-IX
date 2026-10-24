"""Moving the river (overworld editor rung C5): ``world-river --move-from``, a world draft that carries deletions
through Promote and Revert, the ledger travelling with the bytes (so the moved river stays the verb's own), and the
stack read that lets a draft stand in for its source folder.

The river calls that read the install are replaced as ``test_world_river._river_cli`` does, except that the fake
composition's cells follow the placement (a whole-block shift moves every cell) and its stage really writes, so the
promotion, the ledger, the removal and the disc-4 mirror all run for real on a tmp install."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ff9mapkit import cli
from ff9mapkit.world import discmirror as DM
from ff9mapkit.world import draft as D
from ff9mapkit.world import mesh as M
from ff9mapkit.world import river as R

from .test_world_river import _PROMOTE, _full_cell_land, _game, _override, _staged, _w1

FOLDER = "FF9CustomMap-world"
HOME = ((23, 12), (0, 11), (1, 11), (0, 12))                 # the fake river's cells at shift (8, -2)
OLD, NEW = "512,128", "512,192"                              # shift (8,-2), and one block north: (8,-3)


def _cells_at(offset):
    sx, sy = R.block_shift(offset)
    return sorted((M.wrap_block_col(x + sx - 8), y + sy + 2) for x, y in HOME)


@pytest.fixture
def river(tmp_path, monkeypatch):
    """A tmp install stacking FF9CustomMap-world, the fake river pipeline, and the real seam, ledger and mirror."""
    game = _game(tmp_path / "game", monkeypatch, folders=(FOLDER, "OTHER"))
    calls = []
    frag = SimpleNamespace(donor=R.CLUSTER_C, tris=[], report={"tris": 1546, "unit": 330, "cove": 1026, "coast": 141},
                           boundary={"source": [((1128.5, 2.7, -914.9), (1128.9, 3.2, -917.9))], "lawn": []})
    ol = SimpleNamespace(ring=[(0.0, 0.0)] * 138)
    g = {"J": {"E": {"du": 2e-16, "dv": 4e-4, "slope": [78.21]}, "W": {"du": 2e-15, "dv": 4e-4, "slope": [72.04]}},
         "zip": {"tris": 442, "max_edge": 6.66, "max_rise": 1.39, "fails": 0, "ok": True},
         "G1": {"cracks": 0, "where": [], "ok": True}, "G3": {"near_miss": 0, "ok": True},
         "G4": {"points": 10098, "by": {"same": 10098}, "ok": True}, "G4_kit": {"points": 3341, "miss": 0, "ok": True},
         "G5": {"flipped": 0, "skipped_carried": 201, "ok": True}, "G6": {"river_points_moved": {}, "ok": True},
         "C1": {"ok": True, "max": 601, "fails": []}}

    def compose(f, **kw):
        calls.append(("compose", kw))
        cells = _cells_at(kw["offset"])                                  # binding_plan's own folder read, faked
        occ = [p for p in M.existing_overrides(cells, kw["mod_folder"], disc=1)
               if Path(p) not in kw.get("ignore", ())] if kw.get("mod_folder") else []
        b1 = {"ok": not occ, "cells": len(cells), "fails": [f"{len(occ)} override file(s)"] if occ else []}
        return R.Composition(offset=tuple(float(v) for v in kw["offset"]), tris=[], outline=ol,
                             plan={"cells": {f"{x},{y}": {"divert": [16, 15]} for x, y in cells}},
                             report={"gates": {**g, "B1": b1}, "area": {"area": 14, "source": "open-sea"}})

    def write_composition(comp, root, **kw):
        calls.append(("stage", root))
        R.write({tuple(int(v) for v in k.split(",")): {"terrain": _full_cell_land(tuple(int(v) for v in k.split(",")))}
                 for k in comp.plan["cells"]}, root)
        sx, sy = R.block_shift(comp.offset)                              # the understood band edge moves with it
        return _staged(W1=_w1(where=tuple((x + sx, y + sy, i, j) for x, y, i, j in R.UNDERSTOOD_EDGES["cluster-c"])))
    monkeypatch.setattr(R, "read_window", lambda donor, game=None: calls.append(("read",)) or [])
    monkeypatch.setattr(R, "build_fragment", lambda win, donor: frag)
    monkeypatch.setattr(R, "outline", lambda f: ol)
    monkeypatch.setattr(R, "compose", compose)
    monkeypatch.setattr(R, "write_composition", write_composition)
    monkeypatch.setattr(R, "promote", _PROMOTE)
    monkeypatch.setattr(R.X, "block_parts", lambda **kw: {R.DIVERT_PREFAB: frozenset({"terrain", "sea4", "object"})})
    monkeypatch.setattr(DM, "_real_parts", lambda disc, lod="0_1", game=None: {})
    monkeypatch.setattr(cli, "find_game_path", lambda g=None: game)
    return SimpleNamespace(game=game, calls=calls)


def _files(game, folder=FOLDER):
    """``{Disc-relative path: bytes}`` of the folder's world files (no backups)."""
    tree = game / folder / "FF9_Data/WorldMap"
    return {p.relative_to(tree).as_posix(): p.read_bytes() for p in tree.rglob("Block*") if ".bak-" not in p.name} \
        if tree.is_dir() else {}


def _cells(files, disc=1):
    return sorted({D._parse_rel(r)[1] for r in files if r.startswith(f"Disc{disc}/")})


def _run(*argv):
    M.set_deploy_argv(list(argv))
    return cli.main(list(argv))


def test_a_move_judges_the_new_placement_as_if_the_old_river_were_gone(river, capsys, tmp_path):
    assert _run("world-river", "--mod-folder", FOLDER, "--at", OLD) == 0
    before = _files(river.game)
    assert _cells(before) == sorted(_cells_at((512.0, 128.0)))
    capsys.readouterr()
    # the control: the new placement overlaps the old river, so the plain run refuses B1 (this verb's own deploy)
    assert _run("world-river", "--mod-folder", FOLDER, "--at", NEW, "--dry-run") == 2
    err = capsys.readouterr().err                                        # the way out names the river's OWN place
    assert "`world-river --remove --at 512,128` takes it out, or `--move-from 512,128` moves it here" in err
    assert "--remove --at 512,192" not in err
    rep = tmp_path / "v.json"
    assert _run("world-river", "--mod-folder", FOLDER, "--at", NEW, "--move-from", OLD, "--dry-run",
                "--report-json", str(rep)) == 0
    out = capsys.readouterr().out
    assert "moving from --at 512,128: " in out and ", free for this one" in out
    assert "after removing the" in out and "Nothing written." in out
    assert _files(river.game) == before                                  # a dry run judges, and moves nothing
    v = json.loads(rep.read_text())
    assert v["ok"] and v["move_from"] == [512.0, 128.0] and v["at"] == [512.0, 192.0] and v["shift"] == [8, -3]
    assert sorted(map(tuple, v["blocks"])) == sorted(set(_cells_at((512.0, 128.0))) | set(_cells_at((512.0, 192.0))))
    assert any(r["gate"] == "B1 stack" and r["verdict"] == "green" for r in v["gates"])

    assert _run("world-river", "--mod-folder", FOLDER, "--at", NEW, "--move-from", OLD) == 0
    assert "moved: removed" in capsys.readouterr().out
    after = _files(river.game)
    assert _cells(after) == sorted(_cells_at((512.0, 192.0)))           # the old-only cells are empty
    assert _cells(after, 4) == sorted(_cells_at((512.0, 192.0)))        # ...on the disc-4 mirror too
    own = R.deploy_ownership(_cells_at((512.0, 192.0)), FOLDER, shift=(8, -3))
    assert own["foreign"] == [] and len(own["owned"]) == len(after)     # the moved river is the verb's own
    gone = [e for e in M.read_ledger(river.game / FOLDER) if e.get("op") == "remove"]
    assert gone and all(e["pipeline"]["op"] == "move" and e["pipeline"]["to"] == [512.0, 192.0] for e in gone)
    # where the river stands: the cell the move filled with the old river's very bytes reads as the NEW placement
    from ff9mapkit.world import riveredit as RE
    rs = RE.RiverShape(tris=None, ring=None, blocks=[], cells=list(HOME), cells_shift=(8, -2),
                       shifts=[(8, -2), (8, -3)])
    assert [s for s, _p in RE.placements(rs, FOLDER)] == [(8, -3)]
    # and it moves back, the way it came
    assert _run("world-river", "--mod-folder", FOLDER, "--at", OLD, "--move-from", NEW) == 0
    assert _files(river.game) == before


def test_a_refused_move_changes_nothing(river, capsys):
    assert _run("world-river", "--mod-folder", FOLDER, "--at", OLD) == 0
    before = _files(river.game)
    other = _override(river.game, "OTHER", 1, 0, 10)                     # a new-only cell another folder holds
    capsys.readouterr()
    assert _run("world-river", "--mod-folder", FOLDER, "--at", NEW, "--move-from", OLD) == 2
    assert "B1: the stack already overrides these cells" in capsys.readouterr().err
    assert _files(river.game) == before and not [e for e in M.read_ledger(river.game / FOLDER) if e.get("op")]
    other.unlink()
    hand = river.game / FOLDER / "FF9_Data/WorldMap/Disc1/0_1/r11/Block[1][11] Sea4.ff9mesh"
    hand.write_bytes(b"F9WM hand")                                       # a hand edit on an old cell
    assert _run("world-river", "--mod-folder", FOLDER, "--at", NEW, "--move-from", OLD) == 2
    assert "R1: 1 file(s) on the old placement's cells are not this verb's deploy there" in capsys.readouterr().err
    assert hand.read_bytes() == b"F9WM hand" and not [e for e in M.read_ledger(river.game / FOLDER) if e.get("op")]
    assert _run("world-river", "--mod-folder", FOLDER, "--at", OLD, "--move-from", "512,0", "--dry-run") == 2
    assert "R0: no world-river deploy at 512,0" in capsys.readouterr().err
    assert _run("world-river", "--mod-folder", FOLDER, "--at", NEW, "--move-from", "auto") == 2
    assert _run("world-river", "--mod-folder", FOLDER, "--at", NEW, "--move-from", OLD, "--remove") == 2


def test_the_river_row_and_its_recipe(river):
    from ff9mapkit.world import fuse as FU
    from ff9mapkit.world import recipe as RC
    row = RC.row_for(["world-river", "--mod-folder", "-", "--at=512,192", "--move-from=512,128"])
    assert row == {"table": "river", "at": [512.0, 192.0], "move_from": [512.0, 128.0]}
    assert RC.label(row) == "move the river from 512, 128 to 512, 192"
    assert RC.label({"table": "river", "at": [512.0, 128.0]}) == "river at 512, 128"
    with pytest.raises(ValueError, match="plain cluster-c carry"):
        RC.row_for(["world-river", "--mod-folder", "-", "--at", "auto"])
    assert _run("world-river", "--mod-folder", FOLDER, "--at", OLD) == 0
    out = FU.compose_layout(FOLDER, {"river": [{k: v for k, v in row.items() if k != "table"}]}, game=river.game)
    assert out["clean"], out["gates"]
    assert _cells(_files(river.game)) == sorted(_cells_at((512.0, 192.0)))


def test_the_stack_read_lets_a_draft_stand_in_for_its_source(river, tmp_path):
    _override(river.game, FOLDER, 1, 0, 11)
    _override(river.game, "OTHER", 1, 0, 12)
    draft = D.ensure_draft(river.game / FOLDER, game=river.game, root=tmp_path / "drafts")
    assert D.stands_in_for(draft) == FOLDER and D.stands_in_for(FOLDER) is None
    occ = R.stack_occupancy([(0, 11), (0, 12)], str(draft), discs=(1,))
    assert sorted(occ) == [(str(draft), 1), ("OTHER", 1)]               # the draft's copy, never the source's too
    (draft / "FF9_Data/WorldMap/Disc1/0_1/r11/Block[0][11] Terrain.ff9mesh").unlink()
    assert sorted(R.stack_occupancy([(0, 11), (0, 12)], str(draft), discs=(1,))) == [("OTHER", 1)]


# ---------------------------------------------------------------- the draft: deletions, and the ledger with the bytes
def _move_in_draft(river, tmp_path):
    assert _run("world-river", "--mod-folder", FOLDER, "--at", OLD) == 0
    live0 = _files(river.game)
    draft = D.ensure_draft(river.game / FOLDER, game=river.game, root=tmp_path / "drafts")
    D.begin_step(draft, D.all_cells())
    assert _run("world-river", "--mod-folder", str(draft), "--at", NEW, "--move-from", OLD) == 0
    D.commit_step(draft, {"table": "river", "at": [512.0, 192.0], "move_from": [512.0, 128.0]}, "move")
    return draft, live0


def test_a_move_in_a_draft_promotes_its_deletions_and_stays_the_verb_s_own(river, tmp_path):
    draft, live0 = _move_in_draft(river, tmp_path)
    old_only = set(_cells_at((512.0, 128.0))) - set(_cells_at((512.0, 192.0)))
    assert D.removals(draft) and all(D._parse_rel(r)[1] in old_only for r in D.removals(draft))
    assert any(b[1:] in old_only for b in D.edited_blocks(draft))      # the caption counts a removal too
    assert _files(river.game) == live0                                   # nothing live until Promote
    rec = D.promote(draft, game=river.game, log=lambda *a: None)
    live = _files(river.game)
    assert _cells(live) == sorted(_cells_at((512.0, 192.0))) and _cells(live, 4) == _cells(live)
    assert rec["removed"] and all(rec["tags"][r]["verb"] == "world-river" for r in rec["promoted"])
    own = R.deploy_ownership(_cells_at((512.0, 192.0)), FOLDER, shift=(8, -3))
    assert own["foreign"] == [] and len(own["owned"]) == len(live)     # promoted, and still the verb's own
    assert D.edits(draft) == [] and D.removals(draft) == [] and D.stale(draft) == []
    # level with the live folder, its ledger too: a second move in the same draft reads its own river
    assert _run("world-river", "--mod-folder", str(draft), "--at", OLD, "--move-from", NEW, "--dry-run") == 0
    # Revert: the live folder exactly as before, the move the draft's edit again (owned in the draft's ledger)
    D.revert(draft, game=river.game, log=lambda *a: None)
    assert _files(river.game) == live0
    assert D.removals(draft) and D.edits(draft)
    own = R.deploy_ownership(_cells_at((512.0, 192.0)), str(draft), shift=(8, -3), discs=(1,))
    assert own["foreign"] == [] and own["owned"]
    assert R.deploy_ownership(_cells_at((512.0, 128.0)), FOLDER, shift=(8, -2))["foreign"] == []


def test_undo_and_redo_put_the_ledger_back_with_the_bytes(river, tmp_path):
    draft, _live0 = _move_in_draft(river, tmp_path)
    moved = (draft / D.LEDGER).read_bytes()
    D.undo(draft)
    assert R.deploy_ownership(_cells_at((512.0, 128.0)), str(draft), shift=(8, -2))["foreign"] == []
    assert _run("world-river", "--mod-folder", str(draft), "--at", NEW, "--move-from", OLD, "--dry-run") == 0
    D.redo(draft)
    assert (draft / D.LEDGER).read_bytes() == moved
    assert R.deploy_ownership(_cells_at((512.0, 192.0)), str(draft), shift=(8, -3), discs=(1,))["foreign"] == []


def test_a_promote_of_a_removal_refuses_when_the_live_file_moved(river, tmp_path):
    draft, _live0 = _move_in_draft(river, tmp_path)
    rel = D.removals(draft)[0]
    (river.game / FOLDER / rel).write_bytes(b"F9WM another session")
    with pytest.raises(ValueError, match="changed in FF9CustomMap-world since the draft was made"):
        D.promote(draft, game=river.game, log=lambda *a: None)
    assert (river.game / FOLDER / rel).read_bytes() == b"F9WM another session"


# ---------------------------------------------------------------- THE ACCEPTANCE, on real bytes
def test_on_real_bytes_the_hand_typed_move_and_the_recipe_row_write_the_same(tmp_path):
    """A draft of the real FF9CustomMap-world (read only: every write lands in the tmp drafts), the river read where
    it stands by the ledger, moved to the nearest free placement by the command typed by hand into one draft and by
    the recipe's [[river]] row into another: the same bytes, the old river's cells emptied, and the moved river the
    verb's own."""
    import warnings
    from ff9mapkit.world import recipe as RC
    from ff9mapkit.world import riveredit as RE
    from .test_worldcoast import REAL_GAME
    if REAL_GAME is None or not (REAL_GAME / FOLDER).is_dir():
        warnings.warn("the river move went unchecked on real bytes: no FF9 install + UnityPy + FF9CustomMap-world. "
                      "Re-run in the MAIN repo (C:/gd/Dream-World-IX/ff9mapkit).", UserWarning)
        pytest.skip("needs the FF9 install + UnityPy + FF9CustomMap-world")
    rs = RE.shape(game=REAL_GAME)
    here = RE.placements(rs, FOLDER, game=REAL_GAME)
    if not here:
        pytest.skip(f"no world-river deploy in {FOLDER} to move")
    at, mine = here[0]
    hand = D.ensure_draft(REAL_GAME / FOLDER, game=REAL_GAME, root=tmp_path / "hand")
    free = [s for s in rs.shifts if not RE.same_shift(s, at)
            and not R.stack_occupancy(rs.cells_at(s), str(hand), game=REAL_GAME,
                                      ignore=frozenset(hand / Path(p).relative_to(REAL_GAME / FOLDER) for p in mine))]
    if not free:
        pytest.skip(f"no placement is free for the river at {at} to move to")
    argv = RE.command(hand, free[0], move_from=at, dry_run=False)
    assert cli.main(["--game", str(REAL_GAME)] + argv) == 0
    composed = D.ensure_draft(REAL_GAME / FOLDER, game=REAL_GAME, root=tmp_path / "composed")
    recipe = tmp_path / "move.toml"
    recipe.write_text(RC.dumps([RC.row_for(RE.command("-", free[0], move_from=at, dry_run=False))]), encoding="utf-8")
    assert cli.main(["--game", str(REAL_GAME), "world-fuse", str(recipe), "--mod-folder", str(composed)]) == 0

    def world(root):
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in (root / "FF9_Data/WorldMap").rglob("Block*")
                if ".bak-" not in p.name}
    assert world(hand) == world(composed)
    assert D.removals(hand) and D.edits(hand)
    gone = set(rs.cells_at(at)) - set(rs.cells_at(free[0]))
    assert not R.stack_occupancy(sorted(gone), str(hand), discs=(1,), game=REAL_GAME).get((str(hand), 1))
    own = R.deploy_ownership(rs.cells_at(free[0]), str(hand), shift=free[0], discs=(1,), game=REAL_GAME)
    assert own["owned"] and own["foreign"] == []
