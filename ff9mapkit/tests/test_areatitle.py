"""Area-title overlay control: hide a forked/BG-borrowed field's "Ice Cavern"/"Mognet Central" card.
The title is a scene-overlay range (areatitle manifest); content.areatitle prepends ShowTile(i,0) to
Main_Init so a synthesized field that borrows an area-title room doesn't statically claim to be that place.
"""
from __future__ import annotations

import pytest

from ff9mapkit import data
from ff9mapkit.content import areatitle as AT
from ff9mapkit.eb import EbScript, opcodes

SHOWTILE = 0x5B


def _tag0_ops(ebb):
    eb = EbScript.from_bytes(ebb)
    f0 = eb.entry(0).func_by_tag(0)
    return [(i.op, list(i.args or [])) for i in eb.instrs(f0)]


def test_hide_prepends_showtile_off_per_overlay():
    src = data.blank_field_bytes("us")
    out = AT.hide(src, 46, 47)
    assert EbScript.from_bytes(out).to_bytes() == out                 # still a valid .eb (fpos fixed up)
    assert len(out) == len(src) + 2 * len(opcodes.encode(SHOWTILE, 0, 0))   # 2 overlays x ShowTile
    ops = _tag0_ops(out)
    # the FIRST ops of Main_Init are exactly ShowTile(46,0), ShowTile(47,0) -- title hidden from frame 1
    assert ops[0] == (SHOWTILE, [46, 0])
    assert ops[1] == (SHOWTILE, [47, 0])


def test_hide_single_overlay_range():
    src = data.blank_field_bytes("us")
    out = AT.hide(src, 7, 7)                                           # start == end (e.g. a Chocobo row)
    assert _tag0_ops(out)[0] == (SHOWTILE, [7, 0])
    assert len(out) == len(src) + len(opcodes.encode(SHOWTILE, 0, 0))


def test_no_range_is_a_noop():
    src = data.blank_field_bytes("us")
    assert AT.hide(src, None, None) == src                            # field has no area title -> unchanged


def test_build_wires_hide_area_title_from_field_block(tmp_path):
    from ff9mapkit import build
    base = ('[field]\nid=4700\nname="F"\nborrow_bg="MGNT_MAP810_MN_MOG_0"\narea=56\ntext_block=8\n'
            '{flag}[camera]\npitch=30\ndistance=900\nfov=40\n[player]\nspawn=[0,0]\n')
    p = tmp_path / "f.field.toml"
    # hide_area_title + explicit overlays -> Main_Init starts with ShowTile(46,0)/(47,0) (no resources.assets read)
    p.write_text(base.format(flag="hide_area_title=true\narea_title_overlays=[46,47]\n"), encoding="utf-8")
    ops = _tag0_ops(build.build_script(build.FieldProject.load(p), "us", {}))
    assert ops[0] == (SHOWTILE, [46, 0]) and ops[1] == (SHOWTILE, [47, 0])
    # absent -> unchanged (no ShowTile prepend)
    p.write_text(base.format(flag=""), encoding="utf-8")
    ops2 = _tag0_ops(build.build_script(build.FieldProject.load(p), "us", {}))
    assert ops2[0] != (SHOWTILE, [46, 0])


def test_manifest_reader_overlay_ranges():
    # needs the user's install (resources.assets via UnityPy) -- skip if unreachable.
    from ff9mapkit import areatitle
    if not areatitle._manifest(None):
        pytest.skip("area-title manifest not reachable (no install / UnityPy)")
    assert areatitle.title_range("FBG_N56_MGNT_MAP810_MN_MOG_0") == (46, 47)   # Mognet Central
    assert areatitle.title_range("FBG_N05_ICCV_MAP085_IC_ENT_0") == (2, 3)     # Ice Cavern Entrance
    assert areatitle.title_range("FBG_N99_NOT_A_REAL_FIELD_0") is None         # no area title
