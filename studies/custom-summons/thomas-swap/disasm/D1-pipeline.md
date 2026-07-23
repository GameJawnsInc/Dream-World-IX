# D1 — THE RECOMMENDED FAITHFUL-TRANSPLANT PIPELINE

**The synthesis slice.** T1/T2/T3/T4 each answered one question. This document picks the winning path,
states the honest fidelity-vs-effort-vs-provenance tradeoff, names the exact engine hooks and kit surface,
defines the minimum-viable first milestone, and stages the road to full fidelity — ranked by unblock-value.

All RVAs are image-base-relative to the user's own installed `FF9SpecialEffectPlugin.dll` (x64
`ImageBase 0x180000000`). C# cites are relative to `C:/gd/FFIX/Memoria/Assembly-CSharp/`. Confidence tags:
**PROVEN** (statically/independently verified in a Phase-1 slice), **PLAUSIBLE** (source-traced, not yet run
in-game), **SPECULATIVE** (reasoned, unverified). Provenance discipline (§9) is strict this round because the
work touches stock geometry + animation.

---

## 0. HEADLINE — the winning path, and the finding that decides it

**Build the HYBRID: our own skinned model, posed EACH FRAME by the dragon's real 93 world-matrices read live
from `*(SummonData+0x38)`, rendered through Unity's `Camera.main` which the plugin stamps with the native
per-frame camera.** This is T1's option **2.a** (live world-matrix bone drive). It is the faithful transplant
the FLIGHT overlay could never be: **our mesh + the dragon's actual articulation + its actual root flight +
its authored 0.02→3.0 scale sweep + its native camera (15 cuts, 47°→24° push-in)** — every one of the things a
hand-choreographed rigid billboard failed to fake, all inherited, all in perfect lockstep, all provenance-clean
(zero stock bytes shipped).

**The single finding that settles the design (T4 §1.2, PROVEN by constants):** *the native camera is inherited
by the MANAGED path too, not just the native slot.* During any summon, `Camera.main.worldToCameraMatrix` +
`.projectionMatrix` are stamped every frame from the plugin's real camera (`SFX.UpdateCamera`,
`SFX.cs:1590-1605`), and the managed `PsxProj2UnityProj` reconstruction reproduces the native GTE principal
point **exactly** (`PsxScreenHeightNative=220` → `top=120` = native `OFY=120`; `PsxCamera.cs:172-178`,
`FieldMap.cs:2336`). A Unity object placed at the creature's world point projects to the **same screen pixel**
the native creature would — for free, through every cut and zoom.

**Consequence — the brief's own contingency resolves in the managed path's favour.** The brief asked: *"if only
the native slot gets the true camera, say so and make that the target."* It does **not**. T4 proves the managed
path gets the true camera by construction. Therefore the native slot (T2) is **not** required for fidelity of
motion or camera — the two things the overlay got wrong. The **only** thing the native slot buys over the hybrid
is **per-poly depth interleave between our mesh and the screen-space effect prims** (T4 §1.5) — which matters
only for effects that physically *wrap* the creature body, and which is **measurable offline before any
playtest.** So: hybrid is the target; native (T2) is held in reserve for the depth ceiling alone.

---

## 1. THE DECISION — why the hybrid wins on all three axes

### 1.1 Fidelity — the hybrid fixes BOTH overlay failures; native adds only depth interleave

The FLIGHT overlay failed on two axes at once: a rigid billboard **could not read as a creature
flying/banking/shrinking/rolling** (no articulation, no true trajectory), and it **drifted off the camera**
(hand-animated projection). T4's ceiling table decomposes the fix:

| axis the overlay failed | HYBRID (T1 §2.a) | native slot T2 (W5) | T1b baked-clip FileList |
|---|---|---|---|
| **articulation** (wing-flap, body-flex) | **FAITHFUL** — driven by `+0x38` bones (T4 §2.3) | EXACT — native motion clip | **NONE** inherited — only the FBX's own idle (T4 §2.2) |
| **root flight** (the ~40k-unit fly-by) | **FAITHFUL** — folded into the same `+0x38` read (T1 §1.2) | EXACT | ⚠ needs a separate runtime `+0x40` feed |
| **scale sweep** (0.02→3.0×) | **FAITHFUL** — inside the `+0x38` columns (T1 §2.a.1) | EXACT | ⚠ needs the same runtime feed |
| **camera** (15 cuts, 47°→24° zoom) | **FAITHFUL** — `Camera.main` == native (T4 §1.2) | EXACT — GTE draws it | **FAITHFUL** — same mechanism |
| **clock / WAIT-hold sync** | UNIFIED — sampled on the native tick (T4 §2.3) | EXACT — welded to tick | UNIFIED on `SFX.frameIndex` |
| **effect DEPTH interleave** | **BROKEN** — screen-space vs perspective, wholesale sort (T4 §1.5) | **EXACT** — shared ordering table | BROKEN — same regime split |

Reading: **the hybrid closes every column the overlay failed**, and its *only* residual is the effect-depth
regime — a wholesale front/behind sort of our perspective mesh against the plugin's screen-space effect prims
(`SFXRender.cs:130` forces `worldToCameraMatrix = identity` for the effect prims; a real Unity FBX does not
share that Z axis, T4 §1.5). For a plunge-camera summon whose bursts frame the creature fore/background, this
reads acceptably; for effects that pass *through* the body volume it will not. **Native (T2) is the only path
that removes it** — and that is the *entire* fidelity delta between hybrid and native.

### 1.2 Effort — hybrid is MED; native is HIGH behind an untested $0 gate

* **Hybrid:** one new `memoria-patches` managed feature (~60-120 lines, T1 §2.a) co-located with the already-
  shipped s53 probe read, plus the shared rig work (§3). No external hard gate. Reuses the proven `ModelFactory.
  CreateModel` loader (`SFXDataMesh.cs:769`) and the proven camera-stamp path.
* **Native (T2/W5):** the geometry writer is **PROVEN writable** (T2 §2 — `ef_geom_writer.py`, 24/24 creatures
  + 135,728/135,728 primitive records byte-identical, novel block passes every native structural law), so the
  feared blocker is closed. But it is still gated on **W0** (does a mod-folder `ef###.bytes` override even load?
  — source-traced `SFX.cs:1974-1979`→`AssetManager.cs:541-627`, **never run**), plus texture/CLUT emission (W3,
  LOW), plus one cast to clear the opaque fields, plus the same rig conformance — and its failure mode is a
  **silent hang** (`0x151a0` spins forever after `"HIRAISHI ERROR:"`, FORMAT §4.3), so every container must be
  offline-linted before it ships.

### 1.3 Provenance — hybrid is the cleanest; native is verbatim-fork class

* **Hybrid:** reads the plugin's already-computed per-frame pose to drive **our own** mesh — the sanctioned
  choreography class, identical to the camera track logged since s48 and the root logged since s52
  (`SfxMeshProbe.cs:345-375`). It ships **no stock bytes**: no geometry, no animation payload, no
  `ef###.bytes`. The user's own FBX + a locally-derived rig are theirs. (T1 §6.)
* **Native (T2):** a build-time transform of the user's own install into their own mod folder — the
  verbatim-fork precedent. The donor's animation/geometry it edits stays local under
  `C:/gd/SCRATCH/summon-transplant/`. Clean, but one class more invasive.

**Verdict: the hybrid dominates on effort and provenance and matches native on every fidelity axis except
effect-depth interleave. Make it the target. Escalate to native (T2) only per-summon, only when the offline
depth check proves an effect must pass through the creature volume.**

---

## 2. THE ONE HONEST RISK, AND HOW IT IS RETIRED WITHOUT A PLAYTEST

The hybrid rests on two PLAUSIBLE (not yet PROVEN-in-game) mechanisms, and **both are settled by the
already-shipped s53 probe plus one instrumented Bahamut cast — zero playtests, zero new content:**

1. **Camera-mapping gate (T4 §1.6).** Per frame, project one controlled world point through BOTH the logged
   managed `VIEW·PROJ` (`SfxMeshProbe` VIEW/PROJ rows, `SfxMeshProbe.cs:328-337`) and the native `PSXCAM`
   (`M` @`0x1C1DC8` + OFX/OFY/H, `SfxMeshProbe.cs:595-614`). **Predicted: screen delta ≈ 0** (sub-pixel modulo
   fp12 + widescreen aspect). If it holds, "camera faithful by construction" becomes *measured*.
2. **Instant-phase gate (T4 §1.4).** The logged managed `VIEW` should equal the logged native `PSXCAM` `M`
   **every frame**; if it does, our puppet cannot lead/lag the prims by more than the ≤1-step residual, and the
   drive is coherent.

These are FORMAT §5's IMMEDIATE-NEXT-ACTION cast, already specced, already armed (s53 is deployed —
`memoria-patches/s53-sfx-model-census.patch`). **Run it first (Milestone 0 below).** The depth-interleave
residual (§1.1) is *also* offline-measurable from the same cast: inspect whether any effect `PRIM` stream
occupies the same screen region AND a nearer depth than the creature's body `PRIM` AABB on framed frames.

---

## 3. THE SHARED PREREQUISITE — same-skeleton rig conformance (both paths need it)

Every faithful path — hybrid, native, or baked-clip — needs **our mesh skinned to a rig that reproduces the
dragon's rest pose and 1:1 node correspondence** (T1 §3, T2 §3.1, T3 §2.3). This is the one irreducible creative
cost, and it is the natural cost of "wear the dragon's animation." The kit already emits skinned FBX in exactly
the shape this needs: `models/fbx_skin.py` names one bone `bone{NNN}` per node (the digits ARE the FF9 node
number) and **recomputes bind poses from each bone's rest transform** (T1 §3.1).

**Deliver `summon-rig-ref` (= T3's `summon-export` forward exporter).** It reads the USER's own `ef###.bytes`
(local, SCRATCH) and emits a **93-bone rig reference** `.glb` — bones `bone000..bone092`, parent indices, bone
lengths (`Node.length` → local `(0,0,length)`), a chosen rest pose (clip[0] frame 0 gives a recognizable dragon
per T3 §2.3) — that the user opens in Blender and skins their mesh onto. The exporter is **committable code**
(`ef_container.py` is already the validated parser, 372/372); the emitted stock-creature rig is Square-Enix-
derived geometry and stays **local under `C:/gd/SCRATCH/summon-transplant/`** (T3 §2.6). Drive is then **1:1 by
node index** — for the hybrid the world matrices land on `smr.bones[k]`; for the baked-clip lane the `.anim`
curves bind by bone name (T3 §3.1).

**Topology caveat (SPECULATIVE, design risk — flag to the user EARLY, T1 §3.2/P4):** same-skeleton authoring is
pleasant only for a creature whose silhouette suits a 93-node long-necked flyer (another dragon/quadruped/
serpent). A humanoid Thomas on a dragon rig may *pose correctly and still look wrong* — that is an art decision,
not an engine failure, and it should be surfaced before the user invests in skinning.

---

## 4. THE EXACT ENGINE HOOKS (memoria-patches — the hybrid drive feature, "s54")

A new patch on the `memoria-patches/` stack (next free id s54), a **managed** change to open-source
`Assembly-CSharp` — never a patched plugin DLL. It is an **owner go/no-go FEATURE**, one step past the passive
s52/s53 probe: it loads/drives our model and performs a runtime write into the plugin's state (the hide mask).
Say that in the commit message.

### 4.1 Where it hooks — PROVEN location

Co-locate with the s53 read inside `SFXDataMesh.Runtime.Render`, at **`SFXDataMesh.cs:659`** (right after
`SfxMeshProbe.LogModels()`). By that point this frame's native Draw has run — `SFX.SFX_LateUpdate()` +
`SFXRender.Update()` (`SFXDataMesh.cs:618-619`) have harvested the final tick's prims, and `*(SummonData+0x38)`
holds this frame's world matrices. The `Camera camera` is already resolved at **`SFXDataMesh.cs:635`** (the
`Camera.main`-or-"Battle Camera" fallback), and `SFXDataCamera.currentCameraEngine = SFX_PLUGIN` is set in
`Begin()` at **`SFXDataMesh.cs:607`** so the camera is the native one.

### 4.2 The per-frame loop — PLAUSIBLE build, PROVEN read path

Read the summon slot exactly as the probe already does (`SfxMeshProbe.cs:479-497,552-564`):

```
base   = GetModuleHandle("FF9SpecialEffectPlugin.dll")          // SfxMeshProbe.cs:386-400
rec    = base + 0x220830          // summon record (LENGTH 1) — Hi_RegisterSummonModel@0x15ee0:0x15f14
active = ReadByte(rec + 0x50)     // 0 => no summon this frame  — bail
sData  = ReadIntPtr(rec + 0x00)   // -> SummonData
bones  = ReadIntPtr(sData + 0x38) // the 93 world matrices; 0 => never drawn (model_prepare@0x7120:0x71f7) — bail
for k in 0..92:
    M   = bones + k*0x20          // 32-byte PSX MATRIX: s16 3x3 /4096 @+0x00, s32 t @+0x14
    smr.bones[k].position = PsxToUnityPos(M.t)     // absolute WORLD pose (matrices are already composed, T1 §1.2)
    smr.bones[k].rotation = PsxToUnityRot(M.R)      // node builder writes +0x38 every Draw @0x7820:0x7842
```

* `smr` = the `SkinnedMeshRenderer` of our FBX, loaded once via `ModelFactory.CreateModel(fbxPath, …)`
  (`SFXDataMesh.cs:769`) with its `Animation` component disabled. **The existing FileList path exposes NO
  settable bones** — `JSON.Render` only sets a whole-object `transform.position/eulerAngles/localScale` and
  plays a named clip (`SFXDataMesh.cs:831-858`); a grep of `Battle/SFX/` finds **zero** `SkinnedMeshRenderer.
  bones`/`bindposes` refs (T1 §2.0). So this loop is genuinely new managed code — a small custom renderer that
  writes bone `Transform`s each frame.
* Writing each bone's **absolute world** transform overwrites our model's own parenting every frame, so only
  *correspondence* (bone `k` ↔ node `k`) and *bind pose* matter — no runtime hierarchy walk (T1 §2.a).

### 4.3 Hide the native creature body — PROVEN mechanism, runtime write

Assert the total-hide mask each frame before the native draw:

```
WriteInt32(sData + 0x20, (1 << meshCount) - 1)     // 0x3 for Bahamut's 2 meshes
```

The mask at `SummonData+0x20` is **re-read on every mesh of every frame** (`0x17910-0x17919`), is **summon-only**
(`Hi_DrawEffModel` has zero refs to it — T4 §3.1, FORMAT §3.4), and hiding the body **leaves every
swirl/beam/fire-column effect rendering**, with bone-parented props still following the native skeleton (which
keeps computing under a hidden body — T4 §3.2). `meshCount ∈ {2,3}` across all 24 creature-bearing effects
(Bahamut = 2 → mask `0x3`). This is a runtime write into plugin state — **one class more invasive than the s53
read, hence the owner go/no-go** (FORMAT §3.4). (The managed `HideMeshes=` SFXKey split, already proven in the
FLIGHT work, is an alternative that needs no native write and is the safer first cut — §5 M1a uses it.)

### 4.4 The PSX→Unity calibration — PLAUSIBLE, ZERO free parameters

Per bone: `rotation` = the s16 3×3 ÷ 4096 with columns 1,2 negated (the `diag(1,-1,-1)` handedness flip the
plugin itself applies, node builder root branch `0x797a`); `translation` = the s32 triple mapped `(tx,-ty,-tz)/
scale` into `Camera.main`'s world space (T1 §2.a.1). **The scale factor + exact sign are calibrated ONCE**
against the s53 `BONES`/`PRIM` screen AABB (`SfxMeshProbe.cs:667-697`) — a validator with **zero free
parameters**, not a search. The 0.02→3.0 scale sweep is already inside the `+0x38` columns, so it reproduces
automatically — this is the exact term `root_reproject.py:43/75` silently discarded in FLIGHT (FORMAT §1.4).

### 4.5 The camera residual to watch (PLAUSIBLE, the one live unknown)

Our `SkinnedMeshRenderer` renders in Unity's normal camera pass through `Camera.main`'s stamped native
VIEW/PROJ (§0). The open point: `SFXRender.Render()` sets `worldToCameraMatrix = identity` for the effect prims
and restores it (`SFXRender.cs:130`), and `Runtime.Render` saves/restores it at `SFXDataMesh.cs:636/678` — does
this race our puppet's render pass? T4 §1.4 argues no (both settle to the final tick), but it is the one thing
to confirm on the M1a cast.

---

## 5. THE MILESTONE LADDER — smallest thing first, de-risked, verbatim-first

Following the project's `feedback-incremental-verbatim-first` law: study real bytes → replicate ONE piece →
verify; offline ≠ in-game proof. Each milestone is a single in-game check.

### Milestone 0 — the offline camera/reprojection gate (1 cast, ZERO new content) — **do this first**
Take one instrumented Bahamut cast on the bench (field 30300, id 194) with the **already-deployed s53 probe**
armed (`[SfxProbe] Enabled=1 CaptureModels=1 CapturePrims=1 ModelsBoneCount=93`, FORMAT §5.2). Run the two gates
(§2) + the depth-residual scan offline. **Exit:** managed `VIEW·PROJ` == native `PSXCAM` per frame (camera
faithful, measured); the PSX→Unity scale/sign fixed from the `BONES`/`PRIM` AABB. Unblocks everything below.
*Cost: LOW, read-only, provenance-clean.*

### Milestone 1a — our model rides the dragon's CAMERA (reuse rung-7 verbatim, ZERO new engine code)
FileList a proven rung-7 FBX into a Bahamut donor cast and hide the native body with the **managed `HideMeshes=`
split** (already proven in FLIGHT). Our model plays only its own idle, but it **inherits the native camera** —
banks/zooms/cuts — and composites into the effect. **This isolates the camera-inheritance proof, the body-hide,
and the depth-interleave residual (§1.1) in-game, with no new engine code.** Exit: our model stays glued to the
shot through every cut; note whether any effect wrongly sorts through it (the depth check, live).
*Cost: LOW. This is the honest "our model where the creature renders" first light.*

### Milestone 1b — THE FAITHFUL MVP: our model + the dragon's real MOTION
Land the **s54 hybrid drive feature** (§4). The user skins their mesh onto the `summon-rig-ref` rig (§3), the
drive loop poses it each frame from `+0x38`, the body is hidden. **Exit / the smallest faithful render: our
mesh flaps, banks, shrinks, and flies with the dragon's actual per-frame motion, through the dragon's actual
camera, in one cast on the bench.** This is the transplant the overlay could never be. *Cost: MED (the drive
feature + the calibration from M0).*

### Milestone 2 — fidelity polish + the Blender authoring surface (T3)
The s46 render-rig lessons (live-silhouette fit, body-blend zoom, lighting), the measured depth-residual verdict
per summon, and the Blender round-trip: `summon-export` (rig → `.glb`, §3) → user retargets → `summon-import`
(the FileList/`.sfxmodel` return, T3 §3.1, reuses `models/` verbatim). The baked-clip lane (T1 §2.b) becomes the
provenance-cleaner offline-editable sibling here. *Cost: MED, mostly kit code + proven routes.*

### Milestone 3 — the native ceiling (T2), ONLY if the depth residual bites
If M0/M1a show an effect must pass **through** the creature volume (per-poly depth interleave required),
escalate that summon to the native model-package swap. **Run W0 first** — the $0 2-cast load-gate that unblocks
*all* native writing (FORMAT §4.3 W0). If W0 passes: `ef_geom_writer.py` (PROVEN) + the header-offset math
(PROVEN, T2 §2.2) + texture/CLUT emit (W3, LOW) + the offline geom linter (built) → our creature rendered by the
donor's own program/camera, per-poly depth-correct. Failure mode is a silent hang → **never ship an unlinted
container.** *Cost: HIGH. Deferred, and only per-summon.*

---

## 6. THE KIT SURFACE — a managed `[[summon]]` lane, kept SEPARATE from the native family

Per FORMAT §4.4.5 (*"do not conflate the managed and native lanes — different provenance rules, different
failure modes"*):

* **`[[summon]]` block / `summon-transplant` verb (the MANAGED lane — the recommendation).** Inputs: the user's
  retargeted FBX + a donor summon id. It (a) runs `summon-rig-ref` to emit the local rig for skinning, (b)
  deploys the FBX into the effect's model slot, and (c) writes the drive-feature manifest (which summon slot to
  drive with which model, gated like the probe). This is the surface the user authors against — it targets the
  proven managed lane. New kit modules: `summons/build.py` (the Model-struct adapter, T3 §2.2), `summons/motion.
  py` (the offline clip decoder for the baked-clip sibling, T3 §2.4), `summons/export.py` (glTF emit, reuses
  `models/gltf.py`).
* **The native read/fork family (a SEPARATE surface).** `summon-inspect` (container map + creature package +
  camera tracks + loader script + annotated MIPS listing — FORMAT §4.2 R-tier), `summon-disasm`, `summon-fork`
  (the W-tier in-place editors). These share `ef_container.py` + `ef_geom_writer.py` (both committable, both
  proven). **Do not merge them into `[[summon]]`.**

---

## 7. RANKED BY UNBLOCK-VALUE ÷ COST

| # | action | cost | unblocks |
|---|---|---|---|
| 1 | **M0 — the offline camera/reprojection + depth gate** (armed s53 probe, 1 cast) | 1 cast, read-only | The whole hybrid: proves camera inheritance is *measured*, fixes the PSX→Unity calibration, and reads the depth residual that decides hybrid-vs-native per summon. |
| 2 | **`summon-rig-ref` / `summon-export`** (the shared 93-bone rig; committable tool) | LOW–MED | BOTH paths — the user can start skinning immediately; it is the gate on all faithful rendering. |
| 3 | **M1a — rung-7 FBX + managed HideMeshes in a donor cast** | LOW, no new engine code | Camera-inheritance + body-hide + depth residual, proven in-game, isolated from the bone drive. |
| 4 | **M1b — the s54 hybrid drive feature** | MED (memoria-patches) | THE faithful transplant — our mesh + the dragon's real motion + native camera. |
| 5 | **W0 — the native load-gate** ($0, 2 casts) | $0, 2 casts | ALL of the native lane (T2). Run it early even though T2 is deferred — it is free and de-risks the entire depth ceiling. |
| 6 | **M2 — polish + Blender round-trip (T3)** | MED | The user's second ask ("export into Blender") + offline-editable clips. |
| 7 | **M3 — native model-package swap (T2/W5)** | HIGH | Per-poly depth-correct effects — only for body-wrapping summons the depth check flags. |

---

## 8. FALSIFIABLE PREDICTIONS / WHAT WOULD SINK THIS

* **P1 (PROVEN-false-if):** on the M0 cast, `bones = *(sData+0x38)` is zero or static while the creature
  visibly animates ⇒ T1 §1.2 is wrong for this build. (Contra: node builder writes it every Draw, `0x7842`; the
  s53 probe already reads bone-0 from it, `SfxMeshProbe.cs:636-651`.)
* **P2 (camera mapping):** managed `VIEW·PROJ` ≠ native `PSXCAM` `M`+OFX/OFY/H on framed frames ⇒ the camera is
  NOT inherited for free and the hybrid degrades to "right pose, wrong projection." Fix path: drive `Camera.main`
  from the decoded native camera track (W-CAM). T4 §1.2's constants make a match LIKELY.
* **P3 (the calibration):** the driven `bones[0].t` projected through the logged camera does not land inside the
  creature's own `PRIM` AABB ⇒ the PSX→Unity map is wrong; the raw `PsxCtx[+0x14]` tamper column
  (`SfxMeshProbe.cs:602-604`) says whether the effect re-pointed the view — a bounded next question, not a guess.
* **P4 (the depth residual):** an effect prim occupies the creature's screen region at a nearer depth on framed
  frames ⇒ that summon needs native (T2), the hybrid will sort it wrong. Measurable offline from M0.
* **P5 (topology — DESIGN risk, SPECULATIVE):** a humanoid mesh on a 93-node dragon rig may look wrong even when
  posed correctly. Not an engine failure — flag before the user skins (§3, T1 §3.2).
* **P6 (W0):** a mod-folder `ef###.bytes` override does not load ⇒ the entire native lane (T2) needs an engine
  change; the hybrid becomes the only faithful path (T2 §4). $0 to test.

---

## 9. PROVENANCE (this slice)

* This document is **synthesis** — it cites RVAs, `file:line`, struct offsets, and the Phase-1 slices' counts.
  No stock geometry, animation payload, texture, or `ef###.bytes` was read into or quoted here.
* **The hybrid drive feature reads the plugin's already-computed per-frame pose to drive OUR mesh** — the
  sanctioned choreography class, identical to the camera track (s48) and root (s52). It ships no stock content
  and patches no plugin DLL. **Dumping `bones[1..92]` across a cast as a redistributable animation asset stays
  BLOCKED** (that reconstructs the stock skeletal animation); the live drive consumes the matrices frame-by-
  frame and persists none.
* **The `summon-rig-ref`/`summon-export` output (a stock creature's rig + any baked clip) is Square-Enix-
  derived content → local-only under `C:/gd/SCRATCH/summon-transplant/`**, exactly the battle-import / verbatim-
  fork precedent. The tools are committable code; the CLI defaults its output to SCRATCH and refuses to write a
  stock export into the repo or a distributed mod folder.
* **The native model-package swap (T2/M3) is a build-time transform of the user's OWN install into their OWN
  mod folder** — never committed, never redistributed. **Never produce or ship a patched
  `FF9SpecialEffectPlugin.dll`.**
* All native claims are read-only static analysis of the user's own installed DLL, cited `fn@rva`; all managed
  claims cite `file:line`.
