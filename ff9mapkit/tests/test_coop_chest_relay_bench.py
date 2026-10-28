"""[ff9mapkit netsync s160] THE CHEST RELAY BENCH's REPO HALF -- studies/test-harness/scenarios/coop_chest_relay.py.

The bench judges s160's guest half by `netsync.chest`'s counters, the player's control / face / position / clip, the dialog and the
watched opened flag, over every publish after a fabricated section-9 start. These tests pin, offline, with fixtures in the ENGINE's
types:

  * its catalog: each calibration's predicted reds sit in it, K-CAL appears only under COOP_CALIBRATE, and the two levers predict
    DIFFERENT rows (request off keeps C2 green: the in-range body is the stock range request's);
  * the face byte the chest's TimedTurn lands on (the research recipe: about 198 from the field-200 spawn);
  * every pure judge CAN go red: an open with no serve, no accept, two accepts, no control drop, no turn, a move, no flag, no window, a
    window without the item, a missing "already queued" line in range; a close with no control back, no stand clip, or the face lost;
    a nothing-opens leg that opened, counted wrong, or moved the flag;
  * the proof-line verdict needs the line AND the published "ok".

Every scenario-touching test runs in a CHILD process (the scenario puts its own dir on sys.path -- never this process's).
"""
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
SCEN = REPO / "studies" / "test-harness" / "scenarios"


def _child(code: str, env_cal: str = "") -> dict:
    full = ("import json, sys, os\nsys.path.insert(0, %r)\nsys.path.insert(0, %r)\nimport coop_chest_relay as cr\n" % (str(SCEN), str(REPO / "tools"))
            + code + "\nprint('@@' + json.dumps(OUT))\n")
    env = dict(__import__("os").environ)
    env.pop("COOP_CALIBRATE", None)
    if env_cal:
        env["COOP_CALIBRATE"] = env_cal
    r = subprocess.run([sys.executable, "-X", "utf8", "-c", full], capture_output=True, text=True, cwd=str(SCEN), timeout=120, env=env)
    assert r.returncode == 0, r.stderr[-3000:]
    line = next(ln for ln in r.stdout.splitlines() if ln.startswith("@@"))
    return json.loads(line[2:])


_FIX = r'''
def st(control=True, face=0, x=-90.0, z=171.0, anim=200, opened=False, flag=False, text="", acc=0, srv=0, exp=0, dec=0, selftest=None):
    return {"player": {"control": control, "face": face, "x": x, "y": 0.0, "z": z, "anim": anim},
            "dialog": {"open": opened, "texts": [text] if text else []},
            "flags": {"7244": flag, "2471": True},
            "netsync": {"chest": {"accepted": acc, "served": srv, "expired": exp, "declined": dec, "selftest": selftest}}}
B0 = cr.counters(st())
def good_open():
    return [st(control=False, face=120, acc=1), st(control=False, face=198, acc=1, srv=1),
            st(control=False, face=198, acc=1, srv=1, flag=True), st(control=False, face=198, acc=1, srv=1, flag=True, opened=True,
            text="Received Leather Hat!")]
'''


def test_catalog_and_predictions():
    out = _child("OUT = {'plain': sorted(cr.catalog(None)), 'serve': sorted(cr.catalog('serve')), 'pred': {k: list(v) for k, v in cr.PREDICTED.items()}}")
    assert "K-CAL" not in out["plain"] and "K-CAL" in out["serve"]
    for mode, rows in out["pred"].items():
        assert set(rows) <= set(out["plain"]), mode
    assert "C2" in out["pred"]["serve"] and "C2" not in out["pred"]["request"]
    assert set(out["pred"]["request"]) < set(out["pred"]["serve"])


def test_calibrate_env_modes():
    assert _child("OUT = cr.CAL_MODE", env_cal="request") == "request"
    assert _child("OUT = cr.CAL_MODE", env_cal="1") == "serve"
    assert _child("OUT = cr.CAL_MODE") is None


def test_face_toward_the_chest():
    out = _child("OUT = [cr.face_toward(cr.SPAWN, cr.CHEST_XZ), cr.face_diff(250, 4), cr.face_diff(10, 10)]")
    assert out[0] in (197, 198, 199)
    assert out[1] == 10 and out[2] == 0


def test_judge_open_green_and_each_red():
    code = _FIX + r'''
S0 = (-90.0, 0.0, 171.0)
def j(samples, queued=False, lines=()):
    return cr.judge_open(samples, B0, start_xz=S0, want_face=198, queued=queued, lines=list(lines))[0]
g = good_open()
OUT = {
  "green": j(g),
  "no_serve": j([dict(s, netsync={"chest": dict(s["netsync"]["chest"], served=0)}) for s in g]),
  "two_accepts": j(g[:-1] + [st(control=False, face=198, acc=2, srv=1, flag=True, opened=True, text="Received Leather Hat!")]),
  "no_ctl_drop": j([dict(s, player=dict(s["player"], control=True)) for s in g]),
  "no_turn": j([dict(s, player=dict(s["player"], face=120)) for s in g]),
  "moved": j(g[:-1] + [dict(g[-1], player=dict(g[-1]["player"], x=-80.0))]),
  "no_flag": j([dict(s, flags={"7244": False}) for s in g]),
  "no_window": j(g[:-1]),
  "wrong_item": j(g[:-1] + [st(control=False, face=198, acc=1, srv=1, flag=True, opened=True, text="Received Potion!")]),
  "queued_missing": j(g, queued=True, lines=["[NetSync] chest relay: opening chest 9 ... -- tag 2 requested"]),
  "queued_present": j(g, queued=True, lines=["... -- its body is already queued by the stock range request (I stand in push range)"]),
}
'''
    out = _child(code)
    assert out.pop("green") is True and out.pop("queued_present") is True
    reds = {k: v for k, v in out.items() if v is not False}
    assert not reds, reds


def test_judge_close_and_nothing_opens():
    code = _FIX + r'''
back = [st(control=False, face=198, opened=True, anim=2605), st(control=False, face=198, anim=2590), st(control=True, face=198, anim=200)]
OUT = {
  "close_green": cr.judge_close(back, want_face=198)[0],
  "close_never": cr.judge_close(back[:2], want_face=198)[0],
  "close_no_stand": cr.judge_close([dict(s, player=dict(s["player"], anim=2605)) for s in back], want_face=198)[0],
  "close_face_lost": cr.judge_close(back[:2] + [st(control=True, face=60, anim=200)], want_face=198)[0],
  "none_green": cr.judge_nothing_opens([st(acc=1), st(acc=1, exp=1)], B0, want={"accepted": 1, "expired": 1}, flag_was=False)[0],
  "none_opened": cr.judge_nothing_opens([st(acc=1, opened=True), st(acc=1, exp=1)], B0, want={"accepted": 1, "expired": 1}, flag_was=False)[0],
  "none_count": cr.judge_nothing_opens([st(acc=1)], B0, want={"accepted": 1, "expired": 1}, flag_was=False)[0],
  "none_flag": cr.judge_nothing_opens([st(acc=1, exp=1, flag=True)], B0, want={"accepted": 1, "expired": 1}, flag_was=False)[0],
}
'''
    out = _child(code)
    assert out.pop("close_green") is True and out.pop("none_green") is True
    reds = {k: v for k, v in out.items() if v is not False}
    assert not reds, reds


def test_selftest_verdict_needs_line_and_publish():
    code = _FIX + r'''
L = ["2026 | [NetSync] chest relay selftest: OK (37 rows, 6 mutants caught)"]
OUT = {
  "green": cr.selftest_verdict(L, st(selftest="ok"))[0],
  "no_publish": cr.selftest_verdict(L, st(selftest=None))[0],
  "fail_publish": cr.selftest_verdict(L, st(selftest="fail: row 3"))[0],
  "no_line": cr.selftest_verdict([], st(selftest="ok"))[0],
  "fail_line": cr.selftest_verdict(["[NetSync] chest relay selftest: FAIL (row 3: x)"], st(selftest="ok"))[0],
}
'''
    out = _child(code)
    assert out.pop("green") is True
    reds = {k: v for k, v in out.items() if v is not False}
    assert not reds, reds
