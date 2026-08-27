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
import pathlib
import sys
import threading
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

from harness import Channel, HarnessError, Session, State          # noqa: E402
from harness.fakegame import FakeGame                              # noqa: E402


@pytest.fixture
def game(tmp_path):
    """A fake install root with a fake FF9 in it, plus its protocol stand-in (not started)."""
    (tmp_path / "x64").mkdir()
    (tmp_path / "x64" / "FF9.exe").write_bytes(b"MZ")
    (tmp_path / "x64" / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    return tmp_path


def session(game_path, fake, **kw):
    """A Session wired to the stand-in: nothing is launched, nothing real is probed."""
    return Session(
        game_path=game_path,
        run_dir=game_path / "run",
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
    assert ch.send(["press confirm 2"]) == 2
    body = (ch.dir / "req.txt").read_text(encoding="utf-8").splitlines()
    assert body[0] == "seq 2"
    assert body[1] == "press confirm 2"


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
        g.newgame()
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
    assert report["passed"] is True
    assert len(report["checks"]) == 2
    assert (game / "run" / "shots" / "after-chest.png").exists()
    assert (game / "run" / "Memoria.log").read_text(encoding="utf-8") == "fake log\n"


def test_walk_holds_the_direction_for_the_requested_frames(game):
    """The button must actually be down in published state -- a no-op walk would fail silently."""
    fake = FakeGame(game, fps=120.0)
    seen = []
    with session(game, fake) as g:
        g.newgame()

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
        g.newgame()
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
