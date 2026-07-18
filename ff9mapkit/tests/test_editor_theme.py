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
    # the picker order must offer "auto" plus exactly the THEMES keys (no orphan choice, none missing);
    # "mist" leads the list -- it's the default (prefs.theme()).
    choice_modes = [m for m, _label in theme.THEME_CHOICES]
    assert choice_modes[0] == "mist"
    assert set(choice_modes[1:]) | {"mist"} == set(theme.THEMES) | {"auto"}
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
        # EVERY ground a text tier can land on -- and "every" has had to be widened THREE times now, each
        # time by a real sub-AA defect found in shipped pixels:
        #   surface_2 (the card fill)   -- 4 palettes shipped sub-AA muted on it
        #   surface_3 (the rail segment) -- dracula 3.86 / dark 4.13, while this test was green
        #   surface_btn (a BUTTON, and an UNSELECTED TAB LABEL) -- solarized-light shipped muted at 4.37
        # Each widening was written next to the sentence "a fence that covers 3 of 4 grounds just moves
        # the bug to the 4th", and then the bug moved to the ground the list still missed. So the list is
        # now every FILL the sheet paints text on, and adding a fill to the palette means adding it here.
        for _g in ("surface_2", "surface_3", "surface_btn", "field"):
            assert _contrast(pal["text"], d[_g]) >= 4.5, f"{mode}: body text on {_g}"
            assert _contrast(pal["muted"], d[_g]) >= 4.5, f"{mode}: hint text on {_g}"
        # The console is its OWN pair and was fenced against nothing: solarized-light shipped log_fg at
        # 3.97 on log_bg -- the body text of the surface you watch during every build.
        assert _contrast(pal["log_fg"], pal["log_bg"]) >= 4.5, f"{mode}: console body text on its own well"
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
        # ...AND IN ALL THREE OF ITS STATES. This fenced `accent` ALONE, so the :hover and :pressed rules
        # -- which swap the FILL under the SAME ink -- were never checked: 3.48 (nord hover) and 3.56
        # (solarized-dark pressed). The app's primary verb, sub-AA the moment you touched it, with this
        # line green. THE FILLS come to the ink (derive()._accent_states), because measured, ONE ink for
        # all three is impossible (black and white BOUND every ink and both fail in 4 of 8) and a
        # per-state ink FLIPS 219-243/255 between rest and pressed. Same shape as the 3.0-vs-4.5 story
        # this file is full of: a fence that names one ground moves the bug to the ones it did not name.
        for _st in ("accent", "accent_hover", "accent_pressed"):
            assert _contrast(pal["accent_fg"], d[_st]) >= 4.5,                 f"{mode}: the accent BUTTON LABEL is text, and it is still text on :{_st}"
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


def test_a_filled_ground_carries_its_ink():
    """The MIRROR of the `*_text` rung above. `*_text` is a hue moved until it reads AS text ON a surface;
    `*_fg` is the ink that reads ON the hue, when the hue is the ground.

    WHAT SHIPPED WITHOUT THIS FENCE. The breadcrumb chip took a fill from its caller and hardcoded
    `color:#ffffff` -- so the accent chip was sub-AA in 5 of 8 palettes and the BATTLE chip (a `$warn`
    fill) in 7 of 8, bottoming out at **1.12:1** on dracula: white on pale yellow, 12px/600, on screen, on
    every tab. Nothing could catch it, because the ink was a literal and the fill was an argument -- there
    were never two tokens to compare.

    THE BAR IS 4.5. A chip is 12px/600 and the help glyph 14px/bold; weight does not buy the large-text
    bar (18.66px bold does). Both are normal text.

    `accent_fg` IS AUTHORED, NOT DERIVED, and this fence covers it anyway -- that is the point. It is
    hand-picked per palette and a formula reproduces only 5 of its 8 values, choosing MORE contrast than
    the author wanted in the other 3 (dracula's `#282a36` and gruvbox's `#282828` are those projects'
    signature backgrounds, not compromises). So the ink's ORIGIN differs per ground -- authored where
    someone chose, derived where nobody did -- and the CONTRACT does not: whatever ink rides a fill, it
    clears AA on it. See `_fg_token` and studies/gui-aesthetics/evidence/probe_fg_rule.py.
    """
    # (fill, ink) -- every FILL in the app that carries text, censused by reading each `background:{...}`
    # in an inline setStyleSheet under workspace/. `$success`/`$error` are never fills, so they are absent:
    # a token with no call site is the `info` mistake (derived "for now", zero consumers to this day).
    for mode, pal in theme.THEMES.items():
        d = theme.derive(pal)
        for fill, ink in (("accent", "accent_fg"),      # the chip (7 of 8 modes) + QPushButton#accent
                          ("warn", "warn_fg"),          # the BATTLE chip -- the 1.12:1 site
                          ("help", "help_fg"),          # the round "?" concept button
                          # `pressed` is a fill too -- the one nobody saw, because it is TRANSIENT: every
                          # button in the app renders its label on it WHILE HELD. `text` measured 4.09 on
                          # solarized-light and 4.47 on solarized-dark, in the GENERIC rule, so it was
                          # every button in those two palettes. The ground could not move: `pressed` is a
                          # tonal-ladder rung fenced at contrast(pressed, hover) >= 1.03, and in BOTH
                          # failing palettes the ladder walks the OPPOSITE way to legibility -- clearing
                          # 4.5 by retuning the fill drops solarized-light's press feedback to 1.0192,
                          # i.e. fixes the label by making the press invisible. So the ink moved instead.
                          ("pressed", "pressed_fg")):
            assert _contrast(d[ink], d[fill]) >= 4.5, \
                f"{mode}: ${ink} is sub-AA on its own ${fill} fill"


def test_an_ink_is_never_borrowed_from_the_ground_next_door():
    """Each fill gets ITS OWN ink. The round help button wore `accent_fg` on a `$help` fill -- two hexes
    nothing had ever asserted were compatible, because `accent_fg` is fenced against `$accent` alone. It
    measured 2.51:1 on nord.

    This asserts the ACTUAL defect (a mismatch is sub-AA somewhere) rather than the mechanism, so it stays
    true if the tokens are ever re-homed. It is the reason the pairing above is a table and not a habit:
    a token that happens to work on the ground next door is a coincidence, and a coincidence is not fenced.
    """
    borrowed = [("help", "accent_fg"), ("warn", "accent_fg"), ("accent", "warn_fg")]
    for fill, ink in borrowed:
        worst = min(_contrast(theme.derive(p)[ink], theme.derive(p)[fill]) for p in theme.THEMES.values())
        assert worst < 4.5, (
            f"${ink} now happens to clear AA on ${fill} in all 8 palettes. That is luck, not design -- "
            f"re-check whether these grounds still need separate inks before deleting this fence.")


def test_the_narrowed_accent_ladder_still_gives_feedback():
    """Pulling the state fills into the ink's band must not make the primary button DEAD.

    The trade is real and it is the whole risk of narrowing: a fill dragged toward `accent` for legibility
    stops reading as a state. So the floors are the app's OWN shipped minimums, measured across all 8
    BEFORE anything moved -- hover/accent 1.0560 (solarized-light), press/accent 1.0670 (nord), press/hover
    1.1821 (light). A narrowed ladder can never be quieter than the quietest one that already shipped.

    THREE PALETTES CHANGE THE DIRECTION OF A STEP and that is FORCED, not chosen: `dark`'s band below the
    accent is 0.054 wide, and holding both steps darker while keeping press/hover >= 1.1821 is provably
    infeasible there. Where a direction has to go, the search takes the cheapest legal ladder in channel
    distance from what shipped.
    """
    lo_h, lo_p, lo_ph = theme._ACCENT_FEEDBACK
    for mode, pal in theme.THEMES.items():
        d = theme.derive(pal)
        a, h, p = d["accent"], d["accent_hover"], d["accent_pressed"]
        assert _contrast(h, a) >= lo_h, f"{mode}: the accent button's HOVER is invisible ({_contrast(h, a):.4f})"
        assert _contrast(p, a) >= lo_p, f"{mode}: the accent button's PRESS is invisible ({_contrast(p, a):.4f})"
        assert _contrast(p, h) >= lo_ph,             f"{mode}: pressing adds nothing over hovering ({_contrast(p, h):.4f}) -- the states collapsed"
        # in-family: a narrowed step is still the palette's own hue, never a new one
        def _order(x):
            x = x.lstrip("#")
            v = [int(x[i:i + 2], 16) for i in (0, 2, 4)]
            return [i for i, _ in sorted(enumerate(v), key=lambda t: -t[1])]
        for name, val in (("hover", h), ("pressed", p)):
            assert _order(val) == _order(a), f"{mode}: accent_{name} left the accent's hue family"


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


def test_the_selection_rail_clears_the_fill_it_sits_on():
    """A 3:1 mark must clear the thing it is drawn ON -- and the rail sits on the TINTED fill, not the
    plain surface.

    `selection_rail` is `_focus_token` pointed at `selection_bg` rather than `surface`. Zero new math;
    the ground is the fix. Measured: as the raw accent the rail would be 2.13 in nord and 2.87 in
    solarized-dark -- both under the 3.0 non-text floor. Lifted, they land 3.19 and 3.13, and the other
    six clear already and return the accent unchanged.
    """
    for mode, pal in theme.THEMES.items():
        d = theme.derive(dict(pal))
        got = _contrast(d["selection_rail"], d["selection_bg"])
        assert got >= 3.0, f"{mode}: the selected row's rail is {got:.2f} on its own fill -- invisible"


def test_selected_text_is_legible_on_the_tinted_fill():
    """The row's LABEL now sits on `selection_bg` instead of the accent, so it is $text -- and $text must
    clear AA on a ground that only started rendering with this change.

    `selection_bg` shipped as a derived token with ZERO rules since Phase 1. This is the first time any
    pixel has been painted with it, which means it is a NEW GROUND -- exactly the class of thing this
    study keeps discovering after the fact (the hero's bloom, surface_btn, log_bg). Fence it on arrival.
    """
    for mode, pal in theme.THEMES.items():
        d = theme.derive(dict(pal))
        got = _contrast(d["text"], d["selection_bg"])
        assert got >= 4.5, f"{mode}: a selected row's label is {got:.2f} on the tinted fill"


def test_the_selection_cannot_be_confused_with_hover():
    """A selected row is never confused with the PAGE. It is confused with the row under your cursor.

    So `selection_bg` solves against `hover`, not `surface` -- and it measures a raw channel distance,
    not a contrast ratio, because a ratio is the wrong instrument for this and the render proved it:
    by contrast, hover BEATS the old fixed-16% selection in four palettes, yet rendered at 4x gruvbox's
    selection wins decisively. Contrast is luminance-only; hover is a pure lightness step (dHue <=2.5deg,
    dSat ~0) while a selection is a hue/chroma event (dSat up to +0.42). The ratio cannot see the axis
    doing the work.

    The floor is CALIBRATED to those renders: gruvbox reads decisively at 26, nord read marginally at 11.
    """
    for mode, pal in theme.THEMES.items():
        d = theme.derive(dict(pal))
        got = max(abs(a - b) for a, b in zip(_chan(d["selection_bg"]), _chan(d["hover"])))
        assert got >= 20, (
            f"{mode}: the selected row is only {got}/255 from its own HOVER -- the cursor and the "
            f"selection look the same. Contrast will not catch this; it is blind to chroma."
        )


def test_every_log_register_is_legible_on_the_well():
    """The console's four registers all land on `log_bg` -- a ground that was fenced against NOTHING
    until solarized-light shipped its own body text at 3.97 there.

    `text` (the job header), `log_fg` (the command echo and the body) and `error_text` (a traceback) are
    each authored or derived against OTHER grounds entirely, so none of them was ever checked here.
    Worst across all 8 and all three inks: 4.99 (solarized-light).
    """
    for mode, pal in theme.THEMES.items():
        d = theme.derive(dict(pal))
        for ink in ("text", "log_fg", "error_text"):
            got = _contrast(d[ink], d["log_bg"])
            assert got >= 4.5, f"{mode}: the log's {ink} register is {got:.2f} on the well"


def test_the_log_registers_cannot_be_a_tonal_ladder():
    """WHY the log's register is WEIGHT and not a third grey -- fenced, because the reason is invisible.

    `text`, `log_fg` and `muted` were each authored per-palette from their own scheme's canon with no
    relationship to one another. They are not a ladder, and this asserts the specific counter-examples so
    that nobody "simplifies" the weight register into a tonal one:

      dracula          -- text and log_fg are BYTE-IDENTICAL (#f8f8f2): a tonal head tier is invisible
      solarized-*      -- the order INVERTS (muted is brighter than log_fg)

    Weight costs zero contrast headroom, which is why it survives in the palettes that have none.
    """
    d = theme.derive(dict(theme.DRACULA))
    assert d["text"] == d["log_fg"], (
        "dracula's text and log_fg used to be identical -- if that changed, re-check whether the log's "
        "register could now be tonal. It is currently weight BECAUSE of this."
    )
    for mode in ("solarized-dark", "solarized-light"):
        d = theme.derive(dict(theme.THEMES[mode]))
        ordered = (_luminance(d["text"]) > _luminance(d["log_fg"]) > _luminance(d["muted"])
                   if d["dark"] else
                   _luminance(d["text"]) < _luminance(d["log_fg"]) < _luminance(d["muted"]))
        assert not ordered, f"{mode}: the tiers now form a ladder -- the weight register may be revisitable"
