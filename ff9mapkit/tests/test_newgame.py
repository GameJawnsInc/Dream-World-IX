"""ff9mapkit.newgame -- the New-Game entry wiring extracted from tools/wire_newgame_from_stock.py +
tools/retarget_newgame_warp.py (now thin shims). Pure-logic coverage + an install-gated faithfulness check."""
from __future__ import annotations

from pathlib import Path

import pytest

from ff9mapkit import newgame


def test_live_overrides_globs_only_customfolders(tmp_path):
    game = tmp_path / "FF9"
    a = game / "FF9CustomMap" / "x" / "us" / "evt_alex1_ts_opening.eb.bytes"
    b = game / "FF9CustomMap-bb" / "y" / "evt_alex1_ts_opening.eb.bytes"
    other = game / "SomeOtherMod" / "evt_alex1_ts_opening.eb.bytes"   # not FF9CustomMap* -> ignored
    for p in (a, b, other):
        p.parent.mkdir(parents=True)
        p.write_bytes(b"x")
    found = newgame.live_overrides(game)
    assert a in found and b in found
    assert other not in found


def test_retarget_no_override_is_not_ok(tmp_path):
    res = newgame.retarget(tmp_path / "FF9", 4100, backups_dir=tmp_path / "bk", reverts_dir=tmp_path / "rv",
                           verbose=False)
    assert res["found"] == 0 and res["ok"] is False and res["revert"] is None


def test_emit_revert_writes_runnable_script(tmp_path):
    p = newgame._emit_revert(tmp_path / "rv", "revert_x.py", ['print("reverted")'])
    assert p.is_file() and p.name == "revert_x.py"
    assert 'print("reverted")' in p.read_text(encoding="utf-8")


def test_cli_registers_newgame():
    from ff9mapkit import cli
    ns = cli.build_parser().parse_args(["newgame", "6000"])
    assert ns.func.__name__ == "_cmd_newgame" and ns.field_id == 6000 and ns.mod_folder == "FF9CustomMap"


def test_global_game_and_modfolder_survive_subcommand_redeclare():
    """A subcommand redeclaring --game/--mod-folder (needed so `ff9mapkit newgame 6000 --mod-folder X` still
    works) must NOT silently reset a value the user gave BEFORE the subcommand name back to the subcommand's
    own default -- argparse copies the sub-namespace's declared defaults over the parent's on every parse."""
    from ff9mapkit import cli
    p = cli.build_parser()
    ns = p.parse_args(["--game", "C:/MyCustomFF9Install", "model-export", "GEO_MAIN_F0_VIV"])
    assert ns.game == "C:/MyCustomFF9Install"
    ns2 = p.parse_args(["--mod-folder", "FF9CustomMap-bb", "newgame", "6000"])
    assert ns2.mod_folder == "FF9CustomMap-bb"
    # the sub-level flag, given explicitly, still wins over the global one
    ns3 = p.parse_args(["newgame", "6000", "--mod-folder", "FF9CustomMap-ih"])
    assert ns3.mod_folder == "FF9CustomMap-ih"
    # neither given anywhere -> each level's own documented default holds
    ns4 = p.parse_args(["model-export", "GEO_MAIN_F0_VIV"])
    assert ns4.game is None
    ns5 = p.parse_args(["newgame", "6000"])
    assert ns5.mod_folder == "FF9CustomMap"
    # the world verbs whose --mod-folder is optional inherit the global value the same way
    ns6 = p.parse_args(["--mod-folder", "FF9CustomMap-world", "world-coast", "--cells", "1,1", "--donor", "18,15"])
    assert ns6.mod_folder == "FF9CustomMap-world"
    ns7 = p.parse_args(["--mod-folder", "FF9CustomMap-world", "world-encounters", "--config", "x.toml"])
    assert ns7.mod_folder == "FF9CustomMap-world"
    ns8 = p.parse_args(["--mod-folder", "FF9CustomMap-world", "world-morphs"])
    assert ns8.mod_folder == "FF9CustomMap-world"


def _install_game():
    try:
        from ff9mapkit.config import find_game_path
        g = find_game_path()
        return g if (g and Path(g).is_dir()) else None
    except Exception:
        return None


@pytest.mark.skipif(_install_game() is None, reason="needs the FF9 install (BYO p0data)")
def test_wire_from_stock_dryrun_matches_tool(tmp_path):
    """The package dry-run reproduces the in-game-proven tool: stock field 70 warps Field(50); the override
    repoints it to the target across 7 langs; dry-run writes nothing."""
    g = _install_game()
    try:
        res = newgame.wire_from_stock(g, 6000, backups_dir=tmp_path / "bk", reverts_dir=tmp_path / "rv",
                                      dry_run=True, verbose=False)
    except Exception as e:                                   # UnityPy missing / bundle unreadable
        pytest.skip(f"needs install + UnityPy: {e}")
    assert res["ok"] is True
    assert res["stock_dest"] == 50 and res["new_dest"] == 6000
    assert len(res["files"]) == 7
    assert res["revert"] is None                            # dry-run: nothing written
    assert not (tmp_path / "rv").exists()
