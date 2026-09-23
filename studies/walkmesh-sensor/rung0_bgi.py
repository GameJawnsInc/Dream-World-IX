"""RUNG 0 of the walkmesh-sensor arc (the .eb uses board's #2) -- B_BGIID / B_BGIFLOOR read back in-game.

    py tools/play.py studies/walkmesh-sensor/rung0_bgi.py --label bgi-rung0

Bench studies/walkmesh-sensor/bench/bgi0.field.toml (30910): two floors split at x = 0, 16 triangles (floor 0 =
0..7, floor 1 = 8..15), a HUD strip whose rows read B_BGIID / B_BGIFLOOR for the player (B_PTR(250)), the rover
unit (uid 2), the static statue (uid 3), and two negative controls (raw 250, and uid 0 -- the board's own line).

THE ORACLE is the kit's BgiWalkmesh point-in-triangle over the DEPLOYED .bgi, evaluated at the actor's TRUE
position: the player's settled published x/z (live -- FieldMapActorController.HonoLateUpdate copies curPos every
frame) and the rover's .eb position mirrors (Global.Int16 obj(uid).f[0]/f[2], written by the ticker). NEVER the
harness's state.player.tri/floor: those are PosObj fields whose only writer is the battle backup
(EventEngine.cs:1441) -- 0/0 before any battle, frozen after one. A point within 3u of a triangle edge is not
scored (the engine keeps its PREVIOUS triangle there, FieldMapActorController.cs:1374-1385 -- history, not
geometry).

PRE  P1 the deployed .bgi lists triangles floor by floor with floor_ndx == membership (the engine indexes
     WalkMesh.tris by triangle id); P2 the deployed .eb carries the eight HUD statements; P3 the real build seats
     rover at uid 2 and statue at uid 3
A0   first read: MAIN (const(0)) == -1 and RAWK (const(250)) == -1 -- the operand is a RAW uid; the statue reads
     its placement triangle 10 / floor 1 without ever moving; the parked rover reads 4 / 0; the player its spawn
A1   14 player stops over 13 triangles on both floors, the seam crossed both ways: every PTRI/PFLR == the oracle
     at the settled position; floor-1 stops read 8..15 (GLOBAL ids -- a per-floor index would read 0..7); the
     .eb's own player mirror agrees with the harness position (+-1u)
A2   the rover wanders (seeded; its box straddles the tri 4/5 diagonal): >= 8 dwell samples, UTRI/UFLR == the
     oracle at its mirror, both triangles seen
F1   (free rider, a look -- not a check) a shot with the three actors: do actors on a kit-built field cast a
     shadow at all? (#9's kit-wide question)
"""
from __future__ import annotations

import re
import sys
import time
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit import build as BLD  # noqa: E402
from ff9mapkit.content import behaviortoml as BT  # noqa: E402
from ff9mapkit.scene import bgi  # noqa: E402

FIELD = 30910
BENCH = HERE / "bench" / "bgi0.field.toml"
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
FBG = "FBG_N11_BGI0"
LIVE = GAME / "FF9CustomMap" / "StreamingAssets" / "Assets" / "Resources"
BGI_FILE = LIVE / "FieldMaps" / FBG / f"{FBG}.bgi.bytes"
EB_FILE = LIVE / "CommonAsset" / "EventEngine" / "EventBinary" / "Field" / "us" / "EVT_BGI0.eb.bytes"

HEADER = "BGI 0 30910"
ROWS = {"PTRI": 999, "PFLR": 99, "UTRI": 999, "UFLR": 99, "NTRI": 999, "NFLR": 99, "RAWK": 99, "MAIN": 99}
HUD_SIG = ["5ffa70", "5ffa71", "7d020070", "7d020071", "7d030070", "7d030071", "7dfa0070", "7d000070"]
UID = {"rover": 2, "statue": 3}
POS = {"rover": (-813, -1202), "statue": (1017, -108)}
MARGIN = 3.0

_RAW = tomllib.loads(BENCH.read_text(encoding="utf-8"))
_FB, _CB = BT.dry_compile(_RAW)
MIR = {k: _FB.bb.int16(k) for k in ("player.mx", "player.mz", "rover.mx", "rover.mz")}
WALK = _FB.bb.flag("walk")

M = bgi.BgiWalkmesh.from_file(BGI_FILE)
WV = M.world_verts()
FLOOR_OF = {ti: fi for fi, f in enumerate(M.floors) for ti in f.tri_ndx_list}


def _abc(ti):
    return [WV[v] for v in M.tris[ti].vtx]


def _margin(x, z, a, b, c):
    return min(bgi._pt_seg_dist_xz(x, z, p, q) for p, q in ((a, b), (b, c), (c, a)))


def oracle(x, z):
    """(tri, floor, edge margin) the engine must report at (x, z) -- None where exactly-one-hit fails."""
    hits = [ti for ti in range(len(M.tris)) if bgi._pt_in_tri_xz(x, z, *_abc(ti))]
    if len(hits) != 1:
        return None
    ti = hits[0]
    return ti, FLOOR_OF[ti], _margin(x, z, *_abc(ti))


def centroid(ti):
    a, b, c = _abc(ti)
    return (a[0] + b[0] + c[0]) / 3, (a[2] + b[2] + c[2]) / 3


# spawn(3) -> 1 -> 0 -> 2 -> 6 -> 7 -> SEAM -> 13 -> 12 -> 15 -> 14 -> 11 -> 9 -> 8 -> SEAM -> 2 -> 3: one-axis legs
# that never pass within 300u of the rover (tri 4) or the statue (tri 10), crossing x = 0 both ways
STOPS = [1, 0, 2, 6, 7, 13, 12, 15, 14, 11, 9, 8, 2, 3]


def _i16(st, byte_index) -> int:
    v = sum(1 << i for i in range(16) if st.flag(byte_index * 8 + i))
    return v - 0x10000 if v & 0x8000 else v


def _hud_of(st) -> dict | None:
    for text in st.texts:
        if HEADER not in text:
            continue
        vals = {}
        for label in ROWS:
            m = re.search(re.escape(label) + r"\s+(-?\d+)", text)
            if m:
                vals[label] = int(m.group(1))
        if len(vals) == len(ROWS) and all(vals[k] != ROWS[k] for k in ROWS):
            return vals
    return None


def _hud(g, timeout=20.0) -> dict | None:
    got = {}

    def ok(st):
        h = _hud_of(st)
        if h:
            got.update(h)
        return h is not None
    try:
        g.wait_for(ok, timeout=timeout, what="the BGI 0 HUD strip to render live values")
    except Exception as err:                             # noqa: BLE001 -- reported as a check
        print(f"[bgi-rung0] HUD not readable: {err}\n[bgi-rung0] texts: {g.state.texts!r}")
        return None
    return dict(got)


def _settled(g):
    a = g.settle()
    g.wait_frames(8)
    b = g.settle()
    still = abs(a.player_x - b.player_x) <= 0.5 and abs(a.player_z - b.player_z) <= 0.5
    return b, still


def _stable_hud(g):
    """Two HUD reads >= 10 frames apart that agree -- the ticker has published THIS position."""
    h1 = _hud(g)
    g.wait_frames(10)
    h2 = _hud(g)
    return h2 if h1 is not None and h1 == h2 else None


def _preflight(g) -> None:
    eng = [ti for f in M.floors for ti in f.tri_ndx_list]
    g.check(eng == list(range(len(M.tris))) and all(M.tris[t].floor_ndx == FLOOR_OF[t] for t in FLOOR_OF)
            and len(M.tris) == 16 and len(M.floors) == 2,
            "P1: the DEPLOYED .bgi lists 16 triangles floor by floor (0..7, 8..15) with floor_ndx == membership",
            str([f.tri_ndx_list for f in M.floors]))
    data = EB_FILE.read_bytes() if EB_FILE.is_file() else b""
    miss = [k for k, s in enumerate(HUD_SIG) if bytes.fromhex(f"6602{k:02x}{s}7f") not in data]
    g.check(not miss, "P2: the DEPLOYED .eb carries all eight B_BGIID/B_BGIFLOOR HUD statements", f"missing {miss}")
    project = BLD.FieldProject.load(BENCH)
    cap, orig = {}, BT.build

    def spy(raw, *, npc_slots, **kw):
        cap["slots"] = dict(npc_slots)
        return orig(raw, npc_slots=npc_slots, **kw)
    BT.build = spy
    try:
        BLD.build_script(project, "us", {}, behavior_txids={("hud", i): 900 + i for i, _ in BT.hud_lines(project.raw)})
    finally:
        BT.build = orig
    g.check(cap.get("slots") == UID, "P3: the real build seats rover at uid 2 and statue at uid 3", str(cap))
    for name, (x, z) in POS.items():
        o = oracle(x, z)
        g.check(o is not None and o[2] >= 100, f"P4: {name}'s placement is deep inside one triangle", str(o))


def run(g) -> None:
    _preflight(g)
    g.note("walkmesh sensor rung 0")
    g.newgame()
    g.watch(WALK, *[b * 8 + i for b in MIR.values() for i in range(16)])
    g.warp(FIELD)
    g.flag(WALK, False)

    # ---- A0: the first read -- controls, the static statue, the parked rover, the player at spawn
    st, still = _settled(g)
    h = _stable_hud(g)
    g.shot("1-spawn")
    print(f"[bgi-rung0] first read {h} at ({st.player_x:.1f},{st.player_z:.1f})")
    g.check(h is not None, "the HUD strip is readable", str(g.state.texts))
    if h is None:
        return
    g.check(h["MAIN"] == -1 and h["RAWK"] == -1,
            "A0: const(0) B_BGIID (the board's line: uid 0 is the Main entry) and const(250) B_BGIID (a RAW uid, "
            "250 untranslated) both read -1", str(h))
    o = oracle(*POS["statue"])
    g.check((h["NTRI"], h["NFLR"]) == o[:2], "A0: the STATIC statue reads its placement triangle and floor "
            "(CreateObject alone activates tracking)", f"{h['NTRI']},{h['NFLR']} vs {o}")
    o = oracle(*POS["rover"])
    g.check((h["UTRI"], h["UFLR"]) == o[:2], "A0: the parked rover reads its post's triangle and floor",
            f"{h['UTRI']},{h['UFLR']} vs {o}")
    o = oracle(st.player_x, st.player_z)
    g.check(still and o is not None and (h["PTRI"], h["PFLR"]) == o[:2],
            "A0: the player (B_PTR(250)) reads its spawn triangle and floor", f"{h} vs {o}")
    # sampled AFTER the HUD is live (the first run read `st` from before warmup finished: (0, 0), a false red)
    live = g.state
    mir0 = (_i16(live, MIR["player.mx"]), _i16(live, MIR["player.mz"]))
    g.check(abs(mir0[0] - live.player_x) <= 1.5 and abs(mir0[1] - live.player_z) <= 1.5,
            "A0: the .eb's player mirror is live and equals the harness position (the ticker is running)",
            f"{mir0} vs ({live.player_x:.1f},{live.player_z:.1f})")

    # ---- A1: the player sweep over both floors
    g.calibrate_axes()
    rows = []
    for ti in STOPS:
        cx, cz = centroid(ti)
        o = st = h = None
        for _attempt in range(3):
            try:
                g.walk_to(cx, cz, tolerance=30, strict=False)
            except Exception as err:                     # noqa: BLE001 -- a basis disagreement: recalibrate
                print(f"[bgi-rung0] walk_to {ti}: {err} -- recalibrating")
                g.calibrate_axes(recalibrate=True)
                continue
            st, still = _settled(g)
            o = oracle(st.player_x, st.player_z)
            if still and o is not None and o[2] >= MARGIN:
                break
        h = _stable_hud(g)
        st2, _ = _settled(g)
        moved = abs(st2.player_x - st.player_x) > 0.5 or abs(st2.player_z - st.player_z) > 0.5
        mir = (_i16(st2, MIR["player.mx"]), _i16(st2, MIR["player.mz"]))
        row = {"aim": ti, "pos": (round(st.player_x, 1), round(st.player_z, 1)), "oracle": o,
               "hud": None if h is None else (h["PTRI"], h["PFLR"]), "mirror": mir, "moved": moved}
        rows.append(row)
        print(f"[bgi-rung0] stop {row}")
        ok = (h is not None and o is not None and o[2] >= MARGIN and not moved
              and (h["PTRI"], h["PFLR"]) == o[:2])
        g.check(ok, f"A1: stop aimed at tri {ti}: PTRI/PFLR == the oracle at the settled position", str(row))
        g.check(abs(mir[0] - st2.player_x) <= 1.5 and abs(mir[1] - st2.player_z) <= 1.5,
                f"A1: stop {ti}: the .eb's obj(250) mirror == the harness position", f"{mir} vs "
                f"({st2.player_x:.1f},{st2.player_z:.1f})")
    scored = [r for r in rows if r["oracle"] and r["hud"] == r["oracle"][:2]]
    tris = {r["oracle"][0] for r in scored}
    g.check(len(tris) >= 10 and {r["oracle"][1] for r in scored} == {0, 1},
            "A1: coverage -- >= 10 distinct triangles read correctly, on both floors", str(sorted(tris)))
    g.check(any(r["hud"] and r["hud"][0] >= 8 for r in scored),
            "A1: the ids are GLOBAL -- floor-1 stops read 8..15, not a per-floor 0..7")
    g.shot("2-after-sweep")

    # ---- A2: the rover wanders; its HUD rows vs the oracle at its own .eb position mirror
    g.flag(WALK, True)
    samples, prev, deadline = [], None, time.time() + 40
    while time.time() < deadline and len(samples) < 20:
        g.wait_frames(12)
        st = g.state
        hh = _hud_of(st)
        cur = ((_i16(st, MIR["rover.mx"]), _i16(st, MIR["rover.mz"])), None if hh is None else (hh["UTRI"], hh["UFLR"]))
        if prev is not None and cur == prev and cur[1] is not None:
            o = oracle(*cur[0])
            if o is not None and o[2] >= MARGIN and (not samples or samples[-1]["pos"] != cur[0]):
                samples.append({"pos": cur[0], "hud": cur[1], "oracle": o[:2], "margin": round(o[2], 1)})
        prev = cur
    g.flag(WALK, False)
    print(f"[bgi-rung0] rover samples {samples}")
    bad = [s for s in samples if s["hud"] != s["oracle"]]
    g.check(len(samples) >= 8 and not bad, "A2: every rover dwell sample: UTRI/UFLR == the oracle at its .eb "
            "position mirror", f"{len(samples)} samples, mismatches {bad}")
    g.check({s["oracle"][0] for s in samples} >= {4, 5}, "A2: the rover was read on BOTH sides of the 4/5 diagonal",
            str(sorted({s['oracle'][0] for s in samples})))
    g.shot("3-rover")
    g.quit()
