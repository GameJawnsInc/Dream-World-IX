# Thomas swap -- LOCAL-ONLY MEME BUILD

> Builds directly on `studies/custom-summons/PLAN.md` rungs 1-7 (all ★ in-game proven) plus a fresh
> 3-lens recon (suppression / composition / asset) that closed the three open questions this build
> depends on -- see the journal cited in the mission for the full agent output; the headline findings
> are cited by file:line throughout this README and `build_thomas.py`'s own docstring.
>
> **THIRD-PARTY CONTENT.** The asset (`C:/gd/SCRATCH/thomas/Thomas the Tank Engine.fbx` +
> `Thomas_d.png`) is NOT ours and is NEVER committed to this repo -- see "Provenance" below. Every
> script here reads it from `C:/gd/SCRATCH/thomas/` and refuses with a clear message if it's absent.

## What this does

Replaces **only the visible creature mesh** inside the bench's real "Bahamut Cinema" cast (Iviv's
minted Spark → Bahamut Cinema ability, field 30300, `ef084` = rung 3's private fresh-id copy of the
donor) with the user's Thomas the Tank Engine model -- while keeping the REAL native Bahamut
cinematic running underneath it: the real camera (armed by the untouched `LoadSFX: SFX=Bahamut__Full
; UseCamera=True` line), the real sounds (the untouched `ef227/Sequence.seq`'s `PlaySound` calls),
and the real damage/EffectPoint timing. Nothing about Bahamut's OWN drama is edited or re-timed --
only his mesh is suppressed and Thomas is layered in alongside it.

## The mechanism, precisely

`ef084/PlayerSequence.seq` (the script the bench ability's `vfx1=84` dispatches to) is a **spliced
copy of the real, unmodified `ef227/PlayerSequence.seq`** (Bahamut's own donor script -- fetched
fresh from the install every build, sha256-guarded, never committed -- the rung2/3/4 provenance
law). Two edits, both anchored on the donor's one `PlaySFX` line:

```diff
 StopChannel
 PlayAnimation: Char=Caster ; Anim=MP_MAGIC
 WaitAnimation: Char=Caster
+StartThread: Condition=1 == 1 ; Sync=False
+	LoadSFX: SFX=84 ; Char=Caster ; UseCamera=False
+	WaitSFXLoaded: SFX=84
+	PlaySFX: SFX=84 ; SkipSequence=True
+	WaitSFXDone: SFX=84
+EndThread
-PlaySFX: SFX=Bahamut__Full ; Reflect=True
+PlaySFX: SFX=Bahamut__Full ; Reflect=True ; HideMeshes=0,1,2,...,63
 WaitSFXDone: SFX=Bahamut__Full ; Reflect=True
 SetVariable: Variable=cmd_status ; Value=|2 ; Reflect=True
```

Everything else in the donor's 24 lines -- the row-check/turn threads, `Message`, `SetupReflect`,
the **real** `LoadSFX: SFX=Bahamut__Full ; Reflect=True ; UseCamera=True` line (kept byte-for-byte,
unmodified -- this is what arms the real native creature load + the real cinematic camera), the
chant animations, the `WaitSFXDone`/`ActivateReflect`/step-back/`Turn` tail -- ships untouched. The
actual "Mega-Flare" choreography (`EffectPoint`, `PlaySound`, `SetBackgroundIntensity`) lives in the
**donor's own** `ef227/Sequence.seq`, nested-loaded by the RESOLVED id (227, resolved from the name
`Bahamut__Full`) -- never `ef084`'s own `Sequence.seq` (rung 3's inert leftover copy, never read on
this path). It is never copied, never edited, and stays 100% the real cinematic.

### 1. `HideMeshes=0,1,2,...,63` -- suppresses Bahamut's mesh, keeps his camera+tick alive

`PlaySFX`'s own `HideMeshes` argument (`BattleActionCode.cs:394-419 TryGetArgMeshList`) is parsed
into `SFXData.RunningInstance.preventedMeshIndices` (`SFXData.cs:136-154,1376-1392`) and honored
**only at the final draw step**, `SFXDataMesh.Runtime.Render()`'s `Graphics.DrawMeshNow` call
(`SFXDataMesh.cs:620-662`). Everything upstream of that draw call -- `Load(frame)`'s native
`SFX.SFX_Update` tick (which the camera track rides), `SFXRender.Update()`, and the camera-engine
arm at `Runtime.Begin()` (`SFXDataCamera.currentCameraEngine = SFX_PLUGIN`) -- runs completely
untouched every frame. `battle.cs:86`'s `SFXDataCamera.UpdateCamera()` call is a wholly separate,
unconditional-per-frame call site that only reads that static flag -- it has no dependency on the
mesh-draw walk at all. Net effect: the real Bahamut camera cut keeps running exactly as authored;
only his geometry stops rendering. Unmatched indices are inert (no error), so the blanket `0-63`
range is safe regardless of how many distinct `SFXMesh` keys the native effect actually emits --
**this is the one genuinely unproven op in this whole build** (first-ever use anywhere in the
study); see "Failure modes" below for what a partial/total suppression failure looks like.

### 2. A second `LoadSFX` -- Thomas coexists with the native donor, zero shared state

`BattleAction.sfxList` is a `List<SFXData>` (`UnifiedBattleSequencer.cs:89`); every `LoadSFX` op
appends a brand-new, independent `SFXData`. The real donor's `LoadSFX: SFX=Bahamut__Full` produces
a `SFXDataMesh.Raw` instance, loaded async through the native plugin queue. Thomas's own
`LoadSFX: SFX=84` (self-referencing THIS SAME folder, which carries a `FileList.txt`) makes
`SFXData.LoadSFX()` find the `Model creature_manifest.sfxmodel` line and set
`mesh = new SFXDataMesh.JSON(...)` -- critically, `LoadSFX()` **returns before ever touching
`loadingQueue`** (`SFXData.cs:170-181`), so the native `FF9SpecialEffectPlugin.dll` is never invoked
for Thomas's SFXData at any point in its lifecycle; it never enters the same async queue Bahamut's
own load uses, so there is zero load contention. Both objects sit side-by-side in `sfxList` with no
shared mutable state beyond the list itself; each op (`WaitSFXLoaded`/`PlaySFX`/`WaitSFXDone`)
disambiguates which `SFXData` it targets purely by its own `SFX=` argument (`Bahamut__Full` → 227 vs
`84` → this folder) via `TryGetArgSFXInstance` (`BattleActionCode.cs:218-245`).

Thomas's own quartet runs on a **background thread** (`StartThread: ... ; Sync=False`) so it never
blocks the main thread, which falls straight through to the (now `HideMeshes`-carrying) `PlaySFX:
SFX=Bahamut__Full` line on the very next op -- both effectively start on the same tick. Thomas's own
frame-0 (zeroed the moment **his own** `PlaySFX: SFX=84` fires) lands within a tick or two of
Bahamut's own nested-`Sequence.seq` frame-0 (zeroed the moment the **main thread's**
`PlaySFX: SFX=Bahamut__Full` fires) -- see "Timing math" below for how that lines Thomas up against
the real Mega-Flare beat.

`SkipSequence=True` on Thomas's own `PlaySFX` line is required: `SFXData.LoadSFX` unconditionally
re-reads `ef084/Sequence.seq` on every `LoadSFX` call regardless of the `FileList.txt`/JSON-mesh
branch (`SFXData.cs:174`) -- and `ef084/Sequence.seq` is still on disk (rung 3's leftover byte-copy
of Bahamut's **real** nested drama). Without `SkipSequence=True` it would thread in as a second,
parallel, duplicate-damage copy of the real `EffectPoint` pair. Rung 7 hit this exact trap first;
this build reuses the fix.

### 3. The asset -- normalized via Blender so zero runtime rotation compensation is needed

Thomas's source FBX (`C:/gd/SCRATCH/thomas/Thomas the Tank Engine.fbx`, binary FBX 7.5, fully rigid
-- 0 Deformer/Skin/Cluster/AnimationStack nodes, confirmed by probing the raw binary directly) is
**not deployed as-is**. `ModelImporter.CreateCustomModelFromFbx` reads a Geometry node's raw
`Vertices` verbatim with zero FBX unit/axis conversion, and applies a Model node's own local
transform **only when the mesh is bone-parented** -- a fully rigid mesh like Thomas's gets none of
its source Model node's own baked `Lcl Rotation=(-90,0,0)` (the standard 3ds-Max-Z-up → FBX-Y-up
conversion rotation his file carries -- confirmed via a hand-rolled binary FBX reader, not guessed).
Deployed naively, Thomas would render lying on his side.

**Fix**: `blender_normalize.py` (committed, run once, offline -- see "Regenerating the normalized
model") imports the raw FBX in Blender (which DOES apply the Model transform correctly, the way any
standard viewer would), **bakes it into the raw vertex data** (`transform_apply`), recenters the
pivot to base-center (X/Z centered, Y=0 at the wheels), and re-exports with Blender's DEFAULT
Unity-safe axis mapping (`axis_up='Y', axis_forward='-Z'`). The re-exported Model node carries **no**
transform at all (verified: `xform={}` on read-back) -- so whatever the engine reads verbatim now
*is* what Blender's own viewport showed: upright, correctly proportioned, standing on the ground.

## Axis verification (empirical, not assumed)

A tiny 3-vertex marker mesh was exported with the **exact same** export settings used for
`thomas_normalized.fbx`, at known Blender-local points: `(0,-1,0)` and `(0.01,-1,0.01)` (Blender's
own **front-facing** convention, `-Y` -- confirmed by rendering Thomas from `-Y` and seeing his
face, `view_front.png`) and `(1,2,0)` (Blender's `+Y`, confirmed to be his back, `view_back.png`).
Reading the exported file back with a hand-rolled binary FBX parser:

| Blender local (X, Y, Z) | Raw exported file (X, Y, Z) |
|---|---|
| (0, **-1**, 0) -- front | (0, 0, **+1**) |
| (0.01, **-1**, 0.01) -- front | (0.01, 0.01, **+1**) |
| (1, **+2**, 0) -- back | (1, 0, **-2**) |

Confirms: **file X = Blender X** (unchanged), **file Y = Blender Z** (unchanged -- both "up"), **file
Z = -(Blender Y)**. Thomas's face (Blender `-Y`) therefore lands at **+Z** in the raw exported file
-- exactly matching this codebase's own established "+Z = forward, away from the caster, toward the
enemies" convention (`ef227/PlayerSequence.seq`'s own `MoveToPosition: RelativePosition=(0,0,400) ;
Anim=MP_STEP_FORWARD` for the caster's own forward step). **Consequence: Thomas needs a flat
`Rotation` of `(0,0)` -- zero runtime spin -- to already face the enemies**, unlike rung 7's Iviv
clone (a PSX-heritage kit-exported FF9 battle model, needing the player-baseline `(Y=180,Z=180)`
compensation under the SFX path's raw-euler-no-compensation rule, `SFXDataMesh.cs:807`). This is a
**reasoned** choice from Thomas's own axes, not a copy of rung 7's constant.

Renders (`C:/gd/SCRATCH/thomas/blender_out/view_{front,back,side,34,top}.png`, plus
`C:/gd/SCRATCH/thomas/preview.png` = a copy of `view_34.png`, the offline-eye deliverable) confirm:
fully textured, right-way-up, standing correctly on his own wheels, face and number-1 side panel
clearly visible and correctly colored.

## Scale reasoning

Thomas's raw normalized bounding box (engine-verbatim, no unit conversion applied by the reader,
read back from the deployed `6200.fbx` with the same binary parser): **width 3.496, height 4.913 (Y
spans 0..4.913 -- origin at his wheels), length 10.116** (Z spans -5.058..+5.058, centered). FF9
battle characters run roughly 300-600 units tall (mission context); Bahamut towers over the party.
At **265x** uniform scale: **height ≈ 1302, width ≈ 926, length ≈ 2681** -- roughly 2-4x a party
member's height, appropriately Bahamut-scale huge, and dramatically screen-filling given his length
(a deliberate, on-brand comedic choice for a giant toy train). `THOMAS_SCALE` in `build_thomas.py`
is a single constant -- change it and rerun to retune.

## Placement + timing

### THE FLIGHT (2026-07-22 revision -- replaces the original static hover)

The first build's playtest: *"bahamut is invisible, but Thomas just spawns in front of Iviv and stays
stationary instead of flying around like a dragon. there are also just periods of black screen."*
Re-derived from source rather than assumed (see `build_thomas.py`'s own `THE FLIGHT` comment block for
the full citation trail):

**Anchor truth.** The mission's seed hypothesis was that `Target*`/`TargetAveragePosition*` resolve to
the CASTER on Thomas's own `LoadSFX: SFX=84 ; Char=Caster` route. Tracing the actual runtime path
(`StartThread` compiles to a `RunThread` op, `BattleActionThread.cs:183-193`, executed by the MAIN
thread whose `.targetId` was set to the ability's REAL `cmd.tar_id` -- "AllEnemy" per
`rung3.field.toml:147` -- at cast start, `UnifiedBattleSequencer.cs:159-160`) shows the opposite: our
`StartThread`/`LoadSFX` lines carry no `Target=` argument, so both the spawned child thread's own
`.targetId` (`UnifiedBattleSequencer.cs:1155-1156,1168`) and its later `LoadSFX` call
(`UnifiedBattleSequencer.cs:326-330`) fall through to `runningThread.targetId`, which is the REAL
AllEnemy bitmask inherited from the main thread -- NOT reset to 0, NOT the caster. `Char=Caster` only
ever re-resolves the *caster* argument (stays Iviv); it never touches the target. So
`TargetAveragePositionX/Z` (`FF9/BTL_VFX_REQ.cs:72-91`) already correctly averaged the REAL enemies'
position on this exact route -- **the hypothesis is refuted**. The actual defects were structural: (a)
`CasterPositionY + 20` is GROUND level (zero loom for a dragon), (b) `Origin == Destination` was a
deliberate static hold (zero motion), and (c) Thomas's own ~2681-unit length means a ground-level
placement's bounding volume alone can sprawl back over a modest early-game arena's short
caster↔enemy gap -- combined with (a), this reads exactly as "spawns in front of Iviv, stationary."

**Design choice.** Rather than continue depending on `TargetAveragePosition` (scene-specific enemy
formation, unproven for scene 67's exact layout), the flight is built entirely on **caster-relative
offsets** -- unambiguous (Iviv's own real position), and this directly targets both real defects
(needs elevation + needs motion) regardless of the refuted hypothesis. Axis convention (`+Z` from a
player caster = toward the enemies) is independently confirmed twice: rung 7's own in-game-proven
`"CasterPositionZ + 600"` hover ("toward the enemy side"), and Thomas's own axis-verification table
above (his normalized front lands at `+Z`, matching the donor's own
`MoveToPosition: RelativePosition=(0,0,400)` caster forward-step).

**The 3 phases** (every number is a named constant in `build_thomas.py` -- retune + rerun in one line,
recast-only, no relaunch), mapped onto rung-4's tick map (Thomas's own clock zeroes at HIS OWN
`PlaySFX`, which fires within ~1-2 ticks of the donor's nested `Sequence.seq` frame-0 -- generous
overlap margins below, not razor's-edge cuts, to absorb that uncertainty):

| Phase | Frames | Covers | Motion |
|---|---|---|---|
| **P1 Entrance** | 0–420 | blackout ramp (t=0), flash1 (t=116), flash2 (t=289); arrives just before the dim reveal (t=403) | swoop in from high off to one side (`CasterPositionX-2000, CasterPositionY+1500, CasterPositionZ+300`), descending + advancing into center-stage (`CasterPositionX, CasterPositionY+700, CasterPositionZ+1800`); `SinusOut` (decelerating arrival) on all 3 axes; yaw banks 0→90° |
| **P2 The Reign** | 420–520 | the dim reveal (t=403) through the ENTIRE Mega-Flare window (t=434–516) incl. BOTH `EffectPoint`s (t=486, t=498) | a gentle sway/rise off center-stage (`+220/+80` on X/Y, Z held) via `Sinus` easing (floaty, not a static hold); yaw holds broadside (90°) -- the "safe comedic read" per the mission, and his iconic number-1 side panel |
| **P3 Exit** | 520–580 | lights-restored (t=516) through the close (t≈547) + the same ~33-tick tail margin the original build used | climbs away up-forward (`+380/+1600 total/+2600 total` off center-stage) via `SinusIn` (accelerating departure); yaw turns back 90→0° |

Rotation.Z stays `0` in every piece -- **no roll** (Thomas is not PSX-inverted; the axis-verification
above already established his normalized `Rotation=(0,0)` needs no runtime compensation, so only Y-yaw
is ever touched). `Start=0, End=580` unchanged from the original build (the 3 phase durations sum to
exactly 580).

No `Animations` array (Thomas is rigid, zero clips) -- confirmed safe by source: an FBX entry with an
absent `Animations` key renders the bind pose, no error (`SFXDataMesh.cs:976-977,809-810`); `Movement`
alone is sufficient to give a moving prop a well-defined enter/hold/exit window.

## Files in this directory

| File | What it is |
|---|---|
| `blender_normalize.py` | Committed, our script. Run ONCE (offline, via Blender) to produce `thomas_normalized.fbx` from the raw source. Never touches the repo. |
| `thomas_manifest.sfxmodel` | Committed, 100% our JSON -- **GENERATED** by `build_thomas.py`'s `build_manifest_json()` from the named `THE FLIGHT` constants (not hand-typed; the repo copy is kept in sync on every run so it stays git-diffable). Deployed as `ef084/creature_manifest.sfxmodel` (overwrites rung 7's Iviv-clone one there). |
| `thomas_player_sequence.seq` | Committed, 100% our text -- the splice DELTA (not a standalone sequence; see its own header comment). `build_thomas.py` inserts it into a runtime copy of the real stock donor. |
| `build_thomas.py` | Fetches the real donor fresh from the install (sha256-guarded, never committed), splices, mints Thomas's GEO, deploys everything. `--restore` undoes it. |
| `revert_thomas.py` | Alias of `build_thomas.py --restore` (house convention). |
| `README.md` | This file. |

None of these five files contain Square-Enix bytes or third-party asset bytes -- see "Provenance."

## Regenerating the normalized model

Only needed once, or if you want to re-tune Thomas's pose/pivot before the engine-facing scale/
rotation/position numbers in `thomas_manifest.sfxmodel` (those are applied at runtime by the SFX
system, independent of this step):

```
"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --background --python ^
    studies\custom-summons\thomas-swap\blender_normalize.py -- ^
    "C:\gd\SCRATCH\thomas\Thomas the Tank Engine.fbx" "C:\gd\SCRATCH\thomas\blender_out"
```

Writes `C:\gd\SCRATCH\thomas\blender_out\thomas_normalized.fbx` (what `build_thomas.py` deploys,
binary-copied) + five inspection renders. `build_thomas.py` refuses with a clear message if this
file (or the original `Thomas_d.png`) is missing.

## Test procedure

The `.seq`/`FileList.txt`/`.sfxmodel` edits are all zero-cache, per-cast-reparsed -- **recast-only**,
same as every prior rung. Only the GEO mint (`3DModel 6200 ...`) needs a relaunch, and only the
FIRST time.

1. `build_thomas.py` has already been run this session (see "Mint details" below for what it wrote
   and confirmed). If re-running fresh: `py studies/custom-summons/thomas-swap/build_thomas.py`
   (run from `ff9mapkit/` or anywhere -- it resolves its own paths).
2. **Relaunch FF9 entirely** (not `~` Reload) -- `3DModel 6200 GEO_MON_B0_M200` is a load-time-only
   DictionaryPatch directive; this is the ONE relaunch this build needs.
3. Load the bench save (or New Game → `~` → Warp to field → 30300).
4. Get into a battle on field 30300 (the random encounter, scene 67).
5. Select **Iviv → Spark → Bahamut Cinema**.

**Expect**: the full real Bahamut cinematic plays -- same chant, same camera cut, same roars/flashes,
same damage timing -- but the creature on screen is **Thomas the Tank Engine**, huge, upright,
correctly textured, and now FLYING THE 3-PHASE FLIGHT (see "THE FLIGHT" above): swoops in from high
off to one side during the chant/flashes, arrives and hovers broadside (showing his full profile/
number-1 side panel) with a gentle sway through the entire Mega-Flare + both damage beats, then climbs
away up-forward as the lights restore. No visible Bahamut mesh at any point, and no more standing
stationary in front of Iviv.

**If placement/motion is still off**: capture a short VIDEO of the cast (this project's own law --
`feedback-video-for-visual-bugs` -- behavior/positional bugs need footage, not a prose description; a
screenshot can't show a swoop). `tools/game_snap.ps1` captures single frames only, which is enough for
"is Bahamut's mesh really hidden" but NOT for "does the flight read as flying" -- use a screen
recorder (OBS, Xbox Game Bar `Win+Alt+R`, or any capture tool) for the ~10s of the cast (chant through
the flare) so the next iteration can retune `build_thomas.py`'s named `THE FLIGHT` constants (`STAGE_*`
/ `ENTRANCE_*` / `DRIFT_*` / `EXIT_*` / `YAW_BROADSIDE` / the 3 `*_DURATION`s) from what actually
happened frame-by-frame, rather than from a re-guess.

## Failure modes

| Symptom | Meaning | What to check |
|---|---|---|
| **Full cinematic plays, Thomas visible/huge/upright/textured, FLYING the 3-phase flight, Bahamut's own mesh never appears** | **SUCCESS** | -- |
| The cinematic plays with the REAL camera/sounds/timing, but **Bahamut's native mesh is still visible** (Thomas may or may not also be there) | `HideMeshes` didn't suppress the native creature -- the ONE genuinely unproven op in this build (first-ever use in the study; the 0-63 blanket range assumed but never confirmed against ef227's actual emitted mesh-key count). Possible causes: the index range doesn't cover ef227's real keys (try widening past 63, or switch to hex `0x...` KEY form if the recon's `SFXDataMeshConverter` debug dump is used to read ef227's real keys), or the argument name/syntax is subtly wrong | Re-check the deployed `ef084/PlayerSequence.seq`'s `PlaySFX: SFX=Bahamut__Full` line byte-for-byte against the diff above; capture video (behavior bugs need it, not screenshots) |
| The cinematic plays, Bahamut's mesh is correctly hidden, but **Thomas never appears** | Either (a) the FileList.txt/manifest didn't resolve (re-check `ef084/FileList.txt` + `creature_manifest.sfxmodel` bytes match what's printed above), or (b) `GEO_MON_B0_M200` didn't resolve to id 6200 -- **the relaunch didn't happen, or happened before this deploy** (re-run `build_thomas.py`, then relaunch), or (c) the two-SFX coexistence has an untested interaction specific to a background `StartThread` (rung 7 proved the FileList.txt route in the MAIN thread only, never inside a `StartThread` block) | Confirm the relaunch happened AFTER this deploy; re-run `build_thomas.py` and check "directive_added"/the DictionaryPatch line is present; check the game log if reachable |
| Thomas appears but **badly mispositioned** (off to one side, floating far away, only a sliver visible), OR the swoop/hover/climb geometry just looks wrong for this arena's actual camera framing | The caster-relative constants (`STAGE_*`/`ENTRANCE_*`/`DRIFT_*`/`EXIT_*` in `build_thomas.py`) were miscalibrated for scene 67's actual arena size/camera -- a genuinely new discovery, not a mechanism failure (the CASTER anchor itself is unambiguous; only the OFFSET magnitudes are a guess). `TargetAveragePositionY`/`CasterPositionY` ground-truth is always real; nothing here forces Y=0 the way the ORIGINAL build's `TargetAveragePosition` route did | Capture video (see above), then retune the named offset constants in `build_thomas.py` and rerun (recast-only, no relaunch) |
| Thomas reads as **absurdly wide / clipped at the screen edges specifically during the HOVER** (P2, not the swoop-in) | **Found in adversarial review, 2026-07-22, NOT yet in-game-checked**: the `STAGE_Z` clearance math was sized against Thomas's ~2681-unit LENGTH axis, which only runs along world Z while his yaw is near 0. By the time he arrives at center-stage he's already yawed to `YAW_BROADSIDE=90` (the pose held through the entire P2 reign) -- at that yaw his LENGTH sweeps world X instead (P2's own X range is only `STAGE_X=0 -> DRIFT_X=220`, never sized against a 2681-unit sweep), while only his ~926-unit WIDTH remains on Z. See `build_thomas.py`'s own caveat comment above `STAGE_X/Y/Z` for the numbers and candidate fixes | Capture video of the HOVER specifically; if confirmed, retune `YAW_BROADSIDE` toward 0/180 (keeps the long axis on Z) or accept a wider camera crop, per the code comment |
| Thomas still reads as **static / not "flying"** despite the new manifest | Either this build didn't actually redeploy (rerun `build_thomas.py` and confirm the printed sha256 changed), or the phase Durations are too long/too subtle relative to what's actually visible during the donor's own blackout/flash windows | Capture video; check the deployed manifest's `Movement` array has 3 pieces (not 1) via the printed sha256 or a direct read of `ef084/creature_manifest.sfxmodel` |
| Thomas appears **on his side / rotated 90°**, or the P2 broadside yaw looks wrong (facing away instead of showing his profile) | The normalization step's core claim (baked, no runtime rotation needed) was wrong for this specific engine build, OR `YAW_BROADSIDE`'s sign is backwards for this camera angle -- re-open `blender_normalize.py`'s renders and the axis-verification table above | Compare against `view_front.png`/`view_top.png`/`view_side.png`; try `YAW_BROADSIDE = -90` in `build_thomas.py`, rerun (recast-only) |
| Thomas appears **tiny or absurdly, unusably huge** | `THOMAS_SCALE` (265) was miscalibrated for this arena's actual camera framing | Edit `THOMAS_SCALE` in `build_thomas.py`, rerun (recast-only) |
| The cast doesn't play at all / hangs | Something in the spliced `.seq` broke the DSL parser, or the background thread never resolves (`WaitSFXDone: SFX=84` blocking forever -- would only happen if `mesh.Begin()`/`Render()` threw before ever setting `ended`, an unhandled edge case) | `revert_thomas.py` immediately; the debug menu (`~`) may force past a stuck command state; worst case, full restart then revert |
| The cinematic is missing beats / looks re-timed vs. the real Bahamut cast | The splice landed on the wrong anchor or duplicated `ef227/Sequence.seq`'s content (the `SkipSequence=True` guard failed) | Re-diff the deployed `ef084/PlayerSequence.seq` against the printed diff above; confirm no second `EffectPoint` pair fires (double damage numbers) |

## Revert

```
py studies/custom-summons/thomas-swap/revert_thomas.py
```

or equivalently `py studies/custom-summons/thomas-swap/build_thomas.py --restore`. Both put `ef084/`
back to **rung 7's own proven resting state** by reading rung 7's three committed source files
directly (`rung7-creature/FileList.txt`, `creature_manifest.sfxmodel`, `rung7_player_sequence.seq`)
and deploying them itself, and fully remove Thomas's GEO mint (`Models/3/6200/` + its `3DModel`
DictionaryPatch line; unlike rung 7's own Iviv-clone asset, which pre-existed this study and is never
any of these scripts' to manage, Thomas's mint is wholly new content this build introduced). Does not
touch `ef227/` (the shared Bahamut donor -- never written by this build in the first place),
`ef084/Sequence.seq` / `RisingRing.sfxmodel` (rung 3/5's leftovers, inert either way), or Iviv's own
GEO 6100 asset.

**Pre-existing bug found (RESOLVED 2026-07-22 -- and the diagnosis above-the-fold here was wrong in
an instructive way):** `rung7-creature/build_rung7.py --restore` raised a `DriftError` on every
invocation, and this build routed around it by deploying rung 7's three committed sources itself.
The constant (`RUNG6_BARE_SEQ_SHA256`) was in fact **correct** -- it matches the committed blob at
every commit that ever touched `rung6-bare-sequence/bare_player_sequence.seq`. What drifted was the
**checkout**: `core.autocrlf=true` smudged the committed LF bytes to CRLF on checkout (37 LF→CRLF
rewrites, 1833→1870 bytes), and `git status` shows such a file as *clean* because autocrlf's clean
filter reverses the smudge before comparing -- which is exactly why the original session here
concluded "file unmodified, so the constant must be computed wrong". Fixed by marking
`*.seq`/`*.sfxmodel` `-text` in `.gitattributes`, restoring the six affected study assets from
their blobs, and teaching `build_rung7.py`'s guard to diagnose the CRLF-smudge case by name. This
build's own `restore()` path is unchanged (self-contained verification remains the simpler
dependency).

## Provenance -- LOCAL ONLY

- **Third-party bytes** (`Thomas the Tank Engine.fbx`, `Thomas_d.png`, and every derived file --
  `thomas_normalized.fbx`, the Blender render PNGs, the deployed `6200.fbx`/`Thomas_d.png`) live
  ONLY under `C:/gd/SCRATCH/thomas/` and the live game install's `FF9CustomMap/` mod folder --
  **never** under `C:/gd/Dream-World-IX/` (this repo). The repo's `.gitignore` blanket-ignores
  `*.fbx`/`*.glb`/`*.gltf` (an accidental commit is structurally near-impossible), and no script in
  this directory ever writes a path under the repo root for asset bytes.
- **The five files in this directory** (`blender_normalize.py`, `thomas_manifest.sfxmodel`,
  `thomas_player_sequence.seq`, `build_thomas.py`, `revert_thomas.py`, this README) are 100%
  hand-authored text -- zero Square-Enix bytes, zero third-party asset bytes. `thomas_manifest.sfxmodel`
  references Thomas's model purely by his minted GEO NAME (`GEO_MON_B0_M200`), the same way any
  `.seq` op references a resource by id/name.
- **The real stock `ef227/PlayerSequence.seq`** this build splices is fetched fresh from the user's
  own install every run (sha256-drift-guarded) and is **never** written into the repo -- the
  rung2/3/4 provenance convention, unchanged.
- This build is explicitly **not for public/shared distribution** -- it is a local-only promo-video
  prop per the mission. Nothing here should be committed to the public repo, and this README says so
  even though `build_thomas.py` was never asked to be, and was not, committed.

## Mint details (this session's actual run)

- GEO id **6200**, name `GEO_MON_B0_M200`, type_int 3 (`mon` group → `Models/3/6200/`).
- `3DModel 6200 GEO_MON_B0_M200` appended to `FF9CustomMap/DictionaryPatch.txt` (line 67; the only
  other custom `3DModel` line, `6100 GEO_MAIN_B0_M100`, is Iviv's own pre-existing clone, untouched).
- Deployed `6200.fbx` (101,084 bytes) + `Thomas_d.png` (94,533 bytes) under
  `FF9CustomMap/StreamingAssets/Assets/Resources/Models/3/6200/`, both sha256-verified byte-identical
  to their `C:/gd/SCRATCH/thomas/` sources on readback.
