"""PROBE: what does a 14px body cost the toolbar at 1280px?

style.py:104 records the bug this guards:

    "Toolbar metrics are deliberately COMPACT (spacing 6 / button padding 10): every action plus the
     search pill and the gear menu must FIT at the default 1280px window -- overflowing items land in
     Qt's hidden extension chevron, which is how the Ctrl-K search and Preferences went invisible."

QUARTO P1 raises the body 13 -> 14. That is exactly the pressure this comment was written against, so
the claim "tightening tb_space 6->4 buys it back" is load-bearing and is NOT taken on trust here.

Method: build the REAL Workspace, apply a sheet built from patched values IN PROCESS (never on disk --
a sibling agent patching style.py on disk is what made this study's tree look dirty mid-run), resize to
1280, and count toolbar actions whose widget is actually visible. An item pushed into Qt's extension
chevron reports isVisible() == False.

NATIVE ONLY for the font DB. Style is forced to Fusion because THE APP FORCES FUSION (shell.py:129) --
the platform default would measure chrome the app never ships.

Run:  py studies/gui-aesthetics/evidence/probe_toolbar_budget.py
"""
import os
import sys
from pathlib import Path
from string import Template

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
SRC = style._QSS.template                               # the raw template text, pre-substitution


def sheet_for(body_px, tb_space=None, btn_pad=None):
    """Render the QSS with the body literal (and optionally the toolbar metrics) patched, in process."""
    text = SRC
    old = 'QWidget { background-color: $bg; color: $text; font-family: "Segoe UI"; font-size: 13px; }'
    assert old in text, "the body anchor moved -- this probe is not honest, fix the anchor"
    text = text.replace(old, old.replace("font-size: 13px;", f"font-size: {body_px}px;"))

    saved_q, saved_d = style._QSS, {k: dict(v) for k, v in style._DENSITY.items()}
    try:
        style._QSS = Template(text)
        if tb_space is not None:
            style._DENSITY["comfortable"]["tb_space"] = f"{tb_space}px"
        if btn_pad is not None:
            style._DENSITY["comfortable"]["btn_pad"] = btn_pad
        return style.qss(PAL)
    finally:
        style._QSS = saved_q
        style._DENSITY.clear()
        style._DENSITY.update(saved_d)


def count(sheet, width=1280):
    win = S.Workspace(PAL)
    win.setStyleSheet(sheet)
    win.resize(width, 860)
    win.show()
    for _ in range(3):                                   # let the toolbar lay out + decide on the chevron
        app.processEvents()
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


CASES = [
    ("body 13 (today)",              13, None, None),
    ("body 14, naive",               14, None, None),
    ("body 14 + tb_space 6->4",      14, 4,    None),
    ("body 14 + tb_space 4 + pad 8", 14, 4,    "6px 8px"),
    ("body 15, naive",               15, None, None),
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
