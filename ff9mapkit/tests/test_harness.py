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
import math
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


# --------------------------------------------------------------------------- watch_cutscene(choices="default")
# The rung-3 tour stopped on Garnet's choice in the 354 weapon shop ("You changed the way you talk!"): the waiter
# presses Confirm through boxes and stops at a choice, and the scene waited on it for 240 s. The opt-in answers
# with the option the GAME's cursor rests on -- once the window is ready: before that the agent publishes the
# group as '' and whatever cursor the pooled window last held (recorded at 30937 and 30921; the fake's scene()).

_TALK = "Zidane\n“You changed the way you talk!”"
_ANSWERS = ["You’re doing great!", "You still sound funny, though"]


def test_watch_cutscene_takes_the_games_default_choice_and_plays_the_scene_out(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        # the cursor rests on option 1; for longer than the waiter's hold the opening window reads a stale 0.
        # Then a second choice straight after the first -- one masked line, the default past it.
        mark = len(fake.executed)
        fake.scene("Garnet\n“Zidane!”", {"header": _TALK, "options": _ANSWERS, "default": 1},
                   {"header": "Well?", "options": ["Sword", "Dagger", "Nothing"], "disabled": [0], "default": 2},
                   "Garnet\n“Hmph.”", stale=0, opening=360)
        pages = g.watch_cutscene(timeout=30, choices="default")
        seen = [raw for _t, _age, raw in g._ring._buf
                if (raw["dialog"].get("choice") or {}).get("options", [""])[0] == _TALK]
        assert any(r["dialog"]["choice"]["selected"] == 0 and r["menu"]["group"] == "" for r in seen), \
            "premise: the waiter never saw the opening window's stale cursor"
        early = [s for s in fake.executed[mark:fake.readied[0]] if s[0] == "press"]
        assert early == [["press", "confirm", "3"]], f"pressed at a window not yet taking answers: {early}"
        assert fake.answered == [1, 2], fake.answered
        assert [(c["index"], c["text"]) for c in pages.choices] == [(1, _ANSWERS[1]), (2, "Nothing")], pages.choices
        assert pages.choices[0]["prompt"] == _TALK and pages.choices[0]["field"] == 30820
        assert isinstance(pages, list) and pages[0] == "Garnet\n“Zidane!”" and pages[-1] == "Garnet\n“Hmph.”"
        assert g.state.control and not g.state.dialog_open


def test_accept_name_keeps_the_default_name_and_no_confirm_falls_through(game):
    """Menu(1,0): the box opens focused, so it takes two Confirms -- and none may land on the page after it."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        fake.scene({"naming": 0}, "Zidane\n“It's me, Zidane!”")
        published(g, lambda s: s.ui_state == "NameSetting")
        mark = len(fake.executed)
        st = g.accept_name(timeout=10)
        confirms = [s for s in fake.executed[mark:] if s[:2] == ["press", "confirm"]]
        assert fake.named == [0] and st.ui_state == "FieldHUD", (fake.named, st.ui_state)
        assert len(confirms) == 2, confirms
        assert published(g, lambda s: s.dialog_open).texts[0].startswith("Zidane"), "the next page was turned"


def test_accept_name_raises_when_no_naming_screen_opens(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        with pytest.raises(HarnessError, match="the naming screen"):
            g.accept_name(timeout=1.0)
        assert fake.named == []


def test_without_the_opt_in_the_waiter_still_stops_at_a_choice(game):
    """The control: no ``choices``, the old waiter -- it turns the page, never presses at the choice, and says so
    when it times out."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        mark = len(fake.executed)
        fake.scene("Garnet\n“Zidane!”", {"header": _TALK, "options": _ANSWERS, "default": 1})
        with pytest.raises(HarnessError, match="CHOICE is open"):
            g.watch_cutscene(timeout=3)
        confirms = [s for s in fake.executed[mark:] if s[:2] == ["press", "confirm"]]
        assert len(confirms) == 1 and fake.answered == [] and fake.choice is not None, (confirms, fake.answered)
        with pytest.raises(HarnessError, match="only policy"):
            g.watch_cutscene(timeout=3, choices="first")          # no preference of ours, ever


def test_a_default_on_a_disabled_line_is_refused_not_replaced(game):
    """The script's mask can leave the cursor's own line out; there is then no game default, and taking another
    option would be the harness choosing."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        fake.scene({"header": "Well?", "options": ["Sword", "Dagger", "Nothing"], "disabled": [1], "default": 1})
        with pytest.raises(HarnessError, match="disabled"):
            g.watch_cutscene(timeout=10, choices="default")
        assert fake.answered == []


def test_a_choice_whose_prompt_is_still_typing_is_confirmed_again_not_waited_out(game):
    """The engine readies a choice -- its group and default cursor -- while the prompt still TYPES (DialogAnimator
    sets TextAnimation, then AfterShown -> InitializeChoice), and a Confirm then only finishes the text
    (Dialog.OnKeyConfirm's TextAnimation branch). A window still waiting, unchanged, CHOICE_CONFIRM_FRAMES after a
    Confirm gets another at once -- not the 5 s wait for the window to close plus a re-arm (over 6 s a choice)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        fake.scene({"header": _TALK, "options": _ANSWERS, "default": 1, "typing": 10 ** 6}, "Garnet\n“Hmph.”")
        t0 = time.time()
        pages = g.watch_cutscene(timeout=30, choices="default")
        spent = time.time() - t0
        assert fake.answered == [1] and [c["index"] for c in pages.choices] == [1], (fake.answered, pages.choices)
        confirms = [s for s in fake.executed[fake.readied[0]:] if s[:2] == ["press", "confirm"]]
        assert len(confirms) == 3, confirms           # finish the text, answer, turn the last page
        assert spent < 4.5, f"sat out the Confirm that only finished the text: {spent:.1f}s"


def test_a_question_asked_again_after_its_default_is_named_as_a_loop(game):
    """A script whose default answer asks the same question again: answered CHOICE_REPEATS times, then the waiter
    says what it is -- instead of pressing Confirm every second and a half until its timeout ran out."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        again = {"header": "Leave the shop?", "options": ["No", "Yes"], "default": 0}
        fake.scene(*[again] * 6)
        t0 = time.time()
        with pytest.raises(HarnessError, match="again after 3 default answers"):
            g.watch_cutscene(timeout=60, choices="default")
        assert fake.answered == [0, 0, 0], fake.answered
        assert time.time() - t0 < 30


def test_a_choice_left_unanswered_under_the_opt_in_is_named_when_the_waiter_times_out(game):
    """The timeout says a choice is open with or without ``choices``: here one that never becomes ready."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        fake.scene({"header": _TALK, "options": _ANSWERS, "default": 1}, opening=10 ** 6)
        with pytest.raises(HarnessError, match="CHOICE is still open, unanswered"):
            g.watch_cutscene(timeout=3, choices="default")
        assert fake.answered == []


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


def test_fight_closes_the_battle_tutorial_then_plays_the_fight_out(game):
    """Scene 336 (the Masked Man) opens the tutorial screen before the first command, and no command menu opens
    while it is up. The control: with the screen up and nothing pressed, no turn is ever offered."""
    fake = FakeGame(game)
    fake.enemy_hit = 0
    fake.tutorial_scenes = {336}
    fake.atb_gain = 400
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        g.start_battle(336)
        published(g, lambda s: s.ui_state == "Tutorial")
        g.wait_frames(fake.battle_intro_frames + 60)
        assert g.state.turn_slot < 0 and not fake.battle_commands, "premise: the tutorial screen withholds turns"
        assert g.fight(timeout=60.0, finish=False) == 1
        assert not fake._tutorial and len(fake.battle_commands) >= 4


def test_fight_reads_again_when_its_step_lands_after_the_hud_stopped_asking(game):
    """story-o1e run 1: the sample said "asking slot N", the step landed after the Masked Man's scripted end had
    turned the HUD off, and the agent refused it -- fight() raised and the run went VOID. It is not a turn and not a
    failure: fight() reads the state again. Any OTHER refusal still raises (the control)."""
    from harness.channel import StepRefused
    for text, raises in (("menus: the battle is not asking for commands yet (the intro is still running, or the "
                          "fight is already over). Wait for turn.enabled.", False),
                         ("battlecmd: no such command", True)):
        fake = FakeGame(game)
        fake.enemy_hit = 0
        g = _fighting(game, fake)
        try:
            real, calls = g.act, []

            def act(*a, **kw):
                calls.append(1)
                if len(calls) == 1:
                    raise StepRefused(text, ["menus 0"])
                return real(*a, **kw)
            g.act = act
            if raises:
                with pytest.raises(StepRefused):
                    g.fight(timeout=60.0, finish=False)
            else:
                assert g.fight(timeout=60.0, finish=False) == 1
                assert g.last_fight["turns"] == len(calls) - 1, (g.last_fight, len(calls))
        finally:
            g.__exit__(None, None, None)


def test_battle_act_closes_the_battle_tutorial_before_its_command(game):
    fake = FakeGame(game)
    fake.enemy_hit = 0
    fake.tutorial_scenes = {336}
    fake.atb_gain = 400
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        g.start_battle(336)
        published(g, lambda s: s.ui_state == "Tutorial")
        assert g.battle_act("Attack", timeout=30.0)
        assert not fake._tutorial and fake.battle_commands


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
    # an exaggerated tail, to make the window visible: long enough (half a second of the fake's loop) that the read
    # right after the ack still lands inside it on a loaded machine -- at 8 frames a slow read missed it (the premise
    # assert below) in suite runs beside other agents' runs
    fake.coast_frames = 30
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

    The rule is now asked in FRAMES and a GAIT, judged at the measured rate (Session.rate: here the
    calibrated 60 fps): at least PROBE_MIN_FRACTION of the burst's average travel, at most the frames'
    field ticks at the spread's slow end -- UNROUNDED -- at the gait's calls a tick, and one run tick of
    tail. At 60 fps that is the old window at EVERY count (HEAD's pins, in frames: the recorded 114u on
    one run frame is still too much, 60u on one run frame still normal); at 31 fps a frame carries a
    whole tick, and a 31-frame run's 1020u is evidence there, as it was not at 60.

    ⚠ Tested here rather than through walk_to on purpose. Reproducing these numbers through a
    simulated walk depends on where the stand-in character happens to be, and three attempts at
    that passed against a deliberately broken build -- proving nothing while looking thorough."""
    from harness import tickrate as T
    fake = FakeGame(game)
    with session(game, fake) as g:
        # TOO MUCH: 114 units on one run frame (30 commanded). The tail of the previous burst.
        assert not g._burst_is_evidence(114.0, 1, "run")
        assert not g._burst_is_evidence(114.0, 1, "walk")
        # TOO LITTLE: 24 units on 45 run frames (1350 commanded). Pressed into a wall.
        assert not g._burst_is_evidence(24.0, 45, "run")
        # Below the floor entirely -- a nudge, not a move.
        assert not g._burst_is_evidence(4.0, 30, "run")

        # A GENUINELY WRONG BASIS still gets judged: the character walks freely, so he covers very
        # nearly what was commanded. This is the case the guard exists for and must keep catching.
        assert g._burst_is_evidence(1150.0, 40, "run")
        assert g._burst_is_evidence(900.0, 31, "run")
        # And the +/-1 frame the engine actually varies by (measured on 30801) stays evidence.
        assert g._burst_is_evidence(60.0, 1, "run"), "run f=1 covers 60u; that is normal, not a tail"
        assert g._burst_is_evidence(450.0, 31, "walk")
        # At every count the old ceiling exactly, odd ones included: 30N + 60 run, 15N + 60 walked.
        for n in range(1, 40):
            for gait, per in (("run", 30.0), ("walk", 15.0)):
                assert g._burst_is_evidence(per * n + 60.0, n, gait), (n, gait)
                assert not g._burst_is_evidence(per * n + 61.0, n, gait), (n, gait)

        # At 31 fps a run frame carries ~58u, not 30: 1020u on 31 run frames is a burst's own there.
        r31 = T.Rate(31.2, 30.6, 31.8, source="mtime", samples=24, frame=900)
        assert not g._burst_is_evidence(1020.0, 31, "run")
        assert g._burst_is_evidence(1020.0, 31, "run", r31) and g._burst_is_evidence(114.0, 1, "run", r31)
        assert not g._burst_is_evidence(180.0, 1, "run", r31)


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


@pytest.mark.parametrize("smooth", [False, True])
def test_route_to_goes_round_a_gateway_the_straight_walk_takes(game, smooth):
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
        rec = g.route_to(400.0, 0.0, avoid=[door], walkmesh=_flat_bgi(), prior=_prior(), smooth=smooth)
        assert rec["landed"] is None and rec["reached"], rec
        assert len(rec["waypoints"]) > 1 and not fake.fired, (rec, fake.fired)
        assert g.state.field_id == 30820
        # ...and the control: the one-axis walk back takes the door
        g.walk_to(-400.0, 0.0, strict=False)
        assert fake.fired and fake.fired[0]["to"] == 30821


@pytest.mark.parametrize("smooth", [False, True])
def test_route_cross_from_an_arrival_beside_the_door_takes_the_exit_it_was_sent_to(game, smooth):
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
        rec = g.route_cross(goal[0], goal[1], avoid=[door_a], walkmesh=wm, prior=_prior(), expect=30810,
                            smooth=smooth)
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


@pytest.mark.parametrize("smooth", [False, True])
def test_route_to_unstick_waits_out_a_freeze_with_control_held(game, smooth):
    """A freeze that outlasts the stall check and ends inside one wait: the walk goes on from where it stood,
    and neither a push nor a blocker goes in -- nobody was there."""
    fake = FakeGame(game)
    fake.freezes = {30820: [{"zone": _BAND, "frames": 360}]}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -400, 0)
        g.ROUTE_WAIT_SECONDS = 8.0                     # one wait covers the freeze, whatever the stall check took
        rec = g.route_to(400.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), unstick=True, smooth=smooth)
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
        waits = [s for s in fake.executed[mark:] if s[0] == "wait" and int(s[1]) == g._frames_lasting(g.ROUTE_WAIT_SECONDS)]
        assert not waits, waits
        long_holds = [s for s in fake.executed[mark:] if s[0] == "hold" and int(s[2]) > 20]
        assert not long_holds, long_holds


@pytest.mark.parametrize("smooth", [False, True])
def test_route_to_unstick_gives_up_cleanly_on_a_freeze_that_never_lifts(game, smooth):
    """No hang, bounded waits and pushes, and no phantoms: each stall reads as a body ahead and each replan
    presses a way the ones before it left open, and he never moves -- so they were no bodies. Withdrawn, from
    the record and from the visit."""
    fake = FakeGame(game)
    fake.freezes = {30820: [{"zone": _BAND, "frames": None}]}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -400, 0)
        g.ROUTE_WAIT_SECONDS = 0.5
        t0 = time.time()
        rec = g.route_to(400.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), unstick=True, smooth=smooth)
        assert time.time() - t0 < 60, "a freeze that never lifts must end the call, not hang it"
        assert rec["frozen"] and not rec["reached"] and rec["landed"] is None and rec["during"] is None, rec
        assert 1 <= rec["waits"] <= g.ROUTE_WAIT_BUDGET, rec
        assert 1 <= rec["pushes"] <= g.ROUTE_PUSH_BUDGET and rec["pushed"] == 0, rec
        assert rec["blockers"] == [] and not rec["blocked"], rec
        assert g._blockers[1] == [], "a blocker read off a freeze must not outlive the call"
        assert g.state.control and g.state.field_id == 30820


@pytest.mark.parametrize("smooth", [False, True])
def test_a_freeze_in_a_narrow_lane_is_not_read_as_a_sealed_way(game, smooth):
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
        g.ROUTE_WAIT_SECONDS = 0.5
        rec = g.route_to(400.0, 0.0, walkmesh=_flat_bgi(*_LANE), prior=_prior(), unstick=True, smooth=smooth)
        assert rec["frozen"] and not rec["blocked"] and rec["blockers"] == [], rec
        assert g._blockers[1] == [], g._blockers


@pytest.mark.parametrize("smooth", [False, True])
def test_route_to_unstick_pushes_through_a_passable_body_without_placing_a_blocker(game, smooth):
    """THE 350 VILLAGER, as the engine has it: someone standing on the line pressed, without object flag 16.
    Without the flag the bursts stall against him forever; with it the waits go first (he might walk off), then
    one unbroken hold takes him through -- no blocker, no detour, nothing remembered. (Smooth, a hold that
    presses him for the whole lock goes through on its own; these are shorter, so the same rungs run.)"""
    fake = FakeGame(game)
    fake.blockers = {30820: [(0.0, 0.0, 152.0)]}       # 350's NPCs: SetObjectLogicalSize(14, 14, 22), flags 5/7/1
    wm = _flat_bgi()
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -400, 0)
        g.ROUTE_WAIT_SECONDS = 0.5
        old = g.route_to(400.0, 0.0, walkmesh=wm, prior=_prior(), smooth=smooth)
        assert not old["reached"] and abs(g.state.player_x + 152) < 2, (old, g.state.pos)     # the premise
        rec = g.route_to(400.0, 0.0, walkmesh=wm, prior=_prior(), unstick=True, smooth=smooth)
        assert rec["reached"] and not rec["frozen"] and not rec["blocked"], rec
        assert rec["waits"] == g.ROUTE_WAITS and rec["pushes"] == 1 and rec["pushed"] == 1, rec
        assert rec["blockers"] == [] and g._blockers[1] == [], rec


@pytest.mark.parametrize("smooth", [False, True])
def test_route_to_unstick_routes_round_a_solid_body_and_remembers_it_for_the_visit(game, smooth):
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
        g.ROUTE_WAIT_SECONDS = 0.5                     # a body does not walk off in a test; keep the waits short
        old = g.route_to(400.0, 0.0, walkmesh=wm, prior=_prior(), smooth=smooth)
        assert not old["reached"] and old["replans"] == g.ROUTE_REPLANS, old     # the premise
        assert abs(g.state.player_x + 192) < 2, g.state.pos                    # stopped dead against it
        rec = g.route_to(400.0, 0.0, walkmesh=wm, prior=_prior(), unstick=True, smooth=smooth)
        assert rec["reached"], rec
        assert len(rec["blockers"]) >= 1 and rec["waits"] >= g.ROUTE_WAITS and rec["cleared"] == 0, rec
        assert rec["pushes"] >= 1 and rec["pushed"] == 0, rec
        bx, bz = rec["blockers"][0]
        assert abs(bx - 1) <= 2 and abs(bz) <= 2, "placed on the line pressed, at the collision distance"
        assert g._blockers[0] == 30820 and g._blockers[1]
        back = g.route_to(-400.0, 0.0, walkmesh=wm, prior=_prior(), unstick=True, smooth=smooth)
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


@pytest.mark.parametrize("smooth", [False, True])
def test_route_to_unstick_reads_a_wedge_as_bodies_not_a_freeze(game, smooth):
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
        g.ROUTE_WAIT_SECONDS = 0.5
        rec = g.route_to(400.0, 400.0, walkmesh=_flat_bgi(), prior=_prior(), unstick=True, smooth=smooth)
        assert rec["reached"] and not rec["frozen"], rec
        assert len(rec["blockers"]) >= 2, rec


@pytest.mark.parametrize("smooth", [False, True])
def test_a_way_sealed_after_he_moved_is_blocked_and_leaves_no_phantom(game, smooth):
    """``blocked`` -- the REAL strike -- needs him to have MOVED since the call's first blocker: round one solid
    body in the wide room, then another sealing the 300-wide corridor. And even then the call's blockers are
    withdrawn from the visit: a phantom never outlives the call that could not use it.

    Smooth, the corridor's body is wider: 152 seals the 300-wide lane only against one-axis bursts. One long hold
    is pushed round its front, slides to the lane's edge and grazes past its side, where its centre is BEHIND him
    and the engine pushes nobody out (the fake's +-90 degree rule) -- so there it would be no seal at all."""
    fake = FakeGame(game)
    fake.walkmesh = _ROOM_AND_LANE
    fake.blockers = {30820: [(-700.0, 0.0, 192.0, True), (300.0, 0.0, 192.0 if smooth else 152.0, True)]}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -1000, 0)
        g.ROUTE_WAIT_SECONDS = 0.5
        rec = g.route_to(1000.0, 0.0, walkmesh=_l_bgi(), prior=_prior(), unstick=True, smooth=smooth)
        assert rec["blocked"] and not rec["frozen"] and not rec["reached"], rec
        assert len(rec["blockers"]) >= 2 and g.state.player_x > 0, (rec, g.state.pos)   # it got into the corridor
        assert g._blockers[1] == [], g._blockers


@pytest.mark.parametrize("smooth", [False, True])
@pytest.mark.parametrize("off, solid", [(10, True), (30, True), (60, True), (30, False)])
def test_route_to_unstick_reads_a_slide_round_a_body_as_a_stall_not_a_bad_basis(game, off, solid, smooth):
    """A body a little off the pressed line: the engine pushes him out along the line from its centre, so he
    slides SIDEWAYS -- which walk_to's basis check reads as a wrong basis, raising and throwing the basis away.
    Under unstick the slide is a stall like any other: no raise, the basis kept, the goal reached. (The control
    is the chunked walk's: a smooth hold runs free before it meets the body, so the slide round it is a minor
    part of the hold's displacement and not read as a basis at all.)"""
    body = (0.0, float(off), 192.0, True) if solid else (0.0, float(off), 152.0)
    fake = FakeGame(game)
    fake.blockers = {30820: [body]}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -400, 0)
        g.ROUTE_WAIT_SECONDS = 0.5
        if off == 30 and solid and not smooth:         # the control: the old verb still raises (and pops)
            with pytest.raises(HarnessError, match="disagrees"):
                g.route_to(400.0, 0.0, walkmesh=_flat_bgi(), prior=_prior())
            assert 30820 not in g._axes
            _stand(g, fake, -400, 0)
        rec = g.route_to(400.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), unstick=True, smooth=smooth)
        assert rec["reached"], rec
        assert 30820 in g._axes


@pytest.mark.parametrize("smooth", [False, True])
def test_route_cross_with_its_zone_says_where_the_walk_ended(game, smooth):
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
        g.ROUTE_WAIT_SECONDS = 0.5
        goal = pathfind.region_goal(wm, door)
        waited = []
        crossing = g.expect_field_change
        g.expect_field_change = lambda **kw: waited.append(kw["timeout"]) or crossing(**kw)
        rec = g.route_cross(goal[0], goal[1], walkmesh=wm, prior=_prior(), unstick=True, zone=door, timeout=20,
                            smooth=smooth)
        assert rec["landed"] is None and rec["inside"] is False and not fake.fired, rec
        assert waited == [], "waited out a crossing that could not come"
        fake.blockers = {}
        fake.regions = {}                              # the zone is there; the gateway is story-gated shut
        rec = g.route_cross(goal[0], goal[1], walkmesh=wm, prior=_prior(), unstick=True, zone=door, timeout=2,
                            smooth=smooth)
        assert rec["landed"] is None and rec["inside"] is True and waited == [2], (rec, waited)
        rec = g.route_cross(-400.0, 0.0, walkmesh=wm, prior=_prior(), unstick=True, timeout=2, smooth=smooth)
        assert rec["inside"] is None and waited == [2, 2], "no zone: no verdict, and the wait as it was"


@pytest.mark.parametrize("smooth", [False, True])
def test_a_blocker_replan_never_enters_an_avoided_zone(game, smooth):
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
        g.ROUTE_WAIT_SECONDS = 0.5
        rec = g.route_to(400.0, 0.0, avoid=[door], walkmesh=wm, prior=_prior(), unstick=True, smooth=smooth)
        assert rec["blockers"], f"premise: the walk never met the body ({rec})"
        assert not fake.fired, fake.fired
        assert rec["landed"] is None and g.state.field_id == 30820 and rec["reached"], rec


# --------------------------------------------------------------------------- route_to(smooth=True)
# The owner, watching the rung-3 tour: "the movement is non-continuous/choppy but it works". route_to walked every
# leg in chunks of one-axis walk_to bursts with a settle after each. ``smooth`` walks a leg as one continuous hold
# toward its waypoint -- two directions at once where it runs diagonal on the calibrated basis -- re-aimed only
# when a hold ends. What must not change: no hold ever carries him into a region he was not sent to.


def _yawed(deg):
    """The fake's key basis under ``twist=deg`` (FakeGame._step_world's rotation): up and right in world."""
    a = math.radians(deg)
    return {"v": (-math.sin(a), math.cos(a)), "h": (math.cos(a), math.sin(a))}


def _counting(g):
    """Every request ``g`` sends from now on, as its tuple of steps."""
    sent, send = [], g.send
    g.send = lambda *steps, **kw: (sent.append(steps), send(*steps, **kw))[1]
    return sent


def _diagonal(steps) -> bool:
    return len({s.split()[1] for s in steps if s.startswith("hold ")} - {"cancel"}) == 2


def test_a_smooth_route_holds_whole_legs_in_fewer_requests(game):
    """A yawed room, a door band across the straight line: both walks go round it and stay out -- the smooth one
    in a fraction of the requests, pressing two directions at once on its diagonal legs (the chunked walk never
    does)."""
    door = _rect(-100, -300, 100, 300)
    fake = FakeGame(game, twist=17.0)
    fake.regions = {30820: [{"zone": door, "to": 30821, "arrive": (0, 0)}]}
    fake.exit_frames = 30
    prior = _yawed(17.0)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -450, -150)
        g.calibrate_axes(hazards=[door], prior=prior)       # one measured basis for both walks
        sent = _counting(g)
        spent = {}
        for smooth in (False, True):
            _stand(g, fake, -450, -150)
            sent.clear()
            rec = g.route_to(450.0, 200.0, avoid=[door], walkmesh=_flat_bgi(), prior=prior, smooth=smooth)
            assert rec["reached"] and rec["landed"] is None and len(rec["waypoints"]) > 1, (smooth, rec)
            spent[smooth] = len(sent)
            assert any(_diagonal(s) for s in sent) == smooth, (smooth, sent)
        assert not fake.fired, fake.fired
        print(f"synthetic requests: chunked {spent[False]}, smooth {spent[True]}")
        assert spent[True] <= 0.6 * spent[False], spent


def test_a_hold_whose_pad_direction_would_run_into_a_region_is_cut_short(game):
    """The leg keeps its margin from a door below it; the pad direction nearest the leg does not. From
    (-800, -500) the goal (700, 0) bears 18 degrees off 'right', and 'right' held down the leg runs straight
    through the door (the premise). The smooth walk presses 'right' -- and cuts it short, well before the door
    (the drift from the leg, and PROBE_HAZARD_PAD from the door, each bound it) -- then re-aims. Nothing fires."""
    from ff9mapkit.content import pathfind
    door = _rect(-300, -620, 100, -470)
    room = (-1000, -1000, 1000, 1000)
    assert pathfind.seg_poly_gap((-800, -500), (700, 0), door) >= pathfind.KEEPOUT_MARGIN_W     # the leg: clear
    assert pathfind.seg_poly_gap((-800, -500), (700, -500), door) < 0                           # 'right': not
    fake = FakeGame(game, walkmesh=room)
    fake.regions = {30820: [{"zone": door, "to": 30821, "arrive": (0, 0)}]}
    fake.exit_frames = 30
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -800, 0)
        g.calibrate_axes(hazards=[door], prior=_prior())
        _stand(g, fake, -800, -500)
        sent = _counting(g)
        rec = g.route_to(700.0, 0.0, avoid=[door], walkmesh=_flat_bgi(*room), prior=_prior(), smooth=True)
        assert rec["reached"] and rec["landed"] is None and not fake.fired, (rec, fake.fired)
        assert rec["waypoints"] == [[700, 0]], rec                      # one leg: the straight line
        first = sent[0]
        assert [s.split()[:2] for s in first if s.startswith("hold ")] == [["hold", "right"]], first
        frames = int(first[0].split()[2])
        assert g.rate().reach(frames, "run") < 500 - g.PROBE_HAZARD_PAD, first  # short of the door


@pytest.mark.parametrize("err", [3.0, 6.3])
def test_a_smooth_hold_is_planned_for_the_heading_error_of_its_basis(game, err):
    """A basis measured a few degrees off the game's -- in-game, 352's up one-sided 6.3 degrees off a prior that had
    it exactly -- and a leg running 60u beside a door. Planned as if the measured direction were exact, the first
    hold runs 45 frames down the leg and its true line drifts into the door (the control). Planned for every heading
    within the basis's disagreement with its prior, plus ROUTE_HEADING_FLOOR, the holds end short of that and
    re-aim: nothing fires."""
    from ff9mapkit.content import pathfind
    room = (-3000, -1000, 3000, 1000)
    door = _rect(-1400, 60, -1000, 400)
    assert pathfind.seg_poly_gap((-2500, 0), (2500, 0), door) >= pathfind.KEEPOUT_MARGIN_W     # the leg: clear
    fake = FakeGame(game, walkmesh=room, twist=err)          # the game's right is err degrees toward +z
    fake.regions = {30820: [{"zone": door, "to": 30821, "arrive": (0, 0)}]}
    fake.exit_frames = 30
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -2500, 0)
        g._axes[30820] = _prior()                            # measured: err degrees off the game's
        rec = g.route_to(2500.0, 0.0, avoid=[door], walkmesh=_flat_bgi(*room), prior=_yawed(err), smooth=True)
        assert rec["reached"] and rec["landed"] is None and not fake.fired, (rec, fake.fired)
        _stand(g, fake, -2500, 0)
        g._heading_spread = lambda basis, prior: 0.0         # the control: the measured direction taken as exact
        rec = g.route_to(2500.0, 0.0, avoid=[door], walkmesh=_flat_bgi(*room), prior=_yawed(err), smooth=True)
        assert rec["landed"] == 30821 and [f["to"] for f in fake.fired] == [30821], (rec, fake.fired)


def test_a_smooth_walk_with_no_press_that_keeps_the_rules_is_boxed_not_stalled(game):
    """Beside two doors at once, 20u from each, with the leg running north between them: every pad either closes on
    a door outright or could by its heading error. That is no press at all, which the unstick ladder must not read
    as a stall -- no wait, no push, no blocker, not ``frozen`` (a wait cannot change geometry): ``boxed``, with
    nothing pressed and nothing fired."""
    left, right = _rect(-400, -300, -20, 300), _rect(20, -300, 400, 300)
    fake = FakeGame(game, walkmesh=(-1000, -1000, 1000, 1000))
    fake.regions = {30820: [{"zone": left, "to": 30821, "arrive": (0, 0)}, {"zone": right, "to": 30822,
                                                                             "arrive": (0, 0)}]}
    fake.exit_frames = 30
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, 0, -200)
        g._axes[30820] = _prior()
        sent = _counting(g)
        rec = g.route_to(0.0, 800.0, avoid=[left, right], walkmesh=_flat_bgi(-1000, -1000, 1000, 1000),
                         prior=_prior(), smooth=True, unstick=True)
        assert rec["waypoints"] is not None, "premise: the router has a way -- the planner does not"
        assert rec["boxed"] and not rec["frozen"] and not rec["reached"], rec
        assert (rec["waits"], rec["pushes"], rec["blockers"]) == (0, 0, []), rec
        assert sent == [] and not fake.fired, (sent, fake.fired)


def test_route_to_refuses_a_zone_it_cannot_finish_on(game):
    """``zone`` finishes the last leg on it, which only the smooth walk does: the chunked walk refuses it rather
    than take it and stop within tolerance anyway. route_cross passes its zone on only under ``smooth``."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        with pytest.raises(HarnessError, match="only the smooth walk"):
            g.route_to(400.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), zone=_rect(300, -100, 500, 100))


@pytest.fixture(scope="module")
def dali():
    """``(player walkmesh(fid), script(fid))`` from the install, or a warned skip (THE WORKTREE SKIP TRAP) --
    tests/test_route_avoiding.py's ``stock``. Read-only: the Session under test never reads the install (its
    walkmesh and prior are passed in), the fake walks the same walkmesh."""
    import warnings
    try:
        from ff9mapkit import extract, storytrace
        from ff9mapkit.content import pathfind
        src = storytrace.stock_script_source()
        extract.stock_walkmesh(350)
        assert src(350) is not None
    except Exception as err:                                   # noqa: BLE001 -- no install here
        warnings.warn(
            f"the smooth-walk zone checks went UNVERIFIED against real bytes in this run: the game install is not "
            f"readable here ({type(err).__name__}). Run on the machine with the install.", UserWarning)
        pytest.skip("game install unavailable")
    return (lambda fid: pathfind.PlayerWalkmesh(extract.stock_walkmesh(fid))), (lambda fid: src(fid).data)


#: Where each field's walks start: 350's arrival from 351 (entrance 2: 18u beside the 351 door -- the ping-pong
#: spot), 356's decoded arrival (350, -158); 351 and 450 place him by other means, so a standable spot -- 351's
#: in the middle of the street, 450's 20-40u beside its 350 door (test_route_avoiding's 450 start).
_DALI_STARTS = {350: (258, -58), 351: (-450, 1800), 356: (350, -158), 450: (160, -1568)}


def _dali_places(script, fid):
    """The regions of stock ``fid`` a walk is sent to, in scan order: every distinct gateway zone, and on 450 --
    whose one gateway leads back to 350 -- its other trigger regions too (test_route_avoiding's 450 case)."""
    from ff9mapkit import eventscan
    places = []
    for gw in eventscan.scan_gateways(script(fid)):
        if gw["zone"] not in places:
            places.append(gw["zone"])
    if fid == 450:
        places += [z for z in eventscan.scan_region_zones(script(fid)) if z not in places]
    return places


def _dali_fake(game, walkmesh, script, fid, *, radius=True, face_gates=False):
    """A fake standing in stock ``fid``: its player walkmesh for a floor -- his centre kept COLLISION_RADIUS_W off
    its walls, as the engine keeps it (``radius``; off, anywhere on the mesh) -- every place a LIVE region
    (entering one fires it -- to 30000 + its index, so ``fired`` names it), the field's own key yaw, and 4x the
    frame rate (the protocol counts frames, so the suite pays a quarter of the wall clock).

    ``face_gates`` (opt-in, OFF by default so the walks written before the gate keep the doors they were written
    against): a place that is a stock gateway zone whose warp stock's DOOR FACING GATE guards -- any
    ``scan_gateways`` row of that zone with a ``face_gate`` -- carries that window as its region's ``"face"``, so
    the fake fires it only while his yaw faces the door, and the engine's polygon (the row's ``region``, every
    SetRegion point) as its ``"points"``, so it answers where IsInQuad does (FakeGame ``regions``); on 350 that is
    the doors to 351, 354, 353, 356 and 355, as in the game -- each a 5-point region."""
    from ff9mapkit import eventscan
    from ff9mapkit.content import movement
    from ff9mapkit.scene import cam
    twist = eventscan.scan_control_twist(script(fid))
    prior = movement.key_move_basis(None if twist is None else twist[1])
    fake = FakeGame(game, fps=960, twist=math.degrees(math.atan2(-prior["v"][0], prior["v"][1])))
    fake.walkmesh = walkmesh(fid)
    fake.clearance = cam.COLLISION_RADIUS_W if radius else None
    gates = {}
    if face_gates:
        for gw in eventscan.scan_gateways(script(fid)):
            if gw["face_gate"] is not None:
                gates.setdefault(tuple(map(tuple, gw["zone"])), (gw["face_gate"], gw["region"]))
    fake.regions = {fid: []}
    for i, z in enumerate(_dali_places(script, fid)):
        region = {"zone": z, "to": 30000 + i, "arrive": (0, 0)}
        if tuple(map(tuple, z)) in gates:
            window, points = gates[tuple(map(tuple, z))]
            region["face"], region["points"] = list(window), [list(p) for p in points]
        fake.regions[fid].append(region)
    fake.exit_frames = 30
    return fake, prior


@pytest.mark.parametrize("fid", [350, 351, 356, 450])
def test_a_smooth_walk_on_stock_dali_never_enters_a_region_it_was_not_sent_to(game, dali, fid):
    """THE GUARANTEE, on the real floors the tour walks. From each start, a smooth route_to every place of the
    field -- its goal inside that region (pathfind.region_goal), every other place avoided and LIVE: the only
    region any walk may fire is its own. 356 -> 358 alone has no route (a door strip closed to the player,
    test_route_avoiding); every other walk lands. On a floor that keeps his centre COLLISION_RADIUS_W off the
    walls, as the engine does, where a zone that reaches past that line only in a corner -- 350's door to 353 --
    fires only for a walk that finishes ON the zone (``zone``), not within a walk frame of its goal."""
    from ff9mapkit.content import pathfind
    walkmesh, script = dali
    fake, prior = _dali_fake(game, walkmesh, script, fid)
    places = _dali_places(script, fid)
    wm, start = walkmesh(fid), _DALI_STARTS[fid]
    assert all(pathfind.poly_gap(start[0], start[1], z) >= 0 for z in places), "premise: the start fires nothing"
    landed, unrouted = [], []
    with session(game, fake) as g:
        boot(g)
        g.warp(fid)
        _stand(g, fake, *start)
        g.calibrate_axes(hazards=places, prior=prior)     # clear of them all: the walks, not a probe, are on test
        for i, zone in enumerate(places):
            g.warp(fid)
            _stand(g, fake, *start)
            fired = len(fake.fired)
            goal = pathfind.region_goal(wm, zone)
            rec = g.route_to(goal[0], goal[1], avoid=[z for z in places if z is not zone], walkmesh=wm, prior=prior,
                             smooth=True, zone=zone)
            assert [f["to"] for f in fake.fired[fired:]] in ([], [30000 + i]), (i, rec, fake.fired[fired:])
            (unrouted if rec["waypoints"] is None else landed).append(i)
            if rec["waypoints"] is not None:
                assert rec["landed"] == 30000 + i, (i, rec)
    assert unrouted == ([2] if fid == 356 else []), unrouted          # 356's third gateway leads to 358
    assert landed, "premise: no walk ran"


@pytest.mark.parametrize("start", [(-1085, 2302), (153, 1398)])
def test_a_smooth_route_cross_finishes_inside_a_zone_standable_only_in_a_corner(game, dali, start):
    """Stock 350's door to 353: his centre, kept COLLISION_RADIUS_W off the walls, can stand in that zone only in
    a 34u wedge by its east corner, and region_goal's point lies 77u off the wall, where he cannot. Stopping
    within a walk frame of it left him 2-4u OUTSIDE, reached and nothing fired (the in-game run's crossings 9 and
    12). route_cross passes its zone on under ``smooth``; the last leg presses into the zone's nearest standable
    spot, and the 353 door fires -- from 350's arrival from 353 (entrance 9) and from its entrance 6."""
    from ff9mapkit.content import pathfind
    walkmesh, script = dali
    fake, prior = _dali_fake(game, walkmesh, script, 350)
    wm, places = walkmesh(350), _dali_places(script, 350)
    door = places[2]
    goal = pathfind.region_goal(wm, door)
    with session(game, fake) as g:
        boot(g)
        g.warp(350)
        _stand(g, fake, *_DALI_STARTS[350])
        g.calibrate_axes(hazards=places, prior=prior)             # on open ground: the walk is on test
        _stand(g, fake, *start)
        rec = g.route_cross(goal[0], goal[1], avoid=[z for z in places if z is not door], walkmesh=wm, prior=prior,
                            zone=door, smooth=True, timeout=3)
        assert rec["landed"] == 30002 and [f["to"] for f in fake.fired] == [30002], (rec, fake.fired)


@pytest.mark.parametrize("press", [(1, 0), (0, -1), (-1, 0), (0, 1)])
def test_the_fake_pushes_a_centre_placed_inside_his_radius_straight_out_onto_it(game, dali, press):
    """FakeGame's floor, as the engine's (FieldMapActorController.RadiusValid -> ServiceForces): placed nearer a wall
    than his radius -- 352's wake, 22.8u off a strip closed to him, 59u off the back wall -- his first moving frame
    lands him on the radius line, whichever way he pressed, even straight into the strip; it does not leave him
    where he stood nor walk him along the wall."""
    from ff9mapkit.scene import cam
    walkmesh, script = dali
    fake, _prior = _dali_fake(game, walkmesh, script, 352)
    wm = walkmesh(352)
    start = (-133.0, 847.0)
    assert wm.distance_to_boundary(-133, 847) < 25, "premise: deep in the band"
    fake.player = [start[0], 0.0, start[1]]
    fake._move_to(start[0] + 30 * press[0], start[1] + 30 * press[1])
    x, z = fake.player[0], fake.player[2]
    assert wm.distance_to_boundary(round(x), round(z)) >= cam.COLLISION_RADIUS_W - 1, (press, x, z)
    assert math.dist((x, z), start) < 100, (press, x, z)


@pytest.mark.parametrize("tour", [False, True])
def test_a_route_from_352s_wake_spot_walks_out_of_the_wall_band_and_through_its_door(game, dali, tour):
    """THE 352 WAKE (rung-3 runs 4 and 5 -- stock 352 and its verbatim fork 30834, one .bgi): the scene hands control
    back at (-133, 847), 22.8u off a strip closed to him, inside the 80u band a plan keeps off the walls, and
    route_to said "no route" twice, ending the tour. Planned from where he stands (route_avoiding ``leave_wall``),
    the walk leaves the band and fires 352's one door -- on a floor that pushes him straight out onto the radius
    line on his first moving frame, as the engine does (so off the planned leg, up to 57u along the wall's normal:
    FakeGame._pushed_out), and the walk goes on from wherever that put him. Plain, and as the tour walks it
    (unstick, npcs, smooth, zone)."""
    from ff9mapkit.content import pathfind
    walkmesh, script = dali
    fake, prior = _dali_fake(game, walkmesh, script, 352)
    wm, places = walkmesh(352), _dali_places(script, 352)
    zone, start = places[0], (-133, 847)
    assert len(places) == 1 and wm.distance_to_boundary(*start) < 25, "premise: 352's one door; deep in the band"
    goal = pathfind.region_goal(wm, zone)
    with session(game, fake) as g:
        boot(g)
        g.warp(352)
        _stand(g, fake, 0, -600)                                  # open ground: the walk is on test
        g.calibrate_axes(hazards=places, prior=prior)
        _stand(g, fake, *start)
        rec = g.route_cross(goal[0], goal[1], walkmesh=wm, prior=prior, zone=zone, smooth=True, unstick=tour,
                            npcs=tour, timeout=3)
        assert rec["waypoints"] is not None, rec
        assert rec["landed"] == 30000 and [f["to"] for f in fake.fired] == [30000], (rec, fake.fired)
        assert (rec["waits"], rec["pushes"], rec["blockers"]) == (0, 0, []), rec
        assert not rec["frozen"] and not rec["boxed"], rec


def test_a_smooth_leg_out_of_a_door_at_an_angle_to_both_pads_takes_its_first_step(game, dali):
    """Stock 356, 5.8u beside its 350 door, sent to 353: the leg's one zone-clear pad runs 32 degrees off it, and
    its smallest press strayed 24.04u against the door-side leg's drift of 24 -- no hold at all, which the unstick
    ladder read as a stall: two waits, a push refused, a phantom blocker, and ``frozen`` without a step. The drift
    no longer refuses the smallest press, and is judged from the leg still to walk: the walk lands, and nothing
    waited, pushed or was placed."""
    from ff9mapkit.content import pathfind
    walkmesh, script = dali
    fake, prior = _dali_fake(game, walkmesh, script, 356)
    wm, places = walkmesh(356), _dali_places(script, 356)
    zone, start = places[1], (1055, -521)
    assert 3 < pathfind.poly_gap(start[0], start[1], places[0]) < 10, "premise: beside the 350 door"
    goal = pathfind.region_goal(wm, zone)
    with session(game, fake) as g:
        boot(g)
        g.warp(356)
        _stand(g, fake, *_DALI_STARTS[356])
        g.calibrate_axes(hazards=places, prior=prior)
        _stand(g, fake, *start)
        g.ROUTE_WAIT_SECONDS = 0.5
        rec = g.route_to(goal[0], goal[1], avoid=[z for z in places if z is not zone], walkmesh=wm, prior=prior,
                         smooth=True, unstick=True)
        assert rec["landed"] == 30001 and [f["to"] for f in fake.fired] == [30001], (rec, fake.fired)
        assert (rec["waits"], rec["pushes"], rec["blockers"], rec["frozen"]) == (0, 0, [], False), rec
        assert not rec["boxed"], rec


def _swept_holds(g, wm, basis, start, goal, avoid, boxed=None):
    """The holds a smooth route_to plans from ``start`` to ``goal`` round ``avoid``, as the straight lines they
    sweep -- each from where he stands, as far as its frames can carry him at the session's rate (Rate.reach: the
    calibrated 60 fps here, nothing measured) -- executed as planned (he stops where the frames' average ends), on a
    basis that agrees with its prior (the heading spread's floor). None when no route exists. A leg left where no
    hold keeps the rules (route_to's ``boxed``) is appended to ``boxed``. No game: :meth:`Session._plan_hold` is
    pure."""
    import math as _m
    from ff9mapkit.content import pathfind
    wps = pathfind.route_avoiding(wm, start, goal, avoid)
    if wps is None:
        return None
    here, swept = (float(start[0]), float(start[1])), []
    legs = g._route_legs([here] + [(float(a), float(b)) for a, b in wps], avoid, (),
                         spread=g._heading_spread(basis, basis))
    for x, z, tol, leg in legs:
        aim = min(tol, leg["aim"] or tol)
        for _ in range(g.ROUTE_HOLDS):
            if _m.hypot(x - here[0], z - here[1]) <= aim:
                break
            hold = g._plan_hold(basis, here, (x, z), leg)
            if hold is None:
                if boxed is not None and _m.hypot(x - here[0], z - here[1]) > tol:
                    boxed.append((start, goal, here))
                break
            _buttons, u, n, slow = hold
            gait = "walk" if slow else "run"
            speed, reach = g.rate().speed(gait), g.rate().reach(n, gait)
            swept.append((here, (here[0] + u[0] * reach, here[1] + u[1] * reach)))
            here = (here[0] + u[0] * n * speed, here[1] + u[1] * n * speed)
    return swept


def test_no_smooth_hold_planned_across_stock_350_sweeps_into_another_exit(game, dali):
    """THE GUARANTEE AS GEOMETRY, wider than a fake run can afford: every hold planned on the routes from a 400u
    grid of standable starts over stock 350 (the tour's biggest field, 7 exits) -- and from starts 3-60u beside
    each of its zones, where arrivals stand and the drift is clamped -- to each exit, the others avoided, sweeps
    a line that never enters an avoided zone, and no leg is left with no hold at all (``boxed``). The falsifier:
    with the zone rule and the leg's drift switched off, the same planner walks the route from (-24, 3397) to
    the 450 exit into another zone."""
    from ff9mapkit import eventscan
    from ff9mapkit.content import movement, pathfind
    from ff9mapkit.scene import cam
    walkmesh, script = dali
    wm, places = walkmesh(350), _dali_places(script, 350)
    basis = movement.key_move_basis(eventscan.scan_control_twist(script(350))[1])
    goals = [pathfind.region_goal(wm, z) for z in places]
    g = session(game, None)

    def entered(swept, avoid):
        return any(pathfind.seg_poly_gap(a, b, q) < 0 for a, b in swept for q in avoid)

    broken = session(game, None)
    broken._probe_is_clear = lambda *a, **k: True
    broken._leg_chunk = lambda *a, **k: 1e6
    avoid = places[:6]
    assert entered(_swept_holds(broken, wm, basis, (-24, 3397), goals[6], avoid), avoid), "premise: it can fail"
    xs = [v[0] for v in wm.mesh.world_verts()]
    zs = [v[2] for v in wm.mesh.world_verts()]
    starts = [(x, z) for x in range(int(min(xs)), int(max(xs)), 400) for z in range(int(min(zs)), int(max(zs)), 400)
              if (wm.distance_to_boundary(x, z) or 0) >= cam.COLLISION_RADIUS_W
              and all(pathfind.poly_gap(x, z, q) >= pathfind.KEEPOUT_MARGIN_W for q in places)]
    beside = []
    for q in places:                                  # the first standable spot 3-60u out, on 24 bearings
        cx, cz = sum(p[0] for p in q) / len(q), sum(p[1] for p in q) / len(q)
        for k in range(24):
            a = math.radians(15 * k)
            for r in range(40, 800, 20):
                x, z = round(cx + r * math.cos(a)), round(cz + r * math.sin(a))
                if (3 <= pathfind.poly_gap(x, z, q) <= 60 and (wm.distance_to_boundary(x, z) or 0) >= cam.COLLISION_RADIUS_W
                        and all(pathfind.poly_gap(x, z, o) >= 0 for o in places)):
                    beside.append((x, z))
                    break
    routes = holds = 0
    boxed: list = []
    for s in starts + beside:
        for i, zone in enumerate(places):
            avoid = [q for q in places if q is not zone]
            swept = _swept_holds(g, wm, basis, s, goals[i], avoid, boxed)
            if swept is None:
                continue
            routes, holds = routes + 1, holds + len(swept)
            assert not entered(swept, avoid), (s, i)
    assert len(beside) >= 25 and routes >= 350 and holds >= 3000, (len(beside), routes, holds)
    assert boxed == [], boxed[:5]


def test_on_stock_350_the_smooth_walk_to_450_takes_a_fraction_of_the_requests(game, dali):
    """The sample the owner watched: 350 from the 351-door arrival to the 450 exit, chunked and smooth, from the
    same calibrated basis. Both land in 450's region and nothing else fires; smooth spends far fewer requests."""
    from ff9mapkit.content import pathfind
    walkmesh, script = dali
    fake, prior = _dali_fake(game, walkmesh, script, 350)
    places = _dali_places(script, 350)
    door = places[-1]                                              # scan order: 450's is 350's last gateway
    wm = walkmesh(350)
    goal = pathfind.region_goal(wm, door)
    spent = {}
    with session(game, fake) as g:
        boot(g)
        sent = _counting(g)
        for smooth in (False, True):
            g.warp(350)
            _stand(g, fake, *_DALI_STARTS[350])
            if 350 not in g._axes:
                g.calibrate_axes(hazards=places, prior=prior)
            fired = len(fake.fired)
            sent.clear()
            rec = g.route_to(goal[0], goal[1], avoid=[z for z in places if z is not door], walkmesh=wm,
                             prior=prior, smooth=smooth)
            spent[smooth] = len(sent)
            assert rec["landed"] == 30000 + len(places) - 1, (smooth, rec)
            assert [f["to"] for f in fake.fired[fired:]] == [30000 + len(places) - 1], fake.fired[fired:]
    print(f"350 -> 450 requests: chunked {spent[False]}, smooth {spent[True]}")
    assert spent[True] <= 0.6 * spent[False], spent


# --------------------------------------------------------------------------- the fake's door facing gate
# Stock's class-2 doors (content.doorface): a region whose tag 2 fires only while he FACES his projection onto its
# first edge. The fake models it opt-in (``regions`` ``"face"``) with a private yaw the presses turn, 40% a MovePC
# call -- so a walker that never faces the door can FAIL offline, as it did in the game at 350's door to 351. These
# step the fake BY HAND, frame by frame (no thread, no driver), so each names the exact frame a press turns him or
# a door fires.
def _hand_fake(game, regions=(), *, at=(0.0, 0.0), yaw=0.0, walkmesh=(-600.0, -600.0, 600.0, 600.0)):
    """A FakeGame on field 30820 with control, standing at ``at`` with yaw ``yaw``, its ``regions``, no coast tail
    (a released press stops dead, so a frame's turn is the press's alone), stepped only by :func:`_hand_frames`."""
    fake = FakeGame(game, walkmesh=walkmesh)
    fake.ui_state, fake.field_id, fake.control = "FieldHUD", 30820, True
    fake.player = [float(at[0]), 0.0, float(at[1])]
    fake._face_deg = float(yaw)
    fake.coast_frames = 0
    fake.regions = {30820: list(regions)}
    return fake


def _hand_frames(fake, n, *buttons):
    """Step ``fake`` ``n`` frames holding ``buttons`` for exactly those frames (none: he stands)."""
    for _ in range(n):
        fake.frame += 1
        for b in buttons:
            fake.down_at[b], fake.held[b] = fake.frame, fake.frame + 1
        fake._step_world()


#: A gated door on the south wall: its first edge z = -1000, x -500..500 -- from anywhere in it straight ahead of
#: him the exit point lies due -z, bearing 0, so his facing byte IS the gate's error.
_SOUTH_DOOR = [[-500, -1000], [500, -1000], [500, 100], [-500, 100]]


@pytest.mark.parametrize("walked", [False, True])
def test_the_fake_turns_him_40_percent_a_movepc_call_a_run_frame_one_a_walked_frame_half(game, walked):
    from ff9mapkit.content import doorface
    fake = _hand_fake(game, yaw=0.0)
    _hand_frames(fake, 1, "right", *(["cancel"] if walked else []))
    calls = 0.5 if walked else 1.0
    assert fake._face_deg == pytest.approx(-90.0 * (1 - 0.6 ** calls))            # toward +x: yaw -90
    assert fake._face_deg == pytest.approx(doorface.turn_step(0.0, -90.0, doorface.movepc_calls(15 if walked else 30)))
    assert fake.player[0] == pytest.approx(15.0 if walked else 30.0)
    _hand_frames(fake, 5, "right", *(["cancel"] if walked else []))
    assert fake._face_deg == pytest.approx(-90.0 * (1 - 0.6 ** (6 * calls)))


def test_the_fake_turns_him_on_a_press_into_a_wall_and_the_door_fires_where_he_stands(game):
    """His step blocked by the wall at x = 590, the press still turns him (the turn precedes the collision): he stands
    still at the wall and the east door -- its first edge beyond the wall, on x = 600 -- fires on the second frame,
    when 90 -> 18 -> -25.2 degrees brings its error from 76 to 46."""
    door = {"zone": [[600, -100], [600, 100], [400, 100], [400, -100]], "to": 30821, "arrive": (0, 0), "face": True}
    fake = _hand_fake(game, [door], at=(560, 0), yaw=90.0, walkmesh=(-600.0, -600.0, 590.0, 600.0))
    _hand_frames(fake, 1, "right")
    assert (fake.player[0], fake._face_deg, fake.fired) == (590.0, pytest.approx(18.0), [])
    _hand_frames(fake, 1, "right")
    assert fake._face_deg == pytest.approx(-25.2) and [f["to"] for f in fake.fired] == [30821]


def test_the_fake_keeps_his_yaw_standing_and_without_control(game):
    fake = _hand_fake(game, yaw=33.0)
    _hand_frames(fake, 10)
    assert fake._face_deg == 33.0
    fake.control = False
    _hand_frames(fake, 5, "left")
    assert fake._face_deg == 33.0 and fake.player[0] == 0.0
    fake._frozen_until = fake.frame + 100
    fake.control = True
    _hand_frames(fake, 5, "left")                                                # frozen: MovePC moves no one
    assert fake._face_deg == 33.0 and fake.player[0] == 0.0


@pytest.mark.parametrize("err,fires", [(47, True), (48, False), (-47, True), (-48, False)])
def test_the_fakes_facing_gate_is_the_engines_strict_window(game, err, fires):
    """Standing in the south door at yaw ``err`` 256ths off its bearing: the gate is re-tested every frame he stands,
    and fires for +-47, never for +-48 (B_LT / B_GT are strict)."""
    from ff9mapkit.content import doorface
    door = {"zone": _SOUTH_DOOR, "to": 30821, "arrive": (0, 0), "face": True}
    fake = _hand_fake(game, [door], at=(0, 0), yaw=doorface.yaw_of_byte(err))
    _hand_frames(fake, 3)
    assert [f["to"] for f in fake.fired] == ([30821] if fires else [])


def test_the_fakes_facing_gate_takes_an_explicit_window(game):
    from ff9mapkit.content import doorface
    door = {"zone": _SOUTH_DOOR, "to": 30821, "arrive": (0, 0), "face": [56, 200]}
    fake = _hand_fake(game, [door], at=(0, 0), yaw=doorface.yaw_of_byte(50))
    _hand_frames(fake, 1)
    assert [f["to"] for f in fake.fired] == [30821]


def test_a_gated_door_fires_on_a_standing_retest_once_he_faces_it_and_an_ungated_one_keeps_the_step_rule(game):
    """He stands in the gated door facing away: nothing, frame after frame -- and the moment his yaw faces it (as a
    press that moved him nowhere would leave it) it fires with no step at all. An UNGATED region he is placed in
    stays the fake's step-only trigger: standing there fires nothing."""
    door = {"zone": _SOUTH_DOOR, "to": 30821, "arrive": (0, 0), "face": True}
    fake = _hand_fake(game, [door], at=(0, 0), yaw=180.0)
    _hand_frames(fake, 5)
    assert fake.fired == [] and fake.field_id == 30820
    fake._face_deg = 10.0
    _hand_frames(fake, 1)
    assert [f["to"] for f in fake.fired] == [30821] and fake.field_id == 30821
    plain = _hand_fake(game, [{"zone": _SOUTH_DOOR, "to": 30821, "arrive": (0, 0)}], at=(0, 0), yaw=0.0)
    _hand_frames(plain, 5)
    assert plain.fired == []


def test_a_dead_region_and_a_failed_gate_shadow_the_regions_after_them(game):
    """The FIRST region containing him answers (TreadQuad): a dead one (``to`` None) and a gated one he does not face
    both end the search, so the live door listed after them fires only where he is in it alone."""
    live = {"zone": _rect(-200, -200, 200, 200), "to": 30821, "arrive": (0, 0)}
    for first in ({"zone": _rect(-200, -200, 0, 200), "to": None},
                  {"zone": _rect(-200, -200, 0, 200), "to": 30822, "arrive": (0, 0), "face": True}):
        fake = _hand_fake(game, [first, live], at=(-300, 0), yaw=180.0)           # facing +z; the first's edge is -z
        _hand_frames(fake, 4, "right")                                             # into the overlap, x -270 .. -180
        assert fake.fired == [] and fake.player[0] == pytest.approx(-180.0), first
        _hand_frames(fake, 7, "right")                                             # on, into the live door alone
        assert [f["to"] for f in fake.fired] == [30821], first


def test_arrive_face_sets_his_yaw_where_he_appears(game):
    door = {"zone": _rect(-100, -100, 100, 100), "to": 30821, "arrive": (5, 5), "arrive_face": 45.0}
    fake = _hand_fake(game, [door], at=(-130, 0), yaw=0.0)
    _hand_frames(fake, 1, "right")
    assert (fake.field_id, fake.player[0], fake._face_deg) == (30821, 5.0, 45.0)
    plain = _hand_fake(game, [dict(door, arrive_face=None)], at=(-130, 0), yaw=0.0)
    _hand_frames(plain, 1, "right")
    assert plain.field_id == 30821 and plain._face_deg == pytest.approx(-36.0)     # kept: the press's own turn


def test_a_region_with_engine_points_is_dead_in_a_pentagons_middle(game):
    """``points`` = the engine's polygon: IsInQuad's ring of ears. A step into a 5-gon's middle fires nothing, a step
    into an ear fires (the even-odd ``zone`` alone would have fired both)."""
    penta = [[round(400 * math.sin(2 * math.pi * k / 5)), round(400 * math.cos(2 * math.pi * k / 5))] for k in range(5)]
    door = {"zone": penta, "points": penta, "to": 30821, "arrive": (0, 0)}
    fake = _hand_fake(game, [door], at=(-30, 0), walkmesh=(-600.0, -600.0, 600.0, 600.0))
    _hand_frames(fake, 1, "right")                                                 # to the middle (0, 0)
    assert fake.fired == [] and fake.player[0] == pytest.approx(0.0)
    _hand_frames(fake, 12, "up")                                                   # north, into the top ear
    assert [f["to"] for f in fake.fired] == [30821]


def test_the_fake_publishes_dir_0_whatever_his_yaw(game):
    """The agent publishes PosObj.rot[1] as ``dir`` -- 0 on a field, which never writes it -- and so does the fake,
    however its private yaw has turned: a driver can predict the facing, never read it."""
    fake = _hand_fake(game, yaw=0.0)
    _hand_frames(fake, 3, "right")
    assert fake._face_deg != 0.0
    fake.armed = True
    fake.dir.mkdir(parents=True, exist_ok=True)
    fake._publish(force=True)
    assert json.loads((fake.dir / "state.json").read_text(encoding="utf-8"))["player"]["dir"] == 0


@pytest.mark.parametrize("walked", [False, True])
def test_the_coast_after_a_press_turns_him_too(game, walked):
    """The frame after a press is released the engine is still applying it (`coast_frames`): it moves him and TURNS
    him, the same calls as a frame of the press -- a walked frame half a call, a run frame one (research D6: the
    rotation keys on the same pressed booleans as the step). One frame of right, then one released frame."""
    from ff9mapkit.content import doorface
    fake = _hand_fake(game, yaw=0.0)
    fake.coast_frames = 1
    _hand_frames(fake, 1, "right", *(["cancel"] if walked else []))
    _hand_frames(fake, 1)
    calls = doorface.movepc_calls(15.0 if walked else 30.0)
    assert fake._face_deg == pytest.approx(doorface.turn_step(doorface.turn_step(0.0, -90.0, calls), -90.0, calls))
    assert fake.player[0] == pytest.approx(30.0 if walked else 60.0)                 # it moved him, too


def test_a_frozen_frame_still_retests_the_gated_door_he_stands_in(game):
    """A hold on movement with control kept (`_frozen_until`): MovePC moves and turns no one, but the region's tag 2
    still runs every tick he has control -- so standing in a gated door already facing it, it fires, frozen or not."""
    door = {"zone": _SOUTH_DOOR, "to": 30821, "arrive": (0, 0), "face": True}
    fake = _hand_fake(game, [door], at=(0, 0), yaw=180.0)
    fake._frozen_until = float("inf")
    _hand_frames(fake, 3)
    assert fake.fired == []                                                        # facing away: shut
    fake._face_deg = 0.0
    _hand_frames(fake, 1)
    assert [f["to"] for f in fake.fired] == [30821]


@pytest.mark.parametrize("phase", [0, 1])
def test_the_fakes_tick_phase_turns_him_in_whole_calls(game, phase):
    """`tick_phase`: the engine's 30 Hz ticks on every other frame of the fake's 60, a walked frame's call whole on its
    tick frame and none between -- so three walked frames are 2 calls in one phase and 1 in the other (the average,
    1.5, in neither), while the step stays the frame's average (45u either way)."""
    from ff9mapkit.content import doorface
    fake = _hand_fake(game, yaw=0.0)
    fake.tick_phase = phase
    ticks = sum(1 for f in range(fake.frame + 1, fake.frame + 4) if f % 2 == phase)
    _hand_frames(fake, 3, "right", "cancel")
    assert ticks in (1, 2) and fake._face_deg == pytest.approx(doorface.turn_step(0.0, -90.0, ticks))
    assert fake.player[0] == pytest.approx(45.0)


@pytest.mark.parametrize("face_gates", [False, True])
def test_dali_fake_carries_the_stock_face_gates_only_when_asked(game, dali, face_gates):
    """``_dali_fake(face_gates=True)`` gives each gated stock door its scan_gateways window and its engine polygon: on
    350 the doors to 351, 354, 353, 356 and 355 (entries 18-23; the two to 353 share a zone), each a 5-point region
    whose first four points are its zone -- and nothing without the flag."""
    from ff9mapkit import eventscan
    walkmesh, script = dali
    fake, _prior = _dali_fake(game, walkmesh, script, 350, face_gates=face_gates)
    faced = {tuple(map(tuple, r["zone"])): r.get("face") for r in fake.regions[350]}
    rows = [gw for gw in eventscan.scan_gateways(script(350)) if gw["face_gate"]]
    want = {tuple(map(tuple, gw["zone"])) for gw in rows}
    assert len(want) == 5
    assert {z for z, f in faced.items() if f} == (want if face_gates else set())
    assert all(f in (None, [48, 208]) for f in faced.values())
    points = {tuple(map(tuple, r["zone"])): r.get("points") for r in fake.regions[350] if r.get("face")}
    assert all(len(p) == 5 and p[:4] == [list(q) for q in z] for z, p in points.items())


# --------------------------------------------------------------------------- the walker faces the door
# In-game, 350 -> 351 missed 10 of 10 session-2 runs: the walk stood him IN the door's zone facing back up the street,
# and a door stock's facing gate keeps fires only while he faces it -- a REAL miss each time. A walk that ends in the
# zone with nothing fired now ends with a press that turns him to face it (Session._face_the_door). These walk the
# fake with the gate on (FakeGame ``regions`` ``"face"``), its floor keeping his centre 80u off the walls as the
# engine's does, so a walker that never faces the door FAILS here as it did in the game.

#: A door in the fake's east wall: its zone reaches from the room (x 300) to the wall (x 600), its FIRST EDGE the
#: wall's own, as a stock door's is -- so from anywhere in it the door bears due east. He stands in it only where
#: x <= 520 (80u off the wall).
_EAST_DOOR = [[600, -150], [600, 150], [300, 150], [300, -150]]


def _gated_room(game, regions):
    """The fake with ``regions`` on 30820 (a region's ``"face"`` gates it), its floor walled as the engine walls it."""
    fake = FakeGame(game)
    fake.walkmesh, fake.clearance = _flat_bgi(), 80.0
    fake.regions = {30820: list(regions)}
    fake.exit_frames = 30
    return fake


def _gated_start(g, fake, at, yaw=0.0):
    """Standing at ``at`` on 30820 with control, its basis known and his yaw ``yaw`` (the walk turns it from there)."""
    boot(g)
    g.warp(30820)
    g._axes[30820] = _prior()
    _stand(g, fake, *at)
    fake._face_deg = float(yaw)


def _gated_cross(g, zone, *, avoid=(), smooth=True, timeout=3, gate=(48, 208), region=None, goal=None):
    """The tour's crossing call (dali_tour.Tour._cross): route_cross to ``zone``'s region_goal (or ``goal``), the other
    doors kept out of, told the door's facing ``gate`` (scan_gateways' ``face_gate``; None: an ungated door) and its
    engine ``region`` -- smooth and minding the objects, or (``smooth`` False) the chunked walk."""
    from ff9mapkit.content import pathfind
    goal = pathfind.region_goal(_flat_bgi(), zone) if goal is None else goal
    return g.route_cross(goal[0], goal[1], avoid=list(avoid), walkmesh=_flat_bgi(), prior=_prior(), unstick=True,
                         zone=zone, smooth=smooth, npcs=smooth, timeout=timeout,
                         gate=None if gate is None else list(gate), region=region)


def test_a_gated_door_reached_facing_away_is_turned_to_and_crosses(game):
    """He walks into the east-wall door from the south: the walk's last holds press up, so he stands in the zone facing
    north, 90 degrees off the door's bearing -- where HEAD's walker stopped, the door shut. The facing step turns him
    to it (at least ROUTE_FACE_CALLS MovePC calls of a pad the prediction says faces it) and the door fires DURING that
    press: ``during`` "face", ``faced`` True, the exit point on the wall's edge in ``face_to``."""
    door = {"zone": _EAST_DOOR, "to": 30821, "arrive": (0, 0), "face": True}
    fake = _gated_room(game, [door])
    with session(game, fake) as g:
        _gated_start(g, fake, (410, -450))
        rec = _gated_cross(g, _EAST_DOOR)
    assert rec["landed"] == 30821 and [f["to"] for f in fake.fired] == [30821], rec
    assert rec["during"] == "face" and rec["faced"] is True, rec
    assert rec["face_to"][0] == 600 and rec["face_calls"] >= 4 and "right" in rec["face_pad"], rec     # the rule's 4
    assert rec["face_gate"] == [48, 208], rec


def test_an_approach_that_already_faces_the_door_crosses_with_no_turn(game):
    """Walked into from the west, the walk's own holds press right -- toward the door -- and it fires on the way in, as
    stock's does: the facing step is never taken (``faced`` None, no pad, no calls) and ``during`` is the walk's."""
    door = {"zone": _EAST_DOOR, "to": 30821, "arrive": (0, 0), "face": True}
    fake = _gated_room(game, [door])
    with session(game, fake) as g:
        _gated_start(g, fake, (-300, 0), yaw=180.0)
        rec = _gated_cross(g, _EAST_DOOR)
    assert rec["landed"] == 30821 and [f["to"] for f in fake.fired] == [30821], rec
    assert rec["during"] == "walk" and rec["faced"] is None, rec
    assert (rec["face_to"], rec["face_pad"], rec["face_calls"], rec["face_err"]) == (None, None, None, None), rec


def test_a_door_dead_even_when_faced_is_the_doors_real_miss_in_bounded_time(game):
    """The same door, dead (a region that answers and never fires: the story has shut it). The facing step turns him
    to it -- ``faced`` True, the predicted error inside the stock window -- and nothing fires: he stood IN the zone
    FACING the door, so the tour's strike rule reads it as the door's MISS, REAL. The crossing's wait is route_cross's
    own ``timeout``, and the whole call is bounded."""
    D = _tour_module()
    door = {"zone": _EAST_DOOR, "to": None, "face": True}
    fake = _gated_room(game, [door])
    with session(game, fake) as g:
        _gated_start(g, fake, (410, -450))
        t0 = time.time()
        rec = _gated_cross(g, _EAST_DOOR, timeout=2)
        assert time.time() - t0 < 30, "bounded"
    assert rec["landed"] is None and rec["inside"] is True and not fake.fired, rec
    assert rec["faced"] is True and rec["face_calls"] >= 4 and abs(rec["face_err"]) <= 47, rec          # the rule's 4
    assert rec["face_worst"] <= 47, rec
    assert D.failure(rec) == "miss", rec


def test_the_door_faced_is_the_zones_first_edge_not_the_side_he_came_in_by(game):
    """A free-standing zone on open floor whose FIRST edge is its west side (x = -100), walked into through its south
    side: the gate takes his bearing to his projection onto the first edge, wherever that lies -- here due west, with
    floor beyond it he could walk out across. The step presses a pad with a westward part, keeps him in the zone to
    the call it faces the door by, and the door fires."""
    zone = [[-100, 150], [-100, -150], [100, -150], [100, 150]]
    fake = _gated_room(game, [{"zone": zone, "to": 30821, "arrive": (0, 0), "face": True}])
    with session(game, fake) as g:
        _gated_start(g, fake, (0, -450))
        rec = _gated_cross(g, zone)
    assert rec["landed"] == 30821 and rec["during"] == "face" and rec["faced"] is True, rec
    assert rec["face_to"][0] == -100 and "left" in rec["face_pad"], rec


def test_a_turn_press_that_would_leave_the_zone_or_near_another_door_is_not_pressed(game):
    """A small gated zone (80u square on open floor, its first edge the east side) with another door 20u east of it:
    every press that would face this door either walks him out of its zone or up to the other one (PROBE_HAZARD_PAD).
    Nothing is pressed -- ``faced`` False, no pad, no calls -- nothing fires, and the tour does NOT strike the door:
    the walker never gave it its chance (LIVE, never the door's MISS)."""
    D = _tour_module()
    small = [[40, -40], [40, 40], [-40, 40], [-40, -40]]
    other = _rect(60, -300, 300, 300)
    fake = _gated_room(game, [{"zone": small, "to": 30821, "arrive": (0, 0), "face": True},
                              {"zone": other, "to": 30822, "arrive": (0, 0)}])
    with session(game, fake) as g:
        _gated_start(g, fake, (0, -400))
        rec = _gated_cross(g, small, avoid=[other], timeout=2)
    assert rec["landed"] is None and rec["inside"] is True and not fake.fired, rec
    assert rec["faced"] is False and rec["face_pad"] is None and rec["face_calls"] is None, rec
    assert rec["face_to"][0] == 40 and rec["face_err"] is None and rec["face_worst"] is None, rec
    assert D.failure(rec) == "live", rec


def test_the_chunked_route_cross_faces_the_door_too(game):
    """route_cross without ``smooth``: the chunked walk (one-axis walk_to bursts) that ends in the zone gets the same
    facing step -- route_cross hands a gated door to route_to to face either way. Walked in from due south, the last
    bursts press up, and it would stand there, the door shut. The chunked walk measures no hold's turn, so the step
    starts from ANY yaw: it records the bound its prediction holds him to (``face_worst``, inside the window) and no
    centre error at all (``face_err`` None) -- from an unknown yaw there is no single predicted yaw to name."""
    fake = _gated_room(game, [{"zone": _EAST_DOOR, "to": 30821, "arrive": (0, 0), "face": True}])
    with session(game, fake) as g:
        _gated_start(g, fake, (450, -450))
        rec = _gated_cross(g, _EAST_DOOR, smooth=False)
    assert rec["landed"] == 30821 and [f["to"] for f in fake.fired] == [30821], rec
    assert rec["during"] == "face" and rec["faced"] is True, rec
    assert rec["face_err"] is None and 0 <= rec["face_worst"] <= 47, rec


def test_a_door_that_fires_during_the_facing_press_is_landed_as_the_walks_own(game):
    """Control goes during the facing press: route_to lands it exactly as a step that fired a door -- ``during``
    "face", the field it changed to in ``changed_to`` and ``landed``, what the press covered in ``travelled`` -- and
    nothing more is pressed once control is gone (the fade runs 90 frames here). route_cross has nothing left to wait
    for, and ``inside`` is not judged."""
    fake = _gated_room(game, [{"zone": _EAST_DOOR, "to": 30821, "arrive": (0, 0), "face": True}])
    fake.exit_frames = 90
    with session(game, fake) as g:
        _gated_start(g, fake, (410, -450))
        rec = _gated_cross(g, _EAST_DOOR)
    assert (rec["during"], rec["landed"], rec["changed_to"], rec["inside"]) == ("face", 30821, 30821, None), rec
    fired = fake.fired[0]["executed"]
    assert not [s for s in fake.executed[fired:] if s[0] == "hold"], fake.executed[fired:]
    assert rec["travelled"] >= 450 + g.HALF_STEP, rec          # the walk's 450u up to the door, and the press's own


def test_a_smooth_walk_on_stock_350_crosses_every_door_its_facing_gate_keeps(game, dali):
    """THE IN-GAME MISS, OFFLINE: stock 350 with stock's door facing gate on its doors to 351, 354, 353, 356 and 355
    (``_dali_fake(face_gates=True)``), his yaw where the arrival from 351 leaves it (69 degrees, back up the street).
    From that arrival a smooth route_to every place of the field: the walk HEAD made ended in the 351 door's zone
    facing away and stood there, the door shut. Every walk now lands, and only in the region it was sent to -- the 351
    door by the facing step's own press."""
    from ff9mapkit.content import pathfind
    walkmesh, script = dali
    fake, prior = _dali_fake(game, walkmesh, script, 350, face_gates=True)
    places = _dali_places(script, 350)
    wm, start = walkmesh(350), _DALI_STARTS[350]
    turned = []
    with session(game, fake) as g:
        boot(g)
        g.warp(350)
        _stand(g, fake, *start)
        g.calibrate_axes(hazards=places, prior=prior)
        for i, zone in enumerate(places):
            g.warp(350)
            _stand(g, fake, *start)
            fake._face_deg = 69.0
            fired = len(fake.fired)
            goal = pathfind.region_goal(wm, zone)
            door = fake.regions[350][i]              # a gated door is faced by its engine polygon, as the tour does
            rec = g.route_to(goal[0], goal[1], avoid=[z for z in places if z is not zone], walkmesh=wm, prior=prior,
                             smooth=True, zone=zone, face=door.get("points") if door.get("face") else None,
                             face_window=door.get("face"))
            assert [f["to"] for f in fake.fired[fired:]] == [30000 + i] and rec["landed"] == 30000 + i, (i, rec)
            if rec["during"] == "face":
                turned.append(i)
    assert sum(1 for r in fake.regions[350] if r.get("face")) == 5, "premise: the gates are on"
    assert 0 in turned, turned                      # the 351 door: only the facing step opened it


def test_the_walks_last_hold_is_where_the_facing_step_starts():
    """``leg["turned"]`` -- the last hold and the MovePC calls it is known to have spent -- is the facing step's start:
    his yaw within 180 * 0.6**calls of that hold's, plus the leg's heading spread. None (unknown: any yaw) without
    it."""
    from harness.session import Session
    yaw, off = Session._held_yaw({"turned": ((("up",), (0.0, 1.0)), 6.0), "spread": math.radians(2.0)})
    assert abs(yaw) == pytest.approx(180.0) and off == pytest.approx(180 * 0.6 ** 6 + 2.0)
    assert Session._held_yaw({"turned": None, "spread": 0.0}) is None and Session._held_yaw(None) is None


def test_the_tour_reads_the_facing_step_and_a_bounce_by_what_they_were():
    """The strike rule on the facing step's verdict, at a GATED door (``face_gate``): IN the region FACING the door with
    nothing fired is the door's MISS (REAL) -- and so is a faced press whose rest took him on out of the region; in it
    with no press that faces the door possible, or standing in its dead middle, or left there frozen and never turned,
    is LIVE (the walker's limit). At a door with NO gate standing inside with nothing fired is the door's MISS, turned
    or not -- it fires for anyone standing in it; and a record with no gate (older logs) reads as before, a MISS. And a
    crossing that reached a destination which never handed control over -- route_cross's own error naming it -- is a
    BOUNCE."""
    D = _tour_module()
    rec = {"boxed": False, "boxed_by": None, "reached": True, "inside": True, "during": None, "route": 2, "waits": 0,
           "pushes": 0, "blockers": [], "frozen": False, "npc_replans": 0, "box_waits": 0, "held_by": None,
           "pinned": [], "landed": None}
    gated = dict(rec, face_gate=[48, 208])
    assert D.failure(dict(gated, faced=True)) == "miss"
    assert D.failure(dict(gated, faced=False)) == "live" and D.unfaced(dict(gated, faced=False))
    assert D.failure(dict(gated, faced=None, frozen=True)) == "live"                 # frozen inside: never turned
    assert D.failure(dict(gated, inside=False, faced=False)) == "live"               # the region's dead middle
    assert D.failure(dict(gated, inside=False, faced=True, waits=2, reached=False)) == "miss"
    assert D.failure(dict(rec, faced=False)) == "miss" and not D.unfaced(dict(rec, faced=False))   # no gate
    assert D.failure(dict(rec, faced=None)) == "miss" and D.failure(rec) == "miss"
    real = ("crossing from 350 reached field 353, but it never became playable within 20s -- the gateway WORKS and the "
            "destination is the problem. (timed out after 20.0s waiting for the player to have control)")
    assert D.failure({"landed": None, "error": real[:200], "inside": None, "during": None}) == "bounce"
    assert D.entered_field({"error": real[:200]}) == 353


# --- what the facing step must never do (the review of the step above; each a case that once went wrong offline) ---
def _here_cross(g, zone, *, avoid=(), gate=(48, 208), region=None, smooth=True, npcs=True, timeout=2):
    """route_cross whose goal is where he STANDS, inside the zone: the walk is over at once, and the facing step runs
    from exactly this spot (smooth or chunked; the door told its ``gate`` and ``region`` as the tour tells it)."""
    st = g.state
    return g.route_cross(st.player_x, st.player_z, avoid=list(avoid), walkmesh=_flat_bgi(), prior=_prior(),
                         unstick=True, zone=zone, smooth=smooth, npcs=npcs, timeout=timeout,
                         gate=None if gate is None else list(gate), region=region)


def _holds_after(fake, mark):
    return [s for s in fake.executed[mark:] if s[0] == "hold"]


def test_a_door_with_no_gate_is_never_turned_to_and_standing_in_it_shut_is_its_miss(game):
    """A door with NO facing gate (scan_gateways' ``face_gate`` None), shut by the story: he stands in its small zone
    and nothing fires -- which for an ungated region IS the verdict: it fires the first tick anyone stands in it with
    control. Nothing turns him (no hold at all), ``faced`` stays None, and the tour strikes the door (MISS): no press
    toward its first edge -- which would only walk him about, here up to the other door -- and no LIVE for a walker's
    limit that does not apply. A route_to into a zone it is not told to face presses nothing either."""
    D = _tour_module()
    small = [[40, -40], [40, 40], [-40, 40], [-40, -40]]
    other = _rect(60, -300, 300, 300)
    fake = _gated_room(game, [{"zone": small, "to": None}, {"zone": other, "to": 30822, "arrive": (0, 0)}])
    with session(game, fake) as g:
        _gated_start(g, fake, (0, 0))
        mark = len(fake.executed)
        rec = _here_cross(g, small, avoid=[other], gate=None)
        assert not _holds_after(fake, mark), fake.executed[mark:]
        again = g.route_to(0.0, 0.0, avoid=[other], walkmesh=_flat_bgi(), prior=_prior(), smooth=True, zone=small)
    assert rec["inside"] is True and not fake.fired and rec["face_gate"] is None, rec
    assert (rec["faced"], rec["face_pad"], rec["face_to"]) == (None, None, None), rec
    assert D.failure(rec) == "miss", rec
    assert again["faced"] is None and again["face_gate"] is None and not _holds_after(fake, mark), again


@pytest.mark.parametrize("tx,tz,rr", [(470, -40, 60), (465, -45, 60), (480, -50, 50)])
def test_the_facing_press_never_slides_him_into_a_triggers_range(game, tx, tz, rr):
    """A dead gated door (the whole press runs) along the fake's east wall, a Range beside the wall: the press aimed
    diagonally into the wall passes the Range well off its LINE, but slides along the wall into it (FakeGame slides as
    the engine's ServiceChar does) -- its script would fire, and the door's record would carry the blame. The points a
    slide reaches are held to the rules the line is (Session._slide_clear): the Range is never touched. Walked from a
    known yaw facing away (+z)."""
    zone = [[1400, 900], [900, 1400], [-300, 300], [300, -500]]
    fake = _gated_room(game, [{"zone": zone, "to": None, "face": True}])
    trig = {"x": float(tx), "z": float(tz), "r": 10.0, "range_r": float(rr), "uid": 150, "coll": True}
    with session(game, fake) as g:
        _gated_start(g, fake, (505, -150), yaw=180.0)
        fake.blockers = {30820: [trig]}
        published(g, lambda s: s.objects is not None and len(s.objects) == 1)
        rec = _here_cross(g, zone)
    assert not [t for t in fake.touched if t["uid"] == 150], (rec, fake.touched, fake.player)
    assert rec["faced"] in (True, False) and not fake.fired, rec


@pytest.mark.parametrize("coast", [1, 2])
def test_a_dead_doors_facing_press_and_its_tail_never_slide_into_the_live_door_beside_it(game, coast):
    """A DEAD gated door beside a LIVE one along the same wall, their shared side slanted to it: a press run parallel
    to that side keeps its line 60u off the live door, but slides up the wall -- and the press's movement TAIL (the
    harness allows a tick of it, Rate.reach's; the fake's ``coast_frames``) slides it on, over the shared side. The rest
    of
    a press matters for a door that stays shut: its whole travel, tail and slides included, keeps out of every other
    zone. Nothing fires, whatever the tail."""
    dead = [[1400, 830], [1500, 500], [300, -500], [300, -270]]
    live = [[300, -270], [1400, 830], [1400, 1100], [300, 30]]
    fake = _gated_room(game, [{"zone": dead, "to": None, "face": True}, {"zone": live, "to": 30821, "arrive": (0, 0)}])
    fake.coast_frames = coast
    with session(game, fake) as g:
        _gated_start(g, fake, (505, -150), yaw=180.0)
        rec = _here_cross(g, dead, avoid=[live], npcs=False)
    assert not fake.fired and rec["landed"] is None, (rec, fake.fired, fake.player)


def test_a_facing_press_into_a_hold_on_movement_is_not_counted(game):
    """A hold on movement that keeps control (the pad mask) starts as he steps into a live gated door and lasts 100
    frames: MovePC moves and turns no one. A press that moved him nothing where its line ran free did not run -- it is
    counted by what it moved (nothing), and the step presses on: once the hold lifts, a press turns him and the door
    fires. Never ``faced`` True with the door shut and the yaw unturned."""
    fake = _gated_room(game, [{"zone": _EAST_DOOR, "to": 30821, "arrive": (0, 0), "face": True}])
    fake.freezes = {30820: [{"zone": _EAST_DOOR, "frames": 100}]}
    with session(game, fake) as g:
        _gated_start(g, fake, (410, -450))
        rec = _gated_cross(g, _EAST_DOOR, timeout=2)
    assert fake._froze, "premise: the hold took him on the step into the zone"
    assert not (rec["faced"] is True and not fake.fired), rec
    assert [f["to"] for f in fake.fired] == [30821] and rec["during"] == "face", rec


@pytest.mark.parametrize("phase", [0, 1])
def test_an_odd_walked_press_is_counted_by_the_whole_calls_it_is_sure_of(game, phase):
    """The engine turns him in WHOLE MovePC calls, a walked one a 30 Hz tick, in a phase nobody sees (the fake's
    ``tick_phase``): 9 walked frames are 4 calls or 5. The nearest pad (right, 0.6 degrees off the bearing) runs into
    another door; the next (down+right) is 44 degrees off, and from a yaw turned all the way away from it (the chunked
    walk: unknown), its 4.5 AVERAGE calls say faced where 4 whole ones leave the door shut (an error of 48, which the
    strict gate fails). Counting only whole calls, the press is 10 frames -- 5 calls in either phase -- and the door
    fires in both."""
    from ff9mapkit.content import doorface
    q0 = (30000, -300)                            # the exit point stays clamped to q0: the bearing barely moves
    zone = [list(q0), [30000, -5000], [-200, -5000], [-200, 400]]
    other = _rect(150, -30, 250, 30)
    fake = _gated_room(game, [{"zone": zone, "to": 30821, "arrive": (0, 0), "face": True},
                              {"zone": other, "to": 30822, "arrive": (0, 0)}])
    fake.tick_phase, fake.coast_frames = phase, 0         # a press's frames are its held input, no more
    with session(game, fake) as g:
        _gated_start(g, fake, (0, 0), yaw=doorface.yaw_of(0.7071, -0.7071) + 179.9)
        rec = _here_cross(g, zone, avoid=[other], smooth=False, npcs=False)
    assert rec["faced"] is True and rec["face_pad"] == "down+right" and rec["face_calls"] == 5, rec
    assert [f["to"] for f in fake.fired] == [30821] and rec["during"] == "face", rec


def test_a_hold_cut_short_by_an_object_moving_leaves_his_yaw_unknown(game, monkeypatch):
    """A smooth hold that changed pad returns "moved" when an object moves onto the path -- after the hold was pressed,
    before its turn was measured. If the replan then finds no route, the facing step starts from where the walk's last
    hold left him: that must be THIS hold's pad or unknown, never the hold before it (a yaw known to 2 degrees, of the
    wrong pad, would let a farther pad pass as facing the door)."""
    holds, seen, state = [], [], {"moved": False}
    send = Session.send

    def spy_send(self, *steps):
        hb = tuple(s.split()[1] for s in steps if s.startswith("hold ") and s.split()[1] != "cancel")
        if hb:
            holds.append(hb)
        return send(self, *steps)
    npc_moved, plan_npcs, held_yaw = Session._npc_moved, Session._plan_npcs, Session._held_yaw

    def moved(self, st, watch):
        if not state["moved"] and len(holds) >= 2 and holds[-1] != holds[-2]:
            state["moved"] = True
            return True
        return npc_moved(self, st, watch)

    def plan(self, *a, **kw):
        return (None, []) if state["moved"] else plan_npcs(self, *a, **kw)

    def spy_held(leg):
        seen.append(None if leg is None else (leg.get("pressed"), leg.get("turned")))
        return held_yaw(leg)
    monkeypatch.setattr(Session, "send", spy_send)
    monkeypatch.setattr(Session, "_npc_moved", moved)
    monkeypatch.setattr(Session, "_plan_npcs", plan)
    monkeypatch.setattr(Session, "_held_yaw", staticmethod(spy_held))
    from ff9mapkit.content import pathfind
    fake = _gated_room(game, [{"zone": _EAST_DOOR, "to": 30821, "arrive": (0, 0), "face": True}])
    with session(game, fake) as g:
        _gated_start(g, fake, (200, 520))
        goal = pathfind.region_goal(_flat_bgi(), _EAST_DOOR)
        g.route_to(goal[0], goal[1], walkmesh=_flat_bgi(), prior=_prior(), unstick=True, smooth=True, npcs=True,
                   zone=_EAST_DOOR, face=_EAST_DOOR, timeout=3)
    assert state["moved"] and seen, "premise: a pad change, then an object moved"
    pressed, turned = seen[-1]
    assert turned is None or turned[0][0] == pressed[0], (pressed, turned)


def test_a_walk_that_ends_frozen_in_a_gated_door_is_not_turned_and_is_no_strike(game):
    """A hold on movement that never lifts takes him on the step into a gated door: the walk ends ``frozen``, standing
    in it. MovePC turns no one while movement is held, so the facing step is not taken (``faced`` None, nothing pressed
    after it) -- and a gated door he was never turned to is the walker's limit, LIVE, not the door's MISS."""
    D = _tour_module()
    fake = _gated_room(game, [{"zone": _EAST_DOOR, "to": 30821, "arrive": (0, 0), "face": True}])
    fake.freezes = {30820: [{"zone": _rect(300, -150, 600, -60), "frames": None}]}
    with session(game, fake) as g:
        _gated_start(g, fake, (450, -450))
        rec = _gated_cross(g, _EAST_DOOR, smooth=False, timeout=2)
    assert rec["frozen"] and rec["inside"] and not fake.fired, rec
    assert (rec["faced"], rec["face_pad"], rec["face_calls"]) == (None, None, None), rec
    assert D.failure(rec) == "live", rec


def test_a_press_that_would_leave_the_region_before_it_faces_the_door_is_never_made(game):
    """A small free-standing gated zone whose first edge (east, x = 50) he walked in ACROSS, heading west: he stands
    in it facing away, open floor beyond the edge. Every press that faces the door carries him out across it before the
    call that faces it -- and out of the region the gate never runs. None is pressed that would: on no frame with
    control after he first stood in the zone is he outside it before the door fires, and a step that cannot face it
    reads ``faced`` False (LIVE), never a press that walked him out and then read faced."""
    from ff9mapkit.content import doorface, pathfind
    D = _tour_module()
    zone = [[50, -60], [50, 60], [-50, 60], [-50, -60]]
    fake = _gated_room(game, [{"zone": zone, "to": 30821, "arrive": (0, 0), "face": True}])
    trail = []
    with session(game, fake) as g:
        _gated_start(g, fake, (400, 0), yaw=90.0)
        move = fake._move_to

        def spy(x, z, calls=1.0):
            moved = move(x, z, calls)
            trail.append((fake.player[0], fake.player[2], fake.control))
            return moved
        fake._move_to = spy
        rec = _gated_cross(g, zone, goal=pathfind.region_goal(_flat_bgi(), zone), timeout=2)
    first = next((k for k, (x, z, _c) in enumerate(trail) if doorface.region_contains(x, z, zone)), None)
    assert first is not None, "premise: the walk got him into the zone"
    left = [(x, z) for x, z, c in trail[first:] if c and not doorface.region_contains(x, z, zone)]
    assert not left, left
    assert fake.fired or (rec["faced"] is False and D.failure(rec) == "live"), rec


@pytest.mark.parametrize("place,at,yaw", [(0, (317, -102), 70.0), (4, (1043, 3370), None), (4, (1059, 3370), None)])
def test_on_stock_350_a_slide_along_the_wall_never_carries_the_facing_press_out_of_the_region(game, dali, place, at,
                                                                                               yaw):
    """Stock 350's doors to 351 and to 355, standing in them facing away (``yaw`` None: straight away from the door):
    their standable strips run along walls, and a press into a wall slides along it -- out of the region, where the
    gate never runs, before the call that faces the door if the slide is not bounded (Session._face_reach's disc). On
    no frame with control after the facing step begins is he outside the door's region before it fires; and never
    ``faced`` True standing outside it with the door shut (a false MISS)."""
    from ff9mapkit.content import doorface
    walkmesh, script = dali
    fake, prior = _dali_fake(game, walkmesh, script, 350, face_gates=True)
    places = _dali_places(script, 350)
    wm = walkmesh(350)
    zone, door = places[place], fake.regions[350][place]
    if yaw is None:
        yaw = doorface.bearing_deg(at[0], at[1], door["points"][0], door["points"][1]) + 180.0
        yaw = yaw - 360.0 if yaw > 180.0 else yaw
    trail = []
    with session(game, fake) as g:
        boot(g)
        g.warp(350)
        _stand(g, fake, *_DALI_STARTS[350])
        g.calibrate_axes(hazards=places, prior=prior)
        g.warp(350)
        fake._face_deg = yaw
        _stand(g, fake, *at)
        assert not fake.fired and doorface.region_contains(*at, door["points"]), "premise: in the door, facing away"
        move = fake._move_to

        def spy(x, z, calls=1.0):
            moved = move(x, z, calls)
            trail.append((fake.player[0], fake.player[2], fake.control))
            return moved
        fake._move_to = spy
        rec = g.route_cross(at[0], at[1], avoid=[z for z in places if z is not zone], walkmesh=wm, prior=prior,
                            unstick=True, zone=zone, smooth=True, npcs=True, timeout=2, gate=door["face"],
                            region=door["points"])
    out = [(round(x), round(z)) for x, z, c in trail if c and not doorface.region_contains(x, z, door["points"])]
    assert not out, (out[:3], rec)
    assert not (rec["faced"] is True and rec["inside"] is False and rec["landed"] is None), rec


@pytest.mark.parametrize("start", [(500, 0), (500, 30), (480, -20)])
def test_the_facing_press_is_sized_in_movepc_calls_not_frames(game, start):
    """A walked frame is HALF a MovePC call: the press that turns him must be 8 walked frames for its 4 calls, never 4.
    A gated zone whose first edge (its east side, tilted) he walked in across heading up+left: he stands in it facing
    far from the door, the nearest pad 20 degrees off its bearing -- 2 calls do not face it, 4 do -- and the door
    fires during the facing press."""
    from ff9mapkit.content import doorface, pathfind
    zone = [[250, -150], [100, 221], [-200, 221], [-200, -150]]
    fake = _gated_room(game, [{"zone": zone, "to": 30821, "arrive": (0, 0), "face": True}])
    presses = []
    with session(game, fake) as g:
        _gated_start(g, fake, start, yaw=90.0)
        pressed = g._pressed

        def spy(origin, walked, *steps):
            presses.append(steps)
            return pressed(origin, walked, *steps)
        g._pressed = spy
        rec = _gated_cross(g, zone, goal=pathfind.region_goal(_flat_bgi(), zone), timeout=2)
    assert rec["landed"] == 30821 and rec["during"] == "face" and rec["faced"] is True, rec
    frames = int(presses[0][0].split()[2])
    assert presses[0][0].startswith("hold cancel") and frames >= g.rate().frames_for_ticks(4) == 8, presses


def test_standing_in_a_gated_regions_dead_middle_nothing_is_pressed_and_it_is_no_strike(game):
    """A gated door whose region has FIVE points -- the kit's zone keeps its first four -- and a wall that stops him
    short of its live ears: standing where the zone holds him but no triangle of the region does (IsInQuad's dead
    middle, content.doorface.region_contains), the gate never runs, whatever he faces. Judged by the engine's polygon,
    the facing step presses nothing there (a press into the wall would read ``faced`` and leave the door shut: a false
    MISS) -- ``faced`` False, ``inside`` False (route_cross judges by the region too), the tour reads LIVE, and the
    door, which the fake answers only where the engine would, never fires."""
    D = _tour_module()
    penta = [[600, -150], [600, 150], [300, 150], [300, -150], [450, -400]]
    quad = penta[:4]
    fake = _gated_room(game, [{"zone": quad, "points": penta, "to": 30821, "arrive": (0, 0), "face": True}])
    floor = _flat_bgi(-600, -600, 550, 600)                     # his centre stands to x = 470: short of the live ears
    fake.walkmesh = floor
    with session(game, fake) as g:
        _gated_start(g, fake, (450, -100))
        mark = len(fake.executed)
        rec = g.route_cross(450.0, -100.0, walkmesh=floor, prior=_prior(), unstick=True, zone=quad, smooth=True,
                            npcs=True, timeout=2, gate=[48, 208], region=penta)
    from ff9mapkit.content import doorface
    assert not doorface.region_contains(450, -100, penta), "premise: the dead middle"
    assert rec["faced"] is False and rec["inside"] is False and not _holds_after(fake, mark), rec
    assert not fake.fired and D.failure(rec) == "live", rec


def test_on_stock_350_the_351_door_is_faced_by_its_engine_polygon(game, dali):
    """Stock 350's door to 351 is a FIVE-point region; the kit's zone keeps four. Standing at the tour's goal in it, as
    the arrival from 351 leaves his yaw (69): judged by the region -- where IsInQuad holds him, which on this door's
    standable ground is more than the quad -- one whole press (up+right) faces the door, and it fires during it. The
    quad alone admits no whole press there, only bursts."""
    walkmesh, script = dali
    fake, prior = _dali_fake(game, walkmesh, script, 350, face_gates=True)
    places = _dali_places(script, 350)
    wm = walkmesh(350)
    door = fake.regions[350][0]
    zone, penta = places[0], door["points"]
    got, presses = {}, []
    with session(game, fake) as g:
        boot(g)
        g.warp(350)
        _stand(g, fake, *_DALI_STARTS[350])
        g.calibrate_axes(hazards=places, prior=prior)
        pressed = g._pressed

        def spy(origin, walked, *steps):
            presses.append(steps)
            return pressed(origin, walked, *steps)
        g._pressed = spy
        for face in ("region", "quad"):
            g.warp(350)
            fake._face_deg = 69.0
            _stand(g, fake, 289, -74)
            presses.clear()
            fired = len(fake.fired)
            rec = g.route_cross(289.0, -74.0, avoid=[z for z in places if z is not zone], walkmesh=wm, prior=prior,
                                unstick=True, zone=zone, smooth=True, npcs=True, timeout=2, gate=[48, 208],
                                region=penta if face == "region" else None)
            got[face] = (rec, list(presses), [f["to"] for f in fake.fired[fired:]])
    rec, presses, fired = got["region"]
    assert rec["during"] == "face" and fired == [30000] and len(presses) == 1, (rec, presses)
    assert int(presses[0][0].split()[2]) >= 8 and rec["face_pad"] == "up+right", presses
    _rec, presses, _fired = got["quad"]
    assert presses and int(presses[0][0].split()[2]) < 8, presses          # the quad: a burst first


def test_at_350s_door_to_353_the_slide_bound_leaves_the_goal_unfaced(game, dali):
    """PINNED, a trade-off the bound makes: stock 350's door to 353 is standable only in a 34u pocket by its corner, and
    at the tour's goal there every facing press's WALL SLIDE bound (Session._face_reach: a slide either way along a wall
    whose line is not known) reaches out of the region -- though a plain press into the corner would open the door. So
    standing there facing away, the step presses nothing: ``faced`` False, LIVE, never the door's MISS (a replay steps
    back and walks in again; the tour's next visit arrives elsewhere). A tighter slide bound would change this: then
    expect the crossing here instead."""
    from ff9mapkit.content import pathfind
    D = _tour_module()
    walkmesh, script = dali
    fake, prior = _dali_fake(game, walkmesh, script, 350, face_gates=True)
    places = _dali_places(script, 350)
    wm = walkmesh(350)
    zone, door = places[2], fake.regions[350][2]
    goal = pathfind.region_goal(wm, zone)
    with session(game, fake) as g:
        boot(g)
        g.warp(350)
        _stand(g, fake, *_DALI_STARTS[350])
        g.calibrate_axes(hazards=places, prior=prior)
        g.warp(350)
        fake._face_deg = 0.0
        _stand(g, fake, *goal)
        rec = g.route_cross(goal[0], goal[1], avoid=[z for z in places if z is not zone], walkmesh=wm, prior=prior,
                            unstick=True, zone=zone, smooth=True, npcs=True, timeout=2, gate=door["face"],
                            region=door["points"])
    assert rec["faced"] is False and rec["face_pad"] is None and not fake.fired, rec
    assert D.failure(rec) == "live", rec


def test_a_replay_steps_back_from_a_gated_door_it_could_not_face(game, monkeypatch):
    """A replay step through a small GATED door (its first edge the north side) the walk comes into heading east: no
    facing press keeps the rules in so small a zone -- ``faced`` False, and the tour's own record says so (``faced``,
    ``face_gate``). LIVE: nothing struck. A retry from where he stands would only repeat it (the walk goes nowhere, the
    step judges the same spot), so the replay walks BACK to where the step began before it tries again -- and the
    step is done, one way or the other, well inside the budget: never "budget spent" on retries in place."""
    fake, tour, D = _replay_world(game, monkeypatch)
    small = [[360, 40], [440, 40], [440, -40], [360, -40]]
    fake.regions[_A][0] = {"zone": small, "to": _B, "arrive": (-250, 0), "face": True}
    tour._gates[_A] = [(_B, 0, small), (_C, 0, _WEST)]
    tour._doors[_A] = {(_B, tuple(map(tuple, small))): {"gate": [48, 208], "region": small}}
    with session(game, fake) as g:
        log = _replay_start(g, fake)
        stop = tour.replay(g, log, [[_A, 0, _B]], beat=2600, max_crossings=12, max_passes=2, budget_s=120)
    step = [x for x in log if x["k"] == "cross" and x["leg"] == "replay"]
    first = step[0]
    assert first["inside"] and first["faced"] is False and first["face_gate"] == [48, 208], first
    assert D.failure(first) == "live" and first["verdict"] == "live 1 (retried)", first
    walks = [(x.get("back", False), x["verdict"]) for x in step]
    for k, x in enumerate(step[:-1]):                # every retry after an unfaced door walked back first
        if D.unfaced(x) and not x.get("back"):
            assert step[k + 1].get("back") is True, walks
    unfaced = [x for x in step if D.unfaced(x) and not x.get("back")]
    assert len(unfaced) <= D.LIVE, walks
    assert walks[-1][1] == "replayed" or "the gated door was never faced" in stop, (stop, walks)


# --------------------------------------------------------------------------- the walker turns in place (s90)
# memoria-patch s90 publishes the facing a stock door gate reads (state.json player.yaw / player.face) and adds the
# agent verb `turn`, which turns him IN PLACE by the engine's own per-MovePC-call lerp and reports `turn_end` once the
# field has judged the final facing. Where the engine publishes it, the facing step turns him in place and decides by
# the MEASURED outcome (Session._turn_to_the_door); where it cannot, the open-loop press above is the step, unchanged.
# The fake models both (FakeGame ``facing_mode``: "absent", the default every test above runs on, and "published").


def _s90(fake):
    """``fake`` as an s90 engine: the facing published, ``turn`` understood."""
    fake.facing_mode = "published"
    return fake


def _moves(fake, trail):
    """Record where he stands after every frame he has control -- ``(x, z, control, field)`` -- a spy on the fake's
    MovePC frame."""
    step = fake._step_player

    def spy():
        step()
        trail.append((round(fake.player[0], 3), round(fake.player[2], 3), fake.control, fake.field_id))
    fake._step_player = spy


def _pads_turned(fake, mark):
    return [s[1] for s in fake.executed[mark:] if s[0] == "turn"]


def _direction_holds(fake, mark):
    return [s for s in fake.executed[mark:] if s[0] in ("hold", "press") and s[1] in ("up", "down", "left", "right")]


def _logged(fake, kind):
    """Every event of ``kind`` the fake has logged, as written (every value but ``frame`` a string)."""
    path = fake.dir / "events.jsonl"
    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [r for r in rows if r["kind"] == kind]


def _turn_ends(fake):
    return _logged(fake, "turn_end")


def _on_turns(fake, *acts):
    """Run each ``(k, frames, fn)`` of ``acts`` -- ``fn()`` once, on the fake's frame ``frames`` frames after the one
    its k-th ACCEPTED ``turn`` (1-based) began on, after that frame's world has stepped: a script, a UI, a hold on
    movement or a human that comes or goes while a turn is on. Returns the frames the accepted turns began on."""
    begin, step, began = fake._begin_turn, fake._step_world, []

    def begin_spy(*a, **kw):
        begin(*a, **kw)                      # a refusal raises before it is counted
        began.append(fake.frame)

    def step_spy():
        step()
        for k, frames, fn in acts:
            if len(began) >= k and fake.frame == began[k - 1] + frames:
                fn()
    fake._begin_turn, fake._step_world = begin_spy, step_spy
    return began


def test_state_tells_an_engine_that_cannot_face_from_one_with_no_facing_now_from_a_facing():
    """s90's three cases, kept apart as s89's objects are: ``player.face`` ABSENT -- an engine that cannot publish the
    facing (and cannot ``turn``); null -- it can, and there is none this sample; a number -- the facing byte, with the
    raw yaw beside it. 0 is a facing (-z), never "none"; and ``dir`` is not the facing whatever it holds."""
    for raw in ({"frame": 1}, {"frame": 1, "player": {"x": 1.0, "z": 2.0, "dir": 0, "control": True}}):
        st = State(raw)
        assert (st.facing_status, st.player_yaw, st.player_face) == ("cannot", None, None), raw
    unknown = State({"frame": 1, "player": {"x": None, "dir": 0, "yaw": None, "face": None}})
    assert (unknown.facing_status, unknown.player_yaw, unknown.player_face) == ("unknown", None, None)
    known = State({"frame": 1, "player": {"x": 5.0, "dir": 0, "yaw": -85.301, "face": 195}})
    assert (known.facing_status, known.player_yaw, known.player_face) == ("known", -85.301, 195)
    zero = State({"frame": 1, "player": {"dir": 77, "yaw": 0, "face": 0}})
    assert (zero.facing_status, zero.player_yaw, zero.player_face) == ("known", 0.0, 0)


def test_a_turn_refusal_is_classified_on_the_agents_own_words_and_a_turn_end_is_parsed():
    """Every refusal message HarnessAgent.cs (s90) can give a ``turn``, verbatim, to its kind -- on the stable prefix,
    the TurnBlocker token and an overlapping body's uid pulled out; one no rule knows is "other", never guessed.
    And ``turn_end`` as the agent writes it -- every value but ``frame`` quoted -- read back as numbers, the end values
    null after a door's warp."""
    from harness.channel import parse_turn_end, turn_refusal
    said = {
        "needs a direction (up|down|left|right, '+'-joined)": ("argument", None, None),
        "'confirm' is not a direction (up|down|left|right, '+'-joined)": ("argument", None, None),
        "unknown button 'sideways'": ("argument", None, None),
        "needs a field with a controlled player under user control (movement)": ("blocked", "movement", None),
        "needs a field with a controlled player under user control (hud)": ("blocked", "hud", None),
        "the player's field, position or facing is unreadable": ("unreadable", None, None),
        "the last turn's keys are up and the field is still judging it -- wait for its turn_end":
            ("judging", None, None),
        "the turn in progress began on another actor or field -- it is cut this frame; turn again after its turn_end":
            ("cut", None, None),
        "[AnalogControl] Enabled=0 -- MovePC's key path would step him, not turn him": ("analog", None, None),
        "Right is held or scheduled -- release it (and let it lift) first": ("held", None, None),
        "opposite directions cancel to no direction": ("opposite", None, None),
        "a physical stick or key is pushing the axis (|a| 0.8) -- MovePC's axis branch would walk him":
            ("axis", None, None),
        "a click-to-move path is pending -- the turn keys would consume it": ("path", None, None),
        "overlapping object uid 147 -- a turn toward it would push him out": ("overlap", None, 147),
        "unknown op 'turn'": ("cannot", None, None),
        "a refusal this driver has never seen": ("other", None, None),
    }
    for message, want in said.items():
        got = turn_refusal(message)
        assert (got.kind, got.why, got.uid) == want and got.message == message, (message, got)
        assert isinstance(got, HarnessError)
    end = parse_turn_end({"frame": 1234, "kind": "turn_end", "why": "ended", "frames": "8", "yaw0": "69.12",
                          "yaw": "-85.301", "face": "195", "moved": "0"})
    assert end == {"frame": 1234, "why": "ended", "frames": 8, "yaw0": 69.12, "yaw": -85.301, "face": 195,
                   "moved": 0.0}
    warped = parse_turn_end({"frame": 9, "kind": "turn_end", "why": "field", "frames": "3", "yaw0": "0", "yaw": None,
                             "face": None, "moved": None})
    assert (warped["why"], warped["frames"], warped["yaw"], warped["face"], warped["moved"]) == ("field", 3, None,
                                                                                                None, None)


def test_the_fake_publishes_the_facing_only_as_the_s90_agent_does(game):
    """``facing_mode`` "absent" (the default): no ``yaw`` / ``face`` key at all. "published": the yaw to 0.001 and the
    facing BYTE (content.doorface.facing_byte) as numbers on a field, both null together off one; ``dir`` stays 0."""
    from ff9mapkit.content import doorface
    fake = _hand_fake(game, yaw=-85.3014)
    fake.armed = True
    fake.dir.mkdir(parents=True, exist_ok=True)

    def player():
        fake._publish(force=True)
        return json.loads((fake.dir / "state.json").read_text(encoding="utf-8"))["player"]
    assert "yaw" not in player() and "face" not in player()
    fake.facing_mode = "published"
    p = player()
    assert (p["yaw"], p["face"], p["dir"]) == (-85.301, doorface.facing_byte(-85.3014), 0) and p["face"] == 195
    fake.ui_state = "WorldHUD"
    p = player()
    assert p["yaw"] is None and p["face"] is None


def test_the_fakes_turn_refuses_as_the_agent_does_and_never_steps_him(game):
    """The fake's ``turn``, stepped by hand: the agent's refusals in its words -- no direction, not a direction, an
    unknown button, no control, opposite keys, a direction held or scheduled, a body he overlaps, the last turn still
    being judged -- and ``hold`` / ``press`` of a direction refused while a turn is open; an engine without s90
    answers ``unknown op 'turn'``. An accepted turn turns him 40% a MovePC call and never moves him, and its
    ``turn_end`` -- every value a string -- comes two ticks after the keys lift."""
    from ff9mapkit.content import doorface
    fake = _hand_fake(game, at=(100.0, 50.0), yaw=90.0)

    def refused(step, match):
        with pytest.raises(RuntimeError, match=match):
            fake._execute(step)
    refused(["turn", "right", "8"], r"^unknown op 'turn'$")
    _s90(fake)
    refused(["turn"], r"^needs a direction \(up\|down\|left\|right, '\+'-joined\)$")
    refused(["turn", "confirm"], r"^'confirm' is not a direction")
    refused(["turn", "up+sideways"], r"^unknown button 'sideways'$")
    refused(["turn", "north+south"], r"^opposite directions cancel to no direction$")
    fake.control = False
    refused(["turn", "right"], r"^needs a field with a controlled player under user control \(control\)$")
    fake.control = True
    fake._execute(["hold", "up", "5"])
    refused(["turn", "right"], r"^Up is held or scheduled -- release it \(and let it lift\) first$")
    fake.held.clear()
    fake.down_at.clear()
    fake.blockers = {30820: [{"x": 120.0, "z": 50.0, "r": 40.0, "uid": 133}]}
    refused(["turn", "right"], r"^overlapping object uid 133 -- a turn toward it would push him out$")
    fake.blockers = {}
    fake._execute(["turn", "east", "8"])
    refused(["hold", "up", "3"], r"^a `turn` is still open")
    refused(["press", "left", "2"], r"^a `turn` is still open")
    fake._execute(["hold", "cancel", "3"])                                        # never refused
    fake.dir.mkdir(parents=True, exist_ok=True)
    for _ in range(12):
        fake.frame += 1
        fake._step_world()
        fake._service_turn()
        if fake.frame == 9:                                                        # the keys lifted this frame
            refused(["turn", "up"], r"^the last turn's keys are up and the field is still judging it")
    rows = [json.loads(ln) for ln in (fake.dir / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    ends = [r for r in rows if r["kind"] == "turn_end"]
    assert fake.player == [100.0, 0.0, 50.0] and fake._face_deg < -80.0, (fake.player, fake._face_deg)
    assert len(ends) == 1 and ends[0]["frame"] == 11, ends                        # two ticks after the lift
    e = ends[0]
    assert (e["why"], e["frames"], e["yaw0"], e["moved"]) == ("ended", "8", "90", "0"), e
    assert all(isinstance(e[k], str) for k in ("why", "frames", "yaw0", "yaw", "face", "moved")), e
    assert isinstance(e["frame"], int) and e["face"] == str(doorface.facing_byte(float(e["yaw"]))), e


def test_turn_in_place_waits_past_the_ack_for_the_turn_end_and_parses_its_strings(game):
    """Session.turn_in_place sends ``turn right 8`` and ``wait 10``, and the ack comes BEFORE the field has judged the
    final facing -- here, with the report held 60 ticks past the lift, a quarter of a second of the fake's clock after
    it. The call waits for the ``turn_end`` that request produced and returns it with every value PARSED: the frames
    its keys were down, the yaw it began and ended at, the facing byte, and ``moved`` 0 -- he turned where he stood."""
    from ff9mapkit.content import doorface
    fake = _s90(FakeGame(game))
    fake.turn_settle_passes = 60
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, 100, 50)
        fake._face_deg = 90.0
        st = published(g, lambda s: s.player_face == doorface.facing_byte(90.0))
        assert st.facing_status == "known" and st.player_yaw == 90.0
        seq = g.channel.seq + 1
        end = g.turn_in_place("right", 8)
        evs = g.channel.events()
    assert (end["why"], end["frames"], end["moved"]) == ("ended", 8, 0.0), end
    assert end["yaw0"] == 90.0 and end["yaw"] == pytest.approx(doorface.turn_step(90.0, -90.0, 8), abs=1e-3), end
    assert isinstance(end["face"], int) and end["face"] == doorface.facing_byte(end["yaw"]), end
    assert fake.player == [100.0, 0.0, 50.0]
    acked = next(k for k, e in enumerate(evs) if e["kind"] == "ack" and e["seq"] == str(seq))
    ended = next(k for k, e in enumerate(evs) if e["kind"] == "turn_end")
    assert acked < ended and evs[ended]["frame"] - evs[acked]["frame"] >= 40, (evs[acked], evs[ended])


def test_turn_in_place_refuses_an_engine_that_cannot_and_surfaces_the_agents_refusal(game):
    """Never sent to an engine without s90 (no ``player.face`` key: "cannot"), nor for a button that is not a direction:
    the driver refuses before the wire. On an s90 engine the agent's own refusal comes back as TurnRefused, classified
    on its stable words -- a direction still scheduled ("held"), a body he overlaps ("overlap", its uid) -- and a
    ``hold`` of a direction while a turn is still open is refused the other way round."""
    from harness.channel import TurnRefused
    old = FakeGame(game)
    with session(game, old) as g:
        boot(g)
        g.warp(30820)
        assert g.state.facing_status == "cannot"
        with pytest.raises(HarnessError, match="s90"):
            g.turn_in_place("right", 8)
        with pytest.raises(HarnessError, match="DIRECTION"):
            g.turn_in_place("confirm", 8)
        assert not [s for s in old.executed if s[0] == "turn"], old.executed
    fake = _s90(FakeGame(game))
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, 0, 0)
        g.hold("up", 400)
        with pytest.raises(TurnRefused) as got:
            g.turn_in_place("right", 8)
        assert got.value.kind == "held" and got.value.message.startswith("Up is held or scheduled"), got.value
        g.release("up")
        g.wait_frames(2)
        _stand(g, fake, 0, 0)                                  # the hold walked him: back where the body stands on him
        fake.blockers = {30820: [{"x": 20.0, "z": 0.0, "r": 60.0, "uid": 141}]}
        with pytest.raises(TurnRefused) as got:
            g.turn_in_place("right", 8)
        assert (got.value.kind, got.value.uid) == ("overlap", 141), got.value
        fake.blockers = {}
        g.send("turn left 60", wait=False)
        g.wait_frames(3)
        with pytest.raises(HarnessError, match="a `turn` is still open"):
            g.send("hold up 5")


def test_on_an_s90_engine_the_walker_turns_in_place_to_face_a_gated_door_and_it_crosses(game):
    """He stands in the east-wall door facing straight away from it (yaw 90: -x). On an engine that publishes the
    facing, the facing step does not walk: it turns him IN PLACE toward the door (the pad nearest its bearing, right)
    and the door fires during the turn -- ``during`` "face", ``faced`` True, ``face_measured`` True (the field
    changed), ``face_moved`` 0 -- with ZERO travel: no direction held or pressed, and on every frame he had control he
    stood where he stood."""
    door = {"zone": _EAST_DOOR, "to": 30821, "arrive": (0, 0), "face": True}
    fake = _s90(_gated_room(game, [door]))
    trail = []
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=90.0)
        mark = len(fake.executed)
        _moves(fake, trail)
        rec = _here_cross(g, _EAST_DOOR)
    assert _pads_turned(fake, mark) == ["right"] and not _direction_holds(fake, mark), fake.executed[mark:]
    assert [e["why"] for e in _turn_ends(fake)] == ["control"]           # the door's DisableMove took him mid-turn
    assert trail and all((x, z) == (450.0, 0.0) for x, z, c, f in trail if c and f == 30820), trail
    assert rec["landed"] == 30821 and [f["to"] for f in fake.fired] == [30821], rec
    assert (rec["during"], rec["faced"], rec["face_measured"], rec["face_moved"]) == ("face", True, True, 0.0), rec
    assert rec["face_pad"] == "right" and rec["travelled"] == 0, rec


def test_a_door_still_shut_with_the_measured_face_in_the_window_is_a_real_miss(game):
    """The same door, dead (the story has shut it). The turn in place ends ``ended``: the field ran its passes on the
    final facing and did not take him. The facing byte the ENGINE reported is in the window, so the gate read it and
    stayed shut -- ``faced`` True, ``face_measured`` True, ``face_err`` the MEASURED signed error (the byte his yaw
    really has, against the engine's exit point from where he stands), ``face_worst`` its size -- and the tour strikes
    the door: a REAL miss, measured. Nothing walked him."""
    from ff9mapkit.content import doorface
    D = _tour_module()
    fake = _s90(_gated_room(game, [{"zone": _EAST_DOOR, "to": None, "face": True}]))
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=90.0)
        mark = len(fake.executed)
        rec = _here_cross(g, _EAST_DOOR)
    truth = doorface.signed_error(doorface.gate_value(fake.player[0], fake.player[2], fake._face_deg,
                                                      _EAST_DOOR[0], _EAST_DOOR[1]))
    assert _pads_turned(fake, mark) == ["right"] and not _direction_holds(fake, mark), fake.executed[mark:]
    assert abs(truth) <= 47 and fake.player == [450.0, 0.0, 0.0], (truth, fake.player)
    assert rec["landed"] is None and rec["inside"] is True and not fake.fired, rec
    assert (rec["faced"], rec["face_measured"], rec["face_err"], rec["face_worst"]) == (True, True, truth, abs(truth))
    assert D.failure(rec) == "miss", rec


def test_a_turn_that_lands_out_of_the_window_turns_again(game):
    """A machine that spends fewer MovePC calls a frame than the calibrated one (the fake's ``turn_calls``: one call in
    the whole 8-frame turn): the first turn ends with his measured facing still out of the window -- and it MOVED his
    yaw, so the pad has more to give. He is turned again, the same pad, and the second turn's measured facing is in
    the window: ``faced`` True on the engine's report, never on the plan's calls. (The door is dead, so each turn's end
    is judged by its report alone.)"""
    from ff9mapkit.content import doorface
    fake = _s90(_gated_room(game, [{"zone": _EAST_DOOR, "to": None, "face": True}]))
    fake.turn_calls = 1.0 / 8
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=60.0)
        mark = len(fake.executed)
        rec = _here_cross(g, _EAST_DOOR)
    assert _pads_turned(fake, mark) == ["right", "right"], fake.executed[mark:]
    assert fake._face_deg == pytest.approx(doorface.turn_step(60.0, -90.0, 2), abs=0.01)
    assert (rec["faced"], rec["face_measured"]) == (True, True) and abs(rec["face_err"]) <= 47, rec
    assert not _direction_holds(fake, mark) and not fake.fired, fake.executed[mark:]


def test_a_pad_whose_measured_heading_cannot_face_the_door_gives_way_to_one_that_can(game):
    """The basis the driver holds is 100 degrees off the field's (the fake's twist): the pad nearest the door's bearing
    on paper, right, truly heads 100 degrees off it. Its first turn moves his yaw and ends out of the window; its
    second SETTLES there (it has nothing left to turn) -- so that pad cannot face the door, and the heading it settled
    at says how far off the basis is. The next pad is ranked by that measurement, not by the paper: down, which truly
    heads the door's way, and the door fires during its turn. Never a walked step."""
    door = {"zone": _EAST_DOOR, "to": 30821, "arrive": (0, 0), "face": True}
    fake = _s90(_gated_room(game, [door]))
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=90.0)
        fake.twist = 100.0
        mark = len(fake.executed)
        rec = _here_cross(g, _EAST_DOOR)
    turned = _pads_turned(fake, mark)
    assert turned[:2] == ["right", "right"] and turned[2:] == ["down"], turned
    assert rec["landed"] == 30821 and rec["during"] == "face" and rec["face_measured"] is True, rec
    assert rec["face_pad"] == "down" and not _direction_holds(fake, mark), rec


def test_a_turn_refused_for_a_reason_a_press_does_not_share_falls_back_to_the_press(game):
    """``[AnalogControl] Enabled=0``: the agent refuses every ``turn`` (the key path would step him). A walked press
    does not share that -- it is MEANT to step him -- so the facing step falls back to the open-loop press: one turn
    tried, then the press, which faces the door and it fires (``face_measured`` False: a prediction)."""
    door = {"zone": _EAST_DOOR, "to": 30821, "arrive": (0, 0), "face": True}
    fake = _s90(_gated_room(game, [door]))
    fake.analog_control = False
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=90.0)
        mark = len(fake.executed)
        rec = _here_cross(g, _EAST_DOOR)
    assert _pads_turned(fake, mark) == ["right"] and _direction_holds(fake, mark), fake.executed[mark:]
    assert rec["landed"] == 30821 and rec["during"] == "face" and rec["faced"] is True, rec
    assert rec["face_measured"] is False, rec


def test_a_turn_refused_for_a_reason_a_press_shares_is_waited_out_never_pressed_through(game):
    """A hold on movement (the script's pad mask, control kept) lands on the very frame the first turn is asked for:
    the agent refuses it (``needs a field ... (movement)``). A press shares that -- MovePC turns no one while movement
    is held -- so nothing is pressed: the step waits it out and turns again, and the door fires on the turn."""
    door = {"zone": _EAST_DOOR, "to": 30821, "arrive": (0, 0), "face": True}
    fake = _s90(_gated_room(game, [door]))
    execute, froze = fake._execute, []

    def freeze_first_turn(step):
        if step[0] == "turn" and not froze:
            froze.append(fake.frame)
            fake._frozen_until = fake.frame + 40
        return execute(step)
    fake._execute = freeze_first_turn
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=90.0)
        mark = len(fake.executed)
        rec = _here_cross(g, _EAST_DOOR)
    assert froze and _pads_turned(fake, mark) == ["right", "right"], fake.executed[mark:]
    assert not _direction_holds(fake, mark), fake.executed[mark:]
    assert rec["landed"] == 30821 and rec["during"] == "face" and rec["face_measured"] is True, rec


def test_on_a_pre_s90_engine_the_facing_step_is_the_open_loop_press_unchanged(game):
    """An engine that cannot publish the facing (``facing_mode`` "absent": no ``player.face`` key) is never sent a
    ``turn``: the facing step is the walked press it always was -- the door fires during it, ``faced`` True on the
    prediction, and ``face_measured`` False says so."""
    door = {"zone": _EAST_DOOR, "to": 30821, "arrive": (0, 0), "face": True}
    fake = _gated_room(game, [door])
    with session(game, fake) as g:
        _gated_start(g, fake, (410, -450))
        mark = len(fake.executed)
        rec = _gated_cross(g, _EAST_DOOR)
    assert not _pads_turned(fake, mark) and _direction_holds(fake, mark), fake.executed[mark:]
    assert rec["landed"] == 30821 and rec["during"] == "face" and rec["faced"] is True, rec
    assert rec["face_measured"] is False and rec["face_moved"] is None and rec["face_calls"] >= 4, rec


def test_a_turn_that_moved_him_is_judged_as_the_press_it_was(game):
    """A turn in place moves him 0 (the agent's ceiling for its float noise: 0.25u). Standing nearer the wall than his
    radius, the turn's zero step is still pushed out onto the radius line (the fake's floor, as the engine's walls do)
    -- 20u, out of a door region that ends 70u off the wall. His measured facing faces the door; but the gate never
    ran where the push left him, so that is no measured miss: ``faced`` False (nothing judged), ``face_moved`` the
    20u the report witnessed."""
    zone = [[600, -150], [600, 150], [530, 150], [530, -150]]
    fake = _s90(_gated_room(game, [{"zone": zone, "to": None, "face": True}]))
    with session(game, fake) as g:
        _gated_start(g, fake, (540, 0), yaw=-90.0)
        record = {"faced": False, "face_measured": False, "face_err": None, "face_worst": None, "face_calls": None,
                  "face_pad": None, "face_moved": None}
        got = g._turn_to_the_door(zone, record, 30820, (48, 208), 3.0)
    assert got is None and fake.player[0] == pytest.approx(520.0, abs=1.0), (got, fake.player)
    assert record["face_moved"] == pytest.approx(20.0, abs=1.0), record
    assert (record["faced"], record["face_measured"], record["face_err"]) == (False, False, None), record


def test_at_350s_door_to_353_an_s90_engine_faces_the_goal_pocket_the_slide_bound_refused(game, dali):
    """The case the open loop PINS unfaced (test_at_350s_door_to_353_the_slide_bound_leaves_the_goal_unfaced): stock
    350's door to 353 is standable only in a 34u pocket by its corner, where every facing PRESS's wall-slide bound
    reaches out of the region. Standing in that pocket where his centre can stand -- the spot nearest the tour's goal
    that is COLLISION_RADIUS_W off every wall (the goal itself is 77u off one: no walk leaves him there, the engine's
    radius pushes him out, and out of the region) -- facing away (yaw 0): on a pre-s90 engine the step presses nothing
    (``faced`` False, the premise), and on one that publishes the facing it turns him where he stands and the door
    fires -- ``faced`` True, measured, not a direction held."""
    from ff9mapkit.content import doorface, pathfind
    from ff9mapkit.scene import cam
    walkmesh, script = dali
    fake, prior = _dali_fake(game, walkmesh, script, 350, face_gates=True)
    places = _dali_places(script, 350)
    wm = walkmesh(350)
    zone, door = places[2], fake.regions[350][2]
    goal = pathfind.region_goal(wm, zone)
    spots = [(x, z) for x in range(goal[0] - 40, goal[0] + 41, 4) for z in range(goal[1] - 40, goal[1] + 41, 4)
             if doorface.region_contains(x, z, door["points"])
             and (wm.distance_to_boundary(x, z) or 0.0) >= cam.COLLISION_RADIUS_W + 1.0]
    spot = min(spots, key=lambda p: (p[0] - goal[0]) ** 2 + (p[1] - goal[1]) ** 2)
    got = {}
    with session(game, fake) as g:
        boot(g)
        g.warp(350)
        _stand(g, fake, *_DALI_STARTS[350])
        g.calibrate_axes(hazards=places, prior=prior)
        for mode in ("absent", "published"):
            fake.facing_mode = mode
            g.warp(350)
            fake._face_deg = 0.0
            _stand(g, fake, *spot)                      # published after the mode is set: the facing, or no key
            mark, fired = len(fake.executed), len(fake.fired)
            rec = g.route_cross(spot[0], spot[1], avoid=[z for z in places if z is not zone], walkmesh=wm,
                                prior=prior, unstick=True, zone=zone, smooth=True, npcs=True, timeout=2,
                                gate=door["face"], region=door["points"])
            got[mode] = (rec, [f["to"] for f in fake.fired[fired:]], fake.executed[mark:])
    rec, fired, steps = got["absent"]
    assert rec["faced"] is False and rec["face_pad"] is None and not fired, rec          # the premise: no press fits
    assert not [s for s in steps if s[0] in ("hold", "turn") and s[1] != "cancel"], steps
    rec, fired, steps = got["published"]
    assert fired == [30002] and rec["landed"] == 30002, rec
    assert [s for s in steps if s[0] == "turn"], steps
    assert not [s for s in steps if s[0] in ("hold", "press") and s[1] in ("up", "down", "left", "right")], steps
    assert (rec["during"], rec["faced"], rec["face_measured"], rec["face_moved"]) == ("face", True, True, 0.0), rec


def test_on_stock_350_an_s90_engine_crosses_every_gated_door_with_no_facing_press_moving_him(game, dali):
    """Stock 350 end to end with its facing gates on and the facing published: from the arrival from 351 (his yaw 69,
    back up the street) a smooth route_to every place of the field lands in the region it was sent to, and only there
    -- and the facing step, wherever it runs, never presses a walked step: it turns him in place (the 351 door among
    the doors it opens that way)."""
    from ff9mapkit.content import pathfind
    walkmesh, script = dali
    fake, prior = _dali_fake(game, walkmesh, script, 350, face_gates=True)
    _s90(fake)
    places = _dali_places(script, 350)
    wm, start = walkmesh(350), _DALI_STARTS[350]
    turned, pressed, rows = [], [], []
    with session(game, fake) as g:
        boot(g)
        g.warp(350)
        _stand(g, fake, *start)
        g.calibrate_axes(hazards=places, prior=prior)
        face, press = g._face_the_door, g._pressed
        inside = []

        def spy_face(*a, **kw):
            inside.append(True)
            try:
                return face(*a, **kw)
            finally:
                inside.pop()

        def spy_press(*a, **kw):
            if inside:
                pressed.append(a[2:])
            return press(*a, **kw)
        g._face_the_door, g._pressed = spy_face, spy_press
        for i, zone in enumerate(places):
            g.warp(350)
            _stand(g, fake, *start)
            fake._face_deg = 69.0
            fired, mark = len(fake.fired), len(fake.executed)
            goal = pathfind.region_goal(wm, zone)
            door = fake.regions[350][i]
            rec = g.route_to(goal[0], goal[1], avoid=[z for z in places if z is not zone], walkmesh=wm, prior=prior,
                             smooth=True, zone=zone, face=door.get("points") if door.get("face") else None,
                             face_window=door.get("face"))
            assert [f["to"] for f in fake.fired[fired:]] == [30000 + i] and rec["landed"] == 30000 + i, (i, rec)
            if rec["during"] == "face":
                rows.append((i, rec.get("face_measured"), _pads_turned(fake, mark)))
                turned.append(i)
    assert sum(1 for r in fake.regions[350] if r.get("face")) == 5, "premise: the gates are on"
    assert not pressed, pressed                       # no facing step pressed a walked step, on any door
    assert 0 in turned, turned
    assert all(measured is True and pads for _i, measured, pads in rows), rows


# --- the closed loop's review (each a case that once went wrong, or that nothing pinned) ---
def _east_record():
    """A facing-step record as :meth:`Session._face_the_door` hands :meth:`Session._turn_to_the_door` one."""
    return {"faced": False, "face_measured": False, "face_err": None, "face_worst": None, "face_calls": None,
            "face_pad": None, "face_moved": None}


def test_a_turn_that_ran_no_movepc_call_is_turned_again_for_longer_never_read_as_settled(game):
    """A turn's MovePC calls come whole, on 30 Hz ticks paced by the wall clock: on a display fast enough its 8 frames
    fall between two ticks and no call runs -- the ``turn_end``'s yaw is its yaw0 to the print. That is no pad that
    has SETTLED (it proves nothing ran), and no basis may be read off it (it would say the pad heads 150 degrees off
    its calibration, and send the next turn away from the door): the same pad is turned again for twice the frames,
    and the door fires on that turn."""
    door = {"zone": _EAST_DOOR, "to": 30821, "arrive": (0, 0), "face": True}
    fake = _s90(_gated_room(game, [door]))
    fake.turn_calls = 0.0                                   # no tick falls in the first turn's frames
    _on_turns(fake, (1, 9, lambda: setattr(fake, "turn_calls", None)))     # its keys are up by then
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=60.0)
        mark = len(fake.executed)
        rec = _here_cross(g, _EAST_DOOR)
    first = _turn_ends(fake)[0]
    assert (first["why"], first["yaw0"], first["yaw"]) == ("ended", "60", "60"), first      # the premise
    turns = [s for s in fake.executed[mark:] if s[0] == "turn"]
    assert [s[1] for s in turns] == ["right", "right"] and turns[1][2] == "16", turns
    assert rec["landed"] == 30821 and rec["during"] == "face" and rec["face_measured"] is True, rec
    assert not _direction_holds(fake, mark), fake.executed[mark:]


def test_a_pad_that_already_heads_where_he_stands_settles_on_its_one_longer_turn(game):
    """The other reading of a turn that moves his yaw not at all: the pad already heads where he stands. The basis is
    100 degrees off the field's (the fake's twist) and he already faces right's TRUE heading, 100 degrees off the
    door: right's turn leaves his yaw exactly where it was. The one longer turn tells the two apart -- unmoved again,
    so right heads there and SETTLES -- and the next pad, ranked by the heading it measured, faces the door: right,
    right, down. The ambiguity costs one turn, never the step."""
    from ff9mapkit.content import doorface
    door = {"zone": _EAST_DOOR, "to": 30821, "arrive": (0, 0), "face": True}
    fake = _s90(_gated_room(game, [door]))
    a = math.radians(100.0)
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=doorface.yaw_of(math.cos(a), math.sin(a)))      # right, twisted
        fake.twist = 100.0
        mark = len(fake.executed)
        rec = _here_cross(g, _EAST_DOOR)
    turns = [s for s in fake.executed[mark:] if s[0] == "turn"]
    assert [s[1] for s in turns] == ["right", "right", "down"] and turns[1][2] == "16", turns
    assert [e["yaw"] == e["yaw0"] for e in _turn_ends(fake)][:2] == [True, True], _turn_ends(fake)
    assert rec["landed"] == 30821 and rec["during"] == "face" and rec["face_pad"] == "down", rec


@pytest.mark.parametrize("phase", [0, 1])
def test_a_turn_in_whole_calls_that_lands_out_of_the_window_turns_again(game, phase):
    """The engine's own call model (the fake's ``tick_phase``): one WHOLE call a 30 Hz tick, four in a turn's 8
    frames, in either phase. On a narrow gate -- (8, 248): 7 units either way -- the first turn leaves him 14 units off
    the door (out of the window; it moved his yaw, so the pad has more to give) and the second 2 units off: the same
    pad twice, and ``faced`` True on the engine's report."""
    from ff9mapkit.content import doorface
    fake = _s90(_gated_room(game, [{"zone": _EAST_DOOR, "to": None, "face": True}]))
    fake.tick_phase, fake.turn_calls = phase, 0.5
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=60.0)
        mark = len(fake.executed)
        rec = _here_cross(g, _EAST_DOOR, gate=(8, 248))
    assert _pads_turned(fake, mark) == ["right", "right"], fake.executed[mark:]
    assert fake._face_deg == pytest.approx(doorface.turn_step(60.0, -90.0, 8), abs=0.01)
    assert (rec["faced"], rec["face_measured"]) == (True, True) and abs(rec["face_err"]) <= 7, rec


def test_turns_that_never_reach_the_window_end_live_never_a_miss(game):
    """Every turn moves his yaw (a machine spending a sixth of a call a turn: never settled) and none reaches the
    window: ROUTE_TURN_TRIES turns, then the step ends -- ``faced`` False, measured (the reports were judged), the
    last measured error out of the window -- and the tour reads LIVE, never the dead door's REAL miss."""
    D = _tour_module()
    fake = _s90(_gated_room(game, [{"zone": _EAST_DOOR, "to": None, "face": True}]))
    fake.turn_calls = 0.02
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=90.0)
        mark = len(fake.executed)
        rec = _here_cross(g, _EAST_DOOR)
        tries = g.ROUTE_TURN_TRIES
    assert _pads_turned(fake, mark) == ["right"] * tries, fake.executed[mark:]
    assert (rec["faced"], rec["face_measured"]) == (False, True) and abs(rec["face_err"]) > 47, rec
    assert D.failure(rec) == "live", rec


def test_no_pad_heading_within_a_narrow_window_turns_nothing_and_is_live(game):
    """A gate of (8, 248) -- 7 units, 9.8 degrees either way -- on a basis whose every pad heads 22.5 degrees off the
    door's bearing: no pad can face it, so nothing is turned -- ``faced`` False, and the tour reads LIVE."""
    from harness.session import _turn
    D = _tour_module()
    fake = _s90(_gated_room(game, [{"zone": _EAST_DOOR, "to": None, "face": [8, 248]}]))
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=90.0)
        b = dict(g._axes[30820])
        b["v"], b["h"] = _turn(b["v"], math.radians(22.5)), _turn(b["h"], math.radians(22.5))
        g._axes[30820] = b
        mark = len(fake.executed)
        rec = _here_cross(g, _EAST_DOOR, gate=(8, 248))
    assert not _pads_turned(fake, mark) and not _direction_holds(fake, mark), fake.executed[mark:]
    assert rec["faced"] is False and rec["face_pad"] is None and D.failure(rec) == "live", rec


@pytest.mark.parametrize("v,faced", [(47, True), (48, False), (208, False), (209, True)])
def test_a_measured_byte_on_the_windows_edge_is_judged_by_the_gates_strict_compare(game, v, faced):
    """The stock gate is STRICT (B_LT / B_GT): 48 and 208 themselves are shut, 47 and 209 open. A turn whose reported
    byte puts the gate value on either edge is judged exactly so -- 48 / 208 turned again (never a REAL miss), 47 /
    209 a measured miss of +47 / -47."""
    from ff9mapkit.content import doorface
    fake = _s90(_gated_room(game, [{"zone": _EAST_DOOR, "to": None, "face": True}]))
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=90.0)
        st = g.state
        jx, jz = doorface.calc_exit_position(st.player_x, st.player_z, _EAST_DOOR[0], _EAST_DOOR[1])
        face = (doorface.eb_bearing(jx - round(st.player_x), jz - round(st.player_z)) + v) & 255
        assert doorface.gate_value_from_face(st.player_x, st.player_z, face, *_EAST_DOOR[:2]) == v    # the premise
        asked = []

        def turned(buttons, frames, **kw):
            asked.append(buttons)
            return {"frame": 1, "why": "ended", "frames": frames, "yaw0": 90.0, "yaw": -80.0, "face": face,
                    "moved": 0.0}
        g.turn_in_place = turned
        record = _east_record()
        g._turn_to_the_door(_EAST_DOOR, record, 30820, (48, 208), 2.0)
    assert record["faced"] is faced and record["face_err"] == doorface.signed_error(v), record
    assert len(asked) == (1 if faced else g.ROUTE_TURN_TRIES), asked


def test_a_turn_the_engine_has_no_verb_for_falls_back_to_the_press_at_once(game):
    """A sample published a facing, and the agent answers the turn ``unknown op 'turn'`` all the same (an engine
    without s90, whatever a sample said): a press does not share that, so it is the step at once -- one turn asked,
    then the walked press, which faces the door (``face_measured`` False: its prediction)."""
    door = {"zone": _EAST_DOOR, "to": 30821, "arrive": (0, 0), "face": True}
    fake = _s90(_gated_room(game, [door]))

    def no_verb(*a, **kw):
        raise RuntimeError("unknown op 'turn'")
    fake._begin_turn = no_verb
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=90.0)
        mark = len(fake.executed)
        rec = _here_cross(g, _EAST_DOOR)
    assert _pads_turned(fake, mark) == ["right"] and _direction_holds(fake, mark), fake.executed[mark:]
    assert rec["landed"] == 30821 and rec["during"] == "face" and rec["face_measured"] is False, rec


@pytest.mark.parametrize("stays", [True, False])
def test_a_body_he_overlaps_is_waited_for_once_and_the_press_is_the_step_only_if_it_stays(game, stays):
    """``overlapping object uid N`` -- the s90 contract's action is "step clear of that body first". A body that is
    only passing (``stays`` False: gone before the wait is out) is waited for, and the turn asked again faces the
    door: no walked step. One that stays on him refuses the second turn too, for the same uid, and then the walked
    press -- planned to move him clear of the objects -- is the step (``face_measured`` False)."""
    door = {"zone": _EAST_DOOR, "to": 30821, "arrive": (0, 0), "face": True}
    fake = _s90(_gated_room(game, [door]))
    execute, asked = fake._execute, []

    def passing(step):
        if step[0] == "turn":
            asked.append(fake.frame)
            if len(asked) == 2 and not stays:
                fake.blockers = {}                                        # it walked on during the wait
        return execute(step)
    fake._execute = passing
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=90.0)
        fake.blockers = {30820: [{"x": 420.0, "z": 60.0, "r": 70.0, "uid": 150}]}     # 67u from him: on him
        mark = len(fake.executed)
        rec = _here_cross(g, _EAST_DOOR, npcs=False)
    assert _pads_turned(fake, mark) == ["right", "right"], fake.executed[mark:]
    assert asked[1] - asked[0] >= g._frames_lasting(g.ROUTE_WAIT_SECONDS), asked        # waited out in between
    refused = [e["message"] for e in _logged(fake, "error") if e.get("op") == "turn"]
    assert all(m.startswith("overlapping object uid 150 ") for m in refused), refused
    if stays:
        assert len(refused) == 2 and _direction_holds(fake, mark), (refused, fake.executed[mark:])
        assert rec["face_measured"] is False, rec
    else:
        assert len(refused) == 1 and not _direction_holds(fake, mark), (refused, fake.executed[mark:])
        assert rec["landed"] == 30821 and rec["during"] == "face" and rec["face_measured"] is True, rec


@pytest.mark.parametrize("live", [True, False])
def test_control_taken_and_given_back_on_the_same_field_is_a_cut_not_the_door(game, live):
    """Something takes control a frame into the first turn and hands it back 20 frames on, the field unchanged: a talk,
    an ATE, a timed script -- ``control`` is not proof a door fired. The turn is cut, waited out and asked again,
    never landed as the door: a live door fires on the next turn; a dead one is the measured REAL miss."""
    door = {"zone": _EAST_DOOR, "to": 30821 if live else None, "arrive": (0, 0), "face": True}
    fake = _s90(_gated_room(game, [door]))
    _on_turns(fake, (1, 1, lambda: setattr(fake, "control", False)), (1, 21, lambda: setattr(fake, "control", True)))
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=90.0)
        mark = len(fake.executed)
        rec = _here_cross(g, _EAST_DOOR)
    assert _turn_ends(fake)[0]["why"] == "control" and len(_pads_turned(fake, mark)) == 2, fake.executed[mark:]
    if live:
        assert [f["to"] for f in fake.fired] == [30821] and rec["landed"] == 30821, rec
        assert rec["during"] == "face" and rec["face_measured"] is True, rec
    else:
        assert rec["during"] is None and rec["landed"] is None and not fake.fired, rec
        assert (rec["faced"], rec["face_measured"]) == (True, True) and abs(rec["face_err"]) <= 47, rec


@pytest.mark.parametrize("how", ["refused", "cut"])
def test_control_gone_for_good_on_an_unchanged_field_is_no_door_and_no_strike(game, how):
    """Control goes and never comes back, and the field never changes: a talk box waiting for Confirm, a scene -- the
    s90 contract: ``control`` is not proof a door fired; the field changing is. Taken on the frame the first turn is
    asked for (``refused``: the agent refuses it, nothing is turned) or two frames into it (``cut``): landed as the
    walk's loss of control is (``during`` "face"), but ``faced`` False and nothing measured -- the tour reads LIVE,
    never the door's REAL miss."""
    D = _tour_module()
    fake = _s90(_gated_room(game, [{"zone": _EAST_DOOR, "to": None, "face": True}]))
    if how == "refused":
        execute = fake._execute

        def take(step):
            if step[0] == "turn":
                fake.control = False
            return execute(step)
        fake._execute = take
    else:
        _on_turns(fake, (1, 2, lambda: setattr(fake, "control", False)))
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=90.0)
        # the budget covers route_to's own start (control held a whole Session.SETTLE, 1 s) before the wait for control
        # to come back: 1 s left no room for the first, and a loaded suite (-n 6 beside other runs) timed it out there
        rec = _here_cross(g, _EAST_DOOR, timeout=3)
    assert not fake.control and not fake.fired, "premise: control gone, the field unchanged"
    assert rec["during"] == "face" and rec["landed"] is None, rec
    assert (rec["faced"], rec["face_measured"], rec["face_err"]) == (False, False, None), rec
    assert (rec["face_pad"] is None) == (how == "refused"), rec
    assert D.failure(rec) == "live", rec


@pytest.mark.parametrize("cut", ["movement", "hud"])
def test_a_turn_cut_before_the_field_judged_it_is_turned_again_never_judged_on_its_byte(game, cut):
    """A hold on movement (control kept) or a UI over the field lands six frames into the first turn: the agent CUTS
    it (``turn_end`` ``movement`` / ``hud``) before the field had its passes on the facing. Its byte is judged by no
    one: the cut is waited out and the pad turned again, and the dead door's REAL miss is scored on the second turn's
    report -- never on the cut one."""
    fake = _s90(_gated_room(game, [{"zone": _EAST_DOOR, "to": None, "face": True}]))
    if cut == "movement":
        _on_turns(fake, (1, 6, lambda: setattr(fake, "_frozen_until", fake.frame + 20)))
    else:
        _on_turns(fake, (1, 6, lambda: setattr(fake, "ui_state", "MainMenu")),
                  (1, 36, lambda: setattr(fake, "ui_state", "FieldHUD")))
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=90.0)
        mark = len(fake.executed)
        rec = _here_cross(g, _EAST_DOOR)
    ends = _turn_ends(fake)
    assert ends[0]["why"] == cut and ends[-1]["why"] == "ended", ends
    assert _pads_turned(fake, mark) == ["right", "right"], fake.executed[mark:]
    assert (rec["faced"], rec["face_measured"]) == (True, True) and abs(rec["face_err"]) <= 47, rec


@pytest.mark.parametrize("human", ["stick", "path"])
def test_a_human_at_the_controls_ends_the_step_never_fought(game, human):
    """A physical stick over the threshold (``a physical stick or key is pushing the axis``) or a mouse walk pending
    (``a click-to-move path is pending``): a human at the controls. The step is not fought -- one turn asked, nothing
    turned or pressed after it -- and ends ``faced`` False, LIVE. The stick cuts a turn already open the same way
    (``turn_end`` ``axis``)."""
    D = _tour_module()
    fake = _s90(_gated_room(game, [{"zone": _EAST_DOOR, "to": None, "face": True}]))
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=90.0)
        if human == "stick":
            fake.stick = 0.8
        else:
            fake.click_path = True
        mark = len(fake.executed)
        rec = _here_cross(g, _EAST_DOOR)
    assert _pads_turned(fake, mark) == ["right"] and not _direction_holds(fake, mark), fake.executed[mark:]
    assert rec["faced"] is False and D.failure(rec) == "live", rec
    fake = _s90(_gated_room(game, [{"zone": _EAST_DOOR, "to": None, "face": True}]))
    _on_turns(fake, (1, 3, lambda: setattr(fake, "stick", 0.8)))
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=90.0)
        mark = len(fake.executed)
        rec = _here_cross(g, _EAST_DOOR)
    assert [e["why"] for e in _turn_ends(fake)] == ["axis"], _turn_ends(fake)
    assert _pads_turned(fake, mark) == ["right"] and not _direction_holds(fake, mark), fake.executed[mark:]
    assert rec["faced"] is False and D.failure(rec) == "live", rec


def test_a_refusal_is_classified_from_the_acking_sample_not_a_second_read(game):
    """A hold on movement lands on the frame the first turn is asked for, and the agent refuses it -- a refusal the
    step waits out -- and the one read of state.json after the refusal comes back None, as a healthy game's
    mid-rewrite read can. The refusal is still a TurnRefused (read off the sample that acked it), waited out, and the
    door fires on the next turn: never a plain error out of route_cross, which the tour scores a REAL miss."""
    door = {"zone": _EAST_DOOR, "to": 30821, "arrive": (0, 0), "face": True}
    fake = _s90(_gated_room(game, [door]))
    execute, froze = fake._execute, []

    def freeze_first_turn(step):
        if step[0] == "turn" and not froze:
            froze.append(fake.frame)
            fake._frozen_until = fake.frame + 40
        return execute(step)
    fake._execute = freeze_first_turn
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=90.0)
        send, state, torn = g.send, g.channel.state, []

        def spy_send(*steps, **kw):
            try:
                return send(*steps, **kw)
            except HarnessError:
                if any(s.startswith("turn ") for s in steps):
                    torn.append(True)
                raise

        def spy_state(*a, **kw):
            if torn and torn[-1] is True:
                torn[-1] = "torn"
                return None                        # one mid-rewrite read, right after the refusal
            return state(*a, **kw)
        g.send, g.channel.state = spy_send, spy_state
        rec = _here_cross(g, _EAST_DOOR)
    assert froze and torn == ["torn"], torn
    assert rec["landed"] == 30821 and rec["during"] == "face" and rec["face_measured"] is True, rec


def test_a_ui_over_the_field_at_the_turn_is_the_agents_hud_refusal(game):
    """A UI that comes up between the step's own look and the turn: the AGENT refuses the turn (TurnBlocker ``hud``)
    and turn_in_place raises that refusal -- ``blocked``, ``hud`` -- which the step waits out like any, never the field
    verbs' world-map error. Nothing is turned."""
    from harness.channel import TurnRefused
    fake = _s90(FakeGame(game))
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, 100, 50)
        fake.ui_state = "MainMenu"
        published(g, lambda s: s.ui_state == "MainMenu")
        with pytest.raises(TurnRefused) as got:
            g.turn_in_place("right", 8)
        asked = [s[0] for s in fake.executed[-2:]]
    assert (got.value.kind, got.value.why) == ("blocked", "hud"), got.value
    assert fake._turn_open is None and asked == ["turn", "wait"], asked


def test_a_press_after_a_turn_plans_from_any_yaw_and_measures_nothing(game):
    """He walks into the east door from the south (the walk's last hold is up: its yaw is known), and the first turn
    in place moves his yaw toward the door and ends out of the window. A body then stands on him and stays: the next
    turn is refused for it twice, and the walked press is the step. The press decides from scratch: the turn moved his
    yaw off where the walk's hold left it, so it plans from ANY yaw (no predicted ``face_err``), and nothing the turn
    measured is its verdict (``face_measured`` False)."""
    door = {"zone": _EAST_DOOR, "to": 30821, "arrive": (0, 0), "face": True}
    fake = _s90(_gated_room(game, [door]))
    fake.turn_calls = 1.0 / 16                       # half a call a turn: from up, 50 units off the door

    def a_body_on_him():                             # on the lift frame: the turn is over, the next one not asked
        fake.blockers = {30820: [{"x": fake.player[0] - 30.0, "z": fake.player[2], "r": 60.0, "uid": 151}]}
    _on_turns(fake, (1, 9, a_body_on_him))
    with session(game, fake) as g:
        _gated_start(g, fake, (410, -450))
        mark = len(fake.executed)
        rec = g.route_cross(410.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), unstick=True, zone=_EAST_DOOR,
                            smooth=True, npcs=False, timeout=3, gate=[48, 208])
    assert _pads_turned(fake, mark) == ["right"] * 3, fake.executed[mark:]    # turned; refused twice for the body
    assert [e["why"] for e in _turn_ends(fake)] == ["ended"] and _direction_holds(fake, mark), fake.executed[mark:]
    assert rec["landed"] == 30821 and rec["during"] == "face" and rec["faced"] is True, rec
    assert rec["face_measured"] is False and rec["face_err"] is None, rec


def test_turn_in_place_asks_again_for_a_report_a_collided_append_held_back(game):
    """The agent's event append can COLLIDE with the driver's read of the log; it keeps the rows and writes them with
    its NEXT event (HarnessAgent.FlushEvents) -- so a turn's ``turn_end`` can sit unwritten with nothing else to log.
    turn_in_place asks once more (a ``wait 1``, whose own receipt flushes it) before it gives up, and returns that
    turn's report."""
    fake = _s90(FakeGame(game))
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, 100, 50)
        fake._face_deg = 90.0
        fake.event_collisions = {"turn_end": 1}
        end = g.turn_in_place("right", 8)
        steps = [s for s in fake.executed if s[0] == "wait"]
    assert (end["why"], end["frames"], end["yaw0"]) == ("ended", 8, 90.0), end
    assert steps[-1] == ["wait", "1"], steps


def test_turn_in_place_reads_only_the_report_after_its_own_receipt(game):
    """A turn_end from an EARLIER turn -- held back by a collided append and flushed with this request's receipt --
    lands in the log after the driver's mark and BEFORE this request's ``accepted`` row. It is not this turn's:
    turn_in_place returns the report that follows its own receipt."""
    fake = _s90(FakeGame(game))
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, 100, 50)
        fake._face_deg = 90.0
        event, stale = fake._event, []

        def flush_a_stale_report_first(kind, **kv):
            if kind == "accepted" and not stale:
                stale.append(True)
                event("turn_end", why="control", frames=999, yaw0="0", yaw=None, face=None, moved=None)
            return event(kind, **kv)
        fake._event = flush_a_stale_report_first
        end = g.turn_in_place("right", 8)
    assert stale and (end["why"], end["frames"]) == ("ended", 8), end


def test_turn_in_place_waits_for_its_own_receipt_before_reading_any_report(game):
    """The other order: an EARLIER turn's report is in the log after the driver's mark, and this request's own
    ``accepted`` row is the one a collided append held back (HarnessAgent.FlushEvents writes it with the next event) --
    as is every row after it, this turn's report too, until the receipt of turn_in_place's own ``wait 1`` flushes
    them all. With no receipt to read after, turn_in_place waits for it -- it never takes the report it can see for
    its own."""
    fake = _s90(FakeGame(game))
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, 100, 50)
        fake._face_deg = 90.0
        event, stale, holding = fake._event, [], []

        def a_stale_report_then_a_held_receipt(kind, **kv):
            if kind == "accepted" and not stale:
                stale.append(True)
                event("turn_end", why="control", frames=999, yaw0="0", yaw=None, face=None, moved=None)
                holding.append(True)
            elif holding and kind == "accepted":
                holding.clear()                       # the nudge's receipt: its append flushes every held row
            if holding:
                fake.event_collisions[kind] = fake.event_collisions.get(kind, 0) + 1
            return event(kind, **kv)
        fake._event = a_stale_report_then_a_held_receipt
        end = g.turn_in_place("right", 8)
    assert stale and (end["why"], end["frames"]) == ("ended", 8), end


def test_the_fake_keeps_the_agents_frame_rule_and_its_direction_aliases(game):
    """The fake's input as the agent keys it. A ``release`` lands NEXT frame (HarnessAgent `release`: A RELEASE MUST
    NEVER PRESS, and a key down now stays down this frame), so ``release up`` then ``turn up`` in ONE request is
    refused -- a frame later it is not. The direction aliases are the Controls they name (ParseControl): a turn is
    refused while ``hold north`` is down, and ``hold north`` is refused while a turn is open."""
    fake = _s90(_hand_fake(game, at=(100.0, 50.0), yaw=90.0))

    def refused(step, match):
        with pytest.raises(RuntimeError, match=match):
            fake._execute(step)
    fake._execute(["hold", "up", "30"])
    _hand_frames(fake, 2)
    fake._execute(["release", "up"])
    refused(["turn", "up", "8"], r"^Up is held or scheduled")
    _hand_frames(fake, 1)
    fake._execute(["turn", "up", "8"])                                   # a frame on: Up has lifted
    refused(["hold", "north", "3"], r"^a `turn` is still open")
    fake = _s90(_hand_fake(game, at=(100.0, 50.0), yaw=90.0))
    fake._execute(["hold", "north", "30"])
    refused(["turn", "east", "8"], r"^Up is held or scheduled")
    _hand_frames(fake, 3)
    assert fake.player[2] > 50.0, fake.player                             # `hold north` walks him up, as Up does


# --------------------------------------------------------------------------- route_to(npcs=True)
# The owner, on the blind tour that found Dali's villagers by walking into them: "other maps may not be as forgiving
# as this one, it could cause a true movement lock". memoria-patch s89 publishes every other actor on the field;
# these pin the router that plans round them: never a leg through a body, a SOLID one never pushed and a seal by
# solids "blocked", a contact trigger kept out of while a way exists and entered -- and recorded -- only when none
# does, a walker re-planned round a bounded number of times, and an engine that cannot (or could not) list them
# walked exactly as unstick walks, never as an empty field.


def _villager(x, z, **kw):
    """A published body as the fake models it: 350's villagers (SetObjectLogicalSize 14, with Zidane's 24: r 152)."""
    return dict({"x": float(x), "z": float(z), "r": 152.0}, **kw)


def test_state_tells_an_engine_that_cannot_from_one_that_does_not_know_from_a_list():
    """s89's three cases, kept apart: the key ABSENT (an engine without s89), null (it could not say), a list. Only
    the last reads as a list -- "unknown" read as [] would plan a leg straight through a solid body -- and [] is a
    real answer: a field with no other actor."""
    old = State({"frame": 1})
    assert (old.objects_status, old.objects, old.pushout) == ("cannot", None, None)
    unknown = State({"frame": 1, "objects": None, "pushout": None})
    assert (unknown.objects_status, unknown.objects, unknown.pushout) == ("unknown", None, None)
    po = {"slock": -3, "scoll": 2, "slockfree": 1, "fallback": True}
    empty = State({"frame": 1, "objects": [], "pushout": po})
    assert (empty.objects_status, empty.objects, empty.pushout) == ("listed", [], po)
    one = State({"frame": 1, "objects": [{"uid": 3, "x": 1.0, "y": 0.0, "z": 2.0, "r": 152}], "pushout": po})
    assert one.objects_status == "listed" and [o["uid"] for o in one.objects] == [3]


def test_the_fake_publishes_its_bodies_as_s89_objects(game):
    """The stand-in's half of the contract: every body on the field in s89's shape -- a tuple one too -- with its
    solidity, walk-through, trigger radii (``range_r`` only while it collides), height and walking; ``pushout``
    beside it; null in the "null" mode and off a field, and no key at all in the "absent" mode."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -500, -500)
        fake.blockers = {30820: [(0.0, 300.0, 152.0, True),
                                 _villager(300, 0, uid=200, sid=12, range_r=314.0, talk_r=280.0),
                                 _villager(-300, 0, coll=False, range_r=300.0, talk_r=200.0),
                                 _villager(0, -300, y=-500.0, path=[(0, -300), (0, -400)], speed=5)]}
        st = published(g, lambda s: s.objects is not None and len(s.objects) == 4)
        a, b, c, d = st.objects
        assert set(a) == {"uid", "sid", "x", "y", "z", "range", "talk", "r", "solid", "coll", "range_r", "talk_r",
                          "shown", "moving", "flags"}
        assert (a["uid"], a["r"], a["solid"], a["coll"], a["range"], a["range_r"], a["moving"]) == \
            (128, 152.0, True, True, False, None, False)
        assert (b["uid"], b["sid"], b["range"], b["talk"], b["range_r"], b["talk_r"]) == (200, 12, True, True, 314.0, 280.0)
        assert (c["coll"], c["solid"], c["range"], c["range_r"], c["talk_r"]) == (False, False, True, None, 200.0)
        assert d["moving"] and d["y"] == -500.0
        assert st.objects_status == "listed" and set(st.pushout) == {"slock", "scoll", "slockfree", "fallback"}
        fake.objects_mode = "null"
        assert published(g, lambda s: s.objects_status == "unknown").pushout is None
        fake.objects_mode = "absent"
        assert "pushout" not in published(g, lambda s: s.objects_status == "cannot").raw
        fake.objects_mode = "listed"
        fake.ui_state = "WorldHUD"                          # off a field: null, never a list
        published(g, lambda s: s.on_world and s.objects_status == "unknown")


def test_the_obstacles_are_the_engines_own_radii_in_its_own_dy_band(game):
    """The obstacle model (_npc_discs), on the published fields alone: a body is its ``r`` -- the centre distance the
    engine keeps him at -- planned ROUTE_BODY_MARGIN wider; a Range is its ``range_r``, or its ``talk_r`` where that
    is larger and the entry talks too (the talk search then requests the Range), planned the call's zone margin
    wider; a walk-through object is no body, and a trigger only through the talk search; nothing 400 or more away
    in y is anything; and a disc he stands within shrinks to his distance -- a route may leave it, never go deeper."""
    g = session(game, None)
    far = 2000.0

    def obj(uid, x, z, **kw):
        return dict({"uid": uid, "sid": uid, "x": x, "y": 0.0, "z": z, "r": 152.0, "coll": True, "solid": False,
                     "range": False, "talk": False, "range_r": None, "talk_r": None, "moving": False}, **kw)
    objs = [obj(1, far, 0, solid=True, talk=True, talk_r=250.0),                    # talks, no Range: a body only
            obj(2, -far, 0, r=224.0, range=True, talk=True, range_r=314.0, talk_r=400.0),
            obj(3, 0, far, coll=False, range=True, talk=True, talk_r=260.0),          # walk-through, talks, Range
            obj(4, 0, -far, coll=False, talk=True, talk_r=260.0),                     # walk-through, talks: nothing
            obj(5, far, far, y=-400.0),                                               # another floor: nothing
            obj(6, 0, 100)]                                                           # 100u away: he is inside it
    by = {(d["uid"], d["via"]): d for d in g._npc_discs(objs, (0.0, 0.0), 0.0, 56.0)}
    assert set(by) == {(1, "body"), (2, "body"), (2, "talk"), (3, "talk"), (6, "body")}, set(by)
    assert (by[1, "body"]["R"], by[1, "body"]["P"], by[1, "body"]["solid"]) == (152.0, 152.0 + g.ROUTE_BODY_MARGIN, True)
    assert (by[2, "body"]["R"], by[2, "talk"]["kind"], by[2, "talk"]["R"], by[2, "talk"]["P"]) == (224.0, "trigger",
                                                                                                400.0, 456.0)
    assert (by[3, "talk"]["R"], by[3, "talk"]["pad"]) == (260.0, g.PROBE_HAZARD_PAD)
    assert by[6, "body"]["inside"] and by[6, "body"]["P"] == 99.5 and not by[1, "body"]["inside"]


@pytest.mark.parametrize("smooth", [False, True])
def test_route_to_npcs_plans_round_a_published_body_and_never_bumps_it(game, smooth):
    """THE 350 VILLAGER, published: the blind walk presses into him (and waits, and pushes -- the premise); the
    NPC-aware plan goes round him -- no contact, no wait, no push -- and names him in ``avoided``."""
    fake = FakeGame(game)
    fake.blockers = {30820: [_villager(0, 0, uid=140)]}
    wm = _flat_bgi()
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -400, 0)
        g.ROUTE_WAIT_SECONDS = 0.5
        blind = g.route_to(400.0, 0.0, walkmesh=wm, prior=_prior(), unstick=True, smooth=smooth)
        assert blind["reached"] and blind["pushes"] == 1 and fake.contacts, blind
        assert blind["npcs"] is None and (blind["avoided"], blind["npc_replans"]) == ([], 0), blind
        _stand(g, fake, -400, 0)
        mark = len(fake.contacts)
        rec = g.route_to(400.0, 0.0, walkmesh=wm, prior=_prior(), npcs=True, smooth=smooth)
        assert rec["reached"] and rec["npcs"] == "listed" and len(rec["waypoints"]) > 1, rec
        assert fake.contacts[mark:] == [], fake.contacts[mark:]
        assert (rec["waits"], rec["pushes"], rec["blockers"], rec["through"], rec["entered"]) == (0, 0, [], [], []), rec
        assert [(o["uid"], o["kind"], o["radius"]) for o in rec["avoided"]] == [(140, "body", 152)], rec


@pytest.mark.parametrize("smooth", [False, True])
def test_a_solid_object_is_never_pushed_through_and_solids_that_seal_the_way_are_blocked(game, smooth):
    """A SOLID body across a lane too narrow to pass it (object flag 16: the engine never lets him through): the plan
    knows at once that no way goes round it -- ``blocked``, the body named in ``sealed``, not a hold pressed and
    nothing waited on. The same body without the flag is the push the planner falls back to: the route goes
    through him (``through``), one push, reached."""
    fake = FakeGame(game)
    fake.walkmesh = _LANE
    wm = _flat_bgi(*_LANE)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -400, 0)
        g.calibrate_axes(hazards=[], prior=_prior())
        _stand(g, fake, -400, 0)
        fake.blockers = {30820: [_villager(0, 0, uid=150, solid=True)]}
        published(g, lambda s: s.objects and s.objects[0]["solid"])
        g.ROUTE_WAIT_SECONDS = 0.5
        sent = _counting(g)
        rec = g.route_to(400.0, 0.0, walkmesh=wm, prior=_prior(), npcs=True, smooth=smooth)
        assert rec["blocked"] and rec["waypoints"] is None and not rec["reached"] and not rec["frozen"], rec
        assert [(o["uid"], o["solid"]) for o in rec["sealed"]] == [(150, True)], rec
        assert (rec["waits"], rec["pushes"], rec["blockers"]) == (0, 0, []), rec
        assert not [s for s in sent if any(x.startswith("hold ") for x in s)], sent
        fake.blockers = {30820: [_villager(0, 0, uid=150)]}
        published(g, lambda s: s.objects and not s.objects[0]["solid"])
        rec = g.route_to(400.0, 0.0, walkmesh=wm, prior=_prior(), npcs=True, smooth=smooth)
        assert rec["reached"] and [o["uid"] for o in rec["through"]] == [150], rec
        assert (rec["pushes"], rec["pushed"], rec["sealed"], rec["blocked"]) == (1, 1, [], False), rec


def test_the_push_is_never_pressed_into_a_published_solid_object(game):
    """The ladder's own guard, whatever the plan was: standing against a SOLID published object _push_through presses
    nothing -- not even its two-frame probe -- and counts no push; against the same body non-solid it pushes, as it
    always has; and a push whose line runs on into a trigger beyond is not pressed either."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -300, -300)
        g.calibrate_axes(hazards=[], prior=_prior())

        def against(bodies, check):
            fake.blockers = {30820: bodies}
            _stand(g, fake, -152, 0)                             # in contact with the one at the origin
            st = published(g, check)
            watch = g._npc_watch(56.0, {})
            watch["discs"] = g._npc_discs(st.objects, (st.player_x, st.player_z), st.player_y, 56.0)
            record, mark = {"pushes": 0, "pushed": 0}, len(fake.executed)
            got = g._push_through(200.0, 0.0, 30820, [0.0], record, None, watch)
            return got, record, [s for s in fake.executed[mark:] if s[0] == "hold"]

        got, record, holds = against([_villager(0, 0, uid=150, solid=True)], lambda s: s.objects and s.objects[0]["solid"])
        assert (got, record, holds) == ("stuck", {"pushes": 0, "pushed": 0}, []), (got, record, holds)
        got, record, holds = against([_villager(0, 0, uid=150)], lambda s: s.objects and not s.objects[0]["solid"])
        assert got == "pushed" and record == {"pushes": 1, "pushed": 1} and holds, (got, record)
        got, record, holds = against([_villager(0, 0, uid=150), _villager(500, 0, uid=151, range_r=300.0)],
                                     lambda s: s.objects and len(s.objects) == 2)
        assert (got, record, holds) == ("stuck", {"pushes": 0, "pushed": 0}, []), (got, record, holds)


@pytest.mark.parametrize("smooth", [False, True])
def test_a_contact_trigger_is_kept_out_of_while_a_route_exists_and_entered_only_when_none_does(game, smooth):
    """STOCK 350's VIVI: her Range warps the run to 358 from 314u (r 224, speed 30, + 60). A walk that passes within
    that is a crossing the tour never chose. Blind, the straight walk passes her at 200u and is warped (the premise);
    NPC-aware, the plan keeps out of her radius as it keeps out of an exit zone, and nothing fires. Across a lane the
    radius covers wall to wall there is no way round: then -- only then -- the route enters it, and says so."""
    fake = FakeGame(game)
    fake.exit_frames = 20
    vivi = _villager(0, 200, uid=141, r=224.0, range_r=314.0, to=30821, arrive=(0, 0))
    wm = _flat_bgi()
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -450, -300)
        g.calibrate_axes(hazards=[], prior=_prior())
        g.ROUTE_WAIT_SECONDS = 0.5
        _stand(g, fake, -450, 0)
        fake.blockers = {30820: [vivi]}
        blind = g.route_to(450.0, 0.0, walkmesh=wm, prior=_prior(), unstick=True, smooth=smooth)
        assert blind["landed"] == 30821 and [t["uid"] for t in fake.touched] == [141], (blind, fake.touched)
        fake.blockers = {}
        g.warp(30820)
        _stand(g, fake, -450, 0)
        fake.blockers = {30820: [vivi]}
        rec = g.route_to(450.0, 0.0, walkmesh=wm, prior=_prior(), npcs=True, smooth=smooth)
        assert rec["reached"] and rec["landed"] is None and rec["entered"] == [], rec
        assert [t["uid"] for t in fake.touched] == [141], f"fired again: {fake.touched}"
        assert (141, "range") in [(o["uid"], o["kind"]) for o in rec["avoided"]], rec
        fake.blockers = {}
        fake.walkmesh = _LANE
        _stand(g, fake, -450, 0)
        fake.blockers = {30820: [_villager(0, 280, uid=142, range_r=400.0)]}     # beside the lane, its radius across it
        rec = g.route_to(450.0, 0.0, walkmesh=_flat_bgi(*_LANE), prior=_prior(), npcs=True, smooth=smooth)
        assert rec["reached"] and [(o["uid"], o["kind"], o["radius"]) for o in rec["entered"]] == [(142, "range", 400)], rec
        assert [t["uid"] for t in fake.touched] == [141, 142], "entered -- and it fired, as the record said it would"


@pytest.mark.parametrize("smooth", [False, True])
def test_a_walker_stepping_onto_the_path_ahead_re_plans_the_route_round_it(game, smooth):
    """The first plan is the straight line; once he is on his way a villager walks down onto it ahead of him and
    stops there. The objects are read again after every hold (every chunk), so the walk plans again round where
    the villager stands now -- no contact -- and ``npc_replans`` counts it. (He is a slow walker from the start, so
    the holds near him are short: a long one would run on blind while he walked in.)"""
    fake = FakeGame(game)
    walker = _villager(200, 500, uid=160, path=[(200, 500), (200, 0)], speed=1.0, once=True)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -450, 0)
        fake.blockers = {30820: [walker]}
        published(g, lambda s: s.objects and s.objects[0]["moving"])
        settle = g.settle

        def settle_then_step_in(*a, **kw):
            st = settle(*a, **kw)
            if walker["speed"] < 50 and st.player_x is not None and st.player_x > -420:
                walker["speed"] = 50.0                      # he is on his way: the villager walks down onto the path
                st = published(g, lambda s: s.objects and abs(s.objects[0]["z"]) < 1)
            return st

        g.settle = settle_then_step_in
        rec = g.route_to(450.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), npcs=True, smooth=smooth)
        assert walker.get("_done") and rec["waypoints"] == [[450, 0]], (walker, rec)      # the premise
        assert rec["reached"] and rec["npc_replans"] >= 1, rec
        assert not fake.contacts, fake.contacts
        assert (160, "body") in [(o["uid"], o["kind"]) for o in rec["avoided"]], rec


def test_a_walker_that_keeps_crossing_the_path_cannot_hold_the_call(game):
    """The adversary: whenever he has moved, a villager steps in again 250u ahead of him along the way he was
    going -- onto the path still to walk. Each of those is grounds for a re-plan: ROUTE_NPC_REPLANS of them are
    made, no more, though it cuts in more often than that; then the walk goes on under the stall ladder, and the
    call ENDS, wherever that leaves him -- bounded, never an endless re-plan."""
    fake = FakeGame(game)
    goal = (550.0, 450.0)
    body = _villager(-550, 0, uid=170, path=[(-550, 0), (-550, 1)], speed=0.5)     # walking: the holds near it are short
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -550, -450)
        fake.blockers = {30820: [body]}
        published(g, lambda s: s.objects and s.objects[0]["moving"])
        g.ROUTE_WAIT_SECONDS = 0.5
        settle, last, cuts = g.settle, {}, []

        def settle_then_cut_in(*a, **kw):
            st = settle(*a, **kw)
            if st.player_x is None or not st.control:
                return st
            here, prev = (st.player_x, st.player_z), last.get("here")
            last["here"] = here
            if prev is None or math.dist(prev, here) < 10:
                return st
            d = math.dist(prev, here)
            x, z = here[0] + (here[0] - prev[0]) / d * 250, here[1] + (here[1] - prev[1]) / d * 250
            if math.dist((x, z), goal) < 300:
                return st                                  # never onto the goal itself
            body["x"], body["z"], body["path"] = x, z, [(x, z), (x, z + 1)]
            cuts.append((round(x), round(z)))
            return published(g, lambda s: s.objects and math.dist((s.objects[0]["x"], s.objects[0]["z"]), (x, z)) < 2)

        g.settle = settle_then_cut_in
        t0 = time.time()
        rec = g.route_to(*goal, walkmesh=_flat_bgi(), prior=_prior(), npcs=True, smooth=True)
        assert time.time() - t0 < 120, "a walker that keeps crossing must end the call, not hold it"
        assert rec["npc_replans"] == g.ROUTE_NPC_REPLANS < len(cuts), (rec, cuts)
        assert g.state.control and g.state.field_id == 30820


@pytest.mark.parametrize("smooth", [False, True])
def test_an_engine_that_cannot_list_objects_walks_exactly_as_unstick(game, smooth):
    """The key ABSENT (an engine without s89): ``npcs`` degrades to the blind unstick walk -- the same waits, the same
    push through the villager, the same plan -- and says "cannot"."""
    recs = []
    for npcs in (False, True):
        fake = FakeGame(game)
        fake.objects_mode = "absent"
        fake.blockers = {30820: [_villager(0, 0, uid=140)]}
        with session(game, fake) as g:
            boot(g)
            g.warp(30820)
            _stand(g, fake, -400, 0)
            g.ROUTE_WAIT_SECONDS = 0.5
            recs.append(g.route_to(400.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), unstick=True, npcs=npcs,
                                   smooth=smooth))
    blind, degraded = recs
    assert blind["npcs"] is None and degraded["npcs"] == "cannot", recs
    for k in ("reached", "waypoints", "waits", "pushes", "pushed", "blockers", "blocked", "frozen", "avoided"):
        assert blind[k] == degraded[k], (k, blind[k], degraded[k])
    assert degraded["pushes"] == 1 and degraded["reached"], degraded


@pytest.mark.parametrize("smooth", [False, True])
def test_null_objects_are_never_read_as_an_empty_field(game, smooth):
    """null -- the engine could not say -- is read again ROUTE_NPC_READS times, then walked blind (``npcs``
    "unknown"): the villager is still found by walking into him and pushed through, as unstick finds him, and no plan
    claims to have gone round anyone. A null sample mid-walk leaves the last list read standing: a re-plan still
    goes round the villager, and the discs every hold keeps off are not emptied by it."""
    from ff9mapkit.content import pathfind
    from ff9mapkit.scene import routes
    fake = FakeGame(game)
    fake.objects_mode = "null"
    fake.blockers = {30820: [_villager(0, 0, uid=140)]}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -400, 0)
        g.ROUTE_WAIT_SECONDS = 0.5
        sent = _counting(g)
        rec = g.route_to(400.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), npcs=True, smooth=smooth)
        assert rec["npcs"] == "unknown" and rec["avoided"] == [] and rec["reached"], rec
        assert rec["pushes"] == 1 and fake.contacts, "found by walking into him, as the blind walk finds him"
        reads = [s for s in sent if s == (f"wait {g.ROUTE_NPC_READ_FRAMES}",)]
        assert len(reads) == g.ROUTE_NPC_READS, sent[:8]
    listed = [dict(_villager(0, 0, uid=140), y=0.0, coll=True, solid=False)]
    watch = {"objs": listed, "y": 0.0, "margin": 56.0, "keep": set(), "planned": {}, "discs": [], "path": [],
             "moves": 0}
    null = State({"player": {"x": -400.0, "y": 0.0, "z": 0.0}, "objects": None})
    record = {"avoided": [], "entered": [], "through": [], "sealed": []}
    wps, _sealing = g._plan_npcs(_flat_bgi(), null, (400.0, 0.0), [], 56.0, [], [], watch, record)
    pts = [(-400.0, 0.0)] + [tuple(map(float, w)) for w in wps]
    assert all(routes.seg_dist_xz(0, 0, a, b) >= 152 for a, b in zip(pts, pts[1:])), wps
    kept = list(watch["discs"])
    assert kept and g._npc_moved(null, watch) is False and watch["discs"] == kept and watch["objs"] is listed
    assert pathfind.route_avoiding(_flat_bgi(), (-400, 0), (400, 0), []) == [(400, 0)], "premise: empty = straight"


def test_a_smooth_hold_is_bounded_by_the_nearest_object_as_by_a_zone(game):
    """_plan_hold with the published objects in its leg. The pad nearest the leg's bearing runs past a villager
    standing beside the leg: without the objects (the control) the hold runs on into him; with them the hold -- its
    whole heading-error fan -- stays ROUTE_BODY_PAD off his ``r``. And a hold whose line passes near a WALKER runs
    ROUTE_WALKER_HOLD_TICKS at most (6 frames at the calibrated 60 fps): the objects are read again only when it
    ends."""
    from ff9mapkit.scene import routes
    g = session(game, None)
    basis = _prior()
    here, goal = (-800.0, -500.0), (700.0, 0.0)
    villager = {"uid": 1, "x": -450.0, "y": 0.0, "z": -520.0, "r": 100.0, "coll": True}
    legs = g._route_legs([here, goal], [], (), spread=g._heading_spread(basis, basis))
    leg = legs[0][3]

    def line(hold):
        _buttons, u, n, slow = hold
        reach = g.rate().reach(n, "walk" if slow else "run")
        return here, (here[0] + u[0] * reach, here[1] + u[1] * reach)

    free = g._plan_hold(basis, here, goal, leg)
    assert routes.seg_dist_xz(-450, -520, *line(free)) < 100, f"premise: the hold runs into him ({free})"
    leg["watch"] = {"discs": g._npc_discs([villager], here, 0.0, 56.0)}
    held = g._plan_hold(basis, here, goal, leg)
    assert held is not None and routes.seg_dist_xz(-450, -520, *line(held)) >= 100 + g.ROUTE_BODY_PAD - 0.5, held
    beside = g._npc_discs([dict(villager, x=300.0, z=150.0)], (0.0, 0.0), 0.0, 56.0)     # the rule itself
    assert g._probe_is_clear((0.0, 0.0), (1.0, 0.0), 400.0, [], 0.0, discs=beside)      # the line passes 150 off
    assert not g._probe_is_clear((0.0, 0.0), (1.0, 0.0), 400.0, [], 0.3, discs=beside)  # its fan comes within 8
    ahead = g._npc_discs([dict(villager, x=300.0, z=50.0)], (0.0, 0.0), 0.0, 56.0)
    assert not g._probe_is_clear((0.0, 0.0), (1.0, 0.0), 400.0, [], 0.0, discs=ahead)   # into him
    assert g._probe_is_clear((0.0, 0.0), (1.0, 0.0), 150.0, [], 0.0, discs=ahead)       # short of him
    open_leg = g._route_legs([(-800.0, 0.0), (800.0, 0.0)], [], (), spread=g._heading_spread(basis, basis))[0][3]
    cap = g._frames_within(g.ROUTE_WALKER_HOLD_TICKS, g.rate())
    assert cap == 6
    assert g._plan_hold(basis, (-800.0, 0.0), (800.0, 0.0), open_leg)[2] > cap    # the control
    walker = g._npc_discs([dict(villager, x=-600.0, z=250.0, moving=True)], (-800.0, 0.0), 0.0, 56.0)
    open_leg["watch"] = {"discs": walker}
    assert g._plan_hold(basis, (-800.0, 0.0), (800.0, 0.0), open_leg)[2] == cap
    open_leg["watch"] = {"discs": [dict(walker[0], moving=False)]}                        # standing: no cap
    assert g._plan_hold(basis, (-800.0, 0.0), (800.0, 0.0), open_leg)[2] > cap


def test_on_stock_350_the_walk_to_450_goes_round_a_villager_and_clear_of_vivis_range(game, dali):
    """The owner's crossing on real floors: 350 from the 351-door arrival to the 450 exit, a villager standing on the
    longest leg of the route the router takes, and a Range like Vivi's (a warp from 314u) 200u off the next longest.
    Blind (unstick), the walk presses into the villager and passes inside Vivi's radius -- the run is warped (the
    premise). NPC-aware, the crossing lands in 450's region with no contact and nothing fired, both avoided."""
    from ff9mapkit.content import pathfind
    walkmesh, script = dali
    fake, prior = _dali_fake(game, walkmesh, script, 350)
    wm, places = walkmesh(350), _dali_places(script, 350)
    door, start = places[-1], _DALI_STARTS[350]
    goal = pathfind.region_goal(wm, door)
    avoid = [z for z in places if z is not door]
    pts = [start] + [tuple(w) for w in pathfind.route_avoiding(wm, start, goal, avoid)]
    (a, b), (c, d) = sorted(zip(pts, pts[1:]), key=lambda ab: -math.dist(*ab))[:2]
    villager = _villager((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, uid=140)
    n = math.dist(c, d)
    vx, vz = (c[0] + d[0]) / 2 - (d[1] - c[1]) / n * 200, (c[1] + d[1]) / 2 + (d[0] - c[0]) / n * 200
    assert wm.point_on_walkmesh(int(vx), int(vz)) is not None, "premise: Vivi stands on the floor"
    vivi = _villager(vx, vz, uid=141, r=224.0, range_r=314.0, to=30099, arrive=(0, 0))
    with session(game, fake) as g:
        boot(g)
        g.warp(350)
        _stand(g, fake, *start)
        g.calibrate_axes(hazards=places, prior=prior)
        g.ROUTE_WAIT_SECONDS = 0.5
        recs = {}
        for npcs in (False, True):
            fake.blockers = {}
            g.warp(350)
            _stand(g, fake, *start)
            fake.blockers = {350: [villager, vivi]}
            published(g, lambda s: s.objects and len(s.objects) == 2)
            touched, contacts = len(fake.touched), len(fake.contacts)
            recs[npcs] = g.route_cross(goal[0], goal[1], avoid=avoid, walkmesh=wm, prior=prior, zone=door, smooth=True,
                                       unstick=True, npcs=npcs, timeout=3)
            recs[npcs]["contacts"] = len(fake.contacts) - contacts
            recs[npcs]["touched"] = [t["uid"] for t in fake.touched[touched:]]
        blind, aware = recs[False], recs[True]
        assert blind["contacts"] and blind["touched"] == [141] and blind["landed"] == 30099, blind
        assert aware["landed"] == 30000 + len(places) - 1 and aware["npcs"] == "listed", aware
        assert (aware["contacts"], aware["touched"], aware["entered"], aware["through"]) == (0, [], [], []), aware
        assert {(140, "body"), (141, "range")} <= {(o["uid"], o["kind"]) for o in aware["avoided"]}, aware


def test_on_stock_352_a_solid_body_in_the_inn_rooms_one_way_out_is_blocked(game, dali):
    """352's inn room leaves through one corner-to-corner pinch, ~82u from both walls against the 80u controller
    radius. A SOLID body standing in it is the owner's true movement lock: the plan knows there is no way -- ``blocked``
    at once, the body named, not a hold pressed. The same body non-solid is the planner's last resort, a push: the
    route goes through him (``through``)."""
    from ff9mapkit.content import pathfind
    walkmesh, script = dali
    fake, prior = _dali_fake(game, walkmesh, script, 352)
    wm, (zone,) = walkmesh(352), _dali_places(script, 352)
    start, goal = (0, 600), pathfind.region_goal(wm, zone)
    pts = [start] + [tuple(w) for w in pathfind.route_avoiding(wm, start, goal, [])]
    samples = [(a[0] + (b[0] - a[0]) * k / 64, a[1] + (b[1] - a[1]) * k / 64) for a, b in zip(pts, pts[1:])
               for k in range(65)]
    pinch = min(samples, key=lambda p: wm.distance_to_boundary(int(round(p[0])), int(round(p[1]))) or 1e9)
    assert wm.distance_to_boundary(int(round(pinch[0])), int(round(pinch[1]))) < 100, "premise: the pinch"
    with session(game, fake) as g:
        boot(g)
        g.warp(352)
        _stand(g, fake, *start)
        g.calibrate_axes(hazards=[], prior=prior)
        _stand(g, fake, *start)
        fake.blockers = {352: [_villager(*pinch, uid=150, solid=True)]}
        published(g, lambda s: s.objects and s.objects[0]["solid"])
        sent = _counting(g)
        rec = g.route_to(goal[0], goal[1], walkmesh=wm, prior=prior, npcs=True, smooth=True, zone=zone)
        assert rec["blocked"] and rec["waypoints"] is None and [o["uid"] for o in rec["sealed"]] == [150], rec
        assert (rec["waits"], rec["pushes"], sent) == (0, 0, []), (rec, sent)
        fake.blockers = {352: [_villager(*pinch, uid=150)]}
        st = published(g, lambda s: s.objects and not s.objects[0]["solid"])
        record = {"avoided": [], "entered": [], "through": [], "sealed": []}
        watch = g._npc_watch(56.0, {})
        wps, sealing = g._plan_npcs(wm, st, goal, [], 56.0, [], [], watch, record)
        assert wps is not None and sealing == [] and [o["uid"] for o in record["through"]] == [150], record


# ----------------------------------------------------------- route_to(npcs=True): the review's findings, pinned
# A stall laid on a body he was not touching; one trigger across a corridor opening every other; a margin read as
# a wall; a patrolling Range judged where it stood; a band judged at the start's height; a seal that cost a sweep a
# tier; a calibration refused for a villager; a walking solid read as a lock. Each test below fails on the code the
# review read.


class _Rooms:
    """A floor that is a union of axis-aligned rectangles with explicit walls -- the router's view of it (no triangles,
    so no floor heights: the |dy| band is judged against his y)."""

    def __init__(self, rects, walls):
        self.rects, self.walls = rects, walls

    def point_on_walkmesh(self, x, z):
        return 0 if any(x0 <= x <= x1 and z0 <= z <= z1 for x0, z0, x1, z1 in self.rects) else None

    def distance_to_boundary(self, x, z):
        from ff9mapkit.scene import routes
        if self.point_on_walkmesh(x, z) is None:
            return None
        return min(routes.seg_dist_xz(x, z, a, b) for a, b in self.walls)


#: Room A x -1200..-200, a corridor x -200..200 (z -150..150), room B x 200..1200 (z -600..600).
_DUMBBELL = [(-1200, -600, -200, 600), (-200, -150, 200, 150), (200, -600, 1200, 600)]


def _dumbbell():
    c = [(-1200, -600), (-200, -600), (-200, -150), (200, -150), (200, -600), (1200, -600), (1200, 600), (200, 600),
         (200, 150), (-200, 150), (-200, 600), (-1200, 600)]
    return _Rooms(_DUMBBELL, list(zip(c, c[1:] + c[:1])))


def _rect_rooms(x0, z0, x1, z1):
    c = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
    return _Rooms([(x0, z0, x1, z1)], list(zip(c, c[1:] + c[:1])))


def _obj(uid, x, z, **kw):
    """A published object as s89 lists it (a non-solid villager by default)."""
    return dict({"uid": uid, "sid": uid, "x": float(x), "y": 0.0, "z": float(z), "r": 152.0, "coll": True,
                 "solid": False, "range": False, "talk": False, "range_r": None, "talk_r": None, "moving": False,
                 "shown": True, "flags": 1}, **kw)


def _plan_on(g, wm, here, goal, objs, polys=(), heights=None, y=0.0):
    """_plan_npcs from ``here`` over ``objs``: ``(waypoints, sealing, record, points)``."""
    st = State({"player": {"x": float(here[0]), "y": y, "z": float(here[1]), "control": True}, "objects": objs})
    watch = {"objs": objs, "y": y, "margin": 56.0, "heights": heights, "keep": set(), "planned": {}, "discs": [],
             "path": [], "moves": 0}
    record = {"avoided": [], "entered": [], "through": [], "sealed": []}
    wps, sealing = g._plan_npcs(wm, st, goal, [list(p) for p in polys], 56.0, [], [], watch, record)
    pts = None if wps is None else [tuple(map(float, here))] + [tuple(map(float, w)) for w in wps]
    return wps, sealing, record, pts


def _nearest(pts, x, z):
    from ff9mapkit.scene import routes
    return min(routes.seg_dist_xz(x, z, a, b) for a, b in zip(pts, pts[1:]))


@pytest.mark.parametrize("smooth", [False, True])
def test_a_stall_is_laid_on_a_published_body_only_when_he_is_pressed_against_it(game, smooth):
    """A wall the router's floor lacks (x -20..20 from z -300 up) beside a villager standing 54u clear of his ``r``
    from where the walk stops: the stall is the wall's, and the walk must place the unseen blocker the blind walk
    places -- not lay it on the villager, re-plan round him the same way three times and give up. The contact test
    itself: within HALF_STEP of ``r`` and within ROUTE_CONTACT_ANGLE of the press -- and a body the plan already went
    round, unmoved, would be planned round the same way again."""
    fake = FakeGame(game)
    fake.walkmesh = [(-600, -600, -20, 600), (-20, -600, 20, -300), (20, -600, 600, 600)]
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -450, 100)
        fake.blockers = {30820: [_villager(60, 260, uid=140)]}
        published(g, lambda s: s.objects and len(s.objects) == 1)
        g.ROUTE_WAIT_SECONDS = 20 / 60
        rec = g.route_to(450.0, 100.0, walkmesh=_flat_bgi(), prior=_prior(), npcs=True, smooth=smooth)
        assert rec["reached"] and rec["blockers"] and not rec["frozen"], rec
    watch = {"objs": [_obj(1, 0.0, 0.0)], "margin": 56.0, "planned": {1: (0.0, 0.0)}}

    def at(x, z):
        return State({"player": {"x": x, "y": 0.0, "z": z}})
    assert g._body_ahead(at(-157.0, 0.0), (1.0, 0.0), watch)["uid"] == 1              # r + 5, dead ahead
    assert g._body_ahead(at(-206.0, 0.0), (1.0, 0.0), watch) is None                  # 54 clear of r
    assert g._body_ahead(at(-157.0, 0.0), (math.cos(1.4), math.sin(1.4)), watch) is None     # 80 degrees off
    d = g._npc_discs(watch["objs"], (-157.0, 0.0), 0.0, 56.0)[0]
    assert not g._npc_shifted(d, watch)                                              # planned round, unmoved
    assert g._npc_shifted(dict(d, x=20.0), watch) and g._npc_shifted(dict(d, uid=2), watch)


def test_one_trigger_across_the_only_corridor_does_not_open_the_way_through_the_others(game):
    """A chest's Range spans the only corridor; a warp's radius in the far room is avoidable. The plan must give up the
    chest alone -- not every trigger on the field -- and go round the warp; and walked, only the chest fires. The
    review's plan passed the warp 261u from its centre (R 314) and the fake landed in 30821."""
    g = session(game, None)
    chest = _obj(1, 0, 140, r=100.0, range=True, range_r=260.0)
    vivi = _obj(2, 700, 150, r=224.0, range=True, range_r=314.0)
    wps, sealing, record, pts = _plan_on(g, _dumbbell(), (-800, 0), (1000, 0), [chest, vivi])
    assert wps is not None and _nearest(pts, 700, 150) >= 314, (wps, record)
    assert [(o["uid"], o["kind"]) for o in record["entered"]] == [(1, "range")], record
    fake = FakeGame(game)
    fake.exit_frames = 20
    fake.walkmesh = _DUMBBELL
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -800, 0)
        fake.blockers = {30820: [_villager(0, 140, uid=1, r=100.0, range_r=260.0),
                                 _villager(700, 150, uid=2, r=224.0, range_r=314.0, to=30821, arrive=(0, 0))]}
        published(g, lambda s: s.objects and len(s.objects) == 2)
        rec = g.route_to(1000.0, 0.0, walkmesh=_dumbbell(), prior=_prior(), npcs=True, smooth=True)
        assert rec["landed"] is None and rec["reached"], rec
        assert [t["uid"] for t in fake.touched] == [1], fake.touched


def test_a_lane_a_margin_closes_is_still_a_lane(game):
    """THE TIGHT RADIUS. A Range whose radius plus the plan's margin (56) closes the corridor, while its radius plus
    the pad a hold keeps (30) leaves it open: the route stays out -- nothing entered. And a SOLID body whose ``r``
    leaves a pass the engine lets him through (20u each side of the wall's clearance line), which ``r`` + 32 closes:
    a route, not ``blocked`` -- and it keeps ``r`` clear of the body."""
    g = session(game, None)
    chest = _obj(1, 0, 150, r=60.0, range=True, range_r=170.0)
    wps, sealing, record, pts = _plan_on(g, _dumbbell(), (-800, 0), (1000, 0), [chest])
    assert wps is not None and record["entered"] == [] and _nearest(pts, 0, 150) >= 170 + g.PROBE_HAZARD_PAD - 1, \
        (wps, record)
    lane = _rect_rooms(-1200, -300, 1200, 300)
    body = _obj(1, 0, 0, r=200.0, solid=True)
    wps, sealing, record, pts = _plan_on(g, lane, (-800, 0), (800, 0), [body])
    assert wps is not None and sealing == [] and _nearest(pts, 0, 0) >= 200, (wps, sealing)


def test_a_seal_by_solids_costs_one_sweep_and_every_plan_shares_the_floors_answers(game, monkeypatch):
    """The solids alone, at their tight radius, are planned FIRST: every other plan keeps a superset of them, so when
    they seal, one failed sweep (and the walls-and-zones route that names them) is all it costs -- not one full sweep
    a tier. And every plan of a call is handed the same floor memo (route_avoiding ``memo``)."""
    from ff9mapkit.content import pathfind
    g = session(game, None)
    calls = []
    route = pathfind.route_avoiding

    def counted(*a, **kw):
        wps = route(*a, **kw)
        calls.append((wps is None, id(kw.get("memo"))))
        return wps
    monkeypatch.setattr(pathfind, "route_avoiding", counted)
    lane = _rect_rooms(-1200, -150, 1200, 150)
    objs = [_obj(1, 0, 0, solid=True), _obj(2, -600, 60, range=True, range_r=90.0), _obj(3, 600, -60)]
    wps, sealing, record, _pts = _plan_on(g, lane, (-900, 0), (900, 0), objs)
    assert wps is None and [d["uid"] for d in sealing] == [1], sealing
    assert [failed for failed, _memo in calls] == [True, False], calls              # the solids plan, then the bare
    assert len({memo for _failed, memo in calls}) == 1 and calls[0][1] != id(None), calls


def test_a_press_is_judged_where_a_walking_trigger_will_be_not_where_it_was_read(game):
    """A walker 300u off a press's line and walking toward it: read where it stood, the press keeps its pad (the
    premise -- the rule every hold used); judged by where it can be by the time he gets there, it does not. A press
    away from it does. Standing is judged along the line it walks (either way), not in every direction."""
    g = session(game, None)
    walker = g._npc_discs([_obj(1, 300, -300, range=True, range_r=227.0, moving=True)], (0.0, 0.0), 0.0, 56.0,
                          speeds={1: 15.0}, headings={1: (0.0, 1.0)})
    trigger = walker[-1]
    assert trigger["kind"] == "trigger" and trigger["speed"] == 15.0 and trigger["dir"] == (0.0, 1.0)
    assert g._probe_is_clear((0.0, 0.0), (1.0, 0.0), 300.0, [], 0.0, discs=[trigger])        # the premise
    run = g.rate().speed("run")                                                      # his pace: 30u a frame at 60 fps
    assert not g._walker_clear((0.0, 0.0), (1.0, 0.0), 300.0, 0.0, trigger, run, 10 + 12)
    assert g._walker_clear((0.0, 0.0), (-1.0, 0.0), 300.0, 0.0, trigger, run, 10 + 12)
    a, b = g._walker_path(trigger, 20)
    assert a == (300.0, -600.0) and b == (300.0, 0.0)
    far = dict(trigger, x=-2000.0, z=0.0)                                            # its beat runs past him, far off
    assert g._walker_clear((0.0, 1000.0), (1.0, 0.0), 0.0, 0.0, far, run, 30)
    assert not g._walker_clear((0.0, 1000.0), (1.0, 0.0), 0.0, 0.0, dict(far, dir=None), run, 30 * 60)


@pytest.mark.parametrize("phase", [200, 600])
def test_a_patrolling_trigger_is_never_walked_into(game, phase):
    """A warp's Range PATROLLING across the only way (x = 100, z -520..520), at the game's own frame rate and
    speed scale (published ``speed`` 15 a call, a call a two-frame tick: 7.5u a frame). The review's walk was warped
    in every run: each hold judged the walker where it was last read. Now the walk waits for it to go by and crosses
    in one press when it can -- reached, or out of patience (boxed, having waited) -- and never fires it."""
    fake = FakeGame(game, fps=60)
    fake.exit_frames = 20
    z0 = 520 - phase
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -450, 0)
        fake.blockers = {30820: [_villager(100, z0, uid=141, range_r=152.0 + 15.0 + 60.0, to=30821, arrive=(0, 0),
                                           path=[(100, z0), (100, -520), (100, 520)], speed=7.5)]}
        published(g, lambda s: s.objects and s.objects[0]["moving"])
        g.ROUTE_WAIT_SECONDS = 0.5
        rec = g.route_to(450.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), npcs=True, smooth=True)
        assert fake.touched == [] and rec["landed"] is None, (rec, fake.touched)
        assert rec["reached"] or (rec["boxed"] and rec["npc_waits"]), rec


def test_a_trigger_that_reaches_him_as_control_goes_is_named_in_entered(game):
    """When a walk loses control inside a published trigger's reach -- a walker's Range, one a walk strayed into -- the
    record names it, instead of an empty ``entered`` beside a warped run. Not when he stands in the zone he was sent
    to, which took control itself."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, 0, -200)
        fake.blockers = {30820: [_villager(0, 0, uid=141, range_r=227.0)]}      # no warp: control stays for the read
        published(g, lambda s: s.objects and len(s.objects) == 1)
        watch = g._npc_watch(56.0, {})
        record = {"entered": []}
        g._npc_fired(watch, record, 30820, zone=[(-100, -300), (100, -300), (100, -100), (-100, -100)])
        assert record["entered"] == []
        g._npc_fired(watch, record, 30820)
        assert [(o["uid"], o["kind"], o["radius"]) for o in record["entered"]] == [(141, "range", 227)], record
        g._npc_fired(watch, record, 30821)                                    # he is not on that field: nothing
        assert len(record["entered"]) == 1


def test_a_plan_judges_the_dy_band_by_the_floor_under_each_object(game):
    """The engine pairs him with an object only while |dy| < 400; judged against where he stands NOW, an object on the
    level a route climbs to is out of the plan until he is on its level. Given the floor's heights, an object counts
    when it stands on a floor under it -- in the published frame, which puts him on the floor under his own feet
    (every recorded stock state reads ``y == -height``; either sign is allowed). One floating off every floor under it
    is left out; one with no floor under it is kept."""
    g = session(game, None)

    def heights(x, z):
        if abs(z) > 600:
            return []
        return [0.0] if x < 0 else [900.0]                          # a terrace 900 up, east of x = 0
    objs = [_obj(1, 500, 0, y=-900.0), _obj(2, 500, 100, y=-1800.0), _obj(3, 500, 900, y=-3000.0)]
    now = {d["uid"] for d in g._npc_discs(objs, (-500.0, 0.0), 0.0, 56.0)}
    assert now == set(), now                                      # the premise: his y now is 900+ off every one
    kept = {d["uid"] for d in g._npc_discs(objs, (-500.0, 0.0), 0.0, 56.0, heights)}
    assert kept == {1, 3}, kept
    level = g._npc_levels(heights, (500.0, 0.0), 900.0)          # the other sign's frame, stood on the terrace
    assert level(_obj(1, 500, 0, y=900.0)) and not level(_obj(1, 500, 0, y=-900.0))


def test_on_stock_309_a_body_on_the_level_the_route_climbs_to_is_planned_round(game, dali):
    """THE REVIEW'S 309: from the 307 door (floor 967 up) to the 310 door (1665 down) the route passes a SOLID body with
    a Range standing on the floor 534 up -- 433 off his height at the start, so the band judged there left it out and
    the plan walked through it. Judged by the floor under it (the call's walkmesh, the published frame negated) it is
    planned round."""
    from ff9mapkit import eventscan
    from ff9mapkit.content import pathfind
    walkmesh, script = dali
    wm = walkmesh(309)
    zones = {}
    for gw in eventscan.scan_gateways(script(309)):
        zones.setdefault(gw["to"], gw["zone"])
    a, b = pathfind.region_goal(wm, zones[307]), pathfind.region_goal(wm, zones[310])
    polys = [z for t, z in zones.items() if t != 310]
    g = session(game, None)
    heights = g._floor_heights(wm)
    ha = wm.mesh.height_at(*a)
    body = _obj(7, -1103, 1596, y=-534.0, solid=True, range=True, range_r=152.0 + 30 + 60)
    assert abs(-534.0 - (-ha)) >= g.NPC_DY_BAND, "premise: out of the band where he starts"
    wps, sealing, record, pts = _plan_on(g, wm, a, b, [body], polys, heights=heights, y=-float(ha))
    assert wps is not None and _nearest(pts, -1103, 1596) >= 152, (wps, record)
    assert (7, "body") in [(o["uid"], o["kind"]) for o in record["avoided"]], record


def test_on_stock_356_a_solid_villager_beside_a_wall_leaves_the_pass_the_engine_leaves(game, dali):
    """THE REVIEW'S 356: from the arrival to the 350 door, a SOLID villager (r 152) 108u off a wall. At r + 32 the plan
    called it a seal; the engine keeps his centre only ``r`` off the body and 80u off the wall, and the pass is there
    -- the plan must find it, and keep ``r`` clear of the body."""
    from ff9mapkit import eventscan
    from ff9mapkit.content import pathfind
    walkmesh, script = dali
    wm = walkmesh(356)
    zones = []
    for gw in eventscan.scan_gateways(script(356)):
        if all(gw["zone"] != z for _t, z in zones):
            zones.append((gw["to"], gw["zone"]))
    to, zone = zones[0]
    assert to == 350, zones
    g = session(game, None)
    wps, sealing, record, pts = _plan_on(g, wm, (350, -158), pathfind.region_goal(wm, zone),
                                         [_obj(99, 804, -147, solid=True)], [z for _t, z in zones if z is not zone])
    assert wps is not None and sealing == [] and _nearest(pts, 804, -147) >= 152, (wps, sealing)


def test_a_calibration_beside_a_villager_is_not_refused_under_npcs(game):
    """A villager (a body, no trigger) standing 200u from where he arrives, calibrated with no prior:
    route_to(npcs=True) kept every published disc as a calibration hazard, and a blind probe refuses any hazard within
    its reach -- so it raised where route_to(unstick=True) calibrates fine. A body costs a probe a slide, never a wrong room: only the
    TRIGGERS are hazards."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -300, 0)
        fake.blockers = {30820: [_villager(-300, 200, uid=140)]}
        published(g, lambda s: s.objects and len(s.objects) == 1)
        rec = g.route_to(300.0, 0.0, walkmesh=_flat_bgi(), prior=None, npcs=True)
        assert 30820 in g._axes and rec["reached"], rec
        watch = g._npc_watch(56.0, {})
        assert g._npc_hazards(watch, g.state) == []
        fake.blockers = {30820: [_villager(-300, 200, uid=140, range_r=300.0)]}
        published(g, lambda s: s.objects and s.objects[0]["range_r"])
        assert len(g._npc_hazards(g._npc_watch(56.0, {}), g.state)) == 1


def test_a_walking_solid_that_seals_the_lane_is_waited_for(game):
    """A SOLID villager walking out of a lane too narrow to pass him: the seal is his only while he is in it. The walk
    waits for him (ROUTE_WAIT_SECONDS, within the budget) and plans again -- not ``blocked`` at once, a strike spent on
    someone who walks off within seconds."""
    fake = FakeGame(game)
    fake.walkmesh = _LANE
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -450, 0)
        # walking up across the lane: in it -- sealing it -- for its first ~430 frames
        fake.blockers = {30820: [_villager(0, -200, uid=150, solid=True, path=[(0, -200), (0, 900)], speed=1.0,
                                          once=True)]}
        published(g, lambda s: s.objects and s.objects[0]["moving"])
        g.ROUTE_WAIT_SECONDS = 1.0
        rec = g.route_to(450.0, 0.0, walkmesh=_flat_bgi(*_LANE), prior=_prior(), npcs=True, smooth=True)
        assert rec["reached"] and not rec["blocked"] and rec["waits"] >= 1 and rec["sealed"] == [], rec


def test_the_tour_reads_a_walk_boxed_after_waiting_on_walkers_as_live():
    """The tour's strike rule: a walk that waited on walking triggers and was then left with nothing it could press is
    the village in the way (LIVE), not a boxed exit (REAL); a walk boxed without waiting is still BOXED. The rule's
    one implementation is dali_tour (rung3_step1 and rung3_trace both drive it)."""
    sys.path.insert(0, str(REPO / "studies" / "story-trace"))
    import dali_tour as tour
    assert tour.failure({"boxed": True, "npc_waits": 3, "route": 2}) == "live"
    assert tour.failure({"boxed": True, "npc_waits": 0, "route": 2}) == "boxed"


# ---- the session-2 box: two Dali children (talk-only walkers, non-solid, r 152) walked into Zidane on 350 and stood
# there, held -- the engine undoes every step a scripted walker takes into the player -- and every press toward any exit
# came nearer one of them, so seven crossings in a row came back ``boxed``, each a REAL strike, and the run went VOID.
# A box a WALKER is part of is not the spot: waited out, stepped away from when it is held on him, planned again.


def _step_in_front(g, *moves, past=-420.0):
    """Once he is on his way (past x ``past``, after the hold that got him there, where the walk reads the objects next)
    each ``(body, at, path, speed)`` of ``moves`` steps up to ``at`` -- an offset from where he stands -- and walks
    ``path`` (offsets too) at ``speed``, once. Returns where he stood when they did (empty until then)."""
    from ff9mapkit.scene import routes
    settle, done = g.settle, []

    def settle_then_step_in(*a, **kw):
        st = settle(*a, **kw)
        if done or st.player_x is None or st.player_x <= past or not st.control:
            return st
        px, pz = st.player_x, st.player_z
        done.append((px, pz))
        ways = []
        for body, at, path, speed in moves:
            for k in ("_k", "_way", "_done"):
                body.pop(k, None)
            way = [(px + x, pz + z) for x, z in path]
            body.update(x=px + at[0], z=pz + at[1], path=way, speed=speed, once=True)
            ways.append((body["uid"], way))

        def stepped(s) -> bool:
            at = {o["uid"]: (o["x"], o["z"]) for o in s.objects or ()}
            return all(uid in at and routes.seg_dist_xz(*at[uid], way[0], way[-1]) < 1 for uid, way in ways)
        return published(g, stepped)
    g.settle = settle_then_step_in
    return done


def _creeping(uid):
    """A villager walking, barely, well off the path: the holds near him are short from the start
    (ROUTE_WALKER_HOLD_TICKS),
    so the walk reads the objects every ~180u -- as it does beside 350's children -- instead of running the room in
    one hold before anyone can step in."""
    return _villager(-100, 500, uid=uid, path=[(-100, 500), (-100, 501)], speed=0.01)


@pytest.mark.parametrize("fixed", [False, True])
def test_a_walker_that_boxes_him_in_is_waited_for_and_the_route_goes_on(game, fixed):
    """Once he is on his way a villager steps up right in front of him -- in contact with its ``r`` -- walking on,
    across the path; with the movement re-plans spent (ROUTE_NPC_REPLANS 0: the session-2 walk had spent its four)
    every press toward the leg comes nearer it, and no hold keeps the rules. The run's code called that ``boxed`` at once
    (the premise: the box's wait taken out) -- a REAL strike on an exit someone crossed in front of for a second. Boxed
    by a WALKER is not boxed: he stands still until it has walked off, plans again and arrives, the villager named in
    ``boxers``, never pressed into."""
    fake = FakeGame(game)
    kid = _creeping(4)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -450, 0)
        fake.blockers = {30820: [kid]}
        published(g, lambda s: s.objects and s.objects[0]["moving"])
        g.ROUTE_NPC_REPLANS = 0
        if not fixed:
            g._outwait_box = lambda *a, **kw: "boxed"
        stood = _step_in_front(g, (kid, (160, 0), [(160, 0), (160, 700)], 3.0))
        rec = g.route_to(450.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), npcs=True, smooth=True)
        assert stood, "premise: the villager stepped in"
        if not fixed:
            assert rec["boxed"] and not rec["reached"] and rec["box_waits"] == 0, rec
            return
        assert rec["reached"] and not rec["boxed"] and rec["landed"] is None, rec
        assert rec["box_waits"] >= 1 and rec["box_cleared"] >= 1, rec
        assert [(o["uid"], o["kind"], o["moving"]) for o in rec["boxers"]] == [(4, "body", True)], rec
        assert not fake.contacts, fake.contacts


@pytest.mark.parametrize("step", [False, True])
def test_a_walker_held_on_him_is_stepped_away_from(game, step):
    """The session-2 children themselves: a villager walks INTO him and is held there -- the engine undoes every step a
    scripted walker takes into the player (MoveToward.cs:187-189; the fake: `_step_walkers`) -- still ``moving``. A
    wait for it waits on himself (the premise: the step taken out, the box outlasts its wait -- ``boxed``, the villager
    exactly where it stopped). So once it has not moved in ROUTE_WALKER_HELD_SECONDS he steps out of its way, off the
    line it was walking; it walks on, and so does he: reached, and it went on its way."""
    fake = FakeGame(game)
    kid = _creeping(6)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -450, 0)
        fake.blockers = {30820: [kid]}
        published(g, lambda s: s.objects and s.objects[0]["moving"])
        g.ROUTE_NPC_REPLANS = 0
        g.ROUTE_WALKER_BUDGET_SECONDS = 160 / 60
        if not step:
            g._box_step = lambda *a, **kw: False
        stood = _step_in_front(g, (kid, (170, 0), [(170, 0), (-1100, 0)], 3.0))     # along his line, into him
        t0 = time.time()
        rec = g.route_to(450.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), npcs=True, smooth=True)
        assert stood and time.time() - t0 < 60, "bounded: the wait has a budget"
        held_at = stood[0][0] + 152.0
        if not step:
            assert rec["boxed"] and not rec["reached"] and rec["box_waits"] >= 1, rec
            assert abs(kid["x"] - held_at) < 4 and kid["z"] == stood[0][1], (kid, held_at)     # held there all along
            return
        assert rec["reached"] and not rec["boxed"] and rec["box_cleared"] >= 1, rec
        assert (6, "body", True) in [(o["uid"], o["kind"], o["moving"]) for o in rec["boxers"]], rec
        assert kid["x"] < held_at - 300, "freed, it walked on along its line"


def test_two_walkers_held_on_him_from_either_side_are_stepped_away_from(game):
    """The session-2 frame itself: two children walked into him from either side -- one from ahead and up, one from
    below -- and both are held there. Every press toward the leg comes nearer one of them; each is waiting on him. He
    steps off BOTH lines they were walking, they walk on, and so does he."""
    fake = FakeGame(game)
    a, b = _creeping(4), _villager(-100, -500, uid=6, path=[(-100, -500), (-100, -501)], speed=0.01)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -450, 0)
        fake.blockers = {30820: [a, b]}
        published(g, lambda s: s.objects and len(s.objects) == 2 and all(o["moving"] for o in s.objects))
        g.ROUTE_NPC_REPLANS = 0
        stood = _step_in_front(g, (a, (120, 120), [(120, 120), (-700, -700)], 3.0),
                               (b, (0, -170), [(0, -170), (0, 900)], 3.0))
        rec = g.route_to(450.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), npcs=True, smooth=True)
        assert stood, "premise: they stepped in"
        px, pz = stood[0]
        assert rec["reached"] and not rec["boxed"] and rec["box_cleared"] >= 1, rec
        assert {o["uid"] for o in rec["boxers"]} == {4, 6}, rec
        assert a["x"] < px - 200 and b["z"] > pz + 300, "both freed: each walked on along its line"


def test_a_walker_that_outlasts_the_wait_is_boxed_and_bounded(game):
    """A villager that stays in the way -- walking, but slowly -- outlasts the box's wait (ROUTE_WALKER_BUDGET_SECONDS): then
    it IS ``boxed``, the waits counted, in bounded time -- ``boxed_by`` the walkers, not the spot. (A walker this slow,
    this near, is stepped away from like one held on him -- :meth:`_box_step` -- which is taken out here: this is the
    wait's own bound.)"""
    fake = FakeGame(game)
    kid = _creeping(8)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -450, 0)
        fake.blockers = {30820: [kid]}
        published(g, lambda s: s.objects and s.objects[0]["moving"])
        g.ROUTE_NPC_REPLANS = 0
        g.ROUTE_WALKER_BUDGET_SECONDS = 80 / 60
        g._box_step = lambda *a, **kw: False
        stood = _step_in_front(g, (kid, (170, 0), [(170, 0), (170, 700)], 0.05))
        t0 = time.time()
        rec = g.route_to(450.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), npcs=True, smooth=True)
        assert stood and time.time() - t0 < 60
        assert rec["boxed"] and not rec["reached"] and rec["box_waits"] >= (
            g._frames_lasting(g.ROUTE_WALKER_BUDGET_SECONDS) // g._frames_lasting(g.ROUTE_WALKER_WAIT_SECONDS)), rec
        assert rec["box_cleared"] == 0 and [o["uid"] for o in rec["boxers"]] == [8], rec
        assert rec["boxed_by"] == "walkers", rec


def test_a_box_nothing_walking_is_part_of_is_boxed_at_once(game):
    """THE SPOT. Beside two doors (the zones alone refuse every press), with the objects listed: nothing that walks is
    part of the box -- ``boxed`` at once, nothing pressed or waited, no ``boxers``. And a villager STANDING in contact
    where the plan saw him boxes the leg just as surely: not walking, not moved -- nothing will walk off, so ``boxed``
    at once too. The same villager walking off across the path is waited for, and the leg ends "unboxed"."""
    left, right = _rect(-400, -300, -20, 300), _rect(20, -300, 400, 300)
    fake = FakeGame(game, walkmesh=(-1000, -1000, 1000, 1000))
    fake.regions = {30820: [{"zone": left, "to": 30821, "arrive": (0, 0)}, {"zone": right, "to": 30822,
                                                                             "arrive": (0, 0)}]}
    fake.exit_frames = 30
    fake.blockers = {30820: [_villager(700, 700, uid=9)]}              # listed, standing, far off: not in the box
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, 0, -200)
        g._axes[30820] = _prior()
        published(g, lambda s: s.objects and len(s.objects) == 1)
        sent = _counting(g)
        rec = g.route_to(0.0, 800.0, avoid=[left, right], walkmesh=_flat_bgi(-1000, -1000, 1000, 1000),
                         prior=_prior(), smooth=True, npcs=True)
        assert rec["boxed"] and rec["boxed_by"] == "spot" and not rec["reached"], rec
        assert (rec["box_waits"], rec["box_cleared"], rec["boxers"], rec["waits"], rec["pushes"]) == (0, 0, [], 0, 0), rec
        assert sent == [] and not fake.fired, (sent, fake.fired)

        def leg_against(villager):
            fake.regions = {}
            fake.blockers = {30820: [villager]}
            _stand(g, fake, 0, 0)
            st = published(g, lambda s: s.objects and s.objects[0]["uid"] == villager["uid"])
            watch = g._npc_watch(56.0, {})
            watch["keep"], watch["planned"] = {(villager["uid"], "body")}, {villager["uid"]: (160.0, 0.0)}
            g._npc_view(watch, st)
            spread = g._heading_spread(_prior(), _prior())
            leg = g._route_legs([(0.0, 0.0), (1000.0, 0.0)], [], (), spread=spread, watch=watch)[0][3]
            return g._walk_leg(1000.0, 0.0, 45.0, leg, True), watch

        mark = len(sent)
        got, watch = leg_against(_villager(160, 0, uid=4))
        assert got == "boxed" and watch["box_waits"] == 0 and watch["boxers"] == [], (got, watch["boxers"])
        assert sent[mark:] == [], sent[mark:]
        got, watch = leg_against(_villager(160, 0, uid=5, path=[(160, 0), (160, 700)], speed=3.0, once=True))
        assert got == "unboxed" and watch["box_waits"] >= 1 and watch["box_cleared"] == 1, (got, watch)


def test_a_talk_only_neighbour_is_a_body_and_no_trigger(game):
    """s89's contract: ``talk_r`` is the talk SEARCH. Inside it the engine requests the entry's tag-2 Range -- which a
    talk-only entry (350's children: ``talk`` true, ``range`` false) does not have -- and its tag-3 talk runs only on a
    Confirm press, which a routed walk never sends. So it is a BODY and nothing more: a press may pass inside its talk
    radius, keeping only ROUTE_BODY_PAD off its ``r``; the same radius on an entry WITH a Range is a trigger, kept its
    pad clear. Walked in the fake: straight past the child 300u off -- inside its "!" radius -- reached, nothing fired,
    the child ``avoided`` as a body only."""
    g = session(game, None)
    kid = _obj(4, 0, 300, talk=True, talk_r=353.0)
    ranged = _obj(5, 0, 300, range=True, range_r=250.0, talk=True, talk_r=353.0)
    here = (-500.0, 0.0)
    only = g._npc_discs([kid], here, 0.0, 56.0)
    assert [(d["kind"], d["via"], d["R"]) for d in only] == [("body", "body", 152.0)], only
    both = g._npc_discs([ranged], here, 0.0, 56.0)
    assert sorted((d["kind"], d["via"], d["R"]) for d in both) == [("body", "body", 152.0), ("trigger", "talk", 353.0)]
    assert g._probe_is_clear(here, (1.0, 0.0), 1000.0, [], 0.0, discs=only)          # 300 off: inside its talk_r
    assert not g._probe_is_clear(here, (1.0, 0.0), 1000.0, [], 0.0, discs=both)
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -450, 0)
        fake.blockers = {30820: [_villager(0, 300, uid=4, talk_r=353.0)]}
        st = published(g, lambda s: s.objects and s.objects[0]["talk"] and not s.objects[0]["range"])
        assert st.objects[0]["talk_r"] == 353.0
        rec = g.route_to(450.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), npcs=True, smooth=True)
        assert rec["reached"] and rec["waypoints"] == [[450, 0]] and rec["entered"] == [], rec
        assert [(o["uid"], o["kind"]) for o in rec["avoided"]] in ([], [(4, "body")]), rec
        assert fake.touched == [] and not fake.contacts, (fake.touched, fake.contacts)


def test_the_tour_strikes_a_box_only_when_it_is_the_spot():
    """The tour's strike rule for the session-2 box: a box walkers let go of never comes back ``boxed`` -- the walk
    goes on, and a walk that then ends short OUTSIDE the zone having waited out walkers (``box_waits``) is the village
    in the way, LIVE; so is one they held past the wait (``boxed_by`` "walkers": beside a door the step out of their
    way may not fit at all, and the children never walk off him). Only the SPOT -- no walker's going would free a
    press -- is BOXED and strikes (REAL)."""
    sys.path.insert(0, str(REPO / "studies" / "story-trace"))
    import dali_tour as tour
    short = {"boxed": False, "boxed_by": None, "reached": False, "inside": False, "during": None, "route": 3,
             "waits": 0, "pushes": 0, "blockers": [], "frozen": False, "npc_replans": 0}
    assert tour.failure(dict(short, box_waits=4, box_cleared=1)) == "live"
    assert tour.failure(dict(short, box_waits=0, box_cleared=0)) == "miss"                 # the premise: no evidence
    assert tour.failure(dict(short, boxed=True, boxed_by="spot", box_waits=0)) == "boxed"          # the spot
    assert tour.failure(dict(short, boxed=True, boxed_by="spot", box_waits=4, box_cleared=1)) == "boxed"
    assert tour.failure(dict(short, boxed=True, boxed_by="walkers", box_waits=60)) == "live"       # outlasted the wait
    assert tour.failure(dict(short, inside=True, box_waits=4)) == "miss"                   # stood in the zone: REAL


def _box_leg(g, fake, bodies, *, settled=None):
    """A smooth leg from (0, 0) toward (1000, 0) on 30820 under a fresh watch of ``bodies`` (the fake's blockers, placed
    once he stands there), every one of them kept -- body and trigger -- as a plan made round where they stand would
    keep them: ``(leg, watch)``. ``settled`` (a predicate over the published state) is waited for first."""
    _stand(g, fake, 0, 0)
    fake.regions = {}
    fake.blockers = {30820: list(bodies)}
    uids = {b["uid"] for b in bodies}
    published(g, lambda s: s.objects is not None and {o["uid"] for o in s.objects} == uids
              and (settled is None or settled(s)))
    watch = g._npc_watch(56.0, {})
    watch["keep"] = {(uid, kind) for uid in uids for kind in ("body", "trigger")}
    watch["planned"] = {o["uid"]: (float(o["x"]), float(o["z"])) for o in watch["objs"]}
    g._npc_view(watch, g.state)
    spread = g._heading_spread(_prior(), _prior())
    return g._route_legs([(0.0, 0.0), (1000.0, 0.0)], [], (), spread=spread, watch=watch)[0][3], watch


#: THE CREEP BAND, a known planner weakness (not the render rate's): a walker held on him within it is never boxed --
#: a sideways one-walked-frame press keeps its pad, the walk creeps round the walker into the stall ladder, and a
#: phantom unseen blocker is placed. 38-48u beyond ``r`` at HEAD; 48-58u since a one-walked-frame press is judged at
#: the most it can carry him (Rate.reach: a tick and its tail, 60u, where an average frame said 45u). Pinned strict:
#: the day the planner stops creeping, this case passes and says so.
_CREEP_BAND = pytest.mark.xfail(strict=True, reason="the creep band (48-58u beyond r at 60 fps): the walk creeps round a "
                                                    "held walker and places a phantom blocker -- a planner weakness")


@pytest.mark.parametrize("speed, at", [(40.0, 170), pytest.param(60.0, 210, marks=_CREEP_BAND), (60.0, 215)])
def test_a_walker_held_on_him_at_its_own_pace_is_stepped_away_from(game, speed, at):
    """350's children outpace his run (~40u a frame to his 30), and the engine undoes the WHOLE of a walker's step into
    him (MoveToward.cs:187-189): one walking straight at him stops anywhere up to a step short of contact -- here 18u
    and 63u beyond ``r``, where the contact of his own walk (HALF_STEP past ``r``) never reaches. Judged so, it was
    never held on him: the box outlasted the wait -- ``boxed``, a strike. Judged by the walker's own step
    (:meth:`_walker_step`) it is held all the same: he steps off the line it walks, it walks on, and so does he.
    (58u off -- the case this test ran before the render-rate fix -- now sits in THE CREEP BAND, pinned as the known
    failure it is, _CREEP_BAND; 63u is clear of the band before the fix and after it.)"""
    fake = FakeGame(game)
    kid = _villager(-100, 500, uid=6, path=[(-100, 500), (-101, 500)], speed=0.01)   # creeping, along the line it walks
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -450, 0)
        fake.blockers = {30820: [kid]}
        published(g, lambda s: s.objects and s.objects[0]["moving"])
        g.ROUTE_NPC_REPLANS = 0
        g.ROUTE_WALKER_BUDGET_SECONDS = 160 / 60
        stood = _step_in_front(g, (kid, (at, 0), [(at, 0), (-1100, 0)], speed))     # along his line, into him
        rec = g.route_to(450.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), npcs=True, smooth=True)
        assert stood, "premise: it walked into him"
        assert rec["reached"] and not rec["boxed"] and rec["box_cleared"] >= 1, rec
        assert (6, "body", True) in [(o["uid"], o["kind"], o["moving"]) for o in rec["boxers"]], rec
        assert kid["x"] < stood[0][0] - 300, "freed, it walked on along its line"


def test_a_walker_held_on_him_since_before_the_call_is_stepped_off_the_line_at_him(game):
    """Session 2, crossings 25-30: each call began with the children already held on him, so none was ever seen
    walking -- no line to step off. Stepping straight AWAY from where it stands leaves him on its way: freed, it walks
    on after him and is held again. It is held BECAUSE its step comes at him, so the line it walks is the one at him:
    the step goes across it, and freed, it walks on past."""
    fake = FakeGame(game, walkmesh=(-1000, -1000, 1000, 1000))
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        kid = _villager(160, 0, uid=6, path=[(160, 0), (-900, 0)], speed=3.0)       # straight into him: held at 154
        leg, watch = _box_leg(g, fake, [kid], settled=lambda s: s.objects[0]["x"] < 155)
        leg["turned"] = ((("right",), (1.0, 0.0)), 6.0)          # an earlier hold's turn: known, to 2 degrees
        basis, since = g._axes[30820], {}
        for _ in range(12):
            if g._box_step(basis, leg, since):
                break
            g.wait_frames(8)
            g._npc_view(watch, g.state)
        else:
            pytest.fail("it never stepped out of the way of a walker held on him")
        assert watch["heading"].get(6) is None and watch["discs"][0]["dir"] is None, "premise: never seen walking"
        _buttons, u = leg["pressed"]
        assert abs(u[0]) < 0.1, f"straight across the line at him, not back along it: {u}"
        # a step along another line turned him toward IT: where the earlier hold left his yaw is no longer known
        # (a facing step would otherwise start from the wrong pad's yaw, Session._held_yaw)
        assert Session._held_yaw(leg) is None, leg["turned"]
        published(g, lambda s: s.objects[0]["x"] < -300)                  # freed, it walked on past him
        assert not fake.contacts, fake.contacts


def test_a_walker_held_on_him_beside_a_door_is_stepped_away_from_in_the_room_there(game):
    """The (-470, 142) spot of the session-2 log, 174u from 350's door to 354: a step of ROUTE_WALKER_HOLD_TICKS at a
    run could slide him 270u (its reach and the zone pad) -- into the door -- so beside it the step was refused
    outright, the wait for the walker waited on himself, and the box came back ``boxed``. The room there takes a
    SHORTER step, and away from the door where two are about as good: the walker walks on, and so does he, the door
    never entered."""
    from ff9mapkit.content import pathfind
    door = _rect(-560, 120, -240, 400)
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": door, "to": 30821, "arrive": (0, 0)}]}
    kid = _villager(-100, -500, uid=6, path=[(-100, -500), (-101, -500)], speed=0.01)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -450, 0)
        fake.blockers = {30820: [kid]}
        published(g, lambda s: s.objects and s.objects[0]["moving"])
        g.ROUTE_NPC_REPLANS = 0
        g.ROUTE_WALKER_BUDGET_SECONDS = 160 / 60
        stood = _step_in_front(g, (kid, (170, 0), [(170, 0), (-1100, 0)], 3.0))
        rec = g.route_to(450.0, 0.0, avoid=[door], walkmesh=_flat_bgi(), prior=_prior(), npcs=True, smooth=True)
        assert stood, "premise: it walked into him"
        gap = pathfind.poly_gap(stood[0][0], stood[0][1], door)
        step = g.rate().reach(g._frames_within(g.ROUTE_WALKER_HOLD_TICKS, g.rate()), "run")
        assert gap < step + g.PROBE_HAZARD_PAD, gap   # premise
        assert rec["reached"] and not rec["boxed"] and rec["box_cleared"] >= 1 and rec["landed"] is None, rec
        assert not fake.fired, fake.fired


def test_a_box_the_walkers_are_not_the_cause_of_is_boxed_at_once(game):
    """A villager STANDING in contact ahead boxes the leg on its own; a walker beside him refuses a press too. Any
    walker among the boxers used to make it a walkers' box -- the whole wait spent (ROUTE_WALKER_BUDGET_SECONDS, 8 s a
    crossing) for the same verdict. Judged by CAUSE, planned without the walker there is still no press: the spot,
    ``boxed`` at once, nothing pressed or waited."""
    fake = FakeGame(game, walkmesh=(-1000, -1000, 1000, 1000))
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        g.ROUTE_WALKER_BUDGET_SECONDS = 80 / 60
        sent = _counting(g)
        leg, watch = _box_leg(g, fake, [_villager(160, 0, uid=4),
                                        _villager(0, 165, uid=5, path=[(0, 165), (700, 165)], speed=0.3)])
        basis, here, goal = g._axes[30820], g._standing(), (1000.0, 0.0)
        assert g._plan_hold(basis, here, goal, leg) is None, "premise: boxed"
        assert {d["uid"] for d in g._boxers(basis, here, goal, leg)} == {4, 5}, "premise: the walker refuses one too"
        mark = len(sent)
        got = g._walk_leg(1000.0, 0.0, 45.0, leg, True)
        assert got == "boxed" and (watch["box_waits"], watch["boxers"], watch["boxed_by"]) == (0, [], None), watch
        assert sent[mark:] == [], sent[mark:]


def test_a_wanderer_seen_walking_that_stops_in_front_of_him_is_waited_for(game):
    """``moving`` is an instant's flag: a wanderer reads false at the turns of its loop (uid 6 in live 350). One the
    call has SEEN walking, standing now where the plan saw it, boxes the leg alone -- a walker all the same, so the box
    is waited on, not ``boxed`` at once as the spot; still standing when the wait runs out, it is ``boxed_by``
    walkers."""
    fake = FakeGame(game, walkmesh=(-1000, -1000, 1000, 1000))
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        g.ROUTE_WALKER_BUDGET_SECONDS = 40 / 60
        kid = _villager(160, 0, uid=6, path=[(160, 0), (160, 1)], speed=0.01)       # walking, barely
        leg, watch = _box_leg(g, fake, [kid])
        assert 6 in watch["walked"], "premise: seen walking"
        kid["_done"] = True                                                        # it stops: published standing
        published(g, lambda s: not s.objects[0]["moving"])
        g._npc_view(watch, g.state)
        got = g._walk_leg(1000.0, 0.0, 45.0, leg, True)
        assert got == "boxed" and watch["box_waits"] >= 1 and watch["boxed_by"] == "walkers", watch
        assert [o["uid"] for o in watch["boxers"]] == [6], watch["boxers"]


def test_what_walks_is_published_moving_or_seen_walking_by_the_call(game):
    """:meth:`_npc_walks`: published ``moving`` (a walker held on him still reads so), published ``moving`` by any read
    of the call (``walked``, :meth:`_npc_read`), or moved ROUTE_NPC_MOVED since the plan -- never jitter, and never an
    object only because the plan did not see it."""
    g = session(game, None)
    w: dict = {}
    g._npc_read(w, State({"frame": 5, "player": {"x": 0.0, "y": 0.0, "z": 0.0, "control": True},
                          "objects": [_obj(7, 0, 0, moving=True), _obj(8, 0, 0)]}))
    assert w["walked"] == {7}
    watch = {"planned": {1: (0.0, 0.0), 2: (0.0, 0.0), 3: (0.0, 0.0)}, "walked": {2}}

    def d(uid, x=0.0, moving=False):
        return {"uid": uid, "x": x, "z": 0.0, "moving": moving}
    assert g._npc_walks(d(1, moving=True), watch)
    assert g._npc_walks(d(2), watch)                   # standing at a turn: published moving by an earlier read
    assert g._npc_walks(d(3, x=20.0), watch)           # moved since the plan
    assert not g._npc_walks(d(3, x=5.0), watch)        # jitter
    assert not g._npc_walks(d(9), watch)               # never planned, never seen moving


def test_a_step_out_of_a_walkers_way_keeps_clear_of_a_trigger_the_plan_gave_up(game):
    """What a slide could carry the step into is kept out of his whole reach round him -- EVERY published trigger, not
    only the ones the plan kept: a Range the plan gave up (entered, or not in the way) fires just as surely. Beside
    one that leaves no room for even a walk frame, he does not step at all."""
    fake = FakeGame(game, walkmesh=(-1000, -1000, 1000, 1000))
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        kid = _villager(160, 0, uid=6, path=[(160, 0), (-900, 0)], speed=3.0)
        chest = _villager(0, -260, uid=7, range_r=200.0)                            # its Range 30u short of the pad
        leg, watch = _box_leg(g, fake, [kid, chest], settled=lambda s: s.objects[0]["x"] < 155)
        watch["keep"].discard((7, "trigger"))                                      # the plan gave its Range up
        g._npc_view(watch, g.state)
        assert not any(d["uid"] == 7 and d["kind"] == "trigger" for d in watch["discs"]), "premise: given up"
        basis, since = g._axes[30820], {}
        sent = _counting(g)
        for _ in range(8):
            assert not g._box_step(basis, leg, since)
            g.wait_frames(8)
            g._npc_view(watch, g.state)
        assert 6 in since and g.state.frame - since[6][2] >= g._frames_lasting(g.ROUTE_WALKER_HELD_SECONDS), (
            "premise: held on him")
        assert not [s for steps in sent for s in steps if s.startswith("hold")], sent
        assert not fake.touched, fake.touched


# ---- the session-3 door step: both attempts of the stock run at 350's door to 355 ended on the step, a Dali child (a
# talk-only walker, non-solid, r 152) held on him between him and the zone's one standable patch. The last leg's finish
# -- within 45u of a goal a few units inside the zone -- found no press, called that arrival, and each crossing came
# back a MISS: a REAL strike, and two made 355 unreachable. The finish now meets walkers as the rest of the walk does.
# A door at the east wall of the fake's room, 80u wide and standable (80u off the wall) only where x <= 520, its goal
# 4u in; he starts 34u short of it, outside the zone, so the finish takes over at once. A child standing against him
# there covers the whole standable patch, as the frame shows.

_DOOR = _rect(480, -40, 600, 40)
_DOOR_GOAL = (484.0, 0.0)


def _door_kid(uid, walks, at=(605.0, 0.0)):
    """A Dali child parked far off ON the line it will walk -- so the read that sees it step up to ``at`` (see
    :func:`_step_in_front`) reads a jump along that line, never a heading across it -- creeping: "on" walks on north,
    across the door; "into him" walks west, along his line into him, and is held."""
    x, z = at
    park = (x, z - 700) if walks == "on" else (x + 500, z)
    ahead = (park[0], park[1] + 1) if walks == "on" else (park[0] - 1, park[1])
    return _villager(*park, uid=uid, path=[park, ahead], speed=0.01)


def _door_step_up(kid, walks):
    """The :func:`_step_in_front` move of a child stepping up 155u in front of him on the door step: walking "on" north
    across the door at 1u a frame -- slow enough to stand in the way a while, too fast to read as held (ROUTE_NPC_MOVED
    in ROUTE_WALKER_HELD_SECONDS) -- or walking "into him", west along his line, where it is held."""
    if walks == "on":
        return (kid, (155, 0), [(155, 0), (155, 700)], 1.0)
    return (kid, (155, 0), [(155, 0), (-1100, 0)], 3.0)


def _door_fake(game, fake=None):
    """The fake with 350's door on the east wall of its room, a LIVE region (entering it fires, to 30821)."""
    fake = fake or FakeGame(game)
    fake.regions = {30820: [{"zone": _DOOR, "to": 30821, "arrive": (0, 0)}]}
    fake.exit_frames = 30
    return fake


def _door_start(g, fake, bodies, *, replans=0):
    """Standing 34u short of the door's goal, outside its zone, on 30820 with its basis known and ``bodies`` listed (and
    published). ``replans``: the movement re-plans the call may make -- session 3's crossing 13 had spent its four."""
    boot(g)
    g.warp(30820)
    g._axes[30820] = _prior()
    _stand(g, fake, 450, 0)
    fake.blockers = {30820: list(bodies)}
    published(g, lambda s: s.objects is not None and len(s.objects) == len(bodies))
    g.ROUTE_NPC_REPLANS = replans


def _cross_the_door(g):
    """The tour's own crossing call (dali_tour.Tour._cross) at the door: route_cross into its zone, smooth, npcs."""
    return g.route_cross(*_DOOR_GOAL, walkmesh=_flat_bgi(), prior=_prior(), unstick=True, zone=_DOOR, smooth=True,
                         npcs=True, timeout=3)


def _tour_module():
    sys.path.insert(0, str(REPO / "studies" / "story-trace"))
    import dali_tour
    return dali_tour


def test_a_walker_that_pins_him_on_the_door_step_and_walks_on_is_waited_for_and_he_crosses(game):
    """On the door step -- within tolerance of the goal, outside the zone -- a Dali child steps up against him, between
    him and the zone, and walks on across the door. Every press into the zone comes nearer it: the finish used to stop
    right there and call it arrival (the zone's gateway never fired: a MISS). A walker at the door is waited for as it
    is anywhere else: it walks on, the finish presses in, and the door fires -- the child named in ``boxers``."""
    fake = _door_fake(game)
    kid = _door_kid(4, "on")
    with session(game, fake) as g:
        _door_start(g, fake, [kid])
        stood = _step_in_front(g, _door_step_up(kid, "on"), past=440)
        rec = _cross_the_door(g)
        assert stood, "premise: the child stepped up on the door step"
        assert rec["landed"] == 30821 and [f["to"] for f in fake.fired] == [30821], rec
        assert rec["box_waits"] >= 1 and rec["box_cleared"] >= 1 and not rec["boxed"], rec
        assert (4, "body", True) in [(o["uid"], o["kind"], o["moving"]) for o in rec["boxers"]], rec


@pytest.mark.parametrize("replans", [0, 4])
def test_a_walker_held_on_him_on_the_door_step_is_stepped_away_from_and_he_crosses(game, replans):
    """The session-3 frame: the child walked INTO him on the door step and is held there -- the engine undoes every step
    a scripted walker takes into him (MoveToward.cs:187-189; the fake: `_step_walkers`) -- so a wait for it waits on
    himself. Once it has not moved in ROUTE_WALKER_HELD_SECONDS he steps out of its way; it walks on, and he presses into
    the zone and crosses. With the movement re-plans spent (0) the plan still keeps the child's disc and the finish
    finds no press at all; with them left (4) a re-plan gives the child up to walk through -- it stands over the goal --
    and the presses into the zone are made, and held: two held presses, a walker holding him, the same wait and step
    (and the step is taken from a walker the plan gave up: it is held on him all the same)."""
    fake = _door_fake(game)
    kid = _door_kid(6, "into him")
    with session(game, fake) as g:
        _door_start(g, fake, [kid], replans=replans)
        g.ROUTE_WALKER_BUDGET_SECONDS = 4.0
        stood = _step_in_front(g, _door_step_up(kid, "into him"), past=440)
        t0 = time.time()
        rec = _cross_the_door(g)
        assert stood and time.time() - t0 < 60, "bounded"
        if replans:
            assert rec["npc_replans"] >= 1 and 6 in [o["uid"] for o in rec["through"]], "premise: planned through"
        assert rec["landed"] == 30821 and [f["to"] for f in fake.fired] == [30821], rec
        assert rec["box_cleared"] >= 1 and (6, "body", True) in [(o["uid"], o["kind"], o["moving"])
                                                                 for o in rec["boxers"]], rec
        assert kid["x"] < stood[0][0], "freed, it walked on along its line, past where he stood"


def test_a_walker_that_holds_him_on_the_door_step_past_the_wait_is_the_village_not_the_door(game):
    """The same child held on him on the door step, and no step out of its way that the room allows (taken out here):
    the wait for it runs out (ROUTE_WALKER_BUDGET_SECONDS, bounded) and the crossing ends short of the zone, the door unfired.
    The record says why -- ``boxed_by`` walkers, ``held_by`` walkers, the child in ``pinned`` -- and the tour's strike
    rule reads it as the village in the way, LIVE: never the door's MISS."""
    D = _tour_module()
    fake = _door_fake(game)
    kid = _door_kid(6, "into him")
    with session(game, fake) as g:
        _door_start(g, fake, [kid])
        g.ROUTE_WALKER_BUDGET_SECONDS = 80 / 60
        g._box_step = lambda *a, **kw: False
        stood = _step_in_front(g, _door_step_up(kid, "into him"), past=440)
        t0 = time.time()
        rec = _cross_the_door(g)
        assert stood and time.time() - t0 < 60, "bounded: the wait has a budget"
    assert rec["landed"] is None and rec["inside"] is False and rec["reached"] and not fake.fired, rec
    assert rec["boxed"] and rec["boxed_by"] == "walkers" and rec["box_waits"] >= 1, rec
    assert rec["held_by"] == "walkers" and [(o["uid"], o["kind"], o["moving"]) for o in rec["pinned"]] == [
        (6, "body", True)], rec
    assert D.failure(rec) == "live", rec


def test_a_body_that_does_not_walk_in_the_doorway_is_the_doors_miss_at_once(game):
    """A villager who never walks stands in the doorway, against him on the door step, over the zone's whole standable
    strip within reach. Nothing will walk off: no wait, no step, no push -- the finish ends short of the zone at once
    (bounded), and it is a MISS as it always was, REAL. The record names the body (``pinned``, ``held_by`` "bodies"),
    so a strike on a door is never a walker's doing unseen."""
    D = _tour_module()
    fake = _door_fake(game)
    with session(game, fake) as g:
        _door_start(g, fake, [_creeping(4)])
        settle, placed = g.settle, []

        def settle_then_stand_there(*a, **kw):
            st = settle(*a, **kw)
            if not placed and st.player_x is not None and st.control:
                # it was never in any plan and never walked: nothing the call saw says it could walk off
                placed.append((st.player_x, st.player_z))
                fake.blockers[30820].append(_villager(st.player_x + 155, st.player_z, uid=7))
                return published(g, lambda s: s.objects and any(o["uid"] == 7 for o in s.objects))
            return st
        g.settle = settle_then_stand_there
        sent = _counting(g)
        t0 = time.time()
        rec = _cross_the_door(g)
        assert placed and time.time() - t0 < 30, "bounded"
    assert rec["landed"] is None and rec["inside"] is False and rec["reached"] and not fake.fired, rec
    assert (rec["boxed"], rec["box_waits"], rec["waits"], rec["pushes"], rec["boxers"]) == (False, 0, 0, 0, []), rec
    assert rec["held_by"] == "bodies" and [(o["uid"], o["moving"]) for o in rec["pinned"]] == [(7, False)], rec
    assert len(sent) <= 3, f"no waiting, stepping or pushing: {sent}"
    assert D.failure(rec) == "miss", rec


def test_standing_in_a_dead_zone_is_a_miss_whatever_held_him_on_the_way(game):
    """The story has shut the door (the zone is there, nothing fires). A child held on him on the door step is stepped
    away from, the finish presses into the zone, and he stands IN it with nothing fired: a MISS, REAL, exactly as
    before -- whatever the walk met on the way. Nothing holds him short of a zone he stands in: ``held_by`` None,
    ``pinned`` empty. The door has no facing gate, so nothing turns him to it (``faced`` None): one that fires for
    anyone standing in it and has not is shut."""
    D = _tour_module()
    fake = _door_fake(game)
    fake.regions = {}
    kid = _door_kid(6, "into him")
    with session(game, fake) as g:
        _door_start(g, fake, [kid])
        g.ROUTE_WALKER_BUDGET_SECONDS = 4.0
        stood = _step_in_front(g, _door_step_up(kid, "into him"), past=440)
        rec = _cross_the_door(g)
        assert stood, "premise: the child walked into him"
    assert rec["box_cleared"] >= 1, f"premise: the child held him on the way ({rec})"
    assert rec["inside"] is True and rec["landed"] is None and not fake.fired, rec
    assert rec["held_by"] is None and rec["pinned"] == [] and rec["faced"] is None and rec["face_gate"] is None, rec
    assert D.failure(rec) == "miss", rec


def test_the_tour_reads_a_walk_held_short_of_the_zone_by_walkers_as_live():
    """The strike rule, record by record: short of the zone with walkers in the way to a spot of it he could have
    entered with them gone (``held_by`` walkers) is the village, LIVE; held by a body that does not walk, or by nothing
    published (the door's geometry:
    350's door to 353, standable only in a 34u wedge), a MISS as before -- waits on the way or not, since the walk came
    within tolerance; standing IN the zone, a MISS whatever held him; walkers that outlasted the wait, LIVE."""
    D = _tour_module()
    short = {"boxed": False, "boxed_by": None, "reached": True, "inside": False, "during": None, "route": 2,
             "waits": 0, "pushes": 0, "blockers": [], "frozen": False, "npc_replans": 0, "box_waits": 0,
             "held_by": None, "pinned": []}
    assert D.failure(dict(short, held_by="walkers", pinned=[(13, "body", True)])) == "live"
    assert D.failure(dict(short, held_by="bodies", pinned=[(7, "body", False)])) == "miss"
    assert D.failure(short) == "miss"                                                   # the spot
    assert D.failure(dict(short, waits=2, npc_replans=2)) == "miss"                 # session 3's 353 wedge, as before
    assert D.failure(dict(short, inside=True, box_waits=4, box_cleared=1)) == "miss"    # in the zone, nothing fired
    assert D.failure(dict(short, boxed=True, boxed_by="walkers", held_by="walkers")) == "live"
    assert D.failure(dict(short, held_by="walkers", error="crossing ... never became playable")) == "miss"


# ---- the door step, judged PER CAUSE: a walker counts at the zone's edge only where it is what keeps him out -- in the
# way to a spot of the zone he could get into with every walker gone (Session._short_of_zone). A door dead by its own
# geometry, or held shut by a villager who never walks, is the door's REAL miss however many walkers pace nearby: read
# as the village it was three LIVE attempts and a replay retried without end, where two strikes break a dead door. And
# the record is the finish's own verdict, never a second look taken after the walk toward another point.

_DEAD = _rect(530, -40, 600, 40)        # wholly inside the east wall's 80u clearance: nowhere his centre can stand in it


def _pacer(uid, x=600.0, z=180.0, beat=60.0):
    """A villager pacing a short beat at 1u a frame, from (x, z) ``beat`` north and back: near the door step, never in
    contact with him there, never across the way in."""
    return _villager(x, z, uid=uid, path=[(x, z), (x, z + beat)], speed=1.0)


@pytest.mark.parametrize("walker", ["paces a beat nearby", "is held on him from the door's side"])
def test_a_dead_door_is_the_doors_miss_whatever_walker_is_about(game, walker):
    """The zone lies wholly inside the wall's clearance (the fake's floor walled as the planner's is): there is no spot
    in it his centre can stand, and a villager is about -- pacing a short beat 180-253u off the door step (the review's
    probe: 6 of 6 runs LIVE), or walked into him from the north-east, the door's side, and held there in contact. With
    every walker gone the door is no more his to enter, so no walker is the cause: the finish ends short of the zone
    at once -- no wait, no step -- and the tour strikes the door (REAL miss). ``held_by`` None, ``pinned`` empty: the
    finish's own verdict (a look taken again after the walk, toward another point, had named the pacer)."""
    D = _tour_module()
    fake = _door_fake(game)
    fake.walkmesh, fake.clearance = _flat_bgi(), 80.0
    fake.regions = {30820: [{"zone": _DEAD, "to": 30821, "arrive": (0, 0)}]}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        g.ROUTE_WALKER_BUDGET_SECONDS = 2.0
        if walker == "paces a beat nearby":
            _stand(g, fake, 400, 0)
            fake.blockers = {30820: [_pacer(5)]}
            published(g, lambda s: s.objects and s.objects[0]["moving"])
            stood = [(400.0, 0.0)]
        else:
            _stand(g, fake, 500, 0)
            kid = _villager(908, 974, uid=5, path=[(908, 974), (907, 972)], speed=0.01)   # parked on its line, at him
            fake.blockers = {30820: [kid]}
            published(g, lambda s: s.objects and s.objects[0]["moving"])
            stood = _step_in_front(g, (kid, (60, 143), [(60, 143), (-366, -872)], 3.0), past=440)
        t0 = time.time()
        rec = g.route_cross(540.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), unstick=True, zone=_DEAD, smooth=True,
                            npcs=True, timeout=3)
        assert stood and time.time() - t0 < 30, "bounded"
    assert rec["landed"] is None and rec["inside"] is False and rec["reached"] and not fake.fired, rec
    assert (rec["boxed"], rec["box_waits"], rec["box_cleared"], rec["boxers"]) == (False, 0, 0, []), rec
    assert (rec["held_by"], rec["pinned"]) == (None, []), rec
    assert D.failure(rec) == "miss", rec


def test_a_still_villager_in_the_doorway_is_the_doors_miss_with_a_walker_pacing_nearby(game):
    """A villager who never walks stands in the doorway against him, over the zone's whole standable strip within
    reach, and another paces a short beat ~200u off the door's axis (the review's probe: LIVE in 4 of 6 runs). The still
    one keeps him out, and would with every walker gone: nothing is waited on, and it is the door's MISS -- the record
    naming the still body alone (``held_by`` "bodies"), never the pacer."""
    D = _tour_module()
    fake = _door_fake(game)
    with session(game, fake) as g:
        _door_start(g, fake, [_creeping(4), _pacer(9, z=200.0)])
        g.ROUTE_WALKER_BUDGET_SECONDS = 2.0
        settle, placed = g.settle, []

        def settle_then_stand_there(*a, **kw):
            st = settle(*a, **kw)
            if not placed and st.player_x is not None and st.control:
                placed.append((st.player_x, st.player_z))
                fake.blockers[30820].append(_villager(st.player_x + 155, st.player_z, uid=7))
                return published(g, lambda s: s.objects and any(o["uid"] == 7 for o in s.objects))
            return st
        g.settle = settle_then_stand_there
        t0 = time.time()
        rec = _cross_the_door(g)
        assert placed and time.time() - t0 < 30, "bounded"
    assert rec["landed"] is None and rec["inside"] is False and rec["reached"] and not fake.fired, rec
    assert (rec["boxed"], rec["box_waits"], rec["boxers"]) == (False, 0, []), rec
    assert rec["held_by"] == "bodies" and [(o["uid"], o["moving"]) for o in rec["pinned"]] == [(7, False)], rec
    assert D.failure(rec) == "miss", rec


def test_an_end_of_the_finish_that_pressed_nothing_is_judged_like_any_other(game):
    """No hold left to press (ROUTE_HOLDS spent -- here none at all): the finish ends where it stands, 34u short of the
    door, as a child steps up across the way in. That end is judged as every other end of the finish is -- the child
    stands in the way to a spot of the zone he could enter with it gone -- so it is waited on until it has walked on
    (``box_waits``, named in ``boxers``), never recorded as holding him without a wait (a LIVE for nothing) nor left
    unasked (a door's MISS for the village's doing). After it has gone nothing stands in the way, and the end is the
    door's: ``held_by`` None, a MISS -- no hold was pressed at all."""
    D = _tour_module()
    fake = _door_fake(game)
    kid = _door_kid(4, "on")
    with session(game, fake) as g:
        _door_start(g, fake, [kid])
        g.ROUTE_HOLDS = 0
        stood = _step_in_front(g, _door_step_up(kid, "on"), past=440)
        rec = _cross_the_door(g)
        assert stood, "premise: the child stepped up on the door step"
    assert rec["landed"] is None and rec["inside"] is False and not fake.fired, rec
    assert rec["box_waits"] >= 1 and (4, "body", True) in [(o["uid"], o["kind"], o["moving"])
                                                           for o in rec["boxers"]], rec
    assert (rec["held_by"], rec["pinned"]) == (None, []), rec
    assert D.failure(rec) == "miss", rec


def test_a_walker_pacing_a_short_beat_beside_him_is_never_held_on_him(game):
    """A villager 206u off him paces to and fro, and every read finds it 12u from the last -- across a turn of its beat,
    back where it stood: within one of its own steps of contact (a step is judged at 2 * RUN_TICK at the least), and
    never ROUTE_NPC_MOVED from where it was first seen, so read end to end it has "not moved" in ROUTE_WALKER_HELD_SECONDS
    frames. It walked all that while -- the engine never undid a step of it (MoveToward.cs:187-189) -- so it is not
    held on him, and he is never stepped away from it (the review's pacer, on a 60u beat, read as held at a turn and had
    him stepped 210u off the door, twice). What moved is summed read to read. Its reads are placed by hand: a pacer
    walked by the fake is read at a cadence its own period can alias, and the test would be a coin toss."""
    fake = FakeGame(game, walkmesh=(-1000, -1000, 1000, 1000))
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        pacer = _villager(0, 206, uid=5, path=[(0, 206), (0, 9000)], speed=0.001)     # published moving; placed below
        leg, watch = _box_leg(g, fake, [pacer])
        basis, since = g._axes[30820], {}
        frame0 = g.state.frame
        for k in range(16):
            z = (206.0, 218.0, 206.0, 194.0)[k % 4]
            pacer["z"] = z
            g._npc_view(watch, published(g, lambda s, z=z: s.objects and abs(s.objects[0]["z"] - z) < 0.5))
            assert not g._box_step(basis, leg, since), f"stepped out of the way of a pacer (read {k}, z {z})"
            g.wait_frames(8)
        held = g._frames_lasting(g.ROUTE_WALKER_HELD_SECONDS)
        assert g.state.frame - frame0 >= 4 * held, "premise: read over several ROUTE_WALKER_HELD_SECONDS spans"


# ---- Tour.replay (rung-3 predictions v2): session 2's sides walked Dali in different ORDERS -- every stock run boxed at
# 350 -> 355 and saw 355 after 450, every F0 run crossed it first -- and SByte[296] wrote the order into the trace. An F0
# run now walks its stock partner's ENTERED walk step for step, under the tour's own crossing call and strike rules,
# and only then tours blind. A three-room world on the fake: A (30820) with a door east to B (30821) and one west to C
# (30810), each of those a door back; the Tour's own model of it has the same doors, the fake's flat floor, every
# room in "Dali/", no door one-way.

_A, _B, _C = 30820, 30821, 30810
_EAST, _WEST = _rect(400, -150, 600, 150), _rect(-600, -150, -400, 150)


class _StoryFake(FakeGame):
    """The fake with the three things a replay meets that the stand-in does not model: the story moving on
    (``advance`` = (field, SC): arriving in that field sets the scenario, as Garnet's scene does); a room that never
    hands control over (``bounce`` = {field: (back to, arrive)}: ``bounce_frames`` after he arrives it puts him back
    where he came from -- stock 353, Mayor Kapu's arrival scene); and a villager in the way who walks off while the
    camera looks (a screenshot -- the tour takes one after every LIVE miss -- lifts every freeze)."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.advance = None
        self.bounce: dict = {}
        self.bounce_frames = 0

    def _step_exit_now(self) -> None:
        super()._step_exit_now()
        if self.advance and self.field_id == self.advance[0]:
            self.scenario = self.advance[1]
        back = self.bounce.get(self.field_id)
        if back is not None:
            self.control = False
            self._exit = (self.frame + self.bounce_frames, back[0], tuple(back[1]))

    def _write_png(self, name: str) -> None:
        super()._write_png(name)
        self._frozen_until = 0


class _MissOnceFake(_StoryFake):
    """A door that misses the first time he walks in (``miss_once`` = (field, zone)): nothing fires while he stays in
    its zone, and it is live again once he has left it. Session 2's two same-exit retries after a miss started inside
    the zone, travelled 0 and missed again; a replay has no other exit to try in between, and walks back out first.
    Kept as that regression. What it is NOT is a model of the engine's doors: the engine runs a region's tag 2 every
    tick he stands in it with control (EventEngine.ProcessEvents.cs:174-178 -> EventCollision.cs:281-284, at stock
    6b8bb2d5), so a door with no gate fires for someone standing in it as surely as for someone walking in -- one that
    stays shut while he stands there is shut to HIM, and what shut 350's in session 2 was stock's door FACING GATE
    (content.doorface; FakeGame ``regions`` ``"face"``): he stood facing away."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.miss_once = None
        self._missed = False

    def _enter_regions(self) -> None:
        from ff9mapkit.content import pathfind
        if self.miss_once is not None and self.field_id == self.miss_once[0]:
            poly = [(float(p[0]), float(p[1])) for p in self.miss_once[1]]
            if pathfind.poly_gap(self.player[0], self.player[2], poly) < 0:
                self._missed = True
                return
            if self._missed:
                self.miss_once = None              # he left the zone: the door is live again
        super()._enter_regions()


def _replay_world(game, monkeypatch, cls=None):
    """``(fake, tour, dali_tour)``: the three rooms on the fake (``cls``, default :class:`_StoryFake`) -- every door a
    live region -- and a Tour over the same doors. The crossing wait is cut to 1.5 s (a bounce outlasts it, as 353's
    scene outlasts the tour's 20 s)."""
    sys.path.insert(0, str(REPO / "studies" / "story-trace"))
    import dali_tour
    monkeypatch.setattr(dali_tour, "CROSS_TIMEOUT", 1.5)
    fake = (cls or _StoryFake)(game, fps=960)
    fake.regions = {_A: [{"zone": _EAST, "to": _B, "arrive": (-250, 0)}, {"zone": _WEST, "to": _C, "arrive": (250, 0)}],
                    _B: [{"zone": _WEST, "to": _A, "arrive": (250, 0)}],
                    _C: [{"zone": _EAST, "to": _A, "arrive": (-250, 0)}]}
    fake.exit_frames = 30
    floor = _flat_bgi()

    class WorldTour(dali_tour.Tour):
        def label(self, fid):
            return "Dali/Test"

        def floor(self, fid):
            return floor

        def one_way(self, fid, i):
            return False

    tour = WorldTour(stock=lambda fid: None, tag="test")
    tour._gates = {_A: [(_B, 0, _EAST), (_C, 0, _WEST)], _B: [(_A, 0, _WEST)], _C: [(_A, 0, _EAST)]}
    return fake, tour, dali_tour


def _replay_start(g, fake):
    """Standing in A at SC 2600 with control, each room's basis known (the walks, not calibration, are on test)."""
    boot(g)
    g.warp(_A)
    fake.scenario = 2600
    _stand(g, fake, 0, 0)
    published(g, lambda s: s.scenario == 2600)
    for fid in (_A, _B, _C):
        g._priors[fid] = g._axes[fid] = _prior()
    return []


def _replayed(log):
    return [(x["leg"], x.get("step"), x.get("expect"), x["entered"], x["verdict"]) for x in log if x["k"] == "cross"]


def test_a_replay_walks_the_partners_walk_step_for_step_and_stops_where_the_story_moves(game, monkeypatch):
    """Each step is crossed by the tour's own route_cross call and must ENTER the partner's place; every crossing is
    logged like a tour crossing with leg "replay", its step, the place it expected and the place it entered -- so the
    replayed walk reads back off the log as exactly the partner's. The story moving on stops it, as the tour stops."""
    fake, tour, D = _replay_world(game, monkeypatch)
    fake.advance = (_C, 2610)
    walk = [[_A, 0, _B], [_B, 0, _A], [_A, 1, _C]]
    with session(game, fake) as g:
        log = _replay_start(g, fake)
        stop = tour.replay(g, log, walk, beat=2600, max_crossings=20, max_passes=2, budget_s=120)
    assert stop.startswith(f"SC left 2600: now 2610 in field {_C} (replayed 3 of 3 steps"), stop
    assert _replayed(log) == [("replay", 1, _B, _B, "replayed"), ("replay", 2, _A, _A, "replayed"),
                              ("replay", 3, _C, _C, "replayed")], log
    assert D.entered_walk(log, legs=("replay",)) == walk
    assert [f["to"] for f in fake.fired] == [_B, _A, _C], fake.fired


def test_a_live_miss_in_a_replay_is_retried_in_the_same_room_not_struck(game, monkeypatch):
    """A villager in the way (a freeze with control held, for good -- until he walks off) makes the step's first
    crossing LIVE by the tour's own failure(): it strikes nothing, and the step is crossed again from the same room --
    a replay has no other exit to take and no other order to try."""
    fake, tour, D = _replay_world(game, monkeypatch)
    fake.freezes = {_A: [{"zone": _rect(100, -600, 200, 600), "frames": None}]}      # a band across A, before B's door
    fake.advance = (_B, 2610)
    with session(game, fake) as g:
        log = _replay_start(g, fake)
        g.ROUTE_WAIT_SECONDS = 0.5
        stop = tour.replay(g, log, [[_A, 0, _B]], beat=2600, max_crossings=20, max_passes=2, budget_s=120)
    assert fake._froze, "premise: the walk never stepped on the freeze"
    assert stop.startswith(f"SC left 2600: now 2610 in field {_B} (replayed 1 of 1 steps"), stop
    first, *_rest, last = [x for x in log if x["k"] == "cross"]
    assert first["frozen"] and D.failure(first) == "live" and first["verdict"] == "live 1 (retried)", first
    assert first["entered"] is None and first["now"] == _A, first
    assert (last["step"], last["entered"], last["verdict"]) == (1, _B, "replayed"), last
    assert all(x["step"] == 1 and not x.get("back") for x in log if x["k"] == "cross")    # LIVE: no step back


def test_a_replay_that_enters_another_place_stops_the_run_at_that_step(game, monkeypatch):
    """The partner entered B through A's east door; here that door leads to C. Entering a different place breaks the
    replay at once -- no strike, no retry, no tour after it: the run's walk is no longer its partner's."""
    fake, tour, _D = _replay_world(game, monkeypatch)
    fake.regions[_A][0].update(to=_C, arrive=(250, 0))
    with session(game, fake) as g:
        log = _replay_start(g, fake)
        stop = tour.replay(g, log, [[_A, 0, _B], [_B, 0, _A]], beat=2600, max_crossings=20, max_passes=2,
                           budget_s=120)
    assert stop == f"replay broke at step 1 ({_A}.0 -> {_B}): entered {_C}", stop
    assert _replayed(log) == [("replay", 1, _B, _C, f"diverged: entered {_C}")], log


def test_a_replay_step_that_can_only_be_missed_is_struck_out(game, monkeypatch):
    """The story shut B's door (the zone is there, nothing fires): standing inside it is a REAL miss by the tour's
    rule, and BOUNCES of them break the replay -- a step that cannot be entered is not retried for ever, though the
    retry does walk in anew from where the step began. A step whose place is not where he stands breaks it before
    any crossing."""
    fake, tour, D = _replay_world(game, monkeypatch)
    fake.regions[_A] = fake.regions[_A][1:]
    with session(game, fake) as g:
        log = _replay_start(g, fake)
        stop = tour.replay(g, log, [[_A, 0, _B]], beat=2600, max_crossings=20, max_passes=2, budget_s=120)
        assert stop == f"replay broke at step 1 ({_A}.0 -> {_B}): miss, miss", stop
        cross = [x for x in log if x["k"] == "cross"]
        assert [(x["inside"], x.get("back", False), x["verdict"]) for x in cross] == [
            (True, False, f"miss 1/{D.BOUNCES}"), (None, True, "stepped back"),
            (True, False, f"miss 2/{D.BOUNCES} -> the step fails")], log
        assert cross[2]["travelled"] > 0, cross[2]
        elsewhere = tour.replay(g, [], [[_B, 0, _A]], beat=2600, max_crossings=20, max_passes=2, budget_s=120)
    assert elsewhere == f"replay broke at step 1 ({_B}.0 -> {_A}): he stands in place {_A} (field {_A}), not {_B}"


def test_a_real_miss_in_a_replay_is_retried_from_where_the_step_began(game, monkeypatch):
    """A miss leaves him INSIDE the zone, and a retry from there walks nowhere and fires nothing (session 2: both
    same-exit retries after a miss travelled 0 and missed again). So the replay walks him BACK to the spot the step
    began on -- a walk that strikes nothing, logged as a replay crossing with ``back`` -- and the retry walks in anew:
    here the door that missed the first time fires on the second walk in."""
    fake, tour, D = _replay_world(game, monkeypatch, _MissOnceFake)
    fake.miss_once = (_A, _EAST)
    fake.advance = (_B, 2610)
    with session(game, fake) as g:
        log = _replay_start(g, fake)
        stop = tour.replay(g, log, [[_A, 0, _B]], beat=2600, max_crossings=20, max_passes=2, budget_s=120)
    assert fake._missed and fake.miss_once is None, "premise: the first walk in missed, and he left the zone after"
    assert stop.startswith(f"SC left 2600: now 2610 in field {_B} (replayed 1 of 1 steps"), stop
    miss, back, retry = [x for x in log if x["k"] == "cross"]
    assert (miss["inside"], miss["verdict"]) == (True, f"miss 1/{D.BOUNCES}"), miss
    assert (back["back"], back["target"], back["entered"], back["verdict"]) == (True, [0, 0], None,
                                                                                "stepped back"), back
    assert back["travelled"] > 0 and (retry["entered"], retry["verdict"]) == (_B, "replayed"), (back, retry)
    assert [x["step"] for x in (miss, back, retry)] == [1, 1, 1]
    assert [f["to"] for f in fake.fired] == [_B], fake.fired
    assert D.entered_walk(log, legs=("replay",)) == [[_A, 0, _B]]


def test_a_crossing_that_moves_the_story_on_is_never_judged(game, monkeypatch):
    """The story moving on stops the replay where it happens -- read right after the crossing, BEFORE it is judged:
    where the story's own move took him is the fork's doing. Here A's east door leads to C, not to the partner's B,
    and arriving in C moves the story on: no divergence and no strike, "the story moved on", and the run stops as the
    tour stops, "SC left"."""
    fake, tour, _D = _replay_world(game, monkeypatch)
    fake.regions[_A][0].update(to=_C, arrive=(250, 0))
    fake.advance = (_C, 2610)
    with session(game, fake) as g:
        log = _replay_start(g, fake)
        stop = tour.replay(g, log, [[_A, 0, _B], [_B, 0, _A]], beat=2600, max_crossings=20, max_passes=2,
                           budget_s=120)
    assert stop == f"SC left 2600: now 2610 in field {_C} (replayed 0 of 2 steps, crossing 1)", stop
    assert _replayed(log) == [("replay", 1, _B, _C, f"the story moved on (entered {_C})")], log


def test_a_bounce_the_partner_entered_is_a_replayed_step_that_leaves_him_where_he_was(game, monkeypatch):
    """Stock 353: the gateway works, the arrival scene never hands control over, and he is put back where he came
    from. The partner's walk holds that step (it ENTERED 353), so the replay must enter it too: route_cross's error
    names the room it reached, nothing landed, and the next step starts from the room he was put back in."""
    fake, tour, D = _replay_world(game, monkeypatch)
    fake.bounce = {_C: (_A, (-250, 0))}
    fake.bounce_frames = 3000                                    # ~3 s at 960 fps: past the 1.5 s crossing wait
    fake.advance = (_B, 2610)
    walk = [[_A, 1, _C], [_A, 0, _B]]
    with session(game, fake) as g:
        log = _replay_start(g, fake)
        stop = tour.replay(g, log, walk, beat=2600, max_crossings=20, max_passes=2, budget_s=120)
    assert stop.startswith(f"SC left 2600: now 2610 in field {_B} (replayed 2 of 2 steps"), stop
    bounce, into_b = [x for x in log if x["k"] == "cross"]
    assert f"reached field {_C}, but it never became playable" in bounce["error"] and bounce["landed"] is None, bounce
    assert (bounce["entered"], bounce["now"], bounce["verdict"]) == (_C, _A, "replayed"), bounce
    assert (into_b["step"], into_b["entered"], into_b["verdict"]) == (2, _B, "replayed"), into_b
    assert D.entered_walk(log, legs=("replay",)) == walk


def test_a_bounce_over_inside_the_crossing_wait_still_entered_its_room(game, monkeypatch):
    """353's scene can hand control back in the room he came from INSIDE the crossing's wait: route_cross then finds
    the origin playable, ``landed`` names the origin and there is no error to read. The crossing ENTERED 353 all the
    same, and its record says so -- ``changed_to``, the field the id first went to -- so the partner's walk and the
    replay name the step alike however long the scene took (read off ``landed``, the replay 'diverged' into the room
    it stood in)."""
    fake, tour, D = _replay_world(game, monkeypatch)
    fake.bounce = {_C: (_A, (-250, 0))}
    fake.bounce_frames = 200                                     # ~0.2 s at 960 fps: inside the 1.5 s crossing wait
    fake.advance = (_B, 2610)
    walk = [[_A, 1, _C], [_A, 0, _B]]
    with session(game, fake) as g:
        log = _replay_start(g, fake)
        stop = tour.replay(g, log, walk, beat=2600, max_crossings=20, max_passes=2, budget_s=120)
    assert stop.startswith(f"SC left 2600: now 2610 in field {_B} (replayed 2 of 2 steps"), stop
    bounce, into_b = [x for x in log if x["k"] == "cross"]
    assert (bounce["landed"], bounce["changed_to"], bounce.get("error")) == (_A, _C, None), bounce
    assert (bounce["entered"], bounce["verdict"]) == (_C, "replayed"), bounce
    assert D.entered_walk(log, legs=("replay",)) == walk
    assert [f["to"] for f in fake.fired] == [_C, _B], fake.fired


def test_after_the_whole_walk_the_run_tours_blind_on_the_budget_left(game, monkeypatch):
    """The partner's walk replayed and the story still at the beat: the run goes on as the blind tour -- its crossing
    count and clock carried on, its stop reasons the tour's -- so a fork whose story moves on later than its
    partner's still gets its chance."""
    fake, tour, _D = _replay_world(game, monkeypatch)
    fake.advance = (_C, 2610)
    with session(game, fake) as g:
        log = _replay_start(g, fake)
        stop = tour.replay(g, log, [[_A, 0, _B]], beat=2600, max_crossings=20, max_passes=2, budget_s=120)
    cross = [x for x in log if x["k"] == "cross"]
    assert (cross[0]["leg"], cross[0]["verdict"]) == ("replay", "replayed"), cross[0]
    assert cross[1:] and all(x["leg"] in ("tour", "back") and "step" not in x for x in cross[1:]), cross
    assert [x["n"] for x in cross] == list(range(1, len(cross) + 1)), cross
    assert stop == f"SC left 2600: now 2610 in field {_C} (pass 1, crossing {len(cross)})", stop
    assert cross[-1]["entered"] == _C and fake.fired[-1]["to"] == _C


@pytest.mark.parametrize("leg", ["replay", "tour"])
@pytest.mark.parametrize("kid_walks", ["on", "into him"])
def test_a_door_a_walker_held_him_at_is_crossed_by_the_tour_and_the_replay_alike(game, monkeypatch, leg, kid_walks):
    """Session 3's stock run, through the tour's own crossing call (Tour._cross -- the one route_cross call the tour and
    the replay both make): on A's door step a child steps up against him and walks on, or walks into him and is held
    there. The crossing used to come back a MISS, a REAL strike (two made the door unreachable). Now the walker is
    waited on or stepped away from and the door is crossed: no strike, and the replay's step is replayed as the tour's
    is crossed. A's east door: its goal 4u inside the zone, he 34u short of it."""
    fake, tour, D = _replay_world(game, monkeypatch)
    fake.advance = (_B, 2610)
    door = _rect(400, -40, 600, 40)                    # A's east door, 80u wide: the child covers its standable patch
    fake.regions[_A][0]["zone"] = door
    tour._gates[_A] = [(_B, 0, door), (_C, 0, _WEST)]
    tour.goal_for = lambda fid, i: (404, 0) if (fid, i) == (_A, 0) else D.Tour.goal_for(tour, fid, i)
    kid = _door_kid(6, kid_walks, at=(525.0, 0.0))
    with session(game, fake) as g:
        log = _replay_start(g, fake)
        _stand(g, fake, 370, 0)
        fake.blockers = {_A: [kid]}
        published(g, lambda s: s.objects and s.objects[0]["moving"])
        g.ROUTE_NPC_REPLANS = 0
        g.ROUTE_WALKER_BUDGET_SECONDS = 4.0
        stood = _step_in_front(g, _door_step_up(kid, kid_walks), past=360)
        if leg == "replay":
            stop = tour.replay(g, log, [[_A, 0, _B]], beat=2600, max_crossings=20, max_passes=2, budget_s=120)
        else:
            stop = tour.run(g, log, beat=2600, max_crossings=20, max_passes=2, budget_s=120)
    assert stood, "premise: the child stepped up on the door step"
    first = [x for x in log if x["k"] == "cross"][0]
    assert first["entered"] == _B and first["verdict"] == ("replayed" if leg == "replay" else "crossed"), first
    assert first["box_cleared"] >= 1 and 6 in [uid for uid, _kind, _moving in first["boxers"]], first
    assert (first["held_by"], first["pinned"]) == (None, []), first
    assert stop.startswith(f"SC left 2600: now 2610 in field {_B}"), stop
    assert [f["to"] for f in fake.fired] == [_B], fake.fired


def test_a_walk_reads_off_any_log_the_tour_wrote():
    """The partner's walk, off its log: every crossing that ENTERED a field, in order, in donor terms. A crossing the
    tour or a replay drives names the place it entered (``entered``); a log written before that (session 2's: its
    ``entered`` named the trigger radii, now ``triggers``) is read the old way -- landed (late or not), or the room
    route_cross's error names (the 353 bounce) -- a fork id as its donor, and the attempts that never left the room
    are not part of the walk."""
    sys.path.insert(0, str(REPO / "studies" / "story-trace"))
    import dali_tour as D
    reached = "crossing from {} reached field {}, but it never became playable within 20s -- the gateway WORKS and"
    old = [
        {"k": "segment", "ok": True},
        {"k": "cross", "leg": "tour", "from": 352, "exit": 0, "to": 351, "landed": 351, "entered": [[12, "range", 90]]},
        {"k": "cross", "leg": "tour", "from": 350, "exit": 0, "to": 351, "landed": None, "inside": True, "entered": []},
        {"k": "scene", "why": "after crossing 3"},
        {"k": "cross", "leg": "tour", "from": 350, "exit": 2, "to": 353, "landed": None, "error": reached.format(350, 353)},
        {"k": "donor", "field": 30833, "members": 350, "engine": 350},
        {"k": "cross", "leg": "tour", "from": 30833, "exit": 2, "to": 30835, "place": 350, "to_place": 353,
         "landed": None, "error": reached.format(30833, 30835)},
        {"k": "cross", "leg": "back", "from": 30833, "exit": 6, "to": 450, "place": 350, "to_place": 450, "landed": 450},
        {"k": "cross", "leg": "tour", "from": 356, "exit": 2, "to": 358, "verdict": "unreachable: no standable goal"},
        {"k": "cross", "leg": "tour", "from": 350, "exit": 1, "to": 354, "landed": 354, "landed_late": True,
         "error": reached.format(350, 354)},
    ]
    assert D.entered_walk(old, {30833: 350, 30835: 353}) == [
        [352, 0, 351], [350, 2, 353], [350, 2, 353], [350, 6, 450], [350, 1, 354]]
    new = [{"k": "cross", "leg": "replay", "from": 350, "exit": 2, "to": 353, "place": 350, "entered": 353,
            "landed": None, "error": reached.format(350, 353)},
           {"k": "cross", "leg": "tour", "from": 350, "exit": 4, "to": 355, "landed": None, "entered": None,
            "triggers": [[12, "range", 90]]},
           {"k": "cross", "leg": "tour", "from": 355, "exit": 0, "to": 350, "landed": 350, "entered": 350}]
    assert D.entered_walk(new) == [[350, 2, 353], [355, 0, 350]]
    assert D.entered_walk(new, legs=("replay",)) == [[350, 2, 353]]
    # the crossing's own record: a bounce over inside the wait "landed" in the room it left -- it entered 353
    assert D.entered_field({"from": 350, "landed": 350, "changed_to": 353}) == 353
    assert D.entered_field({"from": 350, "landed": 354, "changed_to": 354}) == 354
    assert D.entered_field({"from": 350, "landed": 350}) == 350            # no changed_to: read as before


# ---- F5, the hub lane (studies/story-trace/rung5_hub.py): an F5 run enters its start field through the kit's HUB --
# New Game, `warp 31100 0 2540`, talk to Stiltzkin, pick "Dali (SC 2600)": the pick stamps the seed and runs
# Field(31111), member(359). dali_tour.segment takes that leg as ``enter`` IN PLACE OF rung 3's raw warp and its wait;
# from there the segment is the game's, the same loop on both sides. The hub on the fake: the moogle on the hub's spawn
# (404, 127), a box floor -- the install has no walkmesh for 31100 (route_to would raise) and no script to read a key
# prior from (calibration is blind) -- and Stiltzkin a SOLID body at (480, 127) with a talk ring.

_HUB, _ENTRY, _WAKE = 31100, 31111, 31104                     # the hub, member(359), member(352)
_DALI_ROW, _STAY_ROW = "Dali (SC 2600)", "Stay here, kupo..."
_F5_PLACES = {_ENTRY: 359, _WAKE: 352}
_NIGHT = ("Zidane\n“Where is everybody?”", "Vivi\n“...”")    # the entry's arrival scene, two pages


class _HubFake(FakeGame):
    """The F5 hub and its pick on the fake. ``warp 31100`` stands the moogle on the hub's spawn (and any warp's third
    operand sets the SC, as the debug warp does); ``narrator`` is Stiltzkin, a solid body with a talk ring, published
    under ``objects``. A Confirm with control, his centre inside the ring and facing him (+-90 degrees) opens the
    journey menu -- a choice window as :meth:`FakeGame.scene` plays one (``journey`` is its beat: ``typing`` makes the
    prompt eat the first Confirm, ``default`` is the row the cursor starts on, ``options`` the rows); ``silent``: the
    press opens nothing; ``deaf``: a window that takes no Confirm at all; ``hang``: the game stops taking requests at
    the first press into the ready menu (the press never lands, nothing after it is acked). The row ANSWERED is read by
    its TEXT: the Dali row stamps SC 2600 and runs Field(``lands``) (None: nothing), the stay row gives control back
    in the hub (``stay_lands``: a stay row that warps -- on the ``stay_after``-th ``wait`` request after the answer,
    a few frames late, whatever the render rate; 0 at once; ``stay_control``
    False: one that leaves control withheld; ``stay_throws``: one that logs a THROWS exception through the event
    engine). A field in ``arrivals`` ({field: (pages, wake field)}) plays its arrival scene on entry -- pages Confirm
    turns, control withheld -- then wakes: control back in the wake field at the beat, ``woken`` set (359's night to
    352's wake -- the same after the raw warp and after the pick). ``spawn`` is where a warp into the hub stands him,
    facing south (the hub's TurnInstant(0))."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.facing_mode = "published"                     # s90: the leg's turn in place is a live verb
        self.narrator = {"x": 480.0, "z": 127.0, "r": 32.0, "talk_r": 96.0, "solid": True}
        self.blockers = {_HUB: [self.narrator]}
        self.spawn = (404.0, 127.0)
        self.journey = {"header": "Kupo! Which piece of the story, kupo?", "options": [_DALI_ROW, _STAY_ROW],
                        "default": 0}
        self.lands, self.stay_lands, self.stay_after = _ENTRY, None, 0
        self.stay_control, self.stay_throws = True, False
        self.arrivals = {_ENTRY: (list(_NIGHT), _WAKE)}
        self.beat = 2600
        self.silent = self.deaf = self.hang = False
        self.talks = 0
        self.woken = False
        self._then = None
        self.objects_back_at: int | None = None            # a null objects window: listed again from this frame
        self._stay_pending: tuple | None = None            # (wait requests left, dest) of a late stay-row warp

    def _step_world(self) -> None:
        if self.objects_back_at is not None and self.frame >= self.objects_back_at:
            self.objects_mode, self.objects_back_at = "listed", None
        super()._step_world()

    def _execute(self, step: list[str]) -> None:
        if self.hang and step[0].lower() == "press" and self._beat_phase == "ready":
            self.block_until = 1 << 40                     # stalled at the pick's Confirm: never lands, never acks
            return
        if step[0].lower() == "wait" and self._stay_pending is not None:
            n, dest = self._stay_pending                   # the late stay-row warp: on its n-th wait request
            self._stay_pending = (n - 1, dest) if n > 1 else None
            if n <= 1:
                self._land(dest)
        super()._execute(step)
        if step[0].lower() == "warp":
            if len(step) > 3 and int(step[3]) >= 0:
                self.scenario = int(step[3])
            if self.field_id == _HUB:
                self.player = [float(self.spawn[0]), 0.0, float(self.spawn[1])]
                self._face_deg = 0.0                       # the hub's TurnInstant(0): south
            self._arrive()

    def _arrive(self) -> None:
        got = self.arrivals.get(self.field_id)
        if got is not None:
            pages, wake = got
            self._then = lambda: self._wake(wake)
            self.scene(*pages)

    def _land(self, fid: int) -> None:
        self.field_id, self.player, self.control = fid, [0.0, 0.0, 0.0], True
        self._visit += 1
        self._in_trigger.clear()
        self._arrive()

    def _wake(self, fid: int) -> None:
        self._land(fid)
        self.scenario = self.beat
        self.woken = True

    def _talkable(self) -> bool:
        n = self.narrator
        dx, dz = n["x"] - self.player[0], n["z"] - self.player[2]
        return (self.field_id == _HUB and self.control and self.ui_state == "FieldHUD" and not self._beats
                and math.hypot(dx, dz) < n["talk_r"] and dx * self._facing[0] + dz * self._facing[1] > 0)

    def _menu_step(self, button: str) -> None:
        if button in ("confirm", "ok") and self._talkable():
            self.talks += 1
            if not self.silent:
                self._then = self._picked
                self.scene(dict(self.journey))
            return
        super()._menu_step(button)

    def _scene_press(self, button: str) -> None:
        if self.deaf and button in ("confirm", "ok") and not isinstance(self._beats[0], str):
            return
        super()._scene_press(button)

    def _next_beat(self, stale: int = 0) -> None:
        super()._next_beat(stale)
        if not self._beats and self._then is not None:
            then, self._then = self._then, None
            then()

    def _picked(self) -> None:
        row = self.journey["options"][self.answered[-1]]
        if row == _DALI_ROW:
            self.scenario = 2600                            # the stamp (the words and the party are untraced here)
        dest = self.lands if row == _DALI_ROW else self.stay_lands
        if row != _DALI_ROW:
            if self.stay_throws:
                self.throw("NullReferenceException", ("EventEngine.DoEventCode ()", "EventEngine.ProcessEvents ()",
                                                      "HonoBehaviorSystem.Update ()"))
            if not self.stay_control:
                self.control = False
            if dest is not None and self.stay_after:
                self._stay_pending = (self.stay_after, dest)   # a warp that lands a few requests later
                return
        if dest is not None:
            self._land(dest)


class _MovePCHubFake(_HubFake):
    """The hub at its BUILT sizes, Stiltzkin's body met the way MovePC meets it. The built hub gives him
    SetObjectLogicalSize(14, 14, 22) and the moogle (20, 24, 40): his collision r = 4*(14 + 24) = 152 (WalkMesh.
    Collision, HarnessAgent's ``r``), his talk ring 4*(22 + 40) + his speed + 60 (320 here), and a push-out lands at
    ``safe`` = the moogle's radius 4*20 + 4*14 = 136 -- INSIDE r. The spawn (404, 127) stands 76u from him, inside
    his body. MovePC (FieldMapActorController.cs:744-793 at stock 6b8bb2d5): the yaw turns first (the fake's
    ``_turn``), then a step that ends within r of him, his bearing within +-90 degrees of that yaw, is pushed out to
    ``safe`` along the line from his centre -- and, colliding again there, undone whole, move and all; any other
    step stands. So from the spawn every press whose turn swings the yaw through east (at him) does not move him at
    all -- up, down and right from TurnInstant(0) -- and only a press AWAY from him does."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.narrator.update(r=152.0, talk_r=320.0, safe=136.0)
        self.met: list[str] = []                           # each step that ended within r: "undone" or "pushed"

    def _move_to(self, x: float, z: float, calls: float = 1.0) -> bool:
        n = self.narrator
        if self.field_id != _HUB:
            return super()._move_to(x, z, calls)
        from ff9mapkit.content import doorface
        ox, oz = self.player[0], self.player[2]
        d = math.hypot(x - n["x"], z - n["z"])
        if d < n["r"]:
            off = (self._face_deg - doorface.yaw_of(n["x"] - ox, n["z"] - oz) + 180.0) % 360.0 - 180.0
            if -90.0 <= off <= 90.0:                       # CollisionAngle within +-90: the push-out runs
                px, pz = n["x"] + (x - n["x"]) / d * n["safe"], n["z"] + (z - n["z"]) / d * n["safe"]
                if math.hypot(px - n["x"], pz - n["z"]) < n["r"]:
                    self.met.append("undone")
                    x, z = ox, oz                          # collides again at safeDist: both moves undone
                else:
                    self.met.append("pushed")
                    x, z = px, pz
        bodies, self.blockers = self.blockers, {}          # the floor and the walls as the fake keeps them
        try:
            return super()._move_to(x, z, calls)
        finally:
            self.blockers = bodies


def _rung5():
    """studies/story-trace/rung5_hub.py and dali_tour, loaded as the Tour.replay tests load dali_tour."""
    sys.path.insert(0, str(REPO / "studies" / "story-trace"))
    import dali_tour
    import rung5_hub
    return rung5_hub, dali_tour


def _hub_world(game, cls=None):
    """``(fake, rung5_hub, dali_tour, pred)``: the hub on the fake (``cls``, default :class:`_HubFake`, a 960 fps
    loop), the modules, and the FROZEN predictions v3 the session reads; the hub and its entry member registered in the
    fake install, as the deploy registers them (warp refuses an id no DictionaryPatch names)."""
    with (game / "FF9CustomMap" / "DictionaryPatch.txt").open("a", encoding="utf-8") as fh:
        fh.write(f"FieldScene {_HUB} 21 T5_HUB T5_HUB {_HUB}\nFieldScene {_ENTRY} 11 T5_DL_ENT T5_DL_ENT 359\n")
    H, D = _rung5()
    pred, _sha = H.load_predictions()
    return (cls or _HubFake)(game, fps=960), H, D, pred


def _spy(g, calls: list) -> None:
    """Record every ``send`` and ``wait_for`` the session makes, in order: ``(verb, first arg, timeout, what)``."""
    for name in ("send", "wait_for"):
        real = getattr(g, name)

        def spy(*a, _real=real, _name=name, **kw):
            calls.append((_name, a[0] if a else None, kw.get("timeout"), kw.get("what")))
            return _real(*a, **kw)
        setattr(g, name, spy)


def _confirms_after_ready(fake) -> int:
    """The Confirm presses the fake executed after its first choice window became READY."""
    return sum(1 for s in fake.executed[fake.readied[0]:] if s[:2] == ["press", "confirm"])


def _after_entry(log: list) -> list:
    """A segment's own records -- everything after the entry -- with each field as its PLACE (a member as its donor)."""
    out = []
    for x in log:
        if x["k"] == "hub":
            continue
        y = dict(x, field=_F5_PLACES.get(x["field"], x["field"]))
        out.append(y)
    return out


def test_segment_with_no_enter_is_rung_3s_raw_warp_and_its_wait(game):
    """rung 3's path, unchanged: the FIRST things segment() does are ``warp <start> 0 <sc>`` sent RAW (warp() waits for
    the control this segment never gives) and the 60 s wait for the start field -- then the game's own segment, its
    scene sat through, control back at the beat in ``until`` after the wake. Break: drop the raw warp, or its wait, or
    send it through warp() (which waits for control the night never gives)."""
    fake, _H, D, _pred = _hub_world(game)
    fake.arrivals = {359: (list(_NIGHT), 352)}
    calls, log = [], []
    with session(game, fake) as g:
        boot(g)
        _spy(g, calls)
        seg = D.segment(g, log, start=359, sc=2540, beat=2600, until=352, timeout=30, woke=lambda: fake.woken)
    assert calls[0] == ("send", "warp 359 0 2540", None, None), calls[:2]
    assert calls[1][0] == "wait_for" and calls[1][2:] == (60, "field 359 to load"), calls[:2]
    assert [c for c in calls if c[0] == "send" and str(c[1]).startswith("warp")] == [calls[0]]
    assert seg == {"k": "segment", "field": 352, "place": 352, "sc": 2600, "control": True, "woke": True, "ok": True,
                   "at_beat": True}, seg
    assert _after_entry(log) == [{"k": "scene", "why": "segment", "field": 352, "sc": 2600, "pages": 2, "choices": []},
                                 seg], log
    assert fake.talks == 0 and not fake.answered


def test_segment_with_enter_replaces_the_raw_warp_and_plays_the_rest_the_same(game):
    """F5's path: ``enter`` (the hub leg) is segment()'s first act and REPLACES the raw warp and its wait -- nothing
    is sent or waited on before it, no ``warp 31111`` is ever sent, and the only warp is the leg's own into the hub
    -- and the rest is rung 3's loop: the same scene record and the same segment record, place for place, as the raw
    warp's (test_segment_with_no_enter_is_rung_3s_raw_warp_and_its_wait). Break: ignore ``enter`` (the raw warp
    lands in 31111 without the hub), or call it and warp as well."""
    fake, H, D, pred = _hub_world(game)
    calls, log, entered = [], [], []

    def enter():
        entered.append(len(calls))
        H.hub_leg(g, log, pred)

    with session(game, fake) as g:
        boot(g)
        _spy(g, calls)
        seg = D.segment(g, log, start=_ENTRY, sc=2540, beat=2600, place=lambda f: _F5_PLACES.get(f, f), until=352,
                        timeout=30, woke=lambda: fake.woken, enter=enter)
    assert entered == [0], "enter() was not segment()'s first act"
    warps = [c[1] for c in calls if c[0] == "send" and str(c[1]).startswith("warp")]
    assert warps == [f"warp {_HUB} 0 2540"], warps
    assert not any(c[3] == f"field {_ENTRY} to load" for c in calls), "the raw warp's wait ran as well"
    assert [x["k"] for x in log] == ["hub", "scene", "segment"], log
    assert seg == {"k": "segment", "field": _WAKE, "place": 352, "sc": 2600, "control": True, "woke": True, "ok": True,
                   "at_beat": True}, seg
    assert _after_entry(log) == [{"k": "scene", "why": "segment", "field": 352, "sc": 2600, "pages": 2, "choices": []},
                                 dict(seg, field=352)], log
    assert fake.answered == [0] and fake.talks >= 1


def test_hub_leg_walks_up_to_a_solid_stiltzkin_and_picks_the_dali_row(game):
    """The leg on a custom id: no key prior from the install (31100 has no install script) and no stock walkmesh
    (route_to would raise there), so calibrate_axes on the hub's own frozen twist (rung5_hub.hub_prior) and a walk_to
    that tolerates his body; Stiltzkin read off the published objects; the approach ``d = max(r + margin, min(talk_r
    - margin, r + reach))`` west of him; turned IN PLACE to face him and Confirm -- the FIRST Confirm opens the talk,
    though walk_to's last burst here can be an overshoot correction WEST, away from him ("hold right 13", then "hold
    left 1"); the frozen menu, its cursor on the default; the Dali row picked with ONE Confirm; the wait for 31111.
    The record -- the design's hub record -- is logged and returned. Break: turn only after a silent try (the first
    Confirm, facing away, opens nothing: tries 2)."""
    fake, H, _D, pred = _hub_world(game)
    a = pred["hub"]["approach"]
    n = fake.narrator
    d = max(n["r"] + a["margin"], min(n["talk_r"] - a["margin"], n["r"] + a["reach"]))
    log = []
    with session(game, fake) as g:
        boot(g)
        assert g.key_prior(_HUB) is None, "premise: a custom id has no key prior of its own"
        with pytest.raises(HarnessError):
            g._stock_walkmesh(_HUB)                        # premise: route_to has no floor to route the hub on
        t0 = time.time()
        rec = H.hub_leg(g, log, pred)
        took = time.time() - t0
        st = g.state
    assert st.field_id == _ENTRY and st.scenario == 2600, (st.field_id, st.scenario)
    assert log == [rec] and rec["k"] == "hub", log
    assert rec["options"] == pred["hub"]["options"] and rec["cursor"] == 0 and rec["picked"] == _DALI_ROW, rec
    assert (rec["presses"], rec["r"], rec["talk_r"]) == (1, n["r"], n["talk_r"]), rec
    assert rec["approach"] == [round(n["x"] - d), round(n["z"]), round(d, 1)], rec
    assert (rec["tries"], rec["turns"], rec["nudges"]) == (1, 1, 0), rec
    assert rec["t"] <= pred["budget"]["hub_s"] and took < 60, (rec, took)
    assert fake.answered == [0] and fake.talks == 1, (fake.answered, fake.talks)
    assert _confirms_after_ready(fake) == 1


def test_hub_leg_a_confirm_the_prompt_eats_gets_one_more_press_and_the_record_says_so(game):
    """A prompt still typing takes the first Confirm as "finish the text" (the _pick rule): the menu is still open and
    taking answers 20 frames later, so the leg presses ONE more -- never a second one blind -- and the record logs
    presses 2. The Dali row is answered once. Break: press once, or press twice without looking."""
    fake, H, _D, pred = _hub_world(game)
    fake.journey["typing"] = 10 ** 6
    log = []
    with session(game, fake) as g:
        boot(g)
        rec = H.hub_leg(g, log, pred)
    assert rec["presses"] == 2 and log[-1]["presses"] == 2, log
    assert fake.answered == [0] and _confirms_after_ready(fake) == 2, (fake.answered, fake.executed[-12:])


def test_hub_leg_picks_the_row_by_its_label_not_by_its_place(game):
    """hub_pick names the row: option_index(label) -> select -> Confirm. With the rows the other way round the cursor
    starts on the stay row and the Dali row is answered at index 1 -- a Confirm on the default would have stayed."""
    fake, H, _D, pred = _hub_world(game)
    fake.journey.update(options=[_STAY_ROW, _DALI_ROW], default=0)
    with session(game, fake) as g:
        boot(g)
        g.warp(_HUB)
        fake._then = fake._picked
        fake.scene(dict(fake.journey))
        published(g, lambda s: g._choice_ready(s))
        presses = H.hub_pick(g, pred, _DALI_ROW, time.time() + 30)
        st = g.wait_for(lambda s: s.field_id == _ENTRY, timeout=10, what="the pick's Field()")
    assert presses == 1 and fake.answered == [1] and st.scenario == 2600, (presses, fake.answered)


def test_hub_leg_from_a_spawn_inside_his_body_calibrates_on_the_hubs_twist(game):
    """The hub at its BUILT sizes (:class:`_MovePCHubFake`: r 152, the spawn 76u from him, MovePC undoing whole any
    step that faces him). A BLIND calibrate_axes there refuses the v axis -- up and down both swing his yaw through
    east, at him, and move him nothing -- which would stop P-HUBLEG, and the session, before run 1. The leg calibrates
    on the hub's frozen twist instead (rung5_hub.hub_prior): the left probe, away from him, agrees with the prior and
    the other axis is derived; then the approach 176u west of him (304, 127), the talk on the first Confirm, the
    pick, 31111. A SECOND leg in the same launch reuses the cached basis: from the spawn inside his body the walk
    heads west, away from him, and no step is undone. Break: calibrate blind."""
    fake, H, D, pred = _hub_world(game, _MovePCHubFake)
    log, segs, marks = [], [], []

    def run_in():
        """One F5 run's way in: segment() with the hub leg as its enter, the arrival scene sat through to the wake."""
        fake.woken = False
        marks.append(len(fake.met))
        segs.append(D.segment(g, log, start=_ENTRY, sc=2540, beat=2600, place=lambda f: _F5_PLACES.get(f, f),
                              until=352, timeout=30, woke=lambda: fake.woken, enter=lambda: H.hub_leg(g, log, pred)))

    with session(game, fake) as g:
        boot(g)
        g.warp(_HUB, entrance=0, scenario=2540)
        with pytest.raises(HarnessError, match="neither up nor down moved"):
            g.calibrate_axes()                             # premise: blind, from the spawn, it cannot calibrate
        assert fake.met and set(fake.met) == {"undone"}, fake.met
        assert _HUB not in g._axes
        run_in()
        run_in()                                           # the basis cached: no calibration this time
    legs = [x for x in log if x["k"] == "hub"]
    assert len(legs) == 2 and all(s["ok"] for s in segs), (legs, segs)
    for rec in legs:
        assert rec["approach"] == [304, 127, 176.0] and (rec["tries"], rec["nudges"]) == (1, 0), rec
        assert rec["presses"] == 1 and rec["picked"] == _DALI_ROW and "error" not in rec, rec
    assert "undone" in fake.met[marks[0]:marks[1]], "premise: the first leg's calibration met his body"
    assert "undone" not in fake.met[marks[1]:], fake.met[marks[1]:]
    assert fake.answered == [0, 0], fake.answered


def test_hub_leg_a_walk_his_body_stops_dead_still_reaches_the_talk(game):
    """walk_to toward a point his body lies across (a spawn the far side of him, the approach point west of him: the
    press runs straight at him and the body stops it dead) returns short instead of raising -- strict False -- and
    the leg turns him to face Stiltzkin and talks from where the body held him, inside the ring. The record says
    ``walked`` False. Break: walk_to's defaults (strict True: 'could not reach')."""
    fake, H, _D, pred = _hub_world(game)
    fake.spawn = (560.0, 127.0)
    n = fake.narrator
    log = []
    with session(game, fake) as g:
        boot(g)
        rec = H.hub_leg(g, log, pred)
        st = g.state
    assert rec["walked"] is False and abs(rec["at"][0] - (n["x"] + n["r"])) <= 2, rec
    assert (rec["tries"], rec["presses"]) == (1, 1) and st.field_id == _ENTRY, (rec, st.field_id)


def test_hub_leg_reads_stiltzkin_over_a_null_objects_sample(game):
    """The agent nulls the whole objects list on ANY failure of its walk (null = "could not say THIS sample"): a
    null list right after the calibration is waited out (a few seconds of samples), never read once and taken as
    "the engine published no objects". Break: read g.state.objects once."""
    fake, H, _D, pred = _hub_world(game)
    real = None
    log = []

    def calibrate_then_null(**kw):
        basis = real(**kw)
        fake.objects_mode, fake.objects_back_at = "null", fake.frame + 300
        published(g, lambda s: s.objects is None)
        return basis

    with session(game, fake) as g:
        boot(g)
        real = g.calibrate_axes
        g.calibrate_axes = calibrate_then_null
        rec = H.hub_leg(g, log, pred)
    assert rec["narrator"] == [480, 127] and g.state is not None and fake.answered == [0], rec


def test_hub_leg_the_landing_runs_on_its_own_clock_never_the_legs(game, monkeypatch):
    """TWO CLOCKS: hub_s up to the pick's Confirm, the landing's own (budget.entry_s) from it on. (1) The wait for
    31111 takes entry_s whole -- never the leg's time left, which would let a slow leg cut short the one wait that
    tells a fork's stall from a slow drive. (2) The leg's clock is never READ after the Confirm: with its budget
    spent the moment the pick's press is sent (every later read of it raising "hub leg: budget"), the leg still
    lands -- a budget stop after the stamps would file a fork's stall as DRIVE. Break: the landing wait on the time
    left; the polls or the wait reading the leg's clock."""
    fake, H, _D, pred = _hub_world(game)
    calls, log = [], []
    confirmed = {"at": None}
    real_left = H._left

    def left(end):
        if confirmed["at"] is not None:
            raise HarnessError("hub leg: budget -- (the test) spent the moment the pick's Confirm was sent")
        return real_left(end)

    monkeypatch.setattr(H, "_left", left)
    with session(game, fake) as g:
        boot(g)
        _spy(g, calls)
        real_send = g.send

        def send(*steps, **kw):
            if steps[:1] == ("press confirm 4",) and g.state.choice is not None and g._choice_ready(g.state):
                confirmed["at"] = len(calls)                # the pick's own press (interact's has no menu open)
            return real_send(*steps, **kw)
        g.send = send
        rec = H.hub_leg(g, log, pred, budget_s=600.0, entry_s=7.0)
        st = g.state
    assert confirmed["at"] is not None and st.field_id == _ENTRY and rec["presses"] == 1, (confirmed, st.field_id)
    at = next(i for i, c in enumerate(calls) if c[0] == "wait_for" and c[3] == f"the pick to land in {_ENTRY}")
    assert calls[at][2] == 7.0, calls[at]
    polls = calls[confirmed["at"]:at]                      # the press and its polls: every one on the landing clock
    assert polls and all(c[0] == "send" and c[2] is not None and c[2] <= 7.0 for c in polls), polls


def test_hub_leg_a_drive_bug_is_logged_and_re_raised_unchanged(game):
    """An error that is not a HarnessError -- a bug in the drive -- is logged with the leg's record as far as it
    got (its type in ``error``) and re-raised AS IT IS, the same object: the run's own handler names it (STOPPED
    (unexpected): DRIVE). Break: swallow it, wrap it, or log only a HarnessError."""
    fake, H, _D, pred = _hub_world(game)
    boom = KeyError("the drive's own bug")
    log = []
    with session(game, fake) as g:
        boot(g)

        def options(**_kw):
            raise boom
        g.options = options
        with pytest.raises(KeyError) as err:
            H.hub_leg(g, log, pred)
    assert err.value is boom
    assert [x["k"] for x in log] == ["hub"] and log[0]["error"].startswith("KeyError: "), log
    assert log[0]["r"] == fake.narrator["r"] and "t" in log[0], log


@pytest.mark.parametrize("stay", ["stays", "warps", "warps late", "no control", "throws"])
def test_hub_leg_p_hubleg_takes_the_stay_row_and_it_must_stay(game, monkeypatch, stay):
    """P-HUBLEG, untraced, before run 1: New Game, the leg up to the menu, the STAY row picked by its label (the
    cursor moved off the default) -- which must leave him in the hub with control, no menu and no field change for 60
    frames, watched, not glanced at once -- no THROWS exception through the event engine since the leg's hub warp,
    and the title restored. Each FAILs it: a stay row that warps at once, one that warps a few requests later (seen
    by the watch's third look; a single look sees it stay), one that leaves control withheld, a NullReferenceException
    with an EventEngine frame. Break: drop the watch, the control clause or the exception clause."""
    monkeypatch.setattr(sys.modules["harness.session"], "TITLE_SETTLE", 0)
    fake, H, _D, pred = _hub_world(game)
    if stay in ("warps", "warps late"):
        fake.stay_lands, fake.stay_after = _WAKE, (4 if stay == "warps late" else 0)    # late: on the 4th wait
    fake.stay_control = stay != "no control"
    fake.stay_throws = stay == "throws"
    with session(game, fake) as g:
        ok, detail, rec = H.p_hubleg(g, pred)
        st = g.state
    assert fake.answered == [1] and rec["presses"] == 1 and rec["options"] == pred["hub"]["options"], (fake.answered,
                                                                                                         rec)
    assert rec["picked"] == _STAY_ROW and rec["k"] == "hub", rec
    assert st.ui_state == "Title", "the title was not restored"
    want = {"stays": None, "warps": f"the stay row warped to {_WAKE}", "warps late": f"the stay row warped to {_WAKE}",
            "no control": "the stay row left control False", "throws": "thrown: [('NullReferenceException'"}[stay]
    if want is None:
        assert ok and "stay row stayed" in detail, detail
    else:
        assert not ok and want in detail, detail


@pytest.mark.parametrize("fault", ["no talk ring", "silent", "options", "cursor", "deaf", "never lands"])
def test_hub_leg_every_failure_raises_harness_error_and_is_logged(game, fault):
    """Each way the leg cannot reach its start field raises HarnessError -- the run then stops in phase "hub", read by
    its trace -- with the leg's record logged, the error in it: Stiltzkin's talk ring not outside his body; no
    dialogue after the frozen tries (each after a turn to face him, a walked tick between them); a menu whose rows are
    not the frozen ones; its cursor not on the frozen default; a menu that takes neither Confirm (two presses, no
    third); the pick taken and 31111 never reached (the landing's own wait, entry_s, timing out LIVE -- the text
    FORK-STOP "hub" is read by)."""
    fake, H, _D, pred = _hub_world(game)
    budget = entry = None
    if fault == "silent":
        fake.silent = True
        want = "no dialogue after 3 tries"
    elif fault == "no talk ring":
        fake.narrator["talk_r"] = fake.narrator["r"] + pred["hub"]["approach"]["margin"]
        want = "no talk ring outside the body"
    elif fault == "options":
        fake.journey["options"] = [_DALI_ROW, "Treno (SC 3000)", _STAY_ROW]
        want = "the menu offers"
    elif fault == "cursor":
        fake.journey["default"] = 1
        want = "cursor rests on 1"
    elif fault == "deaf":
        fake.deaf = True
        want = "never took its Confirm"
    else:
        fake.lands = None
        budget, entry = 12.0, 3.0
        want = f"timed out after 3s waiting for the pick to land in {_ENTRY} over"
    log = []
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError, match=re.escape(want)):
            H.hub_leg(g, log, pred, budget_s=budget, entry_s=entry)
        st = g.state
    if fault == "never lands":
        assert re.search(pred["coverage"]["fork_stop"]["hub"]["stop"], log[0]["error"]), log[0]["error"]
    assert st.field_id == _HUB, st.field_id
    assert [x["k"] for x in log] == ["hub"] and want in log[0]["error"], log
    if fault == "silent":
        assert (log[0]["tries"], log[0]["turns"], log[0]["nudges"], fake.talks) == (3, 3, 2, 3), log
    if fault == "deaf":
        assert _confirms_after_ready(fake) == 2 and not fake.answered, fake.executed[-12:]


@pytest.mark.parametrize("stall", ["silent", "hang"])
def test_hub_leg_a_stalled_step_stops_the_leg_within_its_clocks(game, stall):
    """Two clocks, both enforced. Up to the pick's Confirm ONE deadline (hub_s): every call gets min(its default, the
    time left) and a check between calls raises "hub leg: budget" -- Stiltzkin silent: each Confirm's wait for a
    dialogue is cut to the time left, and the next call is refused, within the budget. From the Confirm on the
    landing's own clock (entry_s) -- the game stalled at the pick's Confirm (it takes no more requests): the press's
    wait for its ack is entry_s, not the budget's remainder, and the leg raises within it. Neither a default timeout
    later."""
    fake, H, _D, pred = _hub_world(game)
    fake.silent = stall == "silent"
    fake.hang = stall == "hang"
    budget, entry = 12.0, 3.0
    log = []
    with session(game, fake) as g:
        boot(g)
        t0 = time.time()
        with pytest.raises(HarnessError) as err:
            H.hub_leg(g, log, pred, budget_s=budget, entry_s=entry)
        took = time.time() - t0
        fake.block_until = fake.frame                      # let the teardown's quit land
    assert took < budget + 2.0, (took, str(err.value))
    if stall == "silent":
        assert "hub leg: budget" in str(err.value) and fake.talks >= 1 and not fake.answered, (str(err.value),
                                                                                                fake.talks)
    else:
        assert "not acknowledged within 3s" in str(err.value) and not fake.answered, str(err.value)
    assert log and log[-1]["k"] == "hub" and log[-1]["error"], log


# ---- F5b, the post-wake entry (studies/story-trace/rung5b_hub.py): a hub pick lands member(351) = 31101 PAST the wake,
# at entrance 6 -- stock's first field entry after it. Two hubs share F5's rig: T5B_HUB (31113, the fixed row: removes
# garnet/steiner/vivi, adds zidane) and T5B_CTL (31114, today's pre-phase row: adds all four). The trace cannot see
# the party; the sandbox FIELD-ENTRY AUTOSAVE can (40000_Common.slot), and :class:`_PartyHubFake` writes one on every
# field entry, as the engine does before the new field's scripts run. The predictions are rung5b_hub's SKELETON
# (draft_predictions: F5's hub rig carried, the two hubs, the party table): the machinery is on test, not the numbers.

_B_HUB, _C_HUB, _PAST = 31113, 31114, 31101                   # T5B_HUB, T5B_CTL, member(351)
_B_PLACES = {_PAST: 351, _WAKE: 352, _ENTRY: 359}
_NG_PARTY = [0, 255, 255, 255]                                 # New Game: Zidane alone (ff9play.cs:74-78)


def _sj_str(s: str) -> bytes:
    """.NET BinaryWriter.Write(string): a 7-bit length prefix, then UTF-8 (tests/test_save_extra.py's port)."""
    raw = s.encode("utf-8")
    n, out = len(raw), bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            break
    return bytes(out) + raw


def _sj(node) -> bytes:
    """SimpleJSON's BINARY serialization (JSONClass/JSONArray/JSONData.Serialize) -- the Memoria extra file's format."""
    import struct
    if isinstance(node, dict):
        return struct.pack("<ii", 2, len(node)) + b"".join(_sj_str(k) + _sj(v) for k, v in node.items())
    if isinstance(node, list):
        return struct.pack("<ii", 1, len(node)) + b"".join(_sj(v) for v in node)
    if isinstance(node, bool):
        return struct.pack("<i?", 6, node)
    if isinstance(node, int):
        return struct.pack("<ii", 4, node)
    if isinstance(node, float):
        return struct.pack("<id", 5, node)
    return struct.pack("<i", 3) + _sj_str(str(node))


class _PartyHubFake(_HubFake):
    """F5b's two hubs on the fake, and the sandbox FIELD-ENTRY AUTOSAVE the party is read through. Both hubs are F5's
    rig (the spawn, Stiltzkin, the menu); the row each answers is its own (``rows`` = {hub: {remove, add, entrance,
    lands}}): the pick runs its removes -- a no-op for a non-member (EventEngine.DoEventCode.cs:2754-2767); ``inert``
    makes every one a no-op -- then its adds into the first empty slot (a member already in skipped,
    EventEngine.cs:875-915), stamps SC 2600 and Int16[2] := entrance, and lands. EVERY field entry -- a warp (its
    entrance operand is Int16[2]), a landing -- writes the autosave: the party in SLOT order, gEventGlobal with SC and
    Int16[2], the play time, its st_mtime_ns strictly after the last one's (the engine's saves are seconds apart, the
    fake's frames are not). ``saves`` False: an engine that did not autosave. ``wake_on_landing``: the landing plays
    the wake (its SC store traced: ``woken``). A row may also name the ``sc`` its pick stamps (default the beat), a
    ``then`` = (field, frames) it warps on to after landing, and ``saves`` False (that pick's landing writes no
    autosave). ``ng_party`` is the party New Game leaves. ``save_delay`` / ``control_delay``: a pick's landing
    writes its autosave, and gives control back, that many frames AFTER the field flips -- the engine's order
    (fldMapNo flips in the old field's shutdown, the new field's StartEvents autosaves, control comes last)."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.rows = {_B_HUB: {"remove": [2, 3, 1], "add": [0], "entrance": 6, "lands": _PAST},
                     _C_HUB: {"remove": [], "add": [2, 3, 1, 0], "entrance": 6, "lands": _PAST}}
        for hub in self.rows:
            self.blockers[hub] = [self.narrator]
        self.party = list(_NG_PARTY)
        self.ng_party = list(_NG_PARTY)
        self.entrance = 0
        self.inert = False
        self.saves = True
        self.wake_on_landing = False
        self.save_delay = self.control_delay = 0
        self.play_time = 0.0
        self._saved_ns = 0
        self._pending: dict = {}                           # frame -> what a pick's landing does then

    def _autosave(self) -> None:
        import base64
        import struct
        if not self.saves:
            return
        geg = bytearray(2048)
        struct.pack_into("<Hh", geg, 0, int(self.scenario or 0) & 0xFFFF, self.entrance)
        self.play_time += 1.0
        tree = {"95000_Setting": {"00001_time": self.play_time},
                "20000_Event": {"gStepCount": 0, "gEventGlobal": base64.b64encode(bytes(geg)).decode("ascii"),
                                "gAbilityUsage": [], "gScriptVector": [], "gScriptDictionary": []},
                "40000_Common": {"players": [{"name": "Zidane", "info": {"party": 1}, "cur": {"hp": 105},
                                              "status": 0}], "slot": list(self.party)}}
        path = self.dir / "save" / "SavedData_ww_Memoria_Autosave.dat"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_sj(tree))
        self._saved_ns = max(time.time_ns(), self._saved_ns + 1_000_000)
        os.utime(path, ns=(self._saved_ns, self._saved_ns))

    def _step_world(self) -> None:
        for at in sorted(k for k in self._pending if k <= self.frame):
            for what in self._pending.pop(at):
                if what == "save":
                    self._autosave()
                elif what == "control":
                    self.control = True
                else:                                      # a warp on after the landing: control stays withheld
                    _HubFake._land(self, what)
                    self.control = False
                    self._autosave()
        super()._step_world()

    def _execute(self, step: list[str]) -> None:
        op = step[0].lower()
        if op == "newgame":
            self.party, self.entrance, self._pending = list(self.ng_party), 0, {}
        super()._execute(step)
        if op == "warp":
            if len(step) > 2 and int(step[2]) >= 0:
                self.entrance = int(step[2])
            if self.field_id in self.rows:
                self.player = [float(self.spawn[0]), 0.0, float(self.spawn[1])]
                self._face_deg = 0.0                       # the hub's TurnInstant(0): south
            self._autosave()

    def _land(self, fid: int) -> None:
        super()._land(fid)
        self._autosave()

    def _talkable(self) -> bool:
        n = self.narrator
        dx, dz = n["x"] - self.player[0], n["z"] - self.player[2]
        return (self.field_id in (_HUB, *self.rows) and self.control and self.ui_state == "FieldHUD"
                and not self._beats and math.hypot(dx, dz) < n["talk_r"]
                and dx * self._facing[0] + dz * self._facing[1] > 0)

    def _picked(self) -> None:
        spec = self.rows.get(self.field_id)
        if spec is None or self.journey["options"][self.answered[-1]] != _DALI_ROW:
            return super()._picked()
        for c in spec["remove"]:
            if not self.inert and c in self.party:
                self.party[self.party.index(c)] = 255
        for c in spec["add"]:
            if c not in self.party and 255 in self.party:
                self.party[self.party.index(255)] = c
        self.scenario, self.entrance = spec.get("sc", self.beat), spec["entrance"]
        saves = spec.get("saves", True)
        _HubFake._land(self, spec["lands"])                # the field flips; its autosave follows below
        if self.save_delay or self.control_delay or spec.get("then"):
            self.control = False                           # withheld until its frame
            later = {self.frame + max(self.control_delay, 1): ["control"]}
            if saves:
                later.setdefault(self.frame + self.save_delay, []).append("save")
            if spec.get("then"):
                later.setdefault(self.frame + spec["then"][1], []).append(spec["then"][0])
            for at, what in later.items():
                self._pending.setdefault(at, []).extend(what)
        elif saves:
            self._autosave()
        if self.wake_on_landing:
            self.woken = True


def _rung5b():
    """studies/story-trace/rung5b_hub.py, rung5_hub.py and dali_tour, loaded as the F5 tests load theirs."""
    sys.path.insert(0, str(REPO / "studies" / "story-trace"))
    import dali_tour
    import rung5_hub
    import rung5b_hub
    return rung5b_hub, rung5_hub, dali_tour


def _b_world(game, cls=None):
    """``(fake, rung5b_hub, rung5_hub, pred)``: F5b's two hubs on the fake (``cls``, default :class:`_PartyHubFake`,
    a 960 fps loop), the modules, and the predictions SKELETON -- every id a leg warps to registered."""
    with (game / "FF9CustomMap" / "DictionaryPatch.txt").open("a", encoding="utf-8") as fh:
        for fid, name in ((_B_HUB, "T5B_HUB"), (_C_HUB, "T5B_CTL"), (_PAST, "T5_DL_INN"), (_WAKE, "T5_VGDL_DL_INN"),
                          (_ENTRY, "T5_DL_ENT")):
            fh.write(f"FieldScene {fid} 21 {name} {name} {fid}\n")
    M, H, _D = _rung5b()
    return (cls or _PartyHubFake)(game, fps=960), M, H, M.draft_predictions()


def test_f5b_enter_past_lands_member_351_past_the_wake(game):
    """enter_past on the F5B hub's VIEW (its own id and row): the hub leg -- the pick removes garnet/steiner/vivi from
    New Game's Zidane-alone party (no-ops), adds Zidane, stamps SC 2600 and Int16[2] := 6, lands 31101 -- then the
    LANDING: control in place 351 at 2600, no wake. It logs its record after the hub's and returns it; the phases
    run hub -> landing (the stop class reads them). Break: skip the landing wait, or log no record."""
    fake, M, _H, pred = _b_world(game)
    log, phases = [], []
    with session(game, fake) as g:
        boot(g)
        rec = M.enter_past(g, log, M.hub_view(pred, "F5B"), place=lambda f: _B_PLACES.get(f, f),
                           woke=lambda: fake.woken, phase=phases.append)
        st = g.state
    assert phases == ["hub", "landing"], phases
    assert [x["k"] for x in log] == ["hub", "landing"] and log[-1] is rec, log
    assert rec["ok"] and (rec["field"], rec["place"], rec["sc"], rec["control"], rec["woke"]) == (
        _PAST, 351, 2600, True, False), rec
    assert (st.field_id, fake.entrance, fake.party) == (_PAST, 6, _NG_PARTY), (st.field_id, fake.entrance, fake.party)
    assert log[0]["picked"] == _DALI_ROW and fake.answered == [0], (log[0], fake.answered)


@pytest.mark.parametrize("fault", ["wake", "31104"])
def test_f5b_enter_past_raises_on_a_wake_or_a_31104_landing(game, fault):
    """An entry PAST the wake that is not: the landing plays the wake (its SC store in the run's own trace) -- raised
    as "landing: the wake ran ...", the landing record logged not ok, a text the frozen FORK-STOP "landing" pattern
    reads; or the pick lands member(352) = 31104 -- the hub leg's own wait for 31101 times out (entry_s) and raises,
    with no landing to judge. Break: drop the wake check (the first returns), or swallow the leg's error."""
    fake, M, _H, pred = _b_world(game)
    if fault == "wake":
        fake.wake_on_landing = True
    else:
        fake.rows[_B_HUB]["lands"] = _WAKE
    log = []
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError) as err:
            M.enter_past(g, log, M.hub_view(pred, "F5B"), place=lambda f: _B_PLACES.get(f, f),
                         woke=lambda: fake.woken, entry_s=3.0)
        st = g.state
    if fault == "wake":
        assert str(err.value).startswith("landing: the wake ran"), str(err.value)
        assert log[-1]["k"] == "landing" and not log[-1]["ok"] and log[-1]["woke"], log
        assert re.search(pred["coverage"]["fork_stop"]["landing"]["raised"][0], f"STOPPED: HarnessError: {err.value}")
    else:
        assert f"waiting for the pick to land in {_PAST}" in str(err.value) and st.field_id == _WAKE, str(err.value)
        assert [x["k"] for x in log] == ["hub"], log


def test_f5b_prefix_tour_stops_after_one_step(game, monkeypatch):
    """CTL's walk is a PREFIX of its partner's: PrefixTour replays walk[1:2] -- one step, by the replay's own crossing
    and rules -- and stops ("prefix replayed"), where Tour.replay would tour blind on once its walk is done
    (dali_tour.py:725-726). Break: drop PrefixTour's run() override (the blind tour crosses on)."""
    fake, tour, _D = _replay_world(game, monkeypatch)
    M, _H, _D2 = _rung5b()

    class Prefix(M.PrefixTour, type(tour)):
        """PrefixTour over the three-room world's own doors and floor."""

    pt = Prefix(stock=lambda fid: None, tag="test")
    pt._gates = tour._gates
    walk = [[_C, 0, _A], [_A, 0, _B], [_B, 0, _A]]                  # the partner's walk: the prefix is walk[1:2]
    with session(game, fake) as g:
        log = _replay_start(g, fake)
        stop = pt.replay(g, log, walk[1:2], beat=2600, max_crossings=20, max_passes=2, budget_s=120)
        st = g.state
    assert stop.startswith(M.PREFIX_STOP), stop
    assert _replayed(log) == [("replay", 1, _B, _B, "replayed")], log
    assert st.field_id == _B and [f["to"] for f in fake.fired] == [_B], fake.fired


def test_f5b_replay_why5b_passes_a_walk_from_step_2_that_replay_why5_voids():
    """An F5B run REPLAYS its partner's walk FROM STEP 2 -- the pick lands past step 1, the wake room's exit -- so
    rung5_hub.replay_why5, which compares the WHOLE walk, VOIDs every one; replay_why5b compares the frozen slice
    (walk[1:] for F5B, walk[1:2] for CTL) and passes them. An F5B log that replayed the whole walk (352.0 -> 351
    included) is VOID, named. Break: compare the whole walk (the F5B and CTL cases VOID)."""
    M, H, _D = _rung5b()
    import rung3_trace as R
    pred = M.draft_predictions()
    fork_of = {d: f for f, d in M.chain(pred).items()}
    walk = [[352, 0, 351], [351, 0, 350], [350, 0, 351], [351, 1, 352]]

    def log_of(steps, leg, stop):
        return {"stop": stop, "log": [{"k": "cross", "leg": leg, "from": fork_of[a] if leg == "replay" else a,
                                       "place": a, "exit": e, "to": b, "entered": b} for a, e, b in steps]}

    partner = {"i": 1, "side": "S", "why_void": [], "rec": {}, "log": log_of(walk, "tour", "SC left 2600")}
    f5b = {"i": 2, "side": "F5B", "rec": {"partner": 1}, "log": log_of(walk[1:], "replay", "passes exhausted (3)")}
    ctl = {"i": 3, "side": "CTL", "rec": {"partner": 1}, "log": log_of(walk[1:2], "replay", M.PREFIX_STOP)}
    whole = {"i": 4, "side": "F5B", "rec": {"partner": 1}, "log": log_of(walk, "replay", "passes exhausted (3)")}
    by_i = {1: partner, 2: f5b, 3: ctl, 4: whole}
    chains = R.chain_members(pred)
    assert H.replay_why5(f5b, by_i, pred, chains) == [
        "its replay of S#1's walk diverged at step 1: 351.0 -> 350, not 352.0 -> 351"], "premise: v3's rule VOIDs it"
    assert M.replay_why5b(f5b, by_i, pred, chains, 1, None) == []
    assert M.replay_why5b(ctl, by_i, pred, chains, 1, 2) == []
    assert M.replay_why5b(whole, by_i, pred, chains, 1, None) == [
        "its replay of S#1's walk[1:] diverged at step 1: 352.0 -> 351, not 351.0 -> 350"]


def test_f5b_walk_gate_skips_a_ctl_whose_partner_step_2_is_not_351_to_350():
    """THE WALK GATES: an F5B needs its partner's walk[0] == 352.0 -> 351, a CTL walk[0:2] == [352.0 -> 351, 351.0 ->
    350] (its clauses judge exactly that step 2) -- else the run is not driven, its record saying why. And the re-run
    plan partners a CTL only on a QUALIFYING S: with CTL short, S#1 (step 2 is 351.1 -> 352) is passed over for the
    oldest S that qualifies and has no covered CTL twin. Break: drop the gate from untwinned5b (the plan names S#1)."""
    M, _H, _D = _rung5b()
    pred = M.draft_predictions()
    good = [[352, 0, 351], [351, 0, 350], [350, 0, 351]]
    bad2 = [[352, 0, 351], [351, 1, 352], [352, 0, 351]]
    assert M.walk_gate(pred, "CTL", good) is None and M.walk_gate(pred, "F5B", bad2) is None
    assert M.walk_gate(pred, "CTL", bad2) == "skipped: partner step 2 is not 351.0 -> 350 (it is 351.1 -> 352)"
    assert M.walk_gate(pred, "F5B", [[351, 0, 350]]) == (
        "partner's first step is not the wake room's exit 352.0 -> 351 (it is 351.0 -> 350)")

    def s(i, walk):
        return {"i": i, "side": "S", "why_void": [], "rec": {"i": i, "side": "S"}, "stop_class": None,
                "log": {"log": [{"k": "cross", "from": a, "exit": e, "to": b, "entered": b} for a, e, b in walk]}}

    def fk(i, side, partner, why=None, skipped=None):
        rec = {"i": i, "side": side, "partner": partner, **({"skipped": skipped} if skipped else {})}
        return {"i": i, "side": side, "why_void": [w for w in (why, skipped) if w], "rec": rec, "log": None,
                "stop_class": None}

    runs = [s(1, bad2), fk(2, "F5B", 1), fk(3, "CTL", 1, skipped=M.walk_gate(pred, "CTL", bad2)),
            s(4, good), fk(5, "F5B", 4), fk(6, "CTL", 4),
            s(7, good), fk(8, "F5B", 7), fk(9, "CTL", 7, why="stopped: STOPPED: HarnessError: a drive fault")]
    assert M.short_sides5b(runs, pred) == ["CTL"]
    assert M.rerun_plan5b(runs, pred) == ("CTL", 7)


def test_f5b_party_read_rejects_an_unchanged_mtime_and_a_wrong_arrival(game):
    """THE FRESHNESS RULE on the autosave: a read is fresh only when its st_mtime_ns is AFTER the baseline read taken
    before the transition it judges, its sha stable over two reads 10 frames apart, and SC / Int16[2] / the field
    name the arrival. No transition since the baseline (the same file), an engine that did not autosave (the
    previous file), or an arrival other than the one wanted: each stale, named. Break: drop the mtime clause or the
    arrival clause."""
    fake, M, _H, _pred = _b_world(game)
    arrival = {"sc": 2540, "entrance": 0}
    with session(game, fake) as g:
        boot(g)
        g.warp(_B_HUB, entrance=0, scenario=2540)
        r0 = M.party_read(g)
        same = M.party_read(g, r0, dict(arrival, field=_B_HUB))
        g.warp(_C_HUB, entrance=0, scenario=2540)
        fresh = M.party_read(g, r0, dict(arrival, field=_C_HUB))
        wrong = M.party_read(g, r0, {"sc": 2600, "entrance": 6, "field": _PAST})
        fake.saves = False
        g.warp(_B_HUB, entrance=0, scenario=2540)
        none = M.party_read(g, fresh, dict(arrival, field=_B_HUB))
    assert r0["fresh"] and r0["stable"] and (r0["slot"], r0["sc"], r0["entrance"], r0["field"]) == (
        _NG_PARTY, 2540, 0, _B_HUB), r0
    assert not same["fresh"] and any(w.startswith("st_mtime_ns") for w in same["why"]), same
    assert fresh["fresh"] and fresh["mtime_ns"] > r0["mtime_ns"], fresh
    assert not wrong["fresh"] and sorted(w.split()[0] for w in wrong["why"]) == ["entrance", "field", "sc"], wrong
    assert not none["fresh"] and any(w.startswith("st_mtime_ns") for w in none["why"]), none


@pytest.mark.parametrize("case", ["removes act", "inert removes", "uncalibrated"])
def test_f5b_p_partyremove_fails_on_inert_removes_and_voids_uncalibrated(game, monkeypatch, case):
    """P-PARTYREMOVE, the known positive R5B-PARTY needs (New Game is already Zidane alone, so the F5B pick's removes
    are no-ops there): New Game; the CTL leg lands 31101 with [0,2,3,1] (r1); the F5B hub opened from there (r2, the
    warp keeps the party); the F5B pick lands 31101 with [0,255,255,255] (r3) -- PASS. Inert removes read [0,2,3,1]
    at r3: FAIL, final (a calibrated FAIL is evidence: no retry). A CTL pick that adds no one leaves r1 uncalibrated:
    VOID, after its ONE retry. The title restored either way. Break: drop the r3 comparison, the calibration clause,
    or the retry."""
    monkeypatch.setattr(sys.modules["harness.session"], "TITLE_SETTLE", 0)
    fake, M, _H, pred = _b_world(game)
    fake.inert = case == "inert removes"
    if case == "uncalibrated":
        fake.rows[_C_HUB]["add"] = [0]
    with session(game, fake) as g:
        ok, detail, rec = M.p_partyremove(g, pred)
        st = g.state
    reads = rec["attempts"][-1]["reads"]
    assert st.ui_state == "Title", "the title was not restored"
    if case == "removes act":
        assert ok is True and len(rec["attempts"]) == 1, (detail, rec)
        assert [reads[k]["slot"] for k in ("r1", "r2", "r3")] == [[0, 2, 3, 1], [0, 2, 3, 1], _NG_PARTY], reads
        assert all(reads[k]["fresh"] for k in ("r1", "r2", "r3")), reads
        assert (reads["r2"]["sc"], reads["r2"]["entrance"], reads["r2"]["field"]) == (2540, 0, _B_HUB), reads["r2"]
    elif case == "inert removes":
        assert ok is False and len(rec["attempts"]) == 1 and "r3 reads [0, 2, 3, 1]" in detail, (detail, rec)
    else:
        assert ok is None and len(rec["attempts"]) == 2 and "r1 reads [0, 255, 255, 255]" in detail, (detail, rec)


@pytest.mark.parametrize("side", ["F5B", "CTL"])
def test_f5b_hub_leg_p_hubleg5b_reads_each_hubs_arrival_autosave(game, monkeypatch, side):
    """P-HUBLEG per hub (p_hubleg5b on the side's VIEW): the leg to the menu, the stay row stays -- and, inside the
    leg, the hub arrival's autosave read fresh against the pre-warp read: New Game's baseline, SC 2540, Int16[2] 0,
    the hub's own id. An engine that did not autosave on the warp leaves the leg a PASS and its autosave clause not
    ok (the caller's one retry; twice failed only VOIDs R5B-PARTY). Break: drop the arrival read's baseline."""
    monkeypatch.setattr(sys.modules["harness.session"], "TITLE_SETTLE", 0)
    fake, M, _H, pred = _b_world(game)
    view = M.hub_view(pred, side)
    hid = pred["hubs"][side]["id"]
    with session(game, fake) as g:
        ok, detail, rec = M.p_hubleg5b(g, view)
        fake.saves = False
        ok2, _d2, rec2 = M.p_hubleg5b(g, view)
    assert ok and rec["hub"] == hid and rec["picked"] == _STAY_ROW and fake.answered == [1, 1], (detail, rec)
    sv = rec["save"]
    assert sv["ok"] and (sv["slot"], sv["sc"], sv["entrance"], sv["field"]) == (_NG_PARTY, 2540, 0, hid), sv
    assert ok2 and not rec2["save"]["ok"] and any(w.startswith("st_mtime_ns") for w in rec2["save"]["why"]), rec2


@pytest.mark.parametrize("side", ["F5B", "CTL"])
def test_f5b_hub_leg_each_hub_picks_its_own_row(game, side):
    """THE PER-HUB VIEW: rung5_hub.hub_leg, frozen, on hub_view(pred, side) warps to THAT side's hub and picks ITS
    row -- F5B lands 31101 with the removes' Zidane alone, CTL with the four the control adds ([0,2,3,1], the first
    empty slots) -- both at SC 2600, Int16[2] 6. Break: a view that ignores its side (both warp to one hub)."""
    fake, M, H, pred = _b_world(game)
    log = []
    with session(game, fake) as g:
        boot(g)
        rec = H.hub_leg(g, log, M.hub_view(pred, side))
        st = g.state
    want = {"F5B": _NG_PARTY, "CTL": [0, 2, 3, 1]}[side]
    assert (st.field_id, st.scenario, fake.entrance, fake.party) == (_PAST, 2600, 6, want), fake.party
    assert [s[1] for s in fake.executed if s[0] == "warp"] == [str(pred["hubs"][side]["id"])], fake.executed[:4]
    assert rec["picked"] == _DALI_ROW and fake.answered == [0], rec


@pytest.mark.parametrize("fault", ["sc 2610", "warps on"])
def test_f5b_enter_past_raises_on_another_sc_or_another_place(game, fault):
    """The LANDING's other clauses: the pick lands 31101 but control comes back at SC 2610 (not the beat) -- or the
    game warps him on out of 31101 before control returns (to member(352)). Each raises "landing: ...", named, the
    record logged not ok. Break: drop the SC clause or the place clause."""
    fake, M, _H, pred = _b_world(game)
    if fault == "sc 2610":
        fake.rows[_B_HUB]["sc"] = 2610
    else:
        fake.rows[_B_HUB]["then"] = (_WAKE, 30)
        fake.control_delay = 1 << 20                       # control never comes back in 31101 first
    log = []
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError) as err:
            M.enter_past(g, log, M.hub_view(pred, "F5B"), place=lambda f: _B_PLACES.get(f, f),
                         woke=lambda: fake.woken, arrive_s=5.0)
    want = ("landing: control in 31101 at SC 2610, not 2600" if fault == "sc 2610"
            else "landing: the pick left him in place 352 (field 31104), not 351 (31101)")
    assert str(err.value).startswith(want), str(err.value)
    assert log[-1]["k"] == "landing" and not log[-1]["ok"], log


def test_f5b_hub_leg_p_hubleg5b_fails_the_autosave_clause_on_another_slot(game, monkeypatch):
    """The hub-arrival read is fresh and names the arrival, but its SLOTS are not New Game's Zidane alone: the leg
    stands, its autosave clause is not ok, named. Break: drop the slot clause."""
    monkeypatch.setattr(sys.modules["harness.session"], "TITLE_SETTLE", 0)
    fake, M, _H, pred = _b_world(game)
    fake.ng_party = [0, 2, 3, 1]
    with session(game, fake) as g:
        ok, detail, rec = M.p_hubleg5b(g, M.hub_view(pred, "F5B"))
    assert ok and rec["save"]["fresh"] and not rec["save"]["ok"], (detail, rec["save"])
    assert "slot [0, 2, 3, 1], not [0, 255, 255, 255]" in rec["save"]["why"], rec["save"]["why"]


def test_f5b_hubleg_retry_keeps_the_first_legs_verdict():
    """P-HUBLEG's autosave retry (hubleg5b): the LEG's verdict is the first attempt's. A first leg that passed with
    its autosave clause not ok runs again for that clause alone -- a retry that fails AS A LEG (a flaky menu) is the
    clause failing, named, never the session's stop; a retry that passes replaces only the save clause; the first
    attempt's measures stand; both attempts are recorded. A first leg that fails is final (no retry). Break: take the
    retry's leg verdict (the flaky retry would end a session whose first leg passed)."""
    M, _H, _D = _rung5b()

    def leg(*results):
        it = iter(results)
        return lambda _g, _view: next(it)

    first = (True, "T5B_HUB: legged", {"k": "hub", "r": 152, "save": {"ok": False, "why": ["st_mtime_ns stale"]}})
    flaky = (False, "HarnessError: hub leg: no dialogue after 3 tries",
             {"k": "hub", "save": {"ok": False, "why": ["the leg never reached the hub's menu"]}})
    good = (True, "again", {"k": "hub", "r": 999, "save": {"ok": True, "slot": _NG_PARTY, "why": []}})
    ok, detail, rec = M.hubleg5b(None, {}, leg=leg(first, flaky))
    assert ok is True and detail.startswith("T5B_HUB: legged") and rec["r"] == 152 and rec["tries"] == 2, rec
    assert not rec["save"]["ok"] and rec["save"]["why"][0].startswith("the retry's leg failed: HarnessError"), rec
    assert [a["ok"] for a in rec["attempts"]] == [True, False], rec["attempts"]
    ok, _d, rec = M.hubleg5b(None, {}, leg=leg(first, good))
    assert ok and rec["save"]["ok"] and rec["r"] == 152 and rec["tries"] == 2, rec
    bad = (False, "HarnessError: hub leg: budget", {"k": "hub", "save": {"ok": False, "why": []}})
    ok, _d, rec = M.hubleg5b(None, {}, leg=leg(bad))
    assert ok is False and rec["tries"] == 1, rec


def test_f5b_party_read_needs_a_stable_file(game, monkeypatch):
    """The freshness rule's SHA clause: two reads 10 frames apart must agree. A write landing between them takes one
    more read 10 frames later (compared with the second): a file written once is then stable and fresh; a file still
    changing is not fresh, named. Break: drop the stability clause, or the repair read."""
    fake, M, _H, _pred = _b_world(game)
    seen = []
    real = M.read_autosave
    monkeypatch.setattr(M, "read_autosave", lambda p: seen.append(1) or real(p))
    with session(game, fake) as g:
        boot(g)
        g.warp(_B_HUB, entrance=0, scenario=2540)
        base = M.party_read(g)
        wait = g.wait_frames
        writes = {"left": 1}

        def churn(n):                                      # the autosave rewritten during a wait
            if writes["left"]:
                writes["left"] -= 1
                fake._autosave()
            return wait(n)
        g.wait_frames = churn
        seen.clear()
        once = M.party_read(g, base)
        n_once = len(seen)
        writes["left"] = 99
        still = M.party_read(g, base)
    assert n_once == 3 and once["stable"] and once["fresh"], (n_once, once)
    assert not still["stable"] and not still["fresh"] and any("sha changed" in w for w in still["why"]), still


@pytest.mark.parametrize("case", ["stale r3", "late write"])
def test_f5b_p_partyremove_voids_a_stale_r3_and_reads_after_control(game, monkeypatch, case):
    """P-PARTYREMOVE's freshness and timing. An F5B pick whose landing writes no autosave leaves r3 reading r2's file
    ([0,2,3,1], its mtime): VOID ("r3 not fresh"), never the FAIL a stale read would fake. And the engine writes a
    landing's autosave only a few frames after the field flips (control later still): r1 and r3 are read once control
    is back, so a late write is still read fresh -- PASS. Break: drop the freshness clause (the stale r3 FAILs), or
    read at the flip (the late write is missed: VOID)."""
    monkeypatch.setattr(sys.modules["harness.session"], "TITLE_SETTLE", 0)
    fake, M, _H, pred = _b_world(game)
    if case == "stale r3":
        fake.rows[_B_HUB]["saves"] = False
    else:
        fake.save_delay, fake.control_delay = 40, 60      # frames after the flip (the fake runs 960 a second)
    with session(game, fake) as g:
        ok, detail, rec = M.p_partyremove(g, pred)
    if case == "stale r3":
        assert ok is None and len(rec["attempts"]) == 2, (detail, rec)
        assert detail.split(": ", 1)[1].startswith("r3 not fresh"), detail
    else:
        assert ok is True and len(rec["attempts"]) == 1, (detail, rec)


# ---- F5c, P-AMBIENT (rung5b_hub.p_ambient, predictions v2): P-PARTYREMOVE's leg once more with the story trace armed.
# Its revisit (the debug warp 31101 -> 31113) carries 351's Byte[13] := 2 into the hub, whose prologue marks it 9; the
# FIXED hub's tail clears it (ip275) and 31101 then arrives clean (ip134 0 -> 1). :class:`_AmbientHubFake` writes those
# stores as script rows on every field entry the leg makes -- the ambient slot bytes (13, 14) only -- and withholds
# control where a report window would. The predictions are v2's skeleton (draft_predictions_v2 of the v1 skeleton).

_AMB_WINDOW = "Error Env Play()\nSlot=0"


class _AmbientHubFake(_PartyHubFake):
    """F5b's two hubs with the ambient slot bytes modelled. New Game leaves Byte[13] 1 (field 70's ambient playing).
    A HUB entry (31113/31114) runs the stock prologue on each slot byte -- 2 -> 9 (ip109 / ip190), else := 0 (ip131 /
    ip212), a 9 kept -- then, ``fixed``, the kit's silent tail (a 9 -> 0 at ip275 / ip294); ``hub_window``: a windowed
    tail instead, which on a 9 opens the report window and withholds control, never clearing. A 31101 entry (member
    351, its rows don 351) runs 351's: an arriving 9 is kept and its report window withholds control; else Byte[13]
    := 1 (ip134), Byte[14] := 0 (ip204), then ``sets2``: Byte[13] := 2 (ip1882, 351's Main_Init end) -- the 2 the
    revisit carries."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fixed, self.hub_window, self.sets2 = True, False, True
        #: F5c review: ``grant_after`` s -- the F5B hub (31113) withholds control that long after its entry, then
        #: grants it (a hub slower than session.warp's own wait); ``die_after_a`` -- the game exits right after the
        #: F5B hub's prologue marks the 9 (before the tail); ``fault_after_a`` -- the tracer faults there instead,
        #: the game playing on; ``throw_on_clear`` -- the tail's clear logs an event-engine exception
        self.grant_after: float | None = None
        self.die_after_a = self.fault_after_a = self.throw_on_clear = False
        self._grant_at: float | None = None

    def _step_world(self) -> None:
        if self._grant_at is not None and time.time() >= self._grant_at:
            self._grant_at, self.control = None, True
        super()._step_world()

    def _slot(self, byte: int, ip: int, new: int, don: int | None = None) -> None:
        self.donor = don
        try:
            self.script_store(0, 0, ip, byte, "Byte", new)
        finally:
            self.donor = None

    def _window(self) -> None:
        self.control = False
        self.texts, self.raw_texts = [_AMB_WINDOW], [_AMB_WINDOW]

    def _ambient_entry(self) -> None:
        fid = self.field_id
        if fid in self.rows:                                        # a hub
            for byte, nine, zero in ((13, 109, 131), (14, 190, 212)):
                v = self.story_bytes[byte]
                if v == 2:
                    self._slot(byte, nine, 9)
                elif v != 9:
                    self._slot(byte, zero, 0)
            marked = 9 in (self.story_bytes[13], self.story_bytes[14])
            if marked and fid == _B_HUB and self.die_after_a:
                self.returncode = 3                                  # the process is gone: its loop stops here
                return
            if marked and fid == _B_HUB and self.fault_after_a:
                self.story_fault("a hook threw (modelled)")         # off, no `off` row, the error published
            if self.hub_window and marked:
                self._window()
            elif self.fixed:
                for byte, ip in ((13, 275), (14, 294)):
                    if self.story_bytes[byte] == 9:
                        self._slot(byte, ip, 0)
                        if self.throw_on_clear:
                            self.throw("NullReferenceException", ("EventEngine.DoEventCode ()",
                                                                  "EventEngine.ProcessCode (Obj obj)"))
            if fid == _B_HUB and self.grant_after is not None:
                self.control, self._grant_at = False, time.time() + self.grant_after
        elif fid == _PAST:                                          # member(351)
            if self.story_bytes[13] == 9:
                self._window()
                return
            self._slot(13, 134, 1, 351)
            if self.story_bytes[14] != 9:
                self._slot(14, 204, 0, 351)
            if self.sets2:
                self._slot(13, 1882, 2, 351)

    def _execute(self, step: list[str]) -> None:
        op = step[0].lower()
        super()._execute(step)
        if op == "newgame":
            self.story_bytes[13], self.story_bytes[14] = 1, 0
        elif op == "warp":
            self._ambient_entry()

    def _picked(self) -> None:
        before = self.field_id
        super()._picked()
        if self.field_id != before:
            self._ambient_entry()


def _amb_world(game, **budget):
    """``(fake, rung5b_hub, rung5_hub, pred)``: the ambient fake and v2's skeleton predictions, ``budget`` overriding
    the leg's clocks (a test that expects a wait to run out shortens it) and ``probe_s`` the control marker's."""
    fake, M, H, pred = _b_world(game, _AmbientHubFake)
    pred = M.draft_predictions_v2(pred)
    probe = budget.pop("probe_s", 1.0)
    pred["ambient"]["probe_s"] = probe
    pred["budget"].update(budget)
    return fake, M, H, pred


def _amb_rows(M, g, rec) -> list:
    """The attempts' own trace files, read back: ``[(k, rows)]``."""
    return [(a["k"], M.ambient_rows(g.run_dir / a["file"])[0]) for a in rec["attempts"]]


@pytest.fixture
def amb_fast_close(monkeypatch):
    """The fake's open windows (351's report window, a hub's DIALOG, the pick's menu) never close on Cancel -- the
    game's report window does not either (design F5c 1.3) -- so restore_baseline's close_ui sits out its fixed 20 s on
    every leg that ends in one. 2 s decides the same thing (close_ui still gives up, the restore's outcome is recorded,
    the leg's verdict is unchanged): only the wait is shortened, for the legs that end in a window."""
    real = Session.close_ui
    monkeypatch.setattr(Session, "close_ui", lambda self, *, attempts=6, timeout=20.0:
                        real(self, attempts=attempts, timeout=min(timeout, 2.0)))


def test_f5b_ambient_the_fixed_hub_passes_the_table(game, monkeypatch):
    """P-AMBIENT on a fixed hub: the revisit enters 31113 with 351's 2 -- (a) ip109 2 -> 9 -- the tail clears it -- (b)
    ip275 9 -> 0 -- and 31101 arrives clean -- (c) ip134 0 -> 1, don 351 -- with control back: PASS, one attempt, its
    own file; the leg's control marker ran right after the warp (hub_control True, the hub's state recorded). Break:
    drop the marker (the leg has no hub_control: VOID drive-after-control)."""
    monkeypatch.setattr(sys.modules["harness.session"], "TITLE_SETTLE", 0)
    fake, M, _H, pred = _amb_world(game)
    with session(game, fake) as g:
        ok, detail, rec = M.p_ambient(g, pred)
        files = _amb_rows(M, g, rec)
        st = g.state
    assert ok is True and len(rec["attempts"]) == 1 and rec["outcome"] == "PASS", (detail, rec["attempts"])
    leg = rec["attempts"][0]["leg"]
    assert (leg["hub_control"], leg["presses"], leg["landed"], leg["member_control"]) == (True, 1, True, True), leg
    assert leg["hub_state"]["field"] == _B_HUB and leg["hub_state"]["control"] and leg["phase"] == "done", leg
    rows = [(x.fld, x.ip, x.old, x.new) for x in files[0][1] if x.k == "w" and x.target == "Global.Byte[13]"]
    assert (_B_HUB, 109, 2, 9) in rows and (_B_HUB, 275, 9, 0) in rows and (_PAST, 134, 0, 1) in rows, rows
    assert st.ui_state == "Title", "the title was not restored"


def test_f5b_ambient_no_arriving_2_is_void_and_retried_into_its_own_file(game, monkeypatch):
    """A 351 that never sets its 2 (``sets2`` off): the hub is entered with 1 and takes ip131 -- no precondition, VOID
    "no-precondition" (its old value named), retried ONCE, each attempt its own file (ambient_trace_1/2.jsonl).
    Break: no retry, or one file for both."""
    monkeypatch.setattr(sys.modules["harness.session"], "TITLE_SETTLE", 0)
    fake, M, _H, pred = _amb_world(game)
    fake.sets2 = False
    with session(game, fake) as g:
        ok, detail, rec = M.p_ambient(g, pred)
        files = _amb_rows(M, g, rec)
    assert ok is None and [a["outcome"] for a in rec["attempts"]] == ["no-precondition", "no-precondition"], rec
    assert [a["file"] for a in rec["attempts"]] == ["ambient_trace_1.jsonl", "ambient_trace_2.jsonl"], rec
    assert all(rows for _k, rows in files), "an attempt's file is missing or empty"
    assert "entered with Global.Byte[13] = 1" in rec["attempts"][0]["why"], rec["attempts"][0]["why"]


def test_f5b_ambient_the_arm_raising_is_void_arm_and_the_title_restored(game, monkeypatch):
    """An engine whose story trace cannot arm (no ``storytrace`` block): the leg records arm_error, has no file, and
    the table's first row names it -- VOID "arm", never "before-warp" -- retried once; the title restored after each.
    Break: drop the table's arm row (the leg's error in phase "arm" reads as before-warp)."""
    monkeypatch.setattr(sys.modules["harness.session"], "TITLE_SETTLE", 0)
    fake, M, _H, pred = _amb_world(game)
    fake.storytrace_proto = None
    with session(game, fake) as g:
        ok, detail, rec = M.p_ambient(g, pred)
        st = g.state
    assert ok is None and [a["outcome"] for a in rec["attempts"]] == ["arm", "arm"], (detail, rec["attempts"])
    assert all(a["leg"]["arm_error"] and a["leg"]["phase"] == "arm" for a in rec["attempts"]), rec["attempts"]
    assert st.ui_state == "Title", "the title was not restored"


@pytest.mark.usefixtures("amb_fast_close")
def test_f5b_ambient_an_unfixed_hub_fails_b_and_is_not_retried(game, monkeypatch):
    """The pre-fix hub (no tail): the revisit marks the 9 (a) and nothing clears it; 31101 arrives with it, keeps it
    and its report window withholds control. The hub DID grant control (hub_control True): FAIL (b) "the hub kept the
    9" -- a FAIL is evidence, never retried. Break: VOID it (its retry)."""
    monkeypatch.setattr(sys.modules["harness.session"], "TITLE_SETTLE", 0)
    fake, M, _H, pred = _amb_world(game, arrive_s=2.0)
    fake.fixed = False
    with session(game, fake) as g:
        ok, detail, rec = M.p_ambient(g, pred)
    assert ok is False and len(rec["attempts"]) == 1 and rec["outcome"] == "(b)", (detail, rec["attempts"])
    leg = rec["attempts"][0]["leg"]
    assert leg["hub_control"] is True and leg["member_control"] is False and leg["landed"], leg
    assert rec["why"].startswith("the hub kept the 9: (a)"), rec["why"]


@pytest.mark.usefixtures("amb_fast_close")
def test_f5b_ambient_a_hub_that_withholds_control_fails_b_never_granted(game, monkeypatch):
    """A windowed tail: the hub opens its report window on the 9 and never clears it. session.warp itself waits for
    control, so the warp raises before hub_open's marker runs -- the traced leg measures it on that error: hub_control
    False, the hub's DIALOG recorded -- FAIL (b) "and never granted control". Break: drop the marker on the warp's
    error (hub_control None: VOID cut-after-precondition)."""
    monkeypatch.setattr(sys.modules["harness.session"], "TITLE_SETTLE", 0)
    fake, M, _H, pred = _amb_world(game, hub_s=12.0)
    fake.hub_window = True
    with session(game, fake) as g:
        ok, detail, rec = M.p_ambient(g, pred)
    assert ok is False and rec["outcome"] == "(b)" and "never granted control" in rec["why"], (detail, rec["attempts"])
    leg = rec["attempts"][0]["leg"]
    assert leg["hub_control"] is False and leg["hub_state"]["dialog_open"] and leg["phase"] == "hub-warp", leg
    assert len(rec["attempts"]) == 1, rec["attempts"]


@pytest.mark.usefixtures("amb_fast_close")
def test_f5b_ambient_a_pick_that_raises_is_void_then_the_retry_passes(game, monkeypatch):
    """The F5B pick raises after the hub granted control (its menu never took the Confirm): attempt 1 VOID
    "drive-after-control" -- (a) and (b) are in its file -- and the retry PASSes; both files kept; THE FIX line
    (rung5b_hub.fix_line) re-derives BOTH attempts from their own files and decides on the first non-VOID. Break: one
    file name for both attempts (the retry overwrites the first)."""
    monkeypatch.setattr(sys.modules["harness.session"], "TITLE_SETTLE", 0)
    fake, M, H, pred = _amb_world(game)
    real, calls = H.hub_pick, []

    def pick(*a, **kw):
        calls.append(1)
        if len(calls) == 2:                                          # attempt 1's F5B pick (call 1 is the CTL leg's)
            raise HarnessError("hub leg: the menu never took its Confirm on 'Dali (SC 2600)' (2 presses)")
        return real(*a, **kw)
    monkeypatch.setattr(H, "hub_pick", pick)
    with session(game, fake) as g:
        ok, detail, rec = M.p_ambient(g, pred)
        files = dict(_amb_rows(M, g, rec))
        fix = M.fix_line(g.run_dir, {"ambient": rec}, pred)
    assert ok is True and [a["outcome"] for a in rec["attempts"]] == ["drive-after-control", "PASS"], rec["attempts"]
    one = [(x.fld, x.ip) for x in files[1] if x.k == "w" and x.target == "Global.Byte[13]"]
    assert (_B_HUB, 109) in one and (_B_HUB, 275) in one and files[2], one
    assert fix[0] is True and fix[1].startswith("PROVEN -- attempt 2 of 2"), fix
    assert "attempt 1 (ambient_trace_1.jsonl): NOT PROVEN (drive-after-control)" in fix[1], fix


def test_f5b_ambient_a_restore_that_raises_still_leaves_the_file_and_the_verdict(game, monkeypatch):
    """restore_baseline raising AFTER the leg: the trace was collected first, so the file is whole and the verdict the
    same PASS; the restore's error is recorded, never the leg's. The ORDER is pinned: the leg's collect runs before
    its closing restore (the fake's trace survives a restore, so the verdict alone cannot see a late collect). Break:
    let the restore's error escape the leg (its record is lost: VOID), or collect after the restore."""
    monkeypatch.setattr(sys.modules["harness.session"], "TITLE_SETTLE", 0)
    fake, M, _H, pred = _amb_world(game)
    with session(game, fake) as g:
        real, n, order = g.restore_baseline, [], []
        real_collect = g.collect_story

        def restore():
            n.append(1)
            order.append("restore")
            if len(n) == 2:                                          # the leg's own restore, in its finally
                raise HarnessError("close whatever UI is open failed")
            return real()

        def collect(*a, **kw):
            order.append("collect")
            return real_collect(*a, **kw)
        g.restore_baseline, g.collect_story = restore, collect
        ok, detail, rec = M.p_ambient(g, pred)
        files = _amb_rows(M, g, rec)
    assert ok is True and len(rec["attempts"]) == 1, (detail, rec["attempts"])
    assert "close whatever UI is open failed" in rec["attempts"][0]["restore"], rec["attempts"][0]
    assert files[0][1] and files[0][1][-1].k == "e" and files[0][1][-1].why == "off", "the trace is not whole"
    assert order == ["restore", "collect", "restore"], f"the collect is not before the leg's closing restore: {order}"


def test_f5b_ambient_partyremove_untraced_is_unchanged(game, monkeypatch):
    """P-PARTYREMOVE stays UNTRACED: with ``trace=None`` the leg arms nothing, records no leg and no phase, and its
    record and verdict are v1's -- on the same fake that P-AMBIENT's traced leg PASSes on. Break: build the leg record
    whatever ``trace`` is."""
    monkeypatch.setattr(sys.modules["harness.session"], "TITLE_SETTLE", 0)
    fake, M, _H, pred = _amb_world(game)
    with session(game, fake) as g:
        ok, detail, rec = M.p_partyremove(g, pred)
    assert ok is True and len(rec["attempts"]) == 1, (detail, rec)
    assert set(rec["attempts"][0]) == {"k", "reads", "log", "presses", "verdict", "why"}, sorted(rec["attempts"][0])
    assert not any(s[0] == "storytrace" for s in fake.executed), [s for s in fake.executed if s[0] == "storytrace"]
    assert not (game / "run" / "ambient_trace_1.jsonl").exists()


# ---- F5c, after the review: the control marker measures only a LIVE game, a cut trace never FAILs by what it lacks,
# the leg reports what it threw, P-AMBIENT never raises, and a tracer fault in it ends the session before its runs.

def test_f5b_ambient_the_marker_waits_its_probe_for_a_slow_hub(game, monkeypatch):
    """A hub that grants control AFTER session.warp's own wait gave up (its hub_s, 8 s) but within the marker's
    probe_s: the marker, run on the warp's error, waits and MEASURES control -- hub_control True -- so the table reads
    VOID drive-after-control (the leg still raised at the warp), never FAIL (b) / hub-stalled. Break: the marker
    samples once instead of waiting (hub_control False: FAIL hub-stalled)."""
    monkeypatch.setattr(sys.modules["harness.session"], "TITLE_SETTLE", 0)
    fake, M, _H, pred = _amb_world(game, hub_s=8.0, probe_s=4.0)
    fake.grant_after = 9.5
    with session(game, fake) as g:
        ok, detail, rec = M.p_ambient(g, pred)
    legs = [a["leg"] for a in rec["attempts"]]
    assert ok is None and [a["outcome"] for a in rec["attempts"]] == ["drive-after-control"] * 2, (detail, legs)
    assert all(lg["hub_control"] is True and lg["phase"] == "hub-warp" for lg in legs), legs
    assert all("the player to have control" in (lg["error"] or "") for lg in legs), legs


def test_f5b_ambient_a_game_that_exits_after_a_is_unmeasured_not_stalled(game, monkeypatch):
    """The game exits right after the F5B hub marks the 9 (a), before its tail: the warp raises "the game exited",
    and the marker run on it measures NOTHING -- hub_control None, hub_unmeasured names the exit, and the warp's own
    error stands as the leg's (the root cause) -- so the table reads VOID cut-after-precondition, never FAIL (b).
    Break: record hub_control False on any failed probe (the marker's own "no control" error replaces the exit)."""
    monkeypatch.setattr(sys.modules["harness.session"], "TITLE_SETTLE", 0)
    fake, M, _H, pred = _amb_world(game, probe_s=2.0)
    fake.die_after_a = True
    with session(game, fake) as g:
        ok, detail, rec = M.p_ambient(g, pred)
        files = _amb_rows(M, g, rec)
    one = rec["attempts"][0]
    leg = one["leg"]
    assert ok is None and one["outcome"] == "cut-after-precondition", (detail, rec["attempts"])
    assert leg["hub_control"] is None and "exited" in (leg["hub_unmeasured"] or ""), leg
    assert "exited" in leg["error"] and "no control in" not in leg["error"], leg["error"]
    rows = [(x.fld, x.ip, x.old, x.new) for x in files[0][1] if x.k == "w" and x.target == "Global.Byte[13]"]
    assert (_B_HUB, 109, 2, 9) in rows and not any(r[1] == 275 for r in rows), rows


def test_f5b_ambient_a_tracer_fault_ends_the_session_before_its_runs(game, monkeypatch):
    """The tracer faults in the F5B hub right after (a), the game playing on: attempt 1's collect raises "FAULTED" and
    its file stops at the fault -- (a) with no later row, hub_control True -- VOID cut-after-precondition (a cut trace
    never FAILs (b)); attempt 2's arm is refused (a fault latches until a relaunch): VOID arm. ambient_step then
    reads the published storytrace.error and ENDS the session, named (session["stopped"], a failed check), rather
    than start nine runs whose storytrace 1 would each be refused. Break: skip the tracer-health read (the session
    goes on)."""
    monkeypatch.setattr(sys.modules["harness.session"], "TITLE_SETTLE", 0)
    fake, M, _H, pred = _amb_world(game)
    fake.fault_after_a = True
    session_rec, saves = {}, []
    with session(game, fake) as g:
        go_on = M.ambient_step(g, pred, session_rec, lambda: saves.append(1))
        checks = list(g.checks)
    am = session_rec["ambient"]
    assert go_on is False and "faulted" in session_rec["stopped"] and am.get("tracer_fault"), session_rec
    assert [a["outcome"] for a in am["attempts"]] == ["cut-after-precondition", "arm"], am["attempts"]
    assert am["attempts"][0]["leg"]["hub_control"] is True and am["attempts"][0]["leg"]["collect_error"], am
    assert any(not c["ok"] and "tracer faulted in P-AMBIENT" in c["what"] for c in checks), checks
    assert saves, "the session record was never saved"


def test_f5b_ambient_the_leg_reports_what_it_threw_on_the_fix_line(game, monkeypatch):
    """The tail's clear logs an event-engine exception (the one in-game run of that branch; NC-THROW's mark comes
    after P-AMBIENT): the leg's own log mark catches it -- ``throws`` -- and THE FIX line prints it per attempt,
    REPORT-ONLY: the verdict stays PASS. Break: take no mark in the leg (no ``throws``, nothing on the line)."""
    monkeypatch.setattr(sys.modules["harness.session"], "TITLE_SETTLE", 0)
    fake, M, _H, pred = _amb_world(game)
    fake.throw_on_clear = True
    with session(game, fake) as g:
        ok, detail, rec = M.p_ambient(g, pred)
        fix = M.fix_line(g.run_dir, {"ambient": rec}, pred)
    leg = rec["attempts"][0]["leg"]
    assert ok is True and rec["outcome"] == "PASS", (detail, rec["attempts"])
    assert leg["throws"] and leg["throws"][0][0] == "NullReferenceException", leg.get("throws")
    assert fix[0] is True and "thrown in its leg (report-only): [['NullReferenceException'" in fix[1], fix


def test_f5b_ambient_rows_and_p_ambient_never_raise(tmp_path, monkeypatch):
    """P-AMBIENT runs before any run, so it must never raise: a trace file the reader cannot open (an indexer holding
    it: PermissionError) is ``([], why)``, and a verdict that raises is VOID "read-error" -- both attempts kept.
    Break: catch only TraceError in ambient_rows, or call ambient_verdict outside the guard."""
    M, _H, _D = _rung5b()
    pred = M.draft_predictions_v2(M.draft_predictions())
    path = tmp_path / "ambient_trace_1.jsonl"
    path.write_text('{"k":"e"}\n', encoding="utf-8")

    def locked(_p):
        raise PermissionError(13, "The process cannot access the file", str(_p))
    monkeypatch.setattr(M.T, "read_trace", locked)
    rows, why = M.ambient_rows(path)
    assert rows == [] and "PermissionError" in why, why

    def once(g, pred_, *, trace=None):
        pathlib.Path(trace).write_text('{"k":"e"}\n', encoding="utf-8")
        return {"k": "partyremove", "reads": {}, "verdict": None, "why": "-",
                "leg": {"file": pathlib.Path(trace).name}}

    def broken(*_a, **_kw):
        raise KeyError("precondition")
    monkeypatch.setattr(M, "_partyremove_once", once)
    monkeypatch.setattr(M, "ambient_verdict", broken)
    import types
    ok, detail, rec = M.p_ambient(types.SimpleNamespace(run_dir=tmp_path), pred)
    assert ok is None and [a["outcome"] for a in rec["attempts"]] == ["read-error", "read-error"], rec["attempts"]
    assert "PermissionError" in rec["attempts"][0]["read_error"] and "KeyError" in rec["attempts"][0]["why"], rec


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


# ---------------------------------------------------------------------------------------------
# THE RENDER RATE (harness.tickrate). He moves per 30 Hz FIELD TICK -- one MovePC call a tick walking, two running,
# 30u each -- not per render frame, and the harness has run at ~31 fps for whole launches (and once ~105): a frame
# there carries him twice what the 60 fps the per-frame speeds were measured at said. Every press is now SIZED at the
# measured rate's average, every rule JUDGED at the most its frames can carry him, and what a press moved is checked
# against the rate. These drive the fake at another RENDER rate (``render_fps``: its virtual clock, published as
# ``rt``, which the driver's TickClock measures) -- ``FakeGame(fps=...)`` is only the loop's wall pace. Each fails on
# the per-frame driver (RUN_SPEED 30 / WALK_SPEED 15 a frame).
# ---------------------------------------------------------------------------------------------


_OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}


def _held_directions(steps) -> set:
    """The direction buttons a request's ``hold`` steps press (Cancel is the gait, not a direction)."""
    return {s.split()[1] for s in steps if s.startswith("hold ") and s.split()[1] in _OPPOSITE}


@pytest.mark.parametrize("publish", [("rt",), ("mtime",)])
def test_a_smooth_hold_at_30_fps_does_not_overshoot(game, publish):
    """600u straight down an open room at 30 fps: sized at the MEASURED rate a run frame is 60u (a tick), so the hold
    is ~9 frames and lands on the goal -- where sized at 30u a frame it was 19, ran ~1200u into the far wall, and the
    next hold came straight back (a quarter of the in-game holds at 31 fps reversed the one before). No hold reverses
    the one before it, and the walk takes two at the most. The route's record carries the rate it was planned by.
    ``("mtime",)`` is TODAY'S engine: no clock in state.json, the driver times it by the file's modified time (the
    fake runs in real time at 30 fps and stamps each write with its virtual time)."""
    fake = FakeGame(game, render_fps=30.0, publish=publish)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -300, 0)
        sent = _counting(g)
        rec = g.route_to(300.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), smooth=True)
        holds = [_held_directions(steps) for steps in sent if _held_directions(steps)]
    assert rec["reached"] and rec["landed"] is None, rec
    assert 1 <= len(holds) <= 2, holds
    for a, b in zip(holds, holds[1:]):
        assert not {_OPPOSITE[d] for d in a} & b, f"a hold reversed the one before it: {holds}"
    fps = rec["fps"]
    assert fps["source"] == publish[0] and fps["fps"] == pytest.approx(30.0, rel=0.05), fps
    assert fps["per_frame"] == pytest.approx(1.0, rel=0.05), fps


def test_a_press_at_30_fps_keeps_the_zone_it_was_told_to_avoid(game):
    """A gateway 100u past the goal of a straight 600u leg, at 30 fps. Planned per frame, the hold was 19 frames and
    judged to carry him (19 + 2) x 30 = 630u -- PROBE_HAZARD_PAD short of the gateway, so it kept the rule -- and at a
    tick a frame it carried him 19 ticks and a tail, 1200u: straight through the gateway. The gateway lay between the
    judged reach and the true one. Planned at the measured rate, the hold's reach (Rate.reach: the most its frames can
    carry him) is what keeps the pad, and the hold stops on the goal."""
    from ff9mapkit.content import pathfind
    gate = _rect(400, -300, 600, 300)
    room = (-1000, -1000, 1000, 1000)
    assert pathfind.seg_poly_gap((-300, 0), (300, 0), gate) >= pathfind.KEEPOUT_MARGIN_W          # the leg: clear
    fake = FakeGame(game, walkmesh=room, render_fps=30.0)
    fake.regions = {30820: [{"zone": gate, "to": 30821, "arrive": (0, 0)}]}
    fake.exit_frames = 30
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -300, 0)
        sent = _counting(g)
        rec = g.route_to(300.0, 0.0, avoid=[gate], walkmesh=_flat_bgi(*room), prior=_prior(), smooth=True)
    assert rec["landed"] is None and not fake.fired, (rec, fake.fired)
    assert rec["reached"] and rec["waypoints"] == [[300, 0]], rec
    rate = g.rate()
    assert rate.ready and rate.fps == pytest.approx(30.0), rate
    # the premise, in numbers: the per-frame plan's 19 frames, judged at 630u, truly reach 1200u -- the gateway at 700u
    # between the two -- where the measured plan's hold reaches no further than the pad allows
    assert (19 + 2) * 30 <= 700 - g.PROBE_HAZARD_PAD < rate.reach(19, "run"), rate.describe()
    first = sent[0]
    assert [s.split()[:2] for s in first if s.startswith("hold ")] == [["hold", "right"]], first
    frames = int(first[0].split()[2])
    assert rate.reach(frames, "run") <= 700 - g.PROBE_HAZARD_PAD, (frames, rate.describe())


def test_a_calibration_probe_at_30_fps_keeps_the_zone_its_old_reach_fell_short_of(game):
    """A gateway 230u to his right. A 4-frame run probe was judged to carry him (4 + 2) x 30 = 180u -- clear of the
    gateway by its 30u pad -- and at 30 fps it carries him 4 ticks, 240u: into it (ProbeLeftControl, the probe lost like
    the 350 <-> 351 ping-pong). Judged at the measured rate (Rate.reach: its 4 ticks and a tick of tail, 300u) the run
    probe is refused and the short walked one measures the axis instead; nothing fires."""
    zone = _rect(230, -100, 400, 100)
    fake = FakeGame(game, render_fps=30.0)
    fake.regions = {30820: [{"zone": zone, "to": 30821, "arrive": (0, 0)}]}
    fake.exit_frames = 30
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, 0, 0)
        basis = g.calibrate_axes(hazards=[zone], prior=_prior())
        rate = g.rate()
    assert not fake.fired, fake.fired
    assert rate.reach(4, "run") == pytest.approx(300.0) and rate.reach(2, "walk") == pytest.approx(90.0), rate
    assert basis["h"][0] > 0.99 and basis["v"][1] > 0.99, basis


@pytest.mark.parametrize("smooth", [False, True])
def test_the_basis_check_runs_at_30_fps(game, smooth):
    """A basis 90 degrees off the game's -- the well-formed lie a probe slid along a wall measures -- sends every press
    sideways at full speed. The basis check catches that (walk_to's, and the smooth walk's): a burst that covered real
    ground not along what it pressed. At 30 fps, judged per frame, every run burst of three frames or more "moved too
    much" to be evidence (60u a frame against 30 commanded plus 60), so the check never ran and the walk wandered on;
    judged at the rate, the burst is evidence and the lie is refused, the basis discarded."""
    fake = FakeGame(game, walkmesh=(-2000.0, -2000.0, 2000.0, 2000.0), render_fps=30.0)
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        g.rate(require=True)
        g._axes[30810] = {"v": (1.0, 0.0), "h": (0.0, -1.0)}      # the game's up is +z, its right +x
        _stand(g, fake, 0, -300)
        with pytest.raises(HarnessError, match="axis basis for field 30810 disagrees"):
            if smooth:
                g.route_to(0.0, 300.0, walkmesh=_flat_bgi(-2000, -2000, 2000, 2000), prior=None, smooth=True)
            else:
                g.walk_to(0.0, 300.0, tolerance=45.0, max_bursts=1)          # the first burst is the one judged
        assert 30810 not in g._axes


def test_a_free_press_that_outruns_the_rate_is_loud(game):
    """F1 SPEED MODE (FastForwardFactor 3, which the engine publishes nowhere): every tick comes three times as fast,
    so each probe carries him three times what the measured rate says its frames can -- and every reach the driver
    judges would be a third of the truth. Three presses in a row outside the rate raise, naming the speed mode, rather
    than walk on judging zones at a third of the reach."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        assert g.rate(require=True).fps == pytest.approx(60.0)
        g.calibrate_axes()                                             # the control: at the rate, nothing is loud
        fake.fast_forward = 3.0
        with pytest.raises(HarnessError, match="SPEED MODE") as err:
            g.calibrate_axes(recalibrate=True)
        assert "3 presses in a row" in str(err.value), err.value


def test_the_push_lock_opens_at_120_fps(game):
    """The walk-through lock needs 27 MovePC calls into him unbroken -- 14 run TICKS. At 120 fps a frame holds a quarter
    of one, so the 27 FRAMES a 30u-a-frame driver held made about 13 calls and never opened it: a passable body read as
    stuck, a blocker placed. Held for the frames SURE of 14 ticks at the measured rate, it opens."""
    fake = FakeGame(game, render_fps=120.0)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -300, -300)
        g.calibrate_axes(hazards=[], prior=_prior())
        fake.blockers = {30820: [(0.0, 0.0, 152.0)]}
        _stand(g, fake, -152, 0)
        record, walked = {"pushes": 0, "pushed": 0}, [0.0]
        mark = len(fake.executed)
        assert g._push_through(200.0, 0.0, 30820, walked, record) == "pushed", g.state.pos
        holds = [int(s[2]) for s in fake.executed[mark:] if s[0] == "hold" and s[1] != "cancel"]
        rate = g.rate()
    assert record == {"pushes": 1, "pushed": 1} and g.state.player_x > 152, (record, g.state.pos)
    assert rate.fps == pytest.approx(120.0) and holds[0] == rate.frames_for_ticks(1) == 4, (holds, rate.describe())
    assert holds[1] >= rate.frames_for_ticks(14) == 56, holds


def test_a_press_whose_reach_must_be_judged_is_never_planned_on_the_calibrated_default(game):
    """Before the clock has measured anything the rate is the calibrated 60 fps (``ready`` False): sizing may lean on
    it, a rule may not. ``rate(require=True)`` reads the game for a measured one and, with none -- the title screen
    pairs no frames -- raises instead of guessing."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.RATE_WAIT = 0.3
        published(g, lambda s: s.ui_state == "Title")
        rate = g.rate()
        assert not rate.ready and rate.fps == 60.0 and rate.source == "default", rate
        with pytest.raises(HarnessError, match="no MEASURED render rate"):
            g.rate(require=True)


# ---------------------------------------------------------------------------------------------
# CALL COUNTS, TIME BUDGETS, SETTLE, ARM -- the render rate's other half. What must be SURE of a call count is counted in
# whole ticks at the measured rate (a running press's calls in pairs), or read off the yaw where s90 publishes it; a
# time budget is seconds, held as the frames sure to last them; the settle's stillness spans field ticks, not
# publishes; and the arm cycle waits for the agent to SAY it saw the disarm. Most drive the fake's WHOLE ticks
# (``ticks="quantized"``: FPSManager's accumulator), whose phase nobody publishes -- pinned where it matters
# (:func:`_next_tick_in`) to the one a planner has to survive. Each fails on the per-frame driver.
# ---------------------------------------------------------------------------------------------


def _next_tick_in(fake, frames: int) -> None:
    """Put the quantized fake's tick accumulator in the phase whose next field tick falls ``frames`` frames on (1 .. the
    frames a tick spans at its render rate). FPSManager ticks when ``2 * next < T`` after ``next -= dt`` each frame
    (harness.tickrate.TickAccumulator), so a ``next`` of ``T / 2 + (frames - 0.5) * dt`` crosses on the ``frames``-th.
    Called from the fake's own thread (:func:`_after_step`), between a step's execution and the frames it presses."""
    T, dt = 1.0 / fake.tick_hz, 1.0 / fake.render_fps
    assert fake.tick_mode == "quantized" and 1 <= frames <= round(T / dt), (fake.tick_mode, frames)
    fake._acc._next = T / 2.0 + (frames - 0.5) * dt


def _after_step(fake, match, fn) -> None:
    """Run ``fn()`` in the fake's thread right after it executes each step ``match(step)`` accepts (the op and its
    arguments as the agent reads them) -- in the frame the step lands on, before the frames it presses run."""
    execute = fake._execute

    def spy(step):
        execute(step)
        if match(step):
            fn()
    fake._execute = spy


def test_the_push_probe_moves_him_at_120_fps(game):
    """The probe before a push asks one thing: is he stuck? At 120 fps a field tick falls on every 4th frame, and the
    two walked frames a 60 fps driver probed with can fall between two -- no MovePC call, no step: he "moved nothing"
    on open floor, a push was spent on nobody (counted, and read by the tour as an unstick), and the hold ran blind.
    Probed for the frames SURE of a tick at the measured rate (Rate.frames_for_ticks(1): 4), the probe moves him even in
    the worst phase -- a tick three frames on -- and nothing is pushed."""
    fake = FakeGame(game, render_fps=120.0, ticks="quantized")
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -300, -300)
        g.calibrate_axes(hazards=[], prior=_prior())
        _stand(g, fake, -400, 0)
        assert g.rate(require=True).fps == pytest.approx(120.0)
        _after_step(fake, lambda s: s[:2] == ["hold", "cancel"], lambda: _next_tick_in(fake, 3))
        record, walked = {"pushes": 0, "pushed": 0}, [0.0]
        mark = len(fake.executed)
        got = g._push_through(0.0, 0.0, 30820, walked, record)
        probe = [int(s[2]) for s in fake.executed[mark:] if s[0] == "hold" and s[1] != "cancel"]
    assert got == "free" and record == {"pushes": 0, "pushed": 0}, (got, record, probe)
    assert probe == [4] and 0 < walked[0] < 60, (probe, walked)


def test_a_walled_face_press_at_120_fps_is_not_predicted_faced(game):
    """An engine that cannot publish the facing (pre-s90): the facing press is predicted, never read -- so its CALLS
    must be the ones it is sure of. He stands in the east-wall door against the wall, facing 150 degrees off either
    pad nearest the door (the room is yawed 22.5 degrees: both sit 22.5 off its bearing), and the press into the wall
    turns him without moving him -- so no travel can check the count. Four whole calls face the door from any yaw; the
    8 walked frames a 60 fps driver sized that as hold TWO ticks at 120 fps (every 4th frame), turn him two calls, and
    leave him 76 degrees off -- shut -- while the prediction said faced: the tour's REAL strike on a door never faced.
    Sized at the measured rate (Rate.frames_for_ticks(4): 16 frames), the prediction is the fake's own gate."""
    from ff9mapkit.content import doorface
    door = {"zone": _EAST_DOOR, "to": None, "face": True}
    fake = FakeGame(game, render_fps=120.0, ticks="quantized", twist=22.5)
    fake.walkmesh, fake.clearance = _flat_bgi(), 80.0
    fake.regions = {30820: [door]}
    a = math.radians(22.5)
    basis = {"v": (-math.sin(a), math.cos(a)), "h": (math.cos(a), math.sin(a))}      # the fake's twist, measured
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = basis
        _stand(g, fake, 520, 0)
        fake._face_deg = 97.5
        assert g.rate(require=True).fps == pytest.approx(120.0)
        # every press lands its ticks on frames 4, 8, 12... after it: the frames after its keys lift run none
        _after_step(fake, lambda s: s[:2] == ["hold", "cancel"], lambda: _next_tick_in(fake, 4))
        mark = len(fake.executed)
        rec = _here_cross(g, _EAST_DOOR, npcs=False)
        presses = [int(s[2]) for s in fake.executed[mark:] if s[:2] == ["hold", "cancel"]]
        gate, err = doorface.door_faced(fake.player[0], fake.player[2], fake._face_deg, _EAST_DOOR[0], _EAST_DOOR[1])
        least = g.rate().frames_for_ticks(g.ROUTE_FACE_CALLS)
    assert presses and presses[0] >= least == 16, presses          # the slide along the wall may ask a call more
    assert rec["faced"] is gate, (rec, gate, err, fake._face_deg)
    assert gate is True and abs(err) <= 47 and not fake.fired, (gate, err)


def test_face_calls_never_credits_more_than_the_turn_ran_at_30_fps(game):
    """s90's closed loop turns him in place and reports the turn's yaws. At 30 fps a frame holds a whole tick -- two run
    calls -- and a hitched frame catches up several: the 4-frame turn here ran 14 calls. A count of frames at the
    calibrated 60 fps said 4 (a call a frame); the frames' SURE count at the measured rate says 8 (four ticks, in
    pairs) -- never more than ran. The yaws cannot say 14: a 14-call turn ends a thousandth of the way from the pad's
    heading, which is a calibrated measurement known within the leg's spread, and a tenth of a degree of that moves the
    count by a call (Session._calls_turned asks at the heading's whole uncertainty, and gets no one count) -- so the
    record keeps the sure one."""
    door = {"zone": _EAST_DOOR, "to": None, "face": True}
    fake = FakeGame(game, render_fps=30.0)
    fake.walkmesh, fake.clearance = _flat_bgi(), 80.0
    fake.regions = {30820: [door]}
    fake.facing_mode = "published"
    ran = []
    begin, turn = fake._begin_turn, fake._turn_in_place

    def begin_spy(dirs, frames):
        begin(dirs, frames)
        fake.hitch(0.1, frame=fake.frame + 2)                 # the turn's second frame takes 133 ms: 4 ticks

    def turn_spy(vx, vz, calls):
        turn(vx, vz, calls)
        ran.append(calls)
    fake._begin_turn, fake._turn_in_place = begin_spy, turn_spy
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=60.0)
        assert g.rate(require=True).fps == pytest.approx(30.0)
        mark = len(fake.executed)
        rec = _here_cross(g, _EAST_DOOR, npcs=False)
        turns = [s for s in fake.executed[mark:] if s[0] == "turn"]
    assert [int(s[2]) for s in turns] == [4], turns                   # one turn, the frames sure of 4 run ticks
    assert round(sum(ran)) == 14, ran                                  # 1 + 4 + 1 + 1 ticks, two calls each
    assert rec["face_calls"] == 8 <= round(sum(ran)), rec              # the four ticks its frames are sure of
    assert (rec["faced"], rec["face_measured"]) == (True, True), rec


def test_the_face_wait_spans_two_ticks_at_120_fps(game):
    """He stands in a gated door already facing it, and the door fires on its own on the SECOND field tick after the
    walk ended there (its tag 2 runs once a tick). Waited four frames -- two ticks at 60 fps, ONE at 120 -- the step
    judged it shut and pressed, the door fired under the press, and its crossing was recorded ``during`` "face": a door
    the facing step never opened, credited to it. Waited the frames sure of two ticks at the measured rate
    (Rate.frames_for_ticks(2): 8), nothing is pressed and the crossing is the walk's own."""
    door = {"zone": _EAST_DOOR, "to": None, "arrive": (0, 0), "face": True}
    fake = FakeGame(game, fps=30, render_fps=120.0, ticks="quantized")
    fake.walkmesh, fake.clearance = _flat_bgi(), 80.0
    fake.regions = {30820: [door]}
    fake.exit_frames = 30
    armed = {}
    step = fake._step_world

    def step_spy():                               # the door goes live on the 2nd tick after the wait began
        if armed and door["to"] is None and fake.ticks_run - armed["ticks"] >= 2:
            door["to"] = 30821
        step()

    def on_wait():
        if not armed:
            _next_tick_in(fake, 4)                # the ticks fall 4 and 8 frames on: the 2nd is the wait's last frame
            armed["ticks"] = fake.ticks_run
    fake._step_world = step_spy
    with session(game, fake) as g:
        g.RATE_WAIT = 10.0                        # a 30 Hz loop at 120 fps: the arrival's second is four of the wall's
        _gated_start(g, fake, (450, 0), yaw=-90.0)
        assert g.rate(require=True).fps == pytest.approx(120.0)
        mark = len(fake.executed)
        _after_step(fake, lambda s: s[0] == "wait", on_wait)
        rec = _here_cross(g, _EAST_DOOR, npcs=False, timeout=5)
        after = fake.executed[mark:]
    first = next(k for k, s in enumerate(after) if s[0] == "wait")
    assert not _direction_holds(fake, mark) and not [s for s in after if s[0] == "turn"], after
    assert int(after[first][1]) == 8, after
    assert [f["to"] for f in fake.fired] == [30821] and rec["landed"] == 30821, (rec, fake.fired)
    assert rec["during"] != "face" and rec["faced"] is None and rec["face_pad"] is None, rec


def test_settle_does_not_stop_between_ticks_at_120_fps(game):
    """He moves only on a field tick, every 4th frame at 120 fps, and between two he stands exactly still. Two samples
    at the same spot a publish or two apart -- the settle's old "still" -- can both fall between ticks mid-walk; it
    returned there, and the rest of the walk landed in the next press's measurement (the 30820 tail, at a rate the bench
    never ran at). The stillness must span the frames sure of two ticks at the measured rate: settle returns only once
    he has stopped."""
    fake = FakeGame(game, fps=40, render_fps=120.0, ticks="quantized")
    with session(game, fake) as g:
        # the RULE under test, never the wall clock: a 40 Hz loop turns this 60-frame hold over a second and a half of
        # the wall's -- more under load -- and a settle out of time returns the last state it saw, mid-walk: the very
        # symptom this rules out, blamed on the span
        g.RATE_WAIT, g.SETTLE_TIMEOUT = 30.0, 30.0
        boot(g)
        g.warp(30820)
        _stand(g, fake, -500, 0)
        assert g.rate(require=True).fps == pytest.approx(120.0)
        g.state_every(1)                          # every frame published: the driver reads frames between ticks
        g.send("hold right 60", wait=False)       # 15 ticks of run: 900u, half a second of the game's clock
        published(g, lambda s: s.player_x > -490, timeout=30)
        t0 = time.time()
        st = g.settle()
        assert time.time() - t0 < g.SETTLE_TIMEOUT, "the settle ran out of time: not the span's verdict"
        released = fake.held.get("right", 0)
        published(g, lambda s: s.frame > released + 16, timeout=30)
        final = fake.player[0]
    assert st.frame >= released and st.player_x == pytest.approx(final), (st, released, final)
    assert final == pytest.approx(400.0), final


def test_route_waits_are_seconds_at_120_fps(game):
    """A freeze that never lifts: the stall ladder WAITS before it pushes -- ROUTE_WAITS waits, each long enough for a
    walker to walk through or a script to let go, which happen on the wall clock. As 90 FRAMES a wait lasted 0.75 s at
    120 fps and the ladder climbed to the push twice as fast. Held as the frames sure to last ROUTE_WAIT_SECONDS at the
    measured rate, each wait lasts that long on the game's own clock."""
    fake = FakeGame(game, render_fps=120.0)
    fake.freezes = {30820: [{"zone": _BAND, "frames": None}]}
    waits = []
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -400, 0)
        assert g.rate(require=True).fps == pytest.approx(120.0)
        g.ROUTE_WAIT_BUDGET = 2                   # two waits make the point; the rest would only be more of them
        wait_frames = g.wait_frames

        def timed(frames):
            rt = fake.rt
            wait_frames(frames)
            waits.append((frames, fake.rt - rt))
        g.wait_frames = timed
        rec = g.route_to(400.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), unstick=True, smooth=True)
    assert rec["frozen"] and rec["waits"] == 2 and not rec["reached"], rec
    ladder = [w for w in waits if w[0] >= 60]
    assert len(ladder) == rec["waits"], waits
    assert all(frames == 180 and took >= g.ROUTE_WAIT_SECONDS for frames, took in ladder), waits


def test_flee_holds_for_the_timeout_at_120_fps(game):
    """The flee's hold is FRAMES and its window wall-clock SECONDS: the roll can come any second of the window, and the
    bumpers must be down for all of it. Sized at 60 frames a second, a 6-second flee at 120 fps lifted them after 4 --
    and a roll that could first land 4.2 s in never rolled: the dice took the blame for the driver. Sized at the
    measured rate (Rate.frames_at_least of the window, the field's rate carried into the battle), it rolls and
    escapes. TODAY'S engine: no clock in state.json -- the fake runs in real time and the driver times it by the
    file's modified time. The HOLD is asserted first and on its own: it is the driver's; the escape also waits on a
    real-time stand-in keeping the wall's pace, which a loaded machine can slow."""
    fake = FakeGame(game, render_fps=120.0, publish=("mtime",))
    fake.escape_rate = 0.0
    start = {}
    step = fake._step_battle

    def step_spy():                               # the roll may land only from 4.2 s into the hold, on the game's clock
        if "rt" not in start and fake._is_held("l1") and fake._is_held("r1"):
            start["rt"] = fake.rt
        if "rt" in start and fake.rt - start["rt"] >= 4.2:
            fake.escape_rate = 1.0
        step()
    fake._step_battle = step_spy
    g = session(game, fake)
    g.__enter__()
    try:
        boot(g)
        g.warp(30810)
        assert g.rate(require=True).fps == pytest.approx(120.0, rel=0.03)      # measured on the field
        g.start_battle(105)
        published(g, lambda s: s.commands_enabled)
        mark = len(fake.executed)
        escaped = g.flee(timeout=6.0)
        hold = next(int(s[2]) for s in fake.executed[mark:] if s[:2] == ["hold", "l1"])
    finally:
        g.__exit__(None, None, None)
    assert hold >= 120 * 6.0, hold                                # the bumpers down for the whole window
    assert escaped is True, (hold, start)


def test_rearm_waits_for_the_disarm_document(game):
    """The agent polls the arm file every 30 frames -- a second at 30 fps -- and a delete+create inside one poll is
    INVISIBLE to it: no reset of its sequence numbers, held keys, error latch or story tracer. The cycle slept 0.85 s,
    shorter than that poll. A real 30 Hz loop, its next look at the arm file a whole poll away: the re-arm returns
    only once the agent has published its disarm document ("armed": false), and the agent then arms afresh -- the
    stale error latch cleared."""
    ch = Channel(game, label="first")
    ch.reset()
    fake = FakeGame(game, fps=30).start()
    try:
        assert ch.arm(force_cycle=False) is None
        deadline = time.time() + 5
        while time.time() < deadline and not fake.armed:
            time.sleep(0.02)
        assert fake.armed
        fake.error = "a refusal from the last run"            # the latch only a real re-arm clears
        fake.arm_poll_frame = fake.frame                      # the next poll a whole 30 frames away: a second
        second = Channel(game, label="second", owner_pid=ch.owner_pid)
        t0 = time.time()
        assert second.arm() is True
        took = time.time() - t0
        kinds = [e["kind"] for e in second.events()]
        assert kinds.count("disarmed") == 1, kinds                # observed BEFORE the arm file came back
        deadline = time.time() + 5
        while time.time() < deadline and fake.arm_transitions < 2:
            time.sleep(0.02)
        assert fake.arm_transitions == 2 and fake.error is None, (fake.arm_transitions, fake.error)
        assert took >= 0.85, took                                 # the premise: the old sleep was too short here
    finally:
        ch.disarm()
        fake.stop()


def test_running_calls_come_in_pairs(game):
    """A run is two MovePC calls a TICK, and ticks come whole: an odd number of run frames at 60 fps (half a tick
    each) is sure of the ticks those frames surely hold, two calls apiece -- three frames, one tick, two calls; never
    the three that one call a frame credited. The yaw a walk's last hold leaves (where a facing step starts,
    Session._held_yaw) is judged by those calls."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -120, 0)
        g.rate(require=True)
        spread = g._heading_spread(_prior(), _prior())
        [(x, z, tol, leg)] = g._route_legs([(-120.0, 0.0), (0.0, 0.0)], [], (), spread=spread)
        mark = len(fake.executed)
        assert g._walk_leg(x, z, tol, leg, False) == "arrived"
        holds = [int(s[2]) for s in fake.executed[mark:] if s[0] == "hold"]
    assert holds[:1] == [3] and not [s for s in fake.executed[mark:] if s[:2] == ["hold", "cancel"]], holds
    (_buttons, _u), calls = leg["turned"]
    assert calls == 2, leg["turned"]


def test_a_finish_press_that_ran_no_tick_is_no_wall_at_120_fps(game):
    """The zone's finish presses short walks into the zone -- here three frames, under a tick at 120 fps (a tick every
    4th frame), and in the worst phase they run none: no MovePC call, he moves nothing. Read as a WALL, that pad was
    given up and the other side's short press met the same, two presses that "moved nothing" were a stall, and the
    finish ended OUTSIDE a zone he was 20u from on open floor -- at a door, the tour's strike. A press not sure of a tick
    that moved nothing proves nothing: the next is the frames sure of one (Rate.frames_for_ticks(1): 4), and he is in."""
    from ff9mapkit.content import pathfind
    zone = _rect(0, -100, 100, 100)
    fake = FakeGame(game, render_fps=120.0, ticks="quantized")
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -20, 0)
        assert g.rate(require=True).fps == pytest.approx(120.0)
        # every walked press lands its first tick 4 frames on: a press of 3 runs none
        _after_step(fake, lambda s: s[:2] == ["hold", "cancel"], lambda: _next_tick_in(fake, 4))
        spread = g._heading_spread(_prior(), _prior())
        [(x, z, tol, leg)] = g._route_legs([(-20.0, 0.0), (10.0, 0.0)], [], (), spread=spread, zone=zone,
                                           floor=_flat_bgi())
        mark = len(fake.executed)
        got = g._walk_leg(x, z, tol, leg, False)
        presses = [int(s[2]) for s in fake.executed[mark:] if s[:2] == ["hold", "cancel"]]
    assert got == "arrived" and pathfind.poly_gap(fake.player[0], fake.player[2], zone) < 0, (got, fake.player)
    assert presses[0] < 4 and presses[1:] == [4], presses          # the premise, then the press sure of a tick


def test_the_facing_press_is_never_made_on_a_rate_nobody_measured(game):
    """The open-loop facing press (an engine that cannot publish the facing) is PREDICTED: its calls are what its frames
    are sure of, its travel what they can reach -- both at the render rate. With none measured (the clock paired no
    frames), the calibrated 60 fps would credit a 120 fps press twice the calls it ran and judge a 31 fps one at half
    its reach, so nothing is pressed: ``faced`` False, no pad, no calls -- LIVE, the walker's limit, never the door's
    strike."""
    from harness.tickrate import Rate
    D = _tour_module()
    fake = _gated_room(game, [{"zone": _EAST_DOOR, "to": None, "face": True}])
    with session(game, fake) as g:
        _gated_start(g, fake, (450, 0), yaw=90.0)
        g._clock.rate = Rate.default                          # a clock that never paired a frame
        g.RATE_WAIT = 0.3
        mark = len(fake.executed)
        rec = _here_cross(g, _EAST_DOOR, smooth=False, npcs=False)
    assert not _direction_holds(fake, mark), fake.executed[mark:]
    assert rec["inside"] is True and not fake.fired, rec
    assert rec["faced"] is False and rec["face_pad"] is None and rec["face_calls"] is None, rec
    assert D.failure(rec) == "live", rec


# ---------------------------------------------------------------------------------------------
# THE REVIEW'S FINDINGS, PINNED. A carried rate is checked, never trusted blind; a wait for one is counted on the
# game's clock; a press that may have run no tick is no wall (walk_to, a blind probe); a stillness or a wait that must
# last is sized, before any rate is measured, at the fastest rate the game can be taken to run; a hitch is not a rate
# and a slope is not a short press; the calls a turn ran are read off the yaw only as exactly as its heading is known;
# a dash-inhibited field walks a run. And the rules the review mutated away unnoticed: each call site that waits for a
# measured rate, and each that judges a press at Rate.reach rather than its average.
# ---------------------------------------------------------------------------------------------


def test_a_rate_switched_while_nobody_read_is_measured_again_before_a_press(game):
    """s1c dropped from 60 to 31 fps in 221 s nobody read. Measured at 60, then three seconds with no read in which the
    game drops to 30, then a route whose gateway sits between the reach 60 fps judges and the one 30 fps truly has: the
    estimate from before the gap is STALE (never ``ready``), so the route waits for the rate to be measured again and
    plans at 30 -- the gateway never fires. Kept as it was, the stale 60 planned 'hold right 18' and it fired."""
    gate = _rect(400, -300, 600, 300)
    room = (-1000, -1000, 1000, 1000)
    fake = FakeGame(game, walkmesh=room)                             # 60 fps, rt published
    fake.regions = {30820: [{"zone": gate, "to": 30821, "arrive": (0, 0)}]}
    fake.exit_frames = 30
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -300, 0)
        assert g.rate(require=True).fps == pytest.approx(60.0)
        fake.render_fps = 30.0                                       # the regime switch ...
        time.sleep(3.0)                                              # ... in a stretch nobody reads: no pairs
        st = g.settle()
        assert not g.rate().ready, g.rate().describe()                # stale: measured before the gap
        rec = g.route_to(300.0, 0.0, avoid=[gate], walkmesh=_flat_bgi(*room), prior=_prior(), smooth=True)
    assert not fake.fired and rec["landed"] is None, (rec, fake.fired)
    assert rec["fps"]["fps"] == pytest.approx(30.0) and rec["fps"]["frame"] > st.frame, rec["fps"]


def test_the_wait_for_a_rate_counts_the_games_clock(game):
    """What the wait for a measured rate waits for is counted on the GAME'S clock: the arrival's first second, then
    MIN_PAIRS pairs of published frames -- frames the game renders at its own pace. A stand-in whose loop turns 10
    frames of a 60 fps game a wall second (a busy machine, the nightly gate's six workers: the same, less evenly) takes
    the wall's 1.6 s over the pairs' 16 frames alone, after the arrival's second: a wall-only budget of 2 s raised 'no
    MEASURED render rate' on a healthy game. RATE_WAIT counts both clocks -- two seconds of the game's here are twelve
    of the wall's. (RATE_WAIT_CAP, the bound for a game whose clock never moves, is lifted out of the way: it is not the
    rule under test.)"""
    fake = FakeGame(game, fps=10)                                    # the virtual 60 fps at a sixth of the wall's pace
    with session(game, fake) as g:
        g.RATE_WAIT_CAP = 60.0
        boot(g)
        g.warp(30810)
        g._clock.reset()                                             # the visit's second starts at the next read
        rate = g.rate(require=True)
    assert rate.ready and rate.fps == pytest.approx(60.0), rate.describe()


@pytest.mark.parametrize("fps,phase", [(60.0, 2), (120.0, 4)])
def test_a_walk_to_hop_that_may_run_no_tick_is_no_wall(game, fps, phase):
    """walk_to's last burst is SIZED at the average speed: a 25u hop is one walked frame at 60 fps and three at 120 --
    under a tick either way, and in the worst phase (the next tick ``phase`` frames on) it runs no MovePC call and
    moves nothing. Counted as a stall, two in a row were "a wall" and strict raised 'could not reach' on open floor.
    _walk_leg's own rule: a burst not sure of a tick that moved nothing is no stall, and the next is the frames sure of
    one."""
    fake = FakeGame(game, render_fps=fps, ticks="quantized")
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, 0, 0)
        g.rate(require=True)
        _after_step(fake, lambda s: s[:2] == ["hold", "cancel"], lambda: _next_tick_in(fake, phase))
        mark = len(fake.executed)
        assert g.walk_to(25.0, 0.0, tolerance=16.0) is True, g.state.pos
        holds = [int(s[2]) for s in fake.executed[mark:] if s[:2] == ["hold", "cancel"]]
    least = g._least_frames(g.rate())
    assert holds[0] < least and least in holds[1:], holds             # the premise, then the burst sure of a tick


@pytest.mark.parametrize("fps,phase", [(60.0, 2), (120.0, 3)])
def test_a_blind_probe_that_may_run_no_tick_is_pressed_again(game, fps, phase):
    """Blind calibration (no prior) presses one walked frame a probe -- the shortest press there is to SEND, not the
    shortest sure of a tick: at 120 fps it runs none three times in four, and in the worst phase every probe moved
    nothing and calibration refused, 'boxed in between trigger regions', on open floor 310u from the door. A probe not
    sure of a tick that moved nothing is pressed again for the frames that are -- judged blind at their reach."""
    door = _rect(10, -600, 300, 600)
    fake = FakeGame(game, render_fps=fps, ticks="quantized")
    fake.regions = {30820: [{"zone": door, "to": 30821, "arrive": (0, -400)}]}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -300, 0)
        g.rate(require=True)
        _after_step(fake, lambda s: s[:2] == ["hold", "cancel"], lambda: _next_tick_in(fake, phase))
        basis = g.calibrate_axes(hazards=[door], prior=None)
    assert not fake.fired, fake.fired
    assert basis["h"][0] > 0.99 and basis["v"][1] > 0.99, basis


def test_settle_before_the_first_estimate_never_stops_between_ticks(game):
    """Before the launch's first estimate the rate is the calibrated default, and a settle's stillness sized there was 4
    frames -- less than one field tick at 144 fps, where a tick falls every 4.8 frames: two still reads between ticks,
    mid-walk, returned (x -440 of a hold that ran on to 280). A span that must be SURE of its ticks is sized, while
    nothing is measured, at UNMEASURED_FPS -- the fastest the game can be taken to run -- and the settle returns only
    once he has stopped."""
    fake = FakeGame(game, fps=40, render_fps=144.0, ticks="quantized")
    with session(game, fake) as g:
        g.RATE_WAIT, g.SETTLE_TIMEOUT = 30.0, 30.0                   # the rule under test, never the wall clock
        boot(g)
        g.warp(30820)
        _stand(g, fake, -500, 0)
        g._clock.reset()                                             # nothing measured: a launch's first second
        g.state_every(1)
        g.send("hold right 60", wait=False)
        published(g, lambda s: s.player_x > -490, timeout=30)
        assert not g.rate().ready
        st = g.settle()
        released = fake.held.get("right", 0)
        published(g, lambda s: s.frame > released + 24, timeout=30)
        final = fake.player[0]
    assert st.frame >= released and st.player_x == pytest.approx(final), (st, released, final)


def test_three_free_presses_short_of_their_sure_calls_are_loud_and_a_slope_is_not(game):
    """The cross-check's SHORT side: a free press that moved him less than its sure calls step -- a tick rate below
    the ini's -- three times in a row raises. On free floor a step is 30u times the floor's cos(slope)
    (PSXMovementMethod), so a slope is judged at SLOPE_STEP_FLOOR: stock 350's door to 353 stands on 0.854, and three
    facing presses there that each ran exactly their sure calls (9 walked frames at 60 fps: 4 calls, 102u) are no
    strike -- judged at a flat floor they raised, blaming the rate on a healthy field."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        rate = g.rate(require=True)
        assert rate.calls_sure(9, "walk") == 4 and rate.calls_sure(16, "walk") == 8
        for _ in range(3):
            g._check_movement(4 * 30.0 * 0.854, 9, "walk", rate, free=True)
        assert g._strikes == []
        g._check_movement(100.0, 16, "walk", rate, free=True)       # 240u sure, 100 moved: under half
        g._check_movement(100.0, 16, "walk", rate, free=True)
        with pytest.raises(HarnessError, match="3 presses in a row") as err:
            g._check_movement(100.0, 16, "walk", rate, free=True)
        assert "short of" in str(err.value) and "FieldTPS is lower" in str(err.value), err.value
        g._check_movement(100.0, 16, "walk", rate, free=False)      # not free: a wall may have stopped it
        g._check_movement(0.0, 16, "walk", rate, free=True)         # nothing moved: a hold, not a rate
        assert g._strikes == []


def test_a_hitch_in_a_press_is_logged_as_the_hitchs_not_a_strike(game):
    """A HITCH -- one frame of 120 ms at 60 fps -- catches up four ticks in that frame (FPSManager.cs:94-99): a 4-frame
    run probe with one in it moves ~360u where Rate.reach says 180. Three such probes in a row are three hitches, not a
    wrong rate: the clock sees the time the probe's frames took (TickClock.excess_ticks), and the overshoot within
    those ticks is logged as the hitch's. Blamed on the rate they raised, naming F1 speed mode."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        assert g.rate(require=True).fps == pytest.approx(60.0)
        g.calibrate_axes()
        _stand(g, fake, 0, 0)
        for button in ("up", "right", "down"):
            _after_step(fake, lambda s, b=button: s[:2] == ["hold", b], lambda: fake.hitch(0.12, frame=fake.frame + 3))
            moved = g._probe_axis(button, 4)
            fake._execute = FakeGame._execute.__get__(fake)            # this probe's hitch only
            assert moved is not None and moved[1] > g.rate().reach(4, "run"), moved
        assert g._strikes == []


def test_the_calls_a_turn_ran_are_read_off_the_yaw_only_as_exactly_as_its_heading_is_known(game):
    """doorface.calls_from_turn counts the calls a turn ran from its two yaws -- exactly, toward the heading the engine
    turned him to. The pad's heading is a calibrated measurement, and near the end of a turn a fraction of a degree of
    it moves the count by a call: 7 walked calls from 20 degrees off read 7.85 against a heading 0.2 degrees off, and
    were taken as 8 -- a call more than ran, credited. A count is taken only where the heading's whole uncertainty reads
    one whole count (and a run's in whole ticks: an odd count is no run turn); else None -- the frames' sure count."""
    from ff9mapkit.content import doorface
    fake = FakeGame(game)
    with session(game, fake) as g:
        def yaws(y0, target, k):
            return y0, round(doorface.turn_step(y0, target, k), 3)
        y0, y1 = yaws(20.0, 0.0, 7)                                   # the truth: 7 calls toward 0
        assert g._calls_turned(y0, y1, 0.0, "walk") == 7              # the true heading: exact
        assert g._calls_turned(y0, y1, 0.2, "walk") == 8              # 0.2 degrees off it, taken as exact: a call more
        assert g._calls_turned(y0, y1, 0.2, "walk", spread=0.5) is None   # the heading known to half a degree: no count
        y0, y1 = yaws(0.0, 90.0, 3)                                   # a short turn: its count reads through the spread
        assert g._calls_turned(y0, y1, 90.0, "walk", spread=2.0) == 3
        y0, y1 = yaws(-10.0, 90.0, 13)                                # an odd count is no run turn: runs come in pairs
        assert g._calls_turned(y0, y1, 90.0, "walk") == 13 and g._calls_turned(y0, y1, 90.0, "run") is None
        y0, y1 = yaws(-10.0, 90.0, 14)
        assert g._calls_turned(y0, y1, 90.0, "run") == 14
        assert g._calls_turned(20.0, 20.0, 0.0, "walk", spread=5.0) == 0   # no call ran: 0 at any heading


def test_a_calibration_after_a_relaunch_waits_for_the_measured_rate(game):
    """calibrate_axes' ``rate(require=bool(polys))``, at the call site. A just-reset clock (a relaunch: the rate is never
    carried across launches) at 30 fps and a gateway 230u above him (+z, the first axis probed): judged on the calibrated
    default the 4-frame run probe reaches (4 + 2) x 30 = 180u and is pressed -- and carries him 240u, into it. The site
    waits for the measured rate, and refuses the run probe."""
    zone = _rect(-100, 230, 100, 400)
    fake = FakeGame(game, render_fps=30.0)
    fake.regions = {30820: [{"zone": zone, "to": 30821, "arrive": (0, 0)}]}
    fake.exit_frames = 30
    with session(game, fake) as g:
        g.RATE_WAIT = 10.0
        boot(g)
        g.warp(30820)
        _stand(g, fake, 0, 0)
        g._clock.reset()
        assert not g._clock.rate().ready
        basis = g.calibrate_axes(hazards=[zone], prior=_prior())
    assert not fake.fired, fake.fired
    assert basis["h"][0] > 0.99 and basis["v"][1] > 0.99, basis


def test_a_hold_after_a_relaunch_waits_for_the_measured_rate(game):
    """_walk_leg's ``rate(require=True)``. A just-reset clock at 30 fps and a gateway 100u past a 600u leg's goal:
    planned on the calibrated default the first hold (19 frames, judged at 630u) truly carries him 1140u -- through the
    gateway. The site waits for the measured rate instead, and the hold stops on the goal."""
    gate = _rect(400, -300, 600, 300)
    room = (-1000, -1000, 1000, 1000)
    fake = FakeGame(game, walkmesh=room, render_fps=30.0)
    fake.regions = {30820: [{"zone": gate, "to": 30821, "arrive": (0, 0)}]}
    fake.exit_frames = 30
    with session(game, fake) as g:
        g.RATE_WAIT = 10.0
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -300, 0)
        spread = g._heading_spread(_prior(), _prior())
        [(x, z, tol, leg)] = g._route_legs([(-300.0, 0.0), (300.0, 0.0)], [gate], (), spread=spread)
        g._clock.reset()
        assert not g._clock.rate().ready
        got = g._walk_leg(x, z, tol, leg, False)
    assert not fake.fired and got == "arrived", (got, fake.fired, fake.player)


def test_a_push_after_a_relaunch_waits_for_the_measured_rate(game):
    """_push_through's ``rate(require=True)``: the push's line is judged at its reach, its lock counted in ticks. A
    just-reset clock at 30 fps, a passable body against him at x=-152 and an avoided region from x=910: planned on the
    calibrated default the lock is 28 frames and the shortest push 31, judged to reach 1020u -- to 868, + the 30u pad
    = 898, clear -- where 31 frames at 30 fps truly run 31 ticks, 1860u, through the region. The site waits for the
    measured rate: at it the shortest push (17 frames) reaches 1080u, to 928, and nothing is pressed."""
    room = (-3000.0, -3000.0, 3000.0, 3000.0)
    hazard = _rect(910, -300, 1060, 300)
    fake = FakeGame(game, walkmesh=room, render_fps=30.0)
    fake.blockers = {30820: [(0.0, 0.0, 152.0)]}
    fake.regions = {30820: [{"zone": hazard, "to": 30821, "arrive": (0, 0)}]}
    fake.exit_frames = 30
    with session(game, fake) as g:
        g.RATE_WAIT = 10.0
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -152, 0)
        spread = g._heading_spread(_prior(), _prior())
        [(_x, _z, _tol, leg)] = g._route_legs([(-152.0, 0.0), (200.0, 0.0)], [hazard], (), spread=spread)
        leg["pressed"] = (("right",), (1.0, 0.0))
        g._clock.reset()
        record, walked = {"pushes": 0, "pushed": 0}, [0.0]
        mark = len(fake.executed)
        got = g._push_through(200.0, 0.0, 30820, walked, record, leg)
    assert got == "stuck" and record["pushes"] == 0 and not fake.fired, (got, record, fake.fired)
    assert not [s for s in fake.executed[mark:] if s[:2] == ["hold", "right"]], fake.executed[mark:]


def test_a_blind_probe_is_refused_within_its_reach_not_its_average(game):
    """The blind probe's rule at the UPPER bound. A one-frame walked probe averages 15u at 60 fps and can reach 60u
    (Rate.reach(1, "walk"): its tick and the tail tick). A gateway 70u off lies inside reach + the 30u pad (90) and
    outside average + pad (45): blind calibration refuses before pressing anything."""
    zone = _rect(70, -100, 300, 100)
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": zone, "to": 30821, "arrive": (0, 0)}]}
    fake.exit_frames = 30
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, 0, 0)
        rate = g.rate(require=True)
        assert rate.speed("walk") + g.PROBE_HAZARD_PAD < 70 < rate.reach(1, "walk") + g.PROBE_HAZARD_PAD
        mark = len(fake.executed)
        with pytest.raises(HarnessError, match="blind probe"):
            g.calibrate_axes(hazards=[zone])
        assert not [s for s in fake.executed[mark:] if s[0] == "hold"], fake.executed[mark:]


def test_a_calibration_probe_is_judged_at_its_reach_not_its_average(game):
    """The calibration probe's rule at the UPPER bound. At 30 fps a 4-frame run probe averages 240u and can reach 300u
    (its 4 ticks and the tail tick). A gateway 280u to his right lies between: judged at the average (240 + the 30u
    pad) the run probe was pressed and could carry him in; judged at Rate.reach it is refused and the walked probe
    measures the axis."""
    zone = _rect(280, -100, 400, 100)
    fake = FakeGame(game, render_fps=30.0)
    fake.regions = {30820: [{"zone": zone, "to": 30821, "arrive": (0, 0)}]}
    fake.exit_frames = 30
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, 0, 0)
        rate = g.rate(require=True)
        assert rate.speed("run") * 4 + g.PROBE_HAZARD_PAD < 280 < rate.reach(4, "run"), rate.describe()
        mark = len(fake.executed)
        basis = g.calibrate_axes(hazards=[zone], prior=_prior())
        rights = [int(s[2]) for s in fake.executed[mark:] if s[:2] == ["hold", "right"]]
    assert not fake.fired, fake.fired
    assert rights and max(rights) < 4, rights                          # the run probe right was never pressed
    assert basis["h"][0] > 0.99 and basis["v"][1] > 0.99, basis


def test_a_push_line_is_judged_at_its_reach_not_its_average(game):
    """The blind push's line at the UPPER bound. At 30 fps the lock is 14 run frames and the shortest push 17: it
    averages 1020u -- from x=-152 against the body to 868, + the 30u pad = 898 -- and can reach 1080u (18 ticks), to
    928. An avoided region from x=910 lies between: judged at the reach the push is refused, never pressed."""
    room = (-2000.0, -2000.0, 2000.0, 2000.0)
    hazard = _rect(910, -300, 1060, 300)
    fake = FakeGame(game, walkmesh=room, render_fps=30.0)
    fake.blockers = {30820: [(0.0, 0.0, 152.0)]}
    fake.regions = {30820: [{"zone": hazard, "to": 30821, "arrive": (0, 0)}]}
    fake.exit_frames = 30
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -300, 0)
        g.ROUTE_WAIT_SECONDS = 0.5
        rec = g.route_to(200.0, 0.0, avoid=[hazard], walkmesh=_flat_bgi(*room), prior=_prior(), unstick=True,
                         smooth=True)
    assert not fake.fired and rec["landed"] is None, (rec, fake.fired)
    assert rec["pushes"] == 0, rec                 # the push whose line can reach the region is never pressed


def test_the_ini_field_tps_is_the_tick_rate_the_driver_plans_by(game):
    """Session feeds [Graphics] FieldTPS to its TickClock. A game ticking 60 times a second (FieldTPS 60, honoured:
    Enabled = 1) moves him twice the 30 Hz figure a frame; read from the ini, every probe is within its reach. Ignored,
    the rate said 30 Hz, every probe outran it and the cross-check raised."""
    (game / "Memoria.ini").write_text("[Graphics]\nEnabled = 1\nFieldTPS = 60\n", encoding="utf-8")
    fake = FakeGame(game)
    fake.fast_forward = 2.0                                          # the stand-in's ticks: 30 x 2 = the ini's 60
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        rate = g.rate(require=True)
        assert rate.tick_hz == 60.0 and rate.per_frame() == pytest.approx(1.0), rate.describe()
        g.calibrate_axes()
        assert g._strikes == []


def test_a_choice_and_a_cutscene_page_wait_their_ticks_at_120_fps(game):
    """choose()'s wait after Confirm and watch_cutscene's page turn are TICKS the window's script counts (CHOOSE_TICKS
    6, CUTSCENE_PAGE_TICKS 4): 12 and 8 frames at 60 fps -- literals once, which at 120 fps waited half the ticks. Held
    as the frames sure of them at the measured rate: 24 and 16."""
    fake = FakeGame(game, render_fps=120.0)
    waits = []
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        assert g.rate(require=True).fps == pytest.approx(120.0)
        wait_frames = g.wait_frames

        def timed(frames):
            ticks = fake.ticks_run
            wait_frames(frames)
            waits.append((frames, fake.ticks_run - ticks))
        g.wait_frames = timed
        fake.offer(["Yes", "No"], header="Really?")
        published(g, lambda s: s.choice is not None)
        g.choose(1)
        chose = list(waits)
        waits.clear()
        fake.scene("Garnet\n“Zidane!”", "Garnet\n“Hmph.”")
        g.watch_cutscene(timeout=30)
    assert chose[-1][0] == 24 and chose[-1][1] >= g.CHOOSE_TICKS, chose
    pages = [w for w in waits if w[0] == 16]
    assert pages and all(t >= g.CUTSCENE_PAGE_TICKS for _f, t in pages), waits


def test_the_walkers_wait_is_seconds_at_120_fps(game):
    """A villager that stays in the way outlasts the box's wait: waited ROUTE_WALKER_WAIT_SECONDS at a time within
    ROUTE_WALKER_BUDGET_SECONDS a call -- TIMES, a walker walking on the wall clock. As 8 and 480 FRAMES a 120 fps game
    waited half as long each time and was ``boxed`` in half the budget. Held as the frames sure to last them, each wait
    lasts its seconds on the game's clock, and the box is waited out for the budget's."""
    fake = FakeGame(game, render_fps=120.0)
    kid = _creeping(8)
    waits = []
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, -450, 0)
        fake.blockers = {30820: [kid]}
        published(g, lambda s: s.objects and s.objects[0]["moving"])
        assert g.rate(require=True).fps == pytest.approx(120.0)
        g.ROUTE_NPC_REPLANS = 0
        g.ROUTE_WALKER_BUDGET_SECONDS = 80 / 60
        g._box_step = lambda *a, **kw: False
        stood = _step_in_front(g, (kid, (170, 0), [(170, 0), (170, 700)], 0.05))
        wait_frames = g.wait_frames

        def timed(frames):
            rt = fake.rt
            wait_frames(frames)
            waits.append((frames, fake.rt - rt))
        g.wait_frames = timed
        rec = g.route_to(450.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), npcs=True, smooth=True)
    assert stood and rec["boxed"] and rec["boxed_by"] == "walkers", rec
    box = [w for w in waits if w[0] == g._frames_lasting(g.ROUTE_WALKER_WAIT_SECONDS)]
    assert box and box[0][0] == 16 and all(took >= g.ROUTE_WALKER_WAIT_SECONDS for _f, took in box), waits
    assert sum(took for _f, took in box) >= g.ROUTE_WALKER_BUDGET_SECONDS - g.ROUTE_WALKER_WAIT_SECONDS, waits


def test_a_push_on_a_field_that_inhibits_running_holds_the_lock_in_walked_calls(game):
    """A field that INHIBITS RUNNING (stock's DASHOFF: the Prima Vista cargo room, the Palace Dungeon) walks a run
    hold -- one MovePC call a tick -- and the agent says so (``input.dash_inh`` 1). The walk-through lock needs 27 calls
    into him unbroken: counted in run ticks, 14, the push held 28 frames that made 14 calls and never opened it -- a
    passable body read as stuck. Read as the walk it is, the lock is 27 walked ticks and he goes through."""
    fake = FakeGame(game)
    fake.dash_inhibit = True
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -300, -300)
        g.calibrate_axes(hazards=[], prior=_prior())
        fake.blockers = {30820: [(0.0, 0.0, 152.0)]}
        _stand(g, fake, -152, 0)
        assert g._gait("run") == "walk" and g._gait("walk") == "walk"
        record, walked = {"pushes": 0, "pushed": 0}, [0.0]
        mark = len(fake.executed)
        got = g._push_through(200.0, 0.0, 30820, walked, record)
        holds = [int(s[2]) for s in fake.executed[mark:] if s[:2] == ["hold", "right"]]
    assert got == "pushed" and record == {"pushes": 1, "pushed": 1} and fake.player[0] > 152, (got, record, holds)
    assert holds[-1] >= g.rate().frames_for_calls(27, "walk") == 54, holds                # 27 walked ticks


def test_settle_waits_out_a_published_position_that_lags_its_ticks(game):
    """The published position LAGS its own frame's ticks where the agent's Update runs before the actors' -- an order
    Unity does not fix, so it can come and go. At 120 fps a tick falls every 4th frame; where the publish after one tick
    is late and the next is not, the position reads still for 5 frames mid-walk -- past a span sure of ONE tick (4
    frames), which returned there. SETTLE_TICKS is two: 8 frames, and the settle returns only once he has stopped."""
    fake = FakeGame(game, fps=40, render_fps=120.0, ticks="quantized")
    with session(game, fake) as g:
        g.RATE_WAIT, g.SETTLE_TIMEOUT = 30.0, 30.0                   # the rule under test, never the wall clock
        boot(g)
        g.warp(30820)
        _stand(g, fake, -500, 0)
        assert g.rate(require=True).fps == pytest.approx(120.0)
        g.state_every(1)
        ticked = []
        step = fake._step_world

        def step_spy():                           # the loop advanced the clock just before: this frame's ticks
            step()
            if fake._frame_ticks > 0:
                ticked.append(fake.frame)
        fake._step_world = step_spy
        fake.publish_lag = lambda f: bool(ticked) and ticked[-1] == f and len(ticked) % 2 == 0
        g.send("hold right 60", wait=False)
        published(g, lambda s: s.player_x > -490, timeout=30)
        st = g.settle()
        released = fake.held.get("right", 0)
        published(g, lambda s: s.frame > released + 16, timeout=30)
        final = fake.player[0]
    assert st.frame >= released and st.player_x == pytest.approx(final), (st, released, final)


def test_a_step_out_of_a_held_walkers_way_is_judged_at_its_reach_not_its_average(game):
    """_box_step's rule at the UPPER bound: the step out of a held walker's way must keep PROBE_HAZARD_PAD off the leg's
    zones for as far as its frames can carry him. At 30 fps, with a zone 230u off (room 200u): three run frames average
    180u -- inside the room -- and can reach 240u (their ticks and the tail tick): judged at the average the step was
    three frames; judged at Rate.reach it is the longest whose reach fits, two run frames (180u)."""
    fake = FakeGame(game, walkmesh=(-1000, -1000, 1000, 1000), render_fps=30.0)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        rate = g.rate(require=True)
        kid = _villager(160, 0, uid=6, path=[(160, 0), (-900, 0)], speed=3.0)
        leg, watch = _box_leg(g, fake, [kid], settled=lambda s: s.objects[0]["x"] < 155)
        zone = _rect(-400, -50, -230, 50)                                   # 230u off: 200u of room past the pad
        leg["hazards"] = [zone]
        room = 230.0 - g.PROBE_HAZARD_PAD
        assert rate.speed("run") * 3 <= room < rate.reach(3, "run") and rate.reach(2, "run") <= room, rate.describe()
        basis, since = g._axes[30820], {}
        sent = _counting(g)
        for _ in range(12):
            if g._box_step(basis, leg, since):
                break
            g.wait_frames(8)
            g._npc_view(watch, g.state)
        holds = [int(s.split()[2]) for steps in sent for s in steps if s.startswith("hold ") and "cancel" not in s]
    assert holds and max(holds) == 2 and not fake.fired, (holds, fake.fired)


def test_the_objects_that_box_him_are_judged_at_the_smallest_press_reach(game):
    """_boxers' rule at the UPPER bound: an object boxes him when it refuses the SMALLEST press -- one walked frame, as
    far as it can carry him (Rate.reach: its tick and the tail tick, 60u at 60 fps). A villager standing 200u ahead,
    r 152: that press's line comes to within 140u of its centre, inside ROUTE_BODY_PAD of ``r`` -- a boxer. Judged at
    the frame's AVERAGE travel (15u) the line stopped 33u off ``r`` and the villager was no boxer: a box it made read
    as the spot's own geometry."""
    fake = FakeGame(game, walkmesh=(-1000, -1000, 1000, 1000))
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        rate = g.rate(require=True)
        leg, watch = _box_leg(g, fake, [_villager(200, 0, uid=9)])
        here = (g.state.player_x, g.state.player_z)
        assert rate.speed("walk") + 152.0 + g.ROUTE_BODY_PAD < 200.0 < rate.reach(1, "walk") + 152.0 + g.ROUTE_BODY_PAD
        boxers = g._boxers(g._axes[30820], here, (1000.0, 0.0), leg, rate=rate)
    assert [d["uid"] for d in boxers] == [9], boxers


# ---- O1 (studies/story-trace/o1_opening.py): the opening's route driver, on the fake. A director thread stages the
# segment the way the game plays it: two pages, control, the candle choice + Cinna + the naming screen, the tutorial
# battle, the kidnap question (default: the looping answer), then the warp out. The driver must answer only by its
# frozen rule table, keep the default name, close the tutorial, and stop at the end field.

def _o1_pred(**over):
    sys.path.insert(0, str(REPO / "studies" / "story-trace"))
    import o1_opening as O
    if not (O.CHAIN_DIR / "campaign.toml").is_file():
        pytest.skip(f"the O1 chain is not built here ({O.CHAIN_DIR}): the O1 draft reads its members from it")
    pred = O.draft_predictions()
    pred.update(start={"S": 30820, "F": 30820}, end_field=30821, members={}, names={},
                candle={"donor": 30820, "x": 300.0, "z": 0.0})
    pred["budget"] = dict(pred["budget"], settle_s=0.3)
    pred["choices"] = [dict(c, donor=30820 if c["donor"] is not None else None) for c in pred["choices"]]
    pred.update(over)
    return O, pred


def _o1_director(fake, stop, phases):
    """Run each ``(ready(fake) -> bool, act(fake))`` phase in turn, as soon as its condition holds."""
    def loop():
        for ready, act in phases:
            while not stop.is_set() and not ready(fake):
                time.sleep(0.002)
            if stop.is_set():
                return
            act(fake)
    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return t


def _o1_candle_scene(fake):
    fake.scene({"header": "What shall I do?", "options": ["Light the candle", "Cancel"], "default": 0},
               "Cinna\n“Who's there!?”", {"naming": 0}, "Zidane\n“It's me, Zidane!”")


def _o1_idle(fake):
    return not fake._beats and fake.ui_state == "FieldHUD"


def _o1_confirmed_near(fake, x, z, reach=80.0):
    """A Confirm was pressed with control while he stood within ``reach`` of (x, z)."""
    if not fake.control or math.hypot(fake.player[0] - x, fake.player[2] - z) > reach:
        return False
    return any(s[:2] == ["press", "confirm"] for s in fake.executed[-3:])


def test_o1_drive_plays_the_opening_segment_by_its_rules(game):
    O, pred = _o1_pred()
    fake = FakeGame(game)
    fake.enemy_hit = 0
    fake.tutorial_scenes = {336}
    fake.atb_gain = 400
    stop = threading.Event()
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        fake.scene("Zidane\n“Sure is dark...”", "Zidane\n“Guess nobody's here yet...”")
        hint = "\nPress the  button when the ? appears."
        _o1_director(fake, stop, [
            # control, with the region's hint up the whole time (an overlay: never paged)
            (lambda f: _o1_idle(f) and f.control, lambda f: f.say(hint)),
            # a Confirm pressed near the candle opens its choice (the hint closes, as the script closes it)
            (lambda f: _o1_confirmed_near(f, 300.0, 0.0), lambda f: (f.say(), _o1_candle_scene(f))),
            (lambda f: f.named == [0] and _o1_idle(f), lambda f: f.start_battle(336)),
            (lambda f: f.battle_result == 1 and f.ui_state == "FieldHUD",
             lambda f: f.scene("Baku\n“Gwahahaha!”", {"header": "Who do we kidnap?",
                                                      "options": ["Queen Brahne", "Princess Garnet"], "default": 0},
                               "Blank\n“Right.”")),
            (lambda f: len(f.answered) == 2 and _o1_idle(f), lambda f: setattr(f, "field_id", 30821)),
        ])
        try:
            log: list = []
            out = O.drive(g, pred, "S", log, deadline=time.time() + 90,
                          floor_for=lambda d: _flat_bgi(), prior_for=lambda d: _prior())
        finally:
            stop.set()
    assert out["end"] == "reached", out
    assert out["beats"] == {"candle": True, "named": True, "battle": 1, "garnet": True}, out["beats"]
    assert fake.named == [0] and fake.answered == [0, 1], (fake.named, fake.answered)
    assert [c["index"] for c in out["choices"]] == [0, 1], out["choices"]
    assert out["pages"][0].startswith("Zidane") and any("Who's there" in p for p in out["pages"]), out["pages"]
    assert not fake._tutorial and len(fake.battle_commands) >= 4
    assert [x["k"] for x in log] == ["overlay", "candle", "choice", "named", "battle", "choice", "end"], log
    assert log[1]["opened"] and hint not in out["pages"], (log[1], out["pages"])


def test_route_to_walks_under_an_overlay_hint_only_when_told(game):
    """An async hint window over free movement (Prima Vista 50's "Press the X button when the ? appears."): by
    default route_to's wait for settled control reads it as the scene still owning him and waits out its timeout
    (the control); ``overlay_ok=True`` walks."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        fake.say("\nPress the  button when the ? appears.")
        published(g, lambda s: s.dialog_open and s.control)
        with pytest.raises(HarnessError, match="control to return"):
            g.route_to(300.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), timeout=2.0)
        rec = g.route_to(300.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), timeout=20.0, overlay_ok=True)
        assert rec["reached"], rec
        assert g.state.dialog_open, "the hint is the script's to close, not the walk's"


def test_o1_end_run_leaves_the_end_field_by_warp_before_the_reset(game):
    """Session story-o1d: the soft reset did not reach the title from field 100 (Alexandria's opening playing). The
    control: the ladder where he stands fails; end_run warps to the recovery field first, and resets from there."""
    O, _pred = _o1_pred()
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30821)                                         # "100": no reset reaches the title from here
        real = g.restore_baseline

        def ladder():
            return real() if g.state.field_id == 30820 else (False, "the soft reset did not reach the title")
        g.restore_baseline = ladder
        assert not g.restore_baseline()[0], "premise: the ladder fails where the run ended"
        log: list = []
        O.end_run(g, log, recovery=30820)
        assert log[0] == {"k": "recover-warp", "field": 30820} and g.state.ui_state == "Title", (log, g.state)


def test_o1_drive_voids_a_choice_it_has_no_rule_for(game):
    O, pred = _o1_pred()
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        fake.scene({"header": "Well?", "options": ["Sword", "Dagger"], "default": 1})
        with pytest.raises(O.RouteVoid, match="no rule"):
            O.drive(g, pred, "S", [], deadline=time.time() + 30,
                    floor_for=lambda d: _flat_bgi(), prior_for=lambda d: _prior())
    assert fake.answered == []


def test_o1_drive_voids_control_where_the_route_never_gives_it(game):
    """Control held anywhere but the start field before the candle is not the route's: VOID, never a walk."""
    O, pred = _o1_pred(candle={"donor": 30821, "x": 300.0, "z": 0.0})
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        with pytest.raises(O.RouteVoid, match="control held in 30820"):
            O.drive(g, pred, "S", [], deadline=time.time() + 30,
                    floor_for=lambda d: _flat_bgi(), prior_for=lambda d: _prior())


def test_o1_pick_for_reads_the_frozen_rules_by_option_text():
    """52's question lists "Queen Brahne" first (the script's default, which loops): the rule picks the Garnet line by
    its text, at its ABSOLUTE index; "Skip movie?" takes the game's default; an ambiguous rule is VOID."""
    O, pred = _o1_pred()
    q = {"options": ["Who?", "Queen Brahne", "Princess Garnet"], "active": [0, 1]}
    assert O.pick_for(q, 30820, pred)[0] == 1
    masked = {"options": ["Who?", "Princess Garnet"], "active": [1]}               # line 0 masked out
    assert O.pick_for(masked, 30820, pred)[0] == 1
    # as the agent PUBLISHES them (story-o1b run 1): the line after [CHOO][MOVE=18,0] loses its first character
    candle = {"options": ["", "ight the candle", "Cancel"], "active": [0, 1]}
    assert O.pick_for(candle, 50, O.draft_predictions())[0] == 0
    kidnap = {"options": ["\n“Okay!”\n", "hat’s when I kidnap Queen Brahne, right?",
                          "That’s when I kidnap Princess Garnet, right?"], "active": [0, 1]}
    assert O.pick_for(kidnap, 52, O.draft_predictions())[0] == 1
    skip = {"options": ["Do you want to skip\nthe movie?", "Yes", "No"], "active": [0, 1]}     # SkipMovieDialog, US
    assert O.pick_for(skip, 999, pred)[0] == "default"
    with pytest.raises(O.RouteVoid, match="2 lines"):
        O.pick_for({"options": ["Who?", "Garnet", "Garnet"], "active": [0, 1]}, 30820, pred)
    with pytest.raises(O.RouteVoid, match="no rule"):
        O.pick_for(q, 31999, pred)                    # the Garnet rule is bound to its field


# ---- O2's shared segment machinery (studies/story-trace/segment_drive.py, segment_trace.py; research/o2_design.md
# sections 1 and 9, PART A). O1 runs on the same machinery, so every O1 test above is part of this set's gate.

def _segment_modules():
    sys.path.insert(0, str(REPO / "studies" / "story-trace"))
    import segment_drive as SD
    return SD


def test_o2_pick_for_scopes_rules_by_sc_and_once():
    """O2's rule keys (research/o2_design.md 1.4, 2.6), each optional: ``sc`` scopes a rule to the published
    scenario (215 re-offered at SC 1150 has no rule), ``once`` refuses a second answer (V2), ``take: "default"``
    refuses a pick that is not the game's own ready cursor (V3). A rule without them reads as O1's did, and a
    RouteVoid raised as O1 raises one carries no class."""
    SD = _segment_modules()
    rules = [{"donor": 103, "sc": [1000], "match": "ticket booth", "pick": "ticket booth", "once": True,
              "beat": "booth", "take": "default"},
             {"donor": 105, "sc": [1151], "match": "want to", "pick": "right", "once": True, "beat": "alright",
              "take": "default"},
             {"donor": None, "sc": None, "match": "want to skip", "pick": "default", "once": False, "beat": None}]
    pred = {"choices": rules}
    # 215 as the agent publishes it: no prompt line, and the first option's first character dropped
    booth = {"options": ["", "eek into the ticket booth", "Cancel"], "active": [0, 1], "selected": 0}
    assert SD.pick_for(booth, 103, pred, sc=1000) == (0, rules[0])
    with pytest.raises(SD.RouteVoid, match="no rule") as e:          # the second visit: SC 1150
        SD.pick_for(booth, 103, pred, sc=1150)
    assert (e.value.v, e.value.cell, e.value.by) == (None, None, None)
    with pytest.raises(SD.RouteVoid, match="no rule"):               # a call that publishes no scenario
        SD.pick_for(booth, 103, pred)
    with pytest.raises(SD.RouteVoid, match="answers once") as e:
        SD.pick_for(booth, 103, pred, sc=1000, answered={0})
    assert (e.value.v, e.value.cell, e.value.by) == ("V2", [103, 1000], "game")
    assert SD.pick_for(booth, 103, pred, sc=1000, answered={1})[0] == 0          # another rule's answer
    with pytest.raises(SD.RouteVoid, match="not the game's default") as e:
        SD.pick_for(dict(booth, selected=1), 103, pred, sc=1000)
    assert (e.value.v, e.value.cell, e.value.by) == ("V3", [103, 1000], "game")
    # 310: the rule matches on the SECOND line and picks the first, the cursor's
    alright = {"options": ["", "Alright", "N-No, I don’t want to"], "active": [0, 1], "selected": 0}
    assert SD.pick_for(alright, 105, pred, sc=1151) == (0, rules[1])
    # an sc-free, donor-free rule: any SC, and O1's call without one
    skip = {"options": ["Do you want to skip\nthe movie?", "Yes", "No"], "active": [0, 1], "selected": 1}
    assert SD.pick_for(skip, 999, pred, sc=1234)[0] == "default" and SD.pick_for(skip, 999, pred)[0] == "default"
    # O1 reads the same objects through its re-export
    O, o1 = _o1_pred()
    assert O.pick_for is SD.pick_for and O.RouteVoid is SD.RouteVoid
    assert O.pick_for({"options": ["Who?", "Queen Brahne", "Princess Garnet"], "active": [0, 1]}, 30820, o1)[0] == 1
    err = SD.RouteVoid("plain")
    assert str(err) == "plain" and (err.v, err.cell, err.by) == (None, None, None)


def _segment_trace():
    sys.path.insert(0, str(REPO / "studies" / "story-trace"))
    import segment_trace as ST
    return ST


#: Hippaul's :=2 (103 e18 t1 ip254), O2's one full-key noise pattern (research/o2_design.md 4.6)
_ST_HIPPAUL = {"donor": 103, "m": 1, "src": "eb", "sid": 18, "tag": 1, "off": 51, "target": "Global.Byte[472]",
               "value": 2, "ip": 254, "op": ":=", "why": "Hippaul's :=2 never propagates"}


def _st_w(fld, byte, old, new, *, width="Byte", sid=0, tag=0, ip=6, don=None, bit=-1):
    return {"k": "w", "f": 10, "p": 0, "m": 1, "fld": fld, "don": fld if don is None else don, "sc": 0, "src": "eb",
            "sid": sid, "uid": sid, "lvl": 0, "ip": ip, "tag": tag, "add": 0, "byte": byte, "w": width, "bit": bit,
            "old": old, "new": new, "same": int(old == new)}


def _st_e(why, fld=70):
    return {"k": "e", "f": 0, "p": 0, "m": 1, "fld": fld, "don": fld, "sc": 0, "why": why}


def _st_r(fld, byte, old, new):
    return {"k": "r", "f": 0, "p": 0, "m": 1, "fld": fld, "don": fld, "sc": 0, "byte": byte, "old": old, "new": new,
            "why": "frame"}


def _st_c(w, n, last):
    """The count row the engine closes ``w``'s site with (its fld/don/m are the site's)."""
    return {"k": "c", "f": 0, "p": 0, "sc": 0, **{k: w[k] for k in ("fld", "don", "m", "src", "sid", "tag", "ip",
                                                                    "byte", "w", "bit")}, "n": n, "last": last}


def _st_rows(*rows):
    from ff9mapkit import storytrace as T
    return T.parse_text("".join(json.dumps(r) + "\n" for r in rows))


def test_key_matches_refuses_unknown_fields():
    """A full-key noise pattern (research/o2_design.md 4.6) names EXACTLY the eight WriteKey fields, plus the
    metadata ip/op/why. A typo (``offset``), a missing field, an operator (a list, a range) or a value of the wrong
    type raises -- never a silently wider (or dead) match. It matches only the aligned key equal in all eight."""
    import dataclasses
    from ff9mapkit.storytrace import WriteKey
    ST = _segment_trace()
    k = WriteKey(103, 1, "eb", 18, 1, 51, "Global.Byte[472]", 2)
    assert ST.key_matches(k, _ST_HIPPAUL)
    assert ST.key_matches(k, {f: _ST_HIPPAUL[f] for f in ST.KEY_FIELDS})       # the metadata is the checks', not ours
    assert not ST.key_matches(dataclasses.replace(k, aligned=False), _ST_HIPPAUL)
    for field, other in (("donor", 104), ("m", 2), ("src", "cs"), ("sid", 19), ("tag", 2), ("off", 15),
                         ("target", "Global.Byte[473]"), ("value", 3)):
        assert not ST.key_matches(dataclasses.replace(k, **{field: other}), _ST_HIPPAUL), field
    typo = {**{f: v for f, v in _ST_HIPPAUL.items() if f != "off"}, "offset": 51}
    for bad, match in ((typo, r"unknown field\(s\) \['offset'\]"),
                       ({f: v for f, v in _ST_HIPPAUL.items() if f != "value"}, r"missing \['value'\]"),
                       ({**_ST_HIPPAUL, "ip_range": [0, 300]}, "unknown field"),
                       ({**_ST_HIPPAUL, "value": [2, 3]}, "not a plain int"),
                       ({**_ST_HIPPAUL, "m": True}, "not a plain int"),
                       ({**_ST_HIPPAUL, "off": "51"}, "not a plain int")):
        with pytest.raises(ValueError, match=match):
            ST.key_matches(k, bad)


def test_is_noise_keeps_o1s_legacy_form():
    """O1's registered noise is ``{not_m, target, why}``: every key of that target whose mode is NOT ``not_m`` (scene
    336's AI). A FIELD-mode key of the same byte is not noise -- the O1 gate's G6 mutant, as a unit. The full-key form
    matches its one key; a pattern of neither shape raises, even when another pattern matched first."""
    import dataclasses
    from ff9mapkit.storytrace import WriteKey
    ST = _segment_trace()
    O, o1 = _o1_pred()
    assert O.is_noise is ST.is_noise
    battle = WriteKey(50, 2, "eb", 1, -1, 900, "Global.Byte[206]", 17)
    assert ST.is_noise(battle, o1) and ST.is_noise(dataclasses.replace(battle, target="Global.Byte[199]"), o1)
    assert not ST.is_noise(dataclasses.replace(battle, m=1), o1)                  # field mode: O1's noise is m != 1
    assert not ST.is_noise(dataclasses.replace(battle, target="Global.Byte[205]"), o1)
    both = {"noise": [*o1["noise"], _ST_HIPPAUL]}
    hippaul = WriteKey(103, 1, "eb", 18, 1, 51, "Global.Byte[472]", 2)
    assert ST.is_noise(battle, both) and ST.is_noise(hippaul, both)
    assert not ST.is_noise(dataclasses.replace(hippaul, off=15), both)            # Hippaul's :=1 site is story
    with pytest.raises(ValueError):
        ST.is_noise(battle, {"noise": [*o1["noise"], {"target": "Global.Byte[206]", "why": "no mode rule"}]})


def test_cut_at_start_keeps_residue_out_of_the_kept_rows():
    """The front cut (research/o2_design.md 5.2): the run starts at its first ``w`` row in the start PLACE. The warp's
    residue in field 70, a stray field-70 write and that write's closing count are cut into ``pre``; the epochs stay;
    residue AFTER the start stays among the kept rows (O2-RESIDUE judges it). On the fork side the place is the
    member's frozen donor."""
    ST = _segment_trace()
    w70 = _st_w(70, 13, 0, 2, sid=3, ip=40)
    start = _st_w(100, 23, 1, 0, width="Bit", bit=191, sid=0, ip=36)
    sc = _st_w(100, 0, 1000, 1150, width="UInt16", sid=7, tag=1, ip=1046)
    rows = _st_rows(_st_e("arm"), _st_r(70, 0, 0, 232), _st_r(70, 1, 0, 3), _st_r(70, 2, 0, 102), w70, start, sc,
                    _st_r(100, 5, 0, 9), _st_c(w70, 2, 2), _st_c(sc, 1, 1150), _st_e("off", 100))
    kept, at, pre = ST.cut_at_start(rows, 100, {})
    assert at == 6, at
    assert [r.line for r in pre] == [2, 3, 4, 5, 9], [(r.line, r.k) for r in pre]
    assert [r.line for r in kept] == [1, 6, 7, 8, 10, 11], [(r.line, r.k) for r in kept]
    assert [(r.byte, r.old, r.new) for r in pre if r.k == "r"] == [(0, 0, 232), (1, 0, 3), (2, 0, 102)]
    fork = _st_rows(*[dict(r, fld=31220) if r["fld"] == 100 else r for r in (
        _st_e("arm"), _st_r(70, 0, 0, 232), start, sc, _st_e("off", 100))])
    kept, at, pre = ST.cut_at_start(fork, 100, {31220: 100})
    assert at == 3 and [r.line for r in pre] == [2] and [r.line for r in kept] == [1, 3, 4, 5]
    assert ST.cut_at_start(fork, 100, {})[1] is None             # without the members, 31220 is no place 100


def test_cut_at_start_needs_a_w_row_in_the_start_place():
    """Only a ``w`` row starts the run: residue landing in the start field before any store there is ``pre``, never
    the start (it would hide itself among the kept rows). A run with no ``w`` row in the start place is not cut at
    all, and says so with ``at`` None -- the analysis's "never reached the start field"."""
    ST = _segment_trace()
    rows = _st_rows(_st_e("arm"), _st_r(70, 0, 0, 232), _st_r(100, 1, 0, 3), _st_w(70, 13, 0, 2), _st_e("off"))
    kept, at, pre = ST.cut_at_start(rows, 100, {})
    assert (at, pre) == (None, []) and kept == rows
    rows = _st_rows(_st_e("arm"), _st_r(100, 1, 0, 3), _st_w(100, 23, 1, 0, width="Bit", bit=191), _st_e("off"))
    kept, at, pre = ST.cut_at_start(rows, 100, {})
    assert at == 3 and [(r.line, r.k) for r in pre] == [(2, "r")] and [r.line for r in kept] == [1, 3, 4]


def test_cut_at_end_judges_frozen_places():
    """The end cut on FROZEN places (research/o2_design.md 5.2): the run ends at its first ``w``/``r`` row whose
    place is an end place; after it only the epochs and the closing counts of sites outside the end places stay. A
    member whose donor is an end place ends the run as the real field does. O1's wrapper is this with no members
    (its end field 100 is no member's donor)."""
    ST = _segment_trace()
    O, _o1 = _o1_pred()
    roof = _st_w(31236, 6, 0, 2, sid=2, tag=1, ip=765)
    real61 = _st_w(61, 23, 1, 0, width="Bit", bit=191)
    rows = _st_rows(_st_e("arm"), roof, real61, _st_w(61, 13, 0, 3, ip=22), _st_c(roof, 1, 2), _st_c(real61, 1, 0),
                    _st_e("off", 61))
    kept, at = ST.cut_at_end(rows, [61], {31236: 116})
    assert at == 3 and [r.line for r in kept] == [1, 2, 5, 7], [(r.line, r.k) for r in kept]
    assert O.cut_at_end(rows, 61) == ST.cut_at_end(rows, [61], {})
    member = _st_rows(_st_e("arm"), _st_w(31220, 8, 0, 125), _st_e("off", 31220))
    assert ST.cut_at_end(member, [100], {31220: 100})[1] == 2 and ST.cut_at_end(member, [100], {})[1] is None


def _st_eb(*entries) -> bytes:
    """A .eb whose entries are ``[(tag, eb-src text), ...]``, assembled by the kit (as tests/test_storytrace.py)."""
    import struct
    from ff9mapkit.eb import cmdasm
    from ff9mapkit.eb.model import pack_entry
    bodies = [pack_entry(0, [(t, cmdasm.assemble_block(src)) for t, src in funcs]) for funcs in entries]
    head = bytearray(0x80)
    head[0:2], head[2], head[3] = b"EV", 2, len(entries)
    table, pos = b"", len(entries) * 8
    for body in bodies:
        table += struct.pack("<HHBBH", pos, len(body), 0, 0, 0)
        pos += len(body)
    return bytes(head) + table + b"".join(bodies)


def test_row_keys_maps_every_joined_row_to_its_digest_key():
    """``row_keys`` (research/o2_design.md 5.3): every row the digest keyed maps, by (site, value), to the digest's
    own JOINED key -- the donor through the frozen members, ``off`` the function offset -- keys and seam keys alike;
    a counter site gives one key per value, a count row its suppressed ``last``. A row the digest did not key (a join
    failure, a masked site) has no entry."""
    from ff9mapkit import storytrace as T
    from ff9mapkit.eb import EbScript
    ST = _segment_trace()
    main = ("SET({Global.UInt16[0] const(1150) B_LET B_EXPR_END})\n"          # +0
            "SET({Global.Byte[303] B_POST_PLUS B_EXPR_END})\n"                 # +8
            "SET({Global.Bit[191] const(0) B_LET B_EXPR_END})\n"               # +14 (masked: boot_scratch)
            "SET({Global.Int16[2] const(200) B_LET B_EXPR_END})\nRET()")       # +22
    donor = _st_eb([(0, main)])
    entry = EbScript.from_bytes(donor).entries[0]
    ip0 = entry.func_by_tag(0).abs_start - entry.abs_start                      # the engine's ip of +0
    stock = {100: T.ScriptIndex(donor, field_id=100), 61: T.ScriptIndex(donor, field_id=61)}.get
    fork = T.mod_script_source([], fallback=stock, explicit={31220: donor})

    def run(fld):
        ctr = [_st_w(fld, 303, v, v + 1, ip=ip0 + 8, don=100) for v in (0, 1)]
        return _st_rows(_st_e("arm"),
                        _st_w(fld, 0, 1000, 1150, width="UInt16", ip=ip0, don=100),           # line 2
                        *ctr,                                                                  # 3, 4: one site
                        _st_w(fld, 23, 1, 0, width="Bit", bit=191, ip=ip0 + 14, don=100),     # 5: masked
                        _st_w(fld, 2, 102, 200, width="Int16", ip=ip0 + 23, don=100),         # 6: one byte off
                        _st_w(fld, 2, 102, 200, width="Int16", ip=ip0 + 22, don=100),         # 7: the exit
                        _st_w(61, 2, 200, 200, width="Int16", ip=ip0 + 22),                   # 8: real 61
                        _st_c(ctr[0], 3, 5),                                                   # 9: the count
                        _st_e("off", 61))
    s, f = run(100), run(31220)
    ds = T.digest("S#1", s, scripts=stock)
    df = T.digest("F#2", f, scripts=fork, donor_scripts=stock, members={31220: 100})
    for rows, d, n_seam in ((s, ds, 0), (f, df, 1)):
        rk = ST.row_keys(d)
        assert len(rk) == len(d.keys) + len(d.seam_keys) and len(d.seam_keys) == n_seam, (rk, d.seam_keys)
        got = {r.line: ST.key_of(rk, r) for r in rows if r.k in ("w", "c")}
        assert {line: (k.donor, k.off, k.target, k.value) for line, k in got.items() if k is not None} == {
            2: (100, 0, "Global.UInt16[0]", 1150), 3: (100, 8, "Global.Byte[303]", 1),
            4: (100, 8, "Global.Byte[303]", 2), 7: (100, 22, "Global.Int16[2]", 200),
            8: (61, 22, "Global.Int16[2]", 200), 9: (100, 8, "Global.Byte[303]", 5)}
        assert got[5] is None and got[6] is None                  # masked; one byte off a real store (a failure)
        assert (got[8] in d.seam_keys) == bool(n_seam) and got[7] in d.keys
        assert len(d.failures) == 1 and d.failures[0][0].line == 6


def _stub_segment(game, *, cue, order=("S", "F", "S", "F", "S", "F"), min_covered=2, rerun=None, beats_of=None,
                  void=("V8", [106, 1152], "game"), **over):
    """A Segment with its install stubbed -- no mod roots, a fixed fingerprint, an all-pass preflight, no stock
    scripts -- whose drive pokes one harness byte (so every run's trace holds a row of its own) and then reaches the
    end, or VOIDs with a class, on ``cue(n, side)``: the session loop alone, on the fake. A VOID run raises ``void``
    (its class, cell and attribution); a reached run's outcome carries ``beats_of(n, side)`` (default
    ``{"reached": True}``); ``rerun`` is the predictions' (default ``{"max": 2}``); ``over`` replaces other keys."""
    ST, SD = _segment_trace(), _segment_modules()
    pred = {"version": 1, "what": "a stub segment", "order": list(order), "min_covered": min_covered,
            "rerun": dict(rerun or {"max": 2}), "budget": {"run_s": 60, "run_min_s": 1, "session_s": 600,
                                                           "settle_s": 0.1},
            "start": {"S": 30820, "F": 30820}, "entrance": 0, "end_field": 30821, "stock_fields": [],
            "members": {}, "names": {}, "beats": ["reached"], "noise": [], **over}
    path = game / "zz_predictions.json"
    path.write_text(json.dumps(pred, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    calls: list = []

    class Stub(ST.Segment):
        tag = "ZZ"
        predictions = path
        session_file, report_file = "zz_session.json", "zz_report.txt"
        recovery = 30821

        def roots(self):
            return []

        def preflight(self, pred, roots, build=None, manifest=None):
            return [(True, "P-STUB: the stub's install", "stub")]

        def fingerprint(self, roots, pred):
            return {"stub": 1}

        def stock_source(self):
            return lambda fid: None

        def drive(self, g, pred, side, log, *, deadline, progress=None):
            n = len(calls)
            calls.append(side)
            g.send(f"byte 300 {n + 1}")
            log.append({"k": "stub", "n": n})
            if cue(n, side) == "void":
                v, cell, by = void
                raise SD.RouteVoid(f"stub: no SC 1153 in run {n + 1}", v=v, cell=cell, by=by)
            return {"end": "reached", "why": "field 30821",
                    "beats": beats_of(n, side) if beats_of else {"reached": True}, "pages": ["p"], "choices": [],
                    "t": 0.1}
    return Stub(), pred, calls


def test_segment_session_loop_on_the_fake(game, capsys):
    """Segment.run (research/o2_design.md 1.2, O1's session loop) on the fake: S F S F S F; the F side VOIDs twice,
    with a class, so it is short of min_covered and re-runs (F, once); every run's trace and log land as it ends, the
    record carries the VOID's class, the session is marked finished, and the report and the THROW check follow."""
    from ff9mapkit import storytrace as T
    stub, pred, calls = _stub_segment(game, cue=lambda n, side: "void" if n in (1, 3) else "reached")
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        assert g.restore_baseline()[0], "the session starts at the title, as a launch does"
        stub.run(g)
        checks = list(g.checks)
    run_dir = game / "run"
    sess = json.loads((run_dir / "zz_session.json").read_text(encoding="utf-8"))
    recs = sess["runs"]
    assert [(r["i"], r["side"], r["end"]) for r in recs] == [
        (1, "S", "reached"), (2, "F", "void"), (3, "S", "reached"), (4, "F", "void"), (5, "S", "reached"),
        (6, "F", "reached"), (7, "F", "reached")], recs
    assert calls == ["S", "F", "S", "F", "S", "F", "F"] and recs[6].get("rerun") is True
    assert (recs[1]["v"], recs[1]["cell"], recs[1]["by"]) == ("V8", [106, 1152], "game")
    assert recs[1]["why"] == "route: stub: no SC 1153 in run 2" and not any("v" in r for r in recs if r["end"] != "void")
    for r in recs:
        rows = T.read_trace(run_dir / r["trace"])
        assert r["traced"] == 1 and rows[0].why == "arm" and rows[-1].why == "off", (r, rows)
        assert [(x.src, x.byte, x.new) for x in rows if x.k == "w"] == [("harness", 300, r["i"])]
        log = json.loads((run_dir / r["log"]).read_text(encoding="utf-8"))
        assert log["outcome"]["end"] == r["end"] and {"k": "stub", "n": r["i"] - 1} in log["log"]
    warps = [s for s in fake.executed if s[0] == "warp"]
    assert warps.count(["warp", "30820", "0", "-1"]) == 7 and warps.count(["warp", "30821", "-1", "-1"]) == 6
    assert sess["finished"] and sess["predictions"] == str(game / "zz_predictions.json")
    report = (run_dir / "zz_report.txt").read_text(encoding="utf-8")
    assert report.startswith("ZZ -- run  (predictions v1 ") and "\nVERDICT: PROVEN\n" in report, report[:400]
    whats = [(c["what"], c["ok"]) for c in checks]
    assert whats[:2] == [("P-CAP: the engine advertises the story trace at proto 1", True),
                         ("P-STUB: the stub's install", True)]
    assert ("ZZ-COVER: at least 2 covered runs a side", True) in whats
    assert whats[-1] == ("ZZ-THROW: nothing thrown through the event engine, the evaluator, the tracer or the agent",
                         True)
    out = capsys.readouterr().out
    assert "[zz] run 2 (F) at " in out and ": void -- route: stub: no SC 1153 in run 2" in out
    runs = stub.read_session(run_dir, pred)
    assert runs[1]["void"] == [{"why": "the drive did not reach the end: route: stub: no SC 1153 in run 2",
                                "class": "V8", "by": "game", "cell": [106, 1152]}] and runs[0]["void"] == []


def test_segment_throw_check_fails_on_an_engine_exception(game):
    """THROW never had a mutant (research/o2_design.md C14): the same session loop, with the launch's logs holding a
    NullReferenceException thrown through EventEngine -- the THROW check FAILS and names it. One thrown elsewhere
    (through none of EventEngine/EBin/StoryTrace/HarnessAgent) is not the segment's, and is not named."""
    from harness.logs import LogException
    stub, _pred, _calls = _stub_segment(game, cue=lambda n, side: "reached", order=("S", "F"), min_covered=1)
    thrown = [LogException(log="Memoria.log", type="System.NullReferenceException", message="Object reference",
                           trace=["EventEngine.DoEventCode (EventEngine+EventCodeReturn& ret) [0x00012] in <x>:0"]),
              LogException(log="Memoria.log", type="System.NullReferenceException", message="elsewhere",
                           trace=["BattleHUD.Update () [0x00000] in <x>:0"])]
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        assert g.restore_baseline()[0]
        g.exceptions_since = lambda mark=None: thrown
        stub.run(g)
        throw = [c for c in g.checks if c["what"].startswith("ZZ-THROW")]
    assert len(throw) == 1 and throw[0]["ok"] is False, throw
    assert throw[0]["detail"].count("NullReferenceException") == 1 and "EventEngine" in throw[0]["detail"], throw


def test_segment_read_session_judges_a_registered_battle_by_its_won(game):
    """S1 (research/o3_design.md 1.2): a beat a ``battles`` row registers is done only when the run's record holds
    an INT result in that row's ``won``. A stub session's five reached runs record ``leo`` as 2, 1, 3, None and True
    (the session JSON keeps True a bool): against ``won`` [1, 2] the first two are covered and the other three
    A-BEATS, each naming its result -- a defeat's 3, a None, and True, which equals 1 and is ``in [1, 2]`` but is
    never a battle's result. The same session read with no ``battles`` row (O1's and O2's predictions) keeps today's
    rule: every truthy beat is done, and the A-BEATS text is O1's. Break: drop the ``type(v) is int`` test (run 5
    reads covered)."""
    leo = [2, 1, 3, None, True]
    row = {"donor": 62, "sc": 1155, "scene": 338, "won": [1, 2], "lands": 63, "beat": "leo", "timeout_s": 180,
           "max_turns": 40, "land_s": 30, "land_cap_s": 120, "why": "a stub row"}
    stub, pred, calls = _stub_segment(game, cue=lambda n, side: "reached", order=("S", "F", "S", "F", "S"),
                                      min_covered=1, beats_of=lambda n, side: {"leo": leo[n]}, beats=["leo"],
                                      battles=[row])
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        assert g.restore_baseline()[0]
        stub.run(g)
    run_dir = game / "run"
    sess = json.loads((run_dir / "zz_session.json").read_text(encoding="utf-8"))
    assert [r["beats"] for r in sess["runs"]] == [{"leo": v} for v in leo] and sess["runs"][4]["beats"]["leo"] is True
    assert calls == ["S", "F", "S", "F", "S"]               # each side holds its one covered run: no re-run
    runs = stub.read_session(run_dir, pred)
    assert [r["covered"] for r in runs] == [True, True, False, False, False], [r["void"] for r in runs]
    assert [r["void"] for r in runs[2:]] == [
        [{"why": f"beats not done: ['leo'] (leo result {v!r})", "class": "A-BEATS", "by": "driver"}]
        for v in (3, None, True)]
    legacy = {k: v for k, v in pred.items() if k != "battles"}           # O1's and O2's shape: no registry
    runs = stub.read_session(run_dir, legacy)
    assert [r["covered"] for r in runs] == [True, True, True, False, True]
    assert runs[3]["void"] == [{"why": "beats not done: ['leo'] (battle result None)", "class": "A-BEATS",
                                "by": "driver"}]


def test_segment_rerun_stops_on_a_finding_class(game, tmp_path_factory):
    """S2 (research/o3_design.md 1.2): ``rerun.stop_on`` names FINDING classes. A side with any run VOID in one is
    not re-run however short it is: re-running a finding only repeats it (the s24 leak, V16), and VOID-ASYM already
    reads it. Every F run of a stub session VOIDs with V16 (game): with ``stop_on: ["V16"]`` the session is exactly
    S F S F S F and records ``rerun_held {"F": ["V16"]}``; the control -- the same session without ``stop_on``, O1's
    and O2's shape -- re-runs F twice and records no ``rerun_held``. Break: drop ``s not in held`` (F re-runs)."""
    import shutil
    control = tmp_path_factory.mktemp("control")
    shutil.copytree(game, control, dirs_exist_ok=True)       # a second fake install, as untouched as the first

    def one(root, rerun):
        stub, _pred, calls = _stub_segment(root, cue=lambda n, side: "void" if side == "F" else "reached",
                                           rerun=rerun, void=("V16", [62, 1155], "game"))
        fake = FakeGame(root)
        with session(root, fake) as g:
            boot(g)
            assert g.restore_baseline()[0]
            stub.run(g)
        return calls, json.loads((root / "run" / "zz_session.json").read_text(encoding="utf-8"))

    calls, sess = one(game, {"max": 2, "stop_on": ["V16"]})
    assert calls == ["S", "F", "S", "F", "S", "F"], calls
    assert sess["rerun_held"] == {"F": ["V16"]} and not any(r.get("rerun") for r in sess["runs"]), sess
    assert [(r["v"], r["cell"], r["by"]) for r in sess["runs"] if r["side"] == "F"] == [("V16", [62, 1155], "game")] * 3
    calls, sess = one(control, {"max": 2})
    assert calls == ["S", "F", "S", "F", "S", "F", "F", "F"], calls
    assert "rerun_held" not in sess and [r.get("rerun") for r in sess["runs"][6:]] == [True, True], sess


def _end_run_stub(state, *, field_comes=True, reset_fails=False):
    """A stub session for Segment.end_run: ``state`` is what it publishes; ``warp``/``soft_reset``/``wait_for``/
    ``restore_baseline`` record each call in ``calls``. The warp is refused outside FieldHUD or in a battle (the
    agent's rule: research/o3_design.md 0.2 #9); ``wait_for`` hands over field 63 unless ``field_comes`` is False
    (then it times out); the soft reset reaches the title unless ``reset_fails``."""
    import types
    calls: list = []
    g = types.SimpleNamespace(state=state, calls=calls)

    def warp(field, **kw):
        calls.append(("warp", field))
        if g.state.in_battle or g.state.ui_state != "FieldHUD":
            raise HarnessError("warp refused (not on a field?)")
        return g.state

    def soft_reset(**kw):
        calls.append(("soft_reset",))
        if reset_fails:
            raise HarnessError("the soft reset did not reach the title")
        g.state = types.SimpleNamespace(ui_state="Title", in_battle=False, battle_result=0, battle={}, field_id=-1)
        return g.state

    def wait_for(predicate, *, timeout=20.0, what="condition"):
        calls.append(("wait_for", timeout))
        if not field_comes:
            raise HarnessError(f"timed out after {timeout}s waiting for {what}")
        g.state = types.SimpleNamespace(ui_state="FieldHUD", in_battle=False, battle_result=1, battle={}, field_id=63)
        assert predicate(g.state)
        return g.state

    def restore_baseline():
        calls.append(("restore_baseline",))
        return True, "restored by: soft reset to the title"

    g.warp, g.soft_reset, g.wait_for, g.restore_baseline = warp, soft_reset, wait_for, restore_baseline
    return g


def test_segment_end_run_resets_from_inside_a_battle_without_a_warp():
    """S3 (research/o3_design.md 1.2): a run stopped inside a battle. Mid-fight -- BattleHUD, result 0, the one battle
    state the soft-reset combo fires in -- end_run resets at once: no warp (the agent refuses one there), rows
    ``recover-in-battle`` (scene, ui BattleHUD, result 0) then ``recover-reset``, then the ladder; a reset that fails
    is ``recover-reset-failed``, still the ladder. In the battle's END sequence (BattleHUD with result 2: the fade;
    BattleResult; its load, the scene gone with the UI still BattleResult) there is no soft reset: it waits
    ``battle_end_wait_s`` (120 s) for the field the battle hands
    over, then warps and climbs the ladder (``recover-battle-ending``, ``recover-battle-ended``, ``recover-warp``);
    a field that never comes is ``recover-battle-ending-failed``, then the warp is tried (refused) and the ladder
    climbed. Outside a battle: today's warp and ladder exactly. Break: reset in every battle state (the end
    sequence then resets where the combo is swallowed)."""
    import types
    ST = _segment_trace()
    seg = ST.Segment()
    assert seg.recovery == 4600 and seg.battle_end_wait_s == 120.0

    def battle(ui, result, field):
        return types.SimpleNamespace(ui_state=ui, in_battle=True, battle_result=result,
                                     battle={"scene": 338, "active": True}, field_id=field)

    def end(state, **kw):
        g, log = _end_run_stub(state, **kw), []
        seg.end_run(g, log)
        return g.calls, log

    calls, log = end(battle("BattleHUD", 0, 62))                         # mid-fight
    assert calls == [("soft_reset",), ("restore_baseline",)], calls
    assert log == [{"k": "recover-in-battle", "scene": 338, "ui": "BattleHUD", "result": 0}, {"k": "recover-reset"}]
    calls, log = end(battle("BattleHUD", 0, 62), reset_fails=True)
    assert calls == [("soft_reset",), ("restore_baseline",)], calls
    assert [x["k"] for x in log] == ["recover-in-battle", "recover-reset-failed"]
    assert "did not reach the title" in log[1]["why"]
    for ui, result, field in (("BattleHUD", 2, 62), ("BattleResult", 1, 63)):  # the fade; BattleResult (a flipped id)
        calls, log = end(battle(ui, result, field))
        assert calls == [("wait_for", 120.0), ("warp", 4600), ("restore_baseline",)], (ui, calls)
        assert log == [{"k": "recover-battle-ending", "scene": 338, "ui": ui, "result": result},
                       {"k": "recover-battle-ended", "field": 63}, {"k": "recover-warp", "field": 4600}], (ui, log)
    # the LOAD (the review, research/o3_design.md 11.7 #8): the scene gone, the UI still reading BattleResult -- the end
    # sequence too, waited out (the warp is refused there and the reset swallowed)
    load = types.SimpleNamespace(ui_state="BattleResult", in_battle=False, battle_result=1,
                                 battle={"scene": 338, "active": False}, field_id=63)
    calls, log = end(load)
    assert calls == [("wait_for", 120.0), ("warp", 4600), ("restore_baseline",)], calls
    assert log == [{"k": "recover-battle-ending", "scene": 338, "ui": "BattleResult", "result": 1},
                   {"k": "recover-battle-ended", "field": 63}, {"k": "recover-warp", "field": 4600}], log
    calls, log = end(battle("BattleResult", 1, 63), field_comes=False)   # the field never comes
    assert calls == [("wait_for", 120.0), ("warp", 4600), ("restore_baseline",)], calls
    assert [x["k"] for x in log] == ["recover-battle-ending", "recover-battle-ending-failed", "recover-warp-failed"]
    assert "timed out after 120.0s" in log[1]["why"] and "warp refused" in log[2]["why"]
    field = types.SimpleNamespace(ui_state="FieldHUD", in_battle=False, battle_result=1, battle={"scene": 338},
                                  field_id=64)                           # outside a battle: today's path
    calls, log = end(field)
    assert calls == [("warp", 4600), ("restore_baseline",)] and log == [{"k": "recover-warp", "field": 4600}]
    title = types.SimpleNamespace(ui_state="Title", in_battle=False, battle_result=0, battle={}, field_id=-1)
    calls, log = end(title)
    assert calls == [("restore_baseline",)] and log == []


def test_segment_session_end_warps_first_when_asked(game, tmp_path_factory):
    """S5 (research/o3_design.md 1.2): a segment that sets ``end_session_warps`` ends its session as every run
    between ends -- ``end_run``: the warp to ``recovery`` first, then the ladder -- and records it in
    ``session["ended"]`` (its rows, ``ok``, ``why``), never raising. The default (O1, O2) keeps today's bare
    ``restore_baseline()`` where the last run stopped, and writes no ``ended``. One stub session each way (S F, the
    second on its own fake install), the session's warp and ladder calls recorded: the last two are
    ``warp(recovery)``, ``restore_baseline`` with the flag, and ``restore_baseline`` twice without. A third session
    whose ``end_run`` raises at the end records ``ok`` False with the error and still writes its report. Break:
    ignore the flag (the bare ladder ends the session, and nothing is recorded)."""
    import shutil
    control, failing = tmp_path_factory.mktemp("control"), tmp_path_factory.mktemp("failing")
    for root in (control, failing):
        shutil.copytree(game, root, dirs_exist_ok=True)      # more fake installs, as untouched as the first

    def one(root, warps):
        stub, _pred, calls = _stub_segment(root, cue=lambda n, side: "reached", order=("S", "F"), min_covered=1)
        stub.end_session_warps = warps
        seq: list = []
        fake = FakeGame(root)
        with session(root, fake) as g:
            boot(g)
            assert g.restore_baseline()[0]
            real_warp, real_restore = g.warp, g.restore_baseline

            def warp(field, **kw):
                seq.append(("warp", field))
                return real_warp(field, **kw)

            def restore():
                seq.append(("restore_baseline",))
                return real_restore()
            g.warp, g.restore_baseline = warp, restore
            stub.run(g)
            at_title = g.state.ui_state == "Title"
        assert calls == ["S", "F"]
        return seq, json.loads((root / "run" / "zz_session.json").read_text(encoding="utf-8")), at_title

    seq, sess, at_title = one(game, True)
    # run 2's end_run (warp, ladder), then the session's own end through end_run (warp, ladder)
    assert seq == [("warp", 30821), ("restore_baseline",), ("warp", 30821), ("restore_baseline",)], seq
    assert sess["ended"] == {"log": [{"k": "recover-warp", "field": 30821}], "ok": True, "why": ""}, sess.get("ended")
    assert at_title
    seq, sess, at_title = one(control, False)
    assert seq == [("warp", 30821), ("restore_baseline",), ("restore_baseline",)], seq
    assert "ended" not in sess and at_title
    # never raised: one run, no re-run, so the session's end is the only end_run -- and it fails
    stub, _pred, calls = _stub_segment(failing, cue=lambda n, side: "reached", order=("S",), min_covered=1,
                                       rerun={"max": 0})
    stub.end_session_warps = True

    def end_run(g, log, *, recovery=None):
        log.append({"k": "recover-warp-failed", "why": "stub"})
        raise HarnessError("the title could not be restored: stub")
    stub.end_run = end_run
    fake = FakeGame(failing)
    with session(failing, fake) as g:
        boot(g)
        assert g.restore_baseline()[0]
        stub.run(g)
    sess = json.loads((failing / "run" / "zz_session.json").read_text(encoding="utf-8"))
    assert calls == ["S"] and sess["ended"] == {"log": [{"k": "recover-warp-failed", "why": "stub"}], "ok": False,
                                                "why": "the title could not be restored: stub"}, sess.get("ended")
    assert (failing / "run" / "zz_report.txt").is_file()


def test_o1_segment_run_pins_o1s_session_surface(game, capsys):
    """O1Segment.run on the fake (research/o2_design.md 1.6 G7), its install stubbed as the segment tests stub it:
    the refactored session keeps O1's surface -- it sends ``warp 50 0 -1`` and ``warp 31200 0 -1`` (v4 has no
    scenario), writes o1_session.json and o1_report.txt, prints ``[o1] run 1 (S)``, records the v4 predictions it
    loaded, and titles its checks with O1's exact texts."""
    import types
    O, _pred = _o1_pred()
    patch = game / "FF9CustomMap" / "DictionaryPatch.txt"                 # O1's member(50), so the guard lets it warp
    patch.write_text(patch.read_text(encoding="utf-8") + "FieldScene 31200 11 O1_TSHP_A O1_TSHP_A 31200\n",
                     encoding="utf-8")
    blank = _st_eb([(0, "RET()")])
    beats = {"candle": True, "named": True, "battle": 1, "garnet": True}
    seg = O.O1Segment()
    seg.roots = lambda: []
    seg.preflight = lambda pred, roots, build=None, manifest=None: [(True, "P-STUB: the stubbed install", "stub")]
    seg.fingerprint = lambda roots, pred: {"stub": 1}
    seg.scripts_source = lambda roots: (lambda fid: types.SimpleNamespace(data=blank))
    seg.stock_source = lambda: (lambda fid: None)
    seg.recovery = 30821
    seg.drive = lambda g, pred, side, log, *, deadline, progress=None: {
        "end": "reached", "why": "field 100", "beats": dict(beats), "pages": ["p"], "choices": [], "t": 0.1}
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        assert g.restore_baseline()[0]
        seg.run(g)
        whats = [c["what"] for c in g.checks]
    warps = [s for s in fake.executed if s[0] == "warp"]
    assert warps.count(["warp", "50", "0", "-1"]) == 3 and warps.count(["warp", "31200", "0", "-1"]) == 3, warps
    run_dir = game / "run"
    sess = json.loads((run_dir / "o1_session.json").read_text(encoding="utf-8"))
    _v4, sha = O.load_predictions()
    assert sess["predictions"] == str(O.PREDICTIONS) and sess["predictions_sha256"] == sha
    assert [(r["i"], r["side"], r["start"]) for r in sess["runs"]] == [
        (1, "S", 50), (2, "F", 31200), (3, "S", 50), (4, "F", 31200), (5, "S", 50), (6, "F", 31200)]
    assert (run_dir / "o1_report.txt").read_text(encoding="utf-8").startswith(f"O1 -- run  (predictions v4 {sha[:8]})")
    assert "[o1] run 1 (S) at " in capsys.readouterr().out
    assert whats[0] == "P-CAP: the engine advertises the story trace at proto 1"
    for what in ("O1-FROZEN: the predictions are the file the session recorded, unchanged",
                 "O1-COVER: at least 2 covered runs a side",
                 "O1-LADDER: every covered run writes the four ladder keys, and SC exactly once",
                 "O1-NULL: STOCK ONLY and FORK ONLY are empty outside the registered noise",
                 "O1-STABLE: no key outside the registered noise is written in some runs of a side and not others",
                 "O1-JOIN: every script row joins a store in the bytes its field ran"):
        assert what in whats, what
    assert whats[-1] == "O1-THROW: nothing thrown through the event engine, the evaluator, the tracer or the agent"


# ---- O2's harness additions (research/o2_design.md section 3, PART B). H4: the fake's warp writes its entrance and
# scenario (and the trace's residue of them) in the OLD field, models a ladder, walk-in triggers and an arrival that
# keeps control, and publishes watched bits from its gEventGlobal. H1-H3 and H6 are the driver's verbs the beat-table
# driver needs; each is opt-in, so no caller before it changes. Every test here in which a region warps sets
# exit_frames = 50: the fade between ExitField's control loss and the map change is where the exits' race lives.

def test_fake_warp_publishes_the_scenario(game):
    """H4: ``warp <field> <entrance> <scenario>`` is the debug warp's ServicePendingWarp -- the scenario published and
    laid into the modelled gEventGlobal (UInt16 at bytes 0-1), the entrance beside it (Int16 at bytes 2-3). A -1 (the
    Session.warp default) writes nothing: the scenario stands. Break: drop the scenario write (the fake published SC
    0 after ``warp 30821 102 1000``)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        assert g.state.scenario == 0 and bytes(fake.story_bytes[0:4]) == bytes(4)
        st = g.warp(30821, entrance=102, scenario=1000)
        assert st.scenario == 1000 and bytes(fake.story_bytes[0:4]) == bytes((0xE8, 0x03, 102, 0)), st
        st = g.warp(30820)
        assert st.scenario == 1000 and bytes(fake.story_bytes[0:4]) == bytes((0xE8, 0x03, 102, 0)), st
        st = g.warp(30821, entrance=-1, scenario=1150)
        assert st.scenario == 1150 and bytes(fake.story_bytes[0:4]) == bytes((0x7E, 0x04, 102, 0)), st
    assert ["warp", "30821", "102", "1000"] in fake.executed and ["warp", "30820", "-1", "-1"] in fake.executed


def test_fake_warp_writes_its_residue_in_the_old_field(game):
    """H4 (research/o2_design.md 0.2 #13): with the trace on, ``warp 30820 102 1000`` from New Game's field 70 leaves
    exactly three residue rows, stamped with field 70 -- byte 0: 0 -> 232, byte 1: 0 -> 3 (SC 1000 = 0x03E8), byte 2:
    0 -> 102 -- and nothing on byte 3; the first row in the new field comes after them. A warp that changes no byte
    (the same entrance and scenario again, or -1 -1) leaves none. Break: stamp the rows with the NEW field (they
    would read as residue in the start place, which O2-START forbids)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        assert g.state.field_id == 70
        g.storytrace(True)
        g.warp(30820, entrance=102, scenario=1000)
        g.poke(300, 7)                                     # a row in the new field, after the warp
        g.warp(30821, entrance=102, scenario=1000)         # nothing changes: no residue
        g.warp(30820)                                      # -1 -1: nothing written
        rows = g.story_rows()
        g.storytrace(False)
    got = [(r.k, r.fld, r.byte, r.old, r.new) for r in rows if r.k in ("r", "w")]
    assert got == [("r", 70, 0, 0, 232), ("r", 70, 1, 0, 3), ("r", 70, 2, 0, 102), ("w", 30820, 300, 0, 7)], got
    assert all(r.why == "frame" and r.don == 70 for r in rows if r.k == "r"), rows


def test_fake_watched_bits_read_the_story_bytes(game):
    """H4: a watched bit is published from the modelled gEventGlobal, which a script's store, a ``byte`` poke and the
    ``flag`` verb all write -- so the O2 driver's end-state read (research/o2_design.md 2.2, rule 1) sees what the
    scripts wrote. Break: publish the ``flag`` verb's dict (a script's Bit[3717] := 1 then never shows)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g.watch(3717, 3718)
        st = published(g, lambda s: s.flag(3717) is not None)
        assert (st.flag(3717), st.flag(3718)) == (False, False)
        fake.script_store(7, 1, 319, 3717 >> 3, "Bit", 1, bit=3717)       # the Herald's Bit[3717] := 1 (101 e7 t1)
        st = published(g, lambda s: s.flag(3717) is True)
        assert st.flag(3718) is False
        g.poke(3718 >> 3, 1 << (3718 & 7))                 # one byte over both: 3718 set, 3717 cleared
        st = published(g, lambda s: s.flag(3718) is True)
        assert st.flag(3717) is False
        g.flag(3717)
        st = published(g, lambda s: s.flag(3717) is True)
        assert st.flag(3718) is True


class _StampFake(FakeGame):
    """The fake with WALL-CLOCK stamps, for the tests that time a driver against a grant: every executed step as
    ``(time, frame, step)`` in ``stamped``, and a ``t`` on every entry of `fired`. The loop's own pace is ``fps``
    frames a wall second (240), not the 60 fps render clock -- a bound in its frames converts at that."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.stamped: list = []

    def _execute(self, step: list[str]) -> None:
        self.stamped.append((time.time(), self.frame, list(step)))
        super()._execute(step)

    def _enter_regions(self) -> None:
        n = len(self.fired)
        super()._enter_regions()
        for f in self.fired[n:]:
            f["t"] = time.time()


def test_route_cross_handoff_returns_at_the_control_loss(game):
    """H1: a door whose ExitField takes control on the step into it, its field change 50 frames later (the fade), into
    a destination that arrives with control OFF (an arrival scene). With ``handoff`` the crossing returns DURING the
    fade: ``landed`` None, ``handoff`` True, and ``lost`` -- the first state the call read with control gone -- stands
    inside the door, in the old field, before the field changes; nothing raises, and the field then changes into
    the scene. The control: without ``handoff`` the same crossing waits for the destination to become playable and
    raises "never became playable". Break: drop the handoff branch in route_to's landing (the walk waits the landing
    out and raises)."""
    from ff9mapkit.content import doorface, pathfind
    door = _rect(300, -150, 600, 150)
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": door, "to": 30821, "arrive": (0, 0), "arrive_control": False}]}
    fake.exit_frames = 50
    wm = _flat_bgi()
    goal = (380, 0)                                        # 80u inside: the hold ends just past the door's edge
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -300, 0)
        rec = g.route_cross(*goal, zone=door, smooth=True, walkmesh=wm, prior=_prior(), timeout=2.0, handoff=True)
        fired = fake.fired[-1]
        assert rec["landed"] is None and rec["handoff"] is True and rec["during"] == "walk", rec
        lost = rec["lost"]
        assert lost is not None and lost["field"] == 30820 and lost["control"] is False, rec
        assert doorface.region_contains(lost["x"], lost["z"], door), lost
        assert fired["frame"] <= lost["frame"] < fired["frame"] + fake.exit_frames, (fired, lost)
        st = published(g, lambda s: s.field_id == 30821)
        assert not st.control, "the destination keeps control: its arrival scene's to give back"
        # the control: the same crossing, waited out, never becomes playable
        g.warp(30820)
        _stand(g, fake, -300, 0)
        with pytest.raises(HarnessError, match="never became playable"):
            g.route_cross(*goal, zone=door, smooth=True, walkmesh=wm, prior=_prior(), timeout=2.0)
    assert pathfind.poly_gap(goal[0], goal[1], door) < 0 and len(fake.fired) == 2


def test_route_to_handoff_returns_when_a_trigger_takes_control(game):
    """H1: a WALK-IN trigger across the route (the fake's ``take``: its tag 2 takes control, nothing warps). With
    ``handoff`` route_to returns as soon as the walk's step that entered it has settled -- ``during`` "walk",
    ``landed`` None, ``handoff`` True, ``lost`` inside the trigger -- well inside its timeout; the control waits
    the whole timeout for a landing or control that never comes (``landed`` None either way). Break: drop the
    handoff branch (both wait the timeout)."""
    band = _rect(-60, -600, 60, 600)
    fake = _StampFake(game)
    fake.regions = {30820: [{"zone": band, "take": True}]}
    timeout = 4.0
    got = {}
    with session(game, fake) as g:
        boot(g)
        for handoff in (True, False):
            g.warp(30820)
            _stand(g, fake, -400, 0)
            n = len(fake.fired)
            rec = g.route_to(400.0, 0.0, walkmesh=_flat_bgi(), prior=_prior(), timeout=timeout, handoff=handoff)
            back = time.time()
            assert len(fake.fired) == n + 1 and fake.fired[n]["to"] is None, fake.fired
            got[handoff] = (rec, back - fake.fired[n]["t"])
    for handoff, (rec, waited) in got.items():
        assert rec["during"] == "walk" and rec["landed"] is None and rec["handoff"] is handoff, rec
        assert rec["lost"] is not None and -60 <= rec["lost"]["x"] <= 60, rec["lost"]
    assert got[True][1] < timeout / 4, got[True][1]          # returned at the loss
    assert got[False][1] >= timeout, got[False][1]           # waited the timeout out


def test_route_to_settle_zero_walks_on_the_first_control_sample(game):
    """H1: control granted at a known moment, the basis cached (no calibration) and the rate measured: with
    ``settle=0`` the walk's first hold is executed within 0.2 s of the grant -- counted in the fake's own loop frames
    (240 a second), so a loaded machine cannot fail it by being slow; the control (default settle) is not before
    SETTLE's 1.0 s of WALL time, as SETTLE is a wall-clock hold. Break: stop passing ``settle`` to wait_control."""
    fake = _StampFake(game)
    got = {}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -300, 0)
        g._axes[30820] = _prior()
        g.rate(require=True)
        for settle, goal in ((0.0, 300.0), (None, -300.0)):
            fake.control = False
            published(g, lambda s: not s.control)
            grant: dict = {}

            def director():
                time.sleep(0.3)
                grant["frame"], grant["t"] = fake.frame, time.time()
                fake.control = True
            threading.Thread(target=director, daemon=True).start()
            mark = len(fake.stamped)
            rec = g.route_to(goal, 0.0, walkmesh=_flat_bgi(), prior=_prior(), settle=settle, timeout=10.0)
            assert rec["reached"] and rec["lost"] is None, rec
            t, frame, step = next(s for s in fake.stamped[mark:] if s[2][0] == "hold")
            got[settle] = (t - grant["t"], (frame - grant["frame"]) / fake.fps)
    assert got[0.0][1] <= 0.2, got
    assert got[None][0] >= g.SETTLE, got


def test_route_cross_walks_under_an_overlay_only_when_told(game):
    """H1: O1's overlay rule on route_cross. An async hint up WITH control (106's "Over here!", [TIME=45]): by default
    route_cross's opening wait reads it as the scene still owning him and times out; ``overlay_ok=True`` walks
    through the door (its fade included) and the hint stays the script's to close. Break: stop passing
    ``overlay_ok`` on to route_to."""
    door = _rect(300, -150, 600, 150)
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": door, "to": 30821, "arrive": (0, 0)}]}
    fake.exit_frames = 50
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, -300, 0)
        fake.say("Puck\n“Over here!”")
        published(g, lambda s: s.dialog_open and s.control)
        with pytest.raises(HarnessError, match="control to return"):
            g.route_cross(450.0, 0.0, zone=door, smooth=True, walkmesh=_flat_bgi(), prior=_prior(), timeout=2.0)
        assert not fake.fired
        rec = g.route_cross(450.0, 0.0, zone=door, smooth=True, walkmesh=_flat_bgi(), prior=_prior(), timeout=20.0,
                            overlay_ok=True)
        assert rec["landed"] == 30821 and [f["to"] for f in fake.fired] == [30821], rec
        assert g.state.dialog_open, "the hint is the script's to close, not the walk's"


def _ladder(fake, *, step=20.0, y=200.0):
    """Put him on 115's ladder as its Confirm does (e15 t3: DisableMove, then the climb loop): control off, climbing,
    at ``y`` -- the published y RISES up this ladder, bottom 0 to top 2691 (measured: stock rehearsal o2-rh-115, all
    three runs), ``step`` a field tick of Up (0: a ladder Up does not climb)."""
    fake.ladder = {"top": 2691.0, "bottom": 0.0, "step": float(step)}
    fake.player[1] = float(y)
    fake.control = False
    fake.climbing = True


def test_climb_holds_up_until_the_page_and_nothing_else(game):
    """H2: on the ladder (control off: the climb runs without it) ``climb`` holds Up in bursts -- a hold and a wait in
    one request each, and nothing else ever held or pressed (Down and Right DESCEND) -- and y rises with every burst
    until the top, where the scene opens its page (384): ended "until". Break: hold Right as well."""
    fake = FakeGame(game)
    stop = threading.Event()
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _ladder(fake)
        published(g, lambda s: not s.control)
        _o1_director(fake, stop, [(lambda f: f.climbed, lambda f: f.say("Vivi\n“...!”"))])
        mark = len(fake.executed)
        try:
            rec = g.climb(until=lambda s: s.dialog_open and not s.control)
        finally:
            stop.set()
        steps = fake.executed[mark:]
    assert rec["ended"] == "until" and fake.climbed and rec["y1"] > 2691, rec
    ys = [rec["y0"], *rec["ys"]]
    assert all(b >= a for a, b in zip(ys, ys[1:])), ys
    assert all(b > a for a, b in zip(ys, ys[1:]) if a < 2691), ys           # every burst below the top climbed
    assert rec["frames"] == 30 * rec["bursts"] == 30 * len(rec["ys"]), rec
    pressed = [s for s in steps if s[0] in ("hold", "press", "release", "turn")]
    assert pressed and all(s == ["hold", "up", "30"] for s in pressed), steps
    assert [s for s in steps if s[0] == "wait"] == [["wait", "32"]] * rec["bursts"], steps


def test_climb_says_stalled_when_up_moves_nothing(game):
    """H2: a DEAF ladder -- Up moves y by nothing (the input path not reaching B_KEY(16), freeze item F1): three bursts
    in a row that moved him under 1u end the climb "stalled", counted from the first burst -- never the burst
    budget. Break: never call a climb stalled (it runs to its budget: "bursts")."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _ladder(fake, step=0.0)
        published(g, lambda s: not s.control)
        rec = g.climb(until=lambda s: False, max_bursts=10)
    assert rec["ended"] == "stalled" and rec["bursts"] == 3 and rec["ys"] == [200.0] * 3, rec


def test_climb_says_control_when_he_slides_back(game):
    """H2: mid-climb the director drops him to the bottom -- a slide, whose EnableMove gives control back: the climb
    ends "control" at once, at the bottom. Break: drop the control check (it holds Up on with control held -- a walk
    across the floor, no longer a climb -- until it stalls)."""
    fake = FakeGame(game)
    stop = threading.Event()

    def slide(f):
        f.climbing, f.control = False, True
        f.player[1] = 0.0
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _ladder(fake)
        published(g, lambda s: not s.control)
        _o1_director(fake, stop, [(lambda f: f.player[1] > 700.0, slide)])
        try:
            rec = g.climb(until=lambda s: False, max_bursts=10)
        finally:
            stop.set()
    assert rec["ended"] == "control" and rec["y1"] == 0.0 and rec["bursts"] <= 3, rec


def test_climb_not_started_when_control_stays(game):
    """H2: a Confirm that started no climb leaves control held: after ``start_timeout`` the climb ends "not-started"
    and nothing was pressed. Break: skip the wait for control to go (it holds Up with control: a walk)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        mark = len(fake.executed)
        rec = g.climb(until=lambda s: False, start_timeout=1.0, max_bursts=10)
        steps = fake.executed[mark:]
    assert rec["ended"] == "not-started" and rec["bursts"] == 0 and rec["ys"] == [], rec
    assert not steps, steps


def test_lunge_holds_toward_the_goal_on_the_first_sample(game):
    """H3: control comes back at a known moment on a field whose basis is cached. ``lunge`` acts on its first sample:
    ONE state read, then ONE request carrying the pad's holds and the wait -- executed within 0.1 s of the grant
    (counted in the fake's loop frames, 240 a second). Its pad is the eight-way one nearest the bearing (up+right
    toward (1000, 600)), and it carries him toward the goal. Break: settle before the press."""
    fake = _StampFake(game, walkmesh=(-2000.0, -2000.0, 2000.0, 2000.0))
    wm = _flat_bgi(-2000, -2000, 2000, 2000)
    reads: list = []
    sent_after: list = []
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        _stand(g, fake, 0, 0)
        g._axes[30820] = _prior()
        g.rate(require=True)
        fake.control = False
        published(g, lambda s: not s.control)
        grant: dict = {}

        def director():
            time.sleep(0.3)
            grant["frame"] = fake.frame
            fake.control = True
        threading.Thread(target=director, daemon=True).start()
        published(g, lambda s: s.control, timeout=5.0)
        real_state, real_send = g.channel.state, g.send
        g.channel.state = lambda *a, **kw: (reads.append(1), real_state(*a, **kw))[1]
        g.send = lambda *steps, **kw: (sent_after.append(len(reads)), real_send(*steps, **kw))[1]
        mark = len(fake.stamped)
        try:
            rec = g.lunge(1000.0, 600.0, walkmesh=wm)
        finally:
            g.channel.state, g.send = real_state, real_send
        steps = fake.stamped[mark:]
    assert rec["pressed"] and rec["pad"] == "up+right" and rec["frames"] >= 1, rec
    assert sent_after == [1], sent_after                    # one read before the one request
    lunge = [s for s in steps if s[2][0] in ("hold", "wait")]
    assert [s[2][0] for s in lunge] == ["hold", "hold", "wait"] and len({s[1] for s in lunge}) == 1, lunge
    assert {s[2][1] for s in lunge[:2]} == {"up", "right"} and lunge[2][2] == ["wait", str(rec["frames"] + 2)], lunge
    assert (lunge[0][1] - grant["frame"]) / fake.fps <= 0.1, (lunge[0], grant)
    to = rec["to"]
    assert to[0] > 0 and to[1] > 0 and math.dist(to, (1000, 600)) < math.dist((0, 0), (1000, 600)), rec
    assert rec["sample_frame"] < rec["done_frame"] and rec["travelled"] > 0, rec


def test_lunge_stops_short_of_an_avoid_zone(game):
    """H3: a zone 300u ahead on the line: the hold is clipped to the longest whose whole line -- to the measured
    rate's REACH, tail included -- stays the margin clear of it, and he ends outside the margin. With nothing to
    avoid the same lunge holds its full ticks; with the zone 40u ahead no hold sure of a tick keeps it, and nothing
    is pressed. Break: judge the line at the average speed (the hold runs on into the margin)."""
    from ff9mapkit.content import pathfind
    zone = _rect(300, -200, 500, 200)
    near = _rect(40, -200, 240, 200)
    wm = _flat_bgi(-2000, -2000, 2000, 2000)
    fake = FakeGame(game, walkmesh=(-2000.0, -2000.0, 2000.0, 2000.0))
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g._axes[30820] = _prior()
        _stand(g, fake, 0, 0)
        rate = g.rate(require=True)
        full = g.lunge(1500.0, 0.0, walkmesh=wm)
        assert full["pressed"] and full["frames"] == rate.frames_for_ticks(10), (full, rate)
        _stand(g, fake, 0, 0)
        clipped = g.lunge(1500.0, 0.0, walkmesh=wm, avoid=[zone])
        end = g.settle()
        assert clipped["pressed"] and clipped["pad"] == "right" and 0 < clipped["frames"] < full["frames"], clipped
        assert pathfind.poly_gap(end.player_x, end.player_z, zone) >= pathfind.KEEPOUT_MARGIN_W, (end.pos, clipped)
        _stand(g, fake, 0, 0)
        mark = len(fake.executed)
        none = g.lunge(1500.0, 0.0, walkmesh=wm, avoid=[near])
        assert not none["pressed"] and none["frames"] == 0 and fake.executed[mark:] == [], (none, fake.executed[mark:])


def test_lunge_refuses_without_a_basis(game):
    """H3: a lunge presses at once, and a calibration is a walk of its own: with no CACHED basis for the field it
    raises, pressing nothing -- and so it does with control gone. Break: calibrate on a miss."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        mark = len(fake.executed)
        with pytest.raises(HarnessError, match="no CACHED basis"):
            g.lunge(300.0, 0.0, walkmesh=_flat_bgi())
        assert 30820 not in g._axes and not [s for s in fake.executed[mark:] if s[0] in ("hold", "press")]
        g._axes[30820] = _prior()
        fake.control = False
        published(g, lambda s: not s.control)
        with pytest.raises(HarnessError, match="needs control NOW"):
            g.lunge(300.0, 0.0, walkmesh=_flat_bgi())
        assert not [s for s in fake.executed[mark:] if s[0] in ("hold", "press")]


def test_states_since_returns_the_rings_samples_after_a_frame(game):
    """H6: the samples the state ring kept after a frame, oldest first -- every read the harness made, a walk's own
    included, each frame once (the ring dedupes on frame). StateRing.since is the same rule, pure. Break: ``>=``
    (the frame itself comes back)."""
    from harness.artifacts import StateRing
    ring = StateRing(5)
    for f in (3, 4, 4, 6, 9):
        ring.push(State({"frame": f}))
    assert [s["frame"] for s in ring.since(4)] == [6, 9] and [s["frame"] for s in ring.since(-1)] == [3, 4, 6, 9]
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        f0 = g.state.frame
        g.walk("right", 20)
        g.settle()
        got = g.states_since(f0)
        last = g._ring.frames()[-1]
    frames = [s["frame"] for s in got]
    assert frames and frames[0] > f0 and frames == sorted(set(frames)) and frames[-1] == last, frames
    xs = [s["player"]["x"] for s in got]
    assert xs[-1] > xs[0] + 100, xs                        # the walk's own samples are among them


# ---- O2's beat-table driver (studies/story-trace/segment_drive.drive; research/o2_design.md 2.2-2.7, PART B, B7), on
# the fake's three fields: 30820 and 30821 the route, 30810 the end. A director thread stages each game-side beat;
# the driver answers only by its table. Every test in which a region warps sets exit_frames = 50.

_O2_EXIT = _rect(300, -150, 600, 150)                  # 30820's (or 30821's) exit, its goal (450, 0)
_O2_BOOTH = _rect(-200, 100, 200, 500)                 # a Confirm region, 200 deep at its centre (0, 300)
_O2_DEFAULTS = {"attempts": 2, "interrupts": 1, "timeout_s": 20, "confirm_s": 4.0, "npcs": False, "overlay_ok": False,
                "immediate": False, "settle": None, "lunge_ticks": 0, "tolerance": 45, "min_depth": 40,
                "exit_wait_s": 8.0, "exit_slack": 40,
                "climb": {"burst_frames": 30, "max_bursts": 20, "stall_bursts": 3}}


def _o2_pred(table, *, choices=(), beats=(), start=30820, end=30810, route=(30820, 30821), **over):
    """A synthetic beat table on the fake's fields (research/o2_design.md 4.1's shape): the S side, no members, 4.1's
    step defaults but ``npcs`` off (the fake's rooms are empty), a 0.3 s settle."""
    pred = {"version": 1, "start": {"S": start, "F": start}, "entrance": 102, "scenario": 1000,
            "end_field": end, "end_fields": [end], "route": list(route), "members": {}, "names": {},
            "budget": {"run_s": 120, "run_min_s": 1, "session_s": 600, "settle_s": 0.3, "no_progress_s": 60},
            "beats": list(beats), "table": table, "choices": list(choices), "naming": [], "forbidden": [],
            "end_state": {}, "hotspots": {},
            "regions": {"exit": {"points": _O2_EXIT, "role": "exit"}, "booth": {"points": _O2_BOOTH, "role": "confirm"}},
            "steps_default": dict(_O2_DEFAULTS)}
    pred.update(over)
    return pred


def _o2_cross(**kw):
    return {"kind": "cross", "name": "exit", "target": "exit", "goal": [450, 0], "to": 30810, **kw}


def _o2_sc(fake, sc):
    """The scenario counter published AND in the modelled gEventGlobal (bytes 0-1), as a script's store leaves it."""
    fake.scenario = sc
    fake.story_bytes[0:2] = bytes((sc & 0xFF, (sc >> 8) & 0xFF))


def _o2_move(fake, fid, x=0.0, z=0.0):
    """A scripted transition: the field changes under him, a new visit's actor, control as it was."""
    fake.field_id, fake.player = fid, [float(x), 0.0, float(z)]
    fake._visit += 1


def _o2_start(g, fake, *, sc=1000, at=(-300, 0), fields=(30820, 30821)):
    """New Game, then the segment's raw warp into 30820 at ``sc`` (its residue in field 70), the bases cached."""
    boot(g)
    g.warp(30820, entrance=102, scenario=sc)
    _stand(g, fake, *at)
    for f in fields:
        g._axes[f] = _prior()


def _o2_drive(g, pred, side="S", *, log=None, budget=90.0, **kw):
    SD = _segment_modules()
    log = [] if log is None else log
    kw.setdefault("floor_for", lambda d, closed: _flat_bgi())
    kw.setdefault("prior_for", lambda d: _prior())
    kw.setdefault("forbid_live", False)
    return SD.drive(g, pred, side, log, deadline=time.time() + budget, **kw)


def _o2_booth_rule(**kw):
    return {"donor": 30820, "sc": [1000], "match": "ticket booth", "pick": "ticket booth", "once": True,
            "beat": "booth", "take": "default", **kw}


_O2_BOOTH_CHOICE = {"header": "", "options": ["eek into the ticket booth", "Cancel"], "default": 0}


def test_o2_drive_walks_its_table_to_the_end(game):
    """The driver end to end (research/o2_design.md 2.2-2.4): a CONFIRM walks deep into the booth and presses; its
    default-take choice (215's shape, no prompt line, the first character dropped) is answered at the game's own
    cursor; the answer carries him into a scene field (30821, SC 1150), whose pages are turned; a WAIT_SC step walks
    to its point and holds until a director publishes SC 1153; a CROSS walks into 30821's exit and lands in the end
    field THROUGH its 50-frame fade; the end state is read by watched bits. Beats, choices, steps, end_state as
    registered, and no Up or Down press ever executed (the cursor never moved)."""
    fake = FakeGame(game)
    fake.regions = {30821: [{"zone": _O2_EXIT, "to": 30810, "arrive": (0, 0)}]}
    fake.exit_frames = 50
    table = [{"donor": 30820, "sc": 1000, "steps": [{"kind": "confirm", "name": "booth", "target": "booth",
                                                     "goal": [0, 300], "expect": "choice"}]},
             {"donor": 30821, "sc": 1150, "steps": [{"kind": "wait_sc", "name": "wait", "goal": [-300, 0],
                                                     "sc": 1153, "wait_s": 30}]},
             {"donor": 30821, "sc": 1153, "steps": [_o2_cross()]}]
    pred = _o2_pred(table, choices=[_o2_booth_rule()], beats=["booth"],
                    end_state={"Global.UInt16[0]": 1153, "Global.Bit[3717]": 1})

    def into_30821(f):
        f.script_store(7, 1, 319, 3717 >> 3, "Bit", 1, bit=3717)
        _o2_move(f, 30821)
        _o2_sc(f, 1150)
        f.scene("Herald\n“Hear ye!”", "Herald\n“Princess Garnet's birthday!”")
    stop = threading.Event()
    log: list = []
    with session(game, fake) as g:
        _o2_start(g, fake, at=(0, -400))
        _o1_director(fake, stop, [
            (lambda f: _o1_confirmed_near(f, 0, 300, reach=100), lambda f: f.scene(dict(_O2_BOOTH_CHOICE))),
            (lambda f: f.answered == [0], into_30821),
            (lambda f: f.field_id == 30821 and f.control and math.hypot(f.player[0] + 300, f.player[2]) < 60,
             lambda f: _o2_sc(f, 1153)),
        ])
        try:
            out = _o2_drive(g, pred, log=log)
        finally:
            stop.set()
    assert out["end"] == "reached" and out["why"] == "field 30810", out
    assert out["beats"] == {"booth": True} and fake.answered == [0], out["beats"]
    assert [(c["donor"], c["sc"], c["index"], c["rule"]) for c in out["choices"]] == [(30820, 1000, 0, 0)], out["choices"]
    assert out["choices"][0]["took"] is not None and out["choices"][0]["selected"] == 0
    assert [(s["donor"], s["sc"], s["kind"], s["outcome"]) for s in out["steps"]] == [
        (30820, 1000, "confirm", "done"), (30821, 1150, "wait_sc", "done"), (30821, 1153, "cross", "done")], out["steps"]
    cross = out["steps"][2]
    assert cross["landed"] == 30810 and cross["lost"] is not None and cross["flip_frame"] is not None, cross
    assert out["end_state"] == {"Global.UInt16[0]": 1153, "Global.Bit[3717]": 1}, out["end_state"]
    assert out["pages"] == ["Herald\n“Hear ye!”", "Herald\n“Princess Garnet's birthday!”"], out["pages"]
    assert not [s for s in fake.executed if s[0] == "press" and s[1] in ("up", "down")], "the cursor was moved"
    assert [r["k"] for r in log if r["k"] in ("visit", "end")] == ["visit", "visit", "end"], log


def test_o2_drive_climbs_after_the_ladder_confirm(game):
    """H2 through the driver (research/o2_design.md 2.3 ``confirm`` + ``then: "climb"``): the ladder's Confirm takes
    control (its tag 3 puts him on the ladder), the climb holds Up to the top, where the scene moves him on (the field
    changes): done, with the beat ``climbed`` and the climb's record on the step."""
    fake = FakeGame(game)
    table = [{"donor": 30820, "sc": 1155, "steps": [{"kind": "confirm", "name": "ladder", "target": "booth",
                                                     "goal": [0, 300], "expect": "control_lost", "then": "climb",
                                                     "beat": "climbed"}]}]
    pred = _o2_pred(table, beats=["climbed"])
    stop = threading.Event()
    with session(game, fake) as g:
        _o2_start(g, fake, sc=1155, at=(0, -300))
        _o1_director(fake, stop, [(lambda f: _o1_confirmed_near(f, 0, 300, reach=100), _ladder),
                                  (lambda f: f.climbed, lambda f: _o2_move(f, 30810))])
        try:
            out = _o2_drive(g, pred)
        finally:
            stop.set()
    assert out["end"] == "reached" and out["beats"] == {"climbed": True}, out
    step = out["steps"][0]
    assert step["outcome"] == "done" and step["climb"]["ended"] == "until" and fake.climbed, step
    ys = [step["climb"]["y0"], *step["climb"]["ys"][:-1]]          # the last read is the next field's
    assert all(b > a for a, b in zip(ys, ys[1:])) and ys[-1] > 2000, step["climb"]
    assert not [s for s in fake.executed if s[0] == "hold" and s[1] in ("down", "right") and s[2] == "30"]


def _o2_jack(**kw):
    """Alleyway Jack as the fake publishes him: sid 7, a contact trigger of range_r 299 (4 x (26 + 30) + 15 + 60),
    standing far north of the lookout until he wakes (:func:`_o2_wake`)."""
    return {"x": -300.0, "z": 590.0, "r": 56.0, "range_r": 299.0, "sid": 7, **kw}


def _o2_wake(jack, speed=3.0):
    """Jack wakes as control comes (105: Map.Byte[35] := 0, 13-29 ticks before EnableMove) and walks to the lookout.
    ``speed`` is a frame of the fake's 60 fps model, whose loop runs 240 frames a WALL second: at 3 he is within his
    range_r of the lookout ~97 frames (~0.4 s) after waking -- after an immediate leave, before the driver's settle."""
    jack.update(path=[(jack["x"], jack["z"]), (-300.0, 0.0)], speed=float(speed), once=True)


def _o2_leave_table(*, immediate=True, watch=True):
    step = {"kind": "leave_now", "name": "leave", "target": "exit", "goal": [450, 0], "to": 30810,
            "immediate": immediate, "lunge_ticks": 10, "settle": 0, "npcs": False, "attempts": 1, "interrupts": 0}
    return [{"donor": 30820, "sc": 1152, "no_pages": True, "steps": [step],
             "watch": [{"sid": 7, "name": "Alleyway Jack", "radius": "range_r"}] if watch else []}]


def test_o2_drive_leaves_at_once(game):
    """leave_now (research/o2_design.md 2.3; 105's lookout, Jack's contact about 1.5-2.0 s after control): control is
    granted at a known frame, and an ``immediate`` step presses its first hold -- the lunge -- within 0.2 s of it
    (counted in the fake's loop frames, 240 a second); walking Jack never reaches him (no contact, no V6), and the
    ``watch`` rows include the ring's samples from INSIDE the step's harness calls. The same cell without
    ``immediate`` waits the driver's settle -- at least settle_s of wall time -- before its first hold. Break: settle
    before an immediate step."""
    got = {}
    for immediate in (True, False):
        fake = _StampFake(game)
        fake.regions = {30820: [{"zone": _O2_EXIT, "to": 30810, "arrive": (0, 0)}]}
        fake.exit_frames = 50
        pred = _o2_pred(_o2_leave_table(immediate=immediate, watch=immediate))
        pred["budget"]["settle_s"] = 1.0
        stop = threading.Event()
        grant: dict = {}
        log: list = []
        with session(game, fake) as g:
            _o2_start(g, fake, sc=1152, at=(-300, 0))
            fake.control = False                            # the scene before the lookout's EnableMove
            if immediate:
                fake.blockers = {30820: [_o2_jack()]}
            published(g, lambda s: not s.control and (not immediate or s.objects))

            def give(f):
                time.sleep(0.3)
                grant["frame"], grant["t"] = f.frame, time.time()
                if immediate:
                    _o2_wake(f.blockers[30820][0])
                f.control = True
            _o1_director(fake, stop, [(lambda f: True, give)])
            try:
                out = _o2_drive(g, pred, log=log)
            finally:
                stop.set()
        holds = [s for s in fake.stamped if s[2][0] == "hold" and s[1] >= grant["frame"]]
        got[immediate] = (out, log, holds[0], grant, fake)
    out, log, first, grant, fake = got[True]
    assert out["end"] == "reached" and out["steps"][0]["outcome"] == "done", out
    assert (first[1] - grant["frame"]) / fake.fps <= 0.2, (first, grant)
    assert out["steps"][0]["lunge"]["pressed"], out["steps"][0]
    assert not [t for t in fake.touched if t["uid"] == 128], fake.touched          # Jack never reached him
    step = out["steps"][0]
    inside = [r for r in log if r["k"] == "watch" and step["frame0"] < r["frame"] <= step["frame"]]
    assert len(inside) >= 3 and all(r["objects"] and r["objects"][0]["sid"] == 7 for r in inside), inside
    out, _log, first, grant, fake = got[False]
    assert out["end"] == "reached" and first[0] - grant["t"] >= 1.0, (first, grant)


def test_o2_drive_cross_waits_out_the_fade_inside_the_exit(game):
    """THE DRIVER CRITIQUE'S BLOCKER (research/o2_design.md 11.1 D1): control goes on the step into the exit and the
    field changes 50 frames later; meanwhile a hint is up with control OFF (106's [TIME=45], with no CloseWindow in
    e14 t2). The cross executor waits for the map switch itself, so the loop never reads the hint as a page in the
    ``no_pages`` cell: done, and never V5. Break: judge a loss inside the exit ``interrupted`` at once (the loop then
    meets the hint: V5)."""
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": _O2_EXIT, "to": 30810, "arrive": (0, 0)}]}
    fake.exit_frames = 50
    pred = _o2_pred([{"donor": 30820, "sc": 1153, "no_pages": True, "steps": [_o2_cross()]}])
    stop = threading.Event()
    with session(game, fake) as g:
        _o2_start(g, fake, sc=1153)
        _o1_director(fake, stop, [(lambda f: f.fired, lambda f: f.say("Puck\n“Over here!”"))])
        try:
            out = _o2_drive(g, pred)
        finally:
            stop.set()
    assert out["end"] == "reached" and [s["outcome"] for s in out["steps"]] == ["done"], out
    assert out["steps"][0]["lost"] is not None and out["pages"] == [], out


def test_o2_drive_cross_counts_a_loss_outside_the_exit_as_interrupted(game):
    """The Rat Kid's bump (100, research/o2_design.md 2.4): control taken well short of the exit (outside it by more
    than exit_slack) is ``interrupted`` -- then his page is turned, control comes back, and the same step runs again
    and lands. And a door that answers and never fires (``to`` None) leaves the walk ending with control held: each
    attempt ``failed``, and V7 (driver) once the attempts are spent."""
    SD = _segment_modules()
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": _O2_EXIT, "to": 30810, "arrive": (0, 0)}]}
    fake.exit_frames = 50
    pred = _o2_pred([{"donor": 30820, "sc": 1000, "steps": [_o2_cross()]}])
    stop = threading.Event()
    with session(game, fake) as g:
        _o2_start(g, fake)
        _o1_director(fake, stop, [(lambda f: f.control and f.player[0] > 0, lambda f: f.scene("Rat Kid\n“Hey!”"))])
        try:
            out = _o2_drive(g, pred)
        finally:
            stop.set()
    assert out["end"] == "reached" and out["pages"] == ["Rat Kid\n“Hey!”"], out
    assert [s["outcome"] for s in out["steps"]] == ["interrupted", "done"], out["steps"]
    assert out["steps"][0]["lost"]["x"] < 300 - 40, out["steps"][0]
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": _O2_EXIT, "to": None}]}
    pred = _o2_pred([{"donor": 30820, "sc": 1000, "steps": [_o2_cross(timeout_s=2.0)]}])
    log: list = []
    with session(game, fake) as g:
        _o2_start(g, fake)
        with pytest.raises(SD.RouteVoid, match="failed 2 of its 2 attempts") as err:
            _o2_drive(g, pred, log=log)
    assert (err.value.v, err.value.by, err.value.cell) == ("V7", "driver", [30820, 1000])
    assert [r["outcome"] for r in log if r["k"] == "step"] == ["failed", "failed"], log


def test_o2_drive_cross_inside_loss_without_a_field_change_is_interrupted(game):
    """Control taken INSIDE the exit's zone with no field change after it (a walk-in trigger inside the exit, listed
    first, so it answers): the executor waits ``exit_wait_s`` for the map switch, then calls it ``interrupted``; the
    second time is over the step's one interruption: V7. Under leave_now (``interrupts`` 0) the first is V7."""
    from ff9mapkit.content import pathfind
    SD = _segment_modules()
    for kind, want in (("cross", ["interrupted", "interrupted"]), ("leave_now", ["interrupted"])):
        fake = FakeGame(game)
        fake.regions = {30820: [{"zone": _O2_EXIT, "take": True}, {"zone": _O2_EXIT, "to": 30810, "arrive": (0, 0)}]}
        fake.exit_frames = 50
        step = _o2_cross(kind=kind, exit_wait_s=1.0, interrupts=1 if kind == "cross" else 0)
        pred = _o2_pred([{"donor": 30820, "sc": 1000, "steps": [step]}])
        stop = threading.Event()
        log: list = []

        def back(f):
            time.sleep(1.6)                                 # past exit_wait_s: the executor has judged it
            f.player = [-300.0, 0.0, 0.0]
            f.control = True
        with session(game, fake) as g:
            _o2_start(g, fake)
            _o1_director(fake, stop, [(lambda f: len(f.fired) == 1 and not f.control, back)])
            try:
                with pytest.raises(SD.RouteVoid, match="interrupted") as err:
                    _o2_drive(g, pred, log=log)
            finally:
                stop.set()
        steps = [r for r in log if r["k"] == "step"]
        assert err.value.v == "V7" and [s["outcome"] for s in steps] == want, (kind, steps)
        assert all(pathfind.poly_gap(s["lost"]["x"], s["lost"]["z"], _O2_EXIT) < 1.0 for s in steps), steps
        assert all(f["to"] is None for f in fake.fired), fake.fired


def test_o2_drive_confirm_walks_deep_before_pressing(game):
    """confirm (research/o2_design.md 2.3, the driver critique's D6): the walk goes to the deep goal WITHOUT the zone,
    and the Confirm is pressed only once the settled sample stands in the region at ``min_depth`` or deeper -- the
    ``press`` row's ``pre`` is that sample. A goal at the region's edge settles him too shallow: ``failed`` with
    nothing pressed, and V7 once the attempts are spent."""
    SD = _segment_modules()
    fake = FakeGame(game)
    stop = threading.Event()
    log: list = []
    pred = _o2_pred([{"donor": 30820, "sc": 1000, "steps": [{"kind": "confirm", "name": "booth", "target": "booth",
                                                             "goal": [0, 300], "expect": "choice"}]}],
                    choices=[_o2_booth_rule()], beats=["booth"])
    with session(game, fake) as g:
        _o2_start(g, fake, at=(0, -400))
        _o1_director(fake, stop, [
            (lambda f: _o1_confirmed_near(f, 0, 300, reach=100), lambda f: f.scene(dict(_O2_BOOTH_CHOICE))),
            (lambda f: f.answered == [0], lambda f: _o2_move(f, 30810))])
        try:
            out = _o2_drive(g, pred, log=log)
        finally:
            stop.set()
    SD_depth = SD.depth_in
    press = next(r for r in log if r["k"] == "press" and r["why"] == "confirm")
    assert out["end"] == "reached" and press["pre"]["control"], (out, press)
    assert SD_depth(_O2_BOOTH, press["pre"]["x"], press["pre"]["z"]) >= 40, press
    assert out["steps"][0]["depth"] >= 40 and press["post"] is not None, out["steps"][0]
    fake = FakeGame(game)
    pred = _o2_pred([{"donor": 30820, "sc": 1000, "steps": [{"kind": "confirm", "name": "edge", "target": "booth",
                                                             "goal": [0, 100], "tolerance": 20, "expect": "choice"}]}])
    log = []
    with session(game, fake) as g:
        _o2_start(g, fake, at=(0, -400))
        with pytest.raises(SD.RouteVoid, match="failed 2 of its 2 attempts") as err:
            _o2_drive(g, pred, log=log)
    assert err.value.v == "V7" and not [s for s in fake.executed if s[:2] == ["press", "confirm"]], fake.executed
    assert [(r["outcome"], r["depth"] is None or r["depth"] < 40) for r in log if r["k"] == "step"] == [
        ("failed", True), ("failed", True)], log


def test_o2_drive_counts_steps_per_visit(game):
    """116's three triggers in ONE cell (research/o2_design.md 2.1: the counter is per visit): each ``until`` step is
    done only when control goes with its predicate true at the loss sample, and the next control in the same cell
    runs the NEXT step -- 0, 1, 2 -- all in visit 1."""
    fake = FakeGame(game)
    steps = [{"kind": "trigger", "name": "t1", "until": {"x_le": -300}, "goal": [-400, 0]},
             {"kind": "trigger", "name": "t2", "until": {"z_ge": 300}, "goal": [-400, 400]},
             {"kind": "trigger", "name": "t3", "until": {"x_gt": 300, "z_gt": 300}, "goal": [400, 400]}]
    pred = _o2_pred([{"donor": 30820, "sc": 1155, "steps": steps}])
    stop = threading.Event()

    def take_then(nxt=None):
        def act(f):
            f.control = False
            time.sleep(0.3)
            if nxt is None:
                f.control = True
            else:
                nxt(f)
        return act
    with session(game, fake) as g:
        _o2_start(g, fake, sc=1155, at=(0, 0))
        _o1_director(fake, stop, [
            (lambda f: f.control and f.player[0] <= -300, take_then()),
            (lambda f: f.control and f.player[2] >= 300, take_then()),
            (lambda f: f.control and f.player[0] > 300 and f.player[2] > 300, take_then(lambda f: _o2_move(f, 30810)))])
        try:
            out = _o2_drive(g, pred)
        finally:
            stop.set()
    assert out["end"] == "reached", out
    assert [(s["visit"], s["n"], s["name"], s["outcome"]) for s in out["steps"]] == [
        (1, 0, "t1", "done"), (1, 1, "t2", "done"), (1, 2, "t3", "done")], out["steps"]


def test_o2_drive_voids_control_without_a_cell(game):
    """Control held where the table has no cell (104 in O2, research/o2_design.md 2.4): V4, attributed to the game,
    its cell the (place, SC) it happened in. Nothing is walked."""
    SD = _segment_modules()
    fake = FakeGame(game)
    pred = _o2_pred([{"donor": 30821, "sc": 1000, "steps": [_o2_cross()]}])
    with session(game, fake) as g:
        _o2_start(g, fake)
        mark = len(fake.executed)
        with pytest.raises(SD.RouteVoid, match="where the table has no entry") as err:
            _o2_drive(g, pred, budget=20.0)
        assert not [s for s in fake.executed[mark:] if s[0] == "hold"]
    assert (err.value.v, err.value.by, err.value.cell) == ("V4", "game", [30820, 1000])


def test_o2_drive_voids_a_once_choice_asked_again(game):
    """V2 (research/o2_design.md 2.7): a ``once`` rule asked again -- 251 after an info option -- is VOID, never
    answered twice; and a rule scoped to SC 1000 does not answer at SC 1150 (215 re-offered on the second visit): V1,
    game. Each after the first answer only."""
    SD = _segment_modules()
    rule = {"donor": 30820, "sc": [1000], "match": "ticket", "pick": "ticket", "once": True, "take": "default",
            "beat": "ticket"}
    ticket = {"header": "Guard\n“Well?”", "options": ["Show ticket", "Ask about the play"], "default": 0}
    for sc, want, answered in ((1000, "V2", [0]), (1150, "V1", [])):
        fake = FakeGame(game)
        pred = _o2_pred([], choices=[rule], beats=["ticket"])
        with session(game, fake) as g:
            _o2_start(g, fake, sc=sc)
            fake.scene(dict(ticket), dict(ticket))
            published(g, lambda s: not s.control and s.choice is not None)
            with pytest.raises(SD.RouteVoid) as err:
                _o2_drive(g, pred)
        assert (err.value.v, err.value.by, err.value.cell) == (want, "game", [30820, sc]), err.value
        assert fake.answered == answered, (sc, fake.answered)


def test_o2_drive_voids_when_the_default_is_not_the_pick(game):
    """V3: a ``take: "default"`` rule whose pick is not the game's own ready cursor (the script's default rests on
    another line): VOID -- stepping the cursor is not the route -- and the cursor is left alone (no Up/Down, nothing
    answered)."""
    SD = _segment_modules()
    fake = FakeGame(game)
    rule = {"donor": 30820, "sc": [1000], "match": "ticket", "pick": "Show ticket", "once": True, "take": "default"}
    pred = _o2_pred([], choices=[rule])
    with session(game, fake) as g:
        _o2_start(g, fake)
        fake.scene({"header": "Guard\n“Well?”", "options": ["Show ticket", "Leave"], "default": 1})
        published(g, lambda s: not s.control and s.choice is not None)
        with pytest.raises(SD.RouteVoid, match="not the game's default") as err:
            _o2_drive(g, pred)
    assert (err.value.v, err.value.by) == ("V3", "game") and fake.answered == [], (err.value, fake.answered)
    assert not [s for s in fake.executed if s[0] == "press" and s[1] in ("up", "down", "confirm")], fake.executed


def test_o2_drive_voids_a_page_in_a_no_pages_cell(game):
    """V5: a page (control off) in a ``no_pages`` cell -- in 105 at SC 1152 a Confirm could be Jack's side trip -- is
    VOID with NO Confirm pressed; attributed to the game when no watched object was in contact reach before it."""
    SD = _segment_modules()
    fake = FakeGame(game)
    pred = _o2_pred(_o2_leave_table())
    with session(game, fake) as g:
        _o2_start(g, fake, sc=1152)
        mark = len(fake.executed)
        fake.scene("Alleyway Jack\n“Hey, kid!”")
        published(g, lambda s: not s.control and s.dialog_open)
        with pytest.raises(SD.RouteVoid, match="a page where the route has none") as err:
            _o2_drive(g, pred)
        steps = fake.executed[mark:]
    assert (err.value.v, err.value.by, err.value.cell) == ("V5", "game", [30820, 1152]), err.value
    assert not [s for s in steps if s[:2] == ["press", "confirm"]], steps


def test_o2_drive_voids_a_watched_object_in_reach(game):
    """V6: a watched object within its published radius while he holds control (Jack inside his range_r at the lookout):
    VOID, attributed to the driver (a lost race), and the watch row that saw it is logged."""
    SD = _segment_modules()
    fake = FakeGame(game)
    pred = _o2_pred(_o2_leave_table(immediate=False))
    pred["table"][0]["watch"] = [{"sid": 7, "name": "Alleyway Jack", "radius": "range_r"}]
    log: list = []
    with session(game, fake) as g:
        _o2_start(g, fake, sc=1152, at=(-300, 0))
        fake.blockers = {30820: [{"x": -100.0, "z": 0.0, "r": 56.0, "range_r": 299.0, "sid": 7}]}
        with pytest.raises(SD.RouteVoid, match="Alleyway Jack") as err:
            _o2_drive(g, pred, log=log)
    assert (err.value.v, err.value.by, err.value.cell) == ("V6", "driver", [30820, 1152]), err.value
    row = [r for r in log if r["k"] == "watch"][-1]
    assert row["control"] and row["objects"][0]["sid"] == 7 and row["objects"][0]["dist"] <= 299, row


def test_o2_drive_voids_leaving_the_route(game):
    """V11 three ways (research/o2_design.md 2.2 rule 2, 2.3): a cross whose exit lands -- through its fade -- in a field
    that is not its ``to`` (the driver's walk into the wrong door: ``by`` driver); a scripted transition into a field
    off the route (``by`` game); and, on the F side, a REAL route field reached from a member (the claim-integrity
    critique #2: a donor test would pass it -- the chain is left)."""
    SD = _segment_modules()
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": _O2_EXIT, "to": 30821, "arrive": (0, 0)}]}
    fake.exit_frames = 50
    pred = _o2_pred([{"donor": 30820, "sc": 1000, "steps": [_o2_cross()]}])
    with session(game, fake) as g:
        _o2_start(g, fake)
        with pytest.raises(SD.RouteVoid, match="landed in 30821") as err:
            _o2_drive(g, pred)
    assert (err.value.v, err.value.by) == ("V11", "driver"), err.value
    fake = FakeGame(game)
    pred = _o2_pred([])
    with session(game, fake) as g:
        _o2_start(g, fake)
        fake.control = False
        _o2_move(fake, 30999)
        published(g, lambda s: s.field_id == 30999 and not s.control)
        with pytest.raises(SD.RouteVoid, match="left the route: entered 30999") as err:
            _o2_drive(g, pred)
    assert (err.value.v, err.value.by, err.value.cell) == ("V11", "game", [30999, 1000]), err.value
    fake = FakeGame(game)
    pred = _o2_pred([], start=30821, route=(30820,), members={"30821": 30820})
    pred["budget"]["no_progress_s"] = 3.0
    with session(game, fake) as g:
        boot(g)
        g.warp(30821, entrance=102, scenario=1000)
        fake.control = False
        _o2_move(fake, 30820)                               # the member's Field() went to the REAL donor
        published(g, lambda s: s.field_id == 30820 and not s.control)
        with pytest.raises(SD.RouteVoid, match="left the route: entered 30820 \\(place 30820\\)") as err:
            _o2_drive(g, pred, side="F")
    assert (err.value.v, err.value.by) == ("V11", "game"), err.value


_O2_JACK_BITS = [{"target": "Global.Bit[3715]", "cause": "contact", "object": 7,
                  "why": "Jack's mugging branch (105 e7 t2 ip945)"},
                 {"off_route": True, "cause": "walk", "why": "a write off the route"}]
_O2_HOT = [{"target": "Global.Int16[220]", "cause": "confirm_hotspot", "why": "a hot-spot pickup: a stray Confirm"},
           {"target": "Global.Int16[222]", "cause": "confirm_hotspot", "why": "a hot-spot pickup: a stray Confirm"}]


def _o2_traced_start(g, fake, *, sc=1000, at=(-300, 0)):
    """New Game with the trace armed first, a store in field 70 (off the route), then the raw warp (its residue in 70)
    and 30820's first store: the start row."""
    boot(g)
    g.storytrace(True)
    fake.script_store(3, 1, 40, 13, "Byte", 2)             # field 70: before the start, never scanned
    g.warp(30820, entrance=102, scenario=sc)
    fake.script_store(0, 0, 30, 191 >> 3, "Bit", 0, bit=191)   # the start row: 30820's Main_Init
    _stand(g, fake, *at)
    g._axes[30820] = _prior()


def test_o2_drive_live_scan_ignores_the_warp_residue(game):
    """D2 (research/o2_design.md 11.1): H4's warp writes its three residue rows in field 70, and a store there comes
    before them -- the live scan starts at the run's START ROW (its first ``w`` row in the start place), so neither is
    an off-route hit and the run reaches the end with no forbidden row. In the same kind of run a BACKED forbidden
    row after the start still VOIDs it: a watch sample puts Jack within his range_r + 150 before his contact's
    Bit[3715] := 1 is written -- V12, driver."""
    SD = _segment_modules()
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": _O2_EXIT, "to": 30810, "arrive": (0, 0)}]}
    fake.exit_frames = 50
    pred = _o2_pred([{"donor": 30820, "sc": 1000, "steps": [_o2_cross()]}], forbidden=_O2_JACK_BITS)
    log: list = []
    with session(game, fake) as g:
        _o2_traced_start(g, fake)
        out = _o2_drive(g, pred, log=log, forbid_live=True)
        rows = g.story_rows()
        g.storytrace(False)
    assert out["end"] == "reached" and out["forbidden"] == [] and not [r for r in log if r["k"] == "forbidden"], out
    assert [(r.fld, r.byte) for r in rows if r.k == "r"] == [(70, 0), (70, 1), (70, 2)], rows
    assert any(r.k == "w" and r.fld == 70 for r in rows), "premise: a store before the start"
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": _O2_EXIT, "to": 30810, "arrive": (0, 0)}]}
    fake.exit_frames = 50
    pred = _o2_pred([{"donor": 30820, "sc": 1000, "steps": [_o2_cross()],
                      "watch": [{"sid": 7, "name": "Alleyway Jack", "radius": "range_r"}]}], forbidden=_O2_JACK_BITS)
    stop = threading.Event()
    log = []
    with session(game, fake) as g:
        _o2_traced_start(g, fake)
        fake.blockers = {30820: [{"x": -300.0, "z": 400.0, "r": 56.0, "range_r": 299.0, "sid": 7, "coll": True}]}
        _o1_director(fake, stop, [(lambda f: f.player[0] > 0, lambda f: f.script_store(7, 2, 945, 3715 >> 3, "Bit", 1,
                                                                                         bit=3715))])
        try:
            with pytest.raises(SD.RouteVoid, match="backed by a watch sample") as err:
                _o2_drive(g, pred, log=log, forbid_live=True)
        finally:
            stop.set()
            g.storytrace(False)
    assert (err.value.v, err.value.by) == ("V12", "driver"), err.value
    row = [r for r in log if r["k"] == "forbidden"][-1]
    assert row["backed"] and row["row"]["target"] == "Global.Bit[3715]" and row["cause"] == "contact", row


def _o2_hotspot_run(game, *, press: bool):
    """A run whose 30820 visit writes a hot-spot's rows (Int16[220]/[222] := its position, 103 e20's shape) -- after
    the driver's own Confirm near it (``press``: a confirm step into the booth), or with none (a cross past it)."""
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": _O2_EXIT, "to": 30810, "arrive": (0, 0)}]}
    fake.exit_frames = 50
    step = ({"kind": "confirm", "name": "booth", "target": "booth", "goal": [0, 300], "expect": "choice"} if press
            else _o2_cross())
    pred = _o2_pred([{"donor": 30820, "sc": 1000, "steps": [step]}], choices=[_o2_booth_rule()], forbidden=_O2_HOT,
                    hotspots={"30820": [{"sid": 20, "x": 100, "z": 300, "n": 50}]})

    def spot(f):
        f.script_store(20, 1, 175, 220, "Int16", 100)
        f.script_store(20, 1, 183, 222, "Int16", 300)
        if press:
            f.scene(dict(_O2_BOOTH_CHOICE))
    stop = threading.Event()
    log: list = []
    phases = ([(lambda f: _o1_confirmed_near(f, 0, 300, reach=100), spot),
               (lambda f: f.answered == [0], lambda f: _o2_move(f, 30810))] if press
              else [(lambda f: f.control and f.player[0] > -100, spot)])
    return fake, pred, stop, log, phases


def test_o2_drive_voids_a_backed_forbidden_row(game):
    """V12 (research/o2_design.md 4.7): the driver's own Confirm, control held, 100u from a registered hot-spot
    (reach 226), and then that hot-spot's rows -- its position stores name it -- are a walk divergence the driver's
    log backs: VOID, driver, the forbidden row logged with its backing."""
    SD = _segment_modules()
    fake, pred, stop, log, phases = _o2_hotspot_run(game, press=True)
    with session(game, fake) as g:
        _o2_traced_start(g, fake, at=(0, -400))
        _o1_director(fake, stop, phases)
        try:
            with pytest.raises(SD.RouteVoid, match="backed by a Confirm") as err:
                _o2_drive(g, pred, log=log, forbid_live=True)
        finally:
            stop.set()
            g.storytrace(False)
    assert (err.value.v, err.value.by) == ("V12", "driver"), err.value
    row = next(r for r in log if r["k"] == "forbidden")
    assert row["backed"] and row["hotspot"] == {"sid": 20, "x": 100, "z": 300, "reach": 226.0}, row


def test_o2_drive_logs_an_unbacked_forbidden_row_and_goes_on(game):
    """The same hot-spot rows with NO Confirm of the driver's behind them (a fork's 106 writing hot-spot keys by
    itself): a finding, never a VOID -- a ``forbidden`` row with ``backed`` False per matching row, and the run reaches
    the end."""
    fake, pred, stop, log, phases = _o2_hotspot_run(game, press=False)
    with session(game, fake) as g:
        _o2_traced_start(g, fake)
        _o1_director(fake, stop, phases)
        try:
            out = _o2_drive(g, pred, log=log, forbid_live=True)
        finally:
            stop.set()
            g.storytrace(False)
    assert out["end"] == "reached", out
    assert [(r["backed"], r["row"]["target"]) for r in out["forbidden"]] == [
        (False, "Global.Int16[220]"), (False, "Global.Int16[222]")], out["forbidden"]
    assert all(r["hotspot"] is not None for r in out["forbidden"]), out["forbidden"]


def test_o2_drive_scans_once_more_at_the_end(game):
    """The claim-integrity critique #4: a forbidden row written AFTER the last new visit began (no later visit scans
    it) is still found -- the end runs the scan once more before ``reached``."""
    fake = FakeGame(game)
    pred = _o2_pred([], forbidden=_O2_JACK_BITS)
    stop = threading.Event()
    log: list = []
    with session(game, fake) as g:
        _o2_traced_start(g, fake)
        fake.control = False
        published(g, lambda s: not s.control)
        _o1_director(fake, stop, [(lambda f: True, lambda f: (time.sleep(0.5),
                                                              f.script_store(7, 2, 945, 3715 >> 3, "Bit", 1, bit=3715),
                                                              time.sleep(0.3), _o2_move(f, 30810)))])
        try:
            out = _o2_drive(g, pred, log=log, forbid_live=True)
        finally:
            stop.set()
            g.storytrace(False)
    visits = [r for r in log if r["k"] == "visit"]
    assert out["end"] == "reached" and len(visits) == 1, (out, visits)
    assert [(r["backed"], r["row"]["target"]) for r in out["forbidden"]] == [(False, "Global.Bit[3715]")], out
    assert out["forbidden"][0]["row"]["f"] > visits[0]["frame"], (out["forbidden"], visits)


def test_o2_drive_voids_when_nothing_changes(game):
    """The stall watchdog (research/o2_design.md 2.2, the driver critique's D4): nothing published changes for
    ``no_progress_s`` -- a field with no control and no window -- and the run is VOID V14 (game) in about that time,
    not its whole budget. Any published change resets it: a director moving him every 0.4 s keeps it off for as long
    as it goes on."""
    SD = _segment_modules()
    fake = FakeGame(game)
    pred = _o2_pred([])
    pred["budget"]["no_progress_s"] = 1.0
    stop = threading.Event()
    last: dict = {}

    def nudge(f):
        for k in range(6):
            f.player = [f.player[0] + 16.0, 0.0, f.player[2]]
            last["t"] = time.time()
            time.sleep(0.4)
    with session(game, fake) as g:
        _o2_start(g, fake)
        fake.control = False
        published(g, lambda s: not s.control)
        _o1_director(fake, stop, [(lambda f: True, nudge)])
        t0 = time.time()
        try:
            with pytest.raises(SD.RouteVoid, match="no progress for 1 s in 30820") as err:
                _o2_drive(g, pred, budget=15.0)
        finally:
            stop.set()
        t1 = time.time()
    assert (err.value.v, err.value.by, err.value.cell) == ("V14", "game", [30820, 1000]), err.value
    assert t1 - t0 >= 2.4 and 1.0 <= t1 - last["t"] < 5.0, (t1 - t0, t1 - last["t"])


def test_o2_drive_records_presses_and_watch_samples(game):
    """The evidence 4.7's backing rule reads (research/o2_design.md 2.2): a ``press`` row per Confirm -- ``pre`` the
    sample it was decided on, ``post`` the next one any read kept, ``near`` the published objects whose talk / range
    disc (64u wider) held him -- and a ``watch`` row per poll in a watched cell, shaped ``{k, frame, control, x, z,
    field, donor, objects: [{sid, x, z, range_r, talk_r, dist}]}`` with the watched sids only."""
    fake = FakeGame(game)
    pred = _o2_pred([{"donor": 30820, "sc": 1000, "steps": [_o2_cross()],
                      "watch": [{"sid": 7, "name": "Alleyway Jack", "radius": "range_r"}]}])
    fake.regions = {30820: [{"zone": _O2_EXIT, "to": 30810, "arrive": (0, 0)}]}
    fake.exit_frames = 50
    log: list = []
    with session(game, fake) as g:
        _o2_start(g, fake)
        fake.blockers = {30820: [{"x": -300.0, "z": 150.0, "r": 30.0, "talk_r": 100.0, "sid": 9, "coll": False},
                                 {"x": -300.0, "z": 550.0, "r": 56.0, "range_r": 150.0, "sid": 7}]}
        fake.scene("Kupo\n“Kupo!”")
        published(g, lambda s: s.dialog_open and not s.control and s.objects and len(s.objects) == 2)
        out = _o2_drive(g, pred, log=log)
    assert out["end"] == "reached", out
    press = next(r for r in log if r["k"] == "press")
    assert set(press) == {"k", "why", "field", "donor", "visit", "sc", "pre", "post", "near"}, press
    assert press["why"] == "page" and press["visit"] == 1 and not press["pre"]["control"], press
    assert press["post"]["frame"] > press["pre"]["frame"] and set(press["post"]) == {"frame", "control", "x", "z"}
    assert [(n["sid"], n["kind"]) for n in press["near"]] == [(9, "talk")], press["near"]
    watch = [r for r in log if r["k"] == "watch"]
    assert watch and all(set(r) == {"k", "frame", "control", "x", "z", "field", "donor", "objects"} for r in watch)
    assert all([o["sid"] for o in r["objects"]] == [7] for r in watch), watch[:3]
    o = watch[0]["objects"][0]
    assert set(o) == {"sid", "x", "z", "range_r", "talk_r", "dist"} and o["range_r"] == 150.0, o
    assert o["dist"] == pytest.approx(math.hypot(o["x"] - watch[0]["x"], o["z"] - watch[0]["z"]), abs=0.2), o


# ---- the review's driver findings (research/o2_design.md 11.6): the landing judge every executor shares, rule 2's
# order and attribution, wait_sc's walk short of its point, rule 8's settle before V4, and step_of's refusals.

_O2_DOOR = _rect(-100, -150, 0, 150)                   # a registered exit ACROSS the walk east from (-300, 0)
_O2_FAR = _rect(150, -150, 450, 150)                   # a Confirm region past it, its goal (300, 0)


@pytest.mark.parametrize("kind", ["cross", "wait_sc", "trigger", "confirm"])
def test_o2_drive_voids_a_walk_into_another_registered_door_as_the_drivers(game, kind):
    """The review's finding 1 (106's gated e13 on the street to e14; 106.e12 beside the wait walk): a walk that loses
    control in ANOTHER registered exit of the place -- not its target -- is that door's ExitField. Every executor's
    landing judge waits its switch out (the 50-frame fade) and calls the landing V11, the DRIVER's, with ``landed`` and
    the ``door`` on the step row -- so 4.7's ``walk`` backing holds for the rows written where it landed. Break: judge
    such a loss ``interrupted`` (the loop then reads the landing as the game's: V11 by game, or V4)."""
    SD = _segment_modules()
    step = {"cross": _o2_cross(),
            "wait_sc": {"kind": "wait_sc", "name": "wait", "goal": [200, 0], "sc": 1153, "wait_s": 5},
            "trigger": {"kind": "trigger", "name": "east", "until": {"x_gt": 150}, "goal": [200, 0]},
            "confirm": {"kind": "confirm", "name": "far", "target": "far", "goal": [300, 0], "expect": "choice"}}[kind]
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": _O2_DOOR, "to": 30999, "arrive": (0, 0)},
                            {"zone": _O2_EXIT, "to": 30810, "arrive": (0, 0)}]}
    fake.exit_frames = 50
    pred = _o2_pred([{"donor": 30820, "sc": 1152, "steps": [step]}])
    pred["regions"].update(door={"points": _O2_DOOR, "role": "exit"}, far={"points": _O2_FAR, "role": "confirm"})
    log: list = []
    with session(game, fake) as g:
        _o2_start(g, fake, sc=1152)
        with pytest.raises(SD.RouteVoid, match="landed in 30999") as err:
            _o2_drive(g, pred, log=log)
    assert (err.value.v, err.value.by, err.value.cell) == ("V11", "driver", [30820, 1152]), (kind, err.value)
    assert [f["to"] for f in fake.fired] == [30999], fake.fired
    row = [r for r in log if r["k"] == "step"][-1]
    assert (row["outcome"], row["v"], row["by"], row["landed"], row["door"]) == ("void", "V11", "driver", 30999,
                                                                                 "door"), row
    assert row["flip_frame"] is not None and row["lost"] is not None, row
    assert SD.backing({"f": row["frame"] + 1, "cause": "walk", "fld": 30999}, log, pred) is not None, row


def test_o2_drive_holds_each_visit_to_the_routes_order(game):
    """Rule 2 (the review's finding 1): every new visit must be the place the route's ORDER goes to next (``visits``,
    default ``route``). A walk that steps into a door the table does NOT register (no landing judge can see it) ends
    ``interrupted``; the field then changes -- to 30822, ON the route but out of its order -- with nothing pressed or
    answered since: V11, the DRIVER's, and the interrupted step's row now carries the landing (``late``), so the
    ``walk`` backing holds. The same order break after a page the driver turned is a scripted transition: V11, the
    game's. Break: check membership only (30822 is on the route: the old loop read V4 there, by game)."""
    SD = _segment_modules()
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": _O2_DOOR, "to": 30822, "arrive": (0, 0)},
                            {"zone": _O2_EXIT, "to": 30821, "arrive": (0, 0)}]}
    fake.exit_frames = 240                              # a slow switch: the executor has judged long before it
    pred = _o2_pred([{"donor": 30820, "sc": 1000, "steps": [_o2_cross(to=30821)]}], route=(30820, 30821, 30822))
    log: list = []
    with session(game, fake) as g:
        _o2_start(g, fake, fields=(30820, 30821, 30822))
        with pytest.raises(SD.RouteVoid, match="out of the route's order: entered 30822") as err:
            _o2_drive(g, pred, log=log)
    assert (err.value.v, err.value.by, err.value.cell) == ("V11", "driver", [30820, 1000]), err.value
    row = [r for r in log if r["k"] == "step"][-1]
    assert row["outcome"] == "interrupted" and row["door"] is None, row
    assert (row["v"], row["by"], row["landed"], row["late"]) == ("V11", "driver", 30822, True), row
    assert SD.backing({"f": row["frame"] + 1, "cause": "walk", "fld": 30822}, log, pred) is not None, row
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": _O2_DOOR, "take": True}, {"zone": _O2_EXIT, "to": 30821, "arrive": (0, 0)}]}
    fake.exit_frames = 50
    stop = threading.Event()
    log = []
    with session(game, fake) as g:
        _o2_start(g, fake, fields=(30820, 30821, 30822))
        _o1_director(fake, stop, [(lambda f: f.fired and not f.control, lambda f: f.scene("Guard\n“Halt!”")),
                                  (lambda f: not f._beats and f.control, lambda f: (setattr(f, "control", False),
                                                                                    _o2_move(f, 30822)))])
        try:
            with pytest.raises(SD.RouteVoid, match="out of the route's order: entered 30822") as err:
                _o2_drive(g, pred, log=log)
        finally:
            stop.set()
    assert (err.value.v, err.value.by, err.value.cell) == ("V11", "game", [30822, 1000]), err.value
    assert [r["why"] for r in log if r["k"] == "press"] == ["page"], log
    assert all(r.get("v") is None for r in log if r["k"] == "step"), log


def test_o2_drive_wait_sc_short_of_its_point_is_the_drivers(game):
    """The review's finding 2 (106's wait: SC 1153 needs Vivi within 1400 of Puck's stop): a wait_sc whose walk ends
    short of its point -- here no route at all, the point inside an avoided region -- is ``failed`` with NO wait begun,
    and V7 (the driver's) once its attempts are spent -- never V8, the game's. A wait begun AT its point still times
    out as V8 (game). Break: wait on the SC wherever the walk ended (V8 by game after wait_s)."""
    SD = _segment_modules()
    fake = FakeGame(game)
    step = {"kind": "wait_sc", "name": "wait", "goal": [0, 300], "sc": 1153, "wait_s": 5, "avoid": ["booth"]}
    pred = _o2_pred([{"donor": 30820, "sc": 1152, "steps": [step]}])
    log: list = []
    with session(game, fake) as g:
        _o2_start(g, fake, sc=1152, at=(-500, -500))
        with pytest.raises(SD.RouteVoid, match="failed 2 of its 2 attempts") as err:
            _o2_drive(g, pred, log=log)
    assert (err.value.v, err.value.by, err.value.cell) == ("V7", "driver", [30820, 1152]), err.value
    steps = [r for r in log if r["k"] == "step"]
    assert [s["outcome"] for s in steps] == ["failed", "failed"] and all("no wait" in s["why"] for s in steps), steps
    fake = FakeGame(game)
    step = {"kind": "wait_sc", "name": "wait", "goal": [-300, 300], "sc": 1153, "wait_s": 1.0}
    pred = _o2_pred([{"donor": 30820, "sc": 1152, "steps": [step]}])
    with session(game, fake) as g:
        _o2_start(g, fake, sc=1152)
        with pytest.raises(SD.RouteVoid, match="of a wait begun at the point") as err:
            _o2_drive(g, pred)
    assert (err.value.v, err.value.by) == ("V8", "game"), err.value


def test_o2_drive_settles_before_calling_control_off_the_table(game):
    """The review's finding 3 (O1's order, proven 7/7): a control sample shorter than the settle is no control -- in a
    place with no cell (104), or in a cell whose steps are all done (after a Confirm's choice closed) -- and the run
    goes on to the end; control that STAYS after the cell's last step is still V4 (game), once settled. Break: raise
    either V4 on the first control poll."""
    SD = _segment_modules()

    def flicker_then_end(f):
        time.sleep(0.3)
        f.control = True                                # one control flicker, well under the 0.3 s settle
        time.sleep(0.15)
        f.control = False
        time.sleep(0.3)
        _o2_move(f, 30810)
    fake = FakeGame(game)
    pred = _o2_pred([])
    stop = threading.Event()
    with session(game, fake) as g:
        _o2_start(g, fake)
        fake.control = False
        published(g, lambda s: not s.control)
        _o1_director(fake, stop, [(lambda f: True, flicker_then_end)])
        try:
            out = _o2_drive(g, pred)
        finally:
            stop.set()
    assert out["end"] == "reached", out
    booth = [{"donor": 30820, "sc": 1000, "steps": [{"kind": "confirm", "name": "booth", "target": "booth",
                                                     "goal": [0, 300], "expect": "choice"}]}]
    for then, want in (("flicker", "reached"), ("stay", "V4")):
        fake = FakeGame(game)
        pred = _o2_pred(booth, choices=[_o2_booth_rule()], beats=["booth"])
        stop = threading.Event()
        after = ((lambda f: (setattr(f, "control", False), flicker_then_end(f))) if then == "flicker"
                 else (lambda f: None))
        with session(game, fake) as g:
            _o2_start(g, fake, at=(0, -400))
            _o1_director(fake, stop, [
                (lambda f: _o1_confirmed_near(f, 0, 300, reach=100), lambda f: f.scene(dict(_O2_BOOTH_CHOICE))),
                (lambda f: f.answered == [0] and f.control and not f._beats, after)])
            try:
                if want == "reached":
                    out = _o2_drive(g, pred)
                    assert out["end"] == "reached" and out["beats"] == {"booth": True}, (then, out)
                else:
                    with pytest.raises(SD.RouteVoid, match="after the cell's last step") as err:
                        _o2_drive(g, pred)
                    assert (err.value.v, err.value.by) == ("V4", "game"), err.value
            finally:
                stop.set()


def test_o2_step_of_refuses_a_step_its_executor_cannot_run():
    """The review's finding 8: step_of refuses (ValueError) what an executor would die on mid-run -- a trigger with
    neither target nor until, a crossing without ``to`` or ``target``, a Confirm without ``expect`` (or one it cannot
    wait for), a wait without ``sc``, a goal that is no point, an empty or unknown ``until``, a region nobody
    registered -- and the driver refuses a table holding one before it walks, as it refuses a start place its visit
    order lacks. Break: accept a trigger with neither (x_trigger then reads step["until"]: KeyError after the walk)."""
    SD = _segment_modules()
    pred = _o2_pred([])
    ok = {"cross": _o2_cross(), "leave_now": _o2_cross(kind="leave_now"),
          "trigger": {"kind": "trigger", "until": {"x_le": 0}, "goal": [0, 0]},
          "confirm": {"kind": "confirm", "target": "booth", "goal": [0, 300], "expect": "choice"},
          "wait_sc": {"kind": "wait_sc", "goal": [0, 0], "sc": 1153, "wait_s": 5}}
    for s in ok.values():
        SD.step_of(pred, s)
    drop = lambda s, k: {x: v for x, v in s.items() if x != k}                  # noqa: E731
    bad = [({"kind": "trigger", "goal": [0, 0]}, "needs a target or an until"),
           (drop(ok["cross"], "to"), "needs \\['to'\\]"), (drop(ok["leave_now"], "target"), "needs \\['target'\\]"),
           (drop(ok["confirm"], "expect"), "needs \\['expect'\\]"), (dict(ok["confirm"], expect="page"), "expect is"),
           (drop(ok["wait_sc"], "sc"), "needs \\['sc'\\]"), (dict(ok["cross"], goal=[0]), "goal is a point"),
           (dict(ok["trigger"], until={}), "until is a non-empty"), (dict(ok["trigger"], until={"y_le": 0}), "x\\|z"),
           (dict(ok["cross"], target="nowhere"), "no registered region"),
           (dict(ok["cross"], avoid=["nowhere"]), "no registered region")]
    for s, why in bad:
        with pytest.raises(ValueError, match=why):
            SD.step_of(pred, s)

    def drive_of(p):
        return SD._Drive(None, p, "S", [], deadline=0, floor_for=None, prior_for=None, progress=None, end_fields=None,
                         observe=None, forbid_live=False)
    drive_of(_o2_pred([{"donor": 30820, "sc": 1000, "steps": [ok["trigger"]]}]))
    with pytest.raises(ValueError, match="needs a target or an until"):
        drive_of(_o2_pred([{"donor": 30820, "sc": 1000, "steps": [bad[0][0]]}]))
    with pytest.raises(ValueError, match="not in the route's visit order"):
        drive_of(_o2_pred([], visits=[30821]))


# ---- O2 itself (studies/story-trace/o2_alexandria.py; research/o2_design.md section 9, PART C). The text rule is the
# lead's ruling on the uk text mis-pick as one pure function; P-LANG pins the session's language; the freeze refuses
# to overwrite; the draft's members are the built campaign's.

def _o2_module():
    sys.path.insert(0, str(REPO / "studies" / "story-trace"))
    import o2_alexandria as A
    return A


_O2_LANGS = ("us", "uk", "fr", "gr", "it", "es", "jp")


def _o2_stock_text():
    """Seven distinct stock texts, one per language (the English two differing by a UK spelling, as block 33's do)."""
    return {L: f"[{L}] block 33 -- the colour of the {L} text".encode("utf-8") for L in _O2_LANGS}


def test_o2_text_rule_reads_every_language_equal_as_ok():
    """The lead's ruling (research/o2_design.md 0.1, 6.1): once the kit fix lands and the build is regenerated, every
    shipped language is byte-equal to its own stock asset and the rule reads clean -- ok, seven ok lines, no
    KNOWN-KIT-DEFECT and no FAIL, with no code change. Break: compare against the us asset only."""
    A = _o2_module()
    stock = _o2_stock_text()
    ok, lines = A.text_rule(stock, dict(stock), "us")
    assert ok and len(lines) == 7 and all(" ok: " in ln for ln in lines), lines
    detail = A.text_detail(lines)
    assert detail.startswith("KNOWN-KIT-DEFECT 0, FAIL 0, 7 byte-equal of 7") and A.defect_lines(detail) == []


def test_o2_text_rule_counts_a_foreign_copy_as_known_kit_defect():
    """A build older than master's per-language text pick (aa627d52) ships uk as stock US text (O2's first build did,
    until its chain was rebuilt from repaired sidecars). Not the
    session language, and byte-equal to ANOTHER language's stock asset: a named, counted KNOWN-KIT-DEFECT line -- the
    rule still reads ok (no FAIL), never silently, and the CLI's line reads back from the detail. The line names the
    cause as it stands (a build to regenerate, or sidecars to repair), never a picker line or a fix still to come.
    Break: count a foreign copy as ok."""
    A = _o2_module()
    stock = _o2_stock_text()
    ok, lines = A.text_rule(stock, dict(stock, uk=stock["us"]), "us")
    assert ok, lines
    defects = [ln for ln in lines if ln.startswith("KNOWN-KIT-DEFECT")]
    assert len(defects) == 1 and defects[0].startswith("KNOWN-KIT-DEFECT uk: ships stock us"), lines
    assert "predates the per-language text pick (aa627d52)" in defects[0], defects
    assert "tools/refresh_verbatim_text.py" in defects[0] and "dialogue.py:" not in defects[0], defects
    assert not [ln for ln in lines if ln.startswith("FAIL")], lines
    detail = A.text_detail(lines)
    assert detail.startswith("KNOWN-KIT-DEFECT 1, FAIL 0, 6 byte-equal of 7") and A.defect_lines(detail) == defects


def test_o2_text_rule_fails_the_session_language():
    """The session reads us: a us file that is not stock us is a hard FAIL, even when it is another language's
    stock asset (the mirror of today's defect). Break: let the session language fall through to the foreign-copy
    rule (it would read as a KNOWN-KIT-DEFECT)."""
    A = _o2_module()
    stock = _o2_stock_text()
    ok, lines = A.text_rule(stock, dict(stock, us=stock["uk"]), "us")
    assert not ok, lines
    assert [ln for ln in lines if ln.startswith("FAIL")] == [next(ln for ln in lines if ln.startswith("FAIL us"))]
    assert not [ln for ln in lines if ln.startswith("KNOWN-KIT-DEFECT")], lines


def test_o2_text_rule_fails_garbage():
    """A file that is no language's stock asset is a hard FAIL in any language -- only a byte-equal foreign copy is
    the known defect. Break: call any foreign-language mismatch a KNOWN-KIT-DEFECT."""
    A = _o2_module()
    stock = _o2_stock_text()
    ok, lines = A.text_rule(stock, dict(stock, fr=b"no language's text"), "us")
    assert not ok and [ln for ln in lines if ln.startswith("FAIL")][0].startswith("FAIL fr: ships "), lines
    assert "no language's stock asset" in lines[2] and not [ln for ln in lines if "KNOWN-KIT-DEFECT" in ln], lines


def test_o2_p_lang_reads_the_last_localization_line():
    """P-LANG (research/o2_design.md 6.2): the launch's Memoria.log names the language its text was LAST loaded in
    ("Updating text localization [...]", FF9TextTool.cs:395) -- a launch whose language changed reads its last line
    -- and Memoria.ini's [VoiceActing] ForceLanguage must be -1 or 0, read as the engine reads it (the last
    assignment; outside 0..6 is -1). English(UK) last, or ForceLanguage 1, fails. Break: read the FIRST line."""
    A = _o2_module()
    line = "29.09.2026 21:31:56 |M| Updating text localization [{}]\n"
    uk_then_us = line.format("English(UK)") + "... |M| other\n" + line.format("English(US)")
    us_then_uk = line.format("English(US)") + line.format("English(UK)")
    ini = "[VoiceActing]\n\t; ForceLanguage (default -1) -1: Use in-game setting\nEnabled = 0\nForceLanguage = {}\n"
    ok, detail, info = A.p_lang(uk_then_us, ini.format(-1))
    assert ok and info == {"log": "English(US)", "force": -1} and "(of 2)" in detail, (detail, info)
    assert not A.p_lang(us_then_uk, ini.format(-1))[0]
    assert A.p_lang(uk_then_us, ini.format(0))[0]
    ok, detail, info = A.p_lang(uk_then_us, ini.format(1))
    assert not ok and info["force"] == 1 and "forces another language" in detail, detail
    assert A.p_lang(uk_then_us, ini.format(9))[2]["force"] == -1               # the engine's clamp
    assert not A.p_lang(uk_then_us, ini.format(-1) + "[VoiceActing]\nForceLanguage = 4\n")[0]   # the LAST wins
    assert A.p_lang(uk_then_us, None)[2]["force"] == -1                        # no ini: the default
    assert not A.p_lang("", ini.format(-1))[0] and not A.p_lang(None, ini.format(-1))[0]


def test_o2_freeze_refuses_an_existing_file(tmp_path, monkeypatch):
    """The freeze (research/o2_design.md 0.1): the draft is written ONCE -- LF, sorted keys, its sha the bytes'
    -- and a second freeze onto the same file refuses, leaving it byte for byte; the CLI's --freeze refuses the same
    way. The lead freezes after the stock rehearsals: the real o2_predictions_v1.json is never touched here. The chain
    the draft reads its members from is a machine-local build (C:\\gd\\_ns_playtest\\o2), so it is given here: the
    rule is tested wherever the suite runs. Break: drop the existence check (the second write replaces the file)."""
    import hashlib
    A = _o2_module()
    chain = ({31220 + i: 100 + i for i in range(18)}, {31220 + i: f"O2_SYNTH_{100 + i}" for i in range(18)})
    monkeypatch.setattr(A, "chain_from_campaign", lambda *a, **k: chain)
    path = tmp_path / "o2_predictions_v1.json"
    sha = A.O2.freeze(path)
    data = path.read_bytes()
    assert sha == hashlib.sha256(data).hexdigest() and b"\r" not in data and data.endswith(b"\n")
    assert json.loads(data) == json.loads(json.dumps(A.draft_predictions()))
    assert data.decode("utf-8") == json.dumps(A.draft_predictions(), indent=1, sort_keys=True) + "\n"
    path.write_bytes(data + b" ")                          # the file as frozen, plus one byte a re-freeze would lose
    with pytest.raises(SystemExit, match="frozen"):
        A.O2.freeze(path)
    seg = A.O2Segment()
    seg.predictions = path
    with pytest.raises(SystemExit, match="frozen"):
        seg.main(["--freeze"])
    assert path.read_bytes() == data + b" "


def test_o2_draft_members_are_the_campaigns(tmp_path):
    """The draft's members and names are read from the built chain's campaign.toml (research/o2_design.md 1.5), and
    must be exactly {31220 + i: 100 + i for i in range(18)}; the manifest o2_forks.json carries the same members and
    names, and its deploy record is whole: ``deployed_at`` is set exactly when ``deployed`` is (the chain went live
    for session story-o2, so a pin to "not deployed" would read the lifecycle, not the members). A campaign with any
    other member is refused. Break: drop the assertion (the draft
    would freeze another chain). The chain is a machine-local build: where it is not, this SKIPS (and says so) --
    never a pass."""
    import tomllib
    A = _o2_module()
    if not (A.CHAIN_DIR / "campaign.toml").is_file():
        pytest.skip(f"the O2 chain is not built here ({A.CHAIN_DIR}): the draft reads its members from it")
    pred = A.draft_predictions()
    doc = tomllib.loads((A.CHAIN_DIR / "campaign.toml").read_text(encoding="utf-8"))
    assert pred["members"] == {str(31220 + i): 100 + i for i in range(18)}, pred["members"]
    assert pred["names"] == {str(f["id"]): f["name"] for f in doc["field"]}
    assert pred["start"] == {"S": 100, "F": 31220} and pred["members"][str(pred["start"]["F"])] == 100
    man = json.loads((A.MANIFEST).read_text(encoding="utf-8"))
    assert man["members"] == pred["members"] and man["names"] == pred["names"]
    assert man["deployed"] in (True, False) and (man["deployed_at"] is not None) == man["deployed"], man
    bad = tmp_path / "campaign.toml"
    text = (A.CHAIN_DIR / "campaign.toml").read_text(encoding="utf-8").replace("source = 117", "source = 61")
    bad.write_text(text, encoding="utf-8")
    with pytest.raises(AssertionError, match="not the design's"):
        A.chain_from_campaign(bad)


def test_o2_rehearse_plumbing_on_the_fake(game):
    """C3 (research/o2_design.md 7): one rehearsal stage on a fake two-field route, chosen by ``O2_STAGE`` as a launch
    chooses it (another stage, which would run too, does not): the capabilities (P-LANG reading the launch's own
    Memoria.log and Memoria.ini), New Game, the raw warp at the stage's entrance and scenario, the beat-table driver
    with the recorder on every poll -- an arrival scene (the stage's "movie"), a booth Confirm and its choice, the
    crossing into the end field -- the trace collected, end_run to the title, and o2_rehearsal.json holding every
    section of 7.2: control grants, steps, choices (logged and published), pages, the press/watch evidence, the NPC
    track and its summary, the longest no-progress stretch, the movie's arrival/first page/fps, the end (its state
    and end_run's result) and the trace summary; the rehearsal report prints them. Break: drop the recorder's grants."""
    A = _o2_module()
    import o2_rehearse as R
    (game / "x64" / "Memoria.log").write_text(
        "30.09.2026 10:00:00 |M| Updating text localization [English(US)]\n", encoding="utf-8")
    (game / "Memoria.ini").write_text("[VoiceActing]\nForceLanguage = -1\n", encoding="utf-8")
    stages = {"R-TEST": {"field": 30820, "entrance": 102, "sc": 1000, "end": [30810], "runs": 1, "run_s": 90,
                         "cost_s": 5, "movie": {"donor": 30820}, "settles": "the plumbing"},
              "R-OTHER": {"field": 30821, "entrance": 0, "sc": 1150, "end": [30810], "runs": 1, "run_s": 5,
                          "cost_s": 1, "settles": "never run: O2_STAGE names R-TEST"}}
    assert R.select(stages, env={"O2_STAGE": "R-TEST"}) == ["R-TEST"]
    assert R.select(stages, env={}) == ["R-OTHER", "R-TEST"] and R.select(stages, 30821, env={}) == ["R-OTHER"]
    assert R.select(R.STAGES, 115, env={}) == ["R-115"] and "R-103" not in R.select(R.STAGES, env={})
    assert R.select(R.STAGES, env={})[0] == "R-115"            # F1's climb, the go/no-go, runs first
    with pytest.raises(ValueError, match="no stage"):
        R.select(stages, env={"O2_STAGE": "R-NONE"})
    tracks = [{"donor": 30820, "sid": 7, "name": "Jack", "lookout": [-300, 0]}]
    table = [{"donor": 30820, "sc": 1000, "watch": [{"sid": 7, "name": "Jack", "radius": "range_r"}],
              "steps": [{"kind": "confirm", "name": "booth", "target": "booth", "goal": [0, 300], "expect": "choice"},
                        _o2_cross()]}]
    pred = _o2_pred(table, choices=[_o2_booth_rule()], beats=["booth"], end_state={"Global.UInt16[0]": 1000})
    fake = FakeGame(game)
    fake.regions = {30820: [{"zone": _O2_EXIT, "to": 30810, "arrive": (0, 0)}]}
    fake.exit_frames = 50
    fake.blockers = {30820: [{"x": -500.0, "z": -500.0, "r": 30.0, "range_r": 100.0, "sid": 7}]}
    stop = threading.Event()

    def arrive(f):
        f.control = False
        f.player = [0.0, 0.0, -400.0]
        f.script_store(0, 0, 30, 191 >> 3, "Bit", 0, bit=191)             # the start row: 30820's Main_Init
        time.sleep(0.8)                                                   # the movie: nothing published changes
        f.scene("Vivi\n“...”", "Puck\n“Hey, over here!”")
    with session(game, fake) as g:
        boot(g)
        assert g.restore_baseline()[0], "a launch starts at the title"
        g._axes[30820] = _prior()
        _o1_director(fake, stop, [
            (lambda f: f.field_id == 30820 and f.story_on, arrive),
            (lambda f: _o1_confirmed_near(f, 0, 300, reach=100), lambda f: f.scene(dict(_O2_BOOTH_CHOICE)))])
        try:
            R.run(g, stages=stages, pred=pred, floor_for=lambda d, closed: _flat_bgi(), prior_for=lambda d: _prior(),
                  stock=lambda fid: None, recovery=30821, tracks=tracks, env={"O2_STAGE": "R-TEST"})
        finally:
            stop.set()
        title = g.state.ui_state
    run_dir = game / "run"
    doc = json.loads((run_dir / "o2_rehearsal.json").read_text(encoding="utf-8"))
    assert list(doc["stages"]) == ["R-TEST"] and doc["stages_run"] == ["R-TEST"] and doc.get("finished"), doc.keys()
    assert all(c[0] for c in doc["capabilities"]) and any(c[1].startswith("P-LANG") for c in doc["capabilities"])
    rec = doc["stages"]["R-TEST"][0]
    assert rec["outcome"]["end"] == "reached", rec["outcome"]
    for section in ("grants", "steps", "choices", "published_choices", "pages", "evidence", "tracks", "track_summary",
                    "latency", "no_progress", "mbg101", "end", "trace"):
        assert section in rec, section
    assert rec["grants"] and all({"t", "frame", "field", "sc", "x", "z", "y", "fps"} <= set(x) for x in rec["grants"])
    assert [(s["kind"], s["outcome"]) for s in rec["steps"]] == [("confirm", "done"), ("cross", "done")], rec["steps"]
    assert [(c["index"], c["selected"], c["rule"]) for c in rec["choices"]] == [(0, 0, 0)], rec["choices"]
    assert rec["published_choices"] and rec["published_choices"][0]["options"][1:] == ["eek into the ticket booth",
                                                                                      "Cancel"]
    assert [p["text"] for p in rec["pages"]] == ["Vivi\n“...”", "Puck\n“Hey, over here!”"], rec["pages"]
    assert {"press", "watch"} <= set(rec["evidence"]) and rec["evidence"]["press"] and rec["evidence"]["watch"]
    jack = rec["track_summary"].get("30820.7") or {}
    assert rec["tracks"].get("30820.7") and jack.get("name") == "Jack", rec["track_summary"]
    assert (jack.get("min_dist") or 0) > 100 and "lookout_contact_frame" in jack, jack
    assert rec["no_progress"]["longest_s"] >= 0.5 and rec["no_progress"]["where"]["field"] == 30820, rec["no_progress"]
    mv = rec["mbg101"]
    assert None not in (mv["arrival_frame"], mv["first_page_frame"]) and mv["first_page_frame"] > mv["arrival_frame"], mv
    assert rec["end"]["end_state"] == {"Global.UInt16[0]": 1000}, rec["end"]
    assert rec["end"]["end_run"]["ok"] and rec["end"]["end_run"]["title"] and title == "Title", rec["end"]
    tr = rec["trace"]
    assert tr["start"] is not None and [x[1:] for x in tr["residue_before"]] == [[0, 0, 232], [1, 0, 3], [2, 0, 102]]
    assert (run_dir / rec["trace_file"]).is_file() and (run_dir / rec["log_file"]).is_file()
    report = A.rehearsal_report(run_dir)
    for want in ("== R-TEST: warp 30820 102 1000", "grant: field 30820", "step (30820, 1000) #0 confirm",
                 "choice at frame", "pages: ", "evidence: ", "track 30820.7", "longest no-progress", "mbg101:",
                 "end: state", "trace: start line"):
        assert want in report, (want, report[:1500])


# ---- O3's harness additions (research/o3_design.md section 3, PART B). H9: the FakeGame's opt-in knobs -- a scripted
# battle end, the battle exit in the engine's four phases, a warp refused off the field, a warp that lands without
# control, the soft reset where the engine fires it, a movie beat with its skip dialog -- each absent by default, so no
# test before them changes. H7 and H8 are the two battle verbs the battle beat needs; S4 (B4) is the battle beat.

#: King Leo's latch (BSC_TH_E002 e1 t1 [587]: his own cur.hp <= 10000 of 10186), as `battle_script_end` models it.
_O3_LEO_END = {"unit": "King Leo", "hp_raw_le": 10000, "result": 2, "after_frames": 20}
#: SkipMovieDialog (System.strings 0366, US), its cursor on No (ETb.sChoose = 1), as a movie beat's ``skip``.
_O3_SKIP = {"header": "Do you want to skip\nthe movie?", "options": ["Yes", "No"], "default": 1}


def _o3_unit(slot, uid, name, hp, *, player=False):
    return {"slot": slot, "id": uid, "player": player, "name": name, "hp": hp, "hp_max": hp, "hp_raw": hp,
            "hp_max_raw": hp, "mp": 0, "mp_max": 0, "atb": 0, "atb_max": 6000, "can_act": True, "alive": True,
            "targetable": True, "level": 1, "status": "0"}


def _o3_units(leo_hp=10186, *, minions=True):
    """Battle 338's roster on the fake: Zidane (9999 HP: 62 sets the party's), King Leo FIRST among the enemies (the
    default policy attacks him), and -- unless ``minions`` is False -- Zenero (32) and Benero (28)."""
    units = [_o3_unit(0, 1, "Zidane", 9999, player=True), _o3_unit(4, 16, "King Leo", leo_hp)]
    if minions:
        units += [_o3_unit(5, 32, "Zenero", 32), _o3_unit(6, 64, "Benero", 28)]
    return units


def _o3_end_on_the_fake(fake, result):
    """End the fake's battle with ``result`` on ITS OWN thread, at its next frame (the scripted-end slot): an end a test
    thread runs itself can be published half-done (the scene gone with the UI still BattleHUD)."""
    fake._script_end = (fake.frame + 1, int(result))


class _PubFake(FakeGame):
    """The fake with every PUBLISHED state's battle facts kept, in order: ``(frame, field, result, active, ui,
    control)`` -- what no reader of the channel can promise to have seen whole."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.pubs: list = []

    def _publish(self, force: bool = False) -> None:
        before = self.publish_frame
        super()._publish(force)
        if force or self.publish_frame != before:
            self.pubs.append((self.frame, self.field_id, self.battle_result, self.battle_active, self.ui_state,
                              self.control))


def test_fake_battle_script_end_ends_on_the_units_hp(game):
    """H9 ``battle_script_end`` (research/o3_design.md 3): King Leo's latch. The first time his ``hp_raw`` is at or below
    10000 after a command resolves, the battle ends ``after_frames`` later with result 2, whoever is standing: one
    Attack (260) takes his 10186 to 9926, and the fight ends with him and both minions alive. The control: the same
    battle with the latch on a unit that is not in it never ends by script, and the fight runs out of its turns.
    Break: drop the latch after a command resolves (the fight runs out of its turns)."""
    for unit, ends in (("King Leo", True), ("Nobody", False)):
        fake = FakeGame(game)
        fake.enemy_hit, fake.atb_gain = 0, 400
        fake.battle_script_end = dict(_O3_LEO_END, unit=unit)
        with session(game, fake) as g:
            boot(g)
            g.warp(30821)
            fake.start_battle(338, units=_o3_units())
            published(g, lambda s: s.in_battle and s.battle.get("scene") == 338)
            if ends:
                assert g.fight(timeout=30.0, max_turns=6, finish=False) == 2
                leo = next(u for u in fake.battle_units if u["name"] == "King Leo")
                assert 0 < leo["hp_raw"] <= 10000, leo
                assert all(u["alive"] for u in fake.battle_units), "the scripted end: whoever is standing"
                assert fake.battle_result == 2 and not fake.battle_active and fake.ui_state == "FieldHUD"
            else:
                with pytest.raises(HarnessError, match="took 2 turns without reaching a result"):
                    g.fight(timeout=30.0, max_turns=2, finish=False)
                assert fake.battle_active and fake.battle_result == 0 and len(fake.battle_commands) == 2


def test_fake_battle_exit_runs_the_engines_four_phases(game):
    """H9 ``battle_exit`` (research/o3_design.md 0.2 #8, 11.2 #4): a scripted end's every PUBLISHED state, in the
    engine's order -- the FADE (the end's result 2 at the battle's own field, in the battle, BattleHUD); the OVER
    FRAME and BattleResult (the result folded to 1 AND the exit field, together, still in the battle); the LOAD (the
    scene gone, the UI still reading BattleResult); then FieldHUD in the exit field with control off and a new visit.
    fight() returns 2, read in the fade; the first in-battle sample at the exit field holds result 1, and NO published
    sample pairs the exit field with result 2. Break: flip the field at the fade (the exit field with result 2)."""
    fake = _PubFake(game)
    fake.enemy_hit, fake.atb_gain = 0, 400
    fake.battle_script_end = dict(_O3_LEO_END)
    fake.battle_exit = {"field": 30810, "fade_frames": 120, "result_frames": 60, "load_frames": 80,
                        "arrive_control": False}
    with session(game, fake) as g:
        boot(g)
        g.warp(30821)
        visit = fake._visit
        fake.start_battle(338, units=_o3_units())
        st = published(g, lambda s: s.in_battle and s.battle.get("scene") == 338)
        assert g.fight(timeout=30.0, max_turns=6, finish=False) == 2 and g.last_fight["result"] == 2
        read = g.states_since(st.frame)
        end = g.wait_for(lambda s: s.ui_state == "FieldHUD" and not s.in_battle, timeout=20.0, what="the exit field")
    assert end.field_id == 30810 and end.control is False and fake._visit == visit + 1, end
    assert [e["phase"] for e in fake.exits] == ["fade", "over", "load", "field"], fake.exits
    assert any((r.get("battle") or {}).get("result") == 2 and (r.get("field") or {}).get("id") == 30821
               for r in read), "fight() read its 2 in the fade, at the battle's own field"

    def phase(p):
        frame, field, result, active, ui, control = p
        if active and (field, result, ui) == (30821, 2, "BattleHUD"):
            return "fade"
        if active and (field, result, ui) == (30810, 1, "BattleResult"):
            return "result"
        if not active and (field, result, ui) == (30810, 1, "BattleResult"):
            return "load"
        if not active and (field, ui, control) == (30810, "FieldHUD", False):
            return "field"
        return f"stray {p}"
    tags = [phase(p) for p in fake.pubs if p[0] >= fake.exits[0]["frame"]]
    runs = [t for i, t in enumerate(tags) if i == 0 or t != tags[i - 1]]
    assert runs == ["fade", "result", "load", "field"], runs
    assert not [p for p in fake.pubs if p[1] == 30810 and p[2] == 2], "the exit field paired with result 2"


def test_fake_warp_refuses_off_the_field_when_told(game):
    """H9 ``warp_field_only`` (research/o3_design.md 0.2 #9): the agent refuses a warp outside FieldHUD ("warp refused
    (not on a field?)") -- from inside a battle the warp raises at once, writes nothing (the scenario and entrance
    bytes stand) and moves nothing; from the field it warps. The control: the default fake warps from inside the
    battle (today's). Break: drop the refusal."""
    for refuses in (True, False):
        fake = FakeGame(game)
        fake.warp_field_only = refuses
        with session(game, fake) as g:
            boot(g)
            g.warp(30820)                                     # from the field HUD: either way
            g.start_battle(105)
            if refuses:
                with pytest.raises(HarnessError, match=r"warp refused \(not on a field\?\)"):
                    g.send("warp 30821 0 1155")
                st = g.state
                assert st.field_id == 30820 and st.in_battle and st.ui_state == "BattleHUD", st
                assert bytes(fake.story_bytes[0:4]) == bytes(4), "a refused warp wrote its scenario or entrance"
            else:
                g.send("warp 30821 0 1155")
                published(g, lambda s: s.field_id == 30821)
                assert bytes(fake.story_bytes[0:4]) == bytes((0x83, 0x04, 0, 0))


def test_fake_warp_arrives_without_control_when_told(game):
    """H9 ``warp_arrive_control`` (research/o3_design.md 11.2 #3): False -- a warp lands with control OFF, as the
    engine's field start leaves it in 61-63. Session.warp() there times out in its wait_playable (in the game it would
    hang 60 s a warp: the F-SMOKE trap); start_run's own shape -- the raw warp, then a wait for the field and FieldHUD
    -- lands. The control: the default fake hands control over and Session.warp() returns playable. Break: ignore the
    knob (Session.warp() returns)."""
    fake = FakeGame(game)
    fake.warp_arrive_control = False
    with session(game, fake) as g:
        boot(g)
        with pytest.raises(HarnessError, match="control at a known position"):
            g.warp(30820, timeout=2.0)
        g.send("warp 30821 0 1155")
        st = g.wait_for(lambda s: s.field_id == 30821 and s.ui_state == "FieldHUD", timeout=10.0, what="the field")
        assert st.control is False and st.scenario == 1155, st
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        assert g.warp(30820, timeout=10.0).control is True


def test_fake_soft_reset_follows_the_engines_ui_states(game):
    """H9 ``soft_reset_ui`` (research/o3_design.md 0.2 #9, 11.2 #1): with the ENGINE's set the combo resets from
    BattleHUD mid-fight -- the title, the battle gone with the scene -- and is swallowed in BattleResult (a battle's
    end sequence) and while a movie plays, its skip dialog up or not (MBG marked played); with the default set
    (today's) it is swallowed in BattleHUD too. Break: keep the old literal pair (BattleHUD swallowed under the
    engine's set)."""
    from harness.fakegame import SOFT_RESET_ENGINE_UI

    def battle(ui):
        fake = FakeGame(game)
        if ui is not None:
            fake.soft_reset_ui = ui
        return fake
    fake = battle(SOFT_RESET_ENGINE_UI)                      # the engine's set, mid-fight: the title
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g.start_battle(105)
        st = g.soft_reset(timeout=10.0)
        assert st.ui_state == "Title" and not st.in_battle and fake.soft_resets == 1, st
    fake = battle(SOFT_RESET_ENGINE_UI)                      # ...in BattleResult: swallowed
    fake.battle_exit = {"field": 30821, "fade_frames": 5, "result_frames": 10 ** 6, "load_frames": 5}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g.start_battle(105)
        _o3_end_on_the_fake(fake, 2)
        published(g, lambda s: s.ui_state == "BattleResult" and s.in_battle)
        with pytest.raises(HarnessError, match="did not reach the title"):
            g.soft_reset(timeout=2.0)
        assert fake.soft_resets == 0 and fake.ui_state == "BattleResult"
    fake = battle(SOFT_RESET_ENGINE_UI)                      # ...a movie playing, then its skip dialog: swallowed
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        fake.scene({"movie": 10 ** 6, "skip": dict(_O3_SKIP)}, control=False)
        published(g, lambda s: s.ui_state == "FieldHUD" and not s.dialog_open and not s.control)
        with pytest.raises(HarnessError, match="did not reach the title"):
            g.soft_reset(timeout=2.0)
        g.press("confirm", 4)                                # a stray Confirm: the movie's skip dialog
        published(g, lambda s: s.choice is not None)
        with pytest.raises(HarnessError, match="did not reach the title"):
            g.soft_reset(timeout=2.0)
        assert fake.soft_resets == 0 and fake._movie is not None
    fake = battle(None)                                      # today's default set, mid-fight: swallowed
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g.start_battle(105)
        with pytest.raises(HarnessError, match="did not reach the title"):
            g.soft_reset(timeout=2.0)
        assert fake.soft_resets == 0 and fake.ui_state == "BattleHUD"


def _o3_until(cond, timeout=10.0):
    """Wait on the FAKE's own state (a condition no published key carries), polling."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if cond():
            return
        time.sleep(0.005)
    raise AssertionError("the fake never reached the condition")


def test_fake_movie_beat_holds_and_offers_the_skip_dialog(game):
    """H9's movie beat (research/o3_design.md 2.5, H9): a scene's movie holds -- no dialog, no control, FieldHUD -- for
    its frames; a Confirm during it opens the skip dialog (SkipMovieDialog's text, its cursor on the default, No);
    answering the default resumes the movie for EXACTLY the frames it had left, and the page after it opens when they
    run out; answering the other option ends it at once. Break: restart the movie after its dialog (it plays more
    frames than it has)."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        for answer in ("default", 0):
            fake.scene("Narrator\n“Before”", {"movie": 480, "skip": dict(_O3_SKIP)}, "Narrator\n“After”",
                       control=False)
            published(g, lambda s: s.dialog_open and "Before" in s.text)
            g.press("confirm", 3)                            # the page before the movie
            st = published(g, lambda s: not s.dialog_open)
            assert st.ui_state == "FieldHUD" and not st.control and fake._movie is not None, st
            _o3_until(lambda: fake.movies[-1]["played"] >= 60)
            g.press("confirm", 4)                            # a stray Confirm: the skip dialog
            st = g.wait_for(lambda s: g._choice_ready(s) and s.choice.get("selected") == 1, timeout=5.0,
                            what="the skip dialog, ready")
            assert st.choice["options"] == ["Do you want to skip\nthe movie?", "Yes", "No"], st.choice
            if answer == "default":
                took = g._take_default_choice(st)
                assert took is not None and took["index"] == 1, took
            else:
                g.choose(0)
            g.wait_for(lambda s: s.dialog_open and "After" in s.text, timeout=20.0, what="the page after the movie")
            mv = fake.movies[-1]
            if answer == "default":
                assert (mv["played"], mv["skips"], mv["ended"]) == (480, 1, "played"), mv
                assert mv["end"] - mv["start"] > 480, mv              # the dialog's frames on top of the movie's
            else:
                assert mv["played"] < 480 and (mv["skips"], mv["ended"]) == (1, "skipped"), mv
            assert fake._movie is None
            g.press("confirm", 3)                            # the page after it
            published(g, lambda s: not s.dialog_open)
    assert fake.answered == [1, 0], fake.answered


def test_fake_movie_skip_dialog_skips_on_choice_zero_only(game):
    """The skip dialog as the ENGINE answers it, never as a fixture says (FieldHUD.cs): its cursor always starts on No
    -- OnKeyConfirm sets ``ETb.sChoose = 1`` (:280) whatever the dialog's text -- and OnKeyConfirmAfterDialogHidden
    skips on choice 0 ALONE (:430); any other answer re-arms the hit area and the movie resumes (:434-440). So a movie
    whose skip names another cursor (``default`` 0: the sign of the skip flipped) is refused when the scene is built,
    nothing staged; and with a three-line dialog in the skip slot (the driver's tests stage dialogs the reader must
    refuse there) and no ``default`` given, the cursor opens on 1, line 2 resumes the movie for exactly the frames it
    had left and line 0 ends it. Break: end the movie on any answer but the fixture's default (line 2 then skips)."""
    fake = FakeGame(game)
    three = {"header": "Do you want to skip\nthe movie?", "options": ["Yes", "No", "Later"]}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        with pytest.raises(ValueError, match=r"ETb\.sChoose = 1, FieldHUD\.cs:280"):
            fake.scene({"movie": 480, "skip": dict(_O3_SKIP, default=0)}, "Narrator\n“After”", control=False)
        assert not fake._beats and fake._movie is None and not fake.movies and fake.control, "the refused scene staged"
        for line, ended in ((2, "played"), (0, "skipped")):
            fake.scene({"movie": 480, "skip": dict(three)}, "Narrator\n“After”", control=False)
            published(g, lambda s: s.ui_state == "FieldHUD" and not s.dialog_open and not s.control)
            _o3_until(lambda: fake._movie is not None and fake.movies[-1]["played"] >= 60)
            g.press("confirm", 4)                            # a stray Confirm: the skip dialog, its cursor on No
            st = g.wait_for(lambda s: g._choice_ready(s), timeout=5.0, what="the skip dialog, ready")
            assert st.choice["selected"] == 1 and st.choice["options"][1:] == three["options"], st.choice
            g.choose(line)
            g.wait_for(lambda s: s.dialog_open and "After" in s.text, timeout=20.0, what="the page after the movie")
            mv = fake.movies[-1]
            assert (mv["skips"], mv["ended"]) == (1, ended), (line, mv)
            assert mv["played"] == 480 if ended == "played" else mv["played"] < 480, (line, mv)
            g.press("confirm", 3)                            # the page after it
            published(g, lambda s: not s.dialog_open)
    assert fake.answered == [2, 0], fake.answered


def test_fake_scene_copies_its_beats(game):
    """FakeGame.scene() COPIES each dict beat (the review, research/o3_design.md 11.7 #11): a movie beat keeps its
    countdown (``_left``) on the beat, so one dict staged in two scenes must play twice -- two ``movies`` rows, each its
    whole frames, each followed by its page -- and the caller's dict is left as it was given. Break: keep the caller's
    dicts (the second scene's movie is already spent: one ``movies`` row, and its page at once)."""
    fake = FakeGame(game)
    movie = {"movie": 60}
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        for _ in range(2):
            fake.scene(movie, "Narrator\n“After”", control=False)
            g.wait_for(lambda s: s.dialog_open and "After" in s.text, timeout=10.0, what="the page after the movie")
            g.press("confirm", 3)
            published(g, lambda s: not s.dialog_open)
    assert [(m["frames"], m["played"], m["ended"]) for m in fake.movies] == [(60, 60, "played")] * 2, fake.movies
    assert movie == {"movie": 60}, movie


def test_fight_raises_fight_timeout_without_a_result(game):
    """H7 (research/o3_design.md 3): fight()'s two no-result exits raise FightTimeout -- a HarnessError, with the
    messages they always carried, its ``kind`` the bound that ran out -- and record ``last_fight`` either way, now with
    ``timed_out``, ``seconds`` and ``tutorials``. A battle no attack can end (one enemy of 10^7 HP, no scripted end):
    ``max_turns=0`` raises at the FIRST command prompt, before any command -- no battlecmd executed, the fake still in
    BattleHUD with result 0 (R-BATTLE-VOID's way to stop mid-fight); ``max_turns=1`` raises naming the turns;
    ``timeout=2`` naming the timeout. Break: raise the plain HarnessError on either exit."""
    from harness import FightTimeout
    fake = FakeGame(game)
    fake.enemy_hit, fake.atb_gain = 0, 400
    with session(game, fake) as g:
        boot(g)
        g.warp(30821)
        fake.start_battle(338, units=_o3_units(10 ** 7, minions=False))
        published(g, lambda s: s.in_battle and s.battle.get("scene") == 338)
        with pytest.raises(FightTimeout, match="took 0 turns without reaching a result") as err:
            g.fight(timeout=30.0, max_turns=0, finish=False)
        st = g.state
        assert err.value.kind == "turns" and isinstance(err.value, HarnessError)
        assert not [s for s in fake.executed if s[0] == "battlecmd"] and fake.battle_commands == []
        assert st.in_battle and st.ui_state == "BattleHUD" and st.battle_result == 0, st
        lf = g.last_fight
        assert (lf["turns"], lf["result"], lf["timed_out"], lf["tutorials"]) == (0, 0, True, 0), lf
        assert lf["epoch"] == st.battle_epoch and lf["seconds"] >= 0, lf
        with pytest.raises(FightTimeout, match="took 1 turns without reaching a result") as err:
            g.fight(timeout=30.0, max_turns=1, finish=False)
        assert err.value.kind == "turns" and g.last_fight["turns"] == 1 and g.last_fight["timed_out"] is True
        assert len(fake.battle_commands) == 1
        with pytest.raises(FightTimeout, match=r"did not reach a result within 2s \(\d+ turn\(s\) taken\)") as err:
            g.fight(timeout=2.0, finish=False)
        assert err.value.kind == "timeout" and g.last_fight["timed_out"] is True, g.last_fight
        assert g.last_fight["seconds"] >= 2.0 and g.last_fight["result"] == 0, g.last_fight


def test_fight_tells_a_vanished_battle_from_a_timeout(game):
    """H7's third exit (the review, research/o3_design.md 11.7 #2): the battle scene GOES with no result while both
    bounds still hold -- here the battle ends with result 0 on the fake's own thread, a second in (in the game: a soft
    reset or a crash to the title mid-fight, an engine path that leaves the result 0). FightTimeout kind "gone", its
    own message, ``timed_out`` False, raised at once and far inside its 60 s bound -- never "did not reach a result
    within 60s". No command prompt is ever up (no ATB), so nothing races the end. Break: one exit for both (kind
    "timeout", the timeout's message, ``timed_out`` True)."""
    from harness import FightTimeout
    fake = FakeGame(game)
    fake.enemy_hit, fake.atb_gain = 0, 0
    stop = threading.Event()
    with session(game, fake) as g:
        boot(g)
        g.warp(30821)
        fake.start_battle(338, units=_o3_units(10 ** 7, minions=False))
        published(g, lambda s: s.in_battle and s.battle.get("scene") == 338)
        start = fake.frame
        _o1_director(fake, stop, [(lambda f: f.frame >= start + 240, lambda f: _o3_end_on_the_fake(f, 0))])
        t0 = time.time()
        try:
            with pytest.raises(FightTimeout) as err:
                g.fight(timeout=60.0, finish=False)
        finally:
            stop.set()
        took = time.time() - t0
        st = g.state
    assert err.value.kind == "gone" and "went away with no result" in str(err.value), err.value
    assert "did not reach a result" not in str(err.value) and took < 20.0, (err.value, took)
    assert not st.in_battle and st.battle_result == 0, st
    lf = g.last_fight
    assert (lf["result"], lf["timed_out"], lf["turns"]) == (0, False, 0) and lf["seconds"] < 20.0, lf


def test_fight_counts_its_tutorials_and_seconds(game):
    """H7: ``last_fight`` counts the battle tutorial screens the call closed -- scene 336 opens one before its first
    command: 1 -- and the wall seconds it took, and reads ``timed_out`` False on a result; its old keys (turns, result,
    name, epoch) are all still there. Break: count no tutorial."""
    fake = FakeGame(game)
    fake.enemy_hit, fake.atb_gain = 0, 400
    fake.tutorial_scenes = {336}
    with session(game, fake) as g:
        boot(g)
        g.warp(30810)
        g.start_battle(336)
        published(g, lambda s: s.ui_state == "Tutorial")
        assert g.fight(timeout=60.0, finish=False) == 1
    lf = g.last_fight
    assert lf["tutorials"] == 1 and lf["seconds"] > 0 and lf["timed_out"] is False, lf
    assert (lf["result"], lf["name"]) == (1, "victory") and lf["turns"] >= 4 and lf["epoch"] > 0, lf


def test_leave_battle_stops_where_the_field_begins_and_logs_its_presses(game):
    """H8 (research/o3_design.md 3): ``leave_battle(stop_on_field=True)`` across H9's four-phase exit -- the fade, the
    over frame and BattleResult, then the LOAD lagging as BattleResult with the scene gone -- presses Confirm only while
    the battle scene is up: every recorded press was decided on a sample in the battle, none is executed after the
    scene went (beyond the one race a press decided just before it can lose), and it stops "scene-gone" with the UI
    still reading BattleResult. ``last_leave`` records each press's sample and where the loop ended. "Executed after"
    is counted, not timed: the loop samples before every press, so at most the ONE press already in flight when the
    scene goes can land after it, however slow the machine. The control: the default loop (O1's) presses on through
    the lag. Break: drop the stop (the loop presses into the loading field)."""
    got = {}
    for stop in (True, False):
        fake = _StampFake(game)
        fake.battle_exit = {"field": 30810, "fade_frames": 30, "result_frames": 240, "load_frames": 240,
                            "arrive_control": False}
        with session(game, fake) as g:
            boot(g)
            g.warp(30821)
            g.start_battle(105)
            _o3_end_on_the_fake(fake, 2)
            published(g, lambda s: s.battle_result == 2)
            ui = g.leave_battle(stop_on_field=stop) if stop else g.leave_battle()
            leave = g.last_leave
        gone = next(e["frame"] for e in fake.exits if e["phase"] == "load")
        pressed = [f for _t, f, s in fake.stamped if s[:2] == ["press", "confirm"]]
        got[stop] = (ui, leave, gone, pressed)
    ui, leave, gone, pressed = got[True]
    assert leave["presses"] and all(p["in_battle"] for p in leave["presses"]), leave
    assert all({"frame", "ui", "in_battle", "field", "result"} == set(p) for p in leave["presses"]), leave
    assert {p["ui"] for p in leave["presses"]} <= {"BattleHUD", "BattleResult"}, leave
    assert leave["stopped"] == "scene-gone" and ui == "BattleResult" == leave["ended"], leave
    assert pressed and len([f for f in pressed if f >= gone]) <= 1, (pressed, gone)
    assert len(pressed) == len(leave["presses"]), (pressed, leave)
    ui, leave, gone, pressed = got[False]
    assert len([p for p in leave["presses"] if not p["in_battle"]]) >= 3, leave        # the control: into the lag
    assert len([f for f in pressed if f >= gone]) >= 3, (pressed, gone)
    assert leave["stopped"] == "field" and ui == "FieldHUD", leave


def test_leave_battle_stops_at_its_timeout(game):
    """H8's ``timeout``, honoured (the review, research/o3_design.md 11.7 #1: it was never read). A battle whose
    BattleResult never hands over (``result_frames`` 10^6): with ``timeout`` 1 the loop stops "timeout" after about a
    second, before a Confirm, fewer than its 40 presses made; with ``timeout`` 0 it presses nothing. The control:
    the default bound (90 s) still lets the 40 Confirms run out ("presses"), as it always did. Break: drop the bound
    (every call presses all 40)."""
    got = {}
    for timeout in (1.0, 0.0, None):
        fake = FakeGame(game)
        fake.battle_exit = {"field": 30810, "fade_frames": 5, "result_frames": 10 ** 6, "load_frames": 5}
        with session(game, fake) as g:
            boot(g)
            g.warp(30821)
            g.start_battle(105)
            _o3_end_on_the_fake(fake, 2)
            published(g, lambda s: s.ui_state == "BattleResult" and s.in_battle)
            t0 = time.time()
            ui = g.leave_battle(stop_on_field=True) if timeout is None else \
                g.leave_battle(stop_on_field=True, timeout=timeout)
            got[timeout] = (ui, g.last_leave, time.time() - t0)
    ui, leave, took = got[1.0]
    assert leave["stopped"] == "timeout" and 0 < len(leave["presses"]) < 40 and ui == "BattleResult", leave
    assert 1.0 <= took < 10.0, took
    ui, leave, took = got[0.0]
    assert leave["stopped"] == "timeout" and leave["presses"] == [] and took < 5.0, (leave, took)
    ui, leave, took = got[None]
    assert leave["stopped"] == "presses" and len(leave["presses"]) == 40, leave


def test_leave_battle_records_presses_on_o1s_path(game):
    """H8: O1's shape -- a battle that ends in its own field with FieldHUD at once (no ``battle_exit``) -- through the
    DEFAULT loop: it presses Confirm while the battle is up, stops at the field and returns its UI state as it always
    did, and ``last_leave`` now records every press (its sample in the battle) and the stop ("field"). Break: record
    no press."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        boot(g)
        g.warp(30820)
        g.start_battle(105)
        stop = threading.Event()
        _o1_director(fake, stop, [(lambda f: sum(1 for s in f.executed if s[:2] == ["press", "confirm"]) >= 2,
                                   lambda f: _o3_end_on_the_fake(f, 1))])
        try:
            ui = g.leave_battle()
        finally:
            stop.set()
        leave = g.last_leave
    assert ui == "FieldHUD" and leave["ended"] == "FieldHUD" and leave["field"] == 30820, leave
    assert leave["stopped"] == "field" and len(leave["presses"]) >= 2, leave
    assert all(p["in_battle"] and p["ui"] == "BattleHUD" and p["field"] == 30820 and p["result"] == 0
               for p in leave["presses"]), leave
    assert fake.battle_result == 1 and not fake.exits, "O1's shape: today's end, in its own field"


# ---- O3's battle beat (studies/story-trace/segment_drive.py, S4; research/o3_design.md 2.1-2.6, PART B, B4), on the
# fake's fields as O3's places: 30820 is "61", 30821 "62", 30810 "63", and 30830 "64" -- the end, no member, never
# warped to (so not registered); the F side's members 31211-31213 are appended to the fixture's DictionaryPatch, as
# O1's pinning test appends its member. Every test models the engine where O3 needs it: a warp lands WITHOUT control
# and is refused off the field, the soft reset fires where the engine's does (H9), and 61-63's scenes never hand
# control back. A director thread stages the game: 61's pages, its exit into "62", 62's pages, battle 338 (King Leo's
# latch ends it; its exit runs the engine's four phases into "63", or wherever the test sends it), 63's pages, then
# its Field(64).

_O3_END = 30830
_O3_FIELDS = {"S": {61: 30820, 62: 30821, 63: 30810}, "F": {61: 31211, 62: 31212, 63: 31213}}
_O3_NAMES = {"31211": "O1_TH_BST", "31212": "O1_TH_STG", "31213": "O1_TSHP_TH_STG"}
_O3_ERROR = "Error Env Play()  Slot=1"


def _o3_row(**kw):
    """2.1's registry row on the fake's places: battle 338 in "62" at SC 1155, won [1, 2], landing in "63"."""
    return {"donor": 30821, "sc": 1155, "scene": 338, "won": [1, 2], "lands": 30810, "beat": "leo", "timeout_s": 60,
            "max_turns": 40, "land_s": 15, "land_cap_s": 30,
            "why": "62's Battle(0,338), on the fake: King Leo's latch ends it, its RunBattleCode(37,63) lands in 63",
            **kw}


def _o3_pred(**over):
    """O3's driver keys (research/o3_design.md 2.1, 4.1) on the fake's fields: no table; the registry row; the stop
    page; O1's skip-movie rule; route and visits 61 -> 62 -> 63; the end "64"; the members for the F side."""
    pred = {"version": 1, "start": {"S": 30820, "F": 31211}, "entrance": 0, "scenario": 1155,
            "end_field": _O3_END, "end_fields": [_O3_END], "route": [30820, 30821, 30810],
            "visits": [30820, 30821, 30810], "members": {"31211": 30820, "31212": 30821, "31213": 30810},
            "names": dict(_O3_NAMES),
            "budget": {"run_s": 120, "run_min_s": 1, "session_s": 600, "settle_s": 0.3, "no_progress_s": 60},
            "beats": ["leo"], "table": [], "naming": [], "forbidden": [], "end_state": {}, "regions": {},
            "hotspots": {}, "battles": [_o3_row()],
            "stop_pages": [{"match": "Env Play()", "why": "61-63's ambient error window 3 ('Error Env Play()  Slot=n')"}],
            "choices": [{"donor": None, "sc": None, "match": "want to skip", "pick": "default", "once": False,
                         "beat": None}]}
    pred.update(over)
    return pred


def _o3_fake(game, *, exit_to=None, cls=FakeGame, **exit_kw):
    """The fake as O3's tests model the engine (H9): warps land without control and are refused off the field, the
    soft reset fires in the engine's UI states, King Leo's latch ends battle 338, and -- with ``exit_to`` -- its exit
    runs the four phases into that field (``exit_kw`` overrides a phase's frames)."""
    from harness.fakegame import SOFT_RESET_ENGINE_UI
    fake = cls(game)
    fake.warp_arrive_control, fake.warp_field_only, fake.soft_reset_ui = False, True, SOFT_RESET_ENGINE_UI
    fake.enemy_hit, fake.atb_gain = 0, 400
    fake.battle_script_end = dict(_O3_LEO_END)
    if exit_to is not None:
        fake.battle_exit = {"field": exit_to, "fade_frames": 90, "result_frames": 90, "load_frames": 120,
                            "arrive_control": False, **exit_kw}
    return fake


def _o3_register(game):
    """The F side's members, registered as a deployed chain registers them (O1's pinning test's way)."""
    patch = game / "FF9CustomMap" / "DictionaryPatch.txt"
    patch.write_text(patch.read_text(encoding="utf-8")
                     + "".join(f"FieldScene {f} 11 {n} {n} 2\n" for f, n in _O3_NAMES.items()), encoding="utf-8")


def _o3_start(g, side="S"):
    """start_run's own start: New Game, then the RAW warp into "61" at entrance 0, SC 1155, and a wait for the field
    and FieldHUD -- never Session.warp(), whose wait_playable needs control 61-63 never give."""
    boot(g)
    start = _O3_FIELDS[side][61]
    g._check_field_id(start, "warp", True)
    g.send(f"warp {start} 0 1155")
    return g.wait_for(lambda s: s.field_id == start and s.ui_state == "FieldHUD", timeout=10.0, what=f"field {start}")


def _o3_idle(f):
    return not f._beats and not f.texts and f.ui_state == "FieldHUD" and not f.battle_active and f._bexit is None


def _o3_route(side="S", *, p61=("Narrator\n“Ladies and gentlemen!”",), p62=("Cinna\n“Act I!”",),
              p63=("Zidane\n“Phew.”",), scene=338, units=None, battle_in=62, end=True):
    """O3's game side on the fake, as ``(ready, act)`` phases: 61's pages, then its Field(62); 62's pages, then battle
    ``scene`` (King Leo's roster) -- in "61" instead with ``battle_in`` 61; after the battle's end, 63's pages and
    (``end``) its Field(64). Every scene keeps control off."""
    f61, f62 = _O3_FIELDS[side][61], _O3_FIELDS[side][62]
    seen = {}

    def fight(f):
        seen["epoch"] = f.battle_epoch + 1
        f.start_battle(scene, units=units or _o3_units())
    phases = [(lambda f: f.field_id == f61, lambda f: f.scene(*p61, control=False))]
    if battle_in == 61:
        return phases + [(lambda f: f.field_id == f61 and _o3_idle(f), fight)]
    phases += [(lambda f: f.field_id == f61 and _o3_idle(f), lambda f: (_o2_move(f, f62), f.scene(*p62, control=False))),
               (lambda f: f.field_id == f62 and _o3_idle(f), fight),
               (lambda f: f.battle_epoch == seen.get("epoch") and _o3_idle(f), lambda f: f.scene(*p63, control=False))]
    if end:
        phases.append((lambda f: _o3_idle(f), lambda f: _o2_move(f, _O3_END)))
    return phases


def _o3_drive(g, fake, pred, side="S", *, phases, log=None, budget=60.0):
    """The driver against the director's phases: ``(outcome or the RouteVoid raised, log)``."""
    SD = _segment_modules()
    log = [] if log is None else log
    stop = threading.Event()
    _o1_director(fake, stop, phases)
    try:
        try:
            return SD.drive(g, pred, side, log, deadline=time.time() + budget, floor_for=lambda d, c: _flat_bgi(),
                            prior_for=lambda d: _prior(), forbid_live=False), log
        except SD.RouteVoid as err:
            return err, log
    finally:
        stop.set()


def test_o3_drive_fights_its_registered_battle_and_lands_fresh(game):
    """S4 (research/o3_design.md 2.2-2.3), the S side: 61's and 62's pages, then battle 338 at "62" -- rule 1b, a NEW
    epoch, matched on the published scene, the visit's place and SC 1155 -- fought by fight()'s default policy (King
    Leo's latch: one Attack, result 2, read in the fade), left with leave_battle(stop_on_field), and landed FRESH in "63"
    through the engine's four phases; then 63's pages and the end. Beats {"leo": 2}; ONE battle row: scene 338, its
    epoch the drive's first + 1 (``battle_epoch0``), result 2, turns, the leave's presses, the flip seen on a result-1
    sample, landed "63" (place 63), no land_late; visits 61, 62, 63, each once. Break: drop rule 1b (rule 5's V10)."""
    fake = _o3_fake(game, exit_to=30810)
    with session(game, fake) as g:
        _o3_start(g)
        out, log = _o3_drive(g, fake, _o3_pred(), phases=_o3_route())
    assert not isinstance(out, Exception) and out["end"] == "reached" and out["why"] == f"field {_O3_END}", out
    assert out["beats"] == {"leo": 2} and type(out["beats"]["leo"]) is int, out["beats"]
    rows = [r for r in log if r["k"] == "battle"]
    assert out["battles"] == rows and len(rows) == 1, rows
    b = rows[0]
    assert (b["scene"], b["row"], b["beat"], b["donor"], b["field"], b["sc"]) == (338, 0, "leo", 30821, 30821, 1155), b
    assert b["epoch"] == out["battle_epoch0"] + 1 and b["result"] == 2 and b["turns"] >= 1, b
    assert b["timed_out"] is False and b["tutorials"] == 0 and b["seconds"] > 0, b
    assert b["leave"]["presses"] >= 1 and b["leave"]["stopped"] in ("scene-gone", "field"), b["leave"]
    assert set(b["leave"]["uis"]) <= {"BattleHUD", "BattleResult"}, b["leave"]
    assert b["flip_frame"] is not None and b["flip_result"] == 1 and b["flip_frame"] < b["land_frame"], b
    assert (b["landed"], b["landed_place"], b["land_late"], b["v"]) == (30810, 30810, None, None), b
    visits = [r for r in log if r["k"] == "visit"]
    assert [(r["field"], r["donor"]) for r in visits] == [(30820, 30820), (30821, 30821), (30810, 30810)], visits
    assert visits[2]["frame"] >= b["land_frame"], (visits[2], b)
    assert out["pages"] == ["Narrator\n“Ladies and gentlemen!”", "Cinna\n“Act I!”", "Zidane\n“Phew.”"], out["pages"]


def test_o3_drive_lands_in_the_member_on_the_fork_side(game):
    """S4's landing judge, the F side: the same route through the members (31211 -> 31212 -> battle -> 31213); the
    battle's exit lands in member("63") = 31213 -- the s24 redirect fired -- and the run reaches the end: landed
    31213, its place 63; the visits are the members, their places 61, 62, 63. Break: judge the F landing by the id
    itself (31213 is no "lands" 30810: V11)."""
    _o3_register(game)
    fake = _o3_fake(game, exit_to=31213)
    with session(game, fake) as g:
        _o3_start(g, "F")
        out, log = _o3_drive(g, fake, _o3_pred(), "F", phases=_o3_route("F"))
    assert not isinstance(out, Exception) and out["end"] == "reached", out
    b = out["battles"][0]
    assert (b["field"], b["donor"], b["landed"], b["landed_place"], b["v"]) == (31212, 30821, 31213, 30810, None), b
    assert out["beats"] == {"leo": 2}
    assert [(r["field"], r["donor"]) for r in log if r["k"] == "visit"] == [
        (31211, 30820), (31212, 30821), (31213, 30810)], log


def test_o3_drive_reads_a_landing_in_the_real_field_as_a_finding(game):
    """V16 (research/o3_design.md 2.3 step 7, 2.6): on the F side the battle's exit lands in REAL "63" (30810) -- the
    s24 redirect did not fire: VOID V16, attributed to the GAME (a finding, which rerun.stop_on holds), its cell the
    battle's [62, 1155]; the battle row carries it, and the beat its result. Break: read it as V11."""
    _o3_register(game)
    fake = _o3_fake(game, exit_to=30810)
    with session(game, fake) as g:
        _o3_start(g, "F")
        err, log = _o3_drive(g, fake, _o3_pred(), "F", phases=_o3_route("F", end=False))
    SD = _segment_modules()
    assert isinstance(err, SD.RouteVoid), err
    assert (err.v, err.by, err.cell) == ("V16", "game", [30821, 1155]), (err.v, err.by, err.cell)
    assert "landed in real 30810, not member(30810) 31213: the s24 redirect did not fire" in str(err), err
    b = [r for r in log if r["k"] == "battle"][0]
    assert (b["landed"], b["v"], b["by"], b["result"]) == (30810, "V16", "game", 2), b
    assert not [r for r in log if r["k"] == "visit" and r["field"] == 30810], "no visit to the leaked field"


def test_o3_drive_ignores_the_id_flip_inside_the_battle(game):
    """Rule 1b sits BEFORE rules 9, 2 and 3 (research/o3_design.md 0.2 #8, 2.2): with BattleResult held long, the
    harness reads many samples in the battle AND at "63" with result 1 -- the over frame's flip -- and the run reads
    none of them as a load, a leave or a visit: no V10, no V11, the visit to "63" starting only at the landing, the
    flip on record. Break: hand the loop back after the fight (the main loop then visits 63 inside the battle and
    VOIDs it, V10)."""
    fake = _o3_fake(game, exit_to=30810, result_frames=400, cls=_PubFake)
    with session(game, fake) as g:
        _o3_start(g)
        out, log = _o3_drive(g, fake, _o3_pred(), phases=_o3_route())
    flipped = [p for p in fake.pubs if p[3] and (p[1], p[2]) == (30810, 1)]
    assert not isinstance(out, Exception) and out["end"] == "reached", out
    b = out["battles"][0]
    assert len(flipped) >= 50, f"premise: the flip window was published ({len(flipped)} samples)"
    assert b["flip_result"] == 1 and b["flip_frame"] < b["land_frame"] and b["landed"] == 30810, b
    v63 = [r for r in log if r["k"] == "visit" and r["field"] == 30810]
    assert len(v63) == 1 and v63[0]["frame"] >= b["land_frame"], (v63, b)


def test_o3_drive_waits_out_a_late_landing(game):
    """The two-tier landing (research/o3_design.md 2.3 step 4, 11.2 #2): a load longer than the row's ``land_s`` but
    under its ``land_cap_s`` is no VOID -- the run reaches the end and the battle row records ``land_late`` (the
    landing's frames and seconds from the leave's end), so a slow fork landing can never turn one-sided. Break: VOID
    the run at ``land_s``."""
    fake = _o3_fake(game, exit_to=30810, load_frames=720)
    pred = _o3_pred(battles=[_o3_row(land_s=1.0, land_cap_s=20.0)])
    with session(game, fake) as g:
        _o3_start(g)
        out, log = _o3_drive(g, fake, pred, phases=_o3_route())
    assert not isinstance(out, Exception) and out["end"] == "reached", out
    b = out["battles"][0]
    late = b["land_late"]
    assert late is not None and late["s"] >= 1.0 and late["frames"] >= 360 and b["v"] is None, b


def test_o3_drive_voids_a_landing_past_its_cap(game):
    """No field by ``land_cap_s``: VOID V14, the GAME's (a hang that long is a finding, as the watchdog's V14 is), its
    cell the battle's; the battle row carries it. Break: wait on past the cap (the run's budget, V13, instead)."""
    fake = _o3_fake(game, exit_to=30810, load_frames=10 ** 6)
    pred = _o3_pred(battles=[_o3_row(land_s=0.5, land_cap_s=2.0)])
    with session(game, fake) as g:
        _o3_start(g)
        t0 = time.time()
        err, log = _o3_drive(g, fake, pred, phases=_o3_route(end=False), budget=30.0)
        took = time.time() - t0
    SD = _segment_modules()
    assert isinstance(err, SD.RouteVoid) and (err.v, err.by, err.cell) == ("V14", "game", [30821, 1155]), err
    assert "battle 338 ended and no field came up within 2 s" in str(err) and took < 25.0, (err, took)
    b = [r for r in log if r["k"] == "battle"][0]
    assert (b["v"], b["landed"], b["result"]) == ("V14", None, 2), b


def test_o3_drive_voids_an_unregistered_battle(game):
    """V10 for a battle the registry does not answer (research/o3_design.md 2.3 step 1), each the GAME's, its cell the
    visit's place and SC: scene 337 at "62" (another scene); scene 338 at "61" (another place); and the same row twice
    (a same-field battle -- its row lands in "62" -- answered, then a second battle 338 in "62"). No battle row for an
    unanswered battle. Break: drop the answered set (the second battle is fought)."""
    SD = _segment_modules()
    for case in ("scene", "place", "twice"):
        fake = _o3_fake(game, exit_to=None if case == "twice" else 30810)
        pred = _o3_pred(battles=[_o3_row(lands=30821)]) if case == "twice" else _o3_pred()
        log: list = []
        if case == "scene":
            phases = _o3_route(scene=337, end=False)
        elif case == "place":
            phases = _o3_route(battle_in=61)
        else:                       # the second battle once the driver has landed the first (its row is logged)
            phases = _o3_route(end=False)[:3] + [
                (lambda f: any(r.get("k") == "battle" for r in log) and _o3_idle(f),
                 lambda f: f.start_battle(338, units=_o3_units()))]
        with session(game, fake) as g:
            _o3_start(g)
            err, log = _o3_drive(g, fake, pred, phases=phases, log=log)
            epoch = fake.battle_epoch
        assert isinstance(err, SD.RouteVoid) and (err.v, err.by) == ("V10", "game"), (case, err)
        where = 30820 if case == "place" else 30821
        assert err.cell == [where, 1155] and f"an unregistered battle: scene {337 if case == 'scene' else 338} " \
                                             f"(epoch {epoch}) in {where} (place {where}) at SC 1155" in str(err), err
        rows = [r for r in log if r["k"] == "battle"]
        assert len(rows) == (1 if case == "twice" else 0), (case, rows)


def test_o3_drive_voids_a_battle_with_no_result(game):
    """V15 (research/o3_design.md 2.3 step 2, 2.6): the registered battle reaches no result within the row's own
    bounds -- the DRIVER's (its policy and bounds own the fight). A King Leo no attack can end (10^7 HP, no scripted
    end) with ``timeout_s`` 3: V15 after about 3 s, the battle row ``timed_out``; with ``max_turns`` 0 (R-BATTLE-VOID's
    row): V15 at the first command prompt -- no battlecmd executed, still mid-fight in BattleHUD. Break: let fight()'s
    FightTimeout propagate (the run is STOPPED, V13)."""
    SD = _segment_modules()
    for bounds, want in (({"timeout_s": 3}, "within 3 s / 40 turns"), ({"max_turns": 0}, "within 60 s / 0 turns")):
        fake = _o3_fake(game, exit_to=30810)
        fake.battle_script_end = None
        pred = _o3_pred(battles=[_o3_row(**bounds)])
        with session(game, fake) as g:
            _o3_start(g)
            err, log = _o3_drive(g, fake, pred, phases=_o3_route(units=_o3_units(10 ** 7), end=False), budget=180.0)
            st = g.state
        assert isinstance(err, SD.RouteVoid) and (err.v, err.by, err.cell) == ("V15", "driver", [30821, 1155]), err
        assert f"battle 338 reached no result {want}" in str(err), err
        b = [r for r in log if r["k"] == "battle"][0]
        assert b["timed_out"] is True and b["v"] == "V15" and b["result"] is None, b
        if bounds.get("max_turns") == 0:
            assert b["turns"] == 0 and not [s for s in fake.executed if s[0] == "battlecmd"], fake.executed
            assert st.in_battle and st.ui_state == "BattleHUD" and st.battle_result == 0, st


def test_o3_drive_stops_on_a_battle_gone_without_a_result(game):
    """A registered battle whose scene GOES with no result while its bounds hold (the review, research/o3_design.md
    11.7 #2): fight()'s FightTimeout kind "gone" -- no bound ran out -- is an instrument stop, never V15 (the driver's
    bound, "reached no result within 60 s") nor the budget's message: the executor logs its battle row (v V13, by
    driver, result None, timed_out False, the scene-gone why) and raises HarnessError, which the session records as
    STOPPED (V13). The scene goes a second into the fight (the battle ends with result 0 on the fake's own thread; no
    ATB, so no command prompt races it). Break: read every FightTimeout as a bound (V15)."""
    SD = _segment_modules()
    fake = _o3_fake(game)
    fake.battle_script_end = None
    fake.atb_gain = 0                                       # no command prompt: the fight only waits
    started: dict = {}
    phases = _o3_route(units=_o3_units(10 ** 7), end=False)[:3] + [
        (lambda f: f.battle_active, lambda f: started.update(frame=f.frame)),
        (lambda f: "frame" in started and f.frame >= started["frame"] + 240, lambda f: _o3_end_on_the_fake(f, 0))]
    log: list = []
    with session(game, fake) as g:
        _o3_start(g)
        with pytest.raises(HarnessError, match="went away with no result") as err:
            _o3_drive(g, fake, _o3_pred(), phases=phases, log=log, budget=180.0)
    assert not isinstance(err.value, SD.RouteVoid) and "reached no result within" not in str(err.value), err.value
    b = [r for r in log if r["k"] == "battle"][0]
    assert (b["v"], b["by"], b["result"], b["timed_out"], b["turns"]) == ("V13", "driver", None, False, 0), b
    assert b["why"].startswith("battle 338's scene went away with no result"), b


def test_o3_drive_bounds_the_leave_by_its_row(game):
    """The leave is bounded (the review, research/o3_design.md 11.7 #1): the executor passes leave_battle
    ``timeout=min(the row's land_cap_s, the run's time left)``. A battle whose BattleResult never hands over
    (``result_frames`` 10^6), ``land_cap_s`` 2: the leave stops "timeout" short of its 40 Confirms, each Confirm it made
    a press row, and the landing's own cap then ends the run -- V14, no field within 2 s. Break: call leave_battle
    without its bound (it presses all 40 first)."""
    SD = _segment_modules()
    fake = _o3_fake(game, exit_to=30810, result_frames=10 ** 6)
    pred = _o3_pred(battles=[_o3_row(land_s=1.0, land_cap_s=2.0)])
    with session(game, fake) as g:
        _o3_start(g)
        err, log = _o3_drive(g, fake, pred, phases=_o3_route(end=False), budget=120.0)
    assert isinstance(err, SD.RouteVoid) and (err.v, err.by) == ("V14", "game"), err
    b = [r for r in log if r["k"] == "battle"][0]
    assert b["leave"]["stopped"] == "timeout" and 0 < b["leave"]["presses"] < 40, b["leave"]
    assert len([r for r in log if r["k"] == "press" and r["why"] == "leave_battle"]) == b["leave"]["presses"], log


def test_o3_drive_logs_leave_battle_presses_as_press_rows(game):
    """The leave's Confirms are evidence (research/o3_design.md 2.3 step 3): each is a ``press`` row -- ``why``
    "leave_battle", ``pre`` the sample it was decided on (in the battle), ``post`` None, ``near`` [] -- as many as the
    leave pressed and the battle row counts, every one executed by the game. Break: log no press rows."""
    fake = _o3_fake(game, exit_to=30810, cls=_StampFake)
    with session(game, fake) as g:
        _o3_start(g)
        out, log = _o3_drive(g, fake, _o3_pred(), phases=_o3_route())
        leave = g.last_leave
    assert not isinstance(out, Exception) and out["end"] == "reached", out
    rows = [r for r in log if r["k"] == "press" and r["why"] == "leave_battle"]
    assert rows and len(rows) == len(leave["presses"]) == out["battles"][0]["leave"]["presses"], (rows, leave)
    assert [r["pre"] for r in rows] == leave["presses"], (rows, leave)
    assert all(r["post"] is None and r["near"] == [] and r["pre"]["in_battle"] and r["visit"] == 2 for r in rows), rows
    first, landed = min(r["pre"]["frame"] for r in rows), out["battles"][0]["land_frame"]
    fired = [f for _t, f, s in fake.stamped if s[:2] == ["press", "confirm"] and first <= f < landed]
    assert len(fired) == len(rows), (fired, rows)


def test_o3_drive_stops_on_a_stop_page(game):
    """Rule 7's stop pages (research/o3_design.md 2.2, 2.6): 61-63's error window ("Error Env Play()  Slot=n", which an
    incoming Byte[13]/[14] of 2 or 9 opens) VOIDs the run as V5 with NOTHING pressed -- the DRIVER's in the run's first
    visit, the start place (the warp's start state), the GAME's in a later visit (a fork's deviation). Break: page
    the window (a Confirm closes it and the run goes on)."""
    SD = _segment_modules()
    for at, by, where in ((61, "driver", 30820), (62, "game", 30821)):
        fake = _o3_fake(game, exit_to=30810, cls=_StampFake)
        up = {}

        def error_page(f, up=up):
            up["frame"] = f.frame
            f.scene(_O3_ERROR, control=False)
        if at == 61:
            phases = [(lambda f: f.field_id == 30820, error_page)]
        else:
            phases = [(lambda f: f.field_id == 30820, lambda f: f.scene("Narrator\n“Ladies and gentlemen!”",
                                                                        control=False)),
                      (lambda f: f.field_id == 30820 and _o3_idle(f), lambda f: (_o2_move(f, 30821),
                                                                                 error_page(f)))]
        with session(game, fake) as g:
            _o3_start(g)
            err, log = _o3_drive(g, fake, _o3_pred(), phases=phases)
        assert isinstance(err, SD.RouteVoid) and (err.v, err.by, err.cell) == ("V5", by, [where, 1155]), (at, err)
        assert "Env Play()" in str(err) and "Error Env Play()" in str(err), err
        # a press FOR the window executes at a later frame than the one it went up in: it must be published, sampled
        # and requested first (61's own last page press can share that frame -- the director answers it at once)
        late = [f for _t, f, s in fake.stamped if s[:2] == ["press", "confirm"] and f > up["frame"]]
        assert late == [], (at, late)


def test_o3_drive_answers_a_skip_dialog_at_its_default(game):
    """The skip-movie rule (research/o3_design.md 2.5): during 61's movie a stray Confirm (the director's: the driver
    presses only on pages) opens the skip dialog; the rule answers it at the game's own cursor -- No -- the movie
    resumes for exactly the frames it had left, the page after it is turned, and the run reaches the end. Break: drop
    the rule (V1)."""
    fake = _o3_fake(game)
    movie = {"movie": 600, "skip": dict(_O3_SKIP)}
    phases = [(lambda f: f.field_id == 30820, lambda f: f.scene(movie, "Narrator\n“The curtain rises.”",
                                                                control=False)),
              (lambda f: f._movie is not None and f.movies[-1]["played"] >= 60,
               lambda f: f.queue.append(["press", "confirm", "4"])),
              (lambda f: _o3_idle(f) and f.movies and f.movies[-1]["end"] is not None, lambda f: _o2_move(f, _O3_END))]
    with session(game, fake) as g:
        _o3_start(g)
        out, log = _o3_drive(g, fake, _o3_pred(), phases=phases)
    assert not isinstance(out, Exception) and out["end"] == "reached", out
    assert fake.answered == [1] and len(fake.movies) == 1, (fake.answered, fake.movies)
    assert (fake.movies[0]["played"], fake.movies[0]["skips"], fake.movies[0]["ended"]) == (600, 1, "played")
    assert [(c["index"], c["rule"], c["selected"]) for c in out["choices"]] == [("default", 0, 1)], out["choices"]
    assert out["pages"] == ["Narrator\n“The curtain rises.”"], out["pages"]


def test_o3_drive_watchdog_against_a_long_movie(game):
    """The stall watchdog against a movie (research/o3_design.md 4.12, 11.1 #4): the agent publishes no movie state,
    so a movie longer than ``no_progress_s`` is V14 (game) -- and with ``no_progress_s`` above the movie the run reaches
    the end. The sizing rule, pinned on the fake. Break: count the movie as progress (the short budget then reaches
    the end)."""
    SD = _segment_modules()
    got = {}
    for no_progress_s in (1.0, 15.0):
        fake = _o3_fake(game)
        phases = [(lambda f: f.field_id == 30820, lambda f: f.scene("Narrator\n“Lights.”", {"movie": 960},
                                                                    "Narrator\n“Curtain.”", control=False)),
                  (lambda f: _o3_idle(f) and f.movies and f.movies[-1]["end"] is not None,
                   lambda f: _o2_move(f, _O3_END))]
        pred = _o3_pred()
        pred["budget"]["no_progress_s"] = no_progress_s
        with session(game, fake) as g:
            _o3_start(g)
            got[no_progress_s] = _o3_drive(g, fake, pred, phases=phases, budget=40.0)[0], dict(fake.movies[0])
    err, mv = got[1.0]
    assert isinstance(err, SD.RouteVoid) and (err.v, err.by, err.cell) == ("V14", "game", [30820, 1155]), err
    assert "no progress for 1 s in 30820" in str(err) and mv["end"] is None, (err, mv)
    out, mv = got[15.0]
    assert not isinstance(out, Exception) and out["end"] == "reached" and mv["ended"] == "played", (out, mv)


def test_o3_drive_waits_for_the_end_places_first_row(game):
    """Rule 1's opt-in end row (``budget.end_row_s``; research/o3_design.md 2.2, 11.7 #3). Rule 1 fires on the first
    poll that publishes the end field and the session closes the trace right after the drive returns: story-o1e closed
    it 1-4 frames after the field changed, its run 3 S before any row of the end field (no end cut). The end field's
    first store here comes 240 frames after the arrival. With ``end_row_s`` 3 the drive waits for it: the ``end`` row
    records ``end_row`` {seen True, f its frame, s the wait}, and the row is in the trace when the drive returns. A row
    that never comes is waited for ``end_row_s`` (0.5) and no longer: seen False, no VOID (the analysis's A-NOEND).
    Without the key -- O1's and O2's rule 1 -- no wait and no ``end_row``: the drive returns before the store, and the
    trace holds no row of the end field (the race, reproduced). Break: return before the row (no wait)."""
    got = {}
    for wait, store in ((3.0, True), (0.5, False), (None, True)):
        fake = _o3_fake(game)
        pred = _o3_pred()
        if wait is not None:
            pred["budget"]["end_row_s"] = wait
        arrived: dict = {}

        def to_end(f, arrived=arrived):
            arrived["frame"] = f.frame
            _o2_move(f, _O3_END)
        phases = [(lambda f: f.field_id == 30820, lambda f: f.scene("Narrator\n“Lights.”", control=False)),
                  (lambda f: f.field_id == 30820 and _o3_idle(f), to_end)]
        if store:                                # 64's Main_Init: its first store, 240 frames after the arrival
            phases.append((lambda f, arrived=arrived: f.field_id == _O3_END and f.frame >= arrived["frame"] + 240,
                           lambda f: f.script_store(0, 0, 22, 191 >> 3, "Bit", 0, bit=191)))
        with session(game, fake) as g:
            _o3_start(g)
            g.storytrace(True)
            t0 = time.time()
            out, log = _o3_drive(g, fake, pred, phases=phases)
            took = time.time() - t0
            rows = [r for r in g.story_rows() if r.k == "w" and r.fld == _O3_END]
        assert not isinstance(out, Exception) and out["end"] == "reached", (wait, out)
        got[(wait, store)] = ([r for r in log if r["k"] == "end"][-1], rows, took)
    end, rows, _took = got[(3.0, True)]
    er = end["end_row"]
    assert er["seen"] is True and len(rows) == 1 and er["f"] == rows[0].f, (er, rows)
    assert 0.5 <= er["s"] < 3.0, er                        # it waited for the store, and not for its bound
    end, rows, _took = got[(0.5, False)]
    assert end["end_row"]["seen"] is False and end["end_row"]["f"] is None and rows == [], end
    assert 0.5 <= end["end_row"]["s"] < 2.0, end["end_row"]
    end, rows, _took = got[(None, True)]
    assert "end_row" not in end and rows == [], (end, rows)    # O1's and O2's rule 1: the trace closes before the row


def test_o3_drive_battle_of_rejects_a_bad_row():
    """The registry row, strict (research/o3_design.md 2.1, section 8's battle-row unit): 2.1's row passes (a copy);
    ValueError on ``won`` [1, 2, 3] (a defeat counted won), [2] and []; on a beat not in ``beats``; on a beat a naming
    rule, a table step, a choice rule or a battle row of ANOTHER slot also names; on ``max_turns`` -1 and on True (a
    bool is no int); on ``land_s`` above ``land_cap_s``; on an unknown or a missing key; ``max_turns`` 0 passes --
    R-BATTLE-VOID's override of the SAME slot, checked against the predictions it overrides. And a driver refuses a
    bad row before anything is driven. Break: compare ``won`` by equality alone ([True, 2] then passes)."""
    SD = _segment_modules()
    pred = _o3_pred()
    row = pred["battles"][0]
    got = SD.battle_of(pred, row)
    assert got == row and got is not row
    assert SD.battle_of(pred, dict(row, max_turns=0))["max_turns"] == 0
    other = _o3_pred(battles=[_o3_row(sc=None, won=[1])])          # any SC; WinPose on: won [1]
    assert SD.battle_of(other, other["battles"][0])["won"] == [1]

    def refused(match, **change):
        with pytest.raises(ValueError, match=match):
            SD.battle_of(pred, {**row, **change})
    for won in ([1, 2, 3], [2], [], [True, 2], (1, 2.0)):
        refused("won is", won=won)
    refused("is not one of the predictions' beats", beat="garnet")
    refused("max_turns is an int >= 0", max_turns=-1)
    refused("max_turns is an int >= 0", max_turns=True)
    refused("max_turns is an int >= 0", max_turns=2.5)
    refused("is above land_cap_s", land_s=200)
    refused("positive numbers", timeout_s=0)
    refused("of the wrong type", scene="338")
    refused("of the wrong type", sc=True)
    with pytest.raises(ValueError, match="unknown key"):
        SD.battle_of(pred, {**row, "lands_in": 63})
    with pytest.raises(ValueError, match="missing"):
        SD.battle_of(pred, {k: v for k, v in row.items() if k != "land_cap_s"})
    for where in ("naming", "choices", "table", "battles"):
        p = _o3_pred()
        if where == "naming":
            p["naming"] = [{"donor": 30821, "sc": 1155, "beat": "leo"}]
        elif where == "choices":
            p["choices"] = p["choices"] + [{"donor": 30821, "sc": None, "match": "x", "pick": "y", "beat": "leo"}]
        elif where == "table":
            p["table"] = [{"donor": 30821, "sc": 1155, "steps": [{"kind": "trigger", "goal": [0, 0], "until": {"x_le": 1},
                                                                 "beat": "leo"}]}]
        else:
            p["battles"] = p["battles"] + [_o3_row(scene=339)]
        with pytest.raises(ValueError, match="is also named by"):
            SD.battle_of(p, p["battles"][0])
    bad = _o3_pred(battles=[_o3_row(won=[1, 2, 3])])
    with pytest.raises(ValueError, match="won is"):
        SD.drive(None, bad, "S", [], deadline=time.time() + 1, floor_for=lambda d, c: None, prior_for=lambda d: None)


# ---- THE MOVIE-SKIP POLICY (opt-in, ``pred["movies"]``; studies/story-trace/PLAN.md "Movie skip (opt-in)"). On the
# fake's "61" (30820) at SC 1155: a movie beat -- with H9's skip dialog (FieldHUD.cs:275-286, the cursor on No), or
# none -- then a page, then the end. Each test's movie and timings are its own; 240 fake frames are a second.

_O3_PAGE = "Narrator\n“The curtain rises.”"


def _o3_movies(**over):
    """A policy registering "61" at SC 1155: a press 0.5 s into the visit, again every second, three at most; its next
    page registered 25 s into the visit."""
    cell = {"donor": 30820, "sc": 1155, "after_s": 0.5, "next_page_s": 25.0,
            "why": "61 e2 t1 ip159 Cinematic(0,8,1,1): FMV003, on the fake"}
    cell.update(over.pop("cell", {}))
    return {"policy": "skip", "press_every_s": 1.0, "max_presses": 3, "cells": [cell], **over}


def _o3_movie_route(*beats):
    """61's scene (``beats``: the movie and what follows it), then the end once it is over."""
    return [(lambda f: f.field_id == 30820, lambda f: f.scene(*beats, control=False)),
            (lambda f: f.field_id == 30820 and _o3_idle(f) and f.movies and f.movies[-1]["end"] is not None,
             lambda f: _o2_move(f, _O3_END))]


def _o3_movie_run(game, pred, phases, *, budget=60.0):
    """One drive on a fresh fake: ``(outcome or the RouteVoid raised, log, fake)``."""
    fake = _o3_fake(game)
    with session(game, fake) as g:
        _o3_start(g)
        out, log = _o3_drive(g, fake, pred, phases=phases, budget=budget)
    return out, log, fake


def _presses(log, why):
    return [r for r in log if r["k"] == "press" and r["why"] == why]


def test_segment_movie_skip_answer_reads_only_the_skip_dialog():
    """skip_answer (pure): the engine's skip dialog -- US "the movie?", UK "this cutscene?", each option line as
    published or short its first character (O1's "ight the candle"), the prompt published EMPTY with the text in the
    rendered box -- answers absolute option 0, FieldHUD's skip. Never a skip: another prompt (and an empty one whose
    box says something else), three lines, the pair reversed, Yes at absolute index 1 (a disabled line before it), a
    line that is only a fragment ("s"), no choice. A policy's own ``match``/``yes``/``no`` replace the US text. Break:
    match the lines alone (the "save" dialog then answers 0)."""
    SD = _segment_modules()
    us = {"options": ["Do you want to skip\nthe movie?", "Yes", "No"], "active": [0, 1], "selected": 1, "count": 2}
    assert SD.skip_answer(us) == 0 and SD.skip_answer(dict(us, active=None)) == 0
    assert SD.skip_answer(dict(us, options=["Do you want to skip\nthis cutscene?", "Yes", "No"])) == 0
    assert SD.skip_answer(dict(us, options=["o you want to skip\nthe movie?", "es", "o"])) == 0
    box = ["Do you want to skip\nthe movie?\nYes\nNo"]
    assert SD.skip_answer(dict(us, options=["", "Yes", "No"]), box) == 0
    assert SD.skip_answer(dict(us, options=["", "Yes", "No"]), ["Save the game?\nYes\nNo"]) is None
    assert SD.skip_answer(dict(us, options=["", "Yes", "No"])) is None
    for options in (["Do you want to save\nthe game?", "Yes", "No"], ["Do you want to skip\nthe movie?", "Yes", "No",
                                                                        "Maybe"],
                    ["Do you want to skip\nthe movie?", "No", "Yes"], ["Do you want to skip\nthe movie?", "s", "No"],
                    ["Do you want to skip\nthe movie?", "", "No"], ["Do you want to skip\nthe movie?", "Yes"]):
        assert SD.skip_answer(dict(us, options=options), box) is None, options
    assert SD.skip_answer(dict(us, active=[1, 2])) is None
    assert SD.skip_answer(None) is None and SD.skip_answer({"options": []}) is None
    fr = {"match": "passer", "yes": "Oui", "no": "Non"}
    assert SD.skip_answer({"options": ["Voulez-vous passer\nles cinématiques ?", "Oui", "Non"]}, (), fr) == 0
    assert SD.skip_answer(us, (), fr) is None


def test_segment_movie_skip_policy_is_strict():
    """movies_of: the policy (``pred["movies"]``) is checked STRICT before anything is driven, as a battle row is.
    None without the key (the driver is O3's exactly); a good policy comes back a copy with the engine's US text filled
    in. ValueError on: a policy that is no dict, an unknown or a missing key, a policy other than "skip", empty cells,
    a non-positive ``press_every_s``, ``max_presses`` 0 or True (a bool is no int), an empty ``match``; a cell with an
    unknown or missing key (``length_s`` among the unknown: the span is registered to the NEXT PAGE, ``next_page_s``,
    and a name that read as the movie's own length is refused), a string donor, a bool SC, a non-positive ``after_s``
    or ``next_page_s``, an empty ``why``; two cells one place and SC would both match (an SC None is every SC); a cell
    whose last press and its wait end past its next page. And a driver refuses a bad policy before anything is driven.
    Break: accept unknown keys (a typo'd ``max_press`` then registers nothing)."""
    SD = _segment_modules()
    assert SD.movies_of(_o3_pred()) is None
    pol = _o3_movies()
    got = SD.movies_of({"movies": pol})
    assert got is not pol and got["cells"] == pol["cells"] and got["cells"][0] is not pol["cells"][0]
    assert (got["match"], got["yes"], got["no"]) == ("want to skip", "Yes", "No")
    assert SD.movies_of({"movies": dict(pol, match="passer", yes="Oui", no="Non")})["yes"] == "Oui"
    assert SD.movies_of({"movies": _o3_movies(cell={"sc": None, "next_page_s": None})})["cells"][0]["sc"] is None
    cell = pol["cells"][0]
    no_span = {k: v for k, v in cell.items() if k != "next_page_s"}
    assert SD.movies_of({"movies": dict(pol, cells=[no_span])})["cells"] == [no_span]       # the span is optional

    def refused(match, policy):
        with pytest.raises(ValueError, match=match):
            SD.movies_of({"movies": policy})
    refused("the policy is a dict", ["skip"])
    refused("unknown key", dict(pol, max_press=2))
    refused("missing", {k: v for k, v in pol.items() if k != "max_presses"})
    refused("is not one of", dict(pol, policy="play"))
    refused("non-empty list", dict(pol, cells=[]))
    refused("press_every_s", dict(pol, press_every_s=0))
    for most in (0, True, 1.5):
        refused("max_presses", dict(pol, max_presses=most))
    refused("non-empty strings", dict(pol, match=""))
    refused("a cell is a dict", dict(pol, cells=[61]))
    refused("unknown key", dict(pol, cells=[dict(cell, field=61)]))
    refused(r"unknown key\(s\) \['length_s'\]", dict(pol, cells=[dict(no_span, length_s=25.0)]))
    refused("missing", dict(pol, cells=[{k: v for k, v in cell.items() if k != "after_s"}]))
    for change in ({"donor": "61"}, {"sc": True}, {"after_s": 0}, {"next_page_s": -1}, {"why": ""},
                   {"after_s": False}):
        refused("of the wrong type", dict(pol, cells=[dict(cell, **change)]))
    refused("registered twice", dict(pol, cells=[cell, dict(cell, after_s=2.0)]))
    refused("registered twice", dict(pol, cells=[cell, dict(cell, sc=None)]))
    refused("past its next page at 25 s", dict(pol, cells=[dict(cell, after_s=22.5)]))     # 22.5 + 2 + 1 > 25
    assert SD.movies_of({"movies": dict(pol, cells=[dict(cell, after_s=21.0)])})          # 21 + 2 + 1 = 24 <= 25
    assert SD.movies_of({"movies": dict(pol, cells=[cell, dict(cell, donor=30821)])})      # another place: fine
    with pytest.raises(ValueError, match="unknown key"):
        SD.drive(None, _o3_pred(movies=dict(pol, every=1)), "S", [], deadline=time.time() + 1,
                 floor_for=lambda d, c: None, prior_for=lambda d: None)


def test_o3_drive_movie_skip_presses_once_and_answers_yes(game):
    """The policy's skip (PLAN.md "Movie skip (opt-in)"): in the registered cell, nothing on screen and control off,
    0.5 s into the visit, ONE Confirm (a ``press`` row, "movie_skip", its frame) opens the skip dialog; the policy
    answers it YES -- option 0, over the game's cursor on No -- so the movie ends at once and its wait goes on: the page
    after it is turned and the run reaches the end, long before the movie's 25 s. The visit's ``movie`` row: one press,
    the dialog as published (prompt, options, active [0, 1], selected 1), the frame and the seconds it was skipped at,
    the next page as registered (``next_page_s`` 25) and ``left_s`` -- 25 s less those seconds, the most the skip can
    save -- and NO ``saved_s``: what a skip saved is the A/B's to measure, from the drive times; its ``choice`` row
    (rule "movie_skip", index 0, selected 1). Break: answer the dialog's default (the movie then plays out)."""
    pred = _o3_pred(movies=_o3_movies())
    phases = _o3_movie_route({"movie": 6000, "skip": dict(_O3_SKIP)}, _O3_PAGE)
    out, log, fake = _o3_movie_run(game, pred, phases)
    assert not isinstance(out, Exception) and out["end"] == "reached", out
    assert fake.answered == [0] and len(fake.movies) == 1, (fake.answered, fake.movies)
    mv = fake.movies[0]
    assert (mv["skips"], mv["ended"]) == (1, "skipped") and mv["played"] < 6000 // 4, mv
    presses = _presses(log, "movie_skip")
    assert len(presses) == 1 and presses[0]["pre"]["control"] is False and presses[0]["donor"] == 30820, presses
    row = out["movies"][0]
    assert out["movies"] == [r for r in log if r["k"] == "movie"] and len(out["movies"]) == 1, out["movies"]
    assert (row["outcome"], row["missed"], row["cell"], row["visit"], row["sc"]) == ("skipped", None, 0, 1, 1155), row
    assert row["presses"] == [{"frame": presses[0]["pre"]["frame"], "t": row["presses"][0]["t"]}], row["presses"]
    assert 0.5 <= row["presses"][0]["t"] < row["t"] < 10.0, row
    assert row["dialog"] == {"options": ["Do you want to skip\nthe movie?", "Yes", "No"], "active": [0, 1],
                             "selected": 1, "count": 2}, row["dialog"]
    assert row["frame"] > presses[0]["pre"]["frame"] and row["next_page_s"] == 25.0, row
    assert row["left_s"] == round(25.0 - row["t"], 1) and "saved_s" not in row and "length_s" not in row, row
    assert [(c["rule"], c["index"], c["selected"]) for c in out["choices"]] == [("movie_skip", 0, 1)], out["choices"]
    assert out["pages"] == [_O3_PAGE] and len(_presses(log, "page")) >= 1, out["pages"]
    assert out["t"] < 15.0, out["t"]


def test_o3_drive_movie_skip_is_off_without_the_policy(game):
    """No policy, the driver as it is today: during the same movie it presses nothing; a stray Confirm (the
    director's) opens the skip dialog and O1's rule answers it at the game's default (No), the movie resumes and plays
    out, and the outcome carries no ``movies`` key. With the policy ON in that very cell but its press not yet due
    (``after_s`` past the movie), the stray dialog is still O1's to answer -- the policy answers only the dialog its
    own press opened -- and no ``movie`` row opens. Break: answer any skip dialog of a registered cell YES."""
    phases = [(lambda f: f.field_id == 30820, lambda f: f.scene({"movie": 960, "skip": dict(_O3_SKIP)}, _O3_PAGE,
                                                                control=False)),
              (lambda f: f._movie is not None and f.movies[-1]["played"] >= 60,
               lambda f: f.queue.append(["press", "confirm", "4"])),
              (lambda f: _o3_idle(f) and f.movies and f.movies[-1]["end"] is not None, lambda f: _o2_move(f, _O3_END))]
    for policy in (None, _o3_movies(cell={"after_s": 20.0})):
        pred = _o3_pred() if policy is None else _o3_pred(movies=policy)
        out, log, fake = _o3_movie_run(game, pred, list(phases))
        assert not isinstance(out, Exception) and out["end"] == "reached", (policy, out)
        assert fake.answered == [1], (policy, fake.answered)
        assert (fake.movies[0]["played"], fake.movies[0]["skips"], fake.movies[0]["ended"]) == (960, 1, "played")
        assert [(c["index"], c["rule"], c["selected"]) for c in out["choices"]] == [("default", 0, 1)], out["choices"]
        assert _presses(log, "movie_skip") == [] and not [r for r in log if r["k"] == "movie"], policy
        assert ("movies" in out) is (policy is not None) and out.get("movies", []) == [], (policy, out.get("movies"))


def test_o3_drive_movie_skip_presses_only_in_a_registered_cell(game):
    """No press outside a registered cell: the same movie (4 s, its skip dialog) under a policy that registers
    another place ("62"), another SC (1000), or this cell with ``after_s`` past the movie -- each run presses nothing,
    the movie plays out and the run reaches the end with no ``movie`` row. Break: press in any cell."""
    for cell in ({"donor": 30821}, {"sc": 1000}, {"after_s": 20.0}):
        pred = _o3_pred(movies=_o3_movies(cell=cell))
        out, log, fake = _o3_movie_run(game, pred, _o3_movie_route({"movie": 960, "skip": dict(_O3_SKIP)}, _O3_PAGE))
        assert not isinstance(out, Exception) and out["end"] == "reached", (cell, out)
        assert _presses(log, "movie_skip") == [] and out["movies"] == [] and fake.answered == [], (cell, log)
        assert (fake.movies[0]["played"], fake.movies[0]["skips"], fake.movies[0]["ended"]) == (960, 0, "played")


def test_o3_drive_movie_skip_retries_then_gives_up_without_a_void(game):
    """The bounded retries. A hit area that arms 120 frames into the movie (``armed_after``): the first press, a
    quarter second in, finds none; the second -- ``press_every_s`` (2 s) later -- opens the dialog, answered YES:
    skipped after two presses. A movie with no hit area at all (no skip dialog, ever): three presses, each
    ``press_every_s`` after the last, then -- that long after the third -- 'movie-skip missed', no fourth press, and the
    movie plays out: the run reaches the end, never a VOID. (The fake runs about 195 frames a second here: the margins
    hold from about 80 to 240.) Break: drop ``max_presses`` (a fourth press comes)."""
    pred = _o3_pred(movies=_o3_movies(cell={"after_s": 0.25}, press_every_s=2.0))
    out, log, fake = _o3_movie_run(game, pred, _o3_movie_route(
        {"movie": 2400, "skip": dict(_O3_SKIP, armed_after=120)}, _O3_PAGE))
    assert not isinstance(out, Exception) and out["end"] == "reached", out
    row = out["movies"][0]
    assert (row["outcome"], len(row["presses"]), fake.answered) == ("skipped", 2, [0]), (row, fake.answered)
    assert row["presses"][1]["t"] - row["presses"][0]["t"] >= 2.0 - 0.05, row["presses"]
    assert (fake.movies[0]["skips"], fake.movies[0]["ended"]) == (1, "skipped"), fake.movies
    pred = _o3_pred(movies=_o3_movies(cell={"after_s": 0.25}))
    out, log, fake = _o3_movie_run(game, pred, _o3_movie_route({"movie": 1200}, _O3_PAGE))
    assert not isinstance(out, Exception) and out["end"] == "reached" and out["void"] is None, out
    row = out["movies"][0]
    ts = [p["t"] for p in row["presses"]]
    assert len(_presses(log, "movie_skip")) == 3 and len(ts) == 3, row
    assert all(b - a >= 1.0 - 0.05 for a, b in zip(ts, ts[1:])), ts
    assert row["outcome"] == "missed" and row["missed"].startswith("movie-skip missed: no skip dialog after 3 "
                                                                   "press(es)"), row
    assert (fake.movies[0]["played"], fake.movies[0]["ended"]) == (1200, "played") and fake.answered == []
    assert out["pages"] == [_O3_PAGE], out["pages"]


def test_o3_drive_movie_skip_turns_a_page_that_comes_instead(game):
    """A page that opens instead of the skip dialog: the policy's press finds no hit area (none on this movie), the
    movie ends and a page opens before the next press is due -- the ORDINARY page rule turns it (a "page" press, the
    page in ``pages``), nothing is answered as a skip, and the visit's skip is given up there ('movie-skip missed: a
    page opened instead ...'): when a second gap follows (another movie, then a page), the policy presses nothing more.
    Break: keep the visit's row open after the page (a second press lands in the second gap)."""
    pred = _o3_pred(movies=_o3_movies(cell={"after_s": 0.25}, press_every_s=3.0))
    after = "Narrator\n“Act I.”"
    out, log, fake = _o3_movie_run(game, pred, _o3_movie_route({"movie": 120}, _O3_PAGE, {"movie": 1440}, after))
    assert not isinstance(out, Exception) and out["end"] == "reached", out
    assert len(_presses(log, "movie_skip")) == 1 and fake.answered == [], _presses(log, "movie_skip")
    row = out["movies"][0]
    assert row["outcome"] == "missed" and row["missed"].startswith("movie-skip missed: a page opened instead of the "
                                                                   "skip dialog"), row
    assert "The curtain rises." in row["missed"] and out["pages"] == [_O3_PAGE, after], out["pages"]
    whys = [r["why"] for r in log if r["k"] == "press"]
    assert whys[0] == "movie_skip" and whys[1:] and set(whys[1:]) == {"page"}, whys
    assert [m["ended"] for m in fake.movies] == ["played", "played"], fake.movies


def test_o3_drive_movie_skip_refuses_a_dialog_that_is_not_the_skip_text(game):
    """The skip answer requires the skip dialog's TEXT: here the policy's press opens a dialog that asks something
    else ("Do you want to save / the game?", Yes / No, the cursor on No). The policy refuses it (kept on its row as
    ``refused``, once) and the ordinary rules answer it -- a registered rule for it, at its default (No); pressed
    again ``press_every_s`` later, the same; after ``max_presses`` the visit gives up and the movie plays out.
    Nothing is ever answered 0. Break: match the option lines alone (the dialog is then answered YES and the movie
    ends)."""
    save = {"header": "Do you want to save\nthe game?", "options": ["Yes", "No"], "default": 1}
    pred = _o3_pred(movies=_o3_movies(cell={"after_s": 0.25}, max_presses=2))
    pred["choices"] = pred["choices"] + [{"donor": None, "sc": None, "match": "want to save", "pick": "default",
                                          "once": False, "beat": None}]
    out, log, fake = _o3_movie_run(game, pred, _o3_movie_route({"movie": 1200, "skip": save}, _O3_PAGE))
    assert not isinstance(out, Exception) and out["end"] == "reached", out
    assert fake.answered == [1, 1] and (fake.movies[0]["skips"], fake.movies[0]["ended"]) == (2, "played"), \
        (fake.answered, fake.movies)
    row = out["movies"][0]
    assert row["outcome"] == "missed" and len(row["presses"]) == 2 and row["dialog"] is None, row
    assert [r["options"] for r in row["refused"]] == [["Do you want to save\nthe game?", "Yes", "No"]], row["refused"]
    assert [(c["index"], c["rule"]) for c in out["choices"]] == [("default", 1), ("default", 1)], out["choices"]


def test_o3_drive_movie_skip_answers_an_unread_skip_dialog_at_its_default(game):
    """The policy's own press opens a dialog the skip reader refuses and NO frozen rule answers either: the skip dialog
    in a text it cannot read -- the engine localizes it (FieldHUD.cs:281: "Voulez-vous passer / la vidéo ?", Oui / Non,
    under the default US ``match``), or a prompt published EMPTY whose box lacks the match. The policy answers it at the
    game's own default, No -- the engine resumes the movie on any answer but 0 (:428-440) -- keeps it on its row as
    ``refused`` (once), and its attempts count on to 'movie-skip missed': the movie plays out, the run reaches its end,
    never a VOID, and nothing is ever answered 0. Its ``choice`` rows: index "default", rule "movie_skip_default", the
    cursor 1. A dialog no skip dialog can be -- THREE lines (the engine's has two: [PCHC=2,1]) -- is not the policy's to
    answer: with no rule for it the run VOIDs V1, the game's, as with no policy at all. Break: leave every refused
    dialog to the frozen rules (the first dialog then VOIDs V1 'game')."""
    SD = _segment_modules()
    pred = _o3_pred(movies=_o3_movies(cell={"after_s": 0.25}, max_presses=2))
    fr = {"header": "Voulez-vous passer\nla vidéo ?", "options": ["Oui", "Non"]}
    empty = {"header": "", "options": ["Yes", "No"]}
    for dialog in (fr, empty):
        out, log, fake = _o3_movie_run(game, pred, _o3_movie_route({"movie": 1200, "skip": dialog}, _O3_PAGE))
        assert not isinstance(out, Exception) and out["end"] == "reached" and out["void"] is None, (dialog, out)
        assert fake.answered == [1, 1] and (fake.movies[0]["skips"], fake.movies[0]["ended"]) == (2, "played"), \
            (dialog, fake.answered, fake.movies)
        row = out["movies"][0]
        assert row["outcome"] == "missed" and len(row["presses"]) == 2 and row["dialog"] is None, row
        assert "1 dialog(s) refused as not the skip text" in row["missed"], row["missed"]
        assert [r["options"] for r in row["refused"]] == [[dialog["header"], *dialog["options"]]], row["refused"]
        assert [(c["index"], c["rule"], c["selected"]) for c in out["choices"]] == \
            [("default", "movie_skip_default", 1)] * 2, out["choices"]
        assert out["pages"] == [_O3_PAGE], out["pages"]
    three = dict(fr, options=["Oui", "Non", "Plus tard"])
    err, log, fake = _o3_movie_run(game, pred, _o3_movie_route({"movie": 1200, "skip": three}, _O3_PAGE))
    assert isinstance(err, SD.RouteVoid) and (err.v, err.by) == ("V1", "game") and "with no rule" in str(err), err
    assert fake.answered == [] and len(_presses(log, "movie_skip")) == 1, (fake.answered, log)


def test_o2_drive_voids_a_battle_without_a_registry(game):
    """S4 is opt-in (research/o3_design.md 1.2, 1.4): O2-shaped predictions -- no ``battles`` key, or an empty
    registry -- read a battle on screen exactly as O2's driver did: rule 5's V10 (game) with O2's message, the cell
    the place and SC it happened in, and nothing fought. The one test that puts a battle up under O2's shape (G12 runs
    it). Break: run rule 1b with no registry (V10 with the registry's message)."""
    SD = _segment_modules()
    for registry in (None, []):
        fake = FakeGame(game)
        pred = _o2_pred([])
        if registry is not None:
            pred["battles"] = registry
        with session(game, fake) as g:
            _o2_start(g, fake)
            fake.control = False
            g.start_battle(338)
            with pytest.raises(SD.RouteVoid) as err:
                _o2_drive(g, pred, budget=20.0)
        assert (err.value.v, err.value.by, err.value.cell) == ("V10", "game", [30820, 1000]), err.value
        assert str(err.value) == "a battle in 30820 (place 30820) at SC 1000, where the route registers none", err.value
        assert not fake.battle_commands and not [s for s in fake.executed if s[0] in ("battlecmd", "menus")]


def _o3_raw_warp(g, field):
    """start_run's warp shape (no wait for control): the raw step, then the field and FieldHUD."""
    g.send(f"warp {field} -1 -1")
    return g.wait_for(lambda s: s.field_id == field and s.ui_state == "FieldHUD", timeout=10.0, what=f"field {field}")


def _o3_quick_ladder(g):
    """The recovery ladder's two waiting rungs on short clocks: a combo the game swallows would otherwise cost the
    soft reset's 45 s (and close_ui's 20 s) each time."""
    import functools
    g.soft_reset = functools.partial(Session.soft_reset, g, timeout=3.0)
    g.close_ui = functools.partial(Session.close_ui, g, timeout=3.0)


def test_segment_end_run_from_a_battle_on_the_fake(game):
    """S3 on H9's knobs (research/o3_design.md 1.2, B5): the fake as the engine -- a warp refused off the field and
    landing without control, the soft reset where the engine fires it. From BattleHUD mid-fight, end_run resets at
    once: the title, NO warp executed (rows recover-in-battle, recover-reset). From the BattleResult phase of a
    battle's four-phase exit it waits for the field the battle hands over, warps to ``recovery`` (whose script gives
    control, as 4600's does) and climbs the ladder to the title (recover-battle-ending, recover-battle-ended,
    recover-warp). With ``soft_reset_ui`` left at today's default, from BattleHUD the combo is swallowed and end_run
    raises "the title could not be restored". Break: reset in every battle state (in BattleResult the title never
    comes)."""
    from harness.fakegame import SOFT_RESET_ENGINE_UI
    ST = _segment_trace()
    seg = ST.Segment()
    seg.recovery = 30821

    def fake_for(ui, **exit_):
        fake = FakeGame(game)
        fake.warp_field_only, fake.warp_arrive_control = True, False
        if ui is not None:
            fake.soft_reset_ui = ui
        if exit_:
            fake.battle_exit = exit_
        return fake
    fake = fake_for(SOFT_RESET_ENGINE_UI)                    # mid-fight: the reset, no warp
    with session(game, fake) as g:
        boot(g)
        _o3_raw_warp(g, 30820)
        g.start_battle(338)
        _o3_quick_ladder(g)
        mark, log = len(fake.executed), []
        seg.end_run(g, log)
        st = g.state
    assert st.ui_state == "Title" and not st.in_battle and fake.soft_resets == 1, st
    assert log == [{"k": "recover-in-battle", "scene": 338, "ui": "BattleHUD", "result": 0}, {"k": "recover-reset"}], log
    assert not [s for s in fake.executed[mark:] if s[0] == "warp"], fake.executed[mark:]
    fake = fake_for(SOFT_RESET_ENGINE_UI, field=30810, fade_frames=10, result_frames=1200, load_frames=60,
                    arrive_control=False)                    # BattleResult: the field, the warp, the ladder
    stop = threading.Event()
    with session(game, fake) as g:
        boot(g)
        _o3_raw_warp(g, 30820)
        g.start_battle(338)
        _o3_end_on_the_fake(fake, 2)
        published(g, lambda s: s.ui_state == "BattleResult" and s.in_battle)
        _o3_quick_ladder(g)
        _o1_director(fake, stop, [(lambda f: f.field_id == 30821, lambda f: setattr(f, "control", True))])
        log = []
        try:
            seg.end_run(g, log)
        finally:
            stop.set()
        st = g.state
    assert st.ui_state == "Title" and fake.soft_resets == 1, st
    assert [r["k"] for r in log] == ["recover-battle-ending", "recover-battle-ended", "recover-warp"], log
    assert (log[0]["ui"], log[0]["result"], log[1]["field"], log[2]["field"]) == ("BattleResult", 1, 30810, 30821), log
    fake = fake_for(None)                                    # today's default set: swallowed in BattleHUD
    with session(game, fake) as g:
        boot(g)
        _o3_raw_warp(g, 30820)
        g.start_battle(338)
        _o3_quick_ladder(g)
        log = []
        with pytest.raises(HarnessError, match="the title could not be restored"):
            seg.end_run(g, log)
    assert [r["k"] for r in log] == ["recover-in-battle", "recover-reset-failed"] and fake.soft_resets == 0, log


def test_segment_end_run_waits_out_the_battle_load_on_the_fake(game):
    """S3 in a battle exit's LOAD (H9's fourth phase; the review, research/o3_design.md 11.7 #8): the scene is gone
    (``in_battle`` False) while the UI still reads BattleResult until the next field's HUD is up -- where a battle()
    that stopped before FieldHUD (V14 past ``land_cap_s``, the budget inside the landing wait) leaves the run. end_run
    takes the end sequence's path there too: it waits for the field the battle hands over (``recover-battle-ending``,
    ui BattleResult, result 1), then ``recover-battle-ended`` and the warp to ``recovery`` (``recover-warp``), then the
    title. Break: test ``in_battle`` alone (the load takes the outside-a-battle path: the warp refused off FieldHUD,
    ``recover-warp-failed``, the ladder from BattleResult)."""
    from harness.fakegame import SOFT_RESET_ENGINE_UI
    ST = _segment_trace()
    seg = ST.Segment()
    seg.recovery = 30821
    fake = FakeGame(game)
    fake.warp_field_only, fake.warp_arrive_control, fake.soft_reset_ui = True, False, SOFT_RESET_ENGINE_UI
    fake.battle_exit = {"field": 30810, "fade_frames": 10, "result_frames": 10, "load_frames": 1200,
                        "arrive_control": False}
    stop = threading.Event()
    with session(game, fake) as g:
        boot(g)
        _o3_raw_warp(g, 30820)
        g.start_battle(338)
        _o3_end_on_the_fake(fake, 2)
        st = published(g, lambda s: s.ui_state == "BattleResult" and not s.in_battle)
        assert st.field_id == 30810 and st.battle_result == 1, st          # premise: the load, its lag published
        _o3_quick_ladder(g)
        _o1_director(fake, stop, [(lambda f: f.field_id == 30821, lambda f: setattr(f, "control", True))])
        log = []
        try:
            seg.end_run(g, log)
        finally:
            stop.set()
        st = g.state
    assert st.ui_state == "Title" and fake.soft_resets == 1, st
    assert [r["k"] for r in log] == ["recover-battle-ending", "recover-battle-ended", "recover-warp"], log
    assert (log[0]["ui"], log[0]["result"], log[1]["field"], log[2]["field"]) == ("BattleResult", 1, 30810, 30821), log


def test_segment_session_end_leaves_a_movie_on_the_fake(game, tmp_path_factory):
    """S5 on H9's movie beat (research/o3_design.md 1.2, B5): a session whose last run stops inside a movie (61's
    FMV003, where the soft reset is dead). With ``end_session_warps`` the session ends through end_run: the warp to
    ``recovery`` ends the movie (the field load destroys MBG), that field gives control, the ladder reaches the title,
    and ``session["ended"]`` says so. Without it (O1's and O2's default) the bare ladder where the run stopped cannot:
    the movie swallows the combo and the game is left in it. Break: ignore the flag."""
    import shutil
    from harness.fakegame import SOFT_RESET_ENGINE_UI
    control = tmp_path_factory.mktemp("control")
    shutil.copytree(game, control, dirs_exist_ok=True)      # a second fake install, as untouched as the first

    def one(root, warps):
        stub, _pred, calls = _stub_segment(root, cue=lambda n, side: "reached", order=("S",), min_covered=1,
                                           rerun={"max": 0})
        stub.end_session_warps = warps
        fake = FakeGame(root)
        fake.warp_field_only, fake.warp_arrive_control, fake.soft_reset_ui = True, False, SOFT_RESET_ENGINE_UI
        real = stub.drive

        def drive(g, pred, side, log, *, deadline, progress=None):
            out = real(g, pred, side, log, deadline=deadline, progress=progress)
            fake.scene({"movie": 10 ** 6, "skip": dict(_O3_SKIP)}, control=False)       # the run stops in a movie
            published(g, lambda s: not s.control and not s.dialog_open)
            return out
        stub.drive = drive
        stop = threading.Event()
        with session(root, fake) as g:
            boot(g)
            assert g.restore_baseline()[0], "the session starts at the title, as a launch does"
            _o3_quick_ladder(g)
            _o1_director(fake, stop, [(lambda f: f.field_id == 30821, lambda f: setattr(f, "control", True))])
            try:
                stub.run(g)
            finally:
                stop.set()
            at = (g.state.ui_state, fake._movie is not None)
        assert calls == ["S"]
        return json.loads((root / "run" / "zz_session.json").read_text(encoding="utf-8")), at, fake

    sess, at, fake = one(game, True)
    assert sess["ended"] == {"log": [{"k": "recover-warp", "field": 30821}], "ok": True, "why": ""}, sess.get("ended")
    assert at == ("Title", False) and fake.movies[0]["ended"] == "warp", (at, fake.movies)
    sess, at, fake = one(control, False)
    assert "ended" not in sess and at == ("FieldHUD", True), (sess.keys(), at)
    assert fake.movies[0]["end"] is None and fake.soft_resets == 1, (fake.movies, fake.soft_resets)


# ---- O3 itself (studies/story-trace/o3_prima_vista.py; research/o3_design.md section 9, PART C). The draft's members
# are O1's deployed chain; the freeze refuses to overwrite, and refuses a registry row battle_of refuses; the launch's
# own readers (P-DONOR-LOG, P-LAUNCH), P-STOCK-BATTLE and P-SETTINGS, each pure, on synthetic logs, folders and inis.

def _o3_module():
    sys.path.insert(0, str(REPO / "studies" / "story-trace"))
    import o3_prima_vista as P
    return P


def test_o3_draft_members_are_o1s_chain(tmp_path):
    """The draft's members and names are O1's deployed chain, read from its campaign.toml (research/o3_design.md 1.3):
    exactly o1_forks.json's twenty, the route members 31211 -> 61, 31212 -> 62, 31213 -> 63, the start 61 / 31211 and
    the end real 64; o3_forks.json carries the same members and names, deployed, nothing to relaunch, and names both
    legacy defects (the US-bytecode languages, uk's US text). A campaign with any other member -- or another name -- is
    refused. Break: drop the assertion (the draft would register another chain). The chain is a machine-local build:
    where it is not, this SKIPS (and says so) -- never a pass."""
    P = _o3_module()
    if not (P.CHAIN_DIR / "campaign.toml").is_file():
        pytest.skip(f"O1's chain is not built here ({P.CHAIN_DIR}): the O3 draft reads its members from it")
    pred = P.draft_predictions()
    o1 = json.loads(P.O1_MANIFEST.read_text(encoding="utf-8"))
    assert pred["members"] == o1["members"] and pred["names"] == o1["names"], pred["members"]
    assert {f: pred["members"][str(f)] for f in (31211, 31212, 31213)} == {31211: 61, 31212: 62, 31213: 63}
    assert pred["start"] == {"S": 61, "F": 31211} and pred["route"] == [61, 62, 63] and pred["end_fields"] == [64]
    man = json.loads(P.MANIFEST.read_text(encoding="utf-8"))
    assert man["members"] == pred["members"] and man["names"] == pred["names"], man
    assert man["deployed"] is True and man["relaunch_needed"] is False and man["text_block"] == 2, man
    assert man["route_members"] == {"31211": 61, "31212": 62, "31213": 63}, man
    assert any("US bytecode" in d for d in man["known_defects"]) and any("uk/field/2.mes" in d
                                                                          for d in man["known_defects"]), man
    text = (P.CHAIN_DIR / "campaign.toml").read_text(encoding="utf-8")
    for old, new in (("source = 63", "source = 64"), ('name = "O1_TH_STG"', 'name = "O1_TH_STG_X"')):
        assert old in text, old
        bad = tmp_path / "campaign.toml"
        bad.write_text(text.replace(old, new, 1), encoding="utf-8")
        with pytest.raises(AssertionError, match="not O1's twenty"):
            P.chain_from_campaign(bad)


def test_o3_freeze_refuses_an_existing_file(tmp_path, monkeypatch):
    """The freeze (research/o3_design.md 0.1, 2.1): the draft is written ONCE -- LF, sorted keys, its sha the bytes' --
    and a second freeze onto the same file refuses, leaving it byte for byte; the CLI's --freeze refuses the same way.
    Before anything is written, every registry row passes segment_drive.battle_of: a row whose ``won`` would count a
    defeat (3) won is refused and no file appears. The lead freezes after the rehearsals: the real
    o3_predictions_v1.json is never touched here, and the chain the draft reads is given (a synthetic one, O1's ids),
    so the rule is tested wherever the suite runs. Break: drop the battle_of pass (the bad row freezes)."""
    import hashlib
    P = _o3_module()
    o1 = json.loads(P.O1_MANIFEST.read_text(encoding="utf-8"))
    chain = ({int(f): int(d) for f, d in o1["members"].items()},
             {int(f): f"O3_SYNTH_{d}" for f, d in o1["members"].items()})
    monkeypatch.setattr(P, "chain_from_campaign", lambda *a, **k: chain)
    path = tmp_path / "o3_predictions_v1.json"
    sha = P.O3.freeze(path)
    data = path.read_bytes()
    assert sha == hashlib.sha256(data).hexdigest() and b"\r" not in data and data.endswith(b"\n")
    assert data.decode("utf-8") == json.dumps(P.draft_predictions(), indent=1, sort_keys=True) + "\n"
    path.write_bytes(data + b" ")                          # the file as frozen, plus one byte a re-freeze would lose
    with pytest.raises(SystemExit, match="frozen"):
        P.O3.freeze(path)
    seg = P.O3Segment()
    seg.predictions = path
    with pytest.raises(SystemExit, match="frozen"):
        seg.main(["--freeze"])
    assert path.read_bytes() == data + b" "
    good = P.draft_predictions
    monkeypatch.setattr(P, "draft_predictions", lambda: dict(good(), battles=[dict(P.battle_row(), won=[1, 2, 3])]))
    fresh = tmp_path / "o3_predictions_v2.json"
    with pytest.raises(ValueError, match="won is"):
        P.O3.freeze(fresh)
    assert not fresh.exists(), "a refused row was frozen"


#: The launch's Memoria.log as today's reads (2026-09-30): its first line's stamp, a collision for a donor off the
#: route (351, one of Dali's stacked forks), the patchers' "Initialized".
_O3_LOG_HEAD = "30.09.2026 19:27:42 |M| [WindowManager] Moving window to (2045,33) with size (1286,749) on monitor 0\n"
_O3_LOG_351 = ("30.09.2026 19:27:44 |W| [DataPatchers] ForkDonorPatch: donor field 351 is forked by both 30831 and "
               "30842 -> remap DISABLED (ambiguous); an event-battle/scripted-boss after-warp from either fork will "
               "LEAK to real field 351. Deploy only one fork of donor 351 at a time.\n")
_O3_LOG_DONE = "30.09.2026 19:27:44 |M| [DataPatchers] Initialized\n"


def test_o3_p_donor_log_reads_the_launchs_warnings():
    """P-DONOR-LOG (research/o3_design.md 6.2; section 8's p-donor-log unit): the engine's donor map is fixed at
    launch and it logs a collision only as a warning (DataPatchers.cs:156-160), so the launch's own Memoria.log is
    read -- "Initialized" (the patchers ran) and no collision line for 61, 62 or 63. Today's shape (a collision for 351,
    off the route) PASSES; a line "donor field 63 is forked by both 31213 and 31299" FAILS naming it; a log with no
    "Initialized" FAILS (it does not show the patchers ran); a donor 630 is not 63. Break: drop the "Initialized"
    requirement."""
    P = _o3_module()
    route = (61, 62, 63)
    ok, detail = P.p_donor_log(_O3_LOG_HEAD + _O3_LOG_351 + _O3_LOG_DONE, route)
    assert ok and "[351]" in detail, detail
    assert P.donor_log(_O3_LOG_HEAD + _O3_LOG_351 + _O3_LOG_DONE, route) == (True, [])
    w63 = _O3_LOG_351.replace("351", "63").replace("30831 and 30842", "31213 and 31299")
    ok, detail = P.p_donor_log(_O3_LOG_HEAD + _O3_LOG_351 + w63 + _O3_LOG_DONE, route)
    assert not ok and "donor field 63 is forked by both 31213 and 31299" in detail, detail
    assert P.donor_log(_O3_LOG_HEAD + w63 + _O3_LOG_DONE, route) == (True, [w63.strip()])
    ok, detail = P.p_donor_log(_O3_LOG_HEAD + _O3_LOG_351, route)
    assert not ok and "Initialized" in detail, detail
    assert not P.p_donor_log("", route)[0] and not P.p_donor_log(None, route)[0]
    w630 = _O3_LOG_351.replace("351", "630")
    assert P.p_donor_log(_O3_LOG_HEAD + w630 + _O3_LOG_DONE, route)[0], "630 is no route donor"


def _o3_touch(path, when, frac=0.0):
    ts = when.timestamp() + frac
    os.utime(path, (ts, ts))


def test_o3_p_launch_fails_a_patch_file_newer_than_the_launch(tmp_path):
    """P-LAUNCH (research/o3_design.md 6.2, claim integrity #1; section 8's p-launch unit): the launch read its patch
    files once (DataPatchers.Initialize), so every stacked folder's DictionaryPatch/BattlePatch/TextPatch/
    ForkDonorPatch and every Memoria.ini the engine read must be EARLIER than the launch's first Memoria.log stamp, to
    the second. Synthetic folders under a log whose first line is 30.09.2026 19:27:42: all older -- PASS; a
    ForkDonorPatch.txt that HOLDS `31213 63` (P-DONOR passes it) but was touched at 19:27:50 -- FAIL "relaunch" naming
    it; a same-second mtime (19:27:42.4) -- FAIL; Memoria.ini after -- FAIL; a TextPatch.txt after -- FAIL; a stacked
    folder's own Memoria.ini after -- FAIL; a first line with no stamp -- FAIL; a folder with no patch file -- PASS
    (nothing to date). Break: compare with <= (the same second passes)."""
    import datetime as dt
    P = _o3_module()
    log = _O3_LOG_HEAD + _O3_LOG_DONE
    launched = P.launch_time(log)
    assert launched == dt.datetime(2026, 9, 30, 19, 27, 42), launched
    game = tmp_path / "game"
    root, bare = game / "FF9CustomMap", game / "MoguriVideo"
    root.mkdir(parents=True)
    bare.mkdir()
    (game / "Memoria.ini").write_text("[Battle]\nSpeed = 5\n", encoding="utf-8")
    (root / "DictionaryPatch.txt").write_text("FieldScene 31213 11 O1_TSHP_TH_STG O1_TSHP_TH_STG 2\n", encoding="utf-8")
    (root / "BattlePatch.txt").write_text("Battle: 67\nMusic: 0\n", encoding="utf-8")
    fdp = root / "ForkDonorPatch.txt"
    fdp.write_text("31211 61\n31212 62\n31213 63\n", encoding="utf-8")
    before = dt.datetime(2026, 9, 30, 19, 27, 4)
    for p, when in ((game / "Memoria.ini", dt.datetime(2026, 9, 24, 12, 57, 35)), (root / "DictionaryPatch.txt", before),
                    (root / "BattlePatch.txt", dt.datetime(2026, 9, 29, 21, 6, 41)), (fdp, before)):
        _o3_touch(p, when)
    roots = [root, bare]

    def check():
        return P.launch_check(P.launch_files(game, roots), launched)
    ok, detail = check()
    assert ok and "4 file(s) older than the launch at 30.09.2026 19:27:42" in detail, detail
    pred = {"route": [61, 62, 63], "members": {"31211": 61, "31212": 62, "31213": 63}}
    for when, frac in ((dt.datetime(2026, 9, 30, 19, 27, 50), 0.0), (launched, 0.4)):
        _o3_touch(fdp, when, frac)
        assert P.p_donor(pred, roots)[0], "the row is in the file"
        ok, detail = check()
        assert not ok and "relaunch:" in detail and "ForkDonorPatch.txt" in detail, (when, detail)
        assert when.strftime("%H:%M:%S") in detail, detail
    _o3_touch(fdp, before)
    _o3_touch(game / "Memoria.ini", dt.datetime(2026, 9, 30, 19, 30, 0))
    ok, detail = check()
    assert not ok and "Memoria.ini changed at 30.09.2026 19:30:00" in detail, detail
    _o3_touch(game / "Memoria.ini", dt.datetime(2026, 9, 24, 12, 57, 35))
    for extra in (root / "TextPatch.txt", bare / "Memoria.ini"):
        extra.write_text("x\n", encoding="utf-8")
        _o3_touch(extra, dt.datetime(2026, 9, 30, 19, 28, 0))
        ok, detail = check()
        assert not ok and extra.name in detail and "relaunch:" in detail, (extra, detail)
        extra.unlink()
    assert check()[0]
    assert P.launch_time("[DataPatchers] Initialized\n") is None and P.launch_time("") is None
    ok, detail = P.launch_check(P.launch_files(game, roots), P.launch_time("[DataPatchers] Initialized\n"))
    assert not ok and "relaunch" in detail and "cannot be dated" in detail, detail
    ok, detail = P.launch_check(P.launch_files(tmp_path / "nothing", [bare]), launched)
    assert ok and detail.startswith("0 file(s)"), detail


#: Battle 338's names as its US battle text gives them (BSC_TH_E002: three enemies, then six attacks).
_O3_338_NAMES = ["King Leo", "Zenero", "Benero", "Taste steel!", "Poly", "Clamp Pinch", "Pyro", "Clamp Pinch", "Pyro"]


def test_o3_p_stock_battle_finds_an_override_of_338(tmp_path):
    """P-STOCK-BATTLE (research/o3_design.md 6.2, claim integrity #4; section 8's p-stock-battle unit): battle 338
    must be stock on BOTH sides, over every stacked folder. Today's live shape -- FF9CustomMap's four LEDGER scene
    overrides, its BattlePatch `Battle:` 67, 67, 336, 337, 334, 335 and FF9CustomMap-msgs's 67 -- PASSES; plus
    `BattleMap/BattleScene/EVT_BATTLE_TH_E002/dbfile0000.raw16.bytes` FAILS; plus
    `EventBinary/Battle/fr/EVT_BATTLE_TH_E002.eb.bytes` FAILS; plus `Battle: 338` or `Battle: BSC_TH_E002` FAILS; plus
    `AnyEnemyByName: King Leo` FAILS (a name selector applies to every scene holding the name); plus
    `AnyEnemyByName: Goblin` PASSES, listed. And DictionaryPatch (the review, research/o3_design.md 11.7 #4): today's
    four LEDGER `BattleScene` lines PASS, listed; plus `BattleScene 338 LEDGER_A BBG_B251` -- battle 338 rebound to
    another scene, script and background, no file under TH_E002's name, no selector: SceneData's setter overwrites the
    reverse entry the battle is looked up by -- FAILS (c); plus `BattleScene 30999 TH_E002 BBG_B065` (BSC_TH_E002's
    forward entry repointed: 338's sequence, text and background follow it) FAILS (c); a `FieldScene 338 ...` line
    PASSES (it sets only EventDB[338], which a battle never reads), and so does a `BattleScene` line whose id does not
    parse (the engine skips it). Break: drop the name selectors; or drop the DictionaryPatch read."""
    P = _o3_module()
    res = "StreamingAssets/assets/resources"
    n = {"case": 0}
    scenes = ("BattleScene 30871 LEDGER_A BBG_B251", "BattleScene 30872 LEDGER_B BBG_B252",
              "BattleScene 30881 LEDGER1W BBG_B253", "BattleScene 30882 LEDGER1S BBG_B254")

    def stack(paths=(), lines=(), dict_lines=()):
        n["case"] += 1
        base = tmp_path / f"stack{n['case']}"
        custom, msgs = base / "FF9CustomMap", base / "FF9CustomMap-msgs"
        for scene in ("LEDGER1S", "LEDGER1W", "LEDGER_A", "LEDGER_B"):
            for rel in (f"{res}/BattleMap/BattleScene/EVT_BATTLE_{scene}/dbfile0000.raw16.bytes",
                        f"{res}/commonasset/eventengine/eventbinary/Battle/us/EVT_BATTLE_{scene}.eb.bytes"):
                (custom / rel).parent.mkdir(parents=True, exist_ok=True)
                (custom / rel).write_bytes(b"x")
        for rel in paths:
            (custom / rel).parent.mkdir(parents=True, exist_ok=True)
            (custom / rel).write_bytes(b"x")
        (custom / "BattlePatch.txt").write_text(
            "".join(f"Battle: {b}\nMusic: 0\n\n" for b in (67, 67, 336, 337, 334, 335)) + "".join(f"{x}\n" for x in lines),
            encoding="utf-8")
        (custom / "DictionaryPatch.txt").write_bytes(("﻿FieldScene 31213 11 O1_TSHP_TH_STG O1_TSHP_TH_STG 2\r\n"
                                                      + "".join(f"{x}\r\n" for x in (*scenes, *dict_lines))
                                                      ).encode("utf-8"))
        msgs.mkdir(parents=True)
        (msgs / "BattlePatch.txt").write_text("Battle: 67\nMusic: 0\n", encoding="utf-8")
        return [custom, msgs]

    def judge(**kw):
        ok, detail, _info = P.battle_stock(stack(**kw), 338, _O3_338_NAMES)
        return ok, detail
    ok, detail = judge()
    assert ok and "EVT_BATTLE_LEDGER1S" in detail and "FF9CustomMap-msgs Battle: 67" in detail, detail
    assert "no name selector" in detail, detail
    assert "BattleScene lines (none on 338 or TH_E002): FF9CustomMap 30871 LEDGER_A, 30872 LEDGER_B, 30881 LEDGER1W, " \
           "30882 LEDGER1S" in detail, detail
    for line, says in (("BattleScene 338 LEDGER_A BBG_B251", "rebinds battle 338 to BSC_LEDGER_A"),
                       ("BattleScene 30999 TH_E002 BBG_B065", "repoints BSC_TH_E002 to 30999")):
        ok, detail = judge(dict_lines=[line])
        assert not ok and f"(c) FF9CustomMap/DictionaryPatch.txt '{line}' {says}" in detail, (line, detail)
    for line in ("FieldScene 338 11 X X 2", "BattleScene x338 LEDGER_A BBG_B251", "BattleScene 30999 th_e002 BBG_B065"):
        ok, detail = judge(dict_lines=[line])
        assert ok, (line, detail)
    for paths in ([f"{res}/BattleMap/BattleScene/EVT_BATTLE_TH_E002/dbfile0000.raw16.bytes"],
                  [f"{res}/commonasset/eventengine/EventBinary/Battle/fr/EVT_BATTLE_TH_E002.eb.bytes"]):
        ok, detail = judge(paths=paths)
        assert not ok and "(a)" in detail and "EVT_BATTLE_TH_E002" in detail, detail
    for line in ("Battle: 338", "Battle: BSC_TH_E002", "AnyEnemyByName: King Leo", "AnyAttackByName: Clamp Pinch"):
        ok, detail = judge(lines=["", line, "MaxHP: 1"])
        assert not ok and "(b)" in detail and line.split(": ", 1)[1] in detail, (line, detail)
    ok, detail = judge(lines=["AnyEnemyByName: Goblin", "MaxHP: 1"])
    assert ok and "AnyEnemyByName: Goblin" in detail, detail
    ok, detail = judge(lines=["// AnyEnemyByName: King Leo"])       # a comment line: the engine skips it
    assert ok, detail


def _o3_ini(settings, *, extra=""):
    lines = ["[Mod]", "FolderNames = \"FF9CustomMap\"", ""]
    for sec, kv in settings.items():
        lines += [f"[{sec}]", "\t; a comment line, as Memoria.ini's are"]
        lines += [f"{k} = {v}" for k, v in kv.items()]
        lines.append("")
    return "\n".join(lines) + extra


def test_o3_settings_read_the_ini_the_engines_way(tmp_path):
    """P-SETTINGS (research/o3_design.md 6.2, 4.13; section 8's p-settings unit): Memoria.ini read the ENGINE's way
    (Memoria.Prime/Ini/IniReader.cs) -- an ini equal to 4.13 PASSES; `Speed = 0` FAILS naming it; a later duplicate
    assignment wins (either way round); a `;` comment line and an inline `; ...` are no value; `;;` adds one `;` and
    the value ends at the next other character (ReadPair's escape falls through: `a;;b` is "a;"); sections and keys are
    case-sensitive (`speed = 0` is no Speed); a stacked folder's own Memoria.ini is read over the root's, the first
    folder's winning. Break: let the FIRST assignment win; or skip the re-armed escape (`a;;b` reads "a;b")."""
    P = _o3_module()
    want = P.SETTINGS
    game = tmp_path / "game"
    game.mkdir()
    ini = game / "Memoria.ini"

    def judge(text, roots=()):
        ini.write_text(text, encoding="utf-8")
        return P.p_settings(want, P.install_settings(game, list(roots), want))
    ok, detail = judge(_o3_ini(want))
    assert ok and detail.startswith("23 keys as frozen") and 'DialogProgressButtons "Confirm"' in detail, detail
    slow = {**want, "Battle": dict(want["Battle"], Speed="0")}
    ok, detail = judge(_o3_ini(slow))
    assert not ok and detail == "[Battle] Speed = '0' (frozen '5')", detail
    assert not judge(_o3_ini(want, extra="\n[Battle]\nSpeed = 0\n"))[0], "the later assignment wins"
    assert judge(_o3_ini(slow, extra="\n[Battle]\nSpeed = 5\n"))[0], "the later assignment wins"
    assert judge(_o3_ini(want, extra="\n[Battle]\n; Speed = 0\n#Speed = 0\n"))[0], "a comment line is no value"
    assert judge(_o3_ini(want, extra="\n[Battle]\nSpeed = 5 ; the default is 0\n"))[0], "an inline comment"
    # IniReader.ReadPair's escape branch has no `continue`: the `;` it appends arms the escape again, so the value
    # ends at the next character that is not a `;` (IniReader.cs:169-185) -- `a;;b` is "a;", never "a;b"
    for raw, value in (("a;;b ; c", "a;"), ("a;;;;b", "a;;;"), ("a;;", "a;"), ("a;b", "a"), (";x", "")):
        assert P.ini_settings(f"[Lang]\nText = {raw}\n") == {"Lang": {"Text": value}}, (raw, value)
    assert P.ini_settings("[Battle]\nSpeed = 5\nOther = 1\n[Graphics]\nTileSize = 64\n",
                          {"Battle": ["Speed", "SFXRework"]}) == {"Battle": {"Speed": "5"}}, "keys: only those it sets"
    assert judge(_o3_ini(want, extra="\n[Battle]\nspeed = 0\n[battle]\nSpeed = 0\n"))[0], "case-sensitive"
    first, second = tmp_path / "FF9CustomMap", tmp_path / "MoguriMain"
    first.mkdir()
    second.mkdir()
    (second / "Memoria.ini").write_text("[Battle]\nSpeed = 0\n", encoding="utf-8")
    ok, detail = judge(_o3_ini(want), roots=[first, second])
    assert not ok and "[Battle] Speed = '0'" in detail, detail
    (first / "Memoria.ini").write_text("[Battle]\nSpeed = 5\n", encoding="utf-8")
    assert judge(_o3_ini(want), roots=[first, second])[0], "the first folder's wins"
    (second / "Memoria.ini").write_text("[Graphics]\nTileSize = 64\n", encoding="utf-8")
    (first / "Memoria.ini").unlink()
    assert judge(_o3_ini(want), roots=[first, second])[0], "today's MoguriMain: no key of 4.13"
    ini.unlink()
    ok, detail = P.p_settings(want, P.install_settings(game, [], want))
    assert not ok and "[Battle] Enabled = None (frozen '1')" in detail, detail


# ---- O3's rehearsals (studies/story-trace/o3_rehearse.py; research/o3_design.md section 7, PART C, C3), on the fake as
# O3's tests model the engine (H9): warps land without control and are refused off the field, the soft reset fires in
# the engine's UI states. end_run's recovery rung is a registered field off every route whose script hands control
# over, as 4600's does.

def _o3_rehearse_module():
    sys.path.insert(0, str(REPO / "studies" / "story-trace"))
    import o3_rehearse as R
    return R


_O3_RECOVERY = 30899


def _o3_launch_files(game):
    """The fake install as a launch reads it: Memoria.ini stacking FF9CustomMap, the 4.13 settings and the in-game
    language in it; the recovery field registered; every file dated an hour back; a Memoria.log whose first line dates
    the launch NOW, the patchers' 'Initialized' and the US localization in it."""
    P = _o3_module()
    patch = game / "FF9CustomMap" / "DictionaryPatch.txt"
    patch.write_text(patch.read_text(encoding="utf-8")
                     + f"FieldScene {_O3_RECOVERY} 11 RECOVERY RECOVERY {_O3_RECOVERY}\n", encoding="utf-8")
    (game / "Memoria.ini").write_text(_o3_ini(P.SETTINGS) + "\n[VoiceActing]\nForceLanguage = -1\n", encoding="utf-8")
    back = time.time() - 3600
    for p in [game / "Memoria.ini", *(game / "FF9CustomMap").iterdir()]:
        if p.is_file():
            os.utime(p, (back, back))
    now = time.strftime("%d.%m.%Y %H:%M:%S")
    (game / "x64" / "Memoria.log").write_text(
        f"{now} |M| [WindowManager] Moving window to (2045,33)\n{now} |M| [DataPatchers] Initialized\n"
        f"{now} |M| Updating text localization [English(US)]\n", encoding="utf-8")


def _o3_grant_in(fake, stop, field=_O3_RECOVERY):
    """The recovery field's script on the fake: control handed over whenever he stands there idle without it."""
    def loop():
        while not stop.is_set():
            if fake.field_id == field and not fake.control and fake.ui_state == "FieldHUD" and not fake._beats:
                fake.control = True
            time.sleep(0.005)
    threading.Thread(target=loop, daemon=True).start()


def _o3_rehearse_pred(**over):
    """_o3_pred with what O3's trace summary reads too: the legacy battle noise, landing.before (62's ip1285 on the
    fake's places), the end state, the SC and FieldEntrance bytes."""
    return _o3_pred(noise=[{"not_m": 1, "target": "Global.Byte[206]", "why": "King Leo's AI, on the fake"}],
                    landing={"before": {"place": 30821, "sid": 4, "tag": 1, "ip": 1285, "target": "Global.Int16[2]",
                                        "value": 0}},
                    end_state={"Global.Int16[2]": 0}, sc_bytes=[0, 1], entrance_bytes=[2, 3], **over)


#: 338's names on the fake: P-STOCK-BATTLE's census, standing in for the install's scene read.
_O3_CENSUS = staticmethod(lambda name: {"enemies": ["King Leo", "Zenero", "Benero"], "attacks": ["Taste steel!"]})


def test_o3_rehearse_plumbing_on_the_fake(game):
    """C3 (research/o3_design.md 7.1-7.2): one traced stage on the fake, chosen by ``O3_STAGE`` as a launch chooses it
    (another stage, which would run too, does not), played from "61" (a movie, then a page) through "62" (a page, then
    battle 338: King Leo's latch, the four-phase exit into "63") to "63" (a page) and the end "64": the capabilities
    (P-CAP, P-OBJECTS, P-LANG, P-DONOR-LOG and P-LAUNCH on the launch's own Memoria.log), the launch's readings (the
    settings, P-SETTINGS, P-STOCK-BATTLE), New Game, the raw warp at entrance 0 and SC 1155, the beat-table driver with
    the recorder on every poll, the trace collected, end_run to the title through the recovery warp, and
    o3_rehearsal.json holding every section of 7.2 -- no control grant, the pages, the published choices, the press
    evidence (the leave's presses among them), the battle rows with battle_epoch0, fight()'s and leave_battle()'s own
    records, the longest no-progress stretch, the movie's arrival and first page, the end (its state, end_run's
    result and its recovery rows) and O3's trace summary (the start residue, the battle-mode rows, the first field row
    after 62's ip1285, the end cut's row). The rehearsal report prints them. The stage order a launch takes is pinned
    too. Break: drop the battle rows from the record."""
    P, R = _o3_module(), _o3_rehearse_module()
    assert R.select(R.STAGES, env={}) == ["R-START", "F-SMOKE", "R-62", "R-FULL", "R-BATTLE-VOID"]
    assert R.select(R.STAGES, 61, env={}) == ["R-START"] and R.select(R.STAGES, 62, env={}) == ["R-62"]
    assert R.select(R.STAGES, env={"O3_STAGE": "R-SKIP"}) == ["R-SKIP"]
    with pytest.raises(ValueError, match="no stage"):
        R.select(R.STAGES, env={"O3_STAGE": "R-NONE"})
    _o3_launch_files(game)
    stages = {"R-TEST": {"field": 30820, "entrance": 0, "sc": 1155, "end": [_O3_END], "runs": 1, "run_s": 120,
                         "cost_s": 5, "movie": {"donor": 30820}, "settles": "the plumbing"},
              "R-OTHER": {"field": 30821, "entrance": 0, "sc": 1155, "end": [_O3_END], "runs": 1, "run_s": 5,
                          "cost_s": 1, "settles": "never run: O3_STAGE names R-TEST"}}
    pages = ("Narrator\n“Ladies and gentlemen!”", "Cinna\n“Act I!”", "Zidane\n“Phew.”")
    fake = _o3_fake(game, exit_to=30810)
    seen = {}

    def bit191(f, ip):
        f.script_store(0, 0, ip, 191 >> 3, "Bit", 0, bit=191)

    def fight(f):
        f.script_store(4, 1, 1285, 2, "Int16", 0)                       # landing.before: 62's chain row
        seen["epoch"] = f.battle_epoch + 1
        f.start_battle(338, units=_o3_units())
        f.script_store(1, 1, 267, 206, "Byte", 77)                      # King Leo's AI store: a battle-mode row
    phases = [(lambda f: f.field_id == 30820 and f.story_on,
               lambda f: (bit191(f, 22), f.scene({"movie": 120}, pages[0], control=False))),
              (lambda f: f.field_id == 30820 and _o3_idle(f) and f.movies and f.movies[-1]["end"] is not None,
               lambda f: (_o2_move(f, 30821), bit191(f, 26), f.scene(pages[1], control=False))),
              (lambda f: f.field_id == 30821 and _o3_idle(f), fight),
              (lambda f: f.battle_epoch == seen.get("epoch") and f.field_id == 30810 and _o3_idle(f),
               lambda f: (bit191(f, 22), f.scene(pages[2], control=False))),
              (lambda f: f.field_id == 30810 and _o3_idle(f), lambda f: (_o2_move(f, _O3_END), bit191(f, 22)))]
    stop = threading.Event()
    with session(game, fake) as g:
        boot(g)
        assert g.restore_baseline()[0], "a launch starts at the title"
        _o1_director(fake, stop, phases)
        _o3_grant_in(fake, stop)
        try:
            R.run(g, stages=stages, pred=_o3_rehearse_pred(), floor_for=lambda d, closed: _flat_bgi(),
                  prior_for=lambda d: _prior(), stock=lambda fid: None, recovery=_O3_RECOVERY,
                  env={"O3_STAGE": "R-TEST"}, census=_O3_CENSUS.__func__)
        finally:
            stop.set()
        title = g.state.ui_state
    run_dir = game / "run"
    doc = json.loads((run_dir / "o3_rehearsal.json").read_text(encoding="utf-8"))
    assert list(doc["stages"]) == ["R-TEST"] and doc["stages_run"] == ["R-TEST"] and doc.get("finished"), doc.keys()
    caps = {c[1].split(":")[0]: c[0] for c in doc["capabilities"]}
    assert caps == {"P-CAP": True, "P-OBJECTS": True, "P-LANG": True, "P-DONOR-LOG": True, "P-LAUNCH": True}, \
        doc["capabilities"]
    launch = doc["launch"]
    assert launch["roots"] == ["FF9CustomMap"] and launch["settings"] == P.SETTINGS, launch
    assert [(c[0], c[1].split(":")[0]) for c in launch["checks"]] == [(True, "P-SETTINGS"), (True, "P-STOCK-BATTLE")]
    rec = doc["stages"]["R-TEST"][0]
    assert rec["outcome"]["end"] == "reached" and rec["outcome"]["why"] == f"field {_O3_END}", rec["outcome"]
    for section in ("grants", "choices", "published_choices", "pages", "evidence", "battles", "fight", "leave",
                    "no_progress", "movie", "skip", "end", "trace"):
        assert section in rec, section
    assert rec["grants"] == [] and rec["published_choices"] == [] and rec["skip"] is None, rec["grants"]
    assert [p["text"] for p in rec["pages"]] == list(pages), rec["pages"]
    whys = [p["why"] for p in rec["evidence"]["press"]]
    assert whys.count("page") >= 3 and "leave_battle" in whys, whys
    bt = rec["battles"]
    b = bt["rows"]
    assert len(b) == 1 and (b[0]["scene"], b[0]["result"], b[0]["landed"], b[0]["v"]) == (338, 2, 30810, None), b
    assert b[0]["epoch"] == bt["battle_epoch0"] + 1, bt
    assert rec["fight"]["result"] == 2 and rec["fight"]["timed_out"] is False, rec["fight"]
    assert rec["leave"]["presses"] and rec["leave"]["stopped"] in ("scene-gone", "field"), rec["leave"]
    assert rec["no_progress"]["longest_s"] >= 0 and rec["no_progress"]["where"] is not None, rec["no_progress"]
    mv = rec["movie"]
    assert None not in (mv["arrival_frame"], mv["first_page_frame"]) and mv["first_page_frame"] > mv["arrival_frame"], mv
    end = rec["end"]
    assert end["end_state"] == {"Global.Int16[2]": 0}, end
    assert end["end_run"]["ok"] and end["end_run"]["title"] and title == "Title", end["end_run"]
    assert [x["k"] for x in end["end_run"]["how"]] == ["recover-warp"], end["end_run"]["how"]
    tr = rec["trace"]
    assert tr["start"] is not None and [x[1:] for x in tr["residue_before"]] == [[0, 0, 131], [1, 0, 4]], tr
    assert tr["sc"] == [] and tr["battle"]["w"] == 1 and tr["battle"]["sites"] == ["m2 e1 t1 ip267 Global.Byte[206]"]
    assert tr["after_before"] == "30810 e0 t0 ip22 Global.Bit[191]=0", tr["after_before"]
    assert tr["end_row"] == f"w {_O3_END} e0 t0 ip22 Global.Bit[191]=0", tr["end_row"]
    assert (run_dir / rec["trace_file"]).is_file() and (run_dir / rec["log_file"]).is_file()
    report = P.rehearsal_report(run_dir)
    for want in ("== R-TEST: warp 30820 0 1155 -> [30830]", "PASS  P-LAUNCH", "PASS  P-DONOR-LOG",
                 "PASS  P-STOCK-BATTLE", "launch: settings", "grants: 0 (there must be none)",
                 "battle: scene 338 epoch", "landed 30810", "movie: ", "end: state", "rows ['recover-warp']",
                 "trace: start line", "battle-mode w rows 1", "the first field row after 62 ip1285: 30810 e0 t0 ip22",
                 f"the end cut's row: w {_O3_END} e0 t0 ip22"):
        assert want in report, (want, report[:2500])


def test_o3_rehearse_smoke_sends_no_storytrace_on_the_fake(game):
    """F-SMOKE (research/o3_design.md 7.1, F5) on the fake: three members and their stock twins, each by start_run's
    RAW warp (New Game, ``warp <id> 0 1155``, a wait for the field on FieldHUD) -- never Session.warp(), whose wait for
    control the fake (as 61-63) never grants: it would hang 60 s a warp in the game -- then the field's published
    object sids, and end_run after each warp (the recovery warp, the title). No ``storytrace`` step is ever executed
    (no fork data before the freeze). Each member's sids are compared with its twin's: two pairs equal, the third
    (a body missing) different. Break: warp through Session.warp()."""
    P, R = _o3_module(), _o3_rehearse_module()
    _o3_register(game)
    _o3_launch_files(game)
    pairs = [[31211, 30820], [31212, 30821], [31213, 30810]]
    stages = {"F-SMOKE": dict(R.STAGES["F-SMOKE"], pairs=pairs, smoke_s=0.3, warp_s=10.0)}
    sids = {31211: [2, 7, 8, 14, 16], 30820: [2, 7, 8, 14, 16], 31212: [12, 12, 20, 18], 30821: [12, 12, 20, 18],
            31213: [11, 6], 30810: [11, 6, 8]}
    fake = _o3_fake(game)
    fake.blockers = {fid: [{"x": 300.0 + 60 * i, "z": 300.0, "r": 30.0, "sid": s, "uid": 128 + i}
                           for i, s in enumerate(v)] for fid, v in sids.items()}
    stop = threading.Event()
    with session(game, fake) as g:
        boot(g)
        assert g.restore_baseline()[0]
        real_warp = g.warp

        def warp(field, *a, **k):                 # end_run's recovery rung only: the smoke itself warps raw
            if field != _O3_RECOVERY:
                raise AssertionError(f"Session.warp({field}) inside the smoke")
            return real_warp(field, *a, **k)
        g.warp = warp
        _o3_grant_in(fake, stop)
        try:
            R.run(g, stages=stages, pred=_o3_rehearse_pred(), recovery=_O3_RECOVERY, env={"O3_STAGE": "F-SMOKE"},
                  census=_O3_CENSUS.__func__)
        finally:
            stop.set()
    doc = json.loads((game / "run" / "o3_rehearsal.json").read_text(encoding="utf-8"))
    assert doc.get("finished") and "stopped" not in doc, doc.get("stopped")
    assert not [s for s in fake.executed if s[0] == "storytrace"], "a storytrace step in the smoke"
    order = [31211, 31212, 31213, 30820, 30821, 30810]
    recs = doc["stages"]["F-SMOKE"]
    assert [r["field"] for r in recs] == order, recs
    for r in recs:
        reach = r["reached"]
        assert (reach["field"], reach["ui"], reach["control"]) == (r["field"], "FieldHUD", False), r
        assert r["sids"] == sorted(sids[r["field"]]) and r["objects_status"] == "listed", r
        assert r["exceptions"] == [] and isinstance(r["log_lines"], list), r
        assert r["end_run"]["ok"] and r["end_run"]["title"], r["end_run"]
        assert [x["k"] for x in r["end_run"]["how"]] == ["recover-warp"], r["end_run"]
    warps = [s for s in fake.executed if s[0] == "warp"]
    for f in order:
        assert ["warp", str(f), "0", "1155"] in warps and ["warp", str(f), "-1", "-1"] not in warps, (f, warps)
    assert warps.count(["warp", str(_O3_RECOVERY), "-1", "-1"]) == len(order), warps
    twins = doc["twins"]["F-SMOKE"]
    assert [(t["member"], t["twin"], t["equal"]) for t in twins] == [(31211, 30820, True), (31212, 30821, True),
                                                                     (31213, 30810, False)], twins
    report = P.rehearsal_report(game / "run")
    for want in ("== F-SMOKE: the load smoke", "warp 1: 31211 -> field 31211 FieldHUD", "twin 31211 vs 30820: EQUAL",
                 "twin 31213 vs 30810: DIFFERENT"):
        assert want in report, (want, report[:2000])


def test_o3_rehearse_battle_void_stops_mid_fight_on_the_fake(game):
    """R-BATTLE-VOID (research/o3_design.md 7.1, F3) on the fake: the stage's ``battle_override`` (``max_turns`` 0)
    makes fight() raise FightTimeout at the FIRST command prompt -- V15, the driver's, 0 turns, no battlecmd executed --
    so the run stops mid-fight in BattleHUD by construction; end_run then takes S3's soft reset from BattleHUD: the rows
    recover-in-battle (ui BattleHUD, result 0) and recover-reset, no recover-reset-failed, and the title, with no warp.
    F3's rows, as the launch records them. Break: leave the override off (the fight attacks, and runs out of its
    time)."""
    _P, R = _o3_module(), _o3_rehearse_module()
    _o3_launch_files(game)
    stages = {"R-BATTLE-VOID": dict(R.STAGES["R-BATTLE-VOID"], field=30821, end=[_O3_END], run_s=60)}
    fake = _o3_fake(game, exit_to=30810)
    fake.battle_script_end = None                 # nothing would end it: no attack is ever made
    phases = [(lambda f: f.field_id == 30821 and f.story_on, lambda f: f.scene("Cinna\n“Act I!”", control=False)),
              (lambda f: f.field_id == 30821 and _o3_idle(f), lambda f: f.start_battle(338, units=_o3_units()))]
    stop = threading.Event()
    with session(game, fake) as g:
        boot(g)
        assert g.restore_baseline()[0]
        resets = fake.soft_resets                 # the launch's own way to the title, before the stage
        _o1_director(fake, stop, phases)
        try:
            R.run(g, stages=stages, pred=_o3_rehearse_pred(battles=[_o3_row(timeout_s=5)]),
                  floor_for=lambda d, closed: _flat_bgi(), prior_for=lambda d: _prior(), stock=lambda fid: None,
                  recovery=_O3_RECOVERY, env={"O3_STAGE": "R-BATTLE-VOID"}, census=_O3_CENSUS.__func__)
        finally:
            stop.set()
        title = g.state.ui_state
    doc = json.loads((game / "run" / "o3_rehearsal.json").read_text(encoding="utf-8"))
    rec = doc["stages"]["R-BATTLE-VOID"][0]
    assert (rec["outcome"]["end"], rec["outcome"]["v"], rec["outcome"]["by"]) == ("void", "V15", "driver"), rec["outcome"]
    b = rec["battles"]["rows"]
    assert len(b) == 1 and (b[0]["turns"], b[0]["timed_out"], b[0]["v"], b[0]["result"]) == (0, True, "V15", None), b
    assert rec["fight"]["turns"] == 0 and rec["fight"]["timed_out"] is True, rec["fight"]
    assert not [s for s in fake.executed if s[0] == "battlecmd"], "an attack was made"
    er = rec["end"]["end_run"]
    assert [x["k"] for x in er["how"]] == ["recover-in-battle", "recover-reset"], er["how"]
    assert (er["how"][0]["ui"], er["how"][0]["result"], er["how"][0]["scene"]) == ("BattleHUD", 0, 338), er["how"]
    assert er["ok"] and er["title"] and title == "Title" and fake.soft_resets == resets + 1, (er, fake.soft_resets)
    assert not [s for s in fake.executed if s[0] == "warp" and s[1] == str(_O3_RECOVERY)], "end_run warped"
    assert doc.get("finished") and "stopped" not in doc, doc.get("stopped")


def test_o3_rehearse_clears_the_last_fight_between_runs_on_the_fake(game):
    """Each traced run records ITS OWN fight() and leave_battle() (research/o3_design.md 7.2; the review, 11.7 #7):
    the Session clears ``last_fight`` and ``last_leave`` only at a suite member's start, so ``one()`` clears them before
    every run. Two runs of one stage on the fake: run 1 fights battle 338 from "62" (King Leo's latch, the four-phase
    exit into "63") and reaches the end; run 2 never fights -- control comes back in "62", V4 after the settle. Run 1's
    record holds its fight (result 2) and its leave (its presses); run 2's holds None for both, never run 1's. Break:
    drop the clearing (run 2 records run 1's fight and leave as its own)."""
    _P, R = _o3_module(), _o3_rehearse_module()
    _o3_launch_files(game)
    stages = {"R-TWO": {"field": 30821, "entrance": 0, "sc": 1155, "end": [_O3_END], "runs": 2, "run_s": 60,
                        "cost_s": 5, "settles": "each run's own fight and leave"}}
    fake = _o3_fake(game, exit_to=30810)
    seen = {}

    def fight(f):
        seen["epoch"] = f.battle_epoch + 1
        f.start_battle(338, units=_o3_units())
    phases = [(lambda f: f.field_id == 30821 and f.story_on, lambda f: f.scene("Cinna\n“Act I!”", control=False)),
              (lambda f: f.field_id == 30821 and _o3_idle(f), fight),
              (lambda f: f.battle_epoch == seen.get("epoch") and f.field_id == 30810 and _o3_idle(f),
               lambda f: f.scene("Zidane\n“Phew.”", control=False)),
              (lambda f: f.field_id == 30810 and _o3_idle(f), lambda f: _o2_move(f, _O3_END)),
              # run 2 (New Game and the warp again): control comes back in "62" -- no battle, V4 after the settle
              (lambda f: f.field_id == 30821 and f.story_on and not f._beats,
               lambda f: setattr(f, "control", True))]
    stop = threading.Event()
    with session(game, fake) as g:
        boot(g)
        assert g.restore_baseline()[0], "a launch starts at the title"
        _o1_director(fake, stop, phases)
        _o3_grant_in(fake, stop)
        try:
            R.run(g, stages=stages, pred=_o3_rehearse_pred(), floor_for=lambda d, closed: _flat_bgi(),
                  prior_for=lambda d: _prior(), stock=lambda fid: None, recovery=_O3_RECOVERY,
                  env={"O3_STAGE": "R-TWO"}, census=_O3_CENSUS.__func__)
        finally:
            stop.set()
    doc = json.loads((game / "run" / "o3_rehearsal.json").read_text(encoding="utf-8"))
    assert doc.get("finished") and "stopped" not in doc, doc.get("stopped")
    first, second = doc["stages"]["R-TWO"]
    assert first["outcome"]["end"] == "reached" and len(first["battles"]["rows"]) == 1, first["outcome"]
    assert first["fight"]["result"] == 2 and first["leave"]["presses"], (first["fight"], first["leave"])
    assert (second["outcome"]["end"], second["outcome"]["v"]) == ("void", "V4"), second["outcome"]
    assert second["battles"]["rows"] == [], second["battles"]
    assert second["fight"] is None and second["leave"] is None, (second["fight"], second["leave"])


# ---- THE MOVIE-SKIP A/B (studies/story-trace/PLAN.md "Movie skip (opt-in)"): R-FULL-SKIP, the stock rehearsal that
# carries the policy as its own overlay, and ``o3_prima_vista.py --skip-ab``, which reads it against R-FULL.

def test_o3_rehearse_movie_skip_stage_on_the_fake(game):
    """R-FULL-SKIP (PLAN.md "Movie skip (opt-in)"): R-FULL's warp and end with 61's FMV003 registered for skipping. It
    is picked by name only -- never by the default order or by ``--field 61`` -- and carries the policy as its OWN
    prediction overlay, as R-BATTLE-VOID carries its battle_override: stage_pred puts ``movies`` on a copy (checked
    strict: a bad overlay refuses before anything is driven) and leaves the predictions it was given, and the frozen
    v1, without one. On the fake, a stage with a policy plays "61": the policy's press opens the movie's skip dialog,
    answered YES, then the page and the end; its record holds the ``movies`` rows (skipped after one press, the dialog
    as published), the "movie_skip" press among the evidence, the skip dialog among the published choices and its
    ``choice`` row; the rehearsal report prints the skip. Break: drop the overlay in stage_pred (the movie plays out,
    and the record holds no ``movies``)."""
    P, R, SD = _o3_module(), _o3_rehearse_module(), _segment_modules()
    assert "R-FULL-SKIP" not in R.select(R.STAGES, env={}) and R.select(R.STAGES, 61, env={}) == ["R-START"]
    assert R.select(R.STAGES, env={"O3_STAGE": "R-FULL-SKIP"}) == ["R-FULL-SKIP"]
    stage, full = R.STAGES["R-FULL-SKIP"], R.STAGES["R-FULL"]
    warp = ("field", "entrance", "sc", "end")
    assert [stage[k] for k in warp] == [full[k] for k in warp] and "movies" not in full, stage
    fmv = stage["movies"]["cells"][0]                 # FMV003's span: R-FULL's arrival to page 72, not the movie's
    assert fmv["next_page_s"] == 90.0 and "page is 72" in fmv["why"] and "length_s" not in fmv, fmv
    base = _o3_rehearse_pred()
    sp = R.stage_pred(base, stage)
    pol = SD.movies_of(sp)
    assert [(c["donor"], c["sc"]) for c in pol["cells"]] == [(61, 1155)] and pol["policy"] == "skip", pol
    assert "movies" not in base and sp["movies"] == stage["movies"] and sp["movies"] is not stage["movies"]
    frozen = json.loads((REPO / "studies" / "story-trace" / "o3_predictions_v1.json").read_text(encoding="utf-8"))
    assert "movies" not in frozen
    with pytest.raises(ValueError, match="max_presses"):
        R.stage_pred(base, dict(stage, movies=dict(stage["movies"], max_presses=0)))
    _o3_launch_files(game)
    stages = {"R-SKIPTEST": {"field": 30820, "entrance": 0, "sc": 1155, "end": [_O3_END], "runs": 1, "run_s": 60,
                             "cost_s": 5, "movie": {"donor": 30820}, "movies": _o3_movies(),
                             "settles": "the movie-skip plumbing"}}
    fake = _o3_fake(game)

    def bit191(f):
        f.script_store(0, 0, 22, 191 >> 3, "Bit", 0, bit=191)
    phases = [(lambda f: f.field_id == 30820 and f.story_on,
               lambda f: (bit191(f), f.scene({"movie": 6000, "skip": dict(_O3_SKIP)}, _O3_PAGE, control=False))),
              (lambda f: f.field_id == 30820 and _o3_idle(f) and f.movies and f.movies[-1]["end"] is not None,
               lambda f: (_o2_move(f, _O3_END), bit191(f)))]
    stop = threading.Event()
    with session(game, fake) as g:
        boot(g)
        assert g.restore_baseline()[0], "a launch starts at the title"
        _o1_director(fake, stop, phases)
        _o3_grant_in(fake, stop)
        try:
            R.run(g, stages=stages, pred=_o3_rehearse_pred(), floor_for=lambda d, closed: _flat_bgi(),
                  prior_for=lambda d: _prior(), stock=lambda fid: None, recovery=_O3_RECOVERY,
                  env={"O3_STAGE": "R-SKIPTEST"}, census=_O3_CENSUS.__func__)
        finally:
            stop.set()
    run_dir = game / "run"
    doc = json.loads((run_dir / "o3_rehearsal.json").read_text(encoding="utf-8"))
    rec = doc["stages"]["R-SKIPTEST"][0]
    assert rec["outcome"]["end"] == "reached" and doc["stage_defs"]["R-SKIPTEST"]["movies"], rec["outcome"]
    mv = rec["movies"]
    assert len(mv) == 1 and (mv[0]["outcome"], len(mv[0]["presses"]), mv[0]["dialog"]["selected"]) == \
        ("skipped", 1, 1), mv
    assert [p["why"] for p in rec["evidence"]["press"]].count("movie_skip") == 1, rec["evidence"]["press"]
    assert any((c.get("options") or [""])[0].startswith("Do you want to skip") for c in rec["published_choices"])
    assert [(c["rule"], c["index"]) for c in rec["choices"]] == [("movie_skip", 0)], rec["choices"]
    assert fake.answered == [0] and fake.movies[0]["ended"] == "skipped", (fake.answered, fake.movies)
    report = P.rehearsal_report(run_dir)
    assert "movie-skip: 30820 visit 1 skipped" in report, report[:3000]


@pytest.fixture(scope="module")
def o3_stock():
    """The install's stock scripts of 61-64 (what the A/B joins its rows against), or a WARNED skip -- never a silent
    pass (THE WORKTREE SKIP TRAP)."""
    import warnings
    try:
        from ff9mapkit import storytrace
        src = storytrace.stock_script_source()
        assert all(src(f) is not None for f in (61, 62, 63, 64))
    except Exception as err:                                   # noqa: BLE001 -- no install here
        warnings.warn(f"the movie-skip A/B went UNVERIFIED against real bytes in this run: the game install is not "
                      f"readable here ({type(err).__name__}). Run on the machine with the install.", UserWarning)
        pytest.skip("game install unavailable")
    return src


def _o3_ab_launch(run_dir, name, stage, runs):
    """A rehearsal launch as o3_rehearse.py writes one: ``o3_rehearsal.json`` (its stage def, a record a run) and each
    run's trace and driver log -- ``runs`` the A/B's run records (o3_dryrun.ab_run, its ``raw`` rows)."""
    run_dir.mkdir(parents=True, exist_ok=True)
    recs = []
    for r in runs:
        trace, log = f"rh_{name}_{r['n']}.jsonl", f"rh_{name}_{r['n']}_log.json"
        (run_dir / trace).write_text("".join(json.dumps(x) + "\n" for x in r["raw"]), encoding="utf-8")
        (run_dir / log).write_text(json.dumps({"outcome": r["outcome"], "log": r["log"]}), encoding="utf-8")
        recs.append({"stage": name, "n": r["n"], "trace_file": trace, "log_file": log,
                     "outcome": {k: r["outcome"].get(k) for k in ("end", "why", "t")}})
    (run_dir / "o3_rehearsal.json").write_text(json.dumps({"stages_run": [name], "stage_defs": {name: stage},
                                                           "stages": {name: recs}}), encoding="utf-8")
    return run_dir


def test_o3_skip_ab_on_synthetic_traces(o3_stock, tmp_path):
    """The movie-skip A/B (``o3_prima_vista.py --skip-ab``; PLAN.md "Movie skip (opt-in)") on synthetic stock runs --
    real store sites of 61-64, emitted as the engine emits them, each run its own battle noise. Two no-skip and two
    skip runs of the same events read EQUIVALENT (the noise aside), the time saved per run printed; a skip run that
    lacks 61's ``Byte[8] := 125`` (a key DROPPED) differs on writes and history; one whose two 62 ``Byte[4] := 0``
    stores came in the other order (the same keys, a REORDERED history) on history alone; a skip run that played its
    movie out, and a no-skip run that skipped one, are differences -- never a pass. Through the files too: two
    launches written as o3_rehearse.py writes them (R-FULL; R-FULL-SKIP with its policy), paired by warp and end, read
    EQUIVALENT and the CLI exits 0; the no-skip launch against itself holds no policy stage: NOT EQUIVALENT, exit 1.
    Break: read each history as a set (the reordered one then reads EQUIVALENT)."""
    P, R = _o3_module(), _o3_rehearse_module()
    import o3_dryrun as D3
    pred, _sha = P.O3.load(P.PREDICTIONS)

    def ab(b1=None, *, skipped=True, a2_skip=False):
        a = [D3.ab_run(pred, D3.base_events(seed=0), "no-skip", 1),
             D3.ab_run(pred, D3.base_events(seed=1), "no-skip", 2)]
        if a2_skip:                                  # a no-skip run carrying a skipped movie row
            a[1]["log"].insert(1, dict(D3.ab_run(pred, D3.base_events(seed=1), "skip", 2)["log"][1]))
        b = [D3.ab_run(pred, b1 if b1 is not None else D3.base_events(seed=2), "skip", 1, skipped=skipped),
             D3.ab_run(pred, D3.base_events(seed=3), "skip", 2)]
        ok, lines = P.skip_ab_runs(a, b, pred, stock=o3_stock)
        at = next((i for i, x in enumerate(lines) if x.startswith("DIFFERENCES")), None)
        return ok, lines, [] if at is None else [x.strip() for x in lines[at + 1:-1]]
    ok, lines, diffs = ab()
    assert ok and lines[-1].startswith("VERDICT: EQUIVALENT") and diffs == [], lines
    assert any(ln.startswith("time: no-skip 230 s, 230 s (mean 230.0 s)") and "(saved 90.0 s)" in ln for ln in lines)
    ok, lines, diffs = ab(D3.drop(D3.base_events(seed=2), D3.B8_61))
    assert not ok and lines[-1] == "VERDICT: NOT EQUIVALENT", lines
    assert [d.split(":")[0] for d in diffs] == ["skip R-FULL-SKIP#1 writes", "skip R-FULL-SKIP#1 history"], diffs
    assert "61 Byte[8] := 125" in diffs[0] and diffs[1].startswith("skip R-FULL-SKIP#1 history: Global.Byte[8]"), diffs
    ok, lines, diffs = ab(D3._swap(D3.base_events(seed=2), D3.S62[12], D3.S62[13]))
    assert not ok and len(diffs) == 1 and diffs[0].startswith("skip R-FULL-SKIP#1 history: Global.Byte[4]"), diffs
    ok, lines, diffs = ab(skipped=False)
    assert not ok and len(diffs) == 1 and "skipped no movie (movie-skip missed" in diffs[0], diffs
    ok, lines, diffs = ab(a2_skip=True)
    assert not ok and diffs == ["no-skip R-FULL#2 skipped a movie: the no-skip side must play every movie out"], diffs
    a_dir = _o3_ab_launch(tmp_path / "a", "R-FULL", R.STAGES["R-FULL"],
                          [D3.ab_run(pred, D3.base_events(seed=n), "no-skip", n) for n in (1, 2)])
    b_dir = _o3_ab_launch(tmp_path / "b", "R-FULL-SKIP", R.STAGES["R-FULL-SKIP"],
                          [D3.ab_run(pred, D3.base_events(seed=n + 2), "skip", n) for n in (1, 2)])
    ok, text = P.skip_ab(a_dir, b_dir, pred=pred, stock=o3_stock)
    assert ok and text.splitlines()[-1].startswith("VERDICT: EQUIVALENT"), text
    assert ("skip stage R-FULL-SKIP: warp 61 0 1155 -> [64]; policy skip, cells 61@1155 after 10.0 s; paired with "
            "R-FULL") in text, text
    ok, text = P.skip_ab(a_dir, a_dir, pred=pred, stock=o3_stock)
    assert not ok and "holds no stage with a movie-skip policy" in text, text
    assert P.main(["--skip-ab", str(a_dir), str(b_dir)]) == 0
    assert P.main(["--skip-ab", str(a_dir), str(a_dir)]) == 1
