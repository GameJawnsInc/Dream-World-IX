"""SHOT: THE LAMP -- Build & Deploy, flat (as shipped) vs one card with an accent left-stripe.

THE QUESTION THIS EXISTS TO ANSWER, and it is the oldest open one in the study. VISION.md's whole thesis
is "a dark table, tools laid flat, exactly ONE THING UNDER THE LAMP", and CRITIC.md caught that the vision
NEVER SAYS WHAT THE LIT THING IS on a work surface. PLAN.md deferred it as Open Question #2 with a
recommendation and a contingency:

    "Recommendation: ship it flat. If the page feels rudderless in the screenshot, the honest lift is the
     role="card" + a 4px accent left-stripe (measured 2.44-4.73 against surface_2 in all 7 -- the one
     delineation that survives light themes), applied to *one* element per screen and nothing else."

STATE.md calls the contingency "the highest-value unshipped aesthetic move in either plan" and gates it on
"a playtest verdict, not more research". That gate opened when the arc was playtested. So this renders both
and hands the eye the decision -- because a decoration cannot be settled by a measurement, and this study's
own record is that skepticism kills decorations while defects survive it (the reason round 3 exists).

WHAT THE MEASUREMENTS SAY BEFORE YOU LOOK -- three things, and two of them are against the contingency:

1. ELEVATION IS DEAD, so the vision's LITERAL words are not expressible. "One lifted surface" wants
   surface_3 against surface_2; measured, that is 1.043 (light) to 1.182 (gruvbox) in all 8 palettes --
   invisible everywhere. This is why round 2 reached for the accent instead. The lamp cannot be a lift.

2. THE SPEC'S HEADLINE NUMBER IS STALE. "2.44-4.73 against surface_2 in all 7" was measured in round 2.
   Round 3 (SIGNET) RETUNED THE PALETTES and added MIST as the 8th. Re-measured today: 2.118 (nord) to
   7.095 (mist). So the floor is not 2.44, it is 2.118 -- below the 3.0 WCAG non-text bar. (That bar is
   arguably not binding: a stripe identifies nothing, the card's title does. But the number moved and the
   plan does not know it.)

3. THE STRIPE IDIOM IS ALREADY TAKEN, and this is the objection the plan could not have had.
   `QLabel[role="banner"]` is `border-left: 4px solid $success|$warn|$error` -- shipped 2026-07-14, a day
   BEFORE the recommendation was written. So in this app a 4px left-stripe already means "a status
   verdict". The banner lives in the Problems panel, which shares the screen with the doc whenever the
   console is open. A 4px accent left-stripe on a card makes the same mark mean two things at once.
   It would also be the accent's THIRD spend (the Deploy verb, the breadcrumb chip, and now this),
   against LAW II: "never a hue you spend twice. If two things are shouting, one of them is wrong."

So the honest framing for the eye is NOT "is the stripe pretty" but: DOES THE FLAT PAGE FEEL RUDDERLESS?
If it does not, Open Question #2 closes as "flat, deliberately" -- which is what PLAN.md recommended in
the first place, and the contingency dies on the three findings above rather than on taste.

NATIVE ONLY (Fusion, as the app forces). The text scale is PINNED to 100: the user's real dial is at 110%
and a shot must not inherit it. MIST is the shipped default's climate and the palette the user judged.

Run:  py studies/gui-aesthetics/evidence/shot_lamp.py [stem]
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
os.environ["FF9MAPKIT_NO_THUMBS"] = "1"

from PySide6.QtWidgets import QApplication                                   # noqa: E402

app = QApplication.instance() or QApplication([])
assert app.platformName() != "offscreen", "native only: offscreen stubs the font DB"
app.setStyle("fusion")

from ff9mapkit.editor import theme                                           # noqa: E402
from ff9mapkit.workspace import shell as S                                   # noqa: E402

stem = sys.argv[1] if len(sys.argv) > 1 else "lamp"
pal = theme.derive(dict(theme.THEMES["mist"]))

# The stripe, as PLAN.md specced it: role="card" + a 4px accent left edge, on ONE element and nothing else.
# Applied via a WIDGET stylesheet on the chosen card -- which out-ranks the app sheet and survives its
# re-render, so this is a faithful preview of the rule without editing the shipped sheet.
STRIPE = f"""
QFrame[role="card"] {{
    border-left: 4px solid {pal['accent']};
}}
"""


def shot(lit: bool, name: str):
    win = S.Workspace(pal)
    win.show()
    win._apply_text_scale(100)                     # never inherit the user's real dial
    win.setFixedWidth(1600)
    for _ in range(4):
        app.processEvents()
    assert win.width() == 1600, f"asked 1600, got {win.width()} -- shot void"
    win.tabs.setCurrentWidget(win.build_deploy)
    for _ in range(6):
        app.processEvents()
    doc = win.tabs.currentWidget()
    if lit:
        # ONE element. The first card is "Build to (field)" -- the target of the doc's own primary verb,
        # and the only card on the page that every other card's action depends on.
        from PySide6.QtWidgets import QFrame
        cards = [c for c in doc.findChildren(QFrame) if c.property("role") == "card"]
        assert cards, "no cards found -- the shot would show nothing"
        cards[0].setStyleSheet(STRIPE)
        for _ in range(4):
            app.processEvents()
    img = doc.grab().toImage()
    assert img.width() > 100, "grabbed nothing"
    dst = HERE / f"{stem}_{name}.png"
    img.copy(0, 0, min(1100, img.width()), min(620, img.height())).save(str(dst))
    print(f"  {dst.name}  ({img.width()}x{img.height()} grabbed)")
    win.close()
    app.processEvents()


shot(False, "a_flat")
shot(True, "b_stripe")
print("\n  A = as shipped (flat; the crumb-row verb is the only accent)")
print("  B = the PLAN.md contingency: one card, 4px accent left-stripe")
print("\n  The question is not 'is B prettier'. It is: DOES A FEEL RUDDERLESS?")
