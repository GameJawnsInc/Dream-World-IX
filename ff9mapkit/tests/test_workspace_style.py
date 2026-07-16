"""The PySide6-FREE half of the workspace: the QSS builder. No Qt, no display (like the editor's
headless tests). The Qt shell itself is exercised by `py apps/ff9_workspace.pyw --smoke` (offscreen)."""

from __future__ import annotations

from ff9mapkit import prefs
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
    for role in ('QLabel[role="name"]', 'QLabel[role="caption"]', 'QFrame[role="card"]'):
        assert role in css, role                                        # component role classes present
    # NB not `assert "20px" in css` -- that matched a button's padding-right as happily as the ramp, so it
    # passed whether or not the ramp existed. Match the DECLARATION. (role="h1"/"display" are retired:
    # zero call sites for three rounds; role="name" is the top rung now.)
    import re as _re
    assert _re.search(r'role="name"[^}]*font-size:\s*26px', css)        # the type ramp substituted


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


def test_a_diagnostic_value_can_keep_full_weight():
    """A roleless value label must be able to carry a warn/error state.

    The state colours were scoped to `role="muted"` / `role="caption"` only, so a definition-list VALUE --
    which is deliberately roleless, because it is the answer at full weight -- had no way to turn amber.
    "netsync MISSING" is the answer to "why doesn't co-op work"; demote the explanation, never the answer.

    The role-scoped rules must still out-rank the generic one (more attributes = higher specificity), so a
    muted hint keeps its own tint rather than inheriting the value tint.

    It must wire to the DERIVED *_text rung, not the raw hue: the raw hue is fenced at 3.0 (the non-text
    floor) because its first job is icons, and as TEXT it measured 3.51 (warn, solarized-dark) / 2.67
    (error, nord). A diagnostic you cannot read is not a diagnostic.
    """
    for mode, pal in theme.THEMES.items():
        css = style.qss(pal)
        d = theme.derive(pal)
        warn = [ln for ln in css.splitlines() if 'QLabel[state="warn"]' in ln and "role=" not in ln]
        err = [ln for ln in css.splitlines() if 'QLabel[state="error"]' in ln and "role=" not in ln]
        assert warn, f"{mode}: a roleless value label cannot show a warn state"
        assert err, f"{mode}: a roleless value label cannot show an error state"
        assert d["warn_text"] in warn[0], f"{mode}: warn TEXT must use the derived AA rung, not the raw hue"
        assert d["error_text"] in err[0], f"{mode}: error TEXT must use the derived AA rung, not the raw hue"
        # the role-scoped variants must still exist, or a muted hint would lose its own warn tint
        assert 'QLabel[role="muted"][state="warn"]' in css, f"{mode}: the muted-hint warn rule went missing"
        # the banner STRIPE is non-text and must keep the canonical hue (3.0 is the right bar there)
        stripe = [ln for ln in css.splitlines() if 'role="banner"][state="error"]' in ln]
        assert stripe and d["error"] in stripe[0], f"{mode}: the banner stripe must keep the canonical hue"


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


def test_the_quiet_button_tier_greys_out_when_disabled():
    """The bottom rung of the button ladder must still SAY "disabled" when disabled.

    `QPushButton[role="quiet"]` (0,0,1,1: type + attribute) TIES the generic `QPushButton:disabled`
    (0,0,1,1: type + pseudo-class) on specificity, and the quiet block is declared LATER -- so source
    order hands the win to the quiet rule and a disabled quiet button would paint its enabled colour.
    Measured before this rule existed: enabled and disabled both resolved to $text (#e6e8eb in dark),
    byte-identical. Only `[role="quiet"]:disabled` (0,0,2,1) outranks both.

    Live, not hypothetical: builddoc's `_busy()` disables `pack_btn` for the whole of every build.
    """
    for mode, pal in theme.THEMES.items():
        css = style.qss(pal)
        assert 'QPushButton[role="quiet"]:disabled' in css, mode
        assert 'QPushButton[role="quiet"]:pressed' in css, mode    # no press feedback without it, same trap


def test_the_quiet_tier_drops_the_fill_not_the_text():
    """Hierarchy comes from the missing FILL, never from dimmer text.

    `transparent + muted` is already spent as the DISABLED idiom (QToolButton:disabled), so a quiet
    button drawn in $muted would read as un-clickable rather than as secondary -- and would then be
    indistinguishable from its own :disabled state, which is the very thing the test above fences.
    """
    import re
    for mode, pal in theme.THEMES.items():
        css = style.qss(pal)
        m = re.search(r'QPushButton\[role="quiet"\]\s*\{([^}]*)\}', css)
        assert m, mode
        body = m.group(1)
        assert "background: transparent" in body, mode
        assert pal["text"] in body, f"{mode}: quiet must ink in $text"
        d = theme.derive(dict(pal))
        assert d["muted"] not in body, f"{mode}: quiet must NOT ink in $muted -- that is the disabled idiom"


def test_qss_uses_only_the_radius_language():
    """Three radius tokens, plus documented GEOMETRIC pins. Nothing else gets an opinion on roundness.

    The build had NINE distinct radii (3/4/5/6/7/8/9/10/11) across 26 declarations -- so "make the cards
    rounder" was a 26-site hunt rather than a one-line edit, and two of them (#search 7, #railSeg 7) were
    a rung that existed nowhere else and that nobody could have chosen deliberately.

    The survivors are pinned to a MEASUREMENT, not to taste, and each says so at its site:
      3  -- half of the busy bar's fixed 6px height (shell.py setFixedSize(120, 6)) = its capsule.
            $radius_sm (4) exceeds half-height; Qt then clamps it or squashes the chunk ends.
      9  -- half of the 18px checkbox/radio indicator box = a CIRCLE, the only thing distinguishing
            "pick exactly one" from "pick several".
      11 -- half of the concept badge's fixed 22x22 (forms_qt.py) = a circle.
    The scrollbar handle is also geometric (half its 12px groove) but its value coincides with
    $radius_md, so it spends the token.
    """
    import re
    for mode, pal in theme.THEMES.items():
        css = style.qss(pal)
        got = {int(m) for m in re.findall(r"border-[a-z-]*radius:\s*(\d+)px", css)}
        assert got == {3, 4, 6, 8, 9, 11}, f"{mode}: unexpected radius language {sorted(got)}"


def test_the_dead_groupbox_rules_are_gone():
    """QGroupBox is constructed in ZERO places -- every boxed section is a widgets.section() card now.

    The migration was forced: QSS silently ignores font-* on QGroupBox::title (colour is that
    sub-control's only lever; render-verified at 13/600, 11/700 and 18/700 -- identical ink), so while Qt
    drew the title a card could never be given any presence. Rules for a widget nobody builds are a
    permanent tax on every future palette and a permanent lie to whoever greps for them.

    Comments are STRIPPED before the check: the sheet is allowed to explain why the rules are gone (and
    does), so a substring test over the raw text would fence the prose rather than the rules.
    """
    import re
    for mode, pal in theme.THEMES.items():
        rules = re.sub(r"/\*.*?\*/", "", style.qss(pal), flags=re.S)
        assert "QGroupBox" not in rules, f"{mode}: a rule for a widget nobody constructs"
        assert "QFrame#card" not in rules, f"{mode}: the second card language is back"
    # the density tokens the dead rules were the only consumers of
    src = re.sub(r"/\*.*?\*/", "", style._QSS.template, flags=re.S)
    for dead in ("gb_margin_top", "gb_pad_top"):
        assert dead not in src, f"{dead} outlived the widget it styled"
    for profile in style._DENSITY.values():
        assert "gb_margin_top" not in profile and "gb_pad_top" not in profile


def test_the_spacing_grid_means_one_thing_in_qss_and_in_layouts():
    """`$space_2` in the sheet and `space("space_2", d)` in a layout must be the same number.

    QLayout is not styleable and has no cascade, so the grid can only reach setContentsMargins as an
    int. If the two rungs disagree, one name quietly means 8px in QSS and 6px in a layout -- exactly the
    drift the grid exists to end. Compact must also not ALIAS rungs: a scale whose job is rhythm loses it
    the moment two rungs collapse to the same number.
    """
    for density in ("comfortable", "compact"):
        css = style.qss(theme.DARK, density)
        assert f"padding: 2px {style.space('space_2', density)}px" in css, density
        rungs = [style.space(k, density) for k in ("space_1", "space_2", "space_3", "space_4", "space_6")]
        assert rungs == sorted(rungs), f"{density}: the grid must ascend"
        assert len(set(rungs)) == len(rungs), f"{density}: rungs alias -- {rungs}"
    # compact is genuinely tighter at every rung above the 4px floor
    for k in ("space_2", "space_3", "space_4", "space_6"):
        assert style.space(k, "compact") < style.space(k, "comfortable"), k
    # an unknown density falls back to comfortable, exactly as qss() does
    assert style.space("space_4", "nonsense") == style.space("space_4", "comfortable")


def test_the_accent_emits_one_edge_and_the_border_pair_emits_two():
    """THE MATERIAL'S RULE: emit both edges only where one of them is QUIET; emit one where neither is.

    $border is a desaturated grey with a quiet edge (d6-d13), so every object emits the pair and each
    palette eats the edge it cannot hold. $accent is saturated and has NO quiet edge (carrier/quiet 36/25
    in dark, 24/22 in nord) -- emitting its pair would bevel the largest, loudest object on the screen.

    test_editor_theme asserts the PREMISE (accent has no quiet edge). This asserts the CONSEQUENCE.
    """
    import re
    css = style.qss(theme.DARK)

    m = re.search(r"QPushButton#accent\s*\{([^}]*)\}", css)
    assert m, "the accent rule moved"
    body = m.group(1)
    assert "border-top-color" in body, "the primary must be lit -- and must restate it after `border:`"
    assert "border-bottom-color" not in body, (
        "the accent must emit ONE edge: it is saturated and has no quiet edge, so a pair renders as a "
        "symmetric bevel on the loudest object on screen"
    )

    m = re.search(r"QToolButton, QPushButton\s*\{([^}]*)\}", css)
    assert m and "border-top-color" in m.group(1) and "border-bottom-color" in m.group(1), (
        "the generic button must emit BOTH border edges -- the palette eats the quiet one"
    )


def test_an_input_is_cut_and_a_button_is_raised():
    """The inversion IS the material. Raised and cut are the same two colours in opposite order, which is
    what makes this read as one light source rather than as decoration on two unrelated widgets.
    """
    import re
    for mode, pal in theme.THEMES.items():
        css = style.qss(pal)
        d = theme.derive(dict(pal))
        btn = re.search(r"QToolButton, QPushButton\s*\{([^}]*)\}", css).group(1)
        inp = re.search(r"QLineEdit\s*\{([^}]*)\}", css).group(1)
        assert f"border-top-color: {d['border_lit']}" in btn, mode      # raised: lit on top
        assert f"border-bottom-color: {d['border_shade']}" in btn, mode
        assert f"border-top-color: {d['border_shade']}" in inp, mode    # cut: the exact inverse
        assert f"border-bottom-color: {d['border_lit']}" in inp, mode


def test_no_placeholder_hides_in_a_qss_comment():
    """string.Template has no concept of a CSS comment, so a $name inside one still substitutes.

    This has now broken the build TWICE, both times while writing a comment that EXPLAINS a token:
      - naming a deleted density token as $gb_margin_top -> KeyError on every palette at import
      - naming a rejected token as $well in the console comment -> KeyError, same shape
    and once more as a bare '$' in prose -> ValueError: Invalid placeholder.

    A comment cannot hold this law -- the file already had one saying exactly this and it did not stop
    the second occurrence. So it is a test. Name tokens in comments WITHOUT the leading dollar.

    Live placeholders are fine anywhere; this only fences comments, where a name is prose about a token
    rather than a request for its value.
    """
    import re
    src = style._QSS.template
    for m in re.finditer(r"/\*.*?\*/", src, re.S):
        hits = re.findall(r"\$[A-Za-z_][A-Za-z0-9_]*", m.group(0))
        assert not hits, (
            f"placeholder(s) {hits} inside a QSS comment -- Template will substitute them, and will "
            f"KeyError the moment the token is renamed or removed. Drop the leading dollar."
        )
        assert "$" not in m.group(0), (
            "a bare '$' in a QSS comment is an Invalid-placeholder ValueError at import"
        )


# The weights Segoe UI can actually DRAW, measured on the native platform (Windows 11, Segoe UI 13px):
#
#     weight   advance   renders as
#     100-300   59.08    Light
#     350       61.09    Semilight
#     400-500   63.22    Regular      <-- 500 IS 400. Byte-identical pixel buffers.
#     550-650   65.97    Semibold     <-- 550 is the first weight that gets heavier
#     700-800   69.48    Bold
#     900       74.12    Black
#
# This is DATA, not a render, and it has to be: the suite runs offscreen, where Qt stubs the font
# database -- a render test here would measure the harness, not Segoe. That is the same trap that made an
# earlier round invent a horizontal-scroll emergency. Re-measure with:
#     py -c "from PySide6.QtGui import QFont,QFontMetricsF; ..."   on the NATIVE platform.
_SEGOE_CUTS = ((100, 300, "Light"), (350, 350, "Semilight"), (400, 500, "Regular"),
               (550, 650, "Semibold"), (700, 800, "Bold"), (850, 950, "Black"))


def test_every_declared_weight_is_a_weight_segoe_can_draw():
    """A declared font-weight must be the weight it will actually RENDER as -- or it is a lie in the sheet.

    `role="label"` shipped `font-weight: 500` for three rounds. Segoe UI ships no Medium, so 500 renders
    as Regular: byte-identical to the body text it was supposed to outrank. Every form label in the
    Editor -- the app's #1 hours-spent surface -- was indistinguishable from body, while `forms_qt.py`
    called it "the type ramp".

    The rule: declare the FLOOR of a cut, never a value inside it. 500 and 450 both mean Regular, so
    writing them means you wanted Medium and did not get it. 600 is inside the Semibold cut but is its
    conventional name, so the floor rule is relaxed to "same cut as a canonical CSS weight".
    """
    import re
    canonical = {400, 600, 700, 900, 300, 350}          # the weights this app is allowed to intend
    css = style.qss(theme.DARK)
    for w in {int(m) for m in re.findall(r"font-weight:\s*(\d+)", css)}:
        cut = next((c for c in _SEGOE_CUTS if c[0] <= w <= c[1]), None)
        assert cut, f"font-weight: {w} is outside every measured Segoe cut"
        lo, hi, name = cut
        assert w in canonical, (
            f"font-weight: {w} renders as {name} (the {lo}-{hi} cut). Segoe UI cannot draw a distinct "
            f"weight there -- declare the weight you mean."
        )
        # the specific trap: anything in the Regular cut above 400 is a Medium that does not exist
        assert not (lo == 400 and w > 400), (
            f"font-weight: {w} is byte-identical to 400 on Segoe UI (no Medium). Use 600 for Semibold."
        )


def test_the_type_ramp_assert_actually_measures_the_type_ramp():
    """`assert "20px" in css` could not tell an h1 from a button's padding.

    The sheet contained 20px TWICE -- `QLabel[role="h1"] { font-size: 20px }` and
    `QToolButton[popupMode="2"] { padding-right: 20px }` -- so the assert passed whether or not the type
    ramp existed. It proved nothing it claimed to prove. Match the DECLARATION, not the number.
    """
    import re
    css = style.qss(theme.DARK)
    assert re.search(r'role="name"[^}]*font-size:\s*26px', css), "the nameplate rung is gone or resized"
    assert re.search(r'role="head"[^}]*font-size:\s*18px', css), "the head rung is gone or resized"


def test_only_the_nameplate_wears_the_serif():
    """THE SEAM, FENCED AS A TEST rather than trusted to a comment.

    Extending Sitka out of the hero is the one place this direction touches identity, and it survives on
    a precise argument: `hero.py` ALREADY separated the two halves of the front door -- "the wordmark is
    pal['text'], NEVER gold; a gold 'Dream World IX' is a fan-logo". SIGNET kept GOLD as the identity and
    left the serif neutral. The nameplate spends the neutral half and carries no FF9.

    That argument holds for exactly ONE rule. A serif that spreads to the crumb, the tabs or a card title
    stops being a crown and becomes a costume -- the same failure "one corner, once" was written to
    prevent. `hero.py:138` proved a comment cannot hold a law: it drifted from its own explicit spec
    inside a single round and shipped the front door sub-AA in 8/8. So this is a test.

    (The hero itself paints via QPainter with a QFont chain, not QSS, so it is correctly not counted here.)
    """
    import re
    for mode, pal in theme.THEMES.items():
        rules = re.sub(r"/\*.*?\*/", "", style.qss(pal), flags=re.S)
        wearing = [m.group(0) for m in re.finditer(r"[^{}]+\{[^}]*Sitka[^}]*\}", rules)]
        assert len(wearing) == 1, f"{mode}: {len(wearing)} rules name Sitka -- exactly one may"
        assert 'role="name"' in wearing[0], f"{mode}: the serif escaped the nameplate: {wearing[0][:60]}"


def test_the_nameplate_outranks_the_body_it_crowns():
    """26px is not decoration -- it is the ratio that makes a screen have a subject.

    Measured on the native platform: Sitka Display 26 caps at 16.03 against Segoe 13's 9.09 = 1.76x. The
    fallback (drop the font-family) is Segoe 24/700 = 1.85x. Both are real crowns.

    This asserts the DECLARED size, not the rendered cap: the suite runs offscreen, where the font DB is
    stubbed and every cap-height measurement is fiction.
    """
    import re
    css = style.qss(theme.DARK)
    m = re.search(r'QLabel\[role="name"\]\s*\{([^}]*)\}', css)
    assert m, "the nameplate rule is gone"
    body = m.group(1)
    assert "font-size: 26px" in body
    # it must outrank every other TYPE rung. empty_glyph (34px) is excluded and the sheet says why at its
    # site: it is "a large decorative glyph", an icon rendered as text, not a rung of the ramp.
    rungs = [int(x) for x in re.findall(r"font-size:\s*(\d+)px", css) if int(x) != 26]
    glyph = int(re.search(r'role="empty_glyph"[^}]*font-size:\s*(\d+)px', css).group(1))
    rungs = [r for r in rungs if r != glyph]
    assert 26 > max(rungs), f"the nameplate must be the largest type rung; found {max(rungs)}px"


def test_the_log_register_uses_a_weight_the_mono_face_actually_has():
    """600, not 550 -- THE CUT LIST IS PER-FAMILY, and the console is not the app's face.

    NAMEPLATE's fence encodes SEGOE UI's cuts, where 550 is the first weight reaching Semibold. The
    console renders in the mono chain, and measured natively:

        Cascadia Code (dev boxes; ships with VS / Windows Terminal)
            550 -> a real SemiBold cut
        Consolas      (the CLEAN-Windows fallback; ships Regular + Bold only)
            550 -> renders BYTE-IDENTICAL to 400 -- a total no-op
            600 -> Bold

    So a weight that is a real register in one family is invisible in another, and the head/echo tiers
    would silently flatten on exactly the machines that do not have a developer's fonts installed. 600 is
    the first weight that lands heavier in BOTH.

    Asserted as data, not by render: the suite runs offscreen, where the font DB is stubbed.
    """
    from ff9mapkit.workspace import shell as shell_mod

    code = _code_only(shell_mod.Workspace._log)     # docstrings stripped: this one NAMES both weights
    assert "setFontWeight(600)" in code, "the log's head/echo register must be 600 -- 550 is a no-op on Consolas"
    assert "setFontWeight(550)" not in code, "550 renders as Regular on Consolas, the clean-Windows fallback"


def _code_only(obj) -> str:
    """The SOURCE of `obj` with comments AND docstrings removed.

    A source-grepping fence must read CODE, not prose -- and this study has now tripped on that three
    times, because the prose next to a rule is exactly where the rule gets NAMED. A docstring saying
    "never appendHtml" makes a naive `"appendHtml" not in src` fail on the very file that obeys it.
    ast.unparse drops every docstring and comment, so what is left is what actually executes.
    """
    import ast
    import inspect
    import textwrap
    tree = ast.parse(textwrap.dedent(inspect.getsource(obj)))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


def test_the_log_never_switches_the_document_to_rich_text():
    """appendHtml is banned in the console: it flips the QTextDocument to rich text, and from then on any
    line of raw stdout containing a `<` is eaten as markup. A build log is full of them (generics, shell
    redirects, XML). QTextCursor + setCharFormat + insertText keeps the document plain.
    """
    from ff9mapkit.workspace import shell as shell_mod

    assert "appendHtml" not in _code_only(shell_mod.Workspace), \
        "appendHtml switches the console to rich text and mangles stdout"


def test_the_hint_tier_is_never_smaller_than_the_os_thinks_text_is():
    """QUARTO P1's floor, fenced as the RULE and not as the number 12.

    The Windows system font is Segoe UI 9pt, which RESOLVES to 12px. The tier whose entire job is to teach
    a newcomer what a control does was set to 11 -- one pixel BELOW what the OS itself calls text. That is
    the defect the user reported ("the info/hint text in particular is pretty small") and it is the only
    part of their report that was purely a size problem: contrast passes AA in all 8 palettes (4.59 worst)
    and the shipped option captions average ~61 chars, inside the 45-75 band.

    Fenced against 12 as a CONSTANT, deliberately, rather than against QFontInfo(app.font()) at runtime:
    a fence that reads the developer's own machine would pass or fail depending on their Windows font
    settings, and would go green on a box where the OS default happens to be small. 12 is Segoe UI 9pt at
    96 DPI -- the Windows default since Vista. If a future round proves a different floor, move it here
    WITH its receipt; do not let it drift down silently.
    """
    import re
    css = style.qss(theme.DARK)
    for role in ("caption", "chip"):
        m = re.search(r'QLabel\[role="%s"\][^{]*\{([^}]*)\}' % role, css)
        assert m, f'the {role} rule is gone'
        size = re.search(r"font-size:\s*(\d+)px", m.group(1))
        assert size, f"the {role} rule stopped declaring a size -- it now inherits the BODY, which is bigger"
        assert int(size.group(1)) >= 12, (
            f'role="{role}" is {size.group(1)}px -- below the 12px Windows default. The tier that '
            f"explains the app must not be smaller than what the OS calls text."
        )


def test_a_card_title_outranks_the_hint_text_inside_the_card():
    """RUBRIC, fenced on the RELATIONSHIP -- the thing that was actually broken.

    Both rules pointed at the same rung and the same colour, so a card's title was exactly the size and
    the grey of its own footnotes; only a weight step (+4.5% of advance in Segoe) and a pixel of tracking
    told them apart. Pinning cardtitle == 14px would not have caught that -- the bug was never the value,
    it was that two DIFFERENT jobs resolved to ONE token. So assert the rank, in both axes.

    This also fences the trap QUARTO P1 set: raising the body/caption rungs while the title stayed pinned
    to $type_caption would have made the card title the SMALLEST text on its own card.
    """
    import re
    css = style.qss(theme.DARK)

    def rule(sel):
        m = re.search(r"QLabel\[role=\"%s\"\][^{]*\{([^}]*)\}" % sel, css)
        assert m, f"the {sel} rule is gone"
        return m.group(1)

    title, hint = rule("cardtitle"), rule("caption")
    t_px = int(re.search(r"font-size:\s*(\d+)px", title).group(1))
    h_px = int(re.search(r"font-size:\s*(\d+)px", hint).group(1))
    assert t_px > h_px, f"a card's title ({t_px}px) must be LARGER than the hint inside it ({h_px}px)"

    # ...and a colour step, not a weight's worth of grey. $muted resolves to the same hex in both if the
    # title is still on the caption's colour, which is exactly the old bug.
    t_col = re.search(r"color:\s*(#[0-9a-fA-F]+)", title).group(1).lower()
    h_col = re.search(r"color:\s*(#[0-9a-fA-F]+)", hint).group(1).lower()
    assert t_col != h_col, (
        f"a card's title and its hint are both {t_col} -- the title needs a colour step, not just a size one"
    )
    assert t_col == theme.derive(dict(theme.DARK))["text"].lower(), "the card title should be full $text"


def test_the_body_rung_is_a_token_so_the_card_title_cannot_drift_off_it():
    """role="cardtitle" IS the body rung -- a relationship, not a coincidence of two 14s.

    Typed as a literal in both places they drift the moment either moves, and nothing would notice: the
    rank fence above would still pass with the title at 14 and the body at 18. The token is what makes
    "the title is set at reading size" true by construction. (Collapsing the REMAINING literals -- 26px
    name, 15px h3, 34px glyph, 11px badge -- onto one table is QUARTO P3, and CALIBRE is load-bearing on
    it: _SCALES owns 3 of 8 sizes, so scaling it alone would invert the ramp.)
    """
    import re
    # NB: assert against the LIVE dict, not the source text. _code_only() runs ast.unparse, which
    # normalizes quotes to single -- so a '"type_body"' probe can never match and would fail for a reason
    # that has nothing to do with the rule. (It did. A fence must read code, not prose -- and not the
    # formatter's opinion of the code either.)
    assert "type_body" in style._SCALES, "the body rung stopped being a token"
    # the sheet must SPEND it in both places rather than repeat the number
    body_rule = re.search(r"QWidget \{[^}]*\}", style._QSS.template).group(0)
    assert "$type_body" in body_rule, "the QWidget base re-hard-coded its font-size"
    card_rule = re.search(r'QLabel\[role="cardtitle"\][^{]*\{([^}]*)\}', style._QSS.template).group(1)
    assert "$type_body" in card_rule, "the card title must BE the body rung, not merely equal it today"


# --- QUARTO P3: the type table -------------------------------------------------------------------

def test_the_sheet_hard_codes_no_type_size():
    """QUARTO P3: every size the stylesheet sets comes from _TYPE. No exceptions, no strays.

    Before P3 the ramp was split -- 3 tokens and 5 anonymous px typed into the sheet -- which is why the
    app shipped EIGHT distinct sizes while its docs described six, and why the "?" badge sat at 11px, a
    pixel under the OS floor, for a whole round after QUARTO P1 raised the caption rung. Nothing
    connected them, so nothing noticed.

    This is also CALIBRE's foundation and the reason P3 precedes it: a scale that reaches only _SCALES
    would raise the hint while the body stayed frozen -- the annotation outgrowing what it annotates.
    """
    import re
    strays = re.findall(r"font-size:\s*(\d+)px", style._QSS.template)
    assert not strays, (
        f"{len(strays)} hard-coded font-size(s) in the sheet: {strays}px. Every type size belongs in "
        f"_TYPE -- a size the table cannot see is a size no scale can reach and no fence can check."
    )


def test_no_text_rung_sits_below_the_os_floor():
    """The floor applies to the TABLE, not just to the two rules I happened to fence in QUARTO P1.

    Segoe UI 9pt -- the Windows default -- resolves to exactly 12px. Nothing the user READS may sit under
    it. type_glyph is exempt by name and says why at its site: it is an icon that happens to be drawn by
    the font, never read as text.

    Fenced against 12 as a CONSTANT rather than QFontInfo(app.font()) at runtime: a fence that reads the
    developer's own machine passes or fails on their Windows font settings, and would go green on a box
    where the OS default happens to be small.
    """
    ICON_NOT_TEXT = {"type_glyph"}
    for name, px in style._TYPE.items():
        if name in ICON_NOT_TEXT:
            continue
        assert px >= 12, (
            f"{name} is {px}px -- below the 12px Windows default. Text the user reads must not be "
            f"smaller than what the OS itself calls text."
        )


def test_the_badge_stays_a_circle_at_every_text_scale():
    """The badge's TWO ELEVENS were never the same eleven, and this is what keeps them apart.

    border-radius was 11px because it is HALF of forms_qt's 22x22 box -- the definition of a circle. The
    font-size was 11px for entirely unrelated reasons. Welding them is the obvious refactor and it is
    wrong in both directions: scale the glyph alone and the "?" is silently clipped (measured natively:
    the glyph fits a frozen 22px box at 11/12 and OVERFLOWS at 13 -- and setFixedSize clips, never grows);
    scale the box alone and the circle becomes a rounded square.

    So the box is computed, and the two invariants that make it a circle are asserted at EVERY shipped
    scale rather than pinned as a literal (the old fence asserted "border-radius: 11px" in the template
    and broke the moment the value became correct -- it had encoded the mechanism, not the rule):
      * the radius is exactly half the box  ->  requires the box to be EVEN, which badge_box guarantees
      * the box never shrinks below today's 22, whatever the dial says
    """
    for pct in prefs.TEXT_SCALES:
        box = style.badge_box(pct)
        assert box % 2 == 0, f"{pct}%: badge box {box} is odd -- its radius cannot be exactly half"
        assert box >= 2 * style.BADGE_HALF, f"{pct}%: badge box {box} shrank below the shipped 22"
        assert box >= style.type_px("type_badge", pct) + 4, (
            f"{pct}%: badge box {box} is too tight for a {style.type_px('type_badge', pct)}px glyph"
        )
    # and the sheet must SPEND the tokens rather than re-hard-code a number beside them
    import re
    m = re.search(r"QToolButton#conceptBadge\s*\{([^}]*)\}", style._QSS.template)
    assert m, "the concept badge rule is gone"
    body = m.group(1)
    assert "$badge_radius" in body and "$badge_box" in body, (
        "the badge's box and radius must both come from style.badge_box -- a literal beside a token is "
        "how the circle silently becomes a squircle at the next scale"
    )
    # the rendered radius really is half the rendered widget box, at every scale
    for pct in prefs.TEXT_SCALES:
        css = style.qss(theme.DARK, "comfortable", pct)
        rule = re.search(r"QToolButton#conceptBadge\s*\{([^}]*)\}", css).group(1)
        radius = int(re.search(r"border-radius:\s*(\d+)px", rule).group(1))
        content = int(re.search(r"min-width:\s*(\d+)px", rule).group(1))
        assert radius * 2 == content + 2, (
            f"{pct}%: radius {radius} is not half the {content + 2}px widget box (QSS min-width sizes the "
            f"CONTENTS; the 1px border on each side makes the widget 2px wider)"
        )


def test_a_box_drawn_around_text_never_shrinks_below_its_shipped_size():
    """CALIBRE may only ever GROW a pin. 24 is also the WCAG 2.5.8 target floor.

    scale_px floors at the 100% value on purpose: a dial that shrank a box would clip at a setting that
    is provably fine today, and the whole point of the floor is that 100% is the one setting nobody has
    to re-audit.
    """
    for pct in prefs.TEXT_SCALES:
        assert style.scale_px(style.CONSOLE_H, pct) >= style.CONSOLE_H, f"{pct}% shrank the console pin"
    assert style.scale_px(style.CONSOLE_H, 100) == style.CONSOLE_H, "100% must be inert"
    # it must actually clear the text it wraps: audited, the label outgrows a frozen 24 at 125%
    assert style.scale_px(style.CONSOLE_H, 125) >= 26, "the console head clips its own label at 125%"


def test_the_text_scale_is_provably_inert_at_100_percent():
    """CALIBRE's central promise: turning the dial to its default changes NOTHING.

    Not "we believe it is inert" -- the default path and the explicit-100 path must render the same
    string, for every palette and both densities. int(px * 100/100 + 0.5) == px for every int, so this
    holds by construction; the fence exists so a future refactor of type_px cannot quietly break the one
    setting nobody re-audits.
    """
    for mode, pal in theme.THEMES.items():
        for dens in ("comfortable", "compact"):
            assert style.qss(pal, dens) == style.qss(pal, dens, 100), (mode, dens)
            assert "$" not in style.qss(pal, dens, 100), (mode, dens)


def test_every_shipped_text_scale_substitutes_cleanly():
    """A scale that leaves a placeholder is a black screen, not a big font."""
    for pct in prefs.TEXT_SCALES:
        for mode, pal in theme.THEMES.items():
            assert "$" not in style.qss(pal, "comfortable", pct), (mode, pct)
    assert "$" not in style.qss(theme.DARK, "comfortable", 137)   # an unknown scale must not raise either


def test_the_type_ramp_never_inverts_at_any_scale():
    """THE REASON QUARTO P3 EXISTS, fenced.

    Before the table, _SCALES owned 3 of the 8 sizes. A scale reaching only those would have raised the
    hint while the body stayed frozen -- the annotation outgrowing the thing it annotates. That is not
    hypothetical: it is exactly what CALIBRE would have shipped on the old code, and it is why P3 came
    first.

    Half-up rounding is what keeps this true. Python's banker's round() breaks ties toward even, and the
    table hits exact .5 ties (h3=15 at 110% is 16.5; body=14 at 125% is 17.5) -- so round() would shrink
    one rung and grow the next from the same tie, collapsing steps that must stay ordered.
    """
    for pct in list(prefs.TEXT_SCALES) + [105, 115, 137, 200]:
        body = style.type_px("type_body", pct)
        hint = style.type_px("type_caption", pct)
        name = style.type_px("type_name", pct)
        assert hint < body, f"{pct}%: the hint ({hint}) reached the body ({body}) -- the ramp inverted"
        assert body <= name, f"{pct}%: the body ({body}) outgrew the nameplate ({name})"
        assert style.type_px("type_head", pct) >= body, f"{pct}%: the head fell below the body"


def test_the_scale_is_monotonic_in_every_rung():
    """Turning the dial UP may never make any rung smaller. Half-up guarantees it; round() would not."""
    for k in style._TYPE:
        seen = [style.type_px(k, p) for p in sorted(prefs.TEXT_SCALES)]
        assert seen == sorted(seen), f"{k} is not monotonic across the dial: {seen}"


def test_the_ramp_has_no_dead_rungs():
    """QUARTO P2's fence, and the one that makes the whole ramp a SCALE rather than six accreted numbers.

    The shipped ramp was 26/16/15/13/12/11 -- six rungs and TWO real steps. Its ratios were 1.625 / 1.067 /
    1.154 / 1.083 / 1.091: three of five under 1.15, which Segoe cannot draw as a hierarchy. The worst was
    h2 vs h3 at 1.067 -- a 6.7% CAP-HEIGHT step (10.50 vs 11.20, measured natively) between two roles that
    turned out to be doing the same job at four top-level sites.

    1.15 IS A CHOSEN FENCE, NOT A MEASURED CONSTANT -- it is the rough floor below which a size step stops
    reading as a tier and starts reading as a rounding error. It is here to be argued with, deliberately:
    a future round may move it, but it may not drift under it by accident, which is how 15 and 16 came to
    coexist for three rounds.

    The reading ramp is caption -> body -> head -> name. type_mono is EXCLUDED (a register, not a rung: it
    is the body size in another face, and equal by design). type_glyph and type_badge are excluded and the
    table says why at their own entries -- a decorative icon and a glyph pinned inside a 22px circle.
    """
    rungs = ["type_caption", "type_body", "type_head", "type_name"]
    sizes = [style._TYPE[r] for r in rungs]
    assert sizes == sorted(sizes), f"the ramp is not monotonic: {dict(zip(rungs, sizes))}"
    for lo_name, hi_name in zip(rungs, rungs[1:]):
        lo, hi = style._TYPE[lo_name], style._TYPE[hi_name]
        step = hi / lo
        assert step >= 1.15, (
            f"{lo_name}({lo}) -> {hi_name}({hi}) is a {step:.3f} step -- under 1.15 it is not a tier the "
            f"font can draw, it is a rounding error with a name."
        )
    # ...and the register really is the body in another face, not a rung pretending to be one
    assert style._TYPE["type_mono"] <= style._TYPE["type_body"]


def test_the_head_is_one_rung_not_two():
    """h2 and h3 are MERGED, not aliased. An alias keeps two names for one thing and invites the split to
    grow back -- which is exactly how a "sub-h2 section title" came to describe a nesting that never
    existed at any of its four call sites.
    """
    import re
    css = style.qss(theme.DARK)
    assert "type_h2" not in style._TYPE and "type_h3" not in style._TYPE, "the old head tokens survive"
    for dead in ('role="h2"', 'role="h3"'):
        assert not re.search(re.escape(dead) + r"\]\s*[,{]", css), f"{dead} still has a rule in the sheet"
    head = re.search(r'QLabel\[role="head"\]\s*\{([^}]*)\}', css)
    assert head, "the head rule is gone"
    assert f"font-size: {style._TYPE['type_head']}px" in head.group(1)


def test_no_widget_carries_a_private_font_size_the_dial_cannot_reach():
    """The strays. QUARTO P3 put every size in one table; this stops new ones appearing beside it.

    Two shipped and both were invisible to the ramp:
      * a 15px step-number glyph, set by an INLINE widget stylesheet (one pixel over the body -- the same
        non-tier P2 just deleted between h2 and h3);
      * a 10px Inspector section header, set in INLINE HTML inside a rich-text QLabel -- the smallest text
        in the app, two pixels under the Windows default, and a full rung under role="overline", which is
        the same thing it is. No QSS role reaches HTML, so no fence or sweep could see it.
    Both now substitute a rung at the live scale, which fixes the ramp AND the dial in one move: an inline
    size cannot hear CALIBRE, so those two would have frozen while everything around them grew.

    THIS FENCE CAUGHT ITSELF FIRST, which is the point of writing it down. Its first cut walked every
    ast.Constant -- and a DOCSTRING is an ast.Constant, so it flagged `widgets.Prose._resolve_cap`'s own
    prose ("The stylesheet sets `font-size: 21px`, so this is 21") as a violation. A fence must read code,
    not prose, and a docstring is prose that happens to be stored as a string. Docstrings are stripped.

    KNOWN EXEMPTION, and it is a real limit rather than a dodge: forms_qt's rich-text DOCUMENT bodies (the
    Info Hub catalog card, the concept card, the wrap preview). Those are QTextEdit documents, not chrome
    -- HTML the app authors and hands to a text engine, where no QSS role reaches. They ship 13/14/15px,
    which means the Info Hub renders at the OLD body size and cannot hear the dial either. That is real
    and it is NOT this round: forms_qt has no access to the scale, so fixing it means threading one
    through or reading prefs at build time, and it wants its own decision. Named here so it is a deferred
    defect rather than a silent one.
    """
    import ast
    import pathlib
    import re
    ws = pathlib.Path(style.__file__).parent
    DOC_BODIES = {"forms_qt.py"}          # see the exemption above -- rich text, not chrome
    bad = []
    for py in sorted(ws.glob("*.py")):
        if py.name in ("style.py", "hero.py") or py.name in DOC_BODIES:
            continue                     # style.py IS the table; hero.py is fenced by test_workspace_hero
        tree = ast.parse(py.read_text(encoding="utf-8"))
        docs = set()
        for n in ast.walk(tree):
            if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                d = n.body[0] if n.body else None
                if isinstance(d, ast.Expr) and isinstance(d.value, ast.Constant):
                    docs.add(id(d.value))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if id(node) in docs:
                continue                 # a docstring is prose, not code
            for m in re.finditer(r"font-size:\s*(\d+)px", node.value):
                bad.append(f"{py.name}:{node.lineno} font-size:{m.group(1)}px")
    assert not bad, (
        "these hard-code a font size in a literal, so they sit outside the ramp AND cannot hear the "
        f"text-size dial -- substitute type_px(rung, scale): {bad}"
    )


def test_the_sheet_never_reads_the_developers_own_accessibility_slider():
    """HEED's one way to poison the suite, fenced.

    Round 5's audit named this exactly: "a registry-seeded default makes those tests pass or fail
    depending on the developer's own accessibility slider". Every px fence in this file asserts a rendered
    number, so if `qss()` ever reached for `prefs.text_scale()` instead of taking a parameter, this whole
    file would become a report on whoever ran it.

    The seam is already right and this keeps it right: `scale` is an EXPLICIT parameter defaulting to 100,
    injected only by the app at startup. The sheet is a pure function of (palette, density, scale).
    """
    import ast
    import inspect
    src = inspect.getsource(style)
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            assert not (node.value.id == "prefs" and "text_scale" in node.attr), (
                "style.py reached for prefs.text_scale() -- the sheet must take `scale` as a parameter, or "
                "every px assertion in this file starts depending on the developer's Windows settings"
            )
    assert "prefs" not in {n.name.split(".")[0] for n in ast.walk(tree)
                           if isinstance(n, ast.alias)}, "style.py imported prefs"
    # the default is the inert setting, and it is a real default rather than a sentinel
    import inspect as _i
    sig = _i.signature(style.qss)
    assert sig.parameters["scale"].default == 100
    assert style.qss(theme.DARK) == style.qss(theme.DARK, "comfortable", 100)
