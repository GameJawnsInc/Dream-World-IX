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


def test_the_first_ever_deploy_gets_its_one_occasion(win, monkeypatch):
    """Ask-user #19 (MERGE A's restraint-safe vehicle): the celebration fires on exactly the deploy that
    latches has_deployed -- the gate IS the latch, read pre-latch, so there is no second pref to drift --
    and never again. Observed at the method seam: the card itself is .open()'d non-blocking."""
    fired = []
    monkeypatch.setattr(win, "_celebrate_first_deploy", lambda fid: fired.append(fid))
    win._deploy_target = lambda: "X.toml"
    win._stopped = False
    assert not prefs.has_deployed(), "the isolated prefs read as a fresh install"
    win._job = ("Deploy to test field 4003", "ok", "", "hint", None, 4003)
    win._proc_done(0, None)
    assert fired == [4003], "the first real deploy celebrates, carrying the warp id"
    win._job = ("Deploy to test field 4003", "ok", "", "hint", None, 4003)
    win._proc_done(0, None)
    assert fired == [4003], "the second deploy is silent -- once per install"


def test_the_celebration_card_is_nonblocking_and_names_the_warp(win):
    """The card itself: built and .open()'d -- this call RETURNING is the non-blocking contract (an
    exec() here would hang every headless _proc_done test, the round-8 modal law) -- with the warp id
    and the tilde walk in its body."""
    from PySide6.QtWidgets import QDialog, QLabel
    win._celebrate_first_deploy(4003)
    dlg = next(d for d in win.findChildren(QDialog) if d.windowTitle() == "It's in your game")
    labels = " ".join(lb.text() for lb in dlg.findChildren(QLabel))
    assert "4003" in labels and "~" in labels, labels
    dlg.close()


def test_raise_game_is_opt_in_and_yields_to_the_celebration(win, monkeypatch):
    """Ask-user #16: default OFF -- a deploy raises nothing. Opted in, a non-first deploy calls the
    raiser once; the FIRST-ever deploy hands focus to its once-ever card instead (two things fighting
    for the same focus is worse than either)."""
    from ff9mapkit.workspace import gamewin
    calls = []
    monkeypatch.setattr(gamewin, "raise_game", lambda: calls.append(1) or True)
    cele = []
    monkeypatch.setattr(win, "_celebrate_first_deploy", lambda fid: cele.append(fid))
    win._deploy_target = lambda: "X.toml"
    win._stopped = False

    prefs.set_raise_game_after_deploy(True)              # opted in, but this is the FIRST deploy...
    win._job = ("Deploy to test field 4003", "ok", "", "hint", None, 4003)
    win._proc_done(0, None)
    assert cele == [4003] and not calls, "the first deploy celebrates INSTEAD of raising"

    win._job = ("Deploy to test field 4003", "ok", "", "hint", None, 4003)
    win._proc_done(0, None)
    assert calls == [1], "a veteran's opted-in deploy raises the game"

    prefs.set_raise_game_after_deploy(False)             # the default: no raise
    win._job = ("Deploy to test field 4003", "ok", "", "hint", None, 4003)
    win._proc_done(0, None)
    assert calls == [1], "default OFF: the raiser never runs"


def test_raise_game_is_fail_soft():
    """gamewin's contract: ANY failure (no game, refused Win32 call, non-Windows platform) is a silent
    False -- a convenience must never break the deploy verdict it decorates."""
    from ff9mapkit.workspace import gamewin

    def _boom():
        raise RuntimeError("boom")

    orig = gamewin._game_pids
    gamewin._game_pids = _boom
    try:
        assert gamewin.raise_game() is False
    finally:
        gamewin._game_pids = orig


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
    """After a deploy the spine carries a one-click Copy-warp receipt for the deployed id, followed by the
    quiet 'Undo this deploy' affordance. With no id known (a build/campaign deploy) the receipt drops but
    the undo affordance remains -- undo does not need a warp id."""
    _open_deployable(win, target="X.toml")
    win._deployed_target = "X.toml"
    win._deployed_field_id = 4003
    win._deployed_dest = win.build_deploy.deploy_dest_key()   # the deploy's destination is still selected
    win._deployed_revertible = True                          # the deploy wrote a revert script -> Undo is offered
    guidance, actions = win._next_actions()
    labels = [a[0] for a in actions]
    assert guidance and labels == ["Copy warp: 4003", "Undo this deploy"]
    assert actions[0][2] is False, "a quiet (non-accent) receipt"
    assert actions[1][2] is False, "and a quiet undo -- the crumb Deploy chip owns the surface's accent"

    win._deployed_field_id = None                        # no single warp id -> undo only, no receipt
    guidance, actions = win._next_actions()
    assert guidance and [a[0] for a in actions] == ["Undo this deploy"], "no id: undo stays, receipt drops"


def test_undo_this_deploy_routes_through_the_build_tabs_revert(win):
    """THE SINGLE-OWNER LAW: the spine's undo must invoke the SAME revert path the Build tab's Revert
    button uses (its argv builders + confirm), not a second implementation. A no-op stand-in for on_revert
    would pass a shape check, so this asserts the delegation actually fires BuildDoc.on_revert once."""
    calls = []
    win.build_deploy.on_revert = lambda **k: calls.append(k)
    win._undo_last_deploy()
    assert len(calls) == 1, "undo delegates to the one owner of 'revert a deploy'"
    assert callable(calls[0].get("then")), \
        "and threads a self-dismiss callback so a successful undo collapses the just-deployed spine state"


def test_deploy_dest_key_moves_with_the_destination_radio(win):
    """The captured-destination snapshot the spine compares (findings 2/7): a field's key changes with the
    destination radio, so a post-deploy radio move is detectable; kind != field keys on the kind alone."""
    bd = win.build_deploy
    bd.kind = "field"
    bd.rb_test.setChecked(True)
    assert bd.deploy_dest_key() == ("test",)
    bd.rb_game.setChecked(True)
    assert bd.deploy_dest_key() == ("install",), "moving the radio moves the key"


def test_undo_retires_when_the_destination_radio_moves_off_the_deploy(win):
    """Findings 2/7: the spine's Undo reverts the LIVE destination radio, so a radio move AFTER a deploy must
    RETIRE the stale JUST-DEPLOYED strip rather than offer an undo for a destination the deploy never touched.
    The strip is gated on the destination key captured at deploy time still matching the live one."""
    _open_deployable(win, target="X.toml")
    prefs.set_has_deployed(True)                          # a veteran redeploying -> the fall-through is silent
    win._deployed_target = "X.toml"
    win._deployed_field_id = None
    win._deployed_revertible = True
    win._deployed_dest = ("test",)
    win.build_deploy.deploy_dest_key = lambda: ("test",)   # radio still on the captured destination
    guidance, actions = win._next_actions()
    assert guidance and [a[0] for a in actions] == ["Undo this deploy"], "matched destination -> undo stands"
    win.build_deploy.deploy_dest_key = lambda: ("install",)  # radio moved off the deploy
    guidance, actions = win._next_actions()
    assert (guidance, actions) == ("", []), "a destination change retires the stale undo"


def test_undo_is_withheld_when_the_deploy_left_no_revert_script(win):
    """Finding 5: an install whose pre-install snapshot FAILED cannot be reverted (its own receipt says so),
    so the JUST-DEPLOYED spine must not offer an Undo that would then report 'nothing to revert'. The undo
    tuple is gated on the deploy having written a revert script (_deployed_revertible)."""
    _open_deployable(win, target="X.toml")
    win.build_deploy.deploy_dest_key = lambda: ("install",)
    win._deployed_target = "X.toml"
    win._deployed_field_id = None
    win._deployed_dest = ("install",)
    win._deployed_revertible = False                     # the snapshot failed -> no revert script written
    guidance, actions = win._next_actions()
    assert guidance and actions == [], "the deploy is confirmed, but a non-revertible deploy offers no undo"
    win._deployed_revertible = True                      # a normal (snapshot-backed) install
    _, actions = win._next_actions()
    assert [a[0] for a in actions] == ["Undo this deploy"], "a revertible deploy offers the undo"


def test_a_successful_undo_self_dismisses_the_just_deployed_state(win):
    """Finding 1: once the spine's Undo actually reverts the deploy, the JUST-DEPLOYED strip must COLLAPSE --
    restating '~ -> Reload' + Undo for an already-undone deploy is the defect. _undo_last_deploy threads a
    then-callback that on_revert fires on a code==0 finish; this asserts that callback clears every marker."""
    win._deployed_target = "X.toml"
    win._deployed_field_id = 4003
    win._deployed_dest = ("test",)
    win._deployed_revertible = True
    win._clear_deployed_state()                          # the callback on_revert fires on a successful revert
    assert win._deployed_target is None and win._deployed_field_id is None, "the deploy markers clear"
    assert win._deployed_dest is None and win._deployed_revertible is False, "and so do the destination gates"


def test_copy_warp_puts_the_bare_id_on_the_clipboard(win, app):
    win._copy_warp(6001)
    assert QApplication.clipboard().text() == "6001", "the bare id lands on the clipboard for ~ -> Warp"


# --------------------------------------------------------------- item 5: structured failure + jump
_FAILED = (
    "reading broken.field.toml\n"
    "error: [camera] section is required\n"
)


def _run_failed(win, output, code, *, stopped=False):
    """Simulate a job whose stdout is ``output`` finishing with ``code`` -- populate the console + the job
    buffer the way _drain_proc would, then post the verdict via _proc_done."""
    win._job = ("Build", None, "", "See the Output panel.", None, None)
    win._stopped = stopped
    win._job_out = [output]                              # what _drain_proc accumulates verbatim
    win.output.clear()
    win._log(output.rstrip())                            # what the user sees streamed into Output
    win._proc_done(code, None)


def _anchor_rows(win):
    return [win.problems.item(i) for i in range(win.problems.count())
            if win.problems.item(i).data(win_role())]


def win_role():
    from PySide6.QtCore import Qt
    return Qt.ItemDataRole.UserRole


def test_failed_job_posts_a_clickable_anchor_row(win):
    """A non-zero exit whose log carries a tight anchor posts ONE Problems row carrying the offending line
    in UserRole (the clickable jump target). The chair's law: fire only on failure + a tight anchor."""
    _run_failed(win, _FAILED, 1)
    rows = _anchor_rows(win)
    assert len(rows) == 1, "exactly one anchor row on a failed job with a tight anchor"
    assert rows[0].text() == "error: [camera] section is required"
    assert rows[0].data(win_role()) == "error: [camera] section is required", "carries the jump target"


def test_clicking_the_anchor_row_reveals_the_line_in_output(win):
    """Activating the anchor row selects its line in the Output console -- the jump. (Backward search finds
    THIS job's occurrence since the log accumulates.)"""
    _run_failed(win, _FAILED, 1)
    row = _anchor_rows(win)[0]
    win.output.moveCursor(QTextCursor_start())           # park the cursor away from the match
    win._jump_to_anchor(row)
    assert win.output.textCursor().selectedText() == "error: [camera] section is required", \
        "the jump selects (reveals) the anchored line in Output"


def test_jump_no_ops_on_a_row_without_an_anchor(win):
    """A plain validation row (no UserRole) must not move the Output cursor -- _jump_to_anchor is safe to
    wire for every row because it no-ops on the anchorless ones."""
    from PySide6.QtWidgets import QListWidgetItem
    win.output.clear()
    win._log("some unrelated output")
    win.output.moveCursor(QTextCursor_start())
    before = win.output.textCursor().position()
    win._jump_to_anchor(QListWidgetItem("a validation problem"))   # no UserRole set
    assert win.output.textCursor().position() == before, "no anchor -> no jump"


def test_exit_zero_posts_no_anchor_row(win):
    """Success posts no anchor row even when the log echoes an `error:` line (the extractor gates on code)."""
    _run_failed(win, _FAILED, 0)
    assert _anchor_rows(win) == [], "exit 0 -> no anchor row"


def test_a_stop_kill_posts_no_anchor_row(win):
    """A user Stop is intended, not a failure to dissect -- it carries the 'Stopped.' verdict but no anchor
    row (the exit is non-zero, so this must be gated on _stopped, not on the code alone)."""
    _run_failed(win, _FAILED, 1, stopped=True)
    assert _anchor_rows(win) == [], "a Stop kill surfaces no structured-failure row"
    assert "Stopped." in win.banner.text()


def test_no_anchor_failure_posts_no_row(win):
    """A non-zero exit whose log has neither a traceback nor an `error:` line posts zero rows -- a no-anchor
    mess is not worth a false row (don't cry wolf)."""
    _run_failed(win, "wrote build/error_log.txt\ndone in 3s\n", 1)
    assert _anchor_rows(win) == [], "no tight anchor -> no row"
    assert win.banner.property("state") == "error", "the verdict still reads failed"


def QTextCursor_start():
    from PySide6.QtGui import QTextCursor
    return QTextCursor.MoveOperation.Start
