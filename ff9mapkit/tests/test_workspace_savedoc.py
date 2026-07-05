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
