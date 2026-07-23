# V-effarr-layout — adversarial re-derivation of CLAIM M1-01

**Claim:** EFFARR @ RVA `0x220230`, stride `0x30`, exactly 32 slots, byte `active` flag @ `+0x20`;
and `0x220230 + 32*0x30 == 0x220830` == the summon-model array base (the two arrays are adjacent).

**Verdict: CONFIRMED.** All four numbers re-derived from a fresh disassembly, the adjacency arithmetic
is exact, no counterexample exists among *any* of the array's 20 code references, and the whole
structure is independently reproduced in the x86 build of the same DLL.

Method note: I deliberately did **not** trust `locate_function` for the real bodies (it returns the MSVC
cold error funclet for several of these — e.g. `Hi_DrawEffModel`'s string xref at `0x16547` sits in the
17-byte funclet `0x16547..0x16564`, not in the real body `0x16150`). Instead I built
`refkit.xref_index(pe, 0x220060, 0x220a00)` and enumerated **every** instruction in the image whose
RIP-relative operand resolves into the array region, then disassembled each containing `.pdata` function.

---

## 1. x64 — the four numbers

`Hi_RegisterSolidEffModel` real body = `.pdata` range **`0x15ac0..0x15b66`** (has prologue, the scan
loop, and both error tails inside the same range; the string `Hi_RegisterSolidEffModel()` @`0x4b0e0` is
loaded at `0x15b32` / `0x15b4c` — i.e. this is a real body with in-range cold tails, not a funclet):

```
0x15acc  lea  rbx, [rip + 0x20a75d]        -> 0x220230      <- BASE
0x15ad5  cmp  byte ptr [rbx + 0x20], dil   (dil == 0)       <- ACTIVE FLAG, BYTE, +0x20
0x15add  add  rbx, 0x30                                     <- STRIDE
0x15ae1  cmp  eax, 0x20
0x15ae4  jl   0x180015ad5                                   <- 32 SLOTS (idx 0..31)
```

Occupy path: `0x15aed mov word ptr [rbx+0x20], 1` — a *merged* store (active byte = 1, `+0x21` = 0),
not evidence of a 16-bit flag. Byte-ness is proven three other ways:

* `Hi_FreeEffModel` (`0x159a0..0x159ea`) clears it byte-wide: `0x159c3 mov byte ptr [rax+rdx*8+0x20], 0`
* every scan/index accessor **reads** it with `cmp byte ptr [... + 0x20], 0`
* `0x18a90` writes a *separate* byte at `+0x21` (`mov byte ptr [r8+0x21], 1`), so `+0x20` cannot be a word.

## 2. The index form (stride re-derived a second, independent way)

`Hi_FreeEffModel@0x159a0` reproduces the cited sequence exactly:

```
0x159a4  movsxd rax, ecx
0x159a7  lea    rdx, [rax + rax*2]          ; idx*3
0x159ab  lea    rax, [rip + 0x20a87e]  -> 0x220230
0x159b2  add    rdx, rdx                    ; idx*6
0x159b5  cmp    byte ptr [rax + rdx*8 + 0x20], 0   ; base + idx*48 == idx*0x30
```

(Note: `Hi_FreeEffModel` does **not** bound-check the caller's index — an out-of-range index walks
straight into the adjacent summon record. Observation only; not part of the claim.)

## 3. Refutation sweep — all 20 references, zero counterexamples

`xref_index(0x220060, 0x220a00)` finds exactly 20 code references to `0x220230`. Every one of them is
either the scan-loop form (`add r,0x30 ; cmp eax,0x20 ; jl`) or one of the two idx*0x30 index forms
(`lea r,[rax+rax*2] ; shl r,4` or `lea r,[rax+rax*2] ; add r,r ; [base + r*8]`), and every one tests
`byte [slot+0x20]`:

| site | fn | form |
|---|---|---|
| 0x15224 | 0x15200 | `lea rdi,[rax+rax*2]; shl rdi,4` |
| 0x159ab | 0x159a0 (`Hi_FreeEffModel`) | `*3; add; [b+r*8]` |
| 0x15acc | 0x15ac0 (`RegisterSolidEffModel`) | loop `+0x30`, bound `0x20` |
| 0x15b7c | 0x15b70 (`RegisterGouEffModel`) | loop `+0x30`, bound `0x20` |
| 0x15c4e | 0x15c20 (`RegisterTexEffModel`) | loop `+0x30`, bound `0x20` |
| 0x15d4e | 0x15d30 (`RegisterTexListEffModel`) | loop `+0x30`, bound `0x20` |
| 0x15e2e | 0x15e10 (`RegisterTexPtrEffModel`) | loop `+0x30`, bound `0x20` |
| 0x16160 | 0x16150 (`DrawEffModel` real body) | `*3; shl 4` |
| 0x16587 | 0x16570 | `*3; shl 4` |
| 0x16809 | 0x167f0 | `*3; shl 4` |
| 0x16cce | 0x16cc0 | `*3; shl 4` |
| 0x1719b | 0x17190 | `*3; shl 4` |
| 0x17aea | 0x17ae0 | `*3; add; [b+r*8]` |
| 0x17b37 | 0x17b30 | `*3; add; [b+r*8]` |
| 0x1800a | 0x18000 | `*3; add; [b+r*8]` |
| 0x189a3 | 0x18990 | `*3; add; [b+r*8]` |
| 0x189fa | 0x189f0 | `*3; add; [b+r*8]` |
| 0x18a4b | 0x18a40 | `*3; add; [b+r*8]` |
| 0x18a9b | 0x18a90 | `*3; shl 4` |
| 0x18c07 | 0x18c00 | `*3; add; [b+r*8]` |

**All five `Register*EffModel` variants use the identical `0x220230 / 0x30 / 0x20 / byte@+0x20` quadruple.**
The claim's stated refutation conditions (a different bound constant, or a non-`0x30` stride accessor)
are therefore *not* met anywhere in the image.

Interior-address check: within `[0x220230, 0x220830)` the only other referenced address in the whole
image is `0x220252` (`0x30c8b`, fn `0x30c20`) — that is slot 0's `+0x22` handle word, i.e. *inside*
slot 0. There is no unrelated global embedded between the two arrays.

## 4. The adjacency

Summon array base re-derived independently from `Hi_RegisterSummonModel` real body `0x15ee0..0x15f35`
(the string xrefs at `0x16112`/`0x1612c` are the cold funclet — trap avoided):

```
0x15f01  lea  rbx, [rip + 0x20a928]  -> 0x220830
0x15f08  cmp  byte ptr [rbx + 0x50], dil
0x15f10  add  rbx, 0x58
0x15f14  cmp  eax, 1
0x15f17  jl   0x180015f08              <- LENGTH 1
```

`0x220230 + 32*0x30 = 0x220230 + 0x600 = 0x220830`. **Exact, zero gap.**
Corroborated by the field-zeroing init at fn `0x47330`, which writes `0x220830, 0x220838, 0x220840,
0x220848, 0x220850, 0x220858, 0x220860, 0x220868, 0x220870, 0x220878, 0x22087c` — i.e. it touches the
single summon record `[0x220830, 0x220888)` and nothing below `0x220830`; and by fn `0x30c20`, which
writes the record pointer at `0x220830` and clears the active flag at `0x220880` (= `0x220830 + 0x50`).
`0x220888` (written `1` by fn `0x31060`) and `0x220890` (the assert-context global, 43 xrefs) are the
next globals *after* the record — so the summon array really is exactly one `0x58` record long.

## 5. x86 cross-check (different codegen, same source)

`refkit.load('x86')`, image base `0x10000000`:

* EffModel register (real body `0x12f50`, and a second at `0x12d80`, and the one erroring with
  `Hi_RegisterSolidEffModel()` @VA `0x10036dc0` at `0x12de5`):
  `mov esi, 0x1020819c` ; `cmp byte ptr [esi+0x1c], 0` ; `add esi, 0x28` ; `cmp eax, 0x20` ; `jl`
  → base RVA `0x20819c`, stride `0x28`, **bound 0x20 = 32 slots**, byte active @`+0x1c`.
* Summon register (real body containing the `Hi_RegisterSummonModel()` error site `0x131a9`):
  `0x13097 mov esi, 0x1020869c` ; `cmp byte ptr [esi+0x4c], 0` ; `add esi, 0x54` ; `cmp eax, 1` ; `jl`
  → base RVA `0x20869c`, stride `0x54`, **length 1**, byte active @`+0x4c`.
* **`0x20819c + 32*0x28 = 0x20819c + 0x500 = 0x20869c`.** The adjacency reproduces in the 32-bit build.

The stride/offset differ between builds exactly as pointer width predicts (`0x30`→`0x28`, `0x58`→`0x54`,
flag `+0x20`→`+0x1c`, `+0x50`→`+0x4c`); the **slot count 32 and the summon length 1 are identical**, so
both are genuine source-level constants, not codegen artifacts.

## 6. Caveats recorded (not refutations)

* Both arrays live in the **uninitialized tail of `.data`** (`.data` VirtualAddress `0x4f000`,
  VirtualSize `0x5d3440`, SizeOfRawData `0x1a000` — `0x220230` is far past the raw end, so
  `pe.get_data` returns nothing). **Layout is static-recoverable; contents are runtime-only.** This
  claim is a layout claim, which is legitimate; do not let anything downstream quote *values* from here.
* The claim is purely about array geometry. It does **NOT** establish that Bahamut's visible creature is
  drawn through the EFFARR rather than the single summon slot. "32 slots vs 1" is suggestive, not proof —
  that hypothesis needs its own test (runtime probe of which registrar the creature's meshes flow
  through, or a static trace from the `0xeea4` interpreter's handlers to `Hi_Draw*EffModel`).
* `Hi_FreeEffModel` performs no index bound check, so a bad index reaches the summon record. Irrelevant
  to the claim; relevant if anyone ever writes a patch here (we don't).

All RVAs above were produced by a fresh `refkit` run against the installed
`x64\FF9_Data\Plugins\FF9SpecialEffectPlugin.dll` (646 `.pdata` functions) and
`x86\FF9_Data\Plugins\FF9SpecialEffectPlugin.dll` this session.
