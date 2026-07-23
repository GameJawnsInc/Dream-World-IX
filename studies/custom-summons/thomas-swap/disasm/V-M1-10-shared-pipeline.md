# V-M1-10 — adversarial re-derivation: "summon and eff models share one container + one draw pipeline"

**Claim under test (M1-10):** summon models and eff models share one blob magic `0x6F73`, one `ModelData`
struct, one prepare helper `0x7120`, one pose evaluator `0x186a0`, one world-matrix builder `0x7820`, one
geometry header (`byte[geom+2]=boneCount`, `byte[geom+3]=meshCount`), and the same per-mesh emit helpers
`0x4eb0/0x56c0/0x9150`.

**VERDICT: PARTIAL.** Seven of the eight enumerated elements reproduce exactly from a fresh disassembly,
several of them with *new* independent evidence the source artifact did not cite. **One element is
factually wrong as stated: `0x9150` is NOT shared — `Hi_DrawSummonModel` never calls it.** The source
artifact M1-effmodel-array.md §"the mesh emit loop" (line 279) actually states this correctly
("`0x4eb0` then `0x56c0`/`0x9150`", i.e. *alternatives*); the compressed claim sentence flattened an
either/or into a conjunction. The load-bearing conclusion (one container, one pipeline) survives intact.

All RVAs image-base-relative (x64 `ImageBase 0x180000000`, x86 `0x10000000`). Every line below was
re-disassembled this session with `refkit` off `.pdata` (no linear sweep). New helper: `v10_callers.py`
(direct call/jmp target index), `v10_names.py` (funclet-string naming), `v10_arrays.py` (EFFARR/SUMARR
touch map). Runtime values remain zero-on-disk `.bss`; only layout + logic are static-recoverable.

---

## 1. Element-by-element re-derivation

### 1.1 Blob magic `0x6F73` — CONFIRMED, and strengthened

Fresh disassembly of both cited sites:

```
0x47290 (eff wrapper)                    0x47330 (summon descriptor builder)
  0x4729a  mov  eax, 0x6f73                0x47348  mov  eax, 0x6f73
  0x472a4  cmp  word ptr [rcx], ax         0x47359  cmp  word ptr [rcx], ax
  0x472a7  je   0x472c3                    0x4735c  je   0x47378
  0x472a9  lea  rdx, [rip+0x3130]  -> 0x4a3e0     0x4735e  lea rdx,[rip+0x307b] -> 0x4a3e0
  0x472b0  lea  rcx, [rip+0x2fc9]  -> 0x4a280     0x47365  lea rcx,[rip+0x2f14] -> 0x4a280
  0x472b7  mov  r8d, 0x312                 0x4736c  mov  r8d, 0x312
```

Byte-identical check, **and the two asserts carry the identical file+line pair**: `0x4a3e0` is the UTF-16
string `..\..\SpecialEffectCode\psx\source\psx_compatibility.cpp`, and both pass `r8d = 0x312 = line 786`.
Same source line inlined into both wrappers ⇒ one magic check, one container format.

**Family attribution independently established** (neither was asserted by the artifact, both re-derived here
from the call graph):

* `0x47290` tail-jumps `jmp 0x15d30` (`Hi_RegisterTexListModel`) @`0x47316` and `jmp 0x15b70`
  (`Hi_RegisterGouEffModel`) @`0x47325` ⇒ it is the **eff** registration wrapper.
* `0x47330` `call 0x15ee0` (`Hi_RegisterSummonModel`) @`0x47491` ⇒ it is the **summon** descriptor builder.

### 1.2 `ModelData` struct — CONFIRMED (with one allocation nuance)

`model_prepare@0x7120(rcx=DATA, rdx=texA, r8=texB)` is the struct's constructor and settles the layout
question on its own. Re-disassembled `0x7120..0x7240`:

| write | rva | field |
|---|---|---|
| `mov [rcx+0x28], r10` | `0x71d9` | aux/tex arg |
| `mov [rcx+0x30], rbp(0)` | `0x71dd` | parent link |
| `mov [rcx+0x38], rbp(0)` | `0x71f7` | bone-matrix pointer |
| `mov [rcx+0x20], ebp(0)` | `0x7217` | **hide mask** |
| `mov [rcx+0x70], rbp(0)` | `0x71ff` | texanim |
| `mov word [rcx+0x7c], 0x1000` / `mov dword [rcx+0x78], 0x10001000` | `0x71f3`/`0x7203` | scale defaults |
| reads `dword [rcx+8]` as the PSX geometry address | `0x7130` | geom ptr |

Both families call it (§1.3), so both get the identical field set. Per-family writes at the same offsets:

| offset | eff (`Hi_RegisterSolidEffModel@0x15ac0`) | summon (`Hi_RegisterSummonModel@0x15ee0`) |
|---|---|---|
| `DATA+0x08` geometry | `mov dword[rcx+8],eax` @`0x15b11` | `mov dword[rcx+8],eax` @`0x15f3f` (from descriptor+0x3c) |
| `DATA+0x10` motion clip | `mov qword[rax+0x10],rdi(=0)` @`0x15b17` | `mov qword[rax+0x10],rcx` @`0x15fc6` (decoded from descriptor+0x180) |
| `DATA+0x70` texanim | (not written) | `mov qword[rax+0x70],rdi` @`0x160f5` |

Same offsets, per-family value. No offset was found meaning *different things* in the two families —
which is the claim's own stated refutation criterion, and it does not fire.

**x86 clincher — reproduced, and extended.** `refkit.load('x86')`:

```
eff   Hi_RegisterSolidEffModel @0x12d80 : mov [ecx+8],eax @0x12dc8 ; mov dword [eax+0xc],0 @0x12dcd ; call 0x6980 @0x12dd6
summ  Hi_RegisterSummonModel   @0x13080 : mov [ecx+8],eax @0x130d2 ; mov [ecx+0xc],eax  @0x130ec ; call 0x6980 @0x1317a
```

The cited `0x12dcd` reproduces exactly, **and this round found its summon twin at `0x130ec`** — the eff
Register stores `0` and the summon Register stores the decoded motion pointer *to the same x86 offset
`+0x0c`*, from a different codegen. That is the strongest single piece of evidence in the claim and it
holds. (`0x13080` was located from the `Hi_RegisterSummonModel()` string @`0x36ea4`, whose only absolute
reference is the cold path `push 0x10036ea4` @`0x131a9` — i.e. the funclet-vs-body trap was checked: the
real body is the one with the prologue at `0x13080`, the string lives in its `int3`-terminated error tail.)

**Nuance (not a refutation, but record it):** the two families' DATA blocks have different *owners*.
Eff DATA comes from a `0xC8`-strided pool assigned once by `Hi_InitEffModel@0x15940`
(`mov qword[rax],rcx; add rcx,0xc8` @`0x15982`/`0x15985`). The summon's DATA block is a caller-supplied
buffer: the descriptor builder writes `SUMARR[0].data = rbp+0x90` @`0x47449` (`lea rax,[rbp+0x90]`
@`0x47423`) after zeroing `SUMARR[0]+0x08..+0x4c` (`0x47434`–`0x4747a`). Same *layout*, different
*allocation*. A re-import tool must not assume the summon DATA is poolable.

### 1.3 Prepare helper `0x7120` — CONFIRMED exactly

Fresh direct-call index (`v10_callers.py 7120`) returns **exactly** the six cited call sites and no others:

```
call @0x15b1e (fn 0x15ac0 Hi_RegisterSolidEffModel)
call @0x15bd2 (fn 0x15b70 Hi_RegisterGouEffModel)
call @0x15cc7 (fn 0x15c20 Hi_RegisterTexEffModel)
call @0x15db4 (fn 0x15d30 Hi_RegisterTexListModel)
call @0x15e83 (fn 0x15e10 Hi_RegisterTexPtrModel)
call @0x16078 (fn 0x1606c)                      <-- the summon side
```

`0x1606c` is **not** an independent function: `.pdata` splits `Hi_RegisterSummonModel` into the chained
ranges `0x15ee0–0x15f35–0x15fda–0x1606c–0x16112`. A full disassembly of `0x15ee0..0x16112` shows one
prologue (`push rbx/rsi/rdi; sub rsp,0x40` @`0x15ee0`), one `ret` (`0x16111`), unconditional fall-through
into `0x1606c` from the bone-copy loop exit at `0x16067`, and the SUMARR `lea` at `0x15f01`. Confirmed
same-function.

### 1.4 Pose evaluator `0x186a0` — CONFIRMED, and the calling shape is identical

Callers (fresh): `0x161a1` (fn `0x16184` = `Hi_DrawEffModel` body), `0x165c0` (`Hi_DrawSliceEffModel`),
`0x16db4` (`Hi_DrawMorphEffModel`), **`0x17767` (`Hi_DrawSummonModel`)**. Both families, exactly as cited.

Body: `0x186a0` opens `lea rbx,[rcx+0x40]` and writes the 32-byte PSX MATRIX at `DATA+0x40` — rotation
seeded `0x1000` diagonal (`0x186ca`/`0x186d1`/`0x186dc`), translation copied from the `r8` arg into
`rbx+0x14/+0x18/+0x1c` (`0x1873b`/`0x18742`/`0x18749`). Same field, same semantics, for both families.

**New corroboration the artifact did not cite — the two Draw entry thunks are template-identical:**

```
Hi_DrawEffModel   0x16150            Hi_DrawSummonModel 0x17710
  movsxd rax, r9d                      movsxd rax, r9d
  lea rdi,[rax+rax*2]; shl rdi,4        imul rdi, rax, 0x58        ; stride 0x30 vs 0x58
  lea rax,[rip+0x20a0c9] (=EFFARR)      lea rax,[rip+0x209109] (=SUMARR)
  cmp byte[rdi+0x20],0 ; je err         cmp byte[rdi+0x50],0 ; je err
  mov rcx,[rdi] ; test rcx,rcx ; je err mov rcx,[rdi] ; test rcx,rcx ; je err
  -- falls through to 0x16184 --        -- falls through to 0x17740 --
  mov r9,r8 ; mov r8,rdx ; mov rdx,r10  mov r9,r8 ; mov r8,rdx ; mov rdx,r10
  call 0x186a0                          call 0x186a0
```

Identical register shuffle into the identical callee. This is compiled-from-one-template code.

### 1.5 World-matrix builder `0x7820` — CONFIRMED

Callers (fresh): `0x16234` (`DrawEffModel`), `0x16653` (`DrawSliceEffModel`), `0x168d0`
(`DrawEffModelByBone`), `0x16e39` (`DrawMorphEffModel`), `0x172fd` (`DrawMorphModelByBone`), and
**`0x1786e` (`DrawSummonModel`)** — exactly the cited six.

The family branch is inside it and reproduces: `mov r14,[rcx+0x10]` @`0x7838` (motion), `test r14,r14;
jne 0x7a20` @`0x7846`/`0x7849` ⇒ eff (motion==0) falls to the parent/rigid path at `0x784f`.

**Refinement of a downstream recommendation (flagged, outside M1-10 but consequential).** `0x7820` stores
`mov qword ptr [rcx+0x38], r8` @`0x7842` — i.e. **`DATA+0x38` holds a POINTER to the caller's MATRIX
scratch array, not inline matrices.** The parent path dereferences it exactly that way:
`mov rax,[rax+0x38]` @`0x785c`, then `movzx edx, byte[rcx+4]; shl rdx,5; mov ecx,[rdx+rax+4]`
(`0x7860`–`0x7868`) ⇒ bone *i* at `*(DATA+0x38) + i*0x20`. M1's forward recommendation is written
`*(MATRIX*)(SummonData+0x38)`; a probe that reads 32 bytes *at* `+0x38` will log a pointer and garbage.
It must **dereference first**. Getting this wrong costs a playtest.

### 1.6 Geometry header `byte[geom+2]=boneCount`, `byte[geom+3]=meshCount` — CONFIRMED

* meshCount, **eff**: `movzx esi, byte ptr [rcx+3]` @`0x162c5`, immediately followed by the mesh loop
  `xor ebx,ebx; test esi,esi; jle <end>` (`0x162c9`–`0x162cd`).
* meshCount, **summon**: `movzx esi, byte ptr [rcx+3]` @`0x17900`, identical loop shape at `0x17904`–`0x17909`.
  In both, `rcx` is the PSX-address-decoded `DATA+0x08` geometry blob (the same 4-arm decoder inlined at
  `0x16290`-ish / `0x17899`-ish).
* boneCount: `movzx r10d, byte ptr [rcx+2]` @`0x7aba`, where `rcx` came from decoding
  `mov ecx, dword ptr [rcx+8]` @`0x7a20` — i.e. **the same `DATA+0x08` geometry blob**, +2 instead of +3.
  (This read sits on the motion arm, which an eff model never takes; the *header* is shared, the eff path
  simply has no bones to walk. That is a feature subset, not a divergent offset.)

### 1.7 Per-mesh emit helpers — **PARTIALLY REFUTED**

Fresh caller index:

| helper | eff-family callers | summon-family callers | shared? |
|---|---|---|---|
| `0x4eb0` | `0x162d9` (DrawEffModel), `0x16a07` (DrawEffModelByBone) | **`0x17922` (DrawSummonModel)** | **YES** |
| `0x56c0` | `0x16509`, `0x16c40`, `0x1711b` (DrawMorphEffModel), `0x1767a` (DrawMorphModelByBone) | **`0x179a8` (DrawSummonModel)** | **YES** |
| `0x9150` | 32 call sites, all inside fns `0x16184`, `0x16837`, `0x16ed8`, `0x17355` | **none** | **NO** |

A complete disassembly of `Hi_DrawSummonModel`'s body `0x17740..0x179f2` contains exactly two emit calls —
`call 0x4eb0` @`0x17922` and `call 0x56c0` @`0x179a8` — and no `0x9150` anywhere.

The four `0x9150` caller functions are all **eff-family**, verified by which array they index
(`v10_arrays.py`):

* `0x16184` = `Hi_DrawEffModel` body — EFFARR `lea` @`0x16160`.
* `0x16837` = `Hi_DrawEffModelByBone` — EFFARR entry gate @`0x16809`; its SUMARR touch @`0x168ea` is the
  *bone-parent read*, not a slot lookup.
* `0x16ed8` = a chained `.pdata` range of `Hi_DrawMorphEffModel` (entry `0x16cc0`, EFFARR `lea` @`0x16cce`).
* `0x17355` = a chained range of `Hi_DrawMorphModelByBone` (entry `0x17190`, **two** EFFARR slot lookups
  @`0x1719b` with the `0x30` stride visible as `lea rdi,[rax+rax*2]; shl rdi,4` — a morph blend between two
  *eff* slots; SUMARR @`0x1731f` is again only the bone parent).

**Why:** `0x9150` is the shade-mode-1/offset variant, selected by the eff slot's `shadeMode` field
`word[slot+0x24]` (`movzx ecx,word[rdi+0x24]` @`0x163a6`) and `drawOffset` `word[slot+0x26]` (@`0x162de`).
The 0x58-byte summon slot record has **no such fields**, so the summon draw has nothing to dispatch on and
unconditionally uses `0x56c0`. `0x9150` and `0x56c0` are sibling functions (569 vs 574 bytes, identical
prologue shape; `0x9150` takes one extra `u16` arg spilled at `[rsp+0x20]` @`0x9150`) but they are two
distinct functions, and only `0x4eb0`+`0x56c0` are shared.

**Corrected statement:** *"…and the same per-mesh emit helpers `0x4eb0` + `0x56c0`; the eff family
additionally dispatches to the sibling emitter `0x9150` for shade-mode 1 / non-zero drawOffset, a variant
the summon record cannot select."*

---

## 2. Two structural corroborations found this round (not in the source artifact)

1. **The array adjacency closes on BOTH architectures.** x64: `EFFARR 0x220230 + 32×0x30 = 0x220830 = SUMARR`.
   x86 (re-derived here): `EFFARR 0x20819c` (`mov esi,0x1020819c` @`0x12d84`, stride `0x28` @`0x12d97`,
   count `0x20` @`0x12d9a`, active `+0x1c`) `+ 32×0x28 = 0x20869c = SUMARR` (`mov esi,0x1020869c` @`0x13097`,
   stride `0x54` @`0x130aa`, count `1` @`0x130b0`, active `+0x4c`). Two independent codegens, both closing
   to the byte. The bases/strides/counts for both arrays are now confirmed on two builds.
2. **A whole-image EFFARR/SUMARR touch map** (`v10_arrays.py`, 37 functions) shows a clean family split with
   exactly two crossings — `Hi_DrawEffModelByBone@0x16837` and `Hi_DrawMorphModelByBone@0x17190` — both of
   which are eff draws *reading a summon bone matrix*. Nothing else in the image mixes the arrays. This is
   independent support for M1's "EFFARR is a consumer of the summon slot" finding.

## 3. Per-family logic differences that do NOT refute the claim

* The **hide mask** `DATA+0x20` is tested only by the summon draw
  (`mov eax,[rcx+0x20]; bt eax,ebx; jb <skip>` @`0x17913`–`0x17919`); `Hi_DrawEffModel` has no `+0x20`
  access at all. But `0x7120` zeroes `+0x20` for both (@`0x7217`), and the only setters
  (`Hi_ShowSummonModelMesh@0x187e0` / `Hi_HideSummonModelMesh@0x18840`) touch SUMARR only. Same offset,
  same meaning, feature used by one family. Not a divergence.
* Eff models are rigid by construction (`DATA+0x10 = 0` in all five Registers, re-verified at `0x15b17`
  and its four siblings), so the motion arm of `0x7820` and the bone walk are dead for them. Again a
  subset, not a conflict.

## 4. Falsifiable predictions this verification leaves behind

* Any `.seq` opcode that draws a *summon* model will never route to `0x9150`; if a runtime trace ever shows
  `0x9150` touching the summon slot's DATA, §1.7 here is wrong.
* A container parser written against the `0x6F73` header must accept the *same* bytes for both families;
  if a real `ef###.bytes` yields an eff-model blob whose `byte[geom+2]` is not a bone count in the same
  encoding the summon blob uses, §1.6 is wrong.
* An s52 probe reading 32 bytes at `SummonData+0x38` will log a heap pointer, not a matrix (§1.5).
