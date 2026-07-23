# Adversarial verification: `bone-matrix-array`

VERDICT: **CONFIRMED** (independently re-derived, all refutation conditions fail)

## Claim under test
SummonData(DATA block)+0x38 -> array of 32-byte PSX MATRIX structs (one per bone);
translation X/Y/Z = longs at +0x14/+0x18/+0x1c; GetSummonBoneMatrix copies the full 32 bytes.

## Method
Located both functions with refkit. `locate_function("Hi_GetSummonBoneMatrix")` returns the
COLD ERROR STUB @ 0x16c80 (29 bytes, just `lea rdx->string; call panic; int3`) -- the classic
error-stub-names-the-fn trap. Found the REAL body via the 3rd string xref site (0x18678), whose
`.pdata` container is 0x18630-0x18692. GetSummonBonePos real body located cleanly at 0x185b0-0x18625.

## GetSummonBonePos real body @ 0x185b0 (fresh disasm)
```
0x185b7 imul r9, rax, 0x58              ; record stride 0x58  ✓
0x185bb lea  rax, [rip + 0x20826e]      ; -> RVA 0x220830 (base)  ✓
0x185c2 cmp  byte [r9+rax+0x50], 0      ; active flag +0x50  ✓
0x185ca mov  r10, [r9+rax]              ; r10 = DATA block ptr (rec+0)
0x185d3 mov  rax, [r10+0x38]            ; bone array ptr = DATAblock+0x38  ✓
0x185da shl  rdx, 5                     ; bone stride 0x20  ✓  (refutes "shl !=5" -> not met)
0x185de movzx ecx, word [rdx+rax+0x14]  ; X @ +0x14  ✓
0x185eb movzx ecx, word [rdx+rax+0x18]  ; Y @ +0x18  ✓
0x185f9 movzx ecx, word [rdx+rax+0x1c]  ; Z @ +0x1c  ✓
```
Cited RVAs 0x185da / 0x185de / 0x185eb / 0x185f9 all reproduce exactly.

## GetSummonBoneMatrix real body @ 0x18630 (fresh disasm)
```
0x18637 imul r9, rax, 0x58             ; stride 0x58  ✓
0x1863b lea  rax, [rip + 0x2081ee]     ; -> RVA 0x220830 (same base)  ✓
0x18642 cmp  byte [r9+rax+0x50], 0     ; active flag +0x50  ✓
0x1864a mov  rax, [r9+rax]             ; DATA block ptr
0x18653 mov  rax, [rax+0x38]           ; bone array ptr = DATAblock+0x38  ✓
0x1865a shl  rcx, 5                    ; bone stride 0x20  ✓
0x1865e movups xmm0, [rcx+rax]         ; copy bytes 0x00-0x0f
0x18662 movups [r8], xmm0
0x18666 movups xmm1, [rcx+rax+0x10]    ; copy bytes 0x10-0x1f
0x1866b movups [r8+0x10], xmm1         ; total = 32 bytes  ✓
```
Cited RVAs 0x1865e / 0x18666 (two movups, 32 bytes) reproduce exactly.

## Cross-check against refutation conditions
- "stride other than 0x20 (shl != 5)": FALSE -- both fns `shl,5`.
- "translation read from offsets other than 0x14/0x18/0x1c": FALSE -- exactly those three.

## Struct-layout confirmation
32-byte stride with translation at 0x14/0x18/0x1c IS the canonical PSX LIBGTE `MATRIX`:
`short m[3][3]` (18 bytes) + 2 pad = 0x14, then `long t[3]` at 0x14/0x18/0x1c, total 0x20. Exact.

## One nuance (does not refute)
GetBonePos reads each translation as a **word** (`movzx ...word`, low 16 bits) and returns an
SVECTOR-style 3xint16; GetBoneMatrix copies the storage verbatim (the full 32-byte MATRIX incl.
the long translations). So "longs at +0x14/+0x18/+0x1c" describes the STORAGE correctly; the
pos-getter merely truncates each long to its low word. Struct size, stride, offsets, and the
"copies full 32 bytes" claim all hold.

## Runtime-only caveat
The bone MATRIX array (DATAblock+0x38) lives in the runtime-populated model data; contents are
NOT on disk. The LAYOUT is fully code-recoverable (above); the per-frame VALUES are not statically
recoverable -- they are written by the motion/GTE update path at runtime.
