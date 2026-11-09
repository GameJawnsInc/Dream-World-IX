# Landmass prefabs — feasibility (2026-11-08)

**The question (owner):** using the laws we already have, can we do "synthed prefabs" yet? Making a new
landmass in the World tab still takes too many separate steps.

**Verdict: yes, if a prefab is a FROZEN COMPOSITION of what the kit already carries, placed in whole 64u
blocks.** A prefab is a relative `world-fuse` recipe: one plain `world-island` mint plus carried relief
(forest, mountain, hill) at offsets from an anchor block. Stamping it at a new site writes the SAME land,
shifted. So one in-game walk qualifies it for every site it can legally go. Three position leaks stand in
the way today; all three are small and measured (below).

A prefab is never synthesized surface. THE FORM LESSON and the dead-ends list rule that out, and
THE DEFECT FOLLOWS THE AUTHORSHIP is why it matters: a prefab mints no new surface after the walk that
qualified it. "Synth" can lawfully mean only a **search that proposes arrangements**: island seed/radius x
home-matched donor x relative offset, kept when every gate is green. Gates are not an oracle (0 of 13
verdicts predicted on the Path-D wall arc), so a searched arrangement is a CANDIDATE until it is walked,
exactly like `donors.toml`'s `candidate -> qualified`.

## What was measured (offline, scratch mod folders, nothing written to the install)

Sites: blocks (0-2, 13-15) vs (0-2, 15-17), two of the 30 stock open-ocean 3x3 windows, 128u apart in z.
Scripts: `prefab_xlate_probe.py` (the mint alone, no install), `prefab_folder_compare.py` (folder A vs B
block-shifted), `prefab_mesh_diff.py` (triangle multiset, vertex order ignored).

| Build | Shift | Result |
|---|---|---|
| `build_landmass` grass/desert/snow, 1-2 lobes, no decals | 4u, 32u | different TRIANGLES (the block-border split moves) -- but the SAME SURFACE: corrected in [SYNTH-DEEP-DIVE.md](SYNTH-DEEP-DIVE.md) (height + uv identical at 382 samples; a 2u shift does differ) |
| same | 64u, 128u, 192u | **identical** (position + UV, every triangle) |
| same with `relief_amp` 1.3, `relief_seed` pinned | any | different: the relief noise reads ABSOLUTE x,z |
| `world-island` grass r44 (meadow decals on) | 128u | 2 Terrain blocks differ: 136 tris wear other tiles |
| the same with the decal shuffle sorted first | 128u | same triangles; file bytes differ only in vertex order / normal noise < 1e-9 (neither is read by the engine) |
| `world-island --ground desert` r60 (no decals) | 128u | **byte-identical**, 81 files |
| + `world-forest` (blob 15,15) at the same relative point | 128u | **byte-identical**, all 9 Terrain files |
| + `world-mountain --donor 19,3 --rot 90` (desert peak) | 128u | positions exact; 59 apron tris in 1 block wear other UVs |

Refusals seen on the way (the verbs' own gates, useful for sizing a catalog): Uaho refused on grass r44
and r60 ("best raw clearance 2.5-3.1u vs the 6.5u band"). The forest refused on r44 (no plain-grass
pocket) and placed on r60. The desert peak placed on desert r60 with clearance 29u, all gates clean.

## The three position leaks (all deterministic; the cure is relative-to-anchor)

1. **Meadow decals** — `grassland.place_stamps` (line ~527) shuffles `cells_set` itself, so the shuffle's
   input order follows the absolute cells' hash order. Measured fix: `sorted(sorted(cells_set), ...)`.
2. **Rolling relief** — `island.build_landmass` evaluates `G.relief(x, z)` at absolute coordinates
   (line ~658), and the default `r_seed` comes from the centre (line ~638). A prefab needs the noise read in
   anchor-local coordinates.
3. **Mountain apron fallback** — `interior.py:3232`: a cell the carve cannot decode takes a tile from a
   hash of its ABSOLUTE cell id (seed 0xF95). Hash the anchor-relative cell instead.

**All three must be OPT-IN (a prefab frame flag), never a silent change.** Every recipe already on disk
replays its `[[island]]` / `[[mountain]]` rows and must keep writing the bytes it deployed: the editor's
said-back and replay checks and the C-rung identity gates depend on that. Python's int-tuple hashing is
stable across runs, so today's behaviour IS reproducible at a fixed site. It just doesn't survive a move.

## The laws that bound a prefab catalog

- **Placement snaps to whole 64u blocks** today, because the fingerprint hashes triangles and the relief/mountain
  frames anchor at a block corner. The SURFACE is identical at any 4u shift (SYNTH-DEEP-DIVE.md), so a 4u snap is
  reachable with a surface fingerprint and 4u frame anchors. Quarter TURNS are built (P5): a turn is the walked
  bytes turned block by block, not a re-run of the rows, so it shares the walked fingerprint.
- **THE OPEN-OCEAN TARGET LAW** (every footprint block is true open ocean) keeps a prefab off other land,
  so its own sea ring is the only context it ever meets. That is what lets one walk stand for every site.
  The stock map has 30 open 3x3 windows without the x seam and **56 with it** (19 4x4, 2 5x5); the kit already
  wraps columns, but no prefab has been staged across x = 0 yet.
- **Home ground** per massif (`world-donors --class massif`): desert peak / crag / scrub on desert, the
  snow ridge on snow, Uaho / horseshoe / comp20 on grass. A prefab bakes the match in.
- **Size**: Uaho needs more than a 60u grass mint. A mountain's `--spread S` grows its footprint by S².
  Dunes have a size class (no stock component under ~130 cells). Its "proof" used the label-stamp mechanism later
  convicted, so a small dunes MESH carry is untested, not falsified (SYNTH-DEEP-DIVE.md).
- **THE ONE-SITE WORLD LAW**: the two-ground landmass (`junction_compose`) found one stock site in a July scan that
  excluded seam-crossing footprints; it is a dated census, not a law, until re-run with the seam allowed.
- **Canopy vs rock**: a forest must be ringed by walkable ground (19u rim clearance on the re-home), and
  the rock's foot meets the canopy only on the 5-of-28 massifs measured. Screen offsets by home contact.

## Proposed ladder (one rung per in-game check)

- **P0 — the prefab frame: BUILT (2026-11-08), offline-proven; nothing deployed, no in-game step needed.**
  `--prefab-frame` on `world-island` + `world-mountain` (a `[[mountain]]` handle, cli + row), and
  `prefab_frame = true` on the `[[island]]` / `[[mountain]]` fuse rows, carried by `recipe.row_for`. The frame
  origin is the corner of the block holding the centre, so it moves with the land in whole blocks:
  - decals: `place_stamps(ordered=True)` shuffles the cells in sorted order;
  - relief: read at `(x, z) - frame`, seeded from `seed` (x1000, salted `PREFAB_RELIEF_SALT`) unless
    `--relief-seed` is given. The frame refuses a missing `--seed` (its default is centre-derived) and `--beach`;
  - mountain: the undecodable-cell tile hashes `cell - 16 * floor(centre / 64)`.

  `world-hill` and `world-forest` need no flag: measured byte-identical under a shift without one.
  **Measured:**
  - Default unchanged: 14 mint configs (decals, relief, desert, snow, no-seed; two sites) hash-identical before
    vs after, and the CLI desert isle + desert peak re-run is byte-identical to the pre-change run over 81 files.
  - Framed, through the CLI, sites 128u apart: the desert-peak isle is byte-identical, mountain block
    included (it differed in 59 tris unframed). So is the meadow grass isle (r60) + forest + hill (r14),
    all 81 world files.
  - The relief mint is identical at every whole-block shift, and still differs at 32u (the control).

  Fence: `tests/test_world_prefab_frame.py` (10 tests; the decal and carry ones install-gated). Each of five
  mutations (unsorted shuffle, absolute relief, absolute hash, the fuse row dropping the key, the recipe row
  dropping it) turns it red. `test_world_handles` covers the new handle. The overworld domain is green: 653 tests.
  Comparator law: compare at **float32** (what the `.ff9mesh` stores). In float64 the wall UVs carry 1e-15
  noise from absolute positions, which reads as "different land" that is not there.
- **P1 — `world-prefab NAME --cell BX,BY --mod-folder F`: BUILT (2026-11-08), offline-proven.**
  `world/prefab.py` + `world/data/prefabs.toml`. Rows relative to the anchor block's frame origin
  `(64*bx, -64*(by+1))`. Placement: rows on the map, then the CLEAR WINDOW (the target holds nothing in the
  footprint or any relief row's read window; no other FolderNames folder holds anything in the footprint),
  then a STAGING compose whose fingerprint must equal the catalog's, and only then the compose into the target
  (the verbs' own gates; never a copy of staged files) and a fingerprint of what it wrote.
  **THE FINGERPRINT HASHES TRIANGLES, NOT FILES** (measured): the framed mint alone writes the same triangles
  at every site but not in the same vertex order. Each triangle is taken at float32 with its normal rounded to
  1e-6 and rotated to its smallest corner, so the winding is kept.
  Measured: both prefabs fingerprint identically at (1,14) and (1,16); placed for real on (21,1) and (2,17),
  the written land is the catalog's; a second placement on the same block refuses.
  **ROOM, MEASURED: no stock open-ocean 3x3 window is free in the live FolderNames stack today.**
  `FF9CustomMap-world` holds 128 disc-1 override blocks, 4-9 of them in each of the 30 windows. A prefab on the
  live disc-1 map needs room made first (removing KIT overrides -- a `world-sink` of stock land never frees room:
  the open-ocean law probes the stock bundle), a smaller footprint, or another world (Path D:
  the frame under `--target-disc` is unmeasured). Fence: `tests/test_world_prefab.py` (24 tests; the two
  real-bytes ones are install-gated); 10 mutations of `prefab.py` each turn it red.
- **P2 — seed the catalog from compositions already built here:** desert-peak isle and the meadow isle
  (forest + hill) are in (P1). **`desert-peak-isle` is QUALIFIED (2026-11-08):** after the owner reset the world
  map (memory `project-ff9-world-reset-2026-11`; all 30 stock windows free), it was placed on the live folder at
  block (10,9) through `world-prefab` (staged + written == catalog, ledger 0 drift of 162, disc 4 mirrored, chart
  redrawn) and the owner walked it in game: "Walked it fine". The harness put the party there: New Game -> 750 at
  scenario 4000 -> its world exit -> `teleport(630.6, -605.4)` -> y 3.199 (predicted 3.2).
  FOUND on the way: the hint `world-mountain` prints ("teleport (cx-32.5, cz+0.5)") landed EXACTLY on a tri edge
  here (barycentric 0.0) -- the harness's invisible-at-y-0 case. Check castability before teleporting to it.
  **The meadow isle QUALIFIED (2026-11-08):** placed live on (19,18) beside stock land (18,16)/(19,16) (the
  nav-margin tier; disc 4 identical, ledger 0 drift of 810), the party on its grass at (1240.37, -1168.27) y 3.199,
  and the owner walked it: "Walked it fine". With it EVERY catalog prefab is walked. **ADDED (2026-11-08), candidates:** `snow-ridge-isle` and `desert-scrub-isle`,
  the terrain study's round 21 / round 22 lab islands and carves (both owner-passed in game), framed, at their labs'
  own relative placement (anchor (21,1) there). Snow: `--ground snow --radius 88 --lobes 2 --patches 0 --seed 42`
  centred (64, 32) from the anchor, comp9 (`8-10,0-1`, its inlet floor from the catalog) at (30, 48) rot 270 -- the
  rot the CLI's `--near` scan from round 21's point picks; 403 rock tris + 2 plugs, peak 20.39. Desert scrub: r55
  `--seed 42` desert at (36, 28), comp26 (`14-15,3`, its canopy) at (38, 24) rot 0; 139 rock tris, peak 9.75. Both
  fingerprinted at (1,14), navigation settled; both mints print the WARN-only Sea4 uniformity gate, as the labs did.
  Measured (`evidence/prefab-turn/new-isles.json`): every turn at (1,16) and beside stock land at (0,12) passes
  identity; the ground query matches at clean sites but for 1-2 samples per turn that are the SAME cliff-wall tile
  (topo 58) 1e-4u apart (a steep plane's height read from another vertex order, at the probe's 4-decimal rounding),
  0 beyond 1e-3; controls 2691-4965. All four turns open.
  **BOTH QUALIFIED (2026-11-08):** placed live in FF9CustomMap-world through `world-prefab` -- the snow ridge isle on
  (21,1), its lab's own spot, beside stock land (19,3)/(20,3) (the nav-margin tier), and the desert scrub isle on
  (23,5) across the x seam (a clean site, the full fingerprint); disc 4 identical, ledger 0 drift of 648, chart
  redrawn. The harness put the party on each (snow (1341.87, -79.27) y 3.199; desert apron (1477.87, -359.27) y 3.188,
  reached by `--attach` with no relaunch), and the owner walked both: "Fine, next isle", "Walked it fine". The framed
  mountain carries (the apron fallback hashed from the anchor, not the lab's absolute cell) passed as the labs did.
- **P1b — seam, disc 4, the nav margin, carry units: BUILT (2026-11-08), offline-proven, adversarially reviewed.**
  - **Disc 4:** the auto-mirror's copy must be the staged land and its navigation settled; the clear window counts
    both disc trees.
  - **THE NAV MARGIN (measured):** the coast-nav stamp classes a minted island's sea against stock ground within 16u
    of each sea centroid; at (0,12), 9 Sea4 tris beside (22,13)/(22,14) went 57 -> 53. Identity therefore has TWO
    TIERS. At a clean site (no stamp-visible stock ground within 16u of the footprint) the full fingerprint, classes
    included, must equal the catalog's. Beside stock land, a reference copy is staged at the catalog's
    `fingerprint_cell` (a clean site) and must equal the catalog; the target must equal it triangle for triangle with
    the class masked only on water triangles within 16u of that stock ground; and the stamp must have settled those.
    The first version masked EVERY water class and re-checked with the same stamp: the adversarial review (3 of 4
    lenses independently) showed that blind to any change in the sea's navigation. A widened coast-nav reach (the
    review's sabotage) is now refused, and an install-gated test keeps it so.
  - **The x seam** changes nothing (six seam stagings, the beach chain across x = 0).
  - **Carry units:** the four walked units are catalog prefabs on a `transplant` base; their carried stock sea is
    fingerprinted in full; each identical at two anchors.
  - **The clear window:** the target folder: footprint + one-block ring + relief read windows; other FolderNames
    folders: footprint + ring (the stamp's loader reads only the target folder and stock). A neighbour already in
    the target's ring refuses, deliberately: new land within 16u would leave that neighbour's own sea classes stale.
  - Fence: `tests/test_world_prefab.py`, 38 tests (5 install-gated); 21 mutations across the two rounds each turn
    one red.
- **P1c — 4u placement (designed, not built).** Measured: a framed meadow mint shifted 4u or 32u is the same SURFACE
  (height and uv identical at 382 samples); only the triangle split at block borders moves. What it needs:
  (1) an explicit frame origin = the prefab's anchor point (a 4u point). At a block-aligned anchor it equals today's
  block-corner origin, so the walked fingerprints and the qualified prefab stay valid. (2) A SURFACE fingerprint
  (height, uv, masked class and area sampled on a fixed relative grid, compared at float32 tolerance) instead of the
  triangle multiset. (3) A per-verb measurement for the carries: world-mountain's multi-block SPAN and its apron
  taper "at the span's OUTER borders only" (interior.py ~2138, 2276) depend on which blocks the footprint covers,
  so a 4u shift can change the carve's surface, not just its split. The mint is ready; each carry must show surface
  identity at 4u before its prefabs take 4u anchors.
- **P3 — the World tab "Add a prefab" card: BUILT (2026-11-08), adversarially reviewed; owner look pending.**
  `workspace/worldprefab.py` PrefabTool over `world/prefabedit.py`, first in "Edit the map". The catalog picker
  (walked first); the anchor under the click (the footprint centred, the column wrapped, the rows on the map); the
  ghost is the prefab's own land (the mint's coast ring, a carried base by its quarter-turn map, the carried
  mountain/forest ghosts); `world-prefab`'s first laws as the preview. Check/Accept run `world-prefab --dry-run`
  and then into the draft; it lands as ONE recipe step (`[[prefab]]` name + cell, a `world-fuse` runner over
  `prefab.place`). Real bytes: the card's exact command against a real draft of FF9CustomMap-world placed the meadow
  isle (check 34 s, accept 58 s) and the terminus pair (5 s / 6 s) into one draft; each is the catalog's land, and
  the live folder is untouched.
  A DRAFT target (the card's only target) adds two laws, refused before staging. (1) A live edit to the draft's
  source since the copy must not lie in or beside the footprint, because the stack check skips the source the draft
  stands in for. (2) Promote's disc-4 copy must be predictable: every footprint block is open ocean on disc 4 too,
  with the same stock land near it on both discs, so the mirror copies the checked bytes verbatim. The disc-4
  fingerprint itself is deferred to Promote (a draft has no disc-4 tree).
  The review found 14 real defects, all fixed and fenced (13 mutations, each red):
  - the replay window is the prefab's whole clear window, not its footprint;
  - a draft waives the nested compose's manifest-drift gate;
  - `written` (the cards' file list) no longer carries the fingerprint (the card said "64 blocks written");
  - the card works on a folder with no deployed Terrain;
  - the picker is sized from its own labels;
  - a closed card forgets its click;
  - an `error` verdict is world-prefab's, not "the carve";
  - the runner refuses disc 4 / target-disc;
  - the snap anchors clear of the synthetic island;
  - one test that could not fail now can.
  Snap: `world:3d-prefab` (invented land).
- **P5 — quarter turns: BUILT (2026-11-08), offline-proven, and the first turn OWNER-WALKED: "Walked it fine".**
  `world-prefab --turn 90|180|270`, the `[[prefab]]` row's `turn`, and a Turn picker on the card.
  **A TURN IS A STAMP, NOT A RE-RUN.** Re-running the rows with a turned outline would mint new land (the mains
  tiles, the meadow stamps and the mountain's apron all re-roll), so every turn would need its own walk. Instead
  the prefab is composed at turn 0 at its catalog site (`fingerprint_cell`), held to the catalog fingerprint, and
  every file is turned: each block moves to its turned place and its block-local content turns about the block
  centre (`transplant._rot_xz`, the law transplant was proven on over 11 in-game passes: the 4u lattice maps to
  itself and every tile turns into its own rotation variant). Positions and land normals turn; sea normals (one
  uniform constant), uvs and tangents (the IDALL) are kept. The files go through `deploy_override` /
  `deploy_donor_sidecar` (ledgered), then the coast-nav stamp and the disc-4 mirror, as for every writer.
  **Identity, turned:** the written land must equal the catalog site's land with exactly that turn applied
  (`fingerprint(..., turn=)`, an independent digest of the source turned), at both tiers (full at a clean site;
  beside stock land, outside the nav margin plus a settled stamp).
  **Laws the turn adds:**
  - THE OPEN-OCEAN TARGET LAW is checked by `place()` itself for a turn (at turn 0 the composing verbs check it at the
    target; a turn composes elsewhere).
  - THE RIDING PART: a block whose `Donor.txt` prefab carries a part no file overrides would show that part UNTURNED.
    `turn_blockers` refuses it, reading the bundle's own part list (`extract.block_parts`) on BOTH discs (the mirror
    copies the sidecar to disc 4, which resolves it against its own prefab). Measured: beach-chain's (21,1) block
    rides Chocobo's Lagoon's Object (donor (9,17)), so it stays turn 0 (`turns_note`), and the gate finds that by
    itself; the other five prefabs' donors are fully overridden.
  - THE MANIFEST LAW: a turn is not a fuse row, so `fuse.manifest_step` gives it the compose's drift gate and one
    `world_manifest.json` entry (a draft waives the gate, as for every editor job).
  - The catalog opts a prefab in (`turns`, default `[0]`) and names the site it is composed at.
  **Measured** (`prefab_turn_probe.py`, `evidence/prefab-turn/`): the 2 island prefabs x 4 sites (two clean, (0,12)
  across the seam beside stock land, (21,1) beside stock land) x 3 turns, and the 3 turnable carry units x 2 sites x 3
  turns. All 42 pass world-prefab's own identity. An independent oracle, the engine-faithful ground query, compared
  9216 samples (2048-5120 for the units) of the walked land against the turned land at the turned points: 0
  mismatches at every clean site; beside stock land 15-20 class-only differences (heights and parts identical: the
  nav margin re-classing, as designed). Its negative control (the map one quarter turn short) mismatches on
  1328-3552 samples, so the oracle can fail.
  **Status:** a turn places with a banner until it is in `walked_turns`. **WALKED (2026-11-08):** `desert-peak-isle`
  turned 90 was placed live at block (1,16) in FF9CustomMap-world (identity: clean site, the full fingerprint; disc 4
  mirrored 81 files and identical; ledger 0 drift of 324; chart redrawn), and the owner walked it: "Walked it fine".
  The harness put the party there: New Game -> 750 at scenario 4000 -> its world exit -> `teleport(93.4, -1097.4)`
  (the first walk's apron point, turned; checked castable first) -> y 3.199 (predicted 3.2). `walked_turns = [90]`.
  This is the turn LAW's in-game proof, as the comma's walk at rot 90 was for transplant; other prefabs' turns still
  place with the banner until walked.
  **THE IDENTITY IS NOT THE WRITER CHECKING ITSELF** (review): the digest turns each file by transplant's own
  `_rot_xz` and places each block by the rigid point map (`turn_point` of its centre), while the writer turns by
  `_local_turn` and the block map `turn_rel`. A content turn or block map that is not one rigid motion with them is
  refused (a sabotage test each). The writer computes in `_rot_xz`'s own arithmetic: the first form (`x' = -z`) wrote
  -0.0 where transplant writes 0.0 -- the same land to the engine, a different hash, caught on real bytes.
  **Adversarial review** (3 lenses, 2 refuting skeptics per finding): 8 confirmed, all fixed and fenced -- the donor
  part list was a hand list missing Beach2 / Stream / VolcanoCrater / VolcanoLava / Sea4f and disc 4; the turned
  write skipped the manifest-drift gate and record; `--recipe-out --turn` wrote before checking the turn; `canon`
  had no `turn = 0` default; a window test could not fail (it planted inside the unturned ring); and two findings
  against a catalog and test anchor the review saw before they were finished.
  Fence: `tests/test_world_prefab_turn.py` (the arithmetic as one rigid motion, the turned digest against the turned
  writer, every refusal, the plumbing; four install-gated: the desert peak turned at a clean site and beside stock
  land plus a sabotaged writer refused, the comma turned and written for real with its ledger and manifest, and
  beach-chain's riding object) and the card tests in `tests/test_worldprefab.py`. Snap: `world-3d-prefab-turned`.
  23 mutations (the turn's gates, normals, donor, identity, shift, digest independence, manifest, fuse, recipe, CLI,
  card, preview, the stamp) each turn it red; the first pass left 6 alive, and each became a test. One lesson: the
  beside-land check must stand where the stamp really re-classes -- (21,1) is beside stock land but re-classes
  nothing, (0,12) re-classes 15-20 samples, so only (0,12) catches a turn that skips the stamp.
  Evidence: `evidence/prefab-turn/run-final.log` (+ `islands.json`, `units.json`) is the run on the final writer;
  `run.log`, `comma.json`, `reef.json` and `terminus.json` are the first run, on the -0.0 writer.
- **P4 — the arrangement search ("synth")**: enumerate seed/radius x home-matched donors x offsets, keep
  the all-green ones, and render them for the owner. Only the walked ones become prefabs.

## Open

- Which part of the editor feels janky to the owner (steps per landmass, Check waits, the island card
  offering only the plain mint, finding room) decides whether P3 comes before P1.
- The hill and forest ARE measured now (P0: byte-identical, no flag). The multi-block carries (`world-transplant`
  units) are not measured under a shift. C14 already
  showed a carry relabelled across the x seam is byte-identical 6/6, which is encouraging but not this test.
