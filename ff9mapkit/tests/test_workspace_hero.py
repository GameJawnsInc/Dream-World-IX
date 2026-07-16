"""The SIGNET hero band (workspace/hero.py) -- Home's front door.

Qt-real tests: the band is entirely PAINTED, so nothing here can be asserted from the QSS string. Each
test below guards a trap that was hit or nearly hit while building it (studies/gui-aesthetics/IDENTITY.md).

NB these run on the NATIVE platform where available. QT_QPA_PLATFORM=offscreen stubs the Qt font database
and inflates text advances ~1.8x, so any width/geometry assertion taken offscreen is fiction -- the same
trap that made an earlier round invent a horizontal-scroll emergency that never existed. The geometry test
therefore skips unless a real font DB is present.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt                                            # noqa: E402
from PySide6.QtGui import QFontDatabase                                  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget                      # noqa: E402

from ff9mapkit.editor import theme                                       # noqa: E402
from ff9mapkit.workspace import hero as hero_mod                         # noqa: E402
from ff9mapkit.workspace.style import qss, type_px                                # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _band(app, mode="dark"):
    pal = theme.pick_palette(mode)
    host = QWidget()
    host.resize(900, 300)
    band = hero_mod.HeroBand(pal, parent=host)
    band.setGeometry(0, 0, 900, band.height())
    host.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    host.show()
    app.processEvents()
    return host, band, pal


def test_the_gold_is_not_a_palette_token(app):
    """The signet is a SIGNATURE: it must be the same gold in every theme.

    This is the whole thesis -- the palette is the app's climate, the signet its signature, and a
    signature does not change colour when you change the weather. If the gold were ever derived from
    $accent or $focus it would go cyan in Mist, blue in Dark and orange in Gruvbox, which is precisely
    the negation of the idea. Guarded here because it is a one-line change away, forever.
    """
    assert "gold" not in theme.DARK and "gold" not in theme.MIST, "gold must never become a palette key"
    for mode in theme.THEMES:
        pal = theme.pick_palette(mode)
        want = hero_mod.GOLD_DARK if pal.get("dark") else hero_mod.GOLD_LIGHT
        assert want in (hero_mod.GOLD_DARK, hero_mod.GOLD_LIGHT)
    # exactly two constants, split on dark/light -- not per-palette
    assert hero_mod.GOLD_DARK != hero_mod.GOLD_LIGHT


def test_gold_is_legible_on_every_palette(app):
    """The gold is a brand constant, so it cannot be tuned per theme -- it has to clear every page it
    lands on. Measured floor across all 8: ~4.12 (solarized-light)."""
    def lum(h):
        h = h.lstrip("#")
        c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        c = [(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

    def cr(a, b):
        l1, l2 = sorted([lum(a), lum(b)], reverse=True)
        return (l1 + 0.05) / (l2 + 0.05)

    for mode, pal in theme.THEMES.items():
        gold = hero_mod.GOLD_DARK if pal["dark"] else hero_mod.GOLD_LIGHT
        assert cr(gold, pal["bg"]) >= 3.0, f"{mode}: the signet is invisible on this page"


def test_the_band_paints_a_lifted_plate_not_the_page(app):
    """The band must read as LIFTED off the page, not as more page.

    Honest scope, because I checked: this does NOT catch "someone added super().paintEvent()". I injected
    exactly that and the test still passed -- super() paints nothing on a plain QWidget (the universal
    `QWidget { background-color: $bg; }` in style.py needs WA_StyledBackground to bind, which the hero
    never sets), and the band fills its own rect afterwards regardless. So the load-bearing mechanism is
    OWNING THE FILL, not avoiding super(); the module docstring's emphasis is a little off.

    What this DOES catch is the failure that matters: the band ceasing to paint its own lifted plate (the
    gradient deleted, the fill dropped, the metrics collapsed to zero height) -- after which the front
    door silently becomes a flat page-coloured strip and the whole identity is gone with no error.
    """
    host, band, pal = _band(app)
    img = host.grab().toImage()
    assert band.height() > 0, "the band collapsed"
    assert img.pixelColor(2, 2).name() != pal["bg"], \
        "the hero is painting the page colour -- it no longer reads as a lifted plate"
    host.deleteLater()


def test_wordmark_face_resolves_without_bundling(app):
    """Sitka Banner ships with Windows, so no font is bundled (bundling was rejected: packaging + licence).

    Deliberately does NOT assert the face IS Sitka Banner -- the chain must stay free to fall through on a
    machine without it. It asserts only that whatever it picks actually EXISTS.
    NB the presence test in hero.py uses families() membership, NOT QFont.exactMatch(): exactMatch returns
    False for an INSTALLED font at any weight it lacks, and Sitka Banner ships 400/700 only.
    """
    fams = set(QFontDatabase.families())
    if not fams or "Segoe UI" not in fams:
        pytest.skip("no real font database (offscreen QPA stubs it)")
    assert hero_mod.wordmark_face() in fams


def test_density_changes_the_band_height(app):
    """The band's metrics are PYTHON, and _apply_density only re-renders the QSS -- no rebuild, no signal.
    So the shell must call set_density() explicitly or the band keeps its old height forever."""
    host, band, _ = _band(app)
    tall = band.height()
    band.set_density("compact")
    assert band.height() < tall, "compact must shrink the band"
    band.set_density("comfortable")
    assert band.height() == tall
    band.set_density("bogus")                       # unknown density falls back, never raises
    assert band.height() == tall
    host.deleteLater()


def test_status_is_painted_so_it_retints(app):
    """The status line used to be a QLabel with pal["muted"] baked into inline HTML at build time, so it
    went STALE on a live theme switch. The hero paints it instead. set_palette_ must not raise and the
    text must survive a palette change."""
    host, band, _ = _band(app)
    band.set_status("Currently editing a Field: HEARTH.")
    band.set_palette_(theme.pick_palette("mist"))
    app.processEvents()
    assert band._status == "Currently editing a Field: HEARTH."
    host.deleteLater()


def test_accent_is_never_spent_as_body_text():
    """`role="accent"` must not label any text in the workspace.

    Measured across all 8 palettes, accent on the card fill (surface_2) runs 2.44 (nord) .. 7.09 (mist) --
    SUB-AA IN 6 OF 8. It was being spent on Home's step numbers, the spine's pointer glyph, the fork-row
    tags and Import's "Will fork:" sentence. `text` (4.94 worst) and `muted` (4.55 worst) are the only
    inks that survive as text on a card in every palette.

    The law this pins: accent is a FILL for the verb you press, never a foreground for prose. It stays
    legitimate on `QPushButton#accent` (a fill, where accent_fg rides on top) -- so this checks the ROLE
    property, not the objectName.
    """
    import pathlib
    import re

    # A REGEX, not a substring. The real site was a TERNARY --
    #     g.setProperty("role", "ok" if done else "accent")
    # -- which contains no literal `setProperty("role", "accent")` at all. A substring guard passed with
    # the bug re-injected; verified, which is the only reason this is a regex.
    pat = re.compile(r"""setProperty\(\s*["']role["']\s*,[^)]*["']accent["']""")
    gui = pathlib.Path(__file__).resolve().parents[1] / "ff9mapkit" / "workspace"
    offenders = []
    for f in sorted(gui.glob("*.py")):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if pat.search(line):
                offenders.append(f"{f.name}:{i}")
    assert not offenders, (
        "accent spent as TEXT (sub-AA on a card in 6 of 8 palettes) at: " + ", ".join(offenders)
        + " -- use role='strong' ($text) or 'muted'; accent belongs on a FILL, not a foreground")


def test_every_theme_is_reachable_from_the_command_palette():
    """Ctrl-K must offer one row per registered theme -- and each row must apply ITS OWN theme.

    The rows are generated from THEME_CHOICES with a `m=mode` default arg. A bare
    `lambda: self._set_theme(mode)` would close over the LOOP VARIABLE, so all nine rows would silently
    apply the last theme -- a bug that looks fine in the palette, fires on click, and is invisible until
    someone picks Nord and gets Mist. This is a pure-data check (no QApplication) so it runs everywhere.
    """
    from ff9mapkit.editor.theme import THEMES, THEME_CHOICES
    modes = [m for m, _ in THEME_CHOICES]
    assert modes[0] == "auto", "the picker must lead with Match system"
    # every registered palette is offered, and nothing is offered that isn't registered
    assert set(modes) - {"auto"} == set(THEMES), "the Ctrl-K theme rows must mirror the registry exactly"
    # a late-binding closure would collapse the rows to one distinct callback target
    rows = [(f"Theme: {label}", lambda m=mode: m) for mode, label in THEME_CHOICES]
    assert len({fn() for _, fn in rows}) == len(THEME_CHOICES), \
        "the theme callbacks collapsed -- the lambdas closed over the loop variable"


def test_axis_falls_back_safely_without_a_column(app):
    """_axis() reads Home's real body geometry; unparented or mid-teardown it must fall back, not raise.
    (The live agreement between _axis() and the real column is asserted in the shell smoke.)"""
    host, band, _ = _band(app)
    x, col = band._axis()                            # column_source is None here
    assert isinstance(x, int) and col > 0 and x >= 0
    host.deleteLater()


def test_a_transparent_container_does_not_strip_its_children(app):
    """A container marked transparent must not silence the controls inside it.

    THE BUG THIS PINS (shipped for a long time; found on Home's get-started CTA):
    `w.setStyleSheet("background: transparent;")` has an implicit UNIVERSAL selector, and in Qt a
    stylesheet set on a WIDGET out-ranks the QApplication stylesheet REGARDLESS OF SPECIFICITY. So it
    cascaded down and beat `QPushButton#accent { background: $accent; }` from the app sheet. The button
    lost its FILL while keeping `color: $accent_fg` + `border: 1px solid $accent` (which the container
    rule never set) -- leaving accent-coloured ink on the raw page. Where accent_fg is dark ink it went
    invisible: dracula's #282a36 IS its bg, gruvbox's #282828 IS its bg. Measured on the newcomer's
    primary button: 1.00:1 in dracula and gruvbox-dark, 1.02 mist, 1.09 light, 1.11 solarized-light.

    `.QWidget` is Qt's EXACT-CLASS selector -- it matches a plain QWidget and not its subclasses -- so the
    container goes transparent and every real control keeps its styling. Rendered, not reasoned: this test
    fails against the bare rule and passes against the scoped one.
    """
    import collections

    from PySide6.QtWidgets import QApplication, QFrame, QPushButton, QVBoxLayout, QWidget

    from ff9mapkit.workspace.shell import _TRANSPARENT

    assert ".QWidget" in _TRANSPARENT, "the transparent idiom must be exact-class scoped, not universal"

    for mode in ("dracula", "gruvbox-dark", "mist", "light"):     # the palettes it actually broke
        pal = theme.pick_palette(mode)
        host = QWidget()
        host.setStyleSheet(qss(pal))
        lay = QVBoxLayout(host)
        box = QWidget()
        box.setStyleSheet(_TRANSPARENT)                            # the container under test
        bl = QVBoxLayout(box)
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        btn = QPushButton("Run setup")
        btn.setObjectName("accent")                                # the primary CTA
        cl.addWidget(btn)
        bl.addWidget(card)
        lay.addWidget(box)
        host.resize(240, 120)
        host.show()
        app.processEvents()
        img = host.grab().toImage().copy(
            btn.geometry().translated(btn.mapTo(host, btn.rect().topLeft()) - btn.geometry().topLeft()))
        fill = collections.Counter(
            img.pixelColor(x, y).name()
            for x in range(4, img.width() - 4) for y in range(4, img.height() - 4)).most_common(1)[0][0]
        assert fill.lower() == pal["accent"].lower(), (
            f"{mode}: the accent button lost its fill inside a transparent container "
            f"(got {fill}, want {pal['accent']}) -- its label is now accent_fg on the raw page")
        host.deleteLater()
        app.processEvents()


# --- the band's contrast fence -----------------------------------------------------------------
# This cannot be a palette computation and it cannot use audit_contrast.py. Both were tried:
#
#   MODELLING the ground (bg -> linear gradient -> off-axis radial bloom) requires _axis()'s geometry to
#   be right; a first attempt applied the bloom at full alpha where the render says it is ~32, and was
#   wrong by a full point.
#   MODE-SAMPLING a row strip returns the ground for a SHORT string and THE INK ITSELF for a long one,
#   because the ground is a gradient (hundreds of near-identical colours, few px each) while the ink is
#   one flat colour. It silently reported the status line at contrast 1.00 against "ground" == the ink.
#
# So: render twice, suppress drawText for the ground pass, and read the ground under the glyphs. The band
# is 100% QPainter with NO layout, so suppressing text cannot reflow anything -- the objection that killed
# blank-and-diff for the QSS audit does not apply to a paint-only widget.

def _lum(rgb):
    c = [v / 255 for v in rgb]
    c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _cr(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _bare_plate(d):
    """The band with every glyph suppressed -- the real composited ground, no model."""
    from PySide6.QtGui import QPainter
    orig = QPainter.drawText
    QPainter.drawText = lambda *a, **k: None
    try:
        b = hero_mod.HeroBand(d)
        b.resize(1280, hero_mod._METRICS["comfortable"][0])
        img = b.grab().toImage()
        b.deleteLater()
        return img
    finally:
        QPainter.drawText = orig


def test_the_hero_writes_everything_in_text_because_no_dim_tier_is_legal_here(app):
    """Both painted rows must clear 4.5:1 on the ground the band actually paints.

    THE MIST INVENTS A NINTH GROUND. Every text tier is fenced against the elevation ramp (bg / surface /
    surface_2 / surface_3). The bloom composites $text over the plate and lifts the ground PAST surface_3
    in 7 of 8 palettes, so none of those fences reach this band.

    $muted clears 4.5 on surface_3 in all 8 (4.57-5.70) and STILL fails here -- overline 4.09-4.79 (2/8),
    status 3.63-5.37 (5/8) -- because it is fenced to sit AT the floor and has no headroom for a lifted
    ground. It cannot get any: at _MIST_ALPHA = 0 it still only reaches 4.72. $text clears 8/8.

    Shipped state when this was written: overline in $text_subtle (2.5:1, sub-AA in 8/8) and status in
    $muted (sub-AA in 3/8). Both invisible to every test and to audit_contrast.py.
    """
    from PySide6.QtGui import QImage

    rows = {"overline": 34, "status": 130}
    for mode, pal in theme.THEMES.items():
        d = theme.derive(dict(pal))
        img = _bare_plate(d)
        ink = _rgb(pal["text"])
        for name, y in rows.items():
            worst = min(
                _cr(ink, (lambda c: (c.red(), c.green(), c.blue()))(QImage.pixelColor(img, x, y)))
                for x in range(200, 900, 5)
            )
            assert worst >= 4.5, f"{mode}: hero {name} {worst:.2f} on its painted ground -- sub-AA"


def test_the_hero_never_dims_its_text(app):
    """A shape check, because the value fence above can only measure the token it is handed.

    Any future 'let's soften the version string' will reach for $muted or $text_subtle, and both are
    illegal on this band for a reason no reviewer can see by reading: the bloom's ground is off the ramp
    those tiers are fenced against. This test is the note that says so at the point of temptation.
    """
    import inspect

    src = inspect.getsource(hero_mod.HeroBand.paintEvent)
    code = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
    for dim in ("text_subtle", "muted"):
        assert dim not in code, (
            f"the hero must not ink in ${dim}: the mist lifts its ground past surface_3, "
            f"off the ramp every text tier is fenced against"
        )


def test_gold_is_never_a_left_stripe(app):
    """A PERMANENT LAW, minted by measurement: gold and $warn are the same colour.

    Measured across all 8: ΔHue 0.3-3.3° in SEVEN of them (only dracula's yellow-green warn is far, at
    22.7°), and indistinguishable in luminance too in SIX (CR 1.073-1.312). And $warn's only shape in
    this app IS a left stripe -- `QLabel[role="banner"][state="warn"] { border-left: 4px solid $warn }` --
    while the warn banner shares a splitter with Home.

    So a gold `border-left` would ship "your build has warnings" as "your next action", in the same hue,
    on the same screen. The lede is a turned CORNER instead: a shape the status grammar has never used,
    and one the app already owns.

    The corner is also why this survives the identity contract. "One corner, once, or it's a costume"
    forbids a REPEATED ornament -- and a stripe would be a second, different gold object. The lede is the
    SAME mark from the SAME function at half the ink.
    """
    import inspect
    from ff9mapkit.workspace import style as style_mod

    # 1. no rule may put gold on a border-left
    for mode, pal in theme.THEMES.items():
        d = theme.derive(dict(pal))
        gold = (hero_mod.GOLD_DARK if pal.get("dark") else hero_mod.GOLD_LIGHT).lower()
        css = style_mod.qss(pal).lower()
        for ln in css.splitlines():
            if "border-left" in ln:
                assert gold not in ln, f"{mode}: gold spent as a left stripe -- that is $warn's shape"

    # 2. the lede must paint the elbow, not a stripe. Read the CODE, not the prose: LedeCard's docstring
    #    states this very law, so a naive substring check reads the law and calls it a violation.
    src = inspect.getsource(hero_mod.LedeCard)
    code = "\n".join(ln for ln in src.splitlines()
                     if not ln.lstrip().startswith("#") and '"""' not in ln)
    code = code.split("def ", 1)[-1] if "def " in code else code      # drop the class docstring body
    assert "signet_elbow" in code, "the lede must draw the shared mark"
    for banned in ("border-left", "fillRect", "drawRect"):
        assert banned not in code, f"the lede must be a corner, not a {banned}"


def test_the_lede_cites_the_hero_rather_than_repeating_it(app):
    """One mark, one function, two call sites -- that IS the argument, so fence the shape of it.

    If the lede ever grows its own path-drawing code, the claim "this is the same mark, not a second
    ornament" stops being true the moment the two drift -- and nothing else in the codebase would notice.
    """
    import inspect

    hero_src = inspect.getsource(hero_mod.HeroBand.paintEvent)
    lede_src = inspect.getsource(hero_mod.LedeCard.paintEvent)
    assert "signet_elbow(" in hero_src and "signet_elbow(" in lede_src
    # the lede is subordinate BY CONSTRUCTION: a shorter arm at the same dissolve
    assert hero_mod.LedeCard._ARM < 220, "the lede's arm must stay well under the hero's ~220px of ink"
    # the filigree + bead stay the hero's alone -- they are what make it the signature
    assert "drawPath(ip)" in hero_src, "the hero's inner filigree moved"
    assert "ip" not in lede_src and "_BEAD" not in lede_src, "the lede must not wear the signature's detail"


def test_the_signet_rests_at_one_and_motion_never_moves_the_resting_frame(app):
    """Motion that changes the RESTING frame is not motion -- it is a redesign wearing a stopwatch.

    A freshly-built band rests at 1.0, and at 1.0 signet_elbow uses a SOLID pen rather than a dash whose
    gaps happen to fall outside the path. That distinction is the whole reason the resting frame is
    provably untouched (0 differing px vs the pre-DRAWN render in all 3 palettes checked) instead of
    merely probably untouched.
    """
    for mode, pal in theme.THEMES.items():
        d = theme.derive(dict(pal))
        b = hero_mod.HeroBand(d)
        assert b._draw == 1.0, f"{mode}: a fresh band must rest at the end state"
        b.deleteLater()


def test_the_signet_reveal_is_monotonic_and_draws_in_order(app):
    """The mark only ever GROWS, and it grows in the right direction.

    Measured by frame-diff against t=0 (a colour heuristic gets this wrong -- a first attempt counted
    1287 "gold" pixels at t=0, when nothing was drawn at all):

        t=0.15   52 px   x 413-464  y 106      the arm's FAR END, on the baseline
        t=0.70  244 px   x 221-464  y 106      running left
        t=0.85  391 px   x 189-464  y  25-106  TURNED and RISEN

    That order is not designed -- the path was already in it. It starts where the gradient is faintest
    (alpha 70), so the mark appears out of open air and gains opacity as it resolves into the corner.
    """
    from PySide6.QtGui import QImage

    d = theme.derive(dict(theme.MIST))

    def frame(t):
        b = hero_mod.HeroBand(d)
        b.resize(1280, 156)
        b._draw = t
        img = b.grab().toImage().convertToFormat(QImage.Format.Format_RGB32)
        b.deleteLater()
        return img

    base = frame(0.0)

    def ink(t):
        img = frame(t)
        n, xs = 0, []
        for y in range(0, 156, 2):                      # every other row: this is a shape test, not a count
            for x in range(0, 1280, 2):
                if QImage.pixelColor(img, x, y) != QImage.pixelColor(base, x, y):
                    n += 1
                    xs.append(x)
        return n, (min(xs) if xs else None)

    seen = [(t, *ink(t)) for t in (0.0, 0.3, 0.6, 0.9, 1.0)]
    assert seen[0][1] == 0, "t=0 must draw nothing at all"
    counts = [n for _t, n, _x in seen]
    assert counts == sorted(counts), f"the reveal jumps backwards: {counts}"
    lefts = [x for _t, _n, x in seen if x is not None]
    assert lefts == sorted(lefts, reverse=True), f"the mark must grow LEFTWARD from the arm's end: {lefts}"


def test_motion_off_means_the_signet_is_simply_there(app):
    """The reduced-motion gate is not decoration: with motion off the band must show its END state on the
    first paint, synchronously -- never a blank corner waiting for an animation that will never run.

    This is the same contract every anim.py helper keeps, and it is why anim.configure() had to be hoisted
    ABOVE win.show(): motion is OFF until that call, so a first-paint animation configured afterwards
    would have snapped to the end for every user, forever, and looked exactly like a bug that was not there.
    """
    from ff9mapkit.workspace import anim

    assert not anim.enabled(), "the suite must run with motion off"
    d = theme.derive(dict(theme.DARK))
    b = hero_mod.HeroBand(d)
    b.resize(1280, 156)
    b.show()
    app.processEvents()
    assert b._draw == 1.0, "motion off -> the mark is simply there, on the first paint"
    b.hide()
    b.deleteLater()


# --- PLINTH: the front door measures itself ---------------------------------------------------

def test_the_shipped_band_is_returned_identically_at_100_percent(app):
    """THE GATE, and it is the whole reason band_metrics SCALES the design instead of deriving it.

    106.5 and 94.5 are half-pixel rule positions somebody chose BY EYE against a 40px serif. A formula
    that recomputes them from QFontMetricsF would replace a composition with an average and call it a
    refactor -- and it would be impossible to tell that regression from an improvement, because both
    arrive as "the numbers changed slightly".

    So 100% is IDENTITY, and asserted as such: not "close to", not "within a pixel". If a future round
    wants the band derived from metrics, it must delete this test on purpose and render the delta.
    """
    for density in ("comfortable", "compact"):
        assert hero_mod.band_metrics(density, 100) == hero_mod._METRICS[density], (
            f"{density}: band_metrics no longer reproduces the shipped design at 100%"
        )


def test_the_front_door_is_on_the_ramp_not_on_private_numbers(app):
    """PLINTH's other half. The band kept private 11px / 13px faces, so when QUARTO P1 raised the caption
    floor to 12, the hero became the ONLY surface in the app still shipping 11px text -- the front door
    wearing exactly the small type the user asked us to fix everywhere else.

    Fenced as the RELATIONSHIP (it IS the rung), not as the numbers 12 and 14: pinning the values would
    pass happily while the rest of the ramp moved away underneath them, which is the bug this closes.
    """
    overline, word, status = hero_mod.band_type(100)
    assert overline == type_px("type_caption", 100), "the hero's overline drifted off the caption rung"
    assert status == type_px("type_body", 100), "the hero's status line drifted off the body rung"
    # ...and the wordmark is NOT a rung: it is a brand constant, the one piece of type here chosen as a
    # drawing rather than as a tier. It scales; it must never join the ramp.
    assert word == hero_mod._WORD_PX
    assert word not in (type_px(k, 100) for k in ("type_caption", "type_body", "type_h2", "type_h3"))


def test_the_band_grows_with_the_text_size_dial(app):
    """The defect CALIBRE created: the band paints via QPainter, so no stylesheet reaches it. At 150%
    every tab grew and the front door sat at exactly 156px -- the app's identity surface was the one
    thing that ignored its own accessibility feature.

    Asserts MONOTONIC growth across the real dial, on every axis at once -- height, both faces, and the
    baselines. A partial scale is the worst outcome available: a 60px wordmark on a 156px band overflows
    its own composition, and that is what a half-wired version would ship.
    """
    from ff9mapkit import prefs
    prev = None
    for pct in prefs.TEXT_SCALES:
        m = hero_mod.band_metrics("comfortable", pct)
        overline, word, status = hero_mod.band_type(pct)
        cur = (m[0], m[2], m[4], overline, word, status)          # band_h, word_y, status_y, faces
        if prev is not None:
            assert all(c >= p for c, p in zip(cur, prev)), f"{pct}%: the band did not grow: {prev} -> {cur}"
            assert cur != prev, f"{pct}%: the band did not move at all"
        prev = cur
    biggest = hero_mod.band_metrics("comfortable", max(prefs.TEXT_SCALES))[0]
    assert biggest > hero_mod._METRICS["comfortable"][0] * 1.4, "150% barely moved the band"


def test_the_hero_holds_no_private_type_sizes(app):
    """The whole class of bug PLINTH closes, fenced at the source rather than per-number.

    Every hard setPixelSize() in this module was a number that could not hear the ramp OR the dial -- and
    they were the ONLY such sites in the package. They are now routed through band_type(), so the fence is
    "the paint code asks for a size, it never states one".

    Reads CODE, not prose (ast.unparse strips the docstrings that discuss these numbers -- this module's
    comments are full of "11px" and would pass a naive grep vacuously).
    """
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(hero_mod))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if getattr(fn, "attr", None) != "setPixelSize":
            continue
        arg = node.args[0] if node.args else None
        assert not isinstance(arg, ast.Constant), (
            f"hero.py:{node.lineno} calls setPixelSize({ast.unparse(arg)}) with a literal -- a private "
            f"type size that hears neither the ramp nor the text-size dial. Route it through band_type()."
        )


def test_the_signets_no_overflow_promise_is_structural_not_lucky(app):
    """signet_elbow's docstring promises the mark "can never overflow the column". That was TRUE BY TASTE:
    "bound to adv" binds the arm to the WORDMARK, and nothing bound the wordmark to the column. At 100% it
    never mattered (a 40px "Dream World IX" is ~300px against a 604-860px column) -- but PLINTH makes the
    arm grow with the dial while the column does not, so a scaled band in a narrow window would run the
    mark straight out of its own composition.

    An invariant that a new feature can falsify was never an invariant. Asserted at the extreme: the
    widest dial setting against the narrowest column the axis fallback allows.
    """
    from PySide6.QtGui import QFont, QFontMetricsF

    from ff9mapkit import prefs
    worst = max(prefs.TEXT_SCALES)
    wf = QFont(hero_mod.wordmark_face())
    wf.setPixelSize(hero_mod.band_type(worst)[1])
    wf.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, hero_mod._WORD_TRACK * worst / 100.0)
    adv = QFontMetricsF(wf).horizontalAdvance("Dream World IX")

    narrow = 240                                  # the axis fallback's own floor: max(240, width - 60)
    assert adv > narrow, (
        "this fence has stopped testing anything: the wordmark now fits the narrowest column even at the "
        f"largest scale ({adv:.0f} <= {narrow}), so min() is never exercised. Re-pick the extreme."
    )
    assert min(adv, narrow) == narrow, "the arm must clamp to the column when the wordmark outruns it"
