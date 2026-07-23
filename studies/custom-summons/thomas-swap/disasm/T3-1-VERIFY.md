# T3-1 — ADVERSARIAL VERIFICATION (independent re-derivation)

**Claim T3-1:** A full decode of a stock summon creature yields enough to build an armature + skinned
mesh + baked animation: skeleton (parent+length bone-link table), rigid run-length skin (one bone/vertex,
weight 1.0), FT4/FT3 geometry with pooled UVs, per-frame per-bone 12-bit Euler rotation + root translation
clips.

**VERDICT: CONFIRMED.** Re-derived from scratch on the local stock corpus; the stated falsification
criteria are met NOWHERE.

## What I reproduced (not trusting the cited numbers — recomputed)

1. **ef227 spot-check reproduces exactly** (`py ef_container.py ef227.bytes`): 93 bones, 2 meshes,
   797+642=1439 verts, (39+1326)+(44+1007)=2416 faces, 8 motion clips. Matches the cite to the unit.

2. **Corpus sweep, all 372 files, maxVertexIndex recomputed directly from the primitive stream**
   (`iter_primitives`, not the parser's own geom_checks):
   - **maxVertexIndex == nVert-1: 1092/1092 meshes PASS, 0 FAIL** — the exact stated falsifier
     ("a mesh with maxVertexIndex != nVert-1"). Never observed. This is what makes the rigid run-length
     skin valid: nVert = Σ verts_per_bone, indices span exactly [0, nVert-1], so each vertex falls in
     exactly one bone's run → one bone per vertex, weight 1.0 (no weight/index table exists in the format,
     M4 §4). (1092 vs the doc's 1041 = my sweep double-counts the 24 creature blocks, which appear in both
     the id-5 pass and scan_geom; unique blocks = 1005, meshes = 1041, same population, same 0 failures.)
   - **maxUVIndex == uvCount-1: 1020/1020 PASS, 0 FAIL** — pooled-UV closure holds everywhere UVs exist.
   - **chain-closure (vertsPerBone→positions→primitives→uv→colors + pBoneTable==0x14 + pMeshTable law):
     6174/6174 checks PASS, 0 FAIL** — the format walks exact; a wrong layout cannot close.
   - **skeleton parent < child: 3157/3157 bones PASS, 0 FAIL** — every BoneLink's parent index is lower
     than the child's, i.e. a valid parent+length chain with no sort pass, exactly as M5 §4 asserts.

3. **The 24 creature packages use ONLY FT4/FT3** (isolated from the Eff family): 24/24, aggregate
   FT4=5516 / FT3=33345, zero GT/G/F. The GT4/GT3/G4/G3/F3/F4 buckets seen in a naive whole-corpus sweep
   are all from Eff-family (non-creature) blocks that scan_geom also picks up — the parser handling all 8
   buckets is completeness, not a creature counterexample. So "FT4/FT3 geometry with pooled UVs" is a
   correct creature characterization, not an ef227 overfit.

4. **Motion clip decode reproduces** (`m5_chain.py` on ef227's 8 clip offsets): 8 clips, **N=93 nodes each
   (= the 93 bones)**, frames 24/30/26/48/40/68/82/28, tiling the motion region with **0 overlaps**; the
   only "gaps" are 2-byte 4-byte-alignment padding between clips (M5 §2). A wrong layout could not tile.
   `m5_motion_verify.py` exits 0. The 12-bit coarse+fine Euler + root-track structure is decoded
   (M5 §2.3, cited `0x7c40..0x7dba`).

## The one honest caveat (does NOT refute the STATEMENT)

The STATEMENT claims the decode yields **the clips** (12-bit Euler angles + root tracks) — PROVEN. It does
NOT claim the **angle→rotation-matrix composition** (Euler order + sign, RotMatrix `0x37a0/0x3850/0x3910`)
is solved; T3 §2.4 / M5 §10 correctly mark that PLAUSIBLE-not-proven and self-validating vs the s52 probe's
bone-0 matrix. That is a downstream correctness step for *baking*, not a gap in the *data the decode yields*.
So a baked clip's angles are present and correct; the matrix that consumes them awaits one bounded read.
The claim as worded is precise and survives.

## Provenance
Read-only. Ran committed parsers (`ef_container.py`, `m5_chain.py`, `m5_motion_verify.py`) over local
scratch blobs under `C:/gd/SCRATCH/summon-format/`. No stock bytes copied into the repo; this doc quotes
only counts/offsets/structure.
