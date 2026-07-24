"""THE MIGRATED SWARM BENCH — fort-condor's unit AI rebased on the behavior-tree compiler.

Field **30400** ("SWARM", the 559 Zaghnol-arena donor) rebuilt entirely on the kit's
**[behavior] TOML surface** (2026-07-24, the behavior-trees study's rung-4 product path):

  * THE SWARM (rung 1's actor-budget harness): 40 Mu chasers in four tier bands; the
    spawn lever arms 10/20/30/40 via [behavior] public flags; armed chasers Chase the
    player (compiler standoff 140 — they RING you instead of phasing onto your exact
    point, the behavior study's playtest-1 lesson; the old converge-to-a-point read is
    gone by design), unarmed chasers hold their posts.
  * THE SKIRMISH (rung 2, lever row 5): the exact playtest-6 staging — two Fang
    attackers march the goal past the fight square, two City-Soldier defenders
    (posts flanking FIGHT_CENTER) acquire within 700, duel at contact 200, MUTUAL
    swings at ~1 dmg/s; HP 3/5 vs 5/3 so lane A's defender wins and lane B's attacker
    breaches (the herald's line pops once, a sticky-Once announce). Deaths vanish;
    the winner resumes.
  * PLACEMENT + ECONOMY (the rung-3 REBUILD on compiler vocabulary, 2026-07-24):
    press SELECT (or Special) ANYWHERE -> the parked hire menu -> "Hire (300 gil)"
    -> gil gate + RemoveGil ride the compiled activation block -> the next of FOUR
    POOLED soldiers materializes AT YOUR FEET and holds that post; within 700 of an
    armed attacker it acquires/chases/duels — and combat is MUTUAL both ways (the
    old one-sided-harass debt is gone: attackers swing back at recruits via plain
    branches). Broke or pool-empty = silent refusal (v1 parity). The demo: arm the
    skirmish, let lane B breach once; reload, arm again, drop 1-2 recruits on lane
    B's path — the breach is stopped.

WHAT THE MIGRATION REMOVED (all recorded in PLAN.md): the ~500-line hand-rolled
referee/fight-function/patch machinery (the compiler subsumes it — proven by the
behavior study's rung-2 regression bench 30411), the rung-3 placement/economy layer
(its mechanisms — SPECIAL-button poller, gil purchase, runtime InitObject spawn-at-feet
— are ★ in-game proven and documented in PLAN.md; it returns as COMPILER VOCABULARY
(pooled/runtime-activated units) in the next session, which also moots playtest 11's
staring-duel bug: that referee no longer exists), and the generic-timer probe (its
claim was ★ proven in playtest 2; rung 4's wave scheduling re-adds timers as needed).

Usage (repo root):  py studies/fort-condor/swarm_bench.py gen | deploy
deploy = plain tools/deploy_field.py — `ff9mapkit build` compiles + installs the trees
(zero bench patching). After a deploy: ~ -> Reload field (RELAUNCH only if 30400 was
never registered). Revert: py tools/scroll_out/revert_deploy_30400.py
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

BENCH = Path("C:/gd/_swarm_bench")
BASE_TOML = BENCH / "LDBM_NATIVE.field.toml"
SWARM_TOML = BENCH / "SWARM.field.toml"
REPORT = BENCH / "behavior-report.txt"
FIELD_ID = 30400
FIELD_NAME = "SWARM"
MOD_FOLDER = "FF9CustomMap"

N_CHASERS = 40
BAND = 10                                    # chasers per tier band
CHASER_MODEL = "GEO_MON_F0_MUU"
ATTACKER_MODEL, DEFENDER_MODEL, HERALD_MODEL = \
    "GEO_MON_F0_FFG", "GEO_NPC_F0_CSO", "GEO_NPC_F2_CSO"
CONTACT_R = 200                              # the rung-2 tuned fight range
ACQUIRE_R = 700                              # defender aggro radius (fights stay in view)
HP_PRESET = {"attacker0": 3, "defender0": 5, "attacker1": 5, "defender1": 3,
             "attacker2": 5, "attacker3": 5}                 # wave 2 hits harder
FIGHT_CENTER = (-1225, -827)                 # owner-called visible town square (playtest 4)
TIER_FLAGS = ["tier10", "tier20", "tier30", "tier40"]
N_POOL = 4                                   # the hireable soldier pool (rung-3 parity)
RECRUIT_COST = 300                           # gil per soldier (the old bench's price)
HIRE_FLAG = 8848                             # the old bench's own request flag, explicit
RECRUIT_HP = 4
# ---- rung 4: THE SIEGE (waves + win/loss on the countdown clock) ----
SIEGE_SECONDS = 180                          # the countdown HUD (3:00; ~ Reload resets)
WAVE_BANDS = {0: 170, 1: 170, 2: 90, 3: 90}  # attacker i marches once time < band
GATE_HP = 6                                  # the herald IS the gate; 0 = the loss
LOSS_SCENE = 35                              # 559's OWN arena battle (the tread-region
                                             # Battle(0,35) — stock scene, no BattlePatch)


# --------------------------------------------------------------- layout
def read_spawn() -> tuple[int, int]:
    m = re.search(r"(?m)^spawn = \[(-?\d+), (-?\d+)\]", BASE_TOML.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("no [player] spawn in the base toml")
    return int(m.group(1)), int(m.group(2))


def lattice_points(spawn: tuple[int, int]) -> list[tuple[int, int]]:
    """All on-mesh lattice points (spawn area kept clear), densified until >= N_CHASERS."""
    mesh = BgiWalkmesh.from_bytes((BENCH / "walkmesh.bgi").read_bytes())
    wv = mesh.world_verts()
    tris = [tuple(wv[i] for i in t.vtx) for t in mesh.tris]
    xs = [v[0] for v in wv]
    zs = [v[2] for v in wv]
    x0, x1 = int(min(xs)) + 300, int(max(xs)) - 300
    z0, z1 = int(min(zs)) + 300, int(max(zs)) - 300

    def on_mesh(x: float, z: float) -> bool:
        return any(_pt_in_tri_xz(x, z, a, b, c) for a, b, c in tris)

    step = max(350, min(x1 - x0, z1 - z0) // 9)
    pts: list[tuple[int, int]] = []
    while step >= 200 and len(pts) < N_CHASERS:
        pts = []
        for z in range(z0, z1 + 1, step):
            for x in range(x0, x1 + 1, step):
                if (x - spawn[0]) ** 2 + (z - spawn[1]) ** 2 < 500 ** 2:
                    continue                               # keep the spawn/lever area clear
                if on_mesh(x, z):
                    pts.append((x, z))
        if len(pts) < N_CHASERS:
            step = int(step * 0.7)
    if len(pts) < N_CHASERS:
        raise SystemExit(f"only {len(pts)} on-mesh grid points — widen the lattice")
    return pts


def nearest(pts, x, z):
    return min(pts, key=lambda p: (p[0] - x) ** 2 + (p[1] - z) ** 2)


def skirmish_layout(pts) -> dict:
    """The playtest-6-proven lane geometry grown for the siege: defenders post
    flanking FIGHT_CENTER, THE GATE (the herald) just south, four attackers (two
    waves x two lanes) staged in the far north."""
    fcx, fcz = FIGHT_CENTER
    posts = [nearest(pts, fcx - 400, fcz + 150), nearest(pts, fcx + 400, fcz + 150)]
    goal = nearest(pts, fcx, fcz - 900)
    zmax = max(p[1] for p in pts)
    north = [p for p in pts if p[1] >= zmax - 1000] or sorted(pts, key=lambda p: -p[1])[:2]
    w1 = [min(north, key=lambda p: p[0]), max(north, key=lambda p: p[0])]
    used = set(w1)

    def pick(x, z):                                      # nearest UNUSED lattice point
        for c in sorted(pts, key=lambda p: (p[0] - x) ** 2 + (p[1] - z) ** 2):
            if c not in used:
                used.add(c)
                return c
        raise SystemExit("lattice exhausted picking wave-2 posts")

    atk = [w1[0], w1[1],                                 # wave 1 (lanes 0/1)
           pick(w1[0][0] + 300, w1[0][1] - 400),         # wave 2, staged just behind
           pick(w1[1][0] - 300, w1[1][1] - 400)]
    herald = nearest(pts, goal[0] + 350, goal[1])
    return {"attackers": atk, "defenders": posts, "goal": goal, "herald": herald,
            "gate": herald}


# --------------------------------------------------------------- the [behavior] TOML
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


def behavior_toml(chaser_posts: list, lay: dict) -> str:
    parts = ["\n[behavior]\nwarmup = 45\n"
             f"timer = {SIEGE_SECONDS}\n"
             f"public_flags = {_t(TIER_FLAGS + ['skirmish'])}\n"]

    def unit(name, hp=None, speed=50, pooled_in=None):
        parts.append(f'\n[[behavior.unit]]\nnpc = "{name}"\n'
                     + (f"hp = {hp}\n" if hp is not None else "") + f"speed = {speed}\n"
                     + (f'pooled = true\npool = "{pooled_in}"\n' if pooled_in else ""))

    # THE SWARM: band b arms when ANY tier >= its size is pulled (picking "20 movers"
    # releases bands 0+1 — the original lever semantics)
    for i in range(N_CHASERS):
        band = i // BAND
        arm = {"any_flag": TIER_FLAGS[band:]}
        unit(f"chaser{i:02d}")
        parts.append(_branch(when=[arm], do={"chase": "player"}))
        parts.append(_branch(do={"hold": list(chaser_posts[i])}))

    # THE SIEGE (rung 4): the skirmish grown into timed WAVES against THE GATE (the
    # herald, hp'd) with win/loss on the countdown clock. Lever row 5 arms it; wave
    # bands key on the HUD clock (the Hunt's GetTimerTime band shape); gate down ->
    # the LOSS Battle (559's own scene 35, one-shot by construction); clock out with
    # the gate standing -> the WIN cry.
    armed = {"flag": "skirmish"}
    calm = [{"not_flag": "lost"}, {"not_flag": "won"}]
    recruits = [f"recruit{r}" for r in range(N_POOL)]
    attackers = [f"attacker{i}" for i in range(4)]
    for i, a in enumerate(attackers):
        lane = i % 2
        d = f"defender{lane}"
        unit(a, hp=HP_PRESET[a], speed=40)
        parts.append(_branch(when=[{"hp_le": 0}], do={"die": True}))
        parts.append(_branch(when=[armed, {"active": d}, {"near": [d, CONTACT_R]}],
                             do={"swing_at": d}))
        # THE GATE is the prize: beat on the herald at contact
        parts.append(_branch(when=[armed, {"active": "herald"},
                                   {"near": ["herald", CONTACT_R]}],
                             do={"swing_at": "herald"}))
        # MUTUAL combat vs hired recruits (plain branches — no referee)
        for r in recruits:
            parts.append(_branch(when=[armed, {"active": r}, {"near": [r, CONTACT_R]}],
                                 do={"swing_at": r}))
        # the wave march: my band open + the siege still undecided -> march the gate
        # (route="auto": the walkmesh A* splices detours if a leg would wedge)
        parts.append(_branch(
            when=[armed, {"time_below": WAVE_BANDS[i]}] + calm,
            do={"march": [list(lay["attackers"][i]), list(lay["gate"])],
                "route": "auto", "arrive_r": 180, "speed": 40}))
        parts.append(_branch(do={"hold": list(lay["attackers"][i])}))
    for lane in (0, 1):
        d = f"defender{lane}"
        mine = [attackers[lane], attackers[lane + 2]]    # both waves of my lane
        unit(d, hp=HP_PRESET[d], speed=50)
        parts.append(_branch(when=[{"hp_le": 0}], do={"die": True}))
        for a in mine:
            parts.append(_branch(when=[armed, {"active": a}, {"near": [a, CONTACT_R]}],
                                 do={"swing_at": a}))
        for a in mine:
            parts.append(_branch(when=[armed, {"active": a}, {"near": [a, ACQUIRE_R]}],
                                 do={"chase": a}))
        parts.append(_branch(do={"hold": list(lay["defenders"][lane])}))
    # THE GATE (the herald with hp): loss battle at 0 hp, the win cry at 0:00
    unit("herald", hp=GATE_HP, speed=30)
    parts.append(_branch(when=[{"flag": "lost"}], do={"die": True}))
    parts.append(_branch(when=[{"hp_le": 0}], do={"battle": LOSS_SCENE},
                         raise_flags=["lost"]))
    parts.append(_branch(when=[armed, {"time_below": 1}],
                         do={"announce": "We held the gate!  The Festival is saved!"},
                         raise_flags=["won"], once="wincry"))
    parts.append(_branch(when=[armed, {"any_near": [attackers, 350]}],
                         do={"announce_npc": "herald"}, once="gatecry"))
    parts.append(_branch(do={"hold": list(lay["gate"])}))
    # THE RECRUIT POOL (rung-3 rebuilt as compiler vocabulary): pooled soldiers,
    # hired ANYWHERE via the SELECT/Special poller + the parked menu below; each
    # holds the spot it was placed on (hold_post) and defends it A-then-B priority
    parts.append(f'\n[[behavior.pool]]\nname = "recruits"\nprice = {RECRUIT_COST}\n'
                 f"button = true\nrequest_flag = {HIRE_FLAG}\n")
    for r in recruits:
        unit(r, hp=RECRUIT_HP, speed=50, pooled_in="recruits")
        parts.append(_branch(when=[{"hp_le": 0}], do={"die": True}))
        for a in attackers:
            parts.append(_branch(when=[armed, {"active": a}, {"near": [a, CONTACT_R]}],
                                 do={"swing_at": a}))
        for a in attackers:
            parts.append(_branch(when=[armed, {"active": a}, {"near": [a, ACQUIRE_R]}],
                                 do={"chase": a}))
        parts.append(_branch(do={"hold_post": True}))
    return "".join(parts)


# --------------------------------------------------------------- gen / deploy
def gen() -> None:
    text = BASE_TOML.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^text_block = \d+", f"text_block = {FIELD_ID}", text)
    text = re.sub(r"(?m)^id = \d+", f"id = {FIELD_ID}", text)
    text = re.sub(r'(?m)^name = "[^"]+"', f'name = "{FIELD_NAME}"', text)
    text = re.sub(r"(?ms)^\[\[gateway\]\].*?(?=^\[|\Z)", "", text)

    spawn = read_spawn()
    pts = lattice_points(spawn)
    lay = skirmish_layout(pts)
    parts = [text, "\n# ---- SWARM BENCH (generated by swarm_bench.py; MIGRATED to the "
                   "[behavior] TOML surface 2026-07-24) ----\n"]
    pick = len(pts) / N_CHASERS
    chaser_posts = [pts[int(i * pick)] for i in range(N_CHASERS)]
    for i, (x, z) in enumerate(chaser_posts):
        parts.append(f'\n[[npc]]\nname = "chaser{i:02d}"\nmodel = "{CHASER_MODEL}"\n'
                     f'pos = [{x}, {z}]\ndialogue = "Kweh!"\n')
    for i, (ax, az) in enumerate(lay["attackers"]):
        parts.append(f'\n[[npc]]\nname = "attacker{i}"\nmodel = "{ATTACKER_MODEL}"\n'
                     f'pos = [{ax}, {az}]\ndialogue = "Grrrr!"\n')
    for i, (dx, dz) in enumerate(lay["defenders"]):
        parts.append(f'\n[[npc]]\nname = "defender{i}"\nmodel = "{DEFENDER_MODEL}"\n'
                     f'pos = [{dx}, {dz}]\ndialogue = "For Lindblum! Hold the line!"\n')
    hx, hz = lay["herald"]
    parts.append(f'\n[[npc]]\nname = "herald"\nmodel = "{HERALD_MODEL}"\n'
                 f'pos = [{hx}, {hz}]\n'
                 f'dialogue = "They are at the gate!  Hold them back!"\n')
    # the recruit POOL (never boot-spawned; parked by the goal — the 2-frame
    # pre-DPOS flash lands out of the action, the old bench's park idiom)
    gx0, gz0 = lay["goal"]
    for r in range(N_POOL):
        parts.append(f'\n[[npc]]\nname = "recruit{r}"\nmodel = "{DEFENDER_MODEL}"\n'
                     f'pos = [{gx0 + 80 * (r + 1)}, {gz0 + 80}]\n'
                     f'dialogue = "Holding this ground, sir!"\n')
    gx, gz = lay["gate"]
    parts.append(f'\n[[marker]]\nname = "gate"\npos = [{gx}, {gz}]\n')
    # the march lines, probe-sweepable (informational — route="auto" also self-heals)
    for i, (ax, az) in enumerate(lay["attackers"]):
        parts.append(f'\n[[marker]]\nname = "lane{i}"\npos = [{ax}, {az}]\n'
                     f"path = [[{ax}, {az}], [{gx}, {gz}]]\nclosed = false\n")

    parts.append(behavior_toml(chaser_posts, lay))

    # THE PARKED HIRE MENU must precede validation (the pool row's button check
    # looks for the zone choice that sets its request flag). Rung-3 idiom: parked
    # far off-mesh — the walk trigger never fires; the poller RunScriptSyncs it.
    parts.append(
        f'\n[[choice]]\nzone = [[9000,9000],[9200,9000],[9200,8800],[9000,8800]]\n'
        f'prompt = "Deploy a soldier HERE for {RECRUIT_COST} gil?"\ninstant = true\n'
        f'\n[[choice.options]]\ntext = "Hire ({RECRUIT_COST} gil)"\n'
        f'reply = "Deployed!  Hold this ground!"\n'
        f"set_flag = [{HIRE_FLAG}, 1]\n"
        f'\n[[choice.options]]\ntext = "Not now."\n')

    # the lever wires to the behavior's public flags (deterministic allocation)
    import tomllib
    raw = tomllib.loads("".join(parts))
    problems = BT.validate(raw)
    if problems:
        raise SystemExit("behavior validate:\n  " + "\n  ".join(problems))
    all_units = [u["npc"] for u in raw["behavior"]["unit"]]
    wmesh = BgiWalkmesh.from_bytes((BENCH / "walkmesh.bgi").read_bytes())
    fb = BT.build(raw, npc_slots={n: i + 2 for i, n in enumerate(all_units)},
                  npc_txids_by_name={n.get("name"): 0 for n in raw.get("npc", [])},
                  behavior_txids={(ui, bi): 0 for ui, bi, _ in BT.announce_lines(raw)},
                  routed=BT.autoroute_plan(raw, wmesh))
    fidx = {nm: fb.public_flag(nm) for nm in TIER_FLAGS + ["skirmish"]}

    cx, cz = spawn
    h = 220
    rows = "".join(
        f'\n[[choice.options]]\ntext = "{(b + 1) * BAND} movers"\n'
        f'reply = "{(b + 1) * BAND} released! (~ Reload to reset)"\n'
        f"set_flag = [{fidx[t]}, 1]\n"
        for b, t in enumerate(TIER_FLAGS))
    rows += (f'\n[[choice.options]]\ntext = "Begin the SIEGE ({SIEGE_SECONDS // 60}:'
             f'{SIEGE_SECONDS % 60:02d} on the clock)"\n'
             f'reply = "The beasts are coming!  Soldiers, hold the gate!"\n'
             f"set_flag = [{fidx['skirmish']}, 1]\n")
    parts.append(
        f'\n[[choice]]\nzone = [[{cx - h},{cz + h}],[{cx + h},{cz + h}],'
        f'[{cx + h},{cz - h}],[{cx - h},{cz - h}]]\n'
        f'prompt = "Swarm bench: release how many movers?"\ninstant = true\n'
        f'{rows}\n[[choice.options]]\ntext = "None for now."\n')
    SWARM_TOML.write_text("".join(parts), encoding="utf-8")
    print(f"wrote {SWARM_TOML}  ({N_CHASERS} chasers + the 2-lane skirmish + the "
          f"{N_POOL}-soldier hire pool @{RECRUIT_COST} gil, all [behavior])")
    print(f"  lanes: attackers {lay['attackers']}  posts {lay['defenders']}"
          f"  goal {lay['goal']}  herald {lay['herald']}\n  flags {fidx}"
          f"  hire flag {HIRE_FLAG}")


def deploy() -> None:
    if not SWARM_TOML.exists():
        gen()
    r = subprocess.run([sys.executable, str(REPO / "tools" / "deploy_field.py"),
                        str(SWARM_TOML), "--id", str(FIELD_ID), "--name", FIELD_NAME,
                        "--text-block", str(FIELD_ID), "--mod-folder", MOD_FOLDER])
    if r.returncode != 0:
        raise SystemExit("deploy_field failed")
    import tomllib
    raw = tomllib.loads(SWARM_TOML.read_text(encoding="utf-8"))
    all_units = [u["npc"] for u in raw["behavior"]["unit"]]
    wmesh = BgiWalkmesh.from_bytes((BENCH / "walkmesh.bgi").read_bytes())
    fb = BT.build(raw, npc_slots={n: i + 2 for i, n in enumerate(all_units)},
                  npc_txids_by_name={n.get("name"): 0 for n in raw.get("npc", [])},
                  behavior_txids={(ui, bi): 0 for ui, bi, _ in BT.announce_lines(raw)},
                  routed=BT.autoroute_plan(raw, wmesh))
    report = fb.compile().report
    REPORT.write_text(report + "\n(dry-run placeholders; the build bound the real "
                      "slots/txids)\n", encoding="utf-8")
    print(f"\nreport saved -> {REPORT}")
    print(f"""
PLAYTEST (RUNG 4 — THE SIEGE: waves + win/loss on the clock):
  ~ -> Reload field on {FIELD_ID} (RELAUNCH only if never registered), then:
  0 The {SIEGE_SECONDS // 60}:{SIEGE_SECONDS % 60:02d} countdown HUD shows from field
    entry (~ Reload resets it). Tiers lever + SELECT-hires work as before.
  1 ARM THE SIEGE (lever row 5). ~10s in (clock < {WAVE_BANDS[0]}), WAVE 1: two Fangs
    march their lanes for THE GATE (the herald, south); the posted defenders
    intercept as always — lane A holds, lane B's Fang usually gets through.
  2 THE GATE FIGHT: a Fang reaching the herald beats on HIM (he cries out once);
    gate hp {GATE_HP}. If it drops to 0 -> **the LOSS: a REAL battle** (559's own
    arena fight) — win or lose it, you return to the field, the herald falls, and
    the siege stands down. ~ Reload restarts the whole round.
  3 THE DEFENSE: hire soldiers (SELECT, {RECRUIT_COST} gil) and drop them on the
    lanes/gate approach -> mutual duels; WAVE 2 (clock < {WAVE_BANDS[2]}): two
    TOUGHER Fangs (hp 5) march in — the real test of your placements.
  4 THE WIN: survive to 0:00 with the gate standing -> the herald's victory line
    pops and the beasts stand down.
  5 Sanity: the loss battle fires ONCE per round (no battle loop after returning);
    after-battle the field resumes (no softlock, BGM back).
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "deploy"])
    (gen if ap.parse_args().cmd == "gen" else deploy)()


if __name__ == "__main__":
    main()
