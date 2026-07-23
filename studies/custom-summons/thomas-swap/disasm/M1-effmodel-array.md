# M1 — the EFF-MODEL family + the 32-slot EFFARR (`FF9SpecialEffectPlugin.dll`)

**Slice question:** is the summoned creature drawn through the 32-slot Eff-model array rather than the
single summon slot — i.e. was the s52 ROOT probe pointed at the *wrong subsystem*?

**VERDICT: NO. The leading hypothesis is REFUTED. The creature body cannot be an eff model, and the
summon slot is provably live and drawn during a real cast. The tracking failure is a WRONG-FIELD bug
inside the right subsystem, and this round located the right field.**

All RVAs image-base-relative (x64 `ImageBase 0x180000000`; x86 `0x10000000`). Every claim carries an
`fn@rva`. Runtime values are zero-on-disk `.bss`; only LAYOUT + LOGIC are static-recoverable.
Helpers added this slice (committable, read the user's own DLL, emit RVAs only):
`m1_roster.py`, `m1_effarr_xref.py`, `m1_callsites.py`, `m1_dispatch.py`.

---

## 0. HEADLINE — the three findings that matter

1. **An eff model is a RIGID, SINGLE-MATRIX model. It structurally cannot be an animated creature.**
   All five `Hi_Register*EffModel` bodies explicitly store `DATA+0x10 = 0` (the motion-clip pointer):
   `0x15b17`, `0x15bcb`, `0x15caf`, `0x15d9d`, `0x15e7c`. The world-matrix builder `@0x7820` branches on
   exactly that field (`test r14,r14; jne <motion path>` @`0x7846`/`0x7849`); with it NULL it emits **one**
   32-byte matrix and returns `cursor+0x20` (`0x797a`–`0x7a12`). No motion clip, no bone array, no
   per-mesh hide mask, no texanim. Bahamut's wings cannot be an eff model.
2. **`Hi_DrawEffModelByBone` is the child-attachment op: it copies `summonModels[i].data->bones[b]`
   verbatim into the eff model's root matrix** (`0x168ea`–`0x16928`). Eff models are *parented to the
   summon creature's skeleton* — they are its beams/glows/props, and they **require** an ACTIVE summon
   model to exist. That makes EFFARR a consumer of the summon slot, not a replacement for it.
3. **The creature's TRUE drawn world transform is NOT `SummonData+0x40`.** `+0x40` is the *anchor* the
   `.seq` stream passes to `Hi_DrawSummonModel` each frame. The matrix actually fed to the GTE is the
   composed one at **`*(MATRIX*)(SummonData+0x38)`** (bone 0), built every Draw by `@0x7820` as
   `root ∘ motionRootTrack[frame] ∘ boneChain` — the motion clip supplies the flight (`0x7ba5`–`0x7c16`),
   and the root is folded in through the GTE at `0x7edc`–`0x80a6`. **That is the field the s52 probe
   should read.** The existing log proves the point: the root FREEZES at `(0,−12288,−7168)` from frame
   ~301 to 561 while the creature is visibly flying/charging (§11).

---

## 1. The EFFARR — all four numbers independently verified

| property | value | evidence |
|---|---|---|
| base RVA (x64) | **`0x220230`** | `Hi_RegisterSolidEffModel@0x15ac0`: `lea rbx,[rip+0x20a75d]` @`0x15acc` (next=`0x15ad3`, +disp = `0x220230`). Same base re-derived independently in 20 other functions (`m1_effarr_xref.py`), e.g. `Hi_FreeEffModel@0x159ab`, `Hi_DrawEffModel@0x16160`, `Hi_SetEffModelSlice@0x18a9b`. |
| stride | **`0x30`** | two independent forms: `add rbx,0x30` in every Register slot-loop (`0x15add`, `0x15b8d`, `0x15c60`, `0x15d5d`, `0x15e3d`); and the index math `lea r8,[rax+rax*2]; add r8,r8; [base + r8*8]` = `idx*48` (`Hi_FreeEffModel@0x159a7`, `Hi_ModifyEffModelAbr@0x1899f`) / `lea rdi,[rax+rax*2]; shl rdi,4` (`Hi_DrawEffModel@0x1615c`). |
| slot count | **`0x20` = 32** | loop bound `cmp eax,0x20; jl` in all five Registers (`0x15ae1`, `0x15b91`, `0x15c64`, `0x15d61`, `0x15e41`) **and** in the initialiser `Hi_InitEffModel@0x1596f`. |
| active flag | **byte @+0x20** | `cmp byte ptr [rbx+0x20], dil` @`0x15ad5` (dil=0) — the gate in every accessor; set by `mov word ptr [rbx+0x20],1` @`0x15aed` (a 2-byte store that also clears `+0x21`); cleared by `Hi_FreeEffModel` `mov byte[rax+rdx*8+0x20],0` @`0x159c3`. |

**Structural corroboration (strong):** `0x220230 + 32×0x30 = 0x220830` — **exactly** the summon-model
array base (`Hi_RegisterSummonModel@0x15f01`). The two arrays are adjacent and the arithmetic closes to
the byte; a wrong stride or count would not land on it. The shared error context `DBGCTX @0x220890` sits
just past the summon record (`0x220830 + 0x58 = 0x220888`).

---

## 2. The 0x30-byte slot record — complete field map

```c
// EFFARR @ RVA 0x220230 (x64) — runtime .bss, ZERO on disk. 32 slots, stride 0x30.
struct EffSlot {                 // 0x30 bytes (0x2a used + alignment to the leading pointer)
/*+0x00*/ ModelData* data;       // -> the 0xC8-byte DATA block; assigned ONCE by Hi_InitEffModel.
                                 //    NULL here => every Register* hard-HANGS (see 3).
/*+0x08*/ u8         texInfo[24];// texture-binding record, 24 B. TexList copies it wholesale
                                 //    (movups+movsd @0x15da4-0x15daf). Tex mode uses only the
                                 //    first two u16: +0x08 = arg1(dx), +0x0a = arg2(r8w).
/*+0x20*/ u8         active;     // 1 = in use. THE gate byte.
/*+0x21*/ u8         sliceOn;    // set to 1 by Hi_SetEffModelSlice@0x18ab6; cleared by the
                                 //    word-store at Register (0x15aed).
/*+0x22*/ u16        handle;     // == the slot INDEX. Written once by Hi_InitEffModel@0x15950
                                 //    (`mov word[rax],r8w` with r8d = loop counter) and RETURNED
                                 //    by every Register* (`movzx eax, word[rbx+0x22]` @0x15b23).
                                 //    => the ".seq" model handle IS the slot index 0..31.
/*+0x24*/ u16        shadeMode;  // 0 = Solid, 1 = Gouraud, 2 = Textured. Set by the Register variant.
/*+0x26*/ u16        drawOffset; // Hi_SetEffModelOffset@0x18a64 (`mov word[slot+0x26],dx`).
                                 //    Register clears it for free: `mov dword[rbx+0x24],<0|1|2>`
                                 //    is ONE store covering both u16s.
/*+0x28*/ u16        sliceValue; // Hi_SetEffModelSlice@0x18abb; zeroed by Register (0x15af3 etc.).
/*+0x2a*/ u8         pad[6];
};
```

Field-by-field consumers:

* `+0x24` **shadeMode** drives the per-mesh emit switch in `Hi_DrawEffModel@0x163a6`:
  `movzx ecx,word[rdi+0x24]; test ecx,ecx; je M0; dec ecx; je M1; dec ecx; jne SKIP`.
  Mode 0 **and** mode 2 fall to the emitter `call 0x56c0` (`0x16509`); mode 1 to `call 0x9150` with
  `r9d = 0` (`0x1644a`); modes > 2 emit nothing.
* `+0x26` **drawOffset**, when non-zero, *overrides* the mode switch — `movzx r9d,word[rdi+0x26];
  test r9w,r9w; je <mode switch>` @`0x162de` — and routes to `0x9150` with `r9d = offset` (`0x16330`).
* `+0x28`/`+0x21` **slice**: `Hi_DrawSliceEffModel` computes `word[DATA+0x7e] = word[arg1+4] − word[slot+0x28]`
  (`0x16678`–`0x16683`) — a per-frame clip scalar (dissolve/materialise plane).
* `Hi_ModifyEffModelAbr@0x18990` — `cmp edx,0xff; je noop` (`0x18997`), then `shl dx,5` and tail-jumps
  the shared per-mesh ABR helper `0x18000c880` (`0x189c6`). Identical 0xFF sentinel + `<<5` shape to the
  summon's `Hi_ModifySummonModelAbr`.
* `Hi_ModifyEffModelRGB@0x189f0` — tail-jumps the shared helper `0x83d0` (`0x18a21`).
* `Hi_FreeEffModel@0x159a0` — clears `active` ONLY (`0x159c3`). It never frees `data`; the slot's DATA
  block is permanent for the effect's lifetime.

---

## 3. The lifecycle — and the allocator that closes the "who fills `+0x00`?" hole

`Hi_InitEffModel` **@`0x15940`** (x64) — *this function has NO `.pdata` entry* (leaf, no prologue), so it
is invisible to `refkit.iter_instructions` / `xref_index`; it was found by walking back from
`Hi_FreeEffModel` and confirmed against its x86 twin. **Record this as a refkit caveat.**

```
Hi_InitEffModel(rcx = dataPoolBase, edx = count)
  rax = EFFARR + 0x22
  for i in 0..31:                            ; 0x15950-0x15973
      word[slot+0x22] = i                    ; handle := slot index
      byte[slot+0x20] = 0                    ; active := 0
      qword[slot+0x00] = 0                   ; data := NULL
      qword[slot+0x08] = qword[slot+0x10] = qword[slot+0x18] = 0   ; the 24-B texInfo
      slot += 0x30
  rax = EFFARR                               ; 0x15975
  for k in 0..count-1:                       ; 0x15982-0x15993
      qword[slot+0x00] = poolCursor
      poolCursor += 0xC8                     ; <<< sizeof(ModelData) == 0xC8 on x64
      slot += 0x30
```

* **Called from exactly one site: the mega-interpreter, `call 0x180015940` @`0xf8b8`.** The pool pointer
  comes from `call 0x12740(ctx,0)` @`0xf8a8` and the **count is a literal operand of the effect's own
  command stream** (`mov edx, dword[rbx + r13 + 0xcac]` @`0xf8ad`, `rbx = streamIndex<<7`). So an
  `ef###.bytes` blob *declares how many eff-model slots it wants*; slots ≥ count keep `data == NULL`.
* **A NULL `data` is fatal, not soft.** The `je` at `0x15aeb` lands on the error stub `0x15b4c`, which
  `printf`s into `DBGCTX 0x220890` and calls `0x151a0` — and `0x151a0` prints `"HIRAISHI ERROR:"`
  (`0x4b078`) and then **spins forever** (`0x151f0: cmp rcx,rdx … 0x151fd: jmp 0x151f0`). This is the
  native "memory not enough!" hang. It is therefore *provable that the pool op runs* in any cast that
  registers an eff model — the game does not hang.
* The summon side is symmetric but caller-owned: opcode body `@0x47330` builds a model descriptor in a
  caller buffer, sets `summonModels[0].data = descriptor + 0x90` (`lea rax,[rbp+0x90]` @`0x47423`,
  `mov [0x220830],rax` @`0x47449`), zeroes `0x220838..0x220883`, then `call Hi_RegisterSummonModel`
  (`0x47491`).

---

## 4. What distinguishes the five `Register*` variants — ONE field

All five are byte-for-byte the same function apart from the `shadeMode` constant and how texture info is
delivered:

| variant | real body | writes `[slot+0x24]` | texture delivery (args → `model_prepare@0x7120(data, texA, texB)`) |
|---|---|---|---|
| `Hi_RegisterSolidEffModel` | `0x15ac0` | `edi` = **0** (`0x15afd`) | `rdx = 0`, `r8 = 0` (`0x15b0c`/`0x15b0f`) — untextured flat |
| `Hi_RegisterGouEffModel` | `0x15b70` | **1** (`0x15bad`) | `rdx = 0`, `r8 = 0` — untextured Gouraud |
| `Hi_RegisterTexEffModel` | `0x15c20` | **2** (`0x15c87`) | 4 × u16 params: `word[slot+0x08]=dx`, `word[slot+0x0a]=r8w` (`0x15cb8`/`0x15cbb`); `r9d` + the 5th stack arg packed into a local pair passed as `r8` (`0x15caa`/`0x15cc2`) |
| `Hi_RegisterTexListModel` | `0x15d30` | **2** (`0x15d7d`) | copies a **24-byte** texture table from `rdx` into `slot+0x08..0x1f` (`movups`+`movsd`, `0x15da4`–`0x15daf`); `r8` = the caller's list pointer |
| `Hi_RegisterTexPtrModel` | `0x15e10` | **2** (`0x15e5d`) | passes the caller's two pointers straight through (`rdx=rsi`, `r8=rdi`, `0x15e70`/`0x15e73`) — indirect texture binding |

Common tail in all five: `[DATA+0x08] = PSX(modelBlob)` via `call 0x12940` (host→PSX address), then
`[DATA+0x10] = 0` (**no motion**), then `call 0x7120(DATA, texA, texB)`, then `return word[slot+0x22]`.

There is also a **blob-sniffing wrapper**, interpreter opcode body `@0x47290` (called at `0x121bc`):
it asserts the model blob's magic `word[blob+0] == 0x6F73` (`0x4729a`/`0x472a4`), ORs `(arg1 & 3) << 5`
(an ABR code) into every entry of a u16 table inside the blob (`0x472f0`–`0x47302`), then tail-jumps
`Hi_RegisterTexListModel` (`0x47316`) if `word[blob+2] != 0`, else `Hi_RegisterGouEffModel` (`0x47325`).

---

## 5. Q2 — geometry pointer and motion binding

| DATA field (x64) | meaning | evidence |
|---|---|---|
| `+0x08` u32 | **PSX-format address of the model-geometry blob** (not a "model id" — correct A2/FINDINGS here) | written by every Register (`mov [rcx+8],eax` @`0x15b11` after `call 0x12940`); read back and address-decoded in every Draw, then `movzx esi, byte[geom+3]` = **meshCount** (`Hi_DrawEffModel@0x162c5`, `Hi_DrawSummonModel@0x17900`) and `movzx r10d, byte[geom+2]` = **boneCount** (`0x7aba`) |
| `+0x10` ptr | **motion clip**; NULL ⇒ rigid | eff: forced `0` (`0x15b17` …); summon: set from `[modelDesc+0x180]` in `Hi_RegisterSummonModel`'s work body `0x1606c` (`mov [DATA+0x10],rcx` @`0x15fc6`), rebound by `Hi_SetSummonMotion@0x17a3b`. `frameCount = word[motion+2]` (`0x177c1`) |
| `+0x18` ptr | scratch; **cleared at the top of every Draw** | `mov qword[rax+0x18],0` @`0x16251` (eff), `0x16670` (slice), `0x1697e` (bybone), `0x1788f` (summon) |
| `+0x30` ptr | **parent model's DATA** (hierarchy link) | `0x7820`: `rax=[rcx+0x30]; je <no-parent>` @`0x784f`/`0x7856`; when set, the parent's `+0x38[byte[DATA+0x04]]` matrix is copied as this model's base (`0x785c`–`0x78cf`) |
| `+0x04` u8 | **the parent's bone index** for that link | `movzx edx, byte[rcx+4]; shl rdx,5` @`0x7860`/`0x7864` |
| `+0x38` ptr | **the per-frame WORLD-matrix array** (§6) | assigned every Draw: `mov [rcx+0x38], r8` @`0x7842` |
| `+0x40` MATRIX | the **pose/anchor** root (rot 3×3 s16 fp12 @+0x40, translation s32 @+0x54/+0x58/+0x5C) | `pose_eval@0x186b2`: `lea rbx,[rcx+0x40]` |
| `+0x78` s16×3 | scale (fp12) | `pose_eval@0x187b5`: `mov dword[rsi+0x78],0x10001000; mov word[rsi+0x7c],0x1000` when no scale arg |
| `+0x7e` u16 | slice/clip scalar | `Hi_DrawSliceEffModel@0x16683` |
| `+0xa0/+0xa4` s16×3 | pivot vector used in the parented branch (`t += R·pivot`) | `0x7904`/`0x7910` → GTE V0, `call 0x40d0`, `add dword[[DATA+0x38]+0x14], eax` @`0x795a` |
| size | **`0xC8`** (x64) / **`0x98`** (x86) | `add rcx,0xc8` @`0x15985`; x86 `add ecx,0x98` @`0x12c55` |

---

## 6. Q1 — where the per-frame world transform lives (THE TRACKING PRIZE)

There are **two** transforms, and the study has been reading the wrong one.

### 6.1 `DATA+0x40` — the pose ANCHOR (what s52 currently logs)

`pose_eval@0x186a0` (split body `0x186b8..0x187d7`) is called with `(rcx = DATA, rdx = rot*, r8 = trans*,
r9 = scale*)` and writes **only** `DATA+0x40`:

* seeds the identity in fp12 — `[rbx]=0x1000`, `[rbx+6]=[rbx+0xe]=0x10000000` (`0x186ca`–`0x186dc`);
* composes rotation from the `rot` SVECTOR via the classic PSX chain `0x3910 → 0x37a0 → 0x3850`
  (`0x186f6`/`0x18703`/`0x18729`), reading `word[rot+4]`, `word[rot+0]`, `word[rot+2]` in that order;
* copies the `trans` VECTOR verbatim into the matrix translation `[rbx+0x14/+0x18/+0x1c]`
  (`0x18738`–`0x18749`), zeroing it when the arg is NULL;
* multiplies in the scale matrix via `0x3b60` (`0x187ab`), or writes unit scale to `DATA+0x78`
  (`0x187b5`) and calls `0x5560`.

**Callers of `pose_eval` — exactly four:** `Hi_DrawEffModel@0x161a1`, `Hi_DrawSliceEffModel@0x165c0`,
`Hi_DrawMorphEffModel@0x16db4`, `Hi_DrawSummonModel@0x17767`. Both `*ByBone` variants do **not** call it.
So `DATA+0x40` is *only ever* the arguments the `.seq` stream passed to Draw this frame — a staging
anchor, nothing more.

### 6.2 `*(MATRIX*)(DATA+0x38)` — the COMPOSED world matrix actually fed to the GTE

`build_world_matrices@0x7820(rcx = DATA, dx = frameIdx, r8 = matrixScratch)`; called from **all six** Draw
bodies (`0x16234`, `0x16653`, `0x168d0`, `0x16e39`, `0x172fd`, `0x1786e`). `r8` is the PSX packet/scratch
bump cursor decoded from `[[0x66c68]+0x24]`; the function's return value becomes the advanced cursor.

* First act: `mov qword[rcx+0x38], r8` @`0x7842` — **`DATA+0x38` is (re)pointed at this frame's matrix
  block**, then the block is filled.
* **Rigid path** (motion NULL, parent NULL) — `0x797a`–`0x7a12`: one matrix. Rotation is
  `DATA+0x40`'s 3×3 with **columns 1 and 2 negated** (`neg cx` on the stores to `+0x02,+0x04,+0x08,
  +0x0a,+0x0e,+0x10`; `+0x00,+0x06,+0x0c` copied straight) — i.e. `M · diag(1,−1,−1)`. Translation copied
  **verbatim** from `DATA+0x54/+0x58/+0x5C`. Returns `cursor + 0x20` (exactly one MATRIX).
* **Parented path** (`DATA+0x30 != 0`) — `0x785c`–`0x795a`: copies the parent's bone matrix, then
  `translation += R · pivot(DATA+0xa0)`.
* **Motion path** (`DATA+0x10 != 0`, the summon) — `0x7a20` onward:
  * root translation comes from the **motion clip**, not from Draw: for each axis, `byte[motion+0xa]`
    bit 0/1/2 selects *constant* (`movsx eax, word[motion+4]` → `[out+0x14]`, `0x7ba5`/`0x7bb2`) versus
    *per-frame track* (`rax = motion + word[motion+4]; movsx ecx, word[rax + frame*2]` → `[out+0x14]`,
    `0x7bb8`–`0x7bcc`; same shape for Y at `+6`→`[out+0x18]` and Z at `+8`→`[out+0x1c]`).
  * `boneCount = byte[geom+2]`; the loop `0x7c40`–`0x7dba` decodes each bone's packed rotation nibbles
    at the current frame and builds a matrix per bone at `out + i*0x20`.
  * then, at `0x7edc`–`0x80a6`, **the pose root is folded in through the GTE**: `DATA+0x40..+0x5C`
    (rotation *and* translation) are loaded into the GTE register image `0x211f40..0x211f5c`, each
    rotation column of the bone matrix is transformed by `call 0x41e0`, and the bone's translation is
    pushed through `call 0x3d60` (rot+trans) with the result written back to `[out+0x14/+0x18/+0x1c]`
    (`0x8087`–`0x80a6`).

> **⇒ the creature's true per-frame world matrix is `bones[0]` at `*(MATRIX*)(DATA+0x38)`, whose
> translation `= rootR · motionRootTrack[frame] + rootT`.** `DATA+0x40` is one of the two inputs. The
> other input — the flight path — is the motion clip, and it never appears in `+0x40`.

This is a **correction to FINDINGS §3.1/B1**: `bones[0] == root == DATA+0x40` is false. `bones[0]` is the
*composed* transform; `DATA+0x40` is the pre-composition anchor. (`DATA+0x38` is a *pointer* the probe
must dereference, not an inline array.)

---

## 7. Q3 — "ByBone" means: parent an eff model to a SUMMON bone. Decisive.

`Hi_DrawEffModelByBone` — entry `0x167f0`, body `0x16837`, error stubs `0x16c80` (reuses the
`Hi_GetSummonBoneMatrix` string) / `0x16c9d`.
Signature: `(rcx = scale SVECTOR* | NULL, edx = effModelIdx, r8d = summonModelIdx, r9d = boneIdx)`.

```
0x168d0  call 0x7820(effData, 0, scratch)      ; build the eff model's own (rigid) matrix
0x168ea  lea  rcx,[rip+0x209f3f]               ; -> 0x220830  == the SUMMON array
0x168f1  imul rax, rsi, 0x58                   ; rsi = summonModelIdx, SUMMON stride 0x58
0x168f5  cmp  byte[rax+rcx+0x50], r14b         ; summon .active @+0x50 — else HIRAISHI hang
0x16900  mov  rax,[rax+rcx]                    ; SummonData*
0x1690d  mov  rax,[rax+0x38]                   ; SummonData->bones  (the WORLD matrix array)
0x16911  mov  rdx,[rbx]                        ; EffData*
0x16914  mov  rcx, rbp ; shl rcx,5             ; boneIdx * 0x20
0x1691b  movups xmm0,[rcx+rax]  ; 0x1691f movups [rdx+0x40], xmm0    ; bone matrix -> EFF ROOT
0x16923  movups xmm1,[rcx+rax+0x10]; 0x16928 movups [rdx+0x50], xmm1
0x1692c  (optional) MulMatrix(EffData+0x40, scaleMat, EffData+0x40)  via call 0x3b60 @0x16976
```

So an eff model can be *hard-parented* to any bone of the live summon creature, with an optional scale
and **no translation offset**. `Hi_DrawMorphModelByBone` (entry `0x17190`, body `0x171ef`) does the same
while morphing between **two** eff models (`edx` = model A, `r8d` = model B, both EFFARR — `0x171b3`
and `0x171d3`) and also reaches the summon array (`0x1731f`).

**Consequence for the round's question:** the ByBone ops *consume* `summonModels[i].data->bones`. A cast
that used EFFARR "instead of" the summon slot would make these ops meaningless. And they are the only
mechanism by which a multi-part effect ensemble can follow the creature.

---

## 8. Q4 — the summon model and eff models are the SAME format and the SAME machinery

| shared | evidence |
|---|---|
| the **DATA struct** | Register (eff) writes `[DATA+8]`, `[DATA+0x10]`; `pose_eval` writes `[DATA+0x40]`; `0x7820` writes `[DATA+0x38]` — the *identical* offsets used by the summon path. Cross-arch clincher: on x86 the eff Register writes `mov dword[eax+0xc],0` (`0x12dcd`) — and B5 independently derived **SummonData.motion @+0x0c** on x86. Same struct. |
| the **container blob** | both check magic `word[blob] == 0x6F73`: eff wrapper `0x4729a`/`0x472a4`, summon descriptor builder `0x47348`/`0x47359`. |
| the **geometry header** | `byte[geom+2] = boneCount`, `byte[geom+3] = meshCount` — read identically by `Hi_DrawEffModel@0x162c5` and `Hi_DrawSummonModel@0x17900`. |
| the **prepare** helper | `model_prepare@0x7120` called by all five `Register*EffModel` **and** by `Hi_RegisterSummonModel`'s work body `0x1606c` (`call` @`0x16078`). |
| the **pose evaluator** | `0x186a0`, 4 call sites incl. `Hi_DrawSummonModel@0x17767`. |
| the **world-matrix builder** | `0x7820`, 6 call sites incl. `Hi_DrawSummonModel@0x1786e`. |
| the **mesh emit loop** | both walk `0..meshCount-1` calling `0x4eb0` then `0x56c0`/`0x9150` (`0x162d9`/`0x16509` vs `0x17922`/`0x179a8`). |
| the **ABR/RGB** helpers | eff tail-jumps `0xc880`/`0x83d0`; summon uses the same pair with the same `0xff` sentinel and `<<5`. |

| **summon-only** | **eff-only** |
|---|---|
| motion clip `DATA+0x10` + per-bone array + frame counter `rec+0x54` | `shadeMode` `slot+0x24` (Solid/Gou/Tex) |
| per-mesh hide mask `DATA+0x20` — `mov eax,[rcx+0x20]; bt eax,ebx; jb skip` @`0x17913`. **`Hi_DrawEffModel` has ZERO references to `+0x20`** (verified by grep over `0x16184..0x16547`) | `drawOffset` `slot+0x26`, `sliceValue` `slot+0x28` + `DATA+0x7e` |
| texanim `DATA+0x70` (Start/Stop) | morph (two-model blend, `DrawMorphEffModel`) |
| array LENGTH 1 | array LENGTH 32, pool-allocated by an opcode |

---

## 9. Q5 — x86 cross-check (independent re-derivation; every Δ is pointer-size)

| item | x64 | x86 | Δ | x86 evidence |
|---|---|---|---|---|
| EFFARR base | `0x220230` | `0x2081 9C` | (image) | `mov esi,0x1020819c` @`0x12d84` (RegisterSolid), `mov eax,0x1020819c` @`0x12c3e` (Init) |
| active flag addr | base+0x20 | `0x2081B8` = base+0x1C | −4 | `cmp byte[esi+0x1c],0` @`0x12d90`; `cmp byte[eax*8+0x102081b8],0` @`0x12c69` |
| stride | `0x30` | **`0x28`** | −8 | `add esi,0x28` @`0x12d97`; index `lea eax,[ecx+ecx*4]; [eax*8+base]` = `idx*40` @`0x12c66`. (−8 = −4 pointer −4 realignment: `0x2a→0x30` vs `0x26→0x28`.) |
| slot count | 32 | **32** | 0 | `cmp eax,0x20; jl` @`0x12d9a` and `@0x12c36` |
| handle | +0x22 | +0x1e | −4 | `movzx eax, word[esi+0x1e]` @`0x12ddb`; Init `mov eax,0x102081ba` (= base+0x1e) @`0x12c05` |
| shadeMode / drawOffset | +0x24 / +0x26 | +0x20 / +0x22 | −4 | `mov dword[esi+0x20],eax` @`0x12db6` |
| sliceValue | +0x28 | +0x24 | −4 | `mov word[esi+0x24],ax` @`0x12db9` |
| DATA size | **`0xC8`** | **`0x98`** | −0x30 | `add rcx,0xc8` @`0x15985` vs `add ecx,0x98` @`0x12c55` (= 8 pointers × 4 B, matching B5's monotone shift ladder) |
| `Hi_InitEffModel` | `0x15940` | `0x12C00` | — | same two-phase shape: zero 32 slots then distribute `count` pool blocks |
| `Hi_RegisterSolidEffModel` | `0x15ac0` | `0x12D80` | — | identical slot loop, `[data+0x0c]=0` (motion), `call 0x6980` (= `0x7120`) |
| `Hi_DrawEffModelByBone` | `0x167f0`/`0x16837` | `0x13550` | — | `imul ecx,eax,0x54; add ecx,0x1020869c; cmp byte[ecx+0x4c],0` (SUMMON, stride `0x54`, active `+0x4c`) @`0x135b5`–`0x135be`; `ecx=[SummonData+0x20]` (bones) @`0x135d5`; `movdqu [EffData+0x24], …` (root) @`0x135eb`/`0x135f5` — **exactly** B5's x86 summon offsets |
| `Hi_DrawMorphEffModel` | `0x16cc0`/`0x16d23` | `0x137E0` | — | two EFFARR indices @`0x137f0`/`0x13813`; `call 0x14600` = x86 `pose_eval` @`0x13850` |

**No structural divergence.** Slot count, the active-gate shape, the handle-is-slot-index rule, the
pool distribution, the shade-mode field, the ByBone bone copy, and the shared DATA struct all reproduce.

---

## 10. What this means for the s52 ROOT probe — diagnosis + exact fix

**Diagnosis (high confidence).** The probe reads the right array and the right slot; it reads a field
that is *by construction* only half the transform. `SummonData+0x40` is the anchor the `.seq` hands
`Hi_DrawSummonModel`; the animated flight lives in the motion clip and only ever materialises in the
composed matrices at `*(MATRIX*)(SummonData+0x38)`.

**The fix — one dereference deeper (still a passive read, still no DLL patch):**

```csharp
IntPtr rec  = pluginBase + 0x220830;                 // summon slot 0 (LENGTH 1)
if (Marshal.ReadByte(rec + 0x50) == 0) return;       // rec.active
IntPtr data = (IntPtr)Marshal.ReadInt64(rec);        // -> SummonData (0xC8 bytes)
IntPtr bones = (IntPtr)Marshal.ReadInt64(data + 0x38);   // <-- the composed WORLD matrix array
if (bones == IntPtr.Zero) return;
// bones[0] : PSX MATRIX -- rot 9x Int16 (fp12 /4096) @ +0x00..+0x11, translation 3x Int32 @ +0x14/+0x18/+0x1c
```

Notes that will save a wasted playtest:
* `bones` is **re-pointed every Draw** into the packet/scratch bump allocator (`mov [rcx+0x38],r8`
  @`0x7842`). It is valid for the frame that just drew — reading it from `Render()` (after the native
  tick) is the correct moment, exactly as the current ROOT row does. Never cache the pointer.
* Log **bone 0 only.** Dumping `bones[1..boneCount-1]` across a cast reconstructs the stock skeletal
  animation = extracting stock animation bytes = **BLOCKED** (same line FINDINGS §3.3 drew).
* Keep the existing `+0x40` row too, as `ANCHOR` — the pair (anchor, composed) is what makes the
  reprojection validator diagnostic rather than merely pass/fail.
* Sanity gate before trusting it: `PROJ · VIEW · bones[0].t` must land on the creature's `PRIM`
  screen centroid. The rigid path applies a `diag(1,−1,−1)` column flip (`0x797a`+) that the motion
  path does **not**; if the summon reprojection is mirrored in Y/Z, that convention is the first suspect.

**The one-cast discriminator that closes the EFFARR question empirically** (cheap, and worth doing in the
same probe round): add an `EFF` row that walks all 32 slots once per frame —
`base + 0x220230 + i*0x30`: `active(+0x20)`, `data(+0x00)`, `shadeMode(+0x24)`, `drawOffset(+0x26)`,
`sliceValue(+0x28)`, and for each active slot the translation at `*(long*)(data+0x38)` `+0x14/+0x18/+0x1c`.
Then:
* summon `active==1` with a live `bones[0]` ⇒ the creature is the summon model (predicted);
* an eff slot whose `bones[0].t` tracks the visible creature would refute this slice.
32 × ~40 bytes/frame — negligible, and it also gives the first census of *how many* eff models a real
Eidolon uses and which shade modes, which is direct input to the format pillar.

---

## 11. Runtime corroboration from the log already on disk

`sfxmeshprobe.log` (current contents: effect **227**, 2045 `ROOT` rows, frames 50–561; sampled, never
read whole). Aggregates only — no asset bytes:

* `active == 1` for every row; the matrix is **all-zero for frames 50–81**, then non-zero from frame 82.
  Since `SummonData+0x40` can be written by **nothing but** `pose_eval` called from
  `Hi_DrawSummonModel@0x17767` (§6.1 — 4 call sites, only one touches the summon DATA), the transition
  at frame 82 **proves `Hi_DrawSummonModel` began executing there**. The summon slot is genuinely drawn.
* The rotation carries a uniform ~1.4990 scale folded in (`|m00| = 6140`, `6140/4096 = 1.4990`) — i.e.
  `pose_eval`'s scale multiply (`call 0x3b60` @`0x187ab`) landed, another independent confirmation of
  the `(rot, trans, scale)` Draw-argument reading.
* The anchor translation moves in **146 distinct values** and includes a linear fly-by ramp
  `z: 9216 → −15104 → −39424` over frames 156→166 (≈ −4900/frame). **This is the reported
  "~40,000 units": it is real, intentional staging data, not a corrupt read.**
* From frame **301 through 561** (≈ 260 frames, ~43% of the capture) the anchor is **frozen** at
  `(0, −12288, −7168)` — while the cast is visibly still animating. A frozen anchor over the charge
  phase is exactly what §6 predicts and is *by itself* sufficient to explain "the trajectory does not
  match where the creature visibly is."

---

## 12. Confidence, and what is NOT proven

* **Proven statically (high):** every number in §1, the slot map §2, the pool allocator §3, the variant
  discriminator §4, the DATA sharing §8, the ByBone semantics §7, the two-transform structure §6, the
  x86 agreement §9.
* **Proven by the existing log (high):** the summon slot is registered and drawn during a real cast; the
  anchor freezes mid-cast.
* **NOT proven:** that *Bahamut specifically* (effect 194) behaves like effect 227 — the log on disk is
  227. **NOT proven:** how many eff slots a stock Eidolon actually uses, or whether any eff model is
  `ByBone`-attached in practice (the §10 `EFF` row answers both in one cast). **NOT proven:** that
  `bones[0]` is the visually best tracking point — for a long-necked dragon a named bone may be better;
  pick it empirically from the reprojection check.
* **Corrections this slice makes to prior artifacts:** (a) `bones[0] == root == DATA+0x40` (FINDINGS
  §3.1 / B1) is **false**; (b) `SummonData+0x08` is a **PSX geometry address**, not a "modelId"
  (A2/FINDINGS §2.2); (c) `DATA+0x38` is a *pointer* re-assigned every Draw, not an inline array;
  (d) `refkit`'s `.pdata`-driven iteration **misses no-unwind leaf functions** — `Hi_InitEffModel@0x15940`
  was invisible to `xrefs_to`/`xref_index`/the caller scan; any "nothing references X" conclusion drawn
  from those helpers needs a raw-immediate/leaf sweep before it is safe.
* **Open lead (not asserted):** the `.data` slots holding these handler entries (`0x68780..0x68e38`,
  195 + 20 contiguous code pointers) are **not** indexed by any RIP-relative code in the image; the
  init at `0x30d07` converts the table at `0x68250` to a PSX address and stores it at `0x21ff70`, so the
  table is very likely addressed in PSX space. Opcode numbering therefore probably keys off `0x68250`,
  but that is unverified — do not build a `.seq` opcode map on it without proof.

---

## 13. Provenance

Read-only static analysis of the user's own installed `FF9SpecialEffectPlugin.dll` (x64 **and** x86):
RVAs, mnemonics, struct offsets, control flow. **No DLL was modified or redistributed.** No stock
geometry, animation, or texture bytes were extracted or written anywhere. The runtime figures in §11 are
aggregate statistics over our own `sfxmeshprobe.log` debug output (staging/choreography class — the same
class as the camera track we already log), read by sampling. The helper scripts added this slice
(`m1_roster.py`, `m1_effarr_xref.py`, `m1_callsites.py`, `m1_dispatch.py`) are format-parser/analysis code
that reads the user's own DLL and prints addresses only — committable.
