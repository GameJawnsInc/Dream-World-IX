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
| 1 | THE FIRST MEAL — one Sim (VIV), one need, one stove, one directive menu, HUD | none (wiring) | **BUILT + DEPLOYED (30430), ⚠ playtest pending** — does the number move and does the Sim go? |
| 2 | five needs, ~6 objects, priority-branch autonomy, the day clock, speed control | none | alive when you stop directing it? |
| 3 | `pick` — argmax autonomy; A/B vs rung 2 | `pick` | visibly smarter? if not, DROP it |
| 4 | failure states, mood, emote; readout upgrade (`[TBLE]` words / gauge bridge) | `[TBLE]` lane, gauge `source` | is failing funny? |
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

## Rung 1 — BUILT + DEPLOYED (2026-08-14), ⚠ playtest pending

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

## Bench

**Ids 30430-30435** (30426-30499 is the free band; 30400-30425 is the standing
behavior/minigame family; do NOT take 30600+ — WINSTYLE/lock/multiwindow live
there even when absent from the live DictionaryPatch). Re-verify the live file
before minting. Bench generator: `studies/sims/sims_bench.py` (pure product
path — TOML → `deploy_field --id`), one rung at a time.

Deploy: `py tools/deploy_field.py <toml> --id 30430` (always `--id`; never pin
id in `.ff9deploy.toml`). First deploy of a new id = RELAUNCH; after that
`~ → Reload`. Sim every bench offline first (`behaviorsim` — an instrument,
not proof). Keep bench print strings ASCII (cp1252 console).
