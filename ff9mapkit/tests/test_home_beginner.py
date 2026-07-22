"""Home's beginner guide: THE GOES-AWAY LAW + TAILOR (content-sized modals).

The law (shell._getstarted_show): onboarding is for someone who has not yet done the thing -- DONE is
measured, never assumed, and once measured done the guide leaves on its own. The arc it teaches now runs
all the way to the payoff (setup -> fork -> DEPLOY-and-play), so its completion signal is the last rung:
``has_deployed`` (the sticky first-deploy latch). That is what tells a veteran who closed a project apart
from a newcomer who forked a field but has not yet put it in the game -- the latter still gets the guide
while a target is open (the "now deploy and press ~" moment), gated so a veteran never sees it. Dismissal
(the Hide link) is a user choice and beats everything; the Home setup banner stays as the fail-safe
surface for real setup problems.

TAILOR (widgets.fit_dialog): a popup's size is a FUNCTION of its content -- the width is asked for in
characters of the dialog's own polished font (so it moves with the CALIBRE dial), lists ask to show
their real rows, and what cannot fit the screen is given back by the LIST (which scrolls), never by
squeezing word-wrapped labels (which overpaint their neighbours rather than shrink).

Width notes per the study's instrument laws: these fences assert RELATIONSHIPS recomputed from the same
font the helper read (valid under offscreen's stub font DB, which lies only about absolute advances),
never absolute pixel widths.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtGui import QFont, QFontMetricsF                                 # noqa: E402
from PySide6.QtWidgets import (QApplication, QDialog, QFormLayout, QLabel,     # noqa: E402
                               QLineEdit, QListWidget, QVBoxLayout, QWidget)

from ff9mapkit.workspace import widgets                                        # noqa: E402
from ff9mapkit.workspace.shell import _getstarted_primary_ix, _getstarted_show  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


# ---------------------------------------------------------------------------- the goes-away law (pure)
def test_the_goes_away_law_truth_table():
    """The whole table, spelled out -- the law is small enough to enumerate, so enumerate it. Four state
    booleans (setup_incomplete, has_target, has_recent, has_deployed) x dismissed = 32 rows, each justified
    by the priority order the law itself walks."""
    for setup_incomplete in (False, True):
        for has_target in (False, True):
            for has_recent in (False, True):
                for has_deployed in (False, True):
                    row = (setup_incomplete, has_target, has_recent, has_deployed)
                    # dismissed wins over EVERYTHING, including an incomplete setup.
                    assert _getstarted_show(setup_incomplete=setup_incomplete, has_target=has_target,
                                            has_recent=has_recent, has_deployed=has_deployed,
                                            dismissed=True) is False
                    got = _getstarted_show(setup_incomplete=setup_incomplete, has_target=has_target,
                                           has_recent=has_recent, has_deployed=has_deployed,
                                           dismissed=False)
                    if setup_incomplete:
                        want = True                      # the app cannot build anything yet -> guide
                    elif has_deployed:
                        want = False                     # completed the whole arc once -> veteran, never again
                    else:
                        # setup done, never deployed: show while a target is OPEN (the "now deploy" moment),
                        # or to a true first-run user with no history at all.
                        want = has_target or not has_recent
                    assert got is want, row


def test_a_veteran_who_closed_a_project_is_not_a_new_user():
    """The original regression: setup done + nothing open + real history + HAS DEPLOYED -> the guide is
    GONE (the old rule `setup_incomplete or nothing_open` showed the full newcomer checklist here forever).
    has_deployed is the signal that makes this a veteran and not a stalled newcomer."""
    assert _getstarted_show(setup_incomplete=False, has_target=False, has_recent=True,
                            has_deployed=True, dismissed=False) is False


def test_the_arc_stays_open_from_the_fork_to_the_first_deploy():
    """The gap this round closes: after the fork opens a target, the old rule VANISHED the guide -- exactly
    when "now deploy and press ~" is the next thing to say. With a target open and nothing ever deployed the
    guide STAYS (so the deploy rung can be pointed at), and the instant the first deploy latches has_deployed
    it goes away for good."""
    open_never_deployed = dict(setup_incomplete=False, has_target=True, has_recent=False,
                               dismissed=False)
    assert _getstarted_show(has_deployed=False, **open_never_deployed) is True, \
        "a fork is open but nothing was ever deployed -- the guide names the deploy step"
    assert _getstarted_show(has_deployed=True, **open_never_deployed) is False, \
        "the first deploy latched -> the veteran never sees the guide again"


def test_a_closed_never_deployed_project_relies_on_recent_not_the_guide():
    """A newcomer who forked, then closed the project WITHOUT deploying: with history but no target open the
    guide stays out (Recent + the spine carry them), and reopening the project brings the target -- and the
    guide with it (see the fork->deploy fence above). The full newcomer checklist does not reappear on a
    closed project just because the arc's last rung is unmet."""
    assert _getstarted_show(setup_incomplete=False, has_target=False, has_recent=True,
                            has_deployed=False, dismissed=False) is False


def test_the_accent_walks_the_arc_and_a_done_veteran_gets_no_accent():
    """THE ONE-ACCENT LAW at the step level: the accent lands on the first NOT-done step, and a Ctrl-K
    forced peek by a veteran whose every step is done accents NOTHING (-1) -- never nudging them toward an
    already-completed step. A no-op fallback of ``len(steps)-1`` would accent the last done row here, so the
    all-done row is the assertion that fails a regression. ``steps[i][2]`` is the done flag."""
    step = lambda done: ("title", "why", done, "label", None)
    assert _getstarted_primary_ix([step(True)] * 4) == -1, "all done -> no accent (the forced-peek case)"
    assert _getstarted_primary_ix([step(True), step(False), step(False)]) == 1, "first not-done wins"
    assert _getstarted_primary_ix([step(False), step(True)]) == 0
    assert _getstarted_primary_ix([step(True), step(True), step(False), step(True)]) == 2


# ------------------------------------------------------------------------------------ TAILOR fences
def _form_dialog():
    dlg = QDialog()
    form = QFormLayout(dlg)
    form.addRow("Name", QLineEdit())
    form.addRow("Folder", QLineEdit())
    return dlg


def test_fit_dialog_width_is_a_function_of_the_font(app):
    """The request, recomputed: minimumWidth == avgCharWidth(the dialog's own font) * ch + margins.
    Asserting the FORMULA (not a px number) keeps this valid under offscreen's stub font DB -- both
    sides read the same stub -- and is exactly what makes the dialog hear the text dial."""
    dlg = _form_dialog()
    widgets.fit_dialog(dlg, ch=64)
    fm = QFontMetricsF(dlg.font())
    m = dlg.layout().contentsMargins()
    want = round(fm.averageCharWidth() * 64) + m.left() + m.right()
    scr = dlg.screen() or QApplication.primaryScreen()
    want = min(want, int(scr.availableGeometry().width() * 0.92))
    assert dlg.minimumWidth() == want, (dlg.minimumWidth(), want)
    # the no-op guard: an unfitted twin has no such minimum, so a fit_dialog that stops setting one fails
    bare = _form_dialog()
    assert bare.minimumWidth() < dlg.minimumWidth()
    # and the function-of-the-font half: a bigger font must ask for MORE width (the dial's whole point).
    # ch=30, not 64: offscreen's fake screen is narrow and its stub advances are inflated, so at 64ch
    # BOTH sizes hit the screen clamp and the growth is invisible -- the clamp working as designed, but
    # measured here it hides the thing under test. Small ch keeps the base case under the clamp.
    small, big = _form_dialog(), _form_dialog()
    widgets.fit_dialog(small, ch=30)
    f = QFont(big.font())
    f.setPixelSize(max(2 * (f.pixelSize() if f.pixelSize() > 0 else 13), 26))
    big.setFont(f)
    widgets.fit_dialog(big, ch=30)
    assert big.minimumWidth() > small.minimumWidth(), (big.minimumWidth(), small.minimumWidth())


def test_fit_dialog_shows_the_list_content(app):
    """A populated list asks for its longest row (plus the scrollbar, so overflow never grows an
    h-scrollbar) and list_rows rows of height -- the exact two failures the unsized region catalog
    shipped (385x409, 6 rows visible, both scrollbars)."""
    dlg = QDialog()
    lay = QVBoxLayout(dlg)
    lst = QListWidget()
    for i in range(30):
        # short rows on purpose: offscreen's screen is ~800px with ~2x-inflated advances, and a long
        # row hits fit_dialog's own screen clamp -- correct behaviour that would hide the thing under test
        lst.addItem(f"Region {i:02d}  (seed {i * 50})")
    lay.addWidget(lst)
    widgets.fit_dialog(dlg, ch=64, list_rows=10)
    assert lst.minimumWidth() > lst.sizeHintForColumn(0), "row width + scrollbar allowance"
    assert lst.minimumHeight() >= 10 * lst.sizeHintForRow(0), "list_rows rows of height"


def test_fit_dialog_gives_overflow_back_from_the_list(app):
    """When the asked-for minimums cannot fit the screen, the LIST gives the height back (it scrolls);
    the labels are never squeezed below their wanted height -- a word-wrapped QLabel paints its full
    text over its neighbours rather than shrink (measured live at 150%).

    THE BRANCH MUST ACTUALLY RUN (this fence's first cut was vacuous, probe-verified by the round's
    adversarial review: fit_dialog's own 0.7*max_h pre-cap absorbed a 400-row ask on offscreen's small
    screen, `over` stayed negative, and deleting the whole give-back block passed every assert). So the
    dialog carries a FIXED-height block sized off the same screen the helper reads -- non-list content
    the give-back cannot touch -- which forces fixed + pre-capped-list > max_h, i.e. over > 0."""
    dlg = QDialog()
    lay = QVBoxLayout(dlg)
    scr = dlg.screen() or QApplication.primaryScreen()
    max_h = int(scr.availableGeometry().height() * 0.85)
    ballast = QWidget()
    ballast.setFixedHeight(int(max_h * 0.6))           # 0.6 + the list's 0.7 pre-cap > 1.0, always
    lay.addWidget(ballast)
    lst = QListWidget()
    for i in range(400):
        lst.addItem(f"row {i}")
    lay.addWidget(lst)
    widgets.fit_dialog(dlg, ch=64, list_rows=400)      # ask for the impossible: 400 visible rows
    pre_cap = int(max_h * 0.7)                         # what the list would keep if nothing gave back
    assert lst.minimumHeight() < pre_cap, "the give-back branch never ran -- the fence is vacuous again"
    assert lst.minimumHeight() >= 4 * lst.sizeHintForRow(0), "the give-back floor: 4 visible rows"
    assert dlg.height() <= max_h, "the dialog itself must FIT the screen"


def test_fit_dialog_splits_overflow_across_multiple_lists(app):
    """Two overflowing lists SPLIT the give-back (`over / len(fitted)`); charging each list the WHOLE
    deficit would starve every list beyond the first for no reason -- the more lists a dialog grows,
    the worse a non-split give-back gets.

    `over` is measured independently on a PROBE dialog carried only as far as fit_dialog's own pre-cap
    step (the per-list sizing loop, lines 122-136) -- the ground truth the give-back divides, uncoupled
    from whatever the fix under test actually does with it."""
    def _build(n_lists, rows_per_list):
        dlg = QDialog()
        lay = QVBoxLayout(dlg)
        lists = []
        for i in range(n_lists):
            lst = QListWidget()
            for r in range(rows_per_list):
                lst.addItem(f"row {i}-{r}")
            lay.addWidget(lst)
            lists.append(lst)
        return dlg, lists

    scr = QApplication.primaryScreen()
    max_h = int(scr.availableGeometry().height() * 0.85)
    pre_cap = int(max_h * 0.7)

    probe, probe_lists = _build(2, 1000)
    for lst in probe_lists:
        lst.ensurePolished()
        frame = 2 * lst.frameWidth()
        row_h = lst.sizeHintForRow(0)
        lst.setMinimumHeight(min(1000 * row_h + frame + 4, pre_cap))
    over = probe.sizeHint().height() - max_h
    assert over > 0, "the scenario must actually overflow, or this fence proves nothing"

    dlg, (a, b) = _build(2, 1000)
    widgets.fit_dialog(dlg, ch=64, list_rows=1000)
    row_h, frame = a.sizeHintForRow(0), 2 * a.frameWidth()
    floor = 4 * row_h + frame + 4
    want = max(floor, pre_cap - round(over / 2))
    assert a.minimumHeight() == want, (a.minimumHeight(), want)
    assert b.minimumHeight() == want, "symmetric overflow must shrink both lists identically"
    bug_would_give = max(floor, pre_cap - over)         # charging the FULL `over` to each list
    assert a.minimumHeight() > bug_would_give, \
        "shrank as if paying the whole overflow alone -- the split regressed"
