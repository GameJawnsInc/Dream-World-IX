# Adversarial verification: CLAIM pattern-b-drawregister

**Verdict: PARTIAL** — the Draw* half is CONFIRMED and well-evidenced; the universal
"**All** ... Register*" generalization is REFUTED by the Register*EffModel family.

All RVAs are image-relative (`refkit.load()` x64; base 0x180000000). Re-derived fresh with
refkit `disasm` / `find_strings`, not from prior artifacts.

## What the STATEMENT claims
A 3-part layout for **all** Draw* and Register* Hi_ functions:
1. **validator entry** = the dispatch-table-facing range (small; refs the model array; `je` to stub)
2. **cold-split body** = "the range immediately below it" (callers=0, real work)
3. **separate error stub** = a distinct 29B .pdata range that carries the fn-name string + panics.

## CONFIRMED — the Draw* trios (both cited examples reproduce exactly)

### Hi_DrawSummonModel — 0x17710 / 0x17740 / 0x179f2
- **Entry 0x17710 (48B)** — validator on the SUMMON array:
  `imul rdi, rax, 0x58` (stride 0x58 ✓); `lea rax,[0x220830]` (SUMMON base ✓);
  `cmp byte [rdi+0x50],0 ; je 0x179f2`; `mov rcx,[rdi] ; test rcx,rcx ; je 0x179f2`.
  Preserves rcx→r10 (0x17719) which the body consumes at 0x1775a → proves entry+body are ONE
  MSVC-split function. Falls through into 0x17740.
- **Body 0x17740 (690B, callers=0)** — saves rbx/rbp/rsi/r12/r14/r15, `call 0x186a0`,
  `mov rax,[rdi]` … real draw work. Reached only by fall-through.
- **Stub 0x179f2 (29B)** — `lea rdx,->0x4b2e8 'Hi_DrawSummonModel()'`; `lea rcx,->0x220890`(DBGCTX);
  `call [0x4a110]`(panic import); `call 0x151a0`(shared err-report); `int3`.

### Hi_DrawEffModel — 0x16150 / 0x16184 / 0x16547
- **Entry 0x16150 (52B)** — validator on the EFFARR array (stride 0x30: `lea rax+rax*2; shl 4`);
  `lea rax,[0x220230]`; `cmp byte [rdi+0x20],0 ; je 0x16547`; `mov rcx,[rdi]; test; je 0x16547`.
- **Body 0x16184 (963B, callers=0)** — real work.
- **Stub 0x16547 (29B)** — `lea rdx,->'Hi_DrawEffModel()'`; `->0x220890`; `call [0x4a110]`;
  `call 0x151a0`; `int3`.

The roster (a1_table.py, reproduced) shows the same 29B-stub signature for the rest of the Draw*
family: DrawSliceEffModel 0x167cd, DrawMorphEffModel 0x17156(entry)+stub, DrawEffModelByBone 0x16c9d,
DrawMorphModelByBone 0x176d4, GetSummonBoneMatrix 0x16c80/0x176ba. The Draw* pattern is real.

## REFUTED — the Register*EffModel family are UNIFIED functions (inlined error tail)

The STATEMENT's own refutation clause: *"A Draw*/Register* whose string-bearing range is the
actual work body rather than a small panic stub."* That is exactly what these are.

### Hi_RegisterSolidEffModel — 0x15ac0 (166B), single function
Disassembly of the *string-bearing* range is the real registrar:
- 0x15acc `lea rbx,[0x220230]` (EFFARR) → loop of 0x20 records stride 0x30 scanning `[rbx+0x20]`
  for a free slot (0x15ad5..0x15ae4).
- On hit: `mov word[rbx+0x20],1` (mark used), `call 0x12940` (model load), `mov [rcx+8],eax`,
  `mov [rax+0x10],rdi`, `call 0x7120`, returns the slot handle `movzx eax,[rbx+0x22]; ret` @0x15b31.
- **Error path is INLINE at the tail**, reached by `jmp 0x15b32` (no free slot) / `je 0x15b4c`:
  `lea rdx,->'Hi_RegisterSolidEffModel()'; ->0x220890; call [0x4a110]; call 0x151a0; int3`.
  It is in the **same .pdata range**, NOT a separate 29B stub.

### Hi_RegisterGouEffModel — 0x15b70 (170B), same unified shape
Normal-return `ret` @ 0x15be5 sits BEFORE two inlined panic tails
(`'Hi_RegisterGouEffModel()'` @ 0x15be6 and @ 0x15c00) — same range, inlined, no split stub.

By roster the rest of the family is identically large & string-bearing (not 29B):
RegisterTexEffModel 0x15c20 (260B), RegisterTexListModel 0x15d30 (214B),
RegisterTexPtrModel 0x15e10 (197B), FreeEffModel 0x159a0 (74B). None are the 3-part split.

### Hi_RegisterSummonModel — string range is a stub PAIR, body is ABOVE not below
- The RegisterSummonModel **string range 0x16112 (52B)** is *two* concatenated 29B error stubs
  (`0x16112` and `0x1612c`), each `lea ->'Hi_RegisterSummonModel()'; ->0x220890; call [0x4a110];
  call 0x151a0; int3`. It carries no validator and no fall-through body.
- Its real work body is **0x1606c (166B)**, sitting *immediately ABOVE* the string range
  (ends `call 0x491b0; ret` @0x16111). So even the "body is the range **immediately below**" sub-claim
  is false here — the body is above, and 0x16150 (below) is a *different* function (DrawEffModel's entry).

## Bottom line
- The validator-entry / cold-body / 29B-separate-stub triad is a genuine, reproducible layout for the
  **Draw\*** summon/eff functions (cited examples exact).
- It is **NOT** the layout of the **Register\*** functions: RegisterSolid/Gou/Tex/TexList/TexPtr-EffModel
  are single unified functions with inlined error tails (string range = work body), and RegisterSummonModel
  splits into a stub-pair + body-above. The word "All" and "Register\*" over-generalize.
- No impact on the summon-transform authoring goal: this is purely a code-shape taxonomy claim.
