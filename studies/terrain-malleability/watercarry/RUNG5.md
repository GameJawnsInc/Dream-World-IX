# `world-river` rung 5: the source and the recipe row -- the plan, for the owner's sign-off

PLAN.md's rung 5 was "`--source-massif DONOR` and the `world-fuse [[river]]` row: the source meets a carried foot".
An offline recon measured the source, the massif donors and the room on the live island. **The first half does not
hold:** no catalogued massif can lawfully stand at this river's source, and none would seat there. This plan splits
what survives into three pieces and asks for three decisions.

## What the recon found (offline, 2026-10-20)

**Home's source is born at the continental escarpment, not at a massif.**
- **The source edge** is 5.7u long round (1128.6, -917.8) in (17,14). The tri across it is topo-49 rock (IDALL 196 and
  4036); the plug tri (IDALL 4044) sits at y -0.21..0.39.
- **The profile** (re-measured independently):

  | direction | 4u | 8u | 16u | 24u | 32u | 48u |
  |---|---|---|---|---|---|---|
  | E (upstream) | rock 8.6 | rock 13.2 | rock 22.1 | plateau 26.9 | plateau 27.7 | rock 31.8 |
  | N | rock 3.4 | rock 5.6 | rock 11.7 | rock 19.4 | rock 26.8 | rock 37.3 |
  | S | rock 4.6 | rock 4.7 | grass 4.7 | grass 4.7 | grass 5.2 | grass 4.9 |

- **It is a terrace step** (THE TERRACE LAW): about 24u of rise from the lowland to the plateau over about 24u of run.
- **The rock is comp0, the continental rock network:** disc 1's largest topo-49 component, 15,511 tris over 65
  blocks. It is not a qualified donor (`../mountaindonors/NOTES.md`).
- **Its neighbours are not carryable:**
  - a forest 5.8u from the tip;
  - a building wall 19u east (topo 59, the tower that decision 2 left home);
  - the plateau 21u east, with four entrance tiles.

**No catalogued massif sends water to a lowland foot.**

| donor | rim radius | peak y | aperture |
|---|---|---|---|
| uaho | 20.0u | 13.3 | object |
| comp20 | 31.5u | 21.4 | none |
| crag | 33.7u | 26.5 | none |
| desert-peak | 26.1u | 16.3 | none |
| horseshoe | 54.3u | 31.4 | ensemble |

The horseshoe's falls and river sit in a hanging bowl at y 15.2-26.0, 9-13u above its foot rim, and no water part
leaves the massif.

**The laws already on record say a catalogued massif at the source is the wrong form.**
- **THE TERMINATION CENSUS** (`../../overworld-topography/README.md`): every stock river tip is SEA or MASSIF, zero
  open, and cluster C's source is "at massif foot".
- **RECON.md, "Not recommended":** "stock never shows a stream ending at a foot it was not born at". Uaho or comp20 at
  this source is exactly that.
- **THE ISLAND COROLLARY** (README): no small sea-ringed landmass has walkable highland.
- **THE FORM LESSON:** statistics never reproduce the look; carry the form.

**`world-mountain` could not seat one there anyway.**
- **The band-clean seat** keeps every non-plain tri (the banks included) 6.5u outside the rim (`interior.py` ~2228,
  `band_clean`). The calibrated bench is the rim plus 28u.
- **The room:** the live island has 17.4-21.7u of lawn round the tip (E 17.5, N 21.7, S 21.5). The largest rim that
  fits is r 4.8u.
- **The growth each donor needs:**

  | donor | grow east | half-width each side of the axis |
  |---|---|---|
  | uaho | +28 to +42u | 30-44u |
  | comp20 | +37 to +51u | 43-56u |
  | horseshoe | +80 to +94u | 59-73u |

- **The live placement caps that growth.** Stock land sits at (2,11) and in column 3, so the outline can grow about
  64u east and only 21.7u north. A bigger rectangle also fails `open_ocean_offsets`, which would move the island.

**So the verb's warning gives wrong advice.** `world-river` prints "Every stock river rises in a mountain: add one
with `world-mountain` at (x, z)" (`cli.py` ~5815, pinned by `test_world_river.py` ~861). Followed, that advice either
refuses to seat or builds the not-born-here form.

## What rung 5 becomes

| piece | what | new terrain surface | accept |
|---|---|---|---|
| 5a | correct the source warning | none | the text says what is true; the test pins the new text |
| 5b | the `world-fuse [[river]]` row | none | a one-row recipe writes the CLI's bytes; a later relief row can target the river island |
| 5c | the source's own foot: a RECON, not a build | none (reads only) | the registered prediction below is confirmed or refuted |

**5a -- the warning.** It should say:
- stock never ends a stream in open lawn;
- this river was born at the continental escarpment, which the kit cannot carry yet;
- a catalogued mountain at the source is not stock's form, and `world-mountain` will not seat one there.

Point to `world-forest` for dressing the lawn instead (decision 2). Also correct the CHANGELOG line and
`OVERWORLD_RECIPES.md`. About an hour, offline.

**5b -- the recipe row.** Pure plumbing; no geometry changes.
1. **One entry point.** Lift the pipeline out of `cli._cmd_world_river` into `river.deploy(...)`: compose, stage,
   `write_verdict`, promote, mirror. The CLI and fuse then call one function, which is what "recipe = CLI bytes"
   means.
2. **A tier-1 slot.** Add `[[river]]` (donor, `at`, `apron`) to `fuse.py`'s placement tier, before the
   mountain/forest/hill tier.
   - `at = "auto"` is resolved on the dry run and printed. A real run needs an explicit `at`, so a recipe re-runs to
     the same cells.
3. **Occupancy.**
   - The verb's own stack read stays in force.
   - A re-run is `--remove` first; fuse never waives B1 for a river.
4. **One mirror.** The disc-4 mirror is deferred to fuse's single mirror pass.
5. **Relief rows on the river island.** A later `[[mountain]]`/`[[forest]]` row can target it: fuse's relief rows
   already read the deployed blocks, not the mint. A dry run of such a recipe must deploy the river first, or refuse
   by name (today's dry run fails its read when a relief row targets an island the same doc has not deployed).

Accept:
- a `[[river]]`-only recipe into a scratch folder is byte-identical to the CLI at the same placement (all 264 files);
- a recipe with a `[[forest]]` row on the river island's open lawn passes fuse's gates;
- hermetic tests for parsing, ordering, the explicit-`at` refusal and the remove-first refusal.

Offline throughout. One in-game look at a fused build at the end, when the harness is free.

**5c -- the source's own foot, a recon.** The lawful source is this river's own birthplace: the escarpment step,
carried. The question is whether comp0 has a slice round the source that F1 could accept: one that closes at natural
breaks (a valley, the plateau lip, a coast) without cutting rock, small enough to carry, and with a sea edge stock
ships in that form. `../../overworld-topography/README.md`'s v4 TRANSPLANT CENSUS found one coastal window where a
highland shelf and an escarpment meet lowland grass and the sea. 5c checks whether that is the form such a slice's
seaward edges need.

**Registered prediction: NO.** The ISLAND COROLLARY says no small landmass carries walkable highland. comp0 is one
network over 65 blocks, and the tower and the plateau's entrances stand 19-21u from the tip. The prediction is that
no slice under about 6 blocks closes without a rock cut. If 5c finds one, a build plan follows for a separate
sign-off. If not, the lawn source becomes v1's permanent answer, and the warning (5a) already says why.

## 5a and 5b result (offline; signed off with the three recommended answers, 2026-10-20)

**5a: done.** The warning names the escarpment the river was born at, says not to put a `world-mountain` there and
why, and points nowhere else. The first version pointed to `world-forest`; 5b showed a canopy does not seat on this
island either, so it now says to leave the lawn. CHANGELOG and `OVERWORLD_RECIPES.md` match, and
`test_world_river.py` pins the text.

**5b: done; two of its three accepts hold, and the third is localized.**
- **One pipeline.** `river.deploy()` runs the whole verb (compose, the stack read, the staged audit, the promotion,
  the mirror). The CLI prints round it through two callbacks, so its output and all 71 of its tests are unchanged.
- **The `[[river]]` row** (`fuse.py`, first tier with `[[island]]`): keys donor / at / area / apron. `at = "auto"`
  works on a dry run only, and the printed placement is for copying into the recipe. A river row never waives B1.
- **A finding the plan missed: THE RECIPE COULD NOT BE REMOVED.**
  - `--remove` owned a file only when the ledger row's argv ran `world-river` with that `--at`. A recipe's rows
    carry world-fuse's argv, so every fused river file read as another verb's.
  - Fix: `mesh.ledger_pipeline(verb, **fields)` tags every ledger row written inside it (the promotion and the
    mirror both run inside one). `river._row_verb_shift` reads the tag first.
  - Test: `test_world_river_remove_owns_a_river_world_fuse_wrote` (refused untagged, owned tagged).
- **A dry-run hint.** On a dry run, a relief row that fails after an undeployed base step now says so by name.

**The accepts, measured** (`rung5b_identity.py`, into scratch folders outside the install, the stack read narrowed to
the target because the live river holds 512,128):

| accept | result |
|---|---|
| a `[[river]]`-only recipe writes the CLI's bytes | **green:** 264 of 264 files byte-identical, 132 on Disc1 + 132 on Disc4 (both mirrored explicitly against stock) |
| `world-river --remove` owns a fused river | **green:** 264 owned, 0 foreign; every ledger row tagged under world-fuse's argv |
| a `[[forest]]` row on the river island passes | **red, localized:** see below |

**Why the forest does not seat (not the plumbing):**
- **The read works.** The forest row read the river island the base tier had just deployed.
- **It cannot cross the world's x seam.** The relief verbs are not seam-aware, and the island at 512,128 straddles
  x = 0. The default 96u reach crosses the seam and refuses, so the reach must stay on one side.
- **It has nowhere lawful to stand.** The only lawful canopy placement on the narrow lawn is (36, -820), and it fails
  the forest's annulus-crack gate by one edge (`annulusOnce=1`; every other gate is clean). Five exact centres
  elsewhere are refused as not lawful plain lawn.

Seam-aware relief is the open THE SEAM-WRAP rung of the interior verbs, and a wider island means the outline growth
5c's recon weighs. Neither is 5b's work.

**Also measured:** `--at auto` now finds no free placement on the owner's install. All 56 open-ocean candidates are
held, (8,-2) by the live river itself.

## 5c result (a recon; reads only) -- the prediction holds: NO

`escarpment_recon.py` asks whether the river's own birthplace could be carried as a slice that closes the way every
lawful window does: THE CUT-LINE LAW, under which a cut crosses only lowland (land at y <= 6.5), and high relief is
cut around, never through.

| measurement | result |
|---|---|
| A. every rect up to 4x3 blocks holding the source block, scored on the v4 census's per-edge land heights | **0 of 60 pass.** The best, the source block alone, crosses high ground on all four sides: E and N at 29.6, S at 16.6, W at 8.0 |
| B. the high ground (tris topping 6.5) joined to the 13 high tris within 8u of the source tip | **20,904 tris over 65 blocks**, 147,869 u^2 in plan, x 754-1459, z -1055..-569, peaks at 42.68. It closes inside the read window, so this is its whole extent: the continent's one highland (comp0 and its plateaus). It holds the tower (391 tris) and 83 entrance tiles |
| C. what the source block's own frame would sever | 155.5u of high ground: N 55u (top 27.5), E 64u (27.4), S 27u (16.5), W 9.5u (7.9) |

**So the smallest lawful slice containing this river's birthplace is the whole 65-block highland.** That is
about ten times the 6-block bound, and it carries the tower and the plateau's entrances that decision 2 leaves home.
Anything smaller cuts the escarpment through, and the kit has no wall language at that height to close the cut (the
coastal join columns work only because the kit's 3.2u wall IS stock's coastal wall). This agrees with THE ISLAND
COROLLARY: no small sea-ringed landmass carries walkable highland.

**Per decision 3, the lawn source is v1's permanent answer.** 5a's warning already says why. Rung 5 is closed.

## The forest after the seam rung (offline, 2026-10-20)

The relief verbs now read and write across the seam (`interior.py`, the island mint lane's approach; tests in
`test_world_seam_wrap.py`). `seam_forest.py` re-ran the forest on the river island, into scratch folders outside
the install (`out/seam_forest.json`):

| case | read window | where the canopy stands | result |
|---|---|---|---|
| a. near (49,-824), reach 40 (the 5b run) | columns 0, 1 | (36,-820), rim clearance 47.5u | annulus gate: 1 open edge, midpoint (10.84,-829.54) |
| b. near (49,-824), reach 96 (the default) | columns 23, 0, 1 | (44,-824), rim clearance 38.8u | every geometry gate clean, walk-in worst 2.05 (ceiling 2.34); census MISS in block (0,12) at 4 samples, world about (12-18, -783 to -796) |
| c. center (36,-820), reach 96 | columns 23, 0, 1 | (36,-820) | annulus gate: the same edge |
| `[[river]]` + `[[forest]] near = [49, -824]` through `world-fuse` | columns 23, 0, 1 | (44,-824) | as b |

**The crack is not an artifact of the narrow window.** With column 23 read, (36,-820) fails on the same edge. The
edge is 10.8u east of the seam and is already open on the untouched island, where the kit grass crest meets the
carried stock bank (topo 62). The forest's annulus gate counts every open edge within 11u of the canopy's outline,
and unlike the mountain's it does not subtract the edges the island had before the carve.

**What the narrow window did change is the snap.** Without the coast west of x = 0 it overrated (36,-820)'s rim
clearance. Read whole, the island puts the canopy at (44,-824), and every forest gate passes there. (The snap counted
39 lawful centres in both runs.)

**The census MISS belongs to the island too.** `census_gate` fails on the untouched blocks (0,12), (0,13) and (1,12)
at the same points. It checks Terrain over blank parts and a cut sea, while in game the river's Stream and RiverJoint
parts cover the channel. Even the whole deployed stack misses some points there, the stock-inherited misses that
`world-river`'s own census subtracts. Every relief verb re-checks every block in its read window, so any relief carve
whose window takes in those blocks fails, wherever it stands.

So no forest seats on the river island yet, and neither refusal is about the forest. The next step is making both
gates measure against the island before the carve: census the block's deployed stack and subtract the misses it
already has, as `world-river` does, and subtract the pre-existing open edges in the forest's annulus gate, as
`world-mountain`'s gate does. Then re-measure (44,-824).

## The gates measure the carve: the forest seats (offline, 2026-10-20)

Both gates now compare the island after the carve with the island before it (`interior.py`):

- **`census_gate(stack=)`** reads every override the block already ships besides its Terrain
  (`read_deployed_stack`: on the river island Beach1, Object, RiverJoint, Sea1-5, Stream) and runs the same census
  twice, on the pristine stack (the Terrain as read) and on the edited one. A MISS or stacked sample the pristine
  stack already has is the island's own and is logged; one the carve adds still refuses. This is `world-river`'s
  home-miss subtraction (`river.audit_written`). `parts=` keeps its meaning: a block it names ships exactly those
  ensemble parts, carried or blank (`census_parts` = what `deploy_mountain_parts` writes). All six relief call
  sites (three CLI verbs, three `world-fuse` rows) pass `stack=`. Without `stack=` the gate is unchanged.
- **The forest's annulus-crack gate** subtracts the island's own once-edges, counted the same way over the same
  blocks before the carve. This is how `carve_mountain`'s once-edge gate already worked.

Tests in `test_world_interior.py` ("the gates measure the CARVE, not the island"). Each break-it was checked red by
mutating the fix: a new hole, a deployed River the ensemble deploy replaces, a new stacked sheet, a kept tri knocked
out of the annulus, and a CLI call without `stack=` all refuse.

`seam_forest.py` re-run (scratch outside the install, `out/seam_forest.json`):

| case | where the canopy stands | result |
|---|---|---|
| a. near (49,-824), reach 40 | (36,-820), rim clearance 47.5u | seats: annulusOnce=0, walk-in worst 2.05 |
| b. near (49,-824), reach 96 (the default) | (44,-824), rim clearance 38.8u | seats: annulusOnce=0, walk-in worst 2.05 |
| c. center (36,-820), reach 96 | (36,-820) | seats: annulusOnce=0 (the edge at (10.84,-829.54) is the island's) |
| `[[river]]` + `[[forest]] near = [49, -824]` through `world-fuse` | as b | both rows clean; the forest writes 8 Terrain files, wrapped labels only (canopy in (0,12) and (0,13)) |

In every case the probe grounds on Terrain topo 37 (y 6.88-6.89), the census finds no new MISS, and it logs 43
inherited samples: exactly the deployed stack's own 22 / 9 / 12 in blocks (0,12), (0,13), (1,12). The old
construction still fails those three untouched blocks, which is what the gate no longer judges a carve by.

**Six of the forest's 8 files change no geometry.** Blocks (1,12), (1,13), (23,13), (0,14), (1,14), (23,14) carry the
river's exact positions, UVs, normals and IDALL; only tangent.w differs (the river writes 0.0, the relief re-emit
`_assemble` writes `[idall, 0, 0, 1]`). The worldmap shaders do not read tangents, so nothing renders differently,
but any relief verb on the river island rewrites (and takes ledger ownership of) every block in its window, which by
its ledger contract `world-river --remove` would then stop on as another command's bytes (R1; not run here). This
predates the gate rung; keeping each kept tri's source tangent in `_assemble` would let untouched blocks converge
byte for byte.

Not done: the forest has not been deployed to the live install or seen in game. `world-hill`'s crack gate (once-edges
within radius + 4 of the hill) is still absolute; it was not part of this measurement.

## Decisions for the owner

1. **Drop `--source-massif DONOR`** (a catalogued massif at the source) from the plan. Recommendation: yes. It is the
   form stock never shows, and it cannot seat.
2. **The order:** 5a and 5b now (no new terrain surface, so nothing for THE DEFECT FOLLOWS THE AUTHORSHIP to land on),
   with 5c as a reads-only recon. Recommendation: yes.
3. **If 5c says no,** keep the lawn source as v1's permanent answer, dressed with `world-forest` if wanted.
   Recommendation: yes. The alternative is a two-level island arc, which the corollary says stock never builds small.

## Sources

- The numbers come from an offline recon of the install's bytes, whose scripts were not kept. The profile table was
  re-measured independently from `river.read_window`, and 5c re-derives the rest as committed scripts.
- The laws:
  - `RECON.md` "Not recommended";
  - `../../overworld-topography/README.md` THE TERMINATION CENSUS and THE ISLAND COROLLARY;
  - memory `project-ff9-overworld-interior-topography` (THE FORM LESSON, THE TERRACE LAW);
  - memory `project-ff9-ground-junction-synthesis` (THE DEFECT FOLLOWS THE AUTHORSHIP).
- The code: `interior.py` (`band_clean`, the deployed-span refusal), `fuse.py` (tiers, the blob-only island row),
  `cli.py` (`_cmd_world_river`, the warning).
