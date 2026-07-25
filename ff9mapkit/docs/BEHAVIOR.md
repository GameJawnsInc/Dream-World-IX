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
                                           # route your patrols/marches reference, AND of
                                           # the pursuit lines your chases/wanders admit
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
- **Walkers do not pathfind at runtime.** They walk STRAIGHT at the target and slide on contact;
  a convex obstacle (a round monument) they slide around, but a concave notch WEDGES them. So any
  multi-point route belongs in a `[[marker]]` with `path = [[x,z], ...]` — the layout probe
  (`tools/field_layout_probe.py`) and `behavior lint` both **sweep those legs offline** and name
  the exact spot a walker would jam. Author the route once, verify it once, then reference it
  by name from `patrol` / `march`. The `laying-out-ff9-fields` skill carries the placement laws.
- **…but `patrol` / `march` can auto-route at BUILD time.** Add `route = "auto"` to the verb and
  any leg the sweep finds off-mesh is re-routed through the kit's walkmesh A* (the same
  pathfinder cutscene walks use) with the detour waypoints spliced in — **clear legs stay exactly
  as authored**, so opting in changes nothing until a leg actually jams (`patrol` routes its wrap
  leg too, since it always cycles). `behavior lint` then judges the ROUTED line and reports each
  auto-routed leg instead of calling it a jam. Honest limits: routing avoids **walls only** —
  other units move, so build-time character obstacles would be stale guesses (engine collision
  slides units past each other anyway); waypoint advancement still uses `arrive_r`, so a unit
  turns toward the next detour point from up to that far away (the same slack hand-authored
  routes have); and the spliced total must still fit the verb's **8-point ceiling** or the build
  fails naming the leg — split the route or relay the jamming leg by hand. `walk_to` / `hold` /
  `flee` can't auto-route: their walks start wherever the unit happens to be when the branch
  selects (there is no build-time origin to route from), and spliced flee points would become
  extra *refuges*, not waypoints.
- **What `chase` / `wander` get instead: THE PURSUIT SWEEP.** A chase follows a live position, so
  there is no line to route — but there IS a knowable *family* of lines: every pair of standable
  positions your branch's own `near` radius admits. `behavior lint` sweeps that family and tells
  you what fraction of it jams, plus the worst example as two coordinates ("pursuer here, quarry
  there, off-mesh for ~970u around this spot"). It's a **warning, not an error**: a dynamic jam
  needs your quarry to actually stand on a bad spot, unlike a static route's off-mesh leg, which
  jams every lap. Two things make it quiet or loud, both under your control:
  - **The engagement radius is the dial.** Jamming is a LONG-RANGE phenomenon — measured on the
    donut field the benches use, 0% of pursuit lines under 600u leave the mesh, 10% at 1200u, 82%
    past 2400u. Tightening the `near` row that gates the chase is usually the whole fix.
  - **An ungated chase** (no `near`/`any_near` row naming the target) is called out as such: its
    family is the entire field, so on anything non-convex it *will* wedge somewhere. If you want
    a unit to come from across the map, give it a `march` with `route = "auto"` for the approach
    and let `chase` take over from close range.
  A `wander` is swept the same way over its own box (a roll can land behind a wall — the walker
  then shoves that wall until the next roll). Coverage is sampled, and the sweep always prints the
  spacing it used: the number it reports is a floor on the real rate, not a ceiling.

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
- **`once` / `cooldown`** are *sticky* over movement behaviors: `once` lets its branch run
  through one full engagement and latches when it ends; `cooldown` re-arms N ticks after the
  behavior ends (a stalker that needs a breather once you escape).
- **`once` over an `announce` is an EVENT, not an engagement**: it fires the line once and
  *releases the branch immediately* (via the same edge-latched request lane battles use, so
  another body holding the dispatch level can't eat it). This matters because announce
  conditions are usually **monotonic** — a kill tally, a spent wave counter — and a sticky
  `once` over a condition that never goes false again would hold the selection forever,
  **starving every branch below it** (the BTTABLE round-2 defect: the win line, once fired,
  silently swallowed the wave-three line for the rest of the match).

## Pooled units — spawn reinforcements at your feet

`pooled = true` takes a unit out of the field at boot: its entry is seated **dormant** (no
spawn, no reveal-flag tricks) and it joins a named `pool`. Every pool gets a **spawn-request
flag** — the index prints at build and in `behavior compile` — and setting that flag from any
`[[choice]]` row (`set_flag = [<index>, 1]`) makes the next never-spawned unit of the pool
**materialize at the player's feet**. Where you were standing becomes the unit's *placement
post*, and the `hold_post` action holds it:

```toml
[[behavior.unit]]
npc = "recruit0"
hp = 4
pooled = true
pool = "recruits"

  [[behavior.unit.branch]]
  when = [{ hp_le = 0 }]
  do = { die = true }

  [[behavior.unit.branch]]
  when = [{ active = "raider" }, { near = ["raider", 250] }]
  do = { swing_at = "raider" }

  [[behavior.unit.branch]]
  when = [{ active = "raider" }, { near = ["raider", 700] }]
  do = { chase = "raider", standoff = 160 }

  [[behavior.unit.branch]]
  do = { hold_post = true }                  # guard wherever the player dropped me
```

That tree is a **placement defender** — the Fort Condor unit: hire it anywhere, it holds that
exact spot, intercepts what comes near, and walks back to its post after the fight. Rules:
one spawn per request (set the flag again for the next unit); an exhausted pool consumes the
request silently; a dead pooled unit doesn't respawn; `~ → Reload field` refills the pool.
Until activation the unit simply isn't there — every `active`/`near` gate in other trees
already treats it as absent. (`hold_post` also works on a normal boot-spawned unit, where the
post is just its own spawn point.)

### Price and the buy-anywhere button

A `[[behavior.pool]]` row adds the economy:

```toml
[[behavior.pool]]
name = "recruits"
price = 300                # gil gate + RemoveGil, compiled into the activation block
button = true              # a press-SELECT-anywhere hire poller (or a PSX button mask)
request_flag = 8848        # explicit GLOB bit (required with button; outside the
                           # blackboard band — the parked menu below must set it)
```

`price` charges **only when a soldier actually spawns** — a request with too little gil, or
against an empty pool, is consumed without charging (gil is real save state; a field reload
does not refund). `button` seats a poller entry (the in-game-proven Fort-Condor shape: a
per-frame button poll, an announce blip, then the hire menu) — author the menu as a **parked
zone choice** (a `[[choice]]` whose zone sits far off-mesh so walking never triggers it; the
poller dispatches it remotely) with a Hire row that does `set_flag = [<request_flag>, 1]`:

```toml
[[choice]]
zone = [[9000,9000],[9200,9000],[9200,8800],[9000,8800]]   # parked: never walked into
prompt = "Deploy a soldier HERE for 300 gil?"
instant = true
  [[choice.options]]
  text = "Hire (300 gil)"
  reply = "Deployed!  Hold this ground!"
  set_flag = [8848, 1]
  [[choice.options]]
  text = "Not now."
```

The build matches the menu to the pool by that flag (exactly one zone choice must set it) and
wires the poller automatically. `price` also works without `button` — an NPC-talk or walk-in
hire menu pays the same way, since the gate lives in the activation block, not the menu.

**Honest hire rows — the published `hireable` flag.** Every pool also gets a
`pool.<name>.hireable` flag (index printed at build and in `behavior compile`):
`(gil ≥ price, when priced) AND not sold out`, refreshed by the ticker every pass. Put
`requires_flag = <that index>` on the Hire row and the row **vanishes** the moment the hire
would be refused — the menu can never say "Deployed!" to a request the activation block will
consume without filling (pair a `requires_flag_clear` row for an explicit "sold out" line if
you prefer words over absence). One menu may carry rows for SEVERAL pools — give each pool an
explicit `request_flag` and each row its own `set_flag`/`requires_flag` pair; only the pool
carrying `button` needs to be matched to the menu.

### `award` — pay the player, exactly once

`do = { award = 2000, item = "Phoenix Down" }` adds gil (0..16777215) and/or an item
(name or id; `count = n` for stacks) to the party — the minigame **win-reward** lane. It
**requires `once`** on its branch and compiles on the event-Once machinery (edge-latched
request, latch-first body), which is precisely what makes the payout exactly-once even though
a win condition like `time_below = 1` holds forever. Pair it with a separate `announce`
branch for the fanfare text. Field reload re-arms it (bench semantics — a shipped minigame
gates the whole match behind a story flag instead).

Every unit's `selected` byte is a **live trace** of which branch owns it this tick — the build
report (and `behavior compile`) prints the full blackboard map, and the in-game debug menu's
Flags panel becomes a behavior inspector for free. `~ → Reload field` resets everything:
flags, HP, corpses, clocks, latches.

## The clock, waves, and real battles

Field-level **`timer = <seconds>`** starts FF9's own countdown HUD on entry (the Festival
of the Hunt's clock; `~ → Reload` resets it), and two condition verbs read it:
**`time_below = N`** / **`time_above = N`** (remaining seconds). Gate different units'
march branches on descending bands and you have **timed waves** — the Hunt's own
scheduling shape:

```toml
[behavior]
timer = 180

  # wave 1 marches at 2:50, wave 2 at 1:30 — same tree shape, different bands
  [[behavior.unit.branch]]
  when = [{ time_below = 170 }, { not_flag = "lost" }]
  do = { march = [[x1, z1], [gx, gz]], route = "auto" }
```

**`battle = <scene id>`** fires a REAL battle (the engine's swirl, the actual fight, the
return to the field). It is **one-shot per field load by construction** — a compiled latch
gates the dispatch, so the reactive tree re-selecting the branch after you return can't
re-fire it. The build automatically installs the after-battle Main_Reinit machinery (and
the field-BGM resume) whenever a behavior compiles a battle — no `[encounter]` block
needed. Use a **stock scene id** (the donor's own battles are the safe pick) and no
BattlePatch line is needed either. The Fort Condor loss shape: the gate is a unit with
`hp`; raiders `swing_at` it; its `hp_le 0` branch fires the boss battle and raises
`"lost"`; a `time_below = 1` branch on a surviving gate announces the win.

## Data tables, counters, and the schedule clock

The unrolled `time_below` bands above work, but the schedule is **code**. Tables make it
**data** — real int arrays in the save (Memoria's `gScriptVector`, reachable from `.eb`
expressions with **computed indexes** via the engine's `0xD3` VECTOR lane):

```toml
[behavior]
timer = 180
counters = ["wave", "kills"]         # runtime cells, seeded 0 on entry

[[behavior.table]]
name = "sched"                       # wave start-times — a rebalance edits DATA
values = [170, 90, 60]               # (1..64 values; ±26-bit ints)

[[behavior.schedule]]                # THE WAVE CLOCK: while the countdown HUD sits
counter = "wave"                     # below sched[wave], wave += 1 — one generic
table = "sched"                      # engine instead of N unrolled bands
```

- **Everything re-seeds at every field entry** (and `~ → Reload`): tables get their
  declared values, counters get 0 — deterministic per-session state, never a stale
  save tail (the seed truncates first). Vector ids allocate from 1000 per field
  (`id = N` overrides; the ids are save-global, which the re-seed makes harmless).
- **Reading**: `counter_ge` / `counter_le` / `counter_eq = ["wave", 2]` gate branches
  on a counter; `table_ge` / `table_le` / `table_eq = ["sched", index, n]` compare a
  table cell — and `index` may be a **counter name**, which is a genuine
  runtime-computed lookup (`sched[wave]`), the thing plain `.eb` variables can never do.
- **Writing**: `die = "kills"` bumps that counter exactly once (the death body runs
  once). The schedule clock advances its own counter. That's the v1 write surface —
  deliberately small.
- **The clock stops itself**: when `wave` walks off the table's end, the read fails
  soft to 0 and `timer < 0` never holds — no latch flag, the data is the terminator.

The wave shape becomes: units gate their march branches on `counter_ge = ["wave", 1]`
(wave 2 on `["wave", 2]`, …), the herald announces on `counter_eq`, and a win condition
reads the kill tally with `counter_ge = ["kills", N]`. Bench: field 30415
(`studies/behavior-trees/bttable_bench.py`) — the first in-game consumer of computed
array indexing anywhere.

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
