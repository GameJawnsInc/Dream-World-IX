"""The tk-FREE half of editor/theme.py: palette tables, the palette picker, and the OS dark-mode
probe. No display, no tkinter (like the other editor headless tests). The Tk styling in
``apply_theme`` is verified by the human in the running editor (can't drive a UI offline)."""

from __future__ import annotations

import re

from ff9mapkit.editor import theme

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
# every palette colour the app reads by name (app.py + theme.apply_theme) -- guards against drift.
_USED = {"bg", "surface", "surface_btn", "field", "text", "muted", "accent", "accent_fg",
         "accent_hover", "accent_pressed", "border", "success", "hover", "pressed", "scroll",
         "log_bg", "log_fg", "error", "warn"}


def test_palettes_share_one_key_set():
    keys = set(theme.LIGHT)
    for mode, pal in theme.THEMES.items():           # every selectable palette, not just LIGHT/DARK
        assert set(pal) == keys, f"{mode} has a different key set"


def test_palettes_have_every_key_the_app_uses():
    for pal in theme.THEMES.values():
        assert _USED <= set(pal)


def test_colours_are_hex_and_modes_flagged():
    for mode, pal in theme.THEMES.items():
        assert isinstance(pal["dark"], bool), mode
        for key, val in pal.items():
            if key == "dark":
                continue
            assert _HEX.match(val), f"{mode}.{key}={val!r} is not #rrggbb"
    assert theme.LIGHT["dark"] is False and theme.DARK["dark"] is True
    assert theme.LIGHT["text"] != theme.DARK["text"]     # the two schemes actually differ


def test_theme_choices_cover_every_palette():
    # the picker order must offer "auto" plus exactly the THEMES keys (no orphan choice, none missing).
    choice_modes = [m for m, _label in theme.THEME_CHOICES]
    assert choice_modes[0] == "auto"
    assert set(choice_modes[1:]) == set(theme.THEMES)
    assert len({m for m, _ in theme.THEME_CHOICES}) == len(theme.THEME_CHOICES)   # no dup
    assert all(label for _m, label in theme.THEME_CHOICES)                        # every choice is labelled


def test_pick_palette_explicit():
    assert theme.pick_palette("light") is theme.LIGHT
    assert theme.pick_palette("dark") is theme.DARK
    for mode, pal in theme.THEMES.items():
        assert theme.pick_palette(mode) is pal


def test_pick_palette_auto_returns_a_known_palette():
    assert theme.pick_palette("auto") in (theme.LIGHT, theme.DARK)
    assert theme.pick_palette() in (theme.LIGHT, theme.DARK)       # default mode is auto


def test_pick_palette_unknown_mode_falls_back_to_auto():
    # a stale/garbage saved preference must never crash -> resolve to the OS default (light or dark)
    assert theme.pick_palette("no-such-theme") in (theme.LIGHT, theme.DARK)
    assert theme.pick_palette("") in (theme.LIGHT, theme.DARK)
    assert theme.pick_palette(None) in (theme.LIGHT, theme.DARK)


def test_pick_palette_auto_follows_os_dark(monkeypatch):
    # pin the OS probe so BOTH arms (the DARK one never runs on a light-mode CI box) are exercised; the
    # unknown-mode fallback shares the same resolution, so check it too.
    monkeypatch.setattr(theme, "detect_os_dark", lambda: True)
    assert theme.pick_palette("auto") is theme.DARK
    assert theme.pick_palette("no-such") is theme.DARK
    monkeypatch.setattr(theme, "detect_os_dark", lambda: False)
    assert theme.pick_palette("auto") is theme.LIGHT
    assert theme.pick_palette("no-such") is theme.LIGHT


# --- contrast / legibility invariants (tk-free WCAG relative-luminance) -------------------
def _luminance(hexstr: str) -> float:
    r, g, b = (int(hexstr[i:i + 2], 16) / 255 for i in (1, 3, 5))

    def _lin(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def _contrast(a: str, b: str) -> float:
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def test_palette_contrast_invariants():
    # Phase-1 WCAG AA floors (raised from 4.0/2.7): body text AND hint text must clear 4.5:1 on BOTH the
    # page (bg) and a panel (surface); text on the accent button >= 3.0; the DERIVED focus ring >= 3.0 on
    # the surface (a perceivable focus indicator). Fires on any real regression to legibility.
    for mode, pal in theme.THEMES.items():
        d = theme.derive(pal)
        assert _contrast(pal["text"], pal["bg"]) >= 4.5, f"{mode}: body text on bg"
        assert _contrast(pal["text"], pal["surface"]) >= 4.5, f"{mode}: body text on surface"
        assert _contrast(pal["muted"], pal["bg"]) >= 4.5, f"{mode}: hint text on bg"
        assert _contrast(pal["muted"], pal["surface"]) >= 4.5, f"{mode}: hint text on surface"
        # ...and on an ELEVATED panel (surface_2 -- what every QGroupBox is). This rung was UNTESTED, and
        # four palettes shipped sub-AA on it for real: muted measured 3.87 nord / 3.91 dracula / 3.91
        # solarized-dark / 4.07 gruvbox-dark, and solarized-dark's BODY text 4.22. Every hint inside a
        # groupbox lands here, so it is not a hypothetical surface.
        # EVERY ground a text tier can land on, not just the page. Each rung of the elevation ladder is a
        # real surface under real text -- surface_2 is the card fill, surface_3 is the RAIL SEGMENT -- and
        # the fence stopped one rung short: muted on surface_3 measured 3.86 (dracula) / 4.13 (dark) while
        # this test was green. A fence that covers 3 of 4 grounds just moves the bug to the 4th.
        for _g in ("surface_2", "surface_3"):
            assert _contrast(pal["text"], d[_g]) >= 4.5, f"{mode}: body text on {_g}"
            assert _contrast(pal["muted"], d[_g]) >= 4.5, f"{mode}: hint text on {_g}"
        # `help` is TEXT: it labels the Info Hub button (its one and only use, as the label AND the
        # border). It was fenced against NOTHING and measured 2.97 on solarized-dark.
        assert _contrast(pal["help"], pal["bg"]) >= 4.5, f"{mode}: help text on bg"
        assert _contrast(pal["help"], pal["surface"]) >= 4.5, f"{mode}: help text on surface"
        # muted is the DIMMER tier by definition -- a contrast lift must never invert it past text (a naive
        # solve for the floors above did exactly that on solarized-dark: muted 0.3740 vs text 0.3720).
        assert (_luminance(pal["muted"]) < _luminance(pal["text"])) is bool(pal["dark"]), \
            f"{mode}: muted must stay dimmer than text"
        # 4.5, NOT 3.0. This fence shipped at the LARGE-text floor, but the thing it governs is a 13px
        # BUTTON LABEL ("Deploy F9", "Fork a field", "Run setup..."), which is normal text under WCAG AA.
        # At 3.0 it passed while dark measured 3.20, solarized 3.68 and nord 4.03 -- the app's primary
        # action, unreadable-by-standard, in 4 of 8 palettes, with a green fence. The floor was the bug.
        assert _contrast(pal["accent_fg"], pal["accent"]) >= 4.5, f"{mode}: the accent BUTTON LABEL is text"
        assert _contrast(d["focus"], pal["surface"]) >= 3.0, f"{mode}: focus ring on surface"
        assert (_luminance(pal["bg"]) < 0.5) is pal["dark"], f"{mode}: dark flag disagrees with bg luminance"


def test_status_hues_are_legible_as_text_via_the_derived_rung():
    """A status hue has TWO jobs at TWO different WCAG floors, and one token cannot serve both.

    As a SHAPE (an alert icon, the banner stripe) the bar is 3.0 -- WCAG 1.4.11, non-text. That is what
    `success`/`warn`/`error` are tuned for and `test_status_hues_meet_non_text_contrast` fences.
    As TEXT ("netsync MISSING", "overwrites, no undo") the bar is 4.5 -- and measured on the card fill the
    raw hues gave error 2.67 (nord) / 2.69 (solarized-dark) / 3.29 (gruvbox), warn 3.51, success 3.52.

    Lifting the hues themselves was measured and REJECTED: reaching 4.5 needs +38% toward white on nord's
    aurora red and solarized-dark's, +30% on gruvbox's -- it washes out the signature colour those palettes
    are known for, to fix text that is rare.

    So derive() adds a `*_text` rung per hue -- exactly the trick `focus` has always used to stay legible
    without dragging the accent with it. Base palettes untouched, no new palette KEY taxed.
    """
    for mode, pal in theme.THEMES.items():
        d = theme.derive(pal)
        for hue in ("success", "warn", "error"):
            t = d[f"{hue}_text"]
            assert _contrast(t, d["surface_2"]) >= 4.5, f"{mode}: {hue}_text is sub-AA on a card"
            assert _contrast(t, pal["surface"]) >= 4.5, f"{mode}: {hue}_text is sub-AA on a panel"
            assert _contrast(t, pal["bg"]) >= 4.5, f"{mode}: {hue}_text is sub-AA on the page"
            # the derived rung must stay in the hue's FAMILY -- it is the same status, read louder, not a
            # different colour. (Same channel ordering = same hue; only lightness may move.)
            def _order(h):
                h = h.lstrip("#")
                v = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
                return [i for i, _ in sorted(enumerate(v), key=lambda x: -x[1])]
            assert _order(t) == _order(pal[hue]), f"{mode}: {hue}_text drifted out of the hue's family"


def test_hover_and_pressed_give_real_feedback():
    """A button must visibly react to the pointer -- and `hover` shipped BYTE-IDENTICAL to `surface_btn`
    in nord (#3b4252), dracula (#3a3d4d), solarized-dark (#0b4350) and gruvbox-dark (#3c3836), so four of
    seven palettes had **no button hover feedback at all**. Nothing in the QSS could have saved them: the
    rule `QPushButton:hover { background: $hover; }` was firing correctly and painting the same colour.

    Three assertions, because each catches a different way of getting this wrong:
      1. DIRECTION -- hover moves toward the light in a dark theme, toward the ink in a light one. This is
         the one that catches the byte-identical bug (equal luminance is not `>`, so a dark palette fails).
      2. MAGNITUDE -- a 1-bit difference would satisfy (1) and still be invisible. DARK ships 1.0756.
      3. hover != pressed -- otherwise pressing adds no feedback beyond hovering. This is why the fix had
         to shift BOTH rungs (nord: nord1 rest -> nord2 hover -> nord3 press) rather than just move hover
         onto the old pressed value.

    NB `$hover` serves two resting surfaces -- buttons rest on `surface_btn`, tree/list rows on `surface`
    -- so a value that fixes the button must not flatten the row. Asserted below.
    """
    for mode, pal in theme.THEMES.items():
        toward_light = _luminance(pal["hover"]) > _luminance(pal["surface_btn"])
        assert toward_light is bool(pal["dark"]), \
            f"{mode}: hover must move toward the light in dark themes, toward the ink in light ones " \
            f"(hover {pal['hover']} vs surface_btn {pal['surface_btn']})"
        assert _contrast(pal["hover"], pal["surface_btn"]) >= 1.05, f"{mode}: button hover is invisible"
        assert _contrast(pal["pressed"], pal["hover"]) >= 1.03, f"{mode}: pressed adds nothing over hover"
        assert _contrast(pal["hover"], pal["surface"]) >= 1.05, f"{mode}: tree/list row hover is invisible"


def test_status_hues_meet_non_text_contrast():
    # WCAG 1.4.11: error / warn / success drive status ICONS + the lint stripe, so each must clear the 3:1
    # non-text floor on BOTH the page (bg) and a panel (surface) -- the status stays perceivable as a shape
    # in greyscale. (Text is NEVER coloured the status hue, so the 4.5 text floor doesn't apply here.)
    for mode, pal in theme.THEMES.items():
        for hue in ("error", "warn", "success"):
            assert _contrast(pal[hue], pal["bg"]) >= 3.0, f"{mode}: {hue} on bg = {_contrast(pal[hue], pal['bg']):.2f}"
            assert _contrast(pal[hue], pal["surface"]) >= 3.0, \
                f"{mode}: {hue} on surface = {_contrast(pal[hue], pal['surface']):.2f}"


def test_derive_extends_the_palette_all_hex_and_idempotent():
    for mode, pal in theme.THEMES.items():
        d = theme.derive(pal)
        assert set(d) == set(pal) | set(theme._DERIVED_KEYS), f"{mode}: derive() key set"
        for k in theme._DERIVED_KEYS:
            assert _HEX.match(d[k]), f"{mode}.{k}={d[k]!r} is not #rrggbb"      # no rgba -> hex/parity hold
        assert all(d[k] == pal[k] for k in pal), f"{mode}: derive() changed a base value"
        assert theme.derive(d) is d, f"{mode}: derive() is not idempotent"      # already-derived passes through


def test_derived_elevation_ladder_is_monotonic():
    for mode, pal in theme.THEMES.items():
        d = theme.derive(pal)
        l1, l2, l3 = _luminance(pal["surface"]), _luminance(d["surface_2"]), _luminance(d["surface_3"])
        assert l1 <= l2 + 1e-9 <= l3 + 1e-9, f"{mode}: elevation not lighter-is-higher ({l1:.3f}/{l2:.3f}/{l3:.3f})"


def test_detect_os_dark_is_a_safe_bool():
    assert isinstance(theme.detect_os_dark(), bool)              # never raises, always a bool


def _chan(hexstr: str):
    return tuple(int(hexstr[i:i + 2], 16) for i in (1, 3, 5))


def _delta(a: str, b: str) -> int:
    """The largest per-channel step between two colours -- how far an edge moved from its anchor."""
    return max(abs(x - y) for x, y in zip(_chan(a), _chan(b)))


def test_the_edge_tokens_carry_in_every_palette():
    """INTAGLIO's carrier must be real in all 8, and that is why it anchors on $border and not the fill.

    The app's elevation ladder claims a light source ("higher = lighter") and never draws the light, so a
    fill cannot say "this is an object": LIGHT's surface_btn IS surface (1.0000, the same hex),
    solarized-dark's field IS surface, mist's button-in-a-card is 1.0017, nord/gruvbox 1.024/1.025.

    Fill-anchored, LIGHT gets d5 on a card -- a no-op in the two palettes that need it most, because
    light's surface_3 is #ffffff and its rungs step 1.043/1.046. Border-anchored the carrier lands
    d26-d34 in every palette, no exceptions. That is the whole design, so fence the carrier.

    The floor is d20, and it is not arbitrary: the FILL differences this edge replaces measure d0-d8
    across the app (d0 in LIGHT, where surface_btn and surface are the same hex). d20 is the point where
    the edge is unambiguously doing work the fill cannot. Measured today: border d26-d34, accent d24-d36.
    """
    for mode, pal in theme.THEMES.items():
        d = theme.derive(dict(pal))
        for src, lit, shade in (("border", "border_lit", "border_shade"),
                                ("accent", "accent_lit", "accent_shade")):
            carrier = max(_delta(d[src], d[lit]), _delta(d[src], d[shade]))
            assert carrier >= 20, (
                f"{mode}: {src}'s edge carrier is only d{carrier} -- the fills it replaces are d0-d8, so "
                f"below ~d20 it stops being worth its own existence"
            )


def test_the_border_edge_never_becomes_a_bevel():
    """THE TASTE CALL, FENCED. A raised object gets ONE readable edge; two is a bevel, and a bevel is
    Windows 95.

    The border pair is emitted on EVERY object in the app, so its quiet edge is the whole risk -- and it
    is exactly what a future nudge to EDGE_T would break silently:

        t=0.18 -> quiet edge d8-d17: FIVE palettes (nord 17, mist 17, dracula 16, sol-dark 16,
                  gruvbox 14) grow a second, visible edge. Rendered at 6x, they read bevelled.
        t=0.14 -> quiet edge d6-d13 in all 8. One edge carries everywhere. SHIPPED.

    No contrast ratio distinguishes "lit" from "Win95" -- that judgement was made by rendering at 6x and
    looking (evidence/shot_intaglio_zoom.py). This fence is how it survives the next person who moves the
    number without looking.
    """
    for mode, pal in theme.THEMES.items():
        d = theme.derive(dict(pal))
        quiet = min(_delta(d["border"], d["border_lit"]), _delta(d["border"], d["border_shade"]))
        assert quiet <= 13, (
            f"{mode}: the border's quiet edge is d{quiet} -- both edges now read, on every object in the "
            f"app. Lower theme.EDGE_T (currently {theme.EDGE_T}) and re-render at 6x before believing it."
        )


def test_a_saturated_hue_has_no_quiet_edge_so_the_accent_emits_only_one():
    """The border pair's trick does NOT transfer to $accent, and this is why the accent rule differs.

    $border is a desaturated grey: mixing toward white and toward black moves it by different amounts, so
    one edge carries and the other is quiet enough for the palette to eat. $accent is SATURATED and has
    no quiet edge -- dark's #4c8dff has B=255, so mixing toward black drops B by 36 while mixing toward
    white cannot move it at all. Measured carrier/quiet: light 33/29, dark 36/25, nord 24/22, gruvbox
    36/32. BOTH edges always read.

    So the accent emits a lit top ONLY. Emitting the pair would put a symmetric bevel on the largest,
    loudest object on the screen -- the one place Win95 would actually show. THE RULE, in one line:
    emit both edges only where one of them is quiet; emit one where neither is.

    This test asserts the PREMISE (accent has no quiet edge). test_workspace_style asserts the
    CONSEQUENCE (the rule emits one edge). If a future palette ever gives accent a quiet edge, this fails
    and the accent rule may be reconsidered -- deliberately, not by accident.
    """
    for mode, pal in theme.THEMES.items():
        d = theme.derive(dict(pal))
        quiet = min(_delta(d["accent"], d["accent_lit"]), _delta(d["accent"], d["accent_shade"]))
        assert quiet > 13, (
            f"{mode}: accent's quiet edge is only d{quiet} -- it now behaves like $border. The accent's "
            f"one-edge rule was justified by the opposite; re-derive the decision, do not just relax this."
        )


def test_the_border_is_mode_aware_so_the_edges_need_no_branch():
    """THE INVARIANT THE WHOLE DIRECTION RESTS ON -- fenced because it holds only by convention.

    $border sits ABOVE its fill in all 6 dark palettes and BELOW it in both light ones. That is what lets
    every edge rule emit BOTH edges with no `if dark:` anywhere: each palette's own border eats the edge
    it cannot hold (light's lit edge lands at d8 and vanishes; dark's foot stays quiet).

    Nothing enforces this. It is a property of eight hand-picked hexes, and a ninth palette that broke it
    would silently light every object UPSIDE DOWN rather than fail -- so its author needs a failing test
    at the moment they get it wrong, not a comment they will never read.
    """
    for mode, pal in theme.THEMES.items():
        d = theme.derive(dict(pal))
        above = _luminance(d["border"]) > _luminance(d["surface_btn"])
        assert above == bool(pal.get("dark")), (
            f"{mode}: border sits {'above' if above else 'below'} its fill but dark={bool(pal.get('dark'))}"
            f" -- the no-branch edge rules assume the opposite and would light every object upside down"
        )


def test_a_restated_border_shorthand_never_flattens_a_lit_object():
    """The QSS `border:` shorthand RESETS every per-side colour, so any rule restating it on a lit object
    must restate its edge too -- or the object goes flat exactly when it matters.

    Probed: #accent lost its lit top this way (its own `border: 1px solid $accent` reset the generic
    QPushButton's per-side colours), and an input would have flattened on :focus -- the moment you are
    looking straight at it. Both are invisible to a reviewer reading the diff, because the rule that
    breaks them is correct on its own line. Only the ORDER is wrong, and order is not local.

    AT LEAST ONE edge, not both: the accent deliberately emits only a lit top (it is saturated and has no
    quiet edge -- see test_a_saturated_hue_has_no_quiet_edge_so_the_accent_emits_only_one). This fence is
    about not LOSING the edge to a shorthand, which is a different question from how many edges are right.
    """
    from ff9mapkit.workspace import style

    css = style.qss(theme.DARK)
    for sel in ("QPushButton#accent", "QPushButton#accent:pressed", "QLineEdit:focus",
                "QPushButton#search", "QComboBox:focus, QAbstractSpinBox:focus"):
        m = re.search(re.escape(sel) + r"\s*\{([^}]*)\}", css)
        assert m, f"{sel} not found -- did the selector move?"
        body = m.group(1)
        if "border:" in body:
            assert "border-top-color" in body or "border-bottom-color" in body, (
                f"{sel} restates `border:` (which resets per-side colour) without restating any edge "
                f"-- it renders flat"
            )
