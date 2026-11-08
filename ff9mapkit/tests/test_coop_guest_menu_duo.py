"""[ff9mapkit netsync s168] THE GUEST'S MAIN MENU, RUNG 0 -- THE DUO (D) AND T2 (T) ROWS' REPO HALF
(studies/test-harness/scenarios/coop_guest_menu_duo.py, COOP_GMD_LEG / COOP_GMT_LEG; studies/field-coop/S168-DESIGN.md "The bench"),
plus the owner-gated b3 tape's plan (_coop_peer_bench.GM_TAPE_PLAN / gm_tape_facts) and its recorder variant (coop_tape_record.py
COOP_TAPE_GUEST_MENU).

  * THE TABLES: legs, rows, levers, predictions, measures and stand-in fault rows agree with each other and with the docstring; every D / T
    row of the design's table is a row here (or named as unreached); every lever is an ANY-ROLE `guestmenu` op (THE DUO CANNOT PULL A
    SELFTEST-ROLE LEVER).
  * THE STAND-IN DUO: two fakegame stand-ins (the opt-in `guestmenu` rung) under a stub link run every leg the stand-in models -- NEW green
    but STANDIN_UNMODELLED (each red for its pinned reason), OLD on two s167 stand-ins exactly the predicted rows MEASURED with no `guestmenu`
    op sent, each lever exactly its prediction (the unmodelled rows the only unpredicted reds), each fault exactly its FAULT_REDS rows.
  * THE PURE JUDGES go red on each wrong shape -- the in-game-only rows' judges above all (the stand-in cannot run them).
  * THE TAPE: gm_tape_facts green on a synthetic b3 tape and each segment's loss reddening exactly its fact; the T leg's windows; the
    recorder's OWNER GATE (pure, and on the stand-in: nothing edited, no tape).

Every scenario-touching run is a CHILD process (a scenario reads its COOP_* knobs at import and puts its dir on sys.path).
"""
import json
import os
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from harness import battlewire as BW                                   # noqa: E402
from harness import fakegame as FG                                     # noqa: E402

SCENARIOS = REPO / "studies" / "test-harness" / "scenarios"
DESIGN = REPO / "studies" / "field-coop" / "S168-DESIGN.md"
_CLEAR = ("FF9_S166_CLONE", "FF9_S167_CLONE", "FF9_S168_CLONE")

#: the duo rows the stand-in cannot model -> the words its red detail carries (pinned: a row there can never pass for the wrong reason, and a
#: stand-in that learns one shows up here)
STANDIN_UNMODELLED = {
    "GM0-SEAT-D": "host None",                       # no host_fp on the stand-in host (it builds no section 12 of its own)
    # fakegame C3(a): no census on a stand-in key, and no screen shapes (no groups, no list rows) -- the I1 plan stops short at its
    # Item.Item expect until fakegame models the screens
    "GM0-REFUSE-I1-D": "not reached",
    "GM0-LOCAL-D": "not reached",                    # no Item groups on the stand-in (no rail, no arrange dialog): the sort stops short
    "GM0-GHOST": "not reached",                      # no ghost dress on the stand-ins
    "GM0-CAPS-a": "caps lines naming 'guest menu' 0",   # no caps line logged by the stand-in's world walk book for this route
    "GM0-BW": "type5_len -1",                        # no frame book on a stand-in host
    "GM0-LEAVE": "pin age -1",                       # no swap pin on this route
    "GM0-FADE": "pin -1",
    "GM0-PAIRED-LINE-LOST": "'guest_menu' on 0 of",  # no blip-grace hold on the stand-in: its stalled guest takes NotPairedLineRule
    "GM0-RAMP-FIELD-D": "closes.ending +0",          # no grace-expiry ramp from a stub stall
    "GM0-WORLD": "seated None",                      # a client's Menu press on WorldHUD never reaches the stand-in's door
    "GM0-WORLDTAG4-D": "did not seat",
    "GM0-STSCENE": "NOT measured",                   # no own main menu on a stand-in host's WorldHUD
    "GM0-WALKGHOST": "NOT measured",
    "GM0-REJOIN": "did not seat",
    "GM0-RAMP-WORLD-D": "did not seat",
    "GM0-SCENE": "closes.scene +0",                  # the stand-in host's talk sends no scene flag
    "GM0-SCENE-CHEST": "closes.scene +0",
    "GM0-RAMP-CFG-D": "closes.ending +0",            # a stub ini edit closes nothing (no ApplyConfigChange close)
    "GM0-DIALOG-PATH-A": "no host line on the guest",  # no NPC on the stand-in
    "GM0-DIALOG-PATH-B": "no host line on the guest",
    "GM0-HUDSTRIP": "no strip window up",
}
#: rows a launch leaves unrun by configuration (FadeDuration below 300; COOP_GMD_BATTLE=0 on the stand-in duo; the selftest-only quit
#: prompt -- in game too, until an any-role verb exists): red, out of the verdict, named
CONFIG_SKIPPED = {"GM0-KEY-DOUBLE": "not run (configuration)", "GM0-DOOR-D": "not run (configuration)",
                  "GM0-CUT": "COOP_GMD_BATTLE=0", "GM0-SILENT-D": "COOP_GMD_BATTLE=0", "GM0-CUT-QUIT": "COOP_GMD_BATTLE=0",
                  "GM0-QUIT-D": "no any-role quit-prompt verb"}

# ------------------------------------------------------------------------------------------------ the child
_CHILD = r'''
import importlib.util, json, os, pathlib, sys, tempfile, threading, time
scen, tools, kit = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
sys.path.insert(0, kit)
sys.path.insert(0, scen)
doc = json.loads(sys.stdin.read() or "{}")
for k in [k for k in os.environ if k.startswith("COOP_")] + ["FF9_S166_CLONE", "FF9_S167_CLONE", "FF9_S168_CLONE"]:
    os.environ.pop(k, None)
from harness import Session
from harness import fakegame as FG
from harness import battlewire as BW

SENT = []
FAKES = []


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(scen, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def root():
    t = pathlib.Path(tempfile.mkdtemp(prefix="gmd_"))
    (t / "x64").mkdir()
    (t / "x64" / "FF9.exe").write_bytes(b"MZ")
    (t / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    (t / "FF9CustomMap").mkdir()
    (t / "FF9CustomMap" / "DictionaryPatch.txt").write_text(
        "FieldScene 6603 31 FARSHORE FARSHORE 6603\nFieldScene 30801 31 JOURNAL JOURNAL 30801\nFieldScene 30602 31 LOCKT2 LOCKT2 30602\n",
        encoding="utf-8")
    (t / "Memoria.ini").write_text("[Netsync]\nEnabled = 0\n", encoding="utf-8")
    return t


def fake_for(t, run, role):
    f = FG.FakeGame(t, fps=600, walkmesh=(-2000.0, -3000.0, 2000.0, 2000.0))
    refuse = {str(x).lower() for x in run.get("refuse_ops", ())} if role == "guest" else set()
    f.world_walk_pieces = tuple(FG.FAKE_WORLD_WALK_S167_PIECES)
    if run.get("stage", 168) >= 168:
        FG.guest_menu_stand_in(f, faults=tuple(run.get("faults", ())) if role == "guest" else ())
    f.swap_qpc = None
    f.wf_follow_host_cfg = True
    import coop_world_wait as cw
    f.regions = {6603: [{"zone": cw.FS_DOOR, "world": cw.WORLD, "world_at": list(cw.FS_LANDING)}]}
    f.exit_frames = 900
    f.overworld = {"speed": 2.0, "turn": 2.8125, "cam": 0.0, "lag": 1}
    f.world_locations = {cw.ICE_CAVERN: (cw.ICE_TILE[0], cw.ICE_TILE[1], 2.0)}
    f.world_swirl_frames, f.world_exit_frames = 40, 40
    f.world_block_load_frames = 6
    f.world_out_fade_frames = 120
    f.coop_field_follow = role == "guest"          # the field follow-warp (opt-in on the stand-in): the guest follows the host's warps
    real_ns = f._netsync

    def ns(args, _real=real_ns, _role=role, _refuse=refuse):
        if args and str(args[0]).lower() == "guestmenu":
            SENT.append(f"{_role}: " + " ".join(str(a) for a in args))
            if " ".join(str(a) for a in args[1:]).lower() in _refuse:
                raise RuntimeError("guestmenu: refused (the stand-in test's refusal)")
        _real(args)
    f._netsync = ns
    FAKES.append(f)
    return f


def session(t, f):
    g = Session(game_path=t, run_dir=t / "run", save_dir=t / "player-saves", pid_probe=lambda: [],
                launcher=lambda exe, f=f: f.start(), boot_timeout=15.0, verbose=False)
    g._booted_once = True
    return g


class Link(threading.Thread):
    """The duo's stub TRANSPORT: the host's lane field, section-7 flags, story, intent, battle and caps word onto the guest; a stall
    (the stub blackhole) stops it and stales the guest's lane after StaleMs of the guest's clock."""

    def __init__(self, host, guest):
        super().__init__(daemon=True)
        self.h, self.g, self.halt = host, guest, threading.Event()
        self.stall_until = None
        self.stall_at = None
        self.stall_done = None

    def run(self):
        sent = None
        last = None
        while not self.halt.is_set():
            h, g = self.h, self.g
            if self.stall_until is not None:
                if time.time() < self.stall_until:
                    if g.coop_follow is not None and g.rt - self.stall_at >= BW.STALE_MS / 1000.0:
                        g.host_at(valid=False)
                    time.sleep(0.002)
                    continue
                self.stall_until = None
                if self.stall_done is not None:          # the link is back from HERE: `done` before the first live host_at, never after
                    self.stall_done.set()
                    self.stall_done = None
            if g.coop_follow is None:
                time.sleep(0.002)
                continue
            battle = bool(h.battle_active) or h.ui_state in ("BattleHUD", "BattleResult")
            g.host_at(h.host_lane_field(), flags=h.host_dialog_flags(), story=bytes(h.story_bytes), valid=True, battle=battle)
            if h._gm_on():
                g.gm_host_caps = h._gm_own_caps()
            it = h.host_field_intent
            if it is not None and it != sent:
                sent = it
                g.host_intent(it[1])
            lane = h.host_lane_field()
            if last is not None and lane != last and 0 < lane < 65535:
                g.host_intent(lane)                  # EmitFieldIntentIfHost: a host field change announces its destination (section 4)
            last = lane if lane > 0 else last
            w = h.world
            if h.ui_state == "WorldHUD" and w.get("x") is not None and w.get("id"):
                g.host_world_pose(float(w["x"]), float(w["z"]), idx=int(w["id"]) - 9000, mode=int(w.get("vehicle") or 0))
            time.sleep(0.002)


class StubDuo:
    def __init__(self, host, guest, link):
        self.host, self.guest, self.strict, self.rows, self.notes, self.link = host, guest, True, [], [], link

    def check(self, ok, what, detail="", *, role=None, cid=None):
        self.rows.append((cid, bool(ok), str(detail)[:1500]))
        return bool(ok)

    def note(self, msg):
        self.notes.append(msg)

    def blackhole(self, seconds):
        done = threading.Event()
        self.link.stall_done = done
        self.link.stall_at = self.link.g.rt
        self.link.stall_until = time.time() + seconds
        threading.Timer(seconds + 1.0, done.set).start()   # a backstop only: the Link sets done as it resumes

        class H:
            pass
        h = H()
        h.done = done
        return h

    def set_netsync(self, role, updates, **_kw):
        f = FAKES[0] if role == "host" else FAKES[1]
        vals = {"Enabled": "1", "Role": "client" if role == "guest" else "host", "FollowHost": "1"}
        vals.update(updates)
        f.apply_ini(vals)
        return []


def duo(run):
    os.environ["COOP_GMD_LEG"] = run.get("leg", "key")
    os.environ["COOP_GMD_BATTLE"] = "0"
    if run.get("lever"):
        os.environ["COOP_GMD_LEVER"] = run["lever"]
    else:
        os.environ.pop("COOP_GMD_LEVER", None)
    m = load("coop_guest_menu_duo")
    gm, cb = m.gm, m.cb
    for k, v in dict(OPEN_S=4.0, CLOSE_S=5.0, SEL_S=0.6, STEP_S=0.6, HOLD_S=0.3, SAVE_S=0.5).items():
        setattr(gm, k, v)
    # the bench's waits, shortened for a stand-in whose virtual clock runs ahead of the wall (every JUDGED threshold stays the bench's;
    # a wait that never succeeds on the stand-in -- the ramp, the grace -- ends sooner)
    for k, v in dict(OPEN_S=4.0, CLOSE_S=5.0, HOLD_S=0.6, FOLLOW_S=15.0, SHOT_S=1.0, LINE_S=2.0, CLOSE_OLD_CANCEL_S=0.5,
                     TITLE_HOLD_S=0.6, RAMP_S=6.0, PAST_GRACE_S=4.0, WORLD_S=30.0).items():
        setattr(m, k, v)
    cb.CALIBRATE = bool(run.get("cal"))
    th, tg = root(), root()
    FAKES.clear()
    fh, fgst = fake_for(th, run, "host"), fake_for(tg, run, "guest")
    gh, gg = session(th, fh), session(tg, fgst)
    if run.get("guest_no_menu"):                       # the guest's Menu press never lands (an OLD launch that measured nothing)
        real_press = gg.press
        gg.press = lambda key, *a, _r=real_press, **k: None if str(key).lower() == "menu" else _r(key, *a, **k)
    field = m.PAIR.get("field", 250)
    with gh, gg:
        for g in (gh, gg):
            g.newgame(settle=0)
            g.warp(field)
        fh.netsync.update(enabled=True, role="host", instance=True)
        fgst.follow_session(field, flags=BW.HF_ON_FIELD | BW.HF_CONTROL, fresh=True, story=bytes(fh.story_bytes), pair_kick=True)
        fgst.wf_follow_host_cfg = True
        link = Link(fh, fgst)
        link.start()
        gg.wait_for(lambda s: (s.netsync or {}).get("session", {}).get("mirroring") is True, timeout=5, what="paired")
        d = StubDuo(gh, gg, link)
        try:
            m.run_duo(d)
        finally:
            link.halt.set()
        return {"red": sorted(c for c, ok, _d in d.rows if not ok), "all": [c for c, _ok, _d in d.rows],
                "detail": {c: dd for c, _ok, dd in d.rows}, "notes": list(d.notes), "sent": list(SENT)}


def rows_of(checks):
    rows = [(r["what"].split(":")[0], bool(r["ok"]), r["detail"][:1600]) for r in checks]
    return {"red": sorted(c for c, ok, _d in rows if not ok), "all": [c for c, _ok, _d in rows],
            "detail": {c: d for c, _ok, d in rows}}


def rec(run):
    """coop_tape_record.py's GUEST-MENU variant WITHOUT the owner's go, on a stand-in s168 host: THE OWNER GATE (the bench port check
    stubbed: no socket is bound)."""
    os.environ["COOP_TAPE_GUEST_MENU"] = "1"
    os.environ["COOP_TAPE_DIR"] = run["tape_dir"]
    import _coop_peer_bench as pbm
    pbm.port_free = lambda port, host="127.0.0.1": (True, "")
    r = load("coop_tape_record")
    t = root()
    ini0 = (t / "Memoria.ini").read_bytes()
    FAKES.clear()
    f = fake_for(t, {"stage": 168}, "host")
    g = session(t, f)
    with g:
        r.run(g)
        out = rows_of(list(g.checks))
    out["ini_same"] = (t / "Memoria.ini").read_bytes() == ini0
    out["sent"] = list(SENT)
    return out


def t_leg(run):
    """A T leg (COOP_GMT_LEG) on a stand-in guest, no peer: the `tape` leg's OWNER GATE (no b3 tape: every row unrun, the gate red)."""
    os.environ["COOP_GMT_LEG"] = run["leg"]
    os.environ["COOP_TAPE_DIR"] = run["tape_dir"]
    os.environ.pop("COOP_TAPE_GUEST_MENU", None)
    m = load("coop_guest_menu_duo")
    m.cb.CALIBRATE = bool(run.get("cal"))
    t = root()
    ini0 = (t / "Memoria.ini").read_bytes()
    FAKES.clear()
    f = fake_for(t, {"stage": 168}, "guest")
    g = session(t, f)
    with g:
        m.run(g)
        out = rows_of(list(g.checks))
    out["ini_same"] = (t / "Memoria.ini").read_bytes() == ini0
    out["sent"] = list(SENT)
    return out


kinds = {"duo": duo, "rec": rec, "t": t_leg}
results = {}
for name, run in doc.get("runs", {}).items():
    SENT.clear()
    t0 = time.time()
    results[name] = kinds[run.get("kind", "duo")](run)
    results[name]["wall_s"] = round(time.time() - t0, 1)
print("@@" + json.dumps(results))
'''


def _load(name: str, as_name: str):
    import importlib.util
    sys.path.insert(0, str(SCENARIOS))
    spec = importlib.util.spec_from_file_location(as_name, str(SCENARIOS / f"{name}.py"))
    m = importlib.util.module_from_spec(spec)
    old = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("COOP_")}
    try:
        spec.loader.exec_module(m)
    finally:
        os.environ.update(old)
    return m


@pytest.fixture(scope="module")
def md():
    return _load("coop_guest_menu_duo", "coop_guest_menu_duo_pure")


@pytest.fixture(scope="module")
def pbm():
    return _load("_coop_peer_bench", "_coop_peer_bench_gmd")


# ================================================================================================ the tables
def test_the_tables_agree_with_each_other_and_the_docstring(md):
    legs = set(md.DUO_LEGS) | set(md.T_LEGS)
    assert set(md.DUO_ROWS) == set(md.DUO_LEGS) and set(md.T_ROWS) == set(md.T_LEGS) and set(md.LEG_LEVERS) == legs
    duo_rows = [r for leg in md.DUO_LEGS for r in md.DUO_ROWS[leg]]
    t_rows = [r for leg in md.T_LEGS for r in md.T_ROWS[leg]]
    assert len(duo_rows) == len(set(duo_rows)) and len(t_rows) == len(set(t_rows)) and not set(duo_rows) & set(t_rows)
    assert set(md.DUO_CHECKS) == set(duo_rows) | {"GMD-D0"} and set(md.T_CHECKS) == set(t_rows)
    doc = md.__doc__
    for leg in legs:
        assert re.search(rf"\b{leg}\b", doc), leg
    for row in duo_rows + t_rows:
        assert row in doc, row
    for (leg, lever), rows in md.LEVER_PREDICTED.items():
        assert lever in md.LEG_LEVERS[leg] and rows and set(rows) <= set(md.leg_rows(leg)), (leg, lever)
        assert not set(rows) & md.SAME_ON_OLD, (leg, lever)                  # a row s167 reads the same can never be a lever's
    for leg, levers in md.LEG_LEVERS.items():
        for lever in levers:
            assert (leg, lever) in md.LEVER_PREDICTED and lever in md.MEASURE and lever in md.LEVER_ROLE, (leg, lever)
    # THE DUO CANNOT PULL A SELFTEST-ROLE LEVER: every lever op is an ANY-ROLE `guestmenu` op, its read-back a real lever field and word
    for lever, ops in md.LEVER_OPS.items():
        assert ops[0] in BW.GUESTMENU_ANY_ROLE_OPS, lever
        field, word = md.LEVER_READ[lever]
        assert field in BW.GUEST_MENU_LEVER_DEFAULTS and word in BW.GUEST_MENU_LEVER_WORDS[field], lever
    for leg, table in md.FAULT_REDS.items():
        for fault, rows in table.items():
            assert fault in FG.GUEST_MENU_FAULTS and rows and set(rows) <= set(md.leg_rows(leg)), (leg, fault)
    assert md.old_predicted("dialog") == () and md.old_predicted("hudstrip") == ()
    assert "GM0-STSCENE" not in md.old_predicted("world") and "GM0-WORLD" in md.old_predicted("world")
    assert md.lever_of("key", None) == "old" and md.lever_of("key", "capture") == "capture" and md.lever_of("key", "closeold") is None
    assert md.lever_of("dialog", None) is None and md.lever_of("older166", "old") is None


def _design_rows() -> dict:
    """The design's s168 table: row id -> its harness column."""
    out = {}
    for ln in DESIGN.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| (GM0-[A-Za-z0-9-]+) \| ([^|]+) \|", ln)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def test_every_d_and_t_row_of_the_design_is_a_row_here_or_named(md):
    rows = _design_rows()
    assert len(rows) >= 50 and {"GM0-WHY-x", "GM0-REFUSE-x", "GM0-CAPS-a", "GM0-CAPS-b", "GM0-CAPS-c"} <= set(rows)
    mine = set(md.DUO_CHECKS) | set(md.T_CHECKS)
    doc = md.__doc__
    for row, harness in rows.items():
        if not re.search(r"\b[DT]\b", harness):
            continue
        covered = any(r == row or r.startswith(row + "-") for r in mine) or row in doc
        assert covered, (row, harness)


# ================================================================================================ the pure judges
class St:
    """A state: field / ui / the netsync blocks the judges read."""

    def __init__(self, field=250, ui="FieldHUD", *, mirroring=True, gm=None, raw=None):
        self.field_id, self.ui_state = field, ui
        ns = {"session": {"mirroring": mirroring}}
        if gm is not None:
            ns["world"] = {"walk": {}}                  # an s167+ world block (ww_own_caps_want keys the caps word on it)
            ns["guestmenu"] = gm
        self.raw = {"netsync": ns, **(raw or {})}
        self.netsync = ns


def _gmk(**over) -> dict:
    g = json.loads(json.dumps(BW.GUEST_MENU_SENTINELS))
    g["lever"] = dict(BW.GUEST_MENU_LEVER_DEFAULTS)
    g["caps"] = {"own": BW.CAPS_S168, "peer": BW.CAPS_S168, "on": True}
    g["event_enable"] = True
    g.update(over)
    return g


def _s(ui="FieldHUD", *, mr=None, dialog=False, control=True, **gm_over) -> dict:
    return {"frame": 1, "ui": ui, "field": 250, "control": control, "dialog": dialog, "gm": _gmk(**gm_over), "mr": dict(mr or {}),
            "world": None, "label": None, "booted": False, "fading": False, "save": None}


def _seated(**over):
    comps = {c: {"before": f"0x{i:016X}", "after": None} for i, c in enumerate(BW.GM_FP_COMP_NAMES)}
    seat = {c: f"0x{i + 100:016X}" for i, c in enumerate(BW.GM_FP_COMP_NAMES)}
    base = dict(seated=True, opens=1, seat={"src": "wire", "frame_age_ms": -1, "marker": -1},
                fp={"before": "0x1", "after": None, "equal": False, "named": None, "components": comps, "outside_equal": False,
                    "outside_named": None}, seat_fp={"value": "0x2", "components": seat})
    base.update(over)
    return _s("MainMenu", mr={"count": 3, "now": "guest"}, **base)


def test_every_duo_legs_host_setup_lands_on_the_legs_own_field_not_the_new_game_field(md):
    """duo.py runs a pair's host_setup RIGHT AFTER the host's New Game, while the game stands on field 70 (the New-Game override: no
    player control). The seeder used to warp back to ``g.state.field_id or HOME`` -- 70 -- and the OLD run of 2026-11-07 lost nine duo
    legs at setup (60 s waiting for control on 70). Pin: from a game standing on 70, every leg's host_setup warps LAST to its pair's
    own field, through COOPPARTY when registered, and never to 70."""
    class _State:
        field_id = 70

    class _Game:
        def __init__(self, regs):
            self.state, self.warps, self.regs = _State(), [], regs

        def registered_fields(self):
            return (self.regs,)

        def warp(self, field, *a, **k):
            self.warps.append(int(field))
            self.state.field_id = int(field)

        def wait_frames(self, n):
            pass

    seeded = 0
    for leg in md.DUO_LEGS:
        pair = md._pair_of(leg)
        setup = pair.get("host_setup")
        if setup is None or leg == "chest":                 # hudstrip seeds nothing; chest runs the chest relay duo's own recipe
            continue
        for regs in ([md.cb.PARTY_FIELD, pair["field"]], [pair["field"]]):
            g = _Game(regs)
            note = setup(g)
            if md.cb.PARTY_FIELD in regs:                   # seeded: through COOPPARTY, then on to the leg's own field
                assert g.warps and g.warps[-1] == pair["field"], (leg, regs, g.warps, note)
            else:                                           # not registered: no warp here, duo.py's own warp takes it to the field
                assert g.warps == [], (leg, g.warps, note)
            assert 70 not in g.warps, (leg, g.warps)
            assert (md.cb.PARTY_FIELD in g.warps) == (md.cb.PARTY_FIELD in regs), (leg, regs, g.warps)
        seeded += 1
    assert seeded >= 10, seeded


def test_the_key_seat_ghost_and_double_judges(md):
    pre = _s(mr={"count": 3, "now": "guest"})
    s = _seated()
    assert md.judge_key(pre, s)[0]
    assert not md.judge_key(_s(mr={"count": 3, "now": "audible"}), s)[0]                       # the HUD read s121's
    assert not md.judge_key(pre, _seated(seat={"src": "bench", "frame_age_ms": 12, "marker": 7}))[0]   # a bench seat
    assert not md.judge_key(pre, _seated(opens=2))[0]
    assert not md.judge_key(pre, dict(_seated(), mr={"count": 4}))[0]                           # a refusal counted
    assert not md.judge_key(pre, _s("FieldHUD", mr={"count": 4}, opens=0))[0]
    # OLD's shape: s121's audible refusal
    assert md.key_old_measured(_s(mr={"count": 3, "now": "audible"}), _s(mr={"count": 4}))
    assert not md.key_old_measured(_s(mr={"count": 3, "now": "guest"}), _s(mr={"count": 4}))
    assert not md.key_old_measured(_s(mr={"count": 3, "now": "audible"}), _seated())
    host = {c: f"0x{i + 100:016X}" for i, c in enumerate(BW.GM_FP_COMP_NAMES)}
    assert md.judge_seat_d(_seated(), host)[0]
    assert not md.judge_seat_d(_seated(), dict(host, bag="0xBAD"))[0]                           # a wire component differs
    assert md.judge_seat_d(_seated(), dict(host, keyitems="0xBAD"))[0]                          # keyitems REPORTED only (K1)
    assert not md.judge_seat_d(_seated(), {})[0]                                                # no host_fp: never vacuous
    same = {c: {"before": host[c], "after": None} for c in BW.GM_FP_COMP_NAMES}
    assert not md.judge_seat_d(_seated(fp={"components": same}), host)[0]                       # the guest's own drawn: no second marker
    gh = ((98, 3), (98, 3))
    assert md.judge_ghost(gh, [gh, gh])[0]
    assert not md.judge_ghost(gh, [gh, ((98, 3), (12, 7))])[0]                                  # the rig flips (LiveSlotChars)
    assert not md.judge_ghost(((-1, -1), (98, 3)), [((-1, -1), (98, 3))])[0]                    # no ghost: not reached, never a pass
    assert not md.judge_ghost(gh, [])[0]
    assert md.judge_key_double(pre, _seated(), [])[0]
    assert not md.judge_key_double(pre, dict(_seated(), mr={"count": 4}), [])[0]               # the second press refused `ui`
    assert not md.judge_key_double(pre, _seated(line={"text": "FF9 co-op: x", "age": 5}), [])[0]
    assert not md.judge_key_double(pre, _seated(opens=3), [])[0]


def test_the_pair_and_local_judges(md):
    gmk = _gmk()
    h, g = St(gm=gmk), St(gm=gmk)
    assert md.judge_d0(h, g, 250)[0]
    assert not md.judge_d0(h, St(mirroring=False, gm=gmk), 250)[0]                             # the guest never mirrored
    assert not md.judge_d0(h, St(field=30602, gm=gmk), 250)[0]                                 # off the pairing field
    assert not md.judge_d0(St(), g, 250)[0]                                                     # mixed stages (an s167 host)
    ok, why = md.judge_d0(St(), St(), 250)
    assert ok and "OLD (no guestmenu key)" in why                                               # both s167: OLD, the pair stands
    bad = json.loads(json.dumps(gmk))
    bad["lever"]["menu"] = "old"
    assert not md.judge_d0(h, St(gm=bad), 250)[0]                                               # a lever off its default
    a, b = _s(refused={"count": 1}, captures=1, seated=True), _s(refused={"count": 1}, captures=1, seated=True)
    closed = _s(fp={"equal": True})
    # DESIGN D5: the GUEST's measured manual swap (coop_guest_menu._manual_swap's record: l0 / l2 read, the cursor's row after it reads l0)
    swap = {"manual_label": "Manual", "l0": "Potion", "l2": "Phoenix Down", "swapped": "Potion", "swap_why": "", "row0": "Item 0",
            "row2": "Item 2", "swapped_row": "Item 2"}
    rec = {"reached": True, "what": "sort", "before": a, "after": b, **swap}
    ok, why = md.judge_local_d(rec, "0x1", "0x1", closed)
    assert ok and "'Potion' <-> 'Phoenix Down'" in why and "measured True" in why, why
    assert md.swap_measured_d(rec) and not md.swap_measured_d({})
    assert not md.judge_local_d(rec, "0x1", "0x2", closed)[0]                                   # a sort forwarded to the host
    assert not md.judge_local_d(dict(rec, after=_s(refused={"count": 2}, captures=1, seated=True)), "0x1", "0x1", closed)[0]
    assert not md.judge_local_d(rec, "0x1", "0x1", _s(fp={"equal": False}))[0]
    assert not md.judge_local_d({"reached": False, "why": "no row"}, "0x1", "0x1", closed)[0]
    assert not md.judge_local_d(rec, None, None, closed)[0]                                     # no host_fp: never vacuous
    # no measured swap: red even with the host's bag unchanged and nothing refused (an Auto on a sorted bag changes nothing)
    bare = {"reached": True, "what": "sort", "before": a, "after": b}
    ok, why = md.judge_local_d(bare, "0x1", "0x1", closed)
    assert not ok and "measured False" in why, why
    assert not md.judge_local_d(dict(rec, swapped="Phoenix Down"), "0x1", "0x1", closed)[0]     # the cursor's row is not l0: no swap
    assert not md.judge_local_d(dict(rec, l2="Potion"), "0x1", "0x1", closed)[0]                # one label read twice: nothing to swap
    assert not md.judge_local_d(dict(rec, l0=None, swapped=None), "0x1", "0x1", closed)[0]
    ok, why = md.judge_local_d({"reached": False, "why": "no Item.SubMenu (the rail)", "trail": [("Item.Item", "Potion")]}, "0x1", "0x1",
                               closed)
    assert not ok and why.startswith("not reached: no Item.SubMenu") and "Item.Item" in why, why


def test_the_caps_line_bw_and_world_judges(md):
    own, peer = BW.CAPS_S168, BW.CAPS_S167
    caps_line = "[NetSync] guest " + BW.ww_caps_line_text(own, peer)
    pre = _s(mr={"count": 2, "lines": 1, "now": "audible"})
    s = _s(mr={"count": 3, "lines": 2}, why="older", line={"text": BW.gm_refusal_line_rule("older"), "age": 10})
    on = _seated()
    assert md.judge_caps_a(pre, s, [caps_line], on, own, peer)[0]
    assert not md.judge_caps_a(pre, s, [], on, own, peer)[0]                                    # no caps line
    assert not md.judge_caps_a(pre, s, [caps_line, caps_line], on, own, peer)[0]                # twice
    assert not md.judge_caps_a(pre, dict(s, mr={"count": 3, "lines": 1}), [caps_line], on, own, peer)[0]
    assert not md.judge_caps_a(pre, s, [caps_line], _s(), own, peer)[0]                         # `caps on` never opened
    assert not md.judge_caps_a(pre, _seated(), [caps_line], on, own, peer)[0]                   # caps_ignored: it opened
    g = BW.OVERLAY_NAME_GUEST_MENU
    ln = lambda age: {"text": BW.gm_refusal_line_rule("older"), "age": age}                    # noqa: E731 - the line live at ``age``
    off = {"text": None, "age": -1}
    lived = [("following", off), ("following", ln(10))] + [(g, ln(200 * i)) for i in range(1, 17)] + [("following", off)]
    assert md.judge_paired_line("following", lived, "following")[0]
    assert not md.judge_paired_line("following", [(o if o != g else "following", x) for o, x in lived], "following")[0]  # unchanged branch
    assert not md.judge_paired_line("following", lived, g)[0]                                   # never back
    assert not md.judge_paired_line("following", lived, None)[0]                                # back to another line
    flicker = [(g if i in (1, 2) else "off", ln(250 * i)) for i in range(16)]                   # 2 of 16: falls back to OvlOff early
    assert not md.judge_paired_line("following", flicker, "following")[0]
    one_off = [(g, ln(200 * i)) for i in range(1, 10)]
    one_off[5] = ("off", one_off[5][1])                                                         # a line-live sample on 'off'
    assert not md.judge_paired_line("following", one_off, "following")[0]
    assert not md.judge_paired_line("following", [(g, ln(10)), (g, ln(200)), (g, ln(400))], "following")[0]   # 2 judged: under 3
    assert md.judge_paired_line("following", [(g, ln(10)), (g, ln(200)), (g, ln(400)), (g, ln(600))], "following")[0]
    assert not md.line_live(off) and not md.line_live({"text": "x", "age": BW.GM_GUEST_LINE_MS}) and md.line_live(ln(0))
    assert md.judge_bw({"sec12_len": 40, "type5_len": 2400}, {"sec12_len": -1, "type5_len": 2357}, 900, 800)[0]
    assert not md.judge_bw({"sec12_len": 40, "type5_len": 2400}, {"sec12_len": 40, "type5_len": 2400}, 900, 900)[0]
    assert not md.judge_bw({"sec12_len": 40, "type5_len": 2400}, {"sec12_len": -1, "type5_len": 2390}, 900, 800)[0]
    assert not md.judge_bw({"sec12_len": -1, "type5_len": 2400}, {"sec12_len": -1, "type5_len": 2300}, 0, 0)[0]
    seat, closed = _seated(), _s(fp={"before": "0x1", "after": "0x1", "equal": True, "named": None, "outside_equal": True},
                                  restore={"doors": 1, "drops": 0, "backstops": {}}, seated=False)
    seat = dict(seat, gm=dict(seat["gm"], restore={"doors": 0, "drops": 0, "backstops": {}}))
    ride_pre = _s("WorldHUD", mr={"count": 1})
    ride = _s("WorldHUD", mr={"count": 2}, why="riding")
    assert md.judge_world((seat, closed), (seat, closed), (ride_pre, ride))[0]
    assert not md.judge_world((seat, closed), (None, None), (ride_pre, ride))[0]                 # frozen never seated
    ok, why = md.judge_world((seat, closed), (seat, closed), (ride_pre, ride), frozen_why="walk.lever 'on'")
    assert not ok and "frozen: not reached (walk.lever 'on')" in why                            # a second WALKING cycle is no frozen one
    assert not md.judge_world((seat, closed), (seat, closed), (ride_pre, _s("WorldHUD", mr={"count": 2}, why="world_busy")))[0]
    assert not md.judge_world((seat, closed), (seat, closed), (None, None))[0]
    assert md.judge_measuring([1, 2, 3], "x")[0] and not md.judge_measuring([1], "x")[0]


def _closed(cause, *, frm="Equip", end="done", equal=True, n=1, **over):
    closes = dict.fromkeys(BW.GM_CLOSE_IDS, 0)
    closes[cause] = n
    closes["faults"] = 0
    return _s(closes=closes, last_close={"cause": cause, "from": frm, "ms": 120, "end": end}, seated=False,
              fp={"before": "0x1", "after": "0x1" if equal else "0x2", "equal": equal, "named": None if equal else "party"}, **over)


def _base(ui="Equip"):
    closes = dict.fromkeys(BW.GM_CLOSE_IDS, 0)
    closes["faults"] = 0
    return _s(ui, closes=closes, seated=True, restore={"doors": 0, "drops": 0, "backstops": {"ramp": 0, "ramp_quit": 0}})


#: TONIGHT'S REAL GUEST LINES (the NEW run, .harness-runs/20261108-*-duo-coop_guest_menu_duo/guest/Memoria.log), verbatim: the close-ends
#: verdicts' fixtures -- each judge passes on the engine's own order and goes red on each wrong shape cut from it
_T = "08.11.2026 00:02:00 |M| [NetSync] "
OUT_LINES = [                                                                  # 000054 (GM0-OUT), :71-:77
    _T + "client lane hang over: the partner's game is updating again after 1854 ms (t 150626627 ms)",
    _T + "world follow-out: waits: the field HUD is not up -- field 6603, the host on world map 9011 (t 150626628 ms)",
    _T + "guest menu: restored at the door (MainMenu -> FieldHUD) -- every family back by reference; the session ends",
    _T + "world follow-out: waits: the host has not been live on the world map for 1200 ms yet -- field 6603, the host on world map 9011 "
         "(t 150626713 ms)",
    _T + "guest menu: forced close (out) from MainMenu done: the HUD's Show turned events back on after 125 ms (FieldHUD)",
    "08.11.2026 00:02:02 |M| [NetSync] follow fade: to world map 9011 -- fast: the screen reads visible (sub); fading to black in 12 ticks; "
    "the commit waits for black (no later than 0.9 s) (t 150627828 ms)",
    "08.11.2026 00:02:02 |M| [NetSync] world follow-out: start -- field 6603 follows the host out onto world map 9011 (the host on foot at x "
    "68, z -444, entrance 35; live on the world map for 1203 ms) (t 150627828 ms)",
]
_TR = "08.11.2026 00:03:34 |M| [NetSync] "
REJOIN_LINES = [                                                               # 000216 (GM0-REJOIN), :594-:600
    _TR + "world rejoin to field 300 waits: the world HUD is not up",
    _TR + "guest menu: restored at the door (MainMenu -> WorldHUD) -- every family back by reference; the session ends",
    _TR + "guest menu: forced close (rejoin) from MainMenu done: the HUD's Show turned events back on after 172 ms (WorldHUD)",
    _TR + "intent: rejoining the peer at field 300 from world map 9011 (parallel) -- the host's snapshot applies at the load",
    _TR + "world follow-out: waits: a follow, the kick, a world follow-out or the world rejoin is already in flight -- field 6603, the host "
          "on world map 9011 (t 150720467 ms)",
    _TR + "world walk FROZEN (transition) on world map 9011: a world transition is in flight -- travel input held",
    "08.11.2026 00:03:35 |M| [NetSync] world rejoin landed on field 300 after 813 ms",
]
_TC = "08.11.2026 00:04:44 |M| [NetSync] "
CUT_LINES = [                                                                  # 000344 (GM0-CUT), :68-:81
    _TC + "start hold report: host battle nonce 1 -> BUSY -- I am busy (a menu, a shop, a pause): the diorama waits on me, the host does not",
    _TC + "start hold report: host battle nonce 1 -> BOOTING -- my diorama of it is booting or in its intro (the host holds its gauges)",
    _TC + "guest menu: restored at the door (Item -> FieldHUD) -- every family back by reference; the session ends",
    _TC + "diorama BOOT scene=67 pattern=0 start=BTL_START_FIRST_ATTACK intro=play(host) swirl=0 clamp=0",
    _TC + "diorama wire boot stamped nonce=1",
    _TC + "guest menu: forced close (cut) from Item ended at a clear point after 250 ms (a scene load)",
    _TC + "diorama seated the host's party: 4 slot(s)",
    "08.11.2026 00:04:52 |M| [NetSync] diorama LIVE 8421 ms after the boot (host battle nonce 1, booted from wire nonce 1) -- the start-hold "
    "report for this battle now reads LIVE",
]
_TP = "08.11.2026 00:09:45 |M| [NetSync] "
RAMP_CFG_LINES = [                                                             # 000847 (GM0-RAMP-CFG-D), :68-:75
    _TP + "config enabled=False role=client field=0 ghostAs=auto followHost=1 relay=ws://127.0.0.1:49212 code=ff9-DUOFF21U",
    _TP + "config change applied live (disabled)",
    _TP + "guest menu: restored at the door (Item -> FieldHUD) -- every family back by reference; the session ends",
    _TP + "guest menu: forced close (ending) from Item ended at a clear point after 31 ms (the exit ramp's fire)",
    _TP + "session ended -> reloading own autosave (Continue)",
]
_TS = "08.11.2026 00:12:21 |M| [NetSync] "
RAMP_FIELD_LINES = [                                                           # 001103 (GM0-RAMP-FIELD-D), :86-:91
    _TS + "session: the host has been silent for 5016 ms, past the 5 s grace -- the session ended; the exit ramp reloads your own autosave "
          "once you are free-standing; gaveup=1",
    _TS + "guest menu: restored at the door (MainMenu -> FieldHUD) -- every family back by reference; the session ends",
    _TS + "self-dress arm cleared (the exit ramp) -- a dressed body stays dressed until its next SetModel (the teardown law)",
    _TS + "guest menu: forced close (ending) from MainMenu ended at a clear point after 63 ms (the exit ramp's fire)",
    _TS + "session ended -> reloading own autosave (Continue)",
]
_TW = "08.11.2026 00:15:09 |M| [NetSync] "
RAMP_WORLD_LINES = [                                                           # 001319 (GM0-RAMP-WORLD-D), :613-:618
    _TW + "session: the host has been silent for 5016 ms, past the 5 s grace -- the session ended; the exit ramp reloads your own autosave "
          "once you are free-standing; gaveup=1",
    _TW + "guest menu: restored at the door (MainMenu -> WorldHUD) -- every family back by reference; the session ends",
    _TW + "self-dress arm cleared (the exit ramp) -- a dressed body stays dressed until its next SetModel (the teardown law)",
    _TW + "guest menu: forced close (ending) from MainMenu ended at a clear point after 172 ms (the exit ramp's fire)",
    _TW + "session ended -> reloading own autosave (Continue)",
]


def _moved(lines, i: int, j: int) -> list:
    """``lines`` with line ``i`` moved to index ``j`` (of the list without it)."""
    out = list(lines)
    out.insert(j, out.pop(i))
    return out


def test_the_close_judges_go_red_on_each_wrong_shape(md):
    b = _base()
    W = md.close_words_want                                                                      # noqa: N806 - the cause's words
    assert md.judge_leave(b, _closed("leave"), 900, True, "shot.png", words=W("leave"))[0]
    assert md.judge_leave(b, _closed("leave"), md.PIN_MAX_AGE_MS, True, "x", words=W("leave"))[0]   # PinUseRule: aged only OVER 2500
    assert not md.judge_leave(b, _closed("leave"), md.PIN_MAX_AGE_MS + 1, True, "x", words=W("leave"))[0]
    assert not md.judge_leave(b, _closed("leave"), 2600, True, "x", words=W("leave"))[0]         # the pin aged
    assert not md.judge_leave(b, _closed("leave"), 900, False, "x", words=W("leave"))[0]         # never landed
    assert not md.judge_leave(b, _closed("leave", frm="MainMenu"), 900, True, "x", words=W("leave"))[0]   # not from the sub-screen
    assert not md.judge_leave(b, _closed("leave", equal=False), 900, True, "x", words=W("leave"))[0]
    assert not md.judge_leave(b, _closed("leave", end="watchdog"), 900, True, "x", words=W("leave"))[0]
    assert not md.judge_leave(b, _closed("leave", n=0), 900, True, "x", words=W("leave"))[0]     # leave_ignored / close old
    # THE CLOSE WORDS (stamped at the close): another cause's line, or none, is red on every close judge
    assert not md.judge_leave(b, _closed("leave"), 900, True, "x", words=W("title"))[0]
    assert not md.judge_leave(b, _closed("leave"), 900, True, "x")[0]
    for cause in md.BW.GM_CLOSE_IDS:
        ok, why = md.judge_close(cause, b, _closed(cause), words=W(cause))
        assert ok and f"want {W(cause)!r}" in why, (cause, why)
        other = next(c for c in md.BW.GM_CLOSE_IDS if W(c) != W(cause))
        assert not md.judge_close(cause, b, _closed(cause), words=W(other))[0], cause
        assert not md.judge_close(cause, b, _closed(cause), words=None)[0], cause
        # the default `ends` is ('done',): a clear point passes only where a judge opts in (and pins its form itself)
        assert not md.judge_close(cause, b, _closed(cause, end="clear_point"), words=W(cause))[0], cause
        assert md.judge_close(cause, b, _closed(cause, end="clear_point"), words=W(cause), ends=("done", "clear_point"))[0], cause
        assert not md.judge_close(cause, b, _closed(cause, end="watchdog"), words=W(cause), ends=("done", "clear_point"))[0], cause
    assert md.close_old_measured("leave", b, _base()) and not md.close_old_measured("leave", b, _closed("leave"))
    cyc = [("Equip", b, _closed("leave"), 900, True), ("root", b, _closed("leave"), 1100, True)]
    assert md.judge_fade(cyc)[0] and not md.judge_fade(cyc[:1])[0]
    assert not md.judge_fade([cyc[0], ("root", b, _closed("leave"), 2700, True)])[0]
    assert md.judge_fade([cyc[0], ("root", b, _closed("leave"), md.PIN_MAX_AGE_MS, True)])[0]
    # GM0-OUT on tonight's lines: [wait, door, end, start '; live on the world map for 1203 ms)'] (decision 18: the request frame's one
    # wait before the close's end line; the start after the door)
    out = _closed("out", frm="MainMenu")
    wait, door, end, start = 1, 2, 4, 6                                                          # OUT_LINES' indices
    assert md.judge_out(b, out, True, OUT_LINES, words=W("out"))[0], md.judge_out(b, out, True, OUT_LINES, words=W("out"))[1]
    ok, why = md.judge_out(b, out, True, OUT_LINES, words=W("out"))
    assert "waits 1 at [1]" in why and "host-alive ms 1203" in why, why
    assert md.judge_out(b, out, True, [ln for i, ln in enumerate(OUT_LINES) if i != wait], words=W("out"))[0]   # no wait: fine too
    old_twin = "[NetSync] " + BW.LOG_WORLD_OUT_START + " from field 6603 to world map 9011 (host at (68.0, -444.0), 1450 ms host-alive)"
    assert md.judge_out(b, out, True, OUT_LINES[:start] + [old_twin], words=W("out"))[0]          # the kit twin's older tail parses
    assert not md.judge_out(b, out, True, OUT_LINES)[0]                                           # no words at the close
    assert not md.judge_out(b, out, True, OUT_LINES[:end] + [OUT_LINES[wait]] + OUT_LINES[end:], words=W("out"))[0]   # two waits
    assert not md.judge_out(b, out, True, _moved(OUT_LINES, wait, end), words=W("out"))[0]        # a wait after the end line
    assert not md.judge_out(b, out, True, _moved(OUT_LINES, start, door), words=W("out"))[0]      # the start before the door
    assert not md.judge_out(b, out, True, [ln.replace("for 1203 ms", "for 900 ms") for ln in OUT_LINES], words=W("out"))[0]   # 900 ms
    assert not md.judge_out(b, out, True, [ln for i, ln in enumerate(OUT_LINES) if i != door], words=W("out"))[0]   # no door
    assert not md.judge_out(b, out, True, [ln for i, ln in enumerate(OUT_LINES) if i != end], words=W("out"))[0]    # no end line
    assert not md.judge_out(b, out, True, OUT_LINES[:start], words=W("out"))[0]                    # no start line
    assert not md.judge_out(b, out, False, OUT_LINES, words=W("out"))[0]                          # never landed
    # GM0-REJOIN on tonight's lines: [wait, door, end, arm]
    rj = _closed("rejoin", frm="MainMenu")
    rwait, rdoor, rend, rarm = 0, 1, 2, 3
    assert md.judge_rejoin(b, rj, True, REJOIN_LINES, words=W("rejoin"))[0], md.judge_rejoin(b, rj, True, REJOIN_LINES, words=W("rejoin"))
    assert md.judge_rejoin(b, rj, True, REJOIN_LINES[1:], words=W("rejoin"))[0]                    # no wait: fine too
    assert not md.judge_rejoin(b, rj, True, REJOIN_LINES, words=W("cut"))[0]
    assert not md.judge_rejoin(b, rj, True, _moved(REJOIN_LINES, rarm, rdoor), words=W("rejoin"))[0]   # the arm before the door
    assert not md.judge_rejoin(b, rj, True, _moved(REJOIN_LINES, rwait, rend), words=W("rejoin"))[0]   # a wait after the end line
    assert not md.judge_rejoin(b, rj, True, [REJOIN_LINES[rwait]] + REJOIN_LINES, words=W("rejoin"))[0]   # two waits
    assert not md.judge_rejoin(b, rj, True, [ln for i, ln in enumerate(REJOIN_LINES) if i != rdoor], words=W("rejoin"))[0]   # no door
    assert not md.judge_rejoin(b, rj, True, [ln for i, ln in enumerate(REJOIN_LINES) if i != rarm], words=W("rejoin"))[0]    # no arm
    # GM0-CUT: `done` (a world cut) with no lines; a field cut's `clear_point` at the boot's scene load, the door before 'diorama BOOT'
    cdoor, cboot, cend = 2, 3, 5
    assert md.judge_cut(b, _closed("cut"), "booting", 1, True, words=W("cut"))[0]
    assert md.judge_cut(b, _closed("cut"), "booting", 1, True, words=W("cut"), lines=())[0]
    cp = _closed("cut", frm="Item", end="clear_point")
    assert md.judge_cut(b, cp, "booting", 1, True, words=W("cut"), lines=CUT_LINES)[0], md.judge_cut(b, cp, "booting", 1, True,
                                                                                                    words=W("cut"), lines=CUT_LINES)
    assert not md.judge_cut(b, cp, "booting", 1, True, words=W("cut"))[0]                          # a clear point with no lines: unproven
    assert not md.judge_cut(b, cp, "booting", 1, True, words=W("cut"), lines=_moved(CUT_LINES, cboot, cdoor))[0]   # boot before the door
    assert not md.judge_cut(b, cp, "booting", 1, True, words=W("cut"),
                            lines=[ln.replace(" (a scene load)", "") for ln in CUT_LINES])[0]      # no '(a scene load)'
    assert not md.judge_cut(b, cp, "booting", 1, True, words=W("cut"),
                            lines=[ln.replace("(a scene load)", "(the exit ramp's fire)") for ln in CUT_LINES])[0]   # another site
    assert not md.judge_cut(b, cp, "booting", 0, True, words=W("cut"), lines=CUT_LINES)[0]         # never LIVE
    assert not md.judge_cut(b, _closed("cut", end="watchdog"), "booting", 1, True, words=W("cut"), lines=CUT_LINES)[0]
    assert not md.judge_cut(b, cp, "booting", 1, True, words=W("cut"), lines=[ln for i, ln in enumerate(CUT_LINES) if i != cend])[0]
    assert not md.judge_cut(b, _closed("cut"), "booting", 1, True, words=W("scene"))[0]
    assert not md.judge_cut(b, _closed("cut"), "busy", 1, True, words=W("cut"))[0]               # `close old`: BUSY
    assert not md.judge_cut(b, _closed("cut"), "booting", 0, True, words=W("cut"))[0]            # never LIVE
    assert md.judge_silent("silent", "BattleHUD", 0, False, True)[0]
    assert not md.judge_silent("open", "BattleHUD", 0, False, True)[0]                            # a verdict that opens on BattleHUD
    assert not md.judge_silent("silent", "BattleHUD", 0, True, True)[0]                           # bmenu mainmenu accepted
    assert not md.judge_silent("silent", "BattleHUD", 0, False, False)[0]
    waiting = [_s("Item", close_step="quit", seated=True)] * 3
    assert md.judge_cut_quit(waiting, "busy", _closed("cut"), b)[0]
    assert not md.judge_cut_quit(waiting, "booting", _closed("cut"), b)[0]                        # BOOTING while the prompt holds it
    assert not md.judge_cut_quit([_s("Item", close_step="hide", seated=True)], "busy", _closed("cut"), b)[0]
    # on this FIELD the released close ends at the boot's scene load, as GM0-CUT's (cut_end_ok): proven only by the lines
    cq = _closed("cut", frm="Item", end="clear_point")
    assert md.judge_cut_quit(waiting, "busy", cq, b, lines=CUT_LINES)[0], md.judge_cut_quit(waiting, "busy", cq, b, lines=CUT_LINES)
    assert not md.judge_cut_quit(waiting, "busy", cq, b)[0]                                        # a clear point with no lines
    assert not md.judge_cut_quit(waiting, "busy", cq, b, lines=_moved(CUT_LINES, 3, 2))[0]          # the boot before the door
    assert not md.judge_cut_quit(waiting, "busy", _closed("cut", end="watchdog"), b, lines=CUT_LINES)[0]
    assert md.cut_end_ok("done", ()) and md.cut_end_ok("clear_point", CUT_LINES) and not md.cut_end_ok("clear_point", ())
    assert md.judge_title(b, _closed("title"), 40, words=W("title"))[0]
    assert not md.judge_title(b, _closed("title"), 40, words=W("leave"))[0]                      # another cause's words
    assert not md.judge_title(b, _closed("title"), 40)[0]                                         # no words
    late = _closed("title")
    late["gm"]["last_close"]["ms"] = BW.GM_CLOSE_CAP_MS + 200
    assert not md.judge_title(b, late, 40, words=W("title"))[0]
    held_ok = dict(_closed("title", n=0), gm=dict(_closed("title", n=0)["gm"], restore={"doors": 1, "drops": 0, "backstops": {}}))
    assert md.title_old_measured(b, [_base()], held_ok)
    assert not md.title_old_measured(b, [], held_ok)                                              # no held samples
    assert not md.title_old_measured(b, [_base()], _closed("title"))                              # the close happened
    assert not md.title_old_measured(b, [_base(), dict(_base(), gm=dict(_base()["gm"], seated=False))], held_ok)   # a held sample unseated
    assert md.judge_scene(b, _closed("scene"), True, [], words=W("scene"))[0]
    assert not md.judge_scene(b, _closed("scene"), True, [], words=W("title"))[0]
    assert not md.judge_scene(b, _closed("scene"), True, ["[NetSync] talk relay: expired before my copy was free"], words=W("scene"))[0]
    assert not md.judge_scene(b, _closed("scene"), False, [], words=W("scene"))[0]
    assert md.judge_scene(b, _closed("scene"), False, ["[NetSync] chest relay: opening chest 9 on my copy of field 200"], chest=True,
                          words=W("scene"))[0]
    assert not md.judge_scene(b, _closed("scene"), False, [], chest=True, words=W("scene"))[0]


def test_the_ramp_stall_dialog_and_strip_judges(md):
    b = _base("Item")
    we = md.close_words_want("ending")
    # decision 16 on tonight's lines: the ramp block runs ahead of the close tick, so the fire ends the record -- a clear point at the
    # exit ramp's fire -- on the field (RAMP-CFG-D, RAMP-FIELD-D) and the world map (RAMP-WORLD-D) alike
    for lines, frm in ((RAMP_CFG_LINES, "Item"), (RAMP_FIELD_LINES, "MainMenu"), (RAMP_WORLD_LINES, "MainMenu")):
        cp = _closed("ending", frm=frm, end="clear_point")
        ok, why = md.judge_ramp(b, cp, lines, ui_ok=True, words=we)
        assert ok, why
        other = [ln.replace("(the exit ramp's fire)", "(a scene load)") for ln in lines]
        assert not md.judge_ramp(b, cp, other, ui_ok=True, words=we)[0]                           # another site's clear point
        assert not md.judge_ramp(b, cp, [ln for ln in lines if "forced close (ending)" not in ln], ui_ok=True, words=we)[0]
        assert md.judge_ramp(b, _closed("ending", frm=frm), lines, ui_ok=True, words=we)[0]       # `done` passes too (B16)
        assert not md.judge_ramp(b, _closed("ending", frm=frm, end="watchdog"), lines, ui_ok=True, words=we)[0]
    ok_lines = RAMP_CFG_LINES
    s = _closed("ending", frm="Item", end="clear_point")
    assert md.judge_ramp(b, s, ok_lines, ui_ok=True, words=we)[0]
    assert not md.judge_ramp(b, s, ok_lines, ui_ok=True)[0]                                       # the ending line never drawn
    assert not md.judge_ramp(b, s, ok_lines, ui_ok=True, words=md.close_words_want("title"))[0]
    assert not md.judge_ramp(b, s, list(reversed(ok_lines)), ui_ok=True, words=we)[0]            # the ramp before the restore
    assert not md.judge_ramp(b, s, ok_lines + ["[NetSync] guest menu: restored at x ... (should never happen)"], ui_ok=True, words=we)[0]
    assert not md.judge_ramp(b, s, ok_lines, ui_ok=False, words=we)[0]
    assert not md.judge_ramp(b, s, [ln for ln in ok_lines if md.BW.LOG_GM_RESTORED not in ln], ui_ok=True, words=we)[0]   # no restore
    # `close old` on the ramp: measured only past the 2 s ini poll (a sample at the write's instant reads the same on any build)
    held = _base("Item")
    assert md.ramp_old_measured(b, held, md.RAMP_OLD_AFTER_S)
    assert not md.ramp_old_measured(b, held, 0.4)                                                 # before ApplyConfigChange could run
    assert not md.ramp_old_measured(b, None, 9.0)
    assert not md.ramp_old_measured(b, s, 9.0)                                                    # the close happened
    q0 = _base()
    q1 = _s(restore={"doors": 0, "drops": 0, "backstops": {"ramp": 0, "ramp_quit": 1}}, seated=False)
    assert md.judge_quit_d(q0, q1, [], False)[0]
    assert not md.judge_quit_d(q0, q1, [], True)[0]                                               # the prompt survives the Autoload
    assert not md.judge_quit_d(q0, _s(restore={"doors": 0, "drops": 0, "backstops": {"ramp": 1, "ramp_quit": 0}}), [], False)[0]
    assert not md.judge_quit_d(q0, q1, ["x (should never happen)"], False)[0]
    after = _seated(restore={"doors": 0, "drops": 0, "backstops": {}})
    closed = _s(fp={"before": "0x1", "after": "0x1", "equal": True, "named": None, "outside_equal": True},
                restore={"doors": 1, "drops": 0, "backstops": {}}, seated=False)
    base = _base("MainMenu")
    assert md.judge_stall_view(base, [after, after], after, closed, 1)[0]
    assert not md.judge_stall_view(base, [after, _s(seated=False)], after, closed, 1)[0]          # closed on peer death
    assert not md.judge_stall_view(base, [], after, closed, 0)[0]
    ok, why = md.judge_stall_view(base, [after] * 15, after, closed, 0)                            # THE STALL WITNESS: never stale
    assert not ok and "not reached: the blackhole never staled the link" in why
    assert md.stale_read(St(raw={"netsync": {"session": {"peer_alive": False}}}))
    assert not md.stale_read(St(raw={"netsync": {"session": {"peer_alive": True}}})) and not md.stale_read(St())
    g = BW.OVERLAY_NAME_GUEST_MENU
    lk = (_s(mr={"count": 1}), _s(mr={"count": 2}, why="link"))
    assert md.judge_lost_line(*lk, [("off", True), (g, True), (g, False)])[0]
    assert not md.judge_lost_line(*lk, [("connecting", True)])[0]
    assert not md.judge_lost_line(*lk, [("connecting", True), ("connecting", True), (g, False)])[0]   # 29 only once the link is back
    assert not md.judge_lost_line(*lk, [])[0]                                                         # no sample inside the hold
    assert not md.judge_lost_line(_s(mr={"count": 1}), _s(mr={"count": 1}), [(g, True)])[0]
    pre = _s(mr={"count": 0, "silent": 0, "now": "dialog"}, dialog=True)
    assert md.judge_dialog_a(pre, _s(mr={"count": 0, "silent": 0}, dialog=True), True, True)[0]
    assert not md.judge_dialog_a(pre, _s(mr={"count": 0, "silent": 0}, dialog=False), True, True)[0]   # the window closed
    assert not md.judge_dialog_a(pre, _s(mr={"count": 0, "silent": 1}, dialog=True), True, True)[0]
    assert not md.judge_dialog_a(pre, _s(mr={"count": 0}, dialog=True), True, False)[0]
    assert md.judge_dialog_b(pre, _s(mr={"count": 0}, dialog=True), False, True)[0]
    assert not md.judge_dialog_b(pre, _s(mr={"count": 0}, dialog=False), False, True)[0]          # dialog_drop_lifted: the line closes
    assert not md.judge_dialog_b(pre, _s(mr={"count": 0}, dialog=True), True, True)[0]           # the lock still held it
    assert md.judge_hudstrip(pre, _s(mr={"count": 0, "silent": 0}, dialog=True), True)[0]
    assert not md.judge_hudstrip(pre, _s(mr={"count": 0, "silent": 0}, dialog=True), False)[0]
    assert not md.judge_hudstrip(pre, _s(mr={"count": 1, "silent": 0}, dialog=True), True)[0]


_SELFTEST_REFUSAL = ("the game refused a step: netsync: netsync endbench: needs the selftest role (netsync selftest 1) -- the duo guest "
                     "is role client")


class _PromptGame:
    """A guest for the quit-prompt drive: ``up`` = the stock quit prompt showing (the patched quit_prompt_up reads the state 'prompt')."""

    def __init__(self, md, up: bool):
        self.md, self.up, self.presses = md, up, []

    @property
    def state(self):
        return "prompt" if self.up else "hud"

    def wait_for(self, pred, timeout=None, what=None):
        if pred(self.state):
            return self.state
        raise self.md.HarnessError(f"timed out: {what}")

    def press(self, key, *a, **k):
        self.presses.append(str(key))
        if str(key) == "cancel":
            self.up = False

    def wait_frames(self, n):
        pass


def test_the_quit_prompt_falls_back_to_a_window_close_only_on_the_selftest_refusal(md, monkeypatch):
    """GM0-QUIT-D / GM0-CUT-QUIT (B4): `endbench quit on` first; only its 'needs the selftest role' refusal posts a WM_CLOSE to the duo's
    guest pid (never on another refusal, never without a pid -- the stub duo); a prompt that never came keeps the selftest words, so the
    row stays the NAMED 'not run'; the prompt comes down by Cancel (never Confirm) or `endbench quit off`."""
    sent, posted = [], []
    verdict = {"v": (False, _SELFTEST_REFUSAL)}

    def try_ns(g, *args, **k):
        sent.append(" ".join(map(str, args)))
        return verdict["v"] if args[:3] == ("endbench", "quit", "on") else (True, "")
    monkeypatch.setattr(md.cb, "try_ns", try_ns)
    monkeypatch.setattr(md.cb, "quit_prompt_up", lambda st: st == "prompt")

    class _Inst:
        def __init__(self, n):
            self.n = n

        def post_close(self, pid):
            posted.append(pid)
            return self.n

    class _Duo:
        def __init__(self, pid=4242, n=1, instances=True):
            self.pids = {"guest": pid, "host": 1111}
            self.instances = {"guest": _Inst(n), "host": _Inst(n)} if instances else {}

    class _StubDuo:                                                   # the stand-in's duo: no pids, no instances
        pass

    # endbench answers: no fallback
    verdict["v"] = (True, "")
    assert md._raise_quit_prompt(_Duo(), _PromptGame(md, False)) == (True, "", "endbench") and posted == []
    # another refusal: a plain red, no WM_CLOSE
    verdict["v"] = (False, "the game refused a step: netsync endbench: no bench")
    ok, why, how = md._raise_quit_prompt(_Duo(), _PromptGame(md, True))
    assert not ok and how is None and "no bench" in why and posted == []
    verdict["v"] = (False, _SELFTEST_REFUSAL)
    # the stub duo (no pid): the refusal's own words, no post -- the named 'not run'
    ok, why, how = md._raise_quit_prompt(_StubDuo(), _PromptGame(md, True))
    assert (ok, why, how) == (False, _SELFTEST_REFUSAL, None) and posted == []
    # a duo with the guest's pid: WM_CLOSE to the GUEST (never the host), the prompt up -> 'wm_close'
    ok, why, how = md._raise_quit_prompt(_Duo(), _PromptGame(md, True))
    assert ok and how == "wm_close" and posted == [4242] and "4242" in why
    # posted, but no prompt came: the selftest words kept (-> _quit_unreachable's named 'not run')
    posted.clear()
    ok, why, how = md._raise_quit_prompt(_Duo(), _PromptGame(md, False))
    assert not ok and how is None and posted == [4242] and "needs the selftest role" in why and "window close request" in why
    rows, ctx = [], {"config_skip": set()}
    md._quit_unreachable(lambda cid, okc, detail: rows.append((cid, okc, detail)), ctx, ("GM0-QUIT-D",), why)
    assert rows[0][0] == "GM0-QUIT-D" and rows[0][1] is False and "not run (configuration)" in rows[0][2]
    assert "no any-role quit-prompt verb" in rows[0][2] and ctx["config_skip"] == {"GM0-QUIT-D"}
    # no visible window took it (0 posted): the refusal's own words, no prompt wait
    posted.clear()
    assert md._raise_quit_prompt(_Duo(n=0), _PromptGame(md, True)) == (False, _SELFTEST_REFUSAL, None) and posted == [4242]
    # no Instance on the duo: the module's post_close (stubbed here: never a real WM_CLOSE from a test)
    posted.clear()
    monkeypatch.setattr(md, "_harness_instance", lambda: type("H", (), {"post_close": staticmethod(lambda pid: posted.append(pid) or 1)}))
    ok, _why, how = md._raise_quit_prompt(_Duo(instances=False), _PromptGame(md, True))
    assert ok and how == "wm_close" and posted == [4242]
    # down again: the WM_CLOSE prompt by Cancel, never Confirm; the bench's by `endbench quit off`
    g = _PromptGame(md, True)
    md._lower_quit_prompt(g, "wm_close")
    assert g.presses == ["cancel"] and not g.up
    md._lower_quit_prompt(g, "wm_close")                              # already down: no press at all
    assert g.presses == ["cancel"]
    sent.clear()
    md._lower_quit_prompt(_PromptGame(md, True), "endbench")
    assert sent == ["endbench quit off"]


def test_the_hole_gate_the_cut_quit_seat_and_the_door_read_the_published_session_keys(md):
    """GM0-HOLE-T (B5): the press waits for the session ITSELF (session.state 'live'; guestmenu.session on s168) besides the live freeze
    read -- THE PRE-INIT SAMPLE at the pairing edge. GM0-CUT-QUIT (B2): the second seat waits for the host's battle lane to go stale on the
    guest (term 6). Each a plain `netsync.*` literal, so test_coop_guest_menu's path pin checks it against the catch literal. GM0-DOOR-D
    (B6, DESIGN D1): `control` counts beside busy / leaving."""
    import inspect
    hole = inspect.getsource(md._t_hole)
    assert '"netsync.world.freeze.on") is True' in hole and '"netsync.session.state") == "live"' in hole, hole
    assert 'not ctx.gm["new"] or cb.path(s, "netsync.guestmenu.session") is True' in hole
    assert hole.index('"netsync.guestmenu.session"') < hole.index("_t_press(g, world=True)")
    cut = inspect.getsource(md._leg_cut)
    wf = cut.index("wait_field(host, HOME, RETURN_S)")
    stale = cut.index('"netsync.battle.peer.live") is False')
    assert wf < stale < cut.index('_seat_at(guest, "Item")', wf), cut[wf:wf + 600]
    assert "_raise_quit_prompt(d, guest)" in cut and "close_out(guest)" in cut[cut.index("_quit_unreachable("):]
    assert set(md.DOOR_D_WHYS) == {BW.GM_WHY_BUSY, BW.GM_WHY_LEAVING, BW.GM_WHY_CONTROL, BW.GM_WHY_SCENE}   # R5: + `scene`
    assert "DOOR_D_WHYS" in inspect.getsource(md.judge_door_d) and "judge_door_d" in inspect.getsource(md._leg_door)
    assert "_raise_quit_prompt(d, guest)" in inspect.getsource(md._leg_rampquit)


def test_the_t_leg_judges(md):
    words = BW.gm_refusal_line_rule("not_mirroring")
    pre = _s("WorldHUD", mr={"count": 0, "now": "audible"})
    s = _s("WorldHUD", mr={"count": 1}, why="not_mirroring", line={"text": words, "age": 9}, seated=False)
    assert md.judge_refused(("not_mirroring",), pre, s, world=True)[0]
    assert not md.judge_refused(("not_mirroring",), pre, _s("MainMenu", mr={"count": 0}), world=True)[0]   # its own menu opened
    assert not md.judge_refused(("not_mirroring",), _s("WorldHUD", mr={"count": 0, "now": "open"}), s, world=True)[0]
    assert md.own_menu_measured(_s("MainMenu", seated=False)) and not md.own_menu_measured(s)
    assert md.judge_stall_who(("not_mirroring",), pre, s, True, 2400)[0]
    ok, why = md.judge_stall_who(("not_mirroring",), pre, s, False, 900)                         # the press missed the stall
    assert not ok and "not reached: the press missed the stall (lane age 900 ms)" in why
    assert not md.judge_stall_who(("not_mirroring",), pre, _s("MainMenu", mr={"count": 0}), True, 2400)[0]   # stall_open: it opened
    own, p166 = BW.CAPS_S168, BW.CAPS_S166
    line = "[NetSync] guest " + BW.ww_caps_line_text(own, p166)
    pre2 = _s(mr={"count": 0, "now": "audible"})
    s2 = _s(mr={"count": 1}, why="older", line={"text": BW.gm_refusal_line_rule("older"), "age": 9})
    assert md.judge_caps_b(pre2, s2, [line], own, p166)[0]
    assert "guest menu" in line and "world fingerprint" in line
    assert not md.judge_caps_b(pre2, s2, [], own, p166)[0]
    assert not md.judge_caps_b(pre2, _seated(), [line], own, p166)[0]
    old166 = "[NetSync] guest " + BW.ww_caps_line_text(BW.CAPS_S167, p166)
    assert md.caps_b_old_measured(pre2, _s(mr={"count": 1}), [old166], p166)
    assert not md.caps_b_old_measured(pre2, _s(mr={"count": 1}), [], p166)
    assert md.caps_b_old_measured(pre2, _s(mr={"count": 1}), [], BW.CAPS_S167)
    assert not md.caps_b_old_measured(pre2, _s(mr={"count": 1}), [old166], BW.CAPS_S167)


def test_the_calibration_verdict_never_certifies_an_unpulled_lever_or_nothing(md):
    pred = ("GM0-REFUSE-I1-D",)
    green = md.cal_verdict(True, "capture", "capture", set(pred), pred, {"GM0-REFUSE-I1-D": True}, pred)
    assert green[0], green
    ok, why = md.cal_verdict(True, "capture", None, set(), (), {}, ())                         # refused or never read back
    assert not ok and "was not pulled" in why and "capture off" in why
    ok, why = md.cal_verdict(True, "closeold", "closeold", set(), (), {}, (), skip={"GM0-CUT"})  # every predicted row config-skipped
    assert not ok and "nothing calibrated: every predicted row unrun" in why
    assert md.cal_verdict(True, None, None, set(), (), {}, ())[0]                                # a lever-less s168 leg predicts ()
    # OLD: the leg's default lever is never sent on s167 -- its absence is no red; the shape still has to be MEASURED
    old = md.old_predicted("key")
    assert md.cal_verdict(False, "old", None, set(old), old, dict.fromkeys(old, True), old)[0]
    ok, why = md.cal_verdict(False, "old", None, set(old), old, {}, old)
    assert not ok and "rows whose shape was NOT measured: ['GM0-" in why


# ================================================================================================ the b3 tape (pb) and its T leg
def test_the_guest_menu_tape_facts_hold_on_a_synthetic_b3_tape_and_each_loss_reds_its_fact(pbm):
    cp = pbm.coop_peer_module()
    f = pbm.gm_tape_facts(pbm.synthetic_guest_menu_tape(cp), cp)
    ok, bad = pbm.gm_tape_ok(f)
    assert ok, bad
    assert f["away"] < f["back"] < f["battle"]["start"] < f["talk"] < f["chest"] < f["exit"] < f["rein"]
    assert f["sec12"]["with12"] == f["sec12"]["frames"] > 0 and f["sec12"]["order_ok"] == f["sec12"]["with12"]
    for kw, fact in (({"sec12": False}, "gm3"), ({"guest": False}, "gm3"), ({"battle": False}, "gm5"), ({"talk": False}, "gm6"),
                     ({"chest": False}, "gm7"), ({"world": False}, "gm8"), ({"pair_s": 20.0}, "gm1")):
        f2 = pbm.gm_tape_facts(pbm.synthetic_guest_menu_tape(cp, **kw), cp)
        reds = [k for k in pbm.GM_TAPE_FACT_NAMES if not f2[k]["ok"]]
        assert reds == [fact], (kw, reds, {k: f2[k]["why"] for k in reds})
    assert "an older host" in pbm.gm_tape_facts(pbm.synthetic_guest_menu_tape(cp, sec12=False), cp)["gm3"]["why"]
    empty = pbm.gm_tape_facts([], cp)
    assert all(not empty[k]["ok"] for k in pbm.GM_TAPE_FACT_NAMES)
    assert pbm.gm_stays([(1, 250), (2, 250), (3, 30602), (4, 30602), (5, 250)], 30602, 0) == [(3, 5)]
    assert pbm.gm_stays([(1, 250), (2, 30602)], 30602, 0) == [(2, 2)]
    # the plan's shape: one source for the recorder, the facts and the T leg
    ops = [op for op, _a, _s in pbm.GM_TAPE_PLAN]
    assert ops[:3] == ["stand", "warp", "warp"] and "battle" in ops and ops.index("talk") < ops.index("chest") < ops.index("world")
    assert pbm.GM_TAPE_PLAN[0][2] >= pbm.GM_PAIR_NEED_S


def test_the_tape_legs_windows_and_pointer(md, pbm, tmp_path, monkeypatch):
    cp = pbm.coop_peer_module()
    f = pbm.gm_tape_facts(pbm.synthetic_guest_menu_tape(cp), cp)
    w = md.t_tape_windows(f)
    assert f["start"] < w["key"] < w["stall"] < w["leave"] < f["away"] and w["cut"] < f["battle"]["start"]
    assert w["stall"] + md.STALL_S + 3.0 < f["away"]                                     # the stall clears before the warp
    assert w["stop_at"] == f["battle"]["end"] + 10.0 and md.t_tape_windows({}) == {}
    monkeypatch.setattr(md, "T_RAMP", "world")
    assert md.t_tape_windows(f)["stop_at"] == f["exit"] + 15.0
    monkeypatch.setenv("COOP_TAPE_DIR", str(tmp_path))
    monkeypatch.delenv("COOP_TAPE_GUEST_MENU", raising=False)
    assert pbm.latest_guest_menu_tape() is None
    t = tmp_path / "20261107-000000-host250-guest-menu-s168.f9tape"
    t.write_bytes(b"F9TAPE01")
    assert pbm.latest_guest_menu_tape() == t
    monkeypatch.setenv("COOP_TAPE_GUEST_MENU", str(tmp_path / "x.f9tape"))
    assert pbm.latest_guest_menu_tape() == (tmp_path / "x.f9tape").resolve()


def test_the_recorders_owner_gate_and_catalog():
    rec = _load("coop_tape_record", "coop_tape_record_gmd")
    ok = rec.guest_menu_gate(True, True, "0", True, False)
    assert ok[0]
    for args, words in (((False, True, "0", True, False), "UNSET"), ((True, False, "0", True, False), "UP"),
                        ((True, True, "1", True, False), "THE RECORDER DIALS THE OWNER"), ((True, True, "0", False, False), "LACKS"),
                        ((True, True, "0", True, True), "COOP_CALIBRATE")):
        got = rec.guest_menu_gate(*args)
        assert not got[0] and words in got[1], (args, got)
    assert rec.guest_menu_gate(True, True, None, True, False)[0] and rec.guest_menu_gate(True, True, "", True, False)[0]
    cat = list(rec.GUEST_MENU_CATALOG)
    assert cat[0] == "REC-OWNER" and cat[-1] == "REC-INI"
    assert [c for c in cat if c.startswith("REC-GMF")] == [f"REC-GMF{i}" for i in range(1, 9)]
    assert {"REC-G12", "REC-GL", "REC-B", "REC-W", "REC-GMT", "REC-GMC", "REC-WX", "REC-GMW", "REC-T"} <= set(cat)


# ================================================================================================ the stand-in duo (a child process)
def _child(payload, *, timeout: float = 1800.0) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_") and k not in _CLEAR}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _CHILD, str(SCENARIOS), str(REPO / "tools"), str(REPO / "ff9mapkit")],
                         env=env, input=json.dumps(payload), capture_output=True, text=True, timeout=timeout)
    assert out.returncode == 0, out.stderr[-4000:]
    line = [ln for ln in out.stdout.splitlines() if ln.startswith("@@")][-1]
    return json.loads(line[2:])


def _runs(**runs) -> dict:
    return _child({"runs": runs})


def _show(r, rows=None):
    return {c: r["detail"].get(c, "")[:500] for c in (rows if rows is not None else r["red"])}


def _unmodelled(md, leg) -> set:
    return {r for r in md.leg_rows(leg) if r in STANDIN_UNMODELLED or r in CONFIG_SKIPPED}


#: the duo legs the stand-in runs end to end (each green but its STANDIN_UNMODELLED / CONFIG_SKIPPED rows)
STANDIN_LEGS = ("key", "caps", "leave", "door", "title", "stall", "out", "world")
#: the legs the stand-in cannot drive (every row red for its pinned reason)
STANDIN_LEG_REASONS = ("dialog", "hudstrip", "cut", "scene", "chest", "ramp", "rampquit", "rejoin")
#: each (leg, fault) -> the words each of its rows must show (an unmodelled row's red alone would not prove the fault reached it)
FAULT_WORDS = {
    # C3(a): no census fires on a stand-in key, so `capture_leak` cannot reach its row offline (the row reads its pinned "not reached");
    # the fault is the census's, proven where a census fires (the gm_confirm seam: test_coop_guest_menu.py) and in game
    ("key", "capture_leak"): {"GM0-REFUSE-I1-D": "not reached"},
    ("key", "own_values"): {"GM0-SEAT-D": "TWO MARKERS (the host's players / party drawn, not the guest's own) False",
                            "GM0-BROWSE-D": "the seated party is the guest's own"},
    ("key", "restore_skip"): {"GM0-RESTORE-D": "named 'party'"},
    ("caps", "caps_ignored"): {"GM0-CAPS-a": "why 'no_data'"},
    ("leave", "leave_ignored"): {"GM0-LEAVE": "closes.leave +0", "GM0-FADE": "closes.leave +0"},
    ("title", "title_ignored"): {"GM0-TITLE": "closes.title +0"},
}


def _pinned_words(row):
    return STANDIN_UNMODELLED.get(row) or CONFIG_SKIPPED[row]


def test_the_stand_in_legs_are_green_but_their_unmodelled_rows(md):
    rs = _runs(**{leg: dict(leg=leg) for leg in STANDIN_LEGS})
    for leg in STANDIN_LEGS:
        r = rs[leg]
        want = _unmodelled(md, leg)
        assert set(r["red"]) == want, (leg, _show(r, set(r["red"]) ^ want))
        for row in want:
            assert _pinned_words(row) in r["detail"][row], (leg, row, r["detail"][row])
        assert r["all"][0] == "GMD-D0" and "GMD-D0" not in r["red"]
    d = {k: v for leg in STANDIN_LEGS for k, v in rs[leg]["detail"].items()}
    assert "now 'guest' on the HUD" in d["GM0-KEY"] and "'src': 'wire'" in d["GM0-KEY"] and "'frame_age_ms': -1" in d["GM0-KEY"]
    assert "TWO MARKERS (the host's players / party drawn, not the guest's own) True" in d["GM0-SEAT-D"]
    assert "census lines 1" not in d["GM0-REFUSE-I1-D"]                  # C3(a): never a census counted on a stand-in key
    assert "why 'older'" in d["GM0-CAPS-a"] and "after `caps on` seated True" in d["GM0-CAPS-a"]
    assert "'guest_menu'" in d["GM0-PAIRED-LINE-F"] and "'guest_menu'" in d["GM0-PAIRED-LINE-W"]
    assert "'cause': 'leave'" in d["GM0-LEAVE"] and "'from': 'Equip'" in d["GM0-LEAVE"] and "landed True" in d["GM0-LEAVE"]
    assert "Equip: closes.leave +1" in d["GM0-FADE"] and "root: closes.leave +1" in d["GM0-FADE"]
    assert f"close words {md.close_words_want('title')!r} at the close" in d["GM0-TITLE"] and "closes +0" in d["GM0-STALL-VIEW-D"]
    assert "read the link stale" in d["GM0-STALL-VIEW-D"] and "(0 read the link stale)" not in d["GM0-STALL-VIEW-D"]
    assert f"close words {md.close_words_want('out')!r} at the close" in d["GM0-OUT"]
    # decision 18: the request frame's one wait is lawful (at most one, before the close's end line); the start after the door
    assert "closes.out +1" in d["GM0-OUT"] and re.search(r"'the field HUD is not up' waits [01] at ", d["GM0-OUT"]), d["GM0-OUT"]
    # the any-role levers the legs sent: each a `guestmenu` op the agent takes, on the role the table names
    assert rs["caps"]["sent"] == ["host: guestmenu caps off", "host: guestmenu caps on", "host: guestmenu clear"]
    assert all(s.split()[2] in BW.GUESTMENU_ANY_ROLE_OPS for leg in STANDIN_LEGS for s in rs[leg]["sent"])


def test_the_legs_the_stand_in_cannot_drive_say_why(md):
    rs = _runs(**{leg: dict(leg=leg) for leg in STANDIN_LEG_REASONS})
    for leg in STANDIN_LEG_REASONS:
        r = rs[leg]
        assert set(r["red"]) == set(md.leg_rows(leg)), (leg, r["red"])
        for row in md.leg_rows(leg):
            assert _pinned_words(row) in r["detail"][row], (leg, row, r["detail"][row])


@pytest.mark.parametrize("leg", ["key", "caps", "leave", "door", "title", "stall", "out"])
def test_old_on_two_s167_stand_ins_is_exactly_its_rows_measured_and_no_guestmenu_op_is_sent(md, leg):
    r = _runs(r=dict(leg=leg, stage=167, cal=True))["r"]
    want = set(md.old_predicted(leg))
    assert set(r["red"]) == want, (r["red"], r["detail"].get("S168D-CAL"))
    assert "S168D-CAL" not in r["red"] and "rows whose shape was NOT measured: none" in r["detail"]["S168D-CAL"]
    assert r["sent"] == []
    assert "OLD (no guestmenu key)" in r["detail"]["GMD-D0"]
    assert all("OLD: no `netsync.guestmenu`" in r["detail"][x] and "refusal measured" in r["detail"][x] for x in want), _show(r)


#: the duo (leg, lever) calibrations the stand-in cannot MEASURE: `capture off` needs a census to pass, and no census fires on a stand-in
#: key (fakegame C3(a)) -- pinned to that gap in test_the_lever_the_stand_in_cannot_measure_reads_its_gap; calibrated in game
STANDIN_UNCALIBRATED = {("key", "capture")}


@pytest.mark.parametrize("case", ["key/old", "caps/old", "leave/old", "leave/closeold", "door/old", "title/old", "title/closeold",
                                  "stall/old", "out/old", "out/closeold"])
def test_each_lever_calibrates_exactly_and_measures_its_shape(md, case):
    leg, lever = case.split("/")
    assert (leg, lever) in md.LEVER_PREDICTED
    r = _runs(r=dict(leg=leg, cal=True, lever=lever))["r"]
    pred = set(md.LEVER_PREDICTED[(leg, lever)])
    gaps = _unmodelled(md, leg) - pred
    cal = r["detail"]["S168D-CAL"]
    assert set(r["red"]) - {"S168D-CAL"} == pred | gaps, (case, _show(r))
    assert "predicted reds that stayed GREEN: none" in cal and "rows whose shape was NOT measured: none" in cal, cal
    unpredicted = sorted(x for x in gaps if x not in CONFIG_SKIPPED)
    assert (f"unpredicted reds: {unpredicted}" if unpredicted else "unpredicted reds: none") in cal, cal
    assert ("S168D-CAL" in r["red"]) is bool(unpredicted)
    assert f"{md.LEVER_ROLE[lever]}: guestmenu " + " ".join(md.LEVER_OPS[lever]) in r["sent"], r["sent"]


def test_the_lever_the_stand_in_cannot_measure_reads_its_gap(md):
    """STANDIN_UNCALIBRATED: the lever is still SENT and its predicted rows red, and S168D-CAL is red naming exactly the stand-in's gap --
    the census row's shape NOT measured (no census fires on a stand-in key, C3(a))."""
    for leg, lever in sorted(STANDIN_UNCALIBRATED):
        assert (leg, lever) in md.LEVER_PREDICTED
        r = _runs(r=dict(leg=leg, cal=True, lever=lever))["r"]
        pred = set(md.LEVER_PREDICTED[(leg, lever)])
        cal = r["detail"]["S168D-CAL"]
        assert set(r["red"]) - {"S168D-CAL"} == pred | _unmodelled(md, leg), (leg, lever, _show(r))
        assert "S168D-CAL" in r["red"] and "predicted reds that stayed GREEN: none" in cal, cal
        assert f"rows whose shape was NOT measured: {sorted(pred)}" in cal, cal
        assert all(STANDIN_UNMODELLED[x] in r["detail"][x] for x in pred), _show(r, pred)
        assert f"{md.LEVER_ROLE[lever]}: guestmenu " + " ".join(md.LEVER_OPS[lever]) in r["sent"], r["sent"]


def test_an_old_launch_whose_press_measured_nothing_is_a_red_calibration(md):
    """THE CAL RULE on OLD (needs = the predicted rows): an s167 launch whose guest press never landed measured no s121 refusal -- its rows
    are red as predicted, yet nothing was MEASURED, and OLD cannot be rerun once s168 is deployed."""
    r = _runs(r=dict(leg="key", stage=167, cal=True, guest_no_menu=True))["r"]
    cal = r["detail"]["S168D-CAL"]
    assert "S168D-CAL" in r["red"] and "rows whose shape was NOT measured: ['GM0-" in cal, cal
    assert set(r["red"]) - {"S168D-CAL"} == set(md.old_predicted("key")), r["red"]


def test_a_lever_the_guest_refused_is_a_red_calibration(md):
    r = _runs(r=dict(leg="key", cal=True, lever="capture", refuse_ops=["capture off"]))["r"]
    cal = r["detail"]["S168D-CAL"]
    assert "S168D-CAL" in r["red"] and "was not pulled" in cal, cal
    assert "guest: guestmenu capture off" in r["sent"]


def test_a_lever_that_is_not_the_legs_is_refused_before_anything_runs(md):
    r = _runs(r=dict(leg="title", cal=True, lever="capture"))["r"]
    assert r["red"] == ["S168D-CAL"] and r["all"] == ["S168D-CAL"] and r["sent"] == []


def test_every_fault_the_tables_name_is_exercised(md):
    assert set(FAULT_WORDS) == {(leg, f) for leg, table in md.FAULT_REDS.items() for f in table}
    for (leg, fault), words in FAULT_WORDS.items():
        assert set(words) == set(md.FAULT_REDS[leg][fault]), (leg, fault)


@pytest.mark.parametrize("case", sorted(f"{leg}/{fault}" for leg, fault in FAULT_WORDS))
def test_each_stand_in_fault_turns_exactly_its_rows_red(md, case):
    leg, fault = case.split("/")
    r = _runs(r=dict(leg=leg, faults=[fault]))["r"]
    want = set(md.FAULT_REDS[leg][fault]) | _unmodelled(md, leg)
    assert set(r["red"]) == want, (case, _show(r, set(r["red"]) ^ want))
    for row, words in FAULT_WORDS[(leg, fault)].items():
        assert words in r["detail"][row], (case, row, r["detail"][row])


def test_the_recorders_owner_gate_on_the_stand_in_edits_nothing_and_makes_no_tape(tmp_path):
    r = _runs(rec=dict(kind="rec", tape_dir=str(tmp_path)))["rec"]
    assert "REC-OWNER" in r["red"] and "UNSET (the owner has not said go)" in r["detail"]["REC-OWNER"], r["detail"].get("REC-OWNER")
    assert "REC-INI" not in r["red"] and "never edited" in r["detail"]["REC-INI"]
    assert not list(tmp_path.rglob("*.f9tape")) and r["ini_same"] is True
    assert all(c == "REC-OWNER" or "THE OWNER GATE" in r["detail"][c] for c in r["red"]), {c: r["detail"][c][:200] for c in r["red"]}


def test_the_tape_leg_without_the_owner_gated_tape_is_its_gate_and_unrun_rows(md, tmp_path):
    r = _runs(t=dict(kind="t", leg="tape", tape_dir=str(tmp_path), cal=True))["t"]
    rows = set(md.T_ROWS["tape"])
    assert set(r["red"]) == rows | {"T2-TAPE", "T2-PEER", "S168-GMT-GATE"}, r["red"]
    assert all("no b3 tape (owner-gated)" in r["detail"][x] for x in rows)
    assert "no COOP_TAPE_GUEST_MENU" in r["detail"]["S168-GMT-GATE"] and "S168T-CAL" not in r["red"]
    assert r["ini_same"] is True and r["sent"] == [] and "never edited" in r["detail"]["T2-INI"]


# ------------------------------------------------------------------------------------------------ the 2026-11-08 rerun fixes (R1, R5)
def test_cut_quit_judges_every_report_the_window_saw(md):
    """R1: the window keeps every host report (not only the last): 'busy' seen and 'booting' never; a lone name still reads as one."""
    b = _base("Item")
    waiting = [_s("Item", close_step="quit", seated=True)] * 3
    assert md.judge_cut_quit(waiting, [None, "busy", "busy"], _closed("cut"), b)[0]
    assert md.judge_cut_quit(waiting, ["none", "busy"], _closed("cut"), b)[0]
    ok, why = md.judge_cut_quit(waiting, ["busy", "booting", "busy"], _closed("cut"), b)
    assert not ok and "['busy', 'booting']" in why and "never 'booting'" in why                         # a booting between two busy
    assert not md.judge_cut_quit(waiting, [None, None], _closed("cut"), b)[0]
    assert not md.judge_cut_quit(waiting, [], _closed("cut"), b)[0] and not md.judge_cut_quit(waiting, None, _closed("cut"), b)[0]


def test_cut_quits_window_opens_at_the_guests_close_not_the_hosts_battle(md):
    """R1: start_battle returns at the HOST's battle, one relay hop before the guest's cut close: the window waits for closes.cut +1 on
    the guest first; a close that never begins is 'not reached' (the prompt lowered, the menu closed, the host's fight run out)."""
    import inspect
    cut = inspect.getsource(md._leg_cut)
    sb = cut.index("host.start_battle(SCENE, group=GROUP)")
    began = cut.index('began = poll(guest, lambda x: _d(base2, snap(x), "closes", "cut") >= 1 and (_gm(x).get("close_step") is not None')
    window = cut.index("waiting, reports = [], []")
    assert sb < began < window, cut[sb:window]
    # the request frame's publish reads closes.cut +1 with close_step None: the window waits for the first JUDGED step (or a close ended)
    assert 'or not _gm(x).get("close_pending")),' in cut[began:window] and 'CLOSE_S, "the cut close began on the guest")' in cut[began:window]
    miss = cut[began:window]
    assert "not reached: the host's battle never closed the guest's menu" in miss
    assert miss.index("_lower_quit_prompt(guest, how)") < miss.index("close_out(guest)") < miss.index("_fight_out(host)")
    assert "reports.append(boot_name(host.state))" in cut and "judge_cut_quit(waiting, reports," in cut
    assert 'd.note(f"GM0-CUT-QUIT: the quit prompt up by {how}' in cut


def test_door_d_runs_on_its_own_long_fade_leg_and_accepts_scene(md):
    """R5: GM0-DOOR-D left the leave leg for its own `door` launch, gated on FadeDuration >= FADE_DOOR_MS (800); its door verdicts take
    `scene` -- the host door's control-off lead-in, the likeliest."""
    import inspect
    assert md.DUO_ROWS["door"] == ("GM0-DOOR-D",) and "GM0-DOOR-D" not in md.DUO_ROWS["leave"] and md.FNS["door"] is md._leg_door
    assert md.LEG_LEVERS["door"] == ("old",) and md.LEVER_PREDICTED[("door", "old")] == ("GM0-DOOR-D",) and md.FADE_DOOR_MS == 800
    assert "GM0-DOOR-D" in md.FADE_ROWS and md.DUO_LEGS.index("door") == md.DUO_LEGS.index("leave") + 1
    assert "GM0-DOOR-D" not in inspect.getsource(md._leg_leave)
    door = inspect.getsource(md._leg_door)
    gate = door.index('if ctx["pulled"] != "old" and (ctx["fade_ms"] or 40) < FADE_DOOR_MS:')     # under `old`: at any fade
    assert door.index("_old_gate(") < gate < door.index("ready(guest)") < door.index('guest.press("menu")')
    assert door.index('guest.press("menu")') < door.index('host.send(f"warp {AWAY} -1 -1", wait=False)') < door.index("judge_door_d(")
    pre = _s()
    for w in md.DOOR_D_WHYS:
        s = _s(door_refused=dict(_gmk()["door_refused"], **{w: 1}), seated=False)
        assert md.judge_door_d(pre, s, True)[0], w
    s = _s(door_refused=dict(_gmk()["door_refused"], scene=1), seated=False)
    ok, why = md.judge_door_d(pre, s, True)
    assert ok and "{'scene': 1}" in why
    assert not md.judge_door_d(pre, s, False)[0]                                                          # the follow never landed
    assert not md.judge_door_d(pre, _s(door_refused=dict(_gmk()["door_refused"], ui=1), seated=False), True)[0]   # not a door verdict
    assert not md.judge_door_d(pre, _s(door_refused=dict(_gmk()["door_refused"], scene=1, control=1), seated=False), True)[0]
    assert not md.judge_door_d(pre, _s(door_refused=dict(_gmk()["door_refused"], scene=1), seated=True), True)[0]
    assert not md.judge_door_d(pre, _s(door_refused=dict(_gmk()["door_refused"], scene=1), seated=False, event_enable=False), True)[0]


def test_every_duo_press_carries_the_launchs_fade_into_the_settle(md):
    """R4: _d0 keeps the guest's FadeDuration in LAUNCH_FADE, and _gctx hands it to coop_guest_menu._ready's HUD-FADE SETTLE."""
    import inspect
    d0 = inspect.getsource(md._d0)
    assert d0.index('ctx["fade_ms"] = ') < d0.index('LAUNCH_FADE["ms"] = ctx["fade_ms"]')
    old = md.LAUNCH_FADE["ms"]
    try:
        md.LAUNCH_FADE["ms"] = 800
        from types import SimpleNamespace
        g = SimpleNamespace(state=SimpleNamespace(raw={"netsync": {"guestmenu": {}}}, netsync={"guestmenu": {}}))
        assert md._gctx(g)["fade_ms"] == 800
    finally:
        md.LAUNCH_FADE["ms"] = old
