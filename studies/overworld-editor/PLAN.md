# Overworld visual editor: feasibility and plan

**Status:** UNPARKED 2026-10-23 (owner: "let's start planning towards the GUI terrain editor"); A0, A1, the stack, C1,
C2, C3 and C4 built, see Progress.
The replan below supersedes the rung order further down; the recon sections stay as the evidence. Original status
(2026-10-13): recon only. The owner asked whether the kit is on a path to a visual editor that adjusts the overworld
in real time under the laws the terrain studies have proven. The answer is yes, with one design call. The owner
parked it then: more shaping work came first.

## Replan (2026-10-23)

### What ten days of shaping changed

| Then (10-13) | Now | Effect on the editor |
|---|---|---|
| `render.py` read only deployed overrides; stock land drew as sky | `world-render --stock` draws stock under the overrides plus the donor's free-riding parts (`render.load_batches(stock=True)`), `--mod-root` reads a scratch build | Rung 0's data path and its pixel oracle both exist; the GPU view loads the same batches |
| `[[forest]]`/`[[mountain]]` rows lacked handles | both carry every handle (centre, `rot`, `spread`, `rock_height`, `donor`); the alcove comes from the catalogue; `[[river]]` is a row and `river.deploy` is the one pipeline (recipe == CLI on 264/264 files) | the recipe is the document for island, river, mountain, forest and hill; only `[[sink]]` is missing |
| one canopy, two massifs | `donors.toml`: 7 qualified massifs (incl. snow-ridge, desert-scrub), 5 canopies, 3 coast, the river, the sea plane; `home_ground` per row | the donor picker has real choices, and the home-ground warning is a chip, not a log line |
| refusals were strings | `river.RiverRefused(gate, msg, where)` carries the failing plan points | the shape habit 2 asked for exists once; interior's gates still raise strings |
| reload needed a DLL rung | every lab round since 16 reached a freshly deployed world through bench field 6603 with no DLL | "the game follows" gets a no-DLL rung first; the DLL rung becomes a speed upgrade, only if measured too slow |
| `MTN_*` ceilings partly named | `FOREST_SPREAD_MAX`, `MTN_SPREAD_MAX`, `MTN_ROCK_HEIGHT_MAX` all named in `interior.py` | handles can read their ceilings, but the CLI, the fuse row and a GUI would each read them separately (habit 4 half done) |

Unchanged: no 3D view in the Workspace (the World tab is still the 2D override chart, `workspace/worlddoc.py:439`);
`QtOpenGL`/`QtOpenGLWidgets` ship in the installed PySide6 6.11.1 Essentials; relief verbs are not seam-aware (a
placement straddling x = 0 does not seat, river rung 5b -- STALE: the verbs were seam-aware from 2026-10-20, the editor
from C10); the design call (arrange carried shapes, never sculpt).

### The order now

Two tracks that touch disjoint files, so they can run side by side. Each step has its own acceptance and is useful
alone.

**Track A: the view (Workspace files only)**
- **A0, the read-only 3D view.** `QOpenGLWidget` in the World tab, fed by `render.load_batches(stock=True)`: one
  atlas texture, nearest sampling, unlit, sea at frame 0, the same cull. Orbit, pan, zoom.
  - Accept: at three committed bench cameras the GPU frame matches `world-render`'s still within a small tolerance;
    the whole map orbits smoothly; the owner says it reads as the overworld.
  - Measure first: whole-map load time through `load_batches` (480 blocks, unmeasured), and whether GL exists in
    the offscreen smoke run. The fallback for headless runs is render.py's still, with a test that fails if the GL
    path is silently skipped on a machine that has GL.
- **A1, picking.** A click returns the coordinate triple (world / block / cell), the ground hit via `placement.place`
  with its index, the cell's topograph and area, and which mod folder owns the block (the ledger). "Teleport the game
  here" through the harness.
  - Accept: click a landmark; the harness reads back the same x,z.

**Track B: the backend contract (kit files only, no GUI)**
- **B1, located refusals.** Interior's gates (walk-in, rigid, down, placement census, atlas) raise one refusal type
  shaped like `RiverRefused`: gate name, message, failing points. The CLI text stays byte-identical.
  - Accept: every gate's refusal test also asserts a point inside the plan; a mutation that drops the points goes red.
- **B2, one handle table.** Each carry verb declares its handles once (name, type, range, ceiling constant, catalogue
  source); argparse, the fuse row's `_strict_keys` and the GUI all read it. A law in a docstring is a wish; this puts
  the ceilings at every call site from one place.
  - Accept: the existing CLI-vs-row parity tests pass unchanged; a test fails if a handle exists in one surface only.
- **B3, the warm worker and its timings.** A worker process with UnityPy and the block envs resident (the
  `warm_run.py` precedent), request/reply over stdin/stdout, so the UI thread never imports the heavy kit.
  - Measure: `carve_forest` at a fixed centre (about 5s after habit 5, to re-measure) and `carve_mountain` at a fixed
    centre (never measured). These two numbers decide whether "judge on release" feels live or needs a progress bar.

**Then, joined (needs A1 and B1-B3)**
- **C1, the forest end to end.** Ghost canopy from `_forest_plan`; centre, angle, spread handles; donor picker from
  the 5 canopies; cheap laws live (spread ceiling, footprint inside land, donor qualified); on release the worker runs
  `carve_forest` + `census_gate` and draws refusals where they happen; Accept deploys to a scratch folder first.
  - Accept: an editor-placed forest writes the same bytes as `world-forest` with the same arguments; owner playtest.
- **C2, the mountain.** Same pattern with 7 massifs, `rot`/`spread`/`rock_height`, the catalogued alcove, and the
  home-ground chip.
- **C3, the recipe is the document.** Open and save a `world-fuse` TOML; undo walks the recipe; Accept re-composes.
  Add `[[sink]]` here (it needs the disc-4 replay hook).
- **C4, the game follows (no DLL).** Accept → deploy → world round trip through a bench field → teleport to the
  editor's view, measured by the harness. The DLL `ArmWorldReload` rung only if C4 is measured too slow.
- **C5, the other verbs.** River placement (already editor-shaped), sink as clickable islands (`sink_candidates`),
  coast morphs as clickable lawful windows (`world-morphs`), island and transplant after their compute/deploy split.

### Owner decisions (taken 2026-10-23: "Go with the recommended answers")

1. It lives in the World tab, beside the existing chart.
2. The forest goes end to end first.
3. Accept deploys to a scratch lab folder only, until C4 is proven.

### Progress

- **A0 BUILT + OWNER-PASSED (2026-10-23: "i looked, looks good", after C7's handedness fix)** -> [`A0.md`](A0.md). The GPU view matches `world-render` at the six
  committed bench cameras and a disc-1 coast with blob 0 and coverage <= 2; three break-it mutations are caught.
  Whole-map load 5.4 s (worker thread). Not in A0: the x-torus wrap, picking (A1).
- **A1 BUILT + IN-GAME PROVEN (2026-10-23)** -> [`A1.md`](A1.md). A click picks the surface (front faces, 27-79 ms on
  the whole map) and the strip shows the triple, the engine's ground, the stacked-sheet rule, who the game takes the
  files from, the ledger and the landmark; "Teleport game here" (dev checkout) moved the party to three landmark
  picks within 0.004u, standing within 0.003u of the predicted height. Found on the way: the view draws one folder
  over stock, not the whole FolderNames stack -- the facts flag it per point; drawing the stack is worth doing before C1.
- **THE STACK DRAWN + IN-GAME PROVEN (2026-10-23)** -> [`STACK.md`](STACK.md). The 3D view and the pick resolve every
  file the engine's way (FolderNames first holder per file; Terrain-exists from any folder, Donor.txt from the first;
  a refused file means stock, not the next folder's). Two labs first in FolderNames: 4/4 heights within 0.002u, each
  case 1.5u from the wrong rule; Memoria.log confirmed the loads and the refusal. "Only this folder" previews a
  scratch folder for C1.
- **C1 BUILT + IN-GAME PROVEN + OWNER-PASSED (2026-10-23: "forest is there and walkable")** -> [`C1.md`](C1.md). Add forest in the 3D view:
  click to place, drag the ghost, turn and spread it within the law's ceilings, a donor from the qualified canopies;
  the footprint law previews live (vectorised, 120/120 agreeing with the carve's loop, 3.8 ms); on release the tool
  runs `world-forest --dry-run` and draws its verdict where the gates refuse (B1 for the forest's gates: located
  refusals, `--report-json`); Accept runs the same command into a draft outside the install. The acceptance holds:
  the editor's draft and the hand-typed command's are byte-identical (hermetic, and 1,531 files on the real island).
  In game, the draft first in FolderNames: 4/4 heights within 0.003u, the canopy 1.36-1.72u from the no-lab height.
  Measured: an exact-centre carve takes 7 s cold, so judging on release needs no warm worker (B3 deferred).
- **C4 BUILT + IN-GAME PROVEN (2026-10-23)** -> [`C4.md`](C4.md). Promote writes a draft's edits into the live folder
  (`world-promote`: refuses over another deploy's bytes, backs up and ledgers every write, mirrors disc 4, snapshots the
  edited blocks so `--revert` is byte-exact); Show in game (`tools/world_reload.py`) makes the running game re-read the
  world through bench 6603 and lands the party on the edit. In game: before 3.000 (grass), promoted without a reload
  3.000 (the game keeps its world), reloaded 4.719 (canopy, predicted 4.720), reverted 3.000; the live folder ended
  byte-identical. Promote to visible: about 13 s with NO DLL, so the DLL rung is not needed.
- **C2 BUILT + IN-GAME PROVEN + OWNER-PASSED (2026-10-23: "walked it without issue")** -> [`C2.md`](C2.md). Add mountain beside Add forest:
  the seven qualified massifs, angle, spread and rock height within the law's ceilings (height held at x1 for the
  horseshoe), a home-ground chip that warns off the donor's home ground, the island's own `--ground`. The placement
  laws preview live (60/60 against the carve on the real island, 4 ms); B1 for every mountain gate; `world-mountain
  --report-json`. The forest's card is now `CarryTool`, shared. I1: the editor's draft and the hand-typed command's
  are byte-identical (hermetic, and 1,719 files on the real island). In game, promoted and reloaded: the summit
  15.523 (predicted 15.521, grass 3.000 before), beside it 2.867 (2.868).
- **C3 BUILT (2026-10-23), the acceptance holds on the real island** -> [`C3.md`](C3.md). The Recipe bar: every Accept is
  a `[[forest]]`/`[[mountain]]` row built from the command it ran; Undo/Redo restore each step's snapshots byte for
  byte (0.2 s, fenced above a promote); Save recipe writes TOML for `world-fuse` with `step = N` (THE ORDER LAW:
  `fuse.ordered_rows` keeps the order shapes were placed in); Open recipe composes one `world-fuse` job per row.
  `[[sink]]` is a compose row with world-sink's disc-4 replay. On FF9CustomMap-world: the saved recipe composed by
  the CLI is byte-identical to the editor's draft over 1,531 files, Open recipe the same, two undos back to the
  folder. Found: the preview's anchor law (open sea inside a deployed block).
- **C5, first verb: SINK BUILT + IN GAME (2026-10-23)** -> [`C5.md`](C5.md). "Sink an island": the cached island list
  (sink_candidates + outlines, 3 min once per install), a click picks the island, its outline is the ghost, its
  precomputed verdict previews; Accept is world-sink on disc 1 then disc 4 (THE DRAFT'S DISC-4 HALF: a draft cannot
  mirror, so it makes the replay's own call). I1 identical over 1,541 files. In game: the island's land 4.691 before,
  gone after the promote and reload (the party in open water there; the control unchanged). Found: promote failed
  onto cells the live folder had nothing at (fixed, recovered); a party stands 0.586 under a Sea3 surface.
- **C5, second verb: COAST MORPHS BUILT + IN GAME (2026-10-23)** -> [`C5.md`](C5.md). "Shape a coast": a click picks
  the lawful window (world-morphs' catalog, cached per block), only its lawful verbs, the depth stops at its ceiling;
  world-transplant --in-place judges it; Accept on disc 1 then disc 4; a `[[morph]]` world-fuse table. I1 identical
  over 1,545 files, and on real bytes card == hand == recipe. In game: the cliff face at 1.543 became land at 4.219
  (predicted 4.219). River placement deferred: all 56 open-ocean shifts that fit it are FF9CustomMap-world's already.
- **C5, third verb: A NEW ISLAND BUILT + IN GAME (2026-10-23)** -> [`C5.md`](C5.md). "Add an island": the ghost is the
  mint's own coast (its outline call, exact for the seed), the handles are the mint's (radius, lobes, height, ground,
  seed), the preview its open-ocean and free-block laws; `world-island --report-json`; an `[[island]]` recipe row.
  I1 identical over 1,553 files, and on real bytes card == hand == recipe. In game: open sea (-1.367) at the centre
  before, the new island's grass at 3.199 after (predicted 3.200). The five tools now sit in one "Edit the map" menu
  (five buttons raised the window floor).
- **C5, fourth verb: THE TRANSPLANT BUILT + IN GAME (2026-10-23); C5 DONE but the river** -> [`C5.md`](C5.md).
  "Carry a coast": a qualified coast donor, a quarter turn, a click on the target cell; the ghost is the donor's own
  land by the carry's own turn map (and the shift once a check reports it). The recipe row is a new `[[transplant]]`
  table that runs the command: `[[placement]]`'s fused path refused (land-fit) a carry the command makes, measured.
  I1 identical over 1,568 files; on real bytes hand == recipe. In game: open sea (-1.367) before, the carried grass at
  3.738 after (predicted 3.738).
- **C19, EDIT A STEP IN THE GAME: BUILT (2026-10-24)** -> [`C19.md`](C19.md). Edit / Delete on a promoted step chain
  revert (newest first) -> C9's edit -> promote again on Accept or Cancel; a later revert refusing promotes straight
  back. Real bytes on the live install: live disc 1 == the edited recipe on the snapshot over 999 files, every one of
  72 files at the changed blocks ledgered true, and a final revert leaves the folder exactly as it was.
- **C18, THE GAME'S FOG: BUILT (2026-10-24)** -> [`C18.md`](C18.md). Measured from C7's nine stills (the shaders are
  compiled): linear in view depth 15 -> 61u, +2.75u per unit of height (the Mist is a ground fog), the weather
  table's daylight fogDW; held-out spot rmse 0.051-0.066 vs 0.71-0.83 unfogged. Mist follows the story (scenario
  5990-11090 has none: the ini's fog). On the view's GPU path the far land's error falls 55-94 -> 6-14.
- **C17, THE MOUNTAIN STOPS OFFERING FAILURES: BUILT (2026-10-24)** -> [`C17.md`](C17.md). Offered spots that pass:
  22 of 150 -> 76 of 150. The apron slope judged the whole span (42 of 42 refusals at steep ground it never lifted);
  it judges the lifted grass. The card reads the carve's hole ring (plan-only): a weld split on it, and a zip edge
  bound, refuse before any check (32 caught, no pass refused). Zip down faces and rise stay with the dry run.
- **C16, REFUSALS THAT SAY WHERE: BUILT (2026-10-24)** -> [`C16.md`](C16.md). Measured through the real cards: of the
  refusals they meet, the mountain left 21 of 28 unmarked; now none. The mountain's exact-weld law checked its whole
  read window (16 refusals at far-off sub-mm splits); it checks the ring. A carry donor that fills its frame is refused
  at once with its edges marked (two listed donors always failed land-fit); a carry's report marks a gate's points.
- **C15, THE NORTH-SOUTH EDGE: ANSWERED (2026-10-24)** -> [`C15.md`](C15.md). The engine wraps rows too (positions
  mod 1280), but no land meets across that edge: 23.6u of water at the narrowest, so nothing placeable straddles it
  and no z seam frame is built. The orphan census's ring now wraps rows as well (a read; edged-z writes stay policy);
  real bytes at (2, 0) and (23, 19) identical over 2,007 files.
- **C14, THE CARRY AT COLUMN 0: ANSWERED + FIXED (2026-10-24)** -> [`C14.md`](C14.md). The carry's bytes never
  read the target's neighbours on either side, so nothing joins wrongly; but its orphan-decal census clipped its ring
  to the grid, blind west of column 0 (and east of 23), and --redress-orphans could rewrite a lawful tile there. The
  ring now wraps. Real bytes at (0, 3): the census now reads (23, 4); written bytes identical over 1,871 files.
- **C13, MORPH AND RIVER REPLAY: BUILT (2026-10-24)** -> [`C13.md`](C13.md). Measured: a coast morph reads only its
  own block (it keeps the block's frame), a river only the blocks it changes; neither read a held neighbour. So both
  replay after an edit; the install-gated fence holds them to it. Real bytes: an edited hill with a morph and a
  river move after it -- 2 replayed, 0 composed, 7.0 s against 48.9 s, == world-fuse over 1,739 files.
- **C12, EVERY STEP EDITABLE: BUILT (2026-10-24)** -> [`C12.md`](C12.md). The sink, coast and river cards open on a
  placed step's row, as C9's do: each holds the row until its read is in (island list, block windows, river shape),
  and every card must say the row back key for key or the edit refuses. Real bytes: a sink moved to another
  island, a cliff bump 2 -> 1.5, the river move reopened, each I1 == world-fuse over 1,751 files. Found: an
  open-sea click recursed in the sink card, the coast card's stale "already edited", a river step's pin and pick.
- **C11, FASTER RE-RUNS: BUILT (2026-10-24)** -> [`C11.md`](C11.md). Island, carry and sink steps get a measured
  read window (`recipe.replay_window`: footprint or rect or own cells, plus the ring round them), held to what the
  verbs really read by an install-gated fence; so after an edit they replay instead of running again. Real bytes:
  an edited hill with an island, a carry and a sink after it -- 3 replayed, 0 composed again, 7.7 s against 35.7 s
  to compose the four rows, == world-fuse over 1,900 files. Found: the manifest drift gate refused an opened
  recipe's edit (editor jobs now --allow-overwrite in the draft), and an Edit right after an Accept raced a reader.
- **C10, ACROSS THE SEAM: BUILT + IN GAME (2026-10-24)** -> [`C10.md`](C10.md). The verbs were seam-aware already;
  the editor was not (its soup cut at x = 0, the view drawing column 23 at the far end). Now each card reads the
  island in two frames and judges a centre within 384u of x = 0 in the one read across it, the command naming the
  folded centre; the view draws three columns each side of the seam again across it, the ghost and its marks with
  it. Found: THE ONE SPELLING -- x -2 and x 1534 wrote different bytes (the verbs read round the point as given);
  the verbs and world-fuse now fold first. Real bytes: cards == hand (unfolded) == recipe over 1,863 files; in game
  a hill at x -2 stood 7.238 at its top and 5.266 on both slopes, one in column 23, one in column 0.
- **C9, EDITING A PLACED SHAPE: BUILT + IN GAME (2026-10-24)** -> [`C9.md`](C9.md). A click picks the step placed
  there; Edit opens its own card on its row (the draft undone back to before it, the step and the ones after it
  lifted out), Delete puts nothing in its place; then each later step goes back on top, replayed from its record
  where no block it reads changed (the dirty set), else composed again by `world-fuse`; a refusal leaves the draft
  exactly as it was. On real bytes the edited draft == `world-fuse` of the edited recipe over 1,863 files; in game
  a hill moved and lowered stood at its new place (6.730, predicted 6.733) and its old place was lawn again. Found:
  promote's relabel crashed half way after another draft of the folder promoted and reverted (fixed, fenced).
- **C8, THE GAME CAMERA ON A VEHICLE: BUILT + MEASURED (2026-10-23)** -> [`C8.md`](C8.md). `gamecam` reads each
  mode's type / type_cam from the stack's TransportControls.csv and decodes the flight, boat and forest rules;
  the 3D view's game camera gets a vehicle chooser and a flyer's height. Ten stills on the real vehicles (the
  vehicle study's boarding routes; a fresh boat spawn, the old lane being C5's comma): the boat confirmed (land IoU
  0.90 vs 0.05 for the on-foot camera), the chocobo confirmed (class agreement 0.97-0.98), the airship consistent
  but not tightly pinned (all-land, dusk-tinted frames: three measures, fits inside the on-foot noise).
- **C5 follow-up, MULTI-BLOCK CARRIES: BUILT + IN GAME (2026-10-23)** -> [`C5.md`](C5.md). "Carry a coast" offers the
  coast study's carry units (the comma 2x3, the reef 2x2, the terminus pair 1x2, the chain 4x2) beside the single
  blocks: the ghost by the carry's own region map, the target the turned rect nearest the click, `--size --shift 0,0`,
  a `[[transplant]]` row with `size`. Fixed on the way: the verdict JSON named one block of a unit's rect (Undo would
  have lost the rest). I1/I2 identical over 1,782 files; in game the party stood on the carried comma at 9.551
  (predicted 9.554), where it had been in open sea. The comma is qualified. Then the reef and the terminus pair, walked
  together (`c5v_lab.py`): 9.266 (predicted 9.265, a crystal shard) and 5.039 (predicted 5.044, grass), I1/I2
  identical over 1,830 files; both qualified. The beach chain stays a candidate: no free 4x2 rect here.
- **C7, THE GAME'S OWN CAMERA: ANSWERED + BUILT (2026-10-23)** -> [`C7.md`](C7.md). The chase camera decoded from
  Memoria's source (`world/gamecam.py`: posstats, place, the altitude and tilt blends, the terrain lift, the user's
  Memoria.ini [Worldmap]) and measured against nine in-game stills: exact in plan, within the engine's settle bands in
  height. Found by asking: render.py and the 3D view drew the world as the game's MIRROR image (right-handed); fixed,
  9 of 9 stills now choose the unmirrored frame. "As the game sees it" on the 3D page frames the pick as the game
  would. **A0's owner look is owed again: the view it showed was mirrored.**
- **C6, THE HILL: BUILT + IN GAME (2026-10-23)** -> [`C6.md`](C6.md). "Add a hill": the ghost is the island's own
  triangles lifted by the verb's raised cosine (pinned to `build_hill`'s output), the preview runs its footprint,
  flank and peak laws live (agreeing with the verb gate for gate), and the spins read B2's table. B1 reached the hill:
  its gates raise located refusals. I1/I2 identical over 1,767 files; in game the lawn at 3.199, the hill's top at
  7.320 (predicted 7.322). Every relief verb now has its card.
- **C5, fifth verb: MOVE THE RIVER BUILT + IN GAME (2026-10-23); C5 DONE** -> [`C5.md`](C5.md). Of the river's 28
  placements, all are held in FF9CustomMap-world; with its own files left out, one more is free (one block north). So
  the card is a move: `world-river --at NEW --move-from OLD` judges the new placement with the old river's files free,
  and takes the old one out only once every gate is green. Underneath, drafts now carry deletions, the stack read
  lets a draft stand in for its source, and Promote keeps each file's writer in the ledger (a promoted river was
  foreign to its own verb before). I1/I2 identical over 1,635 files. In game: the new ground went from sea (-1.367)
  to land (3.211, predicted 3.215), and the old from land (3.430) to sea (-1.367).
- **B2, ONE HANDLE TABLE: DONE (2026-10-23).** `world/handles.py` declares each relief verb's handles once (forest,
  mountain, hill): flag, type, default, help, range, the interior constant that is its ceiling, the catalogue its picker
  lists, and its surfaces (cli / row / gui). argparse is built from it (the three parsers' dumps and `--help` are
  byte-identical to the hand-written ones), the fuse runner's key check and defaults read it, and the forest and
  mountain cards take their spin stops and donor catalogues from it and map every gui handle to its widget or rule.
  The fence (`tests/test_world_handles.py`, 18 tests) fails on a flag added by hand, a row key the runner ignores, a
  gui handle no card maps, and a spin hard-coded past the table (each break measured red). The compose parity tests
  pass unchanged. Not in the table: the C5 verbs (sink, morph, island, transplant), whose rows carry a few of many
  CLI flags and have no ceilings; they can join when one grows a handle.

**Rating:**
- **7/10 for an ARRANGEMENT editor.** You place, drag, turn and scale the shapes the kit already carries (forests,
  mountains, hills, islands), and the laws act as the handles' limits and the refusals.
- **3/10 for a freeform SCULPTING editor, and not recommended.** The limit is the project's own record, not the
  engineering (see "The design call").

## What the recon found

Three readers covered the Workspace GUI, the world kit as an editor backend, and the live-game loop. The claims
below were checked against the code. Anything not measured is labelled so.

### The game shows an edit in about a second, with no relaunch

- `WorldMeshOverride.TryLoad` keeps no cache. Every call checks the file and reads it fresh
  (`Memoria/World/WorldMeshOverride.cs:31-57`). Textures are read fresh too (`:141-157`).
- Blocks never stream out (`WorldState.cs:25` sets `DiscardBlockWhenStreaming = false`), so walking away and back
  reloads nothing. A world-scene rebuild reloads every block.
- The ~ menu's "Reload overworld on a state" does exactly that (`Ff9mkDebugMenu.cs:1589-1643`:
  `ForceWorldState` + `ArmWorldReload` → `SceneDirector.Replace("WorldMap")`).
- **Owner-playtest proven** (commit `dcec389e`, "THE RELAUNCH TAX WAS SELF-IMPOSED"): a test hill appeared and
  vanished across reloads, with a fresh `[WorldMeshOverride] loaded` line each time.
- **Two gaps:**
  - The reload lands at the state's spawn, not where the player stood.
  - The test harness cannot trigger it. Its debug-menu adapters are warp, world warp, world teleport and battle
    only (`Ff9mkDebugMenu.cs:469-507`).

### The kit can already draw its world, faithfully, but not interactively

- `world/render.py` (626 LOC; `world-render --around WX,WZ`) is a textured software rasterizer (numpy + PIL). It
  makes the engine's choices:
  - unlit: WorldMap/Terrain binds no normal;
  - one 1024² terrain atlas;
  - nearest sampling;
  - opaque sea at frame 0;
  - the game-eye cull.
- It renders the committed bench cameras pixel-identical to the study it was promoted from.
- Its inner loop runs once per triangle in Python, so it produces stills, not frames.
- **It reads only a mod folder's deployed overrides** (`render.load_batches`): stock land renders as sky. The
  terrain study's `mountaindonors/home_render.py` feeds it stock parts through `part_src`, and the editor's view
  needs the same fallback (stock under the overrides).
- `atlas.load_atlas` (`atlas.py:187`) extracts the atlases and resolves the engine-true HD override across the mod
  stack (`resolve_atlas_source`, `:110`).
- **The look is cheap for a GPU.** It is unlit, uses one texture sheet, and needs one trivial shader. A block is a
  few thousand triangles, and the whole map fits on a GPU many times over.
- The renderer's own BLIND-SPOT LEDGER (`render.py` docstring) is what a GPU port would also lack: sea animation,
  fog, sky and the real camera path.

### The Workspace can host a 3D view, but has none today

- All six canvases are 2D QGraphicsViews: CampaignMap, ConceptMapView, AtlasCanvas, BackdropCanvas, StageCanvas and
  PlanCanvas.
- The World tab (`workspace/worlddoc.py:439`) is a read-only chart of which 24×20 blocks are overridden. It shows no
  geometry, edits nothing and runs no `world-*` verb.
- **`QOpenGLWidget` ships in `PySide6_Essentials`** (`QtOpenGL.pyd` + `QtOpenGLWidgets.pyd`; checked against the
  installed wheel's RECORD). It needs no new dependency and keeps the LGPL Essentials-only pin
  (`ff9mapkit/pyproject.toml:60-65`).
  - Qt3D, QtQuick3D and QtWebEngine are all in Addons, which the pin excludes on purpose. So the viewport is a
    QOpenGLWidget with our own shader, not a scene-graph framework or a web view.
- **How the Workspace calls the kit:**
  - long jobs run as a subprocess through `run_job` (`shell.py:9279-9320`), one QProcess at a time;
  - background work runs on daemon threads that signal back;
  - there is no QThread.
- **Precedent for "rules react as you drag":**
  - The Floorplan tab re-composes the whole plan 140ms after each gesture. Its live-gate memo laws are in the GUI
    memory (CACHE THE ANSWER, NOT THE GEOMETRY).
  - The Trace tab has drag handles with a live outset preview.
  - Every canvas commits ONE callback on release, and the host owns the write and the undo.

### The world kit is half-ready as a backend

- **Size:** `world/` is about 35k LOC in 36 modules; `cli.py` defines 39 `world-*` verbs.
- **The interior verbs are the clean half.** `carve_forest` / `build_hill` / `carve_mountain` take an in-memory
  soup and return `{"changed": {blk: BlockMesh}, "center", "report"}`. Deploying is a separate step
  (`deploy_changed`, `interior.py:3733`) through the one write seam (`mesh.deploy_override`, `mesh.py:628`).
  - They still read stock donor blocks from the install, through an LRU memo.
- **`transplant()`, `terrain.reshape()` and `island.landmass()` read and deploy inside the verb**, behind a
  `dry_run=` flag. Those three and `coastmorph` hold about 15.7k LOC. `carve_mountain` alone is one function of
  about 1,690 lines (`interior.py:1721` to about `:3410`).
- **Every gate is pure Python, with no native acceleration.**
  - The staged plan in the perf memory (`project-ff9-overworld-perf-assessment`) still stands: the cache and the
    warm process shipped; PyO3 kernels only if needed.
  - `placement.place` has an optional grid index measured at 34× (`placement.py:138`).
  - **The forest walk-in gate does not use it** (`interior.py:1175`, verified): every 0.5u rim station places 49
    samples by linear scan.
- **There is no edit history or undo stack.** Each verb writes over deployed files, and `terrain.reshape` compounds
  on a re-run. Recovery is backups (`mesh.park_backup`) plus the append-only `.ff9world.jsonl` ledger. There is no
  `world-revert`.
- **The `world-fuse` layout TOML is already a document.**
  - It holds `[[island]]` / `[[mountain]]` / `[[forest]]` / `[[hill]]` / `[[coastnav]]` / `[[rim_retile]]` tables,
    run in fixed tiers (`fuse.py:293`).
  - It writes a `world_manifest.json`, and a re-compose of the same TOML was proven to produce ZERO diffs.
  - That recipe is the editor's natural save format, and undo is the recipe's history.

### The live link

- **Transport:** the harness talks through files (`<game>/x64/ff9harness/`: `req.txt`, `state.json`, `events.jsonl`,
  `shots/`).
- **What it already has:**
  - overworld `teleport x,z`;
  - `worldwarp`;
  - in-engine screenshots;
  - `noencounter`;
  - published `world.{id, x, z, vehicle}`, with no y.
- **What it lacks:** a camera verb (`Session.world_face` turns the camera with the bumpers) and a world-reload verb.
- **Round trip:** about 4-6 frames for a simple command, **estimated from the code's poll intervals, not
  measured**. That is about 70-200 ms at 31 fps, and half that at 60.
- `tools/warm_run.py --watch` re-runs kit verbs in one warm process. It never touches the game. Nothing deploys on
  save anywhere.

## Rating by layer

| Layer | Feasibility | Size | What it needs |
|---|---|---|---|
| Read-only 3D view of the deployed world; click → coordinate triple | high | small-medium | `read_block_stacked` → GPU buffers; atlas → one texture; render.py's rules as a shader |
| Ghost forest/mountain with centre, angle and scale handles | high | medium | `_forest_plan` is plain maths; handles clamp to the proven constants (`FOREST_SPREAD_MAX`, the qualified donors in `donors.toml`) |
| The laws reacting **while** you drag | medium | medium | only the cheap laws run per frame. The gates run on release: the forest walk-in gate is seconds to minutes. Ghost → judge on release → deploy on Accept |
| Show the change in game after Accept | medium | small, but a DLL patch | expose the world reload to the harness, then teleport back to the editor's view. About 2-3s Accept-to-game; never per frame |
| Coast verbs and transplants behind handles | low-medium | large | the compute/deploy split in transplant/terrain/island/coastmorph. `world-morphs` already enumerates lawful windows with ceilings, so those become clickable spots |
| Freeform terrain brush | not recommended | — | see below |

## The design call: arrange carried shapes, never sculpt

The terrain arcs settled this before any editor existed:
- **THE FORM LESSON:** from-scratch massif synthesis was falsified over 8 rounds.
- **THE DEFECT FOLLOWS THE AUTHORSHIP:** 12 of 13 verdicts landed on what the round had most recently authored.
- **A GREEN GATE SUITE IS A REGRESSION HARNESS, NOT AN ORACLE:** 0 of 13 playtest verdicts were predicted by a gate.

A brush that lets anyone mint surface at will rebuilds the defect factory with a nicer interface.

The editor's job is the opposite. It is a faster, visible way to drive the verbs that carry real stock shapes:
- **The handles are the verbs' parameters:** centre, angle, scale, donor and rock height.
- **The handles' limits are the laws:** the spread slider stops at ×1.5; the donor picker lists only qualified rows.
- **A refusal is drawn where it happens**, with its reason.
- **The CLI stays the oracle:** the same parameters through the editor and through the CLI must write the same
  bytes.

## Rungs

Each rung is useful on its own. One change per in-game test, as everywhere else.

- **Rung 0: the 3D view, read-only.**
  - **What:** a QOpenGLWidget in the World tab. It shows stock blocks plus the deployed overrides
    (`read_block_stacked`), textured with render.py's rules: unlit, nearest sampling, sea at frame 0, the same cull.
    The camera can orbit, pan and zoom.
  - **Accept:**
    - at a bench camera, the GPU frame matches `world-render`'s still to a small pixel tolerance (render.py is the
      oracle, and its bench cameras are committed);
    - the whole map orbits smoothly;
    - the owner says it reads as the overworld.
  - **Risk:** the Workspace's headless smoke and snap tests run offscreen, where GL may not exist. They need a
    software fallback (render.py itself) or a skip that cannot hide a real failure (`feedback-a-check-that-cannot-fail`).
- **Rung 1: picking.**
  - **What:** a click returns the canonical coordinate triple (world / block / cell) and the ground hit through
    `placement.place` with its index, plus "teleport the game here" through the harness `teleport` verb.
  - **Accept:** a click on a landmark, and the harness reads back the same x,z.
- **Rung 2: the warm worker.**
  - **What:** a kit worker process that keeps UnityPy and the loaded block envs resident (the `warm_run.py`
    precedent) and speaks a small request/reply protocol. The UI thread never imports the heavy kit.
  - **Speed work happens here, measured first:**
    - the walk-in gate's missing index (`interior.py:1175`);
    - then PyO3 kernels for `pip` / `near_poly` / `place` only if still needed.
  - **Accept:** `carve_forest` at a fixed centre returns in a measured time recorded here. That time is **not yet
    measured**; the July 16s figure was `--near`, which searches for a centre.
- **Rung 3: the forest, end to end.**
  - **What:**
    - a ghost canopy from `_forest_plan` with centre, angle and spread handles;
    - a donor picker from `donors.toml`'s qualified canopy rows;
    - cheap laws live during the drag: spread clamp, footprint inside the island, donor qualified;
    - on release, the worker runs `carve_forest` + `census_gate`, and its refusals are drawn at their location;
    - Accept calls `deploy_changed`.
  - **Accept:**
    - **identity:** an editor-placed forest writes the same bytes as `world-forest` with the same arguments;
    - the owner's playtest.
- **Rung 4: the recipe is the document.**
  - **What:** the editor opens and saves a `world-fuse` layout TOML. Undo and redo walk the recipe's history, and
    Accept re-composes.
  - **Accept:** a recipe saved by the editor re-composes through the CLI with zero diffs against what the editor
    deployed.
- **Rung 5: the game follows.**
  - **What:** an engine patch (next free s-number, `memoria-patches/`) exposes `ArmWorldReload` to the harness and
    re-teleports to a given x,z after the rebuild. The editor then calls deploy → reload → teleport.
  - **Accept:**
    - a harness-measured Accept-to-visible time;
    - `[WorldMeshOverride] loaded` lines in Memoria.log for exactly the written blocks.
  - **This is the one DLL rung.** The DLL auto-deploys over the live install with no backup, so back up first.
- **Rung 6: the other verbs.**
  - **What:**
    - mountain (angle and rock height), hill and sink as the next handles;
    - then island and transplant, after the compute/deploy split;
    - then coast morphs as clickable lawful windows from `world-morphs`.

## What the shaping work can do now (cheap, and it keeps the path open)

1. **Split compute from deploy in every new or touched verb**, the way the interior verbs are split: return
   `{changed, report}` and deploy separately.
2. **Make refusals say where.** (C16: done for every refusal the cards were measured to meet.) An exception that carries the failing point or edge as well as the text
   ("cannot be carried alone" at x,z) can be drawn. Today's refusals are strings.
3. **Give every verb a `world-fuse` compose table**, because the recipe is the editor's file format.
4. **Express a verb's freedom as handle-shaped parameters** (centre, angle, scale, donor), with the proven ceilings
   as named constants the handles can read (`FOREST_SPREAD_MAX`, `MTN_ROCK_HEIGHT_MAX`).
5. **Pass the grid index into the walk-in gate** (`interior.py:1175`). It is a small, measurable speed-up.

**Progress (2026-10-19):**
- Habit 3, relief half: a `[[forest]]` row takes `spread`/`rot`, a `[[mountain]]` row `rot`/`rock_height`,
  and `donor` is optional on both. `tests/test_world_compose.py` runs a row and the CLI down to the carve and
  compares the bound arguments, one case per relief table. Each of three mutations that drop a handle turns it
  red. Still missing: `[[sink]]`, which needs the disc-4 replay hook the CLI builds.
- Habit 5: the walk-in gate builds the grid index once per gate. The A/B (same verdict, same bytes, time) is in
  the commit that made the change.
- Habits 1, 2 and 4: unchanged, except that the mountain gained the size handle the forest already had:
  `world-mountain --spread` (ceiling `MTN_SPREAD_MAX` 1.5, owner-passed in game, round 20), in the
  `[[mountain]]` row too. Centre, angle, width, height and donor are now handles on both carried shapes.

## Not recommended (and why)

- **A freeform terrain brush:** see "The design call".
- **Qt3D, QtQuick3D or a three.js view in QtWebEngine:** all are in PySide6_Addons, which the LGPL pin excludes.
- **A live game update per drag:** a world reload is a full scene rebuild (about 1s, with a fade). It belongs on
  Accept, not on drag.
- **Default-on renders or golden-image gates per deploy:** already refused by the 3D-interface review ("Refused by
  verification", `../overworld-3d-interface-review/REPORT.md`). Every world edit changes pixels, so warn and keep
  `--enforce` opt-in.

## Open questions (unmeasured)

- ~~`carve_forest` time at a fixed centre~~: 7 s cold through the CLI, every gate included (C1.md).
- The harness round trip on the overworld, measured rather than estimated.
- Whether GL works in the Workspace's offscreen smoke run, or what the fallback costs.
- ~~The game's fog in the view~~: measured (C18.md); weather, time of day and altitude still unmeasured.
- ~~How close a free GPU camera can come to the game's own world camera~~: exact in plan, within the engine's own
  1u / 0.5u settle bands in height (C7.md: nine stills, land-mask IoU 0.873-0.995); and the view had drawn the world
  MIRRORED (fixed). The old note follows. How close a free GPU camera can come to the game's own world camera. render.py's ledger says it cannot see the
  real camera path, so an "as the game sees it" view needs the 9001 rig's numbers
  (`project-ff9-world-scene-rigs`).
