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
- **Rung 4 — ★ BUILT (2026-07-24), ⚠ the parity playtest pending: PRODUCTIZE.**
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
- **Side probes (cheap, unblock the per-unit-brain variant later):** (a) shared-script
  context semantics — does `RunSharedScript` execute with the CALLER as gCur? (the
  Hunt's Entry17 poller hints yes → ONE generic brain shared by all units,
  Instance-var-parameterized); (b) self-REQ (an object dispatching its own higher-level
  function).

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
