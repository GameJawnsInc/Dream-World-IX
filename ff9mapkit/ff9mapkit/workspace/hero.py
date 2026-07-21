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

from PySide6.QtCore import Property, QEasingCurve, QPointF, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QFontDatabase, QFontMetricsF, QLinearGradient,
                           QPainter, QPainterPath, QPen, QRadialGradient)
from PySide6.QtWidgets import QFrame, QWidget

from .. import __version__
from ..editor import theme
from . import anim, style

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

_METRICS = {           # (band_h, overline_y, word_y, rule_y, status_y, arm_up)  -- AT 100%
    "comfortable": (156, 36, 92, 106.5, 132, 78),
    "compact":     (136, 30, 80,  94.5, 118, 70),
}
_ARM_INDENT = 18       # the arm sits in the GUTTER: at 0 it impales the "D" and eats the bead
_ELBOW_R = 6
_BEAD = 3.5
_MIST_ALPHA = 40


def band_metrics(density: str = "comfortable", scale: int = 100):
    """The band's geometry at CALIBRE's ``scale`` (a percent; 100 = the shipped design).

    PLINTH. The band paints with QPainter, so no stylesheet reaches it -- which meant the text-size dial
    grew every tab while the front door sat at exactly 156px, the one surface in the app that ignored the
    accessibility feature. (`shell._apply_text_scale` was already CALLING the hero on every scale change;
    the scale simply never arrived. The wiring was there and inert.)

    THE 100% TUPLES ARE NOT DERIVED -- THEY ARE THE DESIGN, and this scales them rather than recomputing
    them. 106.5 and 94.5 are half-pixel rule positions somebody chose by eye against a 40px serif; a
    formula that re-derives them from font metrics replaces a composition with an average and calls it a
    refactor. So ``scale=100`` returns the shipped tuple IDENTICALLY, by construction rather than by
    arithmetic luck, and every other scale is that same composition, larger. The whole band moves as one
    thing: the mist bloom is keyed to `h`, the rule to the wordmark's baseline, the bead to the rule.
    """
    m = _METRICS.get(density, _METRICS["comfortable"])
    if scale == 100:
        return m                                   # the gate: identity, not a round-trip through floats
    k = scale / 100.0
    return (int(m[0] * k + 0.5),) + tuple(v * k for v in m[1:])


def band_type(scale: int = 100):
    """``(overline_px, word_px, status_px)`` -- the band's three faces at ``scale``.

    The overline and the status JOIN THE RAMP (they are `type_caption` / `type_body`, the same rungs the
    rest of the app spends) rather than keeping private 11 and 13. That is the other half of PLINTH: after
    QUARTO P1 raised the caption floor to 12, the hero was the ONLY surface left shipping 11px text -- the
    front door still wearing exactly the small type the user asked us to fix everywhere else.

    The WORDMARK is not a rung and never joins one: 40px Sitka Banner is a brand constant, the one piece
    of type here chosen as a drawing rather than as a tier. It scales; it does not tier.
    """
    return (style.type_px("type_caption", scale),
            int(_WORD_PX * scale / 100 + 0.5),
            style.type_px("type_body", scale))

# The signet signs itself, once, on the front door's first paint.
#
# THIS EXCEEDS anim.py's stated <=200ms bound ON PURPOSE, and the module's contract is amended rather
# than quietly broken. That bound governs STATE TRANSITIONS -- a drawer opening, a panel settling --
# where anything slower is latency wearing a costume. This is not a transition: it is a signature being
# written, once per session, on the one surface built to be looked at, and 200ms would make it a blink
# rather than a gesture. It is still bounded, still one-shot, still never looping, and still behind the
# same reduced-motion gate as everything else -- motion off, and the mark is simply there.
_SIGN_MS = 520


def wordmark_face() -> str:
    global _FACE
    if _FACE is None:
        fams = set(QFontDatabase.families())
        _FACE = next((f for f in _FACE_CHAIN if f in fams), "Segoe UI")
    return _FACE


def signet_elbow(p, x, y, arm, up, gold, *, a_from=255, a_to=70, r=_ELBOW_R, t=1.0):
    """THE MARK: an arm that runs in, turns a corner, and rises -- dissolving as it goes.

    "An FF9 window has four corners. We draw one." This is that one corner, and it is a FUNCTION rather
    than a block of paint code because it has two call sites and the pair is the whole argument: the hero
    draws it at the wordmark, the lede draws the SAME mark at its title, 200px down the same axis, at
    roughly half the ink. Two calls to one function is not a repeated ornament -- it is one mark, cited
    twice on one page, which is what "one corner, once" was written to protect.

    ``a_to`` is the dissolve: the frame does not stop, it fades out. Lowering ``a_from`` is how a caller
    asks for the mark more quietly -- the lede's subordination is a parameter, not a different drawing.

    Draws only the OUTER elbow. The doubled inner filigree and the bead stay the hero's alone: they are
    what make it the signature rather than a corner, and the lede is not the signature.

    ``t`` REVEALS the mark, 0 to 1 -- the signet signing itself. Nothing here was designed for that and it
    works anyway: the path is ALREADY in draw-on order. Verified by sampling it -- it starts at (arm's far
    end), which is where the gradient is at its FAINTEST (alpha 70), runs left into the corner GAINING
    opacity, turns, and rises. So the mark appears out of open air and resolves into the corner. The
    caller paints the bead after, so the bead lands last.

    At t >= 1 the pen is SOLID, not a dash whose gaps happen to fall outside the path -- so the resting
    frame is byte-identical to a build without any of this. Proven, not assumed.
    """
    path = QPainterPath()
    path.moveTo(x + arm, y)
    path.lineTo(x + r, y)
    path.arcTo(QRectF(x, y - 2 * r, 2 * r, 2 * r), -90, -90)
    path.lineTo(x, y - up)
    grad = QLinearGradient(x, 0, x + arm, 0)
    g0 = QColor(gold); g0.setAlpha(a_from)
    g1 = QColor(gold); g1.setAlpha(a_to)
    grad.setColorAt(0.0, g0); grad.setColorAt(1.0, g1)   # the frame doesn't stop, it dissolves
    pen = QPen(QBrush(grad), 1.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
    if t < 1.0:
        if t <= 0.0:
            return
        # A dash pattern of [total, total] with the offset walked from `total` down to 0 reveals exactly
        # [0, total*t]: the offset is the STARTING POINT WITHIN the pattern, so an offset of total*(1-t)
        # begins total*(1-t) into the dash and leaves total*t of it to run before the gap swallows the
        # rest. Units are pen widths, and the pen is 1.0, so the pattern is in px.
        total = path.length()
        if total <= 0:
            return
        pen.setDashPattern([total, total])
        pen.setDashOffset(total * (1.0 - t))
    p.setPen(pen)
    p.drawPath(path)


class LedeCard(QFrame):
    """Home's ONE card with the mark on it: the next thing to do, named.

    ``shell.py`` has always promised this in a docstring -- "the ONE primary action on the page (Journey
    ▸ Open, the recommended front door) renders in the accent colour" -- and all ten call sites pass
    ``False``. The branch that would paint it is live code nothing reaches. SIGNET built a title page and
    handed off to an index: ten identical cards, none of which is the answer to the question Home exists
    to ask.

    THE CONTRACT, and why this is not a second ornament. "One corner, once, or it's a costume" forbids a
    REPEATED ornament. This is the same mark, from the same function (:func:`signet_elbow`), at roughly
    half the ink, once per page, and only when there is a next action to name. The hero's docstring says
    "An FF9 window has four corners. We draw one" -- this draws that same one, 200px down the same axis.

    WHY GOLD AND NOT ACCENT -- measured, and it picks the colour AND the shape:
      - gold on surface_2 = 4.710 (sol-light) .. 6.964 (mist): the only delineation clearing the 3.0
        non-text floor in ALL 8, because it is the one candidate not sampled from the surface ramp.
      - accent on surface_2 = 2.118 (nord, FAILS) .. 7.095. It cannot carry a mark in nord at all.
      - and gold survives LIGHT (4.837) exactly where every elevation idea has died: a constant does not
        care that light's ramp is compressed.

    THE KILL SHOT, which is why this is a CORNER and never a left stripe: gold and $warn are the same
    colour -- ΔHue 0.3-3.3° in 7 of 8, and indistinguishable in luminance too in 6 of 8 (CR 1.073-1.312).
    $warn's only shape in this app IS a left stripe, and the warn banner shares a splitter with Home. A
    gold left stripe would ship "your build has warnings" as "your next action". A turned corner is a
    shape the status grammar has never used, and it is already ours.
    LAW: gold may never be spent as a border-left-only stripe. Fenced in test_workspace_hero.

    Zero new tokens: this sets ``role="card"`` and paints. Qt type selectors match SUBCLASSES (only
    `.QWidget` is exact-class), so `QFrame[role="card"]`'s fill and border land here byte-exact, and
    ``super().paintEvent`` must run FIRST so the mark goes on top of them.
    """

    _ARM = 170          # ~0.49x the hero's ink at the same dissolve -- subordinate BY CONSTRUCTION
    _INSET = 10
    _TOP = 14           # the card layout's top margin (shell._build_lede) -- where the title's box starts

    def __init__(self, pal, parent=None, scale=100):
        super().__init__(parent)
        self.pal = pal
        self._scale = scale
        self.setProperty("role", "card")

    def set_scale(self, scale):
        self._scale = scale
        self.update()

    def _up(self):
        """The arm's rise -- and therefore where its rule LANDS. Derived, because a number here breaks.

        This was `_UP = 26`, chosen by eye against a 15px title, which put the rule at y=36.5 with 2.6px of
        clearance under the title's box. QUARTO P2 merged h2/h3 into an 18px head rung, the title's box
        grew to y=37.9 -- and the rule went straight THROUGH the words. Nothing caught it: no test measures
        a QPainter stroke against a sibling QLabel, and a 1.4px overlap reads as an underline rather than
        as a bug. The render caught it.

        The rule's job is to sit UNDER the title, exactly as the hero's rule sits under the wordmark. So it
        is computed from the rung the title actually wears, plus the layout's own top margin: change the
        head rung, or turn the text-size dial, and the mark follows instead of striking through.
        """
        f = QFont("Segoe UI")
        f.setPixelSize(style.type_px("type_head", self._scale))
        f.setWeight(QFont.Weight.DemiBold)
        clear = self._TOP + QFontMetricsF(f).height() + 2      # +2: a rule ON the descenders is not a rule
        return max(26, int(clear - self._INSET + 0.5))          # never tighter than the shipped 26

    def paintEvent(self, ev):                          # noqa: N802 (Qt override)
        super().paintEvent(ev)                         # the QSS card fill + border, then the mark on top
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        gold = QColor(GOLD_DARK if self.pal.get("dark") else GOLD_LIGHT)
        k = self._scale / 100.0
        up = self._up()
        x = self._INSET + 0.5
        y = self._INSET + up + 0.5
        signet_elbow(p, x, y, self._ARM * k, up, gold, r=_ELBOW_R * k)
        p.end()


class HeroBand(QWidget):
    """Full-bleed front-door band. ``column_source`` is Home's ``body`` widget -- the hero reads its
    REAL geometry so the wordmark, the gold elbow and every card below sit on ONE axis."""

    def __init__(self, pal, parent=None, column_source=None, scale=100):
        super().__init__(parent)
        self.pal = pal
        self._column_source = column_source
        self._status = None
        self._draw = 1.0                 # the signet's reveal; 1.0 = at rest. See showEvent.
        self._signed = False             # once per session, on the front door's first paint
        self._density = "comfortable"
        self._scale = scale              # CALIBRE's percent -- see set_density / band_metrics
        self.setAutoFillBackground(False)
        self.set_density(self._density)

    # --- the signet signing itself -------------------------------------------------------
    def _get_draw(self):
        return self._draw

    def _set_draw(self, v):
        self._draw = float(v)
        self.update()

    # A real Qt property, because QPropertyAnimation can only drive one of those.
    draw = Property(float, _get_draw, _set_draw)

    def showEvent(self, ev):             # noqa: N802 (Qt override)
        super().showEvent(ev)
        if self._signed or not anim.enabled():
            self._draw = 1.0             # motion off -> the end state, synchronously, like every helper
            return
        self._signed = True              # once. Re-showing Home does not re-sign it.
        self._draw = 0.0
        a = QPropertyAnimation(self, b"draw", self)
        a.setDuration(_SIGN_MS)
        a.setStartValue(0.0)
        a.setEndValue(1.0)
        a.setEasingCurve(QEasingCurve.Type.OutCubic)
        a.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    # --- API -----------------------------------------------------------------------------
    def set_density(self, density, scale=None):
        """Re-lay the band. ``scale`` is CALIBRE's percent; omit it to keep the current one.

        Both knobs land here because both move the same six numbers, and the band's metrics are PYTHON --
        a QSS re-render alone leaves it at the old height. `setFixedHeight` is the whole reason this must
        be called rather than inferred: the band cannot grow itself.
        """
        if scale is not None:
            self._scale = scale
        self._density = density if density in _METRICS else "comfortable"
        self._m = band_metrics(self._density, self._scale)
        self._type = band_type(self._scale)
        self.setFixedHeight(int(self._m[0]))
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
        overline_px, word_px, status_px = self._type
        # PLINTH's one multiplier. The six METRICS and the three faces are already scaled (band_metrics /
        # band_type); `k` is for the mark's own geometry -- the arm's gutter, the elbow radius, the
        # filigree's offsets, the bead. Those are drawing, not type, so they scale here rather than
        # through the ramp. At 100% k is exactly 1.0 and every product below is its shipped literal.
        k = self._scale / 100.0
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
        f = QFont("Segoe UI"); f.setPixelSize(overline_px); f.setWeight(QFont.Weight.DemiBold)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0 * k)
        p.setFont(f); p.setPen(QColor(pal["text"]))
        p.drawText(QPointF(x0, overline_y), f"FF9 FIELD TOOLKIT \u00b7 {__version__}")

        # 6. wordmark -- pal["text"], NEVER gold. A gold "Dream World IX" is a fan-logo; it is the
        #    most predictable move available and why every FF9 fan project looks the same.
        wf = QFont(wordmark_face()); wf.setPixelSize(word_px); wf.setWeight(_WORD_WEIGHT)
        wf.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, _WORD_TRACK * k)
        p.setFont(wf); p.setPen(QColor(pal["text"]))
        p.drawText(QPointF(x0, word_y), "Dream World IX")
        adv = QFontMetricsF(wf).horizontalAdvance("Dream World IX")

        # 7. THE SIGNET -- typographically bound to `adv`, so it can never overflow the column.
        #    `_draw` is 1.0 at rest and everything below is the resting frame, byte-for-byte. It is only
        #    below 1 while the mark is signing itself on the front door's first paint.
        #
        #    THAT INVARIANT WAS TRUE BY TASTE AND IS NOW TRUE BY CONSTRUCTION. "Bound to adv" only bounds
        #    the arm to the WORDMARK; nothing bounded the wordmark to the column. At 100% that never
        #    mattered -- a 40px "Dream World IX" is ~300px against a 604-860px column -- but the arm grows
        #    with the type while the column does not, so a scaled band in a narrow window would run the
        #    mark straight out of its own composition. min() makes the docstring's promise structural:
        #    the arm ends at the wordmark's right edge, or at the column's, whichever comes first.
        ax = x0 - _ARM_INDENT * k + 0.5
        by, top = rule_y, rule_y - arm_up
        t = self._draw
        signet_elbow(p, ax, by, min(adv, col) + _ARM_INDENT * k, arm_up, gold, t=t, r=_ELBOW_R * k)

        # THE FINISH lands last: the filigree and the bead are what make this the signature rather than a
        # corner, so they arrive after the stroke has reached the top -- fading in over the final quarter
        # rather than popping, which reads as the hand lifting rather than as a frame dropping in.
        # `finish` is exactly 1.0 at rest, so both alphas below are their shipped values.
        finish = 1.0 if t >= 1.0 else max(0.0, (t - 0.75) / 0.25)
        if finish > 0.0:
            # the doubled inner rule -- the GRAMMAR of brass filigree (parallel strokes at a fixed
            # offset), abstracted from any specific FF9 flourish. Verified crisp at dpr 1.0/1.25/1.5.
            ip = QPainterPath()
            ix, iy = ax + 3 * k, by - 3 * k
            ip.moveTo(ix + 34 * k, iy); ip.lineTo(ix + 3 * k, iy)
            ip.arcTo(QRectF(ix, iy - 6 * k, 6 * k, 6 * k), -90, -90)
            ip.lineTo(ix, iy - 14 * k)
            gi = QColor(gold); gi.setAlpha(round(115 * finish))
            p.setPen(QPen(gi, 1.0 * k, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            p.drawPath(ip)

            # the bead -- FF9's corner detail, cited ONCE, at one 7px object.
            bead = _BEAD * k
            gb = QColor(gold); gb.setAlpha(round(255 * finish))
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(gb)
            dia = QPainterPath()
            dia.moveTo(ax, top - bead); dia.lineTo(ax + bead, top)
            dia.lineTo(ax, top + bead); dia.lineTo(ax - bead, top)
            dia.closeSubpath(); p.drawPath(dia)

        # 8. status -- painted, so it re-tints live (the QLabel version goes stale on retheme)
        # $text, per the one-ink law at the overline. This shipped in $muted and was sub-AA in 3 of 8
        # (light 3.63, solarized-light 3.98, dracula 4.35) -- found while fixing the overline, same cause:
        # the mist lifts the ground past the top of the ramp that muted is fenced against.
        sf = QFont("Segoe UI"); sf.setPixelSize(status_px)
        p.setFont(sf); p.setPen(QColor(pal["text"]))
        p.drawText(QPointF(x0, status_y),
                   self._status or "Nothing open yet \u2014 pick a starting point below.")
        p.end()
