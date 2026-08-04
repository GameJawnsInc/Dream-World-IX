## Completeness review — 5 findings the panel missed

Measured, not inferred: every file:line below I opened myself; the two timing/UV numbers come from scripts I ran against this worktree and the live install.

---

### 1. Nothing invalidates the systems a geometry edit silently breaks — 1 of 4 post-steps is automated

**Why the panel missed it.** Six lenses all looked at the *producer* side (does the mesh get built right, does a gate reject it). Nobody asked what else in the game is a *function of* the geometry and therefore goes stale when it changes. The project has already learned this lesson once and generalized it exactly one step: the disc-4 mirror is an auto-run post-step in every writer (`world/terrain.py:100,145,336`, `world/island.py:1055`, `world/interior.py:2509,2551`, `world/fuse.py:222`, `world/entrance.py:1037`, `world/blendio.py:260`, `cli.py:3796,3887,4735`). The other three coupled systems got no such treatment.

**Evidence.**
- **Vehicle legality (`coastnav`) auto-runs for exactly one verb.** `cli.py:4569` passes `coastnav=not args.skip_coastnav` — and that line is inside `_cmd_world_island` (confirmed: the nearest preceding `def _cmd_` in 4530-4575 is `_cmd_world_island`). Greps over `cli.py:4206-4500` (`_cmd_world_transplant`/`_cmd_world_morphs`) and `5026-5125` (`_cmd_world_fuse`) return **zero** hits for `coastnav` — not a call, not a warning, not a printed reminder. Same for `world-terrain`, `world-reclaim`, `world-coast`, `world-rim-retile`, `world-mountain/hill/forest`. Yet `world/coastnav.py:8-13` states the hazard generically — "A synthetic landmass ships a full-cell ocean plane under its land… the probe hits the ocean underneath the terrain (topo 57, in the Narciss mask) and the move is LEGAL — the hull crosses the cliff" — which is precisely what `world-reclaim` (ocean → walkable land) and `world-terrain` (raise ground over water) produce. `coastnav.py:29` adds the other half: "53 is additionally the class the get-off gate demands — a coast with no 53 can be sailed to and not landed on."
- **Minimap is never auto-refreshed by anything.** `navimap.composite_world_map` has exactly one caller: `cli.py:5161`, the `world-minimap` verb itself. No geometry writer calls it or mentions it.
- **Encounters are not even joined to geometry.** `world/worldpack.py:14`: an encounter record "is chosen by zone-slice x `topograph = pattern>>2` x `fog = pad&1`". Grepping `island.py`/`transplant.py`/`interior.py`/`terrain.py`/`fuse.py` for `encount` yields one *comment* (`transplant.py:275`) and no code. So a new landmass mints topographs and lands in a zone with no report of which of the 355 records its cells will resolve to.

**Recommendation.** Give `world/` a single `post_edit(written, *, mod_folder, …)` hook alongside `auto_mirror` — it already receives the exact written cell set, which is the hard part (`discmirror.py:28-42`, THE EVIDENCE CONTRACT). Run coastnav restamp on it for any verb that can put land over water (reclaim/terrain/transplant/fuse), and emit a *staleness warning* (not a rebuild) for minimap and for the `(zone, topograph)` → encounter-record join whenever the written cells introduce topographs the zone slice has no record for. Cheapest 80%: even just printing the reminder in the four handlers that currently print nothing would have prevented the sail-through class.

**Impact 4 · Effort small** (warnings + wiring coastnav into 4 handlers) **to medium** (the encounter join report).

---

### 2. The census's cost model makes the panel's own top prescription unaffordable — and the fix is provably free

**Why the panel missed it.** No lens owned performance. The `census-blindness` theme (5 findings) prescribes finer/denser sampling; the `gate-wiring` theme prescribes running gates at more chokepoints. Both multiply calls into `placement.place`, which nobody costed.

**Evidence.** `world/placement.py:52-77` is a linear scan: for every sample, for every mesh in registration order, for every triangle in buffer order, compute a cross product and a barycentric test in pure Python — no spatial index anywhere in the 99-line module. `census` (`placement.py:81-99`) does `samples²` of those. Measured on this machine (synthetic unindexed grid meshes, one mesh, hit found mid-buffer):

```
tris=  512   census(24x24=576) =  0.24s
tris= 2048   census(24x24=576) =  0.86s
tris= 4608   census(24x24=576) =  1.95s   (3.38 ms/sample)
```

A real gate call is far worse than this on three independent axes: the meshlist is the full registration stack (`coastnav.py:62` names 8 parts: Object, Terrain, Beach1, Sea1, Sea2, Sea3, Sea5, Sea4), a **MISS scans every triangle of every mesh to completion** — and MISSes are exactly what the gate exists to find (`placement.py:24`, "MISS must be 0 everywhere") — and `transplant.py:3604` scales the grid with region size (`sx_n, sz_n = census_samples * tw, census_samples * th`), so a 3x3-block region at the default 24 is 5184 samples over 9 blocks of stacked parts. That is minutes, per gate run, per deploy. Halving the sample pitch to resolve a 4u cell costs 4x that.

**Recommendation.** Bucket each mesh's triangles once into a uniform XZ grid (4u, matching `texgates.py`'s `CELL = 4.0`) keyed by triangle bbox, and have `place` iterate meshes in registration order but only the candidate bucket, taking the **minimum buffer index** among passers. This is *exactly* semantics-preserving — the engine rule the module reproduces is "first mesh with any hit, then first triangle in buffer order" (`placement.py:15-21`), not nearest-hit — so the winner is unchanged by construction, and it is testable as byte-identical output against the current implementation on real blocks. Expect ~2 orders of magnitude, which converts "sample finer" from a proposal into a default. ~40 lines in the smallest module in the package.

**Impact 4 · Effort small.**

---

### 3. Three divergent implementations of the Sea5 tile classifier, with three different arity rules

**Why the panel missed it.** `grammar-as-code` says the decoded grammar "lives in prose; no gate scores against a reference." The sharper problem is the opposite: where the grammar *is* in code, it is in code three times, and the copies disagree. `coordinate-centralization` and `walkability-oracle` named duplication for *coordinates* and *ground queries* — not for the tile-grammar decoder, which is the thing the coast pillar's laws are actually written in.

**Evidence.** Same question ("which deepset/transition tile is this Sea5 cell?"), same helper (`water._fit_tile`), three answers:

| implementation | arity guard |
|---|---|
| `water.py:544` (`read_sea5_tiles`, the reference reader over real blocks) | `if all(c in d for c in ((0,0),(1,0),(1,1),(0,1)))` — **all four corners required** |
| `transplant.py:2481` (`_sea5_deepsets`, feeds `wang_carry_gate` at `transplant.py:2556`) | `if len(d) >= 3` **plus** a degenerate-UV guard `max(us)-min(us) > 1e-6` |
| `rimretile.py:269-288` (`_sea5_deepsets`, feeds the rim audit at `rimretile.py:177,256`) | **none** — `_fit_tile(d)` is called on whatever corners exist |

`water._fit_tile` (`water.py:504-520`) has no arity check of its own; it returns the **first** rotation in `ROTS` order that fits within 0.01. Fed one or two corners it is trivially satisfiable, so a sliver cell gets an essentially arbitrary rotation. Net effect: the same deployed cell is *unclassified* to the reference reader, *dropped* by the carry gate, and *confidently classified* by the rim retiler — which then iterates "to a fixed point" on that classification (`rimretile.py:290-297`). This is the exact shape of "the audit is green and the owner sees a seam," and it is live code: HEAD is `972918db fix(world): THE CROP-SEAM WIDENING -- rim retile audits measured seams anywhere, not just the frame`.

**Recommendation.** Promote one classifier — `water.classify_sea5_cell(corners, *, min_corners=4)` — and have both `_sea5_deepsets` copies call it, making the arity relaxation an explicit, named argument at each call site (the rim audit may legitimately want 3; it should say so, not omit the check). Then add the differential test that matters: for a corpus of real blocks, the three call paths must agree on every cell either of them classifies.

**Impact 4 · Effort small.**

---

### 4. The world mod folder has no lifecycle — 32 deploy verbs, zero enumerate / revert / lock / version gate — on state 18+ concurrent sessions share

**Why the panel missed it.** `provenance-manifest` asked for *attribution* of deployed bytes (a debugging/reproducibility concern). The operational axis is separate and, by the project's own history, more expensive: multi-session safety and reversibility.

**Evidence.**
- The full world verb list (extracted from `cli.py`) is 32 verbs, **all** of which read or write; there is no `world-status`, `world-list-deployed`, or `world-revert`. Compare the field pillar, which writes a per-id `revert_deploy_<id>.py` on every deploy (repo `CLAUDE.md` §4). A grep for `revert|undeploy|unlink` across `world/*.py` returns only `atlas.py:212` (deleting a legacy cache) and prose in comments.
- No locking of any kind: `grep -i "lock|flock|msvcrt|fcntl"` over `world/*.py`, `config.py`, `fsutil.py` returns zero. `mesh.deploy_override` (`mesh.py:176-196`) resolves `<game>/<mod_folder>/<relpath>` and overwrites unconditionally; its only guard is `require_block_in_grid`. Two worktrees authoring different worlds into `FF9CustomMap-world` will silently interleave block files, and the resulting on-disk world is a union nobody authored. Repo `CLAUDE.md` §3 states the premise plainly ("Many agent worktrees run concurrently, sharing ONE game install… ONE set of mod folders"), and the cell-allocation registry that would prevent it is study-local (`canvas.json`; `grep -rn "canvas.json" --include=*.py` over the package returns nothing).
- The format has a version field that nothing enforces: `write_ff9mesh` always stamps `VERSION = 1` (`mesh.py:23,79`) and `read_ff9mesh` unpacks `version` (`mesh.py:104`) and never checks it. Since deployed overrides are never enumerated or cleaned, a v1 file from an abandoned experiment three months ago still participates in world load, indistinguishable from current output.

**Recommendation.** One small module, three cheap things, no new concepts: (a) a `world-status` verb that walks the mod folder's `FF9_Data/WorldMap` tree and prints `(disc, block, part, mtime, size)` — this is the enumeration both this finding and the panel's manifest theme need, and it is ~30 lines; (b) an append-only deploy journal next to it so `world-revert --since <stamp>` can delete exactly what a session wrote (`auto_mirror` already receives the written-path set, so the data is in hand); (c) reject a non-`VERSION` magic on read instead of ignoring it. Skip file locking — the journal plus a "these cells were last written by another journal entry" warning gets the concurrency win without a lock protocol.

**Impact 3 · Effort medium.**

---

### 5. The provenance gate — a stated hard constraint — has no world chapter, and the atlas deploy path can launder third-party art

**Why the panel missed it.** All six lenses were engineering lenses. Provenance here is a *release* constraint the project treats as non-negotiable (repo `CLAUDE.md` §5: "Provenance gate is CLEAR and must stay so — zero Square-Enix binary bytes"), and the kit is publicly shipped as 1.0.0b1.

**Evidence.** `ff9mapkit/docs/PROVENANCE.md` is 103 lines and enumerates every derived asset class — blank field, region template, test fixtures, battle-map FBX/PNGs, minted-scene assets, the id↔name tables. A case-insensitive grep for `world|ff9mesh|atlas` across it returns **nothing**. Meanwhile:
- The world pillar's only deliverable *is* bytes. Unlike a field (whose artifact is a `field.toml` recipe), a world exists solely as `.ff9mesh` files, and `world-transplant`'s whole premise is carrying a **real donor block verbatim** — verts, UVs and tangents copied out of `p0data` (`mesh.py:1-13`, `world/transplant.py:1-3`). Sharing a world today means sharing those bytes; there is no recipe-level reproduction path and no doc telling a user that.
- `atlas.deploy_atlas` (`atlas.py:422-433`) copies a whole atlas PNG into the mod folder, and `add_tile` (`atlas.py:405-419`) sources it from `load_atlas(...)` whose default is `source="engine"` — which **resolves the live loose override first** and explicitly names Moguri's HD atlas as the expected case (`atlas.py:190-192`: "a loose mod override (e.g. Moguri's 2048×4096 HD atlas) is read directly"). So on a Moguri install, `world-atlas-add-tile` writes a Moguri-derived HD texture into `FF9CustomMap-world` with no attribution and no record — a third-party-art redistribution vector that no gate, doc, or warning covers.

**Recommendation.** Add a "World / overworld" section to `PROVENANCE.md` stating plainly that deployed `.ff9mesh`/atlas overrides are user-install-derived and not distributable, and that the shareable artifact is the *command sequence* (the `examples/continent-v1/README.md` model). Then make `add_tile` refuse — or at minimum loudly warn and record the source kind — when `resolve_atlas_source` returns `kind == "loose"`, since baking someone else's HD atlas is never what the caller meant. The `_fingerprint`/`.src.json` machinery at `atlas.py:144-163` already computes the identity you'd stamp into the record.

**Impact 3 · Effort medium** (doc) **/ small** (the `add_tile` guard).

---

## Areas I checked and found genuinely fine — do not spend effort here

- **Atlas free-region allocation is sound.** I suspected `find_free_region` (`atlas.py:343-366`) was unsafe because it claims space by alpha alone while the blank-tile law makes alpha-0 texels *render* (white), so a painted tile could repaint stock faces map-wide. Measured against the live install: `find_free_region(atlas, 48)` returns `(976, 976, 1024, 1024)`, and over 3212 real donor faces sampled from 24 disc-1 blocks, **0** have a UV bbox overlapping that box and **0** sample a near-transparent tile at all. `palette.py:66-68`'s claim that blank filtering is "normally a no-op" holds up. Non-finding.
- **The two write-time hard gates are correctly placed.** The unindexed-contract assert and the off-grid refusal sit at the lowest write layer (`mesh.py:71-74`, `mesh.py:43-57` called from `169,193`), not at call sites — which is what makes them unskippable. `deploy_override`'s docstring (`mesh.py:190-192`) shows the author already reasoned through the "why not retag at each call site" trap. This is the healthiest code in the package.
- **`auto_mirror`'s evidence contract** (`discmirror.py:28-42`) is the right pattern for post-steps and should be the template for finding #1 rather than something new.