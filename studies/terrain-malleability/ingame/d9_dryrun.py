"""OFFLINE DRY RUN of d9_session.py against the harness FakeGame, over the REAL Disc9 mesh (no game, no install writes).

What it exercises -- the parts of the scenario that are NEW (the field half of the route, newgame -> warp(30950) ->
calibrate -> walk onto the pad, is the proven 6603 door idiom and is stubbed: the stub still calls newgame() and the
registration-guarded warp(30950), then stands him on 9013 at the landing as the bench's splice would):

  * the preflight against a staged game dir (FolderNames, the lab's registrations, the WorldMap(9013) bytes) -- and
    that it REFUSES the same dir with the splice missing (a check that cannot fail is no check);
  * the teleport-home burst loop on the carry homes and the landing lawn, with the stand-in's ground = the live mesh
    raster (blocked = not foot-walkable; height = ground, canopy minus the sink) -- every burst must stay on its home's
    (area, topograph) class and under BURST_MAX;
  * the ENGINE's encounter rule, re-implemented on the stand-in's per-frame movement (EventEngine.ProcessEvents.cs
    :289-297/:496-518: 960-fixed checks after -1440, base += WORLD13's zone ENCRATE, fire when random8 < base>>3;
    SelectScene over the zone's fog-0 record with d[pattern&3]); a teleport adds nothing, as in the engine;
  * capture (scene, fire position, its class), the soft reset from BattleHUD (FakeGame with the ENGINE's soft-reset UI
    set, SOFT_RESET_ENGINE_UI), the loop bookkeeping, every judged check, and d9_session.json.

It cannot say anything about the engine. It says the scenario does what d9_PLAN.md claims, on the real geometry.

Rerun:  py studies/terrain-malleability/ingame/d9_dryrun.py [--seed N] [--cam DEG]
NEGATIVE CONTROLS (each must turn the named checks red, or the check cannot fail):
        --fog 1         the stand-in rolls the fog-1 twins (777/779): B2 must FAIL on the carry loops, B1 must pass
        --no-sink       the stand-in's canopy height lacks the 1.171875 sink: H must FAIL on the topo-37 loop
        --zone0         the stand-in rolls zone 0's rows everywhere: B1 and B2 must FAIL on the carry loops
"""
import argparse
import json
import math
import os
import random
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
sys.path.insert(0, str(REPO / "tools"))
os.environ["D9_DRYRUN"] = "1"                 # skip the import-time preflight against the REAL install
sys.path.insert(0, str(HERE))
import d9_session as D                         # noqa: E402
from harness import Session                    # noqa: E402
from harness.fakegame import FakeGame, SOFT_RESET_ENGINE_UI   # noqa: E402

PREP = D.PREP
WORLD_ID = 9013
ENC_D = [(96, 168, 224, 255), (64, 128, 192, 255), (90, 167, 244, 255), (115, 217, 244, 255)]  # EventEngine.Static.cs:120-126
LADDER = {int(k): v for k, v in PREP["world13"]["encratio_by_zone"].items()}


def stage_game(root: Path, spliced: bool = True) -> Path:
    game = root / "game"
    (game / "x64").mkdir(parents=True)
    (game / "x64" / "FF9.exe").write_bytes(b"MZ")
    (game / "x64" / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    (game / "Memoria.ini").write_text('[Mod]\nFolderNames = "FF9CustomMap-lab", "FF9CustomMap-world"\n', encoding="utf-8")
    lab = game / D.LAB
    lab.mkdir()
    (lab / "DictionaryPatch.txt").write_text("MessageFile 30950 MES_DWIX_30950\n"
                                             "FieldScene 30950 11 PATHDGATE PATHDGATE 30950\n", encoding="utf-8")
    for lang in D.LANGS:
        p = lab / D.EB_REL.format(lang=lang)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x00" * 16 + (D.WORLDMAP_9013 if spliced else b"\xb6\x00\x33\x23") + b"\x00" * 16)
    w = game / "FF9CustomMap-world"
    w.mkdir()
    (w / "DictionaryPatch.txt").write_text("WorldScene 9013 WORLD13\n", encoding="utf-8")
    return game


def cell_of(x, z):
    for cell in ("carry", "landing"):
        c = D.classify(x, z, cell)
        if c and not c.get("outside_cell"):
            return cell, c
    return None, {}


def ground_model(no_sink=False):
    from ff9mapkit.world.placement import WALK_OK

    def blocked(x, z):
        _cell, c = cell_of(x, z)
        return not c or c.get("topo") not in WALK_OK or c.get("area", -1) < 0

    def height(x, z):
        _cell, c = cell_of(x, z)
        if not c:
            return 0.0
        return c.get("ground", 0.0) if no_sink else c.get("expect_y", 0.0)
    return blocked, height


class Encounters:
    """The engine's world random-encounter rule on the stand-in's movement (see module docstring)."""

    def __init__(self, fake, rng, fog=0, zone0=False):
        self.fake, self.rng, self.fog, self.zone0 = fake, rng, fog, zone0
        self.reset()
        self.fired = []
        self._orig = fake._step_overworld
        fake._step_overworld = self.step

    def reset(self):
        self.timer, self.base, self.last = -1440.0, 0, None

    def table(self, cell):
        return PREP["encounter"] if cell == "carry" and not self.zone0 else PREP["encounter_landing"]

    def step(self):
        f = self.fake
        x0, z0 = f.world["x"], f.world["z"]
        self._orig()
        if f.ui_state != "WorldHUD" or x0 is None or not f._is_held("up"):
            return
        x1, z1 = f.world["x"], f.world["z"]
        d = math.hypot(x1 - x0, z1 - z0)
        if d <= 0:
            return
        cell, c = cell_of(x1, z1)
        if not c:
            return
        enc = self.table(cell)
        zone = enc["zone"]
        self.timer += d * 256.0
        if self.timer <= 960:
            return
        self.timer = 0.0
        self.base += LADDER.get(zone, 0)
        if self.rng.randrange(256) >= (self.base >> 3):
            return
        self.base = 0
        rows = [r for r in enc["rows"] if r["topo"] == c["topo"] and r["fog"] == self.fog]
        if not rows:
            return                                           # s60 hole -> no battle
        r = rows[0]

        def pick():
            n = self.rng.randrange(256)
            dd = ENC_D[r["sel"]]
            return r["scene"][0 if n < dd[0] else 1 if n < dd[1] else 2 if n < dd[2] else 3]
        scene = pick()
        if scene == self.last:
            scene = pick()
        self.last = scene
        self.fired.append({"scene": scene, "x": x1, "z": z1, "topo": c["topo"], "cell": cell})
        f.start_battle(scene)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=9013)
    ap.add_argument("--cam", type=float, default=None, help="fixed camera bearing (default: a random one per loop)")
    ap.add_argument("--fog", type=int, default=0)
    ap.add_argument("--no-sink", action="store_true")
    ap.add_argument("--zone0", action="store_true")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    root = Path(tempfile.mkdtemp(prefix="d9_dryrun_"))
    try:
        # (0) the preflight must PASS on a staged deploy and REFUSE the same deploy without the splice
        bad = D.preflight(stage_game(root / "nosplice", spliced=False))
        assert bad["problems"] and "splice" in " ".join(bad["problems"]), bad
        game = stage_game(root)
        good = D.preflight(game)
        assert not good["problems"], good
        print("preflight: refuses a splice-less deploy, passes the staged one")

        fake = FakeGame(game)
        fake.soft_reset_ui = SOFT_RESET_ENGINE_UI
        blocked, height = ground_model(no_sink=a.no_sink)
        enc = Encounters(fake, rng, fog=a.fog, zone0=a.zone0)
        cams = []

        def fake_enter(g, lrec):
            st = g.state
            if st.ui_state != "Title":
                ok, why = g.restore_baseline()
                if not ok:
                    raise D.HarnessError(why)
            g.newgame(settle=0)
            g.warp(D.BENCH)                        # the registration guard reads the staged lab DictionaryPatch
            cam = a.cam if a.cam is not None else rng.uniform(0, 360)
            cams.append(round(cam, 1))
            fake.overworld = {"speed": 0.3, "turn": 2.8125, "cam": cam, "lag": 3, "blocked": blocked, "height": height}
            fake._ow_yaw = None
            fake.world.update({"id": WORLD_ID, "x": D.LANDING[0], "z": D.LANDING[1]})
            fake.ui_state = "WorldHUD"
            fake.control = True
            enc.reset()                            # InitEncount at the world's StartEvents
            g.wait_world(timeout=10)
            st = g.world_settle()
            lrec["arrival"] = {"world": st.world_id, "x": st.world_x, "z": st.world_z, "y": st.world_y,
                               "scenario": st.scenario, "t": 0}

        D.enter_9013 = fake_enter
        with Session(game_path=game, run_dir=game / "run", save_dir=game / "player-saves", pid_probe=lambda: [],
                     launcher=lambda exe: fake.start(), boot_timeout=15.0, verbose=False) as g:
            D.run(g)
            checks = list(g.checks)
        rec = json.loads((game / "run" / "d9_session.json").read_text(encoding="utf-8"))
        # exercise d9_post.py end to end: keep the run dir, and give it a SYNTHETIC Memoria.log carrying exactly the
        # oracle's predicted Disc9 lines once per world load plus one "[Soft Reset]" per soft-reset recovery
        keep = HERE / "out" / "d9_dryrun_run"
        shutil.rmtree(keep, ignore_errors=True)
        shutil.copytree(game / "run", keep)
        lines = []
        for _load in rec.get("world_loads", []):
            for key, c in sorted(PREP["bind"]["cells"].items()):
                x, y = key.split(",")
                for part in c["bound"]:
                    lines.append(f"07.10.2026 23:59:00 |M| [WorldMeshOverride] loaded 'WorldMap/Disc9/0_1/r{y}/Block[{x}][{y}] "
                                 f"{part}' from FF9CustomMap-world/FF9_Data/WorldMap/Disc9/0_1/r{y}/Block[{x}][{y}] {part}.ff9mesh")
        for l in rec["loops"]:
            if (l.get("recovery") or {}).get("how") == "soft_reset_from_battle":
                lines.append("07.10.2026 23:59:30 |M| [Soft Reset]")
        (keep / "Memoria.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
        import d9_post
        d9_post.main(keep)
        problems = []
        for lrec in rec["loops"]:
            home = lrec["home"]
            want = PREP["homes"][home]
            bursts = lrec.get("bursts", [])
            off = [b for b in bursts if (b.get("area"), b.get("topo")) != (want["area"], want["topo"])]
            big = [b for b in bursts if b["d"] > D.BURST_MAX]
            b = lrec.get("battle") or {}
            print(f"{lrec['label']:12s} bursts {len(bursts):3d}  max d {max([x['d'] for x in bursts] or [0]):.2f}  "
                  f"off-class {len(off)}  >BURST_MAX {len(big)}  battle {b.get('scene')} at topo "
                  f"{(b.get('fire_class') or {}).get('topo')} after {b.get('walked_u')}u  recovery "
                  f"{(lrec.get('recovery') or {}).get('how')}  verdicts {lrec.get('verdicts')}")
            if off:
                problems.append(f"{lrec['label']}: {len(off)} bursts left the home class, e.g. {off[0]}")
            if big:
                problems.append(f"{lrec['label']}: {len(big)} bursts over BURST_MAX, e.g. {big[0]}")
            if lrec.get("error"):
                problems.append(f"{lrec['label']}: error {lrec['error']}")
        fails = [c for c in checks if not c["ok"]]
        print(f"cams {cams}; engine-rule fires {[(f['scene'], f['topo']) for f in enc.fired]}")
        print(f"checks: {len(checks)} ({len(fails)} failed)")
        for c in fails:
            print("   FAIL", c["what"], c.get("detail", "")[:200])
        tag = "".join(t for t, on in (("-fog1", a.fog == 1), ("-nosink", a.no_sink), ("-zone0", a.zone0)) if on)
        out = HERE / "out" / f"d9_dryrun{tag}.json"
        out.write_text(json.dumps({"seed": a.seed, "cams": cams, "fired": enc.fired, "problems": problems,
                                   "checks": [{k: c[k] for k in ("ok", "what")} for c in checks],
                                   "loops": rec["loops"]}, indent=1, default=str), encoding="utf-8")
        print(f"wrote {out}")
        if problems or fails:
            print("DRY RUN PROBLEMS:\n  " + "\n  ".join(problems))
            return 1
        print("DRY RUN CLEAN")
        return 0
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
