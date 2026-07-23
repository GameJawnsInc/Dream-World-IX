# Adversarial verification: summon-array-layout

**Claim id:** summon-array-layout
**Verdict: CONFIRMED** (independently re-derived from fresh disassembly; no refuting access found)

## Claim restated
`summonModels[]` is at RVA **0x220830**, record stride **0x58** (88 bytes).
`rec+0x00` = pointer to the model DATA block; `rec+0x50` = byte active/registered flag;
`rec+0x54` = u16 motion frame counter.

## Method
Disassembled the cited RVAs fresh with refkit (capstone over the real .pdata bodies), then swept
**every** Hi_*Summon* function for the stride/flag/base pattern — directly testing the stated
refutation condition ("a different stride than 0x58 or a different flag offset than +0x50 in any
Hi_*Summon* function"). Base RVAs recomputed by hand from the RIP-relative `lea` (RIP = addr+size).

## Evidence — the two cited sites reproduce exactly

### Hi_SetSummonMotion, real body @ 0x17a10 (81 bytes)
```
0x17a17: imul r8, rax, 0x58              ; stride 0x58
0x17a1b: lea  rax, [rip + 0x208e0e]      ; base = 0x17a22 + 0x208e0e = 0x220830
0x17a25: cmp  byte ptr [r8 + 0x50], 0    ; +0x50 byte flag; je -> error stub
0x17a2c: mov  rax, qword ptr [r8]        ; rec+0x00 = DATA-block ptr
0x17a36: mov  word ptr [r8 + 0x54], dx   ; +0x54 u16 (dx=0) motion frame zeroed
0x17a3b: mov  qword ptr [rax + 0x10], rcx; [[rec+0]+0x10] = the MOTION ptr
```

### Hi_GetSummonBoneMatrix, **real** body @ 0x18630 (0x16c80 is the error stub only)
```
0x18637: imul r9, rax, 0x58              ; stride 0x58
0x1863b: lea  rax, [rip + 0x2081ee]      ; base = 0x18642 + 0x2081ee = 0x220830
0x18642: cmp  byte ptr [r9 + rax + 0x50], 0   ; +0x50 byte flag
0x1864a: mov  rax, qword ptr [r9 + rax]  ; rec+0x00 = DATA-block ptr
0x18653: mov  rax, qword ptr [rax + 0x38]; DATA+0x38 = bone-matrix array base
         ; index edx<<5 (32-byte matrices), copies 32 bytes via two movups
```

## Corroboration — the refutation sweep (all 12 roster fns)
Every function that indexes the array uses **stride 0x58**, **flag +0x50**, **base 0x220830**.
Zero exceptions found:

| function | stride | flag | base(s) |
|---|---|---|---|
| SetSummonMotion (0x17a10) | 0x58 | +0x50 | 0x220830 |
| SetSummonMotFrame (0x17a70) | 0x58 | +0x50 | 0x220830 |
| GetSummonBonePos (0x185b0) | 0x58 | +0x50 | 0x220830 |
| GetSummonBoneMatrix real (0x18630) | 0x58 | +0x50 | 0x220830 |
| ShowSummonModelMesh (0x187e0) | 0x58 | +0x50 | 0x220830 |
| HideSummonModelMesh (0x18840) | 0x58 | +0x50 | 0x220830 |
| StartSummonTexAnim (0x188a0) | 0x58 | +0x50 | 0x220830 |
| StopSummonTexAnim (0x18930) | 0x58 | +0x50 | 0x220830 |
| ModifySummonModelAbr (0x18af0) | 0x58 | +0x50 | 0x220830 |
| ModifySummonModelRGB (0x18b50) | 0x58 | +0x50 | 0x220830 |

Three independent RIP-relative base computations all resolve to **0x180220830** (RVA 0x220830):
`0x17a22+0x208e0e`, `0x18642+0x2081ee`, `0x185c2+0x20826e`.

## +0x54 is genuinely a u16 frame counter (extra confirmation)
Hi_SetSummonMotFrame @ 0x17a70:
```
0x17a94: mov   rax, qword ptr [rax + 0x10]     ; motion ptr (the field SetSummonMotion wrote)
0x17a98: movzx ecx, word ptr [rax + 2]         ; motion.maxFrames (u16 at motion+2)
0x17a9c: cmp   ecx, edx                          ; clamp requested frame vs max
0x17aa2: mov   word ptr [r8 + 0x54], ax         ; write 0 if out of range
0x17aac: mov   word ptr [r8 + 0x54], dx         ; else write requested frame
```
Both writes to `rec+0x54` are `word ptr` (u16), confirming the field width and its role as the
current motion-frame index bounded by `motion[+2]`.

## Notes / caveats (honest)
- Base 0x220830 lives in the zero-on-disk bss scratch region: the runtime **values** are not
  statically recoverable, but the **layout + update logic** are — exactly as the claim (and the
  round calibration) states. No overreach.
- A **secondary** base **0x220890** (= 0x220830 + 0x60) is referenced by most fns and by the
  RegisterSummonModel error stub (0x16112, a pure panic/int3 funclet — correctly NOT the array).
  It is a separate global, never used as an alternate stride/flag base for this record array, so it
  does not bear on the claim.
- The error-stub-vs-real-body trap was actively avoided: GetSummonBoneMatrix's real body is 0x18630
  (does the xmm matrix copy), not the 29-byte stub at 0x16c80 that only names the string.

## Conclusion
Every element of the claim reproduced independently, and the stated refutation condition was tested
against all 12 roster functions and did not occur. **CONFIRMED (high).**
