# West-Seam Continent — Deploy Plan

> `studies/overworld-topography/west-seam-continent/PLAN.md` — the deploy-ready ladder for the ratified
> west-seam continent (deployed 2026-08-28). Every CLI line below was re-verified against the real
> parsers in this worktree (`ff9mapkit/ff9mapkit/cli.py` at 17c61aa0) — the Aldermarch mistake
> (recorded-but-unrunnable commands) is not repeated here. All `py -m ff9mapkit` lines run from
> `ff9mapkit/`. One rung per in-game test; the owner's playtest is the verdict on every rung.

## What is deployed (R1, playtest pending)

```
py -m ff9mapkit world-island --mod-folder FF9CustomMap-world --center 1520,-464 --radius 144 --lobes 3 --seed 9 --flat
```
26 `Block[x][y] Terrain.ff9mesh` overrides, wrapped cols {21,22,23,0,1} × rows 4-9, straddling the
x-seam; 64,315 u² (1.57× Aldermarch), flat y=3.2; coastnav land-anywhere (beach=4011, standoff=969,
keel=1578). Offline: disc parity 234/234, seam welds set-identical rows 4-9, 97/97 Terrain walks
through the seam. 4 WARN-default texture/sea rows pending in-game review on the west coast — blocks
(21,5)(21,6)(21,7)(21,8)(22,4)(22,5).

⚠ **The continent is encounter-LIVE today**: minted ground defaults to area 0
(`world/interior.py:1348`), and zone 0 carries topo-0 records — open grass fights Pythons until R3.
Known; do not diagnose it as a defect during R1.

## Owner input needed

1. **The continent's NAME** — goes on nameplate case 62 (locId 61, explored bit w98 bit 13) and into
   `marker_renames.toml`. Placeholder until supplied: `'  ?  '` (the stock mystery-spot class).
2. **The first landing point's plate/apron** — default recommendation: **East Bay (80, -444), block
   (1,6)** — the best-sheltered bay on the continent (land fraction 0.85 / water window 66°), and the
   only shortlisted apron structurally immune to later relief (see the beacon-blanking law, R2).
   Alternatives measured: N notch (1516,-328), NW notch (1412,-388), S seam (1496,-560).
3. **The second massif** — uaho (default, R5) or comp20 (`--donor 12,16-17 --near 1476,-376 --reach 44`).
   Crag does **not** fit as a second massif anywhere (measured: every seat with clearance ≥51.7 violates
   either the horseshoe's mutual margin or the seam law); crag is only an *instead-of-horseshoe* option.
4. **Optional third hill** — no r18 hill fits the remaining margins; a smaller r13/h3.6 hill (the s25.3
   bench precedent) fits the south tail if wanted.
5. **Ferry pairings for extra berths (R8, optional)** — proposed: S-seam berth ↔ Ashvale (~614u,
   the wrap-meridian showpiece lane), SW berth ↔ Grimhorn (or Tidefall for spread).

## Laws that bound every siting decision (verified file:line)

- **THE SEAM LAW — no relief verb may span cols 23|0.** `read_deployed_blocks` hard-refuses any
  read window crossing x=0/1536 (`world/interior.py:178-186`, explicit: "seam-aware interior relief
  is a follow-on rung"); the carve core rect additionally demands deployed overrides on every block
  of `CX ± (r_rim + 8.5)` (`interior.py:1378-1401`, SCAN_BAND = MTN_CLEAR 2.5 + 4 = 6.5). Corollary:
  every massif/forest/hill seat plus its full apron (foot + MTN_GBLEND 12 + band 6.5,
  `interior.py:90`) must end ≥8u short of the seam column so no x=0/1536 weld vert lifts (the taper
  fires only at borders facing absent blocks, `interior.py:1390-1395`) — the set-identical seam weld
  survives only if seam-edge verts stay byte-identical. **All massifs live on the west span (cols
  21-23); the east clump (cols 0-1) takes only small-window forests.** Toroidalizing the interior
  verbs is a named study arc, not a rung.
- **Relief is CARRY, not synthesis.** Donor catalog verified against `world/data/donors.toml`:
  uaho `0,0` (aperture=object) · crag `10,5-6` · horseshoe `5-6,15-16` (aperture=ensemble) ·
  comp20 `12,16-17` — all `status = qualified`. The README:1277-1287 ensemble caveat applies only to
  the OLD bench at (18-20,17-19); a fresh `world-mountain` carve ships the ensemble parts + `Donor.txt`
  itself (`cli.py:4891-4894`, `interior.py:2509-2554`).
- **THE BEACON-BLANKING LAW.** An ensemble carve replaces Object/Falls/River/RiverJoint on **every
  span block** with carried content or a hidden blank — a prior beacon there is erased with only a
  WARN (`interior.py:2532-2540`). The horseshoe's span is cols 21-23 × rows 6-8. The East Bay landing
  (1,6) is outside every lawful massif span by construction of the seam law.
- **AREA bits, two dialects.** The mountain carve STRIPS donor dispatch bits — carried rock lands
  area=0/event=0, no restamp needed (`interior.py:1343-1351`). The forest carve carries IDALL
  **verbatim** — donor (15,15) imports AREA 7 = zone 2, Lindblum fauna (`interior.py:672-677`), so
  every canopy carry needs the restamp (THE DONOR-AREA LAW, southern-ring REVERT.md §25.3).
- **Encounters are AREA-table driven, never topograph** (falsified in-game twice;
  `world/encounter.py:21-42`: the only terrain clause on the ordinary path is `!= 52`). Safe roads
  are AUTHORED table holes: area 14 → zone 6, whose only records are topos {10,36} — a hole for
  topo 0/37 thanks to the s60 engine patch (already in the shipped bundle). Consuming a stock zone
  is free; only editing records collides. `world-encounter-frequency` is the real rate lever and is
  **not touched** here (its zone flag is `--zone`, repeatable — and any zone-0 edit would leak to
  Alexandria's stock tiles).
- **Nameplates: virgin band 61-64 first** (no stock-byte surgery, no splice needed —
  `world/entrance.py:838-855`; a case >64 auto-deploys the extended band, `:913-919`). Consumed per
  `southern-ring/marker_renames.toml`: 53 network label, 61 Lamplight, 65-68 quays, 69 the boat.
  **Next free: case 62** (then 63-64, then the splice; ceiling 93). Never 52 (quicksand
  `Battle(0,144)`), never 91-93 (vehicle HUD).
- **THE INVISIBLE-DOOR LESSON**: berth layouts must *read* — beacon kit with south-face doorway,
  hull ≥1u off the trigger rect, hull never crossing a block seam, `--building-idall 4078` on
  donor-backed cells (`rebuild_quay_marker.sh`, `mint_quay_beacon.py` SITES + its 29 gates).
- **Gates are regression harnesses, not oracles; the defect follows the authorship.** This ladder
  ships proven verbs only; the one new script (R3) is an R4b-class precedent clone with its own
  invariant probe.

## The ladder

Deploy tree snapshots: before every terrain-writing rung, copy
`<game>\FF9CustomMap-world\FF9_Data\WorldMap\Disc1\0_1` and `...\Disc4\0_1` to
`C:\gd\Dream-World-IX\backups\west-seam-continent\<rung>-pre.<timestamp>\` (MAIN-repo backups — a
worktree-parked backup dies with the worktree). Revert = restore the copy. `world-ledger
--mod-folder FF9CustomMap-world --drift` reconciles what actually landed.

---

### R1 — THE BASE CONTINENT ★★ PLAYTEST CONFIRMED (owner, 2026-08-28: "good")

**Verb lines:** none (deployed; command recorded above, all flags verified `cli.py:9127-9213`).

**Owner playtests:** seam walk at three latitudes (no visible seam; position-readout jump only) ·
boat lap through the seam · land anywhere on the coast · **eyeball the 4 WARN texture/sea rows on
the west coast** — this verdict GATES R4-R7 (five of the later deploys rewrite Terrain in WARN
blocks; a west-coast re-tile after relief would break one-change-per-test attribution) · expect
Pythons on the grass (known, removed at R3).

**Revert:** delete the 26 Terrain overrides + their Disc4 mirrors + the coastnav-stamped sea
overrides (the mint is additive over open ocean; the MOD-OVERWRITE GATE protected everything else).

---

### R2 — THE LANDING + THE NAME (east bay; WARN-independent)

> **★★ PLAYTEST CONFIRMED 2026-08-28 (owner, cold start): all seven checks good** — ferry row,
> voyage, west-facing arrival, "?"→Confirm→interior, walk-out, on-foot state + the Farshore plate +
> the world map (the owner's "might still be offset" hunch was MEASURED: both spans'
> drawn pixels sit inside their expected engine-projection rects to the pixel — west X[1078,1219]
> vs expected [1073,1219], east X[51,132] vs [51,148]; no offset. The odd look is the continent
> correctly SPLIT across the chart's left/right edges — torus behavior, like the marker jump), save/reload.
> Original deploy note: Execution
> errata vs the recipe below, found by the drafting pass and applied: (1) the WORLD11 departure
> director's port table is positional with LAST-ROW DEFAULT, so `depart_code 5` had to land in the
> director BEFORE the hall — `rung3c_origin_departure.py` gained the port-5 rows (anchor tag 67;
> 65/66 are HIDE/SHOW) and was `--deploy`ed first; the East Bay arrival lane was probed all-wet,
> with the eye at (134.5,−448) because the stock (2,6) sea sheet has a margin hole at the idiom's
> −452. (2) The ferry row was folded into the ONE 6601 deploy (not a pre-flight re-deploy plus a
> second). (3) The bare `world-entrance` ran dry-run only; `rebuild_quay_marker.sh eastbay` was
> the single real entrance+beacon deploy. (4) THE ONE LANDING POINT is **(68,−444) face 64**
> (west/inland, the Larkspur idiom) — ferry row, director shore snap, and the 6603 walk-out all
> land there. (5) The old `probe_quay_beacon.py` dies on a July backup path for Ashvale before
> reaching eastbay — East Bay was byte-verified directly (beacon 42,140 B on both discs
> identical; 'Farshore' in the deployed 68.mes; 6601+6603 + both MessageFiles registered).

The player route: New Game/hub → Lantern Hall → ferry → the continent's shore. One relaunch.

**Pre-flight (mandatory, the install is shared by 18+ sessions):**
- Re-grep BOTH live DictionaryPatches at deploy time. Verified 2026-08-28:
  `FF9CustomMap-world` = {4600, 6602}, `FF9CustomMap` = {4010-4013, 30416, 30801} — **6603 is clean,
  and 6601 (the Lantern Hall) is registered in NEITHER folder**. Re-deploy the hall first from
  `studies/overworld-topography/southern-ring/lantern-hall.field.toml` (`--id 6601`) or the ferry
  row has no home.

**Verb lines (all RUNNABLE; entrance flags verified `cli.py:9402-9518`, deploy flags
`tools/deploy_field.py:61-68`):**
```
# 1. the destination interior (BG-borrow, the Lamplight-6602 pattern; own text block = its own id)
py ../tools/deploy_field.py <west-seam-continent/landing.field.toml> --id 6603 --mod-folder FF9CustomMap-world

# 2. the entrance: virgin case 62, cell of the East Bay apron (80,-444) -> cell (2,13)
py -m ff9mapkit world-entrance --mod-folder FF9CustomMap-world --cell 2 13 --field-direct 6603 \
    --nameplate-name "<OWNER NAME>" --nameplate-case 62 \
    --trigger-at 80 -444 --trigger-radius 3.0 --no-tile-area --dry-run   # then without --dry-run

# 3. the beacon: add a sixth Site row to mint_quay_beacon.py SITES + a case arm to
#    rebuild_quay_marker.sh (FIELD=6603 NAME=<owner> CASE=62), then:
sh studies/overworld-topography/southern-ring/rebuild_quay_marker.sh <newsite>

# 4. the ferry row: one [[ferry]] row on the 6601 Purser (decline arm stays LAST), arrive = the
#    landing shore; redeploy 6601. The kit emits key-35 + both position blocks (worldexit idiom).

# 5. the map + the name registry
py -m ff9mapkit world-minimap --mod-folder FF9CustomMap-world        # note Memoria.ini FolderNames AND Priorities order
py -m ff9mapkit world-rename-markers ../studies/overworld-topography/southern-ring/marker_renames.toml --mod-folder FF9CustomMap-world
```
(Add the case-62 entry to `marker_renames.toml` — the registry is merge-idempotent; never rebuild it.)

**Owner playtests (COLD-START — fresh New Game, per THE WARM-MIRROR MASK):** hub → hall → ferry →
shore facing inland → walk to the beacon, doorway facing you → "?" plate → Confirm → interior →
walk out → `~ World` reads the on-foot state → the name registers after first visit → save/reload
closes the loop.

**Revert:** `revert_deploy_6603.py` for the field · `world-entrance` writes per-dispatcher `.eb`
backups (restore them) · delete the (1,6) Object override + restore the Terrain snapshot for the
event tiles · drop the ferry row and redeploy 6601 · the marker rename is additive (remove the
entry, re-run).

---

### R3 — THE SAFE ROAD (the area-policy stamp; hot, WARN-independent)

> **★★ PLAYTEST CONFIRMED 2026-08-28 (owner): open grass silent everywhere, the stock control
> spot normal.** THE TABLE IS THE LAW, proven on the continent. Deploy note:
> `stamp_area_policy.py` + `probe_area14.py` shipped beside this plan: 50,964 open-ground verts →
> area 14 across all 52 files (both discs), 36 event verts (the R2 entrance) byte-identical,
> canopy rule armed for R6, idempotent (second run: 0), every write ledgered, pre-stamp backup in
> `backups/west-seam-continent/`. Probe: ALL CHECKS PASS (a–e).

**The one new script of this plan** — an R4b-class precedent clone (southern-ring REVERT.md §26.2;
deliberately not a kit verb yet): `west-seam-continent/stamp_area_policy.py`. Rule, per Terrain
vert-tangent on the continent's 26 blocks × BOTH discs (52 files), byte-preserving everything else:

- `event == 0 AND topo == 37` → `area := 0` (canopy fauna: zone 0 = Python/Goblin/Mu — replaces any
  donor-imported area; a no-op until R6 exists)
- `event == 0 AND topo ∉ {36,37,38}` → `area := 14` (zone 6's topo-0 hole = no encounters)
- everything else (event tiles included — the R2 entrance survives by construction) → untouched

Verifier: an invariant probe cloned from `southern-ring/probe_r3/probe_area14_stamp.py` (checks a-e
+ full disc parity). **This script is idempotent and scoped, and is RE-RUN after every later
terrain-writing rung** (R4-R7 re-emit whole blocks; new zip/apron tris mint at kit-default area 0
and would leak encounters).

**Owner playtests:** several minutes walking open grass anywhere on the continent — ZERO
encounters; one stock plains spot (Alexandria region) unchanged as the control.

**Revert:** restore the pre-rung snapshot (area bits only — the snapshot diff must show nothing else).

---

### R4 — THE FIRST MASSIF: the horseshoe ensemble (west span; GATED on the R1 WARN verdict)

> **DEFECT ROUND (owner rim walk): the (1418–1433, −469..−485) arc showed a grassy knoll against
> the mountain with no grass–mountain transition; the rest of the perimeter and the plateau passed.**
> Byte forensics: that arc is the donor's HIGH-FOOT arc (foot 4.3–5.1 vs the 3.2 plateau) flanked by
> the ring's deepest dip (1.4); the apron faithfully lifted grass to the rim — the knoll — burying
> the transition. Fix = THE HIGH-FOOT CONFORM (`world-mountain --max-apron-lift 0.75`, see the kit
> CHANGELOG): the apron rises ≤0.75 and 13 boundary columns conformed DOWN to the capped grass
> (bottom wall row stretches, uv kept per the corner-role law; dips untouched per THE FREE-BASE
> LAW). Re-carve take 3: same placement, zipRise 1.88 / zipNyMin 0.66 (both better), junctions
> above cap anywhere: 0; stamp+probe a–e green; seam weld rows 4–9 set-identical; parity 261/261;
> walks 97/97 ×3. **Take 3 REJECTED in the arc re-walk** ("still there"; then "the cliff face is
> basically parallel with the ground and walkable" — the conform's flat shelf). The knoll is the
> donor's mossy LOW-ANGLE flank: at home a forest hides it and its ground rolls (the overhang-context
> class); here it stands bare over flat lawn. Take 4 (broad apron `--gblend 26`, no cap): REJECTED on
> sight — "no new wall, just grass + no transition + 1px seams" (the ramp = S5's off-language class;
> the hairlines = apron T-junction differential lift → fixed on master, THE T-JUNCTION LERP LAW).
> A UV-only ground strip (foot-course paint on flat lawn) also REJECTED ("walkable") and reverted.
> **Take 5 = THE FOOT-COURSE WINDOW** (`world-mountain --foot-course 1415,-489,1440,-462`, new verb
> option, the spur-graft class as a carve option): the arc's rim nodes leave the apron field (the
> lawn stays flat) and the zip annulus there emits as blocked topo-49 rock — r10 exemplar tiles
> harvested from the donor's own foot course, fringe pinned at the lawn line, one full tile per tri
> in both axes, continuous segment-arc u (nearest-vertex snap froze u to one texel column —
> offline-eye-caught + measured), |dev| v so FREE-BASE dips shade rock downward. footCourse=14
> fcNyMin=0.60 (~53°); grass-zip envelope cleaner than every prior take (0/143 banks); stamp+probe
> a–e green; parity 306/306; seam weld set-identical; hermetic tests 30 green (2 new).
> Take 5 walked: "still flat" -- the foot course is 1-2u; the FLANK ABOVE is the flat thing
> (measured: 27.7 deg least-squares over 14.5u plan run -- stock walls run ~51 deg median).
> **Take 6 = THE FACE STEEPEN**: `--foot-course` grew an optional PULL (X0,Z0,X1,Z1[,PULL[,TOP]]) --
> a window-scoped, gated exception to ROCK-RIGID: horizontal pull toward the massif centre, full at
> lawn height fading to zero at TOP (lawn+12), applied as a pure function of world position at every
> donor-to-world transform site so rim/hole/zip/welds derive consistently. Fold safety: 12u feather
> on INNER edges only (all-edge feather starved the pull -- a 25u window has no core; outer edges
> face open lawn), pull gradient <= ~0.7/u (down-winding gate finds the ceiling: PULL 8 folds 15
> tris, 6 folds none). Deployed PULL=6: central chord 27.7 -> 45.5 deg, footCourse=17 fcNyMin=0.52,
> all gates green, stamp+probe a-e, parity 306/306, seam weld OK, tests 31 green.
> Take 6 walked: rejected (poorly shaped faces = the rock-rigid law's own failure class; retired).
> THE SHOULDER HEURISTICS study (6-agent census, SHOULDER-HEURISTICS.md) + its addendum then
> corrected the model: the arc was NEVER shallow (55 deg per-tri; every shallow figure was a
> radial-chord instrument error). The real deltas vs the passed north face: the apron bulge + THE
> DOUBLED FRINGE (green tufty r6c4-7 transition course mid-silhouette, lawful only against a
> VISIBLE grass contact -- the bowl terrace above is hidden from the lawn).
> **Take 7 = flat window + THE FRINGE RE-ALIGN**: re-carve with `--foot-course 1415,-489,1440,-462`
> (no pull -- flat lawn to the wall, rock contact course) + `fringe_realign.py` (the 20 r6c4-7 tris
> -> r7c6-9 pale rock, whole-tile translation CLAMPED into the measured PAINTED extent inset 0.75
> texel -- the offline eye caught both gutter classes pre-deploy: grid-edge clamp still lands in
> Moguri's inset transparent margin; the eye itself needed the alpha-aware sampler to tell true
> gutter hits (magenta) from its own edge-bilinear bleed). Ladder now 10 -> 9 -> 7, fringe only at
> the lawn. Stamp+probe a-e green, parity 306/306, seam weld OK.
> Take 7 walked: REJECTED -- (a) the uniform pale r7 course reads as top-to-bottom BANDING (a
> whole-tile stripe is too clean; stock mixes within bands); (b) the base still bad: the minted
> contact course drops steeply to the lawn instead of continuing the face's own slope.
> **THE ARC IS PARKED (owner: wrap up, measure a different way).** Eight takes, eight rejections;
> the full falsification record: SHOULDER-HEURISTICS.md + the ledger below. Standing design
> constraints from the verdicts: (1) THE NO-KINK LAW -- any base/contact course must CONTINUE the
> local face plane's slope to the ground, never chord steeply down; (2) no uniform single-tile
> bands; (3) all prior classes (apron shapes, conform, strips, steepen, re-charts) falsified.
> POST-MORTEM CORRECTED BY THE OWNER (next day): the renderer was never the gap ("the render looks
> like the site in-game") -- the gap was DIMENSIONALITY: judging from one view instead of the 3D
> shape, and authoring the base from the GROUND side (aprons/banks/courses = flat ground stood up
> into rock walls) instead of continuing the mountain's own slope down. Stock mountains climb in a
> specific range; the takes did not. BUILT + FIRST-RUN VERIFIED: `envelope_profile.py` (THE PROFILE
> INSTRUMENT) -- from each rock-grass contact, march horizontally uphill, A1 = envelope angle over
> 0-8u, A2 over 8-16u, A3 over 8-24u, kink = A1-A2. Results: STOCK feet (n=926) A1 p25-p75 =
> 42.3-52.7 deg, floor p05 33.1, kink centered +1.5 (base continues or slightly steepens the face
> -- convex toe, NEVER a splayed skirt); this massif's OWNER-PASSED faces (n=54) A1 p50 49.0 ==
> Daguerreo home (p50 49.5) -- the carry is lawful everywhere untouched; THE FAILED WINDOW (n=7) is
> the massif's ONLY out-of-law zone, in BOTH tails: mid-arc bases 21-36 deg flaring SHALLOWER than
> the 38-42 deg face above (kink -20..-11), window edges 52-56 deg walls over 13 deg near-flat body
> (kink +36..+43 -- flat ground made into a wall). THE GATE FOR ANY NEXT ATTEMPT: every authored
> foot station must satisfy A1 within the local face family's band AND |kink| inside stock's
> p25-p75 (-6..+18) -- i.e. author the base by EXTENDING each local face plane to the lawn; where
> the body above is flat, no wall may exist at all (the contact retreats instead).
> Deployed state left at take 7; reverts: fringe-realign-pre.* (paint), r4-take4-pre.* (any take),
> r4-pre.20260828-103332 (pre-massif host). Original deploy note: All gates CLEAN on
> the dry run and the deploy: **placement (1462,−462) rot 90°** (the scan slid +10,+6 off the
> `--near`), 9 blocks, 713 donor tris + 143 zip + THE ENSEMBLE CARRY (122 Falls/River/RiverJoint/
> Object tris on span (22,7)-(23,8), `Donor.txt` → (5,15)), peak y 30.87, rock rigidity 0.8%,
> census MISS=0. Safe-road stamp re-run (+6,318 verts; the donor's 6 stock canopy-fleck verts
> correctly kept area 0), probe a–e green. **The seam weld survives the carve** — col-23 rows 4-9
> frame sets still set-identical to col 0; walks 97/97 at three latitudes; disc parity clean on
> every real override (the 18 diffs are Disc1-only `.bak` parkings, invisible by design).
> **R5 CONSEQUENCE: re-aim uaho.** The slide shrank the mutual gap to (1488,−392) to ~74.7u vs
> 82.3 required — exactly the pre-registered hazard. Start the R5 `--near` at ~(1492,−380) (d≈87)
> and let the verb's own gates seat it.

Largest donor first — it has the tightest margins and every later seat re-aims around its printed
placement. Seat verified against the measured clearance field: (1452,-468) clear 96.8 vs need 72.3;
span cols 21-23 × rows 6-8, apron edge ≤ ~1531 < 1536 even at full +10u scan slide.

```
py -m ff9mapkit world-mountain --mod-folder FF9CustomMap-world --near 1452,-468 --donor 5-6,15-16 --reach 66 --dry-run
# review the printed placement + gates, then re-run without --dry-run
```
RUNNABLE (`cli.py:9282-9315`; `--donor` rect parse `:4833-4841`; `--near` comma form `:4749-4755`).
`--reach 66` is REQUIRED — the default 96 crosses the seam window (refusal at `interior.py:178`)
— and covers the core rect (half = r_rim 54.3 + 8.5 ≈ 63 < 66). Blanks ensemble parts across the
span (no beacon there; the landing is on the east clump). **Record the printed centre** — R5 re-aims
from it. Re-run `stamp_area_policy.py` after (rock lands area-0 by the dispatch strip; the stamp
covers the new zip/apron tris).

**Owner playtests:** teleport (the CLI prints the point) → face the massif, walk the whole rim,
walk the falls/river aperture — look-but-don't-touch scenery, no walk-through · confirm the west
coast still reads clean (WARN blocks (21,6)(21,7)(21,8) were rewritten).

**Revert:** restore the pre-rung snapshot (Terrain + the span's Object/Falls/River/RiverJoint +
Donor.txt, both discs).

---

### R5 — THE SECOND MASSIF: uaho (owner may swap for comp20)

Seat (1488,-392): clear 76.6 vs need 38; mutual to the horseshoe 84.1 vs 82.3 required — **only
1.8u spare, and each scan slides ±10u**: re-aim `--near` off the horseshoe's R4 printed placement if
the gap shrank; the carve's own placement probes are the oracle.

```
py -m ff9mapkit world-mountain --mod-folder FF9CustomMap-world --near 1488,-392 --donor 0,0 --reach 32 --dry-run
# alternative (owner pick): --donor 12,16-17 --near 1476,-376 --reach 44
```
RUNNABLE; reach 32 covers uaho's core (half ≈ 28.5) and stays inside the seam window. Uaho's
aperture is object-class — no ensemble blanking. Re-run `stamp_area_policy.py`.

**Owner playtests:** rim walk, the alcove reads and is walkable to its measured floor, sightline
between the two massifs from the ground.

**Revert:** restore the pre-rung snapshot.

---

### R6 — THE CANOPY + THE FAUNA (three carries, one fauna playtest)

Safe roads are authored by where the canopy is NOT: canopy in the massifs' flanks and on the clumps,
the coast-to-landmark corridors stay open area-14 ground.

```
py -m ff9mapkit world-forest --mod-folder FF9CustomMap-world --near 52,-480  --reach 34   # SE clump (wrapped col 0-1)
py -m ff9mapkit world-forest --mod-folder FF9CustomMap-world --near 52,-380  --reach 34   # NE clump
py -m ff9mapkit world-forest --mod-folder FF9CustomMap-world --near 1484,-340 --reach 34  # north lobe (WARN block (22,4)/(22,5))
```
All RUNNABLE (`cli.py:9231-9256`; donor defaults to `15,15`, which parses as the required single
`BX,BY` form, `:4765`). `--reach 34` is REQUIRED on all three — the default 96 crosses the seam
window from either side; the east-clump aprons keep ≥21u of seam margin. After EACH carve, `~ →
reload`-walk it briefly; after all three, **run `stamp_area_policy.py`** — this is what executes THE
DONOR-AREA LAW (the carve imported area 7 verbatim, `interior.py:674`; the stamp rewrites topo-37 →
area 0 and re-covers new grass tris) — then re-run the probe, both discs.

**Owner playtests (the fauna verdict, one session):** canopy fights Python/Goblin/Mu at vanilla
cadence (a Ragtime Mouse is stock-lawful garnish) · the open corridors between pockets stay
SILENT — the safe road as level design · walk-in from the perimeter at several points (the carve's
own walk-in simulation gated it offline; the owner's feet are the verdict).

**Revert:** restore the pre-rung snapshot.

---

### R7 — THE HILLS (last: their envelope gates re-validate against the actually-deployed relief)

```
py -m ff9mapkit world-hill --mod-folder FF9CustomMap-world --near 1436,-384
py -m ff9mapkit world-hill --mod-folder FF9CustomMap-world --near 1412,-540
```
RUNNABLE (`cli.py:9258-9280`). Hill has NO `--reach` — the read window is `max(96, radius+10)`
(`cli.py:4800-4801`), so a hill seat needs `wx + 96 < 1536`: 1436 clears by 4u, 1412 by 28u — do not
nudge hill-1 east. Defaults h4.2/r18; hill-2's clearance (26.5 vs need 26.0) is tight — the scan
slides it or refuses; a refusal here is the gates working, not a bug. Re-run `stamp_area_policy.py`.

**Owner playtests:** walk both hills from all sides (no ledges, no snag), the WARN-row coast
still clean ((21,8)/(22,5) rewritten).

**Revert:** restore the pre-rung snapshot.

---

### R8 — EXTRA FERRY BERTHS (optional, owner call)

After relief, so no carve span can blank a beacon. Cases 63-64 (virgin), then the splice. Proposed:
**S-seam berth** apron (1496,-560) blk (23,8) ↔ Ashvale (the ~614u wrap-meridian lane) · **SW
berth** (1428,-560) blk (22,8) ↔ Grimhorn. Same R2 recipe per berth: Site row + `world-entrance`
+ beacon + `[[ferry]]` row + minimap. Ferry-warp needs no sea-lane proof ("sail where block-proven
open, ferry where not", southern-ring DESIGN.md).

---

## Killed, fixed, and deferred (the adversarial record)

**Killed / corrected:**
- **Crag as a second massif** — killed (no lawful seat; measured exhaustively). Instead-of-horseshoe only.
- **Any seat on P1 (1504,-448) or the clump edges of P3/P4** — killed by THE SEAM LAW
  (`interior.py:178-186`); the horseshoe's lawful seat is pinned west at (1452,-468).
- **`world-encounter-frequency --zones 0`** — flag misnamed in the assembly (`--zone`,
  `cli.py:9703`) and the edit itself is banned regardless: zone 0 leaks to stock Alexandria tiles.
  Rate stays stock.
- **Entrance-before-relief for any west-span berth** — killed by THE BEACON-BLANKING LAW
  (`interior.py:2532-2540`); the landing moved to the east clump, where no massif can lawfully sit.
- **"Massifs need an area restamp"** — false; the carve strips dispatch bits (`interior.py:1343-1351`).
  Only the forest carry imports the donor AREA.
- **A dock berth as a true sailing destination (beach-mint)** — no live lane retrofits a beach onto
  an already-deployed minted block (`world-transplant --beach-mint` demands the donor's own beach
  class, `coastmorph.py:4437-4478`; `world-island --beach` is the FALSIFIED ladder mint,
  `cli.py:9185-9187`). Every continent berth is **entrance-only** near-term; geometry at East Bay is
  beach-admissible (2.45u berm drop → ≥3.6u band, inside the width ladder) if the lane is ever built.

**Deferred to named study arcs (NEW mechanism — never a rung here):**
1. **Seam-spanning interior relief** (toroidal interior verbs) — named a follow-on in the refusal
   text itself (`interior.py:184-186`).
2. **Beach retrofit onto minted blocks** (virgin-mint against deployed bytes, the island-B `:pins=`
   pattern) — upgrades East Bay to a class-53 sailing destination.
3. **The area-14 kit-emitter default** (retire `stamp_area_policy.py`) — needs fresh identity
   baselines (REVERT.md §26 deferral stands).
4. **Distinct canopy fauna** (a consumption stamp of another zone's area, or the
   `WorldEncounters.csv` engine seam) — owner call; `world-encounters --config` is a GLOBAL
   discmr.img re-table, confirm-first, relaunch.

**Verification record:** parsers `cli.py:9127-9213` (island), `:9231-9256` (forest), `:9258-9280`
(hill), `:9282-9315` (mountain), `:9402-9518` (entrance), `:9650-9660` (rename-markers),
`:9568-9585` (minimap), `:4749-4841` (point/rect parse); seam refusal `world/interior.py:155-197`;
core-rect law `:1378-1414`; dispatch strip `:1343-1351`; forest verbatim IDALL `:672-677`; ensemble
blanking `:2509-2554`; donors `world/data/donors.toml`; virgin band `world/entrance.py:838-855,
913-919`; encounter mechanism `world/encounter.py:21-42`; beacon kit
`southern-ring/mint_quay_beacon.py` SITES + `rebuild_quay_marker.sh`; case registry
`southern-ring/marker_renames.toml`; live registrations grep-verified 2026-08-28 (6603 clean, 6601
MISSING — R2 pre-flight). Clearances, donor feet, apron shelter, and the WARN-block envelopes are
measured outputs of the three assembly agents' scratch scripts against the deployed bytes; the
verbs' own gates re-measure every one at deploy time — a green plan is not an oracle.
