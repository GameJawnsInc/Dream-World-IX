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
