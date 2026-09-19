"""Offline tests for the deployed-model inventory + revert (pure filesystem, no install).

scan_mod classifies the three override trees the engine probes (Models/, BattleMap/BattleModel/,
Animations/) + the DictionaryPatch 3DModel mint registrations; revert_entry deletes one entry and
strips a mint's line, path-guarded to the mod folder. Vivi (id 8) stands in for a real model,
7777 for a mint (no catalog row).
"""
from pathlib import Path

import pytest

from ff9mapkit import fsutil
from ff9mapkit.models import deployed

RES = ("StreamingAssets", "Assets", "Resources")


def _mk(mod: Path, *parts, name=None, data=b"x"):
    d = mod.joinpath(*RES, *[str(p) for p in parts])
    d.mkdir(parents=True, exist_ok=True)
    if name:
        (d / name).write_bytes(data)
    return d


def _fixture_mod(tmp_path) -> Path:
    mod = tmp_path / "mod"
    _mk(mod, "Models", 2, 8, name="8.fbx")                 # a real-model override (Vivi)
    _mk(mod, "Models", 2, 8, name="8_0.png")
    _mk(mod, "Models", 4, 10, name="10_0.png")             # a PNG-only reskin (BBA)
    _mk(mod, "Models", 2, 7777, name="7777.fbx")           # a mint (no catalog row)
    _mk(mod, "BattleMap", "BattleModel", 6, 516, name="516_0.png")   # a weapon reskin
    _mk(mod, "Animations", 8, name="148.anim")             # a clip override
    (mod / "DictionaryPatch.txt").write_text(
        "FieldScene 4003 21 XXX YYY 1073\n3DModel 7777 GEO_NPC_F9_XYZ\n3DModel 8888 GEO_NPC_F9_GONE\n",
        encoding="utf-8")
    return mod


def test_scan_classifies_every_kind(tmp_path):
    entries = deployed.scan_mod(_fixture_mod(tmp_path))
    by = {(e["kind"], e["geo_id"]): e for e in entries}
    assert set(by) == {("override", 8), ("reskin", 10), ("mint", 7777), ("reskin", 516),
                       ("anims", 8), ("mint-directive", 8888)}
    assert by[("override", 8)]["name"] == "GEO_MAIN_F0_VIV"
    assert by[("reskin", 516)]["weapon_tree"] is True
    assert by[("mint", 7777)]["registered"] is True
    assert by[("mint", 7777)]["name"] == "GEO_NPC_F9_XYZ"          # named by its directive
    assert by[("mint-directive", 8888)]["name"] == "GEO_NPC_F9_GONE"
    assert by[("anims", 8)]["files"] == ["148.anim"]


def test_scan_empty_mod_is_empty(tmp_path):
    assert deployed.scan_mod(tmp_path / "nothing") == []


def test_unregistered_mint_is_flagged(tmp_path):
    mod = tmp_path / "mod"
    _mk(mod, "Models", 2, 7000, name="7000.fbx")
    (e,) = deployed.scan_mod(mod)
    assert e["kind"] == "mint" and e["registered"] is False
    assert "won't register" in deployed.describe(e)


def test_revert_override_deletes_the_dir(tmp_path):
    mod = _fixture_mod(tmp_path)
    entry = next(e for e in deployed.scan_mod(mod) if e["kind"] == "override")
    r = deployed.revert_entry(mod, entry)
    assert r["removed"] and not r["directive_removed"]
    assert not mod.joinpath(*RES, "Models", "2", "8").exists()
    assert mod.joinpath(*RES, "Animations", "8").exists()          # the anims entry is separate


def test_revert_mint_strips_its_directive_only(tmp_path):
    mod = _fixture_mod(tmp_path)
    entry = next(e for e in deployed.scan_mod(mod) if e["kind"] == "mint")
    r = deployed.revert_entry(mod, entry)
    assert r["directive_removed"]
    text = (mod / "DictionaryPatch.txt").read_text(encoding="utf-8")
    assert "3DModel 7777" not in text
    assert "FieldScene 4003" in text                                # other lines untouched
    assert "3DModel 8888" in text


def test_revert_dangling_directive(tmp_path):
    mod = _fixture_mod(tmp_path)
    entry = next(e for e in deployed.scan_mod(mod) if e["kind"] == "mint-directive")
    r = deployed.revert_entry(mod, entry)
    assert r["directive_removed"] and not r["removed"]
    assert "3DModel 8888" not in (mod / "DictionaryPatch.txt").read_text(encoding="utf-8")


def test_strip_mint_directive_write_is_crash_safe(tmp_path, monkeypatch):
    """A crash mid-rewrite must never truncate the shared DictionaryPatch.txt -- every OTHER field's/mint's
    line already registered in that mod folder has to survive, not just the one entry being stripped."""
    mod = _fixture_mod(tmp_path)
    original = (mod / "DictionaryPatch.txt").read_text(encoding="utf-8")

    def _boom(*a, **k):
        raise OSError("simulated crash between the tmp write and its install")

    monkeypatch.setattr(fsutil.os, "replace", _boom)
    with pytest.raises(OSError):
        deployed._strip_mint_directive(mod, 7777)
    assert (mod / "DictionaryPatch.txt").read_text(encoding="utf-8") == original   # untouched, not truncated
    assert not (mod / "DictionaryPatch.txt.tmp").exists()                          # the tmp is cleaned up


def test_revert_refuses_an_outside_path(tmp_path):
    mod = _fixture_mod(tmp_path)
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    bad = {"kind": "override", "geo_id": 8, "name": "x", "dir": str(outside), "files": [],
           "nbytes": 0, "weapon_tree": False, "registered": False}
    with pytest.raises(ValueError, match="not inside the mod folder"):
        deployed.revert_entry(mod, bad)
    assert outside.exists()
