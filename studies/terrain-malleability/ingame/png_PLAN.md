# In-game plan: the per-cell PNG texture override (README section 7.1, rank 6)

Lane `png` of the terrain-study in-game round. **Not yet run.** Every prediction below was registered (in
`png_session.py`'s docstring and here) before any launch. The scenario is driven by the in-game test harness and
judged numerically: engine log receipts, published heights, and pixel counts of three vivid hue classes.

## 1. The question, and the source answer it tests

The s34 loader can give one block's sub-mesh its own texture. The claim to test (consumption C10, capacity X5/CAP-9)
is that on this install the texture is thrown away for Terrain-class parts and kept for Sea-class parts.

How the texture gets in (the clone path):
- `RegisterBlockComponent` loads `Block[x][y] <child>.ff9mesh` (`WMWorld.cs:823-825`, s34).
- **Only if that mesh override bound** (`:826`), it calls `WorldMeshOverride.TryLoadTexture` (`:835-836`).
- `TryLoadTexture` reads `<mod>/FF9_Data/WorldMap/Disc{d}/0_1/r{y}/Block[x][y] <child>.png` from the highest
  FolderNames folder that has it (`WorldMeshOverride.cs:141-170`). It logs
  `[WorldMeshOverride] loaded texture '<child>' from <path>` (`:160`).
- The call site clones the renderer's material and sets `mainTexture` to the PNG (`WMWorld.cs:839-845`).

How it is thrown away (the clobber):
- `LoadBlock` ends with `block.SetupPreloadedMaterials()` (`WMWorld.cs:808`; `:634` on block 219).
- That call reassigns `renderer.material = MaterialDatabase[gameObject.name]` (`WMBlock.cs:106-111`).
- The database holds a child name only when its texture is found loose on disc (`WMBlock.cs:273-306`), from the
  list `WMBlock.cs:310-326`. The Sea, Beach and River names are commented out of that list (`:328-341`).
- On this install `MoguriMain` ships `worldmap/textures/res(1_24)_terrain.png`, `res(1_24)_objects.png`,
  `worldmap/materials/11_0_192.png` and `11_64_192.png`. It ships none of the Volcano textures.
- `atlas.resolve_atlas_source()` resolves the terrain and object atlases to MoguriMain exactly as the engine does.

Why a Sea texture should survive:
- The sea animation sets `mainTexture` on the **shared** asset materials only. Those are
  `WorldMap/Materials/Sea1..6`, loaded at `WMRenderTextureBank.cs:46-63` and updated in `UpdateSea_*_Render`.
- A cloned per-cell material is never touched, so the PNG should show and stay **static**.
- Sea1-6 and Terrain all render with the `WorldMap/Terrain` shader (consumption census). Its pixel program is
  `_MainTex × (0.40 + 0.60·_DetailTex) × vertex light`, lerped to `unity_FogColor`, with no alpha test.
- So the Sea4 arm is a **positive control on the same shader** for the Terrain arm.

The deployed DLL carries the hook: `Assembly-CSharp.dll` contains the UTF-16 strings `loaded texture '` and
`[ff9tex] `.

## 2. Design

| | cell A (21,1): treatment | cell B (0,13): control |
|---|---|---|
| `Terrain.ff9mesh` | donor `Block[12][10]` Terrain, **float-equal** | same bytes |
| `Sea4.ff9mesh` | donor `Block[12][10]` Sea4, float-equal | same bytes |
| `Terrain.png` | solid magenta (255,0,255,255), 64×64 | none |
| `Sea4.png` | solid red (255,0,0,255) | none |
| `Sea3.png` | solid lime (0,255,0,255), with **no** `Sea3.ff9mesh` | none |

How the two cells are set up:
- Both cells are IsSea, all 8 neighbours are sea, and no live folder has a file in their 3×3.
- B is about 800 u from A, so neither cell appears in the other's frames.
- The Terrain file arms the s34 divert onto `Block[12][10]` (`WMWorld.cs:521-533`).
- So each cell renders the donor's stock islet (29 tris, y 0-3.77) plus its free-riding Sea1, Sea3 and Sea5.
- **Zero geometry authorship.** Each override is the donor's own mesh. `png_prep.py` parses every file back and
  asserts every channel is float-equal to the donor. The cell looks the same with or without the overrides.

Donor first-hit coverage of the cell: Sea4 72.3%, Sea3 17.2%, Sea5 7.0%, Sea1 0.8%. The islet hole is at local
x 23-36, z −19..−32.

The arms:
- **T1**: the Terrain PNG.
- **S4 / S4s**: the Sea4 PNG renders, and stays on across the sea animation.
- **S3**: a PNG with no same-part mesh. This corrects the study's phrase "Sea parts keep it": only a part whose
  mesh is overridden is ever looked up.
- **L0**: bind proof.
- **L1 / R1**: receipts.
- **CTRL**: the classifier on B.

Poses:
- **Stand point**: the centroid of donor lawn tri 18 (topo 0, area 13), local (29.516, −27.384), ground
  **y 3.5456**. It is off the 4 u lattice and off shared edges (the lattice-edge trap).
- World stand points: A (1373.516, −91.384), B (29.516, −859.384).
- **Bearings P1 = 45°, P2 = 225°** (two opposite views), picked by the projection so each frame holds the islet,
  Sea4, Sea3 and Sea5.
- **Face home (32.37, −448.61)** is used instead of the 6603 landing (68, −444). From the landing, the 6603
  entrance tile (event 1) is 8-12 u out on bearings 345°-25°, and the building footprint (topo 59) is 12-14 u out
  on 30°-45°. A `world_face` probe toward P1 could re-enter the field there. FACE_HOME's 40 u disc is all area 14
  (the safe road), walkable, event 0 and flat 3.2 on all 72 bearings (`png_prep.py` step 7, over the live walk list).

Per pose, the scenario does:
1. Teleport to FACE_HOME, then `world_face(bearing)`.
2. Teleport FACE_HOME → A, settle 180 frames, take 3 shots 30 frames apart.
3. Teleport FACE_HOME → B and repeat.

The yaw survives a teleport, so A and B share one pose. Routing through the lawn (y 3.2) means an unbound cell can
never read the islet's 3.546. The teleport re-grounds through `w_movementChrInitSlice`
(`Ff9mkDebugMenu.cs:1851-1852`); sessions 4b and 7 read the new ground after teleport, settle and wait. Nothing
moves on the islets, and encounters need movement.

Then a **world reload** (`world_warp(6603)` → walk out → P1 → A, one shot) tests the re-read.

**The judge** (`png_judge.py`):
- HSV hue classes: magenta 275-325° (S ≥ .40, V ≥ .25); red 340-4° (S ≥ .45, V ≥ .40); lime 100-145° (S ≥ .62, V ≥ .42).
- Counted over the frame minus a player box (560-720 × 360-490 px at 1280×720).
- The no-effect bound is `noise = max(200, 0.05% of the scored pixels)`, which is 450 px at 720p.
- Receipts are parsed from the Memoria.log slice of each world visit (marked on the field before the world loads;
  the log flushes per line, `Memoria.Prime/Log.cs:112`).
- `png_post.py` re-scores the archived frames and log with the same `evaluate()`.

## 3. Registered predictions

| id | check | predicted | counterfactual size |
|---|---|---|---|
| L0 | y at A and B (both poses) | 3.546 ± 0.15 | unbound: ~0 (sea) or 3.2 (lawn kept) |
| L1 | receipts per world load | mesh A{Terrain, Sea4}, B{Terrain, Sea4}, all from FF9CustomMap-lab; texture **exactly A: Terrain, then Sea4**; none for B; **none for Sea3** | — |
| T1 | magenta at A vs B | A ≤ B + noise in all 6 frames: **loaded (L1) but not rendered** | islet = 6.2% (P1) / 8.5% (P2) of the frame, about 56k / 77k px |
| S4 | red at A | ≥ 2% of the frame in all 6 frames, B ≤ noise | projection: 29.3% / 29.8% |
| S4s | red min/max over the 3 frames of a pose | ≥ 0.95 (static) | — |
| ANIM | B lower-half gray change between frames | ≥ 0.3 (the stock sea animates; precondition for S4s) | — |
| S3 | lime at A vs B | A ≤ B + noise | Sea3 detectable 4.7% / 3.8% |
| CTRL | every class at B | ≤ noise in every frame | — |
| R1 | after the reload | L1 repeats (+1 Terrain, +1 Sea4 texture receipt); A y 3.546; red ≥ 2% | — |
| S4m | secondary: red fraction / projected Sea4-detectable | within [0.5, 1.5] | model-dependent |

`$PNG_PHASE=nopng` is an optional **temporal control**: a second launch with the three PNGs deleted. It expects no
texture receipts and every class at A ≤ B + noise.

## 4. Deploy (FF9CustomMap-lab only; the orchestrator performs it)

```
# 0. build (writes only ingame/out/): the lab tree + out/png_prep.json (manifest with sha256)
py studies/terrain-malleability/ingame/png_prep.py

# 1. back up Memoria.ini (same protocol as sessions 4-7), then put the lab FIRST in FolderNames:
#    FolderNames = "FF9CustomMap-lab", "FF9CustomMap", "FF9CustomMap-world", "MoguriMain", "MoguriVideo",
#                  "FF9CustomMap-schema", "FF9CustomMap-msgs"
#    (edit with Edit/Python, never a PowerShell text round trip)

# 2. copy the tree into a FRESH lab folder (fails if one is left over from another lane: clear it first).
#    Python, because the file names contain [ ] (PowerShell Copy-Item would need -LiteralPath):
py -c "import shutil; shutil.copytree(r'C:\gd\Dream-World-IX\studies\terrain-malleability\ingame\out\png_lab\FF9CustomMap-lab', r'C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap-lab')"

# 3. read-only gate: lab first in FolderNames, the 7 files sha256-identical, NOTHING else in the lab, and no other
#    folder holding any file for cells A or B (a lower folder's Sea3.ff9mesh at A would silently arm arm S3)
py studies/terrain-malleability/ingame/png_prep.py --verify-installed      # must print VERIFY OK
```

The 7 files, all under `FF9CustomMap-lab/FF9_Data/WorldMap/Disc1/0_1/`:
- `r1/Block[21][1] Terrain.ff9mesh`
- `r1/Block[21][1] Sea4.ff9mesh`
- `r1/Block[21][1] Terrain.png`
- `r1/Block[21][1] Sea4.png`
- `r1/Block[21][1] Sea3.png`
- `r13/Block[0][13] Terrain.ff9mesh`
- `r13/Block[0][13] Sea4.ff9mesh`

**Relaunch.** A launch is needed only because the lab folder must enter FolderNames, and Memoria.ini is read at
startup. The harness launches fresh anyway. After that, PNG presence and content are re-read on **every world
load**: each `LoadBlock` → `TryLoadTexture` calls `File.Exists` over FolderHighToLow. So a PNG change needs only a
field→world entry, a battle return or a `world_warp`, not a relaunch. R1 shows the per-load re-read. The clobbering
`MaterialDatabase` is process-static (`WMBlock.cs:275`, `:305`).

**Other lanes share the lab.** `cost_` and `veh_` also use (21,1), and `veh_` uses (1,13), B's east neighbour.
Runs are one at a time; step 3 refuses any extra file.

## 5. Run

```
py tools/play.py studies/terrain-malleability/ingame/png_session.py --label terrain-png
py studies/terrain-malleability/ingame/png_post.py .harness-runs/<stamp>-terrain-png
# optional temporal control (second launch): delete the three Block[21][1] *.png from the lab, then
#   PowerShell: $env:PNG_PHASE='nopng'; py tools/play.py studies/terrain-malleability/ingame/png_session.py --label terrain-png-nopng
#   (--verify-installed will then list exactly those three PNGs as missing; that is expected)
# teardown: delete <game>\FF9CustomMap-lab; restore Memoria.ini byte-exact from the backup (compare sha256)
```

Expected duration is about 5-6 minutes: new game and walk out, 2 poses × (face + 2 cells × (2 teleports + 240
frames + 3 shots)), then the reload. `$PNG_RELOAD=0` skips the reload.

## 6. Instrument calibration (offline, done)

- **Camera model** (`png_judge.camera`):
  - Posstat 0/2 is blended by actor height (`ff9.cs:3164-3187`), the FOV is `pers/8 × FieldOfView/44` (`ff9.cs:2676`;
    the install's FieldOfView is 58), and the camera LookAt()s the aim (`:2686-2748`).
  - Against session 7's `vcap-under.png` (the y=6 plane's known outline; the actor was at the `off` point, the loop's
    last teleport), it scores **IoU 0.956 with only the bearing free**, and 0.931 with the FixTypeCam offsets.
- **Shading and fog**: session 7's plane is one atlas texel. Every plane pixel decomposes as `k·texel + b·fog` with
  **RMS 0.42** levels; k is 0.63-0.79, b ≤ 0.22 within 32 u; fog fit `b = −0.236 + 0.0137·dist`.
- **Classifier**:
  - On those measured (k, b), every PNG colour classifies on **100%** of the re-shaded pixels, with zero cross-talk.
  - Detection fails at fog blend 0.60 (magenta), 0.47 (red) and 0.36 (lime).
  - False positives over all 65 archived terrain-session frames: magenta ≤ 11 px, lime 0. Red is over the noise bound
    only on the three session-5 frames showing the Southern Ring boat, which is nowhere near A or B.
  - The first-pass windows hit dark grass as lime and browns as red; they were tightened (recorded in `png_judge.py`).
- **Projection** over the real donor meshes, 24 bearings: Sea4 is 29-41% of the frame, the islet 6-13%, Sea3 0-6.5%.
- **Face home**: the cone check over the live walk list, 72 bearings × 40 u (see section 2).
- **Dry run** (`png_dryrun.py`): the real `do_pose`/`shoot_cell` against the harness FakeGame, with synthetic frames
  from the calibrated model under 6 hypotheses. The predicted world passes everything, and each wrong world fails
  exactly its target:
  - Terrain shows → T1
  - Sea3 shows → S3
  - nothing renders → S4/S4m/S4s
  - red drops in one frame → S4/S4s
  - a Sea3 receipt → the receipt check

  `png_post.py` re-scored a kept dry-run dir identically. Run dirs and json are in `out/`.

## 7. Reading the outcome

| outcome | meaning |
|---|---|
| L1 has a Terrain texture receipt, T1 passes, S4 passes | **C10/CAP-9 confirmed in-game**: the Terrain PNG is loaded and then clobbered. The only step between the clone and the render is stock `SetupPreloadedMaterials`, and S4 proves the clone path renders on the same shader. A per-block Terrain texture needs patch P2. |
| T1 fails (magenta visible) | CAP-9 refuted on this install: per-cell Terrain PNGs work with no patch, and P2 is unnecessary. |
| S4 fails while L1 has the Sea4 texture receipt | the clone path itself does not render. T1 is then **uninformative**: do not call the clobber proven. |
| S4 passes, S4s fails | the bank reaches the clone after all (contradicts `WMRenderTextureBank.cs`). Look at the frames. |
| S3 passes, with no Sea3 receipt | a PNG without a same-part mesh override is dead; free riders are never textured. |
| L0 fails at both cells | the divert did not arm, or the teleport kept height (memory law 5). Read the state ring before any pixel verdict. |
| CTRL fails | a HUD or world element carries a vivid class; re-score with a mask in `png_post.py` before judging. |

## 8. Per-part predictions (the general rule on this Moguri install)

| part | PNG read? | rendered? | why |
|---|---|---|---|
| Terrain, Object (host has a stock Object) | yes, with a receipt | **no**, clobbered | MaterialDatabase has them (Moguri loose atlases) |
| Terrain2, Object2 (switchable cells, Form 2) | yes | **no** | same entries, `WMBlock.cs:313`, `:315` |
| Falls, Stream | yes | **no** | Moguri ships `11_0_192.png` / `11_64_192.png` (`WMBlock.cs:316-317`) |
| bare-block Object (`RegisterBareObjectOverride`) | **never** (no `TryLoadTexture` call, `WMWorld.cs:868-884`) | no | the atlas comes via SetupPreloadedMaterials |
| Sea1-6, Sea3_2/4_2/5_2, Beach1/2, River, RiverJoint, with a same-part mesh | yes | **yes, static** | not in the database; the bank animates only the shared material |
| any part with a PNG but **no** same-part `.ff9mesh` (a free rider) | **never** | no | `TryLoadTexture` sits inside `if (ff9Override != null)` |
| VolcanoCrater1/2, VolcanoLava1/2 | yes | **yes, static** (predicted) | Moguri ships no `0_4_0_*` / `1_4_0_*` loose texture, so no database entry; the clone replaces the RenderTexture reference |

Tested here: Terrain (T1), Sea4 (S4, S4s), and the free-rider Sea3 (S3). The other rows are source-derived.

## 9. Risks

- The camera model was calibrated on one frame whose camera may not have settled. S4m is secondary only, and the
  primary thresholds (2% vs a 29% projection; 450 px vs 38-77k px counterfactuals) leave wide margins.
- T1's inference rests on S4 passing in the same run (section 7).
- HUD elements are not masked. CTRL would expose one, and B carries the same HUD.
- The fog fit is extrapolated past 32 u; near-field pixels dominate every arm.
- `world_face` might not converge within 6°. There is one recover-and-retry per pose; A and B always share a yaw.
- A battle is not expected: probes run on area 14 (the safe road), and no movement happens on the area-13 islets.
  The recover idiom from session 1b is present.

## 10. Files

- `png_judge.py`: constants, classifier, receipts, camera model, renderer, `evaluate()`.
- `png_prep.py`: build, calibrations, projection, cone check, `--verify-installed`.
- `png_session.py`: the scenario.
- `png_post.py`: offline re-score.
- `png_dryrun.py`: FakeGame dry run.

Outputs (gitignored):
- `out/png_lab/FF9CustomMap-lab/`
- `out/png_prep.json`
- `out/png_dryrun.json`
- `out/png_dryrun_<hypothesis>/` (only with `PNG_DRY_KEEP`)

No game bytes are in the repo: the meshes and atlas samples live only in `out/`.
