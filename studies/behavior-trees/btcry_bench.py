"""THE WAR-CRY BENCH — the one-shot family under CLASSES (30425, "BTCRY").

Brains-backend rung 2: `npcs = [...]` class rows may now carry the one-shot
family (announce / sfx / flash / stop_timer / battle) with ONCE-PER-MEMBER
latches — each member's latch is its own uid-indexed cell, written by that
member's dispatch body and read strided by the shared brain. Only the payout
verbs (award / shop) stay on single-npc rows.

TWO CLASSES, TWO MECHANISMS:
  * class "herald" — THREE knights spread across the plaza; each war-cries
    EXACTLY ONCE (event-once announce) the first time the player comes near
    HIM. Three knights = three cries, one .mes line; a knight who has cried
    stays silent forever (until ~ Reload re-arms all three).
  * class "tread" — TWO Mus wandering their posts; walking into one fires a
    REAL battle (scene 35, the donor arena fight — the field carries the
    proven timer=600 clock, THE CLOCK-COUPLED BATTLE LAW) exactly once PER
    MU. The battled latch is compiled construction: the returning tree
    re-selecting the branch can never re-swirl.

THE SHARPEST CLAIM — BRAINS SURVIVE A BATTLE ROUND-TRIP: the engine parks
the whole field EventContext at battle entry and restores it uid-keyed on
return (EventContext.copy; EnterBattleEnd suspends uid!=0 and the state0
wake resumes them, all cid-blind — engine-read, never before run in-game
under Seq brains). After the FIRST battle, every OTHER brain must still be
alive: un-cried knights still cry, and the SECOND Mu still fires its own
battle.

Usage (repo root):  py studies/behavior-trees/btcry_bench.py gen | probe | deploy
30425 is a NEW id -> the FIRST deploy needs a game RELAUNCH, then ~ -> Warp.
Revert: py tools/scroll_out/revert_deploy_30425.py
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import group_bench as gb                                           # noqa: E402
from group_bench import (BASE_TOML, DONOR, KNIGHT_MODEL, MU_MODEL,  # noqa: E402
                         REPO, _branch, _t, layout)

BENCH = gb.BENCH                          # same donor import as ISLES (reused)
BENCH_TOML = BENCH / "BTCRY.field.toml"
REPORT = BENCH / "btcry-report.txt"
FIELD_ID = 30425
FIELD_NAME = "BTCRY"
MOD_FOLDER = "FF9CustomMap"

HERALDS = ["kn0", "kn1", "kn2"]
TREADS = ["mu0", "mu1"]
BATTLE_SCENE = 35                        # the donor arena fight (condor-proven)
TIMER = 600                              # scene 35 is Hunt-family: it ends itself
                                         # at clock 0 -- keep a live countdown
                                         # (THE CLOCK-COUPLED BATTLE LAW)


def behavior_toml(lay: dict) -> str:
    parts = [f'\n[behavior]\nbrains = true\nwarmup = 45\ntimer = {TIMER}\n']
    parts.append(f'\n[[behavior.unit]]\nnpcs = {_t(HERALDS)}\nclass = "herald"\n')
    parts.append(_branch(when=[{"near": ["player", 300]}], once="cry",
                         do={"announce": "STAND AND BE COUNTED!  (This knight "
                                         "will never cry again.)"}))
    parts.append(_branch(do={"hold_post": True}))
    parts.append(f'\n[[behavior.unit]]\nnpcs = {_t(TREADS)}\nclass = "tread"\n')
    parts.append(_branch(when=[{"near": ["player", 220]}],
                         do={"battle": BATTLE_SCENE}))
    # per-member wander centers are not one program (wander_post isn't vocab):
    # the shared center sits between the two posts, radius small enough that
    # each Mu drifts around its own side of the box
    parts.append(_branch(do={"wander": list(lay["wander_c"]), "radius": 350,
                             "every": 70, "speed": 35}))
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
    # three heralds spread along the east arc (>=1200u apart -- each cry is
    # unambiguously ONE knight's); two treads on the west arc, far apart
    lay["heralds"] = [lay["kn"][0], lay["kn"][3], lay["kn"][6]]
    lay["treads"] = [lay["mu"][1], lay["mu"][5]]
    lay["wander_c"] = ((lay["treads"][0][0] + lay["treads"][1][0]) // 2,
                       (lay["treads"][0][1] + lay["treads"][1][1]) // 2)
    parts = [text, "\n# ---- THE WAR-CRY BENCH (generated by "
                   "studies/behavior-trees/btcry_bench.py) ----\n"]
    for i, name in enumerate(HERALDS):
        x, z = lay["heralds"][i]
        parts.append(f'\n[[npc]]\nname = "{name}"\nmodel = "{KNIGHT_MODEL}"\n'
                     f'pos = [{x}, {z}]\nface = 192\n'
                     f'dialogue = "One cry is all a knight owes the plaza."\n')
    for i, name in enumerate(TREADS):
        x, z = lay["treads"][i]
        parts.append(f'\n[[npc]]\nname = "{name}"\nmodel = "{MU_MODEL}"\n'
                     f'pos = [{x}, {z}]\nface = 64\n'
                     f'dialogue = "KWEH?  (It eyes you like a battle waiting '
                     f'to happen.  Once.)"\n')
    parts.append(behavior_toml(lay))

    _raw, fb, cb = _dry_build(parts)
    if set(cb.brain_bodies) != {"herald", "tread"}:
        raise SystemExit(f"BENCH INVALID: expected 2 class brains, got "
                         f"{sorted(cb.brain_bodies)}")
    if not fb.has_battle_actions():
        raise SystemExit("BENCH INVALID: no Battle -> no Main_Reinit would be "
                         "installed (the after-battle resume law)")
    ident = bytes((0x78, 0xFF, 0x05))                # obj(uid=255).f[5]
    for c in ("herald", "tread"):
        if ident not in cb.brain_bodies[c]:
            raise SystemExit(f"BENCH INVALID: no identity reads in brain {c!r}")
    for t in ("cls.herald.once.cry", "cls.herald.areq1",
              "cls.tread.battled1", "cls.tread.breq1"):
        if t not in fb._cls_tids:
            raise SystemExit(f"BENCH INVALID: strided one-shot table {t!r} "
                             f"missing ({sorted(fb._cls_tids)})")
    BENCH_TOML.write_text("".join(parts), encoding="utf-8")
    REPORT.write_text(cb.report, encoding="utf-8")
    print(f"wrote {BENCH_TOML}")
    print(f"  heralds {lay['heralds']}  treads {lay['treads']}")
    print(f"  report -> {REPORT}")


def probe() -> None:
    if not BENCH_TOML.exists():
        gen()
    r = subprocess.run([sys.executable, str(REPO / "tools" / "field_layout_probe.py"),
                        str(BENCH_TOML), "--out",
                        str(REPO / "tools/scroll_out/layout_probe/btcry")])
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
PLAYTEST ({FIELD_ID} is a NEW id -> RELAUNCH once, then ~ -> Warp -> {FIELD_ID}):
  THE POINT: the one-shot family now runs on CLASS rows, once PER MEMBER --
  and the first battle is the first ever fired under Seq brains.
  1 the countdown HUD shows (~10:00). Visit each of the THREE knights: each
    war-cries EXACTLY ONCE (3 cries total); re-approaching a knight who
    already cried = silence.
  2 walk into a Mu (~220u): battle swirl -> the arena fight (scene 35) ->
    win or flee -> CLEAN return to the plaza, that Mu wanders on, and
    re-approaching it NEVER re-swirls.
  3 THE SHARPEST CLAIM -- after that battle the other brains must still be
    alive: any un-cried knight still cries, and the SECOND Mu still fires
    ITS OWN battle (then never again).
  4 ~ -> Reload re-arms everything: 3 fresh cries, 2 fresh battles.
  (Fire the battles before the 10:00 clock runs out -- scene 35 is a Hunt
  fight and ends itself at 0:00: the clock-coupled battle law, not a bug.)
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("verb", choices=["gen", "probe", "deploy"])
    v = ap.parse_args().verb
    {"gen": gen, "probe": probe, "deploy": deploy}[v]()
