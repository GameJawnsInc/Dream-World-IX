"""OFFLINE DRY RUN of stall_session.py: the real harness driver (tools/harness Session) against the protocol stand-in
(FakeGame), whose overworld on (7,17) is driven tick by tick by stall_sim's calibrated port of the engine step loop.

Why: memory project-ff9-test-harness ("an offline dry run caught probes wandering") -- and a check that cannot fail
is no check. So the scenario runs three times, against three ENGINES, and its verdicts must split:
  sim    the calibrated port (stall_sim.Walker)                    -> every K check passes
  seam   H_SEAM, RESULTS.md section 6's leading hypothesis: the creep happens, but the step that would land across
         the seam is refused every tick (a stall at the edge)       -> K3, K4, K5 must FAIL; K1, K2 still pass
  drop   H_DROP, the section-6 reading "descent refused where the drop is ~3u": any probe across a drop > 2.6u is
         refused (no creep, no crossing)                            -> K2, K3, K4 must FAIL
Off the cell (the 6603 landing lawn, where world_face probes) the stand-in is flat ground at y 3.2 and walking
there flushes the triangle cache, as foreign-block hits do in the engine (WMBlock.cs:150).

The fake renders 60 fps and runs the world on its own clock at WorldTPS 28 (Memoria.ini [Graphics] WorldTPS; the
bumpers turn PsxRot(32) a TICK and "up" moves the actor a tick), so a 6-frame burst holds 2 OR 3 ticks depending on
its phase -- as the real runs do (the session-5 +1 ring has 2-tick bursts at seqs 45 and 50). REVIEW FIX: the first
cut stepped a tick every other frame (30 Hz), so every burst held exactly 3 and the fixed-ticks-per-burst K2/K5
tables that fail on real bursts about a third of the time passed here every time.
Nothing here touches the game install: the stand-in's "install" is a folder in the scratchpad.

    py studies/terrain-malleability/ingame/stall_dryrun.py            # all three engines
    py studies/terrain-malleability/ingame/stall_dryrun.py sim        # one
"""
from __future__ import annotations

import importlib.util
import json
import math
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(HERE))
import stall_sim as S                                           # noqa: E402
from harness import Session                                     # noqa: E402
from harness.fakegame import FakeGame                           # noqa: E402

f32 = S.f32
CELL_BOX = (448.0, 512.0, -1152.0, -1088.0)
LAWN_Y = 3.2
TURN_PER_TICK = 2.8125                        # PsxRot(32) a world tick (ff9.cs:6139-6148)
WORLD_TPS, RENDER_FPS = S.WORLD_TPS, 60.0     # the world's own clock against the fake's render


def _in_cell(x, z):
    return CELL_BOX[0] <= x < CELL_BOX[1] and CELL_BOX[2] < z <= CELL_BOX[3]


class SimFake(FakeGame):
    def __init__(self, root, engine: str, cam0: float = 30.0):
        super().__init__(root, fps=600.0)
        self.engine = engine
        self.walker = S.Walker(S.cell_block(3.0), 0.0)
        self.overworld = {"cam": cam0}
        self._ow_y = LAWN_Y
        self._sim_xz = None
        self._tick_acc = 0.0
        self._up_prev = False
        self.burst_ticks: list = []           # ticks each "up" hold held (2 or 3 for a 6-frame hold at 28 TPS)
        self.ticks_log: list = []

    def _sync_from_walker(self):
        self.world["x"], self.world["z"] = float(self.walker.x), float(self.walker.z)
        self._ow_y = float(self.walker.y)
        self._sim_xz = (self.world["x"], self.world["z"])

    def _engine_tick(self):
        w = self.walker
        saved = (w.x, w.y, w.z, w.id, w.part)
        row = w.tick()
        refuse = False
        if self.engine == "seam" and not row.get("stalled") and row.get("collapsed") and row["part"] != row["from_part"]:
            refuse = True                     # H_SEAM: the crossing step is refused
        if self.engine == "drop" and not row.get("stalled") and row.get("collapsed") and abs(row["dy_probe"]) > 2.6:
            refuse = True                     # H_DROP: no step across a ~3u drop at all
        if refuse:
            w.x, w.y, w.z, w.id, w.part = saved
            row = dict(w.state(), stalled=True, hypothesis=self.engine)
        self.ticks_log.append(row)

    def _step_overworld(self) -> None:
        ow = self.overworld
        if self.world["x"] is None:
            return
        x, z = self.world["x"], self.world["z"]
        if _in_cell(x, z) and self._sim_xz != (x, z):          # moved by a teleport: InitSlice re-grounds
            self.walker.teleport(x, z, self._ow_y)
            self._sync_from_walker()
        up = self._is_held("up")
        if up and not self._up_prev:
            self.burst_ticks.append(0)
        self._up_prev = up
        self._tick_acc += WORLD_TPS / RENDER_FPS                # the world ticks on its own clock, held or not
        if self._tick_acc >= 1.0:
            self._tick_acc -= 1.0
            if self._is_held("leftbumper") or self._is_held("l1"):
                ow["cam"] = (ow["cam"] + TURN_PER_TICK) % 360.0
            if self._is_held("rightbumper") or self._is_held("r1"):
                ow["cam"] = (ow["cam"] - TURN_PER_TICK) % 360.0
            if up:
                self.burst_ticks[-1] += 1
                cam = ow["cam"]
                if _in_cell(x, z):
                    self.walker.phi = f32((90.0 - cam) % 360.0)        # RotTrue + 180 from the camera line
                    self._engine_tick()
                    self._sync_from_walker()
                else:
                    s = float(S.SPEED)
                    self.world["x"] = (x + s * math.cos(math.radians(cam))) % 1536.0
                    self.world["z"] = z + s * math.sin(math.radians(cam))
                    self._ow_y = LAWN_Y
                    self._sim_xz = None
                    self.walker.cache.flush()
        x, z = self.world["x"], self.world["z"]
        self.player = [x * 256.0, math.trunc(self._ow_y * 256.0), z * 256.0]


def fake_install(root: Path) -> Path:
    if root.exists():
        shutil.rmtree(root)
    (root / "x64").mkdir(parents=True)
    (root / "x64" / "FF9.exe").write_bytes(b"MZ")
    (root / "x64" / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    mod = root / "FF9CustomMap"
    mod.mkdir()
    (mod / "DictionaryPatch.txt").write_text("", encoding="utf-8")
    lab = root / "FF9CustomMap-lab" / Path("FF9_Data/WorldMap/Disc1/0_1/r17")
    lab.mkdir(parents=True)
    shutil.copyfile(S.regen_terrain(3.0), lab / "Block[7][17] Terrain.ff9mesh")
    return root


def load_scenario():
    spec = importlib.util.spec_from_file_location("stall_session_dry", HERE / "stall_session.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_engine(engine: str) -> dict:
    root = fake_install(S.SCR / f"fakegame-{engine}")
    fake = SimFake(root, engine)
    scen = load_scenario()

    def enter_world(g):
        g.newgame(settle=0)
        fake.world.update({"id": 9011, "x": 68.0, "z": -444.0})
        fake.ui_state = "WorldHUD"
        g.wait_for(lambda s: s.on_world and s.world_x is not None and s.player_y is not None,
                   timeout=10.0, what="the stand-in on the world map")

    scen.enter_world = enter_world
    with Session(game_path=root, run_dir=root / "run", save_dir=root / "player-saves", pid_probe=lambda: [],
                 launcher=lambda exe: fake.start(), boot_timeout=30.0, verbose=False) as g:
        scen.run(g)
        checks = [{"ok": c["ok"], "what": c["what"][:60], "detail": c.get("detail", "")[:200]} for c in g.checks]
    rec = json.loads((root / "run" / "stall_session.json").read_text(encoding="utf-8"))
    sizes = {}
    for n in fake.burst_ticks:
        sizes[n] = sizes.get(n, 0) + 1
    return {"engine": engine, "checks": checks, "faces": {k: rec.get(k) for k in ("face_n", "face_s")},
            "burst_frames": [rec.get("burst_frames"), rec.get("burst_frames_s")],
            "ticks_per_frame": [rec.get("ticks_per_frame_n"), rec.get("ticks_per_frame_s")],
            "hold_tick_counts": dict(sorted(sizes.items())),
            "lines": {ln["name"]: {"approach": (ln.get("approach") or {}).get("outcome"),
                                   "outcome": ln.get("outcome"), "end": ln.get("end", {}).get("pz"),
                                   "y": ln.get("end", {}).get("y"), "creep_tick": ln.get("creep_tick_fit")}
                      for ln in rec["lines"]}}


EXPECT = {"sim": {"K0": True, "K1": True, "K2": True, "K3": True, "K4": True, "K5": True},
          "seam": {"K1": True, "K2": True, "K3": False, "K4": False, "K5": False},
          "drop": {"K2": False, "K3": False, "K4": False}}


def main(engines):
    out = {}
    for e in engines:
        res = run_engine(e)
        out[e] = res
        print(f"== engine {e}: faces {res['faces']} burst {res['burst_frames']} frames "
              f"(ticks/frame {res['ticks_per_frame']}); ticks per up-hold: {res['hold_tick_counts']}")
        for c in res["checks"]:
            print(f"   {'PASS' if c['ok'] else 'FAIL'}  {c['what']}  | {c['detail'][:150]}")
        print(f"   lines: {json.dumps(res['lines'])}")
        got = {c["what"].split()[0]: c["ok"] for c in res["checks"] if c["what"].startswith("K")}
        want = EXPECT.get(e, {})
        bad = {k: (got.get(k), v) for k, v in want.items() if got.get(k) is not v}
        res["discriminates_as_registered"] = not bad
        print(f"   verdicts as registered for this engine: {'YES' if not bad else 'NO ' + json.dumps(bad)}")
    S.OUT.mkdir(exist_ok=True)
    (S.OUT / "stall_dryrun.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    return out


if __name__ == "__main__":
    main(sys.argv[1:] or ["sim", "seam", "drop"])
