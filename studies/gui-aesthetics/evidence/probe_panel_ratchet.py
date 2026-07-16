"""THE PANELS ARE NARROW: is the DEFAULT wrong, or is the default never reached?

The user's saved layout is `central_split: [76, 1138, 64]` -- nothing like the coded default
`[300, 640, 240]`, and far below anything a hand would drag to. Before widening a number, find out whether
the number is even spent. Two candidate mechanisms, and they want opposite fixes:

  A. THE DEFAULT IS TOO SMALL         -> widen [300, 640, 240].
  B. THE DEFAULT IS NEVER HONOURED    -> widening it changes NOTHING, and each session SAVES the squeezed
     result, so the panes ratchet down forever. `setSizes()` on a splitter that has not been laid out yet
     is clamped to its CURRENT width; then `setStretchFactor(1, 1)` hands every later pixel of growth to
     the middle pane, so the outer two are frozen at whatever the clamp left them.

This probe answers it by asking the splitter what it actually did, at cold start, with no saved layout.

TWO HARNESS LAWS THIS ROUND ALREADY PAID FOR:
  * AN EMPTY TEMPDIR IS NOT A CLEAN ROOM. Pointing LOCALAPPDATA at an empty dir makes prefs.text_scale()
    fall through to os_text_scale() -- the DEVELOPER'S Windows slider. So we WRITE a prefs.json and PIN
    the scale, and sweep all four rungs.
  * OFFSCREEN LIES ABOUT WIDTH. Its stub font DB (~14px/char) drives minimumSizeHint, which is exactly
    what a clamp reads. So the ABSOLUTE numbers here are suspect and only the MECHANISM (is the request
    honoured? does saving ratchet?) is trustworthy offscreen. Final numbers want the real platform.

Run:  py studies/gui-aesthetics/evidence/probe_panel_ratchet.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "ff9mapkit"
sys.path.insert(0, str(ROOT))

_TMP = tempfile.mkdtemp(prefix="ff9probe_")
os.environ["LOCALAPPDATA"] = _TMP
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

CFG = Path(_TMP) / "ff9mapkit" / "config"
CFG.mkdir(parents=True, exist_ok=True)


def _seed(scale: int, layout: dict | None) -> None:
    """A POPULATED prefs.json -- never an empty dir. text_scale is PINNED so no OS slider leaks in."""
    d: dict = {"theme": "dark", "text_scale": scale}
    if layout is not None:
        d["layout"] = layout
    (CFG / "prefs.json").write_text(json.dumps(d), encoding="utf-8")


def main() -> int:
    _seed(100, None)
    from PySide6.QtWidgets import QApplication

    from ff9mapkit import prefs
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.shell import Workspace

    app = QApplication.instance() or QApplication([])
    app.setStyle("fusion")

    print(__doc__.split("Run:")[0])
    print(f"  probe config: {CFG}\n")

    DEFAULT = [300, 640, 240]
    print("=== A. IS THE DEFAULT HONOURED AT COLD START? (no saved layout)\n")
    print(f"  {'scale':>6} {'window':>7}  {'requested':<18} {'actual':<20} {'verdict'}")
    ratchet_seed = None
    for scale in (100, 110, 125, 150):
        _seed(scale, None)
        prefs.load.cache_clear() if hasattr(prefs.load, "cache_clear") else None
        assert prefs.text_scale() == scale, f"scale not pinned: {prefs.text_scale()} != {scale}"
        w = Workspace(pick_palette("dark"))
        w.resize(1280, 820)
        w.show()
        app.processEvents()
        got = w._central_split.sizes()
        ok = abs(got[0] - DEFAULT[0]) <= 2 and abs(got[2] - DEFAULT[2]) <= 2
        print(f"  {scale:>5}% {1280:>7}  {str(DEFAULT):<18} {str(got):<20} "
              f"{'honoured' if ok else 'SQUEEZED -> the default is never spent'}")
        if scale == 100:
            ratchet_seed = got
        w.close()

    print("\n=== B. DOES A SESSION SAVE THE SQUEEZE? (the ratchet)\n")
    _seed(100, None)
    w = Workspace(pick_palette("dark"))
    w.resize(1280, 820)
    w.show()
    app.processEvents()
    gen = [list(w._central_split.sizes())]
    w._save_layout()
    w.close()
    for _ in range(3):
        w = Workspace(pick_palette("dark"))
        w.resize(1280, 820)
        w.show()
        app.processEvents()
        gen.append(list(w._central_split.sizes()))
        w._save_layout()
        w.close()
    for i, g in enumerate(gen):
        print(f"  session {i}: {g}")
    shrank = gen[-1][0] < gen[0][0] or gen[-1][2] < gen[0][2]
    print(f"\n  outer panes {'RATCHET DOWN across sessions' if shrank else 'are stable across sessions'}")

    print(f"\n  (user's real saved layout for reference: [76, 1138, 64]; cold start here: {ratchet_seed})")
    print("\n  NOTE: offscreen -- MECHANISM only. Absolute px want the real platform.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
