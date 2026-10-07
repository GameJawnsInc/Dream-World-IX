"""DRY RUN of experiment rank 10 -- never touches the game, a mod folder or the memory store.

PART A (seconds): the DECISION RULE (cost_lib.decide / decide_load / score) fed synthetic per-load tables whose truth
is known -- a null, an effect, a missing positive control, a regime flip, a render-only shift, the load hitch -- and
one deliberately BROKEN rule (walk fps alone, no within-load idle control, no bracketing) on a table where a regime
flip coincides with the x16 loads: the broken rule must say COST, the real rule must not. A rule that cannot be
shown wrong on a table built to fool it is a check that cannot fail.

PART B (~4 min, real time): cost_session.run end to end against the harness FakeGame (tools/harness/fakegame.py) in a
throwaway game dir under the session scratchpad, its lab folder there too (COST_LAB). The world reload hook is
replaced by a stand-in that does what the engine does at world entry -- a scene-switch frame, ~0.3 s on the world
scene, the LoadBlocks frame (+60 ms for x64), then the HUD -- and reads the swapped file's height to ground the walk
(the binding the in-game run proves). The fake walks the circle at the world tick rate (0.4375u and 2.8125deg a
tick, its frame time stretched while "up" is held by an INJECTED per-tick cost: x16 3 ms, x64 12 ms -- x4 none), so
the instrument chain (poller -> windows -> arm binding -> circle fit -> score) must return x64 COST, x16 COST,
x4 FREE, the positive control fired, and x64 LOAD-COST.

Rerun:  py studies/terrain-malleability/ingame/cost_dryrun.py [--part a|b]
"""
from __future__ import annotations

import json
import os
import random
import shutil
import struct
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
import cost_lib as L                                               # noqa: E402

SCRATCH = Path(os.environ.get("COST_SCRATCH", r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX"
                                              r"\8b61f6d3-b0c2-4ade-9f22-b2bc267b1c8d\scratchpad\cost"))
FULL = [1, 1, 64, 1, 16, 1, 4, 1, 64, 1, 16, 1, 4, 1, 64, 1, 16, 1]


# ================================================================================================ PART A
def _w(fps, span, long_rel=0.01, tick_rate=28.0, ok=True):
    return {"ok": ok, "fps": round(fps, 3), "frames": int(round(fps * span)), "span_s": span, "long_rel": long_rel,
            "tick_rate": tick_rate}


def table(effect: dict, amp_effect: dict, *, seed=1, idle=58.0, noise=0.6, regime_at=None, idle_shift=None,
          load_ms=None, load_noise=10.0, schedule=FULL):
    """Synthetic loads: idle fps ~ idle + noise; walk = idle - 3 + effect[arm] + noise; ts-4 walk4 likewise.
    regime_at: {load index: (idle, walk)} overrides (a 31-fps regime on those loads).
    idle_shift: {arm: fps added to that arm's IDLE (a render cost)}; load_ms: {arm: ms added to blocks}."""
    rng = random.Random(seed)
    loads = []
    for i, arm in enumerate(schedule):
        role = "warm" if i == 0 else ("ref" if arm == 1 else "test")
        f_idle = idle + rng.gauss(0, noise) + (idle_shift or {}).get(arm, 0.0)
        f_walk = f_idle - 3.0 + effect.get(arm, 0.0) + rng.gauss(0, noise)
        if regime_at and i in regime_at:
            f_idle, f_walk = regime_at[i]
            f_idle += rng.gauss(0, noise)
            f_walk += rng.gauss(0, noise)
        f_i4 = 55.0 + rng.gauss(0, noise)
        f_w4 = f_i4 - 5.0 + amp_effect.get(arm, 0.0) + rng.gauss(0, noise)
        W = {"idle_pre": _w(f_idle, 4.0), "idle_post": _w(f_idle + rng.gauss(0, noise * 0.5), 3.0),
             "walk": _w(f_walk, 21.4), "idle4": _w(f_i4, 2.0), "walk4": _w(f_w4, 5.4, tick_rate=112.0)}
        blocks = 1300.0 + rng.gauss(0, load_noise) + (load_ms or {}).get(arm, 0.0)
        loads.append({"load": i, "arm": arm, "role": role, "arm_ok": True, "windows": W,
                      "entry": {"blocks_ms": round(blocks, 1)}})
    return loads


def broken_decide(loads):
    """THE BROKEN RULE: walk fps alone vs the mean of ALL refs -- no idle control, no bracketing, no regime test."""
    refs = [ld["windows"]["walk"]["fps"] for ld in loads if ld["role"] == "ref"]
    base = sum(refs) / len(refs)
    out = {}
    for ld in loads:
        if ld["role"] == "test":
            out.setdefault(str(ld["arm"]), []).append(ld["windows"]["walk"]["fps"] - base)
    return {a: ("COST" if all(d < -L.T_MIN_FPS for d in ds) else "FREE") for a, ds in out.items()}


def part_a() -> list[tuple[str, bool, str]]:
    res = []

    def expect(name, got, want):
        ok = got == want if not callable(want) else want(got)
        res.append((name, ok, f"got {got!r}"))

    amp = {64: -20.0, 16: -6.0}
    S = L.score(table({}, amp))
    expect("A1 null: x4/x16/x64 FREE", {a: v["verdict"] for a, v in S["walk"]["verdicts"].items()},
           {"4": "FREE", "16": "FREE", "64": "FREE"})
    expect("A1 positive control fired", S["positive_control"]["fired"], True)
    S = L.score(table({64: -20.0, 16: -5.0}, amp))
    expect("A2 effect: x64 COST, x16 COST, x4 FREE", {a: v["verdict"] for a, v in S["walk"]["verdicts"].items()},
           {"4": "FREE", "16": "COST", "64": "COST"})
    S = L.score(table({}, {}))
    expect("A3 no positive control: FREE is UNPROVEN", S["walk"]["verdicts"]["4"]["verdict"],
           lambda v: v.startswith("FREE-UNPROVEN"))
    # A4: a 31-fps regime on ref load 3 (after the first x64, before the first x16) -- both its neighbours drop out
    S = L.score(table({64: -20.0, 16: -5.0}, amp, regime_at={3: (31.0, 29.0)}))
    v = S["walk"]["verdicts"]
    conf = [o for a in ("64", "16") for o in v[a]["occurrences"] if (o.get("why") or "").startswith("regime")]
    expect("A4 regime flip: the bracketing occurrences are flagged, not scored", len(conf), 2)
    expect("A4 regime flip: x64 still COST from its other occurrences", v["64"]["verdict"], "COST")
    # A5: no real effect anywhere, but the launch sits in the 31 regime exactly during the x16 loads (4, 10, 16)
    flip = {4: (31.0, 28.0), 10: (31.0, 28.0), 16: (31.0, 28.0)}
    t5 = table({}, amp, regime_at=flip)
    expect("A5 BROKEN rule is fooled: x16 COST", broken_decide(t5)["16"], "COST")
    expect("A5 real rule is not: x16 never COST", L.score(t5)["walk"]["verdicts"]["16"]["verdict"],
           lambda v: not v.startswith("COST"))
    # A6: render-only -- idle level
    S = L.score(table({}, amp))
    expect("A6 idle: no render cost -> no COST", {a: v["verdict"] for a, v in S["idle_render"]["verdicts"].items()},
           lambda d: all(not x.startswith("COST") for x in d.values()))
    S = L.score(table({}, amp, idle_shift={64: -27.0}))
    expect("A6 idle: x64 drops idle to 31 every time -> COST (regime shift)", S["idle_render"]["verdicts"]["64"]["verdict"],
           lambda v: v.startswith("COST"))
    # A7: the load hitch
    S = L.score(table({}, amp, load_ms={64: 60.0}, load_noise=8.0))
    expect("A7 load: +60 ms at sigma ~8 -> LOAD-COST", S["load"]["verdicts"]["64"]["verdict"], "LOAD-COST")
    S = L.score(table({}, amp, load_ms={64: 60.0}, load_noise=90.0, seed=3))
    expect("A7 load: +60 ms at sigma ~90 -> not LOAD-COST", S["load"]["verdicts"]["64"]["verdict"],
           lambda v: not v.startswith("LOAD-COST"))
    return res


# ================================================================================================ PART B
def part_b() -> list[tuple[str, bool, str]]:
    sys.path.insert(0, str(REPO / "tools"))
    from harness import Session                                    # noqa: E402
    import harness.fakegame as FG                                  # noqa: E402

    game = SCRATCH / "dryrun_game"
    if game.exists():
        shutil.rmtree(game)
    (game / "x64").mkdir(parents=True)
    (game / "x64" / "FF9.exe").write_bytes(b"MZ")
    (game / "x64" / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    (game / "FF9CustomMap").mkdir()
    (game / "FF9CustomMap" / "DictionaryPatch.txt").write_text("FieldScene 6603 11 LANDING LANDING 6603\n",
                                                                encoding="utf-8")
    lab = game / "FF9CustomMap-lab"
    lab.mkdir()
    os.environ.update({"COST_DRYRUN": "1", "COST_LAB": str(lab), "COST_SCRATCH": str(SCRATCH),
                       "COST_SCHEDULE": "1,1,64,1,16,1,4,1,64,1,16,1,4,1", "COST_TICKS": "100",
                       "COST_AMP": "4", "COST_AMP_TICKS": "100", "COST_IDLE_S": "1.2"})
    import cost_session as CS                                      # noqa: E402  (reads the env at import)
    CS.SETTLE_S = 0.4
    CS.LEAD_S = 0.6
    COST = {6.25: 0.003, 6.375: 0.012}                             # injected seconds per tick while walking

    class CostFake(FG.FakeGame):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.ts, self.tag, self.cost_scene = 1.0, None, "FieldMap"

        def _execute(self, step):
            if step and step[0].lower() == "timescale" and len(step) > 1:
                try:
                    self.ts = float(step[1])
                except ValueError:
                    pass
            return super()._execute(step)

        def _step_overworld(self):
            ow = self.overworld
            if ow is not None:
                dt = self._dt or 1.0 / self.render_fps
                ticks = 28.0 * self.ts * dt
                ow["speed"], ow["turn"] = 0.4375 * ticks, 2.8125 * ticks
                if self._is_held("up") and self.world.get("x") is not None and COST.get(self.tag):
                    self.hitch(COST[self.tag] * 28.0 * self.ts / self.render_fps)
            super()._step_overworld()

    fake_box: dict = {}
    orig = FG._publish_atomic

    def patched(path, text, attempts=6, *, mtime=None):
        f = fake_box.get("fake")
        if f is not None:
            d = json.loads(text)
            d["scene"] = f.cost_scene
            text = json.dumps(d)
        return orig(path, text, attempts, mtime=mtime)
    FG._publish_atomic = patched

    def tag_of(path: Path) -> float:
        b = path.read_bytes()
        return round(struct.unpack_from("<f", b, 20 + 4)[0], 4)      # first vertex y (header 20 B, then x y z)

    def world_entry(g, fake, arm, rec):
        rec["t_walkout"] = time.time()
        rec["_mark"] = CS._log_tail_mark(g)
        time.sleep(0.3)
        fake.hitch(0.7)
        time.sleep(0.8)
        fake.cost_scene = "WorldMap"
        time.sleep(0.3)
        extra = 0.06 if arm == 64 else 0.0
        fake.hitch(1.2 + extra + random.gauss(0, 0.006))
        time.sleep(1.35 + extra)
        tag = tag_of(lab / CS.manifest()["rel_path"])
        with open(g.engine_log(), "a", encoding="utf-8") as fh:
            fh.write("07.10.2026 00:00:00 |M| [WorldMeshOverride] loaded 'WorldMap/Disc1/0_1/r1/Block[21][1] Terrain' "
                     f"from {lab.name}/FF9_Data/WorldMap/Disc1/0_1/r1/Block[21][1] Terrain.ff9mesh\n")
        fake.tag = tag
        fake.overworld = {"speed": 0.2, "turn": 1.3, "cam": 37.0, "lag": 3, "height": (lambda x, z, t=tag: t)}
        fake.world.update({"id": 9011, "x": 68.0, "z": -444.0})
        fake.ui_state = "WorldHUD"
        g.wait_world(timeout=20)
        g.world_settle()

    def reach(g, target, arm, rec):
        fake = fake_box["fake"]
        g.newgame(settle=0)
        g.warp(6603)
        rec["swap"] = CS.swap(target, arm)
        world_entry(g, fake, arm, rec)

    def reload(g, target, arm, rec):
        fake = fake_box["fake"]
        g.state_every(2)
        g.world_warp(6603)
        fake.cost_scene = "FieldMap"
        rec["swap"] = CS.swap(target, arm)
        world_entry(g, fake, arm, rec)

    CS.HOOKS.update(reach=reach, reload=reload)
    fake = CostFake(game, publish=("mtime",), render_fps=60.0)
    fake_box["fake"] = fake
    t0 = time.time()
    with Session(game_path=game, run_dir=game / "run", save_dir=game / "player-saves", pid_probe=lambda: [],
                 launcher=lambda exe: fake.start(), boot_timeout=15.0, verbose=False) as g:
        CS.run(g)
        checks = [(c.get("what"), bool(c.get("ok")), c.get("detail", "")) for c in _checks_of(g)]
    FG._publish_atomic = orig
    rec = json.loads((game / "run" / "cost_session.json").read_text(encoding="utf-8"))
    S = rec["score"]
    out = [("B0 session ran end to end", rec.get("completed", False), f"{time.time() - t0:.0f} s")]
    walk = {a: v["verdict"] for a, v in S["walk"]["verdicts"].items()}
    out.append(("B1 x64 COST, x16 COST, x4 FREE", walk == {"64": "COST", "16": "COST", "4": "FREE"}, f"{walk}"))
    out.append(("B2 positive control fired", S["positive_control"]["fired"], f"{S['positive_control']}"))
    lv = {a: v["verdict"] for a, v in S["load"]["verdicts"].items()}
    out.append(("B3 x64 LOAD-COST (+60 ms injected)", lv.get("64") == "LOAD-COST", f"{S['load']}"))
    binds = [(ld["arm"], ld.get("arm_y"), ld.get("arm_ok")) for ld in rec["loads"]]
    out.append(("B4 every load bound its arm (height tag)", all(b[2] for b in binds), f"{binds}"))
    circ = [(ld["windows"].get("walk") or {}).get("circle") for ld in rec["loads"] if ld["role"] != "warm"]
    out.append(("B5 circle fitted on every load, centred on C", all(c and abs(c["cx"] - CS.CENTRE[0]) < 1.5
                                                                     and abs(c["cz"] - CS.CENTRE[1]) < 1.5 for c in circ),
                f"cal {rec.get('calibration')}; first {circ[:2]}"))
    for name, ok, det in checks:
        out.append((f"B-session check: {name}", ok, str(det)[:160]))
    return out


def _checks_of(g):
    for attr in ("checks", "_checks"):
        v = getattr(g, attr, None)
        if isinstance(v, list):
            return [c if isinstance(c, dict) else getattr(c, "__dict__", {"description": str(c)}) for c in v]
    return []


def main(argv) -> int:
    part = argv[argv.index("--part") + 1] if "--part" in argv else "ab"
    rows = []
    if "a" in part:
        rows += part_a()
    if "b" in part:
        rows += part_b()
    bad = 0
    for name, ok, det in rows:
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}  -- {det}")
    print(f"\n{len(rows) - bad}/{len(rows)} passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
