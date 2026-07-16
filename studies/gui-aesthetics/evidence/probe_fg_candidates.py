"""SPEND -- the ink candidates for the two grounds nobody ever authored (`warn`, `help`).

WHAT probe_fg_rule.py SETTLED, AND WHY IT CHANGES THIS ONE. A single argmax rule reproduces only 5 of the
8 authored `accent_fg` values. Where it misses (dracula / gruvbox-dark / mist) it picks a HIGHER-contrast
ink than the author did -- 6.55 vs 5.90, 6.49 vs 5.84, 9.75 vs 9.43. So the misses are not the authors
settling; they are the authors CHOOSING, from their own palette's vocabulary (dracula's `#282a36` and
gruvbox's `#282828` are those projects' signature backgrounds). => `accent_fg` is authored taste. Derive
nothing there; spend the token that exists.

`warn` and `help` are different: NOBODY EVER CHOSE. There is no taste to overwrite, only a hole to fill --
so a derivation is honest here in a way it would not be one ground over.

This probe does not pick. It lays out every candidate for both grounds in all 8 palettes so the choice is
made against numbers. The candidate set is drawn from what the palettes already contain (in-family) plus
the two extremes (which always bound the achievable contrast):

    #ffffff      pure white -- what the chip hardcodes today
    log_bg       the palette's own deepest ink -- what dark + solarized-dark chose for accent_fg
    bg           the page -- what dracula + gruvbox chose for accent_fg
    text         the palette's body ink
    #000000      pure black -- "an imported black", which `dark`'s own comment argues against

AA 4.5 is the bar: the chip is 12px/600 and the help glyph is 14px/bold. 600 weight does NOT buy the
large-text bar (that needs 18.66px bold), so both are NORMAL text.

Run:  py studies/gui-aesthetics/evidence/probe_fg_candidates.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ff9mapkit"))

from ff9mapkit.editor import theme  # noqa: E402

AA = 4.5


def _lum(hexstr: str) -> float:
    h = hexstr.lstrip("#")
    ch = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


CANDS = ("#ffffff", "log_bg", "bg", "text", "#000000")


def ink_of(pal: dict, cand: str) -> str:
    return cand if cand.startswith("#") else pal[cand]


def main() -> int:
    for ground in ("warn", "help"):
        print(f"\n{'=' * 78}\n=== FILL = ${ground}\n")
        head = "    {:<16} {:<9}".format("palette", "fill") + "".join(f"{c:>10}" for c in CANDS)
        print(head)
        for name in theme.THEMES:
            pal = theme.derive(dict(theme.THEMES[name]))
            fill = pal[ground]
            cells = []
            for c in CANDS:
                r = contrast(ink_of(pal, c), fill)
                cells.append(f"{r:>9.2f}{'*' if r >= AA else ' '}")
            print(f"    {name:<16} {fill:<9}" + "".join(cells))
        print("\n    (* = clears AA 4.5)")

        # How many palettes does each single candidate clear, used alone?
        print(f"\n    clears-AA count per candidate, used as a UNIVERSAL rule for ${ground}:")
        for c in CANDS:
            n = sum(contrast(ink_of(theme.derive(dict(theme.THEMES[m])), c),
                             theme.derive(dict(theme.THEMES[m]))[ground]) >= AA
                    for m in theme.THEMES)
            print(f"        {c:<10} {n}/8")

        # in-family deep ink, and only fall back to an imported black where the family cannot carry it
        print(f"\n    RULE: prefer log_bg (in-family); if it misses AA, take the better extreme:")
        for name in theme.THEMES:
            pal = theme.derive(dict(theme.THEMES[name]))
            fill = pal[ground]
            deep = pal["log_bg"]
            if contrast(deep, fill) >= AA:
                pick, why = deep, "log_bg (in-family)"
            else:
                pick = max(("#ffffff", "#000000"), key=lambda c: contrast(c, fill))
                why = "extreme (family cannot carry it)"
            print(f"        {name:<16} {fill} -> {pick}  {contrast(pick, fill):>6.2f}  {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
