# Rung 1 playtest — demand-driven `story-seed` presets, in-game

Three verbatim forks, each booted with `story-seed`'s emitted `[startup]` block **pasted
verbatim — zero hand edits** (the rung's honesty requirement). Sources under
`C:\gd\_ns_playtest\`; revert via the per-id `revert_deploy_308NN.py` scripts. New ids →
**one game RELAUNCH** needed before the first warp.

| slot | donor | seed | what to look for |
|---|---|---|---|
| **30820** | 111 — Alexandria inn, disc-1 play night | `scenario = 1152`, once-flag 3719 left clear | You are **Vivi, alone**. Walk toward the innkeeper: the **"Whaddya mean, there's no vacancies!!!?"** scene should fire (camera move + angry customer). ~ → Reload and walk again: it should REPLAY (the seed clears the once-flag every load — intended for testing). |
| **30821** | 352 — Dali inn, beat **2700** | 7 bits seeded; **2073 clear** (its window opens at 2990) | The inn during the party's Dali stay. Note the cast present and the state of the story-gated door (it reads bits 2064/2073/2078). |
| **30822** | 352 — same donor, beat **3000** | same + **2073 SET**, scenario 3000 | The SAME room, later beat. The A/B question: does anything observably differ from 30821 — the gated door, the cast, dialogue? The two tomls differ ONLY by `scenario` and bit 2073. |

Verdicts to report per slot: behaves-as-the-beat / scenario-zero-ish / wrong-or-weird (what).

Known limits going in (say so if they bite): bit **2078** is a set-AND-cleared toggle the tool
refuses to auto-seed (reported in the toml comments — if the Dali door looks wrong, that's the
first suspect); **party composition is not seeded** (rung 7) — a scene gating on a specific
cast member may silently not fire (the Ice Cavern lesson).

## Results — round 1 (owner, 2026-08-03)

- 30820 (111 @ 1152): **PASS** — the "no vacancies" scene fired. Noise: "Slot 0/Slot 1" debug
  windows — the DONOR'S OWN dev-instrumentation surfacing because the party was Zidane, not
  Vivi (the same phenomenon as the 1860 wrong-sibling case). Party is the ingredient.
- 30821 (352 @ 2700): **INCONCLUSIVE-FAIL** — slot errors, no scene/cast; Zidane-only party.
  fork-report's Party-need axis had PREDICTED exactly this ("seed [party] to the beat's cast
  or the gated scene won't fire") — the tool just didn't consume it.
- 30822 (352 @ 3000): **PASS** — observably different state (a Snot-nosed Gudo innkeeper now
  offers a room). Same bytes as 30821; only scenario + bit 2073 differ. **The seed drives
  behavior in-game — the arc's first proof.**

**Round-1 verdict: party state IS part of the beat** (the owner's call, matching the June Ice
Cavern lesson). Fixed same-day: `story-seed` now also emits `[party]` — `add` = the cast the
field both ADDS and GATES on, plus a non-Zidane donor player; required-but-never-added members
(the dormant-Quina class) are reported assert-by-hand, never auto-seeded.

## Round 2 — 30820 + 30821 redeployed with the party-aware seed (30822 untouched)

Seeds regenerated + pasted verbatim: 30820 gains `[party] add = ["vivi"]`; 30821 gains
`add = ["garnet", "steiner", "vivi", "zidane"]` (Quina correctly excluded as dormant).
~ → Reload is enough (ids already registered — no relaunch).

- 30820 re-test: **PASS** — Vivi added, scene good. Owner note: Zidane KEPT (add never
  removes) — the solo-Vivi call is the author's; the tool now prints exactly that hint
  (`[party] remove` exists for it).
- 30821 re-test @ 2700: still no scene, party correct → **the BEAT was wrong, not the party**:
  SC 2700 = "Dali (underground)" and falls BETWEEN 352's staged gates (2600-2660 inn-stay
  band, then 2790/2980/2990). An idle inn may even be faithful there. Tool fix: `story-seed
  --beats` lists the field's staged ScenarioCounter values so the author picks one.

## Round 3 — 30821 re-seeded at a STAGED beat (2650, mid inn-stay band)

Same donor, seed now `scenario = 2650` + the same 7 bits + the 4-member party.
~ → Reload. Question: does the inn now stage its beat-2650 content (cast/scene/dialogue of
the party's Dali stay) — distinct from both the empty 2700 state and 30822's Gudo state? PENDING

## Round 4 — the WRONG-SIBLING trap: 30821's donor swapped 352 -> 351

Round 3 (352 @ 2650) was still an empty room. Root cause: one FBG backs MULTIPLE field ids,
one per story VISIT (the June inn lesson repeating) -- 351 is the FIRST-VISIT Dali Inn
(villager + save moogle + props staged at every beat of the stay), 352 is the revisit shell
whose only real content is the 2990-band Gudo state. 30821 is now a verbatim fork of 351
seeded @ 2650 (tool output verbatim; no [party] block emitted -- 351 gates nothing on party).
~ -> Reload. Expect: the populated first-visit inn.
**PASS (owner, 2026-08-03): the save moogle and the SLEEPING INNKEEPER present -- the
first-visit inn at its beat.** (Owner correction folded in: not all save moogles have
barrels -- the cask is field 407's furniture, not a moogle universal.)

Deferred by owner decision (round 3): a researched ScenarioCounter -> ExpectedParty map (the
principled rung-7 answer to the byte-party problem); the adds-and-gates heuristic stands in.

## Rung-1 verdict: CLOSED ★ (all three slots owner-confirmed)

- 30820 / 111 @ 1152: the gated "no vacancies" cutscene fires; party seed silenced the donor
  debug windows.
- 30821 / 351 @ 2650: the first-visit inn staged (sleeping innkeeper + save moogle).
- 30822 / 352 @ 3000: the revisit state (Gudo offering a room) -- same-FBG A/B proven.

THE LOAD-BEARING READ FOR THE DECISION GATE: across four rounds, the bit-RESOLUTION model
never failed -- every miss was a seed-INPUT affordance (party cast, staged-beat choice,
sibling visit-id), each closed by a small tool verb (--beats, [party], fork-report). The
demand-driven seed is sufficient for single-field forks.

## Rung 2 — the ATE avail-word calibration (slot 30823) ★ PASS

`story-seed 552 --beat 3115` DETECTED the ATE availability word (byte 236) mechanically --
any word-var condition dominating the field's ATE(1) arm -- and emitted the words seed; the
one documented author step widened value 1 -> 0x0F (four menu rows). Verbatim Lindblum-552
fork at 30823: **owner-confirmed the ATE prompt was available** -- the July known-good result
reproduced through the tool path. The same detection finds Evil Forest 200's byte 236 and
Dali 351's 239/296 unaided (the doc only gestured at those).

RUNG 2 CLOSED. Detection replaced the planned hand-curated table -- strictly better: it
covers every ATE hub, not three documented regions.

## The campaign lane — an 11-field Dali chain at ONE beat (slots 30830-30840) PENDING

`import-chain 351 --verbatim --whole-zone` (11 fields, 59 in-chain gateways retargeted) then
ONE command: `story-seed --chain <dir> --beat 2650` seeded every member against its own
donor's read set. Deployed additively (per-member deploy_field --id; never the wholesale
campaign replace). **RELAUNCH once** (11 new ids), then ~ -> Warp 30831 (DL_ENT, the village
entrance; the inn is 30830, donor 351).

The question the whole arc has been building to: **walk beat-2650 Dali as a coherent place**
-- doors warp between the forks, each room staged at the same beat (villagers about, the inn's
sleeping keeper + moogle, the shop staffed). Report anything scenario-zero-ish or
beat-INCONSISTENT between rooms (the cross-room coherence is the new claim; single rooms were
rung 1).

### Chain round 1 (owner, 2026-08-03) — MOSTLY WORKING, one stock guard tripped

- My warp pointer was wrong (30831 = donor 312, the mountain OVERLOOK -- its empty-at-2650
  state + seam exits are FAITHFUL; the Dagger-naming scene lives at its own 2525-2540 window).
  The village entrance is 30840 (donor 359). id->donor map now in this doc's table above.
- **THE POSITIVE: the inn-stay cutscenes played across rooms** -- the sleep sequence carried
  the player through a RETARGETED warp into 30833 (donor 352, the morning sibling). Cross-room
  scripted flow works on the seeded chain.
- **"Error Set Scenario Counter() Old=2650 New=2600"** on waking: STOCK's own backwards-write
  debug guard. The morning script writes SC=2600 (the Dali-morning advance); our uniform 2650
  seed is LATER than that resident advance. Skip is safe (each room re-stamps its seed on
  entry). Tool fix: `story-seed --chain` now WARNS per member when a donor writes SC values
  below the seeded beat (`backwards_advance_hazards` -- reproduces this exact case: donor 352
  @ 2650 -> [2600]).
- LESSON for the study: one beat per zone is right for STANDING state; members holding
  advance SEQUENCES want a beat at-or-before their own writes (or accept the skippable guard).
