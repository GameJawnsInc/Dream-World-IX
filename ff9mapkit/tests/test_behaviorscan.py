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
