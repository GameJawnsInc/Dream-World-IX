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
