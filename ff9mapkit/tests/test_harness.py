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
