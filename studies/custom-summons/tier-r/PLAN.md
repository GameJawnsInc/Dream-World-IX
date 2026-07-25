# TIER R — THE DECODE LADDER (the effect PROGRAM becomes readable)

> **The strategy line this executes** (custom-summons memory, minted at the transplant close):
> *"invest in TIER R (probe → inspector → MIPS disassembler = 'decodable')"*. The probes exist
> (s52/s53, permanent instruments). This study builds the other two thirds.

**THE TARGET.** THE FORMAT ROUND (`../thomas-swap/disasm/FORMAT.md`) decoded every layer of the ef
container except one: **resource id-3, the effect PROGRAM** — raw little-endian **MIPS R3000A + full
PlayStation GTE (COP2)** machine code inside PS1 main-RAM images. 385 images corpus-wide; ~7,400
instructions for Bahamut (ef227), organized as entry-point programs (ef227: chunk 0 prog 0 @ image
`0x9d4`, chunk 1 prog 0 @ `0x108c`). **This is the choreography** — the code that drives the bones,
emits the primitives, moves the native camera, and re-points the view matrix mid-cast. Reading it is
the difference between *watching* a stock summon through probes and *understanding* it.

**WHY (what "decodable" buys).** TIER W's cheap half (edit stock summons in place — rescore camera,
retime, reskin) needs to know what the program does before any byte of it is patched. The transplant
lane's next beauty pass (a designed creature on Bahamut's real cinematic) needs the phase structure.
And every falsified flight hypothesis (v1→v10.1) died for want of exactly this readability.

---

## The ladder

| Rung | Deliverable | Gate (falsifiable) |
|---|---|---|
| **R0** | The recon brief — priors consolidated (execution model, the 16 program offsets, what C8 built, the HLE/global boundary, GTE surface, corpus layout, validation instruments) | every claim carries a FORMAT-round citation |
| **R1** | **THE DISASSEMBLER** — committable, reachability-driven R3000A+GTE decoder over the PS1-RAM image model (capstone-MIPS for the integer ISA; custom GTE command-word decode) | **385/385 corpus walk from the program offsets; 0 invalid instructions in reachable code; closure stats reported**; a linear sweep is the documented ANTI-pattern (code/data interleave) |
| **R2** | **THE ANNOTATOR** — names the boundary: HLE stubs / memory-mapped globals (OFX `0x211fa0`, view matrix `0x1C1DC8`, the PSX-RAM cursor, …), data refs into the already-decoded resources (camera sub-file, motion clips, model tables), per-function role table | ef227's known functions land where the probes said (`SFX_Update` work body, the GTE RTPS body); every annotated global cross-checks the FORMAT memory map |
| **R3** | **THE INSPECTOR** — `summon-inspect <ef>`: an annotated choreography report | **ef227 CHOREOGRAPHY.md explains the OBSERVED phases (float / charge / beam / fire-column; creature window 82–412) from the code**, validated against the archived s53 capture — the calibrated instrument, not a narrative |

**Done = "decodable":** a person (or agent) can open the inspector's report for a stock summon and
answer "what happens at frame N and which code does it" without a debugger.

---

## Provenance (the FORMAT round's posture, unchanged)

- **Committable:** the disassembler, the annotator, the inspector, this study's docs — parsers and
  tools, zero SE bytes.
- **SCRATCH-only, never committed:** the extracted `ef###.bytes` images, disassembly LISTINGS of
  stock code, capture logs — all under `C:\gd\SCRATCH\summon-format\` / `C:\gd\SCRATCH\summon-transplant\`.
- RE-to-understand is sanctioned; never ship a patched DLL; probes stay default-OFF.

## R0 — RATIFIED 2026-07-25 (the recon's load-bearing findings)

1. **Execution = a table-driven MIPS interpreter inside `FF9SpecialEffectPlugin.dll`** (pre-decoder
   `fn 0xd1a0` matches words against the DLL's own **99-entry mask/match ISA table @RVA `0x66c70`**;
   interpreter `fn 0xe210`, 90-entry dispatch @`0xed18`). **No recompiled x64 twin exists** — but the
   ISA table is a BETTER ground truth: R1's decoder is validated against the interpreter's own
   accepted encodings, not a spec's opinion of them.
2. **Reachability seeds already exist**: per-image 16-entry program table at `headerRel+8`, exposed by
   `../thomas-swap/disasm/ef_container.py` `parse_chunk_image → ChunkImage.program_offsets`. Corpus:
   **385 id-3 images / 599 live entries** (1–7 per image), 372 `ef###.bytes` at `C:\gd\SCRATCH\summon-format\`.
3. **The C8 seed is validation-only** — linear-sweep, format-unaware, capstone-MIPS never wired.
   Reuse: the `0x66c70` table extraction (`c8_a.py`/`c8_final.py`) + the 589/599 prologue census
   (`c8_ep.py`). The printer is throwaway.
4. **HLE boundary**: the MIPS program JALRs through a DLL-synthesized 216-sentinel table
   (`0xFF000000|i`, .data RVA `0x68250`); trap at `fn 0xec31`. **The table's PSX base constant is
   UNREAD** (`0x21FF78` vs `0x21FF7C`, published at `0x30d2e/0x30d39`) — resolve STATICALLY in R1 by
   disassembling the two publisher stores; only 12 of 216 HLE ops are named (`M3-opcode-table.json`).
5. **GTE cofun field decode does not exist anywhere in-repo** — author from the PS1 GTE spec, validate
   against the DLL's own COP2-cofun handler body (which fields the shipping implementation extracts).
6. **Validation instruments**: the s53 capture rows (PSXCAM/MODEL/BONES in the archived probe logs),
   creature window **f82–417** (corrected from 82–412), FORMAT §5.4's 35–45% PRIM-AABB prediction, the
   PsxCtx tamper check, `hasMotion==1`-only-on-`kind=S`. `fn[0x13c4..]`/`fn[0x3e80..]` are DLL x64
   RVAs, NOT MIPS offsets — never conflate the two address spaces.

## Status

- R0 — ★ DONE (above).
- R1 — IN FLIGHT: the reachability disassembler (gates: 385/385 images × 599 entries walk; 0 invalid
  reachable instructions; delay slots modeled; every JALR target in-image or HLE-trapped; coverage vs
  `headerRel` reported per image — the ef508/ef210 embedded-data files are the canary).
- R2/R3 — pending R1.
