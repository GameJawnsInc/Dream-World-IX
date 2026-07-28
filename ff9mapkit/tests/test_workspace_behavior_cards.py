"""The Info Hub's Behavior-archetypes SECTION (rung D's last item): the sidebar row with its
count, the card list, and the detail pane teaching the doorway (the Behavior tab's own
stamps). The card DATA is fenced in ``ff9mapkit/tests/test_infohub_behavior.py`` (derivation +
stamp-parity + validate); this file pins only the library WIRING."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication                    # noqa: E402

from ff9mapkit import infohub                                 # noqa: E402
from ff9mapkit.workspace.forms_qt import CatalogLibrary       # noqa: E402
from ff9mapkit.workspace.shell import pick_palette            # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_the_library_has_a_behavior_archetypes_section(app):
    lib = CatalogLibrary(None, None, pick_palette("dark"))
    idx = lib._cat_kinds.index("behavior")             # raises if the section is missing
    assert f"({len(infohub.behavior_entries())})" in lib.cats.item(idx).text()
    lib.cats.setCurrentRow(idx)
    names = [lib.lst.item(i).text() for i in range(lib.lst.count())]
    assert names == [e.name for e in infohub.behavior_entries()]
    lib.lst.setCurrentRow(names.index("guard"))
    html = lib.detail.toHtml()
    assert "TARGET" in html                            # the needs fact reached the pane
    assert "Archetype" in html                         # ...and the doorway teaching with it
    lib.lst.setCurrentRow(names.index("siege"))
    html = lib.detail.toHtml()
    assert "[siege]" in html and "skeleton" in html
