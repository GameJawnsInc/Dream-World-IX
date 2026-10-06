# R4 (c2b) on the bench — the horseshoe's whole home island, north of the continent

Registered 2026-10-06 BEFORE any bench write or dry run. Owner: "go with (c2b), build it on the bench."
Follows [`COAST-JOIN-STUDY.md`](COAST-JOIN-STUDY.md). **Bench only: nothing touches the live install.**

## What gets built (on a scratch mirror of the live `FF9CustomMap-world`)

**1. THE R4 REVERT.** The continent goes back to its pre-massif state:
- restore the 560 files of `backups/west-seam-continent/r4-pre.20260828-103332` (Disc1 + Disc4);
- delete the 54 parts the R4 carve CREATED, which a restore alone would leave behind: Falls / River /
  RiverJoint on blocks 21-23 × 6-8, both discs.

`r4-pre` was taken after R3's stamp, so the safe road stays in place.

**2. THE ISLE.** A verbatim region carry of the home island, onto open ocean:
```
py -m ff9mapkit world-transplant --mod-folder <BENCH> --cell 21,1 --donor 5,15 --size 3x2 --excise
```
- **Unrotated and unshifted,** so the falls/river/object ensemble rides its natural sidecars (THE OBJECT
  POSE LAW).
- **`--excise`** drops the two foreign land crumbs that cross the donor rect's north frame (80u² and
  116u²).
- **Carried along:** the two islets INSIDE the rect (948u², with forest, and 76u²).
- **Pre-measured:** the target blocks 21-23 × 1-2 hold no stock parts and no mod overrides. Their one
  stock neighbour, (21,3), is 498 sea4 / 10 sea5 / 4 sea3 tris.

**Declared in advance, the only permitted adjustment:** if the dry run refuses on the land margin (the
948u² islet sits ~2u from the south frame), re-run with `--land-margin 0`. Any other refusal stops the
round and is reported.

## Registered predictions

- **B1, the verb runs clean.**
  - The dry run passes every HARD gate: open-ocean target, mod-overwrite, prefab-parts / effective-prefab,
    the crack and T-junction differentials, the placement census (no introduced misses), the weld audit.
  - The report-only WANG-CARRY gate reports ≥ 1 cropped water seam on the outer frame (all six donor
    blocks carry sea3/sea5).
- **B2, it is verbatim.** On the bench, ≥ 99% of the carried island's Terrain tris equal the donor's tris
  translated by exactly (+1024, 0, +896), in position, uv and topograph. Exceptions may only be:
  - excised footprints and their re-zipped ocean;
  - frame re-partition at interior block borders.
- **B3, the revert is exact.** The bench's continent files are byte-identical to `r4-pre` (560/560), and
  the 54 created parts are absent.
- **B4, the bench changed only what it should.** Versus the live folder, the only changed paths are:
  - the R4 revert set;
  - the target blocks 21-23 × 1-2;
  - their Disc4 mirrors.
- **B5, the look matches stock.** Offline renders (`world-render`) of the isle on the bench, against the
  same views of the stock home island (camera translated by the same offset), are pixel-identical over
  the island's land in every view that doesn't see the frame.

## Where the owner's eye will most likely land (named now, per THE DEFECT FOLLOWS THE AUTHORSHIP)

1. **The outer water frame:** the one place the carry crops stock and meets our generic ocean, plus the
   excise re-zip. If the Wang gate reports seams, the proven follow-up is `world-rim-retile`, as its
   own step.
2. **The two excise scars** at the north frame.
3. **The isle against the continent:** ~70u of water to the continent's north shore. That is a design
   call, not a defect.

## Out of scope for this round (each its own step after the owner's look)

- boat landing on the isle (a coastnav stamp);
- the isle's encounter area bits (carried from the donor region; a restamp per THE DONOR-AREA LAW);
- the minimap;
- R5's seat on the continent;
- any live deploy.

## RESULT

(appended after the run, below this line; nothing above edited)
