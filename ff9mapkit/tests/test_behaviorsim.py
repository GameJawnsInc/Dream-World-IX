"""The offline tick-stepper's fences (rung E1, pure half). The families this instrument
exists to catch are the ones pinned: first-match priority, the hysteresis law (a sticky
decorator's cond is trigger AND keep; latch on cond-fail, never on preemption), the
event-once release (vs. the sticky-once starvation the BTTABLE defect taught), and the
grounded numbers -- Chebyshev proximity, speed units/frame, the compiler's own defaults.
Plus the instrument laws: determinism, and the honesty ledger on its face."""

from __future__ import annotations

from ff9mapkit.workspace import behaviorsim as SIM


def _field(units, npcs=None, **behavior_extra):
    return {
        "player": {"spawn": [0, 0]},
        "npc": npcs or [{"name": "a", "pos": [1000, 0]}, {"name": "b", "pos": [-1000, 0]}],
        "marker": [{"name": "loop", "path": [[0, 0], [400, 0]], "closed": True}],
        "behavior": {"unit": units, **behavior_extra},
    }


def _unit(npc="a", branches=None, **kw):
    return {"npc": npc, "hp": 3, **kw,
            "branch": branches or [{"when": [{"hp_le": 0}], "do": {"die": True}},
                                   {"do": {"hold_post": True}}]}


def test_first_match_wins_and_the_fallback_holds():
    sim = SIM.Sim(_field([_unit("a", [
        {"when": [{"near": ["player", 500]}], "do": {"chase": "player", "speed": 60}},
        {"do": {"hold_post": True}},
    ])]))
    st = sim.at(3)
    assert st["units"]["a"]["sel"] == 1            # player at 0,0 -- 1000 away: fallback
    sim.move_player(3, 900, 0)                     # step inside the 500 box (Chebyshev)
    st = sim.at(5)
    assert st["units"]["a"]["sel"] == 0            # the chase row now outranks


def test_proximity_is_chebyshev_not_euclid():
    sim = SIM.Sim(_field([_unit("a", [
        {"when": [{"near": ["player", 500]}], "do": {"hold_ground": True}},
        {"do": {"hold_post": True}},
    ])]))
    # dx=499, dz=499: Euclid ~705 (outside 500) but Chebyshev 499 -> INSIDE
    sim.move_player(0, 1000 - 499, 499)
    assert sim.at(2)["units"]["a"]["sel"] == 0


def test_movement_is_speed_units_per_frame():
    sim = SIM.Sim(_field([_unit("a", [
        {"do": {"walk_to": [0, 0], "speed": 40}},
    ])]))
    u1 = sim.at(1)["units"]["a"]
    u2 = sim.at(2)["units"]["a"]
    assert abs((u1["x"] - u2["x"]) - 40) < 1e-6    # straight at the target, 40 u/frame


def test_chase_stops_at_the_standoff():
    sim = SIM.Sim(_field([_unit("a", [
        {"do": {"chase": "player", "standoff": 200, "speed": 50}},
    ])]))
    st = sim.at(120)["units"]["a"]
    assert SIM._cheb((st["x"], st["z"]), (0, 0)) >= 140   # never closes past the standoff
    assert SIM._cheb((st["x"], st["z"]), (0, 0)) <= 260   # ...but genuinely arrives at it


def test_swing_kills_and_active_gates_react():
    sim = SIM.Sim(_field([
        _unit("a", [{"when": [{"hp_le": 0}], "do": {"die": True}},
                    {"do": {"hold_post": True}}]),
        _unit("b", [{"when": [{"active": "a"}], "do": {"swing_at": "a", "damage": 1,
                                                       "interval": 10}},
                    {"do": {"hold_post": True}}]),
    ]))
    st = sim.at(40)                                # strikes at ticks 1,11,21 -> hp 0
    assert not st["units"]["a"]["alive"]
    assert st["units"]["b"]["sel"] == 1            # the active gate released the swing
    assert any(e.kind == "die" for e in sim.events)


def test_sticky_once_latches_on_cond_fail_not_on_preemption():
    tree = [
        {"when": [{"hp_le": 0}], "do": {"die": True}},
        {"when": [{"near": ["player", 800]}], "do": {"chase": "player", "speed": 1},
         "once": True},
        {"do": {"hold_post": True}},
    ]
    sim = SIM.Sim(_field([_unit("a", tree)]))
    sim.move_player(0, 400, 0)                     # inside 800 of a@(1000,0)
    assert sim.at(2)["units"]["a"]["sel"] == 1     # engagement open
    # walk the player away -> the keep FAILS -> the once latches
    sim.move_player(4, -3000, 0)
    sim.at(6)
    sim.move_player(8, 400, 0)                     # back inside: latched, never again
    assert sim.at(10)["units"]["a"]["sel"] == 2


def test_event_once_fires_and_releases_never_starves():
    # the BTTABLE round-2 family: an announce over a MONOTONIC cond. Sticky would hold
    # selection forever; the event-once fires once and the rows below keep working.
    tree = [
        {"when": [{"counter_ge": ["wave", 1]}], "do": {"announce": "WAVE!"}, "once": True},
        {"do": {"patrol": "loop"}},
    ]
    sim = SIM.Sim(_field([_unit("a", tree)], counters=["wave"], timer=100,
                         table=[{"name": "sched", "values": [99]}],
                         schedule=[{"counter": "wave", "table": "sched"}]))
    st = sim.at(60)                                # remaining<99 within 2s -> wave=1
    assert st["counters"]["wave"] >= 1
    assert sum(1 for e in sim.events if e.kind == "announce") == 1   # exactly once
    assert st["units"]["a"]["sel"] == 1            # released: the patrol still runs


def test_flee_picks_the_first_uncamped_refuge():
    tree = [{"do": {"flee": "player", "to": [[300, 0], [-1500, 0]], "avoid_r": 600,
                    "speed": 50}}]
    sim = SIM.Sim(_field([_unit("a", tree)]))
    st = sim.at(30)["units"]["a"]                  # player@0,0 camps refuge 1 (300 away)
    assert st["x"] < 0                             # -> runs for the SECOND refuge
    sim2 = SIM.Sim(_field([_unit("a", tree)]))
    sim2.move_player(0, 5000, 5000)                # nobody camping -> first refuge
    st2 = sim2.at(30)["units"]["a"]
    assert st2["x"] > 0


def test_alternator_flips_and_timer_bands_gate():
    tree = [
        {"when": [{"flag": "shift"}], "do": {"hold": [500, 0]}},
        {"when": [{"time_below": 99}], "do": {"hold": [-500, 0]}},
        {"do": {"hold_post": True}},
    ]
    sim = SIM.Sim(_field([_unit("a", tree)], timer=100,
                         alternators=[{"name": "shift", "frames": 10}]))
    assert sim.at(5)["units"]["a"]["sel"] == 2     # tick 5: flag 0, remaining > 99
    assert sim.at(15)["units"]["a"]["sel"] == 0    # ticks 10..19: the alternator is up
    assert sim.at(45)["units"]["a"]["sel"] == 1    # flag down again; 100-45/30 < 99


def test_class_rows_share_the_program_per_member():
    raw = _field([{"npcs": ["a", "b"], "class": "pair", "hp": 2,
                   "branch": [{"when": [{"near": ["player", 1200]}],
                               "do": {"chase": "player", "speed": 30}},
                              {"do": {"hold_post": True}}]}],
                 brains=True)
    sim = SIM.Sim(raw)
    st = sim.at(10)
    assert st["units"]["a"]["sel"] == 0 and st["units"]["b"]["sel"] == 0
    assert st["units"]["a"]["unit"] == st["units"]["b"]["unit"] == "pair"
    assert st["units"]["a"]["x"] < 1000 and st["units"]["b"]["x"] > -1000  # both walking


def test_determinism_and_the_honesty_ledger():
    raw = _field([_unit("a", [{"do": {"wander": [0, 0], "radius": 300}}]),
                  {"npc": "b", "hp": 1, "pooled": True, "pool": "p",
                   "branch": [{"do": {"hold_post": True}}]}],
                 pool=[{"name": "p", "price": 10}])
    s1, s2 = SIM.Sim(raw), SIM.Sim(raw)
    assert s1.at(200) == s2.at(200)                # same doc -> identical history
    assert any("STRAIGHT lines" in n for n in s1.notes)
    assert any("pooled" in n for n in s1.notes)    # the ledger names the dormant unit
    assert s1.at(200)["units"]["b"]["dormant"]


def test_cooldown_announce_is_an_event_and_the_greet_pair_unlatches():
    """THE HANGOUT GREET LATCH: two neighbours wander overlapping boxes and
    announce at each other on a near(partner) cond under ``cooldown``. Sticky
    engagement deadlocks the pair in-engine -- selecting the announce HALTS
    both walkers (the dispatch-halt), so near() never re-falsifies and both
    hold selection forever (the owner's playtest: statues after the first
    exchange). The event-cooldown fires, arms its timer AT DELIVERY, and
    releases: greet -> part -> wander -> greet again."""
    npcs = [{"name": "a", "pos": [320, 0]}, {"name": "b", "pos": [-320, 0]}]
    units = [
        _unit("a", [{"when": [{"near": ["b", 300]}],
                     "do": {"announce": "hi"}, "cooldown": 100},
                    {"do": {"wander": [320, 0], "radius": 350, "speed": 25}}]),
        _unit("b", [{"when": [{"near": ["a", 300]}],
                     "do": {"announce": "yo"}, "cooldown": 120},
                    {"do": {"wander": [-320, 0], "radius": 350, "speed": 25}}]),
    ]
    sim = SIM.Sim(_field(units, npcs=npcs))
    sim.run_to(1500)
    fires = {n: [e.tick for e in sim.events if e.unit == n and e.kind == "announce"]
             for n in ("a", "b")}
    # both greet MORE THAN ONCE -- the un-latch fence -- and the timer gates
    for n, cd in (("a", 100), ("b", 120)):
        assert len(fires[n]) >= 2, f"{n} never re-greeted: {fires[n]}"
        assert all(g >= cd for g in
                   (t2 - t1 for t1, t2 in zip(fires[n], fires[n][1:])))
    # selection releases the tick after a fire (never a held engagement), and
    # the pair genuinely parts and keeps living between greets
    first = min(fires["a"] + fires["b"])
    longest = {n: 0 for n in fires}
    run = {n: 0 for n in fires}
    moved = {n: 0.0 for n in fires}
    prev: dict = {}
    for t in range(first, min(first + 600, 1500)):
        units_t = sim.at(t)["units"]
        for n in fires:
            u = units_t[n]
            if n in prev:
                moved[n] += max(abs(u["x"] - prev[n][0]), abs(u["z"] - prev[n][1]))
            prev[n] = (u["x"], u["z"])
            run[n] = run[n] + 1 if u["sel"] == 0 else 0
            longest[n] = max(longest[n], run[n])
    for n in fires:
        assert longest[n] <= 3, f"{n} held the greet row {longest[n]} ticks"
        assert moved[n] > 200, f"{n} statued after the greet ({moved[n]:.0f}u)"


# --------------------------------------------------------------------------- the tab's sim mode
# Qt half: the strip appears, stepping paints ghosts + sweeps the ladder, an edit exits sim,
# and the honesty caption is ON THE FACE. The interpreter itself is pinned above, Qt-free.
def _qt_doc():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from ff9mapkit.workspace.behaviordoc import BehaviorDoc
    from ff9mapkit.workspace.shell import pick_palette
    return BehaviorDoc(pick_palette("dark"))


def _scene_tags(canvas):
    return [it.data(0) for it in canvas._scene.items() if it.data(0)]


def test_sim_mode_steps_ghosts_and_sweeps_the_ladder():
    doc = _qt_doc()
    doc.show_field("SIMF", _field([_unit("a", [
        {"when": [{"near": ["player", 5000]}], "do": {"chase": "player", "speed": 50}},
        {"do": {"hold_post": True}},
    ])]), None)
    assert not doc.sim_bar.isVisible() if doc.isVisible() else doc.sim_bar.isHidden()
    doc.sim_btn.setChecked(True)
    assert not doc.sim_bar.isHidden()              # the strip is up
    # honesty ON THE FACE, one line: the short tags render, the full sentences ride
    # the tooltip (the 4-line wrap starved the strip — snap-caught), and the latest
    # event owns its OWN label so it can never starve the scrub slider again
    assert doc.sim_note.fullText().startswith("offline approximation")
    assert "straight walks" in doc.sim_note.fullText()
    assert "STRAIGHT lines" not in doc.sim_note.fullText()   # sentences live on hover...
    assert "STRAIGHT lines" in doc.sim_note.toolTip()        # ...and must all be there
    assert doc.sim_slider.minimumWidth() >= 100    # the slider cannot be starved to a sliver
    tags = _scene_tags(doc.canvas)
    assert "sim" in tags and "simplayer" in tags   # boot ghosts painted
    doc._sim_show(10)
    st = doc._sim.at(10)
    assert st["units"]["a"]["x"] < 1000            # the ghost genuinely walked
    assert doc.ladder._prios[0].text().startswith("▶")      # the sweep marks row 1
    assert not doc.ladder._prios[1].text().startswith("▶")
    doc._sim_move_player(4000, 0)                  # click = move the sim player...
    assert doc._sim.player_at(10) == (4000.0, 0.0)
    doc.sim_btn.setChecked(False)
    assert doc.sim_bar.isHidden()
    assert "sim" not in _scene_tags(doc.canvas)    # ghosts cleared with the mode


def test_an_edit_exits_sim_mode_and_stage_edit_is_exclusive():
    from ff9mapkit.workspace import behaviorscan
    doc = _qt_doc()
    doc.show_field("SIMF", _field([_unit("a")]), None)
    doc.sim_btn.setChecked(True)
    behaviorscan.add_branch(doc._raw, "a")
    doc._after_edit("add branch")                  # any committed edit voids the timeline
    assert not doc.sim_btn.isChecked()
    doc.sim_btn.setChecked(True)
    doc.edit_btn.setChecked(True)                  # stage edit kicks sim out...
    assert not doc.sim_btn.isChecked()
    doc.sim_btn.setChecked(True)                   # ...and sim kicks stage edit out
    assert not doc.edit_btn.isChecked()


def test_the_siege_view_simulates_readonly():
    import copy
    import importlib.util
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "ff9mapkit" / "tests" / "test_siege.py"
    spec = importlib.util.spec_from_file_location("_siege_fx_sim", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    doc = _qt_doc()
    doc.show_field("REDOUBT", {"field": {"name": "REDOUBT"}, "player": {"spawn": [0, -600]},
                               "siege": copy.deepcopy(mod.RAW)}, None)
    doc.sim_btn.setChecked(True)                   # a read-only view still SIMULATES
    assert doc.sim_btn.isChecked() and not doc.sim_bar.isHidden()
    doc._sim_show(30)
    assert doc._sim.at(30)["units"]                # the generated army ticks
