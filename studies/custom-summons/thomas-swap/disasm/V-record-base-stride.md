# Adversarial verification: claim `record-base-stride`

**STATEMENT:** The summon-model record array is at RVA `0x220830` with stride `0x58` bytes.

**VERDICT: CONFIRMED** (independently re-derived, multiple corroborating sites)

## Re-derivation (fresh disasm, FF9SpecialEffectPlugin.dll)

### 1. Base RVA from RIP arithmetic — SetSummonMotion real body @ 0x17a10
Fresh `refkit.disasm(0x17a10..0x17a61)`:
```
0x17a17: imul  r8, rax, 0x58            <- stride
0x17a1b: lea   rax, [rip + 0x208e0e]    <- base load
0x17a22: (next instr = RIP)  add r8, rax
```
RIP-relative target = next-instruction RVA + disp = `0x17a22 + 0x208e0e = 0x220830`. ✓ base confirmed.
This is the REAL body (checks `+0x50` active flag, writes motion ptr to `[[rec]+0x10]`, zeroes `+0x54` u16, then rets), not the error stub — the stub/panic path is the *fall-through* at 0x17a44 (`lea rcx,->"...memory not enough!"; call ...; call 0x151a0; int3`). The error-string xref for this fn is at 0x17a4e, inside that cold path.

### 2. Stride `0x58` corroborated across independent accessors
`xrefs_to(0x220830)` returns 17 sites. Of the 10 code sites checked, 9 contain `imul ..., 0x58` in the same function:
```
func 0x16837, 0x171ef, 0x17710, 0x17a10, 0x17a70, 0x185b0, 0x18630, 0x187e0, 0x18af0  -> all imul *,0x58
```
The 10th (func 0x15ee0, the Register routine) uses a **loop increment idiom instead of imul**, which independently corroborates the stride:
```
0x15f01: lea  rbx, [rip + 0x20a928]     ; RIP 0x15f08 + 0x20a928 = 0x220830  (same base)
0x15f08: cmp  byte ptr [rbx + 0x50], dil ; active-flag probe at +0x50
0x15f10: add  rbx, 0x58                   ; STRIDE via pointer increment
0x15f27: mov  byte ptr [rbx + 0x50], 1    ; sets active flag
0x15f2e: mov  word ptr [rbx + 0x54], di   ; zeroes +0x54 frame counter
```
Two different codegen idioms (`imul idx,0x58` and `add ptr,0x58`) over the SAME base = strong cross-check. Field offsets +0x50/+0x54/[rec+0x10] all match the calibration layout.

### 3. Base is runtime scratch (zero on disk) — as calibration states
RVA 0x220830 is in section `.data` (VA 0x4f000, RawSize 0x1a000 => on-disk ends 0x69000). 0x220830 is past raw data, in the zero-init BSS tail: **layout recoverable from code, runtime VALUES not on disk.** Consistent with the "no runtime scratch recovery" constraint.

## Refutation attempts (all failed to refute)
- Different base after RIP math? No — 0x17a22 + 0x208e0e and 0x15f08 + 0x20a928 both resolve to 0x220830 exactly.
- Stride other than 0x58? No — found in 9 imul sites + 1 loop-add site, never any other constant against this base.
- Error-stub confusion? Ruled out — 0x17a10 does real work; the panic path is its fall-through, not the analyzed body.

## Citations
- FF9SpecialEffectPlugin.dll @0x17a17, @0x17a1b, @0x17a22 (SetSummonMotion)
- FF9SpecialEffectPlugin.dll @0x15f01, @0x15f08, @0x15f10 (Register loop)
- xrefs_to(0x220830) = 17 sites; imul-0x58 in funcs 0x16837/0x171ef/0x17710/0x17a10/0x17a70/0x185b0/0x18630/0x187e0/0x18af0
- PE section table: .data VA 0x4f000 RawSize 0x1a000
