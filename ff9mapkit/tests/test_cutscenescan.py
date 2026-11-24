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
    # C27: the speaker is a NAME the row shows, not one more key behind a "+"
    assert rows[0]["extras"] == ["duration", "tail"] and rows[0]["speaker"] == "Cid"


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
    # a cast scene speaks the build's own conductor sentences (one owner per rule)
    assert any("scene #0: actors entry 'Nobody' is not a defined [[npc]]" in p for p in probs)
    assert any("scene #0: step 0 can't have with_prev" in p for p in probs)
    assert any("scene #0: step 1: only walk/path/animation/turn can run with_prev" in p
               for p in probs)
    assert any("scene #0: step 2 actor 'Ghost' is not in actors" in p for p in probs)
    assert any("scene #0: step 2: movement target 'no_such_marker'" in p for p in probs)
    assert any("scene #1: step 0 (turn) needs a cast" in p for p in probs)


def test_scene_problems_flags_a_raw_reserved_flag_write_with_the_lints_own_sentence():
    """C19: a 'Set flag' step on 8600 (the read-mail payload band) went through every GUI check
    green while lint_flag_bands -- reached only from the CLI -- called it save-corrupting. The tab
    now says the build's own sentence, scene-tagged; the band rule stays the lint's (flags.py)."""
    from ff9mapkit import build as _build
    raw = _raw([{"steps": [{"say": "hi"}]},
                {"steps": [{"say": "hi"}, {"set_flag": [8600, 1]}, {"set_flag": [8712, 1]},
                           {"set_flag": ["glen_done", 1]}]}])
    probs = [p for p in cs.scene_problems(raw) if "8600" in p or "8712" in p]
    lint = [ln for ln in _build.lint_flag_bands(_build.FieldProject(copy.deepcopy(raw), "."))
            if "cutscene" in ln]
    assert len(lint) == 1 and len(probs) == 1, (lint, probs)
    assert probs[0] == "scene #1: " + lint[0], "the tab must say the lint's own sentence"
    assert "step #1" in probs[0]
    # a half-typed doc is this lane's NORMAL input: a garbage step must not raise out of the render
    cs.scene_problems(_raw([{"steps": [5, {"set_flag": [8600, 1]}]}]))


def test_scene_problems_flags_an_undefined_flag_name_with_the_resolvers_own_sentence():
    """C19 (after review): 'Set flag' takes a [[flag]] NAME, so a typo applied clean and PROBLEMS
    stayed green while the build refused the whole field. The tab now says the resolver's own
    sentence (flags.resolve_project_flags owns the rule), and a defined name -- the field's own
    [[flag]] table or the campaign's -- stays silent."""
    from ff9mapkit import flags as _flags
    scene = {"steps": [{"say": "hi"}, {"set_flag": ["glen_dnoe", 1]}]}
    raw = _raw([{"steps": [{"say": "a"}]}, scene])
    raw["flag"] = [{"name": "glen_done", "index": 8712}]
    probs = [p for p in cs.scene_problems(raw) if "glen_dnoe" in p]
    with pytest.raises(ValueError) as ei:
        _flags.resolve_project_flags(copy.deepcopy(raw))
    assert probs == ["scene #1: " + str(ei.value)], probs
    scene["steps"][1]["set_flag"][0] = "glen_done"
    assert cs.scene_problems(raw) == []
    camp = _raw({"requires_flag": "bridge_out", "steps": [{"say": "hi"}]})
    assert any("bridge_out" in p for p in cs.scene_problems(camp))
    assert cs.scene_problems(camp, flag_names={"bridge_out": 8713}) == [], \
        "a campaign-level name is defined"


def _two_cast(steps, **extra):
    """A cast-of-two scene (the multi-actor rules only bite with two) over a doc with Mira."""
    r = _raw({"actors": ["Cid", "Mira"], "steps": steps, **extra})
    r["npc"].append({"name": "Mira", "model": "GEO_SUB_F0_CID", "pos": [-250, -200]})
    return r


def _build_cutscene_problems(raw, tmp_path):
    from ff9mapkit import build as _build
    return [p for p in _build.validate(_build.FieldProject(copy.deepcopy(raw), tmp_path))
            if "cutscene" in p]


_TURN = {"turn": 128, "actor": "Mira"}
# (rule, a scene the build REFUSES, the nearest scene the build ACCEPTS)
_PARITY = [
    ("C7a with_prev group led by a step that cannot run in parallel",
     _two_cast([{"say": "hi"}, {**_TURN, "with_prev": True}]),
     _two_cast([{"turn": 0, "actor": "Cid"}, {**_TURN, "with_prev": True}])),
    ("C7b one actor twice in one parallel group",
     _two_cast([dict(_TURN), {**_TURN, "with_prev": True}]),
     _two_cast([dict(_TURN), {**_TURN, "actor": "Cid", "with_prev": True}])),
    ("C7c an untagged actor step in a cast of two",
     _two_cast([{"turn": 128}]),
     _two_cast([dict(_TURN)])),
    ("C7d a cast scene with no steps",
     _two_cast([]),
     _two_cast([dict(_TURN)])),
    ("C7d a narration scene with no steps",
     _raw({"steps": []}),
     _raw({"steps": [{"say": "hi"}]})),
    ("C7e a tail code the build does not know (cast)",
     _two_cast([{"say": "hi", "tail": "SIDEWAYS"}]),
     _two_cast([{"say": "hi", "tail": "UPR"}])),
    ("C7e a tail code the build does not know (narration)",
     _raw({"steps": [{"say": "hi", "tail": "SIDEWAYS"}]}),
     _raw({"steps": [{"say": "hi", "tail": "UPR"}]})),
    ("C7e a window style the build does not know",
     _raw({"steps": [{"say": "hi", "style": "fancy"}]}),
     _raw({"steps": [{"say": "hi", "style": "notail"}]})),
    ("C8 the player acts outside the cast (the build accepts it)",
     None,
     _raw({"actors": ["Cid"], "steps": [{"walk": [0, 300], "actor": "player"}]})),
]


@pytest.mark.parametrize("rule, refused, accepted", _PARITY, ids=[r[0] for r in _PARITY])
def test_scene_problems_agrees_with_the_build_rule_by_rule(tmp_path, rule, refused, accepted):
    """C7 / C8, THE PARITY FENCE: the tab said 'No structural problems' over conductor blocks the
    build refuses (several made by the tab's own buttons), and flagged actor = "player" outside
    the cast, which the build accepts. For each rule: a block the build refuses is flagged here,
    and the nearest block the build accepts is not."""
    if refused is not None:
        assert _build_cutscene_problems(refused, tmp_path), f"{rule}: the fixture must be refused"
        assert cs.scene_problems(refused), f"{rule}: the build refuses it, the tab says nothing"
    assert _build_cutscene_problems(accepted, tmp_path) == [], f"{rule}: the fixture must build"
    assert cs.scene_problems(accepted) == [], f"{rule}: the build accepts it, the tab flags it"


def test_scene_problems_speaks_the_builds_own_conductor_sentences(tmp_path):
    """One owner per rule: a cast scene's structural sentences are the build's own, prefixed with
    the scene on a dispatch (the build's label rides along as the tab's 'scene #k:')."""
    raw = _two_cast([{"say": "hi"}, {**_TURN, "with_prev": True},
                     {"say": "yo", "tail": "SIDEWAYS", "style": "fancy"}])
    raw["cutscene"] = [{"steps": [{"say": "a"}], "requires_scenario": 5}, raw["cutscene"]]
    ours = cs.scene_problems(raw)
    theirs = _build_cutscene_problems(raw, tmp_path)
    assert ours and all(p.startswith("scene #1: ") for p in ours), ours
    for p in ours:
        assert "[cutscene] #1 " + p[len("scene #1: "):] in theirs, (p, theirs)
    # C16: the cast scene's tail and style are judged here too, in the sweep's own sentences
    assert any("tail 'SIDEWAYS'" in p for p in ours) and any("fancy" in p for p in ours), ours
    assert len(ours) == len(theirs), (ours, theirs)    # nothing the build says twice, or the tab misses
    # a cast scene's bad tail is said once (the window sweep owns it), in the tab and the build
    assert len(cs.scene_problems(_two_cast([{"say": "hi", "tail": "SIDEWAYS"}]))) == 1
    assert len(_build_cutscene_problems(_two_cast([{"say": "hi", "tail": "SIDEWAYS"}]), tmp_path)) == 1
    # a tail that is not text is refused too, never raised out of the render
    assert any("tail" in p for p in cs.scene_problems(_raw({"steps": [{"say": "hi", "tail": ["x"]}]})))
    # and a half-typed cast scene never raises out of the render (a step that is not a table)
    cs.scene_problems(_two_cast([5, dict(_TURN)]))


_HALF_TYPED = [
    ("a step that is not a table", lambda r: r["cutscene"]["steps"].insert(0, 5)),
    ("an [[npc]] row that is not a table", lambda r: r["npc"].append("oops")),
    ("a tail that is a list", lambda r: r["cutscene"]["steps"].insert(0, {"say": "hi",
                                                                          "tail": ["x"]})),
]


@pytest.mark.parametrize("why, spoil", _HALF_TYPED, ids=[h[0] for h in _HALF_TYPED])
def test_a_half_typed_cast_scene_never_reads_as_clean(why, spoil):
    """C7 (after review): any exception in the build's conductor validator made the lane return
    nothing, so a half-typed cast scene with a ghost cast member and an actor outside the cast
    read 'No structural problems'. The sentences found so far stay, and a scene the validator
    could not finish says so."""
    raw = _raw({"actors": ["Cid", "Ghost"], "steps": [{"walk": [0, 0], "actor": "Nobody"}]})
    spoil(raw)
    probs = cs.scene_problems(raw)
    assert any('"Ghost"' in p or "'Ghost'" in p for p in probs), (why, probs)
    assert len(probs) >= 2, (why, probs)       # the actor sentence, or the could-not-finish one


def test_scene_problems_never_resolves_an_animation_name(monkeypatch):
    """C7 (after review): the per-render lane resolved every animation NAME in every cast scene
    through the catalog (tens of ms each, on the GUI thread, on every click). That is the
    explicit Check's job (it reports a name that does not resolve) and the build's."""
    from ff9mapkit import build as _build
    calls = []
    monkeypatch.setattr(_build, "_resolve_actor_animation",
                        lambda *a, **k: calls.append(a) or 0)
    raw = _raw([{"actors": ["Cid"], "steps": [{"animation": "idle", "actor": "Cid"}] * 3}] * 4)
    assert cs.scene_problems(raw) == []
    assert calls == [], f"{len(calls)} name lookups on the render lane"


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


def test_duplicate_scene_never_copies_a_pinned_once_flag():
    """C9: the copy shared its source's explicit once-flag, so whichever scene played first set
    the bit and the other never played. The copy now goes without it (the build gives it its
    own), and the undo label says so."""
    raw = _raw([{"requires_scenario": 5, "flag": 8712, "steps": [{"say": "a"}]}])
    lbl = cs.duplicate_scene(raw, 0)
    assert raw["cutscene"][0]["flag"] == 8712, "the source keeps its flag"
    assert "flag" not in raw["cutscene"][1]
    assert "once-flag" in lbl
    plain = _raw([{"steps": [{"say": "a"}]}])
    assert "flag" not in cs.duplicate_scene(plain, 0), "nothing to say when nothing was pinned"


def test_scene_problems_flags_two_scenes_sharing_one_once_flag():
    raw = _raw([{"requires_scenario": 5, "flag": 8712, "steps": [{"say": "a"}]},
                {"requires_scenario": 6, "flag": 8712, "steps": [{"say": "b"}]}])
    probs = [p for p in cs.scene_problems(raw) if "8712" in p]
    assert len(probs) == 1 and "#0" in probs[0] and "#1" in probs[0], probs
    raw["cutscene"][1]["once"] = False             # a replaying scene never tests its once-flag
    assert not [p for p in cs.scene_problems(raw) if "8712" in p]
    raw["cutscene"][1]["once"] = True
    raw["cutscene"][1]["flag"] = 8713
    assert not [p for p in cs.scene_problems(raw) if "once-flag" in p]
    raw["cutscene"][0]["flag"] = raw["cutscene"][1]["flag"] = [8713]   # half-typed: never raise
    cs.scene_problems(raw)


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


def test_the_scene_settings_help_speaks_plain_words_first():
    """C29: the Scene settings help led with engine names ('the DIRECTOR GATE: only plays when the
    ScenarioCounter == this beat', 'pin THIS gEventGlobal bit'), and the staging summary said 'run
    Check' beside a button titled 'Check the staging' -- a different action."""
    for f in forms.CUTSCENE_SPEC:
        head = f.help.split("(")[0].split(".")[0]
        for word in ("DIRECTOR", "ScenarioCounter", "gEventGlobal", "=="):
            assert word not in head, (f.key, f.help)
    gate = next(f for f in forms.CUTSCENE_SPEC if f.key == "requires_scenario")
    assert gate.help.startswith("only plays while the story is at this beat")
    res = cs.StagingResult(scenes=1, cast_scenes=1, skipped=[("[cutscene]", "unknown marker")])
    assert "run the toolbar Check" in res.summary()
