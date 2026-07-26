# A1 — THE SEQUENCE-STREAM TICK ENCODING (W3 recon)

**Question:** how does ef227's binary sequence stream encode TIME, and can every op at seq tick ≥ 82 be
shifted by ±N with a same-length in-place byte edit?

**Read-only rung.** Nothing was written to the game install, no stock file was modified, no repo code was
changed. Decoded stock dumps live at `C:\gd\SCRATCH\summon-format\retime-w3-recon\`
(`A1-ef227-seq-ops.txt` — the complete 93-op table, the probes, and the camera-block keyframe list).

---

## 0. HEADLINE

> **Time is pure DELTA. There is not one absolute tick field anywhere in the stream.** The clock is the
> running sum of `WAIT` (`0x01`, `arg1 == 0`) ops, whose `arg2` is a **single byte** of ticks. Every other
> op is instantaneous and carries no time at all.
>
> **Consequence: shifting every op at seq tick ≥ 82 by +N is a ONE-BYTE edit.** 74 of ef227's 93 ops move,
> and *none of their own bytes change* — they move on the clock, not in the file. The byte is the `arg2`
> of the WAIT that spans tick 81 → 82, at file offset **`0x438`**, stock value **1**.
>
> **And the same-length constraint that dominates W2 does not exist here at all.** The sequence lives in
> the header sector, whose length no field describes; ef227 has **745 unused bytes = 248 spare op slots**
> after its terminator, so W3 may *insert* ops as well as retune them, with zero container reshuffle.

**But one thing found in this recon is bigger than the encoding question and should be read first:
§7.2, THE THIRD CLOCK.** In the mode the user's install actually runs, the binary sequence's sounds,
background fades, character show/hide and the damage EffectPoint are **swallowed by the engine** and
re-issued from a *separate managed text file* that ef227.bytes does not contain. A retime of the binary
moves the camera and the creature program and nothing else. That is not a blocker — it is arguably a
cleaner W3 — but it changes what "everything downstream must move with it" means, and it adds one file
to the edit set.

---

## 1. Method, and how each fact was verified

| step | tool / authority |
|---|---|
| container walk | `thomas-swap/disasm/ef_container.py::parse_header` (a port of native fn `0xd390`), **strict** mode: it refuses unless the resource table's running cursor lands exactly on the file length. It did — `0xc9000`, to the byte. |
| the op stream | `ef_container.parse_sequence` (a port of fn `0x315f1`'s fetch/dispatch head) + `ef_container.opcode_status` (the native jump/qword dispatch tables). |
| the tick derivation | `tier-w/summon_camera.py::walk_camera_ops` — the *strict* clock (blocking waits counted, not summed). Re-implemented independently in the dump script and the two agreed op-for-op. |
| camera blocks | `summon_camera.extract_shots` → `ff9mapkit/battle/camera_codec.py`, unmodified. All 3 ef227 blocks re-serialise **byte-identical**, so the frame lists below are lossless reads, not guesses. |
| corpus checks | all **372** extracted stock containers under `C:\gd\SCRATCH\summon-format\`. |
| engine behaviour | direct read of the patched Memoria tree at `C:\gd\FFIX\Memoria\` (it contains `SfxHybridDrive`, i.e. it *is* the s58 dev-engine source), plus the user's own `Memoria.ini`. |

Source blob: `ef227.bytes`, 823,296 B, sha256 `fe590d…d167` — **matches** the drift guard both
`ef_camera_decode.py` and `rescore.py` registered, so this is the same container W2 cast from.

Everything below is labelled **MEASURED** (I ran it this session), **INHERITED** (a prior round measured
it; cited) or **INFERRED** (my reasoning, falsifiable, marked).

---

## 2. THE STREAM — one stream, both chunks

**MEASURED.** ef227 has exactly **one** sequence stream. It starts at file `0x400` (inside the header
sector), runs **93 ops × 3 bytes = 279 B**, and ends at `0x517` on a real `END` op.

It drives **both** chunks: `LOAD_CHUNK 0` is op #0, `LOAD_CHUNK 1` is op #50 at tick 255, and the two
`0x80` RUN_PROGRAM ops (both program index 0) fire at ticks **12** (chunk slot 0) and **255** (chunk
slot 1) — exactly the two program origins W1 reported. `summon_camera.walk_camera_ops` independently
returns `program_starts = {(0,0): 12, (1,0): 255}`. So the "c0 at 12 / c1 at 255" pair is one stream
switching chunks, not two streams.

**Op census (MEASURED).** All 93 ops are `VALID` under the native dispatch map — zero in the assert holes,
zero in the illegal `0x30..0x4F` band.

| opcode | count | native handler | name status |
|---|---:|---|---|
| `0x00` END/HOLD | 1 | `0x31aad` | read directly (INHERITED) |
| `0x01` WAIT | **34** | `0x31680` | read directly (INHERITED) |
| `0x02` SET_CHANNEL_FLAG | 1 | `0x316af` | read directly (INHERITED) |
| `0x03` | 1 | `0x316c0` | **unnamed** |
| `0x04` | 1 | `0x316f9` | **unnamed** |
| `0x05` LOAD_CHUNK | 2 | `0x31712` | read directly (INHERITED) |
| `0x06` | 2 | `0x3172d` | **unnamed** |
| `0x09` | 2 | `0x3181a` | **unnamed** |
| `0x0A` | 1 | `0x3184b` | **unnamed** |
| `0x0B` | 2 | `0x31cc5` | **unnamed** |
| `0x0F` | 1 | `0x3198d` | **unnamed** |
| `0x24` | 6 | `0x3be40` | C# hypothesis "SHOW_HIDE_CHARACTERS" |
| `0x25` | 2 | `0x3bab0` | C# hypothesis "EFFECT_POINT" |
| `0x28` | 1 | `0x3b0d0` | C# hypothesis "PUT_BACK_IN_SLEEP_MODE" |
| `0x29` PLAY_CAMERA | 3 | `0x3bbd0` | read directly (INHERITED) |
| `0x2A` | 8 | `0x3bd10` | C# hypothesis "SET_BATTLE_SCENE_TRANSPARENCY" — **now corroborated**, §6 |
| `0x2C` | 2 | `0x39dc0` | **unnamed** |
| `0x2D` PLAY_SOUND | 16 | `0x3bf00` | read directly (INHERITED) |
| `0x2E` | 5 | `0x3bf60` | **unnamed** |
| `0x80` RUN_PROGRAM | 2 | `0x49170` | read directly (INHERITED) |

ef227 uses **no** `0x23 SETUP_CAMERA` — W1 §2.1's warning that `0x23` carries 89 % of the corpus's camera
blocks does not bite here. All three shots are `0x29` with `arg2 = 0` (literal), so none is runtime-chosen.

---

## 3. (a) HOW TIME IS ENCODED — delta, one byte, one opcode

**MEASURED + INHERITED.** The record format is a flat 3-byte `(code, arg1, arg2)` stream. There is **no
tick field on an op**, no timestamp column, no absolute time anywhere. The only carrier of time is:

```
WAIT (code 0x01), arg1 == 0   ->  wait arg2 ticks        (native handler 0x31680 stores arg2 as the countdown)
WAIT (code 0x01), arg1 != 0   ->  block while channelFlag[arg2] != 0   (duration NOT statically known)
```

* **Integer width: `arg2` is ONE BYTE (u8).** Mechanical ceiling 255.
* **Corpus envelope (MEASURED, 372 files):** 1,931 non-blocking WAITs, `arg2` ∈ **[1, 240]**, 91 distinct
  values. **`arg2 == 0` occurs ZERO times in the entire stock corpus.** Treat 0 as unattested and unsafe —
  it is the shrink floor, not 0-is-fine.
* Every other op costs **zero** ticks. Ops between two WAITs all fire on the same tick.
* **Blocking waits are everywhere and must not be summed:** 1,103 of them across **372/372** files. ef227
  has exactly **one**, op #2 at file `0x406`, at tick 0 — a load-gate (`SET_CHANNEL_FLAG` is the op before
  it). Its duration is a runtime property, which is *why* the derived tick clock is not `SFX.frameIndex`
  and needs W1's one additive origin. It sits **before everything**, so it shifts both clocks equally and
  cancels out of every offset. ✔ It is not a retime hazard.
* ef227's authored total: **511 ticks**, over **34 distinct tick values**:

  `0 · 11 · 12 · 26 · 35 · 81 · 82 · 106 · 120 · 130 · 131 · 132 · 158 · 188 · 216 · 255 · 290 · 296 ·
  302 · 338 · 362 · 366 · 368 · 372 · 386 · 398 · 449 · 451 · 463 · 471 · 479 · 480 · 492 · 511`

**Why the 1-tick-per-WAIT-unit reading is trustworthy (INHERITED, W1c):** three camera events derived at
ticks 11 / 106 / 255 land on captured host frames 58 / 153 / 302 with **one constant origin (47) and zero
residual**, and the phase boundaries derived at 12 / 107 / 255 land on 57 / 152 / 300 with **one constant
origin (45), zero residual**. Two three-point fits with one free parameter each, over ~500 frames, is a
strong proof that a WAIT unit *is* a host frame.

**Refuted en route (adversarial):** ef227 looks like it has a second duration carrier — op `0x2E(0,11)` at
tick 0 is immediately followed by `WAIT 11`, and its other uses are `(2,4) (2,4) (2,8) (2,18)`. The
corpus histogram kills it: `0x2E`'s `arg2` across 372 files is `64, 16, 27, 32, 2, 8, 10, 139, 81, 35…` —
not duration-shaped. **`0x2E` stays UNKNOWN; the tick-0 coincidence is a coincidence.** (`0x2A`'s `arg2`
*is* a duration, but a fade length internal to that op — §6.)

---

## 4. THE TICK MAP AT THE EDIT SITE

Program-clock arithmetic, re-derived (**MEASURED** sequence side, **INHERITED** thresholds from
`EF227-CHOREOGRAPHY.md` §2):

| | |
|---|---|
| `ef227:c0` starts | seq tick **12** (the `0x80` op) |
| `c0` state 0 guard | `clock >= 69` → 70 program ticks → seq ticks **12 … 81** |
| `c0` enters state 10 | seq tick **82** ← the boundary this rung stretches |
| `c0` state 10 guard | `clock >= 24` → 25 ticks → `c0` enters state 1 at seq tick **107** |

So the window the brief names, **[82, 107)**, is exactly phase `c0` s10 — a complete phase, start to end.

**The co-timed pair that straddles the boundary (MEASURED — this is the load-bearing new number).**
Seq tick **81** is the *last* tick of state 0, and two authored events sit on it:

* sequence op `0x2A(77, 0)` at file `0x433`;
* **shot A's keyframe at local frame 71** (abs tick 11 + 71 − 1 = **81**) — the keyframe W2's cast used as
  its "snaps back to stock framing" self-evidence.

That means the retime has **two defensible anchors**, and they are not equivalent:

| anchor | what it means | WAIT byte to edit | ops that move | shot-A keyframes that move |
|---|---|---|---|---|
| **A — boundary 82** | stretch the gap *after* the tick-81 pair. The pair stays glued to seq tick 81, i.e. N ticks *before* the new phase end. | `0x438` (stock **1**) | **74 / 93** | local frame **≥ 72** → 9 of 11 |
| **B — boundary 81** | stretch the gap *before* the tick-81 pair, so the pair rides the phase's END. | `0x432` (stock **46**) | **76 / 93** | local frame **≥ 71** → 10 of 11 |

**Recommendation (INFERRED):** anchor **B**. The tick-81 pair is authored *to* the end of the entrance
phase (a background-transparency change landing on the camera's hold), and B is also the only anchor with
a usable shrink budget (§5). B is what the brief's own phrasing — "shot A camera keyframes at local frame
≥ 71ish" — already assumes.

---

## 5. (b) THE EDIT — exactly which bytes, and the bounds

### 5.1 The sequence stream: ONE byte

**MEASURED.** Because time is delta-encoded and no op carries a timestamp, a downstream shift is a change
to a single `arg2`:

| anchor | file offset | field | stock | after |
|---|---|---|---|---|
| A | `0x438` | `WAIT.arg2` of the op at `0x436` | 1 | 1 + N |
| B | `0x432` | `WAIT.arg2` of the op at `0x430` | 46 | 46 + N |

**Nothing else in the 279-byte stream changes.** All 74 (or 76) shifted ops keep their exact bytes at
their exact offsets — including the `END`, all three `PLAY_CAMERA`s, and the second `RUN_PROGRAM`.

Both anchors are *clean*: the WAIT immediately precedes the first op that must move, so the shift set is
exactly "tick ≥ boundary" with no op caught in between.

### 5.2 Maximum +N

| bound | anchor A | anchor B | why |
|---|---:|---:|---|
| the `arg2` byte (mechanical) | **+254** | **+209** | u8 ceiling 255 |
| stock-attested envelope | +239 | +194 | corpus max `arg2` = 240 |
| camera frame word | ≫ | ≫ | 13-bit frame field, ceiling 8191 |
| shot A vs shot B collision | none | none | shot A's last move ends at abs 252 and shot B installs at 255; **both shift by the same N**, so the 3-tick margin is preserved |

**Practical answer: +N is not the binding constraint.** Anything up to ~+200 fits in one byte. If more is
ever wanted, both gaps can be fed (up to +463 combined), at the cost of the tick-81 pair moving by only
the first component.

### 5.3 Maximum −N — this is the tight side, and it picks the anchor

Three independent floors; the smallest wins.

| floor | anchor A | anchor B | source |
|---|---:|---:|---|
| the WAIT itself may not reach 0 (unattested corpus-wide, §3) | **−0** (stock value is 1) | **−45** (46 → 1) | MEASURED, 372-file corpus |
| shot A's frame list must stay non-decreasing | −25 (`96` must stay ≥ `71`) | −70 (`71` must stay ≥ `1`) | MEASURED, the block's own frames |
| the phase must outlive its own internal work — `c0` s0's last internal guard is `clock >= 24` | −45 | −45 | INFERRED from `EF227-CHOREOGRAPHY.md` §3 |
| **binding** | **≈ 0 — anchor A cannot shrink at all** | **−45** | |

So: **anchor A can only stretch; anchor B can stretch to ~+209 and shrink to −45**, and at exactly −45 the
program threshold reaches `69 → 24`, which is also where the phase's own beats would start falling off the
end. Two unrelated floors landing on the same number is a good sign the number is real.

*(A `WAIT arg2 = 0` is mechanically expressible and might well mean "no wait". It is simply never done in
827 KB × 372 files of shipping data, and the native countdown's width is unread. Do not spend the rung's
one in-game test on it.)*

### 5.4 The rest of the edit set (for the record — other agents' scope)

| layer | bytes | same-length? |
|---|---|---|
| sequence stream | **1** (§5.1) | yes — trivially |
| camera **shot A** — chunk 0, id-2 sub-file 6, file `[0x29d44 .. 0x29e04)`, **192 B**, 1 declared sequence, 11 keyframes | **9 × u16 frame words = 18 B** (anchor A) or **10 × u16 = 20 B** (anchor B) | **yes** — u16 fields rewritten in place; block length, Code count, every duration and every pose byte untouched, so W1's four byte-exactness invariants and W2's X1/X2 self-check all still apply |
| camera **shot B** (`[0xbeafc..0xbebe0)`, 228 B) and **shot C** (`[0xc3ac8..0xc3af0)`, 40 B) | **ZERO** | n/a — their install ops are at ticks 255 and 480, both ≥ 82, so they shift **for free** with the sequence. Only the shot that *straddles* the stretch point needs in-block work. |
| the effect program `ef227:c0` | the `slti` immediate at image `0x1278` (low 16 bits), 69 → 69+N | yes — one instruction word, immediate field |

**Shot A's frame list (MEASURED, timing only):** `1, 71, 96, 121, 121, 148, 148, 180, 186, 198, 218`
(+ the frame-0 terminator). Duplicated frames at 121 and 148 are real — `rescore.py` already refuses to
target a duplicated frame without an explicit `occurrence`, and a retime tool must add N to **both**
members of each pair. All 11 frame words have `marks == 0x0000`, so W1 §2.3's high-bit hazard does not
arise on this block — but a tool must still mask, because the corpus has 97 keyframes that do set them.

**Shot A's abs-tick alignment before the edit** (why the frame edits and the sequence edit have to agree):
`abs = 11 + local − 1` gives 11, **81**, **106**, 131, 131, 158, 158, 190, 196, 208, 228 — and sequence ops
fire at 81, 106, 131, 158, 188… The two tracks are interleaved by construction, exactly as W1 measured
(19 of 31 camera events within 4 ticks of a phase boundary).

---

## 6. (c) EVERYTHING IN THE WINDOW [82, 107)

**MEASURED — 11 ops, on two ticks.** All of them move under either anchor.

| seq tick | file | op | args | what it is |
|---:|---|---|---|---|
| 82 | `0x439` | `0x06` | (1, 0) | **unnamed**, native `0x3172d`. Its only other use is `(0,0)` at tick 35 — an on/off pair around the entrance phase. |
| 82 | `0x43c` | `0x2D` PLAY_SOUND | (19, 255) | sound sub-file 19 |
| 82 | `0x43f` | `0x2D` PLAY_SOUND | (20, 255) | sound sub-file 20 |
| 82 | `0x442` | `0x2D` PLAY_SOUND | (21, 255) | sound sub-file 21 |
| 82 | `0x445` | `0x2D` PLAY_SOUND | (22, 255) | sound sub-file 22 |
| 82 | `0x448` | `0x2E` | (2, 4) | **unnamed**, native `0x3bf60` |
| 82 | `0x44b` | `0x01` WAIT | (0, 24) | 82 → 106 |
| 106 | `0x44e` | `0x24` | (0, 1) | C# hypothesis "show/hide characters" |
| 106 | `0x451` | `0x2E` | (2, 4) | **unnamed** |
| 106 | `0x454` | `0x09` | (127, 1) | **unnamed**, native `0x3181a`. Its twin at tick 216 pairs with the *other* music cue, so a stream/song trigger is likely (INFERRED). |
| 106 | `0x457` | `0x01` WAIT | (0, 14) | 106 → 120 |

**Reading this against the brief.** W1 saw one thing in this window — the camera event at tick 106
(`H → 415`, shot A's local frame 96). Everything else above is new to the W-tier record. Three notes:

1. **The window is a sound burst.** Four `PLAY_SOUND` ops land on the very tick the phase changes (82).
   Four more land at tick 26 and tick 188, four more at 290 — a 4-op quadruple is this effect's idiom.
2. **Tick 106 is the "arriving at s1" beat, one tick early**, matching the authored −1 lead W1 measured.
   The `0x24` + `0x2E` + `0x09` trio and shot A's keyframe 96 all fire together there.
3. **The boundary tick 81 is *not* in the window but is the one to worry about** — see §4. It carries
   `0x2A(77,0)`, and `0x2A`'s hypothesised name is now corroborated independently: the managed text
   sequence (§7.2) has a `SetBackgroundIntensity: Intensity=0.6015625` at the matching moment, and
   **77 / 128 = 0.6015625 exactly**. All eight of ef227's `0x2A` ops pair with a managed
   `SetBackgroundIntensity` whose `Intensity` is `arg1 / 128` exactly (255 clamping to 1.0) — **8 / 8** —
   and whose `Time` equals `arg2` on **6 / 8**, differing by 1 on the other two. So `0x2A(arg1, arg2)` =
   *set background intensity to `arg1/128` over `arg2` ticks* — **MEASURED by correspondence**, no longer
   a C# guess. `arg2` is therefore a real duration, but one internal to the op: it rides along with a
   shift and needs no edit.

---

## 7. (d) WHAT ELSE REFERENCES ABSOLUTE SEQUENCE TICKS

### 7.1 Inside the container: **nothing.**

**MEASURED, item by item.**

* **No length or op-count field for the stream.** It is self-terminating on code `0x00`. Nothing declares
  where it ends.
* **The chunk/resource table** (file `0x00 .. 0x54`) holds ids, info bytes and **sector counts**. The
  native walker starts its cursor at `0x800` and never sums sector 0 at all — the header sector is
  implicit. Editing bytes inside it cannot perturb any resource offset.
* **No checksum.** The famous "cursor lands exactly on the file length" property is an *empirical corpus
  invariant*, not a native check (`V-C2-container-table-walk.md` §6.1 corrected this explicitly: neither
  build ever compares the cursor to a length). A same-length edit preserves it trivially; even an
  *insertion inside sector 0* preserves it, because sector 0 is never in the sum.
* **The id-2 sub-file directory** is byte offsets into the id-2 region — untouched by any of this.
* **Camera blocks carry LOCAL frames**, rebased at their install op, so only the straddling shot needs
  in-block edits (§5.4).
* **The id-3 effect programs' clocks are program-local** — `*(arg3)`, read at the top of each tick and
  reset to −1 at each transition (R3 §6's evidence block). Their thresholds count *program* ticks, not
  sequence ticks, which is exactly why the `69` immediate is a required co-edit and not an automatic one.
* **The akao sound sub-files** have internal timing that no retime can stretch; but see 7.2 — in the
  live mode they are not played from here anyway.

### 7.2 ⚠ OUTSIDE the container: **THE THIRD CLOCK — the single biggest finding of this recon**

**MEASURED, from the Memoria source the user's engine is built from, plus the user's own `Memoria.ini`.**

`StreamingAssets/Data/SpecialEffects/ef227/Sequence.seq` is a **plain-text managed sequence that carries a
frame-accurate transcription of ef227's own host-facing sequence ops** — the same sounds, the same
background intensities, the same show/hide, plus the damage `EffectPoint`. The correspondence is not
loose:

* four `PlaySound` quadruples at managed t = 60 / 116 / 222 / 324 against the binary's `0x2D` quadruples at
  seq ticks 26 / 82 / 188 / 290 → a **constant offset of exactly 34, four times over**;
* two `PlaySound … SoundType=Song` at t = 140 / 250 against the binary's two `0x09(127,1)` at ticks
  106 / 216 → the same 34;
* nine `SetBackgroundIntensity` entries, eight of which pair with the binary's eight `0x2A` ops with
  `Intensity == arg1 / 128` **exactly, 8/8** (255 clamping to 1.0) and `Time == arg2` on 6/8, off by one
  on the other two; the ninth is the pre-cast fade `PlayerSequence.seq` also issues;
* the managed file even reproduces the engine's own `AdjustSoundIndex` side effect — the first quadruple
  plays at default pitch and every later one at `Pitch=0.85`, which is precisely what
  `SFX.AdjustSoundIndex`'s `Bahamut__Full: if (soundCallCount == 4) soundFPS = -2` produces on the native
  path. It is a transcription, authored from the binary's behaviour.

**And in the mode that actually runs, the binary's copies are dead.** `SFXData.LoadSFX` loads that file for
every SFX; `SFXDataMesh.Runtime.Begin()` installs `SFX.hijackedCallback = SFXData.BattleCallbackDummy` for
the **whole playback** of a `UseCamera` effect (ef227 is one — `PlayerSequence.seq` says
`LoadSFX: … UseCamera=True`), and that dummy **returns 0 and does nothing** for callback codes
**32 (play sound)**, **118 (set background intensity)**, **125 (sound pitch)**, **23 (effect point)**,
**24 (figure point)**, **25 (show/hide mesh)**, **18 (set hidden)**, **113/114/116** (casting name, cursor),
**110/112**, and the actor-manipulation codes 2/4/6/11/12/16/19/… It passes through only the VRAM ops
(100/101/102), the query ops (111/115/117/121–124) and the geometry reads.

The gate is `Configuration.Battle.SFXRework`, which **defaults to `true`** and is additionally forced when
`Speed >= 3`. The user's install: **`SFXRework = 1`** *and* **`Speed = 5`**. So this is not a hypothetical
branch — it is the branch the W2 cast ran on.

**What that means for W3, stated plainly:**

1. **The retime budget of ef227.bytes is exactly the plugin-internal layer: the CAMERA and the effect
   PROGRAM.** Which is precisely the pair the two-clocks law is about — so the W3 gate is intact, and the
   in-game read is *cleaner* than feared (no sound/fade confound in the artifact).
2. **The sounds, the background fades, the mesh show/hide and the damage point will NOT move.** They will
   stay on the managed clock while the camera and the creature move by N. On a large N that is itself
   visible — and it would be very easy to misread as "the retime failed".
3. **So `Sequence.seq` is part of the edit set.** It is a text file, it lives in the same mod-folder
   override lane (`FF9_Data/…` / `StreamingAssets/Data/…`), and its `Wait: Time=` numbers map onto the
   binary's WAIT `arg2` values one for one. Retiming it in lockstep is cheap — far cheaper than any byte
   edit in this rung.
4. **Pick N small for the first cast.** With N ≈ 8–16 the third clock's drift is subtle and the phase↔cut
   evidence is still unambiguous; with N ≈ 60 the cast becomes hard to read.

**Cross-checked and clean:** there is **no** hard-coded `SFX.frameIndex` literal for `Bahamut__Full`
anywhere in the engine (the only frame-keyed specials are Ark 1004/1193, Boomerang 34, Necron 26,
Atomos 350/150), and the s58 `SfxHybridDrive` keys on nothing but its own log line. `PlayerSequence.seq`
ends the cast with `WaitSFXDone`, which adapts to a longer effect on its own. So the third clock is the
*only* external co-edit.

---

## 8. (e) WHERE THE SEQUENCE ENDS THE CAST

**MEASURED.** The terminator is op #92: **code `0x00` at file `0x514`, at seq tick 511**, reached by the
last `WAIT(0, 19)` at `0x511`. The op before it is `0x28(16, 0)` at tick 492.

**INHERITED** (M2 §7.4 / FORMAT §3.2): the native handler `0x31aad` rewinds the interpreter pointer by 3
so the op re-executes every tick, and notifies the host with `0x73000000` — i.e. callback code **115**,
which Memoria implements (in *both* the real and the dummy callback) as "is the command cursor shown".
So the terminator is a per-tick host poll, not a fire-and-forget stop. This is consistent with W1's
"the sequence ends the cast, the programs never stop themselves": R3 shows `c0` s5 and `c1` s5 have **no**
exit guard, so nothing but the sequence can end it.

**Does a +N stretch have to move it? Its tick, yes; its bytes, no.**
Tick 511 is ≥ 82, so it shifts to **511 + N automatically** — the WAIT edit upstream is the whole
mechanism. **Zero bytes of the END op change, and its file offset does not move.** It shifts cleanly, and
it is the cheapest part of the whole edit.

Second-order consequence: the cast is N ticks longer. `WaitSFXDone` in `PlayerSequence.seq` discovers that
(it waits on the effect, it does not count frames), so the surrounding battle action self-adjusts.

---

## 9. THE BONUS — the same-length constraint does not apply here

**MEASURED.** The sequence sits inside the **header sector**, which the native loader copies wholesale
(`0x490d0` copies file `[0x000 .. 0x800)` to `0x3208d0`; the interpreter's pointer is that buffer + `0x400`
— INHERITED). Bytes `0x54 .. 0x400` and `0x517 .. 0x800` are both a single repeated filler value.

| | |
|---|---|
| ef227's stream extent | `0x400 .. 0x517` |
| free bytes after the terminator | **745** |
| spare 3-byte op slots | **248** |
| hard cap | file `0x800` — past that the interpreter reads off the end of the copied sector |
| max stream end anywhere in the corpus | `0x688` (`ef381`, 216 ops) — **no stock file comes near `0x800`** |

**So W3 may insert new ops, not just retune existing ones**, with no directory rewrite, no sub-file shift
and no container resize — the exact thing W1 §6 and W2 §7 warned would be the expensive prerequisite for a
camera-block change. That warning is real *for camera blocks* and simply does not transfer to the sequence
stream. (Two rules if inserting: the `END` must stay last — the filler byte is **not** a safe terminator,
it would decode as `run program 127`, indexing past the 16-entry program table — and the stream must not
cross `0x800`.)

This also gives a second way to spend a shift that a byte would not hold, and a way to add a beat rather
than move one. Not needed for W3's gate; worth knowing before someone re-plans the rung around a ceiling
that isn't there.

---

## 10. THE LEDGER — measured vs inferred

**MEASURED this session** (tooling named in §1; reproduce with the scripts recorded in the SCRATCH dump):
one stream at `0x400`, 93 ops / 279 B / all VALID; the opcode histogram; 33 non-blocking WAITs summing 511
and 1 blocking wait at tick 0; the complete op→tick map; two RUN_PROGRAMs at 12/255 on chunk slots 0/1;
three PLAY_CAMERAs at 11/255/480, all three blocks byte-exact round-trip; shot A's 11 frame words and all
three block extents; the corpus WAIT envelope [1, 240] with **zero** zeros over 1,931 ops; 1,103 blocking
waits across 372/372 files; corpus max stream end `0x688`; ef227's 745 filler bytes; the `0x2A` ↔
`SetBackgroundIntensity` correspondence (8/8 intensities, `arg1/128` exact); the four sound quadruples at
a constant offset of 34 (8/8 intensities exact, 6/8 fade Times exact); `SFXRework` default `true`, the
user's `Memoria.ini` `SFXRework = 1` / `Speed = 5`;
`BattleCallbackDummy`'s swallowed-code set; `Runtime.Begin` installing it for the whole playback.

**INHERITED** (prior rounds, cited, not re-derived): the native interpreter's fetch/dispatch and the
opcode validity map; the WAIT / LOAD_CHUNK / END handlers; `0x80+N` = run program N of the table-ordinal
chunk (0 failures / 372 files); the header-sector copy and the `+0x400` sequence pointer; W1's two-clock
origins 47 / 45 and the authored lead 1/1/0; R3's thresholds 69 / 24 / 24 / 26 / 30 and the `slti` at
`0x1278`; the absence of a native length check.

**INFERRED** (mine, falsifiable): anchor B is the right anchor; the −45 shrink floor from `c0` s0's own
`clock >= 24` guard; `WAIT arg2 = 0` is unsafe because unattested; `0x09` is a music/stream trigger.

**Refuted en route:** `0x2E` is *not* a duration op (§3). And a same-length constraint on the sequence
stream does not exist (§9) — the assumption carried over from W2's camera-block ceiling.

---

## 11. WHAT A1 DOES NOT SETTLE

* **Which callback code each unnamed op reaches.** `0x03 0x04 0x06 0x09 0x0A 0x0B 0x0F 0x2C 0x2E` have
  native handlers but no read semantics, so I cannot say which of them are swallowed by the SFXRework
  dummy and which still act. **Cheap named probe:** one cast with `SFX.isDebugPrintCode` on — the dummy
  logs `[SFXData] Callback <COMMAND> …` for every call, which yields the full op→code→frame trace in a
  single run, and simultaneously confirms §7.2 empirically instead of by source reading.
* **The native WAIT countdown's width**, hence whether `arg2 = 0` means "no wait" or "256". Unread; do not
  rely on it (§5.3).
* **Whether the managed `Sequence.seq` needs to move by N or by something else.** Its offset from the
  binary clock drifts from 34 to ~37 across the cast, so it is not a rigid rebase; the retime should move
  its `Wait` values at the corresponding beat, not add N to the whole file.
* **Nothing here validates the phase-threshold edit itself** — that is a program-image edit and belongs to
  the sibling recon; A1 only establishes that the sequence side of the co-edit is one byte.

---

## 12. Files

| path | what |
|---|---|
| `C:\gd\SCRATCH\summon-format\retime-w3-recon\A1-ef227-seq-ops.txt` | **the complete 93-op table** (index, file offset, length, derived tick, opcode, args, status, note) + the corpus probes + the camera-block keyframe listing — **stock-derived, SCRATCH only** |
| `C:\gd\SCRATCH\summon-format\retime-w3-recon\A1-probe.txt` | the adversarial checks (sector-0 layout, corpus WAIT envelope, `0x2A`/`0x2E` histograms, handler map, edit bounds) |
| `C:\gd\SCRATCH\summon-format\retime-w3-recon\A1-shotA-keyframes.txt` | the three camera blocks' extents, spans and frame lists |
