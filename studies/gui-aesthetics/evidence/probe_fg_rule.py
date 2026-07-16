"""SPEND -- can a RULE reproduce the eight hand-authored `accent_fg` values?

WHY THIS PROBE EXISTS. `warn` and `help` are filled grounds that carry text and have no authored ink
partner, so one has to come from somewhere. Two ways to get it:

  (a) hand-pick 8 more hexes  -- taxes the palette keyset, and my taste is not the 8 authors' taste;
  (b) derive it              -- but a derivation I invent is a guess wearing a formula.

So: test (b) against the ONE ground that already has 8 hand-authored answers. If a rule reproduces
`accent_fg` in all 8 palettes, it is not my taste -- it is the authors' taste, made explicit, and it can
be extended to `warn`/`help` with earned confidence. If it does NOT reproduce, the rule is wrong and this
probe says so out loud rather than shipping a plausible formula.

This is PLINTH's gate again, verbatim (STATE.md round 5 part 3): *"reproduce the shipped tuples, or show
a render of the delta and let your eye decide -- a formula that 'cleans them up' is a regression wearing a
refactor."*

THE HYPOTHESIS comes from reading what the authors WROTE, not from a preference of mine. Three palettes
say it in their own comments:
    dark            "#181b20 is this palette's OWN log_bg -- in-family, not an imported black."
    solarized-dark  "base03-deep ink (this palette's own log_bg)"
    mist            "dark ink on a light accent (the dracula/gruvbox strategy)"
=> H: accent_fg == whichever of {#ffffff, pal['log_bg']} has more contrast against the fill.

Run:  py studies/gui-aesthetics/evidence/probe_fg_rule.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ff9mapkit"))

from ff9mapkit.editor import theme  # noqa: E402


def _lum(hexstr: str) -> float:
    h = hexstr.lstrip("#")
    ch = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def rule(fill: str, pal: dict) -> str:
    """H: white, or the palette's own deep log ink -- whichever the fill can actually carry."""
    cands = ("#ffffff", pal["log_bg"])
    return max(cands, key=lambda c: contrast(c, fill))


def main() -> int:
    print("=== H: accent_fg == argmax(contrast) over {#ffffff, log_bg}, tested on the AUTHORED values\n")
    print(f"    {'palette':<16} {'accent':<9} {'authored':<9} {'rule says':<9} {'':<3} "
          f"{'auth r':>6} {'rule r':>6}")
    hits = 0
    for name in theme.THEMES:
        pal = theme.derive(dict(theme.THEMES[name]))
        got = rule(pal["accent"], pal)
        auth = pal["accent_fg"]
        same = got.lower() == auth.lower()
        hits += same
        print(f"    {name:<16} {pal['accent']:<9} {auth:<9} {got:<9} {'==' if same else '!!':<3} "
             f"{contrast(auth, pal['accent']):>6.2f} {contrast(got, pal['accent']):>6.2f}")
    print(f"\n    REPRODUCED: {hits}/8")
    if hits != 8:
        print("    -> H IS FALSE. Do not ship this rule; the authored values know something it does not.")

    # Even where the hex differs, does the rule still clear the bar the authored value clears?
    print("\n=== does the rule meet AA 4.5 on every ground that needs an ink?\n")
    for key in ("accent", "warn", "help", "success", "error"):
        print(f"    --- fill = ${key}")
        worst = 99.0
        for name in theme.THEMES:
            pal = theme.derive(dict(theme.THEMES[name]))
            ink = rule(pal[key], pal)
            r = contrast(ink, pal[key])
            worst = min(worst, r)
            flag = "" if r >= 4.5 else "   <-- SUB-AA, the rule alone is not enough"
            print(f"        {name:<16} {pal[key]:<9} -> {ink:<9} {r:>6.2f}{flag}")
        print(f"        worst = {worst:.2f}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
