"""The tk-free build/deploy/import job layer (:mod:`ff9mapkit.editor.jobs`): argv builders + the file-kind
detector + the deploy-target reader -- the backend the Build & Deploy and Import GUIs are a view over. No
Tk, no Qt, no game install needed (these are pure path/argv shape, the part worth pinning)."""

from __future__ import annotations

import sys

import pytest

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


def test_import_args_swap_player_lands_before_verbatim_return():
    # --swap-player implies --verbatim in the CLI, so the swap flags must land BEFORE the verbatim short-
    # circuit (the GUI sends verbatim=True when a swap is set). --neutralize-gestures rides along.
    a = jobs.import_args("100", out="/o", field_id=4003, verbatim=True,
                         swap_player="vivi", neutralize_gestures=True)
    assert a == ["import", "100", "--out", "/o", "--id", "4003",
                 "--swap-player", "vivi", "--neutralize-gestures", "--verbatim"]


def test_import_args_swap_player_emitted_on_reauthorable_path_too():
    # a swap on the re-authorable path still emits the flags (the CLI forces verbatim there); a bare model
    # id works as WHO, and --neutralize-gestures is omitted unless ticked.
    a = jobs.import_args("100", out="/o", field_id=4003, art="native", carry_npcs=False, carry_text=False,
                         swap_player="199")
    assert a[a.index("--swap-player") + 1] == "199" and "--native" in a
    assert "--neutralize-gestures" not in a


# --------------------------------------------------------------------------- import-chain (region fork) argv
def test_import_chain_args_dryrun_default_whole_zone_verbatim():
    # no out -> the DRY-RUN (blast-radius preview); whole-zone + verbatim are the GUI defaults
    a = jobs.import_chain_args("300")
    assert a == ["import-chain", "300", "--whole-zone", "--verbatim"]
    assert "--out" not in a                                            # dry-run touches nothing


def test_import_chain_args_fork_with_options():
    a = jobs.import_chain_args("50,100,64", out="/c", id_base=6000, name_prefix="OPEN")
    assert a[:3] == ["import-chain", "50,100,64", "--whole-zone"]
    assert a[a.index("--out") + 1] == "/c"
    assert a[a.index("--id-base") + 1] == "6000" and a[a.index("--name-prefix") + 1] == "OPEN"
    assert "--fresh-ids" not in a                                      # stable ids are the default (saves survive)


def test_import_chain_args_fresh_ids_and_no_flags_off():
    # --fresh-ids only when ticked; whole_zone/verbatim togglable off
    a = jobs.import_chain_args("300", out="/c", whole_zone=False, verbatim=False, fresh_ids=True)
    assert a == ["import-chain", "300", "--out", "/c", "--fresh-ids"]


def test_import_chain_args_idbase_blank_vs_zero():
    # blank id_base (the GUI sends None) OMITS --id-base so the CLI/.ff9deploy.toml default applies;
    # id_base=0 is still emitted (the guard is `is not None`, not truthiness)
    assert "--id-base" not in jobs.import_chain_args("300", out="/c", id_base=None)
    z = jobs.import_chain_args("300", out="/c", id_base=0)
    assert z[z.index("--id-base") + 1] == "0"


def test_import_chain_args_single_toggles_and_optional_kwargs():
    # each flag is independently controlled
    assert jobs.import_chain_args("300", out="/c", whole_zone=True, verbatim=False) == \
        ["import-chain", "300", "--whole-zone", "--out", "/c"]
    assert jobs.import_chain_args("300", out="/c", whole_zone=False, verbatim=True) == \
        ["import-chain", "300", "--verbatim", "--out", "/c"]
    # the optional pass-throughs (GUI-unused today, but the contract is pinned)
    a = jobs.import_chain_args("300", out="/c", flags_per_field=16, max_fields=40, campaign_name="OPEN")
    assert a[a.index("--flags-per-field") + 1] == "16" and a[a.index("--max-fields") + 1] == "40"
    assert a[a.index("--campaign-name") + 1] == "OPEN"


def test_import_chain_args_swap_player_and_neutralize():
    # play the whole chain as one character; --neutralize-gestures rides along when ticked
    a = jobs.import_chain_args("300", out="/c", swap_player="vivi", neutralize_gestures=True)
    assert a[a.index("--swap-player") + 1] == "vivi" and "--neutralize-gestures" in a
    # no swap -> neither flag is emitted (the common case)
    b = jobs.import_chain_args("300", out="/c")
    assert "--swap-player" not in b and "--neutralize-gestures" not in b


def test_import_chain_args_ids_scopes_to_cluster():
    # ids -> --ids (a story-state cluster); it SUPPRESSES --whole-zone even if whole_zone is also True
    a = jobs.import_chain_args("100", out="/c", ids="100-117", whole_zone=True)
    assert a[a.index("--ids") + 1] == "100-117" and "--whole-zone" not in a
    # no ids -> whole_zone path (unchanged)
    b = jobs.import_chain_args("100", out="/c", ids=None, whole_zone=True)
    assert "--whole-zone" in b and "--ids" not in b


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


def test_deploy_campaign_argv_threads_mod_folder(tmp_path):
    # the dev/repo path must pin the campaign's DECLARED folder, else deploy_campaign.py falls back to
    # .ff9deploy.toml/FF9CustomMap and silently disagrees with the UI label (the FF9CustomMap-ow redirect bug)
    a = jobs.deploy_campaign_argv(tmp_path, "c.toml", mod_folder="FF9CustomMap-ow")
    assert a[a.index("--mod-folder") + 1] == "FF9CustomMap-ow"
    assert "--mod-folder" not in jobs.deploy_campaign_argv(tmp_path, "c.toml")  # omitted -> back-compat


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
    # the 3-way New-Game landing: none (no flag) / hub / entry -> --newgame <mode>, gated under --apply
    assert "--newgame" not in jobs.deploy_journey_argv(tmp_path, "j.toml", apply=True, newgame="none")
    hub = jobs.deploy_journey_argv(tmp_path, "j.toml", apply=True, newgame="hub")
    assert hub[-2:] == ["--newgame", "hub"]
    ent = jobs.deploy_journey_argv(tmp_path, "j.toml", apply=True, newgame="entry")
    assert ent[-2:] == ["--newgame", "entry"]
    assert "--newgame" not in jobs.deploy_journey_argv(tmp_path, "j.toml", newgame="hub")  # gated under --apply
    # explicit newgame= wins over the wire_newgame alias
    both = jobs.deploy_journey_argv(tmp_path, "j.toml", apply=True, newgame="entry", wire_newgame=True)
    assert "--newgame" in both and "entry" in both and "--wire-newgame" not in both


def test_newgame_from_stock_argv_carries_the_mod_folder(tmp_path):
    """The re-wire must target the SAME folder the casualty was read from. Both argv builders default the
    folder to FF9CustomMap, but a campaign whose mod_folder is something else needs it threaded through --
    else the wholesale deploy wipes the override in that folder and the re-wire restores it in FF9CustomMap.
    LAW (not the number): whatever folder is passed lands on --mod-folder, in both the repo-tool and the
    installed-package variant."""
    dev = jobs.newgame_from_stock_argv(tmp_path, 6000, mod_folder="FF9CustomMap-ow")
    assert dev[-2:] == ["--mod-folder", "FF9CustomMap-ow"] and "6000" in dev
    pkg = jobs.newgame_from_stock_pkg_argv(6000, mod_folder="FF9CustomMap-ow")
    assert pkg[-2:] == ["--mod-folder", "FF9CustomMap-ow"] and "6000" in pkg
    # the default is still FF9CustomMap (the common case is untouched)
    assert jobs.newgame_from_stock_argv(tmp_path, 6000)[-2:] == ["--mod-folder", "FF9CustomMap"]
    assert jobs.newgame_from_stock_pkg_argv(6000)[-2:] == ["--mod-folder", "FF9CustomMap"]


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
    # the robust path the GUI uses: CREATE the field-70 override from stock (works on a clean install)
    a = jobs.newgame_from_stock_argv(tmp_path, 6000)
    # target id is the positional arg; the folder rides on --mod-folder (default FF9CustomMap) so a re-wire
    # can be aimed at a campaign's own folder -- see test_newgame_from_stock_argv_carries_the_mod_folder
    assert a[1].replace("\\", "/").endswith("tools/wire_newgame_from_stock.py") and "6000" in a
    assert a[-2:] == ["--mod-folder", "FF9CustomMap"]
    # the patch-only twin still available
    b = jobs.newgame_retarget_argv(tmp_path, 4100)
    assert b[1].replace("\\", "/").endswith("tools/retarget_newgame_warp.py") and b[-1] == "4100"


def test_revert_newgame_picks_most_recent(tmp_path):
    # New-Game revert must undo the LAST wiring action: from-stock writes revert_newgame_from_stock.py, the
    # patch writes revert_newgame_retarget.py -- pick whichever is newer (mtime), or None if neither exists.
    import os
    scroll = tmp_path / "tools" / "scroll_out"
    scroll.mkdir(parents=True)
    assert jobs.revert_newgame_argv(tmp_path) is None and jobs.latest_newgame_revert(tmp_path) is None
    stock = scroll / "revert_newgame_from_stock.py"
    retarget = scroll / "revert_newgame_retarget.py"
    stock.write_text("# stock\n", encoding="utf-8")
    retarget.write_text("# retarget\n", encoding="utf-8")
    os.utime(stock, (1000, 1000))                                  # retarget written LAST -> it wins
    os.utime(retarget, (2000, 2000))
    assert jobs.revert_newgame_argv(tmp_path)[-1].endswith("revert_newgame_retarget.py")
    os.utime(stock, (3000, 3000))                                  # now from-stock is newest
    assert jobs.revert_newgame_argv(tmp_path)[-1].endswith("revert_newgame_from_stock.py")


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


# ---- installed-copy deploy: the package CLI argv builders + per-user revert cache --------------------
def test_deploy_campaign_pkg_argv():
    a = jobs.deploy_campaign_pkg_argv("c.toml", mod_folder="FF9CustomMap-ow")
    assert a[1:3] == ["-m", "ff9mapkit"] and a[3] == "deploy-campaign" and a[4] == "c.toml"
    assert "--apply" in a and a[a.index("--mod-folder") + 1] == "FF9CustomMap-ow"
    assert "--no-warp" in a                                              # New Game off by default
    assert "--no-warp" not in jobs.deploy_campaign_pkg_argv("c.toml", wire_newgame=True)  # warp on -> no flag


def test_deploy_journey_pkg_argv():
    base = jobs.deploy_journey_pkg_argv("j.toml")
    assert base[3] == "deploy-journey" and base[-1] == "j.toml"
    assert "--apply" not in base and "--apply-links" not in base        # default = dry-run
    ap = jobs.deploy_journey_pkg_argv("j.toml", apply=True, newgame="hub", single_folder=True)
    assert "--apply" in ap and "--single-folder" in ap and ap[ap.index("--newgame") + 1] == "hub"
    assert "--newgame" not in jobs.deploy_journey_pkg_argv("j.toml", apply=True, newgame="none")
    lk = jobs.deploy_journey_pkg_argv("j.toml", apply_links=True)
    assert "--apply-links" in lk and "--apply" not in lk


def test_revert_pkg_argv_reads_cache(tmp_path, monkeypatch):
    from ff9mapkit import provision
    monkeypatch.setattr(provision, "deploy_reverts_dir", lambda: tmp_path / "rv")
    assert jobs.revert_campaign_pkg_argv() is None and jobs.revert_journey_pkg_argv() is None   # empty cache
    (tmp_path / "rv").mkdir()
    (tmp_path / "rv" / "revert_campaign.py").write_text("print('x')", encoding="utf-8")
    a = jobs.revert_campaign_pkg_argv()
    assert a and a[-1].endswith("revert_campaign.py")
    assert jobs.revert_journey_pkg_argv() is None                       # journey revert still absent


def test_newgame_pkg_argv_and_revert(tmp_path, monkeypatch):
    a = jobs.newgame_from_stock_pkg_argv(6000)
    assert a[1:4] == ["-m", "ff9mapkit", "newgame"] and a[4] == "6000"
    assert a[a.index("--mod-folder") + 1] == "FF9CustomMap"
    from ff9mapkit import provision
    monkeypatch.setattr(provision, "deploy_reverts_dir", lambda: tmp_path / "rv")
    assert jobs.revert_newgame_pkg_argv() is None                       # empty cache
    (tmp_path / "rv").mkdir()
    (tmp_path / "rv" / "revert_newgame_from_stock.py").write_text("x", encoding="utf-8")
    r = jobs.revert_newgame_pkg_argv()
    assert r and r[-1].endswith("revert_newgame_from_stock.py")


def test_resolve_dev_repo(tmp_path, monkeypatch):
    repo = tmp_path / "checkout"
    (repo / "tools").mkdir(parents=True)
    (repo / "tools" / "deploy_field.py").write_text("", encoding="utf-8")
    venv = tmp_path / "venv_lib"; venv.mkdir()             # installed-like: no tools/
    # 1) $FF9_REPO that IS a checkout wins, even when the default isn't one (and the cwd isn't either)
    monkeypatch.chdir(venv)
    monkeypatch.setenv("FF9_REPO", str(repo))
    assert jobs.resolve_dev_repo(venv).resolve() == repo.resolve()
    # 2) a bogus $FF9_REPO is ignored -> default not a repo + cwd not a repo -> default unchanged
    monkeypatch.setenv("FF9_REPO", str(tmp_path / "nope"))
    assert jobs.resolve_dev_repo(venv).resolve() == venv.resolve()
    # 3) the default already a checkout -> kept (the normal apps/ff9_workspace.pyw launch)
    monkeypatch.delenv("FF9_REPO", raising=False)
    assert jobs.resolve_dev_repo(repo).resolve() == repo.resolve()
    # 4) cwd-walk: installed default, but launched from inside a checkout subdir
    sub = repo / "a" / "b"; sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    assert jobs.resolve_dev_repo(venv).resolve() == repo.resolve()


# --------------------------------------------------------------------------- deployed-here ledger scan
def _dp(tmp_path, *fields):
    """Write a DictionaryPatch with the given (id, name) FieldScene rows (+ noise the scanner must skip)."""
    lines = ["3DModel 40 foo bar baz", "# a comment", "MessageFile 4003"]
    for fid, name in fields:
        lines.append(f"FieldScene {fid} 11 0 {name} extra")
    p = tmp_path / "DictionaryPatch.txt"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def test_scan_pairs_each_registered_id_with_its_per_id_revert(tmp_path):
    dp = _dp(tmp_path, ("4003", "TESTROOM"), ("4100", "MYFORK"))
    scroll = tmp_path / "scroll_out"; scroll.mkdir()
    (scroll / "revert_deploy_4100.py").write_text("# undo 4100\n", encoding="utf-8")   # only 4100 has a script
    rows = jobs.scan_deployed_reverts(dp, scroll)
    by_id = {r["id"]: r for r in rows if r["kind"] == "field"}
    assert by_id["4003"]["script"] is None, "an id with no revert script must be read-only informational"
    assert by_id["4100"]["script"] and by_id["4100"]["script"].endswith("revert_deploy_4100.py")
    assert by_id["4100"]["mtime"] is not None and by_id["4003"]["mtime"] is None
    assert by_id["4003"]["name"] == "TESTROOM"           # the FieldScene name is carried for the label


def test_scan_field_rows_keep_dictionarypatch_order(tmp_path):
    dp = _dp(tmp_path, ("4100", "B"), ("4003", "A"))     # order as written, NOT sorted
    rows = jobs.scan_deployed_reverts(dp, tmp_path / "none")
    assert [r["id"] for r in rows if r["kind"] == "field"] == ["4100", "4003"]


def test_scan_appends_folderwide_reverts_newest_first(tmp_path):
    import os, time
    dp = _dp(tmp_path, ("4003", "TESTROOM"))
    scroll = tmp_path / "scroll_out"; scroll.mkdir()
    camp = scroll / "revert_campaign.py"; camp.write_text("x", encoding="utf-8")
    ng = scroll / "revert_newgame_from_stock.py"; ng.write_text("x", encoding="utf-8")
    # make the New-Game revert strictly newer than the campaign one, deterministically
    t = time.time()
    os.utime(camp, (t - 100, t - 100))
    os.utime(ng, (t, t))
    rows = jobs.scan_deployed_reverts(dp, scroll)
    field = [r for r in rows if r["kind"] == "field"]
    extra = [r for r in rows if r["kind"] != "field"]
    assert [r["kind"] for r in rows][:len(field)] == ["field"], "field rows come first"
    assert [r["name"] for r in extra] == ["New Game entry", "campaign deploy"], "folder-wide reverts newest first"
    assert all(r["script"] for r in extra) and all(r["id"] is None for r in extra)


def test_scan_is_inert_without_a_dictpatch_or_scroll_dir(tmp_path):
    # no DictionaryPatch (no install found) -> no field rows; no scroll dir -> every script reads absent.
    assert jobs.scan_deployed_reverts(None, None) == []
    assert jobs.scan_deployed_reverts(tmp_path / "absent.txt", tmp_path / "absent") == []
    # a DictPatch but no scroll dir: field rows present, all read-only (no undo script reachable)
    dp = _dp(tmp_path, ("4003", "TESTROOM"))
    rows = jobs.scan_deployed_reverts(dp, None)
    assert rows and all(r["script"] is None for r in rows)


def test_scan_surfaces_the_install_revert(tmp_path):
    # Install-to-game is now reversible (whole-folder snapshot), so its revert_install.py appears as a
    # folder-wide 'Install to game' ledger row alongside the campaign / New-Game reverts.
    dp = _dp(tmp_path, ("4100", "MYFORK"))
    scroll = tmp_path / "scroll_out"; scroll.mkdir()
    (scroll / "revert_install.py").write_text("x", encoding="utf-8")
    rows = jobs.scan_deployed_reverts(dp, scroll)
    inst = [r for r in rows if r["kind"] == "install"]
    assert len(inst) == 1 and inst[0]["name"] == "Install to game" and inst[0]["script"]
    assert inst[0]["id"] is None


# --------------------------------------------------------------------------- Install-to-game backup law
def test_snapshot_mod_folder_copies_and_writes_a_restoring_revert(tmp_path):
    """The §2 backup law on Install-to-game: the WHOLE folder is snapshotted before the write, and the
    emitted revert restores it byte-for-byte (a mutated DictionaryPatch + a deleted asset both come back)."""
    import subprocess
    mod = tmp_path / "FF9CustomMap"
    (mod / "StreamingAssets").mkdir(parents=True)
    (mod / "DictionaryPatch.txt").write_text("FieldScene 4100 11 0 X extra\n", encoding="utf-8")
    (mod / "StreamingAssets" / "a.bytes").write_bytes(b"\x01\x02")
    backups, reverts = tmp_path / "backups", tmp_path / "reverts"
    rp = jobs.snapshot_mod_folder(mod, backups, reverts)
    assert rp is not None and rp.name == "revert_install.py" and rp.is_file()
    snaps = list(backups.glob("*/FF9CustomMap/DictionaryPatch.txt"))     # copied under backups/<stamp>/<name>/
    assert snaps and snaps[0].read_text(encoding="utf-8").startswith("FieldScene 4100")
    # mutate + delete, then run the revert -> the pre-install truth is restored exactly
    (mod / "DictionaryPatch.txt").write_text("CLOBBERED\n", encoding="utf-8")
    (mod / "StreamingAssets" / "a.bytes").unlink()
    subprocess.run([sys.executable, str(rp)], check=True)
    assert (mod / "DictionaryPatch.txt").read_text(encoding="utf-8").startswith("FieldScene 4100")
    assert (mod / "StreamingAssets" / "a.bytes").read_bytes() == b"\x01\x02"


def test_snapshot_of_an_absent_folder_reverts_by_removing_it(tmp_path):
    """A fresh install (no prior folder): the snapshot records the absence, and the revert removes the
    folder the install created -- restoring the true pre-install state, not an empty stub."""
    import subprocess
    mod = tmp_path / "FF9CustomMap"                                    # does NOT exist yet
    rp = jobs.snapshot_mod_folder(mod, tmp_path / "backups", tmp_path / "reverts")
    assert rp is not None
    (mod / "sub").mkdir(parents=True)                                  # the install then creates it
    (mod / "sub" / "f.bytes").write_bytes(b"x")
    subprocess.run([sys.executable, str(rp)], check=True)
    assert not mod.exists()


def test_revert_install_argv(tmp_path):
    assert jobs.revert_install_argv(tmp_path) is None                  # nothing snapshotted -> nothing to undo
    scroll = tmp_path / "tools" / "scroll_out"; scroll.mkdir(parents=True)
    (scroll / "revert_install.py").write_text("print('x')\n", encoding="utf-8")
    a = jobs.revert_install_argv(tmp_path)
    assert a and a[0] == sys.executable and a[-1].replace("\\", "/").endswith("scroll_out/revert_install.py")


def test_revert_install_pkg_argv_reads_cache(tmp_path, monkeypatch):
    from ff9mapkit import provision
    monkeypatch.setattr(provision, "deploy_reverts_dir", lambda: tmp_path / "rv")
    assert jobs.revert_install_pkg_argv() is None                      # empty cache
    (tmp_path / "rv").mkdir()
    (tmp_path / "rv" / "revert_install.py").write_text("x", encoding="utf-8")
    r = jobs.revert_install_pkg_argv()
    assert r and r[-1].endswith("revert_install.py")


# --------------------------------------------------------------------------- New-Game casualty reader
def test_current_newgame_target_reads_the_deployed_override(tmp_path, monkeypatch):
    # a deployed field-70 override under the mod folder -> current_newgame_target reads its Field() warp
    from ff9mapkit import newgame
    p = tmp_path / newgame.OVERRIDE_REL.format(lang="us")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\x00\x01\x02")                                     # bytes present...
    monkeypatch.setattr(newgame, "newgame_target", lambda data: 6000)  # ...parsed by the real reader
    assert jobs.current_newgame_target(tmp_path) == 6000


def test_current_newgame_target_none_when_absent_or_unparseable(tmp_path):
    from ff9mapkit import newgame
    assert jobs.current_newgame_target(tmp_path) is None               # no override deployed -> None
    p = tmp_path / newgame.OVERRIDE_REL.format(lang="us")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"not a real eb file")                              # unparseable -> graceful None (no raise)
    assert jobs.current_newgame_target(tmp_path) is None


def test_current_newgame_target_round_trips_a_real_override(tmp_path):
    """No stub: build a GENUINE field-70 override from stock, remap its warp -> 6000, and read it back
    through the real ``newgame_target`` bytecode parser. The monkeypatched sibling above proves only the
    plumbing (it hard-codes the parse); this is the CI guard against a field-70 format / entry-tag drift,
    exercising the exact reader ``wire_from_stock`` self-verifies with. Game-gated: this module needs no
    install, so it SKIPS cleanly without one (a fresh public clone), and only runs where p0data is present."""
    from ff9mapkit import config, extract, newgame
    try:
        game = config.find_game_path()
    except Exception:                                                  # noqa: BLE001
        game = None
    if not game or not (game / "StreamingAssets" / "p0data2.bin").is_file():
        pytest.skip("needs the FF9 install + UnityPy (real field-70 .eb round-trip)")
    data = extract.EventBundle(game=str(game)).eb_for_id(newgame.NEWGAME_FIELD)
    assert data, "stock field 70 .eb must extract from p0data"
    stock_dest = newgame.newgame_target(data)                          # the real parser finds the warp
    assert stock_dest is not None
    out = newgame.remap_fields(data, {stock_dest: 6000})
    assert out != data, "the remap must change the warp target"
    p = tmp_path / newgame.OVERRIDE_REL.format(lang="us")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(out)                                                 # a real override on disk...
    assert jobs.current_newgame_target(tmp_path) == 6000              # ...read back with NO stub
