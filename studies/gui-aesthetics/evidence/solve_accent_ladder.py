"""THE ACCENT LADDER -- the search that produced each palette's accent_hover / accent_pressed.

THE DEFECT. `QPushButton#accent` sets `color: $accent_fg` ONCE, and its :hover / :pressed rules swap the
FILL beneath the same ink. `accent_fg` was fenced at 4.5 against `$accent` ALONE, so the two state fills
were never checked against the ink riding on them: 3.48 (nord hover), 3.56 (solarized-dark pressed). The
app's PRIMARY VERB -- "the ONE accent object" -- sub-AA the moment you touch it, in 3 of 8 palettes.

WHY THE FILL MOVES AND NOT THE INK. Both alternatives were measured and both are worse:
  * ONE INK FOR ALL THREE IS IMPOSSIBLE. Black and white BOUND every possible ink, and BOTH fail in 4 of
    8: dark 4.44, nord 4.24, solarized-dark 4.45, solarized-light 4.37. The ladder spans hover-LIGHTER ->
    accent -> pressed-DARKER across the mid-luminance dead zone, so its two ends favour OPPOSITE extremes.
  * A PER-STATE INK reaches AA and FLIPS: 219-243/255 channel shift between rest and pressed (dark's label
    would be near-black at rest and near-WHITE held). A label that changes colour as you touch it.

WHY DERIVING THE FILLS IS HONEST WHERE DERIVING `accent_fg` WAS NOT -- the sibling question, asked the same
way and answered the other way. A best-fit `_mix(accent, white|black, t)` reproduces every SHIPPED state
fill to within **8/255 (hover) and 11/255 (pressed)**: they are mechanical tonal steps, so a rule
formalises what is already there. `accent_fg` reproduced only **5 of 8**, and where it missed it chose MORE
contrast than the author had (dracula's `#282a36`, gruvbox's `#282828` -- those projects' signature
backgrounds). So accent_fg stays authored, and these are computed.

WHY THE OUTPUT IS PASTED INTO THE PALETTES RATHER THAN COMPUTED AT RUNTIME. `derive()` has a contract and
its own fence: *"derive() changed a base value"* -- it EXTENDS, it never mutates. accent_hover/accent_pressed
are BASE keys, so a derive()-time override is a contract violation (and the fence caught it). Authored
values + a fence is exactly how accent_fg already works, and it costs no runtime search.

THREE PALETTES CHANGE THE DIRECTION OF A STEP, and that is FORCED, not chosen: `dark`'s band below the
accent is 0.054 wide, and holding BOTH steps darker while keeping press/hover >= 1.1821 is provably
infeasible there. Where a direction must go, the search takes the cheapest legal ladder in channel distance
from what shipped.

Run:  py studies/gui-aesthetics/evidence/solve_accent_ladder.py        (prints the paste-ready hexes)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ff9mapkit"))

from ff9mapkit.editor import theme  # noqa: E402
from ff9mapkit.editor.theme import _mix  # noqa: E402

AA = 4.5


def lum(h):
    h = h.lstrip("#")
    ch = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def con(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def chan(a, b):
    a, b = a.lstrip("#"), b.lstrip("#")
    return max(abs(int(a[i:i + 2], 16) - int(b[i:i + 2], 16)) for i in (0, 2, 4))


def steps(base):
    out = [base]
    for t in ("#ffffff", "#000000"):
        out += [_mix(base, t, i / 100) for i in range(1, 70)]
    return out


def solve(accent, ink, hover, pressed):
    f_h, f_p, f_ph = theme._ACCENT_FEEDBACK
    band = [c for c in steps(accent) if con(ink, c) >= AA]
    best, cost = None, 1 << 30
    for h in band:
        if con(h, accent) < f_h:
            continue
        dh = chan(h, hover)
        if dh >= cost:
            continue
        for d in band:
            if con(d, accent) < f_p or con(d, h) < f_ph:
                continue
            c = dh + chan(d, pressed)
            if c < cost:
                best, cost = (h, d), c
    return best


def main() -> int:
    print("=== the ladder, solved: ink FIXED, band 4.5, feedback floors "
          f"{theme._ACCENT_FEEDBACK}\n")
    print(f"  {'palette':<16} {'accent':<9} {'hover':<20} {'pressed':<20} {'worst':>6}")
    out = {}
    for n in theme.THEMES:
        p = theme.derive(dict(theme.THEMES[n]))
        got = solve(p["accent"], p["accent_fg"], p["accent_hover"], p["accent_pressed"])
        assert got, f"{n}: NO legible ladder exists -- the ink cannot carry any in-family step"
        h, d = got
        out[n] = (h, d)
        worst = min(con(p["accent_fg"], x) for x in (p["accent"], h, d))
        dirn = ("lighter" if lum(h) > lum(p["accent"]) else "darker",
                "lighter" if lum(d) > lum(p["accent"]) else "darker")
        was = ("lighter" if lum(p["accent_hover"]) > lum(p["accent"]) else "darker",
               "lighter" if lum(p["accent_pressed"]) > lum(p["accent"]) else "darker")
        flip = "  <- DIRECTION FLIPPED" if dirn != was else ""
        print(f"  {n:<16} {p['accent']:<9} {p['accent_hover']}->{h} ({chan(h, p['accent_hover']):>3})  "
              f"{p['accent_pressed']}->{d} ({chan(d, p['accent_pressed']):>3})  {worst:>6.2f}{flip}")

    print("\n=== paste-ready\n")
    for n, (h, d) in out.items():
        print(f'  {n:<16} "accent_hover": "{h}",   "accent_pressed": "{d}",')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
