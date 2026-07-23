# Verification: claim `updatecamera-thunk-body`

VERDICT: **CONFIRMED**

## Claim under test
SFX_UpdateCamera export @RVA 0x1dd0 is a thunk `jmp` to the real body at RVA 0x1e80..0x2030
(432 bytes), which returns a pointer to RVA 0x211df0.

## Independent re-derivation (refkit, fresh disasm)

### 1. Export address
`refkit.exports(pe)` -> `SFX_UpdateCamera = 0x1dd0`. (CONFIRMED; note
`refkit.locate_function` fails to body-locate it -- the export table has the entry but no
code xref -- so I read raw bytes at the export RVA instead.)

### 2. Thunk (FF9SpecialEffectPlugin.dll:0x1dd0)
```
0x180001dd0  jmp 0x180001e80
0x180001dd5  int3  (x10 padding)
```
Single unconditional jmp to image-relative 0x1e80. CONFIRMED -- jumps exactly where claimed,
not elsewhere.

### 3. Body extent (FF9SpecialEffectPlugin.dll:0x1e80)
`.pdata` function record covering 0x1e80 = **[0x1e80, 0x2030), size 0x1b0 = 432 bytes**.
Prologue `push rbx; sub rsp,0x20`, epilogue `add rsp,0x20; pop rbx; ret` at 0x202f; next
function begins at 0x2030. CONFIRMED (matches the cited 0x1e80..0x2030 / 432 bytes exactly).

Body is a real function (does work: reads a `-1` sentinel u16 @[rip+0x3212d2], branches on a
mode dword @[rip+0x20ff7d]==1 and on the `ecx`/ebx arg, copies a block of camera params
between two scratch regions (rip+0x67xxx and rip+0x20fexx), then `cvtdq2ps`-converts ~14 i16
fields to floats into the rip+0x20fexx buffer). Not the error-stub/funclet class.

### 4. Return pointer (FF9SpecialEffectPlugin.dll:0x2010)
```
0x180002010  lea rax, [rip + 0x20fdd9]
```
Instruction length 7 (next ip 0x2017). Target RVA = 0x2017 + 0x20fdd9 = **0x211df0**.
`rax` is not overwritten afterward (only `movss` to memory + `cvtdq2ps` on xmm through the
epilogue), so the function returns a pointer to RVA 0x211df0. CONFIRMED.

## Refutation attempts (all failed to refute)
- Thunk jumping elsewhere: NO -- single jmp to 0x1e80.
- Body a different size / an error funclet: NO -- .pdata says [0x1e80,0x2030)=432B, real
  work body, not the malloc-fail stub pattern.
- Return address differing from 0x211df0: NO -- lea arithmetic reproduces 0x211df0 to the byte.

## Note (not part of the claim)
0x211df0 is in the DLL's data region; this function POPULATES its float fields at runtime from
i16 scratch inputs. The returned struct is the SFX camera-param block, but its per-frame VALUES
are runtime state (scratch), so the pointer identity is statically recoverable while the
contents are not -- consistent with the prior round's runtime-scratch caveat.
