# Overworld visual editor: feasibility and plan

**Status:** UNPARKED 2026-10-23 (owner: "let's start planning towards the GUI terrain editor"); A0 built, see Progress.
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
placement straddling x = 0 does not seat, river rung 5b); the design call (arrange carried shapes, never sculpt).

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

- **A0 BUILT (2026-10-23), owner look pending** -> [`A0.md`](A0.md). The GPU view matches `world-render` at the six
  committed bench cameras and a disc-1 coast with blob 0 and coverage <= 2; three break-it mutations are caught.
  Whole-map load 5.4 s (worker thread). Not in A0: the x-torus wrap, picking (A1).
- **A1 BUILT + IN-GAME PROVEN (2026-10-23)** -> [`A1.md`](A1.md). A click picks the surface (front faces, 27-79 ms on
  the whole map) and the strip shows the triple, the engine's ground, the stacked-sheet rule, who the game takes the
  files from, the ledger and the landmark; "Teleport game here" (dev checkout) moved the party to three landmark
  picks within 0.004u, standing within 0.003u of the predicted height. Found on the way: the view draws one folder
  over stock, not the whole FolderNames stack -- the facts flag it per point; drawing the stack is worth doing before C1.

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
2. **Make refusals say where.** An exception that carries the failing point or edge as well as the text
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

- `carve_forest` time at a fixed centre, before and after the walk-in index.
- The harness round trip on the overworld, measured rather than estimated.
- Whether GL works in the Workspace's offscreen smoke run, or what the fallback costs.
- How close a free GPU camera can come to the game's own world camera. render.py's ledger says it cannot see the
  real camera path, so an "as the game sees it" view needs the 9001 rig's numbers
  (`project-ff9-world-scene-rigs`).
