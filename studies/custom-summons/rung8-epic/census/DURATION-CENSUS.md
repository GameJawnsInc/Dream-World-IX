# THE STOCK SUMMON DURATION CENSUS

> **Round:** rung 8 (NIMBRA) post-playtest re-positioning, 2026-07-24.
> **Owner's verdict that opened it:** the cast works, but *"some of the cinematic beats hold for too
> long which reads as laggy/buggy. we can make it a shorter summon, not everyone has to be Bahamut"*
> — plus the design question: **is stock summon cinematic DURATION correlated with POWER?**
> **Shorter is unconditional** (owner's call). The power/MP move is the census-informed part.
>
> **Source:** `duration_census.py` (committable; re-runs against the install). Every number in this
> document is printed by that script — nothing here is hand-typed arithmetic.
> **Outputs:** `summon_durations.csv`, `correlations.json`, `roll_expected.json`,
> `duration_vs_power.png`.
> **Provenance:** the install's sequence text is READ to measure it. No stock bytes enter the repo —
> the artifacts are tick counts, correlations and a chart.

---

## 0. The one-paragraph answer

**Yes — for the FULL cinematic, duration tracks power (Spearman ρ = +0.84, p = 0.0023) and tracks MP
even harder (ρ = +0.86, p < 0.0001), and both survive deleting Ark.** For the SHORT cinematic there is
**no relation at all** (ρ = −0.29 without Ark): the shorts are a flat 4–12 s band regardless of power.
**But the hypothesis, while correct, is not NIMBRA's actual problem.** NIMBRA's 29.3 s is *unremarkable*
among stock FULL cinematics — it sits at the median, and Bahamut, Odin, Madeen, Fenrir-Wind and
Leviathan are all *longer*. The defect is that **NIMBRA has no short variant**, so its one cinematic
plays on **every** cast, while a stock summon fires its full cinematic only ~10% of the time. Measured
against what the player *actually watches per cast*, **NIMBRA costs 29.3 s where Bahamut costs 10.4 s —
2.8× the game's biggest Eidolon.** That is the number that reads as "laggy/buggy", and it is why the
re-positioning target is ~9 s, not ~20 s.

---

## 1. The roster

The 16 summon `BattleAbilityId`s are read verbatim out of `DecideSummonType`
(`btl_cmd.cs:1583-1615`), with values from `Memoria/Data/Battle/BattleAbilityId.cs` and rows from the
install's `Data/Battle/Actions.csv`. `animationId1` = `aa.Info.VfxIndex` = **full**;
`animationId2` = `aa.Vfx2` = **short** (the selection happens at `btl_vfx.cs:99`).

| Ability | id | full ef | short ef | power | MP | element | type | targets |
|---|---:|---:|---:|---:|---:|---|---:|---|
| Shiva | 49 | 038 | 407 | 36 | 24 | Ice | 4 | AllEnemy |
| Ifrit | 51 | 276 | 445 | 42 | 26 | Fire | 4 | AllEnemy |
| Ramuh | 53 | 186 | 415 | 32 | 22 | Thunder | 4 | AllEnemy |
| Atomos | 55 | 184 | 446 | 30 | 32 | Non-elem | 4 | AllEnemy |
| Odin | 58 | 261 | 424 | 45 | 28 | Non-elem | 4 | AllEnemy |
| Leviathan | 60 | 179 | 406 | 59 | 42 | Water | 4 | AllEnemy |
| **Bahamut** | 62 | **227** | **405** | 88 | 56 | Non-elem | 4 | AllEnemy |
| **Ark** | 64 | **381** | **447** | 106 | 80 | Shadow | 4 | AllEnemy |
| Fenrir (Earth) | 66 | 210 | 508 | 42 | 30 | Earth | 0 | AllEnemy |
| Fenrir (Wind) | 67 | 226 | 509 | 44 | 30 | Wind | 0 | AllEnemy |
| Carbuncle (Reflect) | 68 | 177 | 504 | 0 | 24 | — | 0 | AllAlly |
| Carbuncle (Haste) | 69 | 494 | 506 | 0 | 24 | — | 0 | AllAlly |
| Carbuncle (Shell) | 70 | 493 | 505 | 0 | 24 | — | 0 | AllAlly |
| Carbuncle (Vanish) | 71 | 495 | 507 | 0 | 24 | — | 0 | AllAlly |
| Phoenix | 72 | 211 | 510 | 40 | 32 | Fire | 0 | Everyone |
| Madeen | 74 | 251 | 378 | 71 | 54 | Holy | 0 | AllEnemy |
| *Rebirth Flame (Trance Phoenix)* | 73 | 225 | 225 | 30 | 0 | Non-elem | 0 | AllAlly |

**Cross-check: PASS.** The study's two known pairs (Bahamut 227/405, Ark 381/447) reproduce from the
CSV parse; the script asserts them (`KNOWN_PAIRS`).

Two roster notes worth carrying forward:

* **Rebirth Flame (id 73)** is the Trance-Phoenix auto-revive. It is *not* in `DecideSummonType` and
  its `vfx1 == vfx2 == 225`, so it has no roll and one cinematic — **exactly NIMBRA's shape today**.
  It is also the only stock ability in that shape, and at 523 ticks / 34.9 s it is a genuine outlier
  in per-cast cost. It is excluded from every correlation (power 0, MP 0 are not on either scale).
* **THE TYPE-4 MP LAW** applies to the eight `type = 4` rows only: `(Type & 4) != 0 &&
  GARNET_SUMMON_FLAG != 0` quadruples the displayed/charged MP (`AbilityUI.cs:1313`,
  `BattleHUD.cs:1282`, `btl_cmd.cs:1194`). The MP column above is the **base** cost. NIMBRA is
  `type = 0` and is unaffected — this census's MP axis is directly comparable to it.

---

## 2. The duration model, and why you can trust it

Two files per effect id:

| file | what it is |
|---|---|
| `ef###/Sequence.seq` | the **shared** (SFX-side) timeline. **This is the cinematic** — the thing the owner watched and judged. |
| `ef###/PlayerSequence.seq` | the caster lane: step forward → title plate → `MP_IDLE_TO_CHANT` → `MP_CHANT` → `MP_MAGIC` → `PlaySFX` → **`WaitSFXDone`** → step back. |

`WaitSFXDone` blocks for exactly the `Sequence.seq` runtime, so:

```
cast_ticks  =  pre_ticks (caster front matter)  +  sfx_ticks (the cinematic)  +  post_ticks
```

The walker is the **rung-4 FULL TICK MAP method generalised**: `Wait: Time=N` counts N ticks
(`BattleActionThread.cs:98-116`), TPS = 15 ⇒ 1 tick = 1/15 s, and every other main-line op is
0-tick fire-and-forget except the blocking waits. `WaitMove`/`WaitTurn` take the explicit `Time=` of
their matching `MoveToPosition`/`Turn` (always present in this corpus). `StartThread` bodies advance
the main line **only** with `Sync=True`. The one genuinely text-opaque wait is `WaitAnimation` —
its length lives in the animation asset, not the text — and it is budgeted at 5 ticks and reported
separately (`clip_waits`, `clip_uncertainty_ticks` in the CSV). **All of them sit before `PlaySFX`**
in the stock caster lane, so they shift the cast uniformly and never move the cinematic. `sfx_ticks`
— the load-bearing column — has **zero** clip uncertainty: no summon `Sequence.seq` contains a
top-level clip-bound wait.

One caster-lane shape needs explicit handling: several `PlayerSequence.seq` files put their *entire*
body inside condition-guarded top-level threads — either one `StartThread`/`ElseThread` pair (the
short variants' `Condition=CommandId != 57`) or **sibling** guarded threads (ef225's
`CasterHP == 0` / `CasterHP != 0`). Those branches are mutually exclusive, so the walker detects
"top level is nothing but guarded threads" and takes the longest branch. Without it, ef225's
`cast_ticks` reads 0 — which is how this gap was caught.

### Three independent validations, all green

| | check | result |
|---|---|---|
| **GT1** | ef227 (Bahamut Full): the model must place the stock `EffectPoint` beats where rung 4 *watched them move in game*. Rung 4 logged "stock EffectPoint at t=486/498, ~32.4 s in" (`PLAN.md:380`). | **t = 486 / 498. Exact, to the tick.** Total 547 ticks / 36.5 s — inside the 485–551 ground-truth band. |
| **GT2** | NIMBRA's own `nimbra.seq` walked by the same code. | **RE-BASED 2026-07-24 (adversarial round).** As first written this check *retyped* the pre-retime tick table (`sfx_ticks=330`, `fixed = 45+95+105+90+30+12+18` compared against its own literal `395`, band `475–495`) and so reported **FAIL** the moment the cast was re-cut — while the model itself was fine. It now reads the window from `nimbra.summon.toml` and cross-checks the walker against an **independent parser** (the kit's `summons.seqlint`). Live: fixed waits **123 = 123** (both parsers agree), total **140 ticks / 9.33 s** against a drain at 135 — STORYBOARD §11.1's own figures, re-derived rather than asserted. *(Historic: **395** fixed / **485** ticks / 32.3 s as shipped, 440 / 29.3 s as playtested.)* |
| **GT3** | **The HoldDuration oracle.** `SetBackgroundIntensity: … HoldDuration=H` self-restores after H ticks, and stock authors set H to land exactly on the *next* `SetBackgroundIntensity`. H is written in the file by the original author and is completely independent of our `Wait` arithmetic — one mis-summed `Wait` shows up as a residual. | **59 / 60 land EXACTLY**, across all 33 summon effect ids. The single residual is +1 tick in ef211 (Phoenix). |

GT3 is the strongest of the three: it is 60 independent checkpoints written by Square's own authors,
spread over 33 files, and the walker agrees with 59 of them to the tick.

**The one honest limitation:** Ark's full cinematic (1698 ticks / **113.2 s**) is far longer than
folk memory usually reports. It is not a parse artifact — all 30 of its `Wait`s are top-level (only
two `StartThread` blocks, both bare `ShiftWorld`), and its opening
`SetBackgroundIntensity: Time=14 ; HoldDuration=862` independently corroborates a >1000-tick
cinematic. Ark is flagged as the expected extreme throughout and every correlation is re-run
without it.

---

## 3. The table

Measured `Sequence.seq` runtime, both variants, TPS 15. `cast_s` includes the caster front matter.
Full data: `summon_durations.csv`.

### FULL cinematic

| summon | ef | ticks | sec | cast_s | power | MP |
|---|---:|---:|---:|---:|---:|---:|
| Carbuncle (Reflect) | 177 | 260 | 17.3 | 19.7 | 0 | 24 |
| Carbuncle (Haste) | 494 | 260 | 17.3 | 19.7 | 0 | 24 |
| Carbuncle (Shell) | 493 | 260 | 17.3 | 19.7 | 0 | 24 |
| Carbuncle (Vanish) | 495 | 260 | 17.3 | 19.7 | 0 | 24 |
| Ramuh | 186 | 331 | 22.1 | 23.7 | 32 | 22 |
| Ifrit | 276 | 351 | 23.4 | 24.4 | 42 | 26 |
| Shiva | 038 | 364 | 24.3 | 26.5 | 36 | 24 |
| Fenrir (Earth) | 210 | 422 | 28.1 | 29.8 | 42 | 30 |
| Atomos | 184 | 424 | 28.3 | 29.9 | 30 | 32 |
| Phoenix | 211 | 469 | 31.3 | 32.9 | 40 | 32 |
| Leviathan | 179 | 481 | 32.1 | 34.6 | 59 | 42 |
| Fenrir (Wind) | 226 | 485 | 32.3 | 34.0 | 44 | 30 |
| Madeen | 251 | 519 | 34.6 | 36.9 | 71 | 54 |
| *Rebirth Flame* | 225 | 523 | 34.9 | 36.5 | 30 | 0 |
| Odin | 261 | 537 | 35.8 | 37.5 | 45 | 28 |
| **Bahamut** | 227 | **547** | **36.5** | 38.1 | 88 | 56 |
| **Ark** | 381 | **1698** | **113.2** | 115.5 | 106 | 80 |

**Band (Ark excluded): 17.3 – 36.5 s, median 28.1 s.**

### SHORT cinematic

| summon | ef | ticks | sec | cast_s | power | MP |
|---|---:|---:|---:|---:|---:|---:|
| Carbuncle (Reflect) | 504 | 57 | 3.8 | 5.5 | 0 | 24 |
| Carbuncle (Shell) | 505 | 57 | 3.8 | 5.5 | 0 | 24 |
| Odin | 424 | 59 | 3.9 | 5.6 | 45 | 28 |
| Carbuncle (Vanish) | 507 | 65 | 4.3 | 6.0 | 0 | 24 |
| Carbuncle (Haste) | 506 | 73 | 4.9 | 6.5 | 0 | 24 |
| Ifrit | 445 | 77 | 5.1 | 6.8 | 42 | 26 |
| Fenrir (Earth) | 508 | 89 | 5.9 | 7.6 | 42 | 30 |
| Leviathan | 406 | 111 | 7.4 | 9.1 | 59 | 42 |
| **Bahamut** | 405 | 112 | **7.5** | 9.1 | 88 | 56 |
| Ramuh | 415 | 113 | 7.5 | 9.2 | 32 | 22 |
| Fenrir (Wind) | 509 | 119 | 7.9 | 9.6 | 44 | 30 |
| **Shiva** | 407 | **135** | **9.0** | 10.7 | 36 | 24 |
| Atomos | 446 | 165 | 11.0 | 12.7 | 30 | 32 |
| Madeen | 378 | 168 | 11.2 | 12.9 | 71 | 54 |
| Phoenix | 510 | 187 | 12.5 | 14.1 | 40 | 32 |
| **Ark** | 447 | **396** | **26.4** | 28.1 | 106 | 80 |

**Band (Ark excluded): 3.8 – 12.5 s, median 7.4 s.** The owner's guess in the brief ("if stock shorts
run 8–14 s") was close but a little high — the real band starts at 3.8 s and its median is 7.4 s.

### The correlations

Damage summons only for the power axis — Carbuncle's power 0 is a buff flag, not a weak hit, and a
zero would fabricate leverage. MP axis keeps everyone. `n` = sample size.

| variant | relation | n | Pearson r | R² | **Spearman ρ** | p |
|---|---|---:|---:|---:|---:|---:|
| **FULL** | duration vs **power** | 12 | +0.788 | 0.62 | **+0.841** | 0.0023 |
| FULL | duration vs power, **Ark removed** | 11 | +0.705 | 0.50 | **+0.793** | 0.0155 |
| **FULL** | duration vs **MP** | 16 | +0.868 | 0.75 | **+0.860** | <0.0001 |
| FULL | duration vs MP, damage only | 12 | +0.845 | 0.71 | +0.789 | 0.0006 |
| FULL | duration vs MP, **Ark removed** | 15 | +0.735 | 0.54 | **+0.829** | 0.0018 |
| **SHORT** | duration vs **power** | 12 | +0.631 | 0.40 | **+0.011** | 0.0279 |
| SHORT | duration vs power, **Ark removed** | 11 | −0.014 | 0.00 | **−0.287** | 0.9677 |
| SHORT | duration vs MP | 16 | +0.807 | 0.65 | +0.598 | 0.0002 |
| SHORT | duration vs MP, **Ark removed** | 15 | +0.461 | 0.21 | +0.511 | 0.0837 |

Fitted lines (full variant, damage summons): `seconds ≈ −6.2 + 0.814 × power`, and
`seconds ≈ −8.9 + 1.204 × MP`.

### Verdict, plainly

1. **The owner's hypothesis is RIGHT for the full cinematic.** ρ = +0.84 on power, p = 0.0023, and it
   **survives deleting Ark** (ρ = +0.79). This is not one outlier dragging a line — the rank
   correlation says the ordering itself is real. FF9 does spend screen time in proportion to power.
2. **MP is the better predictor than power** (ρ = +0.86 vs +0.84 with Ark; +0.83 vs +0.79 without).
   That makes design sense: MP is the price the player pays, and the cinematic is part of what they
   are paying for.
3. **The hypothesis is WRONG for the short cinematic.** Ark alone manufactures the apparent
   correlation; delete it and ρ goes *negative* (−0.287, p = 0.97). Bahamut's short (7.5 s, power 88)
   is *shorter* than Ramuh's (7.5 s, power 32) and *much* shorter than Phoenix's (12.5 s, power 40).
   **A short cinematic makes no power claim.** This matters for NIMBRA: it means landing in the short
   band does **not** force the power down — that choice is free, and must be justified on a different
   axis (§4).
4. **Ark is the expected extreme, confirmed and then some**: 113.2 s full / 26.4 s short. It is the
   only summon outside both bands on both variants.

---

## 4. THE PLACEMENT — where NIMBRA actually sits

### 4.1 The finding that reframes the question

Every stock summon has two cinematics *and a roll between them*, `btl_cmd.cs:1600-1614`:

```csharp
if (cmd.regist.cur.mp > cmd.aa.MP * 2) { if (Comn.random8() < 230) cmd.info.short_summon = 1; }
else                                   { if (Comn.random8() < 170) cmd.info.short_summon = 1; }
```

`Comn.random8()` is uniform on [0,255], so **P(short) = 230/256 = 89.8 %** when the caster holds more
than double the cost — the normal case for a dedicated summoner — and 170/256 = 66.4 % otherwise.
**A stock player sees Bahamut's 36.5 s cinematic about one cast in ten.**

So the honest comparison for a summon with **no** short variant is the stock **expected** duration:

| summon | full s | short s | **E[per cast], MP-rich** | E[per cast], MP-poor | power | MP | power/MP |
|---|---:|---:|---:|---:|---:|---:|---:|
| Carbuncle (Reflect) | 17.3 | 3.8 | **5.2** | 8.3 | 0 | 24 | — |
| Carbuncle (Shell) | 17.3 | 3.8 | **5.2** | 8.3 | 0 | 24 | — |
| Carbuncle (Vanish) | 17.3 | 4.3 | **5.7** | 8.7 | 0 | 24 | — |
| Carbuncle (Haste) | 17.3 | 4.9 | **6.1** | 9.1 | 0 | 24 | — |
| Ifrit | 23.4 | 5.1 | **7.0** | 11.3 | 42 | 26 | 1.61 |
| Odin | 35.8 | 3.9 | **7.2** | 14.6 | 45 | 28 | 1.61 |
| Fenrir (Earth) | 28.1 | 5.9 | **8.2** | 13.4 | 42 | 30 | 1.40 |
| Ramuh | 22.1 | 7.5 | **9.0** | 12.4 | 32 | 22 | 1.46 |
| Leviathan | 32.1 | 7.4 | **9.9** | 15.7 | 59 | 42 | 1.41 |
| Fenrir (Wind) | 32.3 | 7.9 | **10.4** | 16.1 | 44 | 30 | 1.47 |
| **Bahamut** | 36.5 | 7.5 | **10.4** | 17.2 | 88 | 56 | 1.57 |
| Shiva | 24.3 | 9.0 | **10.6** | 14.1 | 36 | 24 | 1.50 |
| Atomos | 28.3 | 11.0 | **12.8** | 16.8 | 30 | 32 | 0.94 |
| Madeen | 34.6 | 11.2 | **13.6** | 19.1 | 71 | 54 | 1.31 |
| Phoenix | 31.3 | 12.5 | **14.4** | 18.8 | 40 | 32 | 1.25 |
| **Ark** | 113.2 | 26.4 | **35.2** | 55.6 | 106 | 80 | 1.32 |

**Stock E[per cast] band (Ark excluded): 5.2 – 14.4 s, median 9.0 s.**
**Stock power/MP: min 0.94, max 1.61, mean 1.40.**

### 4.2 NIMBRA today

`bench/rung8.field.toml:96` — `vfx1 = 91, vfx2 = 91, type = 0, power = 62, mp = 24`, and the block's
own comment states the intent exactly: *"vfx1 plays IN FULL on every cast, structurally, not by luck"*
(a minted `BattleCommandId` never enters `DecideSummonType`, and `AllEnemy(8)` is never the `ManyAny`
arm at `btl_vfx.cs:99`). That was the right call for **proving** the cinematic. It is precisely what
makes it expensive to **play**.

| axis | NIMBRA | stock comparison | verdict |
|---|---|---|---|
| Full-cinematic length | 29.3 s | band 17.3–36.5, median 28.1 | **normal.** Bahamut/Odin/Madeen/Fenrir-W/Leviathan are all longer. |
| **Per-cast length** | **29.3 s** | band 5.2–14.4, median 9.0 | **off the scale — longer than 100 % of stock expected casts, 2.8× Bahamut's 10.4 s.** |
| duration vs the full-line fit | 29.3 s at power 62 | fit `−6.2 + 0.814 × power` predicts **44.3 s** | if anything **short** for its power. The full line is not where the problem is. |
| **power/MP** | **2.58** | 0.94 – 1.61, mean 1.40 | **60 % above the most aggressive stock ratio.** Leviathan-tier power (59) at Ramuh-tier price. |

So there are **two** independent over-tunings, and neither is the one the brief guessed:
**(a)** the cinematic is fine in isolation but plays 10× too often, and **(b)** power-per-MP is off
the game's line by 60 %, entirely independent of duration.

Iviv boots 80 MP ÷ 24 MP = **3 casts**, so a single fight can spend ~88 s in NIMBRA. STORYBOARD §7 R17
already flagged this shape as a playtest risk ("a repeatable ability front-loads ~9.3 s of near-static
blackout… up to ~28 s of a single battle on this stretch alone"). **The playtest confirmed R17.**

### 4.3 The build constraint that shapes the candidates

Not all ticks are equally cheap to cut. STORYBOARD §7 R2 / §7.3:

* **Before `PlaySFX` (P0/P1) is FREE.** Trimming there shifts the whole cast uniformly and touches
  neither clock — no manifest, curve, playlist or alignment edit. This is the R2 knob already spent
  once (P1 `95 → 50`).
* **After `PlaySFX` is NOT.** Everything from P2 on lives inside the `.sfxmodel` manifest's pinned
  `start = 0 / end = 330` window (`nimbra.summon.toml:43-44`). Shortening it means re-cutting the
  manifest, the movement curves **and** the playlist `speed` divisors. §7.3 retracted an earlier P3
  trim for exactly this reason.

Two floors follow, both computed by the script:

* **FREE-TRIM FLOOR = 355 ticks / 23.7 s** (20 pre + the untouchable 330-tick manifest window + 5
  tail). *Nothing below 23.7 s is reachable without re-cutting the manifest.*
* **STRUCTURAL FLOOR = 75 ticks / 5.0 s.** P4 cannot go below **50 ticks**: the relight is
  `SetBackgroundIntensity: Intensity=1 ; Time=18` and **THE FIGURE-VISIBILITY LAW** (minted by rung 4)
  requires both `EffectPoint`s to fire ≥12 ticks after it completes, or the damage numbers render
  washed out under the overlay. 18 relight + 12 settle → `EP Effect` → 12 → `EP Figure` → 8 tail = 50.

### 4.4 Three candidates

| | name | ticks | sec | power | MP | power/MP | vs stock E[cast] | manifest re-cut? |
|---|---|---:|---:|---:|---:|---:|---|---|
| **A** | **THE WHISPER** | **140** | **9.3** | **34** | **24** | **1.42** | longer than 53 % — dead centre | **yes** (`end` 330 → 110) |
| B | THE FREE TRIM | 355 | 23.7 | 45 | 32 | 1.41 | longer than 100 % | no |
| C | THE SIGH | 100 | 6.7 | 30 | 20 | 1.50 | longer than 27 % | yes (`end` → 75) |

**A — THE WHISPER. ★ RECOMMENDED.**
9.3 s is the stock expected-cast **median** (9.0 s) and sits inside the short band (3.8–12.5). Power 34
lands between Ramuh (32) and Shiva (36) — honestly the weak tier — and 34/24 = **1.42** is the stock
mean power/MP (1.40) to two decimals. MP stays 24, so Iviv still gets 3 casts and nothing else on the
bench moves. Phase budget that sums exactly and respects the P4 floor:

```
pre (clip 10 + blackout ramp 10 + gather 5)      25
manifest window (end = 330 -> 110):
    P2  THE COALESCE   rise                      25
    P3  THE DRIFT      the look   <- the identity 25
    P4  THE STRIKE     (law floor)                50
    P5  THE DISSOLVE                              10
tail                                               5
                                                 ---
                                                 140  = 9.3 s
```

**Does the eerie identity survive at 9.3 s? The census says yes, and names the proof:
`Shiva__Short` is 135 ticks / 9.0 s** — within 5 ticks of candidate A — and it still reads as Shiva
arriving, freezing the field and leaving. FF9 itself demonstrates that a full summon beat lands in
this budget. And per §3 verdict 3, a short cinematic carries **no** power claim, so nothing about the
9.3 s length forces the power down; power 34 is chosen on the power/MP line, not on the duration line.
The one beat that must not be sacrificed is **P3, the look** — it is NIMBRA's signature, and it keeps
25 ticks (18 % of the cast, versus 20 % in the shipped build). What actually gets cut is the thing the
owner felt: P0+P1's 105-tick near-static blackout collapses to 15.

**B — THE FREE TRIM.** The zero-risk build: trim only pre-`PlaySFX`, touch no manifest, no curve, no
playlist. **But be honest about it — it does not fix the complaint.** 23.7 s is still longer than
100 % of stock expected casts and still 2.3× Bahamut; it is a 19 % cut off a cast the owner already
called too long. Take it only as a stopgap if the manifest re-cut cannot land this round.

**C — THE SIGH.** 6.7 s is deep in the short band and cheapest of all, but the law-bound P4 floor (50)
plus pre/tail (25) leaves **25 ticks total for rise + look** — about 1.7 s for the creature to emerge,
hang and be looked at. **The identity does not survive it.** Documented for completeness; not
recommended.

### 4.5 The recommendation

> **Take candidate A: 140 ticks / 9.3 s, power 34, MP 24, `type = 0`, element Dark, `AllEnemy`.**
>
> It puts NIMBRA at the stock per-cast median, on the stock power/MP line, in the weak tier the owner
> asked for, at a length FF9 itself proves sufficient (`Shiva__Short`, 9.0 s) — and the beat it
> spends its cuts on is the one the playtest complained about.

---

## 5. A lead, recorded not taken: give NIMBRA a real short variant

The structurally *most* faithful fix is not to shorten one cinematic — it is to author the **pair**
FF9 always ships, and let the roll do the work. That would let NIMBRA keep a long, proud full
cinematic for the ~10 % of casts that earn it.

The mechanism exists but is **unverified and out of scope this round**: `cmd.info.short_summon` is
writable from a battle script (`btl_scrp.cs:162`, case 1021) and Memoria exposes it as
`BattleCommand.IsShortSummon` / `MutableBattleCommand` (`BattleCommand.cs:119-120`,
`MutableBattleCommand.cs:118`) — i.e. potentially reachable from a mod Scripts-DLL `[BattleScript]`
with no engine rebuild. **The risk to check first is ORDERING:** `SelectCommandVfx` runs at
command-set time and a `[BattleScript]` runs at damage-calc time, so the write may land *after* the
vfx has already been chosen. Verify that before costing the work.

> **✔ TAKEN + RESOLVED 2026-07-24 (the short/full roll round).** The ordering fear was correct for the
> `[BattleScript]` route (damage-calc runs after the vfx pick — dead as suspected), but a strictly
> earlier data-driven route exists: an **AbilityFeatures Command-trigger** writing NCalc `IsShortSummon`
> (`CharacterAbilityGems.cs:821` — stock Boost's own mechanism, inverted) at `CMD_MODE_SELECT_VFX`,
> before the pick. The kit's `[[summon]]` block now emits it from a `roll_mp`/`roll_command`/
> `roll_ability` trio; the WHISPER became the SHORT (vfx2) and FULL-STORYBOARD's 23.0 s composition the
> FULL (vfx1, ef080). Also learned en route: a SHORT cast deals **2/3 damage** (`BattleCalculator.cs:515`)
> — so this census's power/MP tuning axis (§4.4) needs no retune, sticker powers are full-cast powers
> for stock eidolons too. → FULL-STORYBOARD §7.4, the bench block, `summons/deploy.py`.

---

## 6. Reproducing

```
cd studies/custom-summons/rung8-epic/census
py duration_census.py --validate     # just re-prove GT1/GT2/GT3
py duration_census.py --chart        # full census + duration_vs_power.png
```

Reads `Data/SpecialEffects/ef###/{Player,}Sequence.seq` and `Data/Battle/Actions.csv` from the install
(override with `FF9_GAME_DIR`). Read-only: it writes nothing outside this folder and touches nothing
in the game directory.
