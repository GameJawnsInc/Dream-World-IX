"""[ff9mapkit netsync s154] THE PAIRING-AUTOSAVE + TITLE BENCH's pure judges -- studies/test-harness/scenarios/coop_ramp_title.py.

The solo T2 bench judges #17 (the pairing autosave) on the guest's own byte after the exit ramp's whole-state reload, and
#28 (the title ends the mirror) on whether a New Game picked at the title is YANKED back to the session's field. These
tests feed its judges hand-built publishes shaped like each engine's outcome and pin that:

  * P17: an s153-shaped reload (the pre-poke entry autosave: own byte 0x00) reads P17*-a RED and the safety row green; the
    s154 shape (the pairing autosave: 0x3C) reads green; host story in the restored save (1121 = 0xA5) reads P17*-b RED;
    the pairing point's field row (-c) reads the field;
  * the own walk's instrument row refuses a follow move before the landing, a refused warp, and no landing;
  * T28: an s153-shaped title (ramp_pending true, cause 'config') + New Game yanked to 250 with the ramp's line reads both
    rows RED; the s154 shape reads both green; a yank alone, or a stuck mirror alone, reads its own row red;
  * the own byte is picked off the HOST's story (never a byte the mirror would write 0x3C into);
  * the ini pre-check refuses AutoSaveOnlyAtMoogle / DisableAutoSave, and for T28 a missing (or off) SoftReset or Cheats
    -- BOTH gate the chord: UIKeyTrigger's soft-reset branch sits inside HandleBoosterButton, which returns at once unless
    [Cheats] Enabled (engine default 0);
  * the calibration judge: s153-shaped passes, s154-shaped fails, an instrument red fails, an s154 line fails;
  * PREDICTED_S153 names only rows of each leg's own catalog.

Every call runs in a CHILD process (the scenario puts its own dir and tools/ on sys.path, and reads COOP_* at import).
"""
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
SCENARIOS = REPO / "studies" / "test-harness" / "scenarios"
TOOLS = REPO / "tools"
MODULE = "coop_ramp_title"
HOME, AWAY, MARKER, OWN = 250, 30602, 1121, 1122

_CHILD = r'''
import importlib.util, json, os, sys
scen, tools = sys.argv[1], sys.argv[2]
doc = json.loads(sys.stdin.read())
for k, v in (doc.get("env") or {}).items():
    os.environ[k] = v
sys.path.insert(0, tools)
spec = importlib.util.spec_from_file_location("bench_under_test", os.path.join(scen, doc["module"] + ".py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
out = []
for c in doc["calls"]:
    try:
        fn = getattr(m, c["fn"])
        args = [bytes(a["bytes"]) if isinstance(a, dict) and "bytes" in a else a for a in c.get("args", [])]
        val = fn(*args, **c.get("kwargs", {})) if callable(fn) else fn
        out.append({"ok": True, "value": val})
    except Exception as e:
        out.append({"ok": False, "error": repr(e)})
print(json.dumps({"results": out}, default=lambda o: sorted(o) if isinstance(o, (set, frozenset)) else repr(o)))
'''


def call(*calls, env=None):
    doc = {"module": MODULE, "env": dict(env or {"COOP_CALIBRATE": "", "COOP_LEG": "p17-kick"}),
           "calls": [{"fn": c[0], "args": list(c[1]) if len(c) > 1 else [], "kwargs": dict(c[2]) if len(c) > 2 else {}}
                     for c in calls]}
    p = subprocess.run([sys.executable, "-c", _CHILD, str(SCENARIOS), str(TOOLS)], input=json.dumps(doc),
                       capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr[-3000:]
    res = json.loads(p.stdout.strip().splitlines()[-1])["results"]
    for r, c in zip(res, calls):
        assert r["ok"], f"{c[0]}: {r.get('error')}"
    return [r["value"] for r in res]


def doc(*, field=HOME, own=0, marker=0, ui="FieldHUD", control=True, fading=False, mirroring=False, ramp=False,
        cause=None, pending=-1, frame=0):
    """One publish: the watched bits of the own byte and the marker, the place, the session's mirror / ramp keys."""
    flags = {}
    for byte, val in ((OWN, own), (MARKER, marker)):
        for b in range(8):
            flags[str(byte * 8 + b)] = bool(val >> b & 1)
    return {"frame": frame, "ui_state": ui, "fading": fading, "field": {"id": field}, "player": {"control": control},
            "flags": flags, "netsync": {"session": {"mirroring": mirroring, "ramp_pending": ramp, "ramp_cause": cause,
                                                    "follow": {"pending": pending}}}}


# ------------------------------------------------------------------------------------------------ P17
def test_p17_s153_shape_loses_the_byte_s154_shape_keeps_it():
    s153, s154, leak = call(("judge_p17", [doc(own=0x00, marker=0)], {"own_byte": OWN, "start": HOME, "p": "P17K"}),
                            ("judge_p17", [doc(own=0x3C, marker=0)], {"own_byte": OWN, "start": HOME, "p": "P17K"}),
                            ("judge_p17", [doc(own=0x3C, marker=0xA5)], {"own_byte": OWN, "start": HOME, "p": "P17K"}))
    assert s153["a"][0] is False and s153["b"][0] is True and "c" not in s153
    assert s154["a"][0] is True and s154["b"][0] is True
    assert leak["b"][0] is False                        # host story in the guest's save: the safety row


def test_p17_follow_and_ownwalk_read_the_pairing_point_field():
    back, wrong = call(("judge_p17", [doc(field=AWAY, own=0x3C)], {"own_byte": OWN, "start": AWAY, "p": "P17F"}),
                       ("judge_p17", [doc(field=HOME, own=0x3C)], {"own_byte": OWN, "start": AWAY, "p": "P17W"}))
    assert back["c"][0] is True and wrong["c"][0] is False


def test_the_own_walk_row_refuses_a_follow_move_a_refusal_and_no_landing():
    walk = [doc(field=AWAY, frame=1), doc(field=AWAY, control=False, frame=2), doc(field=HOME, fading=True, frame=3),
            doc(field=HOME, frame=4)]
    followed = [doc(field=AWAY, frame=1), doc(field=AWAY, control=False, pending=HOME, frame=2),
                doc(field=HOME, fading=True, frame=3), doc(field=HOME, frame=4)]
    ok, fol, refused, stuck = call(("judge_ownwalk", [walk], {"home": HOME, "accepted": True}),
                                   ("judge_ownwalk", [followed], {"home": HOME, "accepted": True}),
                                   ("judge_ownwalk", [walk], {"home": HOME, "accepted": False}),
                                   ("judge_ownwalk", [walk[:2]], {"home": HOME, "accepted": True}))
    assert ok[0] is True and fol[0] is False and refused[0] is False and stuck[0] is False
    # [ff9mapkit netsync s154 calibration] a follow that STARTED inside the own warp's fade, while the own load landed first:
    # s153 -- its pending survives onto the landing sample; s154 -- the landing step cancels it (the log line)
    survived = [doc(field=AWAY, frame=1), doc(field=AWAY, control=False, pending=HOME, frame=2),
                doc(field=HOME, fading=True, pending=HOME, frame=3), doc(field=HOME, pending=HOME, frame=4)]
    s153, s154, fell = call(("judge_ownwalk", [survived], {"home": HOME, "accepted": True}),
                            ("judge_ownwalk", [followed], {"home": HOME, "accepted": True, "cancelled": True}),
                            ("judge_ownwalk", [followed], {"home": HOME, "accepted": True, "cancelled": False}))
    assert s153[0] is True and "survived the own landing" in s153[1], s153
    assert s154[0] is True and "cancelled by the own landing" in s154[1], s154
    assert fell[0] is False and "FELL before the landing" in fell[1], fell


# ------------------------------------------------------------------------------------------------ T28
RAMP = "[NetSync] session ended -> reloading own autosave (Continue)"


def test_t28_s153_shape_is_yanked_and_held_s154_shape_is_free():
    title153 = [doc(ui="Title", field=HOME, mirroring=True, ramp=True, cause="config", frame=i) for i in range(5)]
    new153 = ([doc(field=70, mirroring=True, ramp=True, cause="config", control=False, frame=10 + i) for i in range(5)]
              + [doc(field=HOME, frame=20 + i) for i in range(5)])
    title154 = [doc(ui="Title", field=HOME, frame=i) for i in range(5)]
    new154 = [doc(field=70, control=False, frame=10 + i) for i in range(10)]
    r153, r154 = call(("judge_t28", [title153, new153, [RAMP]], {"home": HOME}),
                      ("judge_t28", [title154, new154, []], {"home": HOME}))
    assert r153["a"][0] is False and r153["b"][0] is False
    assert r154["a"][0] is True and r154["b"][0] is True


def test_t28_rows_are_independent():
    title = [doc(ui="Title", frame=i) for i in range(3)]
    yanked = [doc(field=70, frame=10), doc(field=HOME, frame=11)]
    held = [doc(field=70, mirroring=True, frame=10 + i) for i in range(3)]
    ry, rh, rempty = call(("judge_t28", [title, yanked, [RAMP]], {"home": HOME}),
                          ("judge_t28", [title, held, []], {"home": HOME}),
                          ("judge_t28", [title, [], []], {"home": HOME}))
    assert ry["a"][0] is False and ry["b"][0] is True
    assert rh["a"][0] is True and rh["b"][0] is False
    assert rempty["a"][0] is False and rempty["b"][0] is False          # no samples is never a pass


def test_a_missing_mirror_key_is_never_read_as_false():
    bare = {"frame": 1, "ui_state": "Title", "field": {"id": HOME}, "player": {}, "flags": {}}
    r, = call(("judge_t28", [[bare], [doc(field=70, frame=2)], []], {"home": HOME}))
    assert r["b"][0] is False


# ------------------------------------------------------------------------------------------------ the pre-checks
def test_the_own_byte_comes_off_the_hosts_story():
    story = [0] * 2048
    story[MARKER] = 0xA5
    clean, = call(("pick_own_byte", [{"bytes": story}]))
    story[OWN] = 0x3C
    moved, = call(("pick_own_byte", [{"bytes": story}]))
    for b in range(1122, 1128):
        story[b] = 0x3C
    none, short = call(("pick_own_byte", [{"bytes": story}]), ("pick_own_byte", [{"bytes": [0] * 100}]))
    assert clean[0] == OWN and moved[0] == 1123 and none[0] is None and short[0] is None


def test_the_ini_precheck():
    good = {"AutoSaveOnlyAtMoogle": "0", "DisableAutoSave": None, "SoftReset": "1", "CheatsEnabled": "1"}
    p17, moogle, off, t28, t28_bad, t28_cheats = call(
        ("ini_verdict", [good, "p17-kick"]),
        ("ini_verdict", [dict(good, AutoSaveOnlyAtMoogle="1"), "p17-kick"]),
        ("ini_verdict", [dict(good, DisableAutoSave="1"), "p17-follow"]),
        ("ini_verdict", [good, "t28-config"]),
        ("ini_verdict", [dict(good, SoftReset=None), "t28-grace"]),
        ("ini_verdict", [dict(good, CheatsEnabled="0"), "t28-config"]))
    assert p17[0] and not moogle[0] and not off[0] and t28[0] and not t28_bad[0] and not t28_cheats[0]
    # [ff9mapkit netsync s154] an ABSENT [Cheats] Enabled is the engine default 0: HandleBoosterButton returns before the
    # soft-reset branch, so the chord can never fire -- refused, and the reason says why
    t28_absent, p17_no_reset, p17_no_cheats = call(("ini_verdict", [dict(good, CheatsEnabled=None), "t28-grace"]),
                                                   ("ini_verdict", [dict(good, SoftReset=None), "p17-kick"]),
                                                   ("ini_verdict", [dict(good, CheatsEnabled="0"), "p17-follow"]))
    assert not t28_absent[0] and "HandleBoosterButton" in t28_absent[1], t28_absent
    assert "HandleBoosterButton" in t28_cheats[1], t28_cheats
    assert p17_no_reset[0] and p17_no_cheats[0]          # the chord is T28's alone


def test_s154_lines_are_recognised():
    lines = ["[NetSync] pairing autosave written on field 250 (the pairing window): leaving co-op returns you here",
             "[NetSync] pairing autosave declined at the follow-warp on field 30602: you were not free-standing -- x",
             "[NetSync] no pairing autosave this session: the mirror armed at field 250's load",
             "[NetSync] at the title: the story mirror ends here -- Continue, Load and New Game each replace the whole state",
             "[NetSync] at the title: the follow-warp to field 30602 is dropped in its fade -- Continue, Load and New Game "
             "each replace the whole state (the title owns the screen)",
             RAMP, "[NetSync] state-mirror ARMED -- this guest's fields now stage the HOST's story"]
    seen, = call(("s154_seen", [lines]))
    assert seen == lines[:5]


# ------------------------------------------------------------------------------------------------ the calibration
def test_calibration_judgement():
    env = {"COOP_CALIBRATE": "1", "COOP_LEG": "t28-config"}
    cat, pred = call(("catalog", ["t28-config"]), ("PREDICTED_S153",), env=env)
    done = {c: True for c in cat if c != "T28C-CAL"}
    s153 = dict(done, **{"T28C-a": False, "T28C-b": False})
    instr = dict(s153, **{"T2-PEER": False})
    ok153, ok154, okinstr, okline = call(
        ("cal_judgement", [s153, pred["t28-config"], [], "T28C-CAL"]),
        ("cal_judgement", [done, pred["t28-config"], [], "T28C-CAL"]),
        ("cal_judgement", [instr, pred["t28-config"], [], "T28C-CAL"]),
        ("cal_judgement", [s153, pred["t28-config"], ["[NetSync] at the title: the story mirror ends here"], "T28C-CAL"]),
        env=env)
    assert ok153[0] is True, ok153
    assert ok154[0] is False and "stayed GREEN" in ok154[1]
    assert okinstr[0] is False and "T2-PEER" in okinstr[1]
    assert okline[0] is False and "s154" in okline[1]


def test_predicted_rows_live_in_each_legs_catalog():
    legs, pred = call(("LEGS",), ("PREDICTED_S153",))
    cats = call(*[("catalog", [leg, True]) for leg in legs])
    for leg, cat in zip(legs, cats):
        assert pred[leg] and all(c in cat for c in pred[leg]), leg
        assert f"{dict(zip(legs, ['P17K', 'P17F', 'P17W', 'T28C', 'T28G']))[leg]}-CAL" in cat
        assert "T2-SAND" in cat and "T2-INI0" in cat
