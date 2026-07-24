# Fort Condor in FF9 — a real-time lane-defense minigame (study)

**Goal:** emulate FFVII's Fort Condor minigame (real-time lane defense: place units for gil,
enemy waves advance, units auto-engage, a breach falls back to a real boss battle) as an FF9
field minigame built with ff9mapkit. Learn-first mandate: every mechanic gets grounded in
stock bytes before synthesis (the house method; see CLAUDE.md §6).

**The stock donor:** the **Festival of the Hunt** — FF9's own real-time, multi-actor, timed,
scored minigame (Lindblum fields 550–576, scenario band 3160–3180). Decoded in rung 0.
Secondary prior art: Chocobo Hot & Cold (timer/prize lane, `[chocobo]`), the co-op plate
gates (per-frame looping code entries), moving platforms (lockstep choreography).

## Rung ladder

- **Rung 0 — DONE (2026-07-24): the Hunt decode + the actor-budget census.**
  → `RUNG0.md`. Headline: the Hunt already ships ~90% of the RTS vocabulary in stock
  opcodes (chase loop, engagement radius, contact→battle, score economy, wave bands,
  generic countdown HUD); engine ceilings are ~250 objects / 255 entries (way above need);
  the binding risk is O(n²) collision perf with many MOVERS, unproven past stock's ~23.
- **Rung 1 — THE SWARM BENCH: BUILT + DEPLOYED (2026-07-24), ⚠ playtest pending.**
  `swarm_bench.py` (gen/deploy) → field **30400** ("SWARM", FF9CustomMap), a native fork
  of the Festival square (576) carrying **40 kit `[[npc]]` Mu chasers** whose Loop bodies
  are replaced post-deploy with the stock chase idiom (byte-verified vs field 552:
  `SetObjectFlags(7)` + `SetPathing(1)` + per-frame `Walk(obj(250).x, obj(250).z)`), a
  declarative `[[choice]]` tier lever at spawn (GLOB 8800-8803 → arm 10/20/30/40), a
  Main_Init flag-clear (=> ~ Reload resets the bench) + the generic-timer probe
  (`ChangeTimerTime(600)/ShowTimer(1)/RunTimer(1)` — the Hunt's start triplet on a custom
  id). Each ARMED chaser also evaluates a `B_PTR(250) B_DISTANCEA` poll per frame
  (OR-1'd truthy, consumed by a fall-through 0x02) — poll cost scales with the tier.
  En route: the carried 576 dressing includes 5 stock Mu-model objects (chaser detection
  keys on model + the kit standby-loop signature, never model alone); and playtest 1's
  black screen minted **THE PLAYER-REF EVAL LAW** — `B_PTR`/`B_DISTANCEA` hard-cast to
  Actor (EBin.cs:1161-73) and resolve alias 250 to the CONTROLLED object, so evaluating
  them before a controlled Actor exists throws InvalidCast INSIDE the 0x05 eval → the
  next 0x02 pops an EMPTY CalcStack → permanent per-frame desync (8287 log errors, stuck
  black screen). Player-referencing expressions only ever run behind a player-alive gate
  (stock corollary: the Hunt's 552 poller starts only after the player is staged).
  Playtest 2 (same day): ★ the timer HUD renders on the custom id (the generic-clock
  claim PROVEN) + 40 Mus render; but donor 576's ground-parallel camera (pitch -4.9 —
  the lint warning was the tell) made the swarm unobservable, and the kit's
  dialogue-less-NPC default talk collided with the [[choice]] prompt's txid (menu rows
  everywhere, no dispatch — kit-fix chip filed). Round 2 re-homes the bench on **field
  559, the Hunt's own Zaghnol arena (pitch 68.8, near-top-down)**, gives every chaser an
  own "Kweh!" line, puts the lever zone ON the spawn, strips the real-field gateways.
  **★ PLAYTEST 3 PROVEN (2026-07-24): "no performance issues whatsoever" at ALL tiers,
  and the swarm converges on the player ("eventually converge into a single point" —
  the walk-through no-pile-up design working as intended). THE ACTOR BUDGET IS PROVEN
  AT 40 CONCURRENT MOVERS** — ~2x stock's 23-model ceiling, with 40 per-frame
  `Walk(player.x, player.z)` re-targets + armed-tier distance polls live. The rung-0
  O(n²)-collision concern does not bite at 40 (flags-7 movers). Rung 1 is CLOSED; the
  bench stays deployed on 30400 as the standing swarm harness. Revert:
  `tools/scroll_out/revert_deploy_30400.py`.
- **Rung 2 — TWO-LANE SKIRMISH: BUILT + DEPLOYED (2026-07-24), ⚠ playtest pending.**
  Lives ON the swarm bench (30400) as lever row 5 "Skirmish demo" (flag 8804). Cast: 2
  Fang attackers (north plaza) march on a goal post by the spawn (an Elite-Soldier herald
  stands there), 2 City-Soldier defenders posted ~55% down each lane. Per-unit tag-1
  state machine (label-assembled, disasm-verified jump-by-jump): armed gate → HP-death
  gate (`TerminateEntry`) → enemy-alive gate → contact<150 = FIGHT (TurnTowardObject +
  30-frame swing timer, −1 enemy HP/swing, GLOB bytes 1102-1109) → else defender
  acquires <1500 and chases the attacker's live `obj(uid)` position / attacker marches
  the goal; goal-box arrival = the BREACH (once-flag 8805 + the herald's line as a
  popup). HP 3/5 vs 5/3: lane A defender wins, lane B attacker breaches. SAFETY: every
  enemy-referencing eval sits structurally behind the enemy-HP gate as separate
  statement+jump (RPN has no short-circuit — the player-ref eval law generalized to dead
  uids); a corpse's HP hits 0 a tick before its self-terminate, so peers never poll a
  dead object. Assumes unit uid == entry index (stock convention) — the units engaging
  IS the in-game verification. Measure: defenders intercept? both fight outcomes? the
  lane-B breach popup? chasers + skirmish coexist? ~ Reload = full reset (HP re-preset).
  **Playtest 4 (same day): mechanism ★ PROVEN** ("works exactly as described, both
  outcomes and the breach popup" — uid==entry-index confirmed) but melee READ wrong:
  units overlapped + spun. Engine decode → **THE SYNC-WALK LAW**: `InitWalk` sets
  `loopCount=255` making the next Walk SYNCHRONOUS — `stay()` re-executes it each frame
  until arrival AT THE TARGET (freezing the unit's own state machine; live-expr target =
  arrival at the enemy's CENTER = the overlap), while a BARE Walk executes ONE step and
  falls through (v2 tried per-frame bare Walks → per-frame restart JITTER, playtest 5).
  **v3 = THE REFEREE ARCHITECTURE (the stock shape all along):** units walk SMOOTHLY in
  blocked synchronous Walks (attacker: goal; defender: a GLOB-target the referee feeds —
  stay() re-reads expression operands per frame = live chase with the engine's own walk,
  and the GLOB indirection is the dead-uid firewall); ONE seated referee code entry owns
  all cross-unit logic per frame — HP-gated position mirrors into GLOB Int16s, Chebyshev
  contact boxes on pure GLOB math (no squares/overflow), fight dispatch via
  `RunScriptAsync(4, uid, 15)` (field 574's exact walking-actor redirect idiom) into an
  added tag-15 fight function that self-exits on a death (mine → TerminateEntry; enemy's
  → return, and THE INTERRUPTED DUTY WALK RESUMES — the stock talk-an-NPC
  preempt-and-resume shape), and the defender target feed (enemy mirror inside
  ACQUIRE_R=700, else post). Fights staged at the owner-called visible square
  (FIGHT_CENTER (-1225,-827); posts flank it, goal south).
  **★ PLAYTEST 6 (2026-07-24): "it was a bit sloppy but yeah it works" — RUNG 2 CLOSED.**
  The auto-battler core is PROVEN end-to-end: march, acquire, intercept, ranged-stop
  melee, death, winner-resumes, breach — all in stock opcodes on a custom field. The
  "sloppy" = fight THEATER (deferred by design): no attack clips, no hit SFX, instant
  vanish on death, stand-off spacing tuned by radius only. Polish backlog when a rung
  needs it: attack/damage anims from the model catalog, hit sounds, a death anim before
  TerminateEntry, per-model contact radii.
- **Rung 3 — PLACEMENT + ECONOMY.** Walk-and-place: confirm at a spot → unit-type choice
  menu (dialogue choices) → gil spend → runtime `InitObject` from a pre-authored pool
  (Ice Cavern 303 is the stock runtime-spawn precedent; entries are fixed at build → pool
  + recycle).
- **Rung 4 — WAVES + WIN/LOSS.** Timer-band wave scheduling (the Hunt's
  `GetTimerTime > 600/540/480/…` table shape), a base-HP flag, the faithful Fort Condor
  loss fallback: breach → real `Battle()` boss (the Zaghnol pattern at field 559).
- **Rung 5 — THE FORT CONDOR FIT.** Unit roster/costs/waves tuned to the FFVII design
  (owner ratifies which mechanics are essential: unit types, max 20 allies, gil costs,
  fixed artillery, win rewards). Models from the Info Hub catalog.
- Productization (`[minigame]`-style TOML lane) is deliberately deferred until rung 2
  proves the core loop.

## Standing constraints

- Pure-`.eb` is the target: it keeps the minigame playable on stock Memoria (novel fields
  need no engine patches). Engine s-patch is the escape hatch ONLY if script-side polling
  can't hold the frame budget or a persistent funds/score HUD is demanded (stock precedent
  is popup announcements + the generic timer HUD, both `.eb`-reachable).
- Contact (`_Range` tag-2) events are PLAYER-driven collision; unit-vs-unit engagement is
  `DistanceWithEntry` polling (verify in rung 1).
- One change per in-game test; the human owns feel verdicts.
