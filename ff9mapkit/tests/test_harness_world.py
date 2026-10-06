"""``tools/harness`` on the OVERWORLD -- the driver's world verbs against the protocol stand-in.

Same contract as ``test_harness.py``: these pin the DRIVER (does it steer on the right space, learn the
camera instead of assuming it, call a wall a wall), and say nothing about the engine -- the live run of
``rimwalk_take8.py`` is that proof. Every case here is written so reverting the rule it pins turns it red.
"""
import math
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from harness import HarnessError, Session                          # noqa: E402
from harness.fakegame import FakeGame                              # noqa: E402


@pytest.fixture
def game(tmp_path):
    (tmp_path / "x64").mkdir()
    (tmp_path / "x64" / "FF9.exe").write_bytes(b"MZ")
    (tmp_path / "x64" / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    mod = tmp_path / "FF9CustomMap"
    mod.mkdir()
    (mod / "DictionaryPatch.txt").write_text("FieldScene 30810 11 CHEST_ROOM CHEST_ROOM 30810\n",
                                             encoding="utf-8")
    return tmp_path


def session(game_path, fake):
    return Session(game_path=game_path, run_dir=game_path / "run", save_dir=game_path / "player-saves",
                   pid_probe=lambda: [], launcher=lambda exe: fake.start(), boot_timeout=15.0,
                   verbose=False)


def on_world(g, fake, x, z, **overworld):
    """Boot, then stand him on the overworld at (x, z) with the given stand-in ground."""
    g.newgame(settle=0)
    fake.overworld = dict({"speed": 1.0, "turn": 2.8125, "cam": 0.0, "lag": 3}, **overworld)
    fake.world.update({"id": 9000, "x": float(x), "z": float(z)})
    fake.ui_state = "WorldHUD"
    g.wait_for(lambda s: s.on_world and s.world_x is not None and s.player_y is not None,
               timeout=5.0, what="the stand-in on the world map")


# --------------------------------------------------------------------------- the space


def test_world_y_is_the_actor_height_and_only_on_the_world(game):
    """player.* is RealPosition x 256 on the overworld; world_y must be the world height, and None on a field."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(30810)
        assert g.state.world_y is None                     # a field's player.y is not a world height
        fake.overworld = {"speed": 1.0, "height": lambda x, z: 3.2}
        fake.world.update({"id": 9000, "x": 100.0, "z": -100.0})
        fake.ui_state = "WorldHUD"
        g.wait_for(lambda s: s.on_world, timeout=5.0)
        g.world_probe()                                    # a step re-grounds him
        assert g.state.world_y == pytest.approx(3.2, abs=1e-6)


def test_world_delta_goes_the_short_way_round_the_seam():
    """x 1530 -> x 6 is +12 east across the seam, not -1524 west across the map."""
    assert Session.world_delta((1530.0, -400.0), (6.0, -400.0)) == pytest.approx((12.0, 0.0))
    assert Session.world_delta((6.0, -400.0), (1530.0, -400.0)) == pytest.approx((-12.0, 0.0))
    assert Session.world_delta((100.0, -10.0), (100.0, -1270.0)) == pytest.approx((0.0, 20.0))


def test_world_verbs_refuse_a_field(game):
    """On a field player.* is the FIELD space: a world verb steering on it would converge on nonsense."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(30810)
        for verb in (lambda: g.world_probe(), lambda: g.world_face(0.0),
                     lambda: g.world_approach(0.0, 10.0, speed=1.0)):
            with pytest.raises(HarnessError, match="OVERWORLD verb"):
                verb()


# --------------------------------------------------------------------------- facing


def test_world_probe_measures_the_camera_heading_not_the_turn_in(game):
    """The actor eases onto the camera's line; a probe from a standstill facing elsewhere must not
    read that curve as the heading. Break: drop the lead-in hold and the heading is ~10 deg off."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_world(g, fake, 400, -400, cam=120.0, lag=6)
        fake._ow_yaw = 0.0                                 # standing facing east, camera at 120
        p = g.world_probe()
        assert p["heading"] == pytest.approx(120.0, abs=1.5), p
        assert p["speed"] == pytest.approx(1.0, rel=0.1)


@pytest.mark.parametrize("turn", [2.8125, -2.8125, 1.3])
def test_world_face_learns_the_bumpers_sign_and_rate(game, turn):
    """Which way L1 turns the heading, and how far a frame, is MEASURED -- both signs converge, and
    a slower rate (a 28 TPS world under a 60 fps render) too. Break: hard-code the guess's sign and
    the reversed case walks away from the bearing until max_rounds."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_world(g, fake, 400, -400, cam=10.0, turn=turn)
        out = g.world_face(135.0, home=(400.0, -400.0), tolerance=4.0)
        assert abs(out["error"]) <= 4.0, out
        assert out["rate"] is not None and math.copysign(1, out["rate"]) == math.copysign(1, turn)
        assert g.state.world_pos == pytest.approx((400.0, -400.0), abs=0.5)   # home kept him on the spot


def test_world_face_from_home_never_wanders_into_the_rock(game):
    """A station is a lawn spot ~20u off a massif. Probes walked end to end ran into rock on almost
    every bearing before the heading settled (the dry run over the real mesh, every station). With a
    home, every hold restarts there. Break: drop the per-hold teleport and the ring stops the probes."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        ring = lambda x, z: math.hypot(x - 400.0, z + 400.0) >= 22.0     # noqa: E731
        on_world(g, fake, 400, -400, cam=200.0, turn=-1.3, blocked=ring)
        out = g.world_face(45.0, home=(400.0, -400.0), tolerance=4.0)
        assert abs(out["error"]) <= 4.0, out
        assert all(r["heading"] is not None and not r["unsettled"] for r in out["rounds"]), out


def test_world_face_refuses_a_camera_the_bumpers_do_not_reach(game):
    """A rotation-locked camera: every correction turns nothing. That must raise, not walk the wrong
    way with a green report. Break: drop the dead-turn count and it exhausts max_rounds silently."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_world(g, fake, 400, -400, cam=10.0, turn=0.0)
        with pytest.raises(HarnessError, match="not reaching the overworld camera"):
            g.world_face(135.0, home=(400.0, -400.0))


def test_world_face_refuses_where_up_does_not_move_him(game):
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_world(g, fake, 400, -400, blocked=lambda x, z: True)
        with pytest.raises(HarnessError, match="did not move him"):
            g.world_face(90.0)


# --------------------------------------------------------------------------- walking


def test_world_approach_calls_a_wall_blocked_where_it_stands(game):
    """A rock face at x >= 430: walking east from 400 stops ~30u in, outcome blocked, height flat."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_world(g, fake, 400, -400, cam=0.0, blocked=lambda x, z: x >= 430.0,
                 height=lambda x, z: 3.2)
        face = g.world_face(0.0, home=(400.0, -400.0))
        walk = g.world_approach(0.0, 80.0, speed=face["speed"])
        assert walk["outcome"] == "blocked", walk
        assert 25.0 <= walk["progress"] <= 31.0, walk
        assert walk["y_max"] == pytest.approx(3.2, abs=1e-6)


def test_world_approach_sees_a_wall_slide_as_blocked(game):
    """A wall at a slant: pressing into it, the engine slides him ALONG it, so he keeps moving. 'Did
    he move' cannot see that; progress along the bearing can. Break: judge the stall on the distance
    moved instead of the progress and the slide reads as a free walk to the end."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_world(g, fake, 400, -400, cam=0.0)
        face = g.world_face(0.0, home=(400.0, -400.0))
        # from here on, walking east is deflected north along a wall: he moves, but not east
        fake.overworld["cam"] = 85.0                       # the stand-in's slide: the line he is pushed along
        walk = g.world_approach(0.0, 80.0, speed=face["speed"])
        assert walk["outcome"] == "blocked", walk
        assert walk["path"] > walk["progress"]


def test_world_approach_records_a_climb_in_the_height_trace(game):
    """Take 3's complaint, as data: a face that does NOT block lets him walk up it. The walk reaches its
    distance and the trace's height rises -- the scenario's verdict reads exactly this."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_world(g, fake, 400, -400, cam=0.0,
                 height=lambda x, z: 3.2 + max(0.0, (x - 420.0)) * 1.2)
        face = g.world_face(0.0, home=(400.0, -400.0))
        walk = g.world_approach(0.0, 40.0, speed=face["speed"])
        assert walk["outcome"] == "reached", walk
        assert walk["y_max"] - 3.2 > 10.0, walk


def test_world_approach_crosses_the_seam_as_one_walk(game):
    """x 1520 east across the seam to x 20: one continuous walk of ~36u, not a 1500u jump backwards.
    Break: measure the step without world_delta and the seam burst reads as a huge negative step."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_world(g, fake, 1520, -400, cam=0.0)
        face = g.world_face(0.0, home=(1520.0, -400.0))
        walk = g.world_approach(0.0, 36.0, speed=face["speed"])
        assert walk["outcome"] == "reached", walk
        assert all(r.get("step", 1.0) > 0 for r in walk["trace"][1:])
        assert g.state.world_x < 100.0                     # he is east of the seam now


def test_world_approach_stops_when_the_world_map_goes(game):
    """A battle (or any scene change) mid-walk ends it as left_world with the state that says where --
    not a stall, and not another burst pressed into the transition."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_world(g, fake, 400, -400, cam=0.0)
        face = g.world_face(0.0, home=(400.0, -400.0))

        def ambush(x, z):
            if x > 415.0:
                fake.ui_state = "BattleHUD"
            return False
        fake.overworld["blocked"] = ambush
        walk = g.world_approach(0.0, 80.0, speed=face["speed"])
        assert walk["outcome"] == "left_world", walk
        assert walk["trace"][-1]["ui"] == "BattleHUD"


def test_world_approach_refuses_to_judge_without_a_speed(game):
    """Blocked on the very first burst with no speed known: blocked, or input that never arrived? It
    cannot say, so it must not say 'blocked'."""
    fake = FakeGame(game)
    with session(game, fake) as g:
        on_world(g, fake, 400, -400, cam=0.0, blocked=lambda x, z: True)
        with pytest.raises(HarnessError, match="no speed is known"):
            g.world_approach(0.0, 40.0)
