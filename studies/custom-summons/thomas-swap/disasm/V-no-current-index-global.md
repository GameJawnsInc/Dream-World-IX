# Adversarial verification: `no-current-index-global`

**Verdict: CONFIRMED** (independently re-derived from FF9SpecialEffectPlugin.dll x64 with refkit; error-stub-vs-real-body distinguished; no scratch-buffer/endianness assumption involved).

Claim under test: *There is no dedicated current-summon-index global; the record index is
supplied as a caller argument and Register only fills slot 0.*

Summon record array base = RVA **0x220830**, stride **0x58**, `+0x50` = active flag (verified
by re-deriving the RIP targets, not trusting the prior note).

## 1. Every accessor sign-extends the index from an ARGUMENT register — never a memory load

Fresh disassembly of each real body (RVAs are file/image-relative, image base 0x180000000):

| Function (real body) | index instruction | index source |
|---|---|---|
| Hi_SetSummonMotion @0x17a10 | `0x17a14 movsxd rax, edx` | arg2 (edx) |
| Hi_SetSummonMotFrame @0x17a70 | `0x17a74 movsxd rax, ecx` | arg1 (ecx) |
| Hi_GetSummonBonePos @0x185b0 | `0x185b4 movsxd rax, ecx` | arg1 (ecx) |
| Hi_GetSummonBoneMatrix **real body @0x18630** | `0x18634 movsxd rax, ecx` | arg1 (ecx) |
| Hi_ShowSummonModelMesh @0x187e0 | `0x187e4 movsxd rax, ecx` | arg1 (ecx) |
| Hi_HideSummonModelMesh @0x18840 | `0x18844 movsxd rax, ecx` | arg1 (ecx) |
| Hi_StartSummonTexAnim @0x188a0 | `0x188a4 movsxd rax, ecx` | arg1 (ecx) |
| Hi_StopSummonTexAnim @0x18930 | `0x18934 movsxd rax, ecx` | arg1 (ecx) |
| Hi_ModifySummonModelAbr @0x18af0 | `0x18af4 movsxd r9, ecx` | arg1 (ecx) |
| Hi_ModifySummonModelRGB @0x18b50 | `0x18b57 movsxd r8, ecx` | arg1 (ecx) |
| big draw/setup func @0x167f0 | `0x16802 movsxd rsi, r8d` → used `0x168f1 imul rax, rsi, 0x58` | arg3 (r8d) |
| draw/setup func @0x171ef | `0x17314 movsxd r8, dword ptr [rsp+0x80]` → `0x17326 imul rax, r8, 0x58` | 5th stack arg |

Each site is immediately followed by `imul …, …, 0x58` + `lea …, [rip+…]` (RIP target
re-computed = 0x220830) + `cmp byte ptr [… + 0x50], 0`. In **none** of them is the index
`movsxd`/`mov`'d from a `[rip+disp]` global; it is always a calling-convention argument
register (ecx/edx/r8d/r9d) or a spilled incoming **stack** argument (`[rsp+0x80]`). The
error-stub funclets (e.g. Hi_GetSummonBoneMatrix @0x16c80, 29 bytes) were excluded — the
real bodies were located via the base-0x220830 xref set, not the string xref.

## 2. Register @0x15ee0 fills slot 0 only (loop bound = 1)

Real body confirmed at **0x15ee0** (85 bytes); the 52-byte range @0x16112 that carries the
`Hi_RegisterSummonModel` error string is the malloc/full funclet, not the body.

```
0x15ef7 xor edi, edi              ; edi = 0
0x15eff mov eax, edi              ; eax = 0  (loop counter)
0x15f01 lea rbx, [rip+0x20a928]   ; rbx -> 0x220830 (slot 0)
0x15f08 cmp byte ptr [rbx+0x50], dil   ; slot active?
0x15f0c je  0x15f1e               ; free -> register here
0x15f0e inc eax
0x15f10 add rbx, 0x58
0x15f14 cmp eax, 1
0x15f17 jl  0x15f08               ; loop WHILE eax < 1  => only eax==0 iterates
0x15f19 jmp 0x16112               ; all(=1) slots full -> error funclet
0x15f1e ...                       ; slot 0: set [rbx+0x50]=1, zero [rbx+0x54]
```

The free-slot scan runs a single iteration (`cmp eax,1; jl`), so the effective array
capacity searched by Register is **1** and only slot 0 is ever written. No index global is
read or written.

## 3. Writes to base 0x220830 are direct slot-0 field writes (reinforce, not refute)

`xref_index`/`xrefs_to(0x220830)` also surfaces write sites 0x30cc9 (`mov [rip+…],rbx`) and
0x47449 (`mov [rip+…],rax`) that resolve to 0x220830 exactly — these are init/reset routines
storing directly into slot-0 fields (r15/rbx typically 0), i.e. hardcoded slot-0 addressing.
That is consistent with a slot-0-only design and is **not** an index global. (The 0xf90d hit
falls inside a linear-disasm desync region of the 0xeea4 mega-function and is data/mid-insn.)

## Refutation attempted, not found
The claim would be refuted by a global loaded and used as the record index. No summon
accessor loads its index from `.data`/`.bss`; all read it from an argument. If a "current
summon" index exists at all, it lives on the **managed (C#) caller** side and is passed in as
an argument — which is exactly what the claim states. Confirmed.
