"""RUNG 1 of the roll-stream arc -- the kit feature in-game. Two launches, chained by a state file:

    $env:ROLL1_PHASE='write';    py tools/play.py studies/roll-stream/rung1_roll.py --label rs-rung1-write
    $env:ROLL1_PHASE='continue'; py tools/play.py studies/roll-stream/rung1_roll.py --label rs-rung1-continue

Bench studies/roll-stream/bench/roll1.field.toml (30900). NOTHING is hard-coded: slot, flag and vector indices
come from a dry compile of the bench, every expected value from content/rollstream.py (the oracle the build
report prints) -- so a green check means the GAME produced the predicted number.

WRITE     NC1 the first entry's autosave has no stream yet; A0 the seed states; W1 the seeded walker's first
          five targets == the prediction (the control's recorded); A1 16 ephemeral draws == PE[1..16] (value
          AND roll); A2 no extra draw; A8 a second consumer takes the shared stream's NEXT state; A1p 8
          persistent draws == PP[1..8]; A3 ~Reload: epoch 0 (Main_Init ran), E back to x0, P held at PP[8],
          the walker replays PW[1..5], NC2 the control does NOT, 16 draws replay PE[1..16]; A4 PP[9]; A5a the
          autosave holds P = PP[8]; A5b re-entry, 4 DOOMED draws recorded, quit
CONTINUE  B0 the sandbox is the one WRITE left; B1 Continue: P == PP[9] (the save), E == x0 (NC5 -- the save
          held PE[16]); A5 4 draws == the doomed ones (a reload cannot re-roll); B2 PE[1..3] + PW[1..5] in a
          new process; A7 every recorded sequence equals a = 236 and mismatches a = 237 / 235 / seed 2
"""
from __future__ import annotations

import json
import os
import random
import shutil
import sys
import time
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "studies" / "persistent-tables"))
sys.path.insert(0, str(REPO / "ff9mapkit"))
import rung0_persist as R0  # noqa: E402  (the calibrated helpers: _hud, sentinel, _sandbox, nonce, Continue)
from ff9mapkit import save as _save  # noqa: E402
from ff9mapkit.content import behavior as B  # noqa: E402
from ff9mapkit.content import behaviortoml as BT  # noqa: E402
from ff9mapkit.content import rollstream as RS  # noqa: E402

FIELD = 30900
BENCH = HERE / "bench" / "roll1.field.toml"
STATE_FILE = REPO / ".harness-runs" / "rung1-roll-state.json"
PHASE = os.environ.get("ROLL1_PHASE", "").strip().lower()

_RAW = tomllib.loads(BENCH.read_text(encoding="utf-8"))
_FB, _CB = BT.dry_compile(_RAW)
FLAG = {f: _FB.bb.flag(f) for f in ("draw_e", "draw_d", "draw_p", "bump", "walk")}
SLOT = {(u, a): int(_FB._uref(u, a).split("[")[1].rstrip("]")) for u in ("walker", "control") for a in ("wtx", "wtz")}
E, P, W = _FB.streams["eph"], _FB.streams["dwix_rs1"], _FB.wander_streams["walker"]
PE = [E.x0] + RS.states(E.x0, 64)
PP = [P.x0] + RS.states(P.x0, 64)
PW = [RS.wander_target(s, 0, -1100, 300) for s in RS.states(W.x0, 10)]
CENTRE = {"walker": (0, -1100), "control": (-800, -1600)}
BOX = {"walker": 300, "control": 250}
_s = R0.sentinel
ROWS = {"E STATE": _s(5), "P STATE": _s(5), "E ROLL": _s(1), "E DIE": _s(1), "P ROLL": _s(3), "EPOCH": _s(1),
        "CHECK": _s(1)}
HEADER = "ROLL 1 30900"


def _hud(g, **kw):
    return R0._hud(g, ROWS, want_header=HEADER, **kw)


def _i16(st, u, a) -> int:
    base = SLOT[(u, a)] * 8
    v = sum(1 << i for i in range(16) if st.flag(base + i))
    return v - 0x10000 if v & 0x8000 else v


def _watch_all(g) -> None:
    g.watch(*FLAG.values(), *[SLOT[k] * 8 + i for k in SLOT for i in range(16)])


def _targets(g, want: dict, timeout: float = 25.0) -> dict:
    """The first DISTINCT non-centre targets each unit in ``want`` ({unit: n}) rolls, sampled TOGETHER from the
    watched wtx/wtz Int16s (Main_Init presets them to the box centre, so the first roll is the first change)."""
    seq = {u: [] for u in want}
    deadline = time.time() + timeout
    while time.time() < deadline and any(len(seq[u]) < n for u, n in want.items()):
        st = g.state
        for u in want:
            t = (_i16(st, u, "wtx"), _i16(st, u, "wtz"))
            if t != CENTRE[u] and (not seq[u] or seq[u][-1] != t) and len(seq[u]) < want[u]:
                seq[u].append(t)
        g.wait_frames(3)
    return seq


def _at_centres(g) -> bool:
    st = g.state
    return all((_i16(st, u, "wtx"), _i16(st, u, "wtz")) == CENTRE[u] for u in CENTRE)


def _enter(g) -> None:
    """Re-enter the bench with the wanderers parked: ``walk`` is a Global bit, so it survives a warp (and the
    save) -- lower it first, or the walker rolls before the scenario samples."""
    g.flag(FLAG["walk"], False)
    g.wait_for(lambda s: not s.flag(FLAG["walk"]), timeout=5, what="walk lowered")
    g.warp(FIELD)


def _raise(g, name: str) -> None:
    g.flag(FLAG[name], True)


def _draw(g, flag: str, row: str, prev: int) -> dict | None:
    """Raise a roll edge, wait for the drawn row to move, and return the HUD (the flag is consumed)."""
    _raise(g, flag)
    got = _hud(g, until=lambda v: v[row] != prev, timeout=10)
    g.wait_for(lambda s: not s.flag(FLAG[flag]), timeout=5, what=f"{flag} consumed")
    return got


def _preflight(g) -> None:
    g.check((E.x0, P.x0, W.x0) == (RS.seed_state("eph", 1), RS.seed_state("dwix_rs1", 1),
                                    RS.seed_state("wander:walker", 1)), "the stream start states are the oracle's")
    g.check(str(P.word) in BENCH.read_text(encoding="utf-8"), "the bench's CHECK literal is dwix_rs1's check word",
            str(P.word))
    g.check(65535 not in PE[:40] + PP[:40], "no predicted state collides with the HUD's 65535 sentinel")
    eb = (Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX") / "FF9CustomMap"
          / "StreamingAssets" / "Assets" / "Resources" / "CommonAsset" / "EventEngine" / "EventBinary" / "Field"
          / "us" / "EVT_ROLL1.eb.bytes")
    data = eb.read_bytes() if eb.is_file() else b""
    sig236 = bytes.fromhex("7dec00117e0100010013")                   # const(236) B_MULT const4(65537) B_REM
    sig237 = bytes.fromhex("7ded00117e0100010013")
    g.check(data.count(sig236) == 4 and sig237 not in data,
            "the DEPLOYED eb carries exactly 4 advances (3 rolls + the seeded wander) on the 236 generator",
            f"{data.count(sig236)} x 236, {data.count(sig237)} x 237, {eb.name}")


def phase_write(g) -> None:
    _preflight(g)
    sandbox = R0._sandbox(g)
    parked = g.run_dir / "sandbox-before"
    for p in sorted(sandbox.glob("SavedData_ww*.dat")):
        parked.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(parked / p.name))
    g.note("roll-stream rung 1 WRITE")
    g.newgame()
    _watch_all(g)

    auto = sandbox / "SavedData_ww_Memoria_Autosave.dat"
    before = auto.stat().st_mtime_ns if auto.is_file() else None
    g.warp(FIELD)
    h = _hud(g)
    g.wait_frames(30)
    v = _save.read_extra_vectors(auto) if auto.is_file() else None
    g.check(auto.is_file() and auto.stat().st_mtime_ns != before and v is not None
            and P.tid not in v and P.tid + B.PERSIST_GUARD_OFFSET not in v and E.tid not in v,
            "NC1: the first entry's autosave was written (before Main_Init) and holds no stream",
            str(sorted(v) if v is not None else v))
    g.shot("1-seeded")
    g.check(h == {"E STATE": PE[0], "P STATE": PP[0], "E ROLL": 0, "E DIE": 0, "P ROLL": 0, "EPOCH": 0,
                  "CHECK": 1}, "A0: both streams start at their predicted x0; the persistent guard is live", str(h))
    g.check(_at_centres(g), "K3: before walk, both wander targets read their box centres (slot map + sign "
                            "extension)")

    _raise(g, "walk")
    t1 = _targets(g, {"walker": 5, "control": 3})
    w1, c1 = t1["walker"], t1["control"]
    print(f"[rs-rung1] walker {w1}\n[rs-rung1] control {c1}")
    g.check(w1 == PW[:5], "W1: the SEEDED wander's first five targets are the predicted ones", f"{w1} vs {PW[:5]}")
    g.check(len(c1) == 3 and all(abs(x - CENTRE["control"][0]) <= BOX["control"]
                                 and abs(z - CENTRE["control"][1]) <= BOX["control"] for x, z in c1),
            "the STOCK control wanders in its box", str(c1))

    e_seen, prev = [], PE[0]
    for i in range(1, 17):
        h = _draw(g, "draw_e", "E STATE", prev)
        e_seen.append((h or {}).get("E STATE"))
        if not h or h["E STATE"] != PE[i] or h["E ROLL"] != PE[i] % 6:
            g.check(False, f"A1: ephemeral draw {i} == PE[{i}] (value and roll)", str(h))
            break
        prev = h["E STATE"]
    else:
        g.check(True, "A1: 16 ephemeral draws == PE[1..16], each roll == state % 6")
    g.wait_frames(45)
    h = _hud(g)
    g.check(h is not None and h["E STATE"] == PE[16], "A2: no extra draw (the edge was consumed once)", str(h))
    h = _draw(g, "draw_d", "E STATE", PE[16])
    g.check(h is not None and h["E STATE"] == PE[17] and h["E DIE"] == 1 + PE[17] % 6,
            "A8: a SECOND consumer takes the shared stream's next state (die in [1, 6])", str(h))
    prev = PP[0]
    for i in range(1, 9):
        h = _draw(g, "draw_p", "P STATE", prev)
        if not h or h["P STATE"] != PP[i] or h["P ROLL"] != 1 + PP[i] % 100:
            g.check(False, f"A1p: persistent draw {i} == PP[{i}]", str(h))
            break
        prev = h["P STATE"]
    else:
        g.check(True, "A1p: 8 persistent draws == PP[1..8], each roll == 1 + state % 100")

    _raise(g, "bump")
    _hud(g, until=lambda v: v["EPOCH"] == 1, timeout=10)
    _enter(g)                                        # ~Reload's own path: Warp(fldMapNo)
    h = _hud(g, until=lambda v: v["EPOCH"] == 0, timeout=20)
    g.shot("2-reloaded")
    g.check(h is not None and h["E STATE"] == PE[0] and h["P STATE"] == PP[8] and h["CHECK"] == 1,
            "A3: ~Reload -- Main_Init ran (epoch 0): the ephemeral stream re-seeded to x0, the PERSISTENT one "
            "held PP[8] (no re-seed, no hidden draw)", str(h))
    g.check(_at_centres(g), "K3: Main_Init re-preset both wander targets to their centres")
    _raise(g, "walk")
    t2 = _targets(g, {"walker": 5, "control": 3})
    w2, c2 = t2["walker"], t2["control"]
    g.check(w2 == PW[:5], "A3: the seeded walker replays the identical target sequence after ~Reload", str(w2))
    g.check(len(c2) == 3 and c2 != c1, "NC2: the STOCK control rolls a different sequence after ~Reload",
            f"{c1} vs {c2}")
    prev = PE[0]
    replay = []
    for i in range(1, 17):
        h = _draw(g, "draw_e", "E STATE", prev)
        replay.append((h or {}).get("E STATE"))
        prev = replay[-1]
    g.check(replay == PE[1:17], "A3: the ephemeral stream replays PE[1..16] after ~Reload", str(replay))
    h = _draw(g, "draw_p", "P STATE", PP[8])
    g.check(h is not None and h["P STATE"] == PP[9], "A4: the persistent stream continues: PP[9]", str(h))

    v = _save.read_extra_vectors(sandbox / "SavedData_ww_Memoria_Autosave.dat") or {}
    g.check(v.get(P.tid) == [PP[8]] and v.get(P.tid + B.PERSIST_GUARD_OFFSET) == [P.word]
            and v.get(E.tid) == [PE[17]],
            "A5a: the ~Reload entry's autosave (before Main_Init) holds P = PP[8] under its word and E = PE[17]",
            str({k: v.get(k) for k in (P.tid, P.tid + B.PERSIST_GUARD_OFFSET, E.tid)}))

    nonce = random.randint(1, 255)
    g.poke(R0.NONCE_BYTE, nonce)
    _enter(g)                                        # the save CONTINUE will load: P = PP[9], walk lowered
    h = _hud(g, until=lambda v: v["P STATE"] == PP[9], timeout=20)
    doomed, prev = [], PP[9]
    for _ in range(4):
        h = _draw(g, "draw_p", "P STATE", prev)
        doomed.append((h or {}).get("P STATE"))
        prev = doomed[-1]
    g.check(doomed == PP[10:14], "A5b: 4 draws after the save point (doomed: never saved)", str(doomed))
    v = _save.read_extra_vectors(sandbox / "SavedData_ww_Memoria_Autosave.dat") or {}
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "nonce": nonce, "doomed": doomed, "walker": w1, "control": c1, "e_seen": e_seen,
        "saved_p": v.get(P.tid), "saved_e": v.get(E.tid), "write_run": str(g.run_dir),
        "extra_sha": R0._sha(sandbox / "SavedData_ww_Memoria_Autosave.dat"),
        "main_sha": R0._sha(sandbox / "SavedData_ww.dat")}, indent=2), encoding="utf-8")
    g.quit()


def phase_continue(g) -> None:
    st0 = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    _preflight(g)
    sandbox = R0._sandbox(g)
    g.check(R0._sha(sandbox / "SavedData_ww_Memoria_Autosave.dat") == st0["extra_sha"]
            and R0._sha(sandbox / "SavedData_ww.dat") == st0["main_sha"],
            "B0: the sandbox save is exactly the one WRITE left")
    g.check(st0["saved_p"] == [PP[9]] and st0["saved_e"] == [PE[16]],
            "B0: it holds P = PP[9] and E = PE[16]", f"{st0['saved_p']} {st0['saved_e']}")
    g.note("roll-stream rung 1 CONTINUE")
    R0._continue_from_title(g)
    g.wait_playable(timeout=60)
    _watch_all(g)
    g.check(g.state.field_id == FIELD, "Continue landed in the bench", str(g.state.field_id))
    g.check(R0._read_nonce(g) == st0["nonce"], "the nonce came back: WRITE's save loaded")
    _watch_all(g)
    h = _hud(g)
    g.shot("3-continued")
    g.check(h is not None and h["P STATE"] == PP[9] and h["CHECK"] == 1,
            "B1: the PERSISTENT stream loaded at PP[9] (the saved state)", str(h))
    g.check(h is not None and h["E STATE"] == PE[0],
            "NC5: the EPHEMERAL stream re-seeded to x0 although the save held PE[16]", str(h))
    again, prev = [], PP[9]
    for _ in range(4):
        h = _draw(g, "draw_p", "P STATE", prev)
        again.append((h or {}).get("P STATE"))
        prev = again[-1]
    g.check(again == st0["doomed"] and again != PP[1:5],
            "A5: the 4 draws after loading equal the 4 doomed ones -- a reload cannot re-roll",
            f"{again} vs doomed {st0['doomed']}")
    e3, prev = [], PE[0]
    for _ in range(3):
        h = _draw(g, "draw_e", "E STATE", prev)
        e3.append((h or {}).get("E STATE"))
        prev = e3[-1]
    g.check(e3 == PE[1:4], "B2: a NEW PROCESS draws the same ephemeral PE[1..3]", str(e3))
    g.check(_at_centres(g), "K3: the loaded field's wander targets start at their centres (walk was saved low)")
    _raise(g, "walk")
    w3 = _targets(g, {"walker": 5})["walker"]
    g.check(w3 == PW[:5], "B2: a NEW PROCESS walks the same seeded targets", str(w3))
    # A7: the recorded sequences discriminate the generator -- the same checks against a = 237 / 235 / seed 2
    wrong = {}
    for tag, a, seed in (("a=237", 237, 1), ("a=235", 235, 1), ("seed 2", 236, 2)):
        x = RS.seed_state("eph", seed)
        alt = []
        for _ in range(16):
            x = a * x % RS.M
            alt.append(x)
        wrong[tag] = sum(p != q for p, q in zip(alt, PE[1:17]))
    g.check(all(n >= 15 for n in wrong.values()),
            "A7: the in-game sequence would MISMATCH a wrong generator or seed (16 positions each)", str(wrong))
    g.quit()


def run(g) -> None:
    if PHASE == "write":
        phase_write(g)
    elif PHASE == "continue":
        phase_continue(g)
    else:
        raise SystemExit("set ROLL1_PHASE=write|continue")
