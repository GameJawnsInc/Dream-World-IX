"""[ff9mapkit netsync s165] THE s165 BENCH's REPO HALF -- studies/test-harness/scenarios/coop_world_follow.py (the SOLO leg and its
three sections, the T2 `walk` leg, the DUO leg) and the regression re-key it shares with coop_world_wait.py (follow_off).

tests/test_world_coop_harness.py pins the contract (the keys, the verb, the stand-in's `worldfollow` rung and its fault levers). This
file pins what the BENCH builds on them:

  * EVERY LEG SMOKED AGAINST THE STAND-IN through the real Session: the solo leg on the s165 stand-in (every row green), on the s164
    one (exactly OLD_PREDICTED red -- and NOTHING new sent: no `worldfollow` op, no `savemenu`), under each calibration lever (exactly
    LEVER_PREDICTED[lever] red); the T2 walk leg through a STUB REPLAY that feeds the tape's own section-0 pose to the stand-in's one
    reader (FakeGame.host_world_pose) -- green on s165, OLD on s164, the lever's rows under `worldfollow off`; the duo on two stand-ins
    joined by a stub LINK that carries the host's own world pose the same way.
  * EVERY CHECK CAN FAIL: each fault lever (FG.WORLD_FOLLOW_FAULTS) turns EXACTLY its SOLO_FAULT_REDS rows red, a fault family each on
    the T2 and duo legs (T2_FAULT_REDS / DUO_FAULT_REDS); the PURE judges go red on each wrong shape (fed hand-built states) -- the rows
    no stand-in fault reaches (R3's lever words, the save files, the seam bracket, the heartbeat witness, the shared-file instrument).

Every scenario-touching test runs in a CHILD process: a scenario puts its own dir on sys.path and reads its COOP_* knobs at import.
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
wf = load("coop_world_follow")
cw, pb, cb = wf.cw, wf.pb, wf.cb
SPEED = 8.0
# the bench's own waits, shortened for a stand-in that runs at 600 fps (every JUDGED threshold stays the bench's)
for k, v in dict(REFUSE_S=1.0, START_S=4.0, LEAVE_S=12.0, FIELD_S=10.0, HOME_S=10.0, DOT_S=2.0, STALE_S=0.6, PICK_S=0.3,
                 HOLD_SETTLE_S=0.3, TILE_SLACK_S=12.0, REJOIN_S=15.0, FO_S=12.0, DUO_HOME_S=12.0, REPLAY_SPEED=SPEED).items():
    setattr(wf, k, v)
for k, v in dict(FIELD_S=10.0, DIAL_S=8.0, REJOIN_S=12.0).items():
    setattr(cw, k, v)
FAKES, SENT = [], []
KEEPER = {"x": 1600.0, "z": -700.0, "r": 40.0, "talk_r": 80.0, "sid": 12}

def root(ini=None):
    t = pathlib.Path(tempfile.mkdtemp())
    (t / "x64").mkdir()
    (t / "x64" / "FF9.exe").write_bytes(b"MZ")
    (t / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    (t / "FF9CustomMap").mkdir()
    (t / "FF9CustomMap" / "DictionaryPatch.txt").write_text("FieldScene 6603 31 FARSHORE FARSHORE 6603\n", encoding="utf-8")
    if ini:
        (t / "Memoria.ini").write_text(ini, encoding="utf-8")
    sav = t / "x64" / "ff9harness" / "save"                   # the stand-in's sandboxed save path (its `save_path`'s folder)
    sav.mkdir(parents=True)
    (sav / "SavedData_ww.dat").write_bytes(bytes(64))
    return t

def fake_for(t, run):
    f = FG.FakeGame(t, fps=600, walkmesh=(-2000.0, -3000.0, 2000.0, 2000.0))
    if run.get("caps"):
        f.netsync_caps = FG.caps_through(run["caps"])
    if run.get("s167"):                                         # [ff9mapkit netsync s167] round B's piece "b" (default: the deployed s166)
        f.world_walk_pieces = tuple(FG.FAKE_WORLD_WALK_S167_PIECES)
    f.regions = {6603: [{"zone": cw.FS_DOOR, "world": cw.WORLD, "world_at": list(cw.FS_LANDING)}]}
    f.exit_frames = 900
    f.overworld = {"speed": 2.0, "turn": 2.8125, "cam": 0.0, "lag": 1}
    f.world_locations = {cw.ICE_CAVERN: (cw.ICE_TILE[0], cw.ICE_TILE[1], 2.0)}
    f.world_swirl_frames, f.world_exit_frames = 40, 40
    f.world_follow_faults = set(run.get("faults", ()))
    f.world_out_fade_frames = int(run.get("fade", 600))        # 1 s of wall time: room to act inside the fade
    f.blockers = {6603: [dict(KEEPER)]}                         # Mogdrift, the keeper of the landing (a talk object)
    real_ns = f._netsync
    def ns(args, _real=real_ns, _f=f):                          # `netsync talk <uid>` opens the keeper's line (the engine's talk
        _real(args)                                             # relay replay); the stand-in only records the uid
        if args and str(args[0]).lower() == "talk":
            _f.texts, _f._talk_line = ["Kupo... nothing out here but wind and gulls."], True
        if args and str(args[0]).lower() == "worldfollow":
            SENT.append(" ".join(str(a) for a in args[1:]))
    f._netsync = ns
    real_step = f._menu_step
    def step(button, _real=real_step, _f=f):                    # ...and the guest's own Confirm closes it (an unlocked local line)
        if getattr(_f, "_talk_line", False) and str(button).lower() in ("confirm", "ok") and _f.texts:
            _f.texts, _f._talk_line = [], False
            return
        return _real(button)
    f._menu_step = step
    FAKES.append(f)
    return f

def session(t, f):
    g = Session(game_path=t, run_dir=t / "run", save_dir=t / "player-saves", pid_probe=lambda: [],
                launcher=lambda exe, f=f: f.start(), boot_timeout=15.0, verbose=False)
    g._booted_once = True
    return g

def rows_of(checks):
    rows = [(r["what"].split(":")[0], bool(r["ok"]), r["detail"][:600]) for r in checks]
    return {"red": sorted(c for c, ok, _d in rows if not ok), "all": [c for c, _ok, _d in rows],
            "detail": {c: d for c, _ok, d in rows}}

def write_tape(path, recs, head=None):
    head = json.dumps(head or {"tool": "stub", "started": _dt.datetime.now().isoformat()}).encode("utf-8")
    body = b"".join(struct.pack("<dBI", r.t, r.dir, len(r.payload)) + r.payload for r in recs)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"F9TAPE01" + struct.pack("<I", len(head)) + head + body)

class StubIni:
    def __init__(self, ini, values, *, label, run_dir=None, backup_root=None):
        self.values = dict(values)
    def apply(self):
        FAKES[-1].apply_ini(self.values)
        return "the stub ini"
    def update(self, values):
        self.values.update(values)
        FAKES[-1].apply_ini(self.values)
        return "the stub ini updated"
    def restore(self):
        return True, "restored (stub)"

class _Peer(pb.PeerProc):
    def _say(self, msg):
        n = _dt.datetime.now()
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(f"[coop-peer {n:%H:%M:%S}.{n.microsecond // 1000:03d}] {msg}\n")
    def _arg(self, name):
        return self.args[self.args.index(name) + 1] if name in self.args else None

def feed_pose(f, payload):
    """THE ONE READER on the stand-in: a host state frame's section-0 pose (coop_peer's decode, the engine's offsets) onto the
    followed client's host cache -- only while section 7 says b6 and the pose lies inside the torus."""
    fp = CP.frame_pose(payload)
    p = fp.get("pose")
    if fp.get("b6") and p is not None and p.get("torus"):
        f.host_world_pose(p["x"], p["z"], idx=p["idx"], mode=p["mode"], entrance=p["entrance"], veg=p["choco"], yaw=p["yaw"],
                          story=p["story"])

class StubReplay(_Peer):
    """coop_peer replay-host's stand-in: it connects once the stand-in's transport exists, then replays the tape's host frames
    (SPEED x) onto the followed client's seams -- the lane's field, section 7's flags, section 0 and its POSE (feed_pose)."""
    def start(self):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.started = _dt.datetime.now()
        self._halt = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()
    def _run(self):
        f = FAKES[-1]
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
        frames = list(CP.host_frames(recs))
        t0 = frames[0][0].t
        _w = f.netsync_wire_now()   # [ff9mapkit netsync s166] what replay-host logs before REPLAY start (the stand-in's own wire)
        _send, _how = CP.replay_send_wire("auto", _w, CP.tape_wire(recs))
        self._say(CP.GUEST_WIRE_LINE.format(guest=_w, send=_send, how=_how))
        self._say(f"REPLAY start: tape {t0:.2f} s -> now; {len(frames)} host frame(s) up to tape {frames[-1][0].t:.2f} s")
        wall0, field, flags, story, first = time.time(), None, -1, None, True
        for r, w, p in frames:
            due = wall0 + (r.t - t0) / SPEED
            while time.time() < due and not self._halt.is_set():
                time.sleep(0.01)
            if self._halt.is_set():
                return
            fresh_pose = None
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
                fresh_pose = p
            if field is None:
                continue
            if first:
                f.follow_session(field, flags=flags, fresh=True, story=story, pair_kick=True)
                first = False
            else:
                f.host_at(field, flags=flags, story=story)
            if fresh_pose is not None and self.pose:
                feed_pose(f, fresh_pose)
    pose = True
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

def stubs(module_pb):
    module_pb.IniGuard = StubIni
    module_pb.port_free = lambda port, host="127.0.0.1": (True, "")

def solo(run):
    t = root("[Netsync]\nEnabled = 0\nFollowHost = " + ("1" if run.get("follow_host", True) else "0") + "\n")
    cw.read_oracle = lambda game: {"problems": {}, "facts": {"stand-in": True}}
    f = fake_for(t, run)
    f.wf_follow_host_cfg = bool(run.get("follow_host", True))
    cb.CALIBRATE = bool(run.get("cal"))
    wf.LEVER = run.get("lever", "out")
    wf.LEG = "solo"
    wf.SOLO_SECTIONS = tuple(run.get("sections") or wf.SECTIONS)
    with session(t, f) as g:
        wf.run(g)
        out = rows_of(list(g.checks))
    out["sent"] = list(SENT)
    out["savemenu"] = sum(1 for ln in (t / "Memoria.log").read_text(encoding="utf-8", errors="replace").splitlines()
                          if BW.LOG_SAVE_REFUSED in ln)
    return out

def walk(run):
    t = root()
    stubs(pb)
    StubReplay.pose = bool(run.get("pose", True))
    pb.PeerProc = StubReplay
    tape = t / "tape-host6603-world-walk-s164.f9tape"
    write_tape(tape, pb.synthetic_world_walk_tape(CP, tile_s=float(run.get("tile_s", 65.0))))
    os.environ["COOP_TAPE"] = str(tape)
    f = fake_for(t, run)
    cb.CALIBRATE = bool(run.get("cal"))
    wf.LEG = "walk"
    with session(t, f) as g:
        wf.run(g)
        out = rows_of(list(g.checks))
    out["sent"] = list(SENT)
    return out

class Link(threading.Thread):
    """The duo's stub TRANSPORT: the host stand-in's place (its lane, section 7's flags as HostDialogFlags says them, its story) and
    its MAPJUMP intent onto the guest's followed-client seams -- and, s165's one reader, the host's OWN world pose while it stands on
    the world map (its section 0's 64-72 / [102] / [190] as the engine writes them)."""
    def __init__(self, host, guest):
        super().__init__(daemon=True)
        self.h, self.g, self.halt = host, guest, threading.Event()
    def run(self):
        sent = None
        while not self.halt.is_set():
            h = self.h
            self.g.host_at(h.host_lane_field(), flags=h.host_dialog_flags(), story=bytes(h.story_bytes))
            w = h.world
            if h.ui_state == "WorldHUD" and w.get("x") is not None and w.get("id"):
                self.g.host_world_pose(float(w["x"]), float(w["z"]), idx=int(w["id"]) - 9000, mode=int(w.get("vehicle") or 0))
            it = h.host_field_intent
            if it is not None and it != sent:
                sent = it
                self.g.host_intent(it[1])
            time.sleep(0.02)

class StubDuo:
    def __init__(self, host, guest):
        self.host, self.guest, self.strict, self.rows, self.notes = host, guest, True, [], []
    def check(self, ok, what, detail="", *, role=None, cid=None):
        self.rows.append((cid, bool(ok), str(detail)[:600]))
        return bool(ok)
    def note(self, msg):
        self.notes.append(msg)

def duo(run):
    th, tg = root(), root()
    fh, fgst = fake_for(th, run), fake_for(tg, run)
    fh.world_exit_frames = fgst.world_exit_frames = int(run.get("exit_frames", 240))
    fgst.coop_field_follow = True                               # the guest follows the host's warp back onto 6603 (D-FO2)
    cb.CALIBRATE = bool(run.get("cal"))
    gh, gg = session(th, fh), session(tg, fgst)
    with gh, gg:
        for g in (gh, gg):
            g.newgame(settle=0)
            g.warp(cw.FARSHORE)
        fh.netsync.update(enabled=True, role="host", instance=True)
        fh.story_bytes[pb.MARKER_BYTE] = pb.MARKER_VALUE
        fgst.follow_session(cw.FARSHORE, flags=BW.HF_ON_FIELD | BW.HF_CONTROL, fresh=True,
                            story=bytes(fh.story_bytes), pair_kick=True)
        link = Link(fh, fgst)
        link.start()
        gg.wait_for(lambda s: (s.netsync or {}).get("session", {}).get("mirroring") is True, timeout=5, what="paired")
        d = StubDuo(gh, gg)
        try:
            wf.run_duo(d)
        finally:
            link.halt.set()
        return {"red": sorted(c for c, ok, _d in d.rows if not ok), "all": [c for c, _ok, _d in d.rows],
                "detail": {c: dd for c, _ok, dd in d.rows}, "sent": list(SENT)}

kinds = {"solo": solo, "walk": walk, "duo": duo}
REAL_WALK_OFF = cw.walk_off
def one(run):
    SENT.clear()                                                # each run's own sends
    # [ff9mapkit netsync s167] `walkset` False stands round B's re-key down (cw.walk_off: P1's, the walk leg's, the duo's)
    cw.walk_off = REAL_WALK_OFF if run.get("walkset", True) else (lambda g, **k: (True, "s167 re-key: STOOD DOWN (the test)"))
    return kinds[run["kind"]](run)
results = {name: one(run) for name, run in doc.get("runs", {}).items()}
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
spec = importlib.util.spec_from_file_location("coop_world_follow", os.path.join(scen, "coop_world_follow.py"))
wf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wf)
print(json.dumps({
    "solo_all": list(wf.SOLO_ALL), "solo": list(wf.solo_catalog(False)), "solo_cal": list(wf.solo_catalog(True, lever="out")),
    "sections": {k: list(v) for k, v in wf.SECTION_ROWS.items()},
    "old": list(wf.OLD_PREDICTED), "lever": {k: list(v) for k, v in wf.LEVER_PREDICTED.items()},
    "faults": {k: list(v) for k, v in wf.SOLO_FAULT_REDS.items()},
    "t2": list(wf.t2_catalog(False)), "t2_rows": list(wf.T2_ROWS), "t2_old": list(wf.T2_OLD_PREDICTED),
    "t2_lever": {k: list(v) for k, v in wf.T2_LEVER_PREDICTED.items()}, "t2_faults": {k: list(v) for k, v in wf.T2_FAULT_REDS.items()},
    "duo": list(wf.DUO_CHECKS), "duo_old": list(wf.DUO_OLD_PREDICTED), "duo_faults": {k: list(v) for k, v in wf.DUO_FAULT_REDS.items()},
    "consts": {"FARSHORE": wf.FARSHORE, "ICE_TILE": list(wf.ICE_TILE), "FS_LANDING": list(wf.FS_LANDING), "WORLD": wf.WORLD,
               "PROBE": wf.PROBE, "LEGS": list(wf.LEGS), "LEG": wf.LEG, "LEVERS": list(wf.LEVERS), "FAR_U": wf.FAR_U,
               "POSE_TOL": wf.POSE_TOL, "DOT_MARK_SXSY": list(wf.DOT_MARK_SXSY), "DOT_MARK": list(wf.DOT_MARK),
               "WORLD11_DEFAULT": list(wf.WORLD11_DEFAULT), "DEFAULT_MIN_U": wf.DEFAULT_MIN_U,
               "SUPERSEDE_DELAY_MS": wf.SUPERSEDE_DELAY_MS, "EVENT_IDXS": list(wf.EVENT_IDXS), "RANGE_IDX": wf.RANGE_IDX,
               "PAIR": wf.PAIR, "PORT": wf.PORT},
    "doc": " ".join((wf.__doc__ or "").split())}))
'''


@pytest.fixture(scope="module")
def tables() -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _TABLES, str(SCENARIOS), str(REPO / "tools")], env=env,
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-3000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


# ================================================================================================ the tables
def test_the_tables_are_the_docstring_and_each_others(tables):
    """Every row the docstring names; each prediction and fault row a real row; the faults table names exactly the stand-in's levers;
    the T2 / duo tables likewise; the route constants are coop_world_wait's (imported, never copied)."""
    doc, every = tables["doc"], set(tables["solo_all"]) | set(tables["t2"]) | set(tables["duo"])
    for cid in every:
        short = cid.replace("S165-WK-", "WK-").replace("S165-D-", "D-").replace("S165-", "")
        assert short in doc, cid
    assert set(tables["old"]) <= set(tables["solo_all"]) and not set(tables["old"]) & {"S165-INI", "S165-OR", "S165-S0", "S165-R"}
    assert set(tables["lever"]) == set(tables["consts"]["LEVERS"])
    for lever, rows in tables["lever"].items():
        assert rows and set(rows) <= set(tables["solo_all"]), lever
    assert "S165-LEVER" not in tables["lever"]["out"] and set(tables["lever"]["out"]) == set(tables["sections"]["out"]) - {"S165-LEVER"}
    assert set(tables["faults"]) == set(FG.WORLD_FOLLOW_FAULTS)
    assert all(set(v) <= set(tables["solo_all"]) for v in tables["faults"].values())
    assert set(tables["t2_old"]) <= set(tables["t2_rows"]) and set(tables["t2_lever"]["out"]) <= set(tables["t2_old"])
    assert all(set(v) <= set(tables["t2_rows"]) and k in FG.WORLD_FOLLOW_FAULTS for k, v in tables["t2_faults"].items())
    assert set(tables["duo_old"]) <= set(tables["duo"]) and not set(tables["duo_old"]) & {"S165-D0", "S165-D-SHARED"}
    assert all(set(v) <= set(tables["duo"]) and k in FG.WORLD_FOLLOW_FAULTS for k, v in tables["duo_faults"].items())
    assert tables["solo_cal"][-1] == "S165-CAL" and tables["solo"][-1] == "S165-R"
    c = tables["consts"]
    assert (c["FARSHORE"], c["WORLD"], c["ICE_TILE"], c["FS_LANDING"]) == (6603, 9011, [1197.37, -796.7], [68.0, -444.0])
    assert c["PROBE"] == "netsync.world.out" and c["LEGS"] == ["solo", "walk"] and c["LEG"] == "solo" and c["PAIR"] == {"field": 6603}
    assert c["SUPERSEDE_DELAY_MS"] == BW.SWAP_DELAY_RANGE[1]
    assert c["EVENT_IDXS"] == sorted(w - BW.WORLD_BASE for w in BW.EVENT_WORLD_MAPS) and c["RANGE_IDX"] == BW.WORLD_IDX_MAX + 1


def test_the_live_pose_spots_discriminate_in_plain_and_never_by_the_torus(tables):
    """THE DISTANCE TRAP (K1 / E1's review): ICE_TILE stands 1183 u from FS_LANDING in plain x/z but only ~538 u the short way round
    the torus -- FAR_U (1000) is a PLAIN-distance threshold; the tile is ~59 u from WORLD11's default (DEFAULT_MIN_U 30 discriminates
    it); the marker's raw map point is battlewire's navi_get_pos (the engine's w_naviGetPos twin)."""
    c = tables["consts"]
    tile, land, dflt = c["ICE_TILE"], c["FS_LANDING"], c["WORLD11_DEFAULT"]
    plain = ((tile[0] - land[0]) ** 2 + (tile[1] - land[1]) ** 2) ** 0.5
    assert plain >= c["FAR_U"] > BW.world_torus_distance(tile, land)
    d = ((tile[0] - dflt[0]) ** 2 + (tile[1] - dflt[1]) ** 2) ** 0.5
    assert c["POSE_TOL"] < c["DEFAULT_MIN_U"] < d
    sx, sy = BW.navi_get_pos(*c["DOT_MARK"], 0)
    assert (round(sx, 3), round(sy, 3)) == tuple(c["DOT_MARK_SXSY"])


# ================================================================================================ SOLO
def test_the_solo_leg_is_green_on_the_s165_stand_in(tables):
    r = _run("solo")
    assert r["all"] == tables["solo"], r["all"]
    assert r["red"] == [], {c: r["detail"][c] for c in r["red"]}
    # the levers and the fabricated host went out, and every one came back released at the end (the R row)
    assert any(s.startswith("host ") for s in r["sent"]) and "off" in r["sent"] and r["savemenu"] >= 1


def test_the_solo_leg_calibrates_on_s164_and_sends_nothing_new(tables):
    """OLD: the s164 stand-in publishes no `netsync.world.out` -- exactly OLD_PREDICTED red, S165-CAL green, and the bench SENT no
    `worldfollow` op and no `savemenu` (s164 fails the sub-verb closed; an unknown verb would only be refused after the step)."""
    r = _run("solo", caps="swap", cal=True)
    assert r["all"] == tables["solo_cal"]
    assert sorted(set(r["red"]) - {"S165-CAL"}) == sorted(tables["old"]), r["red"]
    assert "S165-CAL" not in r["red"], r["detail"]["S165-CAL"]
    assert r["sent"] == [] and r["savemenu"] == 0


@pytest.mark.parametrize("lever,sections", [("out", ("out",)), ("dot", ("dot",)), ("r3", ("save",)), ("saveguard", ("save",))])
def test_each_calibration_lever_reds_exactly_its_rows(tables, lever, sections):
    r = _run("solo", cal=True, lever=lever, sections=list(sections))
    pred = set(tables["lever"][lever])
    assert set(r["red"]) - {"S165-CAL"} == pred, {c: r["detail"][c] for c in set(r["red"]) ^ pred}
    assert "S165-CAL" not in r["red"], r["detail"]["S165-CAL"]


#: the smallest section set a fault's rows live in (each run carries only those sections: the rest of the leg is never reached)
def _sections_for(rows, tables) -> list:
    out = [sec for sec, cids in tables["sections"].items() if set(rows) & set(cids)]
    return out or ["save"]


@pytest.mark.parametrize("fault", FG.WORLD_FOLLOW_FAULTS)
def test_each_world_follow_fault_turns_exactly_its_solo_rows_red(tables, fault):
    want = set(tables["faults"][fault])
    sections = _sections_for(want, tables)
    r = _run("solo", faults=[fault], sections=sections)
    assert set(r["red"]) == want, (sections, {c: r["detail"][c] for c in set(r["red"]) ^ want})


def test_the_ini_refuses_a_bench_without_followhost():
    """S165-INI is a precondition that CAN fail: FollowHost 0 (the fabricated host's gate) stops the leg before anything is sent."""
    r = _run("solo", follow_host=False, sections=["save"])
    assert "S165-INI" in r["red"] and "FollowHost" in r["detail"]["S165-INI"] and r["sent"] == []


# ================================================================================================ T2
def test_the_walk_leg_is_green_on_s165_old_on_s164_and_reds_the_levers_rows(tables):
    """The T2 walk leg against the synthetic world-walk tape (its pose fed to the stand-in's one reader): green on s165 (the hold,
    the release, the landing at the TAPE's own tile pose, frozen, the dot at the tape's pose, the rejoin into 300); on s164 exactly
    T2_OLD_PREDICTED red and nothing sent; under `worldfollow off` exactly T2_LEVER_PREDICTED['out'] red (the guest then walks out on
    its own: FROZEN / DOT / REJOIN still green)."""
    runs = _child({"runs": {"s165": {"kind": "walk"}, "s164": {"kind": "walk", "caps": "swap", "cal": True},
                            "lever": {"kind": "walk", "cal": True, "tile_s": 240.0}}})   # room for the guest's own walk out
    r = runs["s165"]
    assert r["all"] == tables["t2"], r["all"]
    assert r["red"] == [], {c: r["detail"][c] for c in r["red"]}
    assert "hold" in r["sent"] and "release" in r["sent"] and "clear" in r["sent"]
    old = runs["s164"]
    assert sorted(set(old["red"]) - {"S165-WK-CAL"}) == sorted(tables["t2_old"]), old["red"]
    assert "S165-WK-CAL" not in old["red"] and old["sent"] == []
    lev = runs["lever"]
    assert set(lev["red"]) - {"S165-WK-CAL"} == set(tables["t2_lever"]["out"]), {c: lev["detail"][c] for c in lev["red"]}


def test_the_walk_legs_pose_row_needs_the_tapes_pose_never_the_landing():
    """A check that cannot fail is not a check: with the stub's pose feed OFF the stand-in's host cache reads no section-0 pose, the
    guest never starts (why no_story) and WAIT / LEAVE / POSE go red -- the landing is the tape's pose or nothing."""
    r = _run("walk", pose=False)
    assert {"S165-WK-WAIT", "S165-WK-LEAVE", "S165-WK-POSE"} <= set(r["red"]), r["red"]


@pytest.mark.parametrize("fault", sorted(FG.WORLD_FOLLOW_FAULTS))
def test_each_fault_family_turns_exactly_its_walk_rows_red(tables, fault):
    if fault not in tables["t2_faults"]:
        pytest.skip("a solo-only fault family (the T2 leg's families: T2_FAULT_REDS)")
    want = set(tables["t2_faults"][fault])
    # a long tile stand: the guest's own walk out (never_starts) and the dot's wait fit inside it before the tape's 300; hold_ignored's
    # follow-out lands after the release's base (a 2 s fade: the base is read ~1.2 s after b6 on the wall, the start ~0.1 s after it),
    # so its start is read as BEFORE the release; the fade still ends well inside LEAVE_S on a loaded box
    r = _run("walk", faults=[fault], tile_s=240.0, fade=1200 if fault == "hold_ignored" else 600)
    assert set(r["red"]) == want, {c: r["detail"][c] for c in set(r["red"]) ^ want}


# ================================================================================================ the duo
def test_the_duo_is_green_on_s165_and_calibrates_on_s164(tables):
    runs = _child({"runs": {"s165": {"kind": "duo"}, "s164": {"kind": "duo", "caps": "swap", "cal": True}}})
    r = runs["s165"]
    assert [c for c in r["all"] if c != "S165-D-CAL"] == tables["duo"], r["all"]
    assert r["red"] == [], {c: r["detail"][c] for c in r["red"]}
    assert "hold" in r["sent"] and "release" in r["sent"]
    old = runs["s164"]
    assert sorted(set(old["red"]) - {"S165-D-CAL"}) == sorted(tables["duo_old"]), old["red"]
    assert "S165-D-CAL" not in old["red"] and old["sent"] == []


@pytest.mark.parametrize("fault", sorted(FG.WORLD_FOLLOW_FAULTS))
def test_each_fault_family_turns_exactly_its_duo_rows_red(tables, fault):
    if fault not in tables["duo_faults"]:
        pytest.skip("not a duo fault family (DUO_FAULT_REDS)")
    want = set(tables["duo_faults"][fault])
    r = _run("duo", faults=[fault])
    assert set(r["red"]) == want, {c: r["detail"][c] for c in set(r["red"]) ^ want}


# ================================================================================================ the pure judges
_JUDGES = r'''
import datetime as _dt, importlib.util, os, sys
scen, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
spec = importlib.util.spec_from_file_location("coop_world_follow", os.path.join(scen, "coop_world_follow.py"))
wf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wf)
from harness.channel import State
BW = wf.BW
TILE, LAND = wf.ICE_TILE, wf.FS_LANDING

def st(ui="WorldHUD", field=6603, world=9011, x=1197.37, z=-796.7, out=None, host=None, dot=None, block=True, ticks=10, r3=None,
       sg=None, freeze=None, vehicle=0, ctl=0, entrance=35, frame=1, save=None):
    ns = {"world": {"out": dict(BW.WORLD_OUT_SENTINELS, lever="on", state="idle", **(out or {})),
                    "host": dict(BW.WORLD_HOST_SENTINELS, **(host or {})), "dot": dict(BW.WORLD_DOT_SENTINELS, **(dot or {})),
                    "r3": dict({"lever": "act", "arms_from_9012": 0}, **(r3 or {})), "freeze": dict({"on": True}, **(freeze or {}))},
          "saveguard": dict({"refused": 0, "would_save": 0, "lever": "act", "last_why": None}, **(sg or {}))}
    doc = {"frame": frame, "ui_state": ui, "field": {"id": field if ui == "FieldHUD" else 0, "entrance": entrance},
           "world": {"id": world, "x": x, "z": z, "vehicle": vehicle, "ctl": ctl, "block_ready": block, "ticks": ticks},
           "netsync": ns}
    if save is not None:
        doc.update(save)
    return State(doc)

def red(row, why=None):
    ok, d = row
    assert not ok, d
    if why:
        assert why in d, d
def green(row):
    ok, d = row
    assert ok, d

# refusals: a sample off 6603, the wrong token, a start, the host never read, the line missing
base = st(ui="FieldHUD")
good = [st(ui="FieldHUD", out={"why": "riding"}, host={"b6": True}, frame=2)]
lines = ["[NetSync] world follow-out: waits: the host is riding"]
green(wf.judge_refusal(base, good, lines, ("riding",)))
red(wf.judge_refusal(base, good + [st(ui="WorldHUD", out={"why": "riding"}, host={"b6": True}, frame=3)], lines, ("riding",)), "LEFT")
red(wf.judge_refusal(base, [st(ui="FieldHUD", out={"why": "debounce"}, host={"b6": True})], lines, ("riding",)))
red(wf.judge_refusal(base, [st(ui="FieldHUD", out={"why": "riding", "starts": 1}, host={"b6": True})], lines, ("riding",)))
red(wf.judge_refusal(base, [st(ui="FieldHUD", out={"why": "riding"}, host={"b6": False})], lines, ("riding",)), "NEVER read")
red(wf.judge_refusal(base, good, [], ("riding",)), "waits line 0x")
green(wf.judge_refusal(base, good, [], ("riding",), logged=False))
# the debounce: a count that reached the seed is a wall clock
green(wf.judge_debounce(base, [st(ui="FieldHUD", out={"why": "debounce", "debounce_ms": 66}, host={"b6": True})]))
red(wf.judge_debounce(base, [st(ui="FieldHUD", out={"why": "debounce", "debounce_ms": 1300}, host={"b6": True})]), "debounce_ms")
# the supersede: a WorldHUD sample, no line, no count
sup = [st(ui="FieldHUD", field=300, out={"superseded": 1})]
sl = ["[NetSync] world follow-out: superseded by the host's field follow to 300"]
green(wf.judge_supersede(base, sup, sl))
red(wf.judge_supersede(base, [st(ui="WorldHUD", out={"superseded": 1})] + sup, sl), "WorldHUD on 1")
red(wf.judge_supersede(base, sup, []))
red(wf.judge_supersede(base, [st(ui="FieldHUD", field=300)], sl))
# the leave: a field on the way, a missing line, a double count
lv = [st(ui="WorldHUD", out={"starts": 1, "commits": 1, "lands": 1})]
ll = ["[NetSync] world follow-out: start x", "[NetSync] world follow-out: commit y", "[NetSync] world follow-out: landed on world map 9011 z"]
green(wf.judge_leave(base, lv, ll))
red(wf.judge_leave(base, [st(ui="FieldHUD", field=250)] + lv, ll), "ANOTHER FIELD")
red(wf.judge_leave(base, lv, ll[:2]))
red(wf.judge_leave(base, [st(ui="WorldHUD", out={"starts": 2, "commits": 1, "lands": 1})], ll))
# THE PRE-INIT SAMPLE: blocks out, or a world that does not tick, is never judged
green(wf.judge_block([st(ticks=5, frame=1), st(ticks=6, frame=2)]))
red(wf.judge_block([st(block=False, ticks=5), st(block=False, ticks=6)]))
red(wf.judge_block([st(ticks=5, frame=1), st(ticks=5, frame=2)]))
assert wf.first_judged([st(block=False, ticks=1), st(ticks=2, frame=2), st(ticks=3, frame=3)]).frame == 2
# the pose: WORLD11's default, the landing (and the TORUS trap: the tile is 538 u from it the short way), the frame word
p = st(out={"last": {"frame": "latest"}})
green(wf.judge_pose(p, TILE))
red(wf.judge_pose(st(x=1145.7, z=-825.5, out={"last": {"frame": "latest"}}), (1150.0, -820.0)), "default")
red(wf.judge_pose(st(x=68.0, z=-444.0, out={"last": {"frame": "latest"}}), LAND), "plain")
red(wf.judge_pose(st(out={"last": {"frame": "seed"}}), TILE))
red(wf.judge_pose(None, TILE), "not judged")
assert 500 < BW.world_torus_distance(TILE, LAND) < wf.FAR_U <= wf.plain(TILE, LAND)
# the entrance, the foot, the substitution
green(wf.judge_entrance(base, st(out={"entrance_fix": 1})))
red(wf.judge_entrance(base, st(out={"entrance_fix": 1}, entrance=0)))
red(wf.judge_entrance(base, st(out={"entrance_fix": 0})))
green(wf.judge_foot(st()))
red(wf.judge_foot(st(vehicle=1)))
red(wf.judge_foot(st(ctl=2)))
green(wf.judge_onfoot(base, st(out={"substituted": 1}), TILE))
red(wf.judge_onfoot(base, st(out={"substituted": 0}), TILE))
red(wf.judge_onfoot(base, st(x=500.0, z=-500.0, out={"substituted": 1}), TILE))
red(wf.judge_onfoot(base, st(out={"substituted": 1}, vehicle=1), TILE))
# the frozen walker: a walk, the freeze off, an edge count off
fb = st(ui="FieldHUD", freeze={"edges": 3})
green(wf.judge_frozen_here(fb, st(freeze={"on": True, "edges": 4}), 0.4, 40))
red(wf.judge_frozen_here(fb, st(freeze={"on": True, "edges": 4}), 9.0, 40))
red(wf.judge_frozen_here(fb, st(freeze={"on": False, "edges": 4}), 0.4, 40))
red(wf.judge_frozen_here(fb, st(freeze={"on": True, "edges": 5}), 0.4, 40))
# the dot
green(wf.judge_hud(st(dot={"hud": "HUD", "minimap": True})))
red(wf.judge_hud(st(dot={"hud": "HUDNoMiniMap", "minimap": False})))
me = {"shown": True, "why_not": None, "edge": False, "census": {"sprite": "x"}, "px": 158.6, "py": 120.9, "own_px": 158.6, "own_py": 121.4}
green(wf.judge_dot_self(me))
red(wf.judge_dot_self(dict(me, px=160.0)))
red(wf.judge_dot_self(dict(me, census=None)))
red(wf.judge_dot_self(dict(me, shown=False)))
mk = {"sx": 0.6198, "sy": 0.5644, "host_x": 1197.3, "host_z": -799.6, "want": True, "px": 158.67}
green(wf.judge_dot_mark(mk))
red(wf.judge_dot_mark(dict(mk, sx=0.64)))
red(wf.judge_dot_mark(dict(mk, want=False)))
w = wf.edge_width(mk)
assert abs(w - 256.0) < 0.1
eg = {"shown": True, "edge": True, "sx": -0.648, "px": 256.0}
green(wf.judge_dot_edge(eg, w))
red(wf.judge_dot_edge(dict(eg, px=0.0), w), "right edge")      # pinned LEFT: the raw map's side, never the seam's
red(wf.judge_dot_edge(dict(eg, edge=False), w))
red(wf.judge_dot_edge(dict(eg, sx=1.076), w))                   # the raw sx itself must read the host far left
red(wf.judge_dot_edge(eg, None), "not judged")
green(wf.judge_dot_hidden({"why_not": "stale", "shown": False}, "stale"))
red(wf.judge_dot_hidden({"why_not": "stale", "shown": True}, "stale"))
red(wf.judge_dot_hidden({"why_not": "b6", "shown": False}, "no_b6"))   # the kit's old token: the engine's is no_b6
green(wf.judge_dot_lever({"shown": False, "why_not": "lever", "want": True}, {"shown": True}))
red(wf.judge_dot_lever({"shown": False, "why_not": "lever", "want": False}, {"shown": True}))   # the lever hides a WANTED dot
red(wf.judge_dot_lever({"shown": True, "why_not": None, "want": True}, {"shown": True}))
red(wf.judge_dot_lever({"shown": False, "why_not": "lever", "want": True}, {"shown": False}))
green(wf.judge_dot_lever({"shown": False, "why_not": "lever", "want": True}, None))
# tracking: the host's own pose, its map point
green(wf.judge_dot_track({"shown": True, "host_x": 1197.0, "host_z": -797.0, "sx": 0.6198, "sy": 0.5682}, [TILE], 0))
red(wf.judge_dot_track({"shown": True, "host_x": 68.0, "host_z": -444.0}, [TILE], None))
red(wf.judge_dot_track({"shown": False, "host_x": 1197.0, "host_z": -797.0}, [TILE], None))
red(wf.judge_dot_track({"shown": True, "host_x": 1197.0, "host_z": -797.0, "sx": 0.1, "sy": 0.5682}, [TILE], 0))
# R3: the lever words
green(wf.judge_r3(st(), st(r3={"lever": "old"}), st()))
red(wf.judge_r3(st(r3={"lever": "old"}), st(r3={"lever": "old"}), st()))
red(wf.judge_r3(st(), st(), st()))
red(wf.judge_r3(st(r3={"arms_from_9012": 1}), st(r3={"lever": "old"}), st()))
red(wf.judge_r3(st(), st(r3={"lever": "old"}), st(r3={"lever": "old"})))
# R4: a save written, a dry count missing, a missing reason, the HUD never back
f0 = {"SavedData_ww.dat": (1, 10)}
sg0, sg1 = {"refused": 2, "would_save": 0}, {"refused": 3, "would_save": 0, "last_why": "the selftest bench"}
L = ["[NetSync] save refused while following your partner (the selftest bench)"]
green(wf.judge_save(sg0, sg1, L, f0, dict(f0), dry=False, logged=True))
red(wf.judge_save(sg0, sg1, L, f0, {"SavedData_ww.dat": (2, 10)}, dry=False), "CHANGED")
red(wf.judge_save(sg0, sg1, L, None, None, dry=False), "UNREAD")
red(wf.judge_save(sg0, sg1, L, f0, dict(f0), dry=True))
# [ff9mapkit netsync s165] a DRY would-save counts INSTEAD of a refusal (the engine's ManualSaveRefusedNow): refused +0, would_save +1
green(wf.judge_save(sg0, dict(sg1, refused=2, would_save=1), [], f0, dict(f0), dry=True))
red(wf.judge_save(sg0, dict(sg1, would_save=1), [], f0, dict(f0), dry=True))
red(wf.judge_save(sg0, dict(sg1, would_save=1), L, f0, dict(f0), dry=False))
red(wf.judge_save(sg0, dict(sg1, last_why=None), L, f0, dict(f0), dry=False))
red(wf.judge_save(sg0, sg1, [], f0, dict(f0), dry=False, logged=True))
red(wf.judge_save(sg0, sg1, L, f0, dict(f0), dry=False, hud_back=False))
red(wf.judge_save(sg0, sg0, L, f0, dict(f0), dry=False))
# the probe: a key out of order, a missing proof line, a FAIL
from harness import fakegame as FG
probe = st(save={})
nsdoc = dict(probe.raw["netsync"])
nsdoc["world"] = {k: (dict(v) if isinstance(v, dict) else v) for k, v in BW.WORLD_SENTINELS_S165.items()}
nsdoc["swap"], nsdoc["saveguard"], nsdoc["host"] = {}, dict(BW.SAVEGUARD_SENTINELS), {"world": dict(BW.HOST_WORLD_SENTINELS)}
nsdoc = {k: nsdoc[k] for k in ("world", "swap", "saveguard", "host")}
pdoc = dict(probe.raw, netsync=nsdoc, world=dict(probe.raw["world"]))
pdoc["world"].pop("block_ready")
pdoc["world"]["block_ready"] = True
P = State(pdoc)
pl = ["[NetSync] world follow selftest: OK (153 rows, 26 mutants)", "[NetSync] world dot selftest: OK (24 rows, 9 mutants)"]
green(wf.judge_probe(P, pl))
red(wf.judge_probe(P, pl[1:]), "NONE")
red(wf.judge_probe(P, pl + ["[NetSync] world follow selftest: FAIL (row R1-01)"]))
bad = dict(pdoc, netsync={k: nsdoc[k] for k in ("world", "saveguard", "swap", "host")})
red(wf.judge_probe(State(bad), pl))
# [ff9mapkit netsync s166] a v15 (A2) engine: `wire_peer` after `host`, netsync's LAST key -- green; anywhere else -- red
v15 = dict(pdoc, netsync=dict(nsdoc, wire_peer=dict(BW.WIRE_PEER_SENTINELS)))
green(wf.judge_probe(State(v15), pl))
mid = dict(pdoc, netsync={**{k: nsdoc[k] for k in ("world", "swap", "saveguard")}, "wire_peer": {}, "host": nsdoc["host"]})
red(wf.judge_probe(State(mid), pl))
# [ff9mapkit netsync s168] an s168 engine: `guestmenu` after `wire_peer`, netsync's LAST key -- green; before wire_peer, or with the s166
# tail read as if it were s168's (wire_peer last after an s168 key), red: the re-key BY STAGE never weakens the prefix law
v168 = dict(pdoc, netsync=dict(nsdoc, wire_peer=dict(BW.WIRE_PEER_SENTINELS), guestmenu={"lever": {}}))
green(wf.judge_probe(State(v168), pl))
gm_mid = dict(pdoc, netsync=dict(nsdoc, guestmenu={"lever": {}}, wire_peer=dict(BW.WIRE_PEER_SENTINELS)))
red(wf.judge_probe(State(gm_mid), pl))
gm_early = dict(pdoc, netsync={**{k: nsdoc[k] for k in ("world", "swap", "saveguard")}, "guestmenu": {}, "host": nsdoc["host"],
                               "wire_peer": dict(BW.WIRE_PEER_SENTINELS)})
red(wf.judge_probe(State(gm_early), pl))
assert BW.NETSYNC_TOP_KEYS_S168 == ("guestmenu",)
red(wf.judge_probe(State({"frame": 1, "ui_state": "FieldHUD", "netsync": {"world": {"freeze": {}}}}), pl), "absent")   # s164
# the T2 seam bracket on the tape clock
rows = [{"t": t, "b6": True, "pose": {"x": TILE[0], "z": TILE[1]}} for t in (40.0, 40.5, 41.0)]
rows += [{"t": t, "b6": True, "pose": {"x": LAND[0], "z": LAND[1]}} for t in (30.0, 30.5)]
green(wf.judge_tape_pose(st(out={"last": {"frame": "latest"}}), rows, (40.2, 40.8)))
red(wf.judge_tape_pose(st(out={"last": {"frame": "latest"}}), rows, (30.0, 30.4)))      # the seam fell in the landing stand
red(wf.judge_tape_pose(st(x=68.0, z=-444.0, out={"last": {"frame": "latest"}}), rows, (30.0, 30.4)), "plain")
red(wf.judge_tape_pose(st(out={"last": {"frame": "latest"}}), rows, (50.0, 51.0)), "no tape b6 pose")
red(wf.judge_tape_pose(st(out={"last": {"frame": "latest"}}), rows, None), "not judged")
t0 = _dt.datetime(2026, 11, 1, 12, 0, 0)
assert wf.tape_t(t0 + _dt.timedelta(seconds=2), t0, 10.0, speed=1.0) == 12.0
assert wf.tape_t(t0 + _dt.timedelta(seconds=2), t0, 10.0, speed=4.0) == 18.0
# D-FO1's heartbeat witness: stalled then moving before the commit; stalled and never back; no stall sampled
T = lambda s: t0 + _dt.timedelta(seconds=s)
hs = lambda a: st(ui="FieldHUD", host={"b6": True, "hb_age_ms": a})
assert wf.hb_resumed_before([(T(1), hs(30)), (T(2), hs(900)), (T(3), hs(20))], T(4))[0] is True
assert wf.hb_resumed_before([(T(1), hs(30)), (T(2), hs(900)), (T(5), hs(20))], T(4))[0] is False
assert wf.hb_resumed_before([(T(1), hs(30)), (T(2), hs(40))], T(4))[0] is None
# THE SHARED-FILE LAW: an instrument row
green(wf.judge_shared(["[NetSync] fine"], ["fine"]))
red(wf.judge_shared([], ["IOException: Sharing violation on path x.fbx"]), "INSTRUMENT")
red(wf.judge_shared(["When importing FBX, an error"], []))
print("ok")
'''


def test_the_pure_judges_go_red_on_each_wrong_shape():
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _JUDGES, str(SCENARIOS), str(REPO / "tools")],
                         env={k: v for k, v in os.environ.items() if not k.startswith("COOP_")}, capture_output=True, text=True,
                         timeout=120)
    assert out.returncode == 0 and out.stdout.strip().endswith("ok"), out.stderr[-4000:]


# ================================================================================================ [ff9mapkit netsync s167] round B's re-key
def test_s167_the_regression_rekey_keeps_every_leg_s166s():
    """[ff9mapkit netsync s167] THE REGRESSION RE-KEY, ROUND B (S166-DESIGN.md "Regression"; coop_world_wait.walk_off): on the s167
    stand-in (round B's piece "b") every leg here pulls round B's whole s166 lever set -- the solo leg at P1, the T2 walk leg beside
    `worldfollow hold` (WK-I), the duo on BOTH games (D0) -- reads it back, and is green, its frozen rows reading the walk frozen BY THE
    LEVER (FROZEN, WK-FROZEN, D-DOT's "own pose unmoved"). Stood down, exactly those stage keys go red (a guest frozen for another why;
    in game, an s167 pair's guest WALKS: a free walker who presses nothing is unmoved too, and a walk FREE dispatch takes no freeze edge).
    Re-keyed by stage, never weakened."""
    runs = _child({"runs": {"solo": {"kind": "solo", "s167": True, "sections": ["out"]},
                            "solo_off": {"kind": "solo", "s167": True, "sections": ["out"], "walkset": False},
                            "walk": {"kind": "walk", "s167": True},
                            "duo": {"kind": "duo", "s167": True}, "duo_off": {"kind": "duo", "s167": True, "walkset": False}}})
    for name in ("solo", "walk", "duo"):
        assert runs[name]["red"] == [], (name, {c: runs[name]["detail"][c] for c in runs[name]["red"]})
    want = "s167 re-key: round B's s166 lever set (walk off, refuse silent, stallhold old, decline old, fp off, minimap old, fullmap old)"
    s, w, d = runs["solo"]["detail"], runs["walk"]["detail"], runs["duo"]["detail"]
    assert want in s["S165-P1"] and "'walk', 'fp']" in s["S165-P0"] and "why 'lever'" in s["S165-FROZEN"]
    assert want in w["S165-WK-I"] and "why 'lever'" in w["S165-WK-FROZEN"]
    assert f"the guest's {want}" in d["S165-D0"] and f"the host's {want}" in d["S165-D0"] and "why 'lever'" in d["S165-D-DOT"]
    for name, row in (("solo_off", "S165-FROZEN"), ("duo_off", "S165-D-DOT")):
        r = runs[name]
        assert r["red"] == [row] and "STAGE KEY" in r["detail"][row], (name, {c: r["detail"][c] for c in r["red"]})
