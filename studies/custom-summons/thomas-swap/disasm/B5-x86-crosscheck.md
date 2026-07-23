# B5 — x86 cross-check of the summon-model struct + accessors

**Verdict: FULL AGREEMENT.** The 32-bit build (`x86/FF9_Data/Plugins/FF9SpecialEffectPlugin.dll`,
348 KB, image base `0x10000000`, no `.pdata`) reproduces every structural claim of A1/A2 derived from
the x64 build. Every DIVERGENCE is explained by the pointer size dropping 8→4 (record stride, DATA
field offsets, one TexAnim struct member); every LOAD-BEARING invariant (array length, bone-matrix
layout, pose-eval seed, frame-advance logic, HideMeshes mask, the runtime-only nature of the values)
is **byte/opcode-identical in intent**. Confidence in A1/A2's core conclusion is now very high.

Independently re-derived here (not assumed from x64): the record stride, base, every field offset in
`SetSummonMotion`/`SetSummonMotFrame`/`GetSummonBonePos`/`GetSummonBoneMatrix`/`Show`/`Hide`/`Start`/
`Stop`TexAnim/`ModifyAbr`/`ModifyRGB`/`Register`, the pose evaluator, and the 3-site GetBoneMatrix
string pattern. Reproduce: `py b5_x86.py --fn <hex-rva-hint>` / `--ref <string-rva>` / `--dis rva:n`.

All x86 RVAs image-relative (base `0x10000000`; capstone prints `0x100xxxxx` = RVA `0xxxxxx`).
x86 locates functions by the SAME leftover error strings, referenced as absolute `push imm32`
(`imm == 0x10000000 + string_rva`) rather than x64's `lea reg,[rip+disp]`.

---

## 1. The record array — base, stride, LENGTH (all re-derived on x86)

| property | x64 (A2) | **x86 (B5)** | Δ | agree? |
|---|---|---|---|---|
| record base RVA | `0x220830` | **`0x20869c`** | (different image) | ✓ same role |
| stride | `0x58` | **`0x54`** | −4 | ✓ = one 8→4 ptr (the `data` field) |
| array LENGTH | 1 | **1** | 0 | ✓ IDENTICAL bound |
| base zero-on-disk? | yes (bss) | **yes** (RVA `0x20869c` ≥ `.data` rawEnd `0x51400`) | — | ✓ values runtime-only both arches |
| DBGCTX (err ctx) | `0x220890` (base+0x60) | **`0x2086f0`** (base+0x54 = base+stride) | — | ✓ sits just past the 1 record |

* **base + stride** — `RegisterSummonModel@0x13080`: `mov esi,0x1020869c` @`0x13097`; slot loop
  `cmp byte[esi+0x4c],0; je found; inc eax; add esi,0x54; cmp eax,1; jl loop; jmp err`
  (`0x130a3`–`0x130b5`). The bound constant **1** (`cmp eax,1; jl` @`0x130b0`) is byte-identical to
  x64's (`cmp eax,1; jl` @`0x15f14`) → **only slot 0 is ever allocated in either build.**
* Every accessor computes `imul idx,0x54; add 0x1020869c` (x86) vs `imul idx,0x58; add 0x220830` (x64).
* DBGCTX every error stub pushes = `0x102086f0` (RVA `0x2086f0`) = base + one stride → the length-1
  array plus the debug context, exactly as x64 lays it out (base + array + ctx).

### SummonRec offset map (x64 → x86, all shifts = −4 = the one leading `data*`)
| field | x64 | **x86** | evidence (x86) |
|---|---|---|---|
| `data` ptr | +0x00 | **+0x00** | `mov e/rdx,[rec]; test; je err` everywhere |
| `active` u8 | +0x50 | **+0x4c** | `cmp byte[rec+0x4c],0` in every accessor; set `@0x130c3` |
| flag2 u8 | +0x51? | **+0x4d** | Register `setne al; mov [esi+0x4d],al` @`0x130f2` |
| `frame` u16 | +0x54 | **+0x50** | SetMotion zeros `word[rec+0x50]` @`0x13f5c`; Draw inc @`0x13e33` |

---

## 2. The DATA block — offsets shift by −4×(pointers before the field)

The negative shift grows **monotonically** with offset — the signature of pure pointer-size shrinkage,
strong internal-consistency evidence that both builds compiled the same struct.

| DATA field | x64 | **x86** | Δ | evidence (x86 fn@rva) |
|---|---|---|---|---|
| `modelId` u32 | +0x08 | **+0x08** | 0 | Register `mov eax,[arg+0x3c]; mov [data+8],eax` @`0x130cf` |
| `motion` ptr | +0x10 | **+0x0c** | −4 | SetMotion `mov [data+0xc],arg` @`0x13f63`; MotFrame reads @`0x13fab`; Draw @`0x13d24` |
| `hideMask` u32 | +0x20 | **+0x14** | −0xc | Show `and [data+0x14],~bit` @`0x14756`; Hide `or [data+0x14],bit` @`0x147a4`; Draw skips hidden @`0x13e6b` |
| `bones` ptr | +0x38 | **+0x20** | −0x18 | GetBonePos `mov e/rax,[data+0x20]` @`0x1454b`; GetBoneMatrix @`0x145bd` |
| `root` MATRIX | +0x40 | **+0x24** | −0x1c | pose-eval `lea esi,[data+0x24]` @`0x14610` |
| `texAnim` ptr | +0x70 | **+0x50** | −0x20 | Start `mov eax,[data+0x50]` @`0x147f6`; Stop @`0x14860` |

---

## 3. PSX MATRIX + Motion sub-block — IDENTICAL (no pointers → no shift)

* **Bone-matrix stride `0x20`**: GetBonePos `shl edx,5` @`0x14554`; GetBoneMatrix `shl eax,5` @`0x145c0`
  — same as x64 (`shl 5`). PSX GTE `MATRIX` is a fixed 32-byte struct, arch-independent.
* **Translation @ +0x14/+0x18/+0x1c** within each MATRIX: GetBonePos reads `word[bone+0x14]`,
  `word[bone+0x18]`, `word[bone+0x1c]` (@`0x14557`/`0x14562`/`0x1456f`) → 3×s16 out. Byte-identical
  offsets to x64 (`0x185de`/`0x185eb`/`0x185f9`).
* **Full-matrix copy** — `Hi_GetSummonBoneMatrix` real getter @**`0x145a0`** copies 32 bytes with two
  16-byte moves: `movdqu xmm0,[bone]; movdqu [out],xmm0; movdqu xmm0,[bone+0x10]; movdqu [out+0x10],xmm0`
  (`0x145c8`–`0x145d5`). x64 used two `movups` — same 2×16 B copy, different SSE mnemonic (SSE2 vs
  the AVX-era encoder). **This is the true per-frame transform getter; same shape both builds.**
* **Motion frameCount @ +0x02**: MotFrame `movzx e/ax,word[motion+2]` @`0x13fb1`; Draw @`0x13dd4`.
  Identical to x64 (`word[motion+2]`).

---

## 4. Pose evaluator (root world transform) — the round's core finding, CONFIRMED on x86

x86 `pose_eval@0x14600` (x64 `@0x186a0`), called by DrawSummonModel @`0x13d15` (`call 0x14600`):

* Works on `DATA+0x24` (= root): `lea esi,[edi+0x24]` @`0x14610` (x64 `lea rbx,[rcx+0x40]`).
* **Seeds the identical fixed default matrix**: `mov ebx,0x1000` then `[root]=0x1000`,
  `[root+6]=0x10000000`, `[root+0xe]=0x10000000` (`0x14617`–`0x1462c`). x64: `[rbx]=0x1000`,
  `[rbx+6]=[rbx+0xe]=0x10000000` — **byte-identical seed constants** (1.0 in 1/4096 fixed + the two
  0x10000000 diag terms).
* **Rotation from the `rot` arg**: `movsx ecx,word[rot+4/…]` then the PSX RotMatrix XYZ chain
  `call 0x3500 (X) → 0x33a0 (Y) → 0x3450 (Z)` (`0x1463f`/`0x1464d`/`0x14677`), composing the 3×3 into
  `root+0x00…`. (x64: `0x3910/0x37a0/0x3850`.) Same three-call rotation build.
* **Translation from the `pos` arg**: `mov eax,[pos]; mov [root+0x14],eax` … `[pos+4]→[root+0x18]`,
  `[pos+8]→[root+0x1c]` (`0x14683`–`0x14691`). Translation lands at root+0x14/+0x18/+0x1c — same
  in-matrix offset as x64.

**⇒ A2 §5 is confirmed on x86:** the creature's per-frame **root** transform is *recomputed every
Draw* from the `(rot,pos)` arguments the managed SFX/camera code hands `Hi_DrawSummonModel`; it is NOT
persisted in the struct between frames. The per-bone locals (`DATA+0x20[]`) are sampled from the motion
clip at `rec+0x50`. Both inputs are runtime scratch (base zero-on-disk, §1) → no static/data-side
method recovers the VALUES on either build; the sanctioned runtime read is
`Hi_GetSummonBoneMatrix(0, boneIdx, &out)` per frame, or a Draw-arg `(rot,pos)` probe. Identical
conclusion across both architectures.

---

## 5. Remaining accessors — all agree

| fn | x86 body | key op (x86) | vs x64 | agree |
|---|---|---|---|---|
| SetSummonMotion | `0x13f40` | `[data+0xc]=motion`, `word[rec+0x50]=0` | +0x10/+0x54 | ✓ |
| SetSummonMotFrame | `0x13f90` | clamp `frameCount` vs req; `word[rec+0x50]=req|0` | same logic | ✓ |
| DrawSummonModel | `0x13ce0` | motion+0xc, frame+0x50, loopflag `[ebp+0x18]&1`, hidemask+0x14 | same frame-advance + hide-skip | ✓ |
| ShowSummonModelMesh | `0x14730` | `and [data+0x14],~(1<<n)` | +0x20 | ✓ |
| HideSummonModelMesh | `0x14780` | `or [data+0x14],(1<<n)` | +0x20 | ✓ (HideMeshes mask, same op) |
| StartSummonTexAnim | `0x147d0` | `or byte[tex+4],3|1`; `[tex+0xc]=0`; `word[tex+0x12]=0x1000` | tex+8/+0x10/+0x16 | ✓ (shift −4) |
| StopSummonTexAnim | `0x14840` | `and byte[tex+4],0xfc` | tex+8 | ✓ |
| ModifySummonModelAbr | `0x149d0` | `cmp arg,0xff; je noop`; `shl dx,5`; tail `jmp 0xb390` | 0xff sentinel; abr<<5; jmp 0x8c880 | ✓ |
| ModifySummonModelRGB | `0x14a20` | guards; `call 0x7be0; ret` | tail `jmp 0x83d0` | ✓ (call+ret vs tail-jmp; codegen only) |

* **TexAnim struct stride diverges 0x18→0x14**: Start/Stop index `[base + (idx*5)*4]` = idx*`0x14`
  (x64 stride `0x18`). Explained — the 24-byte x64 TexAnim contains one 8-byte pointer member that is
  4 bytes on x86 (24−4−… → 20). A genuine, *predicted* divergence, not a contradiction.

### The 3-site `Hi_GetSummonBoneMatrix` string pattern reproduces exactly
x86 has 3 `push 0x100370c8` sites — the SAME 1-getter-plus-2-consumers shape A1 found on x64
(`0x16c80/0x176ba/0x18678`):
* `0x145dd` → the **real getter** body `@0x145a0` (the 2×movdqu copy, §3).
* `0x13ca0` → **DrawSummonModel** body `@0x13ce0` (its own tail string is `Hi_DrawSummonModel`
  @`0x13f24`), which inlines a bone/pose fetch and reuses the GetBoneMatrix error string.
* `0x137ab` → an **eff-model bone-draw** body `@0x137e0` (operates on the separate EFFARR at
  `[idx*5*8 + 0x102081b8/0x1020819c]`, stride `0x28`), the x64 `DrawEffModelByBone`/`ByBone` analogue.

---

## 6. Divergence ledger (complete — every one is pointer-size, none contradicts A1/A2)

1. Record stride `0x58`→`0x54` (−4: the `data` ptr).
2. All DATA pointer-following offsets shift −4×(ptrs-before): motion −4, hideMask −0xc, bones −0x18,
   root −0x1c, texAnim −0x20 (monotone — the tell of a faithfully recompiled struct).
3. SummonRec `active`/`frame` shift −4 (past the leading ptr).
4. TexAnim struct stride `0x18`→`0x14` (its internal pointer member).
5. `movdqu` (x86 SSE2) vs `movups` (x64) for the 32-byte matrix copy — identical semantics.
6. ModifyRGB uses `call helper; ret` vs x64 tail-`jmp helper` — identical semantics.
7. String refs: `push imm32` (x86 absolute) vs `lea [rip+disp]` (x64) — different image model, same
   error-diagnostic pattern (the locate-by-error-string method works identically).

**No structural divergence.** Array length, the length-1 bound constant, the bone-matrix layout, the
pose-eval seed constants + RotMatrix chain, the frame-advance loop/hold branch, the HideMeshes bit ops,
and the runtime-only (zero-on-disk) nature of every value are all identical across builds.

---

## 7. x86 quick-reference (bodies + globals)

```
record base RVA   0x20869c   stride 0x54   length 1   (bss, zero on disk)
DBGCTX            0x2086f0   printf import [0x36084]   panic 0x12650
Register          0x13080    SetMotion       0x13f40   SetMotFrame     0x13f90
DrawSummonModel   0x13ce0    pose_eval       0x14600   GetBonePos      0x14530
GetBoneMatrix     0x145a0 (REAL getter)      Show            0x14730   Hide  0x14780
StartTexAnim      0x147d0    StopTexAnim     0x14840   ModifyAbr 0x149d0  ModifyRGB 0x14a20
EFFARR active/data  0x2081b8 / 0x20819c  (stride 0x28)
```

## 8. Provenance

Read-only static analysis of the user's installed 32-bit DLL (RVAs, mnemonics, struct offsets, and
the cross-arch comparison table only). No stock geometry/animation bytes extracted; no DLL modified.
The record base (`0x20869c`) is zero-on-disk scratch — runtime VALUES remain unknowable statically, as
stated for the x64 build. Helper: `b5_x86.py` (committable format-parser; reads the user's own DLL).
