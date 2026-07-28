"""THE WAR-CRY BENCH — one-shots under CLASSES + THE INSTANCE BLOCK (30425).

Rung 2 (★ ratified round 1): `npcs = [...]` class rows carry the one-shot
family (announce / sfx / flash / stop_timer / battle) with ONCE-PER-MEMBER
latches. Rung 3 (★ ratified round 2): brain-PRIVATE state — sticky
once/cooldown latches + timers, patrol progress, wander state, the areq/breq
request flags — migrates into each Seq's own INSTANCE VARS (the entry's varn
block, P3-proven; zeroed at spawn = reset for free, one copy per Seq = per
member for free). Body-written latches (the event-once latch, battled) stay
outside-addressable.

Rung 4 (★ ratified round 2): REQSW TRANSITION DISPATCHES — THE DEATH
KNELL. THE MUST-LAND DISPATCH LAW (seqbrain P4): a lone REQ against a
busy unit drops SILENTLY forever; a transition-critical dispatch (Die) now
emits REQSW 0x12 — the brain Seq stays on the instruction until the unit's
level frees, then binds. The knell: stirring a Mu to battle raises the
"knell" flag, and a top-ranked die branch on the HERALD class drops all
three knights — a knight killed MID-FOLLOW is the flagship case (the sel
flip releases his looping chase body, the REQSW binds the die), composed
with the battle round-trip.

Rung 5 (THIS redeploy, zero-relaunch): INLINE ONE-SHOT BODIES — a PARITY
round. The one-shot request-lane bodies (the cry announce, the knell
announce, the battles) are global-op-only by audit, so they now run INLINE
in the shared brain behind THE FREE-GATE (`obj(uid=255).f[6] > 4` — the
engine's requestAcceptable READ instead of probed; getvobj case 6 =
obj.level): the per-member dispatch-body copies are GONE. Everything
ratified in rungs 2-4 must play IDENTICALLY. The free-gate's one visible
edge: a one-shot that triggers while you hold a unit's dialogue open
defers and fires the moment the dialogue closes.

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
                         KNIGHT_MODEL, MU_MODEL, REPO, _branch, _t,
                         lattice, layout, nearest)

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
    # THE DEATH KNELL (rung 4, top rank): when any Mu battle rings the knell,
    # every knight falls — kneel (hiza), hold, vanish. The die dispatch is the
    # REQSW must-land lane: a knight mid-FOLLOW has a looping chase body at
    # level 4; sel flips to die, the body exits its sel check, the REQSW binds.
    parts.append(_branch(when=[{"flag": "knell"}],
                         do={"die": True, "anim": "hiza_1", "linger": 60}))
    parts.append(_branch(when=[{"near": ["player", 300]}], once="cry",
                         do={"announce": "STAND AND BE COUNTED!  (This knight "
                                         "will never cry again.)"}))
    # THE STICKY ONCE, per member (Instance latch pair): follows while near,
    # latches forever the FIRST time the player escapes. THE HYSTERESIS LAW
    # (round-1 lesson): a sticky decorator's cond is both TRIGGER and KEEP —
    # at 280u (standoff 170) the first natural step back after the cry read
    # as "escaped" and latched instantly. 700u makes escape a real walk.
    parts.append(_branch(when=[{"near": ["player", 700]}], once="follow",
                         do={"chase": "player", "standoff": 170, "speed": 55}))
    parts.append(_branch(do={"hold_post": True}))
    parts.append(f'\n[[behavior.unit]]\nnpcs = {_t(TREADS)}\nclass = "tread"\n')
    # the battle branch RINGS THE KNELL (raise_flags is sticky — the heralds'
    # die branch keys on it forever after, Reload re-arms everything)
    parts.append(_branch(when=[{"near": ["player", 220]}],
                         do={"battle": BATTLE_SCENE}, raise_flags=["knell"]))
    # ROUND 2 — ring the knell EARLY (400u, outside battle range): round 1
    # rang knell+battle on the SAME tick, so the field suspended before the
    # heralds' brains could react and the death beat played half-eaten by
    # the swirl-back. At 400u the kneel+linger+vanish plays IN THE OPEN,
    # ~180u of walking before the swirl. The battle branch keeps its own
    # ring as the belt (a fast run-in still fells the knights).
    parts.append(_branch(when=[{"near": ["player", 400]}], once="knell",
                         do={"announce": "THE KNELL TOLLS.  (Somewhere east, "
                                         "the knights are falling.)"},
                         raise_flags=["knell"]))
    # per-member wander centers are not one program (wander_post isn't vocab):
    # the shared center sits between the two posts, radius small enough that
    # each Mu drifts around its own side of the box
    parts.append(_branch(do={"wander": list(lay["wander_c"]), "radius": 250,
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
    # the wander box must sit on OPEN ground — the arc midpoint put it on the
    # monument's west bulge and the Mus ground the wall (round 1). Anchor it
    # on the clearance-filtered lattice, well west of the centerpiece.
    _pts, clear = lattice()
    lay["wander_c"] = nearest(clear, -1700, 0)
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
    need = [("herald", "areq"), ("herald", "once.follow"), ("tread", "breq"),
            ("tread", "wtimer"), ("stalker", "wp")]      # areq/breq are aid-
    for ow, key in need:                                 # numbered: prefix match
        if not any(o == ow and k.startswith(key) for o, k in fb._inst_slots):
            raise SystemExit(f"BENCH INVALID: Instance slot {(ow, key)}* missing")
    if not all(cb.brain_locs.get(c, 0) > 0 for c in ("herald", "tread", "stalker")):
        raise SystemExit(f"BENCH INVALID: empty instance block ({cb.brain_locs})")
    # RUNG 4 — THE MUST-LAND DISPATCH LAW: the herald die rides REQSW 0x12
    # (block-until-free), with no droppable REQ twin; the dieless brains
    # carry no REQSW at all (routine dispatches keep the drop-on-busy REQ)
    reqsw = bytes((0x12, 0x00, 0x04, 0xFF))          # REQSW lvl 4 -> uid 255
    hb = cb.brain_bodies["herald"]
    if hb.count(reqsw) != 1:
        raise SystemExit(f"BENCH INVALID: expected ONE REQSW die dispatch in "
                         f"the herald brain, found {hb.count(reqsw)}")
    dtag = hb[hb.index(reqsw) + 4]
    if bytes((0x10, 0x00, 0x04, 0xFF, dtag)) in hb:
        raise SystemExit("BENCH INVALID: the die tag also has a droppable REQ")
    for c in ("tread", "stalker"):
        if bytes((0x12, 0x00, 0x04)) in cb.brain_bodies[c]:
            raise SystemExit(f"BENCH INVALID: REQSW in dieless brain {c!r}")
    # RUNG 5 — INLINE ONE-SHOTS: every request-lane body runs in the brain
    # behind THE FREE-GATE (obj(255).f[6] = the unit's script level); the
    # per-member copies are gone. herald = the cry lane; tread = the knell
    # announce + the battle (0x2A inline); stalker has no one-shots.
    fgate = bytes((0x78, 0xFF, 0x06))
    want = {"herald": 1, "tread": 2, "stalker": 0}
    for c, n in want.items():
        got = cb.brain_bodies[c].count(fgate)
        if got != n:
            raise SystemExit(f"BENCH INVALID: brain {c!r} has {got} free-gates, "
                             f"expected {n}")
    if bytes((0x2A, 0x00, 0x00, BATTLE_SCENE, 0)) not in cb.brain_bodies["tread"]:
        raise SystemExit("BENCH INVALID: the battle is not inline in the tread brain")
    for m in HERALDS + TREADS:
        bodies = b"".join(b for _t, b in cb.action_funcs[m])
        if bytes((0x2A, 0x00)) in bodies:
            raise SystemExit(f"BENCH INVALID: member {m!r} still carries a "
                             f"battle dispatch body")
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
  THE POINT (rung 5): INLINE ONE-SHOT BODIES -- a PARITY round. The cry
  announce, the knell announce, and the battles now run INLINE in the
  shared brains (no per-member body copies) behind THE FREE-GATE.
  EVERYTHING from the ratified rounds must play IDENTICALLY:
  1 the KNIGHTS first (east arc): first approach = ONE war cry each, then
    he FOLLOWS while near; escape latches him silent + still forever.
    Keep one knight following for step 3.
  2 THE FREE-GATE (the one new observable): walk up to a FRESH knight and
    TALK to him fast, holding the dialogue open -- his war cry must pop
    RIGHT AFTER your dialogue closes (deferred, never lost, never during).
  3 THE DEATH KNELL: walk west toward a Mu -- at ~400u "THE KNELL TOLLS"
    pops and ALL THREE knights fall (kneel, hold, vanish, in the open);
    the mid-follow one is the flagship. THEN step in (~220u): the battle
    swirl (now fired INLINE from the brain), arena fight, clean return.
  4 the STALKERS: chase/escape/2.5s-cooldown/patrol, repeatable forever,
    still working AFTER the battle + the knell.
  5 the SECOND Mu still fires its own battle once, wander continues after.
    (Beat the 10:00 clock -- scene 35 ends itself at 0:00, the law.)
  6 ~ -> Reload re-arms the WHOLE world: knights back, 3 cries, knell
    cleared, 2 fresh battles, stalkers from their posts.
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("verb", choices=["gen", "probe", "deploy"])
    v = ap.parse_args().verb
    {"gen": gen, "probe": probe, "deploy": deploy}[v]()
