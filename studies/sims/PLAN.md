# The Manor — a simplified Sims on the behavior compiler (study)

**Goal:** a playable one-room life sim in pure `.eb`, stock-Memoria runnable — the
behavior compiler's first non-combat stress test. Every prior proving ground (raids,
brawls, sieges, waves) had boolean, monotonic state; a life sim's state is analog meters
that decay, refill, and rank against each other. Different program shape, different
failure modes — that is the point.

**The design brief** (full mechanics menu, walls, control metaphor) lives in the approved
session plan; the load-bearing decisions are restated here.

**Owner decisions (2026-08-14):** player *directs* autonomous Sims — the player avatar is
a diegetic cursor (a moogle steward with no needs; walk to an object, Confirm, a
`[[choice]]` menu directs the Sim) · all four pillars in scope (needs+affordances /
day-night clock / social / money-job-skills) · first playable = one room, one Sim ·
directives by walk-to-object + Confirm · a neglected Sim **faints, never dies**.

**Setting:** Mognet Manor. Gil = simoleons; kupo nuts = food; buy mode = a real FF9 shop;
a falling-out = a real FF9 battle. Nothing is a port.

---

## Rung 0 — ★ DONE (2026-08-14, offline): the probes + `adjust`/`drift`

**Probe (a) — the countdown-timer leak. RESOLVED, memory corrected.** The
`TIMER_DISARM` fix (commit `551877f9`) had NEVER merged to master — it sat on
`claude/competent-antonelli-d40ac6`; project memory over-recorded it as landed.
Cherry-picked here as `f13eb551` with the engine patch **renumbered s69→s80**
(s69 was since taken by minimap-visible-state — the two-patches-one-number
disease, the s48 precedent). ⚠ **The engine half (`KillCountdown`) is NOT in the
b19 bundle** (rebuilt s22-s79): a ~ debug warp off a timer field still leaks the
clock until the next engine rebuild. The kit half (every compiled exit disarms)
is live in this tree and tested.

**Probe (b) — the Sim model. RESOLVED: `GEO_MAIN_F0_VIV` (id 8), Vivi's own
field rig.** Same-form (own-clip-law-clean) it owns the complete life-sim set:
`on_bed` / `on_bed_snore` / `on_bed_to_sleep` / `off_bed` / `sleeping`,
`dine_1..5`, `sit_chair_1_*` / `sit_ground_1_*`, `hiza_1..3` (the collapse),
`laugh` — 197 clips total, the best-equipped rig in a 710-model survey. The
black mage the design wanted is also the mechanically correct choice.
Runners-up: **Garnet** (`GEO_MAIN_F0_GRN`, 185 — dine + on_bed + sleep_chair +
sit_talk) as the visitor/second Sim; **`GEO_NPC_F0_CAT`** (115 — `sleep`,
`wash_face`) as a free household cat. Eat clips are RARE: `dine_*` exists only
on the main cast (VIV/ZDN/GRN/FRJ/STN) + `GEO_SUB_F2_CID`; generic NPCs top out
at `bar_drink`.

**Probe (c) — `B_SYSVAR[20]` (play-time seconds) as a model clock: DEFERRED to
the rung-1 bench** (it needs the game; unbenched from a field `.eb`, no kit
consumer). Rung 1 uses the countdown clock; the bench prints a `B_SYSVAR[20]`
HUD slot as a free rider to settle the probe.

**`adjust` + `[[behavior.drift]]` SHIPPED** (commit `6a9df157`) — the
vocabulary's first numeric write:
- `adjust` rides a branch like raise_flags: a clamped write while selected,
  `every` = a byte-timer rate divider (central clock v1 / Instance var brains).
- `[[behavior.drift]]` = the field-level metabolism lane in the ticker's clock
  segment. **THE RUNG-0 DECISION: decay is field-level drift, never branches** —
  the selector fires one branch per unit per tick (the draining-condition law),
  so five needs as decay branches would compete for selection; as drift rows
  they just tick.
- Clamp mandatory; ±10^6 magnitude fence on every operand and adjusted-table
  seed (26-bit overflow RE-READS as a different variable class — not truncation).
- Computed-index writes (`index = "<counter>"`) ride the scan loop's proven
  composition. A never-raised drift gate flag refuses at build.
- Unused ⇒ byte-identical (verified working-tree vs HEAD: `ccfef59a580d1ba5`
  both). 24 compiler tests + 3 behaviorsim pins; battery 349 green.

---

## The rung ladder

One mechanism per playtest. Verdicts are the owner's; the gate suite is not an oracle.

| Rung | Delivers | New surface | Verdict question |
|---|---|---|---|
| 0 | probes + `adjust`/`drift` | `adjust`, `[[behavior.drift]]` | ★ DONE offline |
| 1 | THE FIRST MEAL — one Sim (VIV), one need, one stove, one directive menu, HUD | none (wiring) | **★ MECHANISM PROVEN in-game by the harness (27/27)**; feel = owner — does the number move and does the Sim go? |
| 2 | five needs, ~6 objects, priority-branch autonomy, the day clock, speed control | none (+1 kit refusal) | **★ MECHANISM PROVEN in-game by the harness (20/20)**; speed control NOT built; feel = owner — alive when you stop directing it? |
| 3 | `pick` — argmax autonomy; A/B vs rung 2 | `pick` | NOT smarter for the Sims (priority list kept); the lane is in-game proven (23/23) and **KEPT in the kit** (owner: "if it is useful, keep it") |
| 4 | failure states, mood, emote; readout upgrade (`[TBLE]` words / gauge bridge) | `hold_ground` `anim`/`freeze` (posed holds) | **★ MECHANISM PROVEN in-game (13/13)**; words/gauge NOT built (HUD [TEXT=] is refused now); feel = owner — is failing funny? |
| 5 | the visitor (GRN), relationships, conversations, the falling-out battle | none | does the social loop read? |
| 6 | job, skills, gil, the moogle shop / buy mode | none | a reason to play a second day? |
| 7 | productize — a `[household]` block (the `[siege]` pattern, LAST) | the block | — |

Standing rung-1 notes:
- Needs = counters/tables (vector cells): re-seeded at entry, so `~ Reload` = a fresh
  day for free. Cross-day persistence (GLOB bytes) is a deliberate later design.
- Mood = **average** of needs (`B_LMAX`/`B_LMIN` are party selectors, not min/max —
  the documented trap); expressible as an `expr:` HUD source, zero new surface.
- The steward's menus bind to a TALK (`[[choice]] npc =`), never a stacked action
  zone (THE ONE-CONFIRM-RECEIVER LESSON); "Never mind" is the LAST row (cancel
  returns it); `EnableDialogChoices` 0x7C masks rows by live expression ([PCHM]).
- The one-shot use animation is a LAYER: `SetStandAnimation → SetWalkAnimation →
  SetAnimationFlags(1,0) → RunAnimation → Wait` — never a bare RunAnimation.
- HUD strip at `[MPOS=10,48]` (the countdown owns the top-left), `digits` ≤ 5,
  `[NFOC]`+`[NTUR]` via the dressed-window path. When a window closes itself,
  **F9 first** (the turbo latch) before suspecting the mod.
- Layout: `tools/field_layout_probe.py` PNGs BEFORE any coordinate; ≥192u actor
  spacing; `route = "auto"` on marches; run `behavior lint` on the bench.
- Furniture placement position is OUT OF SCOPE (needs a cursor + live walkmesh
  rebuild); bought objects appear at designated slots.

## Rung 1 — ★ MECHANISM PROVEN IN-GAME (harness, 27/27); feel verdict = owner

`sims_bench.py` (`gen`/`sim`/`deploy`) → **30430 "MANOR1"**: Bilba (VIV) wanders a
home corner; the soup pot (`GEO_ACC_F0_SUP`) sits east inside a press-action zone
choice (`bubble`, `instant`; the cook row hides while an order pends via
`requires_flag_clear` on the SAME public flag 14867); hunger = `need[0]` seeded 80
(table id pinned 1000 so the HUD `expr:` source names it stably); drift −1/45f;
cook branch holds at the pot with `adjust` +2/8f to 95+, then walks home and
`clear_flags` retires the order. Offline gates all green: kit lint 1 advisory ·
behavior lint clean · compile report saved (`bench/rung1.report.txt`) · layout
probe PNGs read · the `sim` command asserts both phases (decay 80→74 by t300,
full at t427, home + order cleared t545). En-route toolkit fixes: the harvested
schema's latent `walk_to` hole + the new vocabulary (the regen had been silently
refusing to emit on a cold cache — field 2800 + world_hub cameras), and
`lint_flag_bands` now sanctions a field's own public-flag lever indices.
**RELAUNCH** (first deploy of the id) → `~ → Warp → 30430`. Checklist: (1) hunger
ticks down ~1/1.5s on the strip; (2) pot + "!" + Confirm → "Bilba, cook
something." → Bilba walks over; (3) number climbs to 95+, Bilba ambles home;
(4) while cooking the row is hidden ("Never mind" only), afterwards it returns;
(5) `~ Reload` reseeds 80 / home / order clear. Pacing note for the verdict: a
full meal is ~5s — tune `COOK_BY`/`COOK_EVERY`/`DECAY_EVERY` to taste at rung 2.
⚠ B_SYSVAR[20] probe deferred out of rung 1 (kept the bench one-mechanism).
Revert: `tools/scroll_out/revert_deploy_30430.py`.

**THE HARNESS RUN (`rung1_meal.py`, 27/27 on run 5; `py tools/play.py studies/sims/rung1_meal.py`).**
30430 had dropped out of every DictionaryPatch since rung 1 (the bench toml is gitignored) -- regenerated
and redeployed from `sims_bench.py`; the offline sim still passes on today's compiler. All five checklist
points measured live, from published state only: hunger = the rendered HUD strip, Bilba = her s89
`objects` uid, the order = watched bit 14867.
- (1) boots 80, decays **0.60/s** with nobody directing (design 0.67; 7 points in 11.7 s, quantized);
  unordered Bilba stays <= 253u of home and ambles (moved 181-417u).
- (2) Confirm in the pot zone opens "The soup pot sits cold." / cook / Never mind; ordered, Bilba reaches
  her cooking spot in **1.5-3.1 s**; the "!" bubble renders (frame `4-cooking`).
- (3) hunger climbs **68-71 -> 95 in 3.5-4.0 s**, the order flag clears itself, Bilba is home 1.3-5.7 s
  later; the clamp holds (peak 95).
- (4) with an order pending the cook row is HIDDEN (`active [1]`, "Never mind." only); after the meal it is back.
- (5) re-entry (a warp to 30430 -- what ~ Reload stands in for) mid-order: hunger 80, Bilba home, flag clear.
- Zero exceptions in either log.

Findings the run taught (for the owner's feel verdict and for rung 2):
- **The order lands when the REPLY closes, not at the pick** (reply out frame 1747, flag 1751): "Bilba
  shuffles toward the pot." is read while she stands still. Consider no reply, or a reply that fits the pause.
- **The steward is still Zidane** (the design's moogle steward is not wired yet) -- a rung-2 dressing item.
- The camera scrolls east with the steward; standing at the pot zone's east side puts him in front of the
  pot on screen. Place the pot zone so the steward stands beside, not in front of, the stove.
- **HARNESS DEFECT, FIXED (not the bench): `choose_landed` credited a Confirm pressed while the choice window
  was still OPENING** (menu group `''`, not yet `Dialog.Choice`): the game dropped it, and the first read failed
  `_choice_ready`, which it scored as "left" = landed (run 3's ring: menu up 2128 at group '', Confirm ~2130,
  `Dialog.Choice` from 2136 with the flag still clear). `select`/`choose_landed` now wait on `_choice_ready`
  and `_pick`'s workaround is gone; re-proven live 27/27 (`.harness-runs/20261009-204122-rung1_meal`): all
  three picks requested on the first `Dialog.Choice` read, the window closing two frames later.

## Rung 2 — ★ MECHANISM PROVEN IN-GAME (harness, 20/20); feel verdict = owner

`sims_bench2.py` (`gen`/`sim`/`deploy`) → **30431 "MANOR2"**; harness scenario `rung2_day.py`
(`py tools/play.py studies/sims/rung2_day.py`, ~3 min). No new compiler surface.
- **Five needs** in one table (hunger/thirst/energy/hygiene/fun, id 1000), one drift row each, plus a
  `night`-gated extra energy drain. **Five objects** (pot, cup, tent, cask, the Garnet puppet) with
  Bilba's use-spot on one side and the steward's zone menu on the other flank (no reply page).
- **Autonomy = four tiers over one task flag per need**, in branch order: *finish* (flag + need >= 95
  → clear) · *use* (flag + at the spot → hold + adjust) · *go* (flag → walk) · *urge* (no task, need
  <= 40 → raise its flag; at night energy <= 70 already sends her to bed). A directive raises the same
  flag an urge does, so **orders queue for free**: she finishes the object she is at, then walks to the
  next flagged need in table order.
- **The day clock**: an hours cell (+1 / 150 ticks = 5 s; a day is 2 min, starting 06:00) on a one-strip
  HUD `HUN THR NRG / HYG FUN / DAY n hh:00`; a 12-hour alternator is `night`.

**Live (run 3 of the scenario, after two instrument fixes):** left alone for one in-game day
she started 8 tasks across all five needs (fun 12:00, thirst 14:00, energy 18:00, hunger 20:00, hygiene
00:00, energy 01:00, thirst 06:00, fun 07:00), every one reached its object, filled and retired; lowest
needs 31-42, nothing near 0; never idle > 0.5 s with a need under the urge line; she turned in at 18:00
and again at 01:00. Clock 0.194 h/s; the alternator agrees with the HUD hour (3/285 samples off, each a
flip edge -- it leads the hour by a fraction). Queue: hunger then energy ordered back to back, the second
menu hid its row while pending, both completed, never at the tent with the meal pending.

Findings:
- **The offline sim caught the priority list's failure mode before the game did.** The first tuning
  (fun -1/30, thirst -1/35, sleep +1/10) let FUN HIT 0 in 3 undirected days: fun is the last urge row,
  decays fastest, and drains through long naps. Retuned (fun/45, thirst/40, sleep +1/6, urge at 40) for
  a fair rung-2 baseline. That starvation is exactly the question rung 3's `pick` (argmax) answers --
  A/B it against these rates AND against the first tuning.
- ⚠ **KIT DEFECT FIXED: two `[[behavior.hud]]` strips overwrite each other.** `ETb.gMesValue` is ONE
  static `Int32[8]` (EventEngine.Initialize.cs:30) and `values[i]` always feeds slot `i`; the needs strip
  rendered the clock strip's day/hour/index (`HUN 1 THR 8 NRG 1`). The validator only refused two strips
  on one WINDOW. Now refused at build (`behaviortoml.validate`, test `test_second_hud_strip_refused_...`);
  BEHAVIOR.md HUD section says one strip per field.
- ⚠ **`[TEXT=]` in a HUD strip is FROZEN at window open** (engine: `TextParser.Parse` substitutes constant
  tags before the `VariableText` snapshot every [NUMB] refresh restores). The "(day)/(night)" word rendered
  "" all run. KIT DEFECT FIXED: `hud()` and `behaviortoml.validate` now REFUSE `[TEXT=]` in a strip (they
  used to clamp it as a live lane). Rung 2 reads night off the hour instead; rung 4's "[TBLE] words"
  readout cannot ride the strip -- it needs a re-issued window (flicker), a `[[choice]]` page, or numbers.
- The steward's `walk_to` presses the LARGER axis first: one call from the spawn to the pot cut up past the
  cask inside its collision ring and never arrived. The scenario walks one-axis legs on probe-clear lanes.
- **Speed control is NOT built** (a field-level rate switch would need flag-gated duplicates of every drift
  AND adjust row, and adjust has no flag gate; Memoria's own turbo key speeds the whole game). Owner call:
  is the engine turbo enough, or does the household want its own 1x/2x/3x?
- Feel notes for the owner (frames `1-boot`, `3-asleep`): the cask renders huge and the cup/puppet tiny;
  the back row (tent, puppet) sits at the top edge of the opening view until the steward walks north;
  "asleep" is the standing pose (the sleep clip is rung 4's emote work); the steward is still Zidane.

## Rung 3 — `pick` built and proven in-game (23/23); the A/B says NOT smarter → DROP (owner to confirm)

**The lane** (`[[behavior.pick]]`, branch `claude/sims-rung3-pick`, NOT merged): every ticker pass, after the
drifts and scans, a bounded loop publishes the INDEX of a table's lowest (`mode="min"`) or highest cell into
a counter; ties keep the lower index. Branches gate on `counter_eq`. 138 bytes of ticker per pick whatever the
length + 26 of Main_Init; validate refuses a counter anything else writes; the stepper models it; schema
regenerated; 5 tests (two mutations of the emission each turned one red). Docs: BEHAVIOR.md § Picks, FORMAT.md.

**In-game** (`rung3_pick.py` on bench 30432 = rung 2 with the urge tier gated on `counter_eq = ["urgent", i]`
and the pick shown in HUD slot 7): URG named the lowest displayed need in **314 of 314** samples; every task
she started on her own (bedtime aside) was the need the pick named; every rung-2 check passed against it.

**The A/B (`py studies/sims/sims_bench2.py ab`, 3 undirected days in the stepper):**

| rates | urge tier | lowest need | misery (shortfall under the line, summed per tick) |
|---|---|---|---|
| first (overloaded) | priority | fun 0 | 93,761 |
| first (overloaded) | pick | hunger 6 | 103,601 |
| tuned | priority | hunger 29 | 6,565 |
| tuned | pick | hunger 29 | 6,565 (identical) |

- **Tuned: identical, tick for tick** -- two needs are never both under the line at a decision point. The live
  run confirms it: the same eight starts at the same hours as rung 2's.
- **Overloaded: pick only moves the shortage around.** It rescues fun (0 → 6) and costs hunger (9 → 6) and
  ~10% more total misery. The first tuning's real defect was CAPACITY (needs decay faster than one Sim can
  serve them, worst during long naps), not the ORDER she serves them in.
- **Verdict by this rung's own rule: not visibly smarter → DROP** from the Sims design; rung 4+ keep the
  priority list. The open question for the owner is only whether the KIT keeps `pick` as a general
  primitive (argmin over a table is what no branch condition can say) or the branch is abandoned.
- If urgency ever matters again, the measured lever is not argmin of raw values but time-to-empty (needs on
  one decay rate with per-need capacities), or letting an urgent need INTERRUPT a long task -- both rung-4
  failure-state work, not a new lane.

## Rung 4 — ★ MECHANISM PROVEN IN-GAME (harness, 13/13); feel verdict = owner

**New kit surface: the posed hold** -- `do = { hold_ground = true, anim = "<gesture>", freeze = true|false }`.
While selected the body installs the clip as the unit's stand AND walk animation (field-animation law 4),
optionally freezes it at its last frame (law 5), and plays it; on deselect it CLEARS the animation flags
first (the engine keeps `animFlag` on the actor -- a leftover freeze would freeze the idle), restores the
NPC's own stand/walk clips (resolved by the build's one resolver, `blockmodel.resolve_block_model`), and
plays the stand so she gets up at once. A plain `hold_ground` compiles exactly as before. Gestures resolve
same-form (the own-clip law). 3 tests; dropping the flag reset turns the pose test red.

**Bench 30433 "MANOR4"** (`sims_bench2.py --variant rung4`, the rung-2 priority list + rung 4):
- use poses -- `dine_1` at the pot, `sleeping` at the tent, `laugh` at the puppet (thirst/hygiene stand);
- **FAINT**: a need at 0 drops her where she stands in a frozen `hiza_1`; down, the need creeps +1/11 ticks
  to 25, then she gets up and her urge takes her to fix it;
- **the all-nighter**, a tent directive ("Bilba, stay up all night!"): wakes her, bars sleep, drains energy
  -1/6 ticks -- failure on demand (the tuned household never fails on its own: 3 undirected days, low 29);
- **MOOD** = the floor of the five needs' average, HUD slot 7; idle emotes on a 2.5 s beat -- `yawn` when
  energy <= 55, `laugh` when fun >= 80.

**Live (`rung4_fail.py`, first run 13/13):** MOOD matched the average on 166 of 166 samples; all four poses
fired and were shot; the all-nighter landed, energy 74 -> 0, she fainted at (-61,-868) and did not move
(0u spread over 51 samples) while energy crept 1 -> 24, rose at 25, and WALKED herself 690u to bed -- the
restore works (no frozen kneel carried into the walk); fainting cleared the all-nighter. Zero exceptions.

**Frames, read by the agent** (`.harness-runs/*-rung4_fail/shots`): `3-asleep-at-the-tent` is unmistakable
-- flat on her back before the tent; `2-laugh-at-the-puppet` a distinct arm-out stance; `6-fainted` reads as
a crouched kneel, not a fall; `4-eating-at-the-pot` is hard to tell from standing at this camera distance.

Open for the owner's feel verdict ("is failing funny?"):
- the faint is a KNEEL (`hiza_1`); for an all-nighter, collapsing flat in the `sleeping` pose may be funnier
  (Vivi's rig also owns `hiza_2/3`, `tired_loop`, `wakeup_sad*`, `sad`);
- `dine_1` barely reads; `sit_ground_1_*` or `dine_sleep_*` are candidates;
- not exercised live: the wake rule (she was not in bed when the all-nighter was ordered);
- the readout upgrade (`[TBLE]` words, a gauge) is not built -- HUD `[TEXT=]` is now refused at build.

## Bench

**Ids 30430-30435** (30430 = rung 1, 30431 = rung 2, 30432 = rung 3 pick, 30433 = rung 4) (30426-30499 is the free band; 30400-30425 is the standing
behavior/minigame family; do NOT take 30600+ — WINSTYLE/lock/multiwindow live
there even when absent from the live DictionaryPatch). Re-verify the live file
before minting. Bench generator: `studies/sims/sims_bench.py` (pure product
path — TOML → `deploy_field --id`), one rung at a time.

Deploy: `py tools/deploy_field.py <toml> --id 30430` (always `--id`; never pin
id in `.ff9deploy.toml`). First deploy of a new id = RELAUNCH; after that
`~ → Reload`. Sim every bench offline first (`behaviorsim` — an instrument,
not proof). Keep bench print strings ASCII (cp1252 console).
