# VERIFY cam13-layout — CONFIRMED (with one annotation caveat)

Claim: PSX int16 GTE camera struct @RVA `0x69730` → 13 contiguous floats @RVA `0x211df0`.
Independently re-derived from `FF9SpecialEffectPlugin.dll` (x64, base `0x180000000`) by fresh
capstone disasm of the function `0x1e80–0x2030` (which contains the cited `0x1f1c–0x2022`).

## The conversion routine (`sub_1e80`)
This is a self-contained converter: read a PSX-style camera struct, widen each field to `float`,
store 13 floats to a contiguous array, and `ret` a pointer to that array (`lea rax,[0x211df0]` @`0x2010`).

Two read paths exist; the `[0x20ff7d]==1` special-case branch (`0x1ea9`) reads a DIFFERENT source
(`0x211e48/50/54/58`, i.e. the float-array region itself — a default/copy path) into `0x67850`.
The MAIN path (else, `0x1f01`) is the one that reads the GTE int-struct at `0x69744+`. Both converge
at `0x1f1c` for the rotation reads. The cited claim concerns the GTE-struct read + conversion — reproduced below.

### Source struct @ RVA 0x69730 (all RIP targets recomputed fresh)
| field | offset | RVA | read op @ | width/sign |
|---|---|---|---|---|
| rot[0] | +0x00 | 0x69730 | movsx `0x1f1c` | int16 signed |
| rot[1] | +0x02 | 0x69732 | movsx `0x1f27` | int16 signed |
| rot[2] | +0x04 | 0x69734 | movsx `0x1f32` | int16 signed |
| rot[3] | +0x06 | 0x69736 | movsx `0x1f48` | int16 signed |
| rot[4] | +0x08 | 0x69738 | movsx `0x1f5e` | int16 signed |
| rot[5] | +0x0a | 0x6973a | movsx `0x1f74` | int16 signed |
| rot[6] | +0x0c | 0x6973c | movsx `0x1f8a` | int16 signed |
| rot[7] | +0x0e | 0x6973e | movsx `0x1fa0` | int16 signed |
| rot[8] | +0x10 | 0x69740 | movsx `0x1fb6` | int16 signed |
| TRX | +0x14 | 0x69744 | mov ecx `0x1f16` | int32 |
| TRY | +0x18 | 0x69748 | mov edx `0x1f10` | int32 |
| TRZ | +0x1c | 0x6974c | mov r8d `0x1f09` | int32 |
| H | +0x20 | 0x69750 | movzx r9w `0x1f01` | **int16 unsigned** |

Note the gap +0x12 (0x69742) is unread padding between the 9-int16 rotation block (ends at 0x69741)
and the int32-aligned translation block (starts 0x69744). Consistent with GTE `SVECTOR`+alignment.

### Dest array @ RVA 0x211df0 (13 contiguous floats, all `movss`, step 4)
`0x211df0,4,8,c, 0x211e00,4,8,c, 0x211e10` = array[0..8] = rotation (via cvtdq2ps of the movsx values);
`0x211e14` = array[9] = TRX (ecx), `0x211e18` = array[10] = TRY (edx), `0x211e1c` = array[11] = TRZ (r8d),
`0x211e20` = array[12] = H (r9w). All 13 slots contiguous, no gaps. Matches the claim byte-for-byte.

## Offsets & field count — the stated refutation condition
"WOULD BE REFUTED BY: different offsets or field count." Every offset (+0x00..+0x20 source,
+0x00..+0x30 dest) and the field count (13) reproduce exactly. **NOT refuted.**

## Caveat on "(fixed /4096)"
The `/4096` fixed-point annotation on the rotation entries is NOT present in the cited byte range
(`0x1f1c–0x2022` performs only `movsx`→`cvtdq2ps`→`movss`, i.e. int16→float with NO scale). It is
a *format convention* (PSX GTE rotation matrices are 1.3.12 fixed = /4096), consistent with the
signed `movsx` read, but the divide — if it happens — is downstream in a consumer of the returned
`&array[0]` pointer, not in this function. So the layout/field-count/sign claims are CONFIRMED from
the cited evidence; the `/4096` is a plausible convention annotation, not directly evidenced here.

## Provenance
Understanding-only. No stock bytes reproduced (the source RVA 0x69730 and dest 0x211df0 sit in the
runtime .data region; only the code LAYOUT/logic is cited, all by file:rva).
