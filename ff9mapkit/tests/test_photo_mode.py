"""``[photo]`` -- photo mode, rung 1 (studies/photo-mode/PLAN.md). PURE: never skips.

  * THE ONE REFUSAL TEXT -- every rule of the table, the buttons, the hide targets, the scope and the pan boxes, as
    ``(id, raw, fragment)`` rows, plus the boundaries it must ACCEPT.
  * THE PROVEN BYTES -- the hide/show function, the camera ops, the release table and the grade are byte-identical to
    rung 0's in-game-proven builder (studies/photo-mode/photo0_bench.py, imported, never copied).
  * THE DAEMON, RUN -- the emitted body in ``_ebengine.FieldTickEngine`` against the rung-0-calibrated
    ``CameraModel``, tick by tick: the gate, the latch, the take, the pan and its clamp, the hide cycle and its exact
    restore, the grade, the tracking release, the yields.
  * THE SELF-AUDIT BITES -- each law of ``audit_body`` refuses a mutant daemon built by swapping one emitter.

Each test that guards a named mutant names it in [brackets]; each was run against that mutant and failed.
"""
from __future__ import annotations

import importlib.util
import random
import sys
from pathlib import Path

import pytest

from ff9mapkit.content import photo as P
from ff9mapkit.eb import opcodes

from ._ebengine import CameraModel, FieldTickEngine

_STUDY = Path(__file__).resolve().parents[2] / "studies" / "photo-mode"
_WIDE = {"pitch": 40, "range": [768, 448], "window_width": 384, "scroll": {"enabled": True}}
_BOX = (160, 608, 112, 336)


def _bench():
    """Rung 0's builder -- the daemon proven in-game (154/154), imported so the comparison can never drift."""
    sys.path.insert(0, str(_STUDY))
    spec = importlib.util.spec_from_file_location("photo0_bench_for_tests", _STUDY / "photo0_bench.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _raw(photo=None, **extra) -> dict:
    return {"photo": {} if photo is None else photo, "camera": dict(_WIDE), **extra}


# ============================================================== the one refusal text
_NPC = {"name": "guard", "model": 5, "pos": [0, -800]}
_PROPC = {"prop": "balloon", "name": "b", "pos": [0, -500]}

REFUSED = [
    ("not-a-table", {"photo": 1, "camera": _WIDE}, "[photo]: must be a table"),
    ("unknown-key", _raw({"hide_buton": "r1"}), "unknown key(s) ['hide_buton']"),
    ("not-a-button", _raw({"open_button": "x"}), "not a button name"),
    ("start", _raw({"open_button": "start"}), "Start pauses"),
    ("menu", _raw({"close_button": "menu"}), "main menu"),
    ("d-pad", _raw({"hide_button": "up"}), "the d-pad pans"),
    ("confirm", _raw({"close_button": "confirm"}), "talk check"),
    ("special", _raw({"grade_button": "special"}), "talk check"),
    ("cancel-opens", _raw({"open_button": "cancel", "close_button": "select"}), "walk modifier"),
    ("same-button", _raw({"hide_button": "l1"}), "hide_button and grade_button are both 'l1'"),
    ("open-is-hide", _raw({"open_button": "r1"}), "open_button and hide_button are both 'r1'"),
    ("all-not-last", _raw({"hide": ["all", "player"]}), "\"all\" must be the last step"),
    ("step-twice", _raw({"hide": ["player", "player"]}), "listed twice"),
    ("too-many-steps", _raw({"hide": [f"p{i}" for i in range(9)]}), "at most 8 steps"),
    ("hide-not-list", _raw({"hide": "player"}), "must be a list of names"),
    ("grade-int", _raw({"grade": 1}), "must be true or false"),
    ("hide-button-unused", _raw({"hide_button": "r2", "hide": []}), "hide_button is set but hide = []"),
    ("grade-button-unused", _raw({"grade_button": "r2", "grade": False}), "grade_button is set but grade = false"),
    ("no-such-target", _raw({"hide": ["nobody"]}), "no [[npc]] or [[prop]] is named 'nobody'"),
    ("gated-npc", _raw({"hide": ["guard"]}, npc=[dict(_NPC, requires_flag=8712)]), "requires_flag"),
    ("gated-clear", _raw({"hide": ["guard"]}, npc=[dict(_NPC, requires_flag_clear=8712)]), "requires_flag_clear"),
    ("scenario-npc", _raw({"hide": ["guard"]}, npc=[dict(_NPC, scenario_min=1000)]), "scenario_min"),
    ("pooled-unit", _raw({"hide": ["guard"]}, npc=[_NPC],
                         behavior={"unit": [{"npc": "guard", "pooled": True}]}), "a pooled behavior unit"),
    ("behavior-unit", _raw({"hide": ["guard"]}, npc=[_NPC], behavior={"unit": [{"npc": "guard"}]}),
     "a [behavior] unit"),
    ("holds", _raw({"hide": ["guard"]}, npc=[dict(_NPC, holds="cup")]), "holds"),
    ("carrier", _raw({"hide": ["guard"]}, npc=[_NPC], prop=[{"prop": "cup", "pos": [0, -800], "attach_to": "guard"}]),
     "carries a [[prop]]"),
    ("attached-prop", _raw({"hide": ["b"]}, npc=[_NPC], prop=[dict(_PROPC, attach_to="guard")]), "attach_to"),
    ("gated-prop", _raw({"hide": ["b"]}, prop=[dict(_PROPC, requires_flag=8712)]), "requires_flag"),
    ("ambiguous", _raw({"hide": ["b"]}, npc=[dict(_NPC, name="b")], prop=[_PROPC]), "share that name"),
    ("verbatim", _raw(verbatim_eb={"donor": 1207}), "novel fields only"),
    ("borrowed-camera", {"photo": {}, "camera": {"borrow": "x.bgx"}}, "[camera] borrow"),
    ("bgs", _raw(field={"bgs": "x.bgs"}), "[field] bgs"),
    ("ate-select", _raw(ate={"title": 1}), "[ate]'s menu button"),
    ("pool-select", _raw(behavior={"unit": [{"npc": "g"}], "pool": [{"name": "p", "button": True}]}),
     "hire button"),
    ("siege-select", _raw(siege={"x": 1}, behavior={"unit": [{"npc": "g"}], "pool": [{"name": "p", "button": True}]}),
     "[siege]'s council button"),
    ("viewport-past-art", {"photo": {}, "camera": {"pitch": 40, "range": [320, 224]}}, "reaches past the painting"),
    ("nothing-pans", {"photo": {}, "camera": {"pitch": 40, "range": [398, 224], "viewport": [160, 238, 112, 112]}},
     "no camera can pan either axis"),
]


@pytest.mark.parametrize("raw, frag", [(r, f) for _i, r, f in REFUSED], ids=[i for i, _r, _f in REFUSED])
def test_every_rule_is_refused_with_its_own_text(raw, frag):
    """[collision check removed] [gated target accepted] [holds carrier accepted] [confirm allowed on close]
    Every refusal starts with the table's label and names its rule."""
    probs = P.problems(raw, donor=None)
    assert probs and any(frag in p for p in probs), probs
    assert all(p.startswith("[photo]") for p in probs), probs


def test_a_donor_is_refused():
    probs = P.problems(_raw(), donor=1207)
    assert any("a donor (field 1207)" in p and "novel fields only" in p for p in probs), probs


ACCEPTED = [
    ("bare", _raw()),
    ("toggle", _raw({"open_button": "select", "close_button": "select"})),
    ("no-hide", _raw({"hide": []})),
    ("no-grade", _raw({"grade": False})),
    ("ate-rebound", _raw({"open_button": "l2"}, ate={"title": 1})),
    ("pool-without-button", _raw(behavior={"unit": [{"npc": "g"}], "pool": [{"name": "p", "button": False}]})),
    ("npc-target", _raw({"hide": ["guard", "player", "all"]}, npc=[_NPC])),
    ("prop-target", _raw({"hide": ["b"]}, prop=[_PROPC])),
    ("default-room-y-only", {"photo": {}, "camera": {"pitch": 40}}),
]


@pytest.mark.parametrize("raw", [r for _i, r in ACCEPTED], ids=[i for i, _r in ACCEPTED])
def test_the_boundaries_are_accepted(raw):
    assert P.problems(raw) == []


def test_a_field_without_photo_has_no_problems_and_no_lint():
    raw = {"camera": _WIDE}
    assert P.problems(raw) == [] and P.lint_notes(raw) == [] and P.box_lines(raw) == [] and not P.any_photo(raw)


def test_too_many_parts_counts_every_composite_part():
    from ff9mapkit import prop_archetypes as pa
    comp = max(pa.PROP_COMPOSITES, key=lambda n: len(pa.resolve_composite(n)))
    k = len(pa.resolve_composite(comp))
    assert k >= 2
    props = [{"prop": comp, "name": f"c{i}", "pos": [0, -500]} for i in range(8)]
    raw = _raw({"hide": [f"c{i}" for i in range(8)]}, prop=props)
    over = 8 * k > P.MAX_PARTS
    assert any("at most 15 parts" in p for p in P.problems(raw)) == over


# ============================================================== pan boxes
def test_the_pan_boxes_follow_the_builds_viewport_choice():
    wide = P.pan_boxes(_raw())[0]
    assert wide.viewport == (160, 608, 112, 336) and wide.x169 == (199, 569) and wide.ok
    narrow = P.pan_boxes({"photo": {}, "camera": {"pitch": 40}})[0]
    assert narrow.viewport == (160, 224, 112, 336) and narrow.x169 is None and narrow.pans_x_43 and narrow.pans_y
    explicit = P.pan_boxes({"photo": {}, "camera": dict(_WIDE, viewport=[200, 500, 150, 300])})[0]
    assert explicit.viewport == (200, 500, 150, 300) and explicit.x169 == (239, 461)
    multi = P.pan_boxes({"photo": {}, "camera": [dict(_WIDE), {"pitch": 40, "range": [768, 600]}]})
    assert [b.viewport for b in multi] == [(160, 608, 112, 336), (160, 608, 112, 488)]


def test_the_pan_box_drift_test_against_the_build(tmp_path):
    """The box photo.py computes is the viewport the build bakes into the camera (build._resolve_one_camera)."""
    from ff9mapkit import build
    for cfg, scrolling in ((_WIDE, True), ({"pitch": 40}, False), (dict(_WIDE, viewport=[200, 500, 150, 300]), True)):
        proj = build.FieldProject.__new__(build.FieldProject)
        proj.root = tmp_path
        c = build._resolve_one_camera(proj, dict(cfg), scrolling)
        mine = P.pan_boxes({"photo": {}, "camera": dict(cfg)})[0].viewport
        assert tuple(int(v) for v in c.viewport) == mine, (cfg, c.viewport, mine)


def test_the_lint_reports_both_boxes_and_the_widescreen_pin():
    assert P.box_lines(_raw()) == ["[photo] camera 0 768x448: 4:3 X 160..608 (448 px), Y 112..336 (224 px) | "
                                   "16:9 X 199..569 (370 px), Y 112..336 (224 px)"]
    notes = P.lint_notes({"photo": {}, "camera": {"pitch": 40}})
    assert any("pinned under widescreen" in n for n in notes), notes


# ============================================================== the proven bytes
def test_the_proven_bytes_are_rung_zeros():
    """[a re-typed emitter] The hide/show function, both camera ops, the release table and the grade are the bytes
    rung 0 ran in-game."""
    B = _bench()
    for uid in (3, 250):
        for show in (False, True):
            assert P.flag_function(uid, show) == B.flag_function(uid, show)
    assert P.RELEASE_TABLE == B.RELEASE_TABLE and P.GRADE == B.GRADE and P.GRADE_CLEAR == B.GRADE_CLEAR
    assert opcodes.move_camera(P._x("Global.Int16[1510]"), P._x("Global.Int16[1512]"), 1, 0) == \
        B.move_camera(B.g("tx"), B.g("ty"))
    for n in P.RELEASE_TABLE:
        assert opcodes.release_camera(n, 0) == opcodes.encode(0x70, n, 0)
    assert opcodes.release_camera(16, 8) == opcodes.encode(0x70, *B.RELEASE)
    assert P.STEP == B.STEP


def test_the_release_table_is_the_ease_it_claims():
    import math
    assert P.release_table() == P.RELEASE_TABLE and P.RELEASE_TABLE[-1] == 1
    v, target = 1.0, 0.0
    for k, n in enumerate(P.RELEASE_TABLE, 1):
        v = v + (target - v) / n
        ease = 1 - (1 - math.cos(math.pi * k / 16)) / 2
        assert abs(v - ease) < 0.02, (k, v, ease)
    assert v == 0.0


@pytest.mark.parametrize("dur", [0, 256])
def test_a_zero_or_oversized_camera_duration_is_refused(dur):
    with pytest.raises(ValueError):
        opcodes.move_camera(1, 2, dur, 0)
    with pytest.raises(ValueError):
        opcodes.release_camera(dur if dur else 0, 0)


# ============================================================== the daemon, run
_UIDS = {"player": [250], "g": [5], "c": [6, 7]}        # "c" = a two-part composite


class Rig:
    def __init__(self, steps=("player", "all"), *, boxes=(_BOX,), widescreen=True, objects=None, photo=None,
                 body=None):
        raw = {"photo": dict(photo or {}, hide=list(steps))}
        self.spec = P.parse(raw)
        self.parts, fns = [], {}
        for t, step in enumerate(steps):
            for uid in _UIDS.get(step, []):
                self.parts.append(P.Part(step=t, uid=uid, entry=uid if uid != 250 else 1, hide_tag=96, show_tag=97))
                fns[(uid, 96)] = P.flag_function(uid, False)
                fns[(uid, 97)] = P.flag_function(uid, True)
        self.follow = (384, 286)
        self.cam = CameraModel(boxes[0], lambda: self.follow, widescreen=widescreen)
        self.boxes = list(boxes)
        self.body = body or P.daemon_body(self.spec, self.parts, self.boxes)
        self.e = FieldTickEngine(P.LOC, self.cam, objects=dict(objects or {250: 15, 5: 7, 6: 7, 7: 7, 9: 7}),
                                 functions=fns)

    def run(self, n: int):
        self.e.run(self.body, n)
        return self

    def press(self, name: str, n: int = 2):
        self.e.keys = P.BUTTONS[name]
        self.run(n)
        self.e.keys = 0
        return self.run(2)

    def hold(self, mask: int, n: int):
        self.e.keys = mask
        self.run(n)
        self.e.keys = 0
        return self

    def local(self, name: str) -> int:
        return self.e._read(("inst", "Int16", P.LOCALS[name]))

    def ops(self, op: int) -> list:
        return [x for x in self.e.effects if x[1] == op]

    def settled(self):
        return self.run(P.SETTLE + 2)

    def opened(self):
        return self.settled().press(self.spec.buttons["open_button"])


def test_closed_the_daemon_reads_and_moves_nothing():
    """[0xEA ungated] Closed, it never reads the camera nor moves it, whatever else is pressed."""
    r = Rig().settled()
    for b in ("r1", "l1", "cancel", "r2"):
        r.press(b)
    r.run(100)
    assert not r.ops(0xEA) and not r.ops(0x6F) and not r.ops(0x70) and not r.ops(0x2D) and not r.ops(0xEC)
    assert r.e.objects[250] == 15 and r.local("ST") == 0


@pytest.mark.parametrize("why", ["settle", "usercontrol", "scene", "stay-locked"])
def test_the_open_gate(why):
    """[a gate removed] Open needs 30 ticks of player control, usercontrol on, no conductor scene (MAP 110) and no
    stay-locked latch (MAP 156)."""
    r = Rig()
    if why == "settle":
        r.run(P.SETTLE - 3)
    else:
        r.settled()
        if why == "usercontrol":
            r.e.usercontrol = 0
        else:
            r.e.map_bits[P.SCENE_BIT if why == "scene" else P.STAY_LOCKED_BIT] = 1
    r.press("select")
    assert not r.ops(0x2D) and r.local("ST") == 0
    r.e.usercontrol, r.e.map_bits = 1, {}
    r.settled().press("select")
    assert len(r.ops(0x2D)) == 1 and r.local("ST") == 1


def test_a_held_open_button_opens_once():
    """[PREV update removed] The latch turns a held button into ONE edge."""
    r = Rig().settled().hold(P.BUTTONS["select"], 40).run(5)
    assert len(r.ops(0x2D)) == 1 and r.local("ST") == 1


def test_open_locks_then_takes_the_camera_where_it_is():
    """[lock after take] DisableMove, then MoveCamera(view, 1, 0) in the same tick -- no jump."""
    r = Rig()
    r.follow = (300, 250)
    r.opened()
    (t_lock, _o, _a), = r.ops(0x2D)
    (t_take, _o2, take), = r.ops(0x6F)
    lock_i = r.e.effects.index(r.ops(0x2D)[0])
    take_i = r.e.effects.index(r.ops(0x6F)[0])
    assert t_lock == t_take and lock_i < take_i and take == (300, 250, 1, 0)
    assert r.cam.readback() == (300, 250) and r.e.usercontrol == 0


def test_the_pan_moves_four_px_a_tick_and_idles_quietly():
    r = Rig().opened()
    n = len(r.ops(0x6F))
    r.run(20)
    assert len(r.ops(0x6F)) == n, "an idle open tick issues nothing"
    r.hold(P.PAD["right"], 11).run(3)
    assert r.cam.readback() == (384 + 44, 286)
    r.hold(P.PAD["right"] | P.PAD["up"], 5).run(3)
    assert r.cam.readback() == (428 + 20, 286 - 20)


def test_the_script_clamps_both_axes_to_the_cameras_box():
    """[X clamp removed] [Y clamp removed] With widescreen off the engine clamps NOTHING, so the script's clamp alone
    keeps the view on the painting; Y is never engine-clamped at all."""
    r = Rig(widescreen=False).opened()
    r.hold(P.PAD["right"], 200).run(3)
    assert r.cam.readback()[0] == _BOX[1]
    r.hold(P.PAD["left"], 300).run(3)
    assert r.cam.readback()[0] == _BOX[0]
    r.hold(P.PAD["down"], 200).run(3)
    assert r.cam.readback()[1] == _BOX[3]
    r.hold(P.PAD["up"], 200).run(3)
    assert r.cam.readback()[1] == _BOX[2]


def test_the_box_is_the_open_cameras_and_an_unknown_camera_fails_closed():
    """[fail-open] The box is picked by B_SYSVAR[1] at open; a camera index with no box pans nowhere."""
    boxes = [_BOX, (200, 300, 150, 250)]
    r = Rig(boxes=boxes, widescreen=False)
    r.e.camidx = 1
    r.opened().hold(P.PAD["right"] | P.PAD["down"], 200).run(3)
    assert r.cam.readback() == (300, 250)
    r2 = Rig(boxes=boxes, widescreen=False)
    r2.e.camidx = 5
    r2.opened().hold(P.PAD["right"], 50).run(3)
    assert r2.cam.readback() == (384, 286)


def test_the_hide_cycle_and_its_exact_restore():
    """[forward show order] [PRIOR ignored] Each press hides the next step; a pre-hidden target stays hidden after
    the close; "all" is undone FIRST so the player it snapshotted hidden comes back."""
    r = Rig(steps=("g", "c", "player", "all"), objects={250: 15, 5: 6, 6: 7, 7: 7, 9: 7})   # g starts hidden
    r.opened()
    r.press("r1")
    assert r.e.objects[5] & 1 == 0
    r.press("r1")
    assert r.e.objects[6] & 1 == 0 and r.e.objects[7] & 1 == 0
    r.press("r1")
    assert r.e.objects[250] & 1 == 0
    r.press("r1")
    assert r.e.objects[9] & 1 == 0, "all hides the rest"
    before = dict(r.e.objects)
    r.press("r1")
    assert r.e.objects == before and r.local("HX") == 4, "a press past the last step does nothing"
    r.press("cancel").run(10)
    assert r.e.objects == {250: 15, 5: 6, 6: 7, 7: 7, 9: 7}


def test_the_grade_toggles_and_the_close_clears_it_only_when_on():
    r = Rig().opened()
    r.press("l1")
    assert r.e.grade == (0, 64, 128)
    r.press("l1")
    assert r.e.grade == (0, 0, 0)
    n = len(r.ops(0xEC))
    r.press("cancel").run(5)
    assert len(r.ops(0xEC)) == n, "a close with the grade off issues no clear"
    r2 = Rig().opened().press("l1").press("cancel").run(5)
    assert r2.e.grade == (0, 0, 0)


def test_the_close_issues_the_release_table_once_a_tick_then_nothing():
    """[final 1 dropped] [RT < 15] The tracking release: one step per tick, exactly RELEASE_TABLE, then silence."""
    r = Rig(steps=()).opened().hold(P.PAD["right"], 11)
    r.press("cancel").run(40)
    rel = r.ops(0x70)
    assert [a[0] for _t, _o, a in rel] == list(P.RELEASE_TABLE) and all(a[1] == 0 for _t, _o, a in rel)
    ticks = [t for t, _o, _a in rel]
    assert ticks == list(range(ticks[0], ticks[0] + len(P.RELEASE_TABLE)))
    assert r.e.usercontrol == 1 and r.local("ST") == 0 and r.cam.state == "follow"


def _walking_exit(body=None) -> tuple:
    r = Rig(steps=(), body=body).opened()
    r.hold(P.PAD["right"], 11).run(3)
    r.e.keys = P.BUTTONS["cancel"]
    r.run(1)
    r.e.keys = 0
    trace = [r.cam.readback()[0]]
    for _ in range(30):
        r.follow = (r.follow[0] - 10, r.follow[1])      # the player walks left through the glide
        r.run(1)
        trace.append(r.cam.readback()[0])
    steps = [abs(b - a) for a, b in zip(trace, trace[1:])]
    return r, max(steps), trace


def test_the_walking_exit_lands_on_the_player():
    """[single (16,8) exit] The owner's playtest: walking through the exit glide must not snap. The tracking release
    lands on the moving follow point; the single release it replaced jumps (the in-game 113 px, here >= 100)."""
    r, worst, trace = _walking_exit()
    assert trace[-1] == r.cam._follow_point()[0] and worst <= 40, (worst, trace)
    spec = P.parse({"photo": {"hide": []}})
    orig = P.RELEASE_TABLE
    try:
        P.RELEASE_TABLE = (16,)
        single = P.daemon_body(spec, [], [_BOX])
    finally:
        P.RELEASE_TABLE = orig
    _r2, worst2, _t2 = _walking_exit(single)
    assert worst2 >= 100, worst2


def test_reopening_mid_glide_stops_the_tracking():
    """[RT not zeroed on open]"""
    r = Rig(steps=()).opened().hold(P.PAD["right"], 11).run(3)
    r.press("cancel", n=1)
    r.run(1)
    r.press("select", n=1)
    n = len(r.ops(0x70))
    r.run(30)
    assert len(r.ops(0x70)) == n and r.local("ST") == 1 and r.cam.state == "hold"


@pytest.mark.parametrize("how", ["foreign-enablemove", "camera-switch", "scene"])
def test_photo_mode_yields_with_a_full_restore(how):
    """[yield removed] Anything else taking over closes photo mode exactly as Cancel would."""
    r = Rig(steps=("g", "player")).opened().press("r1").press("r1").press("l1")
    assert r.e.objects[5] & 1 == 0 and r.e.objects[250] & 1 == 0
    if how == "foreign-enablemove":
        r.e.usercontrol = 1
    elif how == "camera-switch":
        r.e.camidx = 1
    else:
        r.e.map_bits[P.SCENE_BIT] = 1
    r.run(8)
    assert r.local("ST") == 0 and r.e.objects[5] & 1 and r.e.objects[250] & 1 and r.e.grade == (0, 0, 0)
    assert r.ops(0x70)


def test_the_tracking_continues_under_a_lock_and_stops_on_a_camera_change():
    """[CAM0 not refreshed]"""
    r = Rig(steps=()).opened().hold(P.PAD["right"], 11).run(3)
    r.press("cancel", n=1)
    r.e.usercontrol = 0                                    # something else locks the player mid-glide
    r.run(20)
    assert [a[0] for _t, _o, a in r.ops(0x70)] == list(P.RELEASE_TABLE)
    r2 = Rig(steps=()).opened().hold(P.PAD["right"], 11).run(3)
    r2.press("cancel", n=1)
    r2.e.camidx = 1
    r2.run(20)
    assert len(r2.ops(0x70)) < len(P.RELEASE_TABLE)


def test_an_absent_target_would_freeze_the_daemon():
    """The TARGET law's reason, demonstrated: RunScriptSync on an object that does not exist stalls for ever."""
    r = Rig(steps=("g",), objects={250: 15}).opened()
    with pytest.raises(AssertionError, match="absent uid|does not exist"):   # the PRIOR read throws first
        r.press("r1")


def test_a_random_soak_keeps_the_locals_lawful():
    rng = random.Random(30956)
    r = Rig(steps=("g", "c", "player", "all")).settled()
    masks = list(P.BUTTONS.values())
    for _ in range(1500):
        r.e.keys = rng.choice(masks) if rng.random() < 0.3 else 0
        if rng.random() < 0.01:
            r.e.usercontrol ^= 1
        r.run(1)
    assert r.local("ST") in (0, 1) and 0 <= r.local("HX") <= 4 and 0 <= r.local("RT") <= 16
    lox, hix, loy, hiy = _BOX
    assert lox <= r.cam.readback()[0] <= hix and loy <= r.cam.readback()[1] <= hiy


# ============================================================== the self-audit bites
def _spec():
    return P.parse({"photo": {}})


def _parts():
    return [P.Part(step=0, uid=250, entry=1, hide_tag=96, show_tag=97)]


def test_the_shipped_daemon_passes_its_audit():
    assert P.audit_body(P.daemon_body(_spec(), _parts(), [_BOX]), _spec(), _parts(), [_BOX]) == []
    assert P.entry_bytes(_spec(), _parts(), [_BOX])[:6] == bytes([0, 1, 0, 0, 4, 0])


class _Shim:
    """opcodes with one emitter swapped for its mutant."""

    def __init__(self, **over):
        self.over = over

    def __getattr__(self, name):
        return self.over.get(name, getattr(opcodes, name))


_MUTANTS = [
    ("enable-camera-services-0",
     {"release_camera": lambda n, t=0: opcodes.encode(0x71, 0, 0, 0) if n == 104 else opcodes.release_camera(n, t)},
     "0x71"),
    ("zero-duration-move", {"move_camera": lambda x, y, d=1, t=0: opcodes.encode(0x6F, x, y, 0, 0, arg_flags=3)},
     "exactly two MoveCamera"),
    ("cosine-move", {"move_camera": lambda x, y, d=1, t=0: opcodes.encode(0x6F, x, y, 1, 8, arg_flags=3)},
     "exactly two MoveCamera"),
    ("no-wait", {"wait": lambda n: b""}, "Wait(1)"),
    ("second-0xEA", {"encode": lambda op, *a, **k: opcodes.encode(0xEA if op == 0x2D else op, *a, **k)},
     "exactly one 0xEA"),
    ("screen-position", {"calculate_screen_origin": lambda: opcodes.encode(0xA9, 250)}, "0xA9"),
]


@pytest.mark.parametrize("over, frag", [(o, f) for _i, o, f in _MUTANTS], ids=[i for i, _o, _f in _MUTANTS])
def test_the_audit_refuses_each_mutant_emitter(monkeypatch, over, frag):
    monkeypatch.setattr(P, "opcodes", _Shim(**over))
    body = P.daemon_body(_spec(), _parts(), [_BOX])
    bad = P.audit_body(body, _spec(), _parts(), [_BOX])
    assert any(frag in b for b in bad), bad
    with pytest.raises(P.PhotoError, match="self-audit"):
        P.entry_bytes(_spec(), _parts(), [_BOX])


@pytest.mark.parametrize("mut, frag", [
    ("keyon", "B_KEYON"),
    ("negative-mask", "reads back NEGATIVE"),
    ("global-write", "not allowed"),
])
def test_the_audit_refuses_forbidden_tokens(monkeypatch, mut, frag):
    """[B_KEY -> B_KEYON] [const(32768) key mask] [a Global write]"""
    if mut == "keyon":
        monkeypatch.setattr(P, "_key", lambda m: f"{P._k(m)} B_KEYON")
    elif mut == "negative-mask":
        monkeypatch.setattr(P, "_k", lambda m: "const(32768)" if m == 0x1 else (f"const({m})" if m <= 0x7FFF
                                                                               else f"const4({m})"))
    else:
        real = P.L
        monkeypatch.setattr(P, "L", lambda n: "Global.Int16[1500]" if n == "GR" else real(n))
    bad = P.audit_body(P.daemon_body(_spec(), _parts(), [_BOX]), _spec(), _parts(), [_BOX])
    assert any(frag in b for b in bad), bad
