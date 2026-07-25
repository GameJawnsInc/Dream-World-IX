"""Wave-2 GUI wiring fences: that wave-1's shared widgets are actually SPENT at every call site.

The study's recurring defect is "a correct mechanism unspent by the call site" -- a good widget that a
caller reimplements or ignores. Wave 1 built widgets.id_field / pack.check_custom_id / widgets.
region_catalog_list / widgets.empty_state; this wave wires them in. So these fence the WIRING, not the
widgets (their own tests live in test_workspace_widgets.py):

  * the empty-stage navigator: no project -> the tree stack shows the teaching empty-state, not a void;
  * the Co-op cross-links + the Home Co-op row (Co-op is a play session, filed under Ship);
  * the FieldIdField call sites: one band lesson, one shared validator, at every id input;
  * the shared region-catalog picker in BOTH dialogs (Import gains Select all/none; shell gains counts).

Headless (offscreen). Every fixture PINS prefs._path to a scratch file for its whole (function-scoped)
life -- the recurring disease is a test that reads or writes the developer's real prefs.json. No
width-to-constant assertions (the offscreen font DB stubs absolute advances); every fence asserts a LAW
a no-op would fail, not a pixel or a row string.
"""
from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
pytest.importorskip("PySide6")

from pathlib import Path                                              # noqa: E402

from PySide6.QtCore import Qt                                        # noqa: E402
from PySide6.QtWidgets import (QApplication, QDialog, QLabel,        # noqa: E402
                               QListWidget, QPushButton, QTreeWidgetItem)

from ff9mapkit import pack                                           # noqa: E402
from ff9mapkit.editor.theme import pick_palette                     # noqa: E402
from ff9mapkit.workspace import shell, widgets                      # noqa: E402
from ff9mapkit.workspace.builddoc import BuildDoc                   # noqa: E402
from ff9mapkit.workspace.coopdoc import CoopDoc                     # noqa: E402
from ff9mapkit.workspace.importdoc import ImportDoc                 # noqa: E402

_REPO = Path(__file__).resolve().parents[2]
_KIT = _REPO / "ff9mapkit"


@pytest.fixture(scope="module")
def app():
    # QApplication is a process singleton and touches no prefs -- module scope is safe (it is not a
    # prefs-bearing fixture, so it can't leak the developer's prefs across the function-scoped pin below).
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pin_prefs(tmp_path, monkeypatch):
    """THE RECURRING DISEASE, fenced: never read or write the developer's real prefs.json. Pinned for the
    whole life of this function-scoped fixture, so Workspace/doc construction + any handler stays isolated."""
    from ff9mapkit import prefs
    monkeypatch.setattr(prefs, "_path", lambda: tmp_path / "prefs.json")
    return tmp_path


def _stub_run(*a, **k):
    return True


def _win(app, pin_prefs):
    return shell.Workspace(pick_palette("dark"))


def _find_link(doc, href):
    for lb in doc.findChildren(QLabel):
        if f'href="{href}"' in lb.text():
            return lb
    return None


# ------------------------------------------------------------------ item 1: the empty-stage navigator
def test_navigator_shows_the_empty_state_until_a_project_loads(app, pin_prefs):
    w = _win(app, pin_prefs)
    # fresh window, nothing open -> the void speaks: the stack shows the empty-state, a filter over a void
    # is misleading so it hides too.
    assert w.tree.topLevelItemCount() == 0
    assert w._nav_stack.currentWidget() is w._nav_empty
    assert w.tree_filter.isHidden(), "no filter box over an empty navigator"
    # a project loads (any top-level row) -> the tree returns and the filter comes back. The tree model's
    # row signals drive the swap, so this must flip with no explicit call.
    w.tree.addTopLevelItem(QTreeWidgetItem(["a field"]))
    assert w._nav_stack.currentWidget() is w.tree
    assert not w.tree_filter.isHidden()
    # ...and closing back to empty returns the empty-state (the open/close path is symmetric)
    w.tree.clear()
    assert w._nav_stack.currentWidget() is w._nav_empty
    assert w.tree_filter.isHidden()


def test_navigator_empty_state_uses_the_shared_teaching_grammar(app, pin_prefs):
    w = _win(app, pin_prefs)
    labels = {lb.property("role"): lb for lb in w._nav_empty.findChildren(QLabel)}
    assert labels["empty_title"].text() == "Nothing open yet"
    assert labels["empty_glyph"].accessibleName() == "", "the glyph is decorative -- not announced"
    assert "caption" in labels, "the teach line rides as a measured caption (inside the measure)"


# ------------------------------------------------------------------ item 2: Co-op wayfinding
def test_build_and_coop_cross_link_each_other(app, pin_prefs):
    fired = []
    b = BuildDoc(pick_palette("dark"), _REPO, run=_stub_run, problems=lambda *a, **k: None,
                 on_coop=lambda: fired.append("coop"))
    link = _find_link(b, "coop")
    assert link is not None and link.property("role") == "muted", "the cross-link is quiet-tier (no accent)"
    assert link.textInteractionFlags() & Qt.TextInteractionFlag.LinksAccessibleByKeyboard, \
        "the cross-link is a keyboard Tab stop, not mouse-only (a11y)"
    link.linkActivated.emit("coop")
    assert fired == ["coop"], "the Build & Deploy header link navigates to Co-op"

    c = CoopDoc(pick_palette("dark"), _KIT, run=_stub_run, on_build=lambda: fired.append("build"))
    c._poll.stop()                                    # don't leave the 2s status poll running past the test
    clink = _find_link(c, "build")
    assert clink is not None and clink.property("role") == "muted"
    assert clink.textInteractionFlags() & Qt.TextInteractionFlag.LinksAccessibleByKeyboard, \
        "the cross-link is a keyboard Tab stop, not mouse-only (a11y)"
    clink.linkActivated.emit("build")
    assert fired == ["coop", "build"], "the Co-op header link navigates to Build & Deploy"


def test_no_cross_link_without_a_nav_callback(app, pin_prefs):
    # the guard: a doc built without the shell's nav lambda renders NO dangling link (it can't navigate).
    b = BuildDoc(pick_palette("dark"), _REPO, run=_stub_run, problems=lambda *a, **k: None)
    assert _find_link(b, "coop") is None


def test_home_carries_a_coop_nav_row(app, pin_prefs):
    w = _win(app, pin_prefs)
    btns = [b for b in w._welcome_tab.findChildren(QPushButton) if b.text() == "Go to Co-op"]
    assert btns, "Home has a Co-op entry row (it was conspicuously absent from the object index)"
    btns[0].click()
    assert w.tabs.currentWidget() is w.coop_doc, "the Home Co-op row navigates to the Co-op tab"


# ------------------------------------------------------------------ item 3: one band lesson, one validator
def test_new_field_rejects_an_out_of_band_id_in_the_shared_voice(app, pin_prefs, tmp_path):
    w = _win(app, pin_prefs)
    with pytest.raises(ValueError) as ei:
        w._new_field("TESTROOM", str(tmp_path), field_id=3999)
    msg = str(ei.value)
    # the shared check_custom_id voice, not a hand-copied string -- names the input + teaches the band
    assert "field id" in msg and "custom band" in msg


def test_new_journey_hub_and_entry_ids_use_the_shared_validator(app, pin_prefs, tmp_path):
    w = _win(app, pin_prefs)
    with pytest.raises(ValueError) as ei:
        w._new_journey("Hub", str(tmp_path), hub_id=99999)
    assert "hub field id" in str(ei.value) and "custom band" in str(ei.value)
    with pytest.raises(ValueError) as ei2:
        w._new_journey("Hub", str(tmp_path), kind="bare", hub_id=4600, entry=1)
    assert "entry field id" in str(ei2.value)


def test_add_region_journey_row_speaks_the_band_voice(app, pin_prefs):
    w = _win(app, pin_prefs)
    w.manifest = SimpleNamespace(journeys=[])         # dialog-free core; no open hub file needed to reach the id check
    problems = []
    w._show_problems = lambda verdict, probs: problems.append((verdict, probs))
    ok = w._append_journey_row("dali", "Dali", "1", "")
    assert ok is False
    joined = " ".join(p.message for _v, probs in problems for p in probs)
    assert "entry field id" in joined and "custom band" in joined


def test_import_fork_id_gets_the_band_caption_and_validator(app, pin_prefs, tmp_path):
    doc = ImportDoc(pick_palette("dark"), _KIT, run=_stub_run, problems=lambda *a, **k: None)
    # the previously caption-less fork-id box now carries the same band lesson the New pickers stamp
    caps = [lb for lb in doc.findChildren(widgets.Prose) if lb.text() == widgets.BAND_HINT]
    assert caps, "the Import fork-id box now teaches the custom band"
    # ...and validates at Import-time in the shared voice (it had NO band check before -- any number passed)
    doc.field.setText("100")
    doc.out.setText(str(tmp_path))
    doc.fid.setText("99999")
    warned = []
    doc._warn = lambda title, text: warned.append((title, text))
    doc.on_import()
    assert warned and "custom band" in warned[-1][1], "an out-of-band fork id is caught with the band lesson"


# ------------------------------------------------------------------ item 4: one region picker, both dialogs
def _fake_catalog(monkeypatch):
    from ff9mapkit import refarc
    arcs = [SimpleNamespace(key="evil_forest", name="Evil Forest", seed=250, members=[250, 251, 252], note="disc 1"),
            SimpleNamespace(key="ice_cavern", name="Ice Cavern", seed=300, members=[300, 301], note="")]
    monkeypatch.setattr(refarc, "load_region_catalog",
                        lambda: SimpleNamespace(title="FF9 Disc 1", arcs=arcs))


def _capture_dialog(monkeypatch):
    """Intercept the modal: capture the built QDialog and reject it instead of blocking on .exec()."""
    captured = []

    def _fake_exec(self):
        captured.append(self)
        return QDialog.DialogCode.Rejected

    monkeypatch.setattr(QDialog, "exec", _fake_exec)
    return captured


def test_import_region_catalog_uses_the_shared_builder_and_gains_select_all(app, pin_prefs, monkeypatch):
    _fake_catalog(monkeypatch)
    captured = _capture_dialog(monkeypatch)
    doc = ImportDoc(pick_palette("dark"), _KIT, run=_stub_run, problems=lambda *a, **k: None)
    doc.open_region_catalog()
    dlg = captured[0]
    lst = dlg.findChildren(QListWidget)[0]
    assert any("fields" in lst.item(i).text() for i in range(lst.count())), "Import shows the member count"
    names = {b.text() for b in dlg.findChildren(QPushButton)}
    assert {"Select all", "Select none"} <= names, "Import GAINED Select all/none from its twin"
    # assert the LAW (a click checks the rows), not the button label
    [b for b in dlg.findChildren(QPushButton) if b.text() == "Select all"][0].click()
    assert all(lst.item(i).checkState() == Qt.CheckState.Checked for i in range(lst.count()))
    [b for b in dlg.findChildren(QPushButton) if b.text() == "Select none"][0].click()
    assert all(lst.item(i).checkState() == Qt.CheckState.Unchecked for i in range(lst.count()))


def test_shell_region_picker_gains_field_counts(app, pin_prefs, monkeypatch):
    _fake_catalog(monkeypatch)
    captured = _capture_dialog(monkeypatch)
    w = _win(app, pin_prefs)
    w._pick_regions()
    dlg = captured[0]
    lst = dlg.findChildren(QListWidget)[0]
    # the shell picker was count-less before; the shared builder gives it Import's field counts
    assert any("fields" in lst.item(i).text() for i in range(lst.count())), "the shell picker now shows counts"


def test_new_campaign_first_id_uses_the_shared_validator(app, pin_prefs, tmp_path):
    # the UX-pass catch: New Campaign's 'First field id' was the LONE id box still outside id_field /
    # check_custom_id -- a real-band 100 sailed through to campaign.new_campaign with no band lesson
    w = _win(app, pin_prefs)
    with pytest.raises(ValueError) as ei:
        w._new_campaign("Camp", str(tmp_path), id_base=100)
    msg = str(ei.value)
    assert "first field id" in msg and "custom band" in msg


def test_the_toolbar_overflow_door_is_a_visible_themed_button(app, pin_prefs):
    # Squeezed (narrow window / CALIBRE 150), Qt folds the toolbar tail -- Refresh/Lint/Info Hub/
    # Search/Settings -- into the extension button, whose default arrow painted INVISIBLY: the app's
    # discoverability features vanished with no door. It must carry the themed icon + an a11y name.
    from PySide6.QtWidgets import QStyle, QToolButton
    shell._apply_app_theme(app, pick_palette("dark"))  # the production style (Fusion + the extent fix)
    w = _win(app, pin_prefs)
    ext = w.findChild(QToolButton, "qt_toolbar_ext_button")
    assert ext is not None, "Qt's toolbar extension button exists from construction"
    assert not ext.icon().isNull(), "the overflow door carries the themed icon (the default was invisible)"
    assert ext.accessibleName() == "More toolbar items"
    # the layout SIZES AND PLACES the door from this metric -- a widget minimum cannot fix it (probed:
    # the widened button hung 9px off the window edge). Fusion's 12px cannot hold a glyph.
    assert app.style().pixelMetric(QStyle.PixelMetric.PM_ToolBarExtensionExtent, None, w) >= 24
