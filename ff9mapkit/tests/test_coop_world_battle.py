"""[ff9mapkit netsync s145] THE s145 BENCH's REPO HALF -- studies/test-harness/scenarios/coop_world_battle.py (the SOLO leg, the two
T2 legs, the DUO leg), the world-battle tape's entry into the Ice Cavern (coop_tape_record.py COOP_TAPE_WB_ENTER, _coop_peer_bench's
facts and plan) and the runners (studies/battle-coop/bench/run/cal145.example.sh / full145.example.sh).

tests/test_world_diorama.py pins the engine's pure steps and tests/test_world_diorama_harness.py the harness core (the stand-in's
`worlddio` rung, its fault levers, the driver, the keys). This file pins what the BENCH builds on them:

  * EVERY LEG SMOKED AGAINST THE STAND-IN, through the real Session: the solo leg on the s145 stand-in (every row green), on the
    s144 one (exactly OLD_PREDICTED red, S145-CAL green) and under the lever (exactly LEVER_PREDICTED red); the T2 legs through a
    STUB PEER that replays a synthetic tape onto the stand-in's followed-client seams (its battle lane included: the host's type-1
    frames -> ``host_at(battle=..., battle_nonce=..., battle_scene=...)``) and plays replay-host's GuestWatch: it DECODES the guest's
    control frame -- the stand-in models no transport, so the stub derives that frame from the stand-in through the engine's own
    twins (battlewire.boot_watching / world_ui_free / guest_boot_state: THE REPORT) -- and logs the two lines the stand-in does not
    write ('diorama LIVE ...', 'the ready mirror is SERVING'); the duo on two stand-ins joined by a stub LINK that carries the
    host's battle lane and, for the HOST stand-in (whose start hold the stand-in models on the selftest loopback only), presents
    the guest's report to the host's `start_hold` / `wait.menu` keys the same way (a HostView over the host's state) -- [fix3]
    through the ENGINE's StartHoldStep (battlewire.start_hold_step) on the host's command-phase opening, the guest's world boot
    swirling and loading first (FakeGame.world_dio_boot_frames) as in-game.
  * EVERY CHECK CAN FAIL: each fault lever (FG.WORLD_DIO_FAULTS) turns EXACTLY its *_FAULT_REDS rows red, leg by leg; the stub's
    own knobs red the report and menu rows the stand-in cannot (an s144 report rule, no LIVE latch, the menu never served); the
    instrument rows (INI, OR, ROUTE, A, the T2 rows) go red on their own wrong shapes; and SWIRL-HANG -- a game quiet on SwirlScene
    -- is an INSTRUMENT row (the logs archived, a frame grabbed, the leg stopped), never an engine verdict.
  * THE PURE JUDGES go red on each wrong shape (fed hand-built states).

Every scenario-touching test runs in a CHILD process: a scenario puts its own dir on sys.path and reads its COOP_* knobs at import.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

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
from harness.channel import State
def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(scen, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
wb = load("coop_world_battle")
cw, pb, cb = wb.cw, wb.pb, wb.cb
# the bench's own waits, shortened for a stand-in that runs at 600 fps (every judged threshold stays the bench's)
for k, v in dict(STAY_S=1.2, MAP_S=1.2, FIELD_S=10.0, BATTLE_S=10.0, FIGHT_S=60.0, RETURN_S=15.0, DUO_LINE_S=10.0).items():
    setattr(cw, k, v)
for k, v in dict(BOOT_S=8.0, LEAVE_S=10.0, SETTLE_S=6.0, DECLINE_S=0.6, QUIET_S=1.0, DIAL_S=8.0, PAIR_S=30.0, EXIT_S=40.0,
                 BATTLE_WAIT_S=60.0, BOOT_WAIT_S=10.0, LIVE_WAIT_S=10.0, RET_WAIT_S=60.0, ENTER_WAIT_S=40.0, REJOIN_S=30.0,
                 HOLD_S=2.0, HOLD_WAIT_S=8.0, BATTLE_S=10.0, FIGHT_S=60.0, RETURN_S=15.0).items():
    setattr(wb, k, v)
FAKES = []
SPEED = float(doc.get("speed", 5.0))
wb.REPLAY_SPEED = SPEED                                    # the stub replays SPEED x real time: the held leg's battle clock
SHOTS = []

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
    f.world_dio_faults = set(run.get("faults", ()))
    if run.get("music"):
        # [fix3 -- v-raudio-1-1] the stand-in's SOUND INSTANCES (opt-in: FakeGame.world_music = (world song, battle song)) and
        # their fault levers (FG.WORLD_MUSIC_FAULTS): S145-MUSIC / the RET rows' MUSIC judged discriminating through the bench's
        # own call sites (song_quiet's re-read included), never only by the pure judges
        f.world_music = tuple(int(x) for x in run["music"])
        f.world_music_faults = set(run.get("music_faults", ()))
        # [fix3-r2] the stop fades on the WALL clock, at the engine's lengths (SaXAudio fades in real time; song_quiet and the
        # settled read are wall-clock reads) -- the stand-in's virtual clock runs ~5x the wall here, never a fixed ratio
        f.world_music_wall = True
    if run.get("hang"):
        _hang_at(f, run["hang"])
    if run.get("slow_ms"):
        _slow_loop(f, float(run["slow_ms"]))
    FAKES.append(f)
    return f

def _slow_loop(f, ms):
    """[fix3-r2] A LOADED BOX: every stand-in frame costs ``ms`` more wall time -- its virtual clock runs slower against the wall
    (as on a busy -n worker, or the duo's two fakes in one process), which must never move a verdict judged on the wall."""
    frame_once = f._frame_once
    def slowed():
        frame_once()
        time.sleep(ms / 1000.0)
    f._frame_once = slowed

def _hang_at(f, where):
    """THE SWIRL HANG on the stand-in: right after a world boot (`boot`), or inside the host's world battle swirl (`battle`: before
    any BattleHUD frame, as the 1-in-26 stall froze after LoadLevel("SwirlScene")), the game publishes ONE last state on
    SwirlScene (no HUD) and goes quiet -- the agent's Update never runs again."""
    flag = {"on": False}
    if where == "boot":
        real = f._dio_boot
        def boot(scene, **kw):
            real(scene, **kw)
            if f._wdx["world_boot"]:
                flag["on"] = True
        f._dio_boot = boot
    publish = f._publish
    def pub(force=False):
        if where == "battle" and f._wt.get("swirl") is not None:
            flag["on"] = True
        publish(force)
        if flag["on"] and f.publish_frame == f.frame:
            p = f.dir / "state.json"
            d = json.loads(p.read_text(encoding="utf-8"))
            d["scene"], d["ui_state"] = "SwirlScene", None
            FG._publish_atomic(p, json.dumps(d))           # [fix3b] atomic, as the fake publishes: no EMPTY read
            f._stop.set()
    f._publish = pub

def _swirl_after_decline(f, hang):
    """[fix3] THE SWIRL A CLAIM DOES NOT SEE, on the stand-in: 300 frames after the guest has declined the host's battle (dio.declines
    counted, its line logged, its report NONE -- the decline itself honest), every publish becomes a WORLD BOOT's SWIRL with netsync's
    `booted` claim UNSET: ui_state WorldHUD (nothing on the swirl path writes UIManager.State: SceneDirector._Swirl, UIManager's
    SwirlScene branch), scene SwirlScene, the WorldMap level gone (HarnessAgent's live gate: the world witness block off -- ticks,
    battle_prob, ctl, cam_upper -1, cam_rot / mapvar null), diorama.booted and dio.booted_world false -- a boot still in its swirl
    at the window's end; or (``hang``) ONE such publish and the game goes quiet (the 1-in-26 stall)."""
    publish = f._publish
    at = {"frame": None}
    def pub(force=False):
        if at["frame"] is None and int(f._wdx.get("declines") or 0) >= 1:
            at["frame"] = f.frame
        publish(force)
        if at["frame"] is not None and f.frame - at["frame"] >= 300 and f.publish_frame == f.frame:
            p = f.dir / "state.json"
            d = json.loads(p.read_text(encoding="utf-8"))
            d["scene"], d["ui_state"] = "SwirlScene", "WorldHUD"
            d.setdefault("world", {}).update(ticks=-1, battle_prob=-1, ctl=-1, cam_upper=-1, cam_rot=None, mapvar=None, area=-1,
                                              topo=-1, phase=-1, next_mode=-1, move=None)
            ns = d.setdefault("netsync", {})
            ns.setdefault("diorama", {})["booted"] = False
            ns.setdefault("world", {}).setdefault("dio", {})["booted_world"] = False
            FG._publish_atomic(p, json.dumps(d))           # [fix3b] atomic, as the fake publishes: no EMPTY read
            if hang:
                f._stop.set()
    f._publish = pub

def _leave_after_decline(f, fid, after):
    """[fix3-r2] A GUEST THAT LEAVES THE WORLD MAP MID-FIGHT, on the stand-in: ``after`` frames past its counted decline (dio.declines
    +1, its line logged, its report NONE -- the decline itself honest), every publish reads it on field ``fid`` -- FieldHUD on
    FieldMap, the WorldMap level gone (world.ticks -1) -- while the host's fight is still on the wire, before its entry into 300:
    the shape decision 3 forbids ('a declined guest stays frozen'), which WD-DECL's window must judge, never cut away."""
    publish = f._publish
    at = {"frame": None}
    def pub(force=False):
        if at["frame"] is None and int(f._wdx.get("declines") or 0) >= 1:
            at["frame"] = f.frame
        publish(force)
        if at["frame"] is not None and f.frame - at["frame"] >= after and f.publish_frame == f.frame:
            p = f.dir / "state.json"
            d = json.loads(p.read_text(encoding="utf-8"))
            d["ui_state"], d["scene"] = "FieldHUD", "FieldMap"
            d["field"] = dict(d.get("field") or {}, id=int(fid), name=f"FBG_FAKE_{int(fid)}")
            d.setdefault("world", {})["ticks"] = -1
            FG._publish_atomic(p, json.dumps(d))           # [fix3b] atomic, as the fake publishes: no EMPTY read
    f._publish = pub

def session(t, f):
    g = Session(game_path=t, run_dir=t / "run", save_dir=t / "player-saves", pid_probe=lambda: [],
                launcher=lambda exe, f=f: f.start(), boot_timeout=15.0, verbose=False)
    g._booted_once = True
    return g

def rows_of(checks):
    # [fix3-r2] 1200: the RET rows' MUSIC terms sit past 600 characters (their whole detail is what the tests read)
    rows = [(r["what"].split(":")[0], bool(r["ok"]), r["detail"][:1200]) for r in checks]
    return {"red": sorted(c for c, ok, _d in rows if not ok), "all": [c for c, _ok, _d in rows],
            "detail": {c: d for c, _ok, d in rows}}

def write_tape(path, recs, head=None):
    head = json.dumps(head or {"tool": "stub", "started": _dt.datetime.now().isoformat()}).encode("utf-8")
    body = b"".join(struct.pack("<dBI", r.t, r.dir, len(r.payload)) + r.payload for r in recs)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"F9TAPE01" + struct.pack("<I", len(head)) + head + body)

def grab(g, path):
    SHOTS.append(str(path))
    return pathlib.Path(path), "stub grab"
wb.grab_frame = grab

# ---- THE REPORT, as the engine's twins compute it over the stand-in (the stand-in models no transport)
def guest_ctl(f, nonce, live_seen, rule):
    """(menu byte, boot) the followed client's GuestControl would send on the host battle ``nonce``: BootWatching (the LOOSE
    gMode 3 on the world side with no durable decline -- or, rule 's144', a field only), the world's uiFree, GuestBootState."""
    wx, d = f._wdx, f._dio
    gmode = int(f._wt["gmode"])
    worlddio = "worlddio" in f._nb_caps()
    decline = wx.get("visit_decline") if worlddio else None
    world_side = gmode == 3 and worlddio and rule != "s144"
    watching = BW.boot_watching(True, True, gmode == 1, world_side, True, decline)
    if gmode == 3:
        ui_free = BW.world_ui_free(f.ui_state == "WorldHUD", bool(f.world_full_map), f.ui_state == "WorldHUD",
                                   int(f._wt.get("counter") or 0))
    else:
        ui_free = f.ui_state == "FieldHUD"
    booted = bool(d["booted"]) and bool(wx.get("by_wire"))
    bn = int(wx.get("wire_nonce", -1)) if booted else -1
    live = booted and bn == nonce and (live_seen or (f.ui_state == "BattleHUD" and bool(f.commands_enabled)))
    if rule == "no_live":
        live = False
    return BW.guest_boot_state(nonce, watching, ui_free, -1, booted, bn, live)

class GuestModel:
    """The guest's control lane over the stand-in: its report and menu byte each tick, the LIVE latch, the two lines the stand-in
    does not log; ``rule``: '' (s145), 's144' (watching on a field only), 'no_live' (never LIVE), 'menu_unserved'."""
    def __init__(self, f, rule=""):
        self.f, self.rule, self.live_nonce, self.served_nonce, self.boot_rt = f, rule, None, None, None
    def frame(self, nonce, ready_guest):
        f = self.f
        if f._dio["booted"] and self.boot_rt is None:
            self.boot_rt = f.rt
        if not f._dio["booted"]:
            self.boot_rt = None
        boot = guest_ctl(f, nonce, self.live_nonce == nonce and f._dio["booted"], self.rule)
        if boot == BW.BOOT_LIVE and self.live_nonce != nonce:
            self.live_nonce = nonce
            ms = int((f.rt - (self.boot_rt or f.rt)) * 1000)
            f._mlog(f"[NetSync] diorama LIVE {ms} ms after the boot (host battle nonce {nonce}, booted from wire nonce {nonce}) "
                    "-- the start-hold report for this battle now reads LIVE")
        menu = 0
        if boot == BW.BOOT_LIVE and ready_guest and self.rule != "menu_unserved":
            menu = BW.CTL_ROOT
            if self.served_nonce != nonce:
                self.served_nonce = nonce
                f._mlog("[NetSync] stock menu: the ready mirror is SERVING -- the host's Ready bits open the stock command menu "
                        "for the guest's slots (the digit panel only for a stranded slot; logged once per boot)")
        return menu, boot

class StubIni:
    def __init__(self, ini, values, *, label, run_dir=None, backup_root=None):
        self.values, self.restored = dict(values), None
    def apply(self):
        FAKES[-1].apply_ini(self.values)
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
    """coop_peer replay-host's stand-in: it CONNECTS whenever the stand-in's transport exists, replays the tape's host frames (SPEED
    x) onto the followed-client seams -- the position lane's field, section 7's flags, section 0, THE BATTLE LANE (type-1: live,
    its nonce and scene; stale 0.5 tape-s after its last frame) -- with replay-host's own lines, and its GuestWatch: the guest's
    control frame (GuestModel) decoded, a line on every change, as replay-host logs it."""
    rule = ""
    last = None
    def start(self):
        StubReplay.last = self
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.started = _dt.datetime.now()
        self._halt = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()
    def _run(self):
        f = FAKES[-1]
        model = GuestModel(f, self.rule)
        port, code = self._arg("--port"), self._arg("--code")
        self._say(f"listening on ws://127.0.0.1:{port} -- the stub replay-host")
        end = time.time() + 30.0
        while not self._halt.is_set() and time.time() < end and not f.dial_socket:
            time.sleep(0.05)
        if self._halt.is_set() or not f.dial_socket:
            return
        self._say(f"GUEST game connected (session {code})")
        f._mlog(f"[NetSync] relay connected ws://127.0.0.1:{port}/sess/{code}?role=guest")
        _h, recs, _torn = CP.read_tape(self.args[0])
        frames = CP.host_frames(recs)
        t0 = frames[0][0].t
        self._say(f"REPLAY start: tape {t0:.2f} s -> now; {len(frames)} host frame(s) up to tape {frames[-1][0].t:.2f} s")
        wall0, field, flags, story, first = time.time(), None, -1, None, True
        nonce, last_bt, ready, lane, said = None, -99.0, False, False, None
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
            elif w == CP.TYPE_BATTLE:
                det = pb.battle_detail(p, CP)
                if det is not None:
                    if det["nonce"] != nonce:
                        self._say(f"tape {r.t:.2f}: host battle nonce {det['nonce']} (map {det['map']}, pattern {det['pattern']}) "
                                  "on the wire")
                    nonce, last_bt = det["nonce"], r.t
                    ready = any(u["player"] and u["ready"] and (det["guest_slots"] >> u["index"]) & 1 for u in det["unit_list"])
                    if not first:
                        f.host_at(battle=True, battle_nonce=int(nonce), battle_scene=int(det["map"]))
                    lane = True
            if lane and r.t - last_bt > 0.5:
                lane = False
                f.host_at(battle=False)
            if field is None:
                continue
            if first:
                f.follow_session(field, flags=flags, fresh=True, story=story, pair_kick=True)
                first = False
            else:
                f.host_at(field, flags=flags, story=story)
            if lane and nonce is not None:
                menu, boot = model.frame(int(nonce), ready)
                if (menu, boot) != said:
                    said = (menu, boot)
                    self._say(f"guest control: menu {menu} ({BW.ctl_name(menu)}) | fmt-1 report: nonce {nonce} boot "
                              f"{BW.boot_name(boot).upper()} -- names THIS battle (host nonce {nonce})")
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

def stubs(module_pb, rule=""):
    module_pb.IniGuard = StubIni
    module_pb.port_free = lambda port, host="127.0.0.1": (True, "")
    StubReplay.rule = rule
    module_pb.PeerProc = StubReplay

PROBS = {"init": FG.FAKE_WORLD_BATTLE_PROB_INIT, "reinit": FG.FAKE_WORLD_BATTLE_PROB_REINIT}   # the stand-in's world script
wb.world_prob_oracle = lambda game: (dict(PROBS), "the stand-in's world (FakeGame's op-26 values)")

def solo(run):
    t = root(run.get("ini"))
    wb.read_oracle = (lambda game: {"problems": run["oracle_problems"], "facts": {"battle_prob": dict(PROBS)}}) \
        if run.get("oracle_problems") else (lambda game: {"problems": {}, "facts": {"stand-in": True, "battle_prob": dict(PROBS)}})
    f = fake_for(t, run)
    if run.get("lever_pre"):
        f._wdx["lever"] = BW.WORLD_WARM_OFF
    cb.CALIBRATE = bool(run.get("cal"))
    wb.LEG = "solo"
    wb.WALK_OFF_FRAMES = int(run.get("walk_off", 45))
    wb.WALK_OFF_TRIES = int(run.get("walk_tries", 3))
    try:
        with session(t, f) as g:
            wb.run(g)
            out = rows_of(list(g.checks))
            if run.get("hang"):
                f.returncode = 0                           # the session's kill: the hung game is gone
            out["shots"] = list(SHOTS)
            out["music_wall"] = bool(f.world_music_wall)          # [fix3-r2] the sound model's fades ran on the wall
            out["archived"] = sorted(p.name for p in pathlib.Path(wb._run_dir(g)).glob("*swirl-hang*"))
            return out
    finally:
        wb.WALK_OFF_FRAMES, wb.WALK_OFF_TRIES = 45, 3

def t2(run):
    leg = run["leg"]
    t = root()
    stubs(pb, run.get("rule", ""))
    if run.get("owner_up"):
        pb.port_free = lambda port, host="127.0.0.1": ((False, f"{host}:{port} is taken (stub: the owner's bridge)")
                                                      if int(port) == pb.OWNER_PORT else (True, ""))
    worldtape = leg in ("battle", "decline")                # [fix1] the decline leg replays the world-battle tape too
    tape = t / ("tape-host6603-world-battle-s144.f9tape" if worldtape else "tape-host6603-s144.f9tape")
    if run.get("tape") != "none":
        if worldtape:
            kw = dict(field_s=20.0, dwell_s=float(run.get("dwell", 100.0)), fight_s=20.0, post_s=28.0,
                      guest_ready=bool(run.get("guest_ready", True)),
                      enter_s=float(run.get("enter", 15.0)))
            write_tape(tape, pb.synthetic_world_battle_tape(CP, **kw))
        else:
            # the fight outlasts the stand-in's timed walk out (~15 s of wall time): the guest boots from the world map mid-fight
            write_tape(tape, pb.synthetic_tape(CP, pre_s=float(run.get("pre", 90.0)), fight_s=float(run.get("fight", 60.0)),
                                               post_s=25.0, field=6603))
        os.environ["COOP_TAPE"] = str(tape)
    else:
        os.environ["COOP_TAPE"] = str(t / "nope.f9tape")
    f = fake_for(t, run)
    if run.get("decline_swirl"):
        _swirl_after_decline(f, run["decline_swirl"] == "hang")
    if run.get("leave_world"):
        _leave_after_decline(f, int(run["leave_world"]), int(run.get("leave_after", 300)))
    cb.CALIBRATE = bool(run.get("cal"))
    wb.LEG = leg
    hold_ms, lead = BW.WORLD_HOLD_MS, wb.HELD_LEAD_S
    real_vehicle = Session.vehicle
    if run.get("board_late"):
        # [fix2] the aboard guard's stand-in: `vehicle 1` waits until the stub has put the host's battle on the wire (the on-foot
        # guest then boots it, or the verb meets the boot) -- WD-DECL must read the instrument's, never the engine's
        def vehicle(self, mode, *a, **k):
            if int(mode) == 1:
                end = time.time() + 90.0
                while time.time() < end and not (StubReplay.last is not None
                                                  and StubReplay.last.first(pb.PEER["tape_nonce"]) is not None):
                    time.sleep(0.05)
                time.sleep(0.3)
            return real_vehicle(self, mode, *a, **k)
        Session.vehicle = vehicle
    if run.get("board_slow"):
        # [fix3] the aboard guard's COMPARISON: the real `vehicle 1` boards at once (the guest aboard BEFORE the battle -- it
        # declines it), but the verb's read-back returns only once the stub has put the host's battle on the wire: the battle anchor
        # then sits before the aboard stamp (the state read after the verb) -- the instrument's by the comparison alone, never the
        # refusal branch
        def vehicle(self, mode, *a, **k):
            out = real_vehicle(self, mode, *a, **k)
            if int(mode) == 1:
                end = time.time() + 90.0
                while time.time() < end and not (StubReplay.last is not None
                                                  and StubReplay.last.first(pb.PEER["tape_nonce"]) is not None):
                    time.sleep(0.05)
                time.sleep(0.3)
            return out
        Session.vehicle = vehicle
    if leg == "held":
        # the stand-in's clock runs 10x the wall at 600 fps: its 15 s hold is 1.5 s of wall time -- scaled so the timed walk's
        # window (the battle inside the hold, the hold over before the host's return) has the shape the in-game one has
        BW.WORLD_HOLD_MS = int(run.get("hold_ms", 150000))
        wb.HELD_LEAD_S = float(run.get("lead", 10.0))
    try:
        with session(t, f) as g:
            wb.run(g)
            out = rows_of(list(g.checks))
            if run.get("hang") or run.get("decline_swirl") == "hang":
                f.returncode = 0
            out["shots"] = list(SHOTS)
            out["music_wall"] = bool(f.world_music_wall)          # [fix3-r2] the sound model's fades ran on the wall
            return out
    finally:
        BW.WORLD_HOLD_MS, wb.HELD_LEAD_S = hold_ms, lead
        Session.vehicle = real_vehicle

# ---- the duo: two stand-ins, a stub LINK
#: NetSyncBattle.NotArmedWhy's short key for a fresh report on this nonce (rptThis), as fakegame._nb_not_armed_why keeps it
NOT_ARMED_WHY = {BW.BOOT_LIVE: "live", BW.BOOT_DECLINED: "declined", BW.BOOT_BUSY: "busy", BW.BOOT_NONE: "none",
                 BW.BOOT_BOOTING: "link"}

class Link(threading.Thread):
    """The stub TRANSPORT of the duo: the host stand-in's place (its field, section 7's flags as HostDialogFlags says them) and
    its BATTLE LANE (an own battle: live, nonce = its epoch, scene) onto the guest's followed-client seams, its MAPJUMP intent
    once per nonce; and back, the guest's report and menu byte (GuestModel) -- what the HOST's start hold and wait parity read
    (HostView presents them: the stand-in models the host's hold on the selftest loopback only).
    [fix3] THE HOST's START HOLD IS THE ENGINE's, never a stub rule: StartHoldTick each tick through the kit's faithful port
    (battlewire.start_hold_step) on the host stand-in's virtual clock, its opening HostCommandPhaseOpen (btl_phase PHASE_NORMAL and
    the command menu enabled: the host's commands_enabled), the guest's report on this nonce its input (fresh: the stub frames one
    every tick); NoteStartHold's why / count / late_ms, ReleaseStartHold's per-reason counters, name and held length, and
    NoteOwnBattleEnd's 'ended' -- the intro follows the report, the opening decides once, a BOOTING within LateArmMs arms late, a
    late window passed is silent, and why / release / held_ms / late_ms stay readable after the battle until the next one starts
    (NetSyncBattle.cs NoteOwnBattleStart / NoteOwnBattleEnd). ``rule``: the guest model's (GuestModel), or a HOST-HALF lever on
    the report the host decodes (the guest's own diorama untouched): 'none_at_opening' (NONE on the host's opening tick alone --
    the intro primed on BOOTING, not armed at the opening, the guest's BOOTING after it arms LATE; published as the guest's real
    word, a one-frame NONE the host's samples miss) or 'none_mid_hold' (one NONE while the hold holds: released 'declined')."""
    HOST_RULES = ("none_at_opening", "none_mid_hold")
    def __init__(self, host, guest, rule=""):
        super().__init__(daemon=True)
        self.h, self.g, self.halt, self.rule = host, guest, threading.Event(), rule
        self.model = GuestModel(guest, "" if rule in self.HOST_RULES else rule)
        self.lock = threading.Lock()
        self.hs = None                                    # this own battle's StartHoldState (None between own battles)
        self.mid_done = False
        self.pub = {"nonce": -1, "why": None, "release": None, "held_ms": -1, "late_ms": -1, "count": 0,
                    "guest": {"nonce": -1, "boot_name": None}}
        self.menu = 0
        self.released = {k: 0 for k in FG.NETSYNC_BATTLE_RELEASED_KEYS}   # per reason, monotonic per process
    def _battle_start(self, nonce):
        """NoteOwnBattleStart: a fresh hold for this nonce; its observables start clean (kept after the last battle until now)."""
        self.hs, self.mid_done = BW.new_hold_state(), False
        self.pub.update(nonce=nonce, why=None, release=None, held_ms=-1, late_ms=-1)
    def _battle_end(self, now):
        """NoteOwnBattleEnd: a hold still holding ends with its battle ('ended'); the nonce -1, the rest kept."""
        hs = self.hs
        if hs["armed"] and not hs["released"]:
            self._release(BW.HOLD_REL_ENDED, now - hs["since_tick"] if hs["started"] else 0)
        self.hs = None
        self.pub["nonce"] = -1
    def _release(self, ev, held_ms):
        """ReleaseStartHold: final, counted per reason, its name and the held length."""
        self.hs["released"] = True
        key = BW.HOLD_RELEASED_KEYS.get(ev)
        if key is not None:
            self.released[key] += 1
        self.pub["release"], self.pub["held_ms"] = BW.HOLD_RELEASE_NAMES[ev], max(0, int(held_ms))
    def _hold_tick(self, nonce, boot, now, opening):
        """StartHoldTick: one StartHoldStep on the report the host decodes, then NoteStartHold's counters and reasons."""
        hs = self.hs
        word = shown = boot
        if self.rule == "none_at_opening" and opening and not hs["open_seen"]:
            # [fix3-r2] NONE on the OPENING tick ALONE (the step marks it seen): the intro primed on the guest's BOOTING, the opening
            # decides NotArmed, the BOOTING after it arms LATE -- and `shown` keeps the guest's real word: a one-frame NONE the
            # host's every-2-frame samples miss, so the decoded sequence reads ['booting', 'live'] and the opening's decision
            # (why 'late') is the ONLY witness
            word = BW.BOOT_NONE
        elif self.rule == "none_mid_hold" and hs["armed"] and not hs["released"] and not self.mid_done:
            word = shown = BW.BOOT_NONE
            self.mid_done = True
        held = now - hs["since_tick"] if hs["armed"] and not hs["released"] and hs["started"] else 0
        cap = int(self.h.ini_start_hold_ms)
        ev = BW.start_hold_step(hs, now, cap > 0, cap, opening, True, word, False, False)
        if ev == BW.HOLD_ARMED:
            self.pub["count"] += 1
            self.pub["why"] = "booting"
        elif ev == BW.HOLD_LATE_ARMED:
            self.pub["count"] += 1
            self.pub["why"], self.pub["late_ms"] = "late", hs["late_ms"]
        elif ev == BW.HOLD_NOT_ARMED:
            self.pub["why"] = NOT_ARMED_WHY.get(word, "unknown")
        elif ev in BW.HOLD_RELEASE_NAMES:
            self._release(ev, held)
        self.pub["guest"] = {"nonce": nonce, "boot_name": BW.boot_name(shown)}
    def run(self):
        sent = None
        while not self.halt.is_set():
            h = self.h
            battle = bool(h.battle_active) and not h.battle_debug
            nonce = (int(h.battle_epoch) & 0xFF) or 1
            kw = {"battle": battle}
            if battle:
                kw.update(battle_nonce=nonce, battle_scene=int(h.battle_scene or 67))
            self.g.host_at(h.host_lane_field(), flags=h.host_dialog_flags(), story=bytes(h.story_bytes), **kw)
            it = h.host_field_intent
            if it is not None and it != sent:
                sent = it
                self.g.host_intent(it[1])
            now = int(h.rt * 1000)
            with self.lock:
                if battle:
                    ready = any(u.get("player") and u.get("slot") == 1 for u in (h.battle_units or []))
                    menu, boot = self.model.frame(nonce, ready)
                    if self.hs is None or self.pub["nonce"] != nonce:
                        if self.hs is not None:
                            self._battle_end(now)
                        self._battle_start(nonce)
                    opening = bool(h.commands_enabled) and h._battle_phase_now() == BW.PHASE_NORMAL
                    self._hold_tick(nonce, boot, now, opening)
                    self.menu = menu
                elif self.hs is not None:
                    self._battle_end(now)
            time.sleep(0.02)

class HostView:
    """The host Session with the Link's start hold / wait parity read presented in its state (``netsync.battle.host``)."""
    def __init__(self, g, link):
        self._g, self._link = g, link
    def __getattr__(self, name):
        return getattr(self._g, name)
    @property
    def state(self):
        s = self._g.state
        link = self._link
        with link.lock:
            hold = json.loads(json.dumps(link.pub))
            hold["released"] = dict(link.released)        # always published, as the engine's block
            menu = link.menu
        raw = json.loads(json.dumps(s.raw))
        host = raw.setdefault("netsync", {}).setdefault("battle", {}).setdefault("host", {})
        if s.in_battle or s.ui_state == "BattleHUD":
            host.setdefault("wait", {})["menu"] = menu
        host["start_hold"] = hold                         # [fix3] the engine's keys, why / release / late_ms kept after the battle
        return State(raw, read_at=s.read_at, mtime=s.mtime)        # (its age kept: a hung host reads as one)

class StubDuo:
    def __init__(self, host, guest):
        self.host, self.guest, self.strict, self.rows, self.notes = host, guest, True, [], []
    def check(self, ok, what, detail="", *, role=None, cid=None):
        self.rows.append((cid, bool(ok), str(detail)[:1200]))         # [fix3-r2] as rows_of: DR's MUSIC past 600
        return bool(ok)
    def note(self, msg):
        self.notes.append(msg)

#: [fix3] the duo GUEST's world boot: its swirl and battle-scene load (FakeGame.world_dio_boot_frames, 1.5 s of the virtual clock)
#: -- in-game the guest boots only once the host's battle lane is on the wire (the host's InitBattle, at the start of ITS intro), and
#: then swirls and loads before its own (mirrored) intro, so its report is still BOOTING at the host's opening: the engine's start
#: hold arms there. With no load modelled the stand-in guest's command phase raced the host's opening frame for frame.
DUO_GUEST_BOOT_FRAMES = 90

def duo(run):
    th, tg = root(), root()
    fh, fgst = fake_for(th, run), fake_for(tg, run)
    fh.world_exit_frames = fgst.world_exit_frames = int(run.get("exit_frames", 240))
    fgst.world_dio_boot_frames = int(run.get("guest_boot_frames", DUO_GUEST_BOOT_FRAMES))
    if run.get("host_intro_frames"):
        # [fix3-r2] the HOST's opening camera lengthened (skipped or not): its opening lands well after the guest's command phase
        # BY CONSTRUCTION, never by the two stand-in threads' wall pace racing frame for frame
        fh.battle_intro_frames = fh.battle_intro_skip_frames = int(run["host_intro_frames"])
    cb.CALIBRATE = bool(run.get("cal"))
    gh, gg = session(th, fh), session(tg, fgst)
    with gh, gg:
        for g in (gh, gg):
            g.newgame(settle=0)
            g.warp(cw.FARSHORE)
        fh.story_bytes[pb.MARKER_BYTE] = pb.MARKER_VALUE
        fgst.follow_session(cw.FARSHORE, flags=BW.HF_ON_FIELD | BW.HF_CONTROL, fresh=True, story=bytes(fh.story_bytes),
                            pair_kick=True)
        link = Link(fh, fgst, run.get("rule", ""))
        link.start()
        gg.wait_for(lambda s: (s.netsync or {}).get("session", {}).get("mirroring") is True, timeout=5, what="paired")
        d = StubDuo(HostView(gh, link), gg)
        try:
            wb.run_duo(d)
        finally:
            link.halt.set()
        if run.get("hang"):
            fh.returncode = fgst.returncode = 0
        return {"red": sorted(c for c, ok, _d in d.rows if not ok), "all": [c for c, _ok, _d in d.rows],
                "detail": {c: dd for c, _ok, dd in d.rows}, "strict": d.strict, "notes": d.notes[-6:],
                "music_wall": bool(fh.world_music_wall and fgst.world_music_wall)}   # [fix3-r2] both fades on the wall

kinds = {"solo": solo, "t2": t2, "duo": duo}
results = {name: kinds[run["kind"]](run) for name, run in doc.get("runs", {}).items()}
print(json.dumps(results))
'''


def _child(payload, *, timeout: float = 900.0) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # [fix3] the child script runs from a file in a private temp dir (it outgrew Windows' 32 767-character command line; the run
    # document stays on stdin) -- a dir of its own, so its sys.path[0] holds nothing but the script
    work = tempfile.mkdtemp(prefix="coop_world_battle_child_")
    try:
        script = pathlib.Path(work) / "child.py"
        script.write_text(_CHILD, encoding="utf-8")
        out = subprocess.run([sys.executable, "-X", "utf8", str(script), str(SCENARIOS), str(REPO / "tools"),
                              str(REPO / "ff9mapkit")], env=env, input=json.dumps(payload), capture_output=True, text=True,
                             timeout=timeout)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    assert out.returncode == 0, out.stderr[-4000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def _run(kind: str, *, speed: float | None = None, **run) -> dict:
    return _child({"runs": {"r": dict(run, kind=kind)}, **({"speed": speed} if speed else {})})["r"]


#: the held leg's stub replays at 2 x (its fight must outlast the stand-in's timed walk out: ~15 s of wall time)
HELD_SPEED = 2.0

_TABLES = r'''
import importlib.util, json, os, sys
scen, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(scen, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
wb, tr = load("coop_world_battle"), load("coop_tape_record")
print(json.dumps({
    "solo": list(wb.solo_catalog(False)), "solo_cal": list(wb.solo_catalog(True)), "world_rows": list(wb.WORLD_ROWS),
    "return_rows": list(wb.RETURN_ROWS), "old": list(wb.OLD_PREDICTED), "lever": list(wb.LEVER_PREDICTED),
    "solo_faults": {k: list(v) for k, v in wb.SOLO_FAULT_REDS.items()},
    "t2": {leg: list(wb.t2_catalog(leg, False)) for leg in ("battle", "held", "decline")},
    "t2_cal": {leg: list(wb.t2_catalog(leg, True)) for leg in ("battle", "held", "decline")},
    "t2_pred": {k: list(v) for k, v in wb.T2_PREDICTED.items()},
    "t2_faults": {leg: {k: list(v) for k, v in d.items()} for leg, d in wb.T2_FAULT_REDS.items()},
    "duo": list(wb.DUO_CHECKS), "duo_order": list(wb.DUO_ORDER), "duo_pred": list(wb.DUO_PREDICTED),
    "duo_faults": {k: list(v) for k, v in wb.DUO_FAULT_REDS.items()},
    "music_faults": {leg: {k: list(v) for k, v in d.items()} for leg, d in wb.MUSIC_FAULT_REDS.items()},
    "consts": {"PROBE": wb.PROBE, "LEGS": list(wb.LEGS), "LEG": wb.LEG, "PORT": wb.PORT, "DIO_SCENE": wb.DIO_SCENE,
               "SCENE": wb.SCENE, "GROUP": wb.GROUP, "WORLD": wb.WORLD, "FARSHORE": wb.FARSHORE, "ICE": wb.ICE_CAVERN,
               "HELD_FIELD": wb.HELD_FIELD, "A_AWAY_MIN": wb.A_AWAY_MIN, "RETURN_TOL": wb.RETURN_TOL,
               "LANDING_MIN": wb.LANDING_MIN, "QUIET_S": wb.QUIET_S, "HELD_LEAD_S": wb.HELD_LEAD_S,
               "REPLAY_SPEED": wb.REPLAY_SPEED, "PAIR_FIELD": wb.PAIR["field"], "PAIR_SETUP": callable(wb.PAIR.get("host_setup")),
               "same_route": [wb.FS_LANDING == wb.cw.FS_LANDING, wb.ICE_TILE == wb.cw.ICE_TILE, wb.cw.__name__]},
    "values": wb.GUEST_VALUES,
    "rec": {"wb": list(tr._catalog(0, world_battle=True)), "enter": tr.WB_ENTER, "enter_s": tr.WB_ENTER_S},
    "doc": " ".join((wb.__doc__ or "").split()), "rec_doc": " ".join((tr.__doc__ or "").split())}))
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
    assert cal == solo | {"S145-CAL"} and "S145-CAL" not in solo
    assert set(t["world_rows"]) <= solo and set(t["return_rows"]) <= set(t["world_rows"])
    assert set(t["old"]) <= solo and set(t["lever"]) < set(t["old"])
    # the instrument rows are never predicted red; the lever spares its own row, the cold reference and the release
    instrument = {"S145-INI", "S145-OR", "S145-S0", "S145-ROUTE", "S145-A", "S145-SWIRL", "S145-R"}
    assert not instrument & set(t["old"]) and not instrument & set(t["lever"])
    assert not {"S145-P0", "S145-P1", "S145-LEVER", "S145-WC"} & set(t["lever"])
    assert set(t["old"]) == set(t["world_rows"]) | {"S145-P0", "S145-P1"}
    # every judged solo row has a fault that reds it (P1's red is an old engine's, pinned by the calibration test; MUSIC's is
    # also the judges' -- the stand-in plays no world song, so only a return off the world map reds it here)
    for faults, cat in ((t["solo_faults"], solo), (t["duo_faults"], set(t["duo"])),
                        *((t["t2_faults"][leg], set(t["t2"][leg])) for leg in ("battle", "held", "decline"))):
        assert set(faults) <= set(FG.WORLD_DIO_FAULTS), set(faults) - set(FG.WORLD_DIO_FAULTS)
        assert all(set(rows) <= cat for rows in faults.values()), faults
    # [fix3] the sound faults: the stand-in's own levers, each leg's MUSIC-judging row (bwe_stop_missing reds exactly it)
    music_cat = {"solo": solo, "battle": set(t["t2"]["battle"]), "held": set(t["t2"]["held"]), "duo": set(t["duo"])}
    assert set(t["music_faults"]) == set(music_cat)
    for leg, faults in t["music_faults"].items():
        assert set(faults) <= set(FG.WORLD_MUSIC_FAULTS) and "bwe_stop_missing" in faults, (leg, faults)
        assert all(set(rows) <= music_cat[leg] for rows in faults.values()), (leg, faults)
    assert t["music_faults"]["solo"] == {"bwe_stop_missing": ["S145-MUSIC"], "latch_before_settle": []}
    # [fix3-r2] the held leg's boot_song_live is not discriminating inside the fade its rejoin leaves in: the stop's removal reds
    # nothing there (the music test pins that its detail SAYS so)
    assert t["music_faults"]["held"] == {"bwe_stop_missing": []}
    covered = {r for rows in t["solo_faults"].values() for r in rows}
    assert covered == set(t["world_rows"]) | {"S145-P0", "S145-R"}, covered ^ (set(t["world_rows"]) | {"S145-P0", "S145-R"})
    for leg in ("battle", "held", "decline"):
        p = {"battle": "S145-WB", "held": "S145-HF", "decline": "S145-WD"}[leg]
        assert set(t["t2_cal"][leg]) == set(t["t2"][leg]) | {f"{p}-CAL"}
        assert set(t["t2_pred"][leg]) < set(t["t2"][leg]) and f"{p}-I" not in t["t2_pred"][leg]
        assert f"{p}-SWIRL" in t["t2"][leg] and f"{p}-SWIRL" not in t["t2_pred"][leg]
    assert t["t2_pred"]["battle"] == ["S145-WB-BOOT", "S145-WB-PLAY", "S145-WB-RET"]
    assert t["t2_pred"]["held"] == ["S145-HF-BOOT", "S145-HF-RET"]
    assert t["t2_pred"]["decline"] == ["S145-WD-DECL"] and t["t2_faults"]["decline"] == {"decline_unprojected": ["S145-WD-DECL"]}
    assert t["duo"] == t["duo_order"] and t["duo_pred"] == ["S145-DB", "S145-DP", "S145-DR"]
    c = t["consts"]
    assert (c["PROBE"], c["LEGS"], c["LEG"], c["PORT"], c["DIO_SCENE"], c["SCENE"], c["GROUP"]) == \
        ("netsync.world.dio", ["solo", "battle", "held", "decline"], "solo", 49231, 359, 67, 0)
    assert (c["WORLD"], c["FARSHORE"], c["ICE"], c["HELD_FIELD"], c["PAIR_FIELD"]) == (9011, 6603, 300, 6603, 6603)
    assert c["PAIR_SETUP"] and c["same_route"] == [True, True, "coop_world_wait"] and c["REPLAY_SPEED"] == 1.0
    assert c["A_AWAY_MIN"] > c["RETURN_TOL"] + c["LANDING_MIN"] - c["RETURN_TOL"] and c["HELD_LEAD_S"] < 15.0
    assert c["PORT"] != 49201 and t["values"]["RelayUrl"] == "ws://127.0.0.1:49231" and t["values"]["GuestStockMenu"] == "1"
    assert t["values"]["Role"] == "client" and t["values"]["FollowHost"] == "1" and t["values"]["DioramaSwirlFrames"] == "0"
    for frag in ("OLD_PREDICTED", "LEVER_PREDICTED", "THE UNATTENDED LAW", "be9abacbd7b11d64", "`bench worldwarm off`",
                 "dioboot 359 0 wire", "SWIRL-HANG", "game_snap.ps1", "COOP_TAPE_WORLD_BATTLE=1", "latest-world-battle.json",
                 "COOP_TAPE_WB_ENTER", "never 49201", "IniGuard", "THE HOLD IS 15 s", "HELD_LEAD_S", "REPLAY_SPEED",
                 "the rejoin RESUMES", "NO SECOND RETURN", "never `stall_cap`", "BOOTING then LIVE", "WHAT NO LEG HERE REACHES",
                 "The race", "THE ACTOR-BRICK LAW", "py tools/harness/duo.py studies/test-harness/scenarios/coop_world_battle.py",
                 "COOP_WB_LEG=held", "decision 11", "decision 4", "COOP_WB_LEG=decline", "THE ENCOUNTER-RATE ORACLE",
                 "BY VALUE", "SOUND INSTANCES", "dioboot 359 0 wire silent"):
        assert frag in t["doc"], frag
    rec = t["rec"]
    assert rec["enter"] is True and rec["enter_s"] == 15.0 and "REC-WE" in rec["wb"]
    assert rec["wb"].index("REC-WP") < rec["wb"].index("REC-WE") < rec["wb"].index("REC-T") and rec["wb"][-1] == "REC-INI"
    assert "COOP_TAPE_WB_ENTER=1" in t["rec_doc"] and "REC-WE the entry" in t["rec_doc"]


# ------------------------------------------------------------------------------------------------ the solo leg
SOLO_ALL = ["S145-INI", "S145-OR", "S145-S0", "S145-P0", "S145-P1", "S145-ROUTE", "S145-A", "S145-BOOT", "S145-AUDIO",
            "S145-RET", "S145-PLACE", "S145-CAM", "S145-MAP", "S145-MODE", "S145-MUSIC", "S145-FROZEN", "S145-SILENT",
            "S145-RESET", "S145-VEH", "S145-LEVER", "S145-WC", "S145-R", "S145-SWIRL"]


def test_the_solo_leg_is_green_on_the_s145_stand_in():
    r = _run("solo")
    assert r["red"] == [], {c: r["detail"][c] for c in r["red"]}
    assert r["all"] == SOLO_ALL                                          # every row, once, in run order
    d = r["detail"]
    assert "the camera turned" in d["S145-A"] and "the walk CHANGED the MAP digest" in d["S145-A"]
    assert "prev_mode 3 (replaced 1) gmode 3" in d["S145-BOOT"] and "the primed line 1x, REFUSED 0x" in d["S145-BOOT"]
    assert "(reloaded)" in d["S145-RET"] and "leave line 1x, warm return 1x, cold 0x" in d["S145-RET"]
    assert "0.00u from A" in d["S145-PLACE"] and "MAP digest = A" in d["S145-MAP"]
    assert "battle_prob 365 -> 231 (want Main_Reinit's 231" in d["S145-MAP"]        # A after a Main_Init load, the return Reinit's
    assert "boot 'warm'" in d["S145-SILENT"] and "not discriminating" in d["S145-SILENT"]
    assert "battle_prob 365 (want Main_Init's 365)" in d["S145-WC"]
    assert d["S145-MUSIC"].startswith("not discriminating")             # the stand-in plays no world song
    assert "edges +1 since A" in d["S145-FROZEN"] and "dio returns 2->3 last 'warm'" in d["S145-RESET"]   # (after SILENT's return)
    assert "aboard a vehicle (travel mode 1)" in d["S145-VEH"] and "monotonic: no reload" in d["S145-VEH"]
    assert "CALIBRATION" in d["S145-LEVER"] and "the OFF line 1x" in d["S145-LEVER"]
    assert "boot 'cold', last_return 'cold'" in d["S145-WC"] and "PLACE reads it red" in d["S145-WC"]
    assert "MAP reads it red" in d["S145-WC"]                            # the warm rows' own judges read the cold return red
    assert "the release line 1x" in d["S145-R"] and "dio.lever 'on'" in d["S145-R"]


def test_the_solo_leg_calibrates_on_s144_and_under_the_lever(tables):
    r = _child({"runs": {"s144": {"kind": "solo", "caps": "worldwait", "cal": True},
                         "lever": {"kind": "solo", "cal": True}}})
    s144, lever = r["s144"], r["lever"]
    assert s144["red"] == sorted(tables["old"]), s144["red"]
    assert lever["red"] == sorted(tables["lever"]), lever["red"]
    for x in (s144, lever):
        assert "S145-CAL" in x["all"] and "S145-CAL" not in x["red"]
    d = s144["detail"]
    assert d["S145-P0"].startswith("absent") and "Not sent" in d["S145-BOOT"] and "Not sent" in d["S145-VEH"]
    assert "Not sent" in d["S145-LEVER"] or "publishes no" in d["S145-LEVER"]
    assert d["S145-R"] == "forced=False booted=False"                   # the role released (no s145 lever there)
    d = lever["detail"]
    assert "the OFF line 1x" in d["S145-P1"] and "refused" in d["S145-BOOT"]
    assert "CALIBRATION" in d["S145-VEH"]                               # the lever's row outranks the vehicle's
    assert "not reached" in d["S145-RET"] and "boot 'cold'" in d["S145-WC"]


@pytest.mark.parametrize("fault", FG.WORLD_DIO_FAULTS)
def test_each_world_dio_fault_turns_exactly_its_solo_rows_red(tables, fault):
    """A CHECK THAT CANNOT FAIL IS NO CHECK: each fault (a value the engine would not publish, never an absent key) reds exactly its
    SOLO_FAULT_REDS rows -- and a fault the solo leg never meets (the watcher's) reds nothing."""
    want = sorted(tables["solo_faults"].get(fault, ()))
    r = _run("solo", faults=[fault])
    assert r["red"] == want, (r["red"], {c: r["detail"][c] for c in set(r["red"]) ^ set(want)})


def test_the_instrument_rows_go_red_on_their_own_wrong_shapes():
    """S145-INI: [Netsync] Enabled 1 stops the bench; S145-OR: an oracle problem reds it alone; S145-ROUTE: a 6603 with no door
    never reaches the world map -- A and every world row 'not reached'; S145-A: a walk that never leaves the landing (the warm
    witnesses could not discriminate) reds A and stops the world rows, 'not reached'."""
    r = _child({"runs": {"ini": {"kind": "solo", "ini": "[Netsync]\nEnabled = 1\n"},
                         "or": {"kind": "solo", "oracle_problems": {"dio scene": "the diorama scene 359 is not in the table"}},
                         "door": {"kind": "solo", "door": False},
                         "a": {"kind": "solo", "walk_off": 1, "walk_tries": 1}}})
    ini, orr, door, a = r["ini"], r["or"], r["door"], r["a"]
    assert "S145-INI" in ini["red"] and "Enabled '1'" in ini["detail"]["S145-INI"]
    assert set(ini["all"]) - set(ini["red"]) <= {"S145-R", "S145-SWIRL"}
    assert orr["red"] == ["S145-OR"] and "359" in orr["detail"]["S145-OR"]
    world = {"S145-BOOT", "S145-AUDIO", "S145-RET", "S145-PLACE", "S145-CAM", "S145-MAP", "S145-MODE", "S145-MUSIC",
             "S145-FROZEN", "S145-SILENT", "S145-RESET", "S145-VEH", "S145-LEVER", "S145-WC"}   # (fix1: + the silent lane)
    assert set(door["red"]) == {"S145-ROUTE", "S145-A"} | world, door["red"]
    assert all("not reached" in door["detail"][c] for c in world | {"S145-A"})
    assert set(a["red"]) == {"S145-A"} | world, a["red"]
    assert "want >= 12" in a["detail"]["S145-A"] and all("the instrument (S145-A)" in a["detail"][c] for c in world)


def test_a_swirl_hang_is_an_instrument_row_never_an_engine_verdict():
    """DECISION 11: a game that goes quiet on SwirlScene (the stand-in publishes one last state there and stops) -- the solo's boot,
    the T2 guest's boot, the duo host's world battle -- records <PFX>-SWIRL red with 'SWIRL-HANG', archives Memoria.log and
    output_log.txt and grabs a frame (the stubbed game_snap), stops the leg ('not reached: SWIRL-HANG' -- never a judged engine
    verdict), sends the hung game no `reset`, and reds the calibration as the instrument's."""
    r = _child({"runs": {"solo": {"kind": "solo", "hang": "boot"},
                         "t2": {"kind": "t2", "leg": "battle", "hang": "boot", "cal": True},
                         "duo": {"kind": "duo", "hang": "battle", "cal": True}}})
    s = r["solo"]
    assert "S145-SWIRL" in s["red"] and "SWIRL-HANG at the BOOT row" in s["detail"]["S145-SWIRL"]
    assert s["archived"] == ["Memoria-swirl-hang.log", "output_log-swirl-hang.txt"] and len(s["shots"]) == 1
    assert "swirl-hang.png" in s["detail"]["S145-SWIRL"]
    after = SOLO_ALL[SOLO_ALL.index("S145-BOOT"):SOLO_ALL.index("S145-R")]
    assert all(s["detail"][c].startswith("not reached: SWIRL-HANG") for c in after), {c: s["detail"][c] for c in after}
    assert "no `reset` is sent" in s["detail"]["S145-R"] and "S145-CAL" not in s["all"]
    assert not [c for c in ("S145-INI", "S145-OR", "S145-S0", "S145-P0", "S145-P1", "S145-ROUTE", "S145-A") if c in s["red"]]
    t = r["t2"]
    assert "S145-WB-SWIRL" in t["red"] and "SWIRL-HANG at the guest's boot" in t["detail"]["S145-WB-SWIRL"]
    assert t["detail"]["S145-WB-BOOT"].startswith("not reached: SWIRL-HANG") and "T2-INI" not in t["red"]
    assert "SWIRL-HANG" in t["detail"]["S145-WB-CAL"]
    d = r["duo"]
    assert "S145-D-SWIRL" in d["red"] and "SWIRL-HANG at the host's world battle" in d["detail"]["S145-D-SWIRL"]
    assert d["detail"]["S145-DB"].startswith("not reached: SWIRL-HANG") and "SWIRL-HANG" in d["detail"]["S145-D-CAL"]
    assert not {"S145-D0", "S145-D1", "S145-D2"} & set(d["red"])


# ------------------------------------------------------------------------------------------------ the T2 legs
BATTLE_ALL = ["T2-TAPE", "T2-PEER", "S145-WB-I", "S145-WB-BOOT", "S145-WB-PLAY", "S145-WB-RET", "S145-WB-300", "T2-SAVE", "T2-INI",
              "S145-WB-SWIRL"]
HELD_ALL = ["T2-TAPE", "T2-PEER", "S145-HF-I", "S145-HF-BOOT", "S145-HF-RET", "S145-HF-REJOIN", "T2-SAVE", "T2-INI",
            "S145-HF-SWIRL"]


def test_the_battle_leg_is_green_on_s145_and_calibrates_on_s144(tables):
    """The T2 battle leg: green on the s145 stand-in -- BOOTING then LIVE as the peer decodes it, the stock menu served, the leave
    on host_world, warm at A, then the rejoin into 300 with no second return; on the s144 stand-in exactly T2_PREDICTED red (it
    stays WorldHUD, the peer reads NONE), WB-I and WB-300 green (s144's rejoin, no diorama to count)."""
    r = _child({"runs": {"s145": {"kind": "t2", "leg": "battle"},
                         "s144": {"kind": "t2", "leg": "battle", "caps": "worldwait", "cal": True}}})
    new, old = r["s145"], r["s144"]
    assert new["red"] == [], {c: new["detail"][c] for c in new["red"]}
    assert new["all"] == BATTLE_ALL, new["all"]
    d = new["detail"]
    assert "BOOTING', 'LIVE'" in d["S145-WB-BOOT"] and "'diorama LIVE' on nonce 5 1x" in d["S145-WB-BOOT"]
    assert "(want 2 or 3); the SERVING line 1x" in d["S145-WB-PLAY"] and "left on 'host_world'" in d["S145-WB-RET"]
    assert "STILL FROZEN `hold up`" in d["S145-WB-RET"] and "dio returns 1->1" in d["S145-WB-300"]
    assert "the entry into 300" in d["T2-TAPE"] and "on the Ice Cavern tile True" in d["S145-WB-I"]
    assert old["red"] == sorted(tables["t2_pred"]["battle"] + []), old["red"]
    assert "the peer decoded ['NONE']" in old["detail"]["S145-WB-BOOT"] and "NEVER booted" in old["detail"]["S145-WB-BOOT"]
    assert "S145-WB-CAL" in old["all"] and "S145-WB-CAL" not in old["red"]


@pytest.mark.parametrize("fault", FG.WORLD_DIO_FAULTS)
def test_each_world_dio_fault_turns_exactly_its_battle_rows_red(tables, fault):
    want = sorted(tables["t2_faults"]["battle"].get(fault, ()))
    r = _run("t2", leg="battle", faults=[fault])
    assert r["red"] == want, (r["red"], {c: r["detail"][c] for c in set(r["red"]) ^ set(want)})


def test_the_report_and_the_menu_rows_can_fail_where_the_stand_in_cannot():
    """The report and the stock menu are the stub's model of the guest's control lane (the stand-in has no transport): each still
    reds its own row -- s144's report rule (watching on a field only: NONE from the world map) reds WB-BOOT; a LIVE latch that
    never comes reds WB-BOOT (no LIVE on the wire, no 'diorama LIVE' line) and WB-PLAY (no LIVE menu byte); a menu never served
    reds WB-PLAY alone."""
    r = _child({"runs": {"s144": {"kind": "t2", "leg": "battle", "rule": "s144"},
                         "nolive": {"kind": "t2", "leg": "battle", "rule": "no_live"},
                         "nomenu": {"kind": "t2", "leg": "battle", "rule": "menu_unserved"}}})
    assert r["s144"]["red"] == ["S145-WB-BOOT"], r["s144"]["red"]
    assert "the peer decoded ['NONE'" in r["s144"]["detail"]["S145-WB-BOOT"]
    assert r["nolive"]["red"] == ["S145-WB-BOOT", "S145-WB-PLAY"], r["nolive"]["red"]
    assert "'diorama LIVE' on nonce 5 0x" in r["nolive"]["detail"]["S145-WB-BOOT"]
    assert r["nomenu"]["red"] == ["S145-WB-PLAY"], r["nomenu"]["red"]
    assert "the SERVING line 0x" in r["nomenu"]["detail"]["S145-WB-PLAY"]


def test_the_held_leg_is_green_on_s145_and_calibrates_on_s144(tables):
    """The T2 held leg (the host fights on 6603, the field the guest just left -- the timed walk lands its battle inside the hold):
    green on s145 (the field battle boots the guest's diorama from WorldHUD, it leaves on host_field, warm at A, then the rejoin
    into 6603 resumes with no second return); exactly T2_PREDICTED red on s144 (HF-I and HF-REJOIN green: s144's hold and rejoin)."""
    r = _child({"runs": {"s145": {"kind": "t2", "leg": "held"},
                         "s144": {"kind": "t2", "leg": "held", "caps": "worldwait", "cal": True}}, "speed": HELD_SPEED})
    new, old = r["s145"], r["s144"]
    assert new["red"] == [], {c: new["detail"][c] for c in new["red"]}
    assert new["all"] == HELD_ALL, new["all"]
    d = new["detail"]
    assert "walked before the battle True" in d["S145-HF-I"] and "the hold line logged 1x" in d["S145-HF-I"]
    assert "left on 'host_field'" in d["S145-HF-RET"] and "FieldHUD 6603" in d["S145-HF-REJOIN"]
    assert "diorama returns 1->1" in d["S145-HF-REJOIN"]
    assert old["red"] == sorted(tables["t2_pred"]["held"]), old["red"]
    assert "S145-HF-CAL" in old["all"] and "S145-HF-CAL" not in old["red"]


@pytest.mark.parametrize("fault", ("boot_cold", "leave_fieldmap", "return_uncounted", "refreeze_lost"))
def test_each_world_dio_fault_turns_exactly_its_held_rows_red(tables, fault):
    want = sorted(tables["t2_faults"]["held"].get(fault, ()))
    r = _run("t2", leg="held", faults=[fault], speed=HELD_SPEED)
    assert r["red"] == want, (r["red"], {c: r["detail"][c] for c in set(r["red"]) ^ set(want)})


def test_a_held_walk_that_misses_the_hold_window_is_the_instruments():
    """THE 15 s HOLD: a hold that expires before the host's battle sends the guest back to 6603 first -- its boot would be a FIELD
    boot (F3.3's). HF-I reads that run red (the walk MISSED the hold window) and every row after it 'not reached': never an
    engine verdict on a mistimed instrument."""
    r = _run("t2", leg="held", hold_ms=1000, speed=HELD_SPEED)
    assert "S145-HF-I" in r["red"] and "MISSED the hold window" in r["detail"]["S145-HF-I"], r["detail"]["S145-HF-I"]
    for c in ("S145-HF-BOOT", "S145-HF-RET", "S145-HF-REJOIN"):
        assert r["detail"][c].startswith("not reached: the instrument"), (c, r["detail"][c])


def test_the_t2_legs_refuse_before_any_edit():
    """No tape -> T2-TAPE red, nothing edited; a dwell too short for the plan -> CANNOT (COOP_TAPE_WB_DWELL_S); a tape with no
    entry into 300 -> CANNOT (COOP_TAPE_WB_ENTER); a battle with no Ready guest slot -> CANNOT (WB-PLAY's premise); a held tape
    too short before its battle -> CANNOT (COOP_TAPE_PRE_S); the owner's bridge up on 49201 -> T2-PEER red before the ini."""
    r = _child({"runs": {"none": {"kind": "t2", "leg": "battle", "tape": "none"},
                         "short": {"kind": "t2", "leg": "battle", "dwell": 40.0},
                         "noenter": {"kind": "t2", "leg": "battle", "enter": 0.0},
                         "noguest": {"kind": "t2", "leg": "battle", "guest_ready": False},
                         "heldshort": {"kind": "t2", "leg": "held", "pre": 40.0},
                         "owner": {"kind": "t2", "leg": "battle", "owner_up": True}}})
    for name, x in r.items():
        assert "never edited" in x["detail"]["T2-INI"], (name, x["detail"].get("T2-INI"))
        assert "T2-INI" not in x["red"] and "T2-SAVE" not in x["red"]
    assert "T2-TAPE" in r["none"]["red"] and "no tape" in r["none"]["detail"]["T2-TAPE"]
    assert "CANNOT" in r["short"]["detail"]["T2-TAPE"] and "COOP_TAPE_WB_DWELL_S" in r["short"]["detail"]["T2-TAPE"]
    assert "CANNOT" in r["noenter"]["detail"]["T2-TAPE"] and "COOP_TAPE_WB_ENTER" in r["noenter"]["detail"]["T2-TAPE"]
    assert "CANNOT" in r["noguest"]["detail"]["T2-TAPE"] and "Ready guest slot" in r["noguest"]["detail"]["T2-TAPE"]
    assert "CANNOT" in r["heldshort"]["detail"]["T2-TAPE"] and "COOP_TAPE_PRE_S=100" in r["heldshort"]["detail"]["T2-TAPE"]
    up = r["owner"]
    assert "T2-PEER" in up["red"] and "the owner's bridge is UP on 127.0.0.1:49201" in up["detail"]["T2-PEER"]


# ------------------------------------------------------------------------------------------------ the duo
DUO_ALL = ["S145-D0", "S145-D1", "S145-D2", "S145-DB", "S145-DP", "S145-DR", "S145-D3", "S145-D-SWIRL"]


def test_the_duo_leg_is_green_on_s145_and_calibrates_on_s144(tables):
    r = _child({"runs": {"s145": {"kind": "duo"}, "s144": {"kind": "duo", "caps": "worldwait", "cal": True}}})
    new, old = r["s145"], r["s144"]
    assert new["red"] == [] and new["all"] == DUO_ALL and new["strict"] is True, new
    d = new["detail"]
    assert "['booting', 'live']" in d["S145-DB"] and "the world diorama booted warm on 9011" in d["S145-DB"]
    # [fix3] the HOST's hold is the engine's StartHoldStep: armed AT its opening, released by the guest's LIVE, once
    assert "why 'booting' release 'live' late_ms -1" in d["S145-DB"] and "released live +1 declined +0" in d["S145-DB"], d["S145-DB"]
    assert "the guest's SERVING line 1x" in d["S145-DP"] and "left on 'host_world'" in d["S145-DR"]
    assert "NO SECOND RETURN" in d["S145-D3"] and "diorama returns 1->1" in d["S145-D3"]
    assert old["red"] == sorted(tables["duo_pred"]) and "S145-D-CAL" in old["all"], old["red"]
    assert "['none']" in old["detail"]["S145-DB"]


def test_the_hosts_start_hold_reds_db_through_the_host_half_alone():
    """v-rharness-duo-host-hold-none-first-stub-not-starthold (fix3): the duo's host hold is the ENGINE's (battlewire.start_hold_step
    on the host's command-phase opening, the guest's world boot swirling and loading first), so its own lanes red S145-DB with the
    GUEST half green -- [fix3-r2] the report BOOTING through the intro (the hold primed), NONE on the host's opening tick ALONE (a
    frame its samples miss: the decoded sequence reads ['booting', 'live'], nothing between) arms LATE (why 'late': the counters
    read live +1, exactly as an on-time arm -- the opening's decision is the only witness); one NONE while it holds releases it
    'declined' (declined +1); and a guest LIVE before the host's opening -- by construction: no boot lag, the host's opening camera
    300 frames -- is NotArmed 'live' (nothing counted -- a timing red, named so)."""
    r = _child({"runs": {"late": {"kind": "duo", "rule": "none_at_opening"},
                         "mid": {"kind": "duo", "rule": "none_mid_hold"},
                         "live_first": {"kind": "duo", "guest_boot_frames": 0, "host_intro_frames": 300}}})
    for name, x in r.items():
        d = x["detail"]["S145-DB"]
        assert x["red"] == ["S145-DB"], (name, x["red"], d)
        assert "FieldHUD never; the world diorama booted warm on 9011" in d and " 1x; HOST " in d, (name, d)   # the guest half
    late, mid, first = (r[k]["detail"]["S145-DB"] for k in ("late", "mid", "live_first"))
    assert "why 'late'" in late and "armed LATE" in late and "released live +1 declined +0" in late, late
    assert "read the guest ['booting', 'live'] (want" in late and "broke on" not in late, late   # the decision ALONE reds it
    assert "release 'declined'" in mid and "declined +1" in mid and "broke on ['none']" in mid, mid
    assert "why 'live'" in first and "timing red on hardware" in first and "released live +0" in first, first


#: [fix3-r2] HF-RET's MUSIC on the held leg's stand-in: its rejoin leaves the world map inside BeforeWorldEvents' fade
HELD_INSIDE_FADE = "not discriminating: the rejoin left the world map inside BeforeWorldEvents' 500 ms fade ("


@pytest.mark.parametrize("leg", ("solo", "battle", "held", "duo"))
def test_music_is_judged_on_the_sound_instances_through_each_legs_own_call_site(tables, leg):
    """v-raudio-1-1 (fix3): with the stand-in's sound instances ON (world song 12, battle song 40; [fix3-r2] their stop fades on
    the WALL clock at the engine's lengths, as SaXAudio runs them -- FakeGame.world_music_wall) MUSIC is judged through each leg's
    own call site -- the solo's world_leave, T2's settled return, the duo's DR -- song_quiet's re-read included (a correct return's
    Leave-latched battle song fades out past the settled read): green with A's own instance resumed and nothing left playing; and
    each sound fault reds exactly its MUSIC_FAULT_REDS rows -- BeforeWorldEvents' stop removed leaves the battle song playing over
    the world song; the pre-fix2 latch order reds nothing on the solo leg (a mid-fight leave: no settle shut the song).
    [fix3-r2] THE HELD LEG (HF-RET, its recorded tail never re-read): its rejoin leaves the world map inside BeforeWorldEvents' 500
    ms fade, where a correct return and a song left playing both read boot_song_live true -- so that term is named NOT
    DISCRIMINATING there, on the correct return and under `bwe_stop_missing` alike (never a green that claims to have judged it),
    while the instance, the slot and the bookkeeping stay judged."""
    kind = {"solo": "solo", "battle": "t2", "held": "t2", "duo": "duo"}[leg]
    base = dict(kind=kind, music=[12, 40], **({"leg": leg} if kind == "t2" else {}))
    faults = tables["music_faults"][leg]
    # [fix3-r2] solo also on a LOADED box (every stand-in frame +10 ms: its virtual clock ~1.4x the wall, not ~5x): the fades are
    # the wall's, so a correct return still reads green -- fix3's x10-scaled virtual fades stretched past song_quiet's window there
    slow = {"slow": dict(base, slow_ms=10)} if leg == "solo" else {}
    r = _child({"runs": {"green": dict(base), **{f: dict(base, music_faults=[f]) for f in faults}, **slow},
                **({"speed": HELD_SPEED} if leg == "held" else {})})
    row = {"solo": "S145-MUSIC", "battle": "S145-WB-RET", "held": "S145-HF-RET", "duo": "S145-DR"}[leg]
    g = r["green"]
    assert g["red"] == [], {c: g["detail"][c] for c in g["red"]}
    assert all(x["music_wall"] is True for x in r.values()), {k: x["music_wall"] for k, x in r.items()}   # the wall fades ran
    assert "song A 12 / booted 40 (its slot 12" in g["detail"][row] and "instance A 100 -> 100" in g["detail"][row], g["detail"][row]
    if leg == "held":
        for name in ("green", "bwe_stop_missing"):           # a correct return and a song left playing read alike: unjudged
            assert "still playing True -- " + HELD_INSIDE_FADE in r[name]["detail"][row], (name, r[name]["detail"][row])
    else:
        d = g["detail"][row]
        assert "not discriminating" not in d and "still playing False (want False)" in d, d
        assert "a Leave-latched instance still playing True (want False)" in r["bwe_stop_missing"]["detail"][row]
    if leg == "solo":
        assert "the silent lane: song A 12 / booted -1 (its slot 12" in g["detail"]["S145-SILENT"], g["detail"]["S145-SILENT"]
        m = r["slow"]["detail"]["S145-MUSIC"]
        assert "S145-MUSIC" not in r["slow"]["red"] and "song A 12 / booted 40 (its slot 12" in m, (r["slow"]["red"], m)
        assert "still playing False (want False)" in m, m                    # judged on the loaded box, and green
    for f, rows in faults.items():
        assert r[f]["red"] == sorted(rows), (f, r[f]["red"], {c: r[f]["detail"][c] for c in r[f]["red"]})


@pytest.mark.parametrize("fault", FG.WORLD_DIO_FAULTS)
def test_each_world_dio_fault_turns_exactly_its_duo_rows_red(tables, fault):
    want = sorted(tables["duo_faults"].get(fault, ()))
    r = _run("duo", faults=[fault])
    assert r["red"] == want, (r["red"], {c: r["detail"][c] for c in set(r["red"]) ^ set(want)})


# ------------------------------------------------------------------------------------------------ the pure judges
_JUDGES = r'''
import datetime as _dt, importlib.util, json, os, sys
scen, tools, kit = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
from harness.channel import State
from harness import battlewire as BW
spec = importlib.util.spec_from_file_location("coop_world_battle", os.path.join(scen, "coop_world_battle.py"))
wb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wb)
cb, pb = wb.cb, wb.pb
_n = [0]
MV = "00" * 80
MV2 = "00" * 26 + "01" + "00" * 53
def st(ui="WorldHUD", x=158.0, z=-444.0, world=9011, field=6603, dio=None, d=None, wit=None, freeze=None, gmode=3, prev=1,
       music=-1, follow=None, rejoin=None, hold=None, wait_menu=None, dio_block=True, scene=None, epoch=None):
    _n[0] += 1
    w = {"id": world, "x": x, "z": z, "next_mode": 3, "cam_rot": 56.25, "cam_upper": 0, "ctl": 0, "battle_prob": 231,
         "ticks": 400, "mapvar": MV}
    w.update(wit or {})
    ns = {"bench": True, "world": {k: dict(v) for k, v in BW.WORLD_SENTINELS.items()}, "diorama": dict(d or {}),
          "session": {"follow": dict(BW.SESSION_FOLLOW_SENTINELS, **(follow or {}))},
          "battle": {"end": {"music": music}, "host": {}}}
    if not dio_block:
        ns["world"].pop("dio")
    else:
        ns["world"]["dio"].update(dio or {})
    ns["world"]["freeze"].update(freeze or {})
    ns["world"]["rejoin"].update(rejoin or {})
    if hold is not None:
        ns["battle"]["host"]["start_hold"] = hold
    if wait_menu is not None:
        ns["battle"]["host"]["wait"] = {"menu": wait_menu}
    doc = {"frame": _n[0], "ui_state": ui, "gmode": gmode, "prev_mode": prev, "field": {"id": field}, "world": w, "netsync": ns}
    if scene is not None:
        doc["scene"] = scene                               # [fix3] the stage scene (HarnessAgent: the loaded level)
    if epoch is not None:
        doc["battle"] = {"epoch": epoch}                   # [fix3] party.battle_no
    return State(doc)
L = lambda *msgs: ["21.10.2026 12:00:00 |M| [NetSync] " + m for m in msgs]
PROBS = {"init": 365, "reinit": 231}                       # the encounter-rate oracle (WORLD11's op-26 writes)
music_of = wb.music
out = {}
proof = L(*(BW.proof_ok(h, n) for h, n in ((BW.PROOF_WORLD_DIORAMA, 86), (BW.PROOF_WORLD_WATCHER, 59),
                                             (BW.PROOF_WORLD_FREEZE, 46), (BW.PROOF_WATCH, 32))))
full = st()
out["probe"] = [wb.judge_probe(full, proof)[0], wb.judge_probe(st(dio_block=False), proof)[0],
                wb.judge_probe(full, proof[:3])[0], wb.judge_probe(full, proof + L(BW.PROOF_WORLD_DIORAMA + "FAIL (row 3)"))[0],
                wb.judge_probe(full, L(*(BW.proof_ok(h, n) for h, n in ((BW.PROOF_WORLD_DIORAMA, 86),
                                                                       (BW.PROOF_WORLD_WATCHER, 59),
                                                                       (BW.PROOF_WORLD_FREEZE, 42), (BW.PROOF_WATCH, 24)))))[0]]
off_line = L(BW.LOG_WORLD_WARM_OFF)
ns_bench0 = lambda lever: State(dict(st(dio={"lever": lever}).raw, netsync=dict(st(dio={"lever": lever}).raw["netsync"], bench=False)))
out["rest"] = [wb.judge_rest(ns_bench0("on"), pulled=False)[0], wb.judge_rest(ns_bench0("off"), pulled=False)[0],
               wb.judge_rest(st(dio={"lever": "on"}), pulled=False)[0], wb.judge_rest(ns_bench0("off"), pulled=True, lines=off_line)[0],
               wb.judge_rest(ns_bench0("off"), pulled=True, lines=())[0], wb.judge_rest(st(dio_block=False), pulled=False)[0]]
arr = st(x=68.0, wit={"cam_rot": 0.0, "mapvar": MV2})
a = st(freeze={"on": True, "why": "bench"})
out["a"] = [wb.judge_a(arr, a, 90.0, 0.0, 40)[0], wb.judge_a(arr, a, 5.0, 0.0, 40)[0], wb.judge_a(arr, a, 90.0, 3.0, 40)[0],
            wb.judge_a(st(x=68.0), a, 90.0, 0.0, 40)[0],                                  # the camera never turned
            wb.judge_a(arr, st(freeze={"on": True, "why": "bench"}, wit={"mapvar": None}), 90.0, 0.0, 40)[0],
            wb.judge_a(arr, st(freeze={"on": False}), 90.0, 0.0, 40)[0],
            wb.judge_a(arr, st(dio_block=False, freeze={"on": True, "why": "bench"}), 90.0, 0.0, 40)[0],   # s144: walk + freeze
            wb.judge_a(arr, None, None, 0.0, 40)[1][:12]]
bootd = {"booted": True, "boot": "warm", "boot_field": -1, "boot_x": 158.0 * 256, "boot_z": -444.0 * 256}
booted = st(ui="BattleHUD", gmode=3, prev=3, dio={"booted_world": True, "boot_world": 9011, "boot": "warm"}, d=bootd)
primed = L(BW.log_world_warm_primed(9011, 158.0 * 256, -444.0 * 256))
out["boot"] = [wb.judge_boot(booted, [st()], primed, a)[0],
               wb.judge_boot(st(ui="BattleHUD", gmode=3, prev=3, dio={"booted_world": True, "boot_world": 9011, "boot": "cold"},
                                d=bootd), [], primed, a)[0],
               wb.judge_boot(st(ui="BattleHUD", gmode=3, prev=1, dio={"booted_world": True, "boot_world": 9011, "boot": "warm"},
                                d=bootd), [], primed, a)[0],
               wb.judge_boot(st(ui="BattleHUD", gmode=1, prev=3, dio={"booted_world": True, "boot_world": 9011, "boot": "warm"},
                                d=bootd), [], primed, a)[0],
               wb.judge_boot(st(ui="BattleHUD", gmode=3, prev=3, dio={"booted_world": True, "boot_world": 9011, "boot": "warm"},
                                d=dict(bootd, boot_x=68.0 * 256)), [], primed, a)[0],
               wb.judge_boot(booted, [], [], a)[0], wb.judge_boot(booted, [st(ui="FieldHUD")], primed, a)[0],
               wb.judge_boot(booted, [], primed + L("diorama boot REFUSED on the world map: x"), a)[0],
               wb.judge_boot(st(), [], primed, a)[0]]
fail = L(BW.LOG_PRESWIRL_AUDIO_FAILED + " (cosmetic): x")
out["audio"] = [wb.judge_audio(True, [])[0], wb.judge_audio(True, fail)[0], wb.judge_audio(False, [])[0],
                wb.judge_audio(True, L(BW.LOG_SWIRL_CENTRE_WORLD_FAILED + " (cosmetic): NullReferenceException"))[0]]
first = st(wit={"ticks": 3}, dio={"returns": 1, "last_return": "warm", "last_world": 9011},
           d={"returns": 1, "last_return": "warm", "last_return_field": -1})
rlines = L(BW.log_world_leave(9011), BW.log_world_return_warm(9011, 158.0 * 256, -444.0 * 256))
out["return"] = [wb.judge_return(first, first, 400, 0, 0, rlines, [st(ui="BattleHUD")])[0],
                 wb.judge_return(first, first, 400, 1, 0, rlines, [])[0],                       # returns +0
                 wb.judge_return(first, first, 2, 0, 0, rlines, [])[0],                         # no reload
                 wb.judge_return(first, first, 400, 0, 0, rlines, [st(ui="FieldHUD")])[0],
                 wb.judge_return(first, first, 400, 0, 0, rlines + L("diorama RETURN (cold) -> world 9011 x"), [])[0],
                 wb.judge_return(first, first, 400, 0, 0, rlines[:1], [])[0],
                 wb.judge_return(st(wit={"ticks": 3}, dio={"returns": 1, "last_return": "warm", "last_world": 9011},
                                    d={"returns": 1, "last_return": "warm", "last_return_field": 6603}), first, 400, 0, 0,
                                 rlines, [])[0],
                 wb.judge_return(None, None, 400, 0, 0, rlines, [])[0],
                 # [fix1] the engine slot's warm line beside ours, and alone (it shares the prefix up to 'Main_Reinit')
                 wb.judge_return(first, first, 400, 0, 0, rlines + L("diorama RETURN (warm) -> world 9011 resumed through "
                                                                       "Main_Reinit from a battle-return copy this diorama did "
                                                                       "NOT prime (the engine's own slot)"), [])[0],
                 wb.judge_return(first, first, 400, 0, 0, L(BW.log_world_leave(9011), "diorama RETURN (warm) -> world 9011 "
                                                            "resumed through Main_Reinit from a battle-return copy this "
                                                            "diorama did NOT prime (the engine's own slot)"), [])[0]]
out["place"] = [wb.judge_place(st(x=159.0), a)[0], wb.judge_place(st(x=170.0), a)[0],
                wb.judge_place(st(x=70.0), st(x=68.0))[0]]
out["cam"] = [wb.judge_camera(st(), a)[0], wb.judge_camera(st(wit={"cam_rot": 61.25}), a)[0],
              wb.judge_camera(st(wit={"cam_upper": 9}), a)[0], wb.judge_camera(st(wit={"cam_rot": None}), a)[0]]
a365 = st(freeze={"on": True, "why": "bench"}, wit={"battle_prob": 365})   # A as the bench takes it: after a Main_Init load
out["map"] = [wb.judge_mapvar(st(), a365, PROBS)[0], wb.judge_mapvar(st(wit={"mapvar": MV2}), a365, PROBS)[0],
              wb.judge_mapvar(st(wit={"battle_prob": 365}), a365, PROBS)[0],          # Main_Init's: a cold return (= A's)
              wb.judge_mapvar(st(wit={"mapvar": None}), a365, PROBS)[0],
              wb.judge_mapvar(st(), a365, None)[0],                                   # no oracle
              # THE INVERSION (fix1): pre-fix1's equality rule read A's 365 at a warm return's 231 RED, and a cold 365 GREEN
              (lambda s, x: s.world_mapvar == x.world_mapvar and s.world_battle_prob == x.world_battle_prob)(st(), a365),
              (lambda s, x: s.world_mapvar == x.world_mapvar and s.world_battle_prob == x.world_battle_prob)(
                  st(wit={"battle_prob": 365}), a365)]
out["mode"] = [wb.judge_mode(st(), a)[0], wb.judge_mode(st(wit={"ctl": 1}), a)[0]]
ma = st(music=12, dio={"suspend_song": -1, "song_sid": 7})                    # A: world song 12, its sound instance 7
mbt = st(ui="BattleHUD", music=40, dio={"suspend_song": 12, "song_sid": 9})  # booted: battle song 40, the world song in the slot
ret = lambda **k: st(music=12, dio=dict({"suspend_song": -1, "song_sid": 7, "boot_song_live": False}, **k))   # noqa: E731
mbs = st(ui="BattleHUD", music=-1, dio={"suspend_song": 12, "song_sid": -1})  # the silent lane: nothing current, the slot A's
out["music"] = [wb.judge_music(st(), st(), st())[0], "not discriminating" in wb.judge_music(st(), st(), st())[1],
                wb.judge_music(ret(), ma, mbt)[0],                                            # warm: A's own instance resumed
                # THE REALISTIC MUTANTS (fix1) -- each leaves the bookkeeping at A's after the restore:
                wb.judge_music(ret(boot_song_live=True), ma, mbt)[0],                         # the battle song left playing over it
                wb.judge_music(ret(song_sid=11), ma, st(ui="BattleHUD", music=40, dio={"suspend_song": -1}))[0],    # double suspend
                wb.judge_music(ret(), ma, st(ui="BattleHUD", music=40, dio={"suspend_song": -1}))[0],   # the slot wiped (booted)
                wb.judge_music(ret(song_sid=11), ma, mbt)[0],                                 # restarted from the top
                wb.judge_music(ret(), ma, st(ui="BattleHUD", music=12, dio={"suspend_song": -1}))[0],   # the same song: no discr.
                wb.judge_music(ret(), ma, mbs, silent=True)[0],                               # the silent lane, warm
                wb.judge_music(ret(), ma, st(ui="BattleHUD", music=40, dio={"suspend_song": 12}), silent=True)[0],   # a song current
                wb.judge_music(ret(song_sid=None), ma, mbt)[0],                               # an engine without the witnesses
                # the pre-fix1 judge (bookkeeping at A and the return only) read both realistic mutants GREEN: it could not fail
                all((lambda s, x: music_of(s) == music_of(x) and s.world_dio_suspend_song == x.world_dio_suspend_song)(r, ma)
                    for r in (ret(boot_song_live=True), ret(song_sid=11)))]
class QG:
    """A session stand-in for song_quiet: ``state`` reads the queued states, then keeps the last."""
    def __init__(self, *states):
        self.q = list(states)
    @property
    def state(self):
        return self.q.pop(0) if len(self.q) > 1 else self.q[0]
fading = ret(boot_song_live=True)
quiet = lambda g, s0: wb.song_quiet(g, s0, timeout=0.6)   # noqa: E731
# fix2 (raudio-1's side note): MUSIC read past the stop fades -- a latched instance still fading at the settled read goes quiet
# (green on the quiet sample), a battle song LEFT PLAYING never does (red after the window), a read that leaves the world map
# keeps the last world sample, a quiet settled read returns at once
out["quiet"] = [quiet(QG(fading, ret()), fading) is not fading and wb.judge_music(quiet(QG(fading, ret()), fading), ma, mbt)[0],
                wb.judge_music(quiet(QG(fading), fading), ma, mbt)[0],
                quiet(QG(st(ui="FieldHUD")), fading) is fading,
                quiet(QG(fading), ret()) is not fading and wb.judge_music(quiet(QG(fading), ret()), ma, mbt)[0],
                wb.song_quiet(QG(fading), None) is None]
fa = st(freeze={"on": True, "why": "bench", "edges": 2})
out["frozen"] = [wb.judge_frozen_back(st(freeze={"on": True, "why": "bench", "edges": 3}), 0.0, 40, fa)[0],
                 wb.judge_frozen_back(st(freeze={"on": True, "why": "bench", "edges": 3}), 4.0, 40, fa)[0],
                 wb.judge_frozen_back(st(freeze={"on": True, "why": "live", "edges": 3}), 0.0, 40, fa)[0],
                 wb.judge_frozen_back(st(freeze={"on": True, "why": "bench", "edges": 2}), 0.0, 40, fa)[0],
                 wb.judge_frozen_back(st(freeze={"on": False, "why": "bench", "edges": 3}), 0.0, 40, fa)[0]]
rel = lambda **k: State(dict(st(**k).raw, netsync=dict(st(**k).raw["netsync"], forced=False)))
r0 = st(dio={"returns": 1})
out["reset"] = [wb.judge_reset(rel(dio={"returns": 2, "last_return": "warm"}), r0, 1, True)[0],
                wb.judge_reset(st(dio={"returns": 2, "last_return": "warm"}), r0, 1, True)[0],      # forced not False
                wb.judge_reset(rel(dio={"returns": 1, "last_return": "warm"}), r0, 1, True)[0],
                wb.judge_reset(rel(x=170.0, dio={"returns": 2, "last_return": "warm"}), r0, 1, True)[0],
                wb.judge_reset(rel(dio={"returns": 2, "last_return": "cold"}), r0, 1, True)[0],
                wb.judge_reset(None, r0, 1, False)[1][:12]]
VWHY = BW.world_warm_row(BW.world_warm_in(travel_mode=1))[0]
s0 = st(wit={"ticks": 100}, dio={"declines": 0})
mid = [st(wit={"ticks": 110 + i}) for i in range(3)]
s1 = st(wit={"ticks": 140}, dio={"declines": 1, "decline_durable": True, "decline_why": VWHY})
REF = "the game refused a step: netsync: netsync dioboot: refused (Memoria.log names why)"
out["decline"] = [wb.judge_decline(s0, s1, mid, REF, VWHY)[0],
                  wb.judge_decline(s0, s1, mid, None, VWHY)[0],                               # it booted
                  wb.judge_decline(s0, s1, mid + [st(ui="BattleHUD", d={"booted": True})], REF, VWHY)[0],
                  wb.judge_decline(s0, s1, [st(wit={"ticks": 5})], REF, VWHY)[0],             # a reload
                  wb.judge_decline(s0, s1, mid, REF, "CALIBRATION: x")[0],
                  wb.judge_decline(s0, st(wit={"ticks": 140}, dio={"declines": 0, "decline_durable": True,
                                                                    "decline_why": VWHY}), mid, REF, VWHY)[0],
                  wb.judge_decline(s0, st(wit={"ticks": 140}, dio={"declines": 1, "decline_durable": False,
                                                                    "decline_why": VWHY}), mid, REF, VWHY)[0]]
cb_st = st(ui="BattleHUD", dio={"boot": "cold"})
cret = st(x=68.0, wit={"mapvar": MV2, "battle_prob": 365}, dio={"last_return": "cold"})
out["cold"] = [wb.judge_cold(cb_st, cret, a, PROBS)[0], wb.judge_cold(st(ui="BattleHUD", dio={"boot": "warm"}), cret, a, PROBS)[0],
               wb.judge_cold(cb_st, st(x=158.0, wit={"mapvar": MV2, "battle_prob": 365}, dio={"last_return": "cold"}), a, PROBS)[0],
               wb.judge_cold(cb_st, st(x=68.0, dio={"last_return": "cold"}), a, PROBS)[0],    # MAP green: A's digest, Reinit's
               wb.judge_cold(cb_st, st(x=68.0, wit={"mapvar": MV2, "battle_prob": 365}, dio={"last_return": "warm"}), a, PROBS)[0],
               wb.judge_cold(cb_st, st(x=68.0, wit={"mapvar": MV2}, dio={"last_return": "cold"}), a, PROBS)[0],   # 231: no Main_Init
               wb.judge_cold(cb_st, cret, a, None)[0]]                                        # no oracle
T = lambda s: _dt.datetime(2026, 10, 21, 12, 0, s)
ctl = lambda m, n, b: f"guest control: menu {m} ({BW.ctl_name(m)}) | fmt-1 report: nonce {n} boot {b} -- names THIS battle"
plines = [(T(1), ctl(0, 5, "BOOTING")), (T(2), ctl(0, 4, "LIVE")), (T(3), ctl(0, 5, "LIVE")), (T(4), ctl(2, 5, "LIVE")),
          (T(5), "tape 9.00: host field 0 -> 300")]
reps = wb.peer_reports(plines, 5)
out["reports"] = [[(m, b) for _t, m, b in reps], len(wb.peer_reports(plines, 5, after=T(3)))]
R = lambda *b: [(T(i), 0, x) for i, x in enumerate(b)]
out["report"] = [wb.judge_report(R("BOOTING", "LIVE"))[0], wb.judge_report(R("LIVE"))[0], wb.judge_report(R("BOOTING"))[0],
                 wb.judge_report(R("BOOTING", "LIVE", "DECLINED"))[0], wb.judge_report(R())[0],
                 wb.judge_report(R("NONE", "BOOTING", "LIVE"))[0], wb.judge_report(R("LIVE", "BOOTING"))[0],
                 wb.judge_report(R("BOOTING", "NONE", "LIVE"))[0], wb.judge_report(R("BOOTING", "BUSY", "LIVE", "LIVE"))[0]]
serving = L("stock menu: the ready mirror is SERVING -- the host's Ready bits open the stock command menu")
out["play"] = [wb.judge_play(reps, serving)[0], wb.judge_play(reps, [])[0],
               wb.judge_play([(T(1), 2, "BOOTING"), (T(2), 0, "LIVE")], serving)[0],
               wb.judge_play([(T(1), 3, "LIVE")], serving)[0]]
hw = st(d={"hold": {"why": "host_world"}})
out["why"] = [wb.leave_why([hw], []), wb.leave_why([st(d={"hold": {"why": "stall_cap"}})], []),
              wb.leave_why([], L("diorama END: end-leave attempt 1, 300 ms after the host's victory -- Leave() follows")),
              wb.leave_why([], L(f"diorama watcher: {BW.WATCH_WHY_TEXT_HOST_WORLD} -- leaving (nonce 5; logged once per boot)")),
              wb.leave_why([hw], L("diorama: the host's battle lane is still silent after 8s with the peer alive on field 0 "
                                   "(nonce 5: its battle lane stalled, or its fight ended unseen inside a cut) -- leaving to the "
                                   "spectate panel")),
              wb.leave_why([], [])]
ga = st(x=1197.37, z=-796.7, wit={"ticks": 300}, dio={"returns": 0}, d={"returns": 0},
        freeze={"on": True, "why": "live", "edges": 1})
gfirst = st(x=1197.37, z=-796.7, wit={"ticks": 4}, dio={"returns": 1, "last_return": "warm", "last_world": 9011},
            d={"returns": 1})
gset = st(x=1197.37, z=-796.7, freeze={"on": True, "why": "live", "edges": 2})
WH = ("terminal", "host_world")
gr = lambda *x, **k: wb.judge_guest_return(*x, **dict({"probs": PROBS}, **k))   # noqa: E731 -- the oracle, unless a case drops it
out["gret"] = [gr(gfirst, gset, ga, 0, 0, "host_world", WH, 0.0, 40, [])[0],
               gr(gfirst, gset, ga, 0, 0, "terminal", WH, 0.0, 40, [])[0],
               gr(gfirst, gset, ga, 0, 0, "stall_cap", WH, 0.0, 40, [])[0],
               gr(gfirst, gset, ga, 0, 0, "host_field", WH, 0.0, 40, [])[0],
               gr(st(x=1197.37, z=-796.7, wit={"ticks": 400}, dio={"returns": 1, "last_return": "warm",
                                                                                      "last_world": 9011}, d={"returns": 1}),
                                     gset, ga, 0, 0, "host_world", WH, 0.0, 40, [])[0],                  # no reload
               gr(gfirst, st(x=68.0, z=-444.0, freeze={"on": True, "why": "live", "edges": 2}), ga, 0, 0,
                                     "host_world", WH, 0.0, 40, [])[0],                                  # not at A
               gr(gfirst, gset, ga, 0, 0, "host_world", WH, 5.0, 40, [])[0],          # walks
               gr(gfirst, gset, ga, 0, 0, "host_world", WH, 0.0, 40, [st(ui="FieldHUD")])[0],
               gr(gfirst, gset, ga, 0, 0, "host_world", WH, None, None, [], keys_only=True)[0],
               gr(gfirst, st(x=1197.37, z=-796.7, freeze={"on": False}), ga, 0, 0, "host_world", WH, None,
                                     None, [], keys_only=True)[0],
               gr(None, None, ga, 0, 0, None, WH, None, None, [])[0],
               # [fix1] the witnesses the engine does not compute: Main_Init's rate (a cold return), no oracle, a MAP digest that is
               # not A's, a turned camera, a restarted song
               gr(gfirst, st(x=1197.37, z=-796.7, wit={"battle_prob": 365}, freeze={"on": True, "why": "live", "edges": 2}), ga, 0,
                  0, "host_world", WH, 0.0, 40, [])[0],
               gr(gfirst, gset, ga, 0, 0, "host_world", WH, 0.0, 40, [], probs=None)[0],
               gr(gfirst, st(x=1197.37, z=-796.7, wit={"mapvar": MV2}, freeze={"on": True, "why": "live", "edges": 2}), ga, 0, 0,
                  "host_world", WH, 0.0, 40, [])[0],
               gr(gfirst, st(x=1197.37, z=-796.7, wit={"cam_rot": 90.0}, freeze={"on": True, "why": "live", "edges": 2}), ga, 0,
                  0, "host_world", WH, 0.0, 40, [])[0],
               gr(gfirst, st(x=1197.37, z=-796.7, music=12, dio={"song_sid": 11, "suspend_song": -1, "boot_song_live": False},
                             freeze={"on": True, "why": "live", "edges": 2}),
                  st(x=1197.37, z=-796.7, music=12, wit={"ticks": 300}, dio={"returns": 0, "song_sid": 7, "suspend_song": -1},
                     d={"returns": 0}, freeze={"on": True, "why": "live", "edges": 1}),
                  0, 0, "host_world", WH, 0.0, 40, [], booted=mbt)[0]]
# [fix3-r2] THE HELD LEG's MUSIC GUARD (HF-RET, keys_only): boot_song_live judged only STOPCURRENT_FADE_MS (500 ms) past the first
# world sample ON THE WALL (State.mtime, else read_at -- never a published rt); inside that fade the term is named not
# discriminating and every other MUSIC term stays judged; the legs song_quiet re-reads (keys_only False) judge it at once
at = lambda s, t, rd=0.05, mt=True: State(s.raw, read_at=t + rd, mtime=t if mt else None)   # noqa: E731 -- written at t
ga_m = st(x=1197.37, z=-796.7, music=12, wit={"ticks": 300}, dio={"returns": 0, "song_sid": 7, "suspend_song": -1},
          d={"returns": 0}, freeze={"on": True, "why": "live", "edges": 1})
def hset(live, **k):
    return st(x=1197.37, z=-796.7, music=12, dio=dict({"song_sid": 7, "suspend_song": -1, "boot_song_live": live}, **k),
              freeze={"on": True, "why": "live", "edges": 2})
F0 = at(gfirst, 100.0)
HW = ("terminal", "host_field")
hg = lambda s, booted=mbt: wb.judge_guest_return(F0, s, ga_m, 0, 0, "host_field", HW, None, None, [], keys_only=True,   # noqa: E731
                                                 probs=PROBS, booted=booted)
out["heldmusic"] = [hg(at(hset(True), 100.0))[0],                       # inside the fade (0 ms): a correct return sounding -- green
                    hg(at(hset(True), 100.45))[0],                      # 450 ms: still inside -- green
                    hg(at(hset(True), 100.6))[0],                       # 600 ms past: a song LEFT playing -- red
                    hg(at(hset(False), 100.6))[0],                      # 600 ms past, quiet -- green, judged
                    hg(at(hset(True, song_sid=11), 100.0))[0],          # inside the fade, restarted from the top -- red (judged)
                    hg(at(hset(True), 100.0), booted=st(ui="BattleHUD", music=40, dio={"suspend_song": -1}))[0],   # slot wiped: red
                    hg(State(hset(True).raw, read_at=100.7, mtime=100.1))[0],   # written 100 ms past (read 650 ms late): inside
                    hg(at(hset(True), 100.6, mt=False))[0],             # no write times: the read times (600 ms) -- judged, red
                    wb.judge_guest_return(F0, at(hset(True), 100.0), ga_m, 0, 0, "host_world", WH, 0.0, 40, [], probs=PROBS,
                                          booted=mbt)[0],               # not keys_only (song_quiet's legs): judged at once, red
                    wb.wall_gap_ms(F0, at(hset(True), 100.6)), wb.wall_gap_ms(F0, at(hset(True), 100.6, rd=0.9)),
                    wb.wall_gap_ms(None, F0), wb.held_live_unjudged(F0, at(hset(True), 100.5))]
out["heldmusic_why"] = [hg(at(hset(True), 100.0))[1], hg(at(hset(True), 100.6))[1]]
gb = st(ui="BattleHUD", dio={"booted_world": True, "boot_world": 9011, "boot": "warm"}, d={"booted": True})
live = L("diorama LIVE 1200 ms after the boot (host battle nonce 5, booted from wire nonce 5) -- the start-hold report for this "
         "battle now reads LIVE")
good_r = R("BOOTING", "LIVE")
out["gboot"] = [wb.judge_guest_boot([st(), gb], gb, good_r, live, 5)[0],
                wb.judge_guest_boot([st(), gb, st(ui="FieldHUD")], gb, good_r, live, 5)[0],
                wb.judge_guest_boot([gb], st(ui="BattleHUD", dio={"booted_world": True, "boot_world": 9011, "boot": "cold"},
                                              d={"booted": True}), good_r, live, 5)[0],
                wb.judge_guest_boot([gb], gb, R("NONE"), live, 5)[0], wb.judge_guest_boot([gb], gb, good_r, [], 5)[0],
                wb.judge_guest_boot([gb], gb, good_r, live, 4)[0], wb.judge_guest_boot([gb], gb, None, live, None)[0],
                wb.judge_guest_boot([st()], None, R("NONE"), [], 5)[0]]
base = st(rejoin={"lands": 2}, d={"returns": 1}, dio={"returns": 1})
on300 = st(ui="FieldHUD", field=300, rejoin={"lands": 3}, d={"returns": 1, "last_return_field": -1}, dio={"returns": 1})
landed = L(BW.log_world_rejoin_landed(300, 300, 900))
out["r300"] = [wb.judge_rejoin_300([st(), on300], base, landed)[0],
               wb.judge_rejoin_300([on300], base, [])[0],
               wb.judge_rejoin_300([st(ui="FieldHUD", field=300, rejoin={"lands": 2}, d={"returns": 1},
                                       dio={"returns": 1})], base, landed)[0],
               wb.judge_rejoin_300([st(ui="FieldHUD", field=300, rejoin={"lands": 3}, d={"returns": 2, "last_return_field": 300},
                                       dio={"returns": 1})], base, landed)[0],                       # s144's consume rule
               wb.judge_rejoin_300([st(ui="FieldHUD", field=300, rejoin={"lands": 3}, d={"returns": 1}, dio={"returns": 2})],
                                   base, landed)[0],
               wb.judge_rejoin_300([st()], base, landed)[0],
               wb.judge_rejoin_300([st(ui="FieldHUD", field=6603, rejoin={"lands": 3}, d={"returns": 1}, dio={"returns": 1})],
                                   base, L(BW.log_world_rejoin_landed(6603, 6603, 900)), field=6603)[0]]
REL = lambda **k: dict({"live": 2, "declined": 0, "link": 0, "oldguest": 0, "cap": 0, "ended": 0}, **k)
# [fix3] the engine's whole start_hold block: the opening's decision (why / release / late_ms, kept after the battle until the next
# starts), holds armed (count), the per-reason releases; and battle.epoch (party.battle_no). H's end state is an on-time arm
# released by LIVE: count 5, epoch 12, live 3 -- each +1 over H0, read before the verb (the LAST battle's decision still kept)
H = lambda b, n=8, g=8, rel=None, why="booting", release="live", late=-1, count=5, epoch=12: st(  # noqa: E731
    ui="BattleHUD", epoch=epoch, hold={"nonce": n, "why": why, "release": release, "late_ms": late, "count": count,
                                       "released": rel or REL(live=3), "guest": {"nonce": g, "boot_name": b}})
H0 = st(epoch=11, hold={"nonce": -1, "why": "booting", "release": "live", "late_ms": -1, "count": 4, "released": REL(),
                        "guest": {"nonce": 5, "boot_name": "live"}})   # before the verb: live 2, 4 armed, epoch 11
AFT = lambda **k: st(epoch=k.pop("epoch", 12), hold=dict({"nonce": -1, "why": "booting", "release": "live", "late_ms": -1,  # noqa
                                                          "count": 5, "released": REL(live=3),
                                                          "guest": {"nonce": 8, "boot_name": "live"}}, **k))
hh = lambda samples, n=8, **k: wb.judge_host_hold(samples, n, **dict({"before": H0}, **k))[0]   # noqa: E731
NO_ENDED = {k: v for k, v in REL(live=3).items() if k != "ended"}
LATE = [H("booting", why=None, release=None), H("none", why="none", release=None, count=4),
        H("booting", why="late", release=None, late=420), H("live", why="late", late=420)]
out["hhold"] = [hh([H("booting"), H("booting"), H("live")]), hh([H("live")]),
                hh([H("booting"), H("live", g=7)]), hh([H("none")]),
                hh([H("booting"), H("live")], None), hh([H("booting"), H("live")], 9),
                # fix2: NONE first (the hold unarmed at its opening) even with a LIVE after it and live +1 / a hold released
                # 'declined' (declined +1, live +0) / the counters unread before the verb / a second live release (+2) / the
                # counters read AFTER the fight (`after`) carry the verdict over the last sample's
                hh([H("none"), H("booting"), H("live")]),
                hh([H("booting"), H("live", rel=REL(declined=1))]),
                wb.judge_host_hold([H("booting"), H("live")], 8)[0],
                hh([H("booting"), H("live", rel=REL(live=4))]),
                hh([H("booting"), H("live", rel=REL(live=2))], after=AFT()),
                hh([H("booting"), H("live")], after=AFT(released=REL(live=3, cap=1))),
                # fix3 -- THE OPENING's DECISION: the late arm's whole lane (NONE at the opening, BOOTING within 1000 ms, LIVE:
                # live +1 like an on-time arm) / the late arm on the end state ALONE (sequence and counters green) / a NONE
                # between BOOTING and LIVE ALONE (the end state on time) / NEVER MOVED: a clean booting-live sequence with every
                # release +0 (the LatePassed and NotArmed('live') lanes) / a released block without 'ended' (UNREAD) / no arm
                # counted / a second own battle in the window / the guest LIVE before the opening (NotArmed('live'), nothing
                # counted) / release not 'live' ALONE / late_ms set ALONE
                hh(LATE),
                hh([H("booting"), H("live")], after=AFT(why="late", late_ms=420)),
                hh([H("booting"), H("none"), H("booting"), H("live")]),
                hh([H("booting", rel=REL()), H("live", rel=REL())]),
                hh([H("booting"), H("live", rel=NO_ENDED)]),
                hh([H("booting"), H("live", count=4)]),
                hh([H("booting"), H("live", epoch=13)]),
                hh([H("live", why=None, release=None, count=4, rel=REL()), H("live", why="live", release=None, count=4, rel=REL())]),
                hh([H("booting"), H("live", release="declined")]),
                hh([H("booting"), H("live", late=0)])]
out["hhold_why"] = wb.judge_host_hold([H("booting"), H("live", rel=REL(declined=1))], 8, before=H0)[1]
out["hhold_late"] = wb.judge_host_hold([H("booting"), H("live")], 8, before=H0, after=AFT(why="late", late_ms=420))[1]
out["hhold_unread"] = wb.judge_host_hold([H("booting"), H("live", rel=NO_ENDED)], 8, before=H0)[1]
out["hhold_live"] = wb.judge_host_hold([H("live", why="live", release=None, count=4, rel=REL())], 8, before=H0)[1]
out["hhold_ok"] = wb.judge_host_hold([H("booting"), H("live")], 8, before=H0)[1]
out["hmenu"] = [wb.judge_host_menu([st(wait_menu=0), st(wait_menu=2)])[0], wb.judge_host_menu([st(wait_menu=0)])[0],
                wb.judge_host_menu([st(wait_menu=3)])[0], wb.judge_host_menu([st()])[0]]
out["hang"] = [wb.is_swirl_hang("SwirlScene", 6.0), wb.is_swirl_hang("SwirlScene", 0.5), wb.is_swirl_hang("WorldMap", 60.0),
               wb.is_swirl_hang("SwirlScene", None), wb.is_swirl_hang("SwirlScene", 5.0)]
class C:
    pass
def held_ctx(walk_s, a_hold, at_ui, at_hold, lines=True):
    c = C()
    c.a = st(x=68.0, z=-444.0, follow={"hold": a_hold}, freeze={"on": True, "why": "live"})
    c.anchors = {"walk": T(walk_s), "held_why": "x",
                 "held_lines": L(BW.log_world_hold_latched(6603, 9011)) if lines else []}
    c.samples = [(T(2), st(ui="FieldHUD")), (T(6), st(ui=at_ui, follow={"hold": at_hold}))]
    return c
out["held"] = [wb._held_window(held_ctx(1, 6603, "WorldHUD", 6603), T(5))[0],
               wb._held_window(held_ctx(6, 6603, "WorldHUD", 6603), T(5))[0],                # the walk started late
               wb._held_window(held_ctx(1, 6603, "FieldHUD", -1), T(5))[0],                  # back on 6603 first
               wb._held_window(held_ctx(1, 6603, "WorldHUD", -1), T(5))[0],                  # the hold already gone
               wb._held_window(held_ctx(1, 6603, "WorldHUD", 6603, lines=False), T(5))[0],   # no hold line
               "MISSED the hold window" in wb._held_window(held_ctx(1, 6603, "FieldHUD", -1), T(5))[1]]
out["stage"] = [wb.stage_of(full), wb.stage_of(st(dio_block=False)), wb.stage_of({})]
out["pre"] = [wb.pre_boot_ticks([st(wit={"ticks": 50}), st(wit={"ticks": 90}), gb, st(wit={"ticks": 3})], ga),
              wb.pre_boot_ticks([st(ui="FieldHUD", wit={"ticks": -1}), gb], ga),
              gr(gfirst, gset, ga, 0, 0, "host_world", WH, 0.0, 40, [], pre_ticks=90)[0],
              gr(gfirst, gset, ga, 0, 0, "host_world", WH, 0.0, 40, [], pre_ticks=2)[0]]
sa = st(music=12, freeze={"on": True, "why": "bench"}, dio={"suspend_song": -1, "song_sid": 7})
sb = st(ui="BattleHUD", music=-1, dio={"booted_world": True, "boot_world": 9011, "boot": "warm", "suspend_song": 12},
        d={"booted": True})
sret = st(music=12, dio={"suspend_song": -1, "song_sid": 7, "boot_song_live": False})
out["silent"] = [wb.judge_silent(sb, sret, sa)[0],
                 wb.judge_silent(st(ui="BattleHUD", music=-1, dio={"booted_world": True, "boot_world": 9011, "boot": "cold",
                                                                    "suspend_song": 12}, d={"booted": True}), sret, sa)[0],
                 wb.judge_silent(sb, st(ui="FieldHUD", music=12, dio={"song_sid": 7}), sa)[0],
                 wb.judge_silent(sb, st(x=68.0, music=12, dio={"suspend_song": -1, "song_sid": 7}), sa)[0],
                 wb.judge_silent(sb, st(music=12, dio={"suspend_song": -1, "song_sid": 11, "boot_song_live": False}), sa)[0],
                 wb.judge_silent(None, sret, sa)[0]]
w0 = st(wit={"ticks": 100}, dio={"declines": 2})
wmid = [st(wit={"ticks": 110 + i}, dio={"declines": 3, "visit_decline": VWHY}) for i in range(3)]
wlast = st(wit={"ticks": 140}, dio={"declines": 3, "decline_durable": True, "visit_decline": VWHY})
dline = L(BW.log_world_declined(9011, VWHY, 5))
NONE3 = R("NONE", "NONE")
out["wdecl"] = [wb.judge_watch_decline(w0, wmid + [wlast], NONE3, dline, 5, VWHY)[0],
                wb.judge_watch_decline(w0, wmid + [wlast], R("BOOTING", "LIVE"), dline, 5, VWHY)[0],   # it watched: BOOTING
                wb.judge_watch_decline(w0, wmid + [wlast], R("NONE", "DECLINED"), dline, 5, VWHY)[0],  # the skip: DECLINED
                wb.judge_watch_decline(w0, wmid + [wlast], R(), dline, 5, VWHY)[0],                     # no report on the wire
                wb.judge_watch_decline(w0, wmid + [st(wit={"ticks": 140}, dio={"declines": 4, "decline_durable": True,
                                                                               "visit_decline": VWHY})], NONE3, dline, 5, VWHY)[0],
                wb.judge_watch_decline(w0, wmid + [st(wit={"ticks": 140}, dio={"declines": 3, "decline_durable": False,
                                                                               "visit_decline": VWHY})], NONE3, dline, 5, VWHY)[0],
                wb.judge_watch_decline(w0, wmid + [st(ui="BattleHUD", d={"booted": True})] + [wlast], NONE3, dline, 5, VWHY)[0],
                wb.judge_watch_decline(w0, [st(wit={"ticks": 3}, dio={"declines": 3})] + [wlast], NONE3, dline, 5, VWHY)[0],
                wb.judge_watch_decline(w0, wmid + [wlast], NONE3, [], 5, VWHY)[0],                      # no line
                wb.judge_watch_decline(w0, wmid + [wlast], NONE3, dline + dline, 5, VWHY)[0],           # the line twice
                wb.judge_watch_decline(w0, [st(wit={"ticks": 120}, dio={"declines": 3})] + [st(wit={"ticks": 140}, dio={
                    "declines": 3, "decline_durable": True})], NONE3, dline, 5, VWHY)[0],                # no visit decline
                # fix2: a BattleHUD sample the engine does NOT claim booted (the UI witness beside the claim) -- red; a sample off
                # the world map at the window's end red, unless the window was cut at the rejoin's FieldHUD (its own load spared);
                # a BattleHUD there is never spared
                wb.judge_watch_decline(w0, wmid + [st(ui="BattleHUD", d={"booted": False}, wit={"ticks": 113},
                                                         dio={"declines": 3, "visit_decline": VWHY})] + [wlast],
                                       NONE3, dline, 5, VWHY)[0],
                wb.judge_watch_decline(w0, wmid + [wlast, st(ui="Pause", wit={"ticks": 141}, dio={
                    "declines": 3, "decline_durable": True, "visit_decline": VWHY})], NONE3, dline, 5, VWHY)[0],
                wb.judge_watch_decline(w0, wmid + [wlast, st(ui="Pause", wit={"ticks": 141}, dio={
                    "declines": 3, "decline_durable": True, "visit_decline": VWHY})], NONE3, dline, 5, VWHY, rejoined=True)[0],
                wb.judge_watch_decline(w0, wmid + [wlast, st(ui="BattleHUD", wit={"ticks": 141}, dio={
                    "declines": 3, "decline_durable": True, "visit_decline": VWHY})], NONE3, dline, 5, VWHY, rejoined=True)[0]]
# [fix3] the swirl and the world tick: a world boot's swirl reads WorldHUD (no UI state written) on SwirlScene with the WorldMap
# level gone (ticks -1) -- every witness beside the claim; the rejoin's own load (WorldHUD, the field level loading: ticks -1, no
# swirl / battle stage) spared ONLY trailing a cut window; a FieldHUD inside an anchored window is the guest leaving the world map
WD = dict(declines=3, decline_durable=True, visit_decline=VWHY)
sw = st(scene="SwirlScene", wit={"ticks": -1}, dio=WD)                         # the swirl, the claim unset (booted False)
load = st(scene="FieldMap", wit={"ticks": -1}, dio=WD)                         # a world -> field load's own sample
jw = lambda samples, **k: wb.judge_watch_decline(w0, samples, NONE3, dline, 5, VWHY, **k)   # noqa: E731
out["wdecl3"] = [jw(wmid + [wlast, sw, sw, sw])[0],                          # a boot still in its swirl at the window's end
                 jw(wmid + [sw, sw, wlast])[0],                               # ...mid-window
                 jw(wmid + [st(wit={"ticks": -1}, dio=WD), wlast])[0],        # the WorldMap level gone alone (no stage read)
                 jw(wmid + [st(scene="BattleMapDebug", wit={"ticks": 120}, dio=WD), wlast])[0],   # a battle stage alone
                 jw(wmid + [wlast, load], rejoined=True)[0],                  # the rejoin's own load, trailing a cut: spared
                 jw(wmid + [wlast, load])[0],                                 # ...the same, the window not cut: red
                 jw(wmid + [load, wlast], rejoined=True)[0],                  # a load-shaped sample MID-window: never spared
                 jw(wmid + [wlast, sw], rejoined=True)[0],                    # a trailing swirl: never spared
                 jw(wmid + [st(ui="FieldHUD", field=6603, wit={"ticks": -1}, dio=WD), wlast])[0],   # left the world map
                 jw(wmid + [st(wit={"ticks": None}, dio=WD), wlast])[0]]      # an unread tick is no verdict: green
out["wdecl3_why"] = [jw(wmid + [wlast, sw, sw])[1], jw(wmid + [st(ui="FieldHUD", field=6603, wit={"ticks": -1}, dio=WD), wlast])[1]]
out["offworld"] = [wb.off_world(st()), wb.off_world(st(ui="BattleHUD")), wb.off_world(st(scene="SwirlScene", wit={"ticks": -1})),
                   wb.off_world(st(wit={"ticks": -1})), wb.off_world(st(ui="FieldHUD", field=6603)),
                   wb.off_world(st(wit={"ticks": None})), wb.off_world(st(ui=None))]
# [fix3] the decline's window: anchored -> [bt, enter] UNCUT (a FieldHUD inside is judged); unanchored -> cut only at a FieldHUD on
# 300 (the follow's target: rejoined); a FieldHUD on any other field stays in
fh66, fh300 = st(ui="FieldHUD", field=6603, wit={"ticks": -1}, dio=WD), st(ui="FieldHUD", field=300, wit={"ticks": -1}, dio=WD)
def stamp(ss, t0=10):
    return [(T(t0 + i), s) for i, s in enumerate(ss)]
def dw(ss, enter, bt=T(10), nb=None):
    since, rejoined = wb.decline_window(stamp(ss), bt, enter, T(59), not_before=nb)
    return [len(since), rejoined, [s.field_id for s in since if s.ui_state == "FieldHUD"]]
out["dwin"] = [dw([wlast, fh66, wlast, fh300, wlast], T(13)),                  # anchored at fh300: uncut, both FieldHUDs in
               dw([wlast, fh66, wlast, fh300, wlast], None),                   # unanchored: cut at 300, 6603 stays
               dw([wlast, fh66, wlast], None),                                 # unanchored, no 300: whole, not rejoined
               dw([wlast, fh66, wlast, fh300], T(13), bt=T(11)),               # from bt on
               dw([wlast, fh300, wlast, fh300, wlast], None, nb=T(13))]        # [fix3b] a 300 before the fight's end stays in
def jdw(ss, enter, nb=None):
    since, rejoined = wb.decline_window(stamp(ss), T(10), enter, T(59), not_before=nb)
    return jw(since, rejoined=rejoined)[0]
out["dwin_judged"] = [jdw(wmid + [wlast, fh66, wlast], T(15)),                # a FieldHUD on 6603 inside an anchored window: red
                      jdw(wmid + [wlast, load, fh300], None),                 # unanchored: cut at 300, its load spared: green
                      jdw(wmid + [wlast, load, fh300], T(15)),                # anchored past it: the FieldHUD judged, red
                      jdw(wmid + [wlast, fh66, wlast, fh300], None),          # unanchored: 6603 before the cut stays red
                      jdw(wmid + [wlast, load, fh300], None, nb=T(59))]       # [fix3b] a 300 while the host still fights: red
booted_b = st(ui="BattleHUD", d={"booted": True})
out["aboard"] = [wb.aboard_refusal_instrument(True, booted_b), wb.aboard_refusal_instrument(True, sw),
                 wb.aboard_refusal_instrument(True, st()), wb.aboard_refusal_instrument(False, booted_b),
                 wb.aboard_refusal_instrument(True, st(ui="FieldHUD")), wb.aboard_refusal_instrument(True, None),
                 wb.aboard_refusal_instrument(True, st(d={"booted": True}))]
print(json.dumps(out))
'''


def test_the_judges_go_red_on_each_wrong_shape():
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # (the script on stdin, `-`: fix2 grew it past Windows' 32 767-character command line)
    run = subprocess.run([sys.executable, "-X", "utf8", "-", str(SCENARIOS), str(REPO / "tools"),
                          str(REPO / "ff9mapkit")], env=env, input=_JUDGES, capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr[-3000:]
    o = json.loads(run.stdout.strip().splitlines()[-1])
    assert o["probe"] == [True, False, False, False, False]      # whole / absent / a line missing / a FAIL / s144's counts
    assert o["rest"] == [True, False, False, True, False, False]  # at rest / mis-set / bench on / pulled / no OFF line / absent
    assert o["a"] == [True, False, False, False, False, False, True, "not reached:"]
    # warm / cold / prevMode 1 / gMode 1 / not at A / no primed line / a FieldHUD sample / a REFUSED line / not booted
    assert o["boot"] == [True, False, False, False, False, False, False, False, False]
    assert o["audio"] == [True, False, False, False]                 # + the world shape's swirl-centre line (fix1)
    # warm on its own load / +0 / no reload / FieldHUD / a cold line / no return line / a field's return / none
    assert o["return"] == [True, False, False, False, False, False, False, False, False, False]   # + the unprimed line (fix1)
    assert o["place"] == [True, False, False] and o["cam"] == [True, False, False, False]
    # MAP by value (fix1): Reinit's 231 green; another digest / Main_Init's 365 / no digest / no oracle red; the pre-fix1 equality
    # rule read a warm 231 RED and a cold 365 GREEN against A's 365 -- the inversion this fix removes
    assert o["map"] == [True, False, False, False, False, False, True] and o["mode"] == [True, False]
    # MUSIC on the instances (fix1): not discriminating / warm green; the battle song left playing, a double suspend, the slot wiped,
    # a restart red; the same song not discriminating; the silent lane warm green, a song current red; no witnesses red; and the
    # pre-fix1 bookkeeping judge read both realistic mutants GREEN (it could not fail)
    assert o["music"] == [True, True, True, False, False, False, False, True, True, False, False, True]
    assert o["quiet"] == [True, False, True, True, True]
    assert o["frozen"] == [True, False, False, False, False]
    assert o["reset"] == [True, False, False, False, False, "not reached:"]
    assert o["decline"] == [True, False, False, False, False, False, False]
    assert o["cold"] == [True, False, False, False, False, False, False]
    assert o["reports"] == [[[0, "BOOTING"], [0, "LIVE"], [2, "LIVE"]], 2]   # the other nonce's frame skipped; `after` cuts
    # BOOTING first, then LIVE / LIVE alone / no LIVE / a DECLINED / nothing / NONE first (s144's field-only watching, the strict
    # onWorld: the host's hold unarmed at its opening) / LIVE before BOOTING / a NONE before the LIVE / a transient BUSY between
    assert o["report"] == [True, False, False, False, False, False, False, False, True]
    assert o["play"] == [True, False, False, True]
    assert o["why"] == ["host_world", "stall_cap", "terminal", "host_world", "stall_cap", None]
    assert o["gret"] == [True, True, False, False, False, False, False, False, True, False, False,
                         False, False, False, False, False]          # fix1: Main_Init's rate / no oracle / MAP / CAM / MUSIC
    # fix3-r2 (the held leg's MUSIC guard): inside BeforeWorldEvents' fade on the wall, boot_song_live unjudged (green, named) while
    # the instance and the slot stay judged; past it judged both ways; write times over read times; song_quiet's legs judge at once
    assert o["heldmusic"] == [True, True, False, True, False, False, True, False, False, 600, 600, None, None], o["heldmusic"]
    assert ("still playing True -- not discriminating: the rejoin left the world map inside BeforeWorldEvents' 500 ms fade (0 ms past "
            "the first world sample)") in o["heldmusic_why"][0], o["heldmusic_why"][0]
    assert "still playing True (want False)" in o["heldmusic_why"][1], o["heldmusic_why"][1]
    assert o["silent"] == [True, False, False, False, False, False]  # warm silent lane / cold / a field / not at A / restarted / none
    # NONE only + one line + one count green; BOOTING / DECLINED / no report / +2 / not durable / a boot / a reload / no line / two
    # lines / no visit decline red
    # fix2: + a BattleHUD sample not claimed booted red; a trailing non-WorldHUD sample red, spared as the rejoin's own load (cut at
    # its FieldHUD), a trailing BattleHUD never spared
    # fix3: a trailing 'Pause' is the pause menu, never a load (UIManager writes no other state between WorldHUD and FieldHUD): red
    assert o["wdecl"] == [True, False, False, False, False, False, False, False, False, False, False, False, False, False, False]
    # fix3 (swirl-blind): a swirl at the window's end / mid-window / the WorldMap level gone alone / a battle stage alone -- red;
    # the rejoin's own load spared only trailing a CUT window (not cut: red; mid-window: red); a trailing swirl never spared; a
    # FieldHUD inside: red; an unread tick: green
    assert o["wdecl3"] == [False, False, False, False, True, False, False, False, False, True], o["wdecl3"]
    assert "WorldHUD on SwirlScene" in o["wdecl3_why"][0], o["wdecl3_why"][0]
    assert "LEFT the world map before the host's entry: field [6603]" in o["wdecl3_why"][1], o["wdecl3_why"][1]
    assert o["offworld"] == [None, "BattleHUD", "WorldHUD on SwirlScene", "WorldHUD, the WorldMap level gone (ticks -1)",
                             "FieldHUD 6603", None, "None"], o["offworld"]
    # fix3 (cut-not-rejoin): anchored -> uncut; unanchored -> cut at 300 only (rejoined); bt bounds it
    assert o["dwin"] == [[4, False, [6603, 300]], [3, True, [6603]], [3, False, [6603]], [3, False, [6603, 300]],
                         [3, True, [300]]], o["dwin"]
    assert o["dwin_judged"] == [False, True, False, False, False], o["dwin_judged"]
    # fix3 (the aboard guard's attribution): the instrument's only when the battle is anchored AND the refusal's sample shows the
    # boot (claim, battle HUD, or a swirl / battle stage); a refusal with no boot, or no anchor, is the engine's
    assert o["aboard"] == [True, True, False, False, False, False, True], o["aboard"]
    assert o["gboot"] == [True, False, False, False, False, False, True, False]
    assert o["r300"] == [True, False, False, False, False, False, True]
    # fix2: + NONE first / declined +1 / counters unread / live +2 red; the after-fight read carries the verdict (green), and
    # a cap release there red
    # fix3: + the late arm's lane / the late arm alone on the end state / a NONE between alone / never moved / no 'ended' / no arm
    # counted / two own battles / LIVE before the opening / release not live / late_ms set -- each red ALONE (its own clause)
    assert o["hhold"] == [True, False, False, False, True, False, False, False, False, False, True, False,
                          False, False, False, False, False, False, False, False, False, False], o["hhold"]
    assert "declined +1" in o["hhold_why"] and "live +0" in o["hhold_why"], o["hhold_why"]
    assert "why 'late'" in o["hhold_late"] and "armed LATE, +420 ms" in o["hhold_late"] and "live +1" in o["hhold_late"]
    assert "UNREAD" in o["hhold_unread"], o["hhold_unread"]
    assert "why 'live'" in o["hhold_live"] and "timing red on hardware" in o["hhold_live"], o["hhold_live"]
    assert ("why 'booting' release 'live' late_ms -1" in o["hhold_ok"] and "live +1" in o["hhold_ok"]
            and "holds armed +1" in o["hhold_ok"] and "own battles +1" in o["hhold_ok"]), o["hhold_ok"]
    assert o["hmenu"] == [True, False, True, False]
    assert o["hang"] == [True, False, False, False, True]
    assert o["held"] == [True, False, False, False, False, True]
    assert o["stage"][0] == 145 and o["stage"][1] < 145 and o["stage"][2] < 145
    # the reload witness reads the tick the world reached right before the boot (A's may be the arrival's own, small)
    assert o["pre"] == [90, 300, True, False]


# ------------------------------------------------------------------------------------------------ the tape, the recorder
def _pb():
    sys.path.insert(0, str(SCENARIOS))
    import _coop_peer_bench as pb                            # noqa: E402
    return pb


def test_the_world_battle_tape_carries_the_entry_and_refuses_a_wrong_one():
    """[s145 bench] the world-battle tape's host enters the Ice Cavern after its stay (COOP_TAPE_WB_ENTER): the facts read the stay
    to the entry and the entry itself (expect.rejoin_field 300); a tape that enters another field, enters too soon or stands on
    300 too briefly refuses; a tape with no entry still plans (rejoin_field None) -- coop_world_battle's battle leg refuses it."""
    pb = _pb()
    cp = pb.coop_peer_module()
    facts = lambda **k: pb.world_battle_tape_facts(pb.synthetic_world_battle_tape(cp, **k), cp)   # noqa: E731
    good = facts(guest_ready=True, enter_s=15.0)
    plan = pb.plan_world_leg("world-battle", good)
    assert plan["ok"] and plan["expect"]["rejoin_field"] == 300 and good["enter"]["field"] == 300, good["wb5"]
    assert good["after_s"] >= pb.WB_AFTER_NEED_S and good["enter"]["on_s"] >= pb.WB_ENTER_NEED_S
    plain = facts()
    assert pb.plan_world_leg("world-battle", plain)["ok"] and plain["enter"] is None
    assert pb.plan_world_leg("world-battle", plain)["expect"]["rejoin_field"] is None
    other = facts(enter_s=15.0, enter_field=250)
    assert not other["wb5"]["ok"] and "only the Ice Cavern (300)" in other["wb5"]["why"]
    brief = facts(enter_s=4.0)
    assert not brief["wb5"]["ok"] and "COOP_TAPE_WB_ENTER_S" in brief["wb5"]["why"]
    early = facts(enter_s=15.0, post_s=10.0)
    assert not early["wb5"]["ok"] and "COOP_TAPE_WB_POST_S" in early["wb5"]["why"]
    # the guest slot's Ready unit: the replayed guest's stock menu has a slot to serve (the head's guest slots 2 = btl index 1)
    recs = pb.synthetic_world_battle_tape(cp, guest_ready=True)
    ready = [any(u["player"] and u["ready"] and u["index"] == 1 for u in d["unit_list"])
             for d in (pb.battle_detail(p, cp) for r, w, p in cp.host_frames(recs) if w == cp.TYPE_BATTLE) if d is not None]
    assert any(ready) and not all(ready)
    # the leg's own planners, off the same tapes (in a child: the scenario reads its knobs at import)
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _PLANS, str(SCENARIOS), str(REPO / "tools")],
                         env={k: v for k, v in os.environ.items() if not k.startswith("COOP_")}, capture_output=True,
                         text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-3000:]
    o = json.loads(out.stdout.strip().splitlines()[-1])
    assert o["battle"] == [True, False, False, False] and "COOP_TAPE_WB_ENTER" in o["battle_why"]
    assert o["ready"] == [True, False, False] and "Ready guest slot" in o["noguest_why"]   # (another nonce offers none)
    assert o["held"] == [True, False, False, False] and "COOP_TAPE_PRE_S=100" in o["held_why"]
    assert o["wall"] == 44.55                                   # (the battle's tape time - the first host frame) / REPLAY_SPEED


_PLANS = r'''
import datetime as _dt, importlib.util, json, os, sys
scen, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
spec = importlib.util.spec_from_file_location("coop_world_battle", os.path.join(scen, "coop_world_battle.py"))
wb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wb)
pb = wb.pb
cp = pb.coop_peer_module()
wf = lambda **k: pb.world_battle_tape_facts(pb.synthetic_world_battle_tape(cp, **k), cp)
tf = lambda **k: pb.tape_facts(pb.synthetic_tape(cp, **k), cp, field=6603)
b = [wb.plan_battle_leg(wf(enter_s=15.0))["ok"], wb.plan_battle_leg(wf())["ok"], wb.plan_battle_leg(wf(dwell_s=40.0))["ok"],
     wb.plan_battle_leg(wf(enter_s=15.0), False)["ok"]]
rg = lambda **k: wb.tape_ready_guest(pb.synthetic_world_battle_tape(cp, **k), cp, 5)
ready = [rg(guest_ready=True), rg(), wb.tape_ready_guest(pb.synthetic_world_battle_tape(cp, guest_ready=True), cp, 6)]
h = [wb.plan_held_leg(tf(pre_s=90.0, field=6603))["ok"], wb.plan_held_leg(tf(pre_s=40.0, field=6603))["ok"],
     wb.plan_held_leg(pb.tape_facts(pb.synthetic_tape(cp, pre_s=90.0), cp, field=6603))["ok"],
     wb.plan_held_leg(wf(enter_s=15.0))["ok"]]
c = wb._T2()
c.facts, c.plan = tf(pre_s=90.0, field=6603), wb.plan_held_leg(tf(pre_s=90.0, field=6603))
c.anchors["start"] = _dt.datetime(2026, 10, 21, 12, 0, 0)
wb.REPLAY_SPEED = 2.0
wall = (wb.battle_wall(c) - c.anchors["start"]).total_seconds()
print(json.dumps({"battle": b, "battle_why": wb.plan_battle_leg(wf())["why"], "held": h, "ready": ready,
                  "noguest_why": wb.plan_battle_leg(wf(enter_s=15.0), False)["why"],
                  "held_why": wb.plan_held_leg(tf(pre_s=40.0, field=6603))["why"], "wall": round(wall, 2)}))
'''


def test_the_recorder_enters_the_ice_cavern_after_its_stay():
    """coop_tape_record.py's world-battle variant: after the STAY the host teleports onto the Ice Cavern tile, waits the prompt's
    frames, Confirms, stands on 300 COOP_TAPE_WB_ENTER_S (REC-WE) -- and the pointer carries the entry."""
    src = (SCENARIOS / "coop_tape_record.py").read_text(encoding="utf-8")
    assert "def _world_battle_enter(g, led: cb.Ledger, ctx: _Ctx, cw) -> None:" in src
    i = src.index("def _world_battle_enter(")
    body = src[i:src.index("\ndef ", i + 10)]
    for frag in ("cw.teleport_settle(g, cw.ICE_TILE)", "g.wait_frames(cw.PROMPT_FRAMES)", 'g.press("confirm")',
                 "pb.WB_ENTER_FIELD", "WB_ENTER_S", 'led.check("REC-WE"'):
        assert frag in body, frag
    assert "if WB_ENTER:\n        _world_battle_enter(g, led, ctx, cw)" in src.replace("\r\n", "\n")
    assert '"enter": facts.get("enter")' in src and "WB_ENTER = pb.env_int(\"COOP_TAPE_WB_ENTER\", 1) != 0" in src


# ------------------------------------------------------------------------------------------------ the runners
def test_the_s145_runners_name_every_step():
    """cal145 STOPs on any DLL but s144's and on an oracle that is not CLEAN, RECORDS THE TAPES FIRST on s144 (the world-battle tape,
    `where --want world-battle`; the held-field tape on 6603), then calibrates every leg (the solo bench through the selftest block,
    the T2 battle and held legs, the duo); full145 proves s145 (S145_DLL): the bench, the lever, both T2 legs (and the battle leg's
    calibration), the duo, then the regression -- block A (the F3.3 warm return, wait parity, the leader guard, ...),
    coop_world_wait's solo + lever + T2 + duo, the cut legs (s120-world on a hand tape), the duo G9. A leg that says SWIRL-HANG is
    re-run ONCE. Neither deploys; both export SELFTEST_WT; every output outside the repo; LF line endings (bash)."""
    cal = (RUN / "cal145.example.sh").read_bytes()
    full = (RUN / "full145.example.sh").read_bytes()
    assert b"\r" not in cal and b"\r" not in full
    cal, full = cal.decode("utf-8"), full.decode("utf-8")
    for text in (cal, full):
        assert 'D="$(dirname "$0")"; WT="${WT:-$(cd "$D/../../../.." && pwd)}"' in text
        assert "/.claude/worktrees/" not in text and "scratchpad" not in text
        assert 'export SELFTEST_WT="$WT"' in text and 'cd "$WT" || { echo "STOP: WT=$WT is missing' in text
        assert "OUT=/c/gd/Dream-World-IX/.harness-runs/s145" in text and "wb.read_oracle(" in text
        assert "controllers OFF and nobody at the keyboard" in text and "THE UNATTENDED LAW" in text
        assert "deploy_field.py" not in text and "build_memoria" not in text and "49201" in text
        assert 'grep -qE "^FieldScene 6603 " "$G/FF9CustomMap-world/DictionaryPatch.txt"' in text
        assert 'if grep -q "SWIRL-HANG" "$out"; then' in text and "re-running the leg ONCE" in text
    assert 'if [ "$DLL" != be9abacbd7b11d64 ]; then' in cal
    for frag in ("env COOP_TAPE_WORLD_BATTLE=1 COOP_TAPE_DIR=", "--want world-battle", "(want 0: b6 before and after the battle)",
                 "env COOP_PEER_PORT=49231 COOP_TAPE_PRE_S=100 COOP_TAPE_DIR=", "coop_tape_record.py --field 6603",
                 "env COOP_WB_LEG=decline COOP_CALIBRATE=1", "PASS  S145-WD-CAL", "latest-world-battle.json",
                 'run_leg "$OUT/c144/tape_world_battle.txt" env COOP_TAPE_WORLD_BATTLE=1', "HF-I / HF-REJOIN green",
                 '"worldbattle_cal144:6603:coop_world_battle:COOP_CALIBRATE=1"',
                 "env COOP_WB_LEG=battle COOP_CALIBRATE=1", "env COOP_WB_LEG=held COOP_CALIBRATE=1",
                 "env COOP_CALIBRATE=1 PYTHONIOENCODING=utf-8 py tools/harness/duo.py $SCN/coop_world_battle.py",
                 "coop-tapes/world-battle", "coop-tapes/held-6603", "PASS  S145-WB-CAL", "PASS  S145-HF-CAL"):
        assert frag in cal, frag
    assert cal.index("wb.read_oracle(") < cal.index("env COOP_TAPE_WORLD_BATTLE=1") \
        < cal.index("coop_tape_record.py --field 6603") < cal.index('bash "$SB"') < cal.index("env COOP_WB_LEG=battle") \
        < cal.index("env COOP_WB_LEG=held") < cal.index("py tools/harness/duo.py")
    assert "HF-HOLD" not in cal and "ls -t \"$WBDIR\"" not in cal and "ls -t \"$WBDIR\"" not in full   # the pointer, never the newest
    assert 'if [ -z "${S145_DLL:-}" ]; then' in full and '[ "$DLL" != "$S145_DLL" ]' in full and "be9abacbd7b11d64" in full
    assert "env COOP_WB_LEG=decline \"COOP_TAPE=$T\"" in full and "latest-world-battle.json" in full
    for frag in ('"worldbattle:6603:coop_world_battle"', '"worldbattle_lever:6603:coop_world_battle:COOP_CALIBRATE=1"',
                 "env COOP_WB_LEG=battle \"COOP_TAPE=$T\"", "env COOP_WB_LEG=battle COOP_CALIBRATE=1",
                 "env COOP_WB_LEG=held", "py tools/harness/duo.py $SCN/coop_world_battle.py",
                 '"diorama_return:30602:coop_diorama_return"', '"wait_parity:30602:coop_battle_wait_parity"',
                 '"leaderguard:30602:coop_leader_guard"', '"start_hold:30602:coop_battle_start_hold"',
                 '"worldwait:6603:coop_world_wait"', '"worldwait_lever:6603:coop_world_wait:COOP_CALIBRATE=1"',
                 "env COOP_WORLD_LEG=rejoin", "env COOP_WORLD_LEG=wait", "py tools/harness/duo.py $SCN/coop_world_wait.py",
                 "for l in cal readopt s119 s120-battle s121; do", "COOP_CUT_LEG=s120-world", "S120_WORLD_TAPE",
                 "coop_dress_wire.py", "for f in 30602 30604 30605 30606 30607 30608 30609; do"):
        assert frag in full, frag
    assert full.index('"worldbattle:6603') < full.index('"worldbattle_lever:6603') < full.index("COOP_WB_LEG=battle") \
        < full.index("COOP_WB_LEG=held") < full.index("duo.py $SCN/coop_world_battle.py") < full.index('"leaderguard:30602')



# ------------------------------------------------------------------------------------------------ fix1: the T2 decline leg
DECLINE_ALL = ["T2-TAPE", "T2-PEER", "S145-WD-I", "S145-WD-DECL", "T2-SAVE", "T2-INI", "S145-WD-SWIRL"]


def test_the_decline_leg_declines_on_s145_calibrates_on_s144_and_reds_unprojected(tables):
    """harness-watcher-decline-unbenched: THE WATCHER's DURABLE DECLINE on a replayed wire (decisions 3 + 4) -- aboard a chocobo the
    followed guest reports NONE on the host's battle (never BOOTING or DECLINED), names the vehicle line as its visit decline,
    counts ONE durable decline with ONE line, never boots, never reloads; on the s144 stand-in exactly WD-DECL red (no `vehicle`
    verb: never sent); under the `decline_unprojected` fault (the projection skipped) the guest boots aboard -- WD-DECL red."""
    r = _child({"runs": {"s145": {"kind": "t2", "leg": "decline"},
                         "s144": {"kind": "t2", "leg": "decline", "caps": "worldwait", "cal": True},
                         "unproj": {"kind": "t2", "leg": "decline", "faults": ["decline_unprojected"]}}})
    new, old, unproj = r["s145"], r["s144"], r["unproj"]
    assert new["red"] == [], {c: new["detail"][c] for c in new["red"]}
    assert new["all"] == DECLINE_ALL, new["all"]
    d = new["detail"]["S145-WD-DECL"]
    assert "the peer decoded ['NONE']" in d and "aboard a vehicle (travel mode 1)" in d and "the declined line 1x" in d, d
    assert old["red"] == sorted(tables["t2_pred"]["decline"]), old["red"]
    assert "S145-WD-CAL" in old["all"] and "S145-WD-CAL" not in old["red"]
    assert unproj["red"] == sorted(tables["t2_faults"]["decline"]["decline_unprojected"]), unproj["red"]
    assert "BOOTING" in unproj["detail"]["S145-WD-DECL"], unproj["detail"]["S145-WD-DECL"]


def test_a_battle_on_the_wire_before_the_guest_boarded_is_the_instruments_never_wd_decl():
    """rharness-decline-leg-no-aboard-guard (fix2): the stub puts the host's battle on the wire BEFORE `vehicle 1` returns (the
    on-foot guest rightly boots it, or the verb meets that boot) -- WD-DECL reads 'not reached: the instrument', never a judged
    engine verdict; the instrument rows before it stay green."""
    r = _run("t2", leg="decline", board_late=True)
    d = r["detail"]["S145-WD-DECL"]
    assert "S145-WD-DECL" in r["red"] and d.startswith("not reached: the instrument"), d
    assert "before the guest was aboard" in d, d
    # [fix3] the REFUSAL branch (its `vehicle 1` text, never the comparison's stamps), and the instrument row red with it (as the
    # held leg reads a missed window): exactly WD-DECL and WD-I
    assert "`vehicle 1`" in d and ", aboard " not in d, d
    assert r["red"] == ["S145-WD-DECL", "S145-WD-I"], {c: r["detail"][c] for c in r["red"]}
    assert "before the guest was aboard" in r["detail"]["S145-WD-I"], r["detail"]["S145-WD-I"]


def test_a_read_back_that_lands_after_the_battle_is_the_instruments_by_the_comparison():
    """v-rharness-decline-leg-no-aboard-guard-comparison-unpinned (fix3): the real `vehicle 1` boards at once (the guest declines
    the battle aboard), but the verb's read-back returns only after the stub put the host's battle on the wire -- the battle anchor
    sits before the aboard stamp (st0's own read, the judge's baseline): the instrument's by the COMPARISON alone (its battle /
    aboard stamps, never the refusal's text), WD-I red with it -- never the judged red ('declines 1->1') a baseline read after the
    decline would give."""
    r = _run("t2", leg="decline", board_slow=True)
    d = r["detail"]["S145-WD-DECL"]
    assert r["red"] == ["S145-WD-DECL", "S145-WD-I"], {c: r["detail"][c] for c in r["red"]}
    assert d.startswith("not reached: the instrument") and "battle " in d and ", aboard " in d and "`vehicle 1`" not in d, d
    assert "before the guest was aboard" in r["detail"]["S145-WD-I"], r["detail"]["S145-WD-I"]


@pytest.mark.parametrize("how", ("slow", "hang"))
def test_a_swirl_the_claim_does_not_see_reds_wd_decl_or_is_a_swirl_hang(how):
    """v-rharness-wd-decl-no-ui-witness-swirl-blind (fix3): after an honest decline the guest's face becomes a world boot's SWIRL
    with netsync's `booted` claim UNSET (WorldHUD -- nothing on the swirl path writes the UI state -- on SwirlScene, the WorldMap
    level gone: world.ticks -1). Still in its swirl at the window's end (`slow`): WD-DECL red on the swirl witness alone (every
    other term green: NONE, the decline counted once, its line, no claim, monotonic live ticks). Quiet there (`hang`): SWIRL-HANG
    whatever the claim says -- WD-SWIRL red, WD-DECL 'not reached: SWIRL-HANG' (the claim-gated check let it pass green)."""
    r = _run("t2", leg="decline", decline_swirl=how)
    d = r["detail"]["S145-WD-DECL"]
    if how == "slow":
        assert r["red"] == ["S145-WD-DECL"], {c: r["detail"][c] for c in r["red"]}
        assert "WorldHUD on SwirlScene" in d and "the peer decoded ['NONE']" in d and "declines 0->1" in d, d
        assert "booted on no sample" in d and "(monotonic)" in d and "the declined line 1x" in d, d
    else:
        assert r["red"] == ["S145-WD-DECL", "S145-WD-SWIRL"], {c: r["detail"][c] for c in r["red"]}
        assert "SWIRL-HANG at the decline's watch" in r["detail"]["S145-WD-SWIRL"], r["detail"]["S145-WD-SWIRL"]
        assert d.startswith("not reached: SWIRL-HANG"), d


def test_a_guest_that_leaves_the_world_map_mid_fight_reds_wd_decl_through_its_window():
    """c3-v-rharness-wd-decl-no-ui-witness-cut-not-rejoin-callsite-unpinned (fix3-r2): the REAL call site -- _t2_decline's window
    through decline_window -- driven on the stand-in. After an HONEST decline (the report NONE, the decline counted once, its line)
    the guest LEAVES the world map onto 6603 while the host's fight is still on the wire, before its entry into 300 (decision 3: a
    declined guest stays frozen): that FieldHUD is judged inside WD-DECL's window -- red, its field named -- never cut away as a
    rejoin (fix2's inline cut at any FieldHUD read this run green: 'off the world map on no sample')."""
    r = _run("t2", leg="decline", leave_world=6603)
    d = r["detail"]["S145-WD-DECL"]
    assert r["red"] == ["S145-WD-DECL"], {c: r["detail"][c] for c in r["red"]}
    assert "LEFT the world map before the host's entry: field [6603]" in d and "FieldHUD 6603" in d, d
    assert "the peer decoded ['NONE']" in d and "declines 0->1" in d and "the declined line 1x" in d, d   # the decline honest


def test_a_guest_that_leaves_onto_the_ice_cavern_mid_fight_reds_wd_decl():
    """...-cut-not-rejoin-callsite-unpinned-ice-cavern-leave-green (fix3b): the same mid-fight leave, onto 300 itself -- the Ice
    Cavern tile every T2 leg parks the guest on, and the follow's own target. The watch used to stop at the guest's first
    FieldHUD, long before the host's entry reached the wire, so the window went unanchored and the 300 cut spared the leave as a
    'rejoin' (green). Now the watch runs to the host's entry and the FieldHUD is judged inside [bt, enter]: red, its field named."""
    r = _run("t2", leg="decline", leave_world=300)
    d = r["detail"]["S145-WD-DECL"]
    assert r["red"] == ["S145-WD-DECL"], {c: r["detail"][c] for c in r["red"]}
    assert "LEFT the world map before the host's entry: field [300]" in d and "FieldHUD 300" in d, d
    assert "the peer decoded ['NONE']" in d and "declines 0->1" in d and "the declined line 1x" in d, d   # the decline honest


# ------------------------------------------------------------------------------------------------ fix1: the tape's place around a battle
def test_the_tape_reads_the_place_around_a_battle_past_the_swirl_the_lead_and_the_tail():
    """harness-tape-where-adjacent-frame: on EVERY recorded host tape the state frames adjacent to a battle's type-1 run are the swirl
    ('other'), the gMode-2 lead and the result tail ('battle') -- never the place. tape_battle_where reads the place past them: the
    world battle's synthetic tape (in the REAL shape now) reads 'world' before and after (a world-map battle: wb3-wb5, the pointer,
    `where --want world-battle`, after_b6), a field tape with section 7 'field' before and after; the old adjacent-frame reader
    reads 'battle' on both (the red that kept every recorded world-battle tape out)."""
    pb = _pb()
    cp = pb.coop_peer_module()
    world = pb.synthetic_world_battle_tape(cp)
    seg = cp.tape_battle_where(world)["battles"][0]
    assert (seg["said_before"], seg["said_after"], seg["world"]) == ("world", "world", True), seg
    field = pb.synthetic_tape(cp, sec7=True, field=6603)
    fseg = cp.tape_battle_where(field)["battles"][0]
    assert (fseg["said_before"], fseg["said_after"], fseg["field_before"], fseg["field_after"], fseg["world"]) == \
        ("field", "field", 6603, 6603, False), fseg
    assert cp.tape_where(field)["world_battles"] == 0 and cp.tape_where(world)["world_battles"] == 1

    def adjacent(records):                                  # the pre-fix1 reader: the frames next to the type-1 run
        raw = cp.tape_battles(records)[0]
        before = after = None
        for r, w, p in cp.host_frames(records):
            if w != cp.TYPE_STATE:
                continue
            body = cp.BW.old_try_read_section(p, cp.BW.SECTION_DIALOG)
            v = cp.BW.parse_dialog_section(body) if body is not None else None
            said = cp._said(v["flags"] if v is not None else None)
            if r.t < raw["start"]:
                before = said
            elif r.t > raw["end"] and after is None:
                after = said
        return before, after
    assert adjacent(world) != ("world", "world") and adjacent(field) == ("battle", "battle"), (adjacent(world), adjacent(field))
    facts = pb.world_battle_tape_facts(world, cp)
    assert all(facts[k]["ok"] for k in ("wb3", "wb4", "wb5")), {k: facts[k]["why"] for k in ("wb3", "wb4", "wb5")}
    assert pb.tape_facts(world, cp, field=pb.WORLD_TAPE_FIELD)["after_b6"] is True
    # a place said only OUTSIDE the window is no place: a host that stood 'other' for longer than WHERE_BEFORE_S reads None
    assert cp.WHERE_BEFORE_S >= pb.SYNTH_SWIRL_S + pb.SYNTH_LEAD_S and cp.WHERE_AFTER_S >= 4.4


# ------------------------------------------------------------------------------------------------ fix1: the recorder's instrument
def test_the_world_battle_recorder_records_a_swirl_hang_as_the_instrument():
    """harness-recorder-no-swirl-instrument: the recorder's world battle -- the trigger of the 1-in-26 short-swirl stall -- writes the
    state every frame across it and turns a hang into decision 11's instrument (coop_world_battle.hang_check: the logs archived, a
    frame grabbed, 'SWIRL-HANG' in REC-WB), and cal145 re-records ONCE (run_leg) then takes the tape the pointer names."""
    src = (SCENARIOS / "coop_tape_record.py").read_text(encoding="utf-8").replace("\r\n", "\n")
    i = src.index("        g.world_battle(WB_SCENE, group=WB_GROUP, rand=True)")
    head, tail = src[i - 400:i], src[i:i + 1200]
    assert "wbm._state_every(g, 1)" in head and "import coop_world_battle as wbm" in head
    assert 'wbm.hang_check(g, "the recorder\'s world battle")' in tail and "except wbm.SwirlHang as hang:" in tail
    assert "SWIRL-HANG -- the instrument" in tail and "wbm._state_every(g, 2)" in tail
