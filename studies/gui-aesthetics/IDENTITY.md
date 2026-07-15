<!--
SIGNET -- the identity build spec. Round 3, 2026-07-15. NOT YET BUILT.

Round 2 (PLAN.md) shipped 9 commits and made the app CORRECT. It failed at BEAUTY for a structural
reason this round was designed to fix: its review pass was tuned to skepticism, and skepticism is
ASYMMETRIC -- a defect has a measurement and survives review, a decoration has only taste and dies. So
every decorative proposal was refuted (gradients +4/255, a bundled font, animation, a new palette), each
refutation individually CORRECT, and the sum was a plan with no positive vision. The user: "is this the
extent of the beauty research? i expected more."

So this round INVERTED the harness: 6 art directors each had to COMMIT to one direction (a menu of
options scored as a failure); taste was an allowed input; and measurement's job was to make the winning
idea WORK rather than to veto it. A 4-lens panel (craft designer / FF9 obsessive / Qt engineer / nightly
user) scored all six out of 50. Every direction scored 8.8-9.0 on point-of-view -- the framing held.

  42.0 Signet  ·  41.5 Mist Engine  ·  41.2 Facet  ·  41.0 Illuminated  ·  39.8 Vellum  ·  39.5 Mist Line

The CONTRARIAN brief won: identity is a signature, not a theme.

VERIFIED INDEPENDENTLY BEFORE THIS FILE LANDED:
  - the MIST palette clears 20/20 fences ON ARRIVAL, no hex moved; every number reproduces to 3dp.
  - focus == accent exactly (#5fc9d8, zero hue drift -- the brightening loop exits on iteration 0).
  - Sitka Banner IS installed on Windows and resolves with no substitution (no bundling needed).
  - the navy+gold kill is real: navy/gold are 177.8 deg apart (near-complement), so the CENTRALLY DERIVED
    selection_bg = mix(surface, accent, 0.16) cancels to the mud hex #35393f (S=15.9%) exactly as claimed;
    navy+cyan keeps #223d53 (S=59%). That is the selected tree row.

READ §"Three things I am handing you honestly" BEFORE BUILDING. The headline caveat: the user asked for a
navy+GOLD theme and the arithmetic says gold-as-accent is wrong, so MIST ships navy+CYAN and the gold is
ornament only. Mist is FF9 by argument more than by sight. That trade is the spec's own admission.
-->

# SIGNET — the Dream World IX identity build spec

## The direction

**Name:** SIGNET.

**Thesis:** *An FF9 window has four corners. We draw one.*

The palette is the app's **climate**. The signet is its **signature**. A signature does not change colour when you change the weather.

**The one move:** a single 1px **gold** rule on the Home hero that turns one corner — up the left margin, past the overline, bracketing the whole text block, then out flat beneath the wordmark where it **dissolves to alpha 70** instead of stopping. One bead at the top. One doubled inner stroke at the elbow. That is the entire ornament, and it is the *entire* citation of FF9's brass-bordered menu: quoted once, at the door, and never again.

Gold is **not a palette token**. It is two module constants (`#d9b45c` dark / `#8a6a1f` light) selected by `pal["dark"]`, **identical in every theme including the neutral ones**. The Mist palette ships alongside as an opt-in climate; it carries gold in **zero** tokens. These two facts are the same decision viewed from two sides, and §4 defends both.

Three things do the work, in this order of importance:
1. **Sitka Banner at 40px / weight 400** on navy — the voice. It reads as a **title page**, a register no dark IDE occupies.
2. **Composition** — a full-bleed 156px band, an off-centre painted mist bloom, a column axis read from the real layout.
3. **The signet** — the gold corner. The signature.

The essay that won this round claimed the signet was "the entire identity." That is false and the direction is stronger for admitting it: if you ever cut something, **cut the inner filigree, not the serif.**

---

## The palette

Registry key `mist`, picker label **`"Mist (FF9)"`**.

> ⚠️ **`theme.py` is pure ASCII.** The label must be `"Mist (FF9)"` — not `"Mist — FF9"`. An em-dash makes it the first non-ASCII byte in the file; the file's own house style writes `--`. A probe hit this as a `SyntaxError`.

Defines **exactly the 22 keys** and **none** of the 6 derived ones (`derive()` short-circuits and returns the same object if all 6 are present — a base palette must never define them).

### The 22 keys

| key | hex | note |
|---|---|---|
| `dark` | `True` | real `bool`, not a string |
| `bg` | `#0f1826` | the page — deep Mist-blue night |
| `surface` | `#16223a` | panels, toolbar, crumb row |
| `surface_btn` | `#1e2d4a` | button rest |
| `field` | `#0c1420` | input wells, below the page |
| `text` | `#e9e6dc` | warm parchment white, not #fff |
| `muted` | `#9fadc4` | the dimmer tier; blue-grey, stays in family |
| `accent` | `#5fc9d8` | **the Mist** — also `info` and `focus` via `derive()` |
| `accent_fg` | `#08171b` | dark ink on a light accent (the dracula/gruvbox strategy) |
| `accent_hover` | `#7ad7e4` | |
| `accent_pressed` | `#46b0c0` | |
| `help` | `#9d8bd8` | violet, 293.9° — far from everything |
| `help_hover` | `#b3a4e4` | |
| `border` | `#2b3d5e` | **stays neutral. Never gold.** See §4 |
| `success` | `#63cf7a` | 162.8°-family green |
| `hover` | `#26385a` | lighter than `surface_btn` (dark-palette direction) |
| `pressed` | `#2f4468` | lighter still |
| `scroll` | `#33456a` | |
| `log_bg` | `#0b111c` | |
| `log_fg` | `#cfd8e6` | |
| `error` | `#ff6b6b` | **unchanged from the tree's natural slot** |
| `warn` | `#e0a93b` | **unchanged. Amber sits 126.8° from Mist** |

Copy-paste block for `ff9mapkit/ff9mapkit/editor/theme.py` (insert after `GRUVBOX_DARK`, before `THEMES`):

```python
# --- authoring law (a COMMENT, not a test) -------------------------------------------------
# Keep every semantic hue >=25 deg from every other in OKLCH. This palette's worst pair is
# accent(196.4) vs success(146.3) = 58.1 deg -- the widest in the tree. It is NOT a fence:
# a fence whose tightest subject is the palette you're shipping is a trap, not a fence.
MIST = {                        # "Mist (FF9)" -- the opt-in FF9 climate. NEVER the default.
    "dark": True,
    "bg": "#0f1826",            # the Mist-blue night page
    "surface": "#16223a",
    "surface_btn": "#1e2d4a",
    "field": "#0c1420",
    "text": "#e9e6dc",          # warm parchment white
    "muted": "#9fadc4",
    "accent": "#5fc9d8",        # THE MIST. derive() aliases info=accent and grows focus from it --
                                # which is why the identity gold is NOT spent here (see IDENTITY.md).
    "accent_fg": "#08171b",     # dark ink on the light accent -- measures 9.430, best in the tree
    "accent_hover": "#7ad7e4",
    "accent_pressed": "#46b0c0",
    "help": "#9d8bd8",
    "help_hover": "#b3a4e4",
    "border": "#2b3d5e",
    "success": "#63cf7a",
    "hover": "#26385a",
    "pressed": "#2f4468",
    "scroll": "#33456a",
    "log_bg": "#0b111c",
    "log_fg": "#cfd8e6",
    "error": "#ff6b6b",
    "warn": "#e0a93b",
}
```

Then two registrations, and **nothing else in the tree enumerates palettes** (`prefs` stores an opaque string; `style.py` reads tokens by name):

```python
THEMES = { ..., "gruvbox-dark": GRUVBOX_DARK, "mist": MIST }
THEME_CHOICES = [ ..., ("gruvbox-dark", "Gruvbox Dark"), ("mist", "Mist (FF9)") ]
```
`theme.py:203` (THEMES) · `theme.py:214` (THEME_CHOICES) · `pick_palette` (`theme.py:246`) needs no change — it reads `THEMES.get(mode)`.

### Derived (by `derive()`, do not define)

| token | formula | value |
|---|---|---|
| `surface_2` | `mix(surface, #ffffff, 0.05)` | `#222d44` ← the `role="card"` fill |
| `surface_3` | `mix(surface, #ffffff, 0.10)` | `#2d384e` |
| `selection_bg` | `mix(surface, accent, 0.16)` | `#223d53` — **51.1% accent chroma retained, best in tree** |
| `text_subtle` | `mix(muted, bg, 0.28)` | `#778398` |
| `focus` | `_focus_token(accent, surface)` | `#5fc9d8` — **exits on iteration 0; `focus == accent` exactly, zero hue drift** |
| `info` | `= accent` | `#5fc9d8` |

### THE FENCE TABLE — every assertion, computed

Measured against the real `ff9mapkit.editor.theme` module (`_contrast`, `_rel_lum`, `derive`). **21/21 green on arrival. No hex moved.**

| # | assertion | floor | **measured** | ✓ |
|---|---|---|---|---|
| 1 | `set(MIST) == set(theme.LIGHT)` | — | **True**, len 22, missing ∅, extra ∅ | ✅ |
| 2 | `contrast(text, bg)` | 4.5 | **14.264** | ✅ |
| 3 | `contrast(text, surface)` | 4.5 | **12.701** | ✅ |
| 4 | `contrast(muted, bg)` | 4.5 | **7.845** | ✅ |
| 5 | `contrast(muted, surface)` | 4.5 | **6.985** | ✅ |
| 6 | `contrast(text, surface_2)` ← card fill | 4.5 | **11.014** | ✅ |
| 7 | `contrast(muted, surface_2)` ← card fill | 4.5 | **6.057** | ✅ |
| 8 | `lum(muted) < lum(text)` == `dark` | — | **0.4124 < 0.7908** | ✅ |
| 9 | `contrast(accent_fg, accent)` | 3.0 | **9.430** ← highest in the tree | ✅ |
| 10 | `contrast(focus, surface)` | 3.0 | **8.182** | ✅ |
| 11 | `(lum(bg) < 0.5) == dark` | — | **0.0089 < 0.5** | ✅ |
| 12 | `lum(hover) > lum(surface_btn)` == `dark` | — | **0.0398 > 0.0265** | ✅ |
| 13 | `contrast(hover, surface_btn)` | 1.05 | **1.174** | ✅ |
| 14 | `contrast(pressed, hover)` | 1.03 | **1.196** | ✅ |
| 15 | `contrast(hover, surface)` | 1.05 | **1.356** | ✅ |
| 16 | `contrast(error, bg)` | 3.0 | **6.419** | ✅ |
| 17 | `contrast(error, surface)` | 3.0 | **5.715** | ✅ |
| 18 | `contrast(warn, bg)` | 3.0 | **8.404** | ✅ |
| 19 | `contrast(warn, surface)` | 3.0 | **7.483** | ✅ |
| 20 | `contrast(success, bg)` / `(success, surface)` | 3.0 | **9.107 / 8.109** | ✅ |
| 21 | elevation monotonic `surface ≤ surface_2 ≤ surface_3` | — | **0.0162 ≤ 0.0263 ≤ 0.0394** | ✅ |

**Registration cost, measured empirically** (registered, ran, reverted): `tests/test_editor_theme.py` + `test_prefs.py` → **22 passed**; the broad GUI/theme/style/workspace surface → **135 passed**. With `THEMES` edited but `THEME_CHOICES` not, exactly one test fails (`test_theme_choices_cover_every_palette`: *"Extra items in the right set: 'mist'"*) — that is the whole coupling.

### Why gold is not the accent — the arithmetic, so nobody relitigates it

A navy+gold-**accent** palette is *buildable*; it is green with `error #f4566b` + `warn #ff9e42`. It was rejected on three measured grounds:

1. **`warn` IS the accent.** Gold `#d9b45c` = OKLCH H **86.8°**; amber `warn #e0a93b` = H **80.9°**. **5.9° apart**, luminance ratio 1.073 — identical in hue *and* in greyscale. And `derive()` aliases `info = accent`, so gold would be simultaneously **"information" and "caution."** Buying `warn` a slot requires **re-hueing `error`** (the window width is exactly `gold_H − error_H − 50`), and the best result still lands a `warn` at L=0.783 against gold's L=0.785 — separating on hue only.
2. **`selection_bg` turns to mud, and no palette can fix it.** `selection_bg = mix(surface, accent, 0.16)` is centrally derived. Every shipped dark palette keeps its accent within **25°** of its own surface. Navy↔gold is **176.4° apart — an almost exact complement** — so the mix *cancels* to neutral **`#35393f`**, retaining **10.3%** chroma. Mist retains **51.1%**. Blue + yellow = grey, in sRGB, by construction. The selected tree row is the most-looked-at surface in a file-tree IDE.
3. **Gold-as-accent paints every checkbox and focus ring in the app** — the costume permanently on.

Move gold to ornament and the `info = accent` "trap" **becomes an asset**: the Mist *is* the game's atmosphere, `warn` sits 126.8° away, and `error`/`warn` never move. Worst-case semantic hue separation: **58.1°** for Mist vs **5.9°** for gold-as-accent.

**And the gold survives everywhere it must.** `gold/bg` across all 8 palettes: light **4.19** · dark **8.17** · nord **6.32** · dracula **7.21** · solarized-dark **7.60** · solarized-light **4.12** · gruvbox-dark **7.47** · mist **9.02**. A **4.12 floor** — a stronger guarantee than the 3:1 a `$focus`-tinted ornament would buy.

---

## The front door

### The traps, and how each is beaten

| trap | fact | handling |
|---|---|---|
| Universal `QWidget { background-color: $bg; }` | `workspace/style.py:81` — any bare container paints `$bg` over a band | `paintEvent` **never calls `super()`**. Verified: hero top-left renders `#212c43` while the page 40px below is `#0f1826`. `WA_StyledBackground` is `False` on the hero and **does not need setting** — the attribute is irrelevant when you own the paint. |
| Python margins are density-deaf | `_apply_density` (`shell.py:535`) **re-renders QSS only** — no rebuild, no signal | explicit `set_density()` call. Real values are **`comfortable` / `compact`** (`prefs.py:20`) — *not* "cozy". |
| Home is built once, never rebuilt | `_welcome()` runs inside `__init__` via `_build_central` (`shell.py:1040`) | register on `self._icon_retint` (`shell.py:462`, iterated in `retheme` at `shell.py:526`). |
| Inline-hex staleness | `_home_status` bakes `self.pal["muted"]` into HTML at build time; `retheme` never calls `_refresh_home_status` → **switch theme while sitting on Home and the status goes stale** | the hero **paints** its status. The pre-existing bug is fixed as a side effect. |
| `QFontDatabase.exactMatch()` | returns **`False` for an installed font** at any weight it lacks. Sitka Banner ships **400/700 only** | resolve by `QFontDatabase.families()` membership. |
| Sitka Banner has no DemiBold | requesting DemiBold **silently snaps to 700**, which renders blocky and reads as a generic textbook heading | **weight 400**, the display cut's designed weight. |
| Offscreen QPA | zero system fonts; advances inflated **1.8×** (title 624px offscreen vs **342px** real). `widgets.py:243` already warns | never measure Home under `--smoke`. Use `QT_QPA_PLATFORM=windows` + `WA_DontShowOnScreen`. |

**Refuted by pixels, kept at full spec:** *"the inner filigree will smear at 125% DPI."* Rendered at dpr 1.0 / 1.25 / 1.5, cropped and 4×-zoomed — **it does not smear, it gets crisper.** Antialiased `QPainter` gains from the extra device pixels. The filigree stays.

### `ff9mapkit/ff9mapkit/workspace/hero.py` — NEW FILE, verbatim

```python
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
        f = QFont("Segoe UI"); f.setPixelSize(11); f.setWeight(QFont.Weight.DemiBold)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
        p.setFont(f); p.setPen(QColor(d["text_subtle"]))
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
        sf = QFont("Segoe UI"); sf.setPixelSize(13)
        p.setFont(sf); p.setPen(QColor(pal["muted"]))
        p.drawText(QPointF(x0, status_y),
                   self._status or "Nothing open yet \u2014 pick a starting point below.")
        p.end()
```

**QSS added: none.** The hero is 100% `QPainter`, on purpose — QSS has no radial gradient placeable off-axis, no path stroking, no per-glyph advance measurement. Every one of those is load-bearing here. The **only** QSS interaction is the one at `style.py:81` that the `paintEvent` deliberately bypasses.

### The three constants that carry the design, and why they are what they are

| constant | value | rendered evidence |
|---|---|---|
| `_ARM_INDENT` | **18** | at 0 (as originally specced) **the vertical arm runs through the "D" and the bead is swallowed by its stem.** Two judges caught it; I reproduced it. The fix is *better than the original*: a rule hanging in the margin is a **manuscript's marginal bracket** — more the thing the direction was reaching for than a rule that touches the text. The metaphor got stronger by being corrected. |
| `arm_up` | **78** (was 28) | at 28 the L is 8:1 and reads as **an underline with a hook** — the thesis failing to arrive. At 78 the arm runs past the overline and brackets the *entire text block*; the ratio drops to ~3.5:1 and it finally reads as **one corner of a window**. Nobody caught this; four arm lengths were rendered and looked at. **The single most important change in the hardening.** |
| `_MIST_ALPHA` | **40** (spec said 18) | 18 rendered **nearly invisible** — the same class of error as round 1's fatal +4/255 gradient. 40 is the floor at which the bloom is a thing you can see. |
| band `h` | **156** (contingency said 132) | rendered side by side: 40px/400 at **h156 is the composed one**; 132 is cramped. Take it on the first screenshot, not after an "is that it?" verdict. |

### `_axis()` — why the formula is deleted, not tuned

The spec's `x0 = (width - col) // 2` is a **duplicate formula for one axis**, and it disagrees with the layout:

```
viewport 724 -> body.x = 60, formula x0 = 30   DELTA +30   <- gold elbow 30px left of every card
viewport 844 -> body.x = 66, formula x0 = 30   DELTA +36
viewport 1044+ .......................................... converged
```

`_axis()` asks the body where it is. **Exact match at all six widths:**

| viewport | `body.x` | `_axis()` | |
|---|---|---|---|
| 724 | 60 | **60** | ✅ |
| 844 | 66 | **66** | ✅ |
| 1044 | 92 | **92** | ✅ |
| 1244 | 192 | **192** | ✅ |
| 1444 | 292 | **292** | ✅ |
| 2000 | 570 | **570** | ✅ |

Closed by construction, not by tuning. The formula survives only as a fallback when no `column_source` is set.

### Wiring — five edits in `ff9mapkit/ff9mapkit/workspace/shell.py`

**(a) `shell.py:1432-1439`** — `page` gets a vertical layout; hero first, then the existing centred row:

```python
page = QWidget()
pv = QVBoxLayout(page); pv.setContentsMargins(0, 0, 0, 0); pv.setSpacing(0)
body = QWidget(); body.setMaximumWidth(860)
self._hero = HeroBand(self.pal, column_source=body)      # reads body's REAL geometry
pv.addWidget(self._hero)
row = QWidget(); row.setStyleSheet("background: transparent;")   # the codebase's own idiom (:1479, :1498, :1556, :1615)
ph = QHBoxLayout(row); ph.setContentsMargins(30, 22, 30, 26)
ph.addStretch(1)
ph.addWidget(body, 20)
ph.addStretch(1)
pv.addWidget(row); pv.addStretch(1)
```

**(b) `shell.py:1438`** — **`ph.addWidget(body, 4)` → `ph.addWidget(body, 20)`.**

The briefing's account of this bug is wrong in every number, and the truth is worse. Measured, fresh user (`%LOCALAPPDATA%\ff9mapkit\config\prefs.json` cleared; window 1280 → split `[300, 738, 240]` → page 724):

```
win=1280  page= 724  body= 512   gutters=152 (22.9%)   <- NOT ~822 / NOT 30%+
win=1600  page=1044  body= 656                          <- 860 NOT reached here
win=2000  page=1444  body= 860   <- the 860 max
```

At 1280 **`body.width() == body.minimumSizeHint() == 512`** — **the stretch is not binding today.** The `4/6` target would be **435px**; the minimum rescues it. And that minimum is propped up by *un-word-wrapped labels* — the `hint` at `shell.py:1522` (no `setWordWrap`), the display title, and Recent's un-wrapped paths (`minW=1105` for `EVFT_NATIVE`). Measured directly:

```
body BEFORE=512  AFTER=398   (labels wrapped + Recent cleared)
gutters 199 of 597 = 33.3%
```

**So the briefing's 30%+ figure is real — it is just the *post-fix* number.** The moment any future round wraps the hint or a fresh user has an empty Recent, the column silently collapses to ~398px. Factor **20** pins the body to 860 as early as geometry allows. *(The hero's `_axis()` makes the hero correct at **any** factor — the `4` gets fixed anyway, in the same breath, because it is a live trap.)*

**(c) `shell.py:1443-1449`** — delete the `title` QLabel (`role="display"` — **the app's only one**) and `self._home_status`; both now live in the hero. **`self._home_setup` STAYS** — it has a `linkActivated` connection and must remain a real QLabel.

**(d) `_refresh_home_status` (`shell.py:1671-1681`)** — replace the two `self._home_status.setText(...)` branches with:
```python
if name is None:
    self._hero.set_status("Nothing open yet \u2014 pick a starting point below.")
else:
    self._hero.set_status(f"Currently editing a {level}: {name}.")
```
(and drop the `hasattr(self, "_home_status")` guard for a `hasattr(self, "_hero")` one).

**(e) `retheme` (`shell.py:526`)** — register on the sanctioned hook, next to `self._icon_retint = []` at `shell.py:462`:
```python
self._icon_retint.append(lambda: self._hero.set_palette_(self.pal))
```
and `_apply_density` (`shell.py:535`) gets one line: `self._hero.set_density(self._density)`.

### Height honesty

156px absorbs the deleted title (42) + status (28) + spacing (20) + 4px margin ≈ **net +40px** on a page already **1313px** against a **562px** viewport. It does not meaningfully change the fold problem — **which is real, which I measured, and which is not this round's job.** For the record: **all 7 entry-point cards are below the fold at the default window.** The first frame today is a title, three paragraphs and a setup checklist, in a 512px column, flanked by an empty tree and an empty inspector. That is a Home **information-architecture** defect and it deserves its own round. It is not being smuggled into an art-direction brief.

> **Recon correction, for the engineer:** Home's rows use `setObjectName("card")` → `style.py:263` (`background: $surface`, radius **10**) — a Home-specific **legacy** rule. They are **not** among the 27 `role="card"` sites (`style.py:290`, `$surface_2`, radius `$radius_lg`=8). **Home's contrast pair is text/`surface`, not text/`surface_2`.** The "surface_2 is the CARD FILL, load-bearing" note in the briefing does not govern the front door. Do not "fix" this in this round.

---

## What we are NOT doing

**The contract, in the user's frame: identity where you look for 5 seconds, restraint where you work for 3 hours.**

Deliberately untouched:

- **Every work surface stays neutral by default.** No theming of dialogs, the console, the tree, the inspector, the toolbar, the crumb row, the tab strip. Nothing in this spec touches a pixel outside Home's hero band and the palette registry.
- **`mist` ships OPT-IN and is NEVER the default.** `pick_palette("auto")` still resolves `DARK if detect_os_dark() else LIGHT` (`theme.py:246`). `mist` is reachable only by an explicit choice in Preferences (`shell.py:753-759`). No migration, no first-run prompt, no nag.
- **No icon pass, no dialog pass, no console pass.** `icons.py`'s family is untouched.
- **No new fence, no new test on the neutral palettes.** The other 7 are byte-identical after this change.
- **The gold does not appear anywhere you work.** One band, one screen, one corner. The hero also carries **no accent at all** — gold is the hero's only chroma, Mist is the app's only chroma, **they never meet.**
- **The Home fold / IA problem** — measured, documented above, explicitly out of scope.

Killed by the panel, with the reason:

| killed | reason |
|---|---|
| **Gold on `border`** (Illuminated) | `border` genuinely carries zero fences — it wins the arithmetic and **loses the argument**. It is stroked on all 27 cards, every input, every toolbar: the costume permanently on. Exactly what "cite the game once, in a place you leave" forbids, and exactly what the user's decision forbids. |
| **Draw the ornament in `$focus`** (Mist Line) | Makes the signet **cyan in Mist, blue in Dark, orange in Gruvbox** — the signature changing colour with the weather, the precise negation of the sentence that won. Its own premise (an ornament needs a perceptibility floor) is already better served by the brand constant: **gold measures 4.12–9.02 on `bg` across all 8 palettes**, stronger than 3:1. |
| **A giant versal "IX" in `$accent`** (Vellum) | **`gold/accent` contrast = 1.019** — near-identical luminance; the gold and the cyan smear in greyscale. |
| **The receding plate `log_bg → bg`** (FACET) | Inverts Signet's lifted band (`surface_2 → bg`). Taking it makes a hybrid — the exact failure being fixed. |
| **Brass rivets** (Mist Engine) | A second, competing identity gesture. One corner, once, or it's a costume. |
| **The chroma law as a 22nd test** (Mist Engine) | Measured across all 8: it *holds*. But **Mist's own margin is 1.48× — the thinnest in the tree** (gruvbox 5.40×, dracula 3.70×). A fence whose tightest subject is the palette you're shipping is a trap. It ships as a **documented authoring comment above `MIST`**, not an assertion. |
| **A gold wordmark** | The most predictable move available, and why every FF9 fan project looks the same. The wordmark is `pal["text"]`. |
| **A `trim` token** (round 1) | Referenced by zero QSS rules: renders in zero pixels while taxing all 8 palettes forever. |
| **Bundling a font** (round 1) | Packaging + licence tax. Sitka Banner ships with Windows. |
| **Navy + gold accent** | See §2's three measured grounds. |

---

## The runners-up, and what we took

| rank | direction | pov | ff9 | ship | hours | door | **total** |
|---|---|---|---|---|---|---|---|
| **1** | **Signet** | 9.0 | 8.3 | 8.0 | 8.8 | 8.0 | **42.0** |
| 2 | MIST ENGINE | 9.0 | 8.0 | 8.5 | 8.3 | 7.8 | 41.5 |
| 3 | FACET | 9.0 | 7.3 | 8.8 | 8.5 | 7.8 | 41.3 |
| 4 | Illuminated | 8.8 | 8.0 | 8.5 | 7.8 | 8.0 | 41.0 |
| 5 | Vellum | 9.0 | 7.3 | 7.5 | 8.0 | 8.0 | 39.8 |
| 6 | Mist Line | 8.8 | 6.8 | 8.5 | 8.3 | 7.3 | 39.5 |

**TAKEN — the Sitka Banner wordmark, at weight 400.** Nominated independently by FACET, Mist Engine and Mist Line. Sitka was already in Signet's chain; the graft is the **weight discipline** (400, not the DemiBold-that-silently-becomes-700) and the **correct presence test** (`families()` membership, not `exactMatch()` — FACET's judge verified "exactMatch=True" against the wrong API and would have *rejected* Sitka). Three judges said the serif does more work than the signet, and the render agrees: swap Sitka for Segoe and you lose more than deleting the L. **I'll say plainly what the author wouldn't: the signet is the signature, but Sitka is the voice.** The direction is *stronger* once that's admitted — the front door survives even if a future Windows drops Sitka, because navy + Mist + composition carry it.

**TAKEN — MIST ENGINE's chroma law, as documentation.** Real, holds everywhere, wrong as a fence (see §4). It ships as an authoring comment.

**TAKEN — the panel's two fatal calls.** The arm through the "D" and the duplicate axis formula were both real, both reproduced, both closed. The direction got *more itself* from each.

**REFUSED, all with reasons in §4:** Illuminated's gold `border`, Mist Line's `$focus` ornament, Vellum's accent versal, FACET's receding plate, Mist Engine's rivets.

**OVERRULED — the Qt engineer's "the inner filigree will look cheap at 125%."** Rendered at three DPRs and zoomed 4×. It gets **crisper**. This is the one place the panel is overruled, and it is overruled with pixels.

---

## Build order

Four phases. Each is **independently shippable and revertible**. Nothing later depends on anything earlier except phase 3 on phase 1's `HeroBand`.

### Phase 1 — the palette

**Do:** add the `MIST` dict + the authoring-law comment to `ff9mapkit/ff9mapkit/editor/theme.py` (after `GRUVBOX_DARK`); register in `THEMES` (`theme.py:203`) and `THEME_CHOICES` (`theme.py:214`). **ASCII label: `"Mist (FF9)"`.** Two files touched — actually one.

**Tests:** `py -m pytest tests/test_editor_theme.py tests/test_prefs.py` → **22 passed** (empirically verified). Full GUI surface → **135 passed**. Every contrast/hover/status/derive fence auto-applies because they all iterate `THEMES.items()`. Nothing else in the tree enumerates palettes.

**You will see:** a new **"Mist (FF9)"** entry at the bottom of Preferences → Theme. Pick it and the whole app turns Mist-blue-and-cyan **with live preview**, `retheme` already wired. Every neutral palette is byte-identical. `auto` still resolves Dark/Light.

**Revert:** delete the dict + two lines.

---

### Phase 2 — the stretch fix, alone

**Do:** `shell.py:1438` — `ph.addWidget(body, 4)` → `ph.addWidget(body, 20)`. One character-run.

**Tests:** the workspace smoke (`apps/ff9_workspace.pyw --smoke`). Manual check must use `QT_QPA_PLATFORM=windows` — **`--smoke`/offscreen inflates advances 1.8× and will lie to you** (`widgets.py:243`).

**You will see:** at 1280 default, **nothing** — the body is on its 512px minimum and the stretch isn't binding. At **1600** the column goes 656 → **860** and the gutters close. This phase exists to disarm the trap *before* phase 3 changes the label set.

**Revert:** one character.

---

### Phase 3 — the hero

**Do:** add `ff9mapkit/ff9mapkit/workspace/hero.py` verbatim. Apply wiring edits **(a)** `shell.py:1432-1439`, **(c)** `shell.py:1443-1449` (delete `title` + `_home_status`; **keep `_home_setup`**), **(d)** `shell.py:1671-1681`, **(e)** `shell.py:462` + `shell.py:526` + `shell.py:535`.

**Tests:**
- workspace smoke — Home constructs, no exception on an unparented `_axis()`.
- **axis regression:** assert `hero._axis()[0] == body.mapTo(win, body.rect().topLeft()).x() - hero.mapTo(win, hero.rect().topLeft()).x()` at viewports 724 / 844 / 1044 / 1244 / 1444 / 2000. Under `QT_QPA_PLATFORM=windows` + `WA_DontShowOnScreen`, `LOCALAPPDATA` redirected to an empty temp dir (`_restore_layout` at `shell.py:6575` otherwise applies a persisted geometry and the numbers are whatever the user last dragged).
- **paint regression:** grab the hero, assert top-left pixel ≠ `pal["bg"]` (proves the `style.py:81` bypass) and that the page 40px below **is** `pal["bg"]`.
- **font regression:** `hero.wordmark_face()` returns a member of `QFontDatabase.families()`. Do **not** assert it equals `"Sitka Banner"` — the chain must be free to fall through on a machine without it.
- **retheme regression:** switch palette while Home is showing; assert the status text is present and the band repaints. (This also fixes the pre-existing inline-hex staleness bug — `_home_status` went stale on a live theme switch until you left Home and came back.)

**You will see:** Home opens on a **full-bleed 156px band**. `FF9 FIELD TOOLKIT · 1.0.0b15` in 11px tracked caps. **"Dream World IX"** at 40px Sitka Banner, weight 400, in parchment `#e9e6dc` — a title page, not a heading. An off-centre pale bloom behind it. A **1px gold rule** rising from the left gutter past the overline, turning a 6px corner, running out flat under the wordmark and **dissolving to alpha 70** in open air; a doubled inner stroke at the elbow; a 7px gold diamond at the top of the arm. The wordmark, the elbow and **every card below** on one axis at every window width. The band's gold is **the same gold on Dark, on Nord, on Gruvbox, on Mist** — and `#8a6a1f` on the two light palettes. Toggle Compact: the band goes 156 → 136 and everything re-lays.

**Revert:** delete `hero.py`, restore the five hunks.

---

### Phase 4 — the record

**Do:** write this file to `studies/gui-aesthetics/IDENTITY.md`. Add one line to `CLAUDE.md` §10 Milestones. **Do not** touch `RELEASE_NOTES_1.0.0b10.md:15` ("seven" themes — correctly frozen). `docs/FEATURES.md:185` says only "themes" — no change needed.

**You will see:** the reason the app looks like this, on disk, next time.

---

## Three things I am handing you honestly, not papering over

1. **The signet is not "the entire identity."** Sitka at 400 on navy does most of the work. If you cut something, cut the inner filigree — not the serif.

2. **Mist is FF9 by argument more than by sight.** The one palette permitted to be FF9 carries gold in **zero** tokens. The arithmetic makes that the right trade (I reproduced the `#35393f` mud), but it means the opt-in theme is Nord-adjacent navy+cyan, and a user expecting blue-and-gold menus will notice. **Ship it anyway** — a working palette that lies about nothing beats a themed one you disable in a week.

3. **The one thing I could not measure is whether you like it.** I rendered it and I do — it reads as a title page, which is the right register for a toolkit whose subject is a storybook JRPG. But "is that it?" is a verdict only you can return. **If it lands thin, raise `_MIST_ALPHA` before adding a second gold element.** One corner, once, or it's a costume.
