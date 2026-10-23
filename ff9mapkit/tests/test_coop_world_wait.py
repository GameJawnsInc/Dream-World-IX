"""[ff9mapkit netsync s144] THE s144 BENCH's REPO HALF -- studies/test-harness/scenarios/coop_world_wait.py (the SOLO leg, the two
T2 legs, the DUO leg), coop_tape_record.py's WORLD variant, _coop_peer_bench's world legs and the runners
(studies/battle-coop/bench/run/cal144.example.sh / full144.example.sh).

tests/test_world_coop.py pins the engine's pure steps and tests/test_world_coop_harness.py the harness core (the stand-in's
`worldwait` rung, its fault levers, the driver, the words). This file pins what the BENCH builds on them:

  * EVERY LEG SMOKED AGAINST THE STAND-IN, through the real Session: the solo leg on the s144 stand-in (every row green), on
    the s143 one (exactly OLD_PREDICTED red, S144-CAL green) and under the lever (exactly LEVER_PREDICTED red); the T2 legs
    through a STUB PEER that connects whenever the stand-in's TRANSPORT exists (FakeGame.dial_socket: born on the first frame
    its dial gate holds -- a field on every rung, the world HUD from s144 -- with a code, then kept in every scene, as
    NetSyncRelay retries) and a stub ini whose edit only a client instance's poll or the next Ensure reads (a field load on
    every rung, a world load from s144); the duo leg on two stand-ins joined by a stub LINK (the host's place as
    HostDialogFlags says it: FakeGame.host_dialog_flags, b6 only from an s144 host on its world scene); the world recorder
    through a stub serve-guest that tapes the stand-in host's own states the same way.
  * EVERY CHECK CAN FAIL: each fault lever (FG.WORLD_FAULTS) turns EXACTLY its *_FAULT_REDS rows red, leg by leg (a fault
    a leg never meets reds nothing there), and the faults together cover every judged row; the instrument rows (INI, OR,
    ROUTE, T2-*) go red on their own wrong shapes.
  * THE PURE JUDGES go red on each wrong shape (fed hand-built states), and the offline oracle reads a kit-built 6603 the
    way it reads the install -- and names each moved target.

Every scenario-touching test runs in a CHILD process: a scenario puts its own dir on sys.path (~40 modules there a bare
import could resolve to) and reads its COOP_* knobs at import.
"""
import json
import os
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from harness import battlewire as BW                               # noqa: E402
from harness import fakegame as FG                                 # noqa: E402

SCENARIOS = REPO / "studies" / "test-harness" / "scenarios"
RUN = REPO / "studies" / "battle-coop" / "bench" / "run"

# ------------------------------------------------------------------------------------------------ the child
_CHILD = r'''
import datetime as _dt, importlib.util, json, os, pathlib, struct, sys, tempfile, threading, time
scen, tools, kit = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
sys.path.insert(0, kit)
doc = json.loads(sys.stdin.read() or "{}")
for k, v in (doc.get("env") or {}).items():
    os.environ[k] = v
from harness import Session
from harness import fakegame as FG
from harness import battlewire as BW
from harness import coop_peer as CP
def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(scen, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
cw = load("coop_world_wait")
pb, cb = cw.pb, cw.cb
# the bench's own waits, shortened for a stand-in that runs at 600 fps (every judged threshold stays the bench's)
for k, v in dict(STAY_S=1.2, MAP_S=1.2, FIELD_S=10.0, BATTLE_S=10.0, FIGHT_S=60.0, RETURN_S=15.0, DIAL_S=8.0, LAND_S=12.0,
                 REJOIN_S=12.0, DUO_LINE_S=10.0).items():
    setattr(cw, k, v)
FAKES = []
SPEED = 4.0

def root(ini=None):
    t = pathlib.Path(tempfile.mkdtemp())
    (t / "x64").mkdir()
    (t / "x64" / "FF9.exe").write_bytes(b"MZ")
    (t / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    (t / "FF9CustomMap").mkdir()
    (t / "FF9CustomMap" / "DictionaryPatch.txt").write_text("FieldScene 6603 31 FARSHORE FARSHORE 6603\n", encoding="utf-8")
    if ini:
        (t / "Memoria.ini").write_text(ini, encoding="utf-8")
    return t

def fake_for(t, run):
    f = FG.FakeGame(t, fps=600, walkmesh=(-2000.0, -3000.0, 2000.0, 2000.0))
    if run.get("caps"):
        f.netsync_caps = FG.caps_through(run["caps"])
    if run.get("door", True):
        f.regions = {6603: [{"zone": cw.FS_DOOR, "world": cw.WORLD, "world_at": list(cw.FS_LANDING)}]}
    f.exit_frames = 900
    f.overworld = {"speed": 2.0, "turn": 2.8125, "cam": 0.0, "lag": 1}
    f.world_locations = {cw.ICE_CAVERN: (cw.ICE_TILE[0], cw.ICE_TILE[1], 2.0)}
    f.world_swirl_frames, f.world_exit_frames = 40, 40
    f.atb_gain, f.enemy_hit, f.cmd_resolve_frames = 60, 1, 45
    f.world_faults = set(run.get("faults", ()))
    FAKES.append(f)
    return f

def session(t, f):
    g = Session(game_path=t, run_dir=t / "run", save_dir=t / "player-saves", pid_probe=lambda: [],
                launcher=lambda exe, f=f: f.start(), boot_timeout=15.0, verbose=False)
    g._booted_once = True
    return g

def rows_of(checks):
    rows = [(r["what"].split(":")[0], bool(r["ok"]), r["detail"][:500]) for r in checks]
    return {"red": sorted(c for c, ok, _d in rows if not ok), "all": [c for c, _ok, _d in rows],
            "detail": {c: d for c, _ok, d in rows}}

def write_tape(path, recs, head=None):
    head = json.dumps(head or {"tool": "stub", "started": _dt.datetime.now().isoformat()}).encode("utf-8")
    body = b"".join(struct.pack("<dBI", r.t, r.dir, len(r.payload)) + r.payload for r in recs)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"F9TAPE01" + struct.pack("<I", len(head)) + head + body)

class StubIni:
    """pb.IniGuard's stand-in: the FILE edit only -- the stand-in's own ini model (FakeGame.apply_ini) decides who reads it:
    an existing client instance's 2 s poll at once, else the next Ensure (a field load; a world load from s144)."""
    def __init__(self, ini, values, *, label, run_dir=None, backup_root=None):
        self.values, self.applied, self.restored = dict(values), False, None
    def apply(self):
        FAKES[-1].apply_ini(self.values)
        self.applied = True
        return "the stub ini"
    def update(self, values):
        self.values.update(values)
        FAKES[-1].apply_ini(self.values)
        return f"the stub ini updated {values}"
    def restore(self):
        self.restored = (True, "restored (stub)")
        return self.restored

class _Peer(pb.PeerProc):
    def _say(self, msg):
        n = _dt.datetime.now()
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(f"[coop-peer {n:%H:%M:%S}.{n.microsecond // 1000:03d}] {msg}\n")
    def _arg(self, name):
        return self.args[self.args.index(name) + 1] if name in self.args else None

class StubReplay(_Peer):
    """coop_peer replay-host's stand-in: it CONNECTS whenever the stand-in's transport exists (FakeGame.dial_socket -- made
    where the dial gate held, kept in any scene), then replays the tape's host frames (SPEED x) onto the stand-in's
    followed-client seams -- the position lane's field, section 7's flags, section 0 -- with replay-host's own lines."""
    def start(self):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.started = _dt.datetime.now()
        self._halt = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()
    def _run(self):
        f = FAKES[-1]
        port, code, stop = self._arg("--port"), self._arg("--code"), self._arg("--stop-at")
        stop = float(stop) if stop else None
        self._say(f"listening on ws://127.0.0.1:{port} -- the stub replay-host")
        end = time.time() + 30.0
        while not self._halt.is_set() and time.time() < end and not f.dial_socket:
            time.sleep(0.05)
        if self._halt.is_set() or not f.dial_socket:
            return
        self._say(f"GUEST game connected (session {code})")
        f._mlog(f"[NetSync] relay connected ws://127.0.0.1:{port}/sess/{code}?role=guest")
        _h, recs, _torn = CP.read_tape(self.args[0])
        frames = [(r, w, p) for r, w, p in CP.host_frames(recs) if stop is None or r.t <= stop]
        t0 = frames[0][0].t
        self._say(f"REPLAY start: tape {t0:.2f} s -> now; {len(frames)} host frame(s) up to tape "
                  f"{stop if stop is not None else frames[-1][0].t:.2f} s")
        wall0, field, flags, story, first = time.time(), None, -1, None, True
        for r, w, p in frames:
            due = wall0 + (r.t - t0) / SPEED
            while time.time() < due and not self._halt.is_set():
                time.sleep(0.01)
            if self._halt.is_set():
                return
            if w == CP.TYPE_POS:
                d = CP.parse_pos_payload(p)
                if d and d["field"] != field:
                    self._say(f"tape {r.t:.2f}: host field {field if field is not None else 'none'} -> {d['field']}")
                    field = d["field"]
            elif w == CP.TYPE_STATE:
                sec = pb.state_sections(p)
                if 0 in sec:
                    story = bytes(sec[0])
                if 7 in sec:
                    v = BW.parse_dialog_section(sec[7])
                    flags = v["flags"] if v else flags
            if field is None:
                continue
            if first:
                f.follow_session(field, flags=flags, fresh=True, story=story, pair_kick=True)
                first = False
            else:
                f.host_at(field, flags=flags, story=story)
        if stop is not None:
            self._say(f"STOP-AT tape {stop:.2f} s reached: the host sends nothing more")
    def alive(self):
        return getattr(self, "_t", None) is not None and self._t.is_alive()
    def stop(self, timeout=10.0):
        if getattr(self, "_t", None) is None:
            self.how_ended = "never started"
            return self.how_ended
        self._halt.set()
        self._t.join(5.0)
        self.how_ended = "stopped cleanly (code 0)"
        self.lines()
        return self.how_ended

TAPE_SCALE = 40.0
class StubServe(_Peer):
    """coop_peer serve-guest's stand-in for the WORLD recorder: the host stand-in connects at once, and its OWN states are
    taped at 10 Hz -- the position lane's field (0 off a field), section 0, section 7's flags as HostDialogFlags says them
    (b6 only from an s144 host on its world HUD) -- each stamped TAPE_SCALE x its wall second (a 2 s stay = 80 tape s)."""
    def start(self):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.started = _dt.datetime.now()
        self.port, self.tap = self._arg("--port"), self._arg("--tap")
        self._halt, self._recs = threading.Event(), []
        self._say(f"listening on ws://127.0.0.1:{self.port} -- the stub serve-guest")
        self._say(f"HOST game connected (session {self._arg('--code') or 'ff9-T2BENCH1'}) -- this tool is its guest now")
        f = FAKES[-1]
        f._mlog(f"[NetSync] relay connected ws://127.0.0.1:{self.port}/sess/ff9-T2BENCH1?role=host")
        self._t = threading.Thread(target=self._tape, daemon=True)
        self._t.start()
    def _tape(self):
        f, t0 = FAKES[-1], time.time()
        while not self._halt.is_set():
            t = 1.0 + (time.time() - t0) * TAPE_SCALE
            fld, flags = f.host_lane_field(), f.host_dialog_flags()       # HostDialogFlags / the lane, as the engine says them
            sec0 = bytes([0, 0x00, 0x08]) + bytes(f.story_bytes[:2048]).ljust(2048, b"\0")
            body = BW.append_section(sec0, BW.SECTION_DIALOG, BW.dialog_section(0x0144, 7, flags, 0, fld))
            self._recs += [CP.Record(t, 0, CP.build_pos_frame(fld, model=1, pos=(0.0, 0.0, 0.0))),
                           CP.Record(t, 0, CP.build_frame(CP.TYPE_STATE, body))]
            time.sleep(0.1 / TAPE_SCALE * 4)
    def alive(self):
        return not self._halt.is_set()
    def stop(self, timeout=10.0):
        if self._halt.is_set():
            return self.how_ended
        self._halt.set()
        self._t.join(5.0)
        write_tape(pathlib.Path(self.tap), self._recs)
        self._say(f"tape {self.tap}: {len(self._recs)} record(s), 0.1 MB")
        self.how_ended = "stopped cleanly (code 0)"
        self.lines()
        return self.how_ended

def stubs(module_pb):
    module_pb.IniGuard = StubIni
    module_pb.port_free = lambda port, host="127.0.0.1": (True, "")

class OwnerDial(threading.Thread):
    """[review 2] THE OWNER's TRANSPORT: the guest game launched on the owner's Memoria.ini, so a client instance was born at its
    first field -- NetSyncRelay.ConnectLoop retrying the owner's endpoint with the bridge down: one refused attempt logged every
    2 s until the park's config change (the stand-in's ini signature leaves the owner's) stops it, then ONE more -- the attempt
    already in flight (NetSyncRelay.Stop only clears _running). RJ-PARK must read none of them as the bench's dial."""
    LINE = ("[NetSync] relay connect to 127.0.0.1:49201 failed (No connection could be made because the target machine "
            "actively refused it.)")
    def __init__(self, f, sig):
        super().__init__(daemon=True)
        self.f, self.sig, self.halt, self.n = f, sig, threading.Event(), 0
    def run(self):
        nxt = 0.0
        while not self.halt.is_set():
            if self.f._ini_sig != self.sig:
                self.f._mlog(self.LINE)
                self.n += 1
                return
            if time.time() >= nxt:
                self.f._mlog(self.LINE)
                self.n += 1
                nxt = time.time() + 2.0
            time.sleep(0.05)

def solo(run):
    t = root(run.get("ini"))
    cw.read_oracle = (lambda game: {"problems": run["oracle_problems"], "facts": {}}) if run.get("oracle_problems") \
        else (lambda game: {"problems": {}, "facts": {"stand-in": True}})
    f = fake_for(t, run)
    cw.cb.CALIBRATE = bool(run.get("cal"))
    cw.LEG = "solo"
    cw.CLOSE_MAP = run.get("close_map", True)
    if run.get("f6_fail"):                                 # F6's way back fails ONCE while the game stays on the world map
        real, calls = cw._reach_world_again, []
        def once(g):
            calls.append(1)
            return (False, "stub: the way back failed", g.state) if len(calls) == 1 else real(g)
        cw._reach_world_again = once
    real_walk, real_press, real_close = cw.walk_out, Session.press, cw.close_opened_map
    trace = {"selects": [], "after_close": []}
    if run.get("hud_on"):                                  # a save whose w_naviMode is 1: the FIRST walk out lands in HUD
        walks = []
        def walk(g, **kw):
            if not walks:
                f.world_navi = 1
            walks.append(1)
            return real_walk(g, **kw)
        cw.walk_out = walk
    def press(self, button, *a, **k):                      # THE STAND-IN's HUD at every Select the bench sends (the test's
        if str(button).lower() == "select":                # read: the engine publishes none)
            trace["selects"].append(f.world_hud_state)
        return real_press(self, button, *a, **k)
    def close(g):
        out = real_close(g)                                # the trail: F3's detail carries it
        trace["after_close"].append(f.world_hud_state)
        return out
    Session.press, cw.close_opened_map = press, close
    try:
        with session(t, f) as g:
            cw.run(g)
            return dict(rows_of(list(g.checks)), trace=trace)
    finally:
        cw.walk_out, Session.press, cw.close_opened_map = real_walk, real_press, real_close

def t2(run):
    leg = run["leg"]
    t = root()
    stubs(pb)
    if run.get("owner_up"):                                # [review 2] the owner's own bridge listening on 49201
        pb.port_free = lambda port, host="127.0.0.1": ((False, f"{host}:{port} is taken (stub: the owner's bridge)")
                                                      if int(port) == pb.OWNER_PORT else (True, ""))
    pb.PeerProc = StubReplay
    tape = t / ("tape-host250-s143.f9tape" if leg == "rejoin" else "tape-host6603-world-s144.f9tape")
    if run.get("tape") != "none":
        if leg == "rejoin":
            write_tape(tape, pb.synthetic_tape(CP))
        else:
            write_tape(tape, pb.synthetic_world_tape(CP, b6=run.get("b6", True), world_s=run.get("world_s", 90.0)))
        if leg == "rejoin" and run.get("cal_sidecar", True):
            pb.write_cal(tape, True, stage=143, detail="stub")
        os.environ["COOP_TAPE"] = str(tape)
    else:
        os.environ["COOP_TAPE"] = str(t / "nope.f9tape")
    if "port" in run:
        cw.PORT = int(run["port"])
    f = fake_for(t, run)
    owner = None
    if run.get("instance"):                                # a client instance before the leg (its 2 s poll reads every edit)
        f.netsync.update(enabled=True, role="client", instance=True, selftest=False, forced=False)
        f.session_code, f._ini_sig = "ff9-OTHER", (True, "client", f.relay_url, "ff9-OTHER")
        owner = OwnerDial(f, f._ini_sig)                   # [review 2] ... retrying the owner's endpoint until the park
        owner.start()
    if run.get("old_order"):                               # s144-as-built's order: the code on 6603, a field reload, the walk
        def old(g, led, ctx, p, rows):
            ctx.path = "old"
            ctx.guard = pb.IniGuard(pathlib.Path(g.game_path) / "Memoria.ini", cw.GUEST_VALUES, label="x")
            g.note(ctx.guard.apply())
            g.warp(cw.FARSHORE)                            # _wait_config's reload: Ensure at the field load
            ctx.cfg = cw._wait_config(g, ctx, reload=False, wait=4.0)
            time.sleep(1.2)                                # the engine's whole-second stamps: a field-side line a second clear
            began = {}
            ok, why, st = cw.walk_out(g, before_walk=lambda: began.setdefault("t", _dt.datetime.now()))
            ctx.anchors["began"] = began.get("t")
            pk_ok, pk_why = cw.judge_park("ensure", ctx.eng.lines(), before=began["t"], overlay=None)
            led.check(f"{p}-PARK", pk_ok, pk_why)
            st = cw._sample(g, ctx)
            ctx.anchors["world"] = _dt.datetime.now()
            led.check(f"{p}-I", ok, why)
            ctx.base = g.state
            return True
        cw._rejoin_park_and_walk = old
    cw.cb.CALIBRATE = bool(run.get("cal"))
    cw.LEG = leg
    with session(t, f) as g:
        cw.run(g)
        out = rows_of(list(g.checks))
    if owner is not None:
        owner.halt.set()
        out["owner_lines"] = owner.n
    return out

class Link(threading.Thread):
    """The stub TRANSPORT of the duo: the host stand-in's place -- its field, or 0 off a field with section 7's flags as
    HostDialogFlags says them (b6 only from an s144 host on its world HUD) -- onto the guest's followed-client seams, and
    the host's world MAPJUMP intent (FakeGame.host_field_intent, section 4) once per nonce: the in-game duo's guest armed
    off it at once, with no serial debounce."""
    def __init__(self, host, guest):
        super().__init__(daemon=True)
        self.h, self.g, self.halt = host, guest, threading.Event()
    def run(self):
        sent = None
        while not self.halt.is_set():
            h = self.h
            self.g.host_at(h.host_lane_field(), flags=h.host_dialog_flags(), story=bytes(h.story_bytes))
            it = h.host_field_intent
            if it is not None and it != sent:
                sent = it
                self.g.host_intent(it[1])
            time.sleep(0.02)

class Coarse:
    """THE BRACKET LAW's in-game shape: a guest sampler SLOWER than the arm -- a read that lands INSIDE the armed window
    (WorldHUD, follow.world_armed >= 0) answers the last publish before it (a frame already read, so every watch skips it).
    s144's first duo: the host's MAPJUMP intent armed the guest at once and its fade was shorter than one sample."""
    def __init__(self, g):
        self._g, self._last = g, None
    def __getattr__(self, name):
        return getattr(self._g, name)
    @property
    def state(self):
        s = self._g.state
        armed = (((s.netsync or {}).get("session") or {}).get("follow") or {}).get("world_armed")
        if s.ui_state == "WorldHUD" and isinstance(armed, int) and armed >= 0 and self._last is not None:
            return self._last
        self._last = s
        return s

class StubDuo:
    def __init__(self, host, guest):
        self.host, self.guest, self.strict, self.rows, self.notes = host, guest, True, [], []
    def check(self, ok, what, detail="", *, role=None, cid=None):
        self.rows.append((cid, bool(ok), str(detail)[:500]))
        return bool(ok)
    def note(self, msg):
        self.notes.append(msg)

def duo(run):
    th, tg = root(), root()
    fh, fgst = fake_for(th, run), fake_for(tg, run)
    # the world -> field fade, in frames: long -- 0.4 s of wall time at 600 fps (4 s of the stand-in's 60 fps game clock, inside
    # WORLD_ARM_TIMEOUT_MS: a longer fade times the arm out and its landing goes uncounted) -- so the guest's samplers land
    # INSIDE its armed window and the overlay is judged (line_s143's D3 red), and the host's intent always reaches the guest
    # before the host's lane says 300 (no serial debounce to read 'rejoining' off); `coarse` stands in for the in-game
    # sampler that missed the window
    fh.world_exit_frames = fgst.world_exit_frames = int(run.get("exit_frames", 240))
    cw.cb.CALIBRATE = bool(run.get("cal"))
    real_arm = cw.judge_rejoin_arm
    if run.get("strict_d3"):                               # D3 judged as before THE BRACKET LAW (the overlay always required)
        cw.judge_rejoin_arm = lambda *a, bracket=False, **k: real_arm(*a, **k)
    gh, gg = session(th, fh), session(tg, fgst)
    try:
        with gh, gg:
            for g in (gh, gg):
                g.newgame(settle=0)
                g.warp(cw.FARSHORE)
            fh.story_bytes[pb.MARKER_BYTE] = pb.MARKER_VALUE
            fgst.follow_session(cw.FARSHORE, flags=BW.HF_ON_FIELD | BW.HF_CONTROL, fresh=True,
                                story=bytes(fh.story_bytes), pair_kick=True)
            link = Link(fh, fgst)
            link.start()
            gg.wait_for(lambda s: (s.netsync or {}).get("session", {}).get("mirroring") is True, timeout=5, what="paired")
            d = StubDuo(gh, Coarse(gg) if run.get("coarse") else gg)
            try:
                cw.run_duo(d)
            finally:
                link.halt.set()
            return {"red": sorted(c for c, ok, _d in d.rows if not ok), "all": [c for c, _ok, _d in d.rows],
                    "detail": {c: dd for c, _ok, dd in d.rows}, "strict": d.strict, "lands": fgst._wj["lands"],
                    "intent": fh.host_field_intent}
    finally:
        cw.judge_rejoin_arm = real_arm

def rec(run):
    t = root()
    os.environ["COOP_TAPE_DIR"] = str(t / "tapes")
    for k, v in (run.get("env") or {}).items():           # read at import (COOP_TAPE_WORLD picks the catalog and the port)
        os.environ[k] = v
    tr = load("coop_tape_record")
    tr.PRE_S, tr.WORLD_S = 0.5, 2.0
    stubs(tr.pb)
    tr.pb.PeerProc = StubServe
    f = fake_for(t, run)
    with session(t, f) as g:
        tr.run(g)
        out = rows_of(list(g.checks))
    tapes = sorted((t / "tapes").glob("*-world-*.f9tape"))
    out["tapes"] = [p.name for p in tapes]
    out["pointer"] = (t / "tapes" / pb.WORLD_POINTER).exists()
    out["latest"] = (t / "tapes" / "latest.json").exists()
    out["port"] = tr.PORT
    if tapes:
        d = CP.tape_where(CP.read_tape(tapes[-1])[1])
        out["where"] = {w: CP.where_ok(d, w) for w in ("world", "none")}
    return out

kinds = {"solo": solo, "t2": t2, "duo": duo, "rec": rec}
results = {name: kinds[run["kind"]](run) for name, run in doc.get("runs", {}).items()}
print(json.dumps(results))
'''


def _child(payload, *, timeout: float = 900.0) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _CHILD, str(SCENARIOS), str(REPO / "tools"),
                          str(REPO / "ff9mapkit")], env=env, input=json.dumps(payload), capture_output=True, text=True,
                         timeout=timeout)
    assert out.returncode == 0, out.stderr[-4000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def _run(kind: str, **run) -> dict:
    return _child({"runs": {"r": dict(run, kind=kind)}})["r"]


_TABLES = r'''
import importlib.util, json, os, sys
scen, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(scen, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
cw, tr = load("coop_world_wait"), load("coop_tape_record")
print(json.dumps({
    "solo": list(cw.solo_catalog(False)), "solo_cal": list(cw.solo_catalog(True)), "world_rows": list(cw.WORLD_ROWS),
    "old": list(cw.OLD_PREDICTED), "lever": list(cw.LEVER_PREDICTED),
    "solo_faults": {k: list(v) for k, v in cw.SOLO_FAULT_REDS.items()},
    "t2": {leg: list(cw.t2_catalog(leg, False)) for leg in ("rejoin", "wait")},
    "t2_cal": {leg: list(cw.t2_catalog(leg, True)) for leg in ("rejoin", "wait")},
    "t2_pred": {k: list(v) for k, v in cw.T2_PREDICTED.items()},
    "t2_faults": {leg: {k: list(v) for k, v in d.items()} for leg, d in cw.T2_FAULT_REDS.items()},
    "duo": list(cw.DUO_CHECKS), "duo_pred": list(cw.DUO_PREDICTED),
    "duo_faults": {k: list(v) for k, v in cw.DUO_FAULT_REDS.items()},
    "consts": {"FARSHORE": cw.FARSHORE, "FS_DOOR": cw.FS_DOOR, "FS_EXIT": list(cw.FS_EXIT), "FS_LANDING": list(cw.FS_LANDING),
               "WORLD": cw.WORLD, "ICE_CAVERN": cw.ICE_CAVERN, "ICE_TILE": list(cw.ICE_TILE), "SCENE": cw.SCENE,
               "GROUP": cw.GROUP, "PORT": cw.PORT, "PROBE": cw.PROBE, "HELD_U": cw.HELD_U, "PAIR": cw.PAIR,
               "LEGS": list(cw.LEGS), "LEG": cw.LEG, "LINE_S": cw.LINE_S},
    "values": cw.GUEST_VALUES,
    "rec": {"world": list(tr.WORLD_CATALOG), "plain": list(tr._catalog(0, False)), "catalog": list(tr.CATALOG),
            "field": tr.WORLD_FIELD, "world_s": tr.WORLD_S, "port_plain": tr.PORT},
    "doc": " ".join((cw.__doc__ or "").split()), "rec_doc": " ".join((tr.__doc__ or "").split())}))
'''


@pytest.fixture(scope="module")
def tables() -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _TABLES, str(SCENARIOS), str(REPO / "tools")], env=env,
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-3000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


# ------------------------------------------------------------------------------------------------ the tables
def test_the_tables_are_the_docstring_and_each_others(tables):
    t = tables
    solo, cal = set(t["solo"]), set(t["solo_cal"])
    assert cal == solo | {"S144-CAL"} and "S144-CAL" not in solo
    assert set(t["world_rows"]) <= solo and set(t["old"]) <= solo and set(t["lever"]) < set(t["old"])
    # the instrument rows and the control are never predicted red; the lever spares the hold, itself, the control, the verb
    assert not {"S144-INI", "S144-OR", "S144-S0", "S144-ROUTE", "S144-F5", "S144-R"} & set(t["old"])
    assert not {"S144-F0", "S144-F4", "S144-F5", "S144-B1", "S144-B2", "S144-B3", "S144-R"} & set(t["lever"])
    for faults, cat in ((t["solo_faults"], solo), (t["duo_faults"], set(t["duo"])),
                        *((t["t2_faults"][leg], set(t["t2"][leg])) for leg in ("rejoin", "wait"))):
        assert set(faults) <= set(FG.WORLD_FAULTS), set(faults) - set(FG.WORLD_FAULTS)
        assert all(set(rows) <= cat and rows for rows in faults.values()), faults
    # every judged solo row has a fault that reds it; the instrument rows have their own tests below
    covered = {r for rows in t["solo_faults"].values() for r in rows}
    assert covered == set(t["world_rows"]) | {"S144-R"}, set(t["world_rows"]) ^ covered
    for leg in ("rejoin", "wait"):
        judged = {c for c in t["t2"][leg] if c.startswith("S144-") and not c.endswith(("-I", "-PARK"))}
        assert judged == set(t["t2_pred"][leg])
        # every judged T2 row has a fault -- but RJ-DIAL, whose red is the s143 stand-in's own dial gate (the calibration
        # run below pins it: an s143 guest never dials off a field)
        assert {r for rows in t["t2_faults"][leg].values() for r in rows} == judged - {"S144-RJ-DIAL"}
        assert set(t["t2_cal"][leg]) == set(t["t2"][leg]) | {f"S144-{'RJ' if leg == 'rejoin' else 'WT'}-CAL"}
    assert "T2-CAL" in t["t2"]["rejoin"] and "T2-CAL" not in t["t2"]["wait"]
    assert {r for rows in t["duo_faults"].values() for r in rows} == set(t["duo_pred"]) == set(t["duo"]) - {"S144-D0"}
    c = t["consts"]
    assert (c["FARSHORE"], c["WORLD"], c["ICE_CAVERN"], c["SCENE"], c["GROUP"], c["PROBE"]) == \
        (6603, 9011, 300, 67, 0, "netsync.world.freeze")
    assert c["FS_LANDING"] == [68.0, -444.0] and c["ICE_TILE"] == [1197.37, -796.7] and c["HELD_U"] == 2.0
    assert c["PORT"] == 49231 and c["PORT"] != 49201 and t["values"]["RelayUrl"] == "ws://127.0.0.1:49231"
    assert t["values"]["Role"] == "client" and t["values"]["FollowHost"] == "1" and t["values"]["SessionGraceMs"] == "30000"
    assert c["PAIR"] == {"field": 6603} and c["LEGS"] == ["solo", "rejoin", "wait"] and c["LEG"] == "solo"
    assert c["LINE_S"] == 6.0                                           # the old-host debounce (3 s) + 3
    for frag in ("OLD_PREDICTED", "LEVER_PREDICTED", "THE UNATTENDED LAW", "be01339d49f6a87b", "FS_DOOR", "FS_LANDING",
                 "(1197.37, -796.7)", "block (18,12)", "THE ACTOR-BRICK LAW", "the s94 booster", "`bench worldfreeze off`",
                 "'battle: field only'", "BSC_EF_R007", "BSC_WM_0007", "COOP_TAPE_WORLD=1", "latest-world.json",
                 "never 49201", "IniGuard", "dial_ready", "WHAT NO LEG HERE REACHES", "game_snap.ps1",
                 "Triangle is NOT pressed", "piece C's finding", "D-CAL", "FieldScene 6603 31",
                 "py tools/harness/duo.py studies/test-harness/scenarios/coop_world_wait.py"):
        assert frag in t["doc"], frag
    rw = t["rec"]
    assert rw["plain"] == t["rec"]["catalog"] and rw["field"] == 6603 and rw["world_s"] == 90.0
    assert {"REC-WX", "REC-WS", "REC-WF1", "REC-WF2", "REC-WF3", "REC-T", "REC-INI"} <= set(rw["world"])
    assert not {"REC-B", "REC-W", "REC-F1", "REC-SEAT"} & set(rw["world"]) and rw["port_plain"] == 49201
    for frag in ("THE WORLD VARIANT", "COOP_TAPE_WORLD=1", "latest-world.json", "NEVER latest.json", "--want world"):
        assert frag in t["rec_doc"], frag


def test_the_route_constants_are_the_landing_tomls_and_round_8s():
    """FS_DOOR / FS_LANDING are the landing toml's own [[gateway]] (read here off the file, as the oracle reads it), the tile
    point lies on round 8's walk lane across the stock tile (x 1197.37, z -795.2..-798.3), and FS_EXIT is inside the door."""
    import tomllib
    doc = tomllib.loads((REPO / "studies" / "overworld-topography" / "west-seam-continent" / "landing.field.toml")
                        .read_text(encoding="utf-8"))
    gw = next(g for g in doc["gateway"] if g.get("to") == "worldmap")
    assert gw["zone"] == [[285, -352], [875, -460], [424, -2944], [-166, -2836]] and gw["arrive"] == [68.0, -444.0]
    src = (REPO / "studies" / "terrain-malleability" / "ingame" / "r8_build.py").read_text(encoding="utf-8")
    assert 'WALK = {"start": (1197.37, -789.63), "bearing": 270.0, "distance": 9.0, "onto_tile_z": -795.5}' in src
    assert "the walk lane crosses the tile: every point of x = 1197.37 between z -795.2 and -798.3 lies on it" in src
    x, z = 1197.37, -796.7
    assert -798.3 <= z <= -795.2

    def inside(q, px, pz):
        n, hit = len(q), False
        for i in range(n):
            (ax, az), (bx, bz) = q[i], q[(i + 1) % n]
            if (az > pz) != (bz > pz) and px < ax + (pz - az) * (bx - ax) / (bz - az):
                hit = not hit
        return hit
    assert inside(gw["zone"], 400.0, -1400.0) and not inside(gw["zone"], 900.0, -1400.0)   # FS_EXIT in; the spawn out


# ------------------------------------------------------------------------------------------------ the solo leg
SOLO_ALL = ["S144-INI", "S144-OR", "S144-S0", "S144-P0", "S144-P1", "S144-ROUTE", "S144-F0", "S144-F1", "S144-F1K",
            "S144-F2", "S144-F3", "S144-F6", "S144-F4", "S144-F5", "S144-B1", "S144-B2", "S144-B3", "S144-R"]


def test_the_solo_leg_is_green_on_the_s144_stand_in():
    r = _run("solo")
    assert r["red"] == [], {c: r["detail"][c] for c in r["red"]}
    assert r["all"] == SOLO_ALL                                          # every row, once, in run order
    d = r["detail"]
    assert "moved 0.00u" in d["S144-F1"] and "edges +1" in d["S144-F1K"] and "keys 0 -> 1" in d["S144-F2"]
    assert "the map shut" in d["S144-F3"] and "ENTRY FieldHUD 300" in d["S144-F5"]
    assert "world battle 67 group 0 as a random encounter started from world map 9011" in d["S144-B1"]
    assert "the release line 1x" in d["S144-R"] and "freeze.off False" in d["S144-R"]
    # THE STOCK CYCLE (the s144 probe): the world landed in HUDNoMiniMap -- press 1 turned the minimap on, press 2 was the
    # refused HUD -> FullMap step; the close then read the map shut and pressed nothing (the stand-in's HUD per Select)
    assert d["S144-F3"].startswith("2 Select press(es): map +1;"), d["S144-F3"]
    assert "THE CLOSE: 0 Select press(es); frozen: skips advance: the map was shut" in d["S144-F3"], d["S144-F3"]
    assert r["trace"] == {"selects": ["HUDNoMiniMap", "HUD"], "after_close": ["HUD"]}, r["trace"]


def test_f3_judges_a_world_that_landed_in_the_hud_after_one_press():
    """A save whose w_naviMode is 1 lands its world map in HUD: the FIRST Select is the refused step -- one press, green, and
    no second Select (it would only be refused again, and counted)."""
    r = _run("solo", hud_on=True)
    assert r["red"] == [], {c: r["detail"][c] for c in r["red"]}
    assert r["detail"]["S144-F3"].startswith("1 Select press(es): map +1;"), r["detail"]["S144-F3"]
    assert r["trace"] == {"selects": ["HUD"], "after_close": ["HUD"]}, r["trace"]


def test_f3_drives_the_stock_cycle_and_its_close_leaves_the_map_shut_whatever_the_state():
    """F3's red stays BEHAVIOURAL and the close leaves the HUD shut, whatever state the presses ended in (never Cancel):
    `fullmap_open` (frozen, never refused) -- press 2 OPENS the map, the dispatcher stops, one close Select shuts it;
    `counters_dark` (a dark `skips` reads as a map that opened) -- no second press, `map` +0, the close's TWO refused
    Selects (CLOSE_PRESSES: never the cycle's three) leave the HUD; the s143 stand-in and the lever (unfrozen, no witness
    of an open map) -- two presses go HUD then FullMap, `map` never counts, and the close's walk witness stalls -> one
    Select -> HUDNoMiniMap. F3 is recorded after the close and carries its trail: on s143 (no key can count) the red names
    the behaviour -- the map OPENED and the close shut it."""
    r = _child({"runs": {"open": {"kind": "solo", "faults": ["fullmap_open"]},
                         "dark": {"kind": "solo", "faults": ["counters_dark"]},
                         "s143": {"kind": "solo", "caps": "leaderguard", "cal": True},
                         "lever": {"kind": "solo", "cal": True}}})
    o = r["open"]
    assert "S144-F3" in o["red"] and "the dispatcher NOT asked after press 2" in o["detail"]["S144-F3"], o["detail"]["S144-F3"]
    assert o["trace"] == {"selects": ["HUDNoMiniMap", "HUD", "FullMap"], "after_close": ["HUDNoMiniMap"]}, o["trace"]
    dk = r["dark"]
    assert dk["detail"]["S144-F3"].startswith("1 Select press(es): map +0 (the refusal never counted)"), dk["detail"]
    assert dk["trace"] == {"selects": ["HUDNoMiniMap", "HUD", "HUD"], "after_close": ["HUD"]}, dk["trace"]
    assert "THE CLOSE: 2 Select press(es)" in dk["detail"]["S144-F3"] and "NOT witnessed shut" in dk["detail"]["S144-F3"]
    for name in ("s143", "lever"):
        x = r[name]
        assert "S144-F3" in x["red"] and x["trace"] == {"selects": ["HUDNoMiniMap", "HUD", "FullMap"],
                                                        "after_close": ["HUDNoMiniMap"]}, (name, x["trace"])
        assert "THE CLOSE: 1 Select press(es)" in x["detail"]["S144-F3"], (name, x["detail"]["S144-F3"])
        assert "the map had OPENED: shut by 1 Select(s)" in x["detail"]["S144-F3"], (name, x["detail"]["S144-F3"])
    assert r["lever"]["detail"]["S144-F3"].startswith("2 Select press(es): map +0 (the refusal never counted)")
    assert r["s143"]["detail"]["S144-F3"].startswith("absent:")
    assert "THE CLOSE: 1 Select press(es)" in o["detail"]["S144-F3"], o["detail"]["S144-F3"]


def test_the_solo_leg_calibrates_on_s143_and_under_the_lever(tables):
    r = _child({"runs": {"s143": {"kind": "solo", "caps": "leaderguard", "cal": True},
                         "lever": {"kind": "solo", "cal": True}}})
    s143, lever = r["s143"], r["lever"]
    assert s143["red"] == sorted(tables["old"]), s143["red"]
    assert lever["red"] == sorted(tables["lever"]), lever["red"]
    for x in (s143, lever):
        assert "S144-CAL" in x["all"] and "S144-CAL" not in x["red"]
    d = s143["detail"]
    assert "absent" in d["S144-P0"] and "moved 60.00u" in d["S144-F1"] and "battle: field only" in d["S144-B1"]
    assert "the lever cannot be sent" in d["S144-F4"] and "netsync.world.freeze" in d["S144-F4"]
    assert "ENTRY FieldHUD 300" in d["S144-F5"]                          # the control: green on every engine
    d = lever["detail"]
    assert "moved 60.00u" in d["S144-F1"] and "keys 0 -> 0" in d["S144-F2"] and "map +0" in d["S144-F3"]
    assert "OFF line 1x" in d["S144-P1"] and "the release line 1x" in d["S144-R"]


@pytest.mark.parametrize("fault", FG.WORLD_FAULTS)
def test_each_world_fault_turns_exactly_its_solo_rows_red(tables, fault):
    """A CHECK THAT CANNOT FAIL IS NO CHECK: each fault (a value the engine would not publish, never an absent key) reds
    exactly its SOLO_FAULT_REDS rows -- and a fault the solo leg never meets (the followed client's) reds nothing."""
    want = sorted(tables["solo_faults"].get(fault, ()))
    r = _run("solo", faults=[fault])
    assert r["red"] == want, (r["red"], {c: r["detail"][c] for c in set(r["red"]) ^ set(want)})


def test_the_bench_closes_a_full_map_that_opened_with_select_never_cancel():
    """harness-f3-cancel-never-closes-fullmap: under the `fullmap_open` fault the map OPENS at F3, and stock never closes it
    on Cancel (the stand-in now models that). With F6's way back failing (the game still on the world map), F4 and F5 are
    green ONLY because the bench closed the map with a second Select; without that close they read red (the walker cannot
    walk with w_naviMode 2)."""
    r = _child({"runs": {"close": {"kind": "solo", "faults": ["fullmap_open"], "f6_fail": True},
                         "open": {"kind": "solo", "faults": ["fullmap_open"], "f6_fail": True, "close_map": False},
                         # [the stock cycle] the LEVER (unfrozen: the close's witness is a walk) opens it too -- press 1 HUD,
                         # press 2 FullMap -- and only the close's Select keeps F4 / F5 (and the calibration) green
                         "lever": {"kind": "solo", "cal": True, "f6_fail": True},
                         "lever_open": {"kind": "solo", "cal": True, "f6_fail": True, "close_map": False}}})
    assert r["close"]["red"] == ["S144-F3", "S144-F6"], r["close"]["red"]
    assert r["open"]["red"] == ["S144-F3", "S144-F4", "S144-F5", "S144-F6"], r["open"]["red"]
    lever = ["S144-F1", "S144-F1K", "S144-F2", "S144-F3", "S144-F6"]
    assert r["lever"]["red"] == lever, r["lever"]["red"]
    assert r["lever_open"]["red"] == sorted(lever + ["S144-F4", "S144-F5", "S144-CAL"]), r["lever_open"]["red"]


def test_the_instrument_rows_go_red_on_their_own_wrong_shapes():
    """S144-INI: [Netsync] Enabled 1 stops the bench (nothing after it judged, R aside); S144-OR: an oracle problem reds it
    alone (the run goes on); S144-ROUTE: a 6603 with no door never reaches the world map -- every world row 'not reached'."""
    r = _child({"runs": {"ini": {"kind": "solo", "ini": "[Netsync]\nEnabled = 1\n"},
                         "or": {"kind": "solo", "oracle_problems": {"block": "block (18, 12) is overridden"}},
                         "door": {"kind": "solo", "door": False}}})
    ini, orr, door = r["ini"], r["or"], r["door"]
    assert "S144-INI" in ini["red"] and "Enabled '1'" in ini["detail"]["S144-INI"]
    assert set(ini["all"]) - set(ini["red"]) <= {"S144-R"}
    assert orr["red"] == ["S144-OR"] and "overridden" in orr["detail"]["S144-OR"]
    assert "S144-ROUTE" in door["red"]
    assert set(door["red"]) == {"S144-ROUTE", "S144-F0", "S144-F1", "S144-F1K", "S144-F2", "S144-F3", "S144-F6", "S144-F4",
                                "S144-F5", "S144-B1", "S144-B2", "S144-B3"}, door["red"]
    assert all("not reached" in door["detail"][c] for c in set(door["red"]) - {"S144-ROUTE"})


# ------------------------------------------------------------------------------------------------ the T2 legs
REJOIN_ALL = ["T2-TAPE", "T2-CAL", "S144-RJ-PARK", "S144-RJ-I", "T2-PEER", "S144-RJ-DIAL", "S144-RJ-ARM", "S144-RJ-LAND",
              "S144-RJ-MIRROR", "T2-SAVE", "T2-INI"]


def test_the_rejoin_leg_is_green_on_s144_and_calibrates_on_s143(tables):
    """Both park paths: ENSURE (no client before the edit: the world load's Ensure births it on the world map) and POLL (a
    client exists: the park config, then the code alone on the world HUD) -- green on s144, exactly T2_PREDICTED red on the
    s143 stand-in (its client is never Ensured on the world map, or its world-read code meets a dial gate that needs a
    field), the instrument rows green on both."""
    r = _child({"runs": {"s144": {"kind": "t2", "leg": "rejoin"},
                         "s144poll": {"kind": "t2", "leg": "rejoin", "instance": True},
                         "s144cal": {"kind": "t2", "leg": "rejoin", "cal": True},
                         "s143": {"kind": "t2", "leg": "rejoin", "caps": "leaderguard", "cal": True},
                         "s143poll": {"kind": "t2", "leg": "rejoin", "caps": "leaderguard", "cal": True, "instance": True}}})
    for name in ("s144", "s144poll"):
        new = r[name]
        assert new["red"] == [], (name, {c: new["detail"][c] for c in new["red"]})
        assert new["all"] == REJOIN_ALL, (name, new["all"])
        d = new["detail"]
        assert "the guest on WorldHUD at the dial" in d["S144-RJ-DIAL"] and "'rejoining' 250" in d["S144-RJ-ARM"]
        assert "the config line after the walk" in d["S144-RJ-DIAL"] and "the relay up after the walk" in d["S144-RJ-DIAL"]
        assert "FieldHUD 250 on" in d["S144-RJ-LAND"] and "['0xa5']" in d["S144-RJ-MIRROR"]
    assert r["s144"]["detail"]["S144-RJ-PARK"].startswith("ENSURE") and r["s144poll"]["detail"]["S144-RJ-PARK"].startswith("POLL")
    assert "'no_code'" in r["s144poll"]["detail"]["S144-RJ-PARK"]
    # [review 2] the POLL runs carried the owner's transport retrying 49201 up to the park (and its in-flight attempt after it):
    # RJ-PARK stays green above and the s143 calibration below stays exact -- the judge reads the bench's own dial only
    assert r["s144poll"]["owner_lines"] >= 2 and r["s143poll"]["owner_lines"] >= 2, (r["s144poll"].get("owner_lines"),
                                                                                    r["s143poll"].get("owner_lines"))
    assert r["s144cal"]["red"] == [] and "S144-RJ-CAL" in r["s144cal"]["all"]          # s144 predicts no red
    for name in ("s143", "s143poll"):
        s143 = r[name]
        assert s143["red"] == sorted(tables["t2_pred"]["rejoin"]), (name, s143["red"])
        assert "S144-RJ-CAL" in s143["all"] and "no guest connection" in s143["detail"]["S144-RJ-DIAL"]
        assert "('WorldHUD', 9011)" in s143["detail"]["S144-RJ-LAND"]                   # it STAYS on the world map
    assert "the config line never" in r["s143"]["detail"]["S144-RJ-DIAL"]             # ENSURE: nothing read the ini
    assert "the config line after the walk" in r["s143poll"]["detail"]["S144-RJ-DIAL"]  # POLL: read, never dialled
    assert "the relay never up" in r["s143poll"]["detail"]["S144-RJ-DIAL"]


def test_the_rejoin_legs_old_order_dials_on_the_field_and_reads_red():
    """rejoin-t2-dial-cannot-fail: s144-as-built's order (the code applied on 6603 with a field reload, THEN the walk out)
    births the transport on the FIELD; it survives the walk and connects from the world HUD on the s143 stand-in too -- the
    peer connected, the replay started, the guest on WorldHUD at the dial: everything the old RJ-DIAL asked. The rows
    now read it: RJ-PARK (the instrument) names the field-side config line, and RJ-DIAL is red on its stamps."""
    r = _run("t2", leg="rejoin", caps="leaderguard", old_order=True)
    d = r["detail"]
    assert "S144-RJ-PARK" in r["red"] and "config lines before the walk" in d["S144-RJ-PARK"], d["S144-RJ-PARK"]
    assert not d["S144-RJ-PARK"].split("config lines before the walk ")[1].startswith("none")
    assert "GUEST connected" in d["S144-RJ-DIAL"] and "REPLAY start" in d["S144-RJ-DIAL"]       # the old judge's inputs:
    assert "the guest on WorldHUD at the dial" in d["S144-RJ-DIAL"]                             # all green on s143
    assert "S144-RJ-DIAL" in r["red"] and "the config line BEFORE the walk" in d["S144-RJ-DIAL"]   # the new judge: red


def test_the_wait_leg_reads_the_tapes_b6_and_calibrates_on_s143(tables):
    r = _child({"runs": {"b6": {"kind": "t2", "leg": "wait"},
                         "old": {"kind": "t2", "leg": "wait", "b6": False},
                         "s143": {"kind": "t2", "leg": "wait", "caps": "leaderguard", "cal": True}}})
    b6, old, s143 = r["b6"], r["old"], r["s143"]
    for x in (b6, old):
        assert x["red"] == [], {c: x["detail"][c] for c in x["red"]}
        assert x["all"] == ["T2-TAPE", "T2-PEER", "S144-WT-I", "S144-WT-FIELD", "S144-WT-FROZEN", "S144-WT-WORLD",
                            "T2-SAVE", "T2-INI"]
    assert "'host_world'" in b6["detail"]["S144-WT-FIELD"] and "released by b6 1x" in b6["detail"]["S144-WT-WORLD"]
    assert "'host_away'" in old["detail"]["S144-WT-FIELD"] and "fallback True" in old["detail"]["S144-WT-WORLD"]
    assert "b6: True" in b6["detail"]["T2-TAPE"] and "b6: False" in old["detail"]["T2-TAPE"]
    assert s143["red"] == sorted(tables["t2_pred"]["wait"]), s143["red"]
    assert "S144-WT-CAL" in s143["all"] and "S144-WT-I" not in s143["red"]       # the pairing is any engine's


@pytest.mark.parametrize("leg,fault", [("rejoin", f) for f in FG.WORLD_FAULTS] +
                         [("wait", f) for f in ("tail_s143", "line_s143", "dispatch_ungated", "counters_dark",
                                                "hold_unlatched", "rejoin_field_recipe", "keys_unmasked", "fullmap_open")])
def test_each_world_fault_turns_exactly_its_t2_rows_red(tables, leg, fault):
    want = sorted(tables["t2_faults"][leg].get(fault, ()))
    r = _run("t2", leg=leg, faults=[fault])
    assert r["red"] == want, (r["red"], {c: r["detail"][c] for c in set(r["red"]) ^ set(want)})


def test_the_t2_legs_refuse_before_any_edit():
    """No tape -> T2-TAPE red, nothing edited (T2-INI 'never edited'); a world stay too short for the wait plan -> T2-TAPE
    red CANNOT; a field tape with no CAL verdict -> T2-CAL red, the leg 'not reached'; the owner's port 49201 -> T2-PEER red
    before the ini."""
    r = _child({"runs": {"none": {"kind": "t2", "leg": "rejoin", "tape": "none"},
                         "short": {"kind": "t2", "leg": "wait", "world_s": 30.0},
                         "nocal": {"kind": "t2", "leg": "rejoin", "cal_sidecar": False},
                         "ownerup": {"kind": "t2", "leg": "rejoin", "owner_up": True},
                         "owner": {"kind": "t2", "leg": "wait", "port": 49201}}})
    for name in ("none", "short", "nocal", "ownerup", "owner"):
        x = r[name]
        assert "never edited" in x["detail"]["T2-INI"], (name, x["detail"].get("T2-INI"))
        assert "T2-INI" not in x["red"] and "T2-SAVE" not in x["red"]
    assert "T2-TAPE" in r["none"]["red"] and "no tape" in r["none"]["detail"]["T2-TAPE"]
    assert "CANNOT" in r["short"]["detail"]["T2-TAPE"] and "COOP_TAPE_WORLD_S" in r["short"]["detail"]["T2-TAPE"]
    assert "T2-CAL" in r["nocal"]["red"] and "S144-RJ-LAND" in r["nocal"]["red"]
    assert "not reached" in r["nocal"]["detail"]["S144-RJ-LAND"]
    assert "T2-PEER" in r["owner"]["red"] and "owner's bridge port" in r["owner"]["detail"]["T2-PEER"]
    # [review 2] THE PRECONDITION enforced: the owner's own bridge up on 49201 -> T2-PEER red, nothing edited, the leg unreached
    up = r["ownerup"]
    assert "T2-PEER" in up["red"] and "the owner's bridge is UP on 127.0.0.1:49201" in up["detail"]["T2-PEER"], up["detail"]
    assert "S144-RJ-PARK" in up["red"] and "not reached" in up["detail"]["S144-RJ-PARK"]


# ------------------------------------------------------------------------------------------------ the duo leg
def test_the_duo_leg_is_green_on_s144_and_calibrates_on_s143(tables):
    r = _child({"runs": {"s144": {"kind": "duo"}, "s143": {"kind": "duo", "caps": "leaderguard", "cal": True}}})
    new, s143 = r["s144"], r["s143"]
    assert new["red"] == [] and new["all"] == ["S144-D0", "S144-D1", "S144-D2", "S144-D3"], new
    assert new["strict"] is True                                         # strict mode restored
    assert "'host_world'" in new["detail"]["S144-D1"] and "FieldHUD 300 on" in new["detail"]["S144-D3"]
    # the host's MAPJUMP intent rode the Link (as in game) and the guest was sampled INSIDE its armed window: the overlay judged
    assert new["intent"] == [1, 300] and "sample(s) inside the armed window" in new["detail"]["S144-D3"], new["detail"]
    assert "'rejoining' 300" in new["detail"]["S144-D3"] and "shown" in new["detail"]["S144-D3"]
    assert s143["red"] == sorted(tables["duo_pred"]) and "S144-D-CAL" in s143["all"], s143["red"]


def test_d3_keeps_the_bracket_law_under_a_sampler_that_misses_the_arm():
    """S144-D3 in game (s144's first duo): the host's MAPJUMP intent armed the guest at once, and the arm-to-fade window was
    shorter than one sample -- every row of the rejoin held but 'the overlay NOT shown'. Reproduced here with a sampler that
    never reads inside the armed window (Coarse): the STRICT judge (the overlay always required) reds it exactly as in game;
    THE BRACKET LAW greens it, saying 'overlay window shorter than a sample', on the engine's line, `arms` and the landing --
    and still reds a guest that NEVER arms (`rejoin_unarmed`: no line, `arms` +0, never on 300). Its cost, named: with no
    sample inside, the world chain's absence (`line_s143`) is D2's red alone (the fine-sampled run reds D3 too)."""
    r = _child({"runs": {"coarse": {"kind": "duo", "coarse": True},
                         "strict": {"kind": "duo", "coarse": True, "strict_d3": True},
                         "never": {"kind": "duo", "coarse": True, "faults": ["rejoin_unarmed"]},
                         "line": {"kind": "duo", "coarse": True, "faults": ["line_s143"]}}})
    c = r["coarse"]
    assert c["red"] == [], {k: c["detail"][k] for k in c["red"]}
    assert "overlay window shorter than a sample" in c["detail"]["S144-D3"] and c["lands"] == 1, c["detail"]["S144-D3"]
    s = r["strict"]
    assert s["red"] == ["S144-D3"] and "NOT shown" in s["detail"]["S144-D3"], s["detail"]["S144-D3"]
    assert "lands +1" in s["detail"]["S144-D3"] and "the rejoining line 1x" in s["detail"]["S144-D3"]   # all else held
    n = r["never"]
    assert n["red"] == ["S144-D3"] and "arms +0" in n["detail"]["S144-D3"], n["detail"]["S144-D3"]
    assert "the rejoining line 0x" in n["detail"]["S144-D3"] and n["lands"] == 0
    assert r["line"]["red"] == ["S144-D2"], r["line"]["red"]


@pytest.mark.parametrize("fault", sorted(set(FG.WORLD_FAULTS) & {"tail_s143", "dispatch_ungated", "line_s143",
                                                                   "hold_unlatched", "counters_dark",
                                                                   "rejoin_field_recipe", "arm_uncounted",
                                                                   "rejoin_departed", "keys_unmasked", "rejoin_unarmed"}))
def test_each_world_fault_turns_exactly_its_duo_rows_red(tables, fault):
    want = sorted(tables["duo_faults"].get(fault, ()))
    r = _run("duo", faults=[fault])
    assert r["red"] == want, (r["red"], {c: r["detail"][c] for c in set(r["red"]) ^ set(want)})


# ------------------------------------------------------------------------------------------------ the world recorder
def test_the_world_recorder_tapes_the_host_and_its_b6_is_the_engines(tables):
    """COOP_TAPE_WORLD=1 on the stand-in: newgame -> 6603 -> the walk out -> WORLD_S on the world map, every REC row green,
    the tape named `-world-` in its own dir with latest-world.json (never latest.json), on the PRIVATE port; its b6 (the
    stub serve-guest tapes the stand-in host's own states) reads `where --want world` on s144 and `--want none` on s143.
    [ff9mapkit netsync s145] BY STAGE: the s144 run is the s144 stand-in (the ladder through `worldwait`); the default
    stand-in is s145 now, and a world tape is named by the host's own stage -- `-s145` there (the wire it records is s144's)."""
    r = _child({"runs": {"s144": {"kind": "rec", "caps": "worldwait", "env": {"COOP_TAPE_WORLD": "1"}},
                         "s145": {"kind": "rec", "env": {"COOP_TAPE_WORLD": "1"}},
                         "s143": {"kind": "rec", "caps": "leaderguard", "env": {"COOP_TAPE_WORLD": "1"}}}})
    for name, x in r.items():
        assert x["red"] == [], (name, {c: x["detail"][c] for c in x["red"]})
        assert set(x["all"]) == set(tables["rec"]["world"]), (name, x["all"])
        assert len(x["tapes"]) == 1 and "-host6603-world-" in x["tapes"][0] and x["pointer"] and not x["latest"]
        assert x["port"] == 49231
    assert r["s144"]["where"] == {"world": True, "none": False} and r["s144"]["tapes"][0].endswith("-s144.f9tape")
    assert r["s145"]["where"] == {"world": True, "none": False} and r["s145"]["tapes"][0].endswith("-s145.f9tape")
    assert r["s143"]["where"] == {"world": False, "none": True}


# ------------------------------------------------------------------------------------------------ the pure judges
_JUDGES = r'''
import importlib.util, json, os, sys
scen, tools, kit = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
from harness.channel import State
from harness import battlewire as BW
spec = importlib.util.spec_from_file_location("coop_world_wait", os.path.join(scen, "coop_world_wait.py"))
cw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cw)
pb = cw.pb
_n = [0]
def st(ui="WorldHUD", field=6603, world=9011, x=68.0, z=-444.0, freeze=None, rejoin=None, waitline=None, follow=None,
       session=None, bench=True, next_mode=None, epoch=0, overlay_text=False, flags=None):
    _n[0] += 1
    d = {"frame": _n[0], "ui_state": ui, "field": {"id": field}, "world": {"id": world, "x": x, "z": z},
         "battle": {"epoch": epoch}, "netsync": {"bench": bench, "session": dict(session or {})}}
    if next_mode is not None:
        d["world"]["next_mode"] = next_mode
    if freeze is not None or rejoin is not None or waitline is not None:
        d["netsync"]["world"] = {"freeze": dict(BW.WORLD_FREEZE_SENTINELS, **(freeze or {})),
                                 "rejoin": dict(BW.WORLD_REJOIN_SENTINELS, **(rejoin or {})),
                                 "waitline": dict(BW.WORLD_WAITLINE_SENTINELS, **(waitline or {}))}
    if follow is not None:
        d["netsync"]["session"]["follow"] = dict(BW.SESSION_FOLLOW_SENTINELS, **follow)
    if overlay_text is not False:
        d["netsync"]["session"]["overlay_text"] = overlay_text
    if flags is not None:
        d["flags"] = flags
    return State(d)
L = lambda *msgs: ["20.10.2026 12:00:00 |M| [NetSync] " + m for m in msgs]
out = {}
proof = L(*(f"{h}OK ({n} rows)" for h, n in ((BW.PROOF_WORLD_FREEZE, BW.WORLD_FREEZE_SELFTEST_ROWS),
                                               (BW.PROOF_WORLD_REJOIN, BW.WORLD_REJOIN_SELFTEST_ROWS),
                                               (BW.PROOF_OVERLAY_TEXT, BW.OVERLAY_TEXT_SELFTEST_ROWS))))
full = st(freeze={}, follow={}, overlay_text=None)
out["probe"] = [cw.judge_probe(full, proof)[0], cw.judge_probe(st(), proof)[0], cw.judge_probe(full, proof[:2])[0],
                cw.judge_probe(full, proof + L(BW.PROOF_WORLD_FREEZE + "FAIL (row 3)"))[0],
                cw.judge_probe(st(freeze={}, follow={}), proof)[0]]
out["rest"] = [cw.judge_rest(st(freeze={}), lever=False)[0], cw.judge_rest(st(freeze={"off": True}), lever=False)[0],
               cw.judge_rest(st(freeze={}, bench=False), lever=False)[0], cw.judge_rest(st(), lever=False)[0],
               cw.judge_rest(st(freeze={"off": True}), lever=True)[0]]
out["route"] = [cw.judge_route(st())[0], cw.judge_route(st(world=9000))[0], cw.judge_route(st(x=90.0))[0],
                cw.judge_route(st(ui="FieldHUD"))[0]]
hl = L(BW.log_world_hold_latched(6603, 9011))
out["hold"] = [cw.judge_hold(st(follow={"hold": 6603}), hl)[0], cw.judge_hold(st(follow={"hold": -1}), hl)[0],
               cw.judge_hold(st(follow={"hold": 6603}), hl + hl)[0], cw.judge_hold(st(follow={"hold": 6603}), [])[0],
               cw.judge_hold(st(), hl)[0]]
out["walk"] = [cw.judge_walk(0.5, 40, 30, held=True)[0], cw.judge_walk(3.0, 40, 30, held=True)[0],
               cw.judge_walk(0.5, 20, 30, held=True)[0], cw.judge_walk(5.0, 40, 30, held=False)[0],
               cw.judge_walk(1.0, 40, 30, held=False)[0], cw.judge_walk(None, None, 30, held=True)[1][:12]]
base = st(freeze={"skips": 10, "edges": 2})
on = L(BW.log_world_freeze_on("bench", 9011))
good = st(freeze={"on": True, "why": "bench", "skips": 30, "edges": 3})
out["keys"] = [cw.judge_freeze_keys(good, base, on)[0],
               cw.judge_freeze_keys(st(freeze={"on": True, "why": "live", "skips": 30, "edges": 3}), base, on)[0],
               cw.judge_freeze_keys(st(freeze={"on": True, "why": "bench", "skips": 12, "edges": 3}), base, on)[0],
               cw.judge_freeze_keys(st(freeze={"on": True, "why": "bench", "skips": 30, "edges": 4}), base, on)[0],
               cw.judge_freeze_keys(good, base, on + on)[0], cw.judge_freeze_keys(st(), base, on)[0]]
stay = [st() for _ in range(3)]
poll = L(BW.decline_line(BW.WORLD_POLL_DECLINE, "world map 9011"))
out["confirm"] = [cw.judge_confirm(stay, 0, 1, poll)[0], cw.judge_confirm(stay, 0, 0, poll)[0],
                  cw.judge_confirm(stay + [st(ui="FieldHUD", field=300)], 0, 1, poll)[0],
                  cw.judge_confirm(stay, 0, 1, [])[0], cw.judge_confirm(stay, None, None, poll)[0],
                  cw.judge_confirm(stay, 2, 2, (), want_keys=False)[0], cw.judge_confirm(stay, 2, 3, (), want_keys=False)[0]]
m0 = st(freeze={"map": 0, "skips": 100})
win = [st(freeze={"map": 1, "skips": 104 + 4 * i}) for i in range(3)]
ml = L(BW.decline_line(BW.WORLD_UI_DECLINE_MAP, "world map 9011"))
# [the stock cycle] press 1 from HUDNoMiniMap turned the minimap on (map +0, the dispatcher asked), press 2 refused
mini = [st(freeze={"map": 0, "skips": 110 + 4 * i}) for i in range(3)]
ref2 = [st(freeze={"map": 1, "skips": 124 + 4 * i}) for i in range(3)]
open2 = [st(freeze={"map": 0, "skips": 124 + min(i, 1)}) for i in range(3)]   # press 2 OPENED it: +1 (the key's tick), then none
out["map"] = [cw.judge_map(m0, [win], [st()], ml)[0], cw.judge_map(m0, [[st(freeze={"map": 0, "skips": 110})]], [], ml)[0],
              cw.judge_map(m0, [[st(freeze={"map": 1, "skips": 101})]], [], ml)[0], cw.judge_map(m0, [win], [], [])[0],
              cw.judge_map(m0, [win], [st(ui="FieldHUD")], ml)[0], cw.judge_map(m0, [win], [st(x=80.0)], ml)[0],
              cw.judge_map(m0, [], [], ml)[1][:12],
              cw.judge_map(m0, [mini, ref2], [st()], ml)[0],                   # two presses, the second refused: green
              cw.judge_map(m0, [mini, open2], [st()], ml)[0],                  # the second opened the map
              cw.judge_map(m0, [mini, mini], [st()], ml)[0],                   # two presses, never refused
              cw.judge_map(m0, [mini, ref2, ref2], [st()], ml)[0],             # a third press: outside the drive
              cw.judge_map(m0, [mini, ref2], [st()], ml + ml)[0],              # the line twice (the latch broke)
              cw.judge_map(m0, [mini, []], [st()], ml)[1][:12],
              cw.judge_map(st(), [mini], [], ml)[1][:7],                       # an engine without the keys
              "the dispatcher NOT asked after press 2" in cw.judge_map(m0, [mini, open2], [], ml)[1],
              "map +0 (the refusal never counted)" in cw.judge_map(m0, [mini, mini], [], ml)[1]]
# F3's drive: a second Select only when `map` did not count and the map did not witnessably open
fz = lambda **k: st(freeze=dict({"on": True}, **k))
out["again"] = [cw.select_again(m0, [fz(map=0, skips=104), fz(map=0, skips=110)]),   # frozen, asked: the minimap came on
                cw.select_again(m0, [fz(map=1, skips=104), fz(map=1, skips=110)]),   # refused: done
                cw.select_again(m0, [fz(map=0, skips=104), fz(map=0, skips=105)]),   # frozen, the dispatcher stopped: opened
                cw.select_again(m0, [st(freeze={"on": False, "map": 0, "skips": 100})]),   # unfrozen: no witness, stock
                cw.select_again(st(), [st()]),                         # no keys (s143): stock
                cw.select_again(m0, []),
                # the settle-to-press ticks never count as "asked": the skips before the window are the press latency's
                cw.select_again(st(freeze={"map": 0, "skips": 90}), [fz(map=0, skips=100), fz(map=0, skips=100)])]
# THE BRACKET LAW (D3): the overlay judged only when a sample fell inside the armed window
w_in = st(rejoin={"arms": 3, "last": 300}, follow={"world_armed": 300},
          session={"overlay": "rejoining", "overlay_detail": 300, "overlay_text": BW.wait_line_text(BW.OVL_REJOINING, 300)})
w_in_dark = st(rejoin={"arms": 3, "last": 300}, follow={"world_armed": 300}, session={"overlay": "off"})
w_pre = st(rejoin={"arms": 2, "last": -1}, follow={"world_armed": -1}, session={"overlay": "host_world"})
f_land = st(ui="FieldHUD", field=300, rejoin={"arms": 3, "last": 300, "lands": 2}, follow={"world_armed": -1})
f_none = st(ui="WorldHUD", rejoin={"arms": 2, "last": -1, "lands": 1}, follow={"world_armed": -1})
rb3 = st(rejoin={"arms": 2, "lands": 1})
rl3 = L(BW.log_world_rejoining(300, 9011, True), BW.log_world_rejoin_landed(300, 300, 900))
out["bracket"] = [cw.judge_rejoin_arm([w_pre, f_land], rb3, rl3, field=300, bracket=True)[0],      # no sample inside: green
                  "overlay window shorter than a sample" in cw.judge_rejoin_arm([w_pre, f_land], rb3, rl3, field=300,
                                                                                bracket=True)[1],
                  cw.judge_rejoin_arm([w_pre, f_land], rb3, rl3, field=300)[0],                     # strict: red (in game)
                  cw.judge_rejoin_arm([w_pre, w_in_dark, f_land], rb3, rl3, field=300, bracket=True)[0],   # inside, unshown
                  cw.judge_rejoin_arm([w_pre, w_in, f_land], rb3, rl3, field=300, bracket=True)[0],        # inside, shown
                  cw.judge_rejoin_arm([w_pre, f_none], rb3, [], field=300, bracket=True)[0],               # never armed
                  cw.judge_rejoin_arm([w_pre, f_land], rb3, [], field=300, bracket=True)[0],               # no line
                  cw.judge_rejoin_arm([w_pre, f_land], st(rejoin={"arms": 3, "lands": 1}), rl3, field=300,
                                      bracket=True)[0],                                                     # arms +0
                  cw.judge_rejoin_arm([w_pre, st(rejoin={"arms": 3, "last": 300}, follow={"world_armed": -1})], rb3, rl3,
                                      field=300, bracket=True)[0],                                          # never landed
                  cw.in_armed_window(w_in), cw.in_armed_window(w_pre), cw.in_armed_window(f_land),
                  cw.in_armed_window(st(ui="FieldHUD", follow={"world_armed": 300}))]
# [review N4] the overlay is required AMONG the samples inside the window: a pre-arm 'rejoining' (WorldGuestOverlay shows it
# off the host's lane alone) never stands in for an inside sample that showed something else; RJ-ARM's strict read (bracket
# off) still takes any sample
w_pre_shown = st(rejoin={"arms": 2, "last": -1}, follow={"world_armed": -1},
                 session={"overlay": "rejoining", "overlay_detail": 300,
                          "overlay_text": BW.wait_line_text(BW.OVL_REJOINING, 300)})
out["bracket_scope"] = [cw.judge_rejoin_arm([w_pre_shown, w_in_dark, f_land], rb3, rl3, field=300, bracket=True)[0],
                        cw.judge_rejoin_arm([w_pre_shown, w_in_dark, f_land], rb3, rl3, field=300)[0],
                        cw.judge_rejoin_arm([w_pre_shown, w_in, f_land], rb3, rl3, field=300, bracket=True)[0]]
# THE CLOSE (review N2): a scripted witness against WorldHUD's stock cycle, unfrozen -- the close never presses three times
# (the cycle's identity), and a DARK witness (no reading) gets one blind Select at most
CYCLE = {"HUD": "FullMap", "FullMap": "HUDNoMiniMap", "HUDNoMiniMap": "HUD"}
class CloseG:
    def __init__(self, hud):
        self.hud, self.presses, self.notes = hud, 0, []
    def press(self, button):
        assert button == "select", button
        self.presses += 1
        self.hud = CYCLE[self.hud]
    def wait_frames(self, n):
        pass
    def note(self, msg):
        self.notes.append(msg)
def close_with(hud, witness):
    """witness(g, i) -> shut True / False / None (dark) at the i-th read"""
    g, reads = CloseG(hud), [0]
    def shut(_g):
        i = reads[0]
        reads[0] += 1
        v = witness(g, i)
        return v, {True: "read shut", False: "read open", None: "read nothing (the witness dark)"}[v]
    real, cw.map_shut = cw.map_shut, shut
    try:
        trail = cw.close_opened_map(g)
    finally:
        cw.map_shut = real
    return [g.presses, g.hud, trail]
true_w = lambda g, i: g.hud != "FullMap"
out["close"] = [close_with("FullMap", true_w)[:2],                         # a true witness: one Select shuts it
                close_with("HUD", true_w)[:2],                             # shut: no press
                close_with("FullMap", lambda g, i: False)[:2],             # STUCK (reads open forever): two, never three --
                close_with("HUDNoMiniMap", lambda g, i: None)[:2],         # DARK: one blind Select, then the close stops
                close_with("FullMap", lambda g, i: None)[:2],              # ... which shuts the likeliest open end
                close_with("FullMap", lambda g, i: None if i == 0 else g.hud != "FullMap")[:2],   # dark, then shut
                "the map had OPENED: shut by 1 Select(s)" in close_with("FullMap", true_w)[2],
                "UNKNOWN after 1 blind Select(s)" in close_with("FullMap", lambda g, i: None)[2],
                "NOT witnessed shut after 2 Select(s)" in close_with("FullMap", lambda g, i: False)[2],
                "shut after 1 blind Select(s)" in close_with("FullMap", lambda g, i: None if i == 0 else g.hud != "FullMap")[2],
                "the map was shut" in close_with("HUD", true_w)[2], cw.CLOSE_PRESSES]
out["edge"] = [cw.judge_edge(st(freeze={"edges": 1}), st(freeze={"edges": 2}), 0.0, 20)[0],
               cw.judge_edge(st(freeze={"edges": 1}), st(freeze={"edges": 1}), 0.0, 20)[0],
               cw.judge_edge(st(freeze={"edges": 1}), st(freeze={"edges": 2}), 9.0, 20)[0]]
out["lever"] = [cw.judge_lever(st(freeze={"on": False, "off": True}))[0], cw.judge_lever(st(freeze={"on": True, "off": True}))[0],
                cw.judge_lever(st(freeze={"on": False, "off": False}))[0], cw.judge_lever(st())[0]]
started = BW.world_battle_started(67, 0, True, 9011)
bl = L(started)
bst = st(ui="BattleHUD", epoch=5)
out["battle"] = [cw.judge_battle_start(bst, 4, [started], bl)[0], cw.judge_battle_start(bst, 5, [started], bl)[0],
                 cw.judge_battle_start(st(epoch=5), 4, [started], bl)[0], cw.judge_battle_start(bst, 4, [None], bl)[0],
                 cw.judge_battle_start(bst, 4, [started], [])[0]]
out["swirl"] = [cw.judge_swirl([st(next_mode=3, rejoin={"latch": False}), st(next_mode=2, rejoin={"latch": True})])[0],
                cw.judge_swirl([st(next_mode=2, rejoin={"latch": False})])[0], cw.judge_swirl([st(next_mode=3)])[0],
                cw.judge_swirl([st(next_mode=3), st(next_mode=-1)])[1][:12],
                cw.judge_swirl([st(next_mode=3), st(next_mode=1)])[1][:12]]
import datetime as _dt
T = lambda s: _dt.datetime(2026, 10, 20, 12, 0, s)
began = _dt.datetime(2026, 10, 20, 12, 0, 3, 500000)
cfg_msg = f"[NetSync] config enabled=True role=client field=0 followHost=1 relay=ws://127.0.0.1:{cw.PORT} code={cw.CODE}"
park_msg = f"[NetSync] config enabled=True role=client field=0 followHost=1 relay=ws://127.0.0.1:{cw.PORT} code="
relay_msg = f"[NetSync] relay connected ws://127.0.0.1:{cw.PORT}/sess/{cw.CODE}?role=guest"
out["park"] = [cw.judge_park("ensure", [], before=began, overlay=None)[0],
               cw.judge_park("ensure", [(T(5), "M", cfg_msg)], before=began, overlay=None)[0],
               cw.judge_park("ensure", [(T(2), "M", cfg_msg)], before=began, overlay=None)[0],
               cw.judge_park("poll", [(T(1), "M", park_msg)], before=began, overlay="no_code")[0],
               cw.judge_park("poll", [(T(1), "M", park_msg)], before=began, overlay=None)[0],
               cw.judge_park("poll", [(T(1), "M", park_msg), (T(2), "M", relay_msg)], before=began, overlay="no_code")[0],
               cw.judge_park("poll", [(T(1), "M", park_msg), (T(2), "M", cfg_msg)], before=began, overlay="no_code")[0]]
own_fail = ("[NetSync] relay connect to 127.0.0.1:49201 failed (No connection could be made because the target machine "
            "actively refused it.)")
own_up = "[NetSync] relay connected ws://127.0.0.1:49201/sess/ff9-0CA62LRC?role=host"
bench_fail = f"[NetSync] relay connect to 127.0.0.1:{cw.PORT} failed (refused)"
code_up = f"[NetSync] relay connected ws://127.0.0.1:49999/sess/{cw.CODE}?role=guest"
out["park_owner"] = [
    cw.judge_park("poll", [(T(1), "M", own_fail), (T(1), "M", park_msg), (T(2), "M", own_fail)], before=began, overlay="no_code")[0],
    cw.judge_park("poll", [(T(1), "M", park_msg), (T(2), "M", own_up)], before=began, overlay="no_code")[0],
    cw.judge_park("ensure", [(T(2), "M", own_fail)], before=began, overlay=None)[0],
    cw.judge_park("poll", [(T(1), "M", park_msg), (T(2), "M", bench_fail)], before=began, overlay="no_code")[0],
    cw.judge_park("poll", [(T(1), "M", park_msg), (T(2), "M", code_up)], before=began, overlay="no_code")[0],
    cw.judge_park("ensure", [(T(2), "M", bench_fail)], before=began, overlay=None)[0],
    bool(cw._RELAY_DIAL.search(own_fail)) and not cw.bench_dial(own_fail) and cw.bench_dial(bench_fail) and cw.bench_dial(code_up),
    "1 of another endpoint's transport ignored" in cw.judge_park("poll", [(T(1), "M", park_msg), (T(2), "M", own_fail)],
                                                                before=began, overlay="no_code")[1]]
cfg = pb.hits([(T(5), "M", cfg_msg)], "config")
rel = pb.hits([(T(6), "M", relay_msg)], "relay_up")
w = [st(), st()]
out["dial"] = [cw.judge_dial(T(6), T(6), cfg, rel, w, began=began)[0],
               cw.judge_dial(None, T(6), cfg, rel, w, began=began)[0],
               cw.judge_dial(T(6), None, cfg, rel, w, began=began)[0],
               cw.judge_dial(T(6), T(6), [], rel, w, began=began)[0],
               cw.judge_dial(T(6), T(6), pb.hits([(T(2), "M", cfg_msg)], "config"), rel, w, began=began)[0],
               cw.judge_dial(T(6), T(6), cfg, pb.hits([(T(2), "M", relay_msg)], "relay_up"), w, began=began)[0],
               cw.judge_dial(T(6), T(6), cfg, rel, w + [st(ui="FieldHUD")], began=began)[0],
               cw.judge_dial(T(6), T(6), cfg, rel, [], began=began)[0]]
out["return"] = [cw.judge_return(st(next_mode=3), (68.0, -444.0))[0], cw.judge_return(st(next_mode=3, x=75.0), (68.0, -444.0))[0],
                 cw.judge_return(st(ui="FieldHUD", next_mode=3), (68.0, -444.0))[0],
                 cw.judge_return(st(next_mode=2), (68.0, -444.0))[0], cw.judge_return(st(world=9000, next_mode=3), (68.0, -444.0))[0]]
hw = dict(session={"overlay": "host_world", "overlay_text": BW.WAIT_TEXT_HOST_WORLD}, waitline={"line": "host_world"},
          follow={"host_world": True})
aw = dict(session={"overlay": "host_away", "overlay_text": BW.WAIT_TEXT_HOST_AWAY}, waitline={"line": "away", "fallback": True},
          follow={"host_world": False})
out["line"] = [cw.judge_line(st(**hw), b6=True)[0], cw.judge_line(st(**aw), b6=False)[0], cw.judge_line(st(**aw), b6=True)[0],
               cw.judge_line(st(**hw), b6=False)[0],
               cw.judge_line(st(**dict(hw, session={"overlay": "host_world", "overlay_text": "x"})), b6=True)[0],
               cw.judge_line(st(**dict(hw, follow={"host_world": False})), b6=True)[0],
               cw.judge_line(st(**dict(aw, waitline={"line": "away", "fallback": False})), b6=False)[0],
               cw.judge_line(st(session={"overlay": "waiting"}), b6=True)[0]]
fb = st(freeze={"skips": 0})
out["frozen"] = [cw.judge_frozen(st(freeze={"on": True, "why": "live", "skips": 30}), 0.0, 40, fb)[0],
                 cw.judge_frozen(st(freeze={"on": True, "why": "mirroring", "skips": 30}), 0.0, 40, fb)[0],
                 cw.judge_frozen(st(freeze={"on": True, "why": "bench", "skips": 30}), 0.0, 40, fb)[0],
                 cw.judge_frozen(st(freeze={"on": True, "why": "live", "skips": 3}), 0.0, 40, fb)[0],
                 cw.judge_frozen(st(freeze={"on": True, "why": "live", "skips": 30}), 5.0, 40, fb)[0],
                 cw.judge_frozen(st(), 0.0, 40, fb)[0]]
rb = st(rejoin={"arms": 2, "lands": 1})
words = BW.wait_line_text(BW.OVL_REJOINING, 250)
arm = st(rejoin={"arms": 3, "last": 250}, session={"overlay": "rejoining", "overlay_detail": 250, "overlay_text": words})
rl = L(BW.log_world_rejoining(250, 9011), BW.log_world_rejoin_landed(250, 250, 800))
out["arm"] = [cw.judge_rejoin_arm([arm], rb, rl, field=250)[0], cw.judge_rejoin_arm([arm], rb, rl, field=300)[0],
              cw.judge_rejoin_arm([st(rejoin={"arms": 2, "last": 250}, session=arm.raw["netsync"]["session"])], rb, rl,
                                  field=250)[0],
              cw.judge_rejoin_arm([st(rejoin={"arms": 3, "last": 250})], rb, rl, field=250)[0],
              cw.judge_rejoin_arm([arm], rb, [], field=250)[0], cw.judge_rejoin_arm([st()], rb, rl, field=250)[0]]
land = st(ui="FieldHUD", field=250, rejoin={"lands": 2}, follow={"world_armed": -1})
out["land"] = [cw.judge_rejoin_land([st(), land], rb, rl, field=250)[0],
               cw.judge_rejoin_land([st(), st(rejoin={"lands": 2}, follow={"world_armed": -1})], rb, rl, field=250)[0],
               cw.judge_rejoin_land([land], st(rejoin={"lands": 2}), rl, field=250)[0],
               cw.judge_rejoin_land([st(ui="FieldHUD", field=250, rejoin={"lands": 2}, follow={"world_armed": 250})], rb, rl,
                                    field=250)[0],
               cw.judge_rejoin_land([land], rb, rl[:1], field=250)[0], cw.judge_rejoin_land([], rb, rl, field=250)[1][:12]]
mark = {str(pb.MARKER_BYTE * 8 + b): bool(pb.MARKER_VALUE >> b & 1) for b in range(8)}
own = {str(pb.MARKER_BYTE * 8 + b): False for b in range(8)}
armed = L("state-mirror ARMED -- this guest's fields now stage the HOST's story")
after = [st(ui="FieldHUD", field=250, session={"mirroring": True}, flags=mark)]
before = [st(session={"mirroring": False}, flags=own)]
out["mirror"] = [cw.judge_mirror(before, after, armed, field=250)[0], cw.judge_mirror(before, after, [], field=250)[0],
                 cw.judge_mirror([st(session={"mirroring": True})], after, armed, field=250)[0],
                 cw.judge_mirror(before, [st(ui="FieldHUD", field=250, session={"mirroring": True}, flags=own)], armed,
                                 field=250)[0],
                 cw.judge_mirror(before, [st(ui="FieldHUD", field=250, session={"mirroring": False}, flags=mark)], armed,
                                 field=250)[0], cw.judge_mirror(before, [], armed, field=250)[0]]
out["stage"] = [cw.stage_of(full), cw.stage_of(st()), cw.stage_of({"netsync": {"battle": {"host": {"guard": {}}}}})]
print(json.dumps(out))
'''


def test_the_judges_go_red_on_each_wrong_shape():
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    run = subprocess.run([sys.executable, "-X", "utf8", "-c", _JUDGES, str(SCENARIOS), str(REPO / "tools"),
                          str(REPO / "ff9mapkit")], env=env, capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr[-3000:]
    o = json.loads(run.stdout.strip().splitlines()[-1])
    assert o["probe"] == [True, False, False, False, False]      # whole / absent / a proof line missing / a FAIL / no text
    assert o["rest"] == [True, False, False, False, True]        # at rest / mis-set / bench off / absent / pulled
    assert o["route"] == [True, False, False, False]             # the landing / another world / 22u off / a field
    assert o["hold"] == [True, False, False, False, False]       # held / none / twice / no line / absent
    assert o["walk"] == [True, False, False, True, False, "not reached:"]
    assert o["keys"] == [True, False, False, False, False, False]
    assert o["confirm"] == [True, False, False, False, False, True, False]
    # one press refused / no count / the dispatcher stopped / no line / left the world map / the walker moved / no sample;
    # [the stock cycle] minimap-then-refused / the second opened / never refused / three presses / the line twice / an empty
    # window / no keys / the stalled press named / the count's absence named
    assert o["map"] == [True, False, False, False, False, False, "not reached:", True, False, False, False, False,
                        "not reached:", "absent:", True, True]
    assert o["again"] == [True, False, False, True, True, False, False]
    # no sample inside -> judged by the line + arms + landing (green, named); the strict read of the same samples: red (the
    # in-game D3); inside unshown -> red; inside shown -> green; never armed / no line / arms +0 / never landed -> red
    assert o["bracket"] == [True, True, False, False, True, False, False, False, False, True, False, False, False]
    # [review N4] inside-window scope: a pre-arm 'rejoining' never greens an inside sample that showed another overlay
    # (bracket), the strict RJ-ARM read still takes any sample, and an inside 'rejoining' greens it
    assert o["bracket_scope"] == [False, True, True]
    # [review N2] THE CLOSE against the stock cycle: a true witness -- one Select from FullMap, none when shut; a STUCK
    # witness -- two Selects from FullMap end in the HUD (three would be the cycle's identity: FullMap again); a DARK
    # witness -- one blind Select, then stop; the trail names each outcome
    assert o["close"] == [[1, "HUDNoMiniMap"], [0, "HUD"], [2, "HUD"], [1, "HUD"], [1, "HUDNoMiniMap"], [1, "HUDNoMiniMap"],
                          True, True, True, True, True, 2]
    assert o["edge"] == [True, False, False]
    assert o["lever"] == [True, False, False, False]
    assert o["battle"] == [True, False, False, False, False]
    assert o["swirl"] == [True, False, False, "not reached:", "2 publish(es"]
    assert o["park"] == [True, True, False, True, False, False, False]   # clean / late cfg / early cfg; poll: parked / no overlay /
    #                                                                       an early relay / an early coded config
    # [review 2] the owner's transport retrying 49201 (refused, or up) is never the bench's dial; the bench's port or its code is
    assert o["park_owner"] == [True, True, True, False, False, False, True, True]
    assert o["dial"] == [True, False, False, False, False, False, False, False]
    assert o["return"] == [True, False, False, False, False]
    assert o["line"] == [True, True, False, False, False, False, False, False]
    assert o["frozen"] == [True, True, False, False, False, False]
    assert o["arm"] == [True, False, False, False, False, False]
    assert o["land"] == [True, False, False, False, False, "not reached:"]
    assert o["mirror"] == [True, False, False, False, False, False]
    assert o["stage"] == [144, 0, 143]


# ------------------------------------------------------------------------------------------------ the oracle
_ORACLE = r'''
import importlib.util, json, os, pathlib, sys
scen, tools, kit = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
spec = importlib.util.spec_from_file_location("coop_world_wait", os.path.join(scen, "coop_world_wait.py"))
cw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cw)
game = pathlib.Path(json.loads(sys.stdin.read())["game"])
o = cw.read_oracle(game)
print(json.dumps({"problems": o["problems"], "exits": o["facts"].get("exits"), "world_eb": o["facts"].get("world_eb"),
                  "evt": cw.deployed_field_eb(game, 6603)[1]}))
'''

_FARSHORE = """[field]
id = 6603
name = "FARSHORE"
area = 31

[camera]
pitch = 40

[walkmesh]
quad = [[-1200, -100], [1200, -100], [1200, -2900], [-1200, -2900]]

[player]
spawn = [900, -1400]

[[gateway]]
zone = [[285, -352], [875, -460], [424, -2944], [-166, -2836]]
to = "worldmap"
arrive = [68.0, -444.0]
arrive_face = 64
"""


def _oracle(game) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    run = subprocess.run([sys.executable, "-X", "utf8", "-c", _ORACLE, str(SCENARIOS), str(REPO / "tools"),
                          str(REPO / "ff9mapkit")], env=env, input=json.dumps({"game": str(game)}), capture_output=True,
                         text=True, timeout=120)
    assert run.returncode == 0, run.stderr[-3000:]
    return json.loads(run.stdout.strip().splitlines()[-1])


def test_the_oracle_reads_a_kit_built_6603_and_names_each_moved_target(tmp_path):
    """A kit-built 6603 with the landing's door (its WorldMap() cascade holds 9011), stacked by FolderNames: CLEAN, the event
    name off the DictionaryPatch line's EVENT column. Then each target moved: a world dispatcher override with no Field(300)
    (WORLD11 swapped for 6603's own script), a block (18,12) override, 6603's script gone -- each named, never green."""
    # the build runs in a CHILD, so what it lacks is a red returncode the conftest's FileNotFoundError -> skip never sees:
    # gate it here. It reads the blank (the templates) AND the install: the worldmap [[gateway]] carries the exit cascade
    # verbatim off the install's event bundle (content/worldexit.cascade_bytes -- real bytes, never shipped)
    from ff9mapkit import provision
    if not provision.templates_present():
        pytest.skip("base templates not extracted (run `ff9mapkit extract-templates`)")
    try:
        from ff9mapkit.extract import EventBundle
        EventBundle()
    except Exception as err:                              # noqa: BLE001 - no install / no UnityPy: either way, no cascade
        pytest.skip(f"needs the FF9 install + UnityPy (a worldmap [[gateway]]'s exit cascade): {type(err).__name__}")
    game = tmp_path / "game"
    game.mkdir()
    toml = tmp_path / "farshore.field.toml"
    toml.write_text(_FARSHORE, encoding="utf-8")
    mod = game / "FF9CustomMap-world"
    r = subprocess.run([sys.executable, "-X", "utf8", "-m", "ff9mapkit", "build", str(toml), "--out", str(mod)],
                       cwd=str(REPO / "ff9mapkit"), capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:] + r.stdout[-2000:]
    (game / "Memoria.ini").write_text('[Mod]\nFolderNames = "FF9CustomMap", "FF9CustomMap-world"\n', encoding="utf-8")
    o = _oracle(game)
    assert o["problems"] == {} and 9011 in o["exits"] and o["world_eb"] == "stock", o
    assert o["evt"].endswith("EVT_FARSHORE.eb.bytes")
    evt = mod / "StreamingAssets" / "assets" / "resources" / "commonasset" / "eventengine" / "eventbinary"
    world = evt / "world" / "us"
    world.mkdir(parents=True)
    (world / "EVT_WORLD_WORLD11.eb.bytes").write_bytes((evt / "field" / "us" / "EVT_FARSHORE.eb.bytes").read_bytes())
    blk = mod / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r1"
    blk.mkdir(parents=True)
    (blk / "Block[18][12] Terrain.ff9mesh").write_bytes(b"x")
    o = _oracle(game)
    assert "Field(300)" in o["problems"]["world eb"] and "block (18, 12) is overridden" in o["problems"]["block"], o
    (evt / "field" / "us" / "EVT_FARSHORE.eb.bytes").unlink()
    o = _oracle(game)
    assert "no stacked mod folder registers it" in o["problems"]["eb 6603"], o
    # rejoin-oracle-fork-300: one stacked fork of 300 moves every world entry into it (ForkSiblingField); two are ambiguous
    # (the engine disables the remap: identity) -- the oracle names only the first
    (mod / "ForkDonorPatch.txt").write_text("# forks\n6300 300\n6250 250\n", encoding="utf-8")
    o = _oracle(game)
    assert "forked by 6300" in o["problems"]["fork"], o
    (game / "FF9CustomMap").mkdir(exist_ok=True)
    (game / "FF9CustomMap" / "ForkDonorPatch.txt").write_text("6301 300\n", encoding="utf-8")
    o = _oracle(game)
    assert "fork" not in o["problems"], o


# ------------------------------------------------------------------------------------------------ the stand-in seams
def test_the_stand_ins_dial_gate_and_its_world_door_on_every_rung(tmp_path):
    """FakeGame.dial_ready (NetSyncClient's dial gate): an enabled client instance dials on a FIELD on every rung, on the
    world HUD only from s144; a 'world' region fires on the s143 stand-in too (the stock WMAPJUMP: the bench calibrates its
    walk out there) and latches no hold there; worldwarp is a field start (the spawn, a new visit)."""
    for caps, world_dials in ((None, True), (FG.caps_through("leaderguard"), False)):
        f = FG.FakeGame(tmp_path / ("a" if caps is None else "b"))
        if caps is not None:
            f.netsync_caps = caps
        assert f.dial_ready() is False                                  # no client instance
        f.netsync.update(enabled=True, role="client", instance=True)
        f.ui_state, f.field_id = "FieldHUD", 6603
        assert f.dial_ready() is True
        f.ui_state = "WorldHUD"
        assert f.dial_ready() is world_dials
        f.ui_state = "BattleHUD"
        assert f.dial_ready() is False
        f.netsync.update(role="host")
        f.ui_state = "FieldHUD"
        assert f.dial_ready() is False
        f.ui_state, f.field_id, f.control, f.player = "FieldHUD", 6603, True, [0.0, 0.0, 0.0]
        f.regions = {6603: [{"zone": [[-10, -10], [10, -10], [10, 10], [-10, 10]], "world": 9011, "world_at": [68.0, -444.0]}]}
        f._enter_regions()                                                # exit_frames 0: the switch at once
        if f._exit is not None:
            f._step_exit_now()
        assert f.ui_state == "WorldHUD" and f.world["id"] == 9011 and f._wj["hold"] == -1
        f.player = [68.0 * 256.0, 0.0, -444.0 * 256.0]                   # the world actor's (world x 256), as a frame leaves it
        visit = f._visit
        f._execute(["worldwarp", "6603"])
        assert f.ui_state == "FieldHUD" and f.field_id == 6603 and f.player == [0.0, 0.0, 0.0] and f._visit == visit + 1


def test_the_stub_transports_say_the_hosts_place_as_host_dialog_flags_does(tmp_path):
    """wire-4: the duo's and the recorder's stub flags come from ONE helper (FakeGame.host_dialog_flags, HostDialogFlags' twin):
    b6 is the STRICT onWorld -- it stays through the host's world main menu (gMode keeps 3: no StartEvents) -- b3 only on a
    live field (a field menu keeps it), b4 any UI but FieldHUD, b5 a battle. A guest fed the host's world menu keeps
    'host_world' past the old-host debounce; s144-as-built's stub (a bare b4 off WorldHUD) dropped it to 'host_away'."""
    host = FG.FakeGame(tmp_path / "h")
    host.ui_state, host.field_id, host.control = "WorldHUD", 6603, True
    host._step_world_coop()
    assert host._wt["gmode"] == 3 and host.host_dialog_flags() & BW.HF_WORLD and host.host_lane_field() == 0
    host.open_menu(["Items"])                                       # its world main menu
    host._step_world_coop()
    f = host.host_dialog_flags()
    assert f & BW.HF_WORLD and f & BW.HF_MENU and not f & BW.HF_ON_FIELD and host._wt["gmode"] == 3
    host.ui_state = "FieldHUD"
    host._wt["gmode"] = 1
    host.open_menu(["Items"])                                       # a FIELD menu: b3 stays, b6 never
    host._step_world_coop()
    f = host.host_dialog_flags()
    assert f & BW.HF_ON_FIELD and f & BW.HF_MENU and not f & BW.HF_WORLD and host.host_lane_field() == 6603
    old = FG.FakeGame(tmp_path / "o")
    old.netsync_caps = FG.caps_through("leaderguard")
    old.ui_state, old._wt["gmode"] = "WorldHUD", 3
    assert not old.host_dialog_flags() & BW.HF_WORLD                # an s143 host says no b6

    def guest_line(flags) -> str:
        g = FG.FakeGame(tmp_path / f"g{flags}")
        g.ui_state, g.field_id = "FieldHUD", 6603
        g.follow_session(0, flags=flags)
        g.rt = 0.0
        for k in range(60):                                         # 6 s of guest ticks, past WAIT_AWAY_MS
            g.rt = k * 0.1
            g._client_tick(False)
        return BW.wait_line_name(g._wl["asked"])
    assert guest_line(BW.HF_WORLD | BW.HF_MENU | BW.HF_CONTROL) == "host_world"        # the world menu, said as the engine says
    assert guest_line(BW.HF_MENU) == "away"                                              # the as-built stub's world menu


def test_the_stand_ins_transport_is_born_at_the_dial_gate_and_kept(tmp_path):
    """rejoin-t2-dial-cannot-fail: the stand-in's transport is a SOCKET -- made on the first frame its dial gate holds with a
    code (a field on every rung, the world HUD from s144), then kept in every scene (NetSyncRelay retries) -- and an ini edit
    reaches it only through a reader: an instance's poll, else the next Ensure (a field load; a world load from s144). An
    s143 guest configured on a field keeps its field-born socket on the world map: the old RJ-DIAL could not fail."""
    vals = {"Enabled": "1", "Role": "client", "RelayUrl": "ws://127.0.0.1:49231", "SessionCode": "ff9-T2BENCH1"}
    for caps, world_births in ((None, True), (FG.caps_through("leaderguard"), False)):
        f = FG.FakeGame(tmp_path / ("a" if caps is None else "b"))
        if caps is not None:
            f.netsync_caps = caps
        f.ui_state, f.field_id = "FieldHUD", 6603
        f.apply_ini(vals)
        assert f.netsync["instance"] is False and f._ini_pending is not None          # nothing reads it on the field ...
        f._step_dial()
        assert f.dial_socket is False
        f._self_on_load()                                                              # ... until a field load's Ensure
        assert f.netsync["instance"] is True and f.netsync["role"] == "client"
        f._step_dial()
        assert f.dial_socket is True
        f.ui_state = "WorldHUD"
        f._step_dial()
        assert f.dial_socket is True                                                   # kept on the world map: any rung
        f.apply_ini(dict(vals, SessionCode=""))                                        # a transport change: dropped
        assert f.dial_socket is False
        f._step_dial()
        assert f.dial_socket is False and f._no_code is world_births
        f.apply_ini(vals)
        f._step_dial()
        assert f.dial_socket is world_births                                           # a world-HUD birth: s144 only
        g = FG.FakeGame(tmp_path / ("c" if caps is None else "d"))
        if caps is not None:
            g.netsync_caps = caps
        g.ui_state, g.field_id = "FieldHUD", 6603
        g.apply_ini(vals)
        g.enter_world(9011, 68.0, -444.0)                                              # a world load: s144's Ensure
        assert g.netsync["instance"] is world_births
        g._step_dial()
        assert g.dial_socket is world_births


# ------------------------------------------------------------------------------------------------ the runners
def test_the_s144_runners_name_every_step():
    """cal144 STOPs on any DLL but s143's and on an oracle that is not CLEAN, then calibrates every leg on s143 (the solo
    bench through the selftest block, the T2 rejoin leg, an s143 world tape whose `where` reads none, the wait leg on it,
    the duo); full144 proves s144 (S144_DLL): the bench, the lever, block A + the leader guard, the dress bench, an s144
    world tape whose `where` reads world, the T2 legs (both tapes), the tape and cut legs, the duo G9 and the s144 duo.
    Neither deploys; both export SELFTEST_WT; every output outside the repo; LF line endings (bash)."""
    cal = (RUN / "cal144.example.sh").read_bytes()
    full = (RUN / "full144.example.sh").read_bytes()
    assert b"\r" not in cal and b"\r" not in full
    cal, full = cal.decode("utf-8"), full.decode("utf-8")
    for text in (cal, full):
        assert 'D="$(dirname "$0")"; WT="${WT:-$(cd "$D/../../../.." && pwd)}"' in text
        assert "/.claude/worktrees/" not in text and "scratchpad" not in text
        assert 'export SELFTEST_WT="$WT"' in text and 'cd "$WT" || { echo "STOP: WT=$WT is missing' in text
        assert "OUT=/c/gd/Dream-World-IX/.harness-runs/s144" in text and "cw.read_oracle(" in text
        assert "controllers OFF and nobody at the keyboard" in text and "THE UNATTENDED LAW" in text
        assert "deploy_field.py" not in text and "build_memoria" not in text and "49201" in text
        assert 'grep -qE "^FieldScene 6603 " "$G/FF9CustomMap-world/DictionaryPatch.txt"' in text
    assert 'if [ "$DLL" != be01339d49f6a87b ]; then' in cal
    for frag in ('"worldwait_cal143:6603:coop_world_wait:COOP_CALIBRATE=1"', "env COOP_WORLD_LEG=rejoin COOP_CALIBRATE=1",
                 "env COOP_TAPE_WORLD=1 COOP_TAPE_DIR=", '--want none > "$OUT/c143/where_none.txt"',
                 "(want 0: an s143 host says no b6)", '--want world > "$OUT/c143/where_world.txt"', "(want 1)",
                 'env COOP_WORLD_LEG=wait COOP_CALIBRATE=1 "COOP_TAPE=$T"',
                 "env COOP_CALIBRATE=1 PYTHONIOENCODING=utf-8 py tools/harness/duo.py studies/test-harness/scenarios/coop_world_wait.py",
                 "coop-tapes/world-s143"):
        assert frag in cal, frag
    assert cal.index("cw.read_oracle(") < cal.index('bash "$SB"') < cal.index("COOP_WORLD_LEG=rejoin")
    assert cal.index("env COOP_TAPE_WORLD=1") < cal.index("env COOP_WORLD_LEG=wait")
    assert 'if [ -z "${S144_DLL:-}" ]; then' in full and '[ "$DLL" != "$S144_DLL" ]' in full and "be01339d49f6a87b" in full
    for frag in ('"worldwait:6603:coop_world_wait"', '"worldwait_lever:6603:coop_world_wait:COOP_CALIBRATE=1"',
                 '"leaderguard:30602:coop_leader_guard"', '"wait_parity:30602:coop_battle_wait_parity"',
                 '"dialogue_authority:30801:coop_dialogue_authority"', '"selfdress:250:coop_self_dress"',
                 '"selfdress_noghost:250:coop_self_dress:COOP_DRESS_LEGS=I+G+S+F"', "coop-tapes/world-s144",
                 "(want 0: b6 on the world map)", "env COOP_WORLD_LEG=rejoin PYTHONIOENCODING",
                 "env COOP_WORLD_LEG=rejoin COOP_CALIBRATE=1", 'env COOP_WORLD_LEG=wait "COOP_TAPE=$(cygpath -m "$WTAPE")"',
                 'env COOP_WORLD_LEG=wait "COOP_TAPE=$(cygpath -m "$OTAPE")"', "replaytape holdtape",
                 "for l in cal readopt s119 s120-battle s121; do", "COOP_CUT_LEG=$l", "coop_dress_wire.py",
                 "py tools/harness/duo.py studies/test-harness/scenarios/coop_world_wait.py",
                 "for f in 30602 30604 30605 30606 30607 30608 30609; do"):
        assert frag in full, frag
    assert full.index('"worldwait:6603:coop_world_wait"') < full.index('"worldwait_lever:6603') < full.index(
        '"leaderguard:30602') < full.index("env COOP_TAPE_WORLD=1") < full.index("env COOP_WORLD_LEG=wait")
