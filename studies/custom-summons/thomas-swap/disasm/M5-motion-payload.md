# M5 — THE MOTION PAYLOAD + THE POSE PIPELINE (decoded, x86-cross-checked, validated on real stock bytes)

Slice M5 of the FF9SpecialEffectPlugin.dll summon-cutscene disasm round. Decodes **how per-frame bone
transforms are produced**: the motion clip's on-disk layout, the rotation encoding, the skeleton /
parenting representation, the frame-advance state machine, and what a re-import would have to emit.
Also answers the round's blocking question — *does the Eff-model family share this machinery?*

Every claim is cited `fn@rva : ins@rva` (x64 `ImageBase 0x180000000`, RVA = VA − base), `fn@rva` for the
32-bit build (`ImageBase 0x10000000`), or `file:line` for C#. **Three independent evidence lines agree:**
x64 disassembly, x86 disassembly (different codegen, same source), and a **byte-level structural
validation against a real stock clip** (Bahamut's own animation set) that tiles with **zero gaps and
zero overlaps**.

> **Provenance.** Static analysis of the user's installed DLL + a structural read of a locally-extracted
> stock blob kept under `C:/gd/SCRATCH/summon-format/` (never the repo). The scanners
> (`m5_motion_scan.py`, `m5_motion_verify.py`, `m5_chain.py`, `m5_stats.py`) are pure format-parser code
> and print **structure + statistics only** — no geometry/animation payload is echoed or copied. No DLL
> was modified.

---

## 0. TL;DR — the five answers

1. **The motion clip is fully decoded and it is a small, regular, re-authorable format.** Header 0x14 B;
   per-bone rotation = **three 12-bit Euler angles built from an 8-bit coarse track + an optional 4-bit
   fine track** (2 frames per byte); root translation = three s16 tracks (or constants); every field is a
   motion-relative byte offset. **`Motion` carries rotation + a root translation ONLY.** §2.
2. **The skeleton is NOT in the clip — it is in the model**, as a 4-byte-per-node table:
   `{ s16 boneLength; u8 unused; u8 parentIndex }`. A bone's local translation is **`(0, 0, boneLength)`**
   — the classic FF9 "parent + length" skeleton. Node count = `u8[model+0x02]`. §4.
3. **Validated on real bytes: `ef227.bytes` = `Bahamut__Full`** (`SpecialEffect.cs:99`) contains **8 motion
   clips, all 93 bones**, back-to-back at file offset `0x07579c..0x089ad4`, plus an **8-entry motion
   pointer table at `0x4a180`**. Every clip's regions partition its span with **0 gaps / 0 overlaps**
   under the decoded layout. A wrong layout cannot tile. §3.
4. **Eff-models are RIGID — the EFFARR hypothesis is REFUTED as the creature's carrier.** All five
   `Hi_Register*EffModel` bodies explicitly write `DATA+0x10 = 0` (the motion pointer), and there is **no
   `Hi_SetEffModelMotion`** anywhere in the DLL's symbol strings. Conversely `Hi_DrawEffModelByBone`
   **reads the SUMMON array** (`0x220830`) and copies a summon *bone's* world matrix into the eff-model's
   root — eff models hang **off** the creature's skeleton. The creature is the summon slot. §7.
5. **THE TRACKING RESULT (the round's motivating problem): the s52 ROOT probe is NOT reading the wrong
   subsystem and its data is NOT garbage — it is a correct, smooth, phase-structured trajectory that
   matches the user's video description beat for beat. It was MIS-READ: `SummonData+0x40` is `R·S`, not
   `R`, and the authored SCALE sweeps 0.02× → 3.0×** (Bahamut's approach/recede is done by *scaling*, PSX
   fake-perspective style, not only by moving). `root_reproject.py:43,75` divides by 4096 and treats the
   result as a rotation, discarding the scale entirely. That is the concrete defect behind "a flight built
   on it made the promo worse." §8.

---

## 1. `0x7820` — the pose builder, and its THREE branches

`0x7820` is the shared per-frame node-matrix builder called by **all six** draw bodies
(`0x16234` DrawEffModel · `0x16653` DrawSliceEffModel · `0x168d0` DrawEffModelByBone · `0x16e39`
DrawMorphEffModel · `0x172fd` DrawMorphModelByBone · **`0x1786e` DrawSummonModel**). MSVC split it into
four `.pdata` chunks — the logical function is **`0x7820 .. 0x83c7`** (2983 B); `refkit.func_of` returns
only the first chunk (`0x7820..0x7a31`), which is why the prior round read the motion branch as a
"tail-call". x86 analogue: **`0x70c0`**.

```
void* nodeBuilder(SummonData* d /*rcx*/, u16 frame /*dx*/, PSXMATRIX* nodeBuf /*r8*/)
    d->bones = nodeBuf;                                  ; 0x7842   (x86 0x70e0)
    if (d->motion /*+0x10*/)          -> branch M        ; 0x7846 jne 0x7a20
    else if (d->parent /*+0x30*/)     -> branch P        ; 0x784f
    else                              -> branch R        ; 0x7856 je 0x797a
    return nodeBuf + writtenNodes;                        ; branch M 0x8379 / P,R "lea rax,[r13+0x20]"
```

| branch | condition | what it writes |
|---|---|---|
| **M — animated** | `DATA+0x10 != 0` | decodes the whole clip at `frame` for **all N nodes**, then runs the hierarchy pass. §2/§4 |
| **P — attached rigid** | no motion, `DATA+0x30 != 0` | node0 = the PARENT DATA's bone `u8[DATA+4]` matrix, verbatim, plus the local offset `DATA+0xa0` (`0x7de7-0x7ed7`; x86 `0x70eb-0x71f9`) |
| **R — free rigid** | no motion, no parent | node0 = `DATA+0x40` with matrix columns 1,2 negated (`neg cx` ×6, `0x797a-0x7a0f`; x86 `0x71fa-`) |

**Only branch M writes more than one node.** Branches P and R write node0 and return `nodeBuf+0x20`;
branch M returns `nodeBuf + N*0x20`. The caller commits that pointer back into the frame scratch arena
(`DrawSummonModel@0x17873-0x17885`: `0x12940(arena, ret) -> [ctx+0x24]`), i.e. **the node matrices are
allocated from a per-frame linear arena, not from a persistent buffer**.

> **Correction to B1 §3 / FINDINGS §3.1.** `DATA+0x38` is set **once per Draw** (`0x7842`), not
> "re-pointed per node" — the whole N-matrix block is valid after the tick. And **`bone[0] == DATA+0x40`
> is TRUE ONLY in branch R** (a rigid eff-model). Under a motion (branch M — every real summon frame)
> `bone[0]` is `DATA+0x40` **composed with the clip**, see §5.

---

## 2. THE MOTION CLIP — on-disk layout (branch M, `0x7a20..0x7dba`; x86 `0x728f..0x7548`)

```c
struct Motion {                 // header = 0x14 bytes
/*+0x00*/ u16  unknown;         // never read by the pose pipeline
/*+0x02*/ u16  frameCount;      // valid frames are 0 .. frameCount-1
/*+0x04*/ u16  tx;              // flags&1 ? (s16) CONSTANT : byte-offset -> s16 track[frameCount]
/*+0x06*/ u16  ty;              // flags&2 ? ...
/*+0x08*/ u16  tz;              // flags&4 ? ...
/*+0x0a*/ u8   flags;           // bits 0..2 only ("root translation axis is constant")
/*+0x0b*/ u8   pad;
/*+0x0c*/ u32  rotKeyOff;       // motion-relative BYTE OFFSET, < 0x10000  -> RotKey[nodeCount]
/*+0x10*/ u32  fineKeyOff;      // motion-relative BYTE OFFSET, < 0x100000 -> RotKey[nodeCount], or 0
};                              // everything after +0x14 is payload, all offsets motion-relative

struct RotKey {                 // 8 bytes, ONE PER NODE, in both tables
    u16 a0;  s16 a1;  u16 a2;   // per axis: flags-bit SET => literal value; CLEAR => byte-offset to a track
    s16 flags;                  // bits 0..2 = "axis is a literal, not a track"
};
```

### 2.1 The relocation (why the offsets look like pointers at runtime)

`DrawSummonModel` converts `[motion+0x0c]` and `[motion+0x10]` **in place, on the first draw**, from a
relative offset to a packed PSX address, guarded by the bounds above
(`0x17785-0x177b4`; x86 `0x13d2d-0x13dcc` shows the encoder explicitly: `esi -= ramBase; esi |= 0x80000000`
or `esi -= segBase[seg]; esi |= (seg<<24)|0xC00000`). **On disk they are plain offsets; after frame 1 they
are packed addresses.** A re-importer emits offsets. (B2 called this "VA-relocate"; the bound constants
`0x10000` / `0x100000` are the disk-format discriminator.)

### 2.2 Root translation — per frame (`0x7b9e..0x7c1a`; x86 `0x72da..0x7337`)

```
for axis i in {X,Y,Z}:
    if (flags & (1<<i)):  node0.t[i] = (s16) hdr.t[i]                      ; constant
    else:                 node0.t[i] = (s16) motion[ hdr.t[i] + frame*2 ]  ; per-frame s16 track
```
Written straight into `nodeBuf[0].t` (`+0x14/+0x18/+0x1c`) BEFORE the node loop. This is **root motion**.

### 2.3 Rotation — the 12-bit two-stream encoding (`0x7c40..0x7dba`; x86 `0x735c..0x7548`)

Per node `k`, per axis `i` (0,1,2 = the arguments of `RotMatrix` `0x37a0`, `0x3850`, `0x3910` in that
call order — `0x7d8a/0x7d9a/0x7daa`):

```
coarse = RotKey[k].field[i]
if !(RotKey[k].flags & (1<<i)):  coarse = motion[ coarse + frame ]      ; u8 track, 1 byte per frame
fine = 0
if (fineKeyOff):
    f = FineKey[k].field[i]
    if !(FineKey[k].flags & (1<<i)):  b = motion[ f + (frame>>1) ]      ; NIBBLE track, 2 frames per byte
                                      f = (frame & 1) ? (b >> 4) : b
    fine = f & 0xF
angle[i] = (s16)(((coarse << 4) | fine) & 0xFFFF)                       ; 0..4095  == 0..360 deg (PSX 4096/turn)
```
Bit-exact evidence (x64): `shl r9,4` `0x7c65` · `shl rcx,0x14` `0x7c7e` · `shl rdx,4` `0x7c96` ·
`or r10d,ecx` `0x7c9e` · stores `[0x212040]=r10` `0x7ca7`, `[0x212044]=edx` `0x7ca1` · nibble path
`and r11d,1` `0x7cca` / `shr ebx,1` `0x7cce` / `sar r9,4` `0x7cee` / `and r9d,0xf` `0x7cf2` ·
final `or r10d,eax` `0x7d46`, re-store `0x7d49/0x7d53` · reads `movsx [0x212040/42/44]`
`0x7d7b/0x7d8f/0x7d9f`. x86 mirror: `shl edx,4` `0x73b4` · `shl esi,0x14` `0x73e9` · `and eax,0xf`
`0x749b/0x74e3/0x7521` · `and eax,1`/`shr ecx,1` `0x743f/0x7442`.

Each node's 3×3 is then built from a **fp12 identity seed** (`0x7d5a-0x7d77`, the same seed pose_eval
uses) followed by the three `RotMatrix` calls, into `nodeBuf[k]` — **rotation only; the node loop never
writes a translation.** `r12 += 8` / `rbp += 8` per node (`0x7d86`, `0x7d4f`).

**There is no interpolation, no keyframe times, no easing.** One stored sample per frame per channel.
Advancing is `frame+1`; §6.

---

## 3. VALIDATION AGAINST REAL STOCK BYTES — `ef227.bytes` = `Bahamut__Full`

`SpecialEffect.Bahamut__Full = 227` (`Memoria/Data/Battle/SpecialEffect.cs:99`), and it is in
`SFXData.FixedCameraEffects` (`SFXData.cs:1346`). The locally-extracted blob (823,296 B) was scanned
with `m5_motion_scan.py` using only the decoded header invariants, then each hit was expanded region by
region with `m5_chain.py`.

| # | file offset | frames | flags | span | gap | overlap |
|---|---|---|---|---|---|---|
| 1 | `0x07579c` | 24 | 5 | `0x1070` | 0 | 0 |
| 2 | `0x07680c` | 30 | 7 | `0x12d9` (+3 pad) | 2 | 0 |
| 3 | `0x077ae8` | 26 | 0 | `0x157b` | 0 | 0 |
| 4 | `0x079064` | 48 | 1 | `0x3374` | 0 | 0 |
| 5 | `0x07c3d8` | 40 | 1 | `0x2010` | 0 | 0 |
| 6 | `0x07e3e8` | 68 | 0 | `0x420e` (+2 pad) | 0 | 0 |
| 7 | `0x0825f8` | 82 | 1 | `0x5489` (+3 pad) | 2 | 0 |
| 8 | `0x087a84` | 28 | 1 | `0x204e` (+2 pad) | 0 | 0 |

* **All eight clips report exactly 93 nodes** (the key-table fixpoint), and each clip's header +
  key tables + translation tracks + every referenced byte/nibble track **exactly partition** its span.
  The 2-byte "gaps" are 4-byte alignment padding between clips.
* **The clips are contiguous**: each clip's computed end lands on the next clip's start
  (`0x07579c + 0x1070 = 0x07680c`, …), forming one 82,744-byte motion block `0x07579c..0x089ad4`.
* **Motion pointer table**: eight consecutive `u32` at file offset **`0x4a180`**, each equal to
  `clipFileOffset − 0x62E60` (`m5_findtable.py`, 8/8 match on a single additive constant — the blob's
  chunk base). Clip 1's value also appears at `0x4a014` = the "initial motion" the model header hands
  `Hi_RegisterSummonModel` (`u32[modelArg+0x180]`, `0x15fc6`).
* **Negative control**: `ef000.bytes` (a non-summon effect) yields **zero** candidates — consistent with
  §7's finding that only the summon slot ever binds a motion.
* Root-translation tracks decode to smooth series (median frame-to-frame step 1–7 units, max 93), and
  node-0 angle tracks decode to smooth circular series (median step 0–50 of 4096) — semantic sanity.

### 3.1 Payload economics (what a re-import costs)

`m5_stats.py`, per clip: only **22 %–56 % of the 279 (93×3) rotation channels are animated**; the rest are
literals in the key. Every animated channel gets its **own** track offset (no sharing observed).
Cost ≈ **1.9–3.1 bytes per bone per frame** for a full 12-bit 3-axis rotation. Bahamut's entire 8-clip,
93-bone, 346-frame animation set is 82 KB.

---

## 4. THE SKELETON — it lives in the MODEL, not the clip

The hierarchy pass (`0x80aa..0x83c7`; x86 `0x79c8..0x7bd0`) re-resolves the model from `DATA+0x08` and
reads a node table at **`u32[model+0x0c]`**:

```c
struct ModelHeader {            // packed PSX model blob
/*+0x02*/ u8   nodeCount;       // 0x7aba  movzx r10d, byte[model+2]   (x86 0x72a5)
/*+0x03*/ u8   meshCount;       // DrawSummonModel 0x17900             (hide-mask bit index domain)
/*+0x0c*/ u32  nodeTable;       // 0x813e                              (4 B per node)
/*+0x10*/ u32  meshTable;       // 0x4eb0 : 0x4f58, stride 0x28        (per-mesh draw records)
};
struct Node {                   // 4 bytes
    s16 length;                 // 0x7aba->0x8282 : the ONLY per-node geometry datum in the table
    u8  unused;                 // never read by the pose pipeline
    u8  parentIndex;            // 0x81aa  movzx edi, byte[entry+3]    (x86 0x79e3 / 0x7b94)
};
```

The child's **local translation is a hard-coded `(0, 0, length)`**: the x64 build clears both leading
components with one qword store `mov qword[0x212048], rdi(=0)` (`0x7abf`) and only writes the third from
the node entry (`0x8282 -> [0x212050]`); the **x86 build clears them as two separate dword stores**
(`0x72a9`, `0x72b3` → `0x101fa0b8`, `0x101fa0bc`) and writes `[0x101fa0c0]` from `movsx word[entry]`
(`0x7aba/0x7abd`) — two independent codegens agreeing that these are three separate slots, two of which
are permanently zero. The 4-word SVECTOR is then packed and passed to the RotTrans helper
(`0x8310-0x836a`; x86 `0x7b46-0x7b88`).

**Per-node composition (children, `k >= 1`):**
```
world.R[k] = world.R[parent] * local.R[k]                  ; three column mults, 0x41e0 (x86 0x3ea0)
world.t[k] = world.R[parent] * (0,0,length[k]) + world.t[parent]   ; RotTrans 0x3d60 (x86 0x39d0)
```
Nodes are walked in index order starting at 1 (`rbp = nodeTable + 4`, `rbp += 4`, `rsi += 0x20` until
`nodeBuf + N*0x20`) — so **a parent's index must be lower than its child's**; the format has no sorting
pass. That is a hard constraint on any re-import.

---

## 5. THE ROOT — what `bone[0]` really is (the tracking-critical composition)

Branch M, no parent (`0x7edc..0x80a6`; x86 `0x7843..`):

```
GTE current matrix R <- DATA+0x40 .. +0x50      ; 0x7edc-0x7f04   (x86 0x7843-0x786a)
GTE translation   T <- DATA+0x54/+0x58/+0x5c    ; 0x7f0a-0x7f1f   (x86 0x786f-0x7882)
bone[0].R = R * clipRotation[0]                 ; 3x 0x41e0       (0x7f46 / 0x7fa2 / 0x7ffe)
bone[0].t = RotTrans(R, clipRootTranslation)    ; 0x3d60 @0x8087  -> results 0x211fe4/e8/ec -> +0x14/18/1c
```
`0x3d60` verifiably ADDS the translation register (`add r11d,[0x211f54]` `0x3dc5`, `add r9d,[0x211f58]`
`0x3df2`), so:

> **THE LAW.** With a motion bound,
> **`creature_world_position = R_root · rootTranslation(frame) + T_root`** and
> **`creature_world_orientation = R_root · clipRotation[0](frame)`**,
> where `R_root` / `T_root` are `SummonData+0x40` / `+0x54` (pose_eval from the Draw args) and the clip
> terms come from the motion. **`bone[0] != DATA+0x40`.**

Branch P adds the local offset `DATA+0xa0` (the `Hi_SetEffModelOffset` vector) through `0x40d0`, then
adds it to the node translation (`0x795a/0x7965/0x796c`; x86 `0x71d9/0x71e2/0x71ee`).

**Magnitude caveat (measured, so nobody wastes a playtest on it):** across Bahamut's 8 clips the root
translation track spans only **7–246 units** per axis (`m5_roottrans.py`). So the composition correction
is real but **small** — it does *not* explain a 40,000-unit staging error. §8 does.

---

## 6. FRAME ADVANCE — confirmed, with the disk-format consequence

`DrawSummonModel@0x17740` (x86 `0x13ce0`), once per rendered frame:
```
frameCount = u16[motion+2]                       ; 0x177c1  (x86 0x13dd4)
if (frameCount > rec.frame)      keep            ; 0x177cb jg
else if (loopFlag & 1)           rec.frame = 0   ; 0x177d4  LOOP
else                             rec.frame = frameCount-1   ; 0x177de  HOLD-last
... pose at rec.frame ...        ; 0x1786e
rec.frame += 1                   ; 0x17888 inc word[rdi+0x54]   (x86 0x13e33)
return rec.frame_before_increment ; eax = ebp @0x179e5
```
`loopFlag` is the 5th argument (stack, bit 0). Full signature, from the validator `0x17710`:
**`Hi_DrawSummonModel(SVECTOR* rot, VECTOR* pos, VECTOR* scale, int summonIdx, int loopFlag)`**
(`0x17716 movsxd rax,r9d` = idx; body `0x1774f-0x1775a` shuffles rot/pos/scale into pose_eval `0x186a0`).
`Hi_SetSummonMotion@0x17a10` binds a clip and zeroes `rec+0x54`; `Hi_SetSummonMotFrame@0x17a70` is a seek
that rewinds to 0 on an out-of-range target.

**Consequences for a format spec:** there is no timestep, no playback rate, no blending, no per-clip loop
flag on disk. Speed is "one clip frame per rendered frame"; loop-vs-hold is a **`.seq` command operand**,
not clip data. A 30 fps clip cannot be authored to play at half speed except by duplicating samples.

---

## 7. DO EFF-MODELS SHARE THIS? — **NO. They are rigid. (EFFARR hypothesis REFUTED.)**

1. **No motion, ever.** All five registrars null the motion pointer before initialising the DATA block:
   `Hi_RegisterSolidEffModel@0x15ac0 : 0x15b17` · `Gou@0x15b70 : 0x15bcb` · `Tex@0x15c20 : 0x15caf` ·
   `TexList@0x15d30 : 0x15d9d` · `TexPtr@0x15e10 : 0x15e7c` — each `mov qword[data+0x10], <zeroed reg>`,
   then `call 0x7120`. With `DATA+0x10 == 0`, branch M is unreachable for an eff model.
2. **No API to bind one.** The DLL's leftover debug-string roster (`refkit.py --list-strings Hi_`, 32
   entries at `0x4b090..0x4b628`) contains `Hi_SetSummonMotion` / `Hi_SetSummonMotFrame` and **no
   `Hi_Set*EffModel*Motion`**. Motion binding exists only for the summon slot.
3. **Eff models hang OFF the creature.** `Hi_DrawEffModelByBone` resolves the **summon** array
   (`0x168ea: lea rcx,[rip+0x209f3f] -> 0x220830`; `imul rax,rsi,0x58`; active `+0x50`; `rax = DATA[0x38]`)
   and copies `summonBones[boneIdx]` (32 B, `movups` pair `0x1691b-0x16928`) straight into the
   **eff-model's** `DATA+0x40` — i.e. an eff model's root IS a summon bone's world matrix.
4. **Corroboration from the interpreter**: the `.seq` mega-interpreter calls
   `Hi_GetSummonBoneMatrix@0x18630` (from `0x1195a`) and `Hi_GetSummonBonePos@0x185b0` (from `0x115cb`)
   during a cast — the effect program is *querying the creature's skeleton* to place sub-effects.
5. **Data corroboration**: `ef227` (Bahamut) contains 8 clips × 93 bones; `ef000` (non-summon) contains
   none.

**So the 32-slot × 0x30 EFFARR is the effect-prop array (beams, rings, sparks, sub-effects), each rigid
and often parented to one of the creature's 93 bones. The creature body is the single summon slot.**
A tracking probe should read the summon slot — but read `+0x38`, not `+0x40` (§5, §9).

---

## 8. THE s52 ROOT PROBE — the data is CORRECT; the READING was wrong

I re-analysed the existing capture (`<game>/sfxmeshprobe.log`, 2,045 `ROOT` rows over frames 50–561 of a
real `effectId=227` cast; `m5_rootstats.py`, `m5_scale.py`).

**Finding A — the rows are not duplicated-with-disagreement.** 512 distinct frames, 3–4 identical rows
each (the probe fires per `Render()` call). **Zero intra-frame disagreements** ⇒ `Hi_DrawSummonModel` runs
**once** per frame; the "last Draw wins" worry is refuted.

**Finding B — `SummonData+0x40` is `R · S`, not `R`.** Column norms are not 1.0: they run 0.02 → 3.00.
`pose_eval@0x186a0` applies the Draw `scale` argument via `0x3b60` (`0x187ab`) and stashes the scale
triple at `DATA+0x78` (default `0x10001000` = 1.0, `0x187b5`). **`root_reproject.py:43` (`FIXED = 4096.0`)
and `:75` (`np.array(m)/FIXED` → "rotation") silently treat a matrix that is up to 3× (or 1/50×) scaled as
a rotation.** Heading (`atan2(R02,R22)`, `:88`) survives; **size does not**, and nothing downstream ever
learns the creature's authored scale.

**Finding C — the trajectory is coherent and matches the user's video description.** Segmenting the log by
(column-norm scale, translation):

| frames | scale | translation | reading |
|---|---|---|---|
| 50–81 | — (all-zero) | — | summon registered, **not yet drawn** |
| 82–115 | **1.50** | `(-1224,-4096,0)` → `(-335,+4092,+82)` | **phase 1 — flying down, Y sweeps −4096→+4092** |
| 116–127 | 1.48 → **0.50** | Y `+4510` → `+16384` | recede (shrink + rise) |
| 128–144 | **0.02 → 0.25** | `(0,−7168,3072)` → `(0,−6656,2901)` | re-enter far away, growing from nothing |
| 145–152 | 0.48 → **2.10** | Y `−6181`→`−2856`, Z `2743`→`1634` | rushing in |
| **153–177** | **3.00** | Z `+23808` → **`−49152`** | **phase 2 — THE FLY-BY, 73 k units of Z in 25 frames** |
| 178–300 | **1.00** | Y `−8576`→`−23567`, Z `21248`→`15878` | settle |
| **301–561** | **1.50** | **constant `(0,−12288,−7168)` for 261 frames** | **phase 3+4 — hovers and charges; the camera does the work** |

The "≈40,000 units below/behind the camera" that motivated this round is the **fly-by** (`Z = −49152`,
25 frames), not the charge. At the charge the creature is **stationary for 47 % of the cast** — exactly
what the user described. **The prior verdict "the logged trajectory does not match where the creature
visibly is" does not survive this segmentation.**

**Finding D — but naive reprojection still fails, and I can prove it.** Projecting the logged root
translation through the same frame's logged `VIEW·PROJ` and correlating against the harvested body-mesh
screen centroid gives |r| ≤ 0.24 for **all eight** sign conventions (`m5_corr.py`, 323 frames). So
"root translation → screen position" is **not** a usable identity as currently computed. Three candidate
causes, in order of my confidence, all cheap to settle:
1. **Scale is missing from the world→screen mapping** and from any puppet sizing (Finding B). At
   `S = 3.0` the creature's *rendered* extent is 3× its model extent while its root point is unchanged —
   a centroid comparison is then dominated by scale, not position.
2. **The comparison target is wrong**: `MESH cx,cy` is a harvested-primitive centroid over one blend
   key, not the creature's centre; body-key selection is by row count, not by identity.
3. **The root point is not the creature's visual centre** — it is node 0 of a 93-bone skeleton whose
   parts are pushed out along bone lengths (§4). `bone[0]` ≠ silhouette centre.

---

## 9. WHAT TO CHANGE — concrete, falsifiable next steps

1. **Log `SummonData+0x38` bone matrices, not just `+0x40`.** One `Marshal.ReadIntPtr(data+0x38)` plus
   `k*0x20` reads gives the *actual* per-frame world pose the renderer uses (§5). Log `bone[0]` and a
   handful of extremities; offline, the bone cloud's centroid/extents ARE the creature's true framing
   datum — that is the thing FLIGHT has never had. Node count for Bahamut is **93** (§3), so a fixed
   `k < 93` loop is safe for this effect; the general value is `u8[model+0x02]`.
2. **Log `rec+0x54` (the motion frame counter) and `DATA+0x78` (the scale triple).** Two extra ints.
   The frame counter proves the summon model is being drawn and tells you *which clip frame* is on
   screen (letting the offline decode of §2 reproduce the pose without any probe at all); the scale is
   the missing term in Finding B.
3. **Fix `root_reproject.py`:** decompose `SummonData+0x40` as `R·S` — `s = column norms / 4096`,
   `R = M / (4096·s)` — and carry `s` into any puppet transform. Today the file's `FIXED = 4096.0`
   comment ("the root MATRIX rotation scale") is factually wrong.
4. **Stop treating the eff-model array as a tracking candidate** (§7) — but DO treat it as the place a
   Thomas-swap prop should be *registered*, since `Hi_DrawEffModelByBone` already parents an eff model to
   any summon bone with zero new machinery.
5. **Offline-first opportunity:** with §2+§4 decoded, the entire Bahamut skeleton animation is now
   computable offline from `ef227.bytes` **without the game running** — modulo the `.seq`-authored
   `(rot,pos,scale)` Draw args, which remain the only runtime term. Pairing the offline clip decode with
   a 3-int-per-frame probe (frame counter + scale) reconstructs every bone, every frame, exactly.

---

## 10. RE-AUTHORABILITY — verdict

**Yes, with one caveat.** A `Motion` is emitable from any DCC clip by a straightforward exporter:

| what the emitter must produce | source | difficulty |
|---|---|---|
| `frameCount`, header flags | clip length; whether a root axis is static | trivial |
| root translation: 3 constants or 3 × `s16[frameCount]` | root bone world translation, sampled per frame | trivial |
| per node, per axis: 8-bit coarse + 4-bit fine track (or a literal) | Euler-decompose the node's LOCAL rotation into the engine's `RotMatrix` order (`0x37a0`,`0x3850`,`0x3910`), quantise to 12 bits, split hi8/lo4 | easy; the only real work is matching the Euler order |
| all offsets motion-relative, `rotKeyOff < 0x10000`, `fineKeyOff < 0x100000` | layout | trivial (caps clip size) |
| 4-byte alignment between clips; a motion pointer table | container | trivial |

**Caveats and hard limits:**
- **The clip cannot define the skeleton.** `nodeCount`, parenting and bone lengths live in the MODEL
  (§4); a clip is only valid against the model it was authored for, and **a parent index must be lower
  than its child's index**.
- **A bone's local translation is a single scalar length along local Z.** No per-frame translation for
  anything but the root, and no non-uniform bone offsets. A DCC rig with arbitrary bone offsets must be
  pre-conformed to this constraint (or the offset baked into the parent's rotation, which cannot fully
  represent it).
- **No interpolation, no scale/shear channels, no blending.** One sample per rendered frame.
- `fineKeyOff = 0` is legal and drops precision to 8 bits (256 steps per turn); every real Bahamut clip
  carries the fine stream.
- Clip size is capped by the `< 0x10000` bound on `rotKeyOff` (the coarse key table must start inside the
  first 64 KB of the clip) — in practice a non-issue since it is at `+0x14`.
- **Not decoded here:** the model/geometry blob itself (mesh table stride `0x28` at `u32[model+0x10]`,
  §4 — that is B3/A4 territory), and `Motion+0x00`.

---

## 11. Cite index

**x64 DLL.** node builder `0x7820..0x83c7` (branch dispatch `0x7846`/`0x784f`/`0x7856`; bones store
`0x7842`; motion reloc-decode `0x7a5a-0x7b9b`; nodeCount `0x7aba`; local-XY zero `0x7abf`; root
translation `0x7b9e-0x7c1a`; rotation decode `0x7c40-0x7cae`; fine stream `0x7cb7-0x7d53`; identity seed
`0x7d5a-0x7d77`; RotMatrix chain `0x7d8a/0x7d9a/0x7daa`; node stride `0x7daf`; branch P `0x7de7-0x7ed7`;
branch R (rigid) `0x797a-0x7a0f`; root compose `0x7edc-0x80a6`; node table `0x813e`, parent byte
`0x81aa`, length `0x8282`, entry stride `0x8326`, loop `0x81c0-0x83a8`).
`DrawSummonModel` validator `0x17710`, body `0x17740` (motion reloc `0x17785-0x177b4`; clamp
`0x177c1-0x177de`; arena resolve `0x177e2-0x17868`; pose call `0x1786e`; arena commit `0x17873-0x17885`;
advance `0x17888`; meshCount `0x17900`; hide-mask `bt` `0x17916`).
`pose_eval 0x186a0` (scale `0x187ab`, default `0x187b5`). `SetSummonMotion 0x17a10`,
`SetSummonMotFrame 0x17a70`. `RegisterSummonModel 0x15ee0` (initial motion `0x15fc6`).
`Register*EffModel` motion-null: `0x15b17`/`0x15bcb`/`0x15caf`/`0x15d9d`/`0x15e7c`.
`DrawEffModelByBone` summon-array read `0x168ea-0x16928`. Mesh prep `0x4eb0` (mesh table `0x4f58`,
stride `0x4fd8-0x4fe8`). GTE helpers: RotTrans `0x3d60` (T-add `0x3dc5`/`0x3df2`), rotate-only `0x40d0`,
column mult `0x41e0`, scale `0x3b60`, RotMatrix `0x37a0`/`0x3850`/`0x3910`. Scratch globals
`0x211f40..0x211f5c` (matrix+T), `0x211fc0/c4` (in-vector), `0x211fe4/e8/ec` (out-vector),
`0x212040/42/44` (angles), `0x212048/4c/50/54` (local translation).

**x86 DLL (independent re-derivation).** node builder `0x70c0` (bones `0x70e0`, branch `0x70e3`;
nodeCount `0x72a5`; local-XY zero `0x72a9`/`0x72b3`; root translation `0x72da-0x7337`; rotation decode
`0x735c-0x7412`; nibble stream `0x743f-0x752e`; branch R `0x71fa-`; branch P `0x70eb-0x71f9`; root
compose `0x7843-`; node table `0x79e3`, parent `0x79e3`/`0x7b94`, length `0x7aba/0x7abd`, stride
`0x7b28`). `DrawSummonModel 0x13ce0` (reloc encoder `0x13d2d-0x13dcc`, clamp `0x13dd4-0x13ded`, pose call
`0x13e10`, advance `0x13e33`). DATA offsets: motion `+0x0c`, parent `+0x1c`, bones `+0x20`, root `+0x24`,
offset vec `+0x74/+0x78`.

**C#.** `Memoria/Data/Battle/SpecialEffect.cs:99` (`Bahamut__Full = 227`);
`Memoria/Battle/SFX/SFXData.cs:1339-1371` (`FixedCameraEffects`);
`studies/custom-summons/thomas-swap/root_reproject.py:43,75,88` (the scale defect).

**Tools added by this slice** (all in `disasm/`): `m5_dump.py`, `m5_fn.py`, `m5_fns_near.py`,
`m5_rip.py`, `m5_ripins.py`, `m5_callers.py`, `m5_x86.py`, `m5_motion_scan.py`, `m5_motion_verify.py`,
`m5_chain.py`, `m5_findtable.py`, `m5_stats.py`, `m5_roottrans.py`, `m5_peek.py`, `m5_rootstats.py`,
`m5_scale.py`, `m5_corr.py`, `m5_delta.py`, `m5_project_check.py`.
