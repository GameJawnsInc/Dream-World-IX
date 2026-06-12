"""Tier-3 import: BG-borrow build mode.

An imported field ships ONLY a custom script + a borrow DictionaryPatch line (areaID + the REAL
field's mapid), so the engine renders that field's art/walkmesh/camera while running our script.
No custom scene is written. (The offline extraction half needs UnityPy + the game, validated live;
this test covers the build wiring with no game data.)"""
from pathlib import Path

from ff9mapkit.build import FieldProject, build_mod, validate
from ff9mapkit.config import LANGS, ModLayout

FIX = Path(__file__).parent / "fixtures"


def _borrow_project(tmp_path):
    d = tmp_path / "proj"
    d.mkdir()
    (d / "camera.bgx").write_bytes((FIX / "grgr.bgx").read_bytes())   # the extracted camera
    (d / "GRGR_FORK.field.toml").write_text(
        '[field]\n'
        'id = 4003\n'
        'name = "GRGR_FORK"\n'
        'area = 21\n'
        'borrow_bg = "GRGR_MAP420_GR_CEN_0"\n'
        'text_block = 1073\n\n'
        '[camera]\n'
        'borrow = "camera.bgx"\n\n'
        '[player]\n'
        'spawn = [404, 127]\n',
        encoding="utf-8",
    )
    return FieldProject.load(d / "GRGR_FORK.field.toml")


def test_borrow_validates_and_emits_borrow_dictionary(tmp_path):
    proj = _borrow_project(tmp_path)
    assert validate(proj) == []
    out = tmp_path / "mod"
    info = build_mod([proj], out)
    # areaID + the REAL field's mapid, then our custom script name + textid
    assert info["dictionary"] == ["FieldScene 4003 21 GRGR_MAP420_GR_CEN_0 GRGR_FORK 1073"]


def test_import_extractors_accept_the_cli_graft_flags():
    # `_cmd_import` passes graft_player_funcs / carry_text / graft_savepoint to ALL three import extractors
    # (native / editable / BG-borrow). A missing param on any one is an uncaught TypeError on that path --
    # the default `import` (BG-borrow) once crashed because write_field_project lacked graft_savepoint. Keep
    # the three signatures in sync with what the cli hands them.
    import inspect
    from ff9mapkit import extract
    for fn in ("write_field_project", "write_native_project", "write_editable_project"):
        params = inspect.signature(getattr(extract, fn)).parameters
        for flag in ("graft_player_funcs", "carry_text", "graft_savepoint"):
            assert flag in params, f"{fn} is missing {flag!r} -> the cli passing it TypeErrors that import path"


def test_plain_import_auto_routes_area_lt_10_to_native(monkeypatch):
    # #4 (FORK_FIDELITY.md): a plain `import` (no --native/--editable) of an area<10 field would BG-borrow ->
    # black-screen (the engine builds 'FBG_N<area>' and reads exactly 2 chars). _cmd_import must auto-route it
    # to the native path (ships its own art at a remapped area>=10). Mocks keep this offline; the extractor
    # raises a sentinel right after recording which path was taken, so no full meta is needed.
    import argparse
    import pytest
    from ff9mapkit import cli, extract

    class _Stop(Exception):
        pass

    def _run(area):
        calls = []

        def _native(*a, **k):
            calls.append("native")
            raise _Stop()

        def _borrow(*a, **k):
            calls.append("borrow")
            raise _Stop()

        monkeypatch.setattr(extract, "resolve_field", lambda field, game: (f"FBG_N{area:02d}_X", None))
        monkeypatch.setattr(extract, "parse_fbg_folder", lambda folder: (area, "X"))
        monkeypatch.setattr(extract, "write_native_project", _native)
        monkeypatch.setattr(extract, "write_field_project", _borrow)
        args = argparse.Namespace(field="x", out=".", name=None, id=4003, game=None, atlas=False,
                                  native=False, editable=False, graft_player_funcs=False, carry_text=False,
                                  save_moogle=False, dialogue=False, verbatim=False)
        with pytest.raises(_Stop):
            cli._cmd_import(args)
        return calls

    assert _run(1) == ["native"]      # area 1 (Alexandria) -> auto-native, not a black-screen borrow
    assert _run(0) == ["native"]      # area 0 (Cargo Ship) -> auto-native
    assert _run(21) == ["borrow"]     # area >= 10 -> BG-borrow unchanged


def test_borrow_ships_script_but_no_custom_scene(tmp_path):
    proj = _borrow_project(tmp_path)
    out = tmp_path / "mod"
    build_mod([proj], out)
    L = ModLayout(out)
    # our script is shipped in every language...
    for lang in LANGS:
        assert L.eb_path(lang, "EVT_GRGR_FORK.eb.bytes").is_file()
    # ...but NO custom background scene (the engine renders the borrowed real field's FBG)
    fm = L.fieldmap_dir("FBG_N21_GRGR_FORK")
    assert not (fm / "FBG_N21_GRGR_FORK.bgx").exists()
    assert not (fm / "FBG_N21_GRGR_FORK.bgi.bytes").exists()


# ---- resolve_field digit-first: `import <id>` must mean the FIELD ID (parity with fork-report), not a
# map<NNN> folder substring. Offline via a monkeypatched index (field ids and folder map-numbers are
# unrelated schemes -- id 100 = Alexandria, but "100" substring-matches the map100 Dali folder).
import pytest                                                              # noqa: E402
from ff9mapkit import extract                                             # noqa: E402


def test_resolve_field_digit_is_a_field_id_not_a_map_substring(monkeypatch):
    real = extract.ID_TO_FBG[100]                 # fbg_n01_alxt_map016_... (id 100, no "100" in the name)
    decoy = "fbg_n06_vgdl_map100_dl_fwm_0"        # the OLD trap: contains "100" (map100) -> the Dali field
    assert "100" not in real and "100" in decoy   # guard the fixture's premise
    monkeypatch.setattr(extract, "build_field_index", lambda game=None, **k: {real: "a.bin", decoy: "b.bin"})
    assert extract.resolve_field("100")[0] == real          # digit -> the field-id folder, NOT the substring
    assert extract.resolve_field("vgdl_map100")[0] == decoy  # a non-digit substring still matches the folder


def test_resolve_field_digit_not_a_field_id_falls_through(monkeypatch):
    monkeypatch.setattr(extract, "build_field_index", lambda game=None, **k: {"fbg_n01_x_map001_y_0": "b.bin"})
    with pytest.raises(FileNotFoundError):
        extract.resolve_field("99999")            # not a real field id + no substring match -> clean error


def test_resolve_field_real_id_with_no_live_bundle_raises(monkeypatch):
    monkeypatch.setattr(extract, "build_field_index", lambda game=None, **k: {})   # empty index
    with pytest.raises(FileNotFoundError):
        extract.resolve_field("100")              # id 100 is real but its folder isn't in the (empty) index
