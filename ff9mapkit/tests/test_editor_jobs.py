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


def test_import_args_verbatim_truest_fork():
    # the recommended path: --verbatim ships the donor's whole .eb + .mes (real logic) -- a short command.
    a = jobs.import_args("100", out="/o", field_id=4003, verbatim=True)
    assert a == ["import", "100", "--out", "/o", "--id", "4003", "--verbatim"]


def test_import_args_verbatim_ignores_art_and_carry():
    # verbatim implies --native + carries everything itself, so NO art/carry flags are emitted (only --verbatim).
    a = jobs.import_args("grgr", out="/o", field_id=5000, name="GRGR", art="editable",
                         carry_npcs=True, carry_text=True, dialogue_stubs=True, save_moogle=True, verbatim=True)
    assert a == ["import", "grgr", "--out", "/o", "--id", "5000", "--name", "GRGR", "--verbatim"]
    assert not any(f in a for f in ("--native", "--editable", "--graft-player-funcs", "--carry-text",
                                    "--dialogue", "--save-moogle"))


def test_import_args_verbatim_native_default_combo():
    # the EXACT combo the GUI passes (art='native' is the default + verbatim): --verbatim short-circuits BEFORE
    # the art branch, so it does NOT also emit --native (pins the early-return order against a refactor).
    a = jobs.import_args("100", out="/o", field_id=4003, art="native", verbatim=True)
    assert a == ["import", "100", "--out", "/o", "--id", "4003", "--verbatim"]


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


def test_detect_kind_journey(tmp_path):
    # a journeys.toml ([hub] + [[journey]]) is a 4th kind -- table-disjoint from field/campaign/battle, and
    # the parsed manifest comes back as the payload (so the Build panel can show the hub/journey counts).
    j = tmp_path / "journeys.toml"
    j.write_text('[hub]\nname = "H"\nid = 4600\n\n[[journey]]\nid = "a"\nentry = 4100\n', encoding="utf-8")
    kind, manifest = jobs.detect_kind(j)
    assert kind == "journey" and manifest is not None and len(manifest.journeys) == 1
    # a field.toml must NOT be mistaken for a journey (no [hub]/[[journey]])
    field = tmp_path / "f.field.toml"
    field.write_text('[field]\nid = 4003\nname = "X"\narea = 11\n', encoding="utf-8")
    assert jobs.detect_kind(field)[0] == "field"


def test_deploy_journey_argv(tmp_path):
    base = jobs.deploy_journey_argv(tmp_path, "j.toml")
    assert base[1].replace("\\", "/").endswith("tools/deploy_journey.py") and base[-1] == "j.toml"
    assert "--apply" not in base and "--apply-links" not in base          # default = a safe dry-run
    ap = jobs.deploy_journey_argv(tmp_path, "j.toml", apply=True, wire_newgame=True)
    assert "--apply" in ap and "--wire-newgame" in ap
    lk = jobs.deploy_journey_argv(tmp_path, "j.toml", apply_links=True)
    assert "--apply-links" in lk and "--apply" not in lk
    # --wire-newgame is gated under --apply (a no-op alone) -> not emitted without it
    assert "--wire-newgame" not in jobs.deploy_journey_argv(tmp_path, "j.toml", wire_newgame=True)


def test_fork_command_argv(tmp_path):
    cmd = ("import-chain 300 --out ice_cavern --verbatim --id-base 6200 --name-prefix ICEC "
           "--mod-folder FF9CustomMap-icec --flags-per-field 16")
    argv = jobs.fork_command_argv(cmd, out_abs=tmp_path / "ice_cavern")
    assert argv[1:5] == ["-m", "ff9mapkit", "import-chain", "300"]
    assert argv[argv.index("--out") + 1] == str(tmp_path / "ice_cavern")   # --out -> absolute path
    assert "--verbatim" in argv and "--flags-per-field" in argv
    # without out_abs the relative --out is preserved (the literal playbook value)
    assert jobs.fork_command_argv(cmd)[argv.index("--out") + 1] == "ice_cavern"


def test_newgame_argv(tmp_path):
    a = jobs.newgame_retarget_argv(tmp_path, 4100)
    assert a[1].replace("\\", "/").endswith("tools/retarget_newgame_warp.py") and a[-1] == "4100"
    r = jobs.revert_newgame_argv(tmp_path)
    assert r[1].replace("\\", "/").endswith("scroll_out/revert_newgame_retarget.py")


def test_revert_journey_argv_picks_most_recent(tmp_path):
    # the journey revert must undo the user's LAST action: --apply writes revert_journey.py, --apply-links
    # writes revert_journey_links.py -- the GUI button picks whichever is newer (mtime), or None if neither.
    import os
    scroll = tmp_path / "tools" / "scroll_out"
    scroll.mkdir(parents=True)
    assert jobs.revert_journey_argv(tmp_path) is None              # no journey deploy -> nothing to undo
    full = scroll / "revert_journey.py"
    links = scroll / "revert_journey_links.py"
    full.write_text("# unified\n", encoding="utf-8")
    links.write_text("# links\n", encoding="utf-8")
    os.utime(full, (1000, 1000))                                   # links-only applied LAST -> it wins
    os.utime(links, (2000, 2000))
    assert jobs.revert_journey_argv(tmp_path)[-1].replace("\\", "/").endswith("scroll_out/revert_journey_links.py")
    os.utime(full, (3000, 3000))                                   # a fresh full --apply -> the unified wins again
    assert jobs.revert_journey_argv(tmp_path)[-1].replace("\\", "/").endswith("scroll_out/revert_journey.py")


def test_detect_deploy_target_reads_pin(tmp_path):
    assert jobs.detect_deploy_target(tmp_path) == ("FF9CustomMap", None)   # no file -> defaults
    (tmp_path / ".ff9deploy.toml").write_text('mod_folder = "FF9CustomMap-ic"\nid = 30004\n', encoding="utf-8")
    assert jobs.detect_deploy_target(tmp_path) == ("FF9CustomMap-ic", 30004)
