"""RUNG 1 of the walkmesh-sensor arc -- the FLOOR VERBS in-game (on_floor / same_floor / other_floor, floor:<who>).

    py tools/play.py studies/walkmesh-sensor/rung1_floor.py --label bgi-rung1

Two benches, one launch (studies/walkmesh-sensor/bench/): bgi1.field.toml (30911, v1 ticker, floor NAMES) and
bgi1b.field.toml (30912, brains + a CLASS, int floors). Both walk a two-floor mesh (ground = 0 west, terrace = 1
east) seamed ONLY on the south half of x = 0 -- the north half is a wall: THE FLOOR LAW's lip. The OBJ reopens
`ground` after `terrace`, so the builder's floor-major REGROUP must restore rung 0's exact numbering.

Every index comes from a dry compile WITH the real floor table; every expectation from the DEPLOYED .bgi (the
kit's BgiWalkmesh point-in-triangle at the actor's TRUE position -- the settled published player x/z, a unit's
.eb position mirror). NEVER the harness's state.player.tri/floor (the battle backup: dead in the field).

PRE  P0 each id is served by exactly one mod folder; P1 NC-REGROUP: the deployed .bgi is floor-major with
     floors [[0..7],[8..15]] and equals resolve_walkmesh(project); the bench OBJ really is interleaved
     (regrouped); the regrouped mesh equals rung 0's in-game-proven BGI0 in vertices, triangles and floors and
     differs ONLY in its seam links (one change per in-game test: only the lip and the verbs are new in-game);
     P2 the deployed .eb reads the floor only in its ticker (player B_PTR(250), units const(uid)) plus the HUD's
     live rows; P3 the real uids; P4 every post lies deep inside one triangle
A0   boot: player mirror == HUD PFLR == the live expr PLIV == the oracle; every unit mirror == its post's floor;
     NC-UNKNOWN: the dormant pooled ghost reads -1 and the lamp's on_floor(ghost) never fires
A1   the player sweep over both floors, the seam crossed both ways: at every settled stop the mirror == the live
     read == the oracle, PTRI == the oracle triangle, and the bell/lamp watchers' flags follow (p_up, b_same,
     l_other)
A2   THE FLOOR LAW, runtime half: the player on the terrace across the lip from two ground chasers -- NC-GATE the
     ungated hound engages (and grinds the lip, never leaving floor 0) while the same_floor sentry does NOT;
     then on the sentry's floor it DOES
A3   the ferry marches across the seam and back: its mirror follows the oracle on BOTH floors, and the clerk's
     on_floor(who = ferry) flag follows it (a unit's floor read by another unit)
A4   the pooled ghost: spawn -> it reads the player's floor (the activation seed) and the lamp fires; kill -> -1
     (THE INACTIVE ARM) and the lamp stops
A5   NC-THROW: no NullReference / InvalidCast / IndexOutOfRange in either log
B    brains + class: with the player on the ground exactly c0 engages; on the terrace exactly c1 (NC-SWAP)
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
from ff9mapkit.eb import disasm as D  # noqa: E402
from ff9mapkit.scene import bgi  # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
LIVE = GAME / "FF9CustomMap" / "StreamingAssets" / "Assets" / "Resources"
MARGIN = 3.0
THROWS = {"NullReferenceException", "InvalidCastException", "IndexOutOfRangeException"}


class Bench:
    def __init__(self, toml: str, fid: int, name: str, uids: dict):
        self.path = HERE / "bench" / toml
        self.fid, self.name, self.uids = fid, name, uids
        self.project = BLD.FieldProject.load(self.path)
        self.raw = tomllib.loads(self.path.read_text(encoding="utf-8"))
        self.floors = BLD.behavior_floor_table(self.project)
        self.fb, self.cb = BT.dry_compile(self.raw, floors=self.floors)
        fbg = f"FBG_N11_{name}"
        self.bgi_file = LIVE / "FieldMaps" / fbg / f"{fbg}.bgi.bytes"
        self.eb_file = LIVE / "CommonAsset" / "EventEngine" / "EventBinary" / "Field" / "us" / f"EVT_{name}.eb.bytes"
        self.M = bgi.BgiWalkmesh.from_file(self.bgi_file)
        self.WV = self.M.world_verts()
        self.FLOOR_OF = {ti: fi for fi, f in enumerate(self.M.floors) for ti in f.tri_ndx_list}
        h = self.raw["behavior"]["hud"][0]
        self.header = h["text"].split("==")[1].strip()
        self.rows = {}
        for i, line in enumerate(h["text"].splitlines()[1:]):
            label = line.split("[")[0].strip()
            self.rows[label] = min(10 ** int(h["digits"][i]) - 1, 0xFFFF)

    def abc(self, ti):
        return [self.WV[v] for v in self.M.tris[ti].vtx]

    def oracle(self, x, z):
        """(tri, floor, edge margin) -- None where the engine's answer is history, not geometry."""
        hits = [ti for ti in range(len(self.M.tris)) if bgi._pt_in_tri_xz(x, z, *self.abc(ti))]
        if len(hits) != 1:
            return None
        a, b, c = self.abc(hits[0])
        m = min(bgi._pt_seg_dist_xz(x, z, p, q) for p, q in ((a, b), (b, c), (c, a)))
        return hits[0], self.FLOOR_OF[hits[0]], m

    def centroid(self, ti):
        a, b, c = self.abc(ti)
        return (a[0] + b[0] + c[0]) / 3, (a[2] + b[2] + c[2]) / 3

    def i16idx(self, who, slot):
        ref = self.fb._uref(who, slot)
        m = re.fullmatch(r"Global\.Int16\[(\d+)\]", ref)
        return int(m.group(1)) if m else None

    def flag(self, name):
        return self.fb.bb.flag(name)


def _i16(st, byte_index) -> int:
    v = sum(1 << i for i in range(16) if st.flag(byte_index * 8 + i))
    return v - 0x10000 if v & 0x8000 else v


def _hud_of(b: Bench, st) -> dict | None:
    for text in st.texts:
        if b.header not in text:
            continue
        vals = {}
        for label in b.rows:
            m = re.search(r"(?m)^" + re.escape(label) + r"\s+(-?\d+)", text)
            if m:
                vals[label] = int(m.group(1))
        if len(vals) == len(b.rows) and all(vals[k] != b.rows[k] for k in b.rows):
            return vals
    return None


def _hud(g, b: Bench, timeout=20.0, until=None) -> dict | None:
    got = {}

    def ok(st):
        h = _hud_of(b, st)
        if h and (until is None or until(h)):
            got.update(h)
            return True
        return False
    try:
        g.wait_for(ok, timeout=timeout, what=f"the {b.header} HUD")
    except Exception as err:                             # noqa: BLE001 -- reported as a check
        print(f"[bgi-rung1] HUD not readable: {err}\n[bgi-rung1] texts: {g.state.texts!r}")
        return None
    return dict(got)


def _settled(g):
    a = g.settle()
    g.wait_frames(8)
    c = g.settle()
    return c, abs(a.player_x - c.player_x) <= 0.5 and abs(a.player_z - c.player_z) <= 0.5


def _stable_hud(g, b):
    h1 = _hud(g, b)
    g.wait_frames(10)
    h2 = _hud(g, b)
    return h2 if h1 is not None and h1 == h2 else None


def _go(g, x, z):
    for _ in range(3):
        try:
            g.walk_to(x, z, tolerance=30, strict=False)
            return
        except Exception as err:                         # noqa: BLE001 -- a basis disagreement: recalibrate
            print(f"[bgi-rung1] walk_to ({x},{z}): {err} -- recalibrating")
            g.calibrate_axes(recalibrate=True)


def _eb_reads(b: Bench) -> list:
    """Every 0x05 statement of the DEPLOYED .eb (decoded function by function) that reads the walkmesh."""
    from ff9mapkit.eb.model import EbScript
    data = b.eb_file.read_bytes()
    out = []
    for e in EbScript(data).entries:
        for f in e.funcs:
            for ins in D.iter_code(data, f.abs_start, f.abs_end):
                if ins.op == 0x05:
                    t = D.pretty_expr(data, ins.off + 1)[0]
                    if "B_BGIFLOOR" in t or "B_BGIID" in t:
                        out.append((e.index, f.tag, t.strip("{} ").replace(" B_EXPR_END", "")))
                elif ins.op == 0x66:                     # SetTextVariable with an expression value
                    t = D.pretty_expr(data, ins.off + 3)[0] if ins.end - ins.off > 3 else ""
                    if "B_BGIFLOOR" in t or "B_BGIID" in t:
                        out.append((e.index, f.tag, "HUD " + t.strip("{} ").replace(" B_EXPR_END", "")))
    return out


def _preflight(g, A: Bench, B: Bench) -> None:
    for b in (A, B):
        folders = [p.parent.name for p in GAME.glob("*/DictionaryPatch.txt")
                   if re.search(rf"FieldScene {b.fid}\b", p.read_text(encoding="utf-8", errors="replace"))]
        g.check(folders == ["FF9CustomMap"], f"P0: {b.fid} is served by FF9CustomMap alone", str(folders))
        probs = bgi.floor_order_problems(b.M)
        g.check(not probs and [f.tri_ndx_list for f in b.M.floors] == [list(range(8)), list(range(8, 16))],
                f"P1: the DEPLOYED {b.name} .bgi is floor-major with floors [[0..7],[8..15]]", str(probs))
        built = BLD.resolve_walkmesh(b.project, BLD.resolve_cameras(b.project)[0])
        g.check(built == b.bgi_file.read_bytes(), f"P1: {b.name}'s deployed .bgi == resolve_walkmesh(project)")
    verts, faces, fids = bgi.load_obj_floors(str(A.project.path(A.raw["walkmesh"]["obj"])))
    g.check(bgi.build(verts, faces, floor_ids=fids).regrouped is True,
            "P1: NC-REGROUP is un-vacuous -- the bench OBJ really is interleaved (ground reopened)")
    bgi0 = bgi.BgiWalkmesh.from_file(LIVE / "FieldMaps" / "FBG_N11_BGI0" / "FBG_N11_BGI0.bgi.bytes")
    same_geo = (bgi0.world_verts() == A.M.world_verts() and [t.vtx for t in bgi0.tris] == [t.vtx for t in A.M.tris]
                and [f.tri_ndx_list for f in bgi0.floors] == [f.tri_ndx_list for f in A.M.floors])
    nbr0, nbr1 = [list(t.nbr) for t in bgi0.tris], [list(t.nbr) for t in A.M.tris]
    diff = [ti for ti in range(16) if nbr0[ti] != nbr1[ti]]
    g.check(same_geo and set(diff) == {2, 9},
            "P1: the regrouped mesh == rung 0's in-game-proven BGI0 in vertices, triangles and floors; it differs "
            "ONLY in the north seam link (tris 2 and 9 unlinked -- the lip)", f"differing nbr at {diff}")
    for b in (A, B):
        reads = _eb_reads(b)
        tick = [t for _e, _f, t in reads if not t.startswith("HUD ")]
        want = {f"{b.fb._uref('player', 'flr')} B_PTR(250) B_BGIFLOOR B_LET"} | {
            f"{b.fb._uref(u, 'flr')} const({b.uids[u]}) B_BGIFLOOR B_LET"
            for u in b.fb._sensed if u != "player"}
        g.check(set(tick) == want and len({e for e, _f, t in reads if not t.startswith("HUD ")}) == 1,
                f"P2: {b.name}'s deployed .eb reads the floor only in ONE entry (the ticker), player via "
                f"B_PTR(250) and units via const(uid)", f"{sorted(set(tick) ^ want)}")
        project = b.project
        cap, orig = {}, BT.build

        def spy(raw, *, npc_slots, **kw):
            cap["slots"] = dict(npc_slots)
            return orig(raw, npc_slots=npc_slots, **kw)
        BT.build = spy
        try:
            BLD.build_script(project, "us", {}, behavior_txids={("hud", i): 900 + i
                                                                 for i, _ in BT.hud_lines(project.raw)})
        finally:
            BT.build = orig
        g.check(cap.get("slots") == b.uids, f"P3: {b.name}'s real uids", str(cap.get("slots")))
        for n in b.raw["npc"]:
            if n["name"] == "ghost":
                continue
            o = b.oracle(*n["pos"])
            g.check(o is not None and o[2] >= 100, f"P4: {b.name} {n['name']}'s post is deep inside one triangle",
                    str(o))


def _watch(g, b: Bench, flags: tuple, int16s: tuple):
    idx = [b.flag(f) for f in flags]
    for who, slot in int16s:
        k = b.i16idx(who, slot)
        idx += [k * 8 + i for i in range(16)]
    g.watch(*idx)


def _mir(st, b, who, slot):
    return _i16(st, b.i16idx(who, slot))


def run_a(g, A: Bench) -> None:
    flags = ("s_eng", "h_eng", "p_up", "b_same", "l_other", "g_on0", "f_up", "arm_s", "arm_h", "go", "kill")
    ints = (("player", "flr"), ("player", "mx"), ("player", "mz"), ("sentry", "mx"), ("sentry", "mz"),
            ("hound", "mx"), ("hound", "mz"), ("ferry", "mx"), ("ferry", "mz"), ("bell", "flr"), ("lamp", "flr"))
    g.warp(A.fid)
    _watch(g, A, flags, ints)
    for f in ("arm_s", "arm_h", "go", "kill"):
        g.flag(A.flag(f), False)

    # ---- A0 boot
    st, still = _settled(g)
    h = _stable_hud(g, A)
    g.shot("1-boot")
    st = g.state
    print(f"[bgi-rung1] A0 hud {h} at ({st.player_x:.1f},{st.player_z:.1f})")
    g.check(h is not None, "A0: the BGI 1 HUD is readable", str(st.texts))
    if h is None:
        return
    o = A.oracle(st.player_x, st.player_z)
    g.check(o is not None and _mir(st, A, "player", "flr") == h["PFLR"] == h["PLIV"] == o[1] and h["PTRI"] == o[0],
            "A0: player mirror == HUD PFLR == live PLIV == the oracle floor; PTRI == the oracle triangle",
            f"{h} vs {o}")
    posts = {n["name"]: tuple(n["pos"]) for n in A.raw["npc"]}
    for label, who in (("SFLR", "sentry"), ("HFLR", "hound"), ("FFLR", "ferry"), ("LFLR", "lamp")):
        g.check(h[label] == A.oracle(*posts[who])[1], f"A0: {who}'s floor mirror == its post's floor",
                f"{h[label]}")
    g.check(_mir(st, A, "bell", "flr") == 0 and _mir(st, A, "lamp", "flr") == 1,
            "A0: the watched bell/lamp mirrors read their posts' floors")
    bad = []
    for _ in range(20):
        g.wait_frames(3)
        s2 = g.state
        hh = _hud_of(A, s2)
        if hh is None or hh["GFLR"] != -1 or s2.flag(A.flag("g_on0")):
            bad.append((hh and hh["GFLR"], s2.flag(A.flag("g_on0"))))
    g.check(not bad, "A0: NC-UNKNOWN -- the dormant pooled ghost reads -1 and lamp's on_floor(who=ghost) never "
            "fires across 60 frames (a zero preset would read floor 0 and fire it)", str(bad[:3]))
    g.check(st.flag(A.flag("b_same")) and not st.flag(A.flag("p_up")) and st.flag(A.flag("l_other"))
            and not st.flag(A.flag("f_up")), "A0: the watchers' flags match the boot floors")

    # ---- A1 the sweep (arms off): stops + two seam crossings (the south half only)
    g.calibrate_axes()
    W0, W1 = (-250, -1300), (300, -1500)
    route = [A.centroid(2), A.centroid(6), A.centroid(7), W0, W1, A.centroid(13), A.centroid(12), A.centroid(14),
             A.centroid(11), A.centroid(8), A.centroid(9), W1, W0, A.centroid(6), A.centroid(3)]
    per_floor = {0: 0, 1: 0}
    for tx, tz in route:
        _go(g, tx, tz)
        st, still = _settled(g)
        o = A.oracle(st.player_x, st.player_z)
        if o is None or o[2] < MARGIN:
            _go(g, tx, tz)
            st, still = _settled(g)
            o = A.oracle(st.player_x, st.player_z)
        h = _stable_hud(g, A)
        st = g.state
        row = {"aim": (round(tx), round(tz)), "pos": (round(st.player_x), round(st.player_z)), "oracle": o,
               "hud": None if h is None else (h["PFLR"], h["PLIV"], h["PTRI"]), "mir": _mir(st, A, "player", "flr"),
               "flags": {f: st.flag(A.flag(f)) for f in ("p_up", "b_same", "l_other")}}
        print(f"[bgi-rung1] stop {row}")
        ok = (h is not None and o is not None and o[2] >= MARGIN
              and row["mir"] == h["PFLR"] == h["PLIV"] == o[1] and h["PTRI"] == o[0]
              and row["flags"] == {"p_up": o[1] == 1, "b_same": o[1] == 0, "l_other": o[1] == 0})
        g.check(ok, f"A1: stop {row['aim']}: mirror == PFLR == PLIV == the oracle floor, PTRI == the oracle "
                f"triangle, and p_up/b_same/l_other follow the floor", str(row))
        if ok:
            per_floor[o[1]] += 1
    g.check(per_floor[0] >= 4 and per_floor[1] >= 4, "A1: coverage -- >= 4 scored stops per floor", str(per_floor))
    g.shot("2-sweep")

    # ---- A2 THE FLOOR LAW, runtime half
    _go(g, *W0)
    _go(g, *W1)
    _go(g, *A.centroid(12))
    _go(g, *A.centroid(8))
    st, _ = _settled(g)
    pm = (_mir(st, A, "player", "mx"), _mir(st, A, "player", "mz"))
    sm = (_mir(st, A, "sentry", "mx"), _mir(st, A, "sentry", "mz"))
    hm = (_mir(st, A, "hound", "mx"), _mir(st, A, "hound", "mz"))
    cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))    # noqa: E731
    g.check(A.oracle(*pm)[1] == 1 and cheb(pm, sm) < 1500 and cheb(pm, hm) < 1500,
            "A2: the player stands on the TERRACE within both chasers' near box", f"p{pm} s{sm} h{hm}")
    g.flag(A.flag("arm_s"), True)
    g.flag(A.flag("arm_h"), True)
    h_eng_at, s_eng_seen, s_drift, hx, hflr_bad = None, False, 0, [], []
    for i in range(50):
        g.wait_frames(3)
        s2 = g.state
        if s2.flag(A.flag("h_eng")) and h_eng_at is None:
            h_eng_at = i * 3
        s_eng_seen |= bool(s2.flag(A.flag("s_eng")))
        s_now = (_mir(s2, A, "sentry", "mx"), _mir(s2, A, "sentry", "mz"))
        s_drift = max(s_drift, cheb(s_now, sm))
        hx.append(_mir(s2, A, "hound", "mx"))
        hh = _hud_of(A, s2)
        if hh is not None and hh["HFLR"] != 0:
            hflr_bad.append(hh["HFLR"])
    g.shot("3-lip")
    print(f"[bgi-rung1] A2 hound x trace {hx[::5]} (max {max(hx)}), h_eng at {h_eng_at}, sentry drift {s_drift}")
    g.check(h_eng_at is not None and h_eng_at <= 12, "A2: NC-GATE -- the UNGATED hound engages the terrace player "
            "(near alone holds)", str(h_eng_at))
    g.check(not s_eng_seen and s_drift <= 4, "A2: the same_floor sentry does NOT engage across the lip (the floor "
            "verb is the only difference) and stays at its post", f"s_eng={s_eng_seen} drift={s_drift}")
    g.check(not hflr_bad and max(hx) <= 50, "A2: the hound grinds the lip -- it never leaves floor 0 (HFLR 0, x <= "
            "50): THE FLOOR LAW's premise seen in-game", f"HFLR {hflr_bad[:3]} max x {max(hx)}")
    g.flag(A.flag("arm_s"), False)
    g.flag(A.flag("arm_h"), False)
    # RECORDED, not asserted: run 1 found the ungated hound stays WEDGED at the lip after disengaging (its blocked
    # Walk never re-aims home) -- a movement behavior outside this arc (filed separately); it no longer blocks
    home = None
    for i in range(50):
        g.wait_frames(6)
        s2 = g.state
        hp = (_mir(s2, A, "hound", "mx"), _mir(s2, A, "hound", "mz"))
        if cheb(hp, posts["hound"]) <= 40:
            home = i * 6
            break
    print(f"[bgi-rung1] A2 the disengaged hound {'walked home in %d frames' % home if home is not None else 'stayed WEDGED at ' + str(hp)}")
    g.note(f"hound after disengaging: {'home' if home is not None else 'wedged at ' + str(hp)}")
    _go(g, *W1)
    _go(g, *W0)
    _go(g, *A.centroid(3))
    st, _ = _settled(g)
    g.check(_mir(st, A, "player", "flr") == 0, "A2: the player is back on the ground")
    sm = (_mir(st, A, "sentry", "mx"), _mir(st, A, "sentry", "mz"))
    pm = (_mir(st, A, "player", "mx"), _mir(st, A, "player", "mz"))
    d0 = cheb(sm, pm)
    g.flag(A.flag("arm_s"), True)
    got = None
    for _ in range(20):
        g.wait_frames(3)
        s2 = g.state
        d = cheb((_mir(s2, A, "sentry", "mx"), _mir(s2, A, "sentry", "mz")), pm)
        if s2.flag(A.flag("s_eng")) and d0 - d >= 150:
            got = d
            break
    g.check(got is not None, "A2: on its OWN floor the same_floor sentry engages and closes >= 150u", f"{d0}->{got}")
    g.flag(A.flag("arm_s"), False)
    g.wait_for(lambda s: cheb((_mir(s, A, "sentry", "mx"), _mir(s, A, "sentry", "mz")), posts["sentry"]) <= 40,
               timeout=15, what="the sentry back at its post")

    # ---- A3 the ferry crosses the seam and back (a MOVING unit's floor, read by another unit)
    _go(g, *W0)                                  # every floor change goes through the SOUTH seam (the north
    _go(g, *W1)                                  # half of x = 0 is the lip)
    _go(g, *A.centroid(11))                     # park on the terrace, clear of the ferry's path

    def ferry_sample():
        s2 = g.state
        hh = _hud_of(A, s2)
        return ((_mir(s2, A, "ferry", "mx"), _mir(s2, A, "ferry", "mz")),
                None if hh is None else hh["FFLR"], bool(s2.flag(A.flag("f_up"))))

    trace = []                                   # every CHANGE of (position, FFLR, f_up), in time order

    def record(until, timeout):
        deadline = time.time() + timeout
        while time.time() < deadline:
            g.wait_frames(2)
            cur = ferry_sample()
            if not trace or trace[-1] != cur:
                trace.append(cur)
            if until(cur):
                return cur
        return None

    dest = (1017, -1202)
    g.flag(A.flag("go"), True)
    arrived = record(lambda c: cheb(c[0], dest) <= 20, 25)
    g.wait_frames(20)                            # the terrace DWELL: stationary, read twice
    dwell = [ferry_sample(), None]
    g.wait_frames(10)
    dwell[1] = ferry_sample()
    g.shot("4-ferry")
    g.flag(A.flag("go"), False)
    home = record(lambda c: cheb(c[0], posts["ferry"]) <= 20, 25)
    g.wait_frames(20)
    home_dwell = ferry_sample()
    flrs = [t[1] for t in trace if t[1] is not None]
    runs = [f for i, f in enumerate(flrs) if i == 0 or flrs[i - 1] != f]
    rise = next((t[0] for i, t in enumerate(trace) if i and t[1] == 1 and trace[i - 1][1] == 0), None)
    fall = next((t[0] for i, t in enumerate(trace) if i and t[1] == 0 and trace[i - 1][1] == 1), None)
    print(f"[bgi-rung1] ferry FFLR runs {runs}; rise at {rise}; fall at {fall}; dwell {dwell}; home {home_dwell}")
    o = A.oracle(*dwell[1][0])
    g.check(arrived is not None and dwell[0] == dwell[1] and o is not None and dwell[1][1] == o[1] == 1
            and dwell[1][2], "A3: at its terrace dwell the ferry's mirror == the oracle (1) and the clerk's "
            "on_floor(who = ferry) flag is up", f"arrived={arrived} dwell={dwell} oracle={o}")
    g.check(runs == [0, 1, 0], "A3: over the whole trip the ferry's floor reads ground, terrace, ground -- one "
            "rise, one fall, no flicker", str(runs))
    g.check(rise is not None and 0 < rise[0] <= 150 and fall is not None and -150 <= fall[0] < 0,
            "A3: the floor flips AT the seam (x = 0) both ways, within one pass of travel", f"rise {rise} fall {fall}")
    g.check(home is not None and home_dwell[1] == 0 and not home_dwell[2],
            "A3: back home across the seam the ferry reads the ground again and f_up drops", str(home_dwell))

    # ---- A4 the pooled ghost: activation seed, then the inactive arm
    _go(g, *W1)
    _go(g, *W0)
    _go(g, *A.centroid(3))
    st, _ = _settled(g)
    req = A.fb.pool_flags["g"]
    g.watch(*([req] + [A.flag(f) for f in flags] + [A.i16idx(w, s) * 8 + i for w, s in ints for i in range(16)]))
    g.flag(req, True)
    spawned = _hud(g, A, timeout=10, until=lambda v: v["GFLR"] != -1)
    g.wait_frames(6)
    s2 = g.state
    g.check(spawned is not None and spawned["GFLR"] == _mir(s2, A, "player", "flr") == 0
            and s2.flag(A.flag("g_on0")),
            "A4: the spawned ghost reads the player's floor at once (the activation seed) and the lamp's "
            "on_floor(who = ghost) fires", f"{spawned} g_on0={s2.flag(A.flag('g_on0'))}")
    g.shot("5-ghost")
    g.flag(A.flag("kill"), True)
    dead = _hud(g, A, timeout=10, until=lambda v: v["GFLR"] == -1)
    g.wait_frames(6)
    g.check(dead is not None and not g.state.flag(A.flag("g_on0")),
            "A4: killed, the ghost reads -1 (THE INACTIVE ARM) and the lamp stops", str(dead))
    g.flag(A.flag("kill"), False)


def run_b(g, B: Bench) -> None:
    g.warp(B.fid)
    _watch(g, B, ("p_up", "b_same", "arm"), (("player", "flr"), ("player", "mx"), ("player", "mz")))
    g.flag(B.flag("arm"), False)
    st, _ = _settled(g)
    h = _stable_hud(g, B)
    print(f"[bgi-rung1] B0 {h}")
    g.check(h is not None and h["C0F"] == 0 and h["C1F"] == 1 and h["PFLR"] == 0
            and g.state.flag(B.flag("b_same")) and not g.state.flag(B.flag("p_up")),
            "B0: c0 reads the ground, c1 the terrace (class cells by uid), the player the ground", str(h))
    if h is None:
        return
    cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))    # noqa: E731

    def engage_one(label, near, far):
        s0 = g.state
        h0 = _hud_of(B, s0)
        pm = (_mir(s0, B, "player", "mx"), _mir(s0, B, "player", "mz"))
        n0, f0 = (h0[f"{near}X"], h0[f"{near}Z"]), (h0[f"{far}X"], h0[f"{far}Z"])
        g.flag(B.flag("arm"), True)
        best, fmove = 0, 0
        for _ in range(50):
            g.wait_frames(3)
            hh = _hud_of(B, g.state)
            if hh is None:
                continue
            best = max(best, cheb(n0, pm) - cheb((hh[f"{near}X"], hh[f"{near}Z"]), pm))
            fmove = max(fmove, cheb((hh[f"{far}X"], hh[f"{far}Z"]), f0))
        g.flag(B.flag("arm"), False)
        g.check(best >= 250 and fmove <= 4, f"{label}: exactly the member on the player's floor engages "
                f"({near} closes, {far} stays) -- NC-SWAP", f"{near} closed {best}, {far} moved {fmove}")
        g.wait_for(lambda s: (_hud_of(B, s) or {}).get(f"{near}X") is not None
                   and cheb(((_hud_of(B, s))[f"{near}X"], (_hud_of(B, s))[f"{near}Z"]), n0) <= 40,
                   timeout=15, what=f"{near} back at its post")

    g.calibrate_axes()
    engage_one("B1 (player on the ground)", "C0", "C1")
    _go(g, -250, -1300)
    _go(g, 300, -1500)
    _go(g, *B.centroid(12))
    st, _ = _settled(g)
    h = _stable_hud(g, B)
    g.check(h is not None and h["PFLR"] == 1 and g.state.flag(B.flag("p_up")) and not g.state.flag(B.flag("b_same")),
            "B2: on the terrace the player reads 1 and the int-floor bell's p_up is up", str(h))
    engage_one("B2 (player on the terrace)", "C1", "C0")
    g.shot("6-pack")


def run(g) -> None:
    A = Bench("bgi1.field.toml", 30911, "BGI1", {"sentry": 2, "hound": 3, "bell": 4, "lamp": 5, "ferry": 6,
                                                   "clerk": 7, "ghost": 8})
    B = Bench("bgi1b.field.toml", 30912, "BGI1B", {"c0": 2, "c1": 3, "bell": 4})
    _preflight(g, A, B)
    g.note("walkmesh sensor rung 1")
    g.newgame()
    mark = g.log_mark()
    run_a(g, A)
    run_b(g, B)
    every = g.exceptions_since(mark)
    # every harness run on this install logs ~26-30 NullReferenceExceptions in the PLAYER's MovePC (<- UpdateMovement
    # <- HonoUpdate: no script frame; other arcs' CONTROL runs too) -- a baseline, not this feature. What the sensor
    # could throw from is a SCRIPT path: the event engine, the expression evaluator, the BGI lookup.
    ours = [e for e in every if e.name in THROWS
            and any(k in fr for fr in e.trace for k in ("EventEngine", "EBin", "BGI"))]
    base = sum(1 for e in every if e.where == "FieldMapActorController.MovePC")
    print(f"[bgi-rung1] exceptions since the mark: {len(every)} (the MovePC baseline {base})")
    g.check(not ours, "A5/B3: NC-THROW -- no NullReference / InvalidCast / IndexOutOfRange through the event "
            "engine, the expression evaluator or the BGI lookup", str([(e.name, e.where) for e in ours[:5]]))
    g.quit()
