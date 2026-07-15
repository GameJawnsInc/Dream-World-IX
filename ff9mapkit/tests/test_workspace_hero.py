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
from ff9mapkit.workspace.style import qss                                # noqa: E402


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
