"""[ff9mapkit netsync s154] THE DIGIT-PICK LAW's REPO HALF (studies/coop-review/REVIEW.md 1.6 / appendix #33): the solo bench
(studies/test-harness/scenarios/coop_digit_picks.py) run against the stand-in's digit-panel model (harness/fakegame.py
FakeGame._nb_digit_tick -- the engine's press path and its two rules, twinned), on the s154 rung, under the `bbench digitsnap
off` lever (s153's draw and press verbatim) and on the s153 stand-in (no digit input: absent, never a calibration).

The engine half -- the rules, the resolvers and s153's position press as the mutant, and the refusal log (PickLogFresh,
against the LAST-key compare as its mutant) -- is NetSyncBattle.DigitPickSelfTest ("digit picks selftest: OK (22 rows)"); a
stand-in cannot run it, so the bench's K1 reads red here until the stand-in's proof block models that line (the same for
K-INV: the stand-in writes no autosave). Every scenario-touching test runs the bench in a CHILD process (the scenario puts
its own dir on sys.path -- never this process's).
"""
import json
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from harness import Session                                        # noqa: E402
from harness import fakegame as FG                                 # noqa: E402

SCENARIOS = REPO / "studies" / "test-harness" / "scenarios"
#: the bench's reds the STAND-IN cannot avoid: no s154 proof line in its proof block (K1), no autosave (K-INV)
STAND_IN_GAPS = {"K1", "K-INV"}
DIGIT_LEGS = {"K2-pre", "I1", "I2", "T1-pre", "T1", "T2-pre", "T2a", "T2b"}

_CHILD = r"""
import importlib.util, json, os, pathlib, sys, tempfile
scen, tools, kit = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
sys.path.insert(0, kit)
from harness import Session
from harness import fakegame as FG
spec = importlib.util.spec_from_file_location("coop_digit_picks", os.path.join(scen, "coop_digit_picks.py"))
dp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dp)
doc = json.loads(sys.stdin.read() or "{}")
"""

_RUNS = _CHILD + r"""
results = {}
_frame_after = dp.frame_after
for name, run in doc["runs"].items():
    # "blind": the frame_after calls (1-based) that see no frame -- the bench host never took one in TAKE_S (review L14's
    # non-behavioural red: the leg reads red, and no s153 marker was seen)
    blind, calls = set(run.get("blind") or ()), [0]
    def frame_after(g, taken0, timeout=dp.TAKE_S, _blind=blind, _calls=calls):
        _calls[0] += 1
        return (None, g.state) if _calls[0] in _blind else _frame_after(g, taken0, timeout)
    dp.frame_after = frame_after
    t = pathlib.Path(tempfile.mkdtemp())
    (t / "x64").mkdir()
    (t / "x64" / "FF9.exe").write_bytes(b"MZ")
    (t / "x64" / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    (t / "FF9CustomMap").mkdir()
    (t / "FF9CustomMap" / "DictionaryPatch.txt").write_text(
        "".join(f"FieldScene {f} 11 T{f} T{f} {f}\n" for f in (30602, 30604)), encoding="utf-8")
    fake = FG.FakeGame(t)
    fake.fps = 240
    if run.get("caps"):
        fake.netsync_caps = FG.caps_through(run["caps"])
    fake.battle_seat_party = True
    fake.party_adds = {30604: (1, 2, 3)}
    fake.atb_gain, fake.enemy_hit, fake.cmd_resolve_frames = 60, 1, 45
    dp.cb.CALIBRATE = bool(run.get("cal"))
    g = Session(game_path=t, run_dir=t / "run", save_dir=t / "player-saves", pid_probe=lambda: [],
                launcher=lambda exe, fake=fake: fake.start(), boot_timeout=15.0, verbose=False)
    with g:
        g._booted_once = True
        dp.run(g)
        rows = list(g.checks)
    log = pathlib.Path(fake.memoria_log).read_text(encoding="utf-8", errors="replace")
    results[name] = {"red": sorted(r["what"].split(":")[0] for r in rows if not r["ok"]),
                     "all": sorted(r["what"].split(":")[0] for r in rows),
                     "detail": {r["what"].split(":")[0]: r["detail"][:900] for r in rows},   # the Ledger's width
                     "log": [ln.split("|M| ", 1)[-1] for ln in log.splitlines() if "digit" in ln]}
print(json.dumps(results))
"""


def _child(script: str, payload=None, *, timeout: float = 600.0) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-c", script, str(SCENARIOS), str(REPO / "tools"), str(REPO / "ff9mapkit")],
                         env=env, input=json.dumps(payload or {}), capture_output=True, text=True, timeout=timeout)
    assert out.returncode == 0, out.stderr[-3000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def _tables() -> dict:
    return _child(_CHILD + r"""
def fr(action, ident, mask, slot=3):
    return {"slot": slot, "action": action, "menu": 0, "id": ident, "mask": mask, "cursor": 0}
it, atk = dp.cb.ACT_ITEM, dp.cb.ACT_ATTACK
marks = {"I1": [dp.s153_marker("I1", x) for x in (fr(it, 239, 8), fr(it, 238, 8), None, fr(it, 239, 8, slot=2))],
         "I2": [dp.s153_marker("I2", x) for x in (fr(it, 238, 8), fr(it, 239, 8), None, fr(atk, 238, 8))],
         "T1": [dp.s153_marker("T1", x) for x in (fr(atk, 0, 4), fr(atk, 0, 2), None, fr(it, 0, 4))],
         "T2a": [dp.s153_marker("T2a", x) for x in (fr(atk, 0, 4), fr(atk, 0, 0x10), None, fr(atk, 0, 4, slot=1))],
         "T2b": [dp.s153_marker("T2b", fr(atk, 0, 4))]}
print(json.dumps({"catalog": sorted(dp._catalog(False)), "catalog_cal": sorted(dp._catalog(True)),
                  "order_cal": list(dp._catalog(True)), "markers": sorted(dp.S153_MARKERS), "marks": marks,
                  "predicted": list(dp.PREDICTED_S153), "legs": list(dp.LEGS), "probe": dp.PROBE,
                  "r1": dp.cb.roster_decode(dp.R1), "r2": dp.cb.roster_decode(dp.R2),
                  "doc": " ".join((dp.__doc__ or "").split())}))
""")


def test_the_benchs_tables_are_its_docstring():
    t = _tables()
    cat, cal = set(t["catalog"]), set(t["catalog_cal"])
    assert cat == DIGIT_LEGS | {"K0", "K1", "K-INV", "K-R"} and set(t["legs"]) == DIGIT_LEGS
    # the calibration drops T2b (unreached under the lever: T2a's accepted frame closed the pick) and judges K-CAL-M, then
    # K-CAL (review L14: a K-CAL-M red is an unpredicted red to K-CAL)
    assert cal == (cat - {"T2b"}) | {"K-CAL-M", "K-CAL"}
    assert t["order_cal"].index("K-CAL-M") < t["order_cal"].index("K-CAL")
    assert set(t["predicted"]) == {"I1", "I2", "T1", "T2a"} and set(t["predicted"]) <= cal and "T2b" not in t["predicted"]
    # each predicted leg's marker is s153's BEHAVIOUR, never "red": the slid frame, not its neighbour, not "no frame",
    # not another slot's or action's frame; a leg outside the prediction has none
    assert t["markers"] == sorted(t["predicted"])
    assert t["marks"] == {c: [True, False, False, False] for c in t["predicted"]} | {"T2b": [False]}
    assert t["probe"] == "netsync.battle.menu.feed.digit_taken"
    assert [(i["id"], i["count"], i["tinfo"]) for i in t["r1"]["items"]] == [(236, 1, 13), (238, 2, 13), (239, 3, 13)]
    assert [(i["id"], i["count"]) for i in t["r2"]["items"]] == [(238, 2), (239, 3)]
    assert [c["menu"] for c in t["r1"]["slots"]["3"]] == [0]
    for frag in ("THE CALIBRATION IS BY LEVER", "UnityEngine.Input.GetKeyDown", "PREDICTED_S153 = {I1, I2, T1, T2a}",
                 "bbench digitsnap off", "COOP_CALIBRATE=1", "coop_digit_picks.py --instance", "COOPPARTY (30604)",
                 "THE UNATTENDED LAW", "THE BENCH ORDERING LAW", "12/12", "T2b is NOT predicted", "K-CAL-M", "9/13",
                 "digit picks selftest: OK (22 rows)"):
        assert frag in t["doc"], frag


def test_the_driver_knows_the_digit_ops_and_tells_them_by_a_feed_key():
    assert Session.NETSYNC_BBENCH_OPS[-2:] == ("digit", "digitsnap") == FG.NETSYNC_BBENCH_OPS[-2:]
    for op in ("digit", "digitsnap"):
        attr, key, patch, _what = Session.NETSYNC_BBENCH_OP_CAPS[op]
        assert (attr, key, patch) == ("coop_digit_pick", "netsync.battle.menu.feed.digit_taken", "s154")
    assert key.rsplit(".", 1)[-1] in FG.NETSYNC_FEED_CAP_KEYS[FG.NETSYNC_S154_RUNG] == FG.NETSYNC_FEED_DIGIT_KEYS
    assert FG.NETSYNC_BATTLE_CAPS[FG.NETSYNC_S154_RUNG][0] == "s154"
    assert Session.NETSYNC_BBENCH_PRIOR_LISTS["s154"] == "|".join(FG.NETSYNC_BBENCH_OPS_S107)


def test_the_bench_runs_green_on_the_s154_stand_in():
    r = _child(_RUNS, {"runs": {"plain": {}}})["plain"]
    assert set(r["red"]) <= STAND_IN_GAPS, {c: r["detail"][c] for c in r["red"]}
    assert DIGIT_LEGS | {"K0", "K-R"} <= set(r["all"]) - set(r["red"])
    assert r["all"] == sorted(_tables()["catalog"])                  # every catalog row recorded, each once
    d = r["detail"]
    assert "'id': 238" in d["I1"] and "'mask': 8" in d["I1"]
    assert "(item 236) is used up since the page was drawn" in d["I2"]
    assert "'mask': 2" in d["T1"] and "(unit 1) is KO since the list was drawn" in d["T2a"] and "'mask': 16" in d["T2b"]
    # the refusal's log line, once per (pick, digit, verdict)
    lines = [ln for ln in r["log"] if ln.startswith("[NetSync] digit panel: ")]
    assert len(lines) == 2 and all(ln.endswith("-- not sent (the pick stays open: pick another or [0] back)") for ln in lines)


def test_the_bench_calibrates_under_the_lever_on_the_stand_in():
    """`bbench digitsnap off`: exactly PREDICTED_S153 red among the digit legs, each BEHAVIOURALLY -- I1 commits the Elixir,
    I2 sends the Ether, T1 and T2a send Garnet -- T2b is dropped, K-R reads the lever's release line."""
    t = _tables()
    r = _child(_RUNS, {"runs": {"lever": {"cal": True}}})["lever"]
    red = set(r["red"])
    assert red - STAND_IN_GAPS - {"K-CAL"} == set(t["predicted"]), r["red"]
    assert {"K-CAL", "K-CAL-M"} <= set(r["all"]) and "T2b" not in r["all"]
    assert ("K-CAL" in red) == bool(red & STAND_IN_GAPS)              # K-CAL judges the WHOLE set: a stand-in gap reds it
    d = r["detail"]
    assert "'id': 239" in d["I1"] and "'id': 238" in d["I2"] and "'mask': 4" in d["T1"] and "'mask': 4" in d["T2a"]
    # review L14: every predicted red was s153's marker, SEEN in the frame its leg read -- so K-CAL-M is green and K-CAL's
    # only unpredicted reds are the stand-in's own gaps
    assert "K-CAL-M" not in red and d["K-CAL-M"].count(" SEEN (") == 4 and "NOT seen" not in d["K-CAL-M"], d["K-CAL-M"]
    assert "K-CAL-M" not in d["K-CAL"].split("unpredicted reds:")[1], d["K-CAL"]
    assert "K-R" not in red
    assert any("digit-panel snapshot OFF -- CALIBRATION" in ln for ln in r["log"])
    assert any("digit-panel snapshot back ON (released with the harness)" in ln for ln in r["log"])
    assert not any(ln.startswith("[NetSync] digit panel: ") for ln in r["log"])   # s153 refused nothing


def test_a_red_that_is_not_s153s_behaviour_cannot_pass_the_calibration():
    """Review L14: under the lever, I1's frame never reaches the bench host (the driver's first frame_after sees none) -- I1
    still reads red and the digit legs' red SET is exactly the prediction (the set judge alone would pass it), but its marker
    (the Elixir) was never seen: K-CAL-M is red naming I1, and K-CAL counts K-CAL-M as an unpredicted red."""
    t = _tables()
    r = _child(_RUNS, {"runs": {"blind": {"cal": True, "blind": [1]}}})["blind"]
    red, d = set(r["red"]), r["detail"]
    assert red & DIGIT_LEGS == set(t["predicted"]), r["red"]          # the same reds as the honest calibration...
    assert "frame None" in d["I1"]                                      # ...I1's for want of a frame, not for the Elixir
    assert "K-CAL-M" in red and "I1 NOT seen" in d["K-CAL-M"], d["K-CAL-M"]
    assert all(f"{c} SEEN (" in d["K-CAL-M"] for c in ("I2", "T1", "T2a")), d["K-CAL-M"]
    assert "K-CAL" in red and "K-CAL-M" in d["K-CAL"].split("unpredicted reds:")[1], d["K-CAL"]


def test_the_stand_ins_refusal_log_is_once_per_pick_digit_and_verdict():
    """Review L15, the stand-in's twin of NetSyncBattle.PickLogFresh (whose engine rows are L1-L3 of "digit picks selftest"):
    the review's [2] [3] [2] [3] on one pick logs twice (a LAST-key compare logged four times), a new verdict on a logged
    digit logs, a new pick clears the logged pairs."""
    def run(presses):
        mask, epoch, out = 0, -1, []
        for pick, digit, verdict in presses:
            fresh, mask, epoch = FG.digit_log_fresh(mask, epoch, pick, digit, verdict)
            out.append(fresh)
        return out
    ko, gone, used = FG.DIGIT_PICK_FALLEN, FG.DIGIT_PICK_GONE, FG.DIGIT_PICK_USED_UP
    assert run([(1, 2, ko), (1, 3, ko), (1, 2, ko), (1, 3, ko)]) == [True, True, False, False]
    assert run([(1, 2, ko), (1, 2, gone), (1, 2, gone)]) == [True, True, False]
    assert run([(1, 3, ko), (2, 3, ko), (2, 3, ko), (3, 3, ko)]) == [True, True, False, True]
    assert run([(1, 9, used), (1, 9, used), (1, 0, 0)]) == [True, False, True]        # the widest pair has its own bit


def test_the_bench_reads_absent_on_the_s153_stand_in_never_a_calibration():
    """The s153 engine has no digit input: K2-pre red "absent", every other digit leg red "not reached", and the driver never
    sends a digit op (the feed's own key refuses it before the step)."""
    r = _child(_RUNS, {"runs": {"s153": {"caps": "worlddio"}}})["s153"]
    assert DIGIT_LEGS <= set(r["red"]), r["red"]
    assert "absent" in r["detail"]["K2-pre"] and "this engine has no digit input" in r["detail"]["I1"]
    assert "K0" not in r["red"] and "K-R" not in r["red"]
