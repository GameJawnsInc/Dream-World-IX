"""GUI wiring for the Story-State editor's Overworld-position field (headless/offscreen). Drives the
doc's handlers directly (no modal dialogs). Reuses the kit's real save backend on a synthetic save."""

import base64
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("Crypto")

from PySide6.QtWidgets import QApplication              # noqa: E402

from ff9mapkit import save as S                          # noqa: E402
from ff9mapkit.editor.theme import pick_palette          # noqa: E402
from ff9mapkit.workspace.savedoc import StoryStateDoc     # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _geg(sc):
    g = bytearray(2048)
    g[0], g[1] = sc & 0xFF, sc >> 8 & 0xFF
    return bytes(g)


def _make_save(geg_by_block):
    from Crypto.Cipher import AES
    key, iv = S._key_iv()
    nblocks = max(geg_by_block) + 1
    data = bytearray(S.BASE_SAVE_BLOCK_OFFSET + S.SAVE_BLOCK_SIZE * nblocks)
    for n, geg in geg_by_block.items():
        pt = bytearray(S.SAVE_BLOCK_SIZE)
        pt[0:4] = b"SAVE"
        b64 = base64.b64encode(geg)
        pt[23:23 + len(b64)] = b64
        data[S.BASE_SAVE_BLOCK_OFFSET + S.SAVE_BLOCK_SIZE * n:
             S.BASE_SAVE_BLOCK_OFFSET + S.SAVE_BLOCK_SIZE * (n + 1)] = \
            AES.new(key, AES.MODE_CBC, iv).encrypt(bytes(pt))
    return bytes(data)


def _doc(tmp_path, out):
    p = tmp_path / "SavedData_ww.dat"
    p.write_bytes(_make_save({1: _geg(2500)}))
    doc = StoryStateDoc(pick_palette("dark"), output=out.append)
    assert doc.load(str(p))
    doc.slots.setCurrentRow(0)
    return doc, p


def test_worldpos_preview_notes_and_hint(app, tmp_path):
    out = []
    doc, _ = _doc(tmp_path, out)
    # the current spot shows as a placeholder hint (synthetic save = origin)
    assert "current 0,0" in doc.worldpos_var.placeholderText()
    doc.worldpos_var.setText("300,-500")
    doc._preview()
    assert any("world X" in t and "300" in t for t in out)
    assert doc.path and S.FF9Save.load(doc.path)                     # preview wrote nothing (still loads)


def test_worldpos_apply_relocates(app, tmp_path):
    out = []
    doc, p = _doc(tmp_path, out)
    doc.worldpos_var.setText("300,-500")
    doc._confirm = lambda detail: True                               # stub the modal confirm
    doc._apply()
    sv = S.FF9Save.load(str(p))
    assert S.decode_world_position(bytearray(sv.gEventGlobal(1))) == (300.0, -500.0)
    assert sv.gEventGlobal(1)[:2] == bytes([2500 & 0xFF, 2500 >> 8])  # scenario preserved


def test_worldpos_bad_input_is_reported(app, tmp_path):
    out = []
    doc, _ = _doc(tmp_path, out)
    doc.worldpos_var.setText("nonsense")
    doc._preview()
    assert any("Cannot apply" in t for t in out)


def test_worldpos_actor_combo_targets_chocobo(app, tmp_path):
    out = []
    doc, p = _doc(tmp_path, out)
    doc.world_actor_combo.setCurrentText("chocobo")
    doc.worldpos_var.setText("911,-355")
    doc._confirm = lambda detail: True
    doc._apply()
    sv = S.FF9Save.load(str(p))
    assert S.decode_world_position(bytearray(sv.gEventGlobal(1)), "chocobo") == (911.0, -355.0)
    assert S.decode_world_position(bytearray(sv.gEventGlobal(1))) == (0.0, 0.0)   # player record untouched


# ==== 'Undo last edit (restore backup)' -- the one-click recovery of the pre-edit .bak ====
from ff9mapkit.workspace.savedoc import ItemEquipDoc       # noqa: E402
from ff9mapkit import sjbinary as SJ                        # noqa: E402
from ff9mapkit import save_items as SI                      # noqa: E402


def _flag_set(path, block, bit):
    g = S.FF9Save.load(str(path)).gEventGlobal(block)
    return (g[bit >> 3] >> (bit & 7)) & 1


def test_undo_disabled_until_apply_then_disarmed_by_a_different_file(app, tmp_path):
    """The enabled-state LAW: off on a fresh load, armed by an Apply on THIS file, off again when a DIFFERENT
    file loads (and the same-file refresh the Apply itself does must NOT disarm it)."""
    out = []
    doc, p = _doc(tmp_path, out)
    assert not doc.undo_btn.isEnabled()                              # nothing applied yet
    doc._confirm = lambda detail: True
    doc.set_var.setText("8720")                                      # a real change -> a backup is written
    doc._apply()                                                     # (reloads the SAME file internally)
    assert doc.undo_btn.isEnabled() and doc._undo_backups            # armed by the Apply, survives its refresh
    p2 = tmp_path / "Other_ww.dat"
    p2.write_bytes(_make_save({1: _geg(3000)}))
    assert doc.load(str(p2))
    assert not doc.undo_btn.isEnabled() and not doc._undo_backups    # a different file -> disarmed


def test_undo_restores_pre_edit_bytes_and_disarms(app, tmp_path):
    out = []
    doc, p = _doc(tmp_path, out)
    doc._confirm = lambda detail: True
    doc.set_var.setText("8720")
    doc._apply()
    assert _flag_set(p, 1, 8720) == 1                                # the edit landed
    doc._restore()
    assert _flag_set(p, 1, 8720) == 0                                # restored to the pre-edit bytes
    assert not doc.undo_btn.isEnabled()                              # one restore per Apply


def test_undo_cancel_confirm_writes_nothing(app, tmp_path):
    out = []
    doc, p = _doc(tmp_path, out)
    doc._confirm = lambda detail: True
    doc.set_var.setText("8720")
    doc._apply()
    doc._confirm = lambda detail: False                             # decline the restore
    doc._restore()
    assert _flag_set(p, 1, 8720) == 1                               # nothing restored
    assert doc.undo_btn.isEnabled()                                 # still armed -> can retry
    assert any("Cancelled" in t for t in out)


# ---- ItemEquipDoc mirrors the same law (opening a Memoria extra-save directly) ----
def _extra_common(gil=12345):
    c = SJ.SJClass()
    p = SJ.SJClass()
    p.add("name", SJ.SJData(SJ.VALUE, "Zidane"))
    info = SJ.SJClass(); info.add("slot_no", SJ.SJData(SJ.INT, 0)); p.add("info", info)
    p.add("equip", SJ.SJArray([SJ.SJData(SJ.INT, x) for x in [1, 112, 88, 149, 255]]))
    c.add("players", SJ.SJArray([p]))
    c.add("gil", SJ.SJData(SJ.INT, gil))
    c.add("items", SJ.SJArray([]))
    return c


def _extra_file(tmp_path, name, gil):
    root = SJ.SJClass()
    root.add("95000_Setting", SJ.SJClass())
    root.add("40000_Common", _extra_common(gil))
    fp = tmp_path / name
    fp.write_bytes(SJ.dumps(root))
    return fp


def _read_gil(path):
    return SI.read_gil(SI.load_extra_common(str(path))[0])


def test_itemdoc_undo_law_and_restore(app, tmp_path):
    out = []
    a = _extra_file(tmp_path, "SavedData_ww_Memoria_0_2.dat", gil=12345)
    doc = ItemEquipDoc(pick_palette("dark"), output=out.append)
    assert doc.load(str(a))
    doc.slots.setCurrentRow(0)
    assert not doc.undo_btn.isEnabled()                             # fresh load: nothing to undo
    doc._confirm = lambda detail: True
    doc.gil_var.setText("999")
    doc._edit("gil", True)                                          # Apply
    assert doc.undo_btn.isEnabled() and doc._undo_backups
    assert _read_gil(a) == 999                                      # edit landed
    # a different file disarms it
    b = _extra_file(tmp_path, "SavedData_ww_Memoria_0_3.dat", gil=555)
    assert doc.load(str(b))
    assert not doc.undo_btn.isEnabled() and not doc._undo_backups
    # re-load A, re-edit, then restore back to pristine
    assert doc.load(str(a))
    doc.slots.setCurrentRow(0)
    doc.gil_var.setText("777")
    doc._edit("gil", True)
    assert _read_gil(a) == 777
    doc._restore()
    assert _read_gil(a) == 999                                      # back to the value before the last edit
    assert not doc.undo_btn.isEnabled()


def test_backups_of_reads_single_and_dual_shapes():
    """_backups_of must harvest the .bak from a lone WriteReport AND from the dual {'main','extra'} dict."""
    class _Rep:
        def __init__(self, bp): self.backup_path = bp
    assert ItemEquipDoc._backups_of(_Rep("a.bak.20260101-000000")) == ["a.bak.20260101-000000"]
    dual = {"main": _Rep("m.bak.20260101-000000"), "extra": _Rep(None)}
    assert ItemEquipDoc._backups_of(dual) == ["m.bak.20260101-000000"]
    assert ItemEquipDoc._backups_of({"main": _Rep(None), "extra": None}) == []
