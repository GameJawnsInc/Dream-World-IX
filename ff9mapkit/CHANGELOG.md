# Changelog

All notable changes to `ff9mapkit`. Format follows [Keep a Changelog](https://keepachangelog.com);
versioning is [SemVer](https://semver.org). The Blender add-on has its own version, kept in lockstep.

## [Unreleased]

### Fixed — the Cutscene tab: a `[[cutscene]]` field no longer freezes the editor, and dialogue stops eating itself
- **Opening the Cutscene tab on a field with `[[cutscene]]` scenes used to kill the session.** After
  that, every tree click, undo, redo, refresh, Check and Save All did nothing — silently, because the
  app launches from a `.pyw` and the traceback had nowhere to go, so it just looked frozen. Both
  shipped `stolen-ember` examples did it, and so did `ff9mapkit edit`, which crashed outright on the
  same files. One helper (`editor.forms.single_block`) now answers "which scene does this form edit?"
  for every path in both editors instead of three of them disagreeing about it.
- **Writing two lines of dialogue in a row kept only the last one.** *Add / Update* guessed which one
  you meant from the step's TYPE, so a second `say` overwrote the first — three lines in, one out, no
  warning, and no way to clear the selection with the mouse. It is now **Add step** (always inserts,
  after the selected row, so you can author into the middle) and **Update selected** (always rewrites
  the selected step). Changing a step's type in place works for the same reason: it used to leave the
  original alone and drop a stray step at the end. **Duplicate** joins Remove/Up/Down.
- **The Inspector was blind to a multi-scene field** — it bailed on the whole dispatch, so no step was
  ever checked and the health badge read 0 problems on a broken scene. It also still looked for the
  singular `actor` key that the cast redesign replaced with `actors`, so it called every cast scene
  "narration". It now summarizes every scene, names the cast, and prefixes each warning with the scene
  it came from. Walk-stall warnings from the build do the same (`[cutscene] #1 step 3: …`).

### Added — the Cutscene tab tells you before the game does
- **"Check the staging"** walks every actor's route against the saved walkmesh and reports the legs
  that would **stall** — the in-game symptom is a scene that locks up with the actor pressed into a
  wall. The kit could already predict this exactly; nothing in the GUI could reach it, so it only ever
  fired from `ff9mapkit lint`. Runs off the UI thread. (Mesh from the *saved* file, steps from what is
  open — editing steps never moves the mesh.)
- **"Runs with the previous beat"** — a checkbox for parallel choreography (two actors moving at
  once). The compiler has always supported it and the step list has always *displayed* `[with prev]`;
  there was simply nothing anywhere that could write it. Enabled only where the compiler accepts one
  (walk / route / animation / turn, never the first step), from the compiler's own rule.
- **A live on-screen wrap preview under the dialogue box**, the same one the other dialogue fields
  get, using the same wrapper the build uses. FF9 never wraps text itself.
- **Step rows are numbered**, 0-based, matching how the build's own warnings address them.

### Changed — `ff9mapkit floorplan` recomposing MERGES; it no longer overwrites your room
- **A recompose now keeps everything you put in a composed room** and regenerates only what the
  composer derives from the plan. `[[npc]]`, `[[prop]]`, `[[chest]]`, `[[event]]`, `[[choice]]`,
  `[behavior]` — anything the Place tab or the Editor forms wrote — survives verbatim. So does a
  **hand-drawn door** and an **extra painted `[[layers]]` row**, which live inside composer-owned
  tables: the composer's own rows are identified (`door_to_*`, `art/back.png` + `art/floor.png`) and
  replaced, and everything else in those tables is left alone. Deleting a door from the plan still
  deletes its gateway — which is why those rows are found by prefix and not merged by name.
- **Your painted art survives too.** Each compose records the sha256 of the two placeholder PNGs it
  wrote; next time, a file that still matches is the composer's and gets repainted, and one that does
  not is yours and is put back. If the reshape moved the floor under a painting, it says so and points
  at `ff9mapkit paint-template` rather than quietly leaving a mismatched backdrop.
- **A reshape that strands your content names it.** An NPC now outside the new outline, inside the
  80u wall clamp, or under a door the recompose moved on top of it is reported per room — all three
  are silent in-game (an off-mesh NPC still renders, standing in the air). It warns; it never deletes.
- `[camera]`, `[player]`, `[field]`, `[walkmesh]`, `[encounter]` and `[savepoint]` are still
  regenerated whole — a per-key merge would leave a stale `range`/`scroll` alive under a room that
  stopped scrolling — and a recompose now *reports* each one whose on-disk value it replaced instead
  of reverting it silently.
- **A composed door the plan no longer wires is named when it goes** — which also covers the one way
  a hand-drawn gateway can vanish: naming it `door_to_…` puts it in the composer's own namespace.
- `--force` keeps its meaning and is no longer the normal path: it regenerates every room from
  scratch, discarding all of the above. The one surviving refusal is a room whose `field.toml` will
  not parse — there is nothing to merge into — and it fires before a single byte is written.

### Fixed — the Floorplan tab's Compose was silently renumbering deployed dungeons
- **The tab stamped its in-memory plan over `floorplan.json` a moment before the verb read it**, and
  a plan drawn in the tab is `{name, poly}` — so the pinned room **`id`** was destroyed on every
  recompose. A dungeon you had already deployed came back on the next free id block, invalidating
  every `deploy_field.py --id N` you wrote down, every external gateway aimed at those rooms, and
  the New Game wiring. The pin has existed since the composer shipped; it never worked from the GUI.
  The tab's write now merges rather than stamps, and the session absorbs what the verb recorded.
- **A `[[sps]] pos` is `[x, y, z]`**, so the new recompose gate read its height as its depth; and
  `[[gauge]]`/`[[numeric_input]]` positions are screen pixels, which it judged as world coordinates
  and reported off-mesh forever. Both fixed, per table.
- **Off the mesh is not automatically wrong.** A normal FF9 NPC stands against the back wall, just
  past the floor edge (the in-game-verified hut oracle has Vivi ~100u out), so the gate now uses the
  same `2 × 96u` talk reach `build`'s own placement lint uses instead of refusing any overhang.

### Added — see an animation before you attach it (Workspace)
- **The Models tab plays a model's clips.** The comma blob of action names is a clip LIST (the five
  movement slots first, then the model's own gestures, cross-form rows marked "other form"); picking a
  row renders that clip and plays it in the preview box — play/pause, a frame scrubber, and an honest
  counter (`f 9/16 · 30fps`, and `preview 15fps` when a long clip is strided). Frames render in the
  background and the loop EXTENDS as they land, so a clip starts playing before it finishes filling;
  Reset puts the still back. Frames are disk-cached per `(model, clip, frame)` under `anim_frames/`,
  bounded at 60 rendered frames per clip (~2.7 MB). Bundled clips only for now — a minted or loose
  `.anim` says so instead of pretending. Plus one "Copy anims= snippet" button.
- **Pickers, so nobody hand-hunts a clip id again.** An `[[npc]]`'s movement clips, a `[[prop]]`'s
  `pose`, and a cutscene `animation` step all grow a **Browse…** that lists what *that block's rig* can
  actually play, previews it, and writes the value back. Scope comes from one shared model-precedence
  helper (`blockmodel.resolve_block_model` — archetype/preset → explicit `model =`, `[player]` → the
  stock avatar), the same answer the build ships, so a picker can never be scoped to a different model
  than the field uses. A gesture picker refuses cross-form clips; the movement picker shows them
  marked; the five-slot editor's blank slot means AUTO and says what auto would fill.
- **Cutscene animation NAMES now work for model actors and the player**, closing FORMAT.md's documented
  gap (a name used to require a playable preset, so every plain-model NPC had to use raw ids). A name
  resolves through the actor's own rig: own-form gestures first, then the five movement slots; a
  cross-form name is refused, listing the own-form alternatives. One alias table is shared by both
  actor kinds — `idle`/`stand`, `walk`, `run`, `turn_left`/`turn_l`/`left`, `turn_right`/`turn_r`/
  `right` — and `lint` runs the very same resolver, so a name that lints clean cannot die mid-build.
- **Lint:** minted clip keys (`60000-65535`) no longer false-positive the AnimationDB check (they
  register at launch via DictionaryPatch), and an `[[npc]] anims` id that is not one of the resolved
  model's own clips now warns — a foreign rig's clip binds by bone name and can pose the model wrong.

### Changed — `[[prop]] pose` resolves the model's OWN FORM first
- A held pose is a one-shot, and a different form code is a different **skeleton**: playing another
  form's clip twists the model in-game. `pose = "<name>"` now resolves through the model's own-form
  gestures before the any-form join. A name only the cross-form join can answer **still builds**
  (backward compat) but emits a lint warning naming the trap and the own-form alternatives.
- **This can change the resolved clip id** for a `[[prop]]`/held model whose form is not `F0` and whose
  pose name exists in more than one form — that is the fix (the old id was the twisted pose). Numeric
  poses, and anything on an `F0` rig, are unchanged.
### Added — summon-reskin: the `so` record's SECOND ARRAY, disclosed
- `so_record` now returns the `P × {u16, u16}` block at `+arrayB` that it used to walk past and
  discard by name (`second`), and `Binding` carries it as `second_pairs`. Nothing interprets it:
  the read is inside a record the reader already accepted (`arrayB == 8 + 4P` is the acceptance
  test), and the `P == 0` invariant is untouched.
- **Why it is disclosed and not modelled.** One stock log-only cast of ef038, read through the U1
  s77 instrument (per-mesh min/max of the primitives' own `u,v` bytes), **measured that array as a
  per-slot texel displacement — pair position 0 onto `u`, pair position 1 onto `v`, +128 texels
  each, one 8bpp column (640 → 704) — on ONE container, at 0.97.** The displacement is baked into
  the submitted primitive and absent from the container's stored UV pool, so every span the kit
  holds is the *undisplaced* coordinate. Five riders stay open and all five are carried verbatim in
  a quotable constant (`depth_attribution.U_DISPLACEMENT_CAVEAT`): generalisation beyond that one
  container; the *operation* (only the values 0 and 128 appear there, so "add 128" and "toggle the
  top bit" are the same function on every observation); depth (every population read was 8bpp);
  wrap-vs-clamp at the byte boundary; and that per-slot is established only where slot equals
  record, so `ORDER_UNMEASURED` is untouched. **Adopting** the displacement into the derivation is
  now an owner decision rather than a blocked one — the instrument that gated it has been built,
  deployed, cast and read.
- `CellHazards.second_array` names, per reader, the non-zero pair and both candidate effective
  columns — `swapped_*` is the measured reading, `original_*` is retained as the retired one so the
  disclosure stays auditable; both are informational, and empty wherever the caller did not consult
  a W6b-2+ channel.
  One new refusal class, `second-array-mover`, is **appended alongside** (the `spill-vs-own-page`
  precedent, never displacing the refusal an author would otherwise be shown) on a cell **all** of
  whose readers carry a non-zero pair: the conservative, labelling-independent predicate.
  `export-art`'s manifest and scaffold print the disclosure before the paint, and a build gate
  refuses an enabled row on such a cell until it says
  `acknowledge_second_array_displacement = true` — a literal boolean, and the one acknowledgement
  in this lane that pairs with **no** `expect_bpp`, because it admits a question about READERSHIP
  and there is no derived number to check it against.
- **The emission set does not move**: same pages, same names, same depths, same bytes. The class
  is in neither `_UNADDRESSABLE` nor `_EXPORT_BLOCKING` (addressability delta 0, export delta 0),
  it adds no `hazards.names` slug and no `DEPTH_SOURCES` token, no published constant moves, and
  under the census channel set it is not stated at all.
- Measured over the 372-container corpus and re-derivation-pinned: **52 cells in 29 containers**
  fire, **47 of them fully open today** (`export-art` hands them back as licensed paintable pages
  with no other refusal). The predicate is labelling-independent *by construction* — it never asks
  which halfword moves which axis and never applies a displacement — which is why the s77 read moved
  none of those three numbers. It is a strict superset of the two earlier lost-cell lists (16 / 19,
  union 35) and contains both completely; since the read, both of those lists are known to be
  **u-only** models, and re-rolling the measured two-axis arithmetic over the same corpus reproduces
  this firing set exactly. `ef038 cell.s0.x640_y256` — 20 movers and seven zero-pair controls — is
  deliberately NOT in it, and a cell read only through a multi-part record cannot be tested at all,
  because pairing an array entry to a binding slot is the order this kit does not claim.

### Changed — summon-reskin: the second array is **ADOPTED** (the effective cover)
- **The kit now models the displacement it used to only disclose**, and this is the first rung in
  that lane that deliberately changes behaviour. Three more log-only casts closed the two riders the
  disclosure rode on: the mechanism GENERALISED (ef227 — key isolated, tri ratio 1.00, control gate
  PASS — and ef446, control gate PASS, with ef038 reproducing in the same log), and the OPERATION was
  settled by a decisive value test on ef227 (raw pool `{0, 25, 55, 85, 111}`, observed extremes
  `{16, 41, 101, 127}` = pool + 16; OR would read 25/85, XOR 9/69, and a FLAG reading predicts a
  disjoint range). **The model is `linear-add-v1`: effective = stored + halfword, per axis,
  independently — pair position 0 onto `u` (texels, converted at the page's own depth), position 1
  onto `v` (VRAM lines, depth-free).**
- **One named seam, one law, both enforced at the call site.** `sampled_halfword` / `effective_cell`
  are the only arithmetic; `assert_intra_page` re-checks THE INTRA-PAGE LAW on every displaced
  binding and fails CLOSED. A tpage is cell-aligned and stored `u,v` are bytes, so a displaced read
  never leaves its own page — measured 340/340 — which is what makes linear-vs-mod-256-wrap
  degenerate, an arriving reader's depth non-extrapolated, and an off-VRAM read impossible.
  ⚠ **And the call site is `effective_cell_readers`, not `bound_models`** — the law is spent where a
  caller has ASKED for the effective join, so only a scope that named `so-displaced` can fail on it.
  Asserting inside the rasteriser (which every scope walks) gave a law-breaking container a way to
  refuse under `CENSUS_CHANNELS` and `LICENSED_CHANNELS` as well, two frozen surfaces that never read
  `effective_cover` at all — which made "the frozen surfaces are unmoved" a fact about the stock 372
  (where the law holds 340/340 and the assertion never fires) instead of a property of the code.
  Demonstrated by inflating one incumbent pair on ef038 (record `0x29dbc`, arrayB `@0x29dc8`,
  `du` 128 → 250): before, all three scopes raised; after, only `EDIT_CHANNELS` does, and all four
  measured surfaces (census / licensed / edit / edit-with-ack) are byte-identical across the fix.
- **Two covers, named, never merged.** `BoundModel.cover` / `cell_readers` keep their meaning forever
  (they are what the writer side, the census freeze and the audit trail are written about);
  `BoundModel.effective_cover` / `effective_cell_readers` answer READERSHIP. They are the **same
  object** wherever nothing is displaced (189 of 340 readers), so the undisplaced path is untouched
  by construction. `columns`/`spills` stay BOUND; `effective_columns`/`effective_spills` are what THE
  NAME-EVERY-COLUMN obligation is now taken on (58 bound → 60 effective).
- **THE DISPLACED CELL NOW NAMES ITS DESTINATION.** `displaced-readerless` (**45 cells / 26
  containers**, 41 of them carrying no other export-blocking refusal) and
  `displaced-readership-substituted` (**7 cells / 10 page names**, where a *disjoint foreign* set
  arrives instead, 4 of them at another depth) now REFUSE by name, in both `_UNADDRESSABLE` and
  `_EXPORT_BLOCKING`. ⚠ The
  number is **45, not the impact scoping's 16**: that list modelled `u` alone, and v-only
  displacement is the largest mover class in the corpus (68 of 151). Both are lifted by the
  **existing** `acknowledge_second_array_displacement`, the same key those rows already needed in
  order to build — so no row that built yesterday needs a new word today; what moves is that the
  refusal now arrives at EXPORT time and NAMES where the readers went.
- **⚠ THE ACKNOWLEDGEMENT LIFTS THE REFUSAL, NOT THE GUARANTEE, and the ledger is measured rather
  than promised.** Over all **55 page names** the two lifted classes cover, with the key said (BEFORE
  = the pre-adoption package at `LICENSED_CHANNELS`, AFTER = the adopted one at `EDIT_CHANNELS` with
  the ack): **39 come back as the identical picture** (34 of them moving only `depth_source`, `so-uv`
  → `so-page` — the column's own depth at the same bit depth, which is the case the fallback was
  written for); **6 come back as a DIFFERENT picture**, and **four of those flip 4 bpp → 8 bpp** —
  ef179 `cell.id9.s0.x768_y256`, ef227 `cell.s0.x512_y256`, ef498 `cell.id9.s0.x832_y256`, ef498
  `cell.s0.x576_y256`, i.e. *the same 16,384 bytes handed back as a different picture*, half the
  texel width through a 256-entry key instead of a 16-entry one (the other two, ef226
  `cell.s0.x512_y256` and ef424 `cell.s0.x448_y384`, keep their depth and change CLUT); and **10 come
  back with nothing at all**, falling through to `depth-unknown` (9) or `channel-g-dual-depth` (1),
  because the channel that has to speak next does not always have an answer either. The ledger is
  stated in the two class texts, in `U_DISPLACEMENT_ACK_WARNING` (printed on every build that says
  the key) and in `docs/SUMMONS.md`. An author who acks and is handed another palette — or nothing —
  was told that was possible.
- **The gain half is licensed by DEFAULT, behind no new key: 70 declared cells acquire a reader they
  do not bind, 29 of them (30 page names) refused `depth-unknown` before.** It is not a new channel —
  it is the sampling arithmetic of one the licensed path already consults, and the arriving reader
  states its depth off its own `so` record at an address inside that same record's tpage. ⚠ **And
  that is this rung's honest limit, stated as an asymmetry rather than left implicit: the loss half
  fails LOUDLY (a refusal, overridable with a stated key) and the gain half fails SILENTLY (no key,
  nothing to contradict it) — so if `linear-add-v1` does not hold on a given container, a perfect
  repaint of a gained cell is invisible in game with no error anywhere.** The scaffold now prints
  `GAINED` on every such cell and `DISPLACEMENT_DERIVATION` carries the sentence; a cast is the only
  thing that closes it. **27 of the
  30 hand back a paintable PNG** — 21 out of `export-art`'s default indexed lane and 6 (all 15 bpp)
  via `--art-lane direct15`; the remaining **3 hand back nothing in either lane**, all on ef038, all
  blocked by the pre-existing and correct `program-vram-write` refusal. ⚠ **So the headline case is
  ef407, not ef038.** Both derive identically — `cell.s0.x640_y256` goes 27 readers → 7, `x704_y256`
  gains 1 and **`x704_y384` gains 20**, the LOWER stacked cell because the `v` term puts them there —
  but `export-art --ef 38` writes none of those pictures, before this rung or after it — for two
  different reasons, which the docs now separate rather than crediting the older one for both: ef038
  is a program-VRAM writer, so three of its four column-640/704 pages carry `program-vram-write`,
  while the fourth (`cell.s0.x640_y384`) is withdrawn by this rung's own `displaced-readerless`.
  ef407 carries no such refusal and
  both gained pages export. *Derivable is not deliverable*, and the docs now say which is which. One
  new VETO, `displaced-vs-page-depth` (1 cell), where an arriving reader contradicts the channel-G
  page depth that was serving a readerless cell: two values is a hazard, not a vote — and no
  acknowledgement lifts it, so it is not in the 55 above.
- **A third channel set, so the delta is a diff between two NAMED sets and never a number that moved
  under a constant's old name.** `CENSUS_CHANNELS` (frozen at W6b-1) / `LICENSED_CHANNELS` (frozen at
  the W6b-3 scope) / **`EDIT_CHANNELS`** (= `LICENSED_CHANNELS + ("so-displaced",)`, the new default
  of `texel_page`, `export_art`, `build`, `scenery_texel_pages`, `scenery_lines`). Measured over all
  372 containers: **the census and W6b-3 surfaces are byte-identical before and after — 0 moved
  pages, 0 moved cells, 0 moved refusal classes, 0 moved bytes on 372/372.** ⚠ One deliberate
  exception a literal diff will show: the 55 `second-array-mover` records on the licensed surface
  carry a rewritten *reason string*, because the caveat they quote was rewritten when the mechanism
  generalised past one container. Nothing addressable moves with it, and `u1_gates` U6 pins the
  retired wording ABSENT so a silent revert fails loud. On the edit surface: pages 300 → 289, refusals
  2,499 → 2,453, exportable pages 211 → 202, exported bytes 3,457,024 → 3,309,568 (−147,456 =
  9 × 0x4000), with all 41 newly-exportable and 50 no-longer-exportable names listed by class.
  **And the 2,499 → 2,453 is nameable term by term, not just netted** (refusal RECORDS, 372/372;
  a cell can carry two classes, which is why records exceed distinct names): −55 `second-array-mover`
  and −15 `channel-g-dual-depth` (both retired by the new join), −30 `depth-unknown` and −11
  `program-vram-write` (cells that gained an attributable reader), +45 `displaced-readerless`,
  +10 `displaced-readership-substituted`, +1 `displaced-vs-page-depth`, and **+9
  `same-bytes-two-depths`** — the last because a displaced reader can move a depth conflict into the
  *other* stacked cell of its column, which is the same mechanism that resolved ef227
  `cell.s0.x576_y256` and raised it at `x576_y384`. Every other class is unmoved.
- `export-art --acknowledge-displacement` exports the loss half's refused names too (the build still
  needs the row key), so an author who overrides the derivation can get whatever channel still speaks
  for the cell — subject to the ledger two bullets up: 10 of the 55 have nothing left to speak.
  `TexelPage.readership` (`"bound"` / `"displaced"`) is a separate field, never an overload of
  `depth_source`. New re-derivation-pinned constants sit BESIDE the W6b-3 ones rather than moving
  them — `SECOND_ARRAY_MOVER_CELLS = 52` is the **VACATE** count (every reader of the cell leaves it)
  and `DISPLACED_READERLESS_CELLS = 45` is the **READERLESS** one; ⚠ they are two readings of one
  population and **not addends** (45 + 7 = 52, 41 + 6 = 47, over the same 29 containers).
- **The reach is unchanged and stated with a number.** `Binding.mover` still refuses to answer on a
  `P >= 2` record, so `ORDER_UNMEASURED` is untouched and **142 novel slots carry a pair nothing here
  models** — the effective cover is a LOWER BOUND on readership, and every string in the lane says
  *"no reader this kit can attribute samples here"*, never *"nothing reads it"*.

### Added — `world-coastnav`: vehicle-legality classes on a synthetic coast
- The Southern Ring's in-game-proven coast-nav stamp (R5d sail-through seal + R5e standoff
  belt) is a kit verb: re-derives every deployed sea override's water-triangle topograph into
  KEEL-BLOCK 56 (under high ground — the seal) / STANDOFF BELT 55 (within 3.5u of a wall) /
  BEACH 53 / CLIFF-FRONT 54, topo bits only, geometry and look byte-preserved. Two landability
  policies: `land-anywhere` (the ring's plateau isles) and `cliffs-refuse` (stock grammar —
  53 fronts beaches only, so a cliff-ringed island can be sailed to but never disembarked on).
  `--disc`/`--mirror-disc` aware; dry-run by default.
- The hour-class runtime is gone, killed twice over — measured on the same five cells as the
  hour-class baseline, results byte-identical per the gate probe:
  1. a uniform-grid triangle index under the stacked ground query (bucketed 2D AABBs, first-hit
     order preserved exactly — calibrated 0/1500 mismatches against the linear scan): ~6×;
  2. the real villain, found by profile, was not Python math at all: **97% of the remaining time
     was UnityPy re-parsing p0data bundles** — on a synthetic disc the loader's stock fallback
     rescanned every bundle per missing part (`_worldmap_env` cached only winners). The loader
     now reads a synthetic namespace's deployed overrides directly, and a no-bundle disc is
     memoized per process. Full five-cell pass: **635s → 0.8s**.
- `island.landmass` (`world-island`) stamps its own cells with the navigation classes **by
  default** after every real deploy — before the Disc-4 mirror, so parity carries the stamped
  bytes. A fresh mint no longer ships boat-permeable straddling triangles, a missing standoff
  belt, or a get-off-less coast. `--coastnav-policy {land-anywhere,cliffs-refuse}` picks the
  landability language; `--skip-coastnav` opts out (A/B work only). Re-stamping is idempotent.
- `terrain.reclaim` deliberately does NOT stamp: per the engine source a sidecar-less reclaimed
  cell resolves to the inland donor (no sea sub-meshes) and never loads `SeaBlockPrefab`, so it
  holds no water at all — miss-sealed at the cell edge by the invisible-wall rule, with no
  in-cell fringe to classify.

### Added — the read/write disc split reaches every world verb
- `world-transplant`, `world-fuse`, `world-forest`, `world-hill`, `world-mountain` and
  `world-minimap` take `--target-disc` (and, where the open-ocean probe applies,
  `--all-sea-target`), completing the split `world-terrain`/`world-reclaim`/`world-coast`/
  `world-island` shipped with: `--disc` stays the stock read disc, the overrides land in the
  target namespace (9 = a Path D synthetic world). The interior verbs move their deployed-
  island READ too, like `terrain.reshape` — before this, a carve near a synthetic island
  silently read and reshaped whatever real disc-1 override sat at those coordinates.

### Added — `ff9mapkit floorplan`: a hand-drawn multi-room plan becomes a wired dungeon
- One verb turns a `floorplan.json` (room outlines + declared doors, in one shared plan
  frame) into a buildable campaign: one FF9 field per room, gateways both ways, an
  arrival position **and facing** per side, encounters, and save-point siting. Each room
  gets its own member directory with a `field.toml`, a `walkmesh.obj` and placeholder art
  clipped to the room's real footprint, plus a `campaign.toml` and the re-editable
  sidecar. `build-all` then compiles the whole set, and each room deploys **additively**
  with `deploy_field.py --id N` (never `deploy-campaign --apply`, which replaces a whole
  mod folder wholesale).
- THE DRAWN-MESH LAW holds throughout: the human's polygon IS the walkmesh, and the
  composer only handles topology. It offers candidate shared walls; the author declares
  which are doors.
- Fifteen gates refuse a plan that cannot become a legal dungeon, and they refuse rather
  than warn — a self-intersecting outline, a room with nowhere to stand or a walkable area
  split by a too-narrow neck, overlapping rooms, a door too shallow for the player's
  centre to enter, an arrival that would strand or instantly re-warp the player, an
  arrival with no facing, a room that will not fit its own camera, two trigger zones that
  would starve each other, and an id already registered in the live game. Warnings cover
  the judgment calls (an unreachable room, a cramped floor, an arrival a step from another
  zone).
- The id pre-flight reads the live `DictionaryPatch` stack **before** minting ids, so a
  collision surfaces while you are authoring rather than at deploy time — and an
  unreadable stack reports UNKNOWN, never "clear".
- `scene.placeholder.write_placeholders` accepts `floor_tris=` and clips the checkerboard
  to the real walkable footprint. Its rectangular frame previously painted ground the
  player cannot reach (68% of one composed room), inverting the placeholder's own purpose
  as an in-game alignment check.

### Added — the Workspace **Floorplan** tab: draw the dungeon, watch the gates
- A new tab on the Author rail beside Map. Draw room outlines on a plan-view chart,
  click a shared wall to turn it into a door, press Compose. The composer runs on
  **every edit**, so its gates paint on the drawing itself — an offending room or
  door strokes in the error colour, every problem is listed in the author's own
  words, and Compose stays disabled while any error stands. Compose then opens the
  finished dungeon as a live campaign, so its graph is immediately visible on the
  Map tab.
- The chart is a chart, not a camera: one isotropic pixel↔world scale with +z up
  the screen, matching the layout probe's frame so the two instruments agree. A
  click lands on the cursor after any zoom or pan.
- Undo is per-session and covers the whole plan, so declaring a door — which
  writes both sides at once — is a single step. A half-undone door would be a
  gateway with no arrival.

### Fixed — two rooms snapped into a shared wall were refused as overlapping
- Assembling two rooms so they share a wall — the thing snapping exists to make
  possible — reported "rooms ROOM1 and ROOM2 overlap: they share floor area", with
  nothing visibly wrong and nothing the author could adjust.
- The segment test underneath treats a cross product of exactly zero as one side
  rather than as contact, so two walls meeting at a shared corner read as a
  crossing. That inclusiveness is wanted elsewhere — an outline whose wall ends on
  another of its own walls is degenerate, and it is what catches two parallel
  rooms overlapping in a band where no corner is strictly inside anything — so the
  overlap check now ignores wall pairs that meet at a shared corner, which is what
  an abutment is, instead of the shared test being weakened. Tightening that test
  was tried first and measurably broke both of the cases it protects.
- The bug is as old as the composer and could not be reached until now: corners
  aimed by hand land close enough to count as a shared wall but never on the same
  exact coordinate, so nothing ever produced the exact contact that triggers it.
- Attaching a corner to the middle of a wall is exact too: the stored coordinates
  are whole numbers and a wall is usually diagonal, so rounding could put the
  corner a fraction of a unit inside its neighbour — a real, invisible overlap.
  The rounding now always goes to the outside, where a sub-unit gap is harmless.

### Fixed — a corner two rooms share can now be grabbed, and moving it keeps them joined
- When you snapped one room's corner onto another's, the resulting stacked handles
  were picked by room order, so only the room drawn first could be grabbed — the other
  room's corner could not be selected at all.
- Coincident corners now move together. That is the point of them: they are stacked
  only because you snapped them into a shared wall, and dragging one out alone would
  tear that wall apart — leaving you to re-make it by landing the other corner within
  eight units by hand, which is the thing snapping exists to spare you. The coordinate
  chip says when a corner is welded, one Undo puts the whole group back, and dragging a
  room bodily still separates it from its neighbour.

### Fixed — the spawn-near-a-door warning fired on ordinary rooms
- The composer warns when a room's spawn sits in line with a trigger zone and close
  enough that "one step could fire it". The reach was four times the player's radius,
  and the distance it measures is fixed by the room's size — so it warned about every
  room under about 1140 units across. A first two-room dungeon with a single door and
  nothing wrong with it collected two of these.
- The reach is now the player's own diameter, which is what the message actually
  claims: inside one body-length, being displaced into the zone is possible; beyond it
  the player has to walk there deliberately. A spawn genuinely a step from a trigger is
  still caught, with a wide margin.

### Fixed — the placeholder floor did not follow a room that wasn't a rectangle
- The checkerboard a composed room ships as stand-in art is there for one reason: to
  let you see, in-game, whether the walkable area matches the art. On a freeform room
  it did the opposite. The dark base was clipped to the real footprint, but each light
  square was painted whole whenever its centre fell inside and skipped entirely
  otherwise — so squares hung off the edges and notches appeared where a square
  straddling the boundary was dropped. The floor read as a ragged chessboard rather
  than as the room's own shape, and some of the paint sat over ground the player
  cannot reach.
- On a rectangle every square is wholly in or wholly out, so this never showed and no
  test noticed. It took walking a five-sided room in-game to see it.
- The footprint is now a per-pixel stencil, so a square that straddles the edge comes
  out cut off at the edge. Measured on the dungeon that found it: 2.57% and 2.87% of
  painted pixels fell outside the walkable area; now none do.

### Added — the Place tab now works on fields you made yourself, not just forks of real ones
- Place let you click content onto a field's background art, but only if that field was
  forked from a real FF9 room. Anything you made yourself — a room composed from a
  floorplan, a new field from the toolbar, a field traced from a photo — was turned away
  with "a novel field places content in Blender or the Editor forms".
- That test was about where the field came from, not about whether it could be placed on.
  Clicking on a floor needs a camera and a walkmesh, and a field you made has both — a
  composed room's camera is in fact known more precisely than a forked one's, because the
  composer worked it out rather than reading it back from the game.
- All three now open at once: composed rooms, new-field scaffolds, and traced fields. The
  background is the field's own layers, composited; the camera and walkmesh come from the
  same resolvers the build uses, so what you click on is what ships. No game install is
  needed.
- Place still refuses a field that has never been saved, since the surface is resolved from
  the file on disk.

### Fixed — recomposing a floorplan silently destroyed anything you had added to its rooms
- Composing a dungeon writes one field file per room. Adding an NPC, a chest or an event
  to one of those rooms — which is what the Place tab and the editor forms do — and then
  recomposing the *unchanged* plan deleted it. No error, no warning, and the command
  reported success.
- Recomposing now refuses when a room carries anything the composer did not put there,
  and says which rooms and which content. `--force` recomposes anyway and discards it.
  Preserving that content through a recompose, rather than refusing, is the next step.
- The check runs before anything is written, so a refusal leaves the campaign exactly as
  it was rather than half-rewritten.
- **A dungeon no longer collides with itself.** Room ids are recorded when a dungeon is
  first composed, and the check that guards against clashing with fields already in your
  game now knows which of those are your own rooms. Previously, deploying a dungeon and
  then recomposing it renumbered every room — invalidating the deploy commands you had
  written down, any gateway pointing into it, and the New Game wiring.

### Added — a room too wide for one screen now scrolls, and one too big to render is refused
- FF9 fields can be painted wider than the screen and pan to follow the player, and the
  toolkit has supported that for a while — but the floorplan composer always emitted a
  single screen-sized camera. A long hall therefore framed by pushing the camera back
  until the whole room fitted, which on a 9762-unit room meant a distance of 18227 and a
  character about two and a half pixels tall.
- Rooms are now fitted at screen size first and only widened when that is not legible,
  in screen-width steps, up to the widest painting FF9 itself ships. The same room now
  paints 960 wide and renders the character at nearly three times the size. A room that
  already framed well is untouched and emits exactly what it did before.
- **A room that cannot be rendered legibly even at the widest painting is now refused
  rather than quietly composed.** The thresholds are measured, not chosen: across all 741
  cameras in the shipped game a character covers 9.3 pixels at the median and 3.9 at the
  5th percentile, so anything below that 5th percentile is refused and anything below the
  25th is warned about.
- The refusal names the fix, and checks it first. Width costs far more than depth — the
  same corridor is nearly three times cheaper drawn the other way round — so where
  rotating the room would genuinely help, it says so with the size that would result;
  where it would not, it says to split the room into two joined by a door, which is what
  FF9 does with a large space and what this composer already builds.

### Fixed — the Floorplan chart moved under the cursor while you were drawing on it
- Every corner you placed recomputed the chart's extent from the outline *in progress*,
  so the first corner of a room collapsed that extent to a fraction of its size and the
  view re-centred — the whole chart jumped, measured at 375px right and 253px down on the
  first click alone. Four clicks aimed at a rectangle on screen produced a misshapen room,
  because every click after the first landed in a different frame.
- It reported as three separate problems and was one: the view shifting as points were
  added, the same spot being impossible to click twice, and the first point appearing to
  land at the origin. That last one is the same bug wearing a disguise — the point never
  moved, the chart did, until the point was sitting where the origin marker had been.
- A second, subtler slide sat behind the first: with a corner placed, simply moving the
  mouse dragged the chart about a pixel per redraw — and the rubber band redraws on every
  mouse move — until it hit a limit and stopped. That one only happened when the chart's
  width was an odd number of pixels, which is why it survived a test suite whose window
  is always an even width.
- The chart now holds still in both cases. Its extent is derived from the rooms alone and
  never from where the view happens to be looking, it grows but never shrinks out from
  under you, Ctrl+0 still frames the rooms rather than wherever you had panned to, and
  scrollbars stay hidden.

### Added — corners and walls snap, so two rooms can actually be made to share one
- Two rooms are offered as a door only if their walls lie within 8 world units, and the
  chart opens at roughly 9 units per screen pixel — so a pixel-perfect click was outside
  the tolerance before the mouse even moved, and all you got was "No shared wall here"
  with nothing to correct. Placing a room against its neighbour was a matter of zooming
  in and nudging until it took.
- A corner or wall within ~12 screen pixels now captures the point you are placing or
  dragging, exactly, and the rubber band previews where it will land so you can see the
  capture before you commit. Corners win over walls, and a corner being dragged never
  snaps to its own room. Measured on identical clicks 3–5px off a shared wall: no door
  offered before, the entire 1049-unit wall offered after.

### Fixed — the Floorplan tab's live gate was a stall: a gesture cost ~17s, now ~0.6s
- Every edit re-derived the **whole** plan from scratch, so on an eight-room dungeon every
  single gesture cost what drawing the plan cost — about 17 seconds, with Compose disabled
  throughout. Typing a name spawned one background check per keystroke, nine of them for a
  nine-character name, which then stacked. Past about four rooms the feature that makes the
  tab worth using stopped being usable.
- A gesture now re-derives only what it touched, and **costs the same on a twelve-room plan
  as on a three-room one** — about 0.6s either way. Re-checking a plan whose geometry did
  not move is 4–18ms, and the first judge of a freshly drawn eight-room plan is ~4s.
- Four changes, largest win first: the tab carries one geometry cache **across** checks
  (keyed on each room's own coordinates, which is the only thing that decides "unchanged"
  here — room records are edited in place, and undo restores a copy, so object identity
  is wrong in both directions); the two grid samplers walk the polygon by rows instead of
  testing every cell of its bounding box; the spawn search rejects cells against a grown
  bounding box before measuring; and a check that has been superseded now stops instead of
  running to completion. `ff9mapkit floorplan` on the command line gets the same speedup.
- The cache memoizes the *answers* — cell counts, fractions, sites — not the geometry
  behind them, and the full grids live only for the duration of one check. The first cut
  kept the grids, which retained over a gigabyte after a few seconds of dragging and, worse,
  fell off a cliff at 33 doors: a check touches each entry exactly once in a fixed order, so
  past the cache's size limit the entry evicted is always the one wanted next and the hit
  rate is not reduced but zero. A 25-room dungeon went back to 4.3s per gesture. Both are
  fenced now.
- **The gates say exactly what they said before.** Every step was gated on a 400-plan
  differential against the previous implementation — errors, warnings, ids, spawns,
  arrivals, facings, camera fits and door quads, all identical — and the row sampler is
  fenced bitwise against the original double loop it replaced.
- Reproduce any number with `studies/click-authoring/gate_bench.py` — `--drag N` measures
  before and after in one run, loading the previous implementation from git rather than
  guessing at it.

### Fixed — a background check finishing mid-drag silently ate the drag (Floorplan tab)
- Dragging a room or a corner while the live gate was running could end with the room
  snapping back to where it started: the check's result re-fed the chart, which discarded
  the in-progress drag, so the mouse release committed nothing — no move, no undo entry,
  no message. A release that had barely travelled was then re-read as a click, which in
  Rooms mode silently started a new outline. It needed a slow check to reproduce, which
  the fix above makes rare, so it is fixed outright rather than left to chance: the
  author's live gesture now outranks a result landing under it.

### Fixed — `[encounter] scene` accepted a battle-scene NAME at lint, then died at build
- `scene = "BSC_CA_E013"` linted **clean** — `lint_logic` resolved the name through the
  catalog to report on it — and then the build compiled it with a bare `int()`, so the
  same value failed as `invalid literal for int() with base 10: 'BSC_CA_E013'` with no
  field, no key and no suggestion. Every shipped example writes a numeric id, so nothing
  exercised the name path through a build.
- Names now resolve in the build (`build.resolve_encounter_scenes`), consistent with what
  the lint already advertised and with `[[npc]] model`'s GEO names. Both consumers go
  through the one seam — the `.eb` `SetRandomBattles` injection and the scene-keyed
  BattlePatch `Battle:`/`Music:` line, which would otherwise have emitted an unmatchable
  `Battle: BSC_…`. A numeric id still passes through untouched, so existing builds stay
  byte-identical.
- The plural `scenes` pool resolves names per slot, and both keys are **fenced**: an
  unresolvable name is now a fatal `validate` problem naming the field, the key (with the
  slot index for a pool) and did-you-mean candidates — so the value either builds or fails
  lint. A pool that isn't exactly 4 slots also fails lint instead of raising mid-build.
- Two silent-nothing gaps in the same block closed: the model-bucket (`BSC_B3_*`,
  in-game null-ref) warning now covers the `scenes` pool, not just `scene`; and a pool
  with **no `scene`** — which arms nothing, since `has_encounter` tests `scene` alone —
  now warns instead of building an encounter-free field in silence.

### Fixed — the form editor was stricter than the format it edits (and its placeholder said so)
- Once `[encounter] scene` took a battle-scene NAME (above), the form editor still parsed it as an
  int: typing `BSC_CA_E013` — the very thing the line edit's own placeholder invited, "a encounter
  name or id" — was refused at **Save** with `expected a whole number`, on a value that is legal TOML
  and builds. `[[npc]] model` had the same split all along: the build resolves a GEO name, `FORMAT.md`
  documents one, and the Inspector's preflight validates one, but the form rejected it.
- Both are now the new `forms.CATINT` kind — a number stays an id, a name stays a **name** (the build
  resolves it, so re-opening and saving no longer rewrites the author's file). Two rules the two
  editors used to duplicate inline now have one owner each: `forms.wants_id` (Browse still fills the
  numeric **id**, unchanged for every user — a warm `encounter` picker LABEL reads "Goblin, Fang —
  Evil Forest (field 250, random)", which no resolver takes) and `forms.placeholder_for`, which can no
  longer promise a name the field's own parser would refuse. The id-only catalogs say so: `song` and
  the carried-effect picker now read "a song id" / "a sps id".
- `[[battle_bgm]] scene` takes a `BSC_` name too. It named the same thing as `[encounter] scene` and
  accepted less, so one file could build a name in one block and fail lint on it in the other; both
  now go through one resolver, and an unknown name fails lint naming the ROW. `song` stays
  integers-only — an akao song-play id has no name catalog — and the error says that.
- The Inspector RESOLVES a named scene instead of falling back to plain text, so the field that
  authors the friendlier value keeps both the `— #67` gloss and the Battle-tab jump the row exists
  for. New pinned snap surfaces `form:encounter` / `form:encounter-named` / `form:music` / `form:npc`
  — the logic forms had none, which is how a placeholder could contradict its own parser unseen.

### Fixed — the layout probe called a correct field COLLIDING
- `tools/field_layout_probe.py` compared `[player] spawn` against `[[player.arrival]]`
  rows as if they were two actors. An entrance-0 arrival is conventionally equal to the
  spawn, so a correct field reported "0u apart -- COLLIDING". The player is exactly one of
  them at a time; NPC-vs-spawn collisions still report.

### Added — the `so` record is a multi-part ARRAY: a reader fix, the witness partition, CHANNEL A (W6b-3)
- **The reader was wrong, and the consequence was a wrong ANSWER, not a missing one.** An `so` binding
  record is `8 + 8P` bytes carrying a **P-entry binding array** (`P` runs 0–7 in the corpus);
  `reskin.so_record` hard-probed `recLen ∈ {0x08, 0x10}` and returned `None` for anything longer, so
  **126 records and all 309 of their binding slots were invisible** — the record, slot 0, and every later
  slot together. The palette lane's `DERIVED PRIVATE` verdict means *exactly one GEOM model binds this
  cell*, so the shipped `summon-reskin` published **five FALSE `DERIVED PRIVATE` verdicts**, named and
  now repaired: `ef179 pal.s0.x16_y244.e16` · `ef179 pal.s0.x0_y248.e256` · `ef381 pal.s0.x0_y248.e256`
  (**seven** distinct models bind that one) · `ef438 pal.s0.x0_y242.e256` · `ef438 pal.s0.x0_y248.e256`.
  The acceptance test now rests on **`arrayB` at +0x06** (`== 8 + 4P`), an independent halfword agreeing
  502/502 and taking a value outside a `P<=1` corpus's two constants on 126 of 126 novel records —
  `recLen == 8 + 8P` is near-tautological given `P := (recLen-8)//8` and is flagged as such.
- **THE SAFETY FIX, unconditional.** Verdicts over the 372-container corpus through the shipped
  `palette_map`: **148 DERIVED PRIVATE / 129 DERIVED SHARED / 2,395 SHARED-UNKNOWN / 301 UNBOUND at
  COMPLETE / 122 UNBOUND at COMPLETE (NOVEL-DEPENDENT)** = 3,095. False-private **5 → 0**. The 205-palette
  move closes exactly as **83 gaining a named binder + 122 whose container's coverage flipped**, and the
  83 split **46 PRIVATE + 37 SHARED** by distinct GEOM model (43 + 40 by slot, measured and printed
  beside it). Guard transitions measured on the field `_gate_shared` actually reads: **46 palettes
  released, 5 newly armed — and the 5 are exactly the five historical false-private names.**
- **★ THE VERDICT COUNTS MODELS, NEVER SLOTS.** One model can bind one palette from two entries of its
  own array, and the reason string says *"GEOM models"*. Two measured populations: **3 palettes flip the
  VERDICT** (`ef179 x0_y249`, `ef186 x0_y248`, `ef415 x0_y248` — on two of them the model's two entries
  name *different columns*) and **2 more keep the verdict with a wrong printed count** (`ef186 x0_y252`
  5→4 models, `ef226 x0_y249` 7→6). A single model binding through several entries now says *"through N
  entries of its own binding array"*. **0 cases corpus-wide of one model binding one palette at two
  different depths**, so the dedupe can never collapse a depth conflict.
- **★ COVERAGE STATES ITS READER POPULATION — and the release it would have granted is measured, not
  taken.** The true record population flips `so`-coverage to COMPLETE on **19 containers** (ef058, 094,
  154, 155, 179, 186, 237, 261, 290, 300, 382, 390, 415, 424, 431, 432, 438, 439, 490), which would have
  released **122 palettes** from `acknowledge_shared` with no binder naming any of them — 24× the
  population of the five verdicts the fix repairs, moving the permissive way. Coverage stays honest
  (a figure the container's own bytes contradict would be the same defect class the fix repairs) and the
  guard stays **ARMED**: those palettes take a new verdict, `UNBOUND at COMPLETE so-coverage
  (NOVEL-DEPENDENT)`, `shared = True`, whose reason states how many GEOM blocks the new reader bought,
  that nothing about that reading is in-game, and that the release awaits owner ratification or a cast.
  **0 palettes released by the coverage flip.** (`W6b3-ARCHIVE.md` §8.2's "the fix makes the kit less
  conservative only in the `len(binders) == 1` branch" is corrected in the same breath — it is wrong;
  there is a second, larger permissive direction and only an explicit decision keeps it shut.)
- **★ THE WITNESS PARTITION — and why no published count moved.** A binding slot's witness class is a
  property of the **record**: `P <= 1` is INCUMBENT (the old reader accepted it), `P >= 2` is NOVEL in
  its entirety. Filtering the fixed reader to INCUMBENT reproduces the pre-fix population **exactly —
  340/340 bindings and 376/376 accepted records, tuple for tuple, 0 of 372 containers differing** — so
  containment is a statement about the consumers' **input**, not an inspection of their output.
  `attribution()` now answers the TRUE population by default (its old answer was a defect, not a scope
  choice); everything that means CHANNEL G or THE CENSUS **says `witness=WITNESS_INCUMBENT` explicitly**,
  at ten call sites, each with a comment naming what it protects and every one findable by grep.
  `w6b_gates` / `w4` / `w5` / `w7` are green **untouched**, as the control.
- **CHANNEL A DISCLOSES — 65 cells, behind `acknowledge_array_derived_depth` + a matching `expect_bpp`.**
  New `depth_source = "so-array"`, new `reskin.array_depth_view` (a WRAPPER on `page_depth_view`'s novel
  half — one derivation, two names, not two scanners). **A is for ARRAY, not ARCHIVE**: the round's own
  id-2-archive premise was falsified, the 126 invisible records split id-2 61 / id-6 53 / id-3 12, and
  the id-2 framing would have cost 52% of the reach. It DISCLOSES rather than licenses because what
  licensed channel G was never binding-ness — it was reading the record the kit already reads, an
  informative calibration, **and a cast**. Channel A has the first only: **0 hits, 4 misses, 2 vacuous
  passes** over six named cells, carried as a call-sited constant on every disclosure and both refusals.
  The 65 split **26 clean + 34 class-C + 7 program-VRAM-write** (2 carry two, so they account for 65 once).
- **Two new refusals, and one of them TAKES A PAGE AWAY.** `array-dual-depth` — **12 cells over 6
  columns** named at two depths by the multi-part entries, derived live and never tabled. They split
  **8 + 4** on an exact predicate (*is the column's incumbent depth set empty?*) and the split is
  printed, but **treatment is uniform: all 12 refuse**, including the 4 whose columns `so-uv`/`so-page`
  does serve — channel A holds **veto power and never emission power**, and the softer
  state-it-alongside treatment is recorded as considered and not shipped. `array-vs-column-depth` —
  **2 cells, one column (`ef184 x448`), the only one in the corpus satisfying the predicate**: channel G
  says 4bpp, an entry of a multi-part record says 8bpp, and their UV covers overlap. *A licence
  contradicted by its own instrument is void for that column.* Both classes are `_UNADDRESSABLE`, and
  this is the rung's one non-zero addressability decision, gated by a counterfactual measuring
  **exactly −6 cells on the licensed path (`so-uv` 187→183, `so-page` 57→55, depth-unknown 2,298→2,290)
  and 0 on the census path**. All four dual-depth classes are re-measured **pairwise disjoint (0 overlap
  on 6 of 6 pairs)**, so the ladder's order is a statement rather than a tie-break.
- **Nothing a caller declined to consult appears to have spoken.** `CENSUS_CHANNELS` is unchanged and
  the census default is byte-identical — 187 cells read, 2,385 depth-unknown, every hazard count
  unmoved — because the channel-A views are gated on the token exactly as channel G's are.
  `LICENSED_CHANNELS` gains `so-array` (CONSULTED, never adopted without the ack), and declining it
  reproduces every W6b-2 number exactly. `W6B_REASON`'s 2,298 / 2,139 populations are **scoped rather
  than restated**, with the 6-cell withdrawal and the 8-cell rename spelled out at both live sites.
- **Class C at the same granularity as the depth.** 34 of the 65 sit on a column bound with 2–4 distinct
  CLUT words. The census's `multi_palette` flag is **reader**-derived and 65/65 of these cells are
  readerless, so its clean `0` there is **vacuous, not a clear** — it is printed beside the derived
  answer so nobody mistakes silence for a pass. Keys come from the column's **novel** slots when the
  depth did, and `export-art` writes an `.as-` alternate PNG for every key.
- **★ THE ORDER CLAUSE IS UNMEASURED AND THE KIT SHIPS THE ARITY ONLY.** *"Selected by the primitive's
  `part` byte"* states an arity **and** an order. The arity is corroborated twice from outside the
  record's header (part-byte range: 0 of 502 records has `max(part) >= P`, stride-8 over-runs 126/126;
  CLUT-arity 264/264 against a 16.2% random floor and a 53.3% ambient). The order is corroborated by
  nothing (identity 63.3% / reversed 56.0% / permutations 59.4%, ~0.9σ). So `parts` is a **SET**
  everywhere, display keys tie-break on **values** (`geom`, `tpage`, `clut_word`) and never on the array
  index, and the sharper reading that would follow from the order — 5 of the 65 are *direct reads* rather
  than inherited, plus a four-cell cast shortlist — is **withheld** and stays in the study. Proven, not
  asserted: a permutation-invariance gate re-runs the shipped path over all 372 containers with each
  record's entries shuffled and asserts every verdict-bearing output is bit-identical.
- **`GAIN_SO_PAGE`, `CHANNEL_G_DUAL_CELLS` and `REFUSED_AMBIGUOUS` are now RE-DERIVATION-PINNED**, with
  `GAIN_ARRAY` and the seven new channel-A counts alongside them. Their only guard was an assert built
  from the same constants — self-consistent, and therefore structurally incapable of catching its own
  drift. Repaired now, while they are still right. New gate board
  `studies/custom-summons/tier-w/w6b3i_gates.py` (I0–I11, incl. the permutation-invariance rung) drives
  every claim above through the code that ships.

### Added — trigger regions drawn on the art (the Place tab's Regions tool)
- Gateway and walk-in-event zones are now DRAWN, not typed: a per-canvas tool strip
  (Place / Regions — explicit click semantics, the strip every canvas mode was waiting
  for) arms a region mode where four clicks build one quad, corner and whole-quad drags
  reshape it, and the quad's own menu rotates its walk-out edge or deletes it. New
  `[[gateway]]` rows take their target field + entrance from the strip's own boxes;
  events land with a placeholder message for the Editor form to word.
- Both region LAWS render on the canvas instead of waiting for the lint: overlapping
  tread regions mark in warn with the starvation explained (the TREADQUAD one-fire law,
  judged by the same `region_overlap_pairs` the lint formats), and every zone is audited
  against the engine's real IsInQuad fan — a dead zone (drawn area that silently never
  fires, the hand-authored collinear-strip class) hatches in error, an over-trigger
  spill (a non-convex/self-crossing quad firing OUTSIDE its own outline) washes in warn.
  A gateway's corners-0→1 walk-out edge draws thick with an outward chevron — the edge
  the exit walks the player across.
- Zone corners project at the walkmesh's real floor height and may hang off the mesh
  (normal donor door layout): an off-mesh click lands through the new plane-at-height
  conversion (`imagefield.click_to_plane` — THE PLANE LAW's one-parameter
  generalization), raycast-exact everywhere the mesh is under the pixel.
- The PHOTO lane draws regions too: the Trace tab grew the same tool strip
  (Floor / Cut-outs / Regions — the Add-cut-out toggle became the Cut-outs segment) and
  stores drawn zones in canvas pixels alongside the floor, so a pitch change re-judges
  them and Generate emits them through the CLI's own new `--gateway
  "to[,entrance]@cx,cy;…"` / `--event-zone "message@cx,cy;…"` arguments —
  `image-field` un-projects the quads through the same camera as the floor and writes
  real `[[gateway]]`/`[[event]]` rows, so a photo project's doors and walk-in messages
  survive every in-place regenerate. The `.trace.json` sidecar and the field.toml
  reopen path round-trip them (a compiled project's world zones invert back to the
  session's canvas pixels).

### Changed — THE DEFAULT-VALUE LAW: GUI-minted defaults are real or loudly invalid
- A sweep of every value the Workspace mints for you, after two playtests traced their bugs
  to quietly-plausible defaults (the Field(0) door, the top-right "..." box). The law: a
  minted default must either render correctly in-game or be refused by a gate — never sit
  in between. Changes: a form-added gateway now defaults to `to = 0` (loudly refused by the
  Field(0) gates and retargetable from its quad) instead of `to = 100`, a REAL field id
  nobody chose that silently warped there; each added `[[flag]]` mints the NEXT free index
  instead of always 8712 (a fixed default aliased every added flag onto one save bit — and
  `validate` now reports index collisions directly instead of leaving them to a load crash);
  minted NPCs (form + Place tab) carry no `dialogue` so the build's silent-talk channel
  shows the canonical FF9 silent line instead of a hand-rolled "..." window; the form's
  default prop is a barrel, not a chest look-alike that isn't openable.
- Drawn event zones got the same treatment as gateway targets: the quad's own menu gains
  **Set message…** (on the photo lane there is no other editor for a drawn zone's words),
  and a zone still carrying the drawn-zone placeholder warns on the canvas and in the lint
  ("it ships as a literal '...' popup") unless it's a `received` item box.

### Fixed — the painted-row inverse spanned the projection pole (low-pitch cameras lost their floor)
- **`cam.solve_z_for_canvasY` bisected across a discontinuity.** `project` divides by `num =
  abs(res.z)`, so past the projection pole at `res.z = 0` the SAME canvas row is re-produced,
  MIRRORED, by points behind the camera. The solver bracketed `[-30000, +30000]` — a window that
  SPANS that pole — so its two-endpoint sign test came back same-sign and returned `None` for rows
  that had a perfectly good front-branch root. Measured at pitch 15 / distance 3000: rows 365, 420
  and 440 all returned `None` (true roots -1650/-1900/-1970, which re-project to exactly those
  rows). It is **not only a shallow-camera bug**: swept over world z genuinely IN FRONT of the seven
  real donor cameras in the regression suite, the old solver lost **112 of 886 samples — all 32 on
  TRNO0_inv**, whose `r[2][2] < 0` puts its entire front branch at negative z.
- **Replaced by the exact closed form.** `canvasY(z)` along a world line is a Möbius function of z,
  so the inverse needs no search: `z = (a*E - A*H)/(B*H - a*G)` on the front branch, with the
  coefficients read straight out of `project`. Exact for ANY camera — yaw, roll, a real imported
  `centerOffset` — not only pure-pitch synthesis: it round-trips `to_canvas` to ~1e-13 px and to
  **zero misses on all seven real cameras**. `zlo`/`zhi` keep their old meaning as a reachable
  window (the default ±30000 is the walkmesh's own Int16 coordinate budget).
- **`horizon_canvas_y` is now exact too.** It probed `z = +1e7`, which rides the same `abs(res.z)`
  mirror — on TRNO0_inv it reported row 321 for a true horizon of -13, a 334-row lie under the
  Workspace's "no floor above" line and `imagefield`'s row cap. And 1e7 is not infinity: the
  residual is O(1/z), still 6.5 rows out on the map158 donor. It is now the analytic asymptote.
- **`guide.frame_floor` stopped lying about why.** It raised at EVERY distance for pitch 15 and 20
  with "canvas Y=420 is above the horizon … horizon at canvas Y~100" — false by 320 rows, because
  the `None` came from the bracket, not from the horizon. It now quotes the reason
  `cam.canvas_row_z` gives (row past the horizon / root behind the camera / root outside the
  window) and names the side of the horizon that is actually reachable — which takes
  `sign(G·det)`, not `sign(G)`: the obvious guess is wrong on TRNO0_inv and on any `det < 0` camera.
- **`ff9mapkit new --pitch 15` no longer ships a mesh that doesn't match its camera.**
  `pack.new_project` wrapped the frame in `except (ValueError, ZeroDivisionError): pass` and fell
  back to a HARD-CODED quad, so the scaffold looked fine and shipped a walkmesh belonging to no
  camera — and because the solver was broken below ~30° pitch, that was the common case, not the
  extreme one. The quad is now ALWAYS derived from the scaffold's own camera, and an unframeable
  camera (a near-level pitch, where the back row really is past the horizon) REFUSES with the knob
  to turn instead of guessing a floor. Nothing is created on the way out.

### Changed — `floorplan` retires its private camera-math fork now that the shared solver is fixed
- `floorplan.cam_params` / `z_for_row` / `horizon_row` existed only because the shared
  `cam.solve_z_for_canvasY` / `cam.horizon_canvas_y` used to lose reachable low-pitch rows across
  the projection pole — a defect, not a preference, and the private form was still only ~0.05 canvas
  px accurate (~0.07 px for `project_floor`'s depth) where the fixed shared math is exact. With the
  pole fix landed, that reason is discharged: `fit_play_camera` now calls `cam.solve_z_for_canvasY`
  and `cam.horizon_canvas_y` directly, and `project_floor` is a thin composition of `cam.to_canvas` +
  `cam.project`'s signed depth rather than its own formula. This also drops the module's yaw-0-only
  restriction — the private math was off by 25–6138 canvas px on the real donor cameras, so it could
  never have been pointed at an imported/forked camera. `pitch_floor` stays as the composer's own
  policy gate (refuse a camera whose horizon falls inside the canvas); its actual gate check now
  reads `cam.horizon_canvas_y(cam) >= 0` directly, which additionally honours a nonzero
  `centerOffset` that the old `range_h/2`-assuming formula silently ignored. No behaviour change for
  any camera the composer builds today (pitch still refused under `p* ≈ 25.7°` at fov 42.2) — the win
  is exactness, real-camera reach, and one owner of this math, not new pitches.

### Fixed — a `received` event now shows the REAL item-get box (the top-right "..." bug)
- `[[event]] received = true` re-styled the author's message as the window-7 item box at the
  dialogue-default geometry — a tiny box pinned to the TOP-RIGHT corner, with no item name in
  it (the Place tab's drawn-zone placeholder made it a literal "..."). Both text channels
  (synthesize + verbatim) now emit the chest's own canonical box — `[STRT]` auto-centering,
  `DEFT` tail, `Received <item>!` with the live item name — through the one shared builder
  chests already used. A `received` event no longer needs a `message` at all; with one, your
  text fills the box verbatim (you own its codes, chest-style), and the bare "..." placeholder
  never ships as box text.

### Fixed — `cooldown` over a one-shot is now an EVENT (the hangout greet latch)
- A `cooldown` branch whose action is a one-shot (`announce`/`sfx`/`flash`/`stop_timer`)
  compiled with sticky-engagement semantics: selecting the announce halts the walker
  (the dispatch-halt), so two neighbours greeting each other on `near` conds parked
  inside each other's radius, the condition could never fail, and both held selection
  forever — statues after their first exchange (only player-keyed rows escaped, because
  the player is an external mover). The cooldown now compiles fire-and-release on the
  one-shot request lane, symmetric with the event `once`: the delivery ARMS the timer
  (a byte on the central clock, or a brain-private slot under `brains`) and clears the
  request, and the branch releases the tick the timer lands. Sticky semantics are
  unchanged for movement children ("chase me, re-aggro N after I escape"). The offline
  stepper had modeled the intended event semantics all along (its cooldown never even
  armed) — the exact divergence that hid the latch — and now arms the timer at fire and
  models the dispatch-halt, converging with the compiled bytes.

### Added — the Place tab (click-to-place content on a forked room's own art)
- A new Workspace document on the Author rail: open any fork of a real field (verbatim,
  native/editable, or BG-borrow — the donor resolves from `[verbatim_eb] donor` /
  `[field] source_field` / `borrow_field`), press **Load the room**, and the donor's
  composited background, real camera, and real walkmesh arrive together (built off the
  GUI thread, disk-cached per camera). Every click raycasts the walkmesh — you click
  what you SEE, slopes and stairs included — and drops an `[[npc]]`, `[[prop]]`,
  `[player] spawn`, or `[[player.arrival]]` row (upserted per entrance) straight into
  the OPEN field.toml: one undo step per drop, Save through the ordinary editor path.
  A stacked-floor pixel (a bridge over a floor) lists its floors and asks — never a
  silent guess. Placed content renders as markers at its real floor height; multi-camera
  fields composite and place per camera. Refusals are hard and honest: bundled examples
  and installed copies refuse the whole surface; a field with no donor says why; a
  verbatim fork refuses spawn/arrival (the donor's own entry sequence runs) while
  npc/prop placement seats below the donor's party band at build, as always.
- The field-card picker knows what you already fork: a card whose room is open in the
  current project offers **Place content on this field** instead of a second fork.

### Added — foreground cut-outs in the Trace tab (occluder contacts)
- Mark a photo's foreground occluder (a pillar, a doorframe) directly on the art: **Add
  cut-out** arms a contact click — click where the object MEETS the floor — and the tab
  derives the overlay depth from the camera (`occluder_z`, the in-game-proven anchor:
  occlusion flips exactly at that line), asks for the object's cut-out PNG,
  and lists every contact in a strip with its depth, re-judged live on every pitch
  change. A contact traced up the body (depth at/behind the base layer) or above the
  horizon refuses with the CLI's own message. Generate emits the classic
  `--foreground path@cx,cy` form, so the build is byte-identical to the CLI loop's.
- **Generate is in place after the first run**: the tab remembers its project, so later
  Generates rebuild the same folder with no dialog (open a new image to start another),
  and it writes a `<stem>.trace.json` session record beside the build — Open it later
  to restore the whole editable state: photo, floor, pitch, cut-outs at their dragged
  spots, name and id.
- **The open field offers itself**: showing the Trace tab with a field open in the Editor
  auto-loads its trace session when the tab is empty, or shows a one-click
  "Load NAME (the open field)" button when a session is already in progress — no
  navigating to a folder the app already has open. And edits made after a Generate flag
  the status ("not stamped — Regenerate…") until the project on disk is updated.
- **Open accepts the project's `field.toml` too** — and a project generated BEFORE the
  session record existed still reopens: the tab rebuilds the editable session from the
  compiled artifacts themselves (the walkmesh ring inverted back through the collision
  outset, the camera block's pitch, the generator's own anchored-contact comments), then
  writes the record on the next Generate. No traced project is ever a dead end.
- **Draggable things now say so**: trace vertices, contact anchors, snip overlays, and
  the Behavior stage's handles/grips show the move (or resize) cursor on hover — the
  pan hand no longer masks what grabs. (Under the hood this surfaced a real crasher:
  canvas child items created with a parent argument were Python-owned and double-freed
  under garbage collection; all child items are now scene-created and reparented.)
- Cut-outs **preview on the art** and snips are **positionable**: a PNG sharing the
  photo's frame registers pixel-for-pixel (inert, exactly where the artist painted it);
  any other size is a SNIP — shown at its natural photo scale with its base parked on
  the contact, draggable into place (its depth anchor rides along, re-deriving live; a
  transparent surround never blocks tracing). Each contact also has its own draggable
  handle to re-tune the flip line alone. Generate composites placed snips onto the full
  frame automatically — cut out just the object, drop it on the art, drag until it sits.

### Added — `[[prop]]` as a first-class editor kind
- Props now appear in the Editor tree (their own "Props" group), with a full form
  (archetype/model/pose/pos/face/collision/gates/attach), Inspector summary + rollup
  tally, and per-node lint mirroring the build's own reads (archetype-or-model, an
  unknown archetype/GEO name, a missing pos).

### Added — floor-aware spatial instruments (THE FLOOR LAW)
- A walker lives on ONE floor of a multi-floor walkmesh and changes floors only across a
  SEAM edge — everywhere else two floors meeting in flattened 2D (a terrace base, a
  balcony lip) is a wall the old point tests could not see, so a wander target / route
  point / post on a raised terrace passed every offline gate while the ground walker
  wedged (the HANGOUT bench, field 559's four floors). Now: `BgiWalkmesh.floors_at`
  reports every floor containing a point and `seam_edges_xz` the legal crossings; the
  route sweep flags any leg crossing floors away from a seam (a lint ERROR, "NO SEAM");
  the pursuit sweep counts such crossings as jams; and a new WANDER sweep models the
  engine's roll honestly — it lands anywhere in the box, mesh or not, so off-mesh and
  off-floor box area is reported with the jam fraction. The layout probe tints each
  floor, draws seams in green, marks unseamed crossings with a magenta X, and reports
  each item's floor(s) plus a per-floor summary. `route = "auto"`'s safety re-sweep
  refuses a detour that still crosses an unseamed floor break (its A* is floor-blind).

### Added — ferry DEPARTURE arms (`[[ferry.destination]] depart_code`)
- A destination row with `depart_code = N` becomes a departure arm: the arm writes the
  code into the pending-departure byte (`flags.FERRY_DEPART_BYTE` by default; `[ferry]
  depart_byte` overrides) and lands at the ferry's `stage_arrive` — the home-quay shore
  where a world-side departure director (the scene-ladder study's WORLD11 build) consumes
  the code, plays the sail-away scene, and completes the journey to the row's real
  `arrive` point. Lint requires `stage_arrive` with any `depart_code`, bounds codes to
  1–255, and rejects duplicates. The plain (code-less) arm is byte-identical to before.
- The depart arm now also caches the hall-entry world X — `Global.Int24[64]`, the world
  mirror's record of where the player stood when they entered the field — into
  `Global.Int24[flags.FERRY_ORIGIN_X_INT24]` (1873) before the stage preset overwrites
  it, so the world-side director can classify the ORIGIN port and stage the sail-out at
  the quay the player actually boarded from (scene-ladder rung 3c). The cache write sits
  in the arm's on-exit block, strictly before `arrive_writes`; a code-less arm carries
  nothing new.

### Added — the archetype stamp WIZARD (one teaching surface, not a picker chain)
- "Stamp an archetype…" now opens a single dialog: the proven trees listed with their
  teach text, the actor bindings (target npc, the guard's enemy, the shift pair's
  partner) appearing exactly when the picked archetype needs them, and a LIVE preview
  of the ladder the stamp will write — produced by running the real stamp on a scratch
  copy, so it can never drift from what lands. Minted route markers are disclosed in
  the preview; anything illegal (a guard with no seated enemy, a pair without a second
  free npc) disables Stamp and says why in place.

### Added — five new behavior archetypes (the ambient-life family)
- The stamp wizard's proven trees grow from five to ten: **Follower** (tails the
  player at a polite standoff — the pet/escort), **Town crier** (a cooldown-gated
  line for every passer-by), **Commuter** (an alternator walks it between two spots
  on the clock), **Duel pair** (two units wearing the guard's whole ladder at each
  other — a sparring match with no referee), and **Chatty pair** (neighbours who
  wander their corners and greet when they drift together). Every stamp still runs
  the real compiler in its fence; the Info Hub cards and wizard rows derive
  automatically.

### Added — branch archetypes (one proven row into an existing ladder)
- ＋ Branch now opens a small picker: a blank row (the old behaviour) or one of four
  proven guarded branches — **Flee when badly wounded**, **Announce once + raise the
  alarm**, **Swing when in reach**, **Chase on sight** — each with its teach text, a
  target picker where the row binds one (swing offers units only; the player can be
  chased and fled but never swung at), and a verbatim preview of the exact row that
  will land.

### Fixed — `lint` rejected every route marker
- The full-field lint required `pos` on every `[[marker]]`, predating path markers —
  so any field carrying a patrol beat (including everything the archetype stamps
  mint) flagged a false error. A marker is now a named point (`pos`) or a named
  route (`path`).

### Added — the ladder tells you when a branch can NEVER run
- A branch whose conditions are subsumed by an earlier row's (a `near 400` below a
  `near 900` on the same target, an `hp_le 0` below an `hp_le 2`, anything below a
  plain unconditional row) now wears a "never selects — row N wins first" chip, with
  the fix options on hover (reorder / tighten / gate). Deliberately conservative: it
  only claims what first-match priority proves, and a sticky `once`/`cooldown` row is
  exempt as a shadower — a latched one-shot releases the rows below it, which is
  exactly how the announce-then-fight idiom works.

### Changed — the ladder's row tools stop out-massing the rows
- The per-branch ↑ ↓ ✎ ✕ controls are now quiet borderless glyphs (a fill only under
  the cursor), so a ladder reads as branches first and furniture second — and more of
  each row fits before it scrolls. The unit bar's stats caption now keeps a readable
  stub when width is tight instead of vanishing, stage labels flip left rather than
  clip at the canvas's right edge, and a label pushed below its marker clears the dot
  row instead of striking through it.

### Changed — a new [[npc]] gets an FF9-flavoured name, never the literal "NPC"
- Adding an NPC (Workspace Editor tab or `ff9mapkit edit`) now mints a fresh compound
  default like `gysahl_peddler` or `mist_porter`, deduped against the field's own cast —
  three new NPCs used to arrive as three identical "NPC"s, and the name is load-bearing
  (behavior units, the field/scene merge, and the archetype wizard all bind by it).

### Changed — a Behavior-tab UX pass (the readable-by-default round)
- The cast rail now asks for its own longest row on each field switch (capped), so
  unit/class info bits ("class ×3 · 4 hp") stop eliding at the default window; a rail
  the user drags stays where they put it until the next field.
- Stage labels negotiate vertical tiers instead of overlapping, and a class's members
  parked in a rank (the [siege] pool bench) collapse to one counted label
  ("soldier ×3 · pooled" — hover names the members) while every member keeps its dot.
- The ▶ Simulate strip: the scrub slider can no longer be starved by long captions
  (the latest event has its own line; the honesty ledger shows its short tags with the
  full sentences on hover), the timer reads "timer 57s" instead of an emoji-font ⏱
  blob, and play/pause/reset wear real SVG icons.
- The [siege] read-only banner and the unit-bar stats elide instead of flooring the
  whole tab's minimum width (the siege face demanded 2300px before).

### Added — ▶ Simulate: the Behavior tab's offline tick-stepper
- Step or play a `[behavior]` tree offline at the engine's own 30 ticks/s: ▶ sweeps the
  ladder rows as branches select, units move as ghosts on the stage, the strip shows
  tick · seconds · the countdown timer and the latest one-shot event, and clicking the stage
  moves the sim's player (the move joins the timeline, so scrubbing back and forward
  replays identically). Built to catch the priority/starvation authoring family — sticky
  `once` vs the event-once release, hysteresis keeps, dead branches — before a playtest.
  An INSTRUMENT, not proof, and it says so on its face: walks are straight lines (no
  walkmesh — the Sweep lane owns wall truth), pooled units stay dormant, `battle` only
  logs. Semantics are grounded in the docs + engine (Chebyshev proximity, speed
  units-per-frame, defaults derived from the compiler itself); works read-only on
  `[siege]` fields' generated armies.

### Fixed — the Info Hub library's "?" help badge rendered as an empty circle at 150% text size
- The round violet help button pinned its box at 30px in Python while the app stylesheet's button
  padding — which grows with the text-size dial — kept applying inside it; at 150% the padding alone
  consumed the whole box and the "?" glyph rendered nothing. The badge's box now lives in the
  stylesheet with zero padding, on the same even-circle arithmetic as the concept badge, so the
  circle grows with the dial and the radius stays exactly half. It also gained real pressed and
  keyboard-focus states.

### Fixed — the Info Hub library opened with an h-scrollbar on its own category sidebar
- The catalog library's three panes were allocated at construction, against a splitter that had
  never been laid out, with a request summing to the dialog's width — margins the panes never
  get — while the detail pane's button bar puts a hard floor under the third pane. Qt settles an
  oversubscribed request by shaving every pane proportionally, so the category sidebar always
  opened a little narrower than its own longest row and grew a horizontal scrollbar. The panes
  are now allocated once at first show, when the splitter's width is real: the sidebar gets its
  measured ask (still capped so a runaway label can't eat the browser), the detail pane its 55%
  or its own floor, the middle list the true remainder.

### Added — the Info Hub's "Behavior stamps" section (the archetype cards)
- A new library section holds one card per Behavior-tab archetype (sentry / patroller /
  civilian / guard / shift pair) plus the `[siege]` whole-block skeleton — searchable by what
  each tree DOES (the teach text is the search body). Every card's snippet is the REAL stamp
  op's output on a scratch field (never a hand-copied tree, so the stamps changing changes the
  cards), validate-clean once its placeholder npcs are renamed; the detail pane teaches the
  in-app doorway (the Behavior tab's ＋ Archetype… / the empty-field guide). Picker-only like
  Encounters — the cards never bloat the All list.

### Fixed — the Workspace Behavior tab speaks class rows (`npcs =`)
- The `[siege]` brains default handed the tab's read-only siege view CLASS rows its projections
  had never seen: the dry-compile lane KeyError'd, the cast rendered `?` units with no ladder,
  and class members had no posts/rings/handles on the stage. A class row is now first-class
  under its CLASS name (validate already pins it unique and npc-clash-free): ONE ladder for the
  shared program, `class ×N` with members in the cast rail, every member's post and ring on the
  stage with one shared radius write path (any member's grip resizes the class's ring — the
  program IS shared), `speeds` presets in the ladder header, and class members counted as taken
  NPCs and offered as archetype targets. Applies equally to hand-authored `[behavior]` class
  rows, not just `[siege]` views.

### Fixed — quad UV covers fanned the WRONG WAY (GEOM quad corners are Z-ordered, not a perimeter)
- `summons.repaint._face_polys` and `summons.build._mesh_tris` triangulated a 4-corner face as
  `(0,1,2) + (0,2,3)`, documented as valid "because a quad's corners are perimeter-ordered". Measured
  corpus-wide, they are not: every quad bucket — creature FT4 included — carries the PSX GPU's own
  Z-order, and the fan is now `(0,1,2) + (1,3,2)` (scoring both fans for winding consistency over
  372 containers: Z 29,725 of 29,986 textured quads, perimeter 13, 0 of 612 quad-bearing geoms
  leaning perimeter). The perimeter fan on a Z-ordered quad is a BOWTIE — one half double-covered, a
  wedge uncovered, and the wrong triangle can even mark texels outside the quad — so quad-bearing
  coverage was mis-counted everywhere: 110 of the corpus's 340 `so`-bound scenery models move
  (+73,626 halfwords net; ef211's pool arc alone was short 700, 17.4%), ef227's creature census
  gains 31 texels (65,267 → 65,298), and its part-5 "interior holes" collapse 33 → 2 — the bowtie
  wedges had been reading as holes. What does NOT move: every W6b census pin (no cell gains or loses
  a reader — the fix changes cover density, never attribution), the u-spill column census, and the
  fire-field cell's 8,128. `summon-export` meshes now emit the Z fan too, so exported quads no
  longer carry a self-crossing triangle pair.

### Added — behavior CLASSES: `npcs = [...]` shares ONE brain across same-tree units
- With `[behavior] brains = true`, a `[[behavior.unit]]` row may bind a LIST of NPCs
  (`npcs = ["kn0", ...]` + optional `class = "name"`): its branches compile ONCE into a single
  shared brain entry every member spawns as its own coroutine — the engine binds each running
  copy to its spawner, and the brain reads that member's state through the caller's own uid
  (engine-native object-variable field 5, resolved through the same expression path the data-
  table indices use). Per-member state (posts, targets, speeds, mirrors, sticky latches, the
  engage register) strides into uid-indexed script-vector cells seeded like every kit table, so
  it also stops consuming the blackboard flag band. Measured on the 7v7 scoreboard brawl: 14
  brawlers share TWO 1.5KB brains — 15.3KB of new bytes vs 46.9KB on per-unit brains (32%).
- v1 class vocabulary: the feeds, `engage`, `swing_at`, `hold_ground`, `die`, sticky
  `once`/`cooldown`, `raise_flags`/`clear_flags`; the one-shot family (`battle`/`award`/shop
  verbs/`sfx`/`flash`/`stop_timer`/`announce*`) stays on single-npc rows, and a class name is
  never a condition target (name a member). `hp`/`speed`/`pooled`/`pool` apply to every member;
  `anim` needs a shared model; class self-`hp_le` needs one hp home (same group, or ungrouped).
  Class-free builds (both backends) compile byte-identically to before.
- The one-shot family (`battle` / `sfx` / `flash` / `stop_timer` / `announce` /
  `announce_npc`) now runs on class rows with **once-PER-MEMBER** latches (each member's
  latch is its own uid-indexed cell; class-wide once = `raise_flags` + `not_flag`). A class
  `battle` also installs the after-battle Main_Reinit, and the engine's battle park/restore
  is uid-keyed and object-kind-blind, so shared brains ride a battle round-trip like any
  stock NPC. Only the payout verbs (`award` / shop stock+synth) still refuse class rows —
  once per member there would mean N payouts.
- Brain-PRIVATE state (sticky `once`/`cooldown` latches + timers, patrol progress, wander
  state, the one-shot request lanes) migrated into each brain coroutine's own PRIVATE variable
  block (zeroed at spawn = reset for free; one copy per running brain = per member for free
  under a class). It costs no script-vector table and no `gEventGlobal` band bytes; the brain
  ticks its own cooldown timers. Body-shared state (the sel/run protocol, mirrors, targets,
  body-written latches) keeps its addressable homes. v1 (ticker) builds are byte-identical;
  the `~` Flags panel cannot see private latches — the compile report prints each brain's
  block map.
- A `die` dispatched from a brain is now **must-land**: it issues the engine's BLOCKING
  script request (REQSW), which waits until the unit's script level frees — a death that
  triggers while the unit is held by an open talk dialogue or a blocked walk still lands the
  moment it releases, where the old fire-and-forget form would have been dropped silently.
  Routine dispatches keep the non-blocking form on purpose (drop-while-busy is the run-gate),
  each brain blocks only itself, and dispatch bodies are pinned never to carry the blocking
  form (a body waiting on the very level it holds would deadlock). v1 ticker builds keep the
  retrying non-blocking dispatch — one shared ticker must never wait on one busy unit — and
  stay byte-identical.
- The **one-shot family runs INLINE in the brain** (battle / event-once announce / sfx /
  flash / stop_timer / award / shop): the work is global by audit (a battle id, a window, a
  sound, a fade, an inventory edit — never a bare actor op), so it executes directly in the
  brain coroutine instead of being dispatched onto per-member function copies — a class pays
  for ONE copy of each one-shot, and the last per-member body duplication is gone (~13.6KB at
  fort-condor scale). The engine's busy-check is preserved by READING the unit's script level
  before firing: a one-shot that triggers while you hold the unit's talk dialogue open defers
  and fires the moment the dialogue closes — never lost, never mid-dialogue. Looping
  (non-once) variants keep per-member bodies (they hold the unit's dispatch level while
  selected); v1 ticker builds are byte-identical.
- **`[siege]` now compiles onto per-class Seq brains BY DEFAULT** — each ally type and each
  raider group becomes ONE shared brain (`npcs =` class rows), raiders walk their SHARED lane
  at private per-member progress from their stage spawns, and the base's ending theater runs
  inline. Same ratified game (played back-to-back on the acceptance field, and the default
  build is byte-identical to the ratified opt-in build), far smaller bytecode: the central
  ticker collapses ~32KB → ~7KB on the reference siege, with class-count headroom for bigger
  armies. `brains = false` is the escape hatch back to the original central-ticker emission
  (kept golden-pinned) — reach for it if a dense field's entry layout collides with the
  brains' +64 uid band. Class rows also gain `speeds = [...]` — per-member walk speeds
  (mutually exclusive with `speed`), so classed marchers keep their anti-lockstep jitter.
- **The class-approach guard**: a classed `march`/`patrol` with `route = "auto"` now verifies
  at build time that every member has a STRAIGHT walkable leg from its spawn to the route's
  first point — a classed route is one shared program, so that approach cannot be auto-routed
  per member, and a spawn tucked behind a wall used to compile fine and jam in-game. Refused
  loudly, naming the member and the fix.
- Fixed: **`byte_band = "wide"` brings its own 240-flag window** (seated flush under the wide
  byte band, same standalone-only contract). The safe partition had left the blackboard flag
  window at 96, which a condor-scale siege's event-once latch + request lanes exceed under the
  v1 ticker — the shipped siege acceptance field could no longer compile. The wide byte band
  keeps its full measured 770 bytes.

### Added — where a scenery cell's DEPTH comes from: two attribution channels (W6b-2)
- W6b-1 shipped the scenery texel lane **attribution-limited**: 2,385 of 2,572 cells had no `so`
  reader, so the container stated no bit depth and the lane refused them by name. W6b-2 asks whether
  the container states it *somewhere else*. **246 of the 2,385 now carry a depth; 2,139 still do not**,
  and the refusal now says which kind of "no" it means. Every page carries a new `depth_source`.
- **CHANNEL G LICENSES — 57 cells, no key.** New `reskin.page_depth_view` reads the container's own
  `so` records at **PAGE** rather than **UV** granularity: a texture page is 256 lines and an
  addressable cell is 128, so one page word names a **column of two stacked cells**. That is not new
  evidence — it is the same record the lane already ships on, read at the granularity the hardware
  uses, and it is exactly W6b-1's lower-half blind spot fixed as a class. 55 of the 57 are addressable
  only through the per-cell map. They flow through every other gate unchanged: **56 build, 1 refuses on
  a program-VRAM write**. Kept as a SECOND VIEW beside `attribution`'s reader view and never merged —
  the two agree 138/140 overall and **16/18 on the informative rows**, and both rows that could have
  falsified the page predicate did.
- **CHANNEL P DISCLOSES — 189 cells, behind `acknowledge_program_derived_depth` + a matching
  `expect_bpp` — and the ack's live surface is 55 of them, which the refusal says out loud.** Channel P
  states a *depth* and names no CLUT, so an INDEXED (4/8bpp) channel-P cell has no key to render
  against and refuses as `program-depth-no-palette` whatever is acknowledged: **134 of the 189 are
  indexed and not one of them renders** (102 reach that refusal, 32 refuse earlier on a program-VRAM
  verdict). The remaining 55 are 15bpp direct colour, 43 of which clear every other gate. The class has
  its own wording rather than reusing `no-declared-clut`, whose text quotes "the reader's `so` record"
  on a channel whose premise is that no such reader exists.
  New `summons/depth_attribution.py` caches the depth the effect's own id-3 program
  *registers* each page at, recovered by const-folding two independently written disassemblers to
  **238/238 sites and 233/233 values**. It is DISCLOSED and not licensed because **the channel's own
  upgrade trigger fired once and failed in-game**: ef251's program-registered 15bpp page drew a 4-cycle
  "bumper strip" — a 4bpp read. `REGISTRATION-IS-NOT-A-DRAW` and its general form, `THE DEPTH
  COROLLARY` (a stated depth is a *binding-side* fact; the draw can read the same bytes at another
  depth), are carried as constants in the refusal text rather than as docstrings. The ack alone
  **FAILS BY NAME**: it is the author's judgement, `expect_bpp` is what the kit checks it against, and
  a judgement with nothing to check is not a guard. A truthy string still refuses (the literal-boolean
  law).
- **Four new refusals, four different populations, and one of them protects nothing on purpose.**
  `program-depth-no-palette` (above); `program-dual-depth` (22 cells in 10 containers the program names
  at two depths — a class the `so` census could not see); `channel-g-dual-depth` (8 cells whose column
  is bound at two depths — named in no recon dossier, so it is derived live from the container rather
  than cached); and `spill-vs-own-page` (2 cells where every reader binds the *neighbouring* page at one
  depth while this cell's own page is named at another). **Unanimity is the verdict rule; two values is
  a hazard, not a vote, and no acknowledgement lifts one.** The spill class is stated plainly as adding
  **zero** cells to the protected set — both already refuse through the name-every-column gate — and
  existing to carry the reason; a gate asserting otherwise would fail, and the gate that asserts it
  measures the counterfactual (`_EXPORT_BLOCKING` re-run with the class added) rather than an identity.
- **Class-C evidence is now taken at the same granularity as the depth.** `multi_palette` reads the
  CLUT keys the cell's *readers* name — and a channel-G cell has none, so the predicate was false by
  construction across the whole newly licensed surface. 7 of the 57 sit on a column bound with two or
  three different CLUTs (one with three): they now carry the class-C disclosure and `export-art` writes
  their read-only `.as-<clut>.png` alternate renderings, as it always did for a multi-reader cell. So
  channel G's 57 split **49 hazard-clean + 7 class-C + 1 refused on a program write**, not 56 + 1.
- **The depth-unknown refusal stopped saying the container is silent, because for most of the residue
  that was false.** It now names the program-derived depth and its call-site count where there is one,
  says WHICH **CHANNEL H** narrowing applies where the container's own `nClut4`/`nClut8` arity speaks
  (`hint = 4` means "4bpp **or** 15bpp" — a narrowing, not a depth, and it breaks 0 of the 30
  dual-depth ties), and ends with the **residue split**: `246 + 1,278 + 861 = 2,385`, asserted rather
  than quoted. The 1,278 sit in the 222 containers that declare no model at all, whose programs
  register nothing and structurally never could — **the ceiling is structural, not statistical.** The
  refusal offers the acknowledgement path only where there is one: on an indexed channel-P cell it says
  the ack cannot reach it, rather than naming necessary conditions a reader would take for sufficient.
- **`repaint.W6B_REASON` names BOTH depth-unknown populations** — the 2,298 cells that refuse under
  that name on the edit surface *and* the record's 2,139-cell attribution residue — with the arithmetic
  between them spelled out, because the 30 dual-depth cells are a subset of the residue and a flat list
  double-counts them. The gate re-measures the printed number against the derivation instead of
  matching it as a substring.
- **Two channel sets, so no published count moved under a caller that did not ask for the new one.**
  `scenery_surface()` defaults to `CENSUS_CHANNELS` (W6b-1's, byte-for-byte); `scenery_texel_pages()`,
  `texel_page()`, `export-art` and `build` default to `LICENSED_CHANNELS`. The precedent is
  `attribution(include_direct=)`: a parameter, never a second derivation. A channel a caller declines
  to consult is not merely un-adopted — its refusals are not stated either, **down to the reason
  strings**: on the census default a depth-unknown refusal is W6b-1's own text byte for byte, not
  merely its own count.
- **The cached table is RE-DERIVATION-PINNED**, like the program-VRAM id lists before it: new
  `studies/custom-summons/tier-w/w6b2i_gates.py` (I0–I10) re-rolls it from the recon artifacts and
  asserts equality cell for cell, re-derives every count per run, and drives the whole acknowledgement
  ladder through the real build path. Its count pins are also asserted **at import**, so a truncated
  table fails loudly instead of quietly attributing fewer cells.

### Added — paint a summon's texture pages in COLOUR: `--art-lane paint` + `source_paint`
- `summon-reskin export-art --art-lane paint` writes an editable **RGBA render** (`<name>.paint.png`)
  and a marked palette (`<name>.swatch.png`) beside the exact indexed PNG, per creature part and per
  lawful 4/8bpp scenery cell. A `[[reskin.texel]]` row picks the lane with `source_paint = "…"`
  instead of `source = "…"` (naming both refuses). The lane writes **indices only and zero CLUT
  bytes**, so every shipped gate — the region partition, the orthogonality intersection, the span
  gate, the cutout law, the region invariant, the page-cell derivation identity — runs unchanged.
- **THE INCUMBENT LOCK makes the no-op exact.** The container's own index at each texel is the first
  term of the selection order, so an unedited export re-imported through this lane changes **0 bytes
  on 240 of 240 lawful surfaces**, including 100%-ambiguous pages and a 239-way tie. Without it the
  naive nearest rule moves 767,531 texels across 191 of those surfaces — and exactly the 1,844 of
  16,384 on ef251 part 0 that the `rgba` refusal has always quoted. That number is the entire reason
  `rgba` refuses and this does not; `INDEXED_RGBA_REASON` is byte-for-byte untouched.
- **Alpha is the cutout and it is authoritative**, both directions: without that rule a plain 40° hue
  slider punches 502 holes on ef227 part 0 that nobody drew; with it, 0. Partial alpha refuses,
  naming the texel. Determinism is structural — a total order over unique indices, integer arithmetic
  only, no set/dict iteration in any decision path, no floating point at all.
- **The approximation is disclosed per texel**, never refused: `plan` prints a QUANTIZE CENSUS
  (exact / approximated / mean, p95 and worst d², ambiguous, ties, STP changes, opaque black, cutout
  crossings) and `--previews` gains a fourth `error` panel. **No error threshold ships**: a fixed CLUT
  is a small subset of a 32,768-colour cube, so any hue move leaves it — and a hue move is this lane's
  own primary use case. A build whose every texel is maximally wrong still passes every gate, while
  the no-op through the same lane stays byte-exact.
- **New refusal: THE ALTERNATE-SPLIT TIE, with no acknowledge key.** On a class-C cell (one index
  array read through several palettes), an edit whose surviving candidates render as different
  colours in another declared key refuses rather than choosing — 298 of 365 duplicate groups on 11 of
  16 such cells split that way. Edit-scoped, candidate-set-scoped, and structurally unreachable on all
  93 creature pages. Fixes named in the message: paint a colour the swatch marks UNIQUE, or use the
  exact lane. Also new: `acknowledge_quantize`, `acknowledge_recoloured_palette`, `page_sha256` and
  `render_key` manifest guards, an absent-paint-source branch in `verify`, and `--dither`, which
  refuses by name (error diffusion is stateful, so an unedited page would dither and move bytes).
- **Painting onto a row you also recolour has a workflow that works, not only an acknowledgement.**
  When the CLUT half of the same build moves the row a paint row maps onto, the build refuses — and
  its first named fix (build the CLUT half, re-export `--art-lane paint --from` the staged container,
  switch the row on) now *clears* the gate: the export manifest records the whole-container sha256 of
  what it read, so the build can measure that the art really was rendered against the row it is being
  mapped onto. `acknowledge_recoloured_palette = true` is the deliberate second answer, never the only
  one. A refusal that names a fix which does not work is worse than one that names none.
- **`--mint-clut` stays deferred**, now with a shipped `MINT_CLUT_REASON` quoted verbatim at a real
  call site and in the docs. The bare spellings `quantize` and `mint_clut` remain **unknown keys**.

### Fixed — `[[reskin.target]]` and `[reskin]` silently ignored a mistyped key
- The fail-closed unknown-key gate existed on `[[reskin.texel]]` only. Both other tables read every
  key through `.get`, so `acknowledge_shard = true` armed nothing while reading like consent, and a
  misspelt `expect_offset` dropped a derivation guard with no error anywhere — **a guard may only
  ever fail CLOSED**. Both now refuse, naming the key and listing the known ones, through one shared
  key set both loaders consume. The deprecated-but-parsed `acknowledge_texanim` stays a known key.

### Changed — the gEventGlobal safe band is now PARTITIONED (campaign lane vs kit-standing lane)
- Campaign/journey per-member flag windows and the kit's own allocators used to share the safe
  band ungoverned — a `flag_base = 8712` campaign's windows silently overlapped the AUTO
  once-flag bands, the behavior Blackboard, and `[siege]`'s request flags. `flags.py` now owns
  the partition: windows grow up from `FIRST_SAFE_FLAG` and must end below
  `KIT_STANDING_FLOOR` (14664, enforced by the campaign lint at the window validator); every
  kit-standing allocator moved above it (AUTO bands 14664-14863 at width 40, Blackboard flags
  14864-14959, siege requests 14960-14975, named world flags 14976-15007, Blackboard bytes
  1876-1989). Bytes 1990-2005 stay unreserved as the `[[qte]]`/`[[numeric_input]]` `result`
  landing. Deployed content keeps its baked indices until rebuilt; saves are untouched.
- `[behavior]` gains `byte_band = "safe" | "wide"`: the default byte band is campaign-compatible
  (114 bytes, ~11 grouped units); `"wide"` reclaims the historical 770-byte band (bytes
  1220-1989) for standalone-world scale — it overlaps campaign flag windows, so never deploy
  wide-band behavior content onto a save that also plays a campaign. `[siege]` generates
  `"wide"` (a condor-scale siege cannot fit otherwise).

### Added — `behavior lint` catches THE DRAINING-CONDITION LAW (and it caught `[siege]`)
- The selector fires **one branch per unit per tick**, so N `once` branches sharing a gate
  need it to hold for N consecutive ticks. Lint now warns when a stack of them rides a gate
  that can stop holding, names the offending condition, and states the fix (latch the moment
  on the first branch, gate the rest on that flag). Sticky and therefore exempt:
  `flag`/`not_flag`/`any_flag` (unless something `clear_flags`es them), `time_below`,
  `hp_le`, and `counter_ge` on a counter **no `[[behavior.scan]]` feeds** — a scan headcount
  rises and falls, a schedule or kill tally only rises.
- **It immediately found a real fragility in the shipped generator:** `[siege]`'s alarm cue
  and alarm text both rode `any_near`, which drains the moment the raider that tripped it
  dies or steps away — the lines below the cue could silently never fire. The alarm chain is
  now generated latched (cue raises `alarmed`, the rest gate on it), pinned by tests.

### Fixed — a standalone-installed FORK silently lost every fork-donor behavior
- `build_mod` now emits **`ForkDonorPatch.txt`**, the `<forkId> <donorRealId>` map the engine's
  s24–s33 fork gates resolve through. `build --out` already shipped a complete standalone mod —
  DictionaryPatch, BattlePatch, TextPatch, ModDescription, every asset — but this one file was
  written only at deploy time by the repo's `tools/deploy_field.py`. A forked real field
  **installed** rather than deployed from the repo therefore booted with off-mesh exemptions,
  name-keyed overlay occlusion and scroll player-binds all silently off: it built, it booted, and
  it looked subtly wrong with no error anywhere. Novel fields were never affected (no donor → no
  file, and none is emitted now either).
- Installing into a folder that already holds another fork no longer drops that fork's mapping
  (`--preserve-existing` gained the same foreign-line merge `DictionaryPatch` already had).
- An **editable** campaign member now records `[field] source_field`, so it too carries its donor
  through a standalone `build --out` — and it completes the pairing its `text_block` already
  assumed (`donor_block_for` / `lint_text_block` read that key to grant the donor's own block).

### Added — `ff9mapkit deploy`: reversible single-field install (no repo needed)
- New `deploy` verb (alias `deploy-field`) installs ONE `field.toml` into a **dedicated** mod
  folder (`FF9CustomMap-<name>` by default). SAFE BY DEFAULT: lints and prints the plan, touching
  nothing until `--apply`. Snapshots any existing folder, then writes a revert script that either
  restores the snapshot or removes the folder the deploy created.
- Runs the same guards as `deploy-campaign` against the built dist — EVT/FBG name collisions and
  GLOBAL-EventDB id collisions abort (`--allow-name-collision` / `--allow-id-collision` override),
  text-block shadowing warns.
- Pointed at a SHARED folder holding other fields it **aborts** rather than unregistering them
  (`--allow-drop` overrides): a single-field install owns its folder and replaces it wholesale.
  Iterating many fields into one shared folder stays the repo dev loop's job.
- This is the installed-copy twin of `tools/deploy_field.py`. That script stays repo-only and
  unchanged — its sandbox id-forcing, `.ff9deploy.toml` resolution and prior-id auto-revert are
  dev-loop concerns with no meaning on a single-game install.
### Added — Behavior ARCHETYPES: stamp a whole proven tree (rung D, first slice)
- The Behavior tab's cast rail (and its no-behavior guide) gained **＋ Archetype…**: pick a
  proven tree, pick a named `[[npc]]`, and the unit is seated in one undo step — **sentry**
  (announces once and raises `alarm` when the player closes, chases from mid range, walks a
  minted beat), **patroller** (die guard + beat), **civilian** (bolts from the player to
  refuge points, strolls a wander box at home). Sentry/patroller mint a closed 4-point beat
  marker around the post (220u legs — clear of the ~192u actor-jam spacing; names dedupe)
  with `route = "auto"`, so jammed legs heal at build; shape everything afterwards with
  Stage edit's drag handles. Every archetype binds against `player`, needs no second unit,
  and is CI-fenced by a real dry-compile of the stamped document.
### Added — `examples/siege/`: the shipped `[siege]` example (+ two lint false positives fixed)
- A whole tower-defense minigame as a bundled example: a **novel** field on **stock Memoria**
  (no donor, no engine patches) that lints, builds offline with the generated placeholder art,
  and shows the `[siege]` surface end to end — waves, priced hire pools, the war council, the
  payout, and the theater dials. `examples/README.md` and `docs/FORMAT.md` point at it.
- Writing it exposed **two lint false positives that fired on every `[siege]` field**, both now
  fixed: a generated hire row's `requires_flag` reads a pool's `hireable` gate, which the
  compiled TICKER publishes rather than an `[[event]]` (new `behaviortoml.published_flags`,
  sharing the deterministic two-pass `siege.resolve_hireable` uses); and **pooled units are
  parked off-play by design** (the ARMOURY idiom), so the placement check no longer calls
  their 9000-band seats a misplacement. The example linted 10 warnings before, 1 advisory now.

### Added — `[siege]` per-siege announce theater: THE WAVE HERALD
- A siege's waves used to arrive in **silence** — the one moment a player most needs told.
  `text_waves = [...]` (one cry per wave, `""` skips a wave) and `wave_sfx` now herald each
  arrival off the wave counter, cue first then line. Because that counter is **monotonic**,
  the cries ride the event-Once lane straight (the draining-condition law's exemption), and
  the `counter_ge` gate means a busy tick can never swallow one.
- `alarm_sfx` cues the breach alarm the same way, and `text_alarm` now accepts a **list**,
  staging like the ending texts. A siege declaring none of these emits the proven shapes
  byte-for-byte — one plain alarm, no wave branches (regression-pinned). Cast-proven:
  "wave heralds land, sounds read fine."

### Added — `behavior lint` catches THE CLOCK-COUPLED BATTLE LAW
- A field with a `timer` that fires a `battle` now has that scene's own AI read from the
  install and scanned for `B_SYSVAR[17]` (= `TimerUI.Time`); a hit warns that the scene
  **ends itself when the clock reads 0** — the Festival of the Hunt rule, which lives
  inside the battle script, and which killed the REDOUBT's loss battle for a full playtest
  round. New `battle.battleai.reads_timer` / `scene_reads_timer` (a conservative scan of
  function bodies for the `0x7A 0x11` operand, so stray container bytes can't trip it).
- Deliberately a WARNING: the same design is correct once the clock is stopped, so it goes
  quiet when the behavior uses `stop_timer` anywhere (`[siege]` is quiet by construction),
  when the field has no timer, and when the scene can't be read — an unreadable scene is
  reported as unknown, never assumed safe.

### Added — fight theater: strike clips, hit cues, and the death beat (theater rung E)
- `swing_at` / `engage` take `anim` (a one-shot clip on the striker) + `hit_sfx` (the impact
  cue), fired on the DAMAGE tick — inside the interval gate, never per frame. The clip is
  fire-and-forget (no `WaitAnimation`), so a strike stays interruptible and a looping clip
  can't wedge the swing loop.
- `die` takes `anim` + `linger`: the long-standing "instant vanish" becomes a collapse —
  active drops first (the corpse is inert immediately), the clip plays once and holds its
  final pose, then the body vanishes after `linger` frames. Cast-proven over five rounds,
  each a distinct mechanism, now written up as **THE FIELD-ANIMATION LAWS** in BEHAVIOR.md:
  a blocking body must hold its dispatch level; a different form is a different skeleton;
  never `WaitAnimation` in a level-4 async body; a one-shot is a LAYER (it ends → reverts to
  the stand clip, and a blocked walk's clip overrides it → install as stand+walk); and it
  must then FREEZE AT END (`SetAnimationFlags(1, 0)`) or a stand clip loops it forever.
- **THE OWN-CLIP LAW, now enforced at the call site:** `anim` takes a gesture NAME resolved
  against that unit's own model, and a foreign name is a lint error listing what the model
  owns. Field rigs are not battle rigs — `GEO_MON_F0_MUU` owns only locomotion + `jump` and
  `GEO_MON_F0_FFG` adds `howl_*`; there is no attack/death clip to borrow. Raw ids bypass
  the lookup.
- **⚠ THE CROSS-FORM CLIP TRAP (in-game):** resolution is **same-form only** (new
  `catalog.own_form_gestures`), not the `(group, token)` join — **a different FORM is a
  different SKELETON**. The CSO token's `attack_cid_*` exist only in the F3 form, and one on
  a `GEO_NPC_F1_CSO` rig renders the model twisted upside-down; cross-form names are now
  refused with the offending clip named. Within a token family the forms own wildly
  different sets (F3 = attacks + `hiza_*`, F0 = `hiza_*` only, F1 = neither, F4 = almost
  nothing), so some units honestly have no clip.
- **Fixed — a dying unit kept acting:** the `die` body never held the dispatch level, which
  was harmless while it was instantaneous but let the ticker keep dispatching the unit's
  other bodies (its swings) once the death beat made it block. It now holds the level and
  never releases it.
- `[siege]`: per-class `anim` / `death_anim` / `linger` + a siege-wide `hit_sfx`. A siege
  with no theater dials emits the proven shapes byte-for-byte (regression-pinned).

### Fixed — the loss battle dying on entry: THE CLOCK-COUPLED BATTLE LAW
- `B_SYSVAR[17]` **is** `TimerUI.Time`, and real battle AI reads it: the Festival of the
  Hunt scenes (id 35 + the `LB_E080x` family — what a Lindblum-plaza fork borrows as its
  donor-native fight) run `B_SYSVAR[17] B_NOT → RunBattleCode` end, terminating themselves
  the instant the countdown reads 0. A siege's ending theater takes seconds, so a late
  loss let the clock hit 0:00 before the `battle` fired and the fight ended the moment
  combat started — nothing wrong in the generated script. New `stop_timer` behavior verb
  (`RunTimer(0)`, needs a field `timer`), and `[siege]` now freezes the clock at the TOP
  of its loss lane (above the sting and the staged text) and on the rout. Diagnosed with
  `ff9mapkit battle-ai` — verify any scene a timed field fires. Cast-proven: "the fight
  works now, clock froze."

### Fixed — the `[[qte]]`/`[[numeric_input]]` result caps clear the nameplate words
- The extended-nameplate band claimed gEventGlobal bytes 2006-2017 as live overworld
  visited state (the explored words), but the modal `result` caps still read 4..2016 —
  the reserved-region walk already refused 2005-2016, so the caps promised offsets the
  validator then rejected, and the QTE suite's own pinned example (`result = 2006`) sat
  on the first explored word. Both caps now derive from one owner,
  `flags.RESULT_WORD_CAP` (2004, flush below `NAMEPLATE_EXPLORED_FLOOR`), so a future
  floor move carries them along; docs and error messages updated, and `lint_flag_bands`
  regression-pins that a result word in the nameplate words is named as such.

### Fixed — the behavior Blackboard byte band clears the reserved heap top
- The compiler's blackboard allocator handed out gEventGlobal bytes 1220..2040 linearly
  with no reserved-region guard — but the top of that range is live state: the nameplate
  explored words (2006-2017, save-persistent overworld visited bits), the `[[qte]]`
  scratch, the netsync co-op cells (engine-written every frame under co-op), and the
  choice mask (2040). A field needing ~786+ blackboard bytes silently allocated into all
  of it. The ceiling is now `behavior.BYTE_END_DEFAULT` (2005, derived from
  `flags.NAMEPLATE_EXPLORED_FLOOR` so a floor move carries it), the sibling of the
  `RESULT_WORD_CAP` fix above; overflow stays a loud build-time `BehaviorError`. The
  measured swarm wall moved with it (~5 swing pairs per unit at 40 units, was ~6 — the
  6th only ever fit inside the reserved bytes), and a regression test exhausts the band
  proving every handed-out word clears `flags.is_reserved`.

### Added — the Behavior tab AUTHORS ON THE STAGE (rung C)
- **Stage edit** (the ✥ toggle): every writable point on the stage grows a drag handle —
  unit posts, the player spawn, patrol/march/flee route points (a point that is a NAME
  reference moves the NAMED marker/NPC, never a silent literal copy), wander/scan centres,
  `near_point` centres — and the selected unit's engagement rings grow a resize grip (the
  radius dial, floored at 16u). One drop = one labeled undo step; right-click a route point
  to insert (lands on the leg's midpoint, ready to drag) or delete (2-point floor). Guides
  while you drag: the world compass in the layout probe's own words (+z back ▲ · −z front/
  camera ▼ · +x east ▶), the ~192u actor-jam spacing ring around a dragged post, and a live
  coordinate readout.
- **Sweep routes** (the Instruments' WALKABILITY section): the `behavior lint` walkability
  lane painted in place — every route leg swept against the field's walkmesh (an OFF-MESH
  sub-segment draws in error with a ✕ at the exact named spot; a wall-hugging leg in warn
  dashes) plus the chase/wander pursuit families (worst position-pairs drawn with the
  blocked rate). The findings text is the CLI's word for word. Two truths, stated on the
  button: the walkmesh comes from the SAVED file, the geometry from the open document; the
  first press is the only disk read, after which every committed edit re-judges on the warm
  mesh, debounced, on a worker.

### Added — staged win/lose text (`announce` delay/sustain + `[siege]` list texts, theater rung D)
- `announce` (and `announce_npc`) grew `delay = <frames>` — hold the dispatch level
  SILENTLY before the window opens (the staged-text primitive: a chain of once-announces
  on one monotonic flag pages like a cutscene, each delay the previous line's read time) —
  and `sustain = <frames>` (hold after the open, so a line is read before a queued
  `battle` takes the screen). Same level-holding law as `sfx`/`flash`.
- `[siege] text_win` / `text_rout` / `text_loss` now also take a LIST of lines, paged at
  `text_pace` frames (default 120). Win/rout aftermath lines page AFTER the proven
  cry → purse → jingle beat; loss lines page PRE-detect (the sting idiom scaled to text),
  the last line sustained before a `loss_battle`. Flashless staging grows `routed` on the
  rout detect so win stages can tell the endings apart. Plain strings keep the proven
  single-window shapes byte-for-byte (regression-pinned).

### Added — the `sfx` + `flash` behavior verbs + `[siege]` win theater (theater rungs A+B)
- `do = { sfx = <id> }` (+ optional `bank`) plays one sound-effect cue from a behavior
  branch — `RunSoundCode3` (0xC8) with the exact bank + pan/volume triple the kit's
  treasure chest plays in-game (bank 53248; ids via `ff9mapkit sfx-list`). Once-wrapped it
  rides the event-Once lane (fire-and-release — the purse-fanfare shape, gated on the same
  monotonic flag as an `award`); bare, it plays at dispatch and idles while selected (a
  bare `announce`'s no-spam shape). Lint checks id/bank ranges; unknown option keys refuse.
- `do = { flash = [r, g, b] }` (+ optional `pause` frames) washes the screen to a colour,
  holds a beat, and releases — stock's ADD-channel `FadeFilter` (0xEC) flash idiom, field
  682's exact `(0,24,white) → Wait(25) → (1,16,black)` pair. THE FADE-CHANNEL LESSON
  (REDOUBT round 2): `mode & 2` = the SUB filter, and SUB toward white is the stock warp
  fade to BLACK — a flash must ride the ADD channel or it reads as a field transition.
  Same once/bare stances as `sfx`; queued one-shots fire when the body releases.
- `[siege]` grew the win-theater dials `win_sfx = <id>` and `win_flash = true | [r,g,b]`,
  choreographed on THE REVEAL BEAT (round-3 playtest: the win cry opening as the white-out
  starts fights it): with `win_flash`, the DETECT branch carries the wash and the cries
  move below it — the wash body holds the base's dispatch level, and the request lane
  fires on run==0 in ladder order, so cry → purse → jingle land on consecutive ticks
  right at the release. Without `win_flash`, the proven announce-on-detect shape is
  byte-unchanged. Win-lane only by design: a loss cue on the base would race its
  die-on-`lost` `TerminateEntry`, so a loss keeps its own drama (the cry / the battle).
  Docs: BEHAVIOR.md, FORMAT.md; bench: REDOUBT (30421). All three rounds
  cast-proven: rung A ("victory sound fired once, nothing on defeat"), the wash
  ("white wash works now, pause feels right"), the reveal beat ("the beat landed").
- `[siege] loss_sfx = <id>` — the loss sting, via THE PRE-DETECT STING: an event-Once
  branch holds selection until it delivers, so seated between die-on-`lost` and the loss
  detect it is guaranteed to ring before the cry / the `loss_battle` transition / the
  base's collapse — no watcher unit needed, the reveal-beat serialization pointed the
  other way. (`hp <= 0` is monotonic — swings gate on target hp > 0 — so the stacked
  once-branches ride the draining-condition law's exemption.) Round 2 added the `sfx`
  verb's `sustain = <frames>` option and gave the sting ~1s of it: the event-once lane
  guarantees ORDER, not DURATION — without sustain the sting got one ~33ms frame of air
  before the boss battle took the audio (the round-1 playtest). Cast-proven: "the sound
  played then battle fires. it was a good defeat noise" (1942's timbre confirmed).
### Added — the texel repaint reaches a summon's SCENERY, at all three colour depths
- **TIER W rung W6b-1** (`studies/custom-summons/tier-w/W6b-SCENERY.md`): `summon-reskin`'s texel
  lever could only repaint a summon's *creature* pages. It now reaches the effect's own **scenery** —
  the sky domes, fire fields, ground planes and energy rings a cinematic ships with itself.
  `export-art --ef N` emits those cells too, and `[[reskin.texel]]` names them
  **`cell.s0.x704_y256`** (writer, then the VRAM cell), beside the creature lane's `tex.part0`.
- **Three colour depths, dispatched on what the container itself declares** — never on the shape of
  the PNG you hand back, so a wrong depth is a refusal instead of a differently-shaped picture that
  happens to pack to the right byte count:
  - **8bpp and 4bpp** are indexed PNGs, exactly as the creature lane already was. A 4bpp cell's PNG
    carries **one byte per texel with values 0..15** — never Pillow's 4-bit mode — so no PNG bit-order
    convention can reach the container, and an index above 15 refuses rather than being masked into a
    different, plausible colour.
  - **15bpp direct colour** ships as a pair: `<cell>.png` (RGBA8 — the colour is authoritative, the
    alpha is a *cutout flag* that is checked but never read back) plus **`<cell>.stp.png`**, a
    one-bit-per-texel sidecar carrying the hardware's blend flag. Both files are the format: a hole
    and a "black, but blended" texel are different values that look identical on screen, so one alpha
    channel structurally cannot carry both. A missing sidecar refuses.
- **New guards, both stated by you and checked against the container**: `expect_bpp` (the same
  `0x4000` bytes are 256, 128 or 64 texels wide at 4 / 8 / 15 bpp, so this is the one number that can
  be wrong quietly) and `expect_cell`.
- **Four things that used to be flat refusals are now remedies you can discharge**:
  - a cell **uploaded by more than one writer** builds once you name *every* writer with its own art
    and say `acknowledge_cotransform = true`. There is deliberately **no "same art for all writers"
    shorthand** — across the whole stock corpus no two writers of a cell hold the same bytes, so a
    broadcast key would be the tool asserting something the game's own data denies;
  - a model whose **picture is wider than one page** builds once you name every cell it reads and say
    `acknowledge_spill = true`; a read-only stitched `spill.<geom>.png` preview ships beside the
    editable cells so you can judge the whole picture while editing the pieces it is made of;
  - a cell **shown through two different palettes** is editable in one of them, with every other key
    written out as a NAMED read-only alternate view of the same bytes — an author who never learns
    the second key would tune a colour they cannot see;
  - a cell **read by several models** builds, and the report NAMES the other models rather than
    letting one edit change two things silently.
- **What still refuses, and why it says so by name.** Most of a summon's scenery is unaddressable for
  a reason no feature fixes: **93 % of scenery cells have no model in the container that samples
  them**, so the file never states what colour depth they are, and a statistical guess was built,
  tested and thrown away (it agreed with the truth 54.5 % of the time on a three-way choice). Those
  cells refuse **by name, with that measurement**, and so do: a cell two models read at *different*
  depths; the containers whose own effect program re-uploads VRAM at run time (a repaint there is a
  lost edit with no symptom); and a model reading a column nothing in its container uploads. Running
  `export-art` lists every refused cell and its reason, and the emitted scaffold prints them as a
  commented block — the refusals are most of the surface, so they teach rather than merely omit.
- **A real gap closed while doing it**: a scenery repaint used to run with the container's page-block
  header and rect table *ungated*, where a mis-seek would have silently re-aimed the whole page map
  while everything still parsed. Both are now protected on every build, and the map is **re-derived**
  from the patched bytes and compared, not merely byte-checked. Docs:
  [`docs/SUMMONS.md`](docs/SUMMONS.md#the-scenery-texel-lane-w6b-1),
  [tutorial 14](docs/tutorials/14-summon-reskin-rescore.md#repainting-a-summons-scenery).

### Changed — five stock summons that could not be reskinned at all now can (the TEXANIM read)
- **TIER W rung W7** (`studies/custom-summons/tier-w/W7-TEXANIM.md`): five stock summon containers —
  **ef038 (Shiva)** and **ef177 / ef493 / ef494 / ef495 (Carbuncle ×4)** — carry a *texture-animation*
  table that `summon-reskin` refused to edit, because nobody had read its format and one of the things
  it might have been doing (swapping the creature's palette mid-cast) would have made a recolour
  pointless. **The table is read now, and it does none of those things**: it copies a small rectangle
  of palette *indices* from a spare strip into a live window inside one creature part's own texture
  page. It cannot change a palette, and on the PC build nothing plays it at all. So:
  - **a creature recolour on those five effects now BUILDS, with no acknowledgement key** — the whole
    class was previously unreachable;
  - **a scenery recolour on them needs no key either.** `acknowledge_texanim` is now a **deprecated
    no-op wherever the table decodes** (that is: on every stock container): it is still accepted for
    one release so existing specs keep building, it is reported when used, and `scaffold` no longer
    emits it. Delete the line when you next touch a spec. On an armed table the reader *cannot*
    decode, the key keeps its original pre-W7 meaning and is still **required** for scenery;
  - **a texel repaint on those five now builds too** — a whole-page repaint with no key, and a
    *localised* one once your edit **reaches** every rect of each animated clip family (the check is
    at least one changed texel per rect — a dense repaint passes in practice, a sparse remap can
    honestly miss a rect and refuse). If you repaint an animated window and leave the frames it swaps
    in untouched, the build refuses with a **work order**: the clip, the rects you painted, and the
    exact rects you left stock. `[[reskin.texel]]`
    gains `acknowledge_texanim_frames = true` (a literal boolean) for a deliberately asymmetric strip.
- **The authoring readouts now print the decoded table** instead of `TEXANIM ARMED (116 bytes)` —
  `scaffold`, `plan`, both lanes' derivation reports **and `export-art`** (report, manifest and the
  emitted texel scaffold) list each clip's part, frame count and rect, plus the protected rect set a
  repaint has to respect — visible *before* you paint, not as a later refusal. The opaque byte count
  was the reason the old refusal could not be acted on.
- **New `summons/texanim.py` — a READER, deliberately with no writer.** It refuses rather than
  guesses: a region whose three sub-arrays do not tile it exactly, whose offsets leave it, or whose
  rects leave the part's own page does not decode — and a table that does not decode is treated
  exactly as it was before this release, per scope: a creature target refuses outright, a scenery
  target needs `acknowledge_texanim`. The lift is conditional on a *successful
  parse*, so an unknown container shape degrades to the old behaviour instead of silently passing.
- **New hard rule, enforced in both lanes at the point of the edit:** the texanim region is never
  resized, relocated, zeroed or rewritten, and `firstBlock` is never edited — the loader keys a real
  decision on that comparison. Every `summon-reskin` build (recolour or repaint) now asserts the
  region came out byte-identical and reports the verdict in `plan`/`describe`.
- **27 new kit tests** (`test_summon_texanim.py`, plus the inverted and split pins in
  `test_summon_reskin.py` / `test_summon_repaint.py`): the decoder's round trip is byte-identical on
  every armed region and on synthetic fixtures, `parse` never raises across all 372 stock containers,
  and the corpus census (which effects are armed, how many clips, which part, and that the four
  364-byte tables are byte-identical — one Carbuncle shipped as four ability rows) is re-measured from
  the containers rather than asserted from a constant. Docs:
  [`docs/SUMMONS.md`](docs/SUMMONS.md) (the texanim sections in both lanes),
  [tutorial 14](docs/tutorials/14-summon-reskin-rescore.md#the-texanim-table--five-summons-that-are-no-longer-off-limits).
  **Cast-proven in-game, both ways**: a recoloured Shiva reads magenta across her whole cast, and a
  marker painted into the animation's spare frame strip never appears — the animation really is
  dormant on the PC build, confirmed on a 60 fps capture, not only in the disassembly.

### Added — `summon-reskin` gains a second lever: the TEXEL REPAINT (`export-art`, `[[reskin.texel]]`)
- **TIER W rung W6a** (`studies/custom-summons/tier-w/PLAN.md`): `summon-reskin` grows a second
  edit lever alongside the CLUT recolour above — a texel repaint that rewrites the palette INDICES
  themselves, so it can move a shape, an edge, a silhouette, which a recolour structurally cannot.
  Landed for **creature texture pages only**, the one texel class corpus-wide free of every known
  hazard (single-writer 24/24 packages, 0 VRAM-cell and 0 file-span collisions against every
  scenery/id-9 page over 93 pages, uniform 8bpp). Scenery pages refuse by name — co-transform /
  same-bytes-two-bindings / u-spill / 15bpp — deferred to a later rung (W6b).
- **New `summons/repaint.py`** (1,621 lines) — consumes `reskin.py`'s own derivations
  (`creature_pages`, `PaletteMap`, `texanim_region`, a new `partition` parameter on `_regions`)
  rather than re-deriving them. The format of record is a **P-mode indexed PNG** — pixels ARE the
  palette indices, the loaded palette is display-only (the container stays the palette authority;
  this lane writes zero CLUT bytes), `tRNS` marks the cutout entry — measured byte-identical round
  trip **93/93** across every stock creature page in every one of the 24 decodable packages; an
  RGBA export is refused by name with the measurement that rules it out (an identity round trip
  that paints nothing already moves 1,844 of 16,384 texels on ef251 part 0, because 8.31% of the
  corpus's palette entries duplicate the full 16-bit word, STP included). Ships THE CUTOUT LAW (an
  index crossing the palette's one alpha-0 entry, in either direction, refuses unless
  `acknowledge_cutout_reshape = true`, a literal boolean), an unconditional TEXANIM refusal on the
  five armed creature packages (ef038/177/493/494/495 — no key lifts it, unlike the CLUT lane's
  scenery-only escape hatch, because there is no scenery half of a texel edit to fall back to), a
  CO-TRANSFORM collision gate measured per target rather than assumed, the region partition
  INVERTED for this lane (the CLUT strip gated byte-identical instead of the texel pages, via a new
  `partition=` argument on `reskin._regions` — one function, two partitions, never a second copy
  that drifts), and a dead-pad census reported, never fatal (only 64.0% of the corpus's creature
  texels are ever sampled by a face — 975,202 of 1,523,712).
- **`export-art` — a new `summon-reskin` action**, registered on the reskin lane only: decodes
  every creature page to its paintable PNG + a `<part>.coverage.png` UV overlay (green hatch = the
  never-sampled pad, rasterised from the container's own uv pools, corner-included so a
  one-texel-thin face still lights its own texel) + `art.manifest.json` (the stock sha256 drift
  guard + every page's derivation) + a guarded `texel.scaffold.toml`, under the same local-only
  root every summon art-export already refuses to write outside of.
- **Composes with the CLUT lane in one container, one ledger, one revert** — a spec may carry
  `[[reskin.target]]`, `[[reskin.texel]]`, or both; with both, `build` recolours first and hands the
  patched bytes to the repaint, and the composed self-check proves the two halves' changed-offset
  sets are disjoint rather than asserting it. **`summons/reskin.py`** gains the matching hook in
  reverse: `ORTH_REBUILDERS["repaint"]`, so a CLUT-only spec can also name a texel sibling and prove
  the same disjointness from its own side. **`cli.py`** gains the `export-art` action wiring and the
  one-spec composed build/plan/verify/deploy/revert path, staged by whichever lane owns the
  resulting artifact.
- **73 new kit tests** (`test_summon_repaint.py`) — every refusal named above ships with its own
  test, plus install/corpus-gated acceptance: the 93/93 indexed round trip and the 0-collision
  census over the real 24-package corpus (via the kit's own `creature_texel_pages`), `export-art`
  end to end against ef227 (6 pages, 65,267 covered texels reproduced exactly), and — THE PROOF —
  an offline composed build that rebuilds the CLUT lane's cast-proven ef227 spectral-mist reskin
  (`sha 7fef205f…`, the artifact the owner already judged in-game — re-pinned and still
  byte-identical after this rung, alongside Phoenix ef211 and Madeen ef251) and splices a
  procedural brand onto part 0's wing on top: **4,832 CLUT bytes + 1,036 texel bytes changed, zero
  cutout flips, zero dead-pad bytes, the two halves' changed-offset sets disjoint by construction
  and gated so** — composed `sha 353f7867…`. An in-game cast of this artifact has not run yet; the
  offline gates are green and the artifact is staged for one.
- Docs: [`docs/SUMMONS.md`](docs/SUMMONS.md) (the texel-lane section — the `export-art` workflow,
  the `[[reskin.texel]]` schema, the indexed-PNG format of record, THE CUTOUT LAW, the
  unconditional texanim refusal, the dead-pad report, and an honest W6b deferral naming the
  scenery hazards), [`docs/FEATURES.md`](docs/FEATURES.md) row,
  [tutorial 14, Part C](docs/tutorials/14-summon-reskin-rescore.md#part-c--repaint-its-texture-the-texel-lane-reskintexel),
  [`../SETUP.md` §7](../SETUP.md#7-cli-command-reference).

### Added — `summon-reskin` / `summon-rescore`: recolour and reframe a STOCK summon in place
- **Promotes the TIER W study** (`studies/custom-summons/tier-w/`) into two first-class CLI verbs
  that edit a stock FF9 summon's OWN container bytes — no donor swap, no new model, unlike the
  `[[summon]]` transplant lane. `summon-reskin` is a CLUT recolour: the creature's palettes AND the
  effect's own scenery (THE EFFECT-OWNED SCENERY LAW — a summon's cinematic ships its own ground/
  sky/fire-field, drawn on its own schedule, not the arena it's cast in), rotated in HSV and spliced
  back at the exact same file offsets, with `0x0000` held byte-exact and the transparency bit
  carried, never recomputed. `summon-rescore` reframes a shot's pose/focal distance on the same
  id-2 camera-archive format the battle engine's `camera_codec` already round-trips byte-identical
  across all 372 stock effects, with every duration and the container's byte length untouched (the
  camera and the effect program are two clocks the original author kept aligned; a content rescore
  moves neither). Both climb one shared six-verb ladder — `scaffold | plan | build | verify | deploy
  | revert` — where `scaffold --ef <id>` reads ANY stock summon out of the user's own install and
  emits a fully guarded, commented spec toml with every knob at identity, and `deploy`/`revert` write
  through / undo a write ledger straight into a resolved mod folder.
- **New `summons/camera.py`** (692 lines) — the camera extractor + adapter + read-out, carrying the
  id-2 extra-sector correction and the Code frame-word high-bit correction. Deliberately ships
  WITHOUT the study's tier-R state-machine recovery (a full MIPS disassembler + annotator, ~4,650
  lines + a 165 KB data file the corpus proved is advisory-only — one "reframe budget" column);
  `machines=()` is the default everywhere, matching the study's own `--no-phases` mode.
- **New `summons/rescore.py`** (1,451 lines) — the pure content-rescore engine: the three hard
  constraints enforced at the call site (no duration edit, no byte-length change, the frame word's
  undecoded high bits survive by never being written), THE THREE-SEQUENCE TRAP, and THE DYNAMIC-OP
  DISCLOSURE gate — **324 of 372 stock effects** carry a runtime-chosen `PLAY_CAMERA arg2=3` camera
  op whose reachable blocks are absent from the container entirely; ef227, the effect this lane was
  first hand-proven on, was the zero-op outlier and its offline completeness claim does not carry
  past it.
- **New `summons/reskin.py`** (2,577 lines) — the pure whole-set recolour engine, generalised past
  the one hand-tuned effect: every palette span DERIVED (never tabulated) off a container's own
  id-0/id-4 headers, `so`-record attribution replacing a hand-authored SHARED table, THE TEXANIM
  GATE (creature scope refused outright on ef038/177/493-495; scenery needs
  `acknowledge_texanim = true`), multi-writer/dual-depth CLUT-cell detectors, and a MEASURED headroom
  gate (46 of the corpus's 93 creature CLUT rows peak at the 5-bit ceiling — ef227 was the one
  effect that happened to have headroom to spare, and "stock leaves headroom" was never a law).
- **New `summons/ledger.py`** (267 lines) — the write/backup/readback/revert accumulator both edit
  lanes share, a strict superset of the transplant lane's own `_Ledger` (`summons/deploy.py`, left
  as-is — a documented, one-directional duplication, not a silent fork); a `ModFileList.txt` is
  appended to and never created, and every emitted revert script is `--root`-rebasable.
  **`summons/container.py`** gains `parse_directory` / `Op`+`parse_op_stream` / `scan_geom`+
  `Geom.end` (ported from the study's disassembly-only `ef_container.py`, folded onto the kit's own
  parser rather than duplicated into a second one). **`battle/camera_codec.py`** gains public
  `parse_camera`/`serialize_camera`/`split_code` aliases over its existing underscored functions (the
  battle round-trip tests stay green by construction). **`config.py`** gains `resolve_mod_folder()` —
  the documented `--mod-folder > $FF9_MOD_FOLDER > .ff9deploy.toml > FF9CustomMap` precedence,
  implemented once and used by these two new verbs (the existing `summon-import`/`summon-deploy`
  still carry the literal-default subparser trap this promotion's own regression tests pin down;
  retro-fitting them is a separate decision).
- Docs: [`docs/SUMMONS.md`](docs/SUMMONS.md) (the full spec-toml schema for both lanes, every
  refusal, and the laws behind them in house voice — THE TEXANIM GATE, THE SATURATED-RAMP LAW +
  the TWO-LOBE refinement, THE EFFECT-OWNED SCENERY LAW, THE ADDITIVE-COMPOSITING COROLLARY, THE
  SILENT-FALLBACK LAW), [tutorial 14](docs/tutorials/14-summon-reskin-rescore.md), the
  [`FEATURES.md`](docs/FEATURES.md) row, [`SETUP.md` §7](../SETUP.md#7-cli-command-reference).
- **233 new kit tests** (`test_summon_reskin.py` 81, `test_summon_rescore.py` 93,
  `test_summons_camera.py` 43, `test_summons_container.py` +16), pure-logic + hand-built synthetic
  containers that run on every CI pass with zero install/corpus, plus the CLI's own registration and
  `argparse.SUPPRESS` root-flag-survival regression tests. Every refusal named above ships with its
  own test, and the build path is additionally held to install-gated byte-identity acceptance tests
  against the study's own cast-proven artifacts — `summon-reskin`'s covers all three reskin
  artifacts (Bahamut ef227, Phoenix ef211, Madeen ef251); `summons.rescore`'s covers Bahamut ef227's
  rescore at module level; and the Phoenix ef211 rescore (`7979566f…`) is pinned end-to-end through
  `summon-rescore build` in the CLI acceptance suite. All four artifacts the promotion's design
  brief named as the acceptance bar are wired to tests.
- Grounded in TIER W (`studies/custom-summons/tier-w/PLAN.md`): rungs W2–W4 cast-proven in-game on
  Bahamut ef227 ("worked as described" on every judged cast — reframed, retimed, whole-set
  recoloured), then W5 generalised every tool past that one hand-tuned effect and cast-proved all
  three levers a SECOND time on effects never hand-tuned against — Phoenix ef211 (scenery recolour +
  camera reframe, after THE ADDITIVE-COMPOSITING COROLLARY corrected a first key that read stock in
  its own cast) and Madeen ef251 (creature recolour). The study's own scripts
  (`reskin.py`/`rescore.py`/`summon_camera.py`) now shim onto this kit surface rather than
  duplicating it.

### Added — the Behavior tab EDITS (rung B: the ladder is writable)
- The ladder's rows grew move-up/down (the priority edit — first-match-wins means order IS
  the program), Edit, and Delete; the unit bar adds branches and removes units; the cast rail
  (and the no-behavior guide) gained **Add unit…**, seating a minimal legal tree (death branch
  + `hold_post` fallback) on any named `[[npc]]`. Edit opens the **branch editor**: the branch
  as its own TOML fragment — exactly the text the chips render — with When/Do insert menus
  generated from the compiler's verb tables and a live readout (parse errors, then
  `validate()`'s own words over the applied copy, then the quiet go-ahead). Apply writes into
  the open document through the Workspace's real undo (one labeled step per edit; Ctrl+Z lands
  back on the Behavior tab), dirty-dots the member, and re-renders ladder + stage + problems.
  A new inert branch (`flag = "never"` guard) opens ready to shape.

### Added — the Workspace **Behavior** tab (read-only, rung A)
- A new Author-group tab rendering the open field's `[behavior]` block: the CAST rail
  (units / groups / pools / counters, tables, schedules, scans, HUD strips), the selected
  unit's LADDER (branches as guarded priority rows in TOML order — the compiled semantics —
  with decorator chips and the required fallback labeled), and the STAGE (posts, patrol/march
  routes, flee refuges, scan/wander boxes, and the selected unit's engagement radii drawn on
  a zoomable canvas in the layout probe's +z-up frame). The Instruments column docks into
  the shell's INSPECTOR while the tab shows (the ladder keeps the doc's width): the
  compiler's own `validate()` problems live, and a **Compile (dry)** button runs the real
  `behavior compile` lane off the saved file on a worker thread — blackboard map, byte
  histogram, and public/pool flag indices with copy-ready `set_flag = [N, 1]` rows. Fully
  read-only: editing stays in the Editor form (rung B is the ladder editor). Vocabulary is
  derived from the compiler's own verb tables, so new verbs render with zero GUI changes.
  Charter: `studies/behavior-trees/GUI-VISION.md`.
### Added — `[siege]`: the fort-condor tower-defense as ONE declarative block
- THE PRODUCTIZATION of the fort-condor arc (`content/siege.py`): the 557-line
  bench script's authoring decisions — clock, waves, hireable classes, raider
  types, base, economy, positions — as a single TOML table. Desugars at project
  load (the `[[ferry]]` pattern) into the round-4 GROUP RE-FIT shape proven on
  field 30400: the data-table wave clock, the two rosters + alive-headcount
  scans, the war-room `[[behavior.hud]]` strip, priced pools (the SELECT
  poller on the first), every unit tree (raiders march/PIN/commit; allies
  fight by STANCE — "chase" pursues, "hold" is contact=radius-1 artillery),
  THE WIN-CONDITION SHAPE (endings detect, ONE payout), parked 9000-band
  pooled seats, and the honest WAR COUNCIL (rows gated on the pools' hireable
  flags, resolved by an internal allocation pass — the bench's two-pass,
  productized). `[siege]` OWNS `[behavior]` (conflict = build error); refuses
  verbatim forks. Named for the game shape, like [[gauge]]/[[qte]]/[[ferry]].

### Fixed — `cam.to_canvas` now folds in a real camera's GTE `centerOffset`
- The painted-canvas map (`cam.to_canvas`, and through it `solve_z_for_canvasY` /
  `horizon_canvas_y`) omitted the camera's GTE `centerOffset` — correct for every kit-authored
  camera (always `[0, 0]`, byte-identical there) but wrong for imported REAL cameras. Proven
  case: donor `fbg_n11_ldbm_map158_lb_plz_0` (field 559, centerOffset `[26, 400]`) projected
  its spawn OFF-canvas at (-9.5, -13.8) instead of the true (16.5, 386.2). The map is now
  `canvasX = rawProj.x + centerOffset.x + w/2`, `canvasY = h/2 + centerOffset.y - rawProj.y`
  (the exact canvas-frame image of the engine's `project_screen`). Downstream, this corrects
  import spawn selection (`extract`'s on-camera test), the `compose_background` walkmesh
  footprint / Blender backdrop, the repaint-native walkmesh outline, `field_layout_probe`'s
  camview, and the Blender editable-fork view-offset fit on offset donors. Regression pinned
  against the real map158 camera in `tests/test_cameras.py`.

### Fixed — single-field auto story-flags moved into the provably-safe band (save-corrupter default)
- The single-field auto once/gate-flag defaults (an unflagged `[[event]]` / `[[cutscene]]` /
  zone-`[[choice]]` / `[[on_entry]]` / `[ate]`) allocated from the legacy 8000/8100/8200/8300
  bands — all below `FIRST_SAFE_FLAG` (8712), and the on_entry/ate band (8300+) sat **inside the
  stock Mognet MAILBOX slot bytes** (`Byte[1024-1045]` = bits 8192-8367 — wipe-guard, delivered
  counter, and the 12 live letter-slot bytes, whole-byte-written by ordinary play at any real
  moogle): a defaulted `[[on_entry]]` hook corrupted real letter state, and reading a letter
  cleared the hook's once-flag. `[ate]` and `[[on_entry]]` #0 also shared index 8300 outright.
  The defaults now live in per-lane bands inside the safe band (`flags.AUTO_*_BASE`: event 9100+ /
  cutscene 9200+ / choice 9300+ / on_entry 9400+ / ate 9500+, width 100, placed clear of the
  `[behavior]` compiler's blackboard bands), and `build._FlagAlloc` **skips any flag index the
  same project references explicitly** (`flags.collect_safe_flag_indices`) — a defaulted block can
  no longer alias an authored story flag in the same build; band exhaustion is a loud `BuildError`.
  `flags.py` gains the `mognet_mailbox` reserved region (8192-8367), so `lint` / `flags-inspect`
  now name a write there. Campaign/journey member allocation (per-member `flag_base` windows) is
  unchanged. Migration note: a save that had legacy auto flags set replays those once-blocks one
  time; a toml that hand-referenced a legacy auto index (e.g. gating on 8000 to read event #0's
  implicit flag) should switch to an explicit `flag = N` — the dangling-flag lint points at it.

### Changed — every import mode now emits `entry_settle = "auto"`
- `ff9mapkit import` (native / editable / BG-borrow / lightweight) and `import-chain`
  logic-only members now write `entry_settle = "auto"` under `[camera]` — the computed
  camera-settle hold behind the entry fade — so a fork never boots with visible warp-in
  drift unless the author deletes the key. Verbatim forks stay bare: the donor `.eb`
  carries its own real entry sequence, so the key would be a lint-flagged dead no-op
  there. Tomls without the key build byte-identically (the settle machinery is unchanged;
  only the generated scaffold gained the line).
- Blender add-on **0.9.29**: `bridge.editable_field_toml` (the CLI-mirror re-export of an
  editable fork) now emits the same `entry_settle = "auto"` line first under `[camera]` —
  it silently dropped the settle on re-export, the same silent-loss class the `_merge_scene`
  camera graft closed. The line is a byte-for-byte mirror of the CLI's constant, pinned by
  a blender test (the add-on can't import `ff9mapkit` inside Blender).
- The remaining generators now emit the same line: the `ff9mapkit new` scaffold (its
  template camera resolves, so the scaffold still builds clean — the one surfaced line is
  the computed hold, asserted) and the experimental `image-field` toml. Every field.toml
  generator in the kit now carries the settle; the ONLY bare `[camera]` left is a verbatim
  fork's, by design.

### Fixed — `world-locate`: geography now follows the engine's CELL-tag dispatch, not tile IDALL areas
- The area→place join was measured wrong (2026-07-25 Object-mesh census): the engine packs the
  walked tile's CELL COORDINATES into the world dispatch key (`WorldEvent`:
  `0x8000 | z<<8 | x<<2 | id`), GetIP-matches it against object-0's function tags, and the
  matched trigger's `Byte[39]` literal picks the dispatch-switch case — the tile's IDALL
  `area` bits are never read (a cosmetic regional tag). The old join filed Alexandria's tile
  cluster under Marsh/Entrance 650 and Qu's Marsh under Treno/Gate 908 because case numbers
  coincide with unrelated area numbers. `world/locate.py` now decodes `case_to_cells` /
  `case_to_blocks` from the object-0 cell tags (alias tags = multi-cell entrances resolve
  through the shared body; triggers with no `Byte[39]` report under case `None`), names each
  entrance by the engine's `navipos` landmark table (embedded, with honest distances), and
  `area_to_fields` is renamed `case_to_fields` (old name kept as an alias — the cases never
  were IDALL areas). `world-locate` prints cells + landmark per case and drops `--disc`
  (geography is dispatcher-derived); `--area` filter is now `--case` (old spelling accepted).
  `world-retarget` no longer implies a tile-area stamp routes anywhere: it now reports the
  block's actual dispatcher triggers. Landmark pins (Alexandria Harbour block (21,10),
  Lindblum Dragon's Gate (14,15)) + the cell-tag join are regression-tested.
### Added — `[[gauge]]`: the tiles-as-sprites value bar (the DLL-free gauge)
- FF9 has no gauge opcode; `[[gauge]]` builds one from the tile vocabulary
  (`content/gauge.py`): the kit GENERATES `segments+1` fill-state PNGs (a complete
  self-backed bar per state), appends them as pure-Memoria overlays plus one
  script-controlled (`SingleFrame`) tile ANIMATION, and a looping daemon drives the
  bar with ONE `SetTileAnimationFrame` per tick — the level is a branchless
  clamp expression computed inline in the opcode arg (`EBG_animShowFrame`: frame i
  shows target overlay i; 255 hides all, which is how `requires_flag` hides the bar).
  Sources: `global:<off>` / `item:<name-or-id>` / `gil`. `pulse_below` shimmers low
  values with field 64's Sin color pulse, carried VERBATIM (`Sin(t<<2)/360+144` on
  the visible overlay via `SetTileColor`). The daemon's state lives in ENTRY LOCALS
  (stock's `allocate 2` — `eb.edit.append_entry`/`seat_entry` grew a `loc` param),
  so gauges coexist with `[behavior]`. Three scene hosts: novel (appends to the
  field's own `.bgx`), NATIVE (`[field] bgs` — an own-scene `USE_BASE_SCENE` hybrid
  re-loads the shipped `.bgs` first, per-tile depth untouched, base indices read
  from that header offline; the minigame-arena path), and BG-borrow (the hybrid
  under the DONOR scene name, pinned by `[field] borrow_scene_counts`; scene-name
  keyed — bench-scoped). `scene/bgx.py` grew the typed `Animation` block
  (+ bare-flag `Loop`/`Palindrome` parse). Verbatim forks refused in v1.

### Added — `[[qte]]`: the Blank-duel reaction game as kit vocabulary
- FF9's one QTE (the Prima Vista sword fight, field 64) decoded and re-emitted with
  rounds / reaction window / prompt set / texts as parameters (`content/qte.py`):
  random no-repeat button prompts (stock's own [DBTN]/[MOBI] glyph lines, verbatim),
  the nine-button edge poll with Start-bail, and stock's exact two-channel scoring —
  a hit banks the countdown LEFTOVER (speed is the score) plus the current combo.
  Finale: a 1..100 score into `Global.Int16[result]`, tiered verdicts, the optional
  gold-lettered gil purse (stock's formula), an optional completion flag. One modal
  seated entry opened from a `[[choice]]` option's `qte =` (the numeric_input
  architecture — stock only split issuer/poller across entries for its actor
  choreography, which is deferred theater along with hit/miss SFX and the
  combo-gated difficulty ramp). Synth-only; refuses [behavior] coexistence (scratch
  band overlap).
- The modal scratch band moved to bytes 2018-2031 (was 2026-2039): the old band's four
  Int16 channels (combo / max-combo / points / bonus) sat exactly on the netsync co-op
  cells (bytes 2032-2039), which the engine rewrites EVERY FRAME while `[Netsync]` co-op
  runs — on any field, `[[coop]]` gates or none — so a bout under live co-op had its
  scoring clobbered per frame. The band is now the `qte_scratch` reserved region in
  `flags.py` (bits 16144-16255), so a `[[qte]]` `flag`/`result` — or any lint-walked
  story flag — can no longer be allocated inside the scratch; `result` caps at 2016.

### Fixed — a `[[numeric_input]]` result word can no longer land on live engine state
- The stepper's `result` cap dropped 2038 → 2016 and the word's 16 bits now walk the
  reserved save regions (the same validation a `[[qte]]` result gets): the old cap
  admitted a result inside the netsync co-op cells (bytes 2032-2039) — which the engine
  rewrites every frame while co-op runs, clobbering the submitted value — and did not
  refuse the Mognet mailbox/lock/read-mail bytes or the byte-23 menu handshake either.

### Added — `add_shop_synth` / `remove_shop_synth`: runtime synthesis recipes (0x116)
- The AddShopItem twin with the mutation inverted: grafts the SHOP onto the RECIPE's
  shop list (the engine's silent no-op guard is on the recipe). `recipe` = a vanilla
  int id, or a `[[synthesis]]` RESULT name resolved at build to the CSV emitter's
  deterministic mint (keyed by resolved item id — "Phoenix Down"/"PhoenixDown" both
  land; a string selector needs a reachable install). Lint refuses a BUY-shop target
  (a `[[shop]]` id or vanilla 0-31 opens as Buy and never renders recipes). The
  hidden-recipe idiom: declare the locked recipe on a PARKED shop id, graft the real
  shop at runtime. Same event-Once + remove-then-add + session semantics as 0x115.

### Fixed — `have_item` reads a top-of-tick snapshot (the pool-consumption race)
- Pool activation runs before the tree blocks, so a live `have_item` read raced an
  item pool consuming the same item — holding exactly N never satisfied
  `have_item >= N` (ARMOURY round 2, owner-diagnosed: the unlock needed 4 writs, not
  3). The cond now reads a snapshot written with the mirrors, before any pool
  consumes; the pool's own gate stays live (it is the consumer). Regression-pinned:
  snapshot → consume → judge ordering asserted on the compiled ticker.

### Added — `add_shop_item` / `remove_shop_item`: runtime shop stock (AddShopItem 0x115)
- Behavior branches can now mutate a shop's buy list mid-run — the wave-by-wave
  armoury unlock (`do = { add_shop_item = [40, "Elite Contract"] }`, `once` required).
  First use of Memoria's extended `AddShopItem` opcode anywhere (zero shipping fields
  carry it). The compiler bakes in the engine semantics: remove-then-add idempotence
  (the raw list-add duplicates), lint refusal of a shop id absent from ShopItems.csv
  (the engine silently no-ops), and the event-Once lane so the session-global
  mutation re-asserts per field entry (the seed law; resets at relaunch, never saved).

### Added — the ITEM pool: the native shop as a hire menu
- `[[behavior.pool]] item = "<item>"` makes a pooled roster's currency an ITEM: no
  request-flag lane at all — holding the item IS the request. Each ticker pass converts
  one held item into one spawn at the player (`B_HAVE_ITEM` gate; `RemoveItem` at the
  spawn site, so an exhausted pool consumes nothing — contracts are real inventory).
  The hire UX is the native `Menu(2, id)` shop (`[[shop]]` + `opens_shop`, both already
  shipped): the shop hard-pauses the ticker while open, so purchases muster on the
  first tick after it closes. Companions: the `have_item = ["<item>", n]` cond (live
  GetItemCount) and the `item:<item>` hud value source. `item` is exclusive with
  price/button/request_flag; the pool's `hireable` flag reads the inventory.

### Added — choice `recall`: render a numeric input's SAVED value later
- A `[[choice]]` option's `recall = "<numeric_input>"` re-loads `[NUMB=0]` from the
  input's save-backed result var (× multiplier) before the row's reply — the NUMPAD
  round-3 lesson: gMesValue slot 0 is transient display state shared by every
  stepper's submit echo, so a readback row without `recall` renders whatever number
  was displayed last (the bench's muster Report row showed the previous *bid*).

### Added — `[[numeric_input]]`: the Treno bid stepper as kit vocabulary
- The game's one number-entry idiom — the Treno auction's 3-digit ×100 stepper, carried
  byte-for-byte by nine shipping fields (852/909/1600/1607/1909/2800/2950/2951/2952) —
  re-emitted with digits (1–4), multiplier, ceiling, `gil_ceiling` (the live GetGil
  clamp), start value, and texts as parameters (`content/numinput.py`, grounded on field
  909's `Code10_31` + `.mes` 203–206; the kit's default-position cursor overlays
  reproduce stock's entries BYTE-FOR-BYTE, pinned by test). Opens from a `[[choice]]`
  option's `input = "<name>"` (modal, movement locked by the choice bracket; such menus
  auto-dispatch via the one-read switch — the nested-window sysvar-9 law). On submit the
  stepped value lands in `Global.Int16[result]`, gMesValue slot 0 loads the full value
  for `[NUMB=0]` echoes/replies, and an optional `flag` bit raises; cancel touches
  nothing. Layout is font-metric-free by construction: the digit run lives in its own
  frameless window and each pink cursor overlay ([B880E0][HSHD], FFIXTextTagCode.Pink)
  re-renders the same [NUMB] at `x + 7·i` — stock's own overlay mechanism, decoded.
  Synthesized fields only for now; a field can't carry both a stepper and a
  `[[behavior.hud]]` strip (one shared 8-slot gMesValue bank; validate refuses).

### Fixed — `world-forest`: the zip annulus' fallback cells wear the mint's own texture policy
- The carve's fully-dropped ring cells — on a real island MOST of the ring (36 of 41
  cells on the island-E bench) — resolved through an uncoupled per-cell uniform pick,
  which the UV arc proved reads as a chevron/diamond quilt (same-rotation ~0.23 vs the
  real map's ~0.49). They now resolve through `grassland.assign_mains_seeded`, the
  UV-arc-proven constrained-boundary mirror of `assign_mains` (uvf_fix2's DIVERSITY
  POLICY): cells decoded from the kept bytes pre-seed the W/S coupling and are never
  rewritten; with an empty pre-seed the mirror is bit-identical to `assign_mains`
  (pinned by test). Byte-conservative outside the fill — only fallback-cell zip UVs
  change (verified per-channel old-vs-new on the island-E carve; ring same-ori 0.23 →
  0.52). `decode_cell_pick` stays for single-cell forensic use. NOTE: a pre-policy
  island-E deploy no longer byte-matches the identity net — re-carve rather than
  restore old backups.

### Added — HUD value sources (`gil` / `timer` / `hp:<unit>`) + per-slot `digits`
- A strip's `values` are now value SOURCES, not just counters: a counter name, `"gil"`
  (the live purse, `B_SYSVAR[6]`), `"timer"` (the countdown HUD's remaining seconds), or
  `"hp:<unit>"` (a unit's hit points — the roster cell for a group member). `digits`
  takes a per-slot list so a 6-digit gil readout can share a strip with 2-digit
  headcounts. The Int16 dirty mirrors are gone: slots are written every pass (a
  `gMesValue` store is a bare array write and the ENGINE already re-renders only on a
  real change), which also removes the Int16 ceiling a gil readout would have hit.

### Added — the substrate polish round: scan group form + `alive_only`, engage `nearest`, `[[behavior.hud]]`, extended opcodes
- **Scan group form**: `[[behavior.scan]] group = "<roster>"` loops the group's OWN
  tables (no position copies), `point`/`radius` become optional (absent = a pure roster
  headcount), and `alive_only = true` gates every cell on act && hp>0 — the team-wipe /
  alive-count primitive (`counter_eq = ["mus_alive", 0]` fires the moment the roster is
  wiped; the truthful-counter lesson from the brawl's unreachable 13-kill finale). ~100B
  of ticker per scan; the group mirror block now runs before scans (same-pass freshness).
- **Engage `nearest = true`**: the acquire loop becomes an argmin over Chebyshev distance
  (|d| by conditional negate, max by conditional copy — the no-squares Int24 stance) —
  units pair off with the closest living foe and survivors pivot to the closest next
  victim. Scratch registers shared field-wide (four blackboard slots total).
- **`[[behavior.hud]]`** — the live counter strip on the stock substrate every PC
  minigame HUD uses (no number opcode exists in FF9): `SetTextVariable` (0x66, the cell
  as an expression arg) feeds `[NUMB=i]` slots and a TRANSPARENT `WindowAsync` (flags 16)
  re-issues in place, only on change (the hunt-points dirty-mirror shape). The `.mes`
  line mints like an announce, `[IMME]` auto-prepended. 1..8 counter values per strip,
  one strip per window id, ~150B of ticker.
- **Extended opcodes 0x112–0x11E** (`AddShopItem`, `WalkEx`, `ClearMemoriaVector`,
  `AddBattleStatus`, …): the regen script grew a documented CUSTOM_EXTENDED block (the
  engine reads these ad hoc with getv3 — they are absent from its static tables) and the
  optables now carry their true arg shapes; encode→decode round-trips pinned by tests.

### Added — `[[behavior.group]]` + the `engage` verb: THE GROUP LOOP (v2 rung 1)
- Rosters as table state: a group's members get `group.<name>.px/pz/act` mirrors and an
  `hp` table that IS their hit points (the `hp_le`/`hp_gt` conds and every SwingAt
  damage write reroute to the cells — one home, no drift; `table_*` conds can read
  them). The `engage` branch verb replaces the unrolled pair apparatus: a sticky
  acquire loop holds a first-in-range target register (roster order = priority order,
  v1 parity), the branch runs two-phase (contact -> ONE target-indexed strike body
  with computed-index damage and table-position facing; else -> a pursue feed on the
  target's cells), and a dead/escaped target drops the register for automatic
  re-acquisition. Measured on the 7v7 parity bench: **42% of the unrolled bytes** for
  the same fight (~880B vs ~2,340B of ticker per unit; one ~170B body vs six ~108B) —
  the ratio is pinned by a suite test. Rung-1 limits: one engage per unit, no
  self-group targets, no raise/clear flags on the branch.

### Added — `[[behavior.scan]]`: the vector loop (v2 rung 0, EXPERIMENTAL)
- The first stone of the vector substrate: per tick, the roster's position mirrors are
  copied into gScriptVector px/pz tables and a bounded backward-jump loop walks them by
  a LIVE index byte — vector reads **and** writes through the loop variable (the one
  0xD3 composition the BTTABLE proof did not cover) — publishing the inside-the-box
  headcount into a counter and the per-unit 0/1 flags into a named table the `table_*`
  conds can read. The count is derived through the flag write-then-read round trip, so
  an indexing fault breaks the number instead of passing silently. ~400B of ticker per
  8-unit roster. In-game proven (THE PILGRIMAGE, 30416: the whole 1/4/8 announce ladder
  landed true off the loop). Caveat: mirrors freeze on deactivation (a dead unit keeps
  counting); the group-loop proper builds on this.

### Added — the compiled-behavior BYTE HISTOGRAM (`CompiledBehavior.size_report()`)
- The compiler now accounts for every byte it emits: zero-width `__seg` markers in the
  ticker (provably byte-inert — labels emit nothing) + exact body lengths yield a
  per-unit / per-branch histogram — ticker segment, duty body, and each dispatch body by
  action — plus the shared-infrastructure segments (head/mirrors/clocks/pools/hireable)
  and the island-overhead delta. Study benches print it on every dry build. First run on
  the shipped Fort Condor build settled where the budget goes: 126 SwingAt dispatch
  bodies × 108B of byte-identical code (13.6KB of the 15KB body total) — the measured
  target for the scoped v2 byte-economy work (`studies/behavior-trees/PLAN.md`, THE
  THREE WALLS). A third wall was measured en route: the blackboard scratch band is 820
  bytes of `gEventGlobal`, exhausting near 40 units × 6 swing pairs (loudly).

### Fixed — assembler + entry-table hardening (the stress pass)
- **Island REUSE**: long jumps that share a target now repoint at an existing in-reach
  island instead of minting one each (batched per fixpoint round; the strictly-between
  progress law prevents an island's own hop from reusing itself — a cycle). Dense
  same-target bails (thousands of branches jumping to one far label) previously cost 6
  bytes + a fixpoint round APIECE and could exhaust the convergence cap.
- Long-jump **detection now uses the true emit limits** (±32767 signed / 65535 unsigned)
  while island **placement keeps the safe-margin goal** — detecting at the soft margin
  made dense island clusters churn (every insertion nudged neighbors over the soft line
  and re-routed them). The convergence cap scales with input size instead of a flat 400.
- `eb.edit.append_entry`: the chunked entry-table growth **no longer overshoots the
  255-slot ceiling** when the requested slot itself still fits (at 250 entries, slot 250
  used to ask for 258 and be refused); slot 255 stays a loud refusal. New boundary,
  dense-jump, distinct-target, histogram, and 40-unit swarm stress tests (suite +9).

### Added — `[behavior]` `award` + the published per-pool `hireable` flag (the Fort Condor economy pieces)
- **`award`** (`do = { award = 2000, item = "Phoenix Down", count = 1 }`): pay the player gil
  (0..16777215, `AddGil` 0xCE) and/or an item (name or id via the items resolver, `AddItem`
  0x48) — the minigame win-reward lane. **Requires `once`** and compiles on the event-Once
  machinery (edge-latched request lane, latch-FIRST body, no idle loop), which is exactly what
  makes the payout exactly-once even under a forever-true win condition (`time_below = 1`); a
  bare Award, an Award shared across sites, and an un-resolvable item are all refused.
- **`pool.<name>.hireable`** (published, printed in the report): `(gil >= price, when priced)
  AND not sold out`, refreshed by the ticker every run pass (after the activation blocks, so
  the tick that sells a pool out flips it the same pass; Main_Init presets it optimistic).
  Wire it into a hire row's `requires_flag` and the row VANISHES instead of saying
  "Deployed!" to a hire the activation block would refuse — the recorded fort-condor polish
  debt, closed. One parked menu may now serve SEVERAL pools (each row its own
  `set_flag`/`requires_flag`; only the `button` pool needs the menu match).
- First composed consumer: `studies/fort-condor/condor_fit_bench.py` (rung 5 — field 30400
  rebuilt as THE FORT CONDOR FIT on the owner-ratified design). En route, two bench-layout
  laws earned their keep: anchors snap to the spawn's CONNECTED COMPONENT of the tri-neighbor
  graph (same-floor pockets can be disconnected sheets — the route planner rightly refuses
  them) with a ~120u wall-clearance filter, and the v1 central ticker has a REAL capacity
  ceiling (~32KB — relative jumps are signed-16), which caps per-ally target lists; a
  long-jump relaxation pass in `labelasm` is the queued fix.

### Added — LONG-JUMP RELAXATION in the label assembler (the ~32KB body ceiling, removed)
- `.eb` signed jumps (0x01 JMP / 0x03 JMP_IF) reach ±32767, so any assembled body past
  ~32KB used to die in `struct.pack` — a hard ceiling on how much behavior one ticker could
  hold (the fort-condor rung-5 capacity finding). `labelasm.asm()` now RELAXES: an
  out-of-range jump re-routes through an inserted ISLAND (`JMP skip; island: JMP target;
  skip:` — 6 bytes, jumped over by fall-through, safe at any block boundary), placed at the
  nearest legal boundary strictly BETWEEN source and target (the progress guarantee) and
  iterated to a fixpoint; spans beyond two hops chain naturally. Invariants pinned by 11
  tests: a body with no out-of-range jump assembles BYTE-IDENTICAL (golden stability), a
  decoder-walk FOLLOWS every chain to its true target, no island ever splits an expression
  statement from the conditional consuming it, and a 30-unit 40KB+ behavior compiles
  deterministic and structurally sound. `JMP_IFNOT` (unsigned forward, 64K reach) keeps its
  backward-refusal.
- **The next wall is now LOUD:** the `.eb` entry table is u16-addressed (whole-file reach
  ≈ 64KB, engine-fixed) and `binutils.set_u16` used to MASK — an oversized file registered a
  silently-wrapped entry offset (garbage function tags, no error at the write site; caught
  post-hoc by lint in the condor round-3 build). `set_u16` is now STRICT (raises with the
  file-budget explanation) and `append_entry` pre-checks both offset and entry size. The
  practical consequence, measured on the condor bench: relaxation frees the BODY, but a
  donor fork's TOTAL behavior budget is ~50-55KB of compiled bodies — the roster/target
  cross-product is now a file-budget decision, not a jump-span accident.

### Added — `[behavior]` `hold_ground` (THE PIN)
- `do = { hold_ground = true }`: a dispatch action whose SELECTION halts the duty walk (the
  dispatch-halt clause) and whose body just idles while the branch holds — a marcher gated on
  `any_near(interceptors)` stands and takes the fight instead of jogging away from its
  attackers, and resumes the march at its current waypoint when it shakes free. Minted from
  the condor round-1 playtest ("the Mu run right to the depot instead of engaging soldiers");
  the raiders' full COUNTER-damage remains blocked on the ticker's ~32KB jump ceiling.

### Fixed — THE MONOTONIC-ONCE STARVATION: `once` over an `announce` is an EVENT, not an engagement
- BTTABLE round 2 (the data-table bench): the herald's win line — `once` + `announce` gated on
  `counter_ge ["kills", 2]` — fired correctly, then **held the selection for the rest of the
  match** and silently starved the wave-three line below it. Sticky `Once` (the rung-1 design,
  correct for feeds: "chase me while I'm near, never again once I escape") disengages when its
  child's conditions go false — but announce conditions are usually **monotonic** (a kill tally,
  a spent wave counter, `time_below`) and never go false again. Any mid-match one-shot line above
  other branches would hit this; branch reordering can't fix two monotonic onces.
- Now `Once` whose branch ends in an `Announce` compiles as **fire-and-release**: selection
  edge-latches a request flag; the one-shot request lane (the same machinery as `battle`'s
  clobber fix — a one-tick selection can be eaten by a body still holding the dispatch level)
  fires the window when the level frees; the dispatch body sets the Once latch FIRST (a
  re-request can never re-fire) and returns without an idle loop — the async window persists on
  its own, and the branch releases the next tick. Sticky semantics are UNCHANGED for movement
  behaviors, and a bare (un-`once`d) `announce` keeps its idle-while-selected spam guard.
  An `Announce` object shared between a `once` site and a bare site is refused at compile.
  3 new tests (the starvation shape structurally, the sticky-feed control, the shared-site
  negative). Docs: BEHAVIOR.md § Alarms, FORMAT.md.

### Added — `[behavior]` DATA TABLES: gScriptVector arrays, counters, and the schedule clock
- **`[[behavior.table]]`** (`name` / `values` 1..64 ±26-bit ints / optional `id`): named int
  arrays in the save's `gScriptVector`, written through the engine's 0xD3 VECTOR lane the
  `exprasm` entry-fee unlock made emittable — **the first consumer of `.eb` computed array
  indexing anywhere**. Every table (and every counter) **re-seeds at each field entry**:
  the Main_Init seed forces size→0 then size→n (the engine zero-fills a grow, so all-zero
  cells cost nothing and a redeploy can never leave a stale tail in the save), then writes
  only non-zero cells. Auto ids allocate from 1000 per field; save-global aliasing is
  harmless by the re-seed.
- **`counters = [...]`** (runtime cells, one internal table) + condition verbs
  **`counter_ge`/`counter_le`/`counter_eq`** and **`table_ge`/`table_le`/`table_eq`** —
  the table verbs' `index` may be a **counter name**, compiling a genuinely
  runtime-computed lookup (`sched[wave]` — nested VECTOR reads compose; the engine keys
  sub-operands by CalcStack depth). **`die = "<counter>"`** bumps a cell exactly once
  (the death body runs once — edge-safe for free).
- **`[[behavior.schedule]]`** (`counter` + `table`, needs `timer =`): THE WAVE CLOCK —
  `counter += 1` while the countdown HUD sits below `table[counter]`, one generic engine
  replacing N unrolled `time_below` bands, and the schedule is DATA (a rebalance edits the
  table, not the trees). Self-terminating by construction: the counter walking off the
  table's end reads 0 (engine fail-soft) and `timer < 0` never holds — no latch flag.
- Python surface: `TableSpec`, `FieldBehavior(tables=, counters=)`, `schedule()`,
  `counter_*`/`table_*` Cond builders, `Die(count=)`. Full validate coverage (unknown
  names, index bounds, 26-bit domain, duplicate ids, schedule-without-timer). Bench:
  field 30415 `studies/behavior-trees/bttable_bench.py` — dormant waves woken by the
  clock, a kill tally, and the OOB terminator, all announced live.
  Docs: [BEHAVIOR.md § Data tables](docs/BEHAVIOR.md), [FORMAT.md](docs/FORMAT.md).

### Added — `behavior lint` sweeps the DYNAMIC feeds too: the pursuit sweep for `chase`/`wander`
- `route = "auto"` refuses `chase`/`wander` because a runtime target has no build-time leg to
  splice — so lint now checks what *is* knowable: the **family** of pursuit lines the branch's own
  engagement gate admits. `scene.routes.sweep_pursuit` tests every pair of *occupiable* positions
  inside the compiler's Chebyshev `near` box (excluding pairs already inside the `standoff`, where
  the pursuer holds ground, and truncating each leg at the standoff ring) and reports the blocked
  fraction plus spatially distinct worst-case pairs as coordinates. New
  `behaviortoml.pursuit_refs` reads each chase's binding radius from the **tightest** `near` /
  `any_near` row that names its target (branch rows are ANDed), turns a `near_point` row into a
  source-box restriction, and models a `wander` as its own box spanning twice the radius; a chase
  with no row bounding its target is reported as **UNGATED** (family = the whole field).
- **WARNINGS, never errors** — a dynamic jam needs the quarry to stand on a bad spot, unlike a
  static route's off-mesh leg, which jams every lap; the hint points at the two real fixes
  (tighten the `near` radius, or `march route = "auto"` the approach and chase from close range).
  Calibration from the Path-B study: 0% of sub-600u pursuit lines jam on the benches' donut field,
  so the check is naturally quiet on sane layouts. Across the four benches that carry a
  `[behavior]` table: silent on `BTROUTE` (patrol-only, no dynamic feed), 5.1% on the raid bench's
  900u guard chase, 3.4%/2.0% on the pool bench, and the swarm bench's 40 ungated chases are
  reported as UNGATED. (`BTREE`/`BTWAR` predate the TOML surface and have no table to lint.)
- **Honest coverage:** the raster/leg **grain** is fixed at the collision radius and never scales
  with the radius, only the sampled endpoint spacing does — and both are printed, so a sampled
  sweep can never read as exhaustive (the reported rate is a floor, not a ceiling). Two false-clean
  bugs found and fixed by the new tests while building it: sizing the sampling off an ungated
  radius rather than off the floor that exists drove a ~4000u endpoint grid on a 1600u mesh, and
  selecting endpoints by `gi % stride == 0` (a modulus on absolute grid indices) matched no cell at
  all — each reported "0 pairs tested" as clean. Sources are now chosen by **bucketing**, and every
  sizing decision is clamped to the occupiable extent. 16 new tests
  (`test_behavior_pursuit.py`). Docs: [BEHAVIOR.md § Movement](docs/BEHAVIOR.md).
  Rationale + the measurements: `studies/behavior-trees/PLAN.md § PATH B`.

### Added — `[behavior]` static-feed auto-routing: `route = "auto"` on `patrol`/`march`
- **`route = "auto"`** on a `patrol`/`march` verb re-routes any leg the walkability sweep finds
  OFF-MESH through the walkmesh A* (`content.pathfind.route_polyline`, the same pathfinder
  cutscene walks use) and splices the detour waypoints in at build time — the concave-notch
  wedge `behavior lint` could only *diagnose* is now *fixed* by the build. **Opt-in and
  conservative:** a field without the key never resolves a walkmesh (byte-identical builds,
  guarded by test), and within an opted-in route clear legs stay exactly as authored. `patrol`
  routes its wrap leg too (it always cycles); routing avoids **walls only** (other units move —
  build-time character obstacles would be stale guesses; the docs say so); the spliced total
  must fit the verb's 8-point ceiling or the build fails naming the field/unit/branch/leg.
  `walk_to`/`hold`/`flee` are refused with an explanation — their legs have no build-time
  origin (and spliced flee points would become extra refuges), that's the dynamic-routing
  problem, deliberately out of scope here.
- **`behavior lint` stays truthful:** an auto-routed patrol/march is swept on its ROUTED line
  (what the build compiles) and each detoured leg is reported as `routed:`, not as a jam; a jam
  on a *non*-routed patrol/march now prints a `route = "auto"` hint. Lint sweeps also became
  verb-aware: a `patrol` is swept CLOSED regardless of the marker's `closed` flag (the compiler
  always cycles the wrap leg — previously a wrap-leg jam on an open marker went unswept), a
  `march` open, and inline point lists are now swept too (previously only markers were).
  `behavior compile`/`view` and the build report the same auto-routed-leg lines
  (`describe_autoroute`), and `build_script` errors cleanly when `route = "auto"` has no
  resolvable walkmesh. New shared resolver `build.behavior_walkmesh` keeps what lint checks ==
  what the build compiles. 10 new tests (`test_behavior_autoroute.py`: detour-splice + re-sweep
  clean + determinism, clear-leg byte identity, wrap-leg routing, ceiling error text,
  off-mesh-waypoint/disconnected-floor refusals, TOML negatives, built-`.eb` byte identity).
  Docs: [BEHAVIOR.md § Movement](docs/BEHAVIOR.md), `FORMAT.md § [behavior]`.

### Added — `[behavior]` pooled units: runtime activation ("hire a soldier at your feet")
- **`pooled = true` / `pool = "name"` on a `[[behavior.unit]]`**: the unit's NPC is seated
  DORMANT at boot (no spawn, no reveal flag — `inject_npc` gains `boot_spawn=False`) and joins a
  named pool. Each pool allocates a **spawn-request flag** (printed at build + `behavior
  compile`); a `[[choice]]` row's `set_flag = [<index>, 1]` makes the next never-spawned unit
  **materialize at the player's feet**, the press-time position becoming its *placement post*.
  The activation block rides the compiled ticker and is the fort-condor rung-3 in-game-proven
  byte shape verbatim: runtime `InitObject` → 2-frame settle → `MoveInstantEx` (the new
  `opcodes.move_instant_ex`, DPOS 0xBF) to the captured post, mirrors seeded before the unit's
  first tree tick (law-clean: no object read precedes its spawn). One spawn per request;
  exhausted pools consume silently; a dead pooled unit stays consumed; reload refills.
- **New action verb `hold_post = true`** (valid unconditional fallback): hold MY placement
  post — with chase/swing branches this is the **placement defender** (the Fort Condor unit).
  On a boot-spawned unit the post is its own spawn.
- Fields with no pooled units and no `hold_post` compile **byte-identical** to before (guarded
  by test). 8 new tests across `test_behavior.py`/`test_behavior_toml.py` (activation-lane
  instruction walks, allocation hygiene, TOML negatives, a built-`.eb` e2e proving the pooled
  entry has no boot `InitObject`). Bench: `studies/behavior-trees/btpool_bench.py` → field
  30413. Docs: [BEHAVIOR.md § Pooled units](docs/BEHAVIOR.md), `FORMAT.md § [behavior]`.

### Added — `.eb` expressions: COMPUTED ARRAY INDEXING (the 0xD3 `flexible_varfunc` lane)
- **`exprasm` can now emit — and every kit expression walker correctly decode — Memoria's
  `0xD3` expression sub-command** (the Path-B study's dividend: stock-Memoria script arrays,
  in the pinned engine base since 2023). New tokens: **`B_VECTOR`** (`<id> <idx> B_VECTOR` —
  reads `gScriptVector[id][idx]`, and as an LVALUE writes it via `B_LET`: index == size
  APPENDS, a missing id at index 0 CREATES, all fail-soft), **`B_VECTOR_SIZE`**,
  **`B_DICTIONARY`**, plus the generic **`flex(id,argc)`** for every other
  `flexible_varfunc` (arity rides the wire — no arity table to trust). Both stores are
  **save-serialized** (JsonParser) — persistent per-save arrays, writable and readable
  entirely from field bytecode: data tables, wave schedules, per-unit params.
- **A latent decoder desync fixed with it**: `0xD3 >= 0xC0`, so all four kit expression
  walkers (`read_expr` / `pretty_expr` / the uid- and const-offset walkers) previously
  parsed it as a 1-byte-operand variable token — 2 bytes of desync per occurrence on any
  field using the Memoria extension. All four now carve it out (engine-faithful: `EBin.expr`
  checks `0xD3` before var decoding). 3 new test groups incl. the walker-desync guard;
  `assemble()`'s round-trip self-verification covers the new tokens by construction.
  Offline-verified; the first in-game consumer (e.g. condor rung-5 wave/cost tables) is the
  natural live proof.

### Added — `[behavior]` waves + win/loss: the countdown clock and REAL battles
- **`timer = <seconds>`** (field-level): starts FF9's own countdown HUD on field entry —
  the Festival of the Hunt's exact start triplet (`ChangeTimerTime`/`ShowTimer`/`RunTimer`,
  in-game proven on a custom id); `~ → Reload` resets the clock. Two condition verbs read
  it: **`time_below` / `time_above`** (remaining seconds) — gate march branches on
  descending bands for TIMED WAVES (the Hunt's `GetTimerTime` scheduling shape).
- **`battle = <scene id>`** action verb: fire a REAL battle — `Battle(0, scene)`, the
  donor-grounded shape (559's tread battles; the engine owns the swirl). **One-shot per
  field load by construction**: a compiled latch gates the dispatch so the reactive tree
  can't re-fire it after the return. The build auto-installs the **entry-0 tag-10
  Main_Reinit** (the after-battle resume law) + the field-BGM resume whenever a behavior
  compiles a battle — no `[encounter]` block needed; a stock scene id needs no BattlePatch.
- Together with pooled units + the hire economy this completes the Fort Condor core loop:
  bench 30400 = THE SIEGE (3:00 clock, two waves × two lanes with `route = "auto"`
  marches, the herald as the hp'd GATE, breach → 559's own boss battle, survive → the
  win cry). 5 new tests (incl. a built-`.eb` e2e asserting the tag-10 installs); suite
  green.

### Added — `[behavior]` pool ECONOMY: price + the buy-anywhere hire button
- **`[[behavior.pool]]`** rows configure a pool: `price` compiles a gil gate
  (`B_SYSVAR[6] >= price`, the inn-553 idiom) into the activation block with `RemoveGil` at
  the SPAWN site — a broke or pool-empty request is consumed **without charging**; works for
  every request source (button, NPC-talk menu, walk-in zone). `button = true` (or a PSX
  button-mask int; default Special|Select) seats a **buy-anywhere POLLER** entry — the
  fort-condor rung-3 in-game-proven shape verbatim: a Wait(1) `B_KEYON` poll (debounce only
  after a menu round), the Hunt's announce blip, then `RunScriptSync(4, <menu>, 3)` opening a
  **parked zone [[choice]]** (zone far off-mesh; its Hire row `set_flag`s the pool's
  `request_flag`, which `button` requires explicit and outside the blackboard band — the
  build matches menu→pool by that flag). 5 new tests; suite 4868. Bench: 30400 (the
  fort-condor placement/economy rebuild — 4 recruits @300 gil, mutual attacker↔recruit
  combat via plain branches).

### Fixed — `[behavior]` staged latch: the New-Game entry NullRef (playtest-caught)
- **Every compiled behavior's staged latch now requires proof the player object is BOUND**, not
  just `B_SYSVAR[2]` (usercontrol): on the New-Game auto-warp entry path usercontrol is set
  before `DefinePlayerCharacter` runs, so the first ticker pass deref'd `obj(250)` on a null
  object → `NullReferenceException` → CalcStack desync → the whole behavior system dead for the
  session (bench-30413 playtest + Memoria.log). `install()` now inserts a `player.bound`
  flag-set immediately after every `DefinePlayerCharacter` (0x2C) in a tag-0 Init (the
  `insert_in_function` docstring's own blessed pattern) and the latch is
  `(bound AND usercontrol) OR latched`; an `.eb` with no 0x2C anywhere is refused (obj(250)
  could never be safe). Flag allocation shifts by one for ALL compiled behaviors — re-run any
  bench `gen` so `[[choice]]` `set_flag` indices re-bind. Benches 30410–30412/30400 remain
  deployed on the old latch (safe via ~ Warp entry); they pick the fix up on their next redeploy.

### Added — `[[summon]]`: transplant your own model onto a stock summon's real cast *(experimental)*
- **The productized custom-summon kit surface** (Milestone 2 of the summon-transplant arc —
  `studies/custom-summons/thomas-swap/m2/DESIGN.md`, the binding module plan): a declarative
  `field.toml` block for wearing a stock FF9 summon's real per-frame bones, native camera, and
  damage timing with a user's own retargeted model, in place of the donor creature. Two lanes:
  **hybrid** (default — the s58 `SfxHybridDrive` engine feature poses the model from the donor's
  live bones; requires the custom `memoria-patches` engine build) and **overlay** (DLL-free —
  baked `.anim` clips + authored or donor-nested staging, the rung-7 FileList/`.sfxmodel` route).
  Emits assets + a printed engine-arm manifest, never `.eb` bytecode; the cast trigger pairs with
  the existing ability `vfx1` lane (`battle/actiondelta.py:64`), unchanged.
  **New `content/summon.py`** — the block-schema layer: resolves a `donor` SpecialEffect *name* to
  its numeric id, enforces the field-schema requirements, and is registered into `ff9mapkit
  build`/`lint` (unknown-key/lane/donor/`private_ef` checks + a `vfx1` cast-trigger reminder); it
  delegates all structural normalization to `summons/deploy.py` rather than duplicating it.
  **New `summons/deploy.py`** — the deploy/arm engine: the mint via `models/mint.py`, the private
  stock-absent sequence host + host-`.seq` splice, `.anim` clips via
  `models/anim.py:clip_to_anim_json`, the overlay `.sfxmodel`/`FileList.txt`, and the `[SfxHybrid]`
  ini writer following `coop.py`'s `[Netsync]` pattern exactly (including the engine-string-probe
  gate that refuses to arm the hybrid lane on a stock engine); every deploy writes a self-contained
  `revert_summon_<id>.py`. **New CLI verbs `summon-import`** (the Blender return trip — a `.glb` or
  `.fbx` in, validated + staged) **and `summon-deploy`** (standalone asset deploy + the explicit,
  confirm-first `--arm` step) join the already-shipped `summon-export`/`summon-rig-ref`. Docs:
  [`docs/SUMMONS.md`](docs/SUMMONS.md), [tutorial 11](docs/tutorials/11-summon-transplant.md),
  [`FORMAT.md` — `[[summon]]`](docs/FORMAT.md#summon-optional-repeatable). Native read/fork
  (`summon-inspect`/`summon-fork`) stays a separate, out-of-scope surface. 70 new tests
  (`test_summon_block.py`/`test_summon_deploy.py` ×2/`test_summons_build.py`), pure-logic + an
  install-gated byte-identity acceptance against the live M1b deployment (skips cleanly without an
  install). Grounded in the in-game-proven hand-built pipeline (Milestone 1b, 2026-07-24 — a
  skinned model flying live on a stock dragon's real 93-bone motion,
  `studies/custom-summons/thomas-swap/m1b/RUNBOOK.md`); this productized surface is itself not yet
  independently cast in-game.
### Added — `[behavior]`: behavior TREES compiled to field bytecode (NPC AI as content)
- **`[behavior]` + `[[behavior.unit]]`** on any novel/native/editable field: give named `[[npc]]`s
  priority-ordered AI branches — patrols with shift clocks (`alternators`), notice-and-chase
  (`near`/`any_near`), MUTUAL combat with HP and deaths (`swing_at`/`die`), flee-at-low-HP with
  priority refuges (`flee`), alarms (`raise_flags`), random wandering (`wander`), multi-leg
  marches (`march`), sticky `once`/`cooldown` decorators, per-action `speed=` that applies
  mid-walk — all compiled to pure `.eb` (zero DLL, stock-Memoria-safe) and installed by the
  normal `build`. Docs: `docs/BEHAVIOR.md` + the FORMAT.md section.
- **`ff9mapkit behavior compile|lint|view`**: dry-compile report (the blackboard map doubles as
  the debug menu's live trace; public-flag indices for `[[choice]]` lever wiring), static checks
  plus walkability SWEEPS of referenced route markers, and a full disassembly of the generated
  bodies.
- **Route markers**: a `[[marker]]` may carry `path = [[x,z], ...]` (+ `closed = true`) — the
  polyline a scripted walker travels. `tools/field_layout_probe.py` draws and sweeps them
  (off-mesh legs = a walker that jams, named with world coordinates), `behavior lint` runs the
  same sweep (shared core: `ff9mapkit.scene.routes`), and `patrol`/`march` verbs reference them
  by name — the route you verified is the route they walk. The probe also stops flagging
  OFF-CANVAS content on scrolling fields (the viewport pans).

### Added — synthesis recipes in the Info Hub item detail (+ fork-report labels synthesists)
- **`itemstats` joins the base `Synthesis.csv`** (live from your install, cached, nothing committed —
  the same provenance stance as the stat join): an item's Info Hub detail now shows **synthesize**
  ("Dagger + MageMasher @ 300 gil (synth shops 32, 33, 34, 35, 38)") and **synth ingredient of**
  (Ore → all eight gems + TinArmor). New `synthesis_of` / `synthesis_uses` / `recipe_desc` API;
  degrades to nothing offline.
- **fork-report** now tells a donor's shops apart: an id absent from `ShopItems.csv` opens as
  SYNTHESIS (`ff9buy.FF9Buy_GetType`) — "opens SYNTHESIS shop(s) #38" + the recipes-caveat, and
  `--explain` says "a synthesis shop".

### Added — `[[synthesis_edit]]`: retune or remove a VANILLA synthesis recipe
- **`[[synthesis_edit]] recipe = "Butterfly Sword"`** (or the recipe's integer Id) + any of
  `price` / `ingredients` (full replacement, dups matter) / `result` / `shops` (which synthesists
  list it, 32..255) — or **`remove = true`** to unlist it from every shop. The engine merges
  `Synthesis.csv` by id whole-row, so the kit re-emits the base row with only the edited cells
  changed; removal ships an **empty `Shops` cell** (`Int32Array("")` → `[]`; `ShopUI` only shows
  rows whose `Shops` contains the open shop's id). Selector checked against the install's base
  file at lint when reachable (unknown/ambiguous flagged); edits to one recipe coalesce across
  blocks (later wins per key, warned). Same footing as `[[synthesis]]`: mod-global CSV delta,
  RELAUNCH to apply, needs a reachable install at build.

### Changed — journey/campaign opens ~2x faster (the tomlcache seam)
- **`tomlcache.load_toml`** — an mtime+size-keyed TOML parse cache at ONE seam: `campaign.load_campaign`,
  `lint_campaign`'s member reads, and the Workspace flag-name annotator. A journey open was parsing
  ~1850 tomls for ~890 distinct files (lint + overview + flag names each re-reading the same members);
  repeats are now cheap private copies — every caller gets its OWN tree (lint's in-place flag-name
  resolution can't poison the cache), an on-disk edit always re-parses (F5/build honesty), and
  parse/IO errors propagate uncached. Bench (73-campaign arc, warm): open 1.18s → 0.79s, re-open
  1.2s → 0.5s. `lint_campaign` also resolves the campaign dir once per lint instead of per member
  (`_within(base_resolved=)` — `Path.resolve()` is syscall-priced on Windows).

### Added — THE MOGNET DONOR-FORK LANE (★ in-game proven): patch a real moogle field in place
- **`tools/mognet_donor_patch.py` + `content/mognetdonor.py`** — the 42nd moogle becomes a full
  network citizen at a REAL donor field, generated from your own install at deploy time (nothing
  SE-derived is shipped; all 7 languages; revert script emitted). Three faces, all proven on
  Kupo/field 1865: the **42nd roster row** (a stock field renders "from Kupo to Mogwai"), **letter
  content** for our variants (guarded arms spliced at ALL FOUR of the donor's letter switches —
  read-mail display + delivery announce/display/thanks, the per-letter txid triplet), and the
  **inbound give** (the donor offers a letter to our moogle inside its own Mognet flow, anchored
  after the migration guard's `Byte[1024] := 1` — the universal donor invariant).
- **Jump-table-aware `edit.insert_in_function`** — the enabling primitive: straddling jumps and
  0x06/0x0B jump tables are now FIXED on insert (crossing targets grow; a target exactly at the
  insert point flows into the fragment — the convergence-splice donor patches ride on).
- **`[savepoint.mognet]` fidelity pass** (the donor playtests' laws): Mognet is a SUBMENU — the
  moogle's menu reopens after every Mognet exit; the no-mail line is FF9's own invariant bubble
  "I want mail!  Kupo!" spoken by the moogle (the 2nd documented game-text exception,
  `docs/PROVENANCE.md`) and closes every visit including the submenu's Cancel; the letter
  header-body separator is the stock two blank lines.

### Added — the visible `[[platform]]` model (★ in-game proven) + the block documented
- **`[[platform]]` gains `prop`/`model` (+ `model_offset`, `model_pos`)** — a visible platform that
  rides with the player in lockstep: the model gets its own walk-through, walkmesh-detached object
  entry whose loop pins it to the player's live position (the 0x78 obj-var read) while a per-platform
  MAP ride-bit (`Bit[328..331]`, a new reserved band) is held by the ride function. No duration math,
  any easing, and one model serves a bidirectional zone pair — it rests wherever the last ride left
  it. Without a model every ride body is byte-identical to before (test-pinned). ★ In-game proven
  (a cask lift riding up under the player, then the `warp_to` fade tail).
- **`[[platform]]` is now documented in FORMAT.md** (it never was — v1's whole zone/land/rise/entry/
  warp_to surface plus the new model keys, and the engine visibility law: keep visible rides short,
  do big floor changes with `warp_to`, fork Pandemonium `--verbatim` for a tall faithful elevator).

### Added — from-scratch navigable jumps (`[[jump]] to =`): the copy-only gap closed (★ in-game proven)
- **`content/jump.py jump_arc_body(to, via=, steps=)`** generates FF9's real ledge-hop arc from just the
  landing point(s) — no verbatim sidecar needed. Grounded in a full-game census (51 navigable hops over
  15 fields): the Ice Cavern hop template is the game-wide modal shape, and the generator reproduces
  **all 6 of field 301's real arcs byte-for-byte** from their coords (single- and two-hop). Per hop:
  turn + wait-turn + jump anim + leap sfx (1324) + `SetupJump`/`Jump` + landing sfx (2342) + land anim;
  the engine arcs from the player's current position, so no take-off point is authored.
- **`[[jump]]` gains `to = [x, z(, y)]`** (the generated lane; `y` = the landing floor's height),
  `via = [[...]]` (intermediate landings — a multi-hop crossing like the real two-hop Ice Cavern gaps),
  `steps` (frames per hop, default 11 = the census mode; scalar or per-hop list), and `sfx = false`.
  `jump = "<file>"` stays the faithful verbatim lane; exactly one of the two is required (lint-enforced).
  Closes `FORK_FIDELITY.md`'s "jumps are copy-only" note (the save-Moogle pop-out remains, same class).

### Added — the orphan-decal gate (`world-transplant` / `transplant_region`): a third carry-time census
- **`world/orphangate.py` productizes the comp[1] fringe arc's proven rule set** (Round 10 of
  `studies/overworld-topography/GROUND-FAMILY-DECODE-2026-07-19.md`, in-game proven across 3 redress
  rounds / 15 cells on the deployed comp[1] region, 2026-07-22): a transition-vocabulary tri
  (`grassland.STRIPS` — today `('grass','desert')` or `('desert','dunes')`, any row, any orientation) is an
  **orphan** unless its neighbourhood context justifies wearing it — straddle rows (1/3) need a genuine
  same-cell straddle of the pair's two families; fringe rows (0/2) need the partner family within the
  calibrated accept radius (2 cells; the observed curvature bound is 4) — plus a second, independent
  **topo-consistency** check (a `(pair,row)` fringe group's topo is measured LIVE; a tri breaking an
  overwhelming majority is a topo/UV mismatch even with lawful context nearby — this axis is what a
  colour-band filter alone cannot see, and what let a misassigned tile slip past one).
- **Follows `wang_carry_gate`'s exact shape**: WARN by default (`ok` stays `True`, a `warn` flag surfaces
  the finding + names the cells/missing-context/remedy), `--enforce-orphan-decals` hard-fails,
  `--allow-orphan-decals` waives even then. In WARN mode (the default) the gate is **purely read-only** —
  it never mutates a byte of any mesh it inspects, so wiring it into `transplant()`/`transplant_region()`
  changes **zero** output bytes of any existing mint/carry/retile path.
- **`--redress-orphans`** auto-fixes every finding to the wearing side's plain `grassland.GROUNDS` mains —
  the arc's own proven FIX-G shape (`assign_mains` → `ground_uv`, the SAME per-cell call the shipped
  `GroundRetile` "recovered" path already uses): UV always, topo only when the tri still carries the
  STRIPS decal's own dedicated fringe topo (not yet the family's own plain-mains topo); vertex positions,
  normals and tangent[1:] are never touched. Applied **in memory, at build time, before any write** — never
  touches an already-deployed file — then the census re-runs over the mutated meshes so a fully successful
  auto-fix makes even an enforced build clean. Opt-in: changes output bytes vs. a plain carry.
- **Scope**: hooked into `transplant()`/`transplant_region()` only — `world-island`/`world-mountain`/
  `world-forest` never touch the STRIPS vocabulary at all (confirmed by grep), and `morph_in_place` has no
  donor mapping, matching both precedent gates' own scope boundary. Validated against real deployed bytes:
  the current comp[1] region censuses zero orphans (already hand-redressed), and the PRE-redress backup
  bytes (`backups/comp1-redress.20260722-140044/`) reproduce the real historical defects — including the
  exact Round-3 topo/UV mismatch at cell (305,−299) — with `--redress-orphans` fixing every one.
  `world/fuse.fuse_layout` reaches `transplant_region()` without a dedicated top-level orphan-decal
  parameter of its own — a placement dict may still set one, but absent that it stays WARN-only by
  default (safe: WARN mode never mutates a byte).

### Fixed — the orphan-decal gate now reads a RING of real context, and never guesses on an overlap
- **RULE-FIDELITY fix (2026-07-22) vs `--census3` (`comp1_orphan_redress.round3_generalized_census`)**:
  the gate's Class-A fringe-row radius search and Class-B topo-consistency group statistics were
  scoped to the just-carried region alone — the study's own instrument always reads a 1-block Moore
  RING of real bordering terrain (deployed override where one exists, else stock) alongside the
  carried core for both checks. `orphan_decal_gate` now takes an injectable `context_provider`
  (default `default_context_provider`, read-only, deployed-override-else-stock) and feeds ring
  records into both checks exactly as the study does — a thin local topo group that needed a larger
  sample to see its own minority member, and a lawful edge-fringe decal whose partner family sits
  just outside the carry, are both handled correctly now. Read-only; changes zero output bytes on
  the default (WARN, no `--redress-orphans`) path.
- **AMBIGUOUS verdict**: a cell Class A and Class B independently claim (the study's own
  `round3_build_and_gate` hard-refuses/asserts on this shape) is now its own `klass="AMBIGUOUS"`
  verdict rather than being silently folded into whichever class happened to be inserted first — it
  still counts toward `n_orphans`/`warn`/fails an enforced build, but `--redress-orphans` refuses to
  auto-fix it (never guess on an unmodelled state). Surfaced as `n_ambiguous`/`ambiguous_cells` on
  the gate result.

### Fixed — a stale atlas cache can no longer shadow the atlas the game renders
- **`world/atlas.load_atlas` now returns the atlas the ENGINE renders by default.** Previously an existing
  `StreamingAssets/.ff9atlas_*.png` extract cache always won — so on an HD-modded install (Moguri) every
  texture-judging instrument built on `load_atlas` could silently measure the VANILLA 1024×1024 atlas while
  the game rendered Moguri's HD one (terrain 2048×4096 — not square; UVs are normalized so any dims render).
  New `resolve_atlas_source(part)` mirrors `AssetManager.SearchAssetOnDisc` for
  `WorldMap/Textures/res(1_24)_<part>.png` exactly: the `Memoria.ini [Mod] FolderNames` stack high→low, then
  the game root, probing `StreamingAssets/Assets/Resources/...` before a `FF9_Data/...` fallback sweep,
  honoring a mod folder's `ModFileList.txt` loose-entry gate (MoguriMain ships one). A loose override is read
  directly and never cached; the extract cache only ever serves the BUNDLE and is keyed to its source
  `p0data*.bin` (size+mtime) via a `.src.json` sidecar — a sidecar-less cache is never trusted, and the
  legacy artifact is deleted once a loose override is what renders. `load_atlas(source="bundle")` /
  `world-atlas-extract --source bundle` keep the vanilla atlas reachable (the extract CLI now reports the
  resolved source + real dimensions).

### Added — Workspace FIELD card picker (region-divided)
- **A region-divided card view over FF9's ~818 real fields** (`workspace/fieldcards.py`
  `FieldCardPicker`): every field as a card of its actual pre-rendered background, with a region list
  (Prima Vista, A. Castle, Alexandria, … — derived from the fields' place names, ordered by first
  field id ≈ story order) dividing the catalog, plus search by place/room/id/FBG name. Opened from the
  Import tab (**Cards…** beside Find…) and from the realfield picker (**Card view…**) — the pick fills
  the fork-source box. Art rides the SHARED field thumbnail service (the same composites the campaign
  Map shows, so caches are shared both ways), requested only for the cards in view; a machine without
  the install degrades to labeled cards.

### Added — Workspace model CARD picker + no-geometry filter; preview caching pass
- **A card-grid model picker** (`workspace/modelcards.py` `ModelCardPicker`): browse the ~2000-model GEO
  catalog as big thumbnail CARDS (search + group / field-only filters, double-click to pick). Opened from
  the Models tab (**Cards…**) — picking selects that model in the tab — and from any form's catalog
  picker on the `model` kind (**Card view…**), answering the form field directly. Renders are requested
  **only for the cards in view** (scroll-driven, debounced), so opening it never floods the render queue.
- **"Hide models with no geometry"** — a new toggle on both the Models tab (opt-in) and the card picker
  (default on) drops the ids the render worker has PROBED as unshipped (PSX-era catalog leftovers; the
  `absent` sidecars, now scanned by `thumbcache.absent_ids()`). The count label reports how many rows are
  hidden, and the set grows live as previews render (`ModelThumbService.missed`). A fresh cache honestly
  hides nothing.
- **Preview caching/performance**: both thumbnail services now answer from the WARM DISK CACHE on the
  GUI thread (one stat) instead of re-queuing every previously-rendered thumb through the worker each
  session — field art shows instantly on campaign open and model list icons on first fill; the Models
  list also memoizes decoded row icons (a search keystroke used to re-load every cached PNG from disk)
  and skips render requests for known no-geometry ids.

### Added — `world-island` OPT-IN rolling relief (THE DEAD-RELIEF RESURRECTION)
- **`world-island --relief` adds gentle inland undulation to minted islands** — the resurrection of the
  ambient relief field RETIRED 2026-07-15 (THE DEAD-RELIEF DISCOVERY: the first `relief_field` keyed a
  donor block's LOCAL 4u lattice while `fill_y` sampled it with WORLD coords, so it read 0.0 everywhere
  off block (0,0)). The rebuild is **not** a re-key of that single-block snapshot (which was also
  non-tileable) — it is a **deterministic WORLD-XZ VALUE-NOISE field** (`grassland.relief(x, z, seed,
  amp)` + `relief_fade`): 2 octaves (base period 20u + detail 10u), default amp 1.3, scaled per ground
  family by `GROUNDS[..]["relief_scale"]` (grass 1.0, desert 1.6). Because it is a PURE function of world
  (x, z), the frame bug **cannot recur** (same world point → same height) and cross-block seams **weld by
  construction** (a block-local field would crack them). **Opt-in — default OFF ⇒ byte-identity**
  (`relief_amp=0` returns `land_height` unchanged; all 17 world-island oracle blocks re-mint
  hash-identical, the same no-op the retire proved). CLI: `--relief` / `--relief-amp N` (default 1.3) /
  `--relief-seed N` (default from the centre). The rim-weld short-circuit the retire dropped is
  **restored** (rim vertices → exactly `land_height`) plus a smoothstep FADE (fade 2→12u ≈ one
  wavelength) so the wall-top ring never moves. New `verify_landmass` **slope-envelope gate**
  (`main_slope_p99 ≤ 28.6` = the measured lowland-grass ceiling; bites an over-amplitude mint, vacuous for
  flat). Calibrated on stock lowland (detrended grass std ~0.5, slope p99 ~15-33, wavelength ~20u); the
  field measures std 0.58 / slope p99 11 / max 15 deg (>2.4× walkability margin), position-independent.
  Relief is mutually exclusive with `world-hill`/`world-forest`/`world-mountain` per island (the 2.4u
  ROLLING-RELIEF ENVELOPE gate is the backstop). Tests: 7 new in `tests/test_world_island.py`
  (world-XZ purity/position-independence, seed decorrelation, fade-to-zero at shore, relief-off
  byte-identity, in-envelope gates-clean, over-amplitude refusal, cross-border weld). Study record +
  offline eye: `studies/overworld-topography/README.md` §THE ROLLING-RELIEF RESURRECTION, `relief_eye.py`.

### Added — overworld grid-bounds gate (the 24×20 block grid)
- **`world-island` / `build_landmass` and the loose-mesh deploy layer now refuse an OFF-GRID target.**
  The engine's world is a fixed **24×20** block grid (`WMWorld.BuildBlockArray = new WMBlock[24, 20]`;
  cols 0..23, rows 0..19; world x 0..1535, z 0..−1279). A landmass whose footprint spills off it streams
  nothing — the overrides are dead files — and the OPEN-OCEAN TARGET check was **vacuously satisfied off
  the map edge** (no mesh assets because there is no map), so nothing caught a dunes-field mint that landed
  on rows 20–22 until the user's debug-menu teleport bounced. New single source of truth
  `mesh.GRID_COLS/GRID_ROWS = 24, 20` + `mesh.block_in_grid` / `mesh.require_block_in_grid` (cited to
  `WMWorld.cs:1675` and the debug-menu bounds `Ff9mkDebugMenu.cs:1595`); `terrain.py`/`water.py`/
  `transplant.py` re-export `GRID_X/GRID_Y` from it. `build_landmass` refuses before building a `BlockMesh`
  (naming every off-grid block); `mesh.deploy_override` / `deploy_donor_sidecar` refuse before touching the
  filesystem (belt-and-braces for any direct-deploy path). Tests: `tests/test_world_grid_bounds.py`.

### Added — battle locations: `encounters` verb + `battle.locate` (scene↔place census, monster names)
- **`ff9mapkit encounters`** answers "what battles are in Evil Forest" and "where does a Goblin appear"
  — the join FF9 never ships: each field's own `.eb` names its battle scenes (`SetRandomBattles` /
  `Battle`/`BattleEx`, decoded by the existing `eventscan`), joined to `region_catalog.toml`'s 73
  story-visit arcs and to each scene's real enemy display names. No args = a per-place summary +
  coverage totals; a query auto-detects a place, monster, or `BSC_` scene name/id (`--monster`/`--place`
  force an axis, `--scene` prints one scene's places + monster/attack names, `--unresolved` prints the
  honest gap report, `--lang` picks the name language). Distinct from `scenes` (bare id/name catalog)
  and `world-encounters` (overworld terrain table only).
- **`ff9mapkit.battle.locate`** — the read-live engine underneath: an ~6s census over all 818 real
  fields (zero computed operands in the whole corpus; scene id 0 is a real scene), honest per-scene
  classification (`placed` 284 / `model-bucket` 176 / `overworld` 274 / `unplaced` 122 of 856), and a
  bulk monster-name extractor that resolves battle text through `mainData`'s ResourceManager container
  path (battle and field `.mes` share bare numeric names inside `resources.assets` — name-matching
  returns the wrong text) in ONE pass instead of per-scene 590MB reloads. Cached under the gitignored
  `provision.cache_dir()/battlemap/` (cold ~9s, warm ~0.006s; `--force` rebuilds); extracted content is
  never committed as repo data.
- **`battle-scene <donor>`** now prints each enemy type's real display name and a "found in:
  <place> (field N, kind)" line. **InfoHub** scene entries show BSC name, classification, enemies, and
  place; the Workspace detail pane wires it lazily via a new `scene_usage_fn` hook (separate from the
  model `usage_fn` — the two id spaces collide numerically).
- A new `engine` block reports whether Memoria is installed, whether the Dream World IX patches were
  applied (detected via the `dwix-engine-backups/` dirs our installer leaves), and — when they weren't —
  which pillars already work unmodified (novel fields, models, battle, audio, playable characters) versus
  which need the bundle (forked real fields, the `world-*` overworld commands). No bundle zip required.
- The installed engine's compile date is decoded from its FileVersion alone (`AssemblyVersion("1.1.*")`
  fills the build field with days since 2000-01-01); a drift of more than ~180 days from the pinned base
  adds a note that the prebuilt bundle may not be a clean match and to build from `memoria-patches/`
  instead. Advisory only — nothing here affects `doctor`'s exit code.

### Added — overworld sea-carry gates (`world-transplant` / `transplant_region`)
- **The effective-prefab gate + auto-arm** — the s34 sea→land divert binds a cell's sub-mesh overrides
  only for the transforms its *effective* prefab exposes, looked up by `transform.name`: an un-armed
  ocean cell loads the generic `SeaBlockPrefab` whose only transform is **`Sea4`**, so every other emitted
  layer (Sea3/Sea5/Beach1…) is silently dropped (holes + a pale/black void — the (11,19) bug). A
  water-only carry that emits more than one sea layer now **auto-arms** the divert with a degenerate,
  never-bound `Terrain` stub (`mesh.stub_terrain_mesh`: one zero-area tri, `tangent.x = 4078` = the
  placement IDALL-skip, byte-identical to the in-game-proven (11,19) fix) plus the `Donor.txt` sidecar, so
  each layer binds its own material. The stub is provably harmless — a water-only donor prefab has no
  `TerrainForm1`, so `LoadBlock`'s `if (prefab.TerrainForm1)` branch never binds it — and idempotent (a
  cell already shipping a Terrain override is left byte-unchanged). `auto_mirror` needs no change: because
  `terrain` joins the overridden set, the Disc4 free-ride pin computes no extras. The gate still **fails**
  a carry that emits a layer the armed donor prefab cannot bind.
- **The Wang-carry gate** — a post-carry, land-aware marching-band edge census of the carried cells' outer
  frame: a shallow/transition tile abutting the open-ocean deep ring with no transition ring is a cropped-
  Wang seam (the 17 rim seams the (8,17)+2×2 island carry introduced). The predicate is **sound** — a
  map-wide census of shipping FF9 finds **zero** sea3-directly-abuts-sea4 edges across any block border
  (all 194 shallow→deep transitions are sea5-mediated; `studies/overworld-topography/wang_seam_census.py`),
  so a flagged edge is a real seam. **Report-only by default, but now WARNS visibly** — `world-transplant`
  prints a `!! WARNING wang-carry: N cropped-Wang frame seam(s)…` line (no longer a bare `-> ok`) pointing
  to the re-tile / `--enforce-wang-carry` / `--allow-wang-seams`. It does *not* refuse by default because
  carrying **any** coastal island standalone necessarily crops the neighbour blocks that hosted its sea5
  transition rings, so a real coastal donor (e.g. (7,17) alone → 16 flagged edges) legitimately produces
  frame seams, fixed by a human-reviewed post-carry re-tile (the shallow-rim look at the exact carry is the
  user's visual call, Hard-Constraint S2). A **donor-baseline subtraction does not enable a safe hard-fail
  default**: with zero pre-existing sea3-abuts-deep edges anywhere, there is nothing to subtract — every
  flagged sea3 frame edge is crop-introduced, so the subtraction collapses to the raw count and would
  refuse every coastal carry (empirically the donor-outward-deep baseline calls 15/16 of the proven (7,17)
  carry "introduced"). `--enforce-wang-carry` hard-fails on any incoherent frame edge (a fresh mint onto
  known-deep open ocean, or a post-retile CI check); `--allow-wang-seams` waives even then. Both gates are
  byte-neutral over every already-deployed lawful carry.
- **The Wang-carry gate learns the coastal shades (Sea1/Sea2).** The gate's shade grid binned only the
  *deep* Sea3/4/5 alphabet, so a **Sea1/Sea2** frame tile read as deep and was never flagged — the exact
  class the `{sea1,sea5}` ladder had to close by hand on the deployed island (2 sea1|sea4 sand-spit corner
  tiles at (12,18)). The gate now bins the coastal shades too (`_sea_shallow_grid`) and flags a Sea1/Sea2
  frame tile facing the deep ring, because stock authors `sea1|sea4` and `sea2|sea4` **zero** times map-wide
  (`studies/overworld-topography/s12_stock_map_census_opus.py`, land-aware, interior + cross-block): a sea1
  tile's *deepest* lawful neighbour is sea5, a sea2 tile's is sea3 (the ring ladder
  `sea4>sea5>sea3>sea1>sea2>beach1>land`), so neither ever faces the deep ring. The lawful set is
  byte-derived, never invented — `transplant.SEA_ADJ_LAWFUL` / `sea_adjacent_lawful()`, with the measured
  stock counts cited per pair (sea1|sea3 588, sea2|sea1 517/488, sea1|sea5 78, sea2|sea3 9, shore contacts
  sea1|beach1 78 / sea2|beach1 465; off-language sea1|sea4 0, sea2|sea4 0, sea2|sea5 0). The report gains
  **additive** keys — `incoherent_deep` (sea3/mis-sea5, byte-identical to the old count) + `incoherent_shallow`
  (sea1/sea2) — and the two systems are mutually exclusive per edge, so the deep verdicts never reclassify.
  The lone interior donor-verbatim `sea2|sea4` tile at (12,19) is an interior edge the frame census never
  sees, so it never false-positives. Public behaviour is unchanged: warn-by-default, `--enforce-wang-carry`
  refuses, `--allow-wang-seams` waives. A fresh `world-transplant --size 2 --donor 8,17` now warns about
  **both** crop classes at carry time (12 deep + 5 shallow), so the sand-spit corner is caught before deploy
  instead of after a playtest.

### Changed — the in-game debug menu: functionality round
- **Three tabs** (Go / Cheats / Flags): Time merged into Cheats as a "Time scale" section. The Go tab's
  "More options" hide-toggle is gone — the entrance/scenario fields are one always-visible row. New
  **Recent fields** chips (the last 6 fields you were on or warped to, session-scoped) under Favorites —
  the everyday 2-3-field bounce no longer needs pins or typing. The screen-blanking "Break control
  (test)" button is removed (the s39 self-heal it validated is long proven). One type step up across the
  whole menu (15px controls on 32px rows, 20px title) with brighter secondary text and full-color
  section headers.

### Changed — the in-game debug menu hotkey is now `~` (tilde/backquote), was F6
- Stock Memoria binds **F6 to its LvMax cheat** (F1–F9 are all cheat/booster keys), and the menu's
  early intercept swallowed it; BackQuote is bound to nothing engine-wide. Engine patch
  `s43-debug-menu-ux-tilde` (rides the next engine-bundle rebuild). Because tilde types a character,
  the toggle is suppressed while a menu text box is focused. Same round: a menu UX pass — one prefs
  row, per-tab scroll reset, boxed status bar, bolder section titles, brighter readouts, the battle
  diorama bench moved below the everyday Go actions, an in-menu "~ toggles" hint, and the Flags batch
  "bad index" error now prints the op grammar. Docs and tool output say `~` throughout; historical
  release notes and studies keep F6 as a record.

## [1.0.0b17] - 2026-07-19 — The moogle letter network, experimental co-op, and living overworld terrain

### Fixed — THE VANILLA SQUAT: custom dialogue was overwriting real locations' text
- A field's dialogue is keyed by mesID in one flat global namespace shared with the BASE GAME, and
  `FF9TextTool` merges every source per-txid with the base game applied first — so custom text on a REAL
  block overwrote that location's own dialogue, needing no stacked mod folder at all. The kit default
  **1073 is Black Mage Village**; the World Hub's 8 is Ice Cavern; 22 is Lindblum Castle. The old cure for
  the cross-folder shadow ("pick a real MesDB id no higher folder defines") is what caused it: all 64 real
  blocks are owned. `text_block` now defaults to the field's **own id** and emits its own
  `MessageFile` registration; forks keep their donor's block (voice-acting and the dual-language remap key
  off it). Identity, not an offset band — mesID *consumption* is Int16, so `40000+id` wraps and loads zero
  text.
- The collision guard now reports that axis too (it called all three live corruptions CLEAR), and suggests
  free custom ids instead of real in-use blocks. Per-language sweep; fork exemption scoped to the donor's
  own block; wired into the journey single-folder and hub installs, which had no text check at all.
- `deploy_field` carries the `MessageFile` line into the live `DictionaryPatch.txt`, before the `FieldScene`
  line — it rebuilds that file from parts rather than copying the dist's, so the registration was dropped
  and the field black-screened (`DataPatchers` skips a scene whose mesID fails the `MesDB` gate).
- `ff9mapkit import` passes the donor's block through; it previously emitted 1073 for every fork.

### Fixed — the 2026-07 adversarial-review pass: 47 defects across the whole kit
- A package-wide adversarial review (24 subsystem reviewers, every finding independently
  refuted-or-confirmed) confirmed 48 defects; 47 are fixed here (1 was informational).
  The worst, most severe first: `bgi.rebuild_neighbors` refuses a non-manifold walkmesh edge
  (3+ triangles on one edge — previously silently mislinked neighbors into a corrupt shipped
  `.bgi`); `deploy-campaign` restores the pre-install snapshot when the wholesale folder
  replace fails partway (previously a half-installed live folder with no revert script); a
  journey whose `entry.campaign` names a non-member campaign is a clean `JourneyError` at all
  three consumption sites (previously a raw `KeyError` from lint itself); a `[[platform]]`
  `land=` carry guards the zero-span interpolation at runtime (previously a divide-by-zero
  fling whenever the boarding floor's height equals the landing height); and
  `insert_in_function`'s jump-straddle safety check reads `JMP_IFNOT` UNSIGNED like the engine
  (a `raw>=0x8000` straddle previously slipped through and silently corrupted the `.eb`).
- Atomicity + backup discipline, kit-wide: the new shared `fsutil.atomic_write_bytes/text`
  (sibling `.tmp` + `os.replace`) now backs every load-bearing writer — the save container
  (`FF9Save.write`), `Memoria.ini` (both coop writers, and `ensure_folder_registered` now
  takes the same timestamped backup `write_netsync` always did), `DictionaryPatch.txt`
  (model mint/anim/strip), the form editor's `field.toml` save, engine-DLL installs, and the
  sound manifest (which is also only written AFTER a successful OGG encode). Save backups are
  collision-proof within the same second everywhere (`save_items`, `save.apply_story_edit`,
  and the `save-edit --in-place` CLI backup all probe for a free name instead of truncating
  an existing backup).
- The rest, briefly: `eventscan` no longer crashes on computed InitObject/STARTSEQ operands
  (skips what it can't prove, like its sibling guards); the scene.toml merge no longer drops
  unnamed content items; a malformed `CAMERA` line is a hard parse error, not a silent
  default camera; a field revert can no longer claim another mod's same-numbered `3DModel`
  registration; the top-level `--game`/`--mod-folder` survive every subcommand that
  redeclares them (`argparse.SUPPRESS` sweep — `world-encounters --config` consequently
  inherits the standard `FF9CustomMap` default rather than demanding its own flag);
  `world-deploy` refuses `--lift/--spike` composed with a reshape instead of silently
  dropping the reshape; `[startup] words` accepts its full documented UInt16 range
  (`region`'s `GLOB_UINT16` consts now pack unsigned); a `[[chest]]` `gil` above 65535 is a
  build-time refusal (the popup's engine text slot is 2 bytes — an honest error beats a
  wrapped number); duplicate-INDEX `[[flag]]`s and same-name-different-content custom
  statuses are build errors; `requires_flag` + `requires_flag_clear` together is rejected on
  every block type (not just `[[choice]]`/`[[cutscene]]`); the editor preserves cutscene
  `actor`/`with_prev` on step updates and escapes all control characters in emitted TOML
  strings; `[journey.tuning]` entries the tuning dialog can't represent are preserved with a
  visible warning instead of silently deleted; plus HiDPI campaign-map thumbnails, the
  Workspace logic-map cache made content-aware (stale on the very first edit before), the
  `blob_cliff_block_mesh` winding fix now applied to the serialized index buffer, `read_clip`
  through the O(1) anim index, an LRU bound on the mod-bundle cache, deploy tempdir cleanup,
  IPv6 relay-host bracket handling, weapon-model mints deferred until the whole item pass
  validates, and `arc_id_base` doing a real interval-overlap check against the reserved
  9000–9012 world band.

### Added — `--diorama on|off`: the battle diorama's config surface (s40 engine)
- The s40 engine's `[Netsync] Diorama` knob (default ON: a following guest's screen boots the
  host's battles live, render-only) joins the established play-style surface: `coop host|join
  --diorama on|off` (written only when given, like every play-style flag), a `coop show` line
  (an absent key reads as the engine default ON), and a Workspace Co-op tab checkbox that greys
  out when the installed DLL predates s40 (`NetSyncDiorama` scan) so the key is never written
  for an engine that can't read it.

### Added — THE BEACH TRANSLATION LAW: the desert sand band (family-keyed beach verbs)
- The desert-beach study (2026-07-15, `studies/overworld-topography/desert_beach_*.py`)
  measured stock desert beaches (14 Outer-Continent blocks; 112 map-wide sand↔topo-17 back
  welds): the topo-32 desert sand band is the grass band's structure at its own atlas spot —
  the u-strip shifted exactly +335/1024 texels (P/Q split preserved) with its own
  single-valued v pins (run 548→579, cap 580→611; the ribbon is 2 texels taller), foam
  universal, and the sand topo family-keyed 1:1 with the backing ground (zero mixed blocks).
  `coastmorph.SAND_BANDS` + per-donor auto-detection now run every sand-band verb
  (`beach_mint`/`virgin_mint`/`sand_rebuild`/`cap_rebuild`/`beach_slide`/`beach_reshape`)
  on either family; grass is byte-frozen through the refactor (the 44 golden tests are the
  proof) and the desert side is proven against every real desert beach block (decode 82%
  vs grass 73%; identity rebuilds green). topo 33 = the Lost Continent's foam-less frozen
  shore (+330 texels) — measured, not yet mintable.

### Fixed — `morph_in_place` silently dropped emissions into parts the cell doesn't carry
- An in-place morph on a real cell whose prefab lacks a part's transform (e.g. minting a
  beach on a never-beached block: no Beach1 to bind an override to) used to skip the part
  entirely — INCLUDING tweak emissions into it — while the tweak gates still read clean, so
  a deploy could ship a beach with no foam/wash. It now refuses actionably, naming the part
  and the eaten tri count.

### Added — five more ground families: THE TRANSLATION LAW IS UNIVERSAL
- The ground-families census (`studies/overworld-topography/ground_families_anatomy.py`,
  2026-07-15) ran the desert method over every remaining stock walkable ground: each one is the
  grass mains 2×2 translated in the atlas, outer-bound byte-exact at 5dp (the grass control
  recovers delta (0,0) with zero spread; dirt topo-19/20 recover the desert constants exactly —
  the "in-family ids are gameplay variants" model byte-proven). `grassland.GROUNDS` (and so
  `world-island --ground` / `world-mountain --ground`) grew: **scrub** (topo 4, the grass↔dirt
  ecotone set), **brush** (topo 38 — whose stock cliff wall is measurably the DESERT wall),
  **snow** (topo 27, with its own measured icy wall band), **canyon** (topo 45, red-rock wall
  band), **dunes** (topo 41 — its own pale-sand set, the one family-model exception). Scrub and
  dunes never coast in stock and borrow the desert wall. Grass and desert stay byte-identical
  (both frozen identity acceptances pass unchanged); constants pinned in
  `test_ground_families_registry`.
- The ground-sampler playtest (five one-block islets, one per family) added a stock-role CLASS
  per family (`GROUNDS[..]["cls"]`): grass/desert/snow/canyon are **island**-class (snow
  sampler-proven; canyon pending a verbatim compare); **scrub** is a *transition* seam set (a
  filled field shows raw tiling mismatches — stock only lays it as narrow grass↔dirt strips),
  **brush** a *slope* set (flat fills read as brush canopy), **dunes** an *interior* fill
  (no native coast). `world-island` prints a note when minting a non-island-class ground.

### Removed — `world-island`: the ambient rolling-relief field (THE DEAD-RELIEF DISCOVERY)
- The desert tile fidelity check (2026-07-15) found `relief="auto"` had NEVER applied: the field
  keyed its lattice on the donor block's LOCAL 4u nodes (around world block (0,0)) while the mint
  sampled it with WORLD coordinates — 0.0 everywhere in practice, so every island ever minted is
  flat. Flat interiors are repeatedly in-game approved (up to an r52 pure-plain desert island:
  "this looks like a fine desert"), so the dead plumbing is RETIRED rather than fixed:
  `grassland.relief_field`/`relief_at` and `build_landmass(relief=...)` are removed, `--flat` now
  means only "skip the verbatim meadow stamps", and docs state the interior is flat at `--height`
  by design (explicit height = `world-hill`/`world-forest`/`world-mountain`). **Byte-identity
  preserved:** removing a `+0.0` changes no floats — a post-change re-mint of the r52 desert
  island reproduces the deployed files byte-for-byte. Resurrection notes for continent-scale
  plains (per-ground measured relief + the frame fix) live in
  `studies/overworld-topography/README.md` (THE DESERT TILE FIDELITY CHECK).

### Fixed — `world-island`: a concave corner dent could ship a one-triangle grass hole
- In-game confirmed (2026-07-13, `--center 160,-1246 --radius 31 --seed 42`): Block[2][19] shipped
  with one grass face MISSING at the rim — a dark sliver through the grass, a closed 3-cycle of
  once-edges at world (143–144, y 3.2, z −1262..−1265). Root cause: the grass triangulation is an
  UNCONSTRAINED Delaunay — at a concave corner dent it may legally pick the other diagonal of the
  quad spanning the notch, so the rim ring edge (the wall-top weld line) is not a triangulation
  edge at all; the centroid keep-filter then drops both cover triangles and the face between the
  wall top and the grass is emitted by nobody. `build_landmass` now runs constrained ring-edge
  RECOVERY (Sloan-style diagonal flips) after the Delaunay; a 60-seed sweep found the same latent
  defect in 2 more seeds (34, 37 — multi-flip cascades included), all clean after recovery.
- **Byte-identity preserved for proven mints:** with zero flips the triangulation is returned
  untouched — the island E baseline (seed 55, the world-forest/world-hill identity proof) needs
  zero flips and re-passes the full mint→forest→hill zero-byte-diff acceptance against the
  deployed, in-game-proven files.
- New CLOSED-SURFACE GATE in `verify_landmass` (and thus the deploy refusal): a position-welded
  once-edge may lie only on the y=0 sea-skirt ring (where the wall base meets the separate Sea4
  plane); `open_edges` / `missing_faces` (once-edge 3-cycles) join the report and `clean`. The old
  30×30 sampled-holes gate could never see a sub-sample-spacing missing face. (Rounded-degenerate
  edge keys are skipped: the border clip lawfully mints ~0.0005u hairline cut-vert pairs.)

### Added — `world-entrance --nameplate-name`: a custom-named native overworld entrance (AREA-switch surgery)
- `world-entrance --field-direct <id> --nameplate-name "Waystation"` authors a custom overworld entrance that
  runs the game's **real native flow**, so its approach nameplate shows a genuine **custom location name** (+ the
  native "Enter with [X]" dialog). It repoints a **dead** AREA-switch case → a tiny appended handler `[set the
  location's explored bit] + Field(<id>)`, writes the **stock** dispatcher trigger to that case, and registers the
  name — the entrance is indistinguishable from a real town's, so none of the self-timing failure modes apply.
- The mechanism, pinned over the investigation: the approach nameplate name is **world text block 68** txid-0
  `split[case]` (`SetTextVariable(0, Byte[24])` + a `[TEXT=0,0]` tag → `GetTableText(0)[Byte[24]]`), **not**
  `worldLocationText` (that feeds the in-menu header). The kit's `world.navimap` writes block 68; a location reads
  "?" until its known bit (`gEventGlobal[92/94/96/98]`, per case range) is set — the handler sets it on entry, so
  the plate faithfully shows "?" until first visit, then the name. The default case is 53 (a placeholder slot with
  no live map-marker side effect).
- New generic tooling: `eb.edit.repoint_switch_case` / `find_switch` / `switch_case_reloff_pos` — a contiguous
  (0x0B/0x0D) switch-arm repoint that appends a handler and rewrites one 2-byte reloffset, refuses a live (mapped)
  case, and asserts round-trip identity. Round-trip byte-exact across all 9 free-roam dispatchers × 7 languages.
  (The earlier self-summon `--action-prompt --nameplate` path is superseded — kept as a flag.)

### Fixed — `world-entrance` worldmap EXIT fades out before the transition (was a hard cut)
- Leaving a field back to the overworld hard-cut instead of fading. The kit carries only the SHARED exit
  cascade SUFFIX (routing + the WorldMap arms); each real exit field's fade lives in its per-field HEAD,
  which the extraction drops. `worldmap_exit_body` now prepends `exit_fade()` = `DisableMove` +
  `FadeFilter(6,24,white)` + `Wait(25)` (matching field 2800's real exit head, the same mode-6 fade the
  choice/gateway warps use) before the arrive/key writes. Default on (`fade=True`); byte-asserted test.

### Added — `world-entrance --action-prompt`: the faithful "!" confirm-to-enter entrance
- Correcting an earlier wrong claim: **stock FF9 overworld town/dungeon entry is CONFIRM-gated, not
  walk-on.** The real dispatcher's fade→`Field()` block is guarded by `B_KEYON(Confirm)` (the
  `0x20000` button mask) — you stand on the tile and press Confirm to enter. (The "walk-on"
  reading was a mis-decode: the RPN operator `0x4F` is `B_KEYON`, a controller read, not a field
  opcode.) Our `--field-direct` trigger warped immediately on walk-on, skipping that gate.
- `world-entrance --field-direct <id> --action-prompt` now builds the faithful entrance: the tile
  trigger (which the engine re-fires every frame you stand on it) raises the `FICON` "!" bubble and
  warps only on a Confirm press — the `B_KEYON(Confirm)` test byte-copied from the real dispatcher
  gate. Default (no flag) stays auto-warp (fine for scripted/cutscene entrances). Pairs with
  `--trigger-only` to retrofit an already-authored entrance.

### Fixed — `world-entrance --field-direct` now performs the real zone-in (fade + arrival sentinel)
- The direct trigger used to warp `Field(N)` bare, bypassing the choreography the real
  `Byte[39]`+`RunScriptAsync` handshake reaches in the dispatcher's main loop — so a custom
  destination loaded IN THE CLEAR: no fade-to-black, the smooth-cam settle fully visible (in-game
  report on the waystation entrance), and the destination read a STALE last-gateway `D8:2`. The
  trigger body now carries the real run, byte-identical to WORLD00's own (donor-oracle test):
  `DisableMove/DisableMenu` + window cleanup + the two PSX worldcodes (Memoria stubs, carried for
  fidelity) + `FadeFilter` to black (24 frames) + `Wait(25)` + `D8:2 = 9999` (the worldmap-arrival
  entrance sentinel) + the ready poll, then `Field(N)`.
- New `world-entrance --trigger-only`: re-deploy just the dispatcher trigger funcs (deployed
  terrain / event tiles / building untouched) — the refresh mode for picking up a trigger-body
  kit upgrade on an already-authored entrance (a full re-run without the original `--building`
  would re-stamp event tiles without the building-hull exclusion).

### Added — `entry_settle = "auto"`: the computed entry black-hold (field-entry rung 7)
- `[camera] entry_settle = "auto"` now COMPUTES the frames held black on entry instead of
  hand-copying "the hub precedent" (45). The estimator (`content.entry_settle`) replicates the
  engine's smooth-cam exactly (Memoria `FieldMap.cs`): the camera's target is the player-aim's
  clamped GTE screen position (aim = spawn + `charAimHeight` 324, the `.bgx` Viewport clamp), it
  rests at the bare projection offset until the player binds, and it eases geometrically by
  `CameraStabilizer/100` per frame — so the hold = bind delay + `ln(delta/0.25px) / −ln(0.85)`,
  rounded up to a multiple of 5 and clamped to 20–90. Calibrated against the in-game-proven holds
  (hub 45/60, waystation 45; 90 read as over-long): all three compute 45–50. A sub-pixel delta
  returns 0 (nothing to hide — byte-identical build); an offline-unresolvable camera falls back
  to the proven 45 with a warning. Best-effort: `CameraStabilizer` is per-user (baked for the
  default 85).
- The chosen value is surfaced in the build output and by `lint` (which also now treats `"auto"`
  as legal, reports what it resolves to, and counts it in the multicam-disagreement check).
- `"auto"` is accepted everywhere the key lives: the `[hub]` generator (emitted quoted), the
  Workspace Camera panel (type `auto` in the entry-settle box), and `fork-report` now suggests
  `entry_settle = "auto"` for scrolling synth forks. The bundled waystation example switched to
  it (computes 50; shipped 45 before).

### Added — battle co-op + visitor mode reach the CLI and the Workspace Co-op tab
- `ff9mapkit coop host|join` grows the s37 play-style flags, each written to `[Netsync]` only when
  given (re-runs never clobber hand tuning): `--guest-slots` (which of YOUR party slots the other
  player commands in battle — human party positions 1-4, `'2,3'`, `'all'`, `'none'`),
  `--guest-wait` (seconds a guest turn may freeze the ATB gauges; 0 = no cap), `--ghost-as`
  (visitor mode: dress their ghost as `auto`/a playable name/`off`), and `--follow-host on|off`
  (guest side: auto-warp to the host's field + own-encounter pause). Unknown outfit names and bad
  slot specs refuse up front — before the room build — instead of silently un-dressing in-engine.
- New `ff9mapkit coop show`: the current `[Netsync]` config printed in human terms (read-only,
  safe with the game running).
- The Workspace **Co-op** tab gains a **Play style** panel mirroring the same four knobs (slot
  checkboxes, wait-cap spinner, outfit picker, follow-host toggle) with its own **Apply** button —
  the engine hot-reloads `[Netsync]`, so changes land in a running game, mid-session, in a couple
  of seconds. The panel reads its state from Memoria.ini on refresh, feeds Start co-op, and greys
  out with a pointer when the engine predates s37 (detection: `NetSyncBattle` in the DLL).

### Added — `world-mirror`: custom overworld land now survives disc 4
- THE DISC-4 GAP (found in-game: "the island no longer exists when I switch to Disc 4"): the
  overworld ships exactly TWO asset trees — `worldmap/disc1` (serving discs 1–3) and
  `worldmap/disc4` (its own art; only `WorldDisc1`/`WorldDisc4` prefabs exist) — and every s34
  lookup (override files, `Donor.txt` sidecars, the reclaim fallback prefab) keys on the engine's
  `currentDisc`. Anything deployed only under `Disc1/` vanishes once the scenario (or the F6 disc
  switch) crosses the disc-4 threshold.
- `world-mirror --mod-folder M` copies every Block override + sidecar into the `Disc4` tree,
  gated per cell (the destination's real cell must be open ocean or byte-identical across discs —
  an `--in-place` edit of a block that differs, e.g. (9,17), skips with a warning), and PINS a
  sidecar cell's un-overridden donor-prefab free-ride parts (falls/rivers/objects) as explicit
  source-disc-byte overrides — the disc-4 Daguerreo donors genuinely differ, so without the pin
  the mirrored island would wear disc-4 variants on disc-1 terrain. Run it after any
  custom-ocean world deploy; RELAUNCH to apply.

### Added — `--ground desert`: a second walkable ground family (THE TRANSLATION LAWS)
- The desert anatomy (`studies/overworld-topography/desert_ground_anatomy.py`) proved topo-17
  wasteland speaks the grass ground grammar — exact linear-in-XZ per 4u cell, one 128px tile
  per cell, 4 rotations, grass handedness, avoid-repeat neighbours — with its mains 2×2 rects
  and its coastal cliff-wall band each sitting at a TRANSLATED atlas spot, byte-exact at 5dp:
  mains (+0.65332, −0.09863), wall (−0.27127, −0.02066). `grassland.GROUNDS` records the
  families; `ground_uv`/`ground_main_region` re-base the proven grass machinery.
- `world-island --ground desert` mints a topo-17 desert island (desert mains + the desert
  cliff band; meadow stamps are grass vocabulary and disable); `world-mountain --ground
  desert` makes the carve's plain-ground checks, zip annulus (UVs + topograph), and rim
  probes speak the bench's family. Grass is the bit-frozen identity: both byte-identity
  acceptances (the Uaho bench AND island E) pass unchanged through the threading, and the
  full desert path runs green offline end-to-end (desert mint → verify → the crag carve).

### Added — `world-mountain`: carry a real rock massif onto a deployed island
- The in-game-approved Uaho carry study (`massif_carry.py`, 2026-07-13 — "the cliff is great —
  walkable, seams against the grass great") is now a kit verb (`interior.carve_mountain`):
  * `world-mountain --mod-folder M --near WX,WZ` (or `--center` exact, rotation 0) carries the
    donor block's REAL massif whole — the largest topo-49/7/62 rock component + enclosed raised
    tris + the donor-conditional alcove floor + the Object-mesh APERTURE PLUGS wearing the rock
    collar's own affine UV chart (small mountains are terrain+object ensembles; `--donor`
    defaults to `0,0` = Uaho, the only donor with an anatomy study behind it).
  * THE ROCK-RIGID LAW: carried rock never deforms beyond the de-tilt affine + the vertical
    anchor; ALL seating deformation goes to the grass as a weld-safe per-POSITION pure-Y apron
    lift (worldmap meshes don't share vertex entries — a one-sided lift splits the weld). Hole
    carve + a minimal-total-chord DP zip + an apron normal re-smooth close the seam; the
    placement scan (exact 90° rotations as fallbacks) keeps the whole band inside ONE block.
  * Gates: rim/aperture accounting, baseline-subtracted once-edges, ROCK-RIGID drift < 3.5%,
    zip rise/winding envelope, apron slope ≤ 29.5°, rock/grass placement probes, the
    Moguri-atlas alpha gate (when installed), and the census.
  * THE DONOR-DISPATCH STRIP: a carried IDALL keeps its topograph + flags but drops the donor's
    event/area bits — dispatch CONTEXT that is meaningless and hazardous on a custom island
    (Uaho's massif is baked area=63, which `w_cameraArea2Place[63]` maps to place bucket 2 =
    cameraDistance 6000, the alcove camera zoom-out; five alcove-floor tiles even carry event=1,
    a latent PLACE-ENTRANCE trigger into the world `.eb`). Verified surgical on the bench:
    re-carve vs the prior approved bytes differs in exactly the 149 carried tris' tangent.x and
    nothing else.
- Acceptance was proven by IDENTITY (`mountain_productize_check.py`): the pristine bench mint →
  module carve reproduces the deployed, playtested Uaho bench byte-for-byte (the scan converges
  on the study's exact placement, (162,-1246) rot 0); the go-forward fresh-mint path differs
  only by the mint's own concave-dent fix (24 tris at the two dents, far outside the carve).
- THE ENSEMBLE CARRY: a water-bearing massif's aperture (the river/falls MOUTH — its ring is
  owned by the UNION of the donor's Object/Falls/River/RiverJoint parts, not the Object part
  alone) now classifies as an ENSEMBLE aperture, and the parts ride the carry: every aux
  component inside the massif footprint transforms under the same rigid map (real tangents as
  sheared directions, UVs verbatim — the animated water materials bind by part name) into
  per-block part overrides, deployed with BLANKS for uncarried parts on every span block plus
  a `Donor.txt` divert to a part-carrying donor block. Gate evolution (each Uaho-frozen, both
  byte-identity acceptances pass): segment-proximity exemption for lawful open rings, the edge
  gate on synthetic zip only, a ≤2-tri zip bank allowance in [0.5, 0.83), the carried-peak
  placement probe (a horseshoe's bbox centre is its open mouth), and apron-wide span widening
  with a per-position taper. `world-island` gains adaptive outline density past r60 + a
  conditional >8u interior refinement (no-ops on every existing radius) for horseshoe-scale
  benches. Proven offline end-to-end on the Daguerreo horseshoe — 713 terrain + 122 aux tris
  over a 10-block span, census MISS=0.
- MULTI-BLOCK carries: `--donor` also takes a block rect (`10,5-6` = the crag island's stock
  massif, which straddles a border — the blob builds on the merged world-frame donor bytes),
  and the TARGET sizes itself automatically: a blob that fits one block runs the proven
  single-block pipeline byte-identically, a bigger one works over the minimal SPAN of deployed
  blocks covering its footprint — new tris split at the 64u borders (`split_borders8`, identity
  welds), the weld-safe apron lift welds internal borders per POSITION and tapers only at the
  span's OUTER borders, and the crack/census gates run across the whole span. Proven offline by
  the crag carry (294 tris across a 2×2 span, every gate green; the Uaho identity acceptance
  still passes bit-for-bit through the generalization).

### Added — `world-forest` + `world-hill`: interior topography on a deployed island
- The two in-game-proven island-E studies are now kit verbs (`ff9mapkit/world/interior.py`), operating
  on the DEPLOYED override bytes of a kit island (never a real block — that is `world-terrain`'s job):
  * `world-forest --mod-folder M --near WX,WZ` (or `--center` exact) carries a REAL canopy blob
    (verbatim topo-37 verts/UVs/normals from `--donor`, default `15,15`) — lattice hole carve, zip
    annulus with per-cell byte-DECODED mains UVs, the comprehensive canopy STEP-LAW rim lift, and a
    perimeter walk-in simulation of the engine climb rule as the deploy gate.
  * `world-hill --near WX,WZ [--height 4.2 --radius 18]` raises a raised-cosine grass hill by pure-Y
    displacement inside the measured grass-language envelope (flank p99 ≤ 28.6°, lowland peak cap,
    local normal re-smooth); the placement scan refuses footprints outside the rolling-relief
    envelope (no stacking on prior displacement).
- Acceptance was proven by IDENTITY: clean seed-55 mint → module forest carve → module hill
  reproduces the deployed, playtested island E byte-for-byte on all 5 blocks — and the CLI verbs'
  own `--near` scans, run end-to-end on a scratch copy, converge on the studies' exact placements
  and reproduce the same bytes.

### Fixed — the placement simulator's walking ray had a phantom drop limit
- Engine-truth correction (source-verified 2026-07-12): `ff9.rayDistance` (2.8) is passed into
  `WMBlock.Raycast` but the parameter is never read — dead code. A walking step can therefore descend
  ANY height (that is how canopies and ledges are exitable); only the climb ceiling (`y + 2.34375`)
  exists. `world/placement.py::place()` dropped its unfaithful `max_drop` window and the module doc +
  tests state the corrected spec. Found while root-causing a forest-canopy stuck report on the
  grass-island canvas: the effective climb is surface-to-surface across one foot step (~0.44u/frame),
  so an un-hittable vertical wall face samples the dome BEYOND it — the wall jump plus one step of
  interior slope, not the face rise alone.

### Added — `world-island` now enforces the open-ocean target law
- The transplant path's OPEN-OCEAN TARGET gate is ported into `world-island`: every footprint block
  must be TRUE open ocean (no real per-block mesh assets), or the whole deploy refuses naming the
  offending blocks and their parts. Root cause (found in-game 2026-07-12, the archipelago canvas):
  a real sea-only block loads its OWN prefab, which has no `Terrain` transform for the s34 loose
  override to bind to — the island fragment silently never renders (one block of the landmass
  missing, water in its place); on a real land block the island would replace real continent
  geometry. No escape hatch — unlike transplants there is no legitimate use.

### Fixed — Memoria.ini mod-order edits now survive the Launcher (FolderNames + Priorities together)
- Root cause (2026-07-12): the Memoria **Launcher** treats `[Mod] Priorities` as the MASTER mod order —
  `LoadModSettings` builds its list in Priorities order and `UpdateModSettings` rewrites `FolderNames`
  from it at every Play click — so any tool (or hand edit) touching only `FolderNames` was silently
  reverted. New `coop.mod_order_updates` sets both keys together (actives in the same order, inactive
  Priorities entries kept in place); `ff9mapkit coop`'s folder registration routes through it, every
  kit-printed "edit Memoria.ini" instruction and the docs now state the both-fields rule, and a
  launcher-round-trip unit test guards the invariant.

### Added — `on_defeat` covers VERBATIM forks
- The wipe-warp check now also lands on **verbatim forks**: a fork carrying the `[deathrules]` block gets
  the check **prepended into its donor's existing tag-10** after-battle handler (an offset-0
  `insert_in_function` prepend — always safe, even over a jump table; part of `compose_verbatim_eb`, so
  logic-edit discovery, the GUI dry-run, and the build all see one stream). A donor without a tag-10 has
  no battles — nothing is injected. With outpost *registration* already riding the shared `[startup]`
  path, a journey's real forked fields now participate fully: register as outposts AND warp on a wipe.
  The build's coverage warning now also names verbatim members lacking the block (their battles are the
  donor's, so it's a maybe-gap: battle-less donors can ignore it). Awaiting in-game playtest on a real
  battle-donor fork.
### Added — `world-minimap`: the custom continent appears on the in-game world map (no DLL)
- The big in-game map (`world_map_full_all.png`) is a mod-overridable loose PNG; `world-minimap
  --mod-folder <mod>` draws the folder's deployed overworld land onto it — the engine's own
  `w_naviGetPos` projection (the mapped world is exactly 1536×1280 units) onto the image's
  structurally-detected art rect, colours sampled from how the map draws real islets, verified
  against the 49 live navipos town anchors. Composes with Moguri's HD map (the override must sit
  above MoguriMain in FolderNames). Markers/labels at custom coords remain the known DLL seam.

### Added — the continent ENTRANCE pair: `world-entrance --field-direct` + `[[gateway]] to = "worldmap"`
- **`world-entrance --field-direct <id>`** wires an overworld entrance to a CUSTOM field: the trigger func
  keeps the proven template's vehicle/state gate verbatim and warps `Field(id)` directly — no dispatcher
  case is used or touched (the AREA switch only carries real base fields), so custom entrances compose
  additively across every free-roam world state.
- **`[[gateway]] to = "worldmap"`** gives a synthesized field a faithful walk-out to the world map: the
  base game's own shared exit cascade (byte-identical across all 79 real world-exit fields) is carried
  VERBATIM at build time, prefixed with the field's region-key write (`region_key`, default 62 — the
  open-sea key every ScenarioCounter band resolves to 9009, the all-vehicle free-roam superset).
  On-exit `set_scenario`/`set_flags` compose behind the usercontrol guard.
- The shipped example: `examples/continent-v1/waystation.field.toml` — the ISLAND WAYSTATION (field 6500,
  BG-borrows Daguerreo/Entrance: real art/walkmesh/camera, our logic; a save moogle + savepoint; the
  worldmap exit reuses field 2800's own real door region), entered from island B's minted cay via a tight
  4-tile trigger on the inland grass tip (the beach stays freely walkable).

### Added — declarative shore tweaks: `world-fuse` layouts + `world-transplant` mint a beach on a kit-made shore
- **`[placement.bank_lower]` + `[placement.virgin_mint]`** sub-tables in a `world-fuse` layout (and the
  matching `world-transplant --bank-lower "CX,CZ:RADIUS[:SLOPE[:CAP]][:along=AX,AZ/BX,BZ]"` /
  `--virgin-mint "...[:pins=PX,PY]"` flags) productize the in-game-proven island-B pattern: sink a
  mesa/cliff bank to a beach-capable profile (the corridor `along=` mode included) and mint a real-scale
  beach on it, `pins_from` byte-reading the foam/sand language from a beach-bearing reference block.
  Coordinates are donor-world; each verb's tweak block derives from them and must sit inside the placement
  region. One shared builder (`coastmorph.build_shore_tweaks`) serves both surfaces; the shipped
  `examples/continent-v1/` layout now carries island B's minted beach and reproduces the deployed world
  **byte-identically** (a re-deploy over the live folder changes zero bytes).
- `fuse_layout` now takes **`tweaks_factory`** per placement (rebuilt fresh for the gate pass and the
  deploy pass — tweak objects are stateful) and refuses plain `tweaks` on a real deploy actionably; the
  CLI wires the factory automatically. This closes a latent double-apply bug for any tweaked layout.

### Fixed — `bank_lower` cliff walls: the per-COLUMN lip anchor + the V-IN-BAND gate
- The wall V re-evaluation is now corner-role true (byte-checked map-wide: crest v=0.8926 / base
  v=0.9229 on every real face whatever its height): every crest keeps its painted lip row verbatim (no
  hard/bevel alternation), each base vert crops along its own column at the column's original density,
  the per-vert map closes seams (any face whose verts change re-emits), and the permanent **V-IN-BAND
  gate** refuses any emitted wall texel outside the byte-derived rock strip — the class that read as
  white gashes/grass bleeding in-game can no longer pass offline. In-game proven on continent island B.

### Added — the OUTPOST system: `on_defeat` warps to "the last camp visited"
- **`[field] outpost = true`** marks a field as an outpost: on **every entry** it writes its own id into a
  kit-reserved save-backed var (`gEventGlobal` bytes 1060–1061; last-write-wins = *the last outpost the
  player entered*; the write rides the `[startup]` injection, so **verbatim forks register too**). A
  `[deathrules] on_defeat` wipe now warps to that var's field — `warp_to` demotes to the **fallback** for
  a wipe before any outpost. Register-on-save/inn policies stay modder-side: the var is documented, write
  it from an `[[event]]` instead of tagging the field.
- The enabling engine mechanism, now a kit primitive: **op arguments can be expressions**
  (`EventEngine.getv2()`/`gArgFlag`: a set bit routes the operand through `CalcExpr` — the "computed ids"
  lane real fields use). New `region.field_to_var()` emits the computed `Field(<var>)`; the kit's own
  disassembler (which already parses the argFlag lane in real fields) round-trips the emission byte-exactly.
- In-game proven 2026-07-11, **both branches**: the computed warp (a wipe in a self-registered outpost
  returned to it) and the fallback (var zeroed → the `warp_to` field, HP/gil knobs intact). Two operational
  notes from the proof: the outpost var must always be written as a **whole word** (a half-written var is a
  garbage field id, and a garbage id black-screens the warp — there is no script-side registry check), and
  the F6 Flags BATCH word-write grammar is `w<i>=<v>` (e.g. `w1060=0`).

### Changed — `on_defeat`: the INSTANT exit (no body slide)
- Round-2 playtest: the quiet defeat worked but the escape sequence's run-away drift slid the fallen
  bodies during the fade. Workaround found in the same escape code: the slide only runs while
  `btl_escape_fade` counts down, so `on_defeat` now zeroes it — the exit is **instant** (no slide, no
  run-away fade, no flee whoosh — which was thematically off for a defeat anyway), and the battle closes
  the next frame, which also all-but-closes the mid-fade re-kill window the double-dock guard covers
  (the guard stays, as defense in depth). In-game proven 2026-07-11 ("instant exit works, no slide") —
  the whole `on_defeat` flow is now ★ proven end to end.

### Changed — `on_defeat`: the QUIET DEFEAT + the double-dock guard
- Playtest verdict on the first cut: mechanically proven (the wipe warps, no game over, gil docks,
  victories don't warp — and `Field()` from a tag-10 context is now an established fact), but the flee
  fade raced the get-up animations, and a mid-fade re-kill could dock gil twice. Both addressed:
  the revive no longer stands the party up (**the quiet defeat** — the battle fades out over the fallen
  party, who are on their feet at the destination because the field spawn owns motion there; this also
  shrinks the re-hit window), and a per-battle **double-dock guard** (`_defeatWarpFired`) makes a re-kill
  during the escape fade re-assert the exit without ever re-docking gil, re-setting the marker, or
  re-rolling a fresh second wind. Builds without `on_defeat` are byte-identical to the proven ones.
- A true "wait for the get-up, then flee" was rejected on engine grounds: no per-frame mod hook exists to
  delay the escape, the engine's escape branch has no motion-wait for living players (an engine patch
  would break the channel's stock-Memoria compatibility), and waiting would widen the ATB re-hit window.

### Added — `[deathrules] on_defeat`: warp instead of a game over
- **`on_defeat = { warp_to = <field id>, hp = 0.2, gil_loss = 0.1, flag = ... }`** cancels the party wipe
  and sends the player somewhere instead of the Game Over screen — the roguelike "back to camp". A DLL +
  FIELD composition built from one table: the DLL half revives the fallen quietly (the proven short-anim
  death-changer recipe) at `hp` × max, optionally docks `gil_loss` × party gil, sets a kit-reserved
  wipe-marker story bit (8508, `flag` overrides), and ends the battle through the engine's **own flee
  sequence** (the `SysEscape` trigger transcribed — the run-away fade, no flee-stat pollution, no engine gil
  cut); the FIELD half is a tag-10 (after-battle) prologue the build injects into every encounter field
  carrying the block: marker set → clear it → the proven fade → `Field(warp_to)`. Composes with
  `second_wind` (the wind fires first; spent or a failed `chance` roll falls through to the warp — the
  proven straight-line second-wind C# stays byte-stable when `on_defeat` is absent). The build **names**
  encounter fields missing the block (a wipe there revives + flees but cannot warp). Offline-proven (the
  money test compiles the DLL surface against the live engine; the tag-10 prologue is byte-tested) —
  awaiting in-game playtest.

### Added — `[lowhp]`: reparameterize the LowHP threshold
- A **`[lowhp]`** table in `field.toml` changes when a player counts as "HP is low" (vanilla: at or below
  1/6 of max HP — the yellow HP number + the engine `LowHP` status that HP-is-low supporting abilities and
  AI key on). `threshold` takes an exact `"N/D"` fraction (denominator ≤ 100) or a number in `(0, 1)`
  (snapped to ≤ 1/100 granularity); the emitted comparison is exact integer math in the engine's own `* 6`
  shape, so there is no float-boundary drift. Optional `flag` gate: bit clear = the vanilla 1/6, toggling
  **live** (the checkpoint runs on every HP/MP change). Rides the Overload channel's second RETURNING hook,
  `UnitCheckPoint` — single-owner; the displaced default's side effects (LowHP status add/remove, HP/MP UI
  colors) are transcribed verbatim with only the threshold changed, and the hub's fail-safe returns `0` (no
  forced status; the side effects retry at the next checkpoint). Facts pinned by the dive: a 0-HP unit is
  dead *before* the hook (not a death-prevention site), and the caller acts only on the returned `Death`
  bit. In-game proven 2026-07-11 (threshold 1/2: the HP number goes yellow on the hit that puts a
  character below half max). ([SCRIPTS_DLL.md §12](docs/SCRIPTS_DLL.md), [FORMAT.md `[lowhp]`](docs/FORMAT.md))

### Added — `[deathrules]` short-animation second wind
- **`animation = "short"`** on the second wind skips the full Rebirth Flame summon (flagged as potentially
  obnoxious in an authored context): instead of queueing the Phoenix command, the fallen party is revived
  directly the way the engine's own death-changer statuses do (`AutoLifeStatusScript.OnDeath` +
  `DeathStatusScript.Remove` + the `DecidePlayerDieSequence` cancel branch: set HP → `RemoveStatus(Death)` →
  `SetDefaultIdle`) — no choreography, the party simply stands up. Since the engine ability no longer decides
  the revive HP, a **`revive_hp`** fraction knob comes with it (of max HP, `(0, 1]`, floor 1 HP, default
  `0.2`). `animation = "full"` (the default) is the in-game-proven Phoenix variant, emitted unchanged. Only
  dead players revive (petrify stays, like the Phoenix ability); a wipe with nobody revivable falls through
  to a vanilla defeat. In-game proven 2026-07-11 (no summon; the party stands up at the set fraction;
  second wipe → game over; next battle → recharged).

## [1.0.0b15] - 2026-07-11 — Battle balance rules, a hand-built continent, and Chocobo Hot & Cold

> v1.0.0b14 was tagged and pushed but never published -- the release CI's Linux test job caught 4
> pre-existing gaps in tests added over the prior few days (never run on a bare, no-install/no-GUI
> machine before). Fixed same-day (commit `740d334`); this is the same content re-cut as b15.

### Added — Chocobo Hot & Cold: custom dig prizes on a verbatim forest fork
- A new declarative **`[chocobo]`** table sets the Chocobo's Forest dig prizes and timer tuning
  (`[[chocobo.prize]]` / `[chocobo.tuning]`) on a `--verbatim` forest fork, via `chocobo-export` +
  a new generic `[[logic_edit]] kind = "expr_literal"` edit primitive (in-expression-literal patching,
  reusable beyond chocobo). Popup text, the item actually given, and the tally all agree by
  construction. In-game proven on **all three Chocobo Forests** (2026-07-10): Elixir (2950),
  Phoenix Down (2951), Magic Tag (2952). Warp-in for testing is one F6 Flags-batch preset.
- The F6 debug menu's Flags tab gained a **BATCH story-flag operator**: bit/byte/word operations in
  one click, all-or-nothing, with named presets — the general tool this chocobo work needed and now
  ships for any story-flag testing.

### Added — the coast-morph pillar: reshape any verbatim coastline in place
- **Cliff morphs**: `--cliff-bump` (a conforming bow, ≤2.5u), `--cliff-headland` (a structural
  promontory, wall rebuilt over a pushed outline), `--cliff-bay` (the inward mirror), and
  `--cliff-lobes` (composed multi-lobe coastlines — a bay between two headlands in one window) on
  any `world-transplant`ed coastline.
- **Beach morphs**: `--beach-bump` (the first morph on a sandy shore — a whole-assembly cosine-tapered
  drag field), `--beach-reshape` (structural shape morph — the sand/waterline/berm assembly slides as
  a unit, the water ladder re-lays through the learned Wang tables), and `--beach-slide` (full-assembly
  translation, growing a beach seaward with native grass fill).
- **`--in-place`** deploys any of the above directly onto the REAL, already-shipped map coastline — no
  carrying/transplanting required first. A new **`ff9mapkit world-morphs --block BX,BY | --all`**
  scanner probes every real coastline window and catalogs **324 lawful morph windows map-wide** (297
  cliff, 27 beach), each with a ready-to-run `--in-place` deploy line.
- All in-game proven across 2026-07-09 through 2026-07-10, including on the live custom continent
  (below) through its `world-fuse` placement.

### Added — beach-mint: author a wholly new beach, not just carry one
- **`--beach-mint WIDTH|auto[:LAND]`** re-mints a real beach's sand+foam assembly from chain specs at
  any width — the seam chain, topology, and every UV are synthesized (no fan-transport from the
  donor), gated by the ribbon/slope/swash envelope laws. `:LAND` additionally synthesizes a new land
  chain (the berm pushed landward and BSP-clipped at the synthetic boundary) — a fully kit-authored
  beach, not a carried one. In-game proven 2026-07-11 (rungs 1 and 2a).
- Underpinning this: the **sand-band edge table** (`sand_rebuild`) and the **end-cap foam/sand tables**
  (`cap_rebuild`) were fully byte-learned map-wide and proven to regenerate every real beach
  byte-for-byte — **the shore tile vocabulary is now closed**.

### Added — the first hand-built continent
- Four real FF9 islands — a cliff/highland island, a shore island, a real sandy beach, and Uaho (FF9's
  own air-only islet) — fused into one seamless multi-island archipelago in open ocean via
  **`world-fuse`**, each carried verbatim and stitched at every shared border with zero seams. In-game
  proven 2026-07-09 ("all 4 islands render and walk fine, no seam at the strait"); ships as a worked
  example, `ff9mapkit/examples/continent-v1/`.
- New growth primitives underneath: `world-transplant --size NxM` carries a multi-cell landmass as one
  rigid assembly; `RowInsert`/`chain_row_inserts` grow an island by inserting real lattice columns
  (bit-exact seam extrusion); `spill-clip` unlocks growth using an empty neighboring cell's water as
  slack, without synthesizing new bytes.

### Added — battle-model export gap closed (all 71 alias ids)
- `extract.resolve_prefab` now replays the engine's own battle-model alias-resolution chain (boss
  forms, alternate outfits, field-avatar aliases), so all **71** shipped alias ids export, preview,
  reskin, and deploy engine-faithfully (a battle form = the shared field body + a battle overlay + its
  own animset; overrides land at the donor prefab folder). The 43 genuinely-unshipped ids now refuse
  with an actionable message. Byte-identical baselines confirmed offline (2026-07-10).

### Added — bone semantic display labels (`model-gltf`)
- Exported skeletons now carry anatomical bone names (e.g. `bone012_R_hand`) for 83% of FF9's rigs,
  derived from family-clustered rest-pose heuristics (`+x` = right, face = `−z`, pinned via weapon-hand
  anchors); binding is untouched, `--plain-bones` opts back out. Makes hand-editing a skinned mesh in
  Blender far easier to navigate. Offline-proven 2026-07-11.

### Added — image-field: `--auto-floor`, anchored occluders, real-photo proof
- **`--auto-floor`** (numpy seeded region grow, refusal-biased) auto-detects the walkable floor region
  instead of requiring a hand-traced polygon, and pre-loads the `--trace` browser tool for correction.
- **Anchored occluders** (`--foreground img.png@cx,cy`) now depth-sort against the player correctly —
  a cut-out's Z is set to the actor's own OT depth at its floor-contact point, so walking behind an
  object hides behind it and walking in front draws over it.
- A full-resolution cover-crop fix sharpens the deployed background (earlier builds shipped a softened
  image); rebuild any pre-existing `image-field` project to pick it up.
- *In-game proven on a real photograph* (2026-07-09) via the `--trace` tracer — the user's own hallway,
  walkable in FF9.

### Added — F6: overworld vehicle/disc tooling + the canonical coordinate readout
- New overworld vehicle-mode swap and disc-switch tooling in F6's Go tab, reverse-engineered from the
  dispatcher tables.
- The Position readout now leads with the canonical WRAPPED coordinate triple every kit tool speaks
  (`world (x,z) · block [x][y] (⌊x/64⌋,⌊−z/64⌋) · cell (x,z) (⌊x/32⌋,⌊−z/32⌋)`) instead of the engine's
  raw unwrapped position — ending a recurring coordinate-confusion class of bug. Copy position copies
  the canonical pair. In-game proven 2026-07-09.

### Added — `[deathrules]`: declarative game-over rules (the first RETURNING Overload hook)
- A **`[deathrules]`** table in `field.toml` owns the party-wipe verdict (`OnGameOver`): **`second_wind`**
  cancels the wipe once per battle with a full Phoenix party revive — the engine's own `SysLastPhoenix`/
  `RebirthFlame` command queued exactly the way the vanilla Eiko default queues it, recharging each battle —
  with an optional **`chance`** (whole percent) roll; **`keep_rebirth_flame = false`** removes Eiko's vanilla
  auto-revive (hardcore). Owning the hook displaces the engine's Eiko default, so the kit transcribes it
  verbatim and keeps it unless turned off. The optional **`flag`** gate means *fully vanilla* while clear
  (Eiko included — the rule sleeps, it isn't half-applied) and toggles live: the next wipe obeys the new
  state. Fail-safe by construction (any hiccup = a vanilla defeat, never a canceled wipe with nobody
  revived). Mod-global, relaunch-scoped, lint gate names it. In-game proven 2026-07-11 (first wipe →
  Phoenix revive at partial HP, second wipe same battle → normal game over, next battle → recharged).
  Known behavior: the revive plays the full Rebirth Flame summon animation (it's the real engine command)
  — a short-animation knob is a noted follow-up for authored contexts.
  ([SCRIPTS_DLL.md §12](docs/SCRIPTS_DLL.md), [FORMAT.md `[deathrules]`](docs/FORMAT.md))
- The Overload hub gained a **returning-hook mode**: hooks whose return value the engine acts on
  (`OnGameOver` → cancel-the-game-over) are single-owner — the hub returns the one owning feature's verdict
  expression and refuses a tree where two features claim one (`render_hub`); void hooks still compose any
  number of features. New `overload.flag_expr_cs` (the gate as a testable condition, for features whose
  vanilla path must run while the flag is clear).

### Added — `[rebalance]`: declarative HP-damage multiplier
- A **`[rebalance]`** table in `field.toml` scales the final HP-damage number by the caster's side —
  `player_damage` / `enemy_damage` (`0.05`–`20.0`) — with the same optional **`flag`** gate as
  `[difficulty]`. Where `[difficulty]` scales enemy *stats*, this is a flat post-formula multiplier and
  the only way to scale what the **party** deals; the two compose. Only pure HP damage is touched
  (healing/recovery/MP untouched). Honest limits documented in-source + docs: the engine clamps to 9999
  after the hook unless `[Battle] BreakDamageLimit = 1` in `Memoria.ini`, and the `IsDmg9999` cheat forces
  player damage to 9999. Rides the Overload channel's `OnDamageFinalChanges` as a **mutator** (runs after
  the verbatim reflect-multiplier default, before telemetry's observer — so a capture logs the rebalanced
  number). Mod-global, relaunch-scoped, lint gate names it. ([SCRIPTS_DLL.md §12](docs/SCRIPTS_DLL.md),
  [FORMAT.md `[rebalance]`](docs/FORMAT.md))
- The `gEventGlobal`-bit flag gate is now a shared `overload.flag_gate_cs` helper (byte-identical to
  `[difficulty]`'s prior inline gate; both features emit it). Flag-gate granularity follows the hook: a
  `[rebalance]` toggle takes effect **per hit** (live mid-battle), a `[difficulty]` toggle **per battle**
  (next battle) — both in-game proven 2026-07-11.

### Added — `[difficulty]`: declarative enemy scaling ("hard mode")
- A **`[difficulty]`** table in `field.toml` scales every enemy once per battle — `enemy_hp` /
  `enemy_attack` / `enemy_magic` (`0.05`–`20.0`), players untouched — with an optional **`flag`** gate
  (a `[[flag]]` name or `gEventGlobal` bit index) so a journey can switch hard mode on/off at runtime
  (seed via `[startup]`/an event; toggle live with F6 → Flags). Mod-global (one per deployed folder);
  identical repeats across campaign members are allowed, conflicting blocks refuse at build. Compiles
  into the mod scripts DLL via the Overload channel's `OnBattleInit` (a hook with **no engine default**
  — nothing vanilla is displaced; any state hiccup degrades to vanilla). Relaunch-scoped like the whole
  channel; the lint toolchain gate now also names `[difficulty]` when `csc` is missing.
  ([SCRIPTS_DLL.md §12](docs/SCRIPTS_DLL.md), [FORMAT.md `[difficulty]`](docs/FORMAT.md))

### Changed — the Overload channel got a HUB (one `IOverload*` implementer per interface)
- The engine registers Overload hooks **one implementer per interface per DLL** (last-wins, type order
  unspecified), so the kit now emits a single regenerated `Sources/Overload/0000_OverloadHub.cs` that
  implements the claimed interfaces (verbatim engine defaults included) and calls features — now plain
  static classes — in a fixed order: **mutators before observers** (telemetry's roster log shows the
  difficulty-scaled stats). Battle telemetry was refactored onto the hub (same events, same JSONL,
  same CLI); a live telemetry source left by an older kit is auto-upgraded at the next compile.
  A hand-dropped `.cs` colliding with the hub (or with another source) on an `IOverload*` interface is
  now a clear compile-time refusal instead of a silent coin flip.
- `deploy_field` deploy-stickiness is **generic**: ANY live-owned Overload feature (telemetry today) is
  folded back into a freshly deployed DLL through one code path (`overload.compile_live`), and
  build-owned script sources (`Battle`, `Difficulty`, the hub) are now **replaced** on deploy so removed
  declarative content can't resurrect from a stale live copy.

### Changed — housekeeping
- 11 project-scoped Claude Code skills added under `.claude/skills/` (deploy loop, `.eb` scripting,
  forking, scenes, overworld, battles, characters, models, engine builds, campaigns, items/saves) as
  load-on-demand agent procedures; the repo-root `CLAUDE.md` agent brief was slimmed from 785 to 186
  lines to route into them. Internal AI-agent tooling — no effect on the toolkit itself.
- The release CI workflow now gates the GitHub Release + PyPI publish on the full test suite passing
  and the git tag matching `pyproject.toml`'s version, and smoke-installs the built wheel into a clean
  venv before anything is published.

## [1.0.0b13] - 2026-07-08 — 14th playable character, Scripts-DLL scripting, custom models & creatures, synthetic overworld

> Versions **b3–b12** predate this file's return to per-version stamping; their notes live in
> [`release-notes/`](../release-notes/) and on the
> [GitHub Releases](https://github.com/GameJawnsInc/Dream-World-IX/releases) page. The per-version log
> resumes at b13.

### Added — EXPERIMENTAL: image → explorable field (`image-field`, MVP)
- **`ff9mapkit image-field <image> --floor "cx,cy …" --out DIR`** synthesizes a walkable FF9 field
  from an arbitrary image + a hand-traced floor polygon: the image becomes the painted background,
  the floor polygon is **un-projected onto the world ground plane into a walkmesh**, and a vanilla
  FF9 camera ties them together (optional `--foreground` cut-out PNGs become occluder overlays).
  Pillow-only, no new dependencies. The one genuinely new piece of math is the floor un-projection —
  because FF9's field projection is **perspective** (not orthographic) and we target a single plane,
  it's a closed-form projective **homography** (verified to round-trip `cam.to_canvas` to ~2e-12
  world units; uses `inv3(R_view)`, never a transpose — the k=14/15 squash makes `R_view`
  non-orthonormal). Everything downstream (camera synth, `.bgi` codec, `.bgx` overlay writer,
  deploy) is existing, in-game-proven machinery. This is the MVP hand-mask slice of a researched
  design; auto floor-detection + neural depth are optional future tiers. Awaiting in-game proof.

### Added — custom battle FORMULAS with no engine rebuild (the Scripts-DLL channel)
- A `[[playable]]` custom ability now takes **`script = { template = "drain_hp" }`** (or `{ body = "<C#>" }`)
  and the kit mints a genuinely new battle-calc formula — a `[BattleScript(id≥256)]` class compiled into a
  mod-owned **`Memoria.Scripts.<Mod>.dll`**, loaded *in addition to* the base engine by `ScriptsLoader`, with
  **zero engine-DLL rebuild**. Four stock-donor templates (`drain_hp`/`drain_mp`/`magic_damage`/`white_wind`) +
  a raw C# `body` escape hatch; the scriptId (256–511) is decoupled from the ability id (192–223). ★ In-game
  proven — Iviv's "Soul Leech" drain (damage + self-heal). Docs: **[docs/SCRIPTS_DLL.md](docs/SCRIPTS_DLL.md)**.
- The DLL is compiled at build/deploy against the INSTALLED engine (version-coupled) and loads once at the title
  screen (RELAUNCH — F6 won't reload it). Reversible deploy (`tools/deploy_field.py`).
- **Lint gate:** `ff9mapkit lint` now fails early with a clear, build-blocking error when a field carries a
  scripted ability but no C# compiler (`csc`) is findable — instead of the build dying mid-compile. Fix by
  setting `$FF9_CSC` or installing VS Build Tools (the always-present .NET Framework csc works too).
- **Engine-version stamp + drift warning:** each build stamps the DLL with the engine FileVersion it compiled
  against (a `<dll>.buildinfo.json` sidecar); deploy and the Setup & Health check warn when a deployed DLL was
  built against a different engine than the one now installed (e.g. after a Memoria update) — catching the
  version-coupling drift offline, before the in-battle `MissingMemberException`.
- **Paired field effects (the channel fan-out):** a custom ability's `script` now accepts a `field = {template/body}`
  sub-table → the kit mints a paired **`[FieldAbilityScript(id)]`** into the *same* DLL at the *same* scriptId, so a
  curative ability works both **in and out of combat** (five field templates transcribed from Memoria's
  `SFieldCalculator`; requires a paired battle formula — they share one minted id). ★ In-game proven — Iviv's
  "Lifewell" healed in battle *and* healed an ally from the field menu. See [docs/SCRIPTS_DLL.md](docs/SCRIPTS_DLL.md) §2.
- **Custom status behaviours (the channel's third surface):** an ability's `status` list accepts a table
  `{ name, template/body, hooks }` → the kit mints a `[StatusScript(BattleStatusId.CustomStatusN)]` (behaviour) into
  the same DLL, a `StatusData.csv` row at the auto-allocated custom id (33–63, so the engine can inflict it), and the
  `StatusSets` row that applies it. Templates `auto_life` (revive-on-death) / `auto_attack` (Berserk) + a raw `body`
  + `hooks`. A per-tick DoT is engine-gated (documented); the reachable hooks are Apply/Remove/OnDeath/OnATB/
  OnFigurePoint/OnFinishCommand. Each custom status **borrows a vanilla status's HUD icon** (template default, or
  `icon = "<vanilla status>"`) via a `BuffIcon`/`DebuffIcon` DictionaryPatch line registered at launch, so it shows
  in every panel display (battle HUD, target/"hover", resists, party menu); an `over_model = "<vanilla status>"`
  additionally gives it an ON-MODEL indicator (inheriting that status's SHP over-model chevron / SPS particle / tint
  from `StatusData`). The `auto_life` template takes a `power` knob (revive at power% of max HP, default 50).
  ★ Behaviour + panel icon + on-model chevron in-game proven (a custom revive-on-death status fired + showed both).

### Added — the Models tab (the custom-3D-models pillar's front door in the Workspace)
- A new top-level **Models** tab: browse every GEO model the kit knows (search + group filter +
  field-placeable filter) with **real rendered thumbnails**, a detail pane (preview still,
  bones/meshes/verts/textures, the model→animation action join, story-evolved/hair-swap appearance
  caveats, overworld-actor identity, Copy name / Copy `[[npc]]` snippet), and the whole DLL-free
  edit round-trip in one place — Export `.glb` (anims auto/all/none) · Import the edited `.glb` ·
  Mint a new id · Dump editable `.anim` clips — each streaming `ff9mapkit model-*` to the Output
  panel. Ctrl-K "Go to Models", a Home row, and dropping a `.glb` on the window all land here; the
  Import tab's old models box is now a pointer. Previews render on a background worker (per-user
  disk cache, `ModelThumbService`); a machine without the install degrades to text rows.

### Added — texture reskin (`model-reskin` + the Models tab's cheapest edit)
- **`ff9mapkit model-reskin <model> --export-textures DIR`** writes a model's pristine textures as
  editable `{name}.png` files; **`--deploy MODFOLDER --texture <edited.png…>`** ships them back to
  the model's own override dir (weapons' `BattleMap/BattleModel/6/` path included). No Blender, no
  FBX, no DLL — the engine probes `<model dir>/{textureName}.png` per material for every
  bundle-loaded model (`ModelFactory.cs:100-116`) and swaps the texture by NAME, so names are
  validated fail-loud (a mis-named PNG deploys fine and then silently never loads). Any size works
  (upscales fine); Zidane's F3/F4/F5 alt-costume forms are warned (the engine skips the probe for
  them). The Models tab gets **Export textures… / Deploy reskin PNG(s)…** buttons.

### Added — deployed-model inventory (`model-deployed` + the Models tab's panel)
- The loose-override system is write-only; this is the read side. **`ff9mapkit model-deployed
  <modfolder>`** lists everything model-side deployed in a mod folder — loose FBX **overrides**,
  PNG-only **reskins** (weapon tree included), **mints** (named via their `3DModel` DictionaryPatch
  line; an unregistered mint is flagged), **anim overrides**, and **dangling** `3DModel` lines whose
  folder is gone. `--revert <id> [--kind …]` deletes one entry (a mint also loses its line;
  path-guarded to the mod folder). The Models tab gets a **"Deployed in this mod folder"** panel
  with Refresh + a confirm-first **Revert selected…**.

### Added — wholly NEW animation clips (`model-anim-new`)
- The anim pillar authored *edits* of real clips; now it authors **new ones**: `ff9mapkit
  model-anim-new <model> --glb <blender.glb> --action <name> --deploy <mod>` (or no `--glb` for the
  built-in spin demo) builds a from-scratch clip — full-hierarchy `SetCurve` bone paths from the
  model's own skeleton — writes the loose `Animations/<id>/<key>.anim`, and registers it with an
  idempotent `3DModelAnimation <key> <ANH_…_SUFFIX>` DictionaryPatch line (keys minted in a
  2,000,000+ band, clear of real ids and the battle-animset band). Play it anywhere an anim id
  goes: `[[npc]] anims = { stand = <key> }`, a cutscene `animation` step. RELAUNCH to register.

### Added — custom weapon models (`[[weapon]] model`)
- A weapon item can now change what it LOOKS like: `model = "GEO_WEP_B1_030"` points it at a stock
  weapon model; `model = { id = 6500, tint = [1.7, 0.5, 0.5] }` (or `hue` / per-stem `textures`)
  **mints a recolored variant** at the new id — the loose FBX + PNGs land at the weapon override
  path (`BattleMap/BattleModel/6/<id>/`), the `3DModel` line registers the name, and the item's
  `Weapons.csv` `Model` column carries it, so the engine resolves it exactly like a stock weapon
  (`btl_eqp.InitWeapon` → `GetGEOID` → the disc probe). Composes with the existing `[[weapon]]`
  stat knobs; validated offline (mint band, ops, duplicate ids — all-specs-first so a bad block
  never leaves earlier mints half-emitted); deploy ships the weapon tree. RELAUNCH to register.
- Fixed: `ModLayout.model_dir` now routes type 6 to `BattleMap/BattleModel/` (was `Models/6/`,
  where the engine never probes).

### Added — palette-swap enemies (`[[scene.enemy]] skin`)
- The classic FF9 move (Goblin → Goblin Mage) as one declarative knob on a forked battle:
  `skin = { id = 6210, hue = 150 }` (or `tint = [r,g,b]` multipliers / `textures = { "<stem>" =
  "my.png" }` hand-painted overrides, composable; optional `from`/`name`). The build mints the
  enemy's model at the new id (≥ 6000) with the recolored textures, registers the `3DModel` line,
  and points the enemy's `Geo@30` at the mint — so the original creature stays vanilla everywhere
  else, and the variant keeps its own skeleton + clips (no cross-model retarget quirk, unlike a
  body re-skin). Alpha (the cutout mask) is preserved exactly; validation is offline + fail-loud
  (mint band 6000–32767 — `Geo@30` is a signed 16-bit field). RELAUNCH to register the id.

### Added — the `[[playable]]` form + the playable-anims GUI
- A **Playables** section in the field editor's object tree: a `[[playable]]` block's flat keys —
  id / name / borrow / recruit / `custom_battle_model` / `custom_battle_anims` / `anim_edits`
  (file-picked) / `portrait` (file-picked) / `battle_model_from` (model-picker) / `battle_model_id`
  — are now form-editable. The nested tables (stats / abilities / commands / status / script) stay
  TOML-authored and **survive a form save untouched** (the editor's save only replaces the keys the
  form owns; pinned by the smoke). The Models tab gains a **"Custom playable's battle animset"** box
  driving `playable-anims` (export the donor `.glb` with motion-named Actions / route the edited
  `.glb` onto the character's own minted animset).

### Added — model previews across the Info Hub + catalog pickers
- Every model-backed Info Hub page (models, archetypes, creatures, props) and the in-form catalog
  picker now show the rendered preview — leading the detail pane (an image below a 197-entry
  animation list reads as no image at all). Strictly CACHE READS (`models/thumbcache.py`, Qt-free):
  browsing the Models tab / running `model-preview` fills the per-user cache; the Info Hub never
  renders on the GUI thread, so a cold cache or a game-less machine degrades to text.

### Added — model previews (`model-preview` + the renderer behind the GUI thumbnails)
- **`ff9mapkit model-preview <model>`** software-renders any FF9 model to a textured PNG still — pure
  PIL (no OpenGL/Blender), orthographic 3/4 view, `--size/--yaw/--pitch/--rest`. Under the hood
  (`models/preview.py`): TRUE linear-blend skinning of the raw prefab (`boneWorld · m_BindPose · v`,
  exact even for the divergent per-bone binds the rigid G-bake approximates — the `GEO_SUB_W0_*`
  overworld actors rendered scrambled without it), posed at **frame 0 of the model's stand clip**
  (some rigs' rest pose is a collapsed authoring pose the player never sees), per-triangle affine
  texture mapping with REPEAT-wrap tile normalization, painter's sort + flat lambert shading.

## [1.0.0b2] - 2026-06-24 — verbatim-fork spatial authoring + engine refresh

Toolkit + engine-bundle refresh on top of the first public beta.

### Added — place additive content on a verbatim fork, visually
- **Verbatim-aware Blender export**: an imported verbatim/faithful fork (its `field.toml` ships
  `[walkmesh] bgi=`) now exports the spatial markers ONLY and keeps the real `.bgi` byte-exact — it
  never round-trips the walkmesh through the `.obj` path (which rebuilds neighbor links by shared
  vertex index and strands multi-floor seams). Closes a latent footgun where a verbatim fork
  mis-detected as editable and shipped a fragmenting walkmesh on export.
- The Blender spatial NPC marker now carries **name + position only**; the model/dialogue is authored
  in the `field.toml` (joined by name). The misleading `preset` field is gone.
- **Workspace** surfaces a scene-placed (`scene.toml`) NPC/marker with no `[[npc]]`/`[[marker]]`
  definition as a **"needs definition"** tree node + count badge, with one-click **Define**; a
  **Refresh (F5)** re-reads the `scene.toml` after a Blender re-export without re-opening the field.
- `lint_logic` warns a bare NPC (no model/preset/archetype) will clone the player model.
- Blender add-on **0.9.20**.

### Changed — engine bundle (`dwix-custom-memoria-1.0.0b2.zip`)
- Rebuilt with the full live fork-fidelity set **s23–s33** (was s23/s24/s29 in 1.0.0b1): adds the
  DoEventCode scripted-walk positions (s30), the name-keyed overlay/control/menu gates (s31/s32), and
  the `fldMapNo`-argument lookups incl. the authorable in-field LOCATION name (s33). Disc-1 + the
  walk/occlusion/menu fixes are in-game proven; s32 and the s33 sibling sweeps ship unverified
  (identity-safe for real fields).

## [1.0.0b1] - 2026-06-19 — Dream World IX public beta

First public (beta) release of **Dream World IX** (the `ff9mapkit` toolkit). The entries below
document the development history leading to this release; the per-entry version labels are the
pre-release development progression.

### Added — raw17 `btlseq` NET-NEW sequence authoring: assembler + length-changing splice (0.9.90)
The final raw17 tier: author choreography from scratch and splice it in, mirroring the proven `.eb`-AI
`cmdasm`/`aiauthor` path. The same-length patcher (0.9.89) edits operands in place; this CHANGES a sequence's
length and repacks the whole file.
- **`battle/seqcodec.serialize_repacked`** — the length-changing serialize: re-lays distinct bodies contiguously,
  recomputes every `seqOffset[]` (+4 skew) + `camOffset` (4-aligned), re-appends the camera block verbatim (its
  offsets are camOffset-relative → it floats intact). Range-checks both i16 offsets. Logical round-trip proven on
  all 562 corpus files (`parse(serialize_repacked(parse(b)))` == same sequences + camera).
- **`battle/seqasm.py`** + CLI **`battle-seq --asm "<src>"`** — the assembler (inverse of the disassembler):
  `Name(field=value, …)` lines → instruction bytes, each operand range-checked against its field; a leading
  `[offset]` + trailing `# comment` paste back in. `to_source`↔`assemble` is an exact mutual inverse, proven
  byte-for-byte over all 3525 distinct corpus bodies; `assemble` self-verifies its output re-decodes. A
  terminator-free `assemble_fragment` feeds inserts.
- **`battle/seqauthor.py`** + battle.toml **`[[scene.seq_replace]]`** (replace a whole sequence body) +
  **`[[scene.seq_insert]]`** (splice a fragment at a `before`/`after` locator — an instruction index or opcode
  name) + CLI **`battle-seq --lint`** (`lint_seq`: the one semantic crash class the codec can't see — an `Anim`
  code resolving past `animList`). Length-changing edits run AFTER `seq_patch` in the build (its offsets stay
  valid), then repack; shared-body aliasing is warned. Composed + validated offline like the AI authoring.
- The keystone for a brand-NEW attack slot (grow `seqCount` + wire a raw16 `AA_DATA` + the `.eb` AI to select it);
  the replace/insert primitives + the repack are its foundation.

### Added — raw17 `btlseq` attack-sequence codec + disassembler + same-length patcher (0.9.89)
The raw17 attack-CHOREOGRAPHY body — the last battle frontier — is now read + patchable, mirroring the proven
`.eb` enemy-AI on-ramp (read → same-length patch → lossless codec). PROVEN against `btlseq.cs` + a 562-scene /
3814-sequence corpus sweep: a width table derived from the 34-entry `gSeqProg[]` delegate table (cross-checked
against the independent `AdvanceSeqCode` skip table — the engine's own built-in parity check, agreeing for all 34
opcodes) disassembles 3814/3814 sequences to a terminator, and the codec round-trips `serialize(parse(b)) == b`
byte-exact on 562/562 real donors (the raw16/camera-codec golden analog).
- **`battle/seqcodec.py`** — the lossless codec (`parse`/`serialize`) + the in-memory model (header + per-body
  decoded instructions + the verbatim camera block, which the separate `camera_codec` owns). The 34-opcode table
  (name + operand width/signedness/kind per `SeqExec*`/`SeqInit*`); the `+4` body skew; `seqOffset` aliasing
  (multiple `sub_no` → one shared body); verbatim gap/pad capture (padding is NOT a derivable alignment rule);
  rejects a body opcode of 34 (the latent `gSeqProg[34]` out-of-bounds crash).
- **`battle/seqdis.py`** + CLI **`battle-seq <scene>`** — the read-only disassembler view: each `sub_no` (= attack
  index) as named instructions with annotated operands + the resolved global anim ids
  (`animList[seqBaseAnim[sub_no] + animCode]`). `--sites` lists the patchable operands (the `aipatch --sites` analog).
- **`battle/seqpatch.py`** + battle.toml **`[[scene.seq_patch]]`** — same-length operand patches (the `aipatch`
  analog): `constant_sites` yields every patchable operand (frame counts, anim/camera/vfx/sfx ids, masks, coords;
  the 0x19 Sfx discarded-pad byte is excluded); `[[scene.seq_patch]]` does an `at`/`old`-guarded/`new` in-place
  edit (no offset repack — byte-accurate by construction), applied to the forked raw17 in the mint build + lint-
  validated offline. raw17 is language-independent, so one patch covers all languages.
- Deferred (the §8 tail): length-changing edits — an instruction assembler + a net-new sequence (a coordinated
  raw16 `AA_DATA` + raw17 header/body + `.eb` AI-by-`sub_no` edit). The `seqcodec` model + offset-fixup are the
  foundation for it.

### Added — `[[learn]]` → Abilities/<Preset>.csv: the character ability-progression curve (0.9.88)
The last Character-CSV lever (and the highest-value): author what each character LEARNS + the AP to master, per
preset. WHOLE-FILE per preset (highest-priority-wins, mirroring `[[leveling]]`): reads the base
`Abilities/<Preset>.csv`, overrides an existing token's AP / appends a new one / drops a removed one, re-emits the
COMPLETE list.
- **`[[learn]]`** = `preset` (a `CharacterPresetId` name/id 0-19 — guests split Cinna1/2 etc.; bare names are an
  ambiguous error) + `[[learn.ability]]` sub-tables (`ability` + `ap`) + an optional `remove = [...]`. The
  `ability`/`remove` tokens accept `0` / `AA:n` / `SA:n` (range-checked), an SA NAME (committed table → `SA:id`),
  or an active-ability NAME (resolved live via Actions.csv → `AA:id`). Multiple blocks per preset merge.
- New `characterdelta.build_learn_file` (per-preset FILE SET) + `_resolve_learn_token` + `_group_learns` + a
  `ModLayout.abilities_csv(preset)` METHOD + the build validate/emit + a dedicated **per-preset deploy step**
  (walks the staging `Abilities/` dir, each file its own reversible backup; folds the 20 preset stems into the
  startup-CSV relaunch set). 3 tests; full suite green. **Character-CSV niche lane COMPLETE** (only `Commands`
  command-DEFINITIONS deferred, cross-ref into Actions).

### Added — `[[character_param]]` + `[[command_set]]`: character identity + battle-menu layout (0.9.87)
The first two of the player-character CSVs (partial per-id deltas, mirroring `[[character]]`/BaseStats):
- **`[[character_param]]`** → `CharacterParameters.csv`: `character` + `row` / `win_pose` / `category` /
  `menu_type` (a CharacterPreset name/id) / `equipment_set` + the advanced `serial_formula` / `name_keyword`
  Strings. CRITICAL: written by **FIXED column index** (the file's legend names are stale — `DefaultMenuType`
  etc.); all numerics are Byte (0-255), range-checked offline; String cells reject an embedded `;`.
- **`[[command_set]]`** → `CommandSets.csv`: re-point a character's battle-menu command SLOTS (`attack` / `defend`
  / `ability1` / `ability2` / `item` / `change` + their `*_trance` variants) to existing `BattleCommandId`s
  (0-47) — e.g. give Vivi a different ability command. Keyed by **preset 0-19** (`CharacterPresetId`, NOT the
  0-11 CharacterId — guests split into Cinna1/2 etc.; bare names are an ambiguous error). Handles the file's
  **tab-padding** (strips every cell) + the colliding `Attack(Trance)` legend (fixed-index slots).
- New committed `PRESET_IDS` (0-19 CharacterPresetId names) + `config` paths + build validate/emit + deploy
  startup-CSV wiring. 4 tests; full suite green. (The `[[learn]]` ability-progression lists + a `commands`
  catalog are the remaining character-CSV pieces.)

### Added — `[[magic_sword_set]]` → MagicSwordSets.csv: author combo unlocks (0.9.86)
The last battle-CSV-family lever: Steiner+Vivi-style combo unlocks — a **Supporter**'s `base_abilities` unlock a
**Beneficiary**'s `unlocked_abilities` (Vivi's Black Magic → Steiner's Magic Sword), unless a `*_blocking_status`
is present. **`[[magic_sword_set]]`** = `id` + `supporter`/`beneficiary` (CharacterId name/id, reuses
`characterdelta._resolve_char_id`) + `base_abilities`/`unlocked_abilities` (active-ability ids → `AA:n` tokens) +
`supporter_blocking_status`/`beneficiary_blocking_status` (reuse `encode_status_list`). Emits a PARTIAL
`MagicSwordSets.csv` (per-id merge, `EnumerateCsvFromLowToHigh`, no base read → offline). Row verified vs the base
(`1;1;3;AA:25, AA:26;AA:50;Silence(3);Sleep(17), Mini(28)`). build validate/emit + deploy startup-CSV wiring. 2 tests.

### Added — `[[status_set]]` → StatusSets.csv: author the status BUNDLES actions inflict (0.9.85)
Completes the action→status story: `[[battle_action]] status_index` (0.9.84) points an ability at a status SET;
this authors new sets. **`[[status_set]]`** = `id` (0-38 = base, ≥39 = custom), `name` (cosmetic), `statuses`
(a BattleStatus list, reusing `encode_status_list`). Emits a PARTIAL `Data/Battle/StatusSets.csv` — the engine
merges per-id low→high (`FF9BattleDB.LoadStatusSets` via `EnumerateCsvFromLowToHigh`), so it ships ONLY the
author's rows (no base read → fully offline + provenance-clean). `actiondelta.build_status_sets` + the build
validate/emit wiring + the deploy startup-CSV copy loop (RELAUNCH). Row format `Name;Id;Name(idx)…` verified
against the base (`Doom + Slow;39;Doom(27), Slow(20)`). 5 tests; full suite green.

### Added — round out `[[battle_action]]` / `[[status]]`: targeting, presentation + status interaction (0.9.84)
The niche player-side levers, completing the Actions.csv / StatusData.csv author surfaces (column-adds to the
existing `actiondelta` emitter + three new committed encoders):
- **`[[battle_action]]`**: `targets` (TargetType, by name/id), `menu_window` (TargetDisplay), `default_ally` /
  `for_dead` / `default_on_dead` / `camera` (booleans), `vfx1` / `vfx2` (anim ids; `vfx1` is signed Int16),
  `status_index` (the StatusSets row an action inflicts/cures).
- **`[[status]]`**: `clear_on_apply` / `immunity_provided` (BattleStatus lists — what applying a status CLEARS /
  what it grants IMMUNITY to).
- New `battlecsv` encoders: `encode_target_type` / `encode_target_display` (committed `TargetType` / `TargetDisplay`
  enum names → `Name(value)`) + `encode_status_list` (`BattleStatusId` → `Name(idx), …`). Verified against the
  engine PARSE side (`CsvParser.EnumValue` reads the int in the parens — the name is cosmetic; `Boolean` reads
  char 0; `ParseBattleStatus` splits the comma-list), so the emit round-trips the base file's own write format
  EXACTLY (`Defend(15), Poison(16)`, `AllEnemy(8)`). cp1252/LF, range-checked offline. 11 tests; full suite green.

### Added — `[[ability_feature]]` → AbilityFeatures.txt: author what abilities DO, no DLL (0.9.83)
The player-side "prize" lever: emit a drop-in Memoria `AbilityFeatures.txt` — the DSL behind Auto-Haste, killers
(Man Eater), MP+20%, Counter, gil-gated casts, command disables. A PARTIAL file merged per-ability over the base.
- **`[[ability_feature]]`**: `kind` (SA/AA/CMD), `ability` (a SupportAbility/active name or id; CMD = int id),
  `cumulate` (the trailing `+` merge flag; default `true` = stack over the base, `false` = full override / clear),
  `comment`, `features` (the `[code=...]` / feature-line body, passed through OPAQUE — the engine validates the
  NCalc formula at load). `abilityfeatures.py` (mirrors `battlepatch` in shape, the CSV-deltas in lifecycle).
- Reuses the committed SA name table (`characterdelta`) + the live `Actions.csv` AA resolver (`actiondelta`);
  provenance-clean (emits only the author's blocks). Offline structure-validation: id range per kind, balanced
  `[code]`/`[/code]`, no nested header, the closed AA/CMD `[code=TAG]` sets (warn on unknown/cross-kind), the
  special-id words `Global`/`GlobalLast`/`GlobalEnemy`/`GlobalEnemyLast` (kind-gated). CLI `ability-features [--tags]`.
  Deploys via the startup-CSV copy loop (`.txt`-aware backup/revert) → **RELAUNCH to apply**.
- Built from a 4-agent recon spec + validated by a 4-lens adversarial review. The review confirmed the whitelists
  EXACTLY match the engine parsers (no real ability is false-rejected or mangled) and caught two bugs + four
  fidelity fixes: ★ the **indented-SA-verb silent no-op** (the engine `^verb` matcher ignores leading whitespace
  → emit now strips body lines to column 0), a **single-table dict build crash** (→ routed through `_as_list` so
  build matches lint), the empty-body "clear" override, the multi-line `[code]` warning, the AA id-0 warning, and
  the exact-token SA verb hint. 28 tests; full suite green. ★ **IN-GAME PROVEN (2026-06-14):** a `>SA Global`
  `StatusInit AutoStatus Haste` block (emitted from `bt_trigger.field.toml`, deployed via `deploy_field.py`'s
  `.txt`-aware copy loop, RELAUNCH) made the WHOLE PARTY start every battle Hasted, no ability equipped — the
  no-DLL ability-effect DSL works end-to-end (author → build → deploy → in-engine).

### Added — enemy `flags` lever + the gap-map reconciled (0.9.82)
- **`[[scene.enemy]] flags`** (raw16 `SB2_MON_PARM.Flags@48`): the one enemy-identity field BattlePatch can't
  reach (not a `[PatchableField]`). Named bits `die_atk`/`die_dmg` (death-animation path) + **`non_dying_boss`**
  (the enemy SURVIVES HP=0 — for scripted boss phases); accepts a name / list of names / raw int (the unnamed
  high bits pass through to the enemy's AI `.eb`). `scene_data._MON_FLAG_NAMES`, from `ENEMY.cs:37-39`.
- **Gap map reconciled — the WHOLE lever map** (`docs/BATTLE_DESIGN.md`): the "Kit" column was systematically
  stale (Phases 3/5/6 shipped but the doc wasn't updated). Two audit passes (the second a 7-agent workflow that
  verified every claim against the code) flipped ~36 stale entries:
  - §2 **(a)** per-enemy stats: `category`/`hit_rate`/4 defences/`blue_magic`/`win_card`/element affinities/status
    masks/`bonus_element`/drop-steal rates/`max_damage_limit` are all built (`scene_data` raw16 + `battlepatch` BP);
    `flags` added (above); only the inert per-type `AP@50` remains unexposed.
  - **(a′)** the AA_DATA enemy attack table → done via `[[battle_attack]]`/`[[battle_patch.attack]]` (BP by name).
  - **(a″)** pattern Rate/AP → done (BP / `[scene] ap`). **(a‴)** scene-wide flags (preemptive/back-attack/
    can-escape/…) → done via the BattlePatch SCENE token (`battlepatch.SCENE_FLAGS`).
  - **(b)** enemy AI: all six rows were understated → done (the Phase-6c `[[scene.ai_function]]`/`ai_phase`/
    `ai_insert`/`ai_patch` + `ai_entry` surfaces).
  - **(c)/(d)/(e)** CSV deltas: `[[battle_action]]`/`[[status]]` (`actiondelta`) + `[[character]]`/`[[leveling]]`/
    `[[ability_gem]]` (`characterdelta`) → done (Phase 3/5/5b).
  - §4 fidelity: the raw16 scene + battle-eb container + raw17 camera are codec-proven on real donors; the
    "what each lever needs first" list is nearly drained (only the raw17-btlseq codec remains).
  - §9: MergeScripts (default false) + raw16-tail preservation marked RESOLVED. The gap map now matches the code.

### Added — enemy BODY re-skin: `[[scene.enemy]] model =` / `model_scene =` (0.9.81)
Make a forked battle enemy LOOK like a different creature while keeping its own gameplay (stats/affinities/
rewards/AI) — the "altered model" lever, no DLL, no new codec.
- **How:** transplant a REAL donor enemy's self-consistent model block (Geo + the 6 Mot animation ids + Mesh +
  Radius + the model-attached cosmetics: bones, die/start SFX, status-icon + shadow bones/offsets) into the
  target type's `SB2_MON_PARM`, leaving every gameplay field. The donor block is read LIVE from the install (so
  the bytes are guaranteed engine-valid — `btl_init.cs:240`/`:521-522`: a Mot id that doesn't belong to the
  loaded Geo freezes the battle). `scene_data._RESKIN_RANGES` is the byte map; `reskin.py` resolves the donor.
- **Two forms:** `model_scene = "<SCENE>"` (+ `model_type = N`) copies a named real battle scene's enemy (the
  reliable form, "look like THAT enemy"); `model = "<GEO_MON_B3_* / numeric id>"` resolves a geo id and scans
  the install for the first real enemy that uses it. (Friendly creature names are FIELD models, not battle
  enemies — use a donor scene or a `GEO_MON_B3_*` id.) `--game` added to `battle-build` for non-standard installs.
- **HONEST SCOPE — a BODY re-skin, not a full one** (adversarial review flagged it; ★ in-game test confirmed the
  split): the transplanted Mot[6] drive the new model's OWN idle/damage/death, but the per-ATTACK animation is
  bound by the untouched raw17 btlseq (keyed by Konran@78) — so the ATTACK plays the target's clip retargeted onto
  the new mesh. Proven in-game: a Goblin re-skinned to the Fang IDLED as a quadruped Fang but Knifed / Goblin-Punched
  with the Goblin's animation (clip load is by name, `AnimationFactory.cs:60`, so the cross-model attack retarget
  never crashes). The build warns per slot; a full re-skin (donor raw17 attack binding + AA_DATA) is deferred.
- Validated by a 4-lens adversarial review (verified the byte ranges partition cleanly model-vs-gameplay, the
  Konran/MesCnt/Flags exclusions are correct, Radius@28 is live; caught + fixed: the attack-anim mis-scoping
  [now warns], a broken friendly-name form [F0 field models ≠ B3 battle enemies; docs/errors corrected], raw
  tracebacks on a missing install/UnityPy [now actionable `ReskinError`], a silent `model_type`-alone typo, and
  the dead `--game` plumbing). 14 new tests incl. 2 install-gated real-donor golden transplants. Full suite green.

### Changed — raw17 camera codec real-donor proven + the btlseq/sequence doc corrected (0.9.80)
A test + docs pass (no behaviour change) closing two `docs/BATTLE_DESIGN.md` gaps surfaced by an analysis workflow.
- **Camera codec golden round-trip on a REAL donor** (`test_battle_scene_codec.py::test_camera_codec_golden_roundtrip_real_donor`,
  install-gated): `serialize_block(parse_block(raw17)) == raw17[camOffset:]` **and** `splice_block(raw17, …) == raw17`
  on `EF_R007`. The opening-camera codec was previously synthetic-tested only; it is now proven lossless on actual
  Square-Enix bytes (the camera-codec analog of the raw16 scene-codec golden). Resolves the §9 open question.
- **Doc correction (the mischaracterization):** the raw17 `btlseq` attack-choreography body was labelled "cannot
  author." Corrected — the *kit* lacks a sequence codec, but the *engine* permits **data authoring with no DLL**.
  New **§2(h)** documents the engine-verified facts (a 10-agent analysis, 3 claims adversarially re-derived from
  source): two channels (binary `btlseq.raw17` via `gSeqProg[]`; text `Data/SpecialEffects/<ef>/*.seq` via
  `UnifiedBattleSequencer`, gated by `SFXRework`), both no-DLL whole-file overrides; the genuine gameplay levers
  (hit-count = total damage via repeated `Calc`; effect-gating; text-only target-rescope + `gEventGlobal` writes);
  what sequences CANNOT change (the damage math, bound from `AA_DATA`/`scriptId` before the sequence); and why
  sequence authoring is **not** a custom-model stepping-stone (it references existing anim/model ids by name).

### Added — `[[scene.enemy]] ai_entry` = an explicit AI-binding override -> a forked boss is now FULLY declarative (0.9.79)
Closes the last gap: a complete forked boss from `battle.toml` alone, no hand-patches.
- **`[[scene.enemy]] ai_entry = N`** overrides `rewrite_main_init`'s generic `1+type` AI binding (used by
  `monster_count`). EF_R007 is an OFFSET-entry donor — its Main_Init `SWITCH(B_SYSVAR[31])` binds the Goblin
  (type 0) to entry **2** (entry 1 is a different type's AI), so `monster_count` alone bound the WRONG, turn-less
  AI (the Goblin stood idle). `ai_entry` pins the right entry (find it with `battle-ai <scene>`). Validated offline
  (a bad/empty entry fails `validate` with a clear message, not just at build).
- So the whole forked boss = `monster_count` (uniform spawn) + `[[scene.enemy]] type=… ai_entry=…` (the binding) +
  `[[scene.ai_phase]]` (the HP phase). The previously-needed rotation **reseed drops out** — `ai_phase` overrides
  the attack index, so the seed is moot. Proven on a clean EF_R007 fork: Main_Init binds entry 2 + the HP-phase
  splices + lint-clean (the same behaviour as the hand-patched, in-game-proven build).
- 4 new tests; full suite green.

### Added — declarative enemy-AI authoring: `[[scene.ai_phase]]` / `[[scene.ai_insert]]` + `B_MEMBER` naming (0.9.78)
Productizes the in-game-PROVEN HP-phase / branch-insert capability into `battle.toml` (was hand-spliced Python).
- **`[[scene.ai_phase]]`** — a high-level "enrage below X% HP" surface: `entry`/`tag`/`stat` (hp/mp/at)/`below`
  (unit fraction)/`then`/`else` (attack index below/above the threshold). Generates the exact `cur < max/N`
  branch 56 shipping bosses use (the `_E`/`B_PICK`/`B_COUNT` extract idiom) and splices it before the function's
  `Attack`; the attack-index variable is INFERRED from that `Attack`. **Proven byte-identical** to the hand-built
  branch that was in-game proven (Goblin Knifes above half HP → Goblin Punch below). `then`/`else` are
  range-checked against the scene attack count (the one fault the composed lint can't see).
- **`[[scene.ai_insert]]`** — the general length-changing primitive made declarative: splice an assembled
  fragment into a function at a locator (`before`/`after` = a command mnemonic, or `at` = a body offset), via
  `eb.edit.insert_in_function`. Composed + linted in the build like `ai_function`/`ai_patch`.
- **`B_MEMBER` naming** (`eb/_membertable.py`): the `btl_scrp.GetCharacterData` selector→field map (cur.hp=36,
  max.hp=35, MP/ATB/status/defence/…). `disassemble_ai` now annotates `B_MEMBER(36)` as `# B_MEMBER 36=cur.hp`
  (read), and the assembler accepts `B_MEMBER(cur.hp)` by name (write) — the `pretty_expr` round-trip stays raw.
- Validated by a multi-lens adversarial review (caught + fixed: a boundary-blind jump-straddle guard that could
  ship a corrupt-but-unlinted eb, a mid-instruction `at`, an append-at-end locator/splice contradiction, an
  uncaught non-numeric `below`, a divisor overflow, an unchecked then/else). `eb.edit.insert_in_function`'s
  straddle check is now boundary-correct (rejects genuine corruption, allows the "before X" target retarget).
- 40 new tests; full suite 1361 green. **Branch/phase splice in-game proven; the declarative surface reproduces
  it byte-for-byte.** Remaining gap: the Main_Init binding fix + seed reseed aren't yet declarative.

### Fixed — scalar-`zone` / string-iterable lint guards on `[[shop]]` / `[[jump]]` / `[[savepoint]]` (0.9.90)
- The `validate()` paths for `[[shop]]`, `[[jump]]`, and `[[savepoint]]` called `len(zone)` on the raw value, so a
  scalar `zone = 5` raised an uncaught `TypeError` that aborted the whole lint with a traceback (instead of a clean
  problem); and `[[shop]] sells = "Potion"` (a bare string) iterated char-by-char into per-character "unknown item
  'P'/'o'…" noise. Added `isinstance(list/tuple)` guards (a new `_zone_desc` helper reports the point count or the
  type, never `len()`-crashing in the message) — mirroring the same guards the synthesis review folded into
  `[[synthesis]]`. The deferred sibling-hardening follow-up from that review, now closed. +4 tests.

### Added — `[[item_text]]`: an item's menu NAME + description text, no DLL (0.9.89, ★ IN-GAME PROVEN)
- Rename an item or rewrite its description — the text companion to the stat tuners (`[[item_effect]]` changes how
  much a Potion *heals*; `[[item_text]]` changes the menu text that *says* so): `[[item_text]] name = "Potion"` +
  `display_name = "Mega Potion"` and/or `description = "Restores 15 HP."` (at least one). Mod-global + repeatable.
- **Channel = a drop-in `TextPatch.txt`** at the mod-folder root — the *same* per-folder patch-file mechanism the
  kit already emits for `DictionaryPatch.txt` / `BattlePatch.txt` (read once per folder at
  `DataPatchers.Initialize` → `TextPatcher.PatchTexts`). Each item becomes a `>DATABASE` find/replace gated by NCalc
  on `Database == 'RegularItem' && EntryId == <id> && IsNameEntry/IsHelpEntry`. The kit writes **only your strings +
  the resolved id** — it reads nothing from the bundles (fully provenance-clean, unlike the CSV deltas).
- **Grounded in the Memoria source** (`TextPatcher.cs` + `FF9TextTool.cs:776-789`, both fully read): `SetItemName`
  flags `IsNameEntry`; `SetItemHelpDesc` **and** `SetItemBattleDesc` BOTH flag `IsHelpEntry` → the menu-help and
  in-battle descriptions are **inseparable** through this channel, so `description` sets both. Full-replace uses the
  Multiline-immune `Find: \A[\s\S]*\z`; the emitter escapes `$`→`$$` (Regex.Replace group-ref) and carries real
  newlines as `\n` (the engine reads the patch line-by-line, then converts `\n`→newline).
- New `content/itemtext.py` (`render_block_lines` / `validate_blocks` / `merge_text_patch`) + `ModLayout.text_patch`
  + `build._emit_item_text` (mod-global aggregate + dedup-warn) writing `TextPatch.txt` in `build_mod` +
  `validate()` lint + `deploy_field.py` non-clobbering splice-under-`//`-markers (mirrors the `BattlePatch.txt`
  merge) with revert + RELAUNCH note. `deploy_campaign` ships it for free (whole-dist copytree). 31 tests
  (1530 total). FORMAT.md `[[item_text]]` section.
- **Multi-lens adversarial review** (3 lenses × verify) folded 4 real findings: reject a *literal* backslash-`n`
  (the engine rewrites `\n`→newline, so it can't be shown literally — fail offline, not in-game); reject `NoItem`
  (255), mirroring the sibling `[[shop]]`/`[[synthesis]]` guards; key the cross-field dedup-warn on the **resolved
  id** so name/id aliases of one item still warn; and reword the same-field-twice warning ("twice on X" vs the
  misleading "in two fields (X and X)"). One finding refuted (first-error-only lint — intentionally mirrors
  `battlepatch.validate_blocks`).
- **★ IN-GAME PROVEN (2026-06-13):** a `[[item_text]]` on the Potion (item 236) showed **"Mega Potion"** in the
  Items menu with the help bubble **"Restores 15 HP."** — both the `display_name` (IsNameEntry) and the
  `description` (IsHelpEntry, menu-help + battle) landed. This also settles the last open question: the patchers
  ARE loaded before the item text is imported (`DataPatchers.Initialize` in `AssetManager.DelayedInitialization`
  precedes the text-bundle import), so a startup-time `>DATABASE` patch applies. Pairs with the 0.9.88
  `[[item_effect]]` proof (that made the Potion *heal* 15; this makes the menu *say* so) — a full no-DLL retune.

### Added — `[[item_effect]]`: tune a consumable's use-effect (ItemEffects.csv), no DLL (0.9.88, ★ IN-GAME PROVEN)
- Tune what a **usable item** does: `[[item_effect]] name = "Potion"` + any of `power` (heal/damage, 0-9999) /
  `rate` (status chance, 0-100) / `element` / `status` (a `BattleStatus` mask by name, e.g. `["Poison"]`) /
  `for_dead` (usable on a KO'd target). Emits an `ItemEffects.csv` (`ItemEffect`) delta — the item is located by its
  `EffectId` and the row is edited **in place** (`EffectId` is **1:1** with a usable item — verified 32/32, no
  shared `Empty` row, unlike `BonusId`). The effect's **behaviour** (`ScriptId`/VFX/target) is preserved, so
  `status` only sets *which* statuses the effect concerns — inflict-vs-cure follows that existing `ScriptId`.
- **Grounded in the Memoria source:** `ItemEffects.csv` = `Id;Targets;DefaultAlly;Display;AnimationId;Dead;
  DefaultDead;ScriptId;Power;Rate;Element;Status` with `#! IncludeId`; whole-row merge by Id (`ff9item.LoadItemEffects`
  via `EnumerateCsvFromLowToHigh`) → a partial delta carries the base header verbatim + only the patched rows.
  `encode_statuses` maps status names → the `BattleStatus` UInt64 mask (the kit's existing `itemstats.STATUSES`).
- New `[[item_effect]]` block in `content/itemdata` (+ `build_item_effects_delta`, `encode_statuses`) + the
  `_emit_item_data` bucket + `write_item_data` param + `ModLayout.item_effects_csv` + `config` + `deploy_field`
  reversible CSV loop + `_STARTUP_CSVS` (RELAUNCH) + `validate()`. Base read LIVE in cp1252, **no game data
  committed**. Multi-lens adversarially reviewed (0 blockers): folded a `UInt64` upper-bound guard on a raw
  `status` bitmask (an over-range mask would `OverflowException` + hard-quit at load) + relaxed the lint to match
  the engine (a gem/Tent with a use-effect is tunable, not just "Usable"-typed consumables). 14 tests (1547
  total).
- **★ IN-GAME PROVEN (2026-06-13):** Potion `power` retuned 10→1 → it healed **15 in combat** (`Power × 15`,
  `BattleCalculator.CalcHpMagicRecovery`) and **10 out of combat** (the field's `× 10`), down from vanilla 150/100 —
  a single `Power` edit scaling **every** use-context because both the battle script and the field item-use read
  the same `ItemEffect.Power`. (The menu *description* still reads "150 HP" — that's the separate item-text channel.)

### Added — `[[item]] teaches`: the abilities a piece of gear teaches (Items.csv AbilityIds), no DLL (0.9.87, ★ IN-GAME PROVEN)
- FF9's "learn abilities from equipment" core: `[[item]] teaches = ["Soul Blade", "Auto-Reflect"]` (ability **names**,
  or explicit **`AA:`** active / **`SA:`** support tokens) **REWRITES** the item's `Items.csv` `AbilityIds` cell — the
  character can use those abilities while the gear is equipped and masters them by earning AP. Rides the existing
  whole-row `[[item]]` delta (composes with `price`/`sell`/`equippable_by`/BonusId-repoint on one row); `teaches = []`
  clears it.
- **Grounded in the Memoria source:** the `AbilityIds` cell is a **comma-list of `AA:X`/`SA:X` tokens inside one
  semicolon-cell** (no delimiter clash), parsed by `CsvParser.AnyAbilityArray`/`AnyAbility` (`AA:` pooled `/192`,
  `SA:` `/64 + 192`). Names resolve via the kit's existing provenance-clean `abilities` module (live-read of the
  per-character pool CSVs — `AA` = Actions, `SA` = support), canonicalised to tokens via `decode_token(resolve(...))`.
  The AP-to-master *cost* stays on the character pools (the battle/character lane), not the item.
- `content/itemdata.ability_tokens` + the `[[item]]` delta wiring + `abilities.is_token` + `build.validate` (tokens
  checked offline; a NAME only when the pools are reachable — no false positive offline). Base read LIVE in cp1252,
  **no game data committed**. Multi-lens adversarially reviewed (0 blockers): folded a real offline-lint gap (a
  token-SHAPED-but-malformed entry like `AA:nope` was misclassified as a name, so a no-install lint silently
  skipped it — `is_token`/`resolve` now treat any `AA:`/`SA:` prefix as a token and reject a bad index offline) +
  a non-equipment `teaches` no-op guard + the per-character-pool + ambiguous-name caveats in FORMAT.md. 13 tests
  (1536 total). **★ Engine note:** a taught ability only takes effect for a character whose learnable pool already
  contains it (`ff9feqp`/`BattleResultUI.AddAp` match `AbilityIds` against the wearer's pool).
- **★ IN-GAME PROVEN (2026-06-13):** `teaches = ["Soul Blade"]` on Mage Masher (vanilla teaches Detect/What's That)
  → equipping it on Zidane made **Soul Blade** appear in his Skill command + Ability screen (Soul Blade is in
  Zidane's pool); **unequipping removed it** — the falsifiable check confirming it's the item, not pre-mastery.

### Added — `[[synthesis]]`: custom synthesis shops (recipes + opener), no DLL (0.9.86, ★ IN-GAME PROVEN)
- A **synthesis shop** combines ingredient items + gil into a new item. `[[synthesis]] shop = N` + `recipes = [{
  result, ingredients, price }, ...]` emits a `Data/Items/Synthesis.csv` (`FF9MIX_DATA`) delta; the opener is the
  **same `Menu(2, id)`** as a buy shop (reused verbatim from `content/shop.py` — NPC `opens_shop = N` or a standalone
  `zone`). The one whole FF9 item-system the kit had **zero** support for (gap-audit's biggest hole).
- **Grounded byte-for-byte in the Memoria source:** `Synthesis.csv` = `Comment;Id;Shops;Price;Result;Ingredients`
  with `#! UseShopList` (so `Shops` parses as an `Int32[]`), **whole-row merge by Id** (`ff9mix.LoadSynthesis` via
  `EnumerateCsvFromLowToHigh`) → the kit **mints recipe ids above the base max (63)** so a delta only *adds* recipes.
  A shop id opens as **Synthesis iff it is absent from `ShopItems.csv`** (`ff9buy.FF9Buy_GetType`); a shop's recipes
  are every row whose `Shops` contains the id (`ShopUI.InitializeMixList`). So the synth `shop` id must be `>= 32`,
  `<= 255`, and **not** a `[[shop]]` buy id — the build **errors** on that collision (it would flip to a buy shop).
- Ingredient duplicates are preserved (need N copies); `NoItem` dropped; base read LIVE in cp1252, **no game data
  committed**. `content/synthesis.py` + `build._emit_synthesis` (mod-global) + the synth `zone` opener (reuses
  `shop.inject_shop_regions`) + `ModLayout.synthesis_csv` + `config` + `deploy_field` reversible CSV loop +
  `_STARTUP_CSVS` (RELAUNCH note) + `validate()`. Multi-lens adversarially reviewed (0 blockers; folded a real
  `ConfigError`-escapes-the-build fix — also in the `itemdata` sibling — + lint type-guards for a scalar `zone` /
  string `ingredients` + doc/message precision). 21 tests (1520 total).
- **★ IN-GAME PROVEN (2026-06-13):** a custom synth shop (id 50, opened by a press-region `Menu(2, 50)` in a test
  field) opened as a **Synthesis** shop and offered a **net-new** recipe (Mythril Dagger ← Mage Masher + Potion, 50
  gil — not a vanilla combo); synthesizing it produced the item and deducted the ingredients + gil. Confirms the
  minted `Synthesis.csv` recipe row + the buy-vs-synthesis routing (id 50 absent from `ShopItems.csv` → Synthesis).

### Added — quick-win item columns: weapon `category`/`status_index`/`rate` + item `equippable_by` (0.9.85, ★ IN-GAME PROVEN)
- Extends the `[[weapon]]`/`[[item]]` CSV-delta surface (`content/itemdata.py`) with four more stock-moddable,
  no-DLL levers the kit previously only **read** for the Info Hub:
  - **`[[weapon]] category`** — the weapon class (`short-range`/`long-range`/`throw`/`offset`, by name or a 0-255
    `WeaponCategory` bitmask). Adding `throw` makes a weapon eligible for Amarant's Throw. (`Weapons.csv Category`, a Byte.)
  - **`[[weapon]] status_index` + `rate`** — the weapon's status effect: `status_index` selects an existing
    `StatusSets.csv` row (the `add_status[]` table). In Memoria the live consumer is **Soul Blade** (Zidane's Skill,
    for his thief-swords), which applies it directly; the normal-attack "Add Status" path is **dummied**
    (`TryAddWeaponStatus` has no callers), so `rate` (0-100) only feeds custom NCalc formulas (`WeaponRate`).
  - **`[[item]] equippable_by`** — a list of party-character names that **REWRITES** the item's 12 `Items.csv`
    equip-by-character bits (exactly those can equip it; everyone else cleared). Composes whole-row with `price`/`sell`/BonusId.
- Grounded byte-for-byte in the Memoria schema (`ItemAttack.cs` cols Category/StatusIndex/Rate, `ItemInfo.cs` 12-char
  mask, `WeaponCategory`) + the real install CSVs. `category` clamps to a Byte and `rate` to 0-100 (overflow crashes the
  loader / over-applies otherwise); `encode_category`/`encode_characters` validate names. `build.validate` lints bad
  category/character names + an **out-of-range `status_index`** (a KeyNotFound battle-crash, like the Phase-4 trap),
  range-guarded against the install's `Data/Battle/StatusSets.csv`. +15 tests (53 in test_itemdata; **1499** total).
- Closes two deferred item-lane tails (weapon class/status-on-hit + who-can-equip). Still deferred: consumable
  use-effects, synthesis recipes, the gear→ability list, item name/description text, net-new ids (>254, needs a DLL).
- **★ IN-GAME PROVEN (2026-06-13):** `equippable_by = ["Zidane"]` on **Broadsword** (vanilla Steiner/Marcus/Blank
  only) made it appear in Zidane's weapon-equip list. `status_index` on **The Ogre** (a Soul Blade thief-sword,
  re-pointed from Blind to **Mini**, set 10) — using **Soul Blade** in battle visibly shrank the enemy (vs vanilla
  Blind), confirming the on-hit status edit (the live route is Soul Blade, not a plain Attack — the latter is dummied;
  a first test with Venom+Poison killed the weak enemy via DoT before the icon could be read). `category` verified
  byte-correct in the deployed `Weapons.csv`. `FORMAT.md` documents the Soul Blade mechanic.

### Added — lint warns on a verbatim-carried gated door's un-remappable window text (#11) (0.9.80)
- A `[[gateway_carry]]` story-gated door is grafted verbatim, so if it opens its OWN window (e.g. "it's locked")
  the window keeps the DONOR txid — and the carry-text remap only touches `[[object]]`/`[[player_func]]` windows,
  so `--carry-text` can't fix it. `lint_logic` now decodes each carried gateway entry's windows and WARNS when
  it shows donor text, pointing to `--verbatim` (which ships the whole donor `.mes`, so the txid resolves) or
  authoring the line — instead of silently shipping wrong text. Only **2 real fields** (352, 552) hit this; the
  full carry+remap of gateway-entry windows is deferred (low value). +2 tests. This clears the #11 interim.
- **Docs:** `FORK_FIDELITY.md` trued up — #9 marked LANDED+PROVEN, #11 status, and a "small/orthogonal backlog
  is CLEAR" summary (the rest is battle-pillar #6/#13, mitigated cosmetic #8, or `--verbatim`-covered #12).

### Changed — a synth fork now spawns at the donor's real main arrival, not a centroid guess (#9) (0.9.79, ★ IN-GAME PROVEN)
- `extract_field`'s spawn cascade now PREFERS a real per-entrance ARRIVAL position (the player Init's
  `D9(0)/D9(4)` block, where the engine actually drops the player walking in a door) over the donor charPos
  (often a cutscene staging spot) or the c.1 walkmesh-centroid. Among the arrivals valid for the fork (in-bounds,
  on-camera, clear of every trigger zone, in the main walkmesh region) it takes the one nearest the visible
  centroid — the natural main-entrance landing, and FAITHFUL (a coordinate the real field uses). The Dali shop
  fork now spawns at its real entrance `(439,-122)` instead of the centroid `(83,209)`.
- Falls through to the exact c.1 charPos→centroid cascade when no arrival qualifies (a single-spawn field, a
  frame mismatch, or all arrivals off-screen/gated) → **byte-identical** there, so c.1 (in-game proven) and the
  blank/hut paths are preserved. A synth fork still can't reconstruct the per-DOOR table (its gateways are
  retargeted — that's `--verbatim`'s job), but the DEFAULT landing now matches the real field. +1 test.
  ★ **IN-GAME PROVEN** (Dali synth fork on scratch slot 4012): the player spawns at the shop's real entrance.

### Added — fork-report flags per-door player spawn (#9) (0.9.78)
- `eventscan.scan_player_arrivals(eb)` decodes a field's per-ENTRANCE arrival table: a warp sets the entrance
  var `D8:2` then `Field()`, and the target's player Init reads `D8:2` (a bare `05 D8 02 7F` push feeding a
  `0x06` switch) and branches to one `D9(0)/D9(4)/D9(6)` (x/z/face) block per entrance. Returns
  `{reads_entrance, arrivals, distinct}` (read-only; never raises). Grounded in the engine (`EventEngine`
  `JMP_SWITCHEX` 0x06) and verified across fields (Alexandria Main St = 4 blocks; Dali shop = 2 distinct spots).
- `fork-report` gains an **Arrival** line when a field has >1 distinct spawn: it warns that a SYNTH fork
  collapses the table to one `[player] spawn` (you arrive at the same spot via every door) and that `--verbatim`
  ships the real table. This is the #9 fidelity signal — surfaced before you fork. +3 tests.
- **Scope note (honest):** per-door spawn is FAITHFUL under `--verbatim` (it carries the whole player Init). A
  synth fork can't meaningfully *reconstruct* the table because its gateways are RETARGETED — the donor's
  entrance indices don't carry over to a fork's own doors. So the right answer for per-door fidelity is
  `--verbatim`, and the report now points there. (A bounded synth follow-up: use the donor's PRIMARY arrival as
  the default single spawn — a better default than the c.1 walkmesh-centroid — left for a separate in-game tick.)

### Added — equip stat bonuses: `[[equip_bonus]]` → `Stats.csv` / ItemStats (the level-up-growth lever, full authorship), IN-GAME PROVEN (0.9.81)
- Tune an item's **equip stat bonus** + elemental affinity via a partial CSV delta — **no DLL**. New block in
  `content/itemdata.py`: `[[equip_bonus]] name=…` with `speed`/`strength`/`magic`/`spirit` (the 4 growth-stat
  bonuses = `Stats.csv` Dexterity/Strength/Magic/Will — the input the engine's level-up accumulator reads,
  `ff9play.cs:302-305`, ~32 levels per permanent point) + `attack_element`/`guard_element`/`absorb_element`/
  `half_element`/`weak_element` (the 5 affinity bitmask columns). This closes the items-lane gap behind the
  classic FF9 "equip stat-boosting gear before you level" mechanic — the bonus shows immediately in the status
  menu on equip (`elem = base + bonus`) and drives permanent growth.
- ★ **The shared-`Empty`-row footgun, handled.** An item's bonus lives in `Stats.csv` keyed by its `BonusId`,
  but ~100 items share the all-zero `Empty` row 0 — editing it would buff every other no-bonus item. The builder
  detects sharing (counts each `BonusId`'s users from `Items.csv`): an item with a **dedicated** bonus row (used
  by it alone) is edited **in place** (seeded from the base so unchanged columns carry); otherwise it **mints a
  fresh `Stats.csv` row** (id = max existing + 1) **and repoints the item's `BonusId`** in an `Items.csv` delta —
  isolating the change to that one item. The repoint merges into the **same** `Items.csv` row as any `[[item]]`
  price edit (whole-row merge: both channels must ship together).
- Merge model = the same `EnumerateCsvFromLowToHigh` whole-row-wins as Weapons/Armors/Items (confirmed
  `ff9equip.cs:26`); base read LIVE from the install in cp1252; the repo commits **no game data**. Wired
  mod-global (`build._emit_item_data` gained an `equip_bonus` bucket) + `ModLayout.stats_csv` + the `deploy_field`
  reversible CSV loop (+ the RELAUNCH `_STARTUP_CSVS` note) + `validate()` (name-resolves / equippable[best-effort]
  / sets a field / element-names / non-negative) + `ItemStat.is_equippable`. 16 new tests (38 in `test_itemdata`).
  ★ **IN-GAME PROVEN (2026-06-13):** Bone Wrist (id 91) equipped → **Strength +50** (in-place, dedicated row 4);
  Mage Masher (id 2) equipped → **Magic +30** (mint id 176 + Items.csv `BonusId` repoint 0→176) — both confirmed
  in the status menu. **Roadmap #1-6 remain complete; this is the deferred `Stats.csv` follow-up of #6, now
  CLOSED.** RELAUNCH to apply (startup CSV).

### Added — item-data tuning: `[[weapon]]` / `[[armor]]` / `[[item]]` (roadmap #6, the last items-lane item), IN-GAME PROVEN (0.9.77)
- Tune EXISTING item stats via partial CSV deltas — **no DLL**. New `content/itemdata.py` + field.toml blocks:
  - `[[weapon]] name=… power=… elements=[…]` → a `Data/Items/Weapons.csv` delta (ItemAttack Power/Elements).
  - `[[armor]] name=… p_def=… p_eva=… m_def=… m_eva=…` → an `Armors.csv` delta (ItemDefence).
  - `[[item]] name=… price=… sell=…` → an `Items.csv` delta (ItemInfo Price/SellingPrice).
- ★ The engine MERGES these by id low→high **whole-row-wins** (`EnumerateCsvFromLowToHigh`), so a delta = the
  base file's header block (verbatim, incl. the `#!` option flags) + only the patched rows, each COMPLETE. The
  base rows are read LIVE from the user's install (cp1252, byte-preserving — apostrophes in weapon names
  round-trip) and the delta is GENERATED at build time into the mod folder — the repo commits **no game data**
  (the same provenance stance as `itemstats`). A `[[weapon]]` resolves the item → its `WeaponId` (via Items.csv)
  → the Weapons.csv row; `[[armor]]` via `ArmorId`; `[[item]]` by item id directly.
- Wired mod-global at the mod-write stage (`build._emit_item_data`, beside `_emit_shops`) + `ModLayout`
  `weapons_csv`/`armors_csv`/`items_csv` + the deploy CSV loop (`deploy_field.py`, reversibly). `validate()`
  checks name-resolves / right-type (best-effort, needs the install) / editable-field-present / element names /
  non-negative values. Needs a RELAUNCH (item CSVs load at startup, not via F6).
- 22 tests (synthetic-CSV builders, install-free, + install-gated end-to-end + validate). ★ **IN-GAME PROVEN
  (2026-06-13):** a `[[weapon]] name="Dagger" power=88` delta deployed to `FF9CustomMap` → relaunch → the equip
  menu showed the Dagger's Attack jump (base 12 → 88), confirming the whole CSV-delta pipeline (build → emit →
  deploy → merge → engine load) end-to-end. Deferred to a follow-up: weapon Category/status, `Stats.csv` equip
  bonuses + affinity, consumable effects, who-can-equip (`CharacterMask`), and minting net-new item ids (>254 —
  needs the `RegularItem` enum/DLL).

### Fixed — a synth fork no longer stacks a self-positioning NPC into a duplicate pair (#13 a) (0.9.76)
- `scan_objects_verbatim` now **dedups InitObject sites by arg**. `InitObject(slot, arg)` addresses *instance*
  `arg`, so the same `(slot, arg)` emitted twice is one instance re-init'd — in the donor a beat **director**
  fires just one of those sites per beat, but a SYNTH (non-`--verbatim`) fork has no director and would emit
  them all, **stacking identical copies**. Found in-game forking the Dali Weapon Shop: `DAF` (a shop NPC that
  hard-sets its own position via local `D9(0)/D9(4)`, ignoring the arg) is `InitObject`'d twice at arg 0 → a
  stacked pair. The scan now carries it as **one** instance at its real self-set spot `(-226,-241)`.
- Distinct args are a genuine row and are **kept** (field-122 `BBX`: a single entry offset per arg 128/129/130 —
  it self-positions from a `D9` *base* it shifts by the arg, so the old `slot_count==1` self-position guard was
  wrong; replaced by the arg-dedup, which is correct whether the object self-positions or inherits Main_Init D9).
- No effect on `--verbatim` forks (they ship the whole `.eb`, bypassing the object graft). +2 tests (a pure
  inject-then-arm round-trip; an install-gated end-to-end on the real Dali roster). Part of the #13 (c) tail.

### Performance — the test suite no longer re-reads the 68 MB event bundle on every install-gated call (0.9.75)
- **Root-caused the "test suite takes 2 hours" report.** The full suite is healthy: **1348 passed in ~146s** serially.
  The 2-hour run was resource **contention** — while pytest (pinned to one core) ran, concurrent background work
  hammered all cores AND re-read the large `p0data*.bin` bundles, thrashing the OS file cache so each of the
  ~150 install-gated `UnityPy.load(p0data7)` calls became a *cold* 68 MB physical read instead of a warm one.
- **Fix (hardens that failure mode):** `extract._load_env()` — a bounded-LRU in-process cache of the loaded
  STATIC base-game bundles, keyed by absolute path. `extract_event_script` / `extract_mapconfig` /
  `EventBundle` / `find_field` now reuse one parse of the hot event bundle instead of re-loading it per call
  (~5x on that pattern; the cache holds exactly the bundles in flight, the hot one staying resident by recency).
  Mirrors the existing `_load_mod_bundle` but kept SEPARATE — mod-folder bundles mutate on deploy, base bundles
  never do. `build_field_index` (force-scan, disk-cached) and `_events_bundle` (one-time detection) are untouched.
  This also speeds real CLI usage (a fork reads the event bundle for `.eb` + MapConfig). +2 tests.
- **Parallelism (optional):** added `pytest-xdist` to the `dev` extra. `py -m pytest -n 6` runs the suite in
  ~56s (2.6x) and stops a single pytest process being starved under load. ~6 workers beats `-n auto`/12 (66s) —
  the install-gated tests are disk-bound on the shared bundles, so too many workers re-contend on I/O.

### Fixed — a fork no longer spawns the player in a walled-off walkmesh pocket (#13 c.1) (0.9.73, ★ IN-GAME PROVEN 0.9.75)
- `import` now keeps the auto-picked `[player] spawn` in the **main walkable region**. A real field's stored
  spawn (`.bgi` charPos) is often a cutscene staging spot — for a shop it sits BEHIND the counter, a small
  walkmesh component walled off from the customer area, so a fork stranded the player there with no way out
  (found in-game forking the Dali shop). The spawn cascade now computes the walkmesh's connected components
  (`BgiWalkmesh.tri_components()`, by triangle neighbour links) and restricts every spawn candidate to the
  component with the most on-camera verts — so charPos is accepted only if it's in that main region, else the
  fallback centroid is taken from it too.
- ★ Offline-confirmed on the Dali shop: its walkmesh splits into a 21-tri customer area + a 7-tri behind-counter
  pocket; the spawn moved from `(-489,-348)` (pocket) to `(83,209)` (the customer area). **No-op on a
  single-region walkmesh → byte-identical** (the common case is untouched). +3 tests (`test_spawn`, incl. an
  install-gated Dali main-region assertion). This is part of the #13 (c) diorama tail.
- ★ **IN-GAME PROVEN** (fork deployed to scratch slot 4012): the player now spawns in the customer area, free to
  walk and reach the exit — no longer trapped behind the counter.

### Added — save-item editor: VANILLA (main-block) AP / ability editing, IN-GAME PROVEN (0.9.72)
- The AP / ability-mastery editor now reaches **vanilla (no-extra) saves** too, via the encrypted main block's
  old-format `pa` array — completing AP across both save kinds (the 7→7b pattern, now 8→8b).
- ★ **Layout finding (derived from the alpha-sorted SharedDataBytesStorage schema, empirically confirmed):** the
  244-byte old player struct (base `basis@5751`) lays out `…equip@5784 exp info@5793 level max name(128) pa@5936
  sa@5984…`, old-slot 8 ending exactly at `rareItems@7947`. A vanilla save's `pa@5936` decodes to each char's
  base-pool AP (Flee@40, Soul Blade@35, …), and the per-slot `info.menu_type@5793` gives the live preset. The
  vanilla saves use the **vanilla pool order**, so by-name resolution is correct on them.
- **`save_items.set_main_ap(container, block, character, ability, value)`** writes the `pa` byte(s) for one
  old-slot — `all` (mod-safe, every position) or a single ability by name/`AA:X`/`SA:X`/id resolved to its pool
  index. + `read_main_abilities` + `main_report`/`ItemReport.abilities` (so `items-inspect` shows AP on vanilla
  slots) + **`set_ap_in_save`** dual-write (extra-first, vanilla → main only) + `render_ability_dual`. CLI
  `items-set-ap` on a container now dual-writes; GUI Abilities works on vanilla slots.
- 5 new tests (synthetic container + install-gated by-name); 1336 suite green. Offline-validated on a temp copy
  of the real container's vanilla block (single by-name `Sacrifice` 28→55, `all max` 21/48→48/48, scoped to only
  that block + that slot's `pa`).
- ★ **IN-GAME PROVEN (2026-06-13):** `items-set-ap … Zidane all max --slot 0 --save-no 0 --apply` on the VANILLA
  slot 1/save 1 → loaded → Zidane's Ability menu showed every ability mastered (`21/48` → `48/48`). Note the old
  format caps at **48** abilities/char (the modern Moguri `pa_extended` carries 50 — see 0.9.71); each `all` masters
  everything that save's format can hold.

### Added — save-item editor: AP / ABILITY-MASTERY editing (the "AP unlocks" the user asked about), IN-GAME PROVEN (0.9.71)
- A new editor for a character's **ability AP / mastery** — set the AP a character has earned toward an ability
  (so an active ability becomes permanently usable, or a support ability becomes equippable). Memoria-extra-only
  for now (a vanilla no-extra save's main-block AP is a follow-up, like the stat editor's 7→7b).
- **`abilities.py`** (new, provenance-clean like `itemstats`/`keyitems` — ships nothing): the mod-agnostic
  `AA:X`/`SA:X` ↔ integer `abil_id` codec (matches Memoria `CsvParser.AnyAbility`/`ff9abil` exactly, round-trips
  even mod high-pool ids), plus a **best-effort** name + AP-to-master lookup read live from the install's
  per-character pool CSVs (`Data/Characters/Abilities/<Preset>.csv`). A modded id with no base entry degrades to
  its `AA:X`/`SA:X` token (no crash) — important because the user runs Moguri (custom ability pools).
- **`save_items.set_ap_extra(character, ability, value)`** — `ability` = a name / `AA:X` / `SA:X` / numeric id /
  `all`; `value` = `master` (the requirement, or AP_CAP=255 when unknown) / `max` / `forget` / a number. Edits
  the EXTRA's `players[].pa_extended` (`{id,cur}`), keyed by `info/menu_type` = the `CharacterPresetId`. The save's
  own `pa_extended` is the source of truth (the engine keys AP by pool entry), so it's correct on a modded save.
  Same safety as every prior writer: GATE 1 + a scoped diff (only that player's `pa_extended` moves) + atomic +
  post-write confirm + dry-run default + `.bak`. + `read_abilities` (mastered / in-progress, in `items-inspect`)
  + `render_ability_write`. CLI **`items-set-ap`**; GUI **Abilities** section; **`items --abilities`** lists which
  ability names resolve per character.
- **Adversarial-review hardening** (a 3-lens engine-fidelity / python-safety / integration workflow, 4 findings,
  all folded in + regression-tested): a save with `pa_extended` but no `menu_type` now degrades instead of
  crashing the whole report; a **duplicate** `pa_extended` id sets EVERY match (the engine loads the last) so the
  edit is deterministic; the bulk `all` summary classifies mastery from the resolved per-ability outcome and shows
  `changed/pool-total`.
- New `abilities.py` tests + ability write tests (synthetic + install-gated real-save dry-run); 1307 suite green.
- ★ **IN-GAME PROVEN (2026-06-13):** `items-set-ap <save> Zidane all max --apply` on the real Moguri save →
  loaded → Zidane's Ability menu showed **every ability mastered** (filled gem icons; 0/50 → 50/50). Confirms the
  `pa_extended` AP write loads and masters in-game, names/tokens resolve on a modded pool, and the mod-robust
  `max` force-master works.

### Added — battle-tuning Phase 6c-iii: the enemy-AI LINTER + the `[[scene.ai_function]]` build surface (0.9.72)
- **`battle/ailint.py`** — the CAPSTONE of the battle-AI stack: validate a scene's enemy AI OFFLINE (the "I can't
  see the game" superpower applied to AI). `lint_ai(eb, atk_count=)` runs SOUND checks — a shipping scene must lint
  CLEAN: **decode** (every function decodes to its boundary), **jump bounds** (every relative jump lands on an
  instruction inside its function), **reachable terminator** (a forward reachability walk flags a path that falls
  through the END without a RET/terminator — trailing NOP padding after a RET/loop is correctly UNREACHABLE), and
  **Attack index** (an immediate Attack operand `< the scene attack count`). ★ **Soundness proven by a 562-scene
  sweep: ALL 562 shipping battle scenes lint CLEAN (0 false positives).** CLI **`battle-ai --lint <scene>`** (exit 1
  on any issue).
- **`battle/aiauthor.py` + `build.py`** — the declarative **`[[scene.ai_function]]`** surface: a `battle.toml` adds
  or replaces an enemy-AI function (`entry` / `tag` / `source` / `replace`), assembled (6c-ii `cmdasm`) + spliced at
  build, applied per-language AFTER `[[scene.ai_patch]]` (length-changing follows same-length). The build VALIDATE
  hook now lints the **composed** (`ai_patch` + `ai_function`) eb — exactly what ships.
- ★ A 3-lens adversarial review (it independently re-ran the 562-sweep) confirmed the design SOUND and found + fixed
  four real defects: **(HIGH)** `_jump_target` decoded `JMP_IFNOT` (0x02) *signed*, but the engine reads it
  **unsigned** (`beq`/`getUShortIP`, unlike `bra`/`bne`) — so the backward-`JMP_IFNOT` fault the linter promises to
  catch was *missed*; now decoded unsigned (it lands out of bounds → flagged). **(MEDIUM)** the validate hook linted
  the *un-patched* donor, not the composed eb the build ships → now composes `ai_patch`+`ai_function` and lints the
  result (catches an `ai_patch` that repoints a jump/Attack-index out of range). **(LOW)** the terminator set
  `{RET, TerminateEntry}` missed the engine's other `adFin()` path-enders (`GameOver` 0xF5, `STOP`, `Battle`, …) →
  a branch ending in one was false-flagged; the set is widened and SHARED with `aiauthor`'s authoring guard so they
  never drift. **(LOW)** an out-of-`u16`-range `tag` crashed with a raw `struct.error` → now a clean `AiAuthorError`.
  44 tests (`test_ailint` + `test_aiauthor` + `test_cmdasm`). **Phase 6c COMPLETE** — the kit now reads, tunes,
  authors, *and* validates the whole enemy-AI stack on stock Memoria.

### Added — save-item editor: vanilla (main-block) STAT editing + the GUI on vanilla slots, IN-GAME PROVEN (0.9.69)
- The stat editor now reaches **vanilla (no-extra) saves** too, and the GUI's Stats control works on them —
  completing the stat editor across both save kinds (and the GUI across all five editors on every slot).
- ★ **Layout finding (empirical, verified vs the extra on all 9 players):** the old-format player struct stores
  `basis` (displayed, Bytes) at **5751** and `bonus` (the equipment accumulator, UInt16 LE) at **5759**, +244·old-slot;
  per-stat byte offsets basis `{dex:0, mgc:5, str:6, wpr:7}`, bonus `{dex:0, mgc:2, str:4, wpr:6}`.
- **`save_items.set_main_stat(container, block, character, stat, target)`** — writes the basis Byte + bonus UInt16
  (same target-stat / formula-delta model as `set_stat_extra`), scoped to those ≤3 bytes, validate gate + atomic +
  backup + confirm. + `read_main_stats` + `main_report`/`ItemReport.stats`. **`set_stat_in_save`** dual-write; CLI
  `items-set-stat` on a container dual-writes; `render_stat_dual`. GUI `_edit_stat` now uses the container path.
- 6 new tests. ★ **IN-GAME PROVEN (2026-06-13):** set Zidane's Strength 27 → 99 on the VANILLA slot 1/save 1's
  main block → loaded → the status menu showed 99 (gil + key items + other slots untouched). **The #5 save-item
  editor is now complete: gil/items/equipment/key-items/stats on BOTH Memoria and vanilla saves, via CLI and GUI.**

### Added — save-item editor: the equipment-driven STAT editor (`items-set-stat`), IN-GAME PROVEN (0.9.68)
- Edit a character's permanent growth stat — Speed / Strength / Magic / Spirit — the hidden "level up in stat
  gear" system. ★ **Engine formula (`ff9level.cs`):** `displayed = base + level·growth + (bonus >> 5)`, capped per
  stat (Speed/Spirit 50, Strength/Magic 99); `bonus` is the equipment accumulator, `basis` is the displayed
  value (recomputed from `bonus` only at level-up; on LOAD the engine runs `FF9Play_Update`, not `_Build`).
- **`save_items.set_stat_extra(extra, character, stat, target)`** — the "set target stat" model: writes BOTH
  `players[].basis.<field>` (shows immediately) AND `players[].bonus.<field>` (holds the value through level-ups).
  ★ The needed bonus comes from the **formula delta** — `new_bonus = (target − old_basis + (old_bonus>>5)) << 5` —
  which cancels the base/growth terms, so **no game-data table is needed**. Scoped to that one player's
  basis+bonus; GATE 1 + atomic + backup + post-write confirm + dry-run. + `read_stats` + `render_stat_write`.
- CLI **`items-set-stat <save> <character> <stat> <value>`**; GUI gains a **Stats** control (who / stat / value →
  Preview / Apply). 6 new tests.
- Scope: extra-only (Memoria saves — the load-authoritative store). The vanilla **main-block** stat editor is a
  follow-up — the offsets are already mapped (basis @ 5751, bonus @ 5759 UInt16, + 244·old-slot).
- ★ **IN-GAME PROVEN (2026-06-13):** set Zidane's Strength 21 → 99 on slot 1/save 3 → loaded → the status menu
  showed Strength 99 (Vivi + gil untouched). The displayed value + the bonus accumulator both set correctly.

### Added — battle-tuning Phase 6c-ii: the enemy-AI COMMAND assembler + branch insertion (0.9.70)
- **`eb/cmdasm.py`** — assembles a whole INSTRUCTION (and a BLOCK of them), the next step after 6c-i's expression
  assembler: the body of a NEW enemy-AI branch. It mirrors `disasm.read_code`'s byte-walk step for step (the `0xFF`
  extended page, the `argFlag` byte for `op >= 0x10`, the forced-expr `SET`=0x05, the stream-read operand count for
  the variable ops 0x06/0x0B/0x0D + the count-prefixed 0x29), so it reproduces the exact bytes `read_code` decoded.
  Expression operands (`{ … }`) go through 6c-i's `exprasm.assemble`; immediates are LE of the opcode's `argsize`.
- **`assemble_block`** adds the authoring layer: `label:` lines + symbolic jump targets (`JMP done`,
  `JMP_IF {expr} loop`) resolved in a two-pass walk to the relative offset the engine reads (instruction sizes are
  known up front — a jump immediate is always 2 bytes — so offsets precede the targets).
- **`battle/aiauthor.py`** — the bridge: `add_ai_function` / `replace_ai_function` assemble a branch and splice it
  into a forked battle `.eb` via the EXISTING byte-safe length-changing primitives (`eb.edit.add_function` grows the
  func table + fixes every `fpos` and later-entry offset; `replace_function_body` swaps a body of any length). The
  first LENGTH-CHANGING AI edit. CLI **`battle-ai --asm-block`** previews a block → bytes + a re-disasm proof.
- ★ A 3-lens adversarial review (decode inversion · block/jump layout · insertion safety) confirmed the layout math
  and the relative-jump survival of the splice, and found + fixed two real defects: **(HIGH)** the engine has *no
  per-function length bound*, so a branch that doesn't end in a flow terminator runs the IP off into adjacent
  bytecode at runtime — `aiauthor` now REQUIRES the body to end in `RET` (0x04) or `TerminateEntry` (0x1C);
  **(MEDIUM)** the engine reads `JMP_IFNOT` (0x02, `beq`) offset **unsigned** while `JMP`/`JMP_IF` (`bra`/`bne`) are
  signed, so a *backward* `JMP_IFNOT` would execute as a ~64KB forward jump — now rejected with a clear error.
  Plus a bracket-imbalance guard in the operand splitter. The strongest test walks the **real EF_R007 AI** and
  asserts every instruction *and* every function assembles back byte-for-byte, and that `add_ai_function` on the
  shipping Goblin AI re-parses with every other function + later entry byte-intact. 35 tests
  (`test_cmdasm` + `test_aiauthor`). **Phase 6c next (6c-iii):** a battle linter (valid AI tags, an Attack index in
  range, a reachable RET) + the declarative `[[scene.ai_function]]` build surface.

### Added — save-item editor: vanilla key items (main-block `rareItems`) + the GUI key-item control, IN-GAME PROVEN (0.9.66)
- Completes key items: a **vanilla (no-extra) save's key items** are now editable, and the **GUI** gains a
  Key-items give/remove control — so the #5 editor covers **every data type on every save kind**.
- ★ **Layout finding (empirical):** the old-format main block holds key items in a **64-byte `rareItems`
  bitfield at offset 7947** — 2 bits per item (obtained at the even bit, used at odd), 256 items (item `j` →
  byte `7947 + j//4`, shift `(j%4)*2`). Verified byte-stable: the vanilla blocks decode to sensible key-item
  sets (16 / 21 items). (The probe memory's "rareItems@7947 was WRONG" was a save with zero key bytes there —
  the *offset* is right.)
- **`save_items.set_main_keyitem(container, block, keyitem, *, obtained, used)`** — flips exactly the item's 2
  bits (validate gate · scoped byte-diff: only that byte moves · atomic · backup · position-aware confirm ·
  dry-run). + `read_main_keyitems` + `main_report` now carries key items. **`set_keyitem_in_save`** dual-write
  (main `rareItems` + extra `rareItemsEx`); CLI `items-set-keyitem` on a container dual-writes; `render_keyitem_dual`.
- **GUI** (`apps/ff9_items.pyw`): a "Key items" section (name → Preview / Give / Remove), dual-write on a
  container (handles vanilla), extra-only on an extra-save. 8 new tests.
- ★ **IN-GAME PROVEN (2026-06-12):** gave Falcon Claw to the VANILLA slot 1/save 1's main block → loaded → it
  shows in the Key Items menu (16 → 17), gil/equipment intact. **The #5 save-item editor is now 100% complete** —
  every data type (gil, items, equipment, key items) on every save kind (Memoria + vanilla), via CLI and GUI.

### Added — battle-tuning Phase 6c-i: the enemy-AI EXPRESSION ASSEMBLER (`eb/exprasm.py`) (0.9.67)
- **`eb/exprasm.py`** — the keystone of Phase-6c new-branch *authoring*: the exact **inverse of the Phase-6a
  disassembler** (`disasm.pretty_expr`). Authoring new enemy-AI logic (a phase-switch condition, a counter
  trigger) means writing the RPN **expression token stream** the engine evaluates; this `assemble()`s that stream
  from the same readable `{ tok tok … }` form the disassembler prints. The load-bearing property is the **round
  trip**: `assemble(pretty_expr(bytes)) == bytes` (byte-exact for canonical bytecode) and
  `pretty_expr(assemble(text)) == text`.
- Each token maps to one encoded token (the inverse of every `pretty_expr` branch): a bare op mnemonic
  (`B_LT`/`B_CURHP`) → its `op_binary` byte; `const(N)` → `B_CONST` (0x7D + 2 LE bytes); `const4(N)` → `B_CONST4`
  (0x7E + 4 LE bytes — `pretty_expr` now prints `const4(N)` distinctly so the round trip is exact); `Source.Type[i]`
  → the `0xC0` variable token (the engine's *minimal* encoding: a 1-byte index, or the `0x20` long-bit + a 2-byte
  LE index when `i > 0xFF`); `B_SYSVAR[i]`/`B_SYSLIST[i]`/`obj(uid=U).f[F]`/`B_MEMBER(i)`/`B_PTR(i)` → their
  operand tokens; `B_EXPR_END` (0x7F) terminates. Provenance-clean (only the open-source op/enum **names**).
- CLI **`battle-ai --asm "{ … }"`** assembles an expression → its bytes + a re-disassembly proof (no scene needed).
- ★ A 3-lens adversarial review (round-trip inversion · engine fidelity vs `EBin.cs` · robustness/API) confirmed
  the engine byte-layout matches `EBin.cs` exactly (var bits, long-index LE, `B_OBJSPECA` uid/field order, const
  widths) and found + fixed: **(HIGH)** the `opXX` fallback was a back-door — a numeric `op7D`/`opC4` assembled to
  a *bare* byte that desynced the stream and mis-executed in-engine; `assemble` now accepts `opXX` only for a
  genuinely-unnamed pure-operator byte (`< 0xC0`, not in the op table) and rejects a named or variable byte with a
  "write it by name / in operand form" message. **(LOW)** the CLI re-disasm dumped a raw `IndexError` traceback on
  a non-re-parsing stream — `assemble()` now **self-verifies** (re-parses its own output, raising `AssembleError`
  unless it consumes exactly every byte), making the round trip a *library-boundary invariant* (this also closes
  the CLI crash and a mid-stream-`B_EXPR_END` edge). **(consistency)** `const`/`const4` now range-check (honoring
  `assemble_token`'s docstring + matching the var/sysvar siblings + the 6b `B_CONST4` cap) instead of silently
  masking a typo. The strongest test walks the **real EF_R007 AI** and asserts `assemble` reproduces the shipping
  game's expression bytes byte-for-byte; + a 256-byte `opXX` sweep. The long-form-small-index and `0x80-0xBF`
  divergences were reviewed and confirmed out-of-scope (the engine's own encoder never emits those). 35 tests
  (`test_exprasm`). **Phase 6c next:** the command assembler + length-changing `add_function` branch insertion + a
  battle linter (this assembler is the prerequisite).

### Added — battle-tuning Phase 6b: same-length enemy-AI constant patches (`[[scene.ai_patch]]`) (0.9.64)
- **`battle/aipatch.py`** — the first AI *authoring* step (read = Phase-6a `battle-ai`). An enemy's AI is the
  per-scene `EVT_BATTLE_*.eb` bytecode; the safest edit is a *literal* one — change a numeric CONSTANT in place
  (an HP threshold a phase-switch compares, the attack index a turn selects, a `Wait` count) **without moving any
  byte**: no `fpos`/entry-table fixup, byte-accurate by construction (the eb-codec identity holds), like
  `scene_data`'s surgical raw16 patch.
- `constant_sites` locates every patchable numeric constant (command immediates + `B_CONST`/`B_CONST4` expression
  literals) with its byte offset + width — a walk that **mirrors the proven `read_code`/`pretty_expr` byte-for-byte**
  so a reported offset is exactly where the constant lives. `battle-ai <scene> --sites` prints them (224 on the
  real EF_R007). `[[scene.ai_patch]]` (in `battle.toml`) cites `at = <offset>`, a required `old`-value guard (a
  stale/wrong offset fails LOUD, never corrupts a byte), and `new` (must fit the same width). Applied to the forked
  eb at build, per-language at the same offset (the bytecode is language-identical).
- Reaches NUMERIC LITERALS only (the "same-length literal patch" tier); structural changes + an expression
  assembler are Phase-6c. Read-the-AI-first is mandatory — you cite the offset the disassembler prints.
- ★ A 3-lens adversarial review (site-walk fidelity vs the decoders · patch safety · build wiring) found and
  fixed: a **3-byte (Int24) immediate** crashed the patcher with `KeyError` (the width map had only 1/2/4 → now a
  generic little-endian width-N pack); a truncated/corrupt eb leaked a raw `IndexError` (now a clean
  `AiPatchError`, mirroring the read path); and `B_CONST4` is **masked to 26 bits** in-engine so a too-large `new`
  would silently change in-game (now per-site capped). The B_CONST signedness path was confirmed benign
  (byte-faithful round-trip). 9 tests (`test_aipatch`) + a real-donor round-trip; *in-game proof is the human step.*

### Fixed — a synthesized fork no longer carries cutscene WARP-directors (#13b), IN-GAME PROVEN (0.9.62)
- A non-`--verbatim` fork's object carry (`content.object.graft_objects`) now SKIPS cutscene **warp-directors** —
  an object whose kept LOOP (tag 1) fires `Field()`. Carrying one renders it as a STACKED, DUPLICATE actor
  (object-carry treated the director as a standing NPC) — the #13 stacked-spawn symptom — and its gated `Field()`
  warps could fire if its phase advanced. Empirically the Dali Weapon Shop's director was carried
  `graft_safety='clean'` with all 13 `Field()` ops in its loop. New `object._loop_warps()`;
  `graft_objects(..., out_skipped=[])` collects the dropped directors' donor ids.
- ★ **IN-GAME PROVEN (2026-06-12):** an A/B of synth Dali-shop forks (4012 = fixed, 4013 = a monkeypatched
  buggy control that keeps the director) — the buggy fork shows **2 shopkeepers** (the real one + the director
  rendered on top), the fixed fork shows **1**. (The warp itself didn't fire — the director's phase was idle at
  the entered beat — so the observable harm is the stacked duplicate, the canonical #13 case.)
- Deliberately NARROW (`Field()` only, checked on the carry_tags-filtered bytes): an `init_only` object whose loop
  was already dropped still renders, and phase-switch-only animated props + the save-Moogle (no LOOP `Field()`) are
  UNAFFECTED — the proven prop/save-point/player-graft carries keep working. `--verbatim` keeps directors whole.
- This is #13's last code piece (after the roster-by-beat analyzer): a synth fork of a story-event field is now a
  clean static diorama instead of a stacked-cutscene mess. +6 tests (`test_object_graft`, incl. an install-gated
  Dali assertion). Remaining #13 tail: the multi-instance self-positioned + per-door spawn sub-bugs (e.g. the
  synth fork still spawns the player behind the shop counter — the donor's cutscene staging spot).

### Added — battle-tuning Phase 6a: the enemy-AI disassembler view (`battle-ai`) (0.9.63)
- **`battle/battleai.py` + CLI `battle-ai <scene>`** — the read-only "see the enemy's AI" step (the foundation of
  Phase 6, per the doc's staging: disassembler → same-length patches → new branches). A battle scene's
  `EVT_BATTLE_*.eb` is the same bytecode container + `EventEngine` interpreter as a field script, so the kit
  already round-trips and decodes it — what was missing to *read* enemy AI is the vocabulary:
  - **`eb/_exprtable.py`** — the `op_binary` expression-operator table (all 128 values, transcribed from the
    open-source `EBin.cs`) + the variable-token decode: a `0xC0+` token → `Source.Type[index]` (so a story-flag
    read shows as `Global.Bit[8512]` — the kit's `GLOB_BOOL` encoding — and an enemy-HP read as `B_CURHP`).
  - **`eb/disasm.pretty_expr`** — names an expression token stream (`op{52}` → `B_CURHP`), mirroring the proven
    `read_expr`'s byte-walk exactly.
  - **`battleai.disassemble_ai`** — walks the eb: entry 0 = Main_Init (spawn/AI binding), entries `1..TypCount` =
    per-enemy-type AI, functions by TAG (Main/Counter/ATB/Dying), each instruction with named commands
    (`SET`/`JMP_IF`/`InitObject`/`BTLCMD`, incl. a control-opcode overlay `OP_NAMES` leaves unnamed) + annotated
    expressions.
- Read-only + offline; provenance-clean (only the open-source opcode/operator NAMES committed; donor bytes read
  live, never committed). Already reads the real EF_R007 Goblin AI cleanly.
- ★ The load-bearing property is **byte-walk parity**: a parity test asserts `_decode_func_pretty` yields the SAME
  instruction offsets as the proven `read_code` across every AI function of a real donor — so the annotated view
  can never mis-align. 10 tests (`test_battleai`), verified by a 3-lens adversarial review (table vs `EBin.cs`,
  byte-walk fidelity, presenter/provenance) which found only a low truncated-eb `IndexError` (guarded — a legible
  `<malformed>` note). *Authoring (Phase 6b: same-length constant patches) is next.*
### Added — save-item editor #5 step 6: KEY/important items (`items-set-keyitem`), IN-GAME PROVEN (0.9.65)
- The last data type: **give / remove a key (important) item by name** in a Memoria save. FF9 has no symbolic
  enum for key items, so names are read **LIVE** from `<install>/StreamingAssets/Text/<lang>/KeyItems.strings`
  (`"$keyNNNN" = "Name"`), cached in-memory, **shipping/committing nothing** — the same provenance-clean live
  pattern as `itemstats`. New `ff9mapkit/keyitems.py` (`resolve`/`name_of`/`available`; 80 key items, ids 0-79).
- **`save_items.set_keyitem_extra(extra, keyitem, *, obtained=True, used=False)`** — edit the extra's
  `40000_Common/rareItemsEx` list (each entry `{id, obtained, used}`; ★ the bools are VALUE strings
  `"True"`/`"False"`, NOT Bool leaves — `bool("False")` would be a bug, so the text is compared). Both flags False
  removes the entry; otherwise add (ascending-id) / update. Same safety (GATE 1 + scoped-change check (only
  `rareItemsEx` moves) + atomic + backup + post-write confirm + dry-run). `read_keyitems` + `ItemReport.keyitems`
  + the inspect/render now show held key items; CLI **`items-set-keyitem <save> <name> [--remove] [--used]`**.
- Scope: key items are EXTRA-only here (the load-authoritative store, Memoria saves). Main-block `rareItems`
  (the 64-byte 2-bit bitfield, for vanilla saves) + a GUI key-item control are follow-ups. 7 new tests; 1200 green.
- ★ **IN-GAME PROVEN (2026-06-12):** gave Falcon Claw to slot 1/save 3 (a Memoria save with 0 key items) → loaded
  → it shows in the Key Items menu (gil/items untouched). **The #5 editor now covers every save data type** — gil,
  regular items, equipment, and key items.

### Added — fork-report ROSTER-BY-BEAT: which carried cast a story-event director spawns at each beat (#13) (0.9.60)
- `fork-report` now prints a **Roster by beat** table for rotating-cast (story-event) fields: for each
  ScenarioCounter beat the field gates on (plus a scenario-zero baseline), the carried NPCs/actors the director
  actually spawns at that beat — so you can pick the right `[startup]` beat OFFLINE instead of deploy-and-warp.
  Built on a small **symbolic walk of Main_Init** (`_spawned_slots`): it evaluates only the ScenarioCounter
  comparisons that drive a conditional jump (decoded by `_sc_cond`/`_eval_cmp`), follows forward jumps incl. the
  unconditional 0x01 (correctly stepping over an if/else's else-branch), and collects the `InitObject` slots
  reached — handling dispatch chains, if/else, and nesting (vs naive range-containment). New `ForkReport.beat_roster`.
- This operationalizes the #13 finding (verbatim + `[startup]` shows a beat-correct rotating roster): the table
  REPRODUCES the in-game observation OFFLINE — on the real Dali Weapon Shop (354) the cast is `DAC`+`DAF*` at
  Dali (2600), gains `DAW` at Iifa/Alexandria (6990/8800), and is wholly different (`HUF`/`HUM`) at Pandemonium
  (11090). Honest about its limits (flag gates assumed present, compound/looping gates run once, a director's
  OWN per-beat model swap not traced — all surfaced in the output caveat). Reviewed by a 2-lens adversarial +
  verify pass (the variation gate now compares (slot, model); backward-jump fall-through pinned by a test).
- +9 tests (`test_forkreport`): the condition decode, the symbolic walk (dispatch chain / if-else / non-SC
  fall-through / backward-jump), and an install-gated Dali rotation assertion.

### Added — battle-tuning Phase 5b: support-ability gem-cost deltas (`[[ability_gem]]`) (0.9.61)
- **`[[ability_gem]]` → `Data/Characters/Abilities/AbilityGems.csv`** (in `battle/characterdelta.py`) — re-cost a
  support ability's gem requirement, the build-economy balance lever (cheaper Auto-Haste = stronger builds). A
  per-SupportAbility **partial delta** (`EnumerateCsvFromLowToHigh`, `ff9abil.cs:409`): only the changed rows are
  emitted, the base supplies the other 63. `ability` resolves a SupportAbility by name (the enum `AutoHaste`, the
  CSV display `Auto-Haste`/`HP+10%`, or a 0-63 id) via a committed name table; `gems` sets `GemsCount`.
- The **`#! IncludeBoosted`** option line + the Boosted column are preserved verbatim (load-bearing: the engine
  parses Boosted only when that option is present). Range-checked offline; the SupportAbility name table is the
  open-source Memoria enum (provenance-clean), gem **values read live, never committed**.
- Wired mod-global into `build`/`validate_field`/`deploy_field`. CLI **`ability-gems`** lists the abilities +
  live costs (the tuning targets; `-f` filter).
- ★ A 3-lens adversarial review (engine source + the live 64-row CSV) verified the name table (64/64 vs the
  enum), the `#! IncludeBoosted`/Boosted handling, the partial-merge + coverage gate, and provenance, and caught
  one real gap: the CSV display name **"Odin's Sword"** (the only possessive) normalized to `odinssword` ≠ the
  enum `OdinSword`→`odinsword`, so copying the catalog-printed name failed to resolve — aliased (now every one of
  the 64 displayed names round-trips). 6 tests + a real-install smoke; *in-game proof is the human step.*

### Added — save-item editor #5 step 4b: main-block EQUIPMENT (vanilla saves fully editable), IN-GAME PROVEN (0.9.59)
- The last deferred piece: a **vanilla (no-extra) save's EQUIPMENT** is now editable, completing the editor.
- ★ **Layout finding (empirical):** the old format stores **9 player structs of 244 bytes**, each with a
  **5-BYTE equip array** `[weapon,head,wrist,armor,accessory]` at `MAIN_EQUIP_OFF=5784 + 244·old_slot` — verified
  byte-stable (all 9 players decoded correctly vs the extra on the autosave, and to valid loadouts on both
  vanilla blocks). The 9 old-slots: 0-4 = Zidane/Vivi/Garnet/Steiner/Freya, 8 = Beatrix; **slots 5/6/7 are SHARED
  by Quina/Eiko/Amarant and their story temp-replacements Cinna/Marcus/Blank** (`SelectOldSaveSlot`) — the
  GUI/inspect shows each slot's current gear so you target the right one.
- **`save_items.set_main_equip(container, block, character, slot, item)`** — set one of a character's 5 equip
  bytes (`character` = CharacterId / name / Cinna·Marcus·Blank → old-slot; `item` = name/id or `empty`/255).
  Same proven safety (validate gate · scoped byte-diff: exactly one byte moves · atomic · backup · position-aware
  confirm · dry-run). Plus `read_main_equipment` + `main_report` now carries the 9 players' equipment.
- **`save_items.set_equip_in_save`** dual-write orchestrator (extra keyed by CharacterId/12, main by old-slot/9 —
  resolved independently); CLI `items-set-equip` on a container dual-writes; `render_equip_dual`. The **GUI** now
  enables the Equipment editor on vanilla slots (was refused).
- A focused adversarial-verify workflow reviewed it (3 doc-staleness findings, all folded in). 18 new tests; 1172
  suite green.
- ★ **IN-GAME PROVEN (2026-06-12):** on the vanilla slot 1/save 1 — Steiner weapon→Excalibur + Ribbon accessory,
  and **Quina (an active-party member at the SHARED old-slot 5) weapon→Gastro Fork showed in-game** (also proving
  the shared slot-5 mapping correctly targets Quina, not Cinna). **The #5 save-item editor is now COMPLETE and
  fully proven** — read+write gil/items/equipment on both the Memoria extra and the encrypted main block (vanilla
  saves), via CLI and GUI. Only key/important items (the 2-bit `rareItems` bitfield) remain deferred.

### Added — save-item editor #5 step 4b cont.: main-block ITEMS + GUI vanilla-save editing, IN-GAME PROVEN (0.9.57)
- Completes editing a **vanilla (no-extra) save** — now its **inventory** is editable too (gil landed in 0.9.56),
  via both the CLI and the GUI.
- **`save_items.set_main_item(container, block, item, count)`** — set an item's count in the main block's 256-pair
  array (count 0 removes → clean `{0,255}` padding; updates in place / adds at the first free slot, reserving the
  last as the padding terminator; clamps 99; `NoItem` rejected). Same safety as `set_main_gil`: validate gate, a
  **scoped byte-diff** that only item-array bytes may move, atomic write, timestamped backup, a **position-aware**
  post-write confirm, dry-run default. Plus `read_main_inventory` (collects all live stacks, tolerating the
  count==0 mid-list gaps FF9 leaves) + `main_report`.
- **`save_items.set_item_in_save`** dual-write orchestrator (main + extra mirror). CLI `items-set-item` on a
  container now dual-writes. `render_item_dual`.
- **GUI (`apps/ff9_items.pyw`)** — refactored to dict targets carrying the container/block; a **vanilla slot is
  now editable** (gil + items via the main block), a Memoria slot dual-writes, and equipment is correctly refused
  on a vanilla slot (main-block equip is the deferred follow-up). `items-inspect` + `inspect()` now decode vanilla
  slots too (were "not yet supported").
- A 3-lens adversarial-verify workflow (crypto/engine · python-safety · integration/GUI) found 11 issues — all
  folded in. The load-bearing one (a **bug**): the dual-write committed the main block before the load-
  authoritative extra, so a failed extra leg would silently show the OLD value in-game → **now the extra (authoritative)
  leg is written FIRST** (a partial failure leaves the visible value correct; documented). Also: reserve the last
  item slot as the padding terminator; a clean ValueError (not IndexError / a wrong-block read) for a bad block
  index; a position-aware post-write confirm; and the stale "extra-only / main mirror pending" docstrings refreshed.
- 18 new tests (synthetic encrypted containers + the GUI `--smoke` vanilla path); suite green.
- ★ **IN-GAME PROVEN (2026-06-12):** on the vanilla slot 1/save 1, edited the inventory via the main block —
  Potion 68→99 (change) + DarkMatter x3 (add, not previously held) — gil + other items + other slots untouched —
  loaded in-game and both showed, inventory intact. **Step 4b is fully done: a vanilla (no-extra) save is editable
  for gil AND items, via CLI + GUI.** The #5 editor is now functionally complete (extra: gil/items/equip; main
  block: gil/items); only main-block equipment + key items remain, both deferred.

### Added — battle-tuning Phase 5: character/growth CSV deltas (`[[character]]` / `[[leveling]]`) (0.9.58)
- **`battle/characterdelta.py`** — the PLAYER side of battle balance (the Phase-3 `actiondelta` twin for the
  enemy/ability side), as `Data/Characters` CSV deltas read live from the install:
  - `[[character]]` → **BaseStats.csv** (`dexterity`/`strength`/`magic`/`will`/`gems` by character name or 0-11
    id) — a **per-id partial delta** (`EnumerateCsvFromLowToHigh`, `ff9level.cs:30`): only the changed characters
    are emitted, the base supplies the other 11.
  - `[[leveling]]` → **Leveling.csv** (`exp`/`bonus_hp`/`bonus_mp` by `level = 1..99`) — the 99-step growth curve.
    The engine reads this **WHOLE-FILE** (`GetCsvWithHighestPriority`, `ff9level.cs:53`) and gates at ≥99 rows, so
    a partial would *wipe* the curve → the emitter reads the base 99 rows live, patches the named levels, and
    re-emits ALL 99 (HP grows `BonusHP·Strength/50`, MP `BonusMP·Magic/100`).
- Range-checked offline against the real C# column types (Dex/Str/Mag/Will = Byte, Gems = UInt32, Exp = UInt32,
  BonusHP/BonusMP = UInt16) so an out-of-range value fails the build, not the game's boot. The `CharacterId`
  name→id table is the open-source Memoria enum (provenance-clean); stat **values are read live, never committed**.
- Wired mod-global into `build` (`_emit_character_data`), offline lint into `validate_field`, both CSVs into
  `deploy_field`'s reversible deploy, and **Leveling into the deploy-time shadow guard** (`deploystack`, whole-file
  like `InitialItems`). CLI **`characters`** lists the live base stats (the tuning targets). `ModLayout` paths.
- ★ A 4-lens adversarial review (engine source + the live CSVs) verified the column layout, the whole-file
  Leveling handling, the range guards, and the merge model, and caught: a **provenance leak** (a test fixture row
  was byte-identical to the real install — de-leaked), the **missing Leveling shadow guard** (added), and a
  single-table `[character]` vs `[[character]]` build/lint disagreement (now normalized). 15 tests + a real-install
  smoke.
- ★ **IN-GAME PROVEN (2026-06-12):** a `[[character]]` boost of Vivi (Dexterity/Strength/Magic/Will → 40/80/90/45)
  seeded into the party (`[party] add = ["vivi"]`) on a New-Game landing field — at a **fresh New Game** her
  status menu read **Speed 40 / Strength 80 / Magic 90 / Spirit 45** vs vanilla 16/12/24/19. So `[[character]]` →
  `BaseStats.csv` lands at the New-Game party build. (Leveling shares the read-base/emit machinery + the
  real-install smoke; its in-game proof is a follow-up.)

### Added — save-item editor #5 step 4b: encrypted MAIN-block gil write + dual-write (edit vanilla saves), IN-GAME PROVEN (0.9.56)
- The editor can now write the **encrypted main AES block** of a `SavedData_ww.dat`, not just the Memoria extra
  file — so a **vanilla save with no Memoria extra is now editable**, and a Memoria save's main block is kept
  consistent with its load-authoritative extra (a dual-write).
- ★ **Layout finding (empirical, this install):** in the OLD save format the main block puts `40000_Common/gil`
  at a **fixed** offset (5235, UInt32 LE) and the 256-pair `{count,id}` item array at 5239 — byte-stable across
  saves at scenario 0→7200 and across Memoria *and* vanilla saves (the earlier "offsets shift" worry was about
  the *modern extra* format). The two no-extra slots turned out to be **vanilla saves** (hence no extra), with
  real mid-game gil/inventories editable via the main block.
- **`save_items.set_main_gil(container, block, gil)`** — decrypt → edit gil → re-encrypt one block (AES-CBC
  round-trips the untouched bytes), guarded by **`validate_main_block`** (refuses unless the 256-pair item array
  parses cleanly at the expected offset — a wrong/foreign layout is rejected, not corrupted), atomic container
  write, timestamped backup, post-write re-read confirm, dry-run default. Plus `read_main_gil`/`read_main_inventory`/
  `decode_main_block` (read a slot's gil/inventory straight from the main block — what a no-extra slot needs).
- **`save_items.set_gil_in_save(container, block, gil, mirror=True)`** — the dual-write orchestrator: writes the
  main block AND mirrors to the extra when present (vanilla → main only). CLI **`items-set-gil`** on a container
  now dual-writes (was extra-only); given an extra-save directly it still writes just that. `render_gil_dual`
  shows both legs; `_resolve_block` factored out and shared with `resolve_extra`.
- 16 new tests (synthetic encrypted containers via the save AES key); 1157 suite green. ★ **IN-GAME PROVEN
  (2026-06-12):** set a vanilla save's (slot 1/save 1, no extra) gil 43,162 → 7,777,777 in the main block — the
  whole container backed up, only block 1's ciphertext changed, other slots untouched — loaded in-game and the
  gil showed 7,777,777 with the inventory intact. The encrypted-write path the extra-only editor couldn't reach.
- Scope: gil first (the safe single-field win). Main-block **items** (the 256-pair array, structure now mapped)
  and the GUI's no-extra-slot editing are the next 4b increment; main-block **equipment** (the old-format
  9-player struct) is the deferred follow-up.

### Fixed — `deploy_campaign` wires New Game via the field-70 retarget, not the legacy field-100 hop (0.9.55)
- `deploy_campaign --apply` now wires New Game by calling `tools/retarget_newgame_warp.py` (byte-patch the shared
  field-70 opening override's `Field()` literal → the chain's entry id: New Game → field 70 → `Field(entry)`)
  instead of the old `newgame_warp.py` field-100 hop, whose injection site (a `RunSoundCode` after the InitRegion
  cluster) doesn't exist on every install — it **silently failed on the live install**, leaving New-Game wiring to
  depend on a manual retarget. `NewGame()` is stock → `fldMapNo` 70, so field 70 IS the New-Game field; a
  self-seeding verbatim chain bakes its party/beat via `[startup]`/`[party]`, so the field-100 party-setup hop isn't
  needed (memory `project-ff9-new-game-entry`). `--stock` is now a deprecated no-op; `revert_campaign.py` chains the
  retarget's revert. Surfaced by running the productionized `--apply` live (the warp step errored, the new guards
  worked). +1 regression-guard test.
- ★ **IN-GAME PROVEN (2026-06-12):** the full productionized path — `deploy_campaign --apply` (collision guard +
  CSV promotion + field-70 retarget) → relaunch → New Game — **boots straight into the Dali chain.** The
  end-to-end campaign New-Game capstone is now reproducible from one command + a relaunch.

### Added — save-item editor #5 step 4c: the Item & Equipment GUI (`apps/ff9_items.pyw`), IN-GAME PROVEN (0.9.54)
- A standalone tkinter app — the item/equip companion to the Story State console — to inspect + EDIT a save's
  gil, inventory and equipment by name, with a click. A **SEPARATE surface** (touches only `save_items`, never
  the story-state core; project-ff9-branch-lanes rule 3), modelled on `ff9_storystate.pyw`'s conventions.
- **Inspect** — pick a `SavedData_ww.dat` (enumerates its populated slots' extra files; the container read needs
  pycryptodome) or a Memoria extra-save directly; the left list shows each slot, the Inspect tab its decoded
  gil/inventory/equipment (`save_items.inspect`). Editable only for slots that have a Memoria extra file (the
  load-authoritative store); a slot with none is shown read-only (the main-block mirror is step 4b).
- **Edit** — three grouped editors (Gil / Item / Equipment), each with **Preview** (dry-run) + **Apply**
  (backup-guarded, atomic, re-read-confirmed via the proven `set_gil`/`set_item`/`set_equip`). Apply pops a
  confirm dialog showing the exact change; the character dropdown is populated from the selected slot; the slot
  dropdown is the five equip slots. After a write, the view refreshes against the just-written save.
- Registered in the launcher (`ff9_studio.pyw`, now 8 tools). A `--smoke` headless self-test exercises the full
  load → gil/item/equip preview+apply → backup path (no display, no real save). ★ Logic also verified against
  the real save's container (5 slots, 3 editable).
- ★ **IN-GAME PROVEN (2026-06-12):** the GUI renders, lists the slots, inspects gil/inventory/equipment, and a
  GUI-made equipment change showed up in-game. Also confirmed crash-safe under misuse: equipping a non-weapon
  (Ore) into the weapon slot via save edit doesn't crash — the engine's equip-load net only checks the item
  *exists* (not slot-appropriateness; that's a menu-only rule), so it loads and renders a fallback model.

### Added — `deploy_campaign` productionized: auto-promote start-state CSVs + a name-collision guard (0.9.53)
- **Name-collision guard** — `tools/deploy_campaign.py` now checks, before install, whether any `EVT_*.eb.bytes`
  or `FBG_*` scene name the chain ships collides (same name) with another live `Memoria.ini` `FolderNames` folder.
  Scene/`.eb` files resolve BY NAME, highest-folder-wins, so a same-named file in a stacked sibling folder silently
  serves the WRONG fork → torn load / black screen (the cross-worktree shadow that black-screened the Dali chain).
  Previewed in the dry-run (EVT names from the manifest), authoritatively checked at `--apply` against the built
  dist (EVT + FBG, ground truth) where it **ABORTS** (override `--allow-name-collision`); the message points at the
  fix, `import-chain --name-prefix <TAG>`. New `deploystack` helpers `check_name_collisions` / `name_collision_warning`
  / `eb_names_at` / `scene_names_at`.
- **Start-state CSV promotion** — a campaign installs into its OWN mod folder (usually NOT the highest), so its
  new-game `InitialItems.csv` (read highest-priority-wins) would be shadowed. When the campaign claims New Game,
  `deploy_campaign` now PROMOTES the entry field's `InitialItems`/`DefaultEquipment`/`ShopItems` CSVs up to the
  highest `FolderNames` folder, reversibly (single-owner, like the warp). Skip with `--no-promote-csv`, retarget with
  `--promote-csv-to <folder>`; gated off for `--no-warp` slices (a World-Hub journey shares the global bag/gear and
  seeds per-journey via scripted `give_item`). `revert_campaign.py` now restores/removes the promoted CSVs too.
- This is the manual lesson from the campaign-scale capstone session, made automatic. The generated
  `revert_campaign.py` is hardened too: it no longer `rmtree`s the live folder when the snapshot is missing,
  tolerates a vanished backup CSV, and is emitted even if CSV promotion fails partway. +13 tests.

### Added — save-item editor #5 step 4a: inventory + equipment WRITES, IN-GAME PROVEN (`items-set-item`/`items-set-equip`) (0.9.52)
- Extends the proven step-3 extra-file write path from gil to **items and equipment**, by name, same safety model.
- **`save_items.set_item(extra, item, count)`** — set an item's inventory stack count (a kit name or 0-254 id).
  `count` 0 REMOVES the stack; a new item inserts in **ascending-id position** (matching how the engine writes
  the bag); count clamps to the in-game cap (99); `NoItem` is rejected (the engine discards it on load anyway).
  The extra's `40000_Common/items` is a variable `[{id,count}]` list of live stacks.
- **`save_items.set_equip(extra, character, slot, item)`** — set one of a character's five equip slots
  (`weapon`/`head`/`wrist`/`armor`/`accessory`, + aliases `body`/`acc`). `character` = a **CharacterId** 0-11,
  the in-save name, a canonical name, or an alias (`dagger`/`salamander`); `item` = a name/id, or
  `empty`/`255`/`None` to unequip. The save's `players[].equip` is a 5-int array keyed by `info/slot_no`
  (CharacterId); the engine resets an unknown id to `NoItem` and recomputes derived defence/affinity on load, so
  only the id is written. Byte-grounded against `JsonParser.cs` (items write/load, equip write/load, player match).
- **`sjbinary.diff_paths(a, b)`** — a generic tree-diff powering the new **scoped-change** check
  (`_assert_scoped`): a variable-length edit (items add/remove) is verified to touch ONLY the allowed subtree
  (the `items` array / one player's `equip`) — the general analog of the gil write's byte-surgical gate.
- Shared `_atomic_write` (temp + `os.replace`, timestamped no-clobber backup) — `set_gil` refactored onto it too.
- CLI **`items-set-item <save> <item> <count>`** / **`items-set-equip <save> <character> <slot> <item>`** (shared
  save-target flags; dry-run unless `--apply`). Reports + renderers per write.
- 32 new tests (66 in `test_save_items` + `test_sjbinary`); 1111 suite green. ★ Build caught + fixed a real bug
  (the CLI passes `character` as a string, so a numeric CharacterId `"6"` failed — `_find_player` now treats
  digit strings as CharacterIds). A 3-lens adversarial-verify workflow (engine-fidelity / python-safety /
  integration) found 6 low-sev issues, all fixed (count-leaf guard, stale docstring, render + scoped-abort +
  post-write-confirm + backup-assertion test coverage).
- ★ **IN-GAME PROVEN (2026-06-12):** applied to slot 1/save 3 — Potion 7→99, +5 Elixir (inserted at its ascending-id
  position), Zidane weapon Dagger→Mage Masher — the main container untouched — loaded in-game and all three showed
  correctly. The editor now writes **gil + items + equipment** to a real save, schema-faithful.

### Added — save-item editor #5 step 3: the first real-save WRITE = gil (`items-set-gil`), IN-GAME PROVEN (0.9.50)
- **`save_items.set_gil(extra_path, gil, *, dry_run=True, backup=True)`** — write `40000_Common/gil` into a
  Memoria EXTRA save file (the **load-authoritative** store — it overrides the encrypted main block on load,
  memory `project-ff9-save-item-layout`). gil is a length-stable Int32 leaf (IntValue, tag 4), so this is the
  smallest possible real-save mutation: the editor's FIRST write, and the falsifiable in-game **proof** that the
  extra overrides the main block (write ONLY the extra — if the in-game gil changes to match, the extra wins).
  Extra-only by design; the main-block mirror + items/equipment are step 4. Never touches `00001_time`.
- **Two safety gates** (it writes a REAL save): (1) refuses to edit any file the SimpleJSON codec can't reproduce
  byte-for-byte (guards an unhandled leaf); (2) asserts the edit is surgical — same length, only the gil's ≤4
  contiguous value bytes move. The write is **atomic** (temp file + `os.replace`) and re-reads to **confirm** the
  new gil; a **timestamped** `.bak.<ts>` backup is taken first (never clobbers a prior one, matching
  `save.apply_story_edit`). **dry-run by default**; a no-op (gil already == requested) writes nothing even on apply.
- **`save_items.resolve_extra(...)`** — target an extra file directly, or resolve one from a `SavedData_ww.dat`
  container + 0-indexed `--slot`/`--save-no` (or `--autosave`; the two are mutually exclusive).
- **CLI `items-set-gil <save> <gil> [--slot S --save-no N | --autosave] [--apply] [--no-backup]`** — dry-run
  preview unless `--apply`. (`render_gil_write` shows the diff + the proof instructions.)
- 14 new tests (37 in `test_save_items`), incl. a CLI-glue test + an install-gated real-save **dry-run** (no
  write). A 3-lens adversarial-verify workflow (engine-fidelity / python-safety / integration) hardened it:
  atomic write, timestamped no-clobber backup, no-op short-circuit, non-Class guard, `--save-no` message fix,
  gil=0 + CLI coverage.
- ★ **IN-GAME PROVEN (2026-06-12):** applied gil `500 → 1,234,567` to the EXTRA file of slot 1/save 3 — the main
  container `SavedData_ww.dat` was byte-untouched — loaded the save and the in-game menu showed **1,234,567**.
  So **the extra overrides the encrypted main block on load = confirmed live** (the whole #5 dual-write thesis).
  ★ And **no relaunch was needed** — the extra is re-read on every save-load, so the edit→load loop is as fast as
  an F6 field reload.

### Added — battle-tuning Phase 4: the `BattlePatch.txt` emitter (enemy/attack/scene by name) (0.9.51)
- **`battle/battlepatch.py`** — author Memoria's reflection-patch `BattlePatch.txt` declaratively, reaching the
  combat data CSV can't and that raw16 `[scene]` can only reach by FORKING the scene. Three `field.toml` blocks
  map 1:1 to the engine's selector model (`DataPatchers.PatchBattles`):
  - `[[battle_patch]]` — **scene-scoped** (`scene = <id|BSC_ name>`): scene flags (`back_attack`, `preemptive`,
    `runaway`, …, → `BTL_SCENE_INFO`) + nested `[[battle_patch.enemy]]` / `.attack` / `.pattern` sub-blocks
    targeting an enemy/attack by `index =` or `name =`. Patches ANY scene **in place** (no fork, no raw16 repack).
  - `[[battle_enemy]]` / `[[battle_attack]]` — **global by-name** (`AnyEnemyByName:` / `AnyAttackByName:`): retune
    EVERY enemy/attack of that name across ALL scenes — the campaign-wide WIN over Hades Workshop ("buff every
    Goblin across the chain").
  - Reaches the **BP-only** levers with no raw16 slot: drop/steal **rate** arrays, `BonusElement`,
    `MaxDamageLimit`/`MaxMpDamageLimit`, `WinCardRate` — and the **enemy ATTACK table** (`AA_DATA`/`BTL_REF`:
    power/element/rate/`status_set`/mp/script), which the kit could not touch before. Plus the full enemy combat
    identity (stats, the 4 element affinities, the 3 status masks, defences, level/category, drop/steal ids).
- **Uniform integer emission**: `.NET Enum.Parse` accepts integer strings for every enum/flags field, so element/
  status/item values resolve through the committed `battlecsv`/`itemstats` name↔bit tables + `items.resolve` —
  **no new SE-derived table is committed** (provenance: the authored toml holds only overrides; the emitted
  `BattlePatch.txt` is build-output, never committed). Narrow engine column types (Byte/UInt16/UInt32) are
  RANGE-CHECKED offline so a value the engine would silently drop fails the lint/build instead.
- **Non-clobbering deploy** (`merge_battle_patch`): the built block is spliced into the live `BattlePatch.txt`
  under per-field `//` sentinel markers (the engine skips `//` lines), so a co-deployed battle's BGM/repoint
  lines + a stacked worktree's lines survive; idempotent + reversible (`deploy_field.py`). `build_mod` merges the
  Phase-4 lines with the per-encounter BGM `Battle:`/`Music:` block into one file.
- CLI **`battle-patch <field.toml>`** previews the emitted lines offline; `battle-patch --fields` lists the
  tunable `[PatchableField]` names by token. Offline lint wired into `validate_field`.
- ★ A 4-lens adversarial review (engine source + the structs) verified the grammar/ordering, every field
  name↔`[PatchableField]`↔token↔range, and the value-encoding sound, and caught three real bugs (fixed): the
  `status_set`/`AddStatusNo` cap was `_U16` but `StatusSetId` defines only 0-38 → an undefined id is a
  `KeyNotFoundException` crash at command-build (capped at 38); a malformed (non-table/non-list) toml block
  tracebacked instead of raising `BattlePatchError`; and the `scene` selector was unvalidated → a
  float/list/over-Int32 value silently emitted a dead `Battle:` line the engine never matches (the whole block
  no-oping). 23 tests (`test_battlepatch.py`).
- ★ **IN-GAME PROVEN (2026-06-12):** a `[[battle_patch.attack]]` on the forked EF_R007 Goblin (scene 30055,
  `FF9CustomMap-bt`) patched the enemy's **normal attack** by index — `power = 30` (now lethal) + `status_set = 16`
  — and both landed: the attack inflicted status-set 16, whose `StatusSets.csv` bundle (`AutoLife`, `Vanish`,
  `Regen`, `Haste`, `Protect`, …) showed up exactly as authored (hit party members revived at 1 HP from AutoLife
  and went invisible from Vanish). So the **enemy `AA_DATA` attack lever** (untouchable by the kit before) works
  by name via BattlePatch. (Lesson for authors: `status_set` is a `StatusSetId` row — 16 = the Dispel bundle,
  Poison = 20; pick the row you mean.)
- ★ **FULLY PROVEN (2026-06-12):** a follow-up confirmed every Phase-4 channel in one fight — `AnyEnemyByName:
  Goblin` (the Goblin started **Poisoned** via `initial_status`; since "Goblin" is a real FF9 enemy, that one
  block also buffs real Goblin battles — the campaign-wide win over Hades Workshop), `AnyAttackByName: Goblin
  Punch` (neutered to **power 1**), the `back_attack` **scene flag** (party started reversed), and a guaranteed
  `drop_rates` **Elixir**. Every selector + the BP-only rate arrays + scene flags are now in-game proven.

### Fixed — `deploy_field` DictionaryPatch revert is now surgical (was clobbering co-deployed registrations)
- `deploy_field`'s generated revert restored the **whole** pre-deploy `DictionaryPatch.txt` snapshot, so when a
  field and a battle scene share one mod folder (the battle-tuning loop: `deploy_battle` registers
  `BattleScene <id>` into `FF9CustomMap-bt`, then `deploy_field` deploys the trigger field there), the field
  deploy's pre-revert wiped the `BattleScene` line → the battle **black-screened** on entry. The revert now drops
  only the field's own `FieldScene <id>` line from the *current* live file and restores that id's prior line from
  the backup, preserving every co-deployed line. (Same wholesale-snapshot hazard the World Hub note flagged.)

### Added — World Hub: a playable journey selector (choice `warp` action + `[player] model=`), IN-GAME PROVEN (0.9.48)
- The **World Hub** is a playable field that lets the player pick which **journey** (a complete arc = one or
  more chained campaign slices) to play, then warps them in — NOT a worldmap (no engine fork), just a field +
  a dialogue-choice menu + warps. overworld's lane (memory `project-ff9-world-hub`). Reuses the existing
  `[[npc]]`+`[[choice]]` pipeline + two small general additions:
  - **The choice `warp` action** (`content/event.warp` + `choice.option_body`): a `[[choice.options]]` row can
    `warp = <field id>` (+ optional `set_scenario = N`). Grounded finding: a `Field` op transitions directly
    from a **tag-3 talk handler** (14+ shipping fields do — the Dali innkeeper, the airship, Gargan Roo),
    unlike a bare `Field` in Main_Init. The warp = `RunSoundCode(265,65535)` + `Field`; `warp` is last in the
    option body (it transitions away). Byte-identical without it.
  - **`[player] model=`** (`npc.set_player_model` + build wiring): re-skin a synthesized field's player avatar
    to any model — the hub's stock Moogle (**220** `GEO_NPC_F0_MOG`, the save moogle), keeping
    `DefinePlayerCharacter`. The field-side twin of `--swap-player`; free-roam-only.
- `examples/world_hub/` — a self-contained 3-field scaffold (hub 4500 + journeys 4501/4502). `validate()` flags
  a bad `warp`/`set_scenario`. 9 tests (`test_world_hub`).
- ★ **IN-GAME PROVEN (2026-06-12):** F6→Warp 4500 — walk as the moogle, talk → the journey menu shows, pick →
  warp into the destination (custom arrival dialogue), "Stay here" closes. Playtest fixes: stock moogle = 220
  (not 199, a bat-winged variant); the text block must avoid **1073** (shadowed by the higher `FF9CustomMap`
  folder). ★ Deploy gotcha (CLAUDE.md §3): `deploy_field`'s wholesale-snapshot revert RE-CLOBBERS a multi-field
  text block back to the first-deployed value — verify the DictionaryPatch textids, or deploy as a campaign.
- **Deferred follow-up now UNBLOCKED:** New-Game→hub uses master's new `tools/retarget_newgame_warp.py 4500`
  (point the field-70 override at the hub). The `[[journey]]` sugar + generator ("hardcoded MVP → generator")
  remains the next step.

### Added — campaign-scale New-Game capstone: boot directly into a forked verbatim CHAIN (0.9.47)
- **`tools/retarget_newgame_warp.py <id>`** — point the field-70 New-Game override at any custom field id (the
  chain's entry), byte-patching its `Field()` literal in place via `content.verbatim.remap_fields`. Composes with
  `skip_opening_fmv.py`. So New Game → a forked `import-chain --verbatim` slice that runs its real story.
- **`import-chain --name-prefix <TAG>`** — namespace every member's deployed FBG/EVT name (e.g. `DC_DL_INN`) so two
  campaigns/worktrees that fork the SAME source field don't collide on the by-name, highest-`FolderNames`-folder-wins
  scene/`.eb` resolution (a shadow that silently serves the WRONG fork → black screen). Byte-identical when unused.
  `member_name`/`assign_ids`/`write_campaign` gain a `name_prefix`; CLI `--name-prefix`. (75 campaign tests pass.)
- ★ IN-GAME PROVEN (Dali): New Game → wake up in the Dali inn → the slice plays its REAL logic (party splits to
  explore town — faithful) → Garnet rejoins at scenario 2640. A forked chain advancing real story state from a fresh
  game. Lessons: seed `[startup]` to the donor's OWN beat (Dali = 2600, not a notch past it); deploy the chain to
  `-sf` but promote the entry's start-state CSVs UP to the highest folder. See memory `project-ff9-new-game-entry`.

### Added — starting-state capstone: a New Game that boots into a custom field with the right beat/party/bag/gear (0.9.43)
- `examples/capstone/` — a self-contained entry `field.toml` that composes all FOUR new-game starting-state channels
  on ONE field: `[startup]` (ScenarioCounter + a story bit) + `[party]` (add Steiner/Freya) → the field `.eb`
  (prepended to Main_Init at synthesis); `[start_inventory]` → `Data/Items/InitialItems.csv` + `[[equipment]]` →
  `Data/Characters/DefaultEquipment.csv` (emitted at the mod-write stage). `build`/`deploy_field` fire all four
  automatically; the CSVs are read **only at a true New Game**. ★ IN-GAME PROVEN end-to-end — New Game → field 4003
  as **Zidane/Steiner/Freya**, Steiner wearing his Excalibur+Genji delta, the custom bag, at ScenarioCounter 2600.
- The entry is the engine-independent field-70 override (`Field(4003)`, FMV-skipped) — no DLL.
- ★ Deploy to **id 4003 in the highest mod folder** (`--id 4003 --mod-folder FF9CustomMap`): the override warps
  `Field(4003)` and `InitialItems.csv` is highest-priority-wins (a lower folder's bag would shadow it silently).
- `tests/test_capstone.py` (5 tests): the four-channel emission + two design invariants — `[party]` adds the others,
  not Zidane (the new-game base is Zidane-slot-0, and added members join wearing their `[[equipment]]` gear); the
  `[startup]` flag stays in the custom safe band.
- No kit code changed — the four channels already existed; this is the **composition + the proof** (story_flags'
  composition lane). Engine facts verified by a 3-lens adversarial review against Memoria source.

### Added — deploy-time shadow guard for the highest-wins `InitialItems.csv` (0.9.43)
- A cross-branch handoff (story_flags' CSV-shadow lane): `deploystack` warned on a `.mes` text-block shadow but
  not on an `InitialItems.csv` shadow. The starting bag is read **highest-priority-wins** (a whole-file win, not
  a per-id merge like `ShopItems`/`DefaultEquipment`), so deploying it into a folder that a **higher**-priority
  `FolderNames` folder also ships **silently drops it** — no error, the wrong bag loads.
- New `deploystack.check_csv_shadow` (mirrors `check_text_block_shadow`): given the mod stack, it flags a
  highest-wins CSV that a higher folder shadows, with a concrete fix (deploy to the highest folder / remove the
  higher copy). `HIGHEST_WINS_CSVS` lists the one file that needs it (`InitialItems.csv`); the merged CSVs don't.
  `tools/deploy_field.py` runs it for each highest-wins CSV it actually shipped, after the text-shadow guard
  (and never breaks a deploy on an odd `Memoria.ini`). 5 tests. kit 0.9.43.

### Added — `[[shop]]` — author a custom shop: inventory + opener (0.9.43)
- A new `[[shop]]` block defines a shop the player can buy from — its **inventory** plus an **opener** — entirely
  on stock Memoria (no DLL). The author-side complement to the `fork-report` Items/Treasure axis.
- **Inventory** → a `StreamingAssets/Data/Items/ShopItems.csv` delta (`content/shop.py`
  `render_shop_items`/`write_shop_items`), emitted once at the mod-write stage (`build._emit_shops`, alongside
  the new-game CSVs). The engine **merges** shops by id over the base (which supplies shops 0-31), so the delta
  lists only the custom shops; ids are `>= 32` (a `< 32` clash overrides a vanilla shop — warned) and `<= 255`
  (the `Menu` sub-id byte). Item names/ids resolved via the kit's item table; duplicates within a shop collapse;
  `NoItem` (255) dropped. Shops collect from **every** built field (not entry-restricted — they merge by id);
  a duplicate id across the mod is warned (last-wins).
- **Opener** → `Menu(2, id)` (`OpenShopMenu`; the `Menu(4, 0)` save-point family). Two shapes:
  - **`[[npc]] opens_shop = N`** — talking to a shopkeeper NPC opens shop `N` (a vanilla 0-31 shop too); its
    `dialogue` is the greeting shown first. Reuses `content/npc.py`'s `speak_body` slot (`shop_speak_body`).
  - **`[[shop]] zone = [...]`** — a standalone press-to-interact region opens the shop (the save-point region
    shape: `DisableMove; Menu(2, id); EnableMove`), `bubble` toggles the "!" prompt. `shop_region`/`inject_shop_regions`.
- `validate()` checks the shop id type/range, a non-empty resolvable `sells`, the zone shape, and `opens_shop`
  range. `_emit_shops` warns on a vanilla-id override, a duplicate id, and an `opens_shop` pointing at an
  undefined custom shop. `ModLayout.shop_items_csv` is the new mod path.
- Byte-identical when no `[[shop]]` is present (no region injected, no CSV written — the base shop file is not
  clobbered). New module `content/shop.py`; touches `build.py` (inject + emit + validate) + `config.py`. 25 tests
  (`tests/test_shop.py`); clear of story_flags' compose lane + overworld's forkreport lane. kit 0.9.43.
- ★ A 3-lens adversarial-review workflow (engine-fidelity / Python-correctness / integration-at-scale) caught
  defects the first pass missed, all fixed: **(blocker)** `tools/deploy_field.py` didn't ship the new
  `ShopItems.csv` (the same selective-copy gap #3 had) — added to its reversible CSV-deploy loop, so the
  edit→deploy→F6 loop actually carries shop stock; **(blocker)** an author `comment` was emitted verbatim as CSV
  column 0, so a `;` corrupted the row (mis-parsed the Id) and a leading `#` made the engine skip the whole line
  (the shop silently never loaded) — `shop.safe_comment` neutralizes `;`/newline/leading-`#` (the label is
  cosmetic); **(bug)** an NPC with both a `[[choice]]` and `opens_shop` silently dropped the shop (the talk-body
  `elif`) — now a `validate()` error; **(bug)** a `sells` that resolves entirely to `NoItem` passed validate then
  built an empty shop — now caught post-resolution; **(smell)** `_emit_shops` made dup-id and vanilla-override
  mutually exclusive (`if/elif`) and could crash on a malformed id (build skips `validate`) — both now independent,
  and a bad id is skipped-with-warning not a crash; **(smell)** a verbatim fork silently dropped a synthesized
  shop opener — now warned (the inventory CSV still ships). The cross-worktree same-id merge collision is noted
  in FORMAT.md.
- ★ **IN-GAME PROVEN (2026-06-12):** a test field (slot 4003) with both openers — a shopkeeper NPC (`opens_shop`)
  and a standalone `zone` counter — opens shop 40 / shop 41 with their authored inventories, and a real purchase
  (a Mage Masher) deducted gil + added the item. The deploy shipped `ShopItems.csv` (the gap fix confirmed).

### Added — `fork-report --explain`: decode a field's NPC interactions into readable English (0.9.44)
- `fork-report <field> --explain` traces every carried NPC's **tag-3 talk routine** into plain steps —
  real `.mes` dialogue + items/gil/menus + the funcs it `RunScript`s — and **inlines** those funcs (the
  Main_Init shared logic `uid 0`, the player sequences `uid 250`/a player entry, a sibling object) so a
  multi-NPC sidequest reads as one quest. It also shows **why** a render-only NPC is render-only: you SEE
  that its talk routine *is* the field's own quest logic (shared/player/economy), not a graftable gesture
  → "fork with `--verbatim` to keep it interactive." Validated on the Daguerreo 2F (field 2803) positive
  control — the debate, the librarian's book quest, the old man's **Excalibur** trade, all legible.
- `forkreport.explain_eb` is **pure** (`.eb`-only structure; a parsed `.mes` enriches the windows with real
  text, else `<line N>` placeholders) → offline-testable; `forkreport.explain` is the id→bytes loader over
  it; `format_explain` renders the transcript (ASCII chrome). Read-only — reuses the disassembler + the
  item-pool decode + `dialogue.parse_mes`; no carry/graft logic of its own (analysis lane). 7 tests.

### Closed (proven infeasible) — #14 talk-handler graft closure
- The carry-fidelity gap "graft a render-only NPC's talk routine into a non-verbatim fork" is **infeasible**.
  A **verified census of all 675 forkable fields under maximal grafting** (`graft_player_funcs` + `carry_text`
  + `graft_seq_helpers` + `graft_savepoint`, with the self-dependency fixpoint modelled) found **55 NPCs across
  36 fields that render faithfully but lose their tag-3 talk handler, and 0 of them are blocked only by a
  graftable gesture**: every one depends on the field's own logic — Main_Init shared dialogue branches (40),
  exotic non-gesture player sequences (15), uncarried co-actors (4), an unsafe background script (1), a party
  op (1). (A further **39 objects in 20 fields are refused outright** — their tag-1 LOOP itself is un-graftable,
  an even harder case.) The census agrees with `fork-report`'s interaction axis (field 2803 = 3 render-only).
  In FF9 an NPC's *interactive* talk handler **is** the field's transaction logic (dialogue + rewards + menus +
  walkmesh-triangle toggles the engine even hardcodes per-field), inseparable from its text/economy/geometry.
  `--verbatim` already carries all of it byte-for-byte, so the standing answer for "keep these NPCs interactive"
  is `--verbatim`. `--explain` is the shipped takeaway: read the quest, decide per-field. (Memory
  `project-ff9-fork-fidelity-worklist`.)

### Fixed — `import <id>` now means the FIELD ID, not a `map<NNN>` folder substring (0.9.42)
- `import <field>` / `import-chain` resolved a token by **FBG-folder substring**, while `fork-report` /
  `list-fields` / `find-rooms` resolve a digit as a **field id** — so they targeted *different* fields for the
  same number. `import 100` forked the Dali field whose folder contains `map100`; `fork-report 100` analyzes
  field id 100 (Alexandria). Field ids and the folder `map<NNN>` numbers are **unrelated schemes** (0 of 676
  coincide), so a numeric token diverged for **every** field — 79 silently forked the wrong field, 38 errored
  ambiguously, 559 just failed.
- Fix: `extract.resolve_field` is now **digit-first** — a pure-digit token resolves via `ID_TO_FBG[int]` (parity
  with `fork-report`); non-digit tokens keep the FBG/mapid-substring behavior (so `map100` / `vgdl_map100` still
  match a folder by its map number). This transitively fixes an **internal** mismatch too: `import 100 --verbatim`
  used to ship the Dali field's `.eb` (folder-keyed) with Alexandria's `.mes` (the dialogue path is already
  digit-first) — now both halves are the same field. Surfaced + grounded by a 2-agent workflow (full caller audit:
  the only digit token entering `resolve_field` is the user's `import` arg; campaign/chain seeds were already
  digit-first; issue #2 "multi-id folders → wrong event" confirmed non-existent — the table is strictly 1:1).
  4 tests (3 offline + an install-gated consistency check). One minor remainder noted: `import` still doesn't
  match bare event-name tokens (`EVT_…`) the way `fork-report` does — a possible future polish. kit 0.9.42.

### Added — `--swap-player --neutralize-gestures`: stand cleanly through a cutscene (0.9.41)
- `import <field> --swap-player <char> --neutralize-gestures` (also on `import-chain`) makes a swapped
  character STAND/idle cleanly through a cutscene field instead of T-posing on the donor rig's scripted
  gestures. On every swap-target player entry it rewrites each `RunAnimation` (0x40) clip — and any LOOP
  movement re-set (`SetStandAnimation`/…) — to the swapped rig's OWN idle clip, leaving `WaitAnimation`/
  `Wait`/`SetAnimationFlags` intact so timing is preserved. (The character won't *emote* — for story fidelity
  use a verbatim fork at the right beat. Requires `--swap-player`.)
- **Engine-grounded** (a workflow read Memoria's `DoEventCode`/`ProcessAnime`/`AnimationFactory`): RunAnimation
  is NAME-keyed via one global clip dict, so a foreign donor gesture clip loads a foreign-skeleton clip = the
  glitch; the swapped rig's idle is already loaded (by `--swap-player`'s SetStandAnimation), so substituting it
  gives a real frame count and the paired `WaitAnimation` completes (no hang). NOP-ing was rejected (it orphans
  the `WaitAnimation`). 0xBD (RunAnimationEx) is left untouched (never targets the player in 676 fields; its clip
  arg sits behind an object selector). `playerswap.neutralize_gestures` (reuses the proven `_put_arg` patch);
  `apply_player_swap(neutralize=)`; `write_campaign(neutralize_gestures=)`.
- **A 2-lens adversarial review caught a blocker** (both lenses): `apply_player_swap` ran swap then neutralize
  as two passes, each re-deriving `swap_targets()` — but `swap_player` mutates the SetModel id those target on,
  so on Zidane-present multi-PC fields (87/668 = 13%) the second pass DRIFTED to a co-actor, neutralizing the
  wrong entry AND corrupting a bystander. Fixed by resolving the target set ONCE on the original bytes and
  reusing it (the `entry=` override now accepts a list), plus a defensive model-match guard in
  `neutralize_gestures` (only rewrite an entry actually swapped to `char`). Field 500 (Cargo Ship) regression
  test. The review also fixed a false "will glitch" WARN in the chain summary (now reports NEUTRALIZED). 6 tests
  (3 offline + a field-500 + an install-gated). kit 0.9.41.

### Added — `list-fields --players` / `--non-zidane`: who you play as in each field (0.9.39)
- `ff9mapkit list-fields --players` enriches the field list with **who you control** in each field, and
  `--non-zidane` (implies `--players`) narrows to fields where you play as **someone other than Zidane** —
  the verbatim-fork donors — so they're discoverable without forking each one. e.g. `list-fields alxt
  --players` shows field 100 = `Vivi *`, and the live `--non-zidane` sweep finds **89 of 675** — split in the
  footer into **53 playable-cast donors** (Steiner 19, Garnet 18, Vivi 10, Eiko 4, Freya/Amarant 1) and 36
  cutscene-driver `GEO_SUB` "players" (so you can tell a real swap donor from a scripted actor).
- **Id-centric** (a player is a property of the `.eb`), so an alternate event script on a shared background
  is its **own** row — revealing the non-Zidane variants folder-centric listing hides (the Steiner `_b`
  scripts 2050–2053 surface next to their Zidane `_a` twins on the same map). The `non_zidane` flag uses the
  in-game-proven, stricter definition (non-Zidane only when **no** Zidane is among the PCs), so it excludes
  Zidane-present multi-PC escape scenes where you actually control Zidane — the honest "you really play as
  someone else" set (which is why 91 < the census's looser 178).
- New `forkreport.field_players` (sweeps `ID_TO_FBG`, reuses `analyze_eb`'s player resolution — one
  `EventBundle`, eb-only) + `player_label` + the `FieldPlayer` dataclass (with a `playable` flag); the CLI
  gained the two flags (`_list_fields_with_players`). Plain `list-fields` (no flags) is unchanged + fast. A
  full no-pattern sweep is ~30s (a pattern narrows it). Read-only; `forkreport.py`/`cli.py` only — clear of
  the build + graft lanes.
- A 2-lens adversarial review caught a real classification bug (both lenses): **`eventscan.ZIDANE_MODELS` was
  missing the ZDD disguise (532) + the ZDN LOD forms (203/432/668-670)**, so Zidane fields leaked into the
  non-Zidane lists (field 401 literally listed as `Zidane(ZDD) *`). Fixed at the root (`ZIDANE_MODELS` now
  covers every `GEO_MAIN_*_ZDN`/`_ZDD` form — which also corrects `find-rooms` + the fork-report Player axis);
  the count drops 91→89. Also hardened `player_label` (keep the non-Zidane flag when the binder name is blank)
  and surfaced the playable-vs-cutscene-driver split. 7 tests (4 pure + 3 install-gated). kit 0.9.39.

### Added — `[start_inventory]` / `[[equipment]]`: new-game starting bag & default gear (0.9.40)
Author what the player **starts a New Game with** — the starting inventory and each character's default
equipment — as **engine-independent CSV deltas** (stock Memoria). This is the item/equip half of the
New-Game-into-a-fork capstone; it composes with the scenario/party half (`[startup]`/`[party]`) and the
seamless New-Game entry (`nop_cinematics`).

```toml
[start_inventory]                              # the FULL starting bag (REPLACES the base; highest-priority-wins)
items = [["Potion", 20], ["Phoenix Down", 5], ["Tent", 3]]

[[equipment]]                                  # a character's starting loadout (partial: only the chars you list)
character = "steiner"
weapon = "Excalibur"
armor  = "Genji Armor"                         # omitted slots (head/wrist/accessory) start empty
```

- `content/inventory.py` renders the FULL `Data/Items/InitialItems.csv` (the engine reads it
  **highest-priority-wins**, so it replaces the base bag; counts clamp to 99, dup ids sum) and
  `content/equipment.py` renders a PARTIAL `Data/Characters/DefaultEquipment.csv` (the engine **merges** it
  low→high over the base's 15 sets, so only the named characters change; each row is a complete loadout).
  Character name→`EquipmentSetId` is a names/ids-only table (provenance-clean, like `_itemdb`).
- Emitted at the **mod-write stage** (`build_mod`, alongside DictionaryPatch/BattlePatch via `ModLayout`),
  not into any `.eb` — these are mod-global files. They live on the **entry field's** `field.toml` only; the
  build **warns** if a block lands on a non-entry field (precise for a campaign via the entry member) and
  surfaces the `InitialItems` highest-wins/shadow caveat. New-game-only scope (read once at new-game init).
- `validate()` resolves every item + character name. New `ModLayout.initial_items_csv` / `default_equipment_csv`.
- **Provenance:** the writers are deterministic from the author's `field.toml` + the committed name tables —
  no game stat data is read or committed. Adversarially reviewed (3 lenses: engine-format / Python / provenance)
  — the partial `DefaultEquipment.csv` was confirmed to merge with the base (no "must define 15 sets" boot
  crash). 15 tests (`test_startstate.py` pure renderers + `test_build.py` emit/validate/lint).
- The dev loop ships them: `deploy_campaign.py` already copied the whole mod (wholesale); `deploy_field.py` now
  also deploys the two CSVs **reversibly** (it previously copied only the field's `.eb`/scene/`.mes`), so a
  single-field test reflects them. Test: deploy → **relaunch** (the bag is read at New-Game init, not via F6
  reload) → **New Game** → check the items/equipment menu (the bag/gear is set before you warp to the field).

### Added — `remove_item`: the symmetric take-item reward lever (0.9.36)
`[[event]]` and `[[choice]]` rewards could `give_item` but not take one back. New `remove_item = [item, count]`
(id or name) emits `RemoveItem` (`0x49`) — pair it with `give_item` for a **trade**, or use it alone to
**consume a quest item**. (Giving equipment by name and the "Received X" box already worked for any item,
incl. weapons/armor — this closes the one missing half.)

```toml
[[event]]                       # a trade: take a Dagger, give a Potion
zone = [[300,-400],[700,-400],[700,-800],[300,-800]]
remove_item = ["Dagger", 1]
give_item   = ["Potion", 1]
message     = "Traded!"
```

- New `opcodes.remove_item` (0x49) + `event.take_item` (name-resolved, like `give_item`); wired symmetrically
  into the event + choice-option builders and `validate()` (a sole `remove_item` is a valid action; an unknown
  name is caught). The engine clamps removal to what's held, so over-removing is safe.
- 4 tests across `test_content` / `test_choice` / `test_build` (a trade event with both ops, a trade choice
  option, a remove-only event validates + builds with `0x49`, and a bad name is rejected).

### Added — `find-rooms`: sweep all fields for the best swap/demo test rooms
- A new `ff9mapkit find-rooms` subcommand scans every forkable field and ranks the best **swap/demo test
  rooms** — a place to walk as a `--swap-player` character or stage a visual test where the model's detail is
  visible. The proven anchor field 1200 `ac_rst_x` ranks #1; the top results match the hand-verified clean
  rooms (1911 Treno house, 310 Ice Cavern cafe, 3055 BMV weapon shop, …).
- A "good room" is the AND of: single-PC + swap-clean + a PLAYABLE controller + a STATIC roster + a **close
  3/4 single-screen camera**. The camera test is the subtle part: **FOV alone is NOT a detail proxy** — FF9's
  projection is orthographic-like (k≈0.93, the camera-math invariant), so a sub-10° "FOV" is a far *telephoto*
  (model is a speck), not a close shot. So the filter ANDs a bounded FOV (10–45°) **with** a 3/4 pitch band
  (6–48°) **with** the camera's visible `range_height` (≤420; the key signal, now exposed from
  `field_camera_info`) **with** a `_CS_` cutscene-name guard. Scrolling is a rank demerit, not a disqualifier.
- Two-phase for speed (~45s over ~675 fields): a cheap `.eb`-only prefilter (one `EventBundle`, no per-field
  scene load) keeps single-PC + swap-clean + static-roster + playable fields, then the expensive per-field
  camera read runs ONLY on those ~75 survivors. `--limit` / `--max-fov`; `find_rooms(ids=…)` scopes the sweep.
- New in `forkreport.py`: `find_rooms` / `room_score` / `RoomSweep` / `format_room_table` / `_is_real_fbg` +
  the `ROOM_*` calibration constants. `extract.field_camera_info` now returns `range_w`/`range_h`;
  `ForkReport` gains `cam_range_h`. The `_camera_line` Camera axis gained a `distant` label for sub-10° FOV
  (a telephoto, not "close" — corrects the just-shipped axis). Grounded in a 676-field calibration sweep and
  hardened by a 3-lens adversarial review (caught the missing low-pitch bound, the loose max-pitch, the
  vehicle-player donor, and story-event leakage — all fixed). Read-only; `forkreport.py`/`extract.py`/`cli.py`
  only. 12 tests (8 pure + 2 install-gated integration). kit 0.9.37.

### Added — `fork-report` Camera axis: the lens a fork plays through (close / medium / wide)
- A new **`Camera`** line previews how the field is framed: a **`close` / `medium` / `wide`** feel bucketed by
  horizontal FOV, plus the raw `pitch`/`FOV`, and notes when the field is `scrolling` or has multiple cameras.
  E.g. field 1200 `ac_rst_x` = `close (FOV 29.5 deg, pitch 28.8 deg); 2 cameras`, the Hangar 1357 =
  `wide (FOV 61.3 deg, pitch 0 deg)` (the "super far away" view), Vivi's street 100 =
  `close (FOV 17.2 deg, pitch 38.5 deg); scrolling` (a tight lens that pans).
- Pairs with the Player swap-friendliness tag: **`swap-clean` + `close`** = a good `--swap-player` / demo test
  room (the detail is actually visible), vs a `wide` establishing shot where models are tiny.
- The camera lives in the scene `.bgs` (not the `.eb`), so it needs the install: a new read-only
  `extract.field_camera_info` (pitch/FOV/scrolling/count — no walkmesh/atlas extraction) populates the report in
  `forkreport.analyze()`. The pure `.eb`-only `analyze_eb` is untouched (no camera → the line is omitted), so the
  fixture reports stay byte-identical. Reuses the existing `cam.pitch_deg` / `cam.decompose` (FOV) math; no new
  camera code. 4 tests (`tests/test_forkreport.py`, incl. an install-gated render). kit 0.9.34.

### Added — `fork-report` Player axis: swap-friendliness tag (is this a good `--swap-player` target?)
- The Player line now ends with a swap-friendliness tag: **`swap-clean`** (a free-roam field — `--swap-player`
  works cleanly) or **`swap: N gesture(s) glitch`** (a cutscene field whose player plays N scripted gestures
  that would glitch on a swapped rig, since only movement clips are swapped). It's the *before-you-fork* preview
  of the existing swap-time `WARN`, useful for browsing/choosing a swap or demo target (e.g. field 1200
  `ac_rst_x` = `swap-clean`, a close 3/4 camera; the Vivi field 100 = `swap: 15 gesture(s) glitch`). Reuses
  `playerswap.scripted_gesture_ops` (the same controlled-leader-targeted gesture count the swap + CLI warn use)
  — `.eb`-only, no new scanner. 1 test (`tests/test_forkreport.py`). kit 0.9.33.

### Added — item stat/effect catalog: the Info Hub now shows what an item DOES (0.9.35)
`ff9mapkit items` and the Info Hub item detail were names-only; they now surface **weapon power + element**,
**armor defence**, **equip stat bonuses + elemental affinity**, the **consumable use-effect**, **price**,
**type/slot**, **who can equip it**, and the **abilities it teaches**.

```
$ ff9mapkit items -f excalibur
   28  Excalibur         weapon - Atk 77 Holy, 19000 gil
   30  ExcaliburII       weapon - Atk 108 Holy, 39000 gil
```

- New `itemstats.py` JOINS the five FF9 item-data CSVs (`Items` + `Weapons`/`Armors`/`Stats`/`ItemEffects`,
  keyed by the catalog's FKs) into one `ItemStat` per id, with `summary()` (one-line) + `facts()` (the detail
  pane). Element/weapon-category/type bitmasks decode to names (`Fire`/`Holy`, `short-range/throw`, …).
- **Provenance:** item STATS are game DATA, so — unlike the committed names table `_itemdb.py` — they are
  **never committed**. `itemstats` reads them **live from YOUR install** (`<install>/StreamingAssets/Data/Items/
  *.csv` — Memoria's editable item tables) and caches in-memory; the repo/wheel ship nothing. Column layout is
  read from each CSV's `#`-legend (not hard-coded indices), so it survives Memoria's option-driven column
  toggles. If the install isn't reachable, every accessor returns `None`/`[]` and the Info Hub degrades to
  id+name (it still works offline). See docs/PROVENANCE.md.
- Wired into `infohub.py` (browse summary + detail facts) and the `items` CLI; both degrade gracefully.
- Consumable use-effects decode the `BattleStatus` mask (a cure/revive item like Phoenix Down has Power 0 and
  acts entirely via the status set), so it shows `effect status Death` rather than a misleading `use pow 0`;
  an all-zero effect row (a stat accessory with a dummy EffectId) shows no use-effect line at all.
- 11 tests (`tests/test_itemstats.py`): pure decoders/parser/formatters + graceful-degradation run offline;
  the real-value join (Dagger Atk 12, Excalibur Atk 77 Holy, Iron Helm M.Def 7, Potion/Phoenix-Down effects) is
  install-gated. Provenance + engine-fidelity + Python were adversarially reviewed (3 lenses). This is the
  read-only foundation the shop/reward/save-editor item pillars build on.

### Added — seamless New-Game entry: `eb.edit.nop_cinematics` + `tools/skip_opening_fmv.py` (0.9.38)
A spin-off from verifying how a New Game reaches a custom field (memory `project-ff9-new-game-entry`): the whole
path is **engine-independent** (the only custom DLL is the F6 menu; `NewGame()` is stock `fldMapNo = 70`, and a
mod **overrides field 70** `EVT_ALEX1_TS_OPENING` to `Field(4003)` after its opening movie). This adds the lever
to make that entry **seamless**, all stock:
- **`eb.edit.nop_cinematics(data, *, entry_index=0, func_tag=0, before_op=0x2B)`** — NOPs every `Cinematic`
  (`0x28`, FMV-playback) op in a function up to the first `Field()` warp, **length-preserving** (in-place `0x00`
  NOPs = engine-confirmed "do nothing", `DoEventCode` case `NOP`; no offsets shift, no jumps to fix). Returns
  `(new_data, n_nopped)`; byte-identical when there are no cinematics.
- **`tools/skip_opening_fmv.py`** — a dev-loop driver: auto-finds the live opening override across all language
  folders (or takes explicit paths), backs each up (per-language backup name — fixed a same-second collision),
  strips the pre-warp cinematics, `--dry-run` supported. Provenance-safe (operates on local/deployed `.eb`s; the
  repo ships no SE bytes). In-game: drop the 2 cinematics in field 70's override → New Game lands in the target
  field instantly, no FMV, no DLL, no `SkipIntros` (that's boot-only).
- 1 test (`tests/test_eb.py::test_nop_cinematics_strips_only_pre_warp_fmv`): pins that only the pre-warp cinematic
  is NOPed, the warp + post-warp cinematics survive, and the `.eb` still round-trips. *(In-game verification of
  the instant New Game is the human step.)*

### Added — `fork-report` Items / Treasure axis: preview the treasure, gil & shops a fork reproduces (0.9.32)
The item-side companion to the Player / Roster / Interaction / Dialogue / Party axes — what a fork does to your
**inventory**. Read-only; reuses the kit's disassembler (no new scanner of its own).

- `forkreport.scan_item_ops` decodes the item ops a field's `.eb` runs: `AddItem` (`0x48`), `AddGil` (`0xCE`),
  and shop opens `Menu(2, id)` (`0x75`). A `--verbatim` fork RUNS these byte-identically; a plain/synthesize
  fork has **no item scanner**, so it **DROPS** every treasure + shop. A shop's stock is also parasitic on the
  base `ShopItems.csv` (a fork can't change the inventory) — the line says so.
- Item ids are classified by the engine's pool rule (`ff9item.FF9Item_Add_Generic`, `id % 1000`): 0-255 regular
  (named via `items`), 256-511 key item, 512-611 Tetra Master card, `>= 612` **inert** (engine no-op → excluded).
  A plain 0-255 regular id is named; higher pools are classified but unnamed.
- Counts are **per-grant maxes, not summed** across the field's mutually-exclusive story branches (else an Ether
  granted on two paths would read as "x2"); a gil literal above the 9,999,999 cap is suppressed as a scripted
  sentinel ("gil (scripted)"). Computed-id grants/shops surface as "computed-id item(s)" / "opens a story-gated
  shop" (the latter recovers 42 gated-shop fields incl. Dali inn 351 / Ice Cavern 300).
- Validated by a 3-lens adversarial-review workflow (engine-fidelity / Python-correctness / scale over all 676
  real fields): the decode is engine-exact, zero false positives; it caught a latent under-report (computed-id-only
  grants/shops rendered nothing) that this lands fixed. 12 tests (`tests/test_forkreport.py`). `forkreport.py` only.
- Recon context: the engine's full item/equipment data model is **CSV-moddable on stock Memoria**
  (`StreamingAssets/Data/Items/*.csv`, no DLL rebuild) — see memory `project-ff9-items-equipment` + docs/FORK_REPORT.

### Added — `--swap-player` accepts ANY model (the field-side bridge to custom characters)
- `--swap-player` (single `import` and `import-chain`) now takes a playable name OR **any registered model** —
  a `GEO_..` name or a numeric id (a moogle `199`, `GEO_NPC_F0_BMG`, …; `ff9mapkit models`). A playable uses
  its proven home-field rig table; any other model resolves its 5 movement clips (stand/walk/run/turn) via the
  kit's model→animation join (`catalog.npc_anims`), so you can **walk as a moogle / an NPC / a creature**. A
  model with no movement (a static monster) raises cleanly; an arbitrary model keeps the field's eye-height
  (cosmetic dialog anchor). This is the **field-side bridge to custom characters** — a registered custom model
  would be driven by exactly this path (`SetModel` + movement clips), no DLL. Smoke-verified (Vivi field → a
  moogle). 2 tests. ★ Cross-rig GESTURE remap was probed and is **infeasible** — a cutscene field's player
  gestures are scene-specific (Vivi field 100's 15 = KOKE/RECEIVE/GIVE/KISS_ME/HIZA, **0** with a Steiner
  equivalent), not a shared vocabulary, so the cutscene-glitch caveat is fundamental and the `WARN` stays the
  right handling. `playerswap.resolve_char` (general) + `cli.py`; read-only join reuse. kit 0.9.30.

### Added — `[party]` block: add/remove party members at field load (0.9.31)
The authoring complement to overworld's `import --swap-player` — where that changes who you **walk as**,
`[party]` changes who's **in the party** (the menu + battle roster). Field *control* and party *state* are
decoupled (memory `project-ff9-pc-party-system`); this is the declarative half flagged for the story_flags
lane.

```toml
[party]
add    = ["steiner", "vivi"]   # add existing playable characters (B_PARTYADD, the real JOIN form)
remove = ["zidane"]            # optional: RemoveParty
```

- New `content/party.py`: `add_member` emits the **in-game-proven** probe bytes `05 C5 93 7D <id> 00 6D 2C
  7F` (op `0x6D` `B_PARTYADD` — the kit had no expression-opcode emitter for it; this is the first), and
  `remove_member` is `RemoveParty` (`0xDD`) via the existing `opcodes.encode`. `party_body`/`inject_party`
  prepend the sequence to **Main_Init** like `[startup]` (`edit.insert_in_function`, byte-safe; byte-identical
  when the block is absent). Names resolve via a CharacterOldIndex table (Zidane 0..Blank 11; aliases
  `dagger`/`salamander`; bare `0`–`11` ok) kept in lockstep with `forkreport.CHAR_OLD_INDEX` by a test.
- Wired into `build.py`: `_apply_party` runs in BOTH the synthesize path (`build_script`) and the verbatim
  `.eb` path (`build_field`) — so a verbatim fork's `[party]` fires too, mirroring `[startup]`/`[[on_entry]]`.
  `validate()` resolves every name (`_validate_party`). ★ A verbatim fork that rebuilds the roster
  (`SetPartyReserve`, `0xB4`, which runs **after** our prepend → can wipe the op) gets a build **warning**
  (`field_resets_party` scan). `.eb`-only, no DLL; FF9 renders only the leader, so an added member shows in
  the menu/battle, not as a field follower. No flag allocation (party state, not gEventGlobal).
- **Adversarial review (3-lens workflow) caught two real bugs the tests missed — both fixed before landing:**
  (1) **jump-table crash** — `inject_party` (and the pre-existing `[startup]`/`[[on_entry]]`) raised an *opaque*
  `ValueError` on the ~11% of real fields (incl. **field 100**) whose Main_Init opens with a 0x06 jump table the
  byte-inserter can't shift past. Now the verbatim path **fails closed** with a clear `BuildError` (shared
  `_field_load_inject` wrapper, all three levers). (2) **wipe-warning blind spot** — the reset scan only looked
  at entry-0/tag-0, but real `SetPartyReserve` lives in object Inits / tag-1 (only **2 of 111** reset fields keep
  it in Main_Init); broadened to all non-empty entries' tag-0 + tag-1 (`field_resets_party`, catches 111/111).
  Plus two minor fixes: the wipe gate widened to `add OR remove`, and `inject_party` normalized to accept bytes
  or `EbScript`. Doc note: don't `remove` every member (an empty party hangs the menu).
- 12 tests (`tests/test_party.py`): emitters pinned to the proven probe, name/alias/int resolution + errors, the
  table↔forkreport lockstep, build injection (prepended, parses clean), byte-identity when absent, validation
  shapes, the broadened reset scan (a non-Main_Init `0xB4` is detected), and the jump-table fail-closed guard.
  (Adding a brand-new *custom* member is still the engine-fork frontier — Tier C in the memory.)

### Added — `import-chain --swap-player <char>`: play as one character across a whole forked region
- `import-chain <seed> --swap-player steiner` swaps EVERY verbatim member's player rig, so you walk as the
  chosen character across the whole forked slice (implies `--verbatim`; party/menu unchanged). Factored a
  shared `extract.apply_player_swap(toml, char)` (the sidecar swap, used by both the single import and the
  chain); `campaign.write_campaign(swap_player=…)` applies it per member + records `swap_gesture_warn`
  (cutscene members whose gestures glitch) and `swap_skipped`; the CLI summary reports the swap.
- ★ The swap-TARGET was fixed by an adversarial review (3-lens workflow) that the test suite missed: on a
  **Zidane-present** multi-PC field, `controlled_player` mispredicts (control routes through the party SLOT to
  the Zidane leader, not the last-`DefinePlayerCharacter` binder), so the swap was re-skinning a **co-actor**
  (Vivi/Garnet) while you still controlled Zidane — **66 of 169** such fields (Cargo Ship 500, Dali Wheel 350…).
  Now the swap targets the controlled-**leader model**: a Zidane field form (98/532) when present, else the
  proven binder for the no-Zidane fixed-SID lane; it patches ALL entries matching that model (`playerswap.
  leader_model` / `swap_targets`). Also: `controlled_player` downgrades to `low` confidence on a Zidane-present
  field; `swap_player` raises a distinct `NoSwappablePlayer` (so a chain SKIPs a no-player member but a real
  overflow/corruption ValueError still propagates loudly); the chain validates the char BEFORE the graph walk
  (true fail-fast); the summary is qualified ("N verbatim member(s) swapped"). 3 tests incl. a Cargo-Ship
  regression (swap hits Zidane, the Vivi co-actor untouched). kit 0.9.29.

### Added — `fork-report` Party axis: what a fork does to your party
- `fork-report` now reports a **Party** line — the party-membership ops a field performs, which a `--verbatim`
  fork RUNS (a plain fork inherits your current party). It decodes the literal single-char `B_PARTYADD`
  (`B_CONST <CharacterOldIndex> B_PARTYADD`, the expr op `0x6D`) inside expression statements + the statement
  party ops (`RemoveParty` 0xDD, `SetPartyReserve` 0xB4 = roster rebuild, `SetCharacterData`/JOIN 0xFE, `Party`
  menu 0xB2) — e.g. field 60 "adds Zidane, Vivi, Garnet, Marcus; sets the recruitable roster", field 100 "adds
  Vivi; rebuilds the roster (story reset)", the Dali Inn "opens the change-members menu"; a party-neutral field
  (the Hangar) gets no line. The `NONE` (0xFFFF) add-terminator is filtered and the lists are deduped. Read-only
  (`forkreport.py` only; `scan_party_ops` reuses the disasm) — completes the fork-preview (Player / Roster /
  Interactions / Dialogue / Story-gating / **Party**), and directly serves the PC/party goal (the recipe lives
  in memory `project-ff9-pc-party-system`). 4 tests (`tests/test_forkreport.py`). kit 0.9.27.

### Added — `import --swap-player <char>`: walk as a different existing character (Tier A, productionized)
- Fork a field and **swap who you walk as** to any existing playable — `import <field> --swap-player steiner`
  (zidane/vivi/steiner/garnet/freya/quina/eiko/amarant; aliases dagger, salamander). It patches the player
  entry's Init `SetModel` + the movement anim ids (idle/walk/run/turn-L/turn-R/idle-break) to that character's
  rig — a same-length, width-aware byte patch (`playerswap.swap_player`). Implies `--verbatim` (it needs the
  donor's real player entry in the shipped `.eb`); **party/menu state is unchanged** (field control and party
  roster are decoupled). The character table is real data, EXTRACTED from each character's home field (model
  id + eye-height + movement clips). ★ The productionized form of the **in-game-proven Tier-A probe** (walk as
  Steiner in a Zidane field; memory `project-ff9-pc-party-system`). New module `ff9mapkit/playerswap.py`
  (read-only transform) + the `--swap-player` flag wired through `cli.py` (forces verbatim, applies the swap to
  the shipped sidecar `.eb`). `.eb`-only, no DLL. ★ CAVEAT (warned): the swap repoints only the 6 MOVEMENT
  clips, so it's CLEAN on a free-roam field but on a CUTSCENE field the player's scripted GESTURES
  (`RunAnimation`, rig-specific) glitch on the new model — `playerswap.scripted_gesture_ops` counts them (Vivi
  field 100 = 15) and the CLI prints a `WARN`. For STORY fidelity (be a character *through* the story), use a
  verbatim fork at the right beat + the right party, not a model swap. 6 offline tests
  (`tests/test_playerswap.py`) — incl. a Vivi field→Steiner round-trip, a "swap to self is identity" check that
  proves the baked table matches the real game, and the gesture-warning detector. kit 0.9.26. (The complementary
  party-MEMBERSHIP authoring — `B_PARTYADD` etc. — is a declarative block in story_flags' lane; here only the
  fork-transform half landed.)

### Fixed — chest-band provenance: it is NOT the Treasure-Hunter scoring region (0.9.28)
Tracked down whether the kit's reserved "treasure-chest 'opened' bitfield" (bits **8376–8511**, bytes
1047–1063) is accurately attributed, after the modern-save safe-band audit flagged a possible conflation.
Verified directly from real `.eb` bytes (fields 115/300/2203/407 + 44 more):
- **The band IS real and correctly reserved** — ~48 chest-bearing fields (Ice Cavern, Burmecia Vault, Dali
  Storage, Cleyra, Palace, …) genuinely read-gate *and* set these bits. Custom flags there WOULD corrupt
  real chest state. `CHEST_FLAG_LO/HI`, the reservation, the lint, and `FIRST_SAFE_FLAG = 8512` are unchanged.
- **But the `EventState.GetTreasureHunterPoints` citation was WRONG** — that engine method scores a *separate*
  region (bytes **182–186 + 896–975**, already correct in `TH_POINT_RANGES`); the **stock engine never reads
  8376–8511** at all (grep-confirmed; the only chest-band reference in the engine tree is the kit's own F6
  debug-menu label). The chest band is justified by the field-script census alone.
- **And "every bit a 48-writer computed index → identity not static" was a misread** — the 48-writers-per-bit
  pattern comes from a **byte-identical 130-entry dispatch block** compiled verbatim into ~48 chest fields
  (fields 115 vs 300 share the same SHA over the 130 `bit = 1` statements), each statement targeting a
  *literal* bit index in a branch — a static block, not a runtime-computed index.

No behavior change (band bounds, reservation, safe band, TH scoring all identical). Corrected the prose +
citation in `flags.py` (the `chest_opened` region), the gate advisory in `build.py`, and the research record
(`research/STORY_FLAGS.md`, `research/make_catalog.py`); added a regression test asserting the chest band and
the engine TH-scoring bytes are disjoint and that the region no longer claims `GetTreasureHunterPoints`.

### Fixed — Story State console: B-slot dropdown + Memoria extra-save authority
- The Diff tab's **"B slot" dropdown couldn't be clicked** — it was created with no menu items and only
  populated when a *second* file loaded. It now fills from the loaded save's slots (or the B file's) on every load.
- **Memoria per-slot extra-save is now treated as authoritative** (the likely cause of "I set a flag but in-game
  it's still 0"): Memoria writes a per-slot `SavedData_ww_Memoria_*.dat` holding the gEventGlobal it RESTORES
  from on load, so the encrypted main block can be stale. `save.inspect` now reads the extra when present (and
  tags the slot) so the console shows what the game *actually loads*; `save.apply_story_edit` re-reads the extra
  after patching to **verify** the write took (`extra_patched`), and the GUI's Apply reports `[OK]` / `[WARN]`
  so an edit that won't show in-game is no longer silent. 3 save tests; kit 0.9.24.

### Added — Story State GUI console (inspect / diff / EDIT a save's story state)
- A new app `apps/ff9_storystate.pyw` (`StoryStateApp`) surfaces the story-flag pillar's save verbs in one
  window — the save-side companion to the Info Hub's story-flag *registry*: **Inspect** (each populated
  slot's ScenarioCounter→beat + story bits by named region, via `save.inspect` + `flags.render_report`),
  **Diff** (load a second save / slot → the A→B delta, `flags.diff_reports`), and **Edit** (set the
  ScenarioCounter / set+clear story bits → write back). Editing is **backup-guarded** (a `.bak` first) and
  **reserved-region-refused**, sharing the CLI's guards via a new `save.apply_story_edit` convenience
  (the in-place edit+backup+write+extra-patch path as one call, with a `dry_run` for the Preview;
  `edit_story_state` stays the shared core). Wired into the launcher + a Campaign-Editor tab. 3 save tests
  (`tests/test_save.py`) + a headless `--smoke` (inspect/diff crypto-free; edit-preview when pycryptodome is
  present). kit 0.9.23.

### Corrected — fork-fidelity #10 premise (entry cutscenes are `.eb`-borne, not a C# `NarrowMapList` trigger)
- A load-bearing belief in the docs/memory was **wrong** and is now corrected (verified directly in the Memoria
  source): `NarrowMapList.cs` is the engine's per-field **camera-WIDTH / widescreen** table (PSX screen widths,
  narrow-vs-wide cam, crop margins) with **zero** cutscene logic — its only callers are `FieldMap`/`PSXCameraAspect`.
  A field's **entry cutscene runs from its own `.eb`** (entry-0 + actor sequences), so a `--verbatim` fork carries
  it (in-game proven: Vivi/field 100's opening), and `[[on_entry]]` re-authors one for a synthesize fork. The
  "needs a dev-engine `NarrowMapList` patch" framing of #10 was a phantom; the only genuine engine-side residual is
  **cosmetic and keyed on the donor's real id** — widescreen camera-width (`MapWidth` defaults to 500 for a custom
  id), a few per-actor anim tweaks (`FieldMapActor.cs`), and FMV playback (field 70). Docs/comments-only correction
  across CLAUDE.md, FORK_FIDELITY.md, FORMAT.md, FEATURES.md, CAMPAIGN_IMPORT.md, `content/onentry.py`, `build.py`,
  the tests, and the project memory (no code-behaviour change).

### Added — `fork-report` Dialogue axis (the #5 text gap, previewed before you fork)
- `fork-report` now reports a **Dialogue** axis (orthogonal to the interaction-safety axis): how many carried
  NPCs **speak** (a tag-3 talk window) and how many lines — e.g. Daguerreo 2F "6 NPC(s) speak 36 line(s)".
  Their words render **wrong** unless the fork carries the text, so the line says ship with `--carry-text`
  (or `--verbatim`), pointing at the build-side lint (FORK_FIDELITY.md #5) as a *before-you-fork* preview.
  Read-only — reuses `dialogue.scan_dialogue` (the analysis-layer `.eb` reader), filtered to the carried
  objects' talk handlers; no scanner logic of its own. Validated on real fields (Daguerreo 6/36, Dali Inn
  1/8). 2 offline tests + an install-gated assertion (`tests/test_forkreport.py`); kit 0.9.21.

### Added — `fork-report` computes the REAL controlled PC in a multi-PC non-Zidane fork
- The control-bind mechanism is now **engine-sourced + in-game proven** (a 3-lens workflow over the Memoria
  C# + the donor bytes + a verbatim playtest). When a field defines >1 `DefinePlayerCharacter` (0x2C), the
  engine binds player control to the entry whose 0x2C **executes LAST** at load (`controlUID = gExec.uid`,
  last-write-wins, `EventEngine.DoEventCode.cs`); entries run their Init in **InitObject (0x09) order**, so the
  binder is the entry whose tag-0 Init runs a 0x2C **unconditionally** and is InitObject'd **latest**. It is
  **party-leader-independent** for fixed-SID character fields. ★ **IN-GAME PROVEN** on a verbatim fork of the
  Treno Dagger+Steiner room (`evt_treno1_tr_qhm_0`, shipped over the FBG scene): you control **Garnet** (entry
  9, last-executed 0x2C) — NOT Steiner (entry 10, spawned first), NOT Zidane (party leader); free-roam, and the
  bind persists across gateways. The party MENU still shows Zidane — `controlUID` is decoupled from party state.
- So `fork-report`'s **Player** axis now reports the *real* controlled character (`controlled_player` = last
  unconditional 0x2C by InitObject order) for a non-Zidane multi-PC field — e.g. `controls Eiko of [Garnet,
  Eiko]` — instead of the old `pents[0]` guess (the FIRST entry, which mispredicts: ac_alt binds Eiko not the
  first-entry Garnet). It's scoped to the non-Zidane lane (where it's validated); a **Zidane-present** multi-PC
  field keeps the conservative "likely Zidane party-leader" hedge (control there can route through a party slot
  to the live leader, which this doesn't model — the Cargo Ship would mispredict). Confidence is hedged (`?`)
  when the binder is multi-spawned or only gated. Read-only (`forkreport.py` only). 2 tests; memory
  `project-ff9-non-zidane-donors`. (No reliable offline free-roam-vs-cutscene flag exists — player-LOOP length
  doesn't separate them: Vivi-100/Dali-Inn free-roam at ploop 254/272, the ac_alt *cutscene* at 50 — so none
  was added; the first multi-PC probe burned a playtest on the ac_alt coronation cutscene.) kit 0.9.22.

### Added — `fork-report` is now PLAYER-CHARACTER aware (non-Zidane donors)
- A field's controlled character isn't always Zidane (Vivi/Steiner/Garnet/Eiko/Freya/Amarant solo sequences).
  A census of all 818 field `.eb` (one events-bundle pass; `eventscan.resolve_player_entries` + `_player_model`)
  found **178 non-Zidane-primary** fields, ~80 *truly playable as a party member*. `fork-report` now reports a
  **Player** axis: who you play as, single- vs **multi-PC** (`[MULTI-PC]`), and — for a non-Zidane controlled
  character — switches the suggested recipe to **`--verbatim`** (which ships the donor player rig + anim packs
  + the field's own party/cutscene setup whole; the `--graft-player-funcs` path *drops* a non-Zidane player's
  funcs as `"model"` graft-safety — another rig's clip ids). The multi-PC inference is conservative: the FIRST
  `DefinePlayerCharacter` is NOT reliably who you control (the Cargo Ship lists Blank first; you play Zidane),
  so a single-PC field is crowned confidently while a multi-PC field is only called non-Zidane-controlled when
  **no Zidane is among the PCs** (the Treno Dagger/Steiner split) — else it's flagged "likely the Zidane
  party-leader; co-actors are the rest". **★ In-game proven (Vivi / Alexandria street, field 100):** a
  `import --verbatim` fork plays IDENTICALLY — Vivi renders + animates + is in the party menu, and the field's
  real ticket-girl opening cutscene plays (so that intro lives in the `.eb` entry-0, not a C# `NarrowMapList`
  table — the verbatim fork carries it). So a clean single-PC non-Zidane field already forks faithfully with
  ZERO new code; the frontier is the multi-PC / scenario-gated-player bind. Read-only (`forkreport.py` only),
  reuses the existing scanners. 2 tests (`tests/test_forkreport.py`); memory `project-ff9-non-zidane-donors`.
  kit 0.9.19.

### Added — softlock / wrong-text lint for a plain (no-carry) import (FORK_FIDELITY.md #5)
- A plain `import` (no carry flags) carries a real field's objects but **not** their player funcs or dialogue
  text, which can softlock or mis-render in-game. Both halves are now caught **build-side, offline**:
  - **(b) dangling player tag = the softlock** was already a build-blocking `validate()` error — a carried
    `[[object]]` that `RunScript`s the player at an un-grafted tag (`_entry_player_call_tags`).
  - **(a) un-carried talkable text = wrong/missing dialogue** is the new piece: `lint_logic` decodes each
    carried object's talk windows (`_entry_window_txids` — mirrors the player-call decoder) and warns when a
    shown donor txid isn't in the `[carry_text]` plan (\"import with --carry-text, or author the line\").
  Validated against real imports — a plain `--native` Daguerreo fork flags all 5 talkable NPCs, a
  `--carry-text` fork is silent (no false positive), props are skipped. Reads only stable build-side
  representations (the `[[object]]` bins + the carry plan); orthogonal to the eventscan classifier.
  5 tests (`tests/test_carry_text_lint.py`); kit 0.9.20.

### Added — message-in-verbatim: an `[[on_entry]]` narration line now SHOWS in a verbatim fork
- After the convergence (`build._apply_on_entry` runs on the verbatim path), an `[[on_entry]]` gated
  state-advance already fired in a `--verbatim` fork — but the narration **message** was dropped (the donor
  `.mes` ships verbatim, with no slot for authored text). Now the authored line is **appended to the donor
  `.mes` above its max txid** (`build._verbatim_on_entry_messages`, floored at `textcarry.CARRY_BASE_TXID`
  1000 — the same append-and-resolve trick `--carry-text` uses), and the hook's `WindowSync` resolves into
  it. So a verbatim fork's on_entry beat now fires its message **and** its state-advance on top of the
  donor's real logic. `_apply_on_entry` is unchanged (its `drop_messages` param stays a general capability);
  only the verbatim branch of `build_field` now supplies the text channel, and the now-obsolete
  "message won't show in verbatim" lint warning is retired. **In-game proven** on a Dali-Inn verbatim fork
  (the appended line renders, `set_flags` advances state, the inn's own NPCs still speak their real lines).
  3 tests (`tests/test_on_entry.py`); kit 0.9.18.

### Added — deploy-time text-block SHADOW guard (`deploystack.py`)
- A field loads its dialogue by **mesID** (`text_block`), and the engine reads that `.mes` from the **first**
  mod folder in `Memoria.ini` `FolderNames` that defines `field/<mesID>.mes`. When several stacked worktree
  mod folders (`FF9CustomMap-*`) all use the kit-default block **1073**, a lower-priority folder's text is
  **shadowed** — the field renders a *higher*-priority folder's block-1073 text instead. This bit an
  `[[on_entry]]` playtest: a probe in `FF9CustomMap-sf` showed `FF9CustomMap`'s stale "Rally-ho!" rather than
  its authored line (the flags were correct; only the text was someone else's). `tools/deploy_field.py` now
  **warns at deploy time** — naming the shadowing folder and suggesting real mesIDs no higher-priority folder
  defines (e.g. "use text_block = 187"). The check is a pure, offline, tested kit function
  (`deploystack.check_text_block_shadow` / `parse_folder_names` / `shadow_warning`); deploy also accepts
  `--text-block N` (or `text_block = N` in `.ff9deploy.toml`) to pin a worktree-unique block. 8 tests
  (`tests/test_deploystack.py`). kit 0.9.16.

### Added — `[[on_entry]]`: gated, once field-load beats (FORK_FIDELITY.md #10)
- *(Premise corrected later — see "fork-fidelity #10 premise" below: a field's entry cutscene runs from its own
  `.eb`, so a verbatim fork carries it; `[[on_entry]]` re-authors one for a synthesize fork. The "C# `NarrowMapList`
  table" framing was a misread — that's the camera-width table.)* `[[on_entry]]` is the declarative re-authoring
  hook: fire a narration `message`
  and/or story-state writes (`set_scenario` / `set_flags`) the moment the player **enters** the field, **once**,
  but **only when the story state matches** (`requires_scenario` = a ScenarioCounter `== N`, and/or
  `requires_flag`). The gating is the new capability — neither `[startup]` (unconditional, every entry) nor
  `[cutscene]` (ungated, single) can say "fire this beat only at scenario N / when bit B is set". Each hook is a standalone code entry armed by an `InitCode`
  in Main_Init (the proven narration-cutscene arming, now robust for any count via the region-arming fix below),
  so it runs at field load *before* control is re-enabled (hence no movement gate); a `message` beat reuses the
  cutscene's reorder-`Wait` + `DisableMove`/`EnableMove` lock so the window shows cleanly during the entry fade.
  `content/onentry.py` + `build.py` (validate / collect_text / inject / lint) + `flags.py` (name resolution,
  read/write parity); surfaced in the dialogue viewer/editor (`collect_text_refs`). Byte-identical when absent.
  An adversarial pre-commit review (4 read-only lenses) hardened two edges: the single-field auto once-flag
  band is guarded against reaching FF9's reserved chest bitfield (a `BuildError` instead of silent save
  corruption), and `lint_logic` warns when `[[on_entry]]` coexists with a `--verbatim` fork (which ships the
  donor `.eb` as-is, bypassing the hook). 16 tests (`tests/test_on_entry.py`); 828 suite. kit 0.9.15.

### Fixed — region arming silently lost on fields with >2 regions
- `eb.edit.activate` (the Main_Init region-arming primitive) overwrites a `Wait` filler shift-free, but the
  blank/borrowed template has only **2 `Wait` fillers**; the 3rd+ region fell back to a raw `insert_bytes` at
  a **stale Main_Init position**, so the 2nd+ insertion landed in already-consumed bytecode and that region
  **silently never armed** (its trigger never fired). It bit a forked **campaign chain** (a field's 2 gateways
  consumed both fillers, so its on-entry events never fired) and would bite any content-rich fork. Fixed by
  routing the fallback through `insert_in_function` (the fpos-fixing insert, same primitive `[startup]` uses),
  so any number of regions arm correctly even on a borrowed field with a real entry-0 tag-1 function.
  Within-budget fields (≤2 regions) still hit the patch path and are **byte-identical**. New `tests/test_arming.py`
  (5 regions all arm; the `.eb` stays parseable). Surfaced by an adversarial diagnosis workflow.
- `build.lint_logic` now counts a gateway's `set_flags` and `[startup]`'s `flags` as flag **setters**, so a
  same-field "a door reveals an NPC" pattern no longer false-warns "no event sets it".

### Added — `fork-report`: preview a real field's fork fidelity (offline)
- **`ff9mapkit fork-report <field>`** (id or FBG substring) answers, before you fork, "will this field play
  faithfully?" — reading the compiled `.eb` with no game running. It reports two INDEPENDENT axes:
  **roster fidelity** (how many objects a fork carries, how many are `Field()`-warp **directors** = cutscene
  actors carried as NPCs, and whether content rotates by story beat) and **interaction fidelity** (per NPC,
  whether its talk handler ports — `clean` = fully interactive / `init_only` = render-only / `refuse` = stub).
  Plus story-gated doors, the ScenarioCounter **beats the field gates content on**, and a suggested
  `[startup] scenario` (the earliest gate) + `import` recipe. Verdict: a clean static-roster field (forks
  faithfully) vs a story-event field (a high-fidelity diorama — rotating cast / cutscene actors). Validated:
  the real Dali Weapon Shop → STORY-EVENT (1 director, 11 rotating beats Dali→Pandemonium); Daguerreo 2F →
  CLEAN static-roster. **Read-only** — reuses `eventscan.scan_objects_verbatim` (the carry `graft_safety`
  classification) + `scan_gateway_entries` + the `flags` beat table; adds no carry/scanner logic. New module
  `ff9mapkit/forkreport.py` (pure `analyze_eb` + thin id-loader, unit-tested offline against a fixture).
  Surfaced as a **Preview fidelity** button in the FFIX Import GUI (`apps/ff9_import.pyw`) — standalone and the
  Campaign Editor's Import tab — so you can read the verdict before importing.
  (`docs/FORK_REPORT.md`; `docs/FORK_FIDELITY.md` — the north star is "fork a real field → does it play identically?")

### Added — `[[gateway]]` on-exit story advance (fork-fidelity #3)
- A `[[gateway]]` can now **advance story state when the player takes that exit**: `set_scenario = N | "area"`
  bumps the ScenarioCounter and `set_flags = [{flag = <index|name>, value = 0|1}]` sets/clears gEventGlobal
  bits. The `set_var` writes are prepended to the gateway's Range trigger **behind a `usercontrol` guard**
  (so they fire on an actual walk-out, not a puppeted pass) and **behind any `requires_flag` gate** (so a
  gated door only advances the story when it's actually open), just before `Field()` — the values commit to
  the save-backed gEventGlobal before the transition. This is the write-side complement to `[startup]`'s
  entry-side assert: a forked field **chain** can now progress the beat as the player moves through it.
  Reuses `content/startup.startup_body`; `validate` + the reserved-band `lint` mirror `[startup]` (a write
  into a reserved region is flagged). Flag **names** in `set_flags` (and `[startup]`'s `flags`) resolve at
  load against the project's `[[flag]]` table **merged with campaign-shared names** — read/write parity with
  `requires_flag`, so a campaign member can write a shared story flag by name. Byte-identical build when the
  keys are absent. (`docs/FORK_FIDELITY.md` #3.)

### Added — FFIX Import GUI: the import-from-game functions, made discoverable
- **`apps/ff9_import.pyw`** — a front door to the kit's "bring content in from the real game" commands, so
  the powerful but cryptic `import` flags become **plain checkboxes**. Two tabs: **Field** (pick a real
  field — `Find…` runs `list-fields` — choose Background art `Native` / BG-borrow / Editable, and tick what
  to carry: *NPCs & props* / *real dialogue* / *dialogue stubs* / *save point*; then `Import field`) and
  **Read & Inspect** (`dialogue-import` a field, `flags-inspect` a save, `list-fields`, regenerate base
  templates). Each action shells out to `py -m ff9mapkit …` from the kit root and **streams** the output;
  the Field tab ends with a "→ deploy with Build & Deploy" hint. Standalone (in the `ff9_studio` launcher)
  **and** a new **Import** tab in the Campaign Editor. The fidelity mapping is a pure, smoke-tested
  `import_args()` (e.g. Native + carry-NPCs + carry-text → `import <f> --out … --id … --native
  --graft-player-funcs --carry-text`).

### Added — `[startup]`: assert the story beat a forked field represents
- **A forked real field boots with a zero `gEventGlobal`**, so every story-gated NPC/door/event takes the
  not-yet-happened branch — the field plays in its scenario-zero state. The new **`[startup]`** block presets
  the **ScenarioCounter** (`scenario = N` or an area name like `"Alexandria Castle"`) and/or specific story
  bits (`flags = [{flag = <index|name>, value = 0|1}]`) **unconditionally at field load**, prepended to
  Main_Init so every gate evaluated afterwards sees the asserted state. The biggest single fork-fidelity lever
  (`docs/FORK_FIDELITY.md` #1): a fork can finally boot in the right beat.
- Author-side only (you assert the beat — you have the game knowledge); no extraction. The ScenarioCounter is
  written via the engine's `0xDC` token (`set_var(GLOB_UINT16, 0, value)`); a story bit via
  `set_var(GLOB_BOOL, idx, value)` (long-index aware). Injected with `edit.insert_in_function` (entry-0 tag-0,
  offset 0 → byte-safe, fpos fixed), so a field **without** `[startup]` builds byte-for-byte as before.
- Unlike authored `set_flag` (safe `[8512,16320)` band only), a `[startup]` preset is *meant* to assert REAL
  FF9 story bits below 8512 — so the safe-band rule doesn't apply; the lint still flags a preset into a
  genuinely *reserved* region (chest bitfield / byte-23 handshake / worldmap unlocks / choice scratch).
  Spine: `content/startup.py`. *In-game verification (F6 reads the asserted beat) is the human step.*

### Added — story-flag registry depth: the worldmap Navi known-location words
- **Four new engine-grounded named vars** (`flags.NAMED_WORDS`): `WorldmapKnownLocationsF0..F3` (bytes
  92/94/96/98, UInt16, tier a) — the worldmap Navi cursor's known-location bitmasks (`keventNaviLocF0..F3`;
  F0 is the engine's own `knownLocations`). The first engine-reader pass grepped `gEventGlobal[<const>]`
  directly and missed the wrapper-accessor form (`ushort_gEventGlobal(92)`); re-scanning the complete
  fixed-index set recovered them. Naming bytes 92–99 as words also reclassifies that slice of the
  "write-only worldmap-unlock bits" as recognized word data (a decoded save now reports
  `WorldmapKnownLocationsF0 = N` instead of anonymous set bits). Surfaces automatically through
  `flags-inspect` / the Info Hub / `flags-diff`. `NAMED_WORDS` stays tier-(a)-pure (tested invariant).

### Added — dialogue polish: campaign-wide review + a live-text resolver diagnostic
- **`ff9mapkit dialogue` now accepts a `campaign.toml`** (it auto-detects a `[campaign]` manifest) and
  reviews **every member field's** authored dialogue in one pass — per-field sections with the final
  on-screen wrapping, plus a roll-up (total lines, which fields may overflow). A member that fails to load
  is noted and skipped, never aborts the review. Single-field `dialogue <field.toml>` is unchanged. Spine:
  `dialogue.campaign_dialogue` + `dialogue.flag_overflow` (the overflow check, now shared by both paths).
- **`dialogue-import` now says WHY a real field's text didn't resolve.** When the live `<zone>.mes` read
  comes back empty it distinguishes the two install/dependency failure modes — UnityPy not installed, or
  the game install / `resources.assets` not found (pass `--game`) — from "the source is fine, the field's
  block just didn't cover these txids; pass `--zone-id`." Spine: `dialogue.text_source_status` (never raises).
- **`ff9mapkit lint <field.toml>` runs the WHOLE offline suite in one go.** It used to be schema
  (`validate`) + story/flag logic (`lint_logic`) only; the walkmesh geometry / content-placement /
  layer-art / cutscene-movement checks lived behind `walkmesh verify`, and the camera-pitch advisory
  behind `guide`. They now all surface through `lint`, grouped by `[section]` — `logic`, `flags`,
  `placement`, `camera`. The pass degrades gracefully: a project whose camera/walkmesh can't resolve
  still reports its schema + logic findings (the resolve failure is recorded as an error, never a crash).
  Spine: `build.lint_all(project) -> LintReport` (the single source of truth; `walkmesh verify` is
  unchanged and still standalone).
- **New check — reserved story-flag bands.** A raw `set_flag = [N, 1]` / hand-written once `flag = N` /
  `requires_flag = N` (on an event, NPC, **prop**, gateway, cutscene, or choice) that lands in a *reserved*
  `gEventGlobal` region (the treasure-chest 'opened' bitfield 8376-8511, the byte-23 menu handshake, the
  worldmap-unlock bits, or the choice-mask scratch) is flagged and named — a WRITE there corrupts real
  save/engine state; a chest-band READ is unreliable. This extends the `[[flag]]` validator's safe-band
  guard to the literal indices that bypass it. The kit's established 8000+ working band is free space, so
  it draws no warning. `build.lint_flag_bands`.
- **Refined — the off-walkmesh content check no longer cries wolf on back-wall NPCs.** An NPC is placed by
  a world transform and renders regardless of the walkmesh; a normal FF9 NPC stands against the back wall,
  just past the floor edge, and the player talks to it from the adjacent floor. The check now HARD-warns
  only when an NPC is *grossly* off (farther than talk reach outside the floor's bounding box — a real
  misplacement), instead of flagging every edge-adjacent NPC as "will float / be unreachable." The player
  spawn and ladder landings still require being on the mesh. (Fixes a false-positive the unified `lint`
  exposed on the in-game-verified `vivi-hut` oracle; affects `build` / `walkmesh verify` warnings too.)

### Added — `flags-diff`: compare two saves' story state
- **`ff9mapkit flags-diff <A> [B]`** decodes two saves' `gEventGlobal` and shows the **A → B delta** — the
  ScenarioCounter change (with beat names), FieldEntrance, Treasure-Hunter points, chests, named word vars,
  and the story **bits set / cleared** (grouped by named region). The practical way to learn what a story
  beat writes: save before, do the thing, save after, diff. Reads the same forms as `flags-inspect` (an
  encrypted `SavedData_ww.dat`, a Memoria extra-save, a save JSON, or a bare Base64 blob); with one save,
  `--slot-a` / `--slot-b` diff two slots (default slot 0 → slot 1). Spine: `flags.diff_reports` /
  `flags.render_diff` (the bit-grouping is shared with `render_report`, so a bit is classified identically).

### Added — faithful object carry v1.5: the STARTSEQ-helper closure (+ two v1 correctness fixes)
- **A forked object now carries the concurrent Seq it launches.** A real field object often runs a
  benign per-frame helper via `STARTSEQ` (RunSharedScript) — a forward-lean, a shadow toggle, a small
  animation loop. v1 dropped that helper, so the object was REFUSED (left to a hand-authored stub).
  v1.5 carries the helper too — appended at a free slot and the launcher's entry-arg remapped, exactly
  like the proven ladder `sequences` graft — so the object renders faithfully. Across the real game this
  **un-refuses 53 objects and un-stubs 23 more** (faithful object coverage ~65% → ~70%); 109 helpers are
  carried, every one a benign type-1 Seq. Always on for `import` (a pure fidelity win, no flag).
- **The closure is body-vetted, not blind.** A helper that runs a cutscene op — a `MoveCamera` sweep, a
  `Battle`, a `Field`/`PreloadField` warp, a menu, a window — is NOT carried (it would fire in a static
  fork): those objects stay refused. The helper is appended-but-never-armed (a Seq is launched at runtime,
  not `InitObject`'d) and a helper shared by several objects is appended **once** (field-scoped dedup).
  `ff9mapkit lint` rejects an unsafe / non-type-1 / nested-STARTSEQ / double-armed helper.
- **Sibling-OBJECT closure was investigated and found EMPTY** — every uncarried object-to-object reference
  resolves to the party, the player, a controller, save machinery, or out-of-range, so there is nothing
  safe to carry there; v1.5 is exclusively the STARTSEQ-helper closure (a 676-field census + adversarial
  verification).
- **Fix: a sibling read inside an EXPRESSION operand is now remapped.** A grafted body that reads another
  object via the `op78` (B_OBJSPECA) expression token kept the donor's entry index after the move → it
  acted on the wrong/empty fork entry. The graft now walks the expression token stream and remaps it (a
  same-length 1-byte patch) — fixing ~31 already-shipped v1 objects as well as the closure.
- **Fix: a field with several `DefinePlayerCharacter` entries (182 of them) is classified correctly.** A
  reference to a *secondary* player entry was mis-read as an uncarried sibling; it now classifies as the
  player and the graft normalizes every PC entry to the runtime controlUID (250). Removes ~170 false
  "uncarried" refs and 7 secondary-PC false objects.
- Single-field authored builds stay **byte-identical** (the closure is off by default in
  `scan_objects_verbatim`; the hut SHA-256 golden is unchanged). Every real field's objects graft and
  round-trip (676/676, 0 errors). See `docs/OBJECT_CARRY.md` §2.

### Added — dialogue pillar (a dialogue editor + a stock-dialogue viewer)
- **The read side of FF9 field text.** New `ff9mapkit.dialogue` spine (UI-agnostic, tk-free): `parse_mes`
  (the missing `.mes` reader — handles BOTH the base game's index-implicit entries, where the txid is the
  entry's 0-based position with no `[TXID=]` tags, and the kit's explicit form it round-trips), `scan_dialogue`
  (decode every dialogue-window call + its txid out of a field's `.eb`), and `read_local_dialogue` /
  `read_field_dialogue` that JOIN the two into "NPC → text". A real field's text block is found via the
  engine's own `eventIDToMESID` table (baked into `_fieldtext.py`), language picked by stopword match.
  `project_dialogue` lists a `field.toml`'s authored lines with their final on-screen wrapping. The proven
  write path (`content.text` wrap/build_mes) is untouched — goldens stay byte-identical.
- **`ff9mapkit dialogue <field.toml>`** views a field's authored dialogue (every NPC line / event message /
  choice prompt+reply / cutscene say) and how each line wraps; flags lines that may overflow the window.
- **`ff9mapkit dialogue-import <field>`** reads a REAL FF9 field's dialogue live from your install and shows
  "NPC → text" — the "import from the game to prove plausibility" verb. `--mod <built mod folder>` reads a
  field offline with no install (the kit's own shipped hut joins to *"I miss you Zidane"*); `--zone-id <n>`
  reads a specific `<n>.mes` text block; `--out` writes a gitignored JSON view (SE-derived). By default it
  shows only real dialogue — `flags=0` system/notification windows (a field's error guard, "Received item!"
  popups) and repeated call sites are hidden (`--all` shows them), and the kit-only `@x,z` position heuristic
  is dropped on real fields.
- **Re-author a fork (`ff9mapkit import <field> --dialogue`)** appends the real field's NPC lines as
  ready-to-use, commented `[[npc]]` blocks (real model resolved by GEO name, clean editable text, a `pos`
  placeholder) — the "fork a field and rewrite its script" workflow. They parallel the verbatim-carried
  `[[object]]` NPCs; uncomment + reposition + rewrite the ones you want.
- **A dedicated Dialogue editor GUI** (`apps/ff9_dialogue.pyw`): every line of a field in one list, each with
  a **live preview of how it wraps on the FF9 screen** (so simple dialogue stays well-formatted — FF9 never
  auto-wraps), speaker + window-tail edited alongside, and an "Import from game" panel that views stock
  dialogue and can drop lines in as NPC stubs. Edits round-trip the same `field.toml` the Logic Editor uses.
- **Integrated:** a **Dialogue tab** in the Campaign Editor that **shares one `FieldDoc`** with the Logic
  Editor (the words edited in either are the same data, no divergence); the Logic Editor's new **"Dialogue…"**
  button hands the current field off to it; and a launcher entry. View stock dialogue, or word-smith a
  campaign's lines, from the same surface.

### Added — battle-map pillar (custom 3D battle backgrounds)
- `ff9mapkit battle-import <BBG>` forks a REAL FF9 battle background out of your install (geometry +
  per-submesh textures) into an editable `battle.toml` + `<BBG>.fbx`; `ff9mapkit battle-build` compiles
  it into a Memoria mod; `tools/deploy_battle.py` installs it reversibly into the per-worktree mod
  folder. `battle-list` browses the real BBGs available to fork.
- A battle map is a real textured **3D mesh** (child groups Group_0/2/4/8 = additive/ground/minus/sky)
  shipped as a loose ASCII **FBX** that **stock Memoria** loads instead of the bundle — no engine
  rebuild. **In-game verified** (texture reskin, a synthetic quad, and a byte-faithful BBG_B013
  round-trip). The first practical custom-battle-background pipeline for FF9. See `docs/FORMAT.md`
  → "Battle maps". Provenance-clean: geometry/textures are extracted from your own install at runtime,
  never committed.
- **Tier-c MINT — a brand-new battle SCENE (in-game proven).** `battle-import --fork-scene <DONOR>`
  also forks a real battle's gameplay/sequence/camera/text (raw16 + raw17 + per-lang `.eb` + `.mes`) into
  the project; `battle-build` emits a net-new `BattleScene <id> <NAME> <BBG>` registration plus those
  assets, and `--ship-as BBG_B<N>` ships the geometry under a **brand-new bbg number** (a wholly original
  map — the kit authors a static `.inb` for it). `deploy_battle.py --trigger-field N` repoints a field's
  encounter at the minted scene so you can fight it. No camera authoring needed (the donor's raw17 carries
  a working camera; a static `.inb` dodges the per-id anim tables). **In-game proven**: a net-new
  `BBG_B200` + scene on stock Memoria, fully fightable. The kit's emitted raw16/raw17/eb/mes are
  byte-identical to the hand-built probe verified in real gameplay. Provenance-clean: forked scene assets
  are SE-derived, written to a gitignored project dir, never committed.
- **Tune the fight (`[scene]`).** A minted battle's forked gameplay is now AUTHORABLE, not just a clone:
  a `[scene]` section in battle.toml overrides enemy **positions** (`pos`/`y`/`rot`), **stats**
  (`hp`/`mp`/`gil`/`exp`/`level`/`speed`/`strength`/`magic`/`spirit`), **rewards** (`drop`/`steal`, items
  by name), and the **camera** pose. The kit surgically patches the forked `raw16` (only edited bytes
  change) and keeps enemy TYPES intact so the forked attack sequences stay valid; items resolve by name
  (`"Hi-Potion"`); shared-type edits warn. Validated against the real Evil Forest scene (Goblin HP 33 →
  1500, etc.).
- **Spawn composition (`[scene]`) — recompose AND grow the encounter.** `monster_count` sets how many
  slots spawn (1–4, the engine cap) and a per-slot `type` chooses which enemy fills it (the scene's
  EXISTING types, so the forked raw17 sequences + GEO cover them; made targetable + auto-grounded). It
  writes the composition to EVERY pattern (a deterministic fight) and **re-authors the battle eb's
  `Main_Init` to bind one enemy-AI object per spawned slot** (`InitObject(1+type, 0x80+slot)`, reusing the
  donor's per-type AI entries). That removes the earlier donor-count cap entirely: a mint can now spawn
  MORE enemies than its donor natively did (e.g. a 1-enemy Evil Forest → four Goblins) with no player-model
  twitch — every slot has a real AI object, so no death misroutes into the player
  (`EventEngine.RequestAction`). In-game proven. Errors only if a needed per-type AI entry is absent
  (a non-standard donor eb). raw16 + Main_Init only; raw17 untouched.
- **Opening-camera tweaks (`[scene]`).** `camera_yaw` / `camera_pitch` / `camera_zoom` rotate / tilt / zoom
  a minted battle's opening camera by offsetting the donor's `SFXDataCamera` keyframes in raw17 IN PLACE
  (no offset-table repack). Cracked the "closed DLL camera" frontier: the native FF9SpecialEffectPlugin.dll
  reads the raw17 camera bytes directly (`SFX_StartPlungeCamera` gets the pinned raw17 + camOffset), so this
  renders with NO engine rebuild — in-game proven. Targets `cameraList[CameraNo]` = the raw16 `camera`
  selector. yaw + zoom are predictable; **pitch is an offset onto the donor's base angle (large values can
  dip the camera below the floor — use small steps).** Full from-scratch keyframe authoring (length-changing)
  is a future tier needing the offset repack.

### Added — `give_item` by name; gil can subtract
- `give_item = ["Potion", 1]` — items resolve by name (case/space/hyphen-insensitive) or numeric id,
  baked from Memoria's `RegularItem` enum (`ff9mapkit items` lists them). No more memorizing ids
  (236 = Potion; 232 was Sapphire). Negative `gil` now correctly **subtracts** (`RemoveGil`).

### Added — dialogue choices (`[[choice]]`)
- Talk to an NPC, pick from a menu, and **branch** on the answer — the interaction / puzzle primitive
  (merchant, Yes/No lever, quest-giver). Each option can show a reply, give an item / gil, and set a
  story flag (feeding the same `requires_flag` system). Grounded byte-for-byte in a real FF9 shop
  choice: a synchronous `WindowSync` prompt (rows after `[CHOO]`) + a `GetChoose()` branch. See
  `docs/FORMAT.md` → `[[choice]]`. **In-game verified.**
- The form editor (`ff9mapkit edit`) has a **Choices** section: edit the prompt/NPC and a list of
  options (text / reply / give item / gil / set flag), reorderable, with `give_item` by name.
- A choice can be **zone-triggered** (a lever / sign): `[[choice]] zone = [...]` instead of `npc`.
  Default `trigger = "action"` (stand on the zone and press) — re-usable, "decline" is non-destructive,
  and it can't loop (edge-triggered by the button), like a real FF9 lever. `trigger = "walk"` auto-pops
  on tread (flag-gated for loop-safety; `once` true/false). Movement locks while the menu is open.

### Added — modern Field Editor look
- The form-based editor (`ff9mapkit edit`) now ships a cohesive theme: a flat `clam`-based palette
  that **matches your Windows light/dark setting** (with a safe light fallback), Segoe UI typography,
  an accent on the primary actions (Save / Build & Test), roomier tree rows, and a colour-tagged
  console log. No new dependency — the palettes + OS probe are pure-stdlib (`editor/theme.py`).

### Changed — provenance: the repo ships no Square Enix game data
- The blank field, exit-region template, and binary test fixtures are no longer committed. They are
  regenerated from the user's **own** FF9 install by the new **`ff9mapkit extract-templates`**
  command, into a local (gitignored) cache. The repo/wheel ship only our copy/insert **patches**
  (our edits + copy offsets) and a SHA-256 manifest — never game bytes. Verified airtight: no patch
  insert run ever duplicates a run in the source field; a built wheel contains zero game bytes.
- `doctor` now reports whether templates are extracted; the byte-level test suite skips cleanly (with
  a pointer to `extract-templates`) when they aren't, so a fresh clone still runs the pure-logic
  tests offline. See [`docs/PROVENANCE.md`](docs/PROVENANCE.md).

Toward the first public **1.0**, remaining:
- Gallery screenshots (`docs/gallery/`).

## [0.9.3] — feature-complete, in-game-verified

The full custom-field pipeline, proven end to end in real gameplay. See
[`docs/FEATURES.md`](docs/FEATURES.md) for the complete capability list and
[`docs/TECHNICAL.md`](docs/TECHNICAL.md) for how the hard parts work. Highlights:

### Fields & camera
- Mint brand-new fields on a **stock Memoria** install (no engine fork).
- BG-borrow and fully-editable custom scenes.
- **Import / fork any of ~670 real fields** — camera, walkmesh, art, and (extracted from the script)
  exits, encounters, field BGM, and movement tuning.
- Author **any camera angle** from scratch; scrolling fields; multi-camera switch zones.

### Walkmesh & art
- Hand-model in Blender or import a real walkmesh; reshape multi-floor forks (seam-preserving).
- Pixel-accurate paint guide; depth layers; foreground occlusion; light/shadow blend layers.
- Build-time validation: reachability, content-on-mesh, near-edge, zero-area tris, seams, layer aspect.

### Content & scripting
- NPCs, custom dialogue, gateways, encounters (+ battle music), events (chests/gil/flags),
  story branching, and cutscenes (narration + actor walk/turn/emote/teleport). Save-persistent flags.

### Front-ends & engineering
- CLI, Blender add-on, form-based logic editor, build GUI; two-file (scene/logic) authoring.
- Byte-exact codecs (`.eb` / `.bgi` / `.bgx` / `.mes`); 254 kit + 47 Blender offline tests;
  opcode + projection math baked from Memoria source.

### Notes
- `0.9.x` unified the CLI and Blender add-on versions; the CLI was previously `0.1.0`.

[1.0.0b17]: https://github.com/GameJawnsInc/Dream-World-IX/compare/v1.0.0b15...v1.0.0b17
[1.0.0b2]: https://github.com/GameJawnsInc/Dream-World-IX/compare/v1.0.0b1...v1.0.0b2
[1.0.0b1]: https://github.com/GameJawnsInc/Dream-World-IX/releases/tag/v1.0.0b1
