# Fort Condor in FF9 — a real-time lane-defense minigame (study)

> **▶ THE MIGRATION IS DONE (2026-07-24) — unit AI now runs on the behavior-tree
> compiler.** The behavior-trees study completed its ladder (rungs 0-4 all ★, incl. the
> `[behavior]` TOML product surface — `studies/behavior-trees/PLAN.md`,
> `docs/BEHAVIOR.md`), and this study's bench is REBASED on it: `swarm_bench.py` now
> emits the whole bench (the 40-chaser tier swarm + the rung-2 skirmish, playtest-6
> staging preserved, MUTUAL duels) as `[behavior]` TOML and deploys via plain
> `deploy_field` — **the ~500-line hand-rolled referee/fight/patch machinery is
> DELETED; the compiler subsumes it** (proven by the behavior study's regression bench
> 30411 and the BTRAID showcase parity). Deployed on 30400; **★ THE MIGRATION PARITY
> PLAYTEST PASSED (2026-07-24 — "all three good")**: tiers converge with the chasers
> RINGING the player at the compiler's 140u standoff (the intended change), the
> skirmish replays playtest-6 (both lane outcomes + the one-shot breach popup, duels
> now MUTUAL), chasers + skirmish coexist and ~ Reload resets. The owner's one flagged
> regression — the hire-soldiers-for-gil menu — is the DESIGNED removal in (a) below,
> returning as compiler vocabulary. **Removed with the referee, by design:** (a) the rung-3 placement/economy
> LAYER — its mechanisms (SPECIAL-button poller / gil purchase via `B_SYSVAR[6]` +
> RemoveGil / runtime `InitObject` + `MoveInstantEx` spawn-at-feet, all ★ in-game
> proven, recipes in the rung-3 entry below) return as COMPILER VOCABULARY
> (pooled/runtime-ACTIVATED units — the v1 compiler forbids `requires_flag` on units,
> so a hire-pool needs a new activation lane); (b) playtest 11's staring-duel bug —
> MOOT, that referee no longer exists; (c) the generic-timer probe (claim ★ proven in
> playtest 2; rung 4 re-adds timers as wave machinery).
> **THE RESUME LADDER (the parity playtest ★ done):** 1. pooled-unit vocabulary in the
> compiler — **★ IN-GAME PROVEN 2026-07-24, bench 30413, 3 rounds** ("all good": spawn-
> at-feet + hold_post + pool + the New-Game staged-latch fix; `pooled`/`pool`/`hold_post`
> in `[behavior]` + the per-pool spawn-request flag; the rung-3 recipes returned as
> compiler vocabulary — behavior study PLAN §POST-LADDER) → 2. placement/economy —
> **★ IN-GAME PROVEN on 30400 (2026-07-24, "good")**: `[[behavior.pool]]`
> price 300 (gil gate + RemoveGil in the activation block, charge only on spawn) +
> `button = true` (the SELECT/Special buy-anywhere poller, rung-3 shape verbatim:
> Wait(1) `B_KEYON` poll / blip / `RunScriptSync(4, menu, 3)`) + the parked hire
> [[choice]] matched by request_flag 8848; 4 pooled recruits with hold_post posts and
> MUTUAL attacker↔recruit combat via plain branches (the v1 one-sided-harass debt
> gone). Proven: broke-hire correctly refuses (no spawn, no charge) and the pool cap
> holds. **POLISH DEBT (cosmetic, owner-noted): the menu's "Deployed!" reply plays
> even on a refused hire** — the reply is baked into the choice row while the real
> transaction happens in the ticker. Fix design (queued): the compiler publishes
> per-pool `affordable`/`exhausted` flags (2 writes/tick, cheap) and the hire menu
> gates its rows on them via the existing option requires_flag machinery ("Hire"
> visible only when affordable+available; a greyed "(need 300 gil)" row otherwise)
> → 3. rung 4 waves +
> win/loss (below) on tree-driven units — **IN PROGRESS**. Read
> [[project-ff9-behavior-trees]] + `docs/BEHAVIOR.md` before extending the compiler.

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
- **Rung 3 — PLACEMENT + ECONOMY: BUILT + DEPLOYED (2026-07-24), ⚠ playtest pending.**
  Press **SPECIAL/Moogle anywhere** (the H&C dig button; 559 Code6's exact
  `const4(mask) B_KEYON B_SYSVAR[2]` poll shape) → a seated POLLER code entry
  remote-dispatches the zone-PARKED recruit `[[choice]]` via `RunScriptSync(4, uid, 3)`
  (the zone trigger is bypassed — the kit dispatch body is self-contained) → on "Hire
  (300 gil)": pool gate → gil gate (`B_SYSVAR[6] >= 300`, the inn-553 idiom) →
  `RemoveGil` → runtime `InitObject` of the first free pooled recruit (4 soldiers,
  `requires_flag` keeps them un-boot-spawned) + **`MoveInstantEx` (DPOS 0xBF — moves
  ANOTHER object, x/z only, no height math) to the player's position** + post/target
  GLOB seeding + the placed bit. Recruits run defender-shaped duty loops on own GLOB
  targets; the referee gains placed-gated recruit mirrors, per-recruit dispatch/reset/
  feed (state 0/1/2 = free/fighting-A/fighting-B, A-then-B priority, ACQUIRE_R=700,
  else hold the placement post), and **the harass-death sweep** (one-sided recruit chip
  can zero an attacker OUTSIDE any fight — the referee latches DEAD_FLAGS + dispatches
  an added die tag at level 5, gated on lane_state==0 so an attacker in its own fight
  dies by its own fn, never a REQ on a maybe-dead object). v1 debts (recorded): recruits
  are UNTARGETED (one-sided harass — mutual N×M = rung 4), broke/pool-empty = silent
  refusal. THE DEMO: lane B breaches unaided; 1-2 recruits placed on lane B stop it.
  Playtest (~ Reload): button menu anywhere? spawn at feet? gil deducted (pause menu)?
  recruits chase+chip? lane B saved? pool caps at 4? reload resets (gil NOT refunded —
  gil is real save state, spend knowingly).
- **Rung 4 — WAVES + WIN/LOSS: BUILT + DEPLOYED (2026-07-24), ⚠ playtest pending.**
  All three mechanisms as COMPILER VOCABULARY (behavior study post-ladder): field-level
  `timer = <seconds>` (the Hunt's exact HUD start triplet — ChangeTimerTime 0x69 /
  ShowTimer 0x8D / RunTimer 0x7D — ★ the custom-id claim was proven back in playtest 2)
  + `time_below`/`time_above` conds (B_SYSVAR[17] = remaining seconds; the Hunt's
  GetTimerTime band shape) + the `battle = <scene>` action (`Battle(0, scene)` —
  559's OWN tread-battle byte shape, scene 35 = the arena's stock fight so no
  BattlePatch; ONE-SHOT per load by construction via a compiled latch that gates the
  dispatch; the build auto-installs the entry-0 tag-10 Main_Reinit + BGM resume — the
  after-battle resume law — whenever a battle compiles). THE SIEGE on 30400: 3:00
  clock, wave 1 (Fangs hp 3/5) at 2:50 + wave 2 (hp 5/5) at 1:30 on `route="auto"`
  marches (the owner's pathfinder lane, dogfooded), the herald = THE GATE (hp 6,
  attackers swing him; his cry once at any_near), gate down → the loss battle →
  return → the gate falls + the siege stands down (`lost`); survive to 0:00 →
  the minted win announce (`won`). Measure: the wave cadence, the gate fight, the
  loss battle firing ONCE with a clean after-battle return (no softlock, BGM back),
  the win path, recruits + defenders + economy unchanged, ~ Reload = full round reset.
  **ROUND 1 (2026-07-24): waves ★ ("all 4 Fangs spawn in" on a late arm — both bands
  open at once, as designed) + the win line ★ — but THE LOSS BATTLE NEVER FIRED,
  owner-diagnosed as the defeat dialogue clobbering it. CONFIRMED mechanically — THE
  ONE-TICK DISPATCH CLOBBER: a Battle branch's own raise_flags ("lost") promotes the
  die branch above it NEXT tick, so the battle is selected for EXACTLY ONE tick; if
  another body (the gatecry announce, still exiting) holds `running` through that
  tick, the sel-gated dispatch never fires. FIX (compiler-structural, same day): THE
  EDGE-LATCHED REQUEST LANE — selecting a Battle branch sets a `breq` flag; the
  dispatch tail fires on breq && !fought && running==0 INDEPENDENT of the current
  selection, ordered first with a one-REQ-per-tick jump.
  ★ ROUND 2 PROVEN (2026-07-24): "i fought a Trick Sparrow with no re-swirl and no
  softlock. win still works" — the loss battle fires (edge-latch ✓), one-shot holds
  (no re-swirl ✓), the after-battle return chain is clean (tag-10 ✓), the win path
  regression-clean. RUNG 4 IS CLOSED — the ladder rungs 0-4 are ALL ★ IN-GAME
  PROVEN. Next: rung 5 (the Fort Condor fit) + the owner's dynamic-pursuit research
  (integrate if viable).**
- **Rung 5 — THE FORT CONDOR FIT.** Unit roster/costs/waves tuned to the FFVII design
  (owner ratifies which mechanics are essential: unit types, max 20 allies, gil costs,
  fixed artillery, win rewards). Models from the Info Hub catalog.
  **RATIFIED (owner, 2026-07-25):** roster = LEAN 3 (Soldier melee chaser / Shooter
  stationary artillery / Defender tanky gate guard, each own model+stats+price) ·
  economy = 20-ally cap across pools, FFVII price band ~300-600 gil · win = GIL + AN
  ITEM (verify the .eb gil-award lane — the chocobo prize path pays gil) · battlefield
  = THE 30400 PLAZA with the owner's siege layout: the defended base/NPC on the EAST
  side (east of the center block); waves enter at the NORTHWEST and SOUTHWEST
  entrances on authored marker paths; the two chokepoints sit ~north and ~south of
  the monument. Also lands: the recorded hire-menu polish debt (compiler-published
  per-pool affordable/exhausted flags gating menu rows — kills "Deployed!" on a
  refused hire). Layout mapping goes through the layout probe FIRST (the cardinals
  law: FRONT = -z; probe PNGs before any coordinate is written).
  **BUILD 1 ⚠ DEPLOYED, playtest pending (2026-07-25)** — `condor_fit_bench.py`
  rebuilds 30400 as CONDOR: depot hp 24 + QM at (1153,-200) east of the monument
  (this camera is yaw-0 — probe-verified, so the owner's screen directions ARE
  world cardinals); 4 pools (5×Soldier-N 300 / 5×Soldier-S 300 / 5×Shooter 550 /
  5×Defender 450 = the 20 cap) hired via the SELECT war council (ONE parked menu,
  four rows, each gated on its pool's NEW published `hireable` flag — rows vanish
  instead of lying); waves 2/2/1+1/2 (2 Fang heavies) on sched [220,170,120,70]
  over a 4:00 clock, marching route="auto" lanes NW→north-choke and
  SW→south-choke; the opening 3000-gil STIPEND + the win purse (2000 gil +
  Phoenix Down) ride the NEW `award` verb (exactly-once by the event-Once lane);
  loss = depot hp 0 → Battle(35). Compiler additions this rung: `award` +
  `pool_hireable`. THE CAPACITY FINDING: the v1 central ticker tops out ~32KB
  (signed-16 jump spans) — the 20-ally × 8-raider full cross-product does NOT
  fit; per-type target trims ship build 1 (soldiers fight their own watch's
  lane, defenders grind the late/heavy four), and the REAL fix — a long-jump
  relaxation pass in `eb/labelasm.py` (island trampolines at
  unconditional-jump sites, offsets iterated to fixpoint) — is the queued
  follow-up. Bench-layout laws minted: anchor picks = the spawn's CONNECTED
  COMPONENT of the tri-nbr graph (same-floor pockets can be DISCONNECTED sheets
  — the east bay was, and the route planner rightly refused an anchor there) +
  a ~120u wall-clearance filter + a height band that keeps the street arms but
  drops the balcony class.
  **ROUND 1 PLAYTEST (2026-07-25): the ECONOMY LANE ★ ("the stipend and reward
  pay out" — the award verb's in-game proof); two design defects + one ask:**
  (1) raiders jogged away from their attackers (single-minded was a budget trim)
  → **`hold_ground` — THE PIN** (new dispatch action: selection halts the walk
  via the dispatch-halt clause, body idles while selected; raiders pin on
  any_near(soldiers, 240), resume the march on release; at the depot the
  swing-base branch outranks the pin so the grinder duel stays a duel);
  (2) the north/south watch split read as nonsense with manual placement (it
  was the ticker-budget hack it looked like) → ONE Soldier pool; (3) 1-minute
  tuning runs → timer 60, sched [55, 40, 20], waves 2 NW / 2 SW / 2 heavies.
  **ROUND 2 ★ (pin proven: "enemies stop when engaged"; loss battle ✓; 14-cap
  accepted "for now"; owner asked: strip the donor bystanders + DIG INTO THE
  LONG-JUMP RELAXATION — "making the compiler/language more robust is equally
  as important if not moreso").**
  **ROUND 3 ⚠ DEPLOYED — THE RELAXATION PASS SHIPPED + the counterattack:**
  `labelasm.asm()` now relaxes out-of-range jumps through fall-through-safe
  ISLANDS (nearest legal boundary strictly between source and target, fixpoint
  iteration, chains past 64K spans; byte-identical when nothing overflows; no
  island between a statement and its conditional; 11 tests incl. a 30-unit
  40KB ticker). THE NEXT WALL FOUND THE SAME HOUR: the u16 ENTRY TABLE = a
  ~64KB whole-FILE reach (engine-fixed) — the first 6×14 counter build wrapped
  an entry offset into garbage tags because `set_u16` MASKED; set_u16 is now
  STRICT and append_entry pre-checks. Measured budget on this donor: ~50-55KB
  of compiled behavior bodies TOTAL; the full 20-ally × counter cross-product
  exceeds the FILE (not the ticker) — so round 3 ships 14 allies with counters
  scoped to the melee engagers: every raider counter-swings any SOLDIER in
  contact (a counter-swing halts the march, so the hold_ground pin branch is
  SUBSUMED and dropped), heavies also counter DEFENDERS (the depot duel is
  mutual), allies have hp (soldier 4 / shooter 3 / defender 8) and die for
  real. Donor bystanders (the 5 npc-kind carried [[object]]s — Zaghnol, the
  red-hat villager, the little girl, the noble woman + one) stripped; the two
  scenery props stay. Shipped .eb 55.4KB / 65.6KB reach.
  **ROUND 3 ★ ("good", 2026-07-25): the COUNTERATTACK is in-game proven** —
  raiders trade blows with their engagers, allies die for real, the mutual
  heavy/Defender duel holds, the plaza is clean of bystanders, win/loss
  regressions clean. NOTE for precision: this ticker is 30.2KB (back under the
  old wall after the file-budget trims), so the ISLAND bytes themselves have
  not yet run in-game at the time — since ★ RESOLVED: the ISLES bench (30416,
  the 14-unit brawl, `studies/behavior-trees/island_bench.py`) crossed the wall
  in-game 2026-07-25 ("brawl runs clean, crier lines all fire") — the
  relaxation is fully proven and condor content may exceed 32KB freely (the
  FILE wall remains the binding budget).
  **ROUND 4 ★ IN-GAME PROVEN (2026-07-25) — THE GROUP RE-FIT: the ratified
  design is WHOLE.** Two fixes bought en route, both recorded as general laws:
  the strip overlapped the countdown clock (MPOS is the PSX-ish 320x224 grid —
  stock pins its save menu at 20,16 — and the TIMER OWNS THE TOP-LEFT CORNER;
  moved to 10,48), and the reward paid TWICE (the rout award and the clock
  award were separate branches with separate once-latches → restructured as
  DETECT-THEN-PAY: each ending announces and raises a shared `won` flag gated
  on `not_flag "won"`, ONE award branch gated on `flag "won"` pays once —
  now in BEHAVIOR.md as the win-condition shape). Owner: "both fixed, one
  purse fires now". The siege now runs on the
  v2 substrate proven on 30416: two GROUPS (raiders / allies) carry position +
  alive + hp as table state; `engage nearest` replaces every hand-listed pair
  branch (one branch + one target-indexed body per unit), so **the ratified
  20-ALLY CAP is restored** (8 Soldiers / 6 Shooters / 6 Defenders) **with the
  FULL mutual cross-product** — every ally fights every raider and vice versa,
  which round 3 could not afford at any cap; class STANCE is now just a radius
  vs contact ratio (Soldiers hunt at 2000/170; Shooters and Defenders take
  contact = radius-1 so their pursue phase can never select = artillery that
  never leaves its post); two `alive_only` scans publish live headcounts,
  feeding both the WAR-ROOM STRIP (`[[behavior.hud]]`: GIL / TROOPS / RAIDERS
  / DEPOT hp, the census substrate, no DLL) and a NEW early win — THE ROUT
  (wave 3 spawned + zero raiders alive → the purse without waiting out the
  clock). **Budget: 42,147B for 26 units WITH the cross-product, vs round 3's
  49,383B for 20 units WITHOUT it** — the three walls are headroom now.
  OPEN rung-5 items:
  the tuning pass toward the FFVII feel (owner-driven, 1-minute clock stays
  until then), restore the real 4:00 clock when tuned, win/lose presentation
  polish. The `[minigame]`/`[condor]` productization decision is ★★ CLOSED 2026-07-26: shipped as the `[siege]` block (content/siege.py, FORMAT.md), acceptance-proven on THE REDOUBT (30421 = the 30400 siege from one block, owner: "pass").
  **PREP DONE (2026-07-24): the DATA-TABLE substrate is built** — `[[behavior.table]]` /
  `counters` / `[[behavior.schedule]]` (the wave clock: `wave += 1` while the HUD sits
  below `sched[wave]`, self-terminating; `die = "kills"` tallies; `counter_ge` gates
  waves and win conditions; `table_*` verbs take a counter as a COMPUTED index). Wave
  compositions, band times, and win thresholds become ONE table edit instead of
  re-unrolled branches. ★ PROVEN on bench 30415 (BTTABLE, 3 playtest rounds,
  2026-07-24 — incl. THE EVENT-ONCE fix) — the substrate is live; rung 5 builds on it. Remaining rung-5 vocabulary gaps, for
  the ratification round: per-pool hire MENUS with multiple unit types priced apart
  (today: one pool = one price; N types = N pools + N menu rows — workable, just
  verbose), the affordable/exhausted feedback flags (recorded polish debt), win
  REWARDS (a `give_gil`/`give_item` on the win branch — the [[event]] lane may
  already cover it), and the 20-ally cap (pool sizes already are the cap).
- Productization: ★★ DONE — the `[siege]` TOML lane (see above).

## Standing constraints

- Pure-`.eb` is the target: it keeps the minigame playable on stock Memoria (novel fields
  need no engine patches). Engine s-patch is the escape hatch ONLY if script-side polling
  can't hold the frame budget or a persistent funds/score HUD is demanded (stock precedent
  is popup announcements + the generic timer HUD, both `.eb`-reachable).
- Contact (`_Range` tag-2) events are PLAYER-driven collision; unit-vs-unit engagement is
  `DistanceWithEntry` polling (verify in rung 1).
- One change per in-game test; the human owns feel verdicts.
