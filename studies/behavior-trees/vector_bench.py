"""THE PILGRIMAGE — vector-substrate RUNG 0 in-game (field 30416, hot reload).

The v2 scoping named THE VECTOR SUBSTRATE the headline (group-looped logic over
gScriptVector state — kills the band/ticker/file walls at once). Its ONE
unproven bytecode composition is the scan loop: a bounded backward-jump loop
INSIDE the ticker whose reads AND writes index vector cells by the LIVE loop
byte. Every ingredient ran on BTTABLE (computed-index reads, constant-index
writes, seeding, OOB fail-soft); the composition never has. This bench runs
exactly that and nothing else new.

THE GAME: eight pilgrims set out from the west plaza at staggered speeds and
march to the SHRINE (the east pocket, where the abbot stands). Each ticker
pass, `[[behavior.scan]]` copies all eight position mirrors into px/pz tables,
then LOOPS: writes each pilgrim's inside-the-ring flag into the near table BY
LOOP INDEX, reads it back, and accumulates the headcount into the `at_shrine`
counter. The abbot announces at 1 / 4 / 8 — numbers derived ENTIRELY through
the loop's computed-index write-then-read round trip, so a mis-indexed cell
breaks the announced count instead of passing silently.

WHAT A PASS LOOKS LIKE:
  * each announce fires when that many pilgrims VISIBLY stand in the shrine
    ring (count the actors on screen — that IS the verification);
  * "ALL EIGHT" fires only once the last pilgrim arrives, and never early;
  * no freeze at any point (a CalcStack fault in the loop = the ticker dies);
  * ~ -> Reload restarts the procession clean (tables re-seed).

Deploys OVER the ISLES slot (30416, already registered — the DictionaryPatch
line is kept IDENTICAL on purpose: same id, same registered name, same text
block -> ZERO RELAUNCH; ~ -> Warp -> 30416 or Reload is enough).

Usage (repo root):  py studies/behavior-trees/vector_bench.py gen | probe | deploy
Revert: py tools/scroll_out/revert_deploy_30416.py
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

BENCH = Path("C:/gd/_isles_bench")       # same donor import as ISLES (reused)
BASE_TOML = BENCH / "LDBM_NATIVE.field.toml"
BENCH_TOML = BENCH / "VECTOR.field.toml"
REPORT = BENCH / "vector-report.txt"
FIELD_ID = 30416
FIELD_NAME = "ISLES"                     # keep the REGISTERED name -> no relaunch
MOD_FOLDER = "FF9CustomMap"
DONOR = "fbg_n11_ldbm_map158_lb_plz_0"                            # 559, yaw-0 plaza

PILGRIM_MODEL = "GEO_NPC_F0_CSO"
ABBOT_MODEL = "GEO_NPC_F2_CSO"

N = 8
PILGRIMS = [f"pg{i}" for i in range(N)]
SPEEDS = [25, 30, 35, 40, 45, 50, 55, 60]          # the arrival stagger
RING_R_CAP = 520                                   # scan box ceiling (Chebyshev)


# --------------------------------------------------------------- walkmesh helpers
def read_spawn() -> tuple[int, int]:
    m = re.search(r"(?m)^spawn = \[(-?\d+), (-?\d+)\]",
                  BASE_TOML.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("no [player] spawn in the base toml")
    return int(m.group(1)), int(m.group(2))


def lattice():
    """The proven anchor filter (condor/ISLES verbatim): spawn's CONNECTED
    COMPONENT + 400u height band + >=120u wall clearance."""
    mesh = BgiWalkmesh.from_bytes((BENCH / "walkmesh.bgi").read_bytes())
    wv = mesh.world_verts()
    spawn = read_spawn()
    tri_pts = [tuple(wv[i] for i in t.vtx) for t in mesh.tris]
    seeds = [ti for ti, (a, b, c) in enumerate(tri_pts)
             if _pt_in_tri_xz(spawn[0], spawn[1], a, b, c)]
    if not seeds:
        raise SystemExit(f"spawn {spawn} is on no tri — mesh read wrong?")
    spawn_y = sum(v[1] for v in tri_pts[seeds[0]]) / 3.0
    comp: set = set()
    stack = list(seeds)
    while stack:
        ti = stack.pop()
        if ti in comp:
            continue
        cy = sum(v[1] for v in tri_pts[ti]) / 3.0
        if abs(cy - spawn_y) > 400:
            continue
        comp.add(ti)
        for nb in mesh.tris[ti].nbr:
            if nb >= 0 and nb not in comp:
                stack.append(nb)
    tris = [tri_pts[ti] for ti in comp]
    xs = [v[0] for tri in tris for v in tri]
    zs = [v[2] for tri in tris for v in tri]

    def on_mesh(x, z):
        return any(_pt_in_tri_xz(x, z, a, b, c) for a, b, c in tris)

    pts = []
    for z in range(int(min(zs)) + 250, int(max(zs)) - 249, 200):
        for x in range(int(min(xs)) + 250, int(max(xs)) - 249, 200):
            if on_mesh(x, z):
                pts.append((x, z))
    if len(pts) < 60:
        raise SystemExit(f"only {len(pts)} lattice points in the spawn component")
    from ff9mapkit.scene import routes as _routes

    class _NS:
        def world_verts(self):
            return wv
        tris = [t for i, t in enumerate(mesh.tris) if i in comp]
    bedges = _routes.mesh_boundary_edges(_NS())

    def _clear(p, r=120.0):
        px, pz = float(p[0]), float(p[1])
        for (ax, az), (bx, bz) in bedges:
            vx, vz = bx - ax, bz - az
            L2 = vx * vx + vz * vz
            t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * vx + (pz - az) * vz) / L2))
            dx, dz = px - (ax + t * vx), pz - (az + t * vz)
            if dx * dx + dz * dz < r * r:
                return False
        return True

    clear = [p for p in pts if _clear(p)]
    return pts, (clear if len(clear) >= 30 else pts)


def nearest(pts, x, z, used=None):
    cands = [p for p in pts if used is None or p not in used]
    p = min(cands, key=lambda q: (q[0] - x) ** 2 + (q[1] - z) ** 2)
    if used is not None:
        used.add(p)
    return p


def layout() -> dict:
    _pts, clear = lattice()
    used: set = set()
    shrine = nearest(clear, 2050, -100, used)
    sx, sz = shrine
    # the ring: the 8 NEAREST clear points — the box radius is DERIVED from the
    # picks (+80u margin), so the scan box always contains every post exactly;
    # a pocket too cramped to hold 8 posts under the cap fails loudly instead
    ring = sorted((p for p in clear if p not in used),
                  key=lambda q: max(abs(q[0] - sx), abs(q[1] - sz)))[:N]
    used.update(ring)
    ring_r = max(max(abs(p[0] - sx), abs(p[1] - sz)) for p in ring) + 80
    if ring_r > RING_R_CAP:
        raise SystemExit(f"ring radius {ring_r} > {RING_R_CAP} — the shrine pocket "
                         f"is too cramped for 8 posts; move the shrine anchor")
    lay = {"spawn": read_spawn(), "shrine": shrine, "ring": ring, "ring_r": ring_r,
           # the western staging line (the old mu arc zone)
           "start": [nearest(clear, -1000, -1400 + 400 * i, used) for i in range(N)],
           "abbot": nearest(clear, 1153, -800, used),
           # the shared lane east along the south edge (snapped; route="auto"
           # re-routes any leg the sweep finds off-mesh)
           "lane": [nearest(clear, *p) for p in
                    [(-2500, -1700), (-800, -1050), (450, -800), (1300, -450)]]}
    return lay


# --------------------------------------------------------------- TOML emit helpers
def _t(v) -> str:
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
    sx, sz = lay["shrine"]
    parts = ['\n[behavior]\nwarmup = 45\ncounters = ["at_shrine"]\n'
             f'\n[[behavior.scan]]\nname = "pilgrims"\n'
             f"units = {_t(PILGRIMS)}\n"
             f"point = [{sx}, {sz}]\nradius = {lay['ring_r']}\n"
             f'count = "at_shrine"\nflags = "near_shrine"\n']
    for i, name in enumerate(PILGRIMS):
        start = lay["start"][i]
        post = lay["ring"][i]
        route = [list(start)] + [list(p) for p in lay["lane"]] + [list(post)]
        parts.append(f'\n[[behavior.unit]]\nnpc = "{name}"\nspeed = {SPEEDS[i]}\n')
        parts.append(_branch(do={"march": route, "route": "auto",
                                 "arrive_r": 120, "speed": SPEEDS[i]}))
    ax, az = lay["abbot"]
    parts.append('\n[[behavior.unit]]\nnpc = "abbot"\nspeed = 30\n')
    parts.append(_branch(when=[{"counter_ge": ["at_shrine", 8]}], once="all8",
                         do={"announce": "ALL EIGHT accounted for — the vector"
                                         " roll call is TRUE, kupo!"}))
    parts.append(_branch(when=[{"counter_ge": ["at_shrine", 4]}], once="four",
                         do={"announce": "Four pilgrims stand in the shrine ring."}))
    parts.append(_branch(when=[{"counter_ge": ["at_shrine", 1]}], once="first",
                         do={"announce": "The first pilgrim reaches the shrine."}))
    parts.append(_branch(do={"hold": [ax, az]}))
    return "".join(parts)


# --------------------------------------------------------------- gen / probe / deploy
def _dry_build(parts: list):
    import tomllib
    raw = tomllib.loads("".join(parts))
    problems = BT.validate(raw)
    if problems:
        raise SystemExit("behavior validate:\n  " + "\n  ".join(problems))
    all_units = [u["npc"] for u in raw["behavior"]["unit"]]
    txids = {(ui, bi): 900 + 10 * ui + bi for ui, bi, _ in BT.announce_lines(raw)}
    routed = None
    if BT.wants_autoroute(raw):
        wmesh = BgiWalkmesh.from_bytes((BENCH / "walkmesh.bgi").read_bytes())
        routed = BT.autoroute_plan(raw, wmesh)
        for line in BT.describe_autoroute(routed, raw):
            print("  route:", line)
    fb = BT.build(raw, npc_slots={n: i + 2 for i, n in enumerate(all_units)},
                  npc_txids_by_name={n.get("name"): 0 for n in raw.get("npc", [])},
                  behavior_txids=txids, routed=routed)
    cb = fb.compile()
    print(f"  ticker {len(cb.ticker_body)} B  main_init {len(cb.main_init)} B")
    for line in cb.size_report().splitlines():
        print(" ", line)
    return raw, fb, cb


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
    text = re.sub(r"(?ms)^\[\[gateway\]\].*?(?=^\[|\Z)", "", text)   # a closed room
    blocks = re.split(r"(?m)(?=^\[)", text)                          # clear the stage
    text = "".join(b for b in blocks
                   if not (b.startswith("[[object]]") and 'kind = "npc"' in b))

    lay = layout()
    parts = [text, "\n# ---- THE PILGRIMAGE (generated by "
                   "studies/behavior-trees/vector_bench.py) ----\n"]
    for i, name in enumerate(PILGRIMS):
        x, z = lay["start"][i]
        parts.append(f'\n[[npc]]\nname = "{name}"\nmodel = "{PILGRIM_MODEL}"\n'
                     f'pos = [{x}, {z}]\nface = 192\n'
                     f'dialogue = "To the shrine, at my own pace."\n')
    ax, az = lay["abbot"]
    parts.append(f'\n[[npc]]\nname = "abbot"\nmodel = "{ABBOT_MODEL}"\n'
                 f'pos = [{ax}, {az}]\n'
                 f'dialogue = "I count the faithful by the table, not by eye —'
                 f' watch the tally hold true."\n')
    parts.append(behavior_toml(lay))

    _raw, fb, cb = _dry_build(parts)
    if not fb._scans or "scan pilgrims" not in cb.report:
        raise SystemExit("BENCH INVALID: the scan did not compile in")
    BENCH_TOML.write_text("".join(parts), encoding="utf-8")
    REPORT.write_text(cb.report, encoding="utf-8")
    print(f"wrote {BENCH_TOML}")
    print(f"  shrine {lay['shrine']}  ring {lay['ring']}")
    print(f"  starts {lay['start'][0]}..{lay['start'][-1]}  abbot {lay['abbot']}")
    print(f"  report -> {REPORT}")


def probe() -> None:
    if not BENCH_TOML.exists():
        gen()
    r = subprocess.run([sys.executable, str(REPO / "tools" / "field_layout_probe.py"),
                        str(BENCH_TOML), "--out",
                        str(REPO / "tools/scroll_out/layout_probe/vector")])
    if r.returncode != 0:
        raise SystemExit("probe failed")


def deploy() -> None:
    if not BENCH_TOML.exists():
        gen()
    r = subprocess.run([sys.executable, str(REPO / "tools" / "deploy_field.py"),
                        str(BENCH_TOML), "--id", str(FIELD_ID), "--name", FIELD_NAME,
                        "--text-block", str(FIELD_ID), "--mod-folder", MOD_FOLDER])
    if r.returncode != 0:
        raise SystemExit("deploy_field failed")
    print(f"""
PLAYTEST (30416 again — registered line unchanged, so NO relaunch:
~ -> Warp -> {FIELD_ID}, or Reload if already there):
  THE POINT: the scan loop — vector reads AND writes indexed by a LIVE loop
  byte, every tick — is the one v2 composition never run in-game. The abbot's
  numbers come ENTIRELY through that loop, so counting actors on screen IS the
  verification:
  1 after the ~4s warm-up, eight pilgrims set out east at different paces;
  2 "The first pilgrim reaches the shrine." — exactly when the lead pilgrim
    enters the shrine ring (the east pocket, by the abbot);
  3 "Four pilgrims stand in the shrine ring." — when the count on screen is 4;
  4 "ALL EIGHT accounted for" — only once the slowest arrives, never early;
  5 no freeze anywhere (a loop-indexing fault kills the ticker = field frozen);
  6 ~ -> Reload restarts the procession; the ladder fires again from step 2.
  (The registered name still reads ISLES on purpose — same slot, zero relaunch.)
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("verb", choices=["gen", "probe", "deploy"])
    v = ap.parse_args().verb
    {"gen": gen, "probe": probe, "deploy": deploy}[v]()
