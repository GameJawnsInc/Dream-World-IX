"""[ff9mapkit netsync s168] THE GUEST'S MAIN MENU, RUNG 0 -- THE RUNNERS' REPO HALF (studies/field-coop/s168/round_gm_*.sh and their Python
guard round_gm_guard.py) and the stage ladder's regression pins. The bench session runs the runners after the s168 deploy (OLD on the live
s167 BEFORE it, BRACKET on the pinned W1a/b build), one leg per launch, so a runner that names a leg or a lever its scenario refuses burns a
launch, one that drops a leg drops a row, and a guard that cannot fail guards nothing. Pinned here, offline (nothing launched, nothing
listening on Any: the one socket test is a client against a loopback listener):

  * every runner: LF and ASCII (`*.sh text eol=lf`), sourcing round_gm_lib.sh and its preflight by kind (old / bracket / new);
  * the library: s167's guards (benchguard, FF9 closed, the owner's bridge DOWN for T2, solo_ini.py), the DLL pins (OLD on s167
    12be3220520813a6, BRACKET on the W1a/b pin 532486364ec05354, NEW neither; ROUND_GM_DLL), the gate window, the port check, the stage's
    sources (FF9_S168_CLONE exported; FF9_S167_CLONE never defaulted), the proof block;
  * THE PLAN (ROUND_GM_PLAN=1, the runners' own control flow, launching nothing): OLD calibrates every solo / T / duo leg the scenarios
    define (the b3 tape's leg excepted); NEW runs every leg once in the design's Order, GM0-QUIT-EXIT last, the tape legs only with a tape;
    LEVER runs every (leg, lever) the scenarios define, exactly; REGRESS carries s167's whole regression set, round B's own legs, the diorama
    legs, the B4-B5 set, s164's Pause MENU and coop_cut_hold's s121 leg unchanged; BRACKET the diorama legs and their D half; RERUN maps
    kind:route:leg[:lever] and refuses a mixed pin;
  * the guard: the window (wrapping midnight), the excluded ranges, the port refusals, the ini read, the proof block and its diff (only the
    round's movers may move), THE CLONE MOVED ON;
  * the stage ladder: _coop_peer_bench.STAGE_KEYS' s168 key, and coop_cut_hold's predictions on an s168 guest equal an s131 one's (its s121
    leg UNCHANGED: the fallback row).
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCENARIOS = REPO / "studies" / "test-harness" / "scenarios"
RUNNERS = REPO / "studies" / "field-coop" / "s168"
S167 = REPO / "studies" / "world-coop" / "s167"
ROUND_A = REPO / "studies" / "world-coop" / "s166-handoff"
NAMES = ("round_gm_lib.sh", "round_gm_old.sh", "round_gm_new.sh", "round_gm_lever.sh", "round_gm_regress.sh", "round_gm_rerun.sh")

sys.path.insert(0, str(RUNNERS))
import round_gm_guard as G  # noqa: E402

_TABLES = r"""
import json, os, sys
scen, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
sys.path.insert(0, scen)
for k in [k for k in os.environ if k.startswith("COOP_")]:
    os.environ.pop(k)
import coop_guest_menu as gm, coop_guest_menu_duo as gmd, coop_cut_hold as ch, _coop_peer_bench as pb
pred = {}
for leg in ch.PFX:
    for tail in (0.0, 40.0, 120.0):
        for why in (None, "stall_cap"):
            a, b = ch._predicted(leg, 168, tail, why), ch._predicted(leg, 131, tail, why)
            pred[f"{leg}|{tail}|{why}"] = [sorted(a[0]) == sorted(b[0]) and sorted(a[1]) == sorted(b[1]), sorted(a[0])]
fw = {"expect": {"why": "stall_cap", "why_s145": "host_world", "after_field": 0}}
s168_doc = {"netsync": {"guestmenu": {}, "menu_refusal": {}, "battle": {"peer": {"expired": {}}}}}
s131_doc = {"netsync": {"menu_refusal": {}, "battle": {"peer": {"expired": {}}}}}
print(json.dumps({"legs": list(gm.LEGS), "levers": {k: list(v) for k, v in gm.LEG_LEVERS.items()}, "gm_field": gm.GM_FIELD,
                  "duo_legs": list(gmd.DUO_LEGS), "t_legs": list(gmd.T_LEGS),
                  "duo_levers": {k: list(v) for k, v in gmd.LEG_LEVERS.items()},
                  "stage_keys": [list(x) for x in pb.STAGE_KEYS], "s121": [sorted(x) for x in ch._predicted("s121", 168)],
                  "pred": pred,
                  "span": [pb.span_why(fw, pb.engine_stage(s168_doc)), pb.span_why(fw, pb.engine_stage(s131_doc))],
                  "stages": [pb.engine_stage({"netsync": {"guestmenu": {}, "menu_refusal": {}, "battle": {"peer": {"expired": {}}}}}),
                             pb.engine_stage({"netsync": {"menu_refusal": {}, "battle": {"peer": {"expired": {}}}}}),
                             pb.engine_stage({"netsync": {"guestmenu": None}}), pb.engine_stage({})]}))
"""


@pytest.fixture(scope="module")
def tables() -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _TABLES, str(SCENARIOS), str(REPO / "tools")], env=env,
                         capture_output=True, text=True, timeout=240)
    assert out.returncode == 0, out.stderr[-3000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def _text(name: str) -> str:
    return (RUNNERS / name).read_text(encoding="ascii")


def _bash():
    """A POSIX bash for THE PLAN: Git for Windows' on Windows (never System32's WSL launcher), else the PATH's; None = skip."""
    if os.name == "nt":
        for p in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"):
            if os.path.isfile(p):
                return p
        return None
    return shutil.which("bash")


def _plan(tmp_path, runner: str, **env_extra) -> list:
    """THE PLAN of ``runner``: its own control flow under ROUND_GM_PLAN=1 (nothing launched, nothing checked) -> [(n, name, kind, command)]
    of every leg line, plus ('skip', name, why) and ('say', text) rows."""
    bash = _bash()
    if bash is None:
        pytest.skip("no POSIX bash for the runners' plan")
    logs = tmp_path / runner.replace(".sh", "")
    logs.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("COOP_", "ROUND_GM_", "ROUND_B_", "ROUND_A_", "FF9_S16"))}
    env.update(ROUND_GM_PLAN="1", ROUND_GM_LOGS=logs.as_posix(), **env_extra)
    out = subprocess.run([bash, (RUNNERS / runner).as_posix()], cwd=str(REPO), env=env, capture_output=True, text=True, timeout=120)
    assert out.returncode in (0, 2, 3), (out.returncode, out.stdout[-2000:], out.stderr[-2000:])
    rows = []
    for ln in out.stdout.splitlines():
        m = re.match(r"^-- \[(\d+)\] (.+?) \((solo|t2|duo)\): (.*)$", ln)
        if m:
            rows.append((int(m.group(1)), m.group(2).strip(), m.group(3), m.group(4)))
            continue
        m = re.match(r"^-- \[(\d+)\] (.+?): NOT RUN -- (.*)$", ln)
        if m:
            rows.append(("skip", m.group(2), m.group(3)))
            continue
        rows.append(("say", ln))
    return rows


def _legs(rows) -> list:
    return [r for r in rows if isinstance(r[0], int)]


def _env(cmd: str, key: str):
    m = re.search(rf"\b{key}=(\S+)", cmd)
    return m.group(1) if m else None


def _says(rows) -> str:
    return "\n".join(r[1] for r in rows if r[0] == "say")


# ================================================================================================ the files
def test_every_runner_is_lf_ascii_and_sources_the_library():
    for name in NAMES:
        b = (RUNNERS / name).read_bytes()
        assert b"\r" not in b and all(c < 128 for c in b), name
        text = b.decode("ascii")
        assert text.startswith("#!/usr/bin/env bash\n"), name
        if name != "round_gm_lib.sh":
            assert '. "$(dirname "$0")/round_gm_lib.sh"' in text and re.search(r"^ROUND_GM_KIND=", text, re.M), name
            assert re.search(r"^\s*preflight (old|bracket|new|\"\$PIN\")( |$)", text, re.M), name
    assert "preflight old t2 duo" in _text("round_gm_old.sh")
    for name in ("round_gm_new.sh", "round_gm_lever.sh"):
        assert "preflight new t2 duo" in _text(name), name
    reg = _text("round_gm_regress.sh")
    assert "preflight new t2 duo" in reg and "preflight bracket duo" in reg
    b = (RUNNERS / "round_gm_guard.py").read_bytes()
    assert all(c < 128 for c in b)


def test_the_library_keeps_s167s_guards_and_the_s168_pins_and_knobs():
    lib = _text("round_gm_lib.sh")
    for frag in ("bench_blockers", "refuse_message", "IMAGENAME eq FF9.exe", "('127.0.0.1',49201)", "S167_DLL=12be3220520813a6",
                 "W1AB_DLL=532486364ec05354", 'SOLO="py studies/world-coop/s166-handoff/solo_ini.py"', "ROUND_GM_DLL", "ROUND_GM_FROM",
                 "ROUND_GM_NOT_AFTER", "ROUND_GM_NOT_BEFORE", "ROUND_GM_RELAY_PORT", "ROUND_GM_PLAN",
                 'DUO_PORTS="${ROUND_GM_DUO_PORTS:-${ROUND_B_DUO_PORTS:-${ROUND_A_DUO_PORTS:-}}}"',
                 'PEER_PORT="${ROUND_GM_PEER_PORT:-${ROUND_B_PEER_PORT:-${ROUND_A_PEER_PORT:-}}}"',
                 'DUO="py tools/harness/duo.py${DUO_PORTS:+ --bridge-ports $DUO_PORTS}${RELAY_PORT:+ --relay-port $RELAY_PORT}"',
                 'export FF9_S168_CLONE="${FF9_S168_CLONE:-C:/gd/FFIX/Memoria/Assembly-CSharp}"', "/c/gd/Dream-World-IX/.harness-runs/s168-round-gm",
                 "round_gm_guard.py", "$GUARD sources", "$GUARD window", "$GUARD ports", "$GUARD proofs", "$GUARD proofdiff"):
        assert frag in lib, frag
    assert (ROUND_A / "solo_ini.py").is_file()
    # FF9_S167_CLONE is NEVER defaulted: the shared clone carries s168 now (THE CLONE MOVED ON)
    assert "export FF9_S167_CLONE" not in lib
    # the pins by kind: OLD on s167, BRACKET on the W1a/b pin, NEW neither (ROUND_GM_DLL overrides / pins)
    assert '[ "$dll" = "${ROUND_GM_DLL:-$S167_DLL}" ]' in lib and '[ "$dll" = "${ROUND_GM_DLL:-$W1AB_DLL}" ]' in lib
    assert '[ "$dll" != "$S167_DLL" ]' in lib and '[ "$dll" != "$W1AB_DLL" ]' in lib
    assert 'if [ "$kind" = "t2" ]; then bridge_down' in lib and 'if [ "$t2" = 1 ]; then\n    bridge_down' in lib
    # the window and the guards run before EVERY leg (the per-leg cutoff names the leg to resume from)
    body = lib[lib.index("\nleg() {"):]
    i_plan = body.index('if [ "$PLAN" = 1 ]')
    assert body.index("$GUARD window") > i_plan and "resume with ROUND_GM_FROM=$N" in body and body.index("guard_suite") > i_plan
    # the knobs' defaults: the gate window covers 03:00 and the 04:00 task
    assert 'NOT_AFTER="${ROUND_GM_NOT_AFTER:-0230}"' in lib and 'NOT_BEFORE="${ROUND_GM_NOT_BEFORE:-0700}"' in lib
    assert G.NOT_AFTER_DEFAULT == "0230" and G.NOT_BEFORE_DEFAULT == "0700"


# ================================================================================================ THE PLAN
def test_old_calibrates_every_leg_on_s167_and_records_the_proof_reference(tables, tmp_path):
    rows = _plan(tmp_path, "round_gm_old.sh")
    legs = _legs(rows)
    assert [n for n, *_ in legs] == list(range(1, len(legs) + 1))
    assert all("COOP_CALIBRATE=1" in c for *_, c in legs), legs
    assert not any(_env(c, k) for *_, c in legs for k in ("COOP_GM_LEVER", "COOP_GMD_LEVER", "COOP_GMT_LEVER"))
    solo = [(_env(c, "COOP_GM_LEG"), c) for _n, _nm, k, c in legs if k == "solo"]
    assert sorted(l for l, _c in solo) == sorted(tables["legs"]) and solo[0][0] == "proof"           # K1's launch first
    for leg, c in solo:
        assert c.endswith(f"--field {6603 if leg == 'world' else tables['gm_field']}"), c
        assert f" s168-gm-old-{leg} -- py tools/play.py studies/test-harness/scenarios/coop_guest_menu.py" in c, c
    t2 = [_env(c, "COOP_GMT_LEG") for _n, _nm, k, c in legs if k == "t2"]
    assert sorted(t2) == sorted(set(tables["t_legs"]) - {"tape"}), t2                                   # the b3 tape: an s168 host's
    duo = [_env(c, "COOP_GMD_LEG") for _n, _nm, k, c in legs if k == "duo"]
    assert sorted(duo) == sorted(tables["duo_legs"]), duo
    assert "preflight old t2=1 duo=1" in _says(rows) and "proof_reference" in _says(rows)


def test_new_runs_every_leg_once_in_the_designs_order_quitexit_last(tables, tmp_path):
    rows = _plan(tmp_path, "round_gm_new.sh")
    legs = _legs(rows)
    assert not any("COOP_CALIBRATE" in c or "LEVER" in c for *_, c in legs)
    solo = [_env(c, "COOP_GM_LEG") for _n, _nm, k, c in legs if k == "solo"]
    assert sorted(solo) == sorted(tables["legs"]) and solo[-1] == "quitexit" and legs[-1][3].count("COOP_GM_LEG=quitexit") == 1
    duo = [_env(c, "COOP_GMD_LEG") for _n, _nm, k, c in legs if k == "duo"]
    assert sorted(set(duo)) == sorted(tables["duo_legs"]) and duo.count("caps") == 2, duo           # caps twice: LAN and the relay
    assert any("COOP_GMD_LEG=caps" in c and "--topology relay" in c for *_, c in legs)
    t2 = [_env(c, "COOP_GMT_LEG") for _n, _nm, k, c in legs if k == "t2"]
    assert t2 == ["hole", "older166", "older167"], t2                                                 # no tape: its legs NOT RUN
    skips = [r for r in rows if r[0] == "skip"]
    assert [s[1] for s in skips] == ["T2 tape COOP_GMT_RAMP=field", "T2 tape COOP_GMT_RAMP=world"] and "S168-GMT-GATE" in skips[0][2]
    # the Order: the proof, the hole, the key and the seat, the census / restore, the closes one trigger at a time, the measuring rows,
    # the T rows, GM0-QUIT-EXIT last
    order = [c for *_, c in legs]
    at = lambda frag: next(i for i, c in enumerate(order) if frag in c)
    seq = [at("COOP_GM_LEG=proof"), at("COOP_GMT_LEG=hole"), at("COOP_GMD_LEG=key"), at("COOP_GM_LEG=seat"), at("COOP_GM_LEG=refuse"),
           at("COOP_GM_LEG=release"), at("COOP_GM_LEG=close"), at("COOP_GMD_LEG=leave"), at("COOP_GMD_LEG=stall"), at("COOP_GM_LEG=world"),
           at("COOP_GMD_LEG=caps"), at("COOP_GMD_LEG=hudstrip"), at("COOP_GMT_LEG=older166"), at("COOP_GM_LEG=quitexit")]
    assert seq == sorted(seq), seq
    assert "proof_report new" in _says(rows)
    # THE EXCLUDED PORT RANGE: the duo's bridges + relay and the T2 world port are probed -- never the regression's peer port here
    # (49257 sat inside Windows' 49252-49351 exclusion on 11-04: a runner with no peer leg must not refuse on it)
    assert "the port check would probe: 49211 49212 7787 49231" in _says(rows)
    knob = _plan(tmp_path / "ports", "round_gm_new.sh", ROUND_GM_DUO_PORTS="49411,49412", ROUND_GM_RELAY_PORT="7790")
    assert "the port check would probe: 49411 49412 7790 49231" in _says(knob)
    assert all("--bridge-ports 49411,49412 --relay-port 7790 " in c for _n, _nm, k, c in _legs(knob) if k == "duo")
    # with the owner's b3 tape: both ramps of the tape leg run, numbered where the skips were
    rows2 = _plan(tmp_path / "tape", "round_gm_new.sh", ROUND_GM_PLAN_TAPE="C:/tapes/x-guest-menu-1.f9tape")
    t2b = [(c, n) for n, _nm, k, c in _legs(rows2) if k == "t2"]
    tape = [(n, _env(c, "COOP_GMT_RAMP")) for c, n in t2b if _env(c, "COOP_GMT_LEG") == "tape"]
    assert [r for _n, r in tape] == ["field", "world"] and [n for n, _r in tape] == [len(legs), len(legs) + 1]


def test_lever_pulls_each_scenario_lever_alone_and_exactly(tables, tmp_path):
    rows = _plan(tmp_path, "round_gm_lever.sh")
    legs = _legs(rows)
    assert all("COOP_CALIBRATE=1" in c for *_, c in legs)
    solo = sorted((_env(c, "COOP_GM_LEG"), _env(c, "COOP_GM_LEVER")) for _n, _nm, k, c in legs if k == "solo")
    want = sorted((leg, v) for leg, vs in tables["levers"].items() for v in vs)
    assert solo == want, (set(solo) ^ set(want))
    duo = sorted((_env(c, "COOP_GMD_LEG"), _env(c, "COOP_GMD_LEVER")) for _n, _nm, k, c in legs if k == "duo")
    want_d = sorted((leg, v) for leg, vs in tables["duo_levers"].items() for v in vs if leg in tables["duo_legs"])
    assert duo == want_d, (set(duo) ^ set(want_d))
    t2 = sorted((_env(c, "COOP_GMT_LEG"), _env(c, "COOP_GMT_LEVER")) for _n, _nm, k, c in legs if k == "t2")
    want_t = sorted((leg, v) for leg, vs in tables["duo_levers"].items() for v in vs if leg in tables["t_legs"])
    assert sorted(t2 + [("tape", "old")]) == want_t, t2                                               # the tape's lever: with a tape only
    assert [r[1] for r in rows if r[0] == "skip"] == ["LEVER T2 tape old"]
    rows2 = _plan(tmp_path / "tape", "round_gm_lever.sh", ROUND_GM_PLAN_TAPE="C:/tapes/x.f9tape")
    t2b = sorted((_env(c, "COOP_GMT_LEG"), _env(c, "COOP_GMT_LEVER")) for _n, _nm, k, c in _legs(rows2) if k == "t2")
    assert t2b == want_t
    for _n, _nm, k, c in legs:                                                                         # every solo lever's solo_ini label is
        if k == "solo":                                                                                # colon-free (restore:<c> -> restore-<c>)
            assert re.search(r" s168-gm-lever-[a-z]+-[a-z-]+ -- ", c), c


def test_regress_carries_s167s_set_round_bs_legs_the_diorama_legs_and_the_s121_fallback(tmp_path):
    rows = _plan(tmp_path, "round_gm_regress.sh")
    legs = _legs(rows)
    cmds = [c for *_, c in legs]
    assert not any("COOP_CALIBRATE" in c or "guestmenu" in c or "LEVER" in c for c in cmds)       # the guest menu ACT: no lever pulled
    norm = lambda c: re.sub(r"s16[678]-reg-", "s16X-reg-", c)
    text = _text("round_gm_regress.sh")
    joined = re.sub(r"\\\n\s*", " ", text)
    mine = {norm(ln.strip().split(" -- ", 1)[1]) for ln in joined.splitlines() if ln.strip().startswith("leg ")}
    s167 = re.sub(r"\\\n\s*", " ", (S167 / "round_b_regress.sh").read_text(encoding="ascii"))
    for ln in s167.splitlines():
        if ln.strip().startswith("leg "):
            assert norm(ln.strip().split(" -- ", 1)[1]) in mine, ln
    # round B's own legs (round_b_new.sh's), each once with its scenario
    new = (S167 / "round_b_new.sh").read_text(encoding="ascii")
    for key, scen in (("COOP_WW_LEG", "coop_world_walk.py"), ("COOP_WWT_LEG", "coop_world_walk_t2.py")):
        for leg in sorted(set(re.findall(rf"{key}=(\w+)", new))):
            assert len([c for c in cmds if _env(c, key) == leg and scen in c]) >= 1, (key, leg)
    assert any("COOP_WWT_DUO=b " in c and "coop_world_walk_t2.py" in c for c in cmds)
    # the diorama legs on 30602 (Enabled 0 only), the B4-B5 set on 30801, s164's Pause MENU, coop_cut_hold's s121 leg UNCHANGED
    dio = ("coop_diorama_return", "coop_battle_flee_defeat", "coop_battle_end_guest", "coop_battle_result_replay", "coop_leader_guard",
           "coop_stock_menu", "coop_stock_menu_live", "coop_stock_menu_content")
    for s in dio:
        hit = [c for c in cmds if f"/{s}.py " in c]
        assert len(hit) == 1 and "SOLO_INI_FOLLOW=0" in hit[0] and hit[0].endswith("--field 30602"), (s, hit)
    for s in ("coop_dialogue_authority", "coop_talk_relay"):
        hit = [c for c in cmds if f"/{s}.py " in c]
        assert len(hit) == 1 and hit[0].endswith("--field 30801"), (s, hit)
    assert sum("COOP_LEGS=MENU " in c and "coop_field_swap_timing_duo.py --keep-going" in c for c in cmds) == 1
    assert sum(c == "env COOP_CUT_LEG=s121 py tools/play.py studies/test-harness/scenarios/coop_cut_hold.py" for c in cmds) == 1
    assert sum("COOP_WW_LEG=pair " in c for c in cmds) == 1                                         # A0b's T2 pair: PR-SAVEMENU
    assert "preflight new t2=1 duo=1 peer=1 regress=1" in _says(rows) and "proof_report new" in _says(rows)
    # the peer port: this runner's; then coop_ramp_title's 49243 and coop_host_code's 49245 / 49246 (RK-4: the regression's own T2 ports)
    assert "the port check would probe: 49211 49212 7787 49231 49257 49243 49245 49246" in _says(rows)
    peer = _plan(tmp_path / "peer", "round_gm_regress.sh", ROUND_B_PEER_PORT="49258")                 # round B's knob honoured
    assert "the port check would probe: 49211 49212 7787 49231 49258 49243 49245 49246" in _says(peer)
    assert any("COOP_PEER_PORT=49258 " in c and "coop_climb_anim_peer.py" in c for *_, c in _legs(peer))
    assert not any("COOP_PEER_PORT" in c for *_, c in legs)                                            # unset: the scenario's default
    # every duo through the library's $DUO (the port knob), every solo leg through $SOLO; no tools/harness/duo.py spelled out
    assert "tools/harness/duo.py" not in text and all(" $DUO " in ln or "$DUO $SC" in ln for ln in joined.splitlines()
                                                      if ln.strip().startswith("leg ") and '" duo ' in ln)


def test_bracket_runs_the_diorama_legs_and_their_d_half_on_the_w1ab_pin(tmp_path):
    rows = _plan(tmp_path, "round_gm_regress.sh", ROUND_GM_SET="bracket")
    legs = _legs(rows)
    assert "preflight bracket t2=0 duo=1" in _says(rows) and "proof_report bracket" in _says(rows)
    names = [re.search(r"scenarios/(\w+)\.py", c).group(1) for *_, c in legs]
    assert names == ["coop_diorama_return", "coop_battle_flee_defeat", "coop_battle_end_guest", "coop_battle_result_replay",
                     "coop_leader_guard", "coop_stock_menu", "coop_stock_menu_live", "coop_stock_menu_content", "coop_world_battle"]
    assert legs[-1][2] == "duo" and all(k == "solo" for _n, _nm, k, _c in legs[:-1])
    bad = _plan(tmp_path / "bad", "round_gm_regress.sh", ROUND_GM_SET="nope")
    assert not _legs(bad)


def test_rerun_maps_each_item_and_refuses_a_mixed_pin(tmp_path):
    rows = _plan(tmp_path, "round_gm_rerun.sh",
                 ROUND_GM_RERUN="lever:solo:seat:restore:bag new:duo:key new:t2:hole lever:duo:leave:closeold new:solo:world x:solo:y")
    legs = _legs(rows)
    assert [(k, _env(c, "COOP_CALIBRATE")) for _n, _nm, k, c in legs] == [("solo", "1"), ("duo", None), ("t2", None), ("duo", "1"),
                                                                            ("solo", None)]
    assert _env(legs[0][3], "COOP_GM_LEVER") == "restore:bag" and _env(legs[3][3], "COOP_GMD_LEVER") == "closeold"
    assert legs[4][3].endswith("--field 6603") and _env(legs[2][3], "COOP_GMT_LEG") == "hole"
    assert [r[1] for r in rows if r[0] == "skip"] == ["rerun x:solo:y"]
    mixed = _plan(tmp_path / "mixed", "round_gm_rerun.sh", ROUND_GM_RERUN="old:solo:seat")
    assert not _legs(mixed) and "needs ROUND_GM_PIN=old" in _says(mixed)
    old = _plan(tmp_path / "old", "round_gm_rerun.sh", ROUND_GM_PIN="old", ROUND_GM_RERUN="old:solo:seat old:duo:key")
    assert len(_legs(old)) == 2 and "preflight old" in _says(old) and all(_env(c, "COOP_CALIBRATE") == "1" for *_, c in _legs(old))
    wrong = _plan(tmp_path / "wrong", "round_gm_rerun.sh", ROUND_GM_PIN="old", ROUND_GM_RERUN="new:solo:seat")
    assert not _legs(wrong) and "runs old:... items only" in _says(wrong)


def test_from_resumes_with_stable_numbers(tmp_path):
    full = _legs(_plan(tmp_path / "a", "round_gm_new.sh"))
    rows = _plan(tmp_path / "b", "round_gm_new.sh", ROUND_GM_FROM="5")
    legs = _legs(rows)
    assert [n for n, *_ in legs] == [n for n, *_ in full if n >= 5]
    assert sum(1 for r in rows if r[0] == "say" and "skipped (ROUND_GM_FROM=5)" in r[1]) == 4


# ================================================================================================ the guard (pure)
def test_the_gate_window_wraps_midnight_and_can_be_switched_off():
    assert G.hhmm("0230") == 150 and G.hhmm("2:30") == 150 and G.hhmm("2359") == 1439 and G.hhmm("off") is None
    assert G.hhmm("2460") is None and G.hhmm("") is None and G.hhmm("12345") is None
    assert G.in_window(160, 150, 420) and not G.in_window(149, 150, 420) and not G.in_window(420, 150, 420)
    assert G.in_window(1430, 1380, 60) and G.in_window(30, 1380, 60) and not G.in_window(600, 1380, 60)     # 23:00 -> 01:00
    assert not G.in_window(160, 150, 150) and not G.in_window(160, None, 420)
    assert G.window_verdict("0245", "0230", "0700")[0] is False and "inside the nightly gate" in G.window_verdict("0245", "0230", "0700")[1]
    assert G.window_verdict("0900", "0230", "0700")[0] is True and G.window_verdict("2330", "0230", "0700")[0] is True
    assert G.window_verdict("0245", "off", "0700")[0] is True                                       # off disables
    assert G.window_verdict("xx", "0230", "0700")[0] is False                                       # an unreadable clock refuses
    assert G.main(["window", "0300"]) == 1 and G.main(["window", "1200"]) == 0                       # the CLI's defaults


def test_the_port_refusals_name_each_cause():
    netsh = ("\nProtocol tcp Port Exclusion Ranges\n\nStart Port    End Port\n----------    --------\n     49252       49351\n"
             "     50000       50059     *\n\n* - Administered port exclusions.\n")
    ranges = G.parse_excluded(netsh)
    assert ranges == [(49252, 49351), (50000, 50059)]
    probe = {49211: (False, True), 49212: (True, False), 7787: (True, False), 49260: (True, False), 49400: (False, False)}
    why = G.port_refusals([49211, 49212, 7787, 49260, 49201, 50010, 49400], ranges, lambda p: probe.get(p, (True, False)))
    assert len(why) == 5, why
    assert "49211 already ACCEPTS" in why[0] and "49260 is inside the excluded range 49252-49351" in why[1]
    assert "49201 is the owner's" in why[2] and "50010 is inside the excluded range 50000-50059" in why[3]
    assert "49400 cannot be bound" in why[4]
    assert G.port_refusals([49212, 7787], ranges, lambda p: (True, False)) == []


def test_the_port_probe_sees_a_loopback_listener():
    """A client against a loopback listener (never Any): the probe reads the port as accepting."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]
        bindable, accepting = G.probe_port(port)
        assert accepting is True and bindable is False
    finally:
        srv.close()


def test_the_ini_read_is_the_engines_last_wins():
    text = "[Control]\nSoftReset = 0\n; SoftReset = 1\n[Cheats]\nEnabled = 1\n[control]\nSoftReset = 1 ; on\n[Netsync]\nEnabled = 0\n"
    assert G.ini_value(text, "Control", "SoftReset") == "1" and G.ini_value(text, "Cheats", "Enabled") == "1"
    assert G.ini_value(text, "Netsync", "Enabled") == "0" and G.ini_value(text, "Interface", "FadeDuration") is None
    assert G.ini_value('[Interface]\nFadeDuration = "300"\n', "interface", "fadeduration") == "300"


PROOF_LOG = ["2026-11-07 10:00:01 |I| [NetSync] main menu refusal selftest: OK (14 rows)",
             "2026-11-07 10:00:01 |I| [NetSync] diorama containment selftest: OK (r9[scope=ok] party[refs=ok untouched=ok])",
             "2026-11-07 10:00:01 |I| [NetSync] diorama seat selftest: OK (31 rows)",
             "2026-11-07 10:00:01 |I| [NetSync] overlay text selftest: OK (58 rows)",
             "2026-11-07 10:00:02 |I| [NetSync] world walk selftest: OK (532 rows, 196 mutants)",
             "2026-11-07 10:00:02 |I| [NetSync] dress rig idle frames: 3, 4",
             "2026-11-07 10:00:02 |I| [NetSync] pairing save + title selftest: OK (12 rows)"]
S168_LINES = ["x [NetSync] seat bracket selftest: OK (19 rows, 7 mutants caught)",
              "x [NetSync] guest menu selftest: OK (420 rows, 249 mutants caught)"]


def _s168_block(ww=(534, 198)):
    lines = [ln.replace("532 rows, 196 mutants", f"{ww[0]} rows, {ww[1]} mutants") for ln in PROOF_LOG] + S168_LINES
    return G.proof_block(lines)


def test_the_proof_block_reads_the_heads_and_keeps_the_last_line():
    b = G.proof_block(PROOF_LOG + ["[NetSync] overlay text selftest: OK (59 rows)"])
    assert b["main menu refusal selftest"] == "OK (14 rows)" and b["overlay text selftest"] == "OK (59 rows)"
    assert b["pairing save + title selftest"] == "OK (12 rows)" and "dress rig idle frames" not in str(b)
    assert len(b) == 6


def test_the_proof_diff_lets_only_the_rounds_movers_move(tmp_path):
    ref = G.proof_block(PROOF_LOG)
    want = ((534, 198), (19, 7), (420, 249))
    new = G.movers("new", *want)
    assert G.proof_diff(ref, _s168_block(), new)[0]
    # NEW's movers off their wants: red, each named
    ok, lines = G.proof_diff(ref, _s168_block((532, 196)), new)
    assert not ok and any("world walk selftest" in ln and ln.startswith("RED") for ln in lines)
    gm_gone = {k: v for k, v in _s168_block().items() if k != "guest menu selftest"}
    assert not G.proof_diff(ref, gm_gone, new)[0]
    # a MUST-EQUAL line moved (GM0-BRACKET's containment line, MenuRefusalSelfTest's 14): red
    for head, tail in (("diorama containment selftest", "OK (r9[scope=ok] party[refs=BAD untouched=ok])"),
                       ("main menu refusal selftest", "OK (15 rows)"), ("diorama seat selftest", None)):
        got = dict(_s168_block())
        if tail is None:
            got.pop(head)
        else:
            got[head] = tail
        ok, lines = G.proof_diff(ref, got, new)
        assert not ok and any(head in ln and ln.startswith("RED") for ln in lines), (head, lines)
    # any other line moving is a NOTE, never a red; a FAIL anywhere is red
    got = dict(_s168_block(), **{"overlay text selftest": "OK (59 rows)", "brand new selftest": "OK (1 rows)"})
    ok, lines = G.proof_diff(ref, got, new)
    assert ok and any(ln.startswith("NOTE overlay text selftest") for ln in lines) and any("brand new" in ln for ln in lines)
    assert not G.proof_diff(ref, dict(_s168_block(), **{"overlay text selftest": "FAIL (row 3)"}), new)[0]
    # no reference: the must-equal lines cannot be compared (red); an empty block is red
    ok, lines = G.proof_diff(None, _s168_block(), new)
    assert not ok and any("NO REFERENCE" in ln for ln in lines)
    assert not G.proof_diff(ref, {}, new)[0]
    # BRACKET (the W1a/b pin): the seat bracket line alone moves; s167's world walk line and no guest menu line
    br = G.movers("bracket", None, (19, 7), None)
    assert set(br) == {"seat bracket selftest"}
    pin = G.proof_block(PROOF_LOG + S168_LINES[:1])
    assert G.proof_diff(ref, pin, br)[0] and not G.proof_diff(ref, G.proof_block(PROOF_LOG), br)[0]
    with pytest.raises(ValueError):
        G.movers("nope", *want)
    assert G.movers("old") == {}
    # the saved form round-trips; the CLI judges two saved blocks
    a, b = tmp_path / "ref.txt", tmp_path / "got.txt"
    G.write_block(ref, a)
    G.write_block(pin, b)
    assert G.read_block(a) == ref and G.read_block(tmp_path / "none.txt") is None


def test_the_newest_log_is_this_legs_and_the_clone_moved_on(tmp_path):
    game = tmp_path / "FF9"
    (game / "x64").mkdir(parents=True)
    (game / "Memoria.log").write_text("old", encoding="utf-8")
    os.utime(game / "Memoria.log", (1000, 1000))
    (game / "x64" / "Memoria.log").write_text("\n".join(PROOF_LOG), encoding="utf-8")
    os.utime(game / "x64" / "Memoria.log", (2000, 2000))
    assert G.newest_log(game, 1500) == game / "x64" / "Memoria.log" and G.newest_log(game, 2500) is None
    out = tmp_path / "p.txt"
    assert G.main(["proofs", str(game), "1500", str(out)]) == 0 and G.read_block(out) == G.proof_block(PROOF_LOG)
    assert G.main(["proofs", str(game), "2500", str(out)]) == 1 and G.read_block(out) == {}
    # THE CLONE MOVED ON: FF9_S167_CLONE naming a source with the s168 tag is named; an s167-only source is not; unset is not
    clone = tmp_path / "clone" / "Memoria" / "Netsync"
    clone.mkdir(parents=True)
    (clone / "NetSyncWorldWalk.cs").write_text("// [ff9mapkit netsync s167]\n// [ff9mapkit netsync s168]\n", encoding="utf-8")
    assert G.s167_clone_is_s168({"FF9_S167_CLONE": str(tmp_path / "clone")})
    (clone / "NetSyncWorldWalk.cs").write_text("// [ff9mapkit netsync s167]\n", encoding="utf-8")
    assert G.s167_clone_is_s168({"FF9_S167_CLONE": str(tmp_path / "clone")}) is None
    assert G.s167_clone_is_s168({}) is None


def test_the_guards_cli_resolves_this_checkout_its_sources_and_the_tape(tmp_path):
    """The guard runs from the lib's cwd but resolves THIS checkout (studies/field-coop/s168 -> the root): `sources` names the s167
    source's tallies (the s167 patch's post-image) and refuses a FF9_S167_CLONE carrying the s168 tag; `tape` prints the b3 tape
    COOP_TAPE_GUEST_MENU names, and nothing when it names none that exists."""
    assert G.WT == REPO and (G.WT / "tools" / "harness" / "fakegame.py").is_file()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("COOP_", "FF9_S16"))}
    guard = str(RUNNERS / "round_gm_guard.py")
    run = lambda *a, **e: subprocess.run([sys.executable, "-X", "utf8", guard, *a], cwd=str(tmp_path), env=dict(env, **e),
                                         capture_output=True, text=True, timeout=180)
    out = run("sources")
    assert out.returncode == 0, out.stdout + out.stderr
    if any(p.name.startswith("s167-") for p in (REPO / "memoria-patches").glob("*.patch")):
        assert "the s167 world walk source's tallies: (532, 196)" in out.stdout, out.stdout
    clone = tmp_path / "clone" / "Memoria" / "Netsync"
    clone.mkdir(parents=True)
    (clone / "NetSyncWorldWalk.cs").write_text("// [ff9mapkit netsync s167]\n// [ff9mapkit netsync s168]\n", encoding="utf-8")
    moved = run("sources", FF9_S167_CLONE=str(tmp_path / "clone"))
    assert moved.returncode == 1 and "FF9_S167_CLONE names an s168 source" in moved.stdout, moved.stdout + moved.stderr
    tape = tmp_path / "x-guest-menu-1.f9tape"
    tape.write_bytes(b"F9TP")
    got = run("tape", COOP_TAPE_GUEST_MENU=str(tape))
    assert got.returncode == 0 and got.stdout.strip() == str(tape.resolve()), got.stdout + got.stderr
    none = run("tape", COOP_TAPE_GUEST_MENU=str(tmp_path / "missing.f9tape"))
    assert none.returncode == 0 and none.stdout.strip() == "", none.stdout


# ================================================================================================ the stage ladder (decision 32's re-keys)
def test_the_stage_ladder_reads_s168_and_coop_cut_hold_predicts_it_as_s131(tables):
    """_coop_peer_bench.STAGE_KEYS gains (168, netsync.guestmenu) FIRST (the newest key wins, a null value still a key); every comparison
    coop_cut_hold makes is `>=` a lower stage or `==` s119, so an s168 guest's predictions equal an s131 one's for every leg and tail at a
    GIVEN over-verdict -- but the over-verdict itself moves: span_why's s145 law fires on s168 (a world-victory span wants host_world; an
    s131 guest stall_cap) -- its s121 leg UNCHANGED (GM0-CAPS-c, the fallback row: a capless v14 peer, the press refused as s121)."""
    assert tables["stage_keys"][0] == [168, "netsync.guestmenu"]
    assert [s for s, _k in tables["stage_keys"]] == sorted((s for s, _k in tables["stage_keys"]), reverse=True)
    assert tables["stages"] == [168, 131, 168, 0]
    assert tables["span"] == ["host_world", "stall_cap"]                  # span_why's s145 law: reached by s168, not by an s131 guest
    bad = {k: v for k, v in tables["pred"].items() if not v[0]}
    assert not bad, bad
    assert tables["s121"] == [["S121-RED"], []]
