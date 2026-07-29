# QUAD-ORDER FIX — ★ APPLIED (owner cleared it: the ef211 casts closed, ladder moved to ef446)

> The kit defect UV-ANALYSIS.md §6 named is FIXED at the source: `repaint._face_polys` and
> `summons.build._mesh_tris` now emit the Z fan `(0,1,2) + (1,3,2)`. The study-record edits this
> note staged are **now applied** — W6b-SCENERY.md (§0 calibration note, F4 row, appendix),
> W6-TEXEL.md §1.4 (all six moving counts + the A2-rect-product vindication), `phoenix_field.toml`'s
> comment table — each naming the old (perimeter-fan) number beside the Z-fan value. This file stays
> as the provenance record those annotations point to.

## 1. The measurement that keyed the fix (archived: `SCRATCH/summon-format/repaint-w6b/quad-order/`)

Both fans scored for winding consistency on every 4-corner primitive, 372 containers, per bucket,
in UV space and (same-bone quads) in 3D — `phoenix_pool_stamp.quad_order_evidence`'s discriminator
at corpus scale:

| family, bucket | space | Z-consistent | perimeter-consistent |
|---|---|---:|---:|
| creature FT4 | UV | **5,469** | 0 |
| creature FT4 | 3D | **5,496** | 0 |
| scenery FT4 | UV | **14,720** | 8 |
| scenery GT4 | UV | **9,536** | 5 |
| scenery G4 / F4 | 3D | **3,521** | 1 |

0 of 612 quad-bearing geoms lean perimeter — so `build._mesh_tris`' "creatures are
perimeter-ordered" was equally false, and ONE rule covers every bucket. (FORMAT.md §2.3 never
stated a corner order; the claim lived only in the two docstrings.)

## 2. What the re-measure says (A/B, `remeasure.py` + `remeasure.json` in the same SCRATCH dir)

**Calibration:** the perimeter fan reproduces the shipped `w6b_gates.PIN` table exactly, all 34 keys.

**ZERO census pins move under the Z fan.** No cell gains or loses a reader corpus-wide — the fix
changes cover *density* inside already-attributed cells, never attribution. `depth_unknown` 2,385,
the whole spill family (58/41/17/0, UV-exact 70, unwritten 8), `shared_read` 93, every class count:
all stand. **`CAST_COVER` (704,256) stays 8,128** — the cell is all-FT3 — so
`PHOENIX_STAMP_PNG_SHA256` / `PHOENIX_STAGED_SHA256`'s inputs are untouched and the board should
re-run 7/7 as-is. Corpus-wide, 110 of 340 `so`-bound models move, +73,626 halfwords net (one model,
ef424 `0x29f98`, LOSES 8 — the bowtie's wrong triangle marked texels outside its quad).

## 3. The published numbers that moved — all edits applied

| where | published (perimeter fan) | correct (Z fan) |
|---|---|---|
| W6b-SCENERY.md appendix + F4 row, x640_y256 union (+ `phoenix_field.toml` comment) | 5,737 | **6,080** |
| W6-TEXEL.md §1.4, ef211 col-640 class-C shared set | 1,659 | **2,016** |
| §1.4 col 448, `0xbb0e8` × `0xc2264` | 3,294 | **4,032** |
| §1.4 col 448, `0x8d888` × `0xc2264` | 2,729 | **4,032** |
| §1.4 col 448, `0x8fc20` × `0xc2264` | 2,750 | **4,032** |
| §1.4 col 576, `0x29e14` × `0x2ba28` | 2,444 | **3,024** |
| §1.4 col 576/640, `0xbe030` × `0x29e14` | 11,710 | **12,544** |

The seventh §1.4 count (col 832, FT3-only) stands at 4,064. The pair-sweep A/B
(`pair-sweep.txt` in the SCRATCH dir; old fan reproduces every published value) also shows the
pair-CLASS census is fan-independent — 1,083 overlapping pairs / 36 effects, 79 mixed-depth / 6,
390 different-palette / 11, 614 same-palette / 33 all stand: no intersection went empty ↔
non-empty, only sizes moved. And a vindication: A2's col-448 "rect product 4,032", which §1.4 had
corrected down to 3,294, was the true polygon cover all along — the 3,294 was the bowtie.

Per-reader, the only ef211 mover is the pool arc `geom 0x2ed7c`: 3,332 → **4,032** (+700, 17.4% —
exactly UV-ANALYSIS §6's number). `0x2d344` (FT3) holds 4,064; x576_y256 holds 3,584 (3,136 +
448); x576_y384 holds 2,688; x704_y256 holds 8,128. All other appendix rows stand.

## 4. What this means for the running cast (nothing retroactive, one label corrects)

- **The cast-3 stamp's zones stand as computed.** UV-ANALYSIS §3's partition was built from the
  stamp's own Z fan and reconciles exactly against the fixed kit: arc-only 2,016 = 4,032 − 2,016,
  cone-only 2,048 = 4,064 − 2,016. Only its "SHARED 1,659" line carried the kit's stale fan — the
  Z-fan shared set is **2,016**.
- The pool spec's "**238 texels outside the cover**" disclosure quoted *the defect, not a stray
  edit* — after this fix the kit's cover includes them, and that sentence retires.
- No deployed artifact changes: covers are measurements, not bytes on disk.

## 5. Already landed kit-side (not waiting on this note)

`_face_polys` + `_mesh_tris` fixed with the census in their docstrings; both synthetic test
fixtures re-authored in Z order; ef227's pinned creature census updated 65,267 → 65,298 covered /
part-5 holes 33 → 2 (bowtie wedges had been reading as interior holes), old predicate named in the
comment; CHANGELOG entry under [Unreleased]; kit summon tests green.

## 6. Late-found movers — the CREATURE-side mean, cross-branch (resolved post-W6b-3i)

The remeasure above ran on master; the W6q board (`w6q_gates.py`) lived on the recon lane
(`claude/summon-work-orchestration-f4605d`, forked at `81c8e864` — before this fix landed) and
merged afterwards (`a3c16bcd`, repaint.py auto-merged), so its G16 coverage pin was authored
against the perimeter fan and never appeared in §3's table. Surfaced as `W6b3-ARCHIVE.md` §11's
inherited finding; A/B at the re-pin (old fan monkeypatched back, same 372-container corpus):

| where | published (perimeter fan) | correct (Z fan) |
|---|---|---|
| `w6q_gates` G16, creature mean covered fraction | 0.640 (measures 0.640017) | **0.6443** (0.644309) |
| W6-TEXEL.md §1.7, corpus creature coverage | 975,202 = 64.00 % (548,510 dead) | **981,741 = 64.43 %** (541,971 dead) |
| W6-TEXEL.md §1.7 per-effect max / ef251 | 71.9 % (ef261) / 64.8 % | **72.2 %** / **65.3 %** |
| W6-TEXEL.md G6 row, MARGIN LAW pad share | 98.767 % (6,765 holes) | **99.241 %** (4,115 holes) |

37 of 93 creature pages gain, **0 lose**, +6,539 texels net — density only, the same class as §2's
scenery movers, and the creature complement of §2's "110 of 340 `so`-bound models move".
Fan-invariant, verified in the same A/B: ef227 `tex.part0`'s 11,563-texel island (the W6a/W6q stamp
vehicle — its sha pins stand), the 52.8 % per-effect minimum (ef211/ef225), every other G16 row, and
`w6_gates` G6's only coverage *assertion* (`holes/dead < 0.02`: 0.76 % post-fix, safe direction).
