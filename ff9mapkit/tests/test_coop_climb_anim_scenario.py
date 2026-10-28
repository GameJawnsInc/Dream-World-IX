"""[ff9mapkit netsync s157] THE CLIMB-ANIM BENCHES' SCENARIO HALF -- studies/test-harness/scenarios/coop_climb_anim.py (the
solo bench) and coop_climb_anim_peer.py (the wire half). Their judges are pinned by test_coop_climb_anim_bench.py; these pin
the SCENARIOS, offline:

  * both import (through the driver's own path setup) and their tables are their docstrings: the catalog per mode, the
    tallies DERIVED from it (solo 21/21, 8/12, 16/20, 17/22; wire 9/9, 3/5), the predicted sets inside the catalog, the N/A
    rows dropped and never scored;
  * the whole solo bench runs against a POCKET SIMULATOR of 114 / 207 / 408 on a virtual clock -- coop_guest_traversal's
    (test_coop_guest_traversal_bench.Sim) with the s157 surfaces added here (:class:`ClimbSim`: the twin rows on a dressed
    body, the mirror ghost's frame-follow, the proof lines, the two levers and their release). It models only what the
    bench OBSERVES, never the engine. It reads 21/21 on a correct s157 model; 8/12 with K-CAL-M + K-CAL green on an s156
    model (never sending `bench ghostframe` -- an s156 agent reads it as `bench 1` -- nor `selfdress twin`); exactly the
    four TW rows red under COOP_CALIBRATE=twin and exactly the five GF rows under COOP_CALIBRATE=frame; and goes red on
    EXACTLY the rows a broken engine breaks (a ghost that never follows, twins that never map, an ini the engine never
    read, a release that keeps the twin lever);
  * every run restores the root's ini, takes the 207 / 408 stills through the seams, and QUITS the game -- also when K0
    refuses and when a leg raises; an --attach'd game is never quit;
  * under the REAL driver (harness.Session) over harness.fakegame.FakeGame -- the stand-in's own key layout -- both benches
    tell the live rung (s157) from the s156 rung, refuse without an instance root, and leave no game process running;
  * the wire half's pure parts (its peer argv per leg, the tape / sender judges and markers) and its refusals (no instance,
    the owner's port) -- which start no peer and still quit.

Every scenario-touching test runs in a CHILD process (the scenarios put their own dir on sys.path -- never this process's).
"""
import json
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
SCENARIOS = REPO / "studies" / "test-harness" / "scenarios"
TOOLS = REPO / "tools"
KIT = REPO / "ff9mapkit"
HERE = pathlib.Path(__file__).resolve()
GT_BENCH = HERE.parent / "test_coop_guest_traversal_bench.py"

_CHILD = r'''
import importlib.util, json, sys
test_file, scen, tools, kit, gt_bench = sys.argv[1:6]
sys.path.insert(0, tools)
sys.path.insert(0, kit)
sys.path.insert(0, scen)
spec = importlib.util.spec_from_file_location("climb_anim_scenario_test", test_file)
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)
doc = json.loads(sys.stdin.read() or "{}")
print("@@RESULT@@" + json.dumps(T.child_main(doc, scen, gt_bench), default=repr))
'''


def _child(doc: dict, timeout: float = 1200.0):
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-c", _CHILD, str(HERE), str(SCENARIOS), str(TOOLS), str(KIT), str(GT_BENCH)],
                         env=env, input=json.dumps(doc), capture_output=True, text=True, timeout=timeout)
    assert out.returncode == 0, (out.stdout[-2000:], out.stderr[-4000:])
    line = [ln for ln in out.stdout.splitlines() if ln.startswith("@@RESULT@@")][-1]
    return json.loads(line[len("@@RESULT@@"):])


def _load(path, name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def child_main(doc: dict, scen: str, gt_bench: str):
    """Runs INSIDE the child: ``tables``, ``runs`` (whole solo sim runs), ``peer`` (the wire half's pure parts + refusals)."""
    ca = _load(pathlib.Path(scen) / "coop_climb_anim.py", "coop_climb_anim")
    cp = _load(pathlib.Path(scen) / "coop_climb_anim_peer.py", "coop_climb_anim_peer")
    out = {}
    if doc.get("tables"):
        out["tables"] = _tables(ca, cp)
    if "runs" in doc:
        T = _load(gt_bench, "gt_bench_for_climb_anim")
        out["runs"] = {name: sim_run(ca, T, **spec) for name, spec in doc["runs"].items()}
    if doc.get("peer"):
        out["peer"] = _peer(cp)
    if "fake" in doc:
        out["fake"] = {cap or "live": {n: _fake_run(m, cap) for n, m in (("solo", ca), ("wire", cp))} for cap in doc["fake"]}
    return out


def _fake_run(mod, caps) -> dict:
    """The scenario under the REAL driver (harness.Session) over harness.fakegame.FakeGame -- no instance root, so the
    setup refuses before any game work; ``caps`` a rung (FG.caps_through) or None (the stand-in's live engine)."""
    import tempfile
    from harness import Session
    from harness import fakegame as FG
    t = pathlib.Path(tempfile.mkdtemp())
    (t / "x64").mkdir()
    (t / "x64" / "FF9.exe").write_bytes(b"MZ")
    (t / "x64" / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    (t / "FF9CustomMap").mkdir()
    (t / "FF9CustomMap" / "DictionaryPatch.txt").write_text("", encoding="utf-8")
    fake = FG.FakeGame(t)
    fake.fps = 240
    if caps:
        fake.netsync_caps = FG.caps_through(caps)
    g = Session(game_path=t, run_dir=t / "run", save_dir=t / "player-saves", pid_probe=lambda: [],
                launcher=lambda exe, fake=fake: fake.start(), boot_timeout=15.0, verbose=False)
    with g:
        mod.run(g)
        rows = list(g.checks)
        alive = g.proc is not None and g.proc.poll() is None
    return {"all": sorted(r["what"].split(":")[0] for r in rows), "red": sorted(r["what"].split(":")[0] for r in rows
                                                                              if not r["ok"]),
            "setup": next((r["detail"] for r in rows if r["what"].startswith(("K0:", "W0:"))), None), "alive": alive}


def _tables(ca, cp) -> dict:
    return {"solo": {m: {"catalog": sorted(ca.catalog(m)), "tally": list(ca.tally(m)), "pred": list(ca.predicted(m))}
                     for m in ("s156", "plain", "twin", "frame")},
            "solo_no_gl": sorted(ca.catalog("s156", False)),
            "modes": [ca.mode_of(c, s) for c, s in (("", True), ("0", True), ("twin", True), ("FRAME ", True), ("1", True),
                                                       ("twin", False), ("", False))],
            "wire": {m: {"catalog": sorted(cp.catalog(m)), "tally": list(cp.tally(m)), "pred": list(cp.predicted(m))}
                     for m in ("s156", "plain")},
            "ids": {"rig": ca.RIG, "model": ca.DRESS_MODEL, "geo": ca.DRESS_GEO, "twins": sorted(ca.TWIN_IDS),
                    "alias": sorted(ca.ALIAS_IDS), "release": ca.DRESS_RELEASE},
            "doc": " ".join((ca.__doc__ or "").split()), "peer_doc": " ".join((cp.__doc__ or "").split())}


# ================================================================================================ the s157 pocket model
#: Zidane's own clips the stock ladder / hop plays (the twin rows' SOURCE ids) and Vivi's own (114's undressed body)
ZDN = {"mount": 10687, "loop": 10539, "exit": 10685, "hop": 10446}
VIV = {"mount": 10281, "loop": 10277, "exit": 10279, "hop": 11670}
FRAMES = {"mount": 8, "loop": 12, "exit": 14, "hop": 27, "idle": 30}


def _climb_sim_class(T):
    """ClimbSim over the guest-traversal bench's Sim (built in the child, where that module is loaded)."""
    import math
    from harness import HarnessError
    from harness import battlewire as BW
    from harness import fakegame as FG

    class ClimbSim(T.Sim):
        """The s157 surfaces over the s156 pocket model -- as the climb-anim bench OBSERVES them, never the engine: the
        controlled body's anim / GEO / frame (a stock RunAnimation per phase: Zidane's on 207 / 408, Vivi's own on 114), a
        `selfdress self steiner` arm at the NEXT load (rig 3, model 5489), MapAnim's twin row on it (or s140's idle alias
        under `twin off` / on s156; `twin miss`: the alias and twin_misses), the per-load counters, the selftest mirror's
        ghost (GhostAs "" wears my body raw; any other value the moogle, whose rule plays its idle: why "clip") and its
        frame-follow (lever, loco, snaps / steps / wraps / restores), the proof lines and the release."""

        def __init__(self, clock, gt, *, s157=True, mutants=(), log_path=None):
            super().__init__(clock, gt, engine="s156", mutants=mutants, log_path=log_path)
            self.s157 = s157
            self.ghost_as = "auto"
            self.self_spec = None
            self.rig = -1
            self.twin_lever = "on"
            self.gf_off = False
            self.twin_proof = False
            self.hazard = []                         # verbs an s156 agent would misread (the bench must never send them)
            self._per_load()
            self.gf_on, self.gf_last, self.gf_clip = False, -1, None
            self.gf_steps = self.gf_wraps = self.gf_snaps = self.gf_restores = 0
            self.gf_time = 0.0

        def _per_load(self):
            self.twins = self.twin_misses = 0
            self.twin_last = {"src": -1, "twin": -1, "site": -1}
            self.raw_anim, self.body_anim, self.anim_frame, self.anim_n = None, None, 0, FRAMES["idle"]
            self._tick = 0

        # -- the body ---------------------------------------------------------------------------------------------
        def _own(self):
            return VIV if self.field == 114 and self.rig < 0 else ZDN

        def _phase(self):
            m = self.motion
            if m is None:
                return "idle"
            return "hop" if m["kind"] == "hop" else m["phase"]

        def _raw_for(self, phase):
            if phase == "idle":
                return 148 if self.field == 114 and self.rig < 0 else 200
            return self._own()[phase]

        def _map(self, raw, phase):
            """MapAnim on the dressed body: the idle slot -> the rig's idle; a Zidane ladder / jump -> its twin row
            (s157, `twin on`), else s140's idle alias (`twin off`, s156, a dead twin); `twin miss`: the alias, counted."""
            if self.rig < 0:
                return raw
            row = BW.rig_row(self.rig)
            if phase == "idle":
                return row["idle"]
            twin = BW.TWIN_BY_KEY.get((self.rig, raw), 0)
            if self.s157 and twin and "twin_dead" not in self.mut:
                if self.twin_lever == "on":
                    self.twins += 1
                    self.twin_last = {"src": raw, "twin": twin, "site": BW.SITE_PLAY}
                    return twin
                if self.twin_lever == "miss":
                    self.twin_misses += 1
            return row["idle_alias"]

        def step(self):
            y0, ph0 = self.pos[1], self._phase()
            super().step()
            ph = self._phase()
            raw = self._raw_for(ph)
            if raw != self.raw_anim:
                self.raw_anim = raw
                self.body_anim = self._map(raw, ph)
                self.anim_n = BW.TWIN_FRAMES.get(self.body_anim, FRAMES[ph])
                self.anim_frame = 0
            else:
                self._tick += 1
                moved = self.pos[1] != y0 if ph == "loop" else (self._tick % 2 == 0)
                if moved and ph == ph0:
                    self.anim_frame = (self.anim_frame + 1) % self.anim_n
            self._ghost_step()

        def body_model(self):
            if self.rig >= 0:
                return BW.rig_row(self.rig)["model"]
            return 8 if self.field == 114 else 98

        # -- the mirror ghost ----------------------------------------------------------------------------------------
        def mirror(self):
            return self.selftest and self.ui == "FieldHUD" and self.field > 0

        def _ghost(self):
            """(model, anim) the mirror plays: my body raw under GhostAs "", else the moogle's idle (s139's rule)."""
            if self.ghost_as == "":
                return self.body_model(), self.body_anim
            return BW.rig_row(8)["model"], BW.rig_row(8)["idle"]

        def _why(self):
            if self.gf_off and self.selftest:
                return "lever"
            if "gf_free" in self.mut:
                return "broken"
            loco_other = BW.classify_loco(self.body_model(), self.body_anim) == BW.LOCO_OTHER
            if not loco_other:
                return "loco"
            return None if self._ghost()[1] == self.body_anim else "clip"

        def _ghost_step(self):
            if not (self.s157 and self.mirror()) or self.body_anim is None:
                self.gf_on = False
                return
            why = self._why()
            n, f = self.anim_n, self.anim_frame
            clip = self._clip(self._ghost()[1])
            if why is None:
                if not self.gf_on or clip != self.gf_clip:
                    self.gf_snaps += 1
                elif f != self.gf_last:
                    kind, _step = BW.ghost_frame_step(self.gf_last, f, n)
                    if kind == BW.GF_STEP_SNAP:
                        self.gf_snaps += 1
                    elif kind == BW.GF_STEP_WRAP:
                        self.gf_wraps += 1
                    else:
                        self.gf_steps += 1
                self.gf_on, self.gf_last, self.gf_clip = True, f, clip
                self.gf_time = f / n * (n / 30.0)
            else:
                if self.gf_on:
                    self.gf_restores += 1
                self.gf_on, self.gf_last, self.gf_clip = False, -1, None
                self.gf_time = (self.gf_time + 1.0 / T.FPS) % (n / 30.0)
            self.gf_why = why

        @staticmethod
        def _clip(anim):
            return BW.anim_name(anim) if anim is not None else None

        # -- the verbs ----------------------------------------------------------------------------------------------
        def netsync(self, sub, args):
            a = [str(x) for x in args]
            if sub == "selftest":
                first = not self.proof_done
                super().netsync(sub, args)
                if first and self.selftest and self.s157 and not self.twin_proof:
                    self.twin_proof = True
                    self.log("[NetSync] " + BW.proof_ok(BW.PROOF_DRESS_TWIN, BW.DRESS_TWIN_SELFTEST_ROWS))
                    self.log(f"[NetSync] {FG.PROOF_GHOST_FRAME}OK ({FG.FAKE_GHOSTFRAME_SELFTEST_ROWS} rows, "
                             f"{FG.FAKE_GHOSTFRAME_MUTANTS} mutants caught)")
                return
            if sub == "bench" and a[:1] == ["ghostframe"]:
                if not self.s157:
                    self.hazard.append(" ".join([sub] + a))
                    self.bench = True                 # an s156 agent's Arg() fallback: `bench 1`, the field-gate bench ON
                    return
                if not self.selftest:
                    raise HarnessError("netsync bench: needs the selftest role (netsync selftest 1)")
                self.gf_off = a[1:] == ["off"]
                self.log(FG.GHOSTFRAME_LOG_OFF if self.gf_off else FG.GHOSTFRAME_LOG_ON)
                return
            if sub == "selfdress":
                if not self.selftest:
                    raise HarnessError("netsync selfdress: needs the selftest role (netsync selftest 1)")
                if a[:1] == ["self"] and len(a) == 2:
                    self.self_spec = a[1]
                    return
                if a[:1] == ["twin"]:
                    if not self.s157:
                        self.hazard.append(" ".join([sub] + a))
                        raise HarnessError("netsync selfdress: unknown op 'twin' (ghost|empty|rule|wire|clear|self|gate|law|"
                                           "polish)")
                    self.twin_lever = a[1]
                    self.log({"on": BW.TWIN_ON_LOG, "off": BW.TWIN_OFF_LOG, "miss": BW.TWIN_MISS_LOG}[a[1]])
                    return
                raise HarnessError(f"sim: selfdress {a} not modelled")
            return super().netsync(sub, args)

        def reset(self):
            super().reset()
            if self.s157 and self.gf_off:
                self.log(FG.GHOSTFRAME_LOG_RELEASE)
            self.gf_off = False
            if self.self_spec is not None or self.twin_lever != "on":
                self.log("[NetSync] harness: " + BW.SELF_RELEASE_LINE + "released with the harness)")
            self.self_spec = None
            if "release_keeps_twin" not in self.mut:
                self.twin_lever = "on"
            self.rig = -1

        def warp(self, fid, scenario=None):
            super().warp(fid, scenario)
            self.rig = BW.NAME_TO_RIG.get(self.self_spec, -1) if self.self_spec else -1
            self.dressed = self.rig >= 0
            self._per_load()

        # -- the published document ------------------------------------------------------------------------------------
        def doc(self):
            d = super().doc()
            anim = self.body_anim
            model = self.body_model()
            geo = BW.geo_name(model)
            name = self._clip(anim)
            d["player"].update(model=model, anim=anim, geo=geo, anim_geo=BW.folder_of(name) if name else None,
                               clip=name, anim_frame=self.anim_frame, frame_n=self.anim_n)
            ns = d["netsync"]
            self_doc = {"armed": self.rig >= 0, "rig": self.rig, "bench_self": self.self_spec}
            if self.s157:
                self_doc.update(twin_rows=BW.TWIN_ROW_COUNT, twins=self.twins, twin_misses=self.twin_misses,
                                twin_last=dict(self.twin_last), ghost_clip_misses=0,
                                twin_clips_on_disc=BW.TWIN_CLIP_COUNT if self.twin_proof else -1, twin_clip_missing=-1,
                                twin=self.twin_lever, twin_selftest=BW.DRESS_TWIN_SELFTEST_OK if self.twin_proof else None)
            mirror = self.mirror()
            gm, ga = self._ghost() if mirror else (0, None)
            ns["dress"] = {"self": self_doc, "ghost": {"model": gm if mirror else 0, "clip": self._clip(ga) if mirror else None,
                                                      "mode": "ini:" + self.ghost_as}}
            ns["session"] = {"ghost": mirror}
            if self.s157:
                gf = dict(FG.NETSYNC_GHOSTFRAME_SENTINELS)
                gf.update(lever_off=self.gf_off, selftest="ok" if self.twin_proof else None, steps=self.gf_steps,
                          wraps=self.gf_wraps, snaps=self.gf_snaps, restores=self.gf_restores)
                if mirror and anim is not None:
                    n = self.anim_n
                    ln = n / 30.0
                    gf.update(follow=self.gf_on, why=getattr(self, "gf_why", None), has_frame=True, wire_anim=anim,
                              wire_frame=self.anim_frame, wire_frame_n=n, wire_loco=BW.classify_loco(model, anim),
                              clip=self._clip(ga), speed=0.0 if self.gf_on else 1.0, time=round(self.gf_time, 5),
                              length=ln, shown=float(self.anim_frame) if self.gf_on else -1.0,
                              target=float(self.anim_frame) if self.gf_on else -1.0)
                ns["ghostframe"] = gf
            return d

    return ClimbSim


class _Instance:
    def __init__(self, sim, mutants):
        self.sim, self.mut = sim, set(mutants)
        self.writes, self.restores = [], 0

    def netsync(self, updates, *, backup_to=None, out=None):
        self.writes.append(dict(updates))
        if "GhostAs" in updates and "ini_unread" not in self.mut:
            self.sim.ghost_as = updates["GhostAs"]
        return pathlib.Path(str(backup_to)) / "Memoria.ini.bak"

    def restore_ini(self):
        self.restores += 1
        self.sim.ghost_as = "auto"
        return True


def sim_run(ca, T, *, s157: bool = True, cal: str = "", mutants=(), instance: bool = True, attach: bool = False,
            raise_at=None, shot_fault: bool = False) -> dict:
    """One whole solo bench run on the pocket simulator (in the child). ``raise_at`` -- the warp to that field raises a
    KeyError (a BENCH bug, not a HarnessError: it escapes the leg and the run); ``shot_fault`` -- every engine `shot`
    raises one (inside a leg: the hang's still, the hop's watch)."""
    import tempfile
    clock = T.VClock()
    for mod in (ca, ca.gt, ca.cb):
        mod.time = clock
    ca.calibration_env = lambda: cal
    ca.gt.kit_table = lambda: (dict(T.SIM_TABLE), "the sim's table")
    grabs = []
    ca.grab_frame = lambda g, path: (grabs.append(("sync", pathlib.Path(path).name)) or (pathlib.Path(path), "grabbed"))
    ca.start_grab = lambda g, path: (grabs.append(("async", pathlib.Path(path).name)) or {"path": pathlib.Path(path)})
    ca.finish_grab = lambda h: (h["path"], "grabbed", 1.2)
    tmp = pathlib.Path(tempfile.mkdtemp())
    sim = _climb_sim_class(T)(clock, ca.gt, s157=s157, mutants=mutants, log_path=tmp / "Memoria.log")
    g = T.SimSession(sim, clock, tmp)
    g.attach = attach
    g.instance = _Instance(sim, mutants) if instance else None
    g.quits, g.shots = [], []
    g.pid = None

    def shot(name):
        g.shots.append(name)
        if shot_fault:
            raise KeyError(f"sim: shot {name} (a test fault)")
        p = tmp / "eshots" / f"{name}.png"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x89PNG")
        return p
    g.shot = shot
    g.quit = lambda: g.quits.append(sim.frame)
    if raise_at is not None:
        real_warp = g.warp

        def warp(field, **kw):
            if int(field) == int(raise_at):
                raise KeyError(f"sim: the warp to {field} raised (a test fault)")
            return real_warp(field, **kw)
        g.warp = warp
    ca.run(g)
    rows = g.checks
    sent = [list(s) for s in g.sent]
    return {"red": sorted(r["what"].split(":")[0] for r in rows if not r["ok"]),
            "all": sorted({r["what"].split(":")[0] for r in rows}), "n": len(rows),
            "detail": {r["what"].split(":")[0]: r["detail"] for r in rows}, "notes": g.notes, "sent": sent,
            "hazard": sim.hazard, "quits": len(g.quits), "after_quit": _after_quit(sent),
            "ini": {"writes": g.instance.writes if g.instance else None, "restores": g.instance.restores if g.instance else 0},
            "grabs": grabs, "shots": g.shots, "log": sim.log_path.read_text(encoding="utf-8").splitlines(),
            "held_at_end": [b for b in ("up", "down", "left", "right", "confirm") if sim.held_now(b)],
            "virtual_s": round(clock.t - 10000.0, 1)}


def _after_quit(sent) -> list:
    """Every verb sent after the quit (none may follow it)."""
    idx = [i for i, s in enumerate(sent) if s[:1] == ["quit"]]
    return sent[idx[0] + 1:] if idx else []


# ================================================================================================ the wire half, in the child
def _peer(cp) -> dict:
    import tempfile
    from harness import coop_peer as CP
    out = {"args": {"base": cp.peer_args(49257), "echo": cp.peer_args(49257, ["--frame", "echo", "--tap", "t.f9tape"]),
                    "pin": cp.pinned_args("5/12"), "guard": [cp.pinned_args(f, loco=lo) for f, lo, _ in cp.GUARDS],
                    "seam": [cp.pinned_args(f, step=s) for f, s in cp.SEAMS]},
           "values": cp.host_values(49257), "pin_clip": cp.BW.anim_name(cp.PIN_ANIM)}
    # the argv parses as coop_peer's own serve-guest parser reads it
    parsed = []
    for extra in out["args"]["guard"] + out["args"]["seam"] + [out["args"]["pin"], ["--frame", "none"]]:
        p = CP._parse_frame(extra[extra.index("--frame") + 1])
        parsed.append(list(p) if isinstance(p, tuple) else p)
    out["parsed"] = parsed
    # the tape judges over two real tapes written by coop_peer's own writer: an s157 host (39 B) and an s156 host (37 B)
    tmp = pathlib.Path(tempfile.mkdtemp())
    res = {}
    for name, kw in (("s157", {"anim_frame": 3, "frame_n": 12}), ("s156", {}), ("mixed", None)):
        path = tmp / f"{name}.f9tape"
        w = CP.TapeWriter(path, mode="serve-guest", extra={"bench": "test_coop_climb_anim_scenario"})
        for i in range(5):
            k = kw if kw is not None else ({"anim_frame": 1, "frame_n": 12} if i % 2 else {})
            w.write(CP.DIR_HOST, CP.build_pos_frame(207, anim=10539, model=98, **k))
            w.write(CP.DIR_GUEST, CP.build_pos_frame(207, anim=10539, model=98))
        w.close()
        f = cp.tape_frames(CP, path)
        res[name] = {"f": f, "judge": list(cp.judge_tape(f)), "marker": list(cp.tape_marker(f))}
    res["missing"] = {"f": cp.tape_frames(CP, tmp / "nope.f9tape")}
    res["missing"]["judge"] = list(cp.judge_tape(res["missing"]["f"]))
    out["tapes"] = res
    edge39 = CP.HOST_TRAILER_LINE.format(n=39, f=0, fn=0)
    edge37 = CP.HOST_NO_TRAILER_LINE.format(n=37)
    out["sender"] = {"s157": list(cp.J.judge_sender([f"x {edge39}"])),
                     "stopped": list(cp.J.judge_sender([f"x {edge39}", f"x {edge37}"])),
                     "s156_marker": list(cp.sender_marker({"lines": ["host pos: field 207 (was -)"], "connected": True})),
                     "s157_marker": list(cp.sender_marker({"lines": [f"x {edge39}"], "connected": True})),
                     "unconnected_marker": list(cp.sender_marker({"lines": [], "connected": False}))}
    out["refusals"] = {k: _peer_refusal(cp, **kw) for k, kw in
                       (("no_instance", {"instance": False}), ("owner_port", {"port": "49201"}),
                        ("attach", {"attach": True}))}
    return out


def _peer_refusal(cp, *, instance=True, port=None, attach=False) -> dict:
    """The wire half on a stand-in session that refuses before any game work: no peer may start, the game still quits."""
    import tempfile
    tmp = pathlib.Path(tempfile.mkdtemp())
    started = []

    class NoPeer:
        def __init__(self, *a, **k):
            started.append(a)
            raise AssertionError("a peer was started by a refused setup")

    class G:
        NETSYNC_SUBVERBS = None
        run_dir = tmp
        scenario_dir = None
        game_path = tmp

        def __init__(self):
            self.attach = attach
            self.instance = object() if instance else None
            self.checks, self.notes, self.quits, self.sent = [], [], 0, []

        @property
        def state(self):
            from harness.channel import State
            return State({"netsync": {"ghostframe": {"follow": False}, "forced": False}, "field": {"id": 70},
                          "player": {"control": True}})

        def wait_for(self, pred, *, timeout=1.0, what=""):
            st = self.state
            if pred(st):
                return st
            from harness import HarnessError
            raise HarnessError("timed out")

        def note(self, t):
            self.notes.append(t)

        def check(self, ok, what, detail=""):
            self.checks.append({"ok": bool(ok), "what": what, "detail": detail})
            return bool(ok)

        def send(self, *steps, **kw):
            self.sent.extend(steps)

        def engine_log(self):
            return None

        def quit(self):
            self.quits += 1

    cp.pb.PeerProc = NoPeer
    if port is not None:
        os.environ[cp.PORT_ENV] = port
    else:
        os.environ.pop(cp.PORT_ENV, None)
    g = G()
    cp.run(g)
    os.environ.pop(cp.PORT_ENV, None)
    rows = g.checks
    return {"red": sorted(r["what"].split(":")[0] for r in rows if not r["ok"]),
            "all": sorted(r["what"].split(":")[0] for r in rows), "w0": next((r["detail"] for r in rows
                                                                             if r["what"].startswith("W0:")), None),
            "quits": g.quits, "started": len(started)}


# ================================================================================================ the tests
def _runs(**runs):
    return _child({"runs": runs})["runs"]


def test_both_scenarios_import_and_their_tables_are_their_docstrings():
    t = _child({"tables": True})["tables"]
    solo, wire = t["solo"], t["wire"]
    assert {m: tuple(v["tally"]) for m, v in solo.items()} == {"s156": (8, 12), "plain": (21, 21), "twin": (16, 20),
                                                               "frame": (17, 22)}
    assert {m: tuple(v["tally"]) for m, v in wire.items()} == {"s156": (3, 5), "plain": (9, 9)}
    for m, v in list(solo.items()) + list(wire.items()):
        assert set(v["pred"]) <= set(v["catalog"]), m                  # a predicted red is a scored row
        assert ("K-CAL" in v["catalog"]) == bool(v["pred"]) == ("K-CAL-M" in v["catalog"]), m
    plain = set(solo["plain"]["catalog"])
    assert {"K1", "K2", "GF114-CAL", "TW207-CAL-OFF", "TW207-CAL-MISS", "TW408-CAL-OFF"} <= plain
    assert not {"K1", "K2", "GF114-HOLD", "GF207-TRACK", "GF114-CAL", "TW408-CAL-OFF"} & set(solo["s156"]["catalog"])
    assert solo["s156"]["pred"] == solo["twin"]["pred"] == ["TW207-UP", "TW207-DN", "TW408", "TW408-RET"]
    assert solo["frame"]["pred"] == ["GF114-HOLD", "GF114-TRACK", "GF114-TRACK-DN", "GF207-HOLD", "GF207-TRACK"]
    assert "GF114-CAL" not in solo["frame"]["catalog"] and "TW207-CAL-OFF" not in solo["twin"]["catalog"]
    assert "K-TRIPS" in solo["s156"]["catalog"] and "K-TRIPS" not in t["solo_no_gl"]
    assert t["modes"] == ["plain", "plain", "twin", "frame", "bad", "s156", "s156"]
    assert t["ids"] == {"rig": 3, "model": 5489, "geo": "GEO_MAIN_F0_STN",
                        "twins": [432, 481, 10741, 10743, 10745, 12032, 12034], "alias": [2001, 2002],
                        "release": "[NetSync] harness: selfdress self / gate / law"}
    doc, pdoc = t["doc"], t["peer_doc"]
    for frag in ("8/12", "21/21", "16/20", "17/22", "COOP_CALIBRATE=twin", "COOP_CALIBRATE=frame", "THE ENV-SLOT LAW",
                 "s207-mid-window.png", "s408-arc-window.png", "THE GAME QUIT", "--instance C:\\gd\\ff9-inst\\host",
                 "never --attach", "GhostAs", "PREDICTED_S156", "K-CAL-M"):
        assert frag.lower() in doc.lower(), frag
    for frag in ("9/9", "3/5", "49257", "49201", "--frame none", "P-TAPE", "THE GAME QUIT", "Never `netsync selftest`"):
        assert frag.lower() in pdoc.lower(), frag


def test_the_solo_bench_reads_21_of_21_on_a_correct_s157_model():
    r = _runs(plain={})["plain"]
    assert r["red"] == [], {c: r["detail"][c][:600] for c in r["red"]}
    assert len(r["all"]) == 21 and r["n"] == 21
    d = r["detail"]
    assert "snaps +1 at the re-entry yes" in d["GF114-CAL"] and "the s156 signature while off yes" in d["GF114-CAL"]
    assert "twins +" in d["TW207-UP"] and "the ghost-frame release line x1 yes" in d["K-R"]
    assert "the self-dress release line x1 yes" in d["K-R"] and "both levers held into the reset yes" in d["K-R"]
    assert "judge_twin (must be RED): red" in d["TW207-CAL-MISS"] and "judge_twin (must be RED): red" in d["TW408-CAL-OFF"]
    # the ini: GhostAs '' written once, restored once; the stills through the seams; THE GAME QUIT, and nothing after it
    assert r["ini"] == {"writes": [{"GhostAs": ""}], "restores": 1}
    assert ["sync", "s207-mid-window.png"] in r["grabs"] and ["async", "s408-arc-window.png"] in r["grabs"]
    assert r["shots"] == ["s207-mid", "s408-arc"]
    assert r["quits"] == 1 and r["after_quit"] == []
    assert r["hazard"] == []


def test_the_s156_model_calibrates_automatically_8_of_12_and_never_sends_an_s157_verb():
    r = _runs(s156={"s157": False})["s156"]
    assert set(r["red"]) == {"TW207-UP", "TW207-DN", "TW408", "TW408-RET"}, {c: r["detail"][c][:400] for c in r["red"]}
    assert len(r["all"]) == 12 and "K-CAL" in r["all"]
    assert r["detail"]["K-CAL-M"].count(" SEEN") == 4 and "NOT seen" not in r["detail"]["K-CAL-M"], r["detail"]["K-CAL-M"]
    assert r["hazard"] == []                                          # `bench ghostframe` would be `bench 1` here
    assert not any(s[:3] == ["netsync", "bench", "ghostframe"] or s[:3] == ["netsync", "selfdress", "twin"]
                   for s in r["sent"])
    assert any("THE AUTOMATIC CALIBRATION" in n for n in r["notes"])
    assert "the ghost-frame release line x0 yes" in r["detail"]["K-R"] and r["quits"] == 1


def test_each_lever_calibration_turns_exactly_its_rows_red_by_its_marker():
    r = _runs(twin={"cal": "twin"}, frame={"cal": "frame"})
    tw, fr = r["twin"], r["frame"]
    assert set(tw["red"]) == {"TW207-UP", "TW207-DN", "TW408", "TW408-RET"}, {c: tw["detail"][c][:400] for c in tw["red"]}
    assert set(fr["red"]) == {"GF114-HOLD", "GF114-TRACK", "GF114-TRACK-DN", "GF207-HOLD", "GF207-TRACK"}, \
        {c: fr["detail"][c][:400] for c in fr["red"]}
    assert (len(tw["all"]), len(fr["all"])) == (20, 22)
    for run in (tw, fr):
        assert "NOT seen" not in run["detail"]["K-CAL-M"], run["detail"]["K-CAL-M"]
        assert run["quits"] == 1
    # each lever pulled once, right after K2 (and once more into the reset for the other half), never released mid-run
    assert [s for s in tw["sent"] if s[:3] == ["netsync", "selfdress", "twin"]][0] == ["netsync", "selfdress", "twin", "off"]
    assert [s for s in fr["sent"] if s[:3] == ["netsync", "bench", "ghostframe"]] == [["netsync", "bench", "ghostframe", "off"]]


def test_a_broken_engine_turns_exactly_its_rows_red():
    """A CHECK THAT CANNOT FAIL IS NO CHECK: each broken s157 model (keys published, behaviour wrong) reds its own rows."""
    r = _runs(gf_free={"mutants": ["gf_free"]}, twin_dead={"mutants": ["twin_dead"]},
              ini_unread={"mutants": ["ini_unread"]}, keeps={"mutants": ["release_keeps_twin"]})
    want = {"gf_free": {"GF114-HOLD", "GF114-TRACK", "GF114-TRACK-DN", "GF207-HOLD", "GF207-TRACK", "GF114-CAL",
                        "TW207-UP", "TW207-DN"},
            "twin_dead": {"TW207-UP", "TW207-DN", "TW408", "TW408-RET", "TW207-CAL-MISS"},
            # the ini never read: the mirror is the moogle -- K2's mode, K3D's ghost model, every ghost judge
            "ini_unread": {"K2", "K3D", "GF114-HOLD", "GF114-TRACK", "GF114-TRACK-DN", "GF207-HOLD", "GF207-TRACK",
                           "GF114-CAL", "TW207-UP", "TW207-DN"},
            "keeps": {"K-R"}}
    for name, reds in want.items():
        assert set(r[name]["red"]) == reds, (name, {c: r[name]["detail"][c][:300] for c in set(r[name]["red"]) ^ reds})
        assert r[name]["quits"] == 1


def test_the_bench_restores_the_ini_and_quits_on_every_path():
    r = _runs(no_instance={"instance": False}, raised={"raise_at": 408}, shot={"shot_fault": True},
              attach={"attach": True})
    ni = r["no_instance"]
    assert "K0" in ni["red"] and "refused: no --instance root" in ni["detail"]["K0"]
    assert set(ni["red"]) == set(ni["all"]) and len(ni["all"]) == 21           # every row red: nothing passes unasked
    assert ni["quits"] == 1 and ni["ini"]["writes"] is None
    rs = r["raised"]                    # a bench bug escapes the 408 arrival: the run's handler, then the whole teardown
    assert set(rs["red"]) == {"TW408", "TW408-RET", "TW408-CAL-OFF", "K3D"}, {c: rs["detail"][c][:200] for c in rs["red"]}
    assert "the run FAULTED" in rs["detail"]["TW408"] and "K-R" not in rs["red"]
    assert rs["ini"]["restores"] == 1 and rs["quits"] == 1 and rs["after_quit"] == []
    sh = r["shot"]                      # a bench bug inside a leg (the hang's still): that leg red, recovered
    assert set(sh["red"]) == {"TW207-UP", "GF207-HOLD", "GF207-TRACK"}, {c: sh["detail"][c][:200] for c in sh["red"]}
    assert all("FAULTED (a bench bug)" in sh["detail"][c] for c in sh["red"])
    # the 408 still rides its OWN unjudged hop (a synchronous shot stalls the watch): its fault is a note, TW408 stays green
    assert any("STILL s408-arc FAULTED" in n for n in sh["notes"]), [n for n in sh["notes"] if "408" in n]
    assert sh["held_at_end"] == [] and sh["quits"] == 1 and sh["ini"]["restores"] == 1
    at = r["attach"]
    assert "refused: --attach" in at["detail"]["K0"] and at["quits"] == 0       # never close a game this run did not launch


def test_the_real_driver_over_the_fake_game_detects_the_engine_refuses_and_quits():
    """harness.Session over harness.fakegame.FakeGame (the stand-in's OWN key layout, not this file's model): the live rung
    reads as s157 (the plain catalogs: 21 / 9 rows), the s156 rung as the automatic calibration (12 / 5); with no instance
    root both refuse at their setup with every row red -- and the game process is gone when run(g) returns."""
    f = _child({"fake": [None, "guestlocal"]})["fake"]
    assert (len(f["live"]["solo"]["all"]), len(f["live"]["wire"]["all"])) == (21, 9)
    assert (len(f["guestlocal"]["solo"]["all"]), len(f["guestlocal"]["wire"]["all"])) == (12, 5)
    for cap, runs in f.items():
        for name, r in runs.items():
            assert r["red"] == r["all"] and "no --instance root" in (r["setup"] or ""), (cap, name, r["setup"])
            assert r["alive"] is False, (cap, name)


def test_the_wire_halfs_pure_parts_and_refusals():
    p = _child({"peer": True})["peer"]
    assert p["args"]["base"] == ["--port", "49257", "--offset", "250,0,0", "--status", "5"]
    assert p["args"]["echo"][-4:] == ["--frame", "echo", "--tap", "t.f9tape"]
    assert p["args"]["pin"] == ["--anim", "10539", "--loco", "0", "--frame", "5/12"]
    assert [a[3] for a in p["args"]["guard"]] == ["0", "0", "0", "1"]
    assert p["args"]["seam"][1][-2:] == ["--frame-step", "-1"]
    assert p["parsed"] == [[3, 1], [3, 255], [0, 0], [5, 12], [10, 12], [1, 12], [5, 12], "none"]
    assert p["values"] == {"Enabled": "1", "Role": "host", "RelayUrl": "ws://127.0.0.1:49257", "SessionCode": "ff9-S157PEER",
                           "GhostAs": "", "GuestSlots": "0"}
    assert p["pin_clip"] == "ANH_MAIN_F0_ZDN_LADDER_1_2"
    t = p["tapes"]
    assert t["s157"]["judge"][0] and not t["s157"]["marker"][0] and t["s157"]["f"]["n"] == 5
    assert not t["s156"]["judge"][0] and t["s156"]["marker"][0]
    assert not t["mixed"]["judge"][0] and not t["mixed"]["marker"][0]          # a host that drops the trailer is neither
    assert not t["missing"]["judge"][0] and t["missing"]["f"]["err"]
    s = p["sender"]
    assert s["s157"][0] and not s["stopped"][0] and s["s156_marker"][0] and not s["s157_marker"][0]
    assert not s["unconnected_marker"][0]                                      # no connection is no calibration
    for name, ref in p["refusals"].items():
        assert ref["started"] == 0 and "W0" in ref["red"] and set(ref["red"]) == set(ref["all"]), (name, ref)
        assert ref["quits"] == (0 if name == "attach" else 1), (name, ref)
    assert "owner's bridge" in p["refusals"]["owner_port"]["w0"]
    assert "no --instance root" in p["refusals"]["no_instance"]["w0"]
