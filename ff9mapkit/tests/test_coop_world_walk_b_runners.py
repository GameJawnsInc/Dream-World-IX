"""[ff9mapkit netsync s167] WORLD WALK, ROUND B -- THE RUNNERS' REPO HALF (studies/world-coop/s167/round_b_*.sh): the bench session runs
them after the s167 build (OLD on the live s166 BEFORE it), one leg per launch, so a runner that names a leg or a lever its scenario
refuses burns a launch, and one that drops a leg drops a row. Pinned here, offline:

  * every runner: LF and ASCII (bash reads a CR as part of the command; `*.sh text eol=lf`), sourcing round_b_lib.sh and its preflight;
  * the library: round A's guards (benchguard, FF9 closed, the owner's bridge DOWN for T2, solo_ini.py), the DLL pin (OLD on the live
    s166 b24e0123ac93960c, ROUND_B_DLL), ROUND_B_FROM / ROUND_B_NOT_AFTER, THE EXCLUDED PORT RANGE's knobs (ROUND_B_*, round A's
    ROUND_A_* honoured), FF9_S167_CLONE for the proof's exact tallies;
  * OLD: every round-B solo leg, T2 leg and the round-B duo, each under COOP_CALIBRATE=1;
  * NEW: every round-B leg once, in the design's Order (the walk; the refusal; pairing / stall hole / decline / fingerprint / TPS; the
    minimap close; decision 8 last; T2; the duo), no calibration;
  * LEVER: every (leg, lever) the scenarios define, exactly, each under COOP_CALIBRATE=1 (the tps leg with none);
  * REGRESS: round A's own legs and every leg of round A's regression set, unchanged (the scenarios pull the s166 lever set themselves);
  * every duo through the library's $DUO (the port knob), every solo leg through $SOLO.
"""
import json
import os
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCENARIOS = REPO / "studies" / "test-harness" / "scenarios"
RUNNERS = REPO / "studies" / "world-coop" / "s167"
ROUND_A = REPO / "studies" / "world-coop" / "s166-handoff"
NAMES = ("round_b_lib.sh", "round_b_old.sh", "round_b_new.sh", "round_b_lever.sh", "round_b_regress.sh")

_TABLES = r"""
import importlib.util, json, os, sys
scen, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
sys.path.insert(0, scen)
for k in [k for k in os.environ if k.startswith("COOP_")]:
    os.environ.pop(k)
def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(scen, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
ww, t2 = load("coop_world_walk"), load("coop_world_walk_t2")
print(json.dumps({"b_legs": list(ww.B_LEGS), "b_levers": {k: list(v) for k, v in ww.B_LEVERS.items()}, "a_legs": list(ww.A_LEGS),
                  "pair": ww.PAIR_LEG, "t2_legs": list(t2.LEGS), "b_t2_legs": list(t2.B_T2_LEGS),
                  "b_t2_levers": {k: list(v) for k, v in t2.B_T2_LEVERS.items()}, "duo_b_levers": list(t2.DUO_B_LEVERS),
                  "s166_set": [list(op) for op in ww.S166_LEVER_SET]}))
"""


@pytest.fixture(scope="module")
def tables() -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _TABLES, str(SCENARIOS), str(REPO / "tools")], env=env,
                         capture_output=True, text=True, timeout=180)
    assert out.returncode == 0, out.stderr[-3000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def _text(name: str) -> str:
    return (RUNNERS / name).read_text(encoding="ascii")


def _legs(text: str) -> list:
    """Each `leg` line (its continuation joined): the runner's launches, in order."""
    joined = re.sub(r"\\\n\s*", " ", text)
    return [ln.strip() for ln in joined.splitlines() if ln.strip().startswith("leg ")]


def test_every_runner_is_lf_ascii_and_sources_the_library():
    for name in NAMES:
        b = (RUNNERS / name).read_bytes()
        assert b"\r" not in b and all(c < 128 for c in b), name
        text = b.decode("ascii")
        assert text.startswith("#!/usr/bin/env bash\n"), name
        if name != "round_b_lib.sh":
            assert '. "$(dirname "$0")/round_b_lib.sh"' in text and re.search(r"^ROUND_B_KIND=\w+$", text, re.M), name
            assert re.search(r"^preflight (old|new) t2$", text, re.M), name
    assert "preflight old t2" in _text("round_b_old.sh")
    for name in ("round_b_new.sh", "round_b_lever.sh", "round_b_regress.sh"):
        assert "preflight new t2" in _text(name), name


def test_the_library_keeps_round_as_guards_and_the_round_b_knobs():
    lib = _text("round_b_lib.sh")
    for frag in ("bench_blockers", "refuse_message", "IMAGENAME eq FF9.exe", "('127.0.0.1',49201)", "S166_DLL=b24e0123ac93960c",
                 'SOLO="py studies/world-coop/s166-handoff/solo_ini.py"', "ROUND_B_DLL", "ROUND_B_FROM", "ROUND_B_NOT_AFTER",
                 'DUO_PORTS="${ROUND_B_DUO_PORTS:-${ROUND_A_DUO_PORTS:-}}"', 'PEER_PORT="${ROUND_B_PEER_PORT:-${ROUND_A_PEER_PORT:-}}"',
                 'DUO="py tools/harness/duo.py${DUO_PORTS:+ --bridge-ports $DUO_PORTS}"', "export FF9_S167_CLONE=",
                 "world_walk_engine_source(stage=167)", "/c/gd/Dream-World-IX/.harness-runs/s167-round-b/"):
        assert frag in lib, frag
    assert (ROUND_A / "solo_ini.py").is_file()
    # OLD pins the live s166; NEW / LEVER / REGRESS refuse it (and honour ROUND_B_DLL)
    assert '[ "$dll" = "${ROUND_B_DLL:-$S166_DLL}" ]' in lib and '[ "$dll" != "$S166_DLL" ]' in lib
    assert 'if [ "$kind" = "t2" ]; then bridge_down' in lib


def test_old_calibrates_every_round_b_leg_on_s166(tables):
    legs = _legs(_text("round_b_old.sh"))
    old = _text("round_b_old.sh")
    assert all("COOP_CALIBRATE=1" in ln for ln in legs), legs
    m = re.search(r"^for l in ([a-z ]+); do\n\s+leg \"OLD solo", old, re.M)
    assert m and m.group(1).split() == tables["b_legs"], m and m.group(1)
    m = re.search(r"^for l in ([a-z ]+); do\n\s+leg \"OLD T2", old, re.M)
    assert m and m.group(1).split() == tables["b_t2_legs"], m and m.group(1)
    assert any("COOP_WWT_DUO=b $DUO $SC/coop_world_walk_t2.py" in ln for ln in legs)
    assert "COOP_WW_LEVER" not in old and "COOP_WWT_LEVER" not in old


def test_new_runs_every_round_b_leg_once_in_the_designs_order(tables):
    new = _text("round_b_new.sh")
    legs = _legs(new)
    assert "COOP_CALIBRATE" not in new and "LEVER" not in "".join(legs)
    solo = [re.search(r"COOP_WW_LEG=(\w+)", ln).group(1) for ln in legs if "COOP_WW_LEG=" in ln]
    t2 = [re.search(r"COOP_WWT_LEG=(\w+)", ln).group(1) for ln in legs if "COOP_WWT_LEG=" in ln]
    assert sorted(solo) == sorted(tables["b_legs"]) and sorted(t2) == sorted(tables["b_t2_legs"]), (solo, t2)
    order = [new.find(k) for k in ("COOP_WW_LEG=free", "COOP_WW_LEG=stale", "COOP_WW_LEG=entry", "COOP_WW_LEG=refuse",
                                   "COOP_WWT_LEG=stallhole", "COOP_WW_LEG=decline", "COOP_WW_LEG=tps", "COOP_WW_LEG=minimap",
                                   "COOP_WW_LEG=map", "COOP_WWT_LEG=walk", "COOP_WWT_LEG=hostb", "COOP_WWT_DUO=b $DUO")]
    assert -1 not in order and order == sorted(order), order
    assert "S167-WR-GATE" in new and "ROAM-TAPE.md" in new            # the owner-gated tape, named


def test_lever_pulls_each_scenario_lever_alone_and_exactly(tables):
    lever = _text("round_b_lever.sh")
    assert all("COOP_CALIBRATE=1" in ln for ln in _legs(lever))
    solo = re.findall(r"^solo ([a-z]+) ([a-z-]+)$", lever, re.M)
    want = sorted([(leg, v) for leg, vs in tables["b_levers"].items() for v in vs]
                  + [(leg, "-") for leg, vs in tables["b_levers"].items() if not vs])
    assert sorted(solo) == want, (solo, want)
    t2 = re.findall(r"^t2 ([a-z]+) ([a-z]+)$", lever, re.M)
    assert sorted(t2) == sorted((leg, v) for leg, vs in tables["b_t2_levers"].items() for v in vs), t2
    m = re.search(r"^for v in ([a-z ]+); do\n\s+leg \"LEVER duo b", lever, re.M)
    assert m and m.group(1).split() == tables["duo_b_levers"]
    assert "COOP_WWT_DUO=b COOP_WWT_LEVER=$v $DUO $SC/coop_world_walk_t2.py" in lever


def test_regress_runs_round_as_legs_and_its_regression_set_unchanged(tables):
    reg = _text("round_b_regress.sh")
    cmds = [ln.split(" -- ", 1)[1] for ln in _legs(reg)]
    norm = lambda c: re.sub(r"s16[67]-reg-", "s16X-reg-", c).replace("${ROUND_A_PEER_PORT:+COOP_PEER_PORT=$ROUND_A_PEER_PORT}",
                                                                      "${PEER_PORT:+COOP_PEER_PORT=$PEER_PORT}")
    have = {norm(c) for c in cmds}
    for ln in _legs((ROUND_A / "round_a_regress.sh").read_text(encoding="ascii")):
        c = norm(ln.split(" -- ", 1)[1])
        assert c in have, c
    # round A's own legs (round_a_new.sh's), now regression: tx alone (the proof rides it), the rest in one loop
    assert any("COOP_WW_LEG=tx " in c for c in cmds)
    m = re.search(r"^for l in ([a-z ]+); do\n\s+leg \"A: solo", reg, re.M)
    assert m and sorted(m.group(1).split() + ["tx"]) == sorted(tables["a_legs"]), m and m.group(1)
    for leg in ("wire", "old", "roam", "freeze", "host"):
        assert any(f"COOP_WWT_LEG={leg} " in c for c in cmds), leg
    assert any(c == "$DUO $SC/coop_world_walk_t2.py" for c in cmds)                     # the round-A duo
    assert any(f"COOP_WW_LEG={tables['pair']} " in c for c in cmds)
    assert any("COOP_WB_LEG=held " in c for c in cmds)                                  # round B adds the held leg
    assert "COOP_CALIBRATE" not in reg and "COOP_WWT_DUO" not in reg and "worldwalk" not in "".join(cmds)


def test_every_leg_names_only_what_its_scenario_accepts_and_goes_through_the_library(tables):
    for name in NAMES[1:]:
        text = _text(name)
        for leg in re.findall(r"COOP_WW_LEG=([a-z$]+)", text):
            assert leg == "$l" or leg in tables["b_legs"] + tables["a_legs"] + [tables["pair"]], (name, leg)
        for leg in re.findall(r"COOP_WWT_LEG=([a-z$0-9]+)", text):
            assert leg == "$l" or leg == "$1" or (leg in tables["t2_legs"] and leg != "record"), (name, leg)   # the recorder: OWNER-GATED
        for ln in _legs(text):
            kind = ln.split('"', 2)[2].split()[0]
            assert kind in ("solo", "t2", "duo"), (name, ln)
            if kind == "duo":
                assert " $DUO $SC/" in ln and "tools/harness/duo.py" not in ln, (name, ln)
            if kind == "solo":
                assert " $SOLO s167-" in ln and "--field" in ln, (name, ln)
            if kind == "t2":
                assert "$DUO" not in ln and "$SOLO" not in ln, (name, ln)
        assert "tools/harness/duo.py" not in text, name
    reg = _text("round_b_regress.sh")
    sd = [ln for ln in _legs(reg) if "coop_self_dress.py" in ln]
    assert sd == ['leg "coop_self_dress" solo reg_self_dress.log -- env SOLO_INI_FOLLOW=0 $SOLO s167-reg-self-dress -- '
                  "py tools/play.py $SC/coop_self_dress.py --field 250"], sd
    peer = [ln for ln in _legs(reg) if "coop_climb_anim_peer.py" in ln]
    assert len(peer) == 1 and " env ${PEER_PORT:+COOP_PEER_PORT=$PEER_PORT} py tools/play.py " in peer[0], peer
