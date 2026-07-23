# Adversarial verification: `bonematrix-real-body`

**Verdict: CONFIRMED** (independently re-derived from FF9SpecialEffectPlugin.dll x64, fresh disasm).

## Claim
Real `Hi_GetSummonBoneMatrix` @ RVA 0x18630 (0x16c80 = error funclet): indexes summonModels
(base 0x220830, stride 0x58), checks +0x50 active, derefs rec+0x00 -> data+0x38 (bone matrix
array), copies a 32-byte PSX matrix at (bone<<5). Values runtime-only, access path static.

## Independent evidence (dll:rva)

Error stub `dll:0x16c80..0x16c9d` (29 bytes) — `lea rdx,->str; lea rcx,->obj; mov r8d,esi;
call [panic]; call 0x1800151a0; int3`. Does **no** matrix work. Its string @0x4b418 is
xref'd from 0x16c80, 0x176ba, **0x18678** — the last is the fail path of the real body.

Real body `dll:0x18630..0x18692` (98 bytes), fresh capstone:
```
0x18630  sub    rsp,0x28
0x18634  movsxd rax,ecx                 ; arg1 = record index
0x18637  imul   r9,rax,0x58             ; stride 0x58  ✓
0x1863b  lea    rax,[rip+0x2081ee]      ; -> 0x220830 (summonModels base)  ✓
0x18642  cmp    byte[r9+rax+0x50],0     ; +0x50 active flag  ✓
0x18648  je     0x18675                 ; -> fail
0x1864a  mov    rax,[r9+rax]            ; rec+0x00 -> data block ptr  ✓
0x1864e  test   rax,rax / je 0x18675    ; null guard on data ptr
0x18653  mov    rax,[rax+0x38]          ; data+0x38 -> bone matrix array  ✓
0x18657  movsxd rcx,edx                 ; arg2 = bone index
0x1865a  shl    rcx,5                   ; bone<<5 = *32  ✓
0x1865e  movups xmm0,[rcx+rax]          ; +0x00..0x0f
0x18662  movups [r8],xmm0               ; -> out (arg3)
0x18666  movups xmm1,[rcx+rax+0x10]     ; +0x10..0x1f
0x1866b  movups [r8+0x10],xmm1          ; total 0x20 bytes copied  ✓
0x18670  add rsp,0x28 / ret
0x18675  mov r8d,ecx
0x18678  lea rdx,[rip+0x32d99]          ; -> 0x4b418 "Hi_GetSummonBoneMatrix () "  ✓
0x1867f  lea rcx,[rip+0x20820a]         ; -> object 0x220890
0x18686  call [panic] / call 0x1800151a0 / int3
```

Resolved lea targets (recomputed from next-insn RIP):
- base: 0x18642 + 0x2081ee = **0x220830** ✓ (bss scratch, zero-on-disk — values runtime-only, path static)
- string: 0x1867f + 0x32d99 = **0x4b418** = `'Hi_GetSummonBoneMatrix () '` ✓

Every WOULD-BE-REFUTED condition fails to trigger: 0x18630 *does* reference summonModels
(0x220830), copies exactly 0x20 bytes, and the 0x16c80 stub does no matrix work.

## Nuance (non-refuting)
"32-byte PSX matrix" = the copied structure is 0x20 bytes and the per-bone stride is 0x20
(shl 5); a raw PSX GTE 3x3 s16 rotation is 18 bytes, so the 32-byte record presumably packs
rot+trans/pad. Descriptive only; the access path and copy size are exactly as claimed.
