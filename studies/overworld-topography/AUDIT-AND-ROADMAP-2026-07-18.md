# Overworld adversarial audit + exploratory roadmap — 2026-07-18

> **What this is.** Two multi-agent workflow runs (137 Sonnet agents, ~14M subagent tokens) executed 2026-07-18:
> **Phase 1** adversarially audited the entire overworld knowledge base — 260 falsifiable claims extracted from
> five doc layers (the coast-mosaic memory law index, the interior-topography memory + study README, the misc
> overworld memories, the docs/skill layer, and the code's own self-claims), clustered into 14 subsystems, attacked
> by one auditor per cluster, every alleged defect re-derived by two independent skeptics (many re-ran the study
> scripts against the live install). **Phase 2** swept six lenses for next work (pendings ledger, unexplored stock
> data, verb-fidelity gaps, audit repairs, engine candidates, player value), merged 113 raw candidates to 28,
> scored each with four judges (feasibility / player-value / fidelity / leverage-risk), and tiered them.
>
> Status ledger: `[ ]` open · `[x]` done (update in place as items land).

---

## Phase 1 — audit scoreboard

**260 claims: ~205 held outright · 20 defects confirmed 2-2 · 19 split 1-1 · 13 allegations rejected · 3 unverifiable offline.**
The mechanisms, gates, and constants overwhelmingly survived; the recurring defect class is **measured numbers and
status framings that don't reproduce from the scripts that supposedly produced them**. The study-arc corollary of
the GUI study's docstring law: **a number without a rerunnable script is a wish.**

| Cluster | claims | held |
|---|---|---|
| Coast Ladder & Open-Water Mechanics | 24 | 21 |
| Beach Shape, Foam & Beach-Mint | 23 | 17 |
| Ground Families & UV-Translation Laws | 19 | 9 |
| Coastal Cliff-Wall Texture Constants | 9 | 6 |
| Interior Massif & Mountain-Wall Organization/Carry | 29 | 22 |
| Interior Topography Census, Terrace & Canopy | 18 | 13 |
| Transplant Growth-Cuts, Weld/Hairline & Donor-Carry Gates | 28 | 25 |
| Fuse Law, Multi-Cell Census & Continent Composition | 9 | 9 |
| Disc-Mirror/Two-Tree & Cross-Cutting Status/Dead-Ends | 18 | 18 |
| Overworld Entrances, Nameplate & Navimap | 11 | 8 |
| Ground-Query, Movement-Legality & Walk-Trap Engine | 24 | 19 |
| World Dispatchers, Encounter Tables & Minimap Arming | 14 | 11 |
| Vehicles, Boats, Chocobo & F6 Vehicle/Actor-State | 21 | 20 |
| Terrain-Authoring Reshape Law & Engine Guards | 13 | 7 |

**What survived (worth stating):** the whole fuse/continent cluster, the whole disc-mirror/two-tree cluster, 25/28
transplant gates, 20/21 vehicle claims, the full per-family UV-translation offset table (reconfirmed to 5dp by
independent probes), the beach translation law, the ground-query registration-order core, walk-legality, the
ensemble/free-ride mechanism, the MOD-OVERWRITE gate, and every recorded dead-end.

---

## Phase 1 — confirmed defects (20, all 2-2 verified)

### A. The one code bug — FIXED
- [x] **`pack_cell_tag` masked z to 7 bits; the engine masks to 6.** `entrance.py` packed `(cell_z&0x7F)<<8` but
  ff9.cs `WorldEvent` builds `z<<8 & 0x3F00` — entrances at `cell_z ≥ 64` (southern half of the map) could never
  fire. **Fixed on master `2b73900`** (2026-07-18, same day, own task session).

### B. Numbers that don't reproduce (the "748/0" class)
- [x] **Canyon "748 wall tris map-wide, 0 coastal"** — `family_wall_envelope.py`'s tally only sums the **top-8
  specimen blocks per family** despite the census loop scanning all 260. Literal re-run: 231/0. Two independently
  written true full-map sweeps both converge on **~655 tris, ~1–3 borderline-coastal** (negative-y, likely interior
  gorge). Git archaeology: the 748/0 figure was *never* reproducible from this code+data. Frozen into the
  coast-mosaic memory, CLAUDE.md Frontier, this study's README (~L836), and the `grassland.py:101` comment.
  **The WALL-CONTEXT LAW's direction survives** (canyon drastically less coastal than grass/desert/snow ~97–99.7%),
  and both refusal gates are correctly wired (`island.py:249`, `transplant.py:493`).
- [x] **Snow "733/733 coastal"** — literal re-run: 272/8; true full-map: **1019/1016 (99.7%, not literally all)**.
  Max face height 5.73u does reproduce exactly.
- [x] **EXACT-PIN "60/63"** — exists only as a prose comment (`uaho_probe_panel.py:174`) citing itself; no committed
  script computes it (the script's `n_snap` counts a different, later operation).
- [x] **NO-FREE-MESA "74–95% high rim"** — no committed script computes it; the nearby ~74% in `crag_anatomy.py:20`
  measures a different quantity (course-weld fraction). The qualitative law itself is well corroborated.
- [x] **BAND-SWEEP "exactly 4.0 tiles / v 2.5–3.3 rows"** — no committed script computes the continuous spans;
  `uaho_flow_anatomy.py` prints discrete touched-tile sets (columns do cluster ~4; rows read as 3–4 discrete bins).
- [x] **Rock-tile base band "564/585 (rows 7–10 × cols 6–9)"** — 564 actually equals rows 9+10 summed across ALL
  columns; the stated rectangle sums to 556/585. Headline counts (8945 groups / 13929 pairs / 86 tiles / crest
  950/1006) all reproduce exactly.
- [x] **Wall foot-weld "~100% (15/15, 13/13, 19/19, 27/27)"** — those four are real but are the strongest cases;
  block (21,14) is **0/5** and (13,5) is 9/11. Course_vert_share=0.0 and crest 0/57 reproduce exactly. *(split 1-1
  on "acknowledged", confirmed as cherry-pick)*
- [x] **GORE-PANEL "residual p90 ≤ ~25px"** — re-run: 9 patches (vs "~8", fine), cut meridians 120°/270° match, but
  measured patch 3 has **u-residual p90 = 40px** — a real counterexample among the law's own specimens.

### C. Superseded laws still live in the canonical layer
- [x] **RING LADDER "exact fixed order"** — the kit's own later map-wide census admits the lawful **{sea1,sea5}**
  adjacency (sea3 skipped): `coastmorph.py:2820` `_LAWFUL_ADJ`, memory L2796. The LAW INDEX entry (L19) and
  `coast-laws.md:24` still state unqualified exact order. *(the index entries confirmed; the memory-body variant split)*
- [x] **MOAT LAW v2 labeled "final form"** — the "final form" label belongs to the **VERGE RULE** (2u topo-49
  relabel), not the superseded ~4u clearance; and `references/terrain-entrance.md:78` still prescribes "clip the sea
  mesh at the coast outline," which the FULL-CELL SEA REVELATION replaced.
- [x] **SHAPE-CLASS gate docstring** (`coastmorph.py:1259`) still carries the "+46% nose" framing that the 32-run
  re-census diagnosed as a pocket misread (the memory's LAW INDEX itself is correct). *(split at index level,
  confirmed at docstring level)*
- [x] **ONE GLOBAL WINDING FLIP is a dead law** — lived only in the abandoned `bay_warp` warp experiment; shipped
  `transplant.py` performs only det=+1 rigid rotations that can never flip winding. The LAW INDEX presents it as a
  durable principle for carried geometry generally.
- [x] **STRICT SHORE donor table stale vs its own tool** — under today's `cut_census`, donors (8,16) and (7,15)
  return **zero** ok cut lines, and (16,17)'s in-game-proven line 1056 now trips `conforming-on-line` (a risk added
  seven commits after the table was minted). *(split 1-1: the build it blessed remains proven; the table is stale)*

### D. The engine is sharper than the docs
- [x] **GHOST-4078 is not "invisible to every query"** — live engine paths set `WMPhysics.IgnoreExceptions=true`,
  re-enabling 4078/4088/2040 as hits: the **per-frame ground snap for every non-controlled actor** (ff9.cs:5116),
  the overworld-entry fix-up `w_movementChrFixBug` (ff9.cs:4666, every entry), and
  `w_movementChrVerifyValidCastPosition`. Matters for followers/co-op ghosts on custom ground.
- [x] **Mesh scan order has real exceptions** — block 219 (Water Shrine) early-returns after Object/Terrain/Sea3/4/5
  (WMWorld.cs:569); volcano blocks insert VolcanoCrater/VolcanoLava **before** Beach1 (WMWorld.cs:606). The
  placement simulator's "universal" order is right everywhere else.
- [x] **F6 vehicle allow-list: 9009 is NOT crash-safe in shipped code** — `VehicleAllowByWorld` is exactly
  {9002, 9010, 9011}; 9009 defaults FootOnly; forcing needs the separate default-OFF `_vehicleForceAll` "may CRASH"
  toggle. The vehicles memory claims otherwise (a 2026-07-08 in-game note says forcing 9009 didn't crash — reconcile
  docs vs dict, see roadmap).
- [x] **Navi-map markers: `ff9.navipos` locIds 49–53/59–63 are all-zero in BOTH map dimensions** — the bit math
  (base 736, bytes 92/94/96/98) and the 63→49 Chocobo's-Paradise alias verified exactly, but a revealed custom bit
  in that range has no coordinates to draw at. **Re-scopes any custom-marker plan.**
- [x] **Special/friendly pack empty slot is `0xFFFF`, not the documented 0** — OVERWORLD_ENGINE.md:949 says "0 =
  empty"; the kit's own `SPECIAL_EMPTY = 0xFFFF` (`worldpack.py:39`) and the real disc bytes (65535 everywhere) agree
  against the doc.
- [x] **Stale `ff9.cs:7141` citation for `w_nwpHit`** — s39's insertions moved it to ~7221; the stale line is baked
  into `terrain.py`'s module docstring, the terrain memory, and OVERWORLD_ENGINE.md:462.
- [x] **Disc-4 selection isn't "purely" SC≥11090** — `WorldConfiguration.GetDisc()` first checks the config-driven
  `_customDiscModifier.HasCondition` override, then falls back. *(split 1-1 — arguably a Memoria-config nuance)*
- [x] **Navi arming nuance** — 9002 truly never arms; 9000/9009 arm unconditionally; but **9005 arms conditionally
  on ScenarioCounter==9605** (the memory does scope 9005 separately; the "every… unconditionally EXCEPT 9002"
  shorthand is what's wrong). *(split — partial strawman)*
- [x] **world-reclaim streaming-site line cite wrong** — `IsSea` gate confirmed at WMWorld.cs:495 and **:1250**
  (not the documented :1180); mechanism itself fully verified, incl. `[NonSerialized]` and no downstream gate.
- [x] **terrain "591-up/0-down" winding figure** is block-(16,14)-specific, presented as general. The other three
  reshape "mesh bugs" verified solid (incl. live byte-identical boundary test across (2,7)+(2,8)).
- [x] **LOAD-BEARING RULE mechanism nuance** — "overlay loses the raycast" is the wrong mechanism: a render-only
  overlay is simply **never registered** in ActiveWalkMeshes; and overriding the Object part on a block whose stock
  prefab carries a real ObjectForm1 (town blocks) is a genuine walkability edge the universal framing misses.
  *(rule-of-thumb stands; split on the restatement, confirmed on the mechanism claim)* — **FIXED 2026-07-19**,
  both halves source-verified against the engine (not transcribed): `WMBlock.ActiveWalkMeshes` serves only
  Form1/Form2 lists, and `RegisterBareObjectOverride` (`WMWorld.cs:831`) calls `AddForm1Transform` but never
  `AddWalkMeshForm1` (`:846`) ⇒ non-registration, no raycast contest. The town-block edge is real and now
  documented with its selector: `:556` (`prefab.ObjectForm1` → `RegisterBlockComponent(form1: true)` → the
  override replaces `mesh` at `:790` and IS registered at `:813`) vs `:563` (bare → render-only). Corrected in
  the skill reference `terrain-entrance.md` and memory `project-ff9-overworld-terrain-authoring`.

### E. Precision nicks in the cliff/wall constants *(mostly split 1-1 — real data, arguably in-tolerance)*
- [x] Desert top-edge V is **not** zero-spread (IQR 0.018–0.029 across topo45/46); grass/highland/topo-27 genuinely
  are exact. Medians all reproduce (0.8926 / 0.8721 / 0.9443 / ~0.39).
- [x] Per-column lip anchor: (7,17) and (16,17) — 2 of 5 specimens — carry a small minority (6.7% / 2.6%) of
  off-band V values (0.8936/0.9219) on frame-edge verts, some at the waterline.
- [x] On-grain gate: code enforces **8.0u** (`island.py:352/594/611`), the law says "~6.6u".
- [x] Topo→family partition covers **35 of 37** ids — topo 38 (bare dirt hillsides, 3119 tris / 52 blocks) and
  topo 51 (stream) are unassigned extras.
- [ ] LOOK-FAMILY / ISLAND COROLLARY headline numbers reproduce almost exactly (14 components, one continent with
  high_a 31.6k / esc 211k); the splits are scope-phrasing.

### F. Unverifiable offline (trusted on their playtest record)
COL-FREEDOM's in-game invisibility; its row-swap converse (the pale off-course square); NO-ENCLOSED-DUNES under the
census 2000-cell cap.

### G. Rejected allegations (13 — the skeptic system working)
(7,17)-only-beach ×2, HUG LAW drift ×2, the 44-donor/block-219 claim, `mint_landmass` naming nit, VertexDisplace
envelope, step-ceiling 2.34375u, topo-13 shelf pinning, GROWTH CEILING skill restatement, mesh-precedence
restatement, WORLD09 roster claim, terrain-entrance 4-bug restatement — all died as strawmen, misreadings, or
caveats the source already carries.

---

## Phase 2 — the roadmap (28 candidates, 4-judge scored, synthesis-tiered)

Judge key: `feas`=feasibility/cost · `play`=player-visible value · `fide`=fidelity north-star · `leve`=leverage/risk.

### DO-NEXT
- [x] **Re-census wall-envelope map-wide, fix canyon/snow figures** (6.75: feas 9 play 1 fide 8 leve 9) — extend
  `family_wall_envelope.py`'s tally to all 260 blocks, inspect the ~3 flagged canyon-coastal tris, correct every
  citation. Root-causes 5 confirmed findings at once. Offline, zero risk.
- [x] **Doc/citation corrections batch** (5.5: feas 9 leve 9) — the ~18 stale passages from Phase 1 §B–E above.
  Zero player value; hardens the layer every future session reads.
- [x] **Fix pack_cell_tag's cell_z 6-bit mask** — landed on master `2b73900`.
- [x] **Auto-run world-mirror inside the deploy writers** (6.5: leve 8) — **DONE 2026-07-19** (`b7d2435`): all 14
  worldmap-writing verbs tail-call `discmirror.auto_mirror`; `--skip-mirror` opts out; standalone verb unchanged.
  Two adversarial review rounds hardened the design: auto_mirror consumes the actual written `Path` returns (a
  mocked hermetic test is inert by construction — the first draft could mirror the LIVE install from a unit test)
  and `mirror(cells=)` scopes the auto path to the cells written this call (no more whole-tree clobber of
  hand-authored disc-4 divergence). 23 regression tests incl. the reviewers' own reproductions; suite 3717 green.
  **Live check ★ DONE 2026-07-19**: the comp20 bench+carve deploy was the maiden run — 36 files cell-scoped to
  Disc4, inner-writer skip + one CLI pass exactly as designed, playtest clean.
- [x] **Grow the massif `--donor` library past 3** (6.75: feas 8 fide 8) — **census DONE 2026-07-19** (`ef31e18`,
  `donor_qualify_scan.py`): 87 rock components map-wide; sanity anchors reproduce all 3 known donors exactly;
  **7 new structurally-qualified candidates**; **comp20 (12,16)-(12,17) passed EVERY offline gate incl. a full dry
  carve** (bench r48/seed42, cleaner than the original Uaho numbers) → **★ IN-GAME PROVEN 2026-07-19 ("looks
  good", first-deploy pass): the 4th qualified `--donor`** — bench at (448,−1216) blocks (6-7,18-19), massif at
  (450,−1216) rot 180°, teleport (412.5,−1215.5), kept deployed. New laws: THE CONTINENTAL ROCK NETWORK (comp0 = 56% of all map rock, 66 blocks, disqualified
  by 36 nested rings incl. an unowned aperture) · THE DRY-CARVE ZIP GATE is a third independent filter (comp10
  passes structure+footing, fails the zip annulus). comp9 (multi-block span) + comp10 (zip notch) = rescue
  follow-ups.
- [x] **Decode the remaining discmr.img pack sub-tables** (6.75: fide 9) — **DONE 2026-07-19** (`3e4f797`,
  `discmr_subtables.py`, all 67 tables): **the ModelSea question is CLOSED negative** — table 66 loads but its only
  consumer is empty commented-out code with zero call sites (the rendered sea = `SeaBlockPrefab`), so `world-water`
  keeps its real-block byte survey as ground truth. The real find: **41–52 = twelve LIVE per-WorldEffect
  ambient-SPS effect-area tables** (64B sentinel-terminated records — a future authoring surface, needs full-pack
  repack for count changes); ColorTable(5) dead + superseded by `WeatherColors.csv`; AnimationTable(6) live for
  exactly the 2 beach foam-scroll speed fields; 32 dark unlabeled tables (8–40 minus 37); every live table
  byte-identical across discs. OVERWORLD_ENGINE.md's pack section corrected accordingly.

### SOON
- [x] **Resolve ground-family + ecotone decode gaps** (6.0) — topo-16 dirt has no translation formula; canyon's
  un-chased 3rd v-level; topo 7/62 lumped with 49 unconfirmed; the earmarked 5dp ecotone strip decode. **Gates** the
  ensemble-carry and mixed-biome items below — sequence first. — **★ ROUND 1 DONE 2026-07-19**
  (`3f99959` study + `b5bb1a7` productization; full record →
  `studies/overworld-topography/GROUND-FAMILY-DECODE-2026-07-19.md`). 6 decode lanes × 3 adversarial lenses
  (REPRODUCE/METHOD/OVER-CLAIM) + a completeness critic; 25 agents, 0 errors. Shipped: **the `wall_coastal` gate
  was failing OPEN** — `island.py` tested `is False`, so the *unset* key on scrub/brush/dunes returned `None` and
  every unmeasured family was silently ALLOWED to mint an island (its sibling `transplant.py` was already
  `is not True`); now fail-closed at both chokepoints · scrub=`False` (touches topo-58 exactly ONCE map-wide),
  dunes=`False` (ZERO topo-58 edges anywhere), brush deliberately UNSET → fail-closes · the new **`STRIPS`
  table** (grass|desert `du=0.52442,dv=-0.04687`; desert|dunes `du=-0.13476,dv=-0.09863`), which **corrected a
  shipped earmark whose dv was off by exactly one row pitch** — minted THE UNION METHOD (a single-side fit ties
  between row alignments because B's row0 is 1 texel shorter than rows 1-3) · `MOUNTAIN_ROCK_TOPOS` {49,7,62}→{49}
  (7 = flat walkable ground, 62 = steep stream-bank; absent from all 4 qualified donors, A/B-proven no-op:
  Uaho byte-identical, others identical refusal) · two corrected tallies (desert 12/13→**19/20 map-wide**; the
  canyon wall figure wrong a SECOND time — **594 of its 655 tris are topo-49 MURAL**, true wall = 60 tris/8 faces).
  New laws: **A UV-RECT COUNT IS NOT A TOPO COUNT** · **naive global-pooled min/max over specimens is unsafe**
  (broke in 3 lanes). ⚠ Deferred to round 2 (in flight): brush's `wall_coastal` (its n=1 open-sea face is *weaker*
  evidence than the scrub face just refused — an inconsistent bar), a canyon 2nd wall constant (43 tris, too thin),
  **topo-16's write-up** (cross-lane defect — its "unrecorded" zones are byte-identical to this round's own strip
  catalog), the **"secondary mains rect"** phenomenon, the **strip PLACEMENT policy** (the real remaining
  dunes-carry blocker — a proven rect is not an authoring recipe), and the **visual modality** (zero offline-eye
  renders ran).
  **★ ROUND 2 DONE same day** (`314f13a`; 5 lanes × 3 lenses, 20/21 agents — **no shipped-code contradiction**,
  round 2 cross-checked shared objects between lanes *before* publishing, exactly what round 1 failed to do):
  **brush SETTLED `False`** — the cross-block-aware adjacency scan (the blind spot every wall figure in this arc
  shared: within-block edges only) was built and run map-wide, adds **zero** new evidence for brush/scrub/dunes
  while proving itself non-null on the desert control (+9/1838 tris); brush and scrub **tie at one open-sea face
  each** and both fail the canyon bar. No family carries an unset `wall_coastal` any more · **topo-16 CLOSED as a
  SEAM-DRESSED ground** — 100.0% zero-residual decomposition into desert mains (36.5%) + both shipped STRIPS
  entries (50.2%+13.3%), independently re-derived and byte-identical at 5dp; its strip choice tracks its real
  neighbour (all 56 desert|dunes-strip tris sit in exactly the 4 of 6 blocks containing dunes); belongs in
  NEITHER table · **a genuinely NEW second desert ground rect** `du=0.85058 dv=-0.11425` (5-block cluster,
  proven-5dp, matching none of 21 catalogued regions; **not** the edge decal despite u-origins 0.85058 vs
  0.85059 — a >0.2 v-gap, a coincidence that cost a round) shipped data-only as
  `grassland.DESERT_MAINS_SECONDARY`, its "geographically isolated" framing STRUCK (block (13,4) is
  PRIMARY-exact and borders the secondary cluster — the rects interleave). **It surfaced as an apparent CONTROL
  FAILURE: read a control failure before you explain it away** · **the OFFLINE EYE ran for the first time in
  this arc's ground-family work** and immediately paid — grass|desert reads as an ordinary hard jigsaw boundary
  with NO visible blend ribbon (placement likely cosmetically free) while **desert|dunes shows a genuine soft
  halo (placement matters)**, which narrows all remaining work to desert|dunes; correction from review: the
  decal's "~47% mainstream" conflated block-INCIDENCE with AREA share (~13% of desert tris) — incidence ≠ extent.
- [ ] **The ecotone strip PLACEMENT policy (desert|dunes)** — **THE ARC'S ACTUAL REMAINING BLOCKER on the dunes
  patch carry**, and all that stands between it and a mint. Depth-alone determinism is FALSIFIED (0.5–3.1%
  purity); the real structure is a locally-alternating small-step **dither** (|Δrow|=1 dominant, negative lag-1
  autocorrelation, adjacent-same-row 9.8% vs a 25.2% shuffled baseline) riding a soft family-relative bias — but
  the recipe is speculative: unimplemented, unrendered, untested. Unexplained: grass|desert's row marginals
  reject uniformity (χ²=11.92), desert|dunes' do not (χ²=1.62). Round 3 (implement + render, scoped to
  desert|dunes) is IN FLIGHT; it terminates at a playtest the agents cannot run.
- [ ] **Screen remaining beach/snow/canyon coastal donors** (6.25) — only (7,17)/(10,17) proven of ~44 beach-bearing
  blocks; the realistic beaches-on-our-islands path now the mint ladder is dead. (Canyon expected near-empty per the
  re-censused wall envelope.)
- [ ] **Resurrect rolling relief for minted islands** (6.0: play 8, feas 5) — every mint since DEAD-RELIEF is
  byte-flat; resurrection notes in this README. Re-key `relief_field` to the same world-coord frame as `fill_y`;
  prove offline before touching shared code (zero-byte-diff acceptances guard it).
- [ ] **Fix minimap player-icon west-bias + document the w_naviGetPos dual regime** (6.0: play 9, leve 3) — likely a
  non-centered RectTransform pivot (WorldHUD.cs:651/733); the pre/post-SC-5990 formula switch is undocumented.
  DLL work — fold into one deliberate engine round.
- [ ] **Playtest a targeted (non-uniform) encounter re-table** (6.0) — one `[[set]] area=N` edit + one F6 check
  closes the last gap on the offline-proven world-encounters feature.
- [ ] **Census and carry a standalone stream/falls part** (5.5) — do any Stream/River/Falls parts sit on lowland
  unattached to a massif? If yes, a genuinely new `world-river` mint verb becomes possible.
- [ ] **Decode unstudied mesh parts: Beach2 (4 blocks), Sea6 (4), the sole Sea4f (12,0), block 219** (5.25) — pure
  read-only UnityPy decode; possible new vocabulary tier.
- [ ] **Scope a real navimap marker slot** (5.25: play 8, feas 3) — given the all-zero navipos discovery, a custom
  location can never draw a pause-map dot without an engine table edit; scope minimal-entry vs repurposing dead
  slot 63 first. DLL round.

### LATER
- [ ] Reconcile the F6 9009 vehicle allow-list vs the 2026-07-08 in-game note (docs or dict — pick one) (4.5)
- [ ] Ensemble-carry rung for scrub/brush/dunes (5.0) — **blocked on the ecotone decode**; also resolve the deployed
  (544,−1248) scrub islet's amputation-stump ends
- [ ] Gulug volcano parts + lava-hazard study (5.0) — prerequisite for any volcano/hazard terrain
- [ ] Mint a second island canvas; re-check the scenery-seal + interior rungs' generality (every proven rung landed
  on the one island-E mint) (5.0)
- [ ] Misc content-decode batch: chocograph destination table, friendly-monster GLOB 194/198 flip timing, airship
  encount 22/23, `m_GetIDArea` bit math (5.25)
- [ ] Small bug-fix batch: the r31 mint 1-tri hole, the confounded Uaho texture probe re-run (mist OFF), self-heal
  fallback point, the stale STRICT SHORE table, the open-ocean gate gap (5.25) — split, don't bundle
- [ ] Extend-feature batch: (6,15) mesa carry at scale, cliff+beach single-cell coast-morph gap, snow/canyon
  ecotones, fuse land-knit seam prototype, s34 sidecar stripping (4.25) — hold for precursors
- [ ] Playtest-verification + apply-recipes batch (4.5) — **violates one-change-per-test as bundled; split it**:
  vehicle-legality on minted terrain, beach-carry onto island E/F, buildings/minimap/chocobo recipes on shipped content
- [ ] Workspace GUI world tab (3.25) — authoring parity with battle/co-op tabs; zero player value

### RESEARCH QUESTIONS
- [ ] **Decode the vehicle topograph masks** (chocobo tiers / gold / airships / Invincible legality unenumerated;
  each dispatcher's vehicle switch undecoded) — settle the study before any F6 allow-list widening.
- [ ] **Can co-op ghosts exist on the overworld at all?** Netsync gates ghosts off at gMode==3 by design; a pure
  WMWorld.cs actor-registration read settles feasibility before any wire work.

### DROPPED
- F6 disc-switch navi-arm (DLL rebuild for a debug-only edge case, resting on a split finding)
- Island-F wall cosmetics (that geometry was reverted — it no longer exists)
- CSV seam for world encounters (no payoff over the byte-proven override path)

### Sequencing laws (from the synthesis)
1. The two trust repairs (wall re-census + doc batch) come **before** anything that cites those numbers again.
2. All DLL-touching items (minimap bias, navimap slot, vehicle masks) = **one deliberate engine round**, not
   piecemeal rebuilds (auto-deploy, no backup).
3. The ecotone/ground-family decode **gates** ensemble-carry and mixed-biome extension — don't schedule those first.
4. Batches that bundle in-game checks must be split per the one-change-per-test law.

---

*Full per-agent evidence: session 2026-07-18 workflow journals (runs `wf_6d85aadf-620` audit, `wf_4eac8404-698`
roadmap). This file is the durable record.*
