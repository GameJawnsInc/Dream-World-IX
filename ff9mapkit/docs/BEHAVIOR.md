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

### The ITEM pool — the shop as the hire menu

```toml
[[behavior.pool]]
name = "levy"
item = "Soldier Contract"   # name or id — the pool's currency is this ITEM
```

An **item pool** has no request-flag lane at all: *holding the item is the request*. Every
ticker pass, if the party holds ≥ 1 of `item` and a dormant member remains, one item converts
into one spawn at the player's position (`B_HAVE_ITEM` gate; `RemoveItem` sits at the spawn
site, so an exhausted pool consumes **nothing** — contracts are real inventory, they survive
saves and can be sold back). One convert per tick gives a natural stagger. `item` is exclusive
with `price`/`button`/`request_flag`.

The hire UX is the **native shop**: author a `[[shop]]` that sells the contract item and a
shopkeeper `[[npc]] opens_shop = N`. The shop UI hard-pauses field scripts while open (the
engine's `SetEventEnable(false)` — the countdown timer keeps ticking), so purchases convert
on the first tick after it closes: buy three contracts, leave the counter, three soldiers
muster at your feet. The pool's `hireable` flag reads the live inventory (`have_item`-shaped)
instead of a gil compare.

Two companion pieces speak inventory directly: the **`have_item` cond** —
`when = [{ have_item = ["Soldier Contract", 2] }]` (count optional, default 1) — and the
**`item:` hud source** (below). `have_item` reads a **top-of-tick snapshot**, not the live
count: pool activation runs before the tree blocks (a fresh spawn must tick the same
pass), so a live read raced the pool's own consumption — holding exactly N never
satisfied `have_item >= N` (the ARMOURY round-2 skew, owner-diagnosed). The snapshot is
written with the mirrors, before any pool consumes: every cond in a pass judges the
inventory as the player left it. The pool's own gate stays live — it is the consumer.

### Runtime shop stock — `add_shop_item` / `remove_shop_item`

```toml
[[behavior.unit.branch]]
when = [{ counter_ge = ["wave", 2] }]
do = { add_shop_item = [40, "Elite Contract"] }   # [shop_id, item]
once = "stock2"                                    # REQUIRED — the event-Once lane
```

> **THE DRAINING-CONDITION LAW (ARMOURY round 3):** the selector picks **one branch per
> unit per tick**, so two once-branches on the same condition fire on *consecutive*
> ticks — and a condition an item pool is draining (`have_item >= N` while the pool
> converts) may hold for exactly ONE tick: the first branch fires, the second finds it
> already false. To hang several once-effects on one transient moment, latch it: the
> first branch carries `raise_flags = ["moment"]` and the others gate on
> `when = [{ flag = "moment" }]` — a raised flag doesn't drain. (Monotonic conditions —
> kill tallies, spent waves — don't need this; the event-Once lane alone serves them.)

Mutates a shop's buy list at runtime (Memoria's extended `AddShopItem`, 0x115) — the
wave-by-wave armoury unlock. Engine semantics the compiler bakes in: the shop must already
exist in `ShopItems.csv` (a `[[shop]]` in this field, or a vanilla 0–31 — lint refuses
anything else, because the engine *silently no-ops* on an unknown id); an add emits
**remove-then-add** (the engine's raw list-add would duplicate the row on a re-fire); and
the mutation is **session-global in-memory state** — it survives field transitions and
`~ Reload`, resets at relaunch, and is never saved. `once` is required and is what makes
the semantics clean: the latch resets per field entry, so each session simply re-asserts
the unlock whenever its condition holds — shop state follows the seed law, like tables.

**The synthesis twin — `add_shop_synth` / `remove_shop_synth`** (`[shop_id, recipe]`,
`once` required, same lane): Memoria's `AddShopSynthesis` (0x116), with the mutation
inverted — it grafts the SHOP onto the RECIPE's `Shops` list, and the engine's silent
no-op guard is on the *recipe*. `recipe` is a vanilla row's int id, or a **result item
name** matched against this project's own `[[synthesis]]` recipes and resolved at build
to the id the CSV emitter mints (deterministic base-max+1; a string selector therefore
needs a reachable install at build — int selectors don't). The target shop must open as
SYNTHESIS — absent from `ShopItems.csv`; lint refuses a `[[shop]]` buy id or vanilla
0–31. The hidden-recipe idiom: declare the locked recipe against a PARKED shop id (no
opener) and graft the real shop onto it at runtime.

> **Why a relaunch resets it but New Game does not:** `ff9buy.ShopItems` is a static,
> process-lifetime table loaded from the CSV once at engine startup. `AddShopItem`
> mutates that table directly — *above* the save layer. New Game swaps the save
> (inventory, flags, gil) but never re-runs the static loaders, so a fresh game
> inherits any unlock from the previous session until the owning field re-asserts or
> the process restarts. An author who needs a lock to *re-engage* should assert both
> directions per entry: an `add_shop_item` branch on the condition and a
> `remove_shop_item` branch on its inverse (the two-sided assert).

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

### `sfx` — a sound-effect cue

```toml
[[behavior.unit.branch]]
when = [{ flag = "won" }]
do = { sfx = 108 }                 # the item-get jingle; ids -> `ff9mapkit sfx-list`
once = "fanfare"
```

Plays one SFX through `RunSoundCode3` (0xC8) with the exact bank + pan/volume triple the
kit's treasure chest plays in-game (`bank = 53248` by default; the only option key).
**Once-wrapped** it rides the event-Once lane — fire-and-release, the purse-fanfare shape:
gate it on the same *monotonic* flag as an `award` branch and the pay fires one tick, the
cue the next (flags don't drain — the draining-condition law's authoring fix). **Bare**, it
behaves like a bare `announce`: it plays when the branch dispatches and cannot re-fire
until the tree deselects and re-selects it (an alarm sting each time raiders close in, not
a per-tick klaxon). `[siege]` exposes the win lane directly as `win_sfx = <id>`.

### `flash` — a screen flash

```toml
[[behavior.unit.branch]]
when = [{ flag = "won" }]
do = { flash = [255, 255, 255] }   # wash to this colour and back
once = "winflash"
```

One screen wash — the donor rest bracket's `FadeFilter` pair (field 300's exact
mode/frame/intensity shape, already in-game proven through the savepoint tent):
`CalculateScreenPosition(player)` + SUB out to the colour over 24 frames, then restore
over 16. Same two stances as `sfx`: once-wrapped = event-Once fire-and-release (the
win-wash lane); bare = fires per dispatch. The body holds the unit's dispatch level for
~40 frames while the wash runs — queued one-shots (a pending purse, an announce) fire the
moment it releases, so stack theater as separate branches on one monotonic flag: pay,
jingle, wash on consecutive rungs. `[siege]` exposes it as `win_flash = true` (white)
or `[r, g, b]`.

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

## Scans — the vector loop (v2 rung 0 — in-game proven)

```toml
[[behavior.scan]]
name = "shrine"                # [a-z][a-z0-9_]*
units = ["m0", "m1", "m2"]     # roster (behavior units; <= 64)
point = [1153, -200]           # the probe point
radius = 300                   # Chebyshev box half-width, 1..30000
count = "at_shrine"            # counter cell receiving the headcount
flags = "near_shrine"          # optional: the per-unit 0/1 table's name
```

Each run pass the compiler copies the roster's position mirrors into internal
px/pz tables, then runs a bounded LOOP whose reads **and** writes index vector
cells by the live loop byte: each unit's inside-the-box flag lands in the flags
table (a computed-index write), is read back and accumulated, and the total is
published into `count` — trees gate on `counter_ge` as usual, and a named
`flags` table is readable by the `table_*` conds (`table_eq = ["near_shrine",
0, 1]` = "is roster member 0 in the box"). The count flows *through* the flag
round-trip on purpose: a mis-indexed cell breaks the number rather than passing
silently. Cost: ~400B of ticker for an 8-unit roster.

The composition is in-game proven (THE PILGRIMAGE, field 30416 — an 8-pilgrim
roll call whose whole announce ladder derives from the loop).

**The group form**: `group = "raiders"` instead of `units` loops the GROUP'S
own tables (no copies), `point`/`radius` become optional (absent = a pure
roster headcount), and `alive_only = true` gates every cell on act && hp>0 —
the team-wipe / alive-count primitive (`counter_eq = ["mus_alive", 0]` fires
the moment the roster is wiped). ~100B of ticker per scan. The units form
keeps its rung-0 caveat: mirrors freeze when a unit deactivates (a dead unit
still standing in the box keeps counting — scan rosters that stay alive, or
use the group form with `alive_only`). This is the first stone of the v2 vector substrate
(`studies/behavior-trees/PLAN.md`, THE THREE WALLS); the group loop below
builds on it.

## Groups + `engage` — THE GROUP LOOP (v2 rung 1)

```toml
[[behavior.group]]
name = "raiders"               # [a-z][a-z0-9_]*
units = ["mu0", "mu1", "mu2"]  # roster; every member needs hp=; one group each

# a branch on any NON-member unit:
do = { engage = "raiders", radius = 900, contact = 170, damage = 1, interval = 25, speed = 60 }
```

A group moves its members' state into roster tables: `group.<name>.px/pz/act`
(mirrored per tick) and `group.<name>.hp` — **the hp cells ARE the members'
hit points** (seeded from `hp=`, damaged by every swing, read by the `hp_le`/
`hp_gt` conds, all rerouted automatically; the tables are also readable via
`table_*` conds). `engage` then replaces the whole unrolled pair apparatus
with ONE branch: a sticky ACQUIRE loop keeps a valid target in the unit's
target register (first-in-range in roster order — roster order is the
priority list, matching v1 pair-branch semantics) and the branch runs
two-phase — within `contact` a single target-INDEXED strike body (damage and
facing through the register), otherwise a pursue feed walking at the target's
table position (live retarget). When the target dies or leaves `radius`, the
register drops and the loop re-acquires — units pivot to the next foe with no
extra authoring, which the unrolled form could only approximate by branch
order.

The economics are the point (the three walls): a 7-per-side mutual brawl costs
**42% of the unrolled bytes** (one ~170B body per unit instead of one ~108B
body per PAIR; ~880B of ticker per unit instead of ~2,340B; one swing timer +
two register bytes instead of a band byte per pair) — pinned by a suite test
so the ratio can't silently regress. v2 limits: one `engage` per unit,
engaging your own group is refused, and `raise_flags`/`clear_flags` don't ride
the engage branch. Acquisition defaults to first-in-range in roster order;
**`nearest = true`** switches the acquire loop to an argmin over Chebyshev
distance (units pair off with the closest living foe within `radius` and
survivors pivot to the closest next victim; the scratch registers are shared
field-wide — ~70B of ticker per unit, four blackboard slots total).

## HUD strips — `[[behavior.hud]]` (the live counter substrate)

```toml
[[behavior.hud]]
window = 6                                       # Dialog.WindowID 0..7
values = ["gil", "troops", "raiders_up", "hp:base"]   # 1..8 value sources
digits = [6, 2, 2, 2]                            # per-slot width reserve
text = "[MPOS=8,8]GIL [NUMB=0]  TROOPS [NUMB=1]  RAIDERS [NUMB=2]  DEPOT [NUMB=3]"
```

A **value source** is a counter name, `"gil"` (the live purse), `"timer"` (the
countdown HUD's remaining seconds), `"hp:<unit>"` (a unit's hit points — the
roster cell for a group member), or `"item:<item>"` (the live held count of an
item, name or id — watch contracts tick down as an item pool converts them).
Slots are written every pass; the engine itself re-renders only when a number
actually changed.

The stock substrate every PC minigame HUD uses (the hunt points, the auction
bid, the jump-rope count — there is no number opcode in FF9): slot i's
`[NUMB=i]` renders `values[i]`, fed by `SetTextVariable` with the source as an
expression arg, into a TRANSPARENT window (flags 16 — frameless floating
text). The `.mes` line is minted like an announce and `[IMME]` is prepended
when absent so the strip never types in.

Three engine facts shape the emitted code, each learned from a playtest:

- **The window opens exactly ONCE** and is never re-issued: the engine
  re-renders a live dialog's `[NUMB]` variables in place every frame they
  change (`Dialog.Update → UpdateMessageValue`), while re-issuing
  `WindowAsync` disposes and recreates the window — the open animation
  replaying on every change is a visible flicker. A dirty-mirror check keeps
  the variable writes off quiet frames; the shown-latch clears on `~ Reload`.
- **`[NFOC]` is prepended** (with `[IMME]`): NoFocus sets
  `Dialog.FlagButtonInh`, so the player's confirm can never close the strip —
  without it, clicking through any dialogue closes the HUD for good.
- **`digits` reserves the width** (default 2, up to 7): `AutomaticSize` bakes
  a dialog's width ONCE at open from the text as it renders THEN, and a
  variable change never re-sizes it — so a strip opened showing `0` clips when
  a counter reaches `11`. The open pass feeds every slot `10^digits - 1`
  before opening, then the real values land the next tick. Size `digits` to
  the widest value a slot will ever show (gil wants 6–7).

Authoring notes: place with `[MPOS=x,y]` — the PSX-ish 320×224 UI grid (stock
pins its save menu at `20,16`), and **the countdown timer owns the top-left
corner**, so a strip belongs below it (`10,48` clears it) or elsewhere on
screen. The window auto-sizes to its text, so keep labels short — a long strip
wraps to a second line (`[WDTH]` is a no-op in this engine). Combine with
`alive_only` scans for live team headcounts.

Win-condition note (a Condor playtest bought this one): two *separate* award
branches each carry their own once-latch, so "pay on rout" plus "pay at the
final whistle" pays TWICE. Model endings as **detect-then-pay** — each ending
branch only announces and raises a shared `won` flag (gated on
`not_flag = "won"`, so whichever lands first closes the other out), with ONE
award branch gated on `flag = "won"`. ~180B of ticker + one window slot per strip; static values cost
nothing.

## Limits (v1)

- **Size**: assembled bodies have NO practical jump ceiling (the label assembler relaxes
  long jumps through fall-through-safe islands automatically, and same-target long jumps
  share islands), but the `.eb` **file** is u16-addressed — roughly **64KB total**,
  engine-fixed — and the entry table caps at **255 slots**. On a donor fork that leaves
  ~50-55KB for all compiled behavior (ticker + every dispatch body); each unit×target
  pair branch costs ~135B of ticker plus ~90B of body, so pair-target scope is the knob.
  A third budget binds at swarm scale: the blackboard scratch band is **820 bytes** of
  `gEventGlobal` (~40 units with ~6 swing pairs each; ~14B per unit + ~1B per swing).
  Every over-budget build fails loudly at build time (never a wrapped offset), and
  `CompiledBehavior.size_report()` prints the per-unit **byte histogram** — where the
  bytes actually went — so the trim is a decision, not a hunt.
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
