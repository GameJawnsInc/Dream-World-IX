"""Rung 4 — THE SHOWCASE ON THE PRODUCT SURFACE (behavior-trees study).

The SAME raid that rung 3 proved (field **30412** "BTRAID"), re-expressed entirely as
the kit's **[behavior] TOML** — this bench no longer patches bytecode at all:

    gen    -> writes BTRAID.field.toml with a [behavior] table (units bind to the
              [[npc]] rows by name; patrol/march verbs reference the SAME probe-swept
              [[marker]] path= routes the layout probe verifies; announce_npc reuses
              each speaker's own dialogue line)
    deploy -> plain tools/deploy_field.py — `ff9mapkit build` compiles + installs the
              trees natively (build_script's [behavior] tail). No discovery, no
              post-patch, no bench-only machinery: WHAT SHIPS IS THE PRODUCT PATH.

The scene (identical to the rung-3 proof): patrol-shift guards trading the monument
circuit and the west-court beat on one alternator clock; the gate watchman whose
once-ever cry raises "alarm" when EITHER bandit closes (the any_near watcher verb);
the two-lane bandit march (west gatehouse rush + the long east second wave, as
March verbs on the swept route markers); mid-fight flees to the market at 1 hp; the
captain's war cry + double-damage stand at the keep; the panicking Wander/Flee
civilian. The lever arms `raid` (a [behavior] public flag — its allocated index is
computed at gen and wired into the [[choice]] set_flag row).

Usage (repo root):  py studies/behavior-trees/btraid_bench.py gen | deploy
After a deploy: ~ -> Reload field (RELAUNCH only if 30412 was never registered).
Revert: py tools/scroll_out/revert_deploy_30412.py
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit.content import behaviortoml as BT                  # noqa: E402
from ff9mapkit.scene.bgi import BgiWalkmesh, _pt_in_tri_xz        # noqa: E402

BENCH = Path("C:/gd/_btraid_bench")
BASE_TOML = BENCH / "LDBM_NATIVE.field.toml"
BENCH_TOML = BENCH / "BTRAID.field.toml"
REPORT = BENCH / "behavior-report.txt"
FIELD_ID = 30412
FIELD_NAME = "BTRAID"
MOD_FOLDER = "FF9CustomMap"
DONOR = "fbg_n11_ldbm_map158_lb_plz_0"

CAST = [
    ("watchman", "GEO_NPC_F0_CSO", "Bandits at the gate!  Sound the alarm!"),
    ("guard0",   "GEO_NPC_F0_CSO", "Patrol shift's almost done."),
    ("guard1",   "GEO_NPC_F0_CSO", "Keep to your route."),
    ("captain",  "GEO_NPC_F2_CSO", "To arms!  Not one step past the keep!"),
    ("bandit0",  "GEO_MON_F0_FFG", "The keep is ours!"),
    ("bandit1",  "GEO_MON_F0_FFG", "Nothing left to stop us!"),
    ("civilian", "GEO_NPC_F0_JJY", "Oh dear, oh dear..."),
]
CONTACT, STANDOFF = 300, 180


# --------------------------------------------------------------- layout (probe-driven)
def read_spawn() -> tuple[int, int]:
    m = re.search(r"(?m)^spawn = \[(-?\d+), (-?\d+)\]", BASE_TOML.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("no [player] spawn in the base toml")
    return int(m.group(1)), int(m.group(2))


def lattice(min_clear: float = 100.0) -> list[tuple[int, int]]:
    """On-mesh grid points at least ``min_clear`` from any walkmesh boundary edge —
    probe round 2's lesson: a bare on-mesh test accepts 1u edge slivers (the market
    landed on one), and walkers shoved by the 48u collision radius drift off any
    line that hugs a wall. Snap targets only to CLEAR points."""
    from ff9mapkit.scene import routes as R
    mesh = BgiWalkmesh.from_bytes((BENCH / "walkmesh.bgi").read_bytes())
    wv = mesh.world_verts()
    idx_tris = [tuple(t.vtx) for t in mesh.tris]
    tris = [tuple(wv[i] for i in t) for t in idx_tris]
    xs, zs = [v[0] for v in wv], [v[2] for v in wv]
    bedges = R.boundary_edges_xz(wv, idx_tris)

    def clear(x, z):
        return (any(_pt_in_tri_xz(x, z, a, b, c) for a, b, c in tris)
                and min(R.seg_dist_xz(x, z, e0, e1) for e0, e1 in bedges) >= min_clear)

    pts = []
    for z in range(int(min(zs)) + 300, int(max(zs)) - 299, 250):
        for x in range(int(min(xs)) + 300, int(max(xs)) - 299, 250):
            if clear(x, z):
                pts.append((x, z))
    if len(pts) < 30:
        raise SystemExit(f"only {len(pts)} clear lattice points")
    return pts


def nearest(pts, x, z):
    return min(pts, key=lambda p: (p[0] - x) ** 2 + (p[1] - z) ** 2)


def layout() -> dict:
    pts = lattice()
    lay = {
        "spawn": read_spawn(),
        "keep": nearest(pts, -2250, 2250),
        # the GATEHOUSE = the neck between the plaza and the NW keep arm: every
        # keep-bound walk routes THROUGH it (probe round 2: straight lines to the
        # keep from anywhere south clip the bay west of the neck)
        "gatehouse": nearest(pts, -1391, 900),
        "watch_post": nearest(pts, -1050, -1300),
        "camp0": nearest(pts, -450, -1750),
        "camp1": nearest(pts, -850, -1780),
        "market": nearest(pts, -1641, 150),
        "safehouse": nearest(pts, -1891, -1600),   # sweep-picked: the ONE straight
                                                   # market->SW line with no off-mesh
                                                   # nick (7u parallel wall slide)
        "east_nook": nearest(pts, -500, 600),
        # routeA = THE MONUMENT CIRCUIT (probe round 1: the old outer ring's west and
        # north legs crossed off-mesh notches — guards stalled in 2 places; the field
        # is a donut around the central monument, so the outer patrol IS the donut).
        # Six corners: the hole bulges west to ~x-850 at its waist (probe round 2),
        # so the west side detours through the court's clear column at x-1141.
        "routeA": [nearest(pts, *p) for p in
                   [(-891, 1150), (1109, 1150), (1109, -850), (-891, -850),
                    (-1141, -100), (-1141, 400)]],
        # routeB = the west-court beat. The court's north half is cluttered (interior
        # notches); the z=500 chord is the SWEPT best (14u) — raw sweep-verified
        # points, deliberately NOT lattice-snapped
        "routeB": [(-1641, 500), (-1141, 500), (-1141, -100), (-1891, -100)],
    }
    for ring in ("routeA", "routeB"):
        if len(set(lay[ring])) != len(lay[ring]):
            raise SystemExit(f"{ring} collapsed: {lay[ring]}")
    if lay["camp0"] == lay["camp1"]:
        raise SystemExit("bandit camps collapsed onto one lattice point")
    return lay


def spawn_of(lay: dict) -> dict:
    # visual start = each unit's initial duty (shift flag starts 0: guard0 walks the
    # INNER ring first, guard1 — not_flag — the outer)
    return {"watchman": lay["watch_post"], "guard0": lay["routeB"][0],
            "guard1": lay["routeA"][0], "captain": lay["keep"],
            "bandit0": lay["camp0"], "bandit1": lay["camp1"],
            "civilian": lay["market"]}


# --------------------------------------------------------------- the [behavior] TOML
def _t(v) -> str:
    """A TOML value: point tuples/lists nest, strings quote, dicts inline."""
    if isinstance(v, str):
        return f'"{v}"'
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_t(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {_t(x)}" for k, x in v.items()) + " }"
    return str(v)


def _branch(when=None, do=None, **keys) -> str:
    out = ["\n  [[behavior.unit.branch]]"]
    if when:
        out.append("  when = [" + ", ".join(_t(c) for c in when) + "]")
    out.append("  do = " + _t(do))
    for k, v in keys.items():
        out.append(f"  {k} = {_t(v)}")
    return "\n".join(out) + "\n"


def behavior_toml(lay: dict) -> str:
    """The whole raid as the kit's [behavior] surface — the rung-3-proven trees,
    branch for branch (flat priority form; the nested alarm selector distributes
    into per-branch condition prefixes)."""
    alarm = {"flag": "alarm"}
    raid = {"flag": "raid"}
    bandits_up = {"any_active": ["bandit0", "bandit1"]}
    parts = ['\n[behavior]\nwarmup = 45\n'
             'alternators = [{ name = "shift", frames = 400 }]\n'
             'public_flags = ["raid"]\n']

    def unit(name, hp=None, speed=40):
        parts.append(f'\n[[behavior.unit]]\nnpc = "{name}"\n'
                     + (f"hp = {hp}\n" if hp is not None else "") + f"speed = {speed}\n")

    # watchman: the once-ever cry (raid-gated any_near notice) -> fall back to market
    unit("watchman")
    parts.append(_branch(when=[raid, {"any_near": [["bandit0", "bandit1"], 450]}],
                         do={"announce_npc": "watchman"},
                         once="cry", raise_flags=["alarm"]))
    parts.append(_branch(when=[alarm],
                         do={"march": "watch_run", "arrive_r": 250, "speed": 70}))
    parts.append(_branch(do={"hold": "watch_post"}))

    # guards: die -> flee at 1 hp -> alarm combat -> the traded patrol shifts
    for g, shift_cond in (("guard0", {"flag": "shift"}), ("guard1", {"not_flag": "shift"})):
        unit(g, hp=(5 if g == "guard0" else 3))
        parts.append(_branch(when=[{"hp_le": 0}], do={"die": True}))
        parts.append(_branch(when=[{"hp_le": 1}],
                             do={"flee": "bandit1", "to": ["market", "east_nook"],
                                 "avoid_r": 600, "speed": 75}))
        for b in ("bandit0", "bandit1"):
            parts.append(_branch(when=[alarm, {"active": b}, {"near": [b, CONTACT]}],
                                 do={"swing_at": b}))
        for b in ("bandit0", "bandit1"):
            parts.append(_branch(when=[alarm, {"active": b}, {"near": [b, 900]}],
                                 do={"chase": b, "standoff": STANDOFF, "speed": 65}))
        parts.append(_branch(when=[alarm, bandits_up],
                             do={"walk_to": "gatehouse", "speed": 65}))
        parts.append(_branch(when=[shift_cond], do={"patrol": "ringA", "arrive_r": 150}))
        parts.append(_branch(do={"patrol": "ringB", "arrive_r": 150}))

    # captain: the keep's boss — double-damage duels; the war cry drawn at 1000
    unit("captain", hp=6)
    parts.append(_branch(when=[{"hp_le": 0}], do={"die": True}))
    for b in ("bandit0", "bandit1"):
        parts.append(_branch(when=[alarm, {"active": b}, {"near": [b, CONTACT]}],
                             do={"swing_at": b, "damage": 2}))
    parts.append(_branch(when=[alarm, bandits_up,
                               {"any_near": [["bandit0", "bandit1"], 1000]}],
                         do={"announce_npc": "captain"}, once="warcry"))
    parts.append(_branch(do={"hold": "keep"}))

    # bandits: THE TWO LANES — March on the probe-swept route markers (each starts
    # at its own camp, so waypoint 0 is an instant arrival)
    for i, b in enumerate(("bandit0", "bandit1")):
        unit(b, hp=(4 if b == "bandit0" else 6))
        parts.append(_branch(when=[{"hp_le": 0}], do={"die": True}))
        for foe in ("captain", "guard0", "guard1"):
            parts.append(_branch(when=[raid, {"active": foe}, {"near": [foe, CONTACT]}],
                                 do={"swing_at": foe}))
        parts.append(_branch(when=[raid, {"near_point": ["keep", 300]}],
                             do={"announce_npc": b}, once=f"gloat{i}"))
        parts.append(_branch(when=[raid],
                             do={"march": f"march{i}", "arrive_r": 250, "speed": 55}))
        parts.append(_branch(do={"hold": f"camp{i}"}))

    # civilian: ambles (Wander) -> panics (Flee) -> ambles again postwar
    unit("civilian", speed=40)
    parts.append(_branch(when=[alarm, bandits_up],
                         do={"flee": "bandit0", "to": ["safehouse", "east_nook"],
                             "avoid_r": 600, "speed": 80}))
    parts.append(_branch(do={"wander": "market", "radius": 500, "every": 110,
                             "speed": 30}))
    return "".join(parts)


# --------------------------------------------------------------- gen / deploy
def gen() -> None:
    if not BASE_TOML.exists():
        print(f"importing donor {DONOR} ...")
        r = subprocess.run([sys.executable, "-m", "ff9mapkit", "import", DONOR,
                            "--native", "--out", str(BENCH)], cwd=REPO / "ff9mapkit")
        if r.returncode != 0:
            raise SystemExit("donor import failed")
    text = BASE_TOML.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^text_block = \d+", f"text_block = {FIELD_ID}", text)
    text = re.sub(r"(?m)^id = \d+", f"id = {FIELD_ID}", text)
    text = re.sub(r'(?m)^name = "[^"]+"', f'name = "{FIELD_NAME}"', text)
    text = re.sub(r"(?ms)^\[\[gateway\]\].*?(?=^\[|\Z)", "", text)

    lay = layout()
    posts = spawn_of(lay)
    parts = [text, "\n# ---- BT RAID BENCH (generated by btraid_bench.py; rung 4 = "
                   "the [behavior] TOML surface) ----\n"]
    for name, geo, line in CAST:
        x, z = posts[name]
        parts.append(f'\n[[npc]]\nname = "{name}"\nmodel = "{geo}"\n'
                     f'pos = [{x}, {z}]\ndialogue = "{line}"\n')

    # named points + probe-swept ROUTE markers — patrol/march verbs reference these
    # by name, so the swept line IS the deployed behavior data
    for name in ("keep", "gatehouse", "market", "safehouse", "east_nook",
                 "watch_post", "camp0", "camp1"):
        x, z = lay[name]
        parts.append(f'\n[[marker]]\nname = "{name}"\npos = [{x}, {z}]\n')

    def route(name: str, points: list, closed: bool = False) -> str:
        pp = ", ".join(f"[{x}, {z}]" for x, z in points)
        x0, z0 = points[0]
        return (f'\n[[marker]]\nname = "{name}"\npos = [{x0}, {z0}]\n'
                f"path = [{pp}]\nclosed = {'true' if closed else 'false'}\n")

    parts.append(route("ringA", lay["routeA"], closed=True))
    parts.append(route("ringB", lay["routeB"], closed=True))
    parts.append(route("march0", [posts["bandit0"], (859, -850), (1109, 1150),
                                  (-891, 1150), lay["gatehouse"], lay["keep"]]))
    parts.append(route("march1", [posts["bandit1"], lay["gatehouse"], lay["keep"]]))
    parts.append(route("panic", [lay["market"], lay["safehouse"]]))
    parts.append(route("gflee", [lay["routeA"][4], lay["market"]]))
    parts.append(route("watch_run", [lay["watch_post"], (-1141, -100), lay["market"]]))

    parts.append(behavior_toml(lay))

    # the lever wires to the behavior's `raid` public flag — its index is
    # deterministic (allocation order = the unit roster), computed by a dry build
    import tomllib
    raw = tomllib.loads("".join(parts))
    problems = BT.validate(raw)
    if problems:
        raise SystemExit("behavior validate:\n  " + "\n  ".join(problems))
    fb = BT.build(raw, npc_slots={n: i + 2 for i, (n, _g, _l) in enumerate(CAST)},
                  npc_txids_by_name={n: 0 for n, _g, _l in CAST},
                  behavior_txids={})
    raid = fb.public_flag("raid")

    cx, cz = lay["spawn"]
    h = 220
    parts.append(
        f'\n[[choice]]\nzone = [[{cx - h},{cz + h}],[{cx + h},{cz + h}],'
        f'[{cx + h},{cz - h}],[{cx - h},{cz - h}]]\n'
        f'prompt = "Raid bench: loose the bandits?"\ninstant = true\n'
        f'\n[[choice.options]]\ntext = "Begin the raid"\n'
        f'reply = "Torches on the ridge..."\nset_flag = [{raid}, 1]\n'
        f'\n[[choice.options]]\ntext = "Not yet."\n')
    BENCH_TOML.write_text("".join(parts), encoding="utf-8")
    print(f"wrote {BENCH_TOML}\n  layout {lay}\n  raid flag {raid}")


def deploy() -> None:
    if not BENCH_TOML.exists():
        gen()
    r = subprocess.run([sys.executable, str(REPO / "tools" / "deploy_field.py"),
                        str(BENCH_TOML), "--id", str(FIELD_ID), "--name", FIELD_NAME,
                        "--text-block", str(FIELD_ID), "--mod-folder", MOD_FOLDER])
    if r.returncode != 0:
        raise SystemExit("deploy_field failed")
    # the report (the ~ Flags watch map) from a dry compile of the same toml
    import tomllib
    raw = tomllib.loads(BENCH_TOML.read_text(encoding="utf-8"))
    fb = BT.build(raw, npc_slots={n: i + 2 for i, (n, _g, _l) in enumerate(CAST)},
                  npc_txids_by_name={n: 0 for n, _g, _l in CAST},
                  behavior_txids={(ui, bi): 0 for ui, bi, _ in BT.announce_lines(raw)})
    report = fb.compile().report
    REPORT.write_text(report + "\n(entry slots + txids here are dry-run placeholders; "
                      "the deployed build bound the real ones)\n", encoding="utf-8")
    print(f"\n{report}\n\nreport saved -> {REPORT}")
    print(f"""
PLAYTEST (rung 4: the SAME raid, now built from [behavior] TOML by `ff9mapkit build`
— zero bench bytecode patching): ~ -> Reload field, then the rung-3 script:
  patrol-shift ring trades -> lever -> two-lane march -> the one-time cry + panic ->
  the gatehouse battle, 1-hp flees to the market -> the captain's stand -> aftermath.
  If ANYTHING differs from round 3, that's a product-surface bug — report it.
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "deploy"])
    (gen if ap.parse_args().cmd == "gen" else deploy)()


if __name__ == "__main__":
    main()
