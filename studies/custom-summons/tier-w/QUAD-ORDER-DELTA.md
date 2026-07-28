# QUAD-ORDER FIX — the coverage deltas awaiting OWNER sign-off on the study records

> The kit defect UV-ANALYSIS.md §6 named is FIXED at the source: `repaint._face_polys` and
> `summons.build._mesh_tris` now emit the Z fan `(0,1,2) + (1,3,2)`. This note exists because the
> fix moves numbers that **W6b-SCENERY.md, W6-TEXEL.md and `phoenix_field.toml` publish**, and those
> files are frozen under the active cast ladder — **nothing in them was edited.** Each delta below
> names the old predicate (perimeter fan, the falsified corner-order assumption) and the new one
> (Z fan, corpus-measured). Apply or direct, then delete this note.

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

## 3. The published numbers that DO move — the pending edits, by exact line

| file : line | published (perimeter fan) | correct (Z fan) |
|---|---|---|
| `W6b-SCENERY.md:739` (appendix, x640_y256 cov) | 5,737 | **6,080** |
| `W6b-SCENERY.md:702` + `:754` ("measured covers 3,584/5,737 (V1 F4)") | 3,584 / 5,737 | 3,584 / **6,080** |
| `W6-TEXEL.md:114` ("column 640 shares 1,659 halfwords") | 1,659 | **2,016** |
| `phoenix_field.toml:26` (comment copy of the appendix row) | 5,737 | **6,080** |

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
