# 08 — Dialogue choices & a cutscene

Add the two core interaction primitives to a field: a branching **choice menu** on an NPC, and a
scripted **actor cutscene** that plays on entry. Both are declarative `field.toml` blocks.

**Prerequisites:** a working field project from [tutorial 01](01-first-fork.md) or
[03](03-original-art-field.md). Full schema: [FORMAT.md](../FORMAT.md).

## 1. A dialogue choice

A `[[choice]]` attaches a menu to an NPC (or to a floor zone — a lever/sign). Options can give
items, charge gil, and set story flags:

```toml
[[npc]]
name = "Merchant"
preset = "vivi"
pos = [0, -700]

[[choice]]
npc = "Merchant"                       # must match an [[npc]] name
prompt = "Buy a Potion for 100 gil?"
[[choice.options]]
text = "Yes."
reply = "A wise purchase."
give_item = ["Potion", 1]              # [item name-or-id, count]
gil = -100
set_flag = [8720, 1]                   # raise a story flag (author band: 8712+)
[[choice.options]]
text = "No."                           # put the decline row LAST — cancel/B selects it
reply = "Another time."
```

Zone-triggered variant: replace `npc = ...` with `zone = [[x1,z1],[x2,z2],[x3,z3],[x4,z4]]`
(4 convex corners on the walkmesh); the default `trigger = "action"` makes it a re-usable
press-to-open lever.

## 2. Branch on the flag

Story flags gate other content across the whole field (and, with campaign/journey scopes, across
fields). For example, an NPC that only appears after the purchase:

```toml
[[npc]]
name = "Collector"
preset = "steiner"
pos = [500, -700]
dialogue = "So you found a Potion..."
requires_flag = 8720                   # hidden until the flag is set (an index or a [[flag]] name)
```

Hand-picked flag indices belong in the safe author band **[8712, 16320)** — indices from 8000 up
to 8511 are the kit's auto-allocation band (once-guards for cutscenes, choices, chests), and
base-game state sits below that. `lint` flags collisions. Mechanics (save-persistent GLOB vs.
per-visit MAP, scopes): [FORMAT.md §Story flags](../FORMAT.md#story-flags--branching).

## 3. An entry cutscene

A `[cutscene]` runs ordered steps with player control locked. Declare a **cast**
(`actors = ["<npc name>", …]`) and the steps drive those NPCs — walk, turn, gesture, speak:

```toml
[[npc]]
name = "vivi"
preset = "vivi"
pos = [0, -300]              # where the actor RESTS (and stands on replay visits)
dialogue = "..."

[cutscene]
actors = ["vivi"]            # a cast of ONE: the steps below default to it, no per-step tag needed
once = true                  # play once ever (save-persistent); false = every entry
steps = [
  { teleport = [-2000, -300] },   # snap off-screen so he can walk IN
  { walk = [0, -300] },           # walk to the resting spot
  { face_player = true },
  { animation = "glad" },         # gesture by name: `ff9mapkit animations vivi`
  { say = "...hi.", speaker = "[VIVI]" },
]
```

Without `actors`, the cutscene is pure narration (`say` / `wait` / `set_flag` steps). Either flavor
may end in a `then_warp = <field id>`. With a bigger cast (`actors = ["vivi", "guard", "player"]` —
`"player"` is a normal cast member) each actor step names its actor
(`{ walk = [...], actor = "guard" }`), a tagged `say` points its window at that actor, and
`with_prev = true` runs a walk/path/animation/turn beat in parallel with the one before it.
Schema: [FORMAT.md §cutscene](../FORMAT.md#cutscene--cutscene-optional).

## 4. Test

```powershell
ff9mapkit lint <project>\<name>.field.toml
py tools\deploy_field.py <project>\<name>.field.toml     # or build + install (tutorial 01 §4-5)
```

A `once = true` cutscene will not replay after its flag is set — retest with **~ → Flags**
(clear the guard flag), a fresh New Game, or `once = false` while iterating.
