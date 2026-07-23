# V-M1-11 — adversarial re-derivation: "the per-mesh hide mask is summon-only"

**Claim under test (M1-11, from `M1-effmodel-array.md`):**
> The per-mesh hide mask is summon-only: `Hi_DrawSummonModel` tests it and skips the mesh, while
> `Hi_DrawEffModel`'s entire body contains ZERO references to `+0x20` and zero bit-test instructions.

**VERDICT: PARTIAL — the load-bearing half is CONFIRMED (and strengthened by an independent x86
cross-build check); one stated sub-fact is FALSE as written and is corrected below.**

Everything here was re-derived from scratch against the user's own installed
`FF9SpecialEffectPlugin.dll` (x64 `ImageBase 0x180000000`, x86 `0x10000000`) with `refkit`, per-function
off `.pdata` (x64) / `0xCC`-padding boundaries (x86). No prior artifact's numbers were assumed.

---

## 1. What is CONFIRMED

### 1.1 The summon draw DOES consult a per-mesh hide mask and skips the mesh

Real body `Hi_DrawSummonModel` = **`[0x17710, 0x179f2)`** in two `.pdata` chunks
(`0x17710..0x17740` entry, `0x17740..0x179f2` main); `0x179f2..0x17a0f` is the MSVC **cold error
funclet** (this is what `refkit.locate_function("Hi_DrawSummonModel")` returns — the documented trap,
independently reproduced).

Entry chunk (freshly disassembled):
```
017710  push rdi
017716  movsxd rax, r9d                  ; r9d = slot index
01771c  imul  rdi, rax, 0x58             ; SUMMON stride 0x58
017720  lea   rax, [rip + 0x209109]      ; next=0x17727 → SUMMARR base RVA 0x220830
017727  add   rdi, rax                   ; rdi = &summonSlot[idx]
01772a  cmp   byte ptr [rdi + 0x50], 0   ; slot ACTIVE flag @+0x50
01772e  je    0x1800179f2                ; -> cold error funclet
017734  mov   rcx, qword ptr [rdi]       ; rcx = slot->data (ModelData*)
017737  test  rcx, rcx ; je 0x1800179f2
```

Per-mesh loop (main chunk):
```
017900  movzx esi, byte ptr [rcx + 3]    ; meshCount = geomBlob[3]
017904  mov   ebx, r14d                  ; ebx = mesh ordinal = 0
017907  test  esi, esi ; jle 0x1800179cc
017910  mov   rcx, qword ptr [rdi]       ; rcx = DATA
017913  mov   eax, dword ptr [rcx + 0x20]; <-- HIDE MASK  (DATA+0x20)
017916  bt    eax, ebx                   ; <-- test bit(meshOrdinal)
017919  jb    0x1800179c2                ; <-- SET => SKIP
01791f  movzx edx, bl
017922  call  0x180004eb0                ; per-mesh setup (shared with the eff draw)
  ...
0179c2  inc   ebx                        ; <-- the jb target IS the loop increment
0179c4  cmp   ebx, esi
0179c6  jl    0x180017910
```
`jb 0x179c2` lands exactly on `inc ebx` → set bit = mesh omitted for this frame. **CONFIRMED, verbatim
at the cited RVAs `0x17913 / 0x17916 / 0x17919`.**

### 1.2 The mask's writers confirm the semantics (set = hidden)

Freshly disassembled, whole bodies:
```
Hi_ShowSummonModelMesh  fn[0x187e0,0x18834)
 0187e7 imul r8, rax, 0x58 ; 0187eb lea rax,[rip+0x20803e] (next 0x187f2 → 0x220830)
 0187f2 cmp byte[r8+rax+0x50],0
 018805 mov eax,1 ; 01880a shl eax,cl ; 01880c not eax
 01880e and dword ptr [r8 + 0x20], eax      ; CLEAR bit  -> shown

Hi_HideSummonModelMesh  fn[0x18840,0x18892)
 018865 mov eax,1 ; 01886a shl eax,cl
 01886c or  dword ptr [r8 + 0x20], eax      ; SET bit    -> hidden
```
(`r8` is reloaded as `slot->data` at `0x187fa` / `0x1885a`, so the operand is **DATA+0x20**.)

**Those two strings — `Hi_ShowSummonModelMesh ()` @`0x4b448`, `Hi_HideSummonModelMesh ()` @`0x4b478` —
are the ONLY `Show`/`Hide`/`Mesh` debug strings in the entire DLL.** There is no
`Hi_HideEffModelMesh` anywhere. (`refkit.find_strings(pe,"Hide"|"Show"|"Mesh")` — 2 hits total.)

### 1.3 The eff draw family never consults it — verified three independent ways

**(a) Whole-image instruction census** (every `.pdata` function disassembled; 646 functions):

* `dword ptr [reg + 0x20]` with a **non-`rsp`** base — **404 total hits image-wide**, of which exactly
  **three** live in the summon/eff model subsystem:
  `0x17913` (DrawSummonModel, the mask read), `0x1880e` (Show), `0x1886c` (Hide).
  **Zero** in `[0x16150,0x16547)` DrawEffModel, `[0x16570,0x167cd)` DrawSliceEffModel,
  `[0x167f0,0x16c80)` DrawEffModelByBone, `[0x16cc0,0x17144)` DrawMorphEffModel.
* `bt`/`bts`/`btr`/`btc` — **55 image-wide**; exactly **one** in the whole model subsystem: `0x17916`.
  Zero in any eff draw function.

**(b) The two loops are otherwise the SAME loop.** Side-by-side, the eff per-mesh loop is the summon
loop minus exactly three instructions:
```
EFF  @0x162c5   movzx esi, byte[rcx+3]   |  SUMMON @0x17900  movzx esi, byte[rcx+3]
     @0x162c9   xor   ebx, ebx           |         @0x17904  mov   ebx, r14d   (=0)
     @0x162cb   test  esi,esi ; jle end  |         @0x17907  test  esi,esi ; jle end
     @0x162d3   mov   rcx, qword[rdi]    |         @0x17910  mov   rcx, qword[rdi]
     ---- (nothing) ----                 |         @0x17913  mov  eax,[rcx+0x20]
     ---- (nothing) ----                 |         @0x17916  bt   eax,ebx
     ---- (nothing) ----                 |         @0x17919  jb   <inc>
     @0x162d6   movzx edx, bl            |         @0x1791f  movzx edx, bl
     @0x162d9   call  0x4eb0             |         @0x17922  call  0x4eb0
```
Same `meshCount` source, same ordinal register, same shared per-mesh callee `0x4eb0`. The mask test is
the *only* structural difference at the top of the loop.

**(c) Call-closure sweep.** Transitive callees of all four eff draw entry chunks (direct
`call`/`jmp` targets, depth ≤ 8) = 19 functions incl. the real emitters `0x4eb0`, `0x56c0`, `0x9150`,
the world-matrix builder `0x7820`, `pose_eval 0x186a0`, `0x12940`, `0xb200`. Exactly **one** candidate
`dword [reg+0x20]` read appeared — `0xb32f` in `fn[0xb200,0xb3ba)` — and it is **not** the hide mask:
`0xb322 lea rcx,[rax+rax*4]; 0xb326 lea r13,[rdx+rcx*8]` makes `r13` a **mesh descriptor at stride
0x28 inside the geometry blob**, and `[r13+0x20]` immediately feeds the PSX address decoder
(`shr edx,0x18; cmp edx,0x80; and eax,0xfffffff; cmp eax,0x200000`) — a PSX pointer field, not a bitmask.
No `test`/`bt` against a shifted 1 anywhere in the closure.

### 1.4 x86 CROSS-BUILD confirmation — the strongest evidence (different codegen, same source)

The 32-bit build compiles the same `if` with a **completely different instruction** (`test`, not `bt`),
which rules out "an artifact of one compiler's peephole".

x86 function bounds re-derived from `0xCC` padding, anchored on each function's own error-string
`push imm32` site:

| function | x86 range | hide-mask consult |
|---|---|---|
| `Hi_DrawEffModel` | `[0x131d0,0x133b2)` | **none** |
| `Hi_DrawSliceEffModel` | `[0x133c0,0x1354b)` | **none** |
| `Hi_DrawEffModelByBone` | `[0x13550,0x137dc)` | **none** |
| `Hi_DrawMorphEffModel` | `[0x137e0,0x139fc)` | **none** |
| `Hi_DrawSummonModel` | `[0x13ce0,0x13f3c)` | **`0x13e6b  test dword ptr [esi+0x14], eax`** |

(x86 `ModelData` packs pointers 4-wide, so the mask sits at **DATA+0x14**, per the −0xc shift already in
`B5-x86-crosscheck.md` — re-derived here, not assumed.) The only `+0x14` references inside the four eff
draws are `mov eax, dword ptr [ebp + 0x14]` at each function's second instruction — a **stack argument**,
not a struct field. Writers match:
```
x86 Hi_ShowSummonModelMesh @0x14730 : imul eax,ecx,0x54 ; add eax,0x1020869c ; cmp byte[eax+0x4c],0
                                      shl eax,cl ; not eax ; 014756 and dword[edx+0x14], eax
x86 Hi_HideSummonModelMesh @0x14780 : ...             ; 0147a4 or  dword[edx+0x14], eax
```

### 1.5 The `.seq` opcode side is summon-only too

The only call sites of `Hi_Show/HideSummonModelMesh` in the whole image are two adjacent handlers inside
the mega-interpreter `fn[0xeea4,0x12321)`:
```
0117c2 …  two operand fetches via call 0x126c0  →  0117df call 0x1800187e0  (Show)
0117e9 …  two operand fetches via call 0x126c0  →  011806 call 0x180018840  (Hide)
```
Both pass `(ecx = index, edx = meshOrdinal)` straight through with **no model-family discriminator** —
the index is always interpreted as a SUMMON slot index. So the `HideMeshes=<hex>` op the Thomas-swap
round used physically cannot address an eff model.

---

## 2. What is FALSE as written (the correction)

> "`Hi_DrawEffModel`'s entire body contains ZERO references to `+0x20`"

**This is false for the actual function.** `Hi_DrawEffModel` is a **two-chunk** function —
`[0x16150,0x16184)` (entry) + `[0x16184,0x16547)` (main) — and the *entry* chunk contains a `+0x20`
reference:
```
016150  push rdi
016156  movsxd rax, r9d
01615c  lea   rdi, [rax + rax*2]
016160  lea   rax, [rip + 0x20a0c9]      ; next=0x16167 → EFFARR base RVA 0x220230
016167  shl   rdi, 4                     ; idx*0x30
01616b  add   rdi, rax
01616e  cmp   byte ptr [rdi + 0x20], 0   ; <-- a "+0x20]" reference
016172  je    0x180016547
```
The cited grep range `[0x16184,0x16547)` **excluded exactly the chunk that contains it.** The same
reference exists in the other three eff draws (`0x16595`, `0x1681a`, `0x16ce6`, `0x16d08`).

**It is not a hide-mask consult — it is an OFFSET COLLISION, and it is a trap for future agents:**

| structure | `+0x20` means | width / op |
|---|---|---|
| **`EffSlot`** (EFFARR, stride 0x30) | the slot **ACTIVE flag** | `cmp byte ptr [slot+0x20], 0` |
| **`ModelData`** (0xC8 block) | the per-mesh **HIDE MASK** | `mov eax, dword ptr [DATA+0x20]` + `bt` |

The summon slot avoids the collision only by accident of its layout (stride 0x58, active @+0x50).
So the correct, defensible wording is:

> `Hi_DrawEffModel` (and Slice/ByBone/Morph) contain zero references to **`ModelData+0x20`** and zero
> bit-test instructions. Their only `+0x20` operands are byte compares of the **EffSlot active flag**
> and `[rsp+0x20]` stack spills.

**Footnote (nuance, not a refutation):** eff models DO carry the field — the shared `model_prepare`
`fn[0x7120,0x7240)` zeroes it for both families (`0x7134 xor ebp,ebp` … `0x7217 mov dword[rcx+0x20], ebp`).
It is present, permanently 0, and never read on the eff path. So the mask is summon-only *by consult
and by API*, not by struct layout.

---

## 3. Refutation criterion, evaluated

> "WOULD BE REFUTED BY: a hide-mask consult anywhere in the eff draw family."

Searched: all four eff draw functions in **both** builds, their depth-≤8 call closure (x64), and every
`bt`-family / `dword [reg+0x20]` instruction in the whole x64 image. **Zero hide-mask consults found.**
Criterion not met.

---

## 4. Consequence for the tracking problem (unchanged by this verdict)

M1-11 is a *negative* result about the eff family and does not by itself move the staging work. It does
add one usable constraint: **`HideMeshes` can only ever hide meshes of the single summon slot**, so any
future "hide the native donor, render the custom creature" trick that involves an eff model needs a
different mechanism (per-mesh ABR/RGB via `Hi_ModifyEffModelAbr@0x18990` / `...RGB@0x189f0`, or simply
not registering the model). Corollary already established elsewhere and *not* re-tested here: the eff
family is rigid single-matrix (`DATA+0x10 = 0` forced at register time), which is consistent with it
having no per-mesh visibility control at all.

---

## 5. Reproduction

All checks are pure read-only disassembly of the user's own install; no game bytes were written
anywhere. Scripts used were throwaway (scratchpad) and are reproducible from the snippets above via
`refkit.load()` / `refkit.functions()` / `refkit.disasm()` / `refkit.find_strings()`.

**refkit caveats re-confirmed this round:**
1. `locate_function` returned the **cold error funclet** for every one of the five draw functions
   (`DrawEffModel → (0x16547,0x16564)`, `DrawSummonModel → (0x179f2,0x17a0f)`, …). Always resolve the
   real body from the preceding `.pdata` entries.
2. MSVC **splits these functions across two `.pdata` entries**. Any grep scoped to "the body" that uses
   only the larger chunk silently drops the prologue — which is exactly how M1-11's evidence line went
   wrong. Always take `[entryChunkBegin, coldFuncletBegin)`.
