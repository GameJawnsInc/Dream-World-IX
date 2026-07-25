# W1 — THE READ-OUT, and the camera recon it was built to perform

**TIER W rung 1.** Deliverables: `summon_camera.py` (the extractor + the decoder adapter + the
read-out + the merged timeline), `test_summon_camera.py`, `w1_gates.py`, this report.
**Read-only rung**: nothing deployed, nothing written to the game install, no stock data modified.

---

## 0. HEADLINE — the round-trip verdict

**Outcome 1 of the three: it parses and re-serialises BYTE-IDENTICAL.**

> **798 / 798 stock summon camera blocks, across 372 / 372 effects, decode and re-encode to the
> exact original bytes — 129,884 bytes of camera data in total — through
> `ff9mapkit/ff9mapkit/battle/camera_codec.py` with not one line of that module changed.**

So FORMAT/D4's never-executed claim — *"the same format `battle/camera_codec.py` already
round-trips"* — is now **proven with an artifact**, and proven at 282× the scope it was made at
(D4 measured Bahamut's 3 blocks; this is every statically-resolvable camera in the corpus).
The battle codec's own tests are untouched and green (W1a), because the summon side is an adapter,
not a fork: an SFX camera sub-file **is** one raw17 camera without raw17's set-offset-table wrapper,
so `parse_camera_block` / `serialize_camera_block` are two calls into `camera_codec`'s existing
per-camera functions.

**Why byte-exact and not merely structure-preserving.** Four invariants the corpus satisfies
798/798, each one a test:

1. the outer offset table's first entry equals the table's own end — no gap, no header padding;
2. the group offsets are **strictly** increasing, so the codec's canonical emit order (sequences,
   then selector, then anchors) **is** the physical order;
3. the **last** group is never a sequence — it is always the bit-3 selector or the bits-4–7 anchor
   records, both of which the codec carries verbatim. That matters: a sequence group stops at its
   frame-0 terminator and would *drop* the 0–2 byte alignment pad at a block's end. Because a
   verbatim group is always last, the pad survives;
4. no camera block is ever the **last** sub-file in its chunk, so a block's end is always a real
   directory delta and never the id-2 region's sector padding.

Those four are the load-bearing facts. Break any of them when authoring at W2 and byte-exactness
stops being free.

---

## 1. Gate table

| gate | result | numbers |
|---|---|---|
| **W1a** no regression | **PASS** | tier-r `r1_gates` 8/8 · `r2_gates` 6/6 · `r3_gates` 5/5 · tier-r tests 41+70+31 = **142 pass, unchanged** · new `test_summon_camera.py` **34 pass** (**176 total**) · kit `tests/test_battle.py -k camera` 12 pass · `tests/test_battle_scene_codec.py -k camera` 1 pass · `camera_codec.py` working tree **UNMODIFIED** |
| **W1b** the round-trip | **PASS** | **798 / 798** blocks byte-identical over **372 / 372** effects, **129,884 B**. Failures: **none**. Refused to read: **2** (both external, §4) |
| **W1c** ef227 two clocks | **PASS** | derived pairs `(11,12,−1) (106,107,−1) (255,255,0)`; capture confirms with **one constant origin per clock**, 47 and 45 |
| **W1d** census | **PASS** | §4 |
| **W1e** provenance | **PASS** | 4 byte literals in the committable sources, **0** of them found anywhere in the corpus; dumps under `C:\gd\SCRATCH\summon-format\camera-w1\`; 0 hex byte runs and 0 decoded-keyframe rows in this report |

Reproduce: `py studies/custom-summons/tier-w/w1_gates.py` (needs the extracted corpus).
Tests run **without** it — `py -m pytest studies/custom-summons/tier-w/test_summon_camera.py -q`
gives 29 passed / 5 skipped on a machine with no extraction.

---

## 2. THE EXTRACTOR — and three corrections it had to make

The chain R2 established is: sequence stream → a camera-naming op → the chunk's id-2 sub-file
archive → a camera block. Walking it end to end turned up three things the existing record gets
wrong or leaves unstated. Each is a test and each is falsifiable.

### 2.1 `0x23 SETUP_CAMERA` is a camera-block op too — and it is the MAJORITY

A tool that walks only `0x29 PLAY_CAMERA` sees **85** of the corpus's **798** camera blocks. The
other **713** are named by `0x23`, which resolves through the same directory (its `arg1 = 0xFF`
sentinel, appearing 324 times, means "no camera"). Every one of the 713 blocks it names parses and
round-trips, which is the evidence that `0x23` is a camera op and not something else that happens to
carry an index. `ef_camera_decode.py` already treated `0x23` this way; the R-tier prose does not,
and R2 §5's "ef227 plays shots 6/16/47" reads as though `0x29` were the whole story. On ef227 it
happens to be — ef227 uses no `0x23` at all — which is exactly how a 3-shot sample can hide 89 % of
a corpus behaviour.

### 2.2 THE ID-2 EXTRA-SECTOR CORRECTION — a silent wrong answer on one file

`ef_container.parse_header` reads the `id == 2 && info != 0` conditional field into `extra_sectors`
and advances the cursor by it **after** the payload; `describe()` then parses the sub-file directory
at `res.offset`. For the one corpus file where `extra_sectors != 0` — `ef251` chunk 0, which D3's own
census already flagged as the single exception — that base is wrong. It yields a **2-entry**
directory that is monotone, in-bounds and entirely plausible (which is why D3's "381/385 clean" check
passed it), and the effect's own camera index then reads out of range.

The correct base is **after** the extra region — `res.offset + extra_sectors * 0x800`, the ordering
`SFXBinaryFile.cs` uses — which yields a 33-entry directory whose region ends exactly on the next
resource's offset, and whose entry the effect asks for is a camera block that round-trips. Both
readings consume identical total bytes, so the container walk is unaffected: **only the directory
base moves.** `id2_directory` applies it; `test_corpus_ef251_needs_the_extra_sector_correction`
pins it; a synthetic test pins it without the corpus.

This is the only file it changes today. It will matter more the moment anything writes an id-2
archive.

### 2.3 The Code `frame` word carries flags in its top 3 bits

97 keyframes across 36 effects set bits in `0xE000` of a Code's `frame` u16 (values `0x4000`,
`0x2000`, `0x6000`), and they sit on the **first** keyframe of a sequence in 86 of 97 cases. Read as
a bare frame number — which every prior reader does — such a shot appears to start at frame 16385
and then run backwards; that is what a naïve monotonicity check flags on 47 of 798 blocks, all of
them false alarms. `frame_number()` / `frame_marks()` split the word. The codec stores it verbatim
so the round-trip never noticed, but **anything that writes a frame must preserve the high bits**,
and what they mean is still open.

---

## 3. THE READ-OUT and the ef227 MERGED TIMELINE (W1c)

`py summon_camera.py read 227` prints, per shot: the naming op and its file offset, the chunk and
sub-file index, the block size, the outer flags decoded into named groups, the block's internal
layout, the round-trip verdict, the shot's span in local frames, and then every keyframe — camera
pose, camera movement (duration + easing), target pose, target movement, the **focal / projection
distance** (the independent zoom lever R2 §3 identified: ops 121/122/148 write `gteH` and touch
neither `gteOFX` nor `gteOFY`), plus every remaining field verbatim. Then the merged timeline.

### The merged timeline puts both clocks on the SEQUENCE clock

Both columns are derived; neither is fitted:

* a camera event sits at `op.seq_tick + local_frame − 1` — `ef_camera_decode.py`'s three-way
  validated rule, mechanically explained by D4 §2.1 (the stepper advances once per
  `SFX_UpdateCamera`, i.e. once per host frame, from the moment `0x12df0` installs the block);
* a phase boundary sits at **the `0x80+N` RUN_PROGRAM op's own tick** + R3's phase `start_tick`.
  ef227's two programs start at sequence ticks 12 and 255, read straight out of the same walk.

So the offset between a cut and a beat is a pure data+code quantity, tuned to nothing.

| camera writes | at seq tick | nearest phase boundary | at seq tick | offset |
|---|---:|---|---:|---:|
| H → 256 (shot A installs) | 11 | `ef227:c0` enters s0 | 12 | **−1** |
| H → 415 | 106 | `ef227:c0` enters s1 | 107 | **−1** |
| H → 512 (shot B installs) | 255 | `ef227:c1` enters s0 | 255 | **0** |

### The capture, consulted only afterwards, confirms it and sharpens the law

TIER R's capture recorded those three H changes at frames 58 / 153 / 302 and the matching phase
boundaries at 57 / 152 / 300. Against the derived ticks that is:

* camera: 58−11 = 153−106 = 302−255 = **47**, one constant;
* program: 57−12 = 152−107 = 300−255 = **45**, one constant;
* the H values match, and the **intervals** between the three events match exactly on both columns
  (95 and 149 ticks for the camera, 95 and 148 for the phases).

Three observations, one free parameter per clock, zero residual. **And the two origins differ by a
constant 2.** That reframes the two-clocks law usefully:

> In the AUTHORED data the camera **leads** the beat by 1, 1 and 0 ticks. At runtime the camera
> install lags the program by a constant 2 frames. What the capture reads as "the cut lands 1–2
> frames *after* the phase boundary" is that constant minus the authored lead — not a sloppy
> alignment, and not something an author can dial.

The consequence for W2/W3 is sharp: **a retime must preserve the authored lead (1, 1, 0), and cannot
touch the 2.** Anyone who "fixes" the alignment by shifting a keyframe forward 1–2 frames to make the
capture read 0 will have moved the cut *off* the beat.

One more thing the merged timeline shows that the capture-side note did not: this is not a
three-event phenomenon. **19 of ef227's 31 camera events land within 4 ticks of a phase boundary**,
at offsets −1 (×8), 0 (×8), +1 (×2) and −4 (×1). The two clocks are locked for the whole cinematic,
not just at the cuts.

It also corrects one row of `EF227-CHOREOGRAPHY.md` §4a: that table lists the H change at frame 529
under "the camera returning to its battle default". It is not — it is **shot C's own first
keyframe**, an authored focal on the outro block, landing exactly where origin 47 predicts. Only the
last row (frame 553) is still unexplained by camera data.

---

## 4. THE CORPUS CENSUS (W1d)

| question | answer |
|---|---|
| effects in the corpus | 372 |
| effects carrying camera-naming ops | **372 — every single one** |
| effects resolving at least one shot | **372** |
| camera-naming ops | 1,448 |
| statically-resolved camera blocks | **798** |
| ops whose shot is chosen at RUNTIME | **324** (`0x29` with `arg2 = 3`) |
| ops meaning "no camera" | **324** (`0x23` with `arg1 = 0xFF`) |
| shots per effect | 1 → 42 · 2 → 240 · 3 → 88 · 4 → 1 · 8 → 1 |
| block size | min 20 · p25 64 · median 132 · p75 244 · max 704 B (mean 163; 129,884 B total) |
| keyframes per shot | min 1 · p25 3 · median 8 · p75 15 · max 36 (7,307 total) |
| shot length | min 1 · p25 41 · median 56 · p75 73 · max 704 local frames |
| sequences per block | 1 → 418 · 2 → 6 · **3 → 374** |
| byte-identical blocks | 118 groups covering 345 references; 32 groups span more than one effect |

### Five things in there that would surprise a rescore author

1. **Half the corpus's camera blocks carry three alternate takes, and they are usually different
   takes.** 380 blocks declare more than one sequence, and in **332** of them the alternates are not
   byte-identical — they are genuinely different camera moves. Which one plays is decided at runtime
   by the bit-3 selector block (D4 §2.2 correction 2). Edit "the" camera of such an effect and you
   have edited one of three; the cast may show you the other two.
2. **A third of all `PLAY_CAMERA` ops choose their shot at runtime.** 324 of 411 use `arg2 = 3`
   (the table lookup keyed on a battle field). Offline decoding cannot name their shot, and this
   module marks them `dynamic` rather than guessing. Notably the pairing is exact: each of the 324
   files with a `0x29 arg2=3` has exactly one `0x23 arg1=0xFF`, so the idiom is "clear the setup
   slot, then pick from the table."
3. **`SETUP_CAMERA` carries 89 % of the camera data** (§2.1).
4. **Two shots point *outside* their own archive.** `ef381` chunks 2 and 4 name sub-files whose
   directory entries are **negative** — signed s32 offsets pointing backwards into earlier-loaded
   data (M2 §5's "external file"). The extractor refuses them by name rather than reading whatever
   is at a negative offset. `ef381` is also the corpus's shot-count outlier at 8, and `ef447` at 4;
   both are the multi-chunk Ark effects that break every other id-2 census too.
5. **The selector block is not a fixed 4 bytes.** 628 blocks carry a 4-byte selector, **170** carry
   6. `SFXDataCamera.cs` reads a fixed 4; `camera_codec` carries the region verbatim to the group
   boundary, which is why it survives. An authored selector must be copied at its real length.

Also worth noting for W2: **58 blocks use the anchor group** (bits 4–7) — 38 with one 6-byte record,
13 with two, 2 with three, 5 with all four. D4 §2.2 correction 1 typed this group; the codec still
carries it verbatim, which is lossless but not yet authorable.

---

## 5. What W1 does NOT settle

* **No offline geometric predictor.** Nothing here turns a (pitch, orientation, roll, distance)
  pose into a world-space eye/look-at. D4 §2.6 located that math in the DLL (`0x13d40` evaluator,
  `resolve_position@0x145a0`, `0x14c30` look-at builder, 4096 units per revolution) but it has not
  been decoded. The read-out prints raw pose bytes for that reason; the degree conventions
  `camera_codec._pose_bytes` uses are a **battle-side** heuristic and are **not** confirmed for SFX.
  Do not treat them as calibrated.
* **Movement `type` beyond 0/1/2.** The corpus uses nine distinct values (0, 1, 2, 4, 5, 6, 8, 9,
  10); only 0/1/2 have a name, from the battle side. The read-out prints `type-N` for the rest
  rather than inventing an easing curve. ef227's shot A uses `type 10` on one of its moves.
* **The frame word's high bits** (§2.3) — live, undecoded, preserve verbatim.
* **The bit-3 selector's input grammar** and **outer flags bit 9** — both still D4 §4's open items.
  Copy stock verbatim until they are read.
* **`op 146` read-vs-write** — the PLAN's named W2 gate. Untouched here, correctly: W1 only reads.

---

## 6. THE ONE THING MOST LIKELY TO BITE AT W2

**The block-size ceiling is the directory delta, not the block.** A camera sub-file's length is
defined by the *next* directory entry, and 187 of 798 blocks already end in 2 bytes of alignment pad
— so the free space inside a block is 0 or 2 bytes, essentially never more. D4 §2.5.2 is right that
a same-size-or-smaller rewrite is a pure in-place splice; what it does not say is how *tight*
same-size is. A rescore that adds a single keyframe adds 4–20 bytes and **will not fit**, which
means re-emitting the id-2 directory and shifting every later sub-file in the archive — a container
writer, i.e. the M2 R2 work D4 hoped to avoid.

The way through, and it is cheap: **a same-size rescore has plenty of room to work in.** Changing a
pose is 6 bytes in place; changing a movement duration is 2; changing the projection distance is 2.
All of W2's stated scope (pose / aim / projection distance, durations unchanged) fits inside an
unchanged block length. The moment W3 wants to *add* or *remove* a keyframe, the directory rewrite
becomes a prerequisite — plan it as W3 work, not as a surprise.

Second-most-likely, and worth a lint rule before the first write: on an effect whose block declares
three sequences, **edit all three or know which one the selector picks**. 332 blocks have genuinely
different alternates; a one-track edit there produces a cast that looks unchanged and a very
confusing afternoon.

---

## 7. Files

| file | what |
|---|---|
| `studies/custom-summons/tier-w/summon_camera.py` | extractor + codec adapter + read-out + merged timeline + census; verbs `read` / `roundtrip` / `census` / `timeline` / `dump` |
| `studies/custom-summons/tier-w/test_summon_camera.py` | 34 tests; 29 run with no corpus and no install |
| `studies/custom-summons/tier-w/w1_gates.py` | W1a–W1e |
| `C:\gd\SCRATCH\summon-format\camera-w1\` | `ef227_camera.csv` (decoded keyframes), `ef227_readout.txt`, `w1_gates.txt` — **stock-derived, SCRATCH only** |
