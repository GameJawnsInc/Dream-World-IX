"""THE WAR-CRY BENCH — one-shots under CLASSES + THE INSTANCE BLOCK (30425).

Rung 2 (★ ratified round 1): `npcs = [...]` class rows carry the one-shot
family (announce / sfx / flash / stop_timer / battle) with ONCE-PER-MEMBER
latches. Rung 3 (THIS redeploy, zero-relaunch): brain-PRIVATE state — sticky
once/cooldown latches + timers, patrol progress, wander state, the areq/breq
request flags — migrates into each Seq's own INSTANCE VARS (the entry's varn
block, P3-proven; zeroed at spawn = reset for free, one copy per Seq = per
member for free). Body-written latches (the event-once latch, battled) stay
outside-addressable. The rung-3 additions to the cast exercise every migrated
slot family in-game.

THE CLASSES AND THEIR MECHANISMS:
  * class "herald" — THREE knights spread across the plaza; each war-cries
    EXACTLY ONCE (event-once announce; areq now Instance) the first time the
    player nears HIM — and then FOLLOWS the player while near, until the
    player first escapes: the STICKY ONCE (Instance latch pair, per knight).
    A knight who has cried and been escaped is silent AND stationary forever
    (until ~ Reload re-arms all three).
  * class "tread" — TWO Mus wandering their posts (wander state = Instance);
    walking into one fires a REAL battle (scene 35; timer=600 per THE
    CLOCK-COUPLED BATTLE LAW) exactly once PER MU (breq now Instance; the
    battled latch stays a strided cell — the body writes it).
  * class "stalker" — TWO Mus patrolling ONE SHARED CHORD at their OWN
    Instance wp progress (start at opposite ends — if progress were shared
    they would snap together); a Cooldown(150) chase: chases when near,
    re-engages only ~2.5s AFTER you escape (Instance timer, ticked by the
    brain itself).

STILL STANDING FROM RUNG 2: brains survive the battle round-trip — after the
first battle every other brain (cries, follows, stalkers, the second Mu's
battle) must still be alive.

Usage (repo root):  py studies/behavior-trees/btcry_bench.py gen | probe | deploy
30425 is REGISTERED -> a redeploy needs NO relaunch: ~ -> Reload (or Warp).
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
from group_bench import (BASE_TOML, CRIER_MODEL, DONOR,             # noqa: E402
                         KNIGHT_MODEL, MU_MODEL, REPO, _branch, _t, layout)

BENCH = gb.BENCH                          # same donor import as ISLES (reused)
BENCH_TOML = BENCH / "BTCRY.field.toml"
REPORT = BENCH / "btcry-report.txt"
FIELD_ID = 30425
FIELD_NAME = "BTCRY"
MOD_FOLDER = "FF9CustomMap"

HERALDS = ["kn0", "kn1", "kn2"]
TREADS = ["mu0", "mu1"]
STALKERS = ["st0", "st1"]
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
    # THE STICKY ONCE, per member (Instance latch pair): follows while near,
    # latches forever the FIRST time the player escapes
    parts.append(_branch(when=[{"near": ["player", 280]}], once="follow",
                         do={"chase": "player", "standoff": 170, "speed": 55}))
    parts.append(_branch(do={"hold_post": True}))
    parts.append(f'\n[[behavior.unit]]\nnpcs = {_t(TREADS)}\nclass = "tread"\n')
    parts.append(_branch(when=[{"near": ["player", 220]}],
                         do={"battle": BATTLE_SCENE}))
    # per-member wander centers are not one program (wander_post isn't vocab):
    # the shared center sits between the two posts, radius small enough that
    # each Mu drifts around its own side of the box
    parts.append(_branch(do={"wander": list(lay["wander_c"]), "radius": 350,
                             "every": 70, "speed": 35}))
    parts.append(f'\n[[behavior.unit]]\nnpcs = {_t(STALKERS)}\nclass = "stalker"\n')
    # THE COOLDOWN (Instance timer, brain-ticked): re-engages ~2.5s after escape
    parts.append(_branch(cooldown=150, when=[{"near": ["player", 500]}],
                         do={"chase": "player", "standoff": 170, "speed": 60}))
    # ONE shared chord, walked at each Seq's OWN Instance wp progress (the two
    # start at opposite ends — shared progress would snap them together)
    parts.append(_branch(do={"patrol": [list(lay["stalkers"][0]),
                                        list(lay["stalkers"][1])],
                             "arrive_r": 150, "speed": 40}))
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
    lay["stalkers"] = [lay["mu"][0], lay["mu"][3]]     # the shared patrol chord
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
    for i, name in enumerate(STALKERS):
        x, z = lay["stalkers"][i]
        parts.append(f'\n[[npc]]\nname = "{name}"\nmodel = "{CRIER_MODEL}"\n'
                     f'pos = [{x}, {z}]\nface = 64\n'
                     f'dialogue = "I walk my half of the line.  Come close and '
                     f'I follow -- for a while."\n')
    parts.append(behavior_toml(lay))

    _raw, fb, cb = _dry_build(parts)
    if set(cb.brain_bodies) != {"herald", "tread", "stalker"}:
        raise SystemExit(f"BENCH INVALID: expected 3 class brains, got "
                         f"{sorted(cb.brain_bodies)}")
    if not fb.has_battle_actions():
        raise SystemExit("BENCH INVALID: no Battle -> no Main_Reinit would be "
                         "installed (the after-battle resume law)")
    ident = bytes((0x78, 0xFF, 0x05))                # obj(uid=255).f[5]
    for c in ("herald", "tread", "stalker"):
        if ident not in cb.brain_bodies[c]:
            raise SystemExit(f"BENCH INVALID: no identity reads in brain {c!r}")
    # THE ELIGIBILITY LINE (rung 3): body-written latches stay strided tables;
    # everything brain-private rides each Seq's Instance block
    for t in ("cls.herald.once.cry", "cls.tread.battled1"):
        if t not in fb._cls_tids:
            raise SystemExit(f"BENCH INVALID: body-written latch table {t!r} "
                             f"missing ({sorted(fb._cls_tids)})")
    if any("areq" in t or "breq" in t or ".wt" in t or ".wp" in t
           or ".cd" in t for t in fb._cls_tids):
        raise SystemExit(f"BENCH INVALID: a brain-private slot still strided: "
                         f"{sorted(fb._cls_tids)}")
    need = [("herald", "areq1"), ("herald", "once.follow"), ("tread", "breq1"),
            ("tread", "wtimer"), ("stalker", "wp")]
    for ow, key in need:
        if (ow, key) not in fb._inst_slots:
            raise SystemExit(f"BENCH INVALID: Instance slot {(ow, key)} missing")
    if not all(cb.brain_locs.get(c, 0) > 0 for c in ("herald", "tread", "stalker")):
        raise SystemExit(f"BENCH INVALID: empty instance block ({cb.brain_locs})")
    print(f"  instance blocks (varn): "
          + ", ".join(f"{o}={n}B" for o, n in sorted(cb.brain_locs.items())))
    BENCH_TOML.write_text("".join(parts), encoding="utf-8")
    REPORT.write_text(cb.report, encoding="utf-8")
    print(f"wrote {BENCH_TOML}")
    print(f"  heralds {lay['heralds']}  treads {lay['treads']}  "
          f"stalkers {lay['stalkers']}")
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
PLAYTEST ({FIELD_ID} is REGISTERED -> NO relaunch: ~ -> Reload or Warp -> {FIELD_ID}):
  THE POINT (rung 3): every brain-private latch/timer now lives in Seq
  INSTANCE VARS -- per-member sticky once, brain-ticked cooldowns, private
  patrol progress, private wander state, the one-shot request lanes.
  1 the KNIGHTS (east arc, three of them): first approach = ONE war cry,
    then he FOLLOWS you while you stay near; ESCAPE once (walk well away)
    and that knight never follows again -- AND never cries. Each knight
    keeps his OWN latches (an untouched knight still cries + follows).
  2 the wandering MUS (west, two): walk in -> battle swirl -> arena fight ->
    clean return, no re-swirl ever from that Mu; the OTHER Mu still fires
    its own battle. (Before the 10:00 clock runs out -- scene 35 is a Hunt
    fight and ends itself at 0:00: the clock-coupled law, not a bug.)
  3 the STALKERS (two townsfolk pacing ONE line on the west side, starting
    at OPPOSITE ends -- each walks his own progress; if they ever snap
    together the private wp failed): come near -> a stalker chases; escape
    -> he resumes the line, and re-engages only ~2.5 SECONDS after you
    escaped (the cooldown) -- repeatable forever, per stalker.
  4 after the FIRST battle everything above must still work (brains survive
    the round-trip -- re-verified under Instance state).
  5 ~ -> Reload re-arms the world: 3 cries, 3 follows, 2 battles, fresh
    stalker patrol from their posts.
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("verb", choices=["gen", "probe", "deploy"])
    v = ap.parse_args().verb
    {"gen": gen, "probe": probe, "deploy": deploy}[v]()
