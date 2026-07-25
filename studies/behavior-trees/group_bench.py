"""THE GROUP BRAWL — vector-substrate RUNG 1 in-game (30416, hot reload).

THE PARITY TEST: the exact ISLES brawl the owner already passed — two teams of
7 converge on the plaza, melee, the wounded flee to their corners, the crier
calls the fight off the fallen counter — re-expressed through THE GROUP LOOP:

  v1 (ISLES, proven):  each unit carried 6 unrolled swing-pair branches + 7
      chase branches + 6 dispatch bodies -> 46,625 new bytes, 33,832B ticker.
  v2 (this build):     each unit carries ONE `engage` branch (a sticky acquire
      loop picks the target register; pursue feeds off the roster tables; ONE
      target-indexed swing body damages hp[ctgt] by computed write) and each
      team's state lives in group tables (px/pz/act/hp).

WHAT A PASS LOOKS LIKE (same fight, told by different bytecode):
  * both arcs charge after the warm-up and a REAL melee resolves — units pick
    whichever foe is in reach (roster order breaks ties), trade blows, die;
  * wounded units (1 hp) break off and run for their corner — their flee cond
    now reads a TABLE CELL, so a working retreat proves the hp reroute;
  * the crier's "First blood" / "Half the brawl has fallen" / "ONE LEFT
    STANDING" ladder lands true (die="fallen" counters, unchanged vocabulary);
  * units RE-ACQUIRE: when a unit's target dies it turns on another foe in
    range (the sticky register dropping + the loop re-picking — watch for a
    survivor pivoting between victims, v1 could only do this by branch order);
  * no freeze anywhere; ~ -> Reload restarts the brawl clean.

Deploys OVER the 30416 slot (registration line identical -> ZERO RELAUNCH;
~ -> Warp -> 30416 or Reload is enough).

Usage (repo root):  py studies/behavior-trees/group_bench.py gen | probe | deploy
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
BENCH_TOML = BENCH / "GROUP.field.toml"
REPORT = BENCH / "group-report.txt"
FIELD_ID = 30416
FIELD_NAME = "ISLES"                     # keep the REGISTERED name -> no relaunch
MOD_FOLDER = "FF9CustomMap"
DONOR = "fbg_n11_ldbm_map158_lb_plz_0"                            # 559, yaw-0 plaza

KNIGHT_MODEL = "GEO_NPC_F0_CSO"
MU_MODEL = "GEO_MON_F0_MUU"
CRIER_MODEL = "GEO_NPC_F2_CSO"

TEAM = 7
KNIGHTS = [f"kn{i}" for i in range(TEAM)]
MUS = [f"mu{i}" for i in range(TEAM)]
ENGAGE = {"radius": 2200, "contact": 170, "damage": 1, "interval": 25, "speed": 60}

# the proven v1 baseline (island_bench round 1, 2026-07-25) — printed for the
# comparison; regenerate island_bench if the compiler changes enough to drift
V1_NEW_BYTES = 46625
V1_TICKER = 33832


# --------------------------------------------------------------- walkmesh helpers
def read_spawn() -> tuple[int, int]:
    m = re.search(r"(?m)^spawn = \[(-?\d+), (-?\d+)\]",
                  BASE_TOML.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("no [player] spawn in the base toml")
    return int(m.group(1)), int(m.group(2))


def lattice():
    """The proven anchor filter (condor/ISLES verbatim)."""
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
    lay = {"spawn": read_spawn(),
           # the ISLES arcs, verbatim: east knights vs west Mus at 400u pitch
           "kn": [nearest(clear, 900, -1200 + 400 * i, used) for i in range(TEAM)],
           "mu": [nearest(clear, -900, -1200 + 400 * i, used) for i in range(TEAM)],
           "crier": nearest(clear, 2300, -600, used),
           "kn_refuge": [nearest(clear, 2300, 1200, used),
                         nearest(clear, 1900, -1500, used)],
           "mu_refuge": [nearest(clear, -3200, 3600, used),
                         nearest(clear, -4300, -2900, used)]}
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
    # ROUND 2 — THE SCOREBOARD: two alive_only group scans feed the live strip
    # (kn/mu headcounts + the fallen tally), engage picks the NEAREST foe, and
    # the crier's finale keys on TEAM WIPE (the truthful-counter lesson: a team
    # fight never reaches a 13-kill tally).
    parts = ['\n[behavior]\nwarmup = 45\n'
             'counters = ["fallen", "kn_alive", "mu_alive"]\n'
             f'\n[[behavior.group]]\nname = "knights"\nunits = {_t(KNIGHTS)}\n'
             f'\n[[behavior.group]]\nname = "mus"\nunits = {_t(MUS)}\n'
             '\n[[behavior.scan]]\nname = "kn_up"\ngroup = "knights"\n'
             'count = "kn_alive"\nalive_only = true\n'
             '\n[[behavior.scan]]\nname = "mu_up"\ngroup = "mus"\n'
             'count = "mu_alive"\nalive_only = true\n'
             # short labels: the window auto-sizes to the text and the round-1
             # strip wrapped ("Fallen" / "7" on two lines) — keep one line
             '\n[[behavior.hud]]\nwindow = 6\n'
             'values = ["kn_alive", "mu_alive", "fallen"]\n'
             'text = "[MPOS=8,8]KN [NUMB=0]  MU [NUMB=1]  DOWN [NUMB=2]"\n']

    def brawler(name, post, foe_group, refuge, threat):
        parts.append(f'\n[[behavior.unit]]\nnpc = "{name}"\nhp = 4\nspeed = 55\n')
        parts.append(_branch(when=[{"hp_le": 0}], do={"die": "fallen"}))
        # the retreat cond now reads the unit's ROSTER hp CELL — a working
        # flee is visible proof of the hp reroute
        parts.append(_branch(when=[{"hp_le": 1}],
                             do={"flee": threat, "to": [list(p) for p in refuge],
                                 "avoid_r": 800, "speed": 70}))
        parts.append(_branch(do=dict(engage=foe_group, nearest=True, **ENGAGE)))
        parts.append(_branch(do={"hold": list(post)}))

    for i, name in enumerate(KNIGHTS):
        brawler(name, lay["kn"][i], "mus", lay["kn_refuge"], MUS[i])
    for i, name in enumerate(MUS):
        brawler(name, lay["mu"][i], "knights", lay["mu_refuge"], KNIGHTS[i])

    cx, cz = lay["crier"]
    parts.append('\n[[behavior.unit]]\nnpc = "crier"\nspeed = 30\n')
    parts.append(_branch(when=[{"counter_eq": ["mu_alive", 0]}], once="muwipe",
                         do={"announce": "The Mus are WIPED OUT — the east side"
                                         " takes the plaza!"}))
    parts.append(_branch(when=[{"counter_eq": ["kn_alive", 0]}], once="knwipe",
                         do={"announce": "The knights are WIPED OUT — the Mus"
                                         " take the plaza!"}))
    parts.append(_branch(when=[{"counter_ge": ["fallen", 7]}], once="half",
                         do={"announce": "Half the brawl has fallen!"}))
    parts.append(_branch(when=[{"counter_ge": ["fallen", 1]}], once="first",
                         do={"announce": "First blood on the plaza!"}))
    parts.append(_branch(do={"hold": [cx, cz]}))
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
    txids.update({("hud", hi): 950 + hi for hi, _h in BT.hud_lines(raw)})
    fb = BT.build(raw, npc_slots={n: i + 2 for i, n in enumerate(all_units)},
                  npc_txids_by_name={n.get("name"): 0 for n in raw.get("npc", [])},
                  behavior_txids=txids)
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
    # entry_settle: the PROVEN camera-ease cover (field-entry rung 7, warp-tested
    # on the waystation) — the importer does not emit it, and without it the
    # reveal lands before the smooth camera parks (the drift seen on warp-in)
    if "entry_settle" not in text:
        text = re.sub(r"(?m)^\[camera\]$", '[camera]\nentry_settle = "auto"', text)
    blocks = re.split(r"(?m)(?=^\[)", text)                          # clear the stage
    text = "".join(b for b in blocks
                   if not (b.startswith("[[object]]") and 'kind = "npc"' in b))

    lay = layout()
    parts = [text, "\n# ---- THE GROUP BRAWL (generated by "
                   "studies/behavior-trees/group_bench.py) ----\n"]
    for i, name in enumerate(KNIGHTS):
        x, z = lay["kn"][i]
        parts.append(f'\n[[npc]]\nname = "{name}"\nmodel = "{KNIGHT_MODEL}"\n'
                     f'pos = [{x}, {z}]\nface = 64\ndialogue = "For the east side!"\n')
    for i, name in enumerate(MUS):
        x, z = lay["mu"][i]
        parts.append(f'\n[[npc]]\nname = "{name}"\nmodel = "{MU_MODEL}"\n'
                     f'pos = [{x}, {z}]\nface = 192\ndialogue = "Kweeeh!"\n')
    cx, cz = lay["crier"]
    parts.append(f'\n[[npc]]\nname = "crier"\nmodel = "{CRIER_MODEL}"\n'
                 f'pos = [{cx}, {cz}]\n'
                 f'dialogue = "Same brawl as before — but this time one little'
                 f' loop is running ALL of them."\n')
    parts.append(behavior_toml(lay))

    _raw, fb, cb = _dry_build(parts)
    if set(fb._groups) != {"knights", "mus"} or len(fb._engages) != 14:
        raise SystemExit("BENCH INVALID: the group lane did not compile in")
    if len(fb._scans) != 2 or not all(s.alive_only for s in fb._scans) \
            or not fb._huds or not all(e.nearest for e in fb._engages.values()):
        raise SystemExit("BENCH INVALID: scoreboard round pieces missing "
                         "(alive scans / hud / nearest)")
    new_bytes = (len(cb.ticker_body) + len(cb.main_init)
                 + sum(len(b) for b in cb.duty_bodies.values())
                 + sum(len(b) for fns in cb.action_funcs.values()
                       for _t2, b in fns))
    print(f"  THE COLLAPSE: v1 (ISLES) {V1_NEW_BYTES}B new / {V1_TICKER}B ticker"
          f"  ->  v2 (this build) {new_bytes}B new / {len(cb.ticker_body)}B ticker"
          f"  ({100 * new_bytes // V1_NEW_BYTES}% of v1)")
    BENCH_TOML.write_text("".join(parts), encoding="utf-8")
    REPORT.write_text(cb.report, encoding="utf-8")
    print(f"wrote {BENCH_TOML}")
    print(f"  arcs: kn {lay['kn'][0]}..{lay['kn'][-1]}  mu {lay['mu'][0]}..{lay['mu'][-1]}")
    print(f"  report -> {REPORT}")


def probe() -> None:
    if not BENCH_TOML.exists():
        gen()
    r = subprocess.run([sys.executable, str(REPO / "tools" / "field_layout_probe.py"),
                        str(BENCH_TOML), "--out",
                        str(REPO / "tools/scroll_out/layout_probe/groupbrawl")])
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
PLAYTEST (30416 again — registration unchanged, NO relaunch: ~ -> Warp -> {FIELD_ID}
or Reload if there). ROUND 2 — THE SCOREBOARD. Three independent features on
the proven brawl; each verifies on its own:
  1 THE HUD STRIP (top-left, frameless): "Knights 7   Mus 7   Fallen 0" from
    boot, live all match — check it against the ACTORS ON SCREEN at any
    moment (the alive counts come from the alive_only scans, the tally from
    the die counter). It must tick down as units die, never lag, never
    flicker.
  2 ALIVE_ONLY SCANS / TEAM WIPE: the finale line now fires on a WIPE ("The
    Mus are WIPED OUT...") the moment the last one drops — exactly when the
    strip shows 0. (First blood / Half unchanged.)
  3 NEAREST: at the charge, units pair off with the closest opposite (fewer
    crossing lines than round 1) and survivors pivot to the CLOSEST next foe.
  4 regressions: flee-at-1hp, deaths, no freeze; ~ -> Reload restarts clean
    (strip back to 7/7/0).
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("verb", choices=["gen", "probe", "deploy"])
    v = ap.parse_args().verb
    {"gen": gen, "probe": probe, "deploy": deploy}[v]()
