"""[ff9mapkit netsync s156] THE GUEST-TRAVERSAL BENCH's REPO HALF -- studies/test-harness/scenarios/coop_guest_traversal.py.

The bench judges R1 (shadow) and R2 (act) of s156 guest traversal by BEHAVIOUR (where the player went, control) and by the
`netsync.guestlocal` block's deltas. These tests pin, offline:

  * its tables are its docstring: the catalog per mode (plain / s155 / the lever calibration), the tallies DERIVED from it
    (28/28, 13/19, 17/30), the predicted sets inside the catalog, the N/A legs dropped and never scored;
  * every pure judge, each with the rows that prove it CAN go red (a climb window is never a stay, a walk is neither, too few
    samples prove nothing, the hold releases only outside the loop's range, a top x/z at the bottom height is no landing, a
    teleport is no climb, a stale or another field's verdict is refused, each marker needs every one of its parts, a late
    release is CONTAMINATED);
  * the whole scenario, run against a POCKET SIMULATOR of the three bench fields and of the s156 gate on a virtual clock
    (:class:`Sim` -- NOT the engine: it models only what the bench observes), reads 28/28 on a correct s156 model, 13/19
    with K-CAL-M + K-CAL green on an s155 model (no key: automatic, no `guestlocal` verb ever sent), 17/30 with K-CAL-M +
    K-CAL green under the held `guestlocal off` lever -- and goes red on EXACTLY the legs a broken gate breaks (the X1 frame
    end, a shadow that acts, a CRC-blind compare, a scene-blind gate, a lever-blind off, a teleport that snaps mid-climb, an
    Async hop tracked on the region's return, a hold that drops the talk at the bench TTL, a flight that ends while control
    is still off, a landing counted as a bail, a no-move end, a 207 mount 5 s late, a teleport that throws at rest, a
    release that forgets the mutate); the selftest's flight-tail mutants (control_only, seq_blind) read 28/28 -- NOT
    PROVEN HERE, pinned: on these rows the Seqs close before control;
  * the two recorded s156 207 act climbs (their real publishes) read green on every part, and no control-on publish of
    theirs carries a Seq;
  * no direction is ever held before a mount (nor by a recovery at the foot), and the bench never sends `netsync talk 2`
    on 114;
  * the log-line twins are the s156 patch's text (RED until the lead captures memoria-patches/s156-*.patch -- by design);
  * INSTALL-GATED: the bench's geometry is the install's .eb (polygons, SetupJump targets, bodies, arming, spawns, the
    landings' walkmesh components) -- read ONLY (both install caches must exist; nothing is built or written).

Every scenario-touching test runs in a CHILD process (the scenario puts its own dir on sys.path -- never this process's).
"""
import json
import math
import os
import pathlib
import subprocess
import sys
import warnings

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCENARIOS = REPO / "studies" / "test-harness" / "scenarios"
TOOLS = REPO / "tools"
KIT = REPO / "ff9mapkit"
HERE = pathlib.Path(__file__).resolve()
PATCH_GLOB = "s156-*.patch"
FPS = 60


# ================================================================================================ the child process
_CHILD = r'''
import importlib.util, json, sys
test_file, scen, tools, kit = sys.argv[1:5]
sys.path.insert(0, tools)
sys.path.insert(0, kit)
spec = importlib.util.spec_from_file_location("gt_bench_test", test_file)
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)
doc = json.loads(sys.stdin.read() or "{}")
print("@@RESULT@@" + json.dumps(T.child_main(doc, scen), default=repr))
'''


def _child(doc: dict, timeout: float = 900.0):
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-c", _CHILD, str(HERE), str(SCENARIOS), str(TOOLS), str(KIT)], env=env,
                         input=json.dumps(doc), capture_output=True, text=True, timeout=timeout)
    assert out.returncode == 0, (out.stdout[-2000:], out.stderr[-4000:])
    line = [ln for ln in out.stdout.splitlines() if ln.startswith("@@RESULT@@")][-1]
    return json.loads(line[len("@@RESULT@@"):])


def _load_scenario(scen: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location("coop_guest_traversal", os.path.join(scen, "coop_guest_traversal.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def child_main(doc: dict, scen: str):
    """Runs INSIDE the child: ``doc["calls"]`` -- the scenario's functions on JSON args; ``doc["runs"]`` -- whole sim runs."""
    gt = _load_scenario(scen)
    out = {}
    if "calls" in doc:
        res = []
        for c in doc["calls"]:
            fn = getattr(gt, c["fn"])
            val = fn(*c.get("args", []), **c.get("kwargs", {})) if callable(fn) else fn
            res.append(val)
        out["calls"] = res
    if "eval" in doc:
        ns = dict(globals())
        ns.update({"gt": gt, "cb": gt.cb, **(doc.get("vars") or {})})
        out["eval"] = {k: eval(expr, ns) for k, expr in doc["eval"].items()}     # noqa: S307 - test-authored exprs
    if "runs" in doc:
        out["runs"] = {name: sim_run(gt, **spec) for name, spec in doc["runs"].items()}
    return out


# ================================================================================================ the pocket simulator
class VClock:
    """A virtual wall clock: ``sleep`` advances it; the scenario's and _coop_battle's `time` are this object."""

    def __init__(self):
        self.t = 10000.0

    def time(self):
        return self.t

    def sleep(self, s):
        self.t += max(0.0, float(s))

    monotonic = perf_counter = time


SIM_TABLE = {"rows": 84, "funcs": 199, "fields": 37, "table_crc": "0xabdefff3"}
SPAWN_Y = {114: 0.0, 207: -12.0, 408: 2.0}
LADDER_Y = {114: (0.0, -1030.0), 207: (-12.0, -477.0)}            # (bottom floor, top floor)
HASHED = {(114, 9): 746, (207, 10): 839, (207, 11): 839, (408, 4): 228, (408, 5): 236}
TTL_FRAMES = 240                                                    # TalkRelayTtlMs 4000 at 60 fps


class Sim:
    """A POCKET MODEL of fields 114 / 408 / 207 and of the s155 / s156 field gate, as the bench OBSERVES them -- never the
    engine. A Confirm KeyOn inside a press region (at its height) starts the stock climb / hop, unless the player is a
    spectator (selftest role + bench 1): then s155 declines (F1's latched line) and s156 runs the CONTRACT's VerdictRule
    (off, unverified, in_flight, host_scene, shadow, allow; every verdict counted, `last` rewritten but for lever_off).
    A climb mounts, HANGS with no key, steps 20 u per 2 frames on a held up/down, exits past the .eb's bound and lands; a
    hop arcs 40 frames. s156 flights end on FlightRule (D6: control back, the body's frame done, no Seq running -- 207's
    two Seqs run over its mount and its dismount and close BEFORE the body lands, as measured in game); the bench talk
    lane, its 4 s TTL, the deferral, the climb-scoped hold (D8b) and teleport-to-host are modelled; trip wires are not
    (they never trip on these rows). ``mutants`` break one rule each, so a test can show which legs the bench turns red
    (or, for the selftest's flight-tail mutants, that no leg here can)."""

    def __init__(self, clock: VClock, gt, *, engine: str = "s156", mutants=(), offset=(250, 0), dressed=False,
                 log_path=None):
        self.clock, self.gt, self.engine, self.mut = clock, gt, engine, set(mutants)
        self.t0 = clock.t
        self.frame = 0
        self.offset = offset
        self.log_path = pathlib.Path(log_path)
        self.log_path.write_text("", encoding="utf-8")
        self.ui, self.field, self.scenario = "Title", -1, 0
        self.pos = [0.0, 0.0, 0.0]
        self.floor = "bottom"
        self.ctl = False
        self.ctl_at = None
        self.dialog = False
        self.env_slot = {13: 0, 14: 0}       # THE ENV-SLOT LAW: 114 leaves slot 1 (Byte[14]) playing (2)
        self.keys = {}                       # button -> [start, end) frames
        self.motion = None
        self.selftest = self.forced = self.bench = False
        self.lock = self.hostscene = self.host_open = False
        self.scene_nonce = 0
        self.dressed = dressed
        self.proof_done = False
        self.last_decline_place = None
        # the s156 gate
        self.lever, self.mut_armed, self.mut_index, self.mut_spent, self.mut_hit, self.mut_hashed = None, False, -1, False, False, 0
        self.verdicts = {n: 0 for n in gt.VERDICT_NAMES}
        self.last = {"seq": 0, "field": -1, "entry": -1, "verdict": None, "reason": None, "kind": None, "hashed": 0,
                     "age_ms": -1}
        self.c = {k: 0 for k in ("climbs", "ended", "bailed", "aborted", "long_climbs", "boots_mid_climb", "tp_calls",
                                 "tp_refusals", "talk_queued", "talk_held", "talk_applied_after_climb", "talk_expired")}
        self.armed = False
        self.flight = None
        self.line_latch = set()
        self.l9_done = False
        self.end_frame = None
        self.seq_frames = self.seq_ctl_frames = 0     # armed frames with a Seq running / with it AND control on
        # the talk relay + teleport
        self.pending = None
        self.talk_nonce = 0
        self.defer_nonce, self.last_nonce = -1, -1
        self.held_slot = None
        self.tp_reason = ""
        self.gl_calls = []
        # NetSyncClient's config line prints the offset only when it is not 250,0 (NetSyncClient.cs ~:1192)
        self.log("[NetSync] config enabled=False role=off field=0"
                 + (f" selfTestOffset={offset[0]},{offset[1]}" if tuple(offset) != (250, 0) else "")
                 + " peer=127.0.0.1:49201")

    # -- plumbing ---------------------------------------------------------------------------------------------
    def log(self, msg: str) -> None:
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(f"f{self.frame:07d}|M| {msg}\n")

    def sync(self) -> None:
        target = int((self.clock.t - self.t0) * FPS)
        while self.frame < target:
            self.step()

    def held_now(self, b: str, frame=None) -> bool:
        f = self.frame if frame is None else frame
        k = self.keys.get(b)
        return k is not None and k[0] <= f < k[1]

    def key(self, b: str, frames: int) -> None:
        k = self.keys.get(b)
        if k is not None and k[0] <= self.frame < k[1]:
            self.keys[b] = [k[0], max(k[1], self.frame + 1 + int(frames))]      # Extend, never a hole
        else:
            self.keys[b] = [self.frame + 1, self.frame + 1 + int(frames)]

    def release(self, b: str) -> None:
        k = self.keys.get(b)
        if k is not None and k[0] <= self.frame < k[1]:
            k[1] = self.frame + 1

    # -- the frame -------------------------------------------------------------------------------------------
    def step(self) -> None:
        k = self.keys.get("confirm")
        if k is not None and k[0] == self.frame:
            self.on_confirm()
        if self.ctl_at is not None and self.frame >= self.ctl_at:
            self.ctl, self.ctl_at = True, None
        self.motion_step()
        if self.engine == "s156" and self.armed:
            self.flight_step()
        self.talk_step()
        self.frame += 1

    def in_region(self, entry: int) -> bool:
        poly = self.gt.GEOM[self.field]["regions"][entry]
        return self.gt.in_quad(self.pos[0], self.pos[2], poly)

    def press_target(self):
        f, y = self.field, self.pos[1]
        if f == 114 and self.in_region(9):
            return "ladder", 9, ("up" if y > -398 else "down")
        if f == 207:
            if self.floor == "bottom" and self.in_region(11):
                return "ladder", 11, "up"
            if self.floor == "top" and self.in_region(10):
                return "ladder", 10, "down"
        if f == 408:
            if self.in_region(4) and y > -260:
                return "hop", 4, "out"
            if self.in_region(5) and -480 < y < -400:
                return "hop", 5, "ret"
        return None

    def on_confirm(self) -> None:
        if self.dialog:
            self.dialog = False
            self.ctl_at = self.frame + 2
            return
        if not self.ctl or self.ui != "FieldHUD":
            return
        tgt = self.press_target()
        if tgt is None:
            return
        kind, entry, way = tgt
        if self.selftest and self.bench:
            if self.engine == "s156" and self.gate(kind, entry, way):
                return
            if self.last_decline_place != self.field:
                self.last_decline_place = self.field
                if "silent_decline" not in self.mut:
                    self.log(self.gt.DECLINE_LINE.format(f=self.field))
            return
        self.start_motion(kind, way)

    def start_motion(self, kind: str, way: str) -> None:
        self.ctl = False
        if kind == "ladder":
            spec = self.gt.LADDERS[self.field]
            self.motion = {"kind": "ladder", "phase": "mount", "t": 8, "spec": spec, "way": way}
            if "slow_mount" in self.mut and self.field == 207 and self.selftest and self.bench:
                self.motion["t"] = 300                    # a wrong engine: the guest's mount lands 5 s after the press
        else:
            hop = self.gt.HOPS[way]
            self.motion = {"kind": "hop", "t": 40, "n": 40, "from": list(self.pos), "to": list(hop["land"]), "way": way}

    def motion_step(self) -> None:
        m = self.motion
        if m is None:
            return
        if m["kind"] == "hop":
            m["t"] -= 1
            a = 1.0 - m["t"] / m["n"]
            self.pos = [m["from"][i] + (m["to"][i] - m["from"][i]) * a for i in range(3)]
            self.pos[1] -= 120.0 * math.sin(math.pi * a)                        # the arc (y negative up)
            if m["t"] <= 0:
                self.pos = list(m["to"])
                self.floor = "shelf" if m["way"] == "out" else "ground"
                self.motion, self.ctl = None, True
            return
        spec = m["spec"]
        if m["phase"] == "mount":                                               # SetupJump: lands at the triple
            m["t"] -= 1
            if m["t"] <= 0:
                self.pos = list(spec["mount_bottom"] if m["way"] == "up" else spec["mount_top"])
                m["phase"] = "loop"
            return
        if m["phase"] == "loop":
            if self.frame % 2 == 0:
                y = self.pos[1]
                if self.held_now("up"):
                    y -= 20.0
                elif self.held_now("down"):
                    y += 20.0
                a = (spec["hi"] - y) / float(spec["hi"] - spec["lo"])
                mb, mt = spec["mount_bottom"], spec["mount_top"]
                self.pos = [mb[0] + (mt[0] - mb[0]) * a, y, mb[2] + (mt[2] - mb[2]) * a]
                if y < spec["lo"]:
                    m.update(phase="exit", t=10, to=list(spec["land_top"]), floor="top", frm=list(self.pos))
                elif y > spec["hi"]:
                    m.update(phase="exit", t=10, to=list(spec["land_bottom"]), floor="bottom", frm=list(self.pos))
            return
        m["t"] -= 1
        a = 1.0 - m["t"] / 10.0
        self.pos = [m["frm"][i] + (m["to"][i] - m["frm"][i]) * a for i in range(3)]
        if m["t"] <= 0:
            self.pos = list(m["to"])
            self.floor = m["floor"]
            self.motion, self.ctl = None, True

    # -- the s156 gate ------------------------------------------------------------------------------------------
    def gate(self, kind: str, entry: int, way: str) -> bool:
        gt = self.gt
        mode = self.lever if (self.lever and self.selftest) else "act"
        if "lever_blind" in self.mut and mode == "off":
            mode = "act"
        if mode == "off":
            self.verdicts["lever_off"] += 1
            return False
        reason = None
        bytes_ok = True
        if self.mut_armed and "crc_blind" not in self.mut:
            hashed = HASHED[(self.field, entry)]
            self.mut_armed, self.mut_spent, self.mut_hashed = False, True, hashed
            self.mut_hit = self.mut_index < hashed
            if self.mut_hit:
                bytes_ok = False
                reason = (gt.REASON_MUTATE.format(n=self.mut_index) + f"entry {entry} tag 3 (region): crc 0x0badf00d, "
                          "want 0xf4e530de")
        host = self.hostscene and self.lock and "scene_blind" not in self.mut
        if not bytes_ok:
            v = "unverified"
        elif self.armed:
            v, reason = "in_flight", f"a guest climb is already in flight (field {self.field} entry {self.flight['entry']})"
        elif host:
            v, reason = "host_scene", gt.REASON_HOST_SCENE
        elif mode == "shadow" and "shadow_acts" not in self.mut:
            v = "shadow"
        else:
            v = "allow"
        self.verdicts[v] += 1
        kname = "jump" if kind == "hop" else "ladder"
        self.last = {"seq": self.last["seq"] + 1, "field": self.field, "entry": entry, "verdict": v, "reason": reason,
                     "kind": kname, "hashed": HASHED[(self.field, entry)], "age_ms": 0}
        if v == "allow":
            self.armed = True
            self.l9_done = False
            self.c["climbs"] += 1
            self.flight = {"field": self.field, "entry": entry, "kind": kname, "region_uid": entry, "body_uid": 250,
                           "f0": self.frame, "seen_off": False, "body_open": True, "body_ran": True, "seq_open": False}
            self.log(gt.GL_STARTED.format(f=self.field, e=entry, kind=kname, h=HASHED[(self.field, entry)], u=250))
            self.start_motion(kind, way)
            return True
        if (entry, v) not in self.line_latch:
            self.line_latch.add((entry, v))
            if v == "shadow":
                self.log(gt.GL_SHADOW.format(f=self.field, e=entry, kind=kname, h=HASHED[(self.field, entry)]))
            else:
                self.log(gt.GL_DECLINED.format(f=self.field, e=entry, kind=kname, reason=reason))
        return False

    def flight_step(self) -> None:
        fl, m = self.flight, self.motion
        fl["seen_off"] = fl["seen_off"] or not self.ctl
        fl["body_open"] = m is not None
        # 207's Seqs (entries 3 / 4: e15 t50's RunSharedScript pitch ramps) run over the mount and the dismount and close a
        # few frames BEFORE the body lands -- in game seq_open fell 4-8 frames before control on every recorded act climb
        fl["seq_open"] = (self.field == 207 and m is not None and m["kind"] == "ladder"
                          and (m["phase"] == "mount" or (m["phase"] == "exit" and m["t"] > 3)))
        self.seq_frames += fl["seq_open"]
        self.seq_ctl_frames += fl["seq_open"] and self.ctl
        if "ends_at_bound" in self.mut and m is not None and ((m["kind"] == "ladder" and m["phase"] == "exit")
                                                               or (m["kind"] == "hop" and m["t"] <= 12)):
            self.end_flight()                         # ended at the loop's bound / before the hop lands: control still OFF
            return
        if "async_blind" in self.mut and fl["kind"] == "jump" and self.frame - fl["f0"] >= 2:
            done = True                                                     # tracked on the region's return
        elif "control_only" in self.mut:
            done = self.ctl                           # the selftest's mutant.flight.control_only (no bail on these rows)
        elif "seq_blind" in self.mut:
            done = self.ctl and m is None             # the selftest's mutant.flight.seq_blind
        else:
            done = self.ctl and m is None and not fl["seq_open"]            # FlightRule's Landed
        if done and "x1" in self.mut and self.field in self.gt.GEOM:
            regions = self.gt.GEOM[self.field]["regions"]
            if any(self.gt.in_quad(self.pos[0], self.pos[2], p) for p in regions.values()):
                done = False                                                # the tag-2 tread re-pushes the frame
        if done:
            self.end_flight()

    def end_flight(self) -> None:
        """NetSyncGuestLocal.End: ended +1 (bailed +1 on a bail) and the L3 line, with End's suffix where it applies."""
        fl = self.flight
        bail = "bails_flag" in self.mut                                     # a normal landing counted as a bail
        self.armed = False
        self.c["ended"] += 1
        self.c["bailed"] += bail
        self.end_frame = self.frame
        sfx = self.gt.GL_ENDED_BAILED if bail else self.gt.GL_ENDED_NO_MOVE if "no_move_line" in self.mut else ""
        self.log(self.gt.GL_ENDED.format(f=self.field, e=fl["entry"], kind=fl["kind"],
                                         ms=int((self.frame - fl["f0"]) * 1000 / FPS)) + sfx)

    # -- the talk relay (the bench lane) -----------------------------------------------------------------------
    def talk_step(self) -> None:
        if not (self.selftest and self.bench):
            return
        gt = self.gt
        if self.pending is not None and self.frame - self.pending["since"] >= TTL_FRAMES:
            self.pending = None
        body = self.pending
        if self.engine == "s156":
            body = self.talk_lane(body)
        if self.defer_nonce >= 0 and (body is None or body["nonce"] != self.defer_nonce):
            self.log(gt.TALK_EXPIRED.format(n=self.defer_nonce))
            self.defer_nonce = -1
        if body is None:
            return
        if body["nonce"] == self.last_nonce:
            self.pending = None
            return
        if body["field"] != self.field:
            self.pending = None
            return
        if not self.ctl:
            r, why = 0, gt.TALK_DEFER_CONTROL
        elif self.engine == "s156" and self.armed:
            r, why = 0, gt.TALK_TAIL_WHY
        else:
            r, why = 1, ""
        if r == 0:
            if self.defer_nonce != body["nonce"]:
                self.log(gt.TALK_DEFERRED.format(n=body["nonce"], u=body["uid"], why=why))
            self.defer_nonce = body["nonce"]
            if self.engine == "s156":
                self.hold_talk(body)
            return
        self.log(gt.TALK_STARTED.format(u=body["uid"], f=self.field))
        self.dialog, self.ctl = True, False
        if self.engine == "s156":
            self.note_talk_result(body["nonce"], r)
        self.last_nonce, self.defer_nonce, self.pending = body["nonce"], -1, None

    def hold_talk(self, body) -> None:
        if not self.armed or "no_retention" in self.mut:
            return
        hs = self.held_slot
        if hs is not None and hs["body"]["nonce"] == body["nonce"]:
            return
        if hs is not None:
            self.drop_held("a newer relayed start replaced it")
        self.held_slot = {"body": dict(body), "scene": self.scene_nonce if self.hostscene else -1, "field": self.field,
                          "f": self.frame}
        self.c["talk_held"] += 1
        self.log(self.gt.GL_TALK_HELD.format(n=body["nonce"], u=body["uid"]))

    def drop_held(self, why: str) -> None:
        self.log(self.gt.GL_TALK_DROPPED.format(n=self.held_slot["body"]["nonce"], why=why))
        self.c["talk_expired"] += 1
        self.held_slot = None

    def talk_lane(self, body):
        hs = self.held_slot
        if hs is None:
            return body
        nonce = hs["body"]["nonce"]
        lane_held = body is not None and body["nonce"] == nonce
        lane_newer = body is not None and not lane_held
        scene_up = self.hostscene
        same_scene = hs["scene"] >= 0 and scene_up and self.scene_nonce == hs["scene"]
        since_end = -1 if self.armed else int((self.frame - (self.end_frame or self.frame)) * 1000 / FPS)
        if lane_held:
            return body
        if lane_newer:
            self.drop_held("a newer relayed start replaced it")
        elif hs["field"] != self.field:
            self.drop_held("the field changed")
        elif not scene_up or not same_scene:
            self.drop_held("the host's scene changed or ended")
        elif not self.armed and since_end >= 4000:
            self.drop_held(f"its TTL ran out after my climb ended ({since_end} ms)")
        else:
            return dict(hs["body"])
        return body

    def note_talk_result(self, nonce: int, r: int) -> None:
        hs = self.held_slot
        if hs is None or hs["body"]["nonce"] != nonce:
            return
        if r > 0:
            self.c["talk_applied_after_climb"] += 1
            self.log(self.gt.GL_TALK_APPLIED.format(n=nonce, ms=int((self.frame - hs["f"]) * 1000 / FPS)))
            self.held_slot = None
        else:
            self.drop_held("declined on my copy (no such object or handler)")

    # -- the verbs --------------------------------------------------------------------------------------------
    def netsync(self, sub: str, args: list) -> None:
        from harness import HarnessError
        a = [str(x) for x in args]
        if sub == "selftest":
            self.selftest = self.forced = a[:1] == ["1"]
            if self.selftest and self.engine == "s156" and not self.proof_done:
                self.proof_done = True
                t = SIM_TABLE
                self.log(f"[NetSync] guest traversal selftest: OK (131 rows, 33 mutants caught, {t['rows']} table rows / "
                         f"{t['funcs']} functions, table crc {t['table_crc']})")
            return
        if sub == "bench":
            self.bench = a[:1] == ["1"]
            return
        if sub == "talk":
            if not (self.selftest and self.bench):
                raise HarnessError("netsync talk: the field-gate bench is OFF (netsync bench 1)")
            self.talk_nonce += 1
            self.pending = {"field": self.field, "uid": int(a[0]), "nonce": self.talk_nonce, "since": self.frame}
            self.log(f"[NetSync] talk bench: fabricated SectionTalk obj {a[0]} field {self.field} nonce "
                     f"{self.talk_nonce} -- applying")
            return
        if sub == "hostscene":
            on = a[:1] == ["1"]
            if on and not self.hostscene:
                self.scene_nonce += 1
            self.hostscene = on
            return
        if sub == "lock":
            self.lock = a[:1] == ["1"]
            return
        if sub == "host":
            self.host_open = a[:1] == ["open"]
            return
        if sub == "selfdress":
            if a[:2] == ["self", "off"]:
                self.dressed = False
            return
        if sub == "guestlocal":
            self.gl_calls.append(list(a))
            if self.engine != "s156":
                raise HarnessError("netsync: unknown sub-verb 'guestlocal' (selftest|bench|...|selfdress)")
            return self.guestlocal(a)
        raise HarnessError(f"netsync: unknown sub-verb {sub!r}")

    def guestlocal(self, a: list) -> None:
        from harness import HarnessError
        gt = self.gt
        if not self.selftest:
            raise HarnessError("netsync guestlocal: needs the selftest role (netsync selftest 1)")
        op = a[0] if a else ""
        if op in ("act", "shadow", "off") and len(a) == 1:
            self.lever = op
            self.log({"act": gt.GL_LEVER_ACT, "shadow": gt.GL_LEVER_SHADOW, "off": gt.GL_LEVER_OFF}[op])
        elif op == "mutate" and len(a) == 2 and a[1].isdigit() and 0 <= int(a[1]) <= 65535:
            self.mut_armed, self.mut_index, self.mut_spent, self.mut_hit = True, int(a[1]), False, False
            self.log(gt.GL_LEVER_MUTATE.format(n=int(a[1])))
        elif op == "clear" and len(a) == 1:
            self.lever, self.mut_armed, self.mut_index = None, False, -1
            self.line_latch = set()
            self.log(gt.GL_LEVER_CLEAR)
        elif op == "teleport" and len(a) == 1:
            self.c["tp_calls"] += 1
            self.teleport()
        else:
            raise HarnessError("netsync guestlocal: expected act|shadow|off|mutate <0-65535>|clear|teleport")

    def tp_decline(self, reason: str) -> None:
        if self.tp_reason == reason:
            return
        self.tp_reason = reason
        self.log(self.gt.TP_DECLINE.format(reason=reason))

    def teleport(self) -> None:
        gt = self.gt
        if self.armed and "tp_snaps" not in self.mut:
            self.c["tp_refusals"] += 1
            if not self.l9_done:
                self.l9_done = True
                self.log(gt.GL_TP_REFUSED.format(f=self.field, e=self.flight["entry"]))
            self.tp_decline(gt.TP_REASON_CLIMB)
            return
        if not self.ctl and not self.armed:
            self.tp_decline("user control is off (dialogue/event/transition)")
            return
        if "tp_throws" in self.mut:                   # the snap moved the body, then the call threw: the catch logs only
            self.pos[0] += self.offset[0]             # (NetSyncClient.TeleportToHostImpl's Log.Error text, not the bench's)
            self.pos[2] += self.offset[1]
            self.log("[NetSync] teleport-to-host failed -- System.NullReferenceException")
            return
        self.pos[0] += self.offset[0]
        self.pos[2] += self.offset[1]
        self.tp_reason = ""
        self.log(gt.TP_SNAPPED)

    def reset(self) -> None:
        if self.engine == "s156" and (self.lever is not None or self.mut_armed):
            self.log(self.gt.GL_RELEASE)
        self.lever, self.mut_armed = None, self.mut_armed and "release_keeps_mutate" in self.mut
        self.line_latch = set()
        self.selftest = self.forced = self.bench = self.lock = self.hostscene = self.host_open = False
        self.pending = None

    def newgame(self) -> None:
        self.ui, self.field, self.ctl = "FieldHUD", 70, False
        self.pos = [0.0, 0.0, 0.0]

    def warp(self, fid: int, scenario=None) -> None:
        if self.armed:
            self.armed = False
            self.c["aborted"] += 1
        self.field, self.ui = int(fid), "FieldHUD"
        if scenario is not None and scenario >= 0:
            self.scenario = scenario
        sx, sz = self.gt.GEOM[fid]["spawn"]
        self.pos = [float(sx), SPAWN_Y[fid], float(sz)]
        self.floor = "ground" if fid == 408 else "bottom"
        self.motion, self.dialog, self.ctl = None, False, False
        self.ctl_at = self.frame + 20
        if fid in (408, 207) and 2 in self.env_slot.values():
            self.dialog, self.ctl_at = True, None        # "Error Env Play() / Slot=N" + WaitWindow: control never comes
        if fid == 114:
            self.env_slot[14] = 2
        self.line_latch = set()

    def route(self, x: float, z: float) -> bool:
        f = self.field
        if f in self.gt.LADDERS:
            spec = self.gt.LADDERS[f]
            near_top = self.gt.dist_xz((x, z), spec["stand_top"]) <= 80
            if (self.floor == "top") != near_top:
                return False
            self.pos = [float(x), LADDER_Y[f][1] if self.floor == "top" else LADDER_Y[f][0], float(z)]
            return True
        if f == 408:
            on_shelf = self.gt.dist_xz((x, z), self.gt.HOPS["ret"]["stand"]) <= 80
            if (self.floor == "shelf") != on_shelf:
                return False
            ledge = self.gt.in_quad(x, z, self.gt.GEOM[408]["regions"][4])
            self.pos = [float(x), -436.0 if on_shelf else (-249.0 if ledge else 2.0), float(z)]
            return True
        return False

    # -- the published document ---------------------------------------------------------------------------------
    def doc(self) -> dict:
        body = 8 if self.field == 114 else 98
        held = [b.capitalize() for b in ("up", "down", "left", "right") if self.held_now(b)]
        ns = {"enabled": False, "role": "selftest" if self.selftest else "off", "selftest": self.selftest,
              "forced": self.forced, "bench": self.bench, "lock_engaged": self.lock,
              "host_flags": (0x01 if self.hostscene else 0) | (0x04 if self.host_open else 0) | 0x08,
              "dress": {"self": {"armed": bool(self.dressed)}}}
        if self.engine == "s156":
            fl = self.flight if self.armed else None
            ns["guestlocal"] = {
                "mode": (self.lever if (self.lever and self.selftest) else "act"), "lever": self.lever,
                "rows": SIM_TABLE["rows"], "funcs": SIM_TABLE["funcs"], "table_crc": SIM_TABLE["table_crc"],
                "selftest": "ok" if self.proof_done else None, "last": dict(self.last), "verdicts": dict(self.verdicts),
                "in_flight": self.armed,
                "flight": ({k: fl[k] for k in ("field", "entry", "kind", "region_uid", "body_uid", "seen_off",
                                               "body_open", "body_ran", "seq_open")} | {"age_ms": 0}) if fl else
                {"field": -1, "entry": -1, "kind": None, "region_uid": -1, "body_uid": -1, "age_ms": -1,
                 "seen_off": False, "body_open": False, "body_ran": False, "seq_open": False},
                **{k: self.c[k] for k in ("climbs", "ended", "bailed", "aborted")}, "abort_why": None,
                "long_climbs": 0, "boots_mid_climb": 0, "trips": {"total": 0, "op": 0, "glob": 0, "last": None},
                "tp_calls": self.c["tp_calls"], "tp_refusals": self.c["tp_refusals"],
                "tp_last": "ok" if self.tp_reason == "" else self.tp_reason,
                **{k: self.c[k] for k in ("talk_queued", "talk_held", "talk_applied_after_climb", "talk_expired")},
                "mutate": {"armed": self.mut_armed, "index": self.mut_index, "spent": self.mut_spent, "hit": self.mut_hit,
                           "hashed": self.mut_hashed}}
        return {"frame": self.frame, "ui_state": self.ui, "fading": False, "scenario": self.scenario,
                "field": {"id": self.field}, "held": held,
                "player": {"x": round(self.pos[0], 2), "y": round(-self.pos[1], 2), "z": round(self.pos[2], 2),   # the ENGINE's y
                           "control": self.ctl, "model": body},
                "dialog": {"open": self.dialog, "texts": ["..."] if self.dialog else []}, "netsync": ns}


class SimSession:
    """The Session surface the bench uses, over :class:`Sim` and a :class:`VClock`."""
    NETSYNC_SUBVERBS = None                  # cb.ns_verb: always through netsync()

    def __init__(self, sim: Sim, clock: VClock, tmp: pathlib.Path):
        self.sim, self.clock = sim, clock
        self.attach = False
        self.game_path = tmp / "game"
        self.run_dir = tmp / "run"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.scenario_dir = None
        self.checks, self.notes, self.sent, self.holds = [], [], [], []

    @property
    def state(self):
        from harness.channel import State
        self.sim.sync()
        self.clock.sleep(1.0 / 240)
        return State(self.sim.doc(), read_at=self.clock.t)

    def wait_for(self, predicate, *, timeout: float = 20.0, what: str = "condition"):
        from harness import HarnessError
        deadline = self.clock.t + timeout
        while True:
            st = self.state
            if predicate(st):
                return st
            if self.clock.t >= deadline:
                raise HarnessError(f"timed out after {timeout}s waiting for {what}")
            self.clock.sleep(1.0 / FPS)

    def _frames(self, n: int) -> None:
        self.clock.sleep(n / FPS)
        self.sim.sync()

    def press(self, button: str, frames: int = 2) -> None:
        self.sent.append(("press", button, frames))
        self.sim.key(button, frames)
        self._frames(int(frames) + 2)

    def hold(self, button: str, frames: int) -> None:
        self.sim.sync()
        m = self.sim.motion
        self.holds.append({"button": button, "frame": self.sim.frame, "control": self.sim.ctl,
                           "phase": None if m is None else m.get("phase", m["kind"])})
        self.sent.append(("hold", button, frames))
        self.sim.key(button, frames)
        self._frames(1)

    def release(self, button: str) -> None:
        self.sim.sync()
        self.sim.release(button)
        self._frames(1)

    def wait_frames(self, frames: int) -> None:
        self._frames(int(frames))

    def send(self, *steps, wait: bool = True, timeout: float = 60.0) -> None:
        from harness import HarnessError
        for step in steps:
            self.sent.append(("send", step))
            parts = step.split()
            if parts[0] == "reset":
                self.sim.reset()
            elif parts[0] == "wait":
                self._frames(int(parts[1]))
            elif parts[0] == "netsync":
                self.netsync(parts[1], *parts[2:])
            else:
                raise HarnessError(f"sim: unknown step {step!r}")
        self._frames(2)

    def netsync(self, sub: str, *args, timeout: float = 20.0):
        self.sent.append(("netsync", sub) + tuple(str(a) for a in args))
        self.sim.sync()
        self.sim.netsync(sub, list(args))
        self._frames(2)
        return self.state

    def newgame(self, **_):
        self.sim.newgame()
        self._frames(60)
        return self.state

    def warp(self, field: int, *, entrance=None, scenario=None, timeout: float = 60.0, **_):
        self.sent.append(("warp", int(field), entrance, scenario))
        self.sim.sync()
        self.sim.warp(int(field), scenario)
        return self.wait_for(lambda s: s.field_id == int(field) and s.control, timeout=timeout, what="the warp")

    def no_encounters(self, on: bool = True) -> None:
        self.sent.append(("noencounter", on))

    def poke(self, index: int, value: int) -> None:
        self.sent.append(("byte", int(index), int(value)))
        if int(index) in self.sim.env_slot and "env_poke_ignored" not in self.sim.mut:
            self.sim.env_slot[int(index)] = int(value)

    def route_to(self, x: float, z: float, *, avoid=(), tolerance: float = 45.0, **_) -> dict:
        from harness import HarnessError
        self.sim.sync()
        self.sent.append(("route", round(x), round(z)))
        if not self.sim.ctl or not self.sim.route(x, z):
            raise HarnessError(f"sim: no route to ({x:.0f}, {z:.0f}) from {self.sim.pos} ({self.sim.floor})")
        self._frames(60)
        return {"reached": True}

    def settle(self, *, timeout=None):
        return self.state

    def engine_log(self):
        return self.sim.log_path

    def note(self, text: str) -> None:
        self.notes.append(str(text))

    def check(self, ok, description: str, detail: str = "") -> bool:
        self.checks.append({"ok": bool(ok), "what": description, "detail": str(detail)})
        return bool(ok)


def sim_run(gt, *, engine: str = "s156", mutants=(), cal: bool = False, offset=(250, 0), dressed=False,
            attach=False) -> dict:
    """One whole bench run on the pocket simulator (in the child). Returns the ledger's reds/greens, details, the notes,
    the verbs sent, the holds, the guestlocal verbs the sim saw and the sim's log."""
    import tempfile
    clock = VClock()
    gt.time = clock
    gt.cb.time = clock
    gt.cb.CALIBRATE = bool(cal)
    gt.kit_table = lambda: (dict(SIM_TABLE), "the sim's table")
    tmp = pathlib.Path(tempfile.mkdtemp())
    sim = Sim(clock, gt, engine=engine, mutants=mutants, offset=tuple(offset), dressed=dressed,
              log_path=tmp / "Memoria.log")
    g = SimSession(sim, clock, tmp)
    g.attach = attach
    gt.run(g)
    rows = g.checks
    return {"red": sorted(r["what"].split(":")[0] for r in rows if not r["ok"]),
            "all": sorted({r["what"].split(":")[0] for r in rows}),
            "detail": {r["what"].split(":")[0]: r["detail"] for r in rows},
            "n": len(rows), "notes": g.notes, "sent": [list(s) for s in g.sent], "holds": g.holds,
            "gl_calls": sim.gl_calls, "log": sim.log_path.read_text(encoding="utf-8").splitlines(),
            "seq": {"frames": sim.seq_frames, "with_control": sim.seq_ctl_frames},
            "virtual_s": round(clock.t - 10000.0, 1)}


# ================================================================================================ child-side helpers
def _iq_rows(gt):
    """(field, entry, mismatches vs the kit's region_contains on a 10 u grid, points inside) per bench polygon."""
    from ff9mapkit.content.doorface import region_contains
    rows = []
    for f, G in gt.GEOM.items():
        for e, poly in list(G["regions"].items()) + list(G["gateways"].items()):
            xs, zs = [q[0] for q in poly], [q[1] for q in poly]
            mism = inside = 0
            for x in range(min(xs) - 20, max(xs) + 21, 10):
                for z in range(min(zs) - 20, max(zs) + 21, 10):
                    a = gt.in_quad(x, z, poly)
                    mism += a != region_contains(x, z, poly)
                    inside += a
            rows.append((f, e, mism, inside))
    return rows


def _stand_rows(gt):
    L, H, R = gt.LADDERS, gt.HOPS, {f: G["regions"] for f, G in gt.GEOM.items()}

    def xz(p):
        return (p[0], p[2]) if len(p) == 3 else tuple(p)
    return [gt.in_quad(*xz(L[114]["stand_bottom"]), R[114][9]), gt.in_quad(*xz(L[114]["stand_top"]), R[114][9]),
            gt.in_quad(*xz(L[114]["land_bottom"]), R[114][9]), gt.in_quad(*xz(L[207]["stand_bottom"]), R[207][11]),
            gt.in_quad(*xz(L[207]["land_bottom"]), R[207][11]), gt.in_quad(*xz(L[207]["land_top"]), R[207][10]),
            gt.in_quad(*xz(H["out"]["stand"]), R[408][4]), gt.in_quad(*xz(H["out"]["land"]), R[408][5]),
            gt.in_quad(*xz(H["ret"]["land"]), R[408][4]),
            gt.in_quad(*gt.GEOM[114]["spawn"], gt.GEOM[114]["gateways"][8]),
            gt.in_quad(0, 0, [(0, 0), (10, 0)]), gt.in_quad(5, 5, [(0, 0), (10, 0), (20, 0)])]


def _crossed_rows(gt):
    out = []
    for f, sp in gt.LADDERS.items():
        for d in ("up", "down"):
            inside = sum(gt.crossed(y, sp, d) for y in range(int(sp["lo"]), int(sp["hi"]) + 1))
            out.append((f, d, inside, gt.crossed(sp["lo"] - 1, sp, "up"), gt.crossed(sp["hi"] + 1, sp, "down"),
                        gt.crossed(sp["hi"] + 1, sp, "up"), gt.crossed(sp["lo"] - 1, sp, "down"), gt.crossed(None, sp, d)))
    return out


def _cal_rows(gt):
    """judge_calibration over the s155 catalog: the exact predicted set passes; an extra red, a predicted green, and a
    K-CAL-M red (an unpredicted red to K-CAL) each fail it."""
    class G:
        def check(self, ok, what, detail=""):
            return bool(ok)

        def note(self, text):
            pass
    out = []
    pred = set(gt.PREDICTED_S155)
    for reds in (pred, pred | {"P114-UP"}, pred - {"A408"}, pred | {"K-CAL-M"}):
        led = gt.cb.Ledger(G(), gt.catalog(False, False))
        for c in led.catalog:
            if c != "K-CAL":
                led.check(c, c not in reds)
        led.judge_calibration("K-CAL", gt.PREDICTED_S155)
        out.append(led.done["K-CAL"])
    return out


# ================================================================================================ the tables
def _calls(*calls, _vars=None, **evals):
    doc = {"calls": [{"fn": c[0], "args": list(c[1]) if len(c) > 1 else [], "kwargs": dict(c[2]) if len(c) > 2 else {}}
                     for c in calls]}
    if evals:
        doc["eval"] = evals
    if _vars:
        doc["vars"] = _vars
    return _child(doc)


def test_the_benchs_tables_are_its_docstring():
    r = _calls(("catalog", [False, True]), ("catalog", [False, False]), ("catalog", [True, True]),
               ("tally", ["plain"]), ("tally", ["s155"]), ("tally", ["lever"]), ("PREDICTED_S155",), ("PREDICTED_OFF",),
               ("NA_S155",), ("FIELD_LEGS",), ("FINALS",),
               doc="' '.join((gt.__doc__ or '').split())", claims="list(gt.CLAIMS)",
               first="sorted(gt.FIRST_DECLINE.items())")
    plain, s155, lever, t_plain, t_s155, t_lever, p155, poff, na, legs, finals = r["calls"]
    e = r["eval"]
    # the tallies are DERIVED from the catalog -- and they are the contract's
    assert (t_plain, t_s155, t_lever) == ([28, 28], [13, 19], [17, 30])
    assert len(plain) == 28 and list(plain) == e["claims"]
    assert set(s155) == (set(plain) - set(na)) | {"K-CAL-M", "K-CAL"}
    assert set(lever) == set(plain) | {"K-CAL-M", "K-CAL"}
    assert list(lever).index("K-CAL-M") < list(lever).index("K-CAL")
    assert set(p155) <= set(s155) and set(poff) <= set(lever) and not set(p155) & set(na)
    assert tuple(poff[:6]) == tuple(p155) and set(poff) - set(p155) == {"S114", "M114", "H114", "H114-CLR", "F114-MID",
                                                                         "T114-MID", "T114-HANG"}
    # every field leg is in the catalog, in the run's order; the finals are judged in the scenario's finally
    flat = [c for f in ("114", "408", "207") for c in legs[f]]
    assert flat == [c for c in plain if c not in ("K0", "K1", "K2", "K3", "K-TRIPS", "K-R")]
    assert finals == ["K3", "K-TRIPS", "K-R", "K-CAL-M", "K-CAL"]
    assert e["first"] == [["A207-UP", 207], ["A408", 408], ["D114", 114]]
    for frag in ("UNDRESSED", "THE DEFECT", "THE FIX", "THE BENCH", "THE CALIBRATION", "THE PREREQS", "PREDICTED_S155",
                 "PREDICTED_OFF", "S155_MARKER", "OFF_MARKER", "COOP_CALIBRATE=1", "coop_guest_traversal.py --instance",
                 "13/19", "28/28", "17/30", "K-CAL-M", "Never `netsync talk 2` on 114", "refuses --attach",
                 "SelfTestOffset", "no watchdog", "NOT PROVEN HERE", "unproven in game until R3",
                 "coop_talk_relay, coop_dialogue_authority, coop_diorama_return, coop_self_dress, coop_follow_race_duo"):
        assert frag in e["doc"], frag


def test_the_names_are_the_contracts():
    """The verdict names, the counter keys, the ops and the line texts the bench greps are the contract's (sections 3.1,
    4.1, 4.2, 5) -- one name table, frozen before code."""
    e = _calls(v="list(gt.VERDICT_NAMES)", ops="list(gt.GL_OPS)", ck="list(gt.COUNTER_KEYS)", key="gt.KEY",
               tp="gt.TP_REASON_CLIMB", hs="gt.REASON_HOST_SCENE", mut="gt.REASON_MUTATE.format(n=3)",
               decl="gt.DECLINE_LINE.format(f=114)", rel="gt.GL_RELEASE", jjy="gt.JJY_UID",
               off="gt.GL_LEVER_OFF")["eval"]
    assert e["v"] == ["allow", "shadow", "lever_off", "not_field", "special", "no_row", "unverified", "wrong_body",
                      "own_story", "no_control", "in_flight", "warp", "host_scene", "busy"]
    assert e["ops"] == ["act", "shadow", "off", "mutate", "clear", "teleport"]
    for k in ("climbs", "ended", "bailed", "aborted", "long_climbs", "boots_mid_climb", "trips.total", "tp_calls",
              "tp_refusals", "talk_queued", "talk_held", "talk_applied_after_climb", "talk_expired"):
        assert k in e["ck"], k
    assert e["key"] == "netsync.guestlocal"
    assert e["tp"] == "a guest climb is in flight (ladder / jump) -- it ends on its own; the ~ menu's Reload is the escape"
    assert e["hs"] == "the host is in a scene on this field"
    assert e["mut"] == ("unverified bytes: the mutate lever flipped byte 3 of the hash input (the live script is "
                        "untouched) -- ")
    assert e["decl"] == "[NetSync] chest/quad interaction suppressed (following guest) on field 114"
    assert e["rel"] == "[NetSync] harness: guest traversal back to act, the mutate disarmed (released with the harness)"
    assert e["jjy"] == 3
    assert e["off"].startswith("[NetSync] harness: guest traversal OFF -- CALIBRATION: the s155 spectator gate")


def test_the_ops_are_the_drivers():
    """The bench's guestlocal ops are the driver's (CONTRACT 4.4: Session.NETSYNC_GUESTLOCAL_OPS) and `guestlocal` is a
    sub-verb the driver knows (so cb.ns_verb routes it through Session.netsync's capability gate, never a raw step)."""
    e = _calls(ops="list(gt.GL_OPS)", drv="list(__import__('harness').Session.NETSYNC_GUESTLOCAL_OPS)",
               sub="'guestlocal' in __import__('harness').Session.NETSYNC_SUBVERBS",
               cap="__import__('harness').Session.NETSYNC_GUESTLOCAL_SUBVERBS['guestlocal'][:3]")["eval"]
    assert e["ops"] == e["drv"] and e["sub"] is True
    assert e["cap"] == ["coop_guest_local", "netsync.guestlocal", "s156"]


# ================================================================================================ the pure judges
def _doc(x=0.0, y=0.0, z=0.0, *, control=True, held=(), gl=None, field=114, model=8, armed=False):
    d = {"frame": 0, "ui_state": "FieldHUD", "field": {"id": field}, "held": list(held),
         "player": {"x": x, "y": -y, "z": z, "control": control, "model": model},   # y given in the .eb frame; published as the engine's
         "netsync": {"dress": {"self": {"armed": armed}}}}
    if gl is not None:
        d["netsync"]["guestlocal"] = gl
    return d


def _gl(**kw):
    b = {"mode": "act", "lever": None, "rows": 84, "funcs": 199, "table_crc": "0xabdefff3", "selftest": "ok",
         "last": {"seq": 0, "field": -1, "entry": -1, "verdict": None, "reason": None, "kind": None, "hashed": 0,
                  "age_ms": -1},
         "verdicts": {n: 0 for n in ("allow", "shadow", "lever_off", "not_field", "special", "no_row", "unverified",
                                     "wrong_body", "own_story", "no_control", "in_flight", "warp", "host_scene", "busy")},
         "in_flight": False, "flight": {"field": -1, "entry": -1, "kind": None, "body_open": False},
         "climbs": 0, "ended": 0, "bailed": 0, "aborted": 0, "long_climbs": 0, "boots_mid_climb": 0,
         "trips": {"total": 0, "op": 0, "glob": 0, "last": None}, "tp_calls": 0, "tp_refusals": 0, "tp_last": "ok",
         "talk_queued": 0, "talk_held": 0, "talk_applied_after_climb": 0, "talk_expired": 0,
         "mutate": {"armed": False, "index": -1, "spent": False, "hit": False, "hashed": 0}}
    for k, v in kw.items():
        if k.startswith("v_"):
            b["verdicts"][k[2:]] = v
        else:
            b[k] = v
    return b


def test_in_quad_is_the_engines_fan_of_triplets_and_every_stand_is_in_its_region():
    """The bench's IsInQuad twin against the kit's (content.doorface.region_contains) on a 10 u grid over every bench
    polygon (408 e5 is a 3-point region); the stands and landings sit in the regions a press needs."""
    r = _calls(rows="_iq_rows(gt)", stands="_stand_rows(gt)")["eval"]
    for f, e, mism, inside in r["rows"]:
        assert mism == 0, (f, e)
        assert inside > 0, (f, e)
    # the spawn is NOT in 114's gateway (36 u east of its edge); two points and a collinear triple contain nothing
    assert r["stands"] == [True] * 9 + [False, False, False]


def test_a_decline_window_reads_stayed_and_a_climb_window_never_does():
    climb = [_doc(-190, 0, 960)] * 3 + [_doc(-188, -67, 1040, control=False)] * 10
    stay = [_doc(-190, 0, 960)] * 30
    walk = [_doc(-190 + i * 3, 0, 960) for i in range(30)]
    few = [_doc(-190, 0, 960)] * 5
    r = _calls(("press_window", [climb, [-190, 0, 960]]), ("press_window", [stay, [-190, 0, 960]]),
               ("press_window", [walk, [-190, 0, 960]]), ("press_window", [few, [-190, 0, 960]]),
               ("press_window", [stay, None]))["calls"]
    wins = r
    st = _calls(*[("stayed", [w]) for w in wins])["calls"]
    assert wins[0]["fell"] is True and wins[0]["first_off"] == 3 and st[0] is False         # a climb is never a stay
    assert st[1] is True and wins[1]["max_d"] == 0.0
    assert st[2] is False and wins[2]["max_d"] > 2                                           # a walk is neither
    assert st[3] is False                                                                    # 5 samples prove nothing
    assert st[4] is False                                                                    # no pre-press position


def test_the_hold_releases_at_the_engines_exit_bound_never_inside_the_loop():
    """crossed() is false over the WHOLE loop range [lo, hi] (a release there hangs the climb) and true one unit past the
    exit bound in the climb's direction -- both ladders, both directions."""
    for f, d, inside, up_out, down_out, up_wrong, down_wrong, none in _calls(rows="_crossed_rows(gt)")["eval"]["rows"]:
        assert inside == 0, (f, d)
        assert up_out and down_out and not up_wrong and not down_wrong and not none, (f, d)


def test_the_top_xz_at_the_bottom_height_is_not_a_landing():
    top = [-188, -1030, 1257]
    r = _calls(("landed_at", [_doc(-188, -1030, 1257), top]), ("landed_at", [_doc(-188, 0, 1257), top]),
               ("landed_at", [_doc(-188, -1030, 1257, control=False), top]),
               ("landed_at", [_doc(-140, -1000, 1300), top]), ("landed_at", [_doc(-139, -1030, 1257), top]))["calls"]
    assert r == [True, False, False, True, False]        # the floor is told by y; control back; +-48 x/z, +-32 y


def test_pos_reads_the_harness_y_back_into_the_eb_frame():
    """THE Y LAW (the s155 calibration found it): the harness publishes PosObj.pos[1], the NEGATED script y (SetupJump
    stores ``jumpy = -getv2()``), so the 114 mount the .eb sends to y -67 publishes +67. pos() flips it; read raw, no
    mount could match, no direction was held, and Vivi hung on the ladder for the rest of the run."""
    up = {"player": {"x": -188.0, "y": 67.0, "z": 1040.0, "control": False}}       # a real s155 sample, as published
    e = _calls(_vars={"up": up}, p="list(gt.pos(up))", m="gt.is_mounted(up, gt.LADDERS[114]['mount_bottom'])",
               raw="gt.is_mounted({'player': dict(up['player'], y=-67.0)}, gt.LADDERS[114]['mount_bottom'])")["eval"]
    assert e["p"] == [-188.0, -67.0, 1040.0] and e["m"] is True and e["raw"] is False


def _climb_res(*, mids=6, land=(-188, -1030, 1257), held=(), gl0=None, gl1=None, flying=True, ended_ok=True,
               crossed=True, mounted=True, tail_off=0, tail_ended=None, lines=()):
    """An A114-UP record: the mount, ``mids`` loop samples, the landing. ``tail_off``: the last N samples read in_flight
    false (an early end, control still off); ``tail_ended``: the last sample's `ended` (a counter that moved mid-climb)."""
    fl = {"field": 114, "entry": 9, "body_open": True}
    samples = [_doc(-188, -67, 1040, control=False, gl=_gl(in_flight=flying, flight=fl))]
    samples += [_doc(-188, -100 - 90 * i, 1045, control=False, gl=_gl(in_flight=flying, flight=fl)) for i in range(mids)]
    for s in samples[len(samples) - tail_off:] if tail_off else ():
        s["netsync"]["guestlocal"] = _gl(in_flight=False, flight={"field": -1, "entry": -1, "body_open": False}, ended=1)
    if tail_ended is not None:
        samples[-1]["netsync"]["guestlocal"]["ended"] = tail_ended
    return {"mounted": mounted, "crossed": crossed, "samples": samples,
            "land": _doc(*land, held=held) if land is not None else None, "b0": gl0, "b1": gl1, "ended_ok": ended_ok,
            "lines": list(lines), "win": {"n": 3, "fell": True, "first_off": 1, "max_d": 80.0}}


L3_114 = "x|M| [NetSync] guest traversal: climb ended -- field 114 entry 9 (ladder), 2210 ms"


def test_an_act_climb_needs_every_part_and_each_can_fail():
    good0, good1 = _gl(), _gl(v_allow=1, climbs=1, ended=1)
    cases = {
        "good": _climb_res(gl0=good0, gl1=good1, lines=[L3_114]),
        "teleport": _climb_res(mids=0, gl0=good0, gl1=good1),                       # option E: no mid-ladder samples
        "few": _climb_res(mids=4, gl0=good0, gl1=good1),
        "no_land": _climb_res(land=None, gl0=good0, gl1=good1),
        "wrong_floor": _climb_res(land=(-188, 0, 1257), gl0=good0, gl1=good1),
        "late_release": _climb_res(held=("Up",), gl0=good0, gl1=good1),
        "no_allow": _climb_res(gl0=good0, gl1=_gl(climbs=1, ended=1)),
        "two_climbs": _climb_res(gl0=good0, gl1=_gl(v_allow=1, climbs=2, ended=1)),
        "not_flying": _climb_res(flying=False, gl0=good0, gl1=good1),
        "no_end": _climb_res(ended_ok=False, gl0=good0, gl1=good1),
        "tripped": _climb_res(gl0=good0, gl1=_gl(v_allow=1, climbs=1, ended=1, trips={"total": 1})),
        "no_block": _climb_res(),
        "not_crossed": _climb_res(crossed=False, gl0=good0, gl1=good1),
        "no_mount": _climb_res(mounted=False, gl0=good0, gl1=good1),
        # WHEN it ended: a flight that ended while control was still OFF, a counter that moved before the landing, a
        # bail, an abort, End's no-move / bailed suffix on the leg's "climb ended" line
        "ended_early": _climb_res(tail_off=2, gl0=good0, gl1=good1),
        "ended_moved": _climb_res(tail_ended=1, gl0=good0, gl1=good1),
        "bailed": _climb_res(gl0=good0, gl1=_gl(v_allow=1, climbs=1, ended=1, bailed=1)),
        "aborted": _climb_res(gl0=good0, gl1=_gl(v_allow=1, climbs=1, ended=1, aborted=1)),
        "no_move_line": _climb_res(gl0=good0, gl1=good1, lines=[L3_114 + ", the handler returned without moving the body"]),
        "bailed_line": _climb_res(gl0=good0, gl1=good1,
                                  lines=[L3_114 + ", bailed: the handler never took control or moved the body"]),
    }
    ev = {n: f"gt.judge_ladder(C[{n!r}], gt.LADDERS[114], 'up', act=True, has_key=True)" for n in cases}
    ev["s155"] = "gt.judge_ladder(C['no_block'], gt.LADDERS[114], 'up', act=True, has_key=False)"
    ev["positive_moved"] = "gt.judge_ladder(C['good'], gt.LADDERS[114], 'up', act=False, has_key=True)"
    ev["positive_quiet"] = ("gt.judge_ladder(dict(C['good'], b1=C['good']['b0']), gt.LADDERS[114], 'up', act=False, "
                            "has_key=True)")
    e = _calls(_vars={"C": cases}, **ev)["eval"]
    assert e["good"][0] is True, e["good"]
    for n in list(cases)[1:]:
        assert e[n][0] is False, (n, e[n])
    assert "CONTAMINATED" in e["late_release"][1] and "not a verdict" in e["late_release"][1]
    assert e["s155"][0] is True                       # s155: behaviour only (the gate's half is s156's)
    assert e["positive_moved"][0] is False            # a positive control whose counters moved: the gate was consulted
    assert e["positive_quiet"][0] is True
    # each WHEN-it-ended row is red on its OWN part (the others still read yes)
    for n, part in (("ended_early", "the flight outlived the climb NO"), ("ended_moved", "the flight outlived the climb NO"),
                    ("bailed", "bailed +0 NO"), ("aborted", "aborted +0 NO"), ("no_move_line", "no bailed / no-move end NO"),
                    ("bailed_line", "no bailed / no-move end NO")):
        assert part in e[n][1] and e[n][1].split(" -- ", 1)[0].count(" NO") == 1, (n, e[n][1])
    assert "NOT in flight" in e["ended_early"][1] and "ended moved on 1" in e["ended_moved"][1]


# ---- the recorded s156 plain run (.harness-runs 20261026-231319, states-final.jsonl): A207-UP / A207-DN, every publish from
# ---- the press to control back -- (frame, control, x, y (the .eb's frame), z, held, in_flight, flight.entry, body_open,
# ---- seq_open, ended). seq_open falls at f8078 / f8226, 8 / 4 frames BEFORE control (f8086 / f8230): NO control-on
# ---- publish carries a Seq, and the landing publish already reads in_flight false.
_REAL_A207_UP = [
    (7998, 1, 96, -11, -55, 'C', 1, 11, 0, 0, 8), (8000, 0, 96, -11, -55, '', 1, 11, 0, 0, 8),
    (8002, 0, 96, -11, -55, '', 1, 11, 0, 0, 8), (8004, 0, 96, -11, -55, '', 1, 11, 1, 0, 8),
    (8006, 0, 96, -11, -55, '', 1, 11, 1, 0, 8), (8008, 0, 96, -11, -55, '', 1, 11, 1, 0, 8),
    (8010, 0, 96, -11, -55, '', 1, 11, 1, 0, 8), (8012, 0, 96, -11, -55, '', 1, 11, 1, 0, 8),
    (8014, 0, 96, -11, -55, '', 1, 11, 1, 0, 8), (8016, 0, 96, -11, -55, '', 1, 11, 1, 0, 8),
    (8018, 0, 96, -11, -55, '', 1, 11, 1, 0, 8), (8020, 0, 96, -11, -55, '', 1, 11, 1, 0, 8),
    (8022, 0, 96, -11, -55, '', 1, 11, 1, 1, 8), (8024, 0, 96, -11, -55, '', 1, 11, 1, 1, 8),
    (8026, 0, 100, -35, -1, '', 1, 11, 1, 1, 8), (8028, 0, 105, -42, 53, '', 1, 11, 1, 1, 8),
    (8030, 0, 110, -34, 107, '', 1, 11, 1, 1, 8), (8032, 0, 115, -9, 161, '', 1, 11, 1, 1, 8),
    (8034, 0, 115, -9, 161, '', 1, 11, 1, 1, 8), (8036, 0, 128, -29, 164, 'U', 1, 11, 1, 1, 8),
    (8038, 0, 141, -49, 167, 'U', 1, 11, 1, 1, 8), (8040, 0, 154, -69, 170, 'U', 1, 11, 1, 0, 8),
    (8042, 0, 167, -89, 173, 'U', 1, 11, 1, 0, 8), (8044, 0, 193, -129, 180, 'U', 1, 11, 1, 0, 8),
    (8046, 0, 206, -149, 183, 'U', 1, 11, 1, 0, 8), (8048, 0, 219, -169, 186, 'U', 1, 11, 1, 0, 8),
    (8052, 0, 258, -229, 196, 'U', 1, 11, 1, 0, 8), (8054, 0, 258, -229, 196, 'U', 1, 11, 1, 0, 8),
    (8056, 0, 271, -249, 199, 'U', 1, 11, 1, 0, 8), (8058, 0, 297, -289, 206, 'U', 1, 11, 1, 0, 8),
    (8060, 0, 297, -289, 206, 'U', 1, 11, 1, 0, 8), (8062, 0, 297, -289, 206, '', 1, 11, 1, 1, 8),
    (8064, 0, 297, -289, 206, '', 1, 11, 1, 1, 8), (8066, 0, 297, -289, 206, '', 1, 11, 1, 1, 8),
    (8068, 0, 327, -368, 209, '', 1, 11, 1, 1, 8), (8070, 0, 388, -479, 216, '', 1, 11, 1, 1, 8),
    (8072, 0, 419, -511, 220, '', 1, 11, 1, 1, 8), (8074, 0, 449, -526, 223, '', 1, 11, 1, 1, 8),
    (8076, 0, 480, -526, 227, '', 1, 11, 1, 1, 8), (8078, 0, 510, -509, 230, '', 1, 11, 1, 0, 8),
    (8080, 0, 541, -477, 234, '', 1, 11, 1, 0, 8), (8082, 0, 541, -477, 234, '', 1, 11, 1, 0, 8),
    (8084, 0, 541, -477, 234, '', 1, 11, 1, 0, 8), (8086, 1, 541, -476, 234, '', 0, -1, 0, 0, 9),
]
_REAL_A207_DN = [
    (8148, 1, 541, -476, 234, 'C', 1, 10, 0, 0, 9), (8150, 0, 541, -476, 234, '', 1, 10, 0, 0, 9),
    (8152, 0, 541, -476, 234, '', 1, 10, 0, 0, 9), (8154, 0, 541, -476, 234, '', 1, 10, 1, 0, 9),
    (8156, 0, 541, -476, 234, '', 1, 10, 1, 0, 9), (8158, 0, 541, -476, 234, '', 1, 10, 1, 0, 9),
    (8160, 0, 541, -476, 234, '', 1, 10, 1, 1, 9), (8162, 0, 541, -476, 234, '', 1, 10, 1, 1, 9),
    (8164, 0, 541, -475, 234, '', 1, 10, 1, 1, 9), (8166, 0, 498, -481, 228, '', 1, 10, 1, 1, 9),
    (8168, 0, 455, -471, 223, '', 1, 10, 1, 1, 9), (8170, 0, 412, -444, 218, '', 1, 10, 1, 1, 9),
    (8172, 0, 369, -402, 213, '', 1, 10, 1, 1, 9), (8174, 0, 326, -344, 208, '', 1, 10, 1, 1, 9),
    (8176, 0, 284, -269, 203, '', 1, 10, 1, 1, 9), (8178, 0, 284, -269, 203, '', 1, 10, 1, 0, 9),
    (8180, 0, 271, -249, 199, 'D', 1, 10, 1, 0, 9), (8182, 0, 258, -229, 196, 'D', 1, 10, 1, 0, 9),
    (8184, 0, 245, -209, 193, 'D', 1, 10, 1, 0, 9), (8186, 0, 232, -189, 190, 'D', 1, 10, 1, 0, 9),
    (8188, 0, 219, -169, 186, 'D', 1, 10, 1, 0, 9), (8190, 0, 206, -149, 183, 'D', 1, 10, 1, 0, 9),
    (8192, 0, 193, -129, 180, 'D', 1, 10, 1, 0, 9), (8194, 0, 180, -109, 177, 'D', 1, 10, 1, 0, 9),
    (8196, 0, 167, -89, 173, 'D', 1, 10, 1, 0, 9), (8198, 0, 154, -69, 170, 'D', 1, 10, 1, 0, 9),
    (8200, 0, 141, -49, 167, 'D', 1, 10, 1, 0, 9), (8202, 0, 128, -29, 164, 'D', 1, 10, 1, 0, 9),
    (8204, 0, 115, -9, 161, 'D', 1, 10, 1, 0, 9), (8206, 0, 102, 11, 158, 'D', 1, 10, 1, 0, 9),
    (8208, 0, 102, 11, 158, 'D', 1, 10, 1, 1, 9), (8210, 0, 102, 11, 158, '', 1, 10, 1, 1, 9),
    (8212, 0, 102, 11, 158, '', 1, 10, 1, 1, 9), (8214, 0, 101, -32, 122, '', 1, 10, 1, 1, 9),
    (8216, 0, 100, -60, 87, '', 1, 10, 1, 1, 9), (8218, 0, 99, -72, 51, '', 1, 10, 1, 1, 9),
    (8220, 0, 98, -68, 16, '', 1, 10, 1, 1, 9), (8222, 0, 97, -48, -19, '', 1, 10, 1, 1, 9),
    (8224, 0, 96, -12, -55, '', 1, 10, 1, 1, 9), (8226, 0, 96, -12, -55, '', 1, 10, 1, 0, 9),
    (8228, 0, 96, -12, -55, '', 1, 10, 1, 0, 9), (8230, 1, 96, -11, -55, '', 0, -1, 0, 0, 10),
]
#: the recorded 114 dismount (.harness-runs 20261026-231601, states-FAILED-2.jsonl f1512-f1518): in the loop's height band,
#: 23-90 u off the ladder's x/z path
_REAL_114_DISMOUNT = [(-188, -81, 1017), (-188, -97, 995), (-188, -97, 973), (-188, -81, 950)]
_HELD = {"C": "Confirm", "U": "Up", "D": "Down"}


def _real_doc(r, field=207):
    f, c, x, y, z, h, fly, e, bo, sq, ended = r
    d = _doc(x, y, z, control=bool(c), held=[_HELD[k] for k in h], field=field, model=98,
             gl=_gl(in_flight=bool(fly), ended=ended, flight={"field": field if fly else -1, "entry": e,
                                                              "body_open": bool(bo), "seq_open": bool(sq)}))
    d["frame"] = f
    return d


def _real_res(rows, entry):
    """A ladder_run record built from a recorded climb: the publishes from the press to control back (the last is the
    landing), the counters around it, its real 'climb ended' line."""
    samples = [_real_doc(r) for r in rows]
    e0 = rows[0][-1]
    return {"mounted": True, "crossed": True, "samples": samples, "land": samples[-1],
            "b0": _gl(v_allow=e0, climbs=e0, ended=e0), "b1": _gl(v_allow=e0 + 1, climbs=e0 + 1, ended=e0 + 1),
            "ended_ok": True, "win": {"n": 40, "fell": True, "first_off": 1, "max_d": 0.0},
            "lines": [f"26.10.2026 23:15:44 |M| [NetSync] guest traversal: climb ended -- field 207 entry {entry} (ladder), "
                      "1547 ms"]}


def test_the_recorded_207_act_climbs_read_green_and_their_seqs_close_before_control():
    """THE REAL TIMELINE PINS THE JUDGES. Both recorded s156 207 act climbs read green on every part --
    the flight outlived the climb (0 publishes off it before the landing), 10 / 12 mid-ladder samples on the path. And
    no control-on publish ever carried a Seq: a "control-on seq_open sample" requirement would turn A207-UP / A207-DN red
    on the CORRECT engine, so the bench does not have one (FlightRule's seq-tail term is the selftest's: NOT PROVEN HERE)."""
    up, dn = _real_res(_REAL_A207_UP, 11), _real_res(_REAL_A207_DN, 10)
    e = _calls(_vars={"U": up, "D": dn},
               up="gt.judge_ladder(U, gt.LADDERS[207], 'up', act=True, has_key=True)",
               dn="gt.judge_ladder(D, gt.LADDERS[207], 'down', act=True, has_key=True)",
               mids="[len(gt.mid_samples(U['samples'], gt.LADDERS[207])), len(gt.mid_samples(D['samples'], gt.LADDERS[207]))]",
               out="[gt.flight_outlived(U['samples'], 207, 11, gt.LADDERS[207]['land_top'], 8),"
                   " gt.flight_outlived(D['samples'], 207, 10, gt.LADDERS[207]['land_bottom'], 9)]")["eval"]
    assert e["up"][0] is True, e["up"]
    assert e["dn"][0] is True, e["dn"]
    assert e["mids"] == [10, 12], e["mids"]
    assert all(ok for ok, _ in e["out"]) and all("0 off the flight" in w and "ended moved on 0" in w for _, w in e["out"])
    for rows in (_REAL_A207_UP, _REAL_A207_DN):
        assert any(r[9] for r in rows)                                                # the Seqs DID run (seq_open)
        assert not any(r[1] and r[9] for r in rows)                                   # never with control on
        assert rows[-1][1] == 1 and rows[-1][6] == 0                                  # the landing: control, out of flight


def test_a_flight_must_outlive_the_climb_and_a_talk_landing_is_cut_at_the_landing():
    """flight_outlived on the recorded A207-UP: an early end with control still OFF is red (the last control-off
    publish, or any one before it); a publish AT the landing position that a relayed talk took (control off, no window
    yet, out of flight) is the landing, not a dropped flight -- the cut is the landing position as well as control."""
    rows = _REAL_A207_UP
    early = [r[:6] + (0, -1, 0, 0, r[10]) if 8074 <= r[0] < 8086 else r for r in rows]       # ended at the dismount
    last = [r[:6] + (0, -1, 0, 0, r[10]) if r[0] == 8076 else r for r in rows]                # the last before the cut
    gap = [r[:6] + (0, -1, 0, 0, r[10]) if r[0] == 8044 else r for r in rows]                 # one dropped mid-climb
    talk = rows[:-1] + [(8086, 0, 541, -477, 234, '', 0, -1, 0, 0, 9)]                         # a talk took the frame
    S = {k: [_real_doc(r) for r in v] for k, v in (("real", rows), ("early", early), ("last", last), ("gap", gap),
                                                    ("talk", talk))}
    ev = {k: f"gt.flight_outlived(S[{k!r}], 207, 11, gt.LADDERS[207]['land_top'], 8)" for k in S}
    ev["never"] = "gt.flight_outlived([], 207, 11, gt.LADDERS[207]['land_top'], 8)"
    ev["other_entry"] = "gt.flight_outlived(S['real'], 207, 10, gt.LADDERS[207]['land_top'], 8)"
    e = _calls(_vars={"S": S}, **ev)["eval"]
    assert e["real"][0] is True and e["talk"][0] is True, (e["real"], e["talk"])
    for k in ("early", "last", "gap", "never", "other_entry"):
        assert e[k][0] is False, (k, e[k])
    assert "NOT in flight" in e["last"][1] and "1 off the flight" in e["gap"][1]


def test_a_stay_at_207s_foot_or_an_arc_is_no_climb():
    """The measured rows: 207's loop band (lo -269, hi -9) holds its FOOT floor (y -11..-16), the mount arc and the
    dismount arc, so the height band alone counted a teleport as a climb (15 / 6 'mid' samples, min_mid 3). On the
    ladder's own x/z path (12 u; inside the mounts' heights by 10 u) the same rows count 0 and read red. The margins are
    the recorded ones: every held-key loop sample within 1 u of the path, every other in-band sample 23 u or more off."""
    def off(x, y, z, **kw):
        return _doc(x, y, z, control=False, field=207, model=98, **kw)
    foot = [off(96, -11, -55) for _ in range(12)]
    arc = [off(100, -35, -1), off(105, -42, 53), off(110, -34, 107), off(115, -9, 161)]
    tp_up = {"mounted": True, "crossed": True, "samples": foot + arc + [_doc(541, -477, 234, field=207, model=98)],
             "land": _doc(541, -477, 234, field=207, model=98), "win": {"n": 40, "fell": True, "first_off": 1, "max_d": 0.0}}
    dis = [off(101, -32, 122), off(100, -60, 87), off(99, -72, 51), off(98, -68, 16), off(97, -48, -19),
           off(96, -12, -55)]
    tp_dn = {"mounted": True, "crossed": True, "samples": [off(284, -269, 203)] + dis + [_doc(96, -12, -55, field=207,
                                                                                               model=98)],
             "land": _doc(96, -12, -55, field=207, model=98), "win": {"n": 40, "fell": True, "first_off": 1, "max_d": 0.0}}
    loop = [(r[2], r[3], r[4]) for r in _REAL_A207_UP + _REAL_A207_DN if r[5] in ("U", "D") and -269 < r[3] < -9]
    other = ([(r[2], r[3], r[4]) for r in _REAL_A207_UP + _REAL_A207_DN if not r[1] and not r[5] and -269 < r[3] < -9],
             _REAL_114_DISMOUNT)
    e = _calls(_vars={"U": tp_up, "D": tp_dn, "LOOP": loop, "O207": other[0], "O114": other[1]},
               up="gt.judge_ladder(U, gt.LADDERS[207], 'up', act=False, has_key=False)",
               dn="gt.judge_ladder(D, gt.LADDERS[207], 'down', act=False, has_key=False)",
               band="[sum(1 for s in X['samples'] if not gt.control(s) and -269 < gt.pos(s)[1] < -9) for X in (U, D)]",
               loop_max="max(gt.path_dist(p, gt.LADDERS[207]) for p in LOOP)",
               other_min="min([gt.path_dist(p, gt.LADDERS[207]) for p in O207]"
                         " + [gt.path_dist(p, gt.LADDERS[114]) for p in O114])",
               tol="gt.LADDER_PATH_TOL",
               on="[gt.on_ladder(p, gt.LADDERS[207]) for p in ((96, -11, -55), (115, -9, 161), (193, -129, 180), "
                  "(297, -289, 206), (101, -32, 122))]")["eval"]
    assert e["band"] == [15, 6]                       # what the height band alone counted: a "climb" by the old rule
    assert e["up"][0] is False and "0 mid-ladder control-off samples" in e["up"][1], e["up"]
    assert e["dn"][0] is False and "0 mid-ladder control-off samples" in e["dn"][1], e["dn"]
    assert len(loop) >= 20 and e["loop_max"] <= 1.0 < e["tol"] < 23.0 <= e["other_min"], (e["loop_max"], e["other_min"])
    assert e["on"] == [False, True, True, False, False]   # the foot, the mount, the loop, past the bound, the dismount arc


def test_a_talk_legs_landing_may_be_the_talks_window():
    """A relayed start can take control in the frame the climb hands it back (no publish between them): on a TALK leg the
    window open at the landing counts as control back; on any other leg it does not; nowhere near the landing never."""
    land = [-188, -1030, 1257]
    talk_up = dict(_doc(*land, control=False), dialog={"open": True})
    far = dict(_doc(-188, 0, 906, control=False), dialog={"open": True})
    e = _calls(_vars={"L": land, "T": {"land": talk_up, "talk_leg": True}, "N": {"land": talk_up},
                      "W": {"land": _doc(*land)}, "F": {"land": far, "talk_leg": True}},
               talk="gt.landing_part(T, L)", other="gt.landing_part(N, L)", plain="gt.landing_part(W, L)",
               far="gt.landing_part(F, L)", none="gt.landing_part({}, L)")["eval"]
    assert e["talk"][0] is True and "the talk window up" in e["talk"][2]
    assert e["other"][0] is False and e["plain"][0] is True and e["far"][0] is False and e["none"][0] is False


def test_a_hop_needs_mid_air_and_an_act_hop_needs_body_open_mid_air():
    land = [1394, -436, 5668]
    before = [1511, -249, 5392]
    air = [_doc(1450, -400, 5530, control=False, field=408,
                gl=_gl(in_flight=True, flight={"field": 408, "entry": 4, "body_open": True})) for _ in range(3)]
    shut = [_doc(1450, -400, 5530, control=False, field=408,
                 gl=_gl(in_flight=False, flight={"field": -1, "entry": -1, "body_open": False})) for _ in range(3)]
    b0, b1 = _gl(), _gl(v_allow=1, climbs=1, ended=1)
    base = {"left": True, "before": before, "land": _doc(*land, field=408), "b0": b0, "b1": b1, "ended_ok": True}
    V = {"good": dict(base, samples=air), "region_return": dict(base, samples=shut), "no_air": dict(base, samples=[]),
         "never_left": dict(base, samples=air, left=False), "positive": dict(base, samples=shut, b1=_gl())}
    ev = {k: f"gt.judge_hop(V[{k!r}], gt.HOPS['out'], act={k != 'positive'}, has_key=True)" for k in V}
    e = _calls(_vars={"V": V}, **ev)["eval"]
    assert e["good"][0] is True, e["good"]
    assert e["region_return"][0] is False and "body_open" in e["region_return"][1]   # the 408 Async row
    assert e["no_air"][0] is False and e["never_left"][0] is False
    assert e["positive"][0] is True


def test_a_verdict_needs_a_moved_seq_on_this_field():
    b0 = _gl(last={"seq": 4, "field": 114, "entry": 9, "verdict": "shadow"})
    moved = _gl(last={"seq": 5, "field": 114, "entry": 9, "verdict": "shadow"})
    stale = _gl(last={"seq": 4, "field": 114, "entry": 9, "verdict": "shadow"})
    other = _gl(last={"seq": 5, "field": 408, "entry": 4, "verdict": "shadow"})
    r = _calls(("fresh_verdict", [b0, moved, 114]), ("fresh_verdict", [b0, stale, 114]),
               ("fresh_verdict", [b0, other, 114]), ("fresh_verdict", [None, moved, 114]),
               ("seq_moved", [b0, stale]), ("seq_moved", [b0, moved]), ("seq_moved", [None, moved]))["calls"]
    assert r[0]["verdict"] == "shadow" and r[1] is None and r[2] is None and r[3] is None
    assert r[4:] == [False, True, None]


def test_the_markers_need_every_part():
    stay = {"n": 40, "fell": False, "first_off": None, "max_d": 0.4}
    walk = {"n": 40, "fell": False, "first_off": None, "max_d": 30.0}
    good = {"in_quad": True, "control": True, "win": stay, "line_needed": True, "line": True,
            "d": {"verdicts.lever_off": 1}, "seq_moved": False}
    V = {"good": good, "route": dict(good, in_quad=False), "no_control": dict(good, control=False),
         "walked": dict(good, win=walk), "no_line": dict(good, line=False),
         "line_not_needed": dict(good, line_needed=False, line=False),
         "computed": dict(good, d={"verdicts.lever_off": 0}), "seq": dict(good, seq_moved=True)}
    ev = {**{f"s155_{k}": f"gt.s155_marker(V[{k!r}])[0]" for k in V},
          **{f"off_{k}": f"gt.off_marker(V[{k!r}])[0]" for k in V},
          "none": "gt.s155_marker(None)[0] or gt.off_marker(None)[0]"}
    e = _calls(_vars={"V": V}, **ev)["eval"]
    assert e["s155_good"] and e["off_good"] and not e["none"]
    for k in ("route", "no_control", "walked", "no_line"):
        assert not e[f"s155_{k}"], k
    assert e["s155_line_not_needed"] and e["s155_computed"] and e["s155_seq"]      # s155 has no counters to read
    for k in ("route", "no_control", "walked", "computed", "seq"):
        assert not e[f"off_{k}"], k
    assert e["off_no_line"]                                                         # OFF_MARKER needs no line


def test_k1_and_k2_judge_against_the_committed_table_never_a_literal():
    tbl = {"rows": 84, "funcs": 199, "fields": 37, "table_crc": "0xabdefff3"}
    other = dict(tbl, rows=86)
    ok_line = ["x|M| [NetSync] guest traversal selftest: OK (120 rows, 30 mutants caught, 84 table rows / 199 functions, "
               "table crc 0xabdefff3)"]
    fail_line = ["x|M| [NetSync] guest traversal selftest: FAIL (slice.T.3: start 19, want 24)"]
    r = _calls(("parse_selftest", [ok_line]), ("parse_selftest", [fail_line]), ("parse_selftest", [[]]))["calls"]
    assert r[0]["ok"] and (r[0]["rows"], r[0]["funcs"], r[0]["crc"]) == (84, 199, "0xabdefff3") and not r[1]["ok"]
    assert r[2] is None
    j = _calls(("judge_k1", [r[0], tbl]), ("judge_k1", [r[0], other]), ("judge_k1", [r[1], tbl]),
               ("judge_k1", [None, tbl]), ("judge_k1", [r[0], None]),
               ("judge_k2", [_gl(), tbl]), ("judge_k2", [_gl(), other]), ("judge_k2", [_gl(selftest=None), tbl]),
               ("judge_k2", [_gl(lever="off"), tbl]), ("judge_k2", [_gl(mode="shadow"), tbl]),
               ("judge_k2", [_gl(table_crc="0xABDEFFF3"), tbl]), ("judge_k2", [None, tbl]))["calls"]
    assert [x[0] for x in j] == [True, False, False, False, False, True, False, False, False, False, True, False]


def test_the_offset_preflight():
    cfg = "x|M| [NetSync] config enabled=False role=off field=0 selfTestOffset=700,0 peer=127.0.0.1:49201"
    r = _calls(("offset_from", [[cfg]]), ("offset_from", [[], "100, -20"]), ("offset_from", [[]]),
               ("offset_from", [["[NetSync] config enabled=False role=off"], "garbage"]),
               ("offset_from", [["[NetSync] config enabled=False role=off"], "700,0"]),
               ("offset_ok", [700, 0]), ("offset_ok", [250, 0]), ("offset_ok", [453, 453]), ("offset_ok", [452, 452]),
               ("offset_ok", [-639, 0]), ("offset_ok", [0, -640]))["calls"]
    assert r[0][:2] == [700, 0] and r[1][:2] == [100, -20] and r[2][:2] == [250, 0] and r[3][:2] == [250, 0]
    assert r[4][:2] == [250, 0]                     # the engine's own config line beats the ini (no token = 250,0)
    assert r[5:] == [False, True, False, True, True, False]          # |offset| >= 640 refuses (452,452 is 639.2)


def test_the_undressed_and_arrival_witnesses():
    r = _calls(("undressed", [_doc(model=8), 114]), ("undressed", [_doc(model=98), 114]),
               ("undressed", [_doc(model=8, armed=True), 114]), ("undressed", [_doc(field=408, model=98), 408]),
               ("arrived", [_doc(-854, 0, -232), 114]), ("arrived", [_doc(-854, 0, -232, control=False), 114]),
               ("arrived", [_doc(-700, 0, -232), 114]), ("arrived", [_doc(-854, 0, -232, field=70), 114]))["calls"]
    assert [x[0] for x in r] == [True, False, False, True, True, False, False, False]


def test_the_calibration_judge_exact_set_extra_red_predicted_green_and_k_cal_m():
    """The ledger's judge_calibration over the predicted set, and K-CAL-M red blocking K-CAL (an unpredicted red)."""
    assert _calls(r="_cal_rows(gt)")["eval"]["r"] == [True, False, False, False]


def test_judge_markers_names_each_predicted_leg():
    stay = {"n": 40, "fell": False, "first_off": None, "max_d": 0.0}
    rec = {"in_quad": True, "control": True, "win": stay, "line_needed": False, "line": False,
           "d": {"verdicts.lever_off": 1}, "seq_moved": False}
    marks = {c: rec for c in ("A114-UP", "A114-DN", "A408", "A408-RET", "A207-UP", "A207-DN")}
    e = _calls(_vars={"M": marks, "M5": {k: v for k, v in marks.items() if k != "A408"}},
               ok="gt.judge_markers('s155', M)", missing="gt.judge_markers('s155', M5)",
               lever_short="gt.judge_markers('lever', M)", plain="gt.judge_markers('plain', {})")["eval"]
    assert e["ok"][0] is True and e["ok"][1].count(" SEEN") == 6 and "NOT seen" not in e["ok"][1]
    assert e["missing"][0] is False and "A408 NOT seen" in e["missing"][1]
    assert e["lever_short"][0] is False and "S114 NOT seen" in e["lever_short"][1]   # the R1 legs carry OFF_MARKER too
    assert e["plain"][0] is False                                                   # nothing to judge is no calibration


# ================================================================================================ the whole bench, simulated
def _runs(**runs):
    return _child({"runs": runs})["runs"]


def test_the_bench_reads_28_of_28_on_a_correct_s156_model():
    r = _runs(plain={})["plain"]
    assert r["red"] == [], {c: r["detail"][c] for c in r["red"]}
    assert r["n"] >= 28 and len(r["all"]) == 28
    d = r["detail"]
    assert "lever_off +1 yes" in d["D114"] and "shadow +1 yes" in d["S114"] and "unverified +1 yes" in d["M114"]
    assert "host_scene +1 yes" in d["H114"] and "tp_refusals +1 yes" in d["F114-MID"]
    assert "talk_applied_after_climb +1 yes" in d["T114-MID"] and "talk_applied_after_climb +1 yes" in d["T114-HANG"]
    assert "flight.body_open on a mid-air sample yes" in d["A408"]
    assert any("UNDRESSED guest" in n for n in r["notes"])
    assert not any(n.startswith("reposition for") for n in r["notes"]), [n for n in r["notes"] if "reposition" in n]
    # the plain run pulls a lever into the reset, so K-R's release line is a check that can fail -- and arms a mutate with
    # it (at rest nothing spends it), so the re-read's 'mutate unarmed' half can fail too
    assert "the release line 1x (want 1)" in d["K-R"]
    assert r["gl_calls"][-2:] == [["mutate", "3"], ["shadow"]], r["gl_calls"][-3:]
    assert "mutate armed into the reset True" in d["K-R"] and "mutate.armed False" in d["K-R"], d["K-R"]
    # every act leg judges WHEN its flight ended; F114-REST judges the snap by the engine's own lines
    for c in ACT_LEGS:
        for part in ("the flight outlived the climb yes", "bailed +0 yes", "aborted +0 yes", "no bailed / no-move end yes"):
            assert part in d[c], (c, part, d[c][:400])
    assert "the snapped line yes" in d["F114-REST"] and "no 'teleport-to-host failed' yes" in d["F114-REST"]
    # the model's 207 Seqs ran on both act climbs and closed before control, as recorded in game
    assert r["seq"]["frames"] > 0 and r["seq"]["with_control"] == 0, r["seq"]


def test_the_s155_model_calibrates_automatically_13_of_19_and_never_sends_guestlocal():
    r = _runs(s155={"engine": "s155"})["s155"]
    red = set(r["red"])
    assert red == {"A114-UP", "A114-DN", "A408", "A408-RET", "A207-UP", "A207-DN"}, {c: r["detail"][c] for c in red}
    assert len(r["all"]) == 19 and "K-CAL" in r["all"] and "K-CAL-M" in r["all"]
    assert r["detail"]["K-CAL-M"].count(" SEEN") == 6 and "NOT seen" not in r["detail"]["K-CAL-M"], r["detail"]["K-CAL-M"]
    assert r["gl_calls"] == []                                       # the driver never sends a verb the engine lacks
    for na in ("K1", "K2", "F114-REST", "S114", "M114", "T114-MID", "H114", "H114-CLR", "F114-MID", "T114-HANG",
               "K-TRIPS"):
        assert na not in r["all"], na
    # A408 and A207-UP are their fields' FIRST quad declines: their markers include the line (a missing line is NOT seen)
    assert any("chest/quad interaction suppressed (following guest) on field 408" in ln for ln in r["log"])
    assert any(n.startswith("reposition for A114-DN") or n.startswith("reposition for T114-LAND") for n in r["notes"])


def test_an_s155_red_without_its_marker_cannot_pass_the_calibration():
    """A red that is not s155's behaviour: the s155 model's decline goes SILENT (no first-decline line), so A408 and A207-UP
    still read red -- the set judge alone would pass -- but their markers are not seen: K-CAL-M red naming them, K-CAL red."""
    r = _runs(silent={"engine": "s155", "mutants": ["silent_decline"]})["silent"]
    red, d = set(r["red"]), r["detail"]
    assert red >= {"A114-UP", "A114-DN", "A408", "A408-RET", "A207-UP", "A207-DN", "K-CAL-M", "K-CAL"}, sorted(red)
    assert "A408 NOT seen" in d["K-CAL-M"] and "A207-UP NOT seen" in d["K-CAL-M"], d["K-CAL-M"]
    assert "A114-UP SEEN" in d["K-CAL-M"]                            # 114's first decline is D114's, not A114-UP's
    assert "K-CAL-M" in d["K-CAL"].split("unpredicted reds:")[1], d["K-CAL"]


def test_the_lever_calibration_reads_17_of_30_with_every_r1_leg_red_by_its_marker():
    r = _runs(lever={"cal": True})["lever"]
    red = set(r["red"])
    want = {"A114-UP", "A114-DN", "A408", "A408-RET", "A207-UP", "A207-DN", "S114", "M114", "H114", "H114-CLR",
            "F114-MID", "T114-MID", "T114-HANG"}
    assert red == want, {c: r["detail"][c][:300] for c in red ^ want}
    assert len(r["all"]) == 30
    assert r["detail"]["K-CAL-M"].count(" SEEN") == 13 and "NOT seen" not in r["detail"]["K-CAL-M"], r["detail"]["K-CAL-M"]
    # the lever is pulled once, right after K2, and held: no act / shadow / clear / mutate is ever sent
    assert r["gl_calls"][0] == ["off"] and all(c[0] in ("off", "teleport") for c in r["gl_calls"]), r["gl_calls"]
    assert "the release line 1x (want 1)" in r["detail"]["K-R"]


#: every act leg: each judges its climb / hop's gate half (judge_ladder / judge_hop -> _gate_parts)
ACT_LEGS = {"A114-UP", "A114-DN", "H114-CLR", "F114-MID", "T114-MID", "T114-HANG", "A408", "A408-RET", "A207-UP",
            "A207-DN"}


@pytest.mark.parametrize("mutant,reds", [
    ("x1", {"A114-UP", "T114-LAND", "A114-DN"}),            # the frame end: a flight never ends at a 114 landing
    ("shadow_acts", {"S114"}),
    ("crc_blind", {"M114"}),
    ("scene_blind", {"H114"}),
    ("lever_blind", {"D114"}),
    ("tp_snaps", {"F114-MID"}),
    ("async_blind", {"A408", "A408-RET"}),
    ("no_retention", {"T114-HANG", "T114-MID"}),
    ("ends_at_bound", ACT_LEGS),            # the flight ends with control still OFF (the loop's bound, a hop's descent)
    ("bails_flag", ACT_LEGS),               # a landing counted -- and logged -- as a bail
    ("no_move_line", ACT_LEGS),             # End's "returned without moving the body" on a climb that moved it
    ("slow_mount", {"A207-UP", "A207-DN"}),  # the guest's 207 mount lands 5 s late (the hold law: the next test)
    ("tp_throws", {"F114-REST"}),           # the snap moved the body, then the call threw (tp_last still 'ok')
    ("release_keeps_mutate", {"K-R"}),      # `reset` releases the lever but leaves the mutate armed
])
def test_each_broken_gate_turns_its_own_legs_red(mutant, reds):
    """A rule broken on purpose turns red the legs that judge it (each leg CAN go red), and the bench recovers its pose."""
    r = _runs(m={"mutants": [mutant]})["m"]
    red = set(r["red"])
    assert reds <= red, (mutant, sorted(red))
    if mutant not in ("x1",):
        assert red == reds, (mutant, sorted(red), {c: r["detail"][c][:300] for c in red - reds})


def test_no_direction_is_held_before_a_mount_and_no_talk_2():
    """THE ORDERING LAW 4 on every run: each hold starts with control off on the ladder's loop (the mount SEEN), never at a
    hop and never at rest; and the bench never sends `netsync talk 2` (BBA) -- only JJY's uid 3. The slow_mount run is
    THE HOLD-ONLY-AFTER-A-MOUNT LAW's: a recovery at 207's foot (control off, the mount still coming) holds nothing until
    the body is ON the ladder's path, then climbs it out from the loop."""
    rr = _runs(plain={}, s155={"engine": "s155"}, lever={"cal": True}, slow={"mutants": ["slow_mount"]})
    assert any(n.startswith("recovery: the player hangs on 207's ladder at (115, -9, 161)") for n in rr["slow"]["notes"]), \
        [n for n in rr["slow"]["notes"] if n.startswith("recovery")]
    for name, r in rr.items():
        assert r["holds"], name
        for h in r["holds"]:
            assert h["control"] is False and h["phase"] == "loop", (name, h)
        talks = [s for s in r["sent"] if s[:2] == ["netsync", "talk"]]
        assert all(s[2] == "3" for s in talks), (name, talks)
        warps = [s for s in r["sent"] if s[0] == "warp"]
        assert [w[1] for w in warps] == [114, 408, 207] and all(w[2] == 0 for w in warps), (name, warps)
        assert ["noencounter", True] in r["sent"]
        for w in warps[1:]:                              # THE ENV-SLOT LAW: both slots zeroed right before 408 / 207's warp
            i = r["sent"].index(w)
            assert r["sent"][i - 2:i] == [["byte", 13, 0], ["byte", 14, 0]], (name, r["sent"][i - 3:i + 1])


def test_an_env_slot_left_playing_strands_408_and_207():
    """The poke is load-bearing: with it ignored, 114's playing slot 1 raises 408's 'Error Env Play()' window and its
    WaitWindow keeps control off, so every 408 / 207 leg is red (each 'not reached'), the 114 legs untouched."""
    r = _runs(m={"mutants": ["env_poke_ignored"]})["m"]
    red = set(r["red"])
    legs = {"P408", "P408-RET", "A408", "A408-RET", "P207-UP", "P207-DN", "A207-UP", "A207-DN"}
    assert legs <= red, sorted(red)
    assert not {c for c in red if c.endswith("114") or "114-" in c}, sorted(red)
    assert all("warp 408 failed" in r["detail"][c] or "warp 207 failed" in r["detail"][c] for c in legs),         {c: r["detail"][c][:200] for c in legs}


def test_the_selftests_flight_tail_mutants_are_invisible_here():
    """NOT PROVEN HERE, pinned: the selftest's mutant.flight.control_only (ends on control alone) and mutant.flight.seq_blind
    (blind to a Seq tail), modelled on the sim's measured 207 Seqs, read 28/28 -- on these rows the Seqs and the body close
    BEFORE control (the model's Seqs ran, never with control on), so no bench leg can tell them from FlightRule; only the
    selftest's flight.seq_tail / flight.async_tail rows can. The bench's own flight judge is the control-OFF half."""
    rr = _runs(control_only={"mutants": ["control_only"]}, seq_blind={"mutants": ["seq_blind"]})
    for name, r in rr.items():
        assert r["red"] == [] and len(r["all"]) == 28, (name, {c: r["detail"][c][:300] for c in r["red"]})
        assert r["seq"]["frames"] > 0 and r["seq"]["with_control"] == 0, (name, r["seq"])
    doc = " ".join((_calls(d="gt.__doc__")["eval"]["d"] or "").split())
    nph = doc.split("NOT PROVEN HERE", 1)[1]
    for frag in ("flight.seq_tail", "flight.async_tail", "control_only", "seq_blind", "BEFORE control"):
        assert frag in nph, frag


def test_f114_rest_needs_the_engines_success_line_not_the_resting_tp_last():
    """F114-REST: tp_last 'ok' is the latch's RESTING value (it starts "" and TeleportToHostImpl's catch never sets it), so a
    call that moved the body and then threw still read 'ok'. The verdict is the snap AND the success line with no failure
    line; a decline still reads red on tp_last; an off-mesh snap is CONTAMINATED."""
    ok_line = "x|M| [NetSync] teleport-to-host: snapped onto the selftest mirror"
    bad_line = "x|E| [NetSync] teleport-to-host failed -- System.NullReferenceException"
    off_line = "x|M| [NetSync] teleport-to-host declined: the mirror offset is off this walkmesh (landed at the default spawn)"
    b0, b1 = _gl(), _gl(tp_calls=1)
    base = {"p0": [-854, 0, -232], "p1": [-604, 0, -232], "b0": b0, "b1": b1, "d": {"tp_calls": 1, "tp_refusals": 0}}
    V = {"good": dict(base, lines=[ok_line]), "threw": dict(base, lines=[bad_line]), "silent": dict(base, lines=[]),
         "both": dict(base, lines=[ok_line, bad_line]), "no_snap": dict(base, p1=base["p0"], lines=[ok_line]),
         "declined": dict(base, b1=_gl(tp_calls=1, tp_last="user control is off (dialogue/event/transition)"),
                          lines=[ok_line]),
         "off_mesh": dict(base, lines=[off_line])}
    e = _calls(_vars={"V": V}, **{k: f"gt.judge_tp_rest(V[{k!r}])" for k in V})["eval"]
    assert e["good"][0] is True, e["good"]
    for k in ("threw", "silent", "both", "no_snap", "declined", "off_mesh"):
        assert e[k][0] is False, (k, e[k])
    assert "the snapped line NO" in e["threw"][1] and "no 'teleport-to-host failed' NO" in e["threw"][1]
    assert "tp_last 'ok' (no decline latched) yes" in e["threw"][1]       # what the old judge leaned on: still 'ok'
    assert e["off_mesh"][1].startswith("CONTAMINATED")


def test_the_preflights_refuse_attach_and_a_large_offset():
    rr = _runs(attach={"attach": True}, offset={"offset": [700, 0]})
    a, o = rr["attach"], rr["offset"]
    assert "K0" in a["red"] and "--attach" in a["detail"]["K0"]
    assert ["warp", 114, 0, None] not in a["sent"]                    # nothing touched
    assert "K0" in o["red"] and "REFUSED" in o["detail"]["K0"]
    for r in (a, o):
        assert set(r["red"]) == set(r["all"]), r["red"]              # every leg reads 'not reached', none green


def test_a_dressed_guest_is_undressed_before_any_leg():
    r = _runs(dressed={"dressed": True})["dressed"]
    assert r["red"] == [], r["red"]
    assert ["netsync", "selfdress", "self", "off"] in r["sent"]


# ================================================================================================ the twins vs the patch
def test_the_log_line_twins_are_the_s156_patchs_text():
    """Every s156 line the bench greps is the engine's text: each template's literal pieces occur in the captured s156
    patch. RED until the lead captures memoria-patches/s156-*.patch -- by design (the contract: generator first, then the
    C# capture)."""
    patches = sorted((REPO / "memoria-patches").glob(PATCH_GLOB))
    assert patches, "s156 not captured: no memoria-patches/s156-*.patch yet (the lead captures it after integration)"
    added = "\n".join(ln[1:] for p in patches for ln in p.read_bytes().decode("utf-8", "replace").splitlines()
                      if ln.startswith("+") and not ln.startswith("+++"))
    e = _calls(_vars={"SRC": added}, missing="_twin_missing(gt, SRC)")["eval"]
    assert not e["missing"], e["missing"]


def _twin_missing(gt, src: str) -> list:
    """(template, piece) the C# source ``src`` does not spell with its literals in order (child-side)."""
    lits = gt.cs_literals(src)
    out = [(k, p) for k, v in gt.GL_TEMPLATES.items() for p in gt.literal_pieces(v) if not gt.spelled(p, lits)]
    out += [("text", t) for t in (gt.TP_REASON_CLIMB, gt.REASON_HOST_SCENE, gt.TALK_QUEUED_WHY, gt.TALK_TAIL_WHY)
            if not gt.spelled(t, lits)]
    return out


def test_the_twin_check_spells_composed_lines_and_refuses_a_drifted_word():
    """spelled(): the engine's literals in order spell a piece across expressions, a ternary's other branches and a
    concatenation; a drifted word, a wrong order or literals too far apart never spell it -- the check can fail."""
    src = ('Log.Message("[NetSync] harness: guest traversal " + (op == "off"\n'
           '    ? "OFF -- CALIBRATION: the s155 spectator gate (every quad press declined, nothing hashed, no new line)"\n'
           '    : op == "shadow" ? "SHADOW (verdicts computed and logged, every press declined as s155)" : "ACT")\n'
           '    + " (released with the harness)");\n'
           'Log.Message("[NetSync] guest traversal: field " + fld + " entry " + entry + (row >= 0 ? " (" + k + ")" : "")\n'
           '    + " declined -- " + reason);  Char c = \'"\';')
    drift = src.replace("spectator gate", "spectator gates")
    e = _calls(_vars={"S": src, "D": drift},
               lits="gt.cs_literals(S)",
               off="gt.spelled(gt.GL_LEVER_OFF, gt.cs_literals(S))", act="gt.spelled(gt.GL_LEVER_ACT, gt.cs_literals(S))",
               shadow="gt.spelled(gt.GL_LEVER_SHADOW, gt.cs_literals(S))",
               declined="all(gt.spelled(p, gt.cs_literals(S)) for p in gt.literal_pieces(gt.GL_DECLINED))",
               drift="gt.spelled(gt.GL_LEVER_OFF, gt.cs_literals(D))",
               order="gt.spelled(' (released with the harness)[NetSync] harness: guest traversal ', gt.cs_literals(S))",
               far="gt.spelled('ab', ['a'] + ['x'] * 20 + ['b'])", near="gt.spelled('ab', ['a', 'x', 'b'])")["eval"]
    assert e["off"] and e["act"] and e["shadow"] and e["declined"] and e["near"]
    assert not e["drift"] and not e["order"] and not e["far"]
    assert e["lits"][0] == "[NetSync] harness: guest traversal " and '"' not in "".join(e["lits"])   # the char '"' is no string


# ================================================================================================ the kit's table
def test_kit_table_reads_the_committed_json_or_says_why_not():
    e = _child({"eval": {"t": "gt.kit_table()"}})["eval"]["t"]
    p = KIT / "ff9mapkit" / "data" / "guest_traversal.json"
    if p.exists():
        doc = json.loads(p.read_text(encoding="utf-8"))
        assert e[0] == {"rows": doc["counts"]["rows"], "funcs": doc["counts"]["funcs"],
                        "fields": doc["counts"].get("fields", -1), "table_crc": str(doc["table_crc"]).lower()}, e
    else:
        assert e[0] is None and "guest_traversal" in e[1], e


# ================================================================================================ INSTALL-GATED
_REQUIRE = os.environ.get("FF9MAPKIT_REQUIRE_INSTALL", "").strip() not in ("", "0")


def _install_or_skip():
    """The real install, READ ONLY: both caches the kit's readers need must already exist (EventBundle writes the events
    cache on a miss; stock_walkmesh builds the field index on a miss -- this test never lets either happen)."""
    sys.path.insert(0, str(KIT))
    try:
        from ff9mapkit import config
        game = config.find_game_path(None)
    except Exception as err:                                           # noqa: BLE001
        game, why = None, f"no install ({err})"
    else:
        why = ""
    if game is not None:
        sa = pathlib.Path(game) / "StreamingAssets"
        for cache in (".ff9mapkit-events-bundle.txt", ".ff9mapkit-field-index.json"):
            if not (sa / cache).exists():
                why, game = f"{sa / cache} is absent (reading would WRITE it)", None
                break
    if game is None:
        msg = f"THE GUEST TRAVERSAL BENCH GEOMETRY WENT UNVERIFIED: {why}"
        if _REQUIRE:
            pytest.fail(msg)
        warnings.warn(msg)
        pytest.skip(msg)
    return pathlib.Path(game)


_GEOM_CHILD = r'''
import json, struct, sys, importlib.util, os
scen, kit, game = sys.argv[1:4]
sys.path.insert(0, kit)
import ff9mapkit
from pathlib import Path
assert Path(ff9mapkit.__file__).resolve().is_relative_to(Path(kit).resolve()), ff9mapkit.__file__
from ff9mapkit import extract
from ff9mapkit.eb import EbScript
sa = Path(game) / "StreamingAssets"
snap = {p.name: (p.stat().st_size, p.stat().st_mtime) for p in sa.iterdir() if p.is_file()}
b = extract.EventBundle(game)                 # reads the existing events cache (asserted present by the parent)
def s16(v): return v - 0x10000 if v & 0x8000 else v
out = {}
for fid, ents in {114: (0, 8, 9, 11), 207: (0, 10, 11, 13, 15), 408: (0, 4, 5, 13, 14, 17)}.items():
    data = b.eb_for_id(fid)
    eb = EbScript.from_bytes(data)
    rec = {"regions": {}, "jumps": {}, "models": {}, "init_regions": [], "tags": {}, "consts": {}}
    for ei in ents:
        e = eb.entry(ei)
        rec["tags"][ei] = [f.tag for f in e.funcs]
        for f in e.funcs:
            for ins in eb.instrs(f):
                if ins.op == 0x29 and f.tag == 0 and ei not in rec["regions"]:
                    rec["regions"][ei] = [[s16(v & 0xFFFF), s16((v >> 16) & 0xFFFF)] for v in ins.args]
                elif ins.op == 0xE2 and all(isinstance(a, int) for a in ins.args[:3]):
                    rec["jumps"].setdefault(f"{ei}/{f.tag}", []).append([s16(ins.args[0]), s16(ins.args[1]), s16(ins.args[2])])
                elif ins.op == 0x2F and f.tag == 0 and isinstance(ins.args[0], int):
                    rec["models"][ei] = ins.args[0]
                elif ins.op == 0x08 and ei == 0 and f.tag == 0 and isinstance(ins.args[0], int):
                    rec["init_regions"].append(ins.args[0])
            if f.tag == 0:
                blob = data[f.abs_start:f.abs_end]
                rec["consts"][ei] = [v for v in range(-2000, 6000) if b"\x7d" + struct.pack("<h", v) in blob] if ei in (11, 15, 17) else []
    out[fid] = rec
comps = {}
for fid, pts in {114: {"bottom": (-188, 906), "top": (-188, 1257), "spawn": (-854, -232), "stand": (-190, 960)},
                 207: {"bottom": (96, -55), "top": (541, 234), "spawn": (-185, -366), "stand": (52, -30)},
                 408: {"ledge": (1550, 5356), "shelf": (1394, 5668), "spawn": (-649, 5139), "stand": (1511, 5392)}}.items():
    wm = extract.stock_walkmesh(fid, game)
    wv = wm.world_verts()
    from collections import deque
    def walk(t): return (t.tri_flags & 1) and not ((t.tri_flags >> 8) & 0x80)
    seen, comp_of = set(), {}
    for s0 in range(len(wm.tris)):
        if s0 in seen: continue
        q, cid = deque([s0]), s0
        while q:
            t = q.popleft()
            if t in seen: continue
            seen.add(t); comp_of[t] = cid
            if not walk(wm.tris[t]): continue
            for n in wm.tris[t].nbr:
                if 0 <= n < len(wm.tris) and n not in seen and walk(wm.tris[n]): q.append(n)
    comps[fid] = {k: sorted({(comp_of[t], round(sum(wv[v][1] for v in wm.tris[t].vtx) / 3.0)) for t in wm.tris_at(x, z)
                            if walk(wm.tris[t])}) for k, (x, z) in pts.items()}
after = {p.name: (p.stat().st_size, p.stat().st_mtime) for p in sa.iterdir() if p.is_file()}
print("@@RESULT@@" + json.dumps({"eb": out, "comps": comps, "wrote": sorted(set(after.items()) ^ set(snap.items()))}))
'''


_ROUTE_CHILD = r"""
import json, sys, importlib.util, os
scen, kit, game = sys.argv[1:4]
sys.path.insert(0, kit)
import ff9mapkit
assert os.path.abspath(ff9mapkit.__file__).startswith(os.path.abspath(kit)), ff9mapkit.__file__
from ff9mapkit import extract
from ff9mapkit.content import pathfind
spec = importlib.util.spec_from_file_location("gt_route", os.path.join(scen, "coop_guest_traversal.py"))
sys.path.insert(0, scen)
gt = importlib.util.module_from_spec(spec); spec.loader.exec_module(gt)
out = {}
for fid, stand in ((114, gt.LADDERS[114]["stand_bottom"]), (207, gt.LADDERS[207]["stand_bottom"]), (408, gt.HOPS["out"]["stand"])):
    wm = extract.stock_walkmesh(fid, game=game)
    avoid = [list(p) for p in gt.GEOM[fid]["gateways"].values()]
    cl = gt.GEOM[fid].get("clearance")
    plan = lambda c: pathfind.route_avoiding(wm, gt.GEOM[fid]["spawn"], stand, avoid, clearance=c) is not None
    out[fid] = {"bench": plan(cl), "default": plan(None), "clearance": cl}
print("@@RESULT@@" + json.dumps(out))
"""


def test_each_stand_routes_from_its_spawn_at_the_benchs_clearance():
    """INSTALL-GATED: every field's first stand plans from its spawn, clear of the gateways, at the clearance go_to
    passes; on 408 the corridor to the e4 ledge is under twice the default 80 u, so the default plans NOTHING (the s155
    calibration's 'no route on field 408') -- the per-field clearance is load-bearing, and only 408 carries one."""
    game = _install_or_skip()
    out = subprocess.run([sys.executable, "-c", _ROUTE_CHILD, str(SCENARIOS), str(KIT), str(game)], capture_output=True,
                         text=True, timeout=600, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    assert out.returncode == 0, out.stderr[-4000:]
    got = json.loads([ln for ln in out.stdout.splitlines() if ln.startswith("@@RESULT@@")][-1][len("@@RESULT@@"):])
    assert all(r["bench"] for r in got.values()), got
    assert got["408"]["default"] is False and got["408"]["clearance"] == 56.0, got
    assert got["114"]["clearance"] is None and got["207"]["clearance"] is None, got


def test_the_bench_geometry_is_the_installs_eb():
    """INSTALL-GATED (a worktree skip is not green -- THE WORKTREE SKIP TRAP: run it in the gate worktree or the main repo):
    the bench's constants re-derived from the install's .eb and stock walkmesh through the kit, read only."""
    game = _install_or_skip()
    out = subprocess.run([sys.executable, "-c", _GEOM_CHILD, str(SCENARIOS), str(KIT), str(game)], capture_output=True,
                         text=True, timeout=600, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    assert out.returncode == 0, out.stderr[-4000:]
    got = json.loads([ln for ln in out.stdout.splitlines() if ln.startswith("@@RESULT@@")][-1][len("@@RESULT@@"):])
    assert got["wrote"] == [], f"the read-only check changed StreamingAssets: {got['wrote']}"
    want = _child({"eval": {"geom": "{f: {'regions': {str(k): [list(p) for p in v] for k, v in {**G['regions'], "
                                     "**G['gateways']}.items()}, 'spawn': list(G['spawn']), 'body': G['body']} for f, G "
                                     "in gt.GEOM.items()}",
                            "ladders": "{f: {k: list(v) for k, v in s.items() if k.startswith(('mount', 'land'))} for f, s "
                                       "in gt.LADDERS.items()}",
                            "hops": "{k: list(h['land']) for k, h in gt.HOPS.items()}"}})["eval"]
    eb = got["eb"]
    # the polygons (SetRegion in each region's tag 0), the press regions' tag 3 (and 114 e9's tag 2 tread)
    for f, G in want["geom"].items():
        for e, poly in G["regions"].items():
            assert eb[f]["regions"][e] == poly, (f, e, eb[f]["regions"].get(e))
    assert 3 in eb["114"]["tags"]["9"] and 2 in eb["114"]["tags"]["9"]
    assert all(3 in eb["207"]["tags"][e] for e in ("10", "11")) and all(3 in eb["408"]["tags"][e] for e in ("4", "5"))
    # the SetupJump targets: the ladders' mounts and landings, the hops' landings
    assert sorted(eb["114"]["jumps"]["11/17"]) == sorted(want["ladders"]["114"].values())
    assert sorted(eb["207"]["jumps"]["15/50"]) == sorted(want["ladders"]["207"].values())
    assert want["hops"]["out"] in eb["408"]["jumps"]["17/15"] and want["hops"]["ret"] in eb["408"]["jumps"]["17/16"]
    # the bodies (UNDRESSED: the field's own player model) and the arming (Main_Init's InitRegion, unconditional)
    assert eb["114"]["models"]["11"] == want["geom"]["114"]["body"]
    assert eb["207"]["models"]["15"] == want["geom"]["207"]["body"] and eb["408"]["models"]["17"] == want["geom"]["408"]["body"]
    assert 9 in eb["114"]["init_regions"] and {4, 5} <= set(eb["408"]["init_regions"])
    # the spawns' coordinates are constants of each player setup
    for f, e in (("114", "11"), ("207", "15"), ("408", "17")):
        sx, sz = want["geom"][f]["spawn"]
        assert sx in eb[f]["consts"][e] and sz in eb[f]["consts"][e], (f, sx, sz)
    # the landings' walkmesh components: each ladder's ends are DIFFERENT components (stranded on foot), the stand and the
    # spawn share the bottom one; the 408 shelf is not the ledge's, and the ledge is the spawn's
    c = got["comps"]
    for f, lo, hi in (("114", "bottom", "top"), ("207", "bottom", "top"), ("408", "ledge", "shelf")):
        cl, ch = {x[0] for x in c[f][lo]}, {x[0] for x in c[f][hi]}
        assert cl and ch and not cl & ch, (f, c[f])
        assert {x[0] for x in c[f]["spawn"]} & cl and {x[0] for x in c[f]["stand"]} & cl, (f, c[f])
