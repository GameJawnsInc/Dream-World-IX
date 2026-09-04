"""``tools/harness`` -- the driver half of the in-game test harness (engine half = memoria-patch s83).

WHAT THESE TESTS ARE FOR. They pin the DRIVER against a protocol stand-in (``harness.fakegame``):
sequence numbers advance and are awaited, a torn ``state.json`` read is survived, every wait is
bounded and reports the last state it saw, a dead game is detected instead of hung on, artifacts land
in the run directory, and the process guard refuses to race a session it does not own.

WHAT THEY ARE NOT. They do not and cannot tell you the engine patch works -- no button is pressed, no
field loads, nothing renders. That is what ``tools/play.py --smoke`` against a real game is for. The
value here is separation: when a real run misbehaves, these say whether the driver is the liar.

Nothing here touches the real game install: every Session is pinned to tmp_path and given an injected
launcher and pid probe, the same "pin the path through a seam" rule the deploy tooling learned the
hard way.
"""

import json
import os
import pathlib
import sys
import threading
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

from harness import Channel, HarnessError, Session, State          # noqa: E402
from harness.fakegame import FakeGame                              # noqa: E402
from harness.suite import SuiteRunner, load_manifest               # noqa: E402


@pytest.fixture
def game(tmp_path):
    """A fake install root with a fake FF9 in it, plus its protocol stand-in (not started).

    It carries a real-shaped ``DictionaryPatch.txt`` because the warp guard reads one: whether a
    field is deployed is a fact about the install, and a guard that cannot read the install must say
    so rather than wave the warp through.
    """
    (tmp_path / "x64").mkdir()
    (tmp_path / "x64" / "FF9.exe").write_bytes(b"MZ")
    (tmp_path / "x64" / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    mod = tmp_path / "FF9CustomMap"
    mod.mkdir()
    # `FieldScene <id> <area> <NAME> <NAME2> <textblock>` -- column 2 is the AREA index, not the name.
    (mod / "DictionaryPatch.txt").write_text(
        "FieldScene 30810 11 CHEST_ROOM CHEST_ROOM 30810\n"
        "FieldScene 30820 11 ROOM_A ROOM_A 30820\n"
        "FieldScene 30821 11 ROOM_B ROOM_B 30821\n",
        encoding="utf-8",
    )
    return tmp_path


def published(g, predicate, *, timeout=4.0):
    """Wait until the stand-in has PUBLISHED a change a test poked straight onto its fields.

    The fake publishes every other simulated frame, so `fake.ui_state = "WorldHUD"` is not yet
    visible to the driver -- a test asserting immediately after would be racing its own stand-in and
    failing for a reason that has nothing to do with the code under test.
    """
    import time as _t
    deadline = _t.time() + timeout
    while _t.time() < deadline:
        st = g.channel.state()
        if st is not None:
            try:
                if predicate(st):
                    return st
            except (TypeError, AttributeError, KeyError):
                pass
        _t.sleep(0.01)
    raise AssertionError("the stand-in never published the change the test made")


def boot(g):
    """New Game with no title settle.

    ``TITLE_SETTLE`` is 10 REAL seconds and exists because Memoria is still loading when the title
    appears; against a stand-in it buys nothing and costs the whole suite ten seconds per test.
    """
    return g.newgame(settle=0)


def session(game_path, fake, **kw):
    """A Session wired to the stand-in: nothing is launched, nothing real is probed."""
    return Session(
        game_path=game_path,
        run_dir=game_path / "run",
        # ⚠ Pinned through the seam. The real one is the OWNER'S SAVE FOLDER on a shared machine;
        # a test that read it would copy 3 MB per case and, worse, teach the suite to touch it.
        save_dir=game_path / "player-saves",
        pid_probe=lambda: [],
        launcher=lambda exe: fake.start(),
        boot_timeout=15.0,
        verbose=False,
        **kw,
    )


# --------------------------------------------------------------------------- channel + state


def test_send_advances_seq_and_writes_the_request(game):
    ch = Channel(game)
    ch.reset()
    assert ch.send(["wait 5"]) == 1
    body = (ch.dir / "req.txt").read_text(encoding="utf-8").splitlines()
    assert body[0] == "seq 1"
    assert body[1] == "wait 5"


def test_a_second_send_refuses_to_overwrite_an_unaccepted_request(game):
    """req.txt is one last-write-wins slot: overwriting it DESTROYS the request that was there.

    And the loss is invisible -- the survivor's ack satisfies the wait for the one that vanished. So
    a new request must wait for the agent's receipt (the published seq) for the previous one.
    """
    ch = Channel(game)
    ch.reset()
    ch.send(["wait 5"])                                   # nobody is running, so nobody accepts it
    with pytest.raises(HarnessError, match="never accepted request 1"):
        ch.send(["press confirm 2"], accept_budget=0.3)
    # ...and the first request is still intact, rather than half-overwritten.
    assert (ch.dir / "req.txt").read_text(encoding="utf-8").splitlines()[1] == "wait 5"


def test_arm_gate_is_a_file(game):
    ch = Channel(game)
    ch.reset()
    assert not ch.armed
    ch.arm()
    assert ch.armed and (ch.dir / "arm").exists()
    ch.disarm()
    assert not ch.armed


def test_reset_clears_stale_artifacts(game):
    ch = Channel(game)
    ch.reset()
    (ch.dir / "state.json").write_text("{}", encoding="utf-8")
    (ch.dir / "events.jsonl").write_text('{"kind":"old"}\n', encoding="utf-8")
    (ch.shots / "old.png").write_bytes(b"\x89PNG")
    ch.reset()
    assert ch.state() is None
    assert ch.events() == []
    assert not (ch.shots / "old.png").exists()


def test_a_torn_state_read_is_survived(game, monkeypatch):
    """A half-written document must never surface as a state -- it would flake every assertion."""
    ch = Channel(game)
    ch.reset()
    good = {"frame": 7, "field": {"id": 42}, "player": {"control": True}}
    (ch.dir / "state.json").write_text(json.dumps(good), encoding="utf-8")

    reads = {"n": 0}
    real = pathlib.Path.read_text

    def flaky(self, *a, **kw):
        if self.name == "state.json":
            reads["n"] += 1
            if reads["n"] == 1:
                return '{"frame": 7, "fie'         # torn
        return real(self, *a, **kw)

    monkeypatch.setattr(pathlib.Path, "read_text", flaky)
    st = ch.state()
    assert st is not None and st.frame == 7 and reads["n"] >= 2


def test_state_maps_the_fields_a_scenario_asserts_on():
    st = State({
        "frame": 3, "ack": 2, "busy": False, "ui_state": "FieldHUD", "fading": False,
        "field": {"id": 30500, "name": "FBG_X"},
        "player": {"x": 1.5, "y": 0.0, "z": -2.5, "control": True},
        "dialog": {"open": True, "texts": ["Hello", "", "world"], "choice": None},
        "flags": {"8712": True},
        "held": ["Up"],
    })
    assert st.field_id == 30500 and st.field_name == "FBG_X"
    assert st.pos == (1.5, 0.0, -2.5) and st.control
    assert st.texts == ["Hello", "world"] and st.text == "Hello\nworld"
    assert st.flag(8712) is True and st.flag(9999) is None
    assert st.held == ["Up"] and "field 30500" in repr(st)


# --------------------------------------------------------------------------- process guards


def test_refuses_to_race_a_game_it_does_not_own(game):
    s = Session(game_path=game, run_dir=game / "run", pid_probe=lambda: [4242],
                launcher=lambda exe: None, verbose=False)
    with pytest.raises(HarnessError, match="already running"):
        s.start()


def test_attach_without_a_running_game_is_refused(game):
    s = Session(game_path=game, run_dir=game / "run", attach=True, pid_probe=lambda: [],
                launcher=lambda exe: None, verbose=False)
    with pytest.raises(HarnessError, match="no FF9 process"):
        s.start()


def test_a_game_that_never_publishes_state_times_out_and_names_the_patch(game):
    class Dead:
        def poll(self):
            return None

    s = Session(game_path=game, run_dir=game / "run", pid_probe=lambda: [],
                launcher=lambda exe: Dead(), boot_timeout=0.6, verbose=False)
    with pytest.raises(HarnessError, match="s83"):
        s.start()


def test_a_failed_start_still_disarms_the_shared_install(game):
    """A start() that raises must not leave `arm` behind for the next person's game to pick up."""
    class Dead:
        def poll(self):
            return None

    s = Session(game_path=game, run_dir=game / "run", pid_probe=lambda: [],
                launcher=lambda exe: Dead(), boot_timeout=0.5, verbose=False)
    with pytest.raises(HarnessError):
        with s:
            pass
    assert not s.channel.armed
    assert (game / "run" / "report.json").exists(), "a failed start must still leave a report"


def test_a_game_that_dies_mid_run_is_reported_not_waited_on(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        fake.returncode = 3                       # the process vanishes under us
        with pytest.raises(HarnessError, match="exited"):
            g.wait_for(lambda s: False, timeout=5, what="never")


# --------------------------------------------------------------------------- driving


def test_a_full_scenario_drives_the_stand_in(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        assert g.state.ui_state == "FieldHUD"

        g.warp(30810)
        assert g.state.field_id == 30810

        g.watch(8712)
        g.flag(8712, True)
        assert g.expect_flag(8712, True)

        g.press("confirm")
        g.wait_frames(3)
        shot = g.shot("after-chest")
        assert shot.exists() and shot.stat().st_size > 0

        assert g.expect_field(30810)
        assert g.passed

    report = json.loads((game / "run" / "report.json").read_text(encoding="utf-8"))
    assert report["passed"] is True and report["verdict"] == "pass"
    assert len(report["checks"]) == 2
    assert (game / "run" / "shots" / "after-chest.png").exists()
    assert (game / "run" / "Memoria.log").read_text(encoding="utf-8") == "fake log\n"


def test_walk_holds_the_direction_for_the_requested_frames(game):
    """The button must actually be down in published state -- a no-op walk would fail silently."""
    fake = FakeGame(game, fps=120.0)
    seen = []
    with session(game, fake) as g:
        boot(g)

        stop = threading.Event()

        def sample():
            while not stop.is_set():
                st = g.channel.state()
                if st and st.held:
                    seen.append(tuple(st.held))
                time.sleep(0.005)

        watcher = threading.Thread(target=sample, daemon=True)
        watcher.start()
        g.walk("up", 30)
        stop.set()
        watcher.join(timeout=2)

    assert ("up",) in seen, f"the direction was never observed held (saw {seen[:5]})"


def test_an_unknown_button_is_rejected_locally(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        with pytest.raises(HarnessError, match="unknown button"):
            g.press("jump")


def test_a_refused_step_surfaces_as_an_error_not_a_hang(game):
    """newgame off the title screen must fail loudly and quickly."""
    fake = FakeGame(game, boot_state="FieldHUD")
    with session(game, fake) as g:
        with pytest.raises(HarnessError, match="refused|title"):
            g.send("newgame", timeout=5)


def test_expect_records_a_failure_without_aborting_the_run(game):
    """One scenario should report EVERY failed expectation, not just the first."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        assert g.expect_field(999, timeout=0.6) is False
        assert g.expect_text("never appears", timeout=0.6) is False
        assert g.expect_field(70) is True
        assert g.passed is False
        assert len(g.checks) == 3

    report = json.loads((game / "run" / "report.json").read_text(encoding="utf-8"))
    assert report["passed"] is False
    assert [c["ok"] for c in report["checks"]] == [False, False, True]


def test_quit_shuts_the_game_down_and_disarms(game):
    fake = FakeGame(game)
    s = session(game, fake)
    s.start()
    s.stop()
    assert fake.returncode == 0
    assert not s.channel.armed, "a finished run must leave the shared install unarmed"


# ======================================================================================
# THE LIE-CLASS REGRESSIONS
#
# Everything below guards a defect that made the harness report a FALSE VERDICT -- a green
# run that observed nothing, or a confident accusation against the game for a fault that
# lived in the driver. That class is the expensive one here: a loud failure costs a re-run,
# a false statement costs a commit message, a study, and the next person's trust.
#
# Each test is written so that reverting its fix turns it red.
# ======================================================================================


# --------------------------------------------------------------------------- the ack contract


def test_an_agent_carrying_a_stale_sequence_never_acks_a_dropped_step(game):
    """THE FALSE-GREEN HEADLINE: an already-armed agent discards our requests and acks anyway.

    Break `_await_ack`'s `last.seq >= seq` term and this goes green while the stand-in is never
    touched -- which is exactly what the live harness did after a leaked arm file.
    """
    fake = FakeGame(game, resets_on_arm=False)
    fake.seq = fake.ack = 40                      # a dead run's counters, still latched

    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        # The OUTCOME, not the ack: the stand-in actually moved.
        assert fake.field_id == 30810
        assert ["warp", "30810", "-1", "-1"] in fake.executed


def test_arming_over_an_existing_arm_file_forces_a_real_transition(game):
    """Rewriting the arm file is a NO-OP to the agent -- it must see a disarm to reset itself."""
    ch = Channel(game, label="first")
    ch.reset()
    ch.dir.mkdir(parents=True, exist_ok=True)
    fake = FakeGame(game).start()
    try:
        ch.arm()
        deadline = time.time() + 5
        while time.time() < deadline and fake.arm_transitions < 1:
            time.sleep(0.02)
        assert fake.arm_transitions == 1

        second = Channel(game, label="second", owner_pid=ch.owner_pid)
        second.arm()                                    # over an arm file that already exists
        deadline = time.time() + 5
        while time.time() < deadline and fake.arm_transitions < 2:
            time.sleep(0.02)
        assert fake.arm_transitions == 2, "the agent never observed a false->true transition"
    finally:
        ch.disarm()
        fake.stop()


def test_a_protocol_mismatch_is_refused_rather_than_read_as_game_data(game):
    """Every State accessor degrades a missing section to a sentinel, so a skew reads as data."""
    fake = FakeGame(game)
    import harness.fakegame as fg
    original = fg.PROTOCOL
    fg.PROTOCOL = original + 7
    try:
        with pytest.raises(HarnessError, match="protocol mismatch"):
            with session(game, fake):
                pass
    finally:
        fg.PROTOCOL = original


# --------------------------------------------------------------------------- the arm lock


def test_a_second_live_session_refuses_to_steal_the_arm(game):
    """Two drivers on one channel delete each other's artifacts and overwrite each other's requests."""
    ch = Channel(game, label="theirs", owner_pid=os.getpid())
    ch.dir.mkdir(parents=True, exist_ok=True)
    ch.arm(force_cycle=False)
    try:
        # A different owner pid, whose claim must refuse because OUR pid is demonstrably alive.
        mine = Channel(game, label="mine", owner_pid=os.getpid() + 1)
        with pytest.raises(HarnessError, match="already has this install armed"):
            mine.claim()
    finally:
        ch.disarm()


def test_disarm_leaves_another_live_runs_arm_alone(game):
    ch = Channel(game, label="theirs", owner_pid=os.getpid())
    ch.dir.mkdir(parents=True, exist_ok=True)
    ch.arm(force_cycle=False)
    other = Channel(game, label="mine", owner_pid=os.getpid() + 1)
    other.disarm()
    assert ch.armed, "disarming stole an arm belonging to a live run"
    ch.disarm()


def test_a_stale_arm_from_a_dead_pid_is_adopted(game):
    ch = Channel(game, label="dead")
    ch.dir.mkdir(parents=True, exist_ok=True)
    (ch.dir / "arm").write_text(json.dumps({"pid": 999999, "label": "dead", "started": "?"}),
                                encoding="utf-8")
    mine = Channel(game, label="mine")
    mine.claim()                                        # must not raise: pid 999999 is not alive
    mine.arm(force_cycle=False)
    assert json.loads((ch.dir / "arm").read_text(encoding="utf-8"))["label"] == "mine"
    mine.disarm()


def test_a_failing_collect_still_disarms_the_shared_install(game, monkeypatch):
    """The gate outranks the artifacts: a locked PNG must not leave the next person's game armed."""
    fake = FakeGame(game)
    s = session(game, fake)
    s.start()

    def boom(self, dest):
        raise OSError("locked")

    monkeypatch.setattr(type(s.channel), "collect", boom)
    s.stop()
    assert not s.channel.armed


# --------------------------------------------------------------------------- error attribution


def test_a_valid_send_after_a_refused_one_succeeds(game):
    """The agent's error is a LATCH -- one refusal used to make every later step raise on it."""
    fake = FakeGame(game, boot_state="FieldHUD")
    with session(game, fake) as g:
        with pytest.raises(HarnessError, match="refused|title"):
            g.send("newgame", timeout=5)
        g.send("wait 2", timeout=5)                 # innocent, and must not inherit the blame
        g.press("confirm")


# --------------------------------------------------------------------------- honest waits


def test_a_raising_predicate_is_reported_as_a_broken_assertion(game):
    """A predicate that raises on every sample is a bug in the test, not a failure of the game."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError, match="broken assertion"):
            g.wait_for(lambda s: s.player_x > "not a number", timeout=1.0, what="a bad comparison")


def test_a_frozen_channel_is_not_reported_as_a_game_condition(game):
    """A hung agent's last state.json satisfies most predicates -- it must not be honoured."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        fake.mode = "frozen"                       # the frame counter stops; the document remains
        time.sleep(2.5)                            # let the surviving document go stale
        with pytest.raises(HarnessError, match="frozen"):
            g.wait_for(lambda s: s.ui_state == "FieldHUD", timeout=2.0, what="a field")
        fake.mode = "normal"          # thaw, so teardown does not spend its full quit budget


def test_watch_cutscene_does_not_call_a_frozen_channel_a_soft_lock(game):
    """Soft-lock is the most expensive verdict this tool emits; it needs a demonstrably LIVE game."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.control(False)
        published(g, lambda s: not s.control)
        fake.mode = "frozen"
        time.sleep(0.3)
        with pytest.raises(HarnessError, match="NOT a soft-lock"):
            g.watch_cutscene(timeout=1.5)
        fake.mode = "normal"          # thaw, so teardown does not spend its full quit budget


def test_wait_control_waits_out_the_load_flicker(game):
    """Control flickers true as a field loads; a single sample returned during the flicker."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)

        def flicker():
            time.sleep(0.15)
            fake.control = False                   # the entry script takes control back
            time.sleep(1.2)
            fake.control = True

        threading.Thread(target=flicker, daemon=True).start()
        started = time.time()
        g.wait_control(timeout=20.0)
        assert time.time() - started > 1.2, "returned during the flicker"


def test_wait_playable_requires_a_known_position(game):
    """GetUserControl() goes true before GetControlChar() does -- measuring there compares to None."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        fake.has_position = False
        published(g, lambda s: s.player_x is None)
        with pytest.raises(HarnessError):
            g.wait_playable(timeout=1.5)


# --------------------------------------------------------------------------- the warp guards


def test_registered_fields_reads_the_scene_name_not_the_area(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        found, read = g.registered_fields()
        assert found[30810] == "CHEST_ROOM", f"got {found[30810]!r} -- that is the area column"
        assert len(read) == 1


def test_warp_refuses_an_unregistered_id_but_allows_a_stock_field(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError, match="neither a stock FF9 field"):
            g.warp(31999)
        # DictionaryPatch lists only MOD registrations, so a membership test against it alone
        # refuses all ~674 shipping rooms with a false claim about a null .eb.
        g.warp(1650)
        assert fake.field_id == 1650


def test_warp_refuses_an_id_that_wraps_in_int16(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError, match="out of range"):
            g.warp(40000)


def test_warp_refuses_when_no_registration_can_be_read(game):
    """'Nothing is registered' and 'I could not read the registrations' are different facts.

    Merging them made the guard disable itself in exactly the situation where it was least able to
    be sure -- and then the black screen arrived as a generic control/position timeout.
    """
    (game / "FF9CustomMap" / "DictionaryPatch.txt").unlink()
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError, match="no DictionaryPatch.txt could be read"):
            g.warp(30810)
        g.warp(30810, check_registered=False)          # the documented override still works


def test_world_warp_off_the_overworld_is_refused_by_the_driver(game):
    """The engine refuses it silently, so the wait would time out blaming the destination field."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError, match="FROM the overworld"):
            g.world_warp(30810)


def test_teleport_asserts_on_the_position_that_resulted(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError, match="OVERWORLD verb"):
            g.teleport(100, 200)
        fake.ui_state = "WorldHUD"
        fake.world["x"], fake.world["z"] = 0.0, 0.0
        published(g, lambda s: s.ui_state == "WorldHUD")
        st = g.teleport(1092, -788)
        assert (st.world_x, st.world_z) == (1092.0, -788.0)


# --------------------------------------------------------------------------- movement honesty


def test_calibrate_axes_rejects_a_wall_slide(game):
    """A character pressed into a wall keeps MOVING -- so 'did it move' cannot detect this.

    The old absolute 15-unit floor accepted the slide, cached the basis, logged |dot|=0.00, and then
    steered every walk_to along the wall before blaming the field for being unreachable.
    """
    fake = FakeGame(game, mode="wall_slide")
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        with pytest.raises(HarnessError,
                           match="not a free axis|not perpendicular|could not calibrate"):
            g.calibrate_axes()


def test_calibrate_axes_discovers_a_yawed_basis(game):
    """FF9 movement is SCREEN-space under a frequently yawed camera; the basis cannot be assumed."""
    fake = FakeGame(game, twist=90.0)
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        basis = g.calibrate_axes()
        # Under a 90-degree twist "up" (screen +z) lands entirely on the world X axis. The SIGN is a
        # property of the twist convention, not of the discovery -- what matters is that the measured
        # axis is not the assumed one, and that the two axes stay perpendicular.
        assert abs(basis["v"][0]) > 0.9 and abs(basis["v"][1]) < 0.2, f"up measured {basis['v']}"
        assert abs(basis["h"][1]) > 0.9, f"right measured {basis['h']}"


def test_walk_to_converges_under_a_yawed_basis(game):
    fake = FakeGame(game, twist=90.0)
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        assert g.walk_to(157.0, -211.0, tolerance=40.0) is True
        assert g.distance_to(157.0, -211.0) <= 40.0


def test_walk_to_refuses_a_tolerance_below_the_physical_floor(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        with pytest.raises(HarnessError, match="physical floor"):
            g.walk_to(100.0, 100.0, tolerance=5.0)


def test_field_verbs_refuse_on_the_world_map(game):
    """player.x is NOT null on the overworld -- it is the same value x256, a different space.

    So the field verbs do not fail loudly there; they converge on confident wrong numbers.
    """
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        fake.ui_state = "WorldHUD"
        published(g, lambda s: s.ui_state == "WorldHUD")
        with pytest.raises(HarnessError, match="FIELD verb"):
            g.distance_to(0, 0)
        with pytest.raises(HarnessError, match="FIELD verb"):
            g.calibrate_axes()


# --------------------------------------------------------------------------- transitions


def test_cross_reports_a_crossing_as_a_record(game):
    fake = FakeGame(game)
    fake.gateway = (300.0, 300.0, 700.0, 700.0, 30821)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        record = g.cross(450.0, 450.0, expect=30821)
        assert record["landed"] == 30821 and record["from"] == 30820


def test_find_transitions_refuses_a_confident_empty_answer(game):
    """'There is no gateway' and 'I never walked that bearing' are opposite findings.

    The only gateway this verb ever found sat at ~950 units against a shipped default radius of 420.
    """
    fake = FakeGame(game, walkmesh=(-40.0, -40.0, 40.0, 40.0))     # boxed in: no bearing is sweepable
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        with pytest.raises(HarnessError, match="never actually walked|could not calibrate|free axis"):
            g.find_transitions(radius=1200.0, bearings=4, timeout=2.0)


# --------------------------------------------------------------------------- assertion hygiene


def test_expect_text_refuses_an_empty_fragment(game):
    """'' in anything is True -- expect_text('') passed against an empty screen."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError, match="non-empty fragment"):
            g.expect_text("")


def test_expect_text_requires_a_box_to_actually_be_open(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        assert g.expect_text("Potion", timeout=0.8) is False
        fake.say("Received a Potion!")
        published(g, lambda s: s.dialog_open)
        assert g.expect_text("Potion", timeout=3.0) is True


def test_expect_flag_auto_watches_instead_of_reporting_a_false_failure(game):
    """An unwatched bit publishes nothing, and `None is False` is False -- so it read as a FAILURE."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        assert g.expect_flag(8712, False, timeout=3.0) is True
        assert 8712 in fake.watch


def test_watch_refuses_a_negative_bit_that_would_corrupt_the_channel(game):
    """-1 >> 3 == -1 passes the agent's bound test, then throws with the key already in the buffer.

    Every state.json after that is invalid JSON, and the driver reads that as 'the deployed engine
    predates s83' about a perfectly healthy game.
    """
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError, match="outside gEventGlobal"):
            g.watch(-1)
        g.press("confirm")                         # the channel is still usable


def test_timescale_zero_is_refused(game):
    """At scale 0 the engine runs no logical ticks while the harness keeps counting render frames."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError, match="pauses the game"):
            g.timescale(0)


def test_report_json_is_not_green_with_zero_checks(game):
    """A run that recorded nothing proved nothing; 'passed: true' there is the purest false green."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
    report = json.loads((game / "run" / "report.json").read_text(encoding="utf-8"))
    assert report["verdict"] == "proved-nothing"
    assert report["passed"] is False and report["checks_recorded"] == 0


def test_shot_with_a_space_in_the_name_still_arrives(game):
    """The request line is split on whitespace, so the agent saw a different name than we polled."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        path = g.shot("after chest")
        assert path.exists() and path.name == "after_chest.png"


# --------------------------------------------------------------------------- dialogue + menus


def test_interact_refuses_to_credit_a_box_that_was_already_open(game):
    """Otherwise a probe of an inert spot returns the PREVIOUS object's dialogue as its own."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        fake.say("An older box nobody closed.")
        published(g, lambda s: s.dialog_open)
        with pytest.raises(HarnessError, match="already open"):
            g.interact()


def test_menu_labels_refuses_to_press_blind(game):
    """With no menu open those 30 presses go to whatever IS live -- on a field, they walk him."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError, match="nothing to walk"):
            g.menu_labels()


def test_menu_labels_reads_the_engines_own_highlight(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        fake.open_menu(["Item", "Ability", "Equip", "Status"])
        published(g, lambda s: s.menu_label == "Item")
        assert g.menu_labels() == ["Item", "Ability", "Equip", "Status"]


def test_options_refuses_when_the_index_spaces_diverge(game):
    """A disabled line is REMOVED from the names while SelectChoice still counts it.

    So options()[i] is not what select(i) lands on, and the scenario confirms a branch it never
    named -- reporting green for a branch it never tested.
    """
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        fake.offer(["Mognet", "Tetra Master"], active=[0, 2, 3])       # 3 selectable, 2 named
        fake.choice.pop("active")                                      # an engine that does not publish it
        published(g, lambda s: s.choice is not None)
        with pytest.raises(HarnessError, match="different index spaces"):
            g.options()


def test_option_index_maps_through_the_published_active_indexes(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        fake.offer(["Mognet", "Tetra Master", "Nothing"], active=[0, 2, 4])
        published(g, lambda s: s.choice is not None)
        assert g.option_index("Tetra Master") == 2
        assert g.option_index("Nothing") == 4


def test_options_drops_the_header_when_the_spaces_agree(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        fake.offer(["Yes", "No"], header="Really?")
        published(g, lambda s: s.choice is not None)
        assert g.options() == ["Yes", "No"]


# --------------------------------------------------------------------------- channel diagnosis


def test_classify_names_the_reason_state_is_absent(game):
    ch = Channel(game)
    ch.reset()
    assert ch.classify().startswith("MISSING")
    (ch.dir / "state.json").write_text("{ not json", encoding="utf-8")
    assert ch.classify().startswith("UNPARSEABLE")
    (ch.dir / "state.json").write_text(json.dumps({"frame": 1, "armed": False}), encoding="utf-8")
    assert ch.classify().startswith("DISARMED")
    (ch.dir / "state.json").write_text(json.dumps({"frame": 1}), encoding="utf-8")
    os.utime(ch.dir / "state.json", (time.time() - 600, time.time() - 600))
    assert ch.classify().startswith("STALE")


def test_a_run_refuses_to_start_when_the_engine_will_not_sandbox_saves(game):
    """MEASURED 2026-08-31: an ordinary newgame()+warp() rewrote the owner's save containers.

    EventEngine autosaves on field entry and DisableAutoSave is 0 on this install, so the opening
    every scenario shares was stamping a scenario-zero autosave over a real player's game. The
    engine now redirects its save path while armed -- and the driver must CHECK that, because a
    sandbox nobody verified is exactly the kind of guard that silently stops working.
    """
    fake = FakeGame(game)
    fake.save_sandboxed = False
    with pytest.raises(HarnessError, match="did NOT redirect its save path"):
        with session(game, fake):
            pass


def test_the_players_saves_are_copied_before_the_game_is_launched(game):
    """Belt to the sandbox's braces, and it works on an engine too old to have one."""
    saves = game / "player-saves"
    saves.mkdir()
    (saves / "SavedData_ww.dat").write_bytes(b"the owner's game")
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
    assert (game / "run" / "saves-before" / "SavedData_ww.dat").read_bytes() == b"the owner's game"


# ======================================================================================
# THE SUITE RUNNER
#
# Many scenarios, one launch. The value is throughput; the risk is that a shared launch
# means shared state, so a scenario that leaves the game somewhere odd starts producing
# failures that belong to the RUNNER and get reported against the game. Every test here
# guards that boundary.
# ======================================================================================


def _manifest(game, body: str) -> pathlib.Path:
    path = game / "suite.toml"
    path.write_text(body, encoding="utf-8")
    return path


def _scenario(game, name: str, body: str) -> str:
    """Write a scenario file under the TEST's own tmp_path and return the path relative to it.

    ⚠ NOT under the repo. `load_manifest(path, root)` takes the root it resolves against precisely so
    this can be pinned -- the same "pin the path through a seam, never touch the real thing" rule the
    deploy tooling learned the hard way. An earlier version wrote into a single shared
    `REPO/_suite_test_scenarios` and rmtree'd it in an autouse fixture, which is fine serially and
    destroys itself under `pytest -n 6`: the nightly gate runs exactly that, and the tests would have
    deleted each other's files mid-run. It also left stray .py files in the repo whenever a run was
    interrupted.
    """
    d = game / "scenarios"
    d.mkdir(exist_ok=True)
    (d / f"{name}.py").write_text(body, encoding="utf-8")
    return f"scenarios/{name}.py"


def test_soft_reset_needs_all_six_buttons_on_one_frame(game):
    """Six separate presses never overlap -- they must go in ONE request to share a Down edge."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        assert fake.ui_state == "FieldHUD"
        g.soft_reset()
        assert fake.soft_resets == 1, "the combo never registered on a single frame"
        assert g.state.ui_state == "Title"


def test_soft_reset_reports_honestly_when_the_engine_has_it_disabled(game):
    """`[Control] SoftReset` defaults to 0 in the engine. A ladder rung that cannot exist must say so."""
    fake = FakeGame(game)
    fake.soft_reset_enabled = False
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError, match="SoftReset"):
            g.soft_reset(timeout=2.0)


def test_restore_baseline_climbs_until_the_precondition_actually_holds(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)                                     # now on a field: NOT the baseline
        ok, why = g.at_baseline()
        assert not ok and "Title" in why
        ok, why = g.restore_baseline()
        assert ok, why
        assert g.state.ui_state == "Title"


def test_a_scenario_that_cannot_be_given_a_baseline_is_poisoned_not_failed(game):
    """It never ran, so it cannot have failed -- and blaming the game for the runner's own
    inability to clean up is the exact mistake this arc keeps making."""
    fake = FakeGame(game)
    fake.soft_reset_enabled = False                 # the ladder cannot reach the title
    rel = _scenario(game, "never_runs", "def run(g):\n    g.check(True, 'ran')\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{rel}"\n')
    with session(game, fake) as g:
        boot(g)                                     # leave it off the baseline on purpose
        meta, scenarios = load_manifest(path, game)
        runner = SuiteRunner(g, scenarios, meta=meta, verbose=False)
        results = runner.run()
    assert [r["verdict"] for r in results] == ["poisoned"]
    assert not runner.passed
    assert "never ran" in results[0]["detail"]


def test_a_scenario_that_records_no_checks_is_proved_nothing(game):
    fake = FakeGame(game)
    rel = _scenario(game, "asserts_nothing", "def run(g):\n    g.newgame(settle=0)\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{rel}"\n')
    with session(game, fake) as g:
        meta, scenarios = load_manifest(path, game)
        runner = SuiteRunner(g, scenarios, meta=meta, verbose=False)
        results = runner.run()
    assert results[0]["verdict"] == "proved-nothing"
    assert not runner.passed


def test_a_raising_scenario_is_an_error_and_the_next_one_still_runs(game):
    """The point of a suite is that one bad member does not cost the rest of the launch."""
    fake = FakeGame(game)
    bad = _scenario(game, "explodes", "def run(g):\n    g.newgame(settle=0)\n    raise ValueError('boom')\n")
    good = _scenario(game, "fine", "def run(g):\n    g.newgame(settle=0)\n    g.check(True, 'still ran')\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{bad}"\n\n[[scenario]]\npath="{good}"\n')
    with session(game, fake) as g:
        meta, scenarios = load_manifest(path, game)
        runner = SuiteRunner(g, scenarios, meta=meta, verbose=False)
        results = runner.run()
    assert [r["verdict"] for r in results] == ["error", "pass"]
    assert "boom" in results[0]["detail"]
    assert "traceback" in results[0]


def test_every_scenario_gets_a_clean_baseline_not_the_previous_ones_leftovers(game):
    """The second scenario calls newgame(), which REQUIRES the title -- so if the runner did not
    restore, it would fail with 'not at the title screen' and the failure would look like the
    game's."""
    fake = FakeGame(game)
    a = _scenario(game, "leaves_a_field", "def run(g):\n    g.newgame(settle=0)\n    g.warp(30810)\n    g.check(True, 'a')\n")
    b = _scenario(game, "needs_the_title", "def run(g):\n    g.newgame(settle=0)\n    g.check(True, 'b')\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{a}"\n\n[[scenario]]\npath="{b}"\n')
    with session(game, fake) as g:
        meta, scenarios = load_manifest(path, game)
        runner = SuiteRunner(g, scenarios, meta=meta, verbose=False)
        results = runner.run()
    assert [r["verdict"] for r in results] == ["pass", "pass"]
    assert runner.passed
    assert fake.soft_resets >= 1, "the runner never actually restored anything"


def test_a_held_button_does_not_leak_into_the_next_scenario(game):
    """`hold` is non-blocking and frame-counted, so a scenario that ends mid-hold leaves a button
    DOWN -- and the next scenario would be driven by it."""
    fake = FakeGame(game)
    a = _scenario(game, "ends_mid_hold",
                  "def run(g):\n    g.newgame(settle=0)\n    g.warp(30810)\n"
                  "    g.send('hold up 600', wait=False)\n    g.check(True, 'held')\n")
    b = _scenario(game, "expects_stillness",
                  "def run(g):\n    g.check(not g.state.held, 'no button is held on entry', str(g.state.held))\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{a}"\n\n[[scenario]]\npath="{b}"\n')
    with session(game, fake) as g:
        meta, scenarios = load_manifest(path, game)
        runner = SuiteRunner(g, scenarios, meta=meta, verbose=False)
        results = runner.run()
    assert [r["verdict"] for r in results] == ["pass", "pass"], results


def test_shots_are_namespaced_per_scenario(game):
    """Two scenarios both capturing "before" would otherwise overwrite each other in the one
    channel directory -- and the evidence lost is always the failing run's."""
    fake = FakeGame(game)
    a = _scenario(game, "shooter_a", "def run(g):\n    g.newgame(settle=0)\n    g.shot('before')\n    g.check(True, 'a')\n")
    b = _scenario(game, "shooter_b", "def run(g):\n    g.newgame(settle=0)\n    g.shot('before')\n    g.check(True, 'b')\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{a}"\n\n[[scenario]]\npath="{b}"\n')
    with session(game, fake) as g:
        meta, scenarios = load_manifest(path, game)
        runner = SuiteRunner(g, scenarios, meta=meta, verbose=False)
        runner.run()
        run_dir = runner.run_dir
    names = sorted(p.name for p in (run_dir).rglob("*.png"))
    assert any(n.startswith("01-shooter_a") for n in names), names
    assert any(n.startswith("02-shooter_b") for n in names), names


def test_the_first_failure_of_a_scenario_is_photographed(game):
    """In a suite, re-running to see what the screen looked like costs the whole suite."""
    fake = FakeGame(game)
    rel = _scenario(game, "fails_once",
                    "def run(g):\n    g.newgame(settle=0)\n"
                    "    g.check(False, 'first')\n    g.check(False, 'second')\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{rel}"\n')
    with session(game, fake) as g:
        meta, scenarios = load_manifest(path, game)
        runner = SuiteRunner(g, scenarios, meta=meta, verbose=False)
        results = runner.run()
        run_dir = runner.run_dir
    assert results[0]["verdict"] == "fail"
    # Scoped to the scenario's OWN directory: the session-level collect keeps a flat copy of every
    # shot too, so an unscoped glob counts the same image twice.
    shots = [p.name for p in (run_dir / "01-fails_once" / "shots").glob("*.png")]
    assert shots == ["01-fails_once-FAILED.png"], (
        f"expected exactly one failure shot -- only the FIRST failure is worth photographing, "
        f"and the second check must not add another. Got {shots}")


def test_each_check_carries_the_state_it_was_made_in(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.check(True, "something")
        row = g.checks[-1]
    assert "state" in row and row["state"]["ui_state"] == "FieldHUD"


def test_a_manifest_pointing_at_a_missing_scenario_is_refused(game):
    """A suite that silently skips a member reports a smaller pass than it claims."""
    path = _manifest(game, '[suite]\nname="t"\n\n[[scenario]]\npath="does/not/exist.py"\n')
    with pytest.raises(HarnessError, match="does not exist"):
        load_manifest(path, game)


def test_an_empty_manifest_is_refused(game):
    path = _manifest(game, '[suite]\nname="t"\n')
    with pytest.raises(HarnessError, match="lists no"):
        load_manifest(path, game)


def test_the_suite_report_tallies_every_verdict(game):
    fake = FakeGame(game)
    ok = _scenario(game, "rep_ok", "def run(g):\n    g.newgame(settle=0)\n    g.check(True, 'x')\n")
    bad = _scenario(game, "rep_bad", "def run(g):\n    g.newgame(settle=0)\n    g.check(False, 'y')\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{ok}"\n\n[[scenario]]\npath="{bad}"\n')
    with session(game, fake) as g:
        meta, scenarios = load_manifest(path, game)
        runner = SuiteRunner(g, scenarios, meta=meta, verbose=False)
        runner.run()
        run_dir = runner.run_dir
    report = json.loads((run_dir / "suite.json").read_text(encoding="utf-8"))
    assert report["tally"]["pass"] == 1 and report["tally"]["fail"] == 1
    assert report["passed"] is False
    assert len(report["scenarios"]) == 2


def test_newgame_settles_on_the_cold_title_only(game):
    """The settle exists because Memoria is still LOADING the first time the title appears.

    On a re-entry the game is loaded and the wait is pure dead time -- once per scenario, which in a
    ten-member suite is a minute and a half of nothing.
    """
    fake = FakeGame(game)
    with session(game, fake) as g:
        assert g._booted_once is False
        g.newgame(settle=0)
        assert g._booted_once is True
        g.soft_reset()
        started = time.time()
        g.newgame()                       # no explicit settle: must NOT pay the cold-title wait
        assert time.time() - started < 5.0


# ======================================================================================
# REGRESSIONS FROM THE SUITE-RUNNER AUDIT
#
# An adversarial pass over the runner (3 readers, 3 skeptics) confirmed 35 defects, two of
# them high. Everything below guards one of the fixes. Several exist because the audit's
# most useful finding was not a defect at all but a TEST THAT COULD NOT FAIL -- so each of
# these names, in its docstring, the thing to break to see it go red.
# ======================================================================================


def test_the_run_level_report_does_not_score_a_suite(game):
    """THE HIGH ONE. `report.json` said "passed": true for a suite whose members failed.

    Session._write_report derives a verdict from self.checks, and begin_scenario REBINDS that per
    scenario -- so under a suite it described only the last member and stamped a whole-run verdict on
    it, under the exact filename this tool documents as the run's report. Break it by deleting the
    `if self._suite_owned:` branch.
    """
    fake = FakeGame(game)
    bad = _scenario(game, "hi_bad", "def run(g):\n    g.newgame(settle=0)\n    g.check(False, 'no')\n")
    good = _scenario(game, "hi_good", "def run(g):\n    g.newgame(settle=0)\n    g.check(True, 'yes')\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{bad}"\n\n[[scenario]]\npath="{good}"\n')
    with session(game, fake) as g:
        meta, scenarios = load_manifest(path, game)
        runner = SuiteRunner(g, scenarios, meta=meta, verbose=False)
        runner.run()
        run_dir = runner.run_dir
    suite = json.loads((run_dir / "suite.json").read_text(encoding="utf-8"))
    report = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
    assert suite["passed"] is False
    assert report.get("passed") is not True, (
        "report.json must not claim a suite passed -- it can only see the last member's checks")
    assert report["verdict"] == "see suite.json"


def test_at_baseline_refuses_a_stale_document(game):
    """The one rung whose whole job is verification must not be satisfiable by a photograph.

    Every other predicate is as true of a hung agent's last state as of a live one. Break it by
    deleting the `st.age > LIVE_WITHIN` guard: a dead game whose final document says Title then reads
    "at the title, idle", the scenario is launched against a corpse, and it is filed as `error` --
    the runner blaming the game for the runner's own dead channel.
    """
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.soft_reset()
        ok, _ = g.at_baseline()
        assert ok, "a live game at the title IS the baseline"
        fake.stop()                                  # the agent stops publishing; the file remains
        time.sleep(2.5)
        ok, why = g.at_baseline()
        assert not ok and ("old" in why or "STALE" in why), why


def test_at_baseline_reports_a_fault_rather_than_a_disarm(game):
    """A faulted agent also disarms, so testing `armed` first threw away the explaining error."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        st = g.channel.state()
        raw = dict(st.raw)
        # Stop the publisher FIRST. Writing the document and then stopping races the fake's own
        # 240fps loop, which simply overwrites it -- and the test then measures the wrong document.
        fake.stop()
        raw.update({"faulted": True, "armed": False, "error": "something exploded",
                    "ui_state": "Title", "held": []})
        (g.channel.dir / "state.json").write_text(json.dumps(raw), encoding="utf-8")
        ok, why = g.at_baseline()
    assert not ok
    assert "faulted" in why and "something exploded" in why, why


def test_the_ladder_closes_a_menu_the_soft_reset_cannot_escape(game):
    """MEASURED IN-GAME: the soft-reset combo is swallowed inside a menu (soft_reset_reach.py).

    `UIKeyTrigger.Update` runs the menu handler first and it consumes Control.Select unconditionally.
    A menu is also where scenarios are most likely to end, and `warp` refuses outside FieldHUD -- so
    without a close-UI rung the ladder would poison every scenario after one that left a menu open.
    Break it by removing the `close whatever UI is open` rung from restore_baseline.
    """
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        fake.open_menu(["Item", "Ability"])
        published(g, lambda s: s.ui_state == "MainMenu")
        assert fake.soft_reset_enabled
        ok, why = g.restore_baseline()
    assert ok, f"the ladder could not escape a menu: {why}"
    assert "close" in why or "soft reset" in why


def test_the_soft_reset_alone_cannot_escape_a_menu(game):
    """The stand-in must be no more forgiving than the engine, or it certifies a ladder that
    cannot climb. Break it by deleting the fake's `if self.ui_state not in (...)` gate."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        fake.open_menu(["Item"])
        published(g, lambda s: s.ui_state == "MainMenu")
        with pytest.raises(HarnessError):
            g.soft_reset(timeout=2.0)
        assert fake.soft_resets == 0


def test_a_dead_game_poisons_the_rest_and_still_writes_the_report(game):
    """begin_scenario does a BLOCKING send, and out of the guard it took the whole run with it.

    Every remaining scenario got NO verdict -- not even poisoned -- and suite.json was never
    written, so the last machine-readable word about a suite that died at member 2 of 10 was a
    single PASS. Break it by moving begin_scenario back outside _run_one's try.
    """
    fake = FakeGame(game)
    a = _scenario(game, "dg_one", "def run(g):\n    g.newgame(settle=0)\n    g.check(True, 'ran')\n")
    b = _scenario(game, "dg_two", "def run(g):\n    g.check(True, 'never')\n")
    c = _scenario(game, "dg_three", "def run(g):\n    g.check(True, 'never')\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{a}"\n\n'
                           f'[[scenario]]\npath="{b}"\n\n[[scenario]]\npath="{c}"\n')
    with session(game, fake) as g:
        meta, scenarios = load_manifest(path, game)
        runner = SuiteRunner(g, scenarios, meta=meta, verbose=False)
        results = runner._run_one(1, 3, scenarios[0]) and None
        runner.results = []
        # kill the game after the first member, the way a crash would
        original = runner._run_one

        def kill_after_first(index, total, scenario):
            row = original(index, total, scenario)
            if index == 1:
                fake.returncode = -9
                fake.stop()
            return row

        runner._run_one = kill_after_first
        try:
            runner.run()
        except HarnessError:
            pass
        run_dir = runner.run_dir
        verdicts = [r["verdict"] for r in runner.results]
    assert len(verdicts) == 3, f"every scenario needs a verdict, got {verdicts}"
    assert verdicts[1:] == ["poisoned", "poisoned"], verdicts
    assert (run_dir / "suite.json").exists(), "the report must survive the runner's own failure"


def test_an_error_verdict_still_names_the_checks_that_failed_first(game):
    """`error` alone reads as "it blew up" -- the tally shows zero fails and real findings vanish."""
    fake = FakeGame(game)
    rel = _scenario(game, "fails_then_raises",
                    "def run(g):\n    g.newgame(settle=0)\n"
                    "    g.check(False, 'the door was locked')\n"
                    "    raise ValueError('and then this')\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{rel}"\n')
    with session(game, fake) as g:
        meta, scenarios = load_manifest(path, game)
        runner = SuiteRunner(g, scenarios, meta=meta, verbose=False)
        results = runner.run()
    assert results[0]["verdict"] == "error"
    assert "1 check(s) had already FAILED" in results[0]["detail"]
    assert "the door was locked" in results[0]["detail"]


def test_begin_scenario_releases_a_held_button_on_the_happy_path(game):
    """reset_agent is documented as THE isolation primitive and was only reached as a RECOVERY rung.

    So when the previous scenario ended tidily -- the common case -- held buttons, a stale watch list
    and a changed timescale carried straight into the next member. Break it by removing the
    `self.reset_agent()` call from begin_scenario. (FF9's soft reset does not release the player's
    buttons, and the stand-in models that, so nothing else would clear them.)
    """
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        g.send("hold up 600", wait=False)
        published(g, lambda s: bool(s.held))
        g.begin_scenario("01-next")
        published(g, lambda s: not s.held, timeout=5.0)
        assert not g.state.held


def test_the_check_list_does_not_carry_into_the_next_scenario(game):
    """Break it by deleting `self.checks = []` from begin_scenario: a proved-nothing scenario after
    a passing one would then inherit its checks and be reported PASS."""
    fake = FakeGame(game)
    a = _scenario(game, "cl_one", "def run(g):\n    g.newgame(settle=0)\n    g.check(True, 'mine')\n")
    b = _scenario(game, "cl_two", "def run(g):\n    g.newgame(settle=0)\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{a}"\n\n[[scenario]]\npath="{b}"\n')
    with session(game, fake) as g:
        meta, scenarios = load_manifest(path, game)
        runner = SuiteRunner(g, scenarios, meta=meta, verbose=False)
        results = runner.run()
    assert [r["verdict"] for r in results] == ["pass", "proved-nothing"]
    assert results[1]["checks"] == []


def test_an_unknown_manifest_key_is_refused(game):
    """A `timeout` key was accepted, stored and never read -- worse than not offering it, because an
    author would reasonably read it as a hang guard and get none."""
    rel = _scenario(game, "uk", "def run(g):\n    pass\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{rel}"\ntimeout=30\n')
    with pytest.raises(HarnessError, match="unknown key"):
        load_manifest(path, game)


def test_collect_finds_shots_written_under_a_sanitised_label(game):
    """`shot()` rewrites illegal characters, so globbing the RAW label collected nothing -- and what
    went uncollected was the failing scenario's evidence."""
    fake = FakeGame(game)
    rel = _scenario(game, "spacey", "def run(g):\n    g.newgame(settle=0)\n    g.shot('frame')\n    g.check(True, 'x')\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\nlabel="walk: north"\npath="{rel}"\n')
    with session(game, fake) as g:
        meta, scenarios = load_manifest(path, game)
        runner = SuiteRunner(g, scenarios, meta=meta, verbose=False)
        results = runner.run()
    assert results[0]["shots"], "the scenario's screenshot was never collected"


# ======================================================================================
# THE BATTLE BLOCK
#
# The pillar the state channel was 100% dark on. It was deliberately deferred out of the
# s83 rev2 batch for one reason: "adding a battle block without extending the stand-in
# reproduces the existing menu lane's defect at ten times the surface" -- a green offline
# suite that observed nothing. The stand-in models a battle now, so these can fail.
#
# The through-line is that almost every battle value is AMBIGUOUS or STALE rather than
# absent, which makes a plausible wrong answer the default failure mode here.
# ======================================================================================


def test_battle_state_is_dark_outside_a_battle(game):
    """Every value in FF9Battle is STALE, not absent, after a fight: btl_phase still reads the last
    one's, battleMapIndex is the last scene, btl_bonus is the last rewards. Publishing them on a
    field hands a scenario a complete, plausible, entirely historical battle. Break it by making the
    agent emit the full block unconditionally."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        st = g.state
        assert st.in_battle is False
        assert st.units() == []
        # The MID-BATTLE keys are the ones that must be absent. result/scene/bonus ride alongside
        # epoch and are published always -- they are the answer only AFTER the fight, and the epoch
        # is what says which fight they belong to.
        assert "units" not in st.battle and "phase" not in st.battle and "turn" not in st.battle
        assert st.battle_epoch > 0, "the epoch is published always -- it is the start EDGE"
        assert "result" in st.battle and "bonus" in st.battle


def test_a_battle_is_recognised_by_its_epoch_not_by_its_result(game):
    """btl_result is 0 DURING a battle and BEFORE any has ever run. Only the epoch disambiguates."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        before = g.state.battle_epoch
        assert g.state.battle_result == 0, "0 before any battle -- indistinguishable from in-progress"
        st = g.start_battle(105)
        assert st.in_battle and st.battle_epoch == before + 1
        assert st.battle_result == 0, "still 0 DURING the battle -- this is the ambiguity"
        assert st.battle.get("scene") == 105


def test_wait_battle_does_not_accept_a_diorama(game):
    """IsBattleScene() is also true for BattleMapDebug and SpecialEffectDebugRoom, which run under
    isDebug -- where the engine suppresses the auto-end and the battle CAN NEVER FINISH. Counting
    that as "in a battle" is how a result assertion becomes vacuous. Break it by dropping the
    `not b.get("debug")` term from State.in_battle."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        fake.start_battle(105, debug=True)
        published(g, lambda s: s.battle.get("active") is True)
        assert g.state.battle.get("active") is True
        assert g.state.in_battle is False, "a diorama must not read as a real battle"


def test_waiting_for_a_result_in_a_diorama_is_refused_rather_than_hung(game):
    """Under isDebug the battle cannot end, so this wait could never succeed. Refusing is the honest
    answer; hanging until a timeout would report it as the game failing to finish a fight."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        fake.start_battle(105, debug=True)
        published(g, lambda s: s.battle.get("debug") is True)
        with pytest.raises(HarnessError, match="isDebug"):
            g.wait_battle_over(timeout=2.0)


def test_units_carry_both_the_logical_and_the_raw_hp(game):
    """CurrentHp is NOT Data.cur.hp -- it routes through btl_para.GetLogicalHP, which subtracts
    10000 for a FLG_NON_DYING_BOSS enemy under [Battle] CustomBattleFlagsMeaning = 1. The HUD shows
    the logical value; the AI script reads the raw one as B_MEMBER (36)/(35). An assertion on "the"
    HP is right about one and wrong about the other depending on the enemy."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        st = g.start_battle(105)
        boss = st.unit("Masked Man")
        assert boss is not None
        assert boss["hp"] == 1200 and boss["hp_raw"] == 11200, boss
        zidane = st.unit("Zidane")
        assert zidane["hp"] == zidane["hp_raw"], "an ordinary unit's two HPs agree"


def test_alive_is_the_death_status_not_zero_hp(game):
    """A unit under a DeathChanger effect sits at 0 HP ALIVE, and the HUD's own liveness test is the
    status bit. Break it by publishing `cur.hp != 0` as `alive`."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        st = g.start_battle(105)
        vivi = st.unit("Vivi")
        assert vivi["hp"] == 0 and vivi["alive"] is True, vivi
        assert len(st.units(alive=True)) == 3
        assert st.units(player=True) and len(st.units(player=False)) == 1


def test_expect_battle_result_names_what_it_got(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        g.start_battle(105)

        def finish():
            time.sleep(0.3)
            fake.end_battle(result=1)

        threading.Thread(target=finish, daemon=True).start()
        assert g.expect_battle_result("victory", timeout=10.0) is True
        assert g.state.battle_epoch > 0
    assert g.checks[-1]["ok"] is True


def test_a_wrong_battle_result_fails_with_the_name_of_the_real_one(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        g.start_battle(105)

        def finish():
            time.sleep(0.3)
            fake.end_battle(result=3)          # defeat

        threading.Thread(target=finish, daemon=True).start()
        assert g.expect_battle_result("victory", timeout=10.0) is False
    assert "defeat" in g.checks[-1]["detail"]


def test_an_unknown_result_name_is_refused_locally(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError, match="unknown battle result"):
            g.expect_battle_result("triumph")


def test_the_rewards_are_readable_after_a_victory(game):
    """btl_bonus is zeroed at battle START, not at the end, so after a victory it IS that victory's
    haul -- but on a field it is the LAST battle's, which is why it is only published in a battle."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        g.start_battle(105)
        assert g.state.battle["bonus"]["exp"] == 0
        fake.battle_bonus = {"exp": 120, "gil": 88, "ap": 3, "items": 1}
        published(g, lambda s: s.battle.get("bonus", {}).get("exp") == 120)
        assert g.state.battle["bonus"]["gil"] == 88


def test_battle_command_goes_through_the_engines_own_entry_point(game):
    """The deterministic path: issue an exact command instead of steering a cursor -- the difference
    between testing a damage formula and testing NGUI navigation."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        g.start_battle(105)
        # Past the opening camera first: a command injected during the intro is refused (and in the
        # real engine, before that refusal existed, it froze the fight).
        published(g, lambda s: s.commands_enabled)
        g.battle_command(0, 4, sub=1, target=16, cursor=2)
        published(g, lambda s: True)
        assert fake.battle_commands == [[0, 4, 1, 16, 2]]


def test_battle_command_outside_a_battle_is_refused(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        with pytest.raises(HarnessError, match="no battle HUD|refused"):
            g.battle_command(0, 4)


def test_start_battle_needs_a_field_to_leave_from(game):
    """The engine routes the transition by the FIELD's nextMode, so this is refused before it can
    become a silent no-op followed by a timeout blaming the battle scene."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        fake.ui_state = "MainMenu"
        published(g, lambda s: s.ui_state == "MainMenu")
        with pytest.raises(HarnessError, match="needs a field"):
            g.start_battle(105)


# ---------------------------------------------------------------------------------------------
# PLAYING a battle (s83 rev 4). Everything above observes one; these take turns in it.
# ---------------------------------------------------------------------------------------------


def _fighting(game, fake, *, turns=True):
    """A session standing in a real battle, PAST the opening camera, gauges optionally running.

    ⚠ The wait for `commands_enabled` is not politeness. Through the intro the engine has not yet
    run InitialBattle(), so CurrentPlayerIndex and the ready/done lists still hold the PREVIOUS
    fight's contents -- and a command injected there freezes the battle solid. Every test that
    takes a turn has to start after that window, the same as every scenario does.
    """
    g = session(game, fake)
    g.__enter__()
    boot(g)
    g.warp(30810)
    g.start_battle(105)
    if turns:
        fake.atb_gain = 400
    published(g, lambda s: s.commands_enabled)
    return g


def test_a_reissued_hold_never_drops_the_button(game):
    """THE DEFECT THAT COST THIS ARC A FLEE. Scheduling a hold set _downFrame = frameCount + 1, so
    re-issuing one while it was already down made the button read UP for exactly one frame. Nothing
    SAMPLING the button notices; anything counting UNBROKEN held time restarts from zero -- and
    BattleHUD._runCounter, which gates the escape roll, is exactly that. Held every 0.8s against a
    1.0s threshold, the roll never fired once while the character ran on screen the whole time.

    Both behaviours are exercised here so the fix is pinned by a contrast rather than by an
    assertion that would also pass if _extend were quietly reverted to _schedule."""
    fake = FakeGame(game)
    fake.frame = 100
    fake._schedule("l1", 60)
    fake.frame = 130
    assert fake._is_held("l1")

    fake._extend("l1", 60)
    assert fake._is_held("l1"), "extending a live hold must not drop the frame it arrives on"
    assert fake.held["l1"] == 190, "and it must LENGTHEN the window, not shorten it"

    fake._schedule("l1", 60)
    assert not fake._is_held("l1"), (
        "the old behaviour, kept as the contrast: restarting a hold in progress un-presses the "
        "button for the frame the request lands on")


def test_extending_a_hold_never_shortens_it(game):
    """Overlapping holds must COMPOSE. A shorter re-issue that truncated a longer one would end a
    press early, which reads as the game ignoring input rather than as the driver cutting it off."""
    fake = FakeGame(game)
    fake.frame = 10
    fake._extend("r1", 600)
    fake.frame = 20
    fake._extend("r1", 5)
    assert fake.held["r1"] == 611


def test_flee_holds_through_the_roll_and_reports_the_escape(game):
    fake = FakeGame(game)
    fake.escape_rate = 1.0
    g = _fighting(game, fake, turns=False)
    try:
        assert g.flee(timeout=10.0) is True
        published(g, lambda s: s.battle_result != 0)
        assert g.state.battle_result_name == "escape"
    finally:
        g.__exit__(None, None, None)


def test_flee_reports_bad_luck_as_bad_luck(game):
    """A roll that does not land is VARIANCE, not a defect: the rate is single digits per second
    against a levelled enemy. Returning False (rather than raising) is what lets a scenario decide
    whether to keep trying, and it must not be confused with the input never arriving."""
    fake = FakeGame(game)
    fake.escape_rate = 0.0
    g = _fighting(game, fake, turns=False)
    try:
        assert g.flee(timeout=3.0) is False
        assert g.state.in_battle, "a failed roll leaves you in the fight, not out of it"
    finally:
        g.__exit__(None, None, None)


def test_flee_raises_when_the_engine_never_saw_the_hold(game):
    """The other failure, which looks identical from outside and means something else entirely: the
    bumpers are down and btl_escape_key never goes high, so the input is not reaching BattleHUD at
    all. Reporting that as an unlucky roll would send the next reader looking at the dice."""
    fake = FakeGame(game)
    fake.escape_rate = 1.0
    fake.deaf_bumpers = True
    g = _fighting(game, fake, turns=False)
    try:
        with pytest.raises(HarnessError, match="never went high|not reaching"):
            g.flee(timeout=2.0)
    finally:
        g.__exit__(None, None, None)


def test_flee_releases_the_bumpers_even_when_it_fails(game):
    """`hold` is non-blocking, so a bumper left down leaks into whatever runs next -- and these two
    in particular keep the party trying to run in the NEXT scenario's battle."""
    fake = FakeGame(game)
    fake.escape_rate = 0.0
    g = _fighting(game, fake, turns=False)
    try:
        g.flee(timeout=2.0)
        published(g, lambda s: not s.battle.get("escape_held"))
        assert not fake._is_held("l1") and not fake._is_held("r1")
    finally:
        g.__exit__(None, None, None)


def test_flee_refuses_a_scene_that_forbids_running(game):
    """btl_escape_key is set BEFORE Runaway is tested, so the character plays the running animation
    indefinitely and nothing on screen says it is futile. Holding there is not a slow escape, it is
    no escape -- and returning False would blame the dice for a rule the scene declared up front."""
    fake = FakeGame(game)
    fake.scene_runaway = False
    g = _fighting(game, fake, turns=False)
    try:
        published(g, lambda s: s.can_escape is False)
        with pytest.raises(HarnessError, match="forbids running"):
            g.flee(timeout=2.0)
    finally:
        g.__exit__(None, None, None)


def test_menus_publishes_what_the_character_can_do(game):
    fake = FakeGame(game)
    g = _fighting(game, fake, turns=False)
    try:
        menu = g.menus(0)
        assert menu["slot"] == 0 and menu["epoch"] == fake.battle_epoch
        names = [c["name"] for c in menu["commands"]]
        assert "Attack" in names and "Item" in names
        assert g.state.command("Attack")["sub"] == 176
        assert g.state.ability("Fire")["mp"] == 6
        assert g.state.item("Potion")["count"] == 9
    finally:
        g.__exit__(None, None, None)


def test_a_menu_from_the_previous_battle_is_not_this_battle_s(game):
    """The engine leaves its battle fields holding the LAST fight's contents, and the stand-in does
    the same on purpose. Without the epoch stamp a driver would answer questions about a fight that
    already ended -- confidently, and with a complete, plausible menu."""
    fake = FakeGame(game)
    g = _fighting(game, fake, turns=False)
    try:
        g.menus(0)
        assert g.state.menu_is_for(0)
        fake.end_battle(1)
        published(g, lambda s: not s.in_battle)
        fake.start_battle(106)
        published(g, lambda s: s.in_battle and s.battle_epoch == fake.battle_epoch)
        assert not g.state.menu_is_for(0), (
            "the stale menu is still published -- what makes it safe is that it no longer claims "
            "to be about this battle")
    finally:
        g.__exit__(None, None, None)


def test_menus_refuses_a_slot_with_no_party_member(game):
    """CollectNetMenus indexes _abilityDetailDict unguarded, so this is a KeyNotFoundException in
    the engine -- which would disarm the agent mid-scenario instead of failing one step."""
    fake = FakeGame(game)
    g = _fighting(game, fake, turns=False)
    try:
        with pytest.raises(HarnessError, match="ability detail|no party"):
            g.menus(4)          # the enemy slot
    finally:
        g.__exit__(None, None, None)


def test_menus_without_a_slot_needs_someone_to_be_asked(game):
    fake = FakeGame(game)
    g = _fighting(game, fake, turns=False)
    try:
        with pytest.raises(HarnessError, match="asking nobody|turn"):
            g.menus()
    finally:
        g.__exit__(None, None, None)


def test_act_commits_the_named_command_with_the_engines_own_arguments(game):
    """By NAME, and the arguments come from the engine's own resolution -- a table kept here would
    be a second copy of a decision that depends on preset, trance and equipment."""
    fake = FakeGame(game)
    g = _fighting(game, fake)
    try:
        rec = g.act("Attack", slot=0)
        assert fake.battle_commands[-1] == [0, 1, 176, 16, 0], fake.battle_commands
        assert rec["target"] == "Masked Man"
    finally:
        g.__exit__(None, None, None)


def test_act_resolves_an_ability_to_its_parent_command(game):
    """"Fire" is not a command -- it lives under one. Making the caller find the parent is how a
    scenario ends up hard-coding a command id that is wrong for a tranced character."""
    fake = FakeGame(game)
    g = _fighting(game, fake)
    try:
        g.act("Fire", slot=0)
        assert fake.battle_commands[-1] == [0, 4, 20, 16, 0]
    finally:
        g.__exit__(None, None, None)


def test_act_refuses_an_ability_that_is_learned_but_not_castable(game):
    """enabled=false is LEARNED BUT GREYED (no MP, silenced). Committing it would exercise a path
    the player cannot reach, and pass."""
    fake = FakeGame(game)
    g = _fighting(game, fake)
    try:
        with pytest.raises(HarnessError, match="not castable"):
            g.act("Blizzard", slot=0)
        assert not fake.battle_commands
    finally:
        g.__exit__(None, None, None)


def test_act_refuses_a_submenu_as_though_it_were_a_move(game):
    fake = FakeGame(game)
    g = _fighting(game, fake)
    try:
        with pytest.raises(HarnessError, match="sub-menu"):
            g.act("Blk Mag", slot=0)
    finally:
        g.__exit__(None, None, None)


def test_act_refuses_a_command_the_hud_would_not_draw(game):
    """offered=false is a command that resolves for the character and that the player never sees --
    an ability command with nothing learned. Sending it is a claim about a move nobody had."""
    fake = FakeGame(game)
    g = _fighting(game, fake)
    try:
        with pytest.raises(HarnessError, match="would not draw"):
            g.act("Swd Art", slot=0)
    finally:
        g.__exit__(None, None, None)


def test_act_names_what_is_available_when_the_move_is_unknown(game):
    fake = FakeGame(game)
    g = _fighting(game, fake)
    try:
        with pytest.raises(HarnessError, match="Attack"):
            g.act("Ultima", slot=0)
    finally:
        g.__exit__(None, None, None)


def test_act_targets_a_named_combatant(game):
    fake = FakeGame(game)
    g = _fighting(game, fake)
    try:
        g.act("Attack", slot=0, target="Vivi")
        assert fake.battle_commands[-1][3] == 2, "Vivi's btl_id bit, not her slot index"
    finally:
        g.__exit__(None, None, None)


def test_act_aims_a_forced_group_ability_at_the_whole_side(game):
    """TargetType.AllEnemy has no single-target form in the UI: the cursor IS the group. Passing one
    bit would be a command the player could not have produced."""
    fake = FakeGame(game)
    g = _fighting(game, fake)
    try:
        rec = g.act("Meteor", slot=0)
        assert rec["cursor"] == 2 and rec["target_id"] == 16
    finally:
        g.__exit__(None, None, None)


def test_act_aims_a_revival_item_at_a_fallen_ally(game):
    """for_dead flips the whole target rule: the living ally a Potion wants is the wrong answer for
    a Phoenix Down, and picking the default would waste the turn on someone standing up."""
    fake = FakeGame(game)
    g = _fighting(game, fake)
    try:
        published(g, lambda s: s.in_battle)
        for u in fake.battle_units:
            if u["name"] == "Vivi":
                u["alive"] = False
        published(g, lambda s: any(not u["alive"] for u in s.units(player=True)))
        rec = g.act("Phoenix Down", slot=0)
        assert rec["target_id"] == 2 and "Vivi" in rec["target"]
    finally:
        g.__exit__(None, None, None)


def test_act_is_closed_loop_on_the_turn_being_taken(game):
    """"The step acked" only means the engine did not throw. What matters is that the HUD stopped
    asking this slot -- which is what SendNetCommand achieves by adding it to InputFinishList, and
    what would NOT happen if the command had been refused."""
    fake = FakeGame(game)
    g = _fighting(game, fake)
    try:
        # ⚠ PINNED so the assertion cannot race the stand-in's own resolution: the slot leaves
        # InputFinishList when its command executes, and this is about it being IN there.
        fake.cmd_resolve_frames = 10 ** 9
        slot = g.wait_turn(timeout=10.0)
        g.act("Attack", slot=slot)
        assert slot in g.state.battle.get("turn", {}).get("done", [])
        assert g.state.turn_slot != slot
    finally:
        g.__exit__(None, None, None)


def test_act_refuses_a_slot_whose_turn_is_already_spent(game):
    """The engine's own refusal, surfaced with its reason instead of a bare "the HUD refused"."""
    fake = FakeGame(game)
    fake.cmd_resolve_frames = 10 ** 9      # the refusal must not race the resolution
    g = _fighting(game, fake)
    try:
        g.act("Attack", slot=0)
        with pytest.raises(HarnessError, match="already in flight|turn is spent"):
            g.act("Attack", slot=0)
    finally:
        g.__exit__(None, None, None)


def test_wait_turn_raises_when_the_battle_ends_first(game):
    """Returning -1 would let a caller press on and command a slot in a fight that is over."""
    fake = FakeGame(game)
    g = _fighting(game, fake, turns=False)
    try:
        fake.end_battle(1)
        with pytest.raises(HarnessError, match="ended before"):
            g.wait_turn(timeout=4.0)
    finally:
        g.__exit__(None, None, None)


def test_fight_plays_a_battle_through_to_a_result(game):
    fake = FakeGame(game)
    fake.enemy_hit = 0                 # the enemy is not the thing under test here
    g = _fighting(game, fake)
    try:
        assert g.fight(timeout=60.0, finish=False) == 1
        assert g.state.battle_result_name == "victory"
        assert len(fake.battle_commands) >= 4, "1200 HP at 260 a hit is five turns, not one"
    finally:
        g.__exit__(None, None, None)


def test_fight_takes_the_loss_as_readily_as_the_win(game):
    """A harness that can only report victories is a harness that will one day report a victory it
    did not see. The result is read, not assumed."""
    fake = FakeGame(game)
    fake.enemy_hit = 5000
    g = _fighting(game, fake)
    try:
        assert g.fight(timeout=60.0, finish=False) == 3
    finally:
        g.__exit__(None, None, None)


def test_fight_refuses_the_diorama_instead_of_timing_out_in_it(game):
    """Under isDebug the engine suppresses the auto-end, so the fight can never finish. Playing it
    out would burn the whole timeout and prove nothing at all."""
    fake = FakeGame(game)
    g = session(game, fake)
    with g:
        boot(g)
        g.warp(30810)
        fake.start_battle(105, debug=True)
        published(g, lambda s: s.battle.get("debug"))
        with pytest.raises(HarnessError, match="isDebug|diorama"):
            g.fight(timeout=5.0)


def test_fight_reports_a_stalemate_rather_than_grinding_on(game):
    fake = FakeGame(game)
    fake.enemy_hit = 0
    g = _fighting(game, fake)
    try:
        with pytest.raises(HarnessError, match="took 2 turns without reaching"):
            g.fight(timeout=60.0, max_turns=2)
    finally:
        g.__exit__(None, None, None)


def test_a_custom_policy_chooses_the_move(game):
    fake = FakeGame(game)
    fake.enemy_hit = 0
    g = _fighting(game, fake)
    try:
        g.fight(policy=lambda st, slot: {"command": "Fire"}, timeout=60.0, finish=False)
        assert all(c[1] == 4 for c in fake.battle_commands), fake.battle_commands
    finally:
        g.__exit__(None, None, None)


def test_the_play_verbs_refuse_an_older_engine(game):
    """A DLL predating rev 4 has no `menus` verb and refuses battlecmd for the local slot, so every
    one of these would fail somewhere deep with a message about the battle. Named at the door."""
    fake = FakeGame(game)
    fake.protocol = 3
    g = _fighting(game, fake, turns=False)
    try:
        published(g, lambda s: s.protocol == 3)
        for call in (lambda: g.menus(0), lambda: g.act("Attack", slot=0), lambda: g.fight()):
            with pytest.raises(HarnessError, match="needs protocol 4"):
                call()
    finally:
        g.__exit__(None, None, None)


def test_the_turn_slot_is_not_believed_during_the_opening_camera(game):
    """THE STALE TURN, and the most expensive bug in this revision.

    CurrentPlayerIndex, ReadyQueue and InputFinishList are reset by BattleHUD.InitialBattle(), which
    runs LATER than the battle scene goes live. So through the opening camera of the SECOND battle
    in a session all three still hold the PREVIOUS fight's contents -- and `turn.slot` publishes a
    completely plausible "your move" for a battle that is asking nobody anything.

    The harness believed it, called menus (which passed: NetMenusReady is a ContainsKey, and
    InitialBattle clears that dictionary's VALUES but not its KEYS), and injected a command into a
    battle mid-intro. The fight FROZE -- no HUD, no ATB, the intro camera held for four minutes.
    Two standalone runs were green beforehand, because their battle was the FIRST of the session,
    where the stale value happens to be -1. Only the suite, which runs a battle scenario after
    another battle scenario, could see it.
    """
    fake = FakeGame(game)
    fake.battle_intro_frames = 10 ** 9          # hold the session inside the stale window
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        g.start_battle(105)
        published(g, lambda s: s.in_battle)
        fake.battle_turn = 0                    # what the previous fight left behind
        published(g, lambda s: s.turn_slot_raw == 0)

        st = g.state
        assert st.commands_enabled is False
        assert st.turn_slot == -1, "the gated value must not offer a turn the battle is not offering"
        assert st.turn_slot_raw == 0, "and the ungated one is kept, so the window is diagnosable"
        assert st.ready_slots == []


def test_the_play_verbs_refuse_a_battle_that_is_not_asking(game):
    """Each of them, because each was a way into the frozen fight: wait_turn believed the stale
    slot, menus passed on a stale dictionary key, and battlecmd queued the command that wedged it."""
    fake = FakeGame(game)
    fake.battle_intro_frames = 10 ** 9
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        g.start_battle(105)
        fake.battle_turn = 0
        published(g, lambda s: s.turn_slot_raw == 0)

        with pytest.raises(HarnessError, match="not asking"):
            g.menus(0)
        with pytest.raises(HarnessError, match="not asking"):
            g.battle_command(0, 1, sub=176, target=16)
        with pytest.raises(HarnessError, match="a party member to be asked"):
            g.wait_turn(timeout=2.0)


def test_the_command_phase_opens_and_then_the_turn_is_real(game):
    """The other half: once InitialBattle has run, the same fields ARE the answer."""
    fake = FakeGame(game)
    fake.battle_intro_frames = 30
    fake.atb_gain = 400
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        g.start_battle(105)
        slot = g.wait_turn(timeout=10.0)
        assert slot == 0 and g.state.commands_enabled
        g.act("Attack", slot=slot)
        assert fake.battle_commands


# ---------------------------------------------------------------------------------------------
# THE MOVEMENT TAIL and the wall retry -- the gateway_check flake.
#
# Measured in-game on 30801, each case from a known open spot: a hold covers what it commanded give
# or take ONE frame, and nothing is still moving by `wait frames + 4`. But on 30820 a burst was
# still credited with 114 units of movement in a direction it had not pressed, because the previous
# burst had not finished when it started -- and walk_to concluded the axis BASIS was wrong. That is
# a confident, well-argued verdict about the wrong thing, and it made the scenario fail on some runs
# and pass on others depending on where the character happened to arrive.
# ---------------------------------------------------------------------------------------------


def test_settle_waits_for_the_character_to_actually_stop(game):
    """Every displacement this driver measures is a difference of two positions, and it is only
    attributable to the burst between them if the character is stationary at both ends."""
    fake = FakeGame(game)
    fake.coast_frames = 8               # an exaggerated tail, to make the window visible
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        g.wait_frames(20)
        settled = g.settle()
        before = (settled.player_x, settled.player_z)

        # A hold whose tail outlives the wait it is given.
        g.send("hold up 4", "wait 6")
        rushed = g.state                # what the old code would have measured
        rested = g.settle()
        assert rested.player_z > rushed.player_z, (
            "the stand-in's tail is not being modelled; without it this test proves nothing")
        # And once settled, it stays settled.
        assert g.settle().player_z == rested.player_z
        assert rested.player_z > before[1]


def test_the_basis_verdict_only_judges_a_burst_that_is_evidence(game):
    """THE RULE, fed the numbers the GAME produced. Both of these were real bursts on 30820, and the
    old test (an absolute `moved >= 15`) called both of them evidence about the axis basis:

        down  f=31 cmd=930 moved=960.0 proj=+960.0  (60,-777) -> (60,-1737)
        left  f=1  cmd= 30 moved=114.0 proj=  -0.0  (60,-1737) -> (60,-1851)

    One frame of `left` credited with 114 units of pure -z -- the tail of the `down` before it. And
    at the other end, 24 units of push-out when 1350 were commanded, which is a character pressed
    into a wall. Neither says anything about the basis, and treating them as though they did is what
    made gateway_check fail on some runs and pass on others.

    ⚠ Tested here rather than through walk_to on purpose. Reproducing these numbers through a
    simulated walk depends on where the stand-in character happens to be, and three attempts at
    that passed against a deliberately broken build -- proving nothing while looking thorough."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        # TOO MUCH: 114 units on 30 commanded. The tail of the previous burst.
        assert not g._burst_is_evidence(114.0, 30.0)
        # TOO LITTLE: 24 units on 1350 commanded. Pressed into a wall.
        assert not g._burst_is_evidence(24.0, 1350.0)
        # Below the floor entirely -- a nudge, not a move.
        assert not g._burst_is_evidence(4.0, 900.0)

        # A GENUINELY WRONG BASIS still gets judged: the character walks freely, so he covers very
        # nearly what was commanded. This is the case the guard exists for and must keep catching.
        assert g._burst_is_evidence(1150.0, 1200.0)
        assert g._burst_is_evidence(900.0, 930.0)
        # And the +/-1 frame the engine actually varies by (measured on 30801) stays evidence.
        assert g._burst_is_evidence(60.0, 30.0), "run f=1 covers 60u; that is normal, not a tail"
        assert g._burst_is_evidence(450.0, 465.0)


def test_a_wall_does_not_get_the_basis_discarded(game):
    """The integration side of the same rule: drive hard into a wall and the basis must survive.
    A discarded basis is not a small thing -- every later walk on that field recalibrates, and the
    scenario ends up reporting the field as unreachable."""
    fake = FakeGame(game, walkmesh=(-600.0, -600.0, 600.0, 200.0))
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        g.wait_frames(20)
        g.calibrate_axes()
        assert g.walk_to(0.0, 1500.0, tolerance=45.0, strict=False) is False
        assert 30810 in g._axes, "a wall is not evidence that the basis is wrong"


def test_walk_to_gives_up_on_a_target_it_keeps_missing(game):
    """Pins the overshoot stall: a loop that steps past the target and back again shows movement
    every time, and without counting that as a stall it burns all 24 bursts before failing.

    ⚠ This guards EXISTING behaviour. A `progress < 1.0` stall was written alongside it and then
    REMOVED: the burst trace showed the overshoot rule already breaks this oscillation, nothing in
    the stand-in could make the new rule fire, and an unverifiable rule inside a steering loop is
    exactly the speculative surface this arc keeps paying for.

    Asserted on the REQUEST COUNT rather than on wall-clock: a timing assertion would pass or fail
    with the machine rather than with the rule under test."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        g.wait_frames(20)
        g.calibrate_axes()
        fake.coast_frames = 10          # every burst overshoots by ~300u; the target is unhittable
        before = fake.seq
        assert g.walk_to(0.0, 300.0, tolerance=45.0, strict=False) is False
        spent = fake.seq - before
        assert spent < 14, (
            f"took {spent} requests to give up on an unreachable target -- with two stalls it "
            f"should be a handful, and 24 bursts is the old behaviour")


def test_calibration_backs_away_from_a_wall_instead_of_refusing(game):
    """THE OTHER HALF OF THE FLAKE, seen on 30801 as

        the h axis is not a free axis: right measured (+1.00,+0.00) over 60u and
        left measured (-1.00,+0.00) over 180u (antiparallel=+1.00, length ratio=0.33)

    antiparallel=+1.00 means the two probes agree PERFECTLY about which world direction the axis is.
    All the length ratio says is that one side ran out of room -- a fact about where the character
    is standing, not about the field, and one that varies between runs. Backing off and measuring
    again is what a person would do."""
    fake = FakeGame(game, walkmesh=(-600.0, -600.0, 600.0, 600.0))
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        g.wait_frames(20)
        # Stand him 50 units from the east wall: `right` measures 50 of the 120 commanded (over the
        # 35% probe floor, so it is not simply discarded) while `left` measures the full 120.
        # ratio 0.42 -- the old code refused here.
        fake.player = [550.0, 0.0, 0.0]
        published(g, lambda s: s.player_x is not None and s.player_x > 500)
        basis = g.calibrate_axes()
        assert basis["h"][0] > 0.9, f"backed off and measured the axis anyway: {basis}"
        assert basis["v"][1] > 0.9 or basis["v"][1] < -0.9


def test_calibration_still_refuses_ground_that_no_retry_can_fix(game):
    """The refusal is kept for what it was written for. In wall_slide mode EVERY press is projected
    onto one fixed direction, so the character always moves and never where he was sent -- backing
    off changes nothing, and a basis measured there is a well-formed lie."""
    fake = FakeGame(game, mode="wall_slide")
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        g.wait_frames(20)
        with pytest.raises(HarnessError, match="not a free axis|deflected|could not calibrate"):
            g.calibrate_axes(recalibrate=True)


def test_backing_off_refuses_to_leave_the_field(game):
    """Calibration that walked into a gateway would cache the NEXT room's basis under this room's
    id -- a wrong answer with no symptom at all until something steered by it."""
    fake = FakeGame(game, walkmesh=(-600.0, -600.0, 600.0, 600.0))
    # A gateway band just west of the calibration spot -- exactly where a character pinned against
    # the east wall backs off to. The `left` probe (120u) stops short of it; the 240u back-off
    # crosses it.
    fake.gateway = (150.0, -600.0, 350.0, 600.0, 30821)
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        g.wait_frames(20)
        fake.player = [550.0, 0.0, 0.0]
        published(g, lambda s: s.player_x is not None and s.player_x > 500)
        with pytest.raises(HarnessError, match="left the field|gateway"):
            g.calibrate_axes(recalibrate=True)


# --------------------------------------------------------------------------- co-op (netsync) benches


def test_state_maps_the_netsync_block_and_tells_absent_from_off():
    """`netsync` is None on an engine that does not publish it -- NOT an empty dict. "The engine
    predates the verbs" and "co-op is disabled" are different facts, and a lockstep assertion that
    read an absent section as a disengaged client would be green against the wrong engine."""
    old = State({"frame": 1, "ack": 0, "busy": False})
    assert old.netsync is None and old.lockstep_pending is None and old.lockstep_suppressed is False
    st = State({"frame": 1, "ack": 0, "busy": False,
                "netsync": {"enabled": True, "role": "selftest", "selftest": True, "forced": True,
                            "bench": True, "l1": True, "suppress": True, "align_win": 3,
                            "align_text": 41, "applied_seq": 0, "wait_armed": True, "wait_ms": 120,
                            "wait_limit_ms": 8000,
                            "pending": {"field": 30801, "win": 15, "text": 65535, "kind": 0,
                                        "index": 255, "seq": 1}}})
    assert st.netsync["role"] == "selftest" and st.lockstep_suppressed is True
    assert st.lockstep_pending == {"field": 30801, "win": 15, "text": 65535, "kind": 0,
                                   "index": 255, "seq": 1}


def test_netsync_verbs_carry_the_engines_refusal(game):
    """The bench verbs are gated (selftest role, the field-gate lever, the L1 flag) and every
    refusal must reach the scenario with the engine's own reason, attached to THIS step -- a bench
    that acked a refused injection would report lockstep green having injected nothing."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        with pytest.raises(HarnessError, match="needs the selftest role"):
            g.netsync("bench", 1)
        st = g.netsync("selftest", 1)
        assert st.netsync["selftest"] and st.netsync["forced"] and st.netsync["instance"]
        fake.say("A line the lockstep will page.")
        published(g, lambda s: s.dialog_open)
        with pytest.raises(HarnessError, match="field-gate bench is OFF"):
            g.netsync("advance")
        g.netsync("bench", 1)
        with pytest.raises(HarnessError, match="L1 host-event flag is OFF"):
            g.netsync("advance")
        g.netsync("l1", 1)
        g.netsync("advance")
        st = published(g, lambda s: not s.dialog_open)
        assert st.netsync["applied_seq"] == 0 and st.lockstep_pending is None
        with pytest.raises(HarnessError, match="no dialogue window is open"):
            g.netsync("advance")
        st = g.netsync("unmatched")
        assert st.lockstep_pending is not None and st.lockstep_pending["win"] == 15
        assert st.netsync["wait_armed"] and not st.lockstep_suppressed


def test_reset_releases_a_forced_selftest_so_it_cannot_leak_to_the_next_scenario(game):
    """The override is process-local, and the next scenario -- or, on a leaked run, the next PLAYER
    -- must not inherit a ghost, a bench gate or an L1 pin. So `reset` is a release point."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.netsync("selftest", 1)
        g.netsync("bench", 1)
        g.netsync("l1", 1)
        g.send("reset")
        st = published(g, lambda s: s.netsync is not None and not s.netsync["forced"])
        assert not st.netsync["enabled"] and not st.netsync["bench"] and not st.netsync["l1"]


def test_netsync_refuses_an_engine_that_predates_the_verbs(game):
    """An older agent answers `unknown op` only AFTER the step is sent; the driver names the
    rebuild it needs before spending the step."""
    fake = FakeGame(game)
    fake.protocol = 4
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError, match="protocol 4"):
            g.netsync("bench", 1)


def test_netsync_talk_is_gated_like_the_other_benches(game):
    """The talk relay's solo bench replays a host's press-fired start by object uid; it needs the
    same selftest + bench-lever gates, and a bad uid is refused with the engine's reason."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.netsync("selftest", 1)
        with pytest.raises(HarnessError, match="field-gate bench is OFF"):
            g.netsync("talk", 3)
        g.netsync("bench", 1)
        with pytest.raises(HarnessError, match="outside 0..65535"):
            g.netsync("talk", 70000)
        g.netsync("talk", 3)
        st = published(g, lambda s: s.netsync is not None and s.netsync.get("last_talk_uid") == 3)
        assert st.netsync["last_talk_uid"] == 3
