# A3 — THE CAMERA TIME-FIELD MAP

**TIER W rung 3 recon, slice A3.** Which bytes inside ef227's three camera blocks encode TIME, how the
frame word and the duration fields are coupled, and the exact in-block edit list for a boundary shift.

**READ-ONLY.** Nothing was written to the game install, nothing stock was modified, no repo code was
changed. Decoded stock keyframe dumps live only under `C:\gd\SCRATCH\summon-format\retime-w3-recon\`.

---

## 0. HEADLINE — the answer to the critical semantic question

> **The stepper advances keyframe-to-keyframe by the FRAME WORDS. The durations are NOT derived and
> NOT redundant: they are independent countdowns that parametrise the interpolation a keyframe
> starts. A timeline shift is therefore a FRAME-WORD-ONLY edit — except for one narrowly defined
> case (an interpolation that straddles the cut), which ef227's target shot does not contain.**

Both halves are proven, not argued:

* **Native, MEASURED.** The stepper `0x13540` reads the Code's frame word, masks it to `& 0x3FF`, and
  fires the Code on an **equality compare against a per-block frame counter** (`@0x135a1..0x135ac`).
  The counter is seeded to **1** by the block parser (`0x13030 @0x1304f`) and incremented by exactly
  **1 per `SFX_UpdateCamera`** (`@0x13adf`). Every duration field is instead stored into a
  `(remaining, total)` pair and consumed by a per-frame lerp — `H = source·t + dest·(1−t)`,
  `t = remaining/duration` (`@0x13a13..0x13a83`). Nothing in the Code-consumption path reads a
  duration to decide *when* the next Code fires.
* **Corpus, MEASURED.** Over **3,537** movement blocks in **798** camera blocks across **372**
  effects, a movement `duration` equals the frame delta to the next keyframe only **25.4 %** of the
  time. **43.0 %** are shorter (the camera reaches its pose and holds) and **30.2 %** are longer (the
  move is interrupted by the next keyframe). If the durations were derived from the frame deltas this
  number would be 100 %.

So the two fields answer two different questions — *when does this Code fire* (frame word) and *how
long does the motion it starts take* (duration) — and only the first one moves when the timeline moves.

---

## 1. How each fact here was obtained (MEASURED vs INFERRED)

| # | claim | how | class |
|---|---|---|---|
| 1 | frame word fires on an equality compare with a per-block counter | `refkit` disasm of the user's own `FF9SpecialEffectPlugin.dll`, fn `0x13540` @`0x135a1`–`0x135ac` | **MEASURED** (static, read-only) |
| 2 | the counter is seeded to 1 at install and +1 per host frame, saturating at 0x3FF | `0x13030 @0x1304f` (`mov dword[0x21ff08], 1`); `0x13540 @0x13acd..0x13ae2` (`cmp r8d,0x3fe / inc / store`) | **MEASURED** |
| 3 | the frame-number field is **10 bits**, not 13 | the mask `and eax, 0x3ff` @`0x135a4`, plus `shr r14d,0xa` @`0x135d9` folding bits 10–15 into a flags composite | **MEASURED** (code); corpus cannot distinguish (§5.1) |
| 4 | durations feed `(remaining,total)` pairs + a lerp, never the schedule | `0x13676` (movement), `0x13748` (focal), `0x137ac` (unk5), lerp `0x13a13` | **MEASURED** |
| 5 | duration ≠ frame delta in 74.6 % of the corpus | `a3_probe.py corpus` over all 372 containers | **MEASURED** |
| 6 | every field offset in ef227's three blocks | `a3_probe.py ef227`, walking the codec's own field order; cross-checks against W2's independently derived offsets (§6.4) | **MEASURED** |
| 7 | shot A's keyframes are locked to c0's phase boundaries at a uniform −1 lead | joined R3's phase spine (thresholds 69/24/24/26/30) to the decoded keyframes on the sequence clock | **MEASURED** (both columns derived from bytes; no capture, no fit) |
| 8 | frame-word bit `0x4000` = **freeze the camera clock** | `0x136ef` (`test r14d,0x100100`) → `0x13707` writes the pause flag `0x2200b2`, which gates the increment at `0x13ad6` | **MEASURED** |
| 9 | frame-word bit `0x2000` = **suppress the battle-camera restore** | `0x1385c` sets `0x21ff49`; fn `0x12fd0 @0x12ff4` skips the restore when it is set, then clears it | **MEASURED** |
| 10 | `CodeFlags 0x8000` (codec `unk6`) hands the camera back to the raw17 battle camera | `0x13b18..0x13bfb` re-invokes `0x13030` on `[0x211e60] + (s16)[+2]` — the raw17 `camOffset` idiom | **INFERRED (high)** — the pointer's provenance is runtime-only |
| 11 | the pause flag is cleared *only* by install/reset | image-wide `.pdata` xref scan for `0x2200b2`: 3 write sites (`0x12d93`, `0x12e24`, `0x13707`); no bulk clear covers it | **INFERRED (high)** — a register-based memset over a range could evade the scan |
| 12 | the edit list round-trips byte-exact at the same length | patched a **copy** in SCRATCH at N = +12 / +40 / +100 / −24, re-parsed and re-serialised through the unmodified `camera_codec` | **MEASURED** |

Reproduce: `py C:\gd\SCRATCH\summon-format\retime-w3-recon\a3_probe.py all` (needs the extracted corpus;
the DLL rows need `refkit` from `studies/custom-summons/thomas-swap/disasm/`).

---

## 2. THE COMPLETE TIME-FIELD CENSUS — every byte that encodes time

Read against `camera_codec._split_code`'s field order, which the native stepper's consumption order
reproduces exactly (independently re-derived here from `0x13600`–`0x137d4`).

| field | where | width | is it TIME? | native evidence |
|---|---|---|---|---|
| **Code `frame`** | Code +0 | u16, **low 10 bits** are the number, bits 10–15 are flags | **YES — THE SCHEDULE** | `and eax,0x3ff` @`0x135a4`; `cmp` + `jne` @`0x135a9` |
| **`cammove.duration`** | `cammove` +0 | declared u16; the stepper reads **byte +0 only** | **YES — interpolation length** | `movzx eax, byte[rdx]` → two adjacent state bytes @`0x13676`–`0x1367b` |
| **`tgtmove.duration`** | `tgtmove` +0 | same | **YES** | same code path (the loop runs twice, one 0x20-byte state block per channel) |
| **`focal.duration`** | `focal` +0 | u8 | **YES** | `0x13748`–`0x13751` seeds `remaining`(`0x21ff38`) **and** `total`(`0x21ff34`); lerp @`0x13a13` |
| **`unk5` +2** | `unk5` +2 | u8 | **YES — a third, undocumented timed channel** | `0x137ac`–`0x137b6` writes the same byte to `0x21ff28` **and** `0x21ff24`; `0x21ff28` then gates the call to `0x14350` @`0x13986` |
| `cammove/tgtmove.type` | +2 | u8 | no — easing curve | `0x1367e` |
| `cammove/tgtmove` +3 | +3 | u8 | no | `0x13685` |
| `campos/tgtpos` (6 B) | — | — | no — pose only | `0x13651` → `0x13c10`, then cursor += 6 |
| `focal.flags`, `focal.distance` | +1, +2 | u8, u16 | no — the lerp's destination | `0x13757`, `0x1376e` |
| `sign` (0x40), `unk3` (0x200), `unk4` (0x400) | — | 2 B each | no — single value stores, no `(remaining,total)` pair | `0x136c6`, `0x13712`, `0x1372d` |
| `setting` (0x4000) | — | 2 B | no | `0x137f0` block |
| `unk6` (0x8000) | — | 4 B | no — but the **Code carrying it is scheduled by a frame word** (§5.4) | `0x13843` → `0x13b18` |
| **outer selector group** (bit 3) | block tail | 4 or 6 B | **no** — read once by the parser `0x13030`, never by the per-frame stepper | `0x13130`–`0x134e2` |
| **outer anchors group** (bits 4–7) | block tail | 6 B × popcount | **no** — memcpy'd at parse time into the anchor slots | `0x130f7`–`0x13109` |

**Corpus presence** (7,307 Codes): `campos` 5,097 · `tgtpos` 4,565 · `cammove` 2,440 · `focal` 1,896 ·
`unk6` 1,493 · `tgtmove` 1,097 · **`unk5` 319** · `sign` 41. The aborting flags `0x04`/`0x20` appear
**zero** times, so the codec's early-return path is dead on stock data.

**So a general retime tool must touch four field kinds, not two:** the Code frame word, `cammove`/
`tgtmove` duration, `focal` duration, and `unk5` +2. ef227 uses the first three and never sets `unk5`.

---

## 3. THE CLOCK, mechanically derived (this replaces "three-way validated")

```
PLAY_CAMERA 0x29  ->  handler 0x3bbd0  ->  sub-file resolve 0x3d800  ->  install 0x12df0
   0x12df0 @0x12e24   pause flag 0x2200b2 = 0        (unfreeze)
   tail-jmp 0x13030   @0x1304f  FRAME COUNTER 0x21ff08 = 1
                      @0x134f1  selected sequence pointer -> 0x21ff00
per host frame:  SFX_UpdateCamera 0x1e80 @0x1e88 calls the stepper 0x13540
   0x13540 @0x135a1   read the Code's frame word at the cursor
           @0x135a4   frame = word & 0x3FF          (10 bits)
           @0x135a9   if (counter != frame) stop consuming        <- EQUALITY, not >=
           @0x135d9   composite = CodeFlags | ((word >> 10) << 16)
           ...        consume the Code's sub-blocks, advance the cursor
           @0x13870   loop, up to 10 Codes per tick
           @0x13877   if the next word == 0 (terminator) NULL the cursor
           @0x13acd   if (counter <= 0x3FE && !pause) counter += 1
   @0x1e8f  if the stepper returned non-zero, call it ONCE more (no counter advance)
```

Four consequences that are load-bearing for W3:

1. **`abs_seq_tick = install_op.seq_tick + local_frame − 1` is now derived, not fitted.** The counter is
   1 on the install tick, so local frame 1 fires there. W1's rule survives contact with the code.
2. **The camera clock and the program clock are the same host-frame clock** and neither is driven by
   the sequence's `WAIT` ops. A `WAIT` only delays later *sequence* ops. **This is why a retime needs
   both a sequence edit and a program-constant edit — the sequence cannot stretch a phase.**
3. **Same-frame Code pairs are legal and normal** (2,033 pairs, 112 triples, 2 quadruples corpus-wide;
   the cap is 10). This also **corrects D4 §2.3**, which attributed same-frame pairs to the double
   `0x1e88`/`0x1e91` call. They are not related: the pairs are consumed by the stepper's own inner
   loop; the double call is triggered by a `CodeFlags 0x8000` Code (§5.4) and deliberately skips the
   counter increment.
4. **The counter saturates at 1023 and a frame word of 0 is the terminator.** Both are hard authoring
   bounds (§8).

---

## 4. THE LOCK TABLE — why the cut point is not where it looks

Both columns below are derived from bytes alone: the camera column from the decoded frame words, the
phase column from R3's recovered thresholds (`c0`: 69/24/24/26/30; `c1`: 35/48/28/2/14) placed at the
`RUN_PROGRAM` op's own sequence tick (c0 @12, c1 @255).

| c0 phase | enters at seq tick | shot A keyframe | at seq tick | authored lead |
|---|---:|---|---:|---:|
| s0 | 12 | f1 (install + first pose) | 11 | **−1** |
| s10 | **82** | **f71** | **81** | **−1** |
| s1 | 107 | f96 | 106 | **−1** |
| s2 | 132 | f121 (×2) | 131 | **−1** |
| s4 | 159 | f148 (×2) | 158 | **−1** |
| s5 | 190 | f180 | 190 | **0** |

Six consecutive locked pairs. The sequence stream corroborates from a third direction: it fires op
`0x2a arg1=77` (file `0x433`) at **tick 81** — the same tick as the f71 camera cut — and a six-op
burst (file `0x439`–`0x448`) at **tick 82** — the same tick as the phase boundary. Three independent
streams agree that **the beat is at 82 and its anticipation is at 81**.

### ⚠ THE ONE-TICK CORRECTION TO THE BRIEF

The recon brief specifies *"shift every camera event at sequence tick ≥ 82"*. That is **one tick too
late**. Stretching `c0` s0 by N moves its boundary to 82+N; the f71 keyframe (and the sequence's
tick-81 op) belong to the **last tick of s0**, so they must move with it. Cutting at 82 leaves f71
parked at 81 while the beat it anticipates walks away to 82+N — the authored −1 lead becomes −(1+N),
which is precisely the drift W3 exists to avoid.

**THE RULE, stated so it generalises:** *a camera event moves iff the phase boundary it is locked to
moves.* For a stretch of a phase, that is every event at `abs ≥ boundary_tick + lead`, i.e.
**`abs ≥ 81`** here, i.e. **shot A local frame ≥ 71**.

Both edit lists are given below; the lead-preserving one is the recommendation and the raw-tick one is
documented because it is a *useful mis-retime demonstrator* — a second, subtler artifact alongside the
gate's "omit the program edit" one.

---

## 5. FIVE CORRECTIONS TO THE STANDING RECORD

### 5.1 The frame-number field is **10 bits**, not 13 — and `summon_camera.FRAME_MASK` is wrong in principle

`summon_camera.py` uses `FRAME_MASK = 0x1FFF` / `FRAME_MARK_MASK = 0xE000` (W1 §2.3). The native
stepper masks with `0x3FF` and folds bits **10–15** into a flags composite above the 16 `CodeFlags`
bits. On stock data the two readings are indistinguishable — **0 of 7,307 Codes set bits 10–12**, the
largest frame number corpus-wide is **451**, and the only high-bit values observed are `0x2000` (19),
`0x4000` (75) and `0x6000` (3), i.e. exactly bits 13 and 14. So W1's round-trip could not have caught
it and did not need to.

It matters the moment anything **writes** a frame:

* a frame number of 1024–8191 would pass W1's mask, then be read by the engine as `value & 0x3FF`
  (firing at the wrong time) with bits 10–12 spuriously appearing as flags;
* the counter saturates at 1023, so a frame ≥ 1024 can never be matched anyway. Because the fire test
  is an **equality** compare and the cursor is only advanced when a Code fires, an unmatchable frame
  word **parks the cursor forever** — the shot freezes on its last applied pose and every later
  keyframe in the block is dead. Silent, and the exact failure class a retime could introduce.

**W3 action:** clamp/validate frames to `1 ≤ f ≤ 1023` and mask with `0x3FF` when writing. Do not
change `summon_camera.py` for this recon — it is a W3 tooling task with its own test.

### 5.2 The frame word's high bits are DECODED

W1 left them "live, undecoded, preserve verbatim". Both live bits now have a mechanism:

| bit | count | meaning | evidence |
|---|---:|---|---|
| `0x4000` | 78 Codes (incl. 3 with `0x6000`) | **FREEZE THE CAMERA CLOCK.** Sets the pause flag `0x2200b2`, which gates the counter increment. Cleared only by a fresh install. **67 of 78 sit on local frame 1** — i.e. the idiom is "hold this single pose until the sequence plays another camera." | `test r14d,0x100100` @`0x136ef` → `0x13707`; gate @`0x13ad6` |
| `0x2000` | 22 Codes (20 on local frame 1) | **Suppress the battle-camera restore.** Sets `0x21ff49`; the restore routine `0x12fd0` skips its re-parse of the raw17 battle camera when it is set, then clears it. | `bt r14d,0x13` @`0x1385c`; consumer @`0x12ff4`/`0x13023` |
| `0x8000` | 0 | composite bit 21, never tested in the stepper | — |

`CodeFlags 0x100` (C#'s `UNKNOWN_FLAG_1`) is the *other* input to the same pause OR-gate — and it
appears **0 times** in the corpus, so `0x4000` is the only pause trigger in practice.

**W3 action:** a retime tool must (a) preserve the high bits through the mask (`new = (old & 0xFC00) |
((old & 0x3FF) + N)`), and (b) **refuse or warn** when shifting keyframes that sit after a `0x4000`
Code in the same track — they are unreachable, so shifting them is a no-op and the "retime did
nothing" symptom would be blamed on the delivery path. **ef227 carries no high bits at all** (all
three shots, all 28 Codes), so neither applies to the W3 target.

### 5.3 The movement duration is a **byte** at runtime, not the u16 the format declares

The stepper reads `byte[dur+0]` only (`0x13676`). Corroborated blind by the corpus: over 3,537
movement blocks the maximum duration is **exactly 255**, hit twice, with nothing above and only 13
values ≥ 200. A u16 field whose 3,537 samples stop dead at 255 is a byte field.

(Byte `+1` — the duration's would-be high byte — is read as a **signed** value shifted left 5 when the
channel's 3-bit group code is 4, i.e. movement without position. That combination requires `CodeFlags`
`0x04`/`0x20`, which never occur, so it is dead data today.)

**W3 action:** any duration edit must stay in `0..255`. A stretch that pushes a movement duration past
255 would silently truncate mod 256 — a very fast move where a slow one was intended.

### 5.4 `CodeFlags 0x8000` (`unk6`) is the hand-back to the battle camera — and it explains W1's one loose capture row

The `0x8000` path (`0x13b18`–`0x13bfb`) re-invokes the block parser `0x13030` on
`[0x211e60] + (s16)word[+2]` — the raw17 `camOffset` idiom `SFXDataCamera.LoadFromBSC` uses verbatim —
then returns non-zero, which makes `SFX_UpdateCamera` run the stepper a second time in the same host
frame **without advancing the counter**. Because `0x13030` re-seeds the counter to 1, the newly
installed track starts from its own frame 1.

ef227 **shot C's second and last Code is exactly this**, at local frame 25 → abs seq tick 504. W1 §3
records that the capture's final H change at frame 553 was "still unexplained by camera data". With
W1's own camera origin of 47, that Code fires at capture frame `504 + 47 = 551`; the re-parse seeds the
new track's counter to 1 so the battle camera's own first Code fires immediately after, and its focal
lands a frame or two later — the observed 553, and an H of **300** that belongs to the battle camera,
not to ef227. **The row is accounted for by camera data after all: shot C's last Code ends the
cinematic camera and hands the battle its own back.** (The residual 2 frames are the same ±1–2 the
rest of the two-clocks record carries; the mechanism is MEASURED, the exact landing frame is not.)

**W3 action:** that Code is scheduled by a frame word like any other, so it moves with the timeline. If
it does not move, the cinematic hands back early — a very visible failure.

### 5.5 D4 §2.3's "zero-duration keyframe consumes two steps" is superseded

Same-frame Code pairs are consumed by the stepper's own inner loop (up to 10 per tick); the double
`0x1e88`/`0x1e91` call is the `0x8000` hand-back (§5.4). No duration is involved in either.

---

## 6. ef227 — THE THREE SHOTS, located and timed

Full per-Code dump with every byte offset: `C:\gd\SCRATCH\summon-format\retime-w3-recon\A3-ef227-camera.txt`.

### 6.1 The blocks

| shot | install op | file offset of op | seq tick | chunk | id-2 sub-file | block @file | size | outer flags | groups | sequences | anchors |
|---|---|---|---:|---:|---:|---|---:|---|---|---:|---|
| **A** | `0x29 PLAY_CAMERA` arg1=6 arg2=0 | `0x40f` | **11** | 0 | 6 | `0x29d44`–`0x29e04` | 192 B | `0x0009` | `sequence0[6..186)` + `selector[186..192)` | **1** | **absent** |
| **B** | `0x29` arg1=16 arg2=0 | `0x499` | **255** | 1 | 16 | `0xbeafc`–`0xbebe0` | 228 B | `0x0009` | `sequence0[6..222)` + `selector[222..228)` | **1** | **absent** |
| **C** | `0x29` arg1=47 arg2=0 | `0x508` | **480** | 1 | 47 | `0xc3ac8`–`0xc3af0` | 40 B | `0x0009` | `sequence0[6..36)` + `selector[36..40)` | **1** | **absent** |

id-2 archive bases: chunk 0 @`0x29800`, chunk 1 @`0xbb000`. `arg2 == 0` on all three, so no shot is
runtime-chosen. **All three declare exactly one sequence** — the three-sequence trap does not apply,
re-confirming W2's X3 from a second walk. The selector region is present on all three (6/6/4 B) and
encodes no time (§2).

### 6.2 Shot A — the retime target (11 Codes + terminator)

`local` = frame word `& 0x3FF`; `abs` = `11 + local − 1`; offsets are block-relative / container-absolute.

| # | local | abs | CodeFlags | frame word @blk | @file | duration fields |
|---:|---:|---:|---|---:|---|---|
| 0 | 1 | 11 | `0x0809` | 6 | `0x29d4a` | `focal.duration` @blk 22 / `0x29d5a` = **1** |
| 1 | **71** | **81** | `0x0809` | **26** | **`0x29d5e`** | `focal.duration` @blk 42 / `0x29d6e` = **1** |
| 2 | 96 | 106 | `0x0809` | 46 | `0x29d72` | `focal.duration` @blk 62 / `0x29d82` = **1** |
| 3 | 121 | 131 | `0x0009` | 66 | `0x29d86` | — |
| 4 | 121 | 131 | `0x0002` | 82 | `0x29d96` | `cammove.duration` @blk 92 / `0x29da0` = **26** |
| 5 | 148 | 158 | `0x0009` | 96 | `0x29da4` | — |
| 6 | 148 | 158 | `0x0002` | 112 | `0x29db4` | `cammove.duration` @blk 122 / `0x29dbe` = **32** |
| 7 | 180 | 190 | `0x0009` | 126 | `0x29dc2` | — |
| 8 | 186 | 196 | `0x0003` | 142 | `0x29dd2` | `cammove.duration` @blk 152 / `0x29ddc` = **12** |
| 9 | 198 | 208 | `0x0002` | 156 | `0x29de0` | `cammove.duration` @blk 166 / `0x29dea` = **20** |
| 10 | 218 | 228 | `0x0002` | 170 | `0x29dee` | `cammove.duration` @blk 180 / `0x29df8` = **24** |
| — | terminator | — | — | 184 | `0x29dfc` | — |

Shot A's own span is 242 local frames (Code 10 at f218 + a 24-frame move) = abs 11..252; shot B
installs at 255, three ticks later.

### 6.3 Shots B and C

Shot B: 15 Codes at local frames 1, 1, 37, 37, 54, 82, 91, 101, 115, 115, 134, 134, 166, 210, 210;
`cammove` durations 31, 16, 27, 10, 14, 6, 16, 27, 41; one `focal.duration` = 1 at f1. Frame words at
block offsets 6, 26, 40, 50, 64, 78, 88, 102, 116, 132, 146, 162, 176, 190, 206.
Shot C: 2 Codes — f1 (`0x0809`, `focal.duration` = 1) and f25 (`0x8000`, the battle-camera hand-back,
§5.4). Frame words at block offsets 6 and 26.

### 6.4 Cross-check against W2

W2 changed four bytes at file `0x29d51`, `0x29d52`, `0x29d5c`, `0x29d5d` and named them Code 0's
orientation, roll and the two halves of H. Independently here: Code 0's block starts at blk 10, so
`campos` is blk 10–15 (orientation = blk 13 = file `0x29d51`, roll = blk 14 = `0x29d52`) and `focal`
is blk 22–25 (distance = blk 24–25 = `0x29d5c`–`0x29d5d`). **Exact agreement, by two different walks.**
W2's "shot A's next focal keyframe is at local frame 71" is also confirmed.

---

## 7. THE EDIT LIST — stretch/shrink `ef227:c0` state 0 by N

Three edits, in three different places, all required:

| # | layer | edit | owner |
|---|---|---|---|
| **E1** | program (id-3 image, chunk 0) | the single threshold immediate **69 → 69+N**, the `slti $v0,$s5,69` at image offset `0x1278` (R3 §6) | A2 |
| **E2** | sequence stream | add **N** to the `WAIT` at file **`0x430`** (currently 46 ticks, carrying 35 → 81) so every op at tick ≥ 81 fires N later — including `RUN_PROGRAM` c1 @`0x4a2`, `PLAY_CAMERA` B @`0x499`, `PLAY_CAMERA` C @`0x508` | A1 |
| **E3** | camera block, **shot A only** | the frame-word list below | **this slice** |

### E3 — the exact in-block edit list (RECOMMENDED: lead-preserving, cut at abs 81 / local 71)

Ten u16 writes into the shot A sub-file. Each is
`new_word = (old_word & 0xFC00) | (((old_word & 0x3FF) + N) & 0x3FF)`, written little-endian.

| blk off | file off | local frame | → | abs tick | → |
|---:|---|---:|---|---:|---|
| 26 | `0x29d5e` | 71 | 71+N | 81 | 81+N |
| 46 | `0x29d72` | 96 | 96+N | 106 | 106+N |
| 66 | `0x29d86` | 121 | 121+N | 131 | 131+N |
| 82 | `0x29d96` | 121 | 121+N | 131 | 131+N |
| 96 | `0x29da4` | 148 | 148+N | 158 | 158+N |
| 112 | `0x29db4` | 148 | 148+N | 158 | 158+N |
| 126 | `0x29dc2` | 180 | 180+N | 190 | 190+N |
| 142 | `0x29dd2` | 186 | 186+N | 196 | 196+N |
| 156 | `0x29de0` | 198 | 198+N | 208 | 208+N |
| 170 | `0x29dee` | 218 | 218+N | 228 | 228+N |

**Codes that do NOT move:** Code 0 only (local frame 1, block offset 6). It is locked to c0's *entry*
at tick 12, which a length change does not move.

**Duration fields that change: NONE.** The straddle test — *a pre-cut Code's interpolation must have
completed by the cut, i.e. `f + d ≤ cut`* — has exactly one candidate, Code 0's `focal.duration` = 1,
giving `1 + 1 = 2 ≤ 71`. Shot A starts no movement at all before local frame 121, so nothing
interpolates across the stretched interval. **Every one of shot A's 5 movement durations and 3 focal
durations stays byte-identical**, which is what makes W3's "the beats still land" claim checkable: the
only bytes that move are the ten schedule words.

### E3-alt — the raw-tick variant (cut at abs 82 / local 72), documented as a demonstrator

Identical minus the first row: **9** frame words, and Code 1 (f71) stays. This variant is exactly
"shift every camera event at seq tick ≥ 82" and it **breaks one authored lock** — f71 stays at abs 81
while the s0→s10 beat moves to 82+N. Useful precisely because it is a *smaller, subtler* drift than
the gate's primary artifact (omit E1 entirely), and it demonstrates that the lock is real: if the
playtester cannot tell E3 from E3-alt at N = +30, the lock claim is weaker than this report asserts.

### Shots B and C — nothing changes inside either block. Verified, not assumed.

Their local frames are relative to their own install op, and the parser re-seeds the frame counter to 1
at **every** install (`0x13030 @0x1304f`), so a block carries no absolute time. E2 moves both install
ops by N, and it moves c1's `RUN_PROGRAM` (file `0x4a2`, same tick 255) by the same N, so c1's entire
phase spine and both shots translate together and all of their leads (0, 0, 0, +1, …) are preserved by
construction. **Zero in-block bytes change in shot B (228 B) and shot C (40 B).**

The one thing that would break this: an E2 that inserts the delay *between* `PLAY_CAMERA` B and
`RUN_PROGRAM` c1 — they share tick 255 and file offsets `0x499`/`0x4a2`. Insert before both.

---

## 8. BOUNDS ON N, and the guard list

| bound | value for this edit | why |
|---|---|---|
| **frame word must never become 0** | `N ≥ −70` | 0 is the sequence terminator; a frame of 0 truncates the shot at that Code |
| frame number ceiling | `N ≤ 805` | field is 10 bits and the counter saturates at 1023; largest moved frame is 218 |
| **phase content floor** | `N ≥ −44` | c0 s0's own internal gates are `clock ≥ 12` and `clock ≥ 24` (R3 §3); a threshold of 69+N below 24 guts the phase. **This is the binding floor.** |
| movement duration ceiling | not reached | no duration is edited; if a future straddle edit adds N to one, keep it ≤ 255 (§5.3) |
| block length | unchanged | frame words are edited in place; the id-2 directory never moves (W2's constraint 2 still holds) |
| lock preservation | exact for all pairs | every event at abs ≥ 81 moves by N; every event at abs ≤ 80 stays; the only pair spanning the cut is (81, 82) and both sides move |

Guards a W3 tool should enforce at the call site:

1. `1 ≤ (old & 0x3FF) + N ≤ 1023` for every rewritten word — refuse otherwise.
2. Preserve `old & 0xFC00` verbatim (§5.2).
3. Refuse if any Code **before** the cut in the same track carries `frame_word & 0x4000` — everything
   after it is unreachable and the retime is a silent no-op.
4. Run the straddle test on every pre-cut Code (`f + d ≤ cut` for `cammove`, `tgtmove`, `focal`,
   `unk5+2`); refuse or auto-extend by N, do not ignore.
5. Assert the re-serialised block length is unchanged (W2's `rescore_block` already does this).
6. Assert the frame words remain strictly non-decreasing within a track.

---

## 9. VERIFICATION PERFORMED

`a3_probe.py shift` applies E3 to a **copy** in SCRATCH and re-runs the whole W1 path:

| N | frame words rewritten | container bytes changed | block length | codec round-trip | container camera blocks |
|---:|---:|---:|---:|---|---|
| **+12** | 9 (raw-tick variant) | 9 | 192 → 192 | **BYTE-EXACT** | **3/3 byte-exact** |
| +40 | 9 | 10 | 192 → 192 | **BYTE-EXACT** | — |
| +100 | 9 | 13 | 192 → 192 | **BYTE-EXACT** | — |
| −24 | 9 | 9 | 192 → 192 | **BYTE-EXACT** | — |

(The byte count exceeds the word count when a shift carries a frame number across a 256 boundary and
the word's high byte changes too — the edit is a u16 write regardless.) The patched container is the
same 823,296 bytes, every changed offset lands inside shot A's sub-file, and all three camera blocks
still parse and re-serialise byte-identically through the **unmodified** `camera_codec`. The patched
copy is `C:\gd\SCRATCH\summon-format\retime-w3-recon\A3-shift-sim-container.bin` — never deployed.

---

## 10. WHAT THIS SLICE DOES NOT SETTLE

* **Whether the −1 lead is intent or coincidence.** Six consecutive pairs plus the sequence's own
  tick-81/82 ops is strong, but it is a pattern argument. The falsifier is cheap and belongs in W3's
  cast: build E3 and E3-alt at the same N; if they read identically, the lock is weaker than claimed.
* **The interrupted-move class.** 30.2 % of corpus movements are cut short by the next keyframe. Under
  a uniform shift of all post-cut Codes their relative spacing is preserved, so nothing changes — but a
  *non-uniform* retime (different N per phase) would change how far each interrupted move gets. Out of
  scope here; a real constraint for any future multi-phase retime.
* **`unk5`'s three non-duration bytes** and what `0x14350` does with the countdown. Named, not decoded.
  ef227 never uses `unk5`.
* **The pause flag's full write set** (§1 row 11) — a register-based bulk clear could evade a
  rip-relative xref scan. It does not affect ef227, which sets no pause bits.
* **The selector's input grammar** and **outer flags bit 9** — still D4 §4 open items, carried verbatim.
* **Anything geometric.** No pose byte was decoded, predicted or edited here.

---

## 11. FILES

| path | what |
|---|---|
| `studies/custom-summons/tier-w/w3-recon/A3-CAMERA.md` | this report |
| `C:\gd\SCRATCH\summon-format\retime-w3-recon\a3_probe.py` | the probe (verbs `ef227` / `corpus` / `shift`) |
| `C:\gd\SCRATCH\summon-format\retime-w3-recon\A3-ef227-camera.txt` | **the decoded keyframe dump** — every Code of all three shots with every time-field offset |
| `…\A3-corpus-stats.txt` | the 372-container measurements (duration-vs-delta, frame bounds, high bits, duration ranges) |
| `…\A3-lock-and-editlist.txt` | the lock table + both candidate edit lists + the straddle test |
| `…\A3-shift-sim.txt`, `…\A3-shift-sim-container.bin` | the round-trip proof and its patched copy |
| `…\A3-seq-ops.txt` | the ef227 sequence stream with accumulated ticks (for A1) |
| `…\A3-extras.txt`, `…\stepper_13540.txt`, `…\stepper_13800.txt` | flag census; the stepper disassembly the native claims cite |

**Provenance.** Stock bytes were read from the user's own extraction at `C:\gd\SCRATCH\summon-format\`
and from a read-only static parse of the user's own installed `FF9SpecialEffectPlugin.dll`. This report
contains structure, offsets, field names, frame numbers, durations and RVAs — **no hex run of stock
bytes of any length**, no pose data, no geometry. Every decoded dump stays in SCRATCH.
