# Behavior Trees on the .eb VM — "the .eb programming language" (study)

**Goal:** a kit capability that COMPILES designer-authored behavior trees into pure `.eb`
bytecode — patrol routes, engagement logic, flee/regroup, guard posts — so complex actor
AI becomes ordinary mod content: **zero DLL, runs on stock Memoria**, deployable and
hot-reloadable like any field. The owner's framing (2026-07-24): this fills the standing
soft goal of an "`.eb` programming language" as part of the kit — an authoring stack the
CLI/GUI can eventually surface directly.

**Origin:** spun out of the fort-condor study (rungs 0-3, all in one day, 2026-07-24 —
`studies/fort-condor/PLAN.md` on branch `claude/ffix-fort-condor-rts-ce9e0b`, and the
project memory [[project-ff9-fort-condor-rts]], which carries the laws referenced below).
The skirmish's REFEREE ARCHITECTURE is the hand-rolled prototype of exactly this system;
this study generalizes it and is DECOUPLED from Fort Condor — fort-condor keeps its own
bench (field 30400) and hand-rolled referee, and may migrate onto the compiler at its
rung 4+, but neither study blocks the other.

## Why this is de-risked (the receipts table)

Every mechanism a BT runtime needs has an in-game-proven counterpart from the
fort-condor benches (all proven 2026-07-24, field 30400):

| BT concept | .eb mechanism | proven |
|---|---|---|
| tick loop | `Wait(1)` looping code entry | the referee/poller; 40 units of per-frame eval = zero felt cost |
| condition leaf | `0x05` expr statement + jump gate | the whole referee |
| Sequence / Selector | jump-chained condition blocks | the `asm()` label assembler's output |
| action leaf | BLOCKING body function at REQ level 4 | sync-walk marches, chases, swing loops |
| Running / latching | per-unit state byte + dispatch guard | `att_state`/`rec_state` |
| completion → resume | the level-stack preempt-and-resume | the same engine path that resumes an NPC's stroll after a talk |
| abort | COOPERATIVE — body loops poll exit conditions | the fight fns' HP gates |
| blackboard | GLOB band (shared) + Instance vars (unit-private) | GLOB proven; Instance = untapped headroom (255 words/entry) |
| perception | the mirror service (gated obj() reads → GLOB Int16) | alive/placed-gated mirrors |
| decorators (cooldown/once) | timer bytes / once-flags | the swing tick, the breach guard |
| live debugging | a per-unit "current node id" trace byte | readable in the ~ Flags panel (convention, to build) |

## v1 architecture (owner-ratified): THE CENTRAL TICKER

- **One seated brain entry** (a code entry, `Wait(1)` loop) ticks every unit's compiled
  tree per frame. The proven shape; per-unit brains are a LATER variant (see probes).
- **Bodies** = blocking action functions ADDED to unit entries (`eb.edit.add_function`,
  the tag-15+ family), dispatched `RunScriptAsync(level 4)`; the death/interrupt class
  at level 5. Units themselves only ever run smooth blocked walks / blocking primitives.
- **Blackboard allocator:** unit-private state → `Instance` vars (free, per-entry);
  shared/cross-unit state → the GLOB safe band (bytes ≥1089; budget ~950 bytes — the
  fort-condor map used ~120 for 10 units). Allocation is COMPILED, never hand-assigned.
- **Perception service:** compiled from the declared unit roster — alive/placed-gated
  position mirrors (the dead-uid firewall), Chebyshev boxes (Int24-safe), optional
  unrolled nearest-of-N.
- **Cancellation:** cooperative — the compiler bakes each action's abort conditions into
  the body loop's every iteration (the only kind of interruption the VM offers).

## THE LAWS AS COMPILER INVARIANTS (the core value proposition)

Every fort-condor playtest failure was a hand-authoring error the compiler makes
structurally impossible — "a law in a docstring is a wish" (the GUI study's lesson); a
law in a compiler is a guarantee:

1. **The player-ref eval law** → every `obj()`/`B_PTR`/`B_DISTANCEA` emitted only behind
   a structural alive/placed gate (RPN has no short-circuit — separate stmt + jump).
2. **The sync-walk law** → only the brain/body split is expressible; no bare-Walk
   jitter, no ticker-freezing blocked walk inside a brain.
3. **The orbit law** → action templates carry snap turns (255) for pursuit, stock speeds
   for scenic walks.
4. **Poll cadence** → tick loops are always `Wait(1)`; cooldowns are decorators, never
   loop-bottom waits (the eaten-button lesson).
5. **Object-init gate / TREADQUAD / Int24** → enforced by template shape (no
   early-return inits, no always-inside region pollers, no squared distances).

## The layer stack (the "language")

- **L0 — exists today:** `eb/exprasm.py` (expression text → bytes, self-verifying), the
  `asm()` label assembler (to be promoted out of the fort-condor study script),
  `eb/edit.py` (add_function / seat_entry / activate), `eblint`.
- **L1 — this study:** `ff9mapkit/content/behavior.py` — node classes (Selector,
  Sequence, Cond, Action; decorators Cooldown/Once/Invert), the action library
  (walk_to, chase, hold_post, swing_at, flee_to, die, announce, set_flag, wander),
  the blackboard allocator, the perception-service generator, the ticker compiler.
- **L2 — authoring surfaces, in order:** Python DSL (studies + power users) → a
  declarative `[[behavior]]` TOML block (the kit's idiom) → CLI verbs
  (`behavior compile` / `behavior lint` / `behavior view` = compile+disasm round-trip) →
  a Workspace GUI section (tree editor + the live blackboard/node-trace watch; built
  per the GUI study's call-site law, and not before the CLI exists).

Deliberately DEFERRED: `Parallel` composites (the level stack gives "one body + the
brain", which covers the real move-and-watch cases); per-unit brains (needs the probes);
runtime tree switching beyond blackboard-driven branches.

## Rung ladder

- **Rung 0 — ★ DONE (2026-07-24, offline): DESIGN + THE GOLDEN COMPILE** → `RUNG0.md`.
  `eb/labelasm.py` (the promoted assembler) + `content/behavior.py` (all v1 nodes,
  feed/dispatch actions, mirror-safe perception helpers, the blackboard allocator, the
  ticker compiler) + 12 tests (instruction-walk verification of every body, determinism,
  the law negatives); full suite 4691 green. Locked en route: the SELECTED/RUNNING
  protocol, the player STAGED-LATCH, the Instance-var correction (ticker-visible state
  must be GLOB), reactive-only v1 semantics, the static-fallback lint. `install()`
  (into a host .eb) deliberately moved to rung 1's head.
- **Rung 1 — BUILT + DEPLOYED (2026-07-24), ⚠ playtest pending: THE FIRST TREES
  IN-GAME.** `bt_bench.py` → field **30410** ("BTREE", a fresh 559 native fork), FIVE
  compiled units, zero hand-written bytecode: the patroller (ring patrol → notice →
  chase → resume), the AUTONOMOUS DUEL (veteran hp6 holds vs Fang hp4 patrolling into
  contact — mutual SwingAt, Die, the survivor resumes post), the greeter (STICKY Once —
  chases while near, latches forever the first time you escape) and the stalker (STICKY
  Cooldown 150 — re-engages only ~2.5s after you escape). En route, rung 1's design
  fix: reactive re-selection made select-time-latching decorators fire ONE tick —
  Once/Cooldown are now STICKY (engage on select; the gate bypassed while the child's
  own conditions hold; latch/timer starts at DISENGAGE), + `install()` shipped
  (seat/replace/add/prepend + the eblint baseline-diff gate, tested against real 559)
  and the decorator/reset flags joined the Main_Init reset. The compile report
  (blackboard map + action ids = the ~ Flags live trace) auto-saves to the bench dir.
  RELAUNCH → ~ → Warp → 30410; ~ Reload = the full reset. Revert:
  `tools/scroll_out/revert_deploy_30410.py`.
- **Rung 2 — BUILT + DEPLOYED (2026-07-24), ⚠ playtest pending: THE REGRESSION
  PROOF.** `btwar_bench.py` → field **30411** ("BTWAR"): the fort-condor skirmish
  re-expressed ENTIRELY as trees — 2 Fang attackers (hp 3/5) march a goal, 2 soldier
  defenders (hp 5/3) acquire/intercept/duel, lane A defender wins, lane B attacker
  breaches (a sticky-Once `Announce` of the herald's scraped txid), lever-armed via
  `public_flag` rows (+ variant 2: two MILITIA soldiers with MUTUAL combat — the
  fort-condor rung-3 one-sided-harass debt closed by trees for free; the beast dies
  before the gate, no breach). New compiler surface: `Announce` (show-once-idle-while-
  selected dispatch body), `any_flag`, `public_flag` (externally-set flags that join
  the Main_Init reset; gen/deploy-deterministic allocation). Review caught the
  regression-purity bug: attacker militia-duels must gate on the militia flag or the
  march stops to beat an idle pacifist. Verdict = identical staging/outcomes to
  fort-condor playtest 6 ⇒ the compiler subsumes the referee and fort-condor can
  migrate. **★ PLAYTEST PROVEN (2026-07-24): "both variants work exactly as
  described" — RUNG 2 CLOSED. THE COMPILER OFFICIALLY SUBSUMES THE HAND-ROLLED
  REFEREE**; fort-condor's migration gate is OPEN, and mutual N×M combat (the condor
  rung-3 debt) ships as a free property of trees.
- **Rung 3 — ★ PLAYTEST PROVEN (2026-07-24, 3 rounds): THE SHOWCASE.** Final verdict:
  "playtest good — the raid plays out as described now" — the full scene (shift-clock
  ring trades, the one-time cry + alarm, the two-lane march with the second wave, the
  panic bolt, mid-fight flees to the market, the captain's stand, the postwar reset)
  runs as designed on bench 30412.
  All three vocabulary gaps closed FIRST, each grounded in engine source before its
  template shipped (verbatim-first):
  * **`Flee(threat, points, avoid_r, speed)`** — the design fork resolved AWAY from
    RPN vector math: PRIORITY REFUGES (run to the first author-picked walkable point
    the threat is NOT within `avoid_r` of; all camped → the last). Targets always
    on-mesh, emission = box-test chain, and it reads as gameplay ("fall back to the
    keep; if it's overrun, the market").
  * **`Wander(center, radius, hold, speed)`** — the RNG question answered from the
    engine itself: **`B_SYSVAR[0]` = `Comn.random8()`** (EventEngine.GetSysvar case 0),
    already encodable by exprasm; offset = `(rand−128)×radius/128` (B_MULT/B_DIV
    exist; Int24-safe to radius 4000). Fresh target every `hold` ticks into a
    persistent wtx/wtz pair; off-mesh rolls self-heal (shove the edge until reroll).
  * **PER-ACTION `speed=`** (every feed) — grounded: the blocked walk calls
    `MoveToward_mixed_ex(actor, actor.speed, ...)` EVERY frame (MoveToward.cs:12),
    so a mid-walk `actor.speed` change applies instantly. Machinery: the duty head's
    MSPEED reads a per-unit speed GLOB (expression arg), and a straight-line level-4
    **SPEED-NUDGE body** (always the unit's last tag) applies changes MID-walk —
    dispatched only when running==0 AND a FEED is selected (never two REQs on one
    unit per tick, by construction).
  * Plus: **`fb.alternator(name, frames)`** (a shift-clock flag that flips every N
    ticks — Int16 timer + B_XOR flip, holds during warm-up, resets on Reload),
    **`Do(..., raise_flags=/clear_flags=)`** (the alarm mechanism — flag writes ride
    any action selection, auto-joining the Main_Init reset), **`fb.any_of(*conds)`**
    (OR-composition: each Cond pushes exactly one stack value, so RPN concatenation +
    B_OROR is structurally valid), and the **shared-Do dedupe** (the same action
    object in 2+ Do sites compiles to ONE dispatch body — the watcher pattern:
    one Announce fired from either notice branch). Re-compiling the same
    FieldBehavior is now idempotent (the reset registries all dedup).
  `btraid_bench.py` → field **30412** ("BTRAID", the 559 donor): THE RAID — 7 units:
  watchman (notices either bandit → ONE cry raises "alarm" → sprints for the keep),
  guard0/1 (opposite-phase patrol-shift rings via one alternator + Invert; alarm →
  rally/chase/duel at 65; hp≤1 → Flee 75 to keep-else-market), captain (keep boss:
  sticky-Once war cry drawn at 1000, double-damage duels), bandit0 hp4/bandit1 hp6
  (lever-armed march at 55, mutual duels, once-gloat at the keep), civilian (Wander
  30 around the market → alarm PANIC = Flee 80 past the player's spawn → ambles
  again postwar). 21 tests (+7 rung-3), full suite 4700 green; 1244 compiled
  instructions all jump-walked. RELAUNCH → ~ → Warp → 30412; ~ Reload resets.
  Revert: `tools/scroll_out/revert_deploy_30412.py`.
  **PLAYTEST ROUNDS 1-2 + THE LAYOUT-PROBE ROUND (2026-07-24):** round-1 "alarm at
  field entry" = the notice box saw the DORMANT CAMP (fix: raid-gate the notice,
  radius 450); round-2 "watchman spams the cry" = Announce re-dispatched on every
  box re-entry (fix: the sticky Once I'd promised but not written) — and "guards
  stuck in 1 of 2 places" = the outer ring's two legs crossed CONCAVE off-mesh
  notches, which point probes can't see. The new `laying-out-ff9-fields` skill +
  `tools/field_layout_probe.py` became the cure AND got improved from this field:
  **ROUTE markers** (`[[marker]] path=/closed=` — polylines drawn on both PNGs +
  walkability-SWEPT per leg, off-mesh spans in red with world coords) + scroll-aware
  OFF-CANVAS suppression; the sweep then caught THREE MORE broken lines I'd shipped
  blind (bandit march, panic run, watchman escape). Layout relaid from the probe's
  eyes: routeA = THE MONUMENT CIRCUIT (the field is a donut; 6 corners, west detour
  around the hole's waist bulge), THE TWO LANES (bandit1 west through the gatehouse,
  bandit0 the long east lane = a SECOND WAVE), watchman/guards fall back to the
  MARKET (every keep-bound flee line grazes the neck bay). Vocabulary grew again:
  **`March`** (walk waypoints, HOLD the last — Patrol that stops; replaces chained
  Once waypoint-latches), **`all_of`** (AND inside any_of), the shared-Do dedupe
  exercised for real (one cry from two notice branches). LAWS MINTED (now in the
  skill): walkers slide around CONVEX obstacles but WEDGE in concave notches;
  snap walk targets to ≥100u wall clearance (1u edge slivers pass naive on-mesh
  tests — the market sat on one); probe ROUTES, not just points. Bench lattice is
  clearance-filtered; all 7 routes sweep ON-MESH; suite 4712. **Round 3 ★ PROVEN**
  ("playtest good — the raid plays out as described now").
- **Rung 4 — ★ PLAYTEST PROVEN (2026-07-24, "parity check passed"): PRODUCTIZE.**
  The TOML-built 30412 plays identically to the rung-3 proof — the product surface
  reproduces the showcase exactly. THE LADDER IS COMPLETE (rungs 0-4 all ★).
  The `[behavior]` TOML surface (`content/behaviortoml.py`): `[[behavior.unit]]`
  binds to a named `[[npc]]`; PRIORITY-ordered `[[behavior.unit.branch]]` rows
  (`when` = verb-keyed condition dicts, `do` = one action verb + options,
  `once`/`cooldown`/`raise_flags`/`clear_flags`); field-level `warmup`/`tick`/
  `alternators`/`public_flags`. 13 condition verbs (incl. `any_near` = the watcher
  idiom and `any_active`) + 11 action verbs; unknown verbs/options/names are ERRORS
  (the laws-as-invariants posture extends to the surface). WIRED INTO BUILD:
  `collect_text` mints `announce` lines (12th txid channel; ~40 unpack sites
  repointed), `build_script`'s tail compiles + installs (npc_slots from the build's
  own injection map — no discovery; per-language builds are allocation-identical),
  `validate` refuses verbatim forks / cutscene-cast overlap / gated units. CLI:
  **`behavior compile|lint|view`** (report + public-flag indices / static checks +
  route-marker SWEEPS / full body disassembly). The sweep core deduped into
  **`scene/routes.py`** (the probe + lint share it verbatim). Docs: `docs/BEHAVIOR.md`
  + FORMAT.md `[behavior]` + the route-marker reference + FEATURES row + CHANGELOG.
  **THE PRODUCT-PATH PROOF:** `btraid_bench.py` rewritten — gen emits the ENTIRE
  rung-3 raid as `[behavior]` TOML (patrol/march verbs referencing the probe-swept
  route markers BY NAME; `announce_npc` reuses each speaker's dialogue; the lever's
  set_flag index computed from the deterministic allocation) and deploy is plain
  `deploy_field` — zero bench bytecode patching; the deployed `.eb`s verified (7
  units off standby onto duty walks + dispatch/nudge tags, the ticker seated).
  9 new tests (`test_behavior_toml.py` incl. a built-.eb e2e); suite **4721** green.
  The playtest = a PARITY check: the redeployed 30412 must play exactly like the
  rung-3 proof. GUI section deliberately deferred (the GUI study's call-site law).
- **POST-LADDER — POOLED UNITS (runtime activation): ★ IN-GAME PROVEN (2026-07-24,
  3 rounds — "all good now").** The fort-condor resume ladder's step 1, as compiler vocabulary:
  `pooled = true` / `pool = "name"` on a `[[behavior.unit]]` seats the NPC's entry
  DORMANT (new `inject_npc(boot_spawn=False)` — no InitObject call site, no reveal-flag
  hack), excludes it from the warm-up wake, and emits a per-pool ACTIVATION BLOCK in the
  ticker: request flag (allocated per pool, printed at build/compile — wire a
  `[[choice]]` row's `set_flag`) → first never-spawned unit → capture the player's
  press-time position as its post GLOBs → runtime `InitObject` → 2-frame settle →
  `MoveInstantEx` to the post (the rung-3 referee's in-game-proven byte shape VERBATIM,
  now emitted by the compiler; new `opcodes.move_instant_ex` 0xBF) → seed the unit's
  mirrors → `spawned`+`active`. New feed verb **`hold_post = true`** (valid fallback):
  hold MY placement post = the placement-defender idiom. v1 rules: one spawn per
  request, exhausted pool consumes silently, no respawn after death, ~ Reload refills.
  Allocation hygiene: a field with no pooled units compiles byte-identical (tested).
  8 new tests (activation instruction-walks, TOML negatives, the built-.eb e2e: pooled
  entry has NO boot InitObject, spawned exactly once by the ticker — also verified on
  the deployed bench bytes). Bench **30413** "BTPOOL" (`btpool_bench.py`, pure product
  path): a wandering/chasing Mu pest + 3 pooled soldiers + 3 quartermaster hire zones
  (spawn-side/west/north, Confirm-press action choices on the pool flag). ~ → Warp
  → 30413 (or New Game). Revert: `tools/scroll_out/revert_deploy_30413.py`.
  **ROUND 1 (2026-07-24): beats 1-3 ★ PROVEN** ("good" ×3 — dormant pool, hire at feet
  + hold, intercept/mutual-duel/resume-post). Beat 4's report ("worked a couple times,
  too many on the first spawn, then stopped — and it persists through relaunches/new
  games") decomposed into: (a) the action-trigger choice is a REUSABLE Confirm lever
  (each press = one hire; round 1's checklist wrongly said re-entry — the pool simply
  drained) and (b) **THE NEW-GAME STAGED-LATCH BUG (Memoria.log-proven, FIXED same
  day):** on the New-Game auto-warp entry, `B_SYSVAR[2]` (usercontrol — NOT existence)
  passes before uid 250 binds → the first run pass's `obj(250)` mirror NullRefs → the
  CalcStack desyncs → the whole behavior system dead for the session ("persists" =
  every re-entry was a New Game; nothing was ever save-persistent). THE FIX (the law
  made structural): `install()` inserts a `player.bound` flag-set right after every
  `DefinePlayerCharacter` (0x2C, the insert_in_function-blessed site); the latch =
  (bound AND usercontrol) OR latched; no 0x2C = install REFUSED. Flag allocation
  shifted +1 → bench re-gen re-wired the hire flag (8868→8869); 30413 redeployed.
  ⚠ Benches 30410-12 + 30400 still carry the old latch as deployed (Warp-entry safe;
  fix rides their next redeploy).
  **ROUND 3 (same day): THE ONE-CONFIRM-RECEIVER LESSON** — round 2's "hire popup
  only from certain positions": the QM's plain-dialogue talk arc (near+facing) and
  the action zone around him were TWO stacked Confirm receivers, and the talk EATS
  the press inside its arc. Never park a talky NPC inside an action zone — bind the
  menu to the TALK (`[[choice]] npc =`, talk → menu → branch). Zone choices deleted;
  the quartermaster's talk IS the hire menu.
  **★ ROUND-3 PLAYTEST: ALL BOXES PROVEN** ("all good now — hires work from anywhere,
  pest intercept still good, new game good, silent 4th, reload refill") — the pooled
  lane is CLOSED: dormant pool / spawn-at-feet + hold_post / intercept-duel-resume /
  the NEW-GAME entry (the staged-latch fix's regression box) / silent exhaustion /
  reload refill, all in-game.
- **POST-LADDER — STATIC-FEED AUTO-ROUTE (PATH A): ★ PLAYTEST PROVEN (2026-07-24,
  bench 30414: "the wedge clumsily rams into walls and walks into them until he
  slowly slides back to a navigable place, while the clever dodges walls" — the
  routed unit clean, and the naive control is the slide law live).** `route = "auto"` on `patrol`/`march` re-routes any leg the
  walkability sweep finds OFF-MESH through the cutscene builder's walkmesh A*
  (`pathfind.route_polyline` — the sweep is the jam oracle, so what's routed ==
  what lint reports) and splices the detours in at build time — the concave-notch
  wedge the rung-3 layout round could only diagnose is now fixed by the compiler.
  Design pins: OPT-IN (no key → the walkmesh is never resolved → byte-identical,
  tested); clear legs stay as authored; patrol routes its WRAP leg (it always
  cycles — the lint sweep is now verb-aware too, closing the old open-marker
  wrap-leg blind spot, and sweeps inline routes); obstacles = WALLS ONLY (units
  move — build-time character obstacles would be stale; engine collision slides
  convex contacts); the 8-point ceiling is a hard error naming field/unit/leg;
  `walk_to`/`hold`/`flee` are REFUSED with the reason (no build-time leg origin —
  that's path B, dynamic routing; spliced flee points would become extra refuges).
  New `build.behavior_walkmesh` (one resolver for build + lint); lint reports
  routed legs as `routed:` lines + hints `route = "auto"` on non-routed jams.
  10 tests (`test_behavior_autoroute.py`), suite 4901. En route: the new inline
  sweep found a REAL latent jam in 30412's civilian inline-flee refuge pair
  (refuge→refuge leg crosses the donut; lint-only, the proven playtest never fired
  that retarget), and the sweep's minwall oracle counts cross-floor SEAMS as walls
  (phantom 1-18u warnings; `distance_to_boundary` is seam-aware — fix task
  spawned). Bench **30414** "BTROUTE" (`btroute_bench.py`, pure product path): the
  A/B — two soldiers patrol THE SAME 2-point chord across the donut hole, `wedge`
  naive (jams, the disease live) vs `clever` route="auto" (an 8/8-point routed
  circuit, byte-verified in the deployed `.eb`). RELAUNCH → ~ → Warp → 30414.
  Revert: `tools/scroll_out/revert_deploy_30414.py`.
- **POST-LADDER — THE CLOCK + REAL BATTLES (fort-condor rung 4's vocabulary,
  2026-07-24): ★ IN-GAME PROVEN, 2 rounds — round 1 waves/win + THE ONE-TICK DISPATCH CLOBBER minted+fixed (the edge-latched breq request lane); round 2 the loss battle/one-shot/clean return ('Trick Sparrow, no re-swirl, no softlock').** Field-level `timer = <seconds>`
  (the Hunt's HUD start triplet in Main_Init — 0x69/0x8D/0x7D, the custom-id claim
  ★ proven long ago) + `time_below`/`time_above` conds (B_SYSVAR[17] remaining
  seconds — timed WAVE bands) + the `battle = <scene>` action: `Battle(0, scene)`
  verbatim from 559's tread battles, ONE-SHOT per field load BY CONSTRUCTION (a
  compiled latch gates the dispatch — a reactive tree re-selecting the branch after
  the battle returns cannot re-fire it; the naive Once-decorator route would have
  looped, sticky-engagement holds the branch selected forever on a dead gate) + the
  build auto-installing `content.reinit.add_reinit` (entry-0 tag-10) + the BGM
  resume whenever a behavior compiles a battle (the after-battle resume law as a
  build invariant). 6 new tests incl. the built-.eb tag-10 e2e. The proof bench =
  fort-condor 30400 "THE SIEGE" (its PLAN rung 4).
- **POST-LADDER — DATA TABLES (the 0xD3 dividend as vocabulary, 2026-07-24):
  ★ FULLY IN-GAME PROVEN over 3 rounds (bench 30415 "BTTABLE" = the FIRST
  IN-GAME RUN of `.eb` computed array indexing anywhere; round 3 "wave 3 is
  good" — every announce fires, the OOB terminator holds, no softlock).** Round 1 proved the clock/computed-index/kill
  path but the bench's own layout hid the tally beat (fang0's dormant post on a
  BALCONY — the lattice spanned all floors of the multi-floor plaza; + both
  approach chords measured 37-92% off-mesh, the arrival was blocked-walk
  sliding) → floor-filtered lattice (`Tri.floor_ndx`, spawn's floor) + the
  approaches as `march route="auto"` (+3/+2 spliced waypoints — the autoroute
  lane escorting the 0xD3 field). Round 2: every dialogue fires ("good") EXCEPT
  the wave-three line → **THE MONOTONIC-ONCE STARVATION** (a compiler defect,
  not a bench bug): sticky Once over a cond that never re-falsifies (a kill
  tally, a spent wave counter) holds the selection FOREVER and starves every
  branch below; reordering cannot fix two monotonic onces. **THE FIX — THE
  EVENT ONCE:** `Once` over an `Announce` compiles fire-and-release — selection
  edge-latches an `areq` flag, the ONE-SHOT REQUEST LANE (Battle's clobber
  machinery, now shared) fires when the level frees, the dispatch body sets the
  Once latch FIRST and returns with no idle loop (the async window persists on
  its own). Sticky is UNCHANGED for feeds; a bare announce keeps its spam
  guard; a shared once/bare Announce object is refused. 4 tests. **Round 3 ★
  ("wave 3 is good"): the starved line fires at its band with the win line
  already latched — THE EVENT ONCE is in-game proven and the lane is CLOSED.** `[[behavior.table]]` (named int
  arrays in `gScriptVector`, RE-SEEDED every field entry: size←0 then size←n —
  engine zero-fill — then non-zero cells only; auto ids from 1000, save-global
  aliasing harmless by the re-seed, stale save tails impossible by the truncate) +
  `counters = [...]` (runtime cells, one internal table) + conds
  `counter_ge/le/eq` and `table_ge/le/eq` (the table verbs' index may be a COUNTER
  NAME — a genuinely runtime-computed lookup; nested VECTOR reads compose, the
  engine keys sub-operands by CalcStack depth) + `die = "<counter>"` (bump-once:
  the death body runs exactly once) + `[[behavior.schedule]]` = **THE WAVE CLOCK**
  (`counter += 1` while the countdown HUD sits below `table[counter]` — one generic
  engine replacing N unrolled `time_below` bands, the schedule is DATA;
  self-terminating: the counter walking off the table's end reads 0 fail-soft and
  `timer < 0` never holds — the data IS the latch). The bench: dormant fangs woken
  per-wave by the clock (counter_ge gates), a MUTUAL guard duel feeding
  `die = "kills"`, the herald announcing every band + the tally + the terminator.
  9 new tests (seed shape / computed-index byte shapes / allocation determinism /
  negatives both surfaces). This is rung 5 of fort-condor's substrate: unit
  rosters, costs and wave compositions as ONE table edit.
- **POST-LADDER — THE COMPILED ROADMAP (PATH B, dynamic navigation): ★ FALSIFIED
  OFFLINE (2026-07-24, zero playtests spent).** Scripts + reproduction:
  `pathb/` (`roadmap.py` decomposition, `emit.py` real-byte emission, `census.py`,
  `worked_559.py`, `census.json`). **Recommendation: build NEITHER the roadmap nor
  the engine opcode.** The decomposition, the table compression and the routing
  QUALITY all work; what has no sound implementation is the *entry point* —
  resolving a live `(x,z)` to a region on the `.eb` expression stack.

  **1. Decomposition (works).** Connectivity comes from `BgiWalkmesh.tris[].nbr` —
  the engine's own seam-aware navmesh graph, never re-derived from geometry
  (`docs/WALKMESH_EDITING.md`'s law). Regions grow greedily + a merge pass under ONE
  contract: *a unit anywhere in region A must walk STRAIGHT to any of A's portal
  waypoints without leaving the mesh*, checked as sampled mutual visibility over the
  **occupiable** point set (the region eroded by the 48u controller radius — corner
  slivers a unit can never stand in constrain nothing). Regions never span floors.
  Portals = shared cross-region edges; waypoint = the widest one's midpoint.
  **Census (100 random real fields; all 674 `.bgi` extracted):** tris median 119 /
  p90 243 / max 463; regions **R p25 9, median 16, p75 26, p90 39, max 64**.

  **2. Cost (buildable, priced high).** Emitted through the SHIPPED emitters, so
  these are measured bytes: the unrolled next-hop table costs a flat **24.4 B per
  cell**. Field **559** (253 tris / 4 floors — the benches' own donut arena, p92 for
  size): R=49, 130 directed portals, 1986 routable ordered pairs.
  * naive chain 1986 cells ≈ 48 KB → **will not assemble**: `0x01` JMP carries a
    SIGNED 16-bit offset, and `.eb` entry offsets/sizes are u16 (65535 ceiling).
    6/100 census fields overflow outright; the p90 field emits 32,436 B.
  * **THE INTERVAL COMPRESSION (a real credit):** number regions by DFS and the
    per-source next-hop rows become piecewise constant — 1986 cells → **333
    intervals → 236 range tests → 8,140 B** (0.17× the raw cells). This alone
    brings essentially every field back inside the jump reach.
  * waypoint chain 5,330 B per-portal, **1,584 B** keyed on next-region only;
    membership 2,352 B (AABB rescan) / 2,499 B (stay-test) / 6,240 B (per-portal
    incremental). Best-case whole stack ≈ **11–12 KB per field**.
  * Scale: the ENTIRE rung-3 showcase (BTRAID, 7 units) compiles to 10,661 B
    (ticker 7,802 B); `EVT_SWARM.eb` (40 movers) is 37,569 B against the 65,535
    ceiling. So the roadmap roughly doubles a behavior-heavy field's `.eb`.
  * **The table can only ever be CODE, not data**: `expr_varSpec` (EBin.cs:464)
    reads a variable's array index from the INSTRUCTION STREAM, so
    `Global.Byte[base + r*R + s]` does not exist. (See the discovery in §5.)

  **3. Per-tick cost (not the blocker).** One pursuer served per tick (round-robin)
  + incremental region tracking = ≤ 2R compares + out-degree (559: 98 + 8, worst
  case). Comfortably inside a `Wait(1)` loop that already carries 40 movers.

  **4. Quality (not the blocker either).** Simulated against the kit's own A* over
  120 random pursuit chords on 559: length ratio **median 1.13×, p90 1.26×, max
  1.89×**, median 3 portal hops, 1 unroutable. Corridor-following reads fine.

  **5. THE FALSIFIER — membership has no sound expressible form.** The roadmap's
  first act each tick is "which region is this position in?", and:
  * Exact point-in-region = point-in-triangle = cross products. The CalcStack is
    **26-bit signed** (`(t0 << 6) >> 6`, EBin.cs:1683 — the project's "Int24"
    shorthand is conservative), so the worst-case delta product overflows on
    **244/674 real fields (36%)**; where it fits it still costs O(tris) tests.
  * The only overflow-safe primitive is the axis-aligned box — and AABB
    first-match membership **misclassifies 20.8%** of occupiable points on 559
    (9.2% of region AABB pairs overlap). A misroute is not cosmetic: it feeds a
    waypoint on the wrong side of a wall.
  * The escape hatch — incremental tracking by portal half-plane crossings — IS
    expressible, but it is dead reckoning: it needs a correct seed, it silently
    desyncs on any teleport (including `MoveInstantEx`, which the shipped
    **pooled-unit** vocabulary fires on *every spawn*), and it has no sound
    recovery test, because recovery needs exact membership.
  * Compounding: **25/100** census fields have floors that OVERLAP in XZ, and the
    ticker's position mirrors carry no floor id — so `(x,z)` is ambiguous there by
    construction.

  **6. THE MEASURED NEED IS SMALL.** Fraction of straight pursuit chords on 559
  (the field chosen *because* its concave hole minted the wedge law) that leave the
  walkmesh, by range: **0–600u 0.0%**, 600–900u 1.8%, 900–1200u 9.6%, 1200–1500u
  19.9%, 2400u+ 82.3%. The shipped vocabulary engages at `Chase` standoff **140**
  and the raid's notice radius **450** — i.e. the naive straight-line chase is
  clean at every range the trees actually pursue at. Dynamic jamming is a
  LONG-RANGE phenomenon, and the long-range approach leg is *static*, which
  **Path A already routes**.

  **7. THE ENGINE-OPCODE ALTERNATIVE — weighed, and caveat (a) is a BLOCKER, not
  an unknown.** The mechanism is real and generic: `MoveNPC()`
  (`FieldMapActorController.cs:875`) runs every frame for every non-player actor
  and drains `movePaths` into `moveTarget` — it is not mouse-specific. But the
  scripted walk (`MoveToward_mixed_ex`) writes `actorController.curPos += moveVec`
  **directly** and never touches `hasTarget`/`moveTarget`/`movePaths`: both lanes
  move `curPos` in the same frame, so they SUM. `PathTo(x,z)` therefore cannot be
  additive — the duty body's blocking `Walk` must be REPLACED by a poll, which is a
  restructure of the proven sync-walk core, and it costs:
  * **per-action `speed=` (a shipped, proven feature)** — `MoveNPC` moves at
    `this.speed`, hardcoded `30f` at construction (line 107) and refreshed only for
    the player (line 211);
  * **the walk animation** — the walk/idle auto-switch is inside
    `if (FF9StateSystem.Field.isDebug)` (line 367); in normal play animation comes
    from `PlayAnimationViaEventScript` (`originalActor.anim`), so a path-driven NPC
    slides in whatever pose the script last set unless the compiler drives the clip;
  * plus `HonoLateUpdate` clears `movePaths` after 30 still frames, and
    `FindPathReversed` uses `List<Int32>.Contains` inside its expansion loop
    (O(V·E)) with the only shipping call site running it TWICE plus
    `SmoothPathsByForce` — never exercised beyond a single mouse click.
  Caveat (b) stands as stated: it costs engine independence. **That is an OWNER
  decision** — but on the evidence above it would be paid for a capability §6 says
  is not currently needed, so this study does not ask for it.

  **8. THE DISCOVERY (the rung's real dividend): stock Memoria already gives `.eb`
  COMPUTED ARRAY INDEXING.** `flexible_varfunc` (expression token **`0xD3`**, then a
  u16 command + u8 argc, args popped off the CalcStack — EBin.cs:331/351) exposes
  **`VECTOR` (cmd 20) / `VECTOR_SIZE` (21) / `DICTIONARY` (22)**, backed by
  `FF9StateSystem.EventState.gScriptVector` — `List<Int32>` indexed by a
  **stack-supplied** value, save-persisted through `JsonParser`. Added upstream in
  **`91e94a66` (2023-09-23)**, verified an ANCESTOR of our pinned base `6b8bb2d5`
  ⇒ available on **stock Memoria at zero engine cost**, and `eb/exprasm.py` cannot
  emit it yet. This is the primitive every branch of this analysis kept colliding
  with (§2's "code, not data"): with vectors, tables become runtime data and
  loops-over-arrays become expressible — a compiler could BFS a next-hop table at
  `Main_Init` instead of unrolling it. It does NOT rescue this rung (§5 is a
  correctness wall, not a size wall), but it is a genuine capability find and the
  natural head of any future "real data structures in `.eb`" rung. Prove it on
  something far simpler than a roadmap first.

  **WHAT WAS DONE INSTEAD — THE PURSUIT SWEEP (★ BUILT 2026-07-24, offline, no
  runtime cost).** The Path-A cure applied to the Path-B symptom: `behavior lint`
  now sweeps the dynamic feeds as well. The insight is §6's — a chase has no
  authored line, but its branch's own `near` radius bounds a knowable FAMILY of
  lines, and the jam rate is a function of that radius. `scene.routes.sweep_pursuit`
  tests every pair of OCCUPIABLE positions inside the compiler's Chebyshev box
  (standoff pairs excluded, legs truncated at the standoff ring) and reports the
  blocked fraction + worst pairs as coordinates; `behaviortoml.pursuit_refs` reads
  the binding radius from the TIGHTEST `near`/`any_near` row naming the target
  (branch rows are ANDed), maps `near_point` to a source box, models `wander` as its
  own box at twice the radius, and flags a chase no row bounds as **UNGATED**.
  Warnings, never errors (a dynamic jam needs the quarry to stand on a bad spot).
  Calibration held across the four benches that carry a `[behavior]` table: silent on
  BTROUTE (patrol-only), **5.1%** on the raid's 900u guard chase, 3.4%/2.0% on the
  pool bench, and the swarm's 40 chases flagged UNGATED. (BTREE/BTWAR predate the TOML
  surface and have no table to lint.) Two FALSE-CLEAN bugs were caught by its own tests en route — sizing
  the sampling off an ungated radius instead of off the floor that exists (a ~4000u
  endpoint grid on a 1600u mesh), and picking endpoints by `gi % stride == 0`, a
  modulus on ABSOLUTE grid indices that can match no cell at all; both reported "0
  pairs tested" as CLEAN, the worst possible answer for a lint. Sources are now
  BUCKETED and every sizing decision is clamped to the occupiable extent; the leg
  grain is pinned at the collision radius and the sampling spacing is always printed
  (the rate is a floor, not a ceiling). 16 tests, suite 4923 green.
  ⚠ Noted, NOT touched (pre-existing, out of this scope): `autoroute_plan` takes
  **~44s** on the 60-unit swarm bench, which dominates both `behavior lint` and
  every deploy of that field — the pursuit sweep itself is ~0.2s.
- **Side probes (cheap, unblock the per-unit-brain variant later):** (a) shared-script
  context semantics — does `RunSharedScript` execute with the CALLER as gCur? (the
  Hunt's Entry17 poller hints yes → ONE generic brain shared by all units,
  Instance-var-parameterized); (b) self-REQ (an object dispatching its own higher-level
  function).

## THE THREE WALLS + V2 SCOPING (2026-07-25 — the stress/measurement pass)

The compiler grew its own instrument this pass — `CompiledBehavior.size_report()`,
a per-unit/per-branch **byte histogram** (zero-width `__seg` ticker markers +
exact body lengths; provably byte-inert). Run against the shipped round-3 CONDOR
build and a 40-unit offline swarm, it turned "the build feels big" into three
MEASURED walls, all binding at roughly the same scale:

| wall | limit | measured onset | nature |
|---|---|---|---|
| blackboard band | 820 bytes of `gEventGlobal` scratch (physical: `Byte[2048]` minus reserved) | ~40 units × 6 swing pairs (a 7th pair/unit exhausts; ~14B unit kit + ~1B per swing timer) | HARD, loud |
| ticker span | old: ±32767 jump reach; now RELAXED via islands | ~240 lean pair branches (~135B each) | SOFT since the island pass — first in-game crossing = the ISLES bench (30416) |
| the FILE | u16 entry table ≈ 64KB whole file | ~50-55KB of new bytes on the plaza donor; CONDOR round 3 ships 49.4KB | HARD, engine-fixed, loud since the strict guards |

**The histogram's verdict on WHERE the bytes go (CONDOR round 3, 49,383B new):**
126 `SwingAt` dispatch bodies × **108B = 13.6KB of byte-identical code** differing
only in target constants; pair TICKER branches ~122-135B each (~190B counter-gated);
shared infrastructure a rounding error (head+mirrors+clocks+pools+hireable = 2.1KB).
The roster cross-product IS the cost — v1 pays it three times (band bytes, ticker
bytes, body bytes) because per-pair logic is UNROLLED over per-unit state held in
`gEventGlobal` scratch.

Assembler hardening shipped alongside (the robustness half of the pass): island
REUSE (dense same-target long jumps repoint at an existing in-reach island instead
of minting one each — batched per fixpoint round, strictly-between so no cycles),
detection at the TRUE emit limits with placement at the safe-margin goal (kills
re-route churn in dense island clusters), an input-scaled convergence cap, the
255-entry table ceiling clamped at the boundary (chunked growth no longer refuses
a slot that fits), and 5 new stress tests (dense-same-target, 300-distinct-target,
boundary-at-255, histogram tiling, the 40-unit swarm).

### V2 candidates, ranked by leverage on the measured walls

1. **THE VECTOR SUBSTRATE (the group loop) — the headline. ★ RUNG 0 IN-GAME
   PROVEN (2026-07-25, "all eight lines fire true, no freeze"):**
   `[[behavior.scan]]` — the bounded in-ticker loop whose reads AND writes
   index vector cells by the live loop byte (the one composition BTTABLE
   didn't cover; count derived THROUGH a computed-index write-then-read round
   trip so faults break the number, never silently) — ran clean on THE
   PILGRIMAGE (30416, `vector_bench.py`; zero-relaunch redeploy over the ISLES
   slot). The abbot's whole 1/4/8 ladder landed true off the loop. Bench
   notes, no re-test needed: the arrival stagger was too tight (fast pilgrims
   had the long legs — the speed×distance products nearly cancel; future
   benches give SLOW units the LONG routes), and the visible camera drift on
   entry is the KNOWN bare-~-warp class (the one unfaded entry path left,
   [[project-ff9-field-entry-arrival]]) — not a fork or bench defect; a
   debug-menu fade-on-warp is a candidate engine-bundle polish item. The full
   substrate now follows: move per-unit state
   (hp, mirrors, active, current-target) out of `gEventGlobal` bytes into
   `gScriptVector` tables (hp[i], mx[i], mz[i]...), and compile per-FOE-GROUP
   logic as a bounded in-tick LOOP over an index instead of an unrolled branch
   per pair; swing dispatch becomes ONE body per unit reading its target's cells
   by computed index. Every ingredient is ALREADY IN-GAME PROVEN on bench 30415
   (computed-index read AND write, VECTOR_SIZE seed/resize, OOB fail-soft).
   Kills all three walls at once: state leaves the band, bodies go O(units), the
   ticker goes O(units·groups). Also UNLOCKS what v1 cannot express at all:
   dynamic target acquisition ("nearest living foe" as an argmin loop) instead of
   static priority lists. Risks to bench first (rung-0 style, one mechanism per
   playtest): per-iteration expression cost (VECTOR indexing per operand — frame
   budget at ~200 iterations/tick), CalcStack depth under composed reads, and the
   loop being a NEW bytecode shape (grounded nowhere in stock fields — needs the
   verbatim-first treatment). Save-persistence footnote: `gScriptVector` rides
   saves (JsonParser) — the size←0/size←n seed idiom already neutralizes stale
   state, keep it law.
2. **Dispatch-body dedup WITHOUT vectors (nearer-term, subsumed by #1 later):**
   one swing body per UNIT, target parameterized through per-unit "current
   target" GLOBs the ticker writes at selection time — the referee's GLOB
   indirection generalized. Saves ~10KB of the 13.6KB on condor-class builds and
   needs no new bytecode shape; costs a few band bytes per unit.
3. **Extended-opcode optable rows (ops 0x112-0x11E):** smaller than the census
   feared — `opcodes.encode` already emits the `0xFF` page prefix and disasm
   decodes it (opcodes.py:44, disasm.py:245); only `_optables.py`'s arg-shape
   rows stop at 0x10A. Adding rows unlocks lint-clean emission of `AddShopItem`
   0x115 (mutate a shop's stock from a running field script — wave-unlocked
   hire rosters), `MOVE_EX`/`AANIM_EX`/`ADD_STATUS`
   (studies/minigame-ui/SURVEY.md).
4. **v1 "Limits" items** (Parallel, action-result plumbing, deeper nesting) —
   still demand-driven; nothing in the ratified fort-condor design needs them.
5. **Side probes** (RunSharedScript caller-context, self-REQ) — unchanged, cheap,
   unlock the per-unit-brain variant.

**★ THE CROSSING PASSED (owner playtest, 2026-07-25):** ISLES (30416, "the
brawl" — 33,820B ticker content, 2 live islands, 14 mutual-combat units + a
crier on the fallen counter) ran clean in-game: "the brawl runs clean, crier
lines all fire." **The LONG-JUMP RELAXATION is now IN-GAME PROVEN** — island
bytes executed, deep-tree branches fired, and the event-Once + counter lanes
re-verified on a second field for free. One observation, owner-triaged as not
worth digging at: a left-arc Mu slid along a wall instead of rounding it —
that is the KNOWN pursuit class, not an island artifact (chase = the duty
body's blocked engine Walk toward a live target; the engine wall-slides, no
routing exists for live-target pursuit, and the pursuit-sweep lint exists
precisely to predict this blocked fraction — the bench's 2200u cross-plaza
chases were authored for the byte crossing, not clean pursuit lines). The
authoring answer stands: place for sightlines, keep chase radii short, use
route="auto" marches for long approaches and chase only for the close.

## Standing constraints

- **Engine independence is THE protected property:** everything pure `.eb`,
  stock-Memoria runnable. The moment a feature seems to need C#, it goes to a
  "wants-engine" list instead of an s-patch reflex.
- Tick cost is proven cheap at bench scale; the compiler keeps a tick-striping knob
  (units tick on alternating frames) in reserve, unexercised until measured need.
- Debug convention from day one: every compiled tree writes its unit's current node id
  to a trace byte — the ~ Flags panel becomes the BT inspector for free.
- One change per in-game test; the human owns feel verdicts. Verbatim-first still
  applies: any NEW engine mechanism an action needs gets grounded in stock bytes before
  its template ships.
