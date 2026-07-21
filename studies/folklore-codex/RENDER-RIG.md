# s46 — THE RENDER RIG (the Folklore display window)

> **ROUND 1 PLAYTEST (2026-07-21): THE MECHANISM IS ★ PROVEN — all four §2 checks passed** (creature
> visible + framed in the pane · clean open/close + L1/R1 + owned↔locked · the field-walk + battle leak
> snaps clean · world-map codex opens). "Not bad, needs some polish" + two findings, both shipped as
> **ROUND 2** (built + deployed same day, ★ playtest pending):
> 1. **Facing** — the yaw-180 guess showed the creature's BACK; round 2 ships yaw **0** (the viewer's
>    own default).
> 2. **The hard-edged black box under the text** — the rung-1 opaque default; round 2 pulls the rung-5
>    TRANSPARENCY probe forward: `backgroundColor (0,0,0,0)` — the field look's Unlit/Transparent
>    Cutout writes clean 0/1 alpha (no PSX battle shader in this path) and UITexture's default
>    Unlit/Transparent Colored alpha-blends, so the creature should composite straight onto the pane
>    sheet. RETREAT LEVER: `Color.black` restores the opaque box.
> 3. **The census log CAUGHT A REAL LATENT BUG** — measured pane depths: Shadow 3 / **Body sheet 4** /
>    body label 6 / Border 8 / frame Caption 9. Round 1's `textDepth−2` "safety margin" = **4, an
>    EXACT TIE with the Body sheet** (the precise instability the skeptic feared; it only happened to
>    resolve in our favor). Round 2 ships `textDepth−1` (= 5, the unique free slot). **LAW: a safety
>    margin chosen without the measurement can BE the collision.**
> Ledger stayed clean: awake 4ms · rig mint **7ms** · first frames 21/3/15 — the rig adds nothing to
> the s45 hang budget.
>
> **ROUND 2 PLAYTEST (2026-07-21): transparency ★ WORKS (creature composites onto the pane sheet, no
> box, faces the camera) — but "not really what I had in mind": superimposed text over the model reads
> badly no matter what. User direction: split the right column like the EQUIP screen's right side
> (EQUIPMENT over ABILITY) — "can't use the exact same setup... but it proves the primitives."
>
> **ROUND 3 — THE EQUIP-SENTENCE SPLIT (built + deployed same day, ★ look-check pending):** two
> stacked bordered windows via the file's own `BuildFramedPane` (the ControlPanel/GenericInfoPanel
> recipe — NOT synthy, both windows are the stock skin): TOP 780×500 @ (410,+150) = the PORTRAIT
> window (caption = entry name, same label binding), 20-unit gap, BOTTOM 780×360 @ (410,−300) = the
> LORE window (caption blank; body label re-seated 680×280). Column footprint byte-preserved
> (+400..−480). Portrait re-seated 680×400 centered in the top window; RT resized to 680×400 (seat ==
> RT, 1:1); NEW FRAMING KNOBS `FolkloreRigCamDist=−700` (was the viewer's −1000) +
> `FolkloreRigAimY=−80` (stage-local aim-up — the round-2 snap showed the low-pivot model sitting
> high with legs clipping the narrow aspect). Depth now derives from the TOP pane's OWN Body sheet
> (+1 → 5) — the round-3 skeptic caught the old min-of-both-labels derivation coupling the bottom
> window's label into a decision local to the top (plus: a blind margin chosen without the census
> WAS the round-1 collision — the instrument law again). Skeptic also RECORDED (not fixed — 16
> approved rounds ship these numbers): the column's right edge (800) exceeds the file's own ±771
> pillarbox-safe comment by 29 units — check once in 4:3/pillarboxed mode someday.
>
> **ROUND 3 PLAYTEST (2026-07-21): ★ "looks good" — RUNG 1 IS CLOSED.** The Equip-sentence split is
> the shipped layout: portrait window (entry name caption, creature filling the frame on the stock
> sheet) over the lore window. Three rounds total, all same-day: mechanism → transparency/facing →
> the split. The patch is `memoria-patches/s46-folklore-render-rig.patch` (1 file, 9 hunks, both
> gates green); merged to master with rung 1 proven.
>
> **RUNGS 2+3 — BUILT + CAPTURED 2026-07-21 (★ playtest pending — the DLL is compiled but NOT
> deployed; FF9 was running, so every compile ran `/p:DWIXNoDeploy=true`; deploy build + RELAUNCH
> needed).** One same-day round, built by a 12-agent Sonnet workflow (`wf_746aa256`: 4 ground lanes →
> design → implement+compile → 3 adversarial skeptics → repair; the kit lane ran as an independent
> parallel chain). What shipped, all in `FolkloreUI.cs` (still the one file, no csproj change):
>
> - **RUNG 2 — THE LIVING IDLE.** Clip discovery re-implements the viewer's GEO-suffix filter against
>   a bare GEO name (`GetAnimationsOfModel` is PRIVATE on the viewer's ModelObject wrapper — not
>   callable); `AddAnimWithAnimatioName` each, first clip plays via the guarded re-Play loop. THREE
>   grounding catches shaped it: (1) **the culling trap was REAL** — the tree has ZERO
>   `Animation.cullingType` precedent and the netsync ghost's huge-bounds hack exists precisely
>   because renderer-level culling lies for offstage models; the rig sets
>   `AnimationCullingType.AlwaysAnimate` + `updateWhenOffscreen=true` (nothing else animates a model
>   no enabled camera ever sees). (2) **The pump is `LateUpdate`, not Update** — legacy Animation
>   samples after Update and before LateUpdate, so a LateUpdate `Render()` captures the CURRENT
>   frame's pose (MovieMaterialProcessor is the in-tree post-sample-pump precedent). (3) **The
>   viewer's own re-Play block is un-gated** — copied verbatim it would spam `Play("")` warnings
>   per-frame on a zero-clip model; ours guards the empty list (static bind pose, still displayed).
> - **RUNG 3 — THE REGISTRY WIRE + AUTO-FRAMING.** `Entry.Display` finally read:
>   `ResolveFolkloreDisplay` (scheme `model:` or colon-less shorthand; all-digits →
>   `FF9BattleDB.GEO.TryGetValue` ONLY — the indexer THROWS on a miss; else `GetGEOID != -1`;
>   `GEO_SUB_W0` refused — needs lights, rung 5). The monolithic mint split at the seam the plan
>   named: per-VISIT rig (stage/camera/RT/portrait, unchanged lifecycle) vs per-ENTRY
>   `EnsureFolkloreModel`/`DestroyFolkloreModel` (HonoBehavior dispose loop + UNCONDITIONAL Destroy,
>   fields cleared in finally). **Per-entry failure isolation:** a bad token degrades THAT entry to
>   text-only (warn naming entry+token) and the rig survives; `folkloreRigFailed` stays
>   rig-infrastructure-only. **Auto-framing** replaces the test-GEO-tuned knobs: 8-corner
>   `sharedMesh.bounds` aggregation (bind-pose, synchronous, render-independent) transformed into
>   stage space, skipping DISABLED renderers (isBattle:false disables the battle_model renderer
>   COMPONENTS, not their GameObjects — a naive walk would pollute the fit), margin 1.2, degenerate
>   cases fall back to the round-3 proven pose (`CamDist −700`/`AimY −80`, re-roled as fallback).
>   Retreat lever: `FolkloreRigLiveIdle=false` = rung-1 static behavior including the fallback pose.
> - **THE SKEPTIC ROUND (7 findings, 3 folded pre-capture):** BLOCKER — `ResolveFolkloreDisplay` ran
>   outside every try/catch, and `GetGEOID` → `Path.GetFileNameWithoutExtension` THROWS on
>   `"`/`<`/`>`/`|` in a hand-edited token (the exact malformed-token case the checklist tests);
>   now whole-body guarded. HIGH — **the fade-window race**: `UIScene.Hide` only `SetActive(false)`s
>   after the fade elapses, so the one-frame-defer coroutine could resurrect a full animated rig
>   AFTER `TeardownFolkloreRig` ran → the `folkloreClosing` flag (set first line of Hide, cleared in
>   Show, checked after every yield). HIGH — the retreat lever didn't gate auto-framing (its comment
>   overclaimed); now gated with an explicit fallback-pose else-branch. Skipped-with-refutation
>   MEDIUM: re-running the fit after Play changes nothing — `sharedMesh.bounds` is the STATIC asset
>   bind-pose, animation never moves it; the 1.2 margin is the absorber (watch on playtest).
> - **RUNG 4 — THE KIT LANE (offline ★ DONE same session):** `display =` on `[[folklore]]`
>   (§3 grammar verbatim): `resolve_display` (friendly → exact GEO/numeric id → `model:` prefix),
>   third-token emission, `validate_blocks` display checks (near-miss hints, `resolve_prefab` alias
>   INFO), build warn-and-drop-display-only. 63 folklore tests; full suite 3444 passed / 0 failed.
>   The p0-demo toml now carries `display =` on 80/83/84 and lints clean — the in-game end-to-end
>   confirmation rides the next demo redeploy.
> - **Playtest wiring (live `FF9CustomMap/FolklorePatch.txt`, hand-edited):** 80 =
>   `model:GEO_MON_B3_187` (small) · 83 = `model:GEO_MON_B3_118` (the rung-1-proven baseline) · 84 =
>   `model:GEO_MON_B3_085` (large) · 81 token-less (text-only path) · 82 = `model:NOT_A_REAL_GEO`
>   (deliberate garbage — the fail-safe warn). The 12-point checklist is in the workflow record; the
>   short form: baseline 83 first, then idle motion (two snaps seconds apart), then 80/84 framing,
>   rapid paging + locked rows, garbage/no-token entries then RESELECT 83 (proves per-entry
>   isolation), the rung-1 leak snaps, world-map open, 5-10 open/close cycles.
> - Gates: reverse `-F0` TEXT clean on live; forward `-F0 --binary` onto
>   `backups/preS46-snapshots.20260721` == live bytes IDENTICAL; 9 hunks. (The recapture's index-line
>   blob hash differs from the rung-1 capture — `--no-index` context, advisory-only; the byte gates
>   are the authority.)
>
> ## NEXT SESSION — where to pick up
>
> - **PLAYTEST RUNGS 2+3** (checklist above): close FF9 → deploy build (msbuild WITHOUT DWIXNoDeploy)
>   → relaunch → codex at field 30020 (~ → Warp; the FOLKP0 demo save has 80-84 granted after the
>   discovery walks).
> - **Rung 5 garnish + open user calls**: unchanged at the bottom of this doc (turntable, W0
>   lights, idleClip, battle-look flip).
> - **Housekeeping still open**: the s45 sharp inner-card corners TODO (`SUBMENU.md`); the column's
>   right edge 800 vs the ±771 pillarbox comment (one 4:3 look someday); the bottom lore window's
>   caption is blank — a `FolkloreLoreCaption` localization row can name it with zero DLL work. Captured as
> `memoria-patches/s46-folklore-render-rig.patch` (ONE file, `FolkloreUI.cs` only — no csproj change; both
> gates green: reverse `-F0` clean on live, forward `--binary -F0` onto `backups/preS46-snapshots.20260721`
> == live bytes; the deployed DLL carries the new method names, both arches MD5-match Output). Build shape:
> a 9-agent ground→design→3-skeptic→repair workflow (Sonnet fleet, `wf_e2b1478a`); the skeptics caught 2
> BLOCKERs + 2 HIGHs pre-compile, all folded in — the shipped rung 1 therefore DEVIATES from the plan below
> in five load-bearing ways:
> 1. **`OnDisable()` teardown backstop** — `UIManager.OnLevelWasLoaded` SetActive(false)'s the scene
>    directly on every level load, bypassing `Hide()`; OnDisable fires for either path.
> 2. **The first mint is deferred ONE frame past `Show()`** (`RenderFolkloreEntryLazily` +
>    a one-shot coroutine) — `Show()` synchronously reaches `RefreshDetail()`, so "lazy on first
>    selection" was otherwise the first-open burst by another name. Later selections render inline.
> 3. **As-you-go field commits in the mint** — every `this.folklore*` field is assigned the moment its
>    object exists, so the catch's `TeardownFolkloreRig()` can destroy a half-built rig (batched-at-end
>    commits made the catch a no-op → a permanent leak under the DontDestroyOnLoad tree).
> 4. **Teardown DESTROYS the portrait GameObject + the RT** (not deactivate/Release-only — one leaked
>    widget per codex visit otherwise) and **`Destroy(stage)` is UNCONDITIONAL** — the HonoBehavior
>    dispose loop is an extra step, never a substitute (dispose kills the component's OWN gameObject,
>    a child, not the ancestor).
> 5. **Portrait depth = `min(labelDepths) − 2`** (tie-avoidance vs the unmeasured sheet depth) + a
>    one-shot pane depth census (`DumpDetailPaneOnce`) that runs BEFORE any portrait exists — read it
>    in the log on the first playtest to confirm the margin.
> Grounding drift kept honest: the viewer's pose is `Euler(20,0,0)` + yaw on a SEPARATE drag wrapper —
> the rig's composed `Euler(20,180,0)` is a declared simplification (yaw = aesthetic, adjust freely);
> `SetActive(false)`-before-Destroy has NO in-tree precedent (new discipline, labeled so in-code); the
> rig parents under `base.transform` (the scene's own DontDestroyOnLoad seat, the file's ROUND-2 LAW) —
> teardown-on-Hide/OnDisable is the cleanup, not scene death. **Playtest = §2 rung 1's four checks; a
> DLL change needs a full RELAUNCH.** Rungs 2+ below remain unbuilt; the open questions at the bottom
> still gate them only.
>
> *(Original pre-build note, kept for the record:)* Rung 1 needs NO user decisions (viewer defaults:
> opaque background, field look, one static render). Plan produced 2026-07-21 by a 4-lane grounding
> workflow over the engine source (model spawn / RT precedent / anim+layers+lighting / kit grammar;
> 5 agents, every mechanism claim cited file:line) + synthesis. The headline: the rig is a COMPOSITION
> OF TWO SHIPPING ENGINE PIECES — Memoria's Model Viewer (spawn any GEO over live NGUI) and the Libra
> photo (camera -> RenderTexture -> menu) — displayed through stock NGUI UITexture. Captures follow the
> PRE-MARKER CR RULE (`memoria-patches/README.md` §s45); the `project-ff9-ngui-menu-construction`
> memory is required reading before touching FolkloreUI.

> **Goal.** A codex bestiary entry displays its creature as a live 3D render inside the existing 780x880 detail pane (`FolkloreUI.cs:410`, `BuildFramedPane` 333-370). The rig is the composition of two proven engine halves — Memoria's **Model Viewer** (spawn any GEO over live NGUI, `ModelViewerScene.cs:1725`) and the **Libra photo** (camera → RenderTexture → menu, `BattleHUD.Public.cs:213-235`) — plus the stock **UITexture** display seat (`Global\UI\UITexture.cs:7-41`). Almost every primitive is cited stock; the NOVEL pieces are flagged and each gets its own rung so a playtest isolates it.

---

## 1. THE MECHANISM MAP

| Concern | Chosen mechanism | Precedent / NOVEL flag |
|---|---|---|
| **Name → GameObject** | `ModelFactory.CreateModel(geoName, isBattle:false, true, Configuration.Graphics.ElementsSmoothTexture)` — the single engine-wide factory; context-free (static `FF9BattleDB.GEO`, `FF9BattleDB.GEO.cs:6`; static `AssetManager`, `AssetManager.cs:35-`). | Verbatim the Model Viewer's creature call, `ModelViewerScene.cs:1725`. `isBattle:false` is load-bearing: unlit shader, no `battlebg.BattleRoot` reparent (`ModelFactory.cs:121, 199-200`). Null return on missing asset (`ModelFactory.cs:62-63, 72-73`) → text-only pane. |
| **Numeric ref → GEO name** | `FF9BattleDB.GEO.GetValue(id)`; unknown-name guard `ModelFactory.GetGEOID(name) == -1`. | Enemy path `BattleUnit.cs:828`, `HonoluluBattleMain.cs:286-288`; guard `ModelFactory.cs:391-401`. |
| **Placement (the leak defense)** | Stage GameObject far offstage (e.g. `(0, -10000, -10000)`) **AND** layer 10 (NGUI) stamped recursively. Belt-and-suspenders because there is **no camera-proof free layer**: Battle Camera masks `0xFFFFFFFF`, FieldMap `0xFFFFFBDF` (all unnamed 12-31 layers included). Layer 10's only renderer is the ortho UI Camera (`cullingMask 0x00000400`, size-1 slab at UI Root) — layer 10 + far position is rendered by nothing stock. | Measured camera census (mainData TagManager + level0..27 dumps — lane 3 numbers); `SetLayerRecursive` shape `NetSyncClient.cs:1856-1861`; layer inherit law `NGUITools.cs:361-376`, `UIManager.cs:205`. Position-as-guarantee: NOVEL discipline (no stock cullingMask hygiene exists — `HonoluluBattleMain.cs:657` runs mask `-1`). |
| **Camera** | Dedicated camera on the stage, **`enabled = false` always**, driven by manual `cam.targetTexture = rt; cam.Render();` — a disabled camera never joins the scene render loop, so even a broken mask assumption can't leak. Pose: stage + `(0,0,-1000)`, `LookAt(stage, Vector3.down)` (PSX y-down), FOV 40, near 0.1, far 10000. `cullingMask = 1<<10`. `depth = -4096` as a parking convention in case of a null-targetTexture bug. | Manual-render pair: `BattleHUD.Public.cs:224-226`. Pose numbers: `ModelViewerScene.cs:296-297, 1668-1674`. Runtime camera mint skeleton: `NGUITools.cs:652-689` (the tree's only one). Depth parking: MBG movie camera `MBG.cs:44`. A camera with a **persistent** targetTexture is NOVEL composition (Libra is one-shot; no in-tree camera keeps targetTexture set). |
| **RenderTexture** | ONE persistent `new RenderTexture(w, h, 24)` — the 24-bit depth buffer is mandatory for 3D (the tree's only nonzero-depth RT is `GEOTEXHEADER.cs:126`; every 0-depth RT is 2D-blit). Even dimensions, pane-sized (e.g. 640x720 inside the 780x880 pane) — `UITexture` trims odd sizes (`UITexture.cs:159-187`). `filterMode` via `ModelFactory.GetFilterMode(...)` (`SFX_Rush.cs:69-77` idiom), `.Create()` (`PSXTextureMgr.cs:24-40`). | Construct+Create: `SFX_Rush.cs:69-77`, `PSXTextureMgr.cs:24-40`. Persistent RT as live texture: `GEOTEXHEADER.cs:126-130`. |
| **Display seat** | `UITexture` minted at runtime — `NGUITools.AddWidget<UITexture>(detailPanel, depth)` (`NGUITools.cs:747-754`), `uiTex.mainTexture = rt` (the setter takes any `Texture`; a RenderTexture IS one — `UITexture.cs:23-40`). Placed with FolkloreUI's own `SetAnchor(null)+pivot+SetRawRect` idiom (`FolkloreUI.cs:364-366, 420-426`). Same panel subtree as the pane sprites; widget depth above the Body sheet — `UIPanel.FillAllDrawCalls` opens a dedicated drawcall for the foreign texture but z-orders strictly by widget depth (`UIPanel.cs:1017-1105`, break at 1041, sort 1011-1014 / `UIWidget.cs:611`). **No new UIPanel** (the s45 panel-depth laws, `FolkloreUI.cs:498-500, 56-59`). Never `MakePixelPerfect` (`UITexture.cs:234-252` snaps to RT dims). | UITexture runtime-swap: `TitleUI.cs:308-314`; in-menu UITexture: `UIManager.cs:623-643`. Default shader `Unlit/Transparent Colored` (`UITexture.cs:72`). Runtime-minted UITexture: helper exists, no in-tree call site does exactly this — **NOVEL call site, stock machinery**. |
| **Background** | Default **opaque** (viewer-style, `ModelViewerScene.cs:102`) — PSX shaders' destination-alpha is unverified; transparent (`backgroundColor = (0,0,0,0)`, nearest precedent `GL.Clear(…, Color.clear)` `GEOTEXHEADER.cs:132-139`) is a rung-gated experiment, never the first build. | Lane 2 risk 1: possible halos/black rect through `Unlit/Transparent Colored`. |
| **Animation** | `isBattle:false` attaches **ZERO clips** (`ModelFactory.cs:171,177` — `addAutoAnim = (isBattle && !_B1_) || _W0_`; empty mapping no-ops `AnimationFactory.cs:68-83`). Fix = the viewer's recipe: filter `FF9DBAll.AnimationDB` on the name suffix (`anim.Value.Substring(4).StartsWith(geoName.Substring(4))`, `ModelViewerScene.cs:1679-1691`), `AnimationFactory.AddAnimWithAnimatioName` each (`AnimationFactory.cs:54-66`), `anim.Play(animList[0])` (`ModelViewerScene.cs:1991-1997`), loop by re-Play in Update (`ModelViewerScene.cs:1324-1327`). Guard `GetClip == null` (`btl_mot.cs:226-227`). Menus never zero `Time.timeScale` (only `QuitUI.cs:55`, `QuadMistGame.cs:175`) so clips tick live behind the codex. **Do NOT copy battle's frame-servo** (`btl_mot.cs:216-234` sets speed=0 + Sample — expects a battle driver). | All viewer-proven; `animList[0]` idle is a heuristic (risk: first alphabetical clip may be a death pose) — optional `idleClip` override token later. |
| **Lighting** | **None.** FF9 GEO models are unlit — `CreateModel` force-assigns `Unlit/Transparent Cutout` (non-battle) / `PSX/BattleMap_Abr_1` / `BattleMap_Ground` (`ModelFactory.cs:117-145`); field and battle scenes contain ZERO Light objects (level dump). The viewer renders every model class lightless and correct. Exception: `GEO_SUB_W0` worldmap actors are lit (`WorldMap/Actor`, `ModelFactory.cs:118-119`) — **refused at parse until a rung ships the viewer's 3 directionals** (`ModelViewerScene.cs:196-217` + `_FogEnabled=0` 1808-1811). Tint is a fix-if-wrong knob: the viewer sets none; neutral is `_Color` 0.5 grey (`fldchar.cs:72`, `FieldMapActor.cs:93`, write loop `btl_util.cs:505-518`). | Measured, not guessed (lane 3). |
| **Model pose** | Uniform scale 0.5, base rotation `Euler(20, yaw, 0)`. | `ModelViewerScene.cs:106, 1795-1797`. |
| **Teardown** | HonoBehavior-safe destroy: if `GetComponentsInChildren<HonoBehavior>()` non-empty → `UnregisterHonoBehavior(dispose:true)`, else `Destroy` — a raw Destroy races `HonoBehaviorSystem`'s sweep (the proven s36 law, code shape `NetSyncClient.cs:1821-1848`). Plus `SetActive(false)` in the same call before any deferred Destroy (Destroy is end-of-frame; a scene camera could catch one frame). Asset memory rides the stock lazy sweep (`Resources.UnloadUnusedAssets`, `SceneDirector.cs:82,400,459,566`). | Viewer swap discipline `ModelViewerScene.cs:1699-1711`, hardened by our own law. |
| **Fallback tier (kept in the back pocket)** | The Libra one-shot: render once, `ReadPixels` into a Texture2D (`BattleHUD.Public.cs:224-235`), assign THAT to the UITexture. Zero novel pieces, immune to device-loss, no live animation. | Shipping stock; this is the retreat position if the live-RT tier misbehaves. |

---

## 2. THE PHASE LADDER

Each rung = one engine build + one human playtest (+ `tools/game_snap.ps1` frames I read myself). Every rung is independently verifiable and fail-safe-vanilla: `[Folklore] Enabled` still gates the whole screen, and any rig failure degrades to the s45 text-only pane.

### Rung 1 — THE HARDCODED PORTRAIT (the core mechanism, nothing else)
**Build:** In `FolkloreUI`, when the detail pane shows any bestiary entry, spawn ONE hardcoded model (a MON B3 GEO, e.g. `GEO_MON_B3_118` — the viewer's own test class, `ModelViewerScene.cs:1725`): stage at `(0,-10000,-10000)` layer 10, disabled camera, persistent 24-bit RT, **opaque black** background, **one manual `Render()`** on entry show (no animation, no per-frame drive), UITexture in the pane. Registry `Display` token untouched. Spawn lazily on first selection — never in Awake (the s45 first-open hang is open; instrument with the existing Stopwatch idiom, `FolkloreUI.cs:380`).
**Playtest proves:** (a) a creature is visible, framed, right-side-up inside the pane (the `up=Vector3.down` + 20° X law, `ModelViewerScene.cs:296-297,1797`); (b) menu opens/closes clean; (c) **the leak test** — walk the field with the menu closed, then enter a battle, snap both (Battle Camera culls nothing — this is the snap that matters); (d) open the codex **from the world map** (no `FieldMap Camera` there, `FieldMap.cs:82-87` / `ff9.cs:2746` — the rig owns its camera so this must just work).
**Can go wrong:** upside-down/mirrored creature (frame law); doubled geometry on a battle-form model (the field_model*/battle_model* overlay policy, `ModelFactory.cs:189-198` — if the snap shows it, the fix is the per-form subtree hide, `extract.py:114-129`); black/too-dark model (tint knob, `btl_util.cs:505-518`); one-frame offstage flash (add `SetActive(false)`-before-Destroy); limbs rendering through the body = someone dropped the 24-bit depth buffer.

### Rung 2 — THE LIVING IDLE (animation + per-frame render)
**Build:** the viewer's clip discovery + `Play(animList[0])` + re-Play loop; the manual `Render()` moves into `FolkloreUI.Update` while the pane is visible (the MovieMaterialProcessor pump pattern, `MovieMaterialProcessor.cs:9-27`, camera stays disabled). Guard missing clips (`AnimationFactory.cs:62-64` silently skips; `GetClip` null → next list entry, log the name; empty list → static bind pose, still displayable).
**Playtest proves:** two snaps seconds apart show different poses (animation ticks behind the menu — the `Time.timeScale` claim); no stutter; a model with no clips still displays statically.
**Can go wrong:** frozen T-pose (clip discovery empty — the isBattle=false zero-clip gap); `animList[0]` is a death/attack pose on some monster (cosmetic, noted for the grammar rung's `idleClip` token); Update stalling reproduces the s45 hang tell (stale frame = Update stopped — a diagnostic gift, not a bug to hide).

### Rung 3 — THE REGISTRY WIRE + LIFECYCLE HARDENING (engine-side `Display` parse)
**Build:** replace the hardcoded name with the s45 `Entry.Display` token (already parsed and stored, s45 patch:986). Engine parse: split on first `:`; scheme `model` → GEO name (or all-digits → `FF9BattleDB.GEO`); unknown scheme / `GetGEOID == -1` / null CreateModel → `Log.Warning` + text-only pane (the registry's existing bad-line law, s45 patch:977). Lifecycle: model **swaps per entry** (viewer `ChangeModel` pattern, `ModelViewerScene.cs:1699-1711`, via the HonoBehavior-safe path); stage+camera+RT **cached for the screen visit**, torn down on Hide (`cam.targetTexture = null; rt.Release();` — `SFX_Rush.cs:84-94` discipline; null the UITexture.mainTexture first). The rig is a plain scene object, **never parented under the persistent UIManager/DontDestroyOnLoad tree** — a leaked rig then dies with the scene as a backstop. Hand-edit `FolklorePatch.txt` with a real token on one entry.
**Playtest proves:** browse 10+ entries switching models rapidly (destroy race — the HonoBehavior law's kill test); open/close the menu 10x (RT release, no VRAM creep); a hand-edited **garbage** third token shows the text-only pane and does not brick the menu; entries with no token show text-only; alt-tab / resolution flip self-heals (per-frame Render repaints device-lost RT contents).
**Can go wrong:** destroy race corrupting HonoBehaviorSystem (the law exists because it happened); RT leak on F8 soft reset (guard like the viewer's re-Init panel destroy, `ModelViewerScene.cs:127-134`); a collider-bearing future model on layer 10 eating UICamera clicks (`UICamera.cs:619,885` — strip colliders at spawn now, cheaply).

### Rung 4 — THE KIT LANE (offline-provable; one in-game confirmation)
**Build:** the full §3 grammar — `display =` key, `resolve_display`, third-token emission, lint. 3993-suite tests carry the proof; the playtest is one authored field.toml whose bestiary entry shows its creature end-to-end.
**Playtest proves:** author-surface → wire → pane, plus the lint UX (a typo'd name gets difflib hints offline, before any deploy).

### Rung 5 — GARNISH (each optional, each its own small round)
- **Battle-look flip** (bestiary showing the battle overlay set instead of field: flip the two renderer loops — NOVEL one-liner per lane 1) — user aesthetic call.
- **Transparent background** over the pane sheet (the untested alpha compositing) — probe with a bright sprite behind the widget, retreat to opaque on any fringe.
- **`idleClip` 4th registry token** (or authoritative `BTL_SCENE.ReadBattleScene → Mot[0]` resolution, standalone-proven `BattleSceneExporter.cs:85-86`, mapping `btl_init.cs:239-240`).
- **Turntable yaw** in Update.
- **W0 world models**: the viewer's 3 directionals + fog-off, or keep the parse-time refusal.
- **Palette variants**: `SB2_MON_PARM.TextureFiles` needs the battle scene binary — bake variant choice into displayRef if ever needed (`HonoluluBattleMain.cs:291-292`).

---

## 3. THE displayRef GRAMMAR

**Wire format (FolklorePatch.txt):** `<keyItemId> <category> [displayRef]` — the third token the s45 engine already stores (`Entry.Display`, s45 patch:925-930, 986). The engine whitespace-splits (`DataPatchers.SpaceSeparators`, s45 patch:974), so the token is **one whitespace-free string**; canonical form emitted by the kit: **`model:GEO_NAME`** (GEO names are `[A-Z0-9_]+`, space-free by construction). Scheme namespace reserves `sprite:` for a 2D contingency (costs one doc line; the engine ignores unknown schemes gracefully — never scheduled unless 3D hits a wall; kit half is nearly free via `thumbcache.py:46-60`).

**Author surface (field.toml):** one optional key on `[[folklore]]`: `display = "<ref>"`, resolved kit-side in order:
1. friendly archetype/creature name (`"moogle"`, `"bandersnatch"`) → GEO via the existing tables (`archetypes.py:20-185`, lookup pattern `infohub.py:63-73`);
2. exact GEO name (case-insensitive) or numeric GEO id → `catalog.model` / `catalog.resolve_model` (`catalog.py:84-96, 119-133` — ValueError with difflib near-miss hints, n=6 cutoff 0.4);
3. explicit `model:` prefix allowed but optional.
**No raw enemy display names ("Bomb")** — no such catalog exists in the kit (verified zero hits) and building one is a separate provenance-sensitive project.

**Canonicalization law:** friendly names die at the kit boundary — the engine has no archetype table; the kit emits the **requested** GEO name, not the post-alias donor, because the engine's own loader replays the alias chain (`extract.py:83-90` documents CheckUpscale→GetRenameModelPath in ModelFactory.cs). Tests assert the emitted token matches `^model:GEO_[A-Z0-9_]+$`.

**Validation (the recurring build-vs-lint split, `folklore.py:162-164`):**
- **lint** (`validate_blocks`): resolve per the order above; unknown → the catalog near-miss error verbatim; then run `resolve_prefab` (`extract.py:76-111`) — `pgid == -1` ⇒ ERROR (no shipping geometry); resolved prefab ≠ requested (~103 alias-only ids, `extract.py:79`) ⇒ INFO naming the donor (so "GEO_MAIN_B0_000 renders Zidane's field body" surprises no one before a playtest). All offline against baked tables — no install needed.
- **build** (`_emit_folklore`): same resolution; on failure **warn and drop the display ONLY** — ship the entry two-token, never skip the entry (the fail-safe philosophy, `build.py:7416, 7445`). The duplicate-id later-wins warning (`build.py:7440-7443`) gains a mention that the earlier block's display is dropped too.
- Display is **not** gated on category (a places entry showing a landmark model is legitimate).

**Kit files to touch (exhaustive — verified no docs/editor/Workspace surface exists yet):**
1. `ff9mapkit\ff9mapkit\content\folklore.py` — `resolve_display(ref) -> "model:GEO_..."`; `render_patch_lines` third token (`folklore.py:41-51`); `validate_blocks` display checks (`folklore.py:161-216`); module grammar docstring (`folklore.py:35-36`).
2. `ff9mapkit\ff9mapkit\build.py` — `_emit_folklore` (`build.py:7408-7479`): resolve inside the existing warn-and-skip try/except, drop-display-only.
3. `ff9mapkit\tests\test_folklore.py` — registry-sidecar section (`:168`): third-token emission, friendly-name canonicalization, no-display omission, whitespace/unknown rejection, alias-chain warning, the `^model:GEO_` regex fence.
4. `studies\folklore-codex\SUBMENU.md` / `REDESIGN.md` — record the finalized grammar (SUBMENU.md:343 already states the shape) + the stale-registry-vs-.mes note (both files write from one `_emit_folklore` pass, `build.py:7460-7478`; only manual edits can skew — documented, not engineered around).

---

## 4. LIFECYCLE + FAIL-SAFETY

**Cache policy (create/destroy vs cache, the menu is entered often):**
- **Per entry-switch:** only the model swaps (viewer pattern, `ModelViewerScene.cs:1699-1711`) — HonoBehavior-safe destroy + `SetActive(false)` first.
- **Per screen visit:** stage + camera + RT minted lazily on the FIRST selection of a display-bearing entry (never Awake — the s45 first-open hang budget, Stopwatch-instrumented `FolkloreUI.cs:380`), cached across entry switches, torn down on Hide: null the UITexture.mainTexture, `cam.targetTexture = null`, `rt.Release()`, destroy the rig (`SFX_Rush.cs:84-94`).
- **Never cached across visits / never DontDestroyOnLoad:** the rig is a plain scene-root object so a missed teardown dies with the next scene transition; asset memory rides the stock lazy sweep (`SceneDirector.cs:400`). Long browse sessions hold swapped-model assets until the next field transition — identical to the viewer's behavior, acceptable; watch only on a reported stutter.

**Fail-safe ladder (a bad displayRef must never brick the menu — every failure lands on the s45 text-only pane):**
1. Kit lint catches typos offline with suggestions; kit build drops the display and ships two-token.
2. Engine parse: unknown scheme / bad name / `GetGEOID == -1` → `Log.Warning`, no rig, text-only pane (s45 bad-line law, patch:977).
3. `CreateModel` returns null (missing prefab bytes — e.g. a modded p0data4 the offline lint cannot see) → same degrade; the engine warn log is the early detector.
4. Empty clip list → static bind pose, still displayed.
5. Any rig exception → try/catch around the whole spawn, degrade to text-only, never throw out of `FolkloreUI` (the codex's standing law).
6. The camera is permanently disabled + manual-Render + `depth -4096` parking + layer 10 + far offstage: four independent defenses against the one catastrophic failure class (the rig drawing on the player's screen).
7. `[Folklore] Enabled` remains the master gate — OFF is byte-vanilla.

**Known-open interactions:** the s45 first-open hang predates this work — the rig adds first-selection cost, which is why spawn is lazy and Stopwatch-attributed before anyone optimizes the wrong thing; a stale pane frame is the tell that `Update` stalled (diagnostic, not a defect of the rig). The Quit dialog freezes the idle (`QuitUI.cs:55` zeroes timeScale) — harmless, do not "fix".

---

## Open questions (user calls — none block rung 1)

- **Ship tier:** live animated idle (rungs 1-2) vs a static Libra-style one-shot portrait (zero novel
  pieces, no device-loss concerns) as v1 — live as an upgrade.
- **Background:** opaque viewer-black (safe, rung-1 default) vs transparent-over-the-sheet (untested PSX
  destination-alpha compositing — a rung-5 probe).
- **Look:** isBattle=false shows the FIELD overlay set; the BATTLE look is a one-line renderer-loop flip
  (rung-5 garnish). The rung-1 snap of a real monster settles whether the difference even reads.
- **Idle fidelity:** animList[0] heuristic vs an optional idleClip 4th registry token vs the authoritative
  BTL_SCENE Mot[0] resolution.
- **Turntable yaw** — yes/no.
- **W0 worldmap models** (need the viewer's 3 directional lights): permanent parse-time refusal vs a
  rung-5 lights garnish.
- **Launch content:** mechanism+grammar only, or also author display tokens onto the existing example
  entries in the same arc.
