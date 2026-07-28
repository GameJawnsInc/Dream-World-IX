"""THE ISLES BENCH — the LONG-JUMP RELAXATION's first IN-GAME crossing (30416).

The labelasm island pass (jump spans past ±32767 re-routed through inserted
hop islands) shipped offline-proven only: every build since has landed back
under the old wall, so ISLAND BYTES HAVE NEVER EXECUTED IN-GAME. This bench
manufactures the crossing honestly — no padding, just a roster whose compiled
ticker is naturally >32KB — and gen() REFUSES to emit a build that doesn't
cross (the bench would prove nothing).

THE BRAWL: two teams of 7 (knights east, Mus west) converge on the plaza and
fight a real melee — every unit chases near foes, swings in contact, FLEES to
its team's corner at 1 hp, and dies at 0. A crier calls the fight from the
sideline off the shared "fallen" counter (the data-table lane re-verified on a
second field for free).

WHAT A PASS LOOKS LIKE (the failure mode islands guard against is a CalcStack
desync = the ticker freezing mid-run, so LIVENESS LATE IN THE RUN is the test):
  * the brawl starts after the warm-up and keeps resolving — no freeze, no
    black screen, no unit stuck mid-swing forever;
  * wounded units break off and run for their corner (hp-1 flee branches sit
    DEEP in every unit's tree — they only fire if selection still walks the
    whole relaxed ticker);
  * the crier's "half the brawl has fallen" and "ONE LEFT STANDING" lines land
    (counter conds evaluated ~30KB into the body, event-Once dispatch);
  * ~ -> Reload restarts the whole fight clean.

Usage (repo root):  py studies/behavior-trees/island_bench.py gen | probe | deploy
30416 is a NEW id -> the FIRST deploy needs a game RELAUNCH (DictionaryPatch
registration); after that ~ -> Reload field re-reads everything.
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

BENCH = Path("C:/gd/_isles_bench")
BASE_TOML = BENCH / "LDBM_NATIVE.field.toml"
BENCH_TOML = BENCH / "ISLES.field.toml"
REPORT = BENCH / "behavior-report.txt"
FIELD_ID = 30416
FIELD_NAME = "ISLES"
MOD_FOLDER = "FF9CustomMap"
DONOR = "fbg_n11_ldbm_map158_lb_plz_0"                            # 559, yaw-0 plaza

KNIGHT_MODEL = "GEO_NPC_F0_CSO"
MU_MODEL = "GEO_MON_F0_MUU"
CRIER_MODEL = "GEO_NPC_F2_CSO"

TEAM = 7                                 # per side
KNIGHTS = [f"kn{i}" for i in range(TEAM)]
MUS = [f"mu{i}" for i in range(TEAM)]
# the ticker-size knobs: swings are lean pair branches (~122B ticker + a 108B
# body); chases are fatter feed branches (~180B) with NO body — the mix crosses
# the old ticker wall while staying inside the u16 FILE wall (both self-checked)
N_SWING = 6
N_CHASE = 7


# --------------------------------------------------------------- walkmesh helpers
def read_spawn() -> tuple[int, int]:
    m = re.search(r"(?m)^spawn = \[(-?\d+), (-?\d+)\]",
                  BASE_TOML.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("no [player] spawn in the base toml")
    return int(m.group(1)), int(m.group(2))


def lattice():
    """The condor bench's proven anchor filter, verbatim: the spawn's CONNECTED
    COMPONENT of the tri-neighbor graph (same-floor pockets can be disconnected
    sheets), a 400u height band (keeps the street arms, drops the balconies),
    and a >=120u wall-clearance set for anchors."""
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
           # two facing arcs flanking the monument (yaw-0: east arc vs west
           # arc), 400u pitch — clear of the probe's ~192u boot-jam line
           "kn": [nearest(clear, 900, -1200 + 400 * i, used) for i in range(TEAM)],
           "mu": [nearest(clear, -900, -1200 + 400 * i, used) for i in range(TEAM)],
           "crier": nearest(clear, 2300, -600, used),
           # team refuges (Flee wants 2..4 in priority order): wounded knights
           # run east, wounded Mus run northwest — each with a fallback corner
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


BRAINS = False    # brains_bench.py flips this: same brawl, the per-unit-brain backend


def behavior_toml(lay: dict) -> str:
    parts = ['\n[behavior]\n' + ('brains = true\n' if BRAINS else '')
             + 'warmup = 45\ncounters = ["fallen"]\n']

    def brawler(name, post, foes, refuge, threat):
        parts.append(f'\n[[behavior.unit]]\nnpc = "{name}"\nhp = 4\nspeed = 55\n')
        parts.append(_branch(when=[{"hp_le": 0}], do={"die": "fallen"}))
        # the hp-1 retreat sits ABOVE the fight: a wounded unit breaks off and
        # runs for its corner — visible proof that selection still walks the
        # whole relaxed ticker for this unit
        parts.append(_branch(when=[{"hp_le": 1}],
                             do={"flee": threat, "to": [list(p) for p in refuge],
                                 "avoid_r": 800, "speed": 70}))
        for f in foes[:N_SWING]:
            parts.append(_branch(when=[{"active": f}, {"near": [f, 250]}],
                                 do={"swing_at": f, "damage": 1, "interval": 25}))
        for f in foes[:N_CHASE]:
            parts.append(_branch(when=[{"active": f}, {"near": [f, 2200]}],
                                 do={"chase": f, "standoff": 170, "speed": 60}))
        parts.append(_branch(do={"hold": list(post)}))

    # foe lists rotate so every enemy is SOMEBODY's swing target and the melee
    # stays mutual — kn_i leads with mu_i, and vice versa
    for i, name in enumerate(KNIGHTS):
        foes = [MUS[(i + k) % TEAM] for k in range(TEAM)]
        brawler(name, lay["kn"][i], foes, lay["kn_refuge"], foes[0])
    for i, name in enumerate(MUS):
        foes = [KNIGHTS[(i + k) % TEAM] for k in range(TEAM)]
        brawler(name, lay["mu"][i], foes, lay["mu_refuge"], foes[0])

    # THE CRIER — sideline commentary off the shared death tally (counter conds
    # + event-Once announces evaluated ~30KB into the relaxed body)
    cx, cz = lay["crier"]
    parts.append(f'\n[[behavior.unit]]\nnpc = "crier"\nspeed = 30\n')
    parts.append(_branch(when=[{"counter_ge": ["fallen", 13]}], once="last",
                         do={"announce": "ONE LEFT STANDING!  The plaza falls silent."}))
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
    blocks = re.split(r"(?m)(?=^\[)", text)                          # clear the stage
    text = "".join(b for b in blocks
                   if not (b.startswith("[[object]]") and 'kind = "npc"' in b))

    lay = layout()
    parts = [text, "\n# ---- THE ISLES BENCH (generated by "
                   "studies/behavior-trees/island_bench.py) ----\n"]
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
                 f'dialogue = "Fourteen brawlers, one plaza.  Watch the corners —'
                 f' the wounded always run."\n')
    parts.append(behavior_toml(lay))

    _raw, fb, cb = _dry_build(parts)
    content = cb.sizes["ticker_content"]
    if BRAINS:
        bsizes = cb.sizes.get("brains") or {}
        if not bsizes:
            raise SystemExit("BENCH INVALID: brains mode compiled no brain bodies")
        print(f"  BRAINS: residual ticker {content}B (shared lanes only); "
              f"{len(bsizes)} brains, largest {max(bsizes.values())}B, "
              f"total {sum(bsizes.values())}B -- no body anywhere near +/-32767")
    elif content <= 32767:
        raise SystemExit(
            f"BENCH INVALID: ticker content {content}B does not cross the old "
            f"±32767 wall — raise N_CHASE/N_SWING; an under-wall build proves "
            f"nothing about islands")
    else:
        print(f"  THE CROSSING: ticker content {content}B > 32767 -> "
              f"{len(cb.ticker_body) - content}B of island bytes are LIVE in-game")
    BENCH_TOML.write_text("".join(parts), encoding="utf-8")
    REPORT.write_text(cb.report, encoding="utf-8")
    print(f"wrote {BENCH_TOML}")
    print(f"  arcs: kn {lay['kn'][0]}..{lay['kn'][-1]}  mu {lay['mu'][0]}..{lay['mu'][-1]}")
    print(f"  refuges: kn {lay['kn_refuge']}  mu {lay['mu_refuge']}  report -> {REPORT}")


def probe() -> None:
    if not BENCH_TOML.exists():
        gen()
    r = subprocess.run([sys.executable, str(REPO / "tools" / "field_layout_probe.py"),
                        str(BENCH_TOML), "--out",
                        str(REPO / "tools/scroll_out/layout_probe/isles")])
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
PLAYTEST ({FIELD_ID} is a NEW id -> RELAUNCH the game once, then ~ -> Warp -> {FIELD_ID}):
  THE POINT: this ticker is the first >32KB body ever run in-game — the island
  bytes themselves are under test. A routing bug looks like a FREEZE (ticker
  desync), so the whole verdict is liveness:
  1 after the ~4s warm-up both arcs charge and the melee starts;
  2 wounded units (1 hp) BREAK OFF and run — knights east, Mus northwest;
  3 the crier calls "First blood", "Half the brawl has fallen", and (if the
    fight runs down) "ONE LEFT STANDING" — late-run announces prove the deep
    half of the relaxed body still executes;
  4 no freeze, no black screen, no unit locked mid-swing; ~ -> Reload restarts
    the brawl clean.
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("verb", choices=["gen", "probe", "deploy"])
    v = ap.parse_args().verb
    {"gen": gen, "probe": probe, "deploy": deploy}[v]()
