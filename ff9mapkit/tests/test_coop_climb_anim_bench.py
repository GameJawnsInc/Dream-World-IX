"""[ff9mapkit netsync s157] THE CLIMB-ANIM BENCH's REPO HALF -- studies/test-harness/scenarios/_climb_anim_judges.py, the pure judges
the s157 solo bench (the selftest mirror) and its wire half (coop_peer serve-guest) read. Offline, no game:

  * every path a judge reads is a key s157 PUBLISHES -- Spec B's `netsync.ghostframe` block, Spec A's twin keys inside
    `netsync.dress.self`, `dress.ghost.clip` and the player block -- and the agent's s157 writers write exactly those keys
    (so a second, never-written witness set cannot come back: studies/field-coop's s157 review, logic errors 1-3);
  * the verbs and lines the bench uses are the engine's: `netsync bench ghostframe on|off`, `netsync selfdress twin
    on|off|miss`, the two s157 proof lines and coop_peer's trailer edge line;
  * each judge is green on its model and red on its calibration (a check that cannot fail is not a check), and each
    predicted-red marker is green exactly on the red it predicts;
  * the judges stay pure (no harness import, no sys.path edit: the bench and this test share them).

Expected ids come from battlewire's twin table (BW.TWIN_BY_KEY / rig_row), never a literal.
"""
from __future__ import annotations

import ast
import importlib.util
import pathlib
import re
import sys

import pytest

from ._patchstack import msr

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from harness import Session                                        # noqa: E402
from harness import battlewire as BW                               # noqa: E402
from harness import coop_peer as CP                                # noqa: E402
from harness import fakegame as FG                                 # noqa: E402

_JPATH = REPO / "studies" / "test-harness" / "scenarios" / "_climb_anim_judges.py"
_spec = importlib.util.spec_from_file_location("climb_anim_judges", _JPATH)
J = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(J)

STN = 3                                                            # the Steiner rig (BW.RIGS row 3)
LEN = 1.1                                                          # a clip length (s) for the models
GEO = "GEO_MAIN_F0_STN"


def _twins(rig):
    return {v for (r, _src), v in BW.TWIN_BY_KEY.items() if r == rig}


def _alias(rig):
    row = BW.rig_row(rig)
    return {row["idle"], row["idle_alias"]}


def _s157_added(fname: str) -> list:
    names = [n for n in msr.stack() if n.startswith("s157-") and n not in msr.DEAD]
    if not names:
        pytest.fail("s157 not captured: no live memoria-patches/s157-*.patch")
    out = []
    for path, sec in msr.sections((msr.PATCHES / names[0]).read_bytes()):
        if path and path.replace("\\", "/").rsplit("/", 1)[-1] == fname:
            out += [ln[1:] for ln in sec.decode("ascii", "replace").replace("\r\n", "\n").split("\n")
                    if ln.startswith("+") and not ln.startswith("+++")]
    return out


def pub(*, frame=5, frame_n=12, follow=True, why=None, speed=0.0, shown=None, wire=None, time=None, steps=0, wraps=0,
        snaps=0, lever_off=False, anim=10539, model=98, geo="GEO_MAIN_F0_ZDN", anim_geo=None, clip="C", ghost_clip=None,
        twins=0, misses=0, twin="on", last_twin=-1, armed=False):
    """One publish, nested as the agent writes it (only the keys the judges read)."""
    wire = frame if wire is None else wire
    shown = wire if shown is None else shown
    time = shown / frame_n * LEN if time is None else time
    return {"player": {"model": model, "anim": anim, "geo": geo, "anim_geo": geo if anim_geo is None else anim_geo,
                       "clip": clip, "anim_frame": frame, "frame_n": frame_n},
            "netsync": {"ghostframe": {"lever_off": lever_off, "follow": follow, "why": why, "has_frame": True,
                                       "wire_frame": wire, "wire_frame_n": frame_n, "clip": clip, "speed": speed, "time": time,
                                       "length": LEN, "shown": shown, "target": wire, "steps": steps, "wraps": wraps,
                                       "snaps": snaps, "restores": 0},
                        "dress": {"self": {"twins": twins, "twin_misses": misses, "twin": twin, "armed": armed,
                                           "twin_last": {"src": -1, "twin": last_twin, "site": -1}},
                                  "ghost": {"clip": clip if ghost_clip is None else ghost_clip}}}}


# ================================================================================================ the wiring
def test_every_path_the_judges_read_is_a_key_s157_publishes():
    homes = {"netsync.ghostframe": set(FG.NETSYNC_GHOSTFRAME_SENTINELS),
             "netsync.dress.self": set(BW.DRESS_SELF_LIVE_SENTINELS) | {"twin_last." + k for k in BW.DRESS_TWIN_LAST_KEYS},
             "netsync.dress.ghost": set(BW.DRESS_GHOST_SENTINELS), "player": set(BW.PLAYER_DRESS_KEYS)}
    bad = []
    for path in J.READS:
        home = max((h for h in homes if path.startswith(h + ".")), key=len, default=None)
        if home is None or path[len(home) + 1:] not in homes[home]:
            bad.append(path)
    assert not bad, f"the judges read paths s157 does not publish: {bad}"
    for gone in ("anim_t", "anim_speed", "twin_remaps", "twin_missing", "frame_sampled", "frame_freerun"):
        assert not any(p.endswith("." + gone) for p in J.READS), gone       # the review's never-written witnesses


def test_the_agents_s157_writers_write_the_keys_the_judges_read():
    """AppendGhostFrame writes every ghostframe key through a NetSyncClient.HarnessGhostFrame* getter, in the stand-in's
    order; AppendDressTwin writes the twin keys the judges read off NetSyncSelfDress."""
    ha = _s157_added("HarnessAgent.cs")
    gf = [m.group(1) for t in ha for m in [re.search(r'(?:Bool|Num|Str)\(sb, "(\w+)", Try\(\(\) => (?:\(Int64\))?'
                                                     r'Memoria\.Netsync\.NetSyncClient\.HarnessGhostFrame\w+', t)] if m]
    assert gf == list(FG.NETSYNC_GHOSTFRAME_SENTINELS)
    twin = " ".join(ha[next(i for i, t in enumerate(ha) if "private static void AppendDressTwin(StringBuilder sb)" in t):])
    keys = re.findall(r'(?:Num|Str)\(sb, "(\w+)", Try\(\(\) => (?:\(Int64\))?Memoria\.Netsync\.NetSyncSelfDress\.\w+', twin)
    assert {"twins", "twin_misses", "twin", "src"} <= set(keys) and '"\\"twin_last\\":{"' in twin


def test_the_benchs_verbs_and_lines_are_the_engines():
    assert Session.NETSYNC_BENCH_OPS["ghostframe"][:3] == ("coop_ghost_frame", "netsync.ghostframe", "s157")
    assert "twin" in Session.NETSYNC_SELFDRESS_OPS and Session.NETSYNC_SELFDRESS_OPS[-1] == "twin"
    client = "\n".join(_s157_added("NetSyncClient.cs"))
    for head in ("[NetSync] dress twin selftest: ", "[NetSync] ghost frame selftest: "):   # never 'climb anim selftest'
        assert f'Log.Message("{head}"' in client, head
    assert FG.PROOF_GHOST_FRAME in client and BW.PROOF_DRESS_TWIN in client
    agent = "\n".join(_s157_added("HarnessAgent.cs"))
    assert 'if (bnop == "ghostframe")' in agent and '"expected `netsync bench ghostframe on|off`"' in agent
    assert CP.HOST_TRAILER_LINE.format(n=CP.POS_FRAME_LEN, f=5, fn=12) == "host type-0: 39 B -- the s157 frame bytes (frame 5 of 12)"


def test_the_judges_are_pure():
    tree = ast.parse(_JPATH.read_text(encoding="utf-8"))
    mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    mods |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert mods <= {"__future__", "math"}, mods                  # no sys, no harness: nothing to edit sys.path with


# ================================================================================================ the ghost frame
def _hold(n=10, **kw):
    return [pub(**kw) for _ in range(n)]


def test_the_hold_judge_is_green_on_a_held_ghost_and_red_on_each_defect():
    assert J.judge_hold(_hold())[0]
    assert J.judge_hold(_hold(wire=4), wire_tol=1)[0] and not J.judge_hold(_hold(wire=4))[0]   # the peer's echo tick
    reds = {
        "free-runs (s156)": [pub(follow=False, why="lever", speed=1.0, time=0.1 * k) for k in range(10)],
        "body moved": [pub(frame=k % 12) for k in range(10)],
        "shown off the wire": _hold(shown=4.0),
        "time off its frame": _hold(time=0.9),
        "frozen but not following": _hold(follow=False, why="clip"),
        "too few": _hold(n=3),
    }
    for name, rows in reds.items():
        assert not J.judge_hold(rows)[0], name


def test_the_frame_red_marker_is_green_only_on_the_free_running_ghost():
    lever = [pub(follow=False, why="lever", lever_off=True, speed=1.0, time=0.033 * k) for k in range(10)]
    assert J.frame_red_marker(lever, why="lever", lever=True)[0]
    assert not J.frame_red_marker(lever, why="no_frame")[0]                                   # the wrong reason
    wrapped = [pub(follow=False, why="no_frame", speed=1.0, time=(0.3 * k) % LEN) for k in range(10)]
    assert J.frame_red_marker(wrapped, why="no_frame")[0]
    assert not J.frame_red_marker(_hold(), why="lever")[0]                                    # a held ghost is no red
    stuck = [pub(follow=False, why="lever", lever_off=True, speed=1.0, time=0.2) for _ in range(10)]
    assert not J.frame_red_marker(stuck, why="lever", lever=True)[0]                          # the clock never moved
    assert not J.frame_red_marker([pub(frame=k, follow=False, why="lever", lever_off=True, speed=1.0, time=0.1 * k)
                                   for k in range(10)], why="lever", lever=True)[0]           # the body moved


def test_the_track_judge_wants_a_driven_ghost_that_steps():
    climb = [pub(frame=k % 12, wire=k % 12, shown=float((k - 1) % 12), steps=k, wraps=k // 12, snaps=1) for k in range(30)]
    assert J.judge_track(climb, min_wraps=1)[0]
    assert not J.judge_track([dict(p, netsync=dict(p["netsync"], ghostframe=dict(p["netsync"]["ghostframe"], speed=1.0,
                                                                                    follow=False))) for p in climb])[0]
    assert not J.judge_track([pub(frame=k % 12, steps=0) for k in range(30)])[0]              # steps never moved
    assert not J.judge_track(climb, min_wraps=5)[0]
    far = [pub(frame=k % 12, wire=k % 12, shown=float((k + 6) % 12), steps=k) for k in range(30)]
    assert not J.judge_track(far)[0]                                                          # half a loop behind


def test_the_guard_judge_is_red_on_a_frozen_ghost():
    assert J.judge_freerun_guard(_hold(follow=False, why="frame_n", speed=1.0), why="frame_n")[0]
    assert not J.judge_freerun_guard(_hold(follow=False, why="frame_n", speed=0.0), why="frame_n")[0]   # frozen: no restore
    assert not J.judge_freerun_guard(_hold(follow=False, why="loco", speed=1.0), why="frame_n")[0]


def test_the_pinned_and_seam_judges():
    pinned = _hold(frame=0, wire=5)
    assert J.judge_pinned(pinned, 5, 12, clip="C")[0]
    assert not J.judge_pinned(pinned, 6, 12)[0] and not J.judge_pinned(pinned, 5, 12, clip="other")[0]
    assert not J.judge_pinned(_hold(frame=0, wire=5, speed=1.0), 5, 12)[0]
    up = [pub(wire=k % 12, time=(k % 12) / 12 * LEN, steps=k, wraps=k // 12) for k in range(60)]
    assert J.judge_seam(up, direction=+1, min_wraps=4, min_steps=40)[0]
    assert not J.judge_seam(up, direction=-1, min_wraps=4, min_steps=40)[0]                  # time ran the other way
    assert not J.judge_seam(up, direction=+1, min_wraps=6, min_steps=40)[0]
    down = [pub(wire=(-k) % 12, time=((-k) % 12) / 12 * LEN, steps=k, wraps=k // 12, snaps=0) for k in range(60)]
    assert J.judge_seam(down, direction=-1, min_wraps=4, min_steps=40)[0]
    # THE READ-GAP RULE (the s157 review's K3): a 7-publish read stall (the wire moved 8 of 12 frames between two reads) is
    # SKIPPED, never scored as a backward step -- scored, that very pair folds to -4 frames (the alias the rule guards against)
    stalled = up[:20] + up[27:]
    assert J._wrap(J._gf(up[27], "time") - J._gf(up[19], "time"), LEN) < -J.TIME_EPS
    ok, why = J.judge_seam(stalled, direction=+1, min_wraps=4, min_steps=40)
    assert ok and "1 skipped" in why, why
    assert not J.judge_seam(stalled, direction=-1, min_wraps=4, min_steps=40)[0]              # still red the wrong way
    # a run starved of judgeable pairs (every read 3 wire frames apart: 4 x 3 >= 12) is red as UNJUDGEABLE, never green
    ok, why = J.judge_seam(up[::3], direction=+1, min_wraps=4, min_steps=40)
    assert not ok and "UNJUDGEABLE" in why, why
    # a snap between two reads is skipped too (its jump says nothing about the direction)
    snapped = [dict(p) for p in up]
    for k in range(30, 60):
        snapped[k] = pub(wire=k % 12, time=(k % 12) / 12 * LEN, steps=k, wraps=k // 12, snaps=1)
    assert J.judge_seam(snapped, direction=+1, min_wraps=4, min_steps=40)[0]


# ================================================================================================ the twin rows
def _dressed(anim, n=8, **kw):
    return [pub(anim=anim, model=5489, geo=GEO, **kw) for _ in range(n)]


def test_the_twin_judge_is_table_driven_and_red_on_the_pencil():
    twin = BW.TWIN_BY_KEY[(STN, 10539)]                     # Zidane's LADDER_1_2 on the Steiner rig
    rows = _dressed(twin, last_twin=twin)
    kw = dict(twin_ids=_twins(STN), alias_ids=_alias(STN))
    assert J.judge_twin(rows, d_twins=3, d_misses=0, **kw)[0]
    assert J.judge_twin(rows, d_twins=3, d_misses=0, follow_share=0.8, **kw)[0]
    alias = BW.rig_row(STN)["idle_alias"]
    pencil = _dressed(alias, twin="off")
    reds = {"the pencil": (pencil, 0, 0), "no twin counted": (rows, 0, 0), "a clip missing": (rows, 3, 1),
            "Zidane's GEO clip": ([dict(p, player=dict(p["player"], anim_geo="GEO_MAIN_F0_ZDN")) for p in rows], 3, 0),
            "the ghost elsewhere": ([dict(p, netsync=dict(p["netsync"], dress=dict(p["netsync"]["dress"], ghost={"clip": "X"})))
                                     for p in rows], 3, 0)}
    for name, (rr, dt, dm) in reds.items():
        assert not J.judge_twin(rr, d_twins=dt, d_misses=dm, **kw)[0], name
    assert J.twin_red_marker(pencil, alias_ids=_alias(STN), mode="off", d_twins=0, d_misses=0)[0]
    assert not J.twin_red_marker(rows, alias_ids=_alias(STN), mode="off", d_twins=0, d_misses=0)[0]
    missing = _dressed(alias, twin="miss")
    assert J.twin_red_marker(missing, alias_ids=_alias(STN), mode="miss", d_twins=0, d_misses=2)[0]
    assert not J.twin_red_marker(missing, alias_ids=_alias(STN), mode="miss", d_twins=0, d_misses=0)[0]
    s156 = [dict(p, netsync=dict(p["netsync"], dress={"ghost": {"clip": "C"}, "self": {"armed": True}})) for p in pencil]
    assert J.twin_red_marker(s156, alias_ids=_alias(STN), mode="s156")[0]
    assert not J.twin_red_marker(pencil, alias_ids=_alias(STN), mode="s156")[0]           # the key is published: not s156


def test_the_undressed_control():
    vivi = BW.rig_row(1)["model"]
    rows = [pub(model=vivi, geo="GEO_MAIN_F0_VIV") for _ in range(6)]
    assert J.judge_undressed(rows, model=vivi, d_twins=0, d_misses=0)[0]
    assert J.judge_undressed(rows, model=vivi, d_twins=None, d_misses=None)[0]              # the s156 DLL: no twin key
    assert not J.judge_undressed(rows, model=vivi, d_twins=1, d_misses=0)[0]
    assert not J.judge_undressed(rows, model=vivi, d_twins=0, d_misses=1)[0]
    assert not J.judge_undressed([pub(model=5489, geo=GEO)], model=vivi, d_twins=0, d_misses=0)[0]   # a dressed body
    assert not J.judge_undressed([pub(model=vivi, geo="GEO_MAIN_F0_VIV", armed=True)], model=vivi, d_twins=0, d_misses=0)[0]


def test_the_sender_judge_reads_coop_peers_own_edge_lines():
    on = "12:00:01 " + CP.HOST_TRAILER_LINE.format(n=39, f=0, fn=0)
    assert J.judge_sender(["host pos: field 207 (was none)", on])[0]
    assert not J.judge_sender(["host pos: field 207 (was none)"])[0]                         # an s156 host: no edge
    assert not J.judge_sender([on, "12:00:02 " + CP.HOST_NO_TRAILER_LINE.format(n=37)])[0]
