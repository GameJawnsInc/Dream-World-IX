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


# ---- write surface: set_gil (step 3 -- the first real-save write, extra-only) ----------------
def test_set_gil_dry_run_writes_nothing(tmp_path):
    path = _extra_file(tmp_path, common=_common(gil=500))
    before = path.read_bytes()
    rep = SI.set_gil(str(path), 9_999_999)                 # dry_run defaults True
    assert rep.wrote is False and rep.old_gil == 500 and rep.new_gil == 9_999_999
    assert rep.bytes_changed <= 4 and rep.backup_path is None
    assert path.read_bytes() == before                     # nothing written


def _baks(tmp_path, path):
    return glob.glob(str(tmp_path / (path.name + ".bak.*")))


def test_set_gil_apply_is_surgical(tmp_path):
    """An applied gil write changes ONLY the gil leaf -- every other byte (siblings, items, equip) is identical
    and the file length is unchanged (Int32 leaf)."""
    path = _extra_file(tmp_path, common=_common(gil=500))
    before = path.read_bytes()
    rep = SI.set_gil(str(path), 123456, dry_run=False)
    assert rep.wrote is True and rep.old_gil == 500 and rep.new_gil == 123456
    after = path.read_bytes()
    assert len(after) == len(before)                       # length-stable
    diff = [i for i in range(len(before)) if before[i] != after[i]]
    assert 1 <= len(diff) <= 4 and diff[-1] - diff[0] < 4  # contiguous, within the 4-byte gil value
    # the new file re-reads as the new gil, and decodes everything else unchanged
    reread = SI.inspect(str(path))[0][1]
    assert reread.gil == 123456
    assert reread.inventory == SI.report_from_common(_common(gil=500)).inventory   # items untouched
    # a timestamped backup holds the original bytes, and no leftover .tmp
    baks = _baks(tmp_path, path)
    assert len(baks) == 1 and open(baks[0], "rb").read() == before
    assert rep.backup_path == baks[0] and not (tmp_path / (path.name + ".tmp")).exists()


def test_set_gil_zero_boundary(tmp_path):
    """gil=0 is a valid lower-bound write (the accept path, not just the reject path)."""
    path = _extra_file(tmp_path, common=_common(gil=500))
    before = path.read_bytes()
    rep = SI.set_gil(str(path), 0, dry_run=False)
    assert rep.wrote is True and rep.new_gil == 0
    after = path.read_bytes()
    assert len(after) == len(before) and SI.inspect(str(path))[0][1].gil == 0


def test_set_gil_no_backup(tmp_path):
    path = _extra_file(tmp_path, common=_common(gil=500))
    rep = SI.set_gil(str(path), 1, dry_run=False, backup=False)
    assert rep.backup_path is None and not _baks(tmp_path, path)
    assert SI.inspect(str(path))[0][1].gil == 1


def test_set_gil_noop_apply_writes_nothing(tmp_path):
    """A no-op apply (gil already == requested) writes NO file and NO backup, and reports wrote=False to match
    render_gil_write's 'nothing to change'."""
    path = _extra_file(tmp_path, common=_common(gil=777))
    before = path.read_bytes()
    rep = SI.set_gil(str(path), 777, dry_run=False)        # apply, but it's a no-op
    assert rep.old_gil == rep.new_gil == 777 and rep.wrote is False and rep.backup_path is None
    assert rep.bytes_changed == 0 and path.read_bytes() == before
    assert not _baks(tmp_path, path)                        # no spurious backup
    assert "already" in SI.render_gil_write(rep)


def test_set_gil_rejects_out_of_range(tmp_path):
    path = _extra_file(tmp_path, common=_common(gil=500))
    with pytest.raises(ValueError):
        SI.set_gil(str(path), -1)
    with pytest.raises(ValueError):
        SI.set_gil(str(path), SI.GIL_CAP + 1)
    with pytest.raises(TypeError):
        SI.set_gil(str(path), True)                        # bool is not a gil int
    assert path.read_bytes()                               # untouched (no write on rejection)


def test_set_gil_missing_gil_leaf(tmp_path):
    c = SJ.SJClass(); c.add("players", SJ.SJArray([]))     # no gil key
    path = _extra_file(tmp_path, common=c)
    with pytest.raises(ValueError, match="gil"):
        SI.set_gil(str(path), 100, dry_run=False)


def test_set_gil_rejects_non_int_gil_leaf(tmp_path):
    c = _common(gil=500)
    c.set("gil", SJ.SJData(SJ.VALUE, "500"))               # a string leaf, not Int32 -> refuse
    path = _extra_file(tmp_path, common=c)
    with pytest.raises(ValueError, match="Int32"):
        SI.set_gil(str(path), 100, dry_run=False)


def test_set_gil_trailing_bytes_preserved(tmp_path):
    """Trailing bytes after the root tree (the real autosave has ~20KB of them) round-trip, so set_gil still
    works and gate 1 passes -- the edit preserves the trailing blob verbatim."""
    path = _extra_file(tmp_path, common=_common(gil=500))
    with open(path, "ab") as fh:
        fh.write(b"\xde\xad\xbe\xef" * 8)                  # a trailing blob
    before = path.read_bytes()
    rep = SI.set_gil(str(path), 4242, dry_run=False)
    after = path.read_bytes()
    assert rep.new_gil == 4242 and after.endswith(b"\xde\xad\xbe\xef" * 8)   # trailing intact
    assert len(after) == len(before) and SI.inspect(str(path))[0][1].gil == 4242


def test_set_gil_aborts_on_non_reproducible_file(tmp_path, monkeypatch):
    """Gate 1: if the codec can't reproduce the on-disk bytes, set_gil refuses (never risk a corrupt write).
    Hard to construct a real such file (the codec is symmetric), so simulate it by making dumps diverge."""
    path = _extra_file(tmp_path, common=_common(gil=500))
    before = path.read_bytes()
    monkeypatch.setattr(SI._sj, "dumps", lambda *a, **k: b"not the original bytes")
    with pytest.raises(ValueError, match="byte-for-byte"):
        SI.set_gil(str(path), 100, dry_run=False)
    assert path.read_bytes() == before                     # untouched
    assert not _baks(tmp_path, path)                        # no backup written either
    assert not (tmp_path / (path.name + ".tmp")).exists()  # no leftover temp


def test_resolve_extra_direct_and_container(tmp_path):
    extra = _extra_file(tmp_path, name="SavedData_ww_Memoria_0_2.dat", common=_common())
    # passing the extra file directly returns it
    assert SI.resolve_extra(str(extra)) == str(extra)
    # a container path + slot/save resolves to the same extra name (block_index(0,2)=3 -> _Memoria_0_2.dat)
    container = tmp_path / "SavedData_ww.dat"
    container.write_bytes(b"not a real container")
    assert SI.resolve_extra(str(container), slot=0, save=2).endswith("SavedData_ww_Memoria_0_2.dat")
    with pytest.raises(ValueError):                        # container with no slot/save
        SI.resolve_extra(str(container))
    with pytest.raises(ValueError):                        # slot/save with no existing extra file
        SI.resolve_extra(str(container), slot=5, save=5)
    with pytest.raises(ValueError, match="not both"):      # autosave + slot/save is ambiguous -> reject
        SI.resolve_extra(str(container), slot=0, save=2, autosave=True)


def _ns(**kw):
    import argparse
    base = dict(save=None, gil=0, slot=None, save_no=None, autosave=False, apply=False, no_backup=False)
    base.update(kw)
    return argparse.Namespace(**base)


def test_cli_items_set_gil_glue(tmp_path, capsys):
    """The items-set-gil CLI glue: dry-run by default, --apply writes + makes a timestamped .bak, --no-backup
    skips it, a bad path returns exit 2. Pins the --save-no->args.save_no->resolve_extra(save=) mapping and the
    dry_run=not apply / backup=not no_backup inversions -- the highest-leverage guard for a real-save writer."""
    from ff9mapkit import cli
    path = _extra_file(tmp_path, common=_common(gil=500))

    rc = cli._cmd_items_set_gil(_ns(save=str(path), gil=4242))          # default = dry-run
    assert rc == 0 and "DRY RUN" in capsys.readouterr().out and SI.inspect(str(path))[0][1].gil == 500

    rc = cli._cmd_items_set_gil(_ns(save=str(path), gil=4242, apply=True))
    assert rc == 0 and "WROTE" in capsys.readouterr().out and SI.inspect(str(path))[0][1].gil == 4242
    assert len(_baks(tmp_path, path)) == 1                              # a backup was made

    rc = cli._cmd_items_set_gil(_ns(save=str(path), gil=1, apply=True, no_backup=True))
    assert rc == 0 and SI.inspect(str(path))[0][1].gil == 1
    assert len(_baks(tmp_path, path)) == 1                              # --no-backup added none

    rc = cli._cmd_items_set_gil(_ns(save=str(tmp_path / "nope.dat"), gil=5))
    assert rc == 2 and "could not set gil" in capsys.readouterr().out  # bad path -> exit 2


# ---- write surface: set_item (step 4a) -------------------------------------------------------
def _inv(path):
    return {i: c for i, _, c in SI.inspect(str(path))[0][1].inventory}


def test_set_item_change_count(tmp_path):
    path = _extra_file(tmp_path, common=_common(items=((236, 7), (28, 1))))
    before = path.read_bytes()
    rep = SI.set_item(str(path), "Potion", 99, dry_run=False)          # 236 = Potion
    assert rep.action == "changed" and rep.old_count == 7 and rep.new_count == 99 and rep.wrote
    assert _inv(path) == {236: 99, 28: 1}                              # only Potion changed
    # an applied write makes one timestamped backup of the pristine bytes, and leaves no .tmp
    baks = _baks(tmp_path, path)
    assert len(baks) == 1 and open(baks[0], "rb").read() == before
    assert rep.backup_path == baks[0] and not (tmp_path / (path.name + ".tmp")).exists()


def test_set_item_malformed_entry_clean_error(tmp_path):
    """A countless {id} stack yields a clean ValueError (not a raw AttributeError)."""
    c = _common(items=())
    bad = SJ.SJClass(); bad.add("id", _int(236))                       # no 'count' leaf
    c.get("items").items.append(bad)
    path = _extra_file(tmp_path, common=c)
    with pytest.raises(ValueError, match="malformed"):
        SI.set_item(str(path), "Potion", 5, dry_run=False)


def test_set_item_add_keeps_ascending_id_order(tmp_path):
    path = _extra_file(tmp_path, common=_common(items=((236, 7), (253, 1))))   # ids 236, 253
    rep = SI.set_item(str(path), 240, 5, dry_run=False)                # insert id 240 between them
    assert rep.action == "added" and rep.new_count == 5
    ids = [i for i, _, _ in SI.inspect(str(path))[0][1].inventory]
    assert ids == [236, 240, 253]                                     # inserted in ascending-id position


def test_set_item_remove(tmp_path):
    path = _extra_file(tmp_path, common=_common(items=((236, 7), (28, 1))))
    rep = SI.set_item(str(path), "Potion", 0, dry_run=False)
    assert rep.action == "removed" and rep.old_count == 7
    assert _inv(path) == {28: 1}                                      # Potion gone, the rest intact


def test_set_item_clamps_count_and_rejects_noitem(tmp_path):
    path = _extra_file(tmp_path, common=_common(items=((236, 7),)))
    rep = SI.set_item(str(path), "Potion", 9999, dry_run=False)        # clamp to 99
    assert rep.new_count == 99 and _inv(path)[236] == 99
    with pytest.raises(ValueError, match="NoItem"):
        SI.set_item(str(path), 255, 1)
    with pytest.raises(ValueError):                                    # negative count
        SI.set_item(str(path), "Potion", -1)


def test_set_item_dry_run_and_noop(tmp_path):
    path = _extra_file(tmp_path, common=_common(items=((236, 7),)))
    before = path.read_bytes()
    rep = SI.set_item(str(path), "Potion", 50)                        # dry-run default
    assert rep.wrote is False and path.read_bytes() == before and not _baks(tmp_path, path)
    rep = SI.set_item(str(path), "Potion", 7, dry_run=False)          # no-op: already 7
    assert rep.action == "unchanged" and rep.wrote is False and not _baks(tmp_path, path)


def test_set_item_scoped_other_fields_untouched(tmp_path):
    """An item edit leaves gil + equipment byte-identical (the scoped-change guard)."""
    path = _extra_file(tmp_path, common=_common(gil=4242, items=((236, 7),),
                                                players=(("Zidane", 0, [1, 112, 88, 149, 255]),)))
    SI.set_item(str(path), "Ether", 3, dry_run=False)
    rep = SI.inspect(str(path))[0][1]
    assert rep.gil == 4242 and rep.equipment[0]["equip"]["weapon"] == (1, I.name_of(1))


# ---- write surface: set_equip (step 4a) ------------------------------------------------------
def test_set_equip_by_charid_and_name(tmp_path):
    players = (("Zidane", 0, [1, 112, 88, 149, 255]), ("Vivi", 1, [70, 255, 255, 255, 255]))
    path = _extra_file(tmp_path, common=_common(players=players))
    rep = SI.set_equip(str(path), 0, "weapon", "MageMasher", dry_run=False)   # by CharacterId 0
    assert rep.wrote and rep.slot_no == 0 and rep.character == "Zidane"
    assert rep.old_name == I.name_of(1) and rep.new_id == I.resolve("MageMasher")
    eq = {p["name"]: p["equip"] for p in SI.inspect(str(path))[0][1].equipment}
    assert eq["Zidane"]["weapon"] == (I.resolve("MageMasher"), I.name_of(I.resolve("MageMasher")))
    # by name + an alias, into the accessory slot
    SI.set_equip(str(path), "vivi", "accessory", "Sapphire", dry_run=False)
    eq = {p["name"]: p["equip"] for p in SI.inspect(str(path))[0][1].equipment}
    assert eq["Vivi"]["accessory"][1] == "Sapphire"
    # a DIGIT-STRING CharacterId (as the CLI passes it) resolves like the int
    rep = SI.set_equip(str(path), "1", "head", "LeatherHat", dry_run=False)
    assert rep.slot_no == 1 and rep.character == "Vivi"


def test_set_equip_unequip(tmp_path):
    path = _extra_file(tmp_path, common=_common(players=(("Zidane", 0, [1, 112, 88, 149, 200]),)))
    rep = SI.set_equip(str(path), "Zidane", "accessory", "empty", dry_run=False)
    assert rep.new_id == SI.NO_ITEM and rep.old_id == 200
    assert SI.inspect(str(path))[0][1].equipment[0]["equip"]["accessory"] is None


def test_set_equip_slot_alias_and_bad_inputs(tmp_path):
    path = _extra_file(tmp_path, common=_common(players=(("Zidane", 0, [1, 112, 88, 149, 255]),)))
    SI.set_equip(str(path), 0, "body", "BronzeArmor", dry_run=False)   # "body" alias -> armor slot
    assert SI.inspect(str(path))[0][1].equipment[0]["equip"]["armor"][1] == "BronzeArmor"
    with pytest.raises(ValueError, match="slot"):
        SI.set_equip(str(path), 0, "ring", "Potion")                  # unknown slot
    with pytest.raises(ValueError):                                    # no such character
        SI.set_equip(str(path), 9, "weapon", "Dagger")


def test_set_equip_noop_and_scoped(tmp_path):
    path = _extra_file(tmp_path, common=_common(gil=4242, items=((236, 7),),
                                                players=(("Zidane", 0, [1, 112, 88, 149, 255]),)))
    rep = SI.set_equip(str(path), 0, "weapon", 1, dry_run=False)       # already Dagger(1) -> no-op
    assert rep.old_id == rep.new_id == 1 and rep.wrote is False and not _baks(tmp_path, path)
    SI.set_equip(str(path), 0, "head", "IronHelm", dry_run=False)      # a real change
    rep2 = SI.inspect(str(path))[0][1]
    assert rep2.gil == 4242 and rep2.inventory == [(236, I.name_of(236), 7)]   # gil + items untouched


def test_cli_set_item_and_equip_glue(tmp_path, capsys):
    from ff9mapkit import cli
    import argparse
    path = _extra_file(tmp_path, common=_common(items=((236, 7),),
                                                players=(("Zidane", 0, [1, 112, 88, 149, 255]),)))
    ns = argparse.Namespace(save=str(path), slot=None, save_no=None, autosave=False, apply=True, no_backup=True,
                            item="Ether", count=3)
    assert cli._cmd_items_set_item(ns) == 0 and _inv(path).get(I.resolve("Ether")) == 3
    ns = argparse.Namespace(save=str(path), slot=None, save_no=None, autosave=False, apply=True, no_backup=True,
                            character="Zidane", equip_slot="head", item="IronHelm")
    assert cli._cmd_items_set_equip(ns) == 0
    assert SI.inspect(str(path))[0][1].equipment[0]["equip"]["head"][1] == "IronHelm"


# ---- write surface: the abort safety-nets (scoped-diff + post-write confirm) ------------------
def test_set_item_aborts_on_out_of_scope_change(tmp_path, monkeypatch):
    """If a mutation touches anything outside the allowed prefix, _assert_scoped aborts and nothing is written."""
    path = _extra_file(tmp_path, common=_common(gil=500, items=((236, 7),)))
    before = path.read_bytes()
    monkeypatch.setattr(SI._sj, "diff_paths", lambda a, b: iter([("40000_Common", "gil")]))  # forge an out-of-scope diff
    with pytest.raises(AssertionError, match="unexpected path"):
        SI.set_item(str(path), "Potion", 99, dry_run=False)
    assert path.read_bytes() == before and not _baks(tmp_path, path)


def test_set_equip_post_write_confirm_failure(tmp_path, monkeypatch):
    """If the post-write re-read disagrees with the requested value, set_equip raises (the last safety net)."""
    path = _extra_file(tmp_path, common=_common(players=(("Zidane", 0, [1, 112, 88, 149, 255]),)))
    monkeypatch.setattr(SI, "load_extra_common", lambda p: (None, None, b""))   # break the confirm re-read
    with pytest.raises(AssertionError, match="post-write check failed"):
        SI.set_equip(str(path), 0, "weapon", "IronSword", dry_run=False)


# ---- rendering: the write-report formatters --------------------------------------------------
def test_render_item_write_branches():
    R = SI.ItemWriteReport
    assert "DRY RUN -- would add x5 of Potion" in SI.render_item_write(
        R("p", 236, "Potion", 0, 5, "added", False))
    assert "WROTE x7 -> x99 of Potion" in SI.render_item_write(
        R("p", 236, "Potion", 7, 99, "changed", True, "p.bak.X"))
    assert "remove (was x7)" in SI.render_item_write(R("p", 236, "Potion", 7, 0, "removed", True, "p.bak.X"))
    assert "already x7" in SI.render_item_write(R("p", 236, "Potion", 7, 7, "unchanged", False))
    assert "--no-backup" in SI.render_item_write(R("p", 236, "Potion", 0, 5, "added", True, None))


def test_render_equip_write_branches():
    R = SI.EquipWriteReport
    out = SI.render_equip_write(R("p", 0, "Zidane", "weapon", 1, "Dagger", 8, "MageMasher", True, "p.bak.X"))
    assert "Zidane (slot 0) weapon: Dagger -> MageMasher" in out and "Backup:" in out
    assert "-> (empty)" in SI.render_equip_write(R("p", 0, "Zidane", "accessory", 200, "GerminasBoots",
                                                   255, None, True, "p.bak.X"))
    assert "already" in SI.render_equip_write(R("p", 0, "Zidane", "weapon", 1, "Dagger", 1, "Dagger", False))


# ---- write surface: the encrypted MAIN block (step 4b) ---------------------------------------
def _has_crypto():
    try:
        import Crypto  # noqa: F401
        return True
    except ImportError:
        return False


def _enc_container(tmp_path, block=1, gil=500, items=((236, 7), (238, 2)), magic=b"SAVE", last_live=False):
    """A synthetic encrypted SavedData_ww.dat with one populated old-format block (SAVE magic + gil + items)."""
    from Crypto.Cipher import AES
    from ff9mapkit import save as SaveMod
    key, iv = SaveMod._key_iv()
    pt = bytearray(SaveMod.SAVE_BLOCK_SIZE)
    pt[0:4] = magic
    pt[SI.MAIN_GIL_OFF:SI.MAIN_GIL_OFF + 4] = int(gil).to_bytes(4, "little")
    for k, (iid, cnt) in enumerate(items):
        pt[SI.MAIN_ITEMS_OFF + 2 * k] = cnt
        pt[SI.MAIN_ITEMS_OFF + 2 * k + 1] = iid
    if last_live:                                          # make the last slot a live item (no padding tail)
        pt[SI.MAIN_ITEMS_OFF + 2 * (SI.MAIN_ITEMS_N - 1)] = 5
        pt[SI.MAIN_ITEMS_OFF + 2 * (SI.MAIN_ITEMS_N - 1) + 1] = 10
    data = bytearray(SaveMod.BASE_SAVE_BLOCK_OFFSET + SaveMod.SAVE_BLOCK_SIZE * (block + 1))
    lo = SaveMod.BASE_SAVE_BLOCK_OFFSET + SaveMod.SAVE_BLOCK_SIZE * block
    data[lo:lo + SaveMod.SAVE_BLOCK_SIZE] = AES.new(key, AES.MODE_CBC, iv).encrypt(bytes(pt))
    p = tmp_path / "SavedData_ww.dat"
    p.write_bytes(bytes(data))
    return str(p)


def test_validate_main_block_unit():
    pt = bytearray(8000)
    pt[0:4] = b"SAVE"
    pt[SI.MAIN_ITEMS_OFF], pt[SI.MAIN_ITEMS_OFF + 1] = 7, 236             # one live item; rest count 0 (padding)
    SI.validate_main_block(pt)                                            # valid -> no raise
    SI.validate_main_block(_with(pt, SI.MAIN_ITEMS_OFF + 8, [0, 196], [3, 238]))  # count==0 mid-list gap is ok
    with pytest.raises(ValueError):                                       # an invalid live pair (count 200)
        SI.validate_main_block(_with(pt, SI.MAIN_ITEMS_OFF + 4, [200, 10]))
    with pytest.raises(ValueError):                                       # last slot live -> no padding tail
        SI.validate_main_block(_with(pt, SI.MAIN_ITEMS_OFF + 2 * (SI.MAIN_ITEMS_N - 1), [5, 10]))
    with pytest.raises(ValueError):                                       # no SAVE magic
        SI.validate_main_block(_with(pt, 0, list(b"XXXX")))


def _with(base, off, *patches):
    b = bytearray(base)
    cur = off
    for p in patches:
        b[cur:cur + len(p)] = bytes(p)
        cur += len(p)
    return b


def test_read_main_inventory_collects_midlist_gaps():
    pt = bytearray(8000)
    pt[0:4] = b"SAVE"
    for k, (cnt, iid) in enumerate([(7, 236), (0, 196), (2, 238)]):       # a count==0 gap in the middle
        pt[SI.MAIN_ITEMS_OFF + 2 * k], pt[SI.MAIN_ITEMS_OFF + 2 * k + 1] = cnt, iid
    inv = SI.read_main_inventory(pt)
    assert (236, I.name_of(236), 7) in inv and (238, I.name_of(238), 2) in inv and len(inv) == 2


@pytest.mark.skipif(not _has_crypto(), reason="needs pycryptodome")
def test_main_block_read_and_set_gil(tmp_path):
    c = _enc_container(tmp_path, block=1, gil=500, items=((236, 7), (238, 2)))
    assert SI.decode_main_block(c, 1).gil == 500
    g = SI.set_main_gil(c, 1, 12345)                                      # dry-run default
    assert g.wrote is False and g.old_gil == 500 and SI.decode_main_block(c, 1).gil == 500
    g = SI.set_main_gil(c, 1, 12345, dry_run=False)                       # apply
    assert g.wrote and g.bytes_changed == 4 and SI.decode_main_block(c, 1).gil == 12345
    assert (236, I.name_of(236), 7) in SI.decode_main_block(c, 1).inventory   # items survived (only gil moved)
    assert len(glob.glob(c + ".bak.*")) == 1 and g.backup_path == glob.glob(c + ".bak.*")[0]


@pytest.mark.skipif(not _has_crypto(), reason="needs pycryptodome")
def test_main_block_refuses_bad_layout(tmp_path):
    bad = _enc_container(tmp_path, block=1, gil=500, magic=b"XXXX")       # no SAVE magic
    assert SI.decode_main_block(bad, 1) is None
    with pytest.raises(ValueError):
        SI.set_main_gil(bad, 1, 1, dry_run=False)
    bad2 = _enc_container(tmp_path, block=1, last_live=True)              # no padding tail
    with pytest.raises(ValueError):
        SI.set_main_gil(bad2, 1, 1, dry_run=False)


@pytest.mark.skipif(not _has_crypto(), reason="needs pycryptodome")
def test_main_block_set_gil_range_and_noop(tmp_path):
    c = _enc_container(tmp_path, block=1, gil=777)
    with pytest.raises(ValueError):
        SI.set_main_gil(c, 1, SI.GIL_CAP + 1)
    with pytest.raises(TypeError):
        SI.set_main_gil(c, 1, True)
    g = SI.set_main_gil(c, 1, 777, dry_run=False)                         # no-op (already 777)
    assert g.wrote is False and not glob.glob(c + ".bak.*")


def test_resolve_block_unit():
    from ff9mapkit import save as SaveMod
    assert SI._resolve_block(autosave=True) == 0
    assert SI._resolve_block(slot=0, save=2) == SaveMod.block_index(0, 2)
    with pytest.raises(ValueError):
        SI._resolve_block()                                              # nothing specified
    with pytest.raises(ValueError, match="not both"):
        SI._resolve_block(slot=0, save=2, autosave=True)


@pytest.mark.skipif(not _has_crypto(), reason="needs pycryptodome")
def test_set_gil_in_save_dual_write(tmp_path):
    """A Memoria save: gil is written to BOTH the main block and the extra mirror."""
    from ff9mapkit import save as SaveMod
    c = _enc_container(tmp_path, block=1, gil=500, items=((236, 7),))
    extra = SaveMod.extra_file_path(c, 1)                                 # block 1 -> _Memoria_0_0.dat
    _extra_file(tmp_path, name=os.path.basename(extra), common=_common(gil=500))
    res = SI.set_gil_in_save(c, 1, 4242, dry_run=False)
    assert res["main"].wrote and res["extra"] is not None and res["extra"].wrote
    assert SI.decode_main_block(c, 1).gil == 4242 and SI.inspect(extra)[0][1].gil == 4242
    assert "[main block]" in SI.render_gil_dual(res) and "load-authoritative" in SI.render_gil_dual(res)


@pytest.mark.skipif(not _has_crypto(), reason="needs pycryptodome")
def test_set_gil_in_save_no_extra_vanilla(tmp_path):
    """A vanilla save (no extra): only the main block is written; the renderer says so."""
    c = _enc_container(tmp_path, block=1, gil=500)
    res = SI.set_gil_in_save(c, 1, 4242, dry_run=False)
    assert res["main"].wrote and res["extra"] is None
    assert SI.decode_main_block(c, 1).gil == 4242 and "vanilla save" in SI.render_gil_dual(res)


@pytest.mark.skipif(not _has_crypto(), reason="needs pycryptodome")
def test_cli_set_gil_container_dual(tmp_path, capsys):
    """The items-set-gil CLI on a container writes the main block (no-extra vanilla slot)."""
    from ff9mapkit import cli
    c = _enc_container(tmp_path, block=1, gil=500)
    rc = cli._cmd_items_set_gil(_ns(save=c, gil=4242, slot=0, save_no=0))   # dry-run default
    assert rc == 0 and "DRY RUN" in capsys.readouterr().out and SI.decode_main_block(c, 1).gil == 500
    rc = cli._cmd_items_set_gil(_ns(save=c, gil=4242, slot=0, save_no=0, apply=True))
    assert rc == 0 and SI.decode_main_block(c, 1).gil == 4242


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


def _real_extra_files():
    from ff9mapkit import save as S
    d = S.default_save_dir()
    return sorted(glob.glob(os.path.join(str(d), "SavedData_ww_Memoria_*.dat"))) if d else []


@pytest.mark.skipif(not _real_extra_files(), reason="no real FF9 Memoria extra save on this machine")
def test_real_extra_set_gil_dry_run_surgical():
    """Dry-run set_gil against EVERY real extra file: gate 1 (codec reproduces the file) passes and the
    computed edit is surgical (<=4 bytes). Writes NOTHING (the real in-game write is the human's go-ahead)."""
    for extra in _real_extra_files():
        before = open(extra, "rb").read()
        rep = SI.set_gil(extra, 1, dry_run=True)           # value differs from the real 500 -> exercises a diff
        assert rep.wrote is False and rep.bytes_changed <= 4
        assert open(extra, "rb").read() == before          # untouched
