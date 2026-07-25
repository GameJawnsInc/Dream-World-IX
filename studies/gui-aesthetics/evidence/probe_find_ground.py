"""What ground can a FIND HIGHLIGHT paint in the console well, in all 8 palettes?

A find highlight is a FILL PAINTED UNDER LOG TEXT. By this study's NINTH-GROUND LAW that voids every
`log_fg`/`log_bg` guarantee on that band: `test_palette_contrast_invariants` fences
`contrast(log_fg, log_bg) >= 4.5`, and a highlight is neither of those colours. So the two tiers a find
bar needs (ALL matches, quiet; the CURRENT match, loud) each need their own ground AND their own ink,
measured -- not `selection_bg` reused on faith.

WHY `selection_bg` IS THE WRONG TOKEN, and this is the whole reason the probe exists: it is derived
against `surface`/`hover` (`_selection_token`) -- the TREE's ground. The console's ground is `log_bg`, a
different and DEEPER fill in every palette. Reusing it would be the study's most-repeated defect: a fence
set on the wrong ground.

Two questions, two metrics, per REGISTER P1 (*a contrast ratio is luminance-only and blind to the axis a
coloured fill uses*):
  1. Is the fill VISIBLE against the well?          -> raw channel distance from `log_bg` (a tint event)
  2. Is the CURRENT match distinct from the others? -> raw channel distance between the two fills
  3. Is the log text still legible ON the fill?     -> CONTRAST (that one really is a text question), 4.5

Run:  py studies/gui-aesthetics/evidence/probe_find_ground.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ff9mapkit"))

from ff9mapkit.editor import theme  # noqa: E402


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def dist(a, b):
    """Max raw channel distance -- the metric `_selection_token` uses (>=20/255), not a ratio."""
    return max(abs(x - y) for x, y in zip(rgb(a), rgb(b)))


def mix(a, b, t):
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(rgb(a), rgb(b)))


def lum(h):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


print("=" * 108)
print("Q1/Q3  THE LOUD TIER -- can the CURRENT match just be the accent fill with its AUTHORED ink?")
print("=" * 108)
print(f"{'palette':17} {'log_bg':9} {'accent':9} {'accent_fg':9} {'d(acc,well)':>12} {'c(fg,acc)':>10} {'c(log_fg,acc)':>14}")
for mode, pal in theme.THEMES.items():
    d = theme.derive(dict(pal))
    print(f"{mode:17} {pal['log_bg']:9} {pal['accent']:9} {pal['accent_fg']:9} "
          f"{dist(pal['accent'], pal['log_bg']):12d} {contrast(pal['accent_fg'], pal['accent']):10.2f} "
          f"{contrast(pal['log_fg'], pal['accent']):14.2f}")
print("\n  d(acc,well) = is the loud fill visible in the well.  c(fg,acc) = the AUTHORED ink on it (already")
print("  fenced >=4.5 by test_a_filled_ground_carries_its_ink).  c(log_fg,acc) = what happens if the")
print("  highlight sets NO ink and lets the log's own body colour ride the accent -- the naive build.")

print()
print("=" * 108)
print("Q2  THE QUIET TIER -- a tint of the WELL toward the accent. Which t clears both floors?")
print("=" * 108)
print("  floors: d(fill,well) >= 20  (visible against the well, _selection_token's metric)")
print("          d(acc,fill)  >= 20  (still distinct from the CURRENT match)")
print("          c(ink,fill)  >= 4.5 (log text legible on it -- the ninth-ground debt)")
print()
hdr = f"{'palette':17}" + "".join(f"{('t=%.2f' % t):>14}" for t in (0.20, 0.30, 0.40, 0.50))
print(hdr)
for mode, pal in theme.THEMES.items():
    cells = []
    for t in (0.20, 0.30, 0.40, 0.50):
        f = mix(pal["log_bg"], pal["accent"], t)
        cells.append(f"{f} {dist(f, pal['log_bg']):3d}/{dist(pal['accent'], f):3d}")
    print(f"{mode:17}" + "".join(f"{c:>14}" for c in cells))
print("\n  each cell: fill  d(fill,well)/d(accent,fill)")

print()
print("=" * 108)
print("Q3  ...and the INK on the quiet tier, per palette, at the t that first clears d>=20")
print("=" * 108)
print(f"{'palette':17} {'t':>5} {'fill':9} {'d(well)':>8} {'d(acc)':>7} "
      f"{'c(log_fg)':>10} {'c(_fg_token)':>13} {'_fg_token':9}")
for mode, pal in theme.THEMES.items():
    t, f = None, None
    for cand in [i / 100 for i in range(4, 101, 2)]:
        f = mix(pal["log_bg"], pal["accent"], cand)
        if dist(f, pal["log_bg"]) >= 20:
            t = cand
            break
    ink = theme._fg_token(f, dict(pal))
    print(f"{mode:17} {t:5.2f} {f:9} {dist(f, pal['log_bg']):8d} {dist(pal['accent'], f):7d} "
          f"{contrast(pal['log_fg'], f):10.2f} {contrast(ink, f):13.2f} {ink:9}")
print("\n  c(log_fg) = leave the ink alone and the log's own body colour rides the tint.")
print("  c(_fg_token) = the existing derived-ink rule (`_fg_token`, fenced >=4.5) applied to this fill.")
