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

### `brains = true` — the per-unit-brain backend

By default one central ticker entry evaluates every unit's branches each frame. Setting
`brains = true` in `[behavior]` compiles each unit's branch segment into its **own**
one-function entry instead, run as a shared-script coroutine spawned from the unit's loop head
(`RunSharedScript`; inside the coroutine the engine binds the CALLER as the current object, so
the brain dispatches onto its own unit via uid 255). The residual ticker keeps the shared
lanes — warm-up, mirrors, clocks, scans, pools, HUDs. **Semantics are identical by
construction** (same conditions, same blackboard, same action bodies); what changes is scale
headroom: no single body ever approaches the ±32K jump reach, so very large rosters compile
without jump islands. Die actions additionally stop the unit's own brain before the entry
terminates (a disposed unit must never leave a live coroutine behind). The build refuses any
layout where a unit's entry slot + 64 collides with an occupied slot (the brain's runtime uid).

One dispatch difference under brains: a **`die` is must-land**. Routine action dispatches
deliberately drop while the unit is busy (that *is* the run-gate — a mid-battle-swirl chase
request should vanish), but a death must actually happen, even if the unit is held by an open
talk dialogue or a blocked walk when it triggers. The brain therefore issues the die as the
engine's *blocking* request (REQSW): it waits on the instruction until the unit's script level
frees, then binds — each brain blocks only itself, and the selection flip already released any
looping body the unit was running. (The v1 ticker keeps the retrying non-blocking form: one
shared ticker must never wait on one busy unit.)

And the **one-shot family runs inline in the brain**. A `battle`, an event-once
`announce`/`sfx`/`flash`/`stop_timer`, an `award` or shop mutation does nothing that cares
which object executes it — the work is a battle id, a window, a sound, a screen fade, an
inventory edit — so under brains it executes directly in the brain coroutine instead of being
dispatched onto a per-member function: a class pays for ONE copy of each one-shot, not one per
member. The engine's busy-check is preserved by reading the unit's script level before firing
(the free-gate): a one-shot that triggers while the unit is held — say you're holding its talk
dialogue open — defers and fires the moment the unit frees, never lost and never mid-dialogue.
Non-once (looping) variants keep per-member bodies, since they hold the unit's dispatch level
while selected — a residency the brain can't carry.

### Classes — `npcs = [...]`: many units, ONE shared brain

With `brains = true`, a `[[behavior.unit]]` row may bind a **list** of NPCs instead of one:

```toml
[[behavior.unit]]
npcs = ["kn0", "kn1", "kn2"]      # a CLASS: one row, many bodies
class = "knight"                  # optional name (reports/labels)
hp = 4
speed = 55
  [[behavior.unit.branch]]
  when = [{ hp_le = 0 }]
  do = { die = "fallen" }
  [[behavior.unit.branch]]
  do = { engage = "mus", nearest = true }
  [[behavior.unit.branch]]
  do = { hold_post = true }       # each member holds its OWN spawn
```

The row's branches compile **once** into a single brain entry that every member spawns as its
own coroutine — each running copy drives *its* spawner (the engine binds the caller as the
current object every frame). Per-member state splits by who touches it. State something
*outside* the brain reads or writes (active/selected/targets/speeds/mirrors, the engage
target register, body-written one-shot latches) lives in uid-indexed script-vector cells,
seeded like every kit table: the shared brain reads *its own* member's cells through the
caller's uid, while member-side bodies read the same cells at their fixed uid. State only the
brain itself touches (sticky `once`/`cooldown` latches and timers, patrol progress, wander
state, the one-shot request lanes) is **coroutine-private** — each running copy carries its
own zeroed-at-spawn variable block, so it costs no table and no band at all. One consequence
for debugging: those private latches are not visible in the `~` Flags panel — the compile
report prints each brain's private-block map instead. Net effect: a 7-member class costs ONE
brain's bytes instead of seven, and its per-member state stops consuming the flag band.
(Every brains-backend unit gets the private block, classed or not.)

What a class row can say: the feeds (`walk_to`/`hold`/`hold_post`/`chase`/`patrol`/
`march`/`flee`/`wander`), `engage`, `swing_at`, `hold_ground`, `die`, sticky `once`/`cooldown`,
`raise_flags`/`clear_flags` (any member raising counts) — and the one-shot family
(`battle`/`sfx`/`flash`/`stop_timer`/`announce`/`announce_npc`), whose latches are **once PER
MEMBER**: each member fires its own one-shot once (three classed knights with a `once` war cry
= three cries, one `.mes` line; each Mu with a `battle` branch fires its battle once). Want
once *per class*? Have the firing branch `raise_flags = ["cried"]` and gate it on
`{ not_flag = "cried" }` — the first member to fire silences the rest. Only the payout verbs
(`award` / shop stock+synth) refuse class rows — once-per-member there means N payouts; keep
them on a single-npc row (a class and plain rows mix freely on one field). Simultaneous
announces share the dialog window — stagger member placement (or windows) if two members can
fire the same tick. A class tree is ONE program: per-member variation
comes from state (`hold_post` posts, `engage` dynamic targets), not literals — and a class
name can never be the *target* of someone else's condition (name a member, or use groups).
Members keep their individual names everywhere else (groups, other trees' conds, `hp:` HUD
sources). `anim` options need all members to share one model. hp rule for class self-tests
(`hp_le` etc.): either every member sits in the SAME `[[behavior.group]]`, or none is grouped.

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
  A `wander` gets its own honest model — **THE WANDER SWEEP**: the engine's roll lands ANYWHERE
  in the `centre ± radius` box and *never checks the mesh*, so the lint tests straight legs from
  standable positions to EVERY roll cell, walkable or not (a roll behind a wall, past the mesh
  edge, or on another floor makes the walker shove that boundary until the next roll — the
  in-game "glitchy waypoints" look). It reports the jam fraction plus the box's own composition
  ("97 of 225 roll cells sit OFF the walkmesh"). Shrink the radius or recentre until the box
  hugs the walker's floor. A seeded wander (`seed = N`, see
  [Roll streams](#roll-streams--seeded-randomness-you-can-predict)) rolls the same box, so the same
  sweep applies — the seed fixes the order of the targets, not where they may land. Coverage is sampled, and the sweep always prints the
  spacing it used: the number it reports is a floor on the real rate, not a ceiling.
- **THE FLOOR LAW (multi-floor fields).** A walker lives on ONE floor and can only change floors
  across a **seam** edge; anywhere else two floors meet in flattened 2D — a terrace base, a
  balcony lip — is a WALL, invisible to a top-down point test. Every sweep above is floor-aware:
  a static route leg crossing floors away from a seam is an **error** ("NO SEAM"), and pursuit /
  wander legs count such crossings as jams. The layout probe tints each floor and draws seams in
  green, so a terrace reads at a glance — look at `topdown.png` before relaying a cast. **The
  runtime half:** gate a chase with `same_floor = "<target>"` (see [Floors](#floors--on_floor--same_floor--other_floor))
  and it never engages across a terrace; `behavior lint` then sweeps only its same-floor pairs, and
  names an ungated chase whose jams are mostly cross-floor.

`patrol` loops its points forever; `march` walks them once and holds the last (a raid column,
an escape run). `flee` is deliberately not vector math: you give it **refuge points in priority
order** and the unit runs to the first one the threat isn't camping — it reads as gameplay
("fall back to the keep; if it's overrun, the market") and the targets are always walkable.

## Floors — `on_floor` / `same_floor` / `other_floor`

On a field with more than one walkmesh floor — a terrace, a balcony, a raised walkway — a unit
can ask which floor someone stands on. The engine already knows (it re-finds every actor's
walkmesh triangle each frame); these conditions read its answer (the `.eb` token `B_BGIFLOOR`).

```toml
[[behavior.unit]]
npc = "guard"
  [[behavior.unit.branch]]
  when = [{ near = ["player", 900] }, { same_floor = "player" }]   # engage only on MY level
  do = { chase = "player", standoff = 200 }
  [[behavior.unit.branch]]
  do = { hold_post = true }

[[behavior.unit]]
npc = "bellringer"
  [[behavior.unit.branch]]
  when = [{ on_floor = "terrace", who = "player" }]                # the player is up there
  do = { announce = "Someone's on the roof!" }
  once = "roof"
  [[behavior.unit.branch]]
  do = { hold_post = true }
```

- **`on_floor = F`** — the row's own unit (or `who = "player"` / another unit / a class member)
  stands on floor `F`, or on any of a list of up to 8. A floor is its **index** (0, 1, …) or its
  **name**: each `o`/`g` object of a `[walkmesh] obj` is a named floor, numbered by first
  appearance among the OBJ's faces. Names resolve against the walkmesh the field actually ships;
  an unknown name or an index past the last floor is a build error.
- **`same_floor = "who"`** — both stand on the same floor. **`other_floor = "who"`** — both
  floors are known and different.
- **UNKNOWN is never a floor.** An actor with no floor reads **−1**: during the warm-up, while a
  pooled unit is not spawned or is dead, and whenever the engine turns its walkmesh tracking off
  (a ladder, a jump, a moving platform, a cutscene teleport). No floor condition is ever true on
  −1, and there are no `not_on_floor` / `not_same_floor` forms (they would read true there —
  write `other_floor`, or list the floors you mean). Note that a branch **below** a floor-gated
  branch still runs while the floor is unknown, like any lower branch.
- **A floor is an index, not a level.** One walkable level can be several floors joined by seams
  (a stock field can have twenty); `same_floor` compares indices, and says nothing about walls.
- **How it runs:** the ticker reads each sensed actor's floor into a mirror once per pass — the
  player's behind the staged latch, a unit's only while it is active — and conditions read the
  mirror, exactly like `near` reads the position mirrors. A field that uses no floor condition
  compiles byte-for-byte as before. The build prints each mirror's address (`[behavior] floor
  sensors: player -> Global.Int16[...]`) for the `~` Flags panel.
- **See it:** a HUD value `"floor:<who>"` shows a mirror (`-1` = unknown; give it 2 digits). The
  live triangle is `expr:B_PTR(250) B_BGIID` for the player and `expr:const(<its uid>) B_BGIID`
  for a unit — the build report prints the uids.
- v1 ticker and `brains = true` both work; a class row's own floor is its member's (`same_floor`
  on a class row compares each member's floor), but a class cannot be the TARGET (name a member).

## Combat

`swing_at` ticks `damage` off the target's HP byte every `interval` frames while selected —
give both sides swing branches and you have MUTUAL combat with no referee. Death is not
built-in: it's a branch (`when = [{ hp_le = 0 }] do = { die = true }`), which means undying
sparring partners, cowards that always flee at 1 HP, and last stands are all just different
trees. `die` removes the unit (its `active` flag drops, so every `active`/`any_active` gate
in other trees reacts the same tick).

### Fight theater — `anim` / `hit_sfx` / the death beat

```toml
do = { swing_at = "raider", anim = "attack_cid_1", hit_sfx = 636 }
do = { die = true, anim = "hiza_1", linger = 45 }     # collapse, hold, THEN vanish
```

`swing_at` and `engage` take **`anim`** (a one-shot clip on the striker) and **`hit_sfx`**
(the impact cue), both fired on the **damage tick** — inside the interval gate, never per
frame. The clip is deliberately **fire-and-forget** (no `WaitAnimation`): the swing loop
keeps ticking its selection check, so a strike stays interruptible and a looping clip
can't wedge the body.

`die` takes **`anim`** + **`linger`** — without them a unit *vanishes* the tick it dies
(the long-standing "instant vanish"). The active flag still drops first, so the dying unit
stops being a target the moment it starts falling; then the clip runs to completion
(`RunAnimation` + `WaitAnimation`) and the corpse holds `linger` frames before
`TerminateEntry`.

#### The field-animation laws

Playing a clip on a field object is the least self-evident surface in the kit — five
separate in-game rounds, each a different mechanism. All five are compiler invariants now;
they're written down because *every one of them fails silently or looks like a different
bug*.

1. **A blocking body must HOLD its dispatch level.** The ticker dispatches on `run == 0`.
   A body that used to be instantaneous (the old `die`) can gain a `Wait` and suddenly the
   ticker keeps dispatching that unit's *other* bodies underneath it — "soldiers still
   swing after the death anim starts". The death body sets `run` and never releases it.
2. **A different FORM is a different SKELETON** (the cross-form clip trap, above).
3. **Never `WaitAnimation` inside a level-4 async body.** Blocking there rendered *nothing
   at all*; the fire-and-forget shape renders. Hold the beat with an ordinary `Wait`.
4. **A one-shot is a LAYER, not a state.** `RunAnimation` ends — and the object then
   reverts to its **stand** clip (a corpse stands back up). Worse, an object still inside a
   blocked `Walk` is being driven by its **walk** clip, which overrides the one-shot
   outright — which is why units that die *in place* showed a clip and units that die
   *mid-march* showed none. Install the clip as the object's stand **and** walk animation
   (`0x33`/`0x34`) before firing it, and whatever the engine drives next drives your clip.
5. **Then it must FREEZE AT END.** A stand clip loops by definition, so law 4 alone makes
   the corpse replay its death for the whole hold. `SetAnimationFlags(1, 0)` (0x3F — the
   engine's own *"1: freeze at end"*, the idiom `content.chest` uses before its lid clip)
   plays it once and holds the final pose.

Laws 3–5 are why the death beat emits `stand → walk → flags(1,0) → anim → wait`, in that
order. A strike clip needs only the fire-and-forget half (it *should* return to idle).

> **THE OWN-CLIP LAW, enforced at the call site:** `anim` takes a **gesture name** resolved
> against *that unit's own model*, and a name the model doesn't own is a lint ERROR listing
> what it does own. This matters because **field rigs are not battle rigs**: a field monster
> like `GEO_MON_F0_MUU` owns only locomotion plus `jump`, and `GEO_MON_F0_FFG` adds
> `howl_*`/`smell_*` — there is no attack or death clip to borrow. A raw clip id bypasses
> the lookup.
>
> **⚠ THE CROSS-FORM CLIP TRAP (proven in-game):** resolution is **same-form only**
> (`catalog.own_form_gestures`), *not* the `(group, token)` join `animations_for_model`
> uses. **A different FORM is a different SKELETON.** The CSO token's `attack_cid_*` clips
> exist only in the **F3** form; playing one on a `GEO_NPC_F1_CSO` rig twists the model
> upside-down in-game. A cross-form name is refused with the offending clip named. The
> practical consequence is worth internalizing: within one token family, *different forms
> own wildly different gesture sets* — `GEO_NPC_F3_CSO` owns the attacks and `hiza_*`,
> `GEO_NPC_F0_CSO` owns `hiza_*` but no attack, `GEO_NPC_F1_CSO` owns neither, and
> `GEO_NPC_F4_CSO` owns almost nothing. Author per rig, and expect some units to have no
> honest clip at all.

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
  behavior ends (a stalker that needs a breather once you escape). **The hysteresis law:** a
  sticky decorator's condition is both the *trigger* and the *keep* — the engagement ends the
  first tick the condition fails. A tight `near` (say 280 with a 170 chase standoff) reads the
  player's first step back as "escaped" and a `once` latches almost instantly; give the keep
  real room (hundreds of units past the standoff) so disengaging means genuinely leaving.
- **`once` / `cooldown` over a one-shot (`announce`/`sfx`/`flash`/`stop_timer`) are EVENTS,
  not engagements**: the branch fires and *releases immediately* (via the same edge-latched
  request lane battles use, so another body holding the dispatch level can't eat it). For
  `once` this matters because announce conditions are usually **monotonic** — a kill tally, a
  spent wave counter — and a sticky `once` over a condition that never goes false again would
  hold the selection forever, **starving every branch below it** (the BTTABLE round-2 defect:
  the win line, once fired, silently swallowed the wave-three line). For `cooldown` the trap
  is worse — a **mutual deadlock**: selecting a one-shot *halts the walker* (the duty walk is
  fed the unit's own position), so two neighbours greeting each other on `near` conds would
  park inside each other's radius with no way for either condition to ever fail — both
  statues, selection held forever (the hangout greet latch). The event form fires the line,
  **arms the timer at delivery**, and hands selection straight back to the fallback — the
  pair parts, wanders, and greets again when the timer allows.

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
>
> **`behavior lint` checks this.** It warns when two or more `once` branches on one unit
> share a gate that can stop holding, names the offending condition, and states the fix.
> Sticky by construction (and so exempt): `flag`/`not_flag`/`any_flag` when nothing
> `clear_flags`es them, `time_below` (remaining time only falls), `hp_le` (hp only falls —
> swings gate on hp > 0), and `counter_ge` on a counter **no `[[behavior.scan]]` feeds** —
> a scan headcount rises *and* falls, while a schedule or kill tally only rises. That
> distinction matters: it is the difference between `counter_ge` being a safe gate and a
> silently starving one. `[siege]`'s own alarm chain is generated in the latched shape
> because this lint caught it riding a draining `any_near`.

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
a per-tick klaxon). `[siege]` exposes the win lane directly as `win_sfx = <id>` and the
loss lane as `loss_sfx = <id>`.

**`sustain = <frames>`** holds the unit's dispatch level for N frames after the play.
The event-once lane guarantees *order*, not *duration* — a cue followed by a queued
one-shot (a `battle`, an `announce`) otherwise gets exactly one ~33ms frame of air before
the next dispatch takes the audio (the loss-sting round-1 playtest). Sustain is how a cue
buys its beat: the queued request fires the moment the sustain releases.

`announce` takes the same pair: **`delay`** holds the level *silently before* the window
opens — the STAGED-TEXT primitive (a chain of once-announces on one monotonic flag, each
delayed by the previous line's read time, pages like a cutscene) — and **`sustain`** holds
*after* the open, for a line that must be read before a queued `battle` takes the screen.
`[siege]` stages its ending texts this way when `text_win`/`text_rout`/`text_loss` are
lists (paged at `text_pace`).

### `stop_timer` — freeze the countdown

`do = { stop_timer = true }` emits `RunTimer(0)`: the clock stops where it stands and
stays on screen. Needs field-level `timer` (lint refuses it otherwise).

> **THE CLOCK-COUPLED BATTLE LAW (REDOUBT rung-D playtest, byte-proven):**
> `B_SYSVAR[17]` **is** `TimerUI.Time`, and real battle AI reads it. The Festival of the
> Hunt scenes — id 35 and the whole `LB_E080x` family, exactly what a Lindblum-plaza fork
> borrows for a "donor-native" fight — run `B_SYSVAR[17] B_NOT → RunBattleCode` and
> **terminate themselves the instant the countdown reads 0** (that's the Hunt's "time's
> up" rule living inside the battle, not the field). So a timed minigame whose ending
> plays theater before firing a `battle` must **stop its clock first**: the sting and the
> staged lines take seconds, and a late loss otherwise lets the clock reach 0:00 before
> the battle fires — the fight then dies the moment combat starts, with nothing wrong in
> your script at all. `[siege]` freezes the clock at the top of its loss lane and on the
> rout for exactly this reason.
>
> **`behavior lint` now checks this for you.** When a timed field fires a `battle`, the
> linter reads that scene's own AI from your install and warns if it reads `B_SYSVAR[17]`.
> It is a *warning*, not an error — the same design is correct once the clock is stopped —
> and it goes quiet as soon as the behavior uses `stop_timer` anywhere (so `[siege]` is
> quiet by construction). If the scene can't be read (no install), the check says nothing
> rather than pretending the scene is safe. Inspect any scene yourself with
> `ff9mapkit battle-ai <scene>` and look for `B_SYSVAR[17]`.

### `flash` — a screen flash

```toml
[[behavior.unit.branch]]
when = [{ flag = "won" }]
do = { flash = [255, 255, 255] }   # wash to this colour, hold a beat, release
once = "winflash"                  # + optional pause = <frames> (default 20;
                                   #   the option is `pause` — `hold` is a verb)
```

One screen wash — stock's ADD-channel `FadeFilter` flash idiom (field 682's exact pair,
the most common ADD pattern across all 817 field exports): `CalculateScreenPosition
(player)` + mode-0 out to the colour over 24 frames + `Wait(25)` (stock's out+1), a held
beat at the colour (`pause` frames), then the mode-1 release to black over 16.

> **THE FADE-CHANNEL LESSON (REDOUBT round 2):** `FadeFilter`'s mode is a channel bit —
> `mode & 2` selects the SUB filter (screen − colour), else ADD (screen + colour). SUB
> toward *white* is therefore the stock **warp fade to BLACK** (modes 6/7 — what gateways
> and ladders emit), and a "flash" built on it reads as a field transition. A true colour
> wash lives on the ADD channel (modes 0/1). The engine ignores bit 0; stock uses it to
> mark the release half of a pair.

Same two stances as `sfx`: once-wrapped = event-Once fire-and-release (the win-wash
lane); bare = fires per dispatch. The body holds the unit's dispatch level for
~out+hold+release frames — queued one-shots (a pending purse, an announce) fire the
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

**The clock never leaves the field.** FF9's countdown is deliberately cross-field (the
Hunt's clock follows you around Lindblum): arming it sets save-persisted engine state
that every later map re-displays until something explicitly turns it off. So on a
`timer` field the build compiles the turn-off (`RunTimer(0)` + `ShowTimer(0)`) into
**every exit it emits** — gateways (including `to = "worldmap"` and `ate = true`
warp-ins), `[[choice]]` `warp`/`worldmap` rows, `[ate]` menu warps, a navigable
ladder's `top_action = "field"`/`"worldmap"`, and a platform's `warp_to` — so walking
out mid-game can't carry the clock onto the world map or into other fields (or into a
save made there). Battles are exempt on purpose: real battle AI reads the clock
(`B_SYSVAR[17]`), and an after-battle return re-enters this same field.

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
  (`id = N` overrides — anywhere but the reserved band 6000000..7999999; the ids are
  save-global, which the re-seed makes harmless). The one exception is a
  **persistent table** (`persist = true`, below), which is deliberately NOT re-seeded.
- **Reading**: `counter_ge` / `counter_le` / `counter_eq = ["wave", 2]` gate branches
  on a counter; `table_ge` / `table_le` / `table_eq = ["sched", index, n]` compare a
  table cell — and `index` may be a **counter name**, which is a genuine
  runtime-computed lookup (`sched[wave]`), the thing plain `.eb` variables can never do.
- **Writing**: `die = "kills"` bumps that counter exactly once (the death body runs
  once); the schedule clock advances its own counter; and the **adjust/drift lane**
  below is the general clamped write.
- **The clock stops itself**: when `wave` walks off the table's end, the read fails
  soft to 0 and `timer < 0` never holds — no latch flag, the data is the terminator.

### Persistent tables — state that survives the save

An ordinary table is re-seeded every time its field is entered. A **persistent** table is
not: what play writes into it survives field entry, `~ → Reload`, battles, and save →
quit → relaunch → load. It is the kit's first author-owned durable structure — counts, ledgers, "how many
times".

```toml
[behavior]
public_flags = ["arrived"]           # raised by a [[choice]] / gateway / event elsewhere

[[behavior.table]]
name = "mymod_visits"                # prefer a mod-prefixed name: the identity is save-global
id = 6412345                         # REQUIRED, 6000000..6999999 -- pick YOUR OWN unused id;
persist = true                       # every mod that copies this one shares one saved table
values = [0, 0, 0]                   # the SEED -- what a fresh game (or a lost save) starts from

[[behavior.unit]]
npc = "innkeeper"
  [[behavior.unit.branch]]
  when = [{ flag = "arrived" }]
  adjust = { table = "mymod_visits", index = 0, by = 1, clamp = [0, 9999] }
  clear_flags = ["arrived"]
  do = { hold_post = true }
  [[behavior.unit.branch]]
  do = { hold_post = true }
```

- **How it works.** Each persistent table T owns a one-cell *guard* vector at T + 1000000
  holding a check word (a hash of the table's name and length). At `Main_Init` the table is
  seeded **only when it is stale** — the guard does not hold its check word, or its size is
  not its length — and the check word is written last. A matching table is left exactly as
  the save left it.
- **What re-seeds it** (every case lands on the declared values, today's ordinary behaviour —
  it degrades, never breaks): a New Game; a save whose **Memoria extra file** is lost or
  rejected (vectors ride only that file — in-game proven, `studies/persistent-tables/`); the
  `~` Flags "reset all" (it clears every vector); a **rename** or a **length change**; a
  different table claiming the same id.
- **What does not.** Editing the seed *values* reaches new games only — existing saves keep
  their cells. To force every player's copy to re-seed after a change of *meaning* at the same
  length (a reordered or retyped cell), give the table a new `id`.
- **The id is the save identity** — like a `[[flag]]` index. Every field that declares the
  same id shares one saved table, so declare it **identically** (name, length) everywhere;
  `lint-campaign` refuses campaign members that disagree, and `lint-journey` does the same
  across the campaigns of one journey (they play into one save). Two tables that differ in
  name or length on one id re-seed each other forever: data is lost, never misread — but two
  with the SAME name and length on one id are one table, whatever their authors meant. Nothing
  is auto-allocated in the band, and an ordinary table may not name an id inside
  6000000..7999999.
- **Values** stay within ±1000000 (a saved cell outlives the deploy that seeded it, and every
  later `adjust` computes `cell + by` on it).
- **Writes reach disk at the next save** — the field-entry autosave, or a save point.
- **A counter-indexed write is fenced.** The engine *appends* a cell when a write lands at
  exactly `index == length` (see the adjust lane below); on a persistent table that write is
  skipped, so the table can never grow past its length and trip its own guard.
- **Written by a battle.** A minted battle's `[scene.ledger]` names the field that declares the table
  (`declared_in`) and writes its cells from the enemy AI — who fell, to whom, how many hits
  ([BATTLE_DESIGN.md § (b′)](BATTLE_DESIGN.md)). Its writes are gated on the table being live, so a fight
  before any declaring field seeded the table writes nothing (its `flag` rows still land): declare the
  table in the field that starts the fight. Read it here with `table_eq`/`table_ge`, and consume an
  "outcome" cell with a clamped `adjust` so it is narrated once. A text row indexed by a cell should be
  seeded with an in-range "nobody yet" value, not −1 (a `[TEXT=]` clamp maps negatives to row 0).
- **Dev loop.** `~ → Reload` no longer resets a persistent table (that is the point); `~`
  Flags "reset all" does. `~` Restore rolls back story flags only, not tables. Co-op does not
  mirror vectors between machines.

### Roll streams — seeded randomness you can predict

Every random thing a field did before — a stock `wander`'s targets — draws from the engine's shared
RNG: never seeded, never saved, a reload re-rolls it and nothing can predict it. A **roll stream** is a
seeded generator held in one table cell: deterministic, optionally saved, and **predictable offline** —
the build prints the exact numbers the game will draw.

```toml
[behavior]
public_flags = ["ask"]               # raised when the player consults the teller: a [[choice]] row
counters = ["omen"]                  # or an [[event]] trigger = "action" (the build prints its bit)

[[behavior.stream]]
name = "mymod_fate"                  # prefer a mod-prefixed name when persist = true
seed = 7                             # 1..2147483647 -- hashed with the name to the start state
persist = true                       # optional: the save keeps the state -- a reload cannot re-roll
id = 6412346                         # REQUIRED with persist: 6000000..6999999, YOUR OWN unused id

[[behavior.unit]]
npc = "teller"
  [[behavior.unit.branch]]
  when = [{ flag = "ask" }]          # THE EDGE IDIOM: a public flag raised from outside...
  roll = { stream = "mymod_fate", counter = "omen", range = [1, 6] }
  clear_flags = ["ask"]              # ...consumed by the branch that draws
  do = { hold_post = true }
  [[behavior.unit.branch]]
  do = { hold_post = true }

[[behavior.hud]]
window = 6
values = ["omen"]
digits = [1]
text = "[MPOS=10,48]OMEN [NUMB=0]"
```

- **What a draw does.** Each time the branch runs, the stream advances once (`S ← 236·S mod 65537`,
  full period: every state 1..65536 once) and `lo + S % n` lands in the counter (`n = hi − lo + 1`,
  2..256; bias at most 0.4%, none for a power of two). Test the result like any counter —
  `counter_eq = ["omen", 6]`. Several branches may draw from one stream; they share its sequence.
- **The edge idiom is required.** A selected branch executes every tick, so a roll on an ordinary
  branch would draw about 30 times a second. The build refuses a roll unless its branch's `when`
  requires a public flag that the same branch clears and nothing else raises (`raise_flags`, an
  alternator) or clears. Raise the flag from outside: a `[[choice]]` row, an `[[event]]` with
  `trigger = "action"`. Anything that writes the flag every frame is refused: a walk tread with
  `once = false` (it re-fires while the player stands in it), a tread whose once-latch `flag` IS the
  roll's flag (the roll's clear re-arms it), and any `[[coop]]` gate that writes it (a gate is polled
  every frame). A `roll` inside `when` is refused outright — a condition is evaluated every tick it is
  reached, so it would draw per evaluation — and so is a `when` that also negates the roll's flag (it
  can never be selected).
- **Ephemeral or persistent.** Without `persist` the stream re-seeds at every field entry (`~ → Reload`
  and Continue too), so the same visit replays the same draws: fixed puzzles, reproducible encounters,
  a deterministic test. With `persist = true` it is guarded exactly like a persistent table (same id
  band, same rules above), so the state survives the save and **a reload cannot re-roll**: load a save
  and the next draws are the ones that were coming anyway. A battle return keeps both kinds. In-game
  proven by the harness ([`studies/roll-stream/`](../../studies/roll-stream/PLAN.md) rung 1).
- **The oracle.** The build prints each stream's start state and first states —
  `mymod_fate (PERSISTENT vector 6412346, …) x0 … -> …` — and `ff9mapkit behavior compile` lists the
  first eight with the roll each draw site makes from them (a stream shared by several sites hands each
  raise the next state, whichever site it was). The seed is hashed with the stream's name, so two
  streams on one seed are unrelated. Editing a persistent stream's `seed` reaches new games only.
- **A seeded wander.** `do = { wander = [x, z], radius = r, seed = N }` takes its targets from a
  private stream instead of the engine RNG: the unit walks the same sequence of targets after every
  entry, and the build prints the first few. A seeded wander must be its unit's only wander.
- **See the state.** A HUD value `"stream:<name>"` shows the raw state (read-only — it never
  advances the stream); give it `digits = 5`.
- **Limits.** v1 ticker only (not on class rows or with `brains = true`); every declared stream must
  be drawn by some `roll`; no roll into a scan headcount or the schedule counter; streams, tables and
  counters share one namespace (a scan's `flags` table too); a wander box must stay inside ±32767 (the
  target slots are Int16).

## Adjust and drift — the numeric-write lane

A life-sim meter, a relationship score, a resource pool: state that decays, refills,
and is read back by the same trees. Two surfaces, one write shape:

```toml
[behavior]
counters = ["hunger", "cur_obj"]

[[behavior.table]]
name = "need"
values = [100, 100, 100, 100, 100]

[[behavior.drift]]                   # THE METABOLISM: a field-level clamped write
counter = "hunger"                   # every N frames, in the ticker's clock segment —
by = -1                              # independent of what any tree selects (decay must
clamp = [0, 100]                     # tick while the Sim walks, cooks, or sleeps)
every = 90                           # REQUIRED here, 1..30000 (an Int16 timer; the
                                     # first write lands one full period in)
# flag = "daytime"                   # optional gate: skips the WRITE, not the cadence.
                                     # Must name a flag something else raises (an
                                     # alternator, a public flag, a raise_flags) —
                                     # a never-raised gate REFUSES at build.

  [[behavior.unit.branch]]           # THE USE-LOOP: adjust rides a branch like
  when = [{ counter_le = ["hunger", 40] }]         # raise_flags — a clamped write
  do = { walk_to = "stove" }                       # WHILE this branch is selected
  adjust = { counter = "hunger", by = 3, clamp = [0, 100], every = 15 }
```

- **`clamp = [lo, hi]` is mandatory.** An unclamped meter walks off its range and
  every gate downstream reads garbage — and the 26-bit CalcStack does not truncate
  on overflow, it **wraps silently mod 2^26** (a wrong value, never an error — measured
  in-game, `studies/roll-stream/` rung 0). All of
  `by`/`lo`/`hi` (and every seed value of an adjusted table) are fenced to ±10^6.
- **Targets**: `counter = "name"`, or `table = "name"` + `index =` an int
  (compile-time bounds-checked) or a **counter name** — the computed-index WRITE,
  the same in-game-proven composition the scan loop rides. Keep a runtime index in
  range; an off-end write is silently lost (the engine lane's soft-fail family) —
  EXCEPT exactly `index == length`, where the engine APPENDS a cell (`EBin.cs:1926`).
  Persistent tables fence that write; ordinary tables do not (the next entry re-seeds).
- **Rates**: a branch `adjust` fires every selected tick by default; `every = 1..255`
  rides a byte timer (central clock under v1, a Seq-private Instance var under
  brains — per member for free on a class row). A drift's `every` is 1..30000.
- **Why decay is field-level**: the selector fires ONE branch per unit per tick
  (the draining-condition law), so five needs decaying as branches would compete
  for selection. Drift rows live with the clocks — all of them fire on their own
  cadence, whatever the trees are doing.
- `adjust` may be one row or a list; `engage` branches refuse it (the two-phase
  subtree owns its selection blocks — use a plain branch or a drift row).

The wave shape becomes: units gate their march branches on `counter_ge = ["wave", 1]`
(wave 2 on `["wave", 2]`, …), the herald announces on `counter_eq`, and a win condition
reads the kill tally with `counter_ge = ["kills", N]`. Bench: field 30415
(`studies/behavior-trees/bttable_bench.py`) — the first in-game consumer of computed
array indexing anywhere.

## Scans — the vector loop

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

## Groups and `engage` — the group loop

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
digits = [5, 2, 2, 2]                            # per-slot width reserve (1..5 reachable)
text = "[MPOS=8,8]GIL [NUMB=0]  TROOPS [NUMB=1]  RAIDERS [NUMB=2]  DEPOT [NUMB=3]"
```

A **value source** is a counter name, `"gil"` (the live purse), `"timer"` (the
countdown HUD's remaining seconds), `"hp:<unit>"` (a unit's hit points — the
roster cell for a group member), `"item:<item>"` (the live held count of an
item, name or id — watch contracts tick down as an item pool converts them), or
`"stream:<name>"` (a [roll stream](#roll-streams--seeded-randomness-you-can-predict)'s
raw state, read-only), or `"floor:<who>"` (the player's or a unit's [walkmesh
floor](#floors--on_floor--same_floor--other_floor), `-1` = unknown; not in a `[TEXT=]` slot).
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
- **`digits` reserves the width** (default 2, accepted 1..7, **reachable 1..5**):
  `AutomaticSize` bakes a dialog's width ONCE at open from the text as it
  renders THEN, and a variable change never re-sizes it — so a strip opened
  showing `0` clips when a counter reaches `11`. The open pass feeds every slot
  `10^digits - 1` before opening, then the real values land the next tick. Size
  `digits` to the widest value a slot will ever show. ⚠ That sentinel rides
  `SetTextVariable`'s **u16** value operand, so it saturates at 65535 — five
  characters. `6` and `7` are still accepted (existing fields keep building) but
  behave exactly as `5`, and `behavior lint` says so.

Authoring notes: place with `[MPOS=x,y]` — the PSX-ish 320×224 UI grid (stock
pins its save menu at `20,16`), and **the countdown timer owns the top-left
corner**, so a strip belongs below it (`10,48` clears it) or elsewhere on
screen. The window auto-sizes to its text, so keep labels short — a long strip
wraps to a second line (`[WDTH]` is a no-op in this engine). Combine with
`alive_only` scans for live team headcounts.

Win-condition note: two separate award branches each carry their own
once-latch, so "pay on rout" plus "pay at the final whistle" pays TWICE. Model endings as **detect-then-pay** — each ending
branch only announces and raises a shared `won` flag (gated on
`not_flag = "won"`, so whichever lands first closes the other out), with ONE
award branch gated on `flag = "won"`. ~180B of ticker + one window slot per strip; static values cost
nothing.

## Limits

- **Size**: assembled bodies have NO practical jump ceiling (the label assembler relaxes
  long jumps through fall-through-safe islands automatically, and same-target long jumps
  share islands), but the `.eb` **file** is u16-addressed — roughly **64KB total**,
  engine-fixed — and the entry table caps at **255 slots**. On a donor fork that leaves
  ~50-55KB for all compiled behavior (ticker + every dispatch body); each unit×target
  pair branch costs ~135B of ticker plus ~90B of body, so pair-target scope is the knob.
  A third budget binds at swarm scale: the blackboard scratch band is **114 bytes** of
  `gEventGlobal` by default (bytes 1876–1989, the campaign-compatible `"safe"` band) —
  `byte_band = "wide"` opens the historical **770 bytes** (1220–1989, capped flush below
  the reserved heap top: the nameplate explored words / qte scratch / co-op cells /
  choice mask), which overlaps campaign per-member flag windows and is standalone-only.
  Cost intuition: ~14B per unit + ~1B per swing timer (`flags.py` is the authority).
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
