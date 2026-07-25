"""RUNG 5 — THE FORT CONDOR FIT (field 30400 rebuilt on the ratified design).

Owner-ratified (2026-07-25): LEAN-3 roster (Soldier / Shooter / Defender, own
stats + gil price each) · 20-ally cap across pools at FFVII-band prices · win
pays GIL + AN ITEM · the plaza siege layout: the DEPOT (the base to defend) on
the EAST side, east of the center block; waves enter at the NORTHWEST and
SOUTHWEST entrances on authored paths; the two chokepoints sit north and south
of the monument. (This field's camera is yaw-0: screen directions ARE world
cardinals — probe-verified.)

The whole thing is `[behavior]` TOML + plain deploy_field — the data-table wave
clock (sched = DATA), pooled hires at your feet, the published HIREABLE flags
(a hire row you can see is a hire that will succeed), and the new `award` verb
(exactly-once payouts riding the event-Once lane) — every mechanism previously
★ proven on benches 30410-30415, composed.

THE GAME (round-2 TUNING clock — 1:00 runs, a wave every ~20s):
  ~boot      the city fronts you a 3000-gil WAR STIPEND (award #1, kupo).
  anywhere   press SELECT/SPECIAL -> the WAR COUNCIL menu -> hire where you
             STAND (that spot becomes the unit's post): Soldier 300g /
             Shooter 550g / Defender 450g (6/4/4 this build). Rows VANISH when
             unaffordable or sold out (the hireable flags) — the menu can
             never take an order it won't fill.
  0:55       wave 1 — 2 Mus in from the NORTHWEST street.
  0:40       wave 2 — 2 Mus in from the SOUTHWEST gate.
  0:20       wave 3 — 2 Fang HEAVIES from the southwest.
  raiders    march their lane, squeeze the chokepoint, and — NEW, THE PIN —
             STAND AND FIGHT while a Soldier is on them (no more jogging away
             from their attackers), then resume the march if they shake free.
             Leakers beat on the DEPOT (hp 24). Soldiers chase the Mus,
             Shooters shell everything within 600u, Defenders grind the
             southwest pressure.
  0:00       depot alive = WE HELD: the win cry + the purse (2000 gil + a
             Phoenix Down, exactly once).
  depot dead = the raiders' boss fight (a REAL battle), then the field mourns.
  (The ratified 20-ally cap and raider COUNTER-damage return with the labelasm
  long-jump pass — this build ships 14 allies under the ~32KB ticker ceiling.)

Usage (repo root):  py studies/fort-condor/condor_fit_bench.py gen | probe | deploy
30400 is long registered -> ~ -> Reload field is enough after deploy.
Revert: py tools/scroll_out/revert_deploy_30400.py
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

BENCH = Path("C:/gd/_condor_fit")
BASE_TOML = BENCH / "LDBM_NATIVE.field.toml"
BENCH_TOML = BENCH / "CONDOR.field.toml"
REPORT = BENCH / "behavior-report.txt"
FIELD_ID = 30400
FIELD_NAME = "CONDOR"
MOD_FOLDER = "FF9CustomMap"
DONOR = "fbg_n11_ldbm_map158_lb_plz_0"                            # 559, yaw-0 plaza

BASE_MODEL = "GEO_NPC_F4_CSO"            # the depot master (the thing to defend)
QM_MODEL = "GEO_NPC_F2_CSO"              # flavor: explains the war council
SOLDIER_MODEL = "GEO_NPC_F0_CSO"
SHOOTER_MODEL = "GEO_NPC_F3_CSO"
DEFENDER_MODEL = "GEO_NPC_F1_CSO"
RAIDER_MODEL = "GEO_MON_F0_MUU"
HEAVY_MODEL = "GEO_MON_F0_FFG"

# ROUND-2 TUNING BUILD (owner: "minute long runs with spawns every 20 seconds"):
# a 1:00 clock, three 2-raider waves, ONE soldier pool (the north/south watch
# split is gone — placement is manual, the lanes were a ticker-budget hack), and
# THE PIN: an engaged raider stands and takes the fight instead of jogging away.
# 14 allies this build — the ratified 20-cap and raider COUNTER-damage both need
# the labelasm long-jump pass (the ~32KB ticker ceiling), the queued next task.
SIEGE_SECONDS = 60
SCHED = [55, 40, 20]                     # wave start-times (remaining seconds)
BASE_HP = 24
LOSS_SCENE = 35                          # the donor's own arena fight (no BattlePatch)
STIPEND = 3000
WIN_GIL = 2000
WIN_ITEM = "Phoenix Down"

# pools: name -> (count, price, request flag). Prices are the ratified band.
# Request flags sit OUTSIDE the blackboard band (8860+); the safe band starts 8712.
POOLS = {
    "soldiers":  (6, 300, 8840),
    "shooters":  (4, 550, 8842),
    "defenders": (4, 450, 8843),
}
N_RAIDERS = {"n": 2, "s": 2, "h": 2}     # NW Mus / SW Mus / SW heavies


# --------------------------------------------------------------- walkmesh helpers
def read_spawn() -> tuple[int, int]:
    m = re.search(r"(?m)^spawn = \[(-?\d+), (-?\d+)\]", BASE_TOML.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("no [player] spawn in the base toml")
    return int(m.group(1)), int(m.group(2))


def lattice() -> list[tuple[int, int]]:
    """Lattice on the spawn's FLOOR *and* its CONNECTED COMPONENT of the engine's
    own tri-neighbor graph — the BTTABLE balcony lesson plus this bench's east-bay
    lesson (same-floor pockets can be DISCONNECTED sheets; an anchor there is
    unroutable by construction, and the route planner rightly refuses)."""
    mesh = BgiWalkmesh.from_bytes((BENCH / "walkmesh.bgi").read_bytes())
    wv = mesh.world_verts()
    spawn = read_spawn()
    tri_pts = [tuple(wv[i] for i in t.vtx) for t in mesh.tris]
    seeds = [ti for ti, (a, b, c) in enumerate(tri_pts)
             if _pt_in_tri_xz(spawn[0], spawn[1], a, b, c)]
    if not seeds:
        raise SystemExit(f"spawn {spawn} is on no tri — mesh read wrong?")
    # pure nbr connectivity (the street arms cross FLOOR seams), bounded by a
    # HEIGHT band around the spawn — balconies ride high, streets stay near
    # ground; the band keeps the arms and drops the BTTABLE balcony class
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
    # anchors want REAL wall clearance (the layout skill's ~100u+ law: a 1u edge
    # sliver point gets its occupant shoved and oscillating) — keep only points
    # >=120u from every boundary edge of the component
    from ff9mapkit.scene import routes as _routes

    class _NS:                                    # routes wants .world_verts/.tris
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
    pts, clear = lattice()
    used: set = set()
    lay = {
        "spawn": read_spawn(),
        # the ratified anchors (yaw-0: these cardinals are also screen directions),
        # picked from the CLEARANCE set (>=120u off every wall)
        "base": nearest(clear, 2050, -100, used),        # the EAST pocket
        "qm": nearest(clear, 1650, -450, used),
        "nw_stage": [nearest(clear, -4100, 4900, used),
                     nearest(clear, -4350, 5150, used),
                     nearest(clear, -3850, 4650, used)],
        "sw_stage": [nearest(clear, -4250, -2850, used),
                     nearest(clear, -4550, -3150, used),
                     nearest(clear, -3950, -2600, used)],
        # dormant pooled seats: never spawned, but keep them on-mesh and spread
        # (~200u lattice pitch) so the probe stays quiet about them
        "park": [nearest(pts, 2200 + 200 * (i % 5), 1400 + 200 * (i // 5), used)
                 for i in range(20)],
    }
    # lane waypoints (hand-picked off the probe, then SNAPPED to the clearance
    # set — an off-mesh waypoint is unfixable by route="auto"): NW lane down
    # the diagonal street through the NORTH-of-monument choke; SW lane along the
    # south edge through the SOUTH choke; both end at the east pocket.
    lay["nw_route"] = [nearest(clear, *p) for p in
                       [(-3400, 3500), (-1900, 1900), (-250, 1450),
                        (950, 750), (1750, 150)]]
    lay["sw_route"] = [nearest(clear, *p) for p in
                       [(-2500, -1700), (-800, -1050), (450, -800),
                        (1300, -450), (1850, -230)]]
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


RAIDERS = (["n0", "n1"], ["s0", "s1"], ["h0", "h1"])
ALL_RAIDERS = [r for grp in RAIDERS for r in grp]
SOLDIERS = [f"sd{i}" for i in range(POOLS["soldiers"][0])]


def behavior_toml(lay: dict) -> str:
    bx, bz = lay["base"]
    parts = [f"\n[behavior]\nwarmup = 45\ntimer = {SIEGE_SECONDS}\n"
             f'counters = ["wave", "kills"]\n'
             f'\n[[behavior.table]]\nname = "sched"\nvalues = {_t(SCHED)}\n'
             f'\n[[behavior.schedule]]\ncounter = "wave"\ntable = "sched"\n']
    for pname, (_n, price, rf) in POOLS.items():
        btn = "\nbutton = true" if pname == "soldiers" else ""
        parts.append(f'\n[[behavior.pool]]\nname = "{pname}"\nprice = {price}\n'
                     f"request_flag = {rf}{btn}\n")

    # THE DEPOT — the base to defend (east pocket). Loses -> the boss battle;
    # holds to 0:00 -> the win cry + the purse. Also pays the opening stipend.
    parts.append(f'\n[[behavior.unit]]\nnpc = "base"\nhp = {BASE_HP}\nspeed = 30\n')
    parts.append(_branch(when=[{"flag": "lost"}], do={"die": True}))
    parts.append(_branch(when=[{"hp_le": 0}], do={"battle": LOSS_SCENE},
                         raise_flags=["lost"]))
    parts.append(_branch(when=[{"time_above": SIEGE_SECONDS - 5}], once="stipend",
                         do={"award": STIPEND}))
    parts.append(_branch(when=[{"time_above": SIEGE_SECONDS - 6}], once="stiptext",
                         do={"announce": f"The city fronts you {STIPEND} gil for the"
                                         f" defense, kupo!  Press Select anywhere to"
                                         f" deploy troops where you stand."}))
    parts.append(_branch(when=[{"time_below": 1}], once="paid",
                         do={"award": WIN_GIL, "item": WIN_ITEM}))
    parts.append(_branch(when=[{"time_below": 2}], once="wincry",
                         do={"announce": f"WE HELD THE DEPOT!  The city pays"
                                         f" {WIN_GIL} gil and a {WIN_ITEM}."}))
    parts.append(_branch(when=[{"any_near": [ALL_RAIDERS, 500]}], once="alarm",
                         do={"announce": "They're through!  Protect the depot!"}))
    parts.append(_branch(do={"hold": [bx, bz]}))

    # THE RAIDERS — march the lane, beat the depot, and STAND THE FIGHT: the
    # hold_ground PIN (round-1 feedback: Mus jogged away from their attackers)
    # halts the march while any soldier is on them; deselect resumes the march
    # at the current waypoint. Priority: at the depot, keep swinging IT (the
    # defenders' grinder duel stays a duel). Each death feeds the kill tally.
    def raider(name, model, hp, stage, route, wave, dmg, ivl, speed):
        parts.append(f'\n[[behavior.unit]]\nnpc = "{name}"\nhp = {hp}\nspeed = {speed}\n')
        parts.append(_branch(when=[{"hp_le": 0}], do={"die": "kills"}))
        parts.append(_branch(when=[{"active": "base"}, {"near": ["base", 300]}],
                             do={"swing_at": "base", "damage": dmg, "interval": ivl}))
        parts.append(_branch(when=[{"any_near": [SOLDIERS, 240]}],
                             do={"hold_ground": True}))
        parts.append(_branch(when=[{"counter_ge": ["wave", wave]}],
                             do={"march": [list(stage)] + [list(p) for p in route],
                                 "route": "auto", "arrive_r": 180, "speed": speed}))
        parts.append(_branch(do={"hold": list(stage)}))

    nw, sw = lay["nw_route"], lay["sw_route"]
    raider("n0", RAIDER_MODEL, 3, lay["nw_stage"][0], nw, 1, 1, 30, 50)
    raider("n1", RAIDER_MODEL, 3, lay["nw_stage"][1], nw, 1, 1, 30, 45)
    raider("s0", RAIDER_MODEL, 3, lay["sw_stage"][0], sw, 2, 1, 30, 50)
    raider("s1", RAIDER_MODEL, 3, lay["sw_stage"][1], sw, 2, 1, 30, 45)
    raider("h0", HEAVY_MODEL, 6, lay["sw_stage"][0], sw, 3, 2, 26, 40)
    raider("h1", HEAVY_MODEL, 6, lay["sw_stage"][1], sw, 3, 2, 26, 38)

    # THE ARMY — 20 POOLED units, hired at your feet, each holding its post.
    #   Soldier: chases + melees its WATCH's lane.  Shooter: stationary, shells
    #   600u.  Defender: stationary grinder, damage 2 at 300u.
    def ally(name, model, pool, targets, *, chase_targets=(), reach=250, dmg=1,
             ivl=25, speed=60):
        parts.append(f'\n[[behavior.unit]]\nnpc = "{name}"\npooled = true\n'
                     f'pool = "{pool}"\nspeed = {speed}\n')
        for r in targets:
            parts.append(_branch(when=[{"active": r}, {"near": [r, reach]}],
                                 do={"swing_at": r, "damage": dmg, "interval": ivl}))
        for r in chase_targets:
            parts.append(_branch(when=[{"active": r}, {"near": [r, 700]}],
                                 do={"chase": r, "standoff": 170, "speed": 65}))
        parts.append(_branch(do={"hold_post": True}))

    # Target lists are the TICKER-SIZE knob (the v1 central ticker is one .eb
    # body; relative jumps are signed-16, so ~32KB is a hard span ceiling):
    # soldiers chase the runners and melee everything; shooters shell all six;
    # defenders grind the SW pressure (the heavies' lane) that reaches them.
    runners = RAIDERS[0] + RAIDERS[1]                    # the chase-worthy Mus
    for i, name in enumerate(SOLDIERS):
        ally(name, SOLDIER_MODEL, "soldiers", ALL_RAIDERS, chase_targets=runners)
    for i in range(POOLS["shooters"][0]):
        ally(f"sh{i}", SHOOTER_MODEL, "shooters", ALL_RAIDERS,
             reach=600, ivl=15, speed=50)
    for i in range(POOLS["defenders"][0]):
        ally(f"df{i}", DEFENDER_MODEL, "defenders", RAIDERS[1] + RAIDERS[2],
             reach=300, dmg=2, ivl=30, speed=45)
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
    cb = fb.compile()                            # fails loudly on a jump overflow
    print(f"  ticker {len(cb.ticker_body)} B  main_init {len(cb.main_init)} B")
    return raw, fb


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

    lay = layout()
    parts = [text, "\n# ---- THE FORT CONDOR FIT (generated by "
                   "studies/fort-condor/condor_fit_bench.py) ----\n"]
    bx, bz = lay["base"]
    qx, qz = lay["qm"]
    parts.append(f'\n[[npc]]\nname = "base"\nmodel = "{BASE_MODEL}"\n'
                 f'pos = [{bx}, {bz}]\nface = 64\n'
                 f'dialogue = "This depot is everything we have.  Hold them off!"\n')
    parts.append(f'\n[[npc]]\nname = "qm"\nmodel = "{QM_MODEL}"\npos = [{qx}, {qz}]\n'
                 f'dialogue = "Press Select ANYWHERE to convene the war council —'
                 f' your troops deploy on the very spot you stand."\n')
    for grp, stages in (("n", lay["nw_stage"]), ("s", lay["sw_stage"])):
        for i in range(N_RAIDERS[grp]):
            sx, sz = stages[i]
            parts.append(f'\n[[npc]]\nname = "{grp}{i}"\nmodel = "{RAIDER_MODEL}"\n'
                         f'pos = [{sx}, {sz}]\ndialogue = "Kweeeh!"\n')
    for i in range(N_RAIDERS["h"]):
        sx, sz = lay["sw_stage"][i]
        parts.append(f'\n[[npc]]\nname = "h{i}"\nmodel = "{HEAVY_MODEL}"\n'
                     f'pos = [{sx + 120 * (i + 1)}, {sz}]\ndialogue = "GRAAAH."\n')
    seat = 0
    for pname, (count, _price, _rf) in POOLS.items():
        model = {"soldiers": SOLDIER_MODEL,
                 "shooters": SHOOTER_MODEL, "defenders": DEFENDER_MODEL}[pname]
        pfx = {"soldiers": "sd", "shooters": "sh", "defenders": "df"}[pname]
        for i in range(count):
            sx, sz = lay["park"][seat]
            parts.append(f'\n[[npc]]\nname = "{pfx}{i}"\nmodel = "{model}"\n'
                         f'pos = [{sx}, {sz}]\n'
                         f'dialogue = "Holding this ground!"\n')
            seat += 1

    parts.append(behavior_toml(lay))

    # THE WAR COUNCIL, two-pass: validate demands the button pool's menu exist,
    # but the honest rows need the hireable flags a dry build publishes — so pass
    # 1 appends the menu WITHOUT requires_flag, the dry build resolves the flags
    # (menu content can't move blackboard allocation), and pass 2 swaps in the
    # flag-gated rows: a row you can SEE is a hire that will succeed.
    LABELS = (("soldiers", "Soldier (chases, melee)"),
              ("shooters", "Shooter (stationary, long reach)"),
              ("defenders", "Defender (stationary, heavy)"))

    def council(h: dict | None) -> str:
        rows = []
        for pname, label in LABELS:
            _c, price, rf = POOLS[pname]
            gate = f"requires_flag = {h[pname]}\n" if h else ""
            rows.append(f'\n[[choice.options]]\ntext = "{label} — {price} gil"\n'
                        f'reply = "Deployed!  He holds this very spot."\n'
                        f"set_flag = [{rf}, 1]\n{gate}")
        return (f'\n[[choice]]\nzone = [[9000,9000],[9200,9000],[9200,8800],'
                f'[9000,8800]]\n'
                f'prompt = "WAR COUNCIL — deploy on this spot:"\ninstant = true\n'
                + "".join(rows)
                + '\n[[choice.options]]\ntext = "Never mind."\n')

    parts.append(council(None))
    _raw, fb = _dry_build(parts)
    h = {p: fb.pool_hireable[p] for p in POOLS}
    parts[-1] = council(h)
    _raw, fb = _dry_build(parts)                 # re-validate the final form
    BENCH_TOML.write_text("".join(parts), encoding="utf-8")
    REPORT.write_text(fb.compile().report, encoding="utf-8")
    print(f"wrote {BENCH_TOML}")
    print(f"  base {lay['base']}  qm {lay['qm']}  nw_stage {lay['nw_stage']}"
          f"  sw_stage {lay['sw_stage']}")
    print(f"  hireable flags: {h}   report -> {REPORT}")


def probe() -> None:
    if not BENCH_TOML.exists():
        gen()
    r = subprocess.run([sys.executable, str(REPO / "tools" / "field_layout_probe.py"),
                        str(BENCH_TOML), "--out",
                        str(REPO / "tools/scroll_out/layout_probe/condor_fit")])
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
PLAYTEST (~ -> Reload field on {FIELD_ID}, or Warp -> {FIELD_ID}):
  0 BOOT: 1:00 clock; depot + quartermaster in the EAST pocket; 2 Mus at the NW
    street, 2 Mus + 2 Fangs at the SW gate. Within seconds: the STIPEND line +
    3000 gil (round-1 confirmed — regression check only).
  1 HIRES: press SELECT anywhere -> THREE rows now (the north/south watch split
    is GONE — one Soldier row; placement is yours). Deploy fast: a Soldier at
    each chokepoint, a Shooter with sightlines, a Defender at the depot.
  2 0:55 — wave 1 (2 Mus, NW street). THE PIN CHECK — the round-1 defect: when
    your Soldier reaches a Mu, the Mu should STOP and stand the fight (idle in
    place, no more jogging to the depot mid-beating), and resume its march only
    if it shakes free (you can test by hiring the Soldier far off the lane).
  3 0:40 — wave 2 (2 Mus, SW gate, SOUTH choke). 0:20 — wave 3 (2 Fangs, hp 6,
    hit the depot for 2).
  4 LEAKERS beat on the depot (hp {BASE_HP}); at the depot a raider keeps
    swinging IT even while Defenders grind him (the duel stays a duel).
    If it dies: the boss battle ({LOSS_SCENE}) fires ONCE, then the field
    resumes lost.
  5 If the depot stands at 0:00: the WIN CRY + the purse — {WIN_GIL} gil and a
    {WIN_ITEM}, paid EXACTLY ONCE (round-1 confirmed).
  6 ~ -> Reload: full reset; a whole run is ONE MINUTE — iterate freely.
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "probe", "deploy"])
    {"gen": gen, "probe": probe, "deploy": deploy}[ap.parse_args().cmd]()


if __name__ == "__main__":
    main()
