# Adversarial verification — CLAIM `hide-mask`

**Verdict: CONFIRMED** (independently re-derived from the DLL, fresh disasm via refkit).

## Claim under test
Mesh-visibility mask is a `u32` at `SummonData+0x20`; SET bit = mesh hidden.
`ShowSummonModelMesh` clears bit `meshIdx`, `HideSummonModelMesh` sets it — the native
equivalent of the `.seq HideMeshes` lever.

## What I did
Located the two functions by their leftover error-diagnostic strings, then disassembled the
**full function bodies** (not the cited mid-body RVAs alone) to rule out error-stub confusion
and linear-disasm desync.

- `'Hi_ShowSummonModelMesh () '` @ `0x4b448`, xref'd (lea) only from `0x1881a` — inside `0x187e0..0x18834`.
- `'Hi_HideSummonModelMesh () '` @ `0x4b478`, xref'd (lea) only from `0x18878` — inside `0x18840..0x18892`.

The cited RVAs `0x18803`/`0x18863` fall inside these real bodies. The string `lea` sits on the
**malloc/validation-fail path**, not in a separate cold funclet — so here the "error stub that
names the fn" and the real body are the SAME `.pdata` range. No stub-vs-body confusion.

## Fresh disassembly (reproduced verbatim)

### ShowSummonModelMesh `0x187e0..0x18834`
```
sub    rsp, 0x28
movsxd rax, ecx                       ; ecx = arg0 = summon index
imul   r8, rax, 0x58                  ; * stride 0x58  (matches calibration)
lea    rax, [rip + 0x20803e]          ; @0x187eb → base 0x220830  (verified: 0x187f2+0x20803e)
cmp    byte ptr [r8 + rax + 0x50], 0  ; rec+0x50 active flag
je     0x18817                        ; -> error path
mov    r8, qword ptr [r8 + rax]       ; r8 = [rec+0x00] = ptr to DATA block
test   r8, r8
je     0x18817                        ; -> error path
mov    ecx, edx                       ; edx = arg1 = meshIdx
mov    eax, 1
shl    eax, cl                        ; eax = 1 << meshIdx
not    eax                            ; eax = ~(1 << meshIdx)
and    dword ptr [r8 + 0x20], eax     ; CLEAR bit meshIdx  at DATA+0x20
add    rsp, 0x28
ret
; 0x18817: error path -> lea rdx,->string ; call panic ; int3
```

### HideSummonModelMesh `0x18840..0x18892`
```
sub    rsp, 0x28
movsxd rax, ecx
imul   r8, rax, 0x58
lea    rax, [rip + 0x207fde]          ; @0x1884b → base 0x220830 (verified: 0x18852+0x207fde)
cmp    byte ptr [r8 + rax + 0x50], 0
je     0x18875
mov    r8, qword ptr [r8 + rax]       ; r8 = ptr to DATA block
test   r8, r8
je     0x18875
mov    ecx, edx                       ; meshIdx
mov    eax, 1
shl    eax, cl                        ; 1 << meshIdx
or     dword ptr [r8 + 0x20], eax     ; SET bit meshIdx  at DATA+0x20
add    rsp, 0x28
ret
; 0x18875: error path
```

## Point-by-point

| Refutation condition (from the claim) | Observed | Result |
|---|---|---|
| Show setting bits | Show does `not eax` then `and` = **clears** | not refuted |
| Hide clearing bits | Hide does `or` = **sets** | not refuted |
| Mask at an offset other than +0x20 | Both `and`/`or` target `[r8+0x20]` | not refuted |

- **Base/stride** independently reproduced from BOTH functions' `lea`: `0x220830`, stride `0x58`
  (`0x187f2 + 0x20803e = 0x180220830`; `0x18852 + 0x207fde = 0x180220830`). Matches the
  SetSummonMotion-derived calibration.
- **SET = hidden** is self-consistent: Hide sets, Show clears; the `.seq HideMeshes=<hex>` first
  native use writes exactly this bit pattern into the same word.

## One precision note (not a refutation)
The mask is at **DATA-block + 0x20**, reached via the record dereference `mov r8,[rec+0x00]` —
NOT at record+0x20 of the 0x58-stride record. The claim says "SummonData+0x20", and A2 defines
`SummonData` as the nested DATA block (rec+0x00 → SummonData), so the wording is consistent.
Anyone reading "SummonData" as the 0x58-stride record would be off by one indirection; A2's own
struct map (§2, lines 84-88) resolves this correctly.

## Provenance
Read-only analysis of `FF9SpecialEffectPlugin` (x64) via refkit/capstone. No bytes extracted,
no DLL produced. All RVAs are image-relative (0x1800187e0 base = 0x180000000).
