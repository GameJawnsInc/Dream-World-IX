"""The PySide6-FREE half of the workspace: the QSS builder. No Qt, no display (like the editor's
headless tests). The Qt shell itself is exercised by `py apps/ff9_workspace.pyw --smoke` (offscreen)."""

from __future__ import annotations

from ff9mapkit.editor import theme
from ff9mapkit.workspace import style


def test_qss_renders_for_every_palette():
    # qss() is a Template.substitute over the palette -> a palette missing ANY $name key would raise here.
    for mode, pal in theme.THEMES.items():
        css = style.qss(pal)
        assert isinstance(css, str) and len(css) > 500, mode
        assert pal["accent"] in css and pal["bg"] in css and pal["text"] in css, mode
        assert "$" not in css, mode             # every placeholder substituted


def test_qss_leaves_no_unsubstituted_placeholders():
    css = style.qss(theme.DARK)
    assert "$" not in css                      # every $name was substituted from the palette


def test_qss_styles_the_core_widgets():
    css = style.qss(theme.LIGHT)
    for sel in ("QTreeWidget", "QTabBar::tab", "QPlainTextEdit", "QPushButton", "QScrollBar"):
        assert sel in css


def test_qss_carries_no_dock_rules():
    # The shell has no QDockWidget any more (the console is a collapsible splitter pane), so these
    # selectors are dead -- and QMainWindow::separator is what could paint a band across the window.
    css = style.qss(theme.DARK)
    for sel in ("QDockWidget", "QMainWindow::separator"):
        assert sel not in css


def test_qss_greys_a_disabled_accent_button():
    # a disabled accent button (Save with nothing to save) must override the #accent blue -- the id
    # selector out-ranks the generic :disabled rule, so it needs its own #accent:disabled.
    css = style.qss(theme.DARK)
    assert "QPushButton#accent:disabled" in css


def test_qss_specifies_checked_indicators():
    # once a stylesheet touches a QCheckBox/QRadioButton, Qt stops drawing the native checked dot -- so the
    # CHECKED indicator must be explicitly styled or the selected state renders invisible (the Import bug).
    css = style.qss(theme.DARK)
    assert "QRadioButton::indicator" in css and "QCheckBox::indicator" in css
    assert "::indicator:checked" in css


def test_qss_styles_dropdown_menus():
    # the toolbar Field/Campaign/Journey buttons open QMenus -- they must be themed (selected item = accent)
    css = style.qss(theme.DARK)
    assert "QMenu" in css and "QMenu::item:selected" in css


def test_qss_uses_the_derived_tokens_and_scales():
    # Phase-1 substrate: qss() derives the semantic tokens and merges the scales, then feeds the component
    # role classes + the focus ring. NORD is the tell -- its focus token differs from its accent (the accent
    # fails 3:1 on the nord surface, so derive() brightens the focus ring), so a distinct value must appear.
    css = style.qss(theme.NORD)
    d = theme.derive(theme.NORD)
    assert d["focus"] != theme.NORD["accent"] and d["focus"] in css     # focus ring wired to the derived token
    assert d["surface_2"] in css and d["surface_3"] in css              # elevation ladder reaches the rules
    for role in ('QLabel[role="h1"]', 'QLabel[role="caption"]', 'QFrame[role="card"]'):
        assert role in css, role                                        # component role classes present
    assert "20px" in css                                               # the type ramp substituted (h1 = 20px)


def test_qss_accepts_an_already_derived_palette():
    # a caller may hand qss() a derived dict; derive() is idempotent, so this must not double-apply or raise
    # -- and it renders identically to passing the base palette.
    assert style.qss(theme.DARK) == style.qss(theme.derive(theme.DARK))


def test_qss_density_profiles_both_substitute_cleanly():
    # both density profiles must fully substitute (a missing $tb_pad/$row_pad/... would raise) for every theme
    for mode, pal in theme.THEMES.items():
        for dens in ("comfortable", "compact"):
            css = style.qss(pal, dens)
            assert "$" not in css, (mode, dens)
    # an unknown density falls back to comfortable (never raises / never leaves a placeholder)
    assert style.qss(theme.DARK, "bogus") == style.qss(theme.DARK, "comfortable")
    assert style.qss(theme.DARK) == style.qss(theme.DARK, "comfortable")   # default is comfortable


def test_qss_compact_is_tighter_than_comfortable():
    # the point of the toggle: compact shrinks the control paddings. Comfortable keeps the roomy tree rows
    # (6px 8px) it was given; compact drops them (3px 4px) -- so the two renders must differ, tightly.
    comfy = style.qss(theme.DARK, "comfortable")
    tight = style.qss(theme.DARK, "compact")
    assert comfy != tight
    assert "padding: 6px 8px" in comfy and "padding: 6px 8px" not in tight   # the roomy row padding is comfy-only
    assert "padding: 3px 4px" in tight                                       # compact's tighter row padding


def test_checked_indicators_carry_a_tick_and_a_dot():
    """A checked checkbox must show a TICK and a checked radio a DOT -- in every palette.

    What shipped was `background: $accent` and nothing else, so a checked checkbox was a solid accent
    square and a checked radio a solid accent circle: identical except for the corner radius. That throws
    away the only signal that separates "pick several" from "pick exactly one", and a filled swatch reads
    as a colour chip rather than as "checked".

    Checked here rather than by render because the pixel probe is genuinely treacherous: in DRACULA and
    GRUVBOX_DARK `accent_fg` is EQUAL to `bg` (their accents are light, so the ink on them is dark), and a
    naive ink count over the widget then counts the page background as tick pixels and "passes" even when
    nothing drew. (The render was done once, by eye, at 9x -- see studies/gui-aesthetics.)
    """
    from pathlib import Path
    for mode, pal in theme.THEMES.items():
        css = style.qss(pal)
        d = theme.derive(pal)
        assert "QCheckBox::indicator:checked" in css, mode
        # the tick is an SVG on disk: QSS cannot draw a checkmark (no transform, no ::before content)
        tick = [ln for ln in css.splitlines() if "QCheckBox::indicator:checked {" in ln]
        assert tick and "image: url(" in tick[0], f"{mode}: checked checkbox has no tick image"
        svg = tick[0].split("image: url(")[1].split(")")[0]
        assert Path(svg).is_file(), f"{mode}: tick asset missing on disk: {svg}"
        body = Path(svg).read_text(encoding="utf-8")
        assert d["accent_fg"] in body, f"{mode}: tick is not tinted accent_fg (illegible on the accent fill)"
        # the radio's dot is pure QSS -- a radial gradient, no asset
        dot = [ln for ln in css.splitlines() if "qradialgradient" in ln]
        assert dot, f"{mode}: checked radio has no dot gradient"


def test_accent_button_keeps_a_visible_focus_ring():
    """The primary button must show focus -- it had NO ring at all until this rule.

    `QPushButton#accent` (specificity 0,1,0,1) out-ranks the generic `QPushButton:focus` (0,0,1,1), so the
    id selector silently won and every accent button in the app -- including the crumb-row Deploy F9, the
    primary action of the whole application -- rendered identically focused and unfocused. Measured before
    the fix: 0 px changed. Same specificity trap the `#accent:disabled` rule already documents.

    The ring must be `$accent_fg`, not `$focus`: `$focus == $accent` in 6 of 7 palettes, so a $focus ring
    on an $accent fill would be invisible in all but one.
    """
    for mode, pal in theme.THEMES.items():
        css = style.qss(pal)
        d = theme.derive(pal)
        rule = [ln for ln in css.splitlines() if "QPushButton#accent:focus" in ln]
        assert rule, f"{mode}: the primary button has no focus ring (the #accent id out-ranks :focus)"
        assert d["accent_fg"] in rule[0], f"{mode}: accent focus ring must be accent_fg, not $focus"


def test_mono_register_sets_family_only():
    """Machine tokens (ids, session codes, paths) get a mono FAMILY -- and must not get a size.

    Family-only is load-bearing: a font-size here would change row heights and could drag a control under
    the 24px target floor (WCAG 2.5.8) in compact density. It inherits 13px from the base QWidget rule.
    `mono` is an orthogonal property, NOT a role= value, because role is single-valued across ~111 call
    sites -- role="id" on a label would silently drop its existing role="muted".
    """
    css = style.qss(theme.DARK)
    assert 'QLabel[mono="true"]' in css, "no mono register rule"
    block = css.split('QLabel[mono="true"]')[1].split("}")[0]
    assert "font-family" in block
    assert "font-size" not in block, "the mono register must not set a size -- it would move row heights"
    # Inspect the TEMPLATE, not the rendered css: $type_mono IS "12px", so the output is byte-identical
    # whether the console hardcodes 12px or spends the token. Only the source can tell them apart.
    tmpl = style._QSS.template
    console = tmpl.split("QPlainTextEdit")[1].split("}")[0]
    assert "$type_mono" in console, "the console should spend the $type_mono token, not hardcode a size"


def test_qss_has_no_malformed_subcontrol_selectors():
    """A pseudo-CLASS before a pseudo-ELEMENT (`QCheckBox:focus::indicator`) is silently catastrophic.

    Qt does not reject it. `Selector::pseudoElement()` reads the FIRST pseudo, recognises `focus` as a known
    CLASS, and returns ""; `pseudoClass()` then returns 0 on the unknown `indicator`. The match test
    `(0 & state) == 0` is true in EVERY state, so the rule degenerates to an unconditional
    `QCheckBox { border: ... }` -- it targets the whole widget, always, instead of the sub-control on focus.

    This shipped at style.py:126 and put a permanent accent rect around every radio and checkbox in the app
    (it *was* the "cards don't read well" screenshot) while leaving them with no focus ring at all. The a11y
    focus test (test_workspace_a11y.py:136) greps for four known-good selector STRINGS and structurally
    cannot see a malformed one, so it passed throughout. Hence a shape check, not a substring check.
    """
    import re
    for mode, pal in theme.THEMES.items():
        css = style.qss(pal)
        # Widget:class::element -- the correct order is ALWAYS Widget::element:class, so any hit is a bug.
        bad = re.findall(r"[A-Za-z_][\w-]*:[a-z-]+::[a-z-]+", css)
        assert not bad, f"{mode}: pseudo-class before sub-control (Qt matches neither): {bad}"
