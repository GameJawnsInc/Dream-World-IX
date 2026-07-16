"""SPEND -- the proposed `_fg_token`, the hexes it emits, and the trap that killed version 1.

=============================================================================================
THE TRAP, RECORDED BECAUSE IT IS GENERAL AND MY FIRST VERSION SHIPPED IT
=============================================================================================
v1 was: start at `log_bg`, walk toward the winning extreme until AA -- a straight copy of `_text_token`.
It ASSERTED ITSELF SUB-AA on solarized-light: started at 3.56, ended at **3.42**, WORSE than where it
began, after 40 steps.

Why: solarized-light's log ink is a CREAM and its `warn` is a mid GOLD. Walking cream toward black must
cross the gold's own luminance, so contrast collapses toward 1.0 and only then climbs. The walk is a
valley, not a ramp.

    A WALK TOWARD AN EXTREME IS MONOTONIC ONLY IF YOU START ON THAT EXTREME'S SIDE OF THE GROUND.

`_text_token` and `_focus_token` are safe from this by accident of their inputs, not by construction: they
pick the ink direction from the MODE and every ground they touch (bg/surface/surface_2) is on the mode's
side. A saturated FILL has arbitrary luminance, so that guarantee evaporates -- and nothing in the file
says so, because nothing had needed it to.

v2 chooses the START by side, not by name. Then the walk is monotonic by construction.

=============================================================================================
WHAT THE MEASUREMENTS FORCED (none of this is a preference)
=============================================================================================
* `target` = argmax(contrast) over {#ffffff, #000000}, PER FILL, never per mode. Falsified alternatives:
  `nord` is a DARK palette whose accent takes WHITE ink; `light` (#9a6b00) and `solarized-light`
  (#a47c00) want OPPOSITE inks on the SAME `warn` semantic -- light fails on black at 4.48,
  solarized-light fails on white at 3.85. Any mode-based rule is dead on arrival.

* The start is in-family. `accent_fg`'s authors said why in their own words: *"this palette's OWN log_bg
  -- in-family, not an imported black."* `log_bg` and `text` are the palette's two authored extremes and
  always sit opposite each other, so at least one lies on any achievable side.

* solarized-light's `warn` is the hard case and it is REAL, not an artefact: **not one of that palette's
  35 hexes clears AA on it** (best = #ffffff at 3.85). Its luminance is 0.223 -- landing almost exactly on
  the **0.220 crossover** `dark`'s own accent_fg comment names as where dark ink starts beating white. The
  palette's `text` (#4a6067) is darker than the fill, so it IS on black's side: the walk starts there and
  stays in-family instead of importing a black.

* `accent` is NOT derived here and must not be. probe_fg_rule.py reproduced only 5/8 of the authored
  `accent_fg` values, and where it missed it picked HIGHER contrast than the author chose (6.55 vs 5.90 on
  dracula, 6.49 vs 5.84 on gruvbox, 9.75 vs 9.43 on mist) -- dracula's `#282a36` and gruvbox's `#282828`
  are those projects' signature backgrounds. That is taste, and a formula must not overwrite it.

Run:  py studies/gui-aesthetics/evidence/probe_fg_token.py
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


def fg_token(fill: str, pal: dict) -> tuple:
    """v2. Returns (ink, steps, start) so the probe can report AUTHORED-verbatim vs WALKED."""
    target = max(("#ffffff", "#000000"), key=lambda c: contrast(c, fill))
    up = _lum(target) > _lum(fill)                       # the direction that can actually win
    # the palette's own two extremes, kept only if they lie on the achievable side
    side = [c for c in (pal["log_bg"], pal["text"]) if (_lum(c) > _lum(fill)) == up]
    start = max(side, key=lambda c: contrast(c, fill)) if side else target
    out = start
    for i in range(40):
        if contrast(out, fill) >= AA:
            return out, i, start
        out = theme._mix(out, target, 0.04)
    return out, 40, start


def main() -> int:
    walked = []
    for ground in ("warn", "help"):
        print(f"\n=== ${ground}_fg\n")
        print(f"    {'palette':<16} {'fill':<9} {'start':<9} {'-> ink':<9} {'ratio':>6} {'steps':>5}  origin")
        for name in theme.THEMES:
            pal = theme.derive(dict(theme.THEMES[name]))
            fill = pal[ground]
            ink, steps, start = fg_token(fill, pal)
            r = contrast(ink, fill)
            which = "log_bg" if start == pal["log_bg"] else ("text" if start == pal["text"] else "EXTREME")
            origin = f"{which} verbatim" if steps == 0 else f"{which} walked {steps} -- LOOK AT IT"
            if steps:
                walked.append((ground, name, fill, start, ink, r, steps))
            assert r >= AA, f"{name}: {ground}_fg landed sub-AA at {r:.2f}"
            print(f"    {name:<16} {fill:<9} {start:<9} {ink:<9} {r:>6.2f} {steps:>5}  {origin}")

    print("\n" + "=" * 82)
    print("MONOTONICITY -- v1's actual bug. Contrast must never DIP below its start along the walk.")
    print("(This check REPLAYS the real walk. My first version compared against _mix(start, target,")
    print(" 0.04*i) -- a LINEAR interpolation -- but the walk re-mixes its own output, which converges")
    print(" exponentially and never reaches t=1. That formula crashed at i=40 (t=1.6 -> a negative")
    print(" channel -> int('0-', 16)) and flagged warn/light non-monotonic on the way. Both were the")
    print(" instrument, not the token: A CHECK THAT DOES NOT REPLAY THE CODE IS CHECKING SOMETHING ELSE.")
    bad = 0
    for ground in ("warn", "help"):
        for name in theme.THEMES:
            pal = theme.derive(dict(theme.THEMES[name]))
            fill = pal[ground]
            _, _, start = fg_token(fill, pal)
            target = max(("#ffffff", "#000000"), key=lambda c: contrast(c, fill))
            series, out = [], start
            for _ in range(41):                       # the real walk, step for step
                series.append(contrast(out, fill))
                out = theme._mix(out, target, 0.04)
            if any(b < a - 1e-9 for a, b in zip(series, series[1:])):
                bad += 1
                print(f"    NON-MONOTONIC: {ground}/{name}  {series[0]:.2f} -> min {min(series):.2f}")
    print(f"    {16 - bad}/16 monotonic" + ("  <- v2 holds" if not bad else "  <- STILL BROKEN"))

    print("\n  v1 REGRESSION -- prove the trap is real and that v2 is what fixes it:")
    pal = theme.derive(dict(theme.THEMES["solarized-light"]))
    fill = pal["warn"]
    out, series = pal["log_bg"], []                   # v1: ALWAYS start at log_bg
    for _ in range(41):
        series.append(contrast(out, fill))
        out = theme._mix(out, "#000000", 0.04)
    print(f"    v1 start {series[0]:.2f} -> dips to {min(series):.2f} -> ends {series[-1]:.2f} "
          f"(40 steps, never reaches AA)")
    v2, steps, start = fg_token(fill, pal)
    print(f"    v2 starts on the achievable side ({start}) -> {v2} at {contrast(v2, fill):.2f} "
          f"in {steps} steps")

    print("\n" + "=" * 82)
    if walked:
        print("VALUES NOBODY AUTHORED (the walk ran) -- these need an EYE, not an assertion:\n")
        for g, n, fill, start, ink, r, steps in walked:
            print(f"    {g}_fg / {n}:  fill {fill}  start {start}  -> {ink}   ({r:.2f}, {steps} steps)")
        print("\n    ^ render these before believing them. A formula that clears 4.5 can still be muddy;")
        print("      this study's FORM LESSON is that statistics reproduce measured properties, not looks.")
    else:
        print("Every value is an authored hex, verbatim. The walk never ran.")

    print("\nSTABILITY: derive() is called defensively on already-derived dicts.")
    for ground in ("warn", "help"):
        for name in theme.THEMES:
            pal = theme.derive(dict(theme.THEMES[name]))
            a, _, _ = fg_token(pal[ground], pal)
            b, _, _ = fg_token(pal[ground], {**pal, f"{ground}_fg": a})
            assert a == b, f"{name}/{ground}: not stable ({a} -> {b})"
    print("    stable 16/16 (reads only `fill`, `log_bg`, `text` -- never its own output)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
