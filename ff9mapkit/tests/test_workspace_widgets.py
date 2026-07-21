"""The Phase-1 component factories in workspace.widgets: each stamps a QSS `role` property AND folds in
an accessible name (the a11y hook baked into the factory), plus the tabular-figures helper."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtGui import QFont                      # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel   # noqa: E402

from ff9mapkit.editor import theme                   # noqa: E402
from ff9mapkit.workspace import style, widgets       # noqa: E402


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


def test_a_bad_value_raises_a_notice_and_the_help_survives_it(app):
    """DICTION, and the bug it was really about.

    This test used to assert that a bad value turns THE HINT red -- which is the defect, written down as
    the contract. One label did two jobs: `validate()` did `h.setText(f"⚠ {e}")` over the help text and
    only gave it back once the value parsed. So the sentence telling you what a valid value LOOKS like
    ("a unique number for your field (use >= 4000)") vanished at exactly the moment you were failing to
    type one -- the only moment it was load-bearing. Proven live before the fix, not inferred.

    The sheet had already written the law, four lines above the rule that broke it: "Never demote a
    diagnostic to 11px grey -- demote the EXPLANATION, never the answer."

    Now: the hint TEACHES and is constant; the notice REPORTS and is the variable.
    """
    from PySide6.QtWidgets import QLineEdit

    from ff9mapkit.editor import forms, theme
    from ff9mapkit.workspace import forms_qt

    pal = theme.pick_palette("dark")
    w, _getters = forms_qt.build_form(forms.FIELD_SPEC, {"id": 4000, "name": "ROOM", "area": 11}, pal)
    id_edit = next(e for e in w.findChildren(QLineEdit) if e.text() == "4000")   # the INT id field
    help_before = [lb.text() for lb in w.findChildren(QLabel)
                   if lb.property("role") == "caption" and lb.text().strip()]
    assert help_before, "the form's hints should carry role='caption'"

    id_edit.setText("not-an-int")                                                # fires validate()

    notices = [lb for lb in w.findChildren(QLabel)
               if lb.property("role") == "notice" and lb.text().strip()]
    assert notices, "a bad value must raise a NOTICE -- not repaint the hint"
    assert any(n.property("state") == "error" for n in notices), "the notice must carry state='error'"

    # THE FIX, asserted: the teaching is still on screen while the error is up.
    help_after = [lb.text() for lb in w.findChildren(QLabel)
                  if lb.property("role") == "caption" and lb.text().strip()]
    assert help_before == help_after, (
        "the error destroyed a field's help text -- the hint must never be repainted by validate(); "
        f"lost: {set(help_before) - set(help_after)}"
    )
    assert not any(c.property("state") == "error" for c in w.findChildren(QLabel)
                   if c.property("role") == "caption"), "an error must not be filed in the caption tier"

    # ...and it clears without taking the help with it
    id_edit.setText("4001")
    assert not [lb for lb in w.findChildren(QLabel)
                if lb.property("role") == "notice" and lb.text().strip()], "the notice must clear"
    assert [lb.text() for lb in w.findChildren(QLabel)
            if lb.property("role") == "caption" and lb.text().strip()] == help_before


def test_a_diagnostic_is_never_smaller_than_the_field_it_is_about(app):
    """The split's whole point, fenced as the RELATIONSHIP.

    `notice` is the body rung and `caption` is the caption rung -- pinning 14 and 12 would pass happily
    while the ramp moved away underneath both. What must stay true is the ORDER: you do not read an error,
    you are interrupted by one, so it can never be set smaller and quieter than the prose beside it.
    """
    import re
    css = style.qss(theme.DARK)
    n = re.search(r'QLabel\[role="notice"\]\s*\{([^}]*)\}', css)
    c = re.search(r'QLabel\[role="caption"\]\s*\{([^}]*)\}', css)
    assert n and c, "the notice/caption rules are gone"
    n_px = int(re.search(r"font-size:\s*(\d+)px", n.group(1)).group(1))
    c_px = int(re.search(r"font-size:\s*(\d+)px", c.group(1)).group(1))
    assert n_px > c_px, f"a notice ({n_px}px) must outrank the hint it interrupts ({c_px}px)"
    assert n_px == style.type_px("type_body", 100), "a notice IS the body rung, not its own number"


def test_a_notice_declines_a_ground_of_its_own(app):
    """THE NINTH-GROUND LAW, applied BEFORE the ground exists rather than after.

    A notice is state-coloured text on the card it belongs to, and must not acquire a chip/badge fill.
    Measured over all 8 palettes: error/warn on `surface_2` (where a form lives) pass 4.54-10.22, but on
    `surface_3` they are SUB-AA IN 6 OF 8 (error 3.84-4.23). That is zero pixels today only because
    nothing grounds state text there -- give a notice a chip and it lights up in six palettes at once.

    So the rule may set a colour and a size; it may not set a background. Fenced because "we decided not
    to" is exactly the kind of decision a later round re-makes by accident.
    """
    import re
    for mode, pal in theme.THEMES.items():
        css = style.qss(pal)
        for m in re.finditer(r'QLabel\[role="notice"\][^{]*\{([^}]*)\}', css):
            body = m.group(1)
            assert "background" not in body, (
                f"{mode}: a notice grew a ground. error_text is sub-AA on surface_3 in 6/8 palettes -- "
                f"extend derive()'s grounds and fence them FIRST, or leave the notice on the card."
            )


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

    THE RATE MOVED WITH THE BODY, and for two rounds this fence did not notice. It divided PROSE_W by a
    rate measured at 13px -- and QUARTO P1 put the body at 14. A constant over a constant cannot see the
    app; this one was answering a question about a font size nothing sets any more, and passing.

    Re-measured natively on the app's OWN prose at the 14px rung (evidence/probe_measure_rate.py):
    5.841-6.217 px/char, so 420px is 67.6-71.9ch. The band's ceiling is the risk here, and the ceiling is
    hit by the NARROWEST rate (fewer px per char = more chars on the line), so that is what is pinned.
    """
    WORST_14PX = 5.841         # px/char: the app's real prose at the body rung, native Segoe UI 14.
    #                            The NARROWEST real rate -- it is the one that puts the most characters
    #                            on a line, so it is the one the 75 ceiling must survive.
    ch = widgets.PROSE_W / WORST_14PX
    assert ch <= 75, f"PROSE_W={widgets.PROSE_W} is {ch:.1f}ch -- above the 45-75 band"
    assert ch >= 45, "PROSE_W is now too narrow to read as prose"
    # the two faces must not share one token again
    import inspect
    src = inspect.getsource(widgets.option)
    assert "width=CAPTION_W" in src, "option()'s caption must not inherit the body's measure"
    assert 'base="caption"' in src, "option()'s caption must scale against the CAPTION rung, not the body"


def test_lowering_the_caption_measure_was_a_deliberate_decision(app):
    """620 -> 380. This test used to assert `CAPTION_W == 620` and it DID ITS JOB: it existed so that
    "lowering it is a decision somebody makes on purpose", and it went red and made this one be that.
    It is kept, inverted, rather than deleted -- the number's history is the reason it is defensible.

    620 SURVIVED THREE ROUNDS ON TWO FALSE DEFENCES.

    "The reviewed-and-approved value" -- the approval was real, and was given to PROSE_W at 13px. LEDE cut
    prose to 420 and moved the 620 onto the caption rung, where the same number is strictly worse, and the
    fence went on citing an approval for a tier it was never granted to. The number stood still while its
    meaning moved underneath it.

    "The cap does not bind" -- true, and it was the indictment, not the defence. It only failed to bind
    because `option()` is 3 of 37 caption sites and its strings are short. The moment COLUMN routed a real
    hint through it, 620 rendered 121 characters to the line: 62% over the ceiling, measured at the real
    rung on the real strings. A cap that never binds is not protecting anything; it is decoration.

    (Its second claim, "the real option captions are ~107-112 chars", described exactly ONE of the three.
    The others are 63 and 30. Both defences were built from a sample of one.)
    """
    assert widgets.CAPTION_W == 380, (
        "CAPTION_W moved. It is not a free number: it is the widest cap that keeps EVERY real caption "
        "inside 75ch at the 12px rung. Re-measure with evidence/probe_column.py before changing it."
    )


def test_the_measure_holds_its_character_count_at_every_text_size(app):
    """GAUGE. The measure is in PIXELS and the text is not, so the dial pulled them apart.

    Why this can be a fence at all, when the suite runs offscreen and every advance here is fiction:
    Segoe's advance is LINEAR in pixel size (measured natively 12..28px, max error 0.065% --
    evidence/probe_measure_rate.py). So

        chars = (cap * k) / (rate * k) = cap / rate

    the character count is INVARIANT under scaling, which means fencing the MECHANISM at any one scale
    fences every scale, using no font metrics at all. What is asserted is the ratio Prose applies; the
    real-rate check lives in test_prose_w_is_a_real_measure, at 100%, where the constant is honest.

    THE OLD FENCE COULD NOT HAVE CAUGHT THIS. It divided PROSE_W by a hard-coded rate -- two constants,
    no app, no font, no scale. It passed at 150% exactly as happily as at 100%, and it would have gone on
    passing if the cap had been welded to 420 forever.
    """
    from PySide6.QtGui import QFont

    base = style.type_px("type_body", 100)
    p = widgets.Prose("x" * 200)
    f = QFont("Segoe UI")
    f.setPixelSize(base)
    p.setFont(f)                                   # fires FontChange -> _resolve_cap
    assert p._cap == widgets.PROSE_W, f"at 100% the cap must be the approved {widgets.PROSE_W}, got {p._cap}"

    for pct in (110, 125, 150):
        px = style.type_px("type_body", pct)
        f2 = QFont("Segoe UI")
        f2.setPixelSize(px)
        p.setFont(f2)
        want = int(widgets.PROSE_W * px / base + 0.5)
        assert p._cap == want, f"{pct}%: cap is {p._cap}, expected {want} -- the column did not track the type"
        # the invariant itself, stated the way it matters: the column grew as fast as the letters did
        assert abs(p._cap / px - widgets.PROSE_W / base) < 0.05, (
            f"{pct}%: cap/px drifted -- the measure no longer holds its character count"
        )
    p.deleteLater()


def test_a_caption_scales_against_the_caption_rung_not_the_body(app):
    """The base is load-bearing and its failure is silent.

    CAPTION_W was chosen against the 12px caption rung; PROSE_W against the 14px body. Resolve a caption
    against the body's base and every cap is wrong by 14/12 -- at EVERY setting including 100%, where
    nothing else would look amiss. That is a 17% measure error that no render would obviously show and no
    ratio fence would catch, because the ratios would all still be internally consistent.
    """
    from PySide6.QtGui import QFont

    cap_px = style.type_px("type_caption", 100)
    body_px = style.type_px("type_body", 100)
    assert cap_px != body_px, "this fence needs the two rungs to differ or it proves nothing"

    c = widgets.Prose("x" * 200, widgets.CAPTION_W, base="caption")
    f = QFont("Segoe UI")
    f.setPixelSize(cap_px)
    c.setFont(f)
    assert c._cap == widgets.CAPTION_W, (
        f"a caption at 100% must be the approved {widgets.CAPTION_W}px, got {c._cap} -- it is being "
        f"scaled against the wrong rung"
    )
    f2 = QFont("Segoe UI")
    f2.setPixelSize(style.type_px("type_caption", 150))
    c.setFont(f2)
    assert c._cap > widgets.CAPTION_W, "the caption's measure did not follow the dial"
    c.deleteLater()


def test_an_unpolished_font_does_not_collapse_the_measure(app):
    """QFontInfo, not QFont -- and this is the difference between a cap and a zero.

    A QFont carrying a POINT size reports pixelSize() == -1 (unresolved). Multiply the cap by -1/14 and
    every Prose in the app silently caps at a NEGATIVE width, i.e. collapses. The Windows system font is
    Segoe UI 9pt and reports exactly that, so this is the default state of any label the stylesheet has
    not reached yet -- not a hypothetical.
    """
    from PySide6.QtGui import QFont

    p = widgets.Prose("x" * 200)
    f = QFont("Segoe UI")
    f.setPointSize(9)                              # pixelSize() == -1; QFontInfo resolves it
    p.setFont(f)
    assert p._cap > 0, f"an unresolved point-size font collapsed the measure to {p._cap}"
    assert p.maximumWidth() > 0
    p.deleteLater()


def test_every_hint_is_built_by_the_factory_not_by_hand(app):
    """COLUMN. A hint is `widgets.caption(...)` -- never a QLabel wearing role="caption".

    37 sites built their own: `QLabel(...)`, `setWordWrap(True)`, `setProperty("role", "caption")`. A
    wrapped QLabel with no maximumWidth takes whatever the pane hands it, so the tier whose whole job is
    to explain the app ran (measured live, on the real labels) 103 ch/line at a 1280 window, 198 at 1920
    and 314 at 2560 -- growing 1:1 with the monitor, against a 45-75 band.

    Reads the AST rather than grepping: this module's prose is full of the word "caption", and several of
    these files DISCUSS the pattern in comments. A grep fence would pass on its own documentation.

    THE ONE EXEMPTION is real and must stay explicit: forms_qt's wrap-preview `note` is a constant-height
    panel (setFixedHeight on the label itself -- toggling its height would clip the fixed-height preview
    box above it). Prose WRAPS, and wrapping inside a fixed height clips silently. It stays a bare label.
    """
    import ast
    import pathlib
    ws = pathlib.Path(widgets.__file__).parent
    # Keyed on the VARIABLE, not the line: this exemption first shipped as {("forms_qt.py", 100), (...101)}
    # and went red the moment an unrelated edit two functions above shifted the file down. A fence that
    # breaks when nothing it guards has changed trains people to re-number it without reading it.
    ALLOWED = {("forms_qt.py", "note"),                          # the fixed-height wrap-preview note
               ("builddoc.py", "oc")}                            # mirrors option()'s measured body (rb_other lives in `of`)
    offenders = []
    for py in sorted(ws.glob("*.py")):
        if py.name == "widgets.py":
            continue                                            # the factory itself sets the role
        for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            if getattr(node.func, "attr", None) != "setProperty" or len(node.args) != 2:
                continue
            a1 = node.args[1]
            if isinstance(a1, ast.Constant) and a1.value == "caption":
                var = getattr(node.func.value, "id", None) if hasattr(node.func, "value") else None
                if (py.name, var) in ALLOWED:
                    continue
                offenders.append(f"{py.name}:{node.lineno}")
    assert not offenders, (
        "these build a hint by hand instead of calling widgets.caption(), so they have no measure and "
        f"grow with the window: {offenders}"
    )


def test_the_caption_factory_returns_a_measured_prose(app):
    """The factory has to actually DO the three things, or the fence above is theatre.

    A `caption()` that returned a bare label would pass "every hint uses the factory" perfectly while
    every hint stayed uncapped -- which is precisely the state COLUMN found (the factory existed, it just
    returned a role_label, and 37 sites had quietly stopped calling it).
    """
    c = widgets.caption("a hint about something")
    assert isinstance(c, widgets.Prose), "caption() must return a Prose -- a measure, not just a role"
    assert c.property("role") == "caption"
    assert c.wordWrap()
    assert c.maximumWidth() == widgets.CAPTION_W
    assert c._base_px == style.type_px("type_caption", 100), "a caption must scale against the CAPTION rung"


def test_the_caption_cap_is_a_real_measure_at_the_caption_rung(app):
    """CAPTION_W = 380, and 620 was never a measure.

    Measured on all 23 REAL caption strings, on the labels the app actually builds, at the real 12px rung:
    the rate band is 5.113-5.661 px/char. The CEILING is set by the NARROWEST rate -- fewest px per char
    puts the MOST characters on the line -- so that is the divisor here, not the median.

        620px -> 121 ch   62% over, EVEN WHERE IT BINDS
        420px ->  82 ch   still over
        380px ->  74.3 ch <- the widest cap that holds every real caption

    Hard-coded rather than measured because the suite runs offscreen, where the font DB is stubbed and
    every advance is fiction. Re-measure with evidence/probe_column.py, natively, if the rung moves.
    """
    NARROWEST_12PX = 5.113     # px/char: the app's real caption strings at the caption rung, native Segoe
    ch = widgets.CAPTION_W / NARROWEST_12PX
    assert ch <= 75, f"CAPTION_W={widgets.CAPTION_W} is {ch:.1f}ch on the tightest real caption -- over the band"
    assert ch >= 45, f"CAPTION_W={widgets.CAPTION_W} is {ch:.1f}ch -- too narrow to read"


def test_the_form_docs_build_their_page_through_the_column(app):
    """The page column, fenced where it can actually be checked: at the call site.

    COLUMN gave the hints a real measure and immediately exposed the gap it had been hiding -- Home caps
    its content at 860 and centres it; the form docs never did, so their cards stretched to the window
    (measured 640 / 1102 / 1136 at 1920). A correct 380px hint inside an 1102px card reads at 3:1: a
    narrow ribbon in a wide pane. THE HINT WAS NEVER TOO NARROW, THE PAGE WAS TOO WIDE -- widening the
    hint to 480 puts it back over the band at 94ch.

    Asserted structurally (does the doc CALL page_column) rather than by measuring a rendered width: the
    suite runs offscreen, where the font DB is stubbed, and every width that depends on text is fiction
    there. The real widths are in evidence/probe_column.py, native: cards now 812 at 1600+, 604-ish at
    1280 -- Home's own documented curve, because it is Home's own geometry.
    """
    import ast
    import inspect
    import pathlib
    ws = pathlib.Path(widgets.__file__).parent
    for name in ("builddoc.py", "importdoc.py", "coopdoc.py"):
        src = (ws / name).read_text(encoding="utf-8")
        assert "widgets.page_column(" in src, (
            f"{name} builds its page without the reading column -- its cards will stretch to the window"
        )
        # ...and not by ALSO hand-rolling the old bare layout beside it
        tree = ast.parse(src)
        bare = [n.lineno for n in ast.walk(tree)
                if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "QVBoxLayout"
                and n.args and getattr(n.args[0], "id", None) == "inner"]
        assert not bare, f"{name}:{bare} still builds a bare QVBoxLayout(inner) -- two page opinions"

    # the column is Home's number, not a second opinion about the same thing
    from ff9mapkit.workspace import shell
    home = inspect.getsource(shell.Workspace._build_home) if hasattr(shell.Workspace, "_build_home") else ""
    assert widgets.PAGE_W == 860, "the form docs' column must stay the number Home already uses"


def test_no_control_carries_prose_as_its_own_label(app):
    """THE THIRD LAW, fenced: never put prose inside a widget.

    `widgets.option`'s docstring has stated it since Phase 4 -- "a label doing a description's job" -- and
    Co-op shipped a QCheckBox whose label was a 763px sentence. A QCheckBox does NOT word-wrap, so its
    minimumSizeHint IS the whole string: that ONE control put a 797px floor under its card and held the
    entire Co-op page open, which is why it forced a horizontal scrollbar where every other doc fitted.

    A law in a docstring is a wish. This is the law.

    Fenced on LENGTH, not on px: the pixel cost depends on the font, the rung and the dial, but "a check
    or radio label is a NAME" is true at every size.

    80 IS NOT A TASTE CALL -- IT IS A GAP IN THE DATA. Censused, the app's check/radio labels are:

        130 (Co-op's follow-host), 107, 101   <- SENTENCES. All three pinned a card open.
         71, 70, 70, 67, 66, 63, 60, 60, 60, 58, 57, 57, 53, 53, 49   <- "Name -- short qualifier"

    A 30-character hole sits between 101 and 71, and it separates two genuinely different things: a
    sentence that happens to be in a widget, versus the ordinary "Native -- seamless + faithful" idiom
    that reads fine and compresses acceptably. Fencing in the gap catches the defect and does not
    re-litigate 15 labels that were never the problem. If a future round wants the whole tier through
    option(), that is a decision to make on purpose -- and this number is where to make it.
    """
    import ast
    import pathlib
    ws = pathlib.Path(widgets.__file__).parent
    LIMIT = 80
    offenders = []
    for py in sorted(ws.glob("*.py")):
        for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            if getattr(fn, "id", None) not in ("QCheckBox", "QRadioButton"):
                continue
            for a in node.args:
                # implicit concatenation folds to one Constant, which is exactly the shape to catch
                if isinstance(a, ast.Constant) and isinstance(a.value, str) and len(a.value) > LIMIT:
                    offenders.append(f"{py.name}:{node.lineno} ({len(a.value)} chars) {a.value[:44]!r}")
    assert not offenders, (
        "these controls carry PROSE as their label. A check/radio does not word-wrap, so its "
        "minimumSizeHint is the whole sentence and it pins its card's width open. Use widgets.option(): "
        f"the NAME you tick, the consequence in a capped caption beneath it. {offenders}"
    )
