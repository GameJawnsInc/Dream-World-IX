"""The #5 editor READ surface (save_items) -- decode a save's items / equipment / gil from the Memoria extra
file (the load-authoritative store). These tests build synthetic SimpleJSON-binary trees (no install needed)
to pin the decoders + the per-slot inspect/render, plus an install-gated check against the real save.
"""
from __future__ import annotations

import glob
import os

import pytest

from ff9mapkit import sjbinary as SJ
from ff9mapkit import save_items as SI
from ff9mapkit import items as I


# ---- synthetic-tree builders ------------------------------------------------------------------
def _int(v):
    return SJ.SJData(SJ.INT, v)


def _item(iid, count):
    c = SJ.SJClass(); c.add("id", _int(iid)); c.add("count", _int(count)); return c


def _player(name, slot_no, equip):
    p = SJ.SJClass()
    p.add("name", SJ.SJData(SJ.VALUE, name))
    info = SJ.SJClass(); info.add("slot_no", _int(slot_no)); p.add("info", info)
    p.add("equip", SJ.SJArray([_int(x) for x in equip]))
    return p


def _common(gil=12345, items=((236, 7), (28, 1)), players=(("Zidane", 0, [1, 112, 88, 149, 255]),)):
    c = SJ.SJClass()
    c.add("players", SJ.SJArray([_player(*p) for p in players]))
    c.add("gil", _int(gil))
    c.add("items", SJ.SJArray([_item(i, n) for i, n in items]))
    return c


def _extra_file(tmp_path, name="SavedData_ww_Memoria_0_2.dat", common=None):
    root = SJ.SJClass()
    root.add("95000_Setting", SJ.SJClass())                # siblings the editor must round-trip
    root.add("40000_Common", common if common is not None else _common())
    p = tmp_path / name
    p.write_bytes(SJ.dumps(root))
    return p


# ---- decoders ---------------------------------------------------------------------------------
def test_read_gil():
    assert SI.read_gil(_common(gil=987654)) == 987654
    assert SI.read_gil(SJ.SJClass()) is None               # absent


def test_read_inventory_names_and_skips_noitem():
    common = _common(items=((236, 7), (255, 0), (28, 1)))   # 255 = NoItem -> skipped
    inv = SI.read_inventory(common)
    assert (236, I.name_of(236), 7) in inv
    assert (28, I.name_of(28), 1) in inv
    assert all(iid != SI.NO_ITEM for iid, _, _ in inv)
    assert len(inv) == 2


def test_read_equipment_slots_and_empty():
    common = _common(players=(("Zidane", 0, [1, 112, 88, 149, 255]),
                              ("Vivi", 1, [70, 255, 255, 255, 255])))
    eq = SI.read_equipment(common)
    assert eq[0]["name"] == "Zidane" and eq[0]["slot_no"] == 0
    assert eq[0]["equip"]["weapon"] == (1, I.name_of(1))
    assert eq[0]["equip"]["accessory"] is None             # 255 -> empty
    assert eq[1]["equip"]["head"] is None and eq[1]["equip"]["weapon"] == (70, I.name_of(70))
    # all 5 slot keys present
    assert set(eq[0]["equip"]) == set(SI.EQUIP_SLOTS)


def test_report_from_common():
    rep = SI.report_from_common(_common())
    assert rep.gil == 12345 and len(rep.inventory) == 2 and rep.equipment[0]["name"] == "Zidane"


# ---- file-level inspect -----------------------------------------------------------------------
def test_inspect_extra_file_directly(tmp_path):
    path = _extra_file(tmp_path, common=_common(gil=42))
    reports = SI.inspect(str(path))
    assert len(reports) == 1
    label, rep = reports[0]
    assert "extra" in label.lower() and rep.gil == 42


def test_load_extra_common_rejects_non_extra(tmp_path):
    bad = tmp_path / "not_a_tree.dat"
    bad.write_bytes(b"\x00\x01\x02\x03 random garbage not a simplejson tree")
    common, root, trailing = SI.load_extra_common(str(bad))
    assert common is None and root is None and trailing == b""


def test_inspect_missing_file_raises(tmp_path):
    with pytest.raises(Exception):
        SI.inspect(str(tmp_path / "does_not_exist.dat"))


# ---- rendering --------------------------------------------------------------------------------
def test_render_report_smoke():
    out = SI.render_report(SI.report_from_common(_common(gil=1000)))
    assert "Gil: 1,000" in out and "Zidane" in out and "Inventory" in out and "Equipment" in out


def test_render_report_none():
    assert "no Memoria extra file" in SI.render_report(None)


# ---- install-gated: the real save ------------------------------------------------------------
def _real_main_save():
    from ff9mapkit import save as S
    d = S.default_save_dir()
    if not d:
        return None
    p = os.path.join(str(d), "SavedData_ww.dat")
    return p if os.path.isfile(p) and glob.glob(os.path.join(str(d), "SavedData_ww_Memoria_*.dat")) else None


@pytest.mark.skipif(not _real_main_save(), reason="no real FF9 save on this machine")
def test_real_save_decodes():
    reports = SI.inspect(_real_main_save())
    assert reports
    # at least one slot has a decoded extra report with the expected shape
    decoded = [rep for _, rep in reports if rep is not None]
    assert decoded
    r = decoded[0]
    assert r.gil is not None and isinstance(r.gil, int)
    assert isinstance(r.inventory, list) and isinstance(r.equipment, list)
    if r.equipment:                                        # 12 players, each with 5 named slots
        assert set(r.equipment[0]["equip"]) == set(SI.EQUIP_SLOTS)
