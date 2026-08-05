# Path D coast design menu

> Produced by the scoping round registered in `SHAPE-SCOPING-PREDICTION.md`. Every kit
> call below was run `--dry-run`; **nothing has been deployed**. The two load-bearing
> structural claims (morphs refuse `--size`; `morph_in_place` cannot see disc-9
> overrides) and the recommended carry's gate result were re-verified independently of
> the agents that produced them.

*All numbers below are measured this session against your install (read-only; every kit call was `--dry-run`). New scratch tooling: `C:\gd\Dream-World-IX\.claude\worktrees\peaceful-rhodes-445d5a\studies\coast-shape-language\scratch\design_preview.py` (paints a layout onto the disc-9 grid, measures pairwise gaps, flags collisions with live cells) plus three layout TOMLs in the same directory.*

---

## 0. The hard boundary you are designing inside

Three measurements set the whole menu. None of them is negotiable today.

**The carryable pool is SEVEN mass-sets, not fifty-seven.** Re-ran `carry_units.py` over every rect 1×1…4×4: only these contain every intersecting landmass *whole* with ≥2u frame clearance.

| donor rect | what it is | land | clearance | rot | advisory gates |
|---|---|---|---|---|---|
| **(9,5)+2x3** | "the comma" — mass 11, mountain spine + walkable SSW arm | 5312u² | 4u | **all 4 free** (no objects) | **all clean** |
| (6,4)+2x2 | Shimmering crystal reef, 6 masses | 3632u² | 8u | all 4 | 68 wang seams |
| (7,17)+4x2 | the 4-member chain (beach + 2 dots) | 3392u² | 12u | **rot 0 only** (object at 9,17) | 15 seams, sea-overlap 0.316 |
| (10,17)+1x2 | terminus pair | 448u² | 16u | all 4 | 8 seams |
| (10,17) / (10,18) / (12,10) 1×1 | single dots | 256/192/192u² | 4–16u | all 4 | — |

Everything else in disc 1 is continent-entangled. Daguerreo, the waisted isthmus island, the sinuous island, the Mognet handshake — all unliftable.

**Coast morphs refuse `--size`** (`ff9mapkit/ff9mapkit/cli.py:3774`, verified). And `morph_in_place` reads `world_tris → extract.read_block`, which only resolves stock disc 1/4 — so **there is no post-deploy coast editing on Path D.** Consequence: a multi-block carry is frozen verbatim forever, and the coast-control verbs reach exactly **one** carryable block — (7,17). I scanned the others: (10,17) and (12,10) admit `cliff-bump 2.5` only; (10,18) admits nothing ("the morph window needs at least 2 base-outline gaps").

**But (7,17)'s morph ceiling is higher than the scanner reports.** `world-morphs` tops its ladder at `cliff-headland 8`. Probed past it:

| morph on the (7,17) cliff window (L=72.5u, 16 gaps) | verdict |
|---|---|
| `--cliff-headland 14` | **CLEAN** |
| `--cliff-lobes 8,-6,8` (headland–cove–headland) | **CLEAN** |
| `--cliff-lobes 6,-5,6,-5` (four lobes) | **CLEAN** |
| `--cliff-headland 14` **+** `--beach-slide -6` in one command | **CLEAN**, census miss=0 introduced=0 |
| `--cliff-lobes 10,-8,10` | FAIL — census introduced=2 |
| `--cliff-lobes 14,-8,14` | FAIL — CLEARANCE GATE, outline pinches to 4.0u vs stock 8.5u |
| `--cliff-lobes 5,-4,5,-4,5,-4` | FAIL — vert 7 escapes the drop sets |

Free disc-9 cells right now: everything except `(5,7)-(7,8)`, `(11,10),(12,10),(13,10),(12,9),(12,11)`, and `(0..4, 16..19)`.

---

## 1. THE FRAYING TAIL — an archipelago with an anchor

**Pitch:** you sail in and a mountain-cored island with a long green arm sits NW of a scatter of five smaller islands running away SE, ending in two bare rocks. It reads as a continent dissolving, not as objects placed.

**Classes composed:** `chain` (the arrangement is the class) + `cape` (the anchor's 51.2u walkable arm) + a class-legal wide `strait` (52.0u mask ≈ 55.5u mesh) at the anchor/chain gap. This is chain0's own grammar — anchor mid-run at 10–25× the median member, ends dropping out as ~200u² dots on a single NW→SE axis — and stock's #1 striking chain feature is exactly this arrangement, not any single island.

**Route (verified `--dry-run`, gates green):**
```
cd ff9mapkit
py -m ff9mapkit world-fuse --mod-folder FF9CustomMap-world --target-disc 9 \
    --all-sea-target --skip-mirror --dry-run \
    ../studies/coast-shape-language/scratch/layout_anchor_chain.toml
py -m ff9mapkit world-coastnav --mod-folder FF9CustomMap-world --disc 9 --policy cliffs-refuse
```
Layout = comma `(9,5)+2x3 rot 90 shift 0,0 → cell (14,12)`, chain `(7,17)+4x2 rot 0 shift 0,0 → cell (14,14)`.
Result: `placement[0] ok · placement[1] ok · rect-overlap ok · fuse[0.S|1.N] ok plane=-896 rows=48 grade-jumps=8 · existing-overrides ok`. Teleport ≈ world (992,−832) / (1024,−960).

**Proven vs new:** 100% carry. Zero authored triangles. `--shift 0,0` is mandatory on both (auto-shift on a rect containing empty ocean destroyed a prior 4×4 test with 2223 introduced census misses).

**Effort:** low — two commands.

**Most likely failure:** the 8 reported grade-jumps at the fused plane — two donors' water ladders (sea1→sea3→sea5→sea4) meeting across the channel, an adjacency stock never builds. Expect a tone line or a shelf stopping mid-water. Secondary: Chocobo's Lagoon's prop free-rides on donor cell (9,17) and will render — a recognizable FF9 landmark in a "genuinely new world". Blanking it is 3 lines of `M.deploy_override(M.hidden_block_mesh(...), part="Object")`; `world-island` does this, `world-transplant` does not.

**Falsifiable predictions:** (a) at game-camera height the anchor's 26.5u mountain is legible and the 192–256u² dots are not, so the *run* reads only because the anchor anchors it; (b) the 52u channel reads as "two islands near each other", not as a strait — the characterization's own threshold is ≥35u gap **and** ≥90u run, and our run is 44u; (c) the grade-jump seam is visible from the channel and invisible from either shore.

---

## 2. THE LONG REACH — the comma island alone

**Pitch:** a single teardrop island, ~190u long, with a bare rock spine rising to 26.5u out of a 3u shore, and one green tapering arm you can walk 51u out to the point with open sea on three sides.

**Classes:** `cape` on a solitary island — both of the characterization's striking modes in one object (silhouette **and** total walkability, 0.91 on the limb), and the arm clears the measured "a player notices it" floor of 50u reach.

**Route:**
```
py -m ff9mapkit world-transplant --mod-folder FF9CustomMap-world \
    --cell 10,12 --donor 9,5 --size 2x3 --shift 0,0 \
    --target-disc 9 --all-sea-target --skip-mirror --dry-run
py -m ff9mapkit world-coastnav --mod-folder FF9CustomMap-world --disc 9 --policy cliffs-refuse
```
Measured: `terrain 917 · sea4 1993 · wang-carry incoherent=0 · sea-plan A/B/C all ok (B_max_ratio 2.971, C_overlap 0) · tex-zero-uv 0 · land-fit ok · weld 0 · clip-drop 0 · census miss=2 inherited=2 introduced=0 · gates CLEAN`.

**Proven vs new:** 100% carry, and **this is the cleanest object in the entire vocabulary** — the only carry I ran with `wang incoherent=0` *and* `sea-plan C_overlap=0`. For contrast, the already-owner-accepted (7,17) bench carry warns 16 seams and 0.2222 sea overlap; the chain unit warns 0.316; the reef warns 68 seams.

**Effort:** low — one command.

**Most likely failure:** biome. It is desert-mains + mountain-rock + shore-rock next to a grass bench. And **`--ground` cannot fix it** — I tested: the kit classifies (9,5) as grass so `--ground grass` is a no-op, and `snow`/`canyon`/`scrub` all FAIL `GATE retile` on four unclassified topo-17 tris. Second: the walker follows the 0.91 flank and is stopped by the foot-illegal spine partway — stock-normal, reads as a bug.

**Predictions:** (a) the spine breaks the skyline at approach range and is the thing the owner comments on first; (b) if the island is sited ≥1 screen from the bench the biome objection does not fire; if it is adjacent, it does.

---

## 3. THE RAGGED CAPE — one block, an authored coastline

**Pitch:** a small green pocket island whose seaward face is no longer a smooth arc — two blunt 8u headlands with a cove bitten between them, and a beach dragged 6u landward behind it.

**Classes:** `cape` ×2 + `bay` ×1, composed in one 32u window. This is the *only* design that actually exercises "more control over the coast", and it is the answer to "push the limits" — the composed-lobe profile at depth 8 is deeper than anything previously deployed (the in-game-proven profile was `3.5,-5,6.5`).

**Route (all verified CLEAN):**
```
W="480.0,-1110.98828125:512.0,-1115.4921875"
py -m ff9mapkit world-transplant --mod-folder FF9CustomMap-world \
    --cell 18,3 --donor 7,17 --target-disc 9 --all-sea-target --skip-mirror \
    --cliff-lobes "$W:8,-6,8" \
    --beach-slide "504.0,-1132.0:476.0,-1124.0:-6" --dry-run
```
Variants that also gate clean on the same window: `--cliff-headland 14` (a single 14u promontory — 45% of the island's own radius), `--cliff-lobes 6,-5,6,-5` (a four-lobe crenellated margin).

**Proven vs new:** **this one mints surface.** Every lobe is authored wall + fill + sea zip. The machinery is in-game proven and every law gate runs offline (crack/grain/water-density/ledger/census), but THE DEFECT FOLLOWS THE AUTHORSHIP applies here and nowhere else in the top three.

**Effort:** low-medium — one command, but budget a playtest for the coast itself.

**Most likely failure:** the two convex lips of the cove. A bay is two V-corners; the V-corner cost twelve playtests over ~10u of shore. Also: the whole feature is ~130–260u² of plan change on an 800u² island — the characterization is blunt that sub-500u² concavities "read as coastline noise, not as places", so this may gate green and read as nothing.

**Predictions:** (a) the two 8u headlands, not the cove, are what the camera sees; (b) a walk trap appears at a lip if anywhere; (c) at depth 8 the outline stays above the 8.5u stock self-clearance — the gate proves it offline, and 14,-8,14 already refuses at 4.0u, so the envelope is real.

---

## 4. THE HIGH ISLAND — mint the outline, carry the rock

**Pitch:** a genuine landmass, ~240u across, three lobes, rolling interior, with a real FF9 rock massif standing on it and a canopy blob on its flank.

**Classes:** none of the six — this is a *body*, not a margin. It exists on the menu because the characterization's verdict on striking-ness is unambiguous: relief carries the horizon, plan shape does not, and nothing in the carryable pool except the comma has relief.

**Route:**
```
py -m ff9mapkit world-island --mod-folder FF9CustomMap-world \
    --center 1200,-820 --radius 60 --lobes 3 --relief --ground grass \
    --target-disc 9 --all-sea-target --skip-mirror --dry-run
# then, on the DEPLOYED island (these verbs are target-disc aware and read the overrides):
py -m ff9mapkit world-mountain --mod-folder FF9CustomMap-world --target-disc 9 --near <x,z> --ground grass
py -m ff9mapkit world-forest   --mod-folder FF9CustomMap-world --target-disc 9 --near <x,z>
py -m ff9mapkit world-hill     --mod-folder FF9CustomMap-world --target-disc 9 --near <x,z>
```
Mint measured: 8 blocks, 2132 tris, `all gates CLEAN (geometry, UV language, placement census: 0 MISS)`; advisories `tex-one-window` and `sea-plan Sea4 uniformity`. Note `--beach` is single-block v1 and **refuses** an arc that crosses a block border — I hit that.

**Proven vs new:** the outline is **minted** (synthesis lane), the relief is **carried** (world-mountain is the verb that superseded 8 rounds of falsified massif synthesis). So: authored plan, verbatim rock.

**Effort:** medium — 4 commands, and steps 2–4 cannot be dry-run until step 1 is deployed.

**Most likely failure:** the outline. `multi_blob_outline` is star-convex by construction; a 3-lobe blob at radius 60 has no cape, no bay, no neck — measured elsewhere in this arc, its narrowest waist is 44u and its deepest concavity 176u², both outside stock's classes. It will read as *a shape*, not as *FF9's shape*.

**Predictions:** (a) `world-mountain`'s "plain-grass placement" scan succeeds on this minted island (it is proven on exactly this kind of island); (b) it would **refuse** on the carried comma island, which has no plain-grass field — cheap to test, and worth testing, because if it passes, design 2 gains a second peak.

---

## 5. THE STEPPING ROW — chain2's row regime

**Pitch:** seven small islands on a near-straight east–west line across ~400u of open water. Nothing is big; the *line* is the feature.

**Classes:** `chain`, row regime (stock's chain2: linearity 0.870, gaps 13–56u, gap/diameter 1.5–2.4 — "reads as deliberate paving rather than debris").

**Route:** the (7,17)+4x2 unit at rot 0, then `(12,10)`, `(10,17)`, `(10,18)` as separate 1×1 transplants at rot 0/90/180/270 for variety. Measured composition (`design_row.png`): gaps 39.1 / 49.8 / 69.5 / 96.1u.

**Proven vs new:** 100% carry, and the *only* design where rotation gives you free variety (the dots are object-free).

**Effort:** low — 4 commands, no fuse needed if the pieces sit ≥1 block apart.

**Most likely failure:** it reads as thin. Only two members exceed 500u², and my measured spacings run 39–96u against stock's row regime of 13–56u — the outer half of the row is looser than any stock chain. It will look sparse rather than paved.

**Prediction:** falsified if the owner reads it as a line at all; the honest expectation is "some rocks".

---

## 6. THE IRON GATE — the passage past something you may not touch *(NOT BUILDABLE TODAY — reported because the failure is the finding)*

**Pitch:** a 36u channel between a walkable green headland and a bristling grey crystal reef you can sail past and never land on. This is stock strait #7 (Lost Continent ↔ Shimmering Island) rebuilt from two carry units — the asymmetric case, the single most distinctive-looking cluster in FF9's small-island vocabulary.

**Measured verdict:** `layout_iron_gate.toml` (comma r0 @ (10,12) + reef r90 @ (12,12), gap **36.2u** mask, tipness 0.44/0.38 — both in the class's 0.20–0.53 band) returns:
```
GATE fuse[0.E|1.W]: FAIL plane=768 rows=32 bad=6 e.g. {'row': -204, 'a': 'water', 'b': 'off-lattice'}
```
The reef's **original N frame is the only fuse-blocked frame in the entire donor pool**, and every rotation that brings the two islands into the 22–63u stock strait envelope rotates that frame into the channel. Turning it away works — reef r0 west of the comma gates **clean** (`fuse[0.E|1.W]: ok, grade-jumps=10`) — but the gap opens to **69.5u**, past stock's own 63u→76u break, and it reads as two islands near each other.

**What would have to change:** one predicate in `ff9mapkit/ff9mapkit/world/fuse.py` `_side_row` — tolerate an off-lattice vert when **both** sides classify as open water. Six rows.

---

## Ranking

| # | design | striking | authored surface | effort | verdict |
|---|---|---|---|---|---|
| **1** | **The Fraying Tail** | **high** (arrangement + relief + a walkable arm) | **none** | low | **build this** |
| 2 | The Long Reach | high | none | low | the safe half of #1 |
| 3 | The Ragged Cape | medium | **yes — lobes** | low-med | the capability demo |
| 4 | The High Island | high | **yes — the whole outline** | medium | the biggest object available |
| 5 | The Stepping Row | low | none | low | filler |
| 6 | The Iron Gate | highest | none | — | **blocked by six lines of fuse.py** |

### Build THE FRAYING TAIL, staged — and deploy the anchor by itself first.

Not because it is the safest thing on the list, but because it is the only one that is simultaneously the safest **and** near the top for striking-ness. Reasoning I'll defend:

1. **It authors nothing.** 12 of 13 verdicts and 32 of 37 named defects in the wall arc landed on whatever the round most recently authored. This round authors zero triangles, so there is nothing for that law to bite.
2. **The anchor is the cleanest carry in the game.** `wang incoherent=0` and `sea-plan C_overlap=0` are numbers I did not see on any other donor, including the one the owner has already accepted in-game. If the first Path D coast object ships with zero advisories, any defect that appears is *informative* rather than ambiguous.
3. **It is the arrangement stock is proudest of.** The characterization's own words about the Daguerreo fraying tail: *"If one thing here is worth carrying, it is this pattern, not a single throat."* We can carry the pattern; we cannot carry Daguerreo.
4. **Staging respects one-change-per-test.** Rung A: the anchor alone (design 2, one command, zero advisories) → get the look verdict at the game camera on a stock-relief silhouette in the new world. Rung B: add the chain via `world-fuse` → the only new thing under test is the fused water plane and its 8 grade-jumps. If rung A comes back "the desert reads wrong next to the bench", you have learned that before spending the chain.

Do **not** open with design 3 or 4. Design 3 mints the only authored surface on the menu and its feature is below the camera's noise floor by the characterization's own measurement — a bad first bet. Design 4 mints an entire outline in the class of thing this arc has falsified four separate times, and its most striking component (`world-mountain`) can be added to *any* island later.

**One thing to check before rung B, cheaply:** run `world-mountain --near` in dry-run against the deployed anchor. If its plain-grass placement scan accepts a carried stock island, then designs 1, 2 and 4 collapse into one and the answer changes.

---

## What this vocabulary says we cannot do yet

We cannot build **an isthmus, a bay at class scale, a strait at class width, or a tight archipelago cluster** — and all four refusals trace to the same root, which is not a missing shape verb.

**The single most valuable missing capability is a donor-rect EXCISE: drop a cropped foreign landmass from a carry and re-zip sea4 over its footprint.**

Why this one:

- **It is the binding constraint on everything else.** The pool is 7 mass-sets out of 57 landmasses, and the disqualifier in essentially every case is a *neighbouring* mass crossing the rect frame, not the target island. `(6,6)+2x2` holds the whole 3616u² waisted island — the only object in FF9 that reads AS an isthmus — and is disqualified solely by 43 cells of Forgotten Continent in the corner. `(3,11)+2x4` holds the sinuous island, disqualified by three neighbours. `(5,15)+3x2` holds Daguerreo — 9264u², 31.4u relief, the only chain anchor in the game with a mountain — disqualified by the same continent.
- **The machinery already exists and is already gated.** `TR.DropTris` (`ff9mapkit/ff9mapkit/world/transplant.py:1998`) and `TR.EmitTris` are first-class transplant tweaks with scope gates; `coastmorph.beach_slide` already uses the drop-and-refill idiom; `meshedit.earclip`/`cover_gap` build the patch. Nothing is exposed on the CLI. The isthmus pass scoped it at ~150 lines.
- **It authors the cheapest surface in the world.** The excised footprint is covered by **sea4** — the anti-tiling quadrant band, where tile choice is free. No land, no land/sea junction, no wall, no walk surface. It is the one authoring job in this arc that cannot mint a walk trap.
- **It pays out beyond this class.** Every future multi-block island carry near a continent has the same crumb problem, and the alternative today — `--land-margin 0` — ships a sheared plateau terminating in mid-air on a ruler-straight 64u block line, which is the most legible possible artifact under THE FORM LESSON.

Runners-up, in order, each small and each named precisely:

1. **Fuse off-lattice tolerance** — `world/fuse.py` `_side_row`: accept an off-lattice vert when both sides are open water. Unblocks the entire strait class (design 6) at its striking width.
2. **The shift lock** — `world/transplant.py:2604-2628`: on a donor whose land reaches no border, `tongue` is empty so `avail` is empty and shift is pinned to 0. Allowing a shift up to `clearance − land_margin` gives continuous 4u gap control. Today the closest two carried dots can be placed is **49.8u** (measured); stock's cluster regime is **4–20u**, so no stock-spaced archipelago cluster is currently expressible.
3. **Region-capable coast morphs** — `cli.py:3774` refuses `--size` with any cliff verb. Until this lifts, six of the seven carryable islands have a permanently frozen coastline, and "more control over the coast" means control over exactly one 800u² block.