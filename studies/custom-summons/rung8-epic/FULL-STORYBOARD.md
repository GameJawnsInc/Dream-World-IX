# NIMBRA — **THE FULL CINEMATIC** (the rare roll)

> **What this is.** `nimbra.seq` (140 ticks / 9.3 s, ★ playtest-approved as CAST 2, *"much tighter"*)
> becomes **THE SHORT** — the common roll. This document composes the **FULL** — the rare roll — and
> `nimbra_full.seq` is its binding artefact.
>
> **Contract chain:** [`STORYBOARD.md`](STORYBOARD.md) §§1-10 (the creature, the laws, the wiring),
> §11 (THE RETIME + §11.9 THE SPEED-DIVISOR DEFECT), [`census/DURATION-CENSUS.md`](census/DURATION-CENSUS.md)
> (the duration-power line, §5's recorded-not-taken *"give NIMBRA a real short variant"* lead — **this
> document takes the other half of it**), [`RUNBOOK.md`](RUNBOOK.md) (CAST 1's *"laggy/buggy"* verdict,
> CAST 2's approval).
>
> **Status: COMPOSED + OFFLINE-VALIDATED. Nothing deployed, nothing minted, no existing file touched.**
> This round created exactly two files: this one and `nimbra_full.seq`. Written 2026-07-24.
>
> **THE ONE RULE THIS DOCUMENT WAS WRITTEN AGAINST:** cast 1's defect was *beats that HOLD*. A full
> earns its length with **more composed content**, never with longer holds. Every tick added below buys
> a new event, a new clip beat, a new mist wave or a new lateral move — the longest single `Wait` in the
> whole cast is 58 ticks (3.9 s) and the creature is animating and travelling through all of it.

---

## 1. THE DURATION TARGET — from the census, re-derived not retyped

### 1.1 The line

The census's headline relation is **FULL-cinematic duration vs power, Spearman ρ = +0.84, p = 0.0023**,
and it survives deleting Ark (ρ = +0.79). Both least-squares forms were **re-fitted from
`census/summon_durations.csv` for this round** rather than copied out of the prose — they reproduce
`correlations.json` to the printed digit:

| form | n | fit | Pearson r | R² | **predicted at power 34** |
|---|---:|---|---:|---:|---:|
| damage summons, **with Ark** (the census headline) | 12 | `s = −6.226 + 0.8135 × power` | +0.788 | 0.62 | **21.43 s** (322 ticks) |
| damage summons, **Ark deleted** (the census's robustness form) | 11 | `s = 20.243 + 0.2004 × power` | +0.705 | 0.50 | **27.06 s** (406 ticks) |

### 1.2 The sanity anchors — the two power-neighbours

NIMBRA is **power 34**, which falls strictly between two real summons:

| anchor | power | FULL ticks | FULL sec |
|---|---:|---:|---:|
| **Ramuh** | 32 | 331 | **22.07** |
| **Shiva** | 36 | 364 | **24.27** |

Linear interpolation between the two anchors at power 34: **23.17 s (347.6 ticks)**.

### 1.3 ▶ THE TARGET: **345 ticks = 23.00 s**

**Justification.** The two regressions *bracket* the answer rather than agreeing on it — 21.4 s with Ark,
27.1 s without — and the disagreement is diagnostic, not noise: deleting the power-106 / 113.2 s point
removes essentially all of the x-leverage, so the Ark-deleted line collapses to an intercept-dominated
slope of 0.2004 that over-predicts the weak end (it would put a power-0 Carbuncle at 20.2 s against a
measured 17.3 s), while the with-Ark line under-predicts it (−6.2 s at power 0, which is not a duration).
At **power 34 the honest instrument is not either line but the two anchors that bracket it**: ρ = +0.84
is a *rank* relation, and the rank statement for a summon between Ramuh (32) and Shiva (36) is that its
full should land between their fulls — 331 and 364 ticks. **345 is on that segment** (4 ticks off the
interpolation, chosen because 345 = 23.00 s exactly *and* because it lands every playlist entry on a
clip boundary, §4). It sits inside both regression predictions, below the FULL band's median (28.1 s)
and above its floor (17.3 s) — the weak tier the owner asked for — and its **FULL/SHORT ratio is
345/140 = 2.46**, inside the stock spread (Phoenix 2.51, Atomos 2.57, Shiva 2.70, Ramuh 2.93; Bahamut's
4.88 is the outlier). The decisive check is the one CAST 2 was won on: under FF9's own roll
(`btl_cmd.cs:1600`, P(short) = 230/256 = 89.84 % for an MP-rich caster) the **expected per-cast cost
becomes 10.72 s** — inside the stock expected-cast band 5.2–14.4 s, between Bahamut (10.4) and Shiva
(10.6), and 13.92 s on the MP-poor roll (stock band 8.3–19.1, between Ramuh 12.4 and Shiva 14.1).
**Adding this full does not re-open the defect the retime closed.**

> **What the target is NOT justified by.** Census §3 verdict 3: a *short* cinematic makes no power
> claim (ρ = −0.29 without Ark). The short stays 140 ticks and **power stays 34** — the 23 s is derived
> from the FULL line only, and nothing here touches `power`, `mp`, `type`, `element` or `targets`.

---

## 2. THE BINDING LAWS, AND WHICH BEAT EACH ONE PINS

| Law | Source | What it pins in this cast |
|---|---|---|
| **THE SPEED-DIVISOR DEFECT** | STORYBOARD §11.9, `SFXDataMesh.cs:869` | **Every playlist entry is `speed = 1`.** Beat length comes from the clip's own frame count, never from a divisor. Verified by `playlist_sim.py`: all six entries *"never over-run"*. |
| **THE PHASE-LOCK RULE** | STORYBOARD §3 | Between `PlaySFX` (t 55) and `WaitSFXDone` every wait is a fixed `Wait: Time=N`. The only clip-bound waits are the two `WaitAnimation`s at the very top, before the manifest clock exists. |
| **THE PLAYLIST-SEAM RULE** | STORYBOARD §1.7 | Six entries chain with no blending; every seam is a shared-rest-pose seam because all four shipped clips open and close on it. |
| **THE ANIMATION-PLAYLIST LAW** | rung 7 | Playlist 295 ticks ≥ the 260-tick window ⇒ never exhausted, never freezes on a last frame. |
| **THE FIGURE-VISIBILITY LAW** | rung 4 | Relight `Intensity=1 ; Time=18` fires at t 263 and completes at t 281; `EffectPoint: Type=Effect` at **t 293** is the 12-tick floor exactly; `Type=Figure` at t 305. |
| **THE INTENSITY SUBTLETY LAW** | rung 6, STORYBOARD §2.5 | Only `Intensity=0` and `Intensity=1` are used. The ramp `Time` is the expressive knob: **25** into the dark (slower than the short's 10, faster than the rejected 45), **18** back out. |
| **THE ANIM=IDLE RELEASE LAW** | rung 6 | The cast closes on `PlayAnimation: Char=Caster ; Anim=Idle`. |
| **THE MULTI-TARGET NULL** | `SFXData.cs:149` | The creature anchors on `TargetAveragePosition*` (`anchor = "target_average"`). `TargetPosition*` would be 0 on an `AllEnemy` cast. |
| **THE AVERAGE-POSITION SPLIT** | STORYBOARD §3.3 | The particles are spawned by `CreateVisualEffect`, where the per-instance `Char=` target *is* valid — so `MistFloor`/`MistWisps`/`RiftFlash` keep their own `TargetPosition*` anchoring unchanged. |
| **THE TOTAL-LIFE FORMULA** | STORYBOARD §4 | Wave scheduling (§5) is computed as *last emission frame + Duration*, read out of the shipped files: MistFloor **28 + 44 = 72**, MistWisps **18 + 22 = 40**, RiftFlash **3 + 30 = 33**. |
| **THE TURNING SPLIT** | `seqlint.FBX_INTERPOLATIONS` | No `Turning1`/`Turning2` anywhere in the creature curves — the FBX render path passes `customParam = null` and it is an NRE per render frame. The circling pass (§4.3) is built from `Sinus`, not from an orbit. |
| **`PlayCamera` is a hard no-op / `ShiftWorld` is refused** | STORYBOARD §2 | Neither appears. The full is composed for the fixed default battle camera, exactly as the short is. |
| **R15** | STORYBOARD §7.1 | No `Sequence.seq` is ever written into the effect folder; `PlaySFX` carries `SkipSequence=True` anyway. |

---

## 3. THE BEAT TABLE

**Clock:** `BattleTPS = 15` ⇒ 1 tick = 1/15 s. Absolute ticks include the ~10-tick budget for the two
clip-bound `WaitAnimation`s at the top (STORYBOARD §3.1's convention; that slack sits *before* `PlaySFX`
and shifts every phase uniformly, so it never touches the two-clock alignment). **`PlaySFX` at t = 55;
manifest window `Start = 0 / End = 260` ⇒ the instance drains at t = 315.**

| # | Beat | Abs ticks | Sec | Playlist entry (manifest frames) | Op intent | Constrained by |
|---|---|---|---:|---|---|---|
| **P0** | **THE HUSH** | 0 → 35 | 2.3 | — | Title plate, the caster bows into the chant, the summon aura, the drone. The arena slides to black over **25 ticks** — and the floor pall fires on the **same tick as the dim**, so the mist arrives *through* the darkening (the retime's own overlap discovery, kept). | INTENSITY LAW (destination 0); the 2 clip-bound waits live here and nowhere else |
| **P1** | **THE GATHER** | 35 → 55 | 1.3 | — | Full black. The wisps peel up off the pall and the whisper swell rises. **20 ticks, not the rejected 95** — long enough to read as a gathering, short enough that it is an arrival and not a hold. | R17 (the cast-1 defect): a gather is content, a wait is not |
| **P2** | **THE COALESCE** | 55 → 75 | 1.3 | `emerge` **0 → 15** (t 55-70) | **Manifest frame 0.** NIMBRA rises out of the mist from below the frame: Movement (−900 → +120), Scaling (0.15 → 1.00) and the `emerge` clip all run the same 15 ticks — the rise, the growth and the unfurl are one gesture. Then it is simply *there*, at full height, for 5 ticks before it moves. | SPEED-DIVISOR (emerge N=15 @ 1); R3 (the `CreateModel` hitch hides inside 45 ticks of full black, up from the short's 15) |
| **P3** | **THE CIRCLING DRIFT** | 75 → 145 | 4.7 | `drift` **15 → 90** (t 70-145) | The full's first new beat. One complete 75-frame sway cycle at the authored eerie half-speed while the creature **travels** — Movement carries it 160 u to stage-left and 60 u back, Rotation yaws it 12° into its own travel. A wisp wave peels off it at t 75; the pall rolls back in under it at t 110. It has not attacked and it is not yet looking. | PLAYLIST-SEAM (rest-pose seam at frame 15); the short could not afford this entry at all |
| **P4** | **THE LOOK** | 145 → 170 | 1.7 | `driftlook` **90 → 115** (t 145-170) | **The identity beat, byte-for-byte the short's.** It stops travelling, and the mask turns 24° across to 12° off square. A fresh wisp wave rises around it. The census protected 25 ticks for this in a 140-tick cast; it gets the same 25 here — a beat that works is not re-cut because there is room. | PLAYLIST-SEAM; §11.10 watch-item 1 (the look's tempo) inherited deliberately unchanged |
| **P5** | **THE SECOND GATHERING** | 170 → 245 | 5.0 | `drift` **115 → 190** (t 170-245) | The full's second new beat, and the one that makes it a *composition*: **the caster causes it.** `StopChannel` + `MP_MAGIC` at t 170 — Iviv commits the gesture — and the whisper swell answers, a second pall + wisp wave rolls in at t 205, and NIMBRA drifts back across the line (160 u to stage-right, 80 u forward) still turned away. The mist thickens toward the blow instead of waiting for it. | PHASE-LOCK (fixed waits only); THE ONE-WAVE INVARIANT (§5) |
| **P6** | **THE WIND-BACK** | 245 → 263 | 1.2 | `strike` **190 → 208** (t 245-263) | The arms draw up and behind, the mask tips down. **THE 18-TICK LEAD** (STORYBOARD §11.2), carried verbatim: the `strike` entry opens 18 ticks before the blow so its lunge peak lands *on* the flash. The wisps are already gone (last wave died at t 245) — only the pall is left, being drawn in. | THE 18-TICK LEAD; verified by `playlist_sim.py`, not asserted |
| **P7** | **THE STRIKE** | 263 → 313 | 3.3 | `strike` **208 → 220**, then `drift` **220 →** | **t 263 is the lunge peak.** Sting + `RiftFlash` + `Intensity=1 ; Time=18` all fire on it: the light returning *is* the impact. Ramp completes t 281; damage at **t 293** (the 12-tick floor, exactly), figures at t 305. The dissolve is already running under both. | FIGURE-VISIBILITY (the law floor, 30/12/8 = 50 ticks, unchanged from the approved short) |
| **P8** | **THE DISSOLVE** | 275 → 315 | 2.7 | `drift` **220 → 260 (cut)** | Scaling piece 3 runs manifest frames 220-260 — it begins **on the `strike` → `drift` seam**, so the settle ends and the vent begins on the same frame. The body thins to a thread while stretching upward; a wisp wave peels off it at t 293, with the damage numbers. 40 ticks against the short's 25 — this is *the* beat the brief asked to spend on. | ANIMATION-PLAYLIST LAW (the tail entry is cut at 260 of 295, never exhausted) |
| **P9** | **THE BREATH + RELEASE** | 315 → 345 | 2.0 | — (instance drained) | `WaitSFXDone` resolves at the drain (t 315) and then **25 ticks of nothing but a lit, empty arena** with the last dissolve wisps trailing out at t 333 and the drone's own fade-out dying at t 325. *Then* the release. **This is §11.10 watch-item 3 answered** — the short's "no breath after the dissolve, the end reads as a cut" is exactly what a full has the budget to fix. | ANIM=IDLE RELEASE LAW; the breath sits after the drain, where no manifest clock exists — the one place a `Wait` is still free |

---

## 4. THE TWO CLOCKS

### 4.1 The window

`PlaySFX` at **t = 55** ⇒ manifest frame 0 = t 55. **`Start = 0`, `End = 260`** ⇒ the instance drains at
**t = 315**, the tick `WaitSFXDone` is authored to resolve on (it blocks 2 ticks, from t 313).

### 4.2 The playlist — six entries, **every one at `speed = 1`**

Only the four clips that **ship on disk today** are referenced (`creature/nimbra/CLIPS.json`, re-read for
this round): `emerge` **N=15**, `drift` **N=75**, `strike` **N=30**, `driftlook` **N=25**, all authored at
30 fps. *(STORYBOARD §11 mentions an original uncut 90-frame `emerge`; it does **not** ship — §11.9
resampled it onto 15 frames and `CLIPS.json` is the truth. Nothing new is minted this round, so the
composition is built from these four.)*

| # | Entry | N | Speed | Manifest frames | Abs ticks | Beat |
|---:|---|---:|---:|---|---|---|
| 1 | `emerge` | 15 | 1 | 0 → 15 | 55 → 70 | the rise |
| 2 | `drift` | 75 | 1 | 15 → 90 | 70 → 145 | **the circling drift** (new) |
| 3 | `driftlook` | 25 | 1 | 90 → 115 | 145 → 170 | **THE LOOK** |
| 4 | `drift` | 75 | 1 | 115 → 190 | 170 → 245 | **the second gathering** (new) |
| 5 | `strike` | 30 | 1 | 190 → 220 | 245 → 275 | wind-back 245-263, **LUNGE PEAK t 263**, settle |
| 6 | `drift` | 75 | 1 | 220 → **260 (cut)** | 275 → 315 | the dissolve sway |

**Playlist 15+75+25+75+30+75 = 295 ≥ 260** ⇒ never exhausted. `playlist_sim.py` reports all six entries
*"never over-runs"* and puts the lunge peak — the `strike` envelope's authored `(36, 1.0)` breakpoint,
which rescales to clip frame 36 × 29/59 = **17.695** on the shipped 30-frame clip — at **t 263**, the exact
tick `nimbra_full.seq` fires the sting, the flash and the relight. Verdict `OK` (§9).

Two of the six entry boundaries land on `.seq` op boundaries by construction: **frame 90 = t 145** (THE
LOOK's ops), **frame 115 = t 170** (the second gathering's ops). A third, **frame 220 = t 275**, aligns
only manifest-internally — the playlist seam meets the dissolve Scaling piece-3 seam; the nearest `.seq`
ops sit at t 263 and t 293 (adversarial re-walk, 2026-07-24).

### 4.3 The curves (the `[summon.staging]` spec)

Each curve must sum to `end − start` = **260** — STORYBOARD §7.3's lesson in force: *no edit after
`PlaySFX` is free*, so the window, all three curves and the playlist were composed **together**.
`A* = TargetAveragePosition*`; the Y offsets are absolute ground-plane heights (`BTL_VFX_REQ.cs:88` hard-zeroes
`trgcpos.vy`).

**Movement** — the rise, then a real lateral **pass** across the enemy line (this is the "circling" the
brief asked for; a literal orbit is impossible because `Turning1/2` NRE on an FBX curve, so the pass is
built from `Sinus` on X and Z):

| piece | dur | → destination (offset from `A*`) | ease X / Y / Z | beat |
|---:|---:|---|---|---|
| 1 | 15 | `(0, 120, 0)` from `(0, −900, 0)` | Linear / **SinusOut** / Linear | the rise |
| 2 | 75 | `(−160, 160, 60)` | Sinus / Sinus / Sinus | the drift, out to stage-left |
| 3 | 25 | `(−160, 170, 60)` | Constant / Sinus / Constant | **THE LOOK — it stops travelling and turns** |
| 4 | 75 | `(+160, 180, −80)` | Sinus / Sinus / Sinus | the pass completes, back across to stage-right |
| 5 | 30 | `(0, 190, 0)` | SinusOut / Sinus / SinusOut | it squares to the line for the blow |
| 6 | 40 | `(0, 200, 0)` | Constant / Sinus / Constant | the dissolve's upward vent |

> **The X/Z pass is the one unproven staging number in this round, and it is a one-line revert.** The
> approved short never moves laterally (X = Z = 0 throughout), so ±160 u X / ±80 u Z on a 1400 u creature
> in front of a fixed camera has no in-game precedent. It is ~11 % of the creature's height — deliberately
> the smallest travel that reads as travel. **If cast 1 of the full shows NIMBRA clipping frame or reading
> as sliding rather than drifting, set every X and Z destination to 0** and the staging is bit-for-bit the
> proven short's, at the cost of the pass. Recast-only, no re-export.

**Rotation** — absolute euler, raw to `eulerAngles`, baseline `(0, 180, 180)` (THE ROTATION BASELINE LAW):

| piece | dur | → destination | ease Y | beat |
|---:|---:|---|---|---|
| 1 | 15 | `(0, 180, 180)` | Constant | square through the rise |
| 2 | 75 | `(0, 192, 180)` | Sinus | yaws into its own travel |
| 3 | 25 | `(0, 168, 180)` | Sinus | **THE LOOK** — 24° across, ending 12° off square (the short's own figure) |
| 4 | 75 | `(0, 164, 180)` | Sinus | stays turned away through the second gathering |
| 5 | 30 | `(0, 180, 180)` | **SinusOut** | squares up through the wind-back |
| 6 | 40 | `(0, 180, 180)` | Constant | holds square through the dissolve |

> **The number, computed rather than claimed** (the short's §11.2 correction, honoured): `Factor2` for
> `SinusOut` is `sin(½π · cur/max)` (`ParametricMovement.cs:309`). Piece 5 spans 30 ticks and the lunge is
> **18** ticks in ⇒ `sin(½π × 0.6) = 0.809` ⇒ 12.94° of the 16° recovered ⇒ **Y ≈ 176.9°, i.e. 3.1° off
> square when the blow lands** (the short's equivalent figure was 7.3°). It still drives *through* the last
> of the turn, which is the intended read.

**Scaling**:

| piece | dur | → destination | ease | beat |
|---:|---:|---|---|---|
| 1 | 15 | `1.00` from `0.15` | SinusOut ×3 | the approach — an approach without a camera move |
| 2 | 205 | `1.00` | Constant ×3 | full height for the drift, the look, the gathering, the blow |
| 3 | 40 | `(0.02, 1.70, 0.02)` | SinusIn / SinusOut / SinusIn | **THE DISSOLVE**, frames 220-260 = t 275-315 |

Σ move = 15+75+25+75+30+40 = **260** ✓ Σ turn = 15+75+25+75+30+40 = **260** ✓ Σ scale = 15+205+40 = **260** ✓

---

## 5. THE PARTICLE + AUDIO SCHEDULE — where the extra length actually goes

The three particle models and the three audio cues were all **re-cut for a 140-tick cast** (§11.5) and are
**not editable this round**. A 345-tick cast therefore cannot be covered by one spawn of anything — and
that constraint is the composition's friend: coverage has to be bought with **re-spawns**, i.e. with
events, which is exactly what "more content, not longer holds" means.

### 5.1 THE ONE-WAVE INVARIANT (new, and it is a perf budget)

> **At most one `MistFloor` instance and one `MistWisps` instance are ever alive at the same time.**

Per-spawn lifetimes read out of the shipped JSON via THE TOTAL-LIFE FORMULA: `MistFloor` = last emission
28 + `Duration` 44 = **72 ticks**; `MistWisps` = 18 + 22 = **40 ticks**; `RiftFlash` = 3 + 30 = **33 ticks**.
`Char=Everyone` spawns one instance per combatant, so a wave is ~8×6 = 48 (floor) or ~7×6 = 42 (wisps)
billboards. The invariant therefore holds the full's **peak concurrent billboard count at ≈ 90 — the exact
figure the approved short measured** (§11.5), against the 180 of the cast-1 build that R13 flagged as
unmeasured. A longer cast costs nothing in draw volume.

| Wave | Spawns at | Dies at | What it is |
|---|---:|---:|---|
| `MistFloor` #1 | 10 | 82 | the pall gathers under the dim; NIMBRA rises **out of** it |
| `MistFloor` #2 | 110 | 182 | it rolls back in under the circling drift, and under THE LOOK |
| `MistFloor` #3 | 205 | 277 | the second gathering — and it **burns off 4 ticks before the relight completes** (t 281), so the mist is drawn in exactly as the light returns (§11.5's stated intent, delivered here by the schedule) |
| `MistWisps` #1 | 35 | 75 | the gather: wisps peel up off the pall while the whisper swell rises |
| `MistWisps` #2 | 75 | 115 | wisps trail off the newly-risen creature |
| `MistWisps` #3 | 145 | 185 | they rise around it during THE LOOK |
| `MistWisps` #4 | 205 | 245 | the second gathering thickens — and they are **gone by the wind-back** |
| `MistWisps` #5 | 293 | 333 | the dissolve, riding the damage window and trailing into THE BREATH |
| `RiftFlash` | 263 | 296 | the blow, on every target |

The two gaps in floor coverage (82→110 and 182→205) are **deliberate**: each wave fades in and out on its
own colour curve, so what the schedule produces is a pall that *breathes* — rolls in, thins, rolls back —
rather than a static layer. The one moment with the least on screen is by design the tail of the second
gathering, immediately before the blow.

### 5.2 The audio bed

The drone (**100001**) is an 8.0 s master = **120 ticks**, fade-in 1.5 s / fade-out 2.0 s. One `PlaySound`
covers 8.3 s of a 23 s cast, so the bed is **re-fired twice**, each time inside the previous voice's own
fade-out — a genuine crossfade, not a restart:

| cue | fires at | runs to | note |
|---|---:|---:|---|
| 100001 drone #1 | 10 | 130 | fade-out 100→130 |
| 100001 drone #2 | 110 | 230 | fade-in 110→132 crosses #1's fade-out |
| 100001 drone #3 | 205 | 325 | fade-in 205→227 crosses #2's fade-out; **its own fade-out dies inside THE BREATH**, leaving ~15 ticks of true silence before the release |
| 100002 whispers #1 | 35 | 95 | the gather |
| 100002 whispers #2 | 170 | 230 | **the second gathering** — the swell answers the caster's `MP_MAGIC` |
| 100003 strike | 263 | 293 | the sting, ringing out onto the damage tick |
| `StopSound` 100001 | 340 | — | safety only: every drone voice has already ended naturally at 325 |

**The no-limiter budget (R6) is not regressed.** At most two drone voices overlap and only inside each
other's fade regions (worst sum ≈ 0.95 of one voice, ≈ 0.21 after `Volume=0.55`). At the blow the stack is
**drone + sting** only — 0.221 + 0.353 ≈ 0.57 — identical to the approved short, because the whisper cue
ends at t 230, 33 ticks before the sting.

---

## 6. THE DURATION LEDGER

| Component | Ticks |
|---|---:|
| clip-bound waits (2 × `WaitAnimation`, before `PlaySFX`; the cast's only uncertainty, ±10) | **10** |
| fixed `Wait` — pre-`PlaySFX` (25 + 20) | **45** |
| fixed `Wait` — inside the window (20+35+35+25+35+58+30+12+8) | **258** |
| `WaitSFXDone` residual block (window 260 − 258 in-window waits) | **2** |
| fixed `Wait` — **THE BREATH**, after the drain | **25** |
| release `Turn: Time=5` | **5** |
| **TOTAL** | **345 ≈ 23.00 s** |

Fixed-`Wait` total = 45 + 258 + 25 = **328** (the number `seqlint` reports). Cross-check against §1.3's
target: **345 ticks / 15 = 23.00 s** ✓, and against the window: `PlaySFX` 55 + 260 = **315 = the drain**,
which is the tick `WaitSFXDone` is authored to resolve on ✓.

**Where the 205 extra ticks over the short went** — and none of them into a hold:

| Beat | short | full | bought |
|---|---:|---:|---|
| the dim + the gather | 25 | 55 | a 25-tick ramp instead of 10, and a gather that is its own beat |
| the rise | 15 | 20 | 5 ticks of NIMBRA simply *being there* at full height |
| **the circling drift** | — | **70** | an entire 75-frame sway cycle with lateral travel — a beat the short does not have |
| THE LOOK | 25 | 25 | **unchanged** — a beat that works is not re-cut because there is room |
| **the second gathering** | — | **75** | the caster's `MP_MAGIC` causes a second mist swell — a beat the short does not have |
| the wind-back | 18 | 18 | unchanged (THE 18-TICK LEAD) |
| the strike | 50 | 50 | **unchanged — it is the law floor** |
| the dissolve | 25 (overlapped) | 40 | a real vent, still overlapped with the damage window |
| **THE BREATH** | 0 | **25** | §11.10 watch-item 3, answered |
| the release | 7 | 7 | unchanged |

---

## 7. WIRING — what a deploy round still has to do (NOT done here)

1. **The full needs its own private effect id: `ef080`.** STORYBOARD §6.1 verified 80 absent from stock
   and explicitly reserved it as *"the spare"*; it carries the same mild legacy semantics (*"Would run
   casting animation & apply effect"*) as 84 and 91. `nimbra_full.seq` therefore writes `SFX=80` on every
   `LoadSFX`/`PlaySFX`/`WaitSFX*` and roots every `SFXModel=` path at `Data/SpecialEffects/ef080/`.
   **Sharing `ef091` was considered and refused:** one folder has one `FileList.txt` naming one manifest,
   and the short's three curves are proportioned to a 110-tick window that the full cannot use.
2. **A companion `[[summon]]` block + manifest is required and is NOT authored here** (this round creates
   exactly two files). It is a copy of `nimbra.summon.toml` with `private_ef = 80`,
   `sequence = "nimbra_full.seq"`, `manifest = "nimbra_full_manifest.sfxmodel"`, `end = 260`, and §4.2/§4.3's
   playlist and curves. **`clips = [...]` must keep the exact same order** — `deploy.clip_key_of` mints
   `60000 + index` and both variants drive the *same* GEO 6400, so a re-ordered list would re-key the
   shared animations and break the approved short. `particles` is the same three files (they are copied
   verbatim into the private folder).
3. **The ability becomes `vfx1 = 80` (full) / `vfx2 = 91` (short).** Everything else in §6.2/§11.4 is
   unchanged: `power = 34`, `mp = 24`, `type = 0`, `element = ["Dark"]`, `targets = "AllEnemy"`.
4. > **⚠ THE ROLL IS THE OPEN LEAD, NOT A SOLVED PROBLEM.** A minted `BattleCommandId` never enters
   > `DecideSummonType`, and `AllEnemy(8)` is never the `ManyAny` arm at `btl_vfx.cs:99` — so **as wired
   > today `vfx1` plays structurally on every cast** and `vfx2` is unreachable. Census §5 records the
   > mechanism (`cmd.info.short_summon` is writable from a battle script; Memoria exposes
   > `BattleCommand.IsShortSummon` / `MutableBattleCommand`) **and its unverified risk (ORDERING:
   > `SelectCommandVfx` runs at command-set time, a `[BattleScript]` at damage-calc time, so the write may
   > land after the vfx is already chosen).** Until that is measured, wiring `vfx1 = 80` would make the
   > **23 s cast the only cast** — which is 2.2× the stock expected-cast median and re-opens exactly the
   > defect CAST 2 closed. **Deploy order is therefore: prove the roll first, then wire the full.** The
   > safe interim wiring is `vfx1 = vfx2 = 91` (unchanged, shipping) with `ef080` staged but unreferenced.
   >
   > **✔ RESOLVED 2026-07-24, the short/full roll round.** The ordering risk was the `[BattleScript]`
   > (damage-calc-time) route's — and that route is dead as feared. The live route is EARLIER: an
   > **AbilityFeatures Command-trigger** writing the NCalc key `IsShortSummon`
   > (`CharacterAbilityGems.cs:821`, the same first-class write stock SA 59 Boost ships as
   > `[code=IsShortSummon] false`). `TriggerOnCommand` runs at `CMD_MODE_SELECT_VFX`
   > (`btl_cmd.cs:594-595`) — strictly BEFORE `SelectCommandVfx` (`:617`) reads the flag — so the write
   > lands in time, adversarially verified (refutation attempted and failed, registration grammar
   > proven to `ff9abil.cs:515-538`). The kit emits it from the `[[summon]]` roll trio
   > (`roll_mp`/`roll_command`/`roll_ability` — ability-DISCRIMINATED, because a minted command hosts
   > several abilities and a command-wide roll would flip the others onto their `Vfx2` at 2/3 damage,
   > `BattleCalculator.cs:515`). Stock odds (`GetRandom() < (MP > 24 ? 230 : 170)`; `MP > cost`
   > post-deduction ≡ stock's pre-deduction `MP > 2×cost`, `btl_cmd.cs:1652`), Boost still wins
   > (`>SA Global` runs before `saExtended`, `ff9abil.cs:70-84`). `vfx1 = 80` is therefore wired —
   > the bench block is the pair, and the 23 s cast is the ~1-in-10 ceremony, E[per cast] ≈ 10.7 s.
   >
   > **★ PLAYTESTED 2026-07-25 ("test was good"; the full's rarity read correctly). WATCH ITEM
   > RESOLVED-AS-ACCEPTED:** the full reads as *"a double cast, kind of awkward"* — the P5 second
   > gathering's `MP_MAGIC` re-gesture is the prime suspect (the beat's own §3 premise, "the caster
   > causes it", is exactly what reads as a second cast). Kept for the demo by the owner; the
   > recast-only knob is recorded in RUNBOOK §THE SHORT/FULL ROLL ROUND.
5. Relaunch/recast split is unchanged from §11.7: a new `ef080/` folder and a changed `Actions.csv`
   need the relaunch; the `.seq`, manifest and particles are recast-only. **No new clip, particle or audio
   id is minted by this round**, so `SoundMetaData` and the `3DModel` line are untouched.

## 8. What this round deliberately does NOT do

- **No new clips, particles or audio.** The composition is built entirely from the four shipped clips, the
  three shipped particle models and the three shipped cues. Every "new" beat is new *arrangement*.
- **No file is edited.** `nimbra.seq`, `nimbra.summon.toml`, `bench/rung8.field.toml`, the creature, the
  audio and the particle JSON are all untouched; the approved short is bit-for-bit intact.
- **No deploy, no game-install access.** Offline only.
- **No camera work**, no `ShiftWorld`, no `[SfxHybrid]`, no engine surface of any kind — the full runs on
  stock Memoria exactly as the short does.

---

## 9. VALIDATOR OUTPUT (verbatim)

### 9.1 `playlist_sim.py` — the study's own sampler, imported and run against the FULL playlist

`playlist_sim.py` has no argv (its `__main__` reports the three historic playlists); it was **imported**
and its own `report()` / `sample()` called on this cast's playlist. `report()` hardcodes
`play_sfx_tick = 25`, so the first block's ticks read `25 + manifest frame`; the second block re-runs the
identical sampling through `sample(..., play_sfx_tick=55)`, the full's own value.

```
=== NIMBRA FULL -- emerge | drift | driftlook | drift | strike | drift, every entry Speed 1 ===
  entry emerge     N=15  Speed=1  frames   0..15  (15 ticks)
  entry drift      N=75  Speed=1  frames  15..90  (75 ticks)
  entry driftlook  N=25  Speed=1  frames  90..115 (25 ticks)
  entry drift      N=75  Speed=1  frames 115..190 (75 ticks)
  entry strike     N=30  Speed=1  frames 190..220 (30 ticks)
  entry drift      N=75  Speed=1  frames 220..295 (75 ticks)
  playlist 295 ticks vs window 260  [covers]
  emerge     never over-runs (plays cleanly across all 15 ticks)
  drift      never over-runs (plays cleanly across all 75 ticks)
  driftlook  never over-runs (plays cleanly across all 25 ticks)
  drift      never over-runs (plays cleanly across all 75 ticks)
  strike     never over-runs (plays cleanly across all 30 ticks)
  drift      never over-runs (plays cleanly across all 75 ticks)
  THE LUNGE PEAK (report clock, PlaySFX=25): clip frame 17.694915254237287 of 'strike' shows at t 233 (manifest 208, shown 17.4); the .seq fires at t 233  -> OK

  --- the same sampling in the FULL's own absolute clock (PlaySFX = t 55) ---
  THE LUNGE PEAK: clip frame 17.695 of 'strike' shows at t 263 (manifest 208, shown 17.4); nimbra_full.seq fires the sting/flash/relight at t 263 -> OK
  window covered: manifest frames 0..259 -> ticks 55..314; drain at t 315
  entry boundaries (manifest frame -> abs tick): emerge@0/t55, drift@15/t70, driftlook@90/t145, drift@115/t170, strike@190/t245, drift@220/t275
```

### 9.2 The census fits, re-derived from `summon_durations.csv` for this round

```
=== FULL duration vs power, re-derived from summon_durations.csv ===
  with Ark   : n=12  s = -6.226 +0.8135 * power   (Pearson r=+0.7880, R2=0.621)
      -> at power 34: 21.43 s  (322 ticks)
  Ark deleted: n=11  s = +20.243 +0.2004 * power   (Pearson r=+0.7046, R2=0.496)
      -> at power 34: 27.06 s  (406 ticks)
  anchor Ramuh  power  32  FULL  331 ticks / 22.07 s
  anchor Shiva  power  36  FULL  364 ticks / 24.27 s
  neighbour interpolation at power 34: 23.17 s (347.6 ticks)

=== the roll arithmetic (btl_cmd.cs:1600) ===
  MP-rich (230/256): P(short)=0.8984  E[per cast] = 10.72 s
  MP-poor (170/256): P(short)=0.6641  E[per cast] = 13.92 s
  FULL/SHORT ratio = 345/140 = 2.46
    stock Ramuh    331/113 = 2.93
    stock Shiva    364/135 = 2.70
    stock Atomos   424/165 = 2.57
    stock Phoenix  469/187 = 2.51
    stock Bahamut  547/112 = 4.88

=== the rotation number at the lunge ===
  SinusOut Factor2 = sin(pi/2 * 18/30) = 0.8090 -> Y = 164 + 12.94 = 176.94 deg (3.06 deg off square)
```

### 9.3 `summon-seq-lint` — the kit's silent-skip guard (K5)

Invoked exactly as the study invokes it for `nimbra.seq` (`build_rung8_stage.py:check` calls
`SL.lint_seq_file(..., private_ef=..., particles=[...])`; the CLI verb is the same code path):

```
$ cd ff9mapkit
$ py -m ff9mapkit summon-seq-lint ../studies/custom-summons/rung8-epic/nimbra_full.seq \
      --private-ef 80 --particles MistFloor.sfxmodel,MistWisps.sfxmodel,RiftFlash.sfxmodel
..\studies\custom-summons\rung8-epic\nimbra_full.seq: 0 error(s), 0 warning(s), 50 op line(s), 328 fixed-Wait ticks (>= 21.9s at BattleTPS=15; excludes 3 clip-bound and any SFX-bound wait)
clean -- no operation or argument would be silently dropped.
rc=0
```

**Both validators green.** The linter's 328 ticks is the fixed-`Wait` floor only — it deliberately counts
neither the 3 clip-bound waits (2 before `PlaySFX` ≈ 10 ticks, 1 in the release tail) nor the `WaitSFXDone`
block (2 ticks) nor the release `Turn` (5), which is the §6 ledger's 345 − 328 = 17.

**Control:** the same command against the shipped short reports `0 error(s), 0 warning(s)` too, so the
full is being held to the identical bar (§9.4).

### 9.4 The shipped short, linted with the same command (the control)

```
$ py -m ff9mapkit summon-seq-lint ../studies/custom-summons/rung8-epic/nimbra.seq \
      --private-ef 91 --particles MistFloor.sfxmodel,MistWisps.sfxmodel,RiftFlash.sfxmodel
..\studies\custom-summons\rung8-epic\nimbra.seq: 0 error(s), 0 warning(s), 36 op line(s), 123 fixed-Wait ticks (>= 8.2s at BattleTPS=15; excludes 3 clip-bound and any SFX-bound wait)
clean -- no operation or argument would be silently dropped.
rc=0
```

*(The `>= 21.9s` in the full's line is the linter's own fixed-`Wait`-only floor, 328/15 — it deliberately
under-reports the cast, which is 23.00 s once the 10 clip-bound, 2 `WaitSFXDone` and 5 `Turn` ticks the
linter refuses to guess are added back. §6.)*
