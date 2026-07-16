"""PROBE: what does a 14px body cost the toolbar at 1280px?

style.py:104 records the bug this guards:

    "Toolbar metrics are deliberately COMPACT (spacing 6 / button padding 10): every action plus the
     search pill and the gear menu must FIT at the default 1280px window -- overflowing items land in
     Qt's hidden extension chevron, which is how the Ctrl-K search and Preferences went invisible."

QUARTO P1 raises the body 13 -> 14. That is exactly the pressure this comment was written against, so
the claim "tightening tb_space 6->4 buys it back" is load-bearing and is NOT taken on trust here.

Method: build the REAL Workspace, apply a sheet built from patched values IN PROCESS (never on disk --
a sibling agent patching style.py on disk is what made this study's tree look dirty mid-run), FORCE it
to 1280 (and assert it took), and count toolbar actions whose widget is actually visible. An item pushed
into Qt's extension chevron reports isVisible() == False.

THIS PROBE SHIPPED TWO BUGS THAT CANCELLED INTO A PLAUSIBLE WRONG ANSWER. Both are worth knowing:
  1. A resize to 1280 is a REQUEST, not a fact. On a 1920 screen this window ignored it and opened at
     1920, so every row printed "@1280" while measuring 1920. Fix: setFixedWidth + assert the width took.
  2. The case labelled "body 14, naive" passed tb_space=None and therefore inherited whatever SHIPS.
     Once QUARTO P1 shipped tb_space 4, "naive" quietly became "with the fix already applied", and the
     probe reported 15/15 -- appearing to refute the claim it existed to prove. A baseline that reads the
     current code is not a baseline.
Together they produced a confident, self-consistent, wrong table. Pin your conditions and assert them.

VERDICT AT A REAL 1280: body 14 + tb_space 6 = 14/15 (one button in the chevron); tb_space 4 buys it
back to 15/15. body 15 does not recover at either. The shipped config is body 14 + tb_space 4.

NATIVE ONLY for the font DB. Style is forced to Fusion because THE APP FORCES FUSION (shell.py:129) --
the platform default would measure chrome the app never ships.

Run:  py studies/gui-aesthetics/evidence/probe_toolbar_budget.py
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"

from PySide6.QtWidgets import QApplication, QToolBar                        # noqa: E402

app = QApplication.instance() or QApplication([])
assert app.platformName() != "offscreen", "native only: offscreen stubs the font DB"
app.setStyle("fusion")                                  # what the app really runs

from ff9mapkit.editor import theme                                          # noqa: E402
from ff9mapkit.workspace import shell as S                                  # noqa: E402
from ff9mapkit.workspace import style                                       # noqa: E402

PAL = theme.derive(dict(theme.THEMES["mist"]))


def sheet_for(body_px, tb_space=None, btn_pad=None):
    """Render the QSS with the body rung (and optionally the toolbar metrics) patched, IN PROCESS.

    Patches the TABLE, not the template text. QUARTO P3 moved every size into style._TYPE, so this is now
    a dict poke rather than a string replace against an anchor that drifts every time the sheet is edited
    -- which is exactly what happened: the first cut anchored on `font-size: 13px` and broke the moment
    the body became a token. (In process, never on disk: a sibling agent patching style.py on disk is what
    made this study's working tree look dirty mid-run.)
    """
    saved_t = dict(style._TYPE)
    saved_d = {k: dict(v) for k, v in style._DENSITY.items()}
    try:
        style._TYPE["type_body"] = body_px
        if tb_space is not None:
            style._DENSITY["comfortable"]["tb_space"] = f"{tb_space}px"
        if btn_pad is not None:
            style._DENSITY["comfortable"]["btn_pad"] = btn_pad
        return style.qss(PAL)
    finally:
        style._TYPE.clear()
        style._TYPE.update(saved_t)
        style._DENSITY.clear()
        style._DENSITY.update(saved_d)


def count(sheet, width=1280):
    win = S.Workspace(PAL)
    win.setStyleSheet(sheet)
    win.show()
    for _ in range(2):
        app.processEvents()
    # setFixedWidth, NOT resize. THE FIRST CUT OF THIS PROBE WAS A LIE: resize(1280) is a REQUEST, and on
    # a 1920 screen this window ignored it and opened at 1920 -- so every row printed "@1280" while
    # measuring 1920. The relative deltas it found were real (the toolbar is genuinely tight), but its
    # LABEL was fiction, and a number reported against the wrong width is not a measurement.
    # Assert what you set: below.
    win.setFixedWidth(width)
    for _ in range(4):                                   # let the toolbar lay out + decide on the chevron
        app.processEvents()
    assert win.width() == width, (
        f"asked for {width}px, got {win.width()} -- the window ignored the size and this run is void"
    )
    tbs = win.findChildren(QToolBar)
    tot = vis = 0
    hidden = []
    for tb in tbs:
        for a in tb.actions():
            w = tb.widgetForAction(a)
            if w is None or a.isSeparator():
                continue
            tot += 1
            if w.isVisible():
                vis += 1
            else:
                hidden.append(a.text() or a.toolTip() or w.__class__.__name__)
    win.close()
    win.deleteLater()
    app.processEvents()
    return vis, tot, hidden


# EVERY case pins tb_space EXPLICITLY -- never `None` (= "whatever ships today").
#
# The second bug this probe taught, and it is nastier than the resize one: the case labelled "body 14,
# naive" passed None and therefore inherited the SHIPPED tb_space. Once QUARTO P1 shipped tb_space 4,
# "naive" silently became "with the fix already applied" and the probe reported 15/15 -- appearing to
# refute the very claim it had been written to prove. A baseline that reads the current code is not a
# baseline; it moves the moment you change the thing you are measuring.
CASES = [
    ("body 13 + tb_space 6 (was)",   13, 6,    None),
    ("body 14 + tb_space 6",         14, 6,    None),
    ("body 14 + tb_space 4 (SHIPS)", 14, 4,    None),
    ("body 14 + tb_space 4 + pad 8", 14, 4,    "6px 8px"),
    ("body 15 + tb_space 4",         15, 4,    None),
    ("body 15 + tb_space 6",         15, 6,    None),
]

print(f"{'config':32} {'visible':>9}  hidden")
print("-" * 78)
for label, body, sp, pad in CASES:
    # repeat: the first layout pass can report stale visibility
    runs = [count(sheet_for(body, sp, pad)) for _ in range(2)]
    vis, tot, hidden = runs[-1]
    flag = "" if vis == tot else "  <-- ITEMS IN THE CHEVRON"
    print(f"{label:32} {vis:>4}/{tot:<4}  {', '.join(hidden) if hidden else '-'}{flag}")

print()
print("style.py:104's whole point: an item in the chevron is INVISIBLE, not merely moved. If a 14px body")
print("costs an item and tb_space 6->4 does not buy it back, QUARTO P1 must pay some other way -- or the")
print("body stays at 13 and only the hint tier moves.")
