# V-M1-14 — adversarial verification: `SummonData+0x08` = PSX geometry address; `+0x38` = per-Draw pointer

**Claim (M1-14):** `SummonData+0x08` is a PSX-format address of the model-geometry blob, not a `modelId`
as A2/FINDINGS labelled it; and `SummonData+0x38` is a pointer re-assigned every Draw, not an inline
bone array.

**VERDICT: CONFIRMED** (both halves), re-derived from scratch with `refkit` against the user's own
installed `FF9SpecialEffectPlugin.dll` (x64 **and** x86). I found *stronger* evidence than the artifact
cited and no counter-evidence. One framing nit is recorded in §6 — it does not change the verdict.

Helper scripts added (committable — read the user's own DLL, print RVAs/mnemonics only):
`v_m114_a.py` … `v_m114_j.py`. All RVAs image-base-relative (x64 `0x180000000`, x86 `0x10000000`).
`refkit.functions(pe)` → **646** `.pdata` chunks, matching the prior round's instrument calibration.

---

## 1. The stated refutation criterion, tested exhaustively — NOT met

> *"WOULD BE REFUTED BY: finding `[DATA+8]` used as a table index rather than dereferenced as an address."*

I enumerated **every** read of `[reg + 8]` inside every function in the model family (`v_m114_h.py`,
spans taken from the `.pdata` chunk table, disassembled per-chunk so no linear desync is possible):

| site | instruction | what happens next |
|---|---|---|
| `model_prepare@0x7130` | `mov r9d, dword ptr [rcx + 8]` | PSX decode @`0x7155` |
| `build_world_matrices@0x7a20` | `mov ecx, dword ptr [rcx + 8]` | PSX decode @`0x7a62` |
| `build_world_matrices@0x80aa` | `mov ecx, dword ptr [rsi + 8]` | PSX decode @`0x80c3` |
| `mesh_helper@0x4ec1` | `mov r8d, dword ptr [rcx + 8]` | PSX decode @`0x4ef3` |
| `Hi_DrawEffModel@0x1625c` | `mov ecx, dword ptr [rax + 8]` | PSX decode `0x16263`–`0x162c3` |
| `Hi_DrawSliceEffModel@0x1668a` | `mov ecx, dword ptr [rax + 8]` | PSX decode |
| `Hi_DrawEffModelByBone@0x16985` | `mov ecx, dword ptr [rax + 8]` | PSX decode |
| `Hi_DrawMorphEffModel@0x16e61` | `mov ecx, dword ptr [rax + 8]` | PSX decode |
| **`Hi_DrawSummonModel@0x17896`** | `mov ecx, dword ptr [rax + 8]` | PSX decode `0x1789d`–`0x178fd` |

**Zero index uses. Zero scaled-index (`*n`) uses. Zero table lookups.** In every case the loaded dword is
run through the same inlined address decoder and the result is used as a **base pointer**.

---

## 2. `+0x08` is written by the host→PSX ENCODER, and I proved the encoder is the decoder's inverse

The prior artifact asserted `call 0x12940` = "host→PSX". I did not take that on trust; I disassembled
`0x12940` in full (it is chunked — `.pdata` chunks `0x12940/0x1297a/0x1298d/0x129cc/0x129ff/0x12a2e/
0x12ac6/0x12ae9`, `v_m114_c.py`+`v_m114_d.py`) and matched its **output encodings** against the
decoder's **input tests**, byte-constant for byte-constant:

| encoder (`0x12940`) emits | decoder (e.g. `0x1789d`) tests |
|---|---|
| `0x12aaf`: `sub edx,[r9+0x1fd0]` ; `0x12abb`: **`bts edx, 0x1f`** → `0x8XXXXXXX` | `0x178a1`: `shr edx,0x18` ; `0x178a4`: **`cmp edx,0x80`** → `and eax,0xfffffff` ; `cmp eax,0x200000` ; `sub ecx,[rip+…]` ; `add rcx,[rip+…]` |
| `0x129e1`/`0x12ace`: `shl idx,0x18` ; **`or …,0xc00000`** ; `sub edx,[regionTable+idx*0x20+8]` ; `or edx,…` | `0x178c7`: **`and eax,0xc00000`** ; `cmp eax,0xc00000` ; `and ecx,0x3fffff` (offset) ; `shl rax,5` ; `add rcx,[rax+r15+8]` (same `*0x20` region table) |
| (scratchpad passthrough) | `0x178ea`: `add ecx,0xe0800000` ; `cmp ecx,0x3ff` — i.e. `ecx ∈ [0x1F800000,0x1F8003FF]` = **the PSX 1 KB scratchpad** |

`0x12940`'s body (`0x1298d`–`0x129c0`) walks a table of `dword[ctx+0x1fc0]` entries, stride `0x20`, each
`{active@-0x10, base@+0x00, limit@+0x08}`, testing `base <= hostPtr < limit` and keeping the smallest
offset — a **host-pointer → region+offset** mapper. `0x12a2e`+ is the "register a new region" path
(`[r8+8] = hostPtr-0x20000`, `[r8+0x10] = hostPtr`, `[r8+0x18] = hostPtr+0x300000`, bump `[ctx+0x1fc0]`).

The three encoder forms and the three decoder forms are an exact 1:1 inverse pair, including the
`0x80` KSEG0 tag, the `0xC00000` region tag, and the `0x1F8003FF` scratchpad window. **`[DATA+8]`
holds a PS1 address in PS1 address space.** "modelId" is not a viable reading of that value.

### 2.1 The write sites, re-derived

* **eff** (`Hi_RegisterSolidEffModel`, real body `0x15ac0`, `.pdata` `[0x15ac0..0x15b66)`):
  `0x15af3 mov rdx,rcx` (the caller's model blob pointer) → `0x15b04 call 0x180012940` →
  `0x15b09 mov rcx,[rbx]` (slot→DATA) → **`0x15b11 mov dword ptr [rcx+8], eax`**. Then
  `0x15b17 mov qword ptr [rax+0x10], rdi` (rdi=0 ⇒ motion NULL) and `0x15b1e call 0x7120`.
* **summon** (`Hi_RegisterSummonModel` `0x15ee0`; the cited `0x15f3f` lives in the **continuation chunk**
  `[0x15f35..0x15fda)` — I confirmed the chunk exists rather than assuming linear flow):
  `0x15f32 mov eax, dword ptr [rsi+0x3c]` → **`0x15f3f mov dword ptr [rcx+8], eax`**.
* **where `modelDesc+0x3c` comes from** (`.pdata` chunk `[0x47330..0x474b5)`):
  `0x47399 movzx edx, word ptr [rsi+4]` ; `0x4739d add rdx, rsi` (⇒ `blobBase + u16 at blob+4`) ;
  **`0x473a0 call 0x180012940`** ; **`0x473a5 mov dword ptr [rbp+0x3c], eax`**.
  So the value is the encoded address of a *sub-block inside the container*, located by the container's
  own `u16` offset field — i.e. the **geometry chunk**, exactly as claimed.
* **x86 cross-check** (independent codegen, same source): `Hi_RegisterSolidEffModel@0x12d80`:
  `0x12da6 push dword ptr [ebp+8]` (blob) → `0x12dbd call 0x1000ffc0` (the **out-of-line** x86 encoder)
  → **`0x12dc8 mov dword ptr [ecx+8], eax`**, then `0x12dcd mov dword ptr [eax+0xc], 0` (motion).
  On x86 the encode/decode are *named functions*, which makes the "this is an address" reading
  unambiguous: `Hi_DrawEffModelByBone@0x13589` does `push dword[ctx+0x24]` → `call 0x100010d0`
  (**decode**) → use → `call 0x1000ffc0` (**encode**) → `mov [ctx+0x24], eax`. A pure round-trip.

### 2.2 …and the decoded pointer is used as GEOMETRY

`Hi_DrawSummonModel`: `0x17900 movzx esi, byte ptr [rcx+3]` = **meshCount**, then the mesh loop
`0x17910`–`0x17922` with the hide-mask gate `mov eax,[rcx+0x20]; bt eax,ebx; jb skip` and
`call 0x4eb0(DATA, meshIdx)`. `Hi_DrawEffModel` is identical at `0x162c5`/`0x162d9`.
`build_world_matrices@0x7aba` reads `byte[geom+2]` as boneCount. A header at `blob[2]/blob[3]` carrying
bone/mesh counts is a geometry header, not an id.

---

## 3. `+0x38` — a pointer, written unconditionally on every Draw

**Image-wide census of writes** to `qword ptr [<non-stack reg> + 0x38]` (`v_m114_e.py`) returns exactly
**three** instructions in the whole DLL:

```
0x71f7  mov qword ptr [rcx + 0x38], rbp     ; model_prepare@0x7120 — rbp = 0 (`xor ebp,ebp` @0x7134) => init to NULL
0x7842  mov qword ptr [rcx + 0x38], r8      ; build_world_matrices@0x7820 — THE per-Draw assignment
0x39ef7 mov qword ptr [rbx + 0x38], rdi     ; unrelated struct, outside the model family
```

`0x7842` sits in the prologue of `0x7820` (`.pdata [0x7820..0x7a31)`), **before any branch**:
`0x7838 mov r14,[rcx+0x10]` / `0x783c mov r13,r8` / `0x783f mov rsi,rcx` / **`0x7842`** / `0x7846 test r14,r14`.
Unconditional — every call re-assigns it.

**Callers of `0x7820`** — I resolved direct `call` targets across all 646 chunks, not by trusting the list:
`0x16234` (DrawEffModel) · `0x16653` (DrawSliceEff) · `0x168d0` (DrawEffByBone) · `0x16e39` (DrawMorphEff) ·
`0x172fd` (DrawMorphByBone) · **`0x1786e` (Hi_DrawSummonModel)**. Six Draw bodies, six re-assignments.

**The assigned value is a fresh bump-allocated block, not a stable buffer.** `Hi_DrawSummonModel`
`0x177e2`–`0x1786e`: load `dword[globalCtx+0x24]`, PSX-decode it into `r8`, `call 0x7820(DATA, frame, r8)`,
then `0x17873`–`0x17879` re-**encode** the *returned* advanced cursor (`rdx=rax`, `call 0x12940`) and
store it back to `[globalCtx+0x24]`. Identical shape in `Hi_DrawEffModel` (`0x161a6`…`0x1624b`).
So `+0x38` points into the PSX packet/scratch arena at a cursor that advances every draw call.

**Readers dereference it, then index off the dereferenced pointer** — decisive against "inline array":

```
Hi_GetSummonBonePos    0x185d3: mov rax, qword ptr [r10 + 0x38]   ; r10 = SummonData
                       0x185da: shl rdx, 5                        ; boneIdx * 0x20
                       0x185de: movzx ecx, word ptr [rdx + rax + 0x14]
Hi_GetSummonBoneMatrix 0x18653: mov rax, qword ptr [rax + 0x38]
                       0x1865e: movups xmm0, xmmword ptr [rcx + rax]      ; 32-byte MATRIX copy
Hi_DrawEffModelByBone  0x1690d: mov rax, qword ptr [rax + 0x38]   ; SummonData->bones
                       0x1691b: movups xmm0, [rcx + rax]          ; -> EffData+0x40
```

If `+0x38` were an inline array these would be `lea`, not `mov qword`. They are `mov qword`.

**x86 cross-check:** `Hi_DrawEffModelByBone@0x13550`: `0x135c8 mov ecx, dword ptr [ecx]` (slot→DATA) →
`0x135d5 **mov ecx, dword ptr [ecx + 0x20]**` (the x86 `bones` field) → `0x135db shl eax,5` →
`0x135e7 movdqu xmm0,[ecx]`. Same *load-then-index* shape at the pointer-size-shifted offset.

---

## 4. Traps checked and cleared

* **Cold error-funclet vs real body** — `0x15ac0` and `0x15ee0` are real bodies (they contain the slot
  loop, the `call 0x12940`, and the `ret`), not the `HIRAISHI ERROR` stubs; the error stubs are the
  `jmp`-targets `0x15b32`/`0x16112`/`0x1612c`. Verified by reading the bodies, not by `locate_function`.
* **Linear-disasm desync** — every listing above starts at a `.pdata` chunk **begin**. Two windows I
  first probed mid-chunk produced garbage (`0x16240: cld`, an empty `0x17800` window); I re-ran from
  chunk starts and the instructions changed. Recorded here so nobody re-derives from a desynced view.
* **Chunked functions** — `0x15f3f` and `0x473a5` are *not* inside the `.pdata` range that begins at the
  function's entry. I located the covering continuation chunks (`[0x15f35..0x15fda)`, `[0x47330..0x474b5)`)
  before quoting them.
* **Runtime-scratch mislabelling** — this claim is about **layout and logic only**. Both fields are in
  zero-on-disk `.bss` (`EFFARR 0x220230` / summon `0x220830`); nothing here asserts a disk value.
* **Overfitting to one file** — no `ef###.bytes` was parsed for this verdict. The evidence is code, and
  it is corroborated by an independently compiled second binary (x86).
* **Dead managed code** — `SFXBinaryFile.cs` was not used and is not cited.

---

## 5. What this changes for the s52 ROOT probe (unchanged from M1 — but now independently supported)

`+0x38` being a per-Draw pointer into a bump arena means a probe **must dereference it fresh each frame
and must never cache it**. It also means a null read is expected before the first Draw
(`model_prepare` initialised it to NULL @`0x71f7`). Both facts are now proven from the write census
(exactly 3 writers image-wide) rather than inferred.

`+0x08` being a PSX address means a probe can, in principle, decode it to a host pointer and read
`byte[geom+2]` / `byte[geom+3]` to learn the model's **bone and mesh counts** at runtime — a legitimate
structural read. Reading the geometry *payload* would be extracting stock content; the counts are not.

---

## 6. Framing nit (does not affect the verdict)

The claim's second half is phrased as a correction ("**not** an inline bone array"). It is a true
statement, but it is not a correction of the prior artifacts: `A2-summon-struct.md:89` already declares
`/*+0x38*/ PSXMATRIX* bones;` and `FINDINGS.md:53` already annotates it "*re-pointed per frame, 2.4*".
The genuine correction is the **first** half: `A2-summon-struct.md:85` and `FINDINGS.md:50` both label
`+0x08` as `u32 modelId`, and that label is wrong — verified above.

---

## 7. Provenance

Read-only static analysis of the user's own installed `FF9SpecialEffectPlugin.dll` (x64 and x86):
RVAs, mnemonics, struct offsets, control flow. **No DLL was modified.** No stock geometry, animation,
or texture bytes were read, extracted, or written anywhere. No `ef###.bytes` was opened for this slice.
The helper scripts `v_m114_a.py`–`v_m114_j.py` are analysis code that reads the user's own DLL and
prints addresses only — committable.
