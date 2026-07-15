"""The Signet hero band -- Home's front door.

An FF9 window has four corners. We draw one: a single 1px gold rule that turns one corner,
brackets the wordmark from the margin, and runs out flat beneath it into open air.

The gold is NOT a palette token. It is two module constants selected by pal["dark"], identical
in every theme including the neutral ones -- the palette is the app's climate, the signet is its
signature, and a signature does not change colour when you change the weather. (Spending gold on
`accent` destroys it: derive() aliases info=accent and grows focus from accent, so it would paint
every checkbox and focus ring; and selection_bg = mix(surface, accent, .16) cancels gold against
navy at 176 deg apart, to grey-brown mud (#35393f) no palette can override.)

paintEvent NEVER calls super(): that is what lets us beat the universal `QWidget { background-color:
$bg; }` rule in style.py:81 without WA_StyledBackground. All text is PAINTED, not QLabels, so the
rule binds to the wordmark's exact advance -- and so the status line re-tints on a live theme switch
(the QLabel version bakes pal["muted"] into inline HTML at build time and goes stale).
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (QBrush, QColor, QFont, QFontDatabase, QFontMetricsF, QLinearGradient,
                           QPainter, QPainterPath, QPen, QRadialGradient)
from PySide6.QtWidgets import QWidget

from ..editor import theme

# --- the brand constants (NOT palette tokens; identical in every theme) --------------------
# Verified legible on all 8 palettes: gold/bg 4.12 (solarized-light) .. 9.02 (mist).
GOLD_DARK = "#d9b45c"
GOLD_LIGHT = "#8a6a1f"

# A display serif with manuscript bones, shipped by Windows -- no bundle, no licence tax.
# NB resolve by families() membership: QFont.exactMatch() returns False for an INSTALLED font at
# any weight it lacks (Sitka Banner has 400/700 only), so it is a broken presence test.
_FACE_CHAIN = ("Sitka Banner", "Sitka Heading", "Constantia", "Georgia", "Segoe UI")
_FACE = None

# Sitka Banner ships 400/700 ONLY -- requesting DemiBold silently snaps to 700, which renders
# blocky. 400 is the display cut's designed weight and is the taste call.
_WORD_WEIGHT = QFont.Weight.Normal
_WORD_PX = 40
_WORD_TRACK = 0.5

_METRICS = {           # (band_h, overline_y, word_y, rule_y, status_y, arm_up)
    "comfortable": (156, 36, 92, 106.5, 132, 78),
    "compact":     (136, 30, 80,  94.5, 118, 70),
}
_ARM_INDENT = 18       # the arm sits in the GUTTER: at 0 it impales the "D" and eats the bead
_ELBOW_R = 6
_BEAD = 3.5
_MIST_ALPHA = 40


def wordmark_face() -> str:
    global _FACE
    if _FACE is None:
        fams = set(QFontDatabase.families())
        _FACE = next((f for f in _FACE_CHAIN if f in fams), "Segoe UI")
    return _FACE


class HeroBand(QWidget):
    """Full-bleed front-door band. ``column_source`` is Home's ``body`` widget -- the hero reads its
    REAL geometry so the wordmark, the gold elbow and every card below sit on ONE axis."""

    def __init__(self, pal, parent=None, column_source=None):
        super().__init__(parent)
        self.pal = pal
        self._column_source = column_source
        self._status = None
        self.setAutoFillBackground(False)
        self.set_density("comfortable")

    # --- API -----------------------------------------------------------------------------
    def set_density(self, density):
        self._m = _METRICS.get(density, _METRICS["comfortable"])
        self.setFixedHeight(self._m[0])
        self.updateGeometry()
        self.update()

    def set_status(self, text):
        self._status = text
        self.update()

    def set_palette_(self, pal):
        self.pal = pal
        self.update()

    # --- the column axis -----------------------------------------------------------------
    def _axis(self):
        """x-origin + width of Home's centred column. Derived from the body's REAL geometry --
        a PARALLEL FORMULA disagrees with the layout by +30px at the 724px default window."""
        src = self._column_source
        if src is not None and src.isVisible():
            top = self.window()
            try:
                x = (src.mapTo(top, src.rect().topLeft()).x()
                     - self.mapTo(top, self.rect().topLeft()).x())
                return x, src.width()
            except Exception:                       # noqa: BLE001 -- unparented / mid-teardown
                pass
        col = min(860, max(240, self.width() - 60))  # fallback only
        return (self.width() - col) // 2, col

    # --- paint ---------------------------------------------------------------------------
    def paintEvent(self, _ev):                       # NB: never calls super() -- see module docstring
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        _bh, overline_y, word_y, rule_y, status_y, arm_up = self._m
        pal = self.pal
        d = theme.derive(dict(pal))
        gold = QColor(GOLD_DARK if pal.get("dark") else GOLD_LIGHT)
        x0, col = self._axis()
        r = QRectF(0, 0, w, h)

        # 1. ground + 2. the lifted plate
        p.fillRect(r, QColor(pal["bg"]))
        g = QLinearGradient(0, 0, 0, h)
        g.setColorAt(0.0, QColor(d["surface_2"]))
        g.setColorAt(1.0, QColor(pal["bg"]))
        p.fillRect(r, QBrush(g))

        # 3. THE MIST -- an off-centre bloom keyed to the wordmark. This is why the band is a
        #    paintEvent and not a QSS gradient: QSS cannot place a radial bloom off-axis.
        mist = QRadialGradient(QPointF(x0 + 0.28 * col, h * 0.62), h * 1.35)
        c0 = QColor(pal["text"]); c0.setAlpha(_MIST_ALPHA)
        c1 = QColor(pal["text"]); c1.setAlpha(0)
        mist.setColorAt(0.0, c0); mist.setColorAt(1.0, c1)
        p.fillRect(r, QBrush(mist))

        # 4. bottom border
        p.fillRect(QRectF(0, h - 1, w, 1), QColor(pal["border"]))

        # 5. overline
        # THE BAND'S ONE INK LAW: everything the hero writes is $text. Nothing here is dimmed, and that is
        # not a preference -- no dim tier is LEGAL on this surface. Measured, per palette, by rendering:
        #
        #   THE MIST INVENTS A NINTH GROUND. Every text tier in this app is fenced against the elevation
        #   ramp (bg / surface / surface_2 / surface_3). The bloom below composites $text over the plate,
        #   which lifts the ground PAST surface_3 in 7 of 8 palettes -- so it lands on a ground no fence
        #   covers and none of those guarantees apply here. $muted clears 4.5 on surface_3 in all 8
        #   (4.57-5.70) and still fails ON THIS BAND: overline 4.09-4.79 (2/8), status 3.63-5.37 (5/8).
        #   It is a tier fenced to sit AT the 4.5 floor, so it has no headroom for a lifted ground and
        #   cannot acquire any: even at _MIST_ALPHA = 0 it only reaches 4.72. There is no alpha that
        #   rescues it -- the mist is not negotiable and the dim tier is not affordable.
        #
        # $text clears 8/8 on both rows (overline 5.16-12.34, status 4.64-10.85). Subordination comes from
        # TYPE, not from dimming -- PLAN.md's own law, written before this band existed: 11px DemiBold at
        # +1.0 tracking against a 28px serif wordmark IS the hierarchy. This shipped as $text_subtle
        # (2.5:1, sub-AA in 8/8) which that same Rejected table forbids for text in writing.
        #
        # audit_contrast.py can never see any of this: it reads ink via w.palette().color(foregroundRole()),
        # a QLabel API, and this band has no QLabels. The fence lives in test_workspace_hero.py and works by
        # rendering the band twice -- once with drawText suppressed -- because the ground is a gradient and
        # cannot be sampled by mode or modelled by hand (both were tried; both lied).
        f = QFont("Segoe UI"); f.setPixelSize(11); f.setWeight(QFont.Weight.DemiBold)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
        p.setFont(f); p.setPen(QColor(pal["text"]))
        p.drawText(QPointF(x0, overline_y), "FF9 FIELD TOOLKIT \u00b7 1.0.0b15")

        # 6. wordmark -- pal["text"], NEVER gold. A gold "Dream World IX" is a fan-logo; it is the
        #    most predictable move available and why every FF9 fan project looks the same.
        wf = QFont(wordmark_face()); wf.setPixelSize(_WORD_PX); wf.setWeight(_WORD_WEIGHT)
        wf.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, _WORD_TRACK)
        p.setFont(wf); p.setPen(QColor(pal["text"]))
        p.drawText(QPointF(x0, word_y), "Dream World IX")
        adv = QFontMetricsF(wf).horizontalAdvance("Dream World IX")

        # 7. THE SIGNET -- typographically bound to `adv`, so it can never overflow the column.
        ax = x0 - _ARM_INDENT + 0.5
        by, top = rule_y, rule_y - arm_up
        path = QPainterPath()
        path.moveTo(ax + adv + _ARM_INDENT, by)
        path.lineTo(ax + _ELBOW_R, by)
        path.arcTo(QRectF(ax, by - 2 * _ELBOW_R, 2 * _ELBOW_R, 2 * _ELBOW_R), -90, -90)
        path.lineTo(ax, top)
        grad = QLinearGradient(ax, 0, ax + adv + _ARM_INDENT, 0)
        g0 = QColor(gold); g0.setAlpha(255)
        g1 = QColor(gold); g1.setAlpha(70)
        grad.setColorAt(0.0, g0); grad.setColorAt(1.0, g1)   # the frame doesn't stop, it dissolves
        p.setPen(QPen(QBrush(grad), 1.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        p.drawPath(path)

        # the doubled inner rule -- the GRAMMAR of brass filigree (parallel strokes at a fixed
        # offset), abstracted from any specific FF9 flourish. Verified crisp at dpr 1.0/1.25/1.5.
        ip = QPainterPath()
        ix, iy = ax + 3, by - 3
        ip.moveTo(ix + 34, iy); ip.lineTo(ix + 3, iy)
        ip.arcTo(QRectF(ix, iy - 6, 6, 6), -90, -90)
        ip.lineTo(ix, iy - 14)
        gi = QColor(gold); gi.setAlpha(115)
        p.setPen(QPen(gi, 1.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        p.drawPath(ip)

        # the bead -- FF9's corner detail, cited ONCE, at one 7px object.
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(gold))
        dia = QPainterPath()
        dia.moveTo(ax, top - _BEAD); dia.lineTo(ax + _BEAD, top)
        dia.lineTo(ax, top + _BEAD); dia.lineTo(ax - _BEAD, top)
        dia.closeSubpath(); p.drawPath(dia)

        # 8. status -- painted, so it re-tints live (the QLabel version goes stale on retheme)
        # $text, per the one-ink law at the overline. This shipped in $muted and was sub-AA in 3 of 8
        # (light 3.63, solarized-light 3.98, dracula 4.35) -- found while fixing the overline, same cause:
        # the mist lifts the ground past the top of the ramp that muted is fenced against.
        sf = QFont("Segoe UI"); sf.setPixelSize(13)
        p.setFont(sf); p.setPen(QColor(pal["text"]))
        p.drawText(QPointF(x0, status_y),
                   self._status or "Nothing open yet \u2014 pick a starting point below.")
        p.end()
