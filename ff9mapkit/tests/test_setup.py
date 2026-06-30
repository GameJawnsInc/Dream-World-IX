"""`ff9mapkit setup` building blocks: config persistence, the installed-package data dir, and the
opt-in Memoria engine-bundle install (detection + backed-up DLL swap that NEVER touches Memoria.ini)."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from ff9mapkit import config, memoria, provision


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


# ---- installed vs repo: the GUI deploy-tools gate (PySide6-free; the Qt shell is covered by --smoke) ----
def test_has_deploy_tools(tmp_path):
    from ff9mapkit.editor import jobs
    assert jobs.has_deploy_tools(tmp_path) is False              # installed-like: no tools/ in the wheel
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "deploy_field.py").write_text("", encoding="utf-8")
    assert jobs.has_deploy_tools(tmp_path) is True               # repo checkout
