# Adversarial verification — claim `dispatch-interpreter`

**Verdict: CONFIRMED** (one section-name correction: the table is `.data`, not `.rdata`).

Re-derived independently with `verify_dispatch.py` (this dir). I did NOT reuse the prior
`a1_callers.py` output. `refkit.xrefs_to` only catches RIP-relative operands (string `lea`s),
so it MISSES `call rel32` — I built my own call/jmp target map by disassembling every one of
the 646 `.pdata` functions with capstone, plus a full-image qword scan for code pointers.

All RVAs image-relative (`ImageBase = 0x180000000`).

## Claim restated
1. Every summon `Hi_*` fn is called from exactly one site inside the mega-interpreter
   `[0xeea4..0x12321]`.
2. Each handler entry is also stored in a `.rdata` fn-ptr table spanning `~0x68780..0x68cf8`.
3. Refuted by: a summon `Hi_*` with a direct caller outside `0xeea4`/init-paths, OR its
   entry absent from the `0x68780`-region table.

## Result — reproduced, matches the prior agent to the byte

The interpreter `[0xeea4..0x12321]` is exactly **one** `.pdata` RUNTIME_FUNCTION
(size 13437 B, in `.text`). All 12 summon entries have **exactly one** call site, and it
falls inside that range:

| fn | entry | interp call site | table slot |
|----|-------|------------------|-----------|
| Hi_RegisterSummonModel | 0x15ee0 | 0xf75a | 0x68838 |
| Hi_DrawSummonModel | 0x17710 | 0xf851 | 0x68848 |
| Hi_SetSummonMotion | 0x17a10 | 0xf87e | 0x68850 |
| Hi_SetSummonMotFrame | 0x17a70 | 0x10d6a | 0x68aa0 |
| Hi_GetSummonBonePos | 0x185b0 | 0x115cb | 0x68c28 |
| Hi_GetSummonBoneMatrix | 0x18630 | 0x1195a | 0x68ca0 |
| Hi_ShowSummonModelMesh | 0x187e0 | 0x117df | 0x68c68 |
| Hi_HideSummonModelMesh | 0x18840 | 0x11806 | 0x68c70 |
| Hi_StartSummonTexAnim | 0x188a0 | 0xf439 | 0x687e0 |
| Hi_StopSummonTexAnim | 0x18930 | 0xf408 | 0x687d8 |
| Hi_ModifySummonModelAbr | 0x18af0 | 0x1157a | 0x68c18 |
| Hi_ModifySummonModelRGB | 0x18b50 | 0x10106 | 0x68988 |

Every in-interp caller RVA ∈ `[0xeea4, 0x12321]` ✓. Every table slot ∈ `[0x68780, 0x68cf8]` ✓
(observed span of summon slots: 0x687d8..0x68ca0). My full-image qword scan found each entry
pointer appearing **exactly once** in the whole image — always in the table, never elsewhere.

## The only outside callers (do NOT refute)
`Hi_RegisterSummonModel` alone has 2 callers outside the interpreter: **0x3e44e** (in fn
0x3de37) and **0x47491** (in fn 0x47330). Both are genuine **init/preload** paths, not a
second dispatcher: each site calls `0x15ee0` and immediately stores the returned slot index
to a global (`0x3e453: mov [rip+0x2e4df7], eax`; `0x47496 region: mov [rip+0x2dbda5], eax`).
Neither function references summon debug strings; both are one-shot setup. This is exactly the
claim's carve-out ("outside 0xeea4/**init-paths**"), so it does not refute. All other 11 fns
have zero callers outside the interpreter.

## Correction (does not change the verdict)
The claim calls the table `.rdata`. It is actually in **`.data`** (writable section,
Characteristics IMAGE_SCN_MEM_WRITE set). Confirmed: `_section_for_rva(0x68780)` → `.data`,
`_section_for_rva(0x68ca0)` → `.data`. The table's location, span, and contents are all as
claimed — only the section label is wrong. (Consistent with MSVC placing an array of runtime
pointers that may be relocation-patched into initialized writable data.)

## Reproduce
`py verify_dispatch.py` — prints the caller map + table-slot map above.
Section check: `refkit._section_for_rva(pe, 0x68780).Name` → `.data`.

Provenance: read-only static analysis of the user's installed DLL. RVAs/mnemonics/section
names only; no game bytes extracted, no DLL modified.
