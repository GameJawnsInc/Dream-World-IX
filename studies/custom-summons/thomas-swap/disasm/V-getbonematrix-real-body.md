# Adversarial verification: getbonematrix-real-body — CONFIRMED

Claim: real `Hi_GetSummonBoneMatrix` body @ **0x18630 (98B)**; the three string-xref sites
0x16c80 / 0x176ba / 0x18678 are cold panic tails, two of them owned by the byBone draw bodies.

Independently re-derived with refkit (fresh disasm), no reliance on prior evidence.

## String + xref sites (reproduced)
`FF9SpecialEffectPlugin.dll` string `0x4b418 'Hi_GetSummonBoneMatrix () '`, three `lea rdx` xrefs:
`0x16c80`, `0x176ba`, `0x18678`. `.pdata` ranges:
- 0x18630..0x18692 (98B) — one function; **0x18678 falls INSIDE it** (its own error tail).
- 0x16c80..0x16c9d (29B) — standalone funclet.
- 0x176ba..0x176d4 (26B) — inline tail inside body 0x171ef..0x17355.

## Real body @ 0x18630 (dll:0x18630)
Does the matrix copy and returns — refutes nothing:
```
sub rsp,0x28
movsxd rax,ecx            ; ecx = summon index
imul r9,rax,0x58          ; stride 0x58  (matches decoded array)
lea rax,[rip+0x2081ee]    ; -> RVA 0x220830  (summon model array base)
cmp byte [r9+rax+0x50],0  ; +0x50 active flag
je  0x18675               ; -> error tail
mov rax,[r9+rax]          ; +0x00 model DATA ptr
test rax,rax / je 0x18675
mov rax,[rax+0x38]        ; bone-matrix array base (data+0x38)
movsxd rcx,edx / shl rcx,5 ; edx = bone idx * 32
movups xmm0,[rcx+rax]      ; copy 32B (2 xmm) -> [r8] out
movups [r8],xmm0
movups xmm1,[rcx+rax+0x10]
movups [r8+0x10],xmm1
add rsp,0x28 / ret
0x18675: mov r8d,ecx; lea rdx,[rip+0x32d99](=the string@0x18678); lea rcx,..; call [rip+0x31a84]; call 0x151a0; int3
```
Each bone "matrix" here is **32 bytes** (2×xmm), array at `data+0x38`, indexed `bone*32`.
Real function: **called** from func 0xeea4 @ dll:0x1195a.

## The two draw-body funclets (dll:0x16c80, dll:0x176ba)
Both are pure `lea+lea+call panic; call 0x151a0; int3` stubs (no work):
- 0x16c80: branched to from body **0x16837** at je 0x168fa / je 0x16907.
- 0x176ba: branched to from body **0x171ef** at je 0x1732f / je 0x1733c.

All three panic paths end in the same `call 0x1800151a0` used by the real body's error tail.

## Verdict
CONFIRMED. 0x18630 performs the matrix copy + ret (98B); 0x16c80 (29B) & 0x176ba (26B) are
panic stubs branched from bodies 0x16837 / 0x171ef; 0x18678 is the real getter's own inline
error tail (not a separate funclet — CITED EVIDENCE correctly counts only two draw-body stubs).
No error-stub-vs-body confusion, no disasm desync, stride/base match the decoded array.
