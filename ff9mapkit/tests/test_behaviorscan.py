"""Fences for the Behavior tab's pure half (:mod:`ff9mapkit.workspace.behaviorscan`).

No Qt anywhere in this file -- the projections are plain data over a raw field dict. The laws:
the vocabulary is DERIVED from behaviortoml's own verb tables (never a hand-copied list);
formatting is LENIENT (an invalid doc renders as written -- validate() owns the refusing);
geometry SKIPS what it cannot resolve rather than raising. The showpiece fixture lives in
``test_behaviordoc.py`` (one owner, shared with gui_snap); this file uses minimal targeted
dicts so each fence names exactly what it pins."""

from __future__ import annotations

from ff9mapkit.content import behaviortoml as BT
from ff9mapkit.workspace import behaviorscan as BS


def _field(units, **behavior_extra):
    return {
        "player": {"spawn": [0, 0]},
        "npc": [{"name": "a", "pos": [100, 200]}, {"name": "b", "pos": [700, -300]}],
        "marker": [{"name": "loop", "path": [[0, 0], [100, 0], [100, 100]], "closed": True},
                   {"name": "nook", "pos": [900, 900]}],
        "behavior": {"unit": units, **behavior_extra},
    }


def _unit(npc="a", branches=None):
    return {"npc": npc, "hp": 3,
            "branch": branches or [{"when": [{"hp_le": 0}], "do": {"die": True}},
                                   {"do": {"hold_post": True}}]}


def test_has_behavior_needs_unit_rows():
    assert not BS.has_behavior({})
    assert not BS.has_behavior({"behavior": {}})
    assert BS.has_behavior(_field([_unit()]))


def test_summary_speaks_real_plurals():
    raw = _field([_unit()], timer=90, table=[{"name": "t", "values": [1]}])
    s = BS.summary(raw)
    assert "1 unit" in s and "1 units" not in s
    assert "1 table" in s and "timer 90s" in s


def test_cond_and_action_formatting_uses_the_toml_vocabulary():
    assert BS.fmt_cond({"near": ["b", 900]}) == "near b 900"
    assert BS.fmt_cond({"hp_le": 0}) == "hp_le 0"
    assert BS.fmt_cond({"counter_ge": ["wave", 2]}) == "counter_ge wave 2"
    verb, detail = BS.fmt_action({"flee": "b", "to": ["nook"], "speed": 75})
    assert verb == "flee" and detail == "b · to nook · speed 75"
    assert BS.fmt_action({"die": True}) == ("die", "")


def test_unknown_verbs_render_as_written_never_raise():
    # the LENIENT twin of BT._one_verb: the view shows the text, validate() owns the error
    assert BS.fmt_cond({"nearr": ["b", 1]}).startswith("? ")
    verb, detail = BS.fmt_action({"telport": [1, 2]})
    assert verb == "?" and "telport" in detail


def test_every_cond_and_action_verb_formats():
    """The anti-rot fence: a NEW verb in the compiler's tables must render, not crash --
    the GUI derives its vocabulary from these dicts, so this sweep IS the derivation proof."""
    for v in BT.COND_VERBS:
        out = BS.fmt_cond({v: ["x", 1]})
        assert out.startswith(v), out
    for v in BT.ACTION_VERBS:
        verb, _detail = BS.fmt_action({v: "x"})
        assert verb == v


def test_ladder_rows_carry_conds_decos_and_the_fallback_mark():
    raw = _field([_unit(branches=[
        {"when": [{"active": "b"}, {"near": ["b", 400]}], "do": {"swing_at": "b", "damage": 2},
         "once": True, "cooldown": 40, "raise_flags": ["alarm"]},
        {"do": {"patrol": "loop"}},
    ])])
    rows = BS.ladder_model(raw, "a")
    assert [r["index"] for r in rows] == [1, 2]
    assert rows[0]["conds"] == ["active b", "near b 400"]
    assert rows[0]["verb"] == "swing_at" and "damage 2" in rows[0]["detail"]
    assert rows[0]["decos"] == ["once", "cooldown 40", "raise alarm"]
    assert not rows[0]["unconditional"] and rows[1]["unconditional"]
    assert BS.ladder_model(raw, "nobody") == []


def test_stage_projects_posts_routes_refuges_rings_and_boxes():
    raw = _field([
        _unit("a", [{"when": [{"near": ["b", 500]}], "do": {"chase": "b"}},
                    {"do": {"patrol": "loop"}}]),
        _unit("b", [{"when": [{"hp_le": 1}], "do": {"flee": "a", "to": ["nook"]}},
                    {"do": {"wander": [700, -300], "radius": 150}}]),
    ], scan=[{"name": "s", "units": ["a"], "point": [50, 50], "radius": 200, "count": "c"}])
    m = BS.stage_model(raw)
    assert {p["name"] for p in m["posts"]} == {"a", "b"}
    (route,) = m["routes"]
    assert route["verb"] == "patrol" and route["closed"] and len(route["points"]) == 3
    (ref,) = m["refuges"]
    assert ref["points"] == [(900, 900)]
    assert m["rings"]["a"][0]["radius"] == 500
    assert m["wanders"][0]["r"] == 150 and m["scans"][0]["r"] == 200
    assert m["player"] == (0, 0)
    x0, z0, x1, z1 = m["bounds"]
    assert x0 <= -150 and x1 >= 900 and z0 <= -450 and z1 >= 900


def test_stage_skips_what_it_cannot_resolve():
    raw = _field([_unit("a", [{"do": {"patrol": "ghost_route"}}])])   # unknown marker
    m = BS.stage_model(raw)
    assert m["routes"] == []                       # skipped, not raised -- validate reports it
    assert any("ghost_route" in p for p in BS.validate_problems(raw))


def test_validate_problems_are_the_compilers_own_words():
    raw = _field([_unit("ghost")])                 # not a named [[npc]]
    assert any("not a named [[npc]]" in p for p in BS.validate_problems(raw))
    assert BS.validate_problems({"field": {}}) == []


# --------------------------------------------------------------------------- rung B: edit ops
def test_branch_toml_round_trips_every_shape():
    """The editor shows branch_toml and Apply parses it back -- a lossy round trip would
    corrupt a branch the user merely opened and closed."""
    branches = [
        {"when": [{"hp_le": 0}], "do": {"die": True}},
        {"when": [{"active": "b"}, {"near": ["b", 900]}],
         "do": {"chase": "b", "standoff": 180, "speed": 65}, "once": "cry",
         "raise_flags": ["alarm", "seen"]},
        {"do": {"patrol": "loop", "route": "auto"}},
        {"when": [{"table_eq": ["t", 0, 1]}], "do": {"announce": 'He said "run"'},
         "cooldown": 40},
    ]
    for b in branches:
        parsed, err = BS.parse_branch(BS.branch_toml(b))
        assert err is None and parsed == b, (b, parsed, err)


def test_every_insert_template_is_valid_toml():
    """The When/Do menus insert these snippets -- a template that does not parse teaches a
    syntax error. Membership comes from the compiler's tables (the anti-rot half)."""
    import tomllib
    conds = BS.cond_templates()
    acts = BS.action_templates()
    assert [v for v, _s in conds] == sorted(BT.COND_VERBS)
    assert [v for v, _s in acts] == sorted(BT.ACTION_VERBS)
    for _verb, snippet in conds:
        tomllib.loads(f"when = [{snippet}]")
    for _verb, snippet in acts:
        tomllib.loads(f"do = {snippet}")


def test_parse_branch_speaks_its_refusals():
    assert "not valid TOML" in BS.parse_branch("when = [")[1]
    assert "unknown branch key" in BS.parse_branch('do = { hold = true }\nwhne = []')[1]
    assert "needs `do" in BS.parse_branch('when = [{ hp_le = 0 }]')[1]
    assert "LIST of condition rows" in BS.parse_branch('when = 3\ndo = { hold = true }')[1]


def test_move_add_delete_duplicate_branch():
    raw = _field([_unit()])                        # 2 branches: die guard + hold fallback
    assert BS.move_branch(raw, "a", 0, +1) == 1    # swap -> the fallback is now first
    br = raw["behavior"]["unit"][0]["branch"]
    assert "when" not in br[0] and br[1]["do"] == {"die": True}
    assert BS.move_branch(raw, "a", 0, -1) == 0    # clamped at the top
    at = BS.add_branch(raw, "a")
    assert at == len(br) - 2                       # just above the fallback
    assert br[at]["when"] == [{"flag": "never"}]   # inert until edited
    ni = BS.duplicate_branch(raw, "a", at)
    assert ni == at + 1 and br[ni] == br[at] and br[ni] is not br[at]
    BS.delete_branch(raw, "a", ni)
    BS.delete_branch(raw, "a", at)
    assert len(br) == 2


def test_add_unit_delete_unit_and_candidates():
    raw = _field([_unit("a")])
    assert BS.npc_candidates(raw) == ["b"]
    BS.add_unit(raw, "b")
    assert BS.npc_candidates(raw) == []
    rows = BS.ladder_model(raw, "b")
    assert rows[-1]["unconditional"]               # the seeded unit is LEGAL out of the box
    assert BS.validate_problems(raw) == []
    BS.delete_unit(raw, "a")
    assert [u["npc"] for u in raw["behavior"]["unit"]] == ["b"]
    BS.delete_unit(raw, "b")
    assert not BS.has_behavior(raw)                # an empty unit list is no behavior at all


def test_check_edit_judges_a_copy_never_the_original():
    raw = _field([_unit("a")])
    bad = {"do": {"patrol": "ghost_route"}}        # an unknown route marker -- validate refuses
    problems = BS.check_edit(raw, "a", 0, bad)
    assert problems and any("ghost_route" in p for p in problems)
    assert raw["behavior"]["unit"][0]["branch"][0]["do"] == {"die": True}   # untouched


def test_pooled_units_read_pooled_on_cast_and_stage():
    raw = _field([{**_unit("a"), "pooled": True, "pool": "p"}],
                 pool=[{"name": "p", "price": 10}])
    cast = BS.cast_model(raw)
    assert cast["units"][0]["pooled"] and cast["pools"][0]["note"] == "10 gil"
    assert BS.stage_model(raw)["posts"][0]["pooled"]


# --------------------------------------------------------------------------- rung C: stage authoring
def _stagey():
    return _field([
        _unit("a", [{"when": [{"near_point": [[50, 60], 300]}], "do": {"chase": "b"}},
                    {"do": {"patrol": "loop"}}]),
        _unit("b", [{"when": [{"hp_le": 1}], "do": {"flee": "a", "to": ["nook", [5, 6]]}},
                    {"do": {"wander": [700, -300], "radius": 150}}]),
    ], scan=[{"name": "s", "units": ["a"], "point": [50, 50], "radius": 200, "count": "c"}],
       counters=["c"])


def test_stage_handles_cover_every_writable_point():
    hs = {h["id"]: h for h in BS.stage_handles(_stagey())}
    assert hs[("pos", "a")]["kind"] == "post"
    assert ("player",) in hs
    assert hs[("path", "loop", 2)]["list_id"] == ("path", "loop", 2)
    # a NAME refuge moves the NAMED owner; its list slot rides along for the point ops
    assert hs[("pos", "nook")]["kind"] == "refuge"
    assert hs[("pos", "nook")]["list_id"] == ("route_pt", 1, 0, "to", 0)
    assert ("route_pt", 1, 0, "to", 1) in hs       # the literal refuge point owns itself
    assert ("wander", 1, 1) in hs
    assert ("near_point", 0, 0, 0) in hs
    assert ("scan_pt", 0) in hs


def test_apply_move_writes_every_kind_as_ints():
    raw = _stagey()
    assert BS.apply_move(raw, ("pos", "a"), 111.6, -22.4) == "move a"
    assert raw["npc"][0]["pos"] == [112, -22]
    BS.apply_move(raw, ("player",), 9.5, 8.5)
    assert raw["player"]["spawn"] == [10, 8]       # ints, trailing components preserved
    BS.apply_move(raw, ("path", "loop", 1), 150, 10)
    assert raw["marker"][0]["path"][1] == [150, 10]
    BS.apply_move(raw, ("route_pt", 1, 0, "to", 1), 44, 55)
    assert raw["behavior"]["unit"][1]["branch"][0]["do"]["to"][1] == [44, 55]
    BS.apply_move(raw, ("wander", 1, 1), 650, -250)
    assert raw["behavior"]["unit"][1]["branch"][1]["do"]["wander"] == [650, -250]
    BS.apply_move(raw, ("near_point", 0, 0, 0), 70, 80)
    assert raw["behavior"]["unit"][0]["branch"][0]["when"][0]["near_point"][0] == [70, 80]
    BS.apply_move(raw, ("scan_pt", 0), 60, 61)
    assert raw["behavior"]["scan"][0]["point"] == [60, 61]


def test_apply_move_matches_the_resolvers_marker_over_npc_precedence():
    """_npc_marker_positions lets a [[marker]] OVERWRITE an [[npc]] of the same name --
    the write must land where the resolver reads or a drag silently forks the truth."""
    raw = _stagey()
    raw["marker"].append({"name": "a", "pos": [1, 2]})
    BS.apply_move(raw, ("pos", "a"), 500, 600)
    assert raw["marker"][-1]["pos"] == [500, 600]
    assert raw["npc"][0]["pos"] == [100, 200]      # the npc row untouched


def test_apply_radius_floors_and_names_its_cond():
    raw = _stagey()
    rid = ("radius", 0, 0, 0, "near_point")
    label = BS.apply_radius(raw, rid, 449.7)
    assert raw["behavior"]["unit"][0]["branch"][0]["when"][0]["near_point"][1] == 450
    assert "450" in label
    BS.apply_radius(raw, rid, 3)                   # a 3u gate is a typo, not a ring
    assert raw["behavior"]["unit"][0]["branch"][0]["when"][0]["near_point"][1] == BS.RADIUS_FLOOR


def test_insert_route_point_defaults_to_the_leg_midpoint():
    raw = _stagey()
    BS.insert_route_point(raw, ("path", "loop", 0))
    assert raw["marker"][0]["path"][1] == [50, 0]  # ON the leg, ready to drag
    BS.insert_route_point(raw, ("path", "loop", 3))    # after the tail -> a small offset
    assert raw["marker"][0]["path"][4] == [180, 180]
    BS.insert_route_point(raw, ("route_pt", 1, 0, "to", 0), 7, 8)   # explicit coords
    assert raw["behavior"]["unit"][1]["branch"][0]["do"]["to"][1] == [7, 8]


def test_delete_route_point_refuses_below_two():
    import pytest
    raw = _stagey()
    BS.delete_route_point(raw, ("path", "loop", 2))
    assert len(raw["marker"][0]["path"]) == 2
    with pytest.raises(ValueError, match="at least 2 points"):
        BS.delete_route_point(raw, ("path", "loop", 0))
    assert len(raw["marker"][0]["path"]) == 2      # the refusal wrote nothing


def test_ring_rids_point_back_at_their_own_cond():
    raw = _stagey()
    ring = BS.stage_model(raw)["rings"]["a"][0]
    assert ring["rid"] == ("radius", 0, 0, 0, "near_point")
    BS.apply_radius(raw, ring["rid"], 512)
    assert BS.stage_model(raw)["rings"]["a"][0]["radius"] == 512


# --------------------------------------------------------------------------- rung D: archetype stamps
def test_every_archetype_stamps_a_legal_unit():
    for a in BS.BEHAVIOR_ARCHETYPES:
        raw = _field([_unit("b")] if a.get("needs_target") else [])
        second = "b" if (a.get("needs_target") or a.get("needs_partner")) else None
        label = BS.stamp_archetype(raw, a["key"], "a", second)
        assert "a" in label
        assert "a" in [u["npc"] for u in raw["behavior"]["unit"]]
        assert BS.validate_problems(raw) == [], (a["key"], BS.validate_problems(raw))
        rows = BS.ladder_model(raw, "a")
        assert rows[0]["verb"] == "die" and rows[-1]["unconditional"]


def test_beat_markers_mint_around_the_post_and_dedupe():
    raw = _field([])
    BS.stamp_archetype(raw, "patroller", "a")
    beat = next(m for m in raw["marker"] if m["name"] == "a_beat")
    assert beat["closed"] and len(beat["path"]) == 4
    assert beat["path"][0] == [320, 200]           # a's post (100,200) + the 220u leg
    BS.delete_unit(raw, "a")
    BS.stamp_archetype(raw, "patroller", "a")      # re-stamp: the old marker name is taken
    assert any(m["name"] == "a_beat_2" for m in raw["marker"])


def test_unknown_archetype_is_a_caller_bug():
    import pytest
    with pytest.raises(KeyError, match="unknown behavior archetype"):
        BS.stamp_archetype(_field([]), "warlord", "a")


def test_guard_binds_its_target_and_refuses_without_one():
    import pytest
    raw = _field([_unit("b")])                     # the enemy is an existing unit
    with pytest.raises(KeyError, match="needs a target"):
        BS.stamp_archetype(raw, "guard", "a")
    BS.stamp_archetype(raw, "guard", "a", "b")
    assert BS.validate_problems(raw) == []
    rows = BS.ladder_model(raw, "a")
    assert rows[2]["verb"] == "swing_at" and "active b" in rows[2]["conds"]
    assert rows[3]["verb"] == "chase" and rows[-1]["verb"] == "hold_post"


def test_shift_pair_seats_two_units_one_alternator_one_beat():
    import pytest
    raw = _field([])
    with pytest.raises(KeyError, match="needs a partner"):
        BS.stamp_archetype(raw, "shift_pair", "a")
    BS.stamp_archetype(raw, "shift_pair", "a", "b")
    b = raw["behavior"]
    assert [u["npc"] for u in b["unit"]] == ["a", "b"]
    assert b["alternators"] == [{"name": "shift", "frames": 400}]
    assert BS.validate_problems(raw) == []
    ra, rb = BS.ladder_model(raw, "a"), BS.ladder_model(raw, "b")
    assert ra[1]["conds"] == ["flag shift"] and rb[1]["conds"] == ["not_flag shift"]
    assert ra[1]["verb"] == rb[1]["verb"] == "patrol"   # the SAME minted beat, traded
    # a second pair on the same field dedupes its alternator flag
    raw["npc"] += [{"name": "c", "pos": [1, 2]}, {"name": "d", "pos": [3, 4]}]
    BS.stamp_archetype(raw, "shift_pair", "c", "d")
    assert [x["name"] for x in b["alternators"]] == ["shift", "shift_2"]


def test_stamp_siege_writes_the_skeleton_and_refuses_the_clashes():
    import pytest
    raw = {"field": {"name": "BARE"}, "player": {"spawn": [100, -200]}}
    assert BS.stamp_siege(raw) == "stamp [siege] skeleton"
    assert raw["siege"]["base"]["pos"] == [100, 200]   # sized around the spawn
    assert BS.siege_view(raw) is not None              # the view renders it the same tick
    with pytest.raises(ValueError, match="already has a \\[siege\\]"):
        BS.stamp_siege(raw)
    with pytest.raises(ValueError, match="OWNS the behavior table"):
        BS.stamp_siege(_field([_unit()]))
    with pytest.raises(ValueError, match="VERBATIM"):
        BS.stamp_siege({"field": {}, "verbatim_eb": "x.eb"})


def test_the_siege_skeleton_survives_a_real_dry_compile(tmp_path):
    import importlib.util
    from pathlib import Path
    from ff9mapkit.editor import model as _model
    spec = importlib.util.spec_from_file_location(
        "_bdoc_fixture2", Path(__file__).with_name("test_behaviordoc.py"))
    fx = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fx)
    p = fx.make_behavior_field(tmp_path)               # the walkmesh sidecar matters:
    raw = {"field": {"name": "BARE", "id": 30991},     # the skeleton's raiders autoroute,
           "player": {"spawn": [500, 100]},            # and its points must LAND on this
           "walkmesh": {"bgi": "walkmesh.bgi"}}        # floor (x -300..1000, z -300..600)
    BS.stamp_siege(raw)
    p.write_text(_model.dumps(raw), encoding="utf-8")
    res = BS.dry_compile(p)
    assert res.ok, res.problems


def _siege_field():
    import copy
    import importlib.util
    from pathlib import Path
    p = (Path(__file__).resolve().parents[1] / "ff9mapkit" / "tests" / "test_siege.py")
    spec = importlib.util.spec_from_file_location("_siege_fixture", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {"field": {"name": "REDOUBT", "id": 30991}, "player": {"spawn": [0, -600]},
            "siege": copy.deepcopy(mod.RAW)}


def test_siege_view_renders_the_generated_behavior_without_touching_the_doc():
    raw = _siege_field()
    view = BS.siege_view(raw)
    assert view is not None and BS.has_behavior(view)
    assert not BS.has_behavior(raw) and "siege" in raw        # the open doc is untouched
    assert BS.stage_model(view)["posts"]                      # the projections have geometry
    assert BS.siege_view({"field": {}}) is None               # no [siege] -> no view
    both = _siege_field()
    both["behavior"] = {"unit": [{"npc": "x", "branch": [{"do": {"hold_post": True}}]}]}
    assert BS.siege_view(both) is None             # [behavior] present: validate owns the clash


def test_every_archetype_survives_a_real_dry_compile(tmp_path):
    """The stamp fence with teeth: stamp onto the demo field's spare npc, serialize with the
    editor's own dumps, and run the REAL dry-compile lane (walkmesh sidecar included, so the
    stamps' route = \"auto\" resolves genuinely). A vocabulary or compiler change that breaks
    a stamped tree must fail HERE, not at a user's build."""
    import importlib.util
    from pathlib import Path
    from ff9mapkit.editor import model as _model
    spec = importlib.util.spec_from_file_location(
        "_bdoc_fixture", Path(__file__).with_name("test_behaviordoc.py"))
    fx = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fx)
    for a in BS.BEHAVIOR_ARCHETYPES:
        root = tmp_path / a["key"]
        p = fx.make_behavior_field(root)
        raw = fx.demo_raw()
        raw["npc"].append({"name": "lamplighter", "pos": [260, 60]})
        raw["npc"].append({"name": "torchboy", "pos": [420, 60]})
        second = "raider" if a.get("needs_target") else \
            ("torchboy" if a.get("needs_partner") else None)
        BS.stamp_archetype(raw, a["key"], "lamplighter", second)
        p.write_text(_model.dumps(raw), encoding="utf-8")
        res = BS.dry_compile(p)
        assert res.ok, (a["key"], res.problems)


# --------------------------------------------------------------------------- rung C: the sweep lane
def _u_mesh(notch_z=-400):
    """The pursuit suite's WELDED U floor: outer x[-800,800] z[-800,200] minus the notch
    x(-400,400) z(notch_z, 200] -- a leg crossing the notch mouth jams."""
    from ff9mapkit.scene import bgi
    xs = (-800, -400, 400, 800)
    verts = [(x, 0, z) for z in (200, notch_z, -800) for x in xs]
    tris = [(0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6),
            (4, 5, 9), (4, 9, 8), (5, 6, 10), (5, 10, 9), (6, 7, 11), (6, 11, 10)]
    return bgi.BgiWalkmesh.from_bytes(bgi.build(verts, tris).to_bytes())


def _sweep_field(**patrol_extra):
    return {
        "player": {"spawn": [0, -600]},
        "npc": [{"name": "w", "pos": [-600, -600]}],
        "marker": [{"name": "line", "path": [[-600, -100], [600, -100]]}],
        "behavior": {"unit": [{"npc": "w", "hp": 1, "branch": [
            {"when": [{"hp_le": 0}], "do": {"die": True}},
            {"do": {"patrol": "line", **patrol_extra}}]}]},
    }


def test_sweep_geometry_names_the_jam_where_the_cli_would():
    res = BS.sweep_geometry(_sweep_field(), _u_mesh(), pursuit=False)
    assert res.ok
    (jam, *_rest) = res.jams                       # the z=-100 line crosses the notch mouth
    assert -400 < jam["mid"][0] < 400 and jam["name"] == "line"
    assert any(k == "error" and "OFF-MESH" in t for k, t in res.lines)
    assert any("route = \"auto\"" in t for _k, t in res.lines)   # the CLI's own hint


def test_sweep_geometry_judges_the_routed_line_for_autoroute():
    """route = "auto" compiles the PATHFOUND line, so lint (and the stage) judge THAT --
    the authored jam heals and the sweep reports clean."""
    res = BS.sweep_geometry(_sweep_field(route="auto"), _u_mesh(), pursuit=False)
    assert res.ok and res.jams == []
    assert not any(k == "error" for k, _t in res.lines)
    # the detour legally HUGS the notch corner -- a warn, not a jam; clean is not promised


def test_sweep_geometry_flags_the_pursuit_family():
    raw = _sweep_field()
    raw["npc"].append({"name": "q", "pos": [600, -600]})
    raw["behavior"]["unit"][0]["branch"].insert(
        1, {"when": [{"near": ["q", 900]}], "do": {"chase": "q"}})
    res = BS.sweep_geometry(raw, _u_mesh())
    assert res.ok and res.pursuits
    p = res.pursuits[0]
    assert p["blocked"] > 0 and p["worst"] and p["unit"] == "w"
    assert any("pursuit" in t for k, t in res.lines if k == "warn")


def test_sweep_geometry_without_a_mesh_is_an_error_not_a_crash():
    res = BS.sweep_geometry(_sweep_field(), None)
    assert not res.ok and "walkmesh" in res.error


def test_load_walkmesh_reports_the_reason(tmp_path):
    wm, err = BS.load_walkmesh(tmp_path / "nope" / "field.toml")
    assert wm is None and err
