"""Verbatim-.eb fork (docs/FORK_FIDELITY.md, the entry-0 carry): ship a real field's WHOLE event script
instead of re-synthesizing, remapping only the Field() destinations."""
from __future__ import annotations

import pytest

from ff9mapkit import data
from ff9mapkit.content import gateway as _gw
from ff9mapkit.content import verbatim as _vb
from ff9mapkit.eb import EbScript


def _fields(eb_bytes):
    s = EbScript.from_bytes(eb_bytes)
    return [i.imm(0) for e in s.entries if not e.empty for f in e.funcs
            for i in s.instrs(f) if i.op == 0x2B]


def test_remap_fields_patches_destinations():
    # a gateway region warps Field(100); remap_fields retargets it (the verbatim-fork destination remap)
    eb = _gw.inject_gateway(data.blank_field_bytes("us"), 100,
                            zone=_gw.quad_zone([(0, 0), (10, 0), (10, 10), (0, 10)]))
    assert 100 in _fields(eb)
    out = _vb.remap_fields(eb, {100: 4100})
    assert 4100 in _fields(out) and 100 not in _fields(out)
    assert EbScript.from_bytes(out).to_bytes() == out          # still a valid, round-tripping eb
    # ids not in the map stay as live seams; an empty map is a byte-identical no-op
    assert _vb.remap_fields(eb, {999: 4100}) == eb
    assert _vb.remap_fields(eb, {}) == eb


def _game_ready():
    try:
        import UnityPy  # noqa: F401,PLC0415
        from ff9mapkit import config  # noqa: PLC0415
        return config.find_game_path(None) is not None
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_import_verbatim_ships_the_whole_donor_eb(tmp_path):
    # import --verbatim emits a [verbatim_eb] block + sidecar; the build ships the donor's WHOLE .eb
    # (Field-remapped) instead of synthesizing -- so the field runs its real logic (in-game proven on Dali Inn).
    from ff9mapkit import build, extract
    meta, toml = extract.write_native_project("fbg_n06_vgdl_map101_dl_inn_0", tmp_path, name="DV", verbatim=True)
    assert meta["imported_content"]["verbatim_eb"]
    assert "[verbatim_eb]" in toml.read_text()
    project = build.FieldProject.load(toml)
    donor = extract.extract_event_script("fbg_n06_vgdl_map101_dl_inn_0")
    assert _vb.verbatim_eb(project) == donor                    # no retarget -> the whole donor .eb, verbatim
    # P2 text: the donor's WHOLE .mes ships too, and the verbatim .eb's index-txids resolve into it (no remap)
    from ff9mapkit import dialogue
    assert meta["imported_content"]["text"]
    us = _vb.verbatim_mes(project, "us")
    assert us == dialogue.extract_field_mes("fbg_n06_vgdl_map101_dl_inn_0", "us")
    shown = {c.txid for c in dialogue.scan_dialogue(EbScript.from_bytes(donor)) if c.txid is not None}
    assert shown and shown <= set(dialogue.parse_mes(us))       # every line the .eb shows resolves in the text
    # with a retarget, that destination is patched in the shipped .eb (the rest stay live seams)
    exits = meta["imported_content"]["field_exits"]
    assert exits                                                # Dali Inn has Field() exits
    project.raw["verbatim_eb"]["retarget"] = {exits[0]: 4100}
    shipped = _vb.verbatim_eb(project)
    assert 4100 in _fields(shipped) and exits[0] not in _fields(shipped)
