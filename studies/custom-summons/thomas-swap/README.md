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

### THE FLIGHT v9 -- 2026-07-23, MEASURED (CURRENT, supersedes v8) -- the creature's REAL screen path

**The breakthrough.** The s53 probe (PROBE.md §11) + the FORMAT round found why v5/v7/v8 all failed: the
creature projects through the plugin's own **native GTE** (world→view matrix `M` @0x1C1DC8 + OFX=160/OFY=120/H),
NOT the managed Unity VIEW/PROJ (retracted — it failed 88.7% of frames). Reading out one s53 cast
(`disasm/FORMAT.md` §5.4) settled it and, for the first time, **measured the creature's true per-frame screen
position** — reproject its composed node-0 (`*(DATA+0x38)`) through `M` + the GTE:
- the creature IS the single summon slot (`hasMotion=1` on `kind=S` only, 0 eff slots) — settled empirically;
- the reprojection lands ON-SCREEN with **ZERO false positives** (every on-screen frame also has the body mesh
  drawn) and **DEAD CENTER through the float/charge** (f288 ndc `(+0.00,-0.01)`, f300 `(0,0)`) — the exact
  phase v8 had Thomas *absent* for.

**v9 (`flight_v9_solve.py`, 334 keyframes):** for each reliable frame (82–412) it takes the creature's measured
native screen NDC and **back-projects it through the MANAGED camera** (the one that renders Thomas, a managed
Unity object) at `HEIGHT_FRAC=0.55` size — so Thomas lands where the real dragon was on screen, at a controlled
size. **One keyframe per frame** in the measured window (the creature's world position back-projects to a
different spot at each of the ~15 camera hard-cuts; interpolating across a cut is what swung the sparse version
111× off-frame — a keyframe/frame removes the interpolation, so cuts render as faithful 1-frame cuts). A
constructed lead-in flies him in from off-frame top; after frame 412 the creature stops being drawn (the camera
leaves for the fire column — the user's phase 4), so Thomas holds and drifts off. The measured window verifies
clean (0 high-drift segments, full camera coverage); the only "drift" is the intended off-screen exit.

**Caveat** (video-for-visual-bugs): this is the first flight built from a *measurement*, but the native→managed
handoff assumes native-NDC ≈ managed-NDC for the same on-screen pixel (true when both fill the same screen;
a 4:3-vs-widescreen mismatch would shift the horizontal — the centered float/charge is aspect-invariant either
way). A fresh capture is the real check. Re-derive: edit `flight_v9_solve.py`'s `HEIGHT_FRAC`/`NDC_CLAMP`, run
it, re-bake into `build_thomas.py`. Deployed 2026-07-23.

<details>
<summary>THE FLIGHT v8 -- 2026-07-23, HYBRID (superseded same day by v9 -- it was built on the RETRACTED +0x40 anchor + the managed VIEW/PROJ; kept for the record)</summary>

### THE FLIGHT v8 -- 2026-07-23, HYBRID: real entrance + constructed reign (was CURRENT, supersedes v7)

**What changed.** The s52 ROOT probe (PROBE.md §10) captured Bahamut's real per-frame world transform.
`root_reproject.py` + a camera-aim diagnostic established that the creature is actively posed (live ROOT)
for frames **82-301 (~43% of the cast** -- matching the user's own recollection of ~40% and a clean
4-phase structure: fly-down, swoop-by, float+charge with the camera ON him, then the camera pans OFF to
follow the fire column), then parks for the fire column. **But only the swoop-in (82-100) has a clean,
camera-VALIDATED ROOT→screen mapping** (camera aimed straight at it, `fwd·dir ≈ +0.97`, projects
on-screen). From ~108 on, the summon-model ROOT diverges hard from where the visible creature is drawn
(at the charge it sits ~40,000 units below/behind the camera) -- the FINDINGS §4 puzzle (a different draw
path, or a large draw-time world offset the probe can't see), so it is NOT a trustworthy placement source
there.

**The hybrid (`flight_v8_solve.py`, 27 keyframes, frames 0-580):**
- **Entrance (82-100): the REAL ROOT world positions** -- Thomas traces Bahamut's actual descent, growing
  naturally 18%→65% of frame as he approaches (measured, camera-validated). Trimmed at 100, not the full
  107, because the real creature swoops so close by 107 that Thomas would fill 167% of frame (a wall of
  train); a constructed lead-in brings him in from off-frame top ("flying down"). Push `ENTRANCE_REAL`
  toward 107 for a deliberately overwhelming close pass.
- **Swoop-by + float/charge (130-300): CONSTRUCTED** via v7's proven NDC back-projection to the user's
  4-phase spec -- a visible lateral swoop-by, then a BIG (62-66% frame) center-stage float held through
  the charge (the beat the user wants Thomas present for). Drift-verified in-frame (21/21 segments,
  worst |ndc| 0.70).
- **Fire column (340-580): world-HOLD** -- Thomas holds his phase-3 world position and the camera pans
  away onto the fire column, carrying him out of frame naturally (faithful "the camera moves off him";
  deliberately not drift-guaranteed -- he is meant to exit).

Yaw is per-keyframe broadside to each frame's real camera (his side/"1" panel to the lens), unwrapped for
continuity -- unchanged from v7. `THOMAS_SCALE=265` throughout (apparent size is controlled by the
per-keyframe depth/height solve, and by the real depth in the measured entrance). **Caveat** (this
project's video-for-visual-bugs law): this is a DESIGN verified against the real camera log's geometry
plus the user's own description of the cinematic -- a fresh capture of an actual cast is the real next
check. Re-derive/retune: edit `flight_v8_solve.py`'s `ENTRANCE_REAL`/`BEATS_AFTER`/`PHASE4_FRAMES`, run
`py flight_v8_solve.py`, and re-bake into `build_thomas.py` (the constant is generated, not hand-typed).
Deployed 2026-07-23.

<details>
<summary>THE FLIGHT v7 -- 2026-07-22, IN-FRAME BY CONSTRUCTION (superseded 2026-07-23 by v8 -- pure construction, no real data; its NDC back-projection + drift machinery is REUSED by v8; kept for the record)</summary>

### THE FLIGHT v7 -- 2026-07-22, IN-FRAME BY CONSTRUCTION (THE FINAL PRAGMATIC ROUND, supersedes v1-v5)

**The pivot -- user-accepted trade.** FLIGHT v5 (below, collapsed) was internally SOUND: Thomas is an
ordinary Unity GameObject whose world position is force-set every frame (`SFXDataMesh.cs:820`) and
rendered by the normal pipeline under the real per-frame camera, so projecting his world position through
the s50 probe's logged VIEW/PROJ correctly predicts where he lands on screen (empirically corroborated
against the user's own video). But v5's premise -- "faithful = wherever Bahamut's own body was, off-screen
swoops included" -- makes a promo clip that is mostly EMPTY: `matrix_solve.py`'s own self-test measures
only ~4/323 (1.2%) of Bahamut's own measured frames landing on-screen; the deployed v5 build scored ~2.7%
(9/336) on-screen coverage end to end. Separately, this round also tried TRACKING Bahamut's own real
position via the native PS1-primitive stream directly (rather than the mesh-bounds proxy) -- **FALSIFIED**:
no stable discriminator isolates his creature in the raw primitive stream (independent methods disagree,
latch onto backdrop planes), and the two video-confirmed beats (swirl entrance, fire column) contain ZERO
body-key primitives. The goal is now explicit and different: **THOMAS VISIBLE AND DRAMATIC THROUGHOUT** --
a promo shot, not a fidelity exercise. The user accepted this trade.

**What stays sound (unchanged from v5, re-used verbatim -- not re-derived).** The captured per-frame
`camera.worldToCameraMatrix` (VIEW) / `camera.projectionMatrix` (PROJ) pair from the s50 probe IS the real
render camera for this cast, and a world point projects through it correctly. Only "where do I put Thomas"
changes -- not the projection math (`flight_v7_solve.py`, this dir, imports `matrix_solve.py`'s
`project_world_to_ndc`/`world_from_ndc` directly, no reimplementation).

**The method -- construct in NDC, back-project to world.** For each of 18 authored story beats spanning
frames 0-580 (a swooping entrance from a frame edge, a big center-stage reign with gentle bob/drift through
the mid + charge, a slow lateral pass, staying BIG AND PRESENT through the fire-column/aftermath window
430-540 -- the beats the user specifically liked, no receding/climbing away there unlike v5's old exit
piece -- then a short exit at the very end):

1. author a target on-screen position `(ndc_x, ndc_y)`, comfortably inside frame (`|ndc| <= ~0.55`), and a
   target apparent HEIGHT fraction of the frame (`~45-65%`);
2. solve the camera-space depth that makes Thomas's own scaled height (`4.913 * 265 ≈ 1301.9` units) fill
   that fraction under THAT FRAME's real `PROJ[1][1]` (the vertical focal term sweeps `~2.33..4.65` across
   the cast -- the PROJ zoom means the SAME height fraction needs a DIFFERENT depth at every beat, per the
   mission's own emphasis: `depth = PROJ[1][1] * height_scaled / (2 * height_frac)`);
3. back-project `(ndc_x, ndc_y, view_z=-depth)` through that frame's real VIEW+PROJ with
   `matrix_solve.world_from_ndc` (the general off-center-frustum inverse, round-trip verified exact);
4. derive a per-keyframe YAW from the camera's own forward vector (`-VIEW[2,:3]`, the row negated) so
   Thomas presents broadside to THAT frame's actual camera -- closing the "fixed yaw drifts as the camera
   pans" open item both v4 and v5 left unresolved (a fixed `YAW_BROADSIDE` constant no longer applies once
   the camera's own heading is known to swing wildly, see below).

**Why 62 keyframes, not ~14-18 -- an honest, MEASURED deviation, not scope creep.** The mission's own
drift-margin language ("dense enough that between-keyframe drift cannot wander out of frame") reads as
assuming a camera that pans/zooms *smoothly*. Directly checking a hand-picked ~16-beat arc against the REAL
camera log refutes that assumption for this cast: `flight_v7_solve.camera_eye_census` finds **15 single-
FRAME eye jumps over 2000 world units** (real hard cuts, e.g. `f177->f178` jumps 18,960 units in ONE frame)
interleaved with sustained fast continuous dolly/orbit shots (hundreds of units per frame for tens of
frames, e.g. the `f178-f236` charge-windup shot). The first straight attempt -- 18 hand-picked beats,
Linear-in-world between them -- blew the `|ndc|<1` on-screen envelope by **10-75x on more than half its
segments** when checked against the real intermediate-frame cameras (not a rounding error -- a wrong
premise: linear-in-world only tracks linear-in-camera, and this camera is not remotely linear). Rather than
ship that and call 16 keyframes "dense enough," `flight_v7_solve.py` ADAPTS: the 18 authored beats remain
mandatory story waypoints (each still lands as a real keyframe at its own authored ndc/height -- their
labels survive verbatim into the final table), and any segment between two beats whose real-camera drift
would exceed `DRIFT_LIMIT=0.85` is **recursively bisected**, inserting an extra keyframe at the intended
screen-position lerp of the two flanking points (solved to world the same way as every authored beat) --
verified per segment, not assumed. The result: **62 total keyframes, 61/61 final segments within the 0.85
margin, worst point anywhere 0.83** (`flight_v7_solve.py`'s own drift-verification pass). 44 of the 62 are
these adaptive "(auto -- drift insert)" keyframes; every one is a measured necessity against the real log.
The fire-column/aftermath window (430-540) the user liked turned out to fall in one of the CALMER stretches
of this camera's motion -- it needed zero drift-inserts at all (`430->470->510` are both 40-frame gaps that
already passed the check directly), so Thomas stays big and steady there by construction, not by luck.

**Interpolation is Linear everywhere -- deliberately, not an oversight.** No `Sinus`/`SinusIn`/`SinusOut`
appears anywhere in the deployed `Movement`/`Rotation` arrays. The drift verification above was performed
assuming Linear interpolation between consecutive keyframes; introducing easing on any segment would make
the DEPLOYED runtime path diverge from the path that was actually checked, silently invalidating the
in-frame guarantee for that stretch. This isn't a visible loss -- the adaptive bisection already packs
keyframes densely wherever the real camera moves fastest (e.g. 8 keyframes inside the first 30 frames of
the entrance), so the swoop-in and the exit both already read as smooth multi-point curves, not abrupt
2-point teleports.

**Orientation and Scaling, unchanged in spirit from v5.** `ShiftWorld` is still a non-issue (Thomas's
`transform.position` is force-assigned in absolute world space every frame, never parented under
`battlebg.btlRoot`) -- world coordinates are used verbatim. `Scaling` stays one constant piece at
`THOMAS_SCALE=265` throughout (unchanged from every prior FLIGHT version -- apparent on-screen size is now
controlled entirely through the per-keyframe DEPTH solve, not by varying the scale itself; `THOMAS_SCALE`
must stay in sync between `build_thomas.py` and `flight_v7_solve.py`, both currently 265, cross-referenced
in each file's own header comment).

**Caveat.** Per this project's own video-for-visual-bugs law, a fresh capture of an actual cast is the real
next check -- everything above is a DESIGN verified against the real camera log's OWN geometry
(`matrix_solve.py`'s projection math + `flight_v7_solve.py`'s drift check), not a claim to have watched it
play. Re-derive/retune with `py flight_v7_solve.py` (edit the `BEATS`/`ENTRANCE_NDC`/`DRIFT_LIMIT`
constants at the top of that file, rerun, paste its printed `KEYFRAMES_V7` table into `build_thomas.py`).
Deployed 2026-07-22 (`creature_manifest.sfxmodel` sha256
`0e34c27758d3ad98bdb360c4500f5ce61225269331731d3b116f22dd3b3c447b`).

<details>
<summary>THE FLIGHT v5 -- TRACK BAHAMUT (superseded 2026-07-22 by v7 -- v5 was technically sound but reads as mostly off-screen; kept for the record)</summary>

### THE FLIGHT v5 -- 2026-07-22, TRACK BAHAMUT (THE FINAL SOLVE, supersedes v1-v4)

**The corrected target (user insight).** The real Bahamut cinematic DELIBERATELY swoops the creature
off-screen while the camera pans to follow his blast -- the subject is intentionally entering/exiting
frame at points. So faithfulness is NOT "keep Thomas centered/in-frame every frame" (that would be *less*
faithful than the dragon he replaces); an always-in-frame check is WRONG. **Faithfulness = Thomas is
wherever Bahamut was, every frame, off-screen swoops included.**

**What overturned FLIGHT v4.** v4 was built on the premise that the render camera is STATIC -- the s48 CAM
hook logged an unchanging `Camera.transform`. The **s50 probe disproves it**: it logs the actual
per-frame render matrices (`camera.worldToCameraMatrix` = VIEW rows, `camera.projectionMatrix` = PROJ
rows -- the very matrices `SFX.UpdateCamera()` assigns at `SFX.cs:1603-1604`), and they are anything but
static. The logged CAM Transform is a **decoy** (nothing writes it per-frame -- exactly the ambiguity
`viewspace_place.py`'s own `render_camera_confirmed` note flagged); the VIEW matrix **pans/orbits**
dramatically frame to frame, and PROJ **zooms** (its `[1][1]` focal term sweeps ~2.33..4.65, i.e. vertical
FOV ~47deg..24deg). v4's "assumed fixed 40deg camera" rested on a premise the raw matrices refute.

**The solve -- placement is camera-INDEPENDENT.** Thomas is rendered by that *same* per-frame camera
(`ef227`'s native camera track replays byte-identically every cast). So we model no camera at all: **place
Thomas at Bahamut's own measured world position each frame, and the real per-frame VIEW+PROJ reproduces
his exact screen position -- pan, zoom, off-screen swoop and all -- for free.** No FOV assumption, no
projection guess. `matrix_solve.py`'s forward projection *verifies* the off-screen beats are real: of
Bahamut's 324 on-cast body frames, only ~5 project strictly inside `|ndc|<1` -- his body is genuinely
off-screen / behind the camera for most of the cast (the camera follows the effect/blast, not the
creature). That's the deliberate behavior the user described, reproduced by copying his world path
verbatim.

**How the numbers are derived (`matrix_solve.py`).** Per frame, Bahamut's world position = the MEDIAN
across his 7 body-mesh keys of (X = bounds `cx`, Y = bounds `cy`, Z = the FAR CORNER `cz -/+ ez`) -- the
pool-pollution heuristic (PROBE.md round 1): the SFX vertex pool sits at world origin, so the AABB
stretches from the real body toward 0; on Z the body is thousands of units out so the far corner recovers
true depth, while on X/Y it sits near origin so the center is the better estimate. A windowed median
(+/-6 frames) suppresses single-frame pooling spikes. The result is a coherent flight: he starts near
(Z~=-1700), **dives far away** (Z~=-18000..-30000 around frames 120-166 -- keys agree tightly there, and
the dive is independently corroborated by the older s47 cast's own ~-34000 reading), then returns to a
moderate Z~=-4000..-7000 for the reign/charge/fire-column window through frame 417.

**The manifest** (`build_thomas.py`'s `TRACKED_KEYFRAMES` + `ENTRANCE_ORIGIN`/`EXIT_DEST`): 30 Movement
pieces -- an entrance (frames 0-82, off-screen origin -> Bahamut's first measured position, SinusOut);
the measured **track** (82-417, 29 keyframes sampled every ~12 frames, Linear between -- the body moves
smoothly in world space, so Linear between dense samples is faithful; the apparent screen cuts/swoops come
from the baked camera, for free); an exit (417-580, climb-away, SinusIn). Rotation holds broadside
(YAW=90) through the track. Durations sum to `THOMAS_END=580`. Only `ENTRANCE_ORIGIN`/`EXIT_DEST` are
reasoned-without-ground-truth (the body is absent outside 82-417); everything in the track is measured.
Re-derive/retune with `py matrix_solve.py --step 12 --window 6`. Deployed 2026-07-22
(`creature_manifest.sfxmodel` sha256 `8a5b3e59c44b60cbaddbba8f69d202f8548e95a09c1c74f7dfa5ab35fbe6445a`).

**Known open item.** With the camera now known to pan wildly, a fixed world yaw does not hold a constant
facing to the lens -- a per-frame camera-relative yaw is now COMPUTABLE from the VIEW rows (`matrix_solve`
exposes them) and is the obvious next refinement if his facing reads wrong on video. Left out of this pass
to keep the FINAL SOLVE about POSITION (the headline). Per the project's video-for-visual-bugs law, a
fresh capture of an actual cast is the real next check.

<details>
<summary>THE FLIGHT v4 -- VIEW-SPACE CHOREOGRAPHY (superseded 2026-07-22 by v5 -- the static-camera premise it rested on was disproved by the s50 probe; kept for the record)</summary>

### THE FLIGHT v4 -- 2026-07-22, VIEW-SPACE CHOREOGRAPHY (supersedes FLIGHT v3's mesh-derived placement)

**The premise underneath every prior FLIGHT version turned out not to hold.** FLIGHT v1-v3 all placed
Thomas at coordinates measured from *Bahamut's own real body position* (the s47 mesh probe's per-frame
medians), on the assumption that wherever Bahamut's body was, the real camera must have been framing
it. This round's own recon fixed the s48 CAM-hook defect (PROBE.md §9) and re-cast: **the logged camera
is completely static across all 561 frames** -- world position `(0, 1000, -4500)`, `eulerAngles(10, 0,
0)` -- verified byte-exact against `BattleMapCameraController.cs:26-30`'s `SetDefaultPsxCamera2()`
directly in the engine source. Bahamut's apparent swoop was never camera motion; it's his own creature
moving through world space while a fixed viewpoint watches. That's good news for placement (a known,
fixed anchor!) but it retroactively undermines the *method*: Bahamut's measured position was framed by
whatever the real per-frame *native* projection was doing (`camera.worldToCameraMatrix`/
`.projectionMatrix`, overridden directly every single frame, `SFX.cs:1603-1604` -- properties this
static Transform pose never reflects either way, confirmed dead end to recover, same as
`ef_camera_solve.py`'s own NO-GO below). So FLIGHT v1-v3's absolute constants were never actually
checked against any camera model -- they just happened to be wherever Bahamut's mesh was, a different
claim.

**THE FIX: construct, don't infer.** `viewspace_place.py` (this dir, committable) implements
`world = cam_pos + R(cam_euler) @ (sx*depth*tan(hfov/2), sy*depth*tan(vfov/2), depth)` against the one
camera anchor that IS on record. Its own module docstring carries the full recon trail (re-verified
directly against the live engine source this round, not merely cited):

- **`fov_projection` -- no literal per-frame FOV in degrees exists, confirmed.** The battle camera runs
  in `CameraEngine.SFX_PLUGIN` mode for the whole fight (`SFX.cs:1634-1642`); every frame,
  `SFX.UpdateCamera()` (`SFX.cs:1590-1605`) assigns `camera.worldToCameraMatrix`/`.projectionMatrix`
  DIRECTLY from a native 13-float array -- `Camera.fieldOfView` is never touched. The projection is a
  hand-built off-center frustum (`PsxCamera.PsxProj2UnityProj`, `PsxCamera.cs:172-178`, verified this
  round): `left=-HalfScreenWidth, right=+HalfScreenWidth, bottom=-100, top=+120` (from
  `FieldMap.PsxScreenHeightNative=220`, verified) fed through `PerspectiveOffCenter`
  (`PsxCamera.cs:122-149`), whose `[0,0]` entry is `2*near/(right-left)` -- i.e. the frustum's angular
  half-width is literally `atan(HalfScreenWidth/near)`, and `near` is `SFX.fxNearZ`
  (`SFX.cs:1599 fxNearZ = array[12]`, overwriting a throwaway `100f` default at `SFX.cs:17` every
  frame) -- a **dynamic, native-plugin-owned value with no static table**, the exact same
  runtime-scratch-buffer dead end `ef_camera_solve.py` already hit for the anchor position. The
  frustum's absolute ANGLE is therefore unrecoverable -- but its SHAPE (aspect + the vertical
  bottom:top split) IS, because both axes share the same unknown `near` and the ratio cancels it.
- **`render_camera_confirmed` -- yes, with the caveat this whole design is built around.** The
  `BattleMapCameraController` GameObject IS the resolved render camera (15+ call sites share the same
  `Camera.main ?? "Battle Camera"` fallback), but nothing in the codebase ever writes its
  `.transform.position`/`.rotation` per frame -- only `worldToCameraMatrix`/`.projectionMatrix`
  (`SFX.cs:1603-1604`). "The logged Transform never changed" is consistent with either "the camera
  genuinely never moves" or "nothing ever updates a Transform that was never the real per-frame eye" --
  the log can't distinguish the two, and this design doesn't pretend to.
- **`shiftworld_effect` -- confirmed NO-OP for Thomas.** `battlebg.ShiftWorld()` only ever moves
  `btlRoot` (background art/props, `battlebg.cs:407-455,11-40`); Thomas's own FBX token gets its
  `transform.position` force-assigned in absolute world space every single frame
  (`SFXDataMesh.cs:820`), immune to a parent-local offset regardless of parenting -- and he's never
  parented under `btlRoot` in the first place. **`view_to_world()`'s output is used verbatim, no
  compensation.**
- **`euler_convention` -- Unity's fixed native order, verified against this codebase's own decomposition.**
  `R = Ry(yaw) * Rx(pitch) * Rz(roll)` applied to a column vector -- `PsxCamera.cs:78-86
  RotationMatrix2EulerAngle` is the textbook decomposition of exactly that product, no local override.
  For this camera's actual pose (yaw=roll=0) the ordering is moot regardless -- pure-pitch rotation.

The absolute FOV **magnitude** is therefore an explicitly-named, freely-retunable ASSUMPTION
(`viewspace_place.DEFAULT_VFOV_DEG = 40.0`, aspect `16:9` -- Memoria's own `WidescreenSupport` defaults
to `True`, `Graphics.cs:75`, verified this round, which rescales the live frustum to the player's own
window aspect rather than the boxed 320:220 native one), never claimed as recovered -- placing Thomas in
view space GUARANTEES he lands at the chosen screen fraction *relative to that assumed model*, by
construction, which is strictly stronger than FLIGHT v3's un-checked absolute constants and honestly
weaker than a claim to have recovered the true per-frame eye (a confirmed, not merely unresolved, dead
end).

**Orientation, computed against this camera's own basis:** the camera's `forward` vector at this pose is
`(0, -sin(10°), cos(10°))` -- mostly world +Z (`cos(10°) ≈ 0.985`), the SAME general direction Thomas's
own neutral yaw=0 nose points (his face is at local/world +Z at yaw=0, per the axis-verification above).
A camera looking the same direction an actor's nose points sees that actor's BACK -- so `YAW_BROADSIDE`
(unchanged value, 90, now justified against this camera's own basis rather than assumed) turns him to
present his iconic side profile. `build_thomas.py` prints the actual computed dot product
(`YAW_FORWARD_DOT ≈ +0.9848`) as evidence, not assertion. No Z-roll in any piece.

**The view-space flight** (8 pieces, replacing FLIGHT v3's 13 -- durations sum to `THOMAS_END=580`,
unchanged, matching the donor's own `WaitSFXDone`-gated cast length). Each `VS_*` keyframe is
`(sx, sy, depth_factor)` -- screen fractions (`+1`=right/top edge of the assumed frustum) and a
multiplier on `REIGN_DEPTH` (the camera-space distance at which Thomas's ~1302-unit HEIGHT -- not his
length, which lies along world X once broadside, see the failure-mode table below -- fills
`TARGET_REIGN_FILL=0.72` of the frame's vertical extent, i.e. squarely inside the mission's own
"fill 60-80% of frame height" ask):

| Piece | Frames | (sx, sy, depth×) | World dest (X, Y, Z) | Interp |
|---|---|---|---|---|
| ENTRANCE_ORIGIN | (P1 Origin) | (-1.35, +0.55, 2.40×) | (-5208, 1247, 1597) | -- |
| **P1 Entrance** | 0-90 | (-0.25, +0.10, 1.35×) | (-542, 549, -1174) | SinusOut |
| **P2 Approach-to-reign** | 90-150 | (+0.05, -0.05, 1.00×) | (80, 528, -2061) | SinusIn |
| **P3 Reign bob (up)** | 150-195 | (+0.10, +0.10, 0.95×) | (153, 682, -2160) | Sinus |
| **P4 Reign bob (down)** | 195-240 | (-0.02, -0.12, 1.05×) | (-34, 445, -1949) | Sinus |
| **P5 Lateral pass** | 240-340 | (+0.55, -0.05, 1.00×) | (884, 528, -2061) | Sinus |
| **P6 Reign bob (settle)** | 340-430 | (0.00, +0.02, 0.98×) | (0, 596, -2099) | Sinus |
| **P7 Reign hold** | 430-490 | (-0.08, -0.06, 1.02×) | (-131, 510, -2013) | Sinus |
| **P8 Exit climb** | 490-580 | (+1.15, +1.25, 3.20×) | (5915, 3505, 4013) | SinusIn |

(World-dest column is `viewspace_place.view_to_world()`'s literal output, rounded -- reproduced exactly
by `thomas_manifest.sfxmodel`; `REIGN_DEPTH ≈ 2484.1` units at the default `vfov=40°`.) Reading the
table left to right: an off-edge **entrance** descending into a near-center settle; an **approach** push
in to full reign size; a **gentle breathing bob** (up then down) through the mid-cast windup; an
**optional slow lateral pass** across the frame "for life" during the charge; a **settle back toward
center** for the ground-reign/fire-column/damage-beat window; a brief **steady hold**; then an
**exit climb** toward a top corner, receding, as the outro fades in.

**Known, inherited trade-off (carried forward, not new):** at full reign size and `YAW_BROADSIDE=90`,
Thomas's ~2681-unit LENGTH sweeps world X while only his ~926-unit WIDTH remains on Z -- at
`REIGN_DEPTH≈2484`, his half-length alone (`≈1340`) already exceeds the assumed frustum's own horizontal
half-extent at that depth. **He is expected to read as overflowing the frame's sides during the REIGN
pieces even though he's correctly sized to the requested 60-80% frame HEIGHT** -- the mission's own fill
target is a height target, and a giant broadside train is wider than it is tall. This is the same
trade-off FLIGHT v3's own failure-mode table already flagged (not a new bug); retune `YAW_BROADSIDE`
toward 0/180 (keeps the long axis on Z instead) or increase `TARGET_REIGN_FILL`'s divisor (push
`REIGN_DEPTH` out) if it reads badly in a real capture.

**Caveat:** this is a DESIGN, not a measurement -- there is no ground truth to check it against (the
donor's real per-frame render state is the same confirmed-unrecoverable native scratch buffer
throughout this whole study). It fully supersedes FLIGHT v1-v3's mesh-derived waypoints (see the
collapsed history below) -- those described where Bahamut's body WAS, a different question from where
Thomas should be FRAMED once the camera model is understood to be this static assumed one. Every
constant (`VS_*`, `TARGET_REIGN_FILL`, `vsp.DEFAULT_VFOV_DEG`, the 8 `*_DURATION`s) is named and
retunable in one edit, recast-only, no relaunch. Per this project's own video-for-visual-bugs law, a
fresh capture of an actual cast is the real next check.

<details>
<summary>FLIGHT v2 + FLIGHT v3 + the camera-DLL-solve attempt (all superseded 2026-07-22, kept for the record)</summary>

**FLIGHT v2** (11 pieces): the s47 mesh-stream probe (PROBE.md) logged Bahamut's own 7 confirmed
body-mesh keys' world-space bounds on every frame he's on screen, giving 10 real per-frame-median
waypoints + 1 unmeasured tail -- a genuine improvement over the earlier hand-eyeballed builds, but it
had no way to tell a real camera CUT from a fast in-shot reposition, and guessed cuts at frames 172-179
and 204-207 (modeling both `Linear`/un-eased) that a later camera decode found don't actually exist.

**FLIGHT v3** (13 pieces, "CAMERA-DECODE REWINDOWED"): `ef_camera_decode.py` (this dir) parsed the REAL
native `ef227.bytes` camera container (open managed code: `SFXBinaryFile.cs`'s container spec,
byte-exact validated; `SFXDataCamera.cs`'s Code-stream reader) and found Bahamut Cinema is exactly 3
real camera shots with hard cuts at absolute tick 258 and 483 -- NOT at 172-179/204-207 where the
mesh-position method had guessed. It kept FLIGHT v2's same measured `P1_DEST`..`P10_DEST` XYZ values
(the decode couldn't recover a literal eye/aim world position -- SFXDataCamera's spherical Position
format has no open-code conversion to it, that runs inside the closed native plugin) and only corrected
the piece BOUNDARIES/EASING to match the real cut timing: P5/P7 re-eased Linear→Sinus (no real cut
covers them), P8 extended 8 ticks to reach the real shot boundary, a new `CUT1` piece carried the
P8→P9 delta as the one deliberate fast snap, a new `P10_Hold` bridged to the real 2nd cut, and the
unmeasured tail's climb-away start moved from tick 417 to 483.

**THE CAMERA DLL SOLVE ATTEMPT** (`ef_camera_solve.py`, this dir): re-disassembled the closed
`FF9SpecialEffectPlugin.dll` (pefile+capstone) trying to recover a literal per-frame eye/look-at and
close the "compute yaw from the eye→Thomas vector" gap for real. **Verdict: NO-GO, confirmed, not
guessed** -- 22 of ef227's 27 keyframes key their anchor into a runtime-populated scratch buffer (a PE
section-table read proved the target RVA has zero bytes backing it on disk -- 1.9MB into `.data`'s
6.1MB `VirtualSize`, but `.data`'s own `SizeOfRawData` is only ~104KB), so no further static
disassembly recovers it. A proxy reconstruction (substituting the s47 probe's own measured Bahamut
position as the anchor) validated only as a coin-flip on directional sanity (9-below/14-above of 24).
This NO-GO is what THE FLIGHT v4 (above) is built on top of, rather than around.

</details>

### THE FLIGHT v4 ADVERSARIAL VERIFICATION -- 2026-07-22 (frustum re-projection + Euler-order fix)

Re-projected the 8 deployed `Destination*` keyframes (plus the entrance origin) back through the static
camera via `viewspace_place.py`'s own inverse math, and full-body-extent edges at all 7 "reign" keyframe
centers, then swept the whole 0-580 range at 5-frame steps checking every sampled position for
behind-camera (depth<=0):

- **Zero behind-camera samples** across the entire 580-frame range (step-5 scan, 117 samples).
- **Center positions**: all 7 reign destinations (P1-P7, frames ~90-490) land inside the assumed
  frustum (`|sx|<=1, |sy|<=1`); the `ENTRANCE_ORIGIN` (frame 0) and `P8_DEST` (frame 580) are off-frame
  by construction (`sx=-1.35/+1.15`, `sy=+0.55/+1.25`) -- exactly the documented, deliberate
  entrance/exit design (`is_in_view()`'s own docstring: "expected and fine ... an entrance origin or an
  exit destination"), not a defect. The actual on-camera window measures roughly frames 31-552 (~90% of
  the 580-frame cast).
- **Height fill, recomputed independently**: at the P2/P5 reign depth (2483.9 units), Thomas's raw
  height (1301.9 = 4.913*265) fills **exactly 72.0%** of the frame's vertical extent -- matches
  `TARGET_REIGN_FILL` by construction, comfortably inside the mission's 60-80% band.
- **Body-edge overflow, reconfirmed (not new)**: at P5 (the lateral pass, `sx=+0.55`), Thomas's
  broadside length edge projects to `sx=+1.383` -- outside the frame on the right. This is the SAME
  trade-off already disclosed in this file's Failure-modes table and the build's own `open_concerns`
  (his ~2676-unit length vs. the horizontal half-extent at reign depth); re-derived independently here,
  not a fresh find. All other 6 reign keyframes' body edges (length AND width) stay inside frame.
- **Euler-order defect found and fixed**: `camera_basis()`'s docstring claimed `R = Ry(yaw)*Rx(pitch)*
  Rz(roll)` was Unity's native order and matched `PsxCamera.cs:78-86`'s own decomposition. Direct
  numeric round-tripping of that decomposition formula against all 6 possible axis-orderings shows the
  ACTUAL matching order is `R = Rz(roll)*Ry(yaw)*Rx(pitch)` (max error 1.1e-16 rad over 20 random-angle
  trials; the previously-claimed order was off by tens of degrees on the same trials). **Fixed in
  `camera_basis()`** -- and confirmed **inert for this specific deployment**: `CAM_EULER_DEG` has
  yaw=roll=0 exactly, so every one of the 6 orderings collapses to the identical pure-X `Rx(pitch)`
  matrix (the two zero-angle matrices are identity and drop out regardless of position in the product).
  Rebuilt after the fix: `thomas_manifest.sfxmodel` sha256 **unchanged**
  (`619f599921b467c55c65808efea68970cecefe49a13a9cfdd36dab33e62bdf09`, verified byte-identical
  pre/post-fix, both against the repo copy and the deployed `ef084/creature_manifest.sfxmodel`
  readback) -- proving the fix changed nothing observable today, only future-proofed the module against
  a camera pose with nonzero yaw/roll.
- **HideMeshes / manifest hygiene, reconfirmed**: deployed `PlayerSequence.seq` still carries the exact
  7-key surgical list (`0x0033B990,0x0033B9D0,0x0035BAD0,0x0035BA90,0x0034BA10,0x0034BA50,0x0097BD02`,
  unchanged); 8 Movement pieces / 8 Rotation pieces with matching per-piece durations summing to
  `THOMAS_END=580`; no `ShiftWorld` op present anywhere in the deployed `.seq` (not merely
  structurally-unreachable -- literally absent); no binary stock bytes committed to the repo (`*.fbx`
  gitignored, `.seq` in-repo is a splice-fragment-plus-documentation, never the full donor file).

</details>

</details>

</details>

</details>

No `Animations` array (Thomas is rigid, zero clips) -- confirmed safe by source: an FBX entry with an
absent `Animations` key renders the bind pose, no error (`SFXDataMesh.cs:976-977,809-810`); `Movement`
alone is sufficient to give a moving prop a well-defined enter/hold/exit window.

## Files in this directory

| File | What it is |
|---|---|
| `blender_normalize.py` | Committed, our script. Run ONCE (offline, via Blender) to produce `thomas_normalized.fbx` from the raw source. Never touches the repo. |
| `matrix_solve.py` | Committed, our script -- the shared projection library (FLIGHT v5's own solver, still load-bearing). Parses the s50 probe's per-frame VIEW/PROJ/MESH, builds the 4x4 render matrices (numpy), exposes `project_world_to_ndc`/`world_from_ndc` (forward + off-center-frustum inverse, round-trip exact) both module-level and as frame-based `ProbeLog` methods. FLIGHT v7 (`flight_v7_solve.py`) imports these primitives directly rather than reimplementing them; v5's own `TRACKED_KEYFRAMES`-style Bahamut-tracking self-test is superseded but the projection math it's built on is not. Standalone: `py matrix_solve.py` self-tests + prints the (superseded) Bahamut-tracking analysis. |
| `flight_v7_solve.py` | Committed, our script -- **THE FLIGHT v7 (IN-FRAME BY CONSTRUCTION) solver**, current. Authors 18 story-beat targets (screen position + apparent height), solves each to a real-camera depth + world position via `matrix_solve`, then recursively bisects any segment whose real-camera drift would leave the frame until every segment verifies. Prints the pasteable `KEYFRAMES_V7` table `build_thomas.py` bakes, plus the camera hard-cut census and the final drift-verification report. Standalone: `py flight_v7_solve.py`. |
| `thomas_manifest.sfxmodel` | Committed, 100% our JSON -- **GENERATED** by `build_thomas.py`'s `build_manifest_json()` from the FLIGHT v7 `KEYFRAMES_V7` constant (not hand-typed; the repo copy is kept in sync on every run so it stays git-diffable). Deployed as `ef084/creature_manifest.sfxmodel` (overwrites rung 7's Iviv-clone one there). |
| `thomas_player_sequence.seq` | Committed, 100% our text -- the splice DELTA (not a standalone sequence; see its own header comment). `build_thomas.py` inserts it into a runtime copy of the real stock donor. |
| `build_thomas.py` | Fetches the real donor fresh from the install (sha256-guarded, never committed), splices, mints Thomas's GEO, deploys everything. `--hide-keys KEY1,KEY2,...` overrides `HIDE_KEYS` for one deploy (the s47 surgical key list above), `--calibrate` deploys with no `HideMeshes` at all. `--restore` undoes it. Bakes `KEYFRAMES_V7` (from `flight_v7_solve.py`'s own printed table) -- no live dependency on either solver script or the probe log at build time. |
| `revert_thomas.py` | Alias of `build_thomas.py --restore` (house convention). |
| `viewspace_place.py` | Committed, our script -- **SUPERSEDED (v4, then v5, now v7).** Was FLIGHT v4's camera/projection model, built on an assumed-STATIC camera; the s50 probe disproved that premise. No longer imported by `build_thomas.py`; kept for the record. Its `render_camera_confirmed` docstring correctly flagged the very ambiguity v5/v7 resolved. |
| `ef_camera_decode.py` | Our script -- parses the REAL `ef227.bytes` native camera container (extracted fresh from `resources.assets` via UnityPy each run, never committed) to recover the 3 real camera shots/2 real cuts FLIGHT v3 (superseded, see the collapsed history above) windowed its pieces against. Standalone; not called by `build_thomas.py`. |
| `ef_camera_solve.py` | Our script -- reproduces the decompiled `FF9SpecialEffectPlugin.dll` spherical->Cartesian camera formula and validates it against `sfxmeshprobe.log`. Confirmed **NO-GO** (see the collapsed history above). Standalone; not called by `build_thomas.py`. Writes its own scratch-only CSV, never under this repo. |
| `README.md` | This file. |

None of these files contain Square-Enix bytes or third-party asset bytes -- see "Provenance."

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

**Expect**: the full real Bahamut cinematic plays -- same chant, same camera cuts, same roars/flashes,
same damage timing -- but the creature on screen is **Thomas the Tank Engine**, huge, upright, correctly
textured, and now **VISIBLE AND DRAMATIC THROUGHOUT** (FLIGHT v7, see "THE FLIGHT v7 -- IN-FRAME BY
CONSTRUCTION" above): a swooping entrance from a frame edge, a big center-stage reign with gentle bob and
a charge windup, a slow lateral pass, staying BIG AND PRESENT through the fire-column/aftermath window
(430-540 -- the beats the user specifically liked, no receding away there), then a short exit at the end.
His facing is now a PER-KEYFRAME broadside yaw computed against each frame's actual camera (not a fixed
world angle), so his presented side should track the lens reasonably even as the camera cuts. Bahamut's
own BODY mesh never appears at any point (his swirl/beam/fire-column EFFECT meshes should still be
visible -- that's the whole point of the s47-probe-derived `HIDE_KEYS`; see "HideMeshes: the s47 surgical
key list" above if they aren't), and no more standing stationary in front of Iviv.

**If placement/motion/suppression is still off**: capture a short VIDEO of the cast (this project's
own law -- `feedback-video-for-visual-bugs` -- behavior/positional bugs need footage, not a prose
description; a screenshot can't show a swoop, and can only show ONE instant of the suppression state).
`tools/game_snap.ps1` captures single frames only, which is enough for "is Bahamut's body really
hidden RIGHT NOW" but NOT for "does the flight read as flying" or "are the effects still there
throughout" -- use a screen recorder (OBS, Xbox Game Bar `Win+Alt+R`, or any capture tool) for the
whole ~40s of the cast (chant through the flare through the exit), so the next iteration can retune
`flight_v7_solve.py`'s `BEATS` (per-beat ndc/height targets), `ENTRANCE_NDC`, or `DRIFT_LIMIT`, rerun it,
and re-paste its printed `KEYFRAMES_V7` table into `build_thomas.py`, from what actually happened
frame-by-frame rather than from a re-guess.

## Failure modes

| Symptom | Meaning | What to check |
|---|---|---|
| **Full cinematic plays, Thomas visible/huge/upright/textured, in-frame and dramatic throughout (swooping entrance, center-stage reign, lateral pass, big through the fire-column/aftermath, short exit), Bahamut's BODY mesh never appears, his swirl/beam/fire-column EFFECT meshes still do** | **SUCCESS** | -- |
| The cinematic plays with the REAL camera/sounds/timing, but **Bahamut's native BODY mesh is still visible** (Thomas may or may not also be there) | `HideMeshes` didn't suppress the native body. Now much less likely than the old index-range guess (the s47 probe's `HIDE_KEYS` are the exact, confirmed keys of Bahamut's own 7 body meshes -- PROBE.md's round-1 results), but still possible if this engine build's `_key` values differ from the probe's own cast (a fresh calibration cast would confirm), or the argument name/syntax is subtly wrong | Re-check the deployed `ef084/PlayerSequence.seq`'s `PlaySFX: SFX=Bahamut__Full` line byte-for-byte against the diff above; capture video (behavior bugs need it, not screenshots); re-run `--calibrate` + the probe to re-derive the keys if needed |
| Bahamut's body is correctly hidden, but **one of the kept effects (swirl/beam/fire-column/etc) also vanished** | One of `HIDE_KEYS`' 7 keys was misclassified as body when it's actually an effect (unlikely -- PROBE.md's round-1 classification found all 7 present together on 92.6% of frames, a strong rigid-body signal), or a round-2 candidate (`00BDBE00`/`0098BD0E`) was added to `--hide-keys` and turned out to be an effect after all | Capture video showing which specific effect is missing; drop the suspect key from `--hide-keys` and recast; see PROBE.md's round-2 protocol |
| The cinematic plays, Bahamut's body is correctly hidden, but **Thomas never appears** | Either (a) the FileList.txt/manifest didn't resolve (re-check `ef084/FileList.txt` + `creature_manifest.sfxmodel` bytes match what's printed above), or (b) `GEO_MON_B0_M200` didn't resolve to id 6200 -- **the relaunch didn't happen, or happened before this deploy** (re-run `build_thomas.py`, then relaunch), or (c) the two-SFX coexistence has an untested interaction specific to a background `StartThread` (rung 7 proved the FileList.txt route in the MAIN thread only, never inside a `StartThread` block) | Confirm the relaunch happened AFTER this deploy; re-run `build_thomas.py` and check "directive_added"/the DictionaryPatch line is present; check the game log if reachable |
| Thomas appears but **badly mispositioned or the wrong apparent size** at some point in the cast | The FLIGHT v7 depth/NDC solve for that keyframe was computed against `flight_v7_solve.py`'s own logged VIEW/PROJ for that frame -- if the engine's per-frame camera differs from the probe log this build was derived against (a different arena state, a stale/mismatched log), the solve would be off for that stretch. The drift-verification pass (61/61 segments, worst |ndc| 0.83) only guarantees the MEASURED log's own geometry, not a different session's | Capture video (see above); re-run `py flight_v7_solve.py` against a fresh `--calibrate` probe cast + re-paste `KEYFRAMES_V7` if the log has drifted; check specific keyframes' printed `ndc`/`height%`/depth against what's on screen at that frame |
| Thomas reads as **too wide / clipped at the screen edges** during a big center-stage or fire-column keyframe | His broadside LENGTH (~2681 units at `THOMAS_SCALE=265`) can exceed the frame's horizontal extent even when correctly sized to the target HEIGHT fraction -- the same trade-off every prior FLIGHT version disclosed (a giant broadside train is wider than it is tall) | Capture video of the specific keyframe; if it reads badly, lower that keyframe's `height_frac` in `flight_v7_solve.BEATS` (pushes depth out) or reconsider `THOMAS_SCALE`, rerun both scripts |
| Thomas still reads as **static / not "flying"** | Either this build didn't actually redeploy (rerun `build_thomas.py` and confirm the printed sha256 changed), or a piece's Duration is too short/subtle relative to what's actually visible during the donor's own blackout/flash windows | Capture video; check the deployed manifest's `Movement` array has 61 pieces via the printed sha256 or a direct read of `ef084/creature_manifest.sfxmodel` |
| Thomas appears **on his side / rotated 90°**, or the broadside yaw looks wrong at some keyframe | The normalization step's core claim (baked, no runtime rotation needed) was wrong for this specific engine build, OR the per-keyframe yaw's `+90` choice (vs. `-90`) reads backwards for that particular camera angle -- re-open `blender_normalize.py`'s renders and the axis-verification table above | Compare against `view_front.png`/`view_top.png`/`view_side.png`; try flipping the `+90.0` in `flight_v7_solve.broadside_yaw_deg` to `-90.0`, rerun both scripts (recast-only) |
| Thomas appears **tiny or absurdly, unusably huge** throughout | `THOMAS_SCALE` (265, must match between `build_thomas.py` and `flight_v7_solve.py`) was miscalibrated, or the two files' copies have drifted out of sync | Confirm both files' `THOMAS_SCALE` match; edit + rerun both (recast-only) |
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
- **The files in this directory** (`blender_normalize.py`, `thomas_manifest.sfxmodel`,
  `thomas_player_sequence.seq`, `build_thomas.py`, `revert_thomas.py`, `viewspace_place.py`,
  `ef_camera_decode.py`, `ef_camera_solve.py`, this README) are 100% hand-authored text -- zero
  Square-Enix bytes, zero third-party asset bytes. `thomas_manifest.sfxmodel` references Thomas's
  model purely by his minted GEO NAME (`GEO_MON_B0_M200`), the same way any `.seq` op references a
  resource by id/name.
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

---

## SESSION CLOSE 2026-07-22 — state, verdicts, and THE NEXT ROUND

**Paused here by the user.** Everything below is on `master`; the probe is disarmed
(`Memoria.ini [SfxProbe] Enabled = 0`); the v7 Thomas swap is left DEPLOYED on bench field 30300.

### What is PROVEN and shipped
- **The native-visual suppression lever** — `PlaySFX ... HideMeshes=<hex keys>` hides exactly
  Bahamut's 7 body meshes while every effect (swirl / flare / beam / fire column) still renders.
  First use of the op anywhere. In-game proven.
- **The creature substitution** — a third-party FBX (Thomas, GEO 6200) minted through the model
  pillar and rendered mid-cast via the rung-7 `FileList.txt` route, coexisting with the native
  donor effect in one cast. In-game proven.
- **s48 + s50 engine probes** (default-OFF, permanent debug-class tools): per-frame mesh keys +
  bounds, the decoded PS1 primitive stream, and the REAL per-frame camera (`worldToCameraMatrix` +
  `projectionMatrix`).

### What is FALSIFIED (do not retry as-is)
- **Tracking Bahamut by mesh bounds** — the `MESH` bounds are pool-polluted; the far-corner Z
  heuristic is *measurably* wrong (f142: real −7,688 vs estimated −18,800).
- **Tracking Bahamut by the primitive stream** — no stable discriminator isolates the creature from
  backdrop/effect geometry (independently reasoned methods disagree: 0/6, 0/10 vs 3/17; they latch
  onto screen-filling backdrop planes). Worse, the two video-confirmed beats (swirl entrance, fire
  column) contain **zero** body-key primitives — they fall outside the 82–417 body window entirely.

### What is DECODED (durable wins)
- **The primitive coordinate space**: a primitive's `(x0, y0, otz)` **IS** the mesh vertex the camera
  consumes — `SFXMesh` builds each vertex as `(x0+drOffsetX, y0+drOffsetY, GzDepth)`, source-proven.
- **The camera is real and moves**: VIEW pans/orbits, PROJ zooms vFOV 47°→24°. The `.transform` is a
  decoy nothing writes per frame.
- **15 CAMERA HARD CUTS** (single-frame eye jumps up to 18,960 world units) — this retroactively
  explains most of the v4/v5/v6 wandering: any smooth world path is framed before a cut and stranded
  after it.
- The DLL is a soft RE target: `SFX_UpdateCamera`'s real body at RVA 0x1e80; the camera anchor
  dispatch recovered byte-exact (`lookup_anchor` @ 0x1800148f0). Blocked only at a runtime-populated
  PS1-emulator scratch buffer (RVA 0x220060, zero bytes on disk).

### Current deployed state (v7) and its honest verdict
`FLIGHT v7` places Thomas **in frame by construction** (choreograph in NDC → back-project through
each frame's real VIEW/PROJ). Verified **100.00% on-screen coverage (551/551 camera frames)** vs the
v5 baseline 2.7%. **User verdict: in-frame, but "doesn't really look good and some parts are
missing."** So: coverage solved, *staging* not solved. v7 is a framing exercise, not a performance —
it does not know what the creature was DOING (pose, scale intent, which beat it belongs to).

### THE NEXT ROUND (user's stated intent): another disasm pass — how are these truly stored?
The remaining prize is the one thing every data-side approach failed to recover: **the creature's
real per-frame transform and geometry**. Concrete targets, in order:
1. **The `Hi_Summon*` subsystem** inside `FF9SpecialEffectPlugin.dll` (~12 functions:
   `Hi_RegisterSummonModel` / `Hi_SetSummonMotion` / `Hi_GetSummonBoneMatrix` / `Hi_DrawSummonModel`
   / …). This is where the creature's model + motion actually live. Decoding
   `Hi_GetSummonBoneMatrix` alone would give Bahamut's true per-frame transform — which is exactly
   what tracking needs, and what neither mesh bounds nor primitives could supply.
2. **The open puzzle worth solving first (cheap, and it gates interpretation):** why do the native
   primitives NOT project sanely through the captured VIEW/PROJ, when the source says they are plain
   mesh vertices under those matrices? Resolving this may show the effect renders through a second
   path/space — and would validate or void every projection-based conclusion here.
3. **Only then**: whether a creature can be swapped at the *source* level (feed our own model into
   the summon pipeline) instead of the current hide-native + overlay-ours composition.

**Provenance for that round:** reading the DLL to UNDERSTAND is sanctioned (PLAN §3A Route D). A
committable format *parser* is fine; extracted stock creature geometry is NOT (gitignore/local only,
the battle-import precedent). Never ship a patched/redistributed DLL.

### Reproduce / revert
- Rebuild + deploy v7: `py studies/custom-summons/thomas-swap/build_thomas.py`
- Back to the rung-7 resting state: `py studies/custom-summons/thomas-swap/revert_thomas.py`
- Re-arm the probes: `Memoria.ini [SfxProbe] Enabled = 1` (+ `CapturePrims = 1` for the primitive
  stream) — **needs a game relaunch**, the flags are cached at process start.

---

## DISASM ROUND COMPLETE 2026-07-22 — the summon subsystem is decoded → `disasm/FINDINGS.md`

The disasm pass the SESSION CLOSE queued **ran and closed** (a 10-agent Opus workflow over
`FF9SpecialEffectPlugin.dll` + the open Memoria source, standing on the committed instrument
`disasm/refkit.py`; 23 load-bearing claims adversarially re-derived, 1 corrected; every native claim
cites `fn@rva`, every managed claim `file:line`). Full report: **`disasm/FINDINGS.md`**; per-slice
trail: `disasm/{A1..A5,B1..B5}-*.md`; verification trail: `disasm/V-*.md`. **No stock bytes were
extracted; the DLL was only read — provenance-clean.** Headline results:

- **A stock summon is a software PS1-GTE renderer inside the DLL.** The whole `summonModels[]`
  pipeline is decoded: a **one-slot** record array @RVA **0x220830** (stride **0x58**) → a `SummonData`
  block (motion `+0x10`, **hide-mask `+0x20`**, per-bone WORLD matrices `+0x38`, **root world TRS
  `+0x40`**, texanim `+0x70`), driven by a mega-interpreter @0xeea4 through a `.data` dispatch table.
  Cross-checked byte-for-byte on the x86 build. The 12-fn `Hi_Summon*` roster is mapped to real
  bodies (e.g. `Hi_GetSummonBoneMatrix` @**0x18630**, independently re-disassembled by the orchestrator).
- **THE PRIZE IS RECOVERABLE — the staging problem is solvable.** The creature's true per-frame world
  transform is **`SummonData+0x40`** (bone[0] of the `+0x38` array). It is **zero-on-disk** (no static
  recovery) and crosses **no managed boundary**, but it is **live-readable by a passive memory read** of
  the plugin's own runtime state: `moduleBase(FF9SpecialEffectPlugin) + 0x220830 → +0x00 → +0x40`.
  No DLL patch, no P/Invoke-by-name, no asset bytes.
- **The primitive-space puzzle is settled (and it VOIDS the old MESH-bounds premise).** `SFX_GetPrim`
  returns **already-projected 2D screen pixels + an ordering-table sort key** (the perspective divide
  happens inside the DLL, `idiv @0x4001b`); the metric transform never escapes. So every prior method
  that read the probe's **MESH `cx,cy,cz` bounds as Bahamut's world position** was reading a
  pool-polluted origin-anchored box (vertCount≡14000, origin in 100% of AABBs) — **that is why
  `matrix_solve.py`'s "put Thomas at Bahamut's measured world position" scattered off-screen.** The
  creature's per-frame **screen** trajectory *is* recoverable — from the un-pooled **`PRIM`** rows, not
  MESH bounds. Deployed FLIGHT v7 (constructs coverage directly) is **not** invalidated.
- **The camera is fully solved and retired as a blocker.** VIEW+PROJ cross the boundary cleanly every
  frame; the zoom is a single near-Z scalar `H`; `resolve_position`'s K=4096.8 branch-A is re-confirmed.
  The eye/anchor scratch buffer @0x220060 is runtime-only but **unneeded** — VIEW+PROJ + the root read
  fully place a puppet (`screen = PROJ · VIEW · root`, same PS1-GTE world space).
- **Native `Hide/ShowSummonModelMesh` (`DATA+0x20` ordinal bitmask) ≠ our `.seq HideMeshes=`
  (SFXKey-hash filter after harvest)** — two different culling layers. The native op is exact and
  emission-free but reaching it needs its `.seq` opcode number decoded (a next-step item).

**THE SINGLE NEXT ACTION (recommended, not yet taken — needs the user's go-ahead):** land the **ROOT
probe** — a ~45-line managed extension to `Memoria/Battle/SFX/SfxMeshProbe.cs` that reads `SummonData+0x40`
each frame (gated on a new `[SfxProbe] CaptureRoot=1` flag) + a **reprojection-validation** pass (project
the read root through the same frame's logged VIEW/PROJ, compare to the `PRIM` centroid). One instrumented
cast then yields Bahamut's **real metric trajectory** to hang the rung-7 Thomas puppet on — closing the
staging problem v7 left open. **Caveats:** it is on the `memoria-patches/` stack, so it is an **engine DLL
rebuild (auto-deploys, no backup — the DANGEROUS lane) + a relaunch + a human playtest cast** to be useful;
log the **root only** (dumping the per-bone `+0x38` array across a cast = extracting stock animation =
BLOCKED). Runway after: re-stage FLIGHT on the captured ROOT curve → decode the native Show/Hide `.seq`
opcode → the `.seq` summon-op linter/inspector (`disasm/FINDINGS.md` §6-7).

*Round hygiene:* two map agents (A4 primitive-space, B5 x86-crosscheck) hit the structured-output retry
cap but **wrote their `.md` artifacts first**, so their content is on the blackboard and was folded into
`FINDINGS.md`; A3 returned a schema-stub as its structured claims but likewise wrote the real 19KB
`A3-managed-boundary.md`. No content was lost.
