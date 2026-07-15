"""The Phase-1 component factories in workspace.widgets: each stamps a QSS `role` property AND folds in
an accessible name (the a11y hook baked into the factory), plus the tabular-figures helper."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtGui import QFont                      # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel   # noqa: E402

from ff9mapkit.workspace import widgets              # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_role_factories_stamp_role_and_accessible_name(app):
    h1 = widgets.heading("Camera", level=1)
    assert h1.property("role") == "h1" and h1.accessibleName() == "Camera"
    assert widgets.heading("X", level=0).property("role") == "display"
    assert widgets.heading("X", level=2).property("role") == "h2"
    assert widgets.caption("hint").property("role") == "caption"
    assert widgets.card().property("role") == "card"


def test_status_chip_names_the_kind_for_a11y(app):
    chip = widgets.status_chip("2 issues", kind="warn")
    assert chip.property("role") == "chip"
    assert chip.property("kind") == "warn"
    assert "warn" in chip.accessibleName()          # status is not conveyed by colour alone


def test_tabular_turns_on_tnum(app):
    lab = widgets.tabular(QLabel("30110"))
    assert lab.font().isFeatureSet(QFont.Tag("tnum"))


def test_empty_state_builds_glyph_title_teach_and_actions(app):
    from PySide6.QtWidgets import QPushButton
    fired = []
    w = widgets.empty_state(
        "▦", "No battle map open",
        teach="A battle map defines an encounter.",
        actions=[("Fork…", lambda: fired.append("fork")),
                 None,                                       # a gated-off action is skipped, not rendered
                 ("Open…", lambda: fired.append("open"))])
    labels = {lb.property("role"): lb for lb in w.findChildren(QLabel)}
    assert "empty_glyph" in labels and "empty_title" in labels and "caption" in labels
    assert labels["empty_glyph"].accessibleName() == "", "the glyph is decorative -- not announced"
    assert labels["empty_title"].text() == "No battle map open"
    btns = w.findChildren(QPushButton)
    assert [b.text() for b in btns] == ["Fork…", "Open…"], "falsy actions are dropped"
    assert btns[0].objectName() == "accent", "the first action is the accented primary"
    btns[0].click(); btns[1].click()
    assert fired == ["fork", "open"], "action callbacks are wired"


def test_attach_shadow_sets_a_drop_shadow_effect(app):
    from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect
    f = widgets.attach_shadow(QFrame(), blur=20, dy=6)
    eff = f.graphicsEffect()
    assert isinstance(eff, QGraphicsDropShadowEffect)
    assert eff.blurRadius() == 20 and eff.yOffset() == 6 and eff.xOffset() == 0


def test_command_palette_is_a_frameless_shadowed_card(app):
    # Phase-3 drop-shadow: the Ctrl-K palette is a frameless, translucent overlay whose inner rounded card
    # carries a real QGraphicsDropShadowEffect (a framed dialog would only get OS chrome).
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect

    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.palette import CommandPalette
    p = CommandPalette(None, [("New Field…", "command", lambda: None)], pick_palette("dark"))
    assert bool(p.windowFlags() & Qt.FramelessWindowHint)
    assert p.testAttribute(Qt.WA_TranslucentBackground)
    card = p.findChild(QFrame, "paletteCard")
    assert card is not None and isinstance(card.graphicsEffect(), QGraphicsDropShadowEffect)


def test_build_form_flips_a_bad_field_to_the_error_state(app):
    # The Phase-2 forms_qt migration replaced the inline red/muted hint styles with a caption `role` + a
    # `state` property (styled by QSS, repolished on change). Assert the mechanism: a value that fails its
    # parser puts its hint into state='error' (which the QSS colours red) -- no inline setStyleSheet.
    from PySide6.QtWidgets import QLineEdit

    from ff9mapkit.editor import forms, theme
    from ff9mapkit.workspace import forms_qt

    pal = theme.pick_palette("dark")
    w, _getters = forms_qt.build_form(forms.FIELD_SPEC, {"id": 4000, "name": "ROOM", "area": 11}, pal)
    id_edit = next(e for e in w.findChildren(QLineEdit) if e.text() == "4000")   # the INT id field
    id_edit.setText("not-an-int")                                                # fires validate()
    captions = [lb for lb in w.findChildren(QLabel) if lb.property("role") == "caption"]
    assert captions, "the form's hints should carry role='caption'"
    assert any(c.property("state") == "error" for c in captions), "a bad value must set state='error'"
