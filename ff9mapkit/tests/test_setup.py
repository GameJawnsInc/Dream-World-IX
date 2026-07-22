"""`ff9mapkit setup` building blocks: config persistence, the installed-package data dir, and the
opt-in Memoria engine-bundle install (detection + backed-up DLL swap that NEVER touches Memoria.ini)."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from ff9mapkit import config, fsutil, memoria, provision


# ---- config.save_game_path -------------------------------------------------------------------------
def test_save_game_path_roundtrip(tmp_path, monkeypatch):
    cfg = tmp_path / ".ff9mapkit.toml"
    monkeypatch.setattr(config, "USER_CONFIG", cfg)
    monkeypatch.delenv("FF9_GAME_PATH", raising=False)
    game = tmp_path / "FF9"
    game.mkdir()
    assert config.save_game_path(game) == cfg
    assert config._read_user_config()["game_path"]          # the file parses as valid TOML
    assert config.find_game_path() == game.resolve()        # and resolves with no env / explicit arg


def test_save_game_path_preserves_other_keys(tmp_path, monkeypatch):
    cfg = tmp_path / ".ff9mapkit.toml"
    cfg.write_text('# my config\nother_key = "keep me"\ngame_path = "C:/old/path"\n', encoding="utf-8")
    monkeypatch.setattr(config, "USER_CONFIG", cfg)
    game = tmp_path / "FF9"
    game.mkdir()
    config.save_game_path(game)
    text = cfg.read_text(encoding="utf-8")
    assert "# my config" in text                            # comment preserved
    assert 'other_key = "keep me"' in text                  # sibling key preserved
    assert "C:/old/path" not in text                        # old game_path line replaced (not duplicated)
    data = config._read_user_config()
    assert data["other_key"] == "keep me"
    assert Path(data["game_path"]) == game.resolve()


def test_save_game_path_stores_forward_slashes(tmp_path, monkeypatch):
    cfg = tmp_path / ".ff9mapkit.toml"
    monkeypatch.setattr(config, "USER_CONFIG", cfg)
    game = tmp_path / "FF9"
    game.mkdir()
    config.save_game_path(game)
    # No backslash in the stored config -> the TOML basic string can't trip an escape on Windows.
    assert "\\" not in cfg.read_text(encoding="utf-8")


# ---- provision data dir: repo checkout vs installed wheel ------------------------------------------
def test_data_dir_env_override_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("FF9MAPKIT_DATA", str(tmp_path / "d"))
    assert provision.data_dir() == tmp_path / "d"
    assert provision.cache_dir() == tmp_path / "d"


def test_data_dir_repo_checkout_uses_package_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("FF9MAPKIT_DATA", raising=False)
    pkg = tmp_path / "ff9mapkit" / "ff9mapkit"
    pkg.mkdir(parents=True)
    (tmp_path / "ff9mapkit" / "pyproject.toml").write_text("[build-system]\n", encoding="utf-8")
    monkeypatch.setattr(provision, "_PKG_DATA", pkg / "data")
    assert provision._is_installed_pkg() is False
    assert provision.data_dir() == pkg / "data"


def test_data_dir_installed_uses_user_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("FF9MAPKIT_DATA", raising=False)
    sp = tmp_path / "site-packages" / "ff9mapkit"             # no pyproject.toml above -> "installed"
    sp.mkdir(parents=True)
    monkeypatch.setattr(provision, "_PKG_DATA", sp / "data")
    assert provision._is_installed_pkg() is True
    dd = provision.data_dir()
    assert dd == provision._user_dir("data")
    assert dd.parts[-2:] == ("ff9mapkit", "data")            # under a per-user ff9mapkit home


# ---- memoria detection + opt-in engine install ----------------------------------------------------
def _make_game(tmp_path, *, memoria_installed=True, dll_bytes=b"OLD"):
    game = tmp_path / "FF9"
    for arch in ("x64", "x86"):
        mgd = game / arch / "FF9_Data" / "Managed"
        mgd.mkdir(parents=True)
        if memoria_installed:
            for dll in memoria.ENGINE_DLLS:
                (mgd / dll).write_bytes(dll_bytes)
    if memoria_installed:
        (game / "Memoria.ini").write_text('[Mod]\nFolderNames = ""\n', encoding="utf-8")
    return game


def _make_bundle(tmp_path, *, complete=True, dll_bytes=b"NEW-ENGINE"):
    zp = tmp_path / "dwix-custom-memoria-test.zip"
    with zipfile.ZipFile(zp, "w") as z:
        for dll in (memoria.ENGINE_DLLS if complete else memoria.ENGINE_DLLS[:-1]):
            z.writestr(f"bundle/{dll}", dll_bytes)            # nested in a folder, like the real zip
    return zp


def test_memoria_status_detected(tmp_path):
    st = memoria.memoria_status(_make_game(tmp_path))
    assert st["installed"] is True and st["ini"] is True and len(st["assembly"]) == 2


def test_memoria_status_absent(tmp_path):
    assert memoria.memoria_status(_make_game(tmp_path, memoria_installed=False))["installed"] is False


def test_install_engine_bundle_swaps_and_backs_up(tmp_path):
    game = _make_game(tmp_path, dll_bytes=b"OLD")
    ini_before = (game / "Memoria.ini").read_bytes()
    zp = _make_bundle(tmp_path, dll_bytes=b"NEW-ENGINE")
    rep = memoria.install_engine_bundle(game, zp, stamp="20260629-120000")

    for mgd in memoria.managed_dirs(game):                   # all 3 DLLs in BOTH arches got the bundle bytes
        for dll in memoria.ENGINE_DLLS:
            assert (mgd / dll).read_bytes() == b"NEW-ENGINE"
    backup = game / "dwix-engine-backups" / "20260629-120000"
    assert (backup / "x64" / "Assembly-CSharp.dll").read_bytes() == b"OLD"
    assert (backup / "x86" / "UnityEngine.UI.dll").read_bytes() == b"OLD"
    assert len(rep["installed"]) == 6 and len(rep["backed_up"]) == 6
    assert (game / "Memoria.ini").read_bytes() == ini_before  # NEVER touches Memoria.ini


def test_install_engine_bundle_write_is_atomic(tmp_path, monkeypatch):
    # a write interrupted mid-copy must never leave a truncated DLL under the live name -- the swap stages
    # to a sibling .tmp and os.replace()s it in, so a failure there leaves the ORIGINAL bytes in place.
    game = _make_game(tmp_path, dll_bytes=b"OLD")
    zp = _make_bundle(tmp_path, dll_bytes=b"NEW-ENGINE")
    real_replace = fsutil.os.replace

    def _boom(src, dst):
        if Path(dst).name == "Assembly-CSharp.dll":
            raise OSError("simulated interrupted write")
        return real_replace(src, dst)
    monkeypatch.setattr(fsutil.os, "replace", _boom)

    with pytest.raises(OSError):
        memoria.install_engine_bundle(game, zp, stamp="20260629-130000")

    for mgd in memoria.managed_dirs(game):
        assert (mgd / "Assembly-CSharp.dll").read_bytes() == b"OLD"    # never truncated/half-written
        assert not (mgd / "Assembly-CSharp.dll.tmp").exists()          # the failed .tmp is cleaned up


def test_install_engine_refuses_without_memoria(tmp_path):
    game = _make_game(tmp_path, memoria_installed=False)
    with pytest.raises(RuntimeError):
        memoria.install_engine_bundle(game, _make_bundle(tmp_path), stamp="x")


def test_bundle_missing_dll_raises(tmp_path):
    with pytest.raises(ValueError):
        memoria.bundle_dll_members(_make_bundle(tmp_path, complete=False))


# ---- engine version detection (advisory: graceful None when unreadable / off-Windows) --------------
def test_read_assembly_version_none_on_missing(tmp_path):
    assert memoria.read_assembly_version(tmp_path / "nope.dll") is None


def test_read_assembly_version_none_on_non_pe(tmp_path):
    f = tmp_path / "fake.dll"
    f.write_bytes(b"not a real PE file with no VS_VERSIONINFO resource")
    assert memoria.read_assembly_version(f) is None           # no version resource -> None, never raises


def test_bundle_assembly_version_none_on_fake_bundle(tmp_path):
    # The fake bundle's DLLs carry no version resource -> None (and None off Windows). Never raises.
    assert memoria.bundle_assembly_version(_make_bundle(tmp_path)) is None


def test_engine_compat_already_applied(tmp_path, monkeypatch):
    # installed FileVersion == bundle's -> the live engine IS our patched build -> skip-able.
    monkeypatch.setattr(memoria, "read_assembly_version", lambda p: "1.1.9670.29463")
    monkeypatch.setattr(memoria, "bundle_assembly_version", lambda z: "1.1.9670.29463")
    cmp = memoria.engine_compat(_make_game(tmp_path), _make_bundle(tmp_path))
    assert cmp["already_applied"] is True
    assert cmp["installed"] == cmp["bundle"] == "1.1.9670.29463"


def test_engine_compat_differs_means_install(tmp_path, monkeypatch):
    # A stock/other Memoria (or one reverted by a re-patch) reads a different version -> (re)apply.
    monkeypatch.setattr(memoria, "read_assembly_version", lambda p: "1.1.1000.1")
    monkeypatch.setattr(memoria, "bundle_assembly_version", lambda z: "1.1.9670.29463")
    assert memoria.engine_compat(_make_game(tmp_path), _make_bundle(tmp_path))["already_applied"] is False


def test_engine_compat_unreadable_not_applied(tmp_path, monkeypatch):
    # Off Windows / unreadable -> both None -> never claims "already applied" (so the caller installs).
    monkeypatch.setattr(memoria, "read_assembly_version", lambda p: None)
    monkeypatch.setattr(memoria, "bundle_assembly_version", lambda z: None)
    assert memoria.engine_compat(_make_game(tmp_path), _make_bundle(tmp_path))["already_applied"] is False


# ---- `setup --install-engine` CLI behavior the installer depends on (graceful + version-aware) ------
def _setup_args(game, zp, **over):
    import argparse
    base = dict(game=str(game), install_engine=str(zp), no_extract=True, force=False, no_fixtures=True)
    base.update(over)
    return argparse.Namespace(**base)


def test_setup_install_engine_graceful_when_memoria_absent(tmp_path, monkeypatch, capsys):
    """The installer passes --install-engine unconditionally; with no Memoria yet it must NOT fail or
    swap anything -- just print how to apply it later and return 0 (base setup still succeeded)."""
    from ff9mapkit import cli
    game = _make_game(tmp_path, memoria_installed=False)       # an FF9 dir, but no Memoria installed
    zp = _make_bundle(tmp_path)
    monkeypatch.setattr(cli, "find_game_path", lambda g: game)
    monkeypatch.setattr(config, "save_game_path", lambda g: tmp_path / ".ff9mapkit.toml")
    rc = cli._cmd_setup(_setup_args(game, zp))
    out = capsys.readouterr().out
    assert rc == 0
    assert "SKIPPED" in out and "Memoria isn't installed" in out
    assert not (game / "dwix-engine-backups").exists()        # nothing was swapped/backed up


def test_setup_install_engine_skips_when_already_applied(tmp_path, monkeypatch, capsys):
    """When the live engine already IS our build (version match), skip -- no needless re-swap/backup."""
    from ff9mapkit import cli
    game = _make_game(tmp_path, memoria_installed=True)
    zp = _make_bundle(tmp_path)
    monkeypatch.setattr(cli, "find_game_path", lambda g: game)
    monkeypatch.setattr(config, "save_game_path", lambda g: tmp_path / ".ff9mapkit.toml")
    monkeypatch.setattr(memoria, "engine_compat",
                        lambda g, z: {"installed": "1.1.9670.29463", "bundle": "1.1.9670.29463",
                                      "already_applied": True})
    rc = cli._cmd_setup(_setup_args(game, zp))
    out = capsys.readouterr().out
    assert rc == 0 and "already installed" in out
    assert not (game / "dwix-engine-backups").exists()        # skipped -> no swap, no backup


# ---- engine_report: the plain-language `doctor` explainer's data (all advisory, never load-bearing) -
def test_assembly_build_date_decodes_days_since_2000():
    # .NET AssemblyVersion("1.1.*") fills BUILD with days since 2000-01-01 -> the DLL's compile date.
    from datetime import date
    assert memoria.assembly_build_date("1.1.9325.29463") == date(2025, 7, 13)   # the BASE_COMMIT date
    assert memoria.assembly_build_date("1.1.0.0") == date(2000, 1, 1)
    assert memoria.assembly_build_date(f"1.1.{memoria.BASE_COMMIT_DATE.toordinal() - date(2000, 1, 1).toordinal()}.1") \
        == memoria.BASE_COMMIT_DATE


def test_assembly_build_date_none_on_garbage():
    for bad in (None, "", "1.1.9324", "1.1.9324.29463.5", "not.a.version.x", "1.1.x.0"):
        assert memoria.assembly_build_date(bad) is None
    assert memoria.assembly_build_date("1.1.99999999.0") is None      # out of date's range, never raises


def test_dwix_backup_dirs_empty_and_populated(tmp_path):
    game = _make_game(tmp_path)
    assert memoria.dwix_backup_dirs(game) == []
    for stamp in ("20260702-090000", "20260629-120000"):
        (game / "dwix-engine-backups" / stamp / "x64").mkdir(parents=True)
    (game / "dwix-engine-backups" / "loose.txt").write_text("", encoding="utf-8")   # files aren't stamps
    got = [p.name for p in memoria.dwix_backup_dirs(game)]
    assert got == ["20260629-120000", "20260702-090000"]              # sorted, oldest stamp first


def test_engine_report_memoria_absent(tmp_path):
    rep = memoria.engine_report(_make_game(tmp_path, memoria_installed=False))
    assert rep["memoria_installed"] is False
    assert rep["dwix_bundle_applied"] is False and rep["assembly_version"] is None


def test_engine_report_stock_fresh(tmp_path, monkeypatch):
    from datetime import date
    monkeypatch.setattr(memoria, "read_assembly_version", lambda p: "1.1.9325.29463")   # 2025-07-13
    rep = memoria.engine_report(_make_game(tmp_path))
    assert rep["memoria_installed"] is True and rep["dwix_bundle_applied"] is False
    assert rep["assembly_build_date"] == date(2025, 7, 13) == rep["base_commit_date"]


def test_engine_report_stock_stale(tmp_path, monkeypatch):
    monkeypatch.setattr(memoria, "read_assembly_version", lambda p: "1.1.11000.1")      # 2030-02-16
    rep = memoria.engine_report(_make_game(tmp_path))
    drift = (rep["assembly_build_date"] - rep["base_commit_date"]).days
    assert drift > memoria.STALE_WARNING_DAYS and rep["dwix_bundle_applied"] is False


def test_engine_report_detects_our_bundle_by_backup_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(memoria, "read_assembly_version", lambda p: "1.1.9670.29463")
    game = _make_game(tmp_path)
    (game / "dwix-engine-backups" / "20260629-120000" / "x64").mkdir(parents=True)
    rep = memoria.engine_report(game)
    assert rep["dwix_bundle_applied"] is True and rep["dwix_backup_count"] == 1


# ---- `doctor`'s engine block: the words the user actually reads -------------------------------------
def _doctor(game, monkeypatch, capsys, mod_root=None):
    import argparse
    from ff9mapkit import cli
    monkeypatch.setattr(cli, "find_game_path", lambda g: Path(game))
    monkeypatch.setattr(cli, "find_mod_root", lambda g, m: Path(mod_root or (Path(game) / "FF9CustomMap")))
    rc = cli._cmd_doctor(argparse.Namespace(game=str(game), mod_folder=None))
    return rc, capsys.readouterr().out


def test_doctor_reports_memoria_absent(tmp_path, monkeypatch, capsys):
    rc, out = _doctor(_make_game(tmp_path, memoria_installed=False), monkeypatch, capsys)
    assert rc == 0                                        # advisory only -- never gates the exit code
    assert "Memoria NOT detected" in out
    assert "world-*" not in out                           # no patch advice when there's no engine at all


def test_doctor_reports_patched_engine(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(memoria, "read_assembly_version", lambda p: "1.1.9670.29463")
    game = _make_game(tmp_path)
    (game / "dwix-engine-backups" / "20260629-120000" / "x64").mkdir(parents=True)
    rc, out = _doctor(game, monkeypatch, capsys)
    assert rc == 0 and "Dream World IX patches" in out
    assert "Forked real fields" in out and "should work" in out
    assert "no Dream World IX patches detected" not in out   # nothing to install; don't nag


def test_doctor_reports_stock_engine_with_reassurance(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(memoria, "read_assembly_version", lambda p: "1.1.9325.29463")   # on-base date
    rc, out = _doctor(_make_game(tmp_path), monkeypatch, capsys)
    assert rc == 0 and "no Dream World IX patches detected" in out
    assert "novel from-scratch fields" in out              # the reassurance: most pillars already work
    assert "FORKED real fields" in out and "world-*" in out
    assert "docs/ENGINE.md" in out and "--install-engine" in out
    assert "option 3" not in out                          # on-base -> no drift note


def test_doctor_stock_engine_adds_drift_note_when_stale(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(memoria, "read_assembly_version", lambda p: "1.1.11000.1")      # years newer
    rc, out = _doctor(_make_game(tmp_path), monkeypatch, capsys)
    assert rc == 0 and "no Dream World IX patches detected" in out
    assert "big gap" in out and "option 3" in out and "memoria-patches/" in out


# ---- game-install detection (Steam + GOG; rejects MS Store) ----------------------------------------
def _make_ff9_root(tmp_path, *, launcher=True, streaming=True, managed=True):
    root = tmp_path / "FINAL FANTASY IX"
    root.mkdir(parents=True, exist_ok=True)
    if launcher:
        (root / "FF9_Launcher.exe").write_bytes(b"")
    if streaming:
        (root / "StreamingAssets").mkdir(exist_ok=True)
    if managed:
        (root / "x64" / "FF9_Data" / "Managed").mkdir(parents=True, exist_ok=True)
    return root


def test_is_ff9_root_accepts_real_layout(tmp_path):
    assert config._is_ff9_root(_make_ff9_root(tmp_path)) is True


def test_is_ff9_root_rejects_incomplete(tmp_path):
    assert config._is_ff9_root(_make_ff9_root(tmp_path / "a", launcher=False)) is False   # MS Store-like
    assert config._is_ff9_root(_make_ff9_root(tmp_path / "b", streaming=False)) is False
    assert config._is_ff9_root(_make_ff9_root(tmp_path / "c", managed=False)) is False
    assert config._is_ff9_root(tmp_path / "nope") is False


def test_parse_vdf_new_schema():
    text = (
        '"libraryfolders"\n{\n'
        '    "0"\n    {\n'
        '        "path"    "C:\\\\Program Files (x86)\\\\Steam"\n'
        '        "apps" { "377840" "12345678" }\n'      # appid->buildid must NOT be read as a library
        '    }\n'
        '    "1"\n    {\n        "path"    "E:\\\\SteamLibrary"\n    }\n}\n'
    )
    assert config._parse_vdf_library_paths(text) == [r"C:\Program Files (x86)\Steam", r"E:\SteamLibrary"]


def test_parse_vdf_old_schema():
    text = '"LibraryFolders"\n{\n    "1"   "E:\\\\Games\\\\Steam"\n    "2"   "F:\\\\Steam"\n}\n'
    assert config._parse_vdf_library_paths(text) == [r"E:\Games\Steam", r"F:\Steam"]


# ---- installed vs repo: the GUI deploy-tools gate (PySide6-free; the Qt shell is covered by --smoke,
#      which test_workspace_smoke.py runs -- this line was a wish until then) ----
def test_has_deploy_tools(tmp_path):
    from ff9mapkit.editor import jobs
    assert jobs.has_deploy_tools(tmp_path) is False              # installed-like: no tools/ in the wheel
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "deploy_field.py").write_text("", encoding="utf-8")
    assert jobs.has_deploy_tools(tmp_path) is True               # repo checkout
