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
import re
import sys
import threading
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

from harness import Channel, HarnessError, Session, State          # noqa: E402
from harness.fakegame import FakeGame                              # noqa: E402
from harness.logs import parse_memoria, parse_unity, split_lines   # noqa: E402
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


# --------------------------------------------------------------------------- the dead tri/floor keys
# s83 publishes player.tri / player.floor from PosObj.activeTri / activeFloor, which only the
# battle-entry backup ever writes: 0/0 before any battle, frozen after one. Two gates keep them from
# being read as where the player stands -- one on State, one on the code that reads the document.

#: Distinctive values no other State field could produce by accident.
_DEAD_TRI, _DEAD_FLOOR = 4321, 77


def test_state_exposes_the_s83_tri_and_floor_only_as_a_battle_snapshot():
    st = State({"player": {"x": 1.0, "y": 0.0, "z": 2.0, "tri": _DEAD_TRI, "floor": _DEAD_FLOOR}})
    assert st.player_tri_battle_snapshot == _DEAD_TRI
    assert st.player_floor_battle_snapshot == _DEAD_FLOOR
    # The gate is on VALUES, not names: an accessor of any name that hands the bare key back
    # presents the snapshot as live, which is the failure this exists to stop.
    leaks = []
    for name in dir(State):
        if name.startswith("_") or name.endswith("_battle_snapshot"):
            continue
        if not isinstance(getattr(State, name), property):
            continue
        v = getattr(st, name)
        vals = v.values() if isinstance(v, dict) else v if isinstance(v, (tuple, list)) else (v,)
        if any(not isinstance(x, bool) and x in (_DEAD_TRI, _DEAD_FLOOR) for x in vals):
            leaks.append(name)
    assert leaks == []


def test_the_floor_snapshot_undoes_the_byte_cast_and_absence_is_none():
    assert State({"player": {"floor": 255}}).player_floor_battle_snapshot == -1   # Byte(-1)
    assert State({"player": {"floor": 3}}).player_floor_battle_snapshot == 3
    assert State({"player": {"x": 0.0}}).player_tri_battle_snapshot is None       # no such key
    assert State({"player": {"x": 0.0}}).player_floor_battle_snapshot is None
    assert State({}).player_tri_battle_snapshot is None


#: A read of a bare key off the player section: ``st.raw["player"]["tri"]``,
#: ``st.raw.get("player", {}).get("floor")``. Same line only -- a reader that binds the section to a
#: name and subscripts it on a later line gets past this, and the State gate above is the backstop.
_BARE_TRI_READ = re.compile(r"""["']player["'].{0,40}?(?:\[|\.get\()\s*["'](?:tri|floor)["']""")


def _bare_tri_readers(root: pathlib.Path) -> list[str]:
    hits = []
    for base in ("tools", "studies"):
        for path in sorted((root / base).rglob("*.py")):
            if path == root / "tools" / "harness" / "channel.py":         # the one sanctioned reader
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for n, line in enumerate(text.splitlines(), 1):
                if _BARE_TRI_READ.search(line):
                    hits.append(f"{path.relative_to(root).as_posix()}:{n}")
    return hits


def test_no_harness_code_reads_the_bare_tri_or_floor_keys(tmp_path):
    # It has to catch the reads it exists for, the recon.py line this change removed among them...
    for line in ("st.raw.get('player', {}).get('floor')", 'st.raw["player"]["tri"]',
                 '(doc.get("player") or {}).get("tri")'):
        assert _BARE_TRI_READ.search(line), line
    assert not _BARE_TRI_READ.search('"player": {"x": px, "floor": 0, "tri": 0}')   # a literal
    # ...and has to find one in a real tree, not just match a string.
    (tmp_path / "studies" / "s").mkdir(parents=True)
    (tmp_path / "studies" / "s" / "scn.py").write_text(
        "def run(g):\n    print(g.state.raw.get('player', {}).get('floor'))\n", encoding="utf-8")
    assert _bare_tri_readers(tmp_path) == ["studies/s/scn.py:2"]
    assert _bare_tri_readers(REPO) == []


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


def test_classify_names_an_empty_document_as_a_rewrite_not_a_throw(game):
    """The agent truncates state.json in place and then writes it, so an EMPTY file is a publish in
    flight -- or, when it stays empty, a game hung INSIDE the publish. UNPARSEABLE's "the agent threw
    partway through the document" is the wrong cause for both. Break: drop the empty-body branch."""
    ch = Channel(game)
    ch.reset()
    (ch.dir / "state.json").write_text("", encoding="utf-8")
    why = ch.classify()
    assert why.startswith("EMPTY") and "mid-rewrite" in why, why
    os.utime(ch.dir / "state.json", (time.time() - 600, time.time() - 600))
    why = ch.classify()
    assert why.startswith("EMPTY") and "INSIDE the publish" in why, why


# --------------------------------------------------------------------------- a publish stalled mid-rewrite
# MEASURED 2026-09-23 (studies/platform-land/rung0_land.py, run 20260923-180350-platform-land-A-
# oldlayout): with `state_every(1)` and a 4 ms poll of `g.state` through a 40-frame ride, the run died
# on `no state published -- OK` while the game went on publishing. The agent rewrites state.json IN
# PLACE, so it is EMPTY between the truncate and the bytes; that gap is usually under a millisecond
# but its p99 is ~80 ms, and Channel.state() gives a parse failure ~30 ms. The stand-in's
# `stall_publish` reproduces the gap; these pin that one miss is ridden out and a dead channel still
# is not.


def _inside_a_stalled_publish(g, fake, seconds):
    """Queue a mid-rewrite stall and return once state.json is being held EMPTY.

    The size check keeps the tests below from passing without the gap they are about.
    """
    fake.stall_publish(seconds)
    assert fake.stalling.wait(5), "the stand-in never began the stalled publish"
    assert (g.channel.dir / "state.json").stat().st_size == 0, "the stall is not holding it empty"


def test_a_publish_stalled_mid_rewrite_is_ridden_out_not_called_no_state(game):
    """Break: make Session.state raise on the channel's first None again."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.state_every(1)                                   # the incident's setting
        _inside_a_stalled_publish(g, fake, 0.4)
        stalled_at = fake.frame                            # its loop is blocked mid-publish
        st = g.state
        assert st.frame >= stalled_at


def test_a_publish_that_never_lands_is_still_a_dead_channel(game):
    """The tolerance must not hide a game hung INSIDE the publish: the read still raises, within
    the budget, and says the file is empty rather than "OK". Break: loop with no deadline."""
    from harness.session import STATE_MISS_BUDGET
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        _inside_a_stalled_publish(g, fake, 60)
        t0 = time.time()
        with pytest.raises(HarnessError, match="no state published") as err:
            g.state
        took = time.time() - t0
        fake.kill()                  # release the stall; an exited game spares teardown its quit wait
    assert took < STATE_MISS_BUDGET + 3.0, took
    assert "EMPTY" in str(err.value), err.value


def test_a_game_that_dies_inside_a_miss_is_reported_at_once(game):
    """A plain sleep through the miss turns a crash into a wait. Break: drop _assert_alive from the
    retry loop in Session._read_state."""
    from harness.session import STATE_MISS_BUDGET
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        _inside_a_stalled_publish(g, fake, 60)
        fake.returncode = 3
        t0 = time.time()
        with pytest.raises(HarnessError, match="exited"):
            g.state
        took = time.time() - t0
        fake.stop()
    assert took < STATE_MISS_BUDGET / 2, took


def test_a_transient_miss_cannot_skip_the_save_sandbox_check(game):
    """`_assert_save_sandbox` RETURNED on a None read, so one stalled publish at boot skipped the only
    check between an autosave and the owner's game. Break: restore `if st is None: return`."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        fake.save_sandboxed = False
        published(g, lambda s: s.raw.get("save_sandboxed") is False)
        _inside_a_stalled_publish(g, fake, 0.4)
        with pytest.raises(HarnessError, match="did NOT redirect"):
            g._assert_save_sandbox()


def test_a_transient_miss_cannot_skip_the_protocol_check(game):
    """`_adopt_agent` RETURNED on a None read, skipping the protocol refusal and the seq seed that
    defends against a leaked arm. Break: restore `if st is None: return`."""
    from harness.channel import PROTOCOL
    fake = FakeGame(game)
    with session(game, fake) as g:
        fake.protocol = PROTOCOL + 7
        published(g, lambda s: s.protocol == PROTOCOL + 7)
        _inside_a_stalled_publish(g, fake, 0.4)
        with pytest.raises(HarnessError, match="protocol mismatch"):
            g._adopt_agent()


def test_a_transient_miss_is_not_a_failed_baseline(game):
    """Break: read the baseline's state with channel.state() again -- one stalled publish then
    climbs the recovery ladder, or poisons the next scenario if it lands on the final re-check."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        ok, why = g.at_baseline()
        assert ok, why
        _inside_a_stalled_publish(g, fake, 0.4)
        ok, why = g.at_baseline()
        assert ok, why


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


# --------------------------------------------------------------------------- the two exception logs
#
# Which log an exception lands in is decided by who CATCHES it (tools/harness/logs.py): battle code is
# caught by HonoluluBattleMain.Update and lands in Memoria.log only; an uncaught MonoBehaviour exception
# lands in Unity's x64/FF9_Data/output_log.txt only. Measured 2026-09-23 (run mp-retype-3): 637 battle
# NREs in Memoria.log / 0 in output_log, 18 MovePC NREs in output_log / 0 in Memoria.log. The driver
# read Memoria.log alone. The unstarted Sessions below never launch anything: FakeGame.throw() only
# writes the log files, and diagnose()/exceptions_since() only read them.

#: A real Unity exception block, BYTES as measured on this install: every frame but the last ends
#: CR CR LF, the block ends with a one-space line and a `(Filename:` line.
UNITY_BLOCK = (
    b"NullReferenceException: Object reference not set to an instance of an object\r\n"
    b"  at FieldMapActorController.MovePC () [0x00000] in <filename unknown>:0 \r\r\n"
    b"  at FieldMapActorController.UpdateMovement (Boolean copyLastPos) [0x00000] in <filename unknown>:0 \r\r\n"
    b"  at FieldMapActorController.HonoUpdate () [0x00000] in <filename unknown>:0 \r\r\n"
    b"  at HonoBehaviorSystem.Update () [0x00000] in <filename unknown>:0 \r\n"
    b" \r\n(Filename:  Line: -1)\r\n\r\n"
)

#: The frames of the battle-init NRE the mp-retype control threw, as Memoria.log recorded them.
BATTLE_FRAMES = ("btl_init.OrganizeEnemyData (.FF9StateBattleSystem btlsys)",
                 "battle.BattleLoadLoop (.FF9StateGlobal sys, .FF9StateBattleSystem btlsys)",
                 "HonoluluBattleMain.Update ()")

MOVEPC = "NullReferenceException at FieldMapActorController.MovePC (output_log.txt)"


def test_the_memoria_parser_reads_each_E_exception_with_its_own_frames():
    """Lifted from studies/battle-multipart/mp_retype.py (same count on a real log: 637). Break: stop
    appending the `|E|   at` frames, or open an exception on an `|E|` line naming no exception type."""
    lines = [
        "23.09.2026 01:14:40 |M| [Harness] armed",
        "23.09.2026 01:14:41 |E| System.NullReferenceException: Object reference not set to an instance "
        "of an object",
        "23.09.2026 01:14:41 |E|   at btl_init.OrganizeEnemyData (.FF9StateBattleSystem btlsys) [0x00000] "
        "in <filename unknown>:0 ",
        "23.09.2026 01:14:41 |E|   at HonoluluBattleMain.Update () [0x00000] in <filename unknown>:0 ",
        "23.09.2026 01:14:41 |E| System.NullReferenceException: ",
        "23.09.2026 01:14:41 |E|   at (wrapper managed-to-native) UnityEngine.GameObject:get_transform ()",
        "23.09.2026 01:14:42 |E| [Loader] could not open a file",
        "23.09.2026 01:14:42 |E|   at Nobody.Owns (this frame)",
        "23.09.2026 01:14:43 |M| unrelated",
    ]
    exc = parse_memoria(lines)
    assert [(e.name, e.where, e.stamp, len(e.trace)) for e in exc] == [
        ("NullReferenceException", "btl_init.OrganizeEnemyData", "23.09.2026 01:14:41", 2),
        ("NullReferenceException", "UnityEngine.GameObject:get_transform", "23.09.2026 01:14:41", 1),
    ]
    assert exc[0].type == "System.NullReferenceException" and exc[0].message.startswith("Object reference")
    assert exc[0].log == "Memoria.log"
    assert exc[0].through("HonoluluBattleMain") and not exc[0].through("MovePC")


def test_unitys_CR_CR_LF_frames_are_one_line_each_and_every_frame_is_kept():
    """Unity ends each stack frame but the last with CR CR LF. splitlines() reads that as the frame
    AND an empty line, and the first cut of the parser kept 1 frame of 4 from the real log.
    Break: make split_lines() use str.splitlines(), or drop parse_unity's empty-line skip."""
    text = ("Loaded the Exception table for field 30801\r\n" + UNITY_BLOCK.decode()
            + "Unloading 2 unused Assets to reduce memory usage.\r\n")
    lines = split_lines(text)
    assert lines[1].startswith("NullReferenceException") and lines[6] == " " and "" not in lines[:7]
    for form in (lines, text.splitlines()):
        [e] = parse_unity(form)
        assert (e.log, e.name, e.stamp, e.where) == (
            "output_log.txt", "NullReferenceException", None, "FieldMapActorController.MovePC")
        assert [f.split(" (")[0] for f in e.trace] == [
            "FieldMapActorController.MovePC", "FieldMapActorController.UpdateMovement",
            "FieldMapActorController.HonoUpdate", "HonoBehaviorSystem.Update"]


def test_teardown_archives_both_exception_logs(game):
    """Break: archive Memoria.log alone in _collect_log (all it did until 2026-09-23)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        fake.throw(caught=True, frames=BATTLE_FRAMES)
        fake.throw()
    mem = (game / "run" / "Memoria.log").read_text(encoding="utf-8")
    uni = (game / "run" / "output_log.txt").read_bytes()
    assert "|E| System.NullReferenceException" in mem and "OrganizeEnemyData" in mem
    assert uni.startswith(b"Initialize engine version") and b"FieldMapActorController.MovePC" in uni


def test_an_output_log_this_launch_never_wrote_is_not_archived_as_its_evidence(game):
    """A game that dies before Unity opens its log leaves the PREVIOUS launch's on disk, and nothing in
    an untimestamped log says so. Break: drop the _predates_launch guard in _collect_log."""
    stale = game / "x64" / "FF9_Data" / "output_log.txt"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(UNITY_BLOCK)
    old = time.time() - 3600
    os.utime(stale, (old, old))
    fake = FakeGame(game)
    fake.writes_unity_log = False
    with session(game, fake) as g:
        boot(g)
    assert not (game / "run" / "output_log.txt").exists()
    assert (game / "run" / "Memoria.log").exists()        # timestamped, so it documents itself


def test_a_hang_behind_an_uncaught_exception_is_explained_from_unitys_log(game):
    """The case this was built for: a MonoBehaviour throws, nothing catches it, the agent stops
    publishing -- and the only record is output_log.txt. Break: make diagnose() read Memoria.log alone."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        fake.throw()
        fake.mode = "frozen"
        time.sleep(0.3)                           # let the last pre-freeze document land
        with pytest.raises(HarnessError, match="frozen") as err:
            g.wait_for(lambda s: False, timeout=1.0, what="anything")
        fake.mode = "normal"          # thaw, so teardown does not spend its full quit budget
    msg = str(err.value)
    assert "NullReferenceException at FieldMapActorController.MovePC" in msg
    assert str(fake.unity_log) in msg


def test_diagnose_reports_every_log_with_a_marker_newest_first(game):
    """Break: stop at the first log with a marker, or drop the newest-first sort."""
    fake = FakeGame(game)
    s = session(game, fake)
    fake.throw(caught=True, frames=BATTLE_FRAMES)
    fake.throw()
    now = time.time()
    os.utime(game / "x64" / "Memoria.log", (now - 60, now - 60))   # the fixture's must not win newest
    os.utime(fake.memoria_log, (now - 5, now - 5))
    os.utime(fake.unity_log, (now - 1, now - 1))
    first, second = s.diagnose().split("; ")
    assert first == ("the engine threw a NullReferenceException at FieldMapActorController.MovePC "
                     f"(from {fake.unity_log})")
    assert second == ("the engine threw a NullReferenceException at btl_init.OrganizeEnemyData "
                      f"(from {fake.memoria_log})")
    os.utime(fake.memoria_log, (now, now))
    assert s.diagnose().split("; ")[0].endswith(f"(from {fake.memoria_log})")


def test_diagnose_will_not_speak_from_a_stale_unity_log(game):
    """Break: drop the max_age test for output_log.txt."""
    fake = FakeGame(game)
    s = session(game, fake)
    fake.throw()
    old = time.time() - 120
    os.utime(fake.unity_log, (old, old))
    assert s.diagnose(max_age=60, window=600) is None
    assert "MovePC" in (s.diagnose(max_age=600, window=600) or "")        # the control


def test_diagnose_window_on_unitys_untimestamped_log_starts_with_its_last_write(game):
    """No line carries a time, but the file does: not one byte of a log last written before the cutoff
    is recent. Break: drop the mtime test in _recent_unity."""
    fake = FakeGame(game)
    s = session(game, fake)
    fake.throw()
    old = time.time() - 60
    os.utime(fake.unity_log, (old, old))
    assert s.diagnose(window=30) is None
    assert "MovePC" in (s.diagnose(window=120) or "")


def test_diagnose_reads_unitys_log_from_where_it_stood_at_the_cutoff(game):
    """Written recently -- but only noise; the exception is older than the window. The size noted at
    or before the cutoff is where "recent" begins. Break: ignore the notes (read from 0)."""
    fake = FakeGame(game)
    s = session(game, fake)
    fake.throw()
    s._unity_notes.append((time.time() - 60, fake.unity_log.stat().st_size))
    with open(fake.unity_log, "ab") as f:
        f.write(b"Unloading 2 unused Assets to reduce memory usage.\r\n")
    assert s.diagnose(window=30) is None
    assert "MovePC" in (s.diagnose(window=120) or "")      # no note that old: all of it counts


def test_unitys_log_size_is_noted_on_the_reads_a_wait_already_makes(game):
    """No thread, no extra poll: the observer that feeds the state ring notes it, at most once per
    UNITY_NOTE_EVERY. Break: stop calling _note_unity_log from _observe, or drop the throttle."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        t0, n0 = time.time(), len(g._unity_notes)
        g.wait_frames(240)
        elapsed = time.time() - t0
        assert len(g._unity_notes) - n0 <= elapsed / g.UNITY_NOTE_EVERY + 1
        g.UNITY_NOTE_EVERY = 0.0
        fake.throw()
        g.wait_frames(4)
        assert g._unity_notes[-1][1] == fake.unity_log.stat().st_size


def test_exceptions_since_a_mark_reads_both_logs_and_nothing_before_it(game):
    """Break: ignore the mark (read each log from its start), or read Memoria.log alone."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        fake.throw(caught=True, frames=BATTLE_FRAMES)
        fake.throw()
        mark = g.log_mark()
        fake.throw("IndexOutOfRangeException", ("btl_cmd.KickCommand ()",),
                   message="Array index is out of range.", caught=True)
        fake.throw()
        since = g.exceptions_since(mark)
        everything = g.exceptions_since()
    assert [str(e) for e in since] == [
        "IndexOutOfRangeException at btl_cmd.KickCommand (Memoria.log)", MOVEPC]
    assert since[0].stamp and since[0].message == "Array index is out of range."
    assert since[1].stamp is None and len(since[1].trace) == 3
    assert len(everything) == 4


def test_a_mark_taken_mid_line_does_not_split_an_exception_from_its_frames(game):
    """Break: mark at the raw file size instead of snapping back to the start of the line."""
    fake = FakeGame(game)
    s = session(game, fake)
    fake.throw()
    head, rest = UNITY_BLOCK.split(b"Exception: ", 1)
    with open(fake.unity_log, "ab") as f:
        f.write(head)                              # the game is part-way through a header
    mark = s.log_mark()
    with open(fake.unity_log, "ab") as f:
        f.write(b"Exception: " + rest)
    assert [str(e) for e in s.exceptions_since(mark)] == [MOVEPC]


def test_a_log_rewritten_since_the_mark_is_read_from_its_start(game):
    """A relaunch rewrites output_log.txt; an offset into the old file means nothing in the new one.
    Break: drop read_from's reset for an offset past the end of the file."""
    fake = FakeGame(game)
    s = session(game, fake)
    for _ in range(3):
        fake.throw()
    mark = s.log_mark()
    fake.unity_log.write_bytes(UNITY_BLOCK)        # rewritten, and shorter than the mark
    assert [str(e) for e in s.exceptions_since(mark)] == [MOVEPC]


def test_a_mark_in_one_memoria_log_does_not_apply_to_the_other(game):
    """Newest-wins can move to the other Memoria.log after a mark, where its offset means nothing.
    Break: apply the marked offset to whatever file is newest now."""
    old = time.time() - 10
    os.utime(game / "x64" / "Memoria.log", (old, old))
    fake = FakeGame(game)
    s = session(game, fake)
    mark = s.log_mark()
    assert mark["Memoria.log"][0] == game / "x64" / "Memoria.log"
    fake.throw(caught=True, frames=BATTLE_FRAMES)             # the game root's: now the newest
    assert [e.where for e in s.exceptions_since(mark)] == ["btl_init.OrganizeEnemyData"]


def test_a_log_the_game_never_wrote_this_launch_is_no_evidence_about_it(game):
    """The previous launch's output_log, still on disk, must not explain or be counted against this
    one. Break: drop _predates_launch from exceptions_since(), or from diagnose()."""
    stale = game / "x64" / "FF9_Data" / "output_log.txt"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(UNITY_BLOCK)
    old = time.time() - 10
    os.utime(stale, (old, old))
    fake = FakeGame(game)
    fake.writes_unity_log = False
    with session(game, fake) as g:
        boot(g)
        assert g.exceptions_since() == []
        assert g.diagnose(window=120) is None
    view = session(game, FakeGame(game))           # the control: a session that launched nothing
    assert [str(e) for e in view.exceptions_since()] == [MOVEPC]
    assert "MovePC" in (view.diagnose(window=120) or "")


def test_diagnose_still_reads_memoria_log_by_its_own_line_timestamps(game):
    """The refactor's guard: a freshly written Memoria.log whose NRE is five minutes old explains
    nothing now. Break: drop the timestamp filter in _recent_memoria."""
    fake = FakeGame(game)
    s = session(game, fake)
    then = time.strftime("%d.%m.%Y %H:%M:%S", time.localtime(time.time() - 300))
    fake.memoria_log.write_text(f"{then} |E| System.NullReferenceException: stale\n"
                                f"{then} |E|   at btl_init.OrganizeEnemyData ()\n", encoding="utf-8")
    assert s.diagnose() is None
    fake.throw(caught=True, frames=BATTLE_FRAMES)
    assert s.diagnose() == ("the engine threw a NullReferenceException at btl_init.OrganizeEnemyData "
                            f"(from {fake.memoria_log})")


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


def test_failure_evidence_is_capped_per_scenario(game):
    """In a suite, re-running to see what the screen looked like costs the whole suite -- so every
    failed check gets the ring flushed and a photograph, up to a cap: a scenario failing forty checks
    does not need forty pictures of the same screen. The cap resets per member. Break: restore the
    one-shot bool, drop the cap, or stop resetting the counter in bind_artifacts."""
    fake = FakeGame(game)
    rel = _scenario(game, "fails_a_lot",
                    "def run(g):\n    g.newgame(settle=0)\n"
                    + "".join(f"    g.check(False, 'f{i}')\n    g.wait_frames(2)\n" for i in range(5)))
    rel2 = _scenario(game, "fails_again",
                     "def run(g):\n    g.newgame(settle=0)\n    g.check(False, 'g')\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{rel}"\n\n'
                           f'[[scenario]]\npath="{rel2}"\n')
    with session(game, fake) as g:
        meta, scenarios = load_manifest(path, game)
        runner = SuiteRunner(g, scenarios, meta=meta, verbose=False)
        results = runner.run()
        run_dir = runner.run_dir
    assert [r["verdict"] for r in results] == ["fail", "fail"]
    # Scoped to the scenario's OWN directory: the session-level collect keeps a flat copy of every
    # shot too, so an unscoped glob counts the same image twice.
    first = run_dir / "01-fails_a_lot"
    shots = sorted(p.name for p in (first / "shots").glob("*.png"))
    assert shots == [f"01-fails_a_lot-FAILED-{k}.png" for k in (1, 2, 3)], shots
    assert sorted(p.name for p in first.glob("states-*.jsonl")) == [
        f"states-FAILED-{k}.jsonl" for k in (1, 2, 3)]
    checks = results[0]["checks"]
    assert checks[2]["shot"] == "01-fails_a_lot-FAILED-3.png"
    assert checks[3]["shot"] is None and "cap" in checks[3]["shot_skipped"]
    assert checks[4]["states"] is None
    # The second member starts its own count.
    assert (run_dir / "02-fails_again" / "shots" / "02-fails_again-FAILED-1.png").exists()
    assert results[1]["states"] == ["states-FAILED-1.jsonl"]


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


# --------------------------------------------------------------------------- routed walking
# Stock 350 <-> 351, eighty times: the arrival from 351 stands 18u from 351's own gateway, and the
# one-axis walk_to (or its calibration probe, or a correction burst pressed during the fade) walked
# straight back through it. These pin route_to / route_cross against the fake's ExitField model:
# entering a region takes control on that frame, the field changes `exit_frames` later.


def _flat_bgi(x0=-600, z0=-600, x1=600, z1=600):
    """The fake's rectangular floor as a real walkmesh in WORLD coords (bgi.build: orgPos 0)."""
    from ff9mapkit.scene import bgi
    c = [(x0, 0, z1), (x1, 0, z1), (x1, 0, z0), (x0, 0, z0)]
    return bgi.BgiWalkmesh.from_bytes(bgi.build(c, [(0, 1, 2), (0, 2, 3)]).to_bytes())


def _rect(x0, z0, x1, z1):
    return [[x0, z0], [x1, z0], [x1, z1], [x0, z1]]


def _prior():
    """The fake's twist 0 is the engine's TWIST -1 (0 deg): up = +z, right = +x."""
    from ff9mapkit.content import movement
    return movement.key_move_basis(-1)


def _stand(g, fake, x, z):
    fake.player = [float(x), 0.0, float(z)]
    published(g, lambda s: s.player_x is not None and abs(s.player_x - x) < 1 and abs(s.player_z - z) < 1)


def test_route_to_goes_round_a_gateway_the_straight_walk_takes(game):
    from ff9mapkit.content import pathfind
    door = _rect(-100, -300, 100, 300)                   # a band across the middle of the room
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": door, "to": 30821, "arrive": (0, 0)}]}
    fake.exit_frames = 20
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -400, 0)
        assert pathfind.seg_poly_gap((-400, 0), (400, 0), door) < 0        # the premise
        rec = g.route_to(400.0, 0.0, avoid=[door], walkmesh=_flat_bgi(), prior=_prior())
        assert rec["landed"] is None and rec["reached"], rec
        assert len(rec["waypoints"]) > 1 and not fake.fired, (rec, fake.fired)
        assert g.state.field_id == 30820
        # ...and the control: the one-axis walk back takes the door
        g.walk_to(-400.0, 0.0, strict=False)
        assert fake.fired and fake.fired[0]["to"] == 30821


def test_route_cross_from_an_arrival_beside_the_door_takes_the_exit_it_was_sent_to(game):
    """THE 350 SHAPE: standing 18u west of door A, sent to door B on the far side. The calibration may not
    press toward A (east); the route must not go back through it; the crossing must be B's."""
    from ff9mapkit.content import pathfind
    door_a = _rect(300, -150, 600, 150)
    door_b = _rect(-600, -150, -380, 150)
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": door_a, "to": 30821, "arrive": (-282, 0)},
                            {"zone": door_b, "to": 30810, "arrive": (0, 0)}],
                    30821: [{"zone": _rect(-600, -150, -300, 150), "to": 30820, "arrive": (282, 0)}]}
    fake.exit_frames = 30
    wm = _flat_bgi()
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, 282, 0)
        mark = len(fake.executed)
        basis = g.calibrate_axes(hazards=[door_a], prior=_prior())
        pressed = {s[1] for s in fake.executed[mark:] if s[0] == "hold" and s[1] != "cancel"}
        assert "right" not in pressed and "left" in pressed, pressed      # never toward A; left one-sided
        assert basis["h"][0] > 0.99 and basis["v"][1] > 0.99, basis       # measured: right is +x
        assert not fake.fired
        goal = pathfind.region_goal(wm, door_b)
        rec = g.route_cross(goal[0], goal[1], avoid=[door_a], walkmesh=wm, prior=_prior(), expect=30810)
        assert rec["landed"] == 30810 and rec["during"] == "walk", rec
        assert [f["to"] for f in fake.fired] == [30810], fake.fired        # door A never fired


def test_a_probe_that_fires_a_gateway_is_reported_not_measured_through(game):
    """A door nobody listed, 10u away: a blind one-frame probe still reaches it. It must be REPORTED -- the
    old probe settled during the fade, read 'same field', and measured on in the next room."""
    from harness.session import ProbeLeftControl
    door = _rect(10, -600, 300, 600)
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": door, "to": 30821, "arrive": (0, -400)}]}
    fake.exit_frames = 60
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, 0, 0)
        with pytest.raises(ProbeLeftControl, match="took control away|left field"):
            g._calibrate_clear_of(30820, [], None, 4)          # nothing to avoid: probes blind
        assert 30820 not in g._axes, "a probe that crossed must not cache a basis"
        g.wait_playable(timeout=10)
        g.warp(30820)
        _stand(g, fake, 0, 0)
        rec = g.route_to(-400.0, 0.0, avoid=[], walkmesh=_flat_bgi(), prior=None)
        assert rec["during"] == "calibrate" and rec["landed"] == 30821, rec


def test_blind_calibration_beside_a_known_door_refuses_before_pressing(game):
    """Without a prior a probe's direction is unknown, and one walk frame settles ~30u: beside a door it
    LISTED, blind calibration must refuse, not press and find out."""
    door = _rect(10, -600, 300, 600)
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": door, "to": 30821, "arrive": (0, -400)}]}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, 0, 0)
        mark = len(fake.executed)
        with pytest.raises(HarnessError, match="blind probe"):
            g.calibrate_axes(hazards=[door], prior=None)
        with pytest.raises(HarnessError, match="blind probe"):
            g.route_to(-400.0, 0.0, avoid=[door], walkmesh=_flat_bgi(), prior=None)
        assert not [s for s in fake.executed[mark:] if s[0] == "hold"], fake.executed[mark:]
        assert not fake.fired and 30820 not in g._axes
        _stand(g, fake, -300, 0)                             # 310u clear: blind is safe again
        g.calibrate_axes(hazards=[door], prior=None)
        assert not fake.fired


def test_each_probe_is_judged_from_where_the_last_one_left_him(game):
    """Door D below (30u) leaves the up axis one-sided, and the up probe carries him ~150u north -- beside
    door H, which the right probe would have cleared from where calibration BEGAN. Judged from where he
    stands when it is pressed, the right probe shrinks to a walk; judged from the start it ran into H."""
    door_d = _rect(-600, -100, 600, -30)
    door_h = _rect(100, 90, 400, 400)
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": door_d, "to": 30821, "arrive": (0, 0)},
                            {"zone": door_h, "to": 30810, "arrive": (0, 0)}]}
    fake.exit_frames = 60
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, 0, 0)
        mark = len(fake.executed)
        basis = g.calibrate_axes(hazards=[door_d, door_h], prior=_prior())
        assert not fake.fired, fake.fired
        assert basis["h"][0] > 0.99 and basis["v"][1] > 0.99, basis
        holds = [s for s in fake.executed[mark:] if s[0] == "hold" and s[1] != "cancel"]
        assert ["hold", "right", "4"] not in holds, holds       # the run that reached H from (0, 150)


def test_a_probe_may_leave_the_region_he_stands_in_but_not_come_back(game):
    """Standing inside a region (Z, a hazard with no live trigger here), the up probe walks out of it. The
    down probe after it starts OUTSIDE Z now, and a run would carry him back in: it must shrink to a walk.
    The old guard ignored any region containing the START, for every probe of the calibration."""
    zone = _rect(-600, -40, 600, 60)
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, 0, 20)
        mark = len(fake.executed)
        g.calibrate_axes(hazards=[zone], prior=_prior())
        holds = [s for s in fake.executed[mark:] if s[0] == "hold" and s[1] != "cancel"]
        assert ["hold", "up", "4"] in holds, holds              # out through the top: allowed
        assert ["hold", "down", "4"] not in holds, holds        # back in: refused
        assert g.state.player_z > 60, "he ended back inside the region he walked out of"


def test_walk_to_halts_the_moment_control_goes(game):
    """A gateway takes control on the frame it fires; the field id changes a fade later. A burst pressed in
    between carries its hold into the destination -- the 350 bounce. halt_on_transition presses nothing more."""
    door = _rect(100, -600, 300, 600)
    for halt in (True, False):
        fake = FakeGame(game)
        fake.regions = {30820: [{"zone": door, "to": 30821, "arrive": (-400, 0)}]}
        fake.exit_frames = 240                            # a slow fade, so the driver sees it
        with session(game, fake) as g:
            boot(g)
            g.warp(30820)
            _stand(g, fake, -300, 0)
            g.calibrate_axes()
            assert g.walk_to(500.0, 0.0, strict=False, halt_on_transition=halt) is False
            assert fake.fired, "the walk never reached the door"
            after = [s for s in fake.executed[fake.fired[0]["executed"]:] if s[0] == "hold"]
            if halt:
                assert not after, f"pressed {after} after control was gone"
            else:
                assert after, "the default loop was expected to keep pressing (the leak it documents)"


def test_route_to_reports_no_route_rather_than_walking_into_the_region(game):
    door = _rect(100, -200, 400, 200)
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": door, "to": 30821, "arrive": (0, 0)}]}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -300, 0)
        rec = g.route_to(250.0, 0.0, avoid=[door], walkmesh=_flat_bgi(), prior=_prior())
        assert rec["waypoints"] is None and rec["landed"] is None and not rec["reached"], rec
        assert not fake.fired


# --------------------------------------------------------------------------- route_to(unstick=True)
# The rung-3 run's crossings in stock Dali that planned a route and then travelled 0: pressed into a villager
# and into a Dali child, with control held the whole time. The router knows walls and zones, not bodies, and
# nothing published tells a freeze with control held (the script's pad mask) from a body in the way -- so these
# pin what MOVEMENT decides: wait a freeze out, push through anyone the engine lets him pass (no object flag
# 16: no NPC on stock 350 sets it), route round anyone it does not, stay out of every avoided zone doing it,
# give up cleanly on a freeze that never lifts, and never leave a phantom behind a call that could not use it.

_BAND = _rect(-160, -600, -100, 600)                   # a strip across the route: step on it and movement holds
_LANE = (-600, -150, 600, 150)                         # narrower than 2 * (OBSTACLE_R_W + the 80u radius)


_ROOM_AND_LANE = [(-1200, -600, 0, 600), (0, -150, 1200, 150)]     # a wide room opening into a 300-wide lane


def _l_bgi():
    """:data:`_ROOM_AND_LANE` as a real walkmesh in WORLD coords, for the router (the fake takes the boxes)."""
    from ff9mapkit.scene import bgi
    v = [(-1200, 0, 600), (0, 0, 600), (0, 0, 150), (1200, 0, 150), (1200, 0, -150), (0, 0, -150), (0, 0, -600),
         (-1200, 0, -600)]
    faces = [(0, 1, 2), (0, 2, 5), (0, 5, 7), (5, 6, 7), (2, 3, 4), (2, 4, 5)]
    return bgi.BgiWalkmesh.from_bytes(bgi.build(v, faces).to_bytes())


def test_one_unbroken_hold_walks_through_a_passable_body_and_bursts_never_do(game):
    """The engine's walk-through-by-insisting, as the fake models it (FieldMapActorController.CheckCollFallback):
    route_to's bursts, a pause apart, are pushed back every time; one hold past the 26-call lock goes through --
    unless the body is solid (object flag 16), when nothing does."""
    fake = FakeGame(game)
    fake.blockers = {30820: [(0.0, 0.0, 152.0)]}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -152, 0)                        # in contact
        for _ in range(6):
            g.send("hold right 12", "wait 16")
        assert abs(g.settle().player_x + 152) < 1, g.state.pos
        g.send("hold right 40", "wait 44")
        assert g.settle().player_x > 152, g.state.pos
        fake.blockers = {30820: [(0.0, 0.0, 152.0, True)]}
        _stand(g, fake, -152, 0)
        g.send("hold right 60", "wait 64")
        assert abs(g.settle().player_x + 152) < 1, g.state.pos


def test_a_push_is_pressed_only_when_a_probe_finds_him_stuck(game):
    """A push is ~30 frames held blind, and walk_to also stops on an overshoot, a slide or max_bursts -- none of
    them a body. Pressed into nobody it would be a run, so a two-frame walk probe goes first: free, no push; into
    a passable body, through; into a solid one, stuck -- and only the last two count as pushes."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -300, -300)
        g.calibrate_axes(hazards=[], prior=_prior())
        _stand(g, fake, -400, 0)
        record, walked = {"pushes": 0, "pushed": 0}, [0.0]
        mark = len(fake.executed)
        assert g._push_through(0.0, 0.0, 30820, walked, record) == "free"
        holds = [int(s[2]) for s in fake.executed[mark:] if s[0] == "hold" and s[1] != "cancel"]
        assert holds == [2] and record == {"pushes": 0, "pushed": 0} and walked[0] < 60, (holds, record, walked)
        fake.blockers = {30820: [(0.0, 0.0, 152.0)]}
        _stand(g, fake, -152, 0)
        assert g._push_through(200.0, 0.0, 30820, walked, record) == "pushed", g.state.pos
        assert record == {"pushes": 1, "pushed": 1} and g.state.player_x > 152, (record, g.state.pos)
        fake.blockers = {30820: [(0.0, 0.0, 152.0, True)]}
        _stand(g, fake, -152, 0)
        assert g._push_through(200.0, 0.0, 30820, walked, record) == "stuck"
        assert record == {"pushes": 2, "pushed": 1} and abs(g.state.player_x + 152) < 1, (record, g.state.pos)


def test_route_to_unstick_waits_out_a_freeze_with_control_held(game):
    """A freeze that outlasts the stall check and ends inside one wait: the walk goes on from where it stood,
    and neither a push nor a blocker goes in -- nobody was there."""
    fake = FakeGame(game)
    fake.freezes = {30820: [{"zone": _BAND, "frames": 360}]}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -400, 0)
        g.ROUTE_WAIT_FRAMES = 480                      # one wait covers the freeze, whatever the stall check took
        rec = g.route_to(400.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), unstick=True)
        assert fake._froze, "premise: the walk never stepped on the freeze"
        assert rec["reached"] and rec["landed"] is None, rec
        assert rec["waits"] >= 1 and rec["cleared"] >= 1 and rec["pushes"] == 0, rec
        assert rec["blockers"] == [] and not rec["frozen"] and not rec["blocked"], rec
        assert g._blockers[1] == []


def test_route_to_without_unstick_is_unchanged_by_a_freeze(game):
    """The control: the same freeze (for good, here) and no flag -- the old stall-and-replan, no wait, no push,
    and the new record fields all at rest."""
    fake = FakeGame(game)
    fake.freezes = {30820: [{"zone": _BAND, "frames": None}]}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -400, 0)
        mark = len(fake.executed)
        rec = g.route_to(400.0, 0.0, walkmesh=_flat_bgi(), prior=_prior())
        assert not rec["reached"] and rec["replans"] == g.ROUTE_REPLANS, rec
        assert (rec["waits"], rec["cleared"], rec["pushes"], rec["pushed"], rec["blockers"], rec["blocked"],
                rec["frozen"]) == (0, 0, 0, 0, [], False, False), rec
        waits = [s for s in fake.executed[mark:] if s[0] == "wait" and int(s[1]) == g.ROUTE_WAIT_FRAMES]
        assert not waits, waits
        long_holds = [s for s in fake.executed[mark:] if s[0] == "hold" and int(s[2]) > 20]
        assert not long_holds, long_holds


def test_route_to_unstick_gives_up_cleanly_on_a_freeze_that_never_lifts(game):
    """No hang, bounded waits and pushes, and no phantoms: each stall reads as a body ahead and each replan
    presses a way the ones before it left open, and he never moves -- so they were no bodies. Withdrawn, from
    the record and from the visit."""
    fake = FakeGame(game)
    fake.freezes = {30820: [{"zone": _BAND, "frames": None}]}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -400, 0)
        g.ROUTE_WAIT_FRAMES = 30
        t0 = time.time()
        rec = g.route_to(400.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), unstick=True)
        assert time.time() - t0 < 60, "a freeze that never lifts must end the call, not hang it"
        assert rec["frozen"] and not rec["reached"] and rec["landed"] is None and rec["during"] is None, rec
        assert 1 <= rec["waits"] <= g.ROUTE_WAIT_BUDGET, rec
        assert 1 <= rec["pushes"] <= g.ROUTE_PUSH_BUDGET and rec["pushed"] == 0, rec
        assert rec["blockers"] == [] and not rec["blocked"], rec
        assert g._blockers[1] == [], "a blocker read off a freeze must not outlive the call"
        assert g.state.control and g.state.field_id == 30820


def test_a_freeze_in_a_narrow_lane_is_not_read_as_a_sealed_way(game):
    """No body anywhere, a freeze in a lane too narrow to route round one: the first phantom seals it at once.
    He has not moved since it went in, so that is not evidence of a body -- ``frozen``, never the REAL strike
    ``blocked``, and the phantom leaves with the call instead of sealing the lane for the rest of the visit."""
    fake = FakeGame(game)
    fake.walkmesh = _LANE
    fake.freezes = {30820: [{"zone": _BAND, "frames": None}]}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -400, 0)
        g.ROUTE_WAIT_FRAMES = 30
        rec = g.route_to(400.0, 0.0, walkmesh=_flat_bgi(*_LANE), prior=_prior(), unstick=True)
        assert rec["frozen"] and not rec["blocked"] and rec["blockers"] == [], rec
        assert g._blockers[1] == [], g._blockers


def test_route_to_unstick_pushes_through_a_passable_body_without_placing_a_blocker(game):
    """THE 350 VILLAGER, as the engine has it: someone standing on the line pressed, without object flag 16.
    Without the flag the bursts stall against him forever; with it the waits go first (he might walk off), then
    one unbroken hold takes him through -- no blocker, no detour, nothing remembered."""
    fake = FakeGame(game)
    fake.blockers = {30820: [(0.0, 0.0, 152.0)]}       # 350's NPCs: SetObjectLogicalSize(14, 14, 22), flags 5/7/1
    wm = _flat_bgi()
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -400, 0)
        g.ROUTE_WAIT_FRAMES = 30
        old = g.route_to(400.0, 0.0, walkmesh=wm, prior=_prior())
        assert not old["reached"] and abs(g.state.player_x + 152) < 2, (old, g.state.pos)     # the premise
        rec = g.route_to(400.0, 0.0, walkmesh=wm, prior=_prior(), unstick=True)
        assert rec["reached"] and not rec["frozen"] and not rec["blocked"], rec
        assert rec["waits"] == g.ROUTE_WAITS and rec["pushes"] == 1 and rec["pushed"] == 1, rec
        assert rec["blockers"] == [] and g._blockers[1] == [], rec


def test_route_to_unstick_routes_round_a_solid_body_and_remembers_it_for_the_visit(game):
    """A body on the straight line that the engine never lets him through (object flag 16), standing still. Without
    the flag the route stalls and replans the SAME line from the same spot; with it the push fails, the body
    goes in as an obstacle and the walk goes round. The walk back plans round it from the start; a field change,
    anything taking control, or ROUTE_BLOCKER_TTL forgets it."""
    fake = FakeGame(game)
    fake.blockers = {30820: [(0.0, 0.0, 192.0, True)]}     # pathfind.OBSTACLE_R_W: the distance the router keeps
    wm = _flat_bgi()
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -400, 0)
        g.ROUTE_WAIT_FRAMES = 30                       # a body does not walk off in a test; keep the waits short
        old = g.route_to(400.0, 0.0, walkmesh=wm, prior=_prior())
        assert not old["reached"] and old["replans"] == g.ROUTE_REPLANS, old     # the premise
        assert abs(g.state.player_x + 192) < 2, g.state.pos                    # stopped dead against it
        rec = g.route_to(400.0, 0.0, walkmesh=wm, prior=_prior(), unstick=True)
        assert rec["reached"], rec
        assert len(rec["blockers"]) >= 1 and rec["waits"] >= g.ROUTE_WAITS and rec["cleared"] == 0, rec
        assert rec["pushes"] >= 1 and rec["pushed"] == 0, rec
        bx, bz = rec["blockers"][0]
        assert abs(bx - 1) <= 2 and abs(bz) <= 2, "placed on the line pressed, at the collision distance"
        assert g._blockers[0] == 30820 and g._blockers[1]
        back = g.route_to(-400.0, 0.0, walkmesh=wm, prior=_prior(), unstick=True)
        assert back["reached"] and back["remembered"] >= 1, back
        assert (back["waits"], back["pushes"], back["blockers"]) == (0, 0, []), "walked into the remembered body"
        g.warp(30821)
        g.warp(30820)
        assert g._blockers[1] == [], "a new visit starts with no blockers"
        g._visit_blockers(30820).append((1.0, 0.0))    # ...and so does anything that takes control on the field
        fake.control = False                           # (a scene: the room's people may have moved)
        published(g, lambda s: not s.control)
        assert g._blockers[1] == []
        fake.control = True
        published(g, lambda s: s.control)
        g._visit_blockers(30820).append((1.0, 0.0))    # ...and so does time: people walk off
        g._blocker_at[(1.0, 0.0)] = time.time() - g.ROUTE_BLOCKER_TTL - 1
        assert g._visit_blockers(30820) == []


def test_route_to_unstick_reads_a_wedge_as_bodies_not_a_freeze(game):
    """Stuck against one body, and the first way round is shut by another (up and right both moved him 0u at
    350's crossings 10-12). Two directions that do not move him are a wedge, not a freeze: the third way does,
    and the walk goes round both. Solid here, so the pushes cannot settle it for him."""
    fake = FakeGame(game)
    fake.blockers = {30820: [(0.0, 192.0, 192.0, True), (192.0, 0.0, 192.0, True)]}   # touching him, N and E
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -300, -300)
        g.calibrate_axes(hazards=[], prior=_prior())       # in the open, so its probes do not unwedge him
        _stand(g, fake, 0, 0)
        g.ROUTE_WAIT_FRAMES = 30
        rec = g.route_to(400.0, 400.0, walkmesh=_flat_bgi(), prior=_prior(), unstick=True)
        assert rec["reached"] and not rec["frozen"], rec
        assert len(rec["blockers"]) >= 2, rec


def test_a_way_sealed_after_he_moved_is_blocked_and_leaves_no_phantom(game):
    """``blocked`` -- the REAL strike -- needs him to have MOVED since the call's first blocker: round one solid
    body in the wide room, then another sealing the 300-wide corridor. And even then the call's blockers are
    withdrawn from the visit: a phantom never outlives the call that could not use it."""
    fake = FakeGame(game)
    fake.walkmesh = _ROOM_AND_LANE
    fake.blockers = {30820: [(-700.0, 0.0, 192.0, True), (300.0, 0.0, 152.0, True)]}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -1000, 0)
        g.ROUTE_WAIT_FRAMES = 30
        rec = g.route_to(1000.0, 0.0, walkmesh=_l_bgi(), prior=_prior(), unstick=True)
        assert rec["blocked"] and not rec["frozen"] and not rec["reached"], rec
        assert len(rec["blockers"]) >= 2 and g.state.player_x > 0, (rec, g.state.pos)   # it got into the corridor
        assert g._blockers[1] == [], g._blockers


@pytest.mark.parametrize("off, solid", [(10, True), (30, True), (60, True), (30, False)])
def test_route_to_unstick_reads_a_slide_round_a_body_as_a_stall_not_a_bad_basis(game, off, solid):
    """A body a little off the pressed line: the engine pushes him out along the line from its centre, so he
    slides SIDEWAYS -- which walk_to's basis check reads as a wrong basis, raising and throwing the basis away.
    Under unstick the slide is a stall like any other: no raise, the basis kept, the goal reached."""
    body = (0.0, float(off), 192.0, True) if solid else (0.0, float(off), 152.0)
    fake = FakeGame(game)
    fake.blockers = {30820: [body]}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -400, 0)
        g.ROUTE_WAIT_FRAMES = 30
        if off == 30 and solid:                        # the control: the old verb still raises (and pops)
            with pytest.raises(HarnessError, match="disagrees"):
                g.route_to(400.0, 0.0, walkmesh=_flat_bgi(), prior=_prior())
            assert 30820 not in g._axes
            _stand(g, fake, -400, 0)
        rec = g.route_to(400.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), unstick=True)
        assert rec["reached"], rec
        assert 30820 in g._axes


def test_route_cross_with_its_zone_says_where_the_walk_ended(game):
    """``zone`` tells "never got there" (``inside`` False -- and no 20 s wait for a gateway that cannot fire
    from out there) from "got there and nothing fired" (``inside`` True, the whole wait)."""
    from ff9mapkit.content import pathfind
    door = _rect(450, -150, 600, 150)
    wm = _flat_bgi(*_LANE)
    fake = FakeGame(game)
    fake.walkmesh = _LANE
    fake.blockers = {30820: [(200.0, 0.0, 152.0, True)]}   # a solid body shuts the lane short of the door
    fake.regions = {30820: [{"zone": door, "to": 30821, "arrive": (0, 0)}]}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -400, 0)
        g.ROUTE_WAIT_FRAMES = 30
        goal = pathfind.region_goal(wm, door)
        waited = []
        crossing = g.expect_field_change
        g.expect_field_change = lambda **kw: waited.append(kw["timeout"]) or crossing(**kw)
        rec = g.route_cross(goal[0], goal[1], walkmesh=wm, prior=_prior(), unstick=True, zone=door, timeout=20)
        assert rec["landed"] is None and rec["inside"] is False and not fake.fired, rec
        assert waited == [], "waited out a crossing that could not come"
        fake.blockers = {}
        fake.regions = {}                              # the zone is there; the gateway is story-gated shut
        rec = g.route_cross(goal[0], goal[1], walkmesh=wm, prior=_prior(), unstick=True, zone=door, timeout=2)
        assert rec["landed"] is None and rec["inside"] is True and waited == [2], (rec, waited)
        rec = g.route_cross(-400.0, 0.0, walkmesh=wm, prior=_prior(), unstick=True, timeout=2)
        assert rec["inside"] is None and waited == [2, 2], "no zone: no verdict, and the wait as it was"


def test_a_blocker_replan_never_enters_an_avoided_zone(game):
    """The detour round a body is planned by the same route_avoiding, so a door on the side the router would
    otherwise take is kept out of exactly as before. The door is a LIVE region here: entering it fires."""
    from ff9mapkit.content import pathfind
    door = _rect(-300, -600, 300, -150)
    wm = _flat_bgi()
    stall, body_seen = (-192.0, 0.0), (1.0, 0.0)       # where he stops, and where _blocker_ahead puts the body
    free = pathfind.route_avoiding(wm, stall, (400, 0), [], obstacles=[body_seen])
    legs = [stall] + [tuple(w) for w in free]
    assert any(pathfind.seg_poly_gap(a, b, door) < 0 for a, b in zip(legs, legs[1:])), \
        f"premise: without the door the detour goes through it ({free})"
    fake = FakeGame(game)
    fake.blockers = {30820: [(0.0, 0.0, 192.0, True)]}
    fake.regions = {30820: [{"zone": door, "to": 30821, "arrive": (0, 0)}]}
    fake.exit_frames = 30
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -400, 0)
        g.ROUTE_WAIT_FRAMES = 30
        rec = g.route_to(400.0, 0.0, avoid=[door], walkmesh=wm, prior=_prior(), unstick=True)
        assert rec["blockers"], f"premise: the walk never met the body ({rec})"
        assert not fake.fired, fake.fired
        assert rec["landed"] is None and g.state.field_id == 30820 and rec["reached"], rec


def test_key_twist_operand_follows_memoria_ini(game):
    """Keys read TWIST arg2 (twist.y) unless [AnalogControl] makes key orientation absolute (1 or 2)."""
    fake = FakeGame(game)
    g = session(game, fake)
    ini = game / "Memoria.ini"
    assert g._key_twist_operand() == 1                    # no ini: the engine default (3)
    for text, want in (("[AnalogControl]\nEnabled = 1\nUseAbsoluteOrientation = 3\n", 1),
                       ("[AnalogControl]\nEnabled = 1\nUseAbsoluteOrientation = 2\n", 0),
                       ("[AnalogControl]\nEnabled = 0\nUseAbsoluteOrientation = 1\n", 1),
                       ("[Graphics]\nUseAbsoluteOrientation = 1\n[AnalogControl]\nEnabled = 1\n", 1)):
        ini.write_text(text, encoding="utf-8")
        assert g._key_twist_operand() == want, text


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


# --------------------------------------------------------------------------- the story-write trace (s88)


def test_state_maps_the_storytrace_block_and_tells_absent_from_off():
    """No block = an engine that cannot trace -- NOT a trace that is off. Reading the absence as "off" would
    let an empty story.jsonl pass for "no script wrote anything"."""
    assert State({"frame": 1}).storytrace is None
    st = State({"frame": 1, "storytrace": {"proto": 1, "on": False, "rows": 0, "suppressed": 0,
                                           "error": None}})
    assert st.storytrace == {"proto": 1, "on": False, "rows": 0, "suppressed": 0, "error": None}


def test_reset_clears_the_story_trace_and_collect_keeps_it(game, tmp_path):
    """The engine only APPENDS to story.jsonl: a reset that left it would hand this run the last run's rows."""
    ch = Channel(game)
    ch.reset()
    ch.story_path.write_text('{"k":"e"}\n', encoding="utf-8")
    ch.collect(tmp_path / "out")
    assert (tmp_path / "out" / "story.jsonl").read_text(encoding="utf-8") == '{"k":"e"}\n'
    ch.reset()
    assert not ch.story_path.exists() and ch.story_text() is None


def test_storytrace_refuses_an_engine_that_does_not_advertise_it(game):
    fake = FakeGame(game)
    fake.storytrace_proto = None
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError, match="predates the story trace"):
            g.storytrace()
        assert not any(step[0] == "storytrace" for step in fake.executed)   # refused before sending


def test_storytrace_refuses_a_proto_this_driver_does_not_read(game):
    fake = FakeGame(game)
    fake.storytrace_proto = 2
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError, match="proto 2, this driver reads proto 1"):
            g.storytrace()


def test_story_rows_refuses_before_a_trace_was_started(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError, match="no story trace was started"):
            g.story_rows()


def test_a_trace_reads_back_as_validated_contract_rows(game):
    """storytrace() -> the arm epoch; the driver's own flag/byte pokes land as `harness` rows (never residue);
    a script store as an `eb` row; storytrace(False) -> the off epoch. Every row passes the kit's proto-1
    parser, and the epochs segment the way the engine closes them."""
    from ff9mapkit.storytrace import epochs

    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        st = g.storytrace()
        assert st.storytrace["on"] is True
        g.flag(9000)
        g.poke(236, 15)
        fake.script_store(sid=0, tag=0, ip=77, byte=9, width="UInt16", new=1582)
        rows = g.story_rows()
        assert [(r.k, r.src) for r in rows] == [("e", None), ("w", "harness"), ("w", "harness"), ("w", "eb")]
        assert rows[1].target == "Global.Bit[9000]" and (rows[1].old, rows[1].new) == (0, 1)
        assert rows[2].target == "Global.Byte[236]" and rows[2].new == 15
        assert (rows[3].sid, rows[3].tag, rows[3].ip, rows[3].fld) == (0, 0, 77, 30810)
        st = g.storytrace(False)
        assert st.storytrace["on"] is False
        rows = g.story_rows()
        assert rows[-1].k == "e" and rows[-1].why == "off"
        [ep] = epochs(rows)
        assert (ep.why, ep.closed_by, len(ep.writes)) == ("arm", "off", 3)
    assert (game / "run" / "story.jsonl").is_file()                          # collected with the run


def test_an_append_in_flight_waits_and_a_broken_line_raises(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.storytrace()
        path = g.channel.story_path
        with path.open("a", encoding="utf-8") as fh:
            fh.write('{"k":"w","f":9')                                        # the engine mid-append
        assert [r.k for r in g.story_rows()] == ["e"]
        with path.open("a", encoding="utf-8") as fh:
            fh.write(',"oops":1}\n')                                         # ...and it lands broken
        with pytest.raises(HarnessError, match="breaks the row contract"):
            g.story_rows()


def test_an_armed_run_that_never_traces_writes_no_file(game):
    """Arming resets the tracer to OFF, silently: pokes without `storytrace 1` leave no story.jsonl."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.flag(9000)
        g.poke(236, 15)
        assert g.channel.story_text() is None
    assert not (game / "run" / "story.jsonl").exists()


def test_reset_stops_the_trace_and_a_faulted_tracer_refuses_with_its_reason(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.storytrace()
        g.send("reset")                                     # one scenario's trace must not run into the next
        st = published(g, lambda s: s.storytrace is not None and not s.storytrace["on"])
        assert g.story_rows()[-1].why == "off" and st.storytrace["error"] is None
        fake.story_fault("story.jsonl has not accepted an append")
        with pytest.raises(HarnessError, match="turned itself off earlier"):
            g.storytrace()


def test_closing_a_faulted_trace_raises_with_the_engines_reason(game):
    """StoryTrace.Fail turns the tracer off with NO `off` row: `on` is already false, so a close that only
    waited for `on` would return, and the cut file would read as a whole run -- an empty STOCK ONLY from a
    broken instrument."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.storytrace()
        fake.script_store(sid=0, tag=0, ip=77, byte=9, width="UInt16", new=1582)
        fake.story_fault("story.jsonl has not accepted an append for 16777216 buffered chars")
        with pytest.raises(HarnessError, match="FAULTED .*16777216 buffered chars"):
            g.storytrace(False)
        with pytest.raises(HarnessError, match="FAULTED"):
            g.story_rows()


def test_closing_the_trace_waits_for_every_row_the_engine_counted(game):
    """The engine appends once per frame and keeps rows buffered while the file is locked: after `on` goes
    false, the published `rows` is final and the file catches up to it -- a close returns only then."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.storytrace()
        path = g.channel.story_path

        def land():
            with path.open("a", encoding="utf-8") as fh:
                fh.write(path.read_text(encoding="utf-8").splitlines()[0] + "\n")

        fake.story_rows += 1                                  # counted, still in the engine's buffer...
        late = threading.Timer(0.4, land)
        late.start()                                          # ...and it lands a few frames later
        try:
            t0 = time.time()
            g.storytrace(False)
            assert time.time() - t0 >= 0.3
        finally:
            late.join()


def test_closing_the_trace_refuses_a_shortfall_and_a_strangers_rows(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.storytrace()
        fake.story_rows += 2                                  # rows the engine wrote that never landed
        with pytest.raises(HarnessError, match="2 of the 4 rows the engine wrote never reached"):
            g.storytrace(False, timeout=1.0)
        fake.story_rows -= 2
        g.storytrace()
        with g.channel.story_path.open("a", encoding="utf-8") as fh:
            fh.write(g.channel.story_path.read_text(encoding="utf-8").splitlines()[0] + "\n")
        with pytest.raises(HarnessError, match="holds 5 rows but the engine wrote 4 since the arm"):
            g.storytrace(False)


def test_teardown_closes_an_open_trace_before_the_disarm(game):
    """keep_open/attach: no `quit`, so the agent stops the trace only when it NOTICES the disarm -- up to 30
    frames after a collect that runs at once. Closed first, the collected file carries its `off`."""
    from ff9mapkit.storytrace import epochs, read_trace
    fake = FakeGame(game)
    try:
        with session(game, fake, keep_open=True) as g:
            boot(g)
            g.storytrace()
            fake.script_store(sid=0, tag=0, ip=77, byte=9, width="UInt16", new=1582)
        [ep] = epochs(read_trace(game / "run" / "story.jsonl"))
        assert (ep.why, ep.closed_by, len(ep.writes)) == ("arm", "off", 1)
    finally:
        fake.stop()


def test_rearming_over_a_leaked_trace_drops_its_tail(game):
    """A driver crashed with the trace on. The next run's reset clears story.jsonl, then its arm cycle's
    disarm makes the still-tracing agent run StoryTrace.Stop -- whose last append would OPEN the new run's
    file with another arm's rows."""
    ch = Channel(game, label="leaked")
    ch.reset()
    fake = FakeGame(game).start()
    try:
        ch.arm(force_cycle=False)
        deadline = time.time() + 5
        while time.time() < deadline and not fake.armed:
            time.sleep(0.02)
        ch.send(["storytrace 1"])
        while time.time() < deadline and not fake.story_on:
            time.sleep(0.02)
        assert fake.story_on and ch.story_path.exists()
        second = Channel(game, label="next", owner_pid=ch.owner_pid)
        second.reset()
        second.arm()                                        # the cycle: the leaked agent stops, then re-arms
        deadline = time.time() + 5
        while time.time() < deadline and fake.arm_transitions < 2:
            time.sleep(0.02)
        assert fake.arm_transitions == 2 and not fake.story_on
        assert not second.story_path.exists(), second.story_path.read_text(encoding="utf-8")
    finally:
        ch.disarm()
        fake.stop()


def test_the_fake_refuses_the_verb_on_an_engine_that_cannot_trace(game):
    """A pre-s88 agent throws `unknown op` -- the stand-in must not trace for a driver that skips the gate."""
    fake = FakeGame(game)
    fake.storytrace_proto = None
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError, match="unknown op 'storytrace'"):
            g.send("storytrace 1")
        assert not g.channel.story_path.exists()


def test_each_suite_member_collects_its_own_traced_runs(game):
    """One story.jsonl holds every trace of a launch; a member's directory gets exactly its own, closed."""
    from ff9mapkit.storytrace import read_trace, split_runs
    fake = FakeGame(game)
    a = _scenario(game, "trace_a", "def run(g):\n    g.newgame(settle=0)\n    g.storytrace()\n"
                                   "    g.flag(9000)\n    g.check(True, 'traced')\n")
    b = _scenario(game, "quiet", "def run(g):\n    g.newgame(settle=0)\n    g.check(True, 'no trace')\n")
    c = _scenario(game, "trace_c", "def run(g):\n    g.newgame(settle=0)\n    g.storytrace()\n"
                                   "    g.poke(236, 15)\n    g.check(True, 'traced')\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{a}"\n\n[[scenario]]\npath="{b}"\n\n'
                           f'[[scenario]]\npath="{c}"\n')
    with session(game, fake) as g:
        meta, scenarios = load_manifest(path, game)
        results = SuiteRunner(g, scenarios, meta=meta, verbose=False).run()
    assert [r.get("story_runs") for r in results] == [1, None, 1]
    runs = {}
    for r in results:
        member = game / "run" / f"{r['index']:02d}-{r['label']}" / "story.jsonl"
        runs[r["label"]] = split_runs(read_trace(member)) if member.exists() else None
    assert runs["quiet"] is None
    [[arm, w, off]] = runs["trace_a"]
    assert (arm.why, w.target, off.why) == ("arm", "Global.Bit[9000]", "off")
    [[arm, w, off]] = runs["trace_c"]
    assert (arm.why, w.target, off.why) == ("arm", "Global.Byte[236]", "off")
    assert len(split_runs(read_trace(game / "run" / "story.jsonl"))) == 2    # the launch's file holds both


# ======================================================================================
# THE BENCH PREFLIGHT
#
# Bench ids are a global namespace another lane's deploy can wipe, and the harness reads EVERY
# mod folder's DictionaryPatch.txt. The preflight answers "is every bench this manifest needs
# deployed, and which folder serves it" BEFORE a four-minute boot -- and it was written the day
# a two-folder grep concluded two benches were gone when two other folders served them.
# ======================================================================================

from harness.suite import preflight_benches, render_preflight      # noqa: E402


def _other_folder(game, name: str, body: str) -> None:
    d = game / name
    d.mkdir(exist_ok=True)
    (d / "DictionaryPatch.txt").write_text(body, encoding="utf-8")


def test_preflight_names_the_folder_serving_each_bench(game):
    """Which folder serves an id is the fact a 'the bench is gone' diagnosis keeps getting wrong."""
    _other_folder(game, "FF9CustomMap-msgs", "FieldScene 30601 11 TEST30601 TEST30601 30601\n")
    rel = _scenario(game, "cs", "def run(g):\n    g.check(True, 'x')\n")
    path = _manifest(game, f'[suite]\nname="t"\nfield=30820\n\n[[scenario]]\npath="{rel}"\n'
                           f'\n[[scenario]]\npath="{rel}"\nfield=30601\nlabel="other"\n')
    _, scenarios = load_manifest(path, game)
    pre = preflight_benches(game, scenarios, stock=set())
    assert pre["missing"] == [] and pre["collisions"] == []
    assert pre["benches"][30820]["folders"] == [("FF9CustomMap", "ROOM_A")]
    assert pre["benches"][30601]["folders"] == [("FF9CustomMap-msgs", "TEST30601")]
    assert pre["benches"][30601]["scenarios"] == ["other"]
    text = render_preflight(pre)
    assert "FF9CustomMap-msgs (TEST30601)" in text and "<- other" in text
    assert sorted(pre["read"]) == ["FF9CustomMap", "FF9CustomMap-msgs"]


def test_preflight_reports_a_bench_no_folder_registers_with_its_deploy_command(game):
    """The answer used to arrive four minutes in, one warp() refusal at a time; now it arrives
    before the launch, with the command that puts the bench back."""
    rel = _scenario(game, "gone", "def run(g):\n    g.check(True, 'x')\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{rel}"\nfield=30999\n'
                           f'deploy="studies/x/bench.field.toml"\n')
    _, scenarios = load_manifest(path, game)
    assert scenarios[0].deploy == "studies/x/bench.field.toml"
    pre = preflight_benches(game, scenarios, stock=set())
    assert pre["missing"] == [30999]
    text = render_preflight(pre)
    assert "MISSING" in text
    assert "py tools/deploy_field.py studies/x/bench.field.toml --id 30999" in text


def test_preflight_says_when_a_missing_bench_has_no_known_source(game):
    """A missing bench with no `deploy =` hint is a bench this checkout cannot rebuild -- say so,
    rather than printing a command that does not exist."""
    rel = _scenario(game, "gone", "def run(g):\n    g.check(True, 'x')\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{rel}"\nfield=30999\n')
    _, scenarios = load_manifest(path, game)
    pre = preflight_benches(game, scenarios, stock=set())
    text = render_preflight(pre)
    assert "cannot be rebuilt from this checkout" in text
    assert "deploy_field.py" not in text


def test_preflight_flags_an_id_two_folders_register(game):
    """EventDB is global across stacked folders: the same id in two of them is the classic
    null-.eb black screen, and which side wins is FolderNames order the preflight cannot see."""
    _other_folder(game, "FF9CustomMap-schema", "FieldScene 30820 11 ROOM_A_TOO ROOM_A_TOO 30820\n")
    rel = _scenario(game, "cs", "def run(g):\n    g.check(True, 'x')\n")
    path = _manifest(game, f'[suite]\nname="t"\nfield=30820\n\n[[scenario]]\npath="{rel}"\n')
    _, scenarios = load_manifest(path, game)
    pre = preflight_benches(game, scenarios, stock=set())
    assert pre["collisions"] == [30820] and pre["missing"] == []
    assert "COLLISION" in render_preflight(pre)


def test_preflight_treats_a_stock_field_as_deployed(game):
    """The ~674 shipping rooms are registered by the base game and appear in no patch file."""
    rel = _scenario(game, "cs", "def run(g):\n    g.check(True, 'x')\n")
    path = _manifest(game, f'[suite]\nname="t"\nfield=1650\n\n[[scenario]]\npath="{rel}"\n')
    _, scenarios = load_manifest(path, game)
    pre = preflight_benches(game, scenarios, stock={1650})
    assert pre["missing"] == [] and pre["benches"][1650]["stock"]
    assert "stock FF9 field" in render_preflight(pre)
    # And WITHOUT the stock set it is missing -- the seam is what makes the test able to fail.
    assert preflight_benches(game, scenarios, stock=set())["missing"] == [1650]


def test_preflight_reads_nothing_when_no_folder_can_be_read(game):
    """'Nothing registered' and 'could not look' are different facts -- the report carries the
    list of folders it actually read so the caller can tell them apart."""
    (game / "FF9CustomMap" / "DictionaryPatch.txt").unlink()
    rel = _scenario(game, "cs", "def run(g):\n    g.check(True, 'x')\n")
    path = _manifest(game, f'[suite]\nname="t"\nfield=30820\n\n[[scenario]]\npath="{rel}"\n')
    _, scenarios = load_manifest(path, game)
    pre = preflight_benches(game, scenarios, stock=set())
    assert pre["read"] == [] and pre["missing"] == [30820]
    assert "no DictionaryPatch.txt under the install" in render_preflight(pre)


# ======================================================================================
# THE BATTLE HUD CURSOR
#
# battle_pick / battle_act steer the HUD by name against the engine's own ActiveButton. Their
# first live run (scenarios/battle_hud_check.py, 2026-09-04) found two facts the docstrings had
# assumed away: the command list is a two-column grid that does NOT wrap, so a one-direction
# walk cannot reach an entry above the cursor or the right-hand column at all; and the Ability /
# Item SUBMENUS are distinct NGUI groups from the target cursor -- "any group but the command
# list" confirmed a Potion. The stand-in now lays its grid out the same way.
# ======================================================================================


def _hud_turn(game):
    """A fake battle past its intro with the command cursor open on slot 0."""
    fake = FakeGame(game)
    fake.atb_gain = 400
    # ⚠ A harmless enemy. Walking a grid is a dozen presses at ten frames each, and at this ATB rate
    # a 90-damage enemy kills the party mid-walk -- the cursor then vanishes and the test fails for
    # a reason that has nothing to do with the cursor.
    fake.enemy_hit = 0
    g = session(game, fake)
    g.start()
    boot(g)
    g.warp(30810)
    g.start_battle(105)
    g.wait_turn()
    published(g, lambda s: s.battle_cursor.get("group") == "Battle.Command")
    return fake, g


def test_battle_pick_reaches_a_command_above_the_cursor(game):
    """From `Item` (bottom of the left column) a down-only walk sees Item forever and never Attack.
    Break: make battle_pick walk `direction` only, and this goes red with 'not on the battle
    command list ... saw [Item]'."""
    fake, g = _hud_turn(game)
    try:
        g.press("down", 4); g.press("down", 4)
        published(g, lambda s: s.battle_cursor.get("label") == "Item")
        assert g.battle_pick("Attack", confirm=False) == "Attack"
        st = published(g, lambda s: s.battle_cursor.get("label") == "Attack")
        assert st.battle_cursor["group"] == "Battle.Command"
    finally:
        g.stop()


def test_battle_pick_finds_a_command_in_the_other_column(game):
    """`Skill` lives in the right-hand column; up/down alone never visits it."""
    fake, g = _hud_turn(game)
    try:
        assert g.battle_pick("Skill", confirm=False) == "Skill"
        published(g, lambda s: s.battle_cursor.get("label") == "Skill")
    finally:
        g.stop()


def test_battle_pick_names_what_it_saw_when_the_command_is_not_there(game):
    fake, g = _hud_turn(game)
    try:
        with pytest.raises(HarnessError, match="not on the battle command list") as err:
            g.battle_pick("Summon", confirm=False)
        # Both columns were walked before giving up, and the message says what IS there.
        assert "Attack" in str(err.value) and "Skill" in str(err.value)
    finally:
        g.stop()


def test_battle_act_refuses_a_submenu_as_the_target_cursor(game):
    """Confirming `Item` opens Battle.Item, not Battle.Target. The first cut confirmed straight
    through it -- a Potion, not an enemy. Break: accept any group but the command list, and this
    goes red because no HarnessError is raised (and fake.battle_commands gains an item command)."""
    fake, g = _hud_turn(game)
    try:
        with pytest.raises(HarnessError, match="submenu"):
            g.battle_act("Item")
        assert fake.battle_commands == [], fake.battle_commands
        # And it backed out: the command list is open again, not the item list.
        published(g, lambda s: s.battle_cursor.get("group") == "Battle.Command")
    finally:
        g.stop()


def test_pid_alive_reads_access_denied_as_alive(monkeypatch):
    """OpenProcess failing with ERROR_ACCESS_DENIED means the process EXISTS and is not ours to open.
    Read through the plain `ctypes.windll.kernel32`, `ctypes.get_last_error()` is always 0, so the
    branch could never fire and another account's live run had its arm adopted. Break: go back to
    `ctypes.windll.kernel32`, and the 5 set below is never seen."""
    import ctypes
    from harness import channel

    class Stub:
        def __init__(self, err):
            self.err = err

        def OpenProcess(self, *a):
            ctypes.set_last_error(self.err)
            return 0

    monkeypatch.setattr(channel, "_K32", Stub(5))          # ERROR_ACCESS_DENIED
    assert channel.pid_alive(424242) is True
    monkeypatch.setattr(channel, "_K32", Stub(87))         # ERROR_INVALID_PARAMETER: no such pid
    assert channel.pid_alive(424242) is False
    # And the real thing: our own pid is alive, a pid nobody has is not.
    monkeypatch.setattr(channel, "_K32", None)
    assert channel.pid_alive(os.getpid()) is True
    assert channel.pid_alive(4000000) is False


def test_flee_does_not_call_a_wipe_an_escape(game):
    """flee()'s wait also returns when the battle ENDS -- for any reason. The first cut returned
    True on every one of them, so a party wiped out mid-hold was reported as having run away.
    Break: make flee() return True whenever its wait returns, and this goes red."""
    fake = FakeGame(game)
    fake.atb_gain = 400
    fake.escape_rate = 0.0                     # the dice never land...
    fake.enemy_hit = 5000                      # ...and the enemy ends the fight in one hit
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        g.start_battle(105)
        published(g, lambda s: s.commands_enabled)
        assert g.flee(timeout=6.0) is False
        st = published(g, lambda s: not s.in_battle)
        assert st.battle_result_name == "defeat"


def test_the_last_fight_record_does_not_carry_into_the_next_scenario(game):
    """battle_play judges the turn loop on `last_fight["turns"]`; a member whose fight() raised
    before recording anything must not be judged on the previous member's fight."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.last_fight = {"turns": 3, "result": 1, "name": "victory", "epoch": 8}
        g.begin_scenario("next")
        assert g.last_fight is None


def test_battle_act_confirms_a_target_and_the_command_lands(game):
    """The positive path: pick Attack, wait for Battle.Target EXACTLY, confirm -- and the command
    reaches the engine's queue with the enemy's id, then its HP falls."""
    fake, g = _hud_turn(game)
    try:
        foe = next(u for u in fake.battle_units if not u["player"])
        before = foe["hp"]
        assert g.battle_act("Attack") is True
        published(g, lambda s: bool(fake.battle_commands))
        assert fake.battle_commands[0][:2] == [0, 1] and fake.battle_commands[0][3] == foe["id"]
        published(g, lambda s: next(u for u in s.units(player=False))["hp"] < before, timeout=6.0)
    finally:
        g.stop()


# ======================================================================================
# THE DIAGNOSABILITY ARTIFACTS (PLAN.md next-action 4)
#
# A failed check used to leave one screenshot and a state-final.json captured AFTER quit.
# Now: steps.jsonl (every request, with when the agent accepted it and when it finished),
# a ring of the last ~10 s of state flushed on failure and always once before quit, evidence
# on every failed check under a cap, and env.json (which DLL, which registrations, which
# ini values). Each writer may fail; none may raise into the run -- and each test names what
# to break to see it red.
# ======================================================================================

import hashlib                                                     # noqa: E402

from harness import PROTOCOL                                       # noqa: E402
from harness import artifacts as _art                              # noqa: E402
from harness import session as _sess                               # noqa: E402
from harness.artifacts import StateRing, read_memoria_ini           # noqa: E402


def _rows(path: pathlib.Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _dead_launcher():
    class Dead:
        returncode = None

        def poll(self):
            return None

        def wait(self, timeout=None):
            return 0

        def kill(self):
            pass
    return Dead()


def test_the_state_ring_dedupes_on_frame_and_keeps_only_the_last_n(tmp_path):
    """Break: drop the `!=` test (every poll of the same document is kept) or use a list."""
    ring = StateRing(3)
    kept = [ring.push(State({"frame": f})) for f in (1, 1, 2, 3, 4)]
    assert kept == [True, False, True, True, True]
    assert ring.frames() == [2, 3, 4]
    assert ring.dump(tmp_path / "s.jsonl") == 3
    assert [r["state"]["frame"] for r in _rows(tmp_path / "s.jsonl")] == [2, 3, 4]


def test_memoria_ini_is_read_the_way_the_engine_does(tmp_path):
    """LAST wins (Memoria's IniFile.Init is a plain dictionary assignment per line, and it re-enters
    a repeated section), the stock file's BOM and tab-indented `;` blocks are tolerated, and a junk
    line costs nothing. Break: take the first match, or parse with a strict configparser."""
    ini = tmp_path / "Memoria.ini"
    ini.write_text('﻿[Mod]\n\t; the launcher rewrites this\nFolderNames = "A", "B"\n'
                   '[AnalogControl]\nEnabled = 0\n[Cheats]\nSpeedMode = 1\nthis line is junk\n'
                   '[AnalogControl]\nEnabled = 1\n[Control]\nSoftReset = 1\nKeyBindings = "W"\n',
                   encoding="utf-8")
    doc = read_memoria_ini(ini)
    assert doc["AnalogControl"]["Enabled"] == "1"
    assert doc["Cheats"] == {"SpeedMode": "1"}
    assert doc["Control"] == {"SoftReset": "1"}          # only the keys asked for
    assert doc["mod_folders"] == ["A", "B"]
    assert read_memoria_ini(tmp_path / "missing.ini") is None


def test_a_broken_ring_observer_cannot_turn_a_healthy_read_into_no_state(game):
    """Break: remove the try/except around the observer in Channel.state()."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        def raiser(st):
            raise RuntimeError("boom")
        g.channel.observer = raiser
        assert g.state is not None
        g.wait_for(lambda s: s.frame > 0, timeout=5)


def test_the_ring_is_fed_by_the_reads_a_wait_already_makes(game):
    """No thread, no extra poll: every document in the ring IS one Channel.state() returned, and
    while nothing reads, nothing reaches it. Break: feed the ring from a timer thread, or read the
    file a second time inside push().

    ⚠ The spy goes on BEFORE start(). start() already reads state (_await_agent, _adopt_agent,
    write_env) and those reads feed the ring too; a spy installed inside the with-block never saw
    start's last frame, so whenever the stand-in moved on before the first spied read -- routinely
    under -n 6 -- that frame sat in the ring alone and the test failed a driver that was right.
    """
    fake = FakeGame(game)
    g = session(game, fake)
    returned: list[dict] = []      # every document a read handed back, kept alive so id() is unique
    real = g.channel.state

    def spy(*a, **k):
        st = real(*a, **k)
        if st is not None:
            returned.append(st.raw)
        return st

    g.channel.state = spy
    with g:
        threads = threading.active_count()
        boot(g)
        g.wait_frames(10)
        assert len(g._ring) > 0
        # By IDENTITY, not by frame: a second read inside push() lands microseconds after the first,
        # so it almost always parses the same frame and a frame comparison waves it through. Its
        # document is still a different object.
        ids = {id(d) for d in returned}
        assert [raw.get("frame") for *_, raw in g._ring._buf if id(raw) not in ids] == []
        # The idle window. A timer thread that polls THROUGH Channel.state() passes the check above
        # (the spy returned its documents too) and, started in start(), is already counted in
        # `threads`. What it cannot do is leave the ring alone while the driver reads nothing.
        ring, published = set(g._ring.frames()), fake.publish_frame
        time.sleep(0.25)
        assert fake.publish_frame > published          # the stand-in kept publishing: not vacuous
        assert [f for f in g._ring.frames() if f not in ring] == []   # arrived with nobody reading
        assert threading.active_count() == threads


def test_the_state_ring_is_bounded(game):
    """Break: ignore maxlen."""
    fake = FakeGame(game)
    with session(game, fake, state_ring=5) as g:
        boot(g)
        g.wait_frames(60)
        g.check(False, "x")
    rows = _rows(game / "run" / "states-FAILED-1.jsonl")
    frames = [r["state"]["frame"] for r in rows]
    assert len(rows) == 5 and frames == sorted(frames)


def test_every_send_is_logged_with_accept_and_ack_latency(game):
    """Break: delete the finally-ledger in send(), or the accept_ms stamp in _await_ack."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.press("confirm", 2)
        g.hold("up", 10)
        g.wait_frames(12)
    rows = [r for r in _rows(game / "run" / "steps.jsonl") if r["kind"] == "step"]
    press = next(r for r in rows if r["steps"] == ["press confirm 2"])
    assert press["awaited"] and press["accept_ms"] is not None and press["ack_ms"] is not None
    assert press["ack_ms"] >= press["accept_ms"] >= 0
    assert press["frame"] is not None and press["error"] is None and press["phase"] == "run"
    hold = next(r for r in rows if r["steps"] == ["hold up 10"])
    assert hold["awaited"] is False and hold["accept_ms"] is None and hold["ack_ms"] is None
    seqs = [r["seq"] for r in rows]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)


def test_a_step_that_never_lands_is_the_row_with_no_ack(game):
    """A frozen agent never reads req.txt: the row has NO accept and NO ack, and the error names
    the timeout. Break: write the row before _await_ack without updating it."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        fake.mode = "frozen"
        with pytest.raises(HarnessError, match="not acknowledged"):
            g.send("wait 1", timeout=1.0)
        fake.mode = "normal"
    row = next(r for r in _rows(game / "run" / "steps.jsonl") if r.get("steps") == ["wait 1"])
    assert row["accept_ms"] is None and row["ack_ms"] is None
    assert "not acknowledged" in row["error"]


def test_a_refused_step_is_logged_with_its_error(game):
    """Break: remove send()'s try/except/finally."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError, match="refused"):
            g.send("flag -1 1")
    row = next(r for r in _rows(game / "run" / "steps.jsonl") if r.get("steps") == ["flag -1 1"])
    assert row["seq"] is not None and "refused" in row["error"]


def test_a_failing_step_log_does_not_fail_the_step(game, monkeypatch):
    """Break: let StepLog.append raise, or stop counting drops."""
    fake = FakeGame(game)
    monkeypatch.setattr(_art.StepLog, "append", lambda self, path, row: False)
    with session(game, fake) as g:
        boot(g)
        g.press("confirm", 2)
        dropped = g._steps_dropped
    assert dropped > 0
    rep = json.loads((game / "run" / "report.json").read_text(encoding="utf-8"))
    # >=: the teardown's own quit row is dropped too, after the number above was read.
    assert rep["steps_dropped"] >= dropped and rep["steps_recorded"] == 0


def test_a_failed_check_flushes_the_ring_before_it_photographs(game):
    """The ring's newest sample IS the check's snapshot. Break: remove the flush, move it below the
    shot (whose ack pushes newer frames in), or take the snapshot after it."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.check(True, "fine")
        assert not list((game / "run").glob("states-*.jsonl"))
        g.check(False, "bad")
        row = g.checks[-1]
    rows = _rows(game / "run" / "states-FAILED-1.jsonl")
    frames = [r["state"]["frame"] for r in rows]
    assert frames == sorted(frames) and frames[-1] == row["state"]["frame"]
    assert row["states"] == "states-FAILED-1.jsonl" and row["shot"] == "FAILED-1.png"
    assert (game / "run" / "shots" / "FAILED-1.png").exists()


def test_a_failed_check_against_a_hung_game_is_not_photographed_and_returns_fast(game):
    """A stale channel means the shot would wait out the whole ack timeout for a picture of
    nothing new. Break: remove the age > LIVE_WITHIN gate in evidence()."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        fake.mode = "frozen"
        time.sleep(2.5)
        t0 = time.time()
        g.check(False, "bad")
        elapsed = time.time() - t0
        row = g.checks[-1]
        fake.mode = "normal"
    assert elapsed < 2.0, elapsed
    assert row["shot"] is None and "stale" in row["shot_skipped"]
    assert (game / "run" / "states-FAILED-1.jsonl").exists()


def test_two_failures_on_the_same_frame_share_one_photograph(game):
    """Break: drop _last_failure_frame."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.check(False, "a")
        first = g.checks[-1]
        same = State(dict(g.channel.state().raw, frame=g._last_failure_frame), mtime=time.time())
        real = g.channel.state
        g.channel.state = lambda *a, **k: same
        try:
            g.check(False, "b")
        finally:
            g.channel.state = real
        second = g.checks[-1]
    assert first["shot"] == "FAILED-1.png"
    assert second["shot"] is None and "same frame" in second["shot_skipped"]
    assert second["states"] == "states-FAILED-2.jsonl"


def test_report_json_links_the_evidence(game):
    """Every check row says which request it followed and where its evidence is. Break: drop the
    seq stamp or the artifacts block."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.press("confirm", 2)
        g.check(False, "bad")
    rep = json.loads((game / "run" / "report.json").read_text(encoding="utf-8"))
    c = rep["checks"][0]
    steps = [r for r in _rows(game / "run" / "steps.jsonl") if r["kind"] == "step"]
    assert next(r for r in steps if r["seq"] == c["seq"])["steps"] == ["press confirm 2"]
    assert c["at"] and (game / "run" / "shots" / c["shot"]).exists()
    assert (game / "run" / c["states"]).exists()
    assert rep["artifacts"]["steps"] == "steps.jsonl"
    assert "states-FAILED-1.jsonl" in rep["artifacts"]["states"]
    assert "states-final.jsonl" in rep["artifacts"]["states"]
    checks = [r for r in _rows(game / "run" / "steps.jsonl") if r["kind"] == "check"]
    assert checks[0]["what"] == "bad" and checks[0]["shot"] == "FAILED-1.png"


def test_env_json_is_written_before_the_agent_answers_and_amended_after(game):
    """A run that dies in boot still documents the install it died against, with the DLL hashed
    before the game opened it; a run that boots adds the engine's own facts. Break: move the first
    write after _await_agent, or drop the second."""
    dll = game / "x64" / "FF9_Data" / "Managed" / "Assembly-CSharp.dll"
    dll.parent.mkdir(parents=True)
    dll.write_bytes(b"not really a dll")
    (game / "Memoria.ini").write_text('[AnalogControl]\nEnabled = 1\n[Mod]\nFolderNames = "FF9CustomMap"\n',
                                      encoding="utf-8")
    s = Session(game_path=game, run_dir=game / "run", save_dir=game / "player-saves",
                pid_probe=lambda: [], launcher=lambda exe: _dead_launcher(),
                boot_timeout=0.5, verbose=False)
    with pytest.raises(HarnessError):
        with s:
            pass
    env = json.loads((game / "run" / "env.json").read_text(encoding="utf-8"))
    assert env["engine"]["protocol"] is None and env["engine"]["boot_seconds"] is None
    assert env["engine"]["assembly_csharp"]["sha256"] == hashlib.sha256(b"not really a dll").hexdigest()
    assert env["memoria_ini"]["present"] and env["memoria_ini"]["AnalogControl"]["Enabled"] == "1"
    assert env["memoria_ini"]["mod_folders"] == ["FF9CustomMap"]
    assert env["registrations"]["FF9CustomMap"]["30810"] == "CHEST_ROOM"
    assert env["driver"]["protocol"] == PROTOCOL and env["errors"] == {}

    fake = FakeGame(game)
    s2 = Session(game_path=game, run_dir=game / "run2", save_dir=game / "player-saves",
                 pid_probe=lambda: [], launcher=lambda exe: fake.start(),
                 boot_timeout=15.0, verbose=False)
    with s2:
        pass
    env2 = json.loads((game / "run2" / "env.json").read_text(encoding="utf-8"))
    assert env2["engine"]["protocol"] == PROTOCOL
    assert env2["engine"]["boot_seconds"] is not None and env2["engine"]["first_state"]
    assert env2["window"]["requested"] == [1280, 720]


def test_env_json_tolerates_a_bare_install_and_a_missing_git(game, monkeypatch):
    """A DIRECTORY where the DLL should be, no ini, no git: every probe answers null with a named
    error where it could not look, and the run boots anyway. Break: remove any per-probe guard, or
    write a failed probe as absent."""
    (game / "x64" / "FF9_Data" / "Managed" / "Assembly-CSharp.dll").mkdir(parents=True)

    def no_git(*a, **k):
        raise OSError("no git here")

    monkeypatch.setattr(_art.subprocess, "run", no_git)
    _art._GIT_CACHE.clear()
    fake = FakeGame(game)
    try:
        with session(game, fake, repo_root=game) as g:
            boot(g)
    finally:
        _art._GIT_CACHE.clear()
    env = json.loads((game / "run" / "env.json").read_text(encoding="utf-8"))
    assert env["memoria_ini"]["present"] is False
    assert env["engine"]["assembly_csharp"]["sha256"] is None
    assert env["engine"]["assembly_csharp"]["exists"] is False
    assert env["driver"]["git_head"] is None and "git_head" in env["errors"]


def test_env_json_never_fails_the_run(game, monkeypatch):
    """Break: remove the guard in write_env."""
    def boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(_sess, "build_env", boom)
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.check(True, "x")
    assert not (game / "run" / "env.json").exists()
    assert (game / "run" / "report.json").exists()
    assert not g.channel.armed


def test_under_a_suite_env_json_lists_the_manifest_and_every_member(game):
    """Break: drop write_env(suite=) in run(), or meta['manifest'] in load_manifest."""
    fake = FakeGame(game)
    rel = _scenario(game, "m1", "def run(g):\n    g.newgame(settle=0)\n    g.check(True, 'ok')\n")
    path = _manifest(game, f'[suite]\nname="t"\nfield=30810\n\n[[scenario]]\npath="{rel}"\n'
                           f'deploy="x/y.toml"\n')
    with session(game, fake) as g:
        meta, scenarios = load_manifest(path, game)
        SuiteRunner(g, scenarios, meta=meta, verbose=False).run()
    env = json.loads((game / "run" / "env.json").read_text(encoding="utf-8"))
    assert env["suite"]["name"] == "t" and env["suite"]["manifest"] == str(path)
    assert env["suite"]["scenarios"] == [{"index": 1, "label": "m1", "path": str(scenarios[0].path),
                                          "field": 30810, "deploy": "x/y.toml"}]
    assert env["driver"]["protocol"] == PROTOCOL            # the merge kept the non-suite keys


def test_suite_artifacts_land_in_the_members_own_directory(game):
    """A member's steps -- INCLUDING its baseline ladder -- its check rows and its rings live under
    <run>/<NN>-<label>/; the run-level ledger keeps the whole timeline and the quit row. Break:
    drop bind_artifacts from _run_one (the ladder lands under the previous member), or
    unbind_artifacts from run() (the quit row lands under the last one)."""
    fake = FakeGame(game)
    a = _scenario(game, "first", "def run(g):\n    g.newgame(settle=0)\n    g.check(True, 'ok')\n")
    b = _scenario(game, "second",
                  "def run(g):\n    g.newgame(settle=0)\n    g.press('confirm', 2)\n    g.check(False, 'bad')\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{a}"\n\n[[scenario]]\npath="{b}"\n')
    with session(game, fake) as g:
        meta, scenarios = load_manifest(path, game)
        runner = SuiteRunner(g, scenarios, meta=meta, verbose=False)
        results = runner.run()
        run_dir = runner.run_dir
    d2 = run_dir / "02-second"
    rows = _rows(d2 / "steps.jsonl")
    assert rows and all(r.get("scenario") == "02-second" for r in rows)
    assert any(r.get("phase") == "baseline" for r in rows if r["kind"] == "step")
    assert any(r["kind"] == "check" and r["what"] == "bad" for r in rows)
    assert (d2 / "states-FAILED-1.jsonl").exists()
    assert not list((run_dir / "01-first").glob("states-*.jsonl"))
    assert results[1]["states"] == ["states-FAILED-1.jsonl"] and results[1]["steps_recorded"] == len(rows)
    top = _rows(run_dir / "steps.jsonl")
    assert {r.get("scenario") for r in top} >= {"01-first", "02-second", None}
    assert any(r.get("steps") == ["quit"] and r.get("scenario") is None for r in top)
    assert (run_dir / "states-final.jsonl").exists()


def test_a_raise_out_of_a_scenario_flushes_the_ring_before_the_ladder_runs(game):
    """The ring is the game as it was WHEN the scenario raised -- not after the next member's
    ladder rolled the moment out. Break: move the flush after _collect or below restore_baseline."""
    fake = FakeGame(game)
    rel = _scenario(game, "boom", "from harness import HarnessError\n"
                                  "def run(g):\n    g.newgame(settle=0)\n    raise HarnessError('kaboom')\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{rel}"\n')
    with session(game, fake) as g:
        meta, scenarios = load_manifest(path, game)
        runner = SuiteRunner(g, scenarios, meta=meta, verbose=False)
        results = runner.run()
        run_dir = runner.run_dir
    assert results[0]["verdict"] == "error"
    rows = _rows(run_dir / "01-boom" / "states-ERROR.jsonl")
    assert rows and rows[-1]["state"]["ui_state"] == "FieldHUD"
    assert results[0]["capture"]["shot"] == "01-boom-ERROR.png"
    assert (run_dir / "01-boom" / "shots" / "01-boom-ERROR.png").exists()


def test_a_poisoned_scenario_flushes_the_states_the_ladder_could_not_restore(game):
    """begin_scenario never ran, and the member still has its evidence: the ladder's own steps and
    the ring of the game it could not clean up. Break: bind_artifacts below restore_baseline."""
    fake = FakeGame(game)
    fake.soft_reset_enabled = False
    rel = _scenario(game, "never_runs", "def run(g):\n    g.check(True, 'ran')\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{rel}"\n')
    with session(game, fake) as g:
        boot(g)
        meta, scenarios = load_manifest(path, game)
        runner = SuiteRunner(g, scenarios, meta=meta, verbose=False)
        results = runner.run()
        run_dir = runner.run_dir
    assert results[0]["verdict"] == "poisoned"
    assert results[0]["states"] == ["states-POISONED.jsonl"]
    assert (run_dir / "01-never_runs" / "states-POISONED.jsonl").exists()
    rows = _rows(run_dir / "01-never_runs" / "steps.jsonl")
    assert rows and all(r.get("phase") == "baseline" for r in rows if r["kind"] == "step")


def test_a_non_pass_member_always_leaves_a_ring(game):
    """A proved-nothing member is the one verdict that would otherwise have nothing to read.
    Break: drop the verdict != pass rule in _run_one."""
    fake = FakeGame(game)
    nothing = _scenario(game, "nothing", "def run(g):\n    g.newgame(settle=0)\n")
    passes = _scenario(game, "passes", "def run(g):\n    g.newgame(settle=0)\n    g.check(True, 'ok')\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{nothing}"\n\n'
                           f'[[scenario]]\npath="{passes}"\n')
    with session(game, fake) as g:
        meta, scenarios = load_manifest(path, game)
        runner = SuiteRunner(g, scenarios, meta=meta, verbose=False)
        results = runner.run()
        run_dir = runner.run_dir
    assert [r["verdict"] for r in results] == ["proved-nothing", "pass"]
    assert (run_dir / "01-nothing" / "states-END.jsonl").exists()
    assert not list((run_dir / "02-passes").glob("states-*.jsonl"))


def test_a_dead_game_does_not_stall_the_error_capture(game):
    """A raise against a game that has exited must not spend the shot timeout on it. Break: remove
    the exited-process gate in evidence()."""
    fake = FakeGame(game)
    rel = _scenario(game, "dies", "def run(g):\n    g.newgame(settle=0)\n"
                                  "    g.proc.returncode = 3\n    raise RuntimeError('the game died')\n")
    path = _manifest(game, f'[suite]\nname="t"\n\n[[scenario]]\npath="{rel}"\n')
    with session(game, fake) as g:
        meta, scenarios = load_manifest(path, game)
        runner = SuiteRunner(g, scenarios, meta=meta, verbose=False)
        t0 = time.time()
        results = runner.run()
        elapsed = time.time() - t0
    assert results[0]["verdict"] == "error"
    assert results[0]["capture"]["shot"] is None and "exited" in results[0]["capture"]["shot_skipped"]
    assert results[0]["capture"]["states"] == "states-ERROR.jsonl"
    assert elapsed < 5.0, elapsed


def test_the_ring_is_flushed_at_stop_and_a_failing_flush_never_skips_the_disarm(game, monkeypatch):
    """states-final.jsonl is the game BEFORE quit (state-final.json is after); and the flush sits in
    the teardown ladder, so a disk that refuses it cannot leave the shared install armed. Break:
    drop the ladder step (a), or move the flush above the disarm outside the per-step try (b)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.wait_frames(10)
    rows = _rows(game / "run" / "states-final.jsonl")
    frames = [r["state"]["frame"] for r in rows]
    assert rows and frames == sorted(frames) and all(r["state"]["armed"] for r in rows)
    final = json.loads((game / "run" / "state-final.json").read_text(encoding="utf-8-sig"))
    assert frames[-1] <= final["frame"]

    def refuse(self, tag):
        raise OSError("disk full")

    monkeypatch.setattr(Session, "flush_states", refuse)
    fake2 = FakeGame(game)
    s = Session(game_path=game, run_dir=game / "run2", save_dir=game / "player-saves",
                pid_probe=lambda: [], launcher=lambda exe: fake2.start(), boot_timeout=15.0,
                verbose=False)
    s.start()
    s.stop(failed=True)
    assert not s.channel.armed
    assert (game / "run2" / "report.json").exists()
