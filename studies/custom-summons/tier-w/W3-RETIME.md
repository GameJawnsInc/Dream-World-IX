# W3 — THE TIMING RESCORE: stock Bahamut's entrance stretched, and every clock locked to it moved with it

**TIER W rung 3.** Deliverables: `retime.py` (E2/E3/E4 derivation + self-check + staging + the
deploy/revert emitter), `w3_program_edits.py` + `w3_clock_emu.py` (B0's E1 spec and its 137-check
offline emulator), `bahamut_retime.toml` (the declarative surface), `test_retime.py`, `w3_gates.py`,
this report. Recon inputs: `A1-SEQUENCE.md`, `A2-PROGRAM.md`, `A3-CAMERA.md`, `A4-LIVESTATE.md`,
`B0-CLOCK-AUDIT.md`.
**Built and STAGED only.** Nothing in this rung's own tooling writes to the game install. `retime.py
build` (no `--live`) produces two container artifacts, one text override, and three stdlib-only
scripts — `deploy_aligned.py`, `deploy_misretime.py`, `revert_summon_retime_227.py` — under
`C:\gd\SCRATCH\summon-format\retime-w3\`. Those three scripts are what touch the install, and they
have **not been run against the live game by this report** — §6 is the protocol for the owner to run
them and judge the result. **The rung is not done until both casts are judged.**

*Method note.* This report is a synthesis, not a fresh measurement pass: B0 derived and proved the
program edit (E1) offline; B1 built both artifacts and ran the tool's own self-check; B2 ran the full
gate suite; V1 and V2 each independently re-derived the load-bearing claims from the raw bytes with
their own tooling (never importing `retime.py`) and could not refute B0/B1. Every number below traces
to one of those five artifacts. MEASURED / INFERRED labels are carried from them, not re-asserted here.

---

## 0. HEADLINE

> **Two clocks, one decision, twelve bytes.** The ALIGNED container differs from the user's own
> stock `ef227` in **24 bytes** — 12 in the effect program, 1 in the sequence stream, 11 in one
> camera shot. The MIS-RETIME container differs in exactly **12** — the same sequence byte, the same
> eleven camera bytes, and **none** of the program. `ALIGNED − MIS-RETIME` is *exactly* the 12
> program bytes that differ, byte for byte, with every other byte identical between the two. That is
> the whole rung reduced to one fact: **the presentation moved in both builds; the creature's own
> clock moved in only one of them.**
>
> N = **+48 ticks** (3.2 s at the live `BattleTPS = 15`) — chosen because it is *exactly two loops*
> of the creature's 24-frame float clip, so the clip lands on the same pose at the new phase end that
> it lands on today. Both containers stay **823,296 bytes**, both round-trip byte-exact through the
> **unmodified** W1 camera codec, and a fourth file — `Sequence.seq`, the outer text clock — carries
> one `Wait:` edit shared by both casts so the sounds and the damage cue stay in step with whichever
> visual clock is running.
>
> The offline proof is a 12-pair lock table (§3): recovered from stock by unbiased nearest-neighbour,
> then re-timed by **identity** in each artifact (never re-paired). ALIGNED keeps **every** lead.
> MIS-RETIME drifts by **exactly +48** on every post-cut `c0` pair and by **zero** on every `c1`
> pair — because `c1`'s own program start is itself a sequence op that rides the presentation clock,
> and `c0`'s is not. Two independent full re-derivations (V1, V2), using none of `retime.py`'s own
> code, reproduced this table and every byte count exactly.

---

## 1. Gate table

| gate | result | numbers |
|---|---|---|
| **X0** no regression | **PASS** | `r1_gates` 8/8 · `r2_gates` 6/6 · `r3_gates` 5/5 · `w1_gates` 5/5 · `w2_gates` 6/6 · **256 tests passed** total · `rescore.py`, `summon_camera.py`, `camera_codec.py`, `w3_program_edits.py`, `w3_clock_emu.py` and the tier-r tools **IMPORTED, never edited** (X0's own git check) |
| **X1** byte accounting | **PASS** | ALIGNED vs stock: **24** bytes (E1 12 / E2 1 / E3 11), 0 unexplained, 0 in a duration field. MIS-RETIME vs stock: **12** bytes (E2 1 / E3 11). `ALIGNED − MIS-RETIME` = **12** bytes == exactly the program bytes that differ (14 written across 7 sites, 12 differ); every shared byte identical |
| **X2** round-trip + W1 invariants | **PASS** | both containers: strict re-parse, `cursor_end == size` (`0xC9000`) · camera blocks **3/3 byte-exact** through the unmodified codec · **six** invariants on the edited block, both artifacts — `i1` first-offset-is-table-end / `i2` offsets-strictly-increasing / `i3` last-group-not-a-sequence / `i4` block-not-last-subfile / `i5` block-reserialises-byte-exact / `i6` block-length-unchanged — **all True** |
| **X3** alignment checker | **PASS** | **12** lock pairs, unbiased nearest-neighbour recovery, re-timed by **identity** (never re-paired). ALIGNED: **12/12** leads kept, 0 drifted, **11/12** pairs actually moved +48 on *both* clocks (the 12th, `c0` state 0's own entry, is before the cut and correctly does not move). MIS-RETIME: **5** post-cut `c0` pairs drift by exactly +47/+48, **1** pre-cut `c0` pair untouched, **6/6** `c1` pairs unchanged. Falsifiability also checked: the guard **fails** when handed aligned-as-both (5/7) and misretime-as-aligned (5/12) |
| **X4** emulator invariants | **PASS** | `retime.py`'s own gate: **154 checks, 0 failures**. ALIGNED's constants == `w3_clock_emu.read_consts` on the patched image exactly (threshold **117**, /117 progress shift **5**, /93 arrival shift **6**). MIS-RETIME's constants == **stock**'s (threshold 69, /69, /45) — its program is byte-identical to stock and independently passes `check_stock_endpoints`. `w3_clock_emu.py`'s own `__main__`: **137 checks, 0 failures** |
| **X5** revert | **PASS** | proven against a **mock** live tree seeded with the real pre-state (W2's 4-byte override present, no `ef227` text folder, a sibling `ef080` as a prune tripwire) — deploy_aligned changes the tree hash and creates the text override; **re-deploy is idempotent**; deploy_misretime on top does **not** overwrite the snapshot; revert = **EXACT RESTORE** (pre hash == post hash), the text `ef227` dir **pruned**, sibling `ef080` **not pruned**; second revert idempotent; a planted `ModFileList.txt` makes deploy **refuse**, rc 1 |
| **X6** provenance | **PASS** | `retime.py`: **0** byte literals of ≥6 non-uniform bytes. `bahamut_retime.toml`: **0** hex byte runs — only offsets, counts and small scalar guards (46, 56, 69, 117, 71, 82, 10, 7) plus three sha256 hashes. Live install **untouched by this report**: `FF9CustomMap/FF9_Data/SpecialEffects/ef227` still sha `8146eff4…` and still differs from stock in exactly W2's 4 bytes at `0x29D51/52/5C/5D`; `StreamingAssets/…/SpecialEffects/` still holds only `ef080/ef084/ef091` |
| **X7** text co-retime | **PASS** | `Sequence.seq` sha `0452a785…` == the registered `EXPECTED_SHA256` (no drift since A4). Anchor = `Wait #2` (file line 14), spanning outer ticks **60→116**, the **unique** `Wait` containing boundary 82 — found by **span**, not text (the stock file has two `Wait: Time=56` lines). `PlayerSequence.seq` sha `4bc643bf…` matches; audited, **0** literal `Wait: Time=` lines, main-thread clock never advances past tick 0, **shipped untouched** |

Reproduce: `py studies/custom-summons/tier-w/w3_gates.py` (needs the install and the corpus; ~10–14
minutes wall-clock because `w3_gates.py`'s X0 re-invokes `w2_gates.py`, which re-invokes `w1_gates.py`,
which re-invokes `r1/r2/r3` — a pre-existing nesting cost inherited from W2's own design, not new here
and not fixed by this rung). Tests alone: `py -m pytest studies/custom-summons/tier-w/test_retime.py -q`.

---

## 2. THE EDIT — four clocks, byte class by byte class

Three edits move the timeline; a fourth keeps a separate file in step with them. **The MIS-RETIME
artifact ships E2+E3(+E4) and omits E1 — that omission is the entire content of the rung's second
cast.**

### E1 — the effect PROGRAM's own clock (7 sites, 14 bytes written, 12 differ — id-3 image, chunk 0)

Not authored by this rung; consumed verbatim from B0's `w3_program_edits.PROGRAM_EDITS`, re-derived
by arithmetic (not fitted) and independently re-decoded by both V1 and V2:

| file offset | instruction | old → new | what moves |
|---|---|---:|---|
| `0x2E278` | `slti $v0,$s5,·` | `0x0045` → `0x0075` | **the threshold**: 69 → 117 ticks (state 0 lasts 70 → 118 ticks) |
| `0x2DB6C`/`0x2DB70` | `lui`/`ori $v1,·` | `0x76B9`/`0x81DB` → `0x4604`/`0x6047` | the **progress** reciprocal: `/69` → `/117`, shift 5 unchanged, no add-back |
| `0x2DC04`/`0x2DC54` | `lui $v1,·` (delay-slot copy / equal-path copy) | `0xB60B` → `0xB02C` (both) | the **arrival** reciprocal's high half — two peer copies, both patched so they can never disagree |
| `0x2DC58` | `ori $v1,$v1,·` | `0x60B7` → `0x0B03` | the arrival reciprocal's low half: `/45` → `/93` |
| `0x2DC70` | `sra $v1,$v1,·` | shamt 5 → 6 | the arrival reciprocal's shift — forced by the magic no longer fitting 31 bits at shift 5 |

New reciprocals are **computed, not copied**: `ceil(2^37/117) = 0x46046047` (shift 5, no add-back);
`ceil(2^38/93) = 0xB02C0B03` (shift 6, add-back retained). `w3_program_edits.build_edits(0)` spliced
into stock changes **zero** bytes — the derivation reproduces the stock constants exactly from
arithmetic alone, which is the strongest evidence that the recipe is the one the original compiler
used, not a curve-fit.

**What does NOT move**, and why: every discrete beat (`clock < 12`, `≥ 24`, `== 24`, `== 44`, `≥ 45`,
`≥ 35`, `< 46`) — all 8 intra-phase gate immediates untouched — and three clock-driven values B0
classifies as **rates**, not progress ramps (rotation Y `clock×7`, the beam elements' `clock×245`/
`clock×32` phase/rotation, the particle-spawner parity test). A rate has no terminal value to land on;
retuning one would *slow a continuous motion*, which is not what "a longer entrance" means. §5 covers
the one place this costs something visible.

### E2 — the SEQUENCE stream's delta clock (1 byte — header sector)

Derived from the stream, not hardcoded: the **unique** non-blocking `WAIT` whose span ends on cut tick
81 is the record at file `0x430`, `arg2` at file **`0x432`** = **46 → 94** (46+48), spanning tick
35 → 81. Time in the binary stream is pure delta — no op carries a timestamp — so this single byte
carries **76 of 93 ops** to a later tick (17 stay, exactly A1's anchor-B prediction) with **zero**
byte changes on any of the 76 ops themselves. `46 → 94` is inside the corpus-attested `[1, 240]`
envelope over 1,931 stock WAITs (`arg2 == 0` occurs zero times).

### E3 — the CAMERA's per-block frame clock (10 writes, 11 bytes — shot A only, 192 B sub-file)

Shot A is the one shot that **straddles** the cut; shots B and C install at sequence ticks that are
themselves ≥ 82, so E2 carries them wholesale and **zero** bytes change inside either block. Ten u16
frame words, chunk 0 id-2 sub-file 6, at file `0x29D5E/72/86/96`, `0x29DA4/B4/C2/D2/E0/EE`:

```
new_word = (old_word & 0xFC00) | (((old_word & 0x3FF) + 48) & 0x3FF)
```

Frames: `1,71,96,121,121,148,148,180,186,198,218` → `1,119,144,169,169,196,196,228,234,246,266`
(Code 0's frame-1 keyframe — locked to the phase's *entry*, which a length change does not move —
stays put). **11 bytes for 10 word writes**: the frame at local 218 crosses a 256 boundary on its way
to 266, so its high byte moves too — the edit is still a clean u16 write. Every changed byte resolves
through the codec's own field walk to `seqN CodeM frame.lo/.hi`; **zero** land on `campos`/`tgtpos`/
`cammove`/`tgtmove`/`focal`/`setting`, **zero** on a duration. All ten new words verified inside
`1..1023`, strictly non-decreasing, with the `0xFC00` flag bits (all zero on this block) preserved.

### E4 — the OUTER text clock (1 line — a separate file, not the container)

Under `SFXRework` (default `true`, forced by the live `Speed = 5`) the engine **swallows** the binary
sequence's own sounds, background fades, show/hide and the damage `EffectPoint`, and re-issues them
from `Sequence.seq` — a plain-text file the container does not contain and the retimed program never
reads. §4 is the full story; the edit itself is one `Wait: Time=56 → 104` line.

---

## 3. THE TWO-CLOCK LOCK TABLES — aligned vs. mis-retimed

12 pairs, recovered from **stock** bytes by unbiased nearest-neighbour matching, then **re-timed by
identity** in each artifact — never re-matched, because re-pairing a drifted table is how a broken
lock looks healthy. Beats come from re-running the state-machine recovery on the patched image
(`c0` s0 → 118 ticks under ALIGNED, unchanged under MIS-RETIME); cuts come back through the
unmodified camera codec; the sequence clock is re-walked from the patched `WAIT`.

`lead = cut − beat`; a negative lead means the camera **anticipates** the beat.

| machine:state | stock beat/cut/lead | ALIGNED beat/cut/lead | MIS-RETIME beat/cut/lead |
|---|---:|---:|---:|
| `ef227:c0` 0 | 12 / 11 / −1 | 12 / 11 / −1 | 12 / 11 / −1 |
| `ef227:c0` 10 | 82 / 81 / −1 | 130 / 129 / −1 | 82 / 129 / **+47 ← DRIFTED +48** |
| `ef227:c0` 1 | 107 / 106 / −1 | 155 / 154 / −1 | 107 / 154 / **+47 ← DRIFTED +48** |
| `ef227:c0` 2 | 132 / 131 / −1 | 180 / 179 / −1 | 132 / 179 / **+47 ← DRIFTED +48** |
| `ef227:c0` 4 | 159 / 158 / −1 | 207 / 206 / −1 | 159 / 206 / **+47 ← DRIFTED +48** |
| `ef227:c0` 5 | 190 / 190 / +0 | 238 / 238 / +0 | 190 / 238 / **+48 ← DRIFTED +48** |
| `ef227:c1` 0 | 255 / 255 / +0 | 303 / 303 / +0 | 303 / 303 / +0 |
| `ef227:c1` 1 | 291 / 291 / +0 | 339 / 339 / +0 | 339 / 339 / +0 |
| `ef227:c1` 2 | 340 / 336 / −4 | 388 / 384 / −4 | 388 / 384 / −4 |
| `ef227:c1` 3 | 369 / 369 / +0 | 417 / 417 / +0 | 417 / 417 / +0 |
| `ef227:c1` 4 | 372 / 369 / −3 | 420 / 417 / −3 | 420 / 417 / −3 |
| `ef227:c1` 5 | 387 / 388 / +1 | 435 / 436 / +1 | 435 / 436 / +1 |

**Reading it:** ALIGNED keeps all six of `c0`'s stock leads (`−1,−1,−1,−1,−1,0`) *and* moves 11 of the
12 pairs by +48 on both columns — a table that hadn't genuinely moved would keep its leads trivially,
so the fact that both the beat and the cut columns shift together is the load-bearing evidence, not
just the lead staying constant. MIS-RETIME shows the opposite signature by construction: every `c0`
pair after the cut drifts by the full +48 (only the beat column moved to compensate less — the program
never got the memo), while **all six** `c1` pairs are untouched, because `c1`'s own `RUN_PROGRAM` is
itself a sequence op riding the presentation clock, not a program-clock threshold.

**Sign correction to the original brief**, recorded for anyone re-reading the recon: the brief
specified "c0 leads differ by exactly −48 (cut minus beat)." Under that convention the observed drift
is **+48** (leads go −1 → +47, and 0 → +48) — in the mis-retime the **cut moves later while the beat
stays**, not the other way round. Magnitude, pair count and the `c0`/`c1` asymmetry are exactly as
specified; only the sign in the brief was inverted. Both V1 and V2 independently reproduced this table
from raw bytes and flagged the same correction, so it is not a transcription slip in this report.

---

## 4. THE THIRD CLOCK — why a fourth file has to move too

`ef227.bytes` is not the only clock this cast runs on. Under `SFXRework = true` (the default, and
forced here because the live install runs `Speed = 5`), `SFXDataMesh.Runtime.Begin()` installs a dummy
callback for the **whole playback** of a `UseCamera` effect — which `PlayerSequence.seq` declares
`ef227` to be — and that dummy returns 0 and does nothing for the binary sequence's `PlaySound`,
`SetBackgroundIntensity`, show/hide and `EffectPoint` (the damage trigger) calls. Those are instead
re-issued from a **separate, plain-text managed file**, `Sequence.seq`, re-read from disc on every
cast with no cache. A retime of the container alone moves the camera and the creature program and
**nothing else** — the sounds and the damage cue would stay on their old schedule and drift by N,
which is not a defect in the retime but would be misread as one.

**The fix is one line**, because every tick in that file is a running sum of its own `Wait: Time=`
values: the single `Wait` whose span **straddles** the boundary carries every downstream beat with it.
That anchor is `Wait #2` (file line 14), spanning outer ticks **60 → 116** — found by **span, not
text**, because the stock file has *two* `Wait: Time=56` lines and only one of them covers the
boundary; anchoring by literal text would have been a coin flip. The edit: `Time=56 → 104`.

**What moves downstream, measured by re-walking the file**: 17 further `Wait` beats +48, both
`EffectPoint` calls (damage computation and the damage-number popup), the flare's background-intensity
ramp, the remaining `PlaySound` clusters, both `Song` cues, and the closing fade — the script's own end
moves 547 → 595. `PlayerSequence.seq`, the *outer-outer* caster script, is **audited, not edited**:
`retime.py` reconstructs its own clock and would refuse to leave it alone if any beat landed after the
boundary. It doesn't — the file has **zero** literal `Wait: Time=` lines (every wait it uses is
animation- or signal-gated), so its main-thread clock never advances past tick 0 and nothing in it can
drift. It ships **untouched**, sha-guarded against drift.

**The stated uncertainty, carried forward honestly**: the exact tick-for-tick correspondence between
the container's `seq_tick` and the outer script's own tick counter is **not measured** anywhere in the
studies — no probe has ever logged both clocks on the same cast. The working hypothesis (near 1:1,
offset a small unmeasured constant) is argued from a shared `PlaySFX` origin and matching order-of-
magnitude total length, not from a direct capture. `delta` is deliberately a **separate** field from
`ticks` in `bahamut_retime.toml` for exactly this reason: because the text file is re-read on every
cast with no relaunch, a recast-only bisect can move `delta` alone to find the true cross-clock offset
without ever rebuilding either container. This rung ships `delta = 48 = ticks`, the straightforward
guess; §5 flags that as unverified, not wrong.

---

## 5. What W3 does NOT settle

1. **THE LIGHT COLUMN — the one place the locked policy visibly breaks an authored coupling.** Its own
   `/46` countdown is untouched and identical tick for tick (150 at tick 0, 4 at tick 45), but the
   `rcos` angle it reads from the now-slower progress ramp is **393, not 667**, on its last live tick
   — it ends its sub-phase **38 %** through the ramp instead of **65 %**. Unavoidable under the locked
   policy: any ramp consumed inside a fixed-tick sub-block reads a different value once the ramp is
   slower, and stretching the `clock < 46` gate to compensate would move a discrete beat, which the
   policy forbids. **CAST WATCH ITEM:** the descending light column in ticks 0–45, for a shape that
   "stops short."
2. **Rotation Y runs 336 units (29.5°) further** (483 → 819 by the new phase end) — a deliberate
   non-edit: it is a **rate**, and no same-length two-instruction skeleton can express the required
   ×4.13 scale anyway. Matters only if the spin's phase at the cut was authored to matter.
3. **The particle spawner runs 48 extra ticks at full rate and the bone trail stays lit 48 ticks
   longer** — both gates are absolute ticks the locked policy leaves alone. This is what "a longer
   entrance" should look like, but it may read as slightly denser than stock.
4. **The float clip: no risk, by construction** — N = +48 is exactly two 24-frame loops, so the clip
   frame at the new phase end is the one stock already ends on.
5. **THE INFERENCE BOUNDARY, stated for review:** the *visual meaning* of every program value ("fly-in
   radius," "camera shake," "light column," "bone trail") is inferred from the HLE call site and
   argument slot, not observed. Strong for the creature (op 25 `Hi_DrawSummonModel`'s own position/
   scale/rotation arguments), weaker for the shared tail's op 68. The arithmetic is measured; the
   reading of what the player sees is not.
6. **A design judgement a reviewer could reasonably dispute:** the RATE-vs-PROGRESS-RAMP distinction
   (retune progress ramps, leave rates alone) is argued from what each value drives, not measured. If
   it is wrong for rotation Y specifically, the fix is not same-length and needs a different skeleton.
7. **The MIS-RETIME artifact built here is the LOUD falsifier, not the subtle one.** With E1 omitted,
   the creature's own arrival arithmetic *inverts* at clock 117 under the unretuned constants: radius
   **−1256** (stock endpoint 24 — through the mark and out the far side), scale **−15428** (stock 2048
   — the model inverts), shake envelope **−2849** (stock 0, wrong-sign camera jitter), RGB **+44**
   (stock 0, over-bright). If W3 ever wants a *subtle* falsifier of the two-clocks law instead, A3
   §7's `E3-alt` (the one-tick camera-lead variant) is the better instrument — not what either cast
   here ships.
8. **Unresolved, carried from A2/B0, not needed for E1 itself:** the exact instruction that increments
   the phase clock each host frame was never located; tail ops `0x2C74`/`0x2DA4`/`0x2E94` have read
   argument shapes but undecoded visuals.
9. **A pre-existing test-infrastructure limitation, out of scope here (B2):** tier-r's synthetic MIPS
   encoder hard-codes the default `psx` constant for jump-target encoding rather than threading a
   caller-supplied `psx=` through, so a synthetic image built for an odd chunk-table slot decodes its
   own jumps against the wrong base. Worked around in the test fixtures by placing the second machine
   at an even slot; not a defect in `retime.py`/`w3_clock_emu.py`/`w3_program_edits.py`, and editing
   tier-r's shared test helpers is out of scope for this rung.
10. **The gate-runner nesting cost is real and not fixed.** `w3_gates.py`'s X0 re-invokes `w1_gates.py`
    and `w2_gates.py`, which themselves re-invoke `r1`/`r2`/`r3`, so a full run takes ~10–14 minutes
    wall-clock. Inherited from W2's own design, reported as an observation per this task's own
    instruction not to redesign for it.
11. **Judge the gate on container-internal alignment.** Per A4 §4.5, the two-clocks law W3 exists to
    prove lives entirely inside the 823,296-byte container (§3's lock table). E4 is shipped in both
    casts precisely so a viewer never has to separate "the retime" from "the outer script drifting" —
    but if the text override ever fails to deploy while the container succeeds, that failure mode
    would look exactly like a mistimed sound cue and should not be blamed on the retime itself (§6).
12. **Pose/geometry semantics remain unconfirmed**, carried unchanged from W1/W2: this rung's camera
    edit is timing-only (frame words), never a pose byte, so W2's own "riskiest assumption" about
    degree conventions is untouched and irrelevant here — noted only so it isn't mistaken for settled.

---

## 6. THE CAST PROTOCOL

### 6.1 Stage (already done; reproduce or re-verify with)

```
cd studies/custom-summons/tier-w
py retime.py build bahamut_retime.toml
```

This re-reads the install's own drift-guarded `resources.assets` copy of `ef227` (not the live
mod-folder override — the retime is built from **pristine stock**, same as W1/W2), re-derives E2/E3/E4
against it, re-runs the full self-check, and stages, under `C:\gd\SCRATCH\summon-format\retime-w3\`:

| artifact | path |
|---|---|
| ALIGNED container | `mod\FF9_Data\SpecialEffects\ef227` |
| MIS-RETIME container | `misretime\ef227` |
| the text co-retime (shared by both casts) | `mod\StreamingAssets\Data\SpecialEffects\ef227\Sequence.seq` |
| `deploy_aligned.py` | writes ALIGNED + the text file to the live install |
| `deploy_misretime.py` | writes MIS-RETIME + the text file to the live install |
| `revert_summon_retime_227.py` | restores the pre-W3 live state |

**Nothing above touches the game.** `--live` is required even to `--root` *inside* the install, and
this build does not pass it. The three generated scripts are what actually touch the install.

> ⚠ **LIVE-STATE NOTE (2026-07-26): the ALIGNED artifact is ALREADY DEPLOYED.** During adversarial
> verification, V2's sandbox harness had a path-substitution bug (2-backslash literal vs the plan
> JSON's 4-backslash escapes silently no-opped the redirect) and ran `deploy_aligned.py` against the
> real install. The orchestrator then verified the outcome byte-for-byte and **adopted it as the
> deliberate cast-1 deploy**: live container sha `692ec8cb…` == staged ALIGNED, live `Sequence.seq`
> sha `2f4f6dbf…` == staged text, and the first-deploy snapshot correctly captured the true pre-W3
> state (W2's `8146eff4…` container backed up at `live-snapshot\SpecialEffects__ef227.pre-w3`, text
> recorded absent) — the revert chain is intact and sandbox-proven. Re-running `deploy_aligned.py`
> is an idempotent no-op (proven; the snapshot is not retaken). **Cast 1 therefore needs no deploy
> step — just cast.** Process lesson for future harnesses: seed a sandbox tree and point the script
> at it by environment, never by rewriting escaped path literals.

**Important:** deploying either W3 artifact **replaces** W2's live 4-byte camera override — the
retime is built from stock framing, not from W2's reframed opening. §6.2's "what you should SEE"
reflects stock camera angles running on the new timing, not W2's wide/rolled entrance. The revert
script (§6.4) puts W2's override back afterward.

### 6.2 CAST 1 — ALIGNED (the rung's primary claim)

**Run:** nothing — **ALIGNED is already live** (see the LIVE-STATE NOTE above). If re-running for
peace of mind: `py C:\gd\SCRATCH\summon-format\retime-w3\deploy_aligned.py` (idempotent no-op).

The live state: the ALIGNED container over `FF9CustomMap\FF9_Data\SpecialEffects\ef227` and the
co-retimed `Sequence.seq` at `FF9CustomMap\StreamingAssets\Data\SpecialEffects\ef227\`. The
FIRST-DEPLOY snapshot of the prior state (W2's camera override, no text override) was taken
correctly, so revert always lands on the true pre-W3 state.

**Relaunch: NONE.** The container is re-read by `SFX.Play` on the very next cast, no cache; the text
file is re-read from disc on every cast. Recast to see it — no `~` reload, no field warp needed. This
is the same no-relaunch guarantee W2 already proved live, now covering a second file too.

**How to cast:** the bench field 30301's ability row 196, "Stock Bahamut" (`vfx1=vfx2=227`, `type=0`),
is this exact override target — confirmed live and correctly wired (A4 §3). `~` → Warp to field →
30301, start the bench battle, Iviv → *Spark* → **Stock Bahamut** on the enemy group. Cleaner
alternative: any save where Garnet can summon Bahamut normally plays the same override — no bench
wiring at all.

**What you should SEE:** the entrance float runs **about 3.2 seconds longer** than stock — the same
angles and poses the game has always shown (this build's camera is stock framing, not W2's reframe),
just held and moved through for longer. The camera cut still lands **exactly** on the moment Bahamut's
own arrival animation finishes and the phase changes — the beat and the cut should feel simultaneous,
the same way they always have, just later. Sounds, the background flash, and the damage number should
all still land **in step** with what's on screen, because the text co-retime moved with the container.
Later in the cast (the approach, Mega Flare, the outro — all of `c1`) should look **completely
unchanged**, because none of that phase's timing moved.

**⚠ THE EFFECT-OWNED SCENERY LAW caution:** `summon-inspect`'s phase table shows the very phase this
rung stretches (`c0` s0, captured frames ~57–126) is one of the phases that **draws effect models** —
Bahamut's own scenery/props, not just the creature (PLAN.md's law, minted off W2's cast). Because this
rung's camera stays at **stock** framing throughout (no reframe), the extended entrance shows more of
the *same already-authored* scenery for longer, not new geometry from an unbudgeted angle — the law's
warning about a tight "reframe budget" does not bite here. It would bite immediately if a future rung
ever stacks a wide-angle reframe (W2-style) on top of a stretched effect-drawing phase; check the phase
table before doing that.

**Failure table:**

| symptom | likely cause / what to do |
|---|---|
| Nothing changed at all | same delivery-path checklist as W2 §6.5: wrong ability cast (check it points at 227, not a private `ef080/084/091`), wrong mod folder, missing extension, a `ModFileList.txt` that doesn't list it, or another `FolderNames` entry shipping its own `ef227` earlier in priority. Nothing logs either way (`suppressMissingError`) |
| Entrance runs longer but the cut visibly drifts off the beat | should be impossible — the offline lock table (§3) proves all 12 pairs land exactly; would mean either the wrong container deployed or a genuine finding the offline math missed. **Report it, do not assume operator error** |
| Sounds/damage feel mistimed relative to the visuals | check whether `Sequence.seq` actually deployed — it is a **separate file** from the container, and a partial deploy (container copied, text write failed) produces exactly this symptom. Distinguish from §5 item 1 (the light column) by watching only ticks 0–45's descending light shape, not the sound |
| The cinematic reads "busier"/denser than remembered | expected, §5 item 3 (spawner + bone trail running the extra 48 ticks at full rate) — not a bug |
| Black or frozen cast | revert immediately (§6.4) and report — would mean the pose evaluator rejects something the emulator's offline model missed despite the round-trip proof |

### 6.3 CAST 2 — MIS-RETIME (the deliberate falsifier)

**Run:** `py C:\gd\SCRATCH\summon-format\retime-w3\deploy_misretime.py`

Same deploy mechanism, same relaunch-none guarantee, same casting path. Overwrites whichever of
{W2's override, ALIGNED} was live before — the snapshot means either cast order still reverts cleanly
to the true pre-W3 state.

**What drift LOOKS like:** per the lock table (§3), all **five** of `c0`'s post-cut phase transitions
drift by exactly +48 while all **six** of `c1`'s stay put. Concretely: the creature should visibly
finish arriving — settle into its post-entrance pose — at its **old stock timing**, roughly **3
seconds before** the camera actually cuts to acknowledge that change, and this early-arrival mismatch
**repeats at every one of `c0`'s later beats too** (not just the first one). The back half of the cast
— everything from the point `c1` takes over through Mega Flare and the outro — should look perfectly
normal, because `c1`'s own clock is a sequence op and moved with the presentation regardless. Per B0
§6.5 this is not subtle: run far enough into the stretched window and the creature's own arrival
arithmetic **inverts** under the unretuned constants (radius through its mark and out the far side,
scale negative, shake envelope wrong-sign, RGB over-bright) — so at the far end of the extension,
watch for an outright glitch in the creature's approach, not just an early settle.

**This cast is SUPPOSED to look wrong.** It is the two-clocks law demonstrated in-game, not merely
asserted from bytes — a controlled A/B against CAST 1 where the only difference is 12 bytes.

**Failure table:**

| symptom | reading |
|---|---|
| Looks identical to CAST 1 — no drift visible | the two-clocks law is **falsified** by this cast. Report it plainly; it overturns the tier's whole premise, it is not a "looks fine" |
| Nothing changed at all from stock | same delivery-path checklist as §6.2's first row |
| The creature visibly glitches/inverts near the end of the stretched window | **expected** — the loud falsifier signature B0 predicted (§5 item 7); note it, do not treat it as a new bug |
| Black or frozen | revert (§6.4), report |

### 6.4 Revert

```
py C:\gd\SCRATCH\summon-format\retime-w3\revert_summon_retime_227.py
```

Restores exactly what was live **before the first W3 deploy** — right now, that is **W2's resting
state**: the 4-byte camera override back byte-for-byte, and no text override. Deletes the container
write and the newly-created `Sequence.seq`/`ef227` text folder, pruning empty parent directories up to
the mod root without touching sibling `ef080`/`ef084`/`ef091`. Idempotent either way — X5 proved EXACT
RESTORE against a mock tree seeded with the real live pre-state, in both deploy orders and after two
reverts. No relaunch needed, same as deploy.

---

## 7. Files

| file | what |
|---|---|
| `studies/custom-summons/tier-w/retime.py` | derives E2 (sequence WAIT), E3 (camera frame words), E4 (text `Wait:` anchor) from the drift-guarded install; consumes E1 verbatim from `w3_program_edits`; self-check + staging ledger + deploy/revert script emitter; verbs `plan` / `build` / `verify` |
| `studies/custom-summons/tier-w/w3_program_edits.py` | B0's E1 spec — `PROGRAM_EDITS`, the write guards, the reciprocal derivation |
| `studies/custom-summons/tier-w/w3_clock_emu.py` | B0's offline emulator — 137 checks, 0 failures; `audit()` is what the gates call |
| `studies/custom-summons/tier-w/bahamut_retime.toml` | the declarative surface — N = +48, the four clocks' guards, in W1/W2's own vocabulary |
| `studies/custom-summons/tier-w/test_retime.py` | the test suite backing X0–X7 |
| `studies/custom-summons/tier-w/w3_gates.py` | X0–X7 |
| `studies/custom-summons/tier-w/w3-recon/A1-SEQUENCE.md` … `A4-LIVESTATE.md`, `B0-CLOCK-AUDIT.md` | the recon this rung's edit sets are derived from |
| `C:\gd\SCRATCH\summon-format\retime-w3\` | the staged mod root, both artifacts, the text override, and the three live-deploy scripts — **stock-derived, SCRATCH only** |

---

## CAST VERDICT — 2026-07-26 ★★ BOTH CASTS PROVEN, THE RUNG IS CLOSED

**"worked as described"** — the owner ran the full protocol: cast 1 (ALIGNED) showed the ~3.2 s longer
entrance with every camera cut landing on its beat; cast 2 (MIS-RETIME) showed the drift as designed;
the revert was run and the live install verified back at W2's resting state byte-for-byte (container
sha `8146eff4…`, text override pruned). **TIER W rung 3 is ★★: a stock summon's TIMING is editable in
place — durations, phase thresholds, ramp normalisers, camera schedule and the outer text clock moved
as one — and the two-clocks law is demonstrated by A/B in-game, not asserted.** No cast surprised the
offline proof; the disclosed light-column residual drew no owner objection.
