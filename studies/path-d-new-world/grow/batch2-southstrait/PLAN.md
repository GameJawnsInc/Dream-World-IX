## THE PLAN

**ANCHOR: `--cell 5,10`** — target rect blocks **(5,10)–(7,11)**, world **x[320,512] z[-768,-640]**. Donor rect `(5,15)+3x2` (world x[320,512] z[-1088,-960]) → **pure translation dx = 0, dz = +320** (the donor's x band is *identical* to the site's, so only z moves). `--rot 0 --shift 0,0` ⇒ THE OBJECT POSE LAW satisfied; all six cells host from their own natural sidecar.

**STRAIT: 78.2 u land-to-land** (bench island's southernmost land vertex z = −561.80, measured on the deployed `Block[5..7][8] Terrain`; the carry's land touches its north frame at z = −640.00) = **1.22 blocks**, over **exactly one full prefab-ocean block row (row 9, z −640…−576 = 64 u)**. Constraint (b) met at the minimum. Rows 11/12 were rejected — see the Wind-Shrine finding.

```
cd C:\gd\Dream-World-IX\.claude\worktrees\path-d-rung-6-handoff-e2535a\ff9mapkit

# 1. CARRY  (dry-run first; identical flags minus --dry-run to deploy)
py -m ff9mapkit world-transplant --mod-folder FF9CustomMap-world --cell 5,10 --donor 5,15 --size 3x2 --rot 0 --shift 0,0 --land-margin 0 --disc 1 --target-disc 9 --all-sea-target --dry-run
py -m ff9mapkit world-transplant --mod-folder FF9CustomMap-world --cell 5,10 --donor 5,15 --size 3x2 --rot 0 --shift 0,0 --land-margin 0 --disc 1 --target-disc 9 --all-sea-target

# 2. RIM RETILE  (ONE invocation -- it iterates to its own fixed point internally)
py -m ff9mapkit world-rim-retile --mod-folder FF9CustomMap-world --cells 5-7,10-11 --donor 5,15 --size 3x2 --disc 1 --target-disc 9 --dry-run
py -m ff9mapkit world-rim-retile --mod-folder FF9CustomMap-world --cells 5-7,10-11 --donor 5,15 --size 3x2 --disc 1 --target-disc 9

# 3. COASTNAV  (NOTE: this verb's --cells does NOT accept ranges -- explicit list only)
py -m ff9mapkit world-coastnav --mod-folder FF9CustomMap-world --disc 9 --cells "5,10;6,10;7,10;5,11;6,11;7,11" --policy land-anywhere --dry-run
py -m ff9mapkit world-coastnav --mod-folder FF9CustomMap-world --disc 9 --cells "5,10;6,10;7,10;5,11;6,11;7,11" --policy land-anywhere

# 4. MINIMAP
py -m ff9mapkit world-minimap --mod-folder FF9CustomMap-world --target-disc 9

# 5. OFFLINE EYE
py -m ff9mapkit world-render --disc 9 --mod-folder FF9CustomMap-world --around 416,-704 --radius 96  --out out/grow2_horseshoe
py -m ff9mapkit world-render --disc 9 --mod-folder FF9CustomMap-world --around 416,-620 --radius 128 --out out/grow2_strait
```

Teleports for the playtest: **lowland ring (331.5, −690.5)** (topo 0, y 3.33) · **terrace bowl (386.5, −693.5)** (topo 13, y 16.41) — both are the v4-proven pair carried through the offset, re-grounded offline on the donor bytes.

---

## 1. PRECEDENT — what the horseshoe shipped with

`studies/overworld-topography/README.md` (the "v4 BUILD" block, ~:300-315), in-game proven **first deploy** 2026-07-13:

```
world-transplant --mod-folder FF9CustomMap-world --cell 1,16 --donor 5,15 --size 3x2 --shift 0,0 --land-margin 0
```
"first dry-run CLEAN, zero hand edits; the machinery auto-armed its proven N tongue strips for the two necks. **Deployed 30 files (6 cells × Terrain/Sea3/5/4 + Donor.txt).**" Verdict: *"the falls/river/bridge ensemble renders — THE FREE-RIDE MECHANISM PROVEN; the neck cuts 'look the same as verbatim'."* Teleports recorded: lowland (75.5, −1074.5), terrace bowl (130.5, −1077.5) — i.e. donor-frame (331.5, −1010.5) / (386.5, −1013.5).

**Donor parts per block, from the real bytes** (`world_tris`, disc 1). Carried as overrides = `terrain/sea3/sea4/sea5`; everything else **rides the sidecar prefab** (`transplant.py:3735`, PARTS at `:46` excludes object/river/falls):

| donor | terrain | sea3 | sea4 | sea5 | FREE-RIDE (prefab only) |
|---|---|---|---|---|---|
| (5,15) | 454 | 87 | 100 | 12 | **object 20** · river 1 · riverjoint 4 · **falls 14** |
| (6,15) | 277 | 72 | 226 | 44 | river 9 |
| (7,15) | 41 | 145 | 222 | 130 | — |
| (5,16) | 287 | 43 | 253 | 26 | **object 47** · river 2 · riverjoint 4 · **falls 6** |
| (6,16) | 424 | 72 | 93 | 46 | **object 8** · river 7 |
| (7,16) | 212 | 147 | 217 | 36 | — |

**No beach1 / sea1 / sea2 anywhere** — a pure all-cliff coast, exactly as the README says. Objects: three cells, 75 tris total, combined bbox donor x 370.7–388.4, y 15.2–29.4, z −1032…−1020 → **at anchor (5,10): x 370.7–388.4, z −712…−700**. The donor is the **Daguerreo** massif (navipos loc 39 = (380.25, −1025.5), dead centre of (5,16)'s object).

---

## 2. PLACEMENT — verified, not assumed

**"Unrotated + unshifted" in code.** `transplant.py:3764-3781`:
```python
identity = (rtarget == disc and nrot == 0 and sh_x == 0.0 and sh_z == 0.0 and (bx+i, by+j) == (dbx+nat[0], dby+nat[1]))
obj_ok = not obj_by_cell[nat]
if not obj_ok and nrot == 0 and sh_x == 0.0 and sh_z == 0.0:
    okeys = {...object verts...}
    touched = {...DropTris keys...} | {...VertexDisplace/SeaBump moves...}
    obj_ok = not (okeys & touched)
```
`identity` is **False** for us (`rtarget=9 ≠ disc=1`), so the pose test is the live branch: `nrot==0` (from `--rot 0`), `sh_x==sh_z==0.0` (from `--shift 0,0` — **not** `auto`, which would re-centre the land and break the law), and `tweaks == []` because we pass no `--grow-cut*`, no morph, no `--ground`, no `--excise` (`cli.py:4307` `build_grow_tweaks` returns empty). A pure block translation therefore qualifies. **Do not add `--shift auto`.**

**Emitted content stays inside the rect** — proven by the dry run's `GATE bounds: x=[0,192] z=[-128,0]` (region-local = exactly 3×2 blocks). The `--strips auto` tongue (N) and coverage strips (E,S,W) are gathered for the shift window and then clipped away at shift 0,0 (`transplant.py:~3695` clamps `i∈[0,tw)`, `j∈[0,th)`).

**Re-survey (today, 13:34 EDT).** `FF9CustomMap-world/FF9_Data/WorldMap/Disc9/0_1/` holds **59 overridden blocks** — unchanged from this session's earlier `canvas_survey.json`. Rows r9–r14 contain **zero** `Block[5|6|7][*]` files; blocks x5-7 × z9-14 are free. `FF9CustomMap` has **no** `WorldMap` tree at all, so no stacked shadow. Bench island = (5,7),(6,7),(7,7),(5,8),(6,8),(7,8).

**Why not z=11 or z=12** — see hazard 3d. z=10 is the only anchor with zero contact with the hardcoded Wind-Shrine SE disc, and it also gives the *tightest* strait, which is what a "strait" wants. No 1-block stretch is needed: 3×2 fits inside x5-7/z10-13 with room to spare (rows 12-13 stay free for a future grow).

---

## 3. HAZARDS

### a) PREFAB-PARTS GATE + GHOST SIDECAR — proven by dry run, not argued

```
cell 5,10: donor prefab (5, 15)   cell 6,10: donor prefab (6, 15)   cell 7,10: donor prefab (7, 15)
cell 5,11: donor prefab (5, 16)   cell 6,11: donor prefab (6, 16)   cell 7,11: donor prefab (7, 16)
GATE object-anchor[5,15]: x=[370.711,380.445] z=[-1024,-1020] moved=False -> ok
GATE object-anchor[5,16]: x=[374.766,384]     z=[-1032,-1024] moved=False -> ok
GATE object-anchor[6,16]: x=[384,388.355]     z=[-1026.38,-1024] moved=False -> ok
GATE prefab-parts: bad=[] -> ok
GATE effective-prefab[*]: armed=False bound=[sea3,sea4,sea5,terrain] unbindable=[] -> ok
```
**Every cell takes its NATURAL donor.** No substitute is ever reached, so no object-bearing prefab is ever hosted by a foreign cell — the 2026-08-04 ghost class (`LATTICE-FILL-PREDICTION.md`, the "rocky part in the middle of the ocean") cannot occur. The three object-bearing donors host only their own translated cells.

**Does the bridge render?** Yes. `WMWorld.cs:589` `if (prefab.ObjectForm1) RegisterBlockComponent(block, prefab.ObjectForm1, true, false);` — the divert-loaded sidecar prefab's Object is registered with its renderer live. The *stock* Daguerreo site additionally runs `WMWorld.cs:703 if (block.Number == 389 …)`, which **disables the block's own Object renderer** and substitutes `EmbeddedAsset/WorldMap_Local/Prefabs/Block[5][16] Object`. Our targets are Number 245/269, not 389, and `SuppressStockLandmarks` is **true** in s75 BLANK mode (`WorldDiscSpike.cs:95`: `Engaged && !CloneStockWorld`), so that case is dead map-wide on 9013. ⇒ what renders at the target is the **block prefab's own** Object mesh — the same thing v4 rendered at (1,16) (Number 385) and the owner accepted. Same for River/RiverJoint/Falls.

### b) EVENT / AREA bits

**Terrain + beach1: ZERO event-armed tris across all six donor blocks** (confirms the README's "quest-clean by construction").

**But the OBJECT mesh is not clean — a finding the earlier census missed.** `Block[5][16] Object` carries **8 tris with `event=1`** (IDALL 28882 = ev 1 / area 48 / **topo 52**), centroids x 380.42–383.09, z −1024.40…−1025.99, y 16.41 — the real **Daguerreo door tile**. This matters because Object is scanned **first** in the form-1 walkmesh order (`placement.py:16-18`, `REGISTRATION_ORDER`) and topo 52 ∈ `WALK_OK`, so a player standing on it fires `ff9.WorldEvent` (`ff9.cs:5345-5352` → `:2231`).

Post-translation cell tags (`0x8000 | (z<<8 & 0x3F00) | (x<<2 & 0xFC) | id`):

| anchor | cell | tag |
|---|---|---|
| (5,10) | (11, 22) | **0x962D** |
| (5,11) | (11, 24) | 0x982D |
| (5,12) | (11, 26) | 0x9A2D |

**Cross-check against the LIVE deployed `EVT_WORLD_WORLD13.eb.bytes`: 47 entry-0 funcs, 43 with cell tags — cell_x 27–43 / cell_z 21–35 (41 inherited) plus (13,17,1) `0x9135` and (4,35,1) `0xA311` (ours). `(11,22)` is NOT among them.** `EventEngine.Request` (`EventEngine.cs:339`) does `GetIP(...)`, and on `nil` never calls — a clean no-op, no log, no throw. **Verdict: harmless.** Two consequences worth carrying forward: (i) when batch 2's gateway is minted, **do not** mint tag `0x962D`/cell (11,22) for something else; (ii) conversely this is a free, stock-authored, reachable "walk-here" tile sitting on a real cave mouth at bowl height — a lawful native entrance seat if the gateway wants one (world x ≈ 380–383, z ≈ −704…−706).

**Encounter AREA bits.** ⚠ **CORRECTED 2026-08-27 — the "encounters gate on topograph 36-38" premise below is FALSE.** `ff9.cs:4255` is GET-sysvar case 205, whose only consumer in every dispatcher is the RAGTIME MOUSE (`Battle(0,941/942)`); ordinary encounters run through `ProcessEncount` (`EventEngine.ProcessEvents.cs:490`) + a per-ZONE `ENCRATE` ladder and have **no topograph 36-38 clause** (falsified in-game 2026-07-26 on topograph 16/41). Read the "encounter-eligible" column below as "Ragtime-Mouse-eligible"; real eligibility is whether the tile's `zone × topograph × fog` triple has a table record. The table is picked by `zone = w_worldAreaZone[m_GetIDArea(...)]` (`ff9.cs:4263`, `:9237`, table at `:1348`). Cross-tab of the carry's land:

| topo | areas → zones | encounter-eligible |
|---|---|---|
| 0 | 48→**18** ×408, 50→**18** ×104 | no |
| 13 | 48→18 ×121 | no |
| 20 | 45→**17** ×12 | no |
| **37** | 48→**18** ×89, 50→**18** ×38 | **YES** |
| 49 / 58 / 59 | 48→18, 0→0 | no (walls) |

So **the only encounter-eligible ground is the topo-37 forest patch** — 381 verts, donor x 387.6–482.2, z −1081.9…−1047.4 → **target x 387.6–482.2, z −761.9…−727.4**, y 3.4–7.7 — and it selects **zone 18**, i.e. the real Daguerreo/Forgotten-Continent set (`w_worldZoneInfo` slice 192-205). This is *lawful* — verbatim land keeping its verbatim encounters — but that zone is late-game country. Note `SuppressMist=true` on a synthetic world (`WorldDiscSpike.cs:87`), and `w_frameFog` is **part of the encounter lookup key** (`ff9.cs:9248`), so the fog=0 rows are what will be rolled. **Playtest call:** if a high-level fight on a low-level bench is unwanted, retune with `world-encounters --peaceful` (rate-only, `.eb` immediate, no table work) before shipping.

### c) Wang-carry gate — expected WARN, report-only

Dry run: `incoherent=51 incoherent_deep=51 incoherent_shallow=0`. The CLI prints only 6 (`transplant.py:2821` truncates at `incoherent[:6]`); I re-derived the full list:

* **by cell:** (5,10) 9 · (6,10) 10 · (7,10) 18 · (6,11) 3 · (7,11) 11
* **by frame edge:** N 20 · E 12 · S 10 · W 9
* **by reason:** 37 × "sea3 abuts deep" · 14 × "sea5 deepset ≠ edge"

All **deep-class**, zero shallow — precisely the class `world-rim-retile` fixes (the warning text names it). `rimretile.harvest_variants` over the 6 donors returns **15 verbatim sea5 termination variants** (deep-sets 0-3 × r0/r90/r180/r270, only `(2,'r180')` absent), so the "no verbatim vocabulary" refusal cannot fire; a per-quad `uncovered()` refusal is only knowable post-deploy.

**Texture gates: leave `--enforce-texture-gates` ON is SAFE here, and I recommend it.** I ran the dry run with it enforced and all four gates report `status=pass`:
`tex-zero-uv` 0/1695 · `tex-one-window` skipped · `tex-family-rect` `{'grass': 487, 'desert': 12}`, `out_of_region_by_family={}` · `sea-plan` A/B/C all ok (`C_overlap_frac 0.102 < 0.1913`). The documented 2026-08-04 false-positive is on **real desert region carries**; this donor is 487 grass + 12 desert mains and clears the grass calibration the gate was built on. (`orphan-decals` also clean: `checked=0 n_orphans=0`.)

### d) `w_worldLocX/Z` — **ONE HIT, and it decides the anchor**

`ff9.cs:1446-1463`, the 3-entry proximity/SE table, read every frame by `w_worldUpdate` (`ff9.cs:9087-9110`, radius **63 u** → `w_musicSEPlay`), **disc-independent — it fires on 9013 too**:

| entry | world (x, z) | block | in site rect x[320,512] z[-896,-640]? |
|---|---|---|---|
| Cleyra | (895.62, −776.18) | (13,12) | no |
| **Wind Shrine** | **(510.86, −889.92)** | **(7,13)** | **YES** — SE #26, disc reaches x[447.9,573.9] z[−952.9,−826.9] |
| Earth Shrine | (1168.75, −366.64) | (18,5) | no |

Nearest-point distance from each candidate footprint to that anchor:

* **anchor (5,10): 121.9 u — CLEAR** ✅
* anchor (5,11): 57.9 u — **overlaps** (a ~5 u × 64 u sliver of block (7,12)'s south edge sits inside the disc)
* anchor (5,12): 0.0 u — **overlaps heavily** (the anchor is inside block (7,13))

Anchors 11 and 12 would put a phantom wind ambience over the new island's SE corner with no visible cause. **This is the deciding constraint, and it is new** — the earlier `canvas_survey.json` checked only the four `block.Number` special cases, not this table. (`navipos` loc 41 "Oeilvert" at (394.59, −798.23) also falls in the site rect, but it is a cosmetic marker table only — no effect at anchor 10, whose footprint stops at z −768.)

The four `block.Number` specials (219/389/91/115 → blocks (3,9)/(5,16)/(19,3)/(19,4)) touch none of the target blocks, and are suppressed anyway in BLANK mode.

---

## 4. COMMAND SEQUENCE — expected output and refusals

**1. `world-transplant`** — `--all-sea-target` is **mandatory**: real disc-1 has land at every target coord ((5,10) terrain 526, (6,10) 627, (7,10) 375, (5,11) 635, (6,11) 525, (7,11) 532), so without it `transplant.py:3458` refuses with *"target cell (5,10) is a REAL world block ({'terrain': 526, …}) — transplanting onto it would replace real game geometry."*
Expect: `carried: terrain:1695 sea3:566 sea4:1111 sea5:294`; the six `cell x,y: donor prefab (…)` lines above; every gate `ok`, incl. `census: miss=25 inherited=25 introduced=0 samples=3456`, `border-census: holes=0 probed=896`, `weld-audit: pairs=0`, `tjunc: new=0`, `clip-drop: area2=0`, `mod-overwrite: cells=6 redeploys=0 existing=0`; **one `!! WARNING wang-carry` (51 seams)**; then `deployed:` with **30 paths** (6 cells × Terrain/Sea3/Sea4/Sea5 + Donor.txt) and `disc-4 mirror: refused for Disc9 (not a real disc — a synthetic override namespace is deliberately unmirrored)` (`discmirror.py:62,189`) — so `--skip-mirror` is unnecessary.
Refusal names to watch: `NOT CLEAN -- deploy refused (every gate must pass; iterate with --dry-run)`; `GATE mod-overwrite … existing=(x,y) N files donor=…` (another session claimed a cell — re-survey, don't `--allow-mod-overwrite` blindly); `refusing to overwrite <name>: its bytes match no ledger entry` (`mesh.py:370`).

**2. `world-rim-retile`** — ⚠ **correction to the brief: it does NOT need two invocations.** `rimretile.py:392` loops `for _k in range(max_passes)` with `max_passes=6` and breaks at the fixed point; the report prints `passes=[n1, n2, …]`. What *does* repeat is different and load-bearing: **any re-deploy of the transplant regenerates the sea meshes and silently discards the retile — re-run this verb after every `world-transplant` re-run** (`studies/coast-shape-language/LATTICE-FILL-PREDICTION.md:118`). Its `--cells` **does** accept the range form (`cli.py:4155 _parse_cells`).
Expect: `rim-retile: 15 verbatim donor variants, passes=[…] (N quad re-tiles)` / `HARD SEAMS … 37 -> 0` (target) / `wrote N file(s); .prerim backups kept`.
Refusals: `no sea5 termination tiles could be harvested` (impossible here — 15 harvested) · `deep-set(s) [...] have no verbatim donor tile — synthesizing one is what produced the checkerboard` (the only real risk: `(2,'r180')` is the one missing variant) · `repartition gate: geometry changed — not a pure re-shade`.

**3. `world-coastnav`** — ⚠ **this verb's `--cells` parser is NOT `_parse_cells`**: `cli.py:4588` does `int(v) for v in c.split(",")`, so `5-7,10-11` throws `invalid literal for int() with base 10: '5-7'`. Pass the explicit semicolon list. Omit `--mirror-disc` (synthetic namespace). Run it **after** the retile (the retile preserves topo, so either order survives, but last-word-on-topo is cleaner).
Expect: `STAMPED coast navigation on Disc9 (policy land-anywhere) across 6 cell(s)` + per-block part/vert lines + `verts by class: keel-block(56)=… beach-front(53)=… standoff-belt(55)=…` + `originals backed up to …` + `re-enter the world map to apply.`
Watch for `!! NO beach-front (53) anywhere` — that line firing would mean the coast is sail-to-but-not-land-on and the `land-anywhere` intent failed. It should **not** fire: `coastnav.py:363-368`, under `land-anywhere`, `near_low or near_high → BEACH(53)`, and `PRIORITY` (`:80`) puts BEACH above BELT/CLIFF at shared verts. The honest caveat: this donor has **no beach1/sea1/sea2 at all** — a cliff coast with a lowland grass ring at y 2.7–3.6. The 3.5 u `BELT_R` standoff still hugs the wall fronts; whether the disembark lands cleanly on the grass ring is the one genuine playtest question. `cliffs-refuse` is the fallback if the owner changes their mind.
⚠ **Backup-dir trap:** `coastnav.py:300-305` roots `backup_dir` at `Path(__file__).parents[3]/backups/coastnav-disc9-<ts>` — i.e. **inside this worktree**, which vanishes with it ([[project-ff9-worktree-parked-backups]]). Copy that dir to `C:\gd\Dream-World-IX\backups\` the same session.

**4. `world-minimap --target-disc 9`** — re-composites the whole Disc9 tree. Its own help warns the sprite override is **per mod folder, not per disc**, so this overwrites whatever a Disc1 composite wrote in the same folder. RELAUNCH to apply.

**5. `world-render`** — `--disc` already defaults to 9 and `--mod-folder` to `FF9CustomMap-world`; writes 10 PNGs per site (1 ortho + 4 close_* + 4 graze_* + overview). Read them before asking for a playtest.

**Revert path.** A transplant writes only loose files — there is no `revert_deploy` for world overrides (that tool is field-only). Delete:

```
<game>\FF9CustomMap-world\FF9_Data\WorldMap\Disc9\0_1\r10\Block[5|6|7][10] {Terrain,Sea3,Sea4,Sea5}.ff9mesh + Donor.txt
<game>\FF9CustomMap-world\FF9_Data\WorldMap\Disc9\0_1\r11\Block[5|6|7][11] {Terrain,Sea3,Sea4,Sea5}.ff9mesh + Donor.txt
```
(30 files; `mesh.override_relpath(9,bx,by,'0_1',part)`). Removing all 30 returns those cells to true `SeaBlockPrefab` ocean — no other cell references them. Rim-retile leaves `*.ff9mesh.prerim` beside each rewritten sea file (restore = copy back); coastnav leaves `<name>.ff9mesh.disc9` copies in its backup dir. Every write also appends a line to `FF9CustomMap-world/.ff9world.jsonl` (ledger, harmless to leave). No Disc4 cleanup — the mirror is refused for Disc9. Take a pre-deploy snapshot of `r10`/`r11` into `C:\gd\Dream-World-IX\backups\grow2-horseshoe-<ts>\` anyway; the install is shared by 18+ sessions.

**Relaunch/reload:** loose `.ff9mesh` overrides + `Donor.txt` are read at world load — re-enter the world map (or `~ → World → teleport`) is enough for 1-3; `world-minimap` needs a **relaunch**.

---

**Scratch artifacts** (all read-only probes, no writes to the install):
`…\scratchpad\donor_census.py` · `world13_tags.py` · `hazards.py` · `b2_locus.py` · `b2_strait.py` · `b2_wang.py` · `b2_wang2.py`