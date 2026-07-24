# M1a BUILD PLAN — camera-inheritance + body-hide + depth-residual, ZERO new engine code

**Status: PLAN ONLY.** Nothing in this document has been deployed; no mod-folder file, no
`Memoria.ini`, and no engine DLL was touched while writing it. All facts below about "what is
currently live" were gathered by **read-only** inspection of the install; all facts about "what
M1a needs" are a design against the study's own already-committed mechanism (`build_thomas.py`
v10.1), not new engine work. Per TRANSPLANT.md §2.4, M1a's job is the smallest possible thing that
isolates *camera inheritance* from the (much harder) hybrid-motion question: hold our own FBX at
one static point inside the REAL Bahamut donor cast, hide the native body, and watch whether the
native camera's cuts/zooms/pans read on our static model exactly as they do on the real creature.

---

## 1. Current deployed bench state

No `.ff9deploy.toml` exists in this worktree (it's gitignored/per-worktree; this worktree never
created one), so every deploy tool in the kit falls back to its documented default
(`mod_folder="FF9CustomMap"`, confirmed live by directly listing the install — see below). The
game install resolved via `~/.ff9mapkit.toml`:

```
game_path = C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX
mod root  = <game>/FF9CustomMap
```

**Read-only inventory of `<mod>/StreamingAssets/Data/SpecialEffects/`:**

| path | state |
|---|---|
| `ef227/` | **does not exist in the mod folder** — the real stock Bahamut donor is untouched, exactly as every prior rung has left it. |
| `ef084/FileList.txt` | `Model creature_manifest.sfxmodel` (rung 7's own file, byte-reused, unchanged since rung 7) |
| `ef084/creature_manifest.sfxmodel` | **88,264 bytes** — byte-identical to the repo's `thomas_manifest.sfxmodel` (v10.1's `KEYFRAMES_V10`-generated flight: 333 keyframes, per-frame Movement/Rotation pieces, one constant `Scaling` piece at `THOMAS_SCALE=265`, `Start=0`/`End=520` — the deployed manifest's own `"End": "520"`, verified by grep; see the §2.2 note on `THOMAS_END`'s stale code comment) |
| `ef084/PlayerSequence.seq` | the **v10.1 splice**: donor `ef227/PlayerSequence.seq` (sha256 `4bc643bf…`, verified byte-identical to `EXPECTED_DONOR_SHA256` this session) with `thomas_player_sequence.seq`'s `StartThread…EndThread` block inserted immediately before the anchor line, and the anchor line itself patched to `PlaySFX: SFX=Bahamut__Full ; Reflect=True ; HideMeshes=0x0033B990,0x0033B9D0,0x0035BAD0,0x0035BA90,0x0034BA10,0x0034BA50,0x0097BD02` (the 7 s47-confirmed body keys — full text below in §2) |
| `ef084/Sequence.seq`, `ef084/RisingRing.sfxmodel` | rung 3/5 leftovers, inert, not this build's to manage |
| `Models/3/6200/6200.fbx` + `Thomas_d.png` | Thomas's minted GEO, present |
| `DictionaryPatch.txt` | `3DModel 6200 GEO_MON_B0_M200` **already registered** (line 62 of 68) — so **no relaunch is needed for M1a**, only for the first-ever mint, which already happened |

**This is `build_thomas.py`'s default (`--thomas`) output — the current build is "FLIGHT v10.1"**,
produced by whatever the most recent bare `py build_thomas.py` run was. It is *not* rung-7's own
resting state (that would have `Start=0/End=60`, a single fixed-point Movement, and an
`Animations` array referencing `Animations/6100/1010000` — rung 7's asset, Iviv's skinned clone,
GEO 6100 — none of which is present in the deployed manifest above).

**Bench identity (unchanged, confirmed against README.md):** field **30300** (`TESTROOM`-style
custom field, `FieldScene 30300 11 TEST30300 TEST30300 30300` in `DictionaryPatch.txt`), random
encounter scene **67**, ability path **Iviv → Spark → Bahamut Cinema**, native donor effect id
**227** (`Bahamut__Full`), our private folder **ef084** (rung 3/7's fresh id, reused, never
re-minted).

**Probe/engine state (relevant to §4):** `Memoria.ini [SfxProbe]` currently has
`Enabled=1 CaptureRoot=1 CaptureModels=1 ModelsActiveOnly=1 ModelsCap=120000 ModelsBoneCount=93`
— **no `CapturePrims`/`PrimSummary`/`PrimCap` lines**. The live engine DLL
(`x64/FF9_Data/Managed/Assembly-CSharp.dll`, sha256 `3CCA581C…`) matches `memoria-patches/README.md`'s
s53 row exactly, which is built **on top of** s52/s48/s47 — and `memoria-patches/README.md`'s own
s48 row says `CapturePrims` was **★ BUILT + DEPLOYED 2026-07-22** ("the CAM hook now logs +
`CapturePrims` works"). **This means `CapturePrims` is already compiled into the live DLL — arming
it is a pure `Memoria.ini` edit + relaunch, no engine rebuild.** Flagged for the record:
`PROBE.md` §9 still says s48 is "CODED, NOT YET BUILT" — that line is **stale**; `memoria-patches/README.md`
is the newer, authoritative build log and should be trusted over it (see §4 below).

---

## 2. The exact M1a build

### 2.1 What does NOT change

- **`ef084/PlayerSequence.seq`** — byte-identical to what's live today (§1). M1a needs the exact
  same splice: the real donor's own `LoadSFX: SFX=Bahamut__Full ; Reflect=True ; UseCamera=True`
  line (unmodified — this is what arms the real cinematic camera), a background `Sync=False`
  thread that loads/plays/holds our own id 84 in parallel, and the anchor `PlaySFX` line carrying
  the same 7-key `HideMeshes=`. Nothing about M1a's *mechanism* differs from v10.1's — only the
  **content of the manifest** (§2.2) changes. Full current text (for the record, `4bc643bf…`-donor-verified):

  ```
  WaitAnimation: Char=Caster
  SetVariable: Variable=cmd_status ; Value=&65533 ; Reflect=True
  StartThread: Condition=CasterRow == 0 && AreCasterAndSelectedTargetsEnemies ; Sync=True
  	MoveToPosition: Char=Caster ; RelativePosition=(0, 0, 400) ; Anim=MP_STEP_FORWARD
  	WaitMove: Char=Caster
  EndThread
  StartThread: Condition=IsSingleSelectedTarget
  	Turn: Char=Caster ; BaseAngle=AllTargets ; Time=5
  EndThread
  Message: Text=[CastName] ; Priority=1 ; Title=True ; Reflect=True
  SetupReflect: Delay=SFXLoaded
  LoadSFX: SFX=Bahamut__Full ; Reflect=True ; UseCamera=True
  PlayAnimation: Char=Caster ; Anim=MP_IDLE_TO_CHANT
  WaitAnimation: Char=Caster
  PlayAnimation: Char=Caster ; Anim=MP_CHANT ; Loop=True
  Channel
  SetBackgroundIntensity: Intensity=0 ; Time=12
  WaitSFXLoaded: SFX=Bahamut__Full ; Reflect=True
  WaitAnimation: Char=Caster
  StopChannel
  PlayAnimation: Char=Caster ; Anim=MP_MAGIC
  WaitAnimation: Char=Caster
  StartThread: Condition=1 == 1 ; Sync=False
  	LoadSFX: SFX=84 ; Char=Caster ; UseCamera=False
  	WaitSFXLoaded: SFX=84
  	PlaySFX: SFX=84 ; SkipSequence=True
  	WaitSFXDone: SFX=84
  EndThread
  PlaySFX: SFX=Bahamut__Full ; Reflect=True ; HideMeshes=0x0033B990,0x0033B9D0,0x0035BAD0,0x0035BA90,0x0034BA10,0x0034BA50,0x0097BD02
  WaitSFXDone: SFX=Bahamut__Full ; Reflect=True
  SetVariable: Variable=cmd_status ; Value=|2 ; Reflect=True
  ActivateReflect
  WaitReflect
  StartThread: Condition=CasterRow == 0 && AreCasterAndSelectedTargetsEnemies ; Sync=True
  	MoveToPosition: Char=Caster ; RelativePosition=(0, 0, -400) ; Anim=MP_STEP_BACK
  	WaitMove: Char=Caster
  EndThread
  PlayAnimation: Char=Caster ; Anim=Idle
  Turn: Char=Caster ; BaseAngle=Default ; Time=5
  WaitTurn: Char=Caster
  ```

- **`ef084/FileList.txt`** — unchanged (`Model creature_manifest.sfxmodel`).
- **The GEO mint** (`3DModel 6200 GEO_MON_B0_M200`, `Models/3/6200/{6200.fbx,Thomas_d.png}`) —
  unchanged; already registered, no relaunch needed.
- **`HIDE_KEYS`** — the same 7 s47-confirmed body keys, unchanged. M1a is not the round to also
  test the two round-2 candidates (`00BDBE00`, `0098BD0E`) — that's an orthogonal refinement
  (PROBE.md's "round 2 refinement protocol") and would confound the camera-inheritance read if
  bundled in.

### 2.2 What DOES change — `creature_manifest.sfxmodel`

Replace the 333-keyframe `KEYFRAMES_V10` flight with **one static hold spanning the whole cast**.
Proposed content (schema per `ParametricMovement.LoadFromJSON`, same as today's manifest, just
one piece per array instead of hundreds):

```json
{
  "FBX": [
    {
      "Path": "GEO_MON_B0_M200",
      "Start": "0",
      "End": "520",
      "Movement": [
        {
          "Duration": "520",
          "OriginX": "132.5", "OriginY": "511.5", "OriginZ": "-1568",
          "DestinationX": "132.5", "DestinationY": "511.5", "DestinationZ": "-1568"
        }
      ],
      "Rotation": [
        {
          "Duration": "520",
          "OriginY": "0", "DestinationY": "0",
          "OriginZ": "0", "DestinationZ": "0"
        }
      ],
      "Scaling": {
        "Duration": "520",
        "OriginX": "265", "OriginY": "265", "OriginZ": "265",
        "DestinationX": "265", "DestinationY": "265", "DestinationZ": "265"
      }
    }
  ]
}
```

Notes on every value:

- **`End=520`** — matches the CURRENTLY DEPLOYED manifest's own `"End": "520"` (verified by direct
  grep of the live file), i.e. the donor's `WaitSFXDone`-gated cast length as v10.1 actually ships
  it today. **Flag for the record:** `build_thomas.py`'s own source comment on `THOMAS_END` reads
  `# 580 -- donor's WaitSFXDone-gated cast length, unchanged`, but `THOMAS_END = KEYFRAMES_V10[-1][0]`
  evaluates to **520** (the last `KEYFRAMES_V10` tuple is `(520, (2236,10356,-5384), +119.60)`, not
  580) — the comment is stale documentation drift, not a live discrepancy (the code and the
  deployed artifact agree at 520; only the inline comment disagrees with both). Worth a one-line
  fix in `build_thomas.py` whenever that file is next touched, but out of scope for this plan. M1a
  should use the real value, 520, not the comment's stale 580. The background thread's
  `PlaySFX: SFX=84` holds our model for `[Start,End)`; if `End` is shorter than the real cast, our
  model would vanish/reset while Bahamut's real `WaitSFXDone: SFX=Bahamut__Full` is still pending
  and the effects (fire column etc.) keep playing — a visible, confusing defect unrelated to what
  M1a is testing. Keep 520.
- **The static point `(132.5, 511.5, -1568)`** — this is **not invented**. It's the already-measured
  `P1 dest ("entrance settle")` row from PROBE.md's own trajectory-reconstruction table (§8): the
  median, across Bahamut's 7 real body-mesh keys, of his own on-screen world position at frame 82
  — the exact instant the real creature first becomes visible and the camera settles on him after
  the cave-entrance swoop. It is genuine Unity **world space**: the s47 probe's `MESH` rows are
  `mesh.bounds` read off a `Graphics.DrawMeshNow(mesh, Matrix4x4.identity)` call, i.e. object space
  *is* world space for that draw — the same world space `SFXDataMesh.cs:820` force-assigns to our
  own FBX's `Transform.position` every frame. So this is a like-for-like reuse of a real, already-
  published measurement, not a new guess, and it's deliberately chosen because it's a moment the
  *real* camera is independently known to be holding/settling on the creature — the best available
  single point to maximize the odds Thomas is actually inside frame when the test begins.
  **Caveat, stated plainly:** Bahamut's own trajectory swings across four other recurring beats in
  roughly the same X/Y/Z neighborhood — 2nd-approach (frame 204, `143,124,-12336`), charge-hold
  (frame 250, `119.5,117.5,-3968`), ground-reign (frame 414, `34.5,-0.8,-3832`) — and diverges wildly
  during the sky-charge excursion (frames ~150–233, Z out to −34,768 and beyond). A single static
  point being near-frame at 4 of ~11 story beats and clearly off-frame during the sky excursion is
  the **expected, informative** result, not a bug to fix — see §3.
- **Rotation `OriginY=DestinationY=0`** — an explicit non-claim. Nothing in this study has measured
  Bahamut's own body *facing* at frame 82 (PROBE.md's table only reconstructs position), and
  `KEYFRAMES_V10`'s own yaw values are solved for a *different*, per-frame back-projected screen
  target — reusing one of those numbers here would look measured but wouldn't correspond to
  anything. `0` matches `blender_normalize.py`'s own normalized facing convention (the FBX's
  "front" as authored). If Thomas visibly faces the wrong way in the settle shot, this is a
  **cosmetic, non-blocking** fix (rotate by eye), not a finding — M1a's claims are about camera
  framing/cuts/zooms and body-hide/depth, not facing direction.
- **No `"Animations"` key.** This is not a simplification choice — Thomas's FBX genuinely has **no
  skeleton and no clips** (`build_thomas.py`'s own docstring: "Thomas's raw third-party FBX is
  fully rigid (no skeleton…)"; confirmed by inspecting the deployed manifest — it has never carried
  an `Animations` array, unlike rung 7's own Iviv-clone manifest, which repeats
  `"Path": "Animations/6100/1010000"` six times because *that* asset is skinned). "Our model plays
  only its own idle" for this specific asset degenerates to: **static geometry, no clip, held at
  rest pose** — see §5 for why this matters for M1b.
- **`Scaling` unchanged at 265** — keep the same physical scale v10.1 already uses, so a visual
  before/after against the currently-deployed build isolates exactly one variable (motion vs. no
  motion), not two (motion and size).

### 2.3 Proposed code change (not applied — plan only)

Add a third mode to `build_thomas.py`'s existing `--thomas` / `--restore` mutually-exclusive
group, parallel to how `--calibrate` already overrides `hide_keys` for one deploy:

```python
group.add_argument("--m1a", action="store_true",
                    help="deploy the M1a static-hold manifest instead of the FLIGHT v10 KEYFRAMES_V10 "
                         "flight -- one fixed Movement/Rotation piece spanning the whole cast, no "
                         "Animations array (Thomas has no clips). Same .seq splice, same HIDE_KEYS, "
                         "same mint as --thomas. Isolates camera-inheritance from flight-matching.")
```

`build_manifest_json()` gains a sibling `build_manifest_json_m1a()` returning the literal dict in
§2.2 (or a tiny `M1A_STATIC_POINT = (132.5, 511.5, -1568)` constant it renders from, mirroring
`_pt()`'s existing helper); `build_thomas()` takes a `manifest_fn` parameter (default
`build_manifest_json`) so `main()` passes `build_manifest_json_m1a` when `args.m1a` is set. No
other function changes — `splice_sequence`, `patched_line`, `mint_thomas`, `HIDE_KEYS` are reused
verbatim, exactly as intended by "reuse rung-7 verbatim, ZERO new engine code."

### 2.4 Deploy / revert commands

**Deploy** (game may be open or closed — no relaunch needed; the mint is already registered):

```
py studies/custom-summons/thomas-swap/build_thomas.py --m1a
```

Writes only `ef084/creature_manifest.sfxmodel` to a new (static-hold) value; `PlayerSequence.seq`,
`FileList.txt`, and the mint are re-written byte-identical to what's already live (idempotent).

**Revert to the CURRENT v10.1 state** (not rung-7 — per the task's explicit requirement):

```
py studies/custom-summons/thomas-swap/build_thomas.py
```

The bare, no-flag default mode. Since `--m1a` changes nothing except which manifest-builder
function is called, running the script with no flags regenerates the full `KEYFRAMES_V10`
manifest and re-splices the identical `PlayerSequence.seq` with the default `HIDE_KEYS` — i.e. it
reproduces exactly today's §1 inventory, byte-for-byte (this is already how `build_thomas.py` is
idempotent today; re-running it with no args is the documented way to reassert v10.1 after any
experiment, e.g. after a `--calibrate` or `--hide-keys` test run).

**Nuclear option (back past v10.1, to rung-7's own pre-Thomas resting state, mint fully removed)** —
unchanged, already exists, not what M1a's own revert needs:

```
py studies/custom-summons/thomas-swap/revert_thomas.py
```

---

## 3. What success and failure look like

**Test procedure** (README.md's existing bench recipe, unchanged): load the bench save, get into
the field-30300 random encounter (scene 67), cast **Iviv → Spark → Bahamut Cinema**, let the whole
~40s cast play through.

**SUCCESS — camera inheritance holds:**
- Thomas (a small rigid train model) is visible, static in **world space**, but his **on-screen**
  size/position/framing visibly changes as the real cinematic camera cuts, dollies, and zooms
  through its ~15 hard cuts and continuous push-ins — e.g. he might read centered and mid-size in
  one shot, then a hard cut reframes him toward a screen edge or off-screen entirely, then a later
  cut/dolly brings a *different* apparent size or angle on the exact same static point. That
  apparent motion, with zero world-position change on our side, **is** the proof: it can only come
  from `Camera.main`'s stamped view/projection actually being the native plugin's per-frame camera
  (TRANSPLANT.md §1.1's "for free" claim, measured for the first time on a rendered model rather
  than argued from source).
- The native Bahamut **body** (scales, wings, head, legs — the 7 hidden keys) is invisible
  throughout. His **effects** (chant swirl, charge orbs, fire column, beam) still render normally —
  expected and desired (only the body keys are in `HideMeshes`).
- **The depth residual, visible for the first time:** watch specifically whether an effect that
  should originate at/near the creature (the fire column, the beam) draws convincingly in front of
  or behind Thomas as he crosses through it, or whether it visibly ignores his position entirely
  (because `SFXRender.Render()` forces the effect prims' `worldToCameraMatrix` to identity — a
  screen-space pass — while Thomas is an ordinary perspective-projected Unity mesh). This is
  TRANSPLANT.md's one true hybrid-vs-native fidelity gap (§1.1/§1.3 row "effect DEPTH interleave:
  BROKEN"), and M1a is the cheapest possible cast to *see* it rather than reason about it.

**FAILURE modes, each naming what it would falsify:**
- **Thomas's screen framing does NOT change across a hard cut** (he stays pixel-static through a
  cut that visibly reframes the arena/background) — falsifies "camera inheritance is free for a
  normal GameObject"; would point at TRANSPLANT.md risk #4 ("the live render-pass race") — i.e.
  Thomas may be rendering through a *different* camera pass than the one the plugin stamps, or the
  93-bone-drive write timing (irrelevant here, no drive yet) masks something about render-order.
- **Thomas renders through the wrong camera entirely** (e.g. the standard battle establishing
  shot instead of the cinematic framing) — same failure class, more obviously visible (totally
  different composition than the effects around him).
- **Thomas pops out / the model disappears before the real cast ends** — a `Start`/`End` or thread-
  timing defect (e.g. `End` too short relative to the donor's real `WaitSFXDone` gate), not a
  camera-inheritance finding; fix by lengthening `End` (520 is already the safe, current value —
  should not recur if §2.2 is followed exactly).
- **A dragon body fragment is still visible** through/behind Thomas — the 7-key `HIDE_KEYS` split
  is incomplete; not fatal to the camera-inheritance claim, but flags the PROBE.md round-2
  candidates (`00BDBE00`, `0098BD0E`) as needing incorporation before any polish milestone.

---

## 4. M1a as the depth-gate PRIM cast — the trade-off (stated, not decided)

Milestone 0 (TRANSPLANT.md §2.4) needs one instrumented cast with `CapturePrims` armed to (a)
validate the native reprojection math against the creature's own rendered `PRIM` screen footprint,
and (b) scan whether any effect `PRIM` occupies the creature's screen region at a nearer depth (the
hybrid-vs-native decision). Whether the M1a cast can supply that too, or should stay a separate
cast, is a real trade-off — not decided here, left for the orchestrator to reconcile with whatever
protocol the depth-prep agent is running:

- **What HideMeshes does NOT block:** `SummonData+0x38`/`+0x40` (bone/root reads), the `MODEL`/
  `BONES`/`PSXCAM` census (`CaptureModels`/`CaptureRoot`), and the still-*visible* effect meshes'
  own `PRIM` stream are all **untouched** by `HideMeshes` — that mask only prevents
  `Graphics.DrawMeshNow` for the 7 masked body keys (FORMAT.md §3.4: "`Hi_DrawEffModel` and friends
  contain zero references to `ModelData+0x20`"). So an M1a cast, if `CapturePrims`/`PrimSummary`
  were also armed, WOULD still yield: the creature's true per-frame position/AABB (from `BONES`,
  independent of rendering), the native camera track (`PSXCAM`), and every non-body effect's real
  `PRIM` rows — enough to run most of FORMAT.md §5.4's read-out steps (1–4, 6–7) and the item-(d)
  depth-occupancy scan.
- **What HideMeshes DOES block, and why that matters:** the creature's own body `PRIM`/`MESH` rows
  are never generated while hidden (FORMAT.md §3.4: "never enter the GTE, the ordering table, or
  `SFX_GetPrim`"). FORMAT.md §5.4 step 5 — the actual **validation** that the zero-free-parameter
  reprojection math is correct in the first place ("does the reprojected node-0 land inside the
  creature's own `PRIM` screen AABB") — needs that ground truth. **An M1a-only cast cannot supply
  it.** It can run the depth *scan* but not the thing the scan's own math rests on having been
  checked.
- **Practical cost of merging:** one fewer relaunch/cast cycle (real, non-trivial — every ini flag
  change needs a fresh game launch); but it also conflates two different visual read-outs on one
  capture (is-the-camera-cutting-around-a-static-Thomas vs. is-an-effect-occluding-him-wrong) and
  spends the M0 cast's "cleanest possible" property (zero Thomas-side variables: no mint, no
  background thread, no HideMeshes) on a build that has all three.
- **Net:** the cheapest-and-cleanest option is a separate, dedicated `--calibrate`-style cast
  (HideMeshes OFF, so the body's own `PRIM` footprint exists) for M0's core validation + depth scan,
  with M1a's own cast judged **by eye/video** for its two claims (camera inheritance, visible depth
  residual) rather than by log. Arming `CaptureModels`/`CaptureRoot`/`CapturePrims`/`PrimSummary`
  on the M1a cast **too** is free and would recover a coarse bonus depth scan — just without the
  step-5 ground-truth check. This document takes no side; the orchestrator should merge with
  whichever protocol the depth-prep agent lands on.

---

## 5. Design note — rigid Thomas on a 93-bone dragon, and what it means for M1b

Thomas the Tank Engine is a rigid, unskinned asset — no bones, no animation clips, normalized
offline once (`blender_normalize.py`) into a fixed upright/scaled/facing pose and shipped as-is.
M1a uses him exactly that way: one static hold, the closest thing to "his own idle" a boneless
model has. This is a fine, honest test of camera inheritance/body-hide/depth — none of those three
claims depend on the model having a skeleton at all.

**M1b is a different animal, and TRANSPLANT.md §2.2 already names the risk plainly:** the hybrid's
faithful-motion milestone poses **our mesh** every frame from the dragon's real 93 world-matrices
read live off `*(SummonData+0x38)` — which requires our mesh to be skinned onto a rig that
reproduces the dragon's own 93-node rest pose and 1:1 node correspondence (`summon-rig-ref`'s whole
purpose). **Thomas cannot be that mesh as-is.** A rigid model has no bones to bind to
`bone000..bone092`, so M1b's drive loop has nothing to write into for him — the hybrid pose-copy
mechanism is fundamentally a skinned-mesh operation. Reusing Thomas for M1b would mean either (a)
rigging a wholly new skinned Thomas onto the 93-bone dragon armature (a real modeling task, and per
TRANSPLANT.md's own flagged risk, a humanoid/vehicle-shaped silhouette on a long-necked quadruped
rig may pose correctly and still look wrong — an art call, not an engine failure), or (b) picking a
different M1b subject whose silhouette actually suits a 93-node dragon rig (another dragon,
quadruped, or serpent) to prove the hybrid mechanism cleanly before spending the rigging effort on
Thomas specifically. Either way, this is a decision for whoever picks up M1b, not a blocker for
M1a — flagged here exactly so it doesn't ambush that round.

---

## M1a — implemented (round 2 build, 2026-07-23)

Section 2.3's proposed code change is now live in `build_thomas.py`: a third mode `--m1a` (parallel to
`--thomas`/`--restore` in the same mutually-exclusive group), `build_manifest_json_m1a()` returning the
§2.2 static-hold dict from a new `M1A_STATIC_POINT = (132.5, 511.5, -1568)` constant, and `build_thomas()`
threading a `manifest_fn` parameter through unchanged otherwise (`splice_sequence`/`patched_line`/
`mint_thomas`/`HIDE_KEYS` all reused verbatim, exactly as this section specified). The stale `THOMAS_END`
comment ("580") is fixed to read the real 520. A `--dry-run` flag (any mode) stages every artifact under
`C:/gd/SCRATCH/summon-transplant/m1a_dry_run/FF9CustomMap/...` instead of the real mod folder and skips the
`thomas_manifest.sfxmodel` repo-copy sync — used to prove the bare (no-flag) mode still reproduces today's
FLIGHT v10.1 build byte-for-byte (re-verified this session by an independent sha256 read-only compare against
the live deployed files: `PlayerSequence.seq` `8465e5fa…`, `FileList.txt` `e0270970…`, `creature_manifest.sfxmodel`
`87140e02…` — all three identical between the `--dry-run` staging output, the live deployed mod folder, and the
repo's own committed `thomas_manifest.sfxmodel`; the mint's `6200.fbx`/`Thomas_d.png` bytes matched too,
`3ba4ad0d…`/`44b6f767…`) and to validate the `--m1a` manifest's JSON shape (Start=0/End=520, exactly one
Movement/Rotation piece at the exact static point, no Animations key, Scaling unchanged at 265 — 22/22 checks
green, re-run this session) before anything is deployed. Both dry runs confirmed zero writes to the real mod
folder (unchanged mtime/hash) and zero writes to the repo's `thomas_manifest.sfxmodel`.

**Deploy** (game may be open or closed — no relaunch needed, the mint is already registered):

```
py studies/custom-summons/thomas-swap/build_thomas.py --m1a
```

**Revert to the CURRENT v10.1 state** (not rung-7's own pre-Thomas resting state — the bare, no-flag
default mode reasserts FLIGHT v10.1 byte-for-byte, exactly as §2.4 already documented):

```
py studies/custom-summons/thomas-swap/build_thomas.py
```

**Success vs. failure on screen** (full table → §3 above): **SUCCESS** — Thomas (a small rigid train,
motionless in world space) visibly changes apparent size/position/framing as the real cinematic camera's
~15 hard cuts/dollies/zooms play through the cast, native Bahamut's body stays invisible throughout while
his effects (swirl/charge/fire column/beam) render normally around the static model. **FAILURE** — Thomas
stays pixel-static through a cut that visibly reframes the arena/background (camera inheritance isn't
free after all), or renders through a visibly different, non-cinematic camera pass entirely.

## M1a CAST READOUT — 2026-07-24 ★ CAMERA INHERITANCE PROVEN IN-GAME

The user deployed `--m1a` and cast. Report: *"thomas not follow at all... back to like 10% screen
time"* — **that IS the world-fixed success signature, now measured**: projecting the M1a static point
(132.5, 511.5, −1568) through the cast's own logged managed VIEW·PROJ predicts the point visible on
**3.3%** of camera frames (one window, f383–401; archived log
`C:/gd/SCRATCH/summon-transplant/logs/sfxmeshprobe.20260724-085556.log`) — the observed ~10% is the
same signature widened by the model's physical extent. The FAILURE mode (screen-glued model, no
camera inheritance) predicts **100%** screen time and is decisively ruled out. **The hybrid's core
premise — a managed object rides the native per-frame camera — is in-game proven.**

**The depth-gate half did NOT deconfound, and now we know why for certain:** the body-hidden cast's
gate table is IDENTICAL to the body-visible one (P8→P9 39/28/69 exact; in-band medians 621–1464
prims/frame) and the raw PRIM volume barely moved (549,216 vs 548,045) — behavioral proof of the
round-2 trace (CAST-PROTOCOL §4a): **the managed `HideMeshes=` suppresses only the final
`DrawMeshNow`, never primitive generation/logging.** The FRONT-class body-skin confound therefore
survives every `.seq`-level cast; the unconfounded depth verdict requires the NATIVE mask
(`SummonData+0x20`) — i.e. **the depth decision folds into M1b (s54 `HideNative`)**. Standing
verdict stays NATIVE-LEANING-BUT-UNPROVEN (DEPTH-GATE.md VERIFICATION).

Bench restored to v10.1 (`build_thomas.py`, live manifest sha 87140e02 re-verified) — the resting
state until the s54 go/no-go.
