"""Overworld marker RENAME (world text block 68) -- resolve, splice txid-0, per-language deploy.

The marker label is GetTableText(0)[locId+1] of world block 68 (txid-0, newline-split after its [TBLE=] tag,
DialogBoxSymbols.cs:35-38). These pin the splice (target changes, entry count stable, other txids intact),
the selector resolution (name -> all slots, locid, validation), and that deploy lands 68.mes per language.
"""
from __future__ import annotations

import pytest

from ff9mapkit import config, dialogue
from ff9mapkit.world import navimap

# a minimal block-68-shaped .mes: txid-0 = [TBLE=...]<names newline-joined>, plus an unrelated txid-1
SYNTH = ("[STRT=0,0][TBLE=1,2,3,]Dummy\nAlexandria\nSouth Gate\nSouth Gate\nLindblum[ENDN]"
         "[STRT=1,0]unrelated moogle text[ENDN]")


def _table0(body: str):
    t0 = dialogue.parse_mes(body)[0].text
    rest = t0[t0.find("]") + 1:] if t0.startswith("[TBLE=") else t0
    return rest.split("\n")


def test_resolve_renames_by_name_and_locid():
    # "South Gate" here owns locIds 1 and 2 in the SYNTH body -- but resolve_renames uses the REAL registry,
    # so use registry names / ids for resolution semantics:
    r = navimap.resolve_renames([{"name": "Lindblum", "to": "Falcon City"}, {"locid": 3, "to": "Frost Cave"}])
    assert r == {24: "Falcon City", 3: "Frost Cave"}
    # a name that owns many slots renames all of them
    assert set(navimap.resolve_renames([{"name": "South Gate", "to": "Gate"}])) == {6, 7, 8, 9, 10}


def test_resolve_renames_validation():
    for bad in ([{"name": "Lindblum"}],                       # missing `to`
                [{"locid": 3, "to": ""}],                     # blank `to`
                [{"locid": 3, "to": "two\nlines"}],           # newline
                [{"to": "x"}],                                # no selector
                [{"name": "Nowhere", "to": "x"}],             # unknown name
                [{"locid": 155, "to": "x"}],                  # past the case-155 cap
                [{"locid": 91, "to": "x"}]):                  # the vehicle HUD trio
        with pytest.raises(ValueError):
            navimap.resolve_renames(bad)


def test_apply_marker_renames_splices_only_the_target():
    before = _table0(SYNTH)                                    # [Dummy, Alexandria, South Gate, South Gate, Lindblum]
    out = navimap.apply_marker_renames(SYNTH, {0: "Alexandria Prime", 3: "New Lindblum"})  # locId 0->idx1, 3->idx4
    after = _table0(out)
    assert after[1] == "Alexandria Prime" and after[4] == "New Lindblum"
    assert len(after) == len(before)                          # no stray newline / dropped entry
    assert [i for i in range(len(before)) if before[i] != after[i]] == [1, 4]
    # the unrelated txid-1 is byte-identical
    assert dialogue.parse_mes(out)[1].text == "unrelated moogle text"
    # empty renames -> unchanged
    assert navimap.apply_marker_renames(SYNTH, {}) == SYNTH


def test_deploy_writes_68_mes_per_language(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    monkeypatch.setattr(dialogue, "extract_field_mes", lambda *a, **k: SYNTH)
    written = navimap.deploy_marker_renames(
        [{"locid": 3, "to": "Lindblum City"}], mod_folder="FF9CustomMap", game=tmp_path, langs=["us", "fr"])
    assert {p.parent.parent.name for p in written} == {"us", "fr"}
    for p in written:
        assert p.name == "68.mes" and p.is_file()
        assert "Lindblum City" in p.read_text(encoding="utf-8")
        assert p == (tmp_path / "FF9CustomMap" / "FF9_Data" / "embeddedasset" / "text"
                     / p.parent.parent.name / "field" / "68.mes")


def test_deploy_merges_with_the_already_deployed_override(tmp_path, monkeypatch):
    """A SECOND named entrance must not wipe the first's name.

    deploy_marker_renames used to rebuild every language's 68.mes from the BASE game text and
    apply only the renames it was given -- so each new named entrance silently erased every name
    a previous one had registered (the R3 Lamplight deploy erased R1's "Lantern Quay" split[53];
    caught only by a byte check of the deployed file). The fix: when an override is already
    deployed, it IS the base -- splice on top of it."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    monkeypatch.setattr(dialogue, "extract_field_mes", lambda *a, **k: SYNTH)
    first = navimap.deploy_marker_renames(
        [{"locid": 3, "to": "Lantern Quay"}], mod_folder="FF9CustomMap", game=tmp_path, langs=["us"])
    # the second deploy must MERGE with the file the first one wrote, not re-extract the base
    monkeypatch.setattr(dialogue, "extract_field_mes",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError(
                            "re-extracted the base over a deployed override -- the wipe bug")))
    second = navimap.deploy_marker_renames(
        [{"locid": 1, "to": "Lamplight"}], mod_folder="FF9CustomMap", game=tmp_path, langs=["us"])
    assert first == second
    names = _table0(second[0].read_text(encoding="utf-8"))
    assert names[4] == "Lantern Quay"        # locId 3 -> split[4]: the FIRST name survives
    assert names[2] == "Lamplight"           # locId 1 -> split[2]: the second lands beside it
    # idempotence: re-running the same rename over the merged file changes nothing
    third = navimap.deploy_marker_renames(
        [{"locid": 1, "to": "Lamplight"}], mod_folder="FF9CustomMap", game=tmp_path, langs=["us"])
    assert _table0(third[0].read_text(encoding="utf-8")) == names
