"""Fences for the Cutscene doc tab's Qt-free model layer (:mod:`workspace.cutscenescan`).

Pure-Python — no Qt anywhere in this file. Two fence families matter most:

  * **Drift fences.** ``dispatch_problems`` mirrors ``build.validate``'s gate rule and
    ``stage_verdicts`` re-drives the sentences ``check_staging`` reports — each is fenced
    against the build's OWN output, so if the compiler's rule moves, the mirror goes red
    instead of silently disagreeing (the ``forms.PARALLEL_STEPS`` idiom).
  * **The never-raise contracts.** ``storyboard``/``stage_model`` see half-typed scenes as
    their NORMAL input (an open doc mid-keystroke); a raise there kills the render loop.
"""
from __future__ import annotations

import copy

import pytest

from ff9mapkit.editor import forms
from ff9mapkit.workspace import cutscenescan as cs

# --------------------------------------------------------------------------- fixtures
# The behaviour suite's synthetic floor: x[-300,1000] z[-300,600], with a VERTICAL SLOT
# x[640,680] z[60,600] missing from the upper band (a wall a straight walk can cross).
_HEAD = ('[field]\nid = 4003\nname = "X"\narea = 11\n\n[camera]\nborrow = "c.bgx"\n\n'
         '[walkmesh]\nbgi = "walkmesh.bgi"\n\n'
         '[player]\nspawn = [-200, 500]\n\n'
         '[[npc]]\nname = "Cid"\nmodel = "GEO_SUB_F0_CID"\npos = [0, 400]\n\n'
         '[[marker]]\nname = "altar"\npos = [900, -200]\n\n')


def _mesh_bytes() -> bytes:
    from ff9mapkit.scene import bgi
    xs = (-300, 640, 680, 1000)
    verts = [(x, 0, z) for z in (600, 60, -300) for x in xs]
    tris = [(0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6),
            (4, 5, 9), (4, 9, 8), (5, 6, 10), (5, 10, 9), (6, 7, 11), (6, 11, 10)]
    return bgi.build(verts, tris).to_bytes()


def _wmesh(tmp_path):
    p = tmp_path / "X.field.toml"
    p.write_text(_HEAD, encoding="utf-8")
    (tmp_path / "walkmesh.bgi").write_bytes(_mesh_bytes())
    mesh, why = cs.load_walkmesh(p)
    assert mesh is not None, why
    return mesh


def _raw(cutscene=None):
    """The dict twin of _HEAD (what an open FieldDoc holds), plus an optional cutscene section."""
    r = {
        "field": {"id": 4003, "name": "X", "area": 11},
        "camera": {"borrow": "c.bgx"},
        "walkmesh": {"bgi": "walkmesh.bgi"},
        "player": {"spawn": [-200, 500]},
        "npc": [{"name": "Cid", "model": "GEO_SUB_F0_CID", "pos": [0, 400]}],
        "marker": [{"name": "altar", "pos": [900, -200]}],
    }
    if cutscene is not None:
        r["cutscene"] = cutscene
    return r


# --------------------------------------------------------------------------- projections
def test_gate_text_speaks_each_gate_and_always():
    assert cs.gate_text({}) == "always"
    assert cs.gate_text({"requires_scenario": 100}) == "plays at beat 100"
    assert cs.gate_text({"requires_flag": "chapel_open"}) == "needs flag chapel_open"
    assert cs.gate_text({"requires_flag_clear": 8712}) == "needs flag 8712 clear"
    assert cs.gate_text({"requires_scenario": "dali", "requires_flag": "met_cid"}) == \
        "plays at beat dali · needs flag met_cid"


def test_scene_rows_normalizes_singleton_and_dispatch():
    single = _raw({"actors": ["Cid"], "steps": [{"say": "hi"}]})
    rows = cs.scene_rows(single)
    assert len(rows) == 1 and rows[0]["idx"] == 0 and rows[0]["label"] == "scene #0"
    assert rows[0]["cast"] == ["Cid"] and not rows[0]["narration"] and rows[0]["steps"] == 1

    plural = _raw([{"steps": [{"say": "a"}, {"wait": 30}]},
                   {"actors": ["Cid"], "requires_scenario": 100, "once": False, "steps": []}])
    rows = cs.scene_rows(plural)
    assert [r["label"] for r in rows] == ["scene #0", "scene #1"]
    assert rows[0]["narration"] and rows[0]["steps"] == 2 and rows[0]["once"] is True
    assert rows[1]["gate"] == "plays at beat 100" and rows[1]["once"] is False

    assert cs.scene_rows(_raw()) == []
    assert cs.scene_rows(None) == []


def test_ladder_rows_group_matches_the_compilers_own_rule():
    from ff9mapkit.content.conductor import group_parallel
    steps = [{"say": "hi"}, {"walk": [0, 300], "actor": "Cid"},
             {"turn": 128, "actor": "Cid", "with_prev": True}, {"wait": 30}]
    rows = cs.ladder_rows(_raw({"actors": ["Cid"], "steps": steps}), 0)
    assert [r["idx"] for r in rows] == [0, 1, 2, 3]
    # the fence: rows share a group exactly when group_parallel puts them in one
    expect = {}
    for g, grp in enumerate(group_parallel(steps)):
        for i, _s in grp:
            expect[i] = g
    assert {r["idx"]: r["group"] for r in rows} == expect
    assert rows[2]["with_prev"] and rows[1]["group"] == rows[2]["group"]


def test_ladder_rows_flag_text_and_valueless_kinds():
    steps = [{"say": "hi"}, {"open": "stays up"}, {"raise": True}, {"face_player": True, "actor": "Cid"}]
    rows = cs.ladder_rows(_raw({"actors": ["Cid"], "steps": steps}), 0)
    assert [r["is_text"] for r in rows] == [True, True, False, False]
    assert [r["valueless"] for r in rows] == [False, False, True, True]
    assert rows[3]["actor"] == "Cid"


def test_ladder_rows_survive_garbage_and_keep_authored_indices():
    steps = [{"say": "hi"}, "not a dict", {"wait": 30}]
    rows = cs.ladder_rows(_raw({"steps": steps}), 0)
    assert [r["idx"] for r in rows] == [0, 1, 2]        # authored indices, never compacted
    assert rows[1]["verb"] == "(empty)"
    assert cs.ladder_rows(_raw({"steps": "garbage"}), 0) == []
    assert cs.ladder_rows(_raw(), 5) == []


def test_ladder_rows_list_the_extras_the_editor_should_show():
    steps = [{"say": "hi", "speaker": "Cid", "tail": "UPR", "duration": 90}]
    rows = cs.ladder_rows(_raw({"steps": steps}), 0)
    assert rows[0]["extras"] == ["duration", "speaker", "tail"]


# --------------------------------------------------------------------------- dispatch fence
def test_dispatch_problems_matches_the_builds_own_rule(tmp_path):
    """THE DRIFT FENCE: every sentence the mirror emits must appear verbatim in build.validate's
    own output — if the compiler's gate rule changes shape, this goes red before the GUI lies."""
    from ff9mapkit import build as _build
    colliding = _raw([
        {"requires_scenario": 100, "steps": [{"say": "a"}]},
        {"requires_scenario": 100, "steps": [{"say": "b"}]},
    ])
    ours = cs.dispatch_problems(colliding)
    assert len(ours) == 1 and "the same gate (100, None, None)" in ours[0]
    theirs = _build.validate(_build.FieldProject(copy.deepcopy(colliding), tmp_path))
    for sentence in ours:
        assert sentence in theirs, f"mirror drifted from build.validate:\n{sentence}"


def test_dispatch_problems_catches_two_ungated_and_passes_distinct():
    ungated = _raw([{"steps": [{"say": "a"}]}, {"steps": [{"say": "b"}]}])
    probs = cs.dispatch_problems(ungated)
    assert len(probs) == 1 and "both UNGATED" in probs[0]
    distinct = _raw([{"requires_scenario": 100, "steps": [{"say": "a"}]},
                     {"requires_scenario": 200, "steps": [{"say": "b"}]}])
    assert cs.dispatch_problems(distinct) == []
    assert cs.dispatch_problems(_raw({"steps": [{"say": "solo"}]})) == []


# --------------------------------------------------------------------------- scene problems
def test_scene_problems_names_the_offenders():
    raw = _raw([{
        "actors": ["Cid", "Nobody"],
        "steps": [{"walk": [0, 300], "actor": "Cid", "with_prev": True},
                  {"say": "hi", "with_prev": True},
                  {"walk": "no_such_marker", "actor": "Ghost"}],
    }, {
        "steps": [{"turn": 128}],
    }])
    probs = cs.scene_problems(raw)
    assert any('cast member "Nobody"' in p for p in probs)
    assert any("step 0 can't run with a previous beat" in p for p in probs)
    assert any("step 1 (say) can't run in parallel" in p for p in probs)
    assert any('actor "Ghost" is not in the cast' in p for p in probs)
    assert any('walk target "no_such_marker"' in p for p in probs)
    assert any("scene #1: step 0 (turn) needs a cast" in p for p in probs)


def test_scene_problems_clean_scene_is_silent():
    raw = _raw({"actors": ["Cid"],
                "steps": [{"walk": "altar", "actor": "Cid"},
                          {"say": "made it", "speaker": "Cid"},
                          {"walk": "@player", "actor": "Cid"}]})
    assert cs.scene_problems(raw) == []
    assert cs.scene_problems(_raw()) == []
    assert cs.scene_problems(None) == []


def test_wrap_width_mirrors_the_build(tmp_path):
    from ff9mapkit import build as _build
    for dl in (None, {"wrap": 28}, {"wrap": False}, {"wrap": 0}, {"wrap": True}, {}):
        raw = _raw()
        if dl is not None:
            raw["dialogue"] = dl
        project = _build.FieldProject(copy.deepcopy(raw), tmp_path)
        assert cs.wrap_width(raw) == _build._wrap_width(project), f"diverged on {dl!r}"


# --------------------------------------------------------------------------- stage model
def test_stage_model_places_cast_markers_obstacles_and_chains_legs():
    raw = _raw([{"actors": ["Cid", "player"],
                 "steps": [{"walk": [0, 100], "actor": "Cid"},
                           {"walk": "altar", "actor": "Cid"},
                           {"teleport": [500, 500], "actor": "player"}]}])
    raw["npc"].append({"name": "Mira", "model": "GEO_SUB_F0_CID", "pos": [600, 300]})
    m = cs.stage_model(raw, 0)
    assert [c["name"] for c in m["cast"]] == ["Cid", "player"]
    assert m["cast"][1]["is_player"] and m["cast"][1]["x"] == -200
    assert [o["name"] for o in m["obstacles"]] == ["Mira"]     # non-cast npcs only
    assert [mk["name"] for mk in m["markers"]] == ["altar"]
    # legs chain: Cid pos (0,400) -> (0,100) -> altar (900,-200)
    assert m["legs"][0]["points"] == [(0, 400), (0, 100)]
    assert m["legs"][1]["points"] == [(0, 100), (900, -200)]
    assert m["legs"][2]["kind"] == "teleport" and m["unresolved"] == 0


def test_stage_model_counts_unresolved_and_never_raises():
    raw = _raw({"actors": ["Cid"],
                "steps": [{"walk": "no_such"}, {"walk": [0, 100]}, {"path": ["ghost", [1, 2]]}]})
    m = cs.stage_model(raw, 0)
    assert m["unresolved"] == 2                                # the bad walk + the bad path
    assert len(m["legs"]) == 1                                 # the good walk still draws
    # garbage in, model out — never a raise
    assert cs.stage_model({"cutscene": 17}, 0)["cast"] == []
    assert cs.stage_model(None, 3)["legs"] == []
    assert cs.stage_model({"cutscene": [{"actors": "notalist", "steps": 5}]}, 0)["cast"] == []


# --------------------------------------------------------------------------- storyboard
def test_storyboard_beats_match_group_parallel(tmp_path):
    raw = _raw({"actors": ["Cid"],
                "steps": [{"walk": [0, 300]}, {"turn": 128, "with_prev": True}, {"say": "hi"}]})
    board = cs.storyboard(raw, tmp_path, None, 0)
    assert board["error"] == ""
    assert len(board["beats"]) == 2                            # [walk+turn] then [say]
    b0, b1 = board["beats"]
    assert b0["step_idxs"] == [0, 1] and b1["step_idxs"] == [2]
    assert b0["positions"]["Cid"] == (0, 300)                  # END-of-beat snapshot
    assert b1["say"] == "hi" and b1["positions"]["Cid"] == (0, 300)
    assert b0["legs"][0]["points"] == [(0, 400), (0, 300)]     # from the npc's start pos


def test_storyboard_error_lane_on_an_unknown_name(tmp_path):
    raw = _raw({"actors": ["Cid"], "steps": [{"walk": "no_such_marker"}]})
    board = cs.storyboard(raw, tmp_path, None, 0)
    assert board["beats"] == [] and "no_such_marker" in board["error"]


def test_storyboard_without_mesh_says_legs_run_straight(tmp_path):
    raw = _raw({"actors": ["Cid"], "steps": [{"walk": [900, 400]}]})
    board = cs.storyboard(raw, tmp_path, None, 0)
    assert any("straight" in n for n in board["notes"])
    board2 = cs.storyboard(raw, tmp_path, _wmesh(tmp_path), 0)
    assert not any("straight" in n for n in board2["notes"])
    assert any("no clock" in n for n in board2["notes"])       # the axis note never leaves


def test_storyboard_routes_a_blocked_walk_once_the_mesh_is_warm(tmp_path):
    # (0,400) -> (900,400) crosses the x[640,680] slot in the upper band; the compiler routes it,
    # so the storyboard's leg must be the ROUTED polyline, not the straight fiction.
    raw = _raw({"actors": ["Cid"], "steps": [{"walk": [900, 400]}]})
    board = cs.storyboard(raw, tmp_path, _wmesh(tmp_path), 0)
    assert board["error"] == ""
    (leg,) = board["beats"][0]["legs"]
    assert leg["kind"] == "path" and len(leg["points"]) > 2    # a real detour, not one segment


def test_storyboard_narration_has_text_beats_and_no_legs(tmp_path):
    raw = _raw({"steps": [{"say": "dusk falls"}, {"wait": 30}, {"open": "a bell tolls"}]})
    board = cs.storyboard(raw, tmp_path, None, 0)
    assert board["narration"] and board["error"] == ""
    assert len(board["beats"]) == 3
    assert board["beats"][0]["say"] == "dusk falls" and board["beats"][2]["say"] == "a bell tolls"
    assert all(b["legs"] == [] for b in board["beats"])


def test_storyboard_say_actor_prefers_the_speaker_key(tmp_path):
    raw = _raw({"actors": ["Cid"], "steps": [{"say": "hi", "actor": "Cid", "speaker": "Regent Cid"}]})
    board = cs.storyboard(raw, tmp_path, None, 0)
    assert board["beats"][0]["say_actor"] == "Regent Cid"


# --------------------------------------------------------------------------- verdicts parity
def test_stage_verdicts_parity_with_check_staging(tmp_path):
    """THE PARITY FENCE: the paint lane and the panel lane must report the SAME sentences —
    a verdict painted on the canvas that the panel doesn't list (or vice versa) is two truths."""
    raw = _raw([{"actors": ["Cid"], "steps": [{"walk": [2000, 2000]}]},        # off-mesh target
                {"actors": ["Cid"], "requires_scenario": 100,
                 "steps": [{"walk": [0, 100]}]}])                              # clean
    mesh = _wmesh(tmp_path)
    panel = cs.check_staging(raw, tmp_path, mesh)
    paint = cs.stage_verdicts(raw, tmp_path, mesh)
    assert panel.warnings, "fixture must actually produce a staging problem"
    assert [v["text"] for v in paint] == panel.warnings
    v = paint[0]
    assert v["scene"] == 0 and v["a"] == (0, 400) and v["b"] == (2000, 2000)


def test_stage_verdicts_clean_scene_paints_nothing(tmp_path):
    raw = _raw({"actors": ["Cid"], "steps": [{"walk": [0, 100]}]})
    assert cs.stage_verdicts(raw, tmp_path, _wmesh(tmp_path)) == []
    assert cs.stage_verdicts(raw, tmp_path, None) == []


# --------------------------------------------------------------------------- ops
def test_add_scene_owns_the_dict_to_list_promotion():
    raw = _raw()
    assert cs.add_scene(raw) == "add cutscene scene"
    assert isinstance(raw["cutscene"], list) and len(raw["cutscene"]) == 1   # a LIST from birth
    cs.add_scene(raw)
    assert len(raw["cutscene"]) == 2

    single = _raw({"actors": ["Cid"], "steps": [{"say": "hi"}]})
    cs.add_scene(single)
    assert isinstance(single["cutscene"], list) and len(single["cutscene"]) == 2
    assert single["cutscene"][0]["actors"] == ["Cid"]          # the singleton became block 0


def test_duplicate_scene_deep_copies():
    raw = _raw([{"steps": [{"say": "a"}]}])
    lbl = cs.duplicate_scene(raw, 0)
    assert "duplicate" in lbl and len(raw["cutscene"]) == 2
    raw["cutscene"][1]["steps"][0]["say"] = "changed"
    assert raw["cutscene"][0]["steps"][0]["say"] == "a"        # the original is untouched


def test_delete_scene_removes_one_and_drops_the_emptied_section():
    raw = _raw([{"steps": [{"say": "a"}]}, {"steps": [{"say": "b"}]}])
    assert cs.delete_scene(raw, 0) == "delete cutscene scene #0"
    assert len(raw["cutscene"]) == 1 and raw["cutscene"][0]["steps"][0]["say"] == "b"
    cs.delete_scene(raw, 0)
    assert "cutscene" not in raw                               # no bare section left behind

    single = _raw({"steps": [{"say": "only"}]})
    cs.delete_scene(single, 0)
    assert "cutscene" not in single
    with pytest.raises(IndexError):
        cs.delete_scene(_raw({"steps": []}), 1)


def test_apply_scene_settings_is_authoritative_only_for_managed_keys():
    raw = _raw([{"actors": ["Cid"], "once": False, "warmup": 60, "mystery_key": 7,
                 "steps": [{"say": "kept"}]}])
    managed = ("actors", "once", "requires_scenario")
    cs.apply_scene_settings(raw, 0, {"actors": ["Cid", "player"], "requires_scenario": 100}, managed)
    b = raw["cutscene"][0]
    assert b["actors"] == ["Cid", "player"] and b["requires_scenario"] == 100
    assert "once" not in b                                     # cleared: managed + absent = pop
    assert b["warmup"] == 60 and b["mystery_key"] == 7         # unmanaged keys preserved
    assert b["steps"] == [{"say": "kept"}]                     # steps NEVER touched


def test_step_ops_roundtrip():
    raw = _raw([{"steps": [{"say": "a"}, {"say": "c"}]}])
    cs.add_step(raw, 0, 1, {"say": "b"})
    assert [s["say"] for s in raw["cutscene"][0]["steps"]] == ["a", "b", "c"]

    # update: managed keys authoritative (absent = pop), unmanaged extras preserved
    raw["cutscene"][0]["steps"][1] = {"say": "b", "speaker": "Cid", "mystery": 1}
    cs.update_step(raw, 0, 1, {"wait": 30}, managed=("actor", "with_prev", "speaker"))
    s = raw["cutscene"][0]["steps"][1]
    assert s == {"mystery": 1, "wait": 30}                     # say gone, speaker popped, mystery kept

    cs.duplicate_step(raw, 0, 1)
    assert raw["cutscene"][0]["steps"][2] == {"mystery": 1, "wait": 30}
    raw["cutscene"][0]["steps"][2]["wait"] = 60
    assert raw["cutscene"][0]["steps"][1]["wait"] == 30        # deep copy

    cs.move_step(raw, 0, 2, -1)
    assert raw["cutscene"][0]["steps"][1]["wait"] == 60
    with pytest.raises(IndexError):
        cs.move_step(raw, 0, 0, -1)                            # the boundary raises; the doc disables

    cs.remove_step(raw, 0, 1)
    assert [forms.step_key(s) for s in raw["cutscene"][0]["steps"]] == ["say", "wait", "say"]


def test_set_step_target_rewrites_a_named_target_and_says_so():
    raw = _raw([{"actors": ["Cid"], "steps": [{"walk": "altar"}, {"path": [[0, 0], "altar"]}]}])
    lbl = cs.set_step_target(raw, 0, 0, 111.6, -222.4)
    assert raw["cutscene"][0]["steps"][0]["walk"] == [112, -222]
    assert 'was "altar"' in lbl                                # the meaning change is SAID
    lbl2 = cs.set_step_target(raw, 0, 1, 5, 6, waypoint=1)
    assert raw["cutscene"][0]["steps"][1]["path"][1] == [5, 6] and 'was "altar"' in lbl2
    with pytest.raises(ValueError):
        cs.set_step_target(_raw([{"steps": [{"say": "x"}]}]), 0, 0, 1, 2)


def test_path_point_insert_and_delete():
    raw = _raw([{"actors": ["Cid"], "steps": [{"path": [[0, 0], [100, 100], "altar"]}]}])
    cs.insert_path_point(raw, 0, 0, 0)                         # midpoint of (0,0)-(100,100)
    assert raw["cutscene"][0]["steps"][0]["path"][1] == [50, 50]
    with pytest.raises(ValueError):
        cs.insert_path_point(raw, 0, 0, 3)                     # a NAMED point refuses with a reason
    cs.delete_path_point(raw, 0, 0, 1)
    assert raw["cutscene"][0]["steps"][0]["path"] == [[0, 0], [100, 100], "altar"]
    solo = _raw([{"steps": [{"path": [[0, 0]]}]}])
    with pytest.raises(ValueError):
        cs.delete_path_point(solo, 0, 0, 0)                    # floor: a path keeps >= 1 point


def test_every_op_returns_a_nonempty_label():
    """The undo contract: ops OWN their labels; a blank label would put a nameless step in the
    history menu. (The doc never composes one — this is the whole channel.)"""
    raw = _raw([{"actors": ["Cid"], "steps": [{"walk": [0, 0]}, {"path": [[0, 0], [9, 9]]}]}])
    labels = [
        cs.add_scene(raw),
        cs.duplicate_scene(raw, 0),
        cs.apply_scene_settings(raw, 0, {"once": False}, ("once",)),
        cs.add_step(raw, 0, 0, {"wait": 1}),
        cs.update_step(raw, 0, 0, {"wait": 2}),
        cs.move_step(raw, 0, 0, +1),
        cs.duplicate_step(raw, 0, 0),
        cs.set_step_target(raw, 0, 0, 1, 2),                   # the original walk step
        cs.insert_path_point(raw, 0, 3, 0),
        cs.delete_path_point(raw, 0, 3, 0),
        cs.remove_step(raw, 0, 0),
        cs.delete_scene(raw, 2),
    ]
    assert all(isinstance(x, str) and x for x in labels), labels
