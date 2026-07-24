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
- **Rung 2 — THE REGRESSION PROOF.** Re-express the fort-condor skirmish (lanes, duels,
  recruits, breach) as trees; identical in-game behavior = the compiler subsumes the
  hand-rolled referee. Fort-condor migrates here if (and only if) this passes.
- **Rung 3 — THE SHOWCASE.** A scene only the system makes writable: e.g. guards with
  patrol shifts + an alarm behavior that regroups them + flee-at-low-HP + a captain
  rallying — layered, interruptible, readable.
- **Rung 4 — PRODUCTIZE.** `[[behavior]]` TOML + CLI verbs + FORMAT.md/docs + tests;
  the GUI section as its own later round.
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
