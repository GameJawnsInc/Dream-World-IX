# Adversarial verification: claim `array-length-one`

**Verdict: CONFIRMED** (independently re-derived from FF9SpecialEffectPlugin.dll bytes, x64).

## What was claimed
RegisterSummonModel's free-slot search loop has bound 1, so only index 0 of the
0x58-stride summon-model record array is ever allocated.

## Independent re-derivation

### Error-stub-vs-real-body check
`refkit.locate_function(pe,"RegisterSummonModel")` returns the panic funclets, NOT
the body — its string @0x4b1d0 is xref'd from **0x16112** and **0x1612c**:
```
0x180016112: lea rdx,[rip+0x350b7]; lea rcx,[rip+0x20a770]; call [rip+0x33fea]; call 0x1800151a0; int3   ; "no free slot"
0x18001612c: lea rdx,[rip+0x3509d]; ... ; int3                                                            ; "null model data"
```
The **real body** is @0x15ee0 (.pdata range 0x15ee0..0x15f35), which *jumps to*
those stubs. Correctly distinguished.

### The search loop (disassembled fresh @0x15ee0)
```
0x180015ef7: xor  edi, edi                 ; edi = 0
0x180015eff: mov  eax, edi                 ; eax = 0  (slot index)
0x180015f01: lea  rbx, [rip + 0x20a928]    ; rbx = array base = 0x180220830
loop:
0x180015f08: cmp  byte ptr [rbx + 0x50], dil ; flag[+0x50] == 0 ?
0x180015f0c: je   0x180015f1e                 ; free -> allocate
0x180015f0e: inc  eax                          ; eax++
0x180015f10: add  rbx, 0x58                    ; next record (stride 0x58)
0x180015f14: cmp  eax, 1                        ; <-- BOUND = 1
0x180015f17: jl   0x180015f08                   ; eax<1 -> loop
0x180015f19: jmp  0x180016112                   ; else -> "no free slot" panic
found:
0x180015f1e: cmp  qword ptr [rbx], rdi          ; model data ptr == 0 ?
0x180015f21: je   0x18001612c                    ; -> "null model data" panic
0x180015f27: mov  byte ptr [rbx + 0x50], 1       ; mark slot registered
0x180015f2e: mov  word ptr [rbx + 0x54], di      ; frame counter = 0
```

### Bound is exactly 1 (raw-byte confirmed, no mislabel)
```
0x15f14: 83 F8 01   cmp eax, 1     <- immediate is 0x01, not a larger constant
0x15f17: 7C EF      jl  0x15f08
0x15f19: E9 ...     jmp 0x16112    <- the RegisterSummonModel "no free slot" stub
```
Trace: eax=0, check slot 0. If occupied -> eax=1, `cmp eax,1` sets SF==OF so
`jl` (eax<1) is **false** -> fall through to the panic jmp. Only slot 0 is ever
examined; the success path allocates with eax==0.

### Cross-checks
- Array base `0x180015f08 + 0x20a928 = 0x180220830` == calibrated summon-array
  base RVA 0x220830. ✓
- Stride 0x58, flag at +0x50, frame counter u16 at +0x54 == calibrated layout. ✓
- The two `jmp` targets (0x16112 / 0x1612c) are exactly the two error funclets
  that name RegisterSummonModel. ✓

### Refutation attempts (all failed to refute)
- **cmp against a constant >1?** No — immediate byte is 0x01. Refuted.
- **another register path writing a slot index != 0?** No — the sole write to the
  +0x50 registered flag in this function is @0x15f27 with rbx pinned to base+0
  (eax never advanced on the success path). No `imul r?,idx,0x58` alternate-index
  write occurs inside RegisterSummonModel.

## Minor note on prior evidence
The prior citation labeled the loop range "@0x15f0c-0x15f17"; 0x15f0c is actually
the `je` (found branch), the `cmp eax,1`/`jl` pair is @0x15f14/0x15f17. Cosmetic
address-labeling imprecision only; the substantive claim reproduces exactly.

## Scope caveat (not a refutation)
This confirms *allocation* is single-slot. Runtime record contents live in the
zero-on-disk bss scratch region @0x220830 and are not statically knowable — but the
allocation logic (bound=1) is fully code-recoverable, as shown.
