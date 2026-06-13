"""The tk-free build/deploy/import job layer (:mod:`ff9mapkit.editor.jobs`): argv builders + the file-kind
detector + the deploy-target reader -- the backend the Build & Deploy and Import GUIs are a view over. No
Tk, no Qt, no game install needed (these are pure path/argv shape, the part worth pinning)."""

from __future__ import annotations

import sys

from ff9mapkit.editor import jobs


# --------------------------------------------------------------------------- import argv
def test_import_args_native_full_carry():
    a = jobs.import_args("alexandria", out="/o", field_id=4003, art="native",
                         carry_npcs=True, carry_text=True, dialogue_stubs=False, save_moogle=False)
    assert a == ["import", "alexandria", "--out", "/o", "--id", "4003", "--native",
                 "--graft-player-funcs", "--carry-text"]


def test_import_args_borrow_bare_room():
    a = jobs.import_args("100", out="/o", field_id=4003, art="borrow",
                         carry_npcs=False, carry_text=False)
    assert a == ["import", "100", "--out", "/o", "--id", "4003"]


def test_import_args_editable_with_name_and_save_moogle():
    a = jobs.import_args("grgr", out="/o", field_id=5000, name="GRGR", art="editable",
                         carry_npcs=False, carry_text=False, dialogue_stubs=True, save_moogle=True)
    assert a[:7] == ["import", "grgr", "--out", "/o", "--id", "5000", "--name"]
    assert "--editable" in a and "--graft-player-funcs" in a       # save-moogle implies the player-func graft
    assert "--dialogue" in a and "--save-moogle" in a and "--carry-text" not in a


# --------------------------------------------------------------------------- deploy / revert argv
def test_build_argv_single_field():
    a = jobs.build_argv("X.field.toml", "/out")
    assert a == [sys.executable, "-m", "ff9mapkit", "build", "X.field.toml", "--out", "/out",
                 "--mod-name", "FF9CustomMap"]


def test_build_campaign_argv():
    assert jobs.build_campaign_argv("c.toml") == [sys.executable, "-m", "ff9mapkit", "build-all", "c.toml"]


def test_deploy_field_argv_runs_the_tool(tmp_path):
    a = jobs.deploy_field_argv(tmp_path, "X.field.toml")
    assert a[0] == sys.executable and a[-1] == "X.field.toml"
    assert a[1].replace("\\", "/").endswith("tools/deploy_field.py")


def test_deploy_campaign_argv_no_warp_by_default(tmp_path):
    a = jobs.deploy_campaign_argv(tmp_path, "c.toml")
    assert "--apply" in a and "--no-warp" in a
    assert jobs.deploy_campaign_argv(tmp_path, "c.toml", wire_newgame=True)[-1] == "--apply"  # warp on -> no flag


def test_deploy_battle_argv_optional_trigger(tmp_path):
    assert "--trigger-field" not in jobs.deploy_battle_argv(tmp_path, "b.toml")
    a = jobs.deploy_battle_argv(tmp_path, "b.toml", trigger="4003")
    assert a[-2:] == ["--trigger-field", "4003"]


def test_revert_argv_paths(tmp_path):
    assert jobs.revert_field_argv(tmp_path)[1].replace("\\", "/").endswith("scroll_out/revert_deploy.py")
    assert jobs.revert_campaign_argv(tmp_path)[1].replace("\\", "/").endswith("scroll_out/revert_campaign.py")
    assert jobs.revert_battle_argv(tmp_path) is None                # no revert_battle_*.py -> nothing to undo


# --------------------------------------------------------------------------- detection
def test_detect_kind_field_vs_campaign_vs_battle(tmp_path):
    field = tmp_path / "x.field.toml"
    field.write_text('[field]\nid = 4003\nname = "X"\narea = 11\n', encoding="utf-8")
    assert jobs.detect_kind(field)[0] == "field"
    assert jobs.field_id_name(field) == (4003, "X")

    battle = tmp_path / "b.battle.toml"
    battle.write_text('[battlemap]\nbbg = "BBG_B001"\n', encoding="utf-8")
    assert jobs.detect_kind(battle)[0] == "battle"


def test_detect_deploy_target_reads_pin(tmp_path):
    assert jobs.detect_deploy_target(tmp_path) == ("FF9CustomMap", None)   # no file -> defaults
    (tmp_path / ".ff9deploy.toml").write_text('mod_folder = "FF9CustomMap-ic"\nid = 30004\n', encoding="utf-8")
    assert jobs.detect_deploy_target(tmp_path) == ("FF9CustomMap-ic", 30004)
