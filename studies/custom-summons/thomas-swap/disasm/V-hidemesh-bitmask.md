# Verification: claim `hidemesh-bitmask` — CONFIRMED

Independently re-derived from FF9SpecialEffectPlugin.dll (x64, image base 0x180000000)
via fresh capstone disasm through refkit. No reliance on prior evidence.

## Hi_ShowSummonModelMesh @ RVA 0x187e0 (real body, not error stub)
```
0x187e0 sub    rsp, 0x28
0x187e4 movsxd rax, ecx                       ; ecx = model index (arg0)
0x187e7 imul   r8, rax, 0x58                   ; stride 0x58 -> record offset
0x187eb lea    rax, [rip + 0x20803e]           ; -> summon model array base RVA 0x220830
0x187f2 cmp    byte [r8+rax+0x50], 0           ; rec+0x50 = active flag
0x187f8 je     0x18817                          ; inactive -> panic tail
0x187fa mov    r8, [r8+rax]                     ; rec+0x00 = ptr to DATA block
0x187fe test   r8, r8
0x18801 je     0x18817                          ; null DATA -> panic tail
0x18803 mov    ecx, edx                         ; edx = mesh index (arg1)
0x18805 mov    eax, 1
0x1880a shl    eax, cl                          ; eax = 1<<mesh_index
0x1880c not    eax                              ; eax = ~(1<<mesh_index)
0x1880e and    dword [r8+0x20], eax             ; DATA+0x20 &= ~(1<<n)  => CLEAR bit
0x18812 add    rsp, 0x28
0x18816 ret
0x18817 ... panic tail; lea rdx,[rip+0x32c27] -> RVA 0x4b448 "Hi_ShowSummonModelMesh () "
```

## Hi_HideSummonModelMesh @ RVA 0x18840 (real body, not error stub)
```
0x18840 sub    rsp, 0x28
0x18844 movsxd rax, ecx
0x18847 imul   r8, rax, 0x58                    ; same stride 0x58
0x1884b lea    rax, [rip + 0x207fde]            ; -> same array base RVA 0x220830
0x18852 cmp    byte [r8+rax+0x50], 0            ; rec+0x50 = active flag
0x18858 je     0x18875                           ; panic tail
0x1885a mov    r8, [r8+rax]                      ; rec+0x00 = ptr to DATA block
0x1885e test   r8, r8
0x18861 je     0x18875
0x18863 mov    ecx, edx
0x18865 mov    eax, 1
0x1886a shl    eax, cl                           ; eax = 1<<mesh_index
0x1886c or     dword [r8+0x20], eax              ; DATA+0x20 |= (1<<n)   => SET bit
0x18870 add    rsp, 0x28
0x18874 ret
0x18875 ... panic tail; lea rdx,[rip+0x32bf9] ... "Hi_HideSummonModelMesh () " @ RVA 0x4b478
```

## Claim-by-claim check
- Offset: BOTH operate on `[DATA_block + 0x20]` (DATA block = qword at rec+0x00), NOT any other
  offset. `imul ...,0x58` + base 0x220830 + `mov r8,[r8+rax]` matches the calibrated array layout
  (stride 0x58, +0x00 = DATA ptr, +0x50 = active flag). ✔
- Hide (0x1886c): `or dword[r8+0x20], (1<<cl)` — SETS the bit. ✔ (cited 0x1886c exact)
- Show (0x1880e): `and dword[r8+0x20], ~(1<<cl)` (`not eax` at 0x1880c precedes) — CLEARS the bit. ✔
  (cited 0x1880e exact)
- Bit-set == hidden: Hide sets, Show clears — semantics consistent with "set = hidden". ✔
- Identity: Show's panic name-string lea resolves exactly to RVA 0x4b448 "Hi_ShowSummonModelMesh";
  Hide's names "Hi_HideSummonModelMesh" (both strings present @ 0x4b448/0x4b478). These are the
  REAL bodies (they do the bitmask work inline; the panic is only the fall-through error tail), NOT
  the cold error funclet. ✔

## Refutation attempts (all failed to refute)
- Wrong offset? No — both use +0x20, confirmed by fresh disasm.
- Inverted semantics? No — Hide=or/set, Show=and-not/clear, exactly as stated.
- Error-stub confusion? No — these functions execute real logic before any panic; the funclet trap
  does not apply here.

VERDICT: CONFIRMED. Cited RVAs (0x1880e, 0x1886c) and mechanism reproduce byte-for-byte.
