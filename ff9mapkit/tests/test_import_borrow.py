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


# ---- a plain `import` records its donor as `[field] source_field`, so a STANDALONE BG-borrow gets the same
# ForkDonorPatch `<forkId> <donorId>` row a campaign member of that donor gets from plan.members -- without it the
# engine's EffectiveFieldId gates (walkmesh hotfixes, off-mesh exemptions, the menu location) never fire for it.
# Offline: the install-reading halves are stubbed; the toml text, its parse and the build are real.
def _stub_borrow_import(monkeypatch, donor_id):
    from ff9mapkit import dialogue, extract

    def _extract_field(field, out_dir, **_k):
        Path(out_dir).mkdir(parents=True, exist_ok=True)         # the real one writes camera.bgx + walkmesh.bgi here
        return {"field": "fbg_n21_grgr_map420_gr_cen_0", "area": 21, "mapid": "GRGR_MAP420_GR_CEN_0",
                "camera": {"pitch_deg": 30.0, "fov_deg": 40.0, "range": [384, 400]},
                "walkmesh_bounds": {"x": [-500, 500], "z": [-500, 500]}, "player_start": [404, 127],
                "scrolling": False}

    def _resolve_field_id(field):
        if donor_id is None:
            raise ValueError(f"no field id for {field!r}")
        return donor_id

    monkeypatch.setattr(extract, "resolve_field", lambda field, game: ("fbg_n21_grgr_map420_gr_cen_0", None))
    monkeypatch.setattr(extract, "extract_field", _extract_field)
    monkeypatch.setattr(extract, "compose_background", lambda *a, **k: False)
    monkeypatch.setattr(extract, "_content_for_import", lambda *a, **k: ("", None, {}))
    monkeypatch.setattr(extract, "extract_mapconfig", lambda *a, **k: None)
    monkeypatch.setattr(dialogue, "_resolve_field_id", _resolve_field_id)


def test_plain_import_records_its_donor(tmp_path, monkeypatch):
    import tomllib
    from ff9mapkit import build, deploystack, extract
    _stub_borrow_import(monkeypatch, 950)
    _, p = extract.write_field_project("950", tmp_path / "f", field_id=30999)
    raw = tomllib.loads(p.read_text(encoding="utf-8"))
    assert raw["field"]["borrow_bg"] == "GRGR_MAP420_GR_CEN_0"    # still a BG-borrow on the donor's own scene
    assert raw["field"]["source_field"] == 950 and build.donor_field_id(raw) == 950
    assert deploystack.donor_block_for(raw) is not None          # the deploy-time text guard sees the fork too


def test_a_plain_import_builds_the_fork_donor_row_a_campaign_member_gets(tmp_path, monkeypatch):
    from ff9mapkit import extract
    _stub_borrow_import(monkeypatch, 950)
    _, p = extract.write_field_project("950", tmp_path / "f", field_id=30999)
    (p.parent / "camera.bgx").write_bytes((FIX / "grgr.bgx").read_bytes())   # what extract_field writes; the
    (p.parent / "walkmesh.bgi").write_bytes((FIX / "multifloor.bgi.bytes").read_bytes())   # mesh is lint-only
    out = tmp_path / "mod"
    build_mod([FieldProject.load(p)], out)
    rows = [ln for ln in ModLayout(out).fork_donor_patch.read_text(encoding="utf-8").splitlines()
            if not ln.startswith("#")]
    assert rows == ["30999 950"]                     # the row build_campaign writes for a member (new_id real_id)


def test_plain_import_records_no_donor_in_place_or_when_unresolved(tmp_path, monkeypatch):
    import tomllib
    from ff9mapkit import build, extract
    _stub_borrow_import(monkeypatch, 950)            # forked IN PLACE: no self-mapping (EffectiveFieldId is the id)
    _, p = extract.write_field_project("950", tmp_path / "ip", field_id=950)
    assert "source_field" not in tomllib.loads(p.read_text(encoding="utf-8"))["field"]
    _stub_borrow_import(monkeypatch, None)           # the donor id did not resolve: record nothing, never a guess
    _, p = extract.write_field_project("950", tmp_path / "nr", field_id=30999)
    raw = tomllib.loads(p.read_text(encoding="utf-8"))
    assert "source_field" not in raw["field"] and build.donor_field_id(raw) is None


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


# ---- shared-FBG ambiguity warning: ~142 of the 818 real fields SHARE a background folder with a sibling
# (the same room at a different story beat). A NAME import silently resolves to the folder-keyed table's
# single winner (2026-07-12: importing the Lindblum inn folder by name forked 2103's event script when 553
# was intended). Resolution stays UNCHANGED (back-compat); the kit must WARN with the sibling ids + EVT
# names and recommend re-running with the numeric id. Pure table lookups -- offline, no install needed.

SHARED = "fbg_n11_ldbm_map160_lb_in1_0"           # Lindblum inn: fields 553 / 1303 / 2103


@pytest.fixture()
def _fresh_shared_warn():
    extract._SHARED_FBG_WARNED.clear()            # the once-per-process dedup must not leak across tests
    yield
    extract._SHARED_FBG_WARNED.clear()


def test_fbg_siblings_enumerates_a_shared_folder():
    sibs = extract.fbg_siblings(SHARED)
    assert [fid for fid, _ in sibs] == [553, 1303, 2103]
    assert dict(sibs)[553] == "EVT_LIND1_TN_LB_IN1_0"
    assert dict(sibs)[2103] == "EVT_LIND3_TN_LB_IN1_0"
    assert len(extract.fbg_siblings(extract.ID_TO_FBG[100])) == 1     # a unique folder is NOT ambiguous


def test_warn_shared_fbg_prints_siblings_once(_fresh_shared_warn, capsys):
    assert extract.warn_shared_fbg(SHARED) is True
    err = capsys.readouterr().err
    for tok in ("553", "1303", "2103", "EVT_LIND1_TN_LB_IN1_0", "EVT_LIND3_TN_LB_IN1_0"):
        assert tok in err
    assert "ff9mapkit import 553" in err          # the fix: re-run by numeric id (the digit branch is exact)
    assert "2103" in [ln for ln in err.splitlines() if "resolves HERE" in ln][0]  # marks the silent winner
    assert extract.warn_shared_fbg(SHARED) is False     # dedup: one warning per folder per process
    assert capsys.readouterr().err == ""


def test_warn_shared_fbg_silent_on_a_unique_folder(_fresh_shared_warn, capsys):
    assert extract.warn_shared_fbg(extract.ID_TO_FBG[100]) is False
    assert capsys.readouterr().err == ""


def test_event_name_for_name_pick_warns_but_resolves_unchanged(_fresh_shared_warn, monkeypatch, capsys):
    monkeypatch.setattr(extract, "build_field_index", lambda game=None, **k: {SHARED: "a.bin"})
    assert extract.event_name_for("lb_in1_0") == "EVT_LIND3_TN_LB_IN1_0"   # back-compat: same winner as before
    err = capsys.readouterr().err
    assert "553" in err and "2103" in err and "SHARED" in err


def test_event_name_for_digit_pick_is_exact_and_silent(_fresh_shared_warn, capsys):
    assert extract.event_name_for("553") == "EVT_LIND1_TN_LB_IN1_0"    # the id pick names ITS beat exactly
    assert capsys.readouterr().err == ""


def test_cmd_import_warns_on_a_shared_name_token(_fresh_shared_warn, monkeypatch, capsys):
    # the CLI must surface the ambiguity BEFORE the heavy extraction; the mocked extractor stops the run there
    import argparse
    from ff9mapkit import cli

    class _Stop(Exception):
        pass

    def _stop(*a, **k):
        raise _Stop()

    monkeypatch.setattr(extract, "build_field_index", lambda game=None, **k: {SHARED: "a.bin"})
    monkeypatch.setattr(extract, "write_field_project", _stop)
    args = argparse.Namespace(field="lb_in1_0", out=".", name=None, id=4003, game=None, atlas=False,
                              native=False, editable=False, graft_player_funcs=False, carry_text=False,
                              save_moogle=False, dialogue=False, verbatim=False)
    with pytest.raises(_Stop):
        cli._cmd_import(args)
    err = capsys.readouterr().err
    assert "SHARED" in err and "553" in err and "2103" in err and "ff9mapkit import 553" in err
