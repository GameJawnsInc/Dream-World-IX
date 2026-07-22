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
only his BODY mesh is suppressed (his own swirl/beam/fire-column EFFECT meshes are deliberately
KEPT -- see "HideMeshes: the s47 surgical key list" below) and Thomas is layered in alongside it.

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
+PlaySFX: SFX=Bahamut__Full ; Reflect=True ; HideMeshes=0,1,2,...,31
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

### 1. `HideMeshes=<HIDE_KEYS>` -- the s47 surgical key list

`PlaySFX`'s own `HideMeshes` argument (`BattleActionCode.cs:394-419 TryGetArgMeshList`) is parsed
into `SFXData.RunningInstance.preventedMeshIndices` (`SFXData.cs:136-154,1376-1392`) and honored
**only at the final draw step**, `SFXDataMesh.Runtime.Render()`'s `Graphics.DrawMeshNow` call
(`SFXDataMesh.cs:620-662`). Everything upstream of that draw call -- `Load(frame)`'s native
`SFX.SFX_Update` tick (which the camera track rides), `SFXRender.Update()`, and the camera-engine
arm at `Runtime.Begin()` (`SFXDataCamera.currentCameraEngine = SFX_PLUGIN`) -- runs completely
untouched every frame. `battle.cs:86`'s `SFXDataCamera.UpdateCamera()` call is a wholly separate,
unconditional-per-frame call site that only reads that static flag -- it has no dependency on the
mesh-draw walk at all. Net effect: the real Bahamut camera cut keeps running exactly as authored;
only the meshes actually named in `HideMeshes` stop rendering; unmatched keys are inert (no error).

`TryGetArgMeshList` splits each comma-separated token two ways: an `0x`-prefixed token parses as an
exact `UInt32` **key** (`SFXMeshBase._key`, stable for a mesh's whole lifetime) into `keyList`; a bare
decimal token parses as an **index** into the separate `indexList`. **This build now uses the key
form exclusively** -- superseding both the original blanket `HideMeshes=0..63` (2026-07-21, over-
suppressed: it also blanked Bahamut's own summon-swirl/beam/fire-column effect meshes) and its
index-range bisection successor (`HideMeshes=0,31`, an assume-body-is-the-low-half guess that was
never actually confirmed against the real index/key layout).

**The guess is gone.** The s47 mesh-stream probe (`memoria-patches/s47-sfx-mesh-probe.patch`;
PROBE.md) logs every native mesh's own `_key` + world-space bounds on every drawn frame. One
`--calibrate` cast (19,456 MESH rows across the whole ~40s cinematic) tallied to exactly **39
distinct keys**, classified in PROBE.md's round-1 results:

- **7 CREATURE/BODY keys** (present together on 301/325 of Bahamut's on-screen frames, 92.6% --
  tracing one coherent rigid-body flight): `0033B990`/`0033B9D0` (paired), `0035BAD0`/`0035BA90`
  (paired), `0034BA10`/`0034BA50` (paired), `0097BD02` (standalone). These are `HIDE_KEYS` in
  `build_thomas.py` -- Bahamut's body vanishes.
- **23 confirmed KEEP-VISIBLE effect keys** -- the cast-in swirl, the sky-act/ground-act backdrops,
  the wing-trail, the 6 charge-orb keys, the Mega-Flare beam, and the fire-column group (7 keys,
  incl. `00B7BD80` -- folded in this round by naming-pattern + z-band match with its sibling orb
  keys, see PROBE.md for the full per-key reasoning).
- **9 remaining keys of genuinely ambiguous classification**, all defaulted KEEP-VISIBLE this round
  (the safer choice over a blind hide) -- two of them (`00BDBE00`, `0098BD0E`) are live round-2
  candidates. See PROBE.md's round-1 results for the full per-key reasoning and its round-2
  refinement protocol for how to test each.

`build_thomas.py --hide-keys KEY1,KEY2,...` overrides `HIDE_KEYS` for one deploy (comma-separated
hex, `0x` prefix optional, e.g. `--hide-keys 0097BD01,0098BD0E` to test a round-2 candidate --
recast-only, no relaunch); `--calibrate` deploys with no `HideMeshes` argument at all (byte-identical
to the stock donor's own `PlaySFX` line -- Bahamut's real mesh renders completely unsuppressed, for a
fresh composition-reference cast/log). See PROBE.md for the full calibration-cast results, the
trajectory reconstruction this build's FLIGHT is derived from, and the round-2 protocol.

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

### THE FLIGHT v2 -- 2026-07-22, s47-PROBE-DERIVED (replaces the static hover, the 3-phase flight, AND the video-eyeballed 6-phase "SKY ARC")

The first (static) build's playtest: *"bahamut is invisible, but Thomas just spawns in front of Iviv
and stays stationary instead of flying around like a dragon. there are also just periods of black
screen."* The 3-phase flight fixed "stationary" but not "black screen" (Bahamut's own cinematic
leaves the ground for an extended sky-realm window the 3-phase flight never visited). The 6-phase
"SKY ARC" fixed that by watching the calibration-cast video and hand-deriving a video-seconds timing
map -- a real improvement, but still an EYEBALLED estimate, built entirely on caster-relative NCalc
expressions.

**This build replaces the eyeball with a measurement.** The s47 mesh-stream probe (PROBE.md) logged
Bahamut's own 7 confirmed body-mesh keys' world-space bounds on every one of the 325 frames he's on
screen (frames 82-417 of his own `PlaySFX`-zeroed clock) -- his ACTUAL baked flight path, not a
video-derived guess.

**Reconstruction method** (PROBE.md's round-1 results; independently re-verified against the raw log
while building this): per frame, take the median across the 7 creature keys of -- **X, Y: bounds
CENTER**; **Z: the FAR CORNER** (`center ± extent`, whichever side has the larger magnitude). The far
corner is essential for Z (the real body sits far enough from world origin that it reliably recovers
his true depth) but produces a noisy, silhouette-chasing signal on X/Y (which stay close enough to
origin that whichever wingtip/tail happens to be farthest that frame gets picked instead of the
body's own center) -- confirmed by a cross-check: raw CENTER `cy` stays in `[-480.5, +511.5]` across
all 8,764 creature-key rows, matching the probe's own independent "Y never exceeds ~512" cluster read
almost exactly.

**Absolute world coordinates** (a genuine design change from both prior builds, not just a retune):
every `Movement` `Origin*`/`Destination*` below is now a **plain numeric NCalc constant**, not a
`CasterPosition* + N` expression. `SFXMesh.Render()` draws via `Graphics.DrawMeshNow(_mesh,
Matrix4x4.identity)` -- no transform in play -- so the native donor's Raw mesh and Thomas's own JSON
mesh draw in the SAME identity world space; the bench arena is fixed, so an absolute coordinate puts
Thomas exactly where Bahamut's own body was measured, regardless of any caster-lookup quirk or this
scene's own camera framing.

**The measured flight** (10 pieces off real per-frame medians + 1 unmeasured tail, summing to
`THOMAS_END=580` unchanged) against the video-beat cross-reference the earlier builds derived by eye:

| Phase | Frames | Dest (X, Y, Z) | Video beat it covers | Interp |
|---|---|---|---|---|
| **P1 Entrance** | 0-82 | (132, 512, -1568) | pre-log swoop-in → the proven cave shots | SinusOut (decelerating arrival) |
| **P2 Rise-to-far** | 82-144 | (129, 128, -17860) | climbs away in DEPTH (Y barely drops, Z plunges) -- the first sky/far shot | SinusIn (accelerating launch) |
| **P3 Far-dip** | 144-157 | (6, -20, -8590) | a brief mid-act partial return (a 2nd camera-cut beat, e.g. a head close-up) | Sinus (floaty) |
| **P4 Far-deep** | 157-172 | (-266, -425, -34368) | the cast's single deepest point (Z=-34768 at frame 166) + a brief hold -- the iconic hover-pose shot | SinusIn |
| **P5 Return-cut** | 172-179 | (144, 47, -4864) | **THE hard cut** (Z snaps -34368→-4864 in ~7 frames) -- kept FAST/un-eased on purpose | Linear (no easing curve) |
| **P6 2nd-approach** | 179-204 | (143, 124, -12336) | a second, shallower re-plunge during the charge windup | Sinus |
| **P7 Charge-cut** | 204-207 | (152, 202, -4720) | a second hard cut back to near-stage | Linear |
| **P8 Charge-hold** | 207-250 | (120, 118, -3968) | Mega-Flare charge+blast -- **CORRECTION vs the 6-phase build**: stays NEAR-STAGE depth, not deep sky | Sinus |
| **P9 Ground-reign** | 250-414 | (35, -1, -3832) | fire column + both damage beats + undercarriage shots | Sinus |
| **P10 Exit-edge** | 414-417 | (35, -1, -9616) | body's last logged position -- a sharp final recess (Bahamut's own climb-away starting) | SinusIn |
| **P11 Tail (UNMEASURED)** | 417-580 | (35, 1600, -30000) | no creature-key rows exist here (only fire-column/ember effect keys, through ~510-515) -- a REASONED climb-away continuation | SinusIn |

Yaw (Rotation.Y) banks 0→90 (broadside) during P1's own arrival, HOLDS broadside from P2 through P10
(the mission's own instruction -- also his iconic number-1 side panel, per the axis-verification
renders), then 90→0 only in the TAIL as he turns forward again to climb away. Rotation.Z stays `0`
throughout -- no roll.

**Open concerns, carried forward (see `build_thomas.py`'s own `THE FLIGHT v2` comment block and
PROBE.md's round-2 protocol for the full detail):**
- **Corrected during adversarial verification:** P5_DEST/P7_DEST (frames 179/207) are each backed by a
  FULL n=28 rows -- solid points, not the sparse n=4 an earlier draft claimed. The real low-sample
  point is `P4_DEST` (frame 172, the deepest/most dramatic pose, n=4) and the gappy frames-153-177
  zone around it (several frames have zero creature-key rows logged at all) -- see PROBE.md's
  "Sample-count correction" section. P5/P7 are still kept short + `Linear` because the data shows a
  genuine large position delta over few frames, not because the endpoints themselves are uncertain.
- P1's Origin (frame 0, pre-log) and P11's Destination (frames 417-580) have ZERO measured ground
  truth -- both are documented reasoned extrapolations (`ENTRANCE_ORIGIN`, `P11_TAIL_DEST` in
  `build_thomas.py`), not measurements. A fresh video/log of THIS build would let round 2 replace
  either with real data.
- Clock alignment (probe-frame ≈ Thomas-frame, offset 0) is a reasoned assumption -- this calibration
  log predates Thomas entirely (no JSON-mesh key present in it) -- treat ±5-10 frames as realistic
  slop on every boundary above.

Every number above is a named constant in `build_thomas.py` (`P1_DEST`...`P10_DEST`, `ENTRANCE_ORIGIN`,
`P11_TAIL_DEST`, `YAW_BROADSIDE`, the 11 `*_DURATION`s) -- retune + rerun in one line, recast-only, no
relaunch.

No `Animations` array (Thomas is rigid, zero clips) -- confirmed safe by source: an FBX entry with an
absent `Animations` key renders the bind pose, no error (`SFXDataMesh.cs:976-977,809-810`); `Movement`
alone is sufficient to give a moving prop a well-defined enter/hold/exit window.

## Files in this directory

| File | What it is |
|---|---|
| `blender_normalize.py` | Committed, our script. Run ONCE (offline, via Blender) to produce `thomas_normalized.fbx` from the raw source. Never touches the repo. |
| `thomas_manifest.sfxmodel` | Committed, 100% our JSON -- **GENERATED** by `build_thomas.py`'s `build_manifest_json()` from the named `THE FLIGHT` constants (not hand-typed; the repo copy is kept in sync on every run so it stays git-diffable). Deployed as `ef084/creature_manifest.sfxmodel` (overwrites rung 7's Iviv-clone one there). |
| `thomas_player_sequence.seq` | Committed, 100% our text -- the splice DELTA (not a standalone sequence; see its own header comment). `build_thomas.py` inserts it into a runtime copy of the real stock donor. |
| `build_thomas.py` | Fetches the real donor fresh from the install (sha256-guarded, never committed), splices, mints Thomas's GEO, deploys everything. `--hide-keys KEY1,KEY2,...` overrides `HIDE_KEYS` for one deploy (the s47 surgical key list above), `--calibrate` deploys with no `HideMeshes` at all. `--restore` undoes it. |
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
correctly textured, and now FLYING THE MEASURED 11-PIECE FLIGHT (see "THE FLIGHT v2" above): swoops in
from high off to one side during the chant/flashes (P1, cave), climbs away in depth toward the first
sky/far shot (P2), a brief partial-return dip (P3), the deepest point + hover-pose hold (P4), a hard
cut back to near-stage (P5), a second shallower re-plunge (P6) and hard cut (P7), the Mega-Flare
charge+blast held near-stage (P8), the long floaty ground-reign hover through the fire column and both
damage beats (P9), a sharp final recess (P10), then a reasoned climb-away as the lights restore (P11,
unmeasured tail). Bahamut's own BODY mesh never appears at any point (his swirl/beam/fire-column
EFFECT meshes should still be visible -- that's the whole point of the s47-probe-derived `HIDE_KEYS`;
see "HideMeshes: the s47 surgical key list" above if they aren't), and no more standing stationary in
front of Iviv.

**If placement/motion/suppression is still off**: capture a short VIDEO of the cast (this project's
own law -- `feedback-video-for-visual-bugs` -- behavior/positional bugs need footage, not a prose
description; a screenshot can't show a swoop, and can only show ONE instant of the suppression state).
`tools/game_snap.ps1` captures single frames only, which is enough for "is Bahamut's body really
hidden RIGHT NOW" but NOT for "does the flight read as flying" or "are the effects still there
throughout" -- use a screen recorder (OBS, Xbox Game Bar `Win+Alt+R`, or any capture tool) for the
whole ~40s of the cast (chant through the flare through the exit), or re-run the s47 probe cast itself
(PROBE.md), so the next iteration can retune `build_thomas.py`'s named FLIGHT v2 constants (`P1_DEST`
through `P10_DEST`, `ENTRANCE_ORIGIN`, `P11_TAIL_DEST`, `YAW_BROADSIDE`, the 11 `*_DURATION`s) or
`HIDE_KEYS` from what actually happened frame-by-frame, rather than from a re-guess.

## Failure modes

| Symptom | Meaning | What to check |
|---|---|---|
| **Full cinematic plays, Thomas visible/huge/upright/textured, FLYING the measured 11-piece flight (cave → far/sky → cave → ground → exit), Bahamut's BODY mesh never appears, his swirl/beam/fire-column EFFECT meshes still do** | **SUCCESS** | -- |
| The cinematic plays with the REAL camera/sounds/timing, but **Bahamut's native BODY mesh is still visible** (Thomas may or may not also be there) | `HideMeshes` didn't suppress the native body. Now much less likely than the old index-range guess (the s47 probe's `HIDE_KEYS` are the exact, confirmed keys of Bahamut's own 7 body meshes -- PROBE.md's round-1 results), but still possible if this engine build's `_key` values differ from the probe's own cast (a fresh calibration cast would confirm), or the argument name/syntax is subtly wrong | Re-check the deployed `ef084/PlayerSequence.seq`'s `PlaySFX: SFX=Bahamut__Full` line byte-for-byte against the diff above; capture video (behavior bugs need it, not screenshots); re-run `--calibrate` + the probe to re-derive the keys if needed |
| Bahamut's body is correctly hidden, but **one of the kept effects (swirl/beam/fire-column/etc) also vanished** | One of `HIDE_KEYS`' 7 keys was misclassified as body when it's actually an effect (unlikely -- PROBE.md's round-1 classification found all 7 present together on 92.6% of frames, a strong rigid-body signal), or a round-2 candidate (`00BDBE00`/`0098BD0E`) was added to `--hide-keys` and turned out to be an effect after all | Capture video showing which specific effect is missing; drop the suspect key from `--hide-keys` and recast; see PROBE.md's round-2 protocol |
| The cinematic plays, Bahamut's body is correctly hidden, but **Thomas never appears** | Either (a) the FileList.txt/manifest didn't resolve (re-check `ef084/FileList.txt` + `creature_manifest.sfxmodel` bytes match what's printed above), or (b) `GEO_MON_B0_M200` didn't resolve to id 6200 -- **the relaunch didn't happen, or happened before this deploy** (re-run `build_thomas.py`, then relaunch), or (c) the two-SFX coexistence has an untested interaction specific to a background `StartThread` (rung 7 proved the FileList.txt route in the MAIN thread only, never inside a `StartThread` block) | Confirm the relaunch happened AFTER this deploy; re-run `build_thomas.py` and check "directive_added"/the DictionaryPatch line is present; check the game log if reachable |
| Thomas appears but **badly mispositioned** (off to one side, floating far away, only a sliver visible), OR the flight geometry just looks wrong for this arena's actual camera framing | Much less likely now that P1_DEST-P10_DEST are MEASURED off Bahamut's own real path (not guessed), but `ENTRANCE_ORIGIN` (frame 0) and `P11_TAIL_DEST` (frames 417-580) are still REASONED EXTRAPOLATIONS with zero ground truth -- see the CAVEAT in `build_thomas.py`'s `THE FLIGHT v2` comment block | Capture video (see above); if the measured pieces (P1-P10) look right but the unmeasured Origin/Tail look wrong, retune just those two constants and rerun (recast-only, no relaunch) |
| Thomas reads as **absurdly wide / clipped at the screen edges specifically during a REIGN piece** (P8 charge-hold or P9 ground-reign, not the transition pieces) | **Carried forward from earlier builds, NOT yet in-game-checked**: while his yaw is held at `YAW_BROADSIDE=90`, his ~2681-unit LENGTH sweeps world X (not Z) and only his ~926-unit WIDTH remains on Z -- neither reign piece's measured X range was sized with this axis swap in mind (they're MEASURED positions, so this is an inherent read of the real data, not a magnitude guess) | Capture video of both reign windows specifically; if confirmed, retune `YAW_BROADSIDE` toward 0/180 (keeps the long axis on Z) or accept a wider camera crop |
| Thomas still reads as **static / not "flying"** | Either this build didn't actually redeploy (rerun `build_thomas.py` and confirm the printed sha256 changed), or a phase's Duration is too short/subtle relative to what's actually visible during the donor's own blackout/flash windows | Capture video; check the deployed manifest's `Movement` array has 11 pieces (not 1, 3, or 6) via the printed sha256 or a direct read of `ef084/creature_manifest.sfxmodel` |
| Thomas appears **on his side / rotated 90°**, or the broadside yaw looks wrong (facing away instead of showing his profile) during any reign | The normalization step's core claim (baked, no runtime rotation needed) was wrong for this specific engine build, OR `YAW_BROADSIDE`'s sign is backwards for this camera angle -- re-open `blender_normalize.py`'s renders and the axis-verification table above | Compare against `view_front.png`/`view_top.png`/`view_side.png`; try `YAW_BROADSIDE = -90` in `build_thomas.py`, rerun (recast-only) |
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
