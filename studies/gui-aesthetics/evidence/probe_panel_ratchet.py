"""THE PANELS ARE NARROW -- and the record of how the INSTRUMENT answered wrongly, twice, before the app
answered at all.

⚠ READ THIS FIRST: THIS PROBE'S ORIGINAL VERDICT WAS FALSE. It is kept because being wrong is the point.

THE REPORT: "the default sizes of the left and right panels are very small... as a default they need to be
wider." The user's saved layout was `central_split: [76, 1138, 64]` -- nothing like the coded default
`[300, 640, 240]`, and far below anything a hand would drag to.

WHAT THIS PROBE SAID (offscreen), and it is a LIE:
    100%  requested [300, 640, 240]  actual [74, 1156, 66]   "SQUEEZED -> the default is never spent"
It concluded `mid_col`'s minimum is **1156**, so the default could never fit and the fix was a
splitter-timing bug. I had that fix designed before I checked it.

WHAT THE REAL PLATFORM SAYS:
    100%  requested [300, 640, 240]  actual [300, 738, 240]   the default IS honoured
    mid_col minimumSizeHint = 542 (100%) / 575 / 685 / 796 (150%)   -- NOT 1156
**offscreen's stub font DB (~14px/char) inflates every minimumSizeHint, and a clamp READS minimums.** This
is the same artifact that manufactured a fake 1296px window floor in round 6, wearing a different hat.
LAW: OFFSCREEN LIES ABOUT WIDTH. Colour is font-independent and safe offscreen; width is a rumour.

THE SECOND WRONG ANSWER -- the one that matters more, because the probe was clean and still wrong. An
in-session resize sweep FALSIFIED the ratchet:
    1280 -> 700 (squeezes to [90, 542, 66]) -> 1920  recovers to [300, 1378, 240], perfectly.
It genuinely does. A LIVE splitter still holds its original `setSizes()` request and re-derives from it on
every resize. **The defect needs a RESTART to destroy that memory**, and a probe that resizes inside one
session can never see it:
    seed [90, 542, 66] -> relaunch at 1280 -> [90, 1122, 66]     the panels never come back
LAW: A PROBE THAT CANNOT REPRODUCE THE LIFECYCLE CANNOT FALSIFY A LIFECYCLE BUG.

THE ACTUAL BUG (and see `_repair_central_split` in workspace/shell.py): the document column has a hard
minimum, so a too-narrow window can only take width from the OUTER panes, which clamp to their minimums
(78/66). `_save_layout` persisted that clamp AS A PREFERENCE; `setStretchFactor(1, 1)` then handed the whole
surplus to the middle pane on the next launch. One narrow session, ever, was permanent -- and the user had
never seen the real default at all.
LAW: A SQUEEZE IS NOT A PREFERENCE. A value the app COMPUTED UNDER DURESS is not a value the user CHOSE.

HARNESS LAWS THIS ARC ALREADY PAID FOR, still in force below:
  * AN EMPTY TEMPDIR IS NOT A CLEAN ROOM -- pointing LOCALAPPDATA at one makes prefs.text_scale() fall
    through to os_text_scale(), i.e. the DEVELOPER'S Windows slider. So we WRITE a prefs.json and PIN the
    scale, and sweep all four rungs.

Run:  py studies/gui-aesthetics/evidence/probe_panel_ratchet.py            (offscreen -- prints the LIE)
      set QT_QPA_PLATFORM= & py studies/gui-aesthetics/evidence/probe_panel_ratchet.py     (the truth)
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
# NOTE: deliberately NOT forced. Default to offscreen (so the suite's platform is reproduced and the lie is
# visible), but honour an explicit empty QT_QPA_PLATFORM so the real platform can be measured.
if "QT_QPA_PLATFORM" not in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
_OFFSCREEN = os.environ.get("QT_QPA_PLATFORM") == "offscreen"

CFG = Path(_TMP) / "ff9mapkit" / "config"
CFG.mkdir(parents=True, exist_ok=True)


def _seed(scale: int, layout: list | None = None) -> None:
    """A POPULATED prefs.json -- never an empty dir. text_scale is PINNED so no OS slider leaks in."""
    d: dict = {"theme": "dark", "text_scale": scale}
    if layout is not None:
        d["layout"] = {"central_split": layout}
    (CFG / "prefs.json").write_text(json.dumps(d), encoding="utf-8")


def main() -> int:
    _seed(100)
    from PySide6.QtWidgets import QApplication

    from ff9mapkit import prefs
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.shell import _DEFAULT_CENTRAL_SPLIT, Workspace

    app = QApplication.instance() or QApplication([])
    app.setStyle("fusion")

    banner = ("OFFSCREEN -- every width below is a RUMOUR (see the docstring)" if _OFFSCREEN
              else "REAL PLATFORM -- these widths are trustworthy")
    print(f"\n  === {banner}\n  === probe config: {CFG}\n")

    def launch(width=1280, scale=100, layout=None):
        _seed(scale, layout)
        assert prefs.text_scale() == scale, f"scale not pinned: {prefs.text_scale()}"
        w = Workspace(pick_palette("dark"))
        w.resize(width, 820)
        w.show()
        for _ in range(6):
            app.processEvents()
        return w

    print("=== A. IS THE DEFAULT HONOURED AT COLD START?  (offscreen says no; the real platform says yes)\n")
    print(f"  {'scale':>6} {'requested':<18} {'actual':<22} {'mid_col min':>11}")
    for scale in (100, 110, 125, 150):
        w = launch(scale=scale)
        got = list(w._central_split.sizes())
        print(f"  {scale:>5}% {str(list(_DEFAULT_CENTRAL_SPLIT)):<18} {str(got):<22} "
              f"{w._central_split.widget(1).minimumSizeHint().width():>11}")
        w.close()
    print("\n  real platform: mid_col min = 542/575/685/796 and the default holds."
          "\n  offscreen    : mid_col min = ~1156 -> the outer panes look 'squeezed'. FICTION.")

    print("\n=== B. THE RATCHET NEEDS A RESTART  (an in-session sweep cannot see it)\n")
    w = launch()
    print(f"  in-session   1280            : {list(w._central_split.sizes())}")
    for width in (700, 1920):
        w.resize(width, 820)
        for _ in range(6):
            app.processEvents()
        print(f"  in-session   resize -> {width:<5}: {list(w._central_split.sizes())}")
    print("  ^ recovers -- the LIVE splitter re-derives from its original setSizes() request.")
    w.close()

    print()
    for saved in ([90, 542, 66], [76, 1138, 64]):
        w = launch(layout=saved)
        print(f"  RESTART with saved {str(saved):<15} -> {list(w._central_split.sizes())}")
        w.close()
    print("  ^ with _repair_central_split in place these HEAL to the default; before it, they never did.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
