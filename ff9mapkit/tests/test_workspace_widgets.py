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
    # heading()/role="h1"/role="display" are RETIRED -- zero call sites for three rounds, kept alive only
    # by this test. role="name" (widgets.nameplate) is the top rung now and it has real callers.
    lab = widgets.role_label("Camera", "h2")
    assert lab.property("role") == "h2" and lab.accessibleName() == "Camera"
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


def test_palette_display_row_is_categorised_with_keybinding_hints():
    # Phase 6: Ctrl-K rows are verb-first + category-prefixed + keybinding-hinted. display_row shapes only the
    # DISPLAY (the stored label is untouched, so the fuzzy matcher + tests still key on it).
    from ff9mapkit.workspace.palette import display_row
    assert display_row("New Field…", "command") == "Action  ·  New Field…      ⌨ Ctrl+N"
    assert display_row("Go to Battle", "view") == "Go to  ·  Battle"           # redundant leading verb stripped
    assert display_row("What is Walkmesh?", "learn") == "Learn  ·  Walkmesh"   # concept row cleaned
    assert display_row("Deploy now (F9)", "command") == "Action  ·  Deploy now      ⌨ F9"   # F9 -> ⌨ column
    assert display_row("IC_ENT ▸ npc", "object").startswith("Go to  ·  ")


def test_build_form_adds_a_concept_badge_to_jargon_fields(app):
    # Phase 5: a field whose KIND is a story-flag/scenario reference (or that sets Field.concept) gets a "?"
    # badge that opens the plain-language card; a plain field gets none.
    from PySide6.QtWidgets import QToolButton

    from ff9mapkit.editor import forms, theme
    from ff9mapkit.workspace import forms_qt
    pal = theme.pick_palette("dark")
    w, _g = forms_qt.build_form(forms.NPC_SPEC, {"name": "G", "requires_flag": "x"}, pal)
    badges = [b for b in w.findChildren(QToolButton) if b.objectName() == "conceptBadge"]
    assert badges and any("Story flag" in b.accessibleName() for b in badges), "flag field needs a concept badge"
    w2, _g2 = forms_qt.build_form([forms.Field("name", "Name", forms.STR)], {"name": "x"}, pal)
    assert not [b for b in w2.findChildren(QToolButton) if b.objectName() == "conceptBadge"], "plain field: none"


def test_build_form_tucks_advanced_fields_in_guided_mode(app):
    # Phase 7: Guided beginner mode tucks each spec's expert fields (Field.advanced, or a help starting with
    # "advanced" -- model/animset here) into an 'Advanced options' drawer; Full shows every field inline.
    # Nothing is removed -- every field still has a getter either way.
    from PySide6.QtWidgets import QToolButton

    from ff9mapkit.editor import forms, theme
    from ff9mapkit.workspace import forms_qt
    pal = theme.pick_palette("dark")
    try:
        forms_qt.set_guided(True)
        w, g = forms_qt.build_form(forms.NPC_SPEC, {"name": "G"}, pal)
        drawers = [b for b in w.findChildren(QToolButton) if b.objectName() == "disclosureToggle"]
        assert drawers and "Advanced" in drawers[0].text(), "guided tucks advanced fields into a drawer"
        assert "model" in g and "animset" in g, "nothing removed -- every field still has a getter"
        forms_qt.set_guided(False)
        w2, _g = forms_qt.build_form(forms.NPC_SPEC, {"name": "G"}, pal)
        assert not [b for b in w2.findChildren(QToolButton) if b.objectName() == "disclosureToggle"], "full: inline"
    finally:
        forms_qt.set_guided(True)                          # restore the module default for other tests


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


def test_the_form_docs_share_one_page_rung(app):
    """Build & Deploy / Import / Co-op are the same SHAPE -- one scrolling column of cards -- so their
    page frame must be one number, defined once.

    They had drifted to 16 / 16 / (18, 14, 18, 18): three docs, three answers, one of them asymmetric
    for no stated reason. That is what a magic number does over time, and it is the entire argument for
    `page_margins` being a function rather than a value typed at each site.

    The splitter browsers (Models / Battle) are deliberately NOT in this fence: their panes are the page
    and edge-to-edge is the convention -- an outer margin there only eats pane width.
    """
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    seen = []
    hosts = []                     # hold the parents: a temporary QWidget is GC'd and takes its layout
    for _ in range(3):
        host = QWidget()
        hosts.append(host)
        lay = QVBoxLayout(host)
        widgets.page_margins(lay)
        m = lay.contentsMargins()
        seen.append((m.left(), m.top(), m.right(), m.bottom()))
    assert len(set(seen)) == 1, f"page_margins is not deterministic: {seen}"
    assert seen[0] == (widgets.PAGE_PAD,) * 4, "the page rung must be symmetric"


def test_the_page_rung_clears_the_card_interior():
    """24 outside, 16 inside. The page frame must OUTRANK a card's own padding, not tie it.

    `section()` insets its content by 16. If the page frame were also 16 the card's border would sit
    exactly halfway between the page edge and its own content, and the page would read as one flat
    stack with a stray line in it rather than as cards ON a page. One rung of separation is the cheapest
    thing that makes the containment legible.
    """
    from ff9mapkit.workspace import style

    assert widgets.PAGE_PAD == style.space("space_6") == 24
    assert widgets.PAGE_PAD > 16, "the page frame must exceed the card's 16px interior"
    # and the inter-card gap sits between the in-card row gap (8) and the page frame (24)
    assert 8 < widgets.SECTION_GAP < widgets.PAGE_PAD


def test_prose_w_is_a_real_measure_and_the_caption_face_has_its_own(app):
    """A px cap is a measure for exactly ONE font size -- which is why there are two of these.

    Measured on a native font DB: 13px Segoe runs ~5.59-5.72 px/char, 11px runs ~4.73-4.84. So a single
    620px cap is ~109 chars on the body face and ~130 on the caption face: THE SAME NUMBER IS WORSE ON
    THE SMALLER FACE. `option()`'s 11px caption defaulted to PROSE_W, so the body's compromise was
    silently governing a face it was never measured for.

    420 and not 430: at the worst measured rate a 430 cap lands 75.2ch and fails the 75 fence by a fifth
    of a character. The rate is hard-coded here rather than measured because the suite runs offscreen,
    where the font DB is stubbed and every advance is fiction.
    """
    WORST_13PX = 5.72          # px/char, real prose, native Segoe UI 13
    assert widgets.PROSE_W / WORST_13PX <= 75, (
        f"PROSE_W={widgets.PROSE_W} is {widgets.PROSE_W / WORST_13PX:.1f}ch -- above the 45-75 band"
    )
    assert widgets.PROSE_W / WORST_13PX >= 45, "PROSE_W is now too narrow to read as prose"
    # the two faces must not share one token again
    import inspect
    src = inspect.getsource(widgets.option)
    assert "width=CAPTION_W" in src, "option()'s 11px caption must not inherit the body's measure"


def test_the_caption_measure_is_unchanged_on_purpose(app):
    """CAPTION_W is 620 -- the reviewed-and-approved value, moved zero pixels by this split.

    At 11px the real option captions are ~107-112 chars, so the cap does not bind: they are single lines
    and narrowing it would re-wrap every one. That wants an eye, not a refactor. This test exists so the
    number is understood as DELIBERATE rather than rediscovered as a bug -- and so that lowering it is a
    decision somebody makes on purpose.
    """
    assert widgets.CAPTION_W == 620
