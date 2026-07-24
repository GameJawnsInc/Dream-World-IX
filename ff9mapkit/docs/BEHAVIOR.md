# Behavior trees — NPC AI as field content

`[behavior]` gives the named `[[npc]]`s of a field real, layered AI — patrol routes that trade
on a shift clock, guards that notice you and give chase, mutual combat with HP and deaths,
flee-at-low-HP, alarms that regroup a whole cast, random wandering — **compiled to pure field
bytecode**. Zero DLL, runs on stock Memoria, hot-reloads and fully resets like any other field
content. Reference: [FORMAT.md § `[behavior]`](FORMAT.md#behavior-optional--behavior-trees-compiled-to-field-bytecode).

```
ff9mapkit behavior compile <field.toml>    # dry-compile: the report (blackboard map, action
                                           # ids, public-flag indices) — nothing written
ff9mapkit behavior lint    <field.toml>    # static checks + a walkability SWEEP of every
                                           # route marker your patrols/marches reference
ff9mapkit behavior view    <field.toml>    # compile, then disassemble every generated body
```

A normal `ff9mapkit build` (and every deploy that runs it) compiles and installs the behavior
automatically — there is no separate step.

## The model: one brain, priority branches

Every tick, each unit's **branches are tried top to bottom**; the first whose `when` conditions
all hold selects its `do` action. That's the whole model — it is REACTIVE (state lives in the
world and the blackboard, not in a program counter), which is why everything is interruptible
and resumable for free:

```toml
[[behavior.unit]]
npc = "guard"
hp = 5

  [[behavior.unit.branch]]
  when = [{ hp_le = 0 }]
  do = { die = true }                        # highest priority: death

  [[behavior.unit.branch]]
  when = [{ hp_le = 1 }]
  do = { flee = "bandit", to = ["market", "east_nook"], speed = 75 }

  [[behavior.unit.branch]]
  when = [{ active = "bandit" }, { near = ["bandit", 300] }]
  do = { swing_at = "bandit" }               # melee at contact

  [[behavior.unit.branch]]
  when = [{ active = "bandit" }, { near = ["bandit", 900] }]
  do = { chase = "bandit", standoff = 180, speed = 65 }

  [[behavior.unit.branch]]
  do = { patrol = "ring" }                   # the unconditional fallback
```

Read it aloud and it is the unit's job description: *dead men die; the badly wounded run for
the market; fight what's in reach; chase what's in sight; otherwise walk the ring.*

The **last branch must be unconditional** and a *static* feed (`walk_to` / `hold` / `patrol` /
`march` / `flee` / `wander`) — it's what the unit does when nothing else applies, and the build
presets it before the field wakes.

## Movement is real walking

Actions that move (`walk_to`, `chase`, `patrol`, `march`, `flee`, `wander`) use the engine's own
smooth walk — unit collision, walkmesh sliding, walk animation. Two consequences:

- **Per-action `speed=`** changes are visible immediately, even mid-walk — a fleeing civilian
  genuinely bolts (80) compared to her stroll (30).
- **Walkers do not pathfind.** They walk STRAIGHT at the target and slide on contact; a convex
  obstacle (a round monument) they slide around, but a concave notch WEDGES them. So any
  multi-point route belongs in a `[[marker]]` with `path = [[x,z], ...]` — the layout probe
  (`tools/field_layout_probe.py`) and `behavior lint` both **sweep those legs offline** and name
  the exact spot a walker would jam. Author the route once, verify it once, then reference it
  by name from `patrol` / `march`. The `laying-out-ff9-fields` skill carries the placement laws.

`patrol` loops its points forever; `march` walks them once and holds the last (a raid column,
an escape run). `flee` is deliberately not vector math: you give it **refuge points in priority
order** and the unit runs to the first one the threat isn't camping — it reads as gameplay
("fall back to the keep; if it's overrun, the market") and the targets are always walkable.

## Combat

`swing_at` ticks `damage` off the target's HP byte every `interval` frames while selected —
give both sides swing branches and you have MUTUAL combat with no referee. Death is not
built-in: it's a branch (`when = [{ hp_le = 0 }] do = { die = true }`), which means undying
sparring partners, cowards that always flee at 1 HP, and last stands are all just different
trees. `die` removes the unit (its `active` flag drops, so every `active`/`any_active` gate
in other trees reacts the same tick).

## Alarms, shifts, levers

- **`raise_flags`** on a branch writes named flags while it's selected — the watcher pattern:
  the sentry's notice branch announces AND raises `"alarm"`, and every other tree gates its
  combat block on `{ flag = "alarm" }`.
- **`alternators`** flip a named flag every N ticks — gate one guard's patrol on
  `{ flag = "shift" }` and the other's on `{ not_flag = "shift" }` and they trade routes on
  the clock.
- **`public_flags`** are set from OUTSIDE the behavior — a `[[choice]]` lever, a gateway.
  Their allocated indices print at build time and in `behavior compile`; wire them into
  `set_flag = [<index>, 1]` rows.
- **`once` / `cooldown`** are *sticky*: `once` lets its branch run through one full engagement
  and latches when it ends (a war cry, a breach line); `cooldown` re-arms N ticks after the
  behavior ends (a stalker that needs a breather once you escape).

## Watching it run

Every unit's `selected` byte is a **live trace** of which branch owns it this tick — the build
report (and `behavior compile`) prints the full blackboard map, and the in-game debug menu's
Flags panel becomes a behavior inspector for free. `~ → Reload field` resets everything:
flags, HP, corpses, clocks, latches.

## Limits (v1)

- Novel fields and `--native`/`--editable` forks only — a VERBATIM fork runs the donor's real
  `.eb` (no kit-injected NPC entries to bind to); `validate` refuses it with this explanation.
- A behavior unit can't also be a `[cutscene]` cast actor (both mechanisms drive the actor at
  the same interrupt level), and can't carry `holds` / `requires_flag` / scenario gating.
- Conditions AND within a branch; OR across branches (or via `any_flag` / `any_near` /
  `any_active`). Deeper nesting, action-result plumbing, and `Parallel` are deliberately out —
  the flat form has expressed everything the study's showcases needed.

The Python surface (`ff9mapkit.content.behavior`) remains available for power users — the TOML
surface compiles through exactly the same compiler, laws and all (mirror-gated perception, the
sync-walk duty split, race-free action dispatch; see `studies/behavior-trees/PLAN.md`).
