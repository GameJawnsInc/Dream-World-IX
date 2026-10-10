"""THE HOUSEHOLD DAY -- sims-arc rung 2 (studies/sims/PLAN.md).

Rung 1 proved one need, one stove, one directive. Rung 2 asks the arc's real question -- is she ALIVE when
you stop directing her? -- with no new compiler surface:

* FIVE NEEDS in one table (hunger, thirst, energy, hygiene, fun), each its own [[behavior.drift]] rate.
* FIVE OBJECTS, one per need, each with a directive zone menu for the steward ("Never mind" last).
* PRIORITY-BRANCH AUTONOMY over one task flag per need, four tiers in branch order:
    finish  -- task flagged and the need is full      -> clear the task
    use     -- task flagged and standing at the object -> hold there, adjust the need up
    go      -- task flagged                            -> walk to the object
    urge    -- (no task at all) a need has run low     -> raise its task
  A directive raises the same flag an urge does, so orders QUEUE: she finishes the object she is at, then
  walks to the next flagged one in tier order. Urge order is the priority (argmax is rung 3's `pick`).
* THE DAY CLOCK: an hours cell (+1 every HOUR ticks) drives a "DAY n  hh:00 (day|night)" HUD line, and an
  alternator flag `night` (flips every 12 hours, the day starting at 06:00) pulls her to bed early and
  tires her faster.

  py studies/sims/sims_bench2.py gen      # write bench/rung2.field.toml (two-pass: flag indices)
  py studies/sims/sims_bench2.py sim      # the offline stepper (an instrument, not proof)
  py studies/sims/sims_bench2.py deploy   # gen + deploy --id 30431

ASCII only in this file's output (cp1252).
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit.content import behaviortoml as BT                  # noqa: E402

FIELD_ID = 30431
FIELD_NAME = "MANOR2"
BENCH = HERE / "bench"
BENCH_TOML = BENCH / "rung2.field.toml"
REPORT = BENCH / "rung2.report.txt"


def configure(variant: str = "priority", rates: str = "tuned") -> None:
    """Select the bench: the urge tier ("priority" = rung 2 at 30431, "pick" = rung 3 at 30432) and the rate set
    ("tuned" | "first"). Everything else -- layout, objects, clock, directives -- is shared, so an A/B differs in
    the urge tier alone. A non-tuned rate set writes its own toml and is for the offline stepper only."""
    global VARIANT, RATESET, FIELD_ID, FIELD_NAME, BENCH_TOML, REPORT, DECAY_EVERY, USE, URGE_AT, NAMES, \
        NOSLEEP_EVERY
    VARIANT, RATESET = variant, rates
    NAMES[:] = BASE_NAMES + (["social"] if variant == "rung5" else [])     # in place: importers hold the list
    NOSLEEP_EVERY = 20 if variant == "rung5" else 5     # rung 5: slow enough to quarrel before the faint
    FIELD_ID, FIELD_NAME, stem = VARIANTS[variant]
    if rates != "tuned":
        stem += f"-{rates}"
    BENCH_TOML, REPORT = BENCH / f"{stem}.field.toml", BENCH / f"{stem}.report.txt"
    DECAY_EVERY, USE, URGE_AT = RATES[rates]["decay"], RATES[rates]["use"], RATES[rates]["urge"]
SIEGE_ART = REPO / "ff9mapkit" / "examples" / "siege" / "art"

# ---------------------------------------------------------------- the layout (probe it: field_layout_probe.py)
# The rung-1 room (x +-1220, z 257..-1931; FRONT = -z, toward the camera). Objects ring the room; Bilba's
# use-spot sits in front of (or beside) each object, the steward's zone on the object's OTHER flank, so a
# steward giving an order never stands on her spot or her approach line (a walker into a standing player
# is held there indefinitely). Every spot pair >= 400u apart (near_point 160 never overlaps).
HOME = (-200, -700)                 # her idle anchor (wander box radius 200)
PLAYER_SPAWN = (0, -1700)           # the steward, front-center, clear of every zone band

#        need       prop          object        her use-spot   steward zone (x0, z0, x1, z1)
NEEDS = [
    ("hunger",  "pot",         (600, -250),  (600, -520),   (730, -420, 960, -60)),
    ("thirst",  "cup",         (-950, -1100), (-720, -1100), (-1120, -1520, -820, -1300)),
    ("energy",  "tent",        (-850, -150), (-850, -500),  (-620, -380, -380, 40)),
    ("hygiene", "cask",        (950, -1050), (720, -1050),  (800, -1460, 1120, -1250)),
    ("fun",     "dagger_doll", (100, -150),  (100, -420),   (230, -360, 430, 40)),
]
BASE_NAMES = [n[0] for n in NEEDS]
NAMES = list(BASE_NAMES)            # rung 5 appends "social" (configure)
SEED = {"hunger": 80, "thirst": 70, "energy": 75, "hygiene": 85, "fun": 60, "social": 60}
# Two rate sets. "first" was rung 2's first tuning: left alone 3 days, FUN HIT 0 and hunger 9 under the
# priority list (fun is the last urge row, decays fastest, and drained during the long naps). "tuned" is the
# fair rung-2 baseline. Rung 3 A/Bs the urge tier (priority list vs `pick`) on BOTH.
RATES = {
    "tuned": {"decay": {"hunger": 45, "thirst": 40, "energy": 55, "hygiene": 60, "fun": 45, "social": 50},
              "use": {"hunger": (2, 8), "thirst": (3, 8), "energy": (1, 6), "hygiene": (2, 8), "fun": (2, 10)},
              "urge": 40},
    "first": {"decay": {"hunger": 40, "thirst": 35, "energy": 55, "hygiene": 60, "fun": 30, "social": 50},
              "use": {"hunger": (2, 8), "thirst": (3, 8), "energy": (1, 10), "hygiene": (2, 8), "fun": (2, 10)},
              "urge": 35},
}
# THE URGE TIER, two ways (rung 3's A/B). "priority": one urge row per need in a fixed order -- the first
# need at/under the line wins. "pick": a [[behavior.pick]] publishes the index of the LOWEST need every pass,
# and only that need's urge row can fire -- serve whatever is most urgent.
VARIANTS = {"priority": (30431, "MANOR2", "rung2"), "pick": (30432, "MANOR3", "rung3"),
            "rung4": (30433, "MANOR4", "rung4"), "rung5": (30434, "MANOR5", "rung5")}
R4V = ("rung4", "rung5")            # the variants that carry rung 4's failure/mood/emote layer
# RUNG 4 -- failure, mood, emote (the priority urge tier: rung 3's verdict). Poses are `hold_ground` + `anim`
# (the kit's posed hold, gestures of Vivi's OWN rig); a need at 0 FAINTS her where she stands.
POSE = {"hunger": "dine_1", "energy": "sleeping", "fun": "laugh"}     # use-tier poses (thirst/hygiene stand)
FAINT_POSE = "hiza_1"               # the collapse, frozen at its last frame
REVIVE_AT = 25                      # lying there, the failed need creeps back to this, then she gets up
FAINT_REGEN = 10                    # +1 every N ticks while down (~8 s on the floor)
NOSLEEP_EVERY = 5                   # "stay up all night": energy -1 every N ticks, and no bed
TIRED_AT, MERRY_AT = 55, 80         # idle emotes on the beat: yawn when tired, laugh when fun is high
BEAT = 75                           # the idle-emote alternator (2.5 s on, 2.5 s off)
# RUNG 5 -- the visitor, the relationship, the falling-out. Garnet lives in the parlour; Bilba's SOCIAL need is
# filled by chatting with her. A chat moves REL (0..100, 50 = neutral) up -- unless Bilba is CRANKY (hungry or
# exhausted at/under CRANKY_AT, or kept up all night): then it is a quarrel and REL falls fast. At FALLOUT_AT
# the falling-out is a REAL battle (once per visit); after it Bilba is sorry until REL is back to SORRY_UNTIL.
GARNET_MODEL = "GEO_MAIN_F0_GRN"
PARLOR = (350, -1000)               # Garnet's wander anchor (radius 150)
SULK_SPOT = (1000, -1650)           # where she goes to sit and sulk
PARLOR_ZONE = (200, -1480, 500, -1260)   # the steward's menu: front of the parlour, on the front-row lane
REL_TABLE_ID, REL_SEED = 1002, 50
CRANKY_AT = 35
FALLOUT_AT, SORRY_UNTIL = 10, 60
GLARE_AT, SULK_AT, FRIENDS_AT = 40, 25, 80
BATTLE_SCENE = 67                   # BSC_EF_R007: a lone Goblin a New Game party can beat
CHAT_GOOD = ((2, 8), (1, 20))       # (social by/every, rel by/every)
CHAT_BAD = ((-1, 20), (-1, 6))      # a quarrel DRAINS social (run 1: it filled it, and ended itself at 95)
MAKEUP = (3, 8)                     # rel +3 every 8 while sorry
VARIANT, RATESET = "priority", "tuned"
DECAY_EVERY, USE, URGE_AT = RATES["tuned"]["decay"], RATES["tuned"]["use"], RATES["tuned"]["urge"]
NIGHT_SLEEP_AT = 70                 # ...but at night energy this low already sends her to bed
FULL_AT = 95
NIGHT_TIRE_EVERY = 40               # an extra -1 energy every N ticks, night only

HOUR = 150                          # ticks per in-game hour (5 s): a day is 2 minutes
START_HOUR = 6                      # the clock reads 06:00 at entry; night = 18:00-06:00
NEED_TABLE_ID, CLOCK_TABLE_ID = 1000, 1001   # pinned so the HUD expr: sources name them stably

VERB = {"hunger": "eat something", "thirst": "have a drink", "energy": "take a nap",
        "hygiene": "wash up", "fun": "play a while"}
PROMPT = {"hunger": "The soup pot.", "thirst": "A cup of water.", "energy": "The tent.",
          "hygiene": "The wash barrel.", "fun": "The puppet."}


NOSLEEP_DRIFT = """
[[behavior.drift]]                  # rung 4: an all-nighter drains her fast
table = "need"
index = {e}
by = -1
clamp = [0, 100]
every = {every}
flag = "nosleep"
"""
BEAT_ALT = f', {{ name = "beat", frames = {BEAT} }}'
MOOD_TEXT = "  MOOD [NUMB=7]"          # rung 4: the average of the five needs, slot 7
URG_TEXT = "  URG [NUMB=7]"           # the pick bench shows its pick: slot 7, the last free gMesValue
PICK_ROW = """[[behavior.pick]]                   # rung 3: the index of the LOWEST need, every pass
name = "most_urgent"
table = "need"
into = "urgent"
mode = "min"
"""


GARNET_NPC = f"""
[[npc]]
name = "garnet"
model = "{GARNET_MODEL}"
pos = [{PARLOR[0]}, {PARLOR[1]}]
dialogue = "Bilba? She is... a good friend. Usually."

[[marker]]
name = "parlor"
pos = [{PARLOR[0]}, {PARLOR[1]}]

[[marker]]
name = "sulk_spot"
pos = [{SULK_SPOT[0]}, {SULK_SPOT[1]}]
"""

REL_TABLE = f"""
[[behavior.table]]
name = "rel"                        # [0] = Bilba <-> Garnet, 0..100 (50 = neutral)
values = [{REL_SEED}]
id = {REL_TABLE_ID}
"""


def _cranky() -> list:
    """The OR of crankiness as separate `when` lists (conditions AND within a branch, OR across branches)."""
    return [f'{{ table_le = ["need", {NAMES.index("hunger")}, {CRANKY_AT}] }}',
            f'{{ table_le = ["need", {NAMES.index("energy")}, {CRANKY_AT}] }}',
            '{ flag = "nosleep" }']


def _hud_block() -> str:
    if VARIANT == "rung5":
        lab = {"hunger": "HUN", "thirst": "THR", "energy": "NRG", "hygiene": "HYG", "fun": "FUN", "social": "SOC"}
        need_txt = " ".join(f"{lab[n]} [NUMB={i}]" for i, n in enumerate(NAMES))
        vals = ", ".join(f'"expr:{_vec(NEED_TABLE_ID, i)}"' for i in range(len(NAMES)))
        return f"""[[behavior.hud]]                    # ONE strip: 6 needs, the hour, REL -- all 8 gMesValue slots
window = 6
text = "[MPOS=10,48]{need_txt}\\n[NUMB=6]:00  REL [NUMB=7]"
values = [{vals},
          "expr:{_vec(CLOCK_TABLE_ID, 0)} const({START_HOUR}) B_PLUS const(24) B_REM",
          "expr:{_vec(REL_TABLE_ID, 0)}"]
digits = [3, 3, 3, 3, 3, 3, 2, 3]
"""
    return None


def _rung5_fallout() -> str:
    """Above the faint tiers: the falling-out (once per visit) and the sorry that follows it."""
    return f"""  [[behavior.unit.branch]]           # THE FALLING-OUT: rel at rock bottom -> a real battle, once
  when = [{{ table_le = ["rel", 0, {FALLOUT_AT}] }}, {{ not_flag = "fought" }}]
  do = {{ battle = {BATTLE_SCENE} }}
  raise_flags = ["fought", "sorry"]
  clear_flags = ["t_social"]          # the conversation is OVER

  [[behavior.unit.branch]]           # made up: sorry ends
  when = [{{ flag = "sorry" }}, {{ table_ge = ["rel", 0, {SORRY_UNTIL}] }}]
  do = {{ hold_ground = true }}
  clear_flags = ["sorry"]

  [[behavior.unit.branch]]           # sorry: she stands sad while they make up
  when = [{{ flag = "sorry" }}]
  do = {{ hold_ground = true, anim = "sad" }}
  adjust = {{ table = "rel", index = 0, by = {MAKEUP[0]}, clamp = [0, 100], every = {MAKEUP[1]} }}
"""


def _rung5_quarrels() -> str:
    """Cranky + chatting = a QUARREL. Above the finish tier: a full social need does not end a fight -- it
    ends at the falling-out (which clears the task) or when she stops being cranky (the good chat takes over)."""
    i = NAMES.index("social")
    (sb, se), (rb, re_) = CHAT_BAD
    out = []
    for c in _cranky():
        out.append(f"""  [[behavior.unit.branch]]           # use: a QUARREL -- she is cranky ({c})
  when = [{{ flag = "t_social" }}, {{ near = ["garnet", 320] }}, {c}]
  do = {{ hold_ground = true, anim = "angry" }}
  adjust = [{{ table = "need", index = {i}, by = {sb}, clamp = [0, 100], every = {se} }},
            {{ table = "rel", index = 0, by = {rb}, clamp = [0, 100], every = {re_} }}]
""")
    return "\n".join(out)


def _rung5_chat_use() -> str:
    i = NAMES.index("social")
    out = []
    (sb, se), (rb, re_) = CHAT_GOOD
    out.append(f"""  [[behavior.unit.branch]]           # use: a good chat
  when = [{{ flag = "t_social" }}, {{ near = ["garnet", 320] }}]
  do = {{ hold_ground = true, anim = "laugh" }}
  adjust = [{{ table = "need", index = {i}, by = {sb}, clamp = [0, 100], every = {se} }},
            {{ table = "rel", index = 0, by = {rb}, clamp = [0, 100], every = {re_} }}]
""")
    return "\n".join(out)


def _garnet_unit() -> str:
    return f"""
[[behavior.unit]]
npc = "garnet"
speed = 25

  [[behavior.unit.branch]]           # Bilba is quarrelling / they are on bad terms: she glares back
  when = [{{ flag = "t_social" }}, {{ near = ["bilba", 360] }}, {{ table_le = ["rel", 0, {GLARE_AT}] }}]
  do = {{ hold_ground = true, anim = "angry_1_1" }}

  [[behavior.unit.branch]]           # Bilba came to chat: she stops and talks
  when = [{{ flag = "t_social" }}, {{ near = ["bilba", 360] }}]
  do = {{ hold_ground = true, anim = "talk_1_1" }}

  [[behavior.unit.branch]]           # sulking, at her sulk spot: sits on the floor
  when = [{{ table_le = ["rel", 0, {SULK_AT}] }}, {{ near_point = ["sulk_spot", 140] }}]
  do = {{ hold_ground = true, anim = "sit_g_sad_1" }}

  [[behavior.unit.branch]]           # sulking: off to her corner
  when = [{{ table_le = ["rel", 0, {SULK_AT}] }}]
  do = {{ walk_to = "sulk_spot", speed = 35 }}

  [[behavior.unit.branch]]           # friends: she tags along after Bilba
  when = [{{ table_ge = ["rel", 0, {FRIENDS_AT}] }}]
  do = {{ chase = "bilba", standoff = 280, speed = 30 }}

  [[behavior.unit.branch]]
  do = {{ wander = "parlor", radius = 150, every = 140, speed = 25 }}
"""


def _hud_default() -> str:
    return f"""[[behavior.hud]]                    # ONE strip: gMesValue[8] is global, a second strip overwrites this one's slots
window = 6
text = "[MPOS=10,48]HUN [NUMB=0] THR [NUMB=1] NRG [NUMB=2] HYG [NUMB=3] FUN [NUMB=4]\\nDAY [NUMB=5]  [NUMB=6]:00{URG_TEXT if VARIANT == "pick" else MOOD_TEXT if VARIANT in R4V else ""}"
values = [{", ".join(f'"expr:{_vec(NEED_TABLE_ID, i)}"' for i in range(len(NAMES)))},
          "expr:{_vec(CLOCK_TABLE_ID, 0)} const({START_HOUR}) B_PLUS const(24) B_DIV const(1) B_PLUS",
          "expr:{_vec(CLOCK_TABLE_ID, 0)} const({START_HOUR}) B_PLUS const(24) B_REM",
          {'"urgent"' if VARIANT == "pick" else _mood_expr() if VARIANT in R4V else ""}]
digits = [3, 3, 3, 3, 3, 2, 2{", 1" if VARIANT == "pick" else ", 3" if VARIANT in R4V else ""}]
"""


def _mood_expr() -> str:
    """MOOD = the average of the five needs (B_LMAX/B_LMIN are party selectors, not min/max -- the trap)."""
    cells = [_vec(NEED_TABLE_ID, i) for i in range(len(NAMES))]
    return '"expr:' + cells[0] + "".join(f" {c} B_PLUS" for c in cells[1:]) + f' const({len(NAMES)}) B_DIV"'


def _vec(table_id: int, i: int) -> str:
    return f"const({table_id}) const({i}) B_VECTOR"


def _field_toml() -> str:
    out = [f"""# THE HOUSEHOLD DAY -- sims-arc bench, urge tier "{VARIANT}", rates "{RATESET}" (generated by studies/sims/sims_bench2.py)
# Five needs, five objects, priority-branch autonomy, the day clock. Novel field, stock Memoria.

[field]
id = {FIELD_ID}
name = "{FIELD_NAME}"
area = 11
title = "mognet manor"

[camera]
entry_settle = "auto"
pitch = 48.0
distance = 4500
fov = 42.2
[camera.frame]
back = 205
front = 432

[walkmesh]
quad = [[-1220, 257], [1220, 257], [1220, -1931], [-1220, -1931]]
frame = "world"

[[layers]]
image = "art/back.png"
z = 4000
[[layers]]
image = "art/floor.png"
z = 3000

[player]
spawn = [{PLAYER_SPAWN[0]}, {PLAYER_SPAWN[1]}]

[[npc]]
name = "bilba"
model = "GEO_MAIN_F0_VIV"
pos = [{HOME[0]}, {HOME[1]}]
dialogue = "...The soup is still worried. So am I, a little."

[[marker]]
name = "home"
pos = [{HOME[0]}, {HOME[1]}]
{GARNET_NPC if VARIANT == "rung5" else ""}
"""]
    for name, prop, obj, spot, _zone in NEEDS:
        out.append(f"""[[prop]]
prop = "{prop}"
pos = [{obj[0]}, {obj[1]}]

[[marker]]
name = "{name}_spot"
pos = [{spot[0]}, {spot[1]}]
""")
    # ---- the behavior
    seeds = ", ".join(str(SEED[n]) for n in NAMES)
    out.append(f"""# ---------------------------------------------------------------- the behavior
[behavior]
warmup = 30
public_flags = [{", ".join(f'"t_{n}"' for n in NAMES)}{', "nosleep"' if VARIANT in R4V else ""}]
alternators = [{{ name = "night", frames = {12 * HOUR} }}{BEAT_ALT if VARIANT in R4V else ""}]
{'counters = ["urgent"]' if VARIANT == "pick" else ""}

[[behavior.table]]
name = "need"                       # {", ".join(f"{i}={n}" for i, n in enumerate(NAMES))} (0..100, 100 = met)
values = [{seeds}]
id = {NEED_TABLE_ID}

[[behavior.table]]
name = "clock"                      # [0] = hours since entry (the day starts at {START_HOUR:02d}:00)
values = [0]
id = {CLOCK_TABLE_ID}{REL_TABLE if VARIANT == "rung5" else ""}

{PICK_ROW if VARIANT == "pick" else ""}
[[behavior.drift]]                  # THE CLOCK
table = "clock"
index = 0
by = 1
clamp = [0, 1000000]
every = {HOUR}
""")
    for i, n in enumerate(NAMES):
        out.append(f"""[[behavior.drift]]                  # metabolism: {n}
table = "need"
index = {i}
by = -1
clamp = [0, 100]
every = {DECAY_EVERY[n]}
""")
    e = NAMES.index("energy")
    out.append(f"""[[behavior.drift]]                  # night tires her faster
table = "need"
index = {e}
by = -1
clamp = [0, 100]
every = {NIGHT_TIRE_EVERY}
flag = "night"
{NOSLEEP_DRIFT.format(e=e, every=NOSLEEP_EVERY) if VARIANT in R4V else ""}
{(_hud_block() or _hud_default()).rstrip(chr(10))}
# (no "(day)/(night)" word: a [TEXT=] in a HUD strip is resolved ONCE at window open -- the engine's constant-tag
#  pass runs before the variable snapshot -- so it freezes at the open pass's sentinel row and renders "")

[[behavior.unit]]
npc = "bilba"
speed = 25
""")
    if VARIANT == "rung5":
        out.append(_rung5_fallout())
    if VARIANT in R4V:
        out.append(_rung4_failure_tiers())
    if VARIANT == "rung5":
        out.append(_rung5_quarrels())
    # ---- tier 1: finish
    for i, n in enumerate(NAMES):
        out.append(f"""  [[behavior.unit.branch]]           # finish: {n} is met -> the task retires
  when = [{{ flag = "t_{n}" }}, {{ table_ge = ["need", {i}, {FULL_AT}] }}]
  do = {('{ hold_ground = true }' if n == "social" else '{ hold = "' + n + '_spot" }')}
  clear_flags = ["t_{n}"]
""")
    # ---- tier 2: use
    for i, n in enumerate(NAMES):
        if n == "social":
            out.append(_rung5_chat_use())
            continue
        by, every = USE[n]
        posed = VARIANT in R4V and n in POSE
        do = (f'{{ hold_ground = true, anim = "{POSE[n]}" }}' if posed else f'{{ hold = "{n}_spot" }}')
        out.append(f"""  [[behavior.unit.branch]]           # use: at the {n} object, the meter climbs
  when = [{{ flag = "t_{n}" }}, {{ near_point = ["{n}_spot", 160] }}]
  do = {do}
  adjust = {{ table = "need", index = {i}, by = {by}, clamp = [0, 100], every = {every} }}
""")
    # ---- tier 3: go
    for n in NAMES:
        go = ('{ chase = "garnet", standoff = 220, speed = 40 }' if n == "social"
              else '{ walk_to = "' + n + '_spot", speed = 40 }')
        out.append(f"""  [[behavior.unit.branch]]           # go: a {n} task is waiting
  when = [{{ flag = "t_{n}" }}]
  do = {go}
""")
    # ---- tier 4: urges (only reached when no task is flagged), most pressing first
    out.append(f"""  [[behavior.unit.branch]]           # urge: night, and tired enough to turn in
  when = [{{ flag = "night" }}, {{ table_le = ["need", {e}, {NIGHT_SLEEP_AT}] }}{NO_ALLNIGHTER if VARIANT in R4V else ""}]
  do = {{ walk_to = "energy_spot", speed = 40 }}
  raise_flags = ["t_energy"]
""")
    for n in ("hunger", "thirst", "energy", "hygiene", "fun") + (("social",) if "social" in NAMES else ()):
        i = NAMES.index(n)
        gate = (f'{{ counter_eq = ["urgent", {i}] }}, ' if VARIANT == "pick" else "")
        out.append(f"""  [[behavior.unit.branch]]           # urge: {n} has run low{' -- and is the MOST urgent' if gate else ''}
  when = [{gate}{{ table_le = ["need", {i}, {URGE_AT}] }}{NO_ALLNIGHTER if VARIANT in R4V and n == "energy" else ""}]
  do = {('{ chase = "garnet", standoff = 220, speed = 40 }' if n == "social" else '{ walk_to = "' + n + '_spot", speed = 40 }')}
  raise_flags = ["t_{n}"]
""")
    if VARIANT in R4V:
        out.append(f"""  [[behavior.unit.branch]]           # idle emote: tired -> a yawn on the beat
  when = [{{ flag = "beat" }}, {{ table_le = ["need", {e}, {TIRED_AT}] }}]
  do = {{ hold_ground = true, anim = "yawn" }}

  [[behavior.unit.branch]]           # idle emote: merry -> a laugh on the beat
  when = [{{ flag = "beat" }}, {{ table_ge = ["need", {NAMES.index("fun")}, {MERRY_AT}] }}]
  do = {{ hold_ground = true, anim = "laugh" }}
""")
    out.append("""  # idle: amble round home
  [[behavior.unit.branch]]
  do = { wander = "home", radius = 200, every = 120, speed = 25 }
""")
    if VARIANT == "rung5":
        out.append(_garnet_unit())
    return "\n".join(out)


NO_ALLNIGHTER = ', { not_flag = "nosleep" }'
ALLNIGHTER_ROW = """
[[choice.options]]
text = "Bilba, stay up all night!"
set_flag = [{f}, 1]
requires_flag_clear = {f}"""


def _rung4_failure_tiers() -> str:
    """Above everything: the all-nighter wakes her, and a need at 0 FAINTS her. Per need, in order:
    revive (down, and the need has crept back to REVIVE_AT -> get up) / down (the frozen collapse, the need
    creeping back) / fall (the need hit 0 -> raise the fainted flag; an energy faint ends the all-nighter)."""
    out = ["""  [[behavior.unit.branch]]           # the all-nighter: up out of bed, now
  when = [{ flag = "nosleep" }, { flag = "t_energy" }]
  do = { hold_ground = true }
  clear_flags = ["t_energy"]
"""]
    for i, n in enumerate(NAMES):
        extra = '\n  clear_flags = ["nosleep"]' if n == "energy" else ""
        out.append(f"""  [[behavior.unit.branch]]           # FAINT {n}: back on her feet
  when = [{{ flag = "f_{n}" }}, {{ table_ge = ["need", {i}, {REVIVE_AT}] }}]
  do = {{ hold_ground = true }}
  clear_flags = ["f_{n}"]

  [[behavior.unit.branch]]           # FAINT {n}: down, frozen, the need creeping back
  when = [{{ flag = "f_{n}" }}]
  do = {{ hold_ground = true, anim = "{FAINT_POSE}", freeze = true }}
  adjust = {{ table = "need", index = {i}, by = 1, clamp = [0, 100], every = {FAINT_REGEN} }}

  [[behavior.unit.branch]]           # FAINT {n}: the need hit 0 -- she drops where she stands
  when = [{{ table_le = ["need", {i}, 0] }}]
  do = {{ hold_ground = true }}
  raise_flags = ["f_{n}"]{extra}
""")
    return "\n".join(out)


def _choices(flags: dict) -> str:
    out = ["""
# ---------------------------------------------------------------- the directives
# One zone menu per object on its steward-side flank (press-action + the "!" bubble). The order row hides
# while that task is already pending (requires_flag_clear on the SAME public flag). No reply page: rung 1
# found the order lands when the reply CLOSES, so a reply only delays the walk."""]
    for name, _prop, _obj, _spot, (x0, z0, x1, z1) in NEEDS:
        out.append(f"""[[choice]]
zone = [[{x0}, {z0}], [{x1}, {z0}], [{x1}, {z1}], [{x0}, {z1}]]
bubble = true
instant = true
prompt = "{PROMPT[name]}"
[[choice.options]]
text = "Bilba, {VERB[name]}."
set_flag = [{flags[name]}, 1]
requires_flag_clear = {flags[name]}{ALLNIGHTER_ROW.format(f=flags["nosleep"]) if VARIANT in R4V and name == "energy" else ""}
[[choice.options]]
text = "Never mind."
""")
    if VARIANT == "rung5":
        x0, z0, x1, z1 = PARLOR_ZONE
        out.append(f"""[[choice]]
zone = [[{x0}, {z0}], [{x1}, {z0}], [{x1}, {z1}], [{x0}, {z1}]]
bubble = true
instant = true
prompt = "Garnet is reading in the parlour."
[[choice.options]]
text = "Bilba, go chat with Garnet."
set_flag = [{flags["social"]}, 1]
requires_flag_clear = {flags["social"]}
[[choice.options]]
text = "Never mind."
""")
    return "\n".join(out)


def _fb(raw: dict):
    """The deterministic-allocation double: same construction path as the build."""
    return BT.build(raw, npc_slots={"bilba": 2, "garnet": 3},
                    npc_txids_by_name={n.get("name"): 0 for n in raw.get("npc", [])},
                    behavior_txids={("hud", 0): 0})


def flag_indices() -> dict:
    import tomllib
    fb = _fb(tomllib.loads(_field_toml()))
    out = {n: fb.bb.flag(f"t_{n}") for n in NAMES}
    if VARIANT in R4V:
        out["nosleep"] = fb.bb.flag("nosleep")
    return out


def gen(quiet: bool = False) -> Path:
    BENCH.mkdir(parents=True, exist_ok=True)
    art = BENCH / "art"
    art.mkdir(exist_ok=True)
    for png in ("back.png", "floor.png"):
        shutil.copyfile(SIEGE_ART / png, art / png)

    import tomllib
    raw = tomllib.loads(_field_toml())
    problems = BT.validate(raw)
    if problems:
        raise SystemExit("behavior validate:\n  " + "\n  ".join(problems))
    flags = flag_indices()
    text = _field_toml() + _choices(flags)
    raw2 = tomllib.loads(text)
    problems = BT.validate(raw2)
    if problems:
        raise SystemExit("behavior validate (final):\n  " + "\n  ".join(problems))
    cb = _fb(raw2).compile()
    REPORT.write_text(cb.report + "\n(dry-run placeholders; the build binds the real "
                      "slots/txids)\n", encoding="utf-8")
    BENCH_TOML.write_text(text, encoding="utf-8")
    if quiet:
        return BENCH_TOML
    print(f"wrote {BENCH_TOML}")
    print("  task flags: " + ", ".join(f"{n}={flags[n]}" for n in NAMES) + f"; report -> {REPORT}")
    return BENCH_TOML


def measure(ticks: int = 3 * 24 * HOUR) -> dict:
    """THE UNDIRECTED DAYS, offline: nobody orders anything for ``ticks`` (default three in-game days). The
    stepper is an instrument, not proof (straight-line walks, no collision). Returns per-need task counts and
    lows, sleeps begun by night/day, and MISERY: the summed shortfall under the urge line, tick by tick --
    a starved need scores large where a fair rotation scores small."""
    import tomllib
    from ff9mapkit.workspace import behaviorsim as SIM
    gen(quiet=True)
    raw = tomllib.loads(BENCH_TOML.read_text(encoding="utf-8"))
    s = SIM.Sim(raw)
    served = {n: 0 for n in NAMES}
    low = {n: 100 for n in NAMES}
    misery = {n: 0 for n in NAMES}
    night_sleep = day_sleep = 0
    prev = {n: 0 for n in NAMES}
    for t in range(1, ticks + 1):
        st = s.at(t)
        need = st["tables"]["need"]
        fl = st["flags"]
        for i, n in enumerate(NAMES):
            low[n] = min(low[n], need[i])
            misery[n] += max(0, URGE_AT - need[i])
            on = 1 if fl.get(f"t_{n}") else 0
            if on and not prev[n]:
                served[n] += 1
                if n == "energy":
                    if fl.get("night"):
                        night_sleep += 1
                    else:
                        day_sleep += 1
            prev[n] = on
    return {"served": served, "low": low, "misery": misery, "night_sleep": night_sleep,
            "day_sleep": day_sleep, "notes": list(s.notes)}


def sim() -> None:
    m = measure()
    print(f"SIM [{VARIANT}/{RATESET}] (3 undirected days): tasks started "
          + ", ".join(f"{n} {m['served'][n]}" for n in NAMES))
    print("  lowest " + ", ".join(f"{n} {m['low'][n]}" for n in NAMES)
          + f"; sleeps begun at night {m['night_sleep']}, by day {m['day_sleep']}")
    print(f"  misery (shortfall under {URGE_AT}, summed per tick) "
          + ", ".join(f"{n} {m['misery'][n]}" for n in NAMES) + f"; total {sum(m['misery'].values())}")
    for n in m["notes"]:
        print(f"  note: {n}")
    assert all(m["served"][n] >= 1 for n in NAMES), f"a need was never served: {m['served']}"
    assert all(m["low"][n] > 0 for n in NAMES), f"a need bottomed out: {m['low']}"
    assert m["night_sleep"] >= 2, f"she never turned in at night ({m['night_sleep']})"
    print("SIM OK")


def ab() -> None:
    """RUNG 3's OFFLINE A/B: the urge tier as a priority list vs as a pick, on both rate sets."""
    print(f"{'rates':6} {'tier':9} {'lowest need':>12} {'misery':>8}  per need (low / misery)")
    for rates in ("first", "tuned"):
        for variant in ("priority", "pick"):
            configure(variant, rates)
            m = measure()
            worst = min(m["low"], key=m["low"].get)
            print(f"{rates:6} {variant:9} {worst + ' ' + str(m['low'][worst]):>12} "
                  f"{sum(m['misery'].values()):>8}  "
                  + "  ".join(f"{n[:3]} {m['low'][n]}/{m['misery'][n]}" for n in NAMES)
                  + f"  sleeps n{m['night_sleep']}/d{m['day_sleep']}")


def deploy() -> None:
    gen()
    r = subprocess.run([sys.executable, str(REPO / "tools" / "deploy_field.py"),
                        str(BENCH_TOML), "--id", str(FIELD_ID)])
    if r.returncode != 0:
        raise SystemExit("deploy_field failed")
    print(f"""
{FIELD_NAME} [{VARIANT}] (first deploy of {FIELD_ID} = RELAUNCH, then ~ -> Warp -> {FIELD_ID}):
  Leave her alone for a few in-game days -- does she look after herself, and sleep at night?
  Then order her about at the objects: orders queue behind what she is doing.
  Harness: py tools/play.py studies/sims/{"rung2_day" if VARIANT == "priority" else "rung3_pick"}.py
  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py""")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "sim", "deploy", "ab"])
    ap.add_argument("--variant", choices=sorted(VARIANTS), default="priority",
                    help="the urge tier: priority (rung 2, 30431) or pick (rung 3, 30432)")
    ap.add_argument("--rates", choices=sorted(RATES), default="tuned")
    a = ap.parse_args()
    if a.cmd == "deploy" and a.rates != "tuned":
        raise SystemExit("deploy ships the tuned rates only (the 'first' set is an offline A/B arm)")
    configure(a.variant, a.rates)
    {"gen": gen, "sim": sim, "deploy": deploy, "ab": ab}[a.cmd]()


if __name__ == "__main__":
    main()
