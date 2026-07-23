# Adversarial re-verification: claim `k4096-confirmed`

**Verdict: CONFIRMED** (independently reproduced from FF9SpecialEffectPlugin.dll with refkit; no
prior evidence trusted).

## What was claimed
resolve_position @RVA 0x145a0 computes `anchor + 4096.8*(cos/sin theta)` using MSVCR120 `cos`
(thunk 0x49cd2) and `sin` (thunk 0x49ce4) with doubles pi@0x4b6a0, 2.0@0x4b698, +4096.8@0x4b6c8,
-4096.8@0x4b6e8.

## Independent reproduction (all fresh)

**Function is a real body, not the error-stub trap.** `.pdata` range 0x145a0..0x148f0 = **848 bytes**;
it sets up a stack canary, calls a helper (0x148f0) twice, runs cos/sin, and writes 3 packed i16 vertex
components to `[rdi]`, `[rdi+2]`, `[rdi+4]`. This is genuine work, not a 29-byte `lea;call panic;int3`
funclet.

**Constants decode exactly** (raw little-endian doubles via `refkit.read_rva`):
| RVA | value |
|---|---|
| 0x4b6c8 | `4096.8` |
| 0x4b698 | `2.0` |
| 0x4b6a0 | `3.141592653589793` (pi) |
| 0x4b6e8 | `-4096.8` |

**RIP-relative targets recomputed from capstone `addr+size+disp`** (not trusting the prior RVAs) — every
`movsd`/`mulsd` in the branch resolves to one of the four constants above. Sample (branch-A, `test bl,0x40`
taken):
```
0x14696 movsd xmm9,[rip+0x37029] -> rva 0x4b6c8 = 4096.8
0x1469f movsd xmm8,[rip+0x36ff0] -> rva 0x4b698 = 2.0
0x146a8 movsd xmm7,[rip+0x36ff0] -> rva 0x4b6a0 = pi
0x146c6 CALL 0x49cd2            (cos)
0x146fc mulsd xmm0,[rip+0x36fe4] -> rva 0x4b6e8 = -4096.8
0x146f7 CALL 0x49ce4            (sin)
```

**Thunks resolve to trig imports (via IAT, not assumed):**
- `0x49cd2` = `jmp qword [rip+0x4b8]` -> IAT slot rva **0x4a190** -> `MSVCR120.dll!cos`
- `0x49ce4` = `jmp qword [rip+0x4be]` -> IAT slot rva **0x4a1a8** -> `MSVCR120.dll!sin`

None of the refutation conditions triggered: constants are the claimed values, and both calls land on
MSVCR120 trig, not some other import.

## Nuance (does NOT refute — accuracy note for downstream authors)
The claim's shorthand "`anchor + 4096.8*(cos/sin theta)`" understates the actual fixed-point shape. Per the
disasm, branch-A per component is:
```
angle_arg = (raw_field_i16 / 4096.8) * 2.0 * pi      ; xmm9=4096.8 divisor, xmm8=2.0, xmm7=pi
c = cos(angle_arg) ;  s = sin(angle_arg)
out = ( (c*4096.8 cvttsd2si) * r15d >>12 ) etc.       ; sar ...,0xc  = fixed-point >>12
```
So **4096.8 is doing double duty**: (a) the angle period normaliser (raw field units per full turn) and
(b) the amplitude the cos/sin result is scaled back up by before the `>>12` fixed-point vertex multiply.
The anchor add is the `[rsp+0x28..0x2c]` midpoint computed by the two 0x148f0 helper calls at the top
(averaged, `sar ...,1`). The core assertion — the four constants, MSVCR120 cos/sin, and the K=4096.8
branch-A trig — is fully confirmed; only the one-line formula gloss is imprecise.

## Method
`refkit.load()` (x64, base 0x180000000), `refkit.disasm(0x145a0,0x148f0)`, `refkit.read_rva` for the
doubles, capstone RIP recompute, and `pe.DIRECTORY_ENTRY_IMPORT` walk for the IAT names. Cited by
file:rva throughout.
