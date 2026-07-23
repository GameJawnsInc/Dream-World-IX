# V-M1-07 — adversarial verification: "the probe fix is one dereference deeper (`SummonData+0x38` → `bones[0]`)"

**Claim under test (M1-07, source `M1-effmodel-array.md` §6.2/§10).**
`bones = ReadInt64(SummonData+0x38)`; read the 32-byte MATRIX at `bones[0]` (rot 9× Int16 fp12
`+0x00..+0x11`, translation 3× Int32 `+0x14/+0x18/+0x1c`). The pointer is re-assigned every Draw into the
packet/scratch bump allocator ⇒ never cache it; log **bone 0 only**.

**VERDICT: CONFIRMED.** Every load-bearing sub-claim reproduced from a fresh disassembly of the user's own
`FF9SpecialEffectPlugin.dll` (x64, `ImageBase 0x180000000`; all RVAs image-base-relative). Both stated
refutation conditions were tested directly and **both fail** — i.e. neither refutes.

Helpers added (committable: read the user's own DLL, print RVAs/mnemonics only, write nothing):
`v_m107_a.py` … `v_m107_l.py`.

---

## 0. Scorecard

| sub-claim | verdict | strongest independent evidence |
|---|---|---|
| `DATA+0x38` is written every Draw by the world-matrix builder | **CONFIRMED** | `build_world_matrices@0x7820`, `mov qword ptr [rcx+0x38], r8` @**`0x7842`** — the 4th instruction after the prologue, before any branch |
| `r8` is the packet/scratch **bump-allocator cursor** from `[[0x66c68]+0x24]` | **CONFIRMED** (stronger than cited) | `Hi_DrawSummonModel`: `mov rax,[rip+0x4f47f]` @`0x177e2` → **`0x66c68`**; `mov ecx,[rax+0x24]` @`0x177f4`; PSX→host decode; `call 0x7820` @`0x1786e`; then the **return value is converted back and stored to the same global**: `call 0x12940` @`0x17879`, `mov rcx,[rip+0x4f3e3]` (=`0x66c68`) @`0x1787e`, `mov dword[rcx+0x24],eax` @`0x17885`. That write-back is what makes it a *bump* allocator, and it was not in the cited evidence. |
| bone stride `0x20` | **CONFIRMED** (5 independent forms) | `shl rcx,5` @`0x16917` (cited, reproduced); `shl rax,5` @`0x7c21` on `boneCount`; `add r15,0x20` @`0x7daf`; `shl rdi,5` @`0x81b2`; `add rsi,0x20` @`0x838e` |
| translation = 3× **Int32** @ `+0x14/+0x18/+0x1c` | **CONFIRMED** | rigid path `mov eax,[rsi+0x54] → mov [rcx+0x14],eax` @`0x79f4`/`0x79fb`; `+0x58→+0x18` @`0x79fe`/`0x7a05`; `+0x5c→+0x1c` @`0x7a08`/`0x7a0f`. Motion path writes the same three dwords @`0x7bb2`/`0x7bdc`/`0x7c01` (const) or `0x7bcc`/`0x7bf1`/`0x7c16` (per-frame track), and the GTE fold rewrites them as dwords @`0x8092`/`0x809c`/`0x80a6`. |
| rotation = 9× **Int16 fp12** @ `+0x00..+0x11` | **CONFIRMED** | rigid path writes exactly 9 `word` stores at `+0x00,+0x02,+0x04,+0x06,+0x08,+0x0a,+0x0c,+0x0e,+0x10` (`0x797e`–`0x79f0`). fp12 proven by the identity seed in the bone loop: `mov dword[r15-8],0x1000` @`0x7d6a`, `mov dword[r15-2],0x10000000` @`0x7d62`, `mov dword[r15+6],0x10000000` @`0x7d5a` ⇒ `diag(4096,4096,4096)`. |
| matrix size 32 B (one bone) | **CONFIRMED** | rigid path returns `lea rax,[r13+0x20]` @`0x7a12` |
| **bone 0 is the model root** | **CONFIRMED** (3 independent ways, §3) | motion root track → `[r13+0x14/+0x18/+0x1c]` with `r13` = the *base* cursor; the pose root is folded into `r13` **only**; the hierarchy loop starts at `r13+0x20` (bone 1) |
| pointer must never be cached | **CONFIRMED, and reinforced** | it is NULL at Register (`0x71f7`), re-pointed every Draw (`0x7842`), and the underlying buffer is **reset to its base at the top of every `SFX_Update`** (`0x1459`, §4) — so a cached pointer's *contents* are overwritten by the next native frame |
| "read it in `Render()` after the native tick" | **CONFIRMED** by call-order, not merely asserted | `SFXDataMesh.cs:612 Load(frame)` (→ `SFX_Update`, which resets + draws) → `:618 SFX_LateUpdate` → `:619 SFXRender.Update` → `:653 LogSummonRoot()`; the next reset is the next managed `Render()`. §4.2 |
| logging the whole bone array = stock animation ⇒ BLOCKED | **CONFIRMED as policy** (not a binary fact) | `bones[1..n-1]` are per-frame **world** matrices for every bone; over a cast that is the creature's skeletal animation in derived form. Judgment, consistent with FINDINGS §3.3. |

---

## 1. Refutation condition 1 — "`DATA+0x38` points to a per-model persistent allocation"

**TESTED DIRECTLY AND FAILS.** I swept the *entire* image for any store into `[reg+0x38]` on a non-`rsp`
register (`v_m107_i.py`, `v_m107_j.py` — `mov`/`movups`/`movdqu`/`movaps`, per-function disassembly off
`.pdata` so it cannot desync). **Exactly four hits in 646 functions:**

| rva | fn | instruction | what it is |
|---|---|---|---|
| `0x71f7` | `model_prepare@0x7120` | `mov qword[rcx+0x38], rbp` | **`rbp = 0`** (`xor ebp,ebp` @`0x7134`) — a **NULL initialiser**, in the same zeroing block as `+0x18`, `+0x30`, `+0x60`, `+0x70`, `+0x80`, `+0x88` (`0x71d9`–`0x721a`). Called by all five `Register*EffModel` and by `Hi_RegisterSummonModel`. |
| `0x7842` | `build_world_matrices@0x7820` | `mov qword[rcx+0x38], r8` | **the only non-zero writer in the image** |
| `0x39ef7` | `0x39e10` | `mov qword[rbx+0x38], rdi` | `rdi = 0`; part of a generic 4-qword zeroing run `+0x30/+0x38/+0x40/+0x48` (`0x39ef3`–`0x39eff`) on an unrelated struct — not ModelData (ModelData `+0x40` is the pose MATRIX and is never zeroed as a qword here) |
| `0x49dec` | `0x49de3` | `mov qword[rbp+0x38], rcx` | an MSVC **C++ SEH exception filter** — `cmp dword[rax],0xe06d7363` @`0x49e03`. Irrelevant. |

⇒ There is **no persistent per-model bone allocation anywhere**. `DATA+0x38` is NULL from Register until
the first Draw, then holds this frame's packet-buffer slice. This is *stronger* than the original claim
stated, and it independently justifies the probe's `if (bones == IntPtr.Zero) return;` guard: a summon
model that is registered but has not yet been drawn will read NULL, not garbage.

---

## 2. Refutation condition 2 — "bone 0 is not the model root"

**TESTED AND FAILS.** Three independent mechanisms all designate `bones[0]` as the root.

**(a) The motion clip's root translation goes to `bones[0]`.** In `build_world_matrices`, `r13 = r8` (the
base cursor, set @`0x783c`). Before any bone loop runs:

```
0x7b9e  test byte[r14+0xa], 1            ; r14 = DATA+0x10 = the motion clip
0x7ba5  movsx eax, word[r14+4]           ; constant-X form
0x7bb2  mov dword[r13+0x14], eax         ; <-- bones[0].tx
0x7bb8  movzx eax, word[r14+4]           ; per-frame-track form
0x7bc5  add rax, r14
0x7bc8  movsx ecx, word[rax + rsi*2]     ; rsi = frameIdx
0x7bcc  mov dword[r13+0x14], ecx         ; <-- bones[0].tx
   ... identical shape: +6 -> [r13+0x18] (0x7bdc/0x7bf1), +8 -> [r13+0x1c] (0x7c01/0x7c16)
```

**(b) The pose root (`DATA+0x40..+0x5c`) is folded into `bones[0]` and nothing else.** After the bone
loop, `r13` is *restored to the base cursor* (`mov r13,[rsp+0x90]` @`0x7dd6`; it had been advanced to the
array end @`0x7c30`). Then `0x7edc`–`0x80a6` runs **once**, on `r13`:

```
0x7edc-0x7f04  DATA+0x40..+0x50 (9 rot words)  -> GTE rotation-register image
0x7f0a-0x7f1f  DATA+0x54/+0x58/+0x5c (dwords)  -> GTE TRX/TRY/TRZ
0x7f25/0x7fa2/0x7ffe  call 0x41e0  x3           ; R_root . R_bone0, column by column, in place at [r13]
0x8039-0x8065  bones[0].t as 4x s16 (V0)        ; note: word-truncated on GTE input (PSX SVECTOR)
0x8087         call 0x3d60                      ; RotTrans = R.V + TR
0x808c-0x80a6  results -> [r13+0x14/+0x18/+0x1c]
```

⇒ `bones[0] = ( R_anchor · R_bone0 , R_anchor · t_motionRoot[frame] + t_anchor )`.

**(c) The hierarchy propagation loop starts at bone 1 and never treats bone 0 as a child.**

```
0x81a6  lea rsi,[r13 + 0x20]             ; <-- starts at bones[1]
0x81aa  movzx edi, byte[rbp + 3]         ; per-bone record: parent index (rbp advances +4/iter, 0x8326)
0x81b2  shl rdi, 5
0x81b6  add rdi, r13                     ; parent = bones[parentIdx]
   ... R_parent . R_local (3x call 0x41e0), then RotTrans (call 0x3d60 @0x836a)
0x838e  add rsi, 0x20
0x83a5  cmp rsi, rax                     ; rax = [rsp+0x98] = r13 + boneCount*0x20
0x83a8  jb  0x81c0
```

Bone 0 is the only matrix that receives the root pose and the only one never composed against a parent.
**It is the root.**

*(Corroborating third party: `Hi_DrawEffModelByBone` @`0x16837` treats `SummonData->bones` as exactly this
array — `mov rax,[rax+0x38]` @`0x1690d`, `shl rcx,5` @`0x16917`, then a 32-byte `movups` pair into the eff
model's own root `[EffData+0x40]`/`[+0x50]` @`0x1691f`/`0x16928`. Two independent consumers, same layout.)*

---

## 3. The probe recipe's other constants — re-derived, all correct

`Hi_DrawSummonModel`'s real entry chunk is **`0x17710`** (the roster's `0x17740` is the *second* `.pdata`
chunk; `locate_function(pe,"Hi_DrawSummonModel")` returns **`0x179f2`**, the cold error funclet — the
documented trap, reproduced):

```
0x17710  push rdi
0x17716  movsxd rax, r9d                 ; summonModelIdx
0x1771c  imul rdi, rax, 0x58             ; STRIDE 0x58                       <- confirmed
0x17720  lea  rax,[rip + 0x209109]       ; next=0x17727 => BASE RVA 0x220830 <- confirmed
0x1772a  cmp  byte[rdi + 0x50], 0        ; ACTIVE @+0x50                     <- confirmed
0x1772e  je   0x1800179f2                ; (bail, not the HIRAISHI hang)
0x17734  mov  rcx, qword[rdi]            ; DATA @+0x00                       <- confirmed
0x17737  test rcx,rcx / je 0x179f2
```

So `SfxMeshProbe.LogSummonRoot()`'s existing `rec = base+0x220830`, `ReadByte(rec+0x50)`,
`ReadIntPtr(rec)` are all correct; the claim changes only the final step from `data+0x40` to
`ReadInt64(data+0x38)` → `bones[0]`.

Also reproduced in the same body, unchanged from prior artifacts: `pose_eval` call `0x17767`, motion
frameCount `movzx ecx, word[rax+2]` @`0x177c1`, the per-model frame counter `word[rec+0x54]`
(`0x177d4`/`0x177de`/`inc` @`0x17888`), and the hide mask `mov eax,[rcx+0x20]; bt eax,ebx` @`0x17913`.

---

## 4. Two findings the claim did NOT state, both of which strengthen it

### 4.1 The buffer is reset once per `SFX_Update` — so "never cache" is stronger than "the pointer moves"

Sweeping every function that references the GPU-context global `0x66c68` for writes to `[ctx+0x24]`
(`v_m107_l.py`) finds the cursor is **re-based to the packet-buffer origin inside `SFX_Update`**:

```
SFX_Update export 0x1d60 -> jmp 0x13a0 -> (chunk) 0x13c4
0x1443  mov rcx, rsi                      ; rsi = the PSX address-map table
0x1446  call 0x12940                      ; host -> PSX,  rdx = <global>+0x4074
0x144b  mov rcx, qword[rip+0x65816]       ; -> 0x66c68
0x1459  mov dword[rcx + 0x24], eax        ; <-- CURSOR RESET, every SFX_Update
```

(The only other write of `0` to that field, `0x312ba` in `fn 0x31060`, is reached from **`SFX_InitSystem`**
`0x1cf0 → jmp 0x2300 → call 0x31060 @0x24e8` — a one-time init, not a per-frame reset.)

⇒ A pointer cached across frames does not merely go stale; the memory it names is **re-used by the next
native frame's packets**. Never cache the pointer *or* the values.

### 4.2 The managed read window is provably inside the valid interval

`SFXDataMesh.cs`, `Runtime.Render()`: `Load(frame)` (line 612 → `SFX.SFX_Update`, lines 563/582/693 — the
reset + all `Hi_Draw*` calls) → `SFX_LateUpdate()` (618) → `SFXRender.Update()` (619, the
`SFX_BeginRender`/`SFX_GetPrim` harvest) → `SfxMeshProbe.LogSummonRoot()` (**653**). The next reset is the
next managed `Render()`. The claim's "read from `Render()` after the native tick" is therefore
**structurally correct, not merely plausible** — this is the one part of the claim I expected to come back
UNVERIFIABLE and it did not.

**Known sampling property (pre-existing, not a defect of the fix):** `Load()` can run `SFX_Update` in a
`while` loop (lines 576-582) when the managed frame outruns the native one, and skips it entirely when
`SFX.frameIndex == frame`. So a ROOT row samples the **last** native frame of that managed tick, and can
repeat a value when no native frame advanced. `MESH`/`CAM` rows already share this property, so joins on
`SFX.frameIndex` stay consistent. **Recommendation: also log `word[rec+0x54]`** (the native motion-frame
counter, `0x17888`) so the offline validator can tell a repeated row from a genuinely static frame.

---

## 5. Residuals and one falsifiable prediction the next round should carry

1. **NOT PROVEN (runtime-only): that this fix makes the trajectory match the video.** The claim is about
   *layout and lifetime*, and that is what I verified. What the composed value will be is now
   statically predictable, and it is worth stating as a falsifiable prediction:
   `bones[0].t = R_anchor · t_motionRoot[frame] + t_anchor`, where `t_motionRoot` is **s16 by
   construction** (`movsx ecx, word[rax+rsi*2]` @`0x7bc8`/`0x7bed`/`0x7c12`). During the frozen-anchor
   window (log frames 301-561, anchor `(0,−12288,−7168)`) the composed position can therefore differ from
   the anchor by **at most ±32767 per axis before the rotation scale**. If the creature visibly traverses
   more than that in the charge phase, `bones[0]` is *still* not the whole story and the next suspect is
   the `.seq` stream re-calling Draw with a new anchor at a cadence the probe is undersampling (§4.2).
2. **NOT PROVEN: `bones[0]` is the best *visual* tracking point.** It is the skeleton root, which for a
   long-necked flying dragon may sit well behind the visual mass. This is the M1 §12 caveat and it stands.
   The sanity gate (`PROJ·VIEW·bones[0].t` vs the `PRIM` centroid) remains mandatory before any flight is
   rebuilt on it.
3. **Convention hazard, reproduced and confirmed as real:** the **rigid** path negates matrix columns 1
   and 2 (`neg cx` on the stores to `+0x02,+0x04,+0x08,+0x0a,+0x0e,+0x10`, `0x798a`–`0x79ee`) — i.e.
   `M·diag(1,−1,−1)`. The **motion** path does not. A summon takes the motion path, so the reprojection
   must **not** apply that flip; if the result is mirrored in Y/Z this is the first thing to check.
4. **Note for whoever writes the C# (a real footgun):** the GTE translate input at `0x8039`–`0x8065` reads
   **four** words starting at `bones[0]+0x14` — the fourth (`+0x20`) is the *next bone's* first word, used
   as SVECTOR padding. That is native behaviour and harmless, but a probe must read the translation as
   **Int32 at `+0x14/+0x18/+0x1c`**, never as the s16 the GTE sees.

---

## 6. Provenance

Read-only static analysis of the user's own installed `FF9SpecialEffectPlugin.dll` (x64) plus read-only
inspection of the open-source Memoria C# tree. No DLL was modified, patched, or redistributed. No stock
geometry, animation, texture, or `ef###.bytes` content was extracted or written anywhere. `v_m107_a.py` …
`v_m107_l.py` are analysis code that reads the user's own DLL and prints RVAs/mnemonics only — committable.
