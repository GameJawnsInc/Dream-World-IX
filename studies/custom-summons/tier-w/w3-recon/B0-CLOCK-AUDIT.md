# B0 — THE s0 CLOCK AUDIT

**TIER W rung 3, slice B0.** The complete, proven **E1** program edit set for stretching
`ef227:c0` state 0 from **70 ticks (threshold 69)** to **118 ticks (threshold 117)**, and the
offline emulator that proves it.

**READ-ONLY against the game.** Nothing was written to the install; no stock file was modified; no
existing tool (`rescore.py`, `summon_camera.py`, `camera_codec.py`, the tier-R tools) was touched.
Decoded stock listings and probe output live only under `C:\gd\SCRATCH\summon-format\retime-w3\b0\`
(§10). This report carries offsets, immediates, mnemonics and derived scalars — **no run of ≥ 6
consecutive stock bytes**.

**Deliverables**

| path | what |
|---|---|
| `studies/custom-summons/tier-w/w3_program_edits.py` | **the E1 spec** — `PROGRAM_EDITS`, the write guards, and the derivation that produces them |
| `studies/custom-summons/tier-w/w3_clock_emu.py` | **the emulator** — 137 checks, 0 failures; a library with a `__main__` |
| this report | the dataflow map, the verdict table, the results, the residual risk |

---

## 0. HEADLINE — three answers

**Q: what is E1?**
> **Seven in-place splices, 14 bytes written, 12 bytes actually different.** One `slti` immediate
> and **two magic reciprocals** (six halfwords + one shift field). A2 was right that the phase
> length is encoded three times; B0 adds *what each encoding drives*, which is what decides whether
> it moves.

**Q: does A2's apparent contradiction — a ÷45 ramp whose domain ends at clock 69, versus a
saturation gate at clock 45 — resolve into two ramps or one?**
> **Neither. It resolves into ONE ramp and ONE STEP, and they are unrelated.** The ÷45 reciprocal
> is the **creature's arrival ramp**: it normalises ticks 24…69 and drives the fly-in radius
> (1224 → 24), the model scale (6144 → 2048) and the spiral angle (0 → 3072). The `clock ≥ 45`
> site is **not a ramp at all** — `328($sp)` is zeroed at image `0x0B2C` on *every* tick before the
> dispatch, and s0's only write to it is the literal constant 4096. It is a **binary on-switch for
> the bone-trail block in the shared tail** (`0x2B38`), which reads it as an intensity argument.
> Both happen to carry the number 45; one is a divisor (69 − 24), the other an absolute tick.
> **A2 §4.1's "below 45 the ramp keeps running" is wrong — below 45 the value is simply 0.** §3.

**Q: what does NOT move, and why?**
> Every discrete beat (`clock < 12`, `≥ 24`, `== 24`, `== 44`, `≥ 45`, `≥ 35`, `< 46`) and **three
> clock-driven values that are RATES rather than progress ramps.** The distinction B0 mints:
> *a progress ramp is normalised to the phase and has a terminal value — retune it; a rate has an
> angular velocity and wraps — retuning it would slow a continuous motion, which is the wrong
> reading of "the entrance is longer".* §4, §6.

**The strongest single piece of evidence for the whole recipe:** the derivation in
`w3_program_edits.recompute` is not fitted to 117. Run it at **N = 0** and splice the result into
the shipping container and **zero bytes differ** — it reproduces `0x76B981DB` shift 5 and
`0xB60B60B7` shift 5 exactly, from arithmetic alone. The rule that picks the new constants is the
rule the original compiler used.

---

## 1. METHOD — how each class of fact was obtained

| step | how | class |
|---|---|---|
| the instruction words at every site | `struct.unpack_from` on the corpus container, re-decoded field by field (`b0_probe.py`) | **MEASURED** |
| the CFG of s0's body (`0x0B6C … 0x1384`, 519 instructions) | a fresh `tier_r_disasm` listing, read line by line; every branch arm walked by hand | **MEASURED** |
| what each value *drives* | followed to its HLE call site and argument slot (`hle_ops.json` names) | **MEASURED** for the call, **INFERRED** for the visual reading |
| `320($sp)` / `328($sp)` / `332($sp)` lifetimes | grep of every `$sp+0x140/0x148/0x14C` access in the whole c0 image, then read in context | **MEASURED** |
| the divisor behind each magic | probed with the image's own idiom against real division over ~40 k inputs (`_recover_divisor`) | **MEASURED** |
| every claim in §5–§7 | the emulator, replaying both timelines tick by tick | **MEASURED** |
| the drift guard | sha256 of the read container == `rescore.EXPECTED_STOCK_SHA[227]`; the audit also runs against the user's own `resources.assets` and passes there | **MEASURED** |

Reproduce: `py studies/custom-summons/tier-w/w3_clock_emu.py` (reads the install) or
`--blob C:\gd\SCRATCH\summon-format\ef227.bytes`.

---

## 2. THE DATAFLOW MAP — s0's clock has exactly five kinds of consumer

`$s5` is the clock, loaded once at image `0x0B44` and never rewritten inside the case (A2 §2).
Every use of it in `0x0B6C … 0x1384`, in order, falls into one of five classes.

```
                          $s5  (the phase clock)
                            |
   +--------+---------------+-----------------+------------------+-----------+
   |        |               |                 |                  |           |
 GATES   PROGRESS RAMP   ARRIVAL RAMP     GATE-LOCAL RAMPS      RATES      THE SLTI
 (7)     /69 -> 320($sp) /45 -> $s1       /12 (clock<12)      clock*7      69 -> state 10
         6 readers       9 derived values /46 (clock<46)      clock*245
                                                              clock*32
```

### 2.1 THE PROGRESS RAMP — `/69`, image `0x0B6C`, stored to `320($sp)`

```
0B6C lui  $v1, <M69.hi>     0B74 sll $v0,$s5,12      x = clock << 12
0B70 ori  $v1, <M69.lo>     0B78 mult $v0,$v1
0B80 mfhi $t1               0B84 sra $v1,$t1,5       no add-back
0B88 subu $v1,$v1,$v0       0B94 sw  $v1,320($sp)    <- UNCONDITIONAL, in a delay slot
```

`P = (clock << 12) / 69`, hitting **exactly 4096 on the phase's last tick**. Six readers, all
inside s0 (every other case writes `320($sp)` at its own head, so the slot is per-phase):

| reader | expression | what it drives | stock 0 → 69 |
|---|---|---|---|
| `0x1030` / `0x1064` | `P<3072 ? P+8192 : 5(P−3072)+11264` | effect-model **scale** (SVECTOR triple at `104/108/112($sp)`, op 24) | 8192 → **16384** (continuous at P=3072) |
| `0x108C` | `P >> 4` | effect-model **rotation X** | 0 → **256** |
| `0x10C0` | `((P>>1)+2048)>>5 − 128` | effect-model **RGB bias** (op 155) | −64 → **0** (fade to neutral) |
| `0x1108` / `0x113C` | `4096 − P`, × `rand(160)`, `>> 12`, added to x and z | the **camera-shake decay envelope** | 4096 → **0** |
| `0x122C` | `P >> 2` → `rcos` | the light column's transform angle (op 74), **inside the `clock < 46` block** | 0 → 667 at its last live tick |

**Every one of these is a progress ramp with an authored terminal value at the phase end.** Two of
them (`4096 − P` and the RGB bias) go **negative / past neutral** the moment `P` passes 4096, which
is the concrete harm A2 predicted.

### 2.2 THE ARRIVAL RAMP — `/45`, image `0x0C54`, kept in `$s1`

```
0C00 bne $s5,$v0,0xC58      0C04 lui $v1,<M45.hi>    <- DELAY SLOT: live on clock != 24
   (clock == 24: SetSummonMotion + SetSummonMotFrame(0))
0C54 lui $v1,<M45.hi>       <- live on clock == 24 only
0C58 ori $v1,<M45.lo>       0C5C addiu $v0,$s5,-24   x = (clock-24) << 12
0C64 mult / 0C68 mfhi / 0C6C addu $v1,$t1,$v0        <- THE ADD-BACK
0C70 sra $v1,$v1,5          0C78 subu $s1,$v1,$v0
```

`Q = ((clock − 24) << 12) / 45`, **0 at clock 24 and exactly 4096 at clock 69**. Nine derived
values, all on the `clock ≥ 24` arm:

| image | expression | what it drives | stock 24 → 69 |
|---|---|---|---|
| `0x0C7C`–`0x0CA4` | `θ = 2048 + rsin(0.75·Q)/8` | the creature's **spiral angle** (rsin arg 0 → **3072**) | 2048 → 1536 |
| `0x0CA8`–`0x0CC8` | `((4096 − Q)·1200 >> 12) + 24` | the creature's **fly-in radius** | **1224 → 24** |
| `0x0CCC`–`0x0D2C` | two segments joined at Q = 3072 | the creature's **vertical curve** (rsin arg) and **scale** | scale **6144 → 2048** |
| `0x0D30`–`0x0DD8` | `pos = base + (rcos θ, ·, rsin θ)·radius`, `rotY = 3072 − 2θ` | `Hi_DrawSummonModel` (op 25, `loopFlag = 1`) | — |

**This is the load-bearing ramp.** It is the creature flying in from far away and landing exactly
where state 10 expects it, on the phase's last tick. A2 framed ÷69 as the important one; the pose
that must be right at the boundary comes from ÷45.

### 2.3 `320` / `328` / `332($sp)` — the three scratch slots, traced end to end

All three are **zeroed at image `0x0B28`–`0x0B30`, every tick, before the dispatch**. That single
fact is what resolves §3.

| slot | written | read | meaning |
|---|---|---|---|
| `320($sp)` | `0x0B94` (s0 head, unconditional) — and once per case elsewhere | 6× inside s0; never in the shared tail | the progress ramp. Per-phase, no cross-phase carry. |
| `328($sp)` | `0x0E6C` only, and only the constant **4096**, gated `clock ≥ 45` | the shared tail `0x2B38` (`beq → skip`), `0x2B54` (halved), `0x2C74`, `0x2DA4`, `0x2E94` (passed at `20($sp)` to op 68) | **the bone-trail intensity.** A STEP, not a ramp: 0 below 45, 4096 at and above. |
| `332($sp)` | `0x0D4C` (set to 1 whenever the creature is drawn) | `0x0E54` (the `clock == 44` one-shot latches it into `80($s3)`), tail `0x2F24`/`0x3080` | "the creature is on screen", armed once at tick 44. `80($s3)` then gates the tail's trail block and is cleared there. |

### 2.4 The rest of the body — gate-local ramps and rates

| image | expression | domain | note |
|---|---|---|---|
| `0x0B98` `/12` reciprocal | `(clock<<10)/12` → `rcos` → `×255 >> 12` → op 64 | gated `clock < 12` | the intro fade, 255 → ~52. **A fourth reciprocal A2's magic table does not list.** |
| `0x1190` `/46` reciprocal | `150 − (clock·150)/46` → op 64 | gated `clock < 46` | the light column's own 150 → 0 countdown |
| `0x0CD8` `/3` | `Q // 3` | Q-domain | rebases with the arrival ramp automatically |
| `0x0E74`–`0x0E84` | `clock·245 + 455·i`, reduced mod 4096 **at most twice** | 9 beam elements | a **rate**; each element stops drawing for good once its phase passes 12288 |
| `0x0E88` | `clock·32 + 511·i` | the same elements' rotation | a rate, read only while drawn |
| `0x10A0` | `clock·8 − clock = clock·7` | effect-model **rotation Y** | a **rate** — a continuous spin on the 4096-unit circle |
| `0x0F9C`–`0x0FB8` | `(clock & 1) || clock ≥ 35` | the particle spawner | **runs every ODD tick from 1, and every tick from 35** — a rate doubling, not a start |

---

## 3. THE APPARENT CONTRADICTION, RESOLVED

A2 §4.1 lists, one line apart:

* a `/45` magic reciprocal whose domain runs ticks 24…69, and
* `slti $s5, 45` at `0x0E50`, where "`clock ≥ 45` writes the **saturated** constant 4096 to
  `328($sp)`; below 45 the ramp keeps running".

Those cannot both describe one ramp — a ramp that saturates at 45 cannot also be normalised to 69.

**The resolution: they are two different mechanisms that share a numeral.**

1. The `/45` reciprocal's `45` is a **divisor** — it is `69 − 24`, the length of the creature's
   fly-in window, and its output reaches 4096 at clock **69**, not 45. Verified: `Q(45) = 1911`,
   nothing special.
2. The `clock ≥ 45` site's `45` is an **absolute tick**. There is no ramp beneath it. `328($sp)`
   is zeroed at `0x0B2C` every tick, and s0's *only* write to it is `addiu $t1,$zero,4096` at
   `0x0E68`. So the value is `{clock < 45 → 0, clock ≥ 45 → 4096}` — a step. The consumer is the
   shared tail's bone-trail block, which uses it first as an on/off test (`beq $t1,$zero → 0x2EDC`)
   and then as an intensity argument.

**Consequence for the retime:** the arrival ramp must be retuned (its endpoint moves); the trail
switch must not (it is a beat, and it is *already* saturated over the whole extended window — the
strongest possible "proven-saturated" verdict, because the value is a literal constant).

*(The `clock == 44` one-shot at `0x0E48` sits on the same diamond and, on the equal branch, jumps
past `0x0E68` — so on tick 44 exactly, `328($sp)` stays 0. Tick 44 is below 45 anyway, so the step
is unaffected; but a retimer that "simplified" that diamond would silently change one tick.)*

---

## 4. THE PER-CONSTANT VERDICT TABLE

Every clock-coupled constant in `0x0B6C … 0x1384`. **Verdict** is one of KEEP (a beat or a
gate-local value), **RETUNE** (a phase-normalised progress ramp), PROVEN-SATURATED, or
PROVEN-COMPLETE (finishes before the stock end and stays finished).

| image | constant | what it is | drives | verdict | evidence |
|---|---|---|---|---|---|
| `0x0B6C`/`0x0B70` | `0x76B981DB` | **/69 progress reciprocal** | effect scale, tilt, RGB, shake envelope, column angle | **RETUNE → /117** | 5 of its 6 consumers have an authored terminal value at 4096; two go negative past it (emulator: `shake_env(117) = −2849`, `eff_rgb(117) = +44`) |
| `0x0B84` | shift 5 | that reciprocal's shift | — | **KEEP** | /117's magic also fits the no-add-back form at shift 5 (`0x46046047`), so the skeleton is unchanged |
| `0x0B8C` | `slti 12` | intro-fade gate | the `/12` block | **KEEP** | a beat; off throughout the extension |
| `0x0B98`/`0x0B9C` | `0x2AAAAAAB` sh 1 | **/12** reciprocal | the intro fade's `rcos` argument | **KEEP** | its divisor **equals its own gate** (12), not the threshold — proven by `_recover_divisor`; it can never overshoot because the block is skipped from tick 12 |
| `0x0BF0` | `slti 24` | creature-half split | everything in §2.2 | **KEEP** | a beat |
| `0x0BFC` | `addiu 24` | `clock == 24` one-shot | `Hi_SetSummonMotion` + `SetSummonMotFrame(0)` | **KEEP** | the clip must start on its stock beat; N = +48 = 2 full 24-frame loops so the end-phase clip frame is stock |
| **`0x0C04`** | `0xB60B` | **/45 arrival reciprocal, high half — DELAY-SLOT copy** | §2.2, on every tick ≠ 24 | **RETUNE → /93** | the load-bearing copy; the emulator shows patching only the *other* one leaves `arrival(117) = 4232` |
| **`0x0C54`** | `0xB60B` | same, **EQUAL-PATH copy** | §2.2, on tick 24 only | **RETUNE → /93** | inert at this N (`arrival(24) = 0` for any magic) — patched so the two copies can never disagree |
| **`0x0C58`** | `0x60B7` | /45 reciprocal, low half | shared by both paths | **RETUNE → /93** | — |
| `0x0C5C` | `addiu −24` | the arrival ramp's origin | — | **KEEP** | it *is* the `clock ≥ 24` gate; moving it would move a beat |
| `0x0C6C` | `addu` (add-back) | the 33-bit magic idiom | — | **KEEP (not nop-ed)** | /93's magic still needs 33 bits at shift 6, so the add-back stays correct — no instruction is removed anywhere in E1 |
| **`0x0C70`** | shift 5 | the arrival reciprocal's shift | — | **RETUNE → 6** | the smallest shift whose /93 magic needs the 33rd bit; shamt field only, `rt`/`rd`/`funct` untouched |
| `0x0CCC` | `slti 3072` | the vertical curve's Q-domain split | — | **KEEP** | Q-relative, so it rebases with the ramp for free; both segments stay continuous |
| `0x0CD8` | `0x55555556` | `/3` in the Q domain | the curve's rsin argument | **KEEP** | Q-relative |
| `0x0E48` | `addiu 44` | `clock == 44` one-shot | latches `332($sp)` → `80($s3)` | **KEEP** | a beat |
| `0x0E50` / `0x0E68` | `slti 45` / `4096` | the bone-trail on-switch | tail `0x2B38` block | **PROVEN-SATURATED** | it is a literal constant on a `≥` gate; the emulator asserts `328($sp) == 4096` on every tick 70…117 |
| `0x0E74`–`0x0E88` | `×245`, `+455`, `×32`, `+511` | 9 beam elements' phase and rotation | op 14/24/155 draws | **PROVEN-COMPLETE** | the mod-4096 loop can subtract at most twice, so an element with phase ≥ 12288 never draws again. Measured: the last element leaves at **clock 50**, 19 ticks before the stock end, and none returns through 117 |
| `0x0FA4` / `0x0FB0` | `slti 35` ×2 | the particle spawner's parity arms | op 97 + op 50 spawns | **KEEP** | a beat. (Correction: the block runs on every *odd* tick from 1 and every tick from 35 — a rate doubling, not a start) |
| `0x1050` | `slti 3072` | the effect scale's P-domain split | — | **KEEP** | P-relative; the two segments meet at 11264 on both sides |
| `0x10A0`/`0x10A4` | `×7` | effect-model **rotation Y** | op 24 | **KEEP — a RATE** | §6.1 |
| `0x1188` | `slti 46` | the light-column sub-phase gate | `0x1194…0x1274` | **KEEP** | a beat; the block is skipped throughout the extension |
| `0x1190`/`0x1194`/`0x11C8` | `0xB21642C9` sh 5 | **/46** reciprocal | the column's 150 → 0 countdown | **KEEP** | its divisor **equals its own gate** (46), not the threshold; the countdown is byte-identical tick for tick |
| **`0x1278`** | `slti 69` | **THE THRESHOLD** | the transition to state 10 | **RETUNE → 117** | the whole point |

**Reciprocal census, corrected.** s0's body holds **five** magic reciprocals, not the three A2's
table lists: `/69` (phase), `/12` (its own gate), `/45` (phase − 24), `/3` (Q-domain), `/46` (its
own gate). **Exactly two are coupled to the phase length, and both are in E1.** The emulator reads
all five out of the container and asserts that the other three divide by their own *gate* or their
own *domain* — a machine-checked statement of the distinction, so a future retimer cannot
re-litigate it by eye or, worse, retune one of them "for symmetry".

---

## 5. THE EDIT SET — E1

`studies/custom-summons/tier-w/w3_program_edits.py`, `PROGRAM_EDITS`.

| # | image | **file** | instruction | change | bytes |
|---|---|---|---|---|---|
| E1a | `0x1278` | **`0x2E278`** | `slti $v0,$s5,69` | imm16 **69 → 117** | 2 (1 differs) |
| E1b | `0x0B6C` | `0x2DB6C` | `lui $v1, ·` | imm16 → **/117 magic high half** | 2 |
| E1c | `0x0B70` | `0x2DB70` | `ori $v1,$v1, ·` | imm16 → /117 magic low half | 2 |
| E1d | `0x0C04` | `0x2DC04` | `lui $v1, ·` (delay slot) | imm16 → **/93 magic high half** | 2 |
| E1e | `0x0C54` | `0x2DC54` | `lui $v1, ·` (equal path) | imm16 → /93 magic high half | 2 |
| E1f | `0x0C58` | `0x2DC58` | `ori $v1,$v1, ·` | imm16 → /93 magic low half | 2 |
| E1g | `0x0C70` | `0x2DC70` | `sra $v1,$v1,5` | shamt **5 → 6** | 2 (1 differs) |

**7 sites · 14 bytes written · 12 bytes actually different.** New reciprocals: `/117` =
`0x46046047` at shift 5, no add-back; `/93` = `0xB02C0B03` at shift 6, add-back. Both are OUR
values, computed from arithmetic.

**Why the shift moves on one ramp and not the other.** The image uses two forms of the same idiom:
`M < 2^31` → plain `mfhi >> s`; `M ≥ 2^31` → `mfhi + x >> s`, where the add-back recovers the
unsigned high half of a 33-bit magic. Keeping each ramp's *existing* form fixes its shift:
the largest shift whose /117 magic still fits in 31 bits is **5** (unchanged); the smallest shift
whose /93 magic still needs the 33rd bit is **6**. Applied to the STOCK divisors that same rule
returns shift 5 for both — which is what they are.

**Nothing is added, removed or nop-ed.** The task's escape hatch (nop-ing an add-back) was
available and is **not used**: every edit is an immediate or a shamt, inside one instruction word,
same length, same opcode, same registers.

**The two `lui` copies are peers, and the split is a trap.** `0x0C04` sits in the delay slot of the
`clock == 24` `bne`, so it is the constant every tick *except* 24 uses; `0x0C54` is the equal-path
copy. The emulator builds both half-patches:

* patch `0x0C04` only → `arrival(117) = 4096`. Correct, because `0x0C54` is only live on the one
  tick where the ramp is 0 regardless.
* patch `0x0C54` only → `arrival(117) = **4232**` — the creature sails 136/4096 past its mark.
  **Small enough to pass a glance**, which is exactly why the set names both.

**Guards.** `verify_stock(blob)` refuses unless all **eight** candidate sites (the seven above plus
the progress-shift word at `0x0B84`, which this N does not write) hold their stock halfwords, and
unless all eight untouched gate immediates hold their stock values. It therefore also refuses a
double-apply. `apply_edits` re-checks same-length, single-word containment and no overlapping
writes at the call site.

---

## 6. THE EMULATOR AND ITS RESULTS

`studies/custom-summons/tier-w/w3_clock_emu.py` replays every clock-coupled expression in s0's body
with exact MIPS semantics (32-bit wrap, signed `mult` + `mfhi`, arithmetic `sra`, both magic-division
idioms), for every tick of both timelines. Every constant is read from the container at run time;
no stock byte is embedded. It does **not** model `rsin`/`rcos` — and does not need to, because
proving that the *argument* at the patched last tick equals the argument at the stock last tick
proves the resulting pose is identical whatever the function is.

**`137 checks, 0 failures`** — against the corpus copy and against the user's own
`resources.assets`, both under the registered sha guard.

### 6.1 (a) The stock machine reproduces its known endpoints

`progress(0) = 0`, `progress(68) = 4036`, `progress(69) = 4096` (A2 §3.2's independently measured
numbers); `arrival(24) = 0`, `arrival(69) = 4096`; `shake_env(69) = 0`; `eff_rgb: −64 → 0`;
`eff_scale: 8192 → 16384`; `eff_tilt(69) = 256`; `cre_radius: 1224 → 24`; `cre_scale: 6144 → 2048`;
`cre_theta(69) = 3072`; `cre_y(69) = (branch B, 1024)`; `328($sp)` steps 0 → 4096 between ticks 44
and 45; the column countdown starts at 150 and its block is off from tick 46; the 9 beams leave for
good at tick **50**.

### 6.2 (b) The patched ramps land, hold, and never invert

| ramp | stock @69 | patched @117 | monotone | inside the stock range | ever negative |
|---|---|---|---|---|---|
| progress | 4096 | **4096** | ✔ | [0, 4096], 0 excursions | no |
| arrival | 4096 | **4096** | ✔ | [0, 4096], 0 excursions | no |
| eff_scale | 16384 | **16384** | ✔ | [8192, 16384] | no |
| eff_tilt | 256 | **256** | ✔ | [0, 256] | no |
| eff_rgb | 0 | **0** | ✔ | [−64, 0] | (stock is negative too) |
| shake_env | 0 | **0** | ✔ | [0, 4096] | no |
| cre_radius | 24 | **24** | ✔ | [24, 1224] | no |
| cre_scale | 2048 | **2048** | ✔ | [2048, 6144] | no |
| cre_theta (rsin arg) | 3072 | **3072** | ✔ | [0, 3072] | no |
| cre_y (rsin arg) | (B, 1024) | **(B, 1024)** | — | — | — |

Every start value is identical too, so both ramps are the same curve stretched, not shifted.

### 6.3 (c) Every beat is where it was

All eight gate immediates byte-identical. All ten per-tick discrete signals (`intro_ran`,
`creature_ran`, `motion_oneshot`, `latch_oneshot`, `trail`, `beams`, `spawner_ran`, `column_ran`,
`beam_cd`, `eff_spin`) **identical tick for tick over the whole stock window 0…69**. Over the
extension 70…117: the trail stays saturated at 4096, no beam returns, the column stays off, the
spawner holds full rate, no one-shot re-fires, and exactly one tick transitions.

### 6.4 (d) The same-length proof

Container length unchanged (823,296 B); instruction count unchanged; every edit `len(new) ==
old_len`; every edit inside a single 4-byte word; **no byte changed outside the 7 declared words**
(12 bytes in 7 words); and each touched word still decodes with its own format's structural fields
preserved — `op/rs/rt` for the six I-types, `op/rs/rt/rd/funct` for the one R-type, with only the
immediate (or shamt) moved.

### 6.5 The mis-retime artifact's offline signature

Running the *stock* constants out to clock 117 — the MIS-RETIME build, E1 omitted entirely — gives:

| signal | at clock 117 | stock endpoint |
|---|---|---|
| progress | **6945** | 4096 |
| arrival | **8465** | 4096 |
| shake envelope | **−2849** | 0 (the camera jitter grows, with the wrong sign) |
| creature radius | **−1256** | 24 (through its mark and out the far side) |
| creature scale | **−15428** | 2048 (the model inverts) |
| effect RGB | **+44** | 0 (over-bright) |

That is a far louder artifact than the orchestrator's brief anticipated. **It is worth saying
plainly before the cast: the MIS-RETIME build is not a subtle drift — with E1 omitted the creature's
own arrival arithmetic inverts.** If W3 wants a *subtle* falsifier for the two-clocks law, A3 §7's
`E3-alt` (the one-tick camera-lead variant) is the better instrument; this one is the loud proof
that the program clock and the presentation clock are genuinely separate.

### 6.6 The identity check

`build_edits(0)` — the same derivation at zero stretch — spliced into the shipping container
changes **0 bytes**. The recipe reproduces `0x76B981DB`/shift 5 and `0xB60B60B7`/shift 5 exactly.

### 6.7 The recipe generalises

`recompute(n)` was swept over N ∈ {−22, −10, 0, +12, +24, +48, +96, +186, +231}: every one lands
`progress = arrival = 4096`, `radius = 24`, `scale = 2048` at its own last tick. The site count
varies 6–8 as the two shifts move; `recompute` refuses any N that puts the threshold below **47**
(the largest intra-phase gate is `clock < 46`, A2 §4.3).

---

## 7. RESIDUAL VISUAL RISK — for the cast protocol, stated plainly

All four are **deliberate consequences of the locked policy**, not defects, and all four are
re-derived from the container by `w3_clock_emu.residuals()` so the numbers stay honest.

1. **The effect model's spin runs 29.5° further.** Rotation Y is `clock × 7` — a **rate**, not a
   progress ramp. It reaches 483 at the stock end and **819** at the new end. Retuning it would
   *slow a continuous spin*, which is the wrong reading of "the entrance is longer"; and no
   same-length 2-instruction skeleton (`sll k` + `subu`) can express `×4.13` anyway. **Risk: low.**
   Cosmetic, and only if the spin's phase at the cut was authored to matter.
2. **The light column ends its sub-phase earlier in the progress ramp.** The column keeps its stock
   schedule (its own /46 countdown is identical tick for tick — 150 at 0, 4 at 45) but the `rcos`
   angle it reads from the progress ramp is now **393 instead of 667** on its last live tick: it
   ends **38 %** of the way through the ramp instead of 65 %. **This is the one place the policy
   visibly breaks an authored coupling**, and it is unavoidable — any ramp consumed inside a
   fixed-tick sub-block reads a different value once the ramp is slower. **Risk: low–moderate.**
   Watch the descending light column in ticks 0–45 for a shape that "stops short". The alternative
   (stretching the `clock < 46` gate and retuning /46 too) would move a discrete beat, which the
   locked policy forbids.
3. **The particle spawner runs 48 extra ticks at full rate and the bone trail stays lit 48 ticks
   longer.** Both gates are absolute ticks the policy deliberately leaves alone. **Risk: low** —
   this is what "a longer entrance" should look like; it may read as slightly denser than stock.
4. **The float clip keeps looping.** N = +48 is exactly two 24-frame loops, so the clip frame at
   the new phase end is the one stock ends on (A2 §7). **Risk: none, by construction.**

**Not a risk but worth the cast report's first line:** the OUTER text `Sequence.seq` clock
(A4 §4) is untouched by E1 and drifts by N unless E4 ships. Judge the W3 gate on container-internal
alignment, exactly as A4 §4.5 recommends.

---

## 8. CORRECTIONS TO THE STANDING RECORD

1. **A2 §4.1, `slti 45`.** "`clock ≥ 45` writes the saturated constant 4096 to `328($sp)`; below 45
   the ramp keeps running" — there is no ramp. `328($sp)` is zeroed at `0x0B2C` every tick and s0's
   only write to it is the constant. It is a step, and its consumer is the shared tail's bone-trail
   block, not anything inside s0. §3.
2. **A2 §4.1, the parity block.** Described as "a `clock ≥ 35` sub-block that alternates by parity".
   Read arm by arm it is the other way round: it runs on **every odd tick from 1**, and on **every**
   tick from 35 — a rate doubling at 35, not a start at 35.
3. **A2 §3.2's magic table lists three reciprocals in this case body; there are five** (`/69`,
   `/12`, `/45`, `/3`, `/46`). The `/12` at `0x0B98` is a clock reciprocal A2's head scanner missed,
   and — like `/46` — its divisor is its own gate, not the phase length.
4. **A2 §5 / §9.1: "the mis-retime artifact is exactly a one-imm16 difference at `0x2E278`" and
   "nothing else in the program has to move for the phase boundary to move".** True of the
   *boundary*; false of the *build*. The ALIGNED artifact is 7 sites / 12 differing bytes, and the
   ALIGNED↔MIS-RETIME A/B is that whole set, not two bytes.
5. **A2 §5's framing of the retune as "three edits" (`slti` + two magics) and "not a same-length
   imm16 splice in general".** It is same-length here: 6 immediates + 1 shamt, no instruction added
   or removed. The general statement is right in principle — a different N can move the *other*
   shift too (the sweep in §6.7 shows 8 sites at N = +96) — but it never needs a length change,
   because both shift fields are in-place shamts.
6. **A2 §3.2 identified `/69` as the ramp whose overshoot matters.** `/45` matters more: it carries
   the creature's own arrival pose, and it is the one whose unretuned overshoot inverts geometry.

---

## 9. MEASURED vs INFERRED

**MEASURED** — read from the container / listing and re-verified by a second route:

* every instruction word, field decode and file offset in §4 and §5 (direct `unpack_from`, then
  re-decoded; cross-checked against a fresh `tier_r_disasm` listing);
* the divisor behind each of the five reciprocals (probed against real division, ~40 k inputs each);
* the complete `320`/`328`/`332($sp)` write/read sets across the whole c0 image;
* the branch structure of every gate, one-shot and diamond in s0 (walked arm by arm);
* every number in §6 — endpoints, monotonicity, ranges, beat identity, the same-length proof, the
  half-patch outcomes, the mis-retime signature, the N = 0 identity, the N sweep;
* the beam elements' retirement at clock 50 and their non-return through 117;
* the drift guard passing against both the corpus copy and the user's own `resources.assets`.

**INFERRED** — reasoned from the call sites, labelled as such:

* the *visual meaning* of each value ("fly-in radius", "camera shake", "light column", "bone
  trail"). The call site, argument slot and HLE op are measured; the reading of what the player sees
  is an inference from the op's name and the value's shape. It is strong for the creature (op 25
  `Hi_DrawSummonModel`'s own position/scale/rotation arguments) and weaker for the tail's op 68;
* that the author *intended* both reciprocals to land on 4096 at the phase end — the arithmetic
  identity is measured, the intent is inference (a strong one: two independent constants both hit
  exactly 4096 at exactly clock 69);
* that a RATE should not be retuned while a PROGRESS ramp should. This is a design judgement, argued
  in §7.1 and §7.2, not a measurement. It is the one place a reviewer could reasonably disagree.

**NOT settled, deliberately:**

* whether the light column's earlier ramp position (§7.2) is visible at all. Only the cast answers
  that;
* the exact instruction that increments the phase clock each host frame (A2 left this open too);
* `unk`-named tail ops `0x2C74`/`0x2DA4`/`0x2E94` — their argument shapes are read, their visuals
  are not.

---

## 10. FILES

**Committable (this rung's deliverables):**

| path | what |
|---|---|
| `studies/custom-summons/tier-w/w3_program_edits.py` | E1 as data + its derivation + the write guards |
| `studies/custom-summons/tier-w/w3_clock_emu.py` | the emulator (library + `__main__`); `audit()` is what B2's gates call |
| `studies/custom-summons/tier-w/w3-recon/B0-CLOCK-AUDIT.md` | this report |

**SCRATCH only — stock-derived, never committed** (`C:\gd\SCRATCH\summon-format\retime-w3\b0\`):

| file | what |
|---|---|
| `s0_body.asm` | s0's 519-instruction body, sliced out of a fresh `tier_r_disasm` listing |
| `b0_probe.py` / `b0_probe.txt` | the site-by-site word decode, the reciprocal identification, the new-magic search |
| `b0_emu.txt` | the emulator's full 137-check output |
| `b0_table.txt` | the per-tick signal table, both timelines |

Reproduce the listing without any of them:
`py studies/custom-summons/tier-r/tier_r_disasm.py --listing <SCRATCH> C:\gd\SCRATCH\summon-format\ef227.bytes`.
