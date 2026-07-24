"""THE POOLED-UNIT BENCH — runtime activation as compiler vocabulary (the ladder's
post-rung-4 extension; unblocks fort-condor's placement/economy rebuild).

Field **30413** ("BTPOOL", a fresh 559 native fork, the same top-down Zaghnol arena as
30410-30412), PURE PRODUCT PATH: everything is `[behavior]` TOML + plain deploy_field —
zero bench bytecode patching.

The demo — placement defenders:
  pest (Mu, hp 3)        wanders mid-arena; CHASES you when you come near (standoff
                         ring); swings at any recruit in reach (MUTUAL combat).
  r0/r1/r2 (soldiers)    POOLED (pool "recruits", never boot-spawned). A Hire row at
                         any quartermaster spawns the next one AT YOUR FEET (the
                         press-time position becomes its post): die -> swing pest ->
                         chase pest (acquire 700) -> hold_post.
  qm0/qm1/qm2            static quartermasters marking the three hire zones (spawn /
                         west / north) — each zone is an instant [[choice]] wired to
                         the pool's spawn-request flag (index printed at gen; the
                         allocation is deterministic).

Usage (repo root):   py studies/behavior-trees/btpool_bench.py gen | deploy
First deploy of 30413 needs a RELAUNCH; then ~ -> Reload field = the full reset
(recruits despawn, the pool refills, the pest returns).
Revert: py tools/scroll_out/revert_deploy_30413.py
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

BENCH = Path("C:/gd/_btpool_bench")
BASE_TOML = BENCH / "LDBM_NATIVE.field.toml"
BENCH_TOML = BENCH / "BTPOOL.field.toml"
REPORT = BENCH / "behavior-report.txt"
FIELD_ID = 30413
FIELD_NAME = "BTPOOL"
MOD_FOLDER = "FF9CustomMap"
DONOR = "fbg_n11_ldbm_map158_lb_plz_0"                            # 559, pitch 68.8

PEST_MODEL = "GEO_MON_F0_MUU"
RECRUIT_MODEL = "GEO_NPC_F0_CSO"
QM_MODEL = "GEO_NPC_F2_CSO"
N_RECRUITS = 3
CONTACT_R = 250                              # swing reach (> the 160 chase standoff)
ACQUIRE_R = 700                              # recruit aggro radius around its post


# --------------------------------------------------------------- walkmesh helpers
def read_spawn() -> tuple[int, int]:
    m = re.search(r"(?m)^spawn = \[(-?\d+), (-?\d+)\]", BASE_TOML.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("no [player] spawn in the base toml")
    return int(m.group(1)), int(m.group(2))


def lattice() -> list[tuple[int, int]]:
    mesh = BgiWalkmesh.from_bytes((BENCH / "walkmesh.bgi").read_bytes())
    wv = mesh.world_verts()
    tris = [tuple(wv[i] for i in t.vtx) for t in mesh.tris]
    xs, zs = [v[0] for v in wv], [v[2] for v in wv]

    def on_mesh(x, z):
        return any(_pt_in_tri_xz(x, z, a, b, c) for a, b, c in tris)

    pts = []
    for z in range(int(min(zs)) + 300, int(max(zs)) - 299, 250):
        for x in range(int(min(xs)) + 300, int(max(xs)) - 299, 250):
            if on_mesh(x, z):
                pts.append((x, z))
    if len(pts) < 30:
        raise SystemExit(f"only {len(pts)} lattice points — mesh read wrong?")
    return pts


def nearest(pts, x, z):
    return min(pts, key=lambda p: (p[0] - x) ** 2 + (p[1] - z) ** 2)


def layout() -> dict:
    pts = lattice()
    spawn = read_spawn()
    xs, zs = [p[0] for p in pts], [p[1] for p in pts]
    cx, cz = (min(xs) + max(xs)) // 2, (min(zs) + max(zs)) // 2
    lay = {
        "spawn": spawn,
        "pest_home": nearest(pts, cx, cz),                       # mid-arena wander
        "park": nearest(pts, max(xs) - 300, max(zs) - 300),      # pooled pre-spawn park
        "qm": [nearest(pts, spawn[0] + 350, spawn[1]),           # spawn-side
               nearest(pts, min(xs) + 500, cz),                  # west
               nearest(pts, cx, max(zs) - 500)],                 # north
    }
    if len({lay["qm"][0], lay["qm"][1], lay["qm"][2]}) != 3:
        raise SystemExit(f"quartermaster posts collapsed: {lay['qm']}")
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
    parts = ["\n[behavior]\nwarmup = 45\n"]
    # THE PEST: wanders mid-arena, chases the player, fights back (MUTUAL)
    parts.append('\n[[behavior.unit]]\nnpc = "pest"\nhp = 3\nspeed = 45\n')
    parts.append(_branch(when=[{"hp_le": 0}], do={"die": True}))
    for r in range(N_RECRUITS):
        parts.append(_branch(when=[{"active": f"r{r}"}, {"near": [f"r{r}", CONTACT_R]}],
                             do={"swing_at": f"r{r}"}))
    parts.append(_branch(when=[{"near": ["player", 800]}],
                         do={"chase": "player", "speed": 60}))
    parts.append(_branch(do={"wander": list(lay["pest_home"]), "radius": 400,
                             "every": 90, "speed": 35}))
    # THE POOL: three recruits, never boot-spawned; a Hire row activates the next one
    # at the player's feet — the press-time position becomes its post (hold_post)
    for r in range(N_RECRUITS):
        parts.append(f'\n[[behavior.unit]]\nnpc = "r{r}"\nhp = 4\nspeed = 50\n'
                     f'pooled = true\npool = "recruits"\n')
        parts.append(_branch(when=[{"hp_le": 0}], do={"die": True}))
        parts.append(_branch(when=[{"active": "pest"}, {"near": ["pest", CONTACT_R]}],
                             do={"swing_at": "pest"}))
        parts.append(_branch(when=[{"active": "pest"}, {"near": ["pest", ACQUIRE_R]}],
                             do={"chase": "pest", "standoff": 160, "speed": 60}))
        parts.append(_branch(do={"hold_post": True}))
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
    text = re.sub(r"(?ms)^\[\[gateway\]\].*?(?=^\[|\Z)", "", text)   # a closed room

    lay = layout()
    parts = [text, "\n# ---- POOLED-UNIT BENCH (generated by "
                   "studies/behavior-trees/btpool_bench.py) ----\n"]
    px_, pz_ = lay["pest_home"]
    parts.append(f'\n[[npc]]\nname = "pest"\nmodel = "{PEST_MODEL}"\n'
                 f'pos = [{px_}, {pz_}]\ndialogue = "Kweeeh!"\n')
    kx, kz = lay["park"]
    for r in range(N_RECRUITS):
        parts.append(f'\n[[npc]]\nname = "r{r}"\nmodel = "{RECRUIT_MODEL}"\n'
                     f'pos = [{kx + 60 * r}, {kz}]\ndialogue = "Holding this ground, sir!"\n')
    for i, (qx, qz) in enumerate(lay["qm"]):
        parts.append(f'\n[[npc]]\nname = "qm{i}"\nmodel = "{QM_MODEL}"\n'
                     f'pos = [{qx}, {qz}]\n'
                     f'dialogue = "Need a soldier?  Step up and say the word."\n')

    parts.append(behavior_toml(lay))

    # the hire zones wire to the pool's spawn-request flag (deterministic allocation)
    import tomllib
    raw = tomllib.loads("".join(parts))
    problems = BT.validate(raw)
    if problems:
        raise SystemExit("behavior validate:\n  " + "\n  ".join(problems))
    all_units = [u["npc"] for u in raw["behavior"]["unit"]]
    fb = BT.build(raw, npc_slots={n: i + 2 for i, n in enumerate(all_units)},
                  npc_txids_by_name={n.get("name"): 0 for n in raw.get("npc", [])},
                  behavior_txids={})
    hire_flag = fb.pool_flags["recruits"]

    h = 220
    for i, (qx, qz) in enumerate(lay["qm"]):
        parts.append(
            f'\n[[choice]]\nzone = [[{qx - h},{qz + h}],[{qx + h},{qz + h}],'
            f'[{qx + h},{qz - h}],[{qx - h},{qz - h}]]\n'
            f'prompt = "Quartermaster: deploy a soldier?"\ninstant = true\n'
            f'\n[[choice.options]]\ntext = "Hire — he holds THIS spot."\n'
            f'reply = "Deployed!  He will hold this ground."\n'
            f"set_flag = [{hire_flag}, 1]\n"
            f'\n[[choice.options]]\ntext = "Not now."\n')
    BENCH_TOML.write_text("".join(parts), encoding="utf-8")
    print(f"wrote {BENCH_TOML}  (1 pest + {N_RECRUITS} POOLED recruits; hire flag "
          f"{hire_flag} wired to {len(lay['qm'])} quartermaster zones)")
    print(f"  layout: {lay}")


def deploy() -> None:
    if not BENCH_TOML.exists():
        gen()
    r = subprocess.run([sys.executable, str(REPO / "tools" / "deploy_field.py"),
                        str(BENCH_TOML), "--id", str(FIELD_ID), "--name", FIELD_NAME,
                        "--text-block", str(FIELD_ID), "--mod-folder", MOD_FOLDER])
    if r.returncode != 0:
        raise SystemExit("deploy_field failed")
    import tomllib
    raw = tomllib.loads(BENCH_TOML.read_text(encoding="utf-8"))
    all_units = [u["npc"] for u in raw["behavior"]["unit"]]
    fb = BT.build(raw, npc_slots={n: i + 2 for i, n in enumerate(all_units)},
                  npc_txids_by_name={n.get("name"): 0 for n in raw.get("npc", [])},
                  behavior_txids={})
    cb = fb.compile()
    REPORT.write_text(cb.report + "\n(dry-run placeholders; the build bound the real "
                      "slots/txids)\n", encoding="utf-8")
    print(f"\nreport saved -> {REPORT}")
    print(f"""
PLAYTEST (RELAUNCH first — new id {FIELD_ID}): ~ -> Warp -> {FIELD_ID}
  1 THE PEST: a Mu wanders mid-arena; come near -> it chases you (140u ring).
    NO soldiers exist anywhere at boot (the pool is dormant).
  2 HIRE AT YOUR FEET: stand by any quartermaster (spawn-side / west / north) ->
    the menu pops on entry -> "Hire" -> a soldier MATERIALIZES AT YOUR FEET and
    holds that exact spot. Step out and back in to hire again.
  3 THE INTERCEPT: lure the pest past a posted soldier (within ~{ACQUIRE_R}) -> the
    soldier acquires, chases, and duels it (MUTUAL: the pest fights back) -> pest
    dies -> the soldier walks BACK TO ITS POST.
  4 POOL EXHAUSTED: after {N_RECRUITS} hires, further Hire rows do nothing (silent,
    v1 semantics — the request is consumed).
  5 ~ -> Reload field: soldiers despawn, the pool refills, the pest returns.
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "deploy"])
    (gen if ap.parse_args().cmd == "gen" else deploy)()


if __name__ == "__main__":
    main()
