# Adversarial verification: CLAIM `bone-matrix-path`

**Verdict: CONFIRMED** (with two typing caveats documented below — neither is a refutation).

## The claim
The per-frame per-bone world transform is a 32-byte PSX MATRIX array pointed by
`DATA+0x38`; rotation is 9× int16 at `+0x00` and translation int32 at `+0x14/+0x18/+0x1c`.
Stride 0x20.

## Independent re-derivation (fresh refkit disasm of the real bodies)

Both cited functions were disassembled fresh from `FF9SpecialEffectPlugin.dll` (x64,
image base 0x180000000). I distinguished the real bodies from the MSVC error funclets
by call-graph/shape and by which error string each references.

### Hi_GetSummonBonePos — real body @ 0x185b0..0x18625 (117 bytes)
```
0x185b4 movsxd rax, ecx                       ; ecx = model index (arg0)
0x185b7 imul   r9, rax, 0x58                   ; record stride 0x58  ✓ (calibration)
0x185bb lea    rax, [rip+0x20826e]             ; base -> 0x180220830 ✓ summon array
0x185c2 cmp    byte [r9+rax+0x50], 0           ; +0x50 active flag   ✓
0x185ca mov    r10, [r9+rax]                   ; r10 = [rec+0x00] = DATA block ptr ✓
0x185d3 mov    rax, [r10+0x38]                 ; rax = DATA+0x38  (matrix array base)
0x185d7 movsxd rdx, edx                        ; edx = bone index (arg1)
0x185da shl    rdx, 5                          ; boneIdx * 0x20  -> STRIDE 0x20 ✓
0x185de movzx  ecx, WORD [rdx+rax+0x14]        ; read 16-bit @ +0x14 -> out[0]
0x185e3 mov    WORD [r8],   cx
0x185eb movzx  ecx, WORD [rdx+rax+0x18]        ; read 16-bit @ +0x18 -> out[2]
0x185f0 mov    WORD [r8+2], cx
0x185f9 movzx  ecx, WORD [rdx+rax+0x1c]        ; read 16-bit @ +0x1c -> out[4]
0x185fe mov    WORD [r8+4], cx
0x185607 ret
```
Error path @0x18608 references string @ 0x4b3e8 = "Hi_GetSummonBonePos()..." (confirms
this is the real getter, not a funclet).

### Hi_GetSummonBoneMatrix — real body @ 0x18630..0x18692 (98 bytes)
The `locate_function` stub for this name is the 29-byte funclet @0x16c80; the REAL body
is @0x18630. Proof: its error path `lea rdx,[rip+0x32d99]` @0x18678 resolves to
0x18004b418 = the "Hi_GetSummonBoneMatrix()" string (one of the 3 xref sites listed in
calibration: 0x16c80 / 0x176ba / **0x18678**).
```
0x18634 movsxd rax, ecx                        ; model index
0x18637 imul   r9, rax, 0x58                   ; stride 0x58 ✓
0x1863b lea    rax, [rip+0x2081ee]             ; base -> 0x180220830 ✓ same array
0x18642 cmp    byte [r9+rax+0x50], 0           ; +0x50 flag ✓
0x1864a mov    rax, [r9+rax]                   ; [rec+0x00] = DATA block ptr ✓
0x18653 mov    rax, [rax+0x38]                 ; rax = DATA+0x38 (matrix array base)
0x18657 movsxd rcx, edx                        ; bone index
0x1865a shl    rcx, 5                          ; boneIdx * 0x20  -> STRIDE 0x20 ✓
0x1865e movups xmm0, [rcx+rax]                 ; copy bytes 0x00..0x0f
0x18662 movups [r8], xmm0
0x18666 movups xmm1, [rcx+rax+0x10]            ; copy bytes 0x10..0x1f
0x1866b movups [r8+0x10], xmm1                 ; TOTAL = 32 bytes copied ✓
0x18670 ret
```

## Test against the stated refutation conditions
- *"GetSummonBonePos reading translation from offsets other than 0x14/0x18/0x1c"* —
  **FALSE**: it reads exactly 0x14, 0x18, 0x1c. Not refuted.
- *"the matrix stride not being 0x20"* — **FALSE**: both functions `shl idx,5`
  (× 0x20). Not refuted.

Neither refutation condition holds → the claim stands.

## Corroboration: this is the canonical PSX `MATRIX` struct
```
typedef struct { short m[3][3]; short pad; long t[3]; } MATRIX;
        m[3][3] = 9 × int16 = 18 bytes @ 0x00..0x11
        pad     = 2 bytes    @ 0x12..0x13
        t[3]    = 3 × int32  @ 0x14, 0x18, 0x1c
        sizeof  = 18 + 2 + 12 = 32 = 0x20   (matches the stride exactly)
```
The translation offsets (0x14/0x18/0x1c, 4-byte spacing) are byte-exact, and 0x20 stride
== sizeof(MATRIX). The rotation-at-0x00 placement follows from this standard layout.

## Two typing caveats (refinements, NOT refutations)
1. **GetSummonBonePos reads 16-bit WORDs, not int32.** The claim says translation is
   "int32". The STORAGE is int32 (canonical `long t[3]`, corroborated by the 4-byte field
   spacing and the 0x20 == sizeof(MATRIX) stride), but this particular getter down-converts
   by reading only the low WORD of each component (`movzx ...,word ptr`) into a 3×int16 /
   SVECTOR-shaped output at `[r8+0/2/4]`. So "int32 storage" is correct; "the getter
   returns int32" would be wrong.
2. **"rotation 9× int16 at +0x00" is inferred, not directly typed here.** Neither cited
   function interprets bytes 0x00..0x11 — GetSummonBoneMatrix blindly `movups`-copies all
   32 bytes, and GetSummonBonePos never touches 0x00..0x13. The rotation typing rests on
   (a) the canonical PSX MATRIX layout and (b) the byte-exact translation offset match. It
   is a strong, standard inference but is not demonstrated by a rotation READ in these two
   bodies. A writer that populates `DATA+0x38` (Register/Draw/update path) would type-prove
   it directly; not required to sustain the claim.

## Provenance note
`DATA+0x38` points into a runtime-allocated block; the matrix VALUES are runtime-only
(never on disk). Only the LAYOUT (offsets/stride/types) is recovered from code — consistent
with the round's rule. No creature bytes extracted.

## Bottom line
The matrix path — 32-byte PSX MATRIX array at `DATA+0x38`, stride 0x20, translation at
0x14/0x18/0x1c — is independently reproduced and matches the canonical PSX MATRIX struct.
CONFIRMED. The only sharpening: the translation is int32 *in storage*, and
GetSummonBonePos returns only its low 16 bits.
