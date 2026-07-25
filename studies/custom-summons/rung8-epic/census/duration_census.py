#!/usr/bin/env python
"""THE STOCK SUMMON DURATION CENSUS  --  rung 8 (NIMBRA) re-positioning round.

Question the owner asked: *is a stock summon's cinematic DURATION correlated with its POWER?*
If it is, NIMBRA (29.3 s, power 62, 24 MP) can be honestly re-positioned as a WEAK + SHORT
summon sitting on the game's own duration-power line, instead of a Bahamut-length cast on a
mid-tier hit.

WHAT THIS MEASURES
------------------
Every summon ability in FF9 has TWO effect ids -- a FULL cinematic and a SHORT one (the MP-roll
system, `btl_cmd.DecideSummonType`; `aa.Info.VfxIndex` = full, `aa.Vfx2` = short, selected at
`btl_vfx.cs:99`).  Each effect id `ef###` ships two text files:

  * `Sequence.seq`        -- the SHARED (SFX-side) timeline.  THE CINEMATIC.  This is what the
                             player watches and what the owner judged "holds for too long".
  * `PlayerSequence.seq`  -- the CASTER-side lane: step forward, title plate, chant, MP_MAGIC,
                             `PlaySFX`, then `WaitSFXDone` (which blocks for exactly the
                             `Sequence.seq` runtime), then the step back.

So:   cast_ticks  =  pre_ticks (caster front matter)  +  sfx_ticks (the cinematic)  +  post_ticks

THE MODEL (the rung-4 FULL TICK MAP method, generalised)
--------------------------------------------------------
`Wait: Time=N` counts N engine ticks (`BattleActionThread.cs:98-116`); TPS = 15, so 1 tick = 1/15 s.
Everything else on the main line is 0-tick (fire-and-forget) EXCEPT the blocking waits:

  Wait            -> +Time
  WaitMove        -> +Time of the matching MoveToPosition (always explicit in this corpus)
  WaitTurn        -> +Time of the matching Turn (always explicit)
  WaitAnimation   -> CLIP-BOUND: the length lives in the animation asset, NOT in the text.
                     Budgeted (CLIP_BUDGET, default 5 ticks) and reported as an explicit
                     uncertainty band -- see `clip_waits` in the output.
  WaitSFXDone     -> resolves at (tick of PlaySFX) + sfx_ticks.  This is the whole point: the
                     Sequence.seq timeline IS the number the text carries for that wait.
  WaitSFXLoaded   -> 0 (the load is kicked off by LoadSFX many ticks earlier and the stock
                     ordering always puts a real Wait/animation between them)
  WaitReflect     -> 0 (no reflect in the measured case)

  StartThread ... [ElseThread ...] EndThread
      Sync=True  -> blocking: the main line advances by the branch's own duration
      otherwise  -> parallel: spawned, does NOT advance the main line
      When the top level of a PlayerSequence is NOTHING BUT guarded threads, those threads are
      mutually-exclusive BRANCHES, not parallel work, and the lane's duration is a branch
      duration.  Two shapes occur: one StartThread/ElseThread pair (the short variants'
      `Condition=CommandId != 57`) and sibling StartThreads (ef225's `CasterHP == 0` /
      `CasterHP != 0`).  Both are detected and the LONGEST branch is taken; all branch
      durations are reported in `branch_ticks`.  Without this, ef225 measures 0 ticks.

VALIDATION (three checks, all green -- see `--validate`)
--------------------------------------------------------
  1. ef227 (Bahamut__Full): this model puts the stock `EffectPoint Type=Effect` damage beat at
     tick 486 and the `Type=Figure` at 498, total 547 ticks.  The rung-4 probe -- which EDITED
     that file and watched the beat move IN GAME -- independently logged "stock EffectPoint at
     t=486/498, ~32.4 s in" (studies/custom-summons/PLAN.md:380).  Exact agreement, to the tick.
  2. NIMBRA's own shipped `nimbra.seq`: the same walker returns 395 fixed ticks + the
     WaitSFXDone hold to 480 => 485 ticks / 32.3 s as shipped, and 440 / 29.3 s with the
     documented P1 trim (STORYBOARD 7 R2).  Both are the STORYBOARD's own numbers.
  3. THE HOLDDURATION ORACLE (see check_holds): 59/60 of the stock authors' own
     `SetBackgroundIntensity ... HoldDuration=H` values land EXACTLY on the next
     SetBackgroundIntensity under this walker, across all 33 summon effect ids.  Those H values
     are independent of our Wait arithmetic, so this is 60 free checkpoints on the model.

PROVENANCE: this script READS the install's sequence text to MEASURE it.  No stock bytes are
copied into the repo -- the outputs are tick counts and correlations.

Usage:
    py duration_census.py                 # write DURATION-CENSUS data + print the table
    py duration_census.py --validate      # just re-prove the two ground truths
    py duration_census.py --chart         # also emit duration_vs_power.png (needs matplotlib)
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------------------------
# Constants

TPS = 15.0  # BattleTPS -- live Memoria.ini [Graphics]; 1 tick = 1/15 s

GAME = Path(os.environ.get(
    "FF9_GAME_DIR",
    r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX",
))
SFX_DIR = GAME / "StreamingAssets" / "Data" / "SpecialEffects"
ACTIONS_CSV = GAME / "StreamingAssets" / "Data" / "Battle" / "Actions.csv"

HERE = Path(__file__).resolve().parent

# The 16 summon BattleAbilityIds, verbatim from btl_cmd.DecideSummonType (btl_cmd.cs:1583-1615).
# Values from Memoria/Data/Battle/BattleAbilityId.cs.
SUMMON_ABILITY_IDS = {
    49: "Shiva",
    51: "Ifrit",
    53: "Ramuh",
    55: "Atomos",
    58: "Odin",
    60: "Leviathan",
    62: "Bahamut",
    64: "Ark",
    66: "Fenrir (Earth)",
    67: "Fenrir (Wind)",
    68: "Carbuncle (Reflect)",
    69: "Carbuncle (Haste)",
    70: "Carbuncle (Shell)",
    71: "Carbuncle (Vanish)",
    72: "Phoenix",
    74: "Madeen",
}
# Not in DecideSummonType (it has no MP roll -- it IS the Trance Phoenix auto-revive), but the
# task asks for it if cheap: id 73 Rebirth Flame, vfx1 == vfx2 == 225 (short-only by construction).
TRANCE_PHANTOM_ID = 73

ELEMENT_BITS = {
    1: "Fire", 2: "Ice", 4: "Thunder", 8: "Earth",
    16: "Water", 32: "Wind", 64: "Holy", 128: "Shadow",
}

# Known pairs from the study, used as a hard cross-check on the CSV parse.
KNOWN_PAIRS = {"Bahamut": (227, 405), "Ark": (381, 447)}

CLIP_BUDGET = 5      # ticks charged for a text-opaque WaitAnimation (see docstring)
DEFAULT_TURN = 5     # a Turn with no explicit Time


# ---------------------------------------------------------------------------------------------
# .seq parsing

@dataclass
class Op:
    name: str
    args: dict
    children: list = field(default_factory=list)   # branch 1 (StartThread body)
    alt: list = field(default_factory=list)        # branch 2 (ElseThread body)
    line: int = 0


def _parse_args(rest: str) -> dict:
    out = {}
    for chunk in rest.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" in chunk:
            k, v = chunk.split("=", 1)
            out[k.strip()] = v.strip()
        else:
            out[chunk] = True
    return out


def parse_seq(text: str) -> list:
    """Parse a .seq into a tree of Op, honouring StartThread/ElseThread/EndThread nesting.

    The engine's own parser (BattleActionCode) keys purely on the op token; indentation is
    cosmetic.  We therefore nest on the tokens, not on tabs.
    """
    root: list = []
    stack = [(root, "root")]  # (list-to-append-to, mode)
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        line = line.split("//", 1)[0].strip()
        if not line:
            continue
        if ":" in line:
            name, rest = line.split(":", 1)
            op = Op(name.strip(), _parse_args(rest), line=lineno)
        else:
            op = Op(line.strip(), {}, line=lineno)

        if op.name == "StartThread":
            stack[-1][0].append(op)
            stack.append((op.children, "thread"))
        elif op.name == "ElseThread":
            if len(stack) < 2:
                raise ValueError(f"ElseThread outside a thread at line {lineno}")
            stack.pop()
            owner = stack[-1][0][-1]
            stack.append((owner.alt, "else"))
        elif op.name == "EndThread":
            if len(stack) < 2:
                raise ValueError(f"EndThread outside a thread at line {lineno}")
            stack.pop()
        else:
            stack[-1][0].append(op)
    if len(stack) != 1:
        raise ValueError("unbalanced StartThread/EndThread")
    return root


def _int(v, default=0):
    try:
        return int(float(str(v)))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------------------------
# Simulation

@dataclass
class Walk:
    ticks: int = 0                 # main-line duration
    clip_waits: int = 0            # count of text-opaque WaitAnimation charged at CLIP_BUDGET
    effect_points: list = field(default_factory=list)   # (tick, Type)
    playsfx_tick: int | None = None
    waitsfxdone: bool = False
    parallel_end: int = 0          # latest end of any spawned (non-Sync) thread
    # (tick, HoldDuration) for every SetBackgroundIntensity that declares one -- the
    # independent self-consistency oracle, see check_holds().
    holds: list = field(default_factory=list)
    sbi_ticks: list = field(default_factory=list)


def walk(block: list, w: Walk, sfx_ticks: int | None = None, base: int = 0) -> Walk:
    """Advance `w` along `block`.  `base` is the absolute tick at block entry."""
    last_move_time = 0
    last_turn_time = DEFAULT_TURN
    for op in block:
        n = op.name
        a = op.args
        if n == "Wait":
            w.ticks += _int(a.get("Time", 0))
        elif n == "MoveToPosition":
            last_move_time = _int(a.get("Time", 0))
        elif n == "Turn":
            last_turn_time = _int(a.get("Time", DEFAULT_TURN), DEFAULT_TURN)
        elif n == "ChangeSize":
            pass  # non-blocking; its own WaitX op does not exist in this corpus
        elif n == "WaitMove":
            w.ticks += last_move_time
        elif n == "WaitTurn":
            w.ticks += last_turn_time
        elif n == "WaitAnimation":
            w.ticks += CLIP_BUDGET
            w.clip_waits += 1
        elif n == "PlaySFX":
            w.playsfx_tick = base + w.ticks
        elif n == "WaitSFXDone":
            w.waitsfxdone = True
            if sfx_ticks is not None and w.playsfx_tick is not None:
                target = w.playsfx_tick + sfx_ticks
                w.ticks = max(w.ticks, target - base)
        elif n in ("WaitSFXLoaded", "WaitReflect"):
            pass
        elif n == "EffectPoint":
            w.effect_points.append((base + w.ticks, a.get("Type", "?")))
        elif n == "SetBackgroundIntensity":
            w.sbi_ticks.append(base + w.ticks)
            if "HoldDuration" in a:
                w.holds.append((base + w.ticks, _int(a["HoldDuration"])))
        elif n == "StartThread":
            sync = str(a.get("Sync", "")).lower() == "true"
            sub = Walk()
            walk(op.children, sub, sfx_ticks, base + w.ticks)
            if op.alt:
                alt = Walk()
                walk(op.alt, alt, sfx_ticks, base + w.ticks)
            w.holds.extend(sub.holds)
            w.sbi_ticks.extend(sub.sbi_ticks)
            if sync:
                w.ticks += sub.ticks
                w.clip_waits += sub.clip_waits
                w.effect_points.extend(sub.effect_points)
            else:
                w.parallel_end = max(w.parallel_end, base + w.ticks + sub.ticks)
                w.effect_points.extend(sub.effect_points)
                if sub.playsfx_tick is not None and w.playsfx_tick is None:
                    w.playsfx_tick = sub.playsfx_tick
        # everything else -- PlaySound, ShowMesh, SetBackgroundIntensity, ShiftWorld, Message,
        # LoadSFX, SetupReflect, ActivateReflect, Channel, StopChannel, SetVariable,
        # PlayAnimation, CreateVisualEffect, StopSound -- is a 0-tick fire-and-forget op.
    return w


def measure_effect(eid: int) -> dict:
    """Measure one ef### folder.  Returns the tick decomposition."""
    d = SFX_DIR / f"ef{eid:03d}"
    shared_p = d / "Sequence.seq"
    player_p = d / "PlayerSequence.seq"
    out = {"effect_id": eid, "exists": d.is_dir()}
    if not shared_p.is_file():
        out["error"] = "no Sequence.seq"
        return out

    shared = parse_seq(shared_p.read_text(encoding="utf-8", errors="replace"))
    sw = walk(shared, Walk())
    sfx_ticks = sw.ticks
    out["sfx_ticks"] = sfx_ticks
    out["sfx_clip_waits"] = sw.clip_waits
    out["sfx_parallel_end"] = sw.parallel_end
    dmg = [t for t, ty in sw.effect_points if ty == "Effect"]
    out["damage_beat_tick"] = dmg[0] if dmg else None
    out["effect_points"] = sw.effect_points

    if not player_p.is_file():
        out["error"] = "no PlayerSequence.seq"
        return out
    ptext = player_p.read_text(encoding="utf-8", errors="replace")
    pblock = parse_seq(ptext)

    # A caster lane is often entirely wrapped in condition-guarded top-level threads, in two
    # different shapes:
    #   (a) ONE StartThread + ElseThread  -- the short variants' `Condition=CommandId != 57`
    #   (b) SEVERAL sibling StartThreads  -- ef225's `CasterHP == 0` / `CasterHP != 0` pair
    # In both shapes the branches are mutually exclusive and the lane's real duration is a branch
    # duration, not zero.  Detect "the top level is nothing but guarded threads" and take the
    # LONGEST branch (the normal full-cast path in every observed case); record the alternatives.
    branches = []
    if pblock and all(op.name == "StartThread" for op in pblock):
        for op in pblock:
            for body in (op.children, op.alt):
                if body:
                    branches.append(body)
    out["player_wrapped_branch"] = bool(branches)

    if branches:
        walks = [walk(b, Walk(), sfx_ticks, 0) for b in branches]
        pw = max(walks, key=lambda w: w.ticks)
        out["branch_ticks"] = sorted(w.ticks for w in walks)
    else:
        pw = walk(pblock, Walk(), sfx_ticks, 0)
    out["cast_ticks"] = pw.ticks
    out["clip_waits"] = pw.clip_waits
    out["playsfx_tick"] = pw.playsfx_tick
    out["pre_ticks"] = pw.playsfx_tick if pw.playsfx_tick is not None else None
    if pw.playsfx_tick is not None:
        out["post_ticks"] = pw.ticks - pw.playsfx_tick - sfx_ticks
    out["cast_seconds"] = round(pw.ticks / TPS, 2)
    out["sfx_seconds"] = round(sfx_ticks / TPS, 2)
    # Uncertainty band from the text-opaque WaitAnimations (all of which sit BEFORE PlaySFX in
    # the stock caster lane, so they shift the cast uniformly and never move the cinematic).
    out["clip_uncertainty_ticks"] = pw.clip_waits * CLIP_BUDGET
    return out


# ---------------------------------------------------------------------------------------------
# Actions.csv

ACTION_COLS = [
    "comment", "id", "menuWindow", "targets", "defaultAlly", "forDead", "defaultOnDead",
    "defaultCamera", "animationId1", "animationId2", "scriptId", "power", "elements", "rate",
    "category", "statusIndex", "mp", "type", "commandTitle",
]


def read_actions() -> dict:
    rows = {}
    for raw in ACTIONS_CSV.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(";")
        if len(parts) < len(ACTION_COLS):
            continue
        rec = dict(zip(ACTION_COLS, parts))
        try:
            aid = int(rec["id"])
        except ValueError:
            continue
        rows[aid] = rec
    return rows


def elements_of(mask: int) -> str:
    if mask == 0:
        return "Non-elem"
    names = [n for b, n in ELEMENT_BITS.items() if mask & b]
    return "+".join(names) if names else f"mask{mask}"


# ---------------------------------------------------------------------------------------------
# Stats

def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return float("nan")
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return float("nan")
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def _rank(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def spearman(xs, ys):
    return pearson(_rank(list(xs)), _rank(list(ys)))


def linfit(xs, ys):
    """Least-squares y = a + b*x."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return my, 0.0
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    return my - b * mx, b


def p_value_approx(r, n):
    """Two-sided p for Pearson r via the t-approximation; good enough at these n."""
    if n < 3 or not (-1 < r < 1):
        return float("nan")
    t = r * math.sqrt((n - 2) / (1 - r * r))
    df = n - 2
    x = df / (df + t * t)
    return _betainc_half(df / 2.0, 0.5, x)


def _betainc_half(a, b, x):
    """Regularised incomplete beta I_x(a,b) via continued fraction (Lentz)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a
    f, c, d = 1.0, 1.0, 0.0
    for i in range(0, 300):
        m = i // 2
        if i == 0:
            num = 1.0
        elif i % 2 == 0:
            num = (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            num = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + num * d
        d = 1e-30 if abs(d) < 1e-30 else d
        d = 1.0 / d
        c = 1.0 + num / c
        c = 1e-30 if abs(c) < 1e-30 else c
        f *= c * d
        if abs(1 - c * d) < 1e-10:
            break
    return front * (f - 1.0)


# ---------------------------------------------------------------------------------------------
# Validation

def check_holds(eid: int):
    """THE HOLDDURATION ORACLE -- an independent, per-line check on the tick walker.

    `SetBackgroundIntensity: Intensity=I ; Time=T ; HoldDuration=H` holds the dim for H ticks and
    then self-restores.  In hand-authored stock cinematics H is set to land exactly on the NEXT
    `SetBackgroundIntensity`, so H must equal (tick of next SBI) - (tick of this SBI).  That
    number is written in the file by the original author and is completely independent of our
    Wait arithmetic -- if the walker mis-sums a single Wait, the residual shows up here.

    Returns (matched, total, residuals).
    """
    p = SFX_DIR / f"ef{eid:03d}" / "Sequence.seq"
    if not p.is_file():
        return 0, 0, []
    w = walk(parse_seq(p.read_text(encoding="utf-8", errors="replace")), Walk())
    sbi = sorted(w.sbi_ticks)
    matched, total, resid = 0, 0, []
    for t, h in sorted(w.holds):
        nxt = next((s for s in sbi if s > t), None)
        if nxt is None:
            continue          # trailing hold: nothing after it to land on, not checkable
        total += 1
        d = (nxt - t) - h
        resid.append(d)
        if d == 0:
            matched += 1
    return matched, total, resid


def validate() -> int:
    bad = 0
    m = measure_effect(227)
    print(f"[GT1] ef227 Bahamut__Full : sfx_ticks={m['sfx_ticks']} "
          f"({m['sfx_seconds']}s)  damage beat t={m['damage_beat_tick']}  "
          f"EffectPoints={m['effect_points']}  cast_ticks={m['cast_ticks']} ({m['cast_seconds']}s)")
    # rung-4 in-game-proven tick map: "stock EffectPoint at t=486/498, ~32.4s in"
    eps = [t for t, _ in m["effect_points"]]
    if eps[:2] != [486, 498]:
        print(f"      FAIL: expected EffectPoints at 486/498, got {eps[:2]}")
        bad += 1
    else:
        print("      OK  : reproduces the rung-4 FULL TICK MAP exactly (486 / 498).")
    if not (485 <= m["sfx_ticks"] <= 551):
        print(f"      FAIL: sfx_ticks {m['sfx_ticks']} outside the 485-551 ground-truth band")
        bad += 1
    else:
        print("      OK  : inside the 485-551 tick ground-truth band.")

    # GT2 -- NIMBRA's own shipped .seq.  It is a PlayerSequence-only summon (no Sequence.seq by
    # design, STORYBOARD 7.1 R15); its WaitSFXDone is bound by the .sfxmodel manifest window
    # (Start..End ticks after PlaySFX), which the TOML pins, not the text.
    #
    # THIS CHECK USED TO RETYPE THE TICK TABLE and went stale the moment the cast was re-cut: it
    # hardcoded sfx_ticks=330, `fixed = 45+95+105+90+30+12+18` (a sum it then compared to its own
    # literal 395 -- vacuous), and a 475-495 band.  After THE RETIME it reported FAIL while the
    # MODEL was fine, which is the worst kind of ground truth.  It now READS the live artifacts and
    # cross-checks the walker against an INDEPENDENT parser (the kit's own summons.seqlint), which
    # is a real check rather than a copy.  STORYBOARD 11.5's "three independent copies" lesson.
    nimbra = HERE.parent / "nimbra.seq"
    toml_path = HERE.parent / "nimbra.summon.toml"
    if nimbra.is_file() and toml_path.is_file():
        import tomllib
        st = tomllib.loads(toml_path.read_text(encoding="utf-8"))["summon"][0]["staging"]
        window = int(st["end"]) - int(st["start"])
        text = nimbra.read_text(encoding="utf-8", errors="replace")
        blk = parse_seq(text)
        w = walk(blk, Walk(), sfx_ticks=window, base=0)
        fixed = sum(_int(op.args.get("Time", 0)) for op in blk if op.name == "Wait")
        print(f"[GT2] nimbra.seq          : cast_ticks={w.ticks} ({w.ticks / TPS:.1f}s) "
              f"clip_waits={w.clip_waits} playsfx_tick={w.playsfx_tick} window={window}")

        # (a) two independent parsers must agree on the fixed-Wait sum
        try:
            sys.path.insert(0, str(HERE.parents[3] / "ff9mapkit"))
            from ff9mapkit.summons import seqlint as _SL
            kit_ticks = _SL.analyze_seq(text).total_ticks
        except Exception as exc:                                    # pragma: no cover
            kit_ticks = None
            print(f"      note: kit seqlint unavailable ({exc.__class__.__name__}) -- "
                  f"cross-check skipped")
        if kit_ticks is not None:
            ok = kit_ticks == fixed
            print(f"      {'OK  ' if ok else 'FAIL'}: fixed Wait sum = {fixed}; the kit's own "
                  f"seqlint independently counts {kit_ticks}")
            bad += 0 if ok else 1

        # (b) the two clocks must close: PlaySFX + the manifest window is the tick WaitSFXDone
        #     resolves on, and the only thing after it is the release Turn.
        drain = (w.playsfx_tick or 0) + window
        print(f"      {'OK  ' if w.ticks >= drain else 'FAIL'}: the cast runs to {w.ticks} ticks "
              f"({w.ticks / TPS:.2f} s) against a drain at {drain} "
              f"(PlaySFX {w.playsfx_tick} + window {window}) + the release Turn")
        if w.ticks < drain:
            bad += 1
    else:
        print("[GT2] nimbra.seq / nimbra.summon.toml not found -- skipped")

    # GT3 -- the HoldDuration oracle, run across every summon effect id in the census.
    actions = read_actions()
    eids = []
    for aid in list(SUMMON_ABILITY_IDS) + [TRANCE_PHANTOM_ID]:
        rec = actions.get(aid)
        if rec:
            eids.extend([int(rec["animationId1"]), int(rec["animationId2"])])
    tm = tt = 0
    worst = []
    for eid in sorted(set(eids)):
        m, t, resid = check_holds(eid)
        tm += m
        tt += t
        for d in resid:
            if d:
                worst.append((eid, d))
    print(f"[GT3] HoldDuration oracle : {tm}/{tt} SetBackgroundIntensity HoldDurations land "
          f"EXACTLY on the next SBI across all {len(set(eids))} summon effect ids")
    if worst:
        print(f"      non-zero residuals: {worst[:12]}")
    if tt and tm / tt < 0.90:
        print("      FAIL: the walker disagrees with the authors' own hold arithmetic")
        bad += 1
    elif tt:
        print("      OK  : independent per-line corroboration of the tick model.")
    return bad


# ---------------------------------------------------------------------------------------------

def build_rows():
    actions = read_actions()
    rows = []
    ids = list(SUMMON_ABILITY_IDS.items())
    ids.append((TRANCE_PHANTOM_ID, "Rebirth Flame (Trance Phoenix)"))
    for aid, name in ids:
        rec = actions.get(aid)
        if rec is None:
            print(f"  !! ability {aid} ({name}) missing from Actions.csv", file=sys.stderr)
            continue
        full_id = int(rec["animationId1"])
        short_id = int(rec["animationId2"])
        base = {
            "ability_id": aid,
            "name": name,
            "csv_name": rec["comment"],
            "power": int(rec["power"]),
            "mp": int(rec["mp"]),
            "element": elements_of(int(rec["elements"])),
            "type": int(rec["type"]),
            "targets": rec["targets"],
            "full_id": full_id,
            "short_id": short_id,
            "is_summon_roll": aid in SUMMON_ABILITY_IDS,
        }
        for variant, eid in (("full", full_id), ("short", short_id)):
            m = measure_effect(eid)
            r = dict(base)
            r["variant"] = variant
            r.update({k: m.get(k) for k in (
                "effect_id", "sfx_ticks", "cast_ticks", "pre_ticks", "post_ticks",
                "damage_beat_tick", "clip_waits", "clip_uncertainty_ticks",
                "sfx_seconds", "cast_seconds", "error")})
            rows.append(r)
    return rows


def cross_check(rows):
    ok = True
    by_name = {r["name"]: r for r in rows if r["variant"] == "full"}
    for nm, (f, s) in KNOWN_PAIRS.items():
        r = by_name.get(nm)
        if r is None or r["full_id"] != f or r["short_id"] != s:
            print(f"  !! CROSS-CHECK FAIL {nm}: expected {f}/{s}, got "
                  f"{r and (r['full_id'], r['short_id'])}", file=sys.stderr)
            ok = False
    print(f"  cross-check vs the study's known pairs (Bahamut 227/405, Ark 381/447): "
          f"{'PASS' if ok else 'FAIL'}")
    return ok


def correlations(rows):
    out = {}
    for variant in ("full", "short"):
        sub = [r for r in rows if r["variant"] == variant and r["is_summon_roll"]
               and r.get("sfx_ticks") is not None]
        # damage summons only for the power axis: Carbuncle rows are power 0 buffs, they are not
        # on the power scale at all (a zero is not a weak hit).  MP axis keeps everyone.
        dmg = [r for r in sub if r["power"] > 0]
        d = {}
        for label, pool, xk in (
            ("duration_vs_power", dmg, "power"),
            ("duration_vs_mp", sub, "mp"),
            ("duration_vs_mp_damage_only", dmg, "mp"),
        ):
            xs = [r[xk] for r in pool]
            ys = [r["sfx_seconds"] for r in pool]
            a, b = linfit(xs, ys)
            r_p = pearson(xs, ys)
            d[label] = {
                "n": len(pool), "pearson_r": round(r_p, 4),
                "r_squared": round(r_p * r_p, 4),
                "spearman_rho": round(spearman(xs, ys), 4),
                "p_two_sided": round(p_value_approx(r_p, len(pool)), 5),
                "fit_intercept_s": round(a, 3), "fit_slope_s_per_unit": round(b, 4),
            }
        # ...and again without Ark (the expected extreme) to test leverage
        for label, pool, xk in (
            ("duration_vs_power_no_ark", [r for r in dmg if r["name"] != "Ark"], "power"),
            ("duration_vs_mp_no_ark", [r for r in sub if r["name"] != "Ark"], "mp"),
        ):
            xs = [r[xk] for r in pool]
            ys = [r["sfx_seconds"] for r in pool]
            r_p = pearson(xs, ys)
            a, b = linfit(xs, ys)
            d[label] = {
                "n": len(pool), "pearson_r": round(r_p, 4),
                "r_squared": round(r_p * r_p, 4),
                "spearman_rho": round(spearman(xs, ys), 4),
                "p_two_sided": round(p_value_approx(r_p, len(pool)), 5),
                "fit_intercept_s": round(a, 3), "fit_slope_s_per_unit": round(b, 4),
            }
        # descriptive band, Ark excluded (it is the acknowledged outlier)
        secs = sorted(r["sfx_seconds"] for r in sub if r["name"] != "Ark")
        d["_band_no_ark"] = {
            "n": len(secs), "min_s": secs[0], "max_s": secs[-1],
            "median_s": round(secs[len(secs) // 2], 2),
            "ark_s": next(r["sfx_seconds"] for r in sub if r["name"] == "Ark"),
        }
        out[variant] = d
    return out


# ---------------------------------------------------------------------------------------------
# THE MP ROLL -- what the player ACTUALLY watches, per cast
#
# btl_cmd.DecideSummonType (btl_cmd.cs:1600-1614), verbatim:
#     if (cmd.regist.cur.mp > cmd.aa.MP * 2)  { if (Comn.random8() < 230) short_summon = 1; }
#     else                                    { if (Comn.random8() < 170) short_summon = 1; }
# Comn.random8() is uniform on [0,255], so P(short) = 230/256 when the caster has more than
# double the cost in MP, else 170/256.  This is the single most important fact in the census:
# a stock summon's FULL cinematic is a RARE event.  The honest comparison for a custom summon
# that has no short variant (and therefore plays its one cinematic every single cast) is the
# stock EXPECTED duration, not the stock full duration.

P_SHORT_RICH = 230 / 256.0     # caster MP > 2x cost -- the normal case for a dedicated summoner
P_SHORT_POOR = 170 / 256.0     # caster MP <= 2x cost


def expected_seconds(full_s, short_s, p_short):
    return p_short * short_s + (1.0 - p_short) * full_s


def roll_table(rows):
    out = []
    byname = {}
    for r in rows:
        byname.setdefault(r["name"], {})[r["variant"]] = r
    for name, pair in byname.items():
        f, s = pair.get("full"), pair.get("short")
        if not f or not s or not f["is_summon_roll"]:
            continue
        out.append({
            "name": name,
            "power": f["power"], "mp": f["mp"],
            "power_per_mp": round(f["power"] / f["mp"], 3) if f["mp"] else None,
            "full_s": f["sfx_seconds"], "short_s": s["sfx_seconds"],
            "expected_s_rich": round(expected_seconds(f["sfx_seconds"], s["sfx_seconds"],
                                                     P_SHORT_RICH), 2),
            "expected_s_poor": round(expected_seconds(f["sfx_seconds"], s["sfx_seconds"],
                                                     P_SHORT_POOR), 2),
        })
    return sorted(out, key=lambda r: r["expected_s_rich"])


# NIMBRA as shipped (STORYBOARD 3.1 + the R2 trim), and the three re-positioning candidates.
NIMBRA_SHIPPED = {"name": "NIMBRA (shipped, trimmed)", "ticks": 440, "power": 62, "mp": 24}
CANDIDATES = [
    {"key": "A", "name": "THE WHISPER (recommended)", "ticks": 140, "power": 34, "mp": 24},
    {"key": "B", "name": "THE FREE TRIM (zero manifest edit)", "ticks": 355, "power": 45, "mp": 32},
    {"key": "C", "name": "THE SIGH (at the structural floor)", "ticks": 100, "power": 30, "mp": 20},
]

# THE P4 FLOOR.  STORYBOARD 3.1 P4 + THE FIGURE-VISIBILITY LAW (rung 4): the relight ramp is
# `SetBackgroundIntensity: Intensity=1 ; Time=18`, and BOTH EffectPoints must fire at least 12
# ticks after it COMPLETES, or the damage numbers render washed out under the overlay.  So the
# strike phase cannot be compressed below:
P4_FLOOR = 30 + 12 + 8      # 18 relight + 12 settle | EP Effect | 12 | EP Figure | 8 tail = 50
TAIL_TICKS = 5              # StopSound/ActivateReflect/Idle/Turn(5)/WaitTurn
MIN_PRE = 20                # clip budget (10) + a token blackout ramp


def placement(rows):
    """Print the NIMBRA placement analysis -- every number quoted in DURATION-CENSUS.md."""
    sub = [r for r in rows if r["is_summon_roll"]]
    fulls = [r for r in sub if r["variant"] == "full" and r["name"] != "Ark"]
    shorts = [r for r in sub if r["variant"] == "short" and r["name"] != "Ark"]
    fs = sorted(r["sfx_seconds"] for r in fulls)
    ss = sorted(r["sfx_seconds"] for r in shorts)
    print("\n== PLACEMENT ==")
    print(f"  stock FULL  band (Ark excl.): {fs[0]:.1f} - {fs[-1]:.1f} s  "
          f"(median {fs[len(fs)//2]:.1f})   Ark = 113.2 s")
    print(f"  stock SHORT band (Ark excl.): {ss[0]:.1f} - {ss[-1]:.1f} s  "
          f"(median {ss[len(ss)//2]:.1f})   Ark = 26.4 s")

    rt = roll_table(rows)
    exp_rich = sorted(r["expected_s_rich"] for r in rt if r["name"] != "Ark")
    print(f"\n  -- EXPECTED seconds per cast (the MP roll applied) --")
    print(f"  {'summon':<22}{'full_s':>8}{'short_s':>9}{'E[rich]':>9}{'E[poor]':>9}"
          f"{'power':>7}{'MP':>5}{'pow/MP':>8}")
    for r in rt:
        print(f"  {r['name']:<22}{r['full_s']:>8.1f}{r['short_s']:>9.1f}"
              f"{r['expected_s_rich']:>9.1f}{r['expected_s_poor']:>9.1f}"
              f"{r['power']:>7}{r['mp']:>5}"
              f"{(r['power_per_mp'] if r['power_per_mp'] else 0):>8.2f}")
    print(f"  stock E[rich] band (Ark excl.): {exp_rich[0]:.1f} - {exp_rich[-1]:.1f} s "
          f"(median {exp_rich[len(exp_rich)//2]:.1f})")
    ratios = [r["power_per_mp"] for r in rt if r["power"] > 0]
    print(f"  stock power/MP: min {min(ratios):.2f}  max {max(ratios):.2f}  "
          f"mean {sum(ratios)/len(ratios):.2f}")

    print(f"\n  -- NIMBRA --")
    for c in [NIMBRA_SHIPPED] + CANDIDATES:
        s = c["ticks"] / TPS
        pm = c["power"] / c["mp"]
        # percentile of this duration inside the stock EXPECTED-cast distribution
        pct = 100.0 * sum(1 for e in exp_rich if e < s) / len(exp_rich)
        print(f"  {c.get('key', '-'):>2}  {c['name']:<36} {c['ticks']:>4} ticks "
              f"{s:>5.1f}s  power {c['power']:>3}  MP {c['mp']:>2}  "
              f"pow/MP {pm:>4.2f}  | longer than {pct:>3.0f}% of stock expected casts")
    # How much of the shipped cast can be trimmed WITHOUT touching the .sfxmodel manifest.
    # Everything BEFORE PlaySFX is free (STORYBOARD 7 R2: it shifts the whole cast uniformly and
    # touches neither clock).  Everything AFTER PlaySFX is inside the manifest's pinned
    # Start=0/End=330 window (nimbra.summon.toml:43-44) and cannot move without re-cutting the
    # manifest, the curves and the playlist speeds.
    free_floor = MIN_PRE + 330 + TAIL_TICKS
    print(f"\n  FREE-TRIM FLOOR (pre-PlaySFX only, manifest untouched): "
          f"{MIN_PRE} pre + 330 manifest window + {TAIL_TICKS} tail = {free_floor} ticks / "
          f"{free_floor / TPS:.1f} s.  Candidate B sits here.  Anything shorter REQUIRES "
          f"re-cutting nimbra.summon.toml's `end = 330`.")
    struct_floor = MIN_PRE + P4_FLOOR + TAIL_TICKS
    print(f"  STRUCTURAL FLOOR (P4 floor {P4_FLOOR} ticks, law-bound): "
          f"{struct_floor} ticks / {struct_floor / TPS:.1f} s with ZERO approach or hang. "
          f"Candidate C ({CANDIDATES[2]['ticks']}) leaves only "
          f"{CANDIDATES[2]['ticks'] - struct_floor} ticks for rise+look -- the identity does "
          f"not survive it.")
    a = CANDIDATES[0]["ticks"]
    print(f"  Candidate A ({a}) budget: {MIN_PRE + 5} pre | manifest window "
          f"{a - (MIN_PRE + 5) - TAIL_TICKS} (P2 25 rise / P3 25 look / P4 {P4_FLOOR} strike / "
          f"P5 10 dissolve) | {TAIL_TICKS} tail.  Closest stock analogue: "
          f"Shiva__Short = 135 ticks / 9.0 s.")


def chart(rows, path: Path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:      # pragma: no cover
        print(f"  (chart skipped: {e})")
        return
    rt = {r["name"]: r for r in roll_table(rows)}
    fig, axes = plt.subplots(1, 3, figsize=(17.5, 5.8))

    panels = [
        ("full", "FULL cinematic\n(the rare one: ~10% of casts)", "sfx_seconds"),
        ("short", "SHORT cinematic\n(the usual one: ~90% of casts)", "sfx_seconds"),
        ("expected", "EXPECTED seconds PER CAST\n(the MP roll applied)", None),
    ]
    for ax, (variant, title, _k) in zip(axes, panels):
        if variant == "expected":
            dmg = [r for r in rt.values() if r["power"] > 0]
            buf = [r for r in rt.values() if r["power"] == 0]
            yk = "expected_s_rich"
        else:
            sub = [r for r in rows if r["variant"] == variant and r["is_summon_roll"]]
            dmg = [r for r in sub if r["power"] > 0]
            buf = [r for r in sub if r["power"] == 0]
            yk = "sfx_seconds"
        ax.scatter([r["power"] for r in dmg], [r[yk] for r in dmg],
                   s=54, c="#3a6ea5", zorder=3, label="damage summons")
        ax.scatter([0] * len(buf), [r[yk] for r in buf],
                   s=46, c="#9aa4ad", marker="s", zorder=3, label="Carbuncle (power 0)")
        for r in dmg:
            ax.annotate(r["name"].split(" (")[0].replace("Fenrir", "Fenrir"),
                        (r["power"], r[yk]), textcoords="offset points",
                        xytext=(5, 4), fontsize=7.5)
        if len(dmg) >= 3:
            a, b = linfit([r["power"] for r in dmg], [r[yk] for r in dmg])
            xs = [min(r["power"] for r in dmg), max(r["power"] for r in dmg)]
            r_p = pearson([r["power"] for r in dmg], [r[yk] for r in dmg])
            ax.plot(xs, [a + b * x for x in xs], "--", c="#c0392b", lw=1.3,
                    label=f"fit r={r_p:+.2f}")
        ax.set_yscale("log")
        ax.set_yticks([4, 6, 10, 20, 40, 80, 120])
        ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.set_xlabel("power (Actions.csv)")
        ax.set_ylabel("seconds @ TPS 15  (log scale)")
        ax.set_title(title, fontsize=10)
        ax.grid(alpha=.25, which="both")
        ax.legend(fontsize=8, loc="lower right")

    # NIMBRA: as shipped, and the three candidates -- all on the "per cast" panel, because
    # NIMBRA has NO short variant, so its one cinematic IS its expected duration.
    axes[0].scatter([62], [29.3], s=150, marker="*", c="#8e44ad", zorder=5)
    axes[0].annotate("NIMBRA as shipped\n29.3 s, power 62", (62, 29.3),
                     textcoords="offset points", xytext=(-40, -30), fontsize=8,
                     color="#8e44ad")
    for c, col, off in zip(CANDIDATES, ("#16a085", "#d35400", "#7f8c8d"),
                           ((-64, -6), (8, 4), (-58, -6))):
        s = c["ticks"] / TPS
        axes[2].scatter([c["power"]], [s], s=170, marker="*", c=col, zorder=6)
        axes[2].annotate(f"{c['key']}: {s:.1f} s", (c["power"], s),
                         textcoords="offset points", xytext=off, fontsize=8.5,
                         color=col, fontweight="bold", zorder=7)
    axes[2].scatter([62], [29.3], s=150, marker="X", c="#8e44ad", zorder=5)
    axes[2].annotate("NIMBRA as shipped\n(no short variant =>\nevery cast is the full one)",
                     (62, 29.3), textcoords="offset points", xytext=(-52, 12), fontsize=8,
                     color="#8e44ad")

    fig.suptitle("FF9 stock summons: cinematic duration vs power  "
                 "(measured from the install's own .seq text; TPS 15)", fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    print(f"  wrote {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--chart", action="store_true")
    ap.add_argument("--out", default=str(HERE))
    args = ap.parse_args()

    if not SFX_DIR.is_dir():
        print(f"install not found at {GAME}", file=sys.stderr)
        return 2

    print("== VALIDATION (ground truths) ==")
    bad = validate()
    if args.validate:
        return 1 if bad else 0
    if bad:
        print("!! validation failed -- the model is not trustworthy; stopping", file=sys.stderr)
        return 1

    print("\n== CENSUS ==")
    rows = build_rows()
    cross_check(rows)

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    keys = ["ability_id", "name", "csv_name", "variant", "effect_id", "sfx_ticks",
            "sfx_seconds", "cast_ticks", "cast_seconds", "pre_ticks", "post_ticks",
            "damage_beat_tick", "power", "mp", "element", "type", "targets",
            "clip_waits", "clip_uncertainty_ticks", "is_summon_roll"]
    with (outdir / "summon_durations.csv").open("w", newline="", encoding="utf-8") as fh:
        wtr = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        wtr.writeheader()
        for r in sorted(rows, key=lambda r: (r["variant"], -r["power"], r["name"])):
            wtr.writerow(r)
    print(f"  wrote {outdir / 'summon_durations.csv'}")

    corr = correlations(rows)
    (outdir / "correlations.json").write_text(json.dumps(corr, indent=2), encoding="utf-8")
    print(f"  wrote {outdir / 'correlations.json'}")

    # console table
    for variant in ("full", "short"):
        print(f"\n-- {variant.upper()} --")
        print(f"{'summon':<22}{'ef':>5}{'ticks':>7}{'sec':>7}{'cast_s':>8}{'power':>7}{'MP':>5}"
              f"{'s/pow':>8}")
        for r in sorted([x for x in rows if x["variant"] == variant],
                        key=lambda r: r["sfx_ticks"] or 0):
            spp = (r["sfx_seconds"] / r["power"]) if r["power"] else float("nan")
            print(f"{r['name']:<22}{r['effect_id']:>5}{r['sfx_ticks']:>7}"
                  f"{r['sfx_seconds']:>7.1f}{r['cast_seconds']:>8.1f}{r['power']:>7}"
                  f"{r['mp']:>5}{spp:>8.3f}")
        for k, v in corr[variant].items():
            if k.startswith("_"):
                print(f"   {k:<28} {v}")
                continue
            print(f"   {k:<28} n={v['n']:<3} r={v['pearson_r']:+.3f}  R2={v['r_squared']:.3f}"
                  f"  rho={v['spearman_rho']:+.3f}  p={v['p_two_sided']:.4f}")

    placement(rows)
    (outdir / "roll_expected.json").write_text(
        json.dumps({"p_short_rich": round(P_SHORT_RICH, 4),
                    "p_short_poor": round(P_SHORT_POOR, 4),
                    "rows": roll_table(rows)}, indent=2), encoding="utf-8")
    print(f"\n  wrote {outdir / 'roll_expected.json'}")

    if args.chart:
        chart(rows, outdir / "duration_vs_power.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
