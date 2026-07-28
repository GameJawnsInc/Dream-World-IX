"""THE CLASS BRAWL — per-class brain sharing's parity cast (30424, "BTCLASS").

The SAME plaza, the SAME 7v7 scoreboard brawl the owner proved on the group
bench (30416 round 2: "works well" / "strip stays up now") — re-expressed as
TWO CLASS ROWS. Fourteen brawlers now share TWO Seq brains:

  BRAWN (per-unit brains, ★ parity-ratified):  15 brains, one per unit.
  THIS BUILD (brains = true + npcs = [...]):   knight x7 + mu x7 -> 2 shared
      brains + the crier's own; per-member state strides into uid-indexed
      gScriptVector cells, and each brain reads ITS caller's cells through
      THE IDENTITY CHANNEL (obj(uid=255).f[5] = the calling unit's uid).

WHAT A PASS LOOKS LIKE — *the same fight*, told by two brains instead of 15:
  * the HUD strip counts down live, the arcs charge, NEAREST pairing holds,
    survivors pivot between victims (re-acquisition through the shared brain);
  * wounded units break off for their team corner at 1 hp (the strided hp
    reroute end to end);
  * dead units vanish cleanly mid-fight (StopSharedScript kills exactly the
    dying member's OWN Seq — its 6 class-siblings must fight on: the orphan
    law under a SHARED entry is this bench's sharpest new claim);
  * the crier's wipe/half/first ladder lands true; ~ -> Reload restarts clean.
ONE authored difference from the group bench (not a finding): each flee keys
its refuge choice off a REPRESENTATIVE threat (mu0 / kn0) instead of a
per-unit foe — a class tree is ONE program, so per-member threat rotations
are not expressible (dynamic targeting is engage's job).

Usage (repo root):  py studies/behavior-trees/classbrawl_bench.py gen | probe | deploy
30424 is a NEW id -> the FIRST deploy needs a game RELAUNCH, then ~ -> Warp.
Revert: py tools/scroll_out/revert_deploy_30424.py
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import group_bench as gb                                           # noqa: E402
from group_bench import (BASE_TOML, CRIER_MODEL, DONOR, ENGAGE,     # noqa: E402
                         KNIGHT_MODEL, KNIGHTS, MU_MODEL, MUS, REPO,
                         _branch, _t, layout)

BENCH = gb.BENCH                          # same donor import as ISLES (reused)
BENCH_TOML = BENCH / "CLASSBRAWL.field.toml"
REPORT = BENCH / "classbrawl-report.txt"
FIELD_ID = 30424
FIELD_NAME = "BTCLASS"
MOD_FOLDER = "FF9CustomMap"

# recorded baselines for the printed comparison (studies/behavior-trees/PLAN.md)
V1_ISLES_NEW = 46625                      # unrolled central ticker
BRAWN_NEW = 46858                         # per-unit brains (15 Seq bodies)


def behavior_toml(lay: dict) -> str:
    from ff9mapkit.content import behaviortoml as BT
    parts = ['\n[behavior]\nbrains = true\nwarmup = 45\n'
             'counters = ["fallen", "kn_alive", "mu_alive"]\n'
             f'\n[[behavior.group]]\nname = "knights"\nunits = {_t(KNIGHTS)}\n'
             f'\n[[behavior.group]]\nname = "mus"\nunits = {_t(MUS)}\n'
             '\n[[behavior.scan]]\nname = "kn_up"\ngroup = "knights"\n'
             'count = "kn_alive"\nalive_only = true\n'
             '\n[[behavior.scan]]\nname = "mu_up"\ngroup = "mus"\n'
             'count = "mu_alive"\nalive_only = true\n'
             '\n[[behavior.hud]]\nwindow = 6\ndigits = 2\n'
             'values = ["kn_alive", "mu_alive", "fallen"]\n'
             'text = "[MPOS=8,8]KN [NUMB=0]  MU [NUMB=1]  DOWN [NUMB=2]"\n']

    def brawler_class(cname, members, foe_group, refuge, threat):
        # ONE row, N bodies: hold_post gives each member ITS OWN spawn as the
        # fallback post (a class tree has no per-member literals)
        parts.append(f'\n[[behavior.unit]]\nnpcs = {_t(members)}\n'
                     f'class = "{cname}"\nhp = 4\nspeed = 55\n')
        parts.append(_branch(when=[{"hp_le": 0}], do={"die": "fallen"}))
        parts.append(_branch(when=[{"hp_le": 1}],
                             do={"flee": threat, "to": [list(p) for p in refuge],
                                 "avoid_r": 800, "speed": 70}))
        parts.append(_branch(do=dict(engage=foe_group, nearest=True, **ENGAGE)))
        parts.append(_branch(do={"hold_post": True}))

    brawler_class("knight", KNIGHTS, "mus", lay["kn_refuge"], MUS[0])
    brawler_class("mu", MUS, "knights", lay["mu_refuge"], KNIGHTS[0])

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
    assert BT  # imported for the caller's dry build
    return "".join(parts)


def _dry_build(parts: list):
    import tomllib

    from ff9mapkit.content import behaviortoml as BT
    raw = tomllib.loads("".join(parts))
    problems = BT.validate(raw)
    if problems:
        raise SystemExit("behavior validate:\n  " + "\n  ".join(problems))
    all_units = [m for u in raw["behavior"]["unit"] for m in BT.row_members(u)]
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
    if "entry_settle" not in text:                                   # the directive
        text = re.sub(r"(?m)^\[camera\]$", '[camera]\nentry_settle = "auto"', text)
    blocks = re.split(r"(?m)(?=^\[)", text)                          # clear the stage
    text = "".join(b for b in blocks
                   if not (b.startswith("[[object]]") and 'kind = "npc"' in b))

    lay = layout()
    parts = [text, "\n# ---- THE CLASS BRAWL (generated by "
                   "studies/behavior-trees/classbrawl_bench.py) ----\n"]
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
                 f'dialogue = "Fourteen brawlers, TWO brains. Each one thinks'
                 f' it is thinking for itself."\n')
    parts.append(behavior_toml(lay))

    _raw, fb, cb = _dry_build(parts)
    if set(fb.classes) != {"knight", "mu"} or not fb.brains:
        raise SystemExit("BENCH INVALID: the class lane did not compile in")
    if set(cb.brain_bodies) != {"knight", "mu", "crier"}:
        raise SystemExit(f"BENCH INVALID: expected 3 brains, got "
                         f"{sorted(cb.brain_bodies)}")
    ident = bytes((0x78, 0xFF, 0x05))                # obj(uid=255).f[5]
    if not all(ident in cb.brain_bodies[c] for c in ("knight", "mu")):
        raise SystemExit("BENCH INVALID: no identity reads in a class brain")
    new_bytes = (len(cb.ticker_body) + len(cb.main_init)
                 + sum(len(b) for b in cb.duty_bodies.values())
                 + sum(len(b) for b in cb.brain_bodies.values())
                 + sum(len(b) for fns in cb.action_funcs.values()
                       for _t2, b in fns))
    brains_total = sum(len(b) for b in cb.brain_bodies.values())
    print(f"  THE CROSS-PRODUCT KILL: ISLES (unrolled ticker) {V1_ISLES_NEW}B new"
          f" / BRAWN (15 per-unit brains) {BRAWN_NEW}B new"
          f"  ->  this build {new_bytes}B new"
          f" ({100 * new_bytes // BRAWN_NEW}% of BRAWN), "
          f"{len(cb.brain_bodies)} brains {brains_total}B total")
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
                        str(REPO / "tools/scroll_out/layout_probe/classbrawl")])
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
  THE POINT: the proven 7v7 scoreboard brawl, but 14 brawlers now share TWO
  brains (one per class) instead of 15 — the verdict is PARITY with the
  remembered group-bench fight:
  1 the HUD strip reads KN 7 MU 7 DOWN 0 from boot and counts down live;
  2 after the warm-up both arcs charge, units pair off NEAREST, melee
    resolves, survivors pivot to the next closest foe;
  3 wounded units (1 hp) break off and run for their team corner;
  4 dead units VANISH cleanly and their 6 class-siblings FIGHT ON — a freeze
    or a whole team going limp when one dies means the shared-brain orphan
    handling failed (the sharpest new claim in this build);
  5 the crier: "First blood" / "Half the brawl has fallen" / the WIPE line
    the moment a strip counter hits 0;
  6 ~ -> Reload restarts clean (strip back to 7/7/0, everyone at their post).
  (Authored nuance, not a finding: flee refuge choice keys off mu0/kn0 as the
  representative threat — a class tree is one program.)
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("verb", choices=["gen", "probe", "deploy"])
    v = ap.parse_args().verb
    {"gen": gen, "probe": probe, "deploy": deploy}[v]()
