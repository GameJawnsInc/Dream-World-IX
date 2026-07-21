"""The subprocess job loop's feedback set (shell.py): the elapsed clock + stall note + Stop button on the
busy indicator, the running-state mirror to the always-visible chrome (crumb Deploy button + console
toggle), the first-run READY spine, and the post-deploy Copy-warp receipt.

Every job-state widget is FENCED to the busy window: the Stop button and the clock hide on _set_busy(False),
and the stall note fires only while a job runs. Prefs are isolated per-test by conftest's autouse
_isolate_prefs (pins prefs._path at a fresh tmp file), so has_deployed() reads False on construction and
these tests can never touch the developer's real prefs.json.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication                                     # noqa: E402

from ff9mapkit import prefs                                                    # noqa: E402
from ff9mapkit.workspace import anim                                          # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(app):
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.shell import Workspace, _apply_app_theme
    anim.set_enabled(False)                              # a test that leaves motion on strands real animations
    _apply_app_theme(app, pick_palette("dark"))
    w = Workspace(pick_palette("dark"))
    w.show()
    app.processEvents()
    yield w
    w.close()


# --------------------------------------------------------------- item 1: clock + stall + Stop
def test_stop_button_and_clock_hide_off_busy(win):
    """The Stop button, the 'Working…' clock and the tick timer are all live only between _set_busy(True)
    and (False) -- a no-op that left any of them showing when nothing runs is the defect this fences."""
    win._set_busy(True)
    assert win._stop_btn.isVisible(), "Stop is offered while a job runs"
    assert win._busy_label.isVisible()
    assert win._job_timer.isActive(), "the 1s clock/stall timer runs only during a job"

    win._set_busy(False)
    assert not win._stop_btn.isVisible(), "Stop hides the instant the job ends (fenced to the busy window)"
    assert not win._busy_label.isVisible(), "the clock hides when nothing runs"
    assert not win._job_timer.isActive(), "the timer stops when the job ends -- no stall note off-busy"


def test_stall_note_fires_only_after_silence_and_only_while_running(win):
    """After a stdout silence the clock says the job is still alive (a silent bundle read reads like a hang);
    fresh output clears it, and OFF-busy _tick_job is inert."""
    win._set_busy(True)

    win._last_output_ms = win._elapsed.elapsed()         # output just arrived -> no stall
    win._tick_job()
    assert win._busy_label.text().startswith("Working…")
    assert "no output" not in win._busy_label.text(), "no stall note right after output"

    win._last_output_ms = -25_000                        # pretend 25s of silence without waiting the clock out
    win._tick_job()
    assert "no output for" in win._busy_label.text(), "after >20s silence the clock reports still-running"

    win._set_busy(False)                                 # off-busy: _tick_job must be inert (the fence)
    win._busy_label.setText("SENTINEL")
    win._tick_job()
    assert win._busy_label.text() == "SENTINEL", "_tick_job is a no-op when no job runs"


def test_clock_reads_minutes_seconds(win):
    win._set_busy(True)
    win._tick_job()
    txt = win._busy_label.text()
    assert txt.startswith("Working… ") and ":" in txt, f"clock is m:ss text (reduced-motion safe): {txt!r}"
    win._set_busy(False)


def test_stop_kills_and_the_verdict_says_stopped(win):
    """Stop kills the subprocess and _proc_done posts the normal ERROR verdict whose next-step is 'Stopped.'."""
    win._job = ("Deploy to test field 4003", "ok", "", "See the Output panel.", None, 4003)
    win._stopped = True
    win._proc_done(1, None)                              # a killed process returns non-zero
    assert "Stopped." in win.banner.text(), "the Stop verdict names itself, not the generic hint"


# --------------------------------------------------------------- item 2: mirror to the chrome
def test_busy_relabels_and_disables_the_crumb_deploy_button(win):
    """While a job runs the always-visible crumb Deploy button mirrors it: disabled + the subject + no
    live-looking rocket. It reverts to 'Deploy   F9' when the job ends."""
    win._job = ("Deploy to test field 4003", None, "", "", None, 4003)
    win._set_busy(True)
    assert not win.deploy_btn.isEnabled(), "a running job disables the button whose click would no-op"
    assert win.deploy_btn.text().endswith("…") and "Deploy to test field 4003" in win.deploy_btn.text()

    win._set_busy(False)
    assert win.deploy_btn.text() == "Deploy   F9", "the label reverts when the job ends"


def test_console_toggle_mirrors_the_clock(win):
    """The collapsed console toggle carries the elapsed clock so the running state is legible even with the
    console collapsed; it drops the moment the job ends."""
    win._set_busy(True)
    assert "Working…" in win._console_btn.text(), "the toggle shows the job is running"
    win._set_busy(False)
    assert "Working…" not in win._console_btn.text(), "the mirror clears off-busy"


# --------------------------------------------------------------- item 3: first-run READY spine
def _open_deployable(win, *, target="X.toml"):
    win._current_target = lambda: ("Field", "field")
    win._deploy_target = lambda: target
    win._dirty_members = lambda: set()


def test_first_run_ready_points_the_newcomer_at_deploy(win):
    """A newcomer who has never deployed is pointed at Deploy once; the instant the marker latches the
    branch goes silent forever (the goes-away law)."""
    _open_deployable(win)
    win._deployed_target = None
    win._deployed_field_id = None
    assert not prefs.has_deployed(), "the isolated prefs read as a fresh install"

    guidance, actions = win._next_actions()
    assert guidance and actions, "the first-run spine speaks"
    assert actions[0][0] == "Deploy", "it names the Deploy step"

    prefs.set_has_deployed(True)                         # first deploy latches -> veteran
    guidance, actions = win._next_actions()
    assert (guidance, actions) == ("", []), "silent forever after the first deploy"


def test_first_run_spine_is_not_a_second_accent_beside_the_crumb_chip(win):
    """ONE accent per surface: in the first-run deployable state the always-visible crumb Deploy chip is
    enabled + accent, so the spine's Deploy action must be QUIET -- two gold Deploys one row apart is the
    defect this fences (the chip carries the accent; the spine only names the step)."""
    _open_deployable(win)
    win._deployed_target = None
    win._deployed_field_id = None
    win._refresh_deploy_btn()                            # arm the crumb chip for the deployable target
    assert win.deploy_btn.objectName() == "accent" and win.deploy_btn.isEnabled(), \
        "the crumb Deploy chip is the surface's live accent in exactly this state"
    _, actions = win._next_actions()
    assert actions[0][0] == "Deploy" and actions[0][2] is False, \
        "the spine's Deploy is quiet -- not a second accent beside the chip"


def test_first_deploy_latches_the_marker(win):
    """_proc_done's deploy-success path stamps prefs.has_deployed -- the sticky first-run marker -- so the
    READY spine stops pointing at a button the user has now found."""
    assert not prefs.has_deployed()
    win._deploy_target = lambda: "X.toml"
    win._job = ("Deploy to test field 4003", "ok", "", "hint", None, 4003)
    win._stopped = False
    win._proc_done(0, None)
    assert prefs.has_deployed() is True, "a successful deploy latches the marker"
    assert win._deployed_target == "X.toml"
    assert win._deployed_field_id == 4003, "and stashes the id for the Copy-warp receipt"


def test_dry_run_playbook_does_not_latch_the_first_run_marker(win):
    """A journey dry-run PRINTS a playbook and writes NOTHING to the game -- its subject carries 'deploy'
    ('Journey deploy playbook (dry-run)') but must not latch the sticky marker nor fake a just-deployed
    state. The latch fires on a real deploy; a preview is not one."""
    assert not prefs.has_deployed()
    win._deploy_target = lambda: "X.toml"
    win._deployed_target = None
    win._job = ("Journey deploy playbook (dry-run)", "ok", "", "hint", None, None)
    win._stopped = False
    win._proc_done(0, None)
    assert not prefs.has_deployed(), "a dry-run that writes nothing does not latch the first-run marker"
    assert win._deployed_target is None, "and does not fake the just-deployed spine state"


# --------------------------------------------------------------- item 4: Copy-warp receipt
def test_just_deployed_offers_a_copy_warp_receipt(win):
    """After a deploy the spine carries a one-click Copy-warp receipt for the deployed id; with no id known
    (a build/campaign deploy) it carries only the guidance."""
    _open_deployable(win, target="X.toml")
    win._deployed_target = "X.toml"
    win._deployed_field_id = 4003
    guidance, actions = win._next_actions()
    assert guidance and len(actions) == 1
    assert actions[0][0] == "Copy warp: 4003" and actions[0][2] is False, "a quiet (non-accent) receipt"

    win._deployed_field_id = None                        # no single warp id -> guidance only, no button
    guidance, actions = win._next_actions()
    assert guidance and actions == [], "no id, no receipt button"


def test_copy_warp_puts_the_bare_id_on_the_clipboard(win, app):
    win._copy_warp(6001)
    assert QApplication.clipboard().text() == "6001", "the bare id lands on the clipboard for ~ -> Warp"
