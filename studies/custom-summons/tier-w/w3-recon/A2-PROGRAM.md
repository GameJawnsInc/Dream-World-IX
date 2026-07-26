# A2 — THE PROGRAM THRESHOLD SITES (the id-3 MIPS edit)

**W3 recon, task A2.** Read-only: nothing was written to the game install, no stock file was modified,
no existing repo code was touched. Decoded stock listings, dumps and probe scripts live **only** under
`C:\gd\SCRATCH\summon-format\retime-w3-recon\` (§10). This report carries offsets, immediates,
mnemonics, counts and derived constants — **no run of ≥ 6 consecutive stock bytes**, and the single
4-byte instruction word it quotes is the one `tier-r/EF227-CHOREOGRAPHY.md` §6 already publishes.

---

## 0. HEADLINE — the three answers

**Q: which container-file bytes hold `ef227:c0` state 0's clock threshold?**
> **File offsets `0x2E278` (low) and `0x2E279` (high)** — the imm16 of the `slti $v0, $s5, 69` at image
> offset `0x1278` in chunk 0's id-3 image, whose payload base is file `0x2D000`. The whole instruction
> is file `0x2E278..0x2E27B`, word `2aa20045`; because MIPS is little-endian and the imm16 is the low
> halfword, **the two bytes to edit are the FIRST two bytes of the instruction**, and the two bytes
> after them (`a2 2a`) must not move. Verified by direct `struct.unpack_from` on the corpus container,
> decoding to `op=10 (SLTI) rs=21 ($s5) rt=2 ($v0) imm=69`.

**Q: is that the ONLY site that encodes the s0 phase length?**
> **For the phase BOUNDARY — yes: exactly one `slti`, exactly one state store, and the value 69 appears
> as an immediate exactly once in the whole chunk-0 image.**
> **For the phase's internal MOTION — no, and this is the finding of this recon.** s0's case body opens
> by computing `(clock << 12) / 69` through a **magic reciprocal** `0x76b981db` (shift 5), a 0…4096
> normalised progress that hits exactly 4096 on the phase's last tick and is then consumed as a
> fixed-point lerp parameter six times inside the phase. A second reciprocal, `0xb60b60b7` (÷45,
> shift 5, add-back) applied to `(clock − 24)`, normalises ticks 24…69 — and **45 = 69 − 24**.
> Neither reciprocal contains the literal 69, so **any grep-for-69 uniqueness check passes while the
> phase length is in fact encoded three times in this one case body**. §3.

**Q: safe bounds for an in-place edit?**
> **Shrink floor 46** (structure-preserving; **absolute** floor 24, below which the creature is never
> drawn in s0 at all). **Stretch: effectively unbounded by the program** — imm16 signed max 32767, the
> clock cell is a 32-bit signed word by the program's own `lw`/`sw`/`slti` contract. The real stretch
> ceilings are *elsewhere*: the sequence's `WAIT` operand is one byte (255), and the unretuned
> reciprocals overshoot linearly past clock 69. §5.

**No integrity mechanism stands in the way.** The container has no magic number, no version field and no
checksum; its only structural self-check is "the resource walker's cursor lands exactly on the file
length", and an imm16 edit changes no length, no sector count and no directory entry. §6.

**Secondary (motion clip): SETTLED, and it is LOOP, not HOLD** — proven twice, statically and from the
archived capture. A stretch of s0 simply plays more of a 24-frame looping clip. §7.

---

## 1. The image base, derived from the resource walk

`ef_container.parse_header` (the port of the native walker `fn 0xd390`) on `ef227.bytes`:

| chunk | id-3 payload @file | size | psxBase | headerRel | live program |
|---|---:|---:|---:|---:|---:|
| 0 | **`0x2D000`** | `0x5000` | `0x801E7700` | `0x3120` | `0x9D4` |
| 1 | `0xC4000` | `0x5000` | `0x801EC700` | `0x42BC` | `0x108C` |

Container size `0xC9000`; the walker's cursor lands on `0xC9000` exactly (strict parse passes).
**So `container_offset = 0x2D000 + image_offset` for every chunk-0 program address in this report**, and
`0x2D000 + 0x1278 = 0x2E278`.

The edit sits at image `0x1278`, well inside the code region `[0, headerRel) = [0, 0x3120)`. It is not in
the header, not in the 16-slot program table at `headerRel + 8`, and not in the BSS.

**Drift guard:** the corpus file's sha256 is
`fe590d00a01d95c6dc473cee9fea9096b9ded63c3daae3aab693099c6d0ed167`, **identical** to
`rescore.py`'s registered `EXPECTED_STOCK_SHA[227]` — so every offset here applies verbatim to the
bytes W2's build path reads out of the user's own `resources.assets`.

---

## 2. The site itself

```
  1278  2aa20045  slti    $v0, $s5, 69     ; stay while clock < 69
```

| what | value | how verified |
|---|---|---|
| image offset | `0x1278` | `summon_inspect.recover()` names it as case-0's transition guard; `tier_r_disasm`'s reachability walk decodes it |
| **container file offset** | **`0x2E278`** | `0x2D000` (walk) + `0x1278`; re-read from the file and re-decoded |
| instruction word | `2aa20045` | direct `<I` read at `0x2E278` |
| decode | `op=10 SLTI`, `rs=21 ($s5)`, `rt=2 ($v0)`, `imm16=69` | field extraction; matches EF227-CHOREOGRAPHY §6 |
| **imm16 bytes** | **`0x2E278` = low byte (69), `0x2E279` = high byte (0)** | little-endian; imm16 is word bits [15:0] |
| bytes that must NOT move | `0x2E27A`, `0x2E27B` (the opcode/rs/rt half) | same decode |

`$s5` **is** the clock, and it is not aliased anywhere in the phase: the recovery names the clock
`*(arg3)`, `$s5` is loaded from it at image `0x0b44` (`lw $s5, 0($t1)`) immediately before the dispatch
at `0x0b64`, and a sweep of every reachable instruction in chunk 0 finds **zero writes to `$s5` between
`0x0b6c` and `0x1384`** — the whole of s0's body. (The 16 `$s5` writes in the image are all in other
functions or in the shared tail at `0x2b38+`, which runs after the case.)

The transition's shape, unchanged from EF227-CHOREOGRAPHY §6: the `bne` at `0x127c` sends the
"not yet" arm to the shared tail `0x2b38`; the fall-through stores state 10 at `0x1284` and resets the
clock to −1 at `0x1290`. **There is exactly one store to the state variable inside s0's body** (`sw $v0,
0($s3)` at `0x1284`) — checked by sweeping every `sw/sh/sb` to `0($s3)` in reachable chunk-0 code, which
returns exactly six: the init arm's zero-seed plus one per case. So s0 has one exit and one guard.

**s0's body is contiguous**: image `0x0b6c … 0x1384`, 519 instructions, `(last−first)/4+1 == count`,
terminating in `j 0x2b38`. That matters for a shrink/stretch: nothing in the phase is spliced across
another case.

---

## 3. UNIQUENESS — the honest answer is "one boundary site, three length encodings"

### 3.1 The literal 69 is unique (MEASURED)

Three independent sweeps of chunk 0:

| sweep | result |
|---|---|
| every **reachable instruction** whose SIMM/UIMM operand equals 69 | **1** — the `slti` at `0x1278` |
| every 4-aligned **32-bit word** equal to 69 in the whole `0x5000`-byte image | **0** |
| every 2-aligned **16-bit halfword** equal to 69 in the image | 5, of which **only `0x1278`** is the imm16 of a reachable instruction (the other four are `0x2652`, `0x26ae`, `0x2fd6`, `0x3032` — halfwords straddling unrelated instruction fields) |

Whole-container 4-aligned words equal to 69: **1**. So no table entry, no camera field and no sequence
byte carries a bare 69.

Also swept: the value **70** (s0's tick *count*) appears as an immediate exactly once in chunk 0, at
image `0x1a14` — inside **state 10's** body, where it is unrelated to s0. No computed offset, no jump
table entry and no `addiu` anywhere derives from 69 or 70.

### 3.2 …but the phase length is ALSO in two magic reciprocals (MEASURED, and this is the trap)

Every one of ef227's phase bodies opens with a `lui`/`ori` pair building a **reciprocal magic constant**
and multiplying it by `clock << 12`. Decoding those (magic + shift + add-back, then verified by
emulating `floor(M·x / 2^(32+s))` against `x // d` over 25k inputs) gives:

| site (image) | magic | shift | add-back | numerator | **divides by** |
|---|---|---:|---|---|---:|
| `0x0b6c`/`0x0b70`, `mult` @`0x0b78`, `sra` @`0x0b84` | `0x76b981db` | 5 | no | `clock << 12` | **69** — s0's own threshold |
| `0x0c54`/`0x0c58`, `mult` @`0x0c64`, `sra` @`0x0c70` | `0xb60b60b7` | 5 | yes | `(clock − 24) << 12` | **45** = 69 − 24 |
| `0x1190`/`0x1194`, `mult` @`0x11ac`, `sra` @`0x11c8` | `0xb21642c9` | 5 | yes | `150 · clock` | 46 (self-contained, see §4) |

`0x76b981db` is uniquely ÷69: of all 20 (shift, add-back) combinations only `(5, no)` yields an exact
divisor, and it yields 69. Evaluated at the phase's own endpoint: `(69 << 12) / 69 == 4096` **exactly**;
at clock 68 it is 4036, at clock 70 it is 4155. The `(clock − 24)` ramp is the same story — it reaches
exactly 4096 at clock 69 and keeps climbing.

**What the ÷69 value is used for.** It is stored to `320($sp)` at `0x0b94` (unconditionally, in a delay
slot) and read back six times inside s0 — at `0x1030`, `0x1064`, `0x108c`, `0x10c0`, `0x1108`, `0x122c`.
At `0x1108`–`0x1124` it is used as a textbook 12-bit fixed-point lerp: `s0 = 4096 − t`, `mult`, `mflo`,
`sra 12`, `addu`. **There is no clamp.** Past clock 69 the term goes negative and the interpolation runs
backwards past its endpoint. At `0x122c`–`0x123c` the same value is fed to `rcos` as `t >> 2`, i.e. an
angle — that one wraps harmlessly.

`320($sp)` is a per-phase scratch slot: every case writes it at its own head (`0x0b94` s0, `0x13ac` s10,
`0x1bd4` s2, `0x1e2c` s4, `0x20b0` s5) and reads it only within that case. So the ÷69 constant is s0's
and s0's alone.

### 3.3 The pattern generalises — a corpus check

Over the whole 372-file corpus, the 16 images `summon_inspect` recovers cleanly carry **85** clock-guarded
transitions with a threshold:

| question | answer |
|---|---|
| the threshold value appears **exactly once** as an immediate in its own case body | **49 / 85** |
| it appears more than once (or zero times) | **36 / 85** |
| the case **head** computes a magic reciprocal of the threshold | **≥ 39 / 85** |

Two cautions on those numbers, both mine:

* The 39 is a **floor**, not a measurement: my head scanner only looks 16 instructions deep, and
  `ef227:c0` state 4's ÷30 (magic `0x88888889`, shift 4, add-back — threshold 30) sits with its `mult` at
  head+`0x18` and its shift at head+`0x50`, so the automated pass missed a case I then confirmed by hand.
  Hand-confirmed for ef227: c0 s0 ÷69, s10 ÷24, s2 ÷26, s4 ÷30; c1 s0 ÷35, s2 ÷28, s4 ÷14. c0 s1 and c1
  s1/s3 have no head reciprocal at all, so the idiom is strong but **not** universal.
* **"one threshold = one imm" is FALSE corpus-wide** (36/85 fail it) and false even elsewhere in ef227 —
  `c0` state 1's threshold 24 appears **3 times** in its own body, `c1` state 1's 48 appears **7 times**.
  It happens to be true for the one phase W3 wants to edit. Do not promote it to a law, and do not build
  a "find the threshold by searching for its value" tool on it.

### 3.4 The five-site transition map (c0) and its twin (c1)

Every one of these was re-read from the file and re-decoded, not taken from the recovery's word:

| program | phase | → | guard (image) | **file offset** | instruction | imm16 bytes @file |
|---|---|---|---:|---:|---|---|
| `c0` | **s0** | 10 | `0x1278` | **`0x2E278`** | `slti $v0, $s5, 69` | `0x2E278`, `0x2E279` |
| `c0` | s10 | 1 | `0x163C` | `0x2E63C` | `slti $v0, $s5, 24` | `0x2E63C`, `0x2E63D` |
| `c0` | s1 | 2 | `0x1ABC` | `0x2EABC` | `slti $v0, $s5, 24` | `0x2EABC`, `0x2EABD` |
| `c0` | s2 | 4 | `0x1D1C` | `0x2ED1C` | `slti $v0, $s5, 26` | `0x2ED1C`, `0x2ED1D` |
| `c0` | s4 | 5 | `0x2010` | `0x2F010` | `slti $v0, $s5, 30` | `0x2F010`, `0x2F011` |
| `c1` | s0 | 1 | `0x14E0` | `0xC54E0` | `slti $v0, $t1, 35` | `0xC54E0`, `0xC54E1` |
| `c1` | s1 | 2 | `0x1C18` | `0xC5C18` | `slti $v0, $t1, 48` | `0xC5C18`, `0xC5C19` |
| `c1` | s2 | 3 | `0x259C` | `0xC659C` | `slti $v0, $t1, 28` | `0xC659C`, `0xC659D` |
| `c1` | s3 | 4 | `0x27C0` | `0xC67C0` | `slti $v0, $t1, 2` | `0xC67C0`, `0xC67C1` |
| `c1` | s4 | 5 | `0xC6FC0`ᵃ | `0xC6FC0` | `slti $v0, $t1, 14` | `0xC6FC0`, `0xC6FC1` |

ᵃ image `0x2FC0`. Note the clock lives in a **different register per program** — `$s5` in c0 (loaded once
at the top of the tick), `$t1` in c1 (reloaded from `616($sp)` at each use). Any tool that keys on `$s5`
will silently find nothing in c1.

Both terminal states (c0 s5, c1 s5) have **no** guard and **no** state store — they end only when the
sequence stops the chunk. All ten thresholds match the recovery's values exactly.

### 3.5 The other two clocks that encode the same boundary (context, not program bytes)

For completeness, because "is this the only site" has an answer larger than the program:

* **The camera block.** Shot A (chunk 0, id-2 sub-file 6) has a keyframe at **local frame 71**, which the
  W1 rule `op.seq_tick + local_frame − 1` places at **seq tick 81** — s0's last tick, one tick before the
  s10 boundary at seq tick 82. That is the authored −1 lead W1 measured. Retiming s0 without moving that
  keyframe breaks the alignment W3 exists to hold.
* **The sequence.** `WAIT 0, 46` at file `0x0430` (arg2 byte at `0x0432`) carries the stream from tick 35
  to tick 81; `WAIT 0, 1` at file `0x0436` (arg2 at `0x0438`) carries it to 82, where six ops fire on the
  boundary. **`WAIT`'s arg2 is a single byte** — 255 max — so a stretch beyond +254 through that one op
  needs an extra 3-byte record. Measured headroom for that: the sequence stream is 93 ops = 279 B, ending
  at file `0x517`, and the rest of sector 0 to `0x800` is **745 bytes of `0xFF` filler** — so records can
  be inserted without changing any sector count.
* ⚠ **A plan-level inconsistency worth resolving before A1 writes anything.** The task brief says
  "every binary-sequence op at seq tick ≥ 82 shifts by N" and "shot A camera keyframes at local frame
  ≥ 71 shift by N". Those two rules sit on **opposite sides of the same boundary**: the camera keyframe at
  local 71 is at seq tick **81**, and there is also a sequence op at seq tick 81 (`0x2A`, arg1 = 77) that
  the ≥ 82 rule leaves in place. Either both tick-81 events ride the boundary or neither does. I cannot
  settle it — `0x2A`'s operand semantics are unread (FORMAT §3 lists the handler `0x3BD10`, not its
  meaning) — but it should be decided deliberately, not by the accident of a threshold.

---

## 4. Every intra-phase clock gate in s0 — and the shrink bound

### 4.1 The complete gate list (MEASURED)

Every compare against the clock inside `0x0b6c … 0x1384`, with what each arm does. Nothing here is
inherited from R3; each was read off the decoded body.

| image | file | compare | branch | what the gated block is |
|---:|---:|---|---|---|
| `0x0B8C` | `0x2DB8C` | `slti $s5, 12` | `beq` → `0x0BF0` | the **clock < 12** intro block `0x0B98…0x0BEC` (op 14, op 64). Falls through into `0x0BF0`, so nothing after it is gated by 12 |
| `0x0BF0` | `0x2DBF0` | `slti $s5, 24` | `bne` → `0x0E74` | **the phase's main split.** `clock ≥ 24` runs `0x0BFC…0x0E6C` — the creature half. Both arms merge at `0x0E74` |
| `0x0BFC`/`0x0C00` | `0x2DBFC` | `clock == 24` (`addiu $v0,$zero,24` + `bne $s5,$v0`) | fall = equal | a **one-shot at tick 24**: `Hi_SetSummonMotion` (`0x0C28`) + `Hi_SetSummonMotFrame(…, 0)` (`0x0C4C`). This is where the creature's clip is started |
| `0x0E48`/`0x0E4C` | `0x2DE48` | `clock == 44` | fall = equal | a **one-shot at tick 44** (`lw`/`sw` of a parameter) |
| `0x0E50` | `0x2DE50` | `slti $s5, 45` | `bne` @`0x0E60` → `0x0E74` | `clock ≥ 45` writes the **saturated** constant 4096 to `328($sp)`; below 45 the ramp keeps running |
| `0x0FA4` | `0x2DFA4` | `slti $s5, 35` | `bne` | the **odd-clock** arm (guarded by `andi $v0,$s5,1` at `0x0F9C`) |
| `0x0FB0` | `0x2DFB0` | `slti $s5, 35` | `bne` | the **even-clock** arm — together, a `clock ≥ 35` sub-block (ops 97, 50, 50) that alternates by parity |
| `0x1188` | `0x2E188` | `slti $s5, 46` | `beq` → **`0x1278`** | `clock ≥ 46` jumps **straight to the transition test**, skipping `0x1194…0x1274` entirely. So `0x1194…0x1274` is a strict **ticks 0…45** sub-phase (op 64, op 102, op 14, op 74) |
| `0x1278` | `0x2E278` | `slti $s5, 69` | `bne` → tail | **THE TRANSITION** |

The three magic reciprocals line up with those gates exactly: ÷46 spans the `clock < 46` sub-phase
(`150 → 0` countdown), ÷45 spans ticks 24…69, ÷69 spans the whole phase.

### 4.2 A correction to `EF227-CHOREOGRAPHY.md` §3's "earliest" column

`summon_inspect._gates_for` decides a gate with a reachability test that **avoids the other arm**. In a
diamond where one arm's only route to a site passes through the other arm's head — which is exactly the
shape at `0x0B8C`/`0x0B90` and `0x0BF0`/`0x0BF4` — that test reports a gate where both arms in fact
reach the site. I re-derived the gating by **plain** reachability from each arm over an
instruction-level CFG of the case body. Result for c0 s0:

* the reported `clock ≥ 12` on 20 call sites is an **artifact** — `0x0BF0` is reached unconditionally,
  so nothing downstream of it is gated by 12;
* `Hi_DrawEffModel` (`0x0F58`, `0x10B8`), `Hi_ModifyEffModelRGB` (`0x0F80`, `0x10E0`) and two op-50 sites
  have **no clock gate at all** — they run on **tick 0**, not tick 12 as §3 reports;
* `get_subfile_ptr` (`0x1220`) and `gte_transform_vertices` (`0x1264`) are gated `clock < 46`, i.e. they
  run ticks 0…45, not "from tick 12";
* `Hi_SetSummonMotion` / `Hi_SetSummonMotFrame` at `0x0C28`/`0x0C4C` are gated by the **equality** test —
  they fire **once**, at tick 24 — not every tick from 24 as a `≥`-only reading implies;
* the `clock ≥ 24` gates on ops 15/25/65 and the `clock ≥ 69` gates on the transition tail
  (`0x12B4`, `0x12D8`) are **confirmed** unchanged.

This does not move any phase boundary and does not affect the A2 answer. It does mean §3's *earliest*
column for this phase reads systematically **late**, and the "op 26 called every tick" reading of §4b is
wrong for s0 specifically. Recorded here rather than edited into the R-tier report, which is that rung's
to own.

### 4.3 THE SHRINK BOUND

A shrink must keep the threshold above every intra-phase gate that has to survive. From §4.1:

| new threshold N | what is lost |
|---|---|
| **N ≥ 47** | nothing — the `clock ≥ 46` hold gets ≥ 2 ticks. **The safe floor to recommend.** |
| N = 46 | structurally intact but degenerate: the `clock ≥ 46` segment runs for exactly one tick, which is also the transition tick |
| N < 46 | the `clock ≥ 46` hold **never happens**; the ticks-0…45 sub-phase (op 102 / op 74 / op 64) runs right up to the boundary and is cut mid-ramp instead of settling |
| N < 45 | the ramp never **saturates** — `328($sp)` never receives its terminal 4096 |
| N < 44 | the tick-44 **one-shot never fires** |
| N < 35 | the parity-alternating `clock ≥ 35` sub-block (ops 97/50/50) never runs |
| **N < 24** | **HARD STOP.** `Hi_SetSummonMotion` / `SetSummonMotFrame` / `DrawSummonModel` / `ModifySummonModelRGB` all live on the `clock ≥ 24` arm. Below 24 the creature is **never drawn in s0**, its clip is never started, and state 10 inherits an unstarted slot. This is a behavioural cliff, not a cosmetic one. |

**Stated as the brief asks: the threshold must stay greater than the largest intra-phase gate, which is
46. Recommended floor 47; absolute floor 24.**

---

## 5. THE STRETCH BOUND

**Nothing in the program stops you.**

* **Encoding.** `slti`'s imm16 is sign-extended, so the encodable positive range is `1 … 32767`. A value
  ≥ 32768 flips the compare's sign and inverts the phase (it would transition on tick 0) — a silent,
  total break, so a writer must range-check at **32767**.
* **The clock cell is 32-bit signed.** MEASURED from the program's own contract: the reset is a 32-bit
  `sw` of −1 at `0x1290`, the read is a 32-bit `lw` at `0x0b44`, and every guard is a **signed** `slti`.
  A 16-bit cell would break the very first compare, so the host's increment must be 32-bit-consistent.
  (INFERRED, host side: `$a3` is a PSX-translated host pointer handed in by the arg-setup helper
  `fn 0xdfd0` — `[rsp+0x50] → $a3`, translated at `0x12940` — from the launcher at `0xd980`, whose 6th
  argument is the SFX **task slot** (the 11-slot, `0x20`-stride table at `0x323278` that `fn 0x48b10`
  allocates and `0x48b97` initialises with `mov dword [rbx], esi`). I did **not** locate the per-tick
  increment instruction; R3's "reset to −1 ⇒ the case lasts N+1 ticks" model is validated behaviourally
  by the s53 capture's 5/5 boundary hits, not by reading the incrementer. Treat the host side as
  inferred.)
* **Practically**, at 60 fps a threshold of 32767 is 9 minutes; the phase is 70 ticks today. Overflow is
  not a real bound.

**The real ceilings on a stretch are outside the `slti`:**

1. **The unretuned reciprocals overshoot, linearly and unclamped.** `(clock<<12)/69` passes 4096 at
   clock 69 and keeps going (4155 at 70, 5936 at 100, 8192 at 138); the `4096 − t` lerp at `0x1108` goes
   **negative** past the old endpoint. This is *cosmetic drift inside the phase*, not a boundary
   misalignment — the two-clocks gate W3 is built on is unaffected. But it is the reason a "clean"
   proportional retime needs three edits, not one: `slti` 69 → 69+N, magic `0x76b981db` → the ÷(69+N)
   reciprocal, and magic `0xb60b60b7` → the ÷(45+N) reciprocal (that second one is a two-instruction
   `lui`/`ori` pair whose shift may also change, so it is **not** a same-length imm16 splice in general).
2. **`WAIT`'s operand is one byte.** The sequence carries the boundary with `WAIT 0, 1` at file `0x0436`
   (arg2 at `0x0438`); bumping it to `1+N` caps N at 254 through that op. Beyond that, insert a record —
   there are 745 bytes of `0xFF` filler after the stream inside sector 0 (§3.5).
3. **The camera block's frame words.** Shot A's keyframe frames are u16 with **flags in the top 3 bits**
   (W1 §2.3) — a writer must preserve `0xE000` and only add N to the low 13 bits. Not an A2 site, but the
   one place a stretch can silently corrupt data rather than merely mistime it.

**For the W3 gate specifically** — "a retimed cast holds phase↔cut alignment; a deliberate mis-retime
drifts" — only edit (1)'s `slti` and the sequence/camera shifts are required. The reciprocals are an
optional fidelity pass, and **the mis-retime artifact (the same build with the program edit omitted) is
exactly a one-imm16 difference at file `0x2E278`.** That is a two-byte A/B, which is about as clean a
falsification as this tier will ever get.

---

## 6. INTEGRITY — nothing checksums the id-3 image

| mechanism | present? | evidence |
|---|---|---|
| magic number / version field | **no** | `FORMAT.md` §2: "There is no magic number and no version field" |
| container checksum / CRC | **no** | same; the format's *only* self-check is structural |
| resource-table length check | **structural only** | `parse_header` (port of `fn 0xd390`): the running cursor `pos += sizeSectors << 11` must equal the file length. Holds 372/372 |
| per-resource size | **sector counts, unchanged by an imm edit** | the id-3 resource is 10 sectors (`0x5000`); the edit changes no byte count |
| id-2 sub-file directory | **untouched** | the directory lives in the id-2 resource; the edit is in id-3 |
| id-3 header / program table | **untouched** | `headerRel = 0x3120`, program table at `headerRel + 8`; the edit at `0x1278` is inside `[0, 0x3120)` |
| the MIPS pre-decoder (`fn 0xd1a0`) | **greedy ISA match, no validation of operands** | R1 §2: 99-row table, first-match; the imm16 is not part of any mask, so the same row matches before and after |
| loader-side asserts | **not on this path** | the `_wassert`s are on invalid *sequence* opcodes (`0x10..0x1F`) and unimplemented GTE cofuns — neither is an `slti` operand |
| runtime caching of the container | **none** | W2 §5: `SFX.Play` re-reads the bytes per action, no cache; this is why the override needs no relaunch |

**Verdict: an in-place imm16 edit at `0x2E278` cannot change any length, any sector count, any directory
entry or any checksum, because none of those depend on it and the last does not exist.** It rides the
exact same whole-container override path W2 already proved in-game.

---

## 7. SECONDARY — the motion clip LOOPS; a stretch is cosmetically free

The brief flagged this as best-effort. It is fully settled, by two independent routes that agree.

**Static (the program + the DLL).** The `Hi_DrawSummonModel` call in s0 is at image `0x0DD8`, and its
5th argument — the MIPS o32 stack slot `16($sp)` — is built two instructions earlier:
`addiu $v0, $zero, 1` at `0x0DC8`, `sw $v0, 16($sp)` at `0x0DCC`. So **`loopFlag = 1`**. The DLL's clamp
(`B2-motion-pipeline.md` / `M5-motion-payload.md`, `0x177C1…0x177DE`) is:

```
frameCount = u16[motion + 2]
if frameCount >  cur      : keep cur
else if (loopFlag & 1)    : cur = 0             <- LOOP
else                      : cur = frameCount-1  <- HOLD last
```

with `inc word[rec+0x54]` at `0x17888` — one clip frame per Draw, no timestep. `loopFlag & 1 == 1` here,
so **LOOP**.

**Measured (the archived s53 capture).** `sfxmeshprobe.20260724-085556.log`, `MODEL,227,<frame>,S,…`
rows, whose `aux0` is the summon slot's motion frame counter:

* frames 50…81: counter constant **0** — the slot is live but nothing draws (op 25 is on the `clock ≥ 24`
  arm; c0's fitted origin is frame 57, so clock 24 = frame 81);
* frames 82…105: counter **1, 2, … 24**, +1 per frame — the clip is playing;
* frame 106: counter **1**. It **wrapped**. There is no `SetSummonMotion` at that clock (s0's only
  op-26 sites are the tick-24 one-shot and the `clock ≥ 69` transition tail) and frame 106 is not a phase
  boundary, so this is the native LOOP wrap;
* frame 126 (clock 69, s0's last tick): counter 21; frame 127 (s10's first tick): 0, from s10's own
  restart.

**Observed period 24** — and ef227's clip **0** has `frameCount = 24` (the eight clips are 24, 30, 26,
48, 40, 68, 82, 28, read as `u16 @ motion+0x02`; 24 is unique among them). So the clip s0 starts at tick
24 is clip 0, and stock s0 already runs it **1.9 loops**.

**Consequence for the planned stretch:** the clip does not run out and does not freeze — it keeps
looping. The only visible difference is *where in the 24-frame cycle the phase ends*: stock ends on clip
frame 21; with a stretch of N it ends on `(21 + N) mod 24`. **A stretch of N ≡ 0 (mod 24) leaves even
that identical.** This is a cosmetic detail with a free mitigation, not a risk.

(General rule for other phases, since W3 may want it: the clip binds by INDEX via op 26, is scrubbed by
op 100, advances one frame per `DrawSummonModel`, and wraps-or-holds on the per-call `loopFlag` bit 0.
Nothing on disc says loop; it is a call-site argument.)

---

## 8. What is MEASURED vs INFERRED

**MEASURED** — read from the file/DLL/capture and re-verified by a second route:

* the id-3 image bases and the container's strict cursor match (`ef_container.parse_header`);
* file offset `0x2E278`, word `2aa20045`, its decode, and the imm16 byte positions (direct byte read +
  field decode, independent of the recovery);
* all ten transition guard offsets, words and immediates (direct byte read; every imm matches the
  recovery's threshold);
* s0's body extent, contiguity and single state store;
* zero `$s5` writes inside s0's body;
* the three uniqueness sweeps (instruction immediates, 32-bit words, 16-bit halfwords);
* every intra-phase compare in s0 and its branch shape;
* the three magic reciprocals and their divisors (emulated against `x // d` over 25k inputs; ÷69 is the
  unique solution over all shift/add-back combinations);
* the six read sites of `320($sp)` and the unclamped `4096 − t` lerp;
* the corpus statistics (16 clean machines, 85 thresholds, 49/85 unique-imm, ≥39/85 head reciprocal);
* the corpus container's sha256 matching `rescore.py`'s registered install hash;
* `loopFlag = 1` at s0's Draw site; the capture's 1…24-then-wrap counter; clip 0's `frameCount = 24`;
* the sequence tick arithmetic, the `WAIT` byte width, and the 745-byte `0xFF` tail inside sector 0.

**INFERRED** — reasoned, and labelled as such:

* the host-side identity of the clock cell (task slot `+0x00`, reached via `fn 0xdfd0`'s `$a3` slot). The
  program-side 32-bit contract is measured; **the incrementer itself was not located**;
* that the ÷69 and ÷45 reciprocals were *authored* to land on 4096 at the phase end. The arithmetic
  identity is measured; the intent is an inference (a very strong one — two independent constants both
  land exactly on 4096 at exactly clock 69);
* that op 26's motion index in s0 is clip 0. Inferred from the unique frame-count match (24), not read
  statically — its `$a0`/`$a1` both come from memory;
* the sector-0 filler being genuinely free space (it is 745 bytes of `0xFF` and unreachable because the
  sequence stops at `END_HOLD`, but nothing was proven to *not* read it).

**NOT settled, and left open on purpose:**

* the semantics of sequence opcode `0x2A` (arg1 = 77) at seq tick 81 — needed to resolve the §3.5
  boundary-side question;
* whether a retime should also retune the ÷46 sub-phase (46 is self-consistent within ticks 0…45 and does
  not depend on 69, so it is a design choice, not a correctness one);
* the exact instruction that increments the clock cell each host frame.

---

## 9. The bottom line for the W3 build

1. **The edit is two bytes** at file `0x2E278`/`0x2E279` (little-endian imm16), inside a whole-container
   override that W2 already proved lands in-game. Nothing else in the program has to move for the phase
   boundary to move.
2. **Bounds: N ∈ [47, 32767] is safe by construction; [24, 46] progressively deletes sub-phase structure;
   below 24 the creature stops being drawn.** For a first cast a stretch is far safer than a shrink — a
   stretch cannot delete anything, only overshoot ramps.
3. **The mis-retime artifact is exactly this two-byte difference**, which makes the W3 gate a genuine A/B
   rather than two unrelated builds.
4. **The trap to write down before anyone builds a general retimer:** the phase length is encoded three
   times in this case body, and only one of the three contains the digit 69. A tool that finds thresholds
   by searching for their value will be right on `ef227:c0 s0` and wrong on 36 of the corpus's 85
   thresholds — and will silently leave every phase's internal ramp normalising against the old length.

---

## 10. Artifacts (SCRATCH only — derived stock content, never committed)

`C:\gd\SCRATCH\summon-format\retime-w3-recon\`

| file | what |
|---|---|
| `disasm/ef227_c0.asm`, `disasm/ef227_c1.asm` | fresh R1 listings, regenerated this session (not the stale `disasm-r1/` dumps) |
| `a2_probe.py` / `a2_probe.txt` | the container walk, the state machines, the transition map with file offsets, the uniqueness sweeps, the transition-site context |
| `a2_ctx.py` / `a2_ctx.txt` | context dumps around every clock-dependent site in s0 |
| `a2_magic.py`, `a2_magic2.py` / `a2_magic2.txt` | the magic-reciprocal scan (v2 takes the shift from the `sra` that consumes the `mfhi`) |
| `a2_heads.txt` | the head of every case body in both programs |
| `a2_gatecheck.py` / `a2_gatecheck.txt` | the independent plain-reachability gate re-derivation (§4.2) |
| `a2_corpus.py` / `a2_corpus.txt` | the 372-file uniqueness + head-reciprocal census |
| `a2_gates.txt`, `a2_lerp.txt`, `a2_motion.txt`, `a2_seq.txt`, `a2_timeline.txt` | supporting dumps |
| `a2_host.py`, `a2_host2.txt` | the DLL-side probe for the MIPS argument slots (§5's inferred half) |

Reproduce the load-bearing offsets without any of them:
`py studies/custom-summons/tier-r/tier_r_disasm.py --listing <SCRATCH> C:\gd\SCRATCH\summon-format\ef227.bytes`
then `py studies/custom-summons/thomas-swap/disasm/ef_container.py C:\gd\SCRATCH\summon-format\ef227.bytes`
for the `0x2D000` base.
